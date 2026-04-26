from dataclasses import dataclass
from typing import ClassVar, Self

import pathway as pw

from streamdaq.computations.generic import count_singletons
from streamdaq.measures.any_column.tuple import Tuple
from streamdaq.measures.base import DataQualityMeasure
from streamdaq.utils.data_type_applicability import DataTypeApplicability


@dataclass
class UniqueCount(DataQualityMeasure):
    _applicability: ClassVar[DataTypeApplicability] = DataTypeApplicability.ANY_COLUMN
    _dependencies: ClassVar[list[type[Self]]] = [Tuple]

    def get_reducer(self) -> pw.ColumnExpression:
        return pw.apply_with_type(
            count_singletons,
            int,
            pw.this[Tuple._get_internal_shared_column_name(self.column)],
        )
