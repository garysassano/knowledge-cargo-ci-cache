# WarpBuild sources and strategy mapping

**Status: upstream descriptions, reviewed 2026-09-06; no local provider benchmark.** Archive acceleration, compiler-cache configuration, and VM snapshots are separate options; the snapshot feature's deployment limits are material.

| First-party source                                                                                                                                                       | Strategy and scope                                                                                               |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------- |
| [Caching overview](https://www.warpbuild.com/docs/ci/features/caching) and [setup-action integrations](https://www.warpbuild.com/docs/ci/features/caching/setup-actions) | Archive integrations, including upstream `Swatinem/rust-cache` with `cache-provider: warpbuild`.                 |
| [cache action](https://github.com/WarpBuilds/cache) and [Rust cache fork](https://github.com/WarpBuilds/rust-cache)                                                      | Provider-specific clients; check whether the upstream provider input already covers the requirement.             |
| [GitHub Actions cache article](https://www.warpbuild.com/blog/github-actions-cache)                                                                                      | Archive key/restore examples; retain Cargo-specific freshness and target-growth constraints when adapting them.  |
| [sccache guide](https://www.warpbuild.com/guides/sccache-github-actions)                                                                                                 | Compiler-cache integration patterns; a guide alone does not establish a provider-managed compiler-cache service. |
| [Snapshot runners](https://www.warpbuild.com/docs/ci/features/snapshot-runners)                                                                                          | Reuse VM disk snapshots between runs; distinct from mounting a selected Cargo cache directory.                   |

## Snapshot limits

The reviewed docs support snapshots on **WarpBuild Cloud Ubuntu only**. BYOC, Windows, and macOS are excluded, and snapshot labels on unsupported runners are silently ignored. `/tmp` does not persist across reboot. Snapshot aliases, cleanup, who can restore/publish, and startup overhead need qualification; the guide warns about credentials and organization-level runner allocation. ([Snapshot-runner documentation](https://www.warpbuild.com/docs/ci/features/snapshot-runners))

Do not copy the guide's broad cleanup commands without examining what they delete: removing ignored build state can defeat the intended cache. Use [persistent-state requirements](../approaches/persistent-state.md) and [Cargo freshness](../concepts/cargo-freshness-model.md) to define what the snapshot must retain.
