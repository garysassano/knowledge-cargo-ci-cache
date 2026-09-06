# Approaches

This category owns architecture choices, tradeoffs, status, and decisions. Current conclusions are canonical in [Decisions](../decisions/README.md); this page helps pick the right approach.

## Decision Tree

```text
Need a Cargo CI cache?
  On RunsOn, start with mise, Magic Cache, input-only rust-cache, and a clean target.
  Keep no Rust cache as the control and remove the input cache if it does not pay for itself.

Need compiler-output reuse across changing PRs?
  Canary S3-backed sccache without a separate Cargo-input archive by default.

Need maximum native target reuse and can upgrade RunsOn?
  Test sticky Cargo inputs after v3.2, then a custom sticky target only if simpler options remain too slow.

Considering a whole-target archive?
  Use it only for a narrow stable workload with exact keys, no broad fallback, and small monitored objects.

Need maximum full-filesystem no-op fidelity and can own lifecycle complexity?
  Consider the archived EBS/filesystem snapshot approach.

Considering S3 Files for Cargo target no-op state?
  Do not use it for this purpose based on these experiments.
```

Use [mise tool setup](../operations/mise-tool-setup.md) alongside any approach when repeated Rust/Zig/helper-tool setup time matters.

## Decision Matrix

| Approach | Status | Best when | Main tradeoff | Page | Example |
| --- | --- | --- | --- | --- | --- |
| Clean target with mise and input-only `rust-cache` through RunsOn Magic Cache | Recommended practical default | You want a low-risk setup for most Rust projects while keeping mutable target state disposable. | Every job compiles; input-only caching avoids downloads but not compilation and may be unnecessary for small dependency sets. | [clean-target.md](clean-target.md) | [RunsOn input-only workflow](../../examples/workflows/runs-on-mise-rust-cache.yml) |
| Clean target with no Rust cache | Measurement control or simplest winner | Dependency downloads are cheap, cache setup is tied, or you need an attributable baseline. | Every job downloads missing inputs and compiles, but there are no Rust cache keys, archives, saves, or backend dependencies. | [clean-target.md](clean-target.md) | [RunsOn input-only workflow](../../examples/workflows/runs-on-mise-rust-cache.yml), whose Rust cache step is marked removable for this variant |
| Clean target with S3-backed `sccache` in default server mode | Leading measured PR-CI candidate | Source changes frequently and eligible compiler outputs remain reusable across commits. | Cargo orchestration, remote object operations, non-cacheable calls, and linking remain. | [sccache.md](sccache.md) | [canary workflow](../../examples/workflows/runs-on-sccache-canary.yml) |
| `Swatinem/rust-cache` whole-target archive with mtime-preserving checkout | Conditional narrow option | A stable workload produces a small archive whose exact restore/save is cheaper than recompilation. | Archive growth and serialization can erase the benefit; source mtimes and target state must agree. | [rust-cache-mtime-checkout.md](rust-cache-mtime-checkout.md) | [workflow](../../examples/workflows/rust-cache-mtime-checkout.yml) |
| `Swatinem/rust-cache` with source-keyed target cache | Narrow workaround | A measured stale exact-hit cycle must be fixed and the resulting target archive can be tightly bounded. | Full-tree archive cost, strict ordering, source invalidation, and copy-forward risk. | [rust-cache-source-keyed-target-cache.md](rust-cache-source-keyed-target-cache.md) | [workflow](../../examples/workflows/rust-cache-source-keyed-target-cache.yml) |
| Mr. Boxington | Experimental | Evaluate broader build-action reuse with supported commands and stable mappings. | The recorded Docker exact restore did not yield useful Rust reuse; newer releases and payload modes need fresh qualification. | [mr-boxington.md](mr-boxington.md) | [Evidence](../evidence/mr-boxington-vs-sccache.md) |
| Kache | Not tested | Inspect an additional compiler-cache candidate. | Upstream claims and examples only; no benchmark or adoption result in this archive. | [Ecosystem entry](../reference/vendor-ci-cache-sources.md#kache-not-tested) | None tested |
| EBS snapshot / filesystem snapshot | Archived alternative | You need maximum local no-op fidelity and can own snapshot lifecycle complexity. | Heavier infrastructure, credential scrubbing, and snapshot scoping. | [ebs-snapshot.md](ebs-snapshot.md) | [workflow](../../examples/workflows/ebs-snapshot.yml) |
| S3 Files | Rejected for Cargo target state | You need shared file-system access for another workload. | Cargo target metadata traversal was too slow/variable for these tests. | [s3-files.md](s3-files.md) | [workflow](../../examples/workflows/s3-files.yml) |

RunsOn sticky disks (native Cargo-input or target persistence without tar archive serialization) are a platform mechanism rather than a generic approach and remain a planned experiment after the v3.2 upgrade (decision D8). They are owned by [Sticky-Disk Options](../deployments/runs-on/README.md#sticky-disk-options) in the RunsOn deployment map.

## Compatibility Rule

Do not combine `Swatinem/rust-cache` target management with a sticky/full filesystem owner for the same `target/`, or two Cargo-home owners for the same `$CARGO_HOME` paths. See the [canonical compatibility rule](../concepts/cargo-path-coverage.md#compatibility-rule-canonical) for why.

## Architecture Diagrams

Keep diagrams beside the canonical explanation of the behavior they represent:

- [`rust-cache` with mtime-preserving checkout](rust-cache-mtime-checkout.md#architecture)
- [`rust-cache` with source-keyed full target cache](rust-cache-source-keyed-target-cache.md#architecture)
- [S3-backed `sccache`](sccache.md#design)
- [RunsOn archive, compiler-cache, and sticky-disk choices](../deployments/runs-on/README.md)
- [Filesystem snapshot lifecycle](ebs-snapshot.md#architecture)
- [S3 Files network-filesystem experiment](s3-files.md#architecture)
- [Cargo freshness decision model](../concepts/cargo-freshness-model.md)
