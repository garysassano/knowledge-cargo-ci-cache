# Agent Instructions

This repository archives Rust/Cargo CI cache research, decisions, evidence, and copyable GitHub Actions examples.

## Route by task

Use [Documentation](docs/README.md) for canonical ownership and navigation, then load only the pages relevant to the task. Use [Decisions](docs/decisions/README.md) for current conclusions, [Approaches](docs/approaches/README.md) and [Examples](examples/README.md) for application, [Operations](docs/operations/README.md) and [Evidence](docs/evidence/README.md) for diagnosis or measurement, and [Research](docs/research/README.md) for unimplemented work.

Before updating versions, external behavior, or current recommendations, follow [the maintenance checklist](docs/operations/maintenance-checklist.md), verify primary upstream sources, and record changed conclusions in `docs/decisions/history.md`.

## Evidence and ownership

- Keep measured evidence, pinned source behavior, inference, and proposal distinct. External benchmarks and provider posts are sources, not measurements performed here; carry workload, version, cache state, sample count, and limitations with timings.
- Follow the [canonical ownership map](docs/README.md#canonical-ownership) instead of duplicating procedures, result tables, or recommendations. Preserve useful failed experiments and superseded conclusions with their context.
- Keep supported workflows under `examples/workflows/`, measurements under `docs/evidence/`, versioned behavior under `docs/reference/`, and untested designs under `docs/research/` until qualified.
- Preserve source URLs, applicability, maturity, review dates, and platform or license boundaries. Public availability does not prove that a backend is open source; use “not assessed” when unknown.
- Practical implementation is limited to open-source components used directly in GitHub Actions. Keep closed-provider, other-platform, and unstable material explicitly classified as research or reference.

For workflow-example changes, use the maintenance checklist for version policy and the [Cargo path ownership rule](docs/concepts/cargo-path-coverage.md#compatibility-rule-canonical) for cache composition. Keep examples generic and preserve their documented ordering, key identity, writer, and restore-key constraints.

## Validation

The validation commands are local and have no production access. Run the checks relevant to the changed paths, fix failures caused by the work, and rerun affected checks before finishing:

```bash
git diff --check
python scripts/check_docs.py
actionlint examples/workflows/*.yml docs/research/runs-on-sccache/*.yml
yq eval-all --exit-status 'true' examples/workflows/*.yml examples/actions/*/action.yml docs/research/runs-on-sccache/*.yml
(cd examples/actions/snapshot && go test ./...)
```

When changing the documentation checker, also run `python -m unittest discover -s scripts -p 'test_*.py'`. Use tools declared in `~/.config/mise/config.toml` rather than installing missing tools imperatively.

## Style and scope

Keep normal prose paragraphs on one source line. Use “with” for cache combinations, not `w/`, `+`, or “plus”. Do not add credentials, organization-specific runner labels, private repository details, or unsanitized local-session evidence.
