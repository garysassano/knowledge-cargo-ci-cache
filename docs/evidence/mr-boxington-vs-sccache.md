# `mr-boxington` vs `sccache`

## Question

How does `mr-boxington` compare with S3-backed `sccache` for clean-target Rust CI, both for local reuse within one job and for cache reuse across fresh runners?

## Same-Job Local-Reuse Experiment

On 2026-08-31, `mr-boxington` 1.2.0 was compared with `sccache` 0.17.0 on the same revision of a large Rust monorepo and the same 16-vCPU Linux runner.

Both jobs fetched dependencies before timing, disabled incremental compilation, and ran `cargo check --all-targets`. Each ran once with an empty target directory, deleted it, then repeated the check using the same target path.

| Strategy                   |    Cold | Warm after deleting `target` | Warm reduction |
| -------------------------- | ------: | ---------------------------: | -------------: |
| RunsOn direct-S3 `sccache` | 87.10 s |                      39.61 s |          54.5% |
| Local `mr-boxington` store | 73.31 s |                      35.32 s |          51.8% |

Warm-cache observations:

- `sccache`: 979 Rust hits, 0 Rust misses, and a 100% Rust hit rate.
- `mr-boxington`: 1,463 hits from 1,711 lookups (85.5%), 1,463 compiler invocations avoided, and 2,851 output files / 2.09 GiB restored.

`mr-boxington` was 4.29 seconds (10.8%) faster on the warm check and 13.79 seconds faster while populating its local cache.

This experiment tested same-job local reuse, not the GitHub Actions cache backend or fresh-runner restoration. The `sccache` cold phase had no Rust hits, but it did reuse 435 native C/assembler entries from its shared S3 cache.

## Cross-Run Fresh-Runner Experiment

On 2026-09-01, a separate experiment compared RunsOn S3 `sccache` with `jdx/mr-boxington-action@v1` using `mr-boxington` 1.3.0.

Each result came from a separate fresh `c8a.4xlarge` runner. Every job used the same source revision, toolchain, container image, eight Cargo build jobs, fixed multi-package lint-and-test workload, and an empty dedicated target directory. The cold run used an empty cache namespace; the warm run reused only the cache produced by its corresponding cold run. Cold and warm work did not run sequentially in one job.

The Cargo commands ran inside Docker while cache restore and export ran on the host. For `mr-boxington`, the parent of `mbx cache dir` was bind-mounted at the container's `$HOME/.cache/mbx`, and the action-provided export variables were forwarded into the container.

The sanitized records are preserved in [the cross-run measurement data](data/mr-boxington-sccache-cross-run.jsonl).

| Strategy             | Cache state | Job wall time | Workload wall time | Cache evidence                                                              |
| -------------------- | ----------- | ------------: | -----------------: | --------------------------------------------------------------------------- |
| RunsOn S3 `sccache`  | Cold        |         6m38s |              4m54s | 0 Rust hits, 675 Rust misses                                                |
| RunsOn S3 `sccache`  | Warm        |         5m47s |              3m57s | 674 Rust hits, 1 Rust miss; 99.85% hit rate                                 |
| `mr-boxington` 1.3.0 | Cold        |         6m26s |              4m37s | Exact miss; 64 objects totaling about 70.5 MiB after the build              |
| `mr-boxington` 1.3.0 | Warm        |         6m24s |              4m35s | Exact restore; the store still contained 64 objects totaling about 70.5 MiB |

The `mr-boxington` cold job was 12 seconds faster than the `sccache` cold job. The `sccache` warm job was 37 seconds faster than the `mr-boxington` warm job.

Relative to its own cold run, `sccache` saved 51 seconds at the job level and 57 seconds in the measured workload. `mr-boxington` saved two seconds at both levels.

## Path-Mapping Observation

The `mr-boxington` action restored the expected exact cache, so the weak warm result was not an action-level cache miss. During the containerized Cargo workload, most reusable Rust results were rejected with warnings equivalent to:

