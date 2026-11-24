# Conversion note: `native/16_sf3_utility` -> `mods/sf3_utility` (2026-11-20)

Rules (`runtime.rs`, 59 tests) copied unchanged (`cmp` ok); `sf3_host.rs` byte-identical. No old test reads a file outside `runtime.rs`, so
no `--skip` is needed (`cargo test`: 66 passed = 59 runtime + 7 glue). Needs the content mods `mob_grinding_utils`, `torchmaster`, `funnels`,
`dimensionalcake`, `darkutils`, `ceramics`, `notenoughwands`, `simplyjetpacks`, `chisel`, `flatcoloredblocks`, `chickenchunks`, `packingtape`,
`shear`, `literalascension`, `randomthings`, `scanner`, `elevatorid`. No `[[native.mixin]]` row; the old Options > Mods entry is dropped (decided).

Source files: `lib.rs` (registration, hooks, the Parts `Machines`, `Contacts`), `machines.rs` (ticks of the machines), `rt.rs` (RandomThings),
`chunks.rs` (loaders, anchors, tickets), `clicks.rs` (block clicks, End Cake, scanners), `items.rs` (`Items` and `Dispenser` Parts), `chisel.rs`,
`packing.rs`, `world.rs` (contacts, elevators, spawns, tether, rain food, packs), `common.rs`, `host_ext.rs`, `glue_tests.rs`.

## Worn accessories: nothing to read from `sf3_player:baubles`

This bundle has no rings, magnets, belts or cloaks (those are 19_sf3_player, 12/13). Its only worn items are the SimplyJetpacks2 packs, which are
the chest armour slot (inventory index 38), read with `inventory_slots`. **No Attachment of `sf3_player` is read.**

New Attachments this mod owns: level attachments `sf3_utility:chunk_loaders` and `sf3_utility:rt_anchors` (list of strings, `{l: [..]}`, same
codec as before) and the player attachment `sf3_utility:rt_imbue` (one `name,until` string). New item component type: `sf3:energy` (int; the packs'
stored energy, same id as `sf3_endgame`: its `component_types` push is guarded by "if absent", merge them once).

## Hook by hook (35 old attach points)

