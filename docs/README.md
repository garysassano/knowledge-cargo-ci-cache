# Documentation

The documentation is organized by reader need first, then by ownership. Put information in one category and link to it from the others instead of repeating it.

## Reader Routes

| Task | Start with | Then use |
| --- | --- | --- |
| Get the current recommendation quickly | [Quickstart](quickstart.md) | [Decisions](decisions/README.md) |
| Choose a RunsOn cache or disk shape | [RunsOn Deployment Map](deployments/runs-on/README.md) | The linked canary or workflow example |
| Choose a cache approach | [Approaches](approaches/README.md) | The linked approach page and workflow example |
| Measure cache phases or compare runner resources | [Measuring Cache Performance](operations/measuring-cache-performance.md) | [Cache Measurement JSONL Schema](reference/cache-measurement-schema.md) |
| Debug unexpected recompilation | [Diagnosing Cargo Rebuilds In CI](operations/diagnosing-rebuilds.md) | [Cargo Freshness Model](concepts/cargo-freshness-model.md) |
| Maintain or change a conclusion | [Maintenance Checklist](operations/maintenance-checklist.md) | [Evidence](evidence/README.md), then [Decisions](decisions/README.md) |
| Review vendor Rust, `sccache`, or cache-product claims | [Vendor Rust And CI Cache Sources](reference/vendor-ci-cache-sources.md) | The linked approach, evidence, or deployment page |
| Audit dense technical detail | [Reference](reference/README.md) | The canonical page that links to it |

## Canonical Ownership

| Section | Owns | Entry point |
| --- | --- | --- |
| Decisions | Current conclusions, statuses, and superseded conclusions | [Decisions](decisions/README.md) |
| Approaches | Selection, tradeoffs, and decision surfaces | [Approaches](approaches/README.md) |
| Deployments | Platform-specific realizations, prerequisites, and trust boundaries | [RunsOn Deployment Map](deployments/runs-on/README.md) |
| Operations | Procedures, configuration, diagnosis, and maintenance | [Operations](operations/README.md) |
| Concepts | Stable mental models and cache semantics | [Concepts](concepts/README.md) |
| Evidence | Test questions, setup, observations, interpretation, and limitations | [Evidence](evidence/README.md) |
| Reference | Dense details that support shorter first-read pages | [Reference](reference/README.md) |

## Page Conventions

| Page type | Expected shape |
| --- | --- |
| Landing or quickstart | Current answer, reader path, compact links |
| Decision | Current conclusion, status, basis, change procedure |
| Approach | Status summary, use/do-not-use guidance, design, settings, limitations, evidence |
| Deployment | Ownership statement, platform-specific deltas, workflow shape, maintenance, related pages |
| Operation | Purpose, recommended configuration/procedure, ordering, caveats, references |
| Concept | Scope, short model, next links, reference links |
| Evidence | Question, test setup/progression, observations, interpretation, limitations, implications |
| Reference | Dense tables, examples, historical notes, and official links |
