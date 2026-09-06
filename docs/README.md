# Documentation

The documentation is organized by reader need first, then by ownership. Put information in one category and link to it from the others instead of repeating it. This page owns the full reader-routing table and page conventions; category indexes own their focused page lists.

## Scope and applicability

Practical implementations in this repository target **open-source components running directly in GitHub Actions**, including container builds invoked by a GitHub Actions job. Keep the implementation, action/client, storage backend, and provider control plane distinct: an open-source wrapper does not make a hosted service open source, and a paid infrastructure dependency does not by itself determine the license of the client code.

Research coverage is deliberately broader. Preserve useful documentation from commercial/closed providers, other CI/build platforms, upstream issues, experimental implementations, and unstable Cargo features. Record the transferable mechanism and the dependency that prevents using that exact implementation in the practical scope. Source inclusion is not adoption, endorsement, or a request to migrate CI platforms.

For each new technique, identify applicability (direct GitHub Actions implementation, provider-dependent reference, other-platform reference, or unstable experiment), evidence class, reviewed version/date, constraints, and the primary sources. Keep untested candidates visible. The [provider index](providers/README.md) owns vendor coverage; [research](research/README.md) owns unimplemented designs and unstable-feature qualification. Expand these collections as new mechanisms or evidence appear, without claiming the catalog is exhaustive.

## Reader Routes

| Task                                                                | Start with                                                                                 | Then use                                                                |
| ------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------- |
| Get the current recommendation quickly                              | [Quickstart](quickstart.md)                                                                | [Decisions](decisions/README.md)                                        |
| Choose a RunsOn cache or disk shape                                 | [RunsOn Deployment Map](deployments/runs-on/README.md)                                     | The linked canary or workflow example                                   |
| Compare sccache, Mr. Boxington, and Kache                           | [Compiler-cache comparison](tools/compiler-caches.md)                                      | [Measured comparison](evidence/mr-boxington-vs-sccache.md)              |
| Diagnose ineffective compiler-cache restores                        | [Compiler-cache integration](operations/diagnosing-compiler-cache-integration.md)          | Versioned sources and the linked experiment                             |
| Plan unimplemented cache improvements                               | [Research](research/README.md)                                                             | [RunsOn performance roadmap](research/runs-on-sccache/roadmap.md)       |
| Choose a cache approach                                             | [Approaches](approaches/README.md)                                                         | The linked approach page and workflow example                           |
| Measure cache phases or compare runner resources                    | [Measuring Cache Performance](operations/measuring-cache-performance.md)                   | [Cache Measurement JSONL Schema](reference/cache-measurement-schema.md) |
| Debug unexpected recompilation                                      | [Diagnosing Cargo Rebuilds In CI](operations/diagnosing-rebuilds.md)                       | [Cargo Freshness Model](concepts/cargo-freshness-model.md)              |
| Maintain or change a conclusion                                     | [Maintenance Checklist](operations/maintenance-checklist.md)                               | [Evidence](evidence/README.md), then [Decisions](decisions/README.md)   |
| Review Rust CI cache projects, providers, or claims                 | [Providers](providers/README.md) and [core projects](reference/vendor-ci-cache-sources.md) | The linked approach, evidence, or deployment page                       |
| Verify sccache, OpenDAL, or RunsOn implementation behavior          | [Implementation reference](reference/compiler-cache-implementation.md)                     | The pinned source and dated release refresh                             |
| Audit dense technical detail                                        | [Reference](reference/README.md)                                                           | The canonical page that links to it                                     |
| Identify tools such as sccache, Kache, Mr. Boxington, or cargo-chef | [Tools](tools/README.md)                                                                   | The relevant profile and comparison                                     |
| Map a strategy to S3/GHA, EBS, local NVMe, or tmpfs                 | [Storage topologies](concepts/storage-topologies.md)                                       | [Provider profiles](providers/README.md) and the selected deployment    |
| Follow all CI strategy families and decision diagrams               | [Strategy map](approaches/README.md)                                                       | [Cache layers](concepts/cache-layers.md), then the focused approach     |
| Track Cargo freshness beyond mtimes                                 | [Cargo freshness alternatives](research/cargo-freshness-alternatives.md)                   | Linked nightly documentation and stabilization trackers                 |

## Canonical Ownership

| Section     | Owns                                                                                   | Entry point                                            |
| ----------- | -------------------------------------------------------------------------------------- | ------------------------------------------------------ |
| Decisions   | Current conclusions, statuses, and superseded conclusions                              | [Decisions](decisions/README.md)                       |
| Tools       | Named implementations, supported cache units, integration limits, and tool comparisons | [Tools](tools/README.md)                               |
| Approaches  | Strategy selection, combinations, and tradeoffs                                        | [Approaches](approaches/README.md)                     |
| Providers   | Dated capabilities, applicability, first-party docs/blogs, and coverage gaps           | [Providers](providers/README.md)                       |
| Deployments | Platform-specific realizations, prerequisites, and trust boundaries                    | [RunsOn Deployment Map](deployments/runs-on/README.md) |
| Operations  | Procedures, configuration, diagnosis, and maintenance                                  | [Operations](operations/README.md)                     |
| Concepts    | Stable mental models and cache semantics                                               | [Concepts](concepts/README.md)                         |
| Evidence    | Test questions, setup, observations, interpretation, and limitations                   | [Evidence](evidence/README.md)                         |
| Research    | Proposed designs, experiments, dependencies, and promotion criteria                    | [Research](research/README.md)                         |
| Reference   | Dense details that support shorter first-read pages                                    | [Reference](reference/README.md)                       |

## Evidence and retrieval

Use [Decisions](decisions/README.md) to identify the adopted or experimental status, then retrieve the relevant approach and evidence. Treat measured results, pinned implementation observations, reasoned inferences, and proposed designs as different claim classes. Always carry a measurement's versions, workload, cache state, sample count, and limitations into an answer. Use [provider profiles](providers/README.md) for first-party documentation and blog posts and [tool profiles](tools/compiler-caches.md) for explicitly untested products; their claims do not establish local benchmark results.

Use the [AGENTS ingestion checklist](../AGENTS.md#ingesting-new-information) when adding or refreshing material.

Short status and version caveats may repeat so independently retrieved pages remain interpretable. Complete task inventories, procedures, result tables, and behavioral contracts have one owner. Within research, use the [ownership map](research/runs-on-sccache/README.md) and link to shared contracts rather than maintaining another checklist.

## Page Conventions

| Page type             | Expected shape                                                                                                                 |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| Landing or quickstart | Current answer, reader path, compact links                                                                                     |
| Decision              | Current conclusion, status, basis, change procedure                                                                            |
| Tool                  | Applicability/status, source version, reusable unit, storage/backend support, integration limits, evidence, and strategy links |
| Approach              | Status summary, use/do-not-use guidance, design, settings, limitations, evidence                                               |
| Provider              | Scope and review date, source collection, transferable strategies, platform/license boundaries, and evidence limits            |
| Deployment            | Ownership statement, platform-specific deltas, workflow shape, maintenance, related pages                                      |
| Operation             | Purpose, recommended configuration/procedure, ordering, caveats, references                                                    |
| Concept               | Scope, short model, next links, reference links                                                                                |
| Evidence              | Question, test setup/progression, observations, interpretation, limitations, implications                                      |
| Reference             | Dense tables, examples, historical notes, and official links                                                                   |
| Research              | Explicit proposal status, versioned basis, focused design or experiment, dependencies, validation, and promotion requirements  |
