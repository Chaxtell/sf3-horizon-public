# Hook audit, 2026-11-18

Engine checkout `../horizon` at 04a2621. Read-only audit, no code changed. Sources: `docs/native-mods.md`, `docs/mods.md`, `crates/horizon-client/src/game/native_*.rs`, `crates/horizon-client/src/game/machines/native_*.rs`, `tools/native-hook-fragments/*.json`.

API numbers: a hook still in `tools/native-hook-fragments/` is unstamped and shows as `@API:name@`; its number is assigned at stamping. File:line is in `../horizon/crates/horizon-client/src/game/` unless a full path is given.

Verdicts: EXISTS = a function, hook or content field does the job; PARTIAL = it does part, or only via a workaround; MISSING = nothing found.

## Part A. HOOK_REQUESTS.md against the engine

| HR | Verdict | What exists (fn, file:line, API) | Would unblock |
|---|---|---|---|
| 1 Crafting remainder with changed stack | MISSING | Only static `crafting_remainder` item id (`crates/horizon-items/src/items.rs:220`); `native_prepare_item_craft` (API 290) edits the result only; `native_item_crafted` (API 161) only hears | Mystical Agriculture Infusion Crystal wear |
| 2 Thrown projectile for a mod item | EXISTS | Content `entity_type` json, template `minecraft:snowball` with `item` + `damage` (`docs/mods.md:389-411`), flies and breaks as a snowball; impact callback `native_projectile_impact` (`native_hooks.rs:9670`) with `native_hears_projectile_impacts` (:9647), API 136, gives hit position `at`. Not yet: dispenser throw | Chickens colored eggs and spawn eggs hatch a baby chick where they land |
| 3 Furnace fuel for a content item | EXISTS | Content item `components: {"minecraft:cooking_fuel": {"burn_time": N, "speed_multiplier": 1.0}}` (generic component patch, `docs/mods.md:247-262`; read at `crates/horizon-items/src/items.rs:1010`; furnace uses it, `crates/horizon-client/src/furnace.rs:91,230`). `minecraft:brewing_fuel` likewise | Charcoal Block 16000, Essence Coals. Check the block's own item takes the component |
| 4 Transient attribute modifier on a player | PARTIAL | `native_set_attribute_base` (`native_player_state.rs:454`), `native_set_attributes` loads a saved list incl. permanent modifiers (:487), `native_attribute_modifiers` lists transient ones (:417), `@API:player_attributes@`. No add/remove of one named transient modifier. Workaround: `native_run_command("attribute ... modifier add/remove")` | Supremium set sprint/air speed |
| 5 Menu over 256 slots / paged | PARTIAL | Server menus: `native_open_menu_with_input` (`native_menus.rs:167`, `@API:menu_input@`) shows up to 54 slots with input slots, `native_set_menu_items` (:149) repages, `native_menu_clicked` hears clicks (API 10). LAN guests only (see HR 17). Content menu types stay 1-256 slots (`docs/mods.md` Menu types), item containers clamp to 256 (API 370) | Actually Additions Large Storage Crate (351) |
| 6 Fishing loot | EXISTS | `native_loot_table_load(id, table)` edits any loot table JSON as it loads, so `minecraft:gameplay/fishing` can get extra pools without replacing vanilla's (`crates/horizon-world/src/loot.rs:730`, API 75); `native_loot_drops` (:9200) for drops | Pam's HarvestCraft 18 fish + Seaweed |
| 7 Buttons / list on a mod screen | EXISTS (buttons), list is DIY | `native_screen_click` (`native_hooks.rs:4256`) turns a press at a pixel into a menu button, `native_screen_tooltip` (:4269), `native_menu_button` (:4282) / `_v2` (:4300), API 20 and 51; draw with `native_screen_draw`; scroll via `native_screen_mouse_scrolled_pre` (API 93) | Pam's Market and Shipping Bin goods list |
| 8 Roll a loot table from a block entity | MISSING | Only `native_loot_odds` (:11732, odds, not a roll) and `native_machine_destroy_block` (HR 9). No `roll_loot_table` | Actually Additions Fishing Net |
| 9 Drops before the break | PARTIAL | `native_machine_destroy_block(pos, tool, collect)` (`native_machines.rs:36`, `@API:machine_breaking@`) breaks with a tool and returns the drops (`collect`), so a machine can store them. No query without breaking | Actually Additions Breaker, Farmer, Miner: drops go to the machine, no spill |
| 10 Entities in an explosion | PARTIAL | `native_explosion_knockback` (`native_hooks.rs:8514`, API 374) can zero the push by position and entity; damage can be cancelled in `native_living_incoming_damage_v2/_v3` (API 384, `@API:living_incoming_damage_v3@`) on `minecraft:explosion`, but not for the single-player host (HR 21). `native_explosion_detonate` (:8491, API 22) is still blocks only | Shock Suppressor protects entities |
| 11 Live container proxy for a mod block entity | MISSING | Only `native_container_accepts` (`native_hooks.rs:3489`, `@API:container_accepts@`), a per-item yes/no filter, and `native_block_entity_container` (API 16) static slots | Phantom Itemface, Player Interface, Item Viewer |
| 12 Redstone read and give | PARTIAL | Emit EXISTS: `native_block_signal` (`native_hooks.rs:1508`, API 38) can change the signal a block gives (it is not read-only), `native_is_signal_source` (:1533), `native_update_signal_neighbors` (:10899). Read of another block's output: MISSING; `native_neighbor_signal` (:10702, API 96) is the signal into a block | Phantom Redstoneface emit side |
| 13 `native_set_flight` for the host | MISSING | Unchanged: `native_travel.rs:332` queues, `native_flight_now` (:344) looks among hub guests only. Same for `native_teleport_player` (:55), `native_set_flying_speed` (`native_motion.rs:46`) | Supremium flight, Wings of the Bats, Simply Jetpacks, Travel Staff |
| 14 Per-entity energy buffer | MISSING | `native_block_entity_energy(block, energy)` (:3394, API 142) takes the block id only, asked once per block at table build | Ender IO capacitor levels |
| 15 Cancelable mob teleport | MISSING | `native_entity_teleport` (:5929, API 221) reports command teleports after the fact; pearl and chorus hooks are players only | Ender IO Inhibitor Obelisk |
| 16 Spawn hooks for mixin bundles | MISSING | Unchanged: `natural_spawning.rs:479` `spawn_hooks` is `!mods().is_empty()` | Ender IO Spawn Guard, Relocator (bundle 04 workaround stays) |
| 17 `native_open_menu` for the host | MISSING | Unchanged: `native_menus.rs:130` finds the player via `native_conn` (:36), hub guests only | Refined Storage Wireless Grid, Ender Pouch menu |
| 18 `native_register_dimension` | MISSING | Reads only (`native_server.rs:748,753`); engine `Dim` enum has 3 members (`game.rs:3156`) | RFTools Dimensions slice 6K, Roots Otherworld |
| 19 Player XP read and deduct | PARTIAL (nearly EXISTS) | Deduct/add: `native_give_levels` (`native_server.rs:1492`) and `native_give_experience` (:1478), API 101; `native_set_player_status` sets level/progress/total (`native_player_state.rs:249`, `@API:player_status@`); gain hook `native_player_xp_change` (API 394). Read: only through `native_player_compound` (:184; XpLevel/XpTotal), None inside a player's own turn | Draconic Disenchanter and Grinder XP costs |
| 20 `native_enchant_power` | PARTIAL | Tag `#minecraft:enchantment_power_provider` makes a block count as a bookshelf, 1 each (`stations.rs:681`); `native_prepare_item_enchant` edits the 3 costs. No 4.0/12.0 weight | Draconic enchant bonus blocks (low priority) |
| 21 Incoming damage for the host | MISSING (re-test) | Unchanged on the host path (`creatures.rs:4207 hurt_player_from`, `:4455 hurt_player_by` never call the hooks). HR 13's recheck says the host is now a hub guest in single player, so the server-player path may now serve it: re-test in game | Draconic armour shield, Feather Feet for the host |
| 22 Mob collision classes | PARTIAL | `collision_context_shapes` now knows `item`, `player`, `living` (non-player living), `other` (`docs/mods.md:679-720`, `horizon-world/src/collision_context.rs:37`); no hostile/passive split; docs say not all mob call sites converted. `native_world_lifecycle` still read-only | RFTools Shields "pass" filters |
| 23 Ender Dragon death + position | MISSING | Only `native_dragon_egg_form` (`native_hooks.rs:1278`, first egg). Dragon hits do reach `native_living_damage_pre/post` (:9486, :9510, `@API:living_damage@`), so a mod can watch its health reach 0 | Dragon Heart every kill |
| 24 Per-block mining state | PARTIAL | `native_break_speed` (`native_hooks.rs:2661`, `@API:break_speed@`): speed 0 means no crack progress at all, which is what the Chaos Crystal needs. Not asked for hardness -1 blocks; no hardness hook | Chaos Crystal until guardian dead |
| 25 Custom entity types with AI | PARTIAL | Content `entity_type` with template `minecraft:zombie`, `villager`, `wandering_trader` + `attributes` (`docs/mods.md:411-436`); goals via `native_register_goals` (`docs/native-mods.md:3738`); own drawing via `native_mob_submit`; spawn via `native_spawn_mob` / `native_summon` (API 37, 59); thrown projectile type with impact (HR 2). No flying or ghast-like template, no boss parts | Chaos Guardian, Guardian Crystals, guardian fireballs |
| 26 Fluid transfer between blocks | EXISTS | `native_move_fluids` (`machines/native_fluids.rs:610`, API 55) | Draconic Fluid Gate |
| 27 `native_living_death` with mixin-only | MISSING | Unchanged: `creatures.rs:1663` `mob_death_canceled` returns early on `mods().is_empty()` (bundle 13 injects there) | Chaos Guardian death |
| 28 Reads in another dimension | MISSING | `native_energy` (`machines/native_energy.rs:136`), `native_fluid_tanks` (`native_fluids.rs:420`), `native_container_slots` (`native_items.rs:115`) all return None for another dimension | RFTools Screen modules |
| 29 Bow keyed on `minecraft:bow` | MISSING | Unchanged: `use_hand.rs:357`, `using_item.rs:117,213` compare the item id | Draconic Wyvern/Draconic Bows |
| 30 Accessory slots | MISSING | Not in the engine; `docs/modpacks.md:179` lists "accessory slots" as a planned built-in API (0.4) | Botania baubles |
| 31 Persistent data and chat for the host | PARTIAL | `native_player_persistent_data` / `native_set_player_persistent_data` (`native_player_state.rs:506,518`, `@API:player_persistent_data@`) use `native_place`, which finds hub guests; with the host a hub guest (HR 13 recheck) this likely works, verify. `native_player_chat` (API 399/v2) is dispatched from the server layer (`entry.rs:159`), unverified for the host | Botania relic binding, Corporea chat requests |
| 32 Damage hooks v2/v3 in a mixin build | MISSING | Unchanged: `mace.rs:211`, `native_damage.rs:21` gate on `mods().is_empty()`; v1 works | Blood Magic Sacrifice Pack |
| 33 Fishing wait + forced spawn | MISSING | `native_fishing_medium` (`native_hooks.rs:7893`, `@API:fishing_medium@`) has `lure_ticks` but is never asked for water; `native_potential_spawns` (:6378, API 388) cannot skip spawn rules | Botania Allure and Bloodthirst |
| 34 Host login and first join | PARTIAL | `native_player_load_from_file(player, name, dir)` (`native_hooks.rs:8693`, API 323) is heard for the integrated server's owner too, on every join; `native_has_played_before` (`native_server.rs:788`, `@API:join_leave_helpers@`). A mod keeps its own `<uuid>.<suffix>` marker in `dir` for the starting kit. `native_player_login/respawned/jump` still guests only (`lan.rs:2127`, `lan_actions.rs:4208,5079`) | InitialInventory kit, Achievement Book hand-out |
| 35 Credit a kill to a fake player | PARTIAL | `native_hurt_entity` (`native_entities.rs:417`, `@API:hurt_entity@`) takes an attacker entity id; `native_set_player_fake` / `native_expect_fake_player` (`native_view_distance.rs`) make a client-less bot player that can be that attacker; `native_use_as_player` (`native_machines.rs:102`, `@API:fake_player@`) | Mob Grinding Utils Spikes/Saw, Killer Joe |
| 36 Fixed dimension ids | MISSING | Same as HR 18; no `data/<ns>/dimension` loading | The Beneath, Scanner, XU2 Quarry |

