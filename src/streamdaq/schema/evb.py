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
from strenum import PascalCaseStrEnum


# ============== EVB Data Schema for Pathway operations - No Validation ==============
class EVBSchema(pw.Schema):
    measurements: list[pw.Json]  # Pathway does not support nested schemas


# ============== EVB Data Schema for Pydantic operations - Schema Validation ==============
class _EVBMeasurementType(PascalCaseStrEnum):
    POINTS = auto()
    REPORT = auto()
    METADATA = auto()
    STATE = auto()
    CONFIGURATION = auto()
    UNKNOWN = auto()


class _EVBMeasurement(BaseModel):
    name: str
    tags: dict[str, str]
    type: _EVBMeasurementType
    fields: list[str]
    values: list[list[int | float]]


class ValidatableEVBSchema(BaseModel):
    measurements: list[_EVBMeasurement]
