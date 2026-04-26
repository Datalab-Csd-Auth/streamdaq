import math

import numpy as np
import pytest

from streamdaq.computations.numeric import (
    calculate_correlation,
    compute_above_mean_count,
    digit_count,
    filter_numeric,
    first_digit,
    first_digit_frequencies,
    fraction,
    fractional_part,
    fractional_part_digit_count,
    integer_part,
    integer_part_digit_count,
    is_greater_than,
    linear_slope,
    percentiles_dict,
    range_conformance_count,
)


class TestIsGreaterThan:
    @pytest.mark.parametrize(
        "a, b, or_equal, expected",
        [
            (5, 3, False, True),
            (3, 5, False, False),
            (5, 5, False, False),
            (5, 5, True, True),
            (5, 3, True, True),
            (3, 5, True, False),
            (-1, -2, False, True),
            (-2, -1, False, False),
            (0, 0, False, False),
            (0, 0, True, True),
            (1.5, 1.4, False, True),
            (0, -1, False, True),
        ],
    )
    def test_parametrized(self, a, b, or_equal, expected):
        assert is_greater_than(a, b, or_equal) is expected


class TestFraction:
    def test_simple_division(self):
        assert fraction(10, 3) == pytest.approx(3.3333333333)

    def test_precision_none(self):
        result = fraction(1, 3)
        assert result == pytest.approx(0.3333333333)

    def test_precision_two(self):
        assert fraction(1, 3, precision=2) == 0.33

    def test_precision_zero(self):
        assert fraction(1, 3, precision=0) == 0.0

    def test_negative_numerator(self):
        assert fraction(-10, 2) == -5.0

    def test_negative_denominator(self):
        assert fraction(10, -2) == -5.0

    def test_both_negative(self):
        assert fraction(-10, -2) == 5.0

    def test_zero_numerator(self):
        assert fraction(0, 5) == 0.0

    def test_zero_denominator_raises(self):
        with pytest.raises(ZeroDivisionError, match="denominator must not be zero"):
            fraction(1, 0)

    @pytest.mark.parametrize(
        "num, den, prec, expected",
        [
            (2, 3, 1, 0.7),
            (2, 3, 3, 0.667),
            (1, 7, 4, 0.1429),
            (22, 7, 5, 3.14286),
        ],
    )
    def test_precision_rounding(self, num, den, prec, expected):
        assert fraction(num, den, precision=prec) == expected


class TestRangeConformanceCount:
    def test_exclusive_both(self):
        assert range_conformance_count([1, 2, 3, 4, 5], 1, 5) == 3

    def test_inclusive_low(self):
        assert range_conformance_count([1, 2, 3, 4, 5], 1, 5, inclusive_low=True) == 4

    def test_inclusive_high(self):
        assert range_conformance_count([1, 2, 3, 4, 5], 1, 5, inclusive_high=True) == 4

    def test_both_inclusive(self):
        result = range_conformance_count(
            [1, 2, 3, 4, 5], 1, 5, inclusive_low=True, inclusive_high=True
        )
        assert result == 5

    def test_empty_elements(self):
        assert range_conformance_count([], 0, 10) == 0

    def test_all_in_range(self):
        assert range_conformance_count([2, 3, 4], 1, 5) == 3

    def test_none_in_range(self):
        assert range_conformance_count([10, 20, 30], 1, 5) == 0

    def test_boundary_values_exclusive(self):
        assert range_conformance_count([1, 5], 1, 5) == 0

    def test_boundary_values_inclusive(self):
        result = range_conformance_count([1, 5], 1, 5, inclusive_low=True, inclusive_high=True)
        assert result == 2

    def test_invalid_range_raises(self):
        with pytest.raises(ValueError, match="low .* must be <= high"):
            range_conformance_count([1, 2, 3], 10, 1)

    def test_equal_low_high_exclusive(self):
        assert range_conformance_count([5], 5, 5) == 0

    def test_equal_low_high_inclusive(self):
        result = range_conformance_count([5], 5, 5, inclusive_low=True, inclusive_high=True)
        assert result == 1


