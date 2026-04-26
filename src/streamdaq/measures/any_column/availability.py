from dataclasses import dataclass, field
from typing import ClassVar, Self

import pathway as pw

from streamdaq.measures.any_column.count import Count
from streamdaq.measures.base import DataQualityMeasure
from streamdaq.utils.data_type_applicability import DataTypeApplicability


@dataclass
class Availability(DataQualityMeasure):
    _applicability: ClassVar[DataTypeApplicability] = DataTypeApplicability.ANY_COLUMN
    _dependencies: ClassVar[list[type[Self]]] = [Count]
    min_samples: int = field(default=1)

    def __post_init__(self):
        if self.min_samples <= 0:
            raise ValueError(
                f"Cannot initialize an availability check on column `{self.column}` "
                f"with a non-positive availability of at least {self.min_samples}. Must be >= 1."
            )

    def get_reducer(self) -> pw.ColumnExpression:
        return pw.apply_with_type(
            lambda x: x >= self.min_samples,
            bool,
            pw.this[Count._get_internal_shared_column_name(self.column)],
        )
