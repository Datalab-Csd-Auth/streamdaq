import pytest
from pydantic import ValidationError

from streamdaq.schema.evb.definitions import (
    _VALID_TIME_DIGITS,
    EVBKeyNames,
    SniffedEVBSchema,
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


def _measurement(**overrides):
    base = {
        "name": "Temp",
        "tags": {"plant": "Factory"},
        "type": "Points",
        "fields": ["time", "temp"],
        "values": [[1645334535000, 60]],
    }
    base.update(overrides)
    return base


class TestEVBMeasurementValidation:
    def test_keys_are_lowercased_before_validation(self):
        model = ValidatableEVBSchema(
            measurements=[
                {
                    "NAME": "T",
                    "TAGS": {},
                    "TYPE": "Points",
                    "FIELDS": ["time", "a"],
                    "VALUES": [[1645334535000, 1.0]],
                }
            ]
        )
        assert model.measurements[0].name == "T"

    def test_non_dict_non_str_measurement_raises(self):
        with pytest.raises(ValidationError, match="instead of JSON-'str' or 'dict'"):
            ValidatableEVBSchema(measurements=[123])

    def test_time_must_be_first_field(self):
        with pytest.raises(ValidationError, match="first EVB field was found to be 'temp'"):
            ValidatableEVBSchema(
                measurements=[_measurement(fields=["temp", "time"], values=[[60, 1645334535000]])]
            )

    def test_field_and_value_lengths_must_match(self):
        with pytest.raises(ValidationError, match=r"2 values were found for 3 fields"):
            ValidatableEVBSchema(
                measurements=[
                    _measurement(fields=["time", "a", "b"], values=[[1645334535000, 1.0]])
                ]
            )

    def test_time_value_must_have_valid_digit_count(self):
        with pytest.raises(ValidationError, match=r"had 3 digits \(123\) instead of 13 digits"):
            ValidatableEVBSchema(
                measurements=[_measurement(fields=["time", "a"], values=[[123, 1.0]])]
            )

    def test_multiple_errors_are_aggregated(self):
        with pytest.raises(ValidationError, match="Also,"):
            ValidatableEVBSchema(
                measurements=[_measurement(fields=["temp", "time"], values=[[60, 12]])]
            )


class TestSniffedEVBSchemaSerialize:
    def test_maps_fields_to_value_types(self):
        result = SniffedEVBSchema(
            fields=["temperature", "count"], values=[60.0, 3], tags={}
        ).serialize()
        assert result["fields"] == (("temperature", float), ("count", int))

    def test_no_tags_yields_empty_tuple(self):
        assert SniffedEVBSchema(fields=["a"], values=[1.0], tags={}).serialize()["tags"] == ()

    def test_tags_are_typed_as_str(self):
        result = SniffedEVBSchema(fields=["a"], values=[1.0], tags={"plant": "F"}).serialize()
        assert result["tags"] == (("plant", str),)
