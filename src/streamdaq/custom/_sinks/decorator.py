from collections.abc import Callable

import pathway as pw

from streamdaq.io.sinks.custom_sink import CustomSink
from streamdaq.io.sinks.registry import SINK_REGISTRY
from streamdaq.utils.picklable import Lambda


def sink(name: str | None = None):
    """Registers the decorated function as a custom streamdaq output sink.
    It can then be referenced by name as an output ``type`` in a task payload."""

    def decorator(func: Callable[[pw.Table], None]) -> Callable[[pw.Table], None]:
        sink_name = name or func.__name__
        SINK_REGISTRY[sink_name] = CustomSink(Lambda(func))
        return func

    return decorator
