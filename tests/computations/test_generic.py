import math

import pytest

from streamdaq.computations.generic import (
    calculate_correlation,
    compute_constancy,
    count_singletons,
    is_monotonic,
    most_frequent_elements,
    set_conformance_count,
)
from streamdaq.utils.correlation_method import CorrelationMethod


class TestSetConformanceCount:
    def test_partial_match(self):
        assert set_conformance_count([1, 2, 3, 4], [2, 4, 6]) == 2

    def test_all_match(self):
        assert set_conformance_count([1, 2, 3], [1, 2, 3, 4]) == 3

    def test_no_match(self):
        assert set_conformance_count([1, 2, 3], [4, 5, 6]) == 0

    def test_empty_elements(self):
        assert set_conformance_count([], [1, 2]) == 0

    def test_empty_allowed_values(self):
        assert set_conformance_count([1, 2, 3], []) == 0

    def test_single_element_match(self):
        assert set_conformance_count([5], [5, 10]) == 1

    def test_single_element_no_match(self):
        assert set_conformance_count([5], [10, 15]) == 0

    def test_with_duplicates_in_elements(self):
        assert set_conformance_count([1, 1, 2, 2, 3], [1, 2]) == 4

    @pytest.mark.parametrize(
        "elements, allowed, expected",
        [
            (["a", "b", "c"], ["a", "c"], 2),
            ([1.0, 2.0, 3.0], [2.0], 1),
            (["x", 1, 2.0], ["x", 2.0], 2),
        ],
    )
    def test_various_types(self, elements, allowed, expected):
        assert set_conformance_count(elements, allowed) == expected

    def test_scalar_element(self):
        assert set_conformance_count(5, [5, 10]) == 1

    def test_scalar_allowed(self):
        assert set_conformance_count([5, 10], 5) == 1


class TestMostFrequentElements:
    def test_single_winner(self):
        result = most_frequent_elements([1, 2, 2, 3])
        assert result == (2,)

    def test_multiple_winners(self):
        result = most_frequent_elements([1, 1, 2, 2, 3])
        assert set(result) == {1, 2}
        assert len(result) == 2

    def test_empty_input(self):
        assert most_frequent_elements([]) == ()

    def test_single_element(self):
        assert most_frequent_elements([42]) == (42,)

    def test_all_unique(self):
        result = most_frequent_elements([1, 2, 3])
        assert set(result) == {1, 2, 3}

    def test_all_same(self):
        assert most_frequent_elements([7, 7, 7]) == (7,)

    @pytest.mark.parametrize(
        "elements, expected",
        [
            (["a", "b", "a"], ("a",)),
            (["x", "y", "z", "x", "y"], ("x", "y")),
        ],
    )
    def test_with_strings(self, elements, expected):
        result = most_frequent_elements(elements)
        assert set(result) == set(expected)

    def test_scalar_input(self):
        assert most_frequent_elements(5) == (5,)


class TestCountSingletons:
    def test_mixed_elements(self):
        assert count_singletons([1, 2, 2, 3, 3, 3]) == 1

    def test_all_singletons(self):
        assert count_singletons([1, 2, 3, 4]) == 4

    def test_no_singletons(self):
        assert count_singletons([1, 1, 2, 2]) == 0

    def test_empty(self):
        assert count_singletons([]) == 0

    def test_single_element(self):
        assert count_singletons([42]) == 1

    @pytest.mark.parametrize(
        "elements, expected",
        [
            (["a", "b", "a", "c"], 2),
            ([1.0, 2.0, 1.0], 1),
            ([1, 1, 1], 0),
        ],
    )
    def test_parametrized(self, elements, expected):
        assert count_singletons(elements) == expected


class TestIsMonotonic:
    @pytest.mark.parametrize(
        "elements, direction, strict, expected",
        [
            ([1, 2, 3, 4], "asc", True, True),
            ([1, 2, 2, 3], "asc", True, False),
            ([1, 2, 2, 3], "asc", False, True),
            ([4, 3, 2, 1], "desc", True, True),
            ([4, 3, 3, 2], "desc", True, False),
            ([4, 3, 3, 2], "desc", False, True),
            ([4, 3, 2, 1], "asc", True, False),
            ([1, 2, 3], "desc", True, False),
            ([3, 3, 3], "asc", False, True),
            ([3, 3, 3], "desc", False, True),
        ],
    )
    def test_direction_strict_combinations(self, elements, direction, strict, expected):
        assert is_monotonic(elements, direction=direction, strict=strict) is expected

    def test_empty_returns_true(self):
        assert is_monotonic([]) is True

    def test_single_element_returns_true(self):
        assert is_monotonic([42]) is True

    def test_two_equal_strict_false(self):
        assert is_monotonic([5, 5], strict=False) is True

    def test_two_equal_strict_true(self):
        assert is_monotonic([5, 5], strict=True) is False

    def test_nan_in_sequence_returns_false(self):
        assert is_monotonic([1, float("nan"), 3]) is False

    def test_nan_at_start_returns_false(self):
        assert is_monotonic([float("nan"), 1, 2]) is False

    def test_nan_at_end_returns_false(self):
        assert is_monotonic([1, 2, float("nan")]) is False

    def test_single_nan_returns_false(self):
        assert is_monotonic([float("nan")]) is False

    def test_strings_asc(self):
        assert is_monotonic(["a", "b", "c"]) is True

    def test_strings_desc(self):
        assert is_monotonic(["c", "b", "a"], direction="desc") is True

    def test_floats_asc(self):
        assert is_monotonic([1.1, 2.2, 3.3]) is True

    def test_invalid_direction_raises(self):
        with pytest.raises(ValueError, match="must be 'asc' or 'desc'"):
            is_monotonic([1, 2, 3], direction="sideways")

    def test_range_input(self):
        assert is_monotonic(range(5)) is True


class TestComputeConstancy:
    @pytest.mark.parametrize(
        "elements, expected",
        [
            ([1, 2, 2, 3], 2),
            ([7, 7, 7], 3),
            ([1, 2, 3, 4], 1),
            ([], 0),
            ([42], 1),
            ([1, 1, 2, 2, 3], 2),
            (["a", "b", "a", "a"], 3),
            (5, 1),
        ],
        ids=[
            "single_dominant",
            "all_same",
            "all_unique",
            "empty",
            "single",
            "tie",
            "strings",
            "scalar",
        ],
    )
    def test_constancy(self, elements, expected):
        assert compute_constancy(elements) == expected


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

    def test_enum_method_param(self):
        result = calculate_correlation(
            [1, 2, 3, 4, 5], [2, 4, 6, 8, 10], method=CorrelationMethod.PEARSON
        )
        assert result == pytest.approx(1.0)

    def test_scalar_inputs_returns_nan(self):
        # Scalar inputs get wrapped by ensure_iterable into single-element lists,
        # which causes scipy to raise ValueError (need at least 2 observations)
        result = calculate_correlation(5, 10)
        assert math.isnan(result)
