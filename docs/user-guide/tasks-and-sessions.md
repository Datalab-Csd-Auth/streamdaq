# :gear: Tasks and Sessions

A **task** describes one monitoring job: where the data comes from, which checks to apply, and where the results go. A **session** runs tasks.

## A minimal task

```py title="A task with one per-row check and one per-window check"
import pathway as pw

from streamdaq.checks import InRange, WindowDataQualityCheck
from streamdaq.measures import Count
from streamdaq.sessions import Session
from streamdaq.tasks import Task


class Reading(pw.Schema):
    timestamp: int
    temperature: float


def read_stream() -> pw.Table:  # (1)!
    return pw.io.jsonlines.read("readings.jsonl", schema=Reading, mode="streaming")


task = Task(
    name="readings",
    input=read_stream,
    output=pw.io.jsonlines.write,  # (2)!
    output_kwargs={"filename": "quality.jsonl"},
    windowby_column="timestamp",
)
task.add_instant_checks(
    InRange(name="valid_temperature", column="temperature", low=-30, high=50),
)
task.add_window_checks(
    WindowDataQualityCheck("enough_readings", Count("temperature"), ">= 5"),
    window=pw.temporal.tumbling(duration=60),
)

if __name__ == "__main__":
    Session(tasks=[task]).start()
```

1. Any function that returns a Pathway table can be the input. See [Inputs and Outputs](inputs-and-outputs.md).
2. Any function that takes a `pw.Table` can be the output. The per-window results go to `quality_window.jsonl`, see [Where results go](inputs-and-outputs.md#where-results-go).

## Task settings

| Setting | Default | What it does |
|---|---|---|
| `name` | `None` | The task's name. **Required** when the task is added to a session. |
| `input` | required | A function returning a `pw.Table`, called as `input(**input_kwargs)`. |
| `output` | required | A function taking a `pw.Table`, called as `output(table, **output_kwargs)`. |
| `input_kwargs` / `output_kwargs` | `{}` | Keyword arguments passed to `input` / `output`. |
| `windowby_column` | `None` | The column holding **when each event happened**. Needed for window checks. |
| `groupby_column` | `None` | Gives each value of this column its own windows. See [Window Checks](window-checks.md#grouping). |
| `wait_for_late` | `None` | How long to keep a window open for late events. See [Window Checks](window-checks.md#late-data). |
| `include_window_bounds` | `True` | Adds `window_start` and `window_end` to every window result. |
| `include_streamdaq_metadata` | `True` | Adds a `_streamdaq_metadata` column, e.g. `{"task_name": "readings", "task_version": 1}`. |

Checks are added with:

- **`task.add_instant_checks(*checks)`**: checks applied to every row. See [Instant Checks](instant-checks.md).
- **`task.add_window_checks(*checks, window=...)`**: checks applied to each window of rows. The `window` applies to all window checks of the task. See [Window Checks](window-checks.md).

Both return the task, so the calls can be chained.

## Results

A task produces up to two result streams, both written to the task's `output`:

| Results | Contents |
|---|---|
| **Per-row** (instant checks) | every input column, plus one `True`/`False` column per instant check |
| **Per-window** (window checks) | `window_start`, `window_end`, the group (if any), one column per window check |

The per-window results go to a separate destination; see [Where results go](inputs-and-outputs.md#where-results-go).

## Sessions

A session runs tasks. Each task runs in **its own process**, so tasks don't slow each other down.

```py
session = Session(tasks=[task_a, task_b])
session.start()
```

| Setting | Default | What it does |
|---|---|---|
| `tasks` | `[]` | The tasks to run. More can be added with `session.add_tasks(...)`. |
| `root_path` | `"./"` | Folder where the session keeps its state (`.streamdaq_db/`, `.internals/`). |
| `clear` | `False` | Delete the stored state in `root_path` when the session starts. |
| `files_path` | `None` | A file or folder of [custom code](custom-code.md) to load in every task process. |

!!! info "Every task needs a unique name"
    Tasks are identified by their names, so `Session` and `add_tasks` reject a task without a name, or with a name already in the session.

### Starting and stopping

- **`session.start()`** starts every task that isn't running yet, and returns immediately.
- **`session.gracefully_kill(timeout_seconds)`** stops every task: it asks each process to stop, and kills it if it hasn't stopped after `timeout_seconds`.

Running tasks from a Jupyter notebook needs one extra step; see [Good to Know](good-to-know.md#jupyter-notebooks).

## Running tasks as a service

Instead of writing Python, you can run Stream DaQ as a server and send tasks to it as JSON:

```bash
streamdaq serve
```

See [REST API and CLI](rest-api.md). Tasks created this way are stored, can be changed while running, and are resumed after a restart; see [Hot-swapping and Persistence](hot-swapping.md).
