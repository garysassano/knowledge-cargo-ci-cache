# Blacksmith sources and strategy mapping

**Status: upstream descriptions, reviewed 2026-09-06; no local provider benchmark.** Blacksmith documents three relevant mechanisms: transparent Actions archive transport, sticky snapshot-derived volumes, and persistent container-builder state.

| First-party source                                                                                                                                           | Strategy and scope                                                                                                              |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------- |
| [Actions dependency caching](https://docs.blacksmith.sh/blacksmith-caching/dependencies-actions)                                                             | Accelerates compatible upstream archive clients. The reviewed page says Rust sccache traffic still uses GitHub's cache backend. |
| [Sticky Disks](https://docs.blacksmith.sh/blacksmith-caching/dependencies-sticky-disks) and [stickydisk action](https://github.com/useblacksmith/stickydisk) | Native ext4 volumes cloned from snapshots, with publication controlled separately from per-job writes.                          |
| [Cache design article](https://www.blacksmith.sh/blog/cache)                                                                                                 | Near-runner storage architecture and archive-transfer motivation.                                                               |
| [The physics of Docker build caching](https://www.blacksmith.sh/blog/the-physics-of-docker-build-caching)                                                    | Container experiments explaining why a restored layer cache may not restore mutable Cargo cache mounts.                         |
| [Archived cache wrapper](https://github.com/useblacksmith/cache) and [archived Rust wrapper](https://github.com/useblacksmith/rust-cache)                    | Historical links; the provider now recommends upstream actions with transparent caching.                                        |

## Publication and interpretation

The sticky-disk docs describe independent job clones, not a shared live writable disk. Branch protection is an optional setting: by default, jobs including pull requests can publish snapshots. With protection enabled, publication is limited to the documented default-branch events; other jobs can use a clone that is discarded afterward. Verify this setting before sharing trusted state with PR jobs. ([Sticky-disk branch protection](https://docs.blacksmith.sh/blacksmith-caching/dependencies-sticky-disks))

The Docker article concerns builder-side layers and mounts. Its results do not establish direct-Cargo target freshness or sccache performance on this archive's workload. Apply the [container-build model](../approaches/container-builds.md) and [persistent-state qualification](../approaches/persistent-state.md) when translating it into an experiment.
