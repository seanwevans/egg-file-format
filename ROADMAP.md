# ROADMAP.md

## Overview

This roadmap sketches the planned development of the **egg file format** and its tooling. Versions and details may change, but the high-level goals remain consistent: a fully self-contained, reproducible document format with simple build and hatch commands.

## Milestones

### v0.1 – Prototype
- Minimal command‑line interface for `build` and `hatch` (placeholders today).
- Draft format specification published in `FORMAT.md`.
- Example manifest and two-language demo notebook.

### v0.2 – Verification Tools
- Hashing utilities and HMAC signing for `hashes.yaml`.
- `egg verify` command to validate archives and detect tampering.

### v0.5 – Builder Pipeline
- Composer, runtime block fetcher, and sandboxer agents integrated.
- `egg_cli.py` can assemble a basic egg with code and data blocks.
- Preliminary tests to ensure determinism and hash verification.

### v0.6 – CLI Enhancements
- Environment variable overrides for runtime command paths.
- Improved help messages and `--force` overwrite flag.

### v1.0 – Stable Format
- Finalize manifest schema and static table layout.
- Cross-platform hatcher to run eggs on Linux, macOS, and Windows.
- Registry for official runtime blocks and community-contributed interpreters.

### v1.1 – Precompute & Caching
- Precompute agent to bake cell outputs for instant previews.
- Incremental loading and caching of large datasets.

### v1.2 – Security Hardening
- Micro‑VM sandbox integration with stricter resource policies.
- Verified runtime blocks downloaded only from trusted registries.

### v2.0 – Ecosystem Expansion
- Plug‑in system for custom agents and alternative runtimes.
- Integration with popular notebook UIs and hosting platforms.

## Longer Term

The project aims to become the standard portable notebook format for science and analytics. Future work includes deep security hardening, a public block registry, and collaborative features built on top of the core egg specification.
