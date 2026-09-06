# Diagnosing compiler-cache integration

Use this procedure when a compiler cache restores successfully but the build remains cold, or when setup fails before usable compiler statistics exist. Cargo target freshness has its own [diagnostic procedure](diagnosing-rebuilds.md).

## Locate the failing layer

| Symptom                                                             | What it establishes                                                                  | Next check                                                                                              |
| ------------------------------------------------------------------- | ------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------- |
| Workflow `startup_failure` before a job or step log                 | Scheduling or workflow initialization failed                                         | Investigate runner and workflow startup before blaming a compiler invocation.                           |
| Missing `ACTIONS_RUNTIME_TOKEN` during shell-invoked action restore | That invocation lacks the expected Actions runtime context                           | Reproduce with the normal `uses:` interface; a later cache save cannot prove the failed restore worked. |
| Exact action-cache hit                                              | The archive key matched and was restored                                             | Inspect compiler/action hits, rejected results, commands avoided, and job time.                         |
| `absolute path has no stable cache mapping`                         | The tool could not encode an observed absolute input in its configured mapping roots | Inspect resolved container paths and mapping roots, including child symlinks.                           |
| Cache directory contains nested `actions/actions`                   | The mounted root may be one directory too deep for the tested mbx layout             | Compare the container cache root with the parent of the host `mbx cache dir` result.                    |
| High compiler hit rate with a slow job                              | Eligible requests reused outputs                                                     | Measure hashing, lookup, materialization, non-cacheable work, linking, and setup/post time.             |
| Population ends with unfinished writes                              | Remote completeness was not established                                              | Preserve write counts and test a fresh reader; do not infer flush from process shutdown.                |

## Container path checks

Record the binary and action versions, working directory, container `HOME`, `CARGO_HOME`, target path, actual cache-store root, bind-mount destinations, and any symlinks. Inspect these paths privately and export only generic path classes to this archive.

In the recorded mbx 1.3.0 experiment, a registry symlink beneath `CARGO_HOME` pointed to a separately mounted directory. The [v1.3.2 normalization code](https://github.com/jdx/mr-boxington/blob/v1.3.2/crates/mbx-cache-core/src/path_mapping.rs) resolves aliases for both observed paths and mapping roots before matching. A child path can therefore escape a lexical mapping root. The maintainer subsequently confirmed this mechanism and merged [PR #259](https://github.com/jdx/mr-boxington/pull/259), adding a dedicated registry mapping visible in [v1.9.0](https://github.com/jdx/mr-boxington/blob/v1.9.0/crates/mbx/src/rustc.rs). Source confirmation is separate from an end-to-end retest.

The candidate retest mounts the registry directly at `$CARGO_HOME/registry`, ensures the same logical roots are used on fresh runners, and repeats independent cold and warm jobs. This is the maintainer-recommended workaround, not a benchmark verified by this archive; also test the released dedicated-registry mapping. The mbx store-root adjustment that avoided nested `actions/actions` was a separate, observed integration correction; it did not fix registry path mapping. See [the full experiment](../evidence/mr-boxington-vs-sccache.md).

## Supported retest order

1. Reproduce through the documented action interface with a pinned binary and explicit payload mode.
2. Verify the intended store was restored into the container and that the workload invokes the selected wrapper.
3. Resolve input paths and mapping roots; classify rejected predictions separately from missing objects.
4. Compare a direct-compiler control, cold population, and warm reuse on separate fresh runners. Keep same-job local reuse in a separate scenario.
5. Inspect export/finalization and fresh-reader visibility. Record cancellation, timeout, and incomplete-write outcomes even when compilation succeeded.

The public reports [startup failure #247](https://github.com/jdx/mr-boxington/discussions/247), [shell restore context #248](https://github.com/jdx/mr-boxington/discussions/248), and [Cargo registry mapping #258](https://github.com/jdx/mr-boxington/discussions/258) preserve the diagnostic questions. Read reports and subsequent maintainer replies separately: #258 links a merged mapping fix, while this archive still has no timing result for the corrected integration. Measure through [the cache-performance procedure](measuring-cache-performance.md).
