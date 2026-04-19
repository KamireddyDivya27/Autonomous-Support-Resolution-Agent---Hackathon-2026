"""Customer lookup tools."""
import asyncio
from datetime import datetime, timedelta
from src.utils.retry import retry_with_backoff

MOCK_CUSTOMERS = {
    "customer1@example.com": {
        "email": "customer1@example.com",
        "name": "Alice Johnson",
        "tier": "GOLD",
        "total_orders": 15
    },
    "customer2@example.com": {
        "email": "customer2@example.com",
        "name": "Bob Smith",
        "tier": "SILVER",
        "total_orders": 5
    },
    "customer3@example.com": {
        "email": "customer3@example.com",
        "name": "Carol White",
        "tier": "BRONZE",
        "total_orders": 2
    }
}

class CustomerTools:
    @retry_with_backoff(max_retries=3, exceptions=(TimeoutError,))
    async def get_customer(self, email: str):
        await asyncio.sleep(0.1)
        if email not in MOCK_CUSTOMERS:
            raise ValueError(f"Customer {email} not found")
        return MOCK_CUSTOMERS[email].copy()

def get_customer_tools():
    return CustomerTools()