Totals: EXISTS 5 (2, 3, 6, 7, 26), PARTIAL 13 (4, 5, 9, 10, 12, 19, 20, 22, 24, 25, 31, 34, 35), MISSING 18. HR 6 also needs a check that a `loot_table_load` pool on `minecraft:gameplay/fishing` works in a mixin-only build (the hook is in `horizon-world`, dispatched wherever tables load).

## Part B. Per-hand hooks in the bundles (bundle 04 skipped)

Which hooks are per hand (from `native_hooks.rs` doc comments and `use_hand.rs`):

- `native_right_click_block` v1 (:8463, API 21): "once per hand", asked before the held-item check, so it runs for an empty hand too. `native_right_click_block_v2` (:7823, `@API:right_click_block_v2@`) adds `hand`.
- `native_interact_entity` v1 (:2602), `native_entity_interact_specific` (:2577), `_v2` (:7803, with `hand`): once per hand.
- `native_use_item_on` (:8156) and `native_use_item` (:8197): called inside one hand's turn (`use_hand`, `use_hand.rs:231-234`), only when that hand holds an item; `stack` is that hand's stack. `game.held()` and `consume_held()` follow the acting hand; `native_held()`, `game.selected`, `main_hand(game)` always mean the main hand.
- `native_left_click_block`, `native_attack_entity`: not per hand.

