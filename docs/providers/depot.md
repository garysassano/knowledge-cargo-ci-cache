# Depot sources and strategy mapping

**Status: upstream descriptions, reviewed 2026-09-06; no local provider benchmark.** Depot's compiler-cache service, container builders, GitHub Actions runners, and Depot CI are distinct surfaces. Verify the product named by a guide before adapting it.

| First-party source                                                                                                                | Strategy and scope                                                                                                        |
| --------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| [sccache integration](https://depot.dev/docs/cache/integrations/sccache)                                                          | Remote compiler-cache service over WebDAV; wrapper and backend configuration still matter.                                |
| [sccache in GitHub Actions](https://depot.dev/blog/sccache-in-github-actions)                                                     | Runner-side compiler-cache setup and its lifecycle.                                                                       |
| [Faster Rust builds in CI](https://depot.dev/blog/guide-to-faster-rust-builds-in-ci)                                              | Rust optimization strategies; map each to the work it avoids before comparing timings.                                    |
| [Rust Dockerfile best practices](https://depot.dev/blog/rust-dockerfile-best-practices)                                           | Dependency recipes, sccache, and persistent BuildKit mounts in a container-builder topology.                              |
| [Depot cargo command](https://depot.dev/changelog/2025-06-30-depot-cargo-command)                                                 | CLI integration for Cargo and the cache service; a setup interface, not a new compiler-cache algorithm.                   |
| [Cache disks](https://depot.dev/docs/ci/how-to-guides/cache-disks) and [cache-mount action](https://github.com/depot/cache-mount) | **Depot CI beta** native filesystem feature; the linked guide does not establish universal GitHub Actions runner support. |

## Native filesystem boundary

The cache-disk guide describes organization-wide names, concurrent reads/writes to a live filesystem, skipped mounts for public-fork PRs, and organization-configured retention. Any organization workflow using a name can access that disk; overlapping application writes need partitioning or synchronization. This is a different contract from a per-job snapshot clone. Do not assume Cargo's mutable target tree is safe for arbitrary concurrent writers. ([Depot CI cache disks](https://depot.dev/docs/ci/how-to-guides/cache-disks))

Use [container builds](../approaches/container-builds.md) for layer/mount choices and [persistent state](../approaches/persistent-state.md) for ownership and qualification. The linked articles are provider-authored evidence of a method, not measurements performed by this archive.
