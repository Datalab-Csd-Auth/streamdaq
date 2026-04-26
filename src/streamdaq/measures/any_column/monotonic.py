from dataclasses import dataclass, field
from typing import ClassVar, Literal, Self

import pathway as pw

from streamdaq.computations.generic import is_monotonic
from streamdaq.measures.any_column.tuple import Tuple
from streamdaq.measures.base import DataQualityMeasure
from streamdaq.utils.data_type_applicability import DataTypeApplicability


@dataclass
class Monotonic(DataQualityMeasure):
    direction: Literal["asc", "desc"] = field(default="asc")
    strict: bool = field(default=True)
    _applicability: ClassVar[DataTypeApplicability] = DataTypeApplicability.ANY_COLUMN
    _dependencies: ClassVar[list[type[Self]]] = [Tuple]

    def __post_init__(self):
        if self.direction not in ("asc", "desc"):
            raise ValueError(
                f"Cannot initialize a monotonic check on column `{self.column}` "
                f"Direction must be 'asc' or 'desc', got {self.direction}"
            )

    def get_reducer(self) -> pw.ColumnExpression:
        return pw.apply_with_type(
            lambda elements: is_monotonic(elements, self.direction, self.strict),
            bool,
            pw.this[Tuple._get_internal_shared_column_name(self.column)],
        )
