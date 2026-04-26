import pandas as pd
import pathway as pw
import pytest

import streamdaq.measures as measures_mod
import streamdaq.measures.any_column as any_column_mod
import streamdaq.measures.categorical as categorical_mod
import streamdaq.measures.numeric as numeric_mod

# any_column measures
from streamdaq.measures.any_column.availability import Availability
from streamdaq.measures.any_column.constancy import Constancy
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

# numeric measures
from streamdaq.measures.numeric.above_mean_count import AboveMeanCount
from streamdaq.measures.numeric.above_mean_fraction import AboveMeanFraction
from streamdaq.measures.numeric.best_line_fit_slope import BestLineFitSlope
from streamdaq.measures.numeric.correlation import Correlation
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
from streamdaq.measures.numeric.standard_deviation import StandardDeviation
from streamdaq.measures.numeric.sum import Sum
from streamdaq.utils.data_type_applicability import DataTypeApplicability


class TestAvailabilityValidation:
    def test_default_min_samples(self):
        m = Availability(column="x")
        assert m.min_samples == 1

    def test_custom_min_samples(self):
        m = Availability(column="x", min_samples=10)
        assert m.min_samples == 10

    def test_zero_raises(self):
        with pytest.raises(ValueError):
            Availability(column="x", min_samples=0)

    def test_negative_raises(self):
        with pytest.raises(ValueError):
            Availability(column="x", min_samples=-5)

    def test_error_message_includes_column(self):
        with pytest.raises(ValueError, match="column `my_col`"):
            Availability(column="my_col", min_samples=0)


class TestMonotonicValidation:
    def test_defaults(self):
        m = Monotonic(column="x")
        assert m.direction == "asc"
        assert m.strict is True

    def test_custom(self):
        m = Monotonic(column="x", direction="desc", strict=False)
        assert m.direction == "desc"
        assert m.strict is False

    def test_invalid_direction_raises(self):
        with pytest.raises(ValueError):
            Monotonic(column="x", direction="up")

    def test_case_sensitive(self):
        with pytest.raises(ValueError):
            Monotonic(column="x", direction="ASC")

    def test_error_message_includes_column(self):
        with pytest.raises(ValueError, match="column `my_col`"):
            Monotonic(column="my_col", direction="up")


class TestMissingCountDisguisedValues:
    def test_no_disguised(self):
        m = MissingCount(column="x")
        assert m._concatenate_explicit_diguised_values() == {None, ""}

    def test_with_disguised(self):
        m = MissingCount(column="x", disguised=["N/A", -999])
        assert m._concatenate_explicit_diguised_values() == {None, "", "N/A", -999}

    def test_deduplication(self):
        m = MissingCount(column="x", disguised=[None, ""])
        result = m._concatenate_explicit_diguised_values()
        assert result == {None, ""}

    def test_returns_set(self):
        m = MissingCount(column="x")
        assert isinstance(m._concatenate_explicit_diguised_values(), set)


class TestMissingFractionDisguisedValues:
    def test_no_disguised(self):
        m = MissingFraction(column="x")
        assert m._concatenate_explicit_diguised_values() == {None, ""}

    def test_with_disguised(self):
        m = MissingFraction(column="x", disguised=["N/A", -999])
        assert m._concatenate_explicit_diguised_values() == {None, "", "N/A", -999}

    def test_returns_set(self):
        m = MissingFraction(column="x")
        assert isinstance(m._concatenate_explicit_diguised_values(), set)


class TestCorrelationValidation:
    @pytest.mark.parametrize("method", ["pearson", "spearman", "kendall", "cramer"])
    def test_valid_methods(self, method):
        Correlation(column="x", other_column="y", method=method)

    def test_default_method(self):
        m = Correlation(column="x", other_column="y")
        assert m.method == "pearson"

    def test_invalid_method_raises(self):
        with pytest.raises(NotImplementedError):
            Correlation(column="x", other_column="y", method="invalid")