class TestPercentilesDict:
    def test_standard_percentiles(self):
        data = list(range(1, 101))
        result = percentiles_dict(data, [25, 50, 75])
        assert result[50] == pytest.approx(50.5)
        assert 25 in result and 75 in result

    def test_with_precision(self):
        result = percentiles_dict([1, 2, 3, 4, 5], [50], precision=2)
        assert result[50] == pytest.approx(3.0)

    def test_single_element(self):
        result = percentiles_dict([42], [0, 50, 100])
        assert result[0] == pytest.approx(42.0)
        assert result[50] == pytest.approx(42.0)
        assert result[100] == pytest.approx(42.0)

    def test_single_percentile(self):
        result = percentiles_dict([1, 2, 3], [50])
        assert len(result) == 1
        assert 50 in result

    def test_zero_percentile(self):
        result = percentiles_dict([5, 10, 15], [0])
        assert result[0] == pytest.approx(5.0)

    def test_hundred_percentile(self):
        result = percentiles_dict([5, 10, 15], [100])
        assert result[100] == pytest.approx(15.0)

    @pytest.mark.parametrize("precision", [0, 1, 2, 4])
    def test_precision_levels(self, precision):
        result = percentiles_dict([1, 2, 3, 4, 5, 6, 7], [33], precision=precision)
        value = result[33]
        if precision == 0:
            assert value == round(value, 0)
        else:
            rounded = round(float(value), precision)
            assert float(value) == pytest.approx(rounded)


class TestFirstDigit:
    def test_positive_integers(self):
        assert first_digit([123, 456, 789]) == [1, 4, 7]

    def test_positive_floats(self):
        assert first_digit([1.23, 4.56]) == [1, 4]

    def test_negative_numbers(self):
        assert first_digit([-123, -456]) == [1, 4]

    def test_single_digits(self):
        assert first_digit([5, 7, 9]) == [5, 7, 9]

    def test_zero(self):
        assert first_digit([0]) == [0]

    def test_small_fractions(self):
        assert first_digit([0.5, 0.9]) == [5, 9]

    def test_infinity_raises(self):
        with pytest.raises(ValueError, match="Cannot extract first digit"):
            first_digit([float("inf")])

    def test_nan_raises(self):
        with pytest.raises(ValueError, match="Cannot extract first digit"):
            first_digit([float("nan")])

    def test_neg_infinity_raises(self):
        with pytest.raises(ValueError, match="Cannot extract first digit"):
            first_digit([float("-inf")])

    @pytest.mark.parametrize(
        "number, expected",
        [
            (100, 1),
            (999, 9),
            (0.001, 1),
            (50.5, 5),
        ],
    )
    def test_various_numbers(self, number, expected):
        assert first_digit([number]) == [expected]


class TestIntegerPart:
    def test_positive_floats(self):
        assert integer_part([1.5, 2.7, 3.9]) == [1, 2, 3]

    def test_negative_floats(self):
        assert integer_part([-1.5, -2.7]) == [-1, -2]

    def test_integers(self):
        assert integer_part([1, 2, 3]) == [1, 2, 3]

    def test_zero(self):
        assert integer_part([0, 0.0]) == [0, 0]

    def test_small_fractions(self):
        assert integer_part([0.1, 0.9]) == [0, 0]

    def test_large_numbers(self):
        assert integer_part([1e10, 1e15]) == [int(1e10), int(1e15)]

    @pytest.mark.parametrize(
        "value, expected",
        [
            (3.14, 3),
            (-0.5, 0),
            (99.99, 99),
            (0.0, 0),
        ],
    )
    def test_various_floats(self, value, expected):
        assert integer_part([value]) == [expected]


class TestFractionalPart:
    def test_simple_decimals(self):
        assert fractional_part([3.14, 2.5, 1.0]) == [14, 5, 0]

    def test_integer(self):
        assert fractional_part([5]) == [0]

    def test_zero(self):
        assert fractional_part([0, 0.0]) == [0, 0]

    def test_negative(self):
        assert fractional_part([-2.5, -3.14]) == [5, 14]

    def test_small_decimal(self):
        assert fractional_part([0.001]) == [1]

    def test_empty(self):
        assert fractional_part([]) == []

    def test_many_digits(self):
        assert fractional_part([3.14159]) == [14159]

    def test_infinity_raises(self):
        with pytest.raises(ValueError, match="Cannot extract fractional part"):
            fractional_part([float("inf")])

    def test_nan_raises(self):
        with pytest.raises(ValueError, match="Cannot extract fractional part"):
            fractional_part([float("nan")])


