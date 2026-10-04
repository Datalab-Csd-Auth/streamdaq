import pytest

from streamdaq.utils.data_type_applicability import DataTypeApplicability


class TestIsApplicableTo:
    @pytest.mark.parametrize("data_type", [int, float, "int", "float"])
    def test_numeric_applicable(self, data_type):
        assert DataTypeApplicability.NUMERIC_ONLY.is_applicable_to(data_type) is True

    @pytest.mark.parametrize("data_type", [str, "str"])
    def test_categorical_applicable(self, data_type):
        assert DataTypeApplicability.CATEGORICAL_ONLY.is_applicable_to(data_type) is True

    @pytest.mark.parametrize("data_type", [str, "str"])
    def test_numerical_not_applicable(self, data_type):
        assert DataTypeApplicability.NUMERIC_ONLY.is_applicable_to(data_type) is False

    @pytest.mark.parametrize("data_type", [int, float, "int", "float"])
    def test_categorical_not_applicable(self, data_type):
        assert DataTypeApplicability.CATEGORICAL_ONLY.is_applicable_to(data_type) is False

    @pytest.mark.parametrize("data_type", [int, float, str, bool, "int", "float", "str", "bool"])
    def test_any_column_applicable_to_all(self, data_type):
        assert DataTypeApplicability.ANY_COLUMN.is_applicable_to(data_type) is True

    @pytest.mark.parametrize(
        "applicability",
        [
            DataTypeApplicability.NUMERIC_ONLY,
            DataTypeApplicability.CATEGORICAL_ONLY,
            DataTypeApplicability.ANY_COLUMN,
        ],
    )
    def test_unknown_type_as_str_not_applicable_to_any_applicability_type(self, applicability):
        assert applicability.is_applicable_to("unknown_type") is False


class TestEnumMembers:
    def test_values(self):
        assert DataTypeApplicability.NUMERIC_ONLY.value == "numeric"
        assert DataTypeApplicability.CATEGORICAL_ONLY.value == "categorical"
        assert DataTypeApplicability.ANY_COLUMN.value == "any"

    def test_applicable_data_types(self):
        assert DataTypeApplicability.NUMERIC_ONLY.applicable_data_types == [int, float]
        assert DataTypeApplicability.CATEGORICAL_ONLY.applicable_data_types == [str]
        assert DataTypeApplicability.ANY_COLUMN.applicable_data_types == [int, float, str, bool]

    @pytest.mark.parametrize("member", list(DataTypeApplicability))
    def test_available_measures_is_list(self, member):
        assert isinstance(member.available_measures, list)
