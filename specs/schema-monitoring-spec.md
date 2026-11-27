# Schema monitoring, sniffing and evolution

**Suggested issue title:** `feat(schema): schema checks with alerts, sniffing and automatic evolution`

## Problem

Today the typed Pathway schema is passed straight to the connector. A record that doesn't match it fails inside Pathway's parser and is dropped with a log line, so Stream DaQ never sees it: there is no alert, no count, and no way to react when a producer changes its payload.

Schema conformance is a data quality matter, so it should be a first-class part of a task, next to `input`, `output` and the checks.

## Goals

1. Emit a JSON alert for every record that does not conform to the expected schema.
2. Support a **declared** schema, a **sniffed** one (inferred from the first records), or a **hybrid** of the two.
3. Let the schema **evolve** automatically under a pluggable policy, using the existing task hot-swap.
4. Keep today's behavior unchanged when schema checks are off.

## Configuration

Schema checks get their own section, `schema_checks_config`, shaped like the other check sections.

```json
"schema_checks_config": {
  "mode": "full",
  "fields": {
    "timestamp": "int",
    "temperature": {"type": "float", "required": true, "nullable": false}
  },
  "sniff": false,
  "policy": "additive",
  "min_evidence": 3,
  "include_raw": false
}
```

The same model is used from Python:

```python
from streamdaq.schema.config import SchemaChecksConfig

Task(..., schema_checks=SchemaChecksConfig(mode="full", fields={...}, policy="additive"))
```

| Setting | Default | Meaning |
|---|---|---|
| `mode` | `"full"` | `"full"`: every issue. `"fast"`: missing fields and wrong types only, at lower cost. `"off"`: `fields` only type the input, without validation. |
| `fields` | `{}` | The declared schema. Shorthand (`"int"`) or full form (`{"type", "required", "nullable"}`). Types: `int`, `float`, `str`, `bool`, `json`. |
| `sniff` | `false` | Infer the schema, or its undeclared part, from the first valid record. `true` or `{"timeout_seconds": 20}`. |
| `policy` | `"strict"` | The schema policy that decides which proposed changes are applied (see Evolution). |
| `min_evidence` | `3` | How many times a change must be seen before the policy is asked. |
| `include_raw` | `false` | Add the nonconforming record itself to each alert. |

- `fields` replaces the input's `schema` param. That param keeps working for older payloads; if both are given, `fields` wins.
- A task with only schema checks is valid. The API error becomes "At least one instant, window or schema check is required."
- An unknown policy name is rejected when the task is created.

| `fields` | `sniff` | Contract |
|---|---|---|
| given | off | declared |
| none | on | sniffed |
| given | on | hybrid: declared fields win, sniffing adds the rest |
| none | off | error at task build |

## Schema contract

The schema a task validates against is a versioned **contract** (`SchemaContract`). It's built from the config, but it's runtime state, kept apart from the config.

- Each field has `type`, `required`, `nullable` and `origin` (`declared` or `sniffed`).
- Columns used by checks, plus `windowby_column` and `groupby_column`, are always required. A used column that isn't in the contract fails the task at start, with a clear error.
- The Session resolves the contract before the worker starts:
  - if one is stored in LMDB (`schema_contracts`), it is used, which covers restarts and hot-swaps;
  - otherwise a declared, sniffed or hybrid v1 is built and stored.
- The contract travels to the worker in the task payload, so a worker never sniffs.

## Validation

**`full` mode.** The source is read untyped: raw bytes for Kafka and MQTT, raw lines for JSON Lines. One Python function per record decodes it with `orjson` (`orjson` is Rust-based so it is faster) and compares fields **by name**:

| Issue | Meaning |
|---|---|
| `missing` | A required field is absent. |
| `unexpected` | A field not in the contract. |
| `null_not_allowed` | `null` in a non-nullable field. |
| `type_mismatch` | Wrong type, with `expected` and `got`. `bool` is never `int`; an `int` is a valid `float`. |
| `malformed` | The message isn't valid JSON. |
| `not_an_object` | The message is JSON, but not an object. |
| `evb_structure` | Compact (EVB) data only: the message structure is invalid. |
| `length_mismatch` | Compact (EVB) data only: a values row has the wrong number of values. |

**`fast` mode.** Every contract field is read as an optional `pw.Json` and checked with native Pathway expressions (`is_none`, `fill_error(as_float())`). Python runs only on bad rows, to build their alert. Limits, verified on Pathway:
- extra fields are dropped by the reader, so `unexpected` can't be detected;
- malformed lines are dropped by Pathway with a log line;
- a JSON `null` and a missing field both read as `None`, so both are reported as `missing`.

