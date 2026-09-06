# Decisions

This page is the single source of truth for the archive's current conclusions. Other pages, including the root `README.md` and `AGENTS.md`, summarize these decisions briefly and link here instead of restating them. When a conclusion changes, update it here first, record the superseded version in [history](history.md), then adjust the summaries that point here.

Treat these as archived conclusions, not timeless upstream facts. They reflect the evidence under [`docs/evidence/`](../evidence/README.md) and external behavior at the time of testing. Before changing any decision that depends on current action versions or service behavior, follow the [maintenance checklist](../operations/maintenance-checklist.md) and verify the relevant upstream documentation.

## Current Conclusions

| # | Decision | Status | Basis |
| --- | --- | --- | --- |
| D1 | For most RunsOn Rust projects, start with mise, Magic Cache, input-only `Swatinem/rust-cache`, and a clean local `target/`. Keep no Rust cache as the control and remove the input cache when measurement shows no material benefit. Do not use whole-target archives as the general default. | Recommended practical default | [Approach](../approaches/clean-target.md), [RunsOn deployment](../deployments/runs-on/README.md), [growth evidence](../evidence/target-archive-growth.md), [benchmarks](../evidence/cache-strategy-benchmarks.md) |
| D2 | Use `jdx/mise-action` backed by an `actions/cache` backend as the setup layer for Rust, Zig, and Cargo-distributed helper tools. | Recommended | [Mise tool setup](../operations/mise-tool-setup.md) |
| D3 | Keep source-keyed full-target archives only as a narrow exception for stable workloads with exact keys, small monitored archives, and no broad fallback that copies an older target tree forward. | Narrow exception | [Approach](../approaches/rust-cache-source-keyed-target-cache.md), [freshness evidence](../evidence/cached-worktree-and-target-cache.md), [growth evidence](../evidence/target-archive-growth.md) |
| D4 | Treat EBS/filesystem snapshots as the strongest local no-op fidelity option, but as an archived alternative because of operational and lifecycle complexity. | Archived alternative | [Approach](../approaches/ebs-snapshot.md), [evidence](../evidence/rust-cache-vs-snapshot.md) |
| D5 | Do not use S3 Files for Cargo target or registry no-op state; remote metadata/read behavior dominated even when Cargo was logically clean. | Rejected for this use | [Approach](../approaches/s3-files.md), [evidence](../evidence/s3-files.md) |
| D6 | Do not mix a full filesystem snapshot with `rust-cache` on the same `target/` or `$CARGO_HOME` paths. | Compatibility rule | [Canonical rule](../concepts/cargo-path-coverage.md#compatibility-rule-canonical) |
| D7 | Treat S3-backed `sccache` 0.17 in default server mode with a clean `target/` as the leading measured PR-CI compiler-cache candidate. Do not combine it with a separate input-only Cargo archive by default; add one only when measured registry or Git download savings justify its archive and action overhead. Client-side direct S3 was substantially slower despite a high warm hit rate, and multilevel background writes were incomplete at teardown. Adoption still requires change/concurrency coverage, IAM-enforced trust separation, lifecycle and cost ownership, and a tested direct-rustc rollback. | Leading candidate with strong warm evidence and measured cold risk | [Approach](../approaches/sccache.md), [benchmarks](../evidence/cache-strategy-benchmarks.md) |
| D8 | Evaluate RunsOn sticky disks after upgrading to RunsOn v3.2 or newer. Test built-in Cargo-input persistence before a custom sticky `target/`; a sticky target requires disk, inode, concurrency, cleanup, and reset controls. | Planned experiment | [RunsOn deployment](../deployments/runs-on/README.md) |

## Additional candidates

| # | Decision | Status | Basis |
| --- | --- | --- | --- |
| D9 | Keep Mr. Boxington experimental. Its same-job reuse was competitive, but the recorded fresh-runner Docker integration was limited by Cargo-registry path mapping despite an exact action-cache restore. The upstream mapping fix is present in mbx 1.9.0, but explicit payload modes and newer releases still need a fresh benchmark before adoption. | Experimental; version and integration limited | [Approach](../approaches/mr-boxington.md), [evidence](../evidence/mr-boxington-vs-sccache.md) |
| D10 | Index Kache as an untested alternative. This archive has not validated its correctness, performance, remote storage, or CI integration. | Not tested | [Kache sources](../reference/vendor-ci-cache-sources.md#kache-not-tested) |

The [RunsOn research collection](../research/runs-on-sccache/README.md) is an implementation and experiment proposal. It supplies no basis to promote a new backend or change D1–D8.

## Detailed Findings

These supporting findings explain why the decisions above hold. Keep the underlying explanation in the linked canonical pages; this section captures only the durable conclusion.

- The D1 default holds because it avoids whole-target growth while retaining reusable tool and dependency downloads. Input-only caching does not reuse compiler output, which is why its setup cost must beat normal downloads to stay. See [the clean-target approach](../approaches/clean-target.md).
- Whole-target `rust-cache` can produce warm Cargo no-op builds while an archive is compact and internally consistent. Its target cleanup is not size-bounded or generation-aware, and broad fallback restores can copy old artifact generations into each new immutable cache object. See [`rust-cache` behavior](../concepts/rust-cache-behavior.md).
- Normal `actions/checkout` can make restored target state less useful because it rewrites source mtimes. Preserve source mtimes only when reusing target/fingerprint state; it is not required for a clean-target design. See [the freshness model](../concepts/cargo-freshness-model.md) and [diagnosing rebuilds](../operations/diagnosing-rebuilds.md).
- `sccache` reuses eligible compiler outputs individually instead of restoring a complete target tree. It does not remove Cargo graph traversal, build scripts, procedural-macro orchestration, non-cacheable calls, or final linking, so hit rate alone is not an adoption metric. See [the `sccache` approach](../approaches/sccache.md).
- `mise-action` accelerates repeated toolchain and helper-tool setup; it does not by itself prove Cargo units fresh. See [mise tool setup](../operations/mise-tool-setup.md).
- Cargo no-op behavior requires a consistent set of proof artifacts (source contents, source mtimes, workspace path, target artifacts, dep-info, fingerprints, build-script outputs, dependency source paths, toolchain, profile, features, flags, and relevant env). If one is missing, stale, moved, or newer than expected, Cargo can mark units dirty. See [the freshness model](../concepts/cargo-freshness-model.md).

## Selected Deployment

The approaches are mapped onto RunsOn with Magic Cache, direct S3 `sccache`, and post-v3.2 sticky-disk options. See the [RunsOn deployment](../deployments/runs-on/README.md). Deployment-specific guidance lives there, not in the generic approach pages.

## Changing A Decision

1. Confirm new measured evidence exists under [`docs/evidence/`](../evidence/README.md).
2. Record the prior conclusion in [history](history.md) with what changed and why.
3. Update the affected row or finding above.
4. Update the brief summaries that link here (root `README.md`, `docs/quickstart.md`, `AGENTS.md`, and any approach page status fields).
