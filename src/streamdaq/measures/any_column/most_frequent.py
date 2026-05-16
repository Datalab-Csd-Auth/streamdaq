from dataclasses import dataclass
from typing import ClassVar

import pathway as pw

from streamdaq.measures.base import DataQualityMeasure
from streamdaq.reducers.most_frequent_approx import most_frequent_approx_reducer
from streamdaq.utils.data_type_applicability import DataTypeApplicability


@dataclass
class MostFrequent(DataQualityMeasure):
    _applicability: ClassVar[DataTypeApplicability] = DataTypeApplicability.ANY_COLUMN
    # _dependencies: ClassVar[list[type[Self]]] = [Tuple] TODO UPDATE TESTS

    def get_reducer(self) -> pw.ColumnExpression:
        return most_frequent_approx_reducer(self.column)
