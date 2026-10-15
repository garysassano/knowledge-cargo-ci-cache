# sccache and Mr. Boxington through RunsOn Magic Cache

Measured 2026-10-15. Raw records: [`data/runs-on-magic-cache-sccache-mbx.jsonl`](data/runs-on-magic-cache-sccache-mbx.jsonl).

## Question

On RunsOn v3.5.0 with Magic Cache isolation enabled, how do the two compiler caches that store per-object entries through Magic Cache compare with no cache on cold, warm and pull-request builds?

- `sccache: true` stores sccache's entries through its GitHub Actions cache backend.
- `mbx: true` runs a helper that serves mbx's remote protocol and stores mbx's objects as GitHub Actions cache entries.

Neither integration was released when this was measured. `sccache: true` was [runs-on/action#78](https://github.com/runs-on/action/pull/78) at `b966bcf`. `mbx: true` was [runs-on/action#65](https://github.com/runs-on/action/pull/65) at `69af66d`. Both PRs were open on 2026-10-15.

## Test setup

| Field       | Value                                                                                                                                                                                           |
| ----------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Stack       | RunsOn v3.5.0, Flex CloudFormation, `EnableCacheIsolation: "true"`, default 10-day cache retention                                                                                              |
| Runner      | `c7a.8xlarge` on demand (32 vCPU, x86_64), fresh runner per job, `ubuntu24-full-x64` image                                                                                                      |
| Workload    | Public [ruff](https://github.com/astral-sh/ruff) 0.17.0, `cargo build --locked -p ruff`, dev profile, Rust 1.99.0, `CARGO_INCREMENTAL=0` (the workload of runs-on/action#78's own measurements) |
| Timed phase | The build command only. Toolchain installation and `cargo fetch --locked` ran in an earlier, untimed step.                                                                                      |
| sccache     | 0.18.0 installed with `taiki-e/install-action` before the action                                                                                                                                |
| mbx         | 1.24.0 through `jdx/mr-boxington-action@v1.7.2` with `backend: remote`, running `mbx build --locked -p ruff`                                                                                    |
| Repetitions | Two per strategy and scenario, each with its own `SCCACHE_GHA_VERSION` / `MBX_REMOTE_NAMESPACE` so repetitions never shared entries                                                             |

Scenarios:

- **Cold:** a push with an empty namespace; the job builds and publishes.
- **Warm:** another job on another runner, same commit and namespace, after the cold jobs finished.
- **Pull request, first run:** a pull request against the pushed commit that appends one constant to `crates/ruff_linter/src/lib.rs`, the crate most ruff pull requests change. It rebuilds that crate and everything that depends on it. The namespace is derived from the base commit, so it reads what the push published.
- **Pull request, re-run:** the same pull-request run re-run about a minute later, which tests whether a pull request reuses its own earlier work.

The test repository could not use branch protection on its plan. In push jobs only, `mbx build` therefore ran with `GITHUB_EVENT_NAME=push GITHUB_REF_TYPE=branch GITHUB_REF_PROTECTED=true` so that mbx's client would publish; Magic Cache still scoped every write to the job's ref. Pull-request jobs ran unmodified, so mbx only read in them.

## Observations

Build-step seconds, both repetitions:

| Scenario                                       | No cache   | `sccache: true` | `mbx: true` |
| ---------------------------------------------- | ---------- | --------------- | ----------- |
| Cold: empty cache, publishes                   | 32.9, 32.2 | 59.8, 60.1      | 35.7, 35.3  |
| Warm: another runner, same commit              | not run    | 11.4, 11.9      | 7.2, 7.4    |
| Pull request changing `ruff_linter`, first run | 32.1, 32.0 | 54.5, 54.5      | 27.1, 27.1  |
| Same pull request, re-run                      | 32.1, 31.9 | 54.6, 55.2      | 27.2, 26.8  |

Whole-job seconds, including setup, toolchain, fetch and post steps:

| Scenario                | No cache | `sccache: true` | `mbx: true` |
| ----------------------- | -------- | --------------- | ----------- |
| Cold                    | 62, 61   | 90, 88          | 63, 64      |
| Warm                    | not run  | 42, 43          | 39, 37      |
| Pull request, first run | 61, 61   | 86, 85          | 58, 57      |
| Pull request, re-run    | 58, 60   | 81, 84          | 55, 56      |

A no-cache build compiles everything every time, so its warm build is a cold build, about 32 s.

Cache counters, identical in both repetitions:

| Scenario                | sccache                                                                                           | mbx                                                                                                   |
| ----------------------- | ------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| Cold                    | 401 compile requests: 310 misses, 310 writes, 0 write errors, 81 not cacheable (69 by crate type) | 4,603 objects uploaded (1.7 GiB), 1 manifest; mbx reported 597 actions not looked up and 339 bypassed |
| Warm                    | 310 hits, 0 misses                                                                                | 410 action hits, 0 misses, 1.6 GiB downloaded                                                         |
| Pull request, both runs | 280 hits, 30 misses, 30 writes                                                                    | 403 hits, 7 misses, 0 uploads                                                                         |

Stored per cold build, from the bucket listing: sccache 311 objects, 240 MiB; mbx 4,604 objects, 1.7 GiB. sccache compresses its entries; the helper stores mbx's objects as they are.

### Where sccache's time went

sccache's own counters rule out uploads as the main cost. In each pull-request run its 30 writes took 1.9 s in total. In each cold run its 310 writes took 14.8 s, summed over compilations that ran in parallel.

The job logs carry a timestamp per line. Offsets from the start of the build step, pull-request first run (both repetitions within 0.1 s):

| Strategy        | `ruff_linter` starts | Its dependents start | Build ends |
| --------------- | -------------------- | -------------------- | ---------- |
| No cache        | +12.0 s              | 12.1 s after it      | +32.1 s    |
| `mbx: true`     | +6.7 s               | 12.0 s after it      | +27.0 s    |
| `sccache: true` | +17.2 s              | 21.5 s after it      | +54.5 s    |

Two pinned source observations at sccache v0.18.0 match this:

- The client writes the compiler's output to Cargo only after the server reports the compile finished (`handle_compile_finished` in `src/commands.rs`). The server reports it only after the cache write (`src/server.rs`). That output carries rustc's notice that a crate's metadata is ready, which is when Cargo starts dependent crates (pipelining). On a miss, dependents therefore wait for the crate's complete compile.
- Before every lookup, hits included, sccache runs rustc with `--emit dep-info` to list the crate's source files (`src/compiler/rust.rs`).

### Pull-request reuse

mbx's client never publishes from a pull request, so both pull-request runs rebuilt the same 7 actions.

sccache wrote its 30 entries into the pull request's own scope in both runs, but the two runs' key sets had no key in common, in either repetition. The re-run therefore missed again. A third run, about four minutes after the first, also missed all 30. ruff's build scripts embed the commit hash, date and last tag, which were identical in every run. The cause was not found. [runs-on/action#78](https://github.com/runs-on/action/pull/78) reports an unexplained 30-entry miss in one of its own `s3` warm runs.

### Functional checks

On the same stack, small Linux, `rust:1` container and Windows jobs published through the mbx helper. Another runner built from the Linux job's objects (17 hits, 0 misses, 0 errors), and a pull request built from what its base branch published without uploading. All 52 mbx objects of that check, and all benchmark entries, landed under the isolated `scoped-cache/<owner>/<repo>/<ref scope>/` prefix; none reached the shared `cache/` prefix.

## Interpretation

- On this 32-vCPU runner, `mbx: true` was the fastest strategy in every scenario. It cost about 3 s over no cache when cold, saved about 25 s when warm, and saved about 5 s on a pull request that rebuilt the crate at the end of the dependency chain.
- `sccache: true` saved about 21 s when warm but was slower than no cache when cold (+27.5 s) and on the pull request (+22.5 s). With 32 vCPUs, Cargo already overlaps most compilations, so build time follows the chain of dependent crates. Cache hits mostly save code generation, which pipelining already overlaps; on a miss, sccache lengthens that chain.
- mbx's warm advantage over sccache also includes work sccache cannot cache: mbx counted 410 actions to sccache's 310 cacheable compilations.
- Storage favours sccache by about 7×. Lifecycle cost and transfer volume scale with that.
- Neither strategy reused a pull request's own work across runs in this test: mbx by design, sccache for an unexplained reason.

## Limitations

- One public workload, one runner size, one profile and two repetitions. Smaller runners, where saved compile work counts for more than the dependency chain, were not measured.
- Unreleased integrations at the commits named above.
- The pull-request change touched a central crate. A change to a leaf crate or a no-op re-run of an unchanged commit was not measured.
- mbx publishing relied on overriding its trusted-context variables in push jobs, as described in the setup.
- Times exclude cache expiry, concurrency between jobs, and a lookup index past its documented 50,000-entry limit per directory.

## Implications

- [D7](../decisions/README.md) and [D9](../decisions/README.md) record the resulting statuses.
- Measure on the target runner size before enabling `sccache: true` for pull requests; its warm benefit can be outweighed by its miss path.
- The [RunsOn deployment map](../deployments/runs-on/README.md#compiler-caches-through-magic-cache) owns the configuration, and the [implementation reference](../reference/compiler-cache-implementation.md#release-refresh-2026-10-15) owns the versioned source behavior.
