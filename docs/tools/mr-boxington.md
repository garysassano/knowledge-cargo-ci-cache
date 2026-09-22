# Mr. Boxington

## Summary

| Field         | Value                                                                                                                                                                          |
| ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Status        | Qualified canary candidate; mbx 1.12.0 with action 1.4.0 produced the leading measured portable object-cache result in the controlled workload.                                |
| Use when      | Evaluating target-tree reuse or broader compilation/build-action reuse beyond sccache's eligible compiler invocations.                                                         |
| Main tradeoff | Object mode is the qualified portable choice. Target mode was faster in immediate warm tests but restores mutable Cargo state and remains unqualified for high-churn lineages. |

## Related files

| Page                                                                                           | Purpose                                                                                      |
| ---------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| [Mr. Boxington compared with sccache](../evidence/mr-boxington-vs-sccache.md)                  | Separate same-job and fresh-runner experiments, original versions, timings, and limitations. |
| [Compiler-cache integration diagnosis](../operations/diagnosing-compiler-cache-integration.md) | Distinguishes action startup, archive restore, path mapping, object reuse, and publication.  |
| [Object-mode restore history](../research/mr-boxington-object-restore.md)                      | Measured bottleneck, released directory fix, and remaining upstream design options.          |
| [Ecosystem sources](../reference/vendor-ci-cache-sources.md)                                   | Upstream documentation, action, limits, and vendor claims.                                   |

## Design

Mr. Boxington (`mbx`) records build actions and their inputs, then restores eligible results when the action and observed inputs match. Upstream describes reuse for Rust compilation, supported Cargo work, and some native compilation/linking. Its coverage differs from sccache; compare correctness, actual commands avoided, and complete job time rather than treating the two tools' hit counters as equivalent. See [how it works](https://mr-boxington.jdx.dev/how-it-works) and [caching limits](https://mr-boxington.jdx.dev/limits).

Treat it as an alternative compiler wrapper. Do not stack it with sccache or another `RUSTC_WRAPPER` owner without a documented and tested composition. Install the required toolchain first and ensure the measured Cargo commands actually execute through `mbx`.

## Version and backend boundary

The latest controlled retest used mbx 1.12.0 with action 1.3.1 and action 1.4.0 in the same workflow batch. The major reference `jdx/mr-boxington-action@v1` resolved to action 1.4.0 commit `867fc530` on 2026-09-16. Keep the action on its supported major reference unless a repository's action-pinning policy requires an immutable commit; selecting mbx's `version` input is a separate choice.

