import pathway as pw

from streamdaq.schema.evb.definitions import EVBSchema, _StreamdaqInternalColumnNames
from streamdaq.schema.evb.wrangling import (
    _construct_validation_errors_report_if_needed,
    _validate_with_pydantic,
    convert_raw_evb_to_native_format,
)


class _FakeJson:
    """Mimics pw.Json's .as_dict() interface for testing."""

    def __init__(self, data: dict):
        self._data = data

    def as_dict(self):
        return self._data


class TestConstructValidationErrorsReport:
    def test_all_valid_returns_none(self):
        result = _construct_validation_errors_report_if_needed(
            pydantic_errors="", is_time_first_field=True, is_time_valid=True
        )
        assert result is None

    def test_pydantic_errors_included(self):
        result = _construct_validation_errors_report_if_needed(
            pydantic_errors="field required", is_time_first_field=True, is_time_valid=True
        )
        assert result is not None
        assert result[_StreamdaqInternalColumnNames.PYDANTIC_ERRORS] == "field required"

    def test_time_not_first_field(self):
        result = _construct_validation_errors_report_if_needed(
            pydantic_errors="", is_time_first_field=False, is_time_valid=True
        )
        assert result is not None
        assert _StreamdaqInternalColumnNames.IS_TIME_FIRST_FIELD in result
        assert result[_StreamdaqInternalColumnNames.IS_TIME_FIRST_FIELD] == (False,)

    def test_time_invalid(self):
        result = _construct_validation_errors_report_if_needed(
            pydantic_errors="", is_time_first_field=True, is_time_valid=False
        )
        assert result is not None
        assert _StreamdaqInternalColumnNames.IS_TIME_VALID in result
        assert result[_StreamdaqInternalColumnNames.IS_TIME_VALID] == (False,)

    def test_all_invalid_has_three_keys(self):
        result = _construct_validation_errors_report_if_needed(
            pydantic_errors="err", is_time_first_field=False, is_time_valid=False
        )
        assert result is not None
        assert len(result) == 3


class TestValidateWithPydantic:
    def test_valid_message_returns_none(self):
        measurement = _FakeJson(
            {
                "name": "Temp",
                "tags": {"plant": "Factory", "unit_id": "001"},
                "type": "Points",
                "fields": ["time", "temp"],
                "values": [[1645334535000, 60]],
            }
        )
        result = _validate_with_pydantic((measurement,))
        assert result is None

    def test_invalid_message_returns_error_string(self):
        measurement = _FakeJson({"name": 123})
        result = _validate_with_pydantic((measurement,))
        assert result is not None
        assert isinstance(result, str)
        assert "validation error" in result.lower()


class TestConvertRawEVBToNativeFormat:
    def test_converts_valid_evb_to_native_columns(self):
        evb_data = {
            "name": "Temp",
            "tags": {"plant": "F"},
            "type": "Points",
            "fields": ["time", "temperature", "humidity"],
            "values": [[1645334535000, 60.0, 55.0]],
        }
        table = pw.debug.table_from_rows(schema=EVBSchema, rows=[([pw.Json(evb_data)],)])
        native_schema = (("temperature", float), ("humidity", float))
        result = convert_raw_evb_to_native_format(table, native_schema)
        df = pw.debug.table_to_pandas(result)

        assert len(df) == 1
        assert df.iloc[0]["temperature"] == 60.0
        assert df.iloc[0]["humidity"] == 55.0
        assert df.iloc[0]["time"] == 1645334535000
        assert df.iloc[0]["name"] == "Temp"
        assert df.iloc[0]["type"] == "Points"
        assert df.iloc[0]["validation_errors_report"] is None
