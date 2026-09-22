# Mr. Boxington object-mode restore history and opportunities

**Status: directory transport and parallel verification released and measured; additional designs remain research. Reviewed 2026-09-16.**

The measurements and proposed directions were published upstream in [Mr. Boxington discussion #460](https://github.com/jdx/mr-boxington/discussions/460).

The corrected [mbx 1.11.1 comparison](../evidence/mr-boxington-vs-sccache.md#source-follow-up-and-corrected-retest) identified nested archive restore and import as the main object-mode disadvantage. The subsequent [controlled mbx 1.12.0 comparison](../evidence/mr-boxington-vs-sccache.md#controlled-action-131-versus-140-comparison) held the engine and workflow constant while action 1.4.0 replaced the inner tar with a directory bundle. Import fell from 5.97 seconds to 0.26 seconds and the warm job fell from 3m16s to 3m01s.

## Historical mbx 1.11.1 data path

At mbx 1.11.1 and action 1.3.1, the object payload had two archive layers:

```text
actions/cache zstd-compressed tar
  -> uncompressed mbx export tar
     -> selected CAS objects and action results
```

The corrected trial selected 4,914 objects and 773 actions, occupied 3.0 GiB logically, and transported approximately 625 MiB through the GitHub cache. GitHub cache extraction took about 3.02 seconds and `mbx cache import` took 6.33 seconds. Object mode completed native Cargo work four seconds faster than sccache but finished seven seconds slower overall.

The importer already contained [PR #353](https://github.com/jdx/mr-boxington/pull/353), which avoids redundant copies and hashes after closure verification and renames verified files when possible. Staging and the destination store shared a filesystem in the measured job, so cross-filesystem copying did not explain the remaining cost.

## Local directory-import prototype

A local branch based on upstream revision `c389d92` added directory-form import to `mbx-cache-store` without changing the CLI, action, export format, cache key, or workflow. It refactored post-extraction validation and publication into a shared helper, rejected symbolic links and special entries, and reused the existing manifest, closure, digest, and path checks.

A release-mode synthetic fixture matched the production count of 4,914 objects but contained approximately 614 MiB rather than the production closure's 3.0 GiB. Tar extraction occurred before the directory-import timer.

| Import path                        |  Time |
| ---------------------------------- | ----: |
| Existing tar import                | 6.99s |
| Already-extracted directory import | 3.11s |

The prototype suggested that avoiding the second extraction could save approximately 3.88 seconds. All 54 `mbx-cache-store` tests and focused Clippy checks passed; the repository-wide gate stopped at the Bats end-to-end task because `bats` was absent locally. This was directional evidence rather than a prediction of released action performance.

## Released upstream implementation

The upstream implementation landed in [mbx PR #462](https://github.com/jdx/mr-boxington/pull/462) for parallel verification, [mbx PR #463](https://github.com/jdx/mr-boxington/pull/463) for directory bundles, and [action PR #41](https://github.com/jdx/mr-boxington-action/pull/41) for directory object transport. The changes shipped in [mbx 1.12.0](https://github.com/jdx/mr-boxington/releases/tag/v1.12.0) and [action 1.4.0](https://github.com/jdx/mr-boxington-action/releases/tag/v1.4.0).

Action 1.4.0 automatically selects directory-form object bundles with mbx 1.12.0 or newer. No additional workflow input is required beyond selecting object mode. The controlled warm comparison restored the same 773 actions and 4,914 objects in both action arms, with zero misses, while import fell from 5.97 seconds under action 1.3.1 to 0.26 seconds under action 1.4.0. Complete warm job time improved from 3m16s to 3m01s, seven seconds ahead of the sccache arm in that batch.

## Remaining research designs

### Read-only lower store with a writable job layer

Restore the selected closure as an immutable lower CAS and write new job results to an upper store. This could move digest work from serial setup into actual reads, avoid eager publication, and let malformed entries become misses or explicit diagnostics. It requires defined garbage collection, corruption, export, task-manifest precedence, and remote-cache composition behavior.

### Streaming standalone tar import

For transports that still require a standalone tar, stage entries under final CAS parent directories and publish only after the referenced closure is known. This could avoid a second complete staging tree, but it does not remove duplicate decompression when another archive carries the tar. Sparse files, manifest order, rollback, and incomplete visibility need explicit handling.

### Action setup overlap

A deterministic staging path or bootstrap payload could overlap binary setup with cache restore. Measure binary resolution, download, extraction, cache download, and cache extraction separately before assigning a saving.

### Optional Cargo registry and Git payload

An optional objects-with-inputs mode may help workflows that otherwise download dependency sources after restoring objects. The controlled comparison ran the same explicit dependency-fetch phase in every arm, so registry omission does not explain the measured object-versus-sccache result.

### Container-aware workspace-state restore

The diagnostic workspace-state experiment expanded the payload from 625 MiB compressed and 3.0 GiB logical to 877 MiB compressed and 4.3 GiB logical, increased import from 6.33 seconds to about 21.9 seconds, and conflicted with container-side target management. Useful support would require explicit host/container workspace and target mappings, caller-selected destinations, or lightweight metadata that references CAS objects without recreating a broad target tree.

## Qualification plan

Repeat exact warm, small-edit, changed-checkout-path, changed-target-path, native-host, and bind-mounted-container scenarios. Instrument setup, cache download and extraction, manifest parsing, verification, publication, first-hit latency, Cargo duration, and complete job duration. Test corruption, cancellation, outage, concurrent readers and writers, cache growth, trust separation, and rollback before broad adoption.

The current [decision D9](../decisions/README.md) qualifies mbx 1.12.0 with action 1.4.0 or newer as a portable clean-target canary alongside sccache. Target mode remains a separate mechanism because it restores Cargo target state.
