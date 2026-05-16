from dataclasses import dataclass
from typing import ClassVar, Self

import pathway as pw

from streamdaq.computations.numeric import fraction
from streamdaq.measures.any_column.count import Count
from streamdaq.measures.any_column.tuple import Tuple
from streamdaq.measures.base import RoundableDataQualityMeasure
from streamdaq.reducers.distinct_count_approx import distinct_count_approx_reducer
from streamdaq.utils.data_type_applicability import DataTypeApplicability


@dataclass
class DistinctFractionApprox(RoundableDataQualityMeasure):
    _applicability: ClassVar[DataTypeApplicability] = DataTypeApplicability.ANY_COLUMN
    _dependencies: ClassVar[list[type[Self]]] = [Tuple, Count]

    def _get_distinct_count_approx_reducer_internal_name(self):
        return f"{self._streamdaq_internal_prefix}#DistinctCountApproxReducer#{self.column}"

    def get_reduce_kwargs(self) -> dict[str, pw.ColumnExpression]:
        reduce_kwargs: dict[str, pw.ColumnExpression] = dict()
        kw = self._get_distinct_count_approx_reducer_internal_name()
        arg = distinct_count_approx_reducer(pw.this[self.column])
        reduce_kwargs[kw] = arg
        return reduce_kwargs

    def get_expression(self) -> pw.ColumnExpression:
        return self._round_reducer_if_needed(
            pw.apply_with_type(
                lambda distinct_count, total_count: fraction(distinct_count, total_count),
                float,
                pw.this[self._get_distinct_count_approx_reducer_internal_name()],  # distinct count
                pw.this[Count._get_internal_shared_column_name(self.column)],  # total_count
            )
        )
