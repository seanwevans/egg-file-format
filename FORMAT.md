# FORMAT.md

## Egg File Format Specification (Draft)

The `.egg` file is a hierarchical, chunked container optimized for instant, breadth-first loading and maximal reproducibility.

### Top-Level Structure

- **Header/TOC** (Layer 1): Magic bytes, version, minimal manifest, offset tables for next layers.
- **Manifest** (Layer 2): Full document metadata, cell layout, references to code/data blocks, build provenance.
- **Notebook Content** (Layer 2): Markdown, code cells (in any language), outputs, static previews, table of contents.
- **Runtime Blocks/Assets** (Layer 3+): Interpreter blobs, rootfs images, large data files.
- **Heap(s)**: Dynamically sized regions for datasets, attachments, and outputs.

### Static Trunk

- Branching factor: 16 (configurable in future versions)
- Up to 3 levels of fixed-size tables for fast access to thousands of objects.

### Heap of Heaps

- Any static slot may point to a heap region (arbitrary size), which may itself be chunked/indexed recursively.
- All heavy assets are referenced by (offset, length, type) in parent tables.

### Example Layout

```
[Header/TOC][Static Table L1][Static Table L2][Manifest][Notebook][Block A][Block B]...[Heap1][Heap2]...
```

For a concrete starting template, see the sample manifest in
[`examples/manifest.yaml`](examples/manifest.yaml).

### Header Details

The header occupies the first 64 bytes of the file and contains information
required to locate the rest of the structures.  All integers are encoded as
little‑endian unsigned values.

- Bytes 0–3: ASCII magic ``"EGGF"`` identifying the file.
- Bytes 4–5: Major and minor version numbers.
- Bytes 6–7: Reserved for future use (must be zero).
- Bytes 8–15: Offset to the manifest table.
- Bytes 16–23: Offset to the notebook content block.
- Bytes 24–31: Offset to the first runtime/asset block.
- Bytes 32–63: Reserved for future metadata.

### Manifest Fields

The builder consumes a YAML manifest. The minimal fields are:

| Field       | Purpose                                              | Egg Layout Mapping                     |
|-------------|------------------------------------------------------|----------------------------------------|
| `name`      | Human-friendly title of the notebook.                | Stored in the header and manifest.     |
| `description` | Short description shown in UIs.                     | Stored in the manifest.                |
| `cells`     | Ordered list of notebook cells. Each entry provides   | Each cell becomes a notebook block in  |
|             | `language` and `source` path to the code.             | the Notebook section pointing to the   |
|             |                                                      | assembled code/data blobs.             |
| `author`    | Optional author or creator name.                      | Stored in the manifest.                |
| `created`   | Timestamp when the egg was built.                     | Stored in the manifest header.         |
| `license`   | SPDX license identifier for the notebook content.     | Stored in the manifest.                |
| `dependencies` | List of runtime block identifiers.                 | Guides the runtime block fetcher.      |
| `permissions` | Mapping of permission names to boolean values.      | Enforced by the sandboxer at hatch time. |

Dependency entries may be relative file paths or container image
specifications like ``python:3.11``. Paths are validated to exist on disk while
entries containing a colon are treated as remote container images.

During the build step the sources listed under `cells` are copied into
the `.egg` file and referenced by the manifest. Runtime blocks and other
assets appear in later layers but remain associated with their cells via
these manifest entries.

### Runtime Blocks Directory

Local dependency files resolved by the runtime block fetcher are included
in the archive under the `runtime/` directory using their original file
names. Container-style entries like `python:3.11` are recorded in the
manifest but are not bundled into the egg.

### Breadth-First Loading

- UI loads Layer 1 & 2 instantly (title, author, structure, text, previews).
- Layers 3+ are loaded on demand, in background, or as user navigates deeper.

### Hash Records

Every archive includes a ``hashes.yaml`` file listing the SHA256 digest of each
member as ``path: digest`` pairs.  The file itself is authenticated by
``hashes.sig`` which contains an HMAC-SHA256 signature.  Verifiers must check
both the signature and that the set of files in the archive exactly matches the
keys recorded in ``hashes.yaml``.

---

See [AGENTS.md](AGENTS.md) for agent/pipeline roles.

