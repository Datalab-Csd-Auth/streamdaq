from typing import TypeVar

from pydantic import BaseModel

from streamdaq.storage.codecs.base import BaseCodec

ModelT = TypeVar("ModelT", bound=BaseModel)


class PydanticCodec(BaseCodec[ModelT]):
    """Serializes a pydantic model via its JSON representation."""

    def __init__(self, model_type: type[ModelT]):
        self.model_type = model_type

    def encode(self, value: ModelT) -> bytes:
        return value.model_dump_json().encode("utf-8")

    def decode(self, raw: bytes) -> ModelT:
        return self.model_type.model_validate_json(raw.decode("utf-8"))
