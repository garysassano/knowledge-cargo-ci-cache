# RunsOn Deployment Map

This page maps the repository's cache approaches onto RunsOn. It owns RunsOn runner prerequisites, Magic Cache, direct S3 `sccache`, sticky-disk behavior, and the boundary with the archived EBS snapshot approach. Generic Cargo tradeoffs remain in [Approaches](../../approaches/README.md).

## Choose A Platform Shape

| Situation | RunsOn shape | Status | Example |
| --- | --- | --- | --- |
| Establish a safe PR-CI baseline | Mise-managed tools, input-only `Swatinem/rust-cache` through Magic Cache, ephemeral local `target/`, and normal checkout | Recommended practical default; remove the input cache if it does not pay for itself | [`runs-on-mise-rust-cache.yml`](../../../examples/workflows/runs-on-mise-rust-cache.yml) |
| Reuse compiler outputs across changing commits | Ephemeral local `target/` with direct S3 `sccache` in default server mode; omit a separate Cargo-input archive unless measured downloads justify it | Leading measured canary | [`runs-on-sccache-canary.yml`](../../../examples/workflows/runs-on-sccache-canary.yml) |
| Persist Cargo registry and Git inputs without archives | RunsOn sticky disk with built-in `rust` mode | Test after RunsOn v3.2 upgrade | [Sticky-Disk Options](#sticky-disk-options) |
| Preserve a native target filesystem | Sticky disk with built-in `rust` mode and a custom target path | Higher-complexity fallback experiment | [Sticky-Disk Options](#sticky-disk-options) |
| Repeat an exact, stable workload with a small target tree | Whole-target archive through Magic Cache with source/build identity in the restore lineage | Conditional narrow option | [`rust-cache-mtime-checkout.yml`](../../../examples/workflows/rust-cache-mtime-checkout.yml) |
| Preserve a complete filesystem with explicit lifecycle ownership | Local EBS snapshot action and mounted snapshot root | Archived alternative | [`ebs-snapshot.yml`](../../../examples/workflows/ebs-snapshot.yml) |

Do not combine archive-managed and sticky/snapshot-managed ownership of the same Cargo paths. The canonical compatibility rule is in [Cargo Path Coverage](../../concepts/cargo-path-coverage.md#compatibility-rule-canonical).

## Version Boundary

The platform facts below were checked on August 20, 2026:

- Sticky disks require RunsOn v3.2.0 or newer.
- RunsOn v2 is scheduled to enter critical-fixes-only support after September 15, 2026. Treat the v3 migration as a separate infrastructure project with a parallel stack, representative workflow tests, and a rollback window.
- `runs-on/action@v2` currently exposes sticky-disk and S3 `sccache` configuration. The released action metadata defaults `sticky_wait_timeout` to `15m`, while the sticky-disk documentation still mentions five minutes; set the timeout explicitly.

Do not couple the immediate Rust cache choice to a rushed platform migration. Establish the clean-target baseline first, upgrade independently, then test sticky storage.

## Magic Cache Input-Only Baseline

Magic Cache replaces the backend used by compatible `actions/cache` calls. It improves transport and capacity characteristics, but cached paths are still archived, downloaded, extracted, cleaned by their owning action, and saved as new immutable objects.

Use this order:

1. Select a runner with `extras=s3-cache`.
2. Run `runs-on/action@v2` before any action that uses the cache protocol.
3. Check out normally; source-mtime preservation is unnecessary when `target/` starts clean.
4. Set up Rust and helper tools.
5. Restore Cargo registry and Git inputs with `cache-targets: false` as the pragmatic default, or omit this step for the no-cache control.
6. Build into an ephemeral local target directory.

The input-only settings are:

```yaml
env:
  CARGO_INCREMENTAL: "0"

steps:
  - uses: runs-on/action@v2

  - uses: Swatinem/rust-cache@v2
    with:
      prefix-key: rust-inputs-v1
      cache-targets: false
      cache-bin: false
      cache-all-crates: false
      save-if: ${{ github.event_name == 'push' && github.ref == 'refs/heads/main' }}
```

Use a fresh prefix when cutting over from target caching. Keep PR jobs restore-only and use one trusted canonical writer. This is the low-risk default for most projects because it avoids mutable target persistence. If input-only setup is effectively tied with normal dependency downloads, remove the Rust cache and keep the simpler no-cache baseline.

`jdx/mise-action` can continue to cache Rust, Zig, and helper-tool setup through Magic Cache. Keep `MISE_DATA_DIR` stable, keep Cargo credentials out of it, and do not treat setup-tool caching as Cargo target freshness.

## Direct S3 `sccache`

RunsOn can export the S3 backend environment and `RUSTC_WRAPPER` for `sccache`:

```yaml
- name: Export RunsOn S3 sccache environment
  uses: runs-on/action@v2
  with:
    sccache: s3

- name: Override RunsOn sccache namespace
  shell: bash
  run: echo "SCCACHE_S3_KEY_PREFIX=cache/sccache/${GITHUB_REPOSITORY_ID}/${RUNNER_OS}-${RUNNER_ARCH}/rust-v1" >> "$GITHUB_ENV"

- uses: Mozilla-Actions/sccache-action@v0.0.11
  with:
    version: v0.17.0
```

With `sccache: s3`, the RunsOn action exports `SCCACHE_BUCKET`, `SCCACHE_REGION`, the stack-wide default `SCCACHE_S3_KEY_PREFIX=cache/sccache`, `SCCACHE_GHA_ENABLED=false`, and `RUSTC_WRAPPER=sccache`. The explicit namespace step is not configuring the backend again; it overrides only `SCCACHE_S3_KEY_PREFIX` to isolate objects by repository, platform, and cache schema. The RunsOn action does not install the `sccache` executable, so keep a separate pinned installer.

Keep `CARGO_INCREMENTAL=0`, leave `target/` on local runner storage, print statistics on every canary, and use a repository/platform/schema-specific prefix instead of the stack-wide default.

The canonical canary does not also run `Swatinem/rust-cache`. Earlier default-server, client-side, read-only, and multilevel measurements included its input-only archive, while the later default-server ablation omitted it. Removing the archive preserved 6,929 compiler-cache hits with zero misses and was directionally faster, although the single cross-family run is not enough to establish a stable effect size or prove direct interference. Keep the mechanisms separate by default and add Cargo-input caching only when measured registry or Git download savings exceed its archive and action overhead in the complete job.

Direct S3 access is not governed by Magic Cache protocol isolation. `SCCACHE_S3_RW_MODE=READ_ONLY` constrains the `sccache` process, but it is not an infrastructure trust boundary: arbitrary workflow code can still use any broader S3 permissions attached to the runner. Enforce untrusted PR read-only behavior with IAM, a separate stack/role, or an equivalent boundary before sharing a writable namespace.

Confirm lifecycle expiry, request volume, object growth, cache errors, and rollback to direct `rustc`. Adopt the compiler cache from representative end-to-end time and cost, not hit rate alone.

## Sticky-Disk Options

Sticky disks preserve a native EBS filesystem through snapshots and avoid tar/zstd archive extraction and recompression. The disk is bounded by its configured size, but Cargo artifacts can still accumulate until cleanup or reset.

The runner requests a named disk lineage with an illustrative size:

```yaml
runs-on:
  - runs-on=${{ github.run_id }}
  - cpu=16
  - image=ubuntu24-full-x64
  - sticky=rust-inputs-v1:20gb
```

The built-in Cargo-input mode persists only Cargo registry and Git paths:

```yaml
- uses: runs-on/action@v2
  with:
    sticky_cache: rust
    sticky_wait_timeout: 15m
```

It does not persist workspace `target/`. A custom target experiment must opt in explicitly:

```yaml
- uses: runs-on/action@v2
  with:
    sticky_cache: |
      rust
      custom,path=sticky-target
    sticky_wait_timeout: 15m
```

Run the action after checkout when a custom path is relative to the GitHub workspace. Keep source paths stable and preserve or account for source mtimes before judging target reuse.

Before enabling a custom target:

- Measure target bytes and file count across source, lockfile, feature, profile, and toolchain changes.
- Monitor free bytes and inodes, and define warning, reset, and maximum-utilization thresholds.
- Serialize or deliberately partition writers because concurrent jobs start from independent snapshots and the newest completed clean-unmount snapshot becomes the next restore point.
- Test successful, failed, and cancelled jobs, disk wait failures, default-branch fallback, and reset behavior.
- Keep the sticky disk as the sole owner of the target and Cargo-input paths it mounts.

The dense lineage, fallback, expiry, free-space, and last-writer semantics are in [RunsOn Cache And Disk Details](../../reference/runson-cache-and-disk-details.md). A [proposed Cargo sticky-disk workflow](../../research/runs-on-sccache/sticky-cargo-canary.yml) is retained under research and has not been benchmarked. Use it only after verifying the required platform, trusted writer, capacity, and lifecycle controls; promote a copyable canary into the main examples together with its first measurements.

## Conditional Whole-Target Archives

Magic Cache can still back a whole-target `rust-cache` or separate `actions/cache` entry, but the backend does not make a growing target archive cheap to serialize.

Use whole-target archives only when:

- Source and build identity are included in the restore lineage.
- There is no broad target fallback across changed source, lockfile, profile, feature, target, toolchain, or compiler-wrapper state.
- One trusted canonical job writes the lineage.
- Compressed bytes, target bytes, file count, restore time, and save time remain bounded and cheaper than recompilation.

Restricting saves to the default branch does not fix a large restore: every reader still downloads and extracts it, and the canonical writer can keep rolling it forward. More backend capacity, shorter object retention, and namespace rotation also do not prune files inside the active archive.

## Archived EBS Snapshot Alternative

The local [EBS snapshot approach](../../approaches/ebs-snapshot.md) remains the strongest measured option for complete Cargo no-op fidelity because it preserves the workspace, Cargo home, target, and related filesystem state together. It also requires custom EC2/EBS permissions, snapshot retention, clean mount/unmount handling, concurrency control, and credential scrubbing.

Prefer supported sticky disks for new post-v3.2 experiments. Keep the local snapshot action as archived evidence and as an explicit fallback when its additional lifecycle control is required.

## Storage And Isolation Notes

- RunsOn local NVMe is fast current-job storage but is wiped when the instance stops or terminates. It pairs naturally with a disposable target and remote `sccache`; it is not a cross-job cache.
- EFS and other shared network filesystems avoid archive creation but add remote metadata latency, contention, and cleanup complexity. They are not the first choice for Cargo target state.
- Magic Cache lifecycle removes complete immutable objects; it does not inspect or prune their contents.
- RunsOn v3.2 adds optional repository/branch Magic Cache isolation. Enabling it changes the cache namespace and can cause a deliberate cold start. It does not constrain direct S3 clients.
- Never persist Cargo registry credentials, cloud credentials, or tokens on a sticky or snapshotted path. Scrub credential-bearing files before a save-capable post step.

## Ownership And Maintenance

This page owns RunsOn-specific deltas only. Cache selection lives in [Approaches](../../approaches/README.md), current conclusions live in [Decisions](../../decisions/README.md), tool setup lives in [Mise Tool Setup](../../operations/mise-tool-setup.md), and measurement procedure lives in [Measuring Cache Performance](../../operations/measuring-cache-performance.md).

Before changing this deployment map, verify the current RunsOn stack requirement, runner-label syntax, `runs-on/action` major and metadata, Magic Cache isolation behavior, sticky-disk lifecycle, `sccache` helper behavior, and S3 IAM/lifecycle assumptions. Record behavior changes according to the [maintenance checklist](../../operations/maintenance-checklist.md).

## Related Pages

- [Quickstart](../../quickstart.md)
- [Decisions](../../decisions/README.md)
- [Approaches](../../approaches/README.md)
- [Clean Target](../../approaches/clean-target.md)
- [S3-Backed `sccache`](../../approaches/sccache.md)
- [RunsOn Cache And Disk Details](../../reference/runson-cache-and-disk-details.md)
- [Measuring Cache Performance](../../operations/measuring-cache-performance.md)
- [Target Archive Growth In Production](../../evidence/target-archive-growth.md)
- [Cache Strategy Benchmarks](../../evidence/cache-strategy-benchmarks.md)

## Proposed improvements

The [RunsOn sccache research index](../../research/runs-on-sccache/README.md) routes versioned implementation details, the performance roadmap, action lifecycle, trust/publication, gateway, sticky compiler objects, alternative backends, and promotion gates. These are proposals and untested integrations; use the workflow shapes above for the existing deployment.
