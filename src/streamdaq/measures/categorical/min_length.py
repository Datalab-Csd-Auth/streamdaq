from dataclasses import dataclass
from typing import ClassVar, Self

import pathway as pw

from streamdaq.computations.strings import strings_to_length
from streamdaq.measures.any_column.tuple import Tuple
from streamdaq.measures.base import DataQualityMeasure
from streamdaq.utils.data_type_applicability import DataTypeApplicability


@dataclass
class MinLength(DataQualityMeasure):
    _applicability: ClassVar[DataTypeApplicability] = DataTypeApplicability.CATEGORICAL_ONLY
    _dependencies: ClassVar[list[type[Self]]] = [Tuple]

    def get_reducer(self) -> pw.ColumnExpression:
        return pw.apply_with_type(
            lambda elements: min(strings_to_length(elements)),
            int,
            pw.this[Tuple._get_internal_shared_column_name(self.column)],
        )
