# Cache Measurement JSONL Schema

This schema stores sanitized cache experiments as append-friendly JSON Lines while preserving enough timing structure to distinguish critical-path wall time from overlapping work. This page is the contract; the committed data files linked under [Examples](#examples) are the authoritative examples of field usage.

## File Contract

- UTF-8 JSONL with one complete JSON object per line.
- Every record has `schema_version` (`cargo-ci-cache/v1`), `record_type`, `run_id`, `strategy`, `scenario_id`, and `privacy` (`sanitized` for anything committed here).
- `run_id` and `scenario_id` are opaque sanitized identifiers, not repository, workflow, pull-request, branch, or commit identifiers. `scenario_id` is shared by directly comparable trials. `strategy` is a stable generic name such as `no-cache`, `input-only-archive`, `whole-target-archive`, `s3-sccache`, `sticky-inputs`, or `sticky-target`.
- Durations use integer milliseconds. Sizes use integer bytes. Resource percentages use numbers from 0 through 100.
- Unknown fields are omitted rather than set to a guessed value. Producers may add namespaced fields; consumers must ignore fields they do not understand.
- One file may contain multiple runs and record types. Repeat the common identity fields on each line so command-line filters do not require a join merely to select a run.

For detailed field types and the phase/metric vocabulary, use [Cache Measurement Fields](cache-measurement-fields.md).

## Record Types

| `record_type` | Cardinality | Purpose |
| --- | --- | --- |
| `run` | Exactly one per `run_id` | Trial identity, sanitized runner/workload profile, top-level result, and authoritative `job_total_ms` wall time |
| `phase` | Zero or more | A measured or derived time interval or aggregate duration |
| `metric` | Zero or more | Size, file count, request count, hit/miss statistic, cost, or other scalar with `name`, `value`, and `unit` |
| `resource_sample` | Zero or more | Timestamped CPU, memory, disk, network, and process-concurrency values |
| `event` | Zero or more | Cache race, fallback, reset, timeout, failure, cancellation, or other discrete behavior |

Take field shapes from the committed data files rather than inventing new ones. Reuse the phase and metric names already present in those files, prefer specific names over combined ones (`cache_lookup` and `cache_download` over `cache_lookup_download` when the source data exposes the split), and document any genuinely new name in the evidence page that introduces it.

## Phase Accounting

Every `phase` record carries `duration_ms` and an `accounting` value:

- `exclusive` — only when the interval is known not to overlap sibling critical-path phases.
- `inclusive` — a total containing child phases (linked through `parent_phase_id`).
- `may-overlap` — compiler requests, parallel rustc processes, background uploads, and resource-related activity.
- `aggregate-only` — a duration whose start/end offsets are unavailable.

## Overlap And Wall-Time Rules

1. `job_total_ms` on the `run` record is authoritative for runner wall time.
2. A parent `inclusive` phase may contain child phases and must not be added to them.
3. `may-overlap` phases can overlap each other and critical-path phases; report their sum only as work, never as elapsed time.
4. To calculate critical-path coverage, take the union of measured `exclusive` intervals inside the job.
5. If offsets are unavailable, report aggregate durations and leave coverage unknown.
6. Record `unattributed_job_overhead` only as an explicitly derived residual, with the inputs and rounding limitation documented.

Resource samples support diagnosis and interval correlation. They are not phases and must not be summed into wall time.

## Sanitization

Allowed fields are generic strategy names, opaque identifiers, public hardware characteristics, aggregate timings, sizes, counts, utilization, and failure classes.

Do not commit:

- Organization, repository, workflow, pull-request, branch, user, or customer identifiers.
- Private URLs, internal runner labels, account IDs, regions tied to private topology, S3 buckets, prefixes, or object keys.
- Package names, source paths, command lines, raw commit hashes, cache keys, or dependency names from a private repository.
- Environment dumps, credentials, tokens, presigned URLs, request headers, or unsanitized logs.

Keep raw logs in the private source system and export only the numeric or categorical observations needed to support the evidence.

## Examples

- [Synthetic mixed-record example](../../examples/measurements/cache-measurements.example.jsonl), the only committed example containing a `resource_sample` record
- [Sanitized degraded archive sample](../evidence/data/target-archive-degraded-sample.jsonl)
- [Sanitized full-workload compiler-cache sample](../evidence/data/compiler-cache-full-workload-sample.jsonl)
- [Sanitized Mr. Boxington and sccache cross-run sample](../evidence/data/mr-boxington-sccache-cross-run.jsonl)
- [Measurement procedure and report tables](../operations/measuring-cache-performance.md)
