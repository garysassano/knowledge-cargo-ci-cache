# Kache

**Status: not tested.** This archive has not installed, validated, benchmarked, or adopted [kunobi-ninja/kache](https://github.com/kunobi-ninja/kache). This profile owns its candidate description and source links. Use the [three-tool comparison](compiler-caches.md) for selection and [D10](../decisions/README.md) for adoption status.

## Upstream design

Reviewed on 2026-09-06 against the [v0.16.0 release](https://github.com/kunobi-ninja/kache/releases/tag/v0.16.0), its [pinned README](https://github.com/kunobi-ninja/kache/blob/v0.16.0/README.md), and the live guides below. The pinned README describes Rust compiler caching through `RUSTC_WRAPPER=kache`, local C/C++ object caching, and Rust artifact sharing through S3-compatible or shared-filesystem stores. C/C++ remote sharing is not included in that release's stated coverage.

Local restores prefer reflinks where available, a restricted single hardlink consumer on Unix where safe, and private copies otherwise; Windows copies by default. Treat “zero-copy” as filesystem- and artifact-dependent. The optional daemon handles remote work; explicit `kache sync` can transfer artifacts without it. The separately described hosted planner is a preview, not a prerequisite for local caching.

The [upstream comparison](https://kunobi.ninja/docs/kache/getting-started/comparison) discusses output/platform support, incremental policy, and differences from sccache. Recheck these against the selected release before testing executables, proc macros, cross compilation, or build scripts. Caching a build-script compiler invocation does not prove that executing `build.rs` is reusable.

## CI and remote storage

| Source                                                                                                                       | What to verify                                                                                              |
| ---------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| [Repository README](https://github.com/kunobi-ninja/kache#readme)                                                            | Current commands, supported compiler shapes, storage model, and upstream benchmark methodology.             |
| [CI guide](https://kunobi.ninja/docs/kache/remote-cache/ci) and [Kache action](https://github.com/kunobi-ninja/kache-action) | Wrapper installation, cache persistence, synchronization, and job lifecycle. No workflow is qualified here. |
| [S3 setup](https://kunobi.ninja/docs/kache/remote-cache/s3-setup)                                                            | Endpoint, namespace, authentication, read/write permissions, and publication semantics.                     |
| [Filesystem remotes](https://kunobi.ninja/docs/kache/remote-cache/filesystem-setup)                                          | Sharing boundaries, concurrency, atomicity, and cleanup on the selected filesystem.                         |

The live CI guide describes protected-branch push restrictions on remote writes and read-only behavior for other CI events. That is application policy: credentials supplied to untrusted job code still need storage-enforced restrictions. Its private per-job runtime directory is separate from any shared local cache store. Measure prefetch and synchronization rather than assuming they help a persistent runner.

## Qualification before adoption

Apply the [common compiler-cache comparison procedure](compiler-caches.md#how-to-compare-fairly). Include path changes across fresh runners, the exact Rust and native output classes the project uses, unsupported-call fallback, local store growth, concurrent consumers, and remote publication after failure or cancellation. Check outputs against the same no-cache build before considering speed.

There are no Kache measurements in [Evidence](../evidence/README.md). The source review is sufficient to retain it as a candidate, not to choose it over sccache or Mr. Boxington.
