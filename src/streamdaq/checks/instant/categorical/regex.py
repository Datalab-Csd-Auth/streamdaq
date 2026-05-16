import re
from dataclasses import dataclass
from typing import ClassVar

import pathway as pw

from streamdaq.checks.base import SingleColumnDataQualityCheck
from streamdaq.checks.instant.base import InstantDataQualityCheck
from streamdaq.utils.data_type_applicability import DataTypeApplicability


@dataclass
class Regex(InstantDataQualityCheck, SingleColumnDataQualityCheck):
    regex: str
    _applicability: ClassVar[DataTypeApplicability] = DataTypeApplicability.CATEGORICAL_ONLY

    def __post_init__(self):
        self._pattern = re.compile(self.regex)

    def get_measurement_expression(self) -> pw.ColumnExpression:
        return pw.apply_with_type(
            lambda value: self._pattern.match(str(value)) is not None, bool, pw.this[self.column]
        )
