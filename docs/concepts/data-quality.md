# :ocean: Stream-first Data Quality

Data quality has been a cornerstone of data management for decades, but streaming data introduces constraints that traditional quality frameworks were not designed to handle.

## Traditional Data Quality Dimensions

Core dimensions used across data quality literature include:

- **:dart: Accuracy**: Data correctly represents real-world entities and relationships.
- **:last_quarter_moon: Completeness**: Required data is present without missing values.
- **:jigsaw: Consistency**: Data follows rules and constraints across records and fields.
- **:heavy_check_mark: Validity**: Data conforms to expected formats, types, and ranges.
- **:crystal_ball: Uniqueness**: Unwanted duplicates are absent.
- **:hourglass_flowing_sand: Timeliness**: Data is available when needed and reflects current state.

## The Implementation Gap

Research on open-source data quality tooling shows that conceptual dimensions and concrete implementations are often loosely coupled: different tools may implement the same dimension differently, and one check may support multiple dimensions.

!!! note annotate "Research insight"
    This mismatch creates a many-to-many relationship between theory and implementation, making quality definitions harder to compare across tools and projects. (1)

1. Learn more in our publicly available research work,
[Unfolding Data Quality Dimensions In Practice](https://dl.acm.org/doi/10.1145/3786328) :scroll:

## Streaming Data Adds New Requirements

When data is continuous and unbounded, quality definitions expand beyond static dataset checks.

### Completeness becomes temporal

In streams, completeness is not only about nulls/missing fields, but also about expected arrival rates and sequence continuity.

### Accuracy without a full gold standard

For unbounded streams, a complete reference dataset is rarely practical. Accuracy often relies on statistical expectations, cross-source consistency, and domain constraints.

### Timeliness is continuous

Timeliness becomes an always-on property that must be observed over time, including late arrivals and delivery delays.

## Stream-native quality dimensions

Beyond traditional dimensions, stream settings emphasize:

| Dimension | Stream interpretation |
| --- | --- |
| **Velocity** | Data arrives at expected rates |
| **Ordering** | Events appear in an acceptable sequence |
| **Latency** | Processing or arrival delays stay in bounds |
| **Continuity** | Unexpected temporal gaps are absent |

## Practical takeaway

High-quality stream monitoring combines traditional data quality principles with time-aware, rate-aware, and sequence-aware checks.
