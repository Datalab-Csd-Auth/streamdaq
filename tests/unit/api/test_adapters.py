import pytest
from fastapi import HTTPException

from streamdaq.api.adapters import validate_coerce_params
from streamdaq.api.models import MeasureConfig
from streamdaq.checks.instant.any_column.in_range import InRange
from streamdaq.custom import measure
from streamdaq.measures.numeric.in_range_count import InRangeCount
from streamdaq.measures.numeric.mean import Mean


class TestCoerceParamsViaTypeAdapter:
    @pytest.mark.parametrize(
        "target, params, expected",
        [
            (Mean, {"column": "temperature"}, {"column": "temperature", "precision": None}),
            (
                InRangeCount,
                {"column": "age", "low": "0", "high": "120"},
                {
                    "column": "age",
                    "low": 0,
                    "high": 120,
                    "inclusive_low": True,
                    "inclusive_high": False,
                },
            ),
        ],
        ids=["mean-defaults", "in-range-count-string-coercion"],
    )
    def test_dataclass_coercion_and_defaults(self, target, params, expected):
        assert validate_coerce_params(target, params, label=target.__name__) == expected

    def test_injects_required_field_and_drops_it(self):
        # ``name`` is a required field on the check, so coercion only succeeds because it is
        # injected; ``drop`` then removes it from the returned constructor params.
        coerced = validate_coerce_params(
            InRange,
            {"column": "age", "low": 0, "high": 120},
            inject={"name": "injected_check"},
            drop=("name",),
            label="InRange",
        )

        assert "name" not in coerced
        assert coerced == {
            "column": "age",
            "low": 0,
            "high": 120,
            "inclusive_low": True,
            "inclusive_high": False,
        }

    def test_non_dataclass_target_passes_params_through(self):
        params = {"anything": 1, "goes": "here"}
        assert validate_coerce_params(dict, params, label="dict") == params

    def test_invalid_params_raise_http_400(self):
        with pytest.raises(HTTPException) as exc_info:
            validate_coerce_params(
                InRangeCount, {"column": "age", "low": "not_a_number"}, label="InRangeCount"
            )

        assert exc_info.value.status_code == 400
        assert "Invalid params for InRangeCount" in exc_info.value.detail


class TestCustomMeasureConfigContract:
    """A registered custom measure validates against ``MeasureConfig`` with empty params."""

    def test_config_accepts_empty_params(self):
        @measure(["x"], name="_ConfigContractSum")
        def _config_contract_sum(d):
            return sum(d["x"])

        config = MeasureConfig(type="_ConfigContractSum", params={})

        assert config.params == {"column": ""}
