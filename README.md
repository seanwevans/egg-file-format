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

*The repository currently implements a minimal prototype with a composer and
hash verification and signing utilities.  The broader features listed above are planned for
future releases.*

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

After installation the `egg` command becomes available. The CLI currently
provides four subcommands:

```bash
egg build --manifest <file> --output <egg> [--force]
egg hatch --egg <egg> [--no-sandbox]
egg verify --egg <egg>
egg info --egg <egg>
```

Use `egg <command> -h` to see all options.

### Runtime Command Overrides

The commands used for each cell language during `egg hatch` can be
customized via environment variables. Set `EGG_CMD_PYTHON`,
`EGG_CMD_R`, or `EGG_CMD_BASH` to the path of the desired executable to
override the defaults.

```bash
EGG_CMD_PYTHON=/opt/python3/bin/python egg hatch --egg demo.egg
```

### Signing Key

The HMAC signature for `hashes.yaml` defaults to a built-in key. Set
`EGG_SIGNING_KEY` to override this value when building and verifying egg
files.

```bash
EGG_SIGNING_KEY=mysecret egg build --manifest examples/manifest.yaml --output demo.egg
```

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

4. Optionally verify the archive:

   ```bash
   egg verify --egg demo.egg
   ```

5. Inspect the archive metadata:

   ```bash
   egg info --egg demo.egg
   ```

The builder reads `manifest.yaml`, copies the referenced source files and writes
their hashes to `hashes.yaml`. The resulting archive is written to
`demo.egg`. For details about the resulting layout, see
[FORMAT.md#example-layout](FORMAT.md#example-layout). Progress on the builder
pipeline is tracked in the
[v0.5 – Builder Pipeline](ROADMAP.md#v05--builder-pipeline) section of the
roadmap.

### Testing

Install dependencies using `pip install .` (or `pip install -e .`) so that
packages like PyYAML are available. Then run `pytest` to execute the test
suite. You can also check formatting or style with tools like `ruff` or
`black`.

---

## License

MIT (see [LICENSE](LICENSE))

---

**egg.software** — "Hatch your world."

