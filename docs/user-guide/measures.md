# :straight_ruler: Measures

A measure is what a [window check](window-checks.md) computes over each window. All measures are imported from `streamdaq.measures`, and the first argument is always the column to measure:

```py
from streamdaq.measures import Count, InRangeFraction, Percentiles

Count("temperature")
InRangeFraction("temperature", low=-30, high=50, precision=2)
Percentiles("temperature", percentiles=[5, 50, 95])
```

!!! tip "Rounding with `precision`"
    Measures marked :material-check: in the **Prec.** column accept `precision=<digits>` to round their result, e.g. `Mean("temperature", precision=2)`.

!!! note "Column types"
    Measures are grouped by the kind of column they apply to. Using a measure on a column of another kind, such as a numeric measure on a text column, is not allowed and is rejected.

## Any column

| Measure | Parameters | Prec. | Returns |
|---|---|---|---|
| `Count` | | | Number of rows. |
| `Min`, `Max` | | | Smallest / largest value. |
| `Tuple` | | | All values, as a tuple. |
| `SortedTupleValue` | | | All values, sorted. |
| `SortedTupleTime` | `time_column` | | All values, ordered by `time_column`. |
| `Ndarray` | | | All values, as a NumPy array. |
| `WindowDuration` | | | `window_end - window_start`. |
| `Availability` | `min_samples=1` | | `True` if the window has at least `min_samples` rows. |
| `Constancy` | | | How often the most common value occurs. |
| `MostFrequent` | | | The most common value(s), as a tuple (all ties included). |
| `MostFrequentApprox` | | | Approximate most common value(s), as a tuple of text values. |
| `DistinctCount` | | | Number of different values. |
| `DistinctFraction` | | :material-check: | Different values ÷ rows. |
| `DistinctCountApprox` | | | Approximate number of different values (HyperLogLog). |
| `DistinctFractionApprox` | | :material-check: | Approximate different values ÷ rows. |
| `UniqueCount` | | | Number of values that occur exactly once. |
| `UniqueFraction` | | :material-check: | Values occurring once ÷ rows. |
| `UniqueOverDistinct` | | :material-check: | Values occurring once ÷ different values. |
| `MissingCount` | `disguised=[]` | | Number of missing values: `None`, `""`, and any value in `disguised` (e.g. `["N/A", -1]`). |
| `MissingFraction` | `disguised=[]` | :material-check: | Missing values ÷ rows. |
| `DistinctPlaceholderCount` | `placeholders` | | How many of the given placeholder values appear. |
| `DistinctPlaceholderFraction` | `placeholders` | :material-check: | That number ÷ rows. |
| `InSetCount` | `allowed_values`, `only_most_frequent=False` | | Number of values in `allowed_values`. |
| `InSetFraction` | `allowed_values`, `only_most_frequent=False` | :material-check: | Values in `allowed_values` ÷ rows. |
| `Monotonic` | `time_column`, `direction="asc"`, `strict=True` | | `True` if the values, ordered by `time_column`, only go up (`"asc"`) or down (`"desc"`). |
| `Correlation` | `other_column`, `method="pearson"` | :material-check: | Correlation with `other_column`: `"pearson"`, `"spearman"`, `"kendall"` or `"cramer"`. |

## Numeric columns

| Measure | Parameters | Prec. | Returns |
|---|---|---|---|
| `Mean` | | :material-check: | Average. |
| `Median` | | | Median. |
| `Sum` | | :material-check: | Sum. |
| `Variance` | | :material-check: | Population variance. |
| `StandardDeviation` | | :material-check: | Population standard deviation. |
| `Percentiles` | `percentiles=[25, 50, 75]` | :material-check: | `{percentile: value}`. For `[18.0, 21.5, 24.0]` the JSON output is `{"25": 19.75, "50": 21.5, "75": 22.75}`. |
| `AboveMeanCount` | | | Number of values above the mean. |
| `AboveMeanFraction` | | :material-check: | Values above the mean ÷ rows. |
| `InRangeCount` | `low`, `high`, `inclusive_low=True`, `inclusive_high=False`, `only_most_frequent=False` | | Number of values in the range. |
| `InRangeFraction` | same as `InRangeCount` | :material-check: | Values in the range ÷ rows. |
| `FrozenNumbers` | `epsilon=0.0`, `min_samples=1` | | `True` if the window has at least `min_samples` values and they vary by at most `epsilon`: the signal looks "frozen". |
| `BestLineFitSlope` | `time_column` | :material-check: | Slope of the best-fit line of the values over `time_column`: the trend. |
| `DeltasTuple` | `time_column` | | Differences between consecutive values, ordered by `time_column`. |
| `MinDelta`, `MaxDelta`, `MeanDelta`, `MedianDelta` | `time_column` | | Smallest / largest / mean / median of those differences. |
| `FirstDigitFreqs` | | :material-check: | `{digit: (count, share)}` of first digits, e.g. to compare with Benford's law. |
| `MinIntegerPartLength`, `MaxIntegerPartLength`, `MeanIntegerPartLength`, `MedianIntegerPartLength` | | | Number of digits before the decimal point. |
| `MinFractionalPartLength`, `MaxFractionalPartLength`, `MeanFractionalPartLength`, `MedianFractionalPartLength` | | | Number of digits after the decimal point. |

## Text columns

| Measure | Parameters | Prec. | Returns |
|---|---|---|---|
| `MinLength`, `MaxLength` | | | Shortest / longest value length. |
| `MeanLength`, `MedianLength` | | | Mean / median value length. |
| `RegexCount` | `regex` | | Number of values matching `regex` from their start. |
| `RegexFraction` | `regex` | :material-check: | Matching values ÷ rows. |

## Counting only the most frequent values

`InSetCount`, `InSetFraction`, `InRangeCount` and `InRangeFraction` take `only_most_frequent=True` to look only at the window's **most frequent value(s)**. The count then includes every occurrence of a most frequent value that conforms, and the fractions divide it by all rows in the window.

| Window | Measure | Result |
|---|---|---|
| `[1, 1, 1, 2]` | `InSetCount(..., allowed_values={1}, only_most_frequent=True)` | `3` |
| `[1, 1, 1, 2]` | `InSetFraction(..., allowed_values={1}, only_most_frequent=True)` | `0.75` |
| `[1, 1, 2, 2, 3]` | `InSetCount(..., allowed_values={1, 2}, only_most_frequent=True)` | `4` (tied values both count) |

## Your own measures

If no built-in measure fits, write your own with `@measure`. See [Custom Code](custom-code.md#measures).