The [v1.4.0 action metadata](https://github.com/jdx/mr-boxington-action/blob/v1.4.0/action.yml) defaults to `backend: github` and `github-cache-mode: target`. Target mode caches a pruned Cargo target tree, Cargo registry/git state, and action-managed tooling. It disables mbx target views and object-backed native-link caching for that transport. With mbx 1.12.0 or newer, object mode exports the selected action/object closure as a directory so `actions/cache` performs the only archive layer; older action versions transported an inner tar. A clean-target portable-object experiment must explicitly select `github-cache-mode: objects`; otherwise it compares a different mechanism.

The backend and payload-mode settings describe different layers:

| Configuration                                       | Data path                                                                                    | Role of `github-cache-mode`         |
| --------------------------------------------------- | -------------------------------------------------------------------------------------------- | ----------------------------------- |
| `backend: github` with `github-cache-mode: objects` | Exported MBX action/object closure transported by an Actions-cache-compatible backend        | Selects the portable object payload |
| `backend: github` with `github-cache-mode: target`  | Pruned Cargo target and Cargo input state transported by an Actions-cache-compatible backend | Selects the target-state payload    |
| `backend: server`                                   | Native MBX protocol to an `mr-boxington-cache` endpoint                                      | Not used                            |
| `backend: local` with `MBX_REMOTE_URL=s3://...`     | Native MBX direct-S3 object remote configured through environment variables                  | Not used                            |
| `backend: local` without a remote                   | Runner-local MBX store only                                                                  | Not used                            |

A RunsOn integration should therefore configure a backend such as a managed server or direct S3. It does not need separate RunsOn settings for GitHub `objects` and `target`; those remain choices owned by `jdx/mr-boxington-action` when `backend: github`. Target mode already travels through RunsOn Magic Cache when that service replaces the GitHub Actions cache endpoint.

The existing `jdx/mr-boxington-cache` server is materially different from direct S3. It supports S3-backed blob storage through the standard AWS SDK credential chain, GitHub OIDC namespace grants, zstd-compressed transfers, streaming blob packs, batched lookups, action promises, PostgreSQL metadata, horizontal replicas, and Prometheus metrics. Direct S3 uses raw per-object S3 operations without those protocol features and currently requires explicit access-key environment variables. See the [remote-backend research](../research/mr-boxington-remote-backends.md).

Record the mbx binary version, action revision, backend, payload mode where applicable, cache generation or namespace, trust/save policy, target path, and container path mapping in every measurement.

### Release changes considered in the retest

The September 15 review covered the releases between the original 1.3.0 trial and 1.11.1 rather than treating the version bump as sufficient by itself. Changes material to this workload included:

- [mbx 1.3.2](https://github.com/jdx/mr-boxington/releases/tag/v1.3.2): shared predictions across Cargo commands.
- [mbx 1.4.0](https://github.com/jdx/mr-boxington/releases/tag/v1.4.0): stable handling for bind-mounted or symlinked Cargo registry paths, plus Clippy and nested-Cargo fixes.
- [mbx 1.4.1](https://github.com/jdx/mr-boxington/releases/tag/v1.4.1): grouped exports preserved through collection.
- [mbx 1.8.0](https://github.com/jdx/mr-boxington/releases/tag/v1.8.0): Cargo workspace-state attachments in object exports.
- [mbx 1.10.1](https://github.com/jdx/mr-boxington/releases/tag/v1.10.1): predictions retained from every exported command.
- [action 1.3.0](https://github.com/jdx/mr-boxington-action/releases/tag/v1.3.0): target-tree transport became the default GitHub payload.
- [action 1.3.1](https://github.com/jdx/mr-boxington-action/releases/tag/v1.3.1): imported objects are preserved on hosted runners.
- [mbx 1.12.0](https://github.com/jdx/mr-boxington/releases/tag/v1.12.0): directory-form bundles and parallel import/export verification.
- [action 1.4.0](https://github.com/jdx/mr-boxington-action/releases/tag/v1.4.0): directory-form GitHub cache transport for object mode when mbx is 1.12.0 or newer.

Use normal GitHub Actions `uses:` execution so the action receives its runtime context. Shell-invoking a bundled action is a diagnostic technique and does not establish supported GitHub-cache behavior. An exact `cache-hit` output establishes an archive match, not reusable build results.

## Qualification procedure

1. Fix source state, compiler identity, runner/container image, workload, concurrency, and target path; use the [measurement procedure](../operations/measuring-cache-performance.md).
2. Verify supported commands and correctness against a direct-compiler control, then measure local cold and warm runs separately from fresh-runner restore/export.
3. For a compiler-object trial, remove target state between runs while retaining only the intended object store. Pin an explicit object payload mode on action versions whose default is a target archive.
4. Record avoided invocations, rejected predictions, store bytes/objects, restore and export time, and job wall time. Diagnose stable-path errors before attributing a weak result to cache transport.
5. Repeat changed-source, invalidation, concurrent-reader/writer, outage, cancellation, and clean-fallback scenarios before changing the [experimental decision](../decisions/README.md).

## Limitations and evidence

The same-job experiment showed competitive local reuse. The original fresh-runner Docker experiment on mbx 1.3.0 restored the exact action cache but rejected Cargo registry paths. The [maintainer confirmed the mapping mechanism](https://github.com/jdx/mr-boxington/discussions/258#discussioncomment-18240056), and [PR #259](https://github.com/jdx/mr-boxington/pull/259) added the dedicated registry mapping. The mbx 1.11.1 retest no longer exhibited that failure: object mode produced 771 hits and zero misses across Clippy and nextest.

In the controlled mbx 1.12.0 comparison, action 1.4.0 object mode restored the same 773-action, 4,914-object closure as action 1.3.1 but reduced import from 5.97 seconds to 0.26 seconds. It finished at 3m01s warm overall, fifteen seconds ahead of action 1.3.1 and seven seconds ahead of sccache. Target mode finished at 2m41s under both action versions. A later same-batch comparison measured action object mode at 3m01s warm versus 3m06s for native S3; native S3 downloaded 3.0 GiB during Clippy while the action restored a 626 MB compressed archive. Keep the complete setup and single-run limitations in [the evidence page](../evidence/mr-boxington-vs-sccache.md).

Target mode's short exact-warm result does not establish safe long-term behavior. Its current save cleanup removes final products and entries whose package names are absent from current Cargo metadata, but keeps every hash variant matching a current package in `build`, `.fingerprint`, and `deps`. It has no byte limit, generation limit, or age-based pruning. This is not proof that it will reproduce the exact `Swatinem/rust-cache` incident, but it leaves the same class of copy-forward growth plausible in frequently changing CI. The production whole-target lineage recorded here grew from 206 MB to 13.89 GB in under five days and later reached 17.82 GB. Qualify target mode with a multi-generation changed-source soak test before using it for that workload.

## Decision

Use mbx object mode with mbx 1.12.0 and action 1.4.0 or newer as a qualified portable clean-target canary alongside sccache under decision D9. Keep target mode to narrow, stable, monitored workloads until archive size stays bounded through representative source, feature, dependency, and build-script changes. Treat native S3 and the existing cache server as separate backend candidates; the current native-S3 measurement did not beat action object mode, while the server has not yet been benchmarked here.
