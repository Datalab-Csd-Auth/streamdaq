"""
Example Event Buss Message (EVB) Format:
```json
{
   "measurements":[
      {
         "name":"TemperatureHumidity",
         "tags":{
            "plant":"StreamdaqFactory",
            "unit_id":"012332"
         },
         "type":"Points",
         "fields":[
            "time",
            "temperature",
            "humidity"
         ],
         "values":[
            [
               1645334535000,
               60,
               55
            ],
            [
               1645338135000,
               62,
               54
            ]
         ]
      }
   ]
}
```
"""

import json
from collections.abc import Callable
from enum import auto
from typing import Any, Self

import pathway as pw
from pydantic import BaseModel, model_validator
from strenum import LowercaseStrEnum, PascalCaseStrEnum


# Always keep in sync with the names used in the BaseModel sub-classes
class EVBKeyNames(LowercaseStrEnum):
    MEASUREMENTS = auto()
    NAME = auto()
    TAGS = auto()
    TYPE = auto()
    FIELDS = auto()
    VALUES = auto()


class _StreamdaqInternalColumnNames(LowercaseStrEnum):
    PYDANTIC_ERRORS = auto()
    TIME = auto()
    VALIDATION_ERRORS_REPORT = auto()


# ============== EVB Data Schema for Pathway operations - No Validation ==============
class EVBSchema(pw.Schema):
    measurements: list[pw.Json]  # Pathway does not support nested schemas


# ============== EVB Data Schema for Pydantic operations - Schema Validation ==============
class _EVBMeasurementType(PascalCaseStrEnum):
    POINTS = auto()  # PascalCase translates to 'Points'
    REPORT = auto()
    METADATA = auto()
    STATE = auto()
    CONFIGURATION = auto()
    UNKNOWN = auto()


_VALID_TIME_DIGITS = 13


class _EVBMeasurement(BaseModel):
    name: str
    tags: dict[str, str]
    type: _EVBMeasurementType
    fields: list[str]
    values: list[list[int | float]]

    @model_validator(mode="before")
    @classmethod
    def validate_measurement_before_pydantic(cls, data: Any):
        if isinstance(data, dict):
            measurement: dict = data
        elif isinstance(data, str):
            measurement: dict = json.loads(data)
        else:
            raise ValueError(
                f"Raw EVB measurement was found to be of type '{type(data)}' "
                "instead of JSON-'str' or 'dict'"
            )

        return {str(key).lower(): value for key, value in measurement.items()}

    def validate_time_is_first_field(self) -> str | None:
        first_field = self.fields[0]
        if first_field != _StreamdaqInternalColumnNames.TIME:
            return (
                f"The first EVB field was found to be '{first_field}' "
                f"instead of '{_StreamdaqInternalColumnNames.TIME}'."
            )
        return None

    def validate_lengths_of_fields_and_values(self) -> str | None:
        number_of_fields = len(self.fields)
        errors: list[str] = []
        for idx, values in enumerate(self.values):
            number_of_values = len(values)
            if number_of_fields != number_of_values:
                errors.append(
                    f"At 'values' index {idx} (0-indexed), {number_of_values} values were found "
                    f"for {number_of_fields} fields ({number_of_values} <> {number_of_fields})."
                )

        if errors:
            return " Also, ".join(errors)
        return None

    def validate_time_values(self) -> str | None:
        time_values = [values[0] for values in self.values]
        errors: list[str] = []
        for idx, time_value in enumerate(time_values):
            if not isinstance(time_value, int):
                errors.append(
                    f"At 'values' index {idx} (0-indexed), '{_StreamdaqInternalColumnNames.TIME}' "
                    f"was of type '{type(time_value)}' instead of 'int'."
                )
            elif len(str(time_value)) != _VALID_TIME_DIGITS:
                errors.append(
                    f"At values index {idx} (0-indexed), '{_StreamdaqInternalColumnNames.TIME}' "
                    f"had {len(str(time_value))} digits ({str(time_value)}) "
                    f"instead of {_VALID_TIME_DIGITS} digits."
                )

        if errors:
            return " Also, ".join(errors)
        return None

    @model_validator(mode="after")
    def validate_measurement_after_pydantic(self) -> Self:
        all_errors: list[str] = []
        validation_functions: list[Callable[[Self], str | None]] = [
            self.validate_time_is_first_field,
            self.validate_lengths_of_fields_and_values,
            self.validate_time_values,
        ]

        for validation_function in validation_functions:
            validation_errors = validation_function()
            if validation_errors:
                all_errors.append(validation_errors)

        if len(all_errors) > 0:
            raise ValueError(" Also, ".join(all_errors))
        return self


class ValidatableEVBSchema(BaseModel):
    measurements: list[_EVBMeasurement]


class SniffedEVBSchema(BaseModel):
    fields: list[str]
    values: list[Any]
    tags: dict[str, str]

    def serialize(self) -> dict[str, Any]:
        fields: tuple[tuple[str, type]] = tuple(
            (field, type(value)) for field, value in zip(self.fields, self.values)
        )
        tags: tuple = tuple()
        if len(self.tags) > 0:
            tags: tuple[tuple[str, str]] = tuple((tag, str) for tag in self.tags.keys())
        return {"fields": fields, "tags": tags}
