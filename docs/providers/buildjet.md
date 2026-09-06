# BuildJet historical cache sources

**Status: historical coverage, reviewed 2026-09-06.** The retained primary source is [`BuildJet/cache`](https://github.com/BuildJet/cache), a provider-specific archive-cache wrapper. It was not archived at review time, but its last change was in March 2024, and its README links migration-oriented documentation.

No current first-party Rust- or sccache-specific guide/blog post was identified in this review. Preserve that gap rather than inventing an integration or treating repository availability as proof of current product support. No BuildJet configuration or performance result has been qualified here.

Use the [archive strategy map](../approaches/README.md) and [core action sources](../reference/vendor-ci-cache-sources.md) to interpret the wrapper. Refresh product availability and migration guidance before considering a new deployment.
