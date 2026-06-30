from dataclasses import dataclass
from typing import ClassVar, Self

import pathway as pw

from streamdaq.computations.numeric import integer_part_digit_count
from streamdaq.measures.any_column.tuple import Tuple
from streamdaq.measures.base import DataQualityMeasure
from streamdaq.utils.data_type_applicability import DataTypeApplicability
from streamdaq.utils.picklable import Lambda


@dataclass
class MinIntegerPartLength(DataQualityMeasure):
    _applicability: ClassVar[DataTypeApplicability] = DataTypeApplicability.NUMERIC_ONLY
    _dependencies: ClassVar[list[type[Self]]] = [Tuple]

    def get_expression(self) -> pw.ColumnExpression:
        return pw.apply_with_type(
            Lambda(lambda elements: min(integer_part_digit_count(elements))),
            int,
            pw.this[Tuple._get_internal_shared_column_name(self.column)],
        )