class TestFrozenNumbersValidation:
    def test_defaults(self):
        m = FrozenNumbers(column="x")
        assert m.epsilon == 0.0
        assert m.min_samples == 1

    def test_min_samples_zero_raises(self):
        with pytest.raises(ValueError):
            FrozenNumbers(column="x", min_samples=0)

    def test_negative_epsilon_abs(self):
        m = FrozenNumbers(column="x", epsilon=-0.5)
        assert m.epsilon == 0.5


class TestFrozenNumbersAreNumbersFrozen:
    def test_all_identical(self):
        m = FrozenNumbers(column="x", epsilon=0, min_samples=1)
        assert m._are_numbers_frozen((5, 5, 5, 5)) is True

    def test_below_min_samples(self):
        m = FrozenNumbers(column="x", epsilon=0, min_samples=10)
        assert m._are_numbers_frozen((5, 5, 5)) is False

    def test_range_within_epsilon(self):
        m = FrozenNumbers(column="x", epsilon=0.5, min_samples=1)
        assert m._are_numbers_frozen((1.0, 1.1, 1.2)) is True

    def test_range_exceeds_epsilon(self):
        m = FrozenNumbers(column="x", epsilon=0.5, min_samples=1)
        assert m._are_numbers_frozen((1.0, 1.1, 2.0)) is False

    def test_single_element(self):
        m = FrozenNumbers(column="x", epsilon=0, min_samples=1)
        assert m._are_numbers_frozen((42,)) is True

    def test_empty_below_min(self):
        m = FrozenNumbers(column="x", epsilon=0, min_samples=1)
        assert m._are_numbers_frozen(()) is False

    def test_exact_boundary(self):
        m = FrozenNumbers(column="x", epsilon=5, min_samples=1)
        assert m._are_numbers_frozen((0, 5)) is True

    def test_just_over_boundary(self):
        m = FrozenNumbers(column="x", epsilon=5, min_samples=1)
        assert m._are_numbers_frozen((0, 6)) is False

    def test_negative_numbers(self):
        m = FrozenNumbers(column="x", epsilon=8, min_samples=1)
        assert m._are_numbers_frozen((-10, -5, -3)) is True


class TestApplicabilityAttributes:
    @pytest.mark.parametrize(
        "cls",
        [
            Availability,
            Constancy,
            Count,
            DistinctCount,
            DistinctCountApprox,
            DistinctFraction,
            DistinctFractionApprox,
            DistinctPlaceholderCount,
            DistinctPlaceholderFraction,
            InSetCount,
            InSetFraction,
            Max,
            Min,
            MissingCount,
            MissingFraction,
            Monotonic,
            MostFrequent,
            Ndarray,
            SortedTupleTime,
            SortedTupleValue,
            Tuple,
            UniqueCount,
            UniqueFraction,
            UniqueOverDistinct,
            WindowDuration,
            # numeric with ANY_COLUMN
            AboveMeanFraction,
            BestLineFitSlope,
            Correlation,
            InRangeCount,
            InRangeFraction,
            Percentiles,
            # categorical with ANY_COLUMN
            RegexCount,
            RegexFraction,
        ],
        ids=lambda c: c.__name__,
    )
    def test_any_column(self, cls):
        assert cls._applicability == DataTypeApplicability.ANY_COLUMN

    @pytest.mark.parametrize(
        "cls",
        [
            AboveMeanCount,
            FirstDigitFreqs,
            FrozenNumbers,
            MaxFractionalPartLength,
            MaxIntegerPartLength,
            Mean,
            MeanFractionalPartLength,
            MeanIntegerPartLength,
            Median,
            MedianFractionalPartLength,
            MedianIntegerPartLength,
            MinFractionalPartLength,
            MinIntegerPartLength,
            StandardDeviation,
            Sum,
        ],
        ids=lambda c: c.__name__,
    )
    def test_numeric_only(self, cls):
        assert cls._applicability == DataTypeApplicability.NUMERIC_ONLY

    @pytest.mark.parametrize(
        "cls",
        [MaxLength, MeanLength, MedianLength, MinLength],
        ids=lambda c: c.__name__,
    )
    def test_categorical_only(self, cls):
        assert cls._applicability == DataTypeApplicability.CATEGORICAL_ONLY


