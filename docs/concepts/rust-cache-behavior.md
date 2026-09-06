# `Swatinem/rust-cache` Behavior

This page documents the released `Swatinem/rust-cache@v2` behavior that matters to the approaches in this archive. It is not a replacement for the upstream input reference; it explains how selected inputs affect restored and saved Cargo state. The current-version notes were checked on August 20, 2026, when `@v2` resolved to v2.9.2. The exact-hit and cleanup-error paths described below were rechecked against v2.9.2 on September 6, 2026.

## Restore And Save Are Different

`Swatinem/rust-cache` restores the configured Cargo home and target cache paths, but it does not save an untouched copy of them. Before saving, it cleans the registry, Git cache, Cargo binaries, and target directories.

For target profiles, the current `v2` cleanup removes profile-root files and keeps package-matching entries under:

```text
target/<profile>/build/
target/<profile>/.fingerprint/
target/<profile>/deps/
```

This is dependency-oriented caching, not a complete target snapshot.

## Exact And Fallback Key Lifecycle

The action builds:

```text
restore key = prefix, optional shared/job key, OS/architecture, Rust/environment hash
exact key   = restore key with a Cargo manifest/lock/config hash suffix
```

On an exact miss, the cache backend may restore the newest object matching the broader restore key. A lockfile or manifest change can therefore produce:

```text
exact key changes
restore key remains the same
older target archive is restored
Cargo adds artifacts for the new graph/configuration
the complete combined archive is saved under the new exact key
```

This copy-forward behavior is useful when the old target is a compact incremental starting point. It is dangerous when old hashed artifact generations remain and the complete archive grows faster than cleanup removes them.

To prevent fallback across a boundary, include that boundary in `shared-key` or `prefix-key`, because those inputs participate in the restore key. Putting identity only in files that contribute to the exact suffix does not stop fallback.

## Relevant Inputs

