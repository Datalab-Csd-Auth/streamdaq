import functools
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


class _StreamingInputCallable:
    def __init__(
        self,
        connector_type: str,
        schema_params: dict,
        connector_params: dict,
        data_type: str,
        extra_params: dict | None = None,
    ):
        self.connector_type = connector_type
        self.schema_params = schema_params
        self.connector_params = connector_params
        self.data_type = data_type
        self.extra_params = extra_params or {}

    def __call__(self, **kwargs) -> pw.Table:
        from streamdaq.schema.evb.definitions import EVBSchema
        from streamdaq.schema.evb.wrangling import convert_raw_evb_to_native_format

        def get_raw_table(schema=None, format=None):
            import uuid

            params = dict(self.connector_params)

            if self.connector_type == "python_connector":
                import importlib

                mod = importlib.import_module(self.extra_params["module"])
                cls = getattr(mod, self.extra_params["class_name"])
                subject = cls(**params)
                if schema is not None:
                    return pw.io.python.read(subject, schema=schema)
                return pw.io.python.read(subject)

            if schema is not None:
                params["schema"] = schema
            if format is not None:
                params["format"] = format

            if self.connector_type == "mqtt":
                base_uri = params.get("uri", "")
                if "client_id=" not in base_uri:
                    sep = "&" if "?" in base_uri else "?"
                    client_id = f"streamdaq_reader_{uuid.uuid4().hex[:8]}"
                    params["uri"] = f"{base_uri}{sep}client_id={client_id}"
                return pw.io.mqtt.read(**params)

            elif self.connector_type == "kafka":
                if "group.id" not in params:
                    params["group.id"] = f"streamdaq_reader_{uuid.uuid4().hex[:8]}"
                return pw.io.kafka.read(**params)

            else:
                raise ValueError(f"Unknown connector_type: {self.connector_type}")

        if self.data_type == "native":
            columns = {
                col: pw.column_definition(dtype=_DTYPE_MAP[dtype_str])
                for col, dtype_str in self.schema_params.items()
            }
            schema = pw.schema_builder(columns) if columns else None

            format_type = None
            if self.connector_type in ("mqtt", "kafka"):
                format_type = self.connector_params.get("format", "json")

            return get_raw_table(schema=schema, format=format_type)

        elif self.data_type == "compact":
            format_type = "json" if self.connector_type in ("mqtt", "kafka") else None
            if not self.schema_params:
                from streamdaq.schema.evb import discover_native_evb_schema

                native_evb_schema = discover_native_evb_schema(
                    get_table_function=lambda: get_raw_table(schema=EVBSchema, format=format_type),
                    timeout_seconds=20,
                )
            else:
                native_evb_schema = tuple(
                    (col_name, _DTYPE_MAP[dtype_str])
                    for col_name, dtype_str in self.schema_params.items()
                )

            raw_table = get_raw_table(schema=EVBSchema, format=format_type)
            return convert_raw_evb_to_native_format(raw_table, native_evb_schema)

        else:
            raise ValueError(f"Unknown data_type: {self.data_type}")


def build_python_connector_input(params: dict[str, Any]):
    """Generic input factory that dynamically loads a ``ConnectorSubject``.

    Expected *params* keys:
        module (str):            Dotted import path  (e.g. ``"testing.mock_stream"``).
        class_name (str):        Class inside that module (e.g. ``"MockStreamSubject"``).
        schema (dict[str,str]):  Column name → type string (``"int"``, ``"float"``, …).
        connector_params (dict): Kwargs forwarded to the ConnectorSubject constructor.
        data_type (str):         "native" or "compact".
    """
    data_type = params.get("data_type", "native")
    schema_params = params.get("schema", {})

    if "connector_params" in params:
        connector_params = params["connector_params"]
    else:
        connector_params = {
            k: v
            for k, v in params.items()
            if k not in ("data_type", "schema", "module", "class_name")
        }

    extra_params = {
        "module": params["module"],
        "class_name": params["class_name"],
    }
    return _StreamingInputCallable(
        "python_connector", schema_params, connector_params, data_type, extra_params
    )


def build_mqtt_input(params: dict[str, Any]):
    """Specific input factory for reading from MQTT."""
    data_type = params.get("data_type", "native")
    schema_params = params.get("schema", {})

    if "connector_params" in params:
        connector_params = params["connector_params"]
    else:
        connector_params = {k: v for k, v in params.items() if k not in ("data_type", "schema")}

    return _StreamingInputCallable("mqtt", schema_params, connector_params, data_type)


def build_kafka_input(params: dict[str, Any]):
    """Specific input factory for reading from Kafka."""
    data_type = params.get("data_type", "native")
    schema_params = params.get("schema", {})

    if "connector_params" in params:
        connector_params = params["connector_params"]
    else:
        connector_params = {k: v for k, v in params.items() if k not in ("data_type", "schema")}

    return _StreamingInputCallable("kafka", schema_params, connector_params, data_type)


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
