# Cache Primitives

Cargo CI caching experiments used several different storage primitives. They are not interchangeable, even when they all make a later build faster.

## Archive Cache

Examples:

- `actions/cache`
- An `actions/cache`-compatible backend
- `Swatinem/rust-cache`, which builds on top of archive cache semantics

Changing the backend used by `actions/cache` does not change archive-cache semantics. The restored state is still selected by a key, downloaded, and extracted into the current filesystem. It is not equivalent to a mounted filesystem snapshot. See the [RunsOn deployment map](../deployments/runs-on/README.md) for platform-specific implementations.

Archive cache behavior:

```text
compute key
download archive if key/restore-key matches
extract files into current filesystem
optionally clean/prune paths
upload new archive under a key
```

Best for:

- Download archives.
- Cargo registry/cache data.
- Dependency-oriented target artifacts.
- Setup action tarballs.
- Tool installer caches.
- `mise-action` tool installs under `MISE_DATA_DIR`.

Limitations:

- Extraction reconstructs files into a fresh filesystem.
- The cache key decides whether a new archive can be saved.
- Archive tools and cache actions may not preserve all metadata exactly as a local filesystem would.
- A cache action can clean or prune paths before save.

## Compiler-Object Cache

Example:

- `sccache` with an S3 backend.

Compiler-cache behavior:

```text
Cargo invokes compiler through wrapper
compute key from compiler and invocation inputs
fetch one matching output on hit
compile and optionally store one output on miss
```

Best for:

- Reusing unaffected compilation across changing commits.
- Keeping `target/` disposable.
- Avoiding monolithic target archive extraction and recompression.

Limitations:

- Cargo orchestration still runs.
- Remote hits still perform many object operations.
- Build scripts, linker-invoking crate types, and final linking remain local or non-cacheable.
- Object-store lifecycle, namespace, IAM, and request cost need ownership.

## Filesystem Snapshot

Examples:

- EBS snapshot restore.
- `runs-on/snapshot`-style mounted volume workflows.

Filesystem snapshot behavior:

```text
restore volume from snapshot
mount filesystem
build using paths inside mounted filesystem
unmount/detach
snapshot resulting filesystem
```

Best for:

- Reproducing local no-op Cargo behavior.
- Preserving exact target state, dep-info, fingerprints, build script outputs, and registry source trees.
- Workflows where the operational cost of volume lifecycle is acceptable.

Limitations:

- More infrastructure and lifecycle complexity.
- Credential-bearing files must be scrubbed before snapshot save.
- Toolchains and tool caches can bloat snapshots if placed under the snapshot root.

## Sticky Persistent Disk

Example:

- RunsOn sticky disks backed by EBS snapshots.

Sticky-disk behavior:

```text
restore newest clean disk snapshot for a lineage
attach and mount native filesystem
build directly on the disk
unmount and record a new clean snapshot
```

Best for:

- Native Cargo-input persistence without tar archive serialization.
- Experimental full target persistence when exact filesystem continuity is worth the lifecycle controls.

Limitations:

- A persistent target can still accumulate stale artifact generations.
- Disk bytes, free space, free inodes, cleanup, reset, and concurrent last-writer behavior must be managed.
- Platform-specific version and runner-label requirements apply.

## Network Filesystem

Examples:

- [Amazon S3 Files](https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-files.html).
- Other remote filesystems exposed as local mount paths.

Network filesystem behavior:

```text
mount shared filesystem
read/write Cargo state directly on the mount
optional prewarm or local copy
unmount
```

Best for:

- Shared file access workloads.
- Cases where many clients need a common filesystem namespace.

Limitations for Cargo target state:

- Cargo no-op traverses many small metadata, fingerprint, dep-info, and build-script files.
- Remote filesystem metadata/read latency can dominate even when Cargo is logically fresh.
- Prewarming often moves cost rather than removing it.

## Choosing A Primitive

| Goal | Preferred primitive |
| --- | --- |
| Keep workflow simple and attributable | Clean target with no Rust cache or input-only `rust-cache` |
| Avoid dependency downloads | Input-only archive cache or sticky Cargo-input disk |
| Reuse compiler outputs across changing commits | S3-backed `sccache` |
| Preserve source mtimes | Cached worktree, sticky workspace, or filesystem snapshot |
| Preserve full local target state | Sticky/custom disk, filesystem snapshot, or tightly bounded source-keyed target archive |
| Cache setup tools and toolchains | Archive cache through `mise-action` |
| Share state across workers without archives | Network filesystem, but not ideal for Cargo target no-op |
