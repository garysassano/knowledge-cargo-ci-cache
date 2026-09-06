# Ubicloud sources and strategy mapping

**Status: upstream descriptions, reviewed 2026-09-06; no local provider benchmark.** The documented strategy is transparent archive transport with upstream cache actions.

| First-party source                                                                                            | Strategy and scope                                                                                                       |
| ------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| [Ubicloud Cache](https://www.ubicloud.com/docs/github-actions-integration/ubicloud-cache)                     | Current configuration and compatibility; recommends upstream actions with transparent caching.                           |
| [Transparent-cache article](https://www.ubicloud.com/blog/github-actions-transparent-cache)                   | Provider explanation of moving compatible cache traffic closer to runners.                                               |
| [cache fork](https://github.com/ubicloud/cache) and [Rust cache fork](https://github.com/ubicloud/rust-cache) | Older provider wrappers. They were not archived in the September 6 review, but their last changes were in December 2024. |

Ubicloud also publishes an [AGPL-3.0 cloud implementation](https://github.com/ubicloud/ubicloud), whose README distinguishes self-managed installation from its hosted service. This establishes an open-source provider implementation to investigate; it does not qualify every managed-cache feature or a self-hosted deployment in this archive.

A changed archive backend does not change `rust-cache` cleanup, keys, selected paths, or Cargo freshness. Use [rust-cache behavior](../concepts/rust-cache-behavior.md) and [approach selection](../approaches/README.md) for those rules. Retain the forks as historical sources rather than assuming they are the current integration path.

This source set does not establish a dedicated sccache service or native Cargo disk feature. That is a coverage limit, not a claim that no such feature can exist.
