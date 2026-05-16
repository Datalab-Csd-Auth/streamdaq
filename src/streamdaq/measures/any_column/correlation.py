from dataclasses import dataclass, field
from typing import ClassVar, Literal, Self

import pathway as pw

from streamdaq.computations.generic import calculate_correlation
from streamdaq.measures.any_column.tuple import Tuple
from streamdaq.measures.base import RoundableDataQualityMeasure
from streamdaq.utils.data_type_applicability import DataTypeApplicability


@dataclass
class Correlation(RoundableDataQualityMeasure):
    other_column: str
    method: Literal["pearson", "spearman", "kendall", "cramer"] = field(default="pearson")
    _applicability: ClassVar[DataTypeApplicability] = DataTypeApplicability.ANY_COLUMN
    _dependencies: ClassVar[list[type[Self]]] = [Tuple]

    def __post_init__(self):
        valid_correlation_methods = ["pearson", "spearman", "kendall", "cramer"]
        if self.method not in valid_correlation_methods:
            raise NotImplementedError(
                "Cannot instantiate a Correlation measure on columns "
                f"`{self.column}` and `{self.other_column}` because the provided correlation "
                f"method `{self.method}` is unknown. Valid options: {valid_correlation_methods}."
            )

    def get_expression(self) -> pw.ColumnExpression:
        return self._round_reducer_if_needed(
            pw.apply_with_type(
                calculate_correlation,
                float,
                pw.this[Tuple._get_internal_shared_column_name(self.column)],
                pw.this[Tuple._get_internal_shared_column_name(self.other_column)],
                self.method,
                self.precision,
            )
        )

    def get_reduce_kwargs(self) -> dict[str, pw.ColumnExpression]:
        reduce_kwargs = super().get_reduce_kwargs()  # constructs reduce args for Tuple(self.column)

        # constructs reduce args for Tuple(self.other_column)
        additional_kw = Tuple._get_internal_shared_column_name(self.other_column)
        additional_arg = Tuple(self.other_column).get_reducer()
        reduce_kwargs[additional_kw] = additional_arg
        return reduce_kwargs
