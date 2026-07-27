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
    _get_tasks_store,
    _handle_running_task,
    _sync_task_statuses,
    _validate_for_start,
    update_task_config,
)

router = APIRouter(prefix="/api/v1")


# Session
@router.get(
    "/session",
    response_model=SessionStatus,
    summary="Get Session Status",
    tags=["Session"],
    response_description="Current status of the StreamDAQ engine session.",
)
async def get_session_status() -> SessionStatus:
    """Retrieve the status of the active StreamDAQ engine session.

    Returns the engine status ('running' or 'stopped'), the total number of currently
    active monitoring tasks, and the system API version.
    """
    session = _get_session()
    status_str = "running" if session else "stopped"
    active_tasks = len(session.tasks) if session else 0

    return SessionStatus(status=status_str, active_tasks_count=active_tasks, version="1.0.0")


# Task CRUD
@router.get(
    "/tasks",
    response_model=dict[str, TaskConfig],
    summary="List All Tasks",
    tags=["Tasks"],
    response_description="A mapping of task IDs to their current configurations.",
)
async def list_tasks() -> dict[str, TaskConfig]:
    """Retrieve all registered tasks and their current configuration states.

    Synchronizes task execution statuses before returning.
    """
    _sync_task_statuses()
    return {k: v for k, v in _get_tasks_store().items()}


@router.get(
    "/tasks/{task_id}",
    response_model=TaskConfig,
    summary="Get Task by ID",
    tags=["Tasks"],
    response_description="The task configuration for the requested task ID.",
    responses={
        404: {"description": "Task not found."},
    },
)
async def get_task(task_id: str) -> TaskConfig:
    """Retrieve details and configuration for a specific task by its ID.

    Used for incremental task building and monitoring.
    """
    _sync_task_statuses()
    if task_id not in _get_tasks_store():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Task with id {task_id} not found."
        )
    return _get_tasks_store()[task_id]


@router.get(
    "/tasks/{task_id}/monitoring",
    summary="Get Task Monitoring Output (Currently Disabled)",
    tags=["Monitoring"],
    response_description=("Currently disabled. Intended for real-time stream monitoring via a UI."),
    deprecated=True,
)
async def get_task_monitoring(
    task_id: str, table_type: str = "instant", lines: int = 50
) -> list[dict]:
    """Reads the latest monitored output logs for a specific task.

    Note:
        This endpoint is currently disabled. It is designed for incremental stream monitoring
        based on the UI interface.

    Args:
        task_id: Identifier of the target monitoring task.
        table_type: Type of monitoring output ('instant' or 'window'). Default is 'instant'.
        lines: Number of recent output lines to read. Default is 50.
    """
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


@router.post(
    "/bulk_create",
    status_code=status.HTTP_201_CREATED,
    summary="Bulk Create and Start Tasks",
    tags=["Tasks"],
    response_description="Success message and list of created task IDs.",
    responses={
        409: {"description": "Task with specified name already exists."},
        422: {"description": "Task validation failed prior to execution."},
        503: {"description": "No active StreamDAQ session is currently mounted."},
        500: {"description": "Internal error occurred while starting the task process."},
    },
)
async def create_task(task_configs: list[TaskConfig]) -> dict[str, Any]:
    """Bulk create, validate, and immediately start multiple data quality tasks.

    Requires an active StreamDAQ session. Validates configurations for completeness before
    starting processes.
    """
    session = _get_session()
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No active StreamDAQ session is currently mounted.",
        )

    for task_config in task_configs:
        errors = _validate_for_start(task_config)
        if errors:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=errors)

        task_id = task_config.name

        if task_id in _get_tasks_store():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Task with name '{task_id}' already exists.",
            )

    task_ids = []
    for task_config in task_configs:
        task_id = task_config.name
        task_config.status = TaskStatus.RUNNING
        _get_tasks_store()[task_id] = task_config

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


