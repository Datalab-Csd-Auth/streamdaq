from collections.abc import Callable
from dataclasses import dataclass
from typing import ClassVar

import pathway as pw

from streamdaq.computations.numeric import compute_deltas_over_time
from streamdaq.measures.any_column.tuple import Tuple
from streamdaq.measures.base import DataQualityMeasure
from streamdaq.utils.data_type_applicability import DataTypeApplicability
from streamdaq.utils.picklable import Lambda


@dataclass
class DeltasTuple(DataQualityMeasure):
    time_column: str
    _applicability: ClassVar[DataTypeApplicability] = DataTypeApplicability.NUMERIC_ONLY
    _dependencies: ClassVar[list[type[DataQualityMeasure]]] = [Tuple]

    # Applied to the time-ordered deltas tuple. ``None`` returns the tuple unaggregated.
    _aggregator: ClassVar[Callable[[tuple], int | float] | None] = None
    _result_dtype: ClassVar[type] = tuple

    def get_reduce_kwargs(self) -> pw.ColumnExpression:
        reduce_kwargs = super().get_reduce_kwargs()  # constructs reduce args for Tuple(self.column)

        # constructs reduce args for Tuple(self.time_column)
        additional_kw = Tuple._get_internal_shared_column_name(self.time_column)
        additional_arg = Tuple(self.time_column).get_reducer()
        reduce_kwargs[additional_kw] = additional_arg
        return reduce_kwargs

    def get_expression(self) -> pw.ColumnExpression:
        aggregator = type(self)._aggregator

        def compute(timestamps: tuple, values: tuple):
            result = compute_deltas_over_time(timestamps, values)
            return aggregator(result) if aggregator is not None else result

        return pw.apply_with_type(
            Lambda(compute),
            self._result_dtype,
            pw.this[Tuple._get_internal_shared_column_name(self.time_column)],  # timestamps
            pw.this[Tuple._get_internal_shared_column_name(self.column)],  # values
        )
