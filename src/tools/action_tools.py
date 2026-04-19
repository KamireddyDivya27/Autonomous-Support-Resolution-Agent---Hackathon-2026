"""Action tools: send_reply, escalate."""
import asyncio
from datetime import datetime

class ActionTools:
    def __init__(self):
        self.sent_replies = []
        self.escalations = []
    
    async def send_reply(self, ticket_id: str, message: str, customer_email: str = None):
        if not message:
            raise ValueError("Cannot send empty reply")
        await asyncio.sleep(0.1)
        self.sent_replies.append({"ticket_id": ticket_id, "message": message})
        return {"ticket_id": ticket_id, "status": "sent"}
    
    async def escalate(self, ticket_id: str, summary: str, priority: str, context: dict = None):
        if not summary:
            raise ValueError("Escalation summary required")
        await asyncio.sleep(0.1)
        self.escalations.append({"ticket_id": ticket_id, "summary": summary, "priority": priority})
        return {"ticket_id": ticket_id, "status": "escalated"}

def get_action_tools():
    return ActionTools()
