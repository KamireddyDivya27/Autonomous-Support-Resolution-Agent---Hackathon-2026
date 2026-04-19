"""
Main entry point for autonomous support agent.

Hackathon requirement: "Concurrent Processing - tickets must be 
processed concurrently, not one-by-one"
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Any
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from src.agents.support_agent import SupportAgent
from src.utils.logger import setup_logging
import logging

# Load environment variables
load_dotenv()

console = Console()
logger = logging.getLogger(__name__)


async def process_ticket_with_agent(
    agent: SupportAgent,
    ticket: Dict[str, Any],
    progress: Progress,
    task_id: int
) -> Dict[str, Any]:
    """
    Process a single ticket with progress tracking.
    
    Args:
        agent: Agent instance
        ticket: Ticket data
        progress: Rich progress bar
        task_id: Progress task ID
    
    Returns:
        Processing result
    """
    try:
        progress.update(task_id, description=f"Processing {ticket['ticket_id']}...")
        
        result = await agent.process_ticket(ticket)
        
        status = "✓ Resolved" if result["is_resolved"] else "⚠ Escalated"
        progress.update(task_id, description=f"{status} {ticket['ticket_id']}")
        
        return {
            "ticket_id": ticket["ticket_id"],
            "status": "RESOLVED" if result["is_resolved"] else "ESCALATED",
            "confidence": result["overall_confidence"],
            "tool_calls": len(result["tool_calls"]),
            "errors": len([tc for tc in result["tool_calls"] if not tc["success"]]),
            "duration_s": time.time() - result["start_time"]
        }
        
    except Exception as e:
        logger.error(f"Failed to process {ticket['ticket_id']}: {e}")
        progress.update(task_id, description=f"✗ Failed {ticket['ticket_id']}")
        
        return {
            "ticket_id": ticket["ticket_id"],
            "status": "FAILED",
            "error": str(e),
            "tool_calls": 0,
            "errors": 1,
            "duration_s": 0
        }


async def process_tickets_concurrently(
    tickets: List[Dict[str, Any]],
    max_workers: int = 3
) -> List[Dict[str, Any]]:
    """
    Process multiple tickets concurrently.
    
    Hackathon requirement: Concurrent processing, not sequential.
    
    Args:
        tickets: List of tickets to process
        max_workers: Maximum concurrent workers
    
    Returns:
        List of processing results
    """
    console.print(f"\n[bold blue]Processing {len(tickets)} tickets with {max_workers} concurrent workers...[/bold blue]\n")
    
    # Initialize agent (reused across tickets for efficiency)
    agent = SupportAgent(llm_model=os.getenv("LLM_MODEL", "gpt-4-turbo-preview"))
    
    results = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(max_workers)
        
        async def process_with_semaphore(ticket: Dict[str, Any]):
            """Process ticket with semaphore to limit concurrency"""
            async with semaphore:
                task_id = progress.add_task(f"Queued {ticket['ticket_id']}", total=None)
                return await process_ticket_with_agent(agent, ticket, progress, task_id)
        
        # Process all tickets concurrently (with max_workers limit)
        results = await asyncio.gather(
            *[process_with_semaphore(ticket) for ticket in tickets],
            return_exceptions=True
        )
    
    # Handle any exceptions in results
    processed_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"Ticket {tickets[i]['ticket_id']} failed: {result}")
            processed_results.append({
                "ticket_id": tickets[i]["ticket_id"],
                "status": "FAILED",
                "error": str(result)
            })
        else:
            processed_results.append(result)
    
    return processed_results


def print_summary(results: List[Dict[str, Any]]):
    """Print summary statistics."""
    console.print("\n[bold green]╔═══════════════════════════════╗[/bold green]")
    console.print("[bold green]║    PROCESSING SUMMARY         ║[/bold green]")
    console.print("[bold green]╚═══════════════════════════════╝[/bold green]\n")
    
    # Calculate statistics
    total = len(results)
    resolved = len([r for r in results if r.get("status") == "RESOLVED"])
    escalated = len([r for r in results if r.get("status") == "ESCALATED"])
    failed = len([r for r in results if r.get("status") == "FAILED"])
    
    total_tool_calls = sum(r.get("tool_calls", 0) for r in results)
    total_errors = sum(r.get("errors", 0) for r in results)
    avg_duration = sum(r.get("duration_s", 0) for r in results) / total if total > 0 else 0
    
    # Create summary table
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Total Tickets", str(total))
    table.add_row("Resolved", f"{resolved} ({resolved/total*100:.1f}%)" if total > 0 else "0")
    table.add_row("Escalated", f"{escalated} ({escalated/total*100:.1f}%)" if total > 0 else "0")
    table.add_row("Failed", f"{failed} ({failed/total*100:.1f}%)" if total > 0 else "0")
    table.add_row("", "")
    table.add_row("Total Tool Calls", str(total_tool_calls))
    table.add_row("Avg Tool Calls/Ticket", f"{total_tool_calls/total:.1f}" if total > 0 else "0")
    table.add_row("Total Errors", str(total_errors))
    table.add_row("Avg Duration", f"{avg_duration:.2f}s")
    
    console.print(table)
    
    # Detailed results table
    console.print("\n[bold]Detailed Results:[/bold]\n")
    
    detail_table = Table(show_header=True, header_style="bold blue")
    detail_table.add_column("Ticket ID", style="cyan")
    detail_table.add_column("Status", style="yellow")
    detail_table.add_column("Tool Calls", justify="right")
    detail_table.add_column("Errors", justify="right")
    detail_table.add_column("Duration", justify="right")
    
    for result in results:
        status_icon = {
            "RESOLVED": "✓",
            "ESCALATED": "⚠",
            "FAILED": "✗"
        }.get(result.get("status"), "?")
        
        detail_table.add_row(
            result.get("ticket_id", "Unknown"),
            f"{status_icon} {result.get('status', 'Unknown')}",
            str(result.get("tool_calls", 0)),
            str(result.get("errors", 0)),
            f"{result.get('duration_s', 0):.2f}s"
        )
    
    console.print(detail_table)


def load_tickets(filepath: str = "data/tickets/sample_tickets.json") -> List[Dict[str, Any]]:
    """Load tickets from JSON file."""
    path = Path(filepath)
    
    if not path.exists():
        console.print(f"[bold red]Error: Ticket file not found: {filepath}[/bold red]")
        sys.exit(1)
    
    with open(path, 'r') as f:
        tickets = json.load(f)
    
    console.print(f"[green]Loaded {len(tickets)} tickets from {filepath}[/green]")
    return tickets


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Autonomous Support Agent")
    parser.add_argument(
        "--tickets",
        default="data/tickets/sample_tickets.json",
        help="Path to tickets JSON file"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=int(os.getenv("CONCURRENT_WORKERS", "3")),
        help="Number of concurrent workers"
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run demo with all 20 sample tickets"
    )
    parser.add_argument(
        "--log-level",
        default=os.getenv("LOG_LEVEL", "INFO"),
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(log_level=args.log_level)
    
    # Print header
    console.print("\n[bold magenta]═══════════════════════════════════════════════[/bold magenta]")
    console.print("[bold magenta]  AUTONOMOUS SUPPORT RESOLUTION AGENT 2026    [/bold magenta]")
    console.print("[bold magenta]═══════════════════════════════════════════════[/bold magenta]\n")
    
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        console.print("[bold red]Error: OPENAI_API_KEY not set in environment![/bold red]")
        console.print("Please set it in .env file or environment variables.")
        sys.exit(1)
    
    # Load tickets
    tickets = load_tickets(args.tickets)
    
    if not tickets:
        console.print("[bold red]No tickets to process![/bold red]")
        sys.exit(1)
    
    # Process tickets
    start_time = time.time()
    
    try:
        results = await process_tickets_concurrently(
            tickets=tickets,
            max_workers=args.workers
        )
        
        total_time = time.time() - start_time
        
        # Print summary
        print_summary(results)
        
        console.print(f"\n[bold green]Total processing time: {total_time:.2f}s[/bold green]")
        console.print(f"[bold]Audit logs saved to: data/audit_logs/[/bold]\n")
        
    except KeyboardInterrupt:
        console.print("\n[bold red]Processing interrupted by user[/bold red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[bold red]Fatal error: {e}[/bold red]")
        logger.exception("Fatal error in main")
        sys.exit(1)


if __name__ == "__main__":
    # Run async main
    asyncio.run(main())
