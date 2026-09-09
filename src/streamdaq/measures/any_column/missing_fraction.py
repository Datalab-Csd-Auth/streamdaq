from dataclasses import dataclass, field
from typing import Any, ClassVar, Self

import pathway as pw

from streamdaq.computations.generic import merge_missing_values, set_conformance_count
from streamdaq.computations.numeric import fraction
from streamdaq.measures.any_column.count import Count
from streamdaq.measures.any_column.tuple import Tuple
from streamdaq.measures.base import RoundableDataQualityMeasure
from streamdaq.utils.data_type_applicability import DataTypeApplicability
from streamdaq.utils.picklable import Lambda


@dataclass
class MissingFraction(RoundableDataQualityMeasure):
    disguised: list[Any] = field(default_factory=Lambda(lambda: []))
    _applicability: ClassVar[DataTypeApplicability] = DataTypeApplicability.ANY_COLUMN
    _explicit_missing_values: ClassVar[list[Any | None]] = [None, ""]
    _dependencies: ClassVar[list[type[Self]]] = [Tuple, Count]

    def get_expression(self) -> pw.ColumnExpression:
        all_missing_values = merge_missing_values(self.disguised, self._explicit_missing_values)
        return self._round_reducer_if_needed(
            pw.apply_with_type(
                Lambda(
                    lambda elements, total_count: fraction(
                        set_conformance_count(elements, all_missing_values), total_count
                    )
                ),
                float,
                pw.this[Tuple._get_internal_shared_column_name(self.column)],  # elements
                pw.this[Count._get_internal_shared_column_name(self.column)],  # total_count
            )
        )
