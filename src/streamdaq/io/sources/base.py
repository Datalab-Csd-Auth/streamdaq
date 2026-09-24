from typing import ClassVar

import pathway as pw

from streamdaq.io.sources.registry import SOURCE_REGISTRY
from streamdaq.io.utils import DTYPE_STR_TO_DTYPE, DataFormat, split_connector_params
from streamdaq.schema.evb import EVBSchema, discover_native_evb_schema
from streamdaq.schema.evb.wrangling import convert_raw_evb_to_native_format
from streamdaq.utils.picklable import Lambda


class BaseSource:
    """A streamdaq input source that produces a native ``pw.Table``."""

    source_type: ClassVar[str] = ""
    supports_compact: ClassVar[bool] = True
    reserved_param_keys: ClassVar[tuple[str, ...]] = ("data_type", "schema")

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls.source_type:
            SOURCE_REGISTRY[cls.source_type] = cls

    def __init__(self, params: dict) -> None:
        self.data_type = params.get("data_type", DataFormat.NATIVE)
        self.schema_params = params.get("schema", {})
        self.connector_params = split_connector_params(params, self.reserved_param_keys)
        self.files_path: str | None = None

    def read_raw(self, schema=None, data_format=None) -> pw.Table:
        raise NotImplementedError

    def __call__(self, **kwargs) -> pw.Table:
        if self.data_type == DataFormat.NATIVE:
            return self._read_native()
        if self.data_type == DataFormat.COMPACT:
            return self._read_compact()
        raise ValueError(f"Unknown data_type: {self.data_type}")

    def _read_native(self) -> pw.Table:
        columns = {
            column: pw.column_definition(dtype=DTYPE_STR_TO_DTYPE[dtype_str])
            for column, dtype_str in self.schema_params.items()
        }
        schema = pw.schema_builder(columns) if columns else None
        return self.read_raw(schema=schema, data_format=self._native_data_format())

    def _read_compact(self) -> pw.Table:
        if not self.supports_compact:
            raise ValueError(
                f"The '{self.source_type}' source does not support the 'compact' data format."
            )

        data_format = self._compact_data_format()
        if self.schema_params:
            native_evb_schema = tuple(
                (column, DTYPE_STR_TO_DTYPE[dtype_str])
                for column, dtype_str in self.schema_params.items()
            )
        else:
            native_evb_schema = discover_native_evb_schema(
                get_table_function=Lambda(
                    lambda: self.read_raw(schema=EVBSchema, data_format=data_format)
                ),
                timeout_seconds=20,
                files_path=self.files_path,
            )

        raw_table = self.read_raw(schema=EVBSchema, data_format=data_format)
        return convert_raw_evb_to_native_format(raw_table, native_evb_schema)

    def _native_data_format(self) -> str | None:
        return None

    def _compact_data_format(self) -> str | None:
        return None
