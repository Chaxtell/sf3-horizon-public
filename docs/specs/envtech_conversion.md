# Bundle 12 (`12_sf3_envtech`) on the stable mod API: conversion note (2026-11-20)

Phase 2.4, the machine-framework proof. New mod: `mods/sf3_envtech/` (flat native mod, layout of `mods/sf3_chance`).
SDK build 0a875da. Nothing was run in game.

- `src/runtime.rs`: byte-identical copy of `native/12_sf3_envtech/mixins/sf3_envtech/runtime.rs` (`cmp` clean). All rules stay there.
- `src/lib.rs`: the hooks and Parts (rewrite of the old `glue.rs` and the 11 helper files).
- `src/sf3_host.rs`: byte-identical copy of `mods/sf3_host/sf3_host.rs` (23 functions added, none changed; see `sf3_host_api.md`).
- `src/glue_tests.rs`: 6 FakeHost tests.
- `horizon-mod.toml`: needs the content mods `environmentaltech` and `etlunar` turned on (comment only, not under `[dependencies]`).

Machines converted: Solar Array T1-T4, Lunar Panel (`etlunar:controller_lunar_custom`), Lightning Rod T1-T4, Void Ore Miner
T1-T4, Void Resource Miner T1-T4, Nano Bot Beacon T1-T4, Launcher; plus the Multiblock Assembler and Digital Guide clicks.

## Hook by hook

| Old attach point (`horizon-mixin.toml`) | New | Notes |
|---|---|---|
| `native_mods` (`list.rs`) | none | No Options > Mods entry on the stable API. `h::on(host, "sf3_envtech")` is still asked everywhere the old code asked `native_on`. |
| `native_block_entity` | `BlockEntityPart::block_entity` on Part `Machines`, attached to types `sf3_envtech:controller` (21 controller blocks) and `sf3_envtech:launcher` (`environmentaltech:launcher_1`) | Same initial compounds. Type ids are declared with `r.block_entity_type(..)` in `register`. |
| `native_block_entity_ticks` | `BlockEntityPart::block_entity_ticks` | Same block test. |
| `native_block_entity_tick` | `BlockEntityPart::block_entity_tick` | `event.entity` is a `ModBlockEntityView`; its `nbt` and `items` are passed on. The level in place is the entity's own, so `h::dimension` names it (trap 2 avoided: no per-level work in `server_tick`). |
| `native_block_entity_energy` | `h::declare_energy` (`block_energy`) per block in `register` | Same `ModEnergyBuffer` literals (generators extract-only, not through the top; miners, beacons, launcher insert-only). The game's `ENERGY` provider reads `nbt.energy`, so other mods' cables reach us with no code of ours. |
| `native_block_entity_container` | `h::declare_container` (`block_container`) per miner in `register` | Same `ModContainer`; `menu` stays the block id (the content menu types `environmentaltech:controller_void_*_miner_N`). |
| `native_screen` | `BlockEntityPart::screen` | Same layout; `recipe_book` and `recipe_book_toggle` None. |
| `native_right_click_block_v2` | `Hooks::right_click_block` | Fires on both sides and once per hand (trap 1): only the main hand acts; `click_action` reads only block, hand item and sneak key, so the client ends (`Cancel` + `Success`) exactly the clicks the server takes, and the off hand never follows. Already-cancelled clicks are skipped by the dispatcher, as the old `*cancel` check. |
| `native_place_block` | `ItemPart::on_block_placed_by` on the 4 `controller_nano_bot_beacon_N` items | Owner is `event.placer` instead of the acting id. |
| `native_destroy_block` | `Hooks::break_block` | Beacon flight release, keyed on `event.state`. |
| `native_loot_drops` (explosions) | `BlockPart::on_block_exploded` on `Machines` | Fires before removal with the block entity still readable, which the loot hook no longer guarantees (the pilot found loot runs after the block entity is gone). |

Engine calls inside the tick and clicks map to `sf3_host` as listed in `sf3_host_api.md` ("Added for machines"). Calls
with no engine counterpart now: `native_level_block_entities` (see below), `native_server_players` / `native_acting_id`
/ `native_player` (replaced by `h::player(uuid)`), the single-player host special cases (`add_player_effect`,
`native_client_action_bar`).

## `sf3_host` functions added (23)

