import uuid

import pathway as pw

from streamdaq.checks import InRange
from streamdaq.schema.evb import convert_raw_evb_to_native_format, discover_native_evb_schema
from streamdaq.schema.evb.definitions import EVBSchema
from streamdaq.sessions.base import Session
from streamdaq.tasks.base import Task


def get_mqtt_table():
    client_id = f"streamdaq_reader_{uuid.uuid4().hex[:8]}"
    return pw.io.mqtt.read(
        uri=f"mqtt://127.0.0.1:1883/?client_id={client_id}",
        topic="evb/data",
        format="json",
        schema=EVBSchema,
    )


def main():
    print("Discovering EVB Schema from MQTT...")
    # This dynamically sniffs the first incoming MQTT message to infer the table columns
    native_schema = discover_native_evb_schema(
        get_table_function=get_mqtt_table, timeout_seconds=20
    )
    print(f"Discovered schema: {native_schema}")

    def get_processed_mqtt_table():
        raw_table = get_mqtt_table()
        # Converts the raw EVB JSON into a proper columnar table
        return convert_raw_evb_to_native_format(raw_table, native_schema)

    # Let's perform a simple check: Ensure time is within a valid range
    check = InRange(
        name="valid_time",
        column="time",
        low=0,
        high=9000000000000,
        inclusive_low=True,
        inclusive_high=True,
    )

    # The Task will read from MQTT, parse the EVB, perform the check, and write to JSONL
    task = Task(
        name="mqtt_reader_task",
        input=get_processed_mqtt_table,
        output=pw.io.jsonlines.write,
        output_kwargs={"filename": "output.jsonl"},
    ).add_instant_checks(check)

    session = Session(tasks=[task], name="mqtt_session")
    print("Starting session... Validated streaming output will be written to output.jsonl")
    print("Press Ctrl+C to stop.")

    # Start the pathway streaming engine
    session.start()


if __name__ == "__main__":
    main()
