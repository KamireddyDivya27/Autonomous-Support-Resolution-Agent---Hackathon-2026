# Autonomous Support Resolution Agent — Hackathon 2026

An autonomous AI agent that resolves customer support tickets using a multi-step reasoning chain with LangGraph-style state management.

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/hackathon2026-YOUR_NAME
cd hackathon2026-YOUR_NAME

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set your API key in .env
OPENROUTER_API_KEY=sk-or-your-key-here

# 5. Run the agent (CLI)
python main.py

# 6. Run the web UI
python app.py
# Open http://localhost:5000
```

## Tech Stack
- **Language:** Python 3.11
- **Orchestration:** Custom agentic state machine (LangGraph-style)
- **LLM:** OpenRouter (openrouter/auto) via LangChain
- **Web UI:** Flask
- **Logging:** Structured JSON audit logs

## Agent Architecture

The agent follows a 6-step reasoning pipeline per ticket:

1. **INTAKE** — Extract entities (order IDs, emails) from raw ticket
2. **CLASSIFY** — LLM classifies category, urgency, confidence (0-1)
3. **PLAN** — Dynamically selects tool chain based on classification
4. **EXECUTE** — Runs tools sequentially with full error handling
5. **DECIDE** — Evaluates success rate, routes to resolve or escalate
6. **RESOLVE / ESCALATE** — Sends reply or hands off with structured summary

## Tool Chain
| Tool | Type | Description |
|------|------|-------------|
| get_customer | READ | Customer profile and tier |
| get_order | READ | Order details and status |
| check_refund_eligibility | READ | Eligibility check (may throw errors) |
| issue_refund | WRITE | Irreversible — guarded by precondition check |
| send_reply | WRITE | Customer-facing response |
| escalate | WRITE | Human handoff with full context |

## Key Features
- **Concurrent processing** — All tickets processed in parallel via asyncio
- **Safety gates** — issue_refund blocked unless eligibility confirmed
- **Confidence calibration** — Agent knows when it does not know (escalates if confidence < 0.5)
- **Full audit trail** — Every tool call, decision, and reasoning step logged to JSON
- **Graceful failure handling** — Tool failures caught, logged, agent continues

## Running Against All 20 Tickets
```bash
python main.py
```
Audit logs saved to `data/audit_logs/`

## Submission
- **Author:** KAMIREDDY DIVYA
- **Hackathon:** Agentic AI Hackathon 2026 by Ksolves
