from typing import ClassVar

import pathway as pw

from streamdaq.io.sinks.base import BaseSink


class JsonlinesSink(BaseSink):
    sink_type: ClassVar[str] = "jsonlines"

    def write(self, table: pw.Table, **params) -> None:
        pw.io.jsonlines.write(table, **params)
