from dataclasses import dataclass, field
from typing import Self

import pathway as pw

from streamdaq.tasks.base import Task


@dataclass
class Session:
    tasks: list[Task] = field(default_factory=lambda: [])
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
            task._start_pw_process()
        return self
