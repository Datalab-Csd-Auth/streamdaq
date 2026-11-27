from typing import Any

import pathway as pw
from pydantic import ValidationError

from streamdaq.schema.evb.definitions import (
    EVBKeyNames,
    ValidatableEVBSchema,
    _StreamdaqInternalColumnNames,
)
from streamdaq.schema.evb.lambda_factory import LambdaFactory

_RECORD = "_record"
_JSON_ACCESSORS: dict[type, str] = {
    bool: "as_bool",
    int: "as_int",
    float: "as_float",
    str: "as_str",
}


def _zip_fields_and_values(fields: pw.Json, values: pw.Json, tags: pw.Json) -> pw.Json:
    return pw.Json({**dict(zip(fields.as_list(), values.as_list())), **tags.as_dict()})


def _validate_with_pydantic(raw_evb: tuple[pw.Json]) -> str | None:
    try:
        ValidatableEVBSchema(**Transform.to_pydantic_validatable(raw_evb))
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
    def explode_top_level(cls) -> dict[str, pw.ColumnExpression]:
        return {
            EVBKeyNames.NAME: pw.this[EVBKeyNames.MEASUREMENTS][EVBKeyNames.NAME].as_str(),
            EVBKeyNames.TAGS: pw.this[EVBKeyNames.MEASUREMENTS][EVBKeyNames.TAGS],
            EVBKeyNames.TYPE: pw.this[EVBKeyNames.MEASUREMENTS][EVBKeyNames.TYPE].as_str(),
            EVBKeyNames.FIELDS: pw.this[EVBKeyNames.MEASUREMENTS][EVBKeyNames.FIELDS],
            EVBKeyNames.VALUES: pw.this[EVBKeyNames.MEASUREMENTS][EVBKeyNames.VALUES],
        }

    @classmethod
    def enrich_with_pydantic_errors(cls) -> dict[str, pw.ColumnExpression]:
        return {
            _StreamdaqInternalColumnNames.PYDANTIC_ERRORS: pw.apply_with_type(
                _validate_with_pydantic, str | None, pw.this[EVBKeyNames.MEASUREMENTS]
            )
        }

    @classmethod
    def extract_time_from_fields_values(cls) -> dict[str, pw.ColumnExpression]:
        return {
            _StreamdaqInternalColumnNames.TIME: pw.apply_with_type(
                LambdaFactory.get_nth_list_element(0, int), int, pw.this.values
            ),
            EVBKeyNames.VALUES: pw.apply_with_type(
                LambdaFactory.get_list_elements_from_n_to_end(1, float),
                list[float],
                pw.this[EVBKeyNames.VALUES],
            ),
            EVBKeyNames.FIELDS: pw.apply_with_type(
                LambdaFactory.get_list_elements_from_n_to_end(1, str),
                list[str],
                pw.this[EVBKeyNames.FIELDS],
            ),
        }

    @classmethod
    def zip_fields_and_values(cls) -> dict[str, pw.ColumnExpression]:
        return {
            _RECORD: pw.apply_with_type(
                _zip_fields_and_values,
                pw.Json,
                pw.this[EVBKeyNames.FIELDS],
                pw.this[EVBKeyNames.VALUES],
                pw.this[EVBKeyNames.TAGS],
            )
        }

    @classmethod
    def to_native(
        cls, native_evb_schema: dict[str, tuple[tuple[str, type], ...]]
    ) -> dict[str, pw.ColumnExpression]:
        # Columns are looked up by field name, so reordered fields don't swap values
        record = pw.this[_RECORD]
        return {
            column_name: pw.unwrap(getattr(record.get(column_name), _JSON_ACCESSORS[dtype])())
            for column_name, dtype in native_evb_schema["fields"]
        } | {tag: record.get(tag).as_str() for tag, _ in native_evb_schema["tags"]}

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
            _RECORD,
        ]


def convert_raw_evb_to_native_format(
    raw_evb_table: pw.Table, native_evb_schema: dict[str, tuple[tuple[str, type], ...]]
) -> pw.Table:
    return (
        raw_evb_table.with_columns(**Transform.enrich_with_pydantic_errors())
        .flatten(pw.this[EVBKeyNames.MEASUREMENTS])
        .with_columns(**Transform.explode_top_level())
        .flatten(pw.this[EVBKeyNames.VALUES])
        .with_columns(**Transform.zip_fields_and_values())
        .with_columns(**Transform.extract_time_from_fields_values())
        .with_columns(**Transform.enrich_with_validation_errors_report())
        .with_columns(**Transform.to_native(native_evb_schema))
        .without(*Transform.cleanup_column_names())
    )
