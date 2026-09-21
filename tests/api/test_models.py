import pytest
from fastapi import HTTPException

from streamdaq.api.models import InstantCheckConfig, MeasureConfig, WindowCheckConfig
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
