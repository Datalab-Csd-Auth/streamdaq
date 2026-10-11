from pathlib import Path

import lmdb

from streamdaq.storage.codecs.int_codec import IntCodec
from streamdaq.storage.namespace_store import NamespaceStore


class WatermarkStore:
    """A per-task LMDB store holding the instant and window watermarks."""

    _NAMESPACE = "watermarks"
    _INSTANT_KEY = "instant"
    _WINDOW_KEY = "window"
    _DEFAULT_MAP_SIZE_BYTES = 1 * 1024 * 1024

    def __init__(self, path: str):
        Path(path).mkdir(parents=True, exist_ok=True)
        self.env = lmdb.open(path, subdir=True, map_size=self._DEFAULT_MAP_SIZE_BYTES, max_dbs=4)
        self._store: NamespaceStore[int] = NamespaceStore(self.env, self._NAMESPACE, IntCodec())

    def _advance(self, key: str, value: int) -> None:
        current = self._store.get(key)
        if current is None or value > current:
            self._store[key] = value

    def read_instant_watermark(self) -> int | None:
        """The latest processed event time for instant checks, or ``None`` if unset."""
        return self._store.get(self._INSTANT_KEY)

    def read_window_watermark(self) -> int | None:
        """The latest processed window end for window checks, or ``None`` if unset."""
        return self._store.get(self._WINDOW_KEY)

    def advance_instant_to(self, value: int) -> None:
        """Persist ``value`` as the instant watermark if it exceeds the current one, else no-op."""
        self._advance(self._INSTANT_KEY, value)

    def advance_window_to(self, value: int) -> None:
        """Persist ``value`` as the window watermark if it exceeds the current one, else no-op."""
        self._advance(self._WINDOW_KEY, value)

    def close(self) -> None:
        self.env.sync()
        self.env.close()
