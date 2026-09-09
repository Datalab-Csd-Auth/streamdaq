import pandas as pd
import pathway as pw
import pytest

import streamdaq.measures as measures_module
import streamdaq.measures.any_column as any_column_mod
import streamdaq.measures.categorical as categorical_mod
import streamdaq.measures.numeric as numeric_mod

# any_column measures
from streamdaq.measures.any_column.availability import Availability
from streamdaq.measures.any_column.constancy import Constancy
from streamdaq.measures.any_column.correlation import Correlation
from streamdaq.measures.any_column.count import Count
from streamdaq.measures.any_column.distinct_count import DistinctCount
from streamdaq.measures.any_column.distinct_count_approx import DistinctCountApprox
from streamdaq.measures.any_column.distinct_fraction import DistinctFraction
from streamdaq.measures.any_column.distinct_fraction_approx import DistinctFractionApprox
from streamdaq.measures.any_column.distinct_placeholder_count import DistinctPlaceholderCount
from streamdaq.measures.any_column.distinct_placeholder_fraction import DistinctPlaceholderFraction
from streamdaq.measures.any_column.in_set_count import InSetCount
from streamdaq.measures.any_column.in_set_fraction import InSetFraction
from streamdaq.measures.any_column.max import Max
from streamdaq.measures.any_column.min import Min
from streamdaq.measures.any_column.missing_count import MissingCount
from streamdaq.measures.any_column.missing_fraction import MissingFraction
from streamdaq.measures.any_column.monotonic import Monotonic
from streamdaq.measures.any_column.most_frequent import MostFrequent
from streamdaq.measures.any_column.most_frequent_approx import MostFrequentApprox
from streamdaq.measures.any_column.ndarray import Ndarray
from streamdaq.measures.any_column.sorted_tuple_time import SortedTupleTime
from streamdaq.measures.any_column.sorted_tuple_value import SortedTupleValue
from streamdaq.measures.any_column.tuple import Tuple
from streamdaq.measures.any_column.unique_count import UniqueCount
from streamdaq.measures.any_column.unique_fraction import UniqueFraction
from streamdaq.measures.any_column.unique_over_distinct import UniqueOverDistinct
from streamdaq.measures.any_column.window_duration import WindowDuration

# categorical measures
from streamdaq.measures.categorical.max_length import MaxLength
from streamdaq.measures.categorical.mean_length import MeanLength
from streamdaq.measures.categorical.median_length import MedianLength
from streamdaq.measures.categorical.min_length import MinLength
from streamdaq.measures.categorical.regex_count import RegexCount
from streamdaq.measures.categorical.regex_fraction import RegexFraction
from streamdaq.measures.measure_dag import build_measure_dag

# numeric measures
from streamdaq.measures.numeric.above_mean_count import AboveMeanCount
from streamdaq.measures.numeric.above_mean_fraction import AboveMeanFraction
from streamdaq.measures.numeric.best_line_fit_slope import BestLineFitSlope
from streamdaq.measures.numeric.first_digit_freqs import FirstDigitFreqs
from streamdaq.measures.numeric.frozen_numbers import FrozenNumbers
from streamdaq.measures.numeric.in_range_count import InRangeCount
from streamdaq.measures.numeric.in_range_fraction import InRangeFraction
from streamdaq.measures.numeric.max_fractional_part_length import MaxFractionalPartLength
from streamdaq.measures.numeric.max_integer_part_length import MaxIntegerPartLength
from streamdaq.measures.numeric.mean import Mean
from streamdaq.measures.numeric.mean_fractional_part_length import MeanFractionalPartLength
from streamdaq.measures.numeric.mean_integer_part_length import MeanIntegerPartLength
from streamdaq.measures.numeric.median import Median
from streamdaq.measures.numeric.median_fractional_part_length import MedianFractionalPartLength
from streamdaq.measures.numeric.median_integer_part_length import MedianIntegerPartLength
from streamdaq.measures.numeric.min_fractional_part_length import MinFractionalPartLength
from streamdaq.measures.numeric.min_integer_part_length import MinIntegerPartLength
from streamdaq.measures.numeric.percentiles import Percentiles
from streamdaq.measures.numeric.sum import Sum
from streamdaq.measures.numeric.variance import Variance
from streamdaq.utils.data_type_applicability import DataTypeApplicability


