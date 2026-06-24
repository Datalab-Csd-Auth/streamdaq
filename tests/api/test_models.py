import pytest
from fastapi import HTTPException

from streamdaq.api.models import InstantCheckConfig, MeasureConfig


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
