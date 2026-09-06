# Direct S3 performance experiments

Status: Proposed and untested integration work. This page specifies requirements; it does not describe a released RunsOn feature. Use [the research index](README.md) for scope, sequencing, and the [version refresh](baseline.md#release-refresh-2026-09-06).

## Improvement 3: Direct-S3 Performance Work Before A Gateway

Direct S3 remains the reference path and should receive targeted improvements that are useful even if a gateway is later adopted.

### Stage-Level Instrumentation

Measure, at minimum:

- Hash generation wall and CPU time.
- Daemon client round-trip time.
- Backend request type and result.
- DNS/connect/TLS time when observable.
- S3/KMS service latency and retry count.
- Object bytes and full-buffer allocation.
- Decompression and decode time.
- Output materialization bytes and time.
- Miss compilation wall and CPU time.
- Compression time by object.
- PUT or multipart time.
- Queue or concurrency delay.

Without this split, a faster or slower result cannot identify whether the limiting stage is hashing, local daemon serialization, S3, KMS, memory, compression, compiler scheduling, or output materialization.

### Connection And Request Behavior

Candidate changes to benchmark behind feature flags:

- Measure and tune the existing shared HTTP client and its connection pool; `sccache` 0.17.0 already installs an OpenDAL `HttpClientLayer` on its S3 operator. Adding pooling from scratch is not an identified missing feature.
- Resolve and cache endpoint information for a bounded interval.
- Separate connect, first-byte, and total request deadlines.
- Use bounded retries with exponential backoff and jitter for retryable failures.
- Respect service throttling and expose retry delay.
- Add circuit breaking so a failing backend does not impose the 60-second lookup ceiling on every compiler request.
- Coalesce identical concurrent reads.
- Avoid HEAD-before-GET patterns unless measurements show a need.
- Use conditional create for duplicate concurrent writes.
- Bound concurrent origin requests independently from rustc process concurrency.

Retries must not turn authorization, invalid request, or corruption errors into long delays. Typed errors are a prerequisite.

### Compression

`sccache` v0.17.0 defaults to zstd level 3. Benchmark levels 1, 3, 6, and 9 with source, runner, cache state, and backend fixed.

Record:

- Compression CPU time.
- Decompression CPU time.
- Stored bytes.
- PUT and GET wall time.
- Peak memory.
- Complete workload and job wall time.
- Request and storage cost.

Lower compression may reduce population CPU while increasing transfer and storage. Higher compression may reduce remote bytes while increasing miss-path CPU. The best setting can differ between cold writers and read-heavy jobs, so format compatibility and namespace versioning must be explicit.

### Memory And Streaming

The released remote path reads complete objects into memory. Large artifacts multiplied by concurrent rustc requests can create avoidable RSS peaks and allocator pressure.

Proposed upstream or gateway behavior:

- Stream remote bytes into a bounded decoder where the entry format permits it.
- Spill large objects to local temporary files when streaming decode is unavailable.
- Enforce maximum compressed and decoded object sizes.
- Account memory per job and per request.
- Reject or quarantine malformed length metadata before allocation.
- Record peak in-flight bytes and spill volume.

### Population Policy

Use one trusted canonical population job rather than allowing every reader to write.

Benefits:

- Avoids duplicate cold writes.
- Makes drain and completeness measurable.
- Reduces poisoning surface.
- Provides one place to publish readiness metadata.
- Makes storage growth and writer cost attributable.

The population workflow should use a representative source state and workload, but it should not pretend to populate every possible feature, profile, target, or source key. Additional populations should be deliberate dimensions with separate metrics or namespaces.

Ordinary read-only jobs may use a private short-lived overlay when the value of within-job reuse justifies it, but an ephemeral overlay is not a substitute for canonical persistence.
