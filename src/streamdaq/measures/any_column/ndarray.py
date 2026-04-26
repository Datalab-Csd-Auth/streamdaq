from dataclasses import dataclass
from typing import ClassVar

import pathway as pw

from streamdaq.measures.base import DataQualityMeasure
from streamdaq.utils.data_type_applicability import DataTypeApplicability


@dataclass
class Ndarray(DataQualityMeasure):
    _applicability: ClassVar[DataTypeApplicability] = DataTypeApplicability.ANY_COLUMN

    def get_reducer(self) -> pw.ColumnExpression:
        return pw.reducers.ndarray(pw.this[self.column])
