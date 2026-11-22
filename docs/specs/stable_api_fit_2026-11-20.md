# Stable mod API fit (survey, 2026-11-20)

Name-level survey of how much of our mixin bundles could move onto Horizon main's stable API
(`crates/horizon-mod-vocab/src/hooks/` = 733 hooks, `.../host/` = 1149 host methods; main `084ae44e40`).
Our build stays pinned at `04a26210e3`. Nothing was migrated. Matching is by name only: signatures and behaviour not checked.

## Where our code attaches (457 injection targets, 118 distinct functions)

- 276 injections (74 hooks) hit a hook that exists on main under the same name (`use_item`, `block_entity_tick`, `loot_drops`, `server_tick`, `level_tick_post`, ...).
- About 67 more hit a hook that exists under a new name (`destroy_block` -> `break_block`, `player_chat` -> `server_chat`, `living_incoming_damage` -> `living_damage_pre`, `perform_command` -> `command`/`run_mod_command`, `break_speed` -> `player_break_speed`, pearl/chorus -> `ender_entity_teleport`/`item_consumption_teleport`, `player_respawn_position` -> `respawn_position`).
- About 114 (25%) have no obvious stable hook: mod block-entity storage (`block_entity_container`, `_fluids`, `_energy`, `_accepts_fluid`, `container_accepts`), `item_energy_buffer`, `native_mods` (registration), `player_tick` (maybe `entity_tick_*`), `recipe_categories` (JEI), `menu_input_closed`, worldgen (`chunk_generate`, `lod_column`), and 10 raw patches of draw/tooltip functions (stay native mixins).

## What our code calls (3,397 calls to 184 engine functions)

- 63 functions (1,426 calls) match a host method by name. Many others exist with an area prefix: `tell` -> `player_tell`, `set_block` -> `level_set_block`, `add_effect` -> `living_add_effect`, `give_stack` -> `player_give_stack`, `insert_item` -> `container_insert`, `energy` -> `energy_*`.
- Biggest unknown: our machines' saved data through `native_with_mod_block_entity` / `native_mod_block_entity` (464 calls). Main has `block_entity_data*` and `attachments`; fit not checked.
- No stable equivalent seen: host flight, `sneaking`, `acting_id` (191 calls, hook context).

## Per bundle (injections: same name / renamed / no stable hook; engine calls)

| Bundle | Inj | Same | Renamed | None | Calls |
|---|---|---|---|---|---|
| 01_sf3_skyblock | 13 | 7 | 3 | 3 | 51 |
| 02_sf3_exnihilo | 11 | 7 | 2 | 2 | 74 |
| 03_sf3_storage_qol | 23 | 17 | 3 | 3 | 97 |
| 04_sf3_tech_power | 43 | 24 | 10 | 9 | 664 |
| 05_sf3_farming | 43 | 29 | 2 | 12 | 229 |
| 06_sf3_endgame | 25 | 17 | 3 | 5 | 198 |
| 07_sf3_jei | 10 | 0 | 0 | 10 | 24 |
| 08_sf3_immersive | 17 | 7 | 2 | 8 | 100 |
| 09_sf3_botania | 31 | 19 | 6 | 6 | 316 |
| 10_sf3_bloodmagic | 29 | 20 | 4 | 5 | 377 |
| 11_sf3_rftools | 30 | 20 | 5 | 5 | 244 |
| 12_sf3_envtech | 11 | 6 | 2 | 3 | 70 |
| 13_sf3_draconic | 28 | 17 | 4 | 7 | 210 |
| 14_sf3_tinkers | 20 | 11 | 4 | 5 | 89 |
| 15_sf3_logistics | 21 | 13 | 2 | 6 | 65 |
| 16_sf3_utility | 33 | 18 | 7 | 8 | 268 |
| 17_sf3_xutils | 30 | 19 | 4 | 7 | 170 |
| 19_sf3_player | 18 | 11 | 2 | 5 | 74 |
| 20_sf3_charset | 13 | 9 | 2 | 2 | 45 |
| 21_sf3_chance | 8 | 5 | 2 | 1 | 32 |

Easiest trial candidates: 21_sf3_chance, 20_sf3_charset, 01_sf3_skyblock. Hardest: 07_sf3_jei (all custom), 04_sf3_tech_power (664 calls).