class TestDigitCount:
    @pytest.mark.parametrize(
        "numbers, expected",
        [
            ([5], [1]),
            ([42], [2]),
            ([1, 22, 333], [1, 2, 3]),
            ([0], [1]),
            ([0.0], [1]),
            ([-42], [2]),
            ([3.14], [1]),
        ],
    )
    def test_parametrized(self, numbers, expected):
        assert digit_count(numbers) == expected

    def test_empty(self):
        assert digit_count([]) == []

    def test_infinity_raises(self):
        with pytest.raises(ValueError, match="non-finite"):
            digit_count([float("inf")])

    def test_nan_raises(self):
        with pytest.raises(ValueError, match="non-finite"):
            digit_count([float("nan")])


class TestIntegerPartDigitCount:
    @pytest.mark.parametrize(
        "numbers, expected",
        [
            ([5], [1]),
            ([12345], [5]),
            ([3.14], [1]),
            ([0], [1]),
            ([0.0], [1]),
            ([-42], [2]),
            ([-999.99], [3]),
        ],
    )
    def test_parametrized(self, numbers, expected):
        assert integer_part_digit_count(numbers) == expected

    def test_empty(self):
        assert integer_part_digit_count([]) == []

    def test_inf_raises(self):
        with pytest.raises(ValueError, match="non-finite"):
            integer_part_digit_count([float("inf")])

    def test_nan_raises(self):
        with pytest.raises(ValueError, match="non-finite"):
            integer_part_digit_count([float("nan")])


class TestFractionalPartDigitCount:
    @pytest.mark.parametrize(
        "numbers, expected",
        [
            ([3.14], [2]),
            ([1.5], [1]),
            ([3.14159], [5]),
            ([5], [0]),
            ([5.0], [0]),
            ([0], [0]),
            ([-2.5], [1]),
            ([0.001], [3]),
        ],
    )
    def test_parametrized(self, numbers, expected):
        assert fractional_part_digit_count(numbers) == expected

    def test_empty(self):
        assert fractional_part_digit_count([]) == []

    def test_inf_raises(self):
        with pytest.raises(ValueError, match="non-finite"):
            fractional_part_digit_count([float("inf")])

    def test_nan_raises(self):
        with pytest.raises(ValueError, match="non-finite"):
            fractional_part_digit_count([float("nan")])


class TestFirstDigitFrequencies:
    def test_single_digit_dominance(self):
        result = first_digit_frequencies([11, 12, 19], precision=2)
        assert result[1] == (3, 1.0)
        assert result[2] == (0, 0.0)

    def test_mixed_digits(self):
        result = first_digit_frequencies([1, 2, 3, 4, 5], precision=1)
        for d in range(1, 6):
            assert result[d] == (1, 0.2)

    def test_precision_none(self):
        result = first_digit_frequencies([1, 2, 3])
        assert isinstance(result[1][1], float)

    def test_all_digits_present(self):
        result = first_digit_frequencies([100])
        assert len(result) == 10
        for d in range(10):
            assert d in result

    def test_zero_values(self):
        result = first_digit_frequencies([0, 0, 1], precision=2)
        assert result[0] == (2, 0.67)
        assert result[1] == (1, 0.33)

    def test_negative_numbers(self):
        result = first_digit_frequencies([-5, -50], precision=1)
        assert result[5] == (2, 1.0)


class TestFilterNumeric:
    def test_integers(self):
        assert filter_numeric([1, 2, 3]) == [1.0, 2.0, 3.0]

    def test_string_numbers(self):
        assert filter_numeric(["1", "2.5"]) == [1.0, 2.5]

    def test_skip_non_convertible(self):
        assert filter_numeric([1, "abc", None, 2]) == [1.0, 2.0]

    def test_skip_booleans(self):
        assert filter_numeric([True, False, 1, 0]) == [1.0, 0.0]

    def test_skip_numpy_booleans(self):
        assert filter_numeric([np.bool_(True), 1]) == [1.0]

    def test_nan_filtered_by_default(self):
        assert filter_numeric([1, float("nan"), 2]) == [1.0, 2.0]

    def test_nan_allowed(self):
        result = filter_numeric([1, float("nan")], allow_nan=True)
        assert len(result) == 2
        assert math.isnan(result[1])

    def test_inf_filtered_by_default(self):
        assert filter_numeric([1, float("inf"), float("-inf")]) == [1.0]

    def test_inf_allowed(self):
        result = filter_numeric([1, float("inf")], allow_inf=True)
        assert result == [1.0, float("inf")]

    def test_empty(self):
        assert filter_numeric([]) == []

    def test_all_invalid(self):
        assert filter_numeric(["a", None, object()]) == []

    def test_numpy_numeric_types(self):
        elements = [np.int32(1), np.int64(2), np.float32(3.5)]
        assert filter_numeric(elements) == [1.0, 2.0, 3.5]


