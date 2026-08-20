# Cache Strategy Benchmarks

This page records controlled and representative comparisons between no Rust cache, input-only Cargo caching, whole-target archives, and S3-backed `sccache` modes. Repository names, private workflow links, package names, and organization-specific configuration are intentionally omitted. The production incident that motivated these trials is in [Target Archive Growth In Production](target-archive-growth.md).

## Question

With a clean `target/` as the starting point, which cache strategy produces the best end-to-end job time, and does S3-backed `sccache` provide enough reuse to be a better long-term design than a whole-target archive?

## Test Setup

The evidence has two parts:

1. A representative full-workload comparison of cache strategies and `sccache` modes, described in detail below.
2. A controlled `cargo check --all-targets` comparison on fresh 16-vCPU runners. Each strategy ran twice on an independent runner, and the `sccache` namespace was already warm for the corrected comparison.

The controlled strategies were:

| Strategy | Cargo inputs | Compiler outputs | Target state at job start |
| --- | --- | --- | --- |
| Input-only `rust-cache` | Registry and Git inputs restored | Not cached | Clean |
| No Rust cache | Downloaded normally | Not cached | Clean |
| Input-only cache with S3 `sccache` | Registry and Git inputs restored | Eligible compiler calls cached individually | Clean |

The representative full-workload trials are preserved as sanitized phase-level JSONL:

- [Full-workload clean-target and compiler-cache trials](data/compiler-cache-full-workload-sample.jsonl)

The file uses the [cache measurement schema](../reference/cache-measurement-schema.md). Combined phases remain combined where the original logs did not expose a reliable split.

## Representative Full-Workload Cache Experiment

The fixed representative workload covered the same monorepo build, lint, and test task set in every arm. The available c8a, m8a, and r8a runner-family choices used the same AMD EPYC 9R45 processor model; the observed trials used c8a and m8a, whose RAM and storage profiles differed. No significant resource constraint or memory pressure was detected. The c8a and m8a observations were not controlled cross-family trials and do not support a performance ranking between c8a, m8a, and r8a; strategy comparisons use same-profile controls.

### End-To-End Results

| Strategy and state | Trials | Workload wall time | Job wall time | Interpretation |
| --- | ---: | ---: | ---: | --- |
| Input-only archive, warm exact hit | 2 | 20m38.242s, 21m06.196s | 22m05s, 22m33s | Control average: 20m52.219s workload, 22m19s job |
| No Rust cache | 2 | 20m36.417s, 21m20.929s | 22m01s, 22m45s | Control average: 20m58.673s workload, 22m23s job |
| S3 `sccache` 0.17 default server mode with input-only `rust-cache`, population run | 1 | 25m54.103s | 27m23s | 21.3% slower workload than the same-profile no-cache trial |
| S3 `sccache` 0.17 default server mode with input-only `rust-cache`, warm repeat | 1 | 10m11.120s | 11m42s | 52.3% less workload time and 48.6% less job time than the same-profile no-cache trial |
| S3 `sccache` 0.17 default server mode without input archive, warm repeat | 1 | 9m50.353s | 11m14s | Preserved 6,929 hits with zero misses; directionally faster than the warm run with input-only `rust-cache` |
| S3 `sccache` 0.17 client-side mode with input-only `rust-cache`, population run | 1 | 26m42.863s | 29m02s | Did not improve cold population |
| S3 `sccache` 0.17 client-side mode with input-only `rust-cache`, warm repeat | 1 | 20m59.720s | 22m25s | 98.4% hit rate did not produce a useful warm speedup |
| S3 `sccache` 0.17 read-only empty namespace with input-only `rust-cache` | 1 | 24m57.112s | 26m25s | Isolated miss lookup, hashing, wrapper, and miss-handling overhead without successful writes |
| S3 `sccache` 0.17 client-side `disk,s3` with input-only `rust-cache`, population run | 1 | 26m21.958s | 27m49s | Background S3 writes did not improve cold wall time and did not all finish before teardown |
| S3 `sccache` 0.17 client-side `disk,s3` with input-only `rust-cache`, warm repeat | 1 | 20m42.113s | 22m05s | 96.3% hit rate produced only a small improvement over no cache and remained far slower than default server mode |
| Whole-target archive, population run | 1 | 21m10.816s | 25m21s | Workload tied the same-profile no-cache trial, but the cold save made the job 11.4% slower |
| Whole-target archive, warm exact hit | 1 | 10m27.136s | 13m49s | 51.0% less workload time and 39.3% less job time than the same-profile no-cache trial |

