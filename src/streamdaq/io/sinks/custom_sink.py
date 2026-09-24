from collections.abc import Callable

import pathway as pw

from streamdaq.io.sinks.base import BaseSink


class CustomSink(BaseSink):
    """A user-defined sink registered via the ``@sink`` decorator.

    ``write`` delegates to the user's writer function, which receives the table and the payload's
    output ``params`` as keyword arguments.
    """

    def __init__(self, writer: Callable[..., None]) -> None:
        self.writer = writer

    def write(self, table: pw.Table, **params) -> None:
        self.writer(table, **params)
