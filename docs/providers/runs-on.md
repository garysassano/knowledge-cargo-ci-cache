# RunsOn sources and strategy mapping

**Status: source review, 2026-09-06.** RunsOn runs GitHub Actions infrastructure in an AWS account. This page owns source discovery and the mapping to generic strategies; current configuration and platform requirements are canonical in the [RunsOn deployment map](../deployments/runs-on/README.md).

| First-party source                                                                                                                                     | Strategy and scope                                                                                                                             |
| ------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| [Magic Cache](https://runs-on.com/docs/performance/caching/actions/) and [RunsOn action](https://github.com/runs-on/action)                            | Changes the backend for compatible Actions archive clients; retains their key/path/serialization semantics.                                    |
| [sccache configuration](https://github.com/runs-on/action#sccache)                                                                                     | Exports settings for direct S3 compiler objects, independently of Magic Cache. Installation and compiler-cache lifecycle remain separate.      |
| [Sticky disks](https://runs-on.com/docs/runners/capabilities/sticky-disks/) and [sticky action inputs](https://github.com/runs-on/action#sticky_cache) | Managed EBS volume/snapshot persistence, including Cargo inputs, custom paths, Git mirrors, and BuildKit state. Requires RunsOn v3.2 or newer. |

## Implementation boundary

The [RunsOn public repository](https://github.com/runs-on/runs-on) identifies its CloudFormation assets and supporting files as MIT-licensed and its server/agent as commercially licensed. The [action](https://github.com/runs-on/action) is MIT-licensed. Keep these components separate: the existing deployment is not evidence of an entirely open-source runner control plane. Managed sticky disks require the RunsOn platform; an independently implemented snapshot lifecycle is a different design.

## Managed EBS persistence

Sticky disks restore a compatible EBS snapshot into a per-job volume and publish a subsequent cleanly unmounted snapshot. The current docs position this as the replacement for the older `runs-on/snapshot@v1` approach. Built-in `rust`/`cargo` mode covers registry and Git dependency inputs; target persistence needs an explicit custom path. The built-in Git mirror speeds checkout transport and does not itself preserve the source worktree's mtimes. ([Sticky-disk documentation](https://runs-on.com/docs/runners/capabilities/sticky-disks/))

Use the [sticky deployment section](../deployments/runs-on/README.md#sticky-disk-options) for configuration and the [versioned failure contract](../reference/runson-cache-and-disk-details.md#sticky-disk-failure-boundary) for the documented/source discrepancy. Keep this managed option distinct from the archive's [custom EBS snapshot action](../approaches/ebs-snapshot.md).

## Evidence boundary

The archive has [direct-S3 compiler-cache measurements](../evidence/cache-strategy-benchmarks.md) and [custom-snapshot evidence](../evidence/rust-cache-vs-snapshot.md). Neither qualifies managed sticky target performance. The existing [sticky Cargo canary](../research/runs-on-sccache/sticky-cargo-canary.yml) remains a research design. Official capability pages serve as the primary source collection here; a provider blog is not required to establish a documented feature.
