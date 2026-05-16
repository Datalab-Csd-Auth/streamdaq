from dataclasses import dataclass
from typing import ClassVar

import pathway as pw

from streamdaq.measures.base import DataQualityMeasure
from streamdaq.reducers.distinct_count_approx import distinct_count_approx_reducer
from streamdaq.utils.data_type_applicability import DataTypeApplicability


@dataclass
class DistinctCountApprox(DataQualityMeasure):
    _applicability: ClassVar[DataTypeApplicability] = DataTypeApplicability.ANY_COLUMN
    # _dependencies: ClassVar[list[type[Self]]] = [Tuple]  TODO UPDATE TESTS

    def _get_distinct_count_approx_reducer_internal_name(self):
        return f"{self._streamdaq_internal_prefix}#DistinctCountApproxReducer#{self.column}"

    def get_expression(self) -> pw.ColumnExpression:
        return pw.apply_with_type(
            lambda count_as_float: int(count_as_float),  # datasketch returns float by default
            int,
            pw.this[self._get_distinct_count_approx_reducer_internal_name()],
        )

    def get_reduce_kwargs(self) -> dict[str, pw.ColumnExpression]:
        reduce_kwargs: dict[str, pw.ColumnExpression] = dict()
        kw = self._get_distinct_count_approx_reducer_internal_name()
        arg = distinct_count_approx_reducer(pw.this[self.column])
        reduce_kwargs[kw] = arg
        return reduce_kwargs
