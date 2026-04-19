"""Retry logic with exponential backoff."""
import asyncio
import random
from functools import wraps
import logging

logger = logging.getLogger(__name__)

def retry_with_backoff(max_retries: int = 3, initial_delay: float = 1.0, 
                       max_delay: float = 10.0, exceptions: tuple = (Exception,)):
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    if attempt < max_retries:
                        delay = min(initial_delay * (2 ** attempt), max_delay)
                        delay += random.uniform(0, delay * 0.25)
                        logger.warning(f"Retry {attempt+1}/{max_retries+1} after {delay:.2f}s: {e}")
                        await asyncio.sleep(delay)
                    else:
                        logger.error(f"All retries exhausted: {e}")
                        raise
        return async_wrapper
    return decorator
