from dataclasses import dataclass
from typing import Any, ClassVar

import pathway as pw

from streamdaq.checks.instant.base import InstantDataQualityCheck
from streamdaq.utils.data_type_applicability import DataTypeApplicability


@dataclass
class InSet(InstantDataQualityCheck):
    allowed_values: set[Any]
    _applicability: ClassVar[DataTypeApplicability] = DataTypeApplicability.ANY_COLUMN

    def get_reducer(self) -> pw.ColumnExpression:
        return pw.apply_with_type(
            lambda value: value in self.allowed_values, bool, pw.this[self.column]
        )
