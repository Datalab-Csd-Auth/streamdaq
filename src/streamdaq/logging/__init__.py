# src/streamdaq/logging/__init__.py

"""
Logging module for StreamDaQ v2.
Handles namespace isolation, root pollution prevention, and structured logging hooks.
"""

from streamdaq.logging.config import configure_logging
from streamdaq.logging.formatters import JsonFormatter
from streamdaq.logging.utils import get_logger
from streamdaq.logging.hooks import LogHook

# Explicitly define the public API for this namespace
__all__ = [
    "configure_logging",
    "get_logger",
    "JsonFormatter",
    "LogHook",
]