Across the two controls, input-only caching saved an average 6.454 seconds of workload time and four seconds of job time relative to no Rust cache. That 0.5% workload difference is operationally a tie at this sample size.

The warm default-server `sccache` repeat saved 11m09.809s of workload time and 11m03s of job time relative to its same-profile no-cache control. It also saved 10m55.076s of workload time and 10m51s of job time relative to the same-profile input-only control.

The original default-server, client-side, read-only, and multilevel `sccache` trials all included input-only `Swatinem/rust-cache` with `cache-targets: false` and `cache-bin: false`. This shared layer keeps the server-versus-client and direct-S3-versus-multilevel comparisons internally comparable. Only the later default-server warm ablation omitted it.

That ablation retained the same fixed workload, isolated compiler-cache namespace, `sccache` version, server mode, and 16-vCPU same-CPU family selector. It completed in 9m50.353s workload and 11m14s job time with 6,929 hits and zero misses. That was 20.767 seconds faster in the workload and 28 seconds faster at the job level than the earlier warm run with the input archive. The ablation ran on a different family with the same AMD EPYC 9R45 CPU model, and only one trial was collected, so the difference is directional. It shows no compiler-cache reuse benefit from keeping `Swatinem/rust-cache` beside warm `sccache`; a separate Cargo-input archive should still be measured if registry or Git downloads are material.

The result does not prove that the two actions directly interfere. Input-only `rust-cache` owns Cargo registry and Git inputs, while `sccache` owns eligible compiler outputs. `rust-cache` also exports `CARGO_INCREMENTAL=0`, but the workflow already set that value explicitly. On a partial archive restore the action can pre-clean workspace target directories even with `cache-targets: false`, but the measured warm archive restore was an exact hit. Its complete restore step took only 1.607–2.015 seconds, so archive restore time alone does not explain the 20.767-second workload difference. Indirect filesystem or scheduling effects and ordinary run variance remain possible.

The warm whole-target exact hit saved 10m53.793s of workload time and 8m56s of job time relative to the same-profile no-cache control. Its workload was 16.016 seconds, or 2.6%, slower than warm `sccache`, while its job was 2m07s, or 18.1%, slower because it restored and extracted the complete archive before beginning the workload.

### Input-Only Restore Phases

| Phase | Observed range |
| --- | ---: |
| Compressed Cargo-input archive | About 200–210 MB |
| Lookup | 63–68ms |
| Download | 0.778–1.201s |
| Extraction | 0.193–0.196s |
| Complete cache action | 1.607–2.015s |
| PR post-save | Disabled |

The input archive itself was healthy and inexpensive. It nevertheless produced no measurable workload improvement because dependency-download avoidance was small relative to the roughly 21-minute compile, lint, and test workload.

### Fresh Whole-Target Archive Trial

The exact-key whole-target trial started from an empty namespace, saved once, and then reran the identical source and workload. It used normal checkout and the action's default `cache-workspace-crates: false`, so the archive was not a complete persistent build directory and the experiment does not isolate source-mtime effects.

| Phase or metric | Cold population | Warm exact hit |
| --- | ---: | ---: |
| Cache lookup | 88ms miss | 46ms hit |
| Compressed archive | 7,599,320,203 bytes | Same object |
| Download | Not applicable | 26.161s |
| Extraction | Not applicable | 90.998s |
| Complete restore | Miss path only | 117.208s |
| Workload | 21m10.816s | 10m27.136s |
| Target after workload | 55,013,614,189 bytes; 46,647 files | 55,013,614,206 bytes; 46,647 files |
| Cleanup before save | 1.561s | Not applicable |
| Archive creation and compression | About 140.912s | Not applicable |
| Upload | About 20.806s | Not applicable |
| Complete post step | 2m44s | 92ms, save skipped on exact hit |
| Job | 25m21s | 13m49s |

