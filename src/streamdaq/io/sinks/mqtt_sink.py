from typing import ClassVar

import pathway as pw

from streamdaq.io.sinks.base import BaseSink
from streamdaq.io.utils import ensure_unique_mqtt_client_id


class MqttSink(BaseSink):
    sink_type: ClassVar[str] = "mqtt"

    def write(self, table: pw.Table, **params) -> None:
        params = dict(params)
        params["uri"] = ensure_unique_mqtt_client_id(params.get("uri", ""), role="writer")
        pw.io.mqtt.write(table, **params)
