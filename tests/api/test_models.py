import pytest
from fastapi import HTTPException

from streamdaq.api.models import (
    InputConfig,
    InstantCheckConfig,
    MeasureConfig,
    OutputConfig,
    TaskConfig,
    WindowCheckConfig,
    WindowChecksConfig,
    WindowConfig,
)
from streamdaq.custom import assessment


def test_measure_config_valid():
    config = MeasureConfig(type="Mean", params={"column": "temperature"})
    assert config.type == "Mean"
    assert config.params["column"] == "temperature"


def test_measure_config_invalid_type():
    with pytest.raises(HTTPException) as exc_info:
        MeasureConfig(type="NonExistentType", params={})
    assert exc_info.value.status_code == 400


def test_measure_config_invalid_params():
    with pytest.raises(HTTPException) as exc_info:
        # InRangeCount requires low and high, passing something wrong
        MeasureConfig(type="InRangeCount", params={"column": "age", "low": "not_a_number"})
    assert exc_info.value.status_code == 400
    assert "Invalid params for InRangeCount" in exc_info.value.detail


def test_instant_check_config_valid():
    config = InstantCheckConfig(
        name="Valid Age", check_class="InRange", params={"column": "age", "low": 0, "high": 120}
    )
    assert config.name == "Valid Age"
    assert config.check_class == "InRange"
    assert config.params["column"] == "age"
    assert config.params["low"] == 0
    assert config.params["high"] == 120


def test_instant_check_config_invalid_check_class():
    with pytest.raises(HTTPException) as exc_info:
        InstantCheckConfig(name="Bad Check", check_class="NonExistent", params={})
    assert exc_info.value.status_code == 400


def test_instant_check_config_invalid_params():
    with pytest.raises(HTTPException) as exc_info:
        InstantCheckConfig(
            name="Bad Params",
            check_class="InRange",
            params={"column": "age"},  # Missing low and high
        )
    assert exc_info.value.status_code == 400
    assert "Invalid params for InRange" in exc_info.value.detail


def _mean_measure() -> MeasureConfig:
    return MeasureConfig(type="Mean", params={"column": "value"})


class TestWindowCheckConfigMustBe:
    """``WindowCheckConfig`` validates ``must_be`` through the resolver without mutating it."""

    def test_none_is_allowed(self):
        config = WindowCheckConfig(name="w", measure=_mean_measure(), must_be=None)
        assert config.must_be is None

    @pytest.mark.parametrize("expr", [">= 2", "[1, 5]"])
    def test_valid_grammar_is_accepted_and_kept_verbatim(self, expr):
        config = WindowCheckConfig(name="w", measure=_mean_measure(), must_be=expr)
        assert config.must_be == expr

    def test_registered_name_is_accepted_and_kept_verbatim(self):
        @assessment(name="IsDropSpike")
        def _is_drop_spike(reading):
            return reading >= 2.0

        config = WindowCheckConfig(name="w", measure=_mean_measure(), must_be="IsDropSpike")

        assert config.must_be == "IsDropSpike"

    def test_unknown_name_raises_http_400_mentioning_both_paths(self):
        with pytest.raises(HTTPException) as exc_info:
            WindowCheckConfig(name="w", measure=_mean_measure(), must_be="unknown")

        assert exc_info.value.status_code == 400
        assert "registered assessment" in exc_info.value.detail
        assert "comparison/range expression" in exc_info.value.detail


class TestInstantCheckConfigMustBe:
    """A bad ``must_be`` inside instant-check params surfaces as HTTP 400."""

    @pytest.mark.parametrize("check_class", ["Value", "Length"])
    def test_unknown_must_be_raises_http_400(self, check_class):
        with pytest.raises(HTTPException) as exc_info:
            InstantCheckConfig(
                name="v",
                check_class=check_class,
                params={"column": "value", "must_be": "unknown"},
            )

        assert exc_info.value.status_code == 400

    @pytest.mark.parametrize("check_class", ["Value", "Length"])
    def test_valid_grammar_must_be_is_accepted(self, check_class):
        config = InstantCheckConfig(
            name="v",
            check_class=check_class,
            params={"column": "value", "must_be": ">= 2"},
        )

        assert config.params["must_be"] == ">= 2"


