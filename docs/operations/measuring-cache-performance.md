# Measuring Cache Performance

Use this procedure to determine whether a Rust CI cache saves end-to-end time and to attribute the result to compilation, S3 transfer, archive serialization, or local storage.

## Measurement Principles

- Pair every cache strategy with the same source state, command, toolchain, features, profile, target, runner image, and workload concurrency.
- Randomize or alternate strategy order within each comparison block so time-of-day, capacity, and transient backend effects do not consistently favor one strategy.
- Record cold population, warm exact reuse, realistic source changes, and invalidating changes separately.
- Keep job wall time as the adoption metric, then explain it with phase timings, sizes, counters, and resource samples.
- Preserve intervals or start/end offsets when phases can overlap. Do not sum parallel rustc invocations, `sccache` requests, or sampled utilization and call the result wall time.
- Label every value as directly measured, log-derived, tool-reported, or inferred. Keep unavailable splits unknown or combined.
- Compare medians and tails from paired runs; do not choose an approach from one favorable run or cache hit rate alone.

Use the [cache measurement JSONL schema](../reference/cache-measurement-schema.md) for machine-readable records. The [synthetic example](../../examples/measurements/cache-measurements.example.jsonl) demonstrates the record shapes.

## Canonical Phase Map

| Phase | Includes | Primary pressure | Important companion values |
| --- | --- | --- | --- |
| Queue | Workflow eligibility until runner assignment | Capacity | Queue duration |
| Runner setup | Instance start, runner registration, checkout prerequisites | Platform | Image and runner profile |
| Tool setup | Rust, task runner, linker, and helper installation | Network, CPU, disk | Downloaded bytes and tool-cache hit state |
| Cache lookup | Key resolution and cache metadata requests | API latency | Request count and exact/fallback/miss state |
| Cache download | Archive object transfer before local extraction | Network | Compressed bytes and effective throughput |
| Archive extraction | Decompression, tar parsing, file creation, and metadata writes | CPU and local disk | Compressed bytes, restored bytes, file count, CPU time, disk writes |
| Cache scan | Directory traversal and metadata inspection before cleanup or save | Local disk and inode metadata | Files visited and scan duration |
| Cache cleanup | Removal or pruning performed by the cache owner | CPU and local disk | Bytes/files before and after cleanup |
| Workload | Complete representative build/test command | Mixed | Wall time and process resource summary |
| Cargo orchestration | Dependency graph traversal, build scripts, scheduling, and work not assigned to compilation/link/test | CPU and process overhead | Cargo timing artifact and unit count |
| Compiler-cache lookup/materialization | Per-invocation lookup, download, decompression, and output materialization | API latency, network, CPU, disk | Requests, hit/miss/error counts and object bytes |
| Compilation | Actual rustc work on cache misses or without a compiler cache | CPU, memory, local disk | rustc wall/CPU time, units, peak concurrency |
| Linking | Final link steps | CPU, memory, local disk | Linker wall/CPU time and output bytes |
| Test execution | Test process execution after build completion | CPU and workload-specific resources | Test count and wall time |
| Archive compression | Archive creation and compression after cleanup | CPU and local disk reads | Input bytes/files, output bytes, compression ratio |
| Cache upload | Transfer of the completed archive or cache object | Network | Uploaded bytes and effective throughput |
| Cache post other | Save checks, key races, metadata calls, and action overhead not captured above | Mixed | Save outcome and duplicate-writer state |
| Job total | Runner-assigned start through completion of post steps | Critical path | Exit status and billed duration |

When logs expose only a combined value such as lookup with download or archive creation with compression, store that combined phase name and document the limitation. Never split a combined duration using an assumed percentage.

## Collection Procedure

### 1. Establish The Pair

Assign an opaque pair or scenario identifier. Keep private repository names, pull-request numbers, branch names, package names, commit hashes, runner labels, S3 buckets, prefixes, and object keys out of the exported records.

Record the public or sanitized runner profile separately from the strategy:

- Architecture, vCPU count, memory, CPU model/generation, and CPU class or public instance type when disclosure is acceptable.
- A repeatable one-thread calibration when comparing processors whose single-thread performance is expected to affect rustc, linking, tar traversal, or compression.
- Advertised network class, same-region/cross-region object-store relationship, and generic endpoint path rather than an internal runner label, account, bucket, or region.
- Workspace storage type, filesystem, capacity, and whether it is local NVMe, EBS, or an unknown abstraction.
- Toolchain/compiler identity, linker class, workload concurrency, codegen settings, incremental-compilation setting, and a sanitized workload version.

#### Scenario Matrix

Predeclare the scenarios that apply to the cache mechanism. Keep each scenario in its own comparison block rather than pooling incompatible cache states or invalidation events.

| Scenario | What it tests |
| --- | --- |
| Cold namespace | Population cost, clean-build behavior, and initial persistent growth |
| Warm exact repeat | Best-case reuse and exact-key behavior |
| Source-only change | Cross-commit reuse without dependency changes |
| Lockfile or manifest change | Dependency invalidation, fallback behavior, and object growth |
| Feature change | Feature-key separation and non-cacheable work |
| Profile, target, or compiler-flags change | Build-configuration separation |
| Toolchain change | Compiler invalidation and namespace separation |
| Concurrent readers and writers | Request pressure, duplicate saves, and last-writer behavior |
| Unauthorized writer attempt | Workflow and infrastructure trust enforcement |
| Cache or backend unavailable | Fail-open behavior, timeout cost, and clean fallback |

