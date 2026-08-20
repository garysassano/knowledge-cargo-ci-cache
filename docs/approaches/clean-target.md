# Clean Target: No Cache Or Cargo Inputs Only

## Summary

| Field | Value |
| --- | --- |
| Status | Recommended practical default with a no-cache control |
| Use when | PR workloads change frequently, whole-target archives are large or unstable, or a simple control is needed before adding compiler caching. |
| Main tradeoff | Every job recreates `target/`; input-only caching avoids downloads but not compilation. |

## Design

Both variants start with an empty local target directory and differ only in whether Cargo registry and Git inputs are restored from an archive or downloaded normally.

```text
no Rust cache
  download Cargo registry/Git inputs as needed
  compile into a clean local target/

input-only rust-cache
  restore Cargo registry/Git inputs
  compile into a clean local target/
```

Neither variant attempts to preserve Cargo fingerprints, build-script outputs, final artifacts, or rustc incremental state across jobs. Source-mtime preservation is therefore unnecessary for this design.

## Choosing Between The Two Variants

| Situation | Prefer |
| --- | --- |
| Dependency downloads are material and the input archive remains small | Input-only `Swatinem/rust-cache` |
| Cache setup is effectively tied with downloading inputs | No Rust cache |
| The `rust-cache` post step still performs material target cleanup | No Rust cache or an explicit Cargo-home-only `actions/cache` entry |
| You need a control for a target-cache or `sccache` experiment | No Rust cache |

The input-only shape is a reasonable operational default even before extensive benchmarking because it does not persist mutable target state. When results are statistically indistinguishable, prefer no Rust cache because it has fewer keys, save races, archives, and backend dependencies.

## Input-Only Configuration

```yaml
env:
  CARGO_INCREMENTAL: "0"

steps:
  - name: Cache Cargo registry and Git inputs
    uses: Swatinem/rust-cache@v2
    with:
      prefix-key: rust-inputs-v1
      cache-targets: false
      cache-bin: false
      cache-all-crates: false
      save-if: ${{ github.event_name == 'push' && github.ref == 'refs/heads/main' }}
```

Use a fresh prefix when changing from whole-target caching so no old target lineage can be restored. Allow one trusted canonical writer; PR jobs should normally restore without saving.

`cache-bin: false` keeps setup tools outside the Cargo-input archive. Install stable tools through the runner image or a dedicated setup layer such as [mise](../operations/mise-tool-setup.md).

## Implementation Caveat

In released `Swatinem/rust-cache` v2.9.2, an eligible post-save path still traverses and cleans configured target directories even when `cache-targets: false`; the target directory is simply omitted from the saved archive. Restore-only jobs, exact hits, and `save-if: false` skip that save path.

Measure the post step. If traversal is material, either remove `rust-cache` or replace it with an explicit cache covering only:

```text
$CARGO_HOME/registry
$CARGO_HOME/git
```

See [`Swatinem/rust-cache` Behavior](../concepts/rust-cache-behavior.md) for the current implementation details.

## Strengths

- Eliminates target-archive extraction, compression, upload, and copy-forward growth.
- Produces predictable clean-build behavior.
- Makes the no-cache and compiler-cache comparison easy to interpret.
- Keeps current compilation and linking on local runner storage.
- Input-only mode can avoid repeated dependency downloads with a relatively small archive.

## Limitations

- Recompiles every cacheable and non-cacheable unit unless a compiler cache such as `sccache` is added.
- Does not produce Cargo no-op builds.
- Input-only caching still has archive setup, keying, storage, and save behavior.
- A full Rust workload can be substantially slower than a healthy compact target cache.

## Evidence

The [target archive growth evidence](../evidence/target-archive-growth.md) records:

- Whole-target archive growth from about 206 MB to 13.9 GB in under five days.
- A representative job that spent 65.8% of its time handling the cache.
- Predictable but compilation-heavy production runs after target caching was disabled.

The [cache strategy benchmarks](../evidence/cache-strategy-benchmarks.md) record:

- Input-only caching with only about five seconds of end-to-end benefit in a short controlled benchmark.
- A representative full-workload comparison in which two input-only trials and two no-cache trials differed by only four seconds on average at the job level.

## Decision

For most RunsOn Rust projects, use mise with Magic Cache, input-only `rust-cache`, and a clean local target as the pragmatic starting point. Keep a no-cache control, remove the input cache when representative measurements show no material benefit, and add [`sccache`](sccache.md) only when compiler-output reuse materially improves end-to-end time.
