# Target Archive Growth In Production

This page records sanitized production observations from a large Rust monorepo. Repository names, private workflow links, package names, and organization-specific configuration are intentionally omitted. Controlled strategy comparisons live in [Cache Strategy Benchmarks](cache-strategy-benchmarks.md).

## Question

Did a whole-target `Swatinem/rust-cache` archive stop paying for itself, and did disabling it make pull-request CI slower?

## Test Setup

The observations come from successful production PR jobs, with runner queue time excluded. Timing windows are labelled with the population they summarize because lightweight and substantive jobs were mixed.

The detailed degraded-archive job is preserved as sanitized phase-level JSONL:

- [Degraded target archive](data/target-archive-degraded-sample.jsonl)

The file uses the [cache measurement schema](../reference/cache-measurement-schema.md). Combined phases remain combined where the original logs did not expose a reliable split.

## Observations

### Whole-Target Archive Growth

A new cache lineage began at about 206 MB compressed. Broad fallback restores then copied the newest older target tree into jobs with changed exact keys, after which Cargo added another artifact generation and the complete combined tree was saved under a new immutable key.

Selected progression:

| Stage | Compressed target-cache object |
| --- | ---: |
| New lineage | 206 MB |
| First large partial-restore save | 2.86 GB |
| Next partial-restore save | 4.15 GB |
| Later partial-restore save | 8.88 GB |
| Later partial-restore save | 12.79 GB |
| Under five days after the new lineage began | 13.89 GB |
| Later observation | 17.82 GB |

The 206 MB to 13.89 GB change was a 67.36-fold increase. Growth was bursty around partial restores rather than a stable daily rate.

### Representative Degraded Job

| Work | Duration | Share or interpretation |
| --- | ---: | --- |
| Target-cache restore | 236s | Mostly local extraction |
| Build and test | 230s | The useful workload |
| Target-cache post/save | 358s | Mostly compression/archive creation |
| Total cache handling | 594s | 65.8% of a 903s job |
| Cache handling divided by build time | 2.58× | Cache work cost more than twice the build |

The restored object was about 13.8 GB compressed. Lookup and download took about 39.5 seconds, while local extraction took about 196.2 seconds. During save, compression and archive creation took about 325 seconds, while upload took about 28 seconds.

This identifies archive serialization and filesystem work as the dominant bottleneck. A faster S3 backend or a larger cache quota would not remove the need to extract and recompress the complete target tree.

### Concurrent Save Duplication

Two concurrent jobs restored the same roughly 13.8 GB fallback object and attempted to save almost identical 13.89 GB objects under the same new exact key. The first completed object became canonical; the other job still paid the full cleanup, compression, and save attempt without creating reusable state.

Restricting target-cache writes to one trusted canonical job avoids this redundant work. It does not fix a large restore or bound growth by itself.

### Pipeline Timing Before And After Target Caching Was Disabled

Queue delay remained around 24 seconds, so runner congestion did not explain the change.

| Production window | Median | p90 | Population |
| --- | ---: | ---: | --- |
| Earlier compact-cache baseline | 7.2m | 10.7m | All successful PR runs |
| Later pre-change baseline | 8.5m | 13.0m | All successful PR runs |
| After disabling target caching | 13.1m | 22.9m | All successful PR runs |
| After disabling target caching | 20.1m | 22.9m | Substantive runs lasting at least five minutes |

The post-change all-run median is diluted by lightweight or no-op jobs. The substantive-run filter better represents jobs that perform the full Rust workload.

The change therefore did make substantive jobs slower than the earlier healthy, compact target-cache period: clean runners now compile rather than reusing a ready target tree. It did not single-handedly create every 15–20 minute run. Before target caching was disabled, the oversized archive had already produced similarly slow and unstable jobs by replacing compile time with restore and save overhead.

The practical result was a trade:

```text
small healthy target archive -> strong reuse and short jobs
oversized target archive     -> unstable jobs dominated by archive handling
clean target                 -> predictable but compilation-heavy jobs
```

### Input-Only Cache After The Cutover

The replacement input-only archive stabilized around 200 MB. One warm production restore took about two seconds, and PR saves were disabled. It removed the target-growth failure but did not reuse compiler output, so representative full-workload build steps took roughly 18–20.5 minutes.

## Upstream Cleanup Check

As checked on August 20, 2026, `Swatinem/rust-cache@v2` resolves to release v2.9.2. Upstream [PR #377](https://github.com/Swatinem/rust-cache/pull/377) is merged on the upstream default branch but is not included in v2.9.2 or the movable `v2` tag.

The change makes the existing one-week age sweep inspect every immediate directory entry after a partial restore instead of stopping after the first entry. It does not add a byte limit, generation-aware deduplication, LRU policy, fingerprint validation, or recursive pruning of every nested Cargo artifact generation.

The observed 206 MB to 13.89 GB growth happened in less than one week, so even the corrected age sweep would not have bounded this incident.
## Interpretation

- Whole-target caching was beneficial while its archive was compact and consistent.
- The tested broad fallback lineage was effectively copy-forward and not size-bounded. Over time, archive handling became slower than the build it was intended to avoid.
- Concurrent writers can duplicate the most expensive save work while only one immutable object wins the key.
- Archive serialization and filesystem work, not S3 transfer, dominated both the degraded restore and the degraded save.
- Disabling target caching traded unstable archive overhead for predictable cold compilation. It is a safe containment action, not necessarily the fastest steady state.
- The replacement input-only archive removed the growth failure without reusing any compiler output, which is what motivated the controlled comparisons in [Cache Strategy Benchmarks](cache-strategy-benchmarks.md).

## Limitations

- The observations come from one anonymized monorepo and should guide experiments rather than serve as universal performance guarantees.
- Production windows contained different mixes of lightweight and substantive jobs, which is why the filtering method is stated explicitly.
- Production jobs are not controlled trials: source, dependency graph, and workload composition changed across the observed windows.
- Runner price, Spot availability, S3 request cost, and cache storage cost were not included in the timing comparison.

## Implications

- Do not run a whole-target archive without recording compressed bytes, restored bytes, file count, restore time, save time, and exact/partial hit state.
- Do not add a broad target `restore-keys` fallback that can copy an older mutable target tree into each new immutable object.
- Restrict target-cache writes to one trusted canonical job so concurrent savers do not repeat the most expensive work.
- Use [Clean Target: No Cache Or Cargo Inputs Only](../approaches/clean-target.md) as the containment baseline, then compare strategies with [Cache Strategy Benchmarks](cache-strategy-benchmarks.md).
