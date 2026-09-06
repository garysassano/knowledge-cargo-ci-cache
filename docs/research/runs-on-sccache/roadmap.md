# RunsOn `sccache` Performance Roadmap

## Scope

Status: Proposed experiments, not completed work or current service features. This page orders performance work; the [trust and publication contract](trust-and-publication.md) and [validation gates](validation.md) remain prerequisites wherever shared storage or publication is involved.

The [versioned baseline](baseline.md#quantitative-constraints-from-existing-evidence) derives a simple warm-probability model from the archived job timings. The priorities are to increase warm reuse, avoid known-empty lookups, and account for population writes before the runner disappears. These are hypotheses to measure, not promised gains.

## Priority Definitions

| Priority | Meaning                                                                                       |
| -------- | --------------------------------------------------------------------------------------------- |
| P0       | Do first; low or moderate effort with direct measured relevance                               |
| P1       | High-value improvement that needs additional implementation or upstream cooperation           |
| P2       | Promising architectural experiment after P0 and P1 measurements                               |
| P3       | Keep as a later alternative; currently speculative, blocked, or unlikely to beat simpler work |

## Ordered Task Sequence

| Order | Priority | Owner area                             | Task                                                                                                                                                                                 | Expected benefit                                                                                                                               | Completion test                                                                                                                    |
| ----: | -------- | -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
|     1 | P0       | Workflow and measurement repository    | Establish repeatable direct-`rustc`, cold population, warm exact, changed-source, and empty read-only controls using the same runner profile and source state.                       | Prevents optimizing from hit rate or one favorable run.                                                                                        | At least 10 randomized paired exploratory runs per important state with full job and workload timings.                             |
|     2 | P0       | Workflow and `runs-on/action`          | Standardize on direct S3 in normal `sccache` server mode with `CARGO_INCREMENTAL=0`. Do not enable client-side or multilevel mode by default.                                        | Uses the only mode that produced the strong measured warm result.                                                                              | Configuration is printed without secrets; warm and cold controls reproduce the expected direction.                                 |
|     3 | P0       | Workflow                               | Test removing the separate input-only `Swatinem/rust-cache` step from the `sccache` workflow.                                                                                        | One ablation was about 28 seconds faster at job level and retained 6,929 compiler-cache hits with zero misses.                                 | Paired runs show whether registry/Git download savings exceed the archive action’s setup and restore overhead.                     |
|     4 | P0       | `runs-on/runs-on` configuration        | Increase S3 compiler-cache retention from the default 10 days to candidate values such as 30 and 60 days.                                                                            | Raises warm-cache probability because S3 object reads do not refresh lifecycle age.                                                            | Measure reuse-distance distribution, warm-job percentage, stored bytes, request cost, and job-time delta before selecting a value. |
|     5 | P0       | Workflow                               | Add a dedicated population workflow after important lockfile, toolchain, feature-set, or build-profile changes.                                                                      | Reduces the number of ordinary jobs that pay cold writes and improves the chance that readers begin warm.                                      | A fresh job after population sees the expected objects and improves against the direct-compiler control.                           |
|     6 | P0       | Workflow wrapper or `runs-on/action`   | Add a small readiness marker and bypass `sccache` entirely when no completed population exists for the selected cache namespace.                                                     | Directly attacks the measured empty-cache regression of about 16%.                                                                             | Known-empty jobs run close to the direct-`rustc` baseline without thousands of remote misses.                                      |
|     7 | P0       | Runner image and `runs-on/runs-on`     | Preinstall an exact `sccache` binary in the runner image instead of downloading it in every job.                                                                                     | Removes repeated setup and network work.                                                                                                       | Compare setup and complete job time with the current installer action.                                                             |
|     8 | P0       | Workflow                               | Benchmark Cargo compiler concurrency together with remote-request pressure. Test a small matrix of `--jobs` values instead of assuming maximum CPU concurrency is optimal.           | Can reduce S3 contention, memory pressure, decompression contention, and tail latency.                                                         | Select the setting with the best complete job time across cold, warm, and changed-source runs.                                     |
|     9 | P0       | Workflow and `sccache` configuration   | Benchmark supported zstd compression levels, starting with levels 1 and 3.                                                                                                           | Level 1 may reduce population CPU; level 3 may reduce transfer bytes. The winner depends on the runner and object sizes.                       | Record compression CPU, stored bytes, GET/PUT time, peak RSS, and full job time.                                                   |
|    10 | P1       | `runs-on/action`                       | Make the action own `sccache` setup: verify the binary, set `CARGO_INCREMENTAL=0`, start with the final backend configuration, test readiness, and only then export `RUSTC_WRAPPER`. | Reduces setup mistakes, stale daemon configuration, and slow failure states.                                                                   | Missing binary, failed backend probe, and stale daemon tests fall back before compilation; normal setup adds negligible overhead.  |
|    11 | P1       | `runs-on/action`                       | Add JSON statistics and timing for setup, cache lookups, hits, misses, non-cacheable calls, writes, errors, and shutdown.                                                            | Identifies whether time is spent hashing, contacting S3, compiling misses, transferring hits, or compressing writes.                           | Every experiment produces a machine-readable record that can be paired with job wall time.                                         |
|    12 | P1       | `sccache`                              | Track multilevel writes and backfills and add a real drain operation that waits for accepted work before process shutdown.                                                           | Prevents warm-cache coverage from being lost at teardown. One trial left exactly 250 writes unfinished, followed by exactly 250 misses.        | A population run terminates with zero unfinished writes, and every acknowledged object is readable in a fresh job.                 |
|    13 | P1       | `sccache`                              | Reuse bytes from a lower-tier cache hit when backfilling an earlier tier instead of fetching the same object again.                                                                  | Removes a duplicate remote read on multilevel lower-tier hits.                                                                                 | Request tracing demonstrates one origin fetch per hit rather than two, with unchanged outputs.                                     |
|    14 | P1       | `sccache`                              | Replace the fixed lookup ceiling with configurable connect, first-byte, idle, and total deadlines plus a temporary circuit breaker.                                                  | Prevents backend trouble from imposing long delays on many compiler invocations.                                                               | Injected slow or failed backends fall back within the declared budget, and healthy warm performance does not regress.              |
|    15 | P1       | `sccache`                              | Stream or spill large remote cache objects rather than always buffering each complete object in memory.                                                                              | Reduces peak RSS and permits useful concurrency without allocator pressure.                                                                    | Measure peak RSS, spill bytes, object latency, and full job time at representative concurrency.                                    |
|    16 | P1       | `runs-on/runs-on` and `runs-on/action` | Add first-class sticky persistence for `SCCACHE_DIR`, with one local cache owner and S3 as the shared fallback tier.                                                                 | Potentially turns repeated jobs on the same lineage into local-disk hits and avoids thousands of S3 GETs. This is the strongest larger design. | Include snapshot restore and save time in the comparison; promote only if complete job time beats direct S3.                       |
|    17 | P1       | `runs-on/runs-on` and `sccache`        | Re-test `disk,s3` only after sticky persistence and reliable drain exist.                                                                                                            | The previous ephemeral local tier paid population cost but vanished before the next job and lost background S3 writes.                         | Compare sticky local hits, S3 hits, population completeness, restore/save overhead, and total job time.                            |
|    18 | P2       | `runs-on/runs-on`                      | Prototype a read-only runner-local WebDAV gateway in front of S3. Begin as a pass-through measurement, then add bounded negative caching and same-key request coalescing separately. | Could reduce repeated confirmed-miss latency and duplicate concurrent fetches while keeping `sccache` on a supported backend.                  | Measure gateway-only overhead first; each feature must independently improve complete job time against hardened direct S3.         |
|    19 | P2       | RunsOn gateway experiment              | Build a generation-scoped membership index for known cache objects so confirmed absences can be answered locally. Do not list an unbounded prefix during every job.                  | Could turn many cold S3 lookups into local negative answers.                                                                                   | Index build/download cost plus job time must beat origin-confirmed misses without hiding valid objects.                            |
|    20 | P2       | RunsOn gateway experiment              | Evaluate immutable object packs with a compact index and S3 range reads.                                                                                                             | Could replace thousands of small-object GETs with fewer larger requests.                                                                       | Trace useful and wasted bytes, range-request reduction, pack-build cost, retained duplication, and full job time.                  |
|    21 | P3       | `runs-on/runs-on` and OpenDAL          | Revisit S3 Express One Zone only after the exact `sccache`/OpenDAL build supports directory buckets.                                                                                 | May reduce small-object latency, but requires backend support and a same-AZ deployment.                                                        | Paired Standard S3 versus Express tests using identical objects, runner placement, and workload.                                   |
|    22 | P3       | Alternative service experiment         | Test Redis or Valkey only if sticky local storage and the WebDAV experiment leave a significant remote-latency problem.                                                              | A nearby shared memory tier may improve small-object hits but adds service cost and operations.                                                | It must beat direct S3 and sticky local caching after including service and operational cost.                                      |
|    23 | P3       | OpenDAL and Magic Cache experiment     | Do not prioritize the native GitHub Actions cache backend until upload-finalization errors are propagated and fresh-job visibility is proven.                                        | No demonstrated performance advantage currently justifies making it an early experiment.                                                       | An acknowledged upload must be readable by a fresh job before performance testing begins.                                          |

## Recommended Work Packages

### Package A: Immediate workflow improvements

Complete tasks 1–9. These require no major architecture and should establish whether retention, deliberate population, readiness bypass, installer removal, compression, and concurrency already capture most available value.

### Package B: Focused upstream requests

Prepare small, independently reviewable requests for tasks 10–15:

1. `runs-on/action`: transactional setup and readiness bypass.
2. `runs-on/action`: structured `sccache` statistics.
3. `sccache`: tracked background operations and drain.
4. `sccache`: remove the duplicate multilevel backfill fetch.
5. `sccache`: staged deadlines and circuit breaking.
6. `sccache`: streaming or bounded spill for large entries.

### Package C: Best larger RunsOn design

Implement tasks 16–17 as one coherent experiment: sticky `SCCACHE_DIR`, one local owner, S3 fallback, and reliable drain. This should be attempted before designing a new remote cache service.

### Package D: Gateway research

Attempt tasks 18–20 only if Packages A–C leave substantial S3 miss or hit latency. Build the gateway incrementally:

1. WebDAV pass-through.
2. Bounded negative cache.
3. Same-key request coalescing.
4. Generation membership index.
5. Immutable packs and range reads.

Do not combine all gateway features in one benchmark because the result would not identify which mechanism helped.

## WebDAV And Server-Mode Clarification

The [gateway proposal](gateway.md) evaluates a loopback WebDAV service in front of S3.

These are two different configuration dimensions:

| Dimension                | Choices                                                                   |
| ------------------------ | ------------------------------------------------------------------------- |
| Storage backend          | Direct S3, WebDAV, Redis, GitHub Actions cache, local disk, or multilevel |
| `sccache` execution mode | Normal daemon/server mode or client-side mode                             |

Therefore, “WebDAV instead of direct S3” does not mean “WebDAV instead of default server mode.” A sensible WebDAV experiment would continue using normal `sccache` server mode while changing only the storage backend from S3 to a loopback WebDAV service.

Keep the protocol capabilities separate from features that a gateway would have to implement:

- WebDAV remains a per-key object protocol; it does not automatically batch compiler-object requests.
- Fetching and listing an entire S3 prefix at every job start can be unbounded and may cost more than it saves.
- Write-behind and teardown flushing would have to be implemented by the RunsOn gateway; selecting WebDAV does not provide them.
- The gateway can add negative membership, request coalescing, local caching, and optional packing, but each feature needs a separate benchmark.
- The existing evidence does not prove that S3 latency alone caused the complete cold regression; wrapper, hashing, lookup handling, and compilation interaction remain mixed together.

The recommended experiment is therefore normal `sccache` server mode using a loopback WebDAV backend, initially read-only and pass-through, followed by separately measured gateway optimizations.

## Deprioritized Ideas

- Client-side direct S3: measured substantially slower despite a high hit rate.
- Ephemeral `disk,s3`: the local tier disappears after the job and background writes were incomplete.
- Adding HTTP pooling from scratch: `sccache` already gives its S3 operator a shared HTTP client; tune and measure the existing pool instead.
- Broad speculative prefetch: likely to create read amplification unless driven by a measured predictor.
- Replacing direct S3 with another backend before retention, population, readiness, compression, concurrency, and sticky local persistence are tested.
