from dataclasses import dataclass, field
from typing import Self

import pathway as pw

from streamdaq.tasks.base import Task
from streamdaq.utils.picklable import Lambda


@dataclass
class Session:
    tasks: list[Task] = field(default_factory=Lambda(lambda: []))
    name: str | None = None

    def __post_init__(self):
        self.task_to_tables_map: dict[Task, list[pw.Table]] | None = None

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

    def serve_api(self, host: str = "127.0.0.1", port: int = 8000) -> None:
        import uvicorn

        from streamdaq.api.app import app, set_active_session

        # Start the already added tasks (if any)
        self.start()

        # Mount this session to the API
        set_active_session(self)

        # Block the main thread and run the API
        # TODO: Create a process to run the api and not block the main thread
        uvicorn.run(app, host=host, port=port)
