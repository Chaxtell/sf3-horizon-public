# Hook audit 2026-11-20: host-unsafe reads in native bundles (rev 2)

Read-only. Scope: `native/*/mixins/*/*.rs`. Rev 1 wrongly treated `native_server_players()` as guests-only. Corrected premise (coordinator, checked: the integrated server always sets `self.lan = Some(host)`, `autosave.rs:105`; host elevators played 2026-11-17, PLAYTEST_LOG.md:656, 1058): it lists the single-player host on the server tick and in block-entity ticks; it is empty only INSIDE a player's hook.

Contexts, from the call chain up to the `horizon-mixin.toml` injection (name-based call graph, then read by hand; the graph over-approximates, so only chains confirmed in code are quoted):
- **S** = `server_tick`, `block_entity_tick`, `level_tick_pre/post`, `random_tick`: `native_server_players()` has everyone incl. the host; `game.player`, `native_player()`, `native_acting_player()`, `native_acting_id()` (0) are None there; `held()`/inventory for the host are stale.
- **P** = a player's hook (`right_click_block(_v2)`, `use_item(_on)`, `destroy_block`, `break_speed`, `attack_entity`, `hurt_enemy`, `release_using`, `inventory_tick`, `player_tick`, `loot_drops` of a kill, ...): `held()`, inventory, `selected`, `game.player` (host), `native_acting_*` valid; `native_server_players()` EMPTY; `native_run_command` does nothing.

BUG rules kept: (a) `native_server_players()` read in P; (b) `game.player`/`native_player()`/`native_acting_*` live-used in S; (c) `native_run_command` in P; (d) `held()`/inventory read in S for the host. Hits grepped: the seven requested reads plus `native_acting_*`, `native_player()`, `held_mut(` and `game.offhand` for rules (b) and (d).

## BUG

| bundle | file:line | read | context (call chain) | rule | what happens | suggested fix |
|---|---|---|---|---|---|---|
| 14 | glue.rs:1027, 1034 `grant_xp` | `held_mut()`, `native_acting_id()` | S: `server_tick` (1450-1461) -> `grant_xp(game, total)`; `HITS` filled by P hooks | d | Tinker tool XP lands on the host's stale held copy (a guest's hits level the host's tool) and the level-up message goes to id 0 | queue (player, xp) from the hook and apply it in the `player_tick` injection via `native_carried_stack`/`native_held_stack(uuid)` |
| 14 | glue.rs:1422 `player_tick` | `native_run_command` | P: `native_player_tick` -> `player_tick` (1402-1422) | c | Necrotic's Instant Health command is refused in the hook (11-19 log:1275 pass was probably Regeneration only: recheck) | push the line on a queue and run it in `server_tick` (bundle 16 `COMMANDS`) |
| 14 | glue.rs:1407 `player_tick` | `native_server_players` | P: `native_player_tick` | a | list empty, so `key` is always 0: every guest shares the host's key 0 (Magnetic, Necrotic, snapshots collide); host fine | `native_acting_player().entity_id`, 0 for the host |
| 14 | glue.rs:1127 `acting_entity` | `native_server_players` | P: `destroy_block` (tool break chain) | a | always 0 inside the break, so a guest is treated as the host | same: use `native_acting_player()` |
| 09 | glue.rs:3581 `soul_cross` | `native_server_players` | P: `loot_drops` of a player's kill | a | list empty, `find` fails, so Soul Cross never heals anybody (host included) | `native_acting_player().health` then `native_set_player_status` |
| 12 | glue.rs:535 `bind_beacon` | `native_server_players` | P: `right_click_block_v2` | a | list empty, `map_or(true)` makes every player an operator: a guest without permission takes over a beacon | `native_acting_player().permission` for guests; the host stays always-operator |
| 12 | glue.rs:576 `find_owner` | `native_server_players` | P chain: `destroy_block`, `loot_drops`, `right_click_block_v2` (same fn also runs in `block_entity_tick`, where it is fine) | a | a guest owner is not found in the player-hook calls, so breaking or exploding the beacon does not release its flight | in P use `native_acting_player()` when its uuid equals the owner |
| 13 | glue.rs:1921 `magnet_tick` | `native_server_players` | P: `inventory_tick` | a | `others` always empty, so the magnet also pulls items beside another player | read other players through `native_level_entities` or drop the check |
| 12 | glue.rs:718 `launcher_tick` | `native_player()` | S: `block_entity_tick` | b | the "cannot launch the host" notice is never shown (cosmetic) | drop the notice or show it from a `player_tick` hook |

