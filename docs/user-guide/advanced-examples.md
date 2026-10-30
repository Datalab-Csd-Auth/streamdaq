# :rocket: Advanced Examples

Complete examples that combine several features.

## Grouping by several columns

[`groupby_column`](window-checks.md#grouping) takes a single column. To check each combination of several columns separately, for example each unit **of each plant**, add a column that combines them, and group by that column.

This task checks every plant and unit separately, in 1-minute windows, waiting 5 seconds for late readings:

=== "Python"

    ```py
    import pathway as pw

    from streamdaq.checks import WindowDataQualityCheck
    from streamdaq.measures import Count, Mean, StandardDeviation
    from streamdaq.sessions import Session
    from streamdaq.tasks import Task


    class Reading(pw.Schema):
        timestamp: int  # epoch milliseconds
        plant: str
        unit_id: str
        temperature: float


    def _group_key(*values: str | None) -> tuple[str | None, ...]:
        return tuple(values)


    def read_stream() -> pw.Table:
        readings = pw.io.jsonlines.read("readings.jsonl", schema=Reading, mode="streaming")
        # One column combining the plant and the unit, e.g. ("P001", "012332")
        group = pw.apply_with_type(_group_key, tuple[str | None, ...], readings.plant, readings.unit_id)
        return readings.with_columns(group=group)


    task = Task(
        name="per_plant_and_unit",
        input=read_stream,
        output=pw.io.jsonlines.write,
        output_kwargs={"filename": "quality.jsonl"},
        windowby_column="timestamp",
        groupby_column="group",
        wait_for_late=5_000,
    )
    task.add_window_checks(
        WindowDataQualityCheck("reading_count", Count("temperature")),
        WindowDataQualityCheck("enough_readings", Count("temperature"), ">= 6"),
        WindowDataQualityCheck("mean_temperature", Mean("temperature", precision=1)),
        WindowDataQualityCheck("stable_temperature", StandardDeviation("temperature"), "<= 2"),
        window=pw.temporal.tumbling(duration=60_000),
    )

    if __name__ == "__main__":
        Session(tasks=[task]).start()
    ```

=== "REST API (EVB data)"

    Over the REST API, the combined column is added by a [custom source](custom-code.md#sources). This one reads [EVB data](compact-data.md) from MQTT and combines the tags listed in `group_by_tags`:

    ```py title="evb_group_by_tags.py"
    import pathway as pw

    from streamdaq.custom import source
    from streamdaq.io.utils import ensure_unique_mqtt_client_id
    from streamdaq.schema.evb.definitions import EVBSchema


    def _group_key(*tag_values: str | None) -> tuple[str | None, ...]:
        return tuple(tag_values)


    @source(name="mqtt_evb_grouped", data_format="compact")
    def mqtt_evb_grouped(uri: str, topic: str, group_by_tags: list[str]):
        uri = ensure_unique_mqtt_client_id(uri)
        raw_table = pw.io.mqtt.read(uri=uri, topic=topic, format="json", schema=EVBSchema)

        def post_transform(native_table: pw.Table) -> pw.Table:
            # Tags can be missing from a message, so their columns may hold None
            tag_columns = [native_table[tag] for tag in group_by_tags]
            group = pw.apply_with_type(_group_key, tuple[str | None, ...], *tag_columns)
            return native_table.with_columns(group=group)

        return raw_table, post_transform
    ```

    Start the server with it loaded, `streamdaq serve --files evb_group_by_tags.py`, and send:

    ```json
    [{
      "name": "per_plant_and_unit",
      "input": {
        "type": "mqtt_evb_grouped",
        "params": {
          "connector_params": {
            "uri": "mqtt://127.0.0.1:1883",
            "topic": "evb/data",
            "group_by_tags": ["plant", "unit_id"]
          }
        }
      },
      "output": {"type": "jsonlines", "params": {"filename": "quality.jsonl"}},
      "wait_for_late": 5000,
      "window_checks_config": {
        "windowby_column": "time",
        "groupby_column": "group",
        "window": {"type": "tumbling", "params": {"duration": 60000}},
        "checks": [
          {"name": "reading_count", "measure": {"type": "Count", "params": {"column": "time"}}},
          {"name": "enough_readings", "measure": {"type": "Count", "params": {"column": "time"}}, "must_be": ">= 6"}
        ]
      }
    }]
    ```

Each window result names its group, so you can tell the plants and units apart:

```json
{"window_start": 0, "window_end": 60000, "group": ["P001", "012332"], "reading_count": 12, "enough_readings": true, ...}
{"window_start": 0, "window_end": 60000, "group": ["P001", "012385"], "reading_count": 4, "enough_readings": false, ...}
```

A value missing from a row, such as an EVB message without a `unit_id` tag, shows as `null` in the group, and forms a group of its own.