| Old attach point | New | Notes |
|---|---|---|
| `native_mods` | dropped | no stable route (decided) |
| `native_block_entity` | `BlockEntityPart::block_entity` | first nbt (`age`, `bites`, `rate`, loader `shape/radius`, collector ranges...); 29 blocks, 27 entity types `sf3_utility:<name>` (same ids), registered once each with `block_entity_part(&kind, Machines)` |
| `native_block_entity_ticks` / `_tick` | `block_entity_ticks` / `block_entity_tick` | torches, tether and anti-slime now tick (they note themselves in `LANDMARKS`) |
| `native_block_entity_container` | `h::declare_container` | saw 6, fan 3, feeder 1, hopper 17 (items 1..16 out), auto-chisel 26, imbuing station 5 (+ `screen`) |
| `native_block_entity_fluids` | `x::declare_fluids` | hopper 16 000 (drain only), tank 32 000, sink 32 000 (drain only), funnel 1 000 |
| `native_block_entity_accepts_fluid` | dropped | no fluid filter in the API: the Hopper and Sink cannot be filled by pipes any more (orbs and standing players still fill them) |
| `native_block_entity_energy` | `h::declare_energy` | scanners 1 000 000, auto-chisel 10 000 |
| `native_right_click_block_v2` | `Hooks::right_click_block` | `clicks::plan` decides from block, held id and sneak on both sides; client cancels with `Success`, server runs `clicks::run`; main hand only |
| `native_use_item` | `ItemPart::use_item` | clay bucket (empty and 5 filled), Teleportation Wand, flat crafter, filter; server only; the old "claim the use that follows a block click" stamp is not needed (the click is cancelled) |
| `native_use_item_on` | `ItemPart::on_item_use_first` | chisels, crafter, carving tools, rope, Illumination Wand |
| `native_place_block` | `ItemPart::on_block_placed_by` | fan/plates facing, loader owner, collector outlet, packaged contents |
| `native_interact_entity_v2` | `ItemPart::item_interact_mob` | clipper, clay bucket on cow, Mob Swab |
| `native_destroy_block` | `Hooks::break_block` | loader/anchor release, detector forgotten, packaged block drops itself (Cancel) |
| `native_loot_drops` | `Hooks::loot_drops` | wither dust |
| `native_potential_spawns` | `Hooks::potential_spawns` | reads `LANDMARKS` |
| `native_block_entity_inside` | `BlockPart::entity_inside` on `Contacts` (10 blocks) | queues; `level_tick_post` of the level acts |
| `native_server_tick` | `server_tick` (clock) + `level_tick_post` (contacts, End Cake commands, anchor sweep) | no per-level work in `server_tick` |
| elevators (polled in `server_tick`) | `Hooks::player_jump`, `player_toggle_sneak` | no more polling of y |
| `native_ender_pearl_teleport` / `_chorus_fruit_teleport` | `Hooks::ender_pearl_teleport` / `item_consumption_teleport` | |
| `native_block_signal` / `_is_signal_source` | `BlockPart::block_signal` / `is_signal_source` on `Machines` | Timer, Entity Detector |
| `native_inventory_tick` (chest slot) | `Hooks::player_tick_post` -> `world::pack_tick` | thrust/flight, flux charging; guest/host split gone |
| `native_item_energy_buffer` | `x::declare_component_energy` over `sf3:energy` | |
| `native_tooltip` | `ItemPart::tooltip` | energy lines (read from the component), imbue name |
| `native_player_input` | `Hooks::player_input` | jump flag |
| `native_level_load` | `Hooks::level_load` | chunk tickets again |
| `native_dispense_item` | `ItemPart::dispense_item` on `Dispenser` | only on listed items (see below) |
| `native_player_tick` | `player_tick_post` -> `world::rain_food` | |
| `native_client_tick_post` | dropped | the host push workaround is gone: `set_velocity` pushes players |
| `native_living_entity_use_item_finish` / `_attack_entity` / `_living_experience_drop` | `living_entity_use_item_finish` / `attack_entity` / `living_experience_drop` | imbues |

## `host_ext.rs`

Same names and signatures as other mods' files where they exist (`hand_item`, `set_main_hand`, `spawn_item`, `game_time`, `position`, `view`,
`yaw`, `property`, `set_property`, `neighbor_signal`, `update_neighbors`, `biome`, `play_sound`, `players_in`, `player_dimension`, `entity_by_id`
(u32), `hurt`, `remove_entity`, `item_entities`, `set_item_entity`, `force_chunk`, `register_ticket_controller`, `declare_fluids` (5 args),
`fluid_tank/extract/insert`, `be_items`, `be_set_items`, `entity_nbt`, `merge_entity_nbt`, `discard`, `shrink_hand`, `count_items`, `take_items`,
`experience_orbs`, `experience_total`, `give_experience`, `food`, `set_food`, `add_effect_with`, `add_effect_to`, `player_name`, `player_of`,
`attachment_get/set`, `damage_main_hand`, `sync`, `explode`, `set_weather`, `teleport_player`, `rotation`, `world_height`, `give_or_throw`,
`declare_component_energy`, `component`, `set_component`, `velocity`, `sprinting`, `max_damage`, `is_plain`, `health_of`, `potion_of`,
`selected_slot`, `state_block`, `all_entities`, `mobs`, `tag_to_bytes/from_bytes`). New ones:

