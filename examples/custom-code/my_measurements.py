from typing import Any

from streamdaq.custom import measure


@measure(
    name="TempDeltaMeasure",
    columns=["time", "lonely_rhino"],
    sort_by_column="time",
    desc=False,
)
def temp_delta(data: dict[str, list[Any]]) -> float:
    temps = data["lonely_rhino"]
    if not temps:
        return 0.0
    return max(temps) - min(temps)
