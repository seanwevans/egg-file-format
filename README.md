# 🥚 egg file format

**egg** is a next-generation, self-contained, portable, and executable document format for reproducible code, data, and results.

Inspired by the metaphor of the egg—slow to build, instant to hatch—egg files deliver “just works” experiences for scientific, analytic, and computational notebooks in any language, on any machine, with zero configuration.

---

## Features

- **Self-contained:** Everything you need—code, data, runtimes, outputs—in a single `.egg` file.
- **Multi-language:** Compose any number of languages/interpreters (e.g. Python, APL, Julia, R, custom VMs).
- **Zero-config:** No installation, no dependencies; "hatch" an egg on any system with the egg viewer.
- **Reproducible:** Deterministic build; every run gives the same results.
- **Secure:** Strong sandboxing via micro-VMs; safe to run untrusted code.
- **Scalable:** Designed for the future—handles GBs to TBs of data and code with instant load.
- **Audit & provenance:** Build logs and full environment info are baked into every file.

---

## Why "egg"?

> Like an egg, your document is crafted slowly and deliberately, encasing everything needed for life. When you hatch it—instant, perfect, agile execution.

- **Build time is slow, careful, deliberate.**
- **Run time is instant, agile, and reliable.**

---

## Getting Started

*Coming soon!* This project is in early stages.
You can start experimenting with a minimal two-language notebook using
[`examples/manifest.yaml`](examples/manifest.yaml).

- See [AGENTS.md](AGENTS.md) for the agent and build pipeline design.
- See [FORMAT.md](FORMAT.md) for the egg file format specification.
- See [SECURITY.md](SECURITY.md) for sandboxing and threat model.
- See [CONTRIBUTING.md](CONTRIBUTING.md) if you want to join the hatch!

## Installation

Install the CLI from source with `pip`:

```bash
pip install .
```

## Usage

After installation the `egg` command becomes available. The CLI has two
subcommands with a few options:

```bash
egg build --manifest <file> --output <egg> [--force]
egg hatch --egg <egg> [--no-sandbox]
```

Use `egg <command> -h` to see all options.

### Example Build Walkthrough

Below is a minimal walkthrough using the placeholder implementation:

1. Prepare the demo manifest and sources found in `examples/`.
2. Run the build command specifying the manifest and desired output:

   ```bash
   egg build --manifest examples/manifest.yaml --output demo.egg
   ```

3. Hatch the resulting file:

   ```bash
   egg hatch --egg demo.egg
   ```

The builder reads `manifest.yaml`, gathers runtimes and assets, and emits the
`demo.egg` file. For details about the resulting layout, see
[FORMAT.md#example-layout](FORMAT.md#example-layout). Progress on the builder
pipeline is tracked in the
[v0.5 – Builder Pipeline](ROADMAP.md#v05--builder-pipeline) section of the
roadmap.

---

## License

MIT (see [LICENSE](LICENSE))

---

**egg.software** — "Hatch your world."

