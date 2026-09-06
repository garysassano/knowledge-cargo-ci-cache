# Compiler-cache experiment and promotion contract

Status: Proposed and untested integration work. This page specifies requirements; it does not describe a released RunsOn feature. Use [the research index](README.md) for scope, sequencing, and the [version refresh](baseline.md#release-refresh-2026-09-06).

## Observability And Cost Model

### Job Metrics

Record through the [cache measurement schema](../../reference/cache-measurement-schema.md):

- Job and workload wall time.
- Setup, readiness, wrapper, drain, and shutdown time.
- Compile requests, cacheable requests, hits, misses, and non-cacheable calls by reason and output class.
- Direct-compiler bypass reason.
- Readiness state.
- Attempted, accepted, committed, rejected-policy, skipped-policy, failed, retried, deferred, and unfinished writes.
- Downloaded and uploaded bytes.
- Compression and decompression work.
- Maximum RSS and spill bytes.
- Configured deadline, observed duration, result, and exceedance count for setup, readiness, connect, first-byte, idle, total lookup, write admission, drain, shutdown, and sticky snapshot publication.
- Invocation identifier, compiler-launch count, fallback boundary, reason, latency, and outcome for every degraded request.

Common `rlib`, `staticlib`, and metadata compilation can be cacheable, while binaries, procedural macros, `cdylib`, `dylib`, build-script work, and final linking remain local. Preserve that taxonomy in every experiment because a changing output mix can change wall time while aggregate hit rate remains constant.

### Gateway Metrics

| Area       | Metrics                                                                                                                                                                         |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Requests   | GET, PUT, not-found, rejected, cancelled, in-flight                                                                                                                             |
| Coalescing | leaders, followers, origin requests avoided, follower wait                                                                                                                      |
| L0         | hits, misses, bytes, evictions, corruptions, GC duration                                                                                                                        |
| Index      | generation, shard age, lookups, definite absences, false-positive origin misses, validation failures                                                                            |
| Origin     | result class, p50/p90/p95/p99/maximum, deadline exceedances, retries, throttle delay, circuit state                                                                             |
| Queue      | admitted, rejected, depth, bytes, oldest age, spool usage                                                                                                                       |
| Writes     | conditional creates, existing-identical, conflicts, committed, failed, unfinished                                                                                               |
| Lifecycle  | session age, credential refresh, quiesce/drain/shutdown/snapshot duration, deadline exceedances, close result                                                                   |
| Resources  | configured limits, observed maximum, rejection count, time at limit, CPU, RSS, open connections, file descriptors, in-flight requests, queue bytes/age, free bytes, free inodes |

### Backend And Storage Metrics

- S3 GET, PUT, multipart, list, and error counts by compiler-cache namespace class.
- Request latency when per-job attribution is possible.
- KMS requests and throttles.
- Object count, total bytes, average and percentile object size.
- Lifecycle expirations.
- Incomplete multipart uploads.
- Canonical and overlay bytes.
- Readiness/index bytes.
- Redis or Valkey memory, evictions, hit rate, failovers, and connection saturation when tested.

### Cost Per Saved Minute

For a paired period:

```text
net cache cost =
    cache storage
  + cache requests
  + cache service or gateway compute
  + cache data transfer
  + additional runner time in cold and failure states
  - runner cost avoided in faster states

cost per saved minute =
    positive incremental cache cost / positive runner minutes saved
```

Report negative savings as a regression rather than forcing a cost-per-saved-minute value.

The budget must include:

- Warm-state frequency and reuse distance.
- Population frequency.
- Read-only guaranteed-empty bypass frequency.
- Runner price by profile and purchase model.
- S3 Standard or Express storage and requests.
- KMS requests.
- Redis, Valkey, gateway, index, and telemetry infrastructure.
- Operator and incident burden when material.

Every cost report declares currency, pricing date, runner purchase model, storage and service region, retention and amortization window, workload volume, and which operational costs are included.

### Alerts

Alert on:

- Canonical write conflicts.
- Cross-prefix authorization denials.
- Corruption or checksum mismatch.
- Unfinished canonical writes.
- Drain timeout.
- Readiness stuck in populating.
- Sustained origin circuit open.
- Retry or throttle surge.
- Queue or spool saturation.
- Sticky disk or inode pressure.
- Unexpected namespace growth.
- Cache-enabled p95 regression against direct `rustc`.

## Failure And Fallback Matrix

| Failure                                                             | Detection                                                           | Cache behavior                                                          | Compilation behavior                          | Recovery                                                                                       |
| ------------------------------------------------------------------- | ------------------------------------------------------------------- | ----------------------------------------------------------------------- | --------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| Binary absent or wrong checksum                                     | Setup verification                                                  | Disabled                                                                | Direct `rustc` unless strict                  | Install approved binary                                                                        |
| Missing or conflicting identity                                     | Setup validation                                                    | Disabled                                                                | Direct `rustc`                                | Fix platform identity                                                                          |
| Writer OIDC replay or platform-attestation mismatch                 | Broker validation                                                   | No session                                                              | Direct `rustc` or strict population failure   | Reject token and investigate admission path                                                    |
| Stale daemon configuration                                          | Fingerprint mismatch                                                | Stop or reject daemon                                                   | Direct `rustc` if restart fails               | Clean runtime state and restart                                                                |
| Readiness absent                                                    | Known manifest lookup                                               | Bypass shared backend                                                   | Direct `rustc` or controlled population       | Publish trusted ready generation                                                               |
| S3 or proxy 401/403                                                 | Typed auth error                                                    | Open circuit; no relabel as miss                                        | Direct compile on safe boundary               | Refresh or correct policy                                                                      |
| KMS denial                                                          | Typed backend error                                                 | Disable affected backend                                                | Direct compile                                | Correct KMS policy                                                                             |
| 404                                                                 | Confirmed not-found                                                 | Normal miss                                                             | Compile and write only if authorized          | None                                                                                           |
| 412 Precondition Failed or 409 Conflict during conditional creation | Fetch authoritative stored metadata and reconcile by operation type | Existing-identical may succeed only after verification; conflict alerts | Continue compilation result                   | Restart upload when required, quarantine conflicting content, and investigate                  |
| 429 or service throttle                                             | Retry budget and metrics                                            | Bounded retry, then circuit                                             | Direct compile                                | Reduce concurrency or capacity pressure                                                        |
| DNS/connect/TLS failure                                             | Staged deadline                                                     | Fast circuit after threshold                                            | Direct compile                                | Restore path                                                                                   |
| Lookup total timeout                                                | Configured total deadline                                           | Typed timeout, not silent miss                                          | Direct compile                                | Tune or repair backend                                                                         |
| Corrupt object                                                      | Checksum or decode validation                                       | Quarantine/bypass                                                       | Direct compile                                | Maintenance repair or rotate                                                                   |
| Oversized object                                                    | Metadata and stream limit                                           | Reject/bypass                                                           | Direct compile                                | Investigate producer                                                                           |
| Local L0 disk full                                                  | Admission and filesystem metrics                                    | Evict, local bypass, or reject write                                    | Continue compile                              | GC, reset, resize                                                                              |
| Queue or spool full                                                 | Bounded admission                                                   | Reject new cache writes                                                 | Continue ordinary job; fail strict population | Drain or restore origin                                                                        |
| Gateway crash before workload                                       | Health probe                                                        | Disabled                                                                | Direct `rustc`                                | Restart gateway                                                                                |
| Gateway crash mid-compilation                                       | Broken wrapper request                                              | Mark integration failed                                                 | Do not auto-retry ambiguous compile           | Next safe invocation/direct rerun by workflow policy                                           |
| Daemon crash                                                        | Control probe or wrapper error                                      | Disabled                                                                | Direct path only after safe reconfiguration   | Restart before new invocation                                                                  |
| Token expiry                                                        | Session timer or auth response                                      | Stop new origin operations                                              | Direct compile                                | Refresh valid session                                                                          |
| Index stale positive                                                | Origin returns 404                                                  | Normal miss and metric                                                  | Compile                                       | Rebuild index                                                                                  |
| Index suspected false negative                                      | Audit sampling or generation bug                                    | Disable index                                                           | Origin/direct path                            | Rebuild and fix publication                                                                    |
| Sticky disk unavailable, unready, or restore timeout                | RunsOn setup result                                                 | Sticky tier unavailable before wrapper setup                            | Job may fail before wrapper fallback          | Set `sticky_wait_timeout: 15m`, repair or cold-start lineage, and test platform-level fallback |
| Cancellation, timeout, workload failure, or missing post            | External termination or expired lease                               | Writes may remain unfinished; no readiness or sticky publication        | Job preserves its actual result               | Replay only remotely admitted or broker-signed fenced records; otherwise repopulate            |
| Drain timeout                                                       | Drain status                                                        | Mark unfinished                                                         | Preserve workload result; population fails    | Replay or repopulate                                                                           |

## Experiment Matrix

### Common Controls

Keep fixed within each pair:

- Source and sanitized workload version.
- Rust toolchain and full `rustc -Vv` identity.
- `sccache` and gateway binary digests.
- Runner image, instance profile, CPU, memory, and storage.
- Workload command, features, profile, targets, environment, and concurrency.
- Cacheable and non-cacheable request mix classified by output class and reason.
- Compression format and level.
- Namespace schema and trust mode.
- Cargo input-cache choice.
- Object-store region, Availability Zone relationship, encryption, and lifecycle.

Randomize strategy order where state construction permits it. Use a new isolated namespace or immutable generation rather than deleting shared production data for cold trials.

### Performance States

| State                                           | Question                                                                                        |
| ----------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| Direct `rustc`                                  | What is the baseline job and workload distribution?                                             |
| Gateway pass-through with cache disabled        | What overhead does the integration add with no cache value?                                     |
| Wrapper/local confirmed miss without remote I/O | What do hashing, daemon, wrapper, and compiler interaction cost without an origin request?      |
| Gateway known-negative                          | What does validated local membership or negative-cache handling cost?                           |
| Origin-confirmed 404                            | What is the incremental remote miss path?                                                       |
| Empty read-only full workload                   | What is the combined bounded miss-path penalty without incorrectly attributing it to one stage? |
| Cold canonical population                       | What does complete durable population cost?                                                     |
| Warm exact                                      | What is the best reusable state?                                                                |
| Changed source                                  | How much unaffected compiler work remains reusable?                                             |
| Lockfile change                                 | How does dependency invalidation affect value?                                                  |
| Feature/profile/target change                   | Are namespaces and keys correct and useful?                                                     |
| Toolchain change                                | Does policy prevent unsafe or useless overlap?                                                  |
| Concurrent identical workload                   | Does coalescing reduce origin fan-out?                                                          |
| Mixed production canary                         | What are realistic medians, tails, warm probability, and cost?                                  |

### Design Comparisons

- Current default-server direct S3.
- Hardened direct S3 with IAM/readiness but no gateway.
- Gateway pass-through.
- Gateway with negative cache.
- Gateway with selected membership index.
- Gateway with coalescing.
- Gateway read-only with ephemeral L0.
- Gateway canonical writer with synchronous remote commit.
- Gateway with durable spool only after the synchronous writer is correct.
- Sticky gateway L0.
- Patched native GHA with Magic Cache isolation disabled and enabled as separate cold-start states.
- Read-only S3 Express after backend support; writer mode only after conditional creation and publication fencing are verified.
- Redis or Valkey L1.
- Memcached L1 if object sizes permit.
- zstd levels 1, 3, 6, and 9.

### Failure And Chaos Tests

Inject:

- 401, 403, 404, 409, 412, 429, and 5xx responses.
- Connect, first-byte, idle, and total timeouts.
- DNS failure.
- KMS denial and throttling.
- STS or GitHub token expiry and clock skew.
- Corrupt checksum, truncated body, invalid metadata, and oversized object.
- Duplicate concurrent writes with identical and conflicting bytes.
- Gateway, daemon, and origin-proxy crash.
- Disk full, inode exhaustion, queue full, and spool corruption.
- Cancellation before post, during drain, and during snapshot publication.
- Sticky restore timeout, missing readiness marker, 20%/10% warning thresholds, below-5% reset, reset skipped while in use, and inactive-lineage expiry.
- Index corruption, stale generation, and missing shards.
- Pointer rollback, predecessor mismatch, stale fencing epoch, expired writer lease, and late publisher completion.
- Cross-repository, cross-scope, and unauthorized write/delete attempts.

### Statistical Plan

- Use at least 10 randomized paired runs per state for exploration.
- Use approximately 30 paired runs per state for central paired-delta inference, not for tail claims.
- Precompute tail sample sizes and stopping rules from the declared p95 or p99 precision and event-rate SLO. Roughly 100 canary jobs are useful for exploration but provide only about one expected p99 observation and cannot by themselves support a precise p99 promotion claim.
- Report paired medians, p90, p95, p99, maximum, and bootstrap confidence intervals where the sample supports them. Retain every timeout, cancellation, fallback, and failed observation rather than censoring it.
- Pre-register workload strata, cache-state weights, source-change distribution, baseline window, absolute deadlines, relative budgets, sample size, and stopping rule before evaluating a promotion candidate.
- Do not sum overlapping compiler-cache request durations and call the result job wall time.
- Follow [Measuring Cache Performance](../../operations/measuring-cache-performance.md) and store sanitized records using the [Cache Measurement JSONL Schema](../../reference/cache-measurement-schema.md).

## Promotion Gates

### Evaluation Order

Correctness, authorization, durability, fallback, publication, and hard-deadline gates are deterministic and zero-tolerance. Any failure blocks performance evaluation; a percentile cannot hide a catastrophic injected failure that occurs below its tail cutoff.

Numeric speed thresholds below are provisional project SLOs rather than conclusions measured by the current one-trial-heavy evidence. Before a canary, pre-register the absolute and relative budgets, workload strata and weights, direct-compiler baseline window, pricing assumptions, sample sizes, and stopping rules.

### Correctness And Security Gates

- Zero correctness divergence from paired direct-`rustc` outputs and tests.
- Trust-matrix, cross-repository, cross-scope, unauthorized listing/read/write/delete, multipart, tagging, ACL, KMS, and role-assumption tests all deny the wrong principal.
- Writer admission rejects wrong audience, replayed `jti`, nonce mismatch, mutable or unapproved workflow identity, stale run attempt, cancelled/completed run, local-field conflict, and RunsOn attestation mismatch.
- A protected writer's complete executable dependency graph is pinned or otherwise admitted by policy; no PR-controlled code or artifact executes with canonical writer authority.
- Checksums are never treated as semantic authenticity, and generation provenance, quarantine, and emergency rotation work as designed.
- Integration-generated logs and exported measurements pass adversarial credential, signed-URL, object-key, repository/ref, debug, retry, and malformed-input redaction tests.
- Canonical PR read remains disabled for sensitive repositories unless an explicit confidentiality-risk exception is recorded.

### Durability, Lifecycle, And Fallback Gates

- Every canonical write acknowledged as successful is remotely committed, readable by a fresh authorized reader, length- and checksum-valid, and bound to the expected compiler key and namespace generation. Zero successful acknowledgements are rejected, failed, deferred, or unfinished.
- Deferred writes, if the future mode exists, are remotely admitted under broker-signed fenced authority, remain excluded from readiness until committed, and have audited durable replay ownership.
- Drain seals new producers, waits for active producers, disables backfills, captures a watermark, drains through it, and atomically reports terminal counts by a predeclared absolute deadline.
- `ready` requires the declared protected workload and identities, `cacheable_requests > 0`, `committed_writes > 0`, and zero rejected, failed, deferred, and unfinished canonical writes.
- Failed, cancelled, timed-out, fenced, lease-expired, or missing-post jobs never publish readiness, an index pointer, or a sticky lineage.
- Generation and sticky-lineage pointer tests reject rollback, stale epoch, unexpected predecessor, expired lease, and duplicate activation while preserving the selected rollback-safe generation.
- No silent GHA finalization, background-write, drain, shutdown, or snapshot-publication loss is observed.
- Setup-time fallback succeeds for daemon, gateway, identity, IAM, KMS, network, backend, disk, and token failures. Subsequent invocations fall back after a proven safe boundary; an already-running invocation launches exactly one compiler and is never automatically retried.
- Every injected failure reaches its declared terminal state or safe fallback within predeclared hard setup, readiness, connect, first-byte, idle, total lookup, write-admission, drain, shutdown, and snapshot deadlines.

### Performance And Cost Gates

- The bootstrap 95% confidence interval upper bound for the pre-registered weighted job-time delta is below zero.
- The point estimate is at least 5% faster for full promotion under the provisional project SLO.
- Mixed-workload p95 is no more than 5% above direct `rustc`, and p99 is no more than 10% above it, under provisional project SLOs and only when sample precision supports those claims.
- Maximum observed duration and every timeout remain within the corresponding predeclared absolute deadline; otherwise expand the sample or reject promotion rather than hiding the event in a percentile.
- Failure, fallback, timeout, cancellation, cold, population, warm, and source-change jobs all remain in the weighted performance result.
- Cost per saved minute is below a declared project threshold using a dated, reviewable cost model.

### Gateway-Specific Gates

- Cache-disabled pass-through overhead is no more than the provisional 1% project SLO against direct-`rustc` job time.
- Duplicate concurrent origin GET fan-out is reduced by at least the provisional 90% project SLO.
- Memory, connection, descriptor, in-flight request, queue, spool, disk, and inode limits remain bounded under overload, with configured limit, observed maximum, rejection count, and time at limit recorded.
- No stale single-flight entry blocks later requests.
- Protected population finishes with zero rejected, failed, deferred, and unfinished writes after drain; elapsed drain time independently meets its absolute deadline.
- Crash recovery never overwrites conflicting canonical content. Duplicate at-least-once replay is expected, is resolved idempotently through conditional creation and authoritative object verification, and never advances readiness twice.
- Index failure falls back without correctness loss.

### Sticky-Specific Gates

- Exactly one local process owns each restored volume, and at most one remotely leased and fenced publisher can advance a lineage.
- Files are synced, the clean marker and parent are durable, and the filesystem is frozen or unmounted before snapshot creation.
- Cancellation, timeout, lease loss, failed workload, missing post, and every interruption between clean marking, snapshot creation, and pointer publication preserve the previous valid lineage.
- Snapshot restore and commit overhead do not erase L0 savings.
- Free-byte and free-inode headroom remain above project thresholds.
- RunsOn v3.2+, explicit `sticky_wait_timeout: 15m`, ten-day inactive expiry, warning thresholds, automatic reset, and reset-skipped behavior are all covered by cold-path and failure tests.
- GC and platform reset are bounded and recoverable.
- Trust-domain and schema mismatch always reject or quarantine the directory.

### Alternative-Backend Gates

- Native GHA propagates finalization failure, passes fresh-job visibility, and tests isolation disabled and enabled as separate namespace populations.
- S3 Express read-only passes same-AZ, Zonal/Regional endpoint, session, lifecycle, fallback, and cost tests. Canonical writer promotion additionally requires the selected conditional-create and publication mechanism to pass duplicate, stale-writer, and failure tests; an external key coordinator is one fallback if client support is insufficient.
- Redis or Valkey passes eviction, failover, persistence, isolation, and cost tests.
- Memcached is never the sole durability tier.
