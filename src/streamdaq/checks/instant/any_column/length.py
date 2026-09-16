from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, ClassVar

import pathway as pw

from streamdaq.checks.base import SingleColumnDataQualityCheck
from streamdaq.checks.instant.base import InstantDataQualityCheck
from streamdaq.translators.string_to_callable import resolve_must_be
from streamdaq.utils.data_type_applicability import DataTypeApplicability
from streamdaq.utils.picklable import Lambda


@dataclass
class Length(InstantDataQualityCheck, SingleColumnDataQualityCheck):
    must_be: Callable[[Any], bool] | str
    _applicability: ClassVar[DataTypeApplicability] = DataTypeApplicability.ANY_COLUMN

    def __post_init__(self):
        # Validate without mutating to simplify serialization to the API
        resolve_must_be(self.must_be)

    def get_measurement_expression(self) -> pw.ColumnExpression:
        predicate = resolve_must_be(self.must_be)
        return pw.apply_with_type(
            Lambda(lambda value: predicate(len(str(value)))), bool, pw.this[self.column]
        )
