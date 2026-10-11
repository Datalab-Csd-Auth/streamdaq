from typing import ClassVar

import pathway as pw

from streamdaq.io.sources.base import BaseSource


class JsonlinesSource(BaseSource):
    source_type: ClassVar[str] = "jsonlines"
    supports_compact: ClassVar[bool] = False
    reserved_param_keys: ClassVar[tuple[str, ...]] = ("data_type", "schema", "mode")

    def __init__(self, params: dict) -> None:
        super().__init__(params)
        self.mode = params.get("mode", "streaming")

    def read_raw(self, schema=None, data_format=None) -> pw.Table:
        return pw.io.jsonlines.read(schema=schema, mode=self.mode, **self.connector_params)
