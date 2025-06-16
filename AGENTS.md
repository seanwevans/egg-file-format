# AGENTS.md

## Egg Build & Runtime Agents

Egg is built on a modular, agent-based system. Each agent is responsible for a
distinct phase in the lifecycle of an egg file.  Only the composer and hashing
agents are implemented in this prototype.  They live in
`egg/composer.py` and `egg/hashing.py` and are driven by the CLI.

### 🛠 Build-Time Agents

- **Composer Agent**
  - Assembles code, data, outputs, and manifest into initial hierarchy.
- **Runtime Block Fetcher**
  - Gathers all specified language/runtime blocks (e.g., Python, APL, Julia, R, custom VMs).
- **Sandboxer**
  - Constructs secure micro-VM images for each needed runtime.
- **Hasher & Signer**
  - Hashes all blobs, signs the manifest for audit/provenance.
- **Chunker/Index Agent**
  - Builds static trunk, offset tables, and "heap of heaps" structure.
- **Precompute Agent**
  - Optionally runs code to precompute cell outputs for instant preview.
- **Test Agent**
  - Dry-runs the built egg to guarantee hatch-ability.

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
- **egg_cli.py** – lightweight command wrapper exposing `build`, `hatch` and
  `verify` commands. The CLI parses the manifest file and invokes the prototype
  agents described above.

---

See [FORMAT.md](FORMAT.md) for the file structure agents produce.

