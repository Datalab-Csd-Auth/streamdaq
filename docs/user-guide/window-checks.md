# :window: Window Checks

Window checks look at **groups of rows over time**. Stream DaQ cuts the stream into windows by event time, computes a **measure** over each window (a count, a mean, the number of distinct values...), and optionally **assesses** whether the result is good.

```py
import pathway as pw

from streamdaq.checks import WindowDataQualityCheck
from streamdaq.measures import Count, DistinctCount, Mean

task = Task(name="readings", input=read_stream, output=..., windowby_column="timestamp")
task.add_window_checks(
    WindowDataQualityCheck("enough_readings", Count("temperature"), ">= 5"),
    WindowDataQualityCheck("mean_temperature", Mean("temperature")),
    WindowDataQualityCheck("few_units", DistinctCount("unit_id"), "<= 10"),
    window=pw.temporal.tumbling(duration=60),
)
```

```json title="One per-window result"
{"window_start": 0, "window_end": 60, "enough_readings": true, "mean_temperature": 21.4, "few_units": true,
 "_streamdaq_metadata": {"task_name": "readings", "task_version": 1}, ...}
```

## Anatomy of a window check

```py
WindowDataQualityCheck(name, measure, must_be=None)
```

| Part | Meaning |
|---|---|
| `name` | The name of the result column. |
| `measure` | What to compute over each window, e.g. `Count("temperature")`. See [Measures](measures.md). |
| `must_be` | Optional. What a good value is, e.g. `">= 5"` or `"(5, 15]"`. See [Assessments](assessments.md). |

- **Without `must_be`**, the column holds the **measured value** (`"mean_temperature": 21.4`).
- **With `must_be`**, the column holds **only the result of the assessment** (`"enough_readings": true`). The measured value itself is not output.

!!! tip "Seeing the value and the verdict"
    To get both, add two checks with the same measure, one with `must_be` and one without:

    ```py
    WindowDataQualityCheck("reading_count", Count("temperature")),
    WindowDataQualityCheck("enough_readings", Count("temperature"), ">= 5"),
    ```

## Windows

Windows are given to `add_window_checks` with `window=`. All window checks of a task share the same window. The task's `windowby_column` tells Stream DaQ which column holds **when each event happened**; windows are based on that time, not on when rows arrive.

| Window | Created with | Use it for |
|---|---|---|
| **Tumbling** | `pw.temporal.tumbling(duration=60)` | Fixed, back-to-back windows: `[0, 60)`, `[60, 120)`, ... |
| **Sliding** | `pw.temporal.sliding(hop=10, duration=60)` | Overlapping windows: a 60-unit window starting every 10 units. Each row belongs to several windows. |
| **Session** | `pw.temporal.session(max_gap=30)` | Windows that follow bursts of activity: events less than `max_gap` apart go into the same window, and a gap longer than `max_gap` starts a new one. Windows can have any length. |

Durations are in the **same units as `windowby_column`**: plain numbers for numeric time columns (e.g. milliseconds for EVB data), or `datetime.timedelta` for datetime columns.

!!! info "When are window results reported?"
    Each window reports its results **exactly once**, as soon as the event time in the stream passes the end of the window (plus `wait_for_late`, see below).

## Window bounds

By default every window result starts with `window_start` and `window_end`, so you know which period it describes. Turn them off with `include_window_bounds=False` on the task.

## Grouping

By default each window covers **all** rows. With `groupby_column`, every value of that column gets **its own windows**, and every result row says which group it belongs to:

```py
task = Task(..., windowby_column="timestamp", groupby_column="unit_id")
```

```json
{"window_start": 0, "window_end": 60, "unit_id": "012332", "enough_readings": true, ...}
{"window_start": 0, "window_end": 60, "unit_id": "012385", "enough_readings": false, ...}
```

To group by several columns, combine them into one column first; see [Advanced Examples](advanced-examples.md#grouping-by-several-columns).

## Late data

Events don't always arrive in order. By default a window is closed as soon as event time reaches its end, and events for it that arrive later are **not counted**.

`wait_for_late` keeps each window open a little longer, in the units of `windowby_column`:

```py
task = Task(..., windowby_column="timestamp", wait_for_late=5)
```

With `wait_for_late=5`, the window `[0, 60)` is reported once event time reaches 65, and events with timestamps in `[0, 60)` arriving before that are still counted.

| `wait_for_late` | Results | Late events |
|---|---|---|
| `None` (default) | as soon as a window ends | dropped once the window has ended |
| higher | later | counted, if they arrive within the wait |

See [Real-time Monitoring](../concepts/real-time-monitoring.md) for the trade-offs.
