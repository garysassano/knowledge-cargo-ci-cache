# Research

This section owns proposed designs, untested experiments, implementation dependencies, and promotion criteria. It does not change [current decisions](../decisions/README.md) or describe features as released merely because a design exists. Keep actual measurements in [Evidence](../evidence/README.md).

| Page                                                            | Purpose                                                                                                                   |
| --------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| [RunsOn sccache research](runs-on-sccache/README.md)            | Routes action lifecycle, direct S3 tuning, trust, gateway, sticky storage, alternative backend, and validation questions. |
| [Performance roadmap](runs-on-sccache/roadmap.md)               | Prioritized experiment sequence with completion tests and work-package boundaries.                                        |
| [Cargo freshness alternatives](cargo-freshness-alternatives.md) | Nightly content fingerprints, related unstable features, stable-feature distinctions, and qualification criteria.         |

Untested tools such as [Kache](../tools/kache.md) have tool profiles and participate in the [compiler-cache comparison](../tools/compiler-caches.md). Commercial/closed-provider and other-platform articles remain in [Providers](../providers/README.md), even where their exact implementation is outside the [direct GitHub Actions scope](../README.md#scope-and-applicability). Keep source discovery separate from proposed implementation work.
