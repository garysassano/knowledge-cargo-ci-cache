# Mr. Boxington remote backends on RunsOn

**Status: a per-object Magic Cache helper (`mbx: true`) is implemented in an open runs-on/action pull request and measured; direct S3 to the stack bucket is rejected for RunsOn; the cache server is not pursued on RunsOn. Reviewed 2026-10-15.**

This page separates MBX backend selection from the GitHub action payload modes. It records the source contract, the RunsOn integration boundary and its history, the direct-S3 experiment, and the helper now proposed upstream. No RunsOn MBX input was released on 2026-10-15.

## Configuration layers

`jdx/mr-boxington-action` supports `local`, `github`, and `server` backends. Its `github-cache-mode: objects|target` input applies only to `backend: github`:

- `objects` exports and imports a portable MBX action/object closure through an Actions-cache-compatible service.
- `target` restores and saves a pruned Cargo target tree and Cargo input state through that service.
- `server` configures MBX native HTTP cache protocol.
- `local` can remain local-only or use an independently supplied `MBX_REMOTE_URL`, including `s3://`.

Since action v1.6.0 the backend values are `local`, `github` and `remote` (`server` is an alias), and `remote` keeps an `MBX_REMOTE_*` configuration exported by an earlier step. RunsOn Magic Cache transparently backs the GitHub archive path, including both `objects` and `target`, so RunsOn needs no settings for those modes. A RunsOn feature configures a native object remote instead.

| Interface     | What it configures                                           | Status on 2026-10-15                                                                                                                                      |
| ------------- | ------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `mbx: true`   | A helper in the job that stores mbx's objects in Magic Cache | Open [runs-on/action#65](https://github.com/runs-on/action/pull/65); measured                                                                             |
| `mbx: s3`     | Direct per-object S3 access with the runner role             | Withdrawn: not isolated (every job on the stack can write `cache/*`), measured slower than action objects once, and RunsOn is retiring direct-S3 adapters |
| `mbx: server` | A managed `mr-boxington-cache` service                       | Not pursued: the RunsOn maintainer declined integrations that need deployed infrastructure; untested here                                                 |

## Magic Cache helper (`mbx: true`)

