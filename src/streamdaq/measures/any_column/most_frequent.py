from dataclasses import dataclass
from typing import ClassVar, Self

import pathway as pw

from streamdaq.measures.any_column.tuple import Tuple
from streamdaq.measures.base import DataQualityMeasure
from streamdaq.reducers.most_frequent_approx import most_frequent_approx_reducer
from streamdaq.utils.data_type_applicability import DataTypeApplicability


@dataclass
class MostFrequent(DataQualityMeasure):
    _applicability: ClassVar[DataTypeApplicability] = DataTypeApplicability.ANY_COLUMN
    _dependencies: ClassVar[list[type[Self]]] = [Tuple]

    def get_reducer(self) -> pw.ColumnExpression:
        return most_frequent_approx_reducer(self.column)
