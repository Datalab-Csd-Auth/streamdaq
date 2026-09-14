# src/streamdaq/logging/__init__.py

"""
Logging module for StreamDaQ v2.
Handles namespace isolation, root pollution prevention, and structured logging hooks.
"""

from streamdaq.logging.handlers import JsonFormatter, LogHook, LogHookHandler
from streamdaq.logging.managers import configure_logging

__all__ = [
    "configure_logging",
    "JsonFormatter",
    "LogHook",
    "LogHookHandler",
]
