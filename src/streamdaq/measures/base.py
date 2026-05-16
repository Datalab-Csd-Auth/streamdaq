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

from abc import ABC
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

    # override this if your measure needs any computation during the reduce phase
    # that is not covered by the dependencies' get_reducer
    def get_reducer(self) -> pw.ColumnExpression | None:
        return None

    def get_reduce_kwargs(self) -> dict[str, pw.ColumnExpression]:
        reduce_kwargs: dict[str, pw.ColumnExpression] = dict()

        if not self._dependencies:
            overridable_kw = self._get_internal_overridable_placeholder_column_name()
            arg = self.get_reducer()
            reduce_kwargs[overridable_kw] = arg
            return reduce_kwargs

        for dependency in self._dependencies:
            kw = dependency._get_internal_shared_column_name(self.column)
            arg = dependency(self.column).get_reducer()
            reduce_kwargs[kw] = arg
        return reduce_kwargs

    # override this if your measure needs a 2-layered computation:
    # first a pw.reducer and then a with_columns on top of the reduced table
    def get_expression(self) -> pw.ColumnExpression | None:
        return None

    @classmethod
    def _get_internal_shared_column_name(cls, column: str) -> str:
        return f"{cls._streamdaq_internal_prefix}#{cls.__name__}#{column}"

    @classmethod
    def _get_internal_overridable_placeholder_column_name(cls) -> str:
        return f"{cls._streamdaq_internal_prefix}#OVERRIDABLE_PLACEHOLDER_MEASURE_COLUMN"


@dataclass(kw_only=True)
class RoundableDataQualityMeasure(DataQualityMeasure):
    precision: int | None = field(default=None)

    def _round_reducer_if_needed(self, reducer: pw.ColumnExpression) -> pw.ColumnExpression:
        if self.precision is None:
            return reducer
        return pw.apply_with_type(round, float, reducer, self.precision)
