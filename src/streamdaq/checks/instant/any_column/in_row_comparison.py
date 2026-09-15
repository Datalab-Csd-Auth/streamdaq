import operator
from dataclasses import dataclass
from typing import ClassVar, Literal

import pathway as pw

from streamdaq.checks.base import MultiColumnDataQualityCheck
from streamdaq.checks.instant.base import InstantDataQualityCheck
from streamdaq.utils.data_type_applicability import DataTypeApplicability


@dataclass
class InRowComparison(InstantDataQualityCheck, MultiColumnDataQualityCheck):
    operator: Literal["lt", "le", "eq", "ne", "gt", "ge"]
    _applicability: ClassVar[DataTypeApplicability] = DataTypeApplicability.ANY_COLUMN

    def __post_init__(self):
        try:
            self.operator = getattr(operator, self.operator)
        except AttributeError:
            raise ValueError(
                f"Cannot instantiate an InRowComparison Check because operator `{self.operator}` "
                f"is unkown. Valid options: all function names (as str, e.g., 'le') in "
                "https://docs.python.org/3/library/operator.html"
            )
        if len(self.columns) != 2:
            raise ValueError(
                f"Cannot instantiate an InRowComparison Check because the columns {self.columns} "
                f"are not exactly 2. Please provide exactly 2 columns for this check."
            )

    def get_measurement_expression(self) -> pw.ColumnExpression:
        return pw.apply_with_type(
            lambda left, right: self.operator(left, right),
            bool,
            pw.this[self.columns[0]],
            pw.this[self.columns[1]],
        )
