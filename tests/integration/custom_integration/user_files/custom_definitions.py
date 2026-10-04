from typing import Any

import pathway as pw
from custom_integration.stream_compact import FiniteCompactEVBStream
from custom_integration.stream_native import FiniteCustomStream

from streamdaq.custom import assessment, measure, sink, source
from streamdaq.schema.evb.definitions import EVBSchema


@measure(
    name="MaxDropBetweenOkReadings",
    columns=["time", "measurement", "status"],
    sort_by_column="time",
)
def max_drop_between_ok_readings(data: dict[str, list[Any]]) -> float:
    """
    Largest drop in ``measurement`` between consecutive ``OK`` readings.
    The result depends on ordering by ``sort_by_column="time"`` to be correct.
    """
    ok_values = [
        measurement_value
        for measurement_value, status in zip(data["measurement"], data["status"])
        if status == "OK"
    ]
    drops = [prev - curr for prev, curr in zip(ok_values, ok_values[1:])]
    return max(drops) if drops else 0.0


@assessment(name="IsDropSpike")
def is_drop_spike(value: float) -> bool:
    """A window's max drop counts as a spike when it is at least two units."""
    return value >= 2.0


@source(name="FiniteCustomPythonSource")
def finite_custom_python_source():
    """Reads the shared finite stream through a user-defined native source.

    Demonstrates that a user can wrap a Pathway connector in an ``@source`` and reference it by
    name in the payload, exactly like a built-in input. It returns a native ``pw.Table``.
    """

    schema = pw.schema_from_types(time=int, measurement=float, status=str)
    return pw.io.python.read(FiniteCustomStream(), schema=schema)


@source(name="FiniteCompactEVBSource", data_format="compact")
def finite_compact_evb_source():
    raw_table = pw.io.python.read(FiniteCompactEVBStream(), schema=EVBSchema)

    def post_transform(native_table: pw.Table) -> pw.Table:
        return native_table

    return raw_table, post_transform


@sink(name="JsonlinesFileSink")
def jsonlines_file_sink(table: pw.Table, **params: Any) -> None:
    """Writes the results to a JSON-lines file after adding an extra column"""
    table = table.with_columns(extra_column_from_custom_sink="extra")
    pw.io.jsonlines.write(table, **params)
