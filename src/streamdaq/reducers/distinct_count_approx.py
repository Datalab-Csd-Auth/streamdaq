import pathway as pw
from datasketch import HyperLogLogPlusPlus


class _DistinctCountApproxReducer(pw.BaseCustomAccumulator):
    def __init__(self, element: str):
        self.hpp_sketch = HyperLogLogPlusPlus()
        self.hpp_sketch.update(element.encode("utf-8"))

    @classmethod
    def from_row(cls, row):
        [value] = row
        return cls(str(value))

    def update(self, other):
        self.hpp_sketch.merge(other.hpp_sketch)

    def compute_result(self) -> float:
        return self.hpp_sketch.count()


distinct_count_approx_reducer = pw.reducers.udf_reducer(_DistinctCountApproxReducer)
