from dataclasses import dataclass
from typing import ClassVar

import pathway as pw

from streamdaq.measures.base import RoundableDataQualityMeasure
from streamdaq.reducers.std_dev import std_dev_reducer
from streamdaq.utils.data_type_applicability import DataTypeApplicability


@dataclass
class StandardDeviation(RoundableDataQualityMeasure):
    _applicability: ClassVar[DataTypeApplicability] = DataTypeApplicability.NUMERIC_ONLY

    def get_reducer(self) -> pw.ColumnExpression:
        return self._round_reducer_if_needed(std_dev_reducer(pw.this[self.column]))
