from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar, Self

import pathway as pw

from streamdaq.utils.data_type_applicability import DataTypeApplicability


@dataclass
class DataQualityCheck(ABC):
    column: str
    _applicability: ClassVar[DataTypeApplicability] = None
    _dependencies: ClassVar[list[type[Self]]] = []
    _streamdaq_internal_prefix: ClassVar[str] = "__streamdaq_internal_shared_"

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        enum_member = getattr(cls, "_applicability", None)
        if isinstance(enum_member, DataTypeApplicability):
            enum_member.available_checks.append(cls)

    def is_applicable_to(self, data_type: type | str):
        return self._applicability.is_applicable_to(data_type)

    # TODO See if it is better to call this get_expression instead of get_reducer
    @abstractmethod
    def get_reducer(self) -> pw.ColumnExpression: ...

    @classmethod
    def _get_internal_shared_column_name(cls, column: str) -> str:
        return f"{cls._streamdaq_internal_prefix}#{cls.__name__}#{column}"
