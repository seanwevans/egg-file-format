# AGENTS.md

## Egg Build & Runtime Agents

Egg is built on a modular, agent-based system. Each agent is responsible for a
distinct phase in the lifecycle of an egg file.  The prototype includes several
lightweight agents wired into `egg_cli.py`:

- `egg/composer.py` – composer
- `egg/runtime_fetcher.py` – runtime fetcher
- `egg/sandboxer.py` – sandboxer
- `egg/precompute.py` – precompute helper
- `egg/chunker.py` – chunker
- `egg/hashing.py` – hashing and signing

### 🛠 Build-Time Agents

- **Composer Agent** – assembles sources and manifest. Invoked by `egg build`.
- **Runtime Fetcher** – collects runtime blocks referenced in the manifest. Automatically run during `egg build`.
- **Precompute Agent** – executes cells and stores outputs when `egg build --precompute` is used.
- **Hasher & Signer** – hashes all blobs and signs the manifest as part of `egg build`.
- **Chunker** – splits files into deterministic chunks; currently a standalone helper not directly called by the CLI.
- **Sandboxer** – prepares micro‑VM images. Triggered by `egg hatch` unless `--no-sandbox`.
- **Test Agent** – dry-runs the built egg to guarantee hatch-ability.

### 🐣 Runtime Agents

- **Hatcher**
  - Instantiates micro-VMs and launches runtimes/cells as needed.
- **UI Loader**
  - Loads trunk/layer 1 for instant UI; progressively loads lower layers/big data.
- **Security Monitor**
  - Enforces runtime limits and sandbox policy.
- **Output Streamer**
  - Streams code output, plots, and previews into the notebook UI.

### 🚦 Agent-Orchestration
- Agents are coordinated by a build pipeline manager (Egg Builder).
- Each agent logs its actions for build reproducibility and provenance.

### 🧰 CLI Modules
- **egg_cli.py** – command wrapper exposing `build`, `hatch` and `verify`.
  `egg build` calls the composer, runtime fetcher, precompute (optional),
  hasher and chunker helpers. `egg hatch` invokes the sandboxer to prepare
  micro‑VM images before running cells. Verification uses the hashing module.

---

See [FORMAT.md](FORMAT.md) for the file structure agents produce.

