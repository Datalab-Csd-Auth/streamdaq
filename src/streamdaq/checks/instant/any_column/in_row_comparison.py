import operator
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, ClassVar, Literal

import pathway as pw

from streamdaq.checks.base import MultiColumnDataQualityCheck
from streamdaq.checks.instant.base import InstantDataQualityCheck
from streamdaq.utils.data_type_applicability import DataTypeApplicability


@dataclass
class InRowComparison(InstantDataQualityCheck, MultiColumnDataQualityCheck):
    operator: Literal["lt", "le", "eq", "ne", "gt", "ge"]
    _applicability: ClassVar[DataTypeApplicability] = DataTypeApplicability.ANY_COLUMN

    def __post_init__(self):
        self._resolve_operator()  # validate without mutating to simplify serialization to API
        if len(self.columns) != 2:
            raise ValueError(
                f"Cannot instantiate an InRowComparison Check because the columns {self.columns} "
                f"are not exactly 2. Please provide exactly 2 columns for this check."
            )

    def _resolve_operator(self) -> Callable[[Any, Any], bool]:
        if not isinstance(self.operator, str):
            raise ValueError(
                f"Cannot instantiate an InRowComparison Check because operator `{self.operator}` "
                f"is not a string. Provide one of the operator function names (as str, e.g. 'le') "
                "in https://docs.python.org/3/library/operator.html"
            )
        try:
            return getattr(operator, self.operator)
        except AttributeError:
            raise ValueError(
                f"Cannot instantiate an InRowComparison Check because operator `{self.operator}` "
                f"is unknown. Valid options: all function names (as str, e.g., 'le') in "
                "https://docs.python.org/3/library/operator.html"
            )

    def get_measurement_expression(self) -> pw.ColumnExpression:
        operator_function = self._resolve_operator()
        return pw.apply_with_type(
            lambda left, right: operator_function(left, right),
            bool,
            pw.this[self.columns[0]],
            pw.this[self.columns[1]],
        )
