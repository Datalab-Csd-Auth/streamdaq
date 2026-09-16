import operator

import pytest

from streamdaq.api.models import InstantCheckConfig
from streamdaq.checks.instant.any_column.in_row_comparison import InRowComparison


class TestInRowComparisonConstruction:
    def test_operator_field_stays_a_string(self):
        check = InRowComparison(name="c", columns=["a", "b"], operator="lt")
        assert check.operator == "lt"

    def test_resolves_to_the_operator_function(self):
        check = InRowComparison(name="c", columns=["a", "b"], operator="ge")
        assert check._resolve_operator() is operator.ge

    @pytest.mark.parametrize("bad_operator", ["nope", "<", 123, operator.lt])
    def test_invalid_operator_raises(self, bad_operator):
        with pytest.raises(ValueError, match="InRowComparison"):
            InRowComparison(name="c", columns=["a", "b"], operator=bad_operator)

    @pytest.mark.parametrize("columns", [["a"], ["a", "b", "c"]])
    def test_requires_exactly_two_columns(self, columns):
        with pytest.raises(ValueError, match="not exactly 2"):
            InRowComparison(name="c", columns=columns, operator="lt")


class TestInRowComparisonApiRoundTrip:
    def test_api_config_keeps_operator_serializable_and_rebuildable(self):
        config = InstantCheckConfig(
            check_class="InRowComparison",
            name="c",
            params={"columns": ["a", "b"], "operator": "lt"},
        )
        assert config.params["operator"] == "lt"

        rebuilt = InRowComparison(name=config.name, **config.params)
        assert rebuilt._resolve_operator() is operator.lt
