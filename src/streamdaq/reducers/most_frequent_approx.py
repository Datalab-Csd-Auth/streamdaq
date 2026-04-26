import pathway as pw

# TODO check if this implementation of HLL++ sketching is more reliable (Apache)
#  https://apache.github.io/datasketches-python/5.0.2/distinct_counting/hyper_log_log.html
from datasketches import frequent_items_error_type, frequent_strings_sketch


class _MostFrequentApproxReducer(pw.BaseCustomAccumulator):
    def __init__(self, element: str):
        # the sketch must be saved in its serialized (raw bytes) form, because it is not
        # "picklable" otherwise.
        # unfortunately, pathway uses pickle.dump(self) internally, so this is the only easy
        # solution I came up with
        # TODO re-explore alternatives, such as implementing __getstate__ and __setstate__
        # or __reduce__ class methods
        k = 3
        self.serialized_sketch = frequent_strings_sketch(k).serialize()
        sketch = frequent_strings_sketch.deserialize(self.serialized_sketch)
        sketch.update(element, 1)
        self.serialized_sketch = sketch.serialize()

    @classmethod
    def from_row(cls, row):
        [value] = row
        return cls(str(value))

    def update(self, other):
        other_sketch = frequent_strings_sketch.deserialize(other.serialized_sketch)
        sketch = frequent_strings_sketch.deserialize(self.serialized_sketch)
        sketch.merge(other_sketch)
        self.serialized_sketch = sketch.serialize()

    def compute_result(self) -> list:
        # TODO align the output format with the measures.any_column.most_frequent
        # current format:
        # (('Fudge_McChoc', 2, 2, 2), ('Ganache_Gobbler', 2, 2, 2), ('Truffle_Muncher', 1, 1, 1))
        # expected format:
        # ('Fudge_McChoc', 'Ganache_Gobbler') because they both have 2
        sketch = frequent_strings_sketch.deserialize(self.serialized_sketch)
        return sketch.get_frequent_items(frequent_items_error_type.NO_FALSE_NEGATIVES)


most_frequent_approx_reducer = pw.reducers.udf_reducer(_MostFrequentApproxReducer)
