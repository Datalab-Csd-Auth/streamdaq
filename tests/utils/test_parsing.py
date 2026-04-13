import pytest

from streamdaq.utils.parsing import (
    RangeExpr,
    extract_leading_integer,
    make_comparison_predicate,
    make_range_predicate,
    parse_comparison_expr,
    parse_range_expr,
    parse_threshold_expr,
)


class TestExtractLeadingInteger:
    @pytest.mark.parametrize(
        "text, expected",
        [
            ("42", 42),
            ("3 errors", 3),
            ("123abc456", 123),
            ("12 items processed", 12),
        ],
    )
    def test_happy_path(self, text, expected):
        assert extract_leading_integer(text) == expected

    def test_leading_whitespace_stripped(self):
        assert extract_leading_integer("  7 items") == 7

    def test_no_strip_whitespace(self):
        assert extract_leading_integer("  7", strip_whitespace=False) == 0

    def test_empty_string(self):
        assert extract_leading_integer("") == 0

    def test_custom_default(self):
        assert extract_leading_integer("", default=-1) == -1

    def test_no_leading_integer(self):
        assert extract_leading_integer("abc") == 0

    def test_whitespace_only(self):
        assert extract_leading_integer("   ") == 0

    def test_none_raises_type_error(self):
        with pytest.raises(TypeError, match="Expected str"):
            extract_leading_integer(None)

    def test_int_raises_type_error(self):
        with pytest.raises(TypeError, match="Expected str"):
            extract_leading_integer(123)

    def test_leading_zeros(self):
        assert extract_leading_integer("007bond") == 7

    def test_large_integer(self):
        assert extract_leading_integer("99999999999") == 99999999999


class TestParseComparisonExpr:
    @pytest.mark.parametrize(
        "expr, expected",
        [
            (">5", (">", 5.0)),
            ("<10", ("<", 10.0)),
            (">=100", (">=", 100.0)),
            ("<=0", ("<=", 0.0)),
            ("==42", ("==", 42.0)),
            ("!=0", ("!=", 0.0)),
            (">=-5", (">=", -5.0)),
            ("<-3.14", ("<", -3.14)),
            (">=3.14159", (">=", 3.14159)),
            (">1e10", (">", 1e10)),
            ("<1e-5", ("<", 1e-5)),
            ("  >= 10  ", (">=", 10.0)),
        ],
    )
    def test_valid_expressions(self, expr, expected):
        result = parse_comparison_expr(expr)
        assert result is not None
        assert result[0] == expected[0]
        assert result[1] == pytest.approx(expected[1])

    @pytest.mark.parametrize(
        "expr",
        ["", "10", "~=5", ">=", ">5abc", "invalid"],
    )
    def test_invalid_returns_none(self, expr):
        assert parse_comparison_expr(expr) is None

    def test_none_returns_none(self):
        assert parse_comparison_expr(None) is None

    def test_overflow_to_positive_infinity_returns_none(self):
        assert parse_comparison_expr(">=1e999") is None

    def test_overflow_to_negative_infinity_returns_none(self):
        assert parse_comparison_expr("<=-1e999") is None

    def test_non_string_returns_none(self):
        assert parse_comparison_expr(123) is None


class TestParseRangeExpr:
    @pytest.mark.parametrize(
        "expr, lower, upper, lower_inc, upper_inc",
        [
            ("[1,5]", 1.0, 5.0, True, True),
            ("(1,5)", 1.0, 5.0, False, False),
            ("(1,5]", 1.0, 5.0, False, True),
            ("[1,5)", 1.0, 5.0, True, False),
            ("[-10,-5]", -10.0, -5.0, True, True),
            ("[1.5,2.5]", 1.5, 2.5, True, True),
            ("  [ 1 , 5 ]  ", 1.0, 5.0, True, True),
            ("[5,5]", 5.0, 5.0, True, True),
        ],
    )
    def test_valid_ranges(self, expr, lower, upper, lower_inc, upper_inc):
        result = parse_range_expr(expr)
        assert result is not None
        assert result.lower == pytest.approx(lower)
        assert result.upper == pytest.approx(upper)
        assert result.lower_inclusive is lower_inc
        assert result.upper_inclusive is upper_inc

    def test_infinity_upper(self):
        result = parse_range_expr("[0, inf)")
        assert result is not None
        assert result.lower == 0.0
        assert result.upper == float("inf")
        assert result.upper_inclusive is False

    def test_infinity_lower(self):
        result = parse_range_expr("(-inf, 0]")
        assert result is not None
        assert result.lower == float("-inf")
        assert result.lower_inclusive is False

    def test_infinity_forced_exclusive(self):
        result = parse_range_expr("[0, inf]")
        assert result is not None
        assert result.upper_inclusive is False

    @pytest.mark.parametrize(
        "expr",
        [
            "[5,1]",
            "(5,5)",
            "[5,5)",
            "",
            "[1 5]",
            "{1,5}",
        ],
    )
    def test_invalid_returns_none(self, expr):
        assert parse_range_expr(expr) is None

    def test_none_returns_none(self):
        assert parse_range_expr(None) is None


