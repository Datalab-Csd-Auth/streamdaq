"""Tests for ``WindowDataQualityCheck`` ``must_be`` resolution."""

from streamdaq.checks.window.base import WindowDataQualityCheck
from streamdaq.custom import assessment
from streamdaq.measures.numeric.mean import Mean


class TestWindowCheckMustBeResolution:
    def test_registered_name_becomes_a_callable_predicate(self):
        @assessment(name="IsDropSpike")
        def _is_drop_spike(reading):
            return reading >= 2.0

        check = WindowDataQualityCheck(
            name="w", measure=Mean(column="value"), must_be="IsDropSpike"
        )

        assert callable(check.must_be)
        assert check.must_be(3.0) is True
        assert check.must_be(1.0) is False

    def test_none_passes_through(self):
        check = WindowDataQualityCheck(name="w", measure=Mean(column="value"), must_be=None)
        assert check.must_be is None

    def test_callable_passes_through_unchanged(self):
        def predicate(reading):
            return reading >= 2.0

        check = WindowDataQualityCheck(name="w", measure=Mean(column="value"), must_be=predicate)

        assert check.must_be is predicate
