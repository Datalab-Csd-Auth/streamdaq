from typing import Any

from fastapi import APIRouter, HTTPException, status

from streamdaq.api.engine import build_task
from streamdaq.api.models import (
    SessionStatus,
    TaskConfig,
    TaskStatus,
)
from streamdaq.utils.api import (
    _get_session,
    _get_tasks_store,
    _handle_running_task,
    _sync_task_statuses,
    _validate_for_start,
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
    """Retrieve details and configuration for a specific task by its ID."""
    _sync_task_statuses()
    if task_id not in _get_tasks_store():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Task with id {task_id} not found."
        )
    return _get_tasks_store()[task_id]


@router.post(
    "/bulk_create",
    status_code=status.HTTP_201_CREATED,
    summary="Bulk Create and Start Tasks",
    tags=["Tasks"],
    response_description="Success message and list of created task IDs.",
    responses={
        422: {"description": "Task validation failed prior to execution."},
        503: {"description": "No active StreamDAQ session is currently mounted."},
        500: {"description": "Internal error occurred while starting the task process."},
    },
)
async def create_task(task_configs: list[TaskConfig]) -> dict[str, Any]:
    """Bulk create, validate, and immediately start multiple data quality tasks.

    Requires an active StreamDAQ session. Validates configurations for completeness before
    starting processes. If a task with the same name already exists, its configuration is
    updated dynamically instead of starting a new process.
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
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=errors)

    task_ids = []
    for task_config in task_configs:
        task_id = task_config.name

        if task_id in _get_tasks_store():
            _handle_running_task(task_id, task_config)
            _get_tasks_store()[task_id] = task_config
            task_ids.append(task_id)
            continue

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


@router.put(
    "/tasks/{task_id}",
    summary="Edit Task",
    tags=["Tasks"],
    response_description="Success message and task ID.",
    responses={
        404: {"description": "Task not found."},
        422: {"description": "Task validation failed."},
    },
)
async def edit_task(task_id: str, task_config: TaskConfig) -> dict[str, str]:
    """Update the configuration of an existing task.

    If the task is currently running, the configuration change is applied dynamically.
    """
    if task_id not in _get_tasks_store():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Task with id '{task_id}' not found."
        )

    errors = _validate_for_start(task_config)
    if errors:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=errors)

    existing_config = _get_tasks_store()[task_id]
    task_config.status = existing_config.status
    _get_tasks_store()[task_id] = task_config

    if existing_config.status == TaskStatus.RUNNING:
        _handle_running_task(task_id, task_config)

    return {"message": "Task updated.", "task_id": task_id}


@router.get(
    "/config/options",
    summary="Get Configuration Options",
    tags=["Configuration"],
    response_description="Available registered inputs, outputs, windows, checks, and measures.",
)
async def get_config_options() -> dict[str, list[str]]:
    """Return available registered option names for inputs, outputs, windows, and checks."""
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
