# Mr. Boxington

## Summary

| Field         | Value                                                                                                                                             |
| ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| Status        | Experimental alternative; current target and object modes were retested on fresh runners, while sccache remains the portable clean-target choice. |
| Use when      | Evaluating target-tree reuse or broader compilation/build-action reuse beyond sccache's eligible compiler invocations.                            |
| Main tradeoff | Target mode is fast but path/layout-sensitive; object mode is portable but currently pays eager archive import and full-closure validation.       |

## Related files

| Page                                                                                           | Purpose                                                                                      |
| ---------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| [Mr. Boxington compared with sccache](../evidence/mr-boxington-vs-sccache.md)                  | Separate same-job and fresh-runner experiments, original versions, timings, and limitations. |
| [Compiler-cache integration diagnosis](../operations/diagnosing-compiler-cache-integration.md) | Distinguishes action startup, archive restore, path mapping, object reuse, and publication.  |
| [Object-mode restore opportunities](../research/mr-boxington-object-restore.md)                | Measured bottleneck, local prototype, and unimplemented upstream design options.             |
| [Ecosystem sources](../reference/vendor-ci-cache-sources.md)                                   | Upstream documentation, action, limits, and vendor claims.                                   |

## Design

Mr. Boxington (`mbx`) records build actions and their inputs, then restores eligible results when the action and observed inputs match. Upstream describes reuse for Rust compilation, supported Cargo work, and some native compilation/linking. Its coverage differs from sccache; compare correctness, actual commands avoided, and complete job time rather than treating the two tools' hit counters as equivalent. See [how it works](https://mr-boxington.jdx.dev/how-it-works) and [caching limits](https://mr-boxington.jdx.dev/limits).

Treat it as an alternative compiler wrapper. Do not stack it with sccache or another `RUSTC_WRAPPER` owner without a documented and tested composition. Install the required toolchain first and ensure the measured Cargo commands actually execute through `mbx`.

## Version and backend boundary

The latest archived retest used mbx 1.11.1 and the major action reference `jdx/mr-boxington-action@v1`, which resolved to action 1.3.1 on 2026-09-15. The pending action 1.3.2 release contained dependency and release-bookkeeping changes only, so it did not alter the tested runtime behavior. Keep the action on its supported major reference unless a repository's action-pinning policy requires an immutable commit; selecting mbx's `version` input is a separate choice.

The [v1.3.1 action metadata](https://github.com/jdx/mr-boxington-action/blob/v1.3.1/action.yml) defaults to `backend: github` and `github-cache-mode: target`. Target mode caches a pruned Cargo target tree, Cargo registry/git state, and action-managed tooling. It disables mbx target views and object-backed native-link caching for that transport. Object mode exports the selected deduplicated mbx action/object closure to a tar, lets `actions/cache` archive that tar, then imports and validates the restored closure before the build. A clean-target portable-object experiment must explicitly select `github-cache-mode: objects`; otherwise it compares a different mechanism.

Local and server backends remain separate experiments. Record the mbx binary version, action revision, payload mode, cache generation, namespace, trust/save policy, target path, and container path mapping in every measurement.

### Release changes considered in the retest

The September 15 review covered the releases between the original 1.3.0 trial and 1.11.1 rather than treating the version bump as sufficient by itself. Changes material to this workload included:

- [mbx 1.3.2](https://github.com/jdx/mr-boxington/releases/tag/v1.3.2): shared predictions across Cargo commands.
- [mbx 1.4.0](https://github.com/jdx/mr-boxington/releases/tag/v1.4.0): stable handling for bind-mounted or symlinked Cargo registry paths, plus Clippy and nested-Cargo fixes.
- [mbx 1.4.1](https://github.com/jdx/mr-boxington/releases/tag/v1.4.1): grouped exports preserved through collection.
- [mbx 1.8.0](https://github.com/jdx/mr-boxington/releases/tag/v1.8.0): Cargo workspace-state attachments in object exports.
- [mbx 1.10.1](https://github.com/jdx/mr-boxington/releases/tag/v1.10.1): predictions retained from every exported command.
- [action 1.3.0](https://github.com/jdx/mr-boxington-action/releases/tag/v1.3.0): target-tree transport became the default GitHub payload.
- [action 1.3.1](https://github.com/jdx/mr-boxington-action/releases/tag/v1.3.1): imported objects are preserved on hosted runners.

The pending action 1.3.2 release reviewed on 2026-09-15 contained dependency updates and release bookkeeping, with no runtime source change affecting this comparison.

Use normal GitHub Actions `uses:` execution so the action receives its runtime context. Shell-invoking a bundled action is a diagnostic technique and does not establish supported GitHub-cache behavior. An exact `cache-hit` output establishes an archive match, not reusable build results.

## Qualification procedure

1. Fix source state, compiler identity, runner/container image, workload, concurrency, and target path; use the [measurement procedure](../operations/measuring-cache-performance.md).
2. Verify supported commands and correctness against a direct-compiler control, then measure local cold and warm runs separately from fresh-runner restore/export.
3. For a compiler-object trial, remove target state between runs while retaining only the intended object store. Pin an explicit object payload mode on action versions whose default is a target archive.
4. Record avoided invocations, rejected predictions, store bytes/objects, restore and export time, and job wall time. Diagnose stable-path errors before attributing a weak result to cache transport.
5. Repeat changed-source, invalidation, concurrent-reader/writer, outage, cancellation, and clean-fallback scenarios before changing the [experimental decision](../decisions/README.md).

## Limitations and evidence

The same-job experiment showed competitive local reuse. The original fresh-runner Docker experiment on mbx 1.3.0 restored the exact action cache but rejected Cargo registry paths. The [maintainer confirmed the mapping mechanism](https://github.com/jdx/mr-boxington/discussions/258#discussioncomment-18240056), and [PR #259](https://github.com/jdx/mr-boxington/pull/259) added the dedicated registry mapping. The mbx 1.11.1 retest no longer exhibited that failure: object mode produced 771 hits and zero misses across Clippy and nextest.

In the corrected retest, target mode was the fastest measured option at 2m36s warm overall. Object mode completed the native Cargo section four seconds faster than sccache but finished seven seconds slower overall because it restored an approximately 625 MiB outer cache, materialized a 3.0 GiB inner tar, and spent 6.33 seconds importing 4,914 objects and 773 actions. Keep the complete setup and single-run limitation in [the evidence page](../evidence/mr-boxington-vs-sccache.md).

## Decision

Use this as a qualified experimental alternative under decision D9. Keep sccache for portable clean-target object reuse in the measured workflow. Consider target mode separately when restoring Cargo target state fits the checkout, target-path, and container model. Revisit object mode if upstream removes or hides enough eager restore/import work to change representative end-to-end results.
