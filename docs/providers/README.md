# Providers and their CI cache strategies

This section owns dated provider capabilities, deployment boundaries, and first-party documentation/blog links. Start with the [strategy decision flow](../approaches/README.md), then choose a provider profile. Tool selection belongs in [sccache vs Mr. Boxington vs Kache](../tools/compiler-caches.md); reusable RunsOn configuration stays in the [deployment map](../deployments/runs-on/README.md).

Reviewed: 2026-09-06. Coverage includes runner providers, self-hosted cache designs, and relevant build platforms. Earthly's articles and Depot CI's cache-disk beta are explicitly distinguished from GitHub Actions runner features. This is a maintained coverage map, not an assertion that every provider offers every strategy.

| Provider or project         | Strategies documented by the linked first-party sources                                                                   | Coverage and qualification                                                           |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| [RunsOn](runs-on.md)        | AWS-hosted Actions archive backend, direct S3 compiler cache, managed EBS sticky disks, Git mirrors, persistent BuildKit. | Existing archive/direct-S3 evidence; managed sticky paths remain unmeasured here.    |
| [Namespace](namespace.md)   | Native cache volumes and a separate WebDAV sccache integration.                                                           | Documentation and Rust case study; no local provider benchmark.                      |
| [Depot](depot.md)           | WebDAV compiler cache, persistent container builders, Rust recipes; native cache disks in **Depot CI beta**.              | Platform-specific sources; no local provider benchmark.                              |
| [Blacksmith](blacksmith.md) | Transparent archive transport, snapshot-backed sticky volumes, persistent container-builder state.                        | Docs and cache/Docker articles; no local provider benchmark.                         |
| [WarpBuild](warpbuild.md)   | Archive clients, upstream rust-cache integration, Cloud Ubuntu VM snapshots, sccache guides.                              | Snapshot feature excludes BYOC, Windows, and macOS in reviewed docs; untested here.  |
| [Ubicloud](ubicloud.md)     | Transparent archive-cache backend with upstream actions.                                                                  | Docs and design article; old provider forks retained as historical links.            |
| [Actuated](actuated.md)     | Self-hosted S3-compatible archive cache near runners, with explicit client substitution; Git object caching.              | Deployment guide and case studies; no Rust benchmark here.                           |
| [Earthly](earthly.md)       | BuildKit cache mounts, sccache, and cargo-chef dependency layers.                                                         | Technical article collection, not a claim about current hosted-service availability. |
| [BuildJet](buildjet.md)     | Historical provider archive-cache wrapper.                                                                                | No current dedicated Rust/sccache article identified in this review.                 |

## Applicability to this repository

The [implementation scope](../README.md#scope-and-applicability) is open-source components used directly in GitHub Actions. Provider-managed services in this index are source material unless an independently usable open-source implementation is identified and qualified. A public action repository establishes the client interface, not the licensing or availability of the remote service. Depot CI-specific cache disks and Earthly-specific build examples are retained as other-platform references; their reusable mechanisms can inform an implementation within GitHub Actions.

Classify source availability at the component boundary. [Ubicloud](ubicloud.md) publishes an AGPL-3.0 cloud implementation as well as offering a managed service. [RunsOn](runs-on.md) has MIT action/template assets with commercially licensed server/agent components. The other linked hosted integrations remain provider-dependent references unless a usable open-source backend is identified. Unknown backend source availability is not proof of closed-source status.

The existing RunsOn deployment is retained as the concrete infrastructure mapping behind archived measurements. It is not an entirely open-source control-plane recommendation, and adding provider profiles does not select a new deployment.

## How to use a provider article

Identify the reused state, transport, compute location, cache state, and tested workload before applying a speed claim. A faster runner with a warm cache changes two variables; a Docker layer hit and a direct Cargo build do different work. Translate the article into a controlled experiment using [cache layers](../concepts/cache-layers.md) and the [measurement procedure](../operations/measuring-cache-performance.md).

A capability omitted from this table is **not assessed**, rather than proven unavailable. Profiles mark explicit unsupported configurations and historical-only coverage. Preserve those distinctions when adding providers, refreshing links, or answering from retrieved snippets. Core upstream projects, GitHub cache semantics, and maintained action forks remain in [ecosystem sources](../reference/vendor-ci-cache-sources.md).
