import functools
import importlib
from typing import Any

import pathway as pw
from fastapi import HTTPException, status

from streamdaq.utils.picklable import Lambda

_DTYPE_MAP: dict[str, type] = {
    "int": int,
    "float": float,
    "str": str,
    "bool": bool,
    "bytes": bytes,
}


class _ConnectorInputCallable:
    def __init__(self, cls, schema_params, connector_params):
        self.cls = cls
        self.schema_params = schema_params
        self.connector_params = connector_params

    def __call__(self, **kwargs) -> pw.Table:
        columns = {
            col: pw.column_definition(dtype=_DTYPE_MAP[dtype_str])
            for col, dtype_str in self.schema_params.items()
        }
        schema = pw.schema_builder(columns)
        subject = self.cls(**self.connector_params)
        return pw.io.python.read(subject, schema=schema)


def build_python_connector_input(params: dict[str, Any]):
    """Generic input factory that dynamically loads a ``ConnectorSubject``.

    Expected *params* keys:
        module (str):            Dotted import path  (e.g. ``"testing.mock_stream"``).
        class_name (str):        Class inside that module (e.g. ``"MockStreamSubject"``).
        schema (dict[str,str]):  Column name → type string (``"int"``, ``"float"``, …).
        connector_params (dict): Kwargs forwarded to the ConnectorSubject constructor.
    """
    mod = importlib.import_module(params["module"])
    cls = getattr(mod, params["class_name"])

    schema_params = params["schema"]
    connector_params: dict = params.get("connector_params", {})

    return _ConnectorInputCallable(cls, schema_params, connector_params)


class _EVBMockInputCallable:
    def __init__(self, schema_params, connector_params):
        self.schema_params = schema_params
        self.connector_params = connector_params

    def __call__(self, **kwargs) -> pw.Table:
        from streamdaq.schema.evb.definitions import EVBSchema
        from streamdaq.schema.evb.mock_generator import EVBMockStream
        from streamdaq.schema.evb.wrangling import convert_raw_evb_to_native_format

        # Construct EVBMockStream
        subject = EVBMockStream(**self.connector_params)

        # Read raw stream using EVBSchema
        raw_table = pw.io.python.read(subject, schema=EVBSchema)

        # Build native schema: tuple[tuple[str, type]]
        native_evb_schema = tuple(
            (col_name, _DTYPE_MAP[dtype_str]) for col_name, dtype_str in self.schema_params.items()
        )

        return convert_raw_evb_to_native_format(raw_table, native_evb_schema)


def build_evb_mock_input(params: dict[str, Any]):
    """Specific input factory for EVBMockStream."""
    schema_params = params.get("schema", {})
    connector_params = params.get("connector_params", {})
    return _EVBMockInputCallable(schema_params, connector_params)


class _MQTT_EVBInputCallable:
    def __init__(self, schema_params, connector_params):
        self.schema_params = schema_params
        self.connector_params = connector_params

    def __call__(self, **kwargs) -> pw.Table:
        import uuid

        from streamdaq.schema.evb.definitions import EVBSchema
        from streamdaq.schema.evb.wrangling import convert_raw_evb_to_native_format

        base_uri = self.connector_params.get("uri")
        topic = self.connector_params.get("topic")

        # Determine if we need to append with ? or &
        sep = "&" if "?" in base_uri else "?"

        def get_raw_mqtt_table():
            client_id = f"streamdaq_reader_{uuid.uuid4().hex[:8]}"
            full_uri = f"{base_uri}{sep}client_id={client_id}"
            return pw.io.mqtt.read(uri=full_uri, topic=topic, format="json", schema=EVBSchema)

        if not self.schema_params:
            from streamdaq.schema.evb import discover_native_evb_schema

            native_evb_schema = discover_native_evb_schema(
                get_table_function=get_raw_mqtt_table, timeout_seconds=20
            )
        else:
            native_evb_schema = tuple(
                (col_name, _DTYPE_MAP[dtype_str])
                for col_name, dtype_str in self.schema_params.items()
            )

        raw_table = get_raw_mqtt_table()
        return convert_raw_evb_to_native_format(raw_table, native_evb_schema)


def build_mqtt_evb_input(params: dict[str, Any]):
    """Specific input factory for parsing EVB over MQTT."""
    schema_params = params.get("schema", {})
    connector_params = params.get("connector_params", {})
    return _MQTT_EVBInputCallable(schema_params, connector_params)


def build_csv_input(params: dict[str, Any]):
    """Stream via ``pw.io.csv.read``; static via ``pw.io.fs.read``.

    Expected *params* keys:
        path (str):  Path to the CSV file or directory.
        mode (str):  ``"static"`` or ``"streaming"`` (default ``"streaming"``).
    """
    mode = params.get("mode", "streaming")
    clean = {k: v for k, v in params.items() if k != "mode"}
    if mode == "static":
        return functools.partial(pw.io.fs.read, format="csv", mode="static", **clean)
    return functools.partial(pw.io.csv.read, **clean)


def build_parquet_input(params: dict[str, Any]):
    """Read a parquet file via pandas and convert to a Pathway table.

    Pathway has no native parquet connector, so pandas is used as a bridge.
    The ``mode`` param is accepted for API consistency but parquet is always static.

    Expected *params* keys:
        path (str):  Path to the parquet file.
    """
    import pandas as pd

    path = params["path"]
    return Lambda(lambda: pw.debug.table_from_pandas(pd.read_parquet(path)))


# --- Route helper functions ---


def _get_session():
    """Lazy import to avoid circular dependency with ``app``."""
    from streamdaq.api.app import get_active_session

    return get_active_session()


def _restart_task_placeholder(task_id: str):
    """Placeholder for dropping the pathway process and starting over."""
    pass


def _get_task_for_update(task_id: str, tasks_store: dict) -> Any:
    """Retrieve a task config or raise 404."""
    if task_id not in tasks_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Task with id '{task_id}' not found."
        )
    return tasks_store[task_id]


def _handle_running_task(task_id: str, config: Any):
    """Handle tasks that are already running by restarting them."""
    from streamdaq.api.models import TaskStatus

    if config.status == TaskStatus.RUNNING:
        _restart_task_placeholder(task_id)


def _validate_for_start(config: Any) -> list[str]:
    """Return a list of reasons the task cannot be started yet."""
    errors = []
    if config.input is None:
        errors.append("Input configuration is required.")
    if config.output is None:
        errors.append("Output configuration is required.")
    if not config.windowby_column:
        errors.append("Windowby column is required.")
    if config.window_checks_config is None:
        errors.append("Window configuration is required.")

    has_instant = bool(config.instant_checks)
    has_window = bool(config.window_checks_config and config.window_checks_config.checks)
    if not has_instant and not has_window:
        errors.append("At least one instant check or window check is required.")

    return errors
