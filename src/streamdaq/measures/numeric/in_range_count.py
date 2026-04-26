from dataclasses import dataclass, field
from typing import ClassVar, Self

import pathway as pw

from streamdaq.computations.numeric import range_conformance_count
from streamdaq.measures.any_column.tuple import Tuple
from streamdaq.measures.base import DataQualityMeasure
from streamdaq.utils.data_type_applicability import DataTypeApplicability


@dataclass
class InRangeCount(DataQualityMeasure):
    low: int | float
    high: int | float
    inclusive_low: bool = field(default=True)
    inclusive_high: bool = field(default=False)
    _applicability: ClassVar[DataTypeApplicability] = DataTypeApplicability.ANY_COLUMN
    _dependencies: ClassVar[list[type[Self]]] = [Tuple]

    def get_reducer(self) -> pw.ColumnExpression:
        return pw.apply_with_type(
            lambda elements: range_conformance_count(
                elements, self.low, self.high, self.inclusive_low, self.inclusive_high
            ),
            int,
            pw.this[Tuple._get_internal_shared_column_name(self.column)],
        )
