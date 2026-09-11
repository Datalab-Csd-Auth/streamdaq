"""End-to-end tests for measures that compute over a value column ordered by a time column."""

from collections.abc import Callable
from dataclasses import dataclass

import pandas as pd
import pathway as pw
import pytest

from streamdaq.measures.any_column.sorted_tuple_time import SortedTupleTime
from streamdaq.measures.base import DataQualityMeasure
from streamdaq.measures.measure_dag import build_measure_dag
from streamdaq.measures.numeric.deltas_tuple import DeltasTuple
from streamdaq.measures.numeric.max_delta import MaxDelta
from streamdaq.measures.numeric.mean_delta import MeanDelta
from streamdaq.measures.numeric.median_delta import MedianDelta
from streamdaq.measures.numeric.min_delta import MinDelta


@dataclass(frozen=True)
class TimeMeasureCase:
    """One end-to-end case for a time-ordered measure.

    Attributes:
        factory: Builds the measure from ``(value_column, time_column)`` names.
        values: Value-column data, deliberately out of timestamp order.
        times: Timestamp-column data aligned with ``values``.
        expected: Expected scalar or tuple result.
        approx: Compare numerically with ``pytest.approx`` (for float aggregates).
        id: pytest parametrization id.
    """

    factory: Callable[[str, str], DataQualityMeasure]
    values: list
    times: list
    expected: object
    approx: bool = False
    id: str = ""


# values ordered by time -> (10, 20, 30); deltas -> (10, 10)
_ORDERED = dict(values=[30, 10, 20], times=[3, 1, 2])
# values ordered by time -> (1, 2, 5, 6); deltas -> (1, 3, 1): max 3, mean 5/3, median 1
_UNEVEN = dict(values=[6, 1, 5, 2], times=[4, 1, 3, 2])


TIME_MEASURE_CASES = [
    TimeMeasureCase(SortedTupleTime, **_ORDERED, expected=(10, 20, 30), id="SortedTupleTime"),
    TimeMeasureCase(DeltasTuple, **_ORDERED, expected=(10, 10), id="DeltasTuple"),
    TimeMeasureCase(MaxDelta, **_UNEVEN, expected=3.0, approx=True, id="MaxDelta"),
    TimeMeasureCase(MinDelta, **_UNEVEN, expected=1.0, approx=True, id="MinDelta"),
    TimeMeasureCase(MeanDelta, **_UNEVEN, expected=5 / 3, approx=True, id="MeanDelta"),
    TimeMeasureCase(MedianDelta, **_UNEVEN, expected=1.0, approx=True, id="MedianDelta"),
]


class TestTimeBasedMeasures:
    @pytest.mark.parametrize("case", TIME_MEASURE_CASES, ids=[c.id for c in TIME_MEASURE_CASES])
    def test_computed_result(self, case):
        measure = case.factory(column="v", time_column="t")
        table = pw.debug.table_from_pandas(pd.DataFrame({"v": case.values, "t": case.times}))
        result = pw.debug.table_to_pandas(build_measure_dag(table, measure))["result"].iloc[0]

        if case.approx:
            assert result == pytest.approx(case.expected)
        else:
            assert result == case.expected
