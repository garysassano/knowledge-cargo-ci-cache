# Knowledge: Cargo CI Cache

A growing knowledge base for LLMs and maintainers researching Rust/Cargo CI caching. Implementation guidance targets open-source components used directly in GitHub Actions; provider articles, other CI platforms, and unstable features remain tracked as research sources. See [scope and evidence rules](docs/README.md#scope-and-applicability).

## Current Answer

For most RunsOn Rust projects, start with mise, Magic Cache, input-only `Swatinem/rust-cache`, and a clean local `target/`. Keep no Rust cache as the control and remove the input cache when measurement shows no material benefit. For changing pull-request workloads whose compile time remains material, the leading measured compiler-output candidate is a clean target with S3-backed `sccache` in default server mode, subject to a representative end-to-end canary.

Whole-target archives and native filesystem persistence are situation-specific options. RunsOn now offers managed EBS sticky disks; the custom snapshot action remains archived evidence. The canonical record is [Decisions](docs/decisions/README.md), and the platform mapping is [RunsOn Deployment Map](docs/deployments/runs-on/README.md).

## Choose A Path

| If you are here to...                                       | Start with                                                                               |
| ----------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| Get the answer fast                                         | [Quickstart](docs/quickstart.md)                                                         |
| Choose a RunsOn implementation                              | [RunsOn Deployment Map](docs/deployments/runs-on/README.md)                              |
| Choose cache strategies                                     | [Approaches and decision flow](docs/approaches/README.md)                                |
| Find engines/tools, including cargo-chef                    | [Tools](docs/tools/README.md)                                                            |
| Map strategies to S3/GHA, EBS, NVMe, or tmpfs               | [Storage topologies](docs/concepts/storage-topologies.md)                                |
| Establish the clean-target baseline                         | [Clean Target](docs/approaches/clean-target.md)                                          |
| Compare sccache, Mr. Boxington, and untested Kache          | [Compiler-cache comparison](docs/tools/compiler-caches.md)                               |
| Find CI strategies and decision diagrams                    | [Strategy map](docs/approaches/README.md), [cache layers](docs/concepts/cache-layers.md) |
| Find providers and their documentation/blog posts           | [Providers](docs/providers/README.md)                                                    |
| Explore freshness beyond mtimes and other unstable features | [Cargo freshness alternatives](docs/research/cargo-freshness-alternatives.md)            |
| Explore proposed compiler-cache improvements                | [Research](docs/research/README.md)                                                      |
| Evaluate compiler-output caching                            | [S3-Backed `sccache`](docs/tools/sccache.md)                                             |
| Measure cache phases and runner bottlenecks                 | [Measuring Cache Performance](docs/operations/measuring-cache-performance.md)            |
| Diagnose recompilation                                      | [Diagnosing Cargo Rebuilds In CI](docs/operations/diagnosing-rebuilds.md)                |
| Understand why this works                                   | [Cargo Freshness Model](docs/concepts/cargo-freshness-model.md)                          |
| Review the measurements                                     | [Evidence](docs/evidence/README.md)                                                      |
| Copy workflow examples                                      | [Examples](examples/README.md)                                                           |

The full routing and ownership map is [Documentation](docs/README.md), and agent-specific editing rules are in [`AGENTS.md`](AGENTS.md).
