# Content mods built for Horizon main (2026-11-20)

Tool: `tools/content_for_main.py`. It builds copies of `content/<mod>/` with main's `cargo-horizon-mod`; `content/` is not
touched, so the old tool and old game build keep working. Follow-up to `content_mods_check_2026-11-20.md`.

Command: `py tools/content_for_main.py` (all mods) or `py tools/content_for_main.py <mod> ... [--out DIR]`;
`--self-test` checks the two JSON rewrites. Default output `C:\Users\chaxt\.sf3-tools\content_main\<mod>`, all `.hmod`
files collected in `...\content_main\_hmod\`.

Result: `summary: 118 pass, 0 fail of 118` (build and `check` both exit 0 for every mod; 118 `.hmod` files in `_hmod`).
No mod fails.

## The two rewrites (on the copy only)

- Item files: top-level `place_block` renamed to `block` (same meaning).
- Fluid files: rewritten to `{"sprite": <old still>}`; `template`, `bucket`, `block`, `still`, `flowing` are dropped.

## Fluid choice: no `world`

Per `how-to/content-mods.md`, a fluid file without `world` is only a client look: `sprite`/`tint` for how the fluid is
drawn, and the fluid is available to recipe pages (the "well" is drawn from it). It does not exist in the world: no
flowing simulation from the fluid file and no generated block or bucket. With `"world": {}` main would generate
`<id>:<path>` (a `minecraft:water` copy) and `<id>:<path>_bucket`, which collide with our own block and bucket files
("declared twice"). We keep our own block (a `minecraft:water` template copy) and bucket (a `minecraft:water_bucket`
template copy). What that means in game is unverified: what the docs describe is that those files are ordinary
template-copy block and item registrations, not tied to the fluid file.

## Not checked

- No game launch and no in-game behaviour (fluid look, flow, buckets, item placement).
- Old tool vs new tool output equivalence beyond build/check; `.hmod` contents not diffed against the old builds.
- Signatures, `check --uses`, `fits`, `.hpack`, native bundles.
- Generators (`extract_sf3_assets.py`, `regen_all.py`) not run and not changed; `content/` keeps old keys.
- `tint` not carried over (old files had none).
