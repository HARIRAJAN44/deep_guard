"""
Structured logging configuration for DeepGuard.
"""
import logging
import sys
from typing import Any


class _SafeFormatter(logging.Formatter):
    """JSON-like log format. Masks sensitive fields."""
    _MASKED_KEYS = frozenset({"password", "otp", "api_key", "secret", "token"})

    def format(self, record: logging.LogRecord) -> str:
        msg = super().format(record)
        # Basic masking: if any masked key appears in the message, truncate its value
        for key in self._MASKED_KEYS:
            if key in msg.lower():
                msg = f"[MASKED LOG — field '{key}' detected]"
                break
        return msg


def configure_logging(debug: bool = False) -> None:
    level = logging.DEBUG if debug else logging.INFO

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    )

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(handler)

    # Quiet noisy libraries
    logging.getLogger("motor").setLevel(logging.WARNING)
    logging.getLogger("pymongo").setLevel(logging.WARNING)
    logging.getLogger("tensorflow").setLevel(logging.ERROR)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("multipart").setLevel(logging.WARNING)
