from typing import Any

from streamdaq.custom import assessment, measure


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


@assessment(name="IsWithinTolerance")
def is_within_tolerance(value: float) -> bool:
    return abs(value) <= 5 or value > 100
