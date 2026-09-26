from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar, Self

import pathway as pw

from streamdaq.checks.registry import INSTANT_CHECK_REGISTRY
from streamdaq.utils.data_type_applicability import DataTypeApplicability


@dataclass
class DataQualityCheck(ABC):
    name: str
    _applicability: ClassVar[DataTypeApplicability] = None
    _dependencies: ClassVar[list[type[Self]]] = []
    _streamdaq_internal_prefix: ClassVar[str] = "__streamdaq_internal_shared_"
    _should_be_registered: ClassVar[bool] = True

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        enum_member = getattr(cls, "_applicability", None)
        if isinstance(enum_member, DataTypeApplicability):
            enum_member.available_checks.append(cls)

        if cls.__dict__.get("_should_be_registered", True):
            INSTANT_CHECK_REGISTRY[cls.__name__] = cls

    def is_applicable_to(self, data_type: type | str):
        return self._applicability.is_applicable_to(data_type)

    @abstractmethod
    def get_measurement_expression(self) -> pw.ColumnExpression: ...

    @classmethod
    def _get_internal_shared_column_name(cls, column: str) -> str:
        return f"{cls._streamdaq_internal_prefix}#{cls.__name__}#{column}"


@dataclass
class SingleColumnDataQualityCheck(DataQualityCheck):
    column: str
    _should_be_registered: ClassVar[bool] = False


@dataclass
class MultiColumnDataQualityCheck(DataQualityCheck):
    columns: list[str]
    _should_be_registered: ClassVar[bool] = False
