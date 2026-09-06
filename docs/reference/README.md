# Reference

This section keeps dense technical details that are useful for maintenance, review, or deep debugging but too heavy for first-read pages.

| Page | Purpose |
| --- | --- |
| [Cache Measurement JSONL Schema](cache-measurement-schema.md) | Machine-readable run, phase, metric, and resource-sample records for cache experiments. |
| [Cache Measurement Fields](cache-measurement-fields.md) | Detailed run, phase, metric, sample, and event vocabulary linked from the compact schema contract. |
| [Cargo Freshness Signals](cargo-freshness-signals.md) | Detailed Cargo freshness table, path notes, local target examples, dep-info example, and fingerprint example. |
| [Mise Tool Setup Details](mise-tool-setup-details.md) | Detailed `mise-action` environment behavior, config discovery notes, diagram, historical failure, and upstream references. |
| [RunsOn Cache And Disk Details](runson-cache-and-disk-details.md) | Archive, direct S3 compiler-cache, sticky-disk, snapshot, lifecycle, and trust-boundary details. |
| [Source Mtime Alternatives](source-mtime-alternatives.md) | Related source-mtime approaches, Retimer evidence, and Cargo checksum-freshness notes. |
| [Rust CI Cache Ecosystem Sources](vendor-ci-cache-sources.md) | Maintained catalog of first-party projects, actions, provider integrations, technical articles, and historical wrappers. |

Use these pages as supporting detail. Current recommendations still live in [Decisions](../decisions/README.md), approach selection lives in [Approaches](../approaches/README.md), and measured results live in [Evidence](../evidence/README.md).
