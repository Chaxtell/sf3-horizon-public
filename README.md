# sf3-horizon

A port of the FTB Presents SkyFactory 3 modpack (Minecraft 1.10.2) to [Horizon](https://github.com/horizon-rust/horizon) 26.3.

This repo holds only my own work:

- `HOOK_REQUESTS.md` and `docs/upstream_requests/`: the engine hooks the port needs, written up for upstream.
- `docs/specs/`: design notes for moving the port onto Horizon's stable mod API.
- `tools/`: the pipeline scripts that build and check the content mods.
- `tools/mod_sources.json`: each original mod, with its licence and page.

The ported mods themselves are not here. Their textures, models, data and behaviour belong to their authors and stay on my machine, as Horizon's `docs/modpacks.md` asks. A mod moves into this repo only when its licence allows sharing.

Since 2026-11-21 the port follows `docs/modpacks.md`: no mod code is read or decompiled. Work from before that date is being checked again by watching each mod in play, and stays private until it is.
