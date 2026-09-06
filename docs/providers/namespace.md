# Namespace sources and strategy mapping

**Status: upstream descriptions, reviewed 2026-09-06; no local provider benchmark.** This page covers native cache volumes and the separate compiler-cache service. Compare the mechanisms using [persistent state](../approaches/persistent-state.md) and [compiler caches](../tools/compiler-caches.md).

| First-party source                                                                                                                 | Strategy and scope                                                                                                       |
| ---------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| [nscloud-cache-action](https://github.com/namespacelabs/nscloud-cache-action)                                                      | Maps selected tool/cache directories to native cache volumes. Verify the selected mode's exact Cargo paths.              |
| [sccache integration](https://namespace.so/docs/integrations/sccache)                                                              | Configures a WebDAV backend with short-lived credentials; describes a hot tier near runners and colder artifact storage. |
| [Reducing GitHub Actions runtime for a Rust project](https://namespace.so/blog/reducing-github-actions-runtime-for-a-rust-project) | Rust case study combining runner changes and native caching; distinguishes initial runs from cache-hit runs.             |

## Interpretation

Native volume restoration and remote sccache objects are separate strategies. Export current backend credentials before the sccache server starts, and include setup/teardown in comparisons. Do not assume a native Cargo mode contains the complete target/worktree state required for Cargo no-op freshness.

The case study changes runner resources as well as cache behavior. Its final timings cannot isolate the effect of caching alone or predict this archive's workload. Reproduce the relevant topology with the [common measurement controls](../operations/measuring-cache-performance.md) before selecting it.
