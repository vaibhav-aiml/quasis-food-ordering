"""Structured logging setup.

Per Phase 0 architecture doc, section 13: every log line is JSON with a
consistent set of base fields, so a request's full trace can be reconstructed
with plain ``grep``/``jq`` even before a database or log aggregator exists.

Deliberately implemented with the stdlib ``logging`` module rather than a
third-party structured-logging library (e.g. ``structlog``) — see the
Phase 2 design notes for the tradeoff. This can be swapped later without
touching call sites, since everything goes through ``get_logger()``.
"""

import logging
import sys
from datetime import datetime, timezone
from typing import Any

from app.core.config import Settings

# Fields present on every stdlib LogRecord that we do NOT want to treat as
# "extra" structured fields when flattening a record to JSON.
_STANDARD_LOG_RECORD_ATTRS = frozenset(logging.makeLogRecord({}).__dict__.keys())


class JsonFormatter(logging.Formatter):
    """Renders each log record as a single line of JSON.

    Any keys passed via ``logger.info(msg, extra={...})`` are merged into
    the output automatically, so callers can attach ``request_id``,
    ``graph_node``, ``store_id``, etc. without this formatter needing to
    know about them in advance.
    """

    def format(self, record: logging.LogRecord) -> str:
        import json

        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        # Merge in any caller-supplied structured fields (e.g. request_id).
        for key, value in record.__dict__.items():
            if key not in _STANDARD_LOG_RECORD_ATTRS and key not in payload:
                payload[key] = value

        return json.dumps(payload, default=str)


def setup_logging(settings: Settings) -> None:
    """Configure the root logger once, at application startup.

    Idempotent-ish: calling this more than once replaces handlers rather
    than stacking them, so re-invoking it (e.g. in tests) doesn't duplicate
    log lines.
    """

    root_logger = logging.getLogger()
    root_logger.setLevel(settings.log_level.upper())

    # Remove any handlers a previous call (or a library) may have attached,
    # so log lines aren't duplicated.
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(JsonFormatter())
    root_logger.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger.

    Thin wrapper over ``logging.getLogger`` — kept as a function (rather
    than having call sites use the stdlib directly) so this is the one
    place that would change if the logging backend is ever swapped.
    """

    return logging.getLogger(name)
