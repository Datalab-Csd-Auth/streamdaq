import pathway as pw

from streamdaq.schema.base import Schema, ValidatableBaseSchema


class TestSchemaFromTypes:
    def test_creates_schema_with_basic_types(self):
        schema = Schema.from_types("TestSchema", name=str, value=float)
        assert issubclass(schema, pw.Schema)
        assert "name" in schema.column_names()
        assert "value" in schema.column_names()

    def test_creates_schema_with_list_types(self):
        schema = Schema.from_types("ListSchema", items=list[int])
        assert "items" in schema.column_names()


class TestSchemaFromDict:
    def test_creates_schema_from_dict(self):
        columns = {"x": {"dtype": int}, "y": {"dtype": str}}
        schema = Schema.from_dict(columns=columns, name="DictSchema")
        assert "x" in schema.column_names()
        assert "y" in schema.column_names()


class TestSchemaColumn:
    def test_returns_column_definition(self):
        col = Schema.column(dtype=int, primary_key=True)
        assert col is not None


class TestSchemaCompact:
    def test_creates_compact_schema(self):
        schema = Schema.compact("CompactSchema")
        assert issubclass(schema, pw.Schema)
        assert "fields" in schema.column_names()
        assert "values" in schema.column_names()


class TestValidatableBaseSchema:
    def test_is_basemodel_subclass(self):
        from pydantic import BaseModel

        assert issubclass(ValidatableBaseSchema, BaseModel)