The cold workload was effectively tied with no cache: it was 10.113 seconds, or 0.8%, faster than the same-profile no-cache trial. The end-to-end cold job was nevertheless 2m36s slower because it created, compressed, and uploaded a 7.60 GB archive.

The cold save was dominated by local archive creation and compression, not S3 transfer. Compression and archive creation took about 140.9 seconds, while upload took about 20.8 seconds. The warm restore showed the same local-cost pattern: downloading took 26.2 seconds, while extraction took 91.0 seconds.

The warm exact hit materially reused target state and roughly halved workload time, but it did not produce a Cargo no-op. The archive excludes workspace-crate artifacts by default, normal checkout does not preserve source mtimes, and the fixed workload includes orchestration, linking, and tests beyond reusable dependency artifacts. This trial therefore demonstrates useful warm target reuse, not complete build-directory persistence.

### Default-Server Full-Workload `sccache` Statistics

| Metric | Population run | Warm repeat |
| --- | ---: | ---: |
| Compile requests | 8,350 | 8,350 |
| Executed cacheable requests | 6,929 | 6,929 |
| Cache hits | 1,329 | 6,928 |
| Cache misses | 5,600 | 1 |
| Non-cacheable calls | 1,421 | 1,421 |
| Rust hits / misses | 2 / 5,136 | 5,137 / 1 |
| Cache writes | 5,599 | Not material |
| Cache errors | Not captured | 0 |
| Aggregate cache-operation duration | 345.129s of writes | 645.039s of read hits |
| Average observed operation | 61.6ms per write | 93.1ms per read hit |

The aggregate cache-operation durations overlap because many compiler requests execute concurrently. They are request-work totals, not elapsed phases, which is why the warm read-hit sum can exceed workload wall time.

The population run demonstrates the combined cost of compiling misses, looking up remote objects, and uploading thousands of resulting objects in the same job. The warm repeat demonstrates that default server mode can reuse nearly all eligible compiler work and materially reduce a complete workload even though 1,421 calls remained non-cacheable.

### `sccache` 0.17 Mode Follow-Up

The original direct-S3 population and warm logs were rechecked and both reported `sccache` 0.17.0 in its default server mode. Follow-up trials used fresh isolated namespaces to compare client-side direct S3, a read-only cold control, and client-side multilevel `disk,s3`. All of those mode-comparison trials included the same input-only `Swatinem/rust-cache` layer; only the separately labelled default-server ablation omitted it. The fixed workload and compiler settings were preserved, but some follow-up trials used different c8a/r8a memory and storage profiles; all selected families used the same AMD EPYC 9R45 processor model. Cross-profile timing differences remain directional rather than controlled family rankings.

| Variant | Cargo-input archive | State | Workload | Job | Hits / misses | Key observation |
| --- | --- | --- | ---: | ---: | ---: | --- |
| Default server with direct S3 | Input-only `rust-cache` | Population | 25m54.103s | 27m23s | 1,329 / 5,600 | Strong cold regression |
| Default server with direct S3 | Input-only `rust-cache` | Warm | 10m11.120s | 11m42s | 6,928 / 1 | Strong warm result |
| Default server with direct S3 | None | Warm | 9m50.353s | 11m14s | 6,929 / 0 | Fastest measured warm result; one cross-family ablation |
| Client-side with direct S3 | Input-only `rust-cache` | Population | 26m42.863s | 29m02s | 1,330 / 5,441 | 5,441 writes; no cold improvement |
| Client-side with direct S3 | Input-only `rust-cache` | Warm | 20m59.720s | 22m25s | 6,661 / 110 | High hit rate concealed a slow remote-read path |
| Default server with direct S3, read-only | Input-only `rust-cache` | Empty namespace | 24m57.112s | 26m25s | 0 / 6,929 | No successful writes; most cold penalty remained |
| Client-side with `disk,s3` | Input-only `rust-cache` | Population | 26m21.958s | 27m49s | 1,324 / 5,447 | 5,447 local writes, but only 5,197 S3 writes completed |
| Client-side with `disk,s3` | Input-only `rust-cache` | Warm partial | 20m42.113s | 22m05s | 6,521 / 250 | Ephemeral L0 had no cross-job hits; remote reads remained expensive |

