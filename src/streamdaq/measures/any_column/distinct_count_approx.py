from dataclasses import dataclass
from typing import ClassVar, Self

import pathway as pw

from streamdaq.measures.any_column.tuple import Tuple
from streamdaq.measures.base import DataQualityMeasure
from streamdaq.reducers.distinct_count_approx import distinct_count_approx_reducer
from streamdaq.utils.data_type_applicability import DataTypeApplicability


@dataclass
class DistinctCountApprox(DataQualityMeasure):
    _applicability: ClassVar[DataTypeApplicability] = DataTypeApplicability.ANY_COLUMN
    _dependencies: ClassVar[list[type[Self]]] = [Tuple]

    def get_reducer(self) -> pw.ColumnExpression:
        return pw.apply_with_type(
            # TODO See if pw.Table.cast_to_types(distinct_count_approx=int) is more performant
            lambda count_as_float: int(count_as_float),  # datasketch returns float by default
            int,
            distinct_count_approx_reducer(pw.this[self.column]),
        )
