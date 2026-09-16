from dataclasses import dataclass, field
from typing import ClassVar, Literal

import pathway as pw

from streamdaq.computations.generic import is_monotonic, sort_list_b_based_on_a
from streamdaq.measures.any_column.tuple import Tuple
from streamdaq.measures.base import DataQualityMeasure
from streamdaq.utils.data_type_applicability import DataTypeApplicability
from streamdaq.utils.picklable import Lambda


@dataclass
class Monotonic(DataQualityMeasure):
    time_column: str
    direction: Literal["asc", "desc"] = field(default="asc")
    strict: bool = field(default=True)
    _applicability: ClassVar[DataTypeApplicability] = DataTypeApplicability.ANY_COLUMN
    _dependencies: ClassVar[list[type[DataQualityMeasure]]] = [Tuple]

    def __post_init__(self):
        if self.direction not in ("asc", "desc"):
            raise ValueError(
                f"Cannot initialize a monotonic check on column `{self.column}` "
                f"Direction must be 'asc' or 'desc', got {self.direction}"
            )

    def get_reduce_kwargs(self) -> dict[str, pw.ColumnExpression]:
        reduce_kwargs = super().get_reduce_kwargs()  # reduce args for Tuple(self.column)

        # constructs reduce args for Tuple(self.time_column)
        additional_kw = Tuple._get_internal_shared_column_name(self.time_column)
        reduce_kwargs[additional_kw] = Tuple(self.time_column).get_reducer()
        return reduce_kwargs

    def get_expression(self) -> pw.ColumnExpression:
        direction = self.direction
        strict = self.strict

        def is_monotonic_over_time(timestamps: tuple, values: tuple) -> bool:
            values_ordered_by_time = sort_list_b_based_on_a(timestamps, values)
            return is_monotonic(values_ordered_by_time, direction, strict)

        return pw.apply_with_type(
            Lambda(is_monotonic_over_time),
            bool,
            pw.this[Tuple._get_internal_shared_column_name(self.time_column)],
            pw.this[Tuple._get_internal_shared_column_name(self.column)],
        )
