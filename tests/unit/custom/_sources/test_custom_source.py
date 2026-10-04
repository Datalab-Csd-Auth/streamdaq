"""The custom-source runtime resolves native and compact factories into a native ``pw.Table``."""

import pandas as pd
import pathway as pw
import pytest

from streamdaq.custom import source
from streamdaq.io.sources.registry import SOURCE_REGISTRY
from streamdaq.schema.evb.definitions import EVBSchema


def _build_input(name: str, params: dict):
    return SOURCE_REGISTRY[name](params)


class TestNativeSource:
    def test_returns_the_factory_table(self):
        @source(name="NativeTable")
        def _native(**params):
            return pw.debug.table_from_pandas(pd.DataFrame({"x": [1, 2, 3]}))

        table = _build_input("NativeTable", {"connector_params": {}})()
        assert sorted(pw.debug.table_to_pandas(table)["x"].tolist()) == [1, 2, 3]

    def test_connector_params_are_forwarded_as_kwargs(self):
        @source(name="NativeEcho")
        def _native(**connector_params):
            value = connector_params["value"]
            return pw.debug.table_from_pandas(pd.DataFrame({"x": [value]}))

        table = _build_input("NativeEcho", {"connector_params": {"value": 42}})()
        assert pw.debug.table_to_pandas(table)["x"].tolist() == [42]

    def test_flat_params_minus_data_format_become_connector_params(self):
        @source(name="NativeFlat")
        def _native(**connector_params):
            return pw.debug.table_from_pandas(pd.DataFrame(connector_params))

        table = _build_input("NativeFlat", {"a": [1], "data_format": "native"})()
        result = pw.debug.table_to_pandas(table)
        assert result["a"].tolist() == [1]
        assert "data_format" not in result.columns

    def test_non_table_return_raises_a_clear_error(self):
        @source(name="NativeBad")
        def _native(**params):
            return "not a table"

        with pytest.raises(TypeError, match="native custom source must return a `pw.Table`"):
            _build_input("NativeBad", {"connector_params": {}})()


class TestCompactSource:
    def test_converts_then_applies_post_transform(self, monkeypatch):
        import streamdaq.io.sources.custom_source as custom_source

        evb = {
            "name": "Temp",
            "tags": {"plant": "F"},
            "type": "Points",
            "fields": ["time", "temperature"],
            "values": [[1645334535000, 60.0]],
        }
        monkeypatch.setattr(
            custom_source,
            "discover_native_evb_schema",
            lambda **kwargs: {"fields": (("temperature", float),), "tags": (("plant", str),)},
        )

        @source(name="CompactEVB", data_format="compact")
        def _compact(**params):
            raw = pw.debug.table_from_rows(schema=EVBSchema, rows=[([pw.Json(evb)],)])

            def post_transform(native_table):
                return native_table.select(*native_table, doubled=native_table.temperature * 2)

            return raw, post_transform

        table = _build_input("CompactEVB", {"connector_params": {}})()
        row = pw.debug.table_to_pandas(table).iloc[0]
        assert row["temperature"] == 60.0
        assert row["doubled"] == 120.0
        assert row["plant"] == "F"

    def test_non_tuple_return_raises_a_clear_error(self):
        @source(name="CompactBad", data_format="compact")
        def _compact(**params):
            return pw.debug.table_from_markdown("x\n1")

        with pytest.raises(TypeError, match="compact custom source must return"):
            _build_input("CompactBad", {"connector_params": {}})()