class MeasureSpec:
    """A single source of truth describing one measure for the data-driven tests.

    Adding a new measure to the suite means adding exactly one ``MeasureSpec`` entry to
    ``MEASURE_SPECS`` below. Each spec drives three checks: applicability, declared
    dependencies, and (when ``cases`` are provided) end-to-end computation.

    Attributes:
        factory: Zero-arg callable that constructs the measure instance. A callable
            (rather than an instance) keeps construction lazy and lets one measure class
            appear several times with different arguments.
        applicability: The expected ``_applicability`` of the measure class.
        dependencies: The expected ``_dependencies`` of the measure class. Kept explicit
            (rather than read from the class) so the test is a genuine assertion and not
            a tautology.
        cases: Optional end-to-end cases as ``(data, expected)`` pairs. ``data`` is the
            column values fed through a real Pathway reduce; ``expected`` is the scalar
            result. Measures whose output is non-deterministic or not a simple scalar
            (e.g. sketches, ndarrays, window metadata) omit cases.
        unordered: When ``True``, tuple-valued results are compared order-insensitively
            (but counts still matter) — for measures whose result is a set of tied or
            unordered values (e.g. ``Tuple``, ``MostFrequent``). Defaults to ``False``,
            i.e. exact comparison, so order-significant measures like ``SortedTupleValue``
            are asserted exactly.
        expected_attrs: Optional ``{attribute_name: expected_value}`` mapping asserted on
            the constructed instance. Covers default and normalized construction values
            (e.g. ``Availability`` defaults ``min_samples`` to ``1``; ``FrozenNumbers``
            normalizes a negative ``epsilon`` to its absolute value).
        invalid_kwargs: Optional list of ``(kwargs, error_type, match)`` tuples asserting
            that constructing the measure class with ``kwargs`` raises ``error_type`` and
            that the error message matches the ``match`` regex fragment. Covers
            construction-time validation of invalid arguments.
        id: Human-readable, unique identifier used for the pytest parametrization id.
    """

    def __init__(
        self,
        factory,
        applicability,
        dependencies,
        cases=None,
        unordered=False,
        expected_attrs=None,
        invalid_kwargs=None,
        id=None,
    ):
        self.factory = factory
        self.applicability = applicability
        self.dependencies = dependencies
        self.cases = cases or []
        self.unordered = unordered
        self.expected_attrs = expected_attrs or {}
        self.invalid_kwargs = invalid_kwargs or []
        self.id = id or factory().__class__.__name__

    @property
    def measure_cls(self):
        """The measure class, derived from a sample constructed instance."""
        return type(self.factory())


_ANY = DataTypeApplicability.ANY_COLUMN
_NUM = DataTypeApplicability.NUMERIC_ONLY
_CAT = DataTypeApplicability.CATEGORICAL_ONLY

