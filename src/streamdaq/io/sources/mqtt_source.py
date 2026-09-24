from typing import ClassVar

import pathway as pw

from streamdaq.io.sources.base import BaseSource
from streamdaq.io.utils import ensure_unique_mqtt_client_id


class MqttSource(BaseSource):
    source_type: ClassVar[str] = "mqtt"

    def read_raw(self, schema=None, data_format=None) -> pw.Table:
        params = dict(self.connector_params)
        if schema is not None:
            params["schema"] = schema
        if data_format is not None:
            params["format"] = data_format
        params["uri"] = ensure_unique_mqtt_client_id(params.get("uri", ""), role="reader")
        return pw.io.mqtt.read(**params)

    def _native_data_format(self) -> str:
        return self.connector_params.get("format", "json")

    def _compact_data_format(self) -> str:
        return "json"
