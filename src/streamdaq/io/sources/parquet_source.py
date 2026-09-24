from typing import ClassVar

import pandas as pd
import pathway as pw

from streamdaq.io.sources.base import BaseSource


class ParquetSource(BaseSource):
    source_type: ClassVar[str] = "parquet"
    supports_compact: ClassVar[bool] = False
    reserved_param_keys: ClassVar[tuple[str, ...]] = ("data_type", "schema", "path")

    def __init__(self, params: dict) -> None:
        super().__init__(params)
        self.path = params["path"]

    def read_raw(self, schema=None, data_format=None) -> pw.Table:
        return pw.debug.table_from_pandas(pd.read_parquet(self.path))
