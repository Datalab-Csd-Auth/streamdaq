from typing import Any

from fastapi import HTTPException, status


def _get_session():
    """Lazy import to avoid circular dependency with ``app``."""
    from streamdaq.api.app import get_active_session

    return get_active_session()


def _get_tasks_store():
    """
    Retrieves the Redis tasks store scoped to the currently active session.
    Because the API relies entirely on the Session, we no longer need global
    state or separate DB instances. The session owns the DB, and we just
    wrap it here with a NamespaceStore to safely serialize TaskConfigs.
    """
    from streamdaq.api.models import TaskConfig
    from streamdaq.storage.lmdb_store import NamespaceStore

    session = _get_session()
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No active StreamDAQ session is currently mounted.",
        )
    return NamespaceStore(session.db, "api_tasks", value_type=TaskConfig)


def _sync_task_statuses():
    from streamdaq.api.models import TaskStatus

    session = _get_session()
    if session is None:
        return
    for task_id, config in _get_tasks_store().items():
        if config.status == TaskStatus.RUNNING:
            for task in session.tasks:
                if task.name == config.name:
                    if task._pw_process is not None and not task._pw_process.is_alive():
                        config.status = TaskStatus.FINISHED
                        _get_tasks_store()[task_id] = config
                    break


def _handle_running_task(task_id: str, config: Any) -> None:
    """Placeholder for dynamically applying a configuration change to a running task."""
    pass


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
