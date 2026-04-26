"""
Base classes for data quality measures.

Defines hierarchy for type-safe measure application:
- DataQualityMeasure: Abstract base for all measures
    - NumericalMeasure: For measures applicable to int/float columns only
    - CategoricalMeasure: For measures applicable to string/enum columns only
    - UniversalMeasure: For measures applicable to any column type

Computation Dependencies: Measures can depend on other measures.
For example, the fraction of NULLs depends on count of NULLs and total
count. Dependencies are

(e.g., fraction_nulls depends on count and count_nulls)
- Dependencies are internal implementation details set by system developers
- Dependencies form a DAG (Directed Acyclic Graph)
- Shared dependencies are computed once in Pathway
- Final table is filtered to user-requested measures
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import ClassVar, Self

import pathway as pw

from streamdaq.utils.data_type_applicability import DataTypeApplicability


@dataclass
class DataQualityMeasure(ABC):
    column: str
    _applicability: ClassVar[DataTypeApplicability] = None
    _dependencies: ClassVar[list[type[Self]]] = []
    _streamdaq_internal_prefix: ClassVar[str] = "__streamdaq_internal_shared_"

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        enum_member = getattr(cls, "_applicability", None)
        if isinstance(enum_member, DataTypeApplicability):
            enum_member.available_measures.append(cls)

    def is_applicable_to(self, data_type: type | str):
        return self._applicability.is_applicable_to(data_type)

    @abstractmethod
    def get_reducer(self) -> pw.ColumnExpression: ...

    @classmethod
    def _get_internal_shared_column_name(cls, column: str) -> str:
        return f"{cls._streamdaq_internal_prefix}#{cls.__name__}#{column}"


@dataclass(kw_only=True)
class RoundableDataQualityMeasure(DataQualityMeasure):
    precision: int | None = field(default=None)

    def _round_reducer_if_needed(self, reducer: pw.ColumnExpression) -> pw.ColumnExpression:
        if self.precision is None:
            return reducer
        return pw.apply_with_type(round, float, reducer, self.precision)