| Signature | Wraps | Replaces |
|---|---|---|
| `set_fire(host, entity, ticks)` | `EntityRef::set_remaining_fire_ticks` | `native_entity_set_fire` |
| `push(host, entity, delta)` | `velocity` + `h::set_velocity` | `native_entity_push`, `native_push_player`, the host-push queue |
| `item_energy_charge(host, &stack, amount) -> Option<(u32, ItemStack)>` | `scratch_slots` + `ITEM_ENERGY` `insert` | `native_item_energy_insert` |
| `item_energy(host, &stack) -> Option<(held, capacity)>` | same, rolled back | `native_item_energy` |
| `state_properties(host, dim, pos)` | `block_state_string` | state read for Packing Tape |
| `set_block_with(host, dim, pos, block, &props, flags)` | `set_block` + `set_block_property` | `native_set_block` with a state, `with_property` |
| `effect_ticks`, `flying`, `light`, `kind_of`, `is_baby`, `look`, `tick_slot_index`, `discard_item` | | small reads |
| `block_entity_data(host, dim, pos)` / `block_entity_replace(host, dim, pos, data)` | `BlockEntityRef::data` / `replace_data` | `native_block_entity_nbt`, `native_set_block_entity` |
| `take_experience(host, player, points)` | `xp add <name> -n points` | the deferred `xp add` |
| `state_property`, `property_in` | `state_string` | |

## Behaviour differences

- Saw and Fan use real entity boxes (`entities_in` on the cell / the fan's box) instead of points with a fudge; the Fan pushes players through
  the same call as mobs (a sneaking player is skipped).
- Vector plates push by adding to the velocity (any entity, players included); no 200 ms host-push queue.
- Elevators act at the jump / sneak event, not on a seen rise; teleport is `teleport_to_level`, not a command.
- Wands, the Auto-Chisel and the End Cake take the experience / move the player directly, not on the next server tick (the End Cake's
  `forceload` / `fill` / `tp` still go through commands, delayed 10 ticks).
- Jetpacks: flight is `may_fly` granted while fuel lasts; a pack that leaves the chest slot ends it on the player's next tick (not within 3
  ticks of a stale mark). Energy lives in the `sf3:energy` int component, not `custom_data.horizon_energy`: old packs in old worlds read 0.
- Packing Tape: the packed block entity is no longer SNBT text. `tile` holds `{id:"<block id>"}|<hex of its network NBT>`; the block entity's
  type id is taken as the block's id (right for chests, barrels, furnaces). A mod block entity's slots are not emptied first (only a vanilla
  `Items` list is), so a mod machine may drop its items when packed.
