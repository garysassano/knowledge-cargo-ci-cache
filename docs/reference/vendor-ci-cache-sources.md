# Rust CI Cache Ecosystem Sources

This reference owns core upstream projects, action wrappers, and historical source links. Provider capabilities and their first-party blog collections live in [Providers](../providers/README.md); mechanism selection lives in the [CI strategy map](../approaches/README.md). Reviewed: 2026-09-06.

## Choose By Cache Layer

Use [cache layers](../concepts/cache-layers.md) to distinguish dependency archives, Cargo target state, compiler objects, native volumes, and container caches. The [strategy map](../approaches/README.md#ci-strategy-map) routes each mechanism to its explanation and provider sources. External benchmarks remain source material; local results belong in [Evidence](../evidence/README.md).

## Core Projects And Actions

| Source                                                                                                                                                                                                                 | Role                                                                                                     | Current interpretation                                                                                                                                                                           |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| [Cargo build cache](https://doc.rust-lang.org/cargo/reference/build-cache.html)                                                                                                                                        | Official explanation of Cargo's local build cache, dependency tracking, and shared-cache considerations. | Baseline for what Cargo itself reuses and why copied state can still rebuild.                                                                                                                    |
| [`actions/cache`](https://github.com/actions/cache) and [GitHub cache documentation](https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/caching-dependencies-to-speed-up-workflows) | Generic archive-cache client and service semantics.                                                      | Canonical transport baseline for actions that delegate to the GitHub cache protocol.                                                                                                             |
| [`Swatinem/rust-cache`](https://github.com/Swatinem/rust-cache)                                                                                                                                                        | Rust-aware Cargo input and dependency-artifact archive policy.                                           | Maintained upstream wrapper. Its current `cache-provider` choices are `github` and `warpbuild`; provider forks may expose older or additional choices.                                           |
| [`actions-rust-lang/setup-rust-toolchain`](https://github.com/actions-rust-lang/setup-rust-toolchain)                                                                                                                  | Rust toolchain installation with caching enabled by default.                                             | Delegates its cache inputs to `Swatinem/rust-cache`; account for this implicit cache when designing controls.                                                                                    |
| [`sccache`](https://github.com/mozilla/sccache) and [`Mozilla-Actions/sccache-action`](https://github.com/Mozilla-Actions/sccache-action)                                                                              | Compiler-output cache plus installer and lifecycle action.                                               | For Rust with the GitHub backend, set both `SCCACHE_GHA_ENABLED=true` and `RUSTC_WRAPPER=sccache`; other backends replace the first setting, not the wrapper.                                    |
| [`mr-boxington`](https://github.com/jdx/mr-boxington) and [`jdx/mr-boxington-action`](https://github.com/jdx/mr-boxington-action)                                                                                      | Cargo/compiler action cache with local, GitHub Actions, or server-backed storage.                        | Emerging alternative introduced in August 2026. It can cache more than rustc object compilation, but it should pass workload-specific correctness and performance qualification before adoption. |
| [Kache](https://github.com/kunobi-ninja/kache)                                                                                                                                                                         | Local compiler cache with content-addressed outputs and remote sharing described by upstream.            | **Not tested in this archive.** See [the Kache profile](../tools/kache.md); upstream benchmark claims are not local evidence.                                                                    |
| [`cargo-chef`](https://github.com/LukeMathWalker/cargo-chef)                                                                                                                                                           | Builds a dependency recipe into a reusable container layer.                                              | Relevant to Docker and BuildKit builds; it is not a direct replacement for a runner-side Cargo or compiler cache.                                                                                |

## Provider documentation, actions, and blog posts

The canonical [provider index](../providers/README.md) links focused collections for RunsOn, Namespace, Depot, Blacksmith, WarpBuild, Ubicloud, Actuated, Earthly, and BuildJet. It records explicit deployment limits, article context, untested status, and gaps. Keep provider-specific behavior there rather than duplicating a second wide catalog here.

## Tool documentation and maintained forks

| Source                                                                                                                                                                                                                                            | Use                                                                                               |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| [sccache Rust support](https://github.com/mozilla/sccache/blob/v0.17.0/docs/Rust.md), [backends](https://github.com/mozilla/sccache/tree/v0.17.0/docs), and [v0.17.0 release](https://github.com/mozilla/sccache/releases/tag/v0.17.0)            | Versioned compiler and transport behavior.                                                        |
| [Multilevel caching](https://github.com/mozilla/sccache/blob/v0.17.0/docs/MultiLevel.md) and [S3](https://github.com/mozilla/sccache/blob/v0.17.0/docs/S3.md)                                                                                     | Backend semantics; separate read/write mode from IAM permissions.                                 |
| [Mr. Boxington action](https://mr-boxington.jdx.dev/github-action), [how it works](https://mr-boxington.jdx.dev/how-it-works), [limits](https://mr-boxington.jdx.dev/limits), and [benchmarks](https://mr-boxington.jdx.dev/benchmarks)           | Action payload, supported actions, and upstream methodology; not local retests.                   |
| [StepSecurity Rust cache](https://github.com/step-security/rust-cache), [sccache action](https://github.com/step-security/sccache-action), and [Maintained Actions program](https://docs.stepsecurity.io/actions/stepsecurity-maintained-actions) | Maintained forks; underlying cache behavior still comes from the corresponding upstream projects. |
| [Docker cache optimization](https://docs.docker.com/build/cache/optimize/)                                                                                                                                                                        | Official container-layer and cache-mount principles.                                              |

## Historical Or Superseded Wrappers

| Repository                                                                                                                | Review result                                                                                                                                     |
| ------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| [`useblacksmith/cache`](https://github.com/useblacksmith/cache)                                                           | Archived. Blacksmith now recommends upstream cache actions with its transparent backend.                                                          |
| [`useblacksmith/rust-cache`](https://github.com/useblacksmith/rust-cache)                                                 | Archived. Its archive notice recommends the upstream-maintained Rust cache action.                                                                |
| [`metalbear-co/sccache-action`](https://github.com/metalbear-co/sccache-action)                                           | Archived. Use the maintained Mozilla action unless reproducing historical behavior.                                                               |
| [`ubicloud/cache`](https://github.com/ubicloud/cache) and [`ubicloud/rust-cache`](https://github.com/ubicloud/rust-cache) | Not archived, but retained here as older provider forks because current Ubicloud documentation prefers transparent caching with upstream actions. |
| [`BuildJet/cache`](https://github.com/BuildJet/cache)                                                                     | Not archived, but its repository and migration-oriented documentation are historical signals rather than a current Rust optimization guide.       |

## `sccache` Upstream Baseline

The [implementation reference](compiler-cache-implementation.md) owns pinned server/client-side, multilevel, OpenDAL, and backend behavior. The [sccache tool profile](../tools/sccache.md) owns configuration and selection; [benchmarks](../evidence/cache-strategy-benchmarks.md) own the measured mode comparisons. A workstation optimization or newly released backend fix does not establish a CI improvement.

## `mr-boxington` Experimental Candidate

The [Mr. Boxington tool profile](../tools/mr-boxington.md) owns version-specific setup. The [paired evidence](../evidence/mr-boxington-vs-sccache.md) separates same-job reuse from fresh-runner restoration. Use the [three-tool comparison](../tools/compiler-caches.md) for capability and evidence differences.

## Kache: not tested

[Kache](https://github.com/kunobi-ninja/kache) remains untested and unadopted here. Its [candidate profile](../tools/kache.md) owns reviewed capabilities, release boundaries, CI/S3/filesystem source links, and qualification needs.

## Applying a source

Follow the [measurement procedure](../operations/measuring-cache-performance.md) when translating a provider claim into an experiment. Use [compiler-cache diagnostics](../operations/diagnosing-compiler-cache-integration.md) for ineffective restores and [maintenance](../operations/maintenance-checklist.md) before changing external assumptions.

## Implication For The Cold-Write Question

The [measured direct-S3 evidence](../evidence/cache-strategy-benchmarks.md) owns the population slowdown and its causal limitations. Provider material motivates transport comparisons; it does not prove that S3 writes caused the whole slowdown. Remaining transport work is tracked once in the [research roadmap](../research/runs-on-sccache/roadmap.md).

## Maintenance

Preserve source URLs when reorganizing this reference or provider profiles. Recheck source date, actual platform, release/interface, maintenance status, and benchmark context. Keep negative findings such as a missing dedicated integration visible, and do not turn a provider's benchmark into a local result.
