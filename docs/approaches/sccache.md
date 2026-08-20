# S3-Backed `sccache`

## Summary

| Field | Value |
| --- | --- |
| Status | Leading PR-CI candidate; adoption requires a representative canary |
| Use when | Jobs start with a clean target, source changes frequently, and eligible compiler outputs are reusable across commits. |
| Main tradeoff | Cargo orchestration, per-object remote operations, non-cacheable calls, build scripts, and final linking still run on every job. |

## Related Files

| File | Purpose |
| --- | --- |
| [RunsOn `sccache` canary workflow](../../examples/workflows/runs-on-sccache-canary.yml) | Generic trusted-writer canary without a separate Cargo-input archive and with compiler-cache statistics. |
| [RunsOn deployment](../deployments/runs-on/README.md) | Direct S3 configuration, namespace, IAM, and runner-specific notes. |
| [Vendor Rust and CI cache sources](../reference/vendor-ci-cache-sources.md) | External direct-object, near-cache-service, colocated archive-cache, and persistent-runner designs. |

## Design

`sccache` caches eligible compiler invocations rather than a complete Cargo target tree:

```text
Cargo requests a rustc invocation
  sccache hashes compiler, source, flags, features, and relevant inputs
    hit  -> fetch and materialize that invocation's outputs
    miss -> compile locally and store the new outputs
Cargo continues orchestration and linking on the runner
```

```mermaid
flowchart LR
    cargo[Cargo graph and orchestration]
    wrapper[sccache rustc wrapper]
    key[Compiler-input key]
    store[(S3 compiler-object store)]
    local[Local compilation]
    target[Clean local target tree]
    link[Local non-cacheable work and linking]

    cargo --> wrapper --> key
    key -->|hit| store --> target
    key -->|miss| local --> target
    local --> store
    cargo --> link --> target
```

Old compiler objects can remain in S3 until lifecycle expiry without being downloaded into every job. A lockfile, feature, compiler, or flag change creates different object keys instead of copying a previous target archive into a new one.

## Required Configuration Principles

- Set `CARGO_INCREMENTAL=0`; `sccache` and rustc incremental compilation are not compatible.
- Keep `target/` disposable and on fast local storage.
- Use a repository-, platform-, and schema-specific S3 prefix.
- Install `sccache`; enabling a backend does not install the executable.
- Print `sccache --show-stats` even when the build fails.
- Keep Cargo registry/Git input caching as a separate measured choice.
- Confirm object lifecycle, request cost, namespace growth, and error handling.

For RunsOn, `runs-on/action@v2` can configure its S3 backend with:

```yaml
- uses: runs-on/action@v2
  with:
    sccache: s3
```

