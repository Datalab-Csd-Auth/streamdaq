import pandas as pd
import pathway as pw
import pytest

from streamdaq.custom import measure
from streamdaq.measures.measure_dag import build_measure_dag
from streamdaq.measures.registry import MEASURE_REGISTRY


@measure(
    ["time", "measurement", "status"],
    name="MaxDropBetweenOkReadings",
    sort_by_column="time",
)
def _max_drop_between_ok_readings(d):
    """Largest fall in ``measurement`` between consecutive OK readings, ordered by time."""
    ok_measurements = [
        measurement for measurement, status in zip(d["measurement"], d["status"]) if status == "OK"
    ]
    return max(earlier - later for earlier, later in zip(ok_measurements, ok_measurements[1:]))


@measure(["value"], name="SumOfPositiveReadings")
def _sum_of_positive_readings(d):
    """Total of the strictly positive readings in the window."""
    return sum(value for value in d["value"] if value > 0)


class TestCustomMeasureEndToEnd:
    """Custom measures compute through the real ``build_measure_dag`` pathway."""

    def test_max_drop_uses_time_sort_and_status_filter(self):
        # Rows are deliberately given out of time order
        # and include a non-OK reading to verify sort_by works.
        dataframe = pd.DataFrame(
            {
                "time": [500, 100, 700, 300],
                "measurement": [2.0, 10.0, 9.0, 3.0],
                "status": ["OK", "OK", "OK", "WARN"],
            }
        )
        table = pw.debug.table_from_pandas(dataframe)
        result_table = build_measure_dag(table, MEASURE_REGISTRY["MaxDropBetweenOkReadings"]())
        result = pw.debug.table_to_pandas(result_table)["result"].iloc[0]

        assert result == pytest.approx(8.0)

    def test_sum_of_positive_readings(self):
        # Positive readings are 3.0, 4.0 and 5.0; the two negatives are excluded, thus 12.0.
        dataframe = pd.DataFrame({"value": [3.0, -1.0, 4.0, -2.0, 5.0]})
        table = pw.debug.table_from_pandas(dataframe)
        result_table = build_measure_dag(table, MEASURE_REGISTRY["SumOfPositiveReadings"]())
        result = pw.debug.table_to_pandas(result_table)["result"].iloc[0]

        assert result == pytest.approx(12.0)