- Torches, tether and Anti-Slime are remembered once they have ticked this session (the SDK lists no level's block entities); a loaded
  chunk's torch protects from its first tick.
- Entity Detector counts every entity whose real box meets the box (players included).
- Imbue attack effects apply directly (`add_effect_to`), no deferred command.
- The Imbuing Station gets a `screen` of its own (4 inputs, output); the old bundle had none.

## Degraded or dropped

- Options > Mods list entry: dropped (decided).
- Hopper and Sink: pipes can no longer be refused non-xpjuice; they are drain-only blocks (the Sink cannot be filled by a pipe at all).
- Block Dispenser: the dispense hook is per item. It is attached to tags `minecraft:logs`, `planks`, `wool`, `sand`, `stone_bricks`, `c:cobblestones`,
  `c:stones`, `c:glass_blocks` and ten vanilla ids; other block items go through vanilla.
- The Ender Tether does not stop Endermen (their hook has no host); pearls and chorus fruit are stopped.
- Saw looting and beheading upgrades: still not applied (as before).
- Creeper clipping uses `explode(fire=false, blocks=true)`; the old call's fourth argument is not known to mean fire.
- Not converted: nothing from the old glue's function list was left out except the points above.

## In-game checklist (14 items; ids from `SF3_REGISTRY.md`, `PLAYTEST_LOG.md`)

1. `mob_grinding_utils:saw` + redstone, a zombie on it: hurt every 10 ticks; with `saw_upgrade_fire` it burns; click with an upgrade puts it in, sneak with an empty hand takes it out.
2. `mob_grinding_utils:fan` facing a wall: items and mobs in front are pushed; placed fan faces away from the surface you looked at.
3. `mob_grinding_utils:absorption_hopper`: drop items and XP orbs within 3.5 blocks: items in slots 1..16, orbs become xpjuice (status line on click); a hopper below pulls the items out.
4. `mob_grinding_utils:tank_sink` + `xp_tap`: standing on the sink fills it from your XP; the tap, powered, spills orbs.
5. `funnels:funnel` under a tank of water: fills to 1000 mB and puts a source block below.
6. `darkutils:timer` pulses (click: +100 ticks, sneak-click: -100); a lamp beside it blinks. `darkutils:feeder`: wheat in, cows within 8 blocks go into love.
7. `darkutils:trap_move*` push you (sneak: not), `trap_tile_*` hit; `mob_grinding_utils:spikes` hurt mobs (5).
8. `torchmaster:mega_torch` near a dark cave: no hostile natural spawns within 64 blocks once its chunk has ticked; `darkutils:ender_tether`: a thrown pearl lands on it.
9. `elevatorid:elevator_white` twice above each other: jump goes up, sneak goes down.
10. `notenoughwands:teleportation_wand` (4 XP) and `illumination_wand` (3 XP): "Not enough experience!" at 0 XP; wand lands on the sighted block.
11. `ceramics:clay_bucket`: right click water/lava/sand takes it, right click again puts it down; on a cow gives milk.
12. `chickenchunks:chicken_chunk_loader`: click empty-handed cycles radius, sneak-click the shape; chunks stay loaded after relog; breaking releases them.
13. `simplyjetpacks:jetpack_eio1` worn with energy: flight in survival, fuel drops while flying; `fluxpack_eio1` worn charges a held energy item.
14. `packingtape:tape` on a chest with paper in the inventory makes `packaged_block`; click puts the chest back with its items; `randomthings:imbue` drink then hit a mob (fire/poison/wither), `imbuing_station` menu crafts in 200 ticks.

## Played

2026-11-22/23, builds native-0a875da-c95837* and -ec7680fed557 (clean, no debug lines), SkyVoid, single player, survival unless said.

1. Pass: saw hurts a zombie every 10 ticks under redstone; fire upgrade burns; upgrade in by click, out by sneak with empty hand.
2. Pass for mobs and facing. Fan does not push item entities; it does push players (backlog).
3. Pass: items into slots, orbs into xpjuice, hopper below pulls items. Hopper renders as a black cube (backlog).
4. Pass after fix: the tap now drains the sink's NBT fluid and spills orbs. Orbs spawn inside the tap block (backlog).
5. Pass: funnel fills to 1000 mB and puts a source below.
6. Pass: timer pulses and +/-100 ticks; lamp blinks; feeder puts cows in love.
7. Pass after fix: move plates push continuously (contacts dedup per tick; the old "resting" rule dropped, touches arrive every tick); poison tile hits; spikes deal 5. Re-checked on the clean build: a pig moved 1.6 blocks in 30 ticks. Sneak-on-plate not played.
8. Pass: mega torch stops natural hostile spawns (Cursed Earth spawns still come, as its own spawner); a thrown pearl lands on the ender tether.
9. Pass: elevator jump up, sneak down (host jump through `host_jump`).
10. Pass: teleportation wand 4 XP, moves to the sighted block; illumination wand 3 XP, places a light block; "Not enough experience!" shows in the action bar at 0 XP.
11. Pass for water take/place and cow milk. Lava and sand not played.
12. Pass for radius cycling (action bar "Square, radius 3 (25 chunk(s)...)"). Sneak-click shape, relog and break release not played.
13. Jetpack: fuel drops while thrusting (80000 to 79808). Flight itself from the 2026-11-19 host flight proof; a double-tap jump cannot be sent across tool calls. Flux pack not played.
14. Pass for tape: chest packed (1 paper used) and unpacked with items intact. Imbue and imbuing station not played.
