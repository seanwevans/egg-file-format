# SECURITY.md

## Security Model for Egg File Format

### Threat Model
- **Assume all input code/data is untrusted.**
- Files may be received from unknown sources and executed by high-value users.

### Sandboxing
- All runtime execution occurs in a micro-VM (e.g., Firecracker), isolated from host OS.
- No direct access to host filesystem, network, or devices unless explicitly permitted by manifest.
- Each VM has strict resource quotas (CPU, RAM, disk, time limits).

### Integrity & Authenticity
- All runtime blocks and assets are hashed and (optionally) signed at build time.
- Manifest includes signature chain for audit/reproducibility.
- Viewer verifies hashes/signatures before executing any code.

### Permissions Model
- Egg manifest can specify per-block or per-cell permissions (network, FS, device, etc).
- Default: deny all except explicit grants.
- User is warned before any non-default permission is activated at hatch time.

### Update Policy
- Runtime blocks from registries are verified via pinned hashes or signatures before use.
- Option to allow only blocks from trusted, whitelisted sources.

### Vulnerability Disclosure
- Please report vulnerabilities by opening an issue or emailing security@egg.software.

---

See [FORMAT.md](FORMAT.md) for file and block validation details.

