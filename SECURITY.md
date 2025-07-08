# SECURITY.md

## Security Model for Egg File Format

Egg aims to make running notebook-style code safe and reproducible even when
content comes from untrusted parties. This document describes the main defense
mechanisms built into the format and CLI tools.

### Threat Model
- **Assume all input code/data is untrusted.**
- Files may be received from unknown sources and executed by high-value users.
- Malicious eggs may try to escape the sandbox, exfiltrate data, or consume
  excessive resources.
- Runtime blocks and dependencies might be tampered with or replaced.

### Sandboxing
- All runtime execution occurs in a micro-VM (e.g., Firecracker) isolated from
  the host OS.
- No direct access to the host filesystem, network, or devices unless explicitly
  permitted by the manifest.
- Each VM runs with strict CPU, RAM, disk, and time limits and uses an ephemeral
  root filesystem.
- During `egg hatch`, the sandboxer prepares a container image (or placeholder
  `microvm.conf` in this prototype) for every runtime.
- Firecracker requires a Linux host with KVM enabled and the `firecracker`
  binary installed. Non-Linux platforms automatically fall back to Docker
  containers for isolation.
- Passing `--no-sandbox` disables isolation and should only be used for testing
  trusted eggs.

### Integrity & Authenticity
- All blocks and assets are deterministically chunked, hashed, and optionally
  signed during `egg build`.
- The manifest stores a chain of hashes and signatures for auditability.
- Viewers verify the manifest and block hashes before executing any code.
- Runtimes fetched from registries are pinned to specific hashes or signatures.

### Permissions Model
- The egg manifest can specify per-block permissions: network access, file
  system paths, devices, etc.
- Default policy is deny-all; the user must opt in to any additional privileges.
- Hatchers warn users before activating non-default permissions.

### Update Policy
- Runtime blocks are verified before use and can be restricted to trusted
  sources only.
- Security updates are delivered via new runtime block versions and manifest
  signatures.

### Vulnerability Disclosure
- Please report vulnerabilities via a private issue or email
  [security@egg.software](mailto:security@egg.software).
- We will acknowledge your report within 48 hours and provide a plan for fixing
  the issue as soon as possible.

---

See [FORMAT.md](FORMAT.md) for file and block validation details.
