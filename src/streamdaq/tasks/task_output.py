from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TaskOutput:
    meta_stream: Callable[[Any], None]  # pw.io...write operation
    meta_stream_kwargs: dict[str, Any] = field(default_factory=lambda: {})
    errors_only: Callable[[Any], None] | None = None
    errors_only_kwargs: dict[str, Any] = field(default_factory=lambda: {})
    valid_only: Callable[[Any], None] | None = None
    valid_only_kwargs: dict[str, Any] = field(default_factory=lambda: {})
