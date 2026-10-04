import pathway as pw

from streamdaq.schema.evb.definitions import EVBSchema
from streamdaq.schema.evb.mock_generator import EVBMockStream


class TestEVBMockStreamDefaults:
    def test_constructor_defaults(self):
        stream = EVBMockStream()
        assert stream.nof_messages == 10
        assert stream.nof_non_time_fields == 15
        assert stream.sleep_between_sec == 0.0
        assert stream.values_min == 0.0
        assert stream.values_max == 100.0
        assert stream.round_values == 2


class TestEVBGenerator:
    def test_yields_correct_number_of_messages(self):
        stream = EVBMockStream(nof_messages=5, nof_non_time_fields=3)
        messages = list(stream.evb_generator(num_messages=5, non_time_fields=3))
        assert len(messages) == 5

    def test_message_structure(self):
        stream = EVBMockStream()
        messages = list(stream.evb_generator(num_messages=1, non_time_fields=2))
        msg = messages[0]
        assert "measurements" in msg
        measurement = msg["measurements"][0]
        assert "name" in measurement
        assert "tags" in measurement
        assert "type" in measurement
        assert "fields" in measurement
        assert "values" in measurement

    def test_fields_and_values_length_match(self):
        stream = EVBMockStream()
        messages = list(stream.evb_generator(num_messages=1, non_time_fields=4))
        meas = messages[0]["measurements"][0]
        assert len(meas["fields"]) == len(meas["values"][0])
        assert len(meas["fields"]) == 5  # time + 4 non-time fields


class TestCorruptTimestamp:
    def test_no_corruption_returns_original(self):
        stream = EVBMockStream()
        ts = 1645334535000
        assert stream.corrupt_timestamp(ts, corruption_probability=0.0) == ts

    def test_always_corrupts_multiplies_by_10(self):
        stream = EVBMockStream()
        ts = 1645334535000
        assert stream.corrupt_timestamp(ts, corruption_probability=1.0) == ts * 10


class TestCorruptFields:
    def test_no_corruption_preserves_order(self):
        stream = EVBMockStream()
        fields = ["time", "temp", "humidity"]
        assert stream.corrupt_fields(fields, corruption_probability=0.0) == fields

    def test_corruption_preserves_elements(self):
        stream = EVBMockStream()
        fields = ["time", "temp", "humidity"]
        result = stream.corrupt_fields(fields, corruption_probability=1.0)
        assert sorted(result) == sorted(fields)


class TestCorruptValues:
    def test_no_corruption_returns_original(self):
        stream = EVBMockStream()
        values = [1645334535000, 42.0, 55.0]
        assert stream.corrupt_values(values, corruption_probability=0.0) == values

    def test_corruption_preserves_elements(self):
        stream = EVBMockStream()
        values = [1645334535000, 42.0, 55.0]
        result = stream.corrupt_values(values, corruption_probability=1.0)
        assert sorted(result) == sorted(values)


class TestEVBMockStreamRun:
    def test_run_produces_pathway_table(self):
        stream = EVBMockStream(nof_messages=3, nof_non_time_fields=2, sleep_between_sec=0.0)
        table = pw.io.python.read(stream, schema=EVBSchema)
        df = pw.debug.table_to_pandas(table)

        assert len(df) == 3
        for _, row in df.iterrows():
            measurements = row["measurements"]
            assert len(measurements) == 1
            meas = measurements[0].as_dict()
            assert "name" in meas
            assert "fields" in meas
            assert "values" in meas
            assert len(meas["fields"]) == 3  # time + 2 non-time fields
