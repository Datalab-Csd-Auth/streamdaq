from collections.abc import Callable

SINK_REGISTRY: dict[str, Callable[..., None]] = {}
