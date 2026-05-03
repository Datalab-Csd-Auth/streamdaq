import pytest
from pydantic import ValidationError

from streamdaq.schema.evb.definitions import (
    _VALID_TIME_DIGITS,
    EVBKeyNames,
    ValidatableEVBSchema,
    _EVBMeasurementType,
    _StreamdaqInternalColumnNames,
)


class TestEVBKeyNames:
    def test_enum_values_are_lowercase(self):
        assert EVBKeyNames.MEASUREMENTS == "measurements"
        assert EVBKeyNames.NAME == "name"
        assert EVBKeyNames.TAGS == "tags"
        assert EVBKeyNames.TYPE == "type"
        assert EVBKeyNames.FIELDS == "fields"
        assert EVBKeyNames.VALUES == "values"


class TestStreamdaqInternalColumnNames:
    def test_enum_values_are_lowercase(self):
        assert _StreamdaqInternalColumnNames.PYDANTIC_ERRORS == "pydantic_errors"
        assert _StreamdaqInternalColumnNames.TIME == "time"
        assert _StreamdaqInternalColumnNames.IS_TIME_FIRST_FIELD == "is_time_first_field"
        assert _StreamdaqInternalColumnNames.IS_TIME_VALID == "is_time_valid"
        assert _StreamdaqInternalColumnNames.VALIDATION_ERRORS_REPORT == "validation_errors_report"


class TestEVBMeasurementType:
    def test_pascal_case_values(self):
        assert _EVBMeasurementType.POINTS == "Points"
        assert _EVBMeasurementType.REPORT == "Report"
        assert _EVBMeasurementType.METADATA == "Metadata"
        assert _EVBMeasurementType.STATE == "State"
        assert _EVBMeasurementType.CONFIGURATION == "Configuration"
        assert _EVBMeasurementType.UNKNOWN == "Unknown"


class TestValidTimeDigits:
    def test_value(self):
        assert _VALID_TIME_DIGITS == 13


class TestValidatableEVBSchema:
    def test_valid_evb_message(self):
        data = {
            "measurements": [
                {
                    "name": "Temp",
                    "tags": {"plant": "Factory", "unit_id": "001"},
                    "type": "Points",
                    "fields": ["time", "temp"],
                    "values": [[1645334535000, 60]],
                }
            ]
        }
        model = ValidatableEVBSchema(**data)
        assert len(model.measurements) == 1
        assert model.measurements[0].name == "Temp"

    def test_invalid_measurement_type_raises(self):
        data = {
            "measurements": [
                {
                    "name": "Temp",
                    "tags": {"plant": "Factory"},
                    "type": "InvalidType",
                    "fields": ["time"],
                    "values": [[123]],
                }
            ]
        }
        with pytest.raises(ValidationError):
            ValidatableEVBSchema(**data)

    def test_missing_required_fields_raises(self):
        with pytest.raises(ValidationError):
            ValidatableEVBSchema(measurements=[{"name": "X"}])
