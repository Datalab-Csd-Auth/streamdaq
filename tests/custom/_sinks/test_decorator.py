"""``@sink`` registers a user writer as a ``CustomSink`` in ``SINK_REGISTRY``."""

import dill

from streamdaq.custom import sink
from streamdaq.io.sinks import SINK_REGISTRY, CustomSink


class TestSinkRegistration:
    def test_name_defaults_to_function_name(self):
        @sink()
        def _my_file_sink(table, **params):
            return None

        assert isinstance(SINK_REGISTRY["_my_file_sink"], CustomSink)

    def test_explicit_name_overrides_function_name(self):
        @sink(name="ExplicitSink")
        def _source_function_name(table, **params):
            return None

        assert "ExplicitSink" in SINK_REGISTRY
        assert "_source_function_name" not in SINK_REGISTRY

    def test_decorator_returns_the_original_function(self):
        def _writer(table, **params):
            return None

        assert sink(name="ReturnedSink")(_writer) is _writer


class TestCustomSinkBehavior:
    def test_forwards_table_and_output_params_to_the_writer(self):
        received = {}

        @sink(name="RecordingSink")
        def _writer(table, **params):
            received["table"] = table
            received["params"] = params

        SINK_REGISTRY["RecordingSink"]("THE_TABLE", filename="out.jsonl")
        assert received == {"table": "THE_TABLE", "params": {"filename": "out.jsonl"}}

    def test_registered_sink_survives_dill_serialization(self):
        @sink(name="PicklableSink")
        def _writer(table, **params):
            return None

        restored = dill.loads(dill.dumps(SINK_REGISTRY["PicklableSink"]))
        assert isinstance(restored, CustomSink)
