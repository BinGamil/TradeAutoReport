"""Logging setup for the project."""

from __future__ import annotations

import logging


def get_logger(name: str = "trade_auto_report") -> logging.Logger:
    """Return a console logger with a consistent format."""

    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    )
    logger.addHandler(handler)
    logger.propagate = False
    return logger