**Both modes.**
- Valid rows are projected to typed columns by name: required fields as `T`, optional ones as `T | None`. They then enter the existing check pipeline unchanged.
- **Records with violations are excluded from the checks** and only become alerts.

### Supported sources

| Source | `full` | `fast` |
|---|---|---|
| JSON Lines | ✅ | ✅ |
| Kafka, MQTT | ✅ | ✅ |
| Kafka, MQTT with compact (EVB) data | ✅ | runs as `full` |
| Parquet, Python connector, custom `@source` | ❌ Their data is typed before Stream DaQ sees it (future fix) | ❌ |

## Alerts and outputs

Each violating record produces one alert:

```json
{"task": "sensors", "task_version": 2, "contract_version": 3, "monitoring_mode": "full",
 "event_time": 1645334535000,
 "issues": [{"field": "humidity", "kind": "type_mismatch", "expected": "float", "got": "str"}]}
```

`raw` is added with `include_raw`. The field is `event_time` rather than `time`, because Pathway writers add their own `time` column.

| Output | Instant results | Window results | Schema alerts |
|---|---|---|---|
| plain writer (`filename: "q.jsonl"`) | `q.jsonl` | `q_window.jsonl` | `q_alerts.jsonl` |
| `TaskOutput.meta_stream` | ✅ | `_window` suffix | `_alerts` suffix |
| `TaskOutput.valid_only` | rows where every check passed | `_window` suffix | — |
| `TaskOutput.errors_only` | rows where a check failed | `_window` suffix | `_alerts` suffix |

- Window rows are judged only by window checks that have a `must_be`.
- When schema checks are on, `_streamdaq_metadata` gains `contract_version`.

## Sniffing

- A short-lived Pathway process reads the source and infers the contract from the **first valid record**. Invalid rows (malformed JSON, or EVB that fails its structure check) are skipped. Without a valid record within `timeout_seconds`, the start fails with `TimeoutError`.
- Each field of that record becomes required, typed by its value.
  - `bool` is never `int`;
  - nested values become `json`;
  - a `null` value gives a nullable `json` field.
- So a field that's an int in the first record stays `int`. Later floats raise `type_mismatch` alerts and `widen_field` proposals, which a `widening` policy can accept.
- In hybrid mode, a sniffed type that disagrees with a declared field is logged as a warning, and the declared type is kept.
- The sniffed message is not processed by the task.

## Evolution (`full` mode only)

1. **Proposals.** Compatible deviations become proposals, next to their alerts:
   - an unexpected field becomes `add_field` (optional, with the type seen);
   - a float in an `int` field becomes `widen_field` to `float`.

   Every other deviation is an alert only.
2. **Collection.** The worker sends proposals to the Session over a `multiprocessing.Queue` (a forked worker can't open the Session's LMDB). The Session stores them in LMDB (`schema_proposals`), keyed by fingerprint (e.g. `add_field:humidity:int`), and counts repeats.
3. **Decision.** Under `streamdaq serve`, every 5 s, each pending proposal against the current contract version that has been seen `min_evidence` times is passed to `policy(proposal, contract) -> bool`.
   - `True`: the change is applied.
   - `False`: the proposal stays pending and is asked again later, with a higher count.
4. **Apply.** The accepted changes are merged by the widening rules into contract v+1, the proposals are marked applied, and the task is hot-swapped. The new field arrives as a typed column, and its alerts stop.

Built-in policies: `strict` (never, the default), `additive` (new fields), `widening` (new fields and int to float). Custom policies use a decorator, like `@assessment`:

```python
from streamdaq.custom import schema_policy

@schema_policy("numeric_fields_only")
def numeric_fields_only(proposal, contract):
    return proposal.change["kind"] == "add_field" and proposal.change["type"] in ("int", "float")
```

They're loaded with `streamdaq serve --files`.

API additions:
- `GET /config/options` lists `schema_policies`.
- `DELETE /tasks/{id}` also removes the task's contract and proposals.


## Out of scope / follow-ups

- **Faster `full` mode:** batched UDF calls, then optionally a Rust validator (PyO3/maturin, `streamdaq[fast]`) that parses and validates batches without the GIL. Measure first.
- **Schema checks for custom sources:** a `data_format="raw"` option for `@source`, so they return untyped messages that Stream DaQ validates.
