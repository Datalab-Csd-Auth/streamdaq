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

from enum import auto
import json
from typing import Any, Iterable, Optional, Self

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

    @classmethod
    def _missing_(cls, value: object) -> Optional[Self]:
        value = str(value).lower()
        for member in cls:
            if member.value == value:
                return member
        return None

    def find_in_list(
            self,
            l: Iterable[str],
            case_sensitive: bool = True
    ) -> Optional[str]:
        parsed_values = iter(l)
        if not case_sensitive:
            parsed_values = map(lambda v: v.lower(), parsed_values)

        for v, original_v in zip(parsed_values, l, strict=True):
            if v == self.value:
                return original_v
                
        return None


class _StreamdaqInternalColumnNames(LowercaseStrEnum):
    IS_TIME_FIRST_FIELD = auto()
    IS_TIME_VALID = auto()
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
    type: Optional[_EVBMeasurementType]
    fields: list[str]
    values: list[list[Any]]

    @model_validator(mode="before")
    @classmethod
    def validate_measurement_before(cls, data: Any) -> Any:
        if isinstance(data, dict):
            measurement = data
        elif isinstance(data, str):
            measurement: dict = json.loads(data)
        else:
            raise ValueError("Raw data should be of type string or json")

        return {
            EVBKeyNames.NAME.value: measurement.get(
                EVBKeyNames.NAME.find_in_list(measurement.keys(), False)
            ),
            EVBKeyNames.TYPE.value: measurement.get(
                EVBKeyNames.TYPE.find_in_list(measurement.keys(), False)
            ),
            EVBKeyNames.FIELDS.value: measurement.get(
                EVBKeyNames.FIELDS.find_in_list(measurement.keys(), False)
            ),
            EVBKeyNames.VALUES.value: measurement.get(
                EVBKeyNames.VALUES.find_in_list(measurement.keys(), False)
            ),
            EVBKeyNames.TAGS.value: measurement.get(
                EVBKeyNames.TAGS.find_in_list(measurement.keys(), False)
            ),
        }


    @model_validator(mode="after")
    def validate_measurement_after(self) -> Self:
        if self.fields[0] != "time":
            raise ValueError("'Time' field must always be first")
        
        if any(map(lambda row: 
                   not isinstance(row[0], int) or len(str(row[0])) != 13, 
                   self.values)):
            raise ValueError("Time values must be 13-digit long UTC ms timestamps")

        if any(map(lambda row: len(row) != len(self.fields), self.values)):
            raise IndexError("Fields and values' rows do not align.")

        return self


#  model_config = ConfigDict(extra='forbid')


class ValidatableEVBSchema(BaseModel):
    measurements: list[_EVBMeasurement]

    @model_validator(mode="before")
    @classmethod
    def validate_evb(cls, data: Any) -> Any:
        if isinstance(data, dict):
            evb = data
        elif isinstance(data, str):
            evb: dict = json.loads(data)
        else:
            raise ValueError("Raw data should be of type string or json")

        return {
            EVBKeyNames.MEASUREMENTS.value: evb.get(
                EVBKeyNames.MEASUREMENTS.find_in_list(evb.keys(), False)
            )
        }
