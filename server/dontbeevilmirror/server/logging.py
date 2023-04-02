from datetime import timezone
from typing import Any

from dontbeevilmirror.server.util import now, strftime


def log(level: str, message: str, extra: dict[str, Any] = {}):
    ts = strftime(now(timezone.utc))
    end = ""
    if extra:
        end = " ::" + "".join(
            f" {key}={str(val)}" for key, val in sorted(extra.items())
        )
    print(f"<evil> {ts} [{level.upper()}] {message}{end}")


def trace(message: str, extra: dict[str, Any] = {}):
    log("trace", message, extra)


def info(message: str, extra: dict[str, Any] = {}):
    log("info", message, extra)


def warn(message: str, extra: dict[str, Any] = {}):
    log("warn", message, extra)


def error(message: str, extra: dict[str, Any] = {}):
    log("error", message, extra)
