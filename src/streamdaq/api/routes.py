import json
import os
from typing import Any

from fastapi import APIRouter, HTTPException, status

from streamdaq.api.engine import build_task
from streamdaq.api.models import (
    InputConfig,
    InstantCheckConfig,
    OutputConfig,
    SessionStatus,
    TaskConfig,
    TaskDynamicCreate,
    TaskStatus,
    WindowChecksConfig,
)
from streamdaq.utils.api import (
    _get_session,
    _get_task_for_update,
    _handle_running_task,
    _validate_for_start,
)

router = APIRouter(prefix="/api/v1")

# TODO: Because session has its own (same) tasks list, we might not need this global store.
# But for now, we will keep it for simplicity.
_TASKS_STORE: dict[str, TaskConfig] = {}


# Session
@router.get("/session", response_model=SessionStatus)
async def get_session_status() -> SessionStatus:
    session = _get_session()
    status_str = "running" if session else "stopped"
    active_tasks = len(session.tasks) if session else 0

    return SessionStatus(status=status_str, active_tasks_count=active_tasks, version="1.0.0")


def _sync_task_statuses():
    session = _get_session()
    if session is None:
        return
    for task_id, config in _TASKS_STORE.items():
        if config.status == TaskStatus.RUNNING:
            for task in session.tasks:
                if task.name == config.name:
                    if task._pw_process is not None and not task._pw_process.is_alive():
                        config.status = TaskStatus.FINISHED
                    break


# Task CRUD
@router.get("/tasks", response_model=dict[str, TaskConfig])
async def list_tasks() -> dict[str, TaskConfig]:
    _sync_task_statuses()
    return _TASKS_STORE


@router.get("/tasks/{task_id}", response_model=TaskConfig)
async def get_task(task_id: str) -> TaskConfig:
    _sync_task_statuses()
    if task_id not in _TASKS_STORE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Task with id {task_id} not found."
        )
    return _TASKS_STORE[task_id]


@router.get("/tasks/{task_id}/monitoring")
async def get_task_monitoring(
    task_id: str, table_type: str = "instant", lines: int = 50
) -> list[dict]:
    """Reads the latest monitored output for a task."""
    filepath = f".streamdaq_monitoring/{task_id}_{table_type}.jsonl"
    if not os.path.exists(filepath):
        return []

    data = []
    with open(filepath) as f:
        all_lines = f.readlines()
        for line in all_lines[-lines:]:
            try:
                data.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return data


@router.post("/bulk_create", status_code=status.HTTP_201_CREATED)
async def create_task(task_configs: list[TaskConfig]) -> dict[str, Any]:
    session = _get_session()
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No active StreamDAQ session is currently mounted.",
        )

    # Since input/output are now optional on the model, enforce them here for
    # the all-in-one creation flow.
    for task_config in task_configs:
        errors = _validate_for_start(task_config)
        if errors:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=errors)

        task_id = task_config.name

        if task_id in _TASKS_STORE:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Task with name '{task_id}' already exists.",
            )

    task_ids = []
    for task_config in task_configs:
        task_id = task_config.name
        task_config.status = TaskStatus.RUNNING
        _TASKS_STORE[task_id] = task_config

        # Build the task
        task = build_task(task_config)

        # Add to the running session
        session.add_tasks(task)

        # Since the session is already active, we start the task's isolated process immediately
        try:
            task._start_pw_process()
        except Exception as e:
            import traceback

            traceback.print_exc()
            raise HTTPException(status_code=500, detail=str(e))

        task_ids.append(task_id)

    return {
        "message": f"{len(task_ids)} tasks created and started successfully",
        "task_ids": task_ids,
    }


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: str) -> None:
    session = _get_session()

    if task_id not in _TASKS_STORE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Task with id {task_id} not found."
        )

    config = _TASKS_STORE[task_id]

    # Find the matching task in the session and terminate its process
    if session:
        from streamdaq.orchestration.utils import gracefully_kill

        for task in session.tasks:
            # We match by name since we don't have a task_id inside Task
            if task.name == config.name and task._pw_process:
                gracefully_kill(task._pw_process, timeout_seconds=5)
                session.tasks.remove(task)
                break

    del _TASKS_STORE[task_id]


# Draft task builder endpoints
@router.post("/tasks/{task_id}/init", status_code=status.HTTP_201_CREATED)
async def create_or_update_task(task_id: str, body: TaskDynamicCreate) -> dict[str, str]:
    """Create or dynamically update a task."""
    is_new = task_id not in _TASKS_STORE
    if is_new:
        config = TaskConfig(name=body.task_name, windowby_column=body.windowby_column)
        if body.window_type:
            from streamdaq.api.models import WindowConfig

            config.window_checks_config = WindowChecksConfig(
                window=WindowConfig(type=body.window_type, params={}), checks=[]
            )
        _TASKS_STORE[task_id] = config
    else:
        config = _TASKS_STORE[task_id]

        if config.status == TaskStatus.DRAFT:
            config.name = body.task_name
            if body.windowby_column is not None:
                config.windowby_column = body.windowby_column
            if body.window_type is not None:
                if config.window_checks_config:
                    config.window_checks_config.window.type = body.window_type
                else:
                    from streamdaq.api.models import WindowConfig

                    config.window_checks_config = WindowChecksConfig(
                        window=WindowConfig(type=body.window_type, params={}), checks=[]
                    )
        else:
            if config.name != body.task_name:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Task name is immutable once started.",
                )

            if body.windowby_column is not None and config.windowby_column != body.windowby_column:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Windowby column is immutable once started.",
                )

            if body.window_type is not None:
                current_type = (
                    config.window_checks_config.window.type if config.window_checks_config else None
                )
                if current_type is not None and current_type != body.window_type:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Window type is immutable once started.",
                    )
                elif current_type is None:
                    from streamdaq.api.models import WindowConfig

                    config.window_checks_config = WindowChecksConfig(
                        window=WindowConfig(type=body.window_type, params={}), checks=[]
                    )

        _handle_running_task(task_id, config)

    return {"message": "Task updated." if not is_new else "Draft task created.", "task_id": task_id}


