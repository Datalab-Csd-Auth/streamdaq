from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, ClassVar

import pathway as pw

from streamdaq.checks.base import SingleColumnDataQualityCheck
from streamdaq.checks.instant.base import InstantDataQualityCheck
from streamdaq.translators.string_to_callable import resolve_must_be
from streamdaq.utils.data_type_applicability import DataTypeApplicability
from streamdaq.utils.picklable import Lambda


@dataclass
class Value(InstantDataQualityCheck, SingleColumnDataQualityCheck):
    must_be: Callable[[Any], bool] | str
    transformation: Callable[[Any], Any] | None = field(default=None)
    _applicability: ClassVar[DataTypeApplicability] = DataTypeApplicability.ANY_COLUMN

    def __post_init__(self):
        # Validate without mutating to simplify serialization to API
        resolve_must_be(self.must_be)

    def get_measurement_expression(self) -> pw.ColumnExpression:
        predicate = resolve_must_be(self.must_be)
        if self.transformation is None:
            return pw.apply_with_type(predicate, bool, pw.this[self.column])
        return pw.apply_with_type(
            Lambda(lambda value: predicate(self.transformation(value))),
            bool,
            pw.this[self.column],
        )
