import time
import uuid
from typing import Dict

from fastapi import APIRouter, HTTPException, status

from streamdaq.api.engine import build_task
from streamdaq.api.models import SessionStatus, TaskConfig


router = APIRouter(prefix="/api/v1")

_TASKS_STORE: Dict[str, TaskConfig] = {}

# We need a lazy import to avoid circular dependency
def _get_session():
    from streamdaq.api.app import get_active_session
    return get_active_session()

@router.get("/session", response_model=SessionStatus)
async def get_session() -> SessionStatus:
    session = _get_session()
    status_str = "running" if session else "stopped"
    active_tasks = len(session.tasks) if session else 0
    
    return SessionStatus(
        status=status_str,
        active_tasks_count=active_tasks,
        version="1.0.0"
    )

@router.get("/tasks", response_model=Dict[str, TaskConfig])
async def list_tasks() -> Dict[str, TaskConfig]:
    return _TASKS_STORE

@router.get("/tasks/{task_id}", response_model=TaskConfig)
async def get_task(task_id: str) -> TaskConfig:
    if task_id not in _TASKS_STORE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Task with id {task_id} not found."
        )
    return _TASKS_STORE[task_id]

@router.post("/create_tasks", status_code=status.HTTP_201_CREATED)
async def create_task(task_config: TaskConfig) -> Dict[str, str]:
    session = _get_session()
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No active StreamDAQ session is currently mounted."
        )

    task_id = task_config.name
    
    if task_id in _TASKS_STORE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Task with name '{task_id}' already exists."
        )

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
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Task with id {task_id} not found."
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
