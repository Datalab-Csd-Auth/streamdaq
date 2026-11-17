from abc import ABC, abstractmethod
from typing import Callable, ClassVar, Protocol

import pathway as pw

from streamdaq.io.sources.registry import SOURCE_REGISTRY
from streamdaq.io.utils import DTYPE_STR_TO_DTYPE, DataFormat, split_connector_params
from streamdaq.schema.evb import EVBSchema, discover_native_evb_schema
from streamdaq.schema.evb.wrangling import convert_raw_evb_to_native_format
from streamdaq.utils.picklable import Lambda


class ReadRaw(Protocol):
    def __call__(
        self, 
        instance: "BaseSource",
        schema: type[pw.Schema] | None = None,
        data_format: DataFormat | None = None
    ) -> pw.Table:
        ...

class ReadRawWithPostTransform(Protocol):
    def __call__(
        self, 
        instance: "BaseSource",
        schema: type[pw.Schema] | None = None,
        data_format: DataFormat | None = None
    ) -> tuple[pw.Table, Callable[[pw.Table], pw.Table]]:
        ...

class BaseSource(ABC):
    """A streamdaq input source that produces a native ``pw.Table``."""

    source_type: ClassVar[str] = ""
    supports_compact: ClassVar[bool] = True
    reserved_param_keys: ClassVar[tuple[str, ...]] = (
        "data_type",
        "schema",
        "timeout",
    )

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls.source_type:
            SOURCE_REGISTRY[cls.source_type] = cls

    def __init__(self, params: dict) -> None:
        self.data_type = DataFormat(params.get("data_type", "native"))
        self.schema_params: dict = params.get("schema", {})
        self.timeout: int = params.get("timeout", 20)
        self.connector_params = split_connector_params(
            params,
            self.reserved_param_keys
        )
        self.files_path: str | None = None

    @abstractmethod
    def read_raw(
        self,
        schema: type[pw.Schema] | None = None,
        data_format: str | None = None
    ) -> pw.Table | tuple[pw.Table, Callable[[pw.Table], pw.Table]]:
        ...

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
        table = self.read_raw(
            schema=schema,
            data_format=self._native_data_format()
        )

        if not isinstance(table, pw.Table):
            raise TypeError(
                f"A native custom source must return a `pw.Table`, got {type(table).__name__}."
            )
        return table

    def _read_compact(self) -> pw.Table:
        if not self.supports_compact:
            raise ValueError(
                f"The '{self.source_type}' source does not support the 'compact' data format."
            )

        data_format = self._compact_data_format()

        result =  self.read_raw(
            schema=EVBSchema,
            data_format=data_format
        )

        table: pw.Table
        post_transform: Callable[[pw.Table], pw.Table] | None = None
        match result:
            case (raw_table, transform_func):
                table = raw_table
                post_transform = transform_func

                get_table_function = Lambda(
                    lambda: self.read_raw(
                        schema=EVBSchema,
                        data_format=data_format
                    )[0]
                )
            case _:
                assert isinstance(result, pw.Table)
                table = result

                get_table_function = Lambda(
                    lambda: self.read_raw(
                        schema=EVBSchema,
                        data_format=data_format
                    )
                )

        if self.schema_params:
            native_evb_schema = {
                "fields": tuple(
                    (column, DTYPE_STR_TO_DTYPE[dtype_str])
                    for column, dtype_str 
                    in self.schema_params.get("fields", {}).items()
                )
            } | {
                "tags": tuple(
                    (column, DTYPE_STR_TO_DTYPE[dtype_str])
                    for column, dtype_str 
                    in self.schema_params.get("tags", {}).items()
                )
            }
        else:
            native_evb_schema = discover_native_evb_schema(
                get_table_function=get_table_function,
                timeout_seconds=self.timeout,
                files_path=self.files_path,
            )

        native_table = convert_raw_evb_to_native_format(
            table,
            native_evb_schema
        )

        return (
            post_transform(native_table) if post_transform 
            else native_table
        )

    def _native_data_format(self) -> str | None:
        return None

    def _compact_data_format(self) -> str | None:
        return None