The read-only cold control was 3m36.183s, or 16.9%, slower than the same-profile no-cache workload even though it successfully uploaded nothing. Default-server read-write cold added only 56.991 seconds over that read-only trial. This means successful uploads contributed to the cold regression but did not explain most of it. Hashing, remote miss lookups, wrapper and miss handling, compiler-process interactions, and run variance remained on the path. The reported 6,929 write errors in the read-only trial were expected policy rejections rather than backend failures.

Client-side mode removed the local daemon path but was not faster in this remote-object workload. Its cold workload was 48.760 seconds slower than default server mode, and its warm workload took 20m59.720s despite 6,661 hits and only 110 misses. The v0.17.0 release description accurately identifies a removed round trip and daemon bottleneck, but its demonstrated performance improvement was workload-specific rather than a general guarantee. In this direct-S3 CI workload, removing the daemon did not compensate for remote object reads and the other per-request work; end-to-end measurement is required.

With the default multilevel `l0` write policy, the local disk write is awaited and later S3 writes run in background tasks. The population trial recorded 5,447 local writes totaling 1.717 seconds of overlapping request work and 5,197 completed S3 writes totaling 283.316 seconds. About 250 expected remote writes, or 4.59%, had not completed when statistics were captured and the job ended. The warm repeat then reported 250 misses—the same count as the prior run's incomplete writes—alongside 6,521 hits, 670.029 seconds of overlapping read-hit duration, and a 20m42.113s workload. Its fresh ephemeral L0 disk recorded no hits, so `disk,s3` supplied no persistent near-cache benefit across jobs. The result was only 38.816 seconds faster than the same-profile no-cache workload and 10m30.993s slower than default-server warm `sccache`. A workflow that depends on remote persistence would need an explicit completion or drain mechanism rather than assuming background writes survive runner teardown.

## Controlled Compiler-Cache Benchmark

This shorter benchmark compared c8a with m8idn, which is a different runner and CPU-family comparison from the same-processor c8a/m8a/r8a full-workload selection above. Its result must not be generalized into a c8a-versus-m8a-or-r8a ranking.

### Compute-Optimized 16-vCPU Runner

| Strategy | Average job | Average build step | Cache setup | Result |
| --- | ---: | ---: | ---: | --- |
| Input-only cache | 82.5s | 54.0s | About 10s | Small net benefit |
| No Rust cache | 87.5s | 69.0s | 0s | Simplest baseline |
| Warm S3 `sccache` with input cache | 69.0s | 40.5s | About 9–10s | Fastest tested |

Input-only caching saved about 15 seconds in the build step but spent about 10 seconds on cache setup, for only about five seconds of end-to-end benefit.

Warm `sccache` improved the build step by about 41% and the full job by about 21% relative to no Rust cache. The absolute end-to-end saving was about 18.5 seconds because the benchmark itself was short.

### `sccache` Statistics

| Metric | Observation |
| --- | ---: |
| Compile requests | 1,861 |
| Executed cacheable requests | 1,413 |
| Cache hits | 1,410 |
| Cache misses in corrected warm runs | 0 |
| Non-cacheable calls | 442 |
| Cache errors | 0 |

These results contradict the claim that `sccache` provided no meaningful benefit. They also show why a 100% hit rate among cacheable calls does not produce an instant build: Cargo orchestration, per-object lookup/materialization, build scripts, procedural macros, non-cacheable calls, and final linking remain.

### Network- And NVMe-Oriented 16-vCPU Runner

| Strategy | Average job | Average build step | Difference from compute-optimized job |
| --- | ---: | ---: | ---: |
| Input-only cache | 105.5s | 71.5s | 27.9% slower |
| No Rust cache | 106.5s | 90.0s | 21.7% slower |
| Warm S3 `sccache` with input cache | 81.0s | 49.0s | 17.4% slower |

