from dataclasses import dataclass
from typing import Any, ClassVar, Self

import pathway as pw

from streamdaq.measures.any_column.tuple import Tuple
from streamdaq.measures.base import DataQualityMeasure
from streamdaq.utils.data_type_applicability import DataTypeApplicability


@dataclass
class DistinctPlaceholderCount(DataQualityMeasure):
    placeholders: list[Any]
    _applicability: ClassVar[DataTypeApplicability] = DataTypeApplicability.ANY_COLUMN
    _dependencies: ClassVar[list[type[Self]]] = [Tuple]

    def get_reducer(self) -> pw.ColumnExpression:
        return pw.apply_with_type(
            lambda elements: len(set(elements).intersection(self.placeholders)),
            int,
            pw.this[Tuple._get_internal_shared_column_name(self.column)],
        )
