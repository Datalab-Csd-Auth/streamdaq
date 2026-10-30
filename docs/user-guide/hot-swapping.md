# :arrows_counterclockwise: Hot-swapping and Persistence

Tasks created through the [REST API](rest-api.md) are **stored**: they survive server restarts, and can be **changed while running** without starting over.

## Changing a running task

Send the task again to `POST /api/v1/bulk_create`, with the **same name** and the new configuration. Stream DaQ then:

1. starts a new version of the task with the new configuration;
2. stops the old version, about a second later;
3. continues from where the old version stopped, using the task's [watermarks](#watermarks).

The response says `"<name> was hot-swapped"`. Each change increases the task's **version**, which appears in every result row:

```json
{"_streamdaq_metadata": {"task_name": "readings", "task_version": 2}, ...}
```

!!! note
    For about a second, both versions run at the same time and can both write results. Use `task_version` to tell their rows apart.

## Restarts

When `streamdaq serve` starts, it **resumes every task that was running** when the server stopped, from its watermarks. Tasks that had finished are kept in the store but not restarted. Use `--clear` to start from an empty store.

A task that can't be rebuilt, for example because its custom code wasn't loaded with `--files`, is skipped with a warning, and the other tasks still start.

## Watermarks

A task's watermarks record how far it got:

- **Instant watermark:** the latest event time processed by the instant checks. When the task resumes, rows **from** that time onwards are processed.
- **Window watermark:** the end of the latest window reported. When the task resumes, windows start **from** that point.

## What is stored where

Everything is stored under the server's `--root` folder:

| Path | Contents |
|---|---|
| `.streamdaq_db/` | Task configurations and versions. |
| `.internals/watermarks/<task name>/` | Each task's watermarks. |

- **Deleting a task** (`DELETE /api/v1/tasks/{name}`) removes its configuration and watermarks.
- **`--clear`** removes both folders.
