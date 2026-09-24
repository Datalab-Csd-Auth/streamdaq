from typing import ClassVar

import pathway as pw

from streamdaq.io.sinks.base import BaseSink


class CsvSink(BaseSink):
    sink_type: ClassVar[str] = "csv"

    def write(self, table: pw.Table, **params) -> None:
        pw.io.csv.write(table, **params)
