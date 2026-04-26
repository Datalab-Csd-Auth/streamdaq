from dataclasses import dataclass
from typing import ClassVar, Self

import pathway as pw

from streamdaq.computations.numeric import first_digit_frequencies
from streamdaq.measures.any_column.tuple import Tuple
from streamdaq.measures.base import RoundableDataQualityMeasure
from streamdaq.utils.data_type_applicability import DataTypeApplicability


@dataclass
class FirstDigitFreqs(RoundableDataQualityMeasure):
    _applicability: ClassVar[DataTypeApplicability] = DataTypeApplicability.NUMERIC_ONLY
    _dependencies: ClassVar[list[type[Self]]] = [Tuple]

    def get_reducer(self) -> pw.ColumnExpression:
        return pw.apply_with_type(
            first_digit_frequencies,
            dict[int, tuple[int, float]],
            pw.this[Tuple._get_internal_shared_column_name(self.column)],
            self.precision,
        )
