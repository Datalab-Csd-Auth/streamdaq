# :hammer_and_wrench: Custom Code

When the built-in pieces aren't enough, you can add your own **measures**, **assessments**, **sources** and **sinks** with decorators from `streamdaq.custom`. Once registered, they can be used by name, including from the [REST API](rest-api.md).

## Measures

`@measure` turns a function into a measure for [window checks](window-checks.md). The function receives the window's values, one sequence per column, and returns the measured value:

```py
from typing import Any

from streamdaq.custom import measure


@measure(columns=["time", "measurement", "status"], name="MaxDropBetweenOkReadings", sort_by_column="time")
def max_drop_between_ok_readings(data: dict[str, Any]) -> float:
    """Largest drop in `measurement` between consecutive OK readings."""
    ok_values = [m for m, s in zip(data["measurement"], data["status"]) if s == "OK"]
    drops = [previous - current for previous, current in zip(ok_values, ok_values[1:])]
    return max(drops) if drops else 0.0
```

| Setting | Meaning |
|---|---|
| `columns` | The columns the function needs. `data` has one entry per column. |
| `name` | The measure's name; defaults to the function's name. Used in API payloads. |
| `sort_by_column` | If set, all columns are sorted together by this column, e.g. time. |
| `desc` | Sort in descending order (default `False`). |

`@measure` turns the function into a measure **class**. Create it **without arguments**:

```py
WindowDataQualityCheck("max_drop", max_drop_between_ok_readings(), "<= 5")
```

In an API payload, use its name with empty `params`: `"measure": {"type": "MaxDropBetweenOkReadings", "params": {}}`.

## Assessments

`@assessment` registers a function as a named [assessment](assessments.md):

```py
from streamdaq.custom import assessment


@assessment(name="IsWithinTolerance")
def is_within_tolerance(value: float) -> bool:
    return abs(value) <= 5 or value > 100
```

Use it with `must_be="IsWithinTolerance"`, in Python or in an API payload.

## Sources

`@source` registers a function that creates the input table. Its keyword arguments come from the payload's `connector_params`.

=== "Native data"

    The function returns a `pw.Table`:

    ```py
    import pathway as pw

    from streamdaq.custom import source


    class Reading(pw.Schema):
        timestamp: int
        temperature: float


    @source(name="readings_from_kafka")
    def readings_from_kafka(bootstrap_servers: str, topic: str):
        return pw.io.kafka.read(
            rdkafka_settings={"bootstrap.servers": bootstrap_servers, "group.id": "streamdaq"},
            topic=topic,
            format="json",
            schema=Reading,
        )
    ```

=== "Compact (EVB) data"

    With `data_format="compact"`, the function returns the raw EVB table **and** a function that Stream DaQ applies after converting the data to rows and columns:

    ```py
    import pathway as pw

    from streamdaq.custom import source
    from streamdaq.io.utils import ensure_unique_mqtt_client_id
    from streamdaq.schema.evb.definitions import EVBSchema


    @source(name="my_evb_source", data_format="compact")
    def my_evb_source(uri: str, topic: str):
        raw_table = pw.io.mqtt.read(
            uri=ensure_unique_mqtt_client_id(uri), topic=topic, format="json", schema=EVBSchema
        )

        def post_transform(native_table: pw.Table) -> pw.Table:
            return native_table.with_columns(source="my_evb_source")

        return raw_table, post_transform
    ```

    The schema is [discovered from the first message](compact-data.md#schema-discovery), which calls your function once more.

```json title="Using a custom source in a payload"
"input": {"type": "readings_from_kafka", "params": {"connector_params": {"bootstrap_servers": "localhost:9092", "topic": "readings"}}}
```

## Sinks

`@sink` registers a function that writes a result table. It receives the table and the payload's output `params`:

```py
import pathway as pw

from streamdaq.custom import sink


@sink(name="jsonlines_with_source")
def jsonlines_with_source(table: pw.Table, **params) -> None:
    pw.io.jsonlines.write(table.with_columns(source="streamdaq"), **params)
```

Per-window results are passed to the sink with `_window` added to `filename`, `topic_name`, `topic` or `table_name`, if one of them is in the params. See [Where results go](inputs-and-outputs.md#where-results-go).

## Loading custom code

Custom code has to be loaded **before** tasks use it, and in **every task process**:

- **With the server:** `streamdaq serve --files my_code.py`. `--files` can be a file or a folder; for a folder, every `.py` file in it is loaded (not subfolders), except files whose names start with `_`.
- **In Python:** import your module before creating tasks, and give the same path to the session, so the task processes load it too: `Session(tasks=[...], files_path="my_code.py")`.

`GET /api/v1/config/options` lists everything registered, so you can check that your code was loaded.

A complete example with all four decorators is in [`examples/custom-code/my_streamdaq.py`](https://github.com/Datalab-Csd-Auth/streamdaq/blob/main/examples/custom-code/my_streamdaq.py).
