"""Structured logging system for audit trail."""
import json
import logging
from pathlib import Path
from datetime import datetime

class AuditLogger:
    def __init__(self, log_dir: str = "data/audit_logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def log_ticket_start(self, ticket_id: str, agent_session_id: str, ticket_data: dict):
        self.logger.info(f"Processing started: {ticket_id}")
    
    def log_classification(self, ticket_id: str, category: str, urgency: str, confidence: float, reasoning: str):
        self.logger.info(f"Classified {ticket_id}: {category} ({urgency}) - {confidence:.2f}")
    
    def log_tool_call(self, ticket_id: str, sequence: int, tool_name: str, input_params: dict, 
                     output: any, success: bool, duration_ms: int, retries: int = 0, error_message: str = None):
        status = "✓" if success else "✗"
        self.logger.info(f"{status} Tool {sequence}: {tool_name} ({duration_ms}ms)")
    
    def log_decision(self, ticket_id: str, step: str, reasoning: str, confidence: float):
        self.logger.info(f"Decision [{step}]: {reasoning}")
    
    def log_resolution(self, ticket_id: str, resolution_type: str, resolution_time_s: float, customer_message: str = None):
        self.logger.info(f"✓ Resolved {ticket_id} in {resolution_time_s:.2f}s")
    
    def log_escalation(self, ticket_id: str, reason: str, priority: str, summary: str, context: dict):
        self.logger.warning(f"⚠ Escalated {ticket_id}: {reason}")
    
    def log_error(self, ticket_id: str, error_type: str, error_message: str, context: dict):
        self.logger.error(f"✗ Error {ticket_id}: {error_message}")
    
    def save_audit_log(self, audit_data: dict, ticket_id: str):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"audit_{ticket_id}_{timestamp}.json"
        filepath = self.log_dir / filename
        with open(filepath, 'w') as f:
            json.dump(audit_data, f, indent=2, default=str)
        return filepath

def setup_logging(log_level: str = "INFO"):
    return AuditLogger()

def get_audit_logger():
    return AuditLogger()
