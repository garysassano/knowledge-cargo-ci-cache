# Proposed sticky local sccache tier

Status: Proposed and untested integration work. This page specifies requirements; it does not describe a released RunsOn feature. Use [the research index](README.md) for scope, sequencing, and the [version refresh](../../reference/compiler-cache-implementation.md#release-refresh-2026-09-06).

## Cargo persistence experiment

The [proposed Cargo sticky-disk workflow](sticky-cargo-canary.yml) preserves the input-only and input-with-target experiment shapes. It is linted research material, not a measured canary or a sticky sccache implementation. It restricts publication candidates to the default branch, serializes each mode, keeps mutable target state outside the cached source worktree, and removes untracked worktree files. Sizes and runner labels are illustrative; verify actual stack version, lineage authority, capacity, and cost before running it. Workflow concurrency is not infrastructure-enforced publication fencing. Copy it into a workload repository only for an explicitly selected experiment, then record its first measurements before promoting it into the archive's main examples.

## Current Boundary

The draft target variant also requires the [cached-worktree checkout action](../../../examples/actions/cached-worktree-checkout/action.yml) at the repository path it invokes. Copy and review that local action when adapting the workflow to another repository.

RunsOn's built-in sticky `rust` mode persists Cargo registry and Git directories, not `SCCACHE_DIR`. An ephemeral `disk,s3` L0 therefore dies with the runner and cannot accelerate the next job.

The existing evidence shows why persistence is necessary for a useful cross-job L0, but it does not prove that a sticky L0 will outperform direct S3 after snapshot restore, commit, GC, and concurrency costs.

Released sticky disks require RunsOn v3.2 or later. Set `sticky_wait_timeout: 15m` explicitly and distinguish terminal unavailability from missing agent configuration or a readiness timeout: v2.3.1 continues cold only for the explicit unavailable marker. The [versioned failure contract](../../reference/runson-cache-and-disk-details.md#sticky-disk-failure-boundary) owns the source/documentation discrepancy and expected states. Inactive lineages expire after ten days, so unexpected cold restoration is normal platform behavior rather than proof of corruption.

## Candidate shapes

| Shape                                              | Cross-job reuse     | Remote sharing | Qualification dependency              |
| -------------------------------------------------- | ------------------- | -------------- | ------------------------------------- |
| Sticky local-only `sccache`                        | Same lineage        | No             | Narrow experiment                     |
| Sticky `disk,s3` managed directly by `sccache`     | Same lineage and S3 | Yes            | Requires upstream drain; experimental |
| Sticky L0 managed by RunsOn gateway with S3 origin | Same lineage and S3 | Yes            | Requires gateway ownership and drain  |

A gateway can give one component ownership of the local directory, remote queue, integrity, and snapshot ordering. Compare that benefit with the implementation cost; the [roadmap](roadmap.md#qualify-larger-experiments-only-when-needed) permits a directly managed sticky experiment first.

## Ownership Marker

The persistent data root should contain a small marker:

```json
{
  "schema": "runs-on-sccache-local/v1",
  "cache_format": "sccache-v2",
  "owner": "runs-on-gateway",
  "binary_version": "opaque-version",
  "os": "linux",
  "arch": "x86_64",
  "trust_domain": "opaque-digest",
  "namespace_schema": "sccache/v2",
  "clean_shutdown": true
}
```

On startup:

1. Acquire an exclusive filesystem lock.
2. Verify marker schema, platform, trust domain, and owner.
3. Reject a live conflicting PID, socket, or lock.
4. Quarantine incompatible or corrupt state rather than mutating it in place.
5. Mark the directory dirty before serving requests.
6. Start the sole cache owner.

On post:

1. Quiesce producers and account for remote writes through the [shared post transaction](action-lifecycle.md#post-transaction), before its optional snapshot publication step.
2. Record its terminal counts before marking filesystem state clean.
3. `fsync` data and metadata, run `syncfs`, atomically write or rename the clean marker, and `fsync` its parent directory.
4. Stop the cache owner and verify no process or open handle holds the directory.
5. Freeze or unmount the filesystem so the snapshot is crash-consistent.
6. Request the snapshot while the remote lineage lease and fencing token remain valid.
7. Publish the external platform-owned lineage pointer only after snapshot creation succeeds and only with predecessor-checked compare-and-swap.
8. Thaw or remount the filesystem if the runner continues, otherwise terminate it.

Runtime sockets, PIDs, logs, credentials, and temporary presigned URLs belong outside the persistent data root.

The clean marker is local consistency metadata, not security proof: root-capable workflow code can forge it. A failed, cancelled, timed-out, lease-expired, fenced, or missing-post job never publishes a sticky snapshot or advances the lineage pointer.

## Concurrency And Lineage

RunsOn sticky jobs restore independent volumes from a lineage snapshot; concurrent completions do not merge, and each clone can acquire its own local filesystem lock. Local locks establish one process owner inside one restored volume but cannot fence publication to the shared lineage.

Choose one:

- One remotely leased and fenced sticky-cache publisher with other jobs read-only or copy-on-write.
- Workflow concurrency that serializes candidate writers as an optimization, not the authoritative lock.
- Separate lineages by trust domain and workload class.
- Read-only default-branch snapshot consumption with private branch writes discarded.

The platform stores lineage generation, predecessor, fencing epoch, trusted publisher identity, snapshot ID, status, and timestamps outside the mutable volume. A losing, expired, failed, cancelled, or timed-out publisher discards its snapshot. Do not let arbitrary concurrent jobs publish divergent LRU state into one logical lineage and assume the hot sets merge.

## Capacity And GC

Record:

- Configured cache maximum.
- Sticky volume size.
- Object count and bytes.
- Free bytes and free inodes before and after the job.
- Evicted objects and bytes.
- GC duration.
- Snapshot restore and commit duration.
- Corrupt or quarantined bytes.

The cache maximum should leave explicit headroom for filesystem metadata, temporary objects, spill files, and snapshot operations. RunsOn's platform reset thresholds are emergency behavior, not a desired operating point.

Inject the released [capacity warning and reset thresholds](../../reference/runson-cache-and-disk-details.md#sticky-disk-capacity-and-reset), including reset skipped while in use. Record whether reset occurred and verify a controlled cold path without partial or cross-trust publication.

GC should be owned by the local cache process and run with a bounded time budget. A failed GC must be visible and must not race another server.

## Unsupported Shared Filesystems

Do not place one mutable local `SCCACHE_DIR` on EFS, FSx, NFS, or another concurrently mounted shared filesystem. The local LRU expects one server owner, and remote metadata latency plus multi-writer coordination changes both correctness and performance.
