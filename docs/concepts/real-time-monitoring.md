# :stopwatch: Real-time Monitoring

Real-time data quality monitoring introduces challenges that do not appear in batch execution. The key is managing trade-offs explicitly.

## Key challenges

- **Late arrivals**: Events may arrive out of order due to network or processing delays.
- **Event time vs processing time**: Systems process data at one time while the event occurred at another.
- **Watermarks**: A strategy is required for deciding when to finalize results despite possible late data.
- **Backpressure**: Input may exceed current processing throughput.

## Stream DaQ approach

Stream DaQ provides first-class controls for event-time semantics and late-data tolerance.

```py title="Late data tolerance"
daq.configure(
    wait_for_late=30,  # wait up to 30 seconds for late records
    time_column="event_timestamp",
)
```

## Trade-offs to consider

### Latency vs completeness

- Lower `wait_for_late` gives faster results but may miss late records.
- Higher `wait_for_late` improves completeness but increases result latency.

### Memory vs statistical stability

- Larger windows often improve statistical signal but need more memory.
- Smaller windows reduce memory but can produce noisier metrics.

## Recommended starting point

1. Start with conservative defaults (`wait_for_late=30` is a common baseline).
2. Measure your real arrival-delay distribution.
3. Tune window sizes to your data frequency and operational SLAs.
4. Validate behavior under realistic traffic patterns.