@router.delete(
    "/tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Task",
    tags=["Tasks"],
    response_description="Task removed successfully.",
    responses={
        404: {"description": "Task not found."},
    },
)
async def delete_task(task_id: str) -> None:
    """Terminate and delete a task by its ID.

    Used for task lifecycle management in incremental task building and monitoring.
    If the task process is running within an active session, it will be gracefully killed.
    """
    session = _get_session()

    if task_id not in _get_tasks_store():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Task with id {task_id} not found."
        )

    config = _get_tasks_store()[task_id]

    # Find the matching task in the session and terminate its process
    if session:
        from streamdaq.orchestration.utils import gracefully_kill

        for task in session.tasks:
            # We match by name since we don't have a task_id inside Task
            if task.name == config.name and task._pw_process:
                gracefully_kill(task._pw_process, timeout_seconds=5)
                session.tasks.remove(task)
                break

    del _get_tasks_store()[task_id]


# Draft task builder endpoints
@router.post(
    "/tasks/{task_id}/init",
    status_code=status.HTTP_201_CREATED,
    summary="Initialize or Update Draft Task",
    tags=["Draft Tasks"],
    response_description="Success message and task ID.",
    responses={
        400: {"description": "Attempted to modify immutable task parameters on running task."},
    },
)
async def create_or_update_task(task_id: str, body: TaskDynamicCreate) -> dict[str, str]:
    """Create a new draft task or dynamically update basic parameters on an existing task.

    This endpoint is used for incremental task building and monitoring. Immutable properties
    (such as `task_name`, `windowby_column`, and `window_type`) cannot be modified once a task
    has started running.
    """
    is_new = task_id not in _get_tasks_store()
    if is_new:
        config = TaskConfig(name=body.task_name, windowby_column=body.windowby_column)
        if body.window_type:
            from streamdaq.api.models import WindowConfig

            config.window_checks_config = WindowChecksConfig(
                window=WindowConfig(type=body.window_type, params={}), checks=[]
            )
        _get_tasks_store()[task_id] = config
    else:
        config = _get_tasks_store()[task_id]

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
        _get_tasks_store()[task_id] = config

    return {"message": "Task updated." if not is_new else "Draft task created.", "task_id": task_id}


@router.post(
    "/tasks/{task_id}/input",
    summary="Set Task Input Configuration",
    tags=["Draft Tasks"],
    response_description="Success message and task ID.",
)
async def set_input(task_id: str, input_config: InputConfig):
    """Set or replace the stream input source configuration (e.g. MQTT, CSV, Kafka) on a task.

    This endpoint is used as part of incremental task building and monitoring.
    """
    with update_task_config(task_id, _get_tasks_store()) as config:
        config.input = input_config
    return {"message": "Input configuration set.", "task_id": task_id}


@router.post(
    "/tasks/{task_id}/output",
    summary="Set Task Output Configuration",
    tags=["Draft Tasks"],
    response_description="Success message and task ID.",
)
async def set_output(task_id: str, output_config: OutputConfig):
    """Set or replace the output sink configuration on a task.

    This endpoint is used as part of incremental task building and monitoring.
    """
    with update_task_config(task_id, _get_tasks_store()) as config:
        config.output = output_config
    return {"message": "Output configuration set.", "task_id": task_id}


@router.post(
    "/tasks/{task_id}/instant-checks",
    summary="Add Instant Check to Task",
    tags=["Draft Tasks"],
    response_description="Success message indicating the check was appended.",
)
async def add_instant_check(task_id: str, check: InstantCheckConfig):
    """Append a per-row instant check to a task configuration.

    This endpoint is used as part of incremental task building and monitoring.
    """
    with update_task_config(task_id, _get_tasks_store()) as config:
        config.instant_checks.append(check)
    return {"message": f"Instant check '{check.name}' added.", "task_id": task_id}


