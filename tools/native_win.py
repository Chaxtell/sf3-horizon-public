#!/usr/bin/env python3
"""Windows staging & build runner for sf3-horizon native mods (native/<dir>/).

Adapted from horizon-mods/native/tools/native_win.py for the sf3-horizon repository layout:
    py tools/native_win.py sync                          # verify/sync compatibility.lock.json -> native/*/
    py tools/native_win.py check 01_sf3_skyblock         # apply on pinned Horizon, cargo check the game
    py tools/native_win.py check all                     # apply all 6 SF3 native mods together and check
    py tools/native_win.py build all                     # build custom Horizon client + horizon-ctl (fast profile)
    py tools/native_win.py package all                   # build deterministic native/target/<id>-<version>.hnmod
    py tools/native_win.py proof --resources PATH all    # build, then drive the game with horizon-ctl

Windows-specific guarantees:
  * staging mirrors with robocopy /MIR; unchanged files keep their timestamps so cargo only recompiles deltas;
  * single-instance execution per native/target/ via filelock (or msvcrt fallback);
  * WinError 32/33 detection when Horizon is still running;
  * all text files read and written as UTF-8 with LF (\\n) line endings;
  * exports from local ../horizon checkout via `git archive` when available before falling back to GitHub.
"""
import argparse
import filecmp
import hashlib
import io
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import time
import tomllib
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NATIVE = ROOT / "native" if (ROOT / "native").is_dir() else ROOT
TARGET = NATIVE / "target"
LOCK_JSON = ROOT / "compatibility.lock.json"
LOCAL_HORIZON = ROOT.parent / "horizon"
SIBLING_MIXINS = ROOT.parent / "horizon-mods" / "native" / "target" / "horizon-mixins"
REPO = "horizon-rust/horizon"
HOOKS_FILE = "crates/horizon-client/src/game/native_hooks.rs"
HOOKS_LINE = re.compile(r"^pub\(crate\) const NATIVE_HOOKS_API: u32 = (\d+);$", re.M)
EXE = ".exe" if os.name == "nt" else ""
LOCKED = (32, 33)  # ERROR_SHARING_VIOLATION, ERROR_LOCK_VIOLATION
CLOSE_GAME = (
    "Close the running Horizon game window (and any horizon-client / horizon-ctl process), "
    "then run this again."
)


class FileInUse(Exception):
    """A file another process (usually the running game) holds open."""

    def __init__(self, path):
        super().__init__(path)
        self.path = path


def read_text(path):
    return Path(path).read_text(encoding="utf-8")


def write_text(path, text):
    """UTF-8 with LF line endings, whatever the platform."""
    Path(path).write_text(text.replace("\r\n", "\n"), encoding="utf-8", newline="\n")


def rmtree(path):
    """shutil.rmtree that clears read-only flags on Windows and tolerates a missing tree."""
    def clear_read_only(function, failed, error):
        if isinstance(error, PermissionError) and getattr(error, "winerror", None) not in LOCKED:
            os.chmod(failed, stat.S_IWRITE)
            function(failed)
        else:
            raise error

    if Path(path).exists():
        shutil.rmtree(path, onexc=clear_read_only)


def rename(source, destination, attempts=5):
    """Path.rename, retried briefly for Windows Defender / indexer locks."""
    for attempt in range(attempts):
        try:
            return Path(source).rename(destination)
        except PermissionError:
            if attempt == attempts - 1:
                raise
            time.sleep(0.5 * (attempt + 1))


def resolve_mod_dir(name):
    """Resolve either a folder name (e.g. '01_sf3_skyblock') or mod id (e.g. 'sf3_skyblock')."""
    direct = NATIVE / name
    if (direct / "compatibility.json").is_file():
        return direct
    for candidate in sorted(NATIVE.iterdir()):
        if not candidate.is_dir() or not (candidate / "compatibility.json").is_file():
            continue
        if candidate.name.endswith(f"_{name}"):
            return candidate
        mixins = candidate / "mixins"
        if mixins.is_dir() and (mixins / name / "horizon-mixin.toml").is_file():
            return candidate
    sys.exit(f"no mod native/{name}/ (compatibility.json)")


