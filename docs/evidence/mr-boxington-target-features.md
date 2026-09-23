# Mr. Boxington 1.15 target-mode features

Reviewed: 2026-09-22

## Question

Do the target-oriented features available in Mr. Boxington 1.15.0 work in a GitHub Actions target-mode lineage, and what do they retain across fresh runners? This evaluation covers `mbx adopt`, automatic post-build garbage collection, `mbx stats` with many managed targets, Cargo incremental compilation, shared `OUT_DIR`, workspace-root sharing, and compiler-notification forwarding. It records absolute behavior rather than comparing target mode with object mode or sccache.

## Upstream behavior under test

[Mr. Boxington 1.15.0](https://github.com/jdx/mr-boxington/releases/tag/v1.15.0) added target adoption, moved automatic store sweeping after the build returns, made `mbx stats` faster on machines with many checkouts, and enabled matching `OUT_DIR` trees to be reused across checkouts. The tested 1.15.0 configuration also enabled the 1.13.0 workspace-root sharing option and the 1.14.0 compiler-notification forwarding behavior.

The [1.4.0 action](https://github.com/jdx/mr-boxington-action/blob/v1.4.0/src/index.ts) exports `MBX_TARGET_VIEWS=0` for GitHub target mode and saves a pruned real `target/` directory. Its [target cleanup](https://github.com/jdx/mr-boxington-action/blob/v1.4.0/src/target-cache.ts) keeps selected `build`, `.fingerprint`, and `deps` entries but removes other profile directories, including Cargo `incremental/`. The harness therefore re-enabled managed target views after action setup, adopted the restored target, and moved the managed directory back to a real `target/` before the action post step. This adaptation tested the features together without claiming that action 1.4.0 invokes `mbx adopt` itself.

## Test setup

- Workload: an anonymized three-package containerized Rust workload running Clippy and nextest, with an edited Clippy follow-up in the exercise run.
- Runner: a fresh Linux x86-64 16-vCPU compute runner for each run.
- Toolchain: Rust 1.98.1 with eight Cargo jobs.
- Cache: Mr. Boxington 1.15.0 with action 1.4.0, `backend: github`, and `github-cache-mode: target`.
- Feature settings: `CARGO_INCREMENTAL=1`, `MBX_INCREMENTAL=1`, `MBX_SHARE_OUT_DIR=1`, `MBX_SHARE_WORKSPACE_ROOT=1`, `MBX_FORWARD_COMPILER_NOTIFICATIONS=1`, `MBX_GC_AUTO=1`, `MBX_GC_INTERVAL=0s`, and an explicit `MBX_TARGET_VIEWS=1` override after action setup.
- Lineage: one cold seed followed by two rolling fallback restores with cumulative source edits. Every workload completed its lint and test checks successfully.

The measured-job interval started before runner and cache setup and ended before the action post-save. The coarser job total includes the action post step. Durations and sizes below are sanitized measurements; the complete machine-readable record is in [`mr-boxington-1.15-target-features.jsonl`](data/mr-boxington-1.15-target-features.jsonl).

| Run | Cache state | Source state | Job total | Measured job | Cache setup | Workload |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| `mbx115-target-seed-01` | Cold | Baseline | 249 s | 232.765 s | 5.861 s | 135.478 s |
| `mbx115-target-exercise-01` | Rolling fallback | First edit | 253 s | 235.230 s | 22.648 s | 114.181 s |
| `mbx115-target-verify-01` | Rolling fallback | Second cumulative edit | 235 s | 218.311 s | 19.885 s | 98.347 s |

## Observations

### Target adoption

`mbx adopt` replaced each same-filesystem real target directory with a managed-target link while preserving its outputs. The seed's 24-byte probe took 61.317 ms. The exercise run adopted 5,245,708,998 logical bytes in 77.595 ms, and the verification run adopted 5,245,709,008 logical bytes in 78.557 ms. These are rename-based same-filesystem adoptions; they do not measure copying a target across filesystems.

The exercise also created 240 synthetic checkouts, each with a 256 KiB target. Recursive adoption managed all 240 targets, totaling 62,914,560 logical bytes, in 6,536.903 ms.

### Statistics with many managed targets

With 241 managed targets, five `mbx stats --json` samples took 148.073, 144.989, 145.556, 143.472, and 141.708 ms, for a median of 144.989 ms. After collection reduced the store to two managed targets, one post-collection sample took 48.993 ms. This establishes the absolute 1.15.0 behavior in this fixture; there is no 1.14.0 control here, so it does not independently establish the upstream approximate 10x release claim.

### Automatic garbage collection

After the 240 synthetic checkout roots were removed, a small triggering build returned in 89.650 ms. The automatic collector was first observed after that build had returned and remained observable for 502.554 ms. It reduced managed targets from 241 to 2 and recorded 62,914,560 logical target bytes as automatically pruned. This directly confirms detached post-build collection for the local managed-target store when collection is forced due with a zero interval.

Automatic MBX collection and action target pruning are separate mechanisms. The collector handled abandoned MBX-managed targets on the active runner; it did not impose a byte, age, or generation bound on the target archive transported by the GitHub action.

### Cargo incremental behavior

The seed Clippy and nextest commands reported 13 and 10 `incremental` bypasses. The exercise's edited follow-up reported 9 incremental bypasses while 91 other compilations hit the MBX action cache with zero misses, and one Cargo incremental directory existed afterward. MBX's report exposed this work under `bypasses.incremental`; the `incremental_compilations` field remained zero in the captured version-5 report.

Neither rolling restore contained a Cargo incremental directory. The verification restore repeated this result after the exercise run had produced one. In this action configuration, Cargo incremental state therefore benefited work only within the active job: incremental compilations bypassed MBX's shared action cache, and action target cleanup removed their `incremental/` directory before transport.

### Other enabled sharing behavior

Shared `OUT_DIR`, workspace-root remapping, and compiler-notification forwarding were enabled for all valid runs, and all output checks passed. They were not independently ablated, so the measurements do not assign a timing change or cache-hit count to any one of these settings. Workspace-root remapping also changes recorded source paths and should remain an explicit compatibility choice rather than an assumed performance win.

The 1.14.0 miss-path changes and native-library cache support were also inherent in the 1.15.0 binary. No valid target-run report listed a native-library bypass, but this evaluation did not isolate their timing contribution.

## Excluded setup attempts

Three setup attempts were discarded before the valid lineage. One had nested-shell quoting and environment precedence errors that prevented the intended incremental configuration. One expected Cargo incremental work in the obsolete `incremental_compilations` interpretation instead of `bypasses.incremental`. One read the obsolete flat managed-target statistic instead of `cache.managed_targets`. They did not advance the valid target-cache lineage, and none of their values appears in the result tables or JSONL.

## Interpretation

The 1.15.0 target-management features worked in the adapted harness. Adoption was cheap for an existing 5.25 GB same-filesystem target, detached collection removed abandoned managed targets after the build returned, and statistics remained sub-150 ms with 241 managed targets. These results make the features useful for persistent local targets and long-lived machines.

They do not by themselves make the GitHub target payload bounded. Action 1.4.0 disables managed target views for target transport and applies its own metadata-based pruning to a real target directory. A workflow that wants adoption must deliberately re-enable views and restore a real target before post-save, while automatic MBX collection remains local to managed targets.

Cargo incremental mode presents a direct tradeoff in this configuration. It preserved state for an edited command within one job, but those compilations were deliberately outside MBX's portable action cache and their incremental directories were absent on the next runner. Enable it when same-job incremental edits are a real workload; do not expect action target mode 1.4.0 to carry that state across jobs.

## Limitations and implication

This was one short three-run rolling lineage on one workload. The statistics fixture was synthetic, garbage collection was forced due, adoption stayed on one filesystem, and the sharing features were enabled together. The run does not measure long-term target-archive growth, cancellation, concurrent writers, archive races, or a 1.14.0 performance baseline.

Decision D9 remains unchanged: object mode is the qualified portable canary, while target mode still needs a multi-generation changed-source soak showing bounded transported archive size. Use these measurements to configure or diagnose persistent managed targets, not as qualification of the GitHub target archive's retention behavior.

## JSONL metric names introduced here

The data file adds the `incremental_followup` aggregate phase and self-describing target-feature metrics: `mbx_adopt_duration_ms`, `adopted_target_bytes`, `restored_incremental_directories`, command-specific `incremental_bypasses`, `incremental_directories_after_followup`, `recursive_adopt_duration_ms`, `recursive_adopted_targets`, `recursive_adopted_target_bytes`, `mbx_stats_duration_ms`, `managed_targets`, `automatic_gc_trigger_build_ms`, `automatic_gc_observed_duration_ms`, `automatic_gc_pruned_target_bytes`, and `post_gc_stats_duration_ms`. Repeated statistics samples carry a numeric `sample` field.
