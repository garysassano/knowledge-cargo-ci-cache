# RunsOn sccache research

Status: Proposed designs and experiments. The [current RunsOn deployment](../../deployments/runs-on/README.md), [sccache approach](../../approaches/sccache.md), and [decisions](../../decisions/README.md) remain the implementation and adoption entry points. Source refresh: 2026-09-06; archived measurements retain their original versions and dates.

This collection explores how to reduce cold-cache overhead, retain useful compiler objects across jobs, make storage failures visible, and improve shared-cache ownership. Load the page for the question at hand; reading the entire design is unnecessary for copying the existing workflow.

| Question                                                                   | Page                                              | Claim status                                                                                     |
| -------------------------------------------------------------------------- | ------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| What did the tested binaries do, and what changed upstream?                | [Implementation baseline](baseline.md)            | Pinned source observations, dated release refresh, and explicitly limited timing model           |
| What should be tried first?                                                | [Performance roadmap](roadmap.md)                 | Proposed priorities and completion tests                                                         |
| Who owns installation, daemon configuration, fallback, and shutdown?       | [Action lifecycle](action-lifecycle.md)           | Proposed action contract                                                                         |
| How should credentials, immutable writes, readiness, and generations work? | [Trust and publication](trust-and-publication.md) | Proposed shared-cache contract                                                                   |
| Which direct-S3 costs should be isolated?                                  | [Direct S3 performance](direct-s3-performance.md) | Proposed instrumentation and tuning experiments                                                  |
| What would a WebDAV gateway add?                                           | [Gateway](gateway.md)                             | Untested protocol, request, write, and drain design                                              |
| How could local compiler objects survive a runner?                         | [Sticky local tier](sticky-local-tier.md)         | Untested persistence and publication design                                                      |
| What blocks GHA, S3 Express, Redis, Valkey, or Memcached trials?           | [Alternative backends](alternative-backends.md)   | Integration qualification; distinguish current upstream fixes from the tested sccache dependency |
| What evidence is needed before promotion?                                  | [Validation](validation.md)                       | Measurement, failure, cost, and provisional acceptance contract                                  |
| Which repository would implement each change?                              | [Implementation map](implementation.md)           | Proposed ownership, dependencies, and unresolved choices                                         |

## Sequencing

Start with repeatable direct-compiler and default-server S3 controls, then measure retention, population policy, setup cost, compression, and concurrency. Complete action lifecycle and write-accounting work before relying on readiness publication or sticky compiler-cache state. A sticky local tier may be tested before a gateway when sccache itself can provide exclusive ownership and reliable drain; a gateway-managed tier depends on those gateway contracts. Follow the [roadmap](roadmap.md) for the complete task inventory.

Prototype a gateway as a read-only WebDAV pass-through before adding negative lookup metadata, request coalescing, local objects, remote writes, packs, or prefetch. WebDAV is a storage protocol; it can still be used with normal sccache server mode. Each optimization needs its own comparison with direct S3.

## Invariants

- Setup exports the wrapper only after the intended binary, daemon configuration, and backend are ready; fallback never starts a second compiler for an ambiguous invocation.
- Workflow inputs, branch names, local sockets, and cache prefixes do not grant remote authority. A loopback service is not a security boundary against root-capable job code.
- Acknowledged canonical writes must be remotely committed. A post hook, local spool, or `--stop-server` call alone does not prove that background work finished.
- Publication uses a trusted writer and an external lease with a fencing token; local markers and locks establish consistency within a volume, not authority across restored clones.
- Byte checksums do not prove that a compiler result is authentic. Lower-trust objects never become canonical through backfill or replay.
- Missing, failed, cancelled, or incomplete populations cannot publish readiness. Negative indexes may suppress origin reads only when they completely describe a sealed generation.
- Every tier has explicit resource limits, telemetry, cost ownership, and independent rollback.

## Rollback and promotion

Keep a known-good direct-rustc workflow, previous action and stack revisions, and independent switches for the gateway, index, sticky tier, and backend. Abandon a namespace to roll back without waiting for deletion. Numeric performance thresholds in [Validation](validation.md) are proposed acceptance budgets, not measured guarantees. Change a current decision or copyable deployment only after implementation and evidence pass the [maintenance procedure](../../operations/maintenance-checklist.md).
