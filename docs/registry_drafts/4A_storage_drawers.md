# 4A Storage Drawers (bundle 03) - registry draft

For Claude to merge into `SF3_REGISTRY.md`. Spec: `docs/specs/batch4_storage.md` SD-B01, SD-B02, SD-I02, SD-I03, SD-I07 (drawer key), SD-I08.

## Ids now handled by `native/03_sf3_storage_qol` (no new content ids)

| id | behaviour |
|---|---|
| `storagedrawers:comp_drawers` | new `StorageKind` `drawer_comp` (entity `sf3:drawer`, `Layout::Triple`, `Capacity::Stacks(16)`, `pooled`). 3 slots share one pool in base units; slot i shows `pool / rates[i]`; capacity = `stack(slot 0 item) * 16 * mult * rates[0]`. Slot hit: top 0, bottom-left 1, bottom-right 2. Tiers from `COMP_CHAINS`. |
| `storagedrawers:upgrade_void` | `UpgradeOp::Void`: matching items accepted when full, excess destroyed. One per drawer. |
| `storagedrawers:upgrade_one_stack` | `UpgradeOp::OneStack`: base capacity 1 stack (times multipliers). One per drawer. Install refused if any slot (pooled: the pool) holds more than the reduced capacity. |
| `storagedrawers:drawer_key` | right click a drawer front: toggle lock (locked slots keep their item at count 0 and refuse others). On `storagedrawers:controller`: every drawer of the network is locked, unless all already were (then unlocked). Works sneaking too (`native_use_item_on`). |
| `storagedrawers:tape` | right click a drawer: seal it (no insert, extract, hopper output, upgrades) and wear the tape by 1. Content `max_damage` is 9 (1.10.2 `setMaxDamage(8)` breaks on the 9th damage, 26.3 breaks at damage >= max). Sneak + empty hand right click unseals. Breaking a sealed drawer drops the drawer item with its whole store (items, upgrades, lock, Kind) in `minecraft:custom_data`; placing it restores the contents unsealed. |

## Saved state (block entity `sf3:drawer`, compound)

Existing keys unchanged (`Kind`, `Item`/`Count`/`Out`, `Item1`.., `Upgrades`); appended: `Locked` (Int), `Sealed` (Int), and for the compacting drawer `Pool` (Int, base units) and `Rates` (String `"81,9,1"`). Old saves have none of them and load as unlocked, unsealed. A pooled drawer ignores its saved `Count`s (derived from `Pool`). The existing 5 kinds keep their slot counts; `drawer_comp` is appended before `barrel` in `KINDS` (the fallback kind of an entity without `Kind` is still the first, `drawer_full1`).

## Tables and generators

- `tools/storage_defs.json`: `drawer_storage` upgrade set gained `{"void": true}` and `{"one_stack": true}` entries; new kind `drawer_comp` (`"layout": "triple"`, `"pooled": true`). `tools/gen_storage_tables.py` knows `triple`, `void`, `one_stack`, `pooled`. `py tools/gen_storage_tables.py --check`.
- `tools/gen_comp_tiers.py` (new, `--check`): fills `// BEGIN GENERATED comp_chains` in bundle 03 `runtime.rs` (`COMP_CHAINS`, top first, base units per item). Sources: the 9 built-in rules of `CompTierRegistry.initialize()` + `compactingRules` (26.3 ids), and every reversible 2x2/3x3 pair in `content/*/data/*/recipe/*.json` (both directions needed; tag ingredients only when the tag has one item). Static table chosen over a runtime recipe hook: the swept recipes are fixed at build time, and the tier lookup is pure and testable. Re-run after a re-sweep.
- `tools/curate_storagedrawers.py` (new, `--check`): the facing fix. Basic 2/4/half2/half4, all custom drawers and `comp_drawers` get template `minecraft:barrel` (as `basic_drawers_fulldrawers1` already had), the front-drawn ones (basic 2/4/half2/half4, `comp_drawers`) get `facing=...,open=...` blockstate variants turned by `y`, and `tape` gets the `max_damage` component. Run it after `extract_sf3_assets.py --seed` (the sweep regenerates these files).

## Hook injections (bundle 03)

New: `place_block` -> `native_place_block` (HEAD; bindings `game`, `stack`, `pos`), helper `place_block.rs`, glue `place_block`. Gives a placed drawer item carrying `minecraft:custom_data` (a sealed drawer that was broken) its contents back, unsealed.

Existing hooks extended, no signature change: `native_right_click_block` (tape, key, unseal), `native_use_item_on` (tape and key while sneaking), `native_destroy_block` + `native_loot_drops` (sealed drawer drops itself with contents; creative break too), `native_container_accepts` (sealed/void/pooled room), `native_block_entity_tick` (pooled mirror).

## Wiring notes

- Pooled output slots: slot i shows a stack of its item taken from what the tiers above left of the pool (`Store::mirrors`), so hoppers never get more than the pool holds in total.
- `Store` API changes (runtime.rs, pure): `add_upgrade(kind, item, &dyn Fn(&str)->u32)`; `size_item` (which item's stack size sets a slot's capacity; a pooled drawer uses slot 0's), `mirrors`, `set_locked`, `seal`, `can_add_upgrade`; `StorageKind.pooled`; `Layout::Triple`.
- Out of scope, not done: shroud/quantify/personal keys, redstone/status/creative upgrades, Obsidian explosion resistance, drawer GUI, front rendering.
