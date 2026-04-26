from dataclasses import dataclass
from typing import ClassVar

import pathway as pw

from streamdaq.measures.base import RoundableDataQualityMeasure
from streamdaq.utils.data_type_applicability import DataTypeApplicability


@dataclass
class Mean(RoundableDataQualityMeasure):
    _applicability: ClassVar[DataTypeApplicability] = DataTypeApplicability.NUMERIC_ONLY

    def get_reducer(self) -> pw.ColumnExpression:
        return self._round_reducer_if_needed(pw.reducers.avg(pw.this[self.column]))
