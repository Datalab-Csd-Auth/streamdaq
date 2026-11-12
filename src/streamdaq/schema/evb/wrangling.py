from typing import Any

import pathway as pw
from pydantic import ValidationError

from streamdaq.schema.evb.definitions import (
    EVBKeyNames,
    ValidatableEVBSchema,
    _StreamdaqInternalColumnNames,
)
from streamdaq.schema.evb.lambda_factory import LambdaFactory


def _validate_with_pydantic(raw_evb: tuple[pw.Json]) -> str | None:
    try:
        ValidatableEVBSchema.model_validate(
            Transform.to_pydantic_validatable(raw_evb)
        )
        return None
    except ValidationError as e:
        return str(e)


def _construct_validation_errors_report_if_needed(
    pydantic_errors: str,
) -> dict[str, str | bool] | None:
    if not pydantic_errors:
        return None

    report = dict()
    report[_StreamdaqInternalColumnNames.PYDANTIC_ERRORS] = pydantic_errors
    return report


class Transform:
    @classmethod
    def to_pydantic_validatable(cls, raw_evb: tuple[pw.Json]) -> dict[str, list[dict[str, Any]]]:
        return {EVBKeyNames.MEASUREMENTS: [pw_json.as_dict() for pw_json in raw_evb]}

    @classmethod
    def _extract_evb_key_if_exists(
        cls,
        raw_measurement: pw.Json,
        key_value: str,
        optional: bool = False
    ) -> Any | None:
        m = raw_measurement.as_dict()
        key = EVBKeyNames(key_value)
        if (
            (field := key.get_matched(m)) is None 
            and not optional
        ):
            raise TypeError(
                f"Key '{key}' does not exist inside measurement"
            )

        return m.get(field, None)

    @classmethod
    def explode_top_level(cls) -> dict[str, pw.ColumnExpression]:
        return {
            EVBKeyNames.NAME: pw.apply_with_type(
                Transform._extract_evb_key_if_exists,
                str,
                pw.this[EVBKeyNames.MEASUREMENTS],
                key_value=EVBKeyNames.NAME.value
            ),
            EVBKeyNames.TAGS: pw.apply_with_type(
                Transform._extract_evb_key_if_exists,
                dict[str, str] | None,
                pw.this[EVBKeyNames.MEASUREMENTS],
                key_value=EVBKeyNames.TAGS.value,
                optional=True
            ),
            EVBKeyNames.TYPE: pw.apply_with_type(
                Transform._extract_evb_key_if_exists,
                str | None,
                pw.this[EVBKeyNames.MEASUREMENTS],
                key_value=EVBKeyNames.TYPE.value,
                optional=True
            ),
            EVBKeyNames.FIELDS: pw.apply_with_type(
                Transform._extract_evb_key_if_exists,
                list[str],
                pw.this[EVBKeyNames.MEASUREMENTS],
                key_value=EVBKeyNames.FIELDS.value,
            ),
            EVBKeyNames.VALUES: pw.apply_with_type(
                Transform._extract_evb_key_if_exists,
                list[list[Any]],
                pw.this[EVBKeyNames.MEASUREMENTS],
                key_value=EVBKeyNames.VALUES.value,
            ),
        }

    @classmethod
    def enrich_with_pydantic_errors(cls) -> dict[str, pw.ColumnExpression]:
        return {
            _StreamdaqInternalColumnNames.PYDANTIC_ERRORS: pw.apply_with_type(
                _validate_with_pydantic,
                str | None,
                pw.this[EVBKeyNames.MEASUREMENTS]
            )
        }

    @classmethod
    def extract_time_from_fields_values(cls) -> dict[str, pw.ColumnExpression]:
        return {
            _StreamdaqInternalColumnNames.TIME: pw.apply_with_type(
                LambdaFactory.get_nth_list_element(0),
                int,
                pw.this[EVBKeyNames.VALUES]
            ),
            EVBKeyNames.VALUES: pw.apply_with_type(
                LambdaFactory.get_list_elements_from_n_to_end(1),
                list[float],
                pw.this[EVBKeyNames.VALUES],
            ),
            EVBKeyNames.FIELDS: pw.apply_with_type(
                LambdaFactory.get_list_elements_from_n_to_end(1),
                list[str],
                pw.this[EVBKeyNames.FIELDS],
            ),
        }

    @classmethod
    def to_native(
        cls, native_evb_schema: dict[str, tuple[tuple[str, type], ...]]
    ) -> dict[str, pw.ColumnExpression]:
        return {
            column_name: pw.apply_with_type(
                LambdaFactory.get_nth_list_element(idx),
                dtype,
                pw.this[EVBKeyNames.VALUES]
            )
            for idx, (column_name, dtype) in enumerate(native_evb_schema["fields"])
        } | {
            tag: pw.coalesce(
                pw.this[EVBKeyNames.TAGS],
                pw.Json({})).get(tag).as_str()
            for tag, _ in native_evb_schema["tags"]
        }

    @classmethod
    def enrich_with_validation_errors_report(cls) -> dict[str, pw.ColumnExpression]:
        return {
            _StreamdaqInternalColumnNames.VALIDATION_ERRORS_REPORT: pw.apply_with_type(
                _construct_validation_errors_report_if_needed,
                dict[str, str | bool] | None,
                pw.this[_StreamdaqInternalColumnNames.PYDANTIC_ERRORS],
            )
        }

    @classmethod
    def cleanup_column_names(cls) -> list[str]:
        return [
            EVBKeyNames.MEASUREMENTS,
            EVBKeyNames.VALUES,
            EVBKeyNames.FIELDS,
            EVBKeyNames.TAGS,
            _StreamdaqInternalColumnNames.PYDANTIC_ERRORS,
        ]


def convert_raw_evb_to_native_format(
    raw_evb_table: pw.Table,
    native_evb_schema: dict[str, tuple[tuple[str, type], ...]]
) -> pw.Table:
    return (
        raw_evb_table.with_columns(**Transform.enrich_with_pydantic_errors())
        .flatten(pw.this[EVBKeyNames.MEASUREMENTS])
        .with_columns(**Transform.explode_top_level())
        .flatten(pw.this[EVBKeyNames.VALUES])
        .with_columns(**Transform.extract_time_from_fields_values())
        .with_columns(**Transform.enrich_with_validation_errors_report())
        .with_columns(**Transform.to_native(native_evb_schema))
        .without(*Transform.cleanup_column_names())
    )
