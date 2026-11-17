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

    def __init__(
        self,
        factory: Callable[..., Any],
        params: dict[str, Any]
    ) -> None:
        super().__init__(params)
        self.factory = factory

    def read_raw(
        self,
        schema: type[pw.Schema] | None = None,
        data_format: str | None = None
    ) -> pw.Table | tuple[pw.Table, Callable[[pw.Table], pw.Table]]:
        return self.factory(**self.connector_params)

def build_custom_input(
    factory: Callable[..., Any],
    data_format: str
) -> Callable[[dict], CustomSource]:
    """Builds the param-taking source factory that the engine invokes for a custom source."""

    def build(params: dict[str, Any] | None) -> CustomSource:
        if params is None:
            params = {}

        return CustomSource(factory, params)

    return build
