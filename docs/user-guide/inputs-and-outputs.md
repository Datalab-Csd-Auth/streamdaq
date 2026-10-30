# :electric_plug: Inputs and Outputs

## In Python

In Python, a task's input and output are plain functions, so you can use any of [Pathway's connectors](https://pathway.com/developers/user-guide/connect/pathway-connectors) directly:

```py
import pathway as pw


class Reading(pw.Schema):
    timestamp: int
    unit_id: str
    temperature: float


def read_stream() -> pw.Table:
    return pw.io.kafka.read(
        rdkafka_settings={"bootstrap.servers": "localhost:9092", "group.id": "streamdaq"},
        topic="readings",
        format="json",
        schema=Reading,
    )


task = Task(
    name="readings",
    input=read_stream,
    output=pw.io.kafka.write,
    output_kwargs={"rdkafka_settings": {"bootstrap.servers": "localhost:9092"}, "topic_name": "quality"},
    windowby_column="timestamp",
)
```

- **Input:** any function returning a `pw.Table`. It's called as `input(**input_kwargs)`.
- **Output:** any function taking a `pw.Table`, called as `output(table, **output_kwargs)`. Window results go to a destination with `_window` added, see [Where results go](#where-results-go).

## In the REST API

Tasks sent to the [REST API](rest-api.md) pick a source and a sink by name, with their settings in `params`:

```json
"input": {
  "type": "jsonlines",
  "params": {"path": "readings.jsonl", "schema": {"timestamp": "int", "unit_id": "str", "temperature": "float"}}
},
"output": {"type": "jsonlines", "params": {"filename": "quality.jsonl"}}
```

`GET /api/v1/config/options` lists every source and sink available, including [custom ones](custom-code.md).

### Sources

| `type` | Reads | Compact data |
|---|---|---|
| `jsonlines` | JSON Lines files, with Pathway's `pw.io.jsonlines.read` | no |
| `mqtt` | An MQTT topic, with `pw.io.mqtt.read` | yes |
| `kafka` | A Kafka topic, with `pw.io.kafka.read` | yes |
| `python_connector` | A Pathway Python connector class from an importable module | yes |
| `parquet` | A Parquet file, read **once** (not streamed) | no |
| `csv` | CSV files, with `pw.io.csv.read` | no |

Settings shared by all sources:

| Setting | Meaning |
|---|---|
| `data_type` | `"native"` (default): one value per column. `"compact"`: [compact messages](compact-data.md), several measurements per message. |
| `schema` | The columns and their types, e.g. `{"timestamp": "int", "unit_id": "str"}`. Types: `"int"`, `"float"`, `"str"`, `"bool"`, `"bytes"`. Required for native JSON data. |
| `mode` | `jsonlines` and `csv` only: `"streaming"` (default, keeps watching for new data) or `"static"` (reads once). |
| `connector_params` | Settings passed to the Pathway reader as they are. If left out, every other setting (apart from those above) is passed instead. |

Source-specific settings:

- **`mqtt`:** `uri` (e.g. `"mqtt://127.0.0.1:1883"`) and `topic`. A unique `client_id` is added to the URI automatically, so several tasks can read the same broker.
- **`kafka`:** `rdkafka_settings` and `topic`, as in Pathway.
- **`python_connector`:** `module` and `class_name` of a `pw.io.python.ConnectorSubject`; other settings are passed to the class.
- **`parquet`:** `path`.

!!! warning "Known limitations"
    - **`csv`:** the `schema` setting isn't passed to Pathway, which requires one, so CSV tasks fail when they start. Use `jsonlines`, or a [custom source](custom-code.md#sources), until this is fixed.
    - **`kafka`:** the source currently adds a `group.id` setting that Pathway rejects, so Kafka tasks fail when they start. A [custom source](custom-code.md#sources) calling `pw.io.kafka.read` works in the meantime.
    - **Compact data with `schema`:** with `data_type: "compact"`, leave `schema` out and let Stream DaQ [discover it](compact-data.md#schema-discovery). Giving a schema currently fails.

### Sinks

| `type` | Writes with | Typical settings |
|---|---|---|
| `jsonlines` | `pw.io.jsonlines.write` | `filename` |
| `csv` | `pw.io.csv.write` | `filename` |
| `kafka` | `pw.io.kafka.write` | `rdkafka_settings`, `topic_name`, `format` |
| `mqtt` | `pw.io.mqtt.write` | `uri`, `topic` (a unique `client_id` is added automatically) |
| `postgres` | `pw.io.postgres.write` | `postgres_settings`, `table_name` |

A sink's `params` are passed to the Pathway writer as they are, so see Pathway's documentation for every option.

!!! warning "Columns named `time` or `diff`"
    Pathway's writers add their own `time` and `diff` fields to every row. If your input has a column with one of these names, which every EVB stream does, the per-row results clash with them: Kafka and MQTT refuse to write, and JSON Lines keeps only Pathway's value. Per-window results aren't affected.

## Where results go

A task writes up to two result streams to its output: **per-row** results from instant checks, and **per-window** results from window checks. Per-row results go to the destination given in the output settings. Per-window results go to the same destination with `_window` added to the first of these settings found:

| Setting | Per-row results | Per-window results |
|---|---|---|
| `filename` | `quality.jsonl` | `quality_window.jsonl` |
| `topic_name` (Kafka) | `quality` | `quality_window` |
| `topic` (MQTT) | `quality` | `quality_window` |
| `table_name` (Postgres) | `quality` | `quality_window` |

If none of them is present, both result streams go to the same destination. This applies to [custom sinks](custom-code.md#sinks) too.

## What the output rows look like

Every row written by a sink contains the result columns, plus two fields added by Pathway:

| Field | Meaning |
|---|---|
| `diff` | `1` for a new row, `-1` when an earlier row is withdrawn (e.g. replaced by an update). |
| `time` | Pathway's processing time for the row: when it was produced, **not** when the event happened. |

Window results are reported once per window, so they're always `diff: 1`.
