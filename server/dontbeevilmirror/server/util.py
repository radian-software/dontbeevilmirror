from contextlib import contextmanager
import datetime
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


def strftime(dt: datetime.datetime):
    return dt.strftime("%Y-%m-%d %H:%M:%S.%f %Z")


def now(tz: datetime.timezone | None = None) -> datetime.datetime:
    return datetime.datetime.now(tz)
