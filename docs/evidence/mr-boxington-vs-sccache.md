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

## Source follow-up and corrected retest

The [public path-mapping report](https://github.com/jdx/mr-boxington/discussions/258) identifies a Cargo registry child symlink whose canonical destination lies outside the canonical `CARGO_HOME` mapping root. The [maintainer response](https://github.com/jdx/mr-boxington/discussions/258#discussioncomment-18240056) confirms the analysis, and [PR #259](https://github.com/jdx/mr-boxington/pull/259) merged on 2026-09-01 with a dedicated `cargo_registry` mapping.

On 2026-09-15, the fresh-runner comparison was repeated with mbx 1.11.1 and `jdx/mr-boxington-action@v1`, resolving to action 1.3.1. The corrected integration produced reusable object-mode results, so it supersedes the old path-mapping limitation as the current-version performance observation while preserving the older trial as historical evidence.

Each cold and warm value below is one fresh-runner job. The workload used the same source revision, Rust 1.98.1, Linux x86-64 16-vCPU runner class, Docker builder, dependency-fetch step, eight Cargo jobs, disabled incremental compilation, and fixed multi-package Clippy-and-nextest checks. Cache namespaces were isolated, and warm mbx jobs required exact action-cache hits.

| Strategy            |  Cold job | Cold native checks |  Warm job | Warm native checks |
| ------------------- | --------: | -----------------: | --------: | -----------------: |
| RunsOn S3 `sccache` |     4m06s |              2m28s |     3m03s |              1m24s |
| mbx target mode     |     4m01s |              2m16s | **2m36s** |            **46s** |
| mbx object mode     | **3m54s** |          **2m12s** |     3m10s |              1m20s |

Warm cache evidence:

- `sccache`: 1,498 Rust hits, 1 Rust miss, and a 99.85% Rust hit rate. Clippy took 18.13 seconds and the nextest build took 18.75 seconds.
- mbx object mode: 449 Clippy hits and 322 nextest hits, totaling 771 hits with zero misses. Clippy took 15.45 seconds and the nextest build took 17.74 seconds.
- mbx object mode restored 4,914 objects and 773 actions. Its action store was 3.0 GiB logical, transported as an approximately 625 MiB GitHub cache entry.

The hit counters are not equivalent units. The command durations show that mbx object mode completed the Cargo work about four seconds faster than sccache, but it finished seven seconds slower at the complete-job level.

### Object-mode restore timeline

The GitHub cache restored an approximately 625 MiB zstd-compressed entry in about 3.02 seconds. Its payload was an uncompressed 3.0 GiB mbx tar. `mbx cache import` then spent 6.33 seconds unpacking, validating, and adopting the selected closure. Combined outer restore and inner import cost approximately 9.35 seconds.

```text
GitHub cache zstd/tar
  -> mbx export tar
     -> CAS objects and action results
```

The tested 1.11.1 importer already contains the merged [redundant-copy/hash optimization](https://github.com/jdx/mr-boxington/pull/353). It validates the closure, carries that proof forward, and adopts verified files by rename where possible. On the measured runner, staging and the destination store were on the same filesystem; the remaining cost was not explained by cross-filesystem copies. See [object-mode restore research](../research/mr-boxington-object-restore.md) for the isolated directory-import experiment and unimplemented options.

### Workspace-state experiment

mbx 1.8.0 added portable Cargo workspace-state attachments to object exports. The normal container benchmark did not export that state because builds recorded `/workspace` inside Docker while the action post step ran on the host. A diagnostic host mapping made capture and restore activate:

```text
exported 773 actions and 4,916 objects (4.3 GiB)
restored Cargo workspace state (1,289 referenced files, 3.0 GiB)
```

The following container build failed because host-side target restoration and container-side target management disagreed at `/workspace/target`. The payload grew from 625 MiB compressed and 3.0 GiB logical to 877 MiB compressed and 4.3 GiB logical; import grew to approximately 21.9 seconds. Complete workspace-state restoration is therefore not a performance improvement for this container layout without explicit host/container path semantics and more selective state handling.

## Record interpretation

`cache_state: warm-exact` in the mbx records identifies the exact action archive restore. It does not mean Rust predictions were reusable. `rust_cache_hits` and `rust_cache_misses` are tool-reported Rust request counts; `cache_objects_after` counts mbx store objects, which are not equivalent units. `cache_size_after` converts the rounded 70.5 MiB report into bytes and retains rounded precision. The same-job trial has an archived summary only, not an additional raw JSONL series. Compiler/container identities omitted from the original sanitized records are not reconstructed.

## Interpretation

- The same-job experiment shows that `mr-boxington` can be competitive with `sccache` when its local results are reusable.
- The original fresh-runner experiment shows that a successful exact action-cache restore is not sufficient evidence of useful compiler reuse.
- The corrected mbx 1.11.1 experiment shows that object mode can make the Cargo phase slightly faster than sccache while losing end to end on eager restore/import overhead.
- Target mode produced the strongest result, but it restores Cargo target state and has different compatibility boundaries from clean-target object caching.
- The 12-second cold advantage for `mr-boxington` is directional and smaller than the 37-second warm advantage for `sccache`.
- Cache hit or restore status must be interpreted alongside end-to-end wall time and tool-specific rejection or miss diagnostics.

## Limitations

- Each cross-run strategy and cache state in both fresh-runner comparisons has one measured run, so the differences are directional rather than stable medians.
- The two strategies use different cache models and expose different statistics; object counts are not directly comparable with compiler-request hit counts.
- The historical mbx 1.3.0 result includes its stable-path limitation; the 1.11.1 retest corrected that integration.
- The workload ran Cargo inside Docker. Native host builds may behave differently.
- The workload is one anonymized Rust monorepo and should not be treated as a universal performance ranking.
- The same-job, original cross-run, and corrected cross-run experiments used different `mr-boxington` versions or workload shapes and should not be combined into one timing series.

## Implications

Keep S3-backed `sccache` as the stronger measured portable clean-target option for this fresh-runner workload. Treat mbx target mode as a separate, faster mechanism when target-tree restoration is compatible. Re-evaluate object mode if upstream reduces nested archive import, eager closure validation, or container workspace-state overhead, and repeat paired trials before changing the decision.
