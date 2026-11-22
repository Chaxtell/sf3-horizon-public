"""Build content/ mods with Horizon main's cargo-horizon-mod, on copies fixed for main's JSON keys.

content/ stays untouched (the old tool and old game build still use it). Per mod: copy (no target/), rewrite
item `place_block` -> `block` and fluid files to `sprite` only, add the source mod's `license`, `credits` and
`homepage` from tools/mod_sources.json to horizon-mod.toml (the old manifest has no such keys), build, check,
collect the .hmod into <out>/_hmod.

  py tools/content_for_main.py [--out DIR] [mod ...]     |     py tools/content_for_main.py --self-test
"""
import json, os, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOL_DIR = Path(r"C:\Users\chaxt\.sf3-tools\main\bin")
DEFAULT_OUT = Path(r"C:\Users\chaxt\.sf3-tools\content_main")
SOURCES = json.loads((ROOT / "tools" / "mod_sources.json").read_text(encoding="utf-8"))


def fix_item(j):
    if "place_block" in j:
        j["block"] = j.pop("place_block")
    return j


def fix_fluid(j):
    # Main takes only sprite/tint/world. `world` is left out on purpose: it would generate a block and bucket that
    # collide with our own block and bucket files ("declared twice").
    return {"sprite": j["still"]} if "still" in j else {}


def rewrite(mod_dir):
    for kind, fix in (("item", fix_item), ("fluid", fix_fluid)):
        for f in mod_dir.glob(f"data/*/horizon/{kind}/*.json"):
            j = json.loads(f.read_text(encoding="utf-8"))
            f.write_text(json.dumps(fix(j), indent=2) + "\n", encoding="utf-8", newline="\n")


def run(cmd, cwd):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    lines = [l for l in (p.stderr + p.stdout).splitlines() if l.strip()]
    return p.returncode, (lines[0] if lines else "no output")


def process(mod, out):
    dst = out / mod.name
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(mod, dst, ignore=shutil.ignore_patterns("target"))
    rewrite(dst)
    if mod.name in SOURCES:
        toml = dst / "horizon-mod.toml"
        head, sep, tail = toml.read_text(encoding="utf-8").partition("\n[")  # top-level keys go before any table
        head = head.rstrip("\n") + "\n" + "".join(f"{k} = {json.dumps(v)}\n" for k, v in SOURCES[mod.name].items())
        toml.write_text(head + ("\n[" + tail if sep else ""), encoding="utf-8", newline="\n")
    exe = str(TOOL_DIR / "cargo-horizon-mod.exe")
    rc, msg = run([exe, "horizon-mod", "build"], dst)
    if rc:
        return "build: " + msg
    hmods = list((dst / "target" / "horizon-mod").glob("*.hmod"))
    if len(hmods) != 1:
        return f"build made {len(hmods)} .hmod files"
    rc, msg = run([exe, "horizon-mod", "check", str(hmods[0])], dst)
    if rc:
        return "check: " + msg
    (out / "_hmod").mkdir(exist_ok=True)
    shutil.copy2(hmods[0], out / "_hmod" / hmods[0].name)
    return None


def self_test():
    assert fix_item({"template": "t", "place_block": "a:b"}) == {"template": "t", "block": "a:b"}
    assert fix_item({"template": "t"}) == {"template": "t"}
    old = {"template": "minecraft:water", "bucket": "m:x_bucket", "block": "m:x", "still": "m:block/s", "flowing": "m:block/f"}
    assert fix_fluid(old) == {"sprite": "m:block/s"}
    assert fix_fluid({"template": "minecraft:water"}) == {}
    print("self-test ok")


def main(argv):
    if "--self-test" in argv:
        return self_test()
    out, names = DEFAULT_OUT, []
    it = iter(argv)
    for a in it:
        if a == "--out":
            out = Path(next(it))
        else:
            names.append(a)
    os.environ["PATH"] = str(TOOL_DIR) + os.pathsep + os.environ["PATH"]
    mods = [ROOT / "content" / n for n in names] if names else sorted(p for p in (ROOT / "content").iterdir() if p.is_dir())
    out.mkdir(parents=True, exist_ok=True)
    failed = 0
    for m in mods:
        err = process(m, out)
        failed += bool(err)
        print(f"{'FAIL' if err else 'pass'} {m.name}" + (f": {err}" if err else ""), flush=True)
    print(f"summary: {len(mods) - failed} pass, {failed} fail of {len(mods)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
