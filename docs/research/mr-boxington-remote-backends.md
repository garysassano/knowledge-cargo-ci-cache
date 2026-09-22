# Mr. Boxington remote backends on RunsOn

**Status: direct S3 measured once; managed cache-server integration proposed and untested. Reviewed 2026-09-16.**

This page separates MBX backend selection from the GitHub action payload modes. It records the current source contract, the RunsOn integration boundary, the direct-S3 experiment, and the remaining server proposal. It does not describe an existing RunsOn MBX feature.

## Configuration layers

`jdx/mr-boxington-action` supports `local`, `github`, and `server` backends. Its `github-cache-mode: objects|target` input applies only to `backend: github`:

- `objects` exports and imports a portable MBX action/object closure through an Actions-cache-compatible service.
- `target` restores and saves a pruned Cargo target tree and Cargo input state through that service.
- `server` configures MBX native HTTP cache protocol.
- `local` can remain local-only or use an independently supplied `MBX_REMOTE_URL`, including `s3://`.

RunsOn Magic Cache transparently backs the GitHub archive path, including both `objects` and `target`. RunsOn does not need distinct MBX settings for those modes. A RunsOn-specific feature would instead configure one of two native object backends: a managed cache server or direct S3.

| Interface     | What it configures                                   | Status                                                                    |
| ------------- | ---------------------------------------------------- | ------------------------------------------------------------------------- |
| `sccache: s3` | Direct-S3 sccache environment                        | Existing RunsOn action feature                                            |
| `mbx: s3`     | Direct per-object S3 access using runner credentials | Proposed convenience; measured slower than action objects in one workload |
| `mbx: server` | Existing `mr-boxington-cache` service                | Preferred proposal; not benchmarked here                                  |

## Existing cache server

The open-source `jdx/mr-boxington-cache` server is experimental. Its latest published release checked on 2026-09-16 was v0.1.1; the default branch declared version 0.2.0. It already provides:

- S3-backed blob storage using the standard AWS SDK credential chain, including EC2 roles.
- GitHub OIDC authorization and namespace grants.
- Zstd-compressed transfers and streaming blob packs.
- Batched lookups and action promises for in-flight deduplication.
- PostgreSQL metadata, horizontal replicas, and Prometheus metrics.
- Namespace isolation, bucket lifecycle compatibility, and metadata sweeping.

Its relevant server settings include:

```text
MBX_CACHE_STORAGE=s3
MBX_CACHE_S3_BUCKET=<bucket>
MBX_CACHE_S3_PREFIX=<prefix>
MBX_CACHE_S3_REGION=<region>
MBX_CACHE_DATABASE_URL=<postgresql-url>
MBX_CACHE_OIDC_PROVIDERS_JSON=<provider-and-grant-configuration>
```

A proposed RunsOn-managed integration would deploy this existing service in the customer AWS environment and export client settings such as:

```text
MBX_REMOTE_URL=https://<private-endpoint>
MBX_REMOTE_NAMESPACE=<repository-scoped-namespace>
MBX_REMOTE_MODE=<effective-mode>
MBX_REMOTE_OIDC_AUDIENCE=<audience>
```

The service, rather than the client-side mode variable, should enforce repository and ref grants. Deployment design must cover private networking, PostgreSQL ownership and backups, lifecycle and sweeping coordination, upgrades, availability, metrics, and fail-open local compilation.

No cache-server benchmark was performed. Testing `backend: server` requires a deployed endpoint, PostgreSQL metadata storage, blob storage, and configured authentication or OIDC grants. Direct-S3 results must not be presented as server-mode performance.

### Aurora DSQL compatibility candidate

Aurora DSQL is a plausible AWS-native metadata service because it speaks the PostgreSQL wire protocol, supports JSONB and core transactions, and authenticates through IAM. It is not currently a verified drop-in replacement for the server PostgreSQL backend.

The current `mbx-cache` implementation uses SQLx/Postgres plus migrations and queries that require an integration test against DSQL:

- Migration `0001_init.sql` contains two `CREATE TABLE` statements. DSQL permits one DDL statement per transaction and requires DDL and DML in separate transactions, so the migration runner or migration split may need adjustment.
- Queries use array `UNNEST ... WITH ORDINALITY`, JSONB operators and functions, interval casts, `UPDATE ... FROM`, `ON CONFLICT`, and explicit multi-statement transactions. Wire compatibility alone does not prove every expression and transaction path works.
- DSQL connections time out after one hour. The SQLx pool must discard and recreate expired connections.
- DSQL uses generated IAM authentication tokens. A long-running service needs token generation when opening new pooled connections rather than one startup-time password.
- DSQL transactions use fixed repeatable-read isolation, can return serialization conflicts instead of blocking, and can modify at most 3,000 rows. Metadata sweep operations may need bounded batches and retry logic.

Keep conventional PostgreSQL as the known contract. Qualify DSQL separately with migrations, CRUD, batched lookup, manifest compare-and-set, sweeping, connection recycling, IAM-token renewal, contention, and failover tests before presenting it as supported.

