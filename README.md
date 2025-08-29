# 🥚 egg file format


[![Coverage](https://img.shields.io/badge/coverage-98%25-cyan)](https://img.shields.io)
[![Pylint](https://img.shields.io/badge/pylint-9.50%2F10-green)](https://pylint.pycqa.org/)


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
egg clean .
```
A file `<source>.out` is created for each executed cell containing stdout. If a
cell fails, its stderr is written to `<source>.err` for later inspection.

For a Julia example see `examples/julia_manifest.yaml`.
A full manifest mixing twelve languages is provided in `examples/dozen_manifest.yaml`.
The example plug-ins used above are described in [AGENTS.md](AGENTS.md#plug-in-development).

## Writing Plug-ins

Egg can be extended with custom Python packages. Each plug-in exposes a
`register()` function and is distributed like any other package:

```
my-egg-plugin/
├── pyproject.toml
└── my_pkg/
    ├── __init__.py
    ├── runtime.py      # runtime plug-in
    └── hello_agent.py  # agent plug-in
```

Place the `register()` function in the module referenced by your entry
point. A minimal `pyproject.toml` looks like:

```toml
[project.entry-points."egg.runtimes"]
python = "my_pkg.runtime:register"

[project.entry-points."egg.agents"]
hello = "my_pkg.hello_agent:register"
```

At start-up the CLI calls `egg.utils.load_plugins()`, which scans the
`egg.runtimes` and `egg.agents` entry point groups, imports each module
and invokes its `register()` function. Runtime plug-ins return a mapping
of language names to command lists, while agent plug-ins run for their
side effects.

Install your plug-in like any other package and run the CLI with the
`-vv` flag to confirm it loads:

```bash
pip install my-egg-plugin
egg -vv --help  # shows "[plugins] loaded ..." messages
```

See [examples/](examples/) for sample plug-ins and
[AGENTS.md](AGENTS.md#plug-in-development) for more on agent architecture
and plug-in development.

## Advanced Usage

The manifest `examples/advanced_manifest.yaml` demonstrates how to
declare dependencies and enable permissions:

```yaml
name: "Advanced Notebook"
description: "Example demonstrating dependencies, permissions, and mixed languages"
dependencies:
  - python:3.11
  - r:4.3
  - bash:5
permissions:
  network: true
  filesystem: true
```

It runs Python, Bash and R cells from the `examples/` directory. Build
and hatch it like so:

```bash
egg build --manifest examples/advanced_manifest.yaml --output advanced.egg --precompute
egg hatch --egg advanced.egg
```

---

## CLI Overview

```bash
egg build  --manifest <file> --output <egg> [--precompute] [--signing-key <file>]
egg hatch  --egg <egg> [--no-sandbox]
egg verify --egg <egg> [--signing-key <file>]
egg info   --egg <egg>
egg languages
egg clean  [path] [--dry-run]
```

Use `egg <command> -h` to see all options. Runtime commands and other settings can be configured via environment variables; see [Environment Variables](#environment-variables).

The `clean` command removes `precompute_hashes.yaml`, `*.out` and `*.err` files,
and any `sandbox` directories beneath the given path. Use `--dry-run` to list
targets without deleting them.

### Environment Variables

| Variable | Description |
|----------|-------------|
| `EGG_CMD_PYTHON` | Command executed for Python cells |
| `EGG_CMD_R` | Command executed for R cells |
| `EGG_CMD_BASH` | Command executed for Bash cells |
| `EGG_SIGNING_KEY` | HMAC key used to sign `hashes.yaml` |
| `EGG_REGISTRY_URL` | Registry base URL for runtime downloads |
| `EGG_DOWNLOAD_TIMEOUT` | Default timeout (seconds) for runtime downloads |

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