@router.post(
    "/tasks/{task_id}/window-checks",
    summary="Add Window Checks to Task",
    tags=["Draft Tasks"],
    response_description="Success message indicating window checks were updated.",
)
async def add_window_checks(task_id: str, body: WindowChecksConfig):
    """Set or update the window specification and append window checks to a task.

    Replaces window timing/tumbling configuration and appends new checks to any existing ones.
    This endpoint is used as part of incremental task building and monitoring.
    """
    with update_task_config(task_id, _get_tasks_store()) as config:
        if config.window_checks_config is None:
            config.window_checks_config = body
        else:
            # Replace window config, append checks
            config.window_checks_config.window = body.window
            config.window_checks_config.checks.extend(body.checks)
    return {"message": "Window checks added.", "task_id": task_id}


@router.delete(
    "/tasks/{task_id}/instant-checks/{check_name}",
    status_code=status.HTTP_200_OK,
    summary="Remove Instant Check from Task",
    tags=["Draft Tasks"],
    response_description="Success message confirming check removal.",
    responses={
        404: {"description": "Instant check with specified name not found."},
    },
)
async def remove_instant_check(task_id: str, check_name: str):
    """Remove a specific instant check from a task by its name.

    This endpoint is used as part of incremental task building and monitoring.
    """
    with update_task_config(task_id, _get_tasks_store()) as config:
        original_count = len(config.instant_checks)
        config.instant_checks = [c for c in config.instant_checks if c.name != check_name]
        if len(config.instant_checks) == original_count:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Instant check '{check_name}' not found.",
            )
    return {"message": f"Instant check '{check_name}' removed.", "task_id": task_id}


@router.delete(
    "/tasks/{task_id}/window-checks/{check_name}",
    status_code=status.HTTP_200_OK,
    summary="Remove Window Check from Task",
    tags=["Draft Tasks"],
    response_description="Success message confirming window check removal.",
    responses={
        404: {"description": "Window check with specified name not found."},
    },
)
async def remove_window_check(task_id: str, check_name: str):
    """Remove a specific window check from a task by its name.

    This endpoint is used as part of incremental task building and monitoring.
    """
    with update_task_config(task_id, _get_tasks_store()) as config:
        if config.window_checks_config is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Window check '{check_name}' not found.",
            )
        original_count = len(config.window_checks_config.checks)
        config.window_checks_config.checks = [
            c for c in config.window_checks_config.checks if c.name != check_name
        ]
        if len(config.window_checks_config.checks) == original_count:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Window check '{check_name}' not found.",
            )
    return {"message": f"Window check '{check_name}' removed.", "task_id": task_id}


@router.delete(
    "/tasks/{task_id}/window-checks",
    status_code=status.HTTP_200_OK,
    summary="Remove All Window Checks from Task",
    tags=["Draft Tasks"],
    response_description="Success message confirming removal of all window checks.",
    responses={
        404: {"description": "No window checks configuration found on task."},
    },
)
async def remove_window_checks(task_id: str):
    """Clear all window checks and reset window configuration on a task.

    This endpoint is used as part of incremental task building and monitoring.
    """
    with update_task_config(task_id, _get_tasks_store()) as config:
        if config.window_checks_config is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Window checks not found."
            )
        config.window_checks_config = None
    return {"message": "Window checks removed.", "task_id": task_id}


@router.post(
    "/tasks/{task_id}/start",
    summary="Start or Restart Task",
    tags=["Tasks"],
    response_description="Status message indicating task was started or restarted.",
    responses={
        404: {"description": "Task not found."},
        422: {"description": "Task failed completeness validation prior to start."},
        503: {"description": "No active StreamDAQ session is currently mounted."},
    },
)
async def start_task(task_id: str) -> dict[str, str]:
    """Validate task configuration completeness and launch or restart the task process.

    Finalizes incremental task building and starts real-time task monitoring.
    """
    if task_id not in _get_tasks_store():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Task with id '{task_id}' not found."
        )
    config = _get_tasks_store()[task_id]

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
    _get_tasks_store()[task_id] = config

    return {"message": "Task started successfully.", "task_id": task_id}


@router.get(
    "/config/options",
    summary="Get Configuration Options",
    tags=["Configuration"],
    response_description="Available registered inputs, outputs, windows, checks, and measures.",
)
async def get_config_options() -> dict[str, list[str]]:
    """Return available option names for registered UI drop-down selectors."""
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
