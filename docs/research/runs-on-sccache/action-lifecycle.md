# Proposed sccache action lifecycle

Status: Proposed and untested integration work. This page specifies requirements; it does not describe a released RunsOn feature. Use [the research index](README.md) for scope, sequencing, and the [version refresh](../../reference/compiler-cache-implementation.md#release-refresh-2026-09-06).

## Ownership

This page owns setup, configuration identity, quiescence, drain, and per-invocation fallback for both direct and gateway modes. [Trust and publication](trust-and-publication.md) owns authority; [validation](validation.md) owns tests. RunsOn should offer one lifecycle owner for the supported integration. The owner may call an external installer internally, but users should not need two unrelated actions whose environment and post steps can race.

The supported interface should make these choices explicit:

| Input or policy             | Purpose                                                                                |
| --------------------------- | -------------------------------------------------------------------------------------- |
| Backend mode                | `off`, direct S3, gateway, native GHA canary, or a future supported backend            |
| Binary source               | RunsOn-managed exact version, externally installed exact version, or development build |
| Binary version and checksum | Prevent movable or substituted binaries                                                |
| Access mode                 | Disabled, read-only, canonical writer, or private overlay writer                       |
| Namespace schema            | Explicit versioned namespace contract                                                  |
| Failure mode                | Fallback to direct `rustc` or strict setup failure                                     |
| Daemon mode                 | Default server mode unless a measured alternative is selected                          |
| Setup timeout               | Bound install, probe, and backend preflight                                            |
| Drain timeout               | Bound post-job write completion                                                        |
| Stats and summary           | JSON artifact, summary, or disabled only by deliberate policy                          |
| Local tier                  | Disabled, ephemeral, or supported sticky mode                                          |

Workflow-controlled values may request a mode, but the action must derive actual authority from verified runner and job identity. An untrusted event cannot turn a read-only credential into a writer by setting an input.

## Setup Transaction

The setup sequence should be:

1. Resolve RunsOn platform identity, numeric GitHub owner and repository IDs, event trust class, OS, architecture, runner identity, and requested cache mode.
2. Reject missing, conflicting, or unsafe identity before creating a shared namespace.
3. Resolve the allowed access mode from remote policy.
4. Verify the selected or externally supplied binary against the [binary supply-chain policy](trust-and-publication.md#binary-supply-chain).
5. Build a canonical configuration object and a non-secret fingerprint of every setting that changes storage behavior.
6. Reject or clear inherited `SCCACHE_CLIENT_SIDE=1` for the supported default-server baseline before fingerprinting; keep client-side modes as isolated experiments because the measured client-side trials did not improve warm performance.
7. Detect a running daemon, query its binary and configuration fingerprint when supported, and stop or reject it if the fingerprint differs.
8. Allocate a private local port or socket and a runtime directory that is not persisted with cache data.
9. Start the daemon explicitly.
10. Probe the daemon control path.
11. Perform a backend preflight according to access mode without creating reusable compiler objects.
12. Reset statistics with `sccache --zero-stats`.
13. Record the prior `CARGO_INCREMENTAL` state, reject an explicit nonzero request in strict mode, and prepare `CARGO_INCREMENTAL=0` for cache-enabled execution.
14. Commit backend variables, `CARGO_INCREMENTAL=0`, and `RUSTC_WRAPPER=sccache` atomically only after every required setup step succeeds.
15. Record a redacted setup event and monotonic timing markers.
16. On non-strict setup failure, clear every wrapper and backend variable owned by the integration, restore the prior incremental-compilation state, report the reason, and continue with direct `rustc`.

The backend probe should use a dedicated health key or control API, not an unbounded namespace listing. Read-only jobs should verify a known metadata object or perform a bounded known-key read. Writer probes should write a unique short-lived health object only under a dedicated probe prefix with lifecycle cleanup, or use a broker/gateway health API that does not modify the compiler namespace.

## Post Transaction

The post sequence should run even when the workload fails:

1. Capture the daemon configuration fingerprint and integration mode for correlation.
2. Optionally capture a pre-drain `sccache --show-stats --stats-format=json` snapshot, label it preliminary, and retain it only to diagnose work that finishes during drain.
3. Move the integration from `OPEN` to `QUIESCING`, seal admission of new compiler producers, and allow already-admitted invocations to finish their one compiler attempt.
4. Wait for the active producer and request count to reach zero, then move to `DRAINING`, disable backfills, capture a write watermark, and close new write admission.
5. Drain accepted writes through the watermark up to the configured deadline when the implementation supports a real drain.
6. Capture the final compiler statistics and atomically record committed, rejected-policy, failed, deferred, and unfinished writes and the exact watermark reached. A future atomic drain-and-stats or stop-with-stats operation should combine this observation with the lifecycle transition.
7. Request daemon shutdown unconditionally and move the integration to `CLOSED`.
8. Verify that the expected process and local socket are gone.
9. Flush and close gateway telemetry.
10. Publish a redacted job summary and machine-readable measurement records.
11. Restore the prior `CARGO_INCREMENTAL` state when the action owns that mutation.
12. Run any sticky-disk snapshot publication only after cache data is quiescent and the publication fence remains valid.

Until upstream supports an explicit drain, the action must not describe `sccache --stop-server` as a flush. Direct single-S3 writes are normally awaited per compilation; default multilevel background writes and backfills are not. Statistics captured with released behavior are therefore compiler statistics rather than proof of final remote-write completion, and any write-completeness fields remain non-final and ineligible for readiness.

Plain WebDAV does not identify compiler-invocation boundaries. Exact quiescence therefore requires either a stable wrapper shim or an upstream control protocol that registers each producer before it can emit object requests.

## Fallback Semantics

Fallback is safe only before compilation or at a clearly defined cache lookup boundary.

- If installation, identity, IAM, daemon startup, or backend preflight fails, clear `RUSTC_WRAPPER`, restore the prior `CARGO_INCREMENTAL` state, and compile directly.
- If the backend is unavailable during a lookup, the cache layer may return a fast typed miss under a configured degrade policy.
- If a wrapper or gateway fails after a compiler process has begun and the outcome is ambiguous, do not rerun the full compilation automatically.
- Prefer a stable wrapper shim that selects `sccache` or direct `rustc` independently for each new compiler invocation, so an already-running Cargo process does not depend on environment mutation.
- If a job explicitly requests nonzero Rust incremental compilation, strict mode fails and fallback mode disables `sccache`; the action does not silently override an incompatible user request.
- A strict mode may fail setup for a trusted population workflow whose purpose is to produce cache state, but ordinary CI should prefer direct-compiler continuity.

## Stale Daemon Prevention

`sccache` storage is created at daemon startup, so environment changes after startup are insufficient. The integration needs one of:

- An upstream daemon API that reports a canonical backend fingerprint.
- A RunsOn wrapper process that owns daemon creation and records PID, binary hash, port, start time, and configuration fingerprint in a private runtime directory.
- A conservative stop-before-start policy on ephemeral runners.

The runtime directory must not be placed in sticky `SCCACHE_DIR`; persisting sockets, PIDs, tokens, or presigned URLs creates stale-state and credential risks.

## Proposed Action Output

A concise summary should include:

| Field              | Example class                                                                                                |
| ------------------ | ------------------------------------------------------------------------------------------------------------ |
| Integration status | enabled, bypassed-empty, fallback, strict-failed                                                             |
| Binary             | version and checksum identifier                                                                              |
| Backend            | direct S3, gateway, native GHA canary                                                                        |
| Access             | read-only, canonical writer, private overlay                                                                 |
| Namespace          | redacted stable digest and schema version                                                                    |
| Requests           | compile, cacheable, hit, miss, and non-cacheable by reason and output class                                  |
| Errors             | auth, timeout, throttle, corruption, and backend                                                             |
| Writes             | attempted, committed, rejected-policy, skipped-policy, failed, deferred, unfinished                          |
| Latency            | setup, lookup, materialization, drain, and shutdown p50, p90, p95, p99, and maximum when sample size permits |
| Data               | downloaded and uploaded bytes                                                                                |
| Lifecycle          | setup, drain, and shutdown duration                                                                          |
| Outcome            | net wall-time delta against paired control when available                                                    |

The summary must not print bucket names, full prefixes, repository or branch text, runtime tokens, cloud account identifiers, or signed URLs.
