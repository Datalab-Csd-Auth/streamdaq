"""Tests for the built-in source classes and their auto-registration."""

from unittest.mock import patch

import pandas as pd
import pathway as pw
import pytest

from streamdaq.io.sources import SOURCE_REGISTRY
from streamdaq.io.sources.csv_source import CsvSource
from streamdaq.io.sources.kafka_source import KafkaSource
from streamdaq.io.sources.mqtt_source import MqttSource
from streamdaq.io.sources.parquet_source import ParquetSource
from streamdaq.io.sources.python_source import PythonConnectorSource


class TestSourceRegistration:
    def test_all_built_in_sources_are_registered_by_type(self):
        assert {"csv", "parquet", "python_connector", "kafka", "mqtt"} <= set(SOURCE_REGISTRY)

    def test_registry_value_builds_the_matching_source_instance(self):
        source = SOURCE_REGISTRY["mqtt"]({"connector_params": {"uri": "mqtt://b/t"}})
        assert isinstance(source, MqttSource)


class TestParamSplitting:
    def test_reserved_keys_are_excluded_from_connector_params(self):
        source = MqttSource({"data_type": "native", "schema": {"x": "int"}, "uri": "mqtt://b/t"})
        assert source.data_type == "native"
        assert source.schema_params == {"x": "int"}
        assert source.connector_params == {"uri": "mqtt://b/t"}

    def test_python_connector_captures_module_and_class(self):
        source = PythonConnectorSource(
            {"module": "pkg.mod", "class_name": "Subject", "data_type": "native", "arg": 1}
        )
        assert (source.module, source.class_name) == ("pkg.mod", "Subject")
        assert source.connector_params == {"arg": 1}


class TestMqttSource:
    def test_native_call_injects_unique_client_id_and_json_format(self):
        source = MqttSource({"uri": "mqtt://broker/topic", "schema": {"x": "int"}})
        with patch("streamdaq.io.sources.mqtt_source.pw.io.mqtt.read") as mock_read:
            source()
            call = mock_read.call_args.kwargs
            assert "client_id=streamdaq_reader_" in call["uri"]
            assert call["format"] == "json"


class TestKafkaSource:
    def test_native_call_defaults_group_id(self):
        source = KafkaSource({"topic": "t"})
        with patch("streamdaq.io.sources.kafka_source.pw.io.kafka.read") as mock_read:
            source()
            assert mock_read.call_args.kwargs["group.id"].startswith("streamdaq_reader_")


class TestCsvSource:
    def test_streaming_mode_reads_via_csv(self):
        source = CsvSource({"path": "/tmp/data.csv"})
        with patch("streamdaq.io.sources.csv_source.pw.io.csv.read") as mock_read:
            source()
            assert mock_read.call_args.kwargs["path"] == "/tmp/data.csv"

    def test_static_mode_reads_via_fs(self):
        source = CsvSource({"path": "/tmp/data.csv", "mode": "static"})
        with patch("streamdaq.io.sources.csv_source.pw.io.fs.read") as mock_read:
            source()
            assert mock_read.call_args.kwargs["mode"] == "static"

    def test_compact_data_format_is_rejected(self):
        source = CsvSource({"path": "/tmp/data.csv", "data_type": "compact"})
        with pytest.raises(ValueError, match="does not support the 'compact' data format"):
            source()


class TestParquetSource:
    def test_reads_parquet_into_a_pathway_table(self, tmp_path):
        path = tmp_path / "data.parquet"
        pd.DataFrame({"x": [1, 2, 3]}).to_parquet(path)

        table = ParquetSource({"path": str(path)})()
        assert sorted(pw.debug.table_to_pandas(table)["x"].tolist()) == [1, 2, 3]

    def test_result_survives_dill_serialization(self, tmp_path):
        import dill

        path = tmp_path / "data.parquet"
        pd.DataFrame({"x": [1, 2, 3]}).to_parquet(path)

        source = dill.loads(dill.dumps(ParquetSource({"path": str(path)})))
        assert sorted(pw.debug.table_to_pandas(source())["x"].tolist()) == [1, 2, 3]

    def test_compact_data_format_is_rejected(self):
        source = ParquetSource({"path": "/tmp/data.parquet", "data_type": "compact"})
        with pytest.raises(ValueError, match="does not support the 'compact' data format"):
            source()
