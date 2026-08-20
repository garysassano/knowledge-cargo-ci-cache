# Cached Worktree And Source-Keyed Target Cache Evidence

This page records the experiments that led from normal checkout behavior to the selected mtime-preserving worktree approach and the source-keyed full-target workaround.

## Question

Why did local workspace crates rebuild after an apparently successful cache restore, and which cache composition made the remaining generated-code and build-script outliers fully fresh?

## Test Progression

### Normal Checkout

Normal GitHub Actions checkout rewrote source mtimes. Cargo then saw local source files as newer than restored target fingerprints and rebuilt workspace crates.

### Cached Worktree

The custom checkout restored a cached Git worktree, skipped checkout when `HEAD` already matched `GITHUB_SHA`, and otherwise checked out the new commit in place. Git rewrote changed files while unchanged files retained their previous mtimes.

This removed the primary false invalidation and showed that the then-current whole-target approach could produce a Cargo no-op. Most matrix jobs completed around 33 to 37 seconds, and a representative no-op Cargo step completed around 0.31 seconds. Local path workspace members in generated-code and build-script chains remained as 50 to 65 second outliers.

### Exact `rust-cache` Hit

The remaining cycle was:

```text
restore exact target cache whose key omits workspace source contents
Cargo rebuilds affected workspace crates
rust-cache post step reports Cache up-to-date
rebuilt target state is not saved
next run restores the same stale exact target cache
```

Adding narrower `cargo:rerun-if-changed` hints was good build-script hygiene but did not solve this cache-key and save behavior.

### Source-Keyed Full Target Cache

The proven workaround split responsibility:

```text
rust-cache restores Cargo home only
actions/cache restores the full target directory after rust-cache
target key includes tracked source state and a build-semantics namespace
Cargo builds with an explicit per-job CARGO_TARGET_DIR
```

Restoring the full target cache before `rust-cache` did not work because `rust-cache` cleanup could remove workspace artifacts. Restoring it after `rust-cache` preserved the full target state for Cargo.

## Observations

Previously slow generated-code and build-script dependency chains became no-op:

| Job type | Cargo result |
| --- | --- |
| Generated-code job A | `Finished ... in 0.26s`, no `Compiling` lines |
| Generated-code job B | `Finished ... in 0.24s`, no `Compiling` lines |
| Generated-code job C | `Finished ... in 0.31s`, no `Compiling` lines |

All tested matrix jobs completed around 34 to 37 seconds in the final workaround verification.

For Trunk jobs, remaining repeated-run time came mostly from the Trunk pipeline itself, including the pre-build hook, helper tool downloads or installation, wasm processing, and dist application, rather than missing Cargo target artifacts. This supports treating frontend helper tools as setup state separate from Cargo freshness state.

## Native `rust-cache` Prototype

A local `rust-cache` prototype added a `target-key` input and split Cargo-home and target caches internally. After one seed run, repeated runs restored exact Cargo-home and target-cache hits across all tested binary and UI jobs. Cargo emitted no `Compiling` lines, and the remaining build phases were around 0.3 seconds.

Introducing `--locked` against an older source-only target key caused some workspace rebuilds. Prefixing the target key with a new namespace such as `locked-v1-` created a fresh lineage; the next warm run returned to no-op behavior.

`--frozen` and `--offline` failed with the `rust-cache`-managed Cargo home because those modes require complete local registry/index state while `rust-cache` intentionally prunes Cargo home.

## Interpretation

- Stable source mtimes remove one major source of false invalidation.
- They do not solve immutable exact target-cache hits whose keys omit workspace source and build semantics.
- A source-keyed full-target cache solves the affected local path workspace-member outliers when restored after `rust-cache`.
- A native split-cache `target-key` design is viable, but the copyable external workaround remains necessary until equivalent upstream support exists.

## Limitations

- The timings come from the recorded matrix workload and are not universal performance guarantees.
- The fast Git source key invalidates all per-job target caches for any tracked change under the selected source tree.
- The native `target-key` result came from a local prototype, not a released upstream `Swatinem/rust-cache` interface.

## Implications

- Preserve source mtimes when a target/fingerprint cache is being evaluated; a clean-target design does not require this extra source cache.
- Treat the source-keyed full-target cache as a freshness workaround, not proof that the archive is economical or size-bounded.
- Use an exact source/build-state restore lineage rather than a broad fallback that can copy an older complete target tree forward.
- Add the workaround only when affected local path workspace members repeatedly rebuild, repeated identical-source runs matter, and the complete archive remains small.
- Keep the external workaround until upstream `rust-cache` exposes equivalent source-keyed target caching.
- Compare it against the [clean-target](../approaches/clean-target.md) and [`sccache`](../approaches/sccache.md) approaches using end-to-end measurements.

## Related Guidance

- [Conditional mtime-preserving whole-target approach](../approaches/rust-cache-mtime-checkout.md)
- [Source-keyed target-cache workaround](../approaches/rust-cache-source-keyed-target-cache.md)
- [`rust-cache` behavior](../concepts/rust-cache-behavior.md)
