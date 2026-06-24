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

router = APIRouter(prefix="/api/v1")

# TODO: Because session has its own (same) tasks list, we might not need this global store. But for now, we will keep it for simplicity.
_TASKS_STORE: dict[str, TaskConfig] = {}


# We need a lazy import to avoid circular dependency
def _get_session():
    from streamdaq.api.app import get_active_session

    return get_active_session()


def _restart_task_placeholder(task_id: str):
    """Placeholder for dropping the pathway process and starting over."""
    pass


def _get_task_for_update(task_id: str) -> TaskConfig:
    """Retrieve a task config."""
    if task_id not in _TASKS_STORE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Task with id '{task_id}' not found."
        )
    return _TASKS_STORE[task_id]


def _handle_running_task(task_id: str, config: TaskConfig):
    """Handle tasks that are already running by restarting them."""
    if config.status == TaskStatus.RUNNING:
        _restart_task_placeholder(task_id)


def _validate_for_start(config: TaskConfig) -> list[str]:
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


# ─── Session ────────────────────────────────────────────────────────────────


@router.get("/session", response_model=SessionStatus)
async def get_session() -> SessionStatus:
    session = _get_session()
    status_str = "running" if session else "stopped"
    active_tasks = len(session.tasks) if session else 0

    return SessionStatus(status=status_str, active_tasks_count=active_tasks, version="1.0.0")


# ─── Task CRUD ──────────────────────────────────────────────────────────────


@router.get("/tasks", response_model=dict[str, TaskConfig])
async def list_tasks() -> dict[str, TaskConfig]:
    return _TASKS_STORE


@router.get("/tasks/{task_id}", response_model=TaskConfig)
async def get_task(task_id: str) -> TaskConfig:
    if task_id not in _TASKS_STORE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Task with id {task_id} not found."
        )
    return _TASKS_STORE[task_id]


@router.post("/bulk_create", status_code=status.HTTP_201_CREATED)
async def create_task(task_config: TaskConfig) -> dict[str, str]:
    session = _get_session()
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No active StreamDAQ session is currently mounted.",
        )

    # Since input/output are now optional on the model, enforce them here for
    # the all-in-one creation flow.
    errors = _validate_for_start(task_config)
    if errors:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=errors)

    task_id = task_config.name

    if task_id in _TASKS_STORE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Task with name '{task_id}' already exists.",
        )

    task_config.status = TaskStatus.RUNNING
    _TASKS_STORE[task_id] = task_config

    # Build the task
    task = build_task(task_config)

    # Add to the running session
    session.add_tasks(task)

    # Since the session is already active, we start the task's isolated process immediately
    task._start_pw_process()

    return {"message": "Task created and started successfully", "task_id": task_id}


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
        for task in session.tasks:
            # We match by name since we don't have a task_id inside Task
            if task.name == config.name and task._pw_process:
                task._pw_process.terminate()
                task._pw_process.join()
                session.tasks.remove(task)
                break

    del _TASKS_STORE[task_id]


# ─── Draft task builder endpoints ───────────────────────────────────────────


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
    config = _get_task_for_update(task_id)
    config.input = input_config
    _handle_running_task(task_id, config)
    return {"message": "Input configuration set.", "task_id": task_id}


@router.post("/tasks/{task_id}/output")
async def set_output(task_id: str, output_config: OutputConfig):
    """Set or replace the output configuration on a task."""
    config = _get_task_for_update(task_id)
    config.output = output_config
    _handle_running_task(task_id, config)
    return {"message": "Output configuration set.", "task_id": task_id}


@router.post("/tasks/{task_id}/instant-checks")
async def add_instant_check(task_id: str, check: InstantCheckConfig):
    """Append an instant check to a task."""
    config = _get_task_for_update(task_id)
    config.instant_checks.append(check)
    _handle_running_task(task_id, config)
    return {"message": f"Instant check '{check.name}' added.", "task_id": task_id}


@router.post("/tasks/{task_id}/window-checks")
async def add_window_checks(task_id: str, body: WindowChecksConfig):
    """Add window checks to a task.

    The window configuration is set (or replaced) and the checks are appended
    to any existing window checks.
    """
    config = _get_task_for_update(task_id)
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
    config = _get_task_for_update(task_id)
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
    config = _get_task_for_update(task_id)
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


@router.post("/tasks/{task_id}/start")
async def start_task(task_id: str) -> dict[str, str]:
    """Validate completeness and start a task."""
    config = _get_task_for_update(task_id)

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
