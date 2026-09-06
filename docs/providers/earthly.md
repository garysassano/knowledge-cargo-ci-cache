# Earthly Rust cache articles

**Status: technical source collection, reviewed 2026-09-06; no local benchmark.** Earthly is included for its build framework and Rust articles. This page does not classify it as a GitHub Actions runner provider or assert availability of a current hosted service.

| First-party article                                                         | Strategy and scope                                                         |
| --------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| [Persistent Rust builds](https://earthly.dev/blog/incremental-rust-builds/) | BuildKit-backed Cargo cache mounts and persistent build state.             |
| [Rust with sccache](https://earthly.dev/blog/rust-sccache/)                 | Compiler-output caching and the work that can remain after a hit.          |
| [cargo-chef](https://earthly.dev/blog/cargo-chef/)                          | Dependency recipes and Docker layer reuse when application source changes. |

These are three different layers. A dependency layer can skip executing Cargo, a native mount can retain Cargo's own target state, and a compiler cache can return outputs after Cargo decides to invoke rustc. Use the [container-build explanation](../approaches/container-builds.md) to interpret the articles together without combining their headline results.

Before reproducing an example, verify current upstream tool interfaces and whether the builder that owns the mutable mounts survives the next job. Compare cold, same-source, source-change, and dependency-change builds separately using the [common measurement controls](../operations/measuring-cache-performance.md).
