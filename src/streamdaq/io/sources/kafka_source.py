import uuid
from typing import ClassVar

import pathway as pw

from streamdaq.io.sources.base import BaseSource


class KafkaSource(BaseSource):
    source_type: ClassVar[str] = "kafka"

    def read_raw(self, schema=None, data_format=None) -> pw.Table:
        params = dict(self.connector_params)
        if schema is not None:
            params["schema"] = schema
        if data_format is not None:
            params["format"] = data_format
        # Pathway reads the consumer group from the rdkafka settings only
        rdkafka_settings = dict(params.get("rdkafka_settings", {}))
        rdkafka_settings.setdefault("group.id", f"streamdaq_reader_{uuid.uuid4().hex[:8]}")
        params["rdkafka_settings"] = rdkafka_settings
        return pw.io.kafka.read(**params)

    def _native_data_format(self) -> str:
        return self.connector_params.get("format", "json")

    def _compact_data_format(self) -> str:
        return "json"
