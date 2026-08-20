# Source Mtime Alternatives

This page preserves source-mtime approaches relevant to conditional whole-target reuse, including [`Swatinem/rust-cache` with mtime-preserving checkout](../approaches/rust-cache-mtime-checkout.md). They address checkout mtime churn, but they are not equivalent to the [source-keyed target-cache workaround](../approaches/rust-cache-source-keyed-target-cache.md).

## Comparison

| Approach | What it does | Notes |
| --- | --- | --- |
| [`chetan/git-restore-mtime-action`](https://github.com/chetan/git-restore-mtime-action) | Rewrites checked-out file mtimes from Git history, usually requiring `fetch-depth: 0`. | Can reduce false rebuilds from checkout mtime churn, but uses synthetic commit-time mtimes rather than preserving the previous CI worktree's mtimes. |
| [Retimer-style cached mtime state](https://gist.github.com/tmm1/0ec42a8a12bf78ece7a43ec6204cbdc3) | Saves prior source mtimes and restores them before running Cargo when file contents still match. | Closer to the cached-worktree idea, but adds another state file/cache to maintain and did not eliminate every rebuild in the linked report. |
| [Cargo checksum freshness](https://doc.rust-lang.org/nightly/cargo/reference/unstable.html#checksum-freshness) | Nightly Cargo's `-Z checksum-freshness` replaces file mtimes in Cargo fingerprints with checksums. | Promising for CI source checkout churn, but still unstable; build-script-ingested files continue to use mtimes. |

These alternatives mainly target source mtime churn. They do not fix `rust-cache` exact-hit behavior where stale workspace target state is restored and not saved again because the target cache key ignores workspace source contents.

## Retimer Primary Report

In a [June 29, 2025 comment on `Swatinem/rust-cache#155`](https://github.com/Swatinem/rust-cache/issues/155#issuecomment-3016173641), `tmm1` showed a workflow that cached `target/` and `.retimer-state`, restored matching source mtimes before `cargo build`, and saved them afterward. The workflow was intended to correct source-mtime invalidation but did not make the final crate fresh:

> However, I still observe the final project is always rebuilt (90s+ in my case), even if none of the code has changed.

Cargo reported the remaining rebuild as `stale, unknown reason`.

The linked [`retimer.sh` revision](https://gist.github.com/tmm1/0ec42a8a12bf78ece7a43ec6204cbdc3/272b22ecbd6d65971d7cc0b3667ce4f6794c0516) stores each Rust source path, SHA-256 digest, and mtime in `.retimer-state`. During restore, it reapplies an mtime only when the current file hash still matches. Its intended sequence is:

```text
restore .retimer-state and target from cache
retimer restore
cargo build
retimer save
save .retimer-state and target for the next run
```

This is useful evidence that correcting source mtimes can remove one class of false invalidation without proving that the entire restored Cargo state is fresh. The script tracks `*.rs` files outside `target/`; Cargo freshness can also depend on manifests, configuration, generated inputs, build-script state, dep-info, fingerprints, paths, toolchain, flags, and environment.

## Cargo Checksum Freshness

The official [Cargo nightly documentation](https://doc.rust-lang.org/nightly/cargo/reference/unstable.html#checksum-freshness) describes `-Z checksum-freshness` as replacing file mtimes in Cargo fingerprints with file checksum values. It is explicitly intended for environments with poor mtime behavior and for CI/CD.

```bash
cargo +nightly -Z checksum-freshness build --locked
```

This directly addresses source files receiving new mtimes during checkout, but it is not yet a drop-in stable replacement for the approaches in this archive:

- It requires nightly Cargo and an unstable `-Z` flag.
- The checksum algorithm may change without notice between Cargo versions, so restored fingerprints should use the same Cargo version.
- Files consumed by build scripts continue to use mtimes for now.
- It changes freshness detection; it does not restore missing artifacts, dep-info, fingerprints, build-script outputs, or other cache state.
- It does not change `rust-cache` target-key or exact-hit save behavior.

Follow the official [tracking issue `cargo#14136`](https://github.com/rust-lang/cargo/issues/14136) for stabilization and build-script coverage. The original implementation is [`cargo#14137`](https://github.com/rust-lang/cargo/pull/14137).
