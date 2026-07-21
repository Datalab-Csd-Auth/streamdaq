from dataclasses import dataclass, field
from typing import Self

from streamdaq.tasks.base import Task
from streamdaq.utils.picklable import Lambda


@dataclass
class Session:
    tasks: list[Task] = field(default_factory=Lambda(lambda: []))
    name: str | None = None

    def __post_init__(self):
        import os
        import shutil

        import lmdb

        # Use lmdb as an embedded, in-process store.
        # A streamdaq session spawns a db,
        # which is used to store the state of the session and its tasks.
        db_path = ".streamdaq_db"
        if os.path.exists(db_path):
            shutil.rmtree(db_path)
        os.makedirs(db_path, exist_ok=True)
        self.db = lmdb.open(db_path)

    def add_tasks(self, *tasks: Task) -> Self:
        for task in tasks:
            self.tasks.append(task)
        return self

    def start(self) -> Self:
        for task in self.tasks:
            # start each task as a separate process - the current (main) process remains unblocked
            if task._pw_process is None or not task._pw_process.is_alive():
                task._start_pw_process()
        return self

    def serve_api(self, host: str = "127.0.0.1", port: int = 8000, **kwargs) -> None:
        import uvicorn

        from streamdaq.api.app import app, set_active_session

        # Start the already added tasks (if any)
        self.start()

        # Mount this session to the API
        # Mounting is needed so the API can interact with the currently running streamdaq engine
        set_active_session(self)

        # Block the main thread and run the API
        # TODO: Create a process to run the api and not block the main thread
        uvicorn.run(app, host=host, port=port, **kwargs)