class Mod:
    """native/<name>/: its compatibility.json and its one mixin bundle."""

    def __init__(self, name):
        self.root = resolve_mod_dir(name)
        self.dir_name = self.root.name
        self.compat = json.loads(read_text(self.root / "compatibility.json"))
        mixins = self.root / "mixins"
        self.bundle = next(p for p in mixins.iterdir() if (p / "horizon-mixin.toml").is_file())
        manifest = tomllib.loads(read_text(self.bundle / "horizon-mixin.toml"))
        self.manifest = manifest
        self.id = manifest["mod"]["id"]
        self.version = manifest["mod"]["version"]
        self.priority = manifest["mod"].get("priority", 100)


def all_mods():
    return sorted(
        p.name
        for p in NATIVE.iterdir()
        if p.is_dir() and (p / "compatibility.json").is_file()
    )


def log(*args):
    print(*args, file=sys.stderr, flush=True)


def get(url):
    request = urllib.request.Request(url, headers={"User-Agent": "sf3-horizon-native-mod"})
    token = os.environ.get("GITHUB_TOKEN")
    if token and url.startswith("https://api.github.com/"):
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request, timeout=300) as response:
        return response.read()


def latest_nightly():
    refs = json.loads(get(f"https://api.github.com/repos/{REPO}/git/matching-refs/tags/nightly-source/"))

    def nightly_date(ref):
        return ref.split("nightly-source/")[1][:10]

    newest_day = max(nightly_date(r["ref"]) for r in refs)
    same_day = [r for r in refs if nightly_date(r["ref"]) == newest_day]
    if len(same_day) == 1:
        newest = same_day[0]
    else:
        def commit_time(r):
            commit = json.loads(get(f"https://api.github.com/repos/{REPO}/commits/{r['object']['sha']}"))
            return commit["commit"]["committer"]["date"]

        newest = max(same_day, key=commit_time)
    return get_commit(newest["ref"].removeprefix("refs/tags/"))


def get_commit(ref):
    if (LOCAL_HORIZON / ".git").exists():
        res = subprocess.run(
            ["git", "-C", str(LOCAL_HORIZON), "rev-parse", f"{ref}^{{commit}}"],
            capture_output=True,
            text=True,
        )
        if res.returncode == 0:
            return res.stdout.strip()
    return json.loads(get(f"https://api.github.com/repos/{REPO}/commits/{ref}"))["sha"]


def source(revision):
    """Horizon's source at `revision`, unpacked once into native/target/horizon/<revision>/."""
    out = TARGET / "horizon" / revision
    if (out / ".horizon-revision").is_file():
        return out
    partial = TARGET / "horizon" / f".{revision}.partial"
    rmtree(partial)
    partial.mkdir(parents=True)

    # Prefer local ../horizon git archive when available for offline speed and determinism.
    exported_locally = False
    if (LOCAL_HORIZON / ".git").exists():
        check = subprocess.run(
            ["git", "-C", str(LOCAL_HORIZON), "cat-file", "-t", revision],
            capture_output=True,
            text=True,
        )
        if check.returncode == 0 and check.stdout.strip() == "commit":
            log(f"Exporting Horizon {revision[:7]} from local checkout {LOCAL_HORIZON}")
            top = partial / f"horizon-{revision}"
            top.mkdir(parents=True)
            archive_proc = subprocess.run(
                ["git", "-C", str(LOCAL_HORIZON), "archive", "--format=tar", revision],
                capture_output=True,
                check=True,
            )
            with tarfile.open(fileobj=io.BytesIO(archive_proc.stdout), mode="r:") as archive:
                archive.extractall(top, filter="data")
            exported_locally = True

    if not exported_locally:
        log(f"Downloading Horizon {revision[:7]}")
        data = get(f"https://codeload.github.com/{REPO}/tar.gz/{revision}")
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
            archive.extractall(partial, filter="data")

    top = next(partial.iterdir())
    for path in top.rglob("*"):
        if path.is_symlink():
            path.unlink()
    write_text(top / ".horizon-revision", revision)
    rmtree(out)
    rename(top, out)
    rmtree(partial)
    return out


def hooks_api(tree):
    found = HOOKS_LINE.search(read_text(tree / HOOKS_FILE)) if (tree / HOOKS_FILE).is_file() else None
    return int(found.group(1)) if found else None


