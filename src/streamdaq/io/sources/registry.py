from collections.abc import Callable

import pathway as pw

SOURCE_REGISTRY: dict[str, Callable[[dict], Callable[..., pw.Table]]] = {}
