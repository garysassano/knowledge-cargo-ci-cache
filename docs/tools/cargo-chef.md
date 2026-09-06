# cargo-chef

**Status: open-source tool, source review on 2026-09-06; not benchmarked here.** The tool is [`cargo-chef`](https://github.com/LukeMathWalker/cargo-chef), sometimes informally called Docker/Cargo chef. It creates a dependency recipe for Rust container builds; it is not a `RUSTC_WRAPPER` or a remote cache service.

## Design and applicability

`cargo chef prepare` captures the project skeleton and dependency inputs in a recipe. A separate container stage uses `cargo chef cook` to build the dependencies before copying application source and performing the real build. Docker can reuse that dependency layer when the relevant recipe and instruction inputs remain unchanged. Keep the Rust version consistent across stages and the cook/build working directories compatible. Run cooking in a disposable container stage, not over a developer worktree: upstream warns that it can overwrite source files. ([Upstream README](https://github.com/LukeMathWalker/cargo-chef))

This is directly applicable to an open-source Docker/BuildKit build invoked from GitHub Actions; no provider-specific build service is required. The [container-build strategy](../approaches/container-builds.md) owns layer invalidation, cache-mount persistence, and how a compiler wrapper can complement the recipe. The [storage map](../concepts/storage-topologies.md) explains local builder state versus exported layers.

## Sources and qualification

The [Earthly article collection](../providers/earthly.md) includes cargo-chef, persistent mounts, and sccache as separate strategies. [Depot's Rust sources](../providers/depot.md) provide another container-build perspective. Keep those provider/framework examples as references; they do not establish local performance or require adopting their platforms.

Test application-only edits, dependency/recipe changes, toolchain changes, and cold builders. Record whether Cargo was skipped by a layer hit or actually ran, and include layer import/export time. No cargo-chef comparison result has been added to [Evidence](../evidence/README.md).