def tool(mods):
    """horizon-mixins at the mods' pinned commit, built or copied once."""
    revs = {m.compat["horizon_mixins_revision"] for m in mods}
    if len(revs) != 1:
        sys.exit(f"the mods pin different horizon-mixins commits: {sorted(revs)}")
    rev = revs.pop()
    root = TARGET / "horizon-mixins" / rev
    binary = root / "bin" / f"horizon-mixins{EXE}"
    if not binary.is_file():
        sibling_bin = SIBLING_MIXINS / rev / "bin" / f"horizon-mixins{EXE}"
        if sibling_bin.is_file():
            log(f"Reusing cached horizon-mixins {rev[:7]} from {sibling_bin}")
            binary.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(sibling_bin, binary)
        else:
            log(f"Building horizon-mixins {rev[:7]}")
            repo = mods[0].compat["horizon_mixins_repository"]
            subprocess.run(
                [
                    "cargo",
                    "install",
                    "--locked",
                    "--quiet",
                    "--git",
                    repo,
                    "--rev",
                    rev,
                    "--root",
                    str(root),
                    "horizon-mixins-cli",
                ],
                check=True,
            )
    return binary


def keep_unchanged_timestamps(fresh, out):
    """Give each file of `fresh` whose content equals its copy in `out` that copy's timestamps."""
    for directory, _, names in os.walk(fresh):
        for name in names:
            new = Path(directory, name)
            old = out / new.relative_to(fresh)
            try:
                old_stat = old.stat()
            except FileNotFoundError:
                continue
            if old_stat.st_size == new.stat().st_size and filecmp.cmp(new, old, shallow=False):
                os.utime(new, ns=(old_stat.st_atime_ns, old_stat.st_mtime_ns))


def mirror(fresh, out):
    """robocopy /MIR fresh -> out: copies new and changed files, deletes extras."""
    keep_unchanged_timestamps(fresh, out)
    done = subprocess.run(
        [
            "robocopy",
            str(fresh),
            str(out),
            "/MIR",
            "/COPY:DAT",
            "/DCOPY:T",
            "/XJ",
            "/R:2",
            "/W:1",
            "/NP",
            "/NJH",
            "/NJS",
            "/NDL",
            "/NFL",
        ],
        capture_output=True,
        text=True,
        errors="replace",
    )
    if done.returncode >= 8:
        report = (done.stdout + done.stderr).strip()
        held = re.search(r"ERROR (?:32|33) \(0x0000002[01]\).*?(\S:\\\S.*)", report)
        if held:
            path = Path(held.group(1).strip())
            raise FileInUse(out / path.relative_to(fresh) if path.is_relative_to(fresh) else path)
        log(report)
        sys.exit(f"robocopy failed with exit code {done.returncode} mirroring {fresh} to {out}")


