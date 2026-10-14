"""
database.py — stubbed out.

MySQL has been removed.  All persistence now lives in app.db.memory_store.
This module is kept so that any remaining import references don't break;
the functions are intentional no-ops.
"""
import logging

logger = logging.getLogger(__name__)


async def connect_db() -> None:
    """No-op: in-memory store requires no connection."""
    logger.info("In-memory store active — no MySQL connection needed.")


async def close_db() -> None:
    """No-op."""
    logger.info("In-memory store shutdown (no-op).")


def get_session_factory():
    """Not used in no-DB mode. Raises clearly if called accidentally."""
    raise RuntimeError(
        "get_session_factory() called but MySQL has been removed. "
        "Use app.db.memory_store directly."
    )

