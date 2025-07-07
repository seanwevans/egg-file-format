# 🥚 egg file format

[![Coverage](https://img.shields.io/badge/coverage-100%25-cyan)](https://img.shields.io)
[![Pylint](https://img.shields.io/badge/pylint-9.39%2F10-green)](https://pylint.pycqa.org/)

**egg** is a self-contained, portable, and executable document format for reproducible code, data, and results. Inspired by the egg metaphor—slow to build, instant to hatch—it aims to make notebooks in any language "just work" on any machine with zero configuration.

---

## Features

- **Self-contained:** Everything—code, data, runtimes, outputs—bundled in a single `.egg` file.
- **Multi-language:** Mix Python, APL, Julia, R, or custom VMs in one archive.
- **Zero-config:** Hatch an egg anywhere without installing dependencies.
- **Reproducible:** Deterministic build process ensures consistent results.
- **Secure:** Strong micro-VM sandboxing for untrusted code.
- **Scalable:** Designed for GB–TB scale data with instant loading.
- **Audit & provenance:** Full build logs and environment info baked in.

*This repository implements a minimal prototype with additional agents for fetching runtimes, sandboxing, precomputing outputs and deterministic chunking. The broader features above are planned for future releases.*

---

## Quick Start

Install the CLI and build the demo archive:

```bash
pip install -e .  # install in editable mode to load example plug-ins
egg build --manifest examples/manifest.yaml --output demo.egg --precompute
egg hatch --egg demo.egg
egg verify --egg demo.egg
egg info --egg demo.egg
```

For a Julia example see `examples/julia_manifest.yaml`.
A full manifest mixing twelve languages is provided in `examples/dozen_manifest.yaml`.

## Writing Plug-ins

Egg can be extended with custom Python modules. Implement a `register()`
function that either returns runtime commands or performs agent side effects.
Declare the module under `egg.runtimes` or `egg.agents` in
`pyproject.toml`. See [examples/](examples/) for sample plug-ins.

Install your plug-in like any other package and run the CLI with the
``-vv`` flag to confirm it loads:

```bash
pip install my-egg-plugin
egg -vv --help  # shows "[plugins] loaded ..." messages
```

---

## CLI Overview

```bash
egg build  --manifest <file> --output <egg> [--precompute] [--signing-key <file>]
egg hatch  --egg <egg> [--no-sandbox]
egg verify --egg <egg> [--signing-key <file>]
egg info   --egg <egg>
```

Use `egg <command> -h` to see all options. Runtime commands can be overridden with `EGG_CMD_PYTHON`, `EGG_CMD_R`, or `EGG_CMD_BASH`. The signing key for `hashes.yaml` can be changed with `--signing-key` or the `EGG_SIGNING_KEY` environment variable.

### Testing

```bash
pip install .       # installs the CLI
pip install -r requirements-dev.txt
pre-commit run --all-files
```
This formats code, lints with flake8 and pylint, runs tests with coverage,
and updates the README badges.

---

## More Documentation

- [AGENTS.md](AGENTS.md) – build pipeline and agent design
- [FORMAT.md](FORMAT.md) – egg file format specification
- [SECURITY.md](SECURITY.md) – sandboxing and threat model
- [ROADMAP.md](ROADMAP.md) – planned features
- [CONTRIBUTING.md](CONTRIBUTING.md) – how to contribute
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) – community expectations
- [CHANGELOG.md](CHANGELOG.md) – release notes

## Citation

If you use this project, cite it using the metadata in [CITATION.cff](CITATION.cff).

## License

MIT – see [LICENSE](LICENSE)

---

**egg.software** — "Hatch your world."
