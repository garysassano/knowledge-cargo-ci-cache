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

The tested 1.11.1 importer already contains the merged [redundant-copy/hash optimization](https://github.com/jdx/mr-boxington/pull/353). It validates the closure, carries that proof forward, and adopts verified files by rename where possible. On the measured runner, staging and the destination store were on the same filesystem; the remaining cost was not explained by cross-filesystem copies. See [object-mode restore history](../research/mr-boxington-object-restore.md) for the isolated prototype, released directory transport, and remaining research options.

## Controlled action 1.3.1 versus 1.4.0 comparison

On 2026-09-16, a new cold/warm pair ran five concurrent arms in each workflow: S3-backed `sccache`, mbx object mode with action 1.3.1, mbx object mode with action 1.4.0, mbx target mode with action 1.3.1, and mbx target mode with action 1.4.0. Both action versions used mbx 1.12.0, so the object-mode comparison isolates the action transport change from the engine version. The current `@v1` reference resolved to action 1.4.0 commit `867fc530`.

Every arm used the same source revision, Rust 1.98.1, Linux x86-64 16-vCPU runner class, Docker builder, dependency-fetch step, eight Cargo jobs, disabled incremental compilation, and fixed three-package Clippy-and-nextest workload. Cold jobs used isolated empty namespaces; warm jobs required exact hits against their corresponding cold outputs. Each cell is one fresh-runner job.

| Strategy            | mbx    | Action |  Cold job | Cold native checks |  Warm job | Warm native checks | Warm import |
| ------------------- | ------ | ------ | --------: | -----------------: | --------: | -----------------: | ----------: |
| RunsOn S3 `sccache` | —      | 0.17.0 |     4m04s |              2m25s |     3m08s |              1m28s |           — |
| mbx objects         | 1.12.0 | 1.3.1  |     4m02s |              2m12s |     3m16s |              1m22s |       5.97s |
| mbx objects         | 1.12.0 | 1.4.0  | **3m50s** |          **2m12s** | **3m01s** |          **1m19s** |   **0.26s** |
| mbx target          | 1.12.0 | 1.3.1  |     3m58s |              2m13s | **2m41s** |            **48s** |           — |
| mbx target          | 1.12.0 | 1.4.0  |     4m00s |              2m18s | **2m41s** |                49s |           — |

Both object-mode warm jobs restored 773 actions and 4,914 objects, representing 3.0 GiB logically and approximately 625–626 MiB in the GitHub cache. Both reported 449 Clippy hits and 322 nextest hits with zero misses. The action 1.3.1 arm restored a tar and imported it in 5.97 seconds. The action 1.4.0 arm restored a directory bundle and imported it in 0.26 seconds.

Action 1.4.0 object mode finished 15 seconds ahead of action 1.3.1 and seven seconds ahead of sccache at the complete-job level. Its native-check step was three seconds faster than action 1.3.1 and nine seconds faster than sccache. The target-mode results were effectively unchanged between action versions, which is expected because action 1.4.0 changes object transport rather than target payload behavior.

The cold workflow is useful as a same-batch population check, but each arm remains a single observation. The controlled warm result provides the strongest current evidence because it holds the mbx version and surrounding workflow constant while changing the action transport. Sanitized records are preserved in [the controlled action comparison data](data/mr-boxington-action-transport.jsonl).

## Controlled mbx 1.12.0 versus 1.15.0 comparison

On 2026-09-22, a controlled fresh-runner experiment compared S3-backed sccache 0.17.0 with mbx 1.12.0 and 1.15.0. Both MBX arms used action 1.4.0 with explicit GitHub object mode. Every arm used the same source revision, Rust 1.98.1, Linux x86-64 16-vCPU compute class, Docker builder, dependency-fetch phase, eight Cargo jobs, disabled incremental compilation, empty target directory, and three-package Clippy-and-nextest workload. One isolated cold cache was populated per arm, followed by three exact-warm baseline samples, one shared-dependency comment change, and one leaf-package comment change. The two MBX arms ran concurrently; sccache ran after one runner slot became available.

| Strategy | Cache state | Samples | Median job wall | Median measured job | Median workload | Hits / misses / unconsulted | Archive bytes | Correctness |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| S3-backed sccache 0.17.0 | Exact warm | 3 | 196s | 184.42s | 93.93s | 1,529 / 1 / not applicable | not measured | Pass |
| mbx 1.12.0 objects | Exact warm | 3 | 198s | 179.19s | 80.38s | 781 / 0 / 0 | 666,473,914 | Pass |
| mbx 1.15.0 objects | Exact warm | 3 | 198s | 181.97s | 80.83s | 788 / 0 / 0 | 675,956,335 | Pass |

The exact-warm workload median for 1.15.0 was 0.45 seconds slower than 1.12.0, while complete-job medians were equal at the available one-second timestamp precision. Version 1.15.0 restored seven additional actions and 43,628,044 additional output bytes. Its reports removed the six native-library bypasses that remained in 1.12.0 across Clippy and nextest. Both versions reported zero exact-warm misses, zero unconsulted actions, and zero remote failures.

The shared-dependency change produced four misses in each MBX arm: 1.12.0 completed the measured job in 182.75 seconds with a 79.70-second workload, while 1.15.0 completed it in 183.03 seconds with an 81.61-second workload. The leaf comment change produced zero MBX misses: 1.12.0 completed the measured job in 182.85 seconds with an 80.01-second workload, while 1.15.0 completed it in 183.88 seconds with an 80.61-second workload. All changed-source jobs passed, and neither MBX version reported a remote failure.

The 1.15.0 cold archive was 9,482,421 bytes, or about 1.4%, larger than the 1.12.0 archive. The result qualifies 1.15.0 for this portable object-mode canary because its performance was neutral within the observed variation and it expanded native-library coverage without correctness or remote-cache regressions. Sanitized records are preserved in [the mbx 1.15.0 object-mode data](data/mr-boxington-1.15-object-mode.jsonl).

## Action object transport versus native S3

On 2026-09-16, a separate two-arm cold/warm experiment compared mbx 1.12.0 through action 1.4.0 object mode with the same MBX client using its native S3 remote. Both arms ran concurrently from the same source revision on the same c8a 16-vCPU runner class, with eight Cargo jobs, disabled incremental compilation, the same Docker build environment, and the same three-package Clippy-and-nextest workload. The cold pair used fresh isolated namespaces; the warm pair immediately reused those namespaces.

| Phase                |                    Action 1.4.0 objects |                                          Native S3 |
| -------------------- | --------------------------------------: | -------------------------------------------------: |
| Cold job             |                                   3m53s |                                              3m53s |
| Cold native checks   |                                   2m14s |                                              2m16s |
| Cold Clippy          |                                  35.05s |                                             35.89s |
| Cold nextest build   |                                  50.95s |                                             51.83s |
| Warm job             |                               **3m01s** |                                              3m06s |
| Warm native checks   |                               **1m21s** |                                              1m29s |
| Warm Clippy          |                              **16.34s** |                                             21.99s |
| Warm nextest build   |                              **17.47s** |                                             17.65s |
| Warm hits            |                               449 + 322 |                                          449 + 322 |
| Warm remote transfer | 626 MB compressed archive restored once | 3.0 GiB during Clippy, then 1.5 KiB during nextest |

The cold jobs were effectively tied. Native S3 uploaded 822.3 MiB during Clippy and 2.2 GiB during nextest, approximately 3.0 GiB of logical objects. The action saved the equivalent 773-action, 4,914-object closure through the Actions cache. Its warm restore transferred 655,928,082 bytes, then imported the 3.0 GiB logical directory closure.

The native-S3 warm Clippy command reported 449 hits, zero misses, 413 prefetched objects, and 3.0 GiB downloaded. Nextest reported 322 hits, zero misses, and only 1.5 KiB downloaded because the Clippy prefetch had already populated the local store. The action arm had the same hit counts and served them from the restored local closure.

This establishes that direct S3 worked correctly with exported RunsOn instance-role credentials, but it did not improve this workload: action object mode was five seconds faster for the job and eight seconds faster for the native-check step. The comparison does not measure the existing `mr-boxington-cache` server, whose protocol adds compression, packs, batched lookup, and action promises. Sanitized records are in [the remote-backend data](data/mr-boxington-remote-backends.jsonl).

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
- The corrected mbx 1.11.1 experiment showed that object mode could make the Cargo phase slightly faster than sccache while losing end to end on eager tar restore/import overhead.
- The controlled mbx 1.12.0 experiment shows that action 1.4.0's directory transport removes that measured disadvantage: object mode finished seven seconds ahead of sccache and fifteen seconds ahead of action 1.3.1 in the same warm batch.
- Target mode produced the strongest result, but it restores Cargo target state and has different compatibility boundaries from clean-target object caching.
- The same-batch remote comparison found action object mode faster than native S3 for this workload; native S3's 3.0 GiB warm Clippy download was substantially larger than the 626 MB compressed action archive.
- The 12-second cold advantage for `mr-boxington` is directional and smaller than the 37-second warm advantage for `sccache`.
- Cache hit or restore status must be interpreted alongside end-to-end wall time and tool-specific rejection or miss diagnostics.

## Limitations

- The experiments before the mbx 1.15.0 qualification generally have one measured run per strategy and cache state, so those differences remain directional. The 1.15.0 comparison adds three exact-warm baseline samples but only one cold and one sample for each source-change shape.
- The two strategies use different cache models and expose different statistics; object counts are not directly comparable with compiler-request hit counts.
- The historical mbx 1.3.0 result includes its stable-path limitation; the 1.11.1 retest corrected that integration.
- The workload ran Cargo inside Docker. Native host builds may behave differently.
- The workload is one anonymized Rust monorepo and should not be treated as a universal performance ranking.
- The same-job, original cross-run, corrected 1.11.1, and controlled 1.12.0 experiments used different versions or workload shapes unless explicitly stated and should not be combined into one timing series.
- The native-S3 comparison used temporary credentials exported from the RunsOn instance role and passed into a trusted build container. It did not test repository-enforced IAM isolation or the MBX cache server.
- The mbx 1.15.0 qualification has three exact-warm baseline samples but only one cold, shared-change, and leaf-change sample. It uses one containerized workload and one runner class; native host builds and other dependency graphs may behave differently.
- The source-change cases used equivalent comment-only mutations against the current workload because the historical source revisions predated the measured container workload. Runner capacity serialized sccache after the paired MBX jobs.

## Implications

Canary mbx object mode with mbx 1.15.0 and action 1.4.0 alongside S3-backed `sccache` for portable clean-target reuse. Set the GitHub backend and object payload explicitly. The controlled workload found 1.15.0 neutral to 1.12.0 on repeated exact-warm timing while expanding native-library coverage, and both versions remained faster than sccache in the measured workload phase. Treat target mode as a narrow target-state mechanism requiring multi-generation growth qualification. Treat `mr-boxington-cache` as an unmeasured server candidate rather than inferring its performance from direct S3.
