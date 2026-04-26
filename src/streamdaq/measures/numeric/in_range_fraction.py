from dataclasses import dataclass, field
from typing import ClassVar, Self

import pathway as pw

from streamdaq.computations.numeric import fraction, range_conformance_count
from streamdaq.measures.any_column.count import Count
from streamdaq.measures.any_column.tuple import Tuple
from streamdaq.measures.base import RoundableDataQualityMeasure
from streamdaq.utils.data_type_applicability import DataTypeApplicability


@dataclass
class InRangeFraction(RoundableDataQualityMeasure):
    low: int | float
    high: int | float
    inclusive_low: bool = field(default=True)
    inclusive_high: bool = field(default=False)
    _applicability: ClassVar[DataTypeApplicability] = DataTypeApplicability.ANY_COLUMN
    _dependencies: ClassVar[list[type[Self]]] = [Tuple, Count]

    def get_reducer(self) -> pw.ColumnExpression:
        return self._round_reducer_if_needed(
            pw.apply_with_type(
                lambda elements, total_count: fraction(
                    range_conformance_count(
                        elements, self.low, self.high, self.inclusive_low, self.inclusive_high
                    ),
                    total_count,
                ),
                float,
                pw.this[Tuple._get_internal_shared_column_name(self.column)],  # elements
                pw.this[Count._get_internal_shared_column_name(self.column)],  # total_count
            )
        )
