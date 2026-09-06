# Knowledge: Cargo CI Cache

Agent-oriented reference notes, decisions, evidence, and copyable GitHub Actions examples for Rust/Cargo CI cache behavior.

## Current Answer

For most RunsOn Rust projects, start with mise, Magic Cache, input-only `Swatinem/rust-cache`, and a clean local `target/`. Keep no Rust cache as the control and remove the input cache when measurement shows no material benefit. For changing pull-request workloads whose compile time remains material, the leading measured compiler-output candidate is a clean target with S3-backed `sccache` in default server mode, subject to a representative end-to-end canary.

Whole-target archives, post-v3.2 RunsOn sticky targets, and EBS snapshots are situation-specific options rather than the general default. The canonical record is [Decisions](docs/decisions/README.md), and the platform mapping is [RunsOn Deployment Map](docs/deployments/runs-on/README.md).

## Choose A Path

| If you are here to... | Start with |
| --- | --- |
| Get the answer fast | [Quickstart](docs/quickstart.md) |
| Choose a RunsOn implementation | [RunsOn Deployment Map](docs/deployments/runs-on/README.md) |
| Compare cache approaches | [Approaches](docs/approaches/README.md) |
| Establish the clean-target baseline | [Clean Target](docs/approaches/clean-target.md) |
| Compare Mr. Boxington and sccache | [Mr. Boxington](docs/approaches/mr-boxington.md) |
| Find Kache, cache providers, and their blog posts | [Ecosystem Sources](docs/reference/vendor-ci-cache-sources.md) |
| Explore proposed compiler-cache improvements | [Research](docs/research/README.md) |
| Evaluate compiler-output caching | [S3-Backed `sccache`](docs/approaches/sccache.md) |
| Measure cache phases and runner bottlenecks | [Measuring Cache Performance](docs/operations/measuring-cache-performance.md) |
| Diagnose recompilation | [Diagnosing Cargo Rebuilds In CI](docs/operations/diagnosing-rebuilds.md) |
| Understand why this works | [Cargo Freshness Model](docs/concepts/cargo-freshness-model.md) |
| Review the measurements | [Evidence](docs/evidence/README.md) |
| Copy workflow examples | [Examples](examples/README.md) |

The full routing and ownership map is [Documentation](docs/README.md), and agent-specific editing rules are in [`AGENTS.md`](AGENTS.md).