class TestRangeExprContains:
    def test_inside_closed(self):
        r = RangeExpr(1, 5, True, True)
        assert r.contains(3) is True

    def test_at_lower_closed(self):
        assert RangeExpr(1, 5, True, True).contains(1) is True

    def test_at_upper_closed(self):
        assert RangeExpr(1, 5, True, True).contains(5) is True

    def test_at_lower_open(self):
        assert RangeExpr(1, 5, False, False).contains(1) is False

    def test_at_upper_open(self):
        assert RangeExpr(1, 5, False, False).contains(5) is False

    def test_outside_below(self):
        assert RangeExpr(1, 5, True, True).contains(0) is False

    def test_outside_above(self):
        assert RangeExpr(1, 5, True, True).contains(6) is False

    def test_nan_always_false(self):
        assert RangeExpr(-100, 100, True, True).contains(float("nan")) is False

    def test_infinity_upper_bound(self):
        r = RangeExpr(0, float("inf"), True, False)
        assert r.contains(1e308) is True

    def test_single_point(self):
        r = RangeExpr(5, 5, True, True)
        assert r.contains(5) is True
        assert r.contains(5.001) is False


class TestMakeComparisonPredicate:
    @pytest.mark.parametrize(
        "op, threshold, test_val, expected",
        [
            ("<", 10, 5, True),
            ("<", 10, 10, False),
            ("<=", 10, 10, True),
            ("<=", 10, 11, False),
            (">", 10, 15, True),
            (">", 10, 10, False),
            (">=", 10, 10, True),
            (">=", 10, 9, False),
            ("==", 10, 10, True),
            ("==", 10, 11, False),
            ("!=", 10, 5, True),
            ("!=", 10, 10, False),
        ],
    )
    def test_operators(self, op, threshold, test_val, expected):
        pred = make_comparison_predicate(op, threshold)
        assert pred(test_val) is expected

    def test_returns_callable(self):
        pred = make_comparison_predicate(">=", 5)
        assert callable(pred)
        assert pred(10) is True
        assert pred(3) is False

    def test_invalid_operator_raises(self):
        with pytest.raises(ValueError, match="Invalid operator"):
            make_comparison_predicate("~", 10)

    def test_non_numeric_threshold_raises(self):
        with pytest.raises(TypeError, match="threshold must be numeric"):
            make_comparison_predicate(">=", "10")


class TestMakeRangePredicate:
    @pytest.mark.parametrize(
        "lower, upper, incl_l, incl_u, val, expected",
        [
            (0, 10, True, True, 0, True),
            (0, 10, True, True, 10, True),
            (0, 10, True, True, 5, True),
            (0, 10, True, True, -1, False),
            (0, 10, True, True, 11, False),
            (0, 10, False, True, 0, False),
            (0, 10, True, False, 10, False),
            (0, 10, False, False, 5, True),
        ],
    )
    def test_boundary_behavior(self, lower, upper, incl_l, incl_u, val, expected):
        pred = make_range_predicate(lower, upper, incl_l, incl_u)
        assert pred(val) is expected

    def test_defaults_both_inclusive(self):
        pred = make_range_predicate(0, 10)
        assert pred(0) is True
        assert pred(10) is True

    def test_lower_greater_upper_raises(self):
        with pytest.raises(ValueError, match="lower bound.*must be <= upper"):
            make_range_predicate(10, 5)

    def test_equal_bounds_not_both_inclusive_raises(self):
        with pytest.raises(ValueError, match="equal bounds"):
            make_range_predicate(5, 5, inclusive_lower=True, inclusive_upper=False)

    def test_non_numeric_raises(self):
        with pytest.raises(TypeError, match="must be numeric"):
            make_range_predicate("0", 10)


class TestParseThresholdExpr:
    @pytest.mark.parametrize(
        "expr, test_val, expected",
        [
            (">= 10", 10, True),
            (">= 10", 9, False),
            ("< 5", 4, True),
            ("< 5", 5, False),
            ("== 100", 100, True),
            ("!= 0", 1, True),
            ("[0, 10]", 5, True),
            ("[0, 10]", 11, False),
            ("(0, 10)", 0, False),
            ("[0, 10)", 10, False),
            ("[-10, -5]", -7, True),
        ],
    )
    def test_valid_expressions(self, expr, test_val, expected):
        pred = parse_threshold_expr(expr)
        assert pred(test_val) is expected

    def test_strict_raises_on_invalid(self):
        with pytest.raises(ValueError, match="Unable to parse"):
            parse_threshold_expr("invalid")

    def test_strict_raises_on_empty(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            parse_threshold_expr("")

    def test_non_strict_returns_none_on_invalid(self):
        assert parse_threshold_expr("invalid", strict=False) is None

    def test_non_strict_returns_none_on_empty(self):
        assert parse_threshold_expr("", strict=False) is None

    def test_non_strict_still_parses_valid(self):
        pred = parse_threshold_expr(">= 10", strict=False)
        assert pred is not None
        assert pred(10) is True

    def test_non_string_raises_type_error(self):
        with pytest.raises(TypeError, match="must be a string"):
            parse_threshold_expr(123)

    def test_type_error_regardless_of_strict(self):
        with pytest.raises(TypeError):
            parse_threshold_expr(123, strict=False)

    def test_returns_reusable_callable(self):
        pred = parse_threshold_expr("[0, 100]")
        results = [pred(x) for x in [-1, 0, 50, 100, 101]]
        assert results == [False, True, True, True, False]