Status: implemented in the open [runs-on/action#65](https://github.com/runs-on/action/pull/65) (2026-10-15), measured, and validated on Linux, a `rust:1` container and Windows. It replaced the earlier `mbx: s3` version of that PR, which exported a direct-S3 remote.

The action starts its own binary with `--mbx-serve` as a detached helper. The helper serves the [mbx remote protocol baseline and conditional manifests](../reference/compiler-cache-implementation.md#mr-boxington-v1240-remote-protocol) on `127.0.0.1` and stores each object as a GitHub Actions cache entry through Magic Cache, with the client shared with gocacheprog. Later steps get `MBX_REMOTE_URL`, `MBX_REMOTE_TOKEN` and, unless set, `MBX_REMOTE_NAMESPACE`; `jdx/mr-boxington-action` with `backend: remote` installs mbx and keeps that remote.

| Design point | Choice                                                                                                                                                                                                                                                                                                    |
| ------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Isolation    | Magic Cache scopes each entry to the job's ref; with stack isolation, the broker enforces it. Nothing is deployed.                                                                                                                                                                                        |
| Credentials  | The runtime token reaches the helper on stdin, never its environment, and is not exported. mbx presents a per-job bearer token, which loopback HTTP allows.                                                                                                                                               |
| Layout       | Action results and blobs are created once, keyed by namespace, kind and digest, and spread over 16 cache versions by the digest's first hex digit, for the lookup index's 50,000-entry limit.                                                                                                             |
| Manifests    | Each revision is a new entry under the manifest's prefix. The newest is current, and its revision is the strong `ETag`; `If-Match` and `If-None-Match` are checked before each write, serialized within a job. Concurrent jobs can lose an update, which mbx documents as costing prefetch coverage only. |
| Errors       | A token that may not write gets 403, which mbx does not retry; other Magic Cache failures get 502, which mbx retries and then builds locally.                                                                                                                                                             |
| Shutdown     | The post step prints counters, then stops the helper through an endpoint that requires the bearer token. The helper drains in-flight requests first. Windows never kills by process ID.                                                                                                                   |

Measured results are in the [Magic Cache benchmark](../evidence/runs-on-magic-cache-sccache-vs-mbx.md): fastest of `sccache: true`, the helper and no cache in every scenario on ruff with 32 vCPUs, at about 7× sccache's storage.

Remaining limits:

- Pull requests only read, because mbx's client publishes only from protected-branch pushes. A pull request rebuilds its own changes on every push. The maintainer declined pull-request writes on remotes "for now" ([jdx/mr-boxington#536](https://github.com/jdx/mr-boxington/discussions/536)).
- Objects are stored uncompressed, and the helper offers no batches or blob packs.
- Objects are never rewritten while in use, so fixed Magic Cache retention expires long-lived objects together.

## Existing cache server

The open-source `jdx/mr-boxington-cache` server is experimental. Its latest published release checked on 2026-09-22 was v0.1.1; the default branch declared version 0.2.0. It already provides:

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
- In the 2026-09-22 review, credentials came only from explicit `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and optional `AWS_SESSION_TOKEN` variables. mbx 1.21.0 and later also sign with an EC2 instance role through IMDSv2 and renew it.
- Region resolution uses `MBX_REMOTE_S3_REGION`, then `AWS_REGION`, then `AWS_DEFAULT_REGION`.
- Readers need `s3:GetObject`; writers also need `s3:PutObject`; prefix-constrained `s3:ListBucket` is needed to distinguish missing objects from access denial.
- Normal operation does not require `s3:DeleteObject`; bucket lifecycle can expire data.
- Task action manifests use conditional writes. `MBX_REMOTE_S3_CONDITIONAL_WRITES=required` can require backend support.

In the measured configuration, direct S3 on RunsOn required exporting temporary instance-role credentials and passing them into any container that runs MBX; mbx 1.21.0 removed that need. The measured container also received `GITHUB_ACTIONS`, `GITHUB_EVENT_NAME`, `GITHUB_REF_TYPE`, and `GITHUB_REF_PROTECTED` because MBX uses those values to reduce untrusted contexts to read-only. Forward the real job values rather than hard-coding a trusted push in a reusable workflow. Missing CI context makes a configured read-write client effectively read-only, while forged trusted context can enable client writes; neither replaces repository-scoped IAM. Masking credentials prevents routine log display but does not make them inaccessible to later job code. RunsOn documents repository and branch isolation for Magic Cache protocol credentials; direct S3 clients instead inherit the runner role broader stack cache authority. `MBX_REMOTE_MODE=read-only` is client behavior, not an IAM boundary.

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

For the helper:

- Compress stored objects, or advertise zstd so mbx uploads compressed bodies, to reduce the 7× storage gap with sccache.
- Offer batched lookups or blob packs if prefetch turns out latency-bound on larger object counts.
- Have Magic Cache refresh entries on hits in writable scopes, or recommend a longer retention, so long-lived objects do not expire together.

For Mr. Boxington:

- Let a client keep its configured mode in pull requests when the server declares that it enforces per-ref scopes. This would allow pull-request reuse across pushes; the maintainer declined pull-request writes "for now".
- Report prefetched-but-unused bytes and objects, request counts, lookup latency, concurrency waits, and demanded versus speculative throughput.

The direct-S3 items from the 2026-09-22 review (compressed objects or client packs, bounded prefetch, the AWS credential chain) were addressed or became moot: mbx 1.21.0 signs with the instance role, and RunsOn no longer pursues direct S3.

## Promotion criteria

- Release of `mbx: true`, then a repeat of the benchmark on the target runner size, including smaller runners and a leaf-crate change.
- Measure S3 requests, stored bytes over a full retention window, and complete job cost.
- Test concurrent publishers updating one manifest, outage behavior, cancellation and lifecycle expiry.
- Preserve direct compilation and action object mode as rollback paths.
- For a cache server outside RunsOn: deploy it in a disposable environment, test OIDC grants for default-branch writers, same-repository pull requests, forks and denied namespaces, and, if Aurora DSQL is considered, run the metadata integration suite with connection recycling, IAM-token renewal, serialization retries and bounded sweeps.

## Sources

- [Mr. Boxington remote cache](https://github.com/jdx/mr-boxington/blob/v1.15.0/docs/remote-cache.md)
- [Mr. Boxington cache server](https://github.com/jdx/mr-boxington/blob/v1.15.0/docs/cache-server.md)
- [`jdx/mr-boxington-cache`](https://github.com/jdx/mr-boxington-cache)
- [Mr. Boxington action v1.4.0](https://github.com/jdx/mr-boxington-action/blob/v1.4.0/README.md)
- [RunsOn caching](https://runs-on.com/docs/performance/caching/)
- [RunsOn action v2.3.1](https://github.com/runs-on/action/blob/v2.3.1/action.yml)
- [runs-on/action#65: `mbx: true`](https://github.com/runs-on/action/pull/65)
- [Mr. Boxington remote cache, v1.24.0](https://github.com/jdx/mr-boxington/blob/v1.24.0/docs/remote-cache.md)
- [Aurora DSQL PostgreSQL compatibility](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/working-with-postgresql-compatibility.html)
- [Aurora DSQL authentication and authorization](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/authentication-authorization.html)
