# src/streamdaq/logging/__init__.py

"""
Logging module for StreamDaQ v2.
Handles namespace isolation, root pollution prevention, and structured logging hooks.
"""

from streamdaq.logging.managers import configure_logging
from streamdaq.logging.handlers import JsonFormatter, LogHook
from streamdaq.logging.utils import get_logger

# Explicitly define the public API for this namespace
__all__ = [
    "configure_logging",
    "get_logger",
    "JsonFormatter",
    "LogHook",
]
