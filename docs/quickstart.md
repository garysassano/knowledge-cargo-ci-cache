# Quickstart

Use this page when you want the current answer without reading the full archive.

## Recommended Default

For GitHub Actions Rust builds, start with:

- A clean local `target/`.
- RunsOn Magic Cache with input-only `Swatinem/rust-cache` as the pragmatic default when RunsOn is available.
- No Rust cache as the paired control.
- `CARGO_INCREMENTAL=0` for a later `sccache` comparison.
- `mise-action` when repeated Rust, Zig, or helper-tool setup is material.

This shape is low-risk because it keeps tool setup and dependency downloads reusable without persisting mutable target state. Prefer no Rust cache when input-only setup is effectively tied with normal dependency downloads. For frequently changing PR workloads, canary S3-backed `sccache` in default server mode without a separate Cargo-input archive by default; add that archive only when dependency-download timing justifies it. The canonical decision record is [Decisions](decisions/README.md).

## Copy The Right Shape

| Need | Use |
| --- | --- |
| Clean RunsOn target with optional Cargo-input cache | [RunsOn Deployment Map](deployments/runs-on/README.md) and [`runs-on-mise-rust-cache.yml`](../examples/workflows/runs-on-mise-rust-cache.yml) |
| Direct S3 compiler-cache canary | [S3-Backed `sccache`](approaches/sccache.md) and [`runs-on-sccache-canary.yml`](../examples/workflows/runs-on-sccache-canary.yml) |
| RunsOn sticky-input or sticky-target canary after v3.2 | [Sticky-Disk Options](deployments/runs-on/README.md#sticky-disk-options) |
| Conditional whole-target archive | [`Swatinem/rust-cache` with mtime-preserving checkout](approaches/rust-cache-mtime-checkout.md) and [`rust-cache-mtime-checkout.yml`](../examples/workflows/rust-cache-mtime-checkout.yml) |
| Tool setup with Rust, Zig, `cargo-lambda`, or Trunk | [Mise Tool Setup](operations/mise-tool-setup.md) |
| Phase-level cache and runner comparison | [Measuring Cache Performance](operations/measuring-cache-performance.md) |
| Rebuild diagnosis | [Diagnosing Cargo Rebuilds In CI](operations/diagnosing-rebuilds.md) |

## When To Escalate

Use a whole-target archive only when a narrow stable workload has exact source/build lineage, one trusted writer, no broad target fallback, and a small monitored archive whose restore/save is cheaper than recompilation.

After RunsOn v3.2, test sticky Cargo inputs before a custom sticky target. Keep EBS/filesystem snapshots as the highest-fidelity archived alternative when lifecycle complexity is acceptable. Do not use S3 Files for Cargo target no-op state based on this archive's experiments.

## Mental Model

Cargo can skip compilation only when source inputs, source mtimes, workspace paths, target artifacts, dep-info, fingerprints, build-script outputs, dependency source paths, toolchain, flags, profile, features, and relevant environment agree with each other.

The short explanation is [Cargo Freshness Model](concepts/cargo-freshness-model.md). The detailed signal table is [Cargo Freshness Signals](reference/cargo-freshness-signals.md).
