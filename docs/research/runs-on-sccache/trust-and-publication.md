# Proposed compiler-cache trust and publication

Status: Proposed and untested integration work. This page specifies requirements; it does not describe a released RunsOn feature. Use [the research index](README.md) for scope, sequencing, and the [version refresh](../../reference/compiler-cache-implementation.md#release-refresh-2026-09-06).

Shared-cache write authority is a software supply-chain capability. In addition to the admission, immutable-write, and integrity rules above, apply [bounded decoding and resource admission](gateway.md#write-queue-and-backpressure), [typed failure and safe fallback](action-lifecycle.md#fallback-semantics), and [trust-bound sticky ownership](sticky-local-tier.md#concurrency-and-lineage). Qualification includes adversarial denial, corruption, and redaction tests in [Validation](validation.md#contract-tests).

## Target Trust Model

| Job class                       | Canonical read                                                                                 | Canonical write | Private overlay | Default behavior                                            |
| ------------------------------- | ---------------------------------------------------------------------------------------------- | --------------- | --------------- | ----------------------------------------------------------- |
| Protected population workflow   | Yes                                                                                            | Yes             | Optional        | Sole canonical writer                                       |
| Trusted ordinary branch job     | Yes                                                                                            | No              | Optional write  | Read-only canonical consumer                                |
| Same-repository pull request    | Disabled by default for private or sensitive repositories; explicit read-only opt-in otherwise | No              | Normally no     | Disabled unless cache-content exfiltration risk is accepted |
| Fork pull request               | Disabled by default; optional explicit read-only                                               | No              | No              | Direct `rustc` by default                                   |
| Unknown or conflicting identity | No                                                                                             | No              | No              | Direct `rustc`                                              |

The exact classification is a platform policy decision. The invariant is that writer authority cannot be derived solely from branch text, workflow expressions, action inputs, or environment variables controlled by the job.

Canonical compiler objects can contain paths, metadata, and repository-derived build outputs. Granting arbitrary pull-request code read access therefore creates a confidentiality and exfiltration channel even when mutation is denied. Any PR read opt-in must deny listing unless required, meter and rate-limit keyed reads, and remain isolated by repository and trust domain.

## Writer Session Admission

`runs-on/action` should obtain a fresh GitHub Actions OIDC ID token with a compiler-cache-broker-specific audience. The broker must validate the issuer, audience, signature, `iat`, `nbf`, `exp`, unique `jti`, immutable `repository_owner_id` and `repository_id`, approved `workflow_sha` or `job_workflow_sha`, `event_name`, `run_id`, `run_attempt`, and `check_run_id` when issued. A broker nonce prevents replay of a token captured before the admission request.

GitHub identity alone does not prove which RunsOn instance is executing the job. The broker must also verify independent RunsOn control-plane attestation that binds the nonce, job, expected runner instance, stack, and current lifecycle state. GitHub runtime/cache tokens, `GITHUB_TOKEN`, arbitrary bearer tokens, environment variables, action inputs, and job-supplied repository or event fields are not accepted as workload identity.

The broker rejects reused token identifiers, stale run attempts, completed or cancelled runs, unapproved reusable workflows, mutable workflow identity, and privileged triggers that consume untrusted content. A protected writer pins every external action and reusable workflow to an approved full commit SHA and treats every checkout, dependency, action, generated script, tool, and artifact executed while writer authority exists as part of the supply-chain trust boundary.

Possession of a writer-capable loopback session is equivalent to canonical write authority because root-capable workflow code can submit arbitrary keys and bytes directly. Canonical writer sessions are therefore issued only to isolated protected population jobs. If untrusted compilation must coexist with cache ingestion, the ingest path needs a remote policy and stronger provenance design; a same-host token or socket is insufficient.

## Namespace Layout

The long-term brokered or gateway namespace should be structurally separate from the released shared direct-client namespace:

```text
scoped-cache/<owner-id>/<repo-id>/<scope-digest>/sccache/v2/<os>-<arch>/<toolchain-policy>/canonical/
```

Optional non-canonical overlays may use:

```text
.../branch/<hashed-ref>/
.../job/<run-id>/<job-id>/
```

Rules:

- Use numeric GitHub owner and repository IDs rather than mutable names.
- Use an explicit `sccache/v2` schema segment.
- Hash refs before including them in object paths.
- Use at least a proposed 128-bit scope digest and treat the full identity tuple, not the digest alone, as the authorization input.
- Include OS, architecture, target family when different from the host, and a documented toolchain policy.
- Do not include the source commit in the canonical namespace; source inputs already participate in compiler invocation keys, and commit partitioning would destroy cross-commit reuse.
- Rotate the schema when key interpretation, compression, integrity, trust, or storage semantics change.
- Keep canonical and overlay objects distinguishable for lifecycle, cost, and trust policy.

An interim direct-S3 design that cannot yet use brokered `scoped-cache/*` should stay under a new versioned `cache/sccache/v2/...` prefix and use separate runner roles or stacks. It must not imply that the prefix itself provides isolation.

## IAM And Bucket Policy

The target infrastructure should provide distinct capabilities:

| Capability       | Allowed actions                                                                                  |
| ---------------- | ------------------------------------------------------------------------------------------------ |
| Canonical reader | Exact-prefix `GetObject`; only bounded listing when a selected index design requires it          |
| Canonical writer | Reader actions plus `PutObject`, multipart completion operations, and conditional-create support |
| Overlay writer   | Read/write only to its own short-lived overlay                                                   |
| Maintenance      | Lifecycle-independent delete, inventory, and namespace rotation operations                       |
| No-cache runner  | No compiler-cache object authority                                                               |

Normal jobs should not receive `DeleteObject`. Lifecycle expiration and a separate maintenance role own deletion. Writer and reader policies should also constrain:

- Exact bucket, access point, or prefix.
- Expected principal and session tags.
- TLS.
- Approved VPC endpoint where applicable.
- Required encryption behavior and KMS key.
- Maximum session duration appropriate to the job.
- Allowed object tags or metadata if used for lifecycle and integrity.

The existing gateway endpoint should receive an explicit endpoint policy if it is part of the trust design. A bucket or S3 Access Point policy should remain authoritative because endpoint policy alone does not protect every possible path.

The ambient runner instance profile must have no compiler-cache data or escalation path. Explicit policy tests should prove denial of unauthorized `ListBucket`, `GetObject`, `PutObject`, `DeleteObject`, object tagging, ACL, multipart initiation, upload-part, completion, abort, list-parts, KMS decrypt/data-key operations, and `AssumeRole` paths that could recover equivalent authority. Requiring IMDSv2 is defense in depth only; root-capable workflow code must be assumed able to reach any authority left on the instance profile.

For brokered access, use short-lived STS sessions with an inline session policy derived from verified job identity. The role trust policy must constrain the broker principal, job-controlled values must not freely set trusted session tags or `SourceIdentity`, the KMS key policy must enforce the same tenant and role boundaries as S3, and generated policies must fail closed if they exceed plaintext or packed-policy limits. Exact object access is constrained with object ARNs; `s3:prefix` constrains listing rather than `GetObject`. Conditional creation is enforced with request headers and bucket or Access Point policy, not a fictional IAM action.

See the official AWS [`AssumeRole` API](https://docs.aws.amazon.com/STS/latest/APIReference/API_AssumeRole.html), [Amazon S3 policy keys](https://docs.aws.amazon.com/AmazonS3/latest/userguide/amazon-s3-policy-keys.html), and [conditional-write policy enforcement](https://docs.aws.amazon.com/AmazonS3/latest/userguide/conditional-writes-enforce.html). RunsOn's existing Magic Cache broker is a useful implementation precedent, but direct `sccache` should not reuse its current scope truncation or listing behavior without a compiler-cache-specific review.

## Immutable Object Writes

Compiler-cache keys are content-derived identifiers. A writer should normally create an absent object, not overwrite an existing key.

The preferred contract is first-writer-wins:

1. Upload with an S3 conditional create equivalent to `If-None-Match: *`.
2. Treat `412 Precondition Failed` as an existing object and fetch authoritative stored metadata and, where policy requires, the bytes before deciding that identical content already exists.
3. Reconcile `409 Conflict` according to the operation type, restarting an upload when required rather than treating it as proof of an existing identical object.
4. Treat a pre-existing object with conflicting digest, length, schema, provenance, or metadata as a poisoning or corruption alert.
5. Abort orphaned multipart uploads through explicit failure handling and lifecycle cleanup.
6. Never trust the losing writer's supplied metadata as evidence about the stored object.
7. Never resolve a conflict by ordinary overwrite from a job.
8. Quarantine or rotate the namespace through maintenance policy when corruption is confirmed.

AWS documents conditional writes in [How to prevent object overwrites with conditional writes](https://docs.aws.amazon.com/AmazonS3/latest/userguide/conditional-writes.html). Released `sccache` and its OpenDAL path need verification or upstream work before this can be assumed.

## Integrity

Each object should have:

- The compiler-cache key.
- Uncompressed and compressed length.
- Cache schema and compression algorithm.
- A strong checksum over the exact stored bytes.
- When feasible, a second logical checksum over the decoded entry.
- Writer implementation version.
- Fenced publisher identity and provenance binding the key, object digest, compiler binary digest, toolchain identity, workload/source digest, workflow SHA, run attempt, and namespace generation.
- Creation timestamp for operations, not for cache-key identity.

The reader verifies stored-byte integrity before decoding and logical integrity before materializing outputs. Integrity failure is not a miss; it is a typed corruption event that triggers quarantine, alerting, and direct compilation.

Checksums detect transport or storage corruption only. An authorized malicious writer can choose an arbitrary key, matching bytes, and matching checksums. Semantic trust therefore comes from the protected population boundary, approved fenced publisher, and independently verifiable provenance or sampled reproducibility checks where assurance warrants them. Readers need an emergency remotely controlled denylist or generation rotation path that takes effect without first deleting the object.

## Readiness Manifest

Known-empty namespaces should bypass `sccache` rather than paying thousands of guaranteed misses.

A population workflow should publish a small readiness manifest only after its required write accounting is complete:

```json
{
  "schema": "runs-on-sccache-readiness/v1",
  "namespace_schema": "sccache/v2",
  "generation": "opaque-generation-id",
  "predecessor": "opaque-prior-generation-id",
  "sequence": 42,
  "fencing_epoch": 17,
  "state": "ready",
  "writer_version": "opaque-version",
  "writer_workflow_sha": "opaque-sha",
  "run_id": "opaque-run-id",
  "run_attempt": 1,
  "workload_digest": "opaque-digest",
  "source_digest": "opaque-digest",
  "toolchain_digest": "opaque-digest",
  "cacheable_requests": 431,
  "attempted_writes": 427,
  "committed_writes": 427,
  "rejected_writes": 0,
  "failed_writes": 0,
  "deferred_writes": 0,
  "unfinished_writes": 0,
  "created_at": "RFC3339 timestamp",
  "provenance_signature": "opaque-signature"
}
```

The illustrative counters are not a complete inventory of all possible future compiler keys. `ready` means the current fenced trusted publisher completed the declared workload and source state with the declared compiler, toolchain, and schema identity; observed nonzero cacheable work; committed at least one canonical object remotely; and reached zero rejected, failed, deferred, and unfinished canonical writes. It does not promise a hit for a particular future source state.

Required states are:

| State           | Meaning                                                                               | Reader action                                                                                      |
| --------------- | ------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| Absent          | No trusted completed population is known                                              | Bypass shared `sccache`                                                                            |
| Populating      | A candidate generation is active or its population did not finish                     | Continue using the previous ready generation when valid; otherwise bypass or use a private overlay |
| Completed-empty | The declared workload completed but produced no cacheable or committed canonical work | Bypass shared `sccache`; do not publish `ready`                                                    |
| Ready           | A trusted population completed and manifest integrity is valid                        | Enable canonical read path                                                                         |
| Degraded        | Backend or integrity monitoring detected a problem                                    | Fall back to direct `rustc`                                                                        |
| Rotated         | This generation is no longer selected                                                 | Follow the current generation pointer                                                              |

Publication uses this order:

1. Commit the declared compiler objects and account for all accepted writes.
2. Seal the candidate generation under the current remote writer lease, excluding later canonical writes.
3. Build, checksum, and commit any complete immutable index shards.
4. Commit signed metadata containing the sequence, predecessor, fencing epoch, publisher/run identity, workload digest, and terminal counts.
5. Activate the generation pointer through predecessor-checked compare-and-swap while the writer fence is current and the readiness conditions above hold.

The remote writer lease has an expiration and a monotonically increasing fencing epoch. Expired or superseded publishers may finish uploads but cannot activate an index, readiness state, or generation pointer.

Pointer readers reject a lower sequence, unexpected predecessor, stale fencing epoch, invalid signature, or namespace mismatch. The platform preserves the currently selected and explicitly retained rollback generations and their referenced objects while a candidate populates. Failed, cancelled, timed-out, lease-expired, fenced, or missing-post jobs cannot activate readiness, index, or sticky-lineage pointers; leases expire independently of post hooks, and the broker denies refresh after completion or cancellation. A job-controlled manifest or locally writable marker cannot grant authority or roll the pointer backward.

## Membership And Negative Index

Readiness describes a completed workload; membership describes individual keys. Negative membership may suppress origin lookup only for a sealed immutable generation whose complete index was built after every object write finished. Open or mutable indexes are advisory: a negative must fall through to origin. Stale metadata must not hide a valid object; false positives may cost an extra lookup.

Do not list an unbounded compiler-object prefix at job start. Use a bounded representation selected in the [gateway index design](gateway.md#membership-index).

## Lifecycle

The released bucket expires compiler objects by object age, not by last access. A warm object that is frequently read does not have its lifecycle age refreshed.

The target design should:

- Keep compiler objects and small control/index objects in separately managed prefixes when their retention needs differ.
- Set explicit lifecycle by namespace schema and trust class.
- Abort incomplete multipart uploads quickly.
- Expire private branch/job overlays more aggressively than canonical objects.
- Preserve readiness and generation metadata long enough to avoid selecting an expired object generation.
- Use inventory or an equivalent control plane to measure object count, bytes, age distribution, and incomplete multipart state.
- Rotate namespaces rather than relying on immediate mass deletion for rollback.
- Re-evaluate the ten-day default against observed reuse distance, storage cost, and warm probability.

Retention changes are experiments: longer retention can increase warm probability and storage cost, while shorter retention can turn otherwise reusable objects into cold misses.

## Credential Handling

- Prefer brokered short-lived credentials or a remote proxy over broad instance-profile access.
- Require IMDSv2 as defense in depth, but assume root-capable workflow code can obtain any instance-profile credentials; the profile therefore carries no authority that violates the job's cache trust class.
- Do not place cloud credentials in persistent cache directories.
- Do not log the gateway bearer token, STS session, S3 bucket, full prefix, KMS key, or presigned URL.
- At close, revoke the loopback or remote-proxy capability, stop refresh, and remove local credential references. Direct AWS STS credentials normally remain valid until expiration unless an explicitly documented broader role-session revocation mechanism is invoked; in-memory zeroization is best effort.
- Account for clock skew and the minimum STS session duration.

## Binary Supply Chain

- Pin exact `sccache` and gateway versions.
- Verify published checksums or signatures.
- Record the verified digest in telemetry.
- Do not auto-download an unreviewed pull-request artifact in a trusted writer.
- Keep patched experimental binaries isolated by namespace and access policy.
