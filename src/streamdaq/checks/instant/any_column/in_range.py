from dataclasses import dataclass, field
from typing import ClassVar

import pathway as pw

from streamdaq.checks.instant.base import InstantDataQualityCheck
from streamdaq.utils.data_type_applicability import DataTypeApplicability


@dataclass
class InRange(InstantDataQualityCheck):
    low: int | float
    high: int | float
    inclusive_low: bool = field(default=True)
    inclusive_high: bool = field(default=False)
    _applicability: ClassVar[DataTypeApplicability] = DataTypeApplicability.ANY_COLUMN

    def get_reducer(self) -> pw.ColumnExpression:
        low_condition = (
            pw.this[self.column] > self.low
            if self.inclusive_low
            else pw.this[self.column] >= self.low
        )
        high_condition = (
            pw.this[self.column] < self.high
            if self.inclusive_high
            else pw.this[self.column] <= self.high
        )
        return low_condition & high_condition
