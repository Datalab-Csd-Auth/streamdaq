from dataclasses import dataclass
from typing import Any, ClassVar, Self

import pathway as pw

from streamdaq.computations.generic import set_conformance_count
from streamdaq.measures.any_column.tuple import Tuple
from streamdaq.measures.base import DataQualityMeasure
from streamdaq.utils.data_type_applicability import DataTypeApplicability


@dataclass
class InSetCount(DataQualityMeasure):
    allowed_values: set[Any]
    _applicability: ClassVar[DataTypeApplicability] = DataTypeApplicability.ANY_COLUMN
    _dependencies: ClassVar[list[type[Self]]] = [Tuple]

    def get_reducer(self) -> pw.ColumnExpression:
        return pw.apply_with_type(
            lambda elements: set_conformance_count(elements, self.allowed_values),
            int,
            pw.this[Tuple._get_internal_shared_column_name(self.column)],
        )