MEASURE_SPECS = [
    # --- any_column: no dependencies ---
    MeasureSpec(lambda: Count(column="x"), _ANY, [], [([10, 20, 10, 30], 4)]),
    MeasureSpec(lambda: Tuple(column="x"), _ANY, [], [([1, 2, 3], (1, 2, 3))], unordered=True),
    MeasureSpec(lambda: SortedTupleValue(column="x"), _ANY, [], [([3, 1, 2], (1, 2, 3))]),
    MeasureSpec(lambda: Ndarray(column="x"), _ANY, []),
    MeasureSpec(lambda: Max(column="x"), _ANY, [], [([1, 5, 3], 5)]),
    MeasureSpec(lambda: Min(column="x"), _ANY, [], [([4, 2, 3], 2)]),
    MeasureSpec(lambda: WindowDuration(column="x"), _ANY, []),
    MeasureSpec(lambda: DistinctCountApprox(column="x"), _ANY, [], [([1, 1, 2, 2, 3], 3)]),
    MeasureSpec(
        lambda: MostFrequentApprox(column="x"),
        _ANY,
        [],
        [(["a", "a", "b", "b", "c"], ("a", "b"))],
        unordered=True,
    ),
    # --- any_column: depends on [Tuple] ---
    MeasureSpec(lambda: SortedTupleTime(column="x", time_column="time"), _ANY, [Tuple]),
    MeasureSpec(lambda: Constancy(column="x"), _ANY, [Tuple], [([1, 1, 2, 3], 2)]),
    MeasureSpec(lambda: DistinctCount(column="x"), _ANY, [Tuple], [([10, 20, 10, 30], 3)]),
    MeasureSpec(lambda: DistinctPlaceholderCount(column="x", placeholders=["N/A"]), _ANY, [Tuple]),
    MeasureSpec(
        lambda: InSetCount(column="x", allowed_values={10, 30}),
        _ANY,
        [Tuple],
        [([10, 20, 10, 30], 3)],
    ),
    MeasureSpec(
        lambda: Monotonic(column="x"),
        _ANY,
        [Tuple],
        expected_attrs={"direction": "asc", "strict": True},
        invalid_kwargs=[
            ({"column": "my_col", "direction": "up"}, ValueError, "column `my_col`"),
            ({"column": "x", "direction": "ASC"}, ValueError, None),  # case-sensitive
        ],
        id="Monotonic[defaults]",
    ),
    MeasureSpec(lambda: Monotonic(column="x", strict=False), _ANY, [Tuple], [([5, 5, 5, 5], True)]),
    MeasureSpec(
        lambda: Monotonic(column="x", direction="desc", strict=False),
        _ANY,
        [Tuple],
        [([3, 3, 3], True)],
        id="Monotonic[desc,non-strict]",
    ),
    MeasureSpec(
        lambda: Monotonic(column="x", direction="desc", strict=True),
        _ANY,
        [Tuple],
        [([3, 3, 3], False)],
        id="Monotonic[desc,strict]",
    ),
    MeasureSpec(
        lambda: MostFrequent(column="x"),
        _ANY,
        [Tuple],
        [(["a", "a", "b", "b", "c"], ("a", "b"))],
        unordered=True,
    ),
    MeasureSpec(lambda: UniqueCount(column="x"), _ANY, [Tuple], [([1, 1, 2, 3], 2)]),
    MeasureSpec(lambda: UniqueOverDistinct(column="x"), _ANY, [Tuple]),
    # --- any_column: depends on [Tuple, Count] ---
    MeasureSpec(
        lambda: DistinctFraction(column="x"), _ANY, [Tuple, Count], [([10, 20, 10, 30], 0.75)]
    ),
    MeasureSpec(lambda: DistinctFraction(column="x", precision=2), _ANY, [Tuple, Count]),
    MeasureSpec(lambda: DistinctFractionApprox(column="x"), _ANY, [Tuple, Count]),
    MeasureSpec(
        lambda: DistinctPlaceholderFraction(column="x", placeholders=["N/A"]), _ANY, [Tuple, Count]
    ),
    MeasureSpec(lambda: InSetFraction(column="x", allowed_values={"a"}), _ANY, [Tuple, Count]),
    MeasureSpec(lambda: MissingCount(column="x"), _ANY, [Tuple], [([1, None, "", 4], 2)]),
    MeasureSpec(
        lambda: MissingFraction(column="x"), _ANY, [Tuple, Count], [([1, None, "", 4], 0.5)]
    ),
    MeasureSpec(lambda: UniqueFraction(column="x"), _ANY, [Tuple, Count], [([1, 1, 2, 3], 0.5)]),
    # --- any_column: depends on [Count] ---
    MeasureSpec(
        lambda: Availability(column="x"),
        _ANY,
        [Count],
        [([1, 2, 3], True)],
        expected_attrs={"min_samples": 1},
        invalid_kwargs=[
            ({"column": "my_col", "min_samples": 0}, ValueError, "column `my_col`"),
            ({"column": "x", "min_samples": -5}, ValueError, None),
        ],
    ),
    MeasureSpec(
        lambda: Availability(column="x", min_samples=10),
        _ANY,
        [Count],
        [([1, 2, 3], False)],
        id="Availability[min_samples=10]",
    ),
    # --- numeric ---
    MeasureSpec(lambda: AboveMeanCount(column="x"), _NUM, [Tuple]),
    MeasureSpec(lambda: AboveMeanFraction(column="x"), _ANY, [Tuple, Count]),
    MeasureSpec(lambda: BestLineFitSlope(column="x", time_column="t"), _ANY, [Tuple]),
    MeasureSpec(
        lambda: Correlation(column="x", other_column="y"),
        _ANY,
        [Tuple],
        expected_attrs={"method": "pearson"},
        invalid_kwargs=[
            (
                {"column": "x", "other_column": "y", "method": "invalid"},
                NotImplementedError,
                None,
            ),
        ],
    ),
    MeasureSpec(lambda: FirstDigitFreqs(column="x"), _NUM, [Tuple]),
    MeasureSpec(
        lambda: FrozenNumbers(column="x", epsilon=0),
        _NUM,
        [SortedTupleValue],
        [([5, 5, 5], True), ([1, 2, 3], False)],
        expected_attrs={"epsilon": 0.0, "min_samples": 1},
        invalid_kwargs=[({"column": "x", "min_samples": 0}, ValueError, None)],
    ),
    MeasureSpec(
        lambda: FrozenNumbers(column="x", epsilon=-0.5),
        _NUM,
        [SortedTupleValue],
        expected_attrs={"epsilon": 0.5},  # negative epsilon is normalized to its abs value
        id="FrozenNumbers[epsilon-normalization]",
    ),
    MeasureSpec(
        lambda: FrozenNumbers(column="x", epsilon=5),
        _NUM,
        [SortedTupleValue],
        [([1, 3, 5], True)],
        id="FrozenNumbers[epsilon=5]",
    ),
    MeasureSpec(lambda: InRangeCount(column="x", low=0, high=100), _ANY, [Tuple]),
    MeasureSpec(lambda: InRangeFraction(column="x", low=0, high=100), _ANY, [Tuple, Count]),
    MeasureSpec(lambda: MaxFractionalPartLength(column="x"), _NUM, [Tuple]),
    MeasureSpec(lambda: MaxIntegerPartLength(column="x"), _NUM, [Tuple]),
    MeasureSpec(lambda: Mean(column="x"), _NUM, [], [([10, 20, 30], 20.0)]),
    MeasureSpec(
        lambda: Mean(column="x", precision=4),
        _NUM,
        [],
        [([1, 3, 3], 2.3333)],
        id="Mean[precision=4]",
    ),
    MeasureSpec(lambda: MeanFractionalPartLength(column="x"), _NUM, [Tuple]),
    MeasureSpec(lambda: MeanIntegerPartLength(column="x"), _NUM, [Tuple]),
    MeasureSpec(lambda: Median(column="x"), _NUM, [], [([10, 20, 30, 40], 25.0)]),
    MeasureSpec(lambda: MedianFractionalPartLength(column="x"), _NUM, [Tuple]),
    MeasureSpec(lambda: MedianIntegerPartLength(column="x"), _NUM, [Tuple]),
    MeasureSpec(lambda: MinFractionalPartLength(column="x"), _NUM, [Tuple]),
    MeasureSpec(lambda: MinIntegerPartLength(column="x"), _NUM, [Tuple]),
    MeasureSpec(lambda: Percentiles(column="x"), _ANY, [Tuple]),
    MeasureSpec(lambda: Variance(column="x"), _NUM, [], [([2, 4, 6], 2.6666666666666665)]),
    MeasureSpec(lambda: Sum(column="x"), _NUM, [], [([10, 20, 30], 60)]),
    # --- categorical ---
    MeasureSpec(lambda: MaxLength(column="x"), _CAT, [Tuple], [(["a", "bbb", "cc"], 3)]),
    MeasureSpec(lambda: MeanLength(column="x"), _CAT, [Tuple], [(["a", "bbb"], 2.0)]),
    MeasureSpec(lambda: MedianLength(column="x"), _CAT, [Tuple], [(["a", "bb", "ccc"], 2)]),
    MeasureSpec(lambda: MinLength(column="x"), _CAT, [Tuple], [(["hello", "hi", "world"], 2)]),
    MeasureSpec(
        lambda: RegexCount(column="x", regex=r"^\d+$"),
        _ANY,
        [Tuple],
        [(["123", "abc", "456"], 2)],
    ),
    MeasureSpec(lambda: RegexFraction(column="x", regex=r"^\d+$"), _ANY, [Tuple, Count]),
]

