# Pokopia Deck Updater

Builds an update package with **only the files that changed** in your PC install of the [Pokopia Recomp](https://github.com/featureJosh/pokopia-recomp) port, so you can send it to a Steam Deck without copying ~25 GB every time and without overwriting the Deck's save or settings.

> **Read this first**
> - This tool does **not** include or download any game files, keys or firmware. To use the port at all you need your own extracted copy of the game, version 2.0.1a.
> - Not affiliated with Nintendo, The Pokémon Company, Koei Tecmo, or the authors of the port.
> - Early version (0.x), built for one specific setup. Read [Limitations](#limitations) before using it.
> - The program's messages are in Spanish for now. An English option is planned.

Versión en español: [README.es.md](README.es.md)

## The problem

The port has to be set up on a Windows PC, and playing it on a Steam Deck (through Proton) has a catch:

- The launcher (`PokopiaLauncher.exe`) needs WebView2, which Proton doesn't include, so it doesn't run on the Deck.
- That means **Set up** (compiles the game from your dump and builds the shader cache, 1–2 hours) can only run on a Windows PC.
- After every new port version you have to move files from the PC to the Deck by hand, with two risks:
  1. Overwriting files that must stay different on the Deck (save, settings, GPU cache).
  2. Sending files that only work as a pair (a new `pkp_rt.dll` with an old `pkp.exe`).
- Copying everything means moving ~25 GB, almost all of it shader cache that didn't change.

This tool compares the PC install with what the Deck has and builds a package with only what is missing or changed, and it never includes the protected files.

## What it does

1. **Checks Set up.** Warns if `pkp.exe` is missing, if the shader cache is incomplete (`shader_cache/spirv/results.tsv`), or if `pkp.exe` doesn't match the port version. For the last check it runs the same check the launcher uses: `tools/build/pkp_build.py --check`. If there are warnings, it asks before continuing.
2. **Reads the inventory.** `inventario_deck.json` lists the size, date and SHA-256 hash of every file the Deck has. The first time, it is built from a PC copy of the Deck's folder.
3. **Compares** every file in the PC install with the inventory and lists what changed and how much it weighs.
4. **Builds the package** (after you confirm). Deletes the previous package, copies the changes into a dated folder, updates the inventory and opens the folder in Explorer.

### Never sent (protected)

| File / folder | Why |
|---|---|
| `game\` | The game dump; the Deck already has it. |
| `save\` | The Deck's save is the one that matters. |
| `pkp.ini` | The Deck's copy uses relative paths and its own options; the PC's has absolute Windows paths. |
| `controls.ini` | The Deck's own settings. |
| `nup_dump\` | Unpacked game copy, if a `.nup` was used. |
| `pipeline_cache.bin` | GPU-specific (e.g. NVIDIA on the PC, AMD on the Deck). |
| `pipeline_keys.bin` | The Deck's copy is kept as a precaution. |

### Also skipped (the Deck doesn't need it)

- `build\`, `pkp_freeze*`, `PokopiaLauncher.exe`.
- `CHANGELOG*`, `README*`, `LICENSE` in the root folder (the `licenses\` folder **is** sent).
- Logs and temporary files anywhere: `pkp.log*`, `*.prev`, `*.tmp`.
- `shader_cache` subfolders other than `spirv` (`missing`, `runtime`, `corpus`): each machine keeps its own.

### How it decides a file changed

- Not in the inventory → the Deck doesn't have it → sent.
- Different size → sent.
- Port files (everything outside `shader_cache\spirv`, under 1 GB in total): always compared by SHA-256 hash, so even a one-line change is detected.
- Shaders in `shader_cache\spirv` (~99,000 files, ~25 GB): same size and date means unchanged; if the date differs, they are compared by hash. Set up gives a file a new date whenever it rewrites it.

## Requirements

- Windows PC (tested on Windows 10) with the port installed and Set up completed.
- Python 3 with the `py` launcher (tested with Python 3.13). No extra packages needed.
- Steam Deck running the port through Proton (tested on a Steam Deck LCD with Proton Experimental).
- A way to send a folder to the Deck (tested with [LocalSend](https://localsend.org)).
- **First run only:** a copy on the PC of what the Deck currently has. It is read once to build the inventory and can be deleted afterwards.

## Setup

1. Put `actualizar_pokopia.py` and `Actualizar Pokopia.bat` in the same folder.
2. Open `actualizar_pokopia.py` in a text editor and change the three folders at the top:
   - `ORIGEN`: your PC install, where you run Set up and press Play.
   - `ENVIO`: where the package is built. It must not be inside `ORIGEN`.
   - `ESPEJO_INICIAL`: the PC copy of the Deck's folder (first run only).

The inventory (`inventario_deck.json`) is saved next to the script. If you move the script, move the inventory with it.

## Usage

On the PC:

1. Copy the new port version **over** your PC install, choosing "Replace" (this keeps `build\` and the shader cache).
2. Open the launcher. If it asks for Set up, let it finish.
3. Press Play once. If there were missing shaders, close it and press Play again (the second launch translates them).
4. Double-click `Actualizar Pokopia.bat`.

On the Deck:

5. Back up the `save` folder, receive the package (for example with LocalSend) and copy its **contents** into the port's folder, choosing "Overwrite all".

Two rules learned along the way:

- `pkp.exe` and `pkp_rt.dll` go together: never send the runtime of one version without its matching `pkp.exe`.
- Some versions need Set up again and others don't. The reliable way to know is to open the launcher.

## Real results

My first real run (November 5, 2026):

| | Time | Result |
|---|---|---|
| First run (build inventory + compare) | ~40 min | 107,323 files in the inventory; ~105,000 files checked on the PC |
| Second run (inventory already built) | ~1 min | 2 changed files (388.5 MB) |

## Limitations

- The folder paths are fixed in the code: right now it is tailored to one user.
- The inventory assumes every package you build gets sent to the Deck. If you build one and don't send it, restore `inventario_deck.json.bak`.
- If you change files on the Deck by hand, the inventory doesn't know.
- It doesn't delete files on the Deck that a new port version removed.
- Copying the package into place on the Deck is still manual.
- Only tested with the [featureJosh/pokopia-recomp](https://github.com/featureJosh/pokopia-recomp) fork.

## Ideas for future versions

- Ask for the folders on first run and remember them.
- English interface.
- Back up `save` automatically.
- A script on the Deck side to apply the package or rebuild the inventory.
- Send over the network directly, without LocalSend.
- Warn when a package has `pkp_rt.dll` without `pkp.exe`, or the other way around.

## Made with AI

I'm not a programmer; this is a learning project. I brought the problem, the hypotheses and the decisions, and Claude (Anthropic) wrote the code with me. I tested it on my own PC and Steam Deck.

## License

[MIT](LICENSE). The script contains no code from the port.
