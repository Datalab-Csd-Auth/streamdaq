from typing import ClassVar

import pathway as pw

from streamdaq.io.sinks.base import BaseSink


class PostgresSink(BaseSink):
    sink_type: ClassVar[str] = "postgres"

    def write(self, table: pw.Table, **params) -> None:
        pw.io.postgres.write(table, **params)
