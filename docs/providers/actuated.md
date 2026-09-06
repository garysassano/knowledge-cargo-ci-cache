# Actuated sources and strategy mapping

**Status: source-backed self-hosted design, reviewed 2026-09-06; no local Rust benchmark.** These sources explain hosting an S3-compatible archive cache on the runner host or nearby infrastructure.

| First-party source                                                                             | Strategy and scope                                                                                            |
| ---------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| [Self-hosted cache setup](https://docs.actuated.com/tasks/local-github-cache/)                 | SeaweedFS/S3-compatible storage with an explicitly substituted archive client; also shows Git object caching. |
| [Faster self-hosted cache](https://actuated.com/blog/faster-self-hosted-cache)                 | Motivation and topology for reducing distance to the cache.                                                   |
| [Local caching for GitHub Actions](https://actuated.com/blog/local-caching-for-github-actions) | Application case study comparing local cache setups; it is not a Rust/compiler-cache benchmark.               |
| [Caching in GitHub Actions](https://actuated.com/blog/caching-in-github-actions)               | General archive-cache background and examples.                                                                |

## Transport boundary

The setup guide replaces `actions/cache` with `tespkg/actions-cache` to target S3-compatible storage; built-in setup-action caches do not automatically use that replacement. Per-host stores can miss when a subsequent job lands elsewhere, while a shared nearby store changes the availability and contention model. The examples include older action versions: use the architecture as source material and refresh interfaces before copying YAML. ([Self-hosted setup guide](https://docs.actuated.com/tasks/local-github-cache/))

This is an archive-client/backend strategy. Using the same S3-compatible server for compiler objects would be a separate configuration and experiment, with distinct namespaces and permissions. Caching Git objects reduces checkout transfer but does not preserve worktree mtimes. Apply [cache layers](../concepts/cache-layers.md) and the [measurement procedure](../operations/measuring-cache-performance.md).