### 2. Capture State Before Restore

Record available disk bytes/inodes, Cargo input bytes/files, target bytes/files, and compiler-cache statistics before the experiment. For a cold trial, use a fresh namespace or verified miss instead of deleting shared production data.

### 3. Mark Archive Restore And Save Boundaries

Capture monotonic offsets around cache setup and post steps. Parse action logs for finer lookup, transfer, extraction, cleanup, compression, and upload boundaries where they are emitted. Preserve both the action's total duration and the component intervals so parser gaps remain visible.

For a whole-target archive, always collect:

- Exact hit, fallback hit, miss, or save-race outcome.
- Compressed object bytes.
- Restored and post-cleanup uncompressed bytes.
- Restored and post-cleanup file count.
- Lookup, download, extraction, scan, cleanup, compression, upload, and total restore/post time when individually observable.

### 4. Measure The Workload And Compilation

Time the complete representative command with a monotonic clock and capture a process resource summary such as `/usr/bin/time -v`. Preserve Cargo's `--timings` report when the command path can enable it without changing the workload.

Use one of these labels according to what was actually measured:

| Available observation | Report as | Do not claim |
| --- | --- | --- |
| Only the task-runner or `cargo` command duration | Workload wall time | Pure compilation time |
| Cargo timing units and critical path | Cargo unit/critical-path timing | Sum of units as wall time |
| Per-rustc wrapper wall and CPU records | Compiler-request work, with overlap metadata | Sum of request durations as elapsed job time |
| A no-cache rustc invocation | Compilation request | That the same duration applies to an `sccache` hit |
| An `sccache` hit invocation | Compiler-cache lookup/materialization request | Compilation |
| A cache miss through `sccache` | Compiler-cache miss request containing compile work | A clean split between lookup, compilation, and write unless traced |

If build and test execution can be separated without changing the representative workload, time compile-only and test-execution phases separately. Otherwise retain one workload duration and mark compile/link/test as unattributed.

For `sccache`, zero statistics immediately before the workload and export statistics immediately after it, even on failure. Record compile requests, executed cacheable requests, hits, misses, non-cacheable calls, errors, reported cache size, and any latency counters exposed by the pinned version. A high hit rate does not replace workload wall time.

### 5. Sample CPU, Disk, And Network

Collect a low-frequency resource trace, normally once per second, plus process totals. Useful Linux sources include `pidstat`, `iostat`, `/proc/diskstats`, `/proc/net/dev`, and `/usr/bin/time -v`; availability varies by runner image.

Capture at least:

- CPU user, system, idle, and I/O-wait percentages.
- Process user/system CPU time, maximum RSS, and voluntary/involuntary context switches.
- Disk read/write bytes, operations, queue or latency indicators, and filesystem free bytes/inodes.
- Network receive/transmit bytes and packets.
- Peak rustc concurrency or process count.

System-wide network counters include unrelated runner traffic. Treat them as supporting evidence unless the experiment isolates the interface and time window. Do not export packet captures, environment dumps, command lines containing secrets, or verbose cloud SDK logs without sanitization.

Before relying on detailed traces, measure their overhead by running the same no-cache workload with detailed sampling disabled and enabled. Keep the sampling cadence and tool set fixed afterward, and report any material measurement overhead.

### 6. Capture State Afterward

Repeat byte/file/inode measurements and record save outcome, cache growth, compiler-cache statistics, billed runner duration, estimated cost per successful job, persistent bytes by mechanism, and any failure, timeout, cancellation, fallback, or duplicate-writer behavior. Preserve raw private logs outside this archive; export only sanitized derived records.

## Repetition And Stopping Rules

Treat the first 10 paired observations per representative scenario as exploratory evidence for central tendency, not automatic proof of a winner. Do not describe p90 or p95 as stable from only 20–30 jobs; tail claims normally require substantially more comparable observations.

Before collecting results, declare the minimum effect that matters, the intended precision or uncertainty interval, the maximum sampling budget, and the stopping rule. Report sample count, spread, uncertainty, exclusions, and any early stopping. Do not combine cold, warm, changed-source, invalidation, or different runner-profile observations merely to increase the sample count.

## Attributing CPU, S3, And Storage

Changing instance type often changes CPU, network, memory, and storage together. A faster run on another instance therefore proves that the complete runner profile is faster, not which resource caused the change.

