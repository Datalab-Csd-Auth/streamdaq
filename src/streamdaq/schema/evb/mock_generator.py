import copy
import random
import time
from collections.abc import Generator
from typing import Any

import pathway as pw

_ADJECTIVES = [
    "happy",
    "sad",
    "magnificent",
    "lonely",
    "fabulous",
    "annoyed",
    "friendly",
    "hostile",
    "hyped",
    "creative",
    "diligent",
    "decisive",
    "fearless",
    "inventive",
    "optimistic",
    "pessimistic",
]

_ANIMALS = [
    "rhino",
    "giraffe",
    "armadillo",
    "panda",
    "panda",
    "elephant",
    "tiger",
    "lion",
    "koala",
    "reindeer",
    "penguin",
    "ant",
    "fly",
    "tortoise",
    "fox",
    "eagle",
    "lynx",
    "flamingo",
    "kangaroo",
]


class EVBMockStream(pw.io.python.ConnectorSubject):
    def __init__(
        self,
        nof_messages: int = 10,
        nof_non_time_fields: int = 15,
        sleep_between_sec: float = 0.0,
        values_min: float = 0.0,
        values_max: float = 100.0,
        round_values: int = 2,
    ):
        super().__init__()
        self.nof_messages: int = nof_messages
        self.nof_non_time_fields: int = nof_non_time_fields
        self.sleep_between_sec: float = sleep_between_sec
        self.values_min: float = values_min
        self.values_max: float = values_max
        self.round_values: int = round_values

    def run(self):
        evb_stream = self.evb_generator(
            num_messages=self.nof_messages, non_time_fields=self.nof_non_time_fields
        )
        for evb_message in evb_stream:
            self.next(**evb_message)
            time.sleep(self.sleep_between_sec)

    def evb_generator(
        self, num_messages: int, non_time_fields: int, non_time_fields_prefix: str = "field"
    ) -> Generator[dict[str, Any], None, None]:
        """
        Generator function that yields mock EVB formatted dictionaries.
        """
        for _ in range(num_messages):
            current_timestamp_ms = int(time.time() * 1000)
            mock_unit_id = f"0123{random.randint(10, 99)}"

            fields = ["time"]
            current_values = [self.corrupt_timestamp(current_timestamp_ms)]

            for _ in range(non_time_fields):
                fields.append(f"{random.choice(_ADJECTIVES)}_{random.choice(_ANIMALS)}")
                current_values.append(
                    round(random.uniform(self.values_min, self.values_max), self.round_values)
                )

            fields = self.corrupt_fields(fields)
            # current_values = self.corrupt_values(current_values)

            evb_message = {
                "measurements": [
                    {
                        "name": "Streamdaq_Demo",
                        "tags": {"plant": "Philips", "unit_id": mock_unit_id},
                        "type": "Points",
                        "fields": fields,
                        "values": [current_values],
                        "another": "test",
                    }
                ],
            }
            yield evb_message

    def corrupt_timestamp(self, timestamp: int, corruption_probability: float = 0.1) -> int:
        if random.uniform(0, 1) > corruption_probability:
            return timestamp
        return timestamp * 10

    def corrupt_fields(self, fields: list[str], corruption_probability: float = 0.1) -> list[str]:
        if random.uniform(0, 1) > corruption_probability:
            return fields

        fields_copy = copy.deepcopy(fields)
        random.shuffle(fields_copy)
        return fields_copy

    def corrupt_values(self, values: list[Any], corruption_probability: float = 0.1) -> list[Any]:
        if random.uniform(0, 1) > corruption_probability:
            return values

        values_copy = copy.deepcopy(values)
        random.shuffle(values_copy)
        return values_copy