def stage(mods, revision):
    """Apply `mods` together on Horizon `revision`: native/target/stage/<ids>/."""
    tree = source(revision)
    api = hooks_api(tree)
    for m in mods:
        # Horizon main (2026-11) dropped NATIVE_HOOKS_API when native_hooks.rs became a directory: no number, no check.
        if api is not None and api < m.compat["hooks"]:
            sys.exit(f"Horizon {revision[:7]} has native hook points v{api}, {m.id} needs v{m.compat['hooks']}.")
    key = "+".join(m.id for m in mods)
    # Windows' 260-character path limit: with every bundle the joined ids would break the C builds under stage/ (mimalloc).
    if len(key) > 120:
        key = "all-" + hashlib.sha1(key.encode()).hexdigest()[:12]
    bundles = TARGET / "mods" / key
    rmtree(bundles)
    for m in mods:
        shutil.copytree(m.bundle, bundles / m.id)
        toml = bundles / m.id / "horizon-mixin.toml"
        write_text(
            toml,
            re.sub(
                r'horizon_revision = "[0-9a-f]{40}"',
                f'horizon_revision = "{revision}"',
                read_text(toml),
            ),
        )
    fresh = (TARGET / "stage.new").resolve()
    rmtree(fresh)
    subprocess.run(
        [str(tool(mods)), "apply", "--workspace", str(tree), "--mods", str(bundles), "--out", str(fresh)],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    out = TARGET / "stage" / key
    out.mkdir(parents=True, exist_ok=True)
    mirror(fresh, out)
    rmtree(fresh)
    return out


def ensure_not_running(binaries):
    for name in ("horizon-client", "horizon-ctl"):
        exe = binaries / f"{name}{EXE}"
        if exe.is_file():
            try:
                with open(exe, "r+b"):
                    pass
            except PermissionError as error:
                raise FileInUse(exe) from error


def cargo(stage_dir, action, target_dir=None):
    cargo_target = Path(target_dir).resolve() if target_dir else (TARGET / "cargo")
    jobs = os.environ.get("FLEET_LOAD_JOBS") or os.environ.get("CARGO_BUILD_JOBS")
    command = ["cargo", action, "--locked", "-p", "horizon-client", "--bin", "horizon-client"]
    if action == "build":
        ensure_not_running(cargo_target / "fast")
        library = stage_dir / "crates/horizon-client-lib/Cargo.toml"
        if library.is_file() and any(
            b.get("name") == "horizon-ctl" for b in tomllib.loads(read_text(library)).get("bin", [])
        ):
            command += ["-p", "horizon-client-lib"]
        command += ["--bin", "horizon-ctl", "--profile", "fast"]
    if os.environ.get("NATIVE_NO_DEFAULT_FEATURES"):
        command.append("--no-default-features")
    if jobs:
        command += ["-j", jobs]
    env = dict(os.environ, CARGO_TARGET_DIR=str(cargo_target), RUSTFLAGS="-D warnings")
    subprocess.run(command, cwd=stage_dir, env=env, check=True)
    return cargo_target / "fast"


def package(m):
    """Build deterministic native/target/<id>-<version>.hnmod."""
    manifest = {
        "schema": 1,
        "id": m.id,
        "version": m.version,
        "game": m.compat["game"],
        "horizon": m.compat["horizon_revision"],
        "mixins": m.compat["horizon_mixins_revision"],
        "hooks": m.compat["hooks"],
    }
    pinned = m.manifest.get("compatibility", {}).get("horizon_revision")
    if pinned != m.compat["horizon_revision"]:
        sys.exit(f"{m.id}: horizon-mixin.toml pins {pinned}, compatibility.json {m.compat['horizon_revision']}")
    files = {"horizon-native.json": (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")}
    data = [Path("data")] + [Path(c["path"]) / "data" for c in m.manifest.get("crate", [])]
    for path in sorted(m.bundle.rglob("*")):
        relative = path.relative_to(m.bundle)
        if path.is_file() and (path.suffix in (".rs", ".toml") or any(relative.is_relative_to(d) for d in data)):
            files[f"mixins/{m.id}/{relative.as_posix()}"] = path.read_bytes()
    licence = m.root / "LICENSE"
    if licence.is_file():
        files.setdefault(f"mixins/{m.id}/LICENSE", licence.read_bytes())
    out = TARGET / f"{m.id}-{m.version}.hnmod"
    TARGET.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in sorted(files.items()):
            info = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, content)
    print(
        json.dumps(
            {
                "id": m.id,
                "priority": m.priority,
                "file": str(out),
                "size": out.stat().st_size,
                "sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
            },
            indent=2,
        )
    )


def sync_lock():
    """Synchronize compatibility.lock.json pins into all native/*/compatibility.json and horizon-mixin.toml."""
    if not LOCK_JSON.is_file():
        sys.exit(f"missing {LOCK_JSON}")
    lock = json.loads(read_text(LOCK_JSON))
    compat_payload = {
        "game": lock["game"],
        "hooks": lock["hooks"],
        "horizon_repository": lock["horizon_repository"],
        "horizon_revision": lock["horizon_revision"],
        "horizon_mixins_repository": lock["horizon_mixins_repository"],
        "horizon_mixins_revision": lock["horizon_mixins_revision"],
    }
    synced = []
    for name in all_mods():
        mod_dir = NATIVE / name
        compat_path = mod_dir / "compatibility.json"
        write_text(compat_path, json.dumps(compat_payload, indent=2) + "\n")
        mixins_dir = mod_dir / "mixins"
        bundle = next(p for p in mixins_dir.iterdir() if (p / "horizon-mixin.toml").is_file())
        toml_path = bundle / "horizon-mixin.toml"
        updated = re.sub(
            r'horizon_revision = "[0-9a-f]{40}"',
            f'horizon_revision = "{lock["horizon_revision"]}"',
            read_text(toml_path),
        )
        write_text(toml_path, updated)
        synced.append(name)
    print(
        json.dumps(
            {
                "status": "synced",
                "horizon_revision": lock["horizon_revision"],
                "horizon_mixins_revision": lock["horizon_mixins_revision"],
                "hooks": lock["hooks"],
                "bundles": synced,
            },
            indent=2,
        )
    )


class TargetLock:
    """Single-instance lock on native/target/.native.lock."""

    def __init__(self):
        TARGET.mkdir(parents=True, exist_ok=True)
        self.path = TARGET / ".native.lock"
        self.handle = None
        self.lock = None

    def __enter__(self):
        try:
            import filelock
        except ImportError:
            filelock = None
        if filelock:
            self.lock = filelock.FileLock(str(self.path))
            try:
                self.lock.acquire(timeout=0)
            except filelock.Timeout:
                log(f"Another native run holds {self.path}; waiting for it to finish...")
                self.lock.acquire()
            return self
        import msvcrt

        self.handle = open(self.path, "a+b")
        self.handle.seek(0)
        try:
            msvcrt.locking(self.handle.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            log(f"Another native run holds {self.path}; waiting for it to finish...")
            while True:
                try:
                    msvcrt.locking(self.handle.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError:
                    time.sleep(1)
        return self

    def __exit__(self, *_):
        if self.lock:
            self.lock.release()
        elif self.handle:
            import msvcrt

            self.handle.seek(0)
            msvcrt.locking(self.handle.fileno(), msvcrt.LK_UNLCK, 1)
            self.handle.close()


def run(args):
    if args.action == "sync":
        sync_lock()
        return
    names = all_mods() if (not args.mods or args.mods == ["all"]) else args.mods
    mods = [Mod(n) for n in names]
    if args.action == "package":
        for m in mods:
            package(m)
        return
    if args.horizon is None:
        newest = max(m.compat["hooks"] for m in mods)
        revs = {m.compat["horizon_revision"] for m in mods if m.compat["hooks"] == newest}
        if len(revs) != 1:
            sys.exit(f"the mods were tested on different Horizons {sorted(revs)}: pass --horizon")
        revision = revs.pop()
    else:
        revision = latest_nightly() if args.horizon == "latest" else args.horizon
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        revision = get_commit(revision)
    log(f"{', '.join(f'{m.id} {m.version} (p={m.priority})' for m in mods)} on Horizon {revision[:7]}")
    out = stage(mods, revision)
    if args.action == "stage":
        print(json.dumps({"mods": [m.id for m in mods], "horizon": revision, "stage": str(out)}, indent=2))
        return
    if args.action == "check":
        cargo(out, "check", args.target_dir)
        print(json.dumps({"mods": [m.id for m in mods], "horizon": revision, "check": "ok"}))
        return
    binaries = cargo(out, "build", args.target_dir)
    if args.action == "build":
        print(
            json.dumps(
                {
                    "mods": [m.id for m in mods],
                    "horizon": revision,
                    "game": str(binaries / f"horizon-client{EXE}"),
                }
            )
        )
        return
    if not args.resources:
        sys.exit("proof needs --resources (prepared resources for Minecraft 26.3)")
    sys.path.insert(0, str(Path(__file__).parent))
    import importlib.util

    for m in mods:
        spec = importlib.util.spec_from_file_location(f"proof_{m.id}", m.root / "proof.py")
        proof = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(proof)
        proof.run(binaries / f"horizon-ctl{EXE}", Path(args.resources).resolve(), TARGET / "proof" / m.id)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("action", choices=["sync", "stage", "check", "build", "package", "proof"])
    parser.add_argument("mods", nargs="*", default=["all"], help="folders or IDs of native/ (`all`: every one)")
    parser.add_argument("--horizon", help="a Horizon commit, `latest` or a tag (default: compatibility.lock.json)")
    parser.add_argument("--resources", help="prepared resources (proof): .local/horizon-client/26.3")
    parser.add_argument("--target-dir", help="shared Cargo target directory (default: native/target/cargo)")
    args = parser.parse_args()
    try:
        with TargetLock():
            run(args)
    except FileInUse as error:
        sys.exit(f"\n{error.path} is in use by another process.\n{CLOSE_GAME}")
    except PermissionError as error:
        if getattr(error, "winerror", None) in LOCKED:
            sys.exit(
                f"\n{error.filename or error} is in use by another process (WinError {error.winerror}).\n"
                f"{CLOSE_GAME}"
            )
        raise


if __name__ == "__main__":
    main()
