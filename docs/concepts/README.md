# Concepts

This category owns stable explanations of Cargo's build-state model and the cache primitives used by the approaches in this archive.

## Pages

| Page                                                     | Purpose                                                                                                                      |
| -------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| [Cargo Freshness Model](cargo-freshness-model.md)        | Explains how Cargo decides whether a build unit is fresh or dirty.                                                           |
| [Cargo Path Coverage](cargo-path-coverage.md)            | Maps Cargo state paths to cache approaches.                                                                                  |
| [Cache Primitives](cache-primitives.md)                  | Compares clean targets, archive caches, compiler-object caches, sticky disks, filesystem snapshots, and network filesystems. |
| [`Swatinem/rust-cache` Behavior](rust-cache-behavior.md) | Explains relevant input defaults, save cleanup, workspace-crate handling, and exact-hit behavior.                            |
| [Cache layers](cache-layers.md)                          | Visual model of the work skipped by tool caches, container layers, Cargo freshness, compiler caches, and artifact reuse.     |
| [Storage topologies](storage-topologies.md)              | S3/GHA object and cache APIs, EBS block storage, local NVMe, tmpfs, network filesystems, and per-strategy placement.         |

## Page Shape

Concept pages open with a one-line scope statement, explain the stable model or semantics, and link to dense reference pages instead of embedding long tables where possible.