class TestDependencies:
    @pytest.mark.parametrize(
        "cls, expected",
        [
            # any_column — no deps
            (Count, []),
            (Tuple, []),
            (SortedTupleValue, []),
            (SortedTupleTime, []),
            (Ndarray, []),
            (Max, []),
            (Min, []),
            (WindowDuration, []),
            # any_column — [Count]
            (Availability, [Count]),
            # any_column — [Tuple]
            (Constancy, [Tuple]),
            (DistinctCount, [Tuple]),
            (DistinctCountApprox, [Tuple]),
            (DistinctPlaceholderCount, [Tuple]),
            (InSetCount, [Tuple]),
            (Monotonic, [Tuple]),
            (MostFrequent, [Tuple]),
            (UniqueCount, [Tuple]),
            (UniqueOverDistinct, [Tuple]),
            # any_column — [Tuple, Count]
            (DistinctFraction, [Tuple, Count]),
            (DistinctFractionApprox, [Tuple, Count]),
            (DistinctPlaceholderFraction, [Tuple, Count]),
            (InSetFraction, [Tuple, Count]),
            (MissingCount, [Tuple]),
            (MissingFraction, [Tuple, Count]),
            (UniqueFraction, [Tuple, Count]),
            # numeric
            (AboveMeanCount, [Tuple]),
            (AboveMeanFraction, [Tuple, Count]),
            (BestLineFitSlope, [Tuple]),
            (Correlation, [Tuple]),
            (FirstDigitFreqs, [Tuple]),
            (FrozenNumbers, [SortedTupleValue]),
            (InRangeCount, [Tuple]),
            (InRangeFraction, [Tuple, Count]),
            (MaxFractionalPartLength, [Tuple]),
            (MaxIntegerPartLength, [Tuple]),
            (Mean, []),
            (MeanFractionalPartLength, [Tuple]),
            (MeanIntegerPartLength, [Tuple]),
            (Median, []),
            (MedianFractionalPartLength, [Tuple]),
            (MedianIntegerPartLength, [Tuple]),
            (MinFractionalPartLength, []),
            (MinIntegerPartLength, []),
            (Percentiles, [Tuple]),
            (StandardDeviation, []),
            (Sum, []),
            # categorical
            (MaxLength, []),
            (MeanLength, []),
            (MedianLength, []),
            (MinLength, [Tuple]),
            (RegexCount, [Tuple]),
            (RegexFraction, [Tuple, Count]),
        ],
        ids=lambda x: x.__name__ if isinstance(x, type) else "",
    )
    def test_dependencies(self, cls, expected):
        assert cls._dependencies == expected


class TestStandardDeviationExport:
    def test_in_numeric_all(self):
        assert "StandardDeviation" in numeric_mod.__all__

    def test_in_measures_all(self):
        assert "StandardDeviation" in measures_mod.__all__


class TestInitExports:
    def test_measures_init_all(self):
        assert isinstance(measures_mod.__all__, list)
        assert "Availability" in measures_mod.__all__
        assert "DataQualityMeasure" in measures_mod.__all__

    def test_any_column_init_all(self):
        assert isinstance(any_column_mod.__all__, list)
        assert "Availability" in any_column_mod.__all__
        assert len(any_column_mod.__all__) == 25

    def test_categorical_init_all(self):
        assert isinstance(categorical_mod.__all__, list)
        assert "RegexCount" in categorical_mod.__all__
        assert len(categorical_mod.__all__) == 6

    def test_numeric_init_all(self):
        assert isinstance(numeric_mod.__all__, list)
        assert "FrozenNumbers" in numeric_mod.__all__
        assert len(numeric_mod.__all__) == 21


