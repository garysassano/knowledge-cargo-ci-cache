# Vendor Rust And CI Cache Sources

This catalog records first-party documentation and articles from CI runner, cache, and build-platform vendors that are relevant to Rust, Cargo, `sccache`, or GitHub Actions cache transport. It is a maintained coverage scan, not a claim that every vendor page is useful or independently verified.

Vendor pages explain supported configurations and vendor architecture, but they are not neutral benchmark evidence. Keep measured observations in [Evidence](../evidence/README.md), approach tradeoffs in [Approaches](../approaches/README.md), and current conclusions in [Decisions](../decisions/README.md).

Last reviewed: 2026-08-20.

## Upstream Baseline

Use upstream `sccache` documentation as the canonical source for mechanics. Vendor pages are useful for backend topology, product integration, and experiment ideas, but they do not override upstream behavior.

Version 0.17.0 added opt-in client-side mode through `SCCACHE_CLIENT_SIDE=1`. Upstream says this removes a client-to-daemon round trip and a server-side bottleneck, with demonstrated improvement on developer workstations. The mechanism claim and workstation result should not be read as a general performance guarantee: the archive's direct-S3 CI trials found client-side mode substantially slower than default server mode despite high warm hit rates.

Version 0.17.0 also documents multilevel caching such as `disk,s3`. Reads check levels from fastest to slowest and asynchronously backfill earlier levels after a lower-level hit. For a normal cache miss with the default `l0` write-error policy, the implementation awaits the L0 disk write and then spawns best-effort writes to later levels such as S3. This can move S3 PUT latency off the compiler invocation's critical path, but a CI experiment must verify whether the background remote writes finish before the runner and `sccache` process terminate.

Direct S3 supports a scoped key prefix and `SCCACHE_S3_RW_MODE=READ_ONLY`. The read-only setting is useful for measurement and workflow behavior, but it is not an IAM boundary.

