# Mr. Boxington object-mode restore opportunities

**Status: measured bottleneck with a local store-library prototype; no released action or CLI implementation. Reviewed 2026-09-15.**

The measurements and proposed directions were published upstream in [Mr. Boxington discussion #460](https://github.com/jdx/mr-boxington/discussions/460).

The corrected [mbx 1.11.1 comparison](../evidence/mr-boxington-vs-sccache.md#source-follow-up-and-corrected-retest) found that object mode completed the native Cargo checks four seconds faster than sccache but finished seven seconds slower overall. Its selected closure contained 4,914 objects and 773 actions, occupied 3.0 GiB logically, and was transported as an approximately 625 MiB GitHub cache entry. GitHub cache extraction took about 3.02 seconds and `mbx cache import` took 6.33 seconds.

## Current data path

At mbx 1.11.1 and action 1.3.1, the object payload has two archive layers:

```text
actions/cache zstd-compressed tar
  -> uncompressed mbx export tar
     -> selected CAS objects and action results
```

The action caches the mbx export archive as one path and invokes `mbx cache import` after `restoreCache`. The importer creates a temporary directory, checks entry types and paths, unpacks the tar, validates the export manifest and complete closure, verifies content-addressed objects, adopts them into the active CAS, publishes action results, and merges task-prediction manifests.

The release already includes [PR #353](https://github.com/jdx/mr-boxington/pull/353), which avoids redundant copies and hashes after closure verification. `adopt_verified_file` renames verified files when source and destination share a filesystem. The measured runner satisfied that condition, so changing only the temporary-directory parent would not recover the observed time.

## Local directory-import prototype

A local branch based on upstream `main` revision `c389d92` added a directory-form import API to `mbx-cache-store`. The local commit was `547369b` (`perf(cache): accept directory-form exports`). It changed only `crates/mbx-cache-store/src/lib.rs` and `store_tests.rs`, with 110 insertions and 8 deletions. No CLI, action, export-format, cache-key, or workflow change was implemented.

The prototype added:

```rust
pub fn import_directory(store: &Path, directory: &Path) -> Result<TransferOutcome>

pub fn import_directory_with_attachments(
    store: &Path,
    directory: &Path,
) -> Result<ImportOutcome>
```

It refactored the existing post-extraction work into a shared internal helper. Archive import continued to unpack the tar and then used that helper; directory import scanned an already-restored tree and used the same manifest parsing, closure traversal, digest verification, object adoption, action publication, and task-manifest merging.

The directory pre-scan accepted regular files and directories only, rejected symbolic links and special entries, and passed every relative file through the existing archive-path policy. It therefore accepted only the export manifest, `cas/v1/...`, and `action-results/v1/...`.

A release-mode synthetic fixture matched the production count of 4,914 objects but contained approximately 614 MiB of data rather than the production closure's 3.0 GiB. Fixture tar extraction occurred before the directory-import timer so the comparison represented work after an archive transport had already restored the tree.

| Import path                        |  Time |
| ---------------------------------- | ----: |
| Existing tar import                | 6.99s |
| Already-extracted directory import | 3.11s |

Removing the second extraction saved approximately 3.88 seconds. The remaining approximately three seconds included directory scanning, complete closure traversal, digest verification, and publication. This is directional local evidence, not a prediction that GitHub-hosted storage will produce the same values.

The prototype added a normal directory-import test and a Unix symbolic-link rejection test. All 54 `mbx-cache-store` tests passed, as did:

```text
cargo clippy -p mbx-cache-store --all-features --all-targets -- -D warnings
```

The repository-wide gate completed formatting, Rust build/tests, generated documentation checks, documentation build, and the focused release diagnostic. It stopped at the Bats end-to-end task because `bats` was absent from the local environment.

## Candidate upstream designs

### Transport-native directory closure

Add a versioned directory-form selected closure while retaining tar as the standalone portable format. `actions/cache` would compress the selected tree once, restore it into an isolated staging directory, and ask mbx to validate and adopt it. This preserves bounded closure selection and avoids confusing direct whole-store caching with the proposed format.

The local measurement suggests this could recover about four seconds for a workload of this shape. Applied mechanically to the single 3m10s warm run, it would project near 3m06s, still about three seconds behind sccache.

### Read-only lower store with a writable job layer

Restore the selected closure as an immutable lower CAS and write new job results to an upper store. Task manifests can be treated as untrusted predictions, while `LocalCas::find` and `LocalActionCache::find` continue validating entries when consumed. This could move digest work from serial setup into actual cache reads and Cargo scheduling, avoid thousands of setup-time renames, and let malformed lower entries become misses or explicit diagnostics.

This design needs defined behavior for garbage collection, lower-layer corruption, export of used lower objects with new upper objects, task-manifest precedence, and remote-cache composition. It is a broader store abstraction rather than an action-only optimization.

### Bounded parallel verification

If complete eager verification remains required, verify independent objects with a bounded worker pool. Measure fast NVMe and smaller hosted runners separately because hashing can compete with decompression or compilation for memory bandwidth. Directory-form transport should be isolated first so extraction does not obscure the result.

### Streaming tar import

For the standalone tar path, stage entries under final CAS parent directories, validate them, and publish only after the complete referenced closure is known. This can avoid constructing and walking a second complete staging tree, but it cannot remove duplicate decompression when the tar is itself carried by `actions/cache`. Sparse files, manifest order, rollback, and visibility of incomplete action results require explicit handling.

### Action setup overlap

Object mode currently needs an mbx binary to discover its cache directory before restoring the object archive. A deterministic staging path or bootstrap payload could let binary setup and cache restore overlap. Instrument binary resolution, download, extraction, cache download, and cache extraction separately before assigning a saving; the measured action had mbx in the runner tool cache.

### Optional Cargo registry/git payload

An optional objects-with-registry mode may help workflows that otherwise download dependency sources after restoring objects. Upstream already has an `mbx-registry` benchmark arm. The corrected comparison ran the same explicit dependency-fetch phase in every cache arm, so registry omission does not explain its object-versus-sccache difference.

### Container-aware workspace-state restore

The diagnostic workspace-state experiment expanded the payload from 625 MiB compressed and 3.0 GiB logical to 877 MiB compressed and 4.3 GiB logical, increased import from 6.33 seconds to about 21.9 seconds, and then conflicted with container-side target management. Useful support would require explicit host/container workspace and target mappings, caller-selected restoration destinations, or a lightweight metadata-only state that references CAS objects without recreating a broad target tree.

## Qualification plan

Instrument binary setup, outer cache download/extraction, inner extraction, manifest parsing, closure traversal, bytes hashed, object publication, task-manifest merge, workspace-state restore, first-hit latency, Cargo duration, and complete job duration. Compare current archive import, directory import with eager verification, bounded parallel verification, and a lazy lower store. Run exact warm, small edit, changed checkout path, changed target path, native host, and bind-mounted container scenarios on small hosted and larger NVMe-backed runners.

Keep these proposals in research until a released implementation passes correctness, corruption, cancellation, outage, concurrent-reader/writer, cache-size, and representative paired performance tests. The current [decision D9](../decisions/README.md) remains sccache for portable clean-target reuse and treats mbx target mode as a separate mechanism.