The action exports the S3 backend environment and `RUSTC_WRAPPER=sccache`; a separate installer such as `Mozilla-Actions/sccache-action` is still required. A later `SCCACHE_S3_KEY_PREFIX` step overrides only the stack-wide default namespace rather than configuring a second backend. See the canonical [RunsOn deployment map](../deployments/runs-on/README.md#direct-s3-sccache) for the exact variables and workflow shape.

## Trust And Isolation

Direct S3 `sccache` traffic does not inherit Magic Cache protocol isolation automatically.

- Let only trusted canonical jobs write compiler objects.
- Give untrusted PR jobs a read-only IAM role or a separate trusted boundary before allowing them to read the shared namespace.
- `SCCACHE_S3_RW_MODE=READ_ONLY` limits `sccache` itself, but it does not prevent arbitrary workflow code from using broader S3 permissions attached to the runner.
- Use a dedicated bucket or narrowly scoped prefix policy when untrusted code can execute.

The writer policy must be enforced by IAM or an equivalent infrastructure boundary, not only by a workflow condition.

## What It Reuses

Current upstream Rust support caches crate outputs that do not invoke the system linker, including common `rlib`, `staticlib`, and metadata compilation. Outputs that invoke linking, such as binaries, procedural macros, `cdylib`, and `dylib`, are not cached in the same way.

Even a perfect cacheable hit rate leaves:

- Cargo dependency-graph traversal.
- Build-script execution and related orchestration.
- Procedural-macro and other linker-invoking outputs.
- Individual remote object lookups, downloads, decompression, and writes.
- Final linking and unsupported outputs.
- Creation of a fresh target tree.

## Strengths

- Reuses compiler work without restoring a complete historical target archive.
- Misses and invalidation occur per compiler invocation instead of per monolithic target tree.
- Avoids full-target tar/zstd extraction and recompression.
- Supports reuse across source changes when unaffected compiler inputs remain identical.
- Exposes hits, misses, non-cacheable calls, errors, and cache size statistics.

## Limitations

- High hit rate can still have modest absolute value on short builds.
- Thousands of small remote operations can create a latency floor.
- Build scripts, linking, and unsupported crate types remain local.
- Warm-cache and cold-population behavior differ.
- Direct object storage needs lifecycle, IAM, namespace, monitoring, and cost ownership.
- A compiler-cache outage or wrapper failure needs a tested rollback to direct rustc execution.

## Evidence

In the controlled benchmark, warm S3 `sccache` with input-only Cargo caching was about 21% faster end to end and 41% faster in the build step than no Rust cache. It produced 1,410 hits, zero misses in the corrected warm runs, 442 non-cacheable calls, and zero cache errors.

A later representative full-workload warm repeat using `sccache` 0.17.0 in default server mode reduced workload time from 21m20.929s to 10m11.120s and job time from 22m45s to 11m42s against the same-profile no-cache control. The preceding population run took 25m54.103s of workload time and wrote 5,599 objects, making it about 21% slower than no cache. Those runs and the later client-side, read-only, and multilevel trials all included input-only `Swatinem/rust-cache`; only the subsequent default-server ablation omitted it. The ablation retained 6,929 hits and zero misses and completed in 9m50.353s workload and 11m14s job time. That single cross-family observation was about 21 seconds faster in the workload and 28 seconds faster in the job, so it supports omitting the separate input archive by default but does not establish a stable effect size or prove direct interference between the actions. See [Cache Strategy Benchmarks](../evidence/cache-strategy-benchmarks.md).

Follow-up `sccache` 0.17.0 trials found that client-side direct S3 was not faster: the warm workload took 20m59.720s despite 6,661 hits and only 110 misses. A cold read-only control remained 16.9% slower than no cache, showing that hashing, remote miss lookup, wrapper, and miss-handling costs accounted for most of the observed cold regression rather than successful uploads alone. Client-side `disk,s3` also did not improve cold population, only 5,197 of 5,447 expected background S3 writes completed before teardown, and its warm partial repeat took 20m42.113s despite 6,521 hits.

## Decision

Use S3-backed `sccache` in default server mode as the leading canary for changing PR workloads after establishing the clean-target baseline. Do not combine it with a separate input-only Cargo archive by default. The two mechanisms own different data, but the measured combination added no compiler-cache reuse benefit and was directionally slower; add Cargo-input caching only when separately measured registry or Git download savings exceed its archive and action overhead. Do not enable client-side or multilevel modes based only on upstream architecture claims; the measured direct-S3 client path was substantially slower despite a high hit rate, and background multilevel writes were incomplete at teardown. Adoption still requires representative source, lockfile, cold, warm, and concurrent scenarios plus IAM-enforced trust separation, lifecycle ownership, cost checks, and a direct-rustc rollback. Do not adopt any mode from hit rate alone.

## Upstream References

- [`sccache` Rust support and limitations](https://github.com/mozilla/sccache/blob/main/docs/Rust.md)
- [`sccache` S3 backend](https://github.com/mozilla/sccache/blob/main/docs/S3.md)
- [`Mozilla-Actions/sccache-action`](https://github.com/Mozilla-Actions/sccache-action)
- [RunsOn `sccache` example](https://github.com/runs-on/action#sccache)
