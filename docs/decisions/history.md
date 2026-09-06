# Decision History

This page records decisions that have changed, so the archive preserves what was previously concluded and why it was superseded. It is keyed by decision, not by date, and it is not a chronological experiment diary. Durable findings still live in the relevant concept, approach, operation, or evidence pages; this page only captures the transition when a [current conclusion](README.md) is overturned or materially revised.

## How To Add An Entry

When a decision in [`docs/decisions/README.md`](README.md) changes, append an entry below before overwriting the current conclusion. Include:

- The decision identifier (for example `D5`) and a short title.
- The prior conclusion, stated plainly.
- The new conclusion.
- The evidence or external change that prompted the revision, with a link.
- The date of the change.

## Entries

### D1 — Default Cargo cache approach

- Changed: 2026-08-20
- Prior conclusion: Use `Swatinem/rust-cache` with target caching, workspace-crate retention, and an mtime-preserving cached worktree as the default Cargo cache approach.
- New conclusion: For most RunsOn Rust projects, start with mise, Magic Cache, input-only `Swatinem/rust-cache`, and a clean local `target/`. Keep no Rust cache as the paired control, remove the input cache when measurement shows no material benefit, and treat whole-target archives as a narrow exception rather than the default.
- Reason: A production target archive grew from about 206 MB to 13.9 GB in under five days, and one representative job spent 65.8% of its time handling the cache. The controlled comparison then found only a small net gain from input-only caching, so the replacement default keeps tool setup and dependency downloads reusable without persisting mutable target state. See [target archive growth](../evidence/target-archive-growth.md), [cache strategy benchmarks](../evidence/cache-strategy-benchmarks.md), and the [clean-target approach](../approaches/clean-target.md).

### D3 — Source-keyed full-target archive

- Changed: 2026-08-20
- Prior conclusion: Keep the source-keyed full-target archive as a generally proven workaround for local workspace members that repeatedly rebuild on exact `rust-cache` hits.
- New conclusion: Keep it only as a narrow, measured exception for stable workloads whose archives remain small, exact-keyed, and monitored. Do not use broad fallback restore keys to copy an older mutable target tree into each new lineage.
- Reason: Source keying can fix stale exact-hit freshness, but it does not bound archive size or remove full-tree extraction and compression. Production evidence showed that copy-forward target archives can become slower than recompilation. See [target archive growth](../evidence/target-archive-growth.md).

### Research qualification and version corrections

- Reviewed: 2026-09-06.
- Prior coverage: The current decisions covered sccache and Cargo/filesystem approaches; they did not classify Mr. Boxington or Kache. The expanded proposal also needed to distinguish old upstream limitations from later releases.
- Change: Added experimental D9 and untested D10, retaining D1–D8. Kept local and fresh-runner evidence separate, documented the newer Mr. Boxington action's target-payload default and the merged registry-mapping fix without claiming a local retest, narrowed the cold-cache causal interpretation, and recorded the OpenDAL 0.59.0 GHA finalization and S3 Express updates against the sccache 0.17.0 dependency. The blanket directory-bucket conditional-PUT restriction is not retained; qualify the exact client and operation.
- Basis: [Mr. Boxington evidence](../evidence/mr-boxington-vs-sccache.md), [Kache source status](../reference/vendor-ci-cache-sources.md#kache-not-tested), and [versioned source refresh](../reference/compiler-cache-implementation.md#release-refresh-2026-09-06). No new workload benchmark or cloud deployment was performed for this integration.

### Documentation scope — Separate open-source implementation from broad research coverage

- Changed: 2026-09-06.
- Prior scope: The archive centered its practical guidance on an existing RunsOn deployment without an explicit source-availability boundary for each component.
- Current scope: Future practical implementation targets open-source components used directly in GitHub Actions. Provider-dependent/closed-service, other-platform, and unstable-feature documentation remains in the research/reference coverage. Existing measured conclusions retain their original RunsOn context; public action/template code does not establish an entirely open-source server/agent stack.
- Basis: Maintainer scope clarification, the [documentation scope](../README.md#scope-and-applicability), and the [RunsOn implementation boundary](../providers/runs-on.md#implementation-boundary). No existing benchmark or implementation was reclassified as newly tested.

### D4, D8, and D11 — Distinguish managed EBS storage and nightly content freshness

- Changed: 2026-09-06.
- Prior wording: The generic EBS approach was labeled archived without an explicit managed-sticky route. Sticky unavailability and readiness timeout were grouped as setup failures. Checksum freshness had a short `-Z` reference without the new content-fingerprint configuration or a dedicated status record.
- Current interpretation: D4 refers to the measured custom snapshot implementation; D8 separately tracks managed EBS sticky disks. The [v2.3.1 source contract](../reference/runson-cache-and-disk-details.md#sticky-disk-failure-boundary) distinguishes explicit unavailable-marker cold fallback from missing configuration, invalid mounts, and deadline errors, despite broader failure wording in the capability docs. D11 keeps Cargo's content-fingerprint work on the nightly watchlist after the September 3 call for testing, with build-script mtimes still a limitation.
- Basis: [RunsOn sticky disks](https://runs-on.com/docs/runners/capabilities/sticky-disks/), the pinned action sources linked in the contract, and [Cargo's tracking issue](https://github.com/rust-lang/cargo/issues/14136). This is documentation/source clarification; no new cache engine, provider deployment, or nightly benchmark was run.

<!--
Template for future entries:

### D# — Short title

- Changed: YYYY-MM-DD
- Prior conclusion: ...
- New conclusion: ...
- Reason: ... (link to docs/evidence/... or upstream source)
-->