## Direct S3

The direct `s3://` backend is intentionally simpler:

- Objects are stored under `<URL-prefix>/<namespace>/v1/...`.
- Transfers use bounded concurrency but no protocol-level batch lookup, negotiated compression, blob-pack endpoint, or action promises.
- Credentials currently come from explicit `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and optional `AWS_SESSION_TOKEN` variables rather than direct use of the EC2 or ECS provider chain.
- Region resolution uses `MBX_REMOTE_S3_REGION`, then `AWS_REGION`, then `AWS_DEFAULT_REGION`.
- Readers need `s3:GetObject`; writers also need `s3:PutObject`; prefix-constrained `s3:ListBucket` is needed to distinguish missing objects from access denial.
- Normal operation does not require `s3:DeleteObject`; bucket lifecycle can expire data.
- Task action manifests use conditional writes. `MBX_REMOTE_S3_CONDITIONAL_WRITES=required` can require backend support.

On RunsOn, direct S3 currently requires exporting temporary instance-role credentials and passing them into any container that runs MBX. Masking them prevents routine log display but does not make them inaccessible to later job code. RunsOn documents repository and branch isolation for Magic Cache protocol credentials; direct S3 clients instead inherit the runner role broader stack cache authority. `MBX_REMOTE_MODE=read-only` is client behavior, not an IAM boundary.

An optional `mbx: s3` input in `runs-on/action` could automate URL, namespace, region, mode, and credential setup. It would be convenience for trusted stacks unless paired with repository-scoped IAM. It should not set `RUSTC_WRAPPER`, install MBX, or expose credentials as outputs; `jdx/mr-boxington-action` can continue to install and wrap Cargo.

## Measurement

The [same-batch remote comparison](../evidence/mr-boxington-vs-sccache.md#action-object-transport-versus-native-s3) found:

| Phase              | Action 1.4.0 objects through Magic Cache |             Native S3 |
| ------------------ | ---------------------------------------: | --------------------: |
| Cold job           |                                    3m53s |                 3m53s |
| Warm job           |                                **3m01s** |                 3m06s |
| Warm native checks |                                **1m21s** |                 1m29s |
| Warm Clippy        |                               **16.34s** |                21.99s |
| Warm transfer      |                626 MB compressed archive | 3.0 GiB during Clippy |

Direct S3 produced 771 total warm hits with zero misses, so the integration was functional. It did not improve end-to-end performance for this workload. This result does not predict cache-server performance because the server protocol has compression, packing, batching, and coordination that direct S3 lacks.

## Proposed upstream work

For Mr. Boxington direct S3:

- Clarify whether it is intended to remain the simple backend for users who do not operate the cache server.
- Consider compressed object representation or immutable client-created packs if they can preserve content identity and concurrency correctness.
- Consider byte-bounded or more selective prefetch; the measured warm Clippy invocation prefetched 413 objects and downloaded 3.0 GiB.
- Support the standard AWS credential provider chain.
- Report prefetched-but-unused bytes and objects, request counts, lookup latency, concurrency waits, and demanded versus speculative throughput.

For RunsOn:

- Prefer a managed deployment or integration of the existing cache server for compression, service-enforced namespace grants, and richer protocol behavior.
- Consider `mbx: s3` separately as lower-complexity setup convenience with explicit IAM and credential-exposure limitations.
- Keep GitHub `objects|target` payload selection in `jdx/mr-boxington-action`; RunsOn already provides the compatible archive backend through Magic Cache.

## Promotion criteria

- Repeat action objects versus direct S3 across changed-source and concurrent workloads.
- Measure S3 requests, remote bytes, prefetched-but-unused bytes, and complete job cost.
- Deploy the cache server in a disposable environment and compare it with both measured paths.
- If Aurora DSQL is considered, run the full metadata integration suite against it and test one-hour connection recycling, IAM-token renewal, serialization retries, and bounded sweeps.
- Test OIDC grants for default-branch writers, same-repository pull requests, forks, and denied namespaces.
- Test outage behavior, cancellation, concurrent publication, lifecycle expiry, and metadata sweeping.
- Preserve direct compilation and action object mode as rollback paths.

## Sources

- [Mr. Boxington remote cache](https://github.com/jdx/mr-boxington/blob/v1.12.0/docs/remote-cache.md)
- [Mr. Boxington cache server](https://github.com/jdx/mr-boxington/blob/v1.12.0/docs/cache-server.md)
- [`jdx/mr-boxington-cache`](https://github.com/jdx/mr-boxington-cache)
- [Mr. Boxington action v1.4.0](https://github.com/jdx/mr-boxington-action/blob/v1.4.0/README.md)
- [RunsOn caching](https://runs-on.com/docs/performance/caching/)
- [RunsOn action v2.3.1](https://github.com/runs-on/action/blob/v2.3.1/action.yml)
- [Aurora DSQL PostgreSQL compatibility](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/working-with-postgresql-compatibility.html)
- [Aurora DSQL authentication and authorization](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/authentication-authorization.html)