## UNSURE

| bundle | file:line | read | context | verdict |
|---|---|---|---|---|
| 11 | glue.rs:2565 `riders_in` | `native_server_players`, `native_player()` | S: `block_entity_tick`; also P: `right_click_block_v2`, `use_item` | UNSURE: the list is cached for the game tick (`RIDERS`); if the first call of a tick is inside the host's click the cache holds only the window player, so guests are missing for that tick. Fix: do not cache when called from a P hook |
| 09 | glue.rs:3436 `entity_on_path` | `native_server_players` | S: `block_entity_tick`; also P: `use_item_on` (name chain) | UNSURE: fine on the tick; in a player hook the list is empty and a Tripwire lens does not see players. Check which hook runs the burst |
| 14 | glue.rs:1415 | `game.held()` | P: `player_tick` | UNSURE: valid in the host's own hook, but line 1412 chose `native_held_stack(uuid)`; use it here too for consistency |

## OK

| bundle | file:line | read | context | verdict |
|---|---|---|---|---|
| 01 | glue.rs:126,148,153 | `native_run_command` | S `server_tick` | OK |
| 01 | glue.rs:164, 250, 437 (`twerks`, `excavations`, `kit_tick`) | `native_server_players` | S `server_tick` | OK (host is listed; Twerk Sim, Veinminer played) |
| 01 | glue.rs:329 | `held()` | P `destroy_block`, and inside `native_as_player` in `excavations` | OK |
| 01 | glue.rs:476-481, 601-616 | `selected`, `inventory` | P `right_click_block`/`use_item` | OK |
| 02 | glue.rs:215, 221 | `native_server_players`, `game.player` | S `block_entity_tick` | OK: host in the list; the `game.player` fallback is dead, harmless |
| 02 | glue.rs:893 | `native_server_players` | S `level_tick_post` | OK |
| 02 | glue.rs:561,563 | `held()` | P `right_click_block` | OK |
| 03 | glue.rs:1041 | `held()` | P `right_click_block` | OK |
| 04 | glue.rs:6073, 6617 | `native_server_players` | S `block_entity_tick` | OK; the host branch at 6628-6646 (`native_player()`, `game.inventory`) is dead on the tick and not needed |
| 04 | glue.rs:925,1241,4653-4654,4799-4819,4953,4974-4975,5078; glue_b13a.rs:177,254-255 | `held/selected/inventory` | P (`right_click_block`, `use_item(_on)`, `break_speed`, `destroy_block`) | OK |
| 04 | glue_b10i.rs:340 | `native_run_command` | S `level_tick_pre` | OK |
| 04 | glue.rs:5735 `explosion_knockback` | `native_player()` | player's turn (`entity` None) | OK |
| 05 | glue.rs:592,1402,1681,1933,2191-2192,2250,2625,2680,3186; 893 `may_edit_front` | `held/selected/inventory`, `native_acting_player` | P `right_click_block(_v2)`, `use_item_on`, `perform_bonemeal` | OK |
| 06 | glue.rs:1947-1953,2115,2157,2175 | `held/inventory/selected` | P (`destroy_block`, `hurt_enemy`, `right_click_block`, `use_item`, `break_speed`) | OK (`runtime.rs:1188,1866` `.held()` is a local helper, not `Game`) |
| 07 | glue.rs:452; options.rs:128 | `game.player` | client screen | OK |
| 09 | glue.rs:714,1763-1798,1952,1971-1975,2099-2204,2264,2324,3383-3384 | `held/inventory/selected/offhand`, `native_acting_id` | P (`right_click_block_v2`, `use_item`, `item_damaged`, `destroy_block`, `left_click_block`, `inventory_tick`, `on_use_tick`); `take_mana` reaches `block_entity_tick` by name only | OK |
| 09 | glue.rs:2683 `corporea_take` | `native_acting_id` | P (Index, Crystal Cube); blocks pass an empty label so `who` is 0 on the tick | OK |
| 09 | glue.rs:3540 `apply_effect_tick` | `native_acting_player` | the hook runs the player's own effect tick (`entity` None) | OK |
| 10 | glue.rs:416,479,901,1528,1591,1983,2278,3712,3740,4098,4588,4666 | `held/inventory` | P | OK |
| 10 | glue.rs:840-852 `players()` | `native_acting_player`, `native_server_players` | S `block_entity_tick`: list gives the host; P `use_item_finish`: acting player gives it | OK (the `native_acting_player` branch is a harmless extra on the tick) |
| 10 | glue.rs:848, 1848, 2730 | `native_server_players` | S `block_entity_tick` | OK (1848: the host is moved by `client_tick_post`, played 11-18) |
| 10 | glue.rs:1779,1788 | `game.player` | C `client_tick_post` | OK |
| 10 | glue.rs:1953,1954,1975 `array_turret` | `native_run_command` | S `block_entity_tick` | OK |
| 10 | glue.rs:1581 `mob_killed` | `native_player()` | P (kill by the player) | OK |
| 10 | glue.rs:3999 `set_health` | `game.player` | P; `native_set_player_status` is tried first | OK |
| 11 | glue.rs:734-4082 (`*_click`, 1393, 2389, 2499, ...) | `held()` | P `right_click_block_v2`/`attack_entity` | OK |
| 11 | glue.rs:3078 | `native_server_players` | S `server_tick` | OK |
| 12 | glue.rs:576 | `native_server_players` | S `block_entity_tick` | OK there (the P chains are in the BUG table) |
| 13 | glue.rs:84-89,521,548,685,715 | `inventory/selected` | P | OK |
| 13 | glue.rs:230 | `game.player` | P `player_tick` | OK for the host; guest gets the 20.0 default (minor) |
| 13 | glue.rs:365 | `native_run_command` | S `level_tick_pre` (queued) | OK |
| 13 | glue.rs:1116, 2557, 3042 | `native_server_players` (+ dead `native_player()`) | S `block_entity_tick` | OK |
| 14 | glue.rs:338,409,781,962,1018,1045,1202,1303,1553 | `held()` | P | OK (played 11-19) |
| 14 | glue.rs:1347,1350,1368 | `native_run_command` | S `server_tick` | OK |
| 14 | glue.rs:1450 | `native_server_players` | S `server_tick` | OK |
| 14 | glue.rs:1497 `mob_drops` | `held()` after `native_held_stack` | P `loot_drops` | OK |
| 15 | glue.rs:588,700,818,846,1034; glue_gyth.rs:19 | `held()` | P | OK |
| 16 | glue.rs:287,298,402,448,719,750; glue_rt.rs:248 | `native_run_command` | S `server_tick` / `block_entity_tick` | OK |
| 16 | glue.rs:307,344,383,410,647,710; glue_rt.rs:241,338 | `native_server_players` | S `server_tick` / `block_entity_tick` | OK (host elevator played 11-17) |
| 16 | glue.rs:367 | `game.player` | C `client_tick_post` | OK |
| 16 | glue.rs:917-922,1575,1657; glue_rt.rs:104,370,469-470 | `inventory/selected/game.player` | P | OK |
| 17 | glue.rs:1145, 1753 | `native_server_players` | S `level_tick_post` | OK (the `native_player()` fallback at 1757 is dead) |
| 17 | glue.rs:1896,1964,1981,2006 | `game.player`, `inventory` | P `hurt_enemy`/`release_using` | OK |
| 19 | glue.rs:87 | `native_server_players` | P `loot_drops` | OK: falls back to `native_acting_player` |
| 19 | glue.rs:434-443, 466 | `inventory`, `game.player` | P `inventory_tick` | OK |
| 20 | glue.rs:61,128,145 | `held()` | P | OK |
| 21 | glue.rs:100,150 | `held()` | P | OK |
| 21 | glue.rs:281 | `native_run_command` | S `server_tick` | OK |

Not checked: whether `riders_in` and `entity_on_path` are reached from a player hook in practice (only the name chain was traced); the `held_mut` grep covered `held_mut(`, `game.offhand` and `.held()` only, not every other host-copy read.
