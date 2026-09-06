# RunsOn sccache research

Status: Proposed designs and experiments. Use the [current deployment](../../deployments/runs-on/README.md), [sccache approach](../../approaches/sccache.md), and [decisions](../../decisions/README.md) for implementation and adoption. Verified behavior and the dated release refresh live in the [implementation reference](../../reference/compiler-cache-implementation.md); the [planning model](../../evidence/cache-strategy-benchmarks.md#planning-model) is an inference from archived measurements.

This collection explores lower cold-cache overhead, cross-job compiler-object reuse, visible storage failures, and shared-cache ownership. Retrieve the page for the question at hand; copying the existing workflow does not require loading this design.

| Question                                                             | Canonical owner                                                                                                                                        |
| -------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| What should be attempted, in what order, and by whom?                | [Roadmap](roadmap.md): the only task inventory, implementation ownership, dependencies, and open choices.                                              |
| Who installs, configures, starts, drains, and stops the integration? | [Action lifecycle](action-lifecycle.md): setup/post ordering and safe per-invocation fallback.                                                         |
| Who may read, write, and publish shared state?                       | [Trust and publication](trust-and-publication.md): admission, namespace, immutable objects, integrity, readiness, and fencing.                         |
| Which direct-S3 costs should be isolated?                            | [Direct S3 performance](direct-s3-performance.md): instrumentation, transport, compression, memory, and population experiments.                        |
| What would a gateway add?                                            | [Gateway](gateway.md): protocol, coalescing, negative lookup, index representation, write queue, replay, and control API.                              |
| How could local objects survive a runner?                            | [Sticky local tier](sticky-local-tier.md): local ownership, snapshot ordering, lineage, and capacity. Includes the separate unmeasured Cargo workflow. |
| What qualifies another backend?                                      | [Alternative backends](alternative-backends.md): GHA, S3 Express, Redis, Valkey, and Memcached conformance.                                            |
| What must an experiment record and prove?                            | [Validation](validation.md): attribution controls, failure injections, contract tests, and promotion gates.                                            |

## Reading and editing rules

The roadmap links to requirements instead of copying them. Each design owns the contract named above and links to other owners for shared rules. Validation expresses tests against those contracts. Generic sampling, accounting, and cost reporting belong in [Measuring cache performance](../../operations/measuring-cache-performance.md).

Keep proposal status visible on every page because a retrieved page may be read independently. A referenced source observation or measured result retains its own version, date, workload, and limitations; it does not validate the surrounding proposal. Proposed API names and JSON shapes are design sketches.

## Promotion and rollback

Retain a direct-rustc control, previous action/stack revisions, independent switches for each experiment, and a namespace rollback that does not depend on immediate deletion. Promote only after implementation and [validation](validation.md#promotion-gates), then update the canonical evidence and decision through the [maintenance checklist](../../operations/maintenance-checklist.md).
