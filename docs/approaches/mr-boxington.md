# Mr. Boxington

## Summary

| Field         | Value                                                                                                                                 |
| ------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| Status        | Experimental alternative; same-job reuse measured, fresh-runner Docker integration limited by path mapping                            |
| Use when      | Evaluating compiler and build-action reuse beyond the workload covered by the existing sccache canary.                                |
| Main tradeoff | Reusable results depend on tracked inputs, supported commands, stable path mappings, backend configuration, and correct cache export. |

## Related files

| Page                                                                                           | Purpose                                                                                      |
| ---------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| [Mr. Boxington compared with sccache](../evidence/mr-boxington-vs-sccache.md)                  | Separate same-job and fresh-runner experiments, original versions, timings, and limitations. |
| [Compiler-cache integration diagnosis](../operations/diagnosing-compiler-cache-integration.md) | Distinguishes action startup, archive restore, path mapping, object reuse, and publication.  |
| [Ecosystem sources](../reference/vendor-ci-cache-sources.md)                                   | Upstream documentation, action, limits, and vendor claims.                                   |

## Design

Mr. Boxington (`mbx`) records build actions and their inputs, then restores eligible results when the action and observed inputs match. Upstream describes reuse for Rust compilation, supported Cargo work, and some native compilation/linking. Its coverage differs from sccache; compare correctness, actual commands avoided, and complete job time rather than treating the two tools' hit counters as equivalent. See [how it works](https://mr-boxington.jdx.dev/how-it-works) and [caching limits](https://mr-boxington.jdx.dev/limits).

Treat it as an alternative compiler wrapper. Do not stack it with sccache or another `RUSTC_WRAPPER` owner without a documented and tested composition. Install the required toolchain first and ensure the measured Cargo commands actually execute through `mbx`.

## Version and backend boundary

The archived experiments used mbx 1.2.0 locally and mbx 1.3.0 with the action. As checked on 2026-09-06, upstream had released mbx 1.9.0 and `jdx/mr-boxington-action` v1.3.0. Those newer releases have not been benchmarked in this archive.

The [v1.3.0 action metadata](https://github.com/jdx/mr-boxington-action/blob/v1.3.0/action.yml) defaults to `backend: github` and `github-cache-mode: target`. That default restores a warm Cargo target tree. A clean-target compiler-object experiment must deliberately select `github-cache-mode: objects`; otherwise it changes the cache mechanism being compared. Local and server backends are separate experiments. Keep the binary version, action revision, payload mode, namespace generation, and export policy in the measurement record.

Use normal GitHub Actions `uses:` execution so the action receives its runtime context. Shell-invoking a bundled action is a diagnostic technique and does not establish supported GitHub-cache behavior. An exact `cache-hit` output establishes an archive match, not reusable build results.

## Qualification procedure

1. Fix source state, compiler identity, runner/container image, workload, concurrency, and target path; use the [measurement procedure](../operations/measuring-cache-performance.md).
2. Verify supported commands and correctness against a direct-compiler control, then measure local cold and warm runs separately from fresh-runner restore/export.
3. For a compiler-object trial, remove target state between runs while retaining only the intended object store. Pin an explicit object payload mode on action versions whose default is a target archive.
4. Record avoided invocations, rejected predictions, store bytes/objects, restore and export time, and job wall time. Diagnose stable-path errors before attributing a weak result to cache transport.
5. Repeat changed-source, invalidation, concurrent-reader/writer, outage, cancellation, and clean-fallback scenarios before changing the [experimental decision](../decisions/README.md).

## Limitations and evidence

The same-job experiment shows competitive local reuse. The Docker experiment restored the expected exact action cache but repeatedly rejected Cargo registry inputs whose resolved paths escaped the mapped Cargo-home root. The [maintainer confirmed the mapping mechanism](https://github.com/jdx/mr-boxington/discussions/258#discussioncomment-18240056) and merged [the dedicated registry-mapping fix](https://github.com/jdx/mr-boxington/pull/259). The mapping is present in [mbx 1.9.0](https://github.com/jdx/mr-boxington/blob/v1.9.0/crates/mbx/src/rustc.rs). The newer release and the recommended direct-registry-mount workaround remain untested by this archive. Keep these findings in [their evidence page](../evidence/mr-boxington-vs-sccache.md); they do not establish a universal ranking or a current-version product defect.

## Decision

Use this as a qualified experimental alternative under decision D9. Keep the existing sccache candidate until representative fresh-runner results, supported mappings, correctness, and publication behavior justify revising the [canonical decisions](../decisions/README.md).
