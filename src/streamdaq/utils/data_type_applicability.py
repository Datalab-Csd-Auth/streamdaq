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

        return data_type_applicability

    def is_applicable_to(self, data_type: type | str):
        data_type_str = str(data_type)
        applicable_data_types_str = set(
            [str(data_type) for data_type in self.applicable_data_types]
        )
        for applicable_data_type in applicable_data_types_str:
            if applicable_data_type in data_type_str:
                return True
        return False
