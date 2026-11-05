# -*- coding: utf-8 -*-
r"""
pokopia_deck_updater.py  —  version 0.4.0

Builds a package with ONLY the files of the Pokopia port (featureJosh/pokopia-recomp) that changed,
so you can send it to your Steam Deck (for example with LocalSend) without ever including your protected files.

The first time, a window asks for your port folder on this PC, and the script remembers it in config.json,
next to this script. Packages are built in the "packages" folder, also next to this script.

To know what the Deck has, it uses an INVENTORY (deck_inventory.json, next to this script):
the size, date and hash of every file on the Deck.
If there is no inventory yet, it asks for the PC copy of the Deck's port folder and builds it once.

Before running it (on the PC):
  1. Copy the new release OVER your install, choosing "Replace".
  2. Open the launcher. If it asks for Set up, let it finish.
  3. Press Play once. If there were missing shaders, close it and press Play again.
  4. Double-click "Update_Pokopia.bat".
"""

import hashlib                  # to compute the "hash" (fingerprint) of a file
import json                     # to save and read the inventory and the settings
import os                       # to rename files and open the package folder at the end
import shutil                   # to copy and delete folders
import subprocess               # to run the same Set up check the launcher uses
import sys                      # to end the program with a message
import time                     # to measure how long the program takes
from datetime import datetime   # to put the date and time in the package folder name
from fnmatch import fnmatch     # to match names with wildcards, like "pkp.log*"
from pathlib import Path        # to work with folder paths comfortably

VERSION = "0.4.0"   # bump it in every new version (and add it to CHANGELOG.md)

# ============================================================
# 1) FOLDERS AND FILES
# ============================================================

# The folder this script is in, wherever that is on each computer.
SCRIPT_DIR = Path(__file__).resolve().parent

# Remembers the port folder you chose the first time.
CONFIG_FILE = SCRIPT_DIR / "config.json"

# Where the package you send to the Deck is built (only the newest one is kept).
PACKAGES_DIR = SCRIPT_DIR / "packages"

# The inventory of what the Deck has.
INVENTORY_FILE = SCRIPT_DIR / "deck_inventory.json"

# The inventory's name up to version 0.3.1. If it exists, it is renamed once (see migrate_old_inventory).
OLD_INVENTORY_FILE = SCRIPT_DIR / "inventario_deck.json"

# Your working install (where you run Set up). Filled in at startup, from config.json or from the window.
PORT_DIR = None

# When the process starts (after the folders are chosen). Used by the timer at the end.
START_TIME = None

# ============================================================
# 2) WHAT IS NEVER SENT
# ============================================================

# Names in the root of the port folder (upper or lower case doesn't matter).
PROTECTED = {
    "game",                # the game dump
    "save",                # the Deck's save
    "pkp.ini",             # the Deck's copy has relative paths and its own options (submit_thread)
    "controls.ini",        # the Deck's own settings
    "nup_dump",            # unpacked copy of the game, if a .nup was used
    "pipeline_cache.bin",  # depends on the graphics card: the PC is NVIDIA, the Deck is AMD
    "pipeline_keys.bin",   # the Deck's copy is kept as a precaution
}

# Things in the root that the Deck doesn't need.
SKIP_IN_ROOT = {
    "build",               # Set up's workshop; the game runs from pkp.exe
    "pokopialauncher.exe", # the launcher doesn't work on the Deck
}
SKIP_ROOT_PATTERNS = ["changelog*", "readme*", "license", "license.*", "pkp_freeze*"]   # careful: the "licenses" folder IS sent

# Files skipped wherever they are (logs and temporary files).
SKIP_ANYWHERE = ["pkp.log*", "*.prev", "*.tmp"]

# ============================================================
# 3) HELPER FUNCTIONS
# ============================================================

def file_hash(path: Path) -> str:
    """Reads the file in chunks and returns its SHA-256 hash. If a single bit changes, the whole hash changes."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):   # 1 MB chunks so memory doesn't fill up
            h.update(chunk)
    return h.hexdigest()


def inventory_key(relative: Path) -> str:
    """The path as text, with "/" and in lower case, so the inventory doesn't depend on how Windows writes it."""
    return relative.as_posix().lower()


