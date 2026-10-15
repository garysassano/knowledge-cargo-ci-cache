# Research

This section owns proposed designs, untested experiments, implementation dependencies, and promotion criteria. It does not change [current decisions](../decisions/README.md) or describe features as released merely because a design exists. Keep actual measurements in [Evidence](../evidence/README.md).

| Page                                                             | Purpose                                                                                                                       |
| ---------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| [RunsOn sccache research](runs-on-sccache/README.md)             | Archived 2026-10-15: direct-S3 gateway, broker and trust designs, largely superseded by RunsOn v3.5.0's isolated Magic Cache. |
| [Performance roadmap](runs-on-sccache/roadmap.md)                | Archived with the collection; its upstream sccache work items still apply.                                                    |
| [Cargo freshness alternatives](cargo-freshness-alternatives.md)  | Nightly content fingerprints, related unstable features, stable-feature distinctions, and qualification criteria.             |
| [Mr. Boxington object restore](mr-boxington-object-restore.md)   | History of the nested-archive bottleneck, its released directory-bundle fix, and remaining store research.                    |
| [Mr. Boxington remote backends](mr-boxington-remote-backends.md) | The proposed `mbx: true` Magic Cache helper, rejected direct S3, the cache server, and upstream proposals.                    |

Untested tools such as [Kache](../tools/kache.md) have tool profiles and participate in the [compiler-cache comparison](../tools/compiler-caches.md). Commercial/closed-provider and other-platform articles remain in [Providers](../providers/README.md), even where their exact implementation is outside the [direct GitHub Actions scope](../README.md#scope-and-applicability). Keep source discovery separate from proposed implementation work.
