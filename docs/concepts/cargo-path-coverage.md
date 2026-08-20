# Cargo Path Coverage

This page lists the Cargo paths that matter between builds and how the major CI cache approaches cover them. The key question is not only whether a file exists after restore, but whether Cargo can use the restored state to prove a build unit is fresh.

## Restore Coverage

| Path | Purpose | `Swatinem/rust-cache` | EBS snapshot / filesystem restore |
| --- | --- | ---: | ---: |
| `<workspace>/Cargo.toml` | Package graph, targets, dependency declarations | Hashed into key only | Covered if workspace is under snapshot root |
| `<workspace>/Cargo.lock` | Exact dependency graph | Hashed into key only | Covered if workspace is under snapshot root |
| `<workspace>/.cargo/config.toml` | Registry, flags, target config | Hashed into key if found | Covered if workspace is under snapshot root |
| `<workspace>/**/src/*.rs` | Source inputs | Recreated by checkout | Covered if workspace is under snapshot root |
| `<workspace>/**/build.rs` | Build script source | Recreated by checkout | Covered if workspace is under snapshot root |
| Generated workspace files | Source/codegen inputs | Recreated by checkout or build | Covered if under snapshot root |
| `$CARGO_HOME/registry/cache` | Compressed crate archives | Covered | Covered if `CARGO_HOME` is under snapshot root |
| `$CARGO_HOME/registry/src` | Extracted dependency sources | Usually recreated or partially preserved | Covered if `CARGO_HOME` is under snapshot root |
| `$CARGO_HOME/registry/index` | Registry metadata | Covered and cleaned | Covered if `CARGO_HOME` is under snapshot root |
| `$CARGO_HOME/git/db` | Git dependency bare repos | Covered and cleaned | Covered if `CARGO_HOME` is under snapshot root |
| `$CARGO_HOME/git/checkouts` | Git dependency source trees | Covered and cleaned for used refs | Covered if `CARGO_HOME` is under snapshot root |
| `$CARGO_HOME/bin` | Cargo-installed binaries | Covered if `cache-bin=true` and represented in Cargo's installed-crate metadata; directly extracted binaries are removed during save cleanup | Covered if `CARGO_HOME` is under snapshot root |
| `$XDG_CACHE_HOME/cargo-zigbuild` | Cargo helper cache/state | Not covered unless separately cached | Covered if `XDG_CACHE_HOME` is under snapshot root |
| Trunk tool cache, for example `$XDG_CACHE_HOME/dev.trunkrs.trunk` | Trunk-managed helper binaries such as `wasm-bindgen`, `wasm-opt`, and `tailwindcss` | Not covered unless separately cached | Covered if under snapshot root |
| `target/<profile>/deps/*.rlib` | Compiled library artifacts | Dependency-oriented; workspace artifacts require `cache-workspace-crates` and still follow `rust-cache` key behavior | Covered |
| `target/<profile>/deps/*.rmeta` | Rust metadata for downstream crates | Dependency-oriented | Covered |
| `target/<profile>/deps/*.d` | Dep-info freshness/input tracking | Dependency-oriented | Covered |
| `target/<profile>/.fingerprint/**` | Cargo unit freshness metadata | Dependency-oriented | Covered |
| `target/<profile>/build/**` | Build script outputs and `OUT_DIR` state | Dependency-oriented | Covered |
| `target/<profile>/incremental/**` | rustc incremental recompilation state | Disabled and cleaned by `rust-cache` | Covered if enabled and under snapshot root |
| `target/<profile>/<final-binary>` | Final executable output | Workspace final artifacts are usually not the primary target | Covered |
| `target/<target-triple>/<profile>/**` | Cross-compiled artifacts | Dependency-oriented | Covered |
| Non-Cargo tool cache dirs | Setup action cache/tool state | Only if separately cached or added via `cache-directories` | Covered if under snapshot root |

## Save Behavior

`Swatinem/rust-cache` restore and save behavior is intentionally not symmetric. On save, it prunes state before uploading the archive. See [`Swatinem/rust-cache` Behavior](rust-cache-behavior.md) for input defaults, true/false examples, and the exact cleanup rules used by the documented approaches.

Important `rust-cache` save behavior:

```text
keeps dependency-oriented target artifacts
workspace crate artifacts require cache-workspace-crates=true
usually removes most extracted registry/src content
cleans unused dependencies
removes pre-existing cargo bin entries
```

`cache-bin=true` should not be treated as a general setup-tool cache. In the tested workflow it was effectively not useful for `cargo-lambda` or `trunk`, because those commands were installed by `taiki-e/install-action` after `rust-cache` restored and the install step still ran on every job. Binaries that are restored into `$CARGO_HOME/bin` also exist before the `rust-cache` post step computes what changed during the job, so they can be considered pre-existing and removed before the next save. For stable CI helper tools, prefer a custom runner image, the setup action's own cache, or an explicit tool cache. Use `rust-cache` for `$CARGO_HOME/bin` only when that tradeoff is acceptable.

An EBS snapshot preserves the mounted filesystem subtree. If the path is under the snapshot root and was not removed before the post step, it is saved.

## Other Coverage Models

| Approach | `$CARGO_HOME/registry` and Git | `target/` at job start | Compiler-output reuse |
| --- | --- | --- | --- |
| No Rust cache | Downloaded normally | Clean | None |
| Input-only `rust-cache` | Restored and cleaned | Clean | None |
| S3-backed `sccache` with clean target | Optional separate input cache | Clean | Eligible compiler invocations only |
| RunsOn sticky `rust` mode | Native persistent registry and Git paths | Clean unless separately configured | None |
| RunsOn sticky custom target | Optional sticky Cargo inputs | Native persistent target path | Full target state, subject to Cargo freshness and disk lifecycle |

`sccache` does not restore Cargo fingerprints or a ready target tree. It materializes outputs in response to compiler calls while Cargo still traverses and orchestrates the graph.

RunsOn's built-in sticky `rust` mode covers Cargo registry and Git inputs only. Persisting `target/` requires a custom sticky path and makes the sticky disk the sole owner of that target state.

## Choosing Coverage

| State | Preferred coverage | Why |
| --- | --- | --- |
| `target/` | Clean by default; add `sccache` for compiler outputs, or use a tightly bounded exact target archive/sticky target only after measurement | A clean target avoids archive growth. Full target persistence has stronger no-op potential but also carries filesystem growth and freshness state. |
| `$CARGO_HOME/registry`, `$CARGO_HOME/git` | Input-only `rust-cache`, sticky Cargo-input mode, or no cache according to measured setup cost | These paths avoid dependency downloads but do not reuse compilation. |
| `$XDG_CACHE_HOME/cargo-zigbuild` | Explicit `actions/cache` entry if preserving the helper cache is worthwhile | This is Cargo-helper state outside Cargo home and `target/`. |
| Trunk tool cache | Custom AMI, setup-action cache, or explicit `actions/cache` entry | Trunk downloads helper tools outside Cargo target state. Cache these paths separately if their setup time matters. |
| Cargo-installed helper binaries | Custom AMI or setup-action cache preferred | These are setup state, not freshness proof; `rust-cache cache-bin` is limited to Cargo-registered installs and is not a complete tool-cache strategy. |
| Rust toolchain and rustup targets | Custom AMI preferred, otherwise a setup action's cache | Toolchain state is large and stable. |
| Zig compiler install | Custom AMI preferred, otherwise a setup action's cache | Stable tool state. |
| Zig tarball/download cache | `actions/cache` | Immutable download archives fit keyed archive cache semantics. |
| Node/package/deployment dependencies | Ecosystem cache or custom AMI | Outside Cargo freshness. |

The archived EBS snapshot approach covers these paths with greater filesystem continuity, but it is not the selected deployment because of its operational and lifecycle complexity.

## Compatibility Rule (Canonical)

This is the canonical statement of decision [D6](../decisions/README.md). Other pages reference it instead of restating it.

Avoid combining `Swatinem/rust-cache` target management with a sticky/full Cargo build-state owner for the same `target/`, or two mechanisms that both restore and clean the same `$CARGO_HOME` paths. `rust-cache` restores and prunes an archive-oriented subset, while sticky disks and snapshots depend on preserving filesystem continuity. Mixing owners can rewrite files, alter mtimes, reintroduce archive work, and reduce native-state reuse.
