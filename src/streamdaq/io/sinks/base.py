from typing import ClassVar

import pathway as pw

from streamdaq.io.sinks.registry import SINK_REGISTRY


class BaseSink:
    """A streamdaq output sink that writes a ``pw.Table``.

    Subclasses implement :meth:`write` for their destination and declare a ``sink_type``; each
    concrete subclass is auto-registered as an instance into ``SINK_REGISTRY``, so the engine
    can invoke it directly as ``sink(table, **output_kwargs)``.
    """

    sink_type: ClassVar[str] = ""

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls.sink_type:
            SINK_REGISTRY[cls.sink_type] = cls()

    def __call__(self, table: pw.Table, **params) -> None:
        self.write(table, **params)

    def write(self, table: pw.Table, **params) -> None:
        raise NotImplementedError
