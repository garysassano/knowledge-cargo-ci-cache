# Maintenance Checklist

Use this checklist when refreshing the archive or copying its examples into a live repository.

## Decisions

- When a conclusion in [`docs/decisions/README.md`](../decisions/README.md) changes, append the prior conclusion to [`docs/decisions/history.md`](../decisions/history.md) before overwriting it, including what changed and the evidence or upstream change that prompted it.
- After updating a decision, update the brief summaries that link to it: the root `README.md`, `docs/quickstart.md`, `AGENTS.md`, and any approach page status field.

## Example Versions

- Check current GitHub-owned action majors for `actions/checkout`, `actions/cache`, `actions/upload-artifact`, and `actions/download-artifact`.
- Keep non-GitHub actions intentionally pinned or floating by policy. For example, this archive keeps `Swatinem/rust-cache@v2` and `dtolnay/rust-toolchain@stable` because those are the intended upstream interfaces.
- Re-check the released `runs-on/action@v2` metadata, `Mozilla-Actions/sccache-action`, and the selected `sccache` binary version before changing the compiler-cache or sticky-disk examples.
- Re-check `jdx/mise-action` inputs and cache-key behavior when changing mise setup examples.
- Re-check where inline `mise_toml` is written and where later build steps run; config discovery is path-sensitive.
- Run `actionlint examples/workflows/*.yml` when `actionlint` is available.
- Parse all example YAML files after edits.

## Cargo Cache Semantics

- Re-check `Swatinem/rust-cache` release notes before changing the recommendation, especially around target keys, `cache-workspace-crates`, incremental state, and save cleanup behavior.
- Re-check whether the input-only post step still traverses configured target directories on an eligible save even though `cache-targets: false` excludes them from the archive.
- Re-check the official [Cargo checksum freshness documentation](https://doc.rust-lang.org/nightly/cargo/reference/unstable.html#checksum-freshness) and [tracking issue](https://github.com/rust-lang/cargo/issues/14136) before changing source-mtime guidance.
- Keep the source-keyed target-cache workaround documented until upstream target keys include workspace source state or an equivalent mechanism exists.
- When using source-keyed target caches, hash source state with the resolved `rustc -Vv` identity, include a manual namespace for remaining build-command semantics, for example `locked-v1-<source-and-compiler-hash>`, and bump the namespace after changing build flags, target triples, profiles, features, or wrappers.
- Do not add a source-independent fallback for a full target archive. Use separate restore/save actions when one trusted canonical writer is required.
- Also bump the target-key namespace after changing setup semantics that affect Cargo's environment, such as moving `MISE_DATA_DIR`, `MISE_RUSTUP_HOME`, cached worktrees, cached target directories, switching from Rust/Zig installer actions to mise, or changing Cargo helper installation backends.
- Prefer `--locked` for CI artifact builds. Do not switch to `--frozen` / `--offline` with `rust-cache` unless complete local registry/index state is known to be restored.
- Prefer `mise-action` with inline `mise_toml` for stable setup tools such as Zig, Rust targets, `cargo-lambda`, `trunk`, and `cargo-binstall`; do not rely on `rust-cache cache-bin=true` as the only cache for those tools when setup time matters.
- Prefer a cached source worktree under `$GITHUB_WORKSPACE`, such as `cached-worktree/app`, so mise can discover `$GITHUB_WORKSPACE/mise.toml` without `MISE_OVERRIDE_CONFIG_FILENAMES`.
- Do not add `depends = ["rust", "cargo-binstall"]` to Cargo-backed mise tools as a workaround for shim/config discovery failures. Fix the config path instead.
- Preserve the [canonical compatibility rule](../concepts/cargo-path-coverage.md#compatibility-rule-canonical) against mixing full filesystem snapshots with `rust-cache` on the same `target/` or `$CARGO_HOME` paths.
- For every whole-target archive, record compressed bytes, target bytes, file count, restore/save time, and exact/partial hit state. Save restrictions, larger capacity, shorter retention, and key rotation do not prune the active object.

## Platform Guidance

- Keep RunsOn Magic Cache, direct S3 `sccache`, sticky-disk, support-transition, and current-version checks in [`docs/deployments/runs-on/README.md`](../deployments/runs-on/README.md).
- Verify the RunsOn stack is v3.2.0 or newer before testing sticky disks.
- Set `sticky_wait_timeout` explicitly while the documentation and released action metadata disagree on the default.
- Re-check sticky lineage, default-branch fallback, concurrency, inactive expiry, free-space/inode warnings, automatic reset, and failure/cancellation behavior.
- Treat Magic Cache protocol isolation and direct S3 IAM as separate boundaries. `SCCACHE_S3_RW_MODE=READ_ONLY` is not a substitute for an IAM-enforced read-only runner role.
- Confirm lifecycle and inventory against the actual RunsOn S3 backend; do not assume GitHub cache API commands expose every third-party backend object.
- Keep the RunsOn v3 migration separate from a Rust cache canary, with a parallel-stack test and an explicit rollback path.

## Compiler wrappers and research

- Keep compiler-wrapper candidates, provider documentation, and blog posts in the ecosystem catalog. Preserve source URLs when reorganizing it and label untested products explicitly.
- Record mbx binary, action version, and GitHub payload mode separately. The current action's `target` default is a different mechanism from `objects`; recheck these inputs before reproducing old compiler-object trials.
- Keep same-job reuse separate from fresh-runner restore/export, and do not infer compiler reuse from an exact archive hit.
- Recheck the version of OpenDAL embedded in the tested sccache binary before carrying a fixed upstream limitation forward. Record changed release status in the research baseline and decision history.
- Keep proposed inputs, drain APIs, gateways, readiness/index formats, and storage tiers under research until implemented and qualified. Numeric promotion budgets are proposals, not benchmark results.
- Validate relative Markdown links and heading anchors, JSONL identity/accounting, retained evidence, and example YAML after moving or splitting pages.

## Archived AWS Experiments

- Re-check current S3 Files docs before using the S3 Files page for new experiments.
- Re-check `runs-on/snapshot` inputs and snapshot identity behavior before copying the snapshot example.
- Keep credential scrubbing guidance on any snapshot layout that places `$CARGO_HOME` under the snapshot root.
- Keep snapshot and S3 Files local action examples generic; do not reintroduce app-specific names, secrets, or runner labels.

## Evidence Hygiene

- Keep test setup, observations, measurements, interpretation, and limitations in focused pages under `docs/evidence/`.
- Link approach pages to evidence instead of duplicating result tables and timings.
- Do not maintain a chronological experiment diary; retain only findings that affect a current model, decision, procedure, or evidence record.
- Keep diagnostic procedures in `docs/operations/diagnosing-rebuilds.md`.
