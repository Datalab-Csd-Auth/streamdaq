import time
from typing import Dict, List
import uuid

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from streamdaq.api.engine import engine
from streamdaq.api.models import SessionStatus, TaskConfig


router = APIRouter(prefix="/api/v1")

# In-memory store to simulate the engine state
# In a real implementation, this state might be synchronized with the Pathway engine manager.
_MOCK_START_TIME = time.time()
_TASKS_STORE: Dict[str, TaskConfig] = {}


@router.get("/session", response_model=SessionStatus)
async def get_session() -> SessionStatus:
    """
    Fetches the current status of the engine and summary metrics.
    """
    uptime = int(time.time() - _MOCK_START_TIME)
    return SessionStatus(
        status="running",
        active_tasks_count=len(_TASKS_STORE),
        uptime_seconds=uptime,
        version="1.0.0"
    )


@router.get("/tasks", response_model=Dict[str, TaskConfig])
async def list_tasks() -> Dict[str, TaskConfig]:
    """
    Returns a list of all currently configured tasks.
    """
    return _TASKS_STORE


@router.get("/tasks/{task_id}", response_model=TaskConfig)
async def get_task(task_id: str) -> TaskConfig:
    """
    Returns the configuration details of a specific task.
    """
    if task_id not in _TASKS_STORE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Task with id {task_id} not found."
        )
    return _TASKS_STORE[task_id]


@router.post("/tasks", status_code=status.HTTP_201_CREATED)
async def create_task(task: TaskConfig) -> Dict[str, str]:
    """
    Create a new task in the stream processing session.
    """
    task_id = str(uuid.uuid4())
    _TASKS_STORE[task_id] = task
    
    # Here, the dynamic engine re-compilation / hot-reload is triggered.
    engine.apply_tasks(list(_TASKS_STORE.values()))
    
    return {"message": "Task created successfully", "task_id": task_id}


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: str) -> None:
    """
    Removes a task from the active session.
    """
    if task_id not in _TASKS_STORE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Task with id {task_id} not found."
        )
    del _TASKS_STORE[task_id]
    
    # Trigger hot-reload on the backend.
    engine.apply_tasks(list(_TASKS_STORE.values()))
