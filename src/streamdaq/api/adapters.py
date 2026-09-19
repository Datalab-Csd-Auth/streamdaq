import dataclasses
from typing import Any

from fastapi import HTTPException, status
from pydantic import TypeAdapter, ValidationError


def validate_coerce_params(
    target: type[Any],
    params: dict[str, Any],
    *,
    inject: dict[str, Any] | None = None,
    drop: tuple[str, ...] | None = None,
    label: str,
) -> dict[str, Any]:
    """Validate and Coerce ``params`` against ``target`` . When the ``target`` is a dataclass
    the coerced field values are returned with any ``drop`` keys removed; otherwise ``params``
    is passed through unchanged. Raises ``HTTPException`` (400) when validation fails.
    """
    try:
        validated = TypeAdapter(target).validate_python({**(inject or {}), **params})
    except ValidationError as e:
        errors = []
        for err in e.errors():
            loc = ".".join(map(str, err.get("loc", [])))
            errors.append(f"{loc}: {err.get('msg', 'Invalid')}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid params for {label}: {'; '.join(errors)}",
        )
    if not dataclasses.is_dataclass(validated) or isinstance(validated, type):
        return params
    coerced = dataclasses.asdict(validated)
    for key in drop or ():
        coerced.pop(key, None)
    return coerced
