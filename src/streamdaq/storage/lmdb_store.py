from collections.abc import Iterator
from typing import Any, Generic, TypeVar

import lmdb

T = TypeVar("T")


class NamespaceStore(Generic[T]):
    """
    A dictionary-like interface to an LMDB environment, scoped by a namespace.
    """

    def __init__(self, db: lmdb.Environment, namespace: str, value_type: Any):
        self.db = db
        self.namespace = namespace.encode("utf-8") + b":"
        self.value_type = value_type

    def _make_key(self, key: str) -> bytes:
        return self.namespace + key.encode("utf-8")

    def __getitem__(self, key: str) -> T:
        db_key = self._make_key(key)
        with self.db.begin() as txn:
            data = txn.get(db_key)
            if data is None:
                raise KeyError(key)
            return self.value_type.model_validate_json(data.decode("utf-8"))

    def __setitem__(self, key: str, value: T) -> None:
        db_key = self._make_key(key)
        data = value.model_dump_json().encode("utf-8")
        with self.db.begin(write=True) as txn:
            txn.put(db_key, data)

    def __delitem__(self, key: str) -> None:
        db_key = self._make_key(key)
        with self.db.begin(write=True) as txn:
            if not txn.delete(db_key):
                raise KeyError(key)

    def __contains__(self, key: str) -> bool:
        db_key = self._make_key(key)
        with self.db.begin() as txn:
            return txn.get(db_key) is not None

    def clear(self) -> None:
        with self.db.begin(write=True) as txn:
            cursor = txn.cursor()
            if cursor.set_range(self.namespace):
                keys_to_delete = []
                for key, _ in cursor:
                    if not key.startswith(self.namespace):
                        break
                    keys_to_delete.append(key)
                for k in keys_to_delete:
                    txn.delete(k)

    def items(self) -> Iterator[tuple[str, T]]:
        with self.db.begin() as txn:
            cursor = txn.cursor()
            if cursor.set_range(self.namespace):
                for key, value in cursor:
                    if not key.startswith(self.namespace):
                        break
                    str_key = key[len(self.namespace) :].decode("utf-8")
                    parsed_value = self.value_type.model_validate_json(value.decode("utf-8"))
                    yield str_key, parsed_value