class TestGetReducerSmoke:
    """Call get_reducer() on every measure class to verify no crashes under mocked pathway."""

    @pytest.mark.parametrize(
        "measure_cls, kwargs",
        [
            # any_column — plain
            (Availability, dict(column="x")),
            (Constancy, dict(column="x")),
            (Count, dict(column="x")),
            (DistinctCount, dict(column="x")),
            (DistinctCountApprox, dict(column="x")),
            (DistinctPlaceholderCount, dict(column="x", placeholders=["N/A"])),
            (InSetCount, dict(column="x", allowed_values={"a"})),
            (Max, dict(column="x")),
            (Min, dict(column="x")),
            (MissingCount, dict(column="x")),
            (Monotonic, dict(column="x")),
            (MostFrequent, dict(column="x")),
            (Ndarray, dict(column="x")),
            (SortedTupleTime, dict(column="x")),
            (SortedTupleValue, dict(column="x")),
            (Tuple, dict(column="x")),
            (UniqueCount, dict(column="x")),
            (WindowDuration, dict(column="x")),
            # any_column — roundable (precision=None)
            (DistinctFraction, dict(column="x")),
            (DistinctFractionApprox, dict(column="x")),
            (DistinctPlaceholderFraction, dict(column="x", placeholders=["N/A"])),
            (InSetFraction, dict(column="x", allowed_values={"a"})),
            (MissingFraction, dict(column="x")),
            (UniqueFraction, dict(column="x")),
            (UniqueOverDistinct, dict(column="x")),
            # any_column — roundable (precision=2)
            (DistinctFraction, dict(column="x", precision=2)),
            (DistinctFractionApprox, dict(column="x", precision=2)),
            (DistinctPlaceholderFraction, dict(column="x", placeholders=["N/A"], precision=2)),
            (InSetFraction, dict(column="x", allowed_values={"a"}, precision=2)),
            (MissingFraction, dict(column="x", precision=2)),
            (UniqueFraction, dict(column="x", precision=2)),
            (UniqueOverDistinct, dict(column="x", precision=2)),
            # numeric — plain
            (AboveMeanCount, dict(column="x")),
            (FrozenNumbers, dict(column="x")),
            (InRangeCount, dict(column="x", low=0, high=100)),
            (MaxFractionalPartLength, dict(column="x")),
            (MaxIntegerPartLength, dict(column="x")),
            (MeanFractionalPartLength, dict(column="x")),
            (MeanIntegerPartLength, dict(column="x")),
            (Median, dict(column="x")),
            (MedianFractionalPartLength, dict(column="x")),
            (MedianIntegerPartLength, dict(column="x")),
            (MinFractionalPartLength, dict(column="x")),
            (MinIntegerPartLength, dict(column="x")),
            # numeric — roundable (precision=None)
            (AboveMeanFraction, dict(column="x")),
            (BestLineFitSlope, dict(column="x", time_column="t")),
            (Correlation, dict(column="x", other_column="y")),
            (FirstDigitFreqs, dict(column="x")),
            (InRangeFraction, dict(column="x", low=0, high=100)),
            (Mean, dict(column="x")),
            (Percentiles, dict(column="x")),
            (StandardDeviation, dict(column="x")),
            (Sum, dict(column="x")),
            # numeric — roundable (precision=2)
            (AboveMeanFraction, dict(column="x", precision=2)),
            (BestLineFitSlope, dict(column="x", time_column="t", precision=2)),
            (Correlation, dict(column="x", other_column="y", precision=2)),
            (FirstDigitFreqs, dict(column="x", precision=2)),
            (InRangeFraction, dict(column="x", low=0, high=100, precision=2)),
            (Mean, dict(column="x", precision=2)),
            (Percentiles, dict(column="x", precision=2)),
            (StandardDeviation, dict(column="x", precision=2)),
            (Sum, dict(column="x", precision=2)),
            # categorical — plain
            (MaxLength, dict(column="x")),
            (MeanLength, dict(column="x")),
            (MedianLength, dict(column="x")),
            (MinLength, dict(column="x")),
            (RegexCount, dict(column="x", regex=r"^\d+$")),
            # categorical — roundable
            (RegexFraction, dict(column="x", regex=r"^\d+$")),
            (RegexFraction, dict(column="x", regex=r"^\d+$", precision=2)),
        ],
        ids=lambda x: x.__name__ if isinstance(x, type) else "",
    )
    def test_get_reducer_does_not_raise(self, measure_cls, kwargs):
        measure = measure_cls(**kwargs)
        result = measure.get_reducer()
        assert result is not None


