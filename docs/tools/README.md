# Tools and cache engines

This section owns named implementations, supported cache units, integration limits, and cross-tool comparisons. [Approaches](../approaches/README.md) owns reusable strategies, [Providers](../providers/README.md) owns service/platform sources, and [storage topologies](../concepts/storage-topologies.md) maps the underlying storage.

| Tool or comparison                                                  | Purpose and evidence status                                                                          |
| ------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| [sccache vs Mr. Boxington vs Kache](compiler-caches.md)             | Direct compiler-tool comparison with source versions and measured/untested boundaries.               |
| [sccache](sccache.md)                                               | Compiler-output engine; this archive's substantial measurements concern direct S3 in GitHub Actions. |
| [Mr. Boxington](mr-boxington.md)                                    | Compilation/build-action engine; experimental here, with older same-job and fresh-runner trials.     |
| [Kache](kache.md)                                                   | Local-first compiler cache with remote sharing; explicitly untested here.                            |
| [cargo-chef](cargo-chef.md)                                         | Dependency-recipe tool for Docker layers; source-backed, untested here.                              |
| [Swatinem/rust-cache semantics](../concepts/rust-cache-behavior.md) | Rust-aware archive action; its input/cleanup contract has one existing owner.                        |
| [Mise setup](../operations/mise-tool-setup.md)                      | Tool installation/cache operation; keep its detailed setup in operations.                            |
| [Docker/BuildKit strategies](../approaches/container-builds.md)     | Container build layers and mutable mounts; pair with the named recipe/compiler tools as appropriate. |

The three compiler caches are open-source implementations that can run directly in GitHub Actions. Evaluate each chosen backend separately; a provider-hosted cache or hosted planner is not made open source by its client. `cargo-chef` is also open source, but it operates at the container dependency-layer boundary rather than serving as a fourth interchangeable compiler wrapper. Repository/license sources and applicability are linked from the focused pages; see the [scope rules](../README.md#scope-and-applicability).
