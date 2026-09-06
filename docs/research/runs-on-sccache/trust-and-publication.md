# Proposed compiler-cache trust and publication

Status: Proposed and untested integration work. This page specifies requirements; it does not describe a released RunsOn feature. Use [the research index](README.md) for scope, sequencing, and the [version refresh](baseline.md#release-refresh-2026-09-06).

## Improvement 2: Direct-S3 Security, Namespace, And Readiness

### Target Trust Model

| Job class                       | Canonical read                                                                                 | Canonical write | Private overlay | Default behavior                                            |
| ------------------------------- | ---------------------------------------------------------------------------------------------- | --------------- | --------------- | ----------------------------------------------------------- |
| Protected population workflow   | Yes                                                                                            | Yes             | Optional        | Sole canonical writer                                       |
| Trusted ordinary branch job     | Yes                                                                                            | No              | Optional write  | Read-only canonical consumer                                |
| Same-repository pull request    | Disabled by default for private or sensitive repositories; explicit read-only opt-in otherwise | No              | Normally no     | Disabled unless cache-content exfiltration risk is accepted |
| Fork pull request               | Disabled by default; optional explicit read-only                                               | No              | No              | Direct `rustc` by default                                   |
| Unknown or conflicting identity | No                                                                                             | No              | No              | Direct `rustc`                                              |

The exact classification is a platform policy decision. The invariant is that writer authority cannot be derived solely from branch text, workflow expressions, action inputs, or environment variables controlled by the job.

Canonical compiler objects can contain paths, metadata, and repository-derived build outputs. Granting arbitrary pull-request code read access therefore creates a confidentiality and exfiltration channel even when mutation is denied. Any PR read opt-in must deny listing unless required, meter and rate-limit keyed reads, and remain isolated by repository and trust domain.

### Writer Session Admission

`runs-on/action` should obtain a fresh GitHub Actions OIDC ID token with a compiler-cache-broker-specific audience. The broker must validate the issuer, audience, signature, `iat`, `nbf`, `exp`, unique `jti`, immutable `repository_owner_id` and `repository_id`, approved `workflow_sha` or `job_workflow_sha`, `event_name`, `run_id`, `run_attempt`, and `check_run_id` when issued. A broker nonce prevents replay of a token captured before the admission request.

GitHub identity alone does not prove which RunsOn instance is executing the job. The broker must also verify independent RunsOn control-plane attestation that binds the nonce, job, expected runner instance, stack, and current lifecycle state. GitHub runtime/cache tokens, `GITHUB_TOKEN`, arbitrary bearer tokens, environment variables, action inputs, and job-supplied repository or event fields are not accepted as workload identity.

The broker rejects reused token identifiers, stale run attempts, completed or cancelled runs, unapproved reusable workflows, mutable workflow identity, and privileged triggers that consume untrusted content. A protected writer pins every external action and reusable workflow to an approved full commit SHA and treats every checkout, dependency, action, generated script, tool, and artifact executed while writer authority exists as part of the supply-chain trust boundary.

Possession of a writer-capable loopback session is equivalent to canonical write authority because root-capable workflow code can submit arbitrary keys and bytes directly. Canonical writer sessions are therefore issued only to isolated protected population jobs. If untrusted compilation must coexist with cache ingestion, the ingest path needs a remote policy and stronger provenance design; a same-host token or socket is insufficient.

### Namespace Layout

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

### IAM And Bucket Policy

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

### Immutable Object Writes

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

### Integrity

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

### Readiness Manifest

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

Publication requires a remote writer lease with expiration and a monotonically increasing fencing epoch. A publisher may advance the current pointer only while its lease remains valid and only with compare-and-swap against the expected predecessor and sequence. Generation metadata records the predecessor, epoch, trusted workflow/run identity, workload digest, and terminal counts. Expired or superseded publishers may finish uploads but cannot publish an index, readiness state, or generation pointer.

Pointer readers reject a lower sequence, unexpected predecessor, stale fencing epoch, invalid signature, or namespace mismatch. The platform preserves the currently selected and explicitly retained rollback generations and their referenced objects while a candidate populates. A job-controlled manifest or locally writable marker cannot grant authority or roll the pointer backward.

### Membership And Negative Index

A readiness manifest avoids guaranteed-empty work but does not answer whether an individual compiler key exists. A gateway can reduce repeated miss work with one of these designs:

| Design                       | Advantages                                         | Risks and controls                                                                                        |
| ---------------------------- | -------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| Sharded Bloom filter         | Compact, no false negatives if generated correctly | False positives still reach S3; rebuild and generation ordering required                                  |
| Sharded Xor filter           | Compact and fast lookup                            | Immutable generation rebuilds; more complex producer                                                      |
| Sorted manifest shards       | Exact membership and simple integrity              | Larger downloads and binary-search implementation                                                         |
| DynamoDB index               | Low-latency mutable membership candidate           | S3 and index writes are not one transaction; negative answers are advisory until the generation is sealed |
| Redis or Valkey index        | Fast mutable membership                            | Eviction and durability can create false negatives unless treated carefully                               |
| Bounded local negative cache | Simple and useful during one job                   | Supplemental only; short TTL and namespace generation key required                                        |

Do not list an entire compiler-object prefix at job start. Full listings are unbounded, require broad `ListBucket`, race concurrent writers and lifecycle expiration, and can move rather than remove startup latency.

A negative membership result may suppress origin lookup only for a sealed immutable object generation whose complete index was built after every object write finished. For open or mutable generations, all indexes are advisory: positive results may optimize lookup, but negative results must fall through to origin. Generation sealing itself requires the current remote fencing token and prevents further canonical writes.

A probabilistic membership index must be designed so stale state can produce false positives, which only cause an origin lookup, but not false negatives that incorrectly suppress a valid cache hit. Generation metadata, sealing, monotonic fencing, and predecessor-checked pointer updates are required.

### Lifecycle

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

## Security And Threat Model

### Protected Assets

- Trusted compiler outputs later linked or executed by CI.
- Repository and trust-domain isolation.
- AWS and GitHub credentials.
- KMS permissions.
- Cache availability and cost budget.
- Logs and metrics that can reveal repository identity or signed URLs.

### Principal Threats

| Threat                                                 | Consequence                                               | Required control                                                                                                                      |
| ------------------------------------------------------ | --------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| Untrusted job overwrites canonical object              | Cache poisoning and possible later code execution         | IAM-separated writer, conditional create, checksums, conflict alerts                                                                  |
| Job lists or reads another repository                  | Confidentiality loss and cross-tenant leakage             | Exact broker policy, Access Point or bucket isolation, denial tests                                                                   |
| Ordinary job deletes cache                             | Availability and cost attack                              | No routine `DeleteObject`; maintenance-only deletion                                                                                  |
| Compromised workflow steals broad instance credentials | Cross-prefix mutation                                     | Remove broad direct-client role from cache path; use scoped sessions                                                                  |
| Root workflow interferes with local gateway            | Denial, token theft within job authority                  | Remote enforcement, per-job least privilege, quotas, no security claim for loopback                                                   |
| Replayed or forged writer admission                    | Canonical poisoning under a stale or wrong job identity   | Broker-specific OIDC audience, nonce, `jti`, run-attempt checks, immutable IDs, approved workflow SHA, independent RunsOn attestation |
| Malformed cache object exhausts memory or disk         | Runner denial of service                                  | Size bounds, streaming/spill, checksums, quotas                                                                                       |
| Backend error becomes a miss                           | Hidden outage and large compile regression                | Typed errors and explicit degrade policy                                                                                              |
| Token expires mid-job                                  | Long lookup/write failures                                | Refresh, staged deadlines, circuit break, safe fallback                                                                               |
| Sticky state crosses trust domains                     | Persistent poisoning or leakage                           | Trust-bound lineage, marker validation, read-only untrusted policy                                                                    |
| Untrusted PR reads canonical objects                   | Repository-derived output or metadata exfiltration        | Default-off sensitive-repository policy, no listing, keyed-read limits, exact repository/trust isolation                              |
| Stale publisher advances a generation or lineage       | Rollback, incomplete readiness, or divergent sticky state | Remote lease, monotonic fencing, predecessor CAS, external publication metadata                                                       |
| Logs expose credentials or object identity             | Secret or metadata disclosure                             | Structured redaction and allow-listed fields                                                                                          |

### Cache Poisoning

Compiler-cache outputs are later consumed by trusted build steps. Treat shared compiler-cache write access as a software supply-chain capability.

Controls:

- Only a protected population identity writes canonical objects.
- Objects are immutable under normal job credentials.
- Conflicting duplicate writes are alerts.
- Readers verify checksums, schema, approved generation, and publisher provenance.
- Canonical namespace rotation is reviewable and auditable.
- Corrupt objects are quarantined or bypassed, never silently repaired by an untrusted job.
- Promotion includes malicious cross-prefix and conflicting-object tests.

Checksums and first-writer-wins do not prove semantic authenticity. The same unrestricted job must not be allowed to fabricate both an object and the only evidence that it is trustworthy. High-assurance populations should consider independent rebuilds or sampled direct recompilation before activating a generation.

### Credential Handling

- Prefer brokered short-lived credentials or a remote proxy over broad instance-profile access.
- Require IMDSv2 as defense in depth, but assume root-capable workflow code can obtain any instance-profile credentials; the profile therefore carries no authority that violates the job's cache trust class.
- Do not place cloud credentials in persistent cache directories.
- Do not log the gateway bearer token, STS session, S3 bucket, full prefix, KMS key, or presigned URL.
- At close, revoke the loopback or remote-proxy capability, stop refresh, and remove local credential references. Direct AWS STS credentials normally remain valid until expiration unless an explicitly documented broader role-session revocation mechanism is invoked; in-memory zeroization is best effort.
- Account for clock skew and the minimum STS session duration.

### Binary Supply Chain

- Pin exact `sccache` and gateway versions.
- Verify published checksums or signatures.
- Record the verified digest in telemetry.
- Do not auto-download an unreviewed pull-request artifact in a trusted writer.
- Keep patched experimental binaries isolated by namespace and access policy.
