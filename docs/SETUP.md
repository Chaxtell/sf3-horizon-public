# SF3-Horizon: Windows setup

Environment reference only. No plan or next steps here: those are in `MASS_PORT_PLAN.md`.
Repository layout: `CLAUDE.md` section 1.

## Part 2: Setting Up Your Windows Development Environment

Horizon's upstream Python staging scripts (`native/tools/native.py` in `horizon-mods` and `tools/horizon.py` in `horizon-native-mod-template`) were written for Linux (`rsync`, `fcntl`, and LF line endings). If you or an AI agent naively port that script to Windows, you will hit **four major traps**. Here is how we solve all four right out of the gate.

### The 4 Windows Traps & How We Fix Them

1. **Trap 1: Cargo Recompiling from Scratch Every Time (`shutil` Timestamp Issue)**
   * **Why it happens:** Linux's `rsync` only copies files that actually changed, leaving timestamps on untouched files alone. A basic `shutil.copytree` in Python overwrites every file in the staging folder and updates all modification timestamps. When Cargo sees new timestamps on every file, it thinks you rewrote the entire engine and triggers a slow, full rebuild from scratch every single time you stage.
   * **The Fix:** Use Windows' built-in `robocopy /MIR` command via Python's `subprocess` instead of `shutil`. `robocopy /MIR` is the native Windows equivalent of `rsync`—it only copies changed files and preserves timestamps, keeping your Rust builds fast and incremental. *(Note: `robocopy` returns exit codes `0–7` for success, which your Python wrapper must treat as non-errors).*

2. **Trap 2: "Access Denied" Crashes While the Game is Open (`WinError 32` & `fcntl`)**
   * **Why it happens:** Linux lets scripts overwrite files even while another program has them open. Windows does not. If the Horizon game window is running while you stage an update, Windows blocks the script from overwriting the active `.hnmod` or compiled binary (`WinError 32`). Furthermore, Python's raw `msvcrt` locks specific byte ranges rather than whole files like Linux's `fcntl`, which gets finicky if a build crashes mid-run.
   * **The Fix:** Install the `filelock` Python package (`pip install filelock`) for clean cross-platform lockfiles, catch `PermissionError` (`WinError 32`) gracefully with a clear reminder to close the running Horizon game window before staging (you can leave the Horizon Launcher open as long as the game instance isn't actively locking the mod folder).

3. **Trap 3: Windows Line Endings (`CRLF`) Breaking `source_sha256` Hashes**
   * **Why it happens:** Windows defaults to `CRLF` (`\r\n`) line endings, while Linux uses `LF` (`\n`). Horizon's mixin system verifies `source_sha256` hashes on target engine files and parses manifest headers inside `.hnmod` bundles. Windows `CRLF` line endings will cause `source_sha256` mismatches and silent parsing failures.
   * **The Fix:** Force `encoding="utf-8"` and `newline="\n"` on all file writes in Python, configure Git to never convert line endings to `CRLF`, and drop a `.gitattributes` file in the root of your repo containing `* text=auto eol=lf`.

4. **Trap 4: Git Conflicts When Horizon Updates**
   * **Why it happens:** If Claude edits `native.py` or `horizon.py` directly, Git will complain about local changes the next time you run `git pull` on the upstream Horizon repositories.
   * **The Fix:** Have Claude create a separate copy called `native_win.py` (and `horizon_win.py`) instead of modifying the original script.

---

### 1. Required Tools & Initial Git Line-Ending Setup

Install these on your Windows machine:

* **Rust Toolchain:** Latest stable Rust (`1.90+` / `1.95.0` via `rustup`).
* **Python 3.12+ & `filelock`:**
  ```powershell
  pip install filelock
  ```
* **JDK 25 & Official Minecraft 26.3 Install:** Required once so `horizon-prepare` can extract vanilla 26.3 assets and server data from your legally owned copy of Minecraft.
* **`cargo-horizon-mod` CLI:** Horizon's official tool for scaffolding, building, and checking `.hmod` content mods:
  ```powershell
  cargo install --git https://github.com/horizon-rust/horizon cargo-horizon-mod
  ```
* **Lock Git to `LF` Line Endings Before Cloning:** Run this once in PowerShell or Git Bash before cloning the Horizon repos so `source_sha256` hashes never break on Windows:
  ```powershell
  git config --global core.autocrlf input
  git config --global core.eol lf
  ```

### 2. Clone the Three Official Reference Repos

Create a parent folder called `horizon-workspace/` and clone Horizon's core repositories side-by-side so both you and Claude Code can inspect their exact source files and hook points:

```powershell
mkdir horizon-workspace
cd horizon-workspace

# 1. The Horizon engine source (contains native-hooks.json, CLAUDE.md, and AGENTS.md)
git clone https://github.com/horizon-rust/horizon.git

# 2. Official Horizon mods & native build tools (contains native/tools/native.py)
git clone https://github.com/horizon-rust/horizon-mods.git

# 3. The official template for horizon-mixins native mods (based on levzzz5154's Veinminer port)
git clone https://github.com/horizon-rust/horizon-native-mod-template.git
```

### 3. `native_win.py`

`tools/native_win.py` already exists in this repository (robocopy `/MIR`, `filelock`, the `WinError 32` reminder, UTF-8 with LF). The upstream `native.py` stays untouched.

---

## Part 3: Fast Iteration Tricks in Horizon Launcher

Even with `robocopy /MIR` preserving timestamps, you can combine three built-in Horizon features to make your daily coding loop near-instant:

1. **Enable the `dev` Native Profile in Horizon Launcher:**
   Run this command once before working on `.hnmod` mods:
   ```powershell
   horizon-launcher settings native-profile dev
   ```
   This compiles your native mod instance unoptimized, making incremental Rust rebuilds **6 times faster** when you run (with the game window closed):
   ```powershell
   horizon-launcher native-build D:\claudeprojects\horizon-workspace\sf3-horizon\native\01_sf3_skyblock\mixins\sf3_skyblock --trust-native-code
   ```

2. **Use `--dev-mod` for `.hmod` Content Changes:**
   In the Horizon Launcher settings under **Game arguments**, add:
   ```text
   --dev-mod "D:\claudeprojects\horizon-workspace\sf3-horizon\content\sf3_content"
   ```
   Now you do not even need to package `.hmod` files while tweaking textures, block hardness, or recipes. Restart the client and your changes load immediately.

3. **Reuse a Cached Cargo Target Directory:**
   When running `py tools/native_win.py check all` (or `stage` / `build` / `--target-dir`), `tools/native_win.py` defaults to `--target-dir D:\claudeprojects\horizon-workspace\sf3-horizon\native\target\cargo` so Cargo reuses compiled Horizon dependencies across every `.hnmod` bundle.
