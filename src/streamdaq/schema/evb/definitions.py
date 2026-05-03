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

import pathway as pw
from pydantic import BaseModel
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
    type: _EVBMeasurementType
    fields: list[str]
    values: list[list[int | float]]


#  model_config = ConfigDict(extra='forbid')


class ValidatableEVBSchema(BaseModel):
    measurements: list[_EVBMeasurement]
