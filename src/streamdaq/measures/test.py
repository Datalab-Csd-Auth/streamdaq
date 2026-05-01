from pprint import pprint

from streamdaq.measures.any_column.availability import Availability
from streamdaq.utils.data_type_applicability import DataTypeApplicability

from streamdaq.measures import Mean, Percentiles

for applicability in DataTypeApplicability:
    print(f"{applicability}:")
    pprint([measure.__name__ for measure in applicability.available_measures])
    print()

measure = Mean("test")
print(measure.get_reducer())
print(measure.column)

measure = Percentiles()

measure = Availability("test", min_samples=9)
print(measure.get_reducer())
print(measure.column)

print(Mean._get_internal_shared_column_name("paokara"))
