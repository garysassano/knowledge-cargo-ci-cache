# Agent Instructions

This repository archives Rust/Cargo CI cache research, decisions, evidence, and copyable GitHub Actions examples. Optimize edits for accuracy, low duplication, and easy retrieval by other agents.

## Start here

Use [Documentation](docs/README.md) for the canonical reader routes, category ownership, and page conventions. Load the relevant category index and focused pages instead of reading the entire archive.

| Need                                     | Entry point                                                                                                                                    |
| ---------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| Current answer and status                | [Quickstart](docs/quickstart.md) and [Decisions](docs/decisions/README.md)                                                                     |
| Apply a cache approach                   | [Approaches](docs/approaches/README.md), [RunsOn deployment](docs/deployments/runs-on/README.md), and [Examples](examples/README.md)           |
| Diagnose or measure                      | [Operations](docs/operations/README.md) and [Evidence](docs/evidence/README.md)                                                                |
| Verify implementation or external claims | [Implementation reference](docs/reference/compiler-cache-implementation.md) and [ecosystem sources](docs/reference/vendor-ci-cache-sources.md) |
| Identify tools and storage               | [Tools](docs/tools/README.md) and [storage topologies](docs/concepts/storage-topologies.md)                                                    |
| Compare compiler tools                   | [sccache vs Mr. Boxington vs Kache](docs/tools/compiler-caches.md)                                                                             |
| Find provider strategies and articles    | [Provider index](docs/providers/README.md) and [strategy map](docs/approaches/README.md)                                                       |
| Track unstable freshness features        | [Cargo freshness alternatives](docs/research/cargo-freshness-alternatives.md)                                                                  |
| Explore unimplemented work               | [Research](docs/research/README.md) and the RunsOn collection's single roadmap                                                                 |

Implementation scope is [open-source components used directly in GitHub Actions](docs/README.md#scope-and-applicability). Keep closed-provider, other-platform, and unstable-feature documentation as explicitly classified research/reference material; do not discard it or promote its implementation into practical guidance implicitly.

## Retrieval and claim handling

Read the current decisions and the relevant category index first, then load only the focused pages needed. Use `rg` for exact tool names, errors, decision IDs, and version strings. Follow evidence links before quoting timings; retain workload, version, cache state, sample count, and limitations.

Keep four claim classes distinct: measured evidence, pinned source behavior, inference, and proposal. Material under `docs/research/` is proposed or untested unless a page explicitly identifies a measured result and links its evidence. External benchmarks and provider blog posts are source material, not measurements performed by this archive. A newer action major or binary release does not retroactively update old measurements.

## Current Conclusions

The archive's conclusions are maintained canonically in `docs/decisions/README.md`, with superseded conclusions recorded in `docs/decisions/history.md`. Do not restate the conclusions here or in other pages; link to the decisions page and keep only brief summaries elsewhere.

Treat the conclusions as archived, not as timeless upstream facts. Before changing any action version, service behavior, or recommendation that depends on current external behavior, follow `docs/operations/maintenance-checklist.md`, verify the relevant upstream documentation, and record the change in `docs/decisions/history.md`.

## Ownership and duplication

Follow the [canonical ownership and page conventions](docs/README.md#canonical-ownership). In particular:

- Keep conclusions in decisions/history, selection in approaches, configuration in operations/deployments, and measurements with setup and limitations in evidence. Link to each owner instead of repeating result tables, long checklists, or recommendations.
- Preserve versioned source behavior in reference and unimplemented designs under research. Keep one research task inventory and one owner per shared contract; validation links to those contracts and adds test assertions.
- Preserve failed experiments and superseded conclusions when they explain a decision. Do not maintain a chronological experiment diary.
- Keep sanitized measurements in `docs/evidence/data/`, the compact JSONL contract and detailed field vocabulary in reference, and the synthetic example in `examples/measurements/`.
- Keep supported copyable workflows in `examples/workflows/`; explicitly unmeasured workflow designs stay under research until qualified.
- Keep provider capabilities and blog collections in `docs/providers/`, core projects and historical wrappers in reference, and cross-tool selection in `docs/tools/compiler-caches.md`. Preserve source URLs when reorganizing. Keep untested candidates, including Kache, labeled explicitly.
- Keep decision diagrams beside their canonical explanation, with adjacent prose/links for retrieval. Diagrams must retain applicability and maturity boundaries; do not imply that a reference-only hosted service is an adopted implementation.
- Brief claim-status and version caveats may repeat for independent retrieval; complete procedures and behavioral rules must link to their owner.

## Ingesting new information

1. Search existing tool names/aliases, provider names, strategy pages, source URLs, and decision IDs before creating a page. Prefer enriching the existing owner; a newly discovered article is not automatically a new strategy.
2. Use the [ownership map](docs/README.md#canonical-ownership): named implementations in tools, combinations/tradeoffs in approaches, provider capabilities and blog sources in providers, storage semantics in concepts, and unstable work or implementation proposals in research. Keep measurements in evidence and operational procedures in operations/deployments.
3. Record a concise applicability/status statement and a review date. Distinguish an open-source component usable directly in GitHub Actions from a provider-dependent service, another CI platform, or an unstable experiment. Check the actual component's license/source; a public action does not establish that its backend is open source. Use “not assessed” when that boundary is unknown.
4. For external claims, link the primary source near the claim and record the relevant version, platform, cache layer, backend/protocol, and persistence lifetime. Keep provider timing claims separate from local measurements. Preserve useful closed-provider documentation and unstable ideas even when their exact implementation is outside practical scope.
5. Summarize only the durable new information in its owner and cross-link related tools, strategies, storage, and providers. Preserve contradictory or superseded evidence with its original context; resolve changed current conclusions through decisions/history. Do not silently turn an upstream fix into a local retest.
6. Link a new page from its category index and any directly affected reader route or strategy entry. Update a decision diagram when the choice actually changes. Keep one canonical comparison/result table and link to it; brief independently retrievable status caveats may repeat.
7. Run the relevant validation below, review the diff for lost source URLs, and check that each new page is reachable from the root README. Review scope, maturity, and duplicate claims manually: the checker enforces local links and measurement structure, not factual truth or editorial ownership.

Category indexes and these conventions are the ingestion contract. Extend them when a real recurring ambiguity appears; keep review dates and applicability beside the content they qualify.

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
- Preserve the [canonical Cargo path ownership rule](docs/concepts/cargo-path-coverage.md#compatibility-rule-canonical): archive-managed and snapshot/sticky-managed caches must not own the same paths.

## Validation

Run these checks after relevant edits:

```bash
git diff --check
python scripts/check_docs.py
actionlint examples/workflows/*.yml
yq eval-all --exit-status 'true' examples/workflows/*.yml examples/actions/*/action.yml
actionlint docs/research/runs-on-sccache/*.yml
yq eval-all --exit-status 'true' docs/research/runs-on-sccache/*.yml
(cd examples/actions/snapshot && go test ./...)
```

When changing the documentation checker, also run `python -m unittest discover -s scripts -p 'test_*.py'`. It uses only the Python standard library.

If `actionlint`, `yq`, or `go` is unavailable, say so and use a compatible tool declared in `~/.config/mise/config.toml`.

## Scope

This archive documents conclusions and reusable examples. Do not add live deployment credentials, organization-specific runner labels, or private repository details. If information comes from another local repository or opencode session history, summarize it as sanitized evidence and place it in the appropriate canonical page.
