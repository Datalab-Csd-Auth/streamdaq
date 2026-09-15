"""
Single source of truth for how each measure and check is tested end to end through the API.

To cover a new measure or instant check, add exactly one entry to ``MEASURE_SPECS`` or
``INSTANT_CHECK_SPECS`` (or, if it cannot be covered yet, to ``EXCLUDED_MEASURES``). Each
entry carries a ``must_be`` threshold chosen so that, over the fixed stream, at least one
window (or row) satisfies it and at least one violates it — proving the check's computation
actually runs through the API in both directions.
"""

from dataclasses import dataclass
from typing import Any

from api_integration.test_utils.stream import CATEGORICAL, FLOAT, INT, TEXT, TIME
from streamdaq.api.registries import MEASURE_REGISTRY


@dataclass(frozen=True)
class MeasureSpec:
    params: dict[str, Any]
    must_be: str


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
    "DistinctCount": MeasureSpec({"column": INT}, ">= 3"),
    "DistinctCountApprox": MeasureSpec({"column": INT}, ">= 3"),
    "DistinctFraction": MeasureSpec({"column": INT}, ">= 0.75"),
    "DistinctFractionApprox": MeasureSpec({"column": INT}, ">= 0.7"),
    "DistinctPlaceholderCount": MeasureSpec({"column": INT, "placeholders": [-1]}, ">= 1"),
    "DistinctPlaceholderFraction": MeasureSpec({"column": INT, "placeholders": [-1]}, ">= 0.1"),
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
    "RegexCount": MeasureSpec({"column": TEXT, "regex": r"^\d+$"}, ">= 2"),
    "RegexFraction": MeasureSpec({"column": TEXT, "regex": r"^\d+$"}, ">= 0.5"),
    "Sum": MeasureSpec({"column": INT}, ">= 185"),
    "UniqueCount": MeasureSpec({"column": INT}, ">= 4"),
    "UniqueFraction": MeasureSpec({"column": INT}, ">= 1"),
    "UniqueOverDistinct": MeasureSpec({"column": INT}, ">= 1"),
    "Variance": MeasureSpec({"column": INT}, ">= 1000"),
}

# Measures deliberately not covered as window checks temporarily.
# TODO Enable them once https://github.com/Datalab-Csd-Auth/streamdaq/issues/16 is implemented
EXCLUDED_MEASURES: frozenset[str] = frozenset(
    {
        "DeltasTuple",
        "FirstDigitFreqs",
        "MostFrequent",
        "MostFrequentApprox",
        "Ndarray",
        "Percentiles",
        "SortedTupleTime",
        "SortedTupleValue",
        "Tuple",
        "WindowDuration",
    }
)

# TODO Add 'Row' is excluded when implemented at the source code level.
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


def assert_completeness_of_integration_tests() -> None:
    """Fail if a registered measure is neither specified nor explicitly excluded."""
    registered = set(MEASURE_REGISTRY)
    specified = set(MEASURE_SPECS)

    overlap = specified & EXCLUDED_MEASURES
    assert not overlap, f"Conflict: Found measures both specified and excluded: {sorted(overlap)}."

    accounted_for = specified | EXCLUDED_MEASURES
    unaccounted = registered - accounted_for
    assert not unaccounted, (
        f"Measures registered but not covered or excluded: {sorted(unaccounted)}. "
        "Add each to MEASURE_SPECS (with its params and must_be) or to EXCLUDED_MEASURES."
    )

    stale = accounted_for - registered
    assert not stale, f"Specs/exclusions reference unknown measures: {sorted(stale)}."
