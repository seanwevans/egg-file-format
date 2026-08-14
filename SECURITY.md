# SECURITY.md

## Security Model for Egg File Format

Egg aims to make running notebook-style code safe and reproducible even when
content comes from untrusted parties. This document describes the main defense
mechanisms built into the format and CLI tools.

> ## ⚠️ Implementation status
>
> **The sandbox described below is not implemented. Do not hatch untrusted
> eggs.**
>
> `egg hatch` currently executes every cell as a normal subprocess on the host,
> with the caller's full privileges and no resource limits. The sandboxer
> writes placeholder image files — an empty `vmlinux`, a zeroed `rootfs.ext4`,
> and a `microvm.json` describing them — but nothing boots them:
> `launch_microvm` and `launch_container` exist and are never called from any
> code path. `--precompute` runs cells the same way at build time.
>
> Sections marked **Planned** describe the intended design, not current
> behavior. Sections marked **Implemented** describe what the code does today.

### Threat Model
- **Assume all input code/data is untrusted.**
- Files may be received from unknown sources and executed by high-value users.
- Malicious eggs may try to escape the sandbox, exfiltrate data, or consume
  excessive resources.
- Runtime blocks and dependencies might be tampered with or replaced.

### Sandboxing — **Planned**

Intended design:

- All runtime execution occurs in a micro-VM (e.g., Firecracker) isolated from
  the host OS.
- No direct access to the host filesystem, network, or devices unless explicitly
  permitted by the manifest.
- Each VM runs with strict CPU, RAM, disk, and time limits and uses an ephemeral
  root filesystem.
- Firecracker requires a Linux host with KVM enabled and the `firecracker`
  binary installed. Non-Linux platforms fall back to containers.

What happens today:

- During `egg hatch`, the sandboxer writes placeholder image files per runtime
  language — on Linux a `microvm.json`, an empty `vmlinux`, and a zeroed 1 MiB
  `rootfs.ext4`; elsewhere a `container.json`. These are scaffolding for the
  design above and provide no isolation.
- Cells then run via `subprocess.run` on the host, inheriting the caller's
  privileges, environment, filesystem, and network access.
- `--no-sandbox` currently only suppresses placeholder-image creation and logs
  a warning. It does not change how cells execute, because nothing is being
  disabled.
- There are no CPU, memory, disk, or wall-clock limits. `--precompute-timeout`
  bounds build-time cells only; `hatch` has no timeout.

### Integrity & Authenticity — **Partly implemented**

Implemented:

- Every archive member is SHA-256 hashed into `hashes.yaml`, which is signed
  with Ed25519 during `egg build`.
- `build`, `hatch`, `verify`, and `info` all verify the signature and every
  member digest before doing anything else, and reject archives containing
  members not listed in `hashes.yaml`, duplicate member names, or names that
  are absolute or contain `..`.
- Archives are written with fixed ZIP timestamps and sorted entries, so
  repeated builds of identical inputs are byte-identical.

Not yet implemented:

- **Deterministic chunking.** `egg/chunker.py` exists but is not part of the
  build pipeline; assets are hashed whole, not per chunk.
- **Hash chains.** The manifest records no chain of hashes or signatures; the
  flat `hashes.yaml` mapping is the only integrity record.
- **Registry pinning.** `_download_container` accepts an expected SHA-256
  digest, but `fetch_runtime_blocks` never supplies one, so images pulled via
  `EGG_REGISTRY_URL` are used unverified. The registry URL is also not
  restricted to `https`.

### Permissions Model — **Planned**

Intended design:

- The egg manifest can specify per-block permissions: network access, file
  system paths, devices, etc.
- Default policy is deny-all; the user must opt in to any additional privileges.
- Hatchers warn users before activating non-default permissions.

What happens today: the `permissions` mapping is validated when the manifest is
loaded and printed by `egg info`. Nothing reads it at hatch time, so setting
`network: false` does not restrict anything.

### Update Policy — **Planned**
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
