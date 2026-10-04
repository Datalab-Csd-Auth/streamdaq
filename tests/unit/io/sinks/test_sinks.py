"""Tests for the built-in sink classes and their auto-registration."""

from unittest.mock import MagicMock, patch

from streamdaq.io.sinks import SINK_REGISTRY
from streamdaq.io.sinks.base import BaseSink
from streamdaq.io.sinks.jsonlines_sink import JsonlinesSink
from streamdaq.io.sinks.mqtt_sink import MqttSink


class TestSinkRegistration:
    def test_all_built_in_sinks_are_registered_by_type(self):
        assert {"jsonlines", "csv", "postgres", "kafka", "mqtt"} <= set(SINK_REGISTRY)

    def test_registry_value_is_a_callable_sink_instance(self):
        sink = SINK_REGISTRY["jsonlines"]
        assert isinstance(sink, BaseSink)
        assert callable(sink)


class TestJsonlinesSink:
    def test_delegates_to_pathway_writer(self):
        table = MagicMock()
        with patch("streamdaq.io.sinks.jsonlines_sink.pw.io.jsonlines.write") as mock_write:
            JsonlinesSink()(table, filename="out.jsonl")
            mock_write.assert_called_once_with(table, filename="out.jsonl")


class TestMqttSink:
    def test_injects_client_id_when_absent(self):
        with patch("streamdaq.io.sinks.mqtt_sink.pw.io.mqtt.write") as mock_write:
            MqttSink()(MagicMock(), uri="mqtt://broker:1883/topic")
            assert "client_id=streamdaq_writer_" in mock_write.call_args.kwargs["uri"]

    def test_makes_existing_client_id_unique(self):
        with patch("streamdaq.io.sinks.mqtt_sink.pw.io.mqtt.write") as mock_write:
            MqttSink()(MagicMock(), uri="mqtt://broker/topic?client_id=fixed")
            assert "client_id=fixed_" in mock_write.call_args.kwargs["uri"]
