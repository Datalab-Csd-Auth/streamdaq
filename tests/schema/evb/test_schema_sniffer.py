"""Integration tests for discover_native_evb_schema — real multiprocessing, no mocking."""

import pathway as pw
import pytest

from streamdaq.schema.evb.definitions import EVBSchema
from streamdaq.schema.evb.mock_generator import EVBMockStream
from streamdaq.schema.evb.schema_sniffer import discover_native_evb_schema

# --- Module-level callables (picklable for multiprocessing spawn) ---


def get_table_function() -> pw.Table:
    return pw.io.python.read(
        EVBMockStream(nof_non_time_fields=6, nof_messages=15, sleep_between_sec=0.0),
        schema=EVBSchema,
    )


class _NeverValidStream(pw.io.python.ConnectorSubject):
    """Emits messages with 14-digit timestamps so on_change guard always rejects."""

    def run(self):
        for _ in range(5):
            self.next(
                measurements=[
                    {
                        "name": "Streamdaq_Demo",
                        "tags": {"plant": "X", "unit_id": "000000"},
                        "type": "Points",
                        "fields": ["time", "a", "b"],
                        "values": [[16453345350000, 1.0, 2.0]],  # 14 digits — invalid
                    }
                ]
            )


def get_table_function_never_valid() -> pw.Table:
    return pw.io.python.read(_NeverValidStream(), schema=EVBSchema)


# --- Tests ---


class TestDiscoverNativeEVBSchema:
    @pytest.mark.filterwarnings("ignore::DeprecationWarning")
    def test_happy_path_discovers_schema(self):
        result = discover_native_evb_schema(
            get_table_function=get_table_function, timeout_seconds=10
        )

        assert isinstance(result, tuple)
        assert len(result) == 6
        for field_name, field_type in result:
            assert isinstance(field_name, str)
            assert field_type is float

    @pytest.mark.filterwarnings("ignore::DeprecationWarning")
    def test_timeout_on_invalid_source(self):
        with pytest.raises(TimeoutError, match="did not respond within"):
            discover_native_evb_schema(
                get_table_function=get_table_function_never_valid, timeout_seconds=2
            )
