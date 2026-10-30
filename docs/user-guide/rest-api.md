# :globe_with_meridians: REST API and CLI

Stream DaQ can run as a service: you start a server, then create, inspect and remove monitoring tasks over HTTP, without writing Python.

## Starting the server

```bash
streamdaq serve
```

```text
🪡  Initialized a streamdaq API session with name 'streamdaq_api_session'.
🌱 The streamdaq root directory is set to '/home/me/project/' (reusing existing root)
🦆 Attempting to start streamdaq API on http://127.0.0.1:8080.
ℹ️  Visit http://127.0.0.1:8080/docs for API Swagger UI.
```

Open **`http://127.0.0.1:8080/docs`** for interactive API documentation, where you can also try every request.

| Option | Default | Meaning |
|---|---|---|
| `-H`, `--host` | `127.0.0.1` | Address to listen on. |
| `-P`, `--port` | `8080` | Port to listen on. |
| `-R`, `--root` | `./` | Folder for the server's stored state. Relative paths are resolved from the current folder. |
| `-C`, `--clear` | off | Start from scratch: delete the stored tasks and watermarks in `--root`. |
| `-F`, `--files` | none | A file or folder of [custom code](custom-code.md) to load. |
| `-S`, `--session` | `streamdaq_api_session` | A name for the session, shown at startup. |

On startup, the server **resumes the tasks that were running** when it last stopped (unless `--clear` is given). Press ++ctrl+c++ to stop it; running tasks are stopped too.

!!! tip "Use an absolute `--root` for services"
    Tasks are stored in `--root`. If you start the server from a different folder with a relative `--root`, it uses a different, empty store, and your earlier tasks seem to be gone. For services and containers, use an absolute path.

Check whether a server is running with:

```bash
streamdaq status            # same --host / --port options
```

## Endpoints

All endpoints start with `/api/v1`.

| Method | Path | What it does |
|---|---|---|
| `POST` | `/bulk_create` | Create tasks, or update running ones. |
| `GET` | `/tasks` | All stored tasks, by name. |
| `GET` | `/tasks/{name}` | One task's configuration. |
| `DELETE` | `/tasks/{name}` | Stop and remove a task. |
| `GET` | `/session` | Server status: number of tasks and Stream DaQ version. |
| `GET` | `/heartbeat` | `{"status": "OK", "service": "streamdaq"}` if the server is up. |
| `GET` | `/config/options` | Everything you can use in a task: sources, sinks, windows, instant checks and measures, including custom ones. |

### Creating and updating tasks

`POST /api/v1/bulk_create` takes a **list** of tasks. For each one:

- if **no task has that name** yet, it's created and started;
- if a task **with that name exists**, it's replaced by the new configuration while running. See [Hot-swapping](hot-swapping.md).

```bash
curl -X POST http://127.0.0.1:8080/api/v1/bulk_create \
  -H "Content-Type: application/json" \
  -d @tasks.json
```

```json title="Response"
{"message": "Successfully processed 1 task requests", "task_ids": ["readings"], "details": ["readings was created and started"]}
```

### Removing a task

`DELETE /api/v1/tasks/{name}` stops the task and removes its configuration and [watermarks](hot-swapping.md#watermarks). Its output files or topics are not touched.

### Task status

`GET /tasks` and `GET /tasks/{name}` include a `status`:

- **`running`:** the task's process is running.
- **`finished`:** the process has stopped, whether it completed normally or crashed.

## Task configuration

```json title="tasks.json"
[{
  "name": "readings",
  "input": {
    "type": "jsonlines",
    "params": {"path": "readings.jsonl", "schema": {"timestamp": "int", "unit_id": "str", "temperature": "float"}}
  },
  "output": {"type": "jsonlines", "params": {"filename": "quality.jsonl"}},
  "wait_for_late": 5,
  "instant_checks": [
    {"name": "valid_temperature", "check_class": "InRange", "params": {"column": "temperature", "low": -30, "high": 50}}
  ],
  "window_checks_config": {
    "windowby_column": "timestamp",
    "groupby_column": "unit_id",
    "window": {"type": "tumbling", "params": {"duration": 60}},
    "checks": [
      {"name": "enough_readings", "measure": {"type": "Count", "params": {"column": "temperature"}}, "must_be": ">= 5"},
      {"name": "mean_temperature", "measure": {"type": "Mean", "params": {"column": "temperature", "precision": 2}}}
    ]
  }
}]
```

### Task

| Field | Required | Meaning |
|---|---|---|
| `name` | yes | Unique name of the task. |
| `input` | yes | `{"type": ..., "params": {...}}`. See [Inputs and Outputs](inputs-and-outputs.md#sources). |
| `output` | yes | `{"type": ..., "params": {...}}`. See [Inputs and Outputs](inputs-and-outputs.md#sinks). |
| `instant_checks` | one of these two | List of [instant checks](instant-checks.md). |
| `window_checks_config` | one of these two | [Window checks](window-checks.md) and their window. |
| `wait_for_late` | no | How long to wait for [late data](window-checks.md#late-data), in time-column units. |
| `include_streamdaq_metadata` | no | Add `_streamdaq_metadata` to results (default `true`). |

### Instant check

| Field | Meaning |
|---|---|
| `name` | Name of the result column. |
| `check_class` | `InRange`, `InSet`, `Regex`, `Length`, `Value` or `InRowComparison`. |
| `params` | The check's parameters except `name`, e.g. `{"column": "temperature", "low": -30, "high": 50}`. |

### Window checks

| Field | Required | Meaning |
|---|---|---|
| `windowby_column` | yes | The column holding when each event happened. |
| `window` | yes | `{"type": "tumbling" \| "sliding" \| "session", "params": {...}}`, e.g. `{"duration": 60}` or `{"hop": 10, "duration": 60}`. |
| `checks` | yes | List of `{"name", "measure": {"type", "params"}, "must_be"}`. `must_be` is optional. |
| `groupby_column` | no | Separate windows per value of this column. See [Grouping](window-checks.md#grouping). |
| `include_window_bounds` | no | Add `window_start`/`window_end` (default `true`). |

Measure `params` are the measure's parameters, e.g. `{"column": "temperature"}`; see [Measures](measures.md).

### Validation

Requests are checked before any task starts. Common errors:

- an unknown `type`, `check_class` or measure, or invalid parameters for it;
- a `must_be` that is neither a [comparison or range](assessments.md) nor a registered assessment;
- `"Input configuration is required."` / `"Output configuration is required."`;
- `"At least one instant check or window check is required."`.
