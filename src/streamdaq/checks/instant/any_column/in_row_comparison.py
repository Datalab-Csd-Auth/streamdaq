import operator
from dataclasses import dataclass
from typing import ClassVar, Literal

import pathway as pw

from streamdaq.checks.instant.base import InstantDataQualityCheck
from streamdaq.utils.data_type_applicability import DataTypeApplicability


@dataclass
class InRowComparison(InstantDataQualityCheck):
    other_column: str
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

    def get_reducer(self) -> pw.ColumnExpression:
        return pw.apply_with_type(
            lambda left, right: self._str_to_operator_map[self.operator](left, right),
            bool,
            pw.this[self.column],
            pw.this[self.other_column],
        )
