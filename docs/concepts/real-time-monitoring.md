# :stopwatch: Real-time Monitoring

Real-time data quality monitoring introduces challenges that do not appear in batch execution. The key is managing trade-offs explicitly.

## Key challenges

- **Late arrivals**: Events may arrive out of order due to network or processing delays.
- **Event time vs processing time**: Systems process data at one time while the event occurred at another.
- **Watermarks**: A strategy is required for deciding when to finalize results despite possible late data.
- **Backpressure**: Input may exceed current processing throughput.

## Stream DaQ approach

Stream DaQ windows the stream by **event time**: you choose the column that holds when each event happened
(`windowby_column`) and the window to group events by.

```py title="Event-time windows"
task = Task(
    input=input_source,
    output=output_sink,
    windowby_column="event_timestamp",
)
task.add_window_checks(
    WindowDataQualityCheck("count", Count("value"), "(5, 15]"),
    window=pw.temporal.tumbling(duration=30),
)
```

Each window produces its results **exactly once**, as soon as the event time in the stream passes the end of the
window. Records that arrive after that, for a window that has already been closed, are not counted in it.

## Trade-offs to consider

### Latency vs completeness

- Window results are emitted as soon as each window closes, so latency stays low and every window is reported once.
- Records that arrive too late for their window are left out, so out-of-order streams can under-count.

### Memory vs statistical stability

- Larger windows often improve statistical signal but need more memory.
- Smaller windows reduce memory but can produce noisier metrics.

## Recommended starting point

1. Use the column that records when each event happened as `windowby_column`, not the arrival time.
2. Measure your real arrival-delay distribution, to know how often records arrive after their window has closed.
3. Tune window sizes to your data frequency and operational SLAs.
4. Validate behavior under realistic traffic patterns.