# The concrete measure classes covered by the spec table (deduplicated, ordered).
_MEASURE_CLASSES = list(dict.fromkeys(spec.measure_cls for spec in MEASURE_SPECS))

# The abstract base classes that are exported alongside the concrete measures but are
# not themselves measures (and therefore never appear in MEASURE_SPECS).
_ABSTRACT_BASE_NAMES = {"DataQualityMeasure", "RoundableDataQualityMeasure"}

# End-to-end cases flattened for parametrization: (measure_factory, data, expected, id).
_END_TO_END_CASES = [
    (spec.factory, data, expected, spec.unordered, f"{spec.id}[{i}]")
    for spec in MEASURE_SPECS
    for i, (data, expected) in enumerate(spec.cases)
]

# Specs that assert default/normalized attribute values on the constructed instance.
_CONSTRUCTION_SPECS = [spec for spec in MEASURE_SPECS if spec.expected_attrs]

# Invalid-argument cases flattened for parametrization:
# (measure_class, kwargs, error_type, match, id).
_INVALID_KWARGS_CASES = [
    (spec.measure_cls, kwargs, error_type, match, f"{spec.id}[{i}]")
    for spec in MEASURE_SPECS
    for i, (kwargs, error_type, match) in enumerate(spec.invalid_kwargs)
]


