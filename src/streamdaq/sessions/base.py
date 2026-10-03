import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Self

import lmdb

from streamdaq.api.engine import build_task
from streamdaq.api.models import TaskConfig, TaskStatus
from streamdaq.storage.lmdb_store import NamespaceStore
from streamdaq.tasks.base import Task


@dataclass
class Session:
    tasks: list[Task] = field(default_factory=lambda: [])
    name: str | None = None
    files_path: str | None = None
    root_path: str = "./"
    clear: bool = False

    def __post_init__(self):
        # Use lmdb as an embedded, in-process store.
        # A streamdaq session spawns a db,
        # which is used to store the state of the session and its tasks.
        self.root_path = Path(self.root_path).resolve()
        db_path = str(self.root_path / ".streamdaq_db")
        if self.clear and os.path.exists(db_path):
            shutil.rmtree(db_path)
        os.makedirs(db_path, exist_ok=True)
        self.db = lmdb.open(db_path)

    def add_tasks(self, *tasks: Task) -> Self:
        for task in tasks:
            self.tasks.append(task)
        return self

    def restore_tasks(self) -> Self:
        """Re-materialize tasks that a previous session left running, from the persisted store.

        Only tasks persisted as ``RUNNING`` are resumed; finished or errored ones stay in the
        store untouched. Any ``--files`` custom code must already be loaded so their
        configurations can be rebuilt.
        """

        store: NamespaceStore = NamespaceStore(self.db, "api_tasks", value_type=TaskConfig)
        existing = {task.name for task in self.tasks}
        for _, config in store.items():
            if config.status != TaskStatus.RUNNING or config.name in existing:
                continue
            try:
                self.add_tasks(build_task(config))
            except Exception as error:
                # A single unrebuildable config must not stop the whole session from starting
                print(f"⚠️  Skipping resume of task '{config.name}': {error}")
        return self

    def start(self) -> Self:
        for task in self.tasks:
            # start each task as a separate process - the current (main) process remains unblocked
            task.files_path = self.files_path
            if task._pw_process is None or not task._pw_process.is_alive():
                task._start_pw_process()
        return self

    def tasks_store(self) -> NamespaceStore:
        """The persistent store of task configurations owned by this session."""
        return NamespaceStore(self.db, "api_tasks", value_type=TaskConfig)

    def sync_task_statuses(self) -> None:
        """Reconcile persisted RUNNING statuses with the actual liveness of their processes."""
        store = self.tasks_store()
        for task_id, config in store.items():
            if config.status != TaskStatus.RUNNING:
                continue
            for task in self.tasks:
                if task.name == config.name:
                    if task._pw_process is not None and not task._pw_process.is_alive():
                        config.status = TaskStatus.FINISHED
                        store[task_id] = config
                    break

    def _has_running_tasks(self) -> bool:
        return any(
            task._pw_process is not None and task._pw_process.is_alive() for task in self.tasks
        )

    def gracefully_kill(self, timeout_seconds: int) -> None:
        for task in self.tasks:
            task.gracefully_kill(timeout_seconds)