def _window_check() -> WindowCheckConfig:
    return WindowCheckConfig(
        name="w",
        measure=MeasureConfig(type="Mean", params={"column": "a"}),
        must_be="[0, 1]",
    )


def _window_checks_config(*checks) -> WindowChecksConfig:
    return WindowChecksConfig(
        window=WindowConfig(type="tumbling", params={"duration": 5}), checks=list(checks)
    )


def _instant_check() -> InstantCheckConfig:
    return InstantCheckConfig(
        name="r", check_class="InRange", params={"column": "a", "low": 0, "high": 1}
    )


class TestTaskConfigStartabilityValidation:
    """``TaskConfig`` validates startability at construction with rich 422 messages.

    Valid shapes: instant-only (no windowby, no window checks), window-only (windowby + window
    checks), or both. A windowby column and window checks are coupled: neither is allowed
    without the other.
    """

    def _config_kwargs(self, **overrides) -> dict:
        base = dict(
            name="t",
            windowby_column="ts",
            input=InputConfig(type="csv", params={"path": "/tmp/x.csv"}),
            output=OutputConfig(type="jsonlines", params={"filename": "o.jsonl"}),
            instant_checks=[_instant_check()],
            window_checks_config=_window_checks_config(_window_check()),
        )
        base.update(overrides)
        return base

    def test_both_instant_and_window_is_accepted(self):
        config = TaskConfig(**self._config_kwargs())
        assert config.name == "t"

    def test_instant_only_task_is_accepted(self):
        config = TaskConfig(**self._config_kwargs(windowby_column=None, window_checks_config=None))
        assert config.instant_checks and config.window_checks_config is None

    def test_window_only_task_is_accepted(self):
        config = TaskConfig(**self._config_kwargs(instant_checks=[]))
        assert config.instant_checks == []

    def test_wait_for_late_defaults_to_none(self):
        config = TaskConfig(**self._config_kwargs())
        assert config.wait_for_late is None

    def test_wait_for_late_accepts_a_value(self):
        config = TaskConfig(**self._config_kwargs(wait_for_late=5))
        assert config.wait_for_late == 5

    @pytest.mark.parametrize(
        "override, expected_error",
        [
            (dict(input=None), "Input configuration is required."),
            (dict(output=None), "Output configuration is required."),
        ],
    )
    def test_missing_input_or_output_reported(self, override, expected_error):
        with pytest.raises(HTTPException) as exc_info:
            TaskConfig(**self._config_kwargs(**override))
        assert exc_info.value.status_code == 422
        assert expected_error in exc_info.value.detail

    def test_no_checks_at_all_is_rejected(self):
        with pytest.raises(HTTPException) as exc_info:
            TaskConfig(
                **self._config_kwargs(
                    instant_checks=[],
                    windowby_column=None,
                    window_checks_config=None,
                )
            )
        assert exc_info.value.status_code == 422
        assert "At least one instant check or window check is required." in exc_info.value.detail

    def test_window_checks_without_windowby_is_rejected(self):
        with pytest.raises(HTTPException) as exc_info:
            TaskConfig(**self._config_kwargs(windowby_column=None))
        assert exc_info.value.status_code == 422
        assert "Window checks require a windowby column." in exc_info.value.detail

    def test_windowby_without_window_checks_is_rejected(self):
        with pytest.raises(HTTPException) as exc_info:
            TaskConfig(**self._config_kwargs(window_checks_config=None))
        assert exc_info.value.status_code == 422
        assert (
            "A windowby column is provided but no window checks: "
            "Unnecessary windowby or forgotten window check(s)."
        ) in exc_info.value.detail
