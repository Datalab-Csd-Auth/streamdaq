from dataclasses import dataclass
from typing import ClassVar, Self

import pathway as pw

from streamdaq.computations.numeric import linear_slope
from streamdaq.measures.any_column.tuple import Tuple
from streamdaq.measures.base import RoundableDataQualityMeasure
from streamdaq.utils.data_type_applicability import DataTypeApplicability


@dataclass
class BestLineFitSlope(RoundableDataQualityMeasure):
    time_column: str
    _applicability: ClassVar[DataTypeApplicability] = DataTypeApplicability.ANY_COLUMN
    _dependencies: ClassVar[list[type[Self]]] = [Tuple]

    def get_reducer(self) -> pw.ColumnExpression:
        return self._round_reducer_if_needed(
            pw.apply_with_type(
                linear_slope,
                float,
                pw.this[Tuple._get_internal_shared_column_name(self.column)],
                pw.this[Tuple._get_internal_shared_column_name(self.time_column)],
            )
        )
