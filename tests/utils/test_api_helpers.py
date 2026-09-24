"""Tests for the route-helper validation logic that remains in ``utils/api.py``."""

from types import SimpleNamespace

import pytest

from streamdaq.utils.api import _validate_for_start


class TestValidateForStart:
    def _config(self, **overrides):
        base = dict(
            input=object(),
            output=object(),
            windowby_column="ts",
            window_checks_config=SimpleNamespace(checks=[object()]),
            instant_checks=[],
        )
        base.update(overrides)
        return SimpleNamespace(**base)

    def test_complete_config_has_no_errors(self):
        assert _validate_for_start(self._config()) == []

    @pytest.mark.parametrize(
        "override, expected_error",
        [
            (dict(input=None), "Input configuration is required."),
            (dict(output=None), "Output configuration is required."),
            (dict(windowby_column=None), "Windowby column is required."),
            (dict(window_checks_config=None), "Window configuration is required."),
        ],
    )
    def test_each_missing_field_reported(self, override, expected_error):
        errors = _validate_for_start(self._config(**override))
        assert expected_error in errors

    def test_requires_at_least_one_check(self):
        config = self._config(instant_checks=[], window_checks_config=SimpleNamespace(checks=[]))
        errors = _validate_for_start(config)
        assert "At least one instant check or window check is required." in errors

    def test_instant_check_alone_satisfies_check_requirement(self):
        config = self._config(
            instant_checks=[object()], window_checks_config=SimpleNamespace(checks=[])
        )
        errors = _validate_for_start(config)
        assert "At least one instant check or window check is required." not in errors
