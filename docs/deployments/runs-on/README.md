# RunsOn Deployment Map

This page maps the repository's cache approaches onto RunsOn. It owns RunsOn runner prerequisites, Magic Cache and its compiler-cache integrations, direct S3 `sccache`, sticky-disk behavior, and the boundary with the archived EBS snapshot approach. Generic Cargo tradeoffs remain in [Approaches](../../approaches/README.md).

## Choose A Platform Shape

| Situation                                                        | RunsOn shape                                                                                                             | Status                                                                              | Example                                                                                                                              |
| ---------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| Establish a safe PR-CI baseline                                  | Mise-managed tools, input-only `Swatinem/rust-cache` through Magic Cache, ephemeral local `target/`, and normal checkout | Recommended practical default; remove the input cache if it does not pay for itself | [`runs-on-mise-rust-cache.yml`](../../../examples/workflows/runs-on-mise-rust-cache.yml)                                             |
| Reuse compiler outputs across changing commits                   | Ephemeral local `target/` with `sccache: true` or `mbx: true` through Magic Cache, with cache isolation enabled          | Measured; both unreleased on 2026-10-15; size the runner before choosing            | [Compiler caches through Magic Cache](#compiler-caches-through-magic-cache)                                                          |
| Reuse compiler outputs with released components only             | Ephemeral local `target/` with Mr. Boxington GitHub object mode, or direct S3 `sccache` on a trusted stack               | Qualified canaries; direct S3 is not repository-isolated                            | [Mr. Boxington](../../tools/mr-boxington.md), [`runs-on-sccache-canary.yml`](../../../examples/workflows/runs-on-sccache-canary.yml) |
| Persist Cargo registry and Git inputs without archives           | RunsOn sticky disk with built-in `rust` mode                                                                             | Test after RunsOn v3.2 upgrade                                                      | [Sticky-Disk Options](#sticky-disk-options)                                                                                          |
| Preserve a native target filesystem                              | Sticky disk with built-in `rust` mode and a custom target path                                                           | Higher-complexity fallback experiment                                               | [Sticky-Disk Options](#sticky-disk-options)                                                                                          |
| Speed up repeated checkouts of a large repository                | Sticky disk with `git` mode before `actions/checkout`                                                                    | Untested; checkout transport only                                                   | [Git Checkout Mode](#git-checkout-mode)                                                                                              |
| Repeat an exact, stable workload with a small target tree        | Whole-target archive through Magic Cache with source/build identity in the restore lineage                               | Conditional narrow option                                                           | [`rust-cache-mtime-checkout.yml`](../../../examples/workflows/rust-cache-mtime-checkout.yml)                                         |
| Preserve a complete filesystem with explicit lifecycle ownership | Local EBS snapshot action and mounted snapshot root                                                                      | Archived alternative                                                                | [`ebs-snapshot.yml`](../../../examples/workflows/ebs-snapshot.yml)                                                                   |

Do not combine archive-managed and sticky/snapshot-managed ownership of the same Cargo paths. The canonical compatibility rule is in [Cargo Path Coverage](../../concepts/cargo-path-coverage.md#compatibility-rule-canonical).

## Version Boundary

Live documentation and release-source review: October 15, 2026, against [RunsOn v3.5.0](https://github.com/runs-on/runs-on/releases/tag/v3.5.0) and `runs-on/action` `main` at `cb1cb4f`. A test stack was upgraded from v3.4.0 to v3.5.0 with isolation enabled and used for the [Magic Cache benchmark](../../evidence/runs-on-magic-cache-sccache-vs-mbx.md). The [provider source map](../../providers/runs-on.md) lists the pages checked, and the [implementation reference](../../reference/compiler-cache-implementation.md#release-refresh-2026-10-15) owns the versioned behavior.

- Sticky disks require RunsOn v3.2.0 or newer. Magic Cache serves sccache's GitHub Actions cache backend from v3.5.0.
- RunsOn v2 entered critical-fixes-only support after September 15, 2026. Treat a v3 migration as a separate infrastructure project with a parallel stack, representative workflow tests, and a rollback window.
- v3.5.0 moved Linux jobs to `/home/runner/work`. Caches keyed on the absolute workspace path miss once after upgrading.
- `runs-on/action@v2` sets `sticky_wait_timeout` to `15m` by default; set it explicitly.

Establish the clean-target baseline first, upgrade independently, then test compiler caches or sticky storage.

## Magic Cache Input-Only Baseline

Magic Cache replaces the backend used by compatible `actions/cache` calls. It improves transport and capacity characteristics, but cached paths are still archived, downloaded, extracted, cleaned by their owning action, and saved as new immutable objects.

The workflow shapes here use Flex per-job labels. For Fleet, configure the capability in the Terraform runner catalog and target the named fleet from workflow YAML; do not copy Flex resource labels into a Fleet job.

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

## Compiler caches through Magic Cache

Enable `EnableCacheIsolation` first. Magic Cache then stores each repository's entries under its own scoped prefix with GitHub's branch rules: a job reads its own ref, its base branch and the default branch, and writes only its own ref. Low-trust triggers and `cache-mode: read` get read-only tokens. Without isolation, Magic Cache data stays in `cache/*`, which every runner of the stack can write, so the scoping is logical only.

Two per-object compiler-cache integrations use this path. Both were open pull requests on 2026-10-15; use their released inputs once available:

```yaml
# sccache (runs-on/action#78): install sccache 0.10.0 or newer before the action
- uses: taiki-e/install-action@v2
  with:
    tool: sccache@0.18.0
- uses: runs-on/action@v2
  with:
    sccache: true

# Mr. Boxington (runs-on/action#65)
- uses: runs-on/action@v2
  with:
    mbx: true
- uses: jdx/mr-boxington-action@v1
  with:
    backend: remote
```

Measured on ruff with 32-vCPU runners ([evidence](../../evidence/runs-on-magic-cache-sccache-vs-mbx.md)):

| Build                                 | No cache   | `sccache: true` | `mbx: true` |
| ------------------------------------- | ---------- | --------------- | ----------- |
| Cold                                  | 32.5 s     | 60.0 s          | 35.5 s      |
| Warm, another runner                  | about 32 s | 11.7 s          | 7.3 s       |
| Pull request changing a central crate | 32.0 s     | 54.5 s          | 27.1 s      |

- `sccache: true` caches only eligible compilations. On a miss it delays dependent crates until the whole compile is done, so on a large runner a cold build, or a pull request that changes a central crate, can be slower than no cache. Pin the sccache version, because each release starts an empty cache, and keep `CARGO_INCREMENTAL=0`.
- `mbx: true` publishes only from pushes to protected branches. Pull requests read their base branch's objects and rebuild their own changes on every push. It stores about 7× more than sccache for the same build (1.7 GiB versus 240 MiB on ruff).
- Both store entries that are never rewritten while in use. With fixed retention (default 10 days; hits do not extend it), long-lived dependency entries expire together. Raise `S3CacheExpirationInDays` if that periodic cold rebuild matters.
- sccache keeps every entry under one cache version. Magic Cache's lookup index covers a version directory only below 50,000 entries, which a busy default branch can reach within the retention window. The mbx helper spreads its entries over 16 versions.

Choose on the target runner size and change pattern, measured with the [procedure](../../operations/measuring-cache-performance.md). Keep direct `rustc` as the rollback.

## Direct S3 `sccache`

`sccache: s3` writes straight to the stack's S3 bucket. It is legacy on RunsOn v3.5.0, where the action warns and recommends `sccache: true`. It remains the configuration behind the archived [S3 benchmarks](../../evidence/cache-strategy-benchmarks.md) and the [canary workflow](../../../examples/workflows/runs-on-sccache-canary.yml):

```yaml
- uses: runs-on/action@v2
  with:
    sccache: s3
- uses: Mozilla-Actions/sccache-action@v0.0.11
  with:
    version: v0.17.0
```

The action exports `SCCACHE_BUCKET`, `SCCACHE_REGION`, a repository- and platform-scoped `SCCACHE_S3_KEY_PREFIX` (from [#58](https://github.com/runs-on/action/pull/58)), `SCCACHE_GHA_ENABLED=false`, and `RUSTC_WRAPPER=sccache`. It does not install `sccache`. Apply overrides before anything starts the daemon; a running daemon keeps its startup configuration.

Direct S3 is outside Magic Cache isolation. The runner role can read and write `cache/*` for every repository on the stack, so a prefix separates objects but does not protect them, and `SCCACHE_S3_RW_MODE=READ_ONLY` constrains only the `sccache` process. Use direct S3 only on a stack where every job is trusted, or enforce untrusted read-only behavior with a separate stack or role.

Keep `CARGO_INCREMENTAL=0`, leave `target/` on local runner storage, print statistics on every canary, and confirm lifecycle expiry, request volume, cache errors, and rollback to direct `rustc`.

## Mr. Boxington backend boundary

| Interface                                        | Responsibility                                                                              | Status on 2026-10-15                                                                                                         |
| ------------------------------------------------ | ------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| `jdx/mr-boxington-action` with `backend: github` | `objects` or `target` payload archives through Magic Cache                                  | Released; qualified object-mode canary ([D9](../../decisions/README.md))                                                     |
| `mbx: true`                                      | A helper in the job serving mbx's remote protocol from Magic Cache, per object and isolated | Open [runs-on/action#65](https://github.com/runs-on/action/pull/65); measured, and validated on Linux, container and Windows |
| Direct MBX `s3://` to the stack bucket           | Per-object storage with the runner role                                                     | Rejected: not isolated, and RunsOn is retiring direct-S3 adapters                                                            |
| `mr-boxington-cache` server                      | Self-hosted server with OIDC grants and protocol extensions                                 | Not pursued on RunsOn because it requires deployed infrastructure; untested here                                             |

See [Mr. Boxington remote backends](../../research/mr-boxington-remote-backends.md) for the history and remaining proposals.

## Sticky-Disk Options

RunsOn now provides [managed sticky disks](https://runs-on.com/docs/runners/capabilities/sticky-disks/) for the EBS approach: a per-job native filesystem is restored and preserved through EBS snapshots, avoiding tar/zstd archive extraction and recompression. The current documentation positions this as the successor to `runs-on/snapshot@v1`; the archive's [custom snapshot implementation](../../approaches/ebs-snapshot.md) remains separate historical evidence. The disk is bounded by its configured size, but Cargo artifacts can still accumulate until cleanup or reset.

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

For missing storage, distinguish explicit cold fallback from setup errors using the [v2.3.1 failure contract](../../reference/runson-cache-and-disk-details.md#sticky-disk-failure-boundary). These source checks do not qualify a managed sticky-target benchmark.

### Git Checkout Mode

Since v2.3.0, `runs-on/action` also accepts `sticky_cache: git` (alias `checkout`) and `git-full`. v2.3.1 was still the latest release on September 26, 2026. These modes keep bare Git mirrors on the sticky disk and serve `actions/checkout` through a local proxy. They speed up checkout transport only. They do not persist the source worktree, its mtimes, or `target/`. Unlike the other modes, the action must run before checkout. The `rust` paths are under the runner home, not the workspace, so both modes can share one invocation on the same disk:

```yaml
- uses: runs-on/action@v2
  with:
    sticky_cache: |
      git
      rust
    sticky_wait_timeout: 15m
- uses: actions/checkout@v7
```

A workspace-relative record, such as `custom,path=sticky-target`, cannot share that invocation. Put it in a second `runs-on/action@v2` step after checkout. `git` and `git-full` are mutually exclusive. Prefer `git`; use `git-full` only when the workflow needs arbitrary refs or repeatedly checks out other repositories. Both modes are Linux-only and do not speed up SSH remotes, container jobs, or GitHub Enterprise Server. Size the disk for the mirror plus any other modes on it. This archive has not measured either mode. The [versioned Git-mode details](../../reference/runson-cache-and-disk-details.md#sticky-git-checkout-mode) cover proxy behavior, token handling, Cargo Git dependencies, and trust.

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

The optional `EnableStickyDiskIsolation` / `enable_stickydisk_isolation` setting removes the runner EBS permissions this legacy action needs. Migrate legacy workflows before enabling it; managed sticky disks continue through control-plane-owned EBS operations.

Prefer supported sticky disks for new post-v3.2 experiments. Keep the local snapshot action as archived evidence and as an explicit fallback when its additional lifecycle control is required.

## Storage And Isolation Notes

Use the [storage topology reference](../../concepts/storage-topologies.md) for the generic model and the [RunsOn storage details](../../reference/runson-cache-and-disk-details.md#runner-local-and-shared-storage) for platform-specific mount paths, lifetime, and availability.

- Enable Magic Cache isolation (`EnableCacheIsolation: "true"`). It is off by default, and enabling it makes the first build per repository and branch cold.
- Isolation covers the Magic Cache protocol only. Direct S3 clients and job code keep the runner role's stack-shared `cache/*` access; RunsOn recommends a separate stack for untrusted repositories.
- Local instance-store NVMe suits a disposable target with remote compiler objects. It survives reboot but loses data on stop/termination; an NVMe device name alone does not prove instance-store backing.
- Linux `extras=tmpfs` takes precedence over automatic NVMe placement and competes with compilation for RAM. It provides no cross-job durability by itself.
- EFS is an explicitly enabled Linux Flex shared filesystem. Verify that it is mounted before writing; the docs describe a missing/disabled mount as silently skipped.
- Magic Cache isolation and sticky-disk isolation are separate opt-ins. The former scopes protocol credentials; the latter removes legacy runner EBS authority.
- Never persist Cargo registry credentials, cloud credentials, or tokens on a sticky or snapshotted path. Scrub credential-bearing files before a save-capable post step.

## Ownership And Maintenance

This page owns RunsOn-specific deltas only. Cache selection lives in [Approaches](../../approaches/README.md), current conclusions live in [Decisions](../../decisions/README.md), tool setup lives in [Mise Tool Setup](../../operations/mise-tool-setup.md), and measurement procedure lives in [Measuring Cache Performance](../../operations/measuring-cache-performance.md).

Before changing this deployment map, verify the current RunsOn stack requirement, runner-label syntax, `runs-on/action` major and metadata, Magic Cache isolation behavior, sticky-disk lifecycle, `sccache` helper behavior, and S3 IAM/lifecycle assumptions. Record behavior changes according to the [maintenance checklist](../../operations/maintenance-checklist.md).

## Related Pages

- [Quickstart](../../quickstart.md)
- [Decisions](../../decisions/README.md)
- [Approaches](../../approaches/README.md)
- [Clean Target](../../approaches/clean-target.md)
- [`sccache`](../../tools/sccache.md)
- [RunsOn Cache And Disk Details](../../reference/runson-cache-and-disk-details.md)
- [Measuring Cache Performance](../../operations/measuring-cache-performance.md)
- [Target Archive Growth In Production](../../evidence/target-archive-growth.md)
- [Cache Strategy Benchmarks](../../evidence/cache-strategy-benchmarks.md)

## Proposed improvements

The [archived RunsOn sccache research](../../research/runs-on-sccache/README.md) designed a gateway, broker and trust contract for direct S3 `sccache`; RunsOn v3.5.0's isolated Magic Cache and its per-object integrations supersede most of it. Open proposals are in [Research](../../research/README.md).