```text
prediction was not restored: absolute path has no stable cache mapping: <container-cargo-home>/registry/src/...
result was not stored: absolute path has no stable cache mapping: <container-cargo-home>/registry/src/...
```

This indicates that the containerized Cargo registry path was not represented by a stable cache mapping. The exact action cache therefore restored successfully while most compiler results remained unusable.

The cache-store mount itself required care. Mounting the host path returned by `mbx cache dir` directly at the container cache root created a nested `actions/actions` store. The working layout mounted `dirname "$(mbx cache dir)"` at `$HOME/.cache/mbx` in the container.

## Source follow-up

The [public path-mapping report](https://github.com/jdx/mr-boxington/discussions/258) identifies a Cargo registry child symlink whose canonical destination lies outside the canonical `CARGO_HOME` mapping root. The [v1.3.2 normalization implementation](https://github.com/jdx/mr-boxington/blob/v1.3.2/crates/mbx-cache-core/src/path_mapping.rs) supports that explanation. The [maintainer response](https://github.com/jdx/mr-boxington/discussions/258#discussioncomment-18240056) confirms the analysis, says 1.3.2 did not change it, and recommends mounting the registry directly at `$CARGO_HOME/registry`. [PR #259](https://github.com/jdx/mr-boxington/pull/259) merged on 2026-09-01 and adds a dedicated `cargo_registry` mapping. That mapping is present in [v1.9.0 rustc setup](https://github.com/jdx/mr-boxington/blob/v1.9.0/crates/mbx/src/rustc.rs). This archive has not repeated the benchmark with the fix or direct mount.

Source refresh on 2026-09-06 found mbx 1.9.0 and action v1.3.0, whose default GitHub payload is now `target`. These releases have not been retested here. Use [the approach's version boundary](../approaches/mr-boxington.md#version-and-backend-boundary) and [integration diagnostics](../operations/diagnosing-compiler-cache-integration.md) when reproducing the object-cache experiment.

## Record interpretation

`cache_state: warm-exact` in the mbx records identifies the exact action archive restore. It does not mean Rust predictions were reusable. `rust_cache_hits` and `rust_cache_misses` are tool-reported Rust request counts; `cache_objects_after` counts mbx store objects, which are not equivalent units. `cache_size_after` converts the rounded 70.5 MiB report into bytes and retains rounded precision. The same-job trial has an archived summary only, not an additional raw JSONL series. Compiler/container identities omitted from the original sanitized records are not reconstructed.

## Interpretation

- The same-job experiment shows that `mr-boxington` can be competitive with `sccache` when its local results are reusable.
- The fresh-runner experiment shows that a successful exact action-cache restore is not sufficient evidence of useful compiler reuse.
- In this containerized workload, S3 `sccache` delivered the stronger warm end-to-end result because nearly all Rust requests hit, while `mr-boxington` was constrained by unstable absolute Cargo-registry paths.
- The 12-second cold advantage for `mr-boxington` is directional and smaller than the 37-second warm advantage for `sccache`.
- Cache hit or restore status must be interpreted alongside end-to-end wall time and tool-specific rejection or miss diagnostics.

## Limitations

- Each cross-run strategy and cache state has one measured run, so the differences are directional rather than stable medians.
- The two strategies use different cache models and expose different statistics; object counts are not directly comparable with compiler-request hit counts.
- The `mr-boxington` result measures the tested container integration, including its unresolved stable-path limitation, rather than the best performance the tool might achieve with a supported path mapping.
- The workload ran Cargo inside Docker. Native host builds may behave differently.
- The workload is one anonymized Rust monorepo and should not be treated as a universal performance ranking.
- The same-job and cross-run experiments used different `mr-boxington` versions and workload shapes and should not be combined into one timing series.

## Implications

Keep S3-backed `sccache` as the stronger measured option for this clean-target, fresh-runner workload. Re-evaluate `mr-boxington` using the upstream registry-mapping fix or maintainer-recommended direct mount, then repeat independent cold and warm runs with the same controls. The historical timings do not quantify the corrected integration.