Higher peak network capacity and local NVMe did not improve this workload. The result points to CPU/compiler throughput and per-object orchestration as more important than bulk network or disk bandwidth for this benchmark.
## Interpretation

- Input-only `rust-cache` is healthy and low risk but offered only a small net gain in the controlled benchmark.
- No Rust cache is a credible baseline whenever input-cache setup is close to the download time it avoids.
- S3-backed `sccache` in 0.17 default server mode is the strongest measured PR-CI candidate because its warm full-workload repeat roughly halved end-to-end time without reconstructing a complete historical target tree.
- A separate input-only `Swatinem/rust-cache` step did not improve compiler-cache reuse beside warm `sccache`; the one measured ablation without it was directionally faster, so omit it unless dependency-download timing justifies the extra archive.
- Cold `sccache` population is a real regression, but the read-only control shows that successful uploads do not explain most of the penalty. A deployment needs a trusted canonical population policy, lifecycle management, and an explicit clean-compilation rollback.
- `SCCACHE_CLIENT_SIDE=1` was not a performance improvement for the measured direct-S3 workload despite a high warm hit rate.
- Client-side `disk,s3` background writes did not improve the cold trial, were not fully durable by job teardown, and produced only a small warm improvement over no cache on an ephemeral runner.
- A high hit rate is not an adoption metric. Cargo orchestration, per-object lookup and materialization, build scripts, procedural macros, non-cacheable calls, and final linking remain on the critical path.
- A narrow whole-target archive can still be competitive for a stable artifact build when keys are exact, fallback is disabled, archive size stays small, and restore/save remains cheaper than recompilation. In the fresh full-workload trial, a 7.60 GB archive approached warm `sccache` workload time but lost 2m07s end-to-end to restore and extraction.

## Limitations

- The controlled benchmark used `cargo check --all-targets`, not the complete production workload.
- Two runs per strategy are directional evidence, not a stable median or p95.
- The representative full-workload controls had two runs each, while each full-workload `sccache` mode and cache state had one run.
- The fresh whole-target population and warm states also had one run each.
- The c8a, m8a, and r8a selection set shared the AMD EPYC 9R45 processor model; the observed c8a and m8a trials were separated in time and varied RAM and storage characteristics, so no cross-family performance ranking is supported.
- The full-workload command did not expose a reliable pure compilation, linking, and test-execution split; it remains recorded as workload wall time.
- The fresh whole-target trial recorded the post-workload target size and file count, but that is not necessarily the exact uncompressed archive payload after action cleanup.
- The recorded full-workload direct-S3 population and warm trials reported `sccache` 0.17.0 in default server mode.
- The follow-up client-side and multilevel trials crossed c8a/r8a memory and storage profiles. Their shared CPU model reduces one source of variation but does not turn them into controlled runner-profile comparisons.
- Runner price, Spot availability, S3 request cost, and cache storage cost were not included in the timing comparison.
- The measurements come from one anonymized monorepo and should guide experiments rather than serve as universal performance guarantees.

## Implications

- Use [Clean Target: No Cache Or Cargo Inputs Only](../approaches/clean-target.md) as the safe baseline.
- Use [S3-Backed `sccache`](../approaches/sccache.md) as the leading compiler-cache canary for changing PR workloads.
- Use [`Swatinem/rust-cache` with mtime-preserving checkout](../approaches/rust-cache-mtime-checkout.md) and the [source-keyed target workaround](../approaches/rust-cache-source-keyed-target-cache.md) only as conditional whole-target designs with explicit size and timing guardrails, given the growth behavior in [Target Archive Growth In Production](target-archive-growth.md).
- Evaluate [RunsOn sticky disks](../deployments/runs-on/README.md#sticky-disk-options) only after the required platform upgrade and with native-disk lifecycle controls.
- Follow [Measuring Cache Performance](../operations/measuring-cache-performance.md) when reproducing or extending these comparisons.
