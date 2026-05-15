from dataclasses import dataclass
from typing import ClassVar

import pathway as pw

from streamdaq.measures.base import RoundableDataQualityMeasure
from streamdaq.reducers.variance import variance_reducer
from streamdaq.utils.data_type_applicability import DataTypeApplicability


@dataclass
class Variance(RoundableDataQualityMeasure):
    _applicability: ClassVar[DataTypeApplicability] = DataTypeApplicability.NUMERIC_ONLY

    def get_reducer(self) -> pw.ColumnExpression:
        return self._round_reducer_if_needed(variance_reducer(pw.this[self.column]))
