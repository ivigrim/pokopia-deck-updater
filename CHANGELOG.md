# Changelog

All notable changes to this project are listed here.
Versions follow [Semantic Versioning](https://semver.org): 0.x means the tool is still early and may change in incompatible ways.

Versions before 0.3.1 were never published. Their old internal names (v1, v1.1, v2, v3) are noted in parentheses.

## [0.4.0] - 2026-11-05

### Added
- On the first run, a window asks for your port folder and the tool remembers it in `config.json`. You no longer edit the code. If the saved folder no longer has `pkp.exe`, it asks again.
- If there is no inventory yet, a window asks for the PC copy of the Deck's folder.
- If the window can't open, the tool asks you to paste the folder path in the console.
- The total time is shown at the end, counted from when the folders are chosen.
- The tool stops if it is inside the port folder (it would send its own files to the Deck).

### Changed
- The program is now in English only: messages, file names and code.
- Files renamed: `actualizar_pokopia.py` → `pokopia_deck_updater.py`, `Actualizar Pokopia.bat` → `Update_Pokopia.bat`, `inventario_deck.json` → `deck_inventory.json`. An existing inventory (and its backup) is renamed and converted automatically the first time, so it doesn't have to be built again.
- Packages are built in a `packages` folder next to the tool, named `package_<date>`.
- Questions are answered with `y` or `n`.
- The port folder must have `pkp.exe` (a folder where Set up was run). An unzipped release is rejected.
- The instructions shown at the end no longer assume a folder name or a file manager on the Deck.

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
