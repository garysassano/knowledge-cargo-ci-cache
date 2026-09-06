# Cargo freshness beyond source mtimes

**Status: nightly evaluation and upstream watchlist; not adopted or benchmarked here.** Reviewed on 2026-09-06. This page owns unstable freshness alternatives and their promotion criteria. The [Cargo freshness model](../concepts/cargo-freshness-model.md) explains the stable default; [source-mtime techniques](../reference/source-mtime-alternatives.md) cover ways to work with that default.

## Content fingerprints

Cargo's [checksum-freshness documentation](https://doc.rust-lang.org/nightly/cargo/reference/unstable.html#checksum-freshness) describes replacing mtimes in fingerprints with content checksums. The current interface includes `build.fingerprint = "content"` behind the unstable gate:

```toml
# .cargo/config.toml - experiment with a pinned nightly Cargo
[unstable]
checksum-freshness = true

[build]
fingerprint = "content"
```

The [tracking issue](https://github.com/rust-lang/cargo/issues/14136) was still open on the review date. Its September 3 call for testing identifies `1.100.0-nightly (2e2b193f8 2026-09-02)` for the new configuration. A stabilization proposal or call for testing is not a stable release. Record the resolved `cargo -Vv` and `rustc -Vv` in an experiment, and isolate its cache namespace from stable and other nightlies.

Build-script-ingested files still use mtimes, and the checksum algorithm may change between Cargo versions. The feature changes freshness detection; it does not restore missing artifacts or make incompatible paths, flags, toolchains, and target state valid. The [performance tracker](https://github.com/rust-lang/cargo/issues/14722) is a separate reason to measure metadata/checksum work on representative workspaces.

## Related features and common confusions

| Mechanism                                                                                                  | Reviewed status                                                             | Relevance and boundary                                                                                                                            |
| ---------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| Content fingerprints / checksum freshness                                                                  | Nightly-only; pending stabilization                                         | Direct alternative to source-mtime comparisons for covered inputs. Build-script coverage is incomplete.                                           |
| [`rustdoc-depinfo`](https://doc.rust-lang.org/nightly/cargo/reference/unstable.html#rustdoc-depinfo)       | Unstable; [tracking issue](https://github.com/rust-lang/cargo/issues/15370) | More precise documentation dependency tracking; the docs describe combining it with checksum freshness. It is not general build-script freshness. |
| [`binary-dep-depinfo`](https://doc.rust-lang.org/nightly/cargo/reference/unstable.html#binary-dep-depinfo) | Unstable                                                                    | Adds binary dependencies to dep-info, especially for compiler development. It does not replace mtime comparisons.                                 |
| [`mtime-on-use`](https://doc.rust-lang.org/nightly/cargo/reference/unstable.html#mtime-on-use)             | Unstable                                                                    | Updates artifact usage timestamps for cleanup tooling. It is not content-based source freshness.                                                  |
| [`build.build-dir`](https://doc.rust-lang.org/cargo/reference/config.html#buildbuild-dir)                  | Documented in the stable Cargo reference                                    | Relocates intermediate build artifacts. Relocation does not provide a semantic shared cache or remove mtime checks.                               |
| Git-derived or content-checked source retiming                                                             | External workflow techniques                                                | Rewrites/preserves timestamps under the existing model; see [source-mtime alternatives](../reference/source-mtime-alternatives.md).               |
| rustc incremental state and compiler wrappers                                                              | Separate layers                                                             | Reuse work after Cargo decides to invoke a compiler. They do not make Cargo report `Fresh`; see [cache layers](../concepts/cache-layers.md).      |

The first four feature statuses come from the linked Cargo nightly reference. The original checksum implementation is [cargo#14137](https://github.com/rust-lang/cargo/pull/14137). Do not classify every unstable Cargo feature as a cache strategy, or describe the stable `build-dir` setting as an unreleased freshness solution.

## Experiment and promotion criteria

Use a disposable branch and a pinned nightly; the configuration above is a research specimen, not an instruction to migrate the stable workflow. Compare stable mtime behavior and nightly mtime/content modes on the same workload, with separate cache namespaces and equivalent target-state restoration.

Test identical source with new checkout mtimes, changed contents with preserved mtimes, changed dependency inputs, manifest/feature/toolchain changes, generated files, build-script `rerun-if-changed` inputs, and missing target metadata. Include `cargo doc` separately when testing rustdoc dependency tracking. Check outputs against clean builds; a faster run that misses an invalidation fails qualification.

Measure fresh-checkout no-op time, rebuild time, checksum/metadata overhead, restore/save cost, and target growth. An unchanged build should show whether Cargo skipped rustc, rather than merely whether a wrapper returned a hit. Preserve Cargo fingerprint traces for unexpected outcomes using the [diagnosis procedure](../operations/diagnosing-rebuilds.md).

Promote into stable guidance only after an actual stable release supports the required interface and coverage, and after workload correctness and end-to-end measurements justify it. Until then, an opt-in nightly experiment is possible, but [current decisions](../decisions/README.md) continue to target stable Cargo.