| Input | Default | `false` | `true` |
| --- | --- | --- | --- |
| [`cache-all-crates`](https://github.com/Swatinem/rust-cache/blob/v2/action.yml#L39-L42) | `false` | Clean the Cargo registry down to crates selected from the current workspace dependency graph. | Skip registry crate archive and extracted-source cleanup, retaining crates beyond the current dependency graph. |
| [`cache-bin`](https://github.com/Swatinem/rust-cache/blob/v2/action.yml#L55-L58) | `true` | Do not add `$CARGO_HOME/bin` and Cargo's installed-crate metadata files to the cache paths. | Cache binaries tracked by Cargo's installed-crate metadata, subject to binary cleanup before save. |
| [`cache-targets`](https://github.com/Swatinem/rust-cache/blob/v2/action.yml#L32-L35) | `true` | Cache Cargo home state without configured workspace target directories. | Add configured target directories to the cache paths; clean them before save. |
| [`cache-workspace-crates`](https://github.com/Swatinem/rust-cache/blob/v2/action.yml#L43-L46) | `false` | Exclude workspace members from the target-cleanup allowlist; retain dependency package artifacts. | Add workspace members to the allowlist so matching workspace target artifacts also survive cleanup. |

`cache-all-crates` affects Cargo registry cleanup. `cache-workspace-crates` affects target artifact cleanup. They do not enable the same behavior.

## `cache-workspace-crates` Example

Suppose the repository is:

```text
app/
├── Cargo.toml          # workspace members: app and crates/common
├── src/
└── crates/
    └── common/
        ├── Cargo.toml
        └── src/
```

The application depends on a local library and a registry crate:

```toml
[dependencies]
common = { path = "crates/common" }
serde = "1"
```

Cargo normally makes an [in-tree path dependency a workspace member](https://doc.rust-lang.org/cargo/reference/workspaces.html#the-members-and-exclude-fields), so `crates/common` is a workspace crate in this example.

With the default `cache-workspace-crates: false`:

```text
serde and other dependencies:
  matching target artifacts are retained

app and crates/common workspace members:
  matching target artifacts are removed during save cleanup
```

With `cache-workspace-crates: true`:

```text
serde and other dependencies:
  matching target artifacts are retained

app and crates/common workspace members:
  matching target artifacts are also retained
```

The flag follows workspace membership, not `path = ...` by itself:

- A path dependency inside the workspace normally becomes a member and is covered when the flag is `true`.
- A path dependency outside the workspace root is already treated as a dependency and does not need this flag.
- A path crate explicitly excluded from the workspace is not covered merely because its dependency uses `path = ...`.

For retained packages, `v2` keeps matching entries under profile `build/`, `.fingerprint/`, and `deps/` for package names and library/proc-macro target names. It does not preserve the entire target tree or profile-root binaries.

## Choosing Values

For the recommended clean-target input-only baseline:

```yaml
cache-targets: false
cache-bin: false
```

This caches Cargo registry and Git inputs without storing compiler output. It does not need source-mtime preservation because the target starts clean.

For a conditional whole-target archive:

```yaml
cache-targets: true
cache-workspace-crates: true
```

These two inputs describe the broader Cargo state that approach intends to reuse:

- Keep `cache-targets: true` because the approach needs target metadata and artifacts in addition to stable source mtimes. It is already the default, but writing it explicitly makes the architecture clear.
- Use `cache-workspace-crates: true` when repeated-run reuse of workspace library artifacts is desired.
- Put source/build identity in the restore lineage and monitor archive bytes, file count, restore time, and save time.

Choose the remaining inputs from the other steps in the workflow:

- Keep `cache-all-crates` at `false` unless the workflow downloads registry crates outside the workspace dependency graph, such as a tool compiled through `cargo install` or an install action's source-build fallback.
- Keep the `cache-bin: true` default when the workflow has Cargo-registered installed tools to preserve. Set it to `false` when it does not.

These decisions are independent of the `actions/cache` backend. GitHub's hosted cache service, RunsOn Magic Cache, and another compatible backend do not change what `rust-cache` selects or removes.

These options do not guarantee a complete or current target snapshot. In v2.9.2, the post step returns as soon as it detects an exact cache hit, before package selection or cleanup. It therefore neither prunes the restored state nor replaces the exact-hit object with target state produced during the job. The target key also does not include all workspace source contents, so stale workspace artifacts can be repeatedly restored; use the source-keyed target-cache workaround only when that is measurable and the resulting full archive remains bounded.

One v2.9.2 implementation detail matters for input-only mode: on an eligible save after a miss or partial restore, the post step still calls target cleanup for each configured workspace even when `cache-targets: false`. The target path is omitted from the saved archive, but traversal can still occur. `save-if: false` and exact hits skip the post-save path. Measure this residual work and use no Rust cache or an explicit Cargo-home-only cache if it is material.

On an eligible save, v2.9.2 catches top-level target, registry, binary, and Cargo Git cleanup errors, emits their stacks only through debug logging, and continues to save. Without debug logging, a cleanup failure can therefore be hard to distinguish from a successful pass that removed nothing. When bounded size matters, verify before/after bytes and file counts instead of treating the absence of a warning as proof that cleanup succeeded.

## Cleanup Is Not A Size Bound

The target cleanup performs useful work:

- Removes profile-root files.
- Retains package-matching entries under `build`, `.fingerprint`, and `deps`.
- Removes packages no longer present in the selected dependency graph.
- Disables and removes incremental state.

It does not:

- Enforce a byte or file-count budget.
- Keep only one artifact generation per package.
- Determine which hash matches the currently active version, features, compiler flags, or fingerprint.
- Replace an exact hit with target state rebuilt during the job.
- Prevent a partial restore from being copied into the next immutable object.

In one production lineage, the compressed archive grew from about 206 MB to 13.89 GB in under five days. See [Target Archive Growth In Production](../evidence/target-archive-growth.md).

Upstream [PR #377](https://github.com/Swatinem/rust-cache/pull/377) corrects the partial-restore age sweep so it checks every immediate entry rather than stopping after the first. As of August 20, 2026 it is merged on the upstream default branch but is not in v2.9.2 or the `v2` tag. The change retains the existing one-week threshold and does not add recursive generation-aware pruning or a size limit; the observed growth completed inside that one-week window.

## Tool Example: taiki-e Prebuilt Tools

`taiki-e/install-action` officially supports tools including `cargo-lambda` and `trunk` through prebuilt GitHub Release archives. It installs tools backed by Rust crates under `$CARGO_HOME/bin` only when the active `cargo` executable also comes from that directory. Otherwise it falls back to `$HOME/.install-action/bin`.

`cache-all-crates` is unrelated to these executables: it controls registry crate cleanup, not `$CARGO_HOME/bin`.

`cache-bin: true` also does not make these taiki-installed executables reusable through `rust-cache`. If an executable is placed in `$CARGO_HOME/bin`, `rust-cache` removes it during save because taiki's release extraction does not register it in Cargo's `.crates2.json` installation metadata. If taiki uses its fallback directory, that path is outside the `rust-cache` Cargo-home paths entirely.

Use explicit `cache-bin: true` when the workflow installs tools through `cargo install` or another path that updates Cargo's installation metadata. It is not useful for caching the normal taiki-e release installation of these tools.

`cache-all-crates: true` becomes relevant only if installation falls back to compiling the tool from registry sources and the workflow wants to retain all of those downloaded crate archives and sources.

The install action also does not currently skip a supported tool when a matching executable is already present. Its upstream idempotent-install issue remains open, and the maintainer states that the existing check applies only to `cargo-binstall` itself. Supported `cargo-lambda` and `trunk` versions proceed through the release download and extraction path.

Official implementation references:

- [Supported tools](https://github.com/taiki-e/install-action/blob/main/TOOLS.md)
- [`cargo-lambda` release manifest](https://github.com/taiki-e/install-action/blob/main/manifests/cargo-lambda.json)
- [`trunk` release manifest](https://github.com/taiki-e/install-action/blob/main/manifests/trunk.json)
- [Supported-tool download path](https://github.com/taiki-e/install-action/blob/7a79fe8c3a13344501c80d99cae481c1c9085912/main.sh#L946-L992)
- [Cargo binary directory selection](https://github.com/taiki-e/install-action/blob/7a79fe8c3a13344501c80d99cae481c1c9085912/main.sh#L616-L639)
- [Open idempotent-install request](https://github.com/taiki-e/install-action/issues/577)
- [`cache-bin` input](https://github.com/Swatinem/rust-cache/blob/v2/action.yml#L55-L58)
- [`cache-bin` path selection](https://github.com/Swatinem/rust-cache/blob/v2/src/config.ts#L272-L280)
- [`cache-bin` save cleanup](https://github.com/Swatinem/rust-cache/blob/v2/src/cleanup.ts#L77-L111)

## Upstream Implementation

The behavior above follows the upstream `v2` implementation:

- [Input definitions](https://github.com/Swatinem/rust-cache/blob/v2/action.yml#L32-L46)
- [Cache-path selection](https://github.com/Swatinem/rust-cache/blob/v2/src/config.ts#L272-L289)
- [Save-time package selection](https://github.com/Swatinem/rust-cache/blob/v2/src/save.ts#L39-L60)
- [Workspace target selection](https://github.com/Swatinem/rust-cache/blob/v2/src/workspace.ts#L6-L38)
- [Target cleanup](https://github.com/Swatinem/rust-cache/blob/v2/src/cleanup.ts#L35-L75)
- [Exact-hit early return and cleanup-error handling](https://github.com/Swatinem/rust-cache/blob/v2.9.2/src/save.ts#L24-L84)
