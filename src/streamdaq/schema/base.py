from typing import Any

import pathway as pw
from pathway.internals.helpers import _no_default_value_marker
from pydantic import BaseModel


class Schema:
    @classmethod
    def from_types(cls, _class_name: str, **kwargs) -> type[pw.Schema]:
        return pw.schema_from_types(_class_name, **kwargs)

    @classmethod
    def from_dict(cls, columns: dict[str, Any], name: str | None = None) -> pw.Schema:
        return pw.schema_from_dict(columns=columns, name=name)

    @classmethod
    def column(
        cls,
        *,
        primary_key: bool = False,
        default_value: Any | None = _no_default_value_marker,
        dtype: Any | None = None,
        name: str | None = None,
        append_only: bool | None = None,
        description: str | None = None,
    ) -> Any:
        return pw.column_definition(
            primary_key=primary_key,
            default_value=default_value,
            dtype=dtype,
            name=name,
            append_only=append_only,
            description=description,
        )

    @classmethod
    def compact(
        cls, _class_name: str, *, fields_dtype: type = str, values_dtype: type = float
    ) -> type[pw.Schema]:
        return pw.schema_from_types(
            _class_name,
            fields=list[fields_dtype],
            values=list[list[values_dtype]],
        )


class ValidatableBaseSchema(BaseModel):
    """https://pydantic.dev/docs/validation/latest/concepts/models/"""

    ...