class TestLinearSlope:
    def test_positive_slope(self):
        assert linear_slope([0, 1, 2], [0, 1, 2]) == pytest.approx(1.0)

    def test_negative_slope(self):
        assert linear_slope([2, 1, 0], [0, 1, 2]) == pytest.approx(-1.0)

    def test_zero_slope(self):
        assert linear_slope([5, 5, 5], [0, 1, 2]) == pytest.approx(0.0)

    def test_with_precision(self):
        result = linear_slope([0, 1, 2], [0, 1, 2], precision=2)
        assert result == 1.0

    def test_nonzero_start_timestamps(self):
        assert linear_slope([0, 1, 2], [100, 101, 102]) == pytest.approx(1.0)

    def test_single_point_returns_zero(self):
        assert linear_slope([5], [0]) == 0.0

    def test_empty_returns_zero(self):
        assert linear_slope([], []) == 0.0

    def test_zero_variance_timestamps(self):
        assert linear_slope([1, 2, 3], [5, 5, 5]) == 0.0

    def test_length_mismatch_raises(self):
        with pytest.raises(ValueError, match="same length"):
            linear_slope([1, 2, 3], [1, 2])

    def test_steep_slope(self):
        assert linear_slope([0, 10], [0, 1]) == pytest.approx(10.0)

    def test_fractional_slope(self):
        assert linear_slope([0, 0.5, 1], [0, 1, 2]) == pytest.approx(0.5)


class TestComputeAboveMeanCount:
    def test_normal_case(self):
        assert compute_above_mean_count([1, 2, 3, 4, 5]) == 2

    def test_all_above_mean(self):
        assert compute_above_mean_count([1, 1, 1, 100]) == 1

    def test_none_above_mean(self):
        assert compute_above_mean_count([5, 5, 5]) == 0

    def test_single_element(self):
        assert compute_above_mean_count([42]) == 0

    def test_floats(self):
        assert compute_above_mean_count([1.0, 2.0, 3.0]) == 1


class TestCalculateCorrelation:
    @pytest.mark.parametrize("method", ["pearson", "spearman", "kendall"])
    def test_perfect_positive(self, method):
        result = calculate_correlation([1, 2, 3, 4, 5], [2, 4, 6, 8, 10], method=method)
        assert result == pytest.approx(1.0)

    @pytest.mark.parametrize("method", ["pearson", "spearman", "kendall"])
    def test_perfect_negative(self, method):
        result = calculate_correlation([1, 2, 3, 4, 5], [10, 8, 6, 4, 2], method=method)
        assert result == pytest.approx(-1.0)

    def test_spearman_monotonic_nonlinear(self):
        result = calculate_correlation([1, 2, 3, 4, 5], [1, 4, 9, 16, 25], method="spearman")
        assert result == pytest.approx(1.0)

    def test_precision_rounding(self):
        result = calculate_correlation([1, 2, 3, 4], [1, 3, 2, 5], method="pearson", precision=2)
        assert result == round(result, 2)

    def test_empty_returns_nan(self):
        result = calculate_correlation([], [])
        assert math.isnan(result)

    @pytest.mark.filterwarnings("ignore: An input array is constant")
    def test_constant_array_returns_nan(self):
        result = calculate_correlation([5, 5, 5], [1, 2, 3])
        assert math.isnan(result)

    def test_invalid_method_raises(self):
        with pytest.raises(NotImplementedError, match="cosine"):
            calculate_correlation([1, 2], [3, 4], method="cosine")

    def test_cramer_smoke(self):
        result = calculate_correlation([0, 0, 1, 1], [0, 1, 0, 1], method="cramer")
        assert isinstance(result, float)

    def test_precision_none_no_rounding(self):
        result = calculate_correlation([1, 2, 3], [2, 4, 6], precision=None)
        assert result == pytest.approx(1.0)
