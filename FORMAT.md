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

### Breadth-First Loading

- UI loads Layer 1 & 2 instantly (title, author, structure, text, previews).
- Layers 3+ are loaded on demand, in background, or as user navigates deeper.

---

See [AGENTS.md](AGENTS.md) for agent/pipeline roles.

