from dataclasses import dataclass
from math import sqrt
from typing import ClassVar

import pathway as pw

from streamdaq.measures.base import RoundableDataQualityMeasure
from streamdaq.reducers.variance import variance_reducer
from streamdaq.utils.data_type_applicability import DataTypeApplicability


@dataclass
class StandardDeviation(RoundableDataQualityMeasure):
    _applicability: ClassVar[DataTypeApplicability] = DataTypeApplicability.NUMERIC_ONLY

    def get_reducer(self) -> pw.ColumnExpression:
        return self._round_reducer_if_needed(
            pw.apply_with_type(
                # Rounding can make the variance of identical values slightly negative
                lambda variance_value: sqrt(max(variance_value, 0.0)),
                float,
                variance_reducer(pw.this[self.column]),
            )
        )
