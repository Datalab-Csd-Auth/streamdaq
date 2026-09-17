# StreamDAQ Integration Tests

End-to-end tests that validate the API works as expected for all current streamdaq checks and measures.
These tests are currently not part of the default `pytest`/`nox` run, but they can be executed
on demand with `nox -s integration-tests`.

## How the output is verified

The test compares each produced file to its expected_output. Pathway appends a non-deterministic
wall-clock `time` field to every output row, which is stripped before comparison. The
remaining content is deterministic, so the assertion is strict: **same number of lines, and
each output line present exactly (byte-for-byte) in the expected_output**. The comparison is
order-insensitive (Pathway's read order is not fixed) but exact per line — a multiset match.

### Regenerating the expected_output files

After an intentional change to the stream, payload, or a measure's output, regenerate:

```bash
STREAMDAQ_UPDATE_expected_output=1 nox -s integration_tests
```

Review the resulting `expected_output/*.jsonl` diff before committing.

## Adding coverage for a new measure or check

Add **one entry** to `registry.py`:

- a new measure → `MEASURE_SPECS["MyMeasure"] = MeasureSpec({"column": INT, ...}, ">= N")`
  with its full constructor params and a `must_be` that both passes and fails over the
  stream (use `derive_thresholds.py` to find the per-window values), **or** add its name to
  `EXCLUDED_MEASURES` if it cannot be covered yet;
- a new instant check → `INSTANT_CHECK_SPECS["MyCheck"] = InstantCheckSpec("MyCheck", {...})`.

Then regenerate the expected_outputs.

## Debugging a failure

When a test fails, the API's working directory — the server log (`api.log`) and every task
output file — is copied to `integration-tests/.artifacts/<test-name>/`, and the path is
printed at the end of the run. Look there first: `api.log` has the server-side traceback and
any task-worker error, and the `*.jsonl` files show exactly what each task produced.
Artifacts are kept until the next failure of the same test (a passing run does not delete a
prior failure's evidence) and are git-ignored.
