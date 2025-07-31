# AGENTS.md

This guide explains the role of each agent in the Egg build system and how they
work together.  Agents are small Python modules located in the `egg/` package.
They each handle a single phase of the egg lifecycle and can be combined via the
CLI wrapper found in `egg_cli.py`.

## Directory Layout

- `egg/composer.py` – assembles sources and manifests
- `egg/runtime_fetcher.py` – gathers runtime blobs referenced in a manifest
- `egg/sandboxer.py` – prepares micro‑VM images
- `egg/precompute.py` – optional helper that executes cells during build
- `egg/chunker.py` – deterministic file chunking utility
- `egg/hashing.py` – hashing and signing helpers

All of these agents are orchestrated by the CLI. Additional examples and helper
scripts live in the `scripts/` and `examples/` directories.

## 🛠 Build‑Time Agents

The following agents run when `egg build` is executed:

- **Composer** – gathers source files and writes out the manifest
- **Runtime Fetcher** – collects external runtimes so they are embedded in the egg
- **Precompute** – executes cells when `egg build --precompute` is used
- **Hasher & Signer** – computes hashes for all blobs and signs the manifest
- **Chunker** – splits files into stable chunks to deduplicate content
- **Sandboxer** – constructs micro‑VM images (also used by `egg hatch`)
- **Test Agent** – dry‑runs a build to confirm the resulting egg hatches

Build‑time agents can log verbose output for reproducibility and debugging. All
agents are designed to be composable and self‑contained.

## 🐣 Runtime Agents

When an egg is hatched the runtime agents take over:

- **Hatcher** – launches micro‑VMs and executes cells on demand
- **UI Loader** – loads the UI rapidly and fetches lower layers as needed
- **Security Monitor** – enforces sandbox policies and resource limits
- **Output Streamer** – streams cell output back into the notebook UI

Runtime agents aim to keep startup latency low while maintaining security.

## 🚦 Agent Orchestration

Agents are coordinated by a simple pipeline manager built into the CLI. Each
agent publishes log events that can be replayed to reproduce the build process.
The modular design also means new agents can be added easily without modifying
existing ones.

### Creating New Agents

1. Place the new module in the `egg/` package and document the public API.
2. Keep the interface small—each agent should focus on a single task.
3. Update this file and any examples to reflect the new functionality.

### Developer Workflow

Run the project's automated checks before submitting a pull request:

```bash
pip install .
pip install -r requirements-dev.txt
pre-commit run --all-files
```

These commands format the code, perform static analysis and run the test suite.
Refer to [CONTRIBUTING.md](CONTRIBUTING.md) for details on style guidelines.

### Cleaning Artifacts

Use `egg clean [path] [--dry-run]` to delete `precompute_hashes.yaml`, `*.out`
files, and any `sandbox` directories beneath a path. Pass `--dry-run` to show
targets without removing them.

### Plug-in Development

Egg's functionality can be extended through Python entry points. Create a
`register()` function in your module and list it under the appropriate group in
`pyproject.toml`:

```toml
[project.entry-points."egg.runtimes"]
ruby = "mypkg.ruby_plugin:register"

[project.entry-points."egg.agents"]
hello = "mypkg.hello_agent:register"
```

Runtime plug-ins should return a mapping of language names to command lists.
Agent plug-ins run for their side effects and may modify the CLI or agents.
Both types are discovered by `egg.utils.load_plugins()` when the CLI starts.

---

See [FORMAT.md](FORMAT.md) for the file structure produced by these agents.
