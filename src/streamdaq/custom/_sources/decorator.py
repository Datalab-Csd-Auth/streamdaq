from collections.abc import Callable
from typing import Any

from streamdaq.io.sources.custom_source import build_custom_input
from streamdaq.io.sources.registry import SOURCE_REGISTRY
from streamdaq.io.utils import DataFormat
from streamdaq.utils.picklable import Lambda


def source(name: str | None = None, data_format: str = DataFormat.NATIVE):
    """Registers the decorated factory as a custom streamdaq input source.
    It can then be referenced by name as an input ``type`` in a task payload.
    The payload's ``connector_params`` are forwarded to the decorated factory as
    keyword arguments."""

    if data_format not in DataFormat:
        available_formats = [str(data_format) for data_format in DataFormat]
        raise ValueError(f"`data_format` must be one of {available_formats}, got '{data_format}'.")

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        source_name = name or func.__name__
        SOURCE_REGISTRY[source_name] = build_custom_input(Lambda(func), data_format)
        return func

    return decorator
