# Changelog

All notable changes to this project will be documented in this file.
This project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]
- Initial draft of the changelog.

## [0.1.0] - 2025-06-16
- Initial prototype with `egg build` and `egg hatch` commands.


## [0.2.0] - Unreleased
- Added hashing utilities and HMAC signing of `hashes.yaml`.
- New `egg verify` command to validate archives.
- Implemented chunking support for large files with validation.
- Introduced environment variable overrides for runtime commands.
- Added `info` subcommand for inspecting egg metadata.
- Allow configuring signing key via `EGG_SIGNING_KEY`.
- Improved manifest validation and relative path handling.
- Expanded documentation and file format specification.

---

### Updating this file

1. Add a new heading for each version in descending order (most recent first).
2. Summarize noteworthy features, fixes, and changes in bullet points.
3. Keep unreleased changes under an `Unreleased` section until a release is tagged.
4. Commit the updated CHANGELOG alongside code changes for that version.

