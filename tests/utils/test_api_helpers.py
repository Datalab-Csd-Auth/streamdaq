"""Tests for the connector-factory and validation helpers in ``utils/api.py``.

Network-touching Pathway IO calls (``pw.io.mqtt``, ``pw.io.kafka``, etc.) are
patched so the *factory wiring* — parameter splitting, client-id injection,
mode handling — is tested without a live broker. The pure validation helper is
tested directly.
"""

import functools
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pandas as pd
import pathway as pw
import pytest

from streamdaq.utils.api import (
    _StreamingInputCallable,
    _validate_for_start,
    build_csv_input,
    build_kafka_input,
    build_mqtt_input,
    build_mqtt_output,
    build_parquet_input,
    build_python_connector_input,
)


class TestCsvInputFactory:
    def test_streaming_mode_uses_csv_read(self):
        callable_ = build_csv_input({"path": "/tmp/data.csv"})
        assert isinstance(callable_, functools.partial)
        assert "mode" not in callable_.keywords
        assert callable_.keywords["path"] == "/tmp/data.csv"

    def test_static_mode_uses_fs_read_static(self):
        callable_ = build_csv_input({"path": "/tmp/data.csv", "mode": "static"})
        assert isinstance(callable_, functools.partial)
        assert callable_.keywords["mode"] == "static"
        assert callable_.keywords["format"] == "csv"


class TestParquetInputFactory:
    def test_reads_parquet_into_a_pathway_table(self, tmp_path):
        path = tmp_path / "data.parquet"
        pd.DataFrame({"x": [1, 2, 3]}).to_parquet(path)

        table = build_parquet_input({"path": str(path)})()
        result = pw.debug.table_to_pandas(table)

        assert sorted(result["x"].tolist()) == [1, 2, 3]


class TestMqttOutput:
    def test_injects_client_id_when_absent(self):
        with patch("streamdaq.utils.api.pw.io.mqtt.write") as mock_write:
            build_mqtt_output(MagicMock(), uri="mqtt://broker:1883/topic")
            uri = mock_write.call_args.kwargs["uri"]
            assert "client_id=streamdaq_writer_" in uri

    def test_uses_ampersand_when_query_already_present(self):
        with patch("streamdaq.utils.api.pw.io.mqtt.write") as mock_write:
            build_mqtt_output(MagicMock(), uri="mqtt://broker:1883/topic?qos=1")
            uri = mock_write.call_args.kwargs["uri"]
            assert "?qos=1&client_id=streamdaq_writer_" in uri

    def test_makes_existing_client_id_unique(self):
        with patch("streamdaq.utils.api.pw.io.mqtt.write") as mock_write:
            build_mqtt_output(MagicMock(), uri="mqtt://broker/topic?client_id=fixed")
            uri = mock_write.call_args.kwargs["uri"]
            assert "client_id=fixed_" in uri


class TestStreamingInputFactories:
    def test_mqtt_factory_splits_reserved_keys(self):
        callable_ = build_mqtt_input(
            {"data_type": "native", "schema": {"x": "int"}, "uri": "mqtt://b/t"}
        )
        assert isinstance(callable_, _StreamingInputCallable)
        assert callable_.connector_type == "mqtt"
        assert callable_.data_type == "native"
        assert callable_.schema_params == {"x": "int"}
        assert "data_type" not in callable_.connector_params
        assert "schema" not in callable_.connector_params

    def test_kafka_factory_defaults_to_native(self):
        callable_ = build_kafka_input({"topic": "t"})
        assert callable_.connector_type == "kafka"
        assert callable_.data_type == "native"

    def test_python_connector_captures_module_and_class(self):
        callable_ = build_python_connector_input(
            {"module": "pkg.mod", "class_name": "Subject", "data_type": "native"}
        )
        assert callable_.connector_type == "python_connector"
        assert callable_.extra_params == {"module": "pkg.mod", "class_name": "Subject"}

    def test_mqtt_native_call_injects_unique_client_id(self):
        callable_ = build_mqtt_input({"uri": "mqtt://broker/topic", "schema": {"x": "int"}})
        with patch("streamdaq.utils.api.pw.io.mqtt.read") as mock_read:
            callable_()
            uri = mock_read.call_args.kwargs["uri"]
            assert "client_id=streamdaq_reader_" in uri


class TestValidateForStart:
    def _config(self, **overrides):
        base = dict(
            input=object(),
            output=object(),
            windowby_column="ts",
            window_checks_config=SimpleNamespace(checks=[object()]),
            instant_checks=[],
        )
        base.update(overrides)
        return SimpleNamespace(**base)

    def test_complete_config_has_no_errors(self):
        assert _validate_for_start(self._config()) == []

    @pytest.mark.parametrize(
        "override, expected_error",
        [
            (dict(input=None), "Input configuration is required."),
            (dict(output=None), "Output configuration is required."),
            (dict(windowby_column=None), "Windowby column is required."),
            (dict(window_checks_config=None), "Window configuration is required."),
        ],
    )
    def test_each_missing_field_reported(self, override, expected_error):
        errors = _validate_for_start(self._config(**override))
        assert expected_error in errors

    def test_requires_at_least_one_check(self):
        config = self._config(instant_checks=[], window_checks_config=SimpleNamespace(checks=[]))
        errors = _validate_for_start(config)
        assert "At least one instant check or window check is required." in errors

    def test_instant_check_alone_satisfies_check_requirement(self):
        config = self._config(
            instant_checks=[object()], window_checks_config=SimpleNamespace(checks=[])
        )
        errors = _validate_for_start(config)
        assert "At least one instant check or window check is required." not in errors
