from abc import ABC, abstractmethod
from typing import Generic, TypeVar

T = TypeVar("T")


class BaseCodec(ABC, Generic[T]):
    """Converts a stored value to and from the raw ``bytes`` that LMDB persists."""

    @abstractmethod
    def encode(self, value: T) -> bytes: ...

    @abstractmethod
    def decode(self, raw: bytes) -> T: ...