| Bundle | Per-hand hooks injected | Gates on `Hand::Main`? | Visible double act? |
|---|---|---|---|
| 01 skyblock | `right_click_block` v1, `use_item` | Yes: book open after `game.hand != Main` return (`glue.rs:537`); `use_item` gated (:510) | No |
| 02 exnihilo | `right_click_block` v1 | Yes (`glue.rs:430`). Silkworm path before the gate uses `held_item(game, game.hand)`, so each hand acts only on its own item and the leaves turn infested after the first | No |
| 03 storage_qol | `right_click_block` v1, `use_item`, `use_item_on`, `left_click_block` | Yes: `click_block` (:601), `transporter_click` (:1038), `chest_upgrade` (:980), drawer sneak (:745). `use_item_on` acts on `stack`; `use_item` only claims | No |
| 05 farming | `right_click_block` v1 + v2, `interact_entity` v1, `use_item`, `use_item_on`, use start/tick | Yes: v1 (:647,670), v2 harvest (:1627), `interact_entity` (:720), `use_item` (:622). `power_click` is hand-explicit (ER wrench Off, Yeta Main) | No |
| 06 endgame | `right_click_block` v1, `use_item` | Yes: every branch gates (`tool_click` :3577, `cycle_click`, `settings_click`, `energy_click`, `fusion_click`, `infuser_click`, `fluid_grid_click`, `encode_click`, `monitor_click`, `link_click`, grid sneak craft :1132,1153) | No |
| 08 immersive | `use_item_on` only | Not gated; acts on `stack` only. Wire coil in both hands would run the two-step link twice | No in normal play |
| 09 botania | `right_click_block_v2`, `use_item`, `use_item_on` | Yes in v2 (:705). `use_item` acts on `stack` but writes the main slot (`game.selected`): see act-on 3 | No double; a wrong-slot bug |
| 10 bloodmagic | `right_click_block_v2`, `use_item`, `use_item_on`, finish | Yes in v2 (:552). `use_item`/`use_item_on` act on `stack` | No |
| 11 rftools | `right_click_block_v2`, `use_item`, `attack_entity` | Yes in v2 (:667) | No |
| 12 envtech | `right_click_block_v2` | Yes (:899): status lines once | No |
| 13 draconic | `right_click_block_v2`, `use_item` | Yes (:495); `use_item` gated | No |
| 14 tinkers | `right_click_block_v2`, `use_item` | Yes (:594); `use_item` only claims | No |
| 15 logistics | `right_click_block` v1, `use_item` | Yes: `click` returns false off-hand (:598) before any action; `use_item` pouch line uses hand-aware `game.held()` | No |
| 16 utility | `right_click_block_v2`, `use_item`, `use_item_on`, `interact_entity_v2` | Yes in all four (:873-880, :896, :1360) | No |
| 17 xutils | `right_click_block_v2`, `use_item`, `use_item_on` | Yes in v2 (:352): status line once; `use_item` hand-aware (`consume_held`) | No |
| 19 player | `right_click_block_v2`, `use_item`, finish | Yes in v2 (:194): grave line and stacks once | No |
| 20 charset | `right_click_block_v2`, `attack_entity` | Yes (:125) | No |
| 21 chance | `right_click_block_v2` (no `hand` binding) | No gate, but reads `game.held()` (hand-aware): acts only when the acting hand holds the Scanner, so an empty off hand does not repeat the chat line | No (only with a Scanner in both hands) |
| 07 jei | none | n/a | n/a |

