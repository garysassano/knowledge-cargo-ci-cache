# Alternative sccache backend experiments

Status: Proposed and untested integration work. This page specifies requirements; it does not describe a released RunsOn feature. Use [the research index](README.md) for scope, sequencing, and the [version refresh](../../reference/compiler-cache-implementation.md#release-refresh-2026-09-06).

## Native GitHub Actions Cache Through Magic Cache

### Why It Is Interesting

A native GHA backend could use RunsOn's existing Magic Cache proxy and brokered repository/scope credentials instead of broad direct S3 instance-role access. It could also reuse platform handling for GitHub runtime tokens.

This is an architectural possibility, not verified compatibility.

RunsOn Magic Cache repository and branch protocol isolation is optional and disabled by default. Enabling it moves new objects into scoped namespaces, causes a cold cutover from prior unscoped state, and can change intentional cross-repository sharing. Isolation enablement is therefore an explicit canary precondition and experiment dimension, followed by a fresh controlled population rather than comparison against previously warm unscoped objects.

### Blocking Defect

The OpenDAL 0.55.0 writer embedded in sccache 0.17.0 discards upload finalization errors. OpenDAL 0.59.0 fixes this; qualify an updated or patched sccache build before evaluating performance. See the [release refresh](../../reference/compiler-cache-implementation.md#release-refresh-2026-09-06). A successful upload-body transfer is not a successful cache write until finalization succeeds and a fresh client can read the key.

### Required Conformance Matrix

Test the patched `sccache` and OpenDAL build against RunsOn Magic Cache for:

- GHA v2 Twirp request and response compatibility.
- Signed upload URL handling.
- Finalization success and injected finalization failure.
- Cold write followed by read from a fresh job.
- Duplicate immutable key behavior.
- `SCCACHE_GHA_VERSION` rotation.
- Repository, branch, default-branch, and fork scopes.
- Read-only and writer sessions.
- Runtime-token expiry and STS-session overlap.
- Proxy variables exported before the first daemon start.
- Concurrent thousands-of-object GET and PUT load.
- Rate limits, quota, abandoned uploads, and cancellation.
- Cross-repository and cross-scope denial.
- Cache visibility after premature runner teardown.
- Isolation disabled and enabled as separate namespace states, including the expected cold cutover.

The canary must use an isolated namespace and a patched binary. Do not switch the current canary merely by setting `SCCACHE_GHA_ENABLED=true`.

### Promotion Condition

Native GHA remains experimental until:

- Finalization errors propagate.
- Every acknowledged write is readable from a new job.
- Scope and trust behavior pass the matrix.
- Mixed-state job performance beats hardened direct S3 with confidence.
- Request and storage cost are attributable.
- Failure behavior remains within the direct-compiler gates.

## S3 Express One Zone

### Status

Untested integration, blocked for the archived sccache 0.17.0 binary. OpenDAL [v0.59.0](https://github.com/apache/opendal/releases/tag/v0.59.0) includes S3 Express session-authentication support and tracker [#8053](https://github.com/apache/opendal/issues/8053) is closed. A RunsOn experiment still requires that dependency in an explicitly tested sccache build, with its selected bucket and operation capabilities verified.

Verify first-writer-wins behavior through the exact sccache/OpenDAL write path, including conditional requests and duplicate writers. The current AWS PutObject reference no longer supports a blanket claim that directory buckets lack `If-None-Match`. If the selected implementation cannot perform conditional creation, evaluate an external key coordinator or keep canonical writing disabled; backend authentication alone is insufficient.

### Why It May Help

S3 Express One Zone is designed for low-latency access within one Availability Zone. The compiler-cache workload performs many small object operations, so reduced origin latency could improve hit materialization and confirmed misses without introducing a separate Redis-class service.

### Additional Requirements

This is not a bucket-class toggle. The design must include:

- A directory bucket with valid zonal naming and placement.
- Runner placement in the same Availability Zone.
- S3 Express Zonal endpoints for object data operations and Regional endpoints for control operations such as lifecycle configuration.
- The distinct VPC gateway endpoint service `com.amazonaws.<region>.s3express`, or another supported network path for the selected design.
- Data-plane session authorization through `s3express:CreateSession` where required and independent Regional control-plane authorization such as `s3express:PutLifecycleConfiguration`.
- Session refresh and expiry handling.
- OpenDAL endpoint, signing, and directory-bucket semantics.
- Lifecycle expiration and incomplete multipart cleanup appropriate to directory buckets; transitions, versioned-object expiration, and tag filters are unavailable.
- A bucket policy permitting the S3 lifecycle service principal to use `s3express:CreateSession` with `ReadWrite` when lifecycle expiration is configured.
- Verified conditional creation through the selected client, or an explicitly tested external first-writer-wins coordinator when the client cannot provide it.
- A Standard S3 fallback and namespace migration plan.
- Availability, failure-domain, and cost acceptance for single-AZ storage.

Official AWS references include [Networking for directory buckets](https://docs.aws.amazon.com/AmazonS3/latest/userguide/directory-bucket-az-networking.html), [Authorizing Regional endpoint APIs with IAM](https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-express-security-iam.html), [`PutObject` directory-bucket behavior](https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutObject.html), and [Directory bucket lifecycle management](https://docs.aws.amazon.com/AmazonS3/latest/userguide/directory-buckets-objects-lifecycle.html).

### Experiment

After backend support exists, run a read-only S3 Express experiment first. A writer experiment additionally requires verified conditional creation and publication fencing, with external key reservation only if the selected client requires it. Compare Standard S3 and S3 Express with:

- Same source, binary, compression, namespace contents, runner type, and Availability Zone.
- Cold empty read-only, cold population, warm exact, realistic changed-source, and concurrent identical-key states.
- Request p50, p90, and p95.
- KMS or session overhead.
- GET, PUT, session, storage, and endpoint cost.
- AZ-capacity and fallback behavior.
- Conditional-write latency, duplicate contenders, stale-writer rejection, and coordinator failure if an external coordinator is used.

Do not promote it from microbenchmark latency alone, and do not promote a canonical writer while conditional creation or publication fencing remains unresolved.

## Redis, Valkey, And Memcached

### Backend Roles

| Backend   | Plausible role                         | Durability expectation                                      | Main concerns                                                              |
| --------- | -------------------------------------- | ----------------------------------------------------------- | -------------------------------------------------------------------------- |
| Redis     | Shared low-latency L1 or primary cache | Configurable persistence and HA, but cache policy may evict | Memory cost, eviction, cluster behavior, TLS, auth, operations             |
| Valkey    | Redis-protocol shared L1 candidate     | Depends on selected managed or self-hosted topology         | Compatibility with the exact OpenDAL client, operations, persistence, cost |
| Memcached | Disposable shared hot tier             | None beyond node survival                                   | Eviction, item-size limits, no authoritative durability, isolation         |

`sccache` v0.17.0 documents Redis single-node and cluster endpoints, expiration, key prefixes, authentication, TLS, and read-only mode. It documents Memcached endpoints, expiration, key prefixes, authentication, and read-only mode. Valkey should be treated as a Redis-protocol compatibility test rather than assumed first-class support.

### Design Rules

- Keep S3 or another durable object store as origin unless the selected Redis or Valkey deployment explicitly owns durability.
- Partition keys by repository, trust domain, schema, platform, and toolchain policy.
- Enforce writer authority outside workflow-controlled variables.
- Use TLS and authenticated connections.
- Make eviction a typed miss, not corruption.
- Measure hot-set size and object-size distribution before sizing memory.
- Test node replacement, failover, resharding, max-memory eviction, and credential rotation.
- Bound client connections and concurrent requests.
- Include managed-service, cross-AZ, data-transfer, backup, and operational cost.

### Redis Or Valkey Experiment

Compare:

1. Direct S3.
2. Redis or Valkey as the only remote cache.
3. Redis or Valkey L1 with S3 origin through the gateway.
4. Sticky local L0 with Redis or Valkey L1 and S3 origin only if the two-tier result justifies added complexity.

Required states include warm hot-set, hot-set larger than memory, deliberate eviction, failover, cold service restart, and origin outage.

### Memcached Experiment

Use Memcached only as a disposable L1 in front of a durable origin. Validate object-size distribution against the service's configured item limit. A Memcached miss or eviction must fall through to origin; a Memcached acknowledgement must never be described as canonical durability.
