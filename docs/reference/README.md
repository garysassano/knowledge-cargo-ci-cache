# Reference

This section keeps dense technical details that are useful for maintenance, review, or deep debugging but too heavy for first-read pages.

| Page                                                              | Purpose                                                                                                                              |
| ----------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| [Compiler-cache implementation](compiler-cache-implementation.md) | Pinned sccache, OpenDAL, and RunsOn behavior, source revisions, and dated release refresh; separate from proposals and measurements. |
| [Cache Measurement JSONL Schema](cache-measurement-schema.md)     | Machine-readable run, phase, metric, and resource-sample records for cache experiments.                                              |
| [Cache Measurement Fields](cache-measurement-fields.md)           | Detailed run, phase, metric, sample, and event vocabulary linked from the compact schema contract.                                   |
| [Cargo Freshness Signals](cargo-freshness-signals.md)             | Detailed Cargo freshness table, path notes, local target examples, dep-info example, and fingerprint example.                        |
| [Mise Tool Setup Details](mise-tool-setup-details.md)             | Detailed `mise-action` environment behavior, config discovery notes, diagram, historical failure, and upstream references.           |
| [RunsOn Cache And Disk Details](runson-cache-and-disk-details.md) | Archive, direct S3 compiler-cache, sticky-disk, snapshot, lifecycle, and trust-boundary details.                                     |
| [Source Mtime Alternatives](source-mtime-alternatives.md)         | Source retiming approaches and Retimer evidence; routes unstable content fingerprints to research.                                   |
| [Rust CI Cache Ecosystem Sources](vendor-ci-cache-sources.md)     | Core upstream projects, action forks, and historical sources; provider articles have their own index.                                |

Use these pages as supporting detail. Current recommendations still live in [Decisions](../decisions/README.md), approach selection lives in [Approaches](../approaches/README.md), and measured results live in [Evidence](../evidence/README.md).
