import struct

from streamdaq.storage.codecs.base import BaseCodec


class IntCodec(BaseCodec[int]):
    """Serializes an integer as a big-endian signed 64-bit value"""

    _BIG_ENDIAN_SIGNED_INT_FORMAT = ">q"

    def encode(self, value: int) -> bytes:
        return struct.pack(self._BIG_ENDIAN_SIGNED_INT_FORMAT, value)

    def decode(self, raw: bytes) -> int:
        return struct.unpack(self._BIG_ENDIAN_SIGNED_INT_FORMAT, raw)[0]
