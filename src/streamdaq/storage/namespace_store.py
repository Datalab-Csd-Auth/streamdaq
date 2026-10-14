from collections.abc import Iterator
from typing import Generic

import lmdb

from streamdaq.storage.codecs import BaseCodec, T


class NamespaceStore(Generic[T]):
    """A dictionary-like interface to a named sub-database within an LMDB environment.
    https://lmdb.readthedocs.io/en/latest/#named-databases"""

    def __init__(self, env: lmdb.Environment, namespace: str, codec: BaseCodec[T]):
        self.env = env
        self.sub_db = env.open_db(namespace.encode("utf-8"))
        self.codec = codec

    def __getitem__(self, key: str) -> T:
        with self.env.begin(db=self.sub_db) as txn:
            data = txn.get(key.encode("utf-8"))
            if data is None:
                raise KeyError(key)
            return self.codec.decode(data)

    def __setitem__(self, key: str, value: T) -> None:
        with self.env.begin(write=True, db=self.sub_db) as txn:
            txn.put(key.encode("utf-8"), self.codec.encode(value))

    def __delitem__(self, key: str) -> None:
        with self.env.begin(write=True, db=self.sub_db) as txn:
            if not txn.delete(key.encode("utf-8")):
                raise KeyError(key)

    def __contains__(self, key: str) -> bool:
        with self.env.begin(db=self.sub_db) as txn:
            return txn.get(key.encode("utf-8")) is not None

    def get(self, key: str, default: T | None = None) -> T | None:
        with self.env.begin(db=self.sub_db) as txn:
            data = txn.get(key.encode("utf-8"))
            return self.codec.decode(data) if data is not None else default

    def atomically_advance_to_max(self, key: str, value: T) -> None:
        with self.env.begin(write=True, db=self.sub_db) as txn:
            raw = txn.get(key.encode("utf-8"))
            current = self.codec.decode(raw) if raw is not None else None
            if current is None or value > current:
                txn.put(key.encode("utf-8"), self.codec.encode(value))

    def clear(self) -> None:
        with self.env.begin(write=True) as txn:
            txn.drop(self.sub_db, delete=False)

    def items(self) -> Iterator[tuple[str, T]]:
        with self.env.begin(db=self.sub_db) as txn:
            for key, value in txn.cursor():
                yield key.decode("utf-8"), self.codec.decode(value)
