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

<!--
Template for future entries:

### D# — Short title

- Changed: YYYY-MM-DD
- Prior conclusion: ...
- New conclusion: ...
- Reason: ... (link to docs/evidence/... or upstream source)
-->
