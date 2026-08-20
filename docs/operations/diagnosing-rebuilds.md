# Diagnosing Cargo Rebuilds In CI

This page is a triage procedure for when a supposedly cached Cargo build still recompiles crates.

## Related Files

| File | Purpose |
| --- | --- |
| [Diagnostic workflow](../../examples/workflows/cargo-fingerprint-diagnostics.yml) | Captures Cargo fingerprint logs and summarizes fresh/dirty indicators. |

## Enable Fingerprint Diagnostics

Set:

```bash
CARGO_LOG=cargo::core::compiler::fingerprint=trace
```

Then run the same Cargo command used in CI:

```bash
cargo build --workspace --locked -v
```

or for Lambda-style builds:

```bash
cargo lambda build --release --arm64 --bin example
```

## What To Count

Search logs for:

```text
Compiling
Fresh
dirty
fingerprint
stale
```

Useful summary metrics:

- Number of `Compiling` lines.
- Number of `Fresh` lines.
- Number of fingerprint dirty indicators.
- Whether build scripts reran.
- Whether registry sources were re-extracted.

## Common Causes

### Source Mtime Churn

Fresh checkout can rewrite source mtimes, making sources appear newer than restored target artifacts.

Fixes:

- Use a cached worktree checkout.
- Avoid rewriting unchanged files.
- Keep workspace path stable.

### Missing Target Metadata

Cargo needs more than final binaries. It also needs dep-info, fingerprints, build-script state, and unit artifacts.

Fixes:

- If a measured narrow whole-target workload justifies it, use the source-keyed full-target workaround when dependency-oriented target cleanup repeatedly removes required workspace state.
- Avoid cache cleanup that removes workspace target artifacts.

### Build Script Reruns

Build scripts rerun when Cargo sees inputs as changed or when rerun instructions are too broad.

Fixes:

```rust
println!("cargo:rerun-if-changed=build.rs");
println!("cargo:rerun-if-changed=path/to/input");
```

### Registry Source Re-Extraction

If extracted registry sources are missing, Cargo may recreate them from crate archives. This is correct, but source mtimes and path state may differ from previous builds.

Fixes:

- Accept it for dependency-oriented caching.
- Consider the source-keyed target-cache workaround only when the missing state causes material repeated rebuilds and full-archive economics remain acceptable.

### Cache Key Does Not Include Source State

If a target cache key ignores workspace source contents, a cache can restore stale workspace artifacts repeatedly.

Fixes:

- Use a source-keyed target cache only as the narrow workaround described in the [approach page](../approaches/rust-cache-source-keyed-target-cache.md).
- Ask cache action maintainers for source-keyed target-cache support.

## Triage Checklist

1. Confirm the same workspace path is used across runs.
2. Confirm unchanged source files keep old mtimes.
3. Confirm `target/**/.fingerprint` exists after restore.
4. Confirm `target/**/deps/*.d` dep-info files exist after restore.
5. Confirm build-script `target/**/build/**` state exists after restore.
6. Confirm Cargo config and registry credentials are present before cache post steps that run `cargo metadata`.
7. Confirm no later cache restore/cleanup overwrites or removes target state before the build.