def is_shader(relative: Path) -> bool:
    """Is it a file in shader_cache\\spirv? Those are compared by size and date (Set up generates them)."""
    parts = [p.lower() for p in relative.parts]
    return len(parts) > 2 and parts[0] == "shader_cache" and parts[1] == "spirv"


def is_skipped(relative: Path) -> bool:
    """Is this path left out of the package (and of the inventory)?"""
    parts = [p.lower() for p in relative.parts]
    root, name = parts[0], parts[-1]

    if root in PROTECTED or root in SKIP_IN_ROOT:
        return True
    if any(fnmatch(root, pattern) for pattern in SKIP_ROOT_PATTERNS):
        return True
    if any(fnmatch(name, pattern) for pattern in SKIP_ANYWHERE):
        return True
    if root == "shader_cache" and len(parts) > 2 and parts[1] != "spirv":
        return True        # missing, runtime, corpus...: each machine keeps its own
    return False


def port_files(folder: Path):
    """Every file in the folder that counts for the package."""
    for path in folder.rglob("*"):
        if path.is_file():
            relative = path.relative_to(folder)
            if not is_skipped(relative):
                yield relative


def human_size(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def ask_yes_no(text: str) -> bool:
    return input(text + " (y/n): ").strip().lower() in ("y", "yes")


def quit_with(message: str):
    print("\n" + message)
    sys.exit(1)

# ============================================================
# 4) FOLDERS: SETTINGS AND THE WINDOW TO CHOOSE THEM
# ============================================================

def read_config() -> dict:
    """Reads config.json. If it doesn't exist or is damaged, returns empty settings (and you're asked again)."""
    if CONFIG_FILE.is_file():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            print("config.json could not be read. You'll be asked for the folder again.")
    return {}


def save_config(config: dict):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def pick_folder(title: str):
    """Opens a window to choose a folder. If the window can't open, asks you to paste the path in the console.
    Returns the chosen folder, or None if you cancelled."""
    try:
        import tkinter                          # the window toolkit that comes with Python
        from tkinter import filedialog
        window = tkinter.Tk()
        window.withdraw()                       # hide the empty main window: we only want the folder picker
        window.attributes("-topmost", True)     # make the picker appear in front of the console
        path = filedialog.askdirectory(parent=window, title=title, mustexist=True)
        window.destroy()
    except Exception:
        print(f"\n{title}")
        path = input("Paste the folder path and press Enter: ").strip().strip('"')   # "Copy as path" adds quotes
    return Path(path) if path else None


def has_pkp_exe(folder: Path) -> bool:
    """Does the folder have pkp.exe? Only a folder where Set up was run has it."""
    return (folder / "pkp.exe").is_file()


def ask_port_folder() -> Path:
    """Asks for the port folder until you choose one with pkp.exe."""
    print("\nChoose your Pokopia install folder on this PC: the one where you ran Set up and press Play.")
    while True:
        folder = pick_folder("Select your Pokopia install folder (where you ran Set up)")
        if folder is None:
            quit_with("No folder selected. Nothing was done.")
        if has_pkp_exe(folder):
            return folder
        print(f"\n{folder} has no pkp.exe. Choose your install folder. "
              "If it is the right one, run Set up in the launcher first.")


def ask_mirror_folder() -> Path:
    """Only the first time, when there is no inventory: asks for the PC copy of the Deck's port folder."""
    print("\nFirst run: there is no inventory of your Deck yet.")
    print("Choose the copy on this PC of your Deck's port folder. It is read once (~25 GB) to build the inventory.")
    while True:
        folder = pick_folder("Select the PC copy of your Steam Deck's port folder")
        if folder is None:
            quit_with("No folder selected. Nothing was done.")
        if folder.resolve() == PORT_DIR.resolve():
            print("\nThat is your PC install, not the copy of the Deck. Choose the copy of the Deck.")
        elif not has_pkp_exe(folder):
            print(f"\n{folder} doesn't look like a copy of the port (no pkp.exe). Try again.")
        else:
            return folder

# ============================================================
# 5) THE INVENTORY
# ============================================================

def migrate_old_inventory():
    """Up to 0.3.1 the inventory was called inventario_deck.json. Renames it (and its backup) once."""
    if INVENTORY_FILE.exists() or not OLD_INVENTORY_FILE.exists():
        return
    os.replace(OLD_INVENTORY_FILE, INVENTORY_FILE)
    old_backup = OLD_INVENTORY_FILE.with_suffix(".json.bak")
    if old_backup.exists():
        os.replace(old_backup, INVENTORY_FILE.with_suffix(".json.bak"))
    print("Renamed inventario_deck.json to deck_inventory.json.")


def read_inventory() -> dict:
    with open(INVENTORY_FILE, "r", encoding="utf-8") as f:
        inv = json.load(f)
    if "archivos" in inv:     # format up to 0.3.1 (Spanish field names): convert it to the new one
        inv = {"version": 2,
               "files": {k: {"size": v["tam"], "mtime": v["fecha"], "sha256": v["huella"]}
                         for k, v in inv["archivos"].items()}}
    return inv


def save_inventory(inv: dict):
    """Writes to a temporary file first and then renames it: if something fails halfway, the previous one is still fine."""
    tmp = INVENTORY_FILE.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(inv, f, ensure_ascii=False, indent=0)
    if INVENTORY_FILE.exists():
        shutil.copy2(INVENTORY_FILE, INVENTORY_FILE.with_suffix(".json.bak"))   # backup of the previous one
    os.replace(tmp, INVENTORY_FILE)


def build_inventory(mirror: Path):
    """Reads the copy of the Deck once and records the size, date and hash of every file."""
    print(f"      First run: building the inventory from {mirror}.")
    print("      This reads the whole folder (~25 GB) only once. It may take a while.\n")
    inv = {"version": 2, "files": {}}
    for i, r in enumerate(port_files(mirror), 1):
        path = mirror / r
        st = path.stat()
        inv["files"][inventory_key(r)] = {"size": st.st_size, "mtime": st.st_mtime, "sha256": file_hash(path)}
        if i % 5000 == 0:
            print(f"      ...{i} files recorded")
    save_inventory(inv)
    print(f"      Inventory ready: {len(inv['files'])} files.\n")
    return inv


def has_changed(relative: Path, inv: dict) -> bool:
    """Is this PC file different from what the Deck has, according to the inventory?"""
    path = PORT_DIR / relative
    st = path.stat()
    entry = inv["files"].get(inventory_key(relative))
    if entry is None:
        return True                                    # the Deck doesn't have it
    if st.st_size != entry["size"]:
        return True                                    # different size: it surely changed
    if is_shader(relative) and abs(st.st_mtime - entry["mtime"]) <= 2:
        return False                                   # shader with the same size and date: unchanged
    if file_hash(path) != entry["sha256"]:             # port files: always by hash
        return True
    entry["mtime"] = st.st_mtime                       # same content: record the new date so next time is fast
    return False

# ============================================================
# 6) SET UP CHECK
# ============================================================

def check_setup() -> list:
    """Warnings if Set up looks incomplete or doesn't match this port version."""
    warnings = []
    if not (PORT_DIR / "shader_cache" / "spirv" / "results.tsv").is_file():
        warnings.append("The shader cache is not complete: let Set up finish.")

    # The same check the launcher runs to decide whether to ask for Set up (pkp_build.py --check).
    python = PORT_DIR / "tools" / "python" / "python.exe"
    checker = PORT_DIR / "tools" / "build" / "pkp_build.py"
    if python.is_file() and checker.is_file():
        try:
            r = subprocess.run([str(python), "-I", str(checker), "--check", "--game", str(PORT_DIR)],
                               capture_output=True, timeout=300)
            if r.returncode != 0:
                warnings.append("pkp.exe doesn't match this port version: the launcher would ask for Set up. "
                                "Run it before sending anything (pkp.exe and pkp_rt.dll go together).")
        except Exception as e:
            warnings.append(f"Couldn't run the Set up check ({e}). Open the launcher to confirm.")
    else:
        warnings.append("Couldn't find the launcher's check tool. Open the launcher to confirm.")
    return warnings

# ============================================================
# 7) MAIN PROGRAM
# ============================================================

def main():
    global PORT_DIR, START_TIME      # they live outside main(); with "global", main() can change them for the whole program

    print("=" * 60)
    print(f"  Pokopia Deck Updater  (v{VERSION})")
    print("=" * 60)
    print("Reminder: if the launcher asked for Set up, finish it and start the game twice before running this.\n")

    # Port folder: the one saved in config.json or, if there is none (or it no longer has pkp.exe), the one you choose
    config = read_config()
    saved = config.get("port_folder")
    if saved and has_pkp_exe(Path(saved)):
        PORT_DIR = Path(saved)
    else:
        if saved:
            print(f"The saved port folder is missing or has no pkp.exe: {saved}")
        PORT_DIR = ask_port_folder()

    if SCRIPT_DIR == PORT_DIR.resolve() or PORT_DIR.resolve() in SCRIPT_DIR.parents:
        quit_with("This script is inside the port folder. Move it (with its files) to another folder and run it again.")

    if config.get("port_folder") != str(PORT_DIR):
        config["port_folder"] = str(PORT_DIR)
        save_config(config)

    print(f"Port folder:     {PORT_DIR}")
    print(f"Packages folder: {PACKAGES_DIR}")
    print("(To choose another port folder, delete config.json next to this script.)")

    migrate_old_inventory()
    mirror = None
    if not INVENTORY_FILE.is_file():
        mirror = ask_mirror_folder()     # asked here, at the start, so the long process isn't interrupted

    START_TIME = time.monotonic()        # the timer starts here: the folders are already chosen

    # Step 1: Set up
    print("\n[1/4] Checking Set up...")
    warnings = check_setup()
    if not warnings:
        print("      ok")
    for warning in warnings:
        print("      WARNING:", warning)
    if warnings and not ask_yes_no("\n      There are warnings. Continue anyway?"):
        quit_with("Cancelled. Nothing was done.")

    # Step 2: the Deck's inventory
    print("\n[2/4] Reading the Deck's inventory...")
    inv = read_inventory() if mirror is None else build_inventory(mirror)
    print(f"      The Deck has {len(inv['files'])} files recorded.")

    # Step 3: compare
    print("\n[3/4] Comparing with the PC...")
    changes = []
    for i, r in enumerate(port_files(PORT_DIR), 1):
        if has_changed(r, inv):
            changes.append(r)
        if i % 5000 == 0:
            print(f"      ...{i} files checked")
    save_inventory(inv)        # saves the updated dates of unchanged files (doesn't change what the Deck has)

    if not changes:
        quit_with("      The Deck is up to date. Nothing to send.")

    changes.sort()
    total = sum((PORT_DIR / r).stat().st_size for r in changes)
    print(f"      Files that changed: {len(changes)} ({human_size(total)})")
    for r in changes[:25]:
        print("        ", r)
    if len(changes) > 25:
        print(f"         ... and {len(changes) - 25} more")
    print("      Never included:", ", ".join(sorted(PROTECTED)))

    # Step 4: build the package
    if not ask_yes_no("\n[4/4] Build the package?"):
        quit_with("Cancelled. Nothing was copied.")

    PACKAGES_DIR.mkdir(parents=True, exist_ok=True)
    for old in PACKAGES_DIR.glob("package_*"):        # deletes only the previous packages this script built
        if old.is_dir():
            shutil.rmtree(old)

    package = PACKAGES_DIR / datetime.now().strftime("package_%Y-%m-%d_%H-%M")
    for i, r in enumerate(changes, 1):
        target = package / r
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(PORT_DIR / r, target)
        st = (PORT_DIR / r).stat()
        inv["files"][inventory_key(r)] = {"size": st.st_size, "mtime": st.st_mtime, "sha256": file_hash(target)}
        if i % 500 == 0:
            print(f"      [{i}/{len(changes)}]")
    save_inventory(inv)        # now the inventory counts these files as already sent

    print("\nDone. Package built in:")
    print("  ", package)
    print("\nOn the Deck:")
    print("  1. Back up the save folder.")
    print("  2. Receive the package (for example with LocalSend).")
    print("  3. Copy its CONTENTS into the port folder on your Deck and choose 'Overwrite all'.")

    if hasattr(os, "startfile"):
        os.startfile(package)       # opens the folder in Explorer so you can drag it to LocalSend


if __name__ == "__main__":
    try:
        main()                                # the whole program
    finally:                                  # this always runs, however the program ends
        if START_TIME is not None:            # if you cancelled while choosing folders, there is no time to show
            seconds = int(time.monotonic() - START_TIME)
            print(f"\nTotal time: {seconds // 60} min {seconds % 60:02d} s")
