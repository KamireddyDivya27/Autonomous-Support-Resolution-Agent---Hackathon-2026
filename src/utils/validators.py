"""Schema validation utilities."""
import logging
logger = logging.getLogger(__name__)

def validate_preconditions(conditions: dict, action_name: str) -> bool:
    failed = [k for k, v in conditions.items() if not v]
    if failed:
        error = f"Precondition failed for {action_name}: {failed}"
        logger.error(error)
        raise ValueError(error)
    return True

def is_malformed_response(response) -> bool:
    if response is None:
        return True
    if isinstance(response, dict):
        if response.get("status") == "unknown" or response.get("data") is None:
            return True
    return False
