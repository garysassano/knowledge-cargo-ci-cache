# Rust CI Cache Ecosystem Sources

This catalog indexes selected first-party documentation, action repositories, and technical articles that are relevant to Rust, Cargo, compiler caching, persistent build state, or GitHub Actions cache transport. It is intended to be a broad, maintained starting point, not a literal claim to cover the entire internet or every thin action fork.

The useful unit is not merely a URL: each entry should identify the cache layer it changes, the implementation or protocol it delegates to, its current maintenance status, and the boundary on any accompanying performance claim. Vendor pages explain supported configurations and architecture, but they are not neutral benchmark evidence. Keep measured observations in [Evidence](../evidence/README.md), approach tradeoffs in [Approaches](../approaches/README.md), and current conclusions in [Decisions](../decisions/README.md).

Catalog expanded: 2026-08-31. Repository maintenance metadata, compiler-action interfaces, and provider source links refreshed: 2026-09-06. Provider product details are dated source observations, not guarantees for a particular account or deployment.

## Choose By Cache Layer

| Cache layer | Typical state | Representative sources | Main boundary |
| --- | --- | --- | --- |
| Cargo input archive | Registry archives, Git checkouts, and optionally installed tools | [`actions/cache`](https://github.com/actions/cache), [`Swatinem/rust-cache`](https://github.com/Swatinem/rust-cache), and [GitHub dependency-cache documentation](https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/caching-dependencies-to-speed-up-workflows) | Saves downloads and setup, but does not by itself cache rustc compilation results. |
| Cargo target archive | Dependency artifacts and selected `target/` state | [`Swatinem/rust-cache`](https://github.com/Swatinem/rust-cache) and compatible provider forks | Archive transfer, Cargo freshness, path stability, pruning, and writer policy all affect whether a nominal hit saves time. |
| Compiler action cache | rustc outputs and, depending on the tool, native compilation, build scripts, or links | [`sccache`](https://github.com/mozilla/sccache), [`Mozilla-Actions/sccache-action`](https://github.com/Mozilla-Actions/sccache-action), [`mr-boxington`](https://github.com/jdx/mr-boxington), and [Kache](https://github.com/kunobi-ninja/kache) | Compiler wrappers should be compared as alternatives. Do not stack tools that both own `RUSTC_WRAPPER` unless that composition is explicitly supported and tested. |
| Native persistent filesystem | Cargo inputs, compiler-cache objects, target state, or tool downloads mounted directly | [`namespacelabs/nscloud-cache-action`](https://github.com/namespacelabs/nscloud-cache-action), [`depot/cache-mount`](https://github.com/depot/cache-mount), [`useblacksmith/stickydisk`](https://github.com/useblacksmith/stickydisk), and [`runs-on/action` sticky caches](https://github.com/runs-on/action#sticky_cache) | Avoids per-job archive serialization, but adds lineage, concurrency, trust, retention, garbage-collection, and disk-pressure concerns. |
| Container or BuildKit cache | Dependency layers, package-manager cache mounts, and persistent builder state | [`cargo-chef`](https://github.com/LukeMathWalker/cargo-chef), [Docker build-cache guidance](https://docs.docker.com/build/cache/optimize/), and Earthly's [persistent Rust builds](https://earthly.dev/blog/incremental-rust-builds/) | Applies inside a container-builder topology and should not be presented as equivalent to direct Cargo execution on the runner. |

## Core Projects And Actions

| Source | Role | Current interpretation |
| --- | --- | --- |
| [Cargo build cache](https://doc.rust-lang.org/cargo/reference/build-cache.html) | Official explanation of Cargo's local build cache, dependency tracking, and shared-cache considerations. | Baseline for what Cargo itself reuses and why copied state can still rebuild. |
| [`actions/cache`](https://github.com/actions/cache) and [GitHub cache documentation](https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/caching-dependencies-to-speed-up-workflows) | Generic archive-cache client and service semantics. | Canonical transport baseline for actions that delegate to the GitHub cache protocol. |
| [`Swatinem/rust-cache`](https://github.com/Swatinem/rust-cache) | Rust-aware Cargo input and dependency-artifact archive policy. | Maintained upstream wrapper. Its current `cache-provider` choices are `github` and `warpbuild`; provider forks may expose older or additional choices. |
| [`actions-rust-lang/setup-rust-toolchain`](https://github.com/actions-rust-lang/setup-rust-toolchain) | Rust toolchain installation with caching enabled by default. | Delegates its cache inputs to `Swatinem/rust-cache`; account for this implicit cache when designing controls. |
| [`sccache`](https://github.com/mozilla/sccache) and [`Mozilla-Actions/sccache-action`](https://github.com/Mozilla-Actions/sccache-action) | Compiler-output cache plus installer and lifecycle action. | For Rust with the GitHub backend, set both `SCCACHE_GHA_ENABLED=true` and `RUSTC_WRAPPER=sccache`; other backends replace the first setting, not the wrapper. |
| [`mr-boxington`](https://github.com/jdx/mr-boxington) and [`jdx/mr-boxington-action`](https://github.com/jdx/mr-boxington-action) | Cargo/compiler action cache with local, GitHub Actions, or server-backed storage. | Emerging alternative introduced in August 2026. It can cache more than rustc object compilation, but it should pass workload-specific correctness and performance qualification before adoption. |
| [Kache](https://github.com/kunobi-ninja/kache) | Local compiler cache with content-addressed outputs and remote sharing described by upstream. | **Not tested in this archive.** See [the untested entry](#kache-not-tested); upstream benchmark claims are not local evidence. |
| [`cargo-chef`](https://github.com/LukeMathWalker/cargo-chef) | Builds a dependency recipe into a reusable container layer. | Relevant to Docker and BuildKit builds; it is not a direct replacement for a runner-side Cargo or compiler cache. |

## Provider documentation, actions, and blog posts

Product descriptions retain the 2026-08-31 source review; repository archive/activity status was refreshed on 2026-09-06; it is not a security endorsement or a guarantee that a provider feature is enabled for every account.

| Provider or project | Actions and wrappers | First-party documentation and articles | Boundary or status |
| --- | --- | --- | --- |
| GitHub | [`actions/cache`](https://github.com/actions/cache) | [Caching dependencies to speed up workflows](https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/caching-dependencies-to-speed-up-workflows) | Generic archive transport. Cache-hit status says nothing about Cargo freshness after restoration. |
| Rust community | [`Swatinem/rust-cache`](https://github.com/Swatinem/rust-cache), [`actions-rust-lang/setup-rust-toolchain`](https://github.com/actions-rust-lang/setup-rust-toolchain) | The action READMEs are the canonical current input references. | The setup action enables and delegates to `rust-cache` unless `cache: false` is set. |
| Mozilla | [`Mozilla-Actions/sccache-action`](https://github.com/Mozilla-Actions/sccache-action) | [`sccache` Rust documentation](https://github.com/mozilla/sccache/blob/v0.17.0/docs/Rust.md) and [backend documentation](https://github.com/mozilla/sccache/tree/v0.17.0/docs) | The action installs and manages `sccache`; backend and `RUSTC_WRAPPER` configuration remain explicit. |
| jdx | [`jdx/mr-boxington-action`](https://github.com/jdx/mr-boxington-action) | [GitHub Action](https://mr-boxington.jdx.dev/github-action), [how it works](https://mr-boxington.jdx.dev/how-it-works), [limits](https://mr-boxington.jdx.dev/limits), and [benchmarks](https://mr-boxington.jdx.dev/benchmarks) | Emerging alternative to `sccache`; treat it as experimental and benchmark it on the target workload. |
| StepSecurity | [`step-security/rust-cache`](https://github.com/step-security/rust-cache), [`step-security/sccache-action`](https://github.com/step-security/sccache-action) | [Maintained Actions program](https://docs.stepsecurity.io/actions/stepsecurity-maintained-actions) | Security-maintained drop-in forks of the upstream Rust cache and `sccache` installer actions; cache semantics still derive from those upstream projects. |
| Namespace | [`namespacelabs/nscloud-cache-action`](https://github.com/namespacelabs/nscloud-cache-action) | [`sccache` integration](https://namespace.so/docs/integrations/sccache) and [Rust project case study](https://namespace.so/blog/reducing-github-actions-runtime-for-a-rust-project) | The action maps selected cache directories to a native cache volume; the separate `sccache` integration uses short-lived WebDAV credentials and describes a nearby hot tier with colder artifact storage. |
| Depot | [`depot/cache-mount`](https://github.com/depot/cache-mount) | [Durable cache disks](https://depot.dev/docs/ci/how-to-guides/cache-disks), [`sccache` integration](https://depot.dev/docs/cache/integrations/sccache), [`sccache` in GitHub Actions](https://depot.dev/blog/sccache-in-github-actions), and [faster Rust builds in CI](https://depot.dev/blog/guide-to-faster-rust-builds-in-ci) | Cache mounts are organization-scoped native filesystems with concurrent access, skip mounting for public-fork PRs, and follow the configured retention policy, whose documented default is 14 days. The separate compiler-cache integration uses WebDAV; installation and wrapper configuration still matter. |
| Blacksmith | [`useblacksmith/stickydisk`](https://github.com/useblacksmith/stickydisk) | [Sticky Disks](https://docs.blacksmith.sh/blacksmith-caching/dependencies-sticky-disks), [Actions dependency caching](https://docs.blacksmith.sh/blacksmith-caching/dependencies-actions), [colocated cache design](https://www.blacksmith.sh/blog/cache), and [Docker cache physics](https://www.blacksmith.sh/blog/the-physics-of-docker-build-caching) | Sticky Disks clone native filesystem snapshots with separate branch/publication controls. Transparent Actions caching accelerates compatible archive clients, while the linked documentation says Rust `sccache` still routes through GitHub's backend. The Docker article concerns builder-side Cargo state, not a direct-Cargo benchmark. |
| RunsOn | [`runs-on/action`](https://github.com/runs-on/action) | [`sccache` configuration](https://github.com/runs-on/action#sccache) and [Magic Cache](https://runs-on.com/docs/performance/caching/actions/) | One action exposes separate direct-S3 `sccache`, transparent Actions-cache, and sticky-cache paths. Keep those transports distinct in experiments. |
| WarpBuild | [`WarpBuilds/cache`](https://github.com/WarpBuilds/cache), [`WarpBuilds/rust-cache`](https://github.com/WarpBuilds/rust-cache) | [Caching](https://www.warpbuild.com/docs/ci/features/caching) and [GitHub Actions cache examples](https://www.warpbuild.com/blog/github-actions-cache) | Current provider-specific archive clients. Upstream `Swatinem/rust-cache` also supports `cache-provider: warpbuild`, reducing the need for the Rust fork. |
| Ubicloud | [`ubicloud/cache`](https://github.com/ubicloud/cache), [`ubicloud/rust-cache`](https://github.com/ubicloud/rust-cache) | [Ubicloud Cache](https://www.ubicloud.com/docs/github-actions-integration/ubicloud-cache) and [transparent-cache article](https://www.ubicloud.com/blog/github-actions-transparent-cache) | The repositories are not archived but have not changed since December 2024. Current product documentation recommends transparent caching with upstream actions over the old forks. |
| Earthly | No GitHub Actions cache wrapper in this index. | [Persistent Rust builds](https://earthly.dev/blog/incremental-rust-builds/), [`sccache` with Rust](https://earthly.dev/blog/rust-sccache/), and [`cargo-chef` for Docker layer caching](https://earthly.dev/blog/cargo-chef/) | The persistent-build article uses BuildKit with native Cargo cache mounts; the sccache tutorial and cargo-chef article describe different cache layers. Translate the topology and method before comparing their headline timings with a runner-side experiment. |
| BuildJet | [`BuildJet/cache`](https://github.com/BuildJet/cache) | The repository links a provider migration guide but no current first-party Rust or `sccache` guide was found in this review. | The wrapper is not archived but has not changed since March 2024. Retain it as historical coverage rather than current Rust guidance. |

## Historical Or Superseded Wrappers

| Repository | Review result |
| --- | --- |
| [`useblacksmith/cache`](https://github.com/useblacksmith/cache) | Archived. Blacksmith now recommends upstream cache actions with its transparent backend. |
| [`useblacksmith/rust-cache`](https://github.com/useblacksmith/rust-cache) | Archived. Its archive notice recommends the upstream-maintained Rust cache action. |
| [`metalbear-co/sccache-action`](https://github.com/metalbear-co/sccache-action) | Archived. Use the maintained Mozilla action unless reproducing historical behavior. |
| [`ubicloud/cache`](https://github.com/ubicloud/cache) and [`ubicloud/rust-cache`](https://github.com/ubicloud/rust-cache) | Not archived, but retained here as older provider forks because current Ubicloud documentation prefers transparent caching with upstream actions. |
| [`BuildJet/cache`](https://github.com/BuildJet/cache) | Not archived, but its repository and migration-oriented documentation are historical signals rather than a current Rust optimization guide. |

## `sccache` Upstream Baseline

Use upstream `sccache` documentation as the canonical source for mechanics. Vendor pages are useful for backend topology, product integration, and experiment ideas, but they do not override upstream behavior.

Version 0.17.0 added opt-in client-side mode through `SCCACHE_CLIENT_SIDE=1`. Upstream says this removes a client-to-daemon round trip and a server-side bottleneck, with demonstrated improvement on developer workstations. The mechanism claim and workstation result should not be read as a general performance guarantee: the archive's direct-S3 CI trials found client-side mode substantially slower than default server mode despite high warm hit rates.

Version 0.17.0 also documents multilevel caching such as `disk,s3`. Reads check levels from fastest to slowest and asynchronously backfill earlier levels after a lower-level hit. For a normal cache miss with the default `l0` write-error policy, the implementation awaits the L0 disk write and then spawns best-effort writes to later levels such as S3. This can move S3 PUT latency off the compiler invocation's critical path, but a CI experiment must verify whether the background remote writes finish before the runner and `sccache` process terminate.

Direct S3 supports a scoped key prefix and `SCCACHE_S3_RW_MODE=READ_ONLY`. The read-only setting is useful for measurement and workflow behavior, but it is not an IAM boundary.

- [`sccache` v0.17.0 release](https://github.com/mozilla/sccache/releases/tag/v0.17.0)
- [Multilevel cache documentation](https://github.com/mozilla/sccache/blob/v0.17.0/docs/MultiLevel.md)
- [S3 backend documentation](https://github.com/mozilla/sccache/blob/v0.17.0/docs/S3.md)
- [Rust support and limitations](https://github.com/mozilla/sccache/blob/v0.17.0/docs/Rust.md)

## `mr-boxington` Experimental Candidate

The [Mr. Boxington approach](../approaches/mr-boxington.md) owns selection and version-specific setup. The [evidence](../evidence/mr-boxington-vs-sccache.md) separates same-job reuse from an ineffective exact restore on fresh Docker runners. The current action defaults to a target payload; select an explicit object payload when testing clean-target compiler reuse. Do not infer a current-version fix or result from the older trials.

## Kache: not tested

[kunobi-ninja/kache](https://github.com/kunobi-ninja/kache) is included at the source-discovery stage only. This archive has not installed, benchmarked, validated, or adopted it. Its [README](https://github.com/kunobi-ninja/kache#readme) describes a local compiler cache for Rust and C/C++, content-addressed build outputs, reuse across worktrees, and S3-compatible or filesystem remotes. Those are upstream descriptions, not results established here.

| First-party source | Use |
| --- | --- |
| [Repository and README](https://github.com/kunobi-ninja/kache) | Architecture, supported workloads, storage model, commands, and benchmark links. |
| [CI guide](https://kunobi.ninja/docs/kache/remote-cache/ci) and [Kache action](https://github.com/kunobi-ninja/kache-action) | Candidate CI setup; not a workflow tested by this archive. |
| [Kache and sccache comparison](https://kunobi.ninja/docs/kache/getting-started/comparison) | Upstream comparison claims and methodology to examine before an experiment. |
| [S3 setup](https://kunobi.ninja/docs/kache/remote-cache/s3-setup) and [filesystem remotes](https://kunobi.ninja/docs/kache/remote-cache/filesystem-setup) | Remote-store semantics to qualify independently. |

If evaluated, use an isolated compiler-wrapper configuration and the same [measurement controls](../operations/measuring-cache-performance.md) as other candidates. Correctness, supported output classes, path stability, local disk growth, remote durability, and trust boundaries need validation before any performance recommendation.

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
