from typing import ClassVar

import pathway as pw

from streamdaq.io.sources.base import BaseSource


class CsvSource(BaseSource):
    source_type: ClassVar[str] = "csv"
    supports_compact: ClassVar[bool] = False
    reserved_param_keys: ClassVar[tuple[str, ...]] = ("data_type", "schema", "mode")

    def __init__(self, params: dict) -> None:
        super().__init__(params)
        self.mode = params.get("mode", "streaming")

    def read_raw(self, schema=None, data_format=None) -> pw.Table:
        if self.mode == "static":
            return pw.io.fs.read(format="csv", mode="static", **self.connector_params)
        return pw.io.csv.read(**self.connector_params)
