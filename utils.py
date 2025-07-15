import time
import logging


def retry_on_failure(retries: int = 3, delay: int = 2, backoff: int = 2):
    """Retry decorator for BitMEX orders."""

    def decorator(func):
        def wrapper(*args, **kwargs):
            current_delay = delay
            for attempt in range(retries):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    logging.warning(
                        "Retry %s/%s after error: %s", attempt + 1, retries, exc
                    )
                    time.sleep(current_delay)
                    current_delay *= backoff
            logging.error(
                "Function %s failed after %s retries.", func.__name__, retries
            )
            return None

        return wrapper

    return decorator