class TestApplicability:
    """Every measure declares the expected applicability."""

    @pytest.mark.parametrize("spec", MEASURE_SPECS, ids=[s.id for s in MEASURE_SPECS])
    def test_applicability(self, spec):
        assert spec.factory()._applicability == spec.applicability


class TestDependencies:
    """Every measure declares the expected computation dependencies."""

    @pytest.mark.parametrize("spec", MEASURE_SPECS, ids=[s.id for s in MEASURE_SPECS])
    def test_dependencies(self, spec):
        assert spec.factory()._dependencies == spec.dependencies


class TestConstruction:
    """Measures expose the expected default and normalized attribute values."""

    @pytest.mark.parametrize("spec", _CONSTRUCTION_SPECS, ids=[s.id for s in _CONSTRUCTION_SPECS])
    def test_expected_attrs(self, spec):
        measure = spec.factory()
        for attr, expected in spec.expected_attrs.items():
            assert getattr(measure, attr) == expected


class TestValidation:
    """Measures reject invalid constructor arguments with informative errors."""

    @pytest.mark.parametrize(
        "measure_cls, kwargs, error_type, match",
        [(cls, kwargs, err, match) for (cls, kwargs, err, match, _id) in _INVALID_KWARGS_CASES],
        ids=[_id for (_cls, _kwargs, _err, _match, _id) in _INVALID_KWARGS_CASES],
    )
    def test_invalid_kwargs_raise(self, measure_cls, kwargs, error_type, match):
        with pytest.raises(error_type, match=match):
            measure_cls(**kwargs)


class TestExports:
    """The public ``__all__`` lists stay in sync with the actual measures.

    These assertions are driven by ``MEASURE_SPECS`` and the package structure rather than
    hardcoded names or counts, so they self-maintain as measures are added or moved.
    """

    @pytest.mark.parametrize(
        "measure_cls", _MEASURE_CLASSES, ids=[cls.__name__ for cls in _MEASURE_CLASSES]
    )
    def test_every_measure_is_exported(self, measure_cls):
        # Any measure exercised by the suite must be publicly exported.
        assert measure_cls.__name__ in measures_module.__all__

    @pytest.mark.parametrize("base_name", sorted(_ABSTRACT_BASE_NAMES))
    def test_abstract_bases_are_exported(self, base_name):
        assert base_name in measures_module.__all__

    def test_subpackage_union_equals_concrete_measures(self):
        # The top-level measures package re-exports exactly the concrete measures from its
        # subpackages and plus the abstract bases.
        subpackage_union = (
            set(any_column_mod.__all__) | set(numeric_mod.__all__) | set(categorical_mod.__all__)
        )
        concrete_top_level = set(measures_module.__all__) - _ABSTRACT_BASE_NAMES
        assert subpackage_union == concrete_top_level

    def test_no_measure_appears_in_two_subpackages(self):
        # Each concrete measure is owned by exactly one subpackage.
        names = (
            list(any_column_mod.__all__) + list(numeric_mod.__all__) + list(categorical_mod.__all__)
        )
        assert len(names) == len(set(names))


class TestMeasureEndToEnd:
    """Compute each measure that declares end-to-end cases through the real Pathway engine.

    The computation goes through the production helper ``build_measure_dag`` (the same
    two-phase reduce/expression assembly the engine uses), so the test exercises the real
    contract rather than re-implementing it.
    """

    @pytest.mark.parametrize(
        "factory, data, expected, unordered",
        [
            (f, data, expected, unordered)
            for (f, data, expected, unordered, _id) in _END_TO_END_CASES
        ],
        ids=[_id for (_f, _data, _expected, _unordered, _id) in _END_TO_END_CASES],
    )
    def test_computed_result(self, factory, data, expected, unordered):
        measure = factory()
        table = pw.debug.table_from_pandas(pd.DataFrame({"x": data}))
        result_table = build_measure_dag(table, measure)
        result = pw.debug.table_to_pandas(result_table)["result"].iloc[0]

        if isinstance(expected, float):
            assert result == pytest.approx(expected)
        elif unordered:
            assert sorted(result) == sorted(expected)
        else:
            assert result == expected
