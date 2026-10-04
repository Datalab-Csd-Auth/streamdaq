"""Tests for the ``@assessment`` decorator.

``assessment`` registers a user predicate under a name in ``ASSESSMENT_REGISTRY`` and
returns the original function so it stays importable and testable.
"""

import pytest

from streamdaq.assessments.registry import ASSESSMENT_REGISTRY
from streamdaq.custom import assessment


class TestCustomRegistration:
    """The decorator registers the predicate under the resolved assessment name."""

    def test_name_defaults_to_function_name(self):
        @assessment()
        def _is_drop_spike(reading):
            return reading >= 2.0

        assert "_is_drop_spike" in ASSESSMENT_REGISTRY

    def test_explicit_name_overrides_function_name(self):
        @assessment(name="IsDropSpike")
        def _source_function_name(reading):
            return reading >= 2.0

        assert "IsDropSpike" in ASSESSMENT_REGISTRY
        assert "_source_function_name" not in ASSESSMENT_REGISTRY

    def test_decorator_returns_the_original_function(self):
        def _is_drop_spike(reading):
            return reading >= 2.0

        decorated = assessment(name="IsDropSpike")(_is_drop_spike)

        assert decorated is _is_drop_spike


class TestRegisteredPredicate:
    """The registered predicate is a one-argument callable that runs the user logic."""

    @pytest.mark.parametrize(
        "reading, expected",
        [(3.0, True), (2.0, True), (1.0, False)],
    )
    def test_registered_predicate_evaluates_user_logic(self, reading, expected):
        @assessment(name="IsDropSpike")
        def _is_drop_spike(value):
            return value >= 2.0

        predicate = ASSESSMENT_REGISTRY["IsDropSpike"]

        assert predicate(reading) is expected


class TestCustomExports:
    """The public re-export chain resolves to a single decorator object."""

    def test_reexports_are_the_same_object(self):
        from streamdaq.custom import assessment as top_level
        from streamdaq.custom._assessments import assessment as subpackage
        from streamdaq.custom._assessments.decorator import assessment as origin

        assert top_level is subpackage is origin
