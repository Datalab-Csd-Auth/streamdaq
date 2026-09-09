from dataclasses import dataclass, field
from typing import ClassVar, Self

import pathway as pw

from streamdaq.computations.numeric import are_numbers_frozen
from streamdaq.measures.any_column.sorted_tuple_value import SortedTupleValue
from streamdaq.measures.base import DataQualityMeasure
from streamdaq.utils.data_type_applicability import DataTypeApplicability
from streamdaq.utils.picklable import Lambda


@dataclass
class FrozenNumbers(DataQualityMeasure):
    epsilon: int | float = field(default=0.0)
    min_samples: int = field(default=1)
    _applicability: ClassVar[DataTypeApplicability] = DataTypeApplicability.NUMERIC_ONLY
    _dependencies: ClassVar[list[type[Self]]] = [SortedTupleValue]

    def __post_init__(self):
        if self.min_samples < 1:
            raise ValueError(
                f"Cannot initialize a FrozenNumbers check on column `{self.column}` "
                f"with a non-positive min_samples of {self.min_samples}. Must be >= 1."
            )
        if self.epsilon < 0:
            # TODO USE A PROPER LOGGER HERE WITH A WARNING
            print(
                f"WARNING: Cannot initialize a FrozenNumbers check on column `{self.column}` "
                f"with a non-positive epsilon of {self.epsilon}. "
                f"Casting to absolute value: epsilon={abs(self.epsilon)}"
            )
            self.epsilon = abs(self.epsilon)

    def get_expression(self) -> pw.ColumnExpression:
        epsilon = self.epsilon
        min_samples = self.min_samples
        return pw.apply_with_type(
            Lambda(
                lambda numbers_sorted_asc: are_numbers_frozen(
                    numbers_sorted_asc, epsilon, min_samples
                )
            ),
            bool,
            pw.this[SortedTupleValue._get_internal_shared_column_name(self.column)],
        )
