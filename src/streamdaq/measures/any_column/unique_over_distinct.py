from dataclasses import dataclass
from typing import ClassVar, Self

import pathway as pw

from streamdaq.computations.generic import count_singletons
from streamdaq.computations.numeric import fraction
from streamdaq.measures.any_column.tuple import Tuple
from streamdaq.measures.base import RoundableDataQualityMeasure
from streamdaq.utils.data_type_applicability import DataTypeApplicability


@dataclass
class UniqueOverDistinct(RoundableDataQualityMeasure):
    _applicability: ClassVar[DataTypeApplicability] = DataTypeApplicability.ANY_COLUMN
    _dependencies: ClassVar[list[type[Self]]] = [Tuple]

    def get_reducer(self) -> pw.ColumnExpression:
        return self._round_reducer_if_needed(
            pw.apply_with_type(
                lambda elements: fraction(count_singletons(elements), len(set(elements))),
                float,
                pw.this[Tuple._get_internal_shared_column_name(self.column)],
            )
        )
