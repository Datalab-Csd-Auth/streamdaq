"""
Single source of truth for how each measure and check is tested end to end through the API.

To cover a new measure or instant check, add exactly one entry to ``MEASURE_SPECS`` or
``INSTANT_CHECK_SPECS``. Each entry carries a ``must_be`` threshold chosen so that, over the
fixed stream, at least one window (or row) satisfies it and at least one violates it — proving
the check's computation actually runs through the API in both directions.
"""

from dataclasses import dataclass
from typing import Any

from api_integration.test_utils.stream import CATEGORICAL, FLOAT, INT, TEXT, TIME


@dataclass(frozen=True)
class MeasureSpec:
    params: dict[str, Any]
    must_be: str
    extra_must_be: tuple[str, ...] = ()
    suffixes: tuple[str, ...] = ()


@dataclass(frozen=True)
class InstantCheckSpec:
    check_class: str
    params: dict[str, Any]


MEASURE_SPECS: dict[str, MeasureSpec] = {
    "AboveMeanCount": MeasureSpec({"column": INT}, ">= 2"),
    "AboveMeanFraction": MeasureSpec({"column": INT}, ">= 0.5"),
    "Availability": MeasureSpec({"column": INT, "min_samples": 3}, ">= 1"),
    "BestLineFitSlope": MeasureSpec({"column": INT, "time_column": TIME}, ">= 0.01"),
    "Constancy": MeasureSpec({"column": INT}, ">= 2"),
    "Correlation": MeasureSpec({"column": INT, "other_column": FLOAT}, ">= 0.99"),
    "Count": MeasureSpec({"column": INT}, ">= 4"),
    "DeltasTuple": MeasureSpec({"column": INT, "time_column": TIME}, "has_positive_jump"),
    "DistinctCount": MeasureSpec({"column": INT}, ">= 3"),
    "DistinctCountApprox": MeasureSpec({"column": INT}, ">= 3"),
    "DistinctFraction": MeasureSpec({"column": INT}, ">= 0.75"),
    "DistinctFractionApprox": MeasureSpec({"column": INT}, ">= 0.7"),
    "DistinctPlaceholderCount": MeasureSpec({"column": INT, "placeholders": [-1]}, ">= 1"),
    "DistinctPlaceholderFraction": MeasureSpec({"column": INT, "placeholders": [-1]}, ">= 0.1"),
    "FirstDigitFreqs": MeasureSpec({"column": INT}, "leading_digit_one_present"),
    "FrozenNumbers": MeasureSpec({"column": INT, "epsilon": 0, "min_samples": 1}, ">= 1"),
    "InRangeCount": MeasureSpec({"column": INT, "low": 0, "high": 25}, ">= 3"),
    "InRangeFraction": MeasureSpec({"column": INT, "low": 0, "high": 25}, ">= 0.75"),
    "InSetCount": MeasureSpec({"column": CATEGORICAL, "allowed_values": ["OK"]}, ">= 2"),
    "InSetFraction": MeasureSpec({"column": CATEGORICAL, "allowed_values": ["OK"]}, ">= 0.5"),
    "Max": MeasureSpec({"column": INT}, ">= 95"),
    "MaxDelta": MeasureSpec({"column": INT, "time_column": TIME}, "[16, 999)"),
    "MaxFractionalPartLength": MeasureSpec({"column": FLOAT}, ">= 3"),
    "MaxIntegerPartLength": MeasureSpec({"column": INT}, ">= 2"),
    "MaxLength": MeasureSpec({"column": TEXT}, ">= 10"),
    "Mean": MeasureSpec({"column": FLOAT}, ">= 8"),
    "MeanDelta": MeasureSpec({"column": INT, "time_column": TIME}, ">= 7"),
    "MeanFractionalPartLength": MeasureSpec({"column": FLOAT}, ">= 1.25"),
    "MeanIntegerPartLength": MeasureSpec({"column": INT}, ">= 2"),
    "MeanLength": MeasureSpec({"column": TEXT}, ">= 4"),
    "Median": MeasureSpec({"column": INT}, ">= 40"),
    "MedianDelta": MeasureSpec({"column": INT, "time_column": TIME}, ">= 7"),
    "MedianFractionalPartLength": MeasureSpec({"column": FLOAT}, ">= 1.5"),
    "MedianIntegerPartLength": MeasureSpec({"column": INT}, ">= 2"),
    "MedianLength": MeasureSpec({"column": TEXT}, ">= 4"),
    "Min": MeasureSpec({"column": INT}, ">= 5"),
    "MinDelta": MeasureSpec({"column": INT, "time_column": TIME}, ">= 10"),
    "MinFractionalPartLength": MeasureSpec({"column": FLOAT}, ">= 1"),
    "MinIntegerPartLength": MeasureSpec({"column": INT}, ">= 2"),
    "MinLength": MeasureSpec({"column": TEXT}, ">= 2"),
    "MissingCount": MeasureSpec({"column": TEXT}, ">= 1"),
    "MissingFraction": MeasureSpec({"column": TEXT}, ">= 0.25"),
    "Monotonic": MeasureSpec({"column": INT, "time_column": TIME}, ">= 1"),
    "MostFrequent": MeasureSpec({"column": CATEGORICAL}, "contains_ok"),
    "MostFrequentApprox": MeasureSpec({"column": CATEGORICAL}, "contains_ok"),
    "Ndarray": MeasureSpec({"column": INT}, "array_max_at_least_100"),
    "Percentiles": MeasureSpec({"column": INT}, "median_at_least_20"),
    "RegexCount": MeasureSpec({"column": TEXT, "regex": r"^\d+$"}, ">= 2"),
    "RegexFraction": MeasureSpec({"column": TEXT, "regex": r"^\d+$"}, ">= 0.5"),
    "SortedTupleTime": MeasureSpec(
        {"column": INT, "time_column": TIME}, "ends_higher_than_it_starts"
    ),
    "SortedTupleValue": MeasureSpec({"column": INT}, "value_span_at_least_50"),
    "Sum": MeasureSpec({"column": INT}, ">= 185"),
    "Tuple": MeasureSpec({"column": INT}, "has_enough_samples"),
    "UniqueCount": MeasureSpec({"column": INT}, ">= 4"),
    "UniqueFraction": MeasureSpec({"column": INT}, ">= 1"),
    "UniqueOverDistinct": MeasureSpec({"column": INT}, ">= 1"),
    "Variance": MeasureSpec({"column": INT}, ">= 1000"),
    "WindowDuration": MeasureSpec(
        {"column": INT},
        "== 1000",
        extra_must_be=("== 1001",),
        suffixes=(
            "true",
            "false",
        ),
    ),
}

INSTANT_CHECK_SPECS: dict[str, InstantCheckSpec] = {
    "InRange": InstantCheckSpec("InRange", {"column": INT, "low": 0, "high": 25}),
    "InRowComparison": InstantCheckSpec(
        "InRowComparison", {"columns": [INT, FLOAT], "operator": "lt"}
    ),
    "InSet": InstantCheckSpec("InSet", {"column": CATEGORICAL, "allowed_values": ["OK"]}),
    "Length": InstantCheckSpec("Length", {"column": TEXT, "must_be": "<= 4"}),
    "Regex": InstantCheckSpec("Regex", {"column": TEXT, "regex": r"^\d+$"}),
    "Value": InstantCheckSpec("Value", {"column": INT, "must_be": "<= 15"}),
}
