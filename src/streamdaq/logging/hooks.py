from abc import ABC, abstractmethod
import logging
from typing import Any, Dict

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
