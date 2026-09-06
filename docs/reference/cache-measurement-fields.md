# Cache measurement field reference

This page owns the detailed field, phase, and metric vocabulary for [the JSONL contract](cache-measurement-schema.md). Field names are extensible; archived unknown values remain unknown. Use the existing committed records as examples and document new names in the evidence page that introduces them.

## Common Fields

| Field                | Type    | Required    | Meaning                                                                                                                                                                                |
| -------------------- | ------- | ----------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `schema_version`     | string  | Yes         | `cargo-ci-cache/v1`                                                                                                                                                                    |
| `record_type`        | string  | Yes         | One of the [contract record types](cache-measurement-schema.md#record-types)                                                                                                           |
| `run_id`             | string  | Yes         | Opaque unique trial identifier                                                                                                                                                         |
| `strategy`           | string  | Yes         | Stable generic name such as `no-cache`, `input-only-archive`, `whole-target-archive`, `s3-sccache`, `sticky-inputs`, or `sticky-target`                                                |
| `scenario_id`        | string  | Yes         | Opaque pairing identifier shared by directly comparable trials                                                                                                                         |
| `trial`              | integer | Recommended | Repetition number within the scenario and strategy                                                                                                                                     |
| `cache_state`        | string  | Recommended | `cold`, `warm`, `warm-exact`, `warm-fallback`, `warm-partial`, `mixed`, `miss`, or `not-applicable`; `warm-exact` may describe an exact archive restore, not successful compiler reuse |
| `privacy`            | string  | Yes         | Must be `sanitized` for data committed to this repository                                                                                                                              |
| `measurement_source` | string  | Recommended | `monotonic-marker`, `action-log`, `tool-report`, `process-wrapper`, `resource-sampler`, `derived`, or another documented generic source                                                |

## `run` Record

| Field               | Type    | Meaning                                                                                        |
| ------------------- | ------- | ---------------------------------------------------------------------------------------------- |
| `runner_profile_id` | string  | Opaque profile used to group comparable runners                                                |
| `runner`            | object  | Sanitized CPU, memory, network, and storage characteristics                                    |
| `workload`          | object  | Sanitized toolchain, command class, concurrency, and workload version                          |
| `job_total_ms`      | integer | Runner-assigned start through completion of post steps                                         |
| `queue_ms`          | integer | Eligibility through runner assignment, kept outside `job_total_ms` unless documented otherwise |
| `exit_status`       | integer | Process or job result where available                                                          |
| `save_outcome`      | string  | `saved`, `skipped-hit`, `skipped-policy`, `lost-race`, `failed`, or `not-applicable`           |

Suggested `runner` fields are `architecture`, `vcpus`, `memory_bytes`, `cpu_model`, `cpu_profile`, `public_instance_type`, `advertised_network_gbps`, `object_store_proximity`, `object_store_endpoint_class`, `workspace_storage`, `workspace_filesystem`, and `workspace_capacity_bytes`. Omit internal runner labels and any infrastructure identifier that reveals private topology.

Suggested `workload` fields are `class`, `toolchain`, `compiler_identity`, `linker_class`, `profile`, `target`, `incremental`, `codegen_units`, `lto`, `concurrency`, `build_flags_digest`, and an opaque `version`. Do not include private package names, source paths, command arguments, raw flags, or commit hashes.

## `phase` Record

| Field             | Type    | Required    | Meaning                                                                                 |
| ----------------- | ------- | ----------- | --------------------------------------------------------------------------------------- |
| `phase_id`        | string  | Yes         | Unique within `run_id`                                                                  |
| `phase`           | string  | Yes         | Canonical or explicitly named combined phase                                            |
| `parent_phase_id` | string  | No          | Structural parent such as `job-total`, `restore-total`, or `workload-total`             |
| `start_offset_ms` | integer | No          | Monotonic offset from runner-assigned job start                                         |
| `end_offset_ms`   | integer | No          | Monotonic offset from runner-assigned job start                                         |
| `duration_ms`     | integer | Yes         | Direct or aggregate duration                                                            |
| `accounting`      | string  | Yes         | `exclusive`, `inclusive`, `may-overlap`, or `aggregate-only`                            |
| `precision_ms`    | integer | Recommended | Resolution or known rounding bound                                                      |
| `attribution`     | string  | Recommended | `measured`, `log-derived`, `tool-reported`, or `inferred`                               |
| `scope`           | string  | Recommended | Generic owner such as `cargo-inputs`, `target-archive`, `compiler-cache`, or `workload` |

Apply the [phase accounting](cache-measurement-schema.md#phase-accounting) and [wall-time rules](cache-measurement-schema.md#overlap-and-wall-time-rules) from the contract.

Canonical phase names are:

| Area               | Phase names                                                                                                                                   |
| ------------------ | --------------------------------------------------------------------------------------------------------------------------------------------- |
| Top level          | `job_total`, `queue`, `runner_setup`, `tool_setup`, `unattributed_job_overhead`                                                               |
| Archive restore    | `cache_restore_total`, `cache_lookup`, `cache_download`, `cache_lookup_download`, `archive_extract`, `cache_restore_other`                    |
| Workload           | `workload_total`, `cargo_orchestration`, `compiler_request`, `compiler_cache_lookup`, `compiler_cache_materialize`, `compile`, `link`, `test` |
| Archive save       | `cache_post_total`, `cache_scan`, `cache_cleanup`, `archive_create_compress`, `archive_compress`, `cache_upload`, `cache_post_other`          |
| Native persistence | `snapshot_restore`, `volume_attach`, `volume_mount`, `snapshot_commit`, `volume_unmount`, `volume_detach`                                     |

Prefer the specific names. Use `cache_lookup_download` or `archive_create_compress` only when the source data does not expose a reliable split.

## `metric` Record

| Field         | Type   | Required    | Meaning                                                                                                      |
| ------------- | ------ | ----------- | ------------------------------------------------------------------------------------------------------------ |
| `name`        | string | Yes         | Stable metric name                                                                                           |
| `value`       | number | Yes         | Numeric value                                                                                                |
| `unit`        | string | Yes         | `bytes`, `files`, `requests`, `objects`, `percent`, `milliseconds`, `seconds`, `count`, or a documented unit |
| `scope`       | string | Recommended | Cache or workload component                                                                                  |
| `aggregation` | string | Recommended | `point`, `sum`, `average`, `maximum`, `minimum`, `median`, `p90`, or `p95`                                   |
| `precision`   | string | Recommended | `exact`, `rounded`, or `approximate`                                                                         |

Common metric names include:

| Category                    | Metric names                                                                                                                                                                                                      |
| --------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Archive                     | `archive_compressed_bytes`, `restored_uncompressed_bytes`, `restored_file_count`, `post_cleanup_bytes`, `post_cleanup_file_count`, `uploaded_bytes`, `compression_ratio`                                          |
| Filesystem                  | `target_bytes_before`, `target_bytes_after`, `target_file_count_before`, `target_file_count_after`, `free_bytes`, `free_inodes`                                                                                   |
| Compiler cache              | `compile_requests`, `executed_cacheable_requests`, `cache_hits`, `cache_misses`, `non_cacheable_calls`, `cache_errors`, `compiler_cache_reported_bytes`                                                           |
| S3                          | `s3_get_requests`, `s3_put_requests`, `s3_head_requests`, `s3_downloaded_bytes`, `s3_uploaded_bytes`                                                                                                              |
| Workload                    | `cargo_units`, `rustc_invocations`, `rustc_wall_sum_ms`, `rustc_cpu_sum_ms`, `peak_rustc_processes`, `tests_executed`                                                                                             |
| Runner/process              | `single_thread_calibration_ms`, `process_user_cpu_ms`, `process_system_cpu_ms`, `maximum_rss_bytes`, `voluntary_context_switches`, `involuntary_context_switches`                                                 |
| Storage/network calibration | `local_read_bytes_per_second`, `local_write_bytes_per_second`, `metadata_operations_per_second`, `s3_bulk_download_bytes_per_second`, `s3_bulk_upload_bytes_per_second`, `s3_request_p50_ms`, `s3_request_p90_ms` |
| Derived                     | `download_bytes_per_second`, `extract_bytes_per_second`, `compress_bytes_per_second`, `upload_bytes_per_second`, `cache_handling_share_percent`, `phase_coverage_percent`                                         |

Keep tool-reported `sccache` latency and cache-size metrics under explicit names and units from the pinned version. Do not normalize an unknown statistic into a different meaning.

## `resource_sample` Record

| Field | Type | Meaning |
| --- | --- |
| `offset_ms` | integer | Monotonic offset from runner-assigned job start |
| `interval_ms` | integer | Sampling interval represented by the values |
| `cpu_user_percent` | number | System-wide CPU user percentage |
| `cpu_system_percent` | number | System-wide CPU system percentage |
| `cpu_iowait_percent` | number | System-wide CPU I/O-wait percentage |
| `memory_used_bytes` | integer | System-wide memory in use |
| `process_rss_bytes` | integer | Workload process-tree RSS when available |
| `disk_read_bytes` | integer | Bytes read during the interval |
| `disk_write_bytes` | integer | Bytes written during the interval |
| `disk_read_ops` | integer | Read operations during the interval |
| `disk_write_ops` | integer | Write operations during the interval |
| `network_rx_bytes` | integer | Interface bytes received during the interval |
| `network_tx_bytes` | integer | Interface bytes transmitted during the interval |
| `rustc_processes` | integer | Concurrent rustc or compiler-wrapper processes |

Resource samples support diagnosis and interval correlation. They are not phases and must not be summed into wall time.

## `event` Record

| Field | Type | Meaning |
| --- | --- |
| `offset_ms` | integer | Monotonic offset when known |
| `event` | string | Generic event name |
| `outcome` | string | Generic result |
| `detail` | object | Sanitized structured attributes |

Useful event names include `cache_exact_hit`, `cache_fallback_hit`, `cache_miss`, `cache_save_race`, `cache_reset`, `backend_unavailable`, `timeout`, `cancellation`, and `measurement_gap`.
