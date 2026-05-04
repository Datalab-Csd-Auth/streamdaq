from dataclasses import dataclass
from statistics import median
from typing import ClassVar

import pathway as pw

from streamdaq.measures.base import DataQualityMeasure
from streamdaq.utils.data_type_applicability import DataTypeApplicability


@dataclass
class Median(DataQualityMeasure):
    _applicability: ClassVar[DataTypeApplicability] = DataTypeApplicability.NUMERIC_ONLY

    def get_reducer(self) -> pw.ColumnExpression:
        # TODO THE COLUMN TYPE CAN BE FOUND WITH table.typehints()["column_name"]
        return pw.apply(median, pw.reducers.tuple(pw.this[self.column]))