| Question | Controlled comparison | Evidence of sensitivity |
| --- | --- | --- |
| Does better CPU reduce clean compilation? | Same source, no cache, same storage class and workload concurrency; include a one-thread calibration | Lower compile/workload wall time with high CPU utilization and a consistent single-thread difference |
| Does better CPU reduce archive serialization? | Extract and compress the same local archive on each runner | Lower extraction/compression time without proportional storage throughput change |
| Does S3 bulk transfer dominate? | Download/upload the same object without extraction/compression | Transfer time scales with network throughput; local serialization does not |
| Do S3 request latency and concurrency dominate `sccache`? | Same warm object set and workload, compare request latency/count while keeping CPU similar | High cache-hit request time with low bulk bytes and idle CPU gaps |
| Does local NVMe help archive restore/save? | Extract, scan, clean, and compress the same local tree on otherwise comparable runners | Lower metadata/file-operation time and disk queueing |
| Does local NVMe help compilation/linking? | Same cold no-cache workload on otherwise comparable runners | Lower target-write/link time with prior disk saturation |

Network configuration and instance selection can be optimized in the same final design, but attribution requires staged measurements:

1. Measure the current runner with phase instrumentation.
2. Change one factor where practical: CPU profile, S3 path/configuration, or local storage.
3. If two factors are expected to interact, run a two-by-two comparison with both current, each improvement alone, and both improvements together.
4. Confirm the combined winner on the complete representative workflow.

For archive caches, reducing archive bytes and file count usually improves transfer, extraction, traversal, compression, and upload together. For `sccache`, distinguish many small-object request latency from bulk bandwidth; an instance with higher advertised network throughput can still lose when compiler throughput or per-request latency is the limiting factor. Record S3 request counts and latency distributions when the backend exposes them, but use workflow-side monotonic timings as the per-run source of truth when shared backend metrics cannot isolate one job.

For a separately authorized S3 compiler-cache diagnostic in an isolated test namespace, benchmark representative object sizes with bounded parallel PUT and GET operations at concurrency 1, 4, 8, 16, and 32. Record object-size distribution, latency percentiles, throughput, retries, failures, route/endpoint class, and encryption mode.

For compression attribution, compare supported settings on the same runner, source state, backend, namespace, and workload. Run each setting for both cold population and warm reuse, and capture workload/job wall time, compiler CPU, request duration, stored and transferred bytes, and request counts.

## Derived Metrics

Calculate derived values from the measured records:

| Metric | Calculation |
| --- | --- |
| Download throughput | Compressed downloaded bytes / cache download seconds |
| Extraction throughput | Restored uncompressed bytes / archive extraction seconds |
| Compression throughput | Post-cleanup input bytes / archive compression seconds |
| Upload throughput | Uploaded compressed bytes / cache upload seconds |
| Compression ratio | Uncompressed input bytes / compressed archive bytes |
| Cache handling share | Union of cache intervals on the critical path / job wall time |
| Net cache benefit | Paired no-cache job wall time − cached job wall time |
| Cache return on overhead | Workload time avoided / cache setup and post critical-path time |
| Compiler-cache hit rate | Hits / executed cacheable requests |
| Compiler-cache error rate | Errors / executed cacheable requests |
| Phase coverage | Measured exclusive critical-path time / job wall time |

Use interval unions for cache handling share when phases overlap. Report summed compiler CPU or request work as CPU/work totals, not as elapsed time.

## Reporting Tables

### End-To-End Decision Table

| Strategy | Cache state | Runner profile | Job | Workload | Restore critical path | Post critical path | Net vs paired baseline | Cost / successful job | Persistent bytes | Operational/trust risk | Decision |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| … | … | … | … | … | … | … | … | … | … | … | … |

### Archive Breakdown

| Strategy | Object | Files | Lookup | Download | Extract | Scan | Cleanup | Compress | Upload |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| … | … | … | … | … | … | … | … | … | … |

### Compiler-Cache Breakdown

| Strategy | Requests | Cacheable | Hits | Misses | Non-cacheable | Errors | Workload | Request wall sum | Request CPU sum |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| … | … | … | … | … | … | … | … | … | … |

### Runner Resource Comparison

| Runner profile | No-cache compile/workload | Archive extract | Archive compress | S3 download | S3 upload | Warm compiler-cache workload |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| … | … | … | … | … | … | … |

Report median and tail values only at the precision supported by the repetition plan, plus sample count, spread, uncertainty, and limitations. Keep exact organization-specific comparisons in their private operational context; only sanitized evidence belongs in this archive.

## Adoption And Rollback Gate

Before inspecting results, predeclare adoption thresholds for end-to-end benefit, acceptable cold and tail regressions, cache errors, cost per successful job, persistent growth, and operational or trust risk. A higher hit rate alone does not pass the gate.

Test an unauthorized write and a backend outage. An optional cache should fail open to the clean direct-build path; if the mechanism cannot do that, record the cache as a required dependency and include its failure mode in the decision. Keep the experiment non-required until rollback has been rehearsed, including disabling the cache, returning to direct `rustc` or a clean target, and safely abandoning or expiring persistent state.

## Related Pages

- [Cache Measurement JSONL Schema](../reference/cache-measurement-schema.md)
- [Target Archive Growth In Production](../evidence/target-archive-growth.md)
- [Cache Strategy Benchmarks](../evidence/cache-strategy-benchmarks.md)
- [RunsOn Cache And Disk Details](../reference/runson-cache-and-disk-details.md)
- [Diagnosing Cargo Rebuilds In CI](diagnosing-rebuilds.md)
