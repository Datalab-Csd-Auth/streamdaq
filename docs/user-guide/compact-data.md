# :satellite: Compact Data

Stream DaQ can monitor **compact** IoT messages in the **EVB** (Event Bus) format, where one message carries several measurements at once. Stream DaQ unpacks them into ordinary rows and columns, so all checks work on them as usual. See [Compact vs Native Data Formats](../concepts/compact-vs-native-data.md) for the background.

## The EVB format

```json title="An EVB message"
{
  "measurements": [
    {
      "name": "TemperatureHumidity",
      "tags": {"plant": "StreamdaqFactory", "unit_id": "012332"},
      "type": "Points",
      "fields": ["time", "temperature", "humidity"],
      "values": [
        [1645334535000, 60, 55],
        [1645338135000, 62, 54]
      ]
    }
  ]
}
```

| Part | Meaning |
|---|---|
| `fields` | The column names. The **first one must be `time`**. |
| `values` | One list per reading, in the same order as `fields`. The time is in **epoch milliseconds** (13 digits). |
| `tags` | Text labels that apply to all readings of the measurement, e.g. the plant and unit. |
| `type` | `Points`, `Report`, `Metadata`, `State`, `Configuration` or `Unknown`. |

## From messages to rows

Each reading in `values` becomes **one row**. The message above becomes:

| `time` | `temperature` | `humidity` | `plant` | `unit_id` | `name` | `type` | `validation_errors_report` |
|---|---|---|---|---|---|---|---|
| 1645334535000 | 60 | 55 | StreamdaqFactory | 012332 | TemperatureHumidity | Points | `null` |
| 1645338135000 | 62 | 54 | StreamdaqFactory | 012332 | TemperatureHumidity | Points | `null` |

- **Fields** become columns, and **each tag** becomes a text column.
- **`validation_errors_report`** is `null` for a valid message. For an invalid one, it describes what's wrong, and the row is still kept, so you can check for it.

A message is invalid if, for example, its first field isn't `time`, a reading has a different number of values than there are fields, or a time doesn't have 13 digits.

!!! warning "Fields are matched by position"
    Values are assigned to columns by their **position**, using the field order discovered from the first message. Producers must always send the fields in the same order.

## Schema discovery

You don't need to describe the columns of compact data: Stream DaQ **discovers them from the first valid message** it receives. It waits up to 20 seconds; if no valid message arrives by then, the task fails with a timeout error.

The discovered columns are fixed from then on. Fields or tags that only appear in later messages don't become columns.

## Monitoring EVB data

Set `data_type` to `"compact"` in the source's settings, and use `time` as the time column. Durations are in milliseconds:

```json title="POST /api/v1/bulk_create"
[{
  "name": "evb_quality",
  "input": {
    "type": "mqtt",
    "params": {
      "data_type": "compact",
      "connector_params": {"uri": "mqtt://127.0.0.1:1883", "topic": "evb/data"}
    }
  },
  "output": {"type": "jsonlines", "params": {"filename": "evb_quality.jsonl"}},
  "window_checks_config": {
    "windowby_column": "time",
    "groupby_column": "unit_id",
    "window": {"type": "tumbling", "params": {"duration": 5000}},
    "checks": [
      {"name": "enough_readings", "measure": {"type": "Count", "params": {"column": "time"}}, "must_be": ">= 1"}
    ]
  }
}]
```

The sources that support compact data are `mqtt`, `kafka` and `python_connector`, plus [custom sources](custom-code.md#sources) declared with `data_format="compact"`.

## Grouping by tags

Tags become ordinary columns, so you can check each unit separately with `"groupby_column": "unit_id"`. To group by **several** tags, for example each unit of each plant, see [Advanced Examples](advanced-examples.md#grouping-by-several-columns).

## Test data

`EVBMockStream` generates EVB messages for testing, including some deliberately invalid ones. Use it through the `python_connector` source:

```json
"input": {
  "type": "python_connector",
  "params": {
    "data_type": "compact",
    "module": "streamdaq.schema.evb.mock_generator",
    "class_name": "EVBMockStream",
    "connector_params": {"nof_messages": 100, "sleep_between_sec": 0.1}
  }
}
```

| Setting | Default |
|---|---|
| `nof_messages` | `10` |
| `nof_non_time_fields` | `15` |
| `sleep_between_sec` | `0.0` |
| `values_min`, `values_max` | `0.0`, `100.0` |
| `round_values` | `2` |
