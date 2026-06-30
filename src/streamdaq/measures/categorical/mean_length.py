from dataclasses import dataclass
from statistics import mean
from typing import ClassVar, Self

import pathway as pw

from streamdaq.computations.strings import strings_to_length
from streamdaq.measures.any_column.tuple import Tuple
from streamdaq.measures.base import DataQualityMeasure
from streamdaq.utils.data_type_applicability import DataTypeApplicability
from streamdaq.utils.picklable import Lambda


@dataclass
class MeanLength(DataQualityMeasure):
    _applicability: ClassVar[DataTypeApplicability] = DataTypeApplicability.CATEGORICAL_ONLY
    _dependencies: ClassVar[list[type[Self]]] = [Tuple]  # TODO ADD TESTS

    def get_expression(self) -> pw.ColumnExpression:
        return pw.apply_with_type(
            Lambda(lambda elements: mean(strings_to_length(elements))),
            int,
            pw.this[Tuple._get_internal_shared_column_name(self.column)],
        )
