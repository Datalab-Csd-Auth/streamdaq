import json
import logging
import time
from typing import Any, Dict
from abc import ABC, abstractmethod

class JsonFormatter(logging.Formatter):
    """
    Serializes LogRecords into single-line JSON objects.
    Dynamically extracts standard attributes and merges custom extra context.
    """
    def __init__(self, datefmt: str = "%Y-%m-%dT%H:%M:%S") -> None:
        # We don't rely on standard fmt strings since layout is explicitly structured JSON
        super().__init__(datefmt=datefmt)

    def format(self, record: logging.LogRecord) -> str:
        # Base JSON payload with standardized engineering keys
        payload: Dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Include exception tracking if present in the log record
        if record.exc_info:
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
            payload["exception"] = record.exc_text

        # Include stack trace info if explicitly requested via stack_info=True
        if record.stack_info:
            payload["stack_info"] = self.formatStack(record.stack_info)

        # Dynamic Extraction: Capture any extra={...} variables passed at runtime
        # Standard LogRecord internal attributes to skip so we don't duplicate data
        reserved_attrs = {
            "args", "asctime", "created", "exc_info", "exc_text", "filename",
            "funcName", "levelname", "levelno", "lineno", "module", "msecs",
            "message", "msg", "name", "pathname", "process", "processName",
            "relativeCreated", "stack_info", "thread", "threadName"
        }

        for key, value in record.__dict__.items():
            if key not in reserved_attrs:
                payload[key] = value

        return json.dumps(payload, ensure_ascii=False)

class LogHook(ABC):
    """
    Abstract Base Class defining the v2 LogHook specification interface.
    Subclasses must implement emission logic to stream structured telemetry 
    records to custom sinks (e.g., memory rings, persistent files, network topics).
    """
    
    @abstractmethod
    def emit(self, record: logging.LogRecord, formatted_record: str) -> None:
        """
        Processes a single log record event.

        Args:
            record: The raw, stateful execution logging.LogRecord object.
            formatted_record: The pre-serialized string output (e.g., JSON line).
        """
        pass

    @abstractmethod
    def flush(self) -> None:
        """
        Forces the underlying sink mechanism to empty its internal volatile buffers.
        Crucial for preventing data loss on application teardown or panics.
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """
        Safely tears down the sink allocations, disposes of active network descriptors,
        or handles outstanding background file handles.
        """
        pass