@router.post("/tasks/{task_id}/input")
async def set_input(task_id: str, input_config: InputConfig):
    """Set or replace the input configuration on a task."""
    config = _get_task_for_update(task_id, _TASKS_STORE)
    config.input = input_config
    _handle_running_task(task_id, config)
    return {"message": "Input configuration set.", "task_id": task_id}


@router.post("/tasks/{task_id}/output")
async def set_output(task_id: str, output_config: OutputConfig):
    """Set or replace the output configuration on a task."""
    config = _get_task_for_update(task_id, _TASKS_STORE)
    config.output = output_config
    _handle_running_task(task_id, config)
    return {"message": "Output configuration set.", "task_id": task_id}


@router.post("/tasks/{task_id}/instant-checks")
async def add_instant_check(task_id: str, check: InstantCheckConfig):
    """Append an instant check to a task."""
    config = _get_task_for_update(task_id, _TASKS_STORE)
    config.instant_checks.append(check)
    _handle_running_task(task_id, config)
    return {"message": f"Instant check '{check.name}' added.", "task_id": task_id}


@router.post("/tasks/{task_id}/window-checks")
async def add_window_checks(task_id: str, body: WindowChecksConfig):
    """Add window checks to a task.

    The window configuration is set (or replaced) and the checks are appended
    to any existing window checks.
    """
    config = _get_task_for_update(task_id, _TASKS_STORE)
    if config.window_checks_config is None:
        config.window_checks_config = body
    else:
        # Replace window config, append checks
        config.window_checks_config.window = body.window
        config.window_checks_config.checks.extend(body.checks)
    _handle_running_task(task_id, config)
    return {"message": "Window checks added.", "task_id": task_id}


@router.delete("/tasks/{task_id}/instant-checks/{check_name}", status_code=status.HTTP_200_OK)
async def remove_instant_check(task_id: str, check_name: str):
    """Remove an instant check from a task by name."""
    config = _get_task_for_update(task_id, _TASKS_STORE)
    original_count = len(config.instant_checks)
    config.instant_checks = [c for c in config.instant_checks if c.name != check_name]
    if len(config.instant_checks) == original_count:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Instant check '{check_name}' not found."
        )
    _handle_running_task(task_id, config)
    return {"message": f"Instant check '{check_name}' removed.", "task_id": task_id}


@router.delete("/tasks/{task_id}/window-checks/{check_name}", status_code=status.HTTP_200_OK)
async def remove_window_check(task_id: str, check_name: str):
    """Remove a window check from a task by name."""
    config = _get_task_for_update(task_id, _TASKS_STORE)
    if config.window_checks_config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Window check '{check_name}' not found."
        )
    original_count = len(config.window_checks_config.checks)
    config.window_checks_config.checks = [
        c for c in config.window_checks_config.checks if c.name != check_name
    ]
    if len(config.window_checks_config.checks) == original_count:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Window check '{check_name}' not found."
        )
    _handle_running_task(task_id, config)
    return {"message": f"Window check '{check_name}' removed.", "task_id": task_id}


@router.delete("/tasks/{task_id}/window-checks", status_code=status.HTTP_200_OK)
async def remove_window_checks(task_id: str):
    config = _get_task_for_update(task_id, _TASKS_STORE)
    if config.window_checks_config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Window checks not found."
        )
    config.window_checks_config = None
    _handle_running_task(task_id, config)
    return {"message": "Window checks removed.", "task_id": task_id}


@router.post("/tasks/{task_id}/start")
async def start_task(task_id: str) -> dict[str, str]:
    """Validate completeness and start a task."""
    config = _get_task_for_update(task_id, _TASKS_STORE)

    errors = _validate_for_start(config)
    if errors:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=errors)

    session = _get_session()
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No active StreamDAQ session is currently mounted.",
        )

    if config.status == TaskStatus.RUNNING:
        _handle_running_task(task_id, config)
        return {"message": "Task restarted successfully.", "task_id": task_id}

    task = build_task(config)
    session.add_tasks(task)
    task._start_pw_process()
    config.status = TaskStatus.RUNNING

    return {"message": "Task started successfully.", "task_id": task_id}


@router.get("/config/options")
async def get_config_options() -> dict[str, list[str]]:
    """Return available options for UI dropdowns."""
    from streamdaq.api.registries import (
        INPUT_REGISTRY,
        INSTANT_CHECK_REGISTRY,
        MEASURE_REGISTRY,
        OUTPUT_REGISTRY,
        WINDOW_REGISTRY,
    )

    return {
        "inputs": list(INPUT_REGISTRY.keys()),
        "outputs": list(OUTPUT_REGISTRY.keys()),
        "windows": list(WINDOW_REGISTRY.keys()),
        "instant_checks": list(INSTANT_CHECK_REGISTRY.keys()),
        "measures": list(MEASURE_REGISTRY.keys()),
    }
