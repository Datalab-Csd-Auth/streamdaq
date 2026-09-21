from typing import Any

from streamdaq.custom import assessment, measure


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