- [`sccache` v0.17.0 release](https://github.com/mozilla/sccache/releases/tag/v0.17.0)
- [Multilevel cache documentation](https://github.com/mozilla/sccache/blob/v0.17.0/docs/MultiLevel.md)
- [S3 backend documentation](https://github.com/mozilla/sccache/blob/v0.17.0/docs/S3.md)
- [Rust support and limitations](https://github.com/mozilla/sccache/blob/v0.17.0/docs/Rust.md)

## Direct `sccache` And Rust Sources

| Vendor | Source | What it contributes | Applicability |
| --- | --- | --- | --- |
| Namespace | [`sccache` integration](https://namespace.so/docs/integrations/sccache) | Configures `sccache` through short-lived WebDAV credentials. Namespace describes a hot cache near the runner with a colder artifact-storage tier. | Architectural comparison for direct S3: reducing per-object network latency is a product feature, not a workflow flag we omitted. |
| Namespace | [Reducing GitHub Actions runtime for a Rust project](https://namespace.so/blog/reducing-github-actions-runtime-for-a-rust-project) | Rust-specific runner and cache case study. | Useful as a vendor case study and source of scenarios to reproduce; do not compare its headline result directly with this archive's workloads. |
| Depot | [`sccache` integration](https://depot.dev/docs/cache/integrations/sccache) | Uses Depot Cache as a WebDAV backend. Depot runners preconfigure the endpoint; workflows still install `sccache` and set `RUSTC_WRAPPER`. | Confirms the same wrapper and installation requirements as our canary while using a different cache transport. |
| Depot | [`sccache` in GitHub Actions](https://depot.dev/blog/sccache-in-github-actions) | End-to-end Rust workflow guidance, including `CARGO_INCREMENTAL=0`, installation, wrapper configuration, and statistics. | Configuration cross-check. It does not establish that a WebDAV service and direct S3 have the same cold-write behavior. |
| Depot | [Guide to faster Rust builds in CI](https://depot.dev/blog/guide-to-faster-rust-builds-in-ci) | Broader Rust CI guidance covering runner resources, dependency caching, compiler caching, and build configuration. | Candidate checklist and terminology source; individual recommendations still require measurement on the target workload. |
| Earthly | [How `sccache` works with Rust](https://earthly.dev/blog/rust-sccache/) | Tutorial-level explanation of local and remote `sccache`, wrapper setup, stats, and CI usage. | Useful conceptual introduction. Treat versions and workflow snippets as historical until rechecked. |
| Earthly | [Persistent Rust builds](https://earthly.dev/blog/incremental-rust-builds/) | Uses persistent BuildKit runners with native Cargo cache mounts to avoid archive transfer on every run. | Architectural analogue for sticky or snapshot-backed native storage. Reported timings are workload-specific vendor case-study results. |
| RunsOn | [`runs-on/action` `sccache` configuration](https://github.com/runs-on/action#sccache) | Exports the direct S3 backend settings and `RUSTC_WRAPPER`; installation remains separate. | Canonical source for the RunsOn workflow shape in this archive. |
| RunsOn | [Magic Cache](https://runs-on.com/docs/performance/caching/actions/) | Describes transparent acceleration of GitHub Actions cache protocol traffic. | Applies to `actions/cache`-compatible clients such as `Swatinem/rust-cache`; it is not the direct S3 transport used by the RunsOn `sccache` configuration. |

## Adjacent GitHub Actions Cache Providers

These sources matter when comparing cache transport, but a faster GitHub Actions cache implementation does not automatically accelerate an `sccache` backend.

| Vendor | Source | Relevant behavior | Rust boundary |
| --- | --- | --- | --- |
| Blacksmith | [Actions dependency caching](https://docs.blacksmith.sh/blacksmith-caching/dependencies-actions) | Transparently redirects supported Actions cache clients to a colocated backend. The page explicitly says Rust `sccache` still uses GitHub's backend. | Useful for `Swatinem/rust-cache` and archive-cache comparisons, but currently not evidence for accelerated `sccache`. Blacksmith's old `useblacksmith/rust-cache` fork is archived. |
| Blacksmith | [Colocated cache implementation](https://www.blacksmith.sh/blog/cache) | Describes transparent request redirection to a colocated S3-compatible cache and the importance of preserving client concurrency behavior. | Architecture and vendor performance claims apply to compatible GitHub Actions archive-cache traffic, not the excluded Rust `sccache` path. |
| Blacksmith | [Sticky Disks](https://docs.blacksmith.sh/blacksmith-caching/dependencies-sticky-disks) | Clones the last committed ext4 disk snapshot into each job and commits a new snapshot after the job. Optional branch protection lets PR jobs read trusted state while discarding their writes. | Native-filesystem comparison for large Cargo state. It avoids archive serialization but still requires key, mutation, growth, trust, and last-committed-snapshot policies. |
| Blacksmith | [The physics of Docker build caching](https://www.blacksmith.sh/blog/the-physics-of-docker-build-caching) | Compares layer cache, persistent BuildKit cache mounts, and image-store persistence, including a Rust container workload. | The Rust result concerns Cargo directories mounted inside a persistent Docker builder, not direct Cargo execution or `sccache`. |
| Depot | [Durable cache disks](https://depot.dev/docs/ci/how-to-guides/cache-disks) | Mounts an organization-scoped persistent filesystem that supports concurrent workflows and explicitly lists Cargo inputs and `sccache` directories as uses. | Native-filesystem comparison with no per-job archive transfer. Shared multi-writer state, organization-wide naming, retention, fork behavior, and trust boundaries must be evaluated separately. |
| Ubicloud | [Ubicloud Cache](https://www.ubicloud.com/docs/github-actions-integration/ubicloud-cache) | Documents a transparent, near-runner Actions cache and supports third-party clients including `Swatinem/rust-cache`. It also distinguishes the recommended transparent cache from older cache-action forks. | Relevant to Cargo archive transport. The page does not describe a dedicated `sccache` backend. |
| Ubicloud | [GitHub Actions transparent cache](https://www.ubicloud.com/blog/github-actions-transparent-cache) | Explains the transparent cache product and its motivation. | Vendor architecture context, not a Rust benchmark. |
| WarpBuild | [Caching](https://www.warpbuild.com/docs/ci/features/caching) | Documents a drop-in Actions cache and cache-aware setup actions, including Rust toolchain setup. | Relevant to archive and setup caches. No dedicated Rust `sccache` integration was found in the reviewed source index. |
| WarpBuild | [Using GitHub Actions cache with popular languages](https://www.warpbuild.com/blog/github-actions-cache) | Generic language-cache examples and cache-key guidance. | Use only where the Rust example and current action behavior have been rechecked. |

## Coverage Notes

| Provider or source family | Review result |
| --- | --- |
| Namespace | Dedicated `sccache` integration and Rust case study found. |
| Depot | Dedicated `sccache` integration, near-runner WebDAV cache, broader Rust CI guidance, and durable cache disks found. |
| Earthly | Rust-specific `sccache` tutorial found; Earthly is a build platform rather than a transparent GitHub-hosted runner cache. |
| RunsOn | Direct S3 `sccache` configuration and separate Magic Cache documentation found. |
| Blacksmith | Colocated Actions cache, native sticky disks, and Docker-specific Rust material found; its Actions-cache documentation explicitly excludes Rust `sccache` from the accelerated backend. |
| Ubicloud | Transparent Actions cache with explicit `Swatinem/rust-cache` support found; no dedicated `sccache` integration found. |
| WarpBuild | Generic Actions cache and cache-aware Rust setup support found; no dedicated `sccache` integration found. |
| BuildJet | No durable first-party Rust or `sccache` guide was located during this review. Treat old BuildJet cache material as historical if it is later recovered rather than as current product guidance. |

Add a provider when a first-party page supplies at least one of the following: Rust/Cargo configuration, an `sccache` backend, GitHub Actions cache transport behavior, cache isolation or retention semantics, or a measured case study that can seed a local experiment. Do not add generic runner marketing pages that contain no cache detail.

## Configuration Cross-Check

| Guidance from the collected sources | Archive status |
| --- | --- |
| Disable rustc incremental compilation with `CARGO_INCREMENTAL=0` when using `sccache`. | Applied in the canary. |
| Install `sccache`; configuring a remote backend alone does not install it. | Applied through `Mozilla-Actions/sccache-action`. |
| Set `RUSTC_WRAPPER=sccache`. | Applied by `runs-on/action` for the documented S3 mode. |
| Print `sccache --show-stats`. | Applied, including failure paths. |
| Start the `sccache` server explicitly. | Not required for the current workflow because the wrapper can auto-start it and the installer action manages lifecycle. Explicit startup remains useful for debugging. |
| Set `SCCACHE_GHA_ENABLED=true`. | Not applicable to the current direct S3 backend. It selects the GitHub Actions cache backend and would change the experiment. |
| Use a near-runner WebDAV or transparent cache service. | Architectural alternative offered by some vendors, not a missing RunsOn S3 setting. Benchmark it as a separate approach. |
| Use `disk,s3` multilevel caching with the default `l0` policy. | Measured on `sccache` v0.17.0. It did not improve cold population, remote writes were incomplete at teardown, and an ephemeral L0 produced no cross-job hits. See the canonical [evidence](../evidence/cache-strategy-benchmarks.md). |
| Optimize uploads through a provider-specific cache client. | Relevant to Actions archive caches. It does not imply that direct S3 `sccache` writes are uploaded by RunsOn or inherit the provider's archive-upload concurrency. |

## Implication For The Cold-Write Question

The collected vendor material makes low-latency, near-runner cache transport a credible comparison point, but it does not prove that S3 uploads caused the entire cold-run slowdown. The measured population run was about 21% slower than the same-profile no-cache control and performed 5,599 writes, while write durations overlapped with compilation. RunsOn configures the S3 endpoint and credentials; `sccache` itself performs the object operations. See [Cache Strategy Benchmarks](../evidence/cache-strategy-benchmarks.md) for the measurements and limitations.

The direct-S3 client-side, multilevel, and read-only isolation experiments are recorded in the canonical [evidence](../evidence/cache-strategy-benchmarks.md). Remaining useful transport experiments are:

1. Measure a near-runner Redis or WebDAV service if operating one is realistic.
2. Benchmark representative S3 small-object PUT and GET operations at bounded concurrency.
3. Compare supported compression levels with backend, namespace, source, and runner fixed.
4. Test persistent native storage separately after the RunsOn upgrade.

Keep CPU, runner shape, source state, `sccache` version, compression, namespace, and build command fixed, and measure build critical-path time separately from server shutdown or cache-drain time.

## Maintenance

- Recheck vendor pages before using a claimed multiplier, backend, retention rule, action fork, or compatibility statement as current behavior.
- Record the exact review date when materially changing this catalog.
- Prefer first-party documentation over vendor comparison pages.
- Preserve negative findings such as “no dedicated `sccache` integration found” so later reviews can identify actual product changes.
- Move locally reproduced measurements into [Evidence](../evidence/README.md); do not promote vendor benchmarks into this archive's conclusions.
