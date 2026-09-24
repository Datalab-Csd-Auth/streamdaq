from collections.abc import Callable
from typing import Any

import pathway as pw

from streamdaq.io.sources.base import BaseSource
from streamdaq.io.utils import DataFormat
from streamdaq.schema.evb import discover_native_evb_schema
from streamdaq.schema.evb.wrangling import convert_raw_evb_to_native_format
from streamdaq.utils.picklable import Lambda


class CustomSource(BaseSource):
    """A user-defined source registered via the ``@source`` decorator.

    ``read_raw`` is supplied by the user factory rather than a built-in connector: a native
    factory returns a ``pw.Table``; a compact factory returns a ``(raw_table, post_transform)``
    tuple, which streamdaq sniffs, converts to native form and post-transforms.
    """

    def __init__(self, factory: Callable[..., Any], data_format: str, connector_params: dict):
        self.factory = factory
        self.data_type = data_format
        self.connector_params = connector_params
        self.files_path: str | None = None

    def __call__(self, **kwargs) -> pw.Table:
        result = self.factory(**self.connector_params)

        if self.data_type == DataFormat.NATIVE:
            if not isinstance(result, pw.Table):
                raise TypeError(
                    f"A native custom source must return a `pw.Table`, got {type(result).__name__}."
                )
            return result

        if not (isinstance(result, tuple) and len(result) == 2 and callable(result[1])):
            raise TypeError(
                "A compact custom source must return a `(pw.Table, post_transform)` tuple."
            )
        raw_table, post_transform = result

        native_evb_schema = discover_native_evb_schema(
            get_table_function=Lambda(lambda: self.factory(**self.connector_params)[0]),
            timeout_seconds=20,
            files_path=self.files_path,
        )
        native_table = convert_raw_evb_to_native_format(raw_table, native_evb_schema)
        return post_transform(native_table)


def build_custom_input(factory: Callable[..., Any], data_format: str) -> Callable[[dict], Any]:
    """Builds the param-taking source factory that the engine invokes for a custom source."""

    def build(params: dict[str, Any]) -> CustomSource:
        if "connector_params" in params:
            connector_params = params["connector_params"]
        else:
            connector_params = {k: v for k, v in params.items() if k != "data_format"}
        return CustomSource(factory, data_format, connector_params)

    return build
