from typing import TYPE_CHECKING, Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status

from streamdaq.__about__ import __version__
from streamdaq.api.engine import build_task
from streamdaq.api.models import APIHeartbeat, SessionStatus, TaskConfig, TaskStatus
from streamdaq.api.utils import API_PREFIX, _handle_running_task
from streamdaq.checks.registry import INSTANT_CHECK_REGISTRY
from streamdaq.io.sinks.registry import SINK_REGISTRY
from streamdaq.io.sources.registry import SOURCE_REGISTRY
from streamdaq.measures.registry import MEASURE_REGISTRY
from streamdaq.temporal.windows.registry import WINDOW_REGISTRY

if TYPE_CHECKING:
    from streamdaq.sessions.base import Session

router = APIRouter(prefix=API_PREFIX)


def get_session(request: Request) -> "Session":
    """Dependency that provides the single Session owned by the running API."""
    return request.app.state.session


# https://fastapi.tiangolo.com/reference/dependencies/?h=depends
SessionDependency = Annotated["Session", Depends(get_session)]


# API Heartbeat
@router.get(
    "/heartbeat",
    response_model=APIHeartbeat,
    summary="Get API status (heartbeat)",
    tags=["Heartbeat"],
    response_description="'OK' if the API is up and running, else no response.",
)
async def health_check() -> APIHeartbeat:
    return APIHeartbeat()


# Session
@router.get(
    "/session",
    response_model=SessionStatus,
    summary="Get Session Status",
    tags=["Session"],
    response_description="Current status of the StreamDAQ engine session.",
)
async def get_session_status(session: SessionDependency) -> SessionStatus:
    """Retrieve the status of the StreamDAQ engine session.

    Returns the engine status, the number of currently active monitoring tasks, and the API
    version.
    """
    return SessionStatus(
        status="running", active_tasks_count=len(session.tasks), version=__version__
    )


# Task CRUD
@router.get(
    "/tasks",
    response_model=dict[str, TaskConfig],
    summary="List All Tasks",
    tags=["Tasks"],
    response_description="A mapping of task IDs to their current configurations.",
)
async def list_tasks(session: SessionDependency) -> dict[str, TaskConfig]:
    """Retrieve all registered tasks and their current configuration states.

    Synchronizes task execution statuses before returning.
    """
    session.sync_task_statuses()
    return {k: v for k, v in session.tasks_store().items()}


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
async def get_task(task_id: str, session: SessionDependency) -> TaskConfig:
    """Retrieve details and configuration for a specific task by its ID."""
    session.sync_task_statuses()
    store = session.tasks_store()
    if task_id not in store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Task with id {task_id} not found."
        )
    return store[task_id]


@router.post(
    "/bulk_create",
    status_code=status.HTTP_201_CREATED,
    summary="Bulk Create and Start Tasks",
    tags=["Tasks"],
    response_description="Success message and list of created task IDs.",
    responses={
        422: {"description": "Task validation failed prior to execution."},
        500: {"description": "Internal error occurred while starting the task process."},
    },
)
async def create_tasks(
    task_configs: list[TaskConfig], session: SessionDependency
) -> dict[str, Any]:
    """Bulk create, validate, and immediately start multiple data quality tasks.
    Validates configurations for completeness before starting processes."""
    store = session.tasks_store()

    task_ids = []
    for task_config in task_configs:
        task_id = task_config.name

        if task_id in store:
            _handle_running_task(task_id, task_config)
            store[task_id] = task_config
            task_ids.append(task_id)
            continue

        task_config.status = TaskStatus.RUNNING
        store[task_id] = task_config

        # Build the task
        task = build_task(task_config)
        task.files_path = session.files_path

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
async def delete_task(task_id: str, session: SessionDependency) -> None:
    """Terminate and delete a task by its ID.

    If the task process is running, it will be gracefully killed.
    """
    store = session.tasks_store()
    if task_id not in store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Task with id {task_id} not found."
        )

    config = store[task_id]

    # Find the matching task in the session and terminate its process
    from streamdaq.orchestration.utils import gracefully_kill

    for task in session.tasks:
        # We match by name since we don't have a task_id inside Task
        if task.name == config.name and task._pw_process:
            gracefully_kill(task._pw_process, timeout_seconds=5)
            session.tasks.remove(task)
            break

    del store[task_id]


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
async def edit_task(
    task_id: str, task_config: TaskConfig, session: SessionDependency
) -> dict[str, str]:
    """Update the configuration of an existing task.

    If the task is currently running, the configuration change is applied dynamically.
    """
    store = session.tasks_store()
    if task_id not in store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Task with id '{task_id}' not found."
        )

    existing_config = store[task_id]
    task_config.status = existing_config.status
    store[task_id] = task_config

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
    return {
        "inputs": sorted(list(SOURCE_REGISTRY.keys())),
        "outputs": sorted(list(SINK_REGISTRY.keys())),
        "windows": sorted(list(WINDOW_REGISTRY.keys())),
        "instant_checks": sorted(list(INSTANT_CHECK_REGISTRY.keys())),
        "measures": sorted(list(MEASURE_REGISTRY.keys())),
    }
