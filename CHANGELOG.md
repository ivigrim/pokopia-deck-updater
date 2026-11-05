# Changelog

All notable changes to this project are listed here.
Versions follow [Semantic Versioning](https://semver.org): 0.x means the tool is still early and may change in incompatible ways.

Versions before 0.3.1 were never published. Their old internal names (v1, v1.1, v2, v3) are noted in parentheses.

## [0.3.1] - 2026-11-05

First public release.

### Fixed
- `pkp_freeze.txt` was being included in the package. The exclusion now uses the pattern `pkp_freeze*`.

### Added
- The version number is shown when the program starts.

## [0.3.0] - 2026-11-05 (internal v3)

### Changed
- An inventory file (`inventario_deck.json`) replaces the ~25 GB mirror of the Deck's folder. The mirror is only read once, to build the inventory.
- Files are compared automatically: port files always by SHA-256 hash, shaders by size and date (hash only if the date differs). No switches.
- Previous packages are deleted, so only the newest one is kept.
- `spirv.preload.pack` and `spirv.preload.pack.new` are included when they change.

### Added
- `Actualizar Pokopia.bat` to run the tool with a double click.
- A backup of the inventory (`inventario_deck.json.bak`) every time it is saved.

### Removed
- Mode 2 (merging a manual package into the mirror).

## [0.2.0] - 2026-11-05 (internal v2)

### Changed
- The source folder is the working install (where Set up runs), not the unzipped release.

### Added
- More exclusions: GPU cache, logs, `build\`, launcher, readme and license files.
- A Set up check before comparing, using the launcher's own check (`pkp_build.py --check`).
- Mode 2, to merge a manual package into the mirror.

## [0.1.1] - 2026-11-05 (internal v1.1)

### Added
- A send folder for LocalSend, compared against a mirror of the Deck on the PC.

## [0.1.0] - 2026-11-05 (internal v1)

### Added
- Folder-to-folder copy from the PC to the Deck, with a dry run first. Dropped because the Deck can't be connected to the PC as a drive.
