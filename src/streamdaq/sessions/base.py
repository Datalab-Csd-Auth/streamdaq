import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Self

import lmdb

from streamdaq.api.engine import build_task
from streamdaq.api.models import TaskConfig, TaskMetadata, TaskStatus
from streamdaq.api.utils import SWAP_KILL_TIMEOUT_SECONDS
from streamdaq.storage.codecs.pydantic_codec import PydanticCodec
from streamdaq.storage.namespace_store import NamespaceStore
from streamdaq.tasks.base import Task


@dataclass
class Session:
    tasks: list[Task] = field(default_factory=list)
    name: str | None = None
    files_path: str | None = None
    root_path: str = "./"
    clear: bool = False

    def __post_init__(self):
        # transform the tasks to a registry structure: name -> task config
        self.tasks: dict[str, Task] = {task.name: task for task in self.tasks}

        # Use lmdb as an embedded, in-process store.
        # A streamdaq session spawns a db,
        # which is used to store the state of the session and its tasks.
        self.root_path = Path(self.root_path).resolve()
        db_path = str(self.root_path / ".streamdaq_db")
        if self.clear and os.path.exists(db_path):
            shutil.rmtree(db_path)
        os.makedirs(db_path, exist_ok=True)
        # ``max_dbs`` must cover every NamespaceStore sub-database (configs, metadata, ...).
        self.db = lmdb.open(db_path, max_dbs=16)

    def add_tasks(self, *tasks: Task) -> Self:
        for task in tasks:
            self.tasks[task.name] = task
        return self

    def restore_tasks(self) -> Self:
        """Re-materialize tasks that a previous session left running, from the persisted store.

        Only tasks persisted as ``RUNNING`` are resumed; finished or errored ones stay in the
        store untouched. Any ``--files`` custom code must already be loaded so their
        configurations can be rebuilt.
        """

        tasks_store = self.get_tasks_store()
        metadata_store = self.get_metadata_store()
        for name, config in tasks_store.items():
            if config.status != TaskStatus.RUNNING or name in self.tasks:
                continue
            version = metadata_store[name].version if name in metadata_store else 1
            try:
                self.add_tasks(
                    build_task(
                        config,
                        files_path=self.files_path,
                        watermark_path=self._get_watermark_path(name),
                        version=version,
                    )
                )
            except Exception as error:
                print(f"⚠️  Skipping resume of task '{name}': {error}")
        return self

    def start(self) -> Self:
        for task in self.tasks.values():
            task.files_path = self.files_path
            if task._pw_process is None or not task._pw_process.is_alive():
                task._start_pw_process()
        return self

    def get_tasks_store(self) -> NamespaceStore:
        """The persistent store of task configurations owned by this session."""
        return NamespaceStore(self.db, "api_tasks", PydanticCodec(TaskConfig))

    def get_metadata_store(self) -> NamespaceStore:
        """The persistent store of server-owned task metadata (version, start time)."""
        return NamespaceStore(self.db, "api_task_meta", PydanticCodec(TaskMetadata))

    def _get_watermark_path(self, task_name: str) -> str:
        """The task's watermark store path, reused across versions of the same task."""
        return str(self.root_path / ".internals" / "watermarks" / task_name)

    def delete_watermark_store(self, task_name: str) -> None:
        """Remove the task's watermark store."""
        watermark_path = Path(self._get_watermark_path(task_name))
        if watermark_path.exists():
            shutil.rmtree(watermark_path)

    def register_task(self, config: TaskConfig) -> Task:
        """Build, persist, and start a brand-new task."""
        config.status = TaskStatus.RUNNING
        version = 1
        task = build_task(
            config,
            files_path=self.files_path,
            watermark_path=self._get_watermark_path(config.name),
            version=version,
        )
        task._start_pw_process()

        self.tasks[config.name] = task
        self.get_tasks_store()[config.name] = config
        self.get_metadata_store()[config.name] = TaskMetadata(version=version)
        return task

    def hotswap_task(self, config: TaskConfig) -> Task:
        """Restart a running task by starting a new worker, then killing the old one."""
        name = config.name
        old_task = self.tasks.get(name)
        metadata_store = self.get_metadata_store()
        previous_version = metadata_store[name].version if name in metadata_store else 0
        version = previous_version + 1

        config.status = TaskStatus.RUNNING
        new_task = build_task(
            config,
            files_path=self.files_path,
            watermark_path=self._get_watermark_path(name),
            version=version,
        )
        new_task._start_pw_process()

        self.tasks[name] = new_task
        self.get_tasks_store()[name] = config
        metadata_store[name] = TaskMetadata(version=version)

        if old_task is not None:
            old_task.gracefully_kill(SWAP_KILL_TIMEOUT_SECONDS)
        return new_task

    def sync_task_statuses(self) -> None:
        """Reconcile persisted RUNNING statuses with the actual liveness of their processes."""
        store = self.get_tasks_store()
        for name, config in store.items():
            if config.status != TaskStatus.RUNNING:
                continue
            task = self.tasks.get(name)
            if task is None or task._pw_process is None:
                continue
            if not task._pw_process.is_alive():
                config.status = TaskStatus.FINISHED
                store[name] = config

    def _has_running_tasks(self) -> bool:
        return any(
            task._pw_process is not None and task._pw_process.is_alive()
            for task in self.tasks.values()
        )

    def gracefully_kill(self, timeout_seconds: int) -> None:
        for task in self.tasks.values():
            task.gracefully_kill(timeout_seconds)
