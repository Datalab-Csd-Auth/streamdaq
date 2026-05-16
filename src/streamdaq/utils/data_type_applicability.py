import builtins
from enum import Enum


class DataTypeApplicability(Enum):
    NUMERIC_ONLY = ("numeric", [int, float])
    CATEGORICAL_ONLY = ("categorical", [str])
    ANY_COLUMN = ("any", [int, float, str, bool])

    def __new__(cls, value: str, applicable_data_types: list[type]):
        data_type_applicability = object.__new__(cls)
        data_type_applicability._value_ = value
        data_type_applicability.applicable_data_types = applicable_data_types

        # handled in DataQualityMeasure __init_subclass__
        data_type_applicability.available_measures = []

        # handled in DataQualityCheck __init_subclass__
        data_type_applicability.available_checks = []

        return data_type_applicability

    def is_applicable_to(self, data_type: type | str):
        # convert to python's `type` if it is a string
        if isinstance(data_type, str):
            data_type = getattr(builtins, data_type, None)

        return data_type in self.applicable_data_types
