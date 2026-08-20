# Agent Instructions

This repository archives Rust/Cargo CI cache research, decisions, evidence, and copyable GitHub Actions examples. Optimize edits for accuracy, low duplication, and easy retrieval by other agents.

Use the routing table below to load only the pages relevant to the task instead of reading the entire archive.

## Canonical Entry Points

| Task | Use |
| --- | --- |
| Get the current recommendation quickly | `docs/quickstart.md` |
| See current conclusions and their status | `docs/decisions/README.md` |
| See superseded or revised conclusions | `docs/decisions/history.md` |
| Understand documentation ownership | `docs/README.md` |
| Choose or compare cache approaches | `docs/approaches/README.md` |
| Choose or apply a RunsOn cache/disk deployment | `docs/deployments/runs-on/README.md` |
| Configure fast CI tool setup | `docs/operations/mise-tool-setup.md` |
| Measure cache phases and runner bottlenecks | `docs/operations/measuring-cache-performance.md` |
| Explain Cargo freshness/no-op behavior | `docs/concepts/cargo-freshness-model.md` |
| Map Cargo state paths to cache coverage | `docs/concepts/cargo-path-coverage.md` |
| Explain cache primitives | `docs/concepts/cache-primitives.md` |
| Explain `Swatinem/rust-cache` inputs and cleanup | `docs/concepts/rust-cache-behavior.md` |
| Diagnose rebuilds | `docs/operations/diagnosing-rebuilds.md` |
| Review measured evidence | `docs/evidence/README.md` |
| Read detailed freshness signals, examples, or historical notes | `docs/reference/README.md` |
| Review vendor Rust, `sccache`, or GitHub Actions cache sources | `docs/reference/vendor-ci-cache-sources.md` |
| Record machine-readable cache measurements | `docs/reference/cache-measurement-schema.md` |
| Refresh examples and assumptions | `docs/operations/maintenance-checklist.md` |
| Copy workflow shapes | `examples/README.md` and `examples/workflows/` |
| Understand the local snapshot fork | `examples/actions/snapshot/README.md` |
| Understand the S3 Files mount action | `examples/actions/s3-files-mount/action.yml` |

## Current Conclusions

The archive's conclusions are maintained canonically in `docs/decisions/README.md`, with superseded conclusions recorded in `docs/decisions/history.md`. Do not restate the conclusions here or in other pages; link to the decisions page and keep only brief summaries elsewhere.

Treat the conclusions as archived, not as timeless upstream facts. Before changing any action version, service behavior, or recommendation that depends on current external behavior, follow `docs/operations/maintenance-checklist.md`, verify the relevant upstream documentation, and record the change in `docs/decisions/history.md`.

## Duplication Rules

- Keep current conclusions in `docs/decisions/README.md` and superseded conclusions in `docs/decisions/history.md`; summarize and link instead of restating them.
- Keep approach selection and tradeoffs in `docs/approaches/README.md`.
- Keep test setup, observations, measurements, interpretation, and limitations in focused pages under `docs/evidence/`.
- Do not maintain a chronological experiment log; move durable findings into the relevant concept, approach, operation, or evidence page.
- Keep diagnostic procedures in `docs/operations/diagnosing-rebuilds.md`.
- Keep `Swatinem/rust-cache` input and cleanup semantics in `docs/concepts/rust-cache-behavior.md`.
- Keep dense technical details, long tables, historical notes, and official-reference collections in `docs/reference/` when they would make first-read pages heavy.
- Keep RunsOn runner, Magic Cache, direct S3 `sccache`, and sticky-disk guidance in `docs/deployments/runs-on/README.md`, and keep generic Cargo guidance out of it; the deployment links to the canonical approach, concept, and operation pages instead of copying their configuration.
- Keep sanitized measurement records as JSONL in `docs/evidence/data/` beside the evidence page that cites them; keep the record contract in `docs/reference/cache-measurement-schema.md` and the copyable synthetic example in `examples/measurements/`.
- Keep copyable workflow examples in `examples/workflows/`.
- Link to canonical pages instead of repeating long tables or result summaries.

## Page Conventions

- Quickstart and landing pages stay short, opinionated, and link-heavy.
- Concept pages explain stable models and semantics, then link to reference pages for dense tables or examples.
- Approach pages use this order where applicable: status summary, related files, design/architecture, operational details, strengths, limitations, evidence, decision.
- Operation pages contain a purpose, recommended procedure or configuration, ordering, caveats, and references.
- Evidence pages contain a question, test setup or progression, observations, interpretation, limitations, and implications.
- Reference pages preserve dense tables, examples, historical notes, and official references.
- Deployment pages contain an ownership statement, platform-specific deltas, the workflow shape, maintenance notes, and related-page links; they link to generic approach/concept/operation pages instead of restating configuration.
- Category `README.md` files use a short ownership statement followed by a `Page | Purpose` table or a decision matrix.

## Markdown Style

- Keep each normal prose paragraph on one source line and let the renderer wrap it to the available width.
- Do not manually hard-wrap prose. Preserve structural line breaks in lists, tables, blockquotes, code fences, Mermaid diagrams, YAML, and front matter.
- Use "with" when naming combinations of cache approaches. Avoid `w/`, `+`, and "plus" as alternate labels for the same relationship.

## Example Maintenance

When editing workflow examples:

- Check current GitHub-owned action majors for `actions/checkout`, `actions/cache`, `actions/upload-artifact`, and `actions/download-artifact`.
- Keep `jdx/mise-action@v4`, `Swatinem/rust-cache@v2`, and `dtolnay/rust-toolchain@stable` unless there is a deliberate reason to change them.
- Preserve source-keyed target cache ordering: restore `rust-cache` first with `cache-targets: false`, then restore the full target cache.
- Preserve resolved compiler identity in source-keyed target keys by hashing `rustc -Vv` with source state.
- Do not add a broad target `restore-keys` fallback to source-keyed target examples; use one trusted target-cache writer.
- Preserve the generic nature of examples; do not add app-specific package names, secrets, runner labels, or deployment steps unless a page explicitly documents them as examples.

## Validation

Run these checks after relevant edits:

```bash
git diff --check
actionlint examples/workflows/*.yml
yq eval-all --exit-status 'true' examples/workflows/*.yml examples/actions/*/action.yml
(cd examples/actions/snapshot && go test ./...)
```

If `actionlint`, `yq`, or `go` is unavailable, say so and use a compatible tool declared in `~/.config/mise/config.toml`.

## Scope

This archive documents conclusions and reusable examples. Do not add live deployment credentials, organization-specific runner labels, or private repository details. If information comes from another local repository or opencode session history, summarize it as sanitized evidence and place it in the appropriate canonical page.
