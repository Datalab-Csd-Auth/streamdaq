import re
import uuid
from enum import auto

from strenum import LowercaseStrEnum

from streamdaq.utils.enums import Py312EnumMeta

DTYPE_STR_TO_DTYPE: dict[str, type] = {
    "int": int,
    "float": float,
    "str": str,
    "bool": bool,
    "bytes": bytes,
}


class DataFormat(LowercaseStrEnum, metaclass=Py312EnumMeta):
    NATIVE = auto()
    COMPACT = auto()


def ensure_unique_mqtt_client_id(uri: str, role: str = "reader") -> str:
    """Returns ``uri`` with a unique ``client_id`` query parameter.

    If client ID is missing, it is appended appended.
    If client ID exists, it is suffixed to keep it unique across concurrent connections.
    """
    if "client_id=" not in uri:
        separator = "&" if "?" in uri else "?"
        return f"{uri}{separator}client_id=streamdaq_{role}_{uuid.uuid4().hex[:8]}"
    return re.sub(r"(client_id=[^&]+)", r"\1_" + uuid.uuid4().hex[:6], uri)


def split_connector_params(params: dict, reserved_keys: tuple[str, ...]) -> dict:
    """Extracts the connector kwargs from a payload's input params.

    An explicit ``connector_params`` mapping is used as-is; otherwise every key that is not a
    reserved streamdaq key is treated as a connector kwarg.
    """
    if "connector_params" in params:
        return params["connector_params"]
    return {key: value for key, value in params.items() if key not in reserved_keys}
