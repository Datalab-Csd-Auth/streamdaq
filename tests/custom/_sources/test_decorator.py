"""``@source`` registers a factory under a name in ``SOURCE_REGISTRY`` and validates its format."""

import pathway as pw
import pytest

from streamdaq.api.registries import SOURCE_REGISTRY
from streamdaq.custom import source


class TestSourceRegistration:
    def test_name_defaults_to_function_name(self):
        @source()
        def _my_native_source(**params):
            return pw.debug.table_from_markdown("x\n1")

        assert "_my_native_source" in SOURCE_REGISTRY
        assert callable(SOURCE_REGISTRY["_my_native_source"])

    def test_explicit_name_overrides_function_name(self):
        @source(name="ExplicitSource")
        def _source_function_name(**params):
            return pw.debug.table_from_markdown("x\n1")

        assert "ExplicitSource" in SOURCE_REGISTRY
        assert "_source_function_name" not in SOURCE_REGISTRY

    def test_decorator_returns_the_original_function(self):
        def _factory(**params):
            return pw.debug.table_from_markdown("x\n1")

        decorated = source(name="ReturnedSource")(_factory)
        assert decorated is _factory

    def test_invalid_data_format_is_rejected(self):
        with pytest.raises(ValueError, match="data_format"):
            source(name="BadSource", data_format="tabular")