Result: no handler in a non-04 bundle would double-act in the normal case (empty or other item in the off hand). Bundles 01, 02, 03, 05, 06, 15 learned this in the early batches; the v2 bundles got `hand` explicitly. Not exercised in game: this is a code read, not a play test. Residual cases, all needing an item in both hands: 08 wire coils in both hands, 21 Scanner in both hands, 09 below.

## Act on (ranked by player impact)

1. HR 13, 17, 21, 31, 34 (host-only gaps: flight, menus, damage, chat, join). Re-test on 04a2621 first, since HR 13's recheck says the host is now a hub guest; if flight, menus and damage still fail they block the most player-visible items (Simply Jetpacks, Wireless Grid, Draconic shield, Botania baubles). HR 34 has a ready workaround: `native_player_load_from_file` + a marker file in `dir`.
2. Switch to hooks that now exist and delete workarounds: HR 3 (`minecraft:cooking_fuel` on Charcoal Block/Essence Coals), HR 6 (`native_loot_table_load` on the fishing table, Pam's fish), HR 2 (content thrown `entity_type` + `native_projectile_impact` for colored eggs), HR 7 (`native_screen_click`/`native_menu_button` for the Market list), HR 26 (`native_move_fluids`, port the Fluid Gate), HR 19 (`native_give_levels` for the Disenchanter), HR 24 (`native_break_speed` 0 for the Chaos Crystal).
3. Bundle 09 `use_item` (Terra Shatterer, Rainbow Rod, Tornado Rod): it takes `stack` from the acting hand but edits `game.inventory[game.selected]`. An off-hand rod with nothing or another item in the main hand claims the use and does nothing, or writes `enabled`/`ready`/`flying` data onto the main-hand item. Fix: use `game.held_mut()`.
4. Partial wins: HR 10 (Shock Suppressor via `native_explosion_knockback`, damage cancel for non-host), HR 9 (Breaker/Miner via `native_machine_destroy_block` with `collect`), HR 12 emit side (`native_block_signal` is writable), HR 35 (fake player attacker), HR 25 (zombie/villager-template guardian is possible, not a flyer).
5. Still need an engine change: HR 16, 27, 32 (all `mods().is_empty()` gates, one fix each), 14, 15, 29, 33, 18/36, 28, 8, 11, 1, 23, 30. Group the three `mods().is_empty()` gates into one request.
