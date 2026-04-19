"""Order management tools with realistic failures."""
import asyncio
import random
from datetime import datetime, timedelta
from src.utils.retry import retry_with_backoff
import logging

logger = logging.getLogger(__name__)

MOCK_ORDERS = {
    "ORD-001": {
        "order_id": "ORD-001",
        "customer_email": "customer1@example.com",
        "status": "delivered",
        "order_date": (datetime.now() - timedelta(days=15)).isoformat(),
        "items": [{"product_id": "PROD-101", "name": "Laptop"}],
        "total_amount": 999.99
    },
    "ORD-002": {
        "order_id": "ORD-002",
        "customer_email": "customer2@example.com",
        "status": "shipped",
        "order_date": (datetime.now() - timedelta(days=5)).isoformat(),
        "items": [{"product_id": "PROD-102", "name": "Mouse"}],
        "total_amount": 49.99
    },
    "ORD-003": {
        "order_id": "ORD-003",
        "customer_email": "customer3@example.com",
        "status": "delivered",
        "order_date": (datetime.now() - timedelta(days=45)).isoformat(),
        "items": [{"product_id": "PROD-103", "name": "Keyboard"}],
        "total_amount": 129.99
    }
}

class OrderTools:
    def __init__(self):
        pass
    
    @retry_with_backoff(max_retries=3, exceptions=(TimeoutError,))
    async def get_order(self, order_id: str):
        await asyncio.sleep(random.uniform(0.1, 0.3))
        if order_id not in MOCK_ORDERS:
            raise ValueError(f"Order {order_id} not found")
        return MOCK_ORDERS[order_id].copy()
    
    @retry_with_backoff(max_retries=3, exceptions=(TimeoutError,))
    async def check_refund_eligibility(self, order_id: str):
        await asyncio.sleep(random.uniform(0.1, 0.3))
        order = await self.get_order(order_id)
        order_date = datetime.fromisoformat(order["order_date"])
        days_old = (datetime.now() - order_date).days
        
        if days_old > 30:
            return {"eligible": False, "reason": "Order older than 30 days"}
        return {"eligible": True, "reason": "Within 30-day window", "refund_amount": order["total_amount"]}
    
    async def issue_refund(self, order_id: str, amount: float, eligibility_verified: bool = False):
        if not eligibility_verified:
            raise ValueError("SAFETY ABORT: Cannot issue refund without eligibility verification")
        await asyncio.sleep(0.2)
        return {
            "refund_id": f"REF-{random.randint(1000, 9999)}",
            "order_id": order_id,
            "amount": amount,
            "status": "processed"
        }

def get_order_tools():
    return OrderTools()
