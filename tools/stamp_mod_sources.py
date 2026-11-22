"""Record each content mod's source mod (licence, page, jar) in tools/mod_sources.json.

content/ manifests stay in the old tool's format; `content_for_main.py` adds these keys to the copies it builds.

Reads the dev pipeline's inventory (`horizon-port-pack import` + `inventory`, work dir outside the
repo). Only jar metadata and Modrinth's records are used, never classes (CLAUDE.md rule 6).

    py tools/stamp_mod_sources.py [work dir]
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORK = Path(sys.argv[1] if len(sys.argv) > 1 else "C:/Users/chaxt/.sf3-tools/port-work")
# Namespaces whose jar's metadata gives no usable mod id: matched by jar file name.
BY_JAR = {"charset": "Charset-", "dimensionalcake": "dimensionalcake-", "elevatorid": "ElevatorMod",
          "gyth": "Gyth-", "simpleachievements": "SimpleAchievements-", "solarfluxreborn": "SolarFluxReborn",
          "voidcup": "voidcup-", "woodenshears": "SBM-WoodenShears"}
OURS = {"sf3_content"}
FIELDS = ("license", "homepage", "credits")


def main() -> None:
    inv = json.loads((WORK / "inventory.json").read_text(encoding="utf-8"))
    mr = json.loads((WORK / "modrinth.json").read_text(encoding="utf-8"))
    slug = {}  # jar file name -> modrinth project page
    for v in mr["versions"].values():
        p = mr["projects"].get(v["project_id"]) or {}
        for f in v["files"]:
            if p.get("slug"):
                slug[f["filename"]] = f"https://modrinth.com/mod/{p['slug']}"
    by_key = {r["key"].lower(): r for r in inv}
    out = {}
    for toml in sorted((ROOT / "content").glob("*/horizon-mod.toml")):
        ns = toml.parent.name
        if ns in OURS:
            continue
        pre = BY_JAR.get("charset" if ns.startswith("charset") else ns)
        r = by_key.get(ns) or next((r for r in inv if pre and Path(r["path"]).name.startswith(pre)), None)
        assert r, f"no jar for {ns}"
        jar = Path(r["path"]).name
        lic = r["license"] if r["license"] not in ("", "unknown") else "unknown (not on Modrinth; see the mod's page)"
        vals = {"license": lic, "credits": f"Port of {jar} from FTB Presents SkyFactory 3"}
        if jar in slug:
            vals["homepage"] = slug[jar]
        out[ns] = vals
        # The old tool rejects these keys: keep content/ manifests free of them.
        text = toml.read_text(encoding="utf-8")
        clean = "".join(l for l in text.splitlines(keepends=True) if not re.match(rf"({'|'.join(FIELDS)})\s*=", l))
        if clean != text:
            toml.write_text(clean, encoding="utf-8", newline="\n")
    (ROOT / "tools" / "mod_sources.json").write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"{len(out)} mods recorded, {sum(1 for v in out.values() if 'homepage' in v)} with a Modrinth page")


if __name__ == "__main__":
    main()
