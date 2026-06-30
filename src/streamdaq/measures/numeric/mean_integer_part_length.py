from dataclasses import dataclass
from statistics import mean
from typing import ClassVar, Self

import pathway as pw

from streamdaq.computations.numeric import integer_part_digit_count
from streamdaq.measures.any_column.tuple import Tuple
from streamdaq.measures.base import RoundableDataQualityMeasure
from streamdaq.utils.data_type_applicability import DataTypeApplicability


@dataclass
class MeanIntegerPartLength(RoundableDataQualityMeasure):
    _applicability: ClassVar[DataTypeApplicability] = DataTypeApplicability.NUMERIC_ONLY
    _dependencies: ClassVar[list[type[Self]]] = [Tuple]

    def get_reducer(self) -> pw.ColumnExpression:
        return self._round_reducer_if_needed(
            pw.apply_with_type(
                lambda elements: mean(integer_part_digit_count(elements)),
                float,
                pw.this[Tuple._get_internal_shared_column_name(self.column)],
            )
        )
