# Mise Tool Setup

Use `jdx/mise-action` as the preferred CI setup layer for Rust-adjacent tools and runtimes, especially on RunsOn runners with Magic Cache enabled.

This is not a Cargo cache approach. Let Cargo caches handle Cargo home and target freshness; let mise handle repeated tool installation.

## Recommended Shape

Use inline `mise_toml` in the workflow when the tool set is CI-specific:

```yaml
env:
  MISE_DATA_DIR: ${{ github.workspace }}/.mise
  MISE_RUSTUP_HOME: ${{ github.workspace }}/.mise/rustup

steps:
  - name: Setup Toolchain And Tools
    uses: jdx/mise-action@v4
    with:
      cache: true
      mise_toml: |
        [tools]
        zig = "0.16.0"
        rust = { version = "stable", components = "rustfmt", targets = "aarch64-unknown-linux-gnu" }
        cargo-binstall = "latest"
        "cargo:cargo-lambda" = "1.9.1"
```

For Trunk/WebAssembly jobs, keep the same env vars and swap the tool block:

```toml
[tools]
rust = { version = "stable", components = "rustfmt", targets = "wasm32-unknown-unknown" }
cargo-binstall = "latest"
"cargo:trunk" = "0.21.14"
```

Pin artifact build tools such as Zig, `cargo-lambda`, and Trunk. Use `rust = "stable"` unless the repository declares a Rust version in `rust-toolchain.toml` or `workspace.package.rust-version`. Keeping `cargo-binstall = "latest"` is acceptable because it is the installer mechanism for Cargo-backed tools.

## Environment Rules

| Setting | Rule |
| --- | --- |
| `MISE_DATA_DIR` | Set it to a stable job-local path such as `${{ github.workspace }}/.mise`. |
| `MISE_RUSTUP_HOME` | Put it under `MISE_DATA_DIR` so mise-managed Rust toolchains and targets are cached with the mise tree. |
| `MISE_OVERRIDE_CONFIG_FILENAMES` | Use it only when build steps run outside `$GITHUB_WORKSPACE` and cannot discover the inline `mise_toml`. |
| `CARGO_HOME` | Do not put it under the mise cache when registry credentials are written there; let `rust-cache` own Cargo home. |

Keep build worktrees under `$GITHUB_WORKSPACE` when possible, for example `$GITHUB_WORKSPACE/cached-worktree/app`. That lets mise discover `$GITHUB_WORKSPACE/mise.toml` naturally and avoids shim/config visibility failures.

## Ordering

Run setup in this order:

1. Restore/check out the workspace using the repository's mtime-preserving strategy.
2. Configure private registry credentials when required.
3. Run `mise-action` for toolchains and setup tools.
4. Restore `rust-cache` or target caches.
5. Run Cargo builds with explicit `CARGO_TARGET_DIR`.

`mise-action` should happen before `rust-cache` so `rust-cache` sees the Rust environment that the build will use.

## Target-Key Rule

Changing setup tooling can change Cargo's build semantics even when application source does not change. If using a source-keyed target cache, bump the target-key namespace after changing any of these:

- Rust home/toolchain location.
- Rust targets.
- Build flags such as `--locked` vs `--frozen`.
- Target triples.
- Profiles or features.
- Tool wrappers or setup backend, such as switching from `dtolnay/rust-toolchain` and installer actions to mise.
- Moving `MISE_DATA_DIR`, `MISE_RUSTUP_HOME`, cached worktrees, or cached target directories.

Example:

```yaml
target-key: mise-locked-v2-${{ steps.target-key.outputs.hash }}
```

The computed target hash should include source state and the resolved `rustc -Vv` identity as shown in the [source-keyed target-cache approach](../approaches/rust-cache-source-keyed-target-cache.md). The first run after a namespace bump should seed the new target cache. The immediate follow-up run is the one that should prove warm no-op behavior.

## What This Does Not Solve

Mise setup caching makes tool installation fast. It does not by itself prove Cargo units fresh. Cargo no-op behavior still depends on source mtimes, target fingerprints, dep-info files, build-script outputs, registry source paths, and consistent build semantics.

Keep using the selected Cargo cache approach. If a measured narrow workload still justifies whole-target caching, use a source-keyed target cache only when affected local path workspace members repeatedly rebuild and justify the extra cache composition.

## Details

The detailed cache-path behavior, inline config discovery rules, historical shim failure, data-flow diagram, and upstream links are preserved in [Mise Tool Setup Details](../reference/mise-tool-setup-details.md).
