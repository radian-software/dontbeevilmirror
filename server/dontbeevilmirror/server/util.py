from contextlib import contextmanager
import threading


class TimeoutDueToRateLimit(Exception):
    pass


@contextmanager
def rate_limit_with_timeout(ratelimit: threading.Semaphore, timeout_seconds: float):
    try:
        if ratelimit.acquire(timeout=timeout_seconds):
            yield
        else:
            raise TimeoutDueToRateLimit
    finally:
        ratelimit.release()
