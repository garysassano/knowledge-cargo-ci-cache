# Examples

These examples are intentionally generic. They are meant to preserve the workflow shapes and ordering constraints discovered during the cache experiments, not to be copied without adapting package names, paths, runner labels, credentials, and deployment steps.

For CI tool setup, prefer inline `mise_toml` with `jdx/mise-action`; see [Mise Tool Setup](../docs/operations/mise-tool-setup.md). The workflow examples focus on Cargo cache layouts and may omit project-specific tool installation details.

## Workflows

| Example | Purpose | Referenced by |
| --- | --- | --- |
| [`runs-on-mise-rust-cache.yml`](workflows/runs-on-mise-rust-cache.yml) | Clean RunsOn target with mise-owned tools and an optional input-only Cargo cache through Magic Cache. | [`docs/deployments/runs-on/README.md`](../docs/deployments/runs-on/README.md) |
| [`runs-on-sccache-canary.yml`](workflows/runs-on-sccache-canary.yml) | Trusted-writer S3 `sccache` canary with an ephemeral target, no separate Cargo-input archive, and statistics. | [`docs/approaches/sccache.md`](../docs/approaches/sccache.md) |
| [`runs-on-sticky-disk-canary.yml`](workflows/runs-on-sticky-disk-canary.yml) | Post-v3.2 canary for built-in sticky Cargo inputs and a separate custom sticky-target experiment. | [`docs/deployments/runs-on/README.md`](../docs/deployments/runs-on/README.md) |
| [`rust-cache-mtime-checkout.yml`](workflows/rust-cache-mtime-checkout.yml) | Conditional exact-source whole-target `rust-cache` archive with mtime-preserving checkout and a trusted writer. | [`docs/approaches/rust-cache-mtime-checkout.md`](../docs/approaches/rust-cache-mtime-checkout.md) |
| [`rust-cache-source-keyed-target-cache.yml`](workflows/rust-cache-source-keyed-target-cache.yml) | Narrow workaround combining input-only `rust-cache` with an exact source/build-keyed target archive restored afterward. | [`docs/approaches/rust-cache-source-keyed-target-cache.md`](../docs/approaches/rust-cache-source-keyed-target-cache.md) |
| [`ebs-snapshot.yml`](workflows/ebs-snapshot.yml) | EBS/filesystem snapshot layout for high-fidelity Cargo no-op behavior. | [`docs/approaches/ebs-snapshot.md`](../docs/approaches/ebs-snapshot.md) |
| [`cargo-lambda-snapshot-matrix.yml`](workflows/cargo-lambda-snapshot-matrix.yml) | Sanitized RunsOn snapshot fork workflow shape for per-Lambda Cargo build-state snapshots. | [`docs/approaches/ebs-snapshot.md`](../docs/approaches/ebs-snapshot.md) |
| [`s3-files.yml`](workflows/s3-files.yml) | S3 Files target-cache experiment shape. Not recommended for Cargo target no-op state based on these experiments. | [`docs/approaches/s3-files.md`](../docs/approaches/s3-files.md) |
| [`cargo-fingerprint-diagnostics.yml`](workflows/cargo-fingerprint-diagnostics.yml) | Diagnostic workflow for fingerprint and dirty-rebuild investigation. | [`docs/operations/diagnosing-rebuilds.md`](../docs/operations/diagnosing-rebuilds.md) |

## Local Actions

| Example | Purpose |
| --- | --- |
| [`actions/cached-worktree-checkout/action.yml`](actions/cached-worktree-checkout/action.yml) | Generic composite action for checking out into a restored Git worktree without rewriting unchanged file mtimes. |
| [`actions/snapshot/action.yml`](actions/snapshot/action.yml) | Local RunsOn snapshot fork with keyed snapshot streams and smart-save support. Its launcher and binaries are generated; run `make build` in that directory first (see [its README](actions/snapshot/README.md#building)). |
| [`actions/s3-files-mount/action.yml`](actions/s3-files-mount/action.yml) | Composite action for installing and mounting S3 Files with cached client setup. |

## Measurement Data

| Example | Purpose |
| --- | --- |
| [`measurements/cache-measurements.example.jsonl`](measurements/cache-measurements.example.jsonl) | Synthetic mixed-record JSONL showing run, phase, metric, and resource-sample records without repository-specific identifiers. |
