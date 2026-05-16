from dataclasses import dataclass

import pathway as pw

# TODO THIS IS NOT READY YET, WE NEED TO WRAP SLIDING, TUMBLING, SESSION FROM PW


@dataclass
class Window:
    def to_pathway_window(self) -> pw.temporal.Window: ...
