"""Tests for the ``must_be`` expression parser used by window checks.

``string_to_callable`` turns declarative condition strings such as ``">=2"`` or ``"[1, 4]"``
into predicate callables using regex parsing (no ``eval``).
"""

import pytest

from streamdaq.custom import assessment
from streamdaq.translators.string_to_callable import resolve_must_be, string_to_callable


class TestComparisonExpressions:
    @pytest.mark.parametrize(
        "expr, satisfied, not_satisfied",
        [
            (">=10", 10, 9),
            ("<=10", 10, 11),
            ("==5", 5, 6),
            (">0", 1, 0),
            ("<5.5", 5.4, 5.5),
        ],
    )
    def test_comparison_predicates(self, expr, satisfied, not_satisfied):
        predicate = string_to_callable(expr)
        assert predicate(satisfied) is True
        assert predicate(not_satisfied) is False

    def test_whitespace_is_tolerated(self):
        predicate = string_to_callable("  >= 3 ")
        assert predicate(3) is True
        assert predicate(2) is False


class TestRangeExpressions:
    @pytest.mark.parametrize(
        "expr, inside, outside",
        [
            ("[1,5]", 1, 0),
            ("[1,5]", 5, 6),
            ("(1,5)", 3, 1),
            ("(1,5)", 4, 5),
            ("[1.5, 2.5]", 2.0, 3.0),
        ],
    )
    def test_range_predicates(self, expr, inside, outside):
        predicate = string_to_callable(expr)
        assert predicate(inside) is True
        assert predicate(outside) is False

    def test_mixed_inclusive_exclusive_bounds(self):
        predicate = string_to_callable("[1,5)")
        assert predicate(1) is True
        assert predicate(5) is False


class TestInvalidExpressions:
    @pytest.mark.parametrize("expr", ["", "garbage", "??", None, 42, ">=abc"])
    def test_unparseable_expression_raises(self, expr):
        with pytest.raises(ValueError, match="Cannot construct check function"):
            string_to_callable(expr)

    @pytest.mark.parametrize("expr", ["[5,1]", "[3,3]"])
    def test_inverted_or_empty_range_raises(self, expr):
        with pytest.raises(ValueError, match="Cannot construct check function"):
            string_to_callable(expr)


class TestResolveMustBe:
    def test_callable_is_returned_unchanged(self):
        def predicate(value):
            return value > 0

        assert resolve_must_be(predicate) is predicate

    @pytest.mark.parametrize(
        "expr, satisfied, not_satisfied",
        [
            (">= 2", 3, 1),
            ("<= 10", 10, 11),
            ("[1, 5]", 1, 6),
            ("[1, 5]", 5, 0),
            ("(1, 5)", 4, 5),
            ("(1, 5)", 4, 1),
        ],
    )
    def test_grammar_strings_still_parse(self, expr, satisfied, not_satisfied):
        predicate = resolve_must_be(expr)
        assert predicate(satisfied) is True
        assert predicate(not_satisfied) is False

    def test_registered_name_resolves_to_its_predicate(self):
        @assessment(name="IsDropSpike")
        def _is_drop_spike(reading):
            return reading >= 2.0

        predicate = resolve_must_be("IsDropSpike")

        assert predicate(3.0) is True
        assert predicate(1.0) is False

    @pytest.mark.parametrize("unknown", ["unknown", "not_registered", "??"])
    def test_unknown_string_raises_valueerror_mentioning_both_paths(self, unknown):
        with pytest.raises(ValueError) as exc_info:
            resolve_must_be(unknown)

        message = str(exc_info.value)
        assert "registered assessment" in message
        assert "comparison/range expression" in message