World: `day_time`, `weather`, `has_signal`, `sky_light`, `is_loaded`, `min_y`, `has_collision`, `is_block`,
`strike_lightning`. Entities: `entities_in`, `entity_kind`, `set_velocity`. Players: `sneaking`, `permission`, `may_fly`,
`set_may_fly`, `action_bar`, `add_effect_ambient`. Items and capabilities: `max_stack`, `energy_insert`, `insert_item`.
Registration: `declare_energy`, `declare_container`. No signature changed; `mods/sf3_chance/src/sf3_host.rs` recopied
(byte-identical), its `lib.rs` untouched, its `cargo test` passes. Not added (no use in this bundle): menu data slots /
progress bars, `block_entity_sync` / update tags (the old bundle drew no bar and synced nothing beyond what the game sends).

## Behaviour differences

- **Rain and thunder are yes/no.** `runtime` gets 1.0 or 0.0 instead of vanilla's fading 0..1 levels. Solar daytime,
  brightness and the piezo bonus jump when the weather flips instead of ramping over the fade (old play: "rose to 509 RF/t
  while the rain faded" after `/weather clear`; now the drop to rain and the return are one step).
- **Formed-controller registry.** `claimed` (a block serves one formed controller) used `native_level_block_entities`;
  the SDK lists no level's block entities, so controllers record themselves in a static set when they tick and `claimed`
  reads that set (stale entries dropped when the block is no longer a controller; set cleared on world close). Right after
  a world load, a controller that has not ticked yet is not in the set for that first tick.
- **Single-player host is an ordinary player.** The old engine could not give the host flight or velocity and printed
  "The engine cannot give flight to the single-player host yet" / "...cannot launch the single-player host yet". Now the
  beacon grants flight (`set_may_fly`) and the Launcher launches players (`PlayerRef::set_velocity`) for everyone; both
  notices are gone and `fly` is only 0 or 1 (old 2 = "host told").
- **Beacon takeover.** Operator test is `permission_level >= 2` for every player (an unreadable level counts as operator).
  Old: the host always counted. A single-player world without cheats now reads the owner's level 0, so its owner cannot take
  over another player's beacon.
- **Flight grant** keeps a flying player flying (`set_abilities` with `may_fly`); the old `native_set_flight(.., true, false)`
  landed them, which the glue worked around. Taking flight lands the player as before.
- **Beacon effects** for every player: ambient, no particles, icon shown (old guests: same; old host: hidden).
- **Spectators** clicking a controller now do nothing (the hook fires for spectators).
- **Status lines** go to the clicking player's action bar through `PlayerRef::action_bar` (old host fallback to its own
  client is not needed).
- **Output merge** uses `ItemStack::is_stackable_with` (item and components) instead of item id only; miner draws have no
  components, so the result is the same.
- **Assembler `take`**: one item from main slots 0-35 or the off hand (40); the old `native_take_items` scope was not read.

## Features degraded

1. Options > Mods entry (title, version, description): gone (no stable route).
2. Weather levels: yes/no only (above).
3. Nothing else is dropped: every old path (tick of each kind, energy out, item eject, menus, status, Assembler, Guide,
   Launcher settings, beacon bind/takeover/effects/flight/release on break and explosion) has a new counterpart.

## In-game checklist (expected results from `docs/PLAYTEST_LOG.md` and `SF3_REGISTRY.md` 9F)

Instance with `sf3_envtech`, `environmentaltech`, `etlunar` on; creative unless said; status = empty-hand click (action bar).

