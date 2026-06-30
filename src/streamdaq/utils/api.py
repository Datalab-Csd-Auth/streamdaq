import importlib
from typing import Any

import pathway as pw
from fastapi import HTTPException, status

_DTYPE_MAP: dict[str, type] = {
    "int": int,
    "float": float,
    "str": str,
    "bool": bool,
    "bytes": bytes,
}


class _ConnectorInputCallable:
    def __init__(self, cls, schema, connector_params):
        self.cls = cls
        self.schema = schema
        self.connector_params = connector_params

    def __call__(self, **kwargs) -> pw.Table:
        subject = self.cls(**self.connector_params)
        return pw.io.python.read(subject, schema=self.schema)


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

    # Build Pathway schema from the type-string mapping
    columns = {
        col: pw.column_definition(dtype=_DTYPE_MAP[dtype_str])
        for col, dtype_str in params["schema"].items()
    }
    schema = pw.schema_builder(columns)
    connector_params: dict = params.get("connector_params", {})

    return _ConnectorInputCallable(cls, schema, connector_params)


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
