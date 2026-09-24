import importlib
from typing import ClassVar

import pathway as pw

from streamdaq.io.sources.base import BaseSource


class PythonConnectorSource(BaseSource):
    source_type: ClassVar[str] = "python_connector"
    reserved_param_keys: ClassVar[tuple[str, ...]] = (
        "data_type",
        "schema",
        "module",
        "class_name",
    )

    def __init__(self, params: dict) -> None:
        super().__init__(params)
        self.module = params["module"]
        self.class_name = params["class_name"]

    def read_raw(self, schema=None, data_format=None) -> pw.Table:
        module = importlib.import_module(self.module)
        subject_class = getattr(module, self.class_name)
        subject = subject_class(**self.connector_params)
        if schema is not None:
            return pw.io.python.read(subject, schema=schema)
        return pw.io.python.read(subject)
