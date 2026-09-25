from typing import Any

import pathway as pw

from streamdaq.custom import assessment, measure, sink, source
from streamdaq.io.utils import ensure_unique_mqtt_client_id
from streamdaq.schema.evb.definitions import EVBSchema

# --- Custom data quality measures ---


@measure(
    name="MaxDropBetweenOkReadings",
    columns=["time", "measurement", "status"],
    sort_by_column="time",
)
def max_drop_between_ok_readings(data: dict[str, list[Any]]) -> float:
    """Largest drop in `measurement` between consecutive ``OK`` readings in chronological order."""

    # Access the data per column using `data[<column_name>]`.
    # Here, ``sort_by_column="time"`` ensures that all columns are already sorted by time!
    measurements = data["measurement"]
    statuses = data["status"]

    # Compute the custom data quality measure of your choice
    ok_values = [
        measurement_value
        for measurement_value, status in zip(measurements, statuses)
        if status == "OK"
    ]
    drops = [previous - current for previous, current in zip(ok_values, ok_values[1:])]

    # Return the measure value. If ``must_be`` is provided, it will run on this return value
    return max(drops) if drops else 0.0


# --- Custom data quality assessments ---


@assessment(name="IsWithinTolerance")
def is_within_tolerance(value: float) -> bool:
    return abs(value) <= 5 or value > 100


# --- Custom data sources to be monitored (native and compact available) ---


@source(name="MyNativeDataSource")  # if not specified, ``data_format`` defaults to "native"
def my_mqtt_native(uri: str, topic: str):
    """Reads raw messages from MQTT and adds one custom column before registering it as
    a streamdaq input sources.
    See https://pathway.com/developers/user-guide/connect/live-data-framework-connectors
    for a full list of streamdaq-supported options.

    If not specified otherwise (see below) a source is treated as ``native`` data format.
    For ``native`` data format, the custom source function should return a pathway Table. The
    keyword arguments come from the payload's ``connector_params``.
    """
    schema = pw.schema_builder(  # More: https://pathway.com/developers/user-guide/connect/schema
        columns={
            "key": pw.column_definition(dtype=int, primary_key=True),
            "data": pw.column_definition(dtype=int, default_value=0),
        },
        name="my_schema",
    )

    uri = ensure_unique_mqtt_client_id(uri)
    raw_table = pw.io.mqtt.read(uri=uri, topic=topic, format="json", schema=schema)
    result = raw_table.with_columns(custom_logic="just an example!")
    return result


@source(name="MyCompactDataSource", data_format="compact")
def my_mqtt_compact(uri: str, topic: str):
    """Reads raw EVB messages from MQTT for streamdaq to convert to its native format.

    A ``compact`` source returns ``(raw_table, post_transform)``: streamdaq sniffs the schema,
    converts ``raw_table`` to its native form, and then applies ``post_transform`` to it. The
    keyword arguments come from the payload's ``connector_params``.
    """
    uri = ensure_unique_mqtt_client_id(uri)
    raw_table = pw.io.mqtt.read(uri=uri, topic=topic, format="json", schema=EVBSchema)

    def post_transform(native_table: pw.Table) -> pw.Table:
        native_table_enriched = native_table.with_columns(custom_logic="just an example!")
        return native_table_enriched

    return raw_table, post_transform


# --- Custom data sinks to write the quality meta-stream to ---


@sink(name="MyJsonlinesSink")
def my_jsonlines_sink(table: pw.Table, **params: Any) -> None:
    """Writes the results to a JSON-lines file after doing a custom column addition."""
    result = table.with_columns(extra_column_from_custom_sink="extra")
    pw.io.jsonlines.write(result, **params)
