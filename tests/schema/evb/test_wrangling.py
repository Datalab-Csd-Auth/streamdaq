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
    def test_no_errors_returns_none(self):
        assert _construct_validation_errors_report_if_needed(pydantic_errors="") is None

    def test_pydantic_errors_included(self):
        result = _construct_validation_errors_report_if_needed(pydantic_errors="field required")
        assert result == {_StreamdaqInternalColumnNames.PYDANTIC_ERRORS: "field required"}


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
        native_schema = {
            "fields": (("temperature", float), ("humidity", float)),
            "tags": (("plant", str),),
        }
        result = convert_raw_evb_to_native_format(table, native_schema)
        df = pw.debug.table_to_pandas(result)

        assert len(df) == 1
        row = df.iloc[0]
        assert row["temperature"] == 60.0
        assert row["humidity"] == 55.0
        assert row["time"] == 1645334535000
        assert row["name"] == "Temp"
        assert row["type"] == "Points"
        assert row["plant"] == "F"
        assert row["validation_errors_report"] is None
