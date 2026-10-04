"""Tests for the shared IO helpers."""

from streamdaq.io.utils import ensure_unique_mqtt_client_id, split_connector_params


class TestEnsureUniqueMqttClientId:
    def test_appends_client_id_when_missing_and_no_query(self):
        result = ensure_unique_mqtt_client_id("mqtt://host:1883")
        assert "?client_id=streamdaq_reader_" in result

    def test_appends_with_ampersand_when_query_present(self):
        result = ensure_unique_mqtt_client_id("mqtt://host:1883?topic=x")
        assert "&client_id=streamdaq_reader_" in result

    def test_uniquifies_an_existing_client_id(self):
        result = ensure_unique_mqtt_client_id("mqtt://host:1883?client_id=abc")
        assert result.startswith("mqtt://host:1883?client_id=abc_")
        assert result != "mqtt://host:1883?client_id=abc"

    def test_role_is_reflected_in_the_generated_id(self):
        assert "streamdaq_writer_" in ensure_unique_mqtt_client_id(
            "mqtt://host:1883", role="writer"
        )

    def test_successive_calls_produce_distinct_ids(self):
        assert ensure_unique_mqtt_client_id("mqtt://h") != ensure_unique_mqtt_client_id("mqtt://h")


class TestSplitConnectorParams:
    def test_explicit_connector_params_are_used_verbatim(self):
        params = {"connector_params": {"uri": "mqtt://h"}, "data_type": "native"}
        assert split_connector_params(params, ("data_type", "schema")) == {"uri": "mqtt://h"}

    def test_flat_params_drop_reserved_keys(self):
        params = {"uri": "mqtt://h", "data_type": "native", "schema": {"x": "int"}}
        assert split_connector_params(params, ("data_type", "schema")) == {"uri": "mqtt://h"}