def _compute_measure(measure, data, column="x"):
    """Run a measure through a real Pathway reduce pipeline and return the scalar result."""
    t = pw.debug.table_from_pandas(pd.DataFrame({column: data}))

    # Resolve dependency shared columns
    dep_kwargs = {}
    for dep_cls in measure._dependencies:
        dep = dep_cls(column=column)
        col_name = dep_cls._get_internal_shared_column_name(column)
        dep_kwargs[col_name] = dep.get_reducer()

    if dep_kwargs:
        step1 = t.reduce(**dep_kwargs)
        result = step1.select(result=measure.get_reducer())
    else:
        result = t.reduce(result=measure.get_reducer())

    return pw.debug.table_to_pandas(result)["result"].iloc[0]


class TestMeasureEndToEnd:
    """Verify actual computed results through real Pathway engine."""

    @pytest.mark.parametrize(
        "measure, data, expected",
        [
            # Measures without dependencies
            (Count(column="x"), [10, 20, 10, 30], 4),
            (Mean(column="x"), [10, 20, 30], 20.0),
            (Mean(column="x"), [1, 3, 3], 2.333333333333333),
            (Mean(column="x", precision=4), [1, 3, 3], 2.3333),
            (Sum(column="x"), [10, 20, 30], 60),
            (Median(column="x"), [10, 20, 30, 40], 25.0),
            # Measures that depend on Tuple
            (DistinctCount(column="x"), [10, 20, 10, 30], 3),
            (Constancy(column="x"), [1, 1, 2, 3], 2),
            (UniqueCount(column="x"), [1, 1, 2, 3], 2),
            (Monotonic(column="x", strict=False), [5, 5, 5, 5], True),
            (Monotonic(column="x", direction="desc", strict=False), [3, 3, 3], True),
            (Monotonic(column="x", direction="desc", strict=True), [3, 3, 3], False),
            (InSetCount(column="x", allowed_values={10, 30}), [10, 20, 10, 30], 3),
            (MissingCount(column="x"), [1, None, "", 4], 2),
            (MinLength(column="x"), ["hello", "hi", "world"], 2),
            (RegexCount(column="x", regex=r"^\d+$"), ["123", "abc", "456"], 2),
            # Measures that depend on Count
            (Availability(column="x"), [1, 2, 3], True),
            (Availability(column="x", min_samples=10), [1, 2, 3], False),
            # Measures that depend on Tuple and Count
            (DistinctFraction(column="x"), [10, 20, 10, 30], 0.75),
            (MissingFraction(column="x"), [1, None, "", 4], 0.5),
            (UniqueFraction(column="x"), [1, 1, 2, 3], 0.5),
            # Measures that depend on SortedTupleValue
            (FrozenNumbers(column="x", epsilon=0), [5, 5, 5], True),
            (FrozenNumbers(column="x", epsilon=0), [1, 2, 3], False),
            (FrozenNumbers(column="x", epsilon=5), [1, 3, 5], True),
        ],
        ids=lambda x: x.__class__.__name__ if hasattr(x, "get_reducer") else "",
    )
    def test_computed_result(self, measure, data, expected):
        result = _compute_measure(measure, data)
        if isinstance(expected, float):
            assert result == pytest.approx(expected)
        else:
            assert result == expected
