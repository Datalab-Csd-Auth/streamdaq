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

    def get_reducer(self) -> pw.ColumnExpression:
        return pw.apply_with_type(
            _sort_values_by_timestamp,
            tuple,
            pw.this[Tuple._get_internal_shared_column_name(self.column)],  # values
            pw.this[Tuple._get_internal_shared_column_name(self.time_column)],  # timestamps
        )