1. Block entity: `/setblock 0 64 0 environmentaltech:controller_solar_1`; `/data get block 0 64 0` shows id `sf3_envtech:controller`, ints `energy`..`fly` at 0.
2. Assembler (creative): click `controller_solar_1..4` with `environmentaltech:tool_multiblock_assembler`: "the Solar Array TN is complete"; `formed` 1, `cells` 9 / 25 / 49 / 81.
3. Solar T1 at noon, clear: about 648 RF/t, `energy` reaches the 6480 buffer; a stone block over one cell: `cells` 8.
4. Solar output: `environmentaltech:launcher_1` west of a T1 controller (insert-only buffer): the launcher's `energy` rises, the controller's stays near 0. Nothing leaves through the top.
5. Piezo: T1, 2 cores swapped for `environmentaltech:modifier_piezo_1`, noon, `/weather thunder`: "40 RF/t now (9 of 9 cells see the sky, 2 piezo)"; `/weather clear`: back to 648 at once (difference above).
6. Redstone: a lever on the controller: no energy gained while on.
7. Lightning Rod T1 (controller, 4 structure, 4 insulated rods, 3 rods): in thunder `energy` 500,000 after about 1750 ticks, 1,000,000 after about 2560; a real bolt at the top rod; status "thunder yes".
8. Void Ore Miner T1: Assembler places 47 parts; `data merge` 1,000,000 energy; `see` 1; after 400 ticks an iron ore in slot 0, energy -320,000 (800 RF/t); it keeps drawing past the first item (stacks).
9. Miner menu: plain click opens the 1-slot menu; sneak click gives the status line; a hopper or chest beside it takes the output.
10. Red lens (`lens_colored_red`): `focus` "red", `duration` 400, 800 RF/t; chest on top fills (about 13% redstone ore).
11. T2 miner, 4 `modifier_speed_1`: `duration` 96, 2622 RF/t; 4 `modifier_accuracy_1` + `lens_colored_blue`: lapis about 29%.
12. Void Resource Miner T1: andesite after 200 ticks at 20 RF/t, keeps going.
13. Void column: a solid block under the laser core: `see` 0 (glass lets it through).
14. Launcher: `launcher_1` with 100,000 RF, click until `up` 7 ("up +10"): a pig on it goes from y 82 to about y 260, launcher -8,000 RF; a `NoAI` pig is not moved. New: a player standing on it is launched too.
15. Launcher sneak click cycles the sideways force in the status line.
16. Beacon T1: Assembler places 36 parts; 2 cores swapped for regeneration and night vision modifiers; click: "formed, 100000 / 100000 RF, bound to you, 8320 RF a cycle, ... gives: night_vision 1, regeneration 1"; player gets both effects, beacon -8320 RF per cycle.
17. Beacon T2 / T3 / T4: 68 / 108 / 156 parts; all speed modifiers: "speed 2" / "speed 3" / "10240 RF a cycle, gives: speed 4", Speed II / III / IV.
18. Beacon takeover: `owner` set to another uuid by command: plain click keeps "bound to someone else"; sneak click with cheats on: "bound to you".
19. Beacon flight (new, never played): a `environmentaltech:modifier_flight` in a modifier slot, survival owner: may fly after one cycle; break the beacon: flight taken; rebuild, blow it up with TNT: flight taken.
20. Placed beacon (survival, by hand): `owner` is the placer's uuid in hex.
21. Lunar Panel (registry 9F steps 1-5): `/time set 18000` full moon: "10368 RF/t now", "moon phase 0"; phases 1-4: 7776, 5184, 2592, 0; day: 0 RF/t.
22. Digital Guide (`environmentaltech:digital_guide`) on a half-built controller: "Solar Array T1: ... N/M ... | next: ...".
23. A block in hand (e.g. stone) on a controller places the block; no status line, no off-hand use after a status click.
24. Two controllers sharing a structure block: the second stays "not formed" while the first is formed.

24 items.

## Gates (run in `mods/sf3_envtech`, final lines)

- `cargo check`: `Finished `dev` profile [unoptimized + debuginfo] target(s)`
- `cargo test`: `test result: ok. 26 passed; 0 failed` (20 runtime + 6 glue)
- `cargo horizon-mod check`: passes; its three "built field by field" notes fixed with `..Default::default()`
- `mods/sf3_chance`: `cargo test` `test result: ok. 31 passed; 0 failed`
- `cmp` runtime.rs and both `sf3_host.rs` copies: no output (identical)

## Not checked

- Anything in game (the checklist above): no launcher build, no play.
- That `block_entity_type(..).blocks(..)` accepts blocks of the `environmentaltech` and `etlunar` content mods (the pilot
  did this for `chancecubes:chance_cube` and it played; not checked for a 22-block list or for two types).
- That `block_energy` / `block_container` accept content-mod blocks and that the content menu types open with the
  container's slots (old route, same names).
- Which level is in place during `on_block_exploded` and `break_block` (`h::dimension` assumed to be the block's).
- Client-side reads in `click_action`: `h::player` and the sneak key on a client host; if they return nothing, the client
  decides as "not sneaking" and the server still acts correctly.
- `PlayerRef::set_velocity` and `set_abilities` on the single-player owner and on LAN guests.
- `strike_lightning` being refused by a mod's `lightning_strike` cancel (the rod then still gains the pulse, as the old
  code ignored the bolt result).
- Whether the game's `ENERGY` / `ITEMS` providers for our own block answer while it is out of the world for its tick (a
  pipe pulling in the same tick).
- The registry's first-tick gap after load (behaviour differences).
