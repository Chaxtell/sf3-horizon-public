"""Copy the shareable part of this repo into a separate folder for the public GitHub repo.

The private repo keeps everything. The public one gets only our own work: pipeline scripts, hook requests, engine notes.
Left out: every mod's content (textures, models, data), the native mods, generators and data tables taken from
jars, the plan and CLAUDE.md (they quote jar internals), and any text file that mentions reading mod code
(`javap` etc.) or, in docs, numbers read from a jar. A file moves over
only by being allowed here after review.

    py tools/export_public.py [out dir]      |      py tools/export_public.py --self-test
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT.parent / "sf3-horizon-public"
CODE_WORDS = re.compile(r"javap|decompil|\bcfr\b|procyon|fernflower|\.class\b|ClassReader", re.I)
JAR_WORDS = re.compile(r"\bjar", re.I)  # docs only: older notes state numbers "read from the jar"
# Reviewed by hand: no mod code, only what the port needs or the rule itself.
REVIEWED = {"HOOK_REQUESTS.md", "tools/export_public.py"}
TOP = {"HOOK_REQUESTS.md", "compatibility.lock.json", ".gitignore", ".gitattributes"}
# Pipeline scripts with no mod data in them. Generators hold numbers taken from the jars: kept private.
TOOLS = {"content_for_main.py", "stamp_mod_sources.py", "export_public.py", "native_win.py", "mod_sources.json"}


def allowed(path: str) -> bool:
    """Path rules only; the text check is separate."""
    if path.endswith(".png") or path == "docs/PUBLIC_README.md":
        return False
    if path in TOP or path.startswith("docs/"):
        return True
    return path.startswith("tools/") and path[6:] in TOOLS  # not content/, native/, the plan, CLAUDE.md


def clean_text(path: str, text: str) -> bool:
    if path in REVIEWED:
        return True
    return not CODE_WORDS.search(text) and not (path.startswith("docs/") and JAR_WORDS.search(text))


def self_test():
    assert allowed("tools/export_public.py") and allowed("tools/mod_sources.json") and allowed("docs/SETUP.md")
    assert not allowed("tools/sf3_catalog.json") and not allowed("tools/hand_content/x/a.json")
    assert not allowed("tools/gen_aa_tables.py") and not allowed("MASS_PORT_PLAN.md") and not allowed("CLAUDE.md")
    assert not allowed("content/sf3_content/data/sf3/recipe/a.json") and not allowed("native/sf3_core/src/lib.rs")
    assert not allowed("docs/a.png") and not allowed("SF3_REGISTRY.md")
    assert clean_text("docs/a.md", "watched in play") and not clean_text("docs/a.md", "read with javap -c")
    assert not clean_text("docs/a.md", "numbers read from the jar") and clean_text("tools/x.py", "jar name")
    assert clean_text("tools/export_public.py", "javap")
    print("self-test ok")


def main(argv):
    if "--self-test" in argv:
        return self_test()
    out = Path(argv[0]) if argv else DEFAULT_OUT
    files = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.split("\n")
    keep, dropped = [], 0
    for f in filter(None, files):
        if not allowed(f):
            continue
        if not clean_text(f, (ROOT / f).read_text(encoding="utf-8", errors="replace")):
            dropped += 1
            continue
        keep.append(f)
    for p in out.glob("*"):  # fresh copy each run; the public repo's own .git stays
        if p.name != ".git":
            shutil.rmtree(p) if p.is_dir() else p.unlink()
    out.mkdir(parents=True, exist_ok=True)
    for f in keep:
        (out / f).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / f, out / f)
    shutil.copy2(ROOT / "docs" / "PUBLIC_README.md", out / "README.md")
    print(f"{len(keep)} files copied to {out}, {dropped} left out for mentioning mod code")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
