from dataclasses import dataclass
from typing import ClassVar, Self

import pathway as pw

from streamdaq.measures.any_column.tuple import Tuple
from streamdaq.measures.base import DataQualityMeasure
from streamdaq.utils.data_type_applicability import DataTypeApplicability


def _sort_values_by_timestamp(values: tuple, timestamps: tuple) -> tuple:
    sorted_timestamps, sorted_values = zip(*sorted(zip(timestamps, values)))
    return sorted_values


@dataclass
class SortedTupleTime(DataQualityMeasure):
    time_column: str
    _applicability: ClassVar[DataTypeApplicability] = DataTypeApplicability.ANY_COLUMN
    _dependencies: ClassVar[list[type[Self]]] = [Tuple]

    def get_reduce_kwargs(self) -> pw.ColumnExpression:
        reduce_kwargs = super().get_reduce_kwargs()  # constructs reduce args for Tuple(self.column)

        # constructs reduce args for Tuple(self.time_column)
        additional_kw = Tuple._get_internal_shared_column_name(self.time_column)
        additional_arg = Tuple(self.time_column).get_reducer()
        reduce_kwargs[additional_kw] = additional_arg
        return reduce_kwargs

    def get_expression(self) -> pw.ColumnExpression:
        return pw.apply_with_type(
            _sort_values_by_timestamp,
            tuple,
            pw.this[Tuple._get_internal_shared_column_name(self.column)],  # values
            pw.this[Tuple._get_internal_shared_column_name(self.time_column)],  # timestamps
        )
