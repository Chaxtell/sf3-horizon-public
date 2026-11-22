# Conversion note: `native/11_sf3_rftools` -> `mods/sf3_rftools` (2026-11-20)

COMPLETE conversion (third round: Screens, Screen Controller, hit blocks and the screen modules, drawn in the world through the stable `block_entity_submit`). Nothing was run in game. SDK build 0a875da. Needs the content mod `rftools` on in the instance.

Files: `src/runtime.rs` (byte-identical to the old one, `cmp` ok), `src/sf3_host.rs` (byte-identical to `mods/sf3_host`), `src/lib.rs`
(Hooks, Parts, registration, infusion carried through placement/break/loot), `src/machines.rs` (ticks), `src/clicks.rs` (item clicks, Syringe),
`src/env.rs` (Environmental Controller), `src/slot_rules.rs` (menu rule), `src/host_ext.rs`, `src/glue_tests.rs`. Second round, one file per group:
`src/ender.rs` (Endergenic, Pearl Injector, Ender Monitor), `src/protector.rs`, `src/logic.rs`, `src/remote.rs` (Remote Storage and the Modular Storage link),
`src/scanner.rs`, `src/elevator.rs`, `src/teleport.rs` (Matter Transmitter, Receiver, Dialing Device, porters), `src/builder.rs`, `src/shield.rs`. Third round: `src/screens.rs`.

One block entity type `sf3_rftools:machine` carries every converted block; the tick finds the machine from the block at its place. Old
per-block ids (`rftools:coalgenerator` ...) are gone, so saved old machines are not migrated. Ints in the entity's NBT are as before
(`energy`, `infused`, `burning`, `net`, `modes`, `next`, `speed`, `cap`, `matter0..2`, `timer`, `radius`, `bounds`, `sig`, `cost`, `mask`, `age`;
Strings `recipe0..`, `dest`).

## Converted

Coal Generator, Machine Infuser, Powercells (simple, normal, advanced, creative: pools by card, side modes, cost factor), Crafters 1-3,
Modular Storage (module and filter slots, overflow, comparator), Spawner with Syringe, Matter Beamer (wrench link), Environmental Controller
(modules, Peaceful, No Teleport, flight, potion effects), and for every converted infusable item: the infusion carried through placing,
breaking and explosions, and the "Infused: N%" tooltip.

Second round: Endergenic, Pearl Injector, Ender Monitor (pearls in flight, charge logic, pulses, injector stock and launch); Block Protector (wrench
picking, break and blast protection); logic blocks (Timer, Counter, Sequencer, Redstone Transmitter and Receiver, with their redstone output);
Remote Storage and the Modular Storage's link to it; Storage Scanner; Elevator; Matter Transmitter, Receiver, Dialing Device and the Charged Porters
(energy as the `sf3:energy` component); Builder (quarry cards, chunk ticket, buffer); Shield projectors T1-T4.

## Screens: the world-text route (third round)

A stable route exists, so nothing is degraded to a text display entity or the action bar. `block_entity_submit` (client, once per frame in view, then
`draw.keep()`) gets `BlockEntityDrawContext::text` (a sign's letters, `Text`, colour, glowing/outline; pose scaled `px, -px, px`) and `quad` (a
white-concrete sprite tinted for the panel and the bars). The server writes the lines into the screen's entity (Strings `l0..l10`, Ints `c`, `b`, `k`,
`n`, `on`, `face`, `size`, marker `scr`), `block_entity_update_tag` sends only those and `x::sync` resends them (at most every 20 ticks), exactly as
storage_qol's drawer fronts and immersive's wire nodes do. `block_entity_render_bounding_box` widens the box for 2x2 and 3x3 screens. Since every machine
shares one entity type the hooks fire for all of them: non-screens call `keep()` and return, and the update tag is sent only for entities with `scr` 1.

| Old attach point | New | Notes |
|---|---|---|
| `block_entity_tick` for `SCREEN`, `CREATIVE_SCREEN` | `screens::screen_tick` (arm in `block_entity_tick`) | cost, power, lines, sync |
| `SCREEN_CONTROLLER` tick | `screens::controller_tick` | claims screens, pays `cost x 20` every 20 ticks; range grows with infusion |
| `SCREEN_HIT` tick | `screens::hit_tick` | looks for its screen every 40 ticks, removes itself when none |
| `native_right_click_block_v2` (screen, hit, controller, `screen_module_point`) | `clicks::claims` arm `Click::Screen`, and `Click::Point` for sneak + a target module on any block | the client claims from the block, held id, sneak, and (hit blocks) the screen's client copy |
| `native_place_block` | `ItemPart::on_block_placed_by` (`screens::placed`) | face from placer yaw, size 1 |
| `native_destroy_block` | `Hooks::break_block` (`screens::broken`, `controller_broken`) | hit cells go, master shrinks back to 1 |
| `native_block_entity_update_tag` / `_render_bounding_box` / `_submit` | the same-named `BlockEntityPart` methods | see above |
| `native_block_entity_container` (screens) | `declare_container`, 11 slots, no menu | modules go in by clicks |

Modules converted: Text, Clock, Energy, Energy Plus, Fluid, Fluid Plus, Inventory, Inventory Plus, Counter, Counter Plus (the old runtime knows only these ten;
no redstone or button module existed in the old bundle).

## Hook by hook (converted part)

| Old attach point | New | Notes |
|---|---|---|
| `native_mods` | dropped | no Options > Mods entry (decided); `h::on(host, "sf3_rftools")` still asked everywhere |
| `native_block_entity` | `BlockEntityPart::block_entity` (`Machines`) | initial compound `energy` 0 |
| `native_block_entity_ticks` / `_tick` | `block_entity_ticks` / `block_entity_tick` | dispatch on the block at the entity's place; level in place is the entity's |
| `native_block_entity_energy` | `h::declare_energy` per block in `register` | same `m::buffer_for` numbers; faces `[max>0; 6]` as before |
| `native_block_entity_container` | `h::declare_container` per block | same slots, inputs, outputs; menu = block id, Powercells share `rftools:powercell` |
| `native_screen` | `BlockEntityPart::screen` | same layouts |
| `native_container_accepts` | none | no per-slot veto (see degraded) |
| `horizon_client_lib::menu::native_menu_slot_rules` (`slots.rs`) | `MenuPart::menu_slot_rules` (`slot_rules::Rules`) on `rftools:modular_storage`, `rftools:spawner`, `rftools:environmental_controller` | own container only |
| `native_right_click_block_v2` | `Hooks::right_click_block` (`clicks::claims` read-only on both sides, `clicks::run` on the server) | main hand only; client ends exactly the clicks the server takes |
| `native_place_block` | `ItemPart::on_block_placed_by` (`MachineItem`) on every converted infusable item | infusion, and a Powercell's energy and network, from the stack's `custom_data` |
| `native_destroy_block` | `Hooks::break_block` | notes what the machine carries (entity still there), a Powercell leaves its pool |
| `native_loot_drops` | `Hooks::loot_drops` | puts the note (or, for an explosion, the entity's data) on the drop |
| `native_tooltip` | `ItemPart::tooltip` (client) | yellow line under the name |
| `native_attack_entity` (Syringe) | `Hooks::attack_entity` | player from `acting_player`; the old check "kind is a known mob type" is now "not a player or item" |
| `native_analog_output` / `native_has_analog_output` (Modular Storage only) | `BlockPart::analog_output` / `has_analog_output` on `Machines` | reading kept in `machines::STORAGE_LEVEL` by level name and place |
| `native_potential_spawns` | `Hooks::potential_spawns` | Peaceful area, monsters only |
| `native_ender_pearl_teleport`, `native_chorus_fruit_teleport` | `Hooks::ender_pearl_teleport`, `Hooks::item_consumption_teleport` | No Teleport area; level from `h::dimension` |
| `native_server_tick` (flight lapse) | `Hooks::server_tick` (`ServerTickEnd`) -> `env::lapse` | time from the overworld's game time |
| `native_lifecycle` world close | `Hooks::world_lifecycle` | clears pools, storage levels, areas, flight, break notes |
| `native_right_click_block_v2` (second round) | `clicks::claims` / `clicks::run` gained arms | Endergenic and Injector and Monitor (`ender`), Protector and the picked wrench on any block (`protector`), logic blocks (`logic`), Remote Storage (`remote`), Scanner, Elevator, Transmitter group, Builder, Shield; a plain click on a Modular Storage first runs `remote::look` (server) |
| `native_block_signal` / `native_is_signal_source` | `BlockPart::block_signal` / `is_signal_source` on `Machines` | weak power only; Ender Monitor 15 while pulsing (`ender::monitor_signal`), logic blocks their level on their output side (`logic::signal`); both from tables, no world read |
| `native_destroy_block` (`harvest_blocked`) | `Hooks::break_block` returning `Flow::Cancel` | `protector::harvest_blocked` first; then the table clean-ups, `remote::unlink_for_break`, `builder::release`, `shield::release` |
| `native_explosion_detonate` | `Hooks::explosion_detonate` | `protector::explosion` (blast size is a TNT's: the source is not told) |
| `native_place_block` (logic facing) | `ItemPart::on_block_placed_by` (`MachineItem`) | `logic::placed`: out side from the placer's yaw; the item part is also registered for logic blocks |
| `native_loot_drops` (injector) | `Hooks::loot_drops` | the Pearl Injector's pearls fall with it (stacks of 16); explosions also run the forget and release steps |
| `native_use_item` (porters) | `ItemPart::use_item` (`Porter`) | main hand, server only; replaces the old block-click stamp: the block click is the block's (`right_click_block` Success ends it) |
| `native_item_energy_buffer` (porters) | `h`-style `x::declare_component_energy` (`ITEM_ENERGY` over the Int component `sf3:energy`) + `Hooks::component_types` | capacity 200,000 / 1,000,000, 2,000 in |
| `native_server_tick` (shield clean-up queue) | `Hooks::level_tick_post` -> `shield::orphan_tick` | per level, as the trap list says |
| `native_block_entity_*` for the new blocks | same `Machines` Part, new arms in `block_entity_tick`, `container`, `screen_of` | only Builder and Remote Storage have a container and a screen |
| `native_menu_slot_rules` | `slot_rules::Rules` on `rftools:remote_storage` (slots 0-3 take tier modules) and `rftools:builder` (slot 0 takes `rftools:shape_card*`) | |
| `native_lifecycle` world close | `Hooks::world_lifecycle` also clears `ender`, `protector`, `logic`, `remote`, `scanner`, `teleport`, `shield` | |

## `host_ext.rs` functions (merge into `sf3_host` after the wave)

Names and signatures shared with storage_qol / charset / endgame / draconic kept where they exist.

| Signature | Wraps | Replaces |
|---|---|---|
| `game_time(host, dim) -> u64` | `LevelRef::game_time` | `game.world.game_time` (same as storage_qol) |
| `is_plain(&ItemStack) -> bool` | damage 0 and no component changes | `plain` (same) |
| `hand_item(host, player, hand) -> Option<ItemStack>` / `set_main_hand(host, player, Option<ItemStack>) -> bool` | `LivingRef::hand_item` / `set_hand_item` | `game.held()` / `held_mut()` (same) |
| `max_stack_of(host, id) -> u32` | `h::max_stack` | `native_max_stack_size` (same) |
| `craft(host, dim, matrix) -> Option<ItemStack>` | `LevelRef::recipe_for` (`minecraft:crafting`, 3x3) | `recipes().craft` (same as endgame) |
| `craft_leftovers(host, dim, matrix) -> Vec<(String, u32)>` | `RecipeMatch::remainders` | `recipes().remainders` |
| `update_neighbors` / `update_output(host, dim, pos) -> bool` | `LevelRef::update_neighbors` | `native_update_*_neighbors` (same as storage_qol) |
| `spawn_item(host, dim, stack, at, motion) -> bool` | `spawn_item_with_motion` | `game.spawn_item` (same as storage_qol) |
| `state_block(level, state) -> Option<String>` | `LevelHost::state_string` | same as storage_qol |
| `item_slot(host, dim, pos, slot) -> Option<ItemStack>` | `BlockEntityRef::item_slot` | reading another entity's slot (same as storage_qol) |
| `players_in(host, dim) -> Vec<PlayerRef>` / `position(host, player)` | `online_players` / `EntityRef::position` | `riders_in` (same as draconic) |
| `set_data_int` / `set_data_str` / `data_int` / `data_str` (stack `custom_data` keys) | `apply_components` custom_data merge | `set_stack_int`, `put_stack_str`, `gets_data` |
| `consume_main_hand(host, player, n) -> bool` | `ItemStack::shrink` + `set_hand_item` | `game.consume_held()` |
| `side_signal(host, dim, pos, side) -> i32` | `LevelRef::signal(neighbour, direction)` | the old `side_signal` (reads one side; exact now) |
| `rotation(host, player) -> Option<[f32; 2]>` | `EntityRef::rotation` | the acting player's yaw/pitch (same as xutils `yaw`/`pitch`) |
| `be_items(host, dim, pos, n)` / `be_set_items(host, dim, pos, &changes)` | `BlockEntityRef::item_slot` / `set_item_slot` in one transaction | `native_with_mod_block_entity` on another entity's items (same as draconic) |
| `is_air_at(host, dim, pos) -> bool` | block id is air, cave air, void air or unknown | `is_air_at` (same as xutils) |
| `teleport_player(host, player, dim, pos, yaw, pitch) -> bool` | `EntityRef::teleport_to_level` | `native_teleport_player` (same as draconic) |
| `has_block_entity(host, dim, pos) -> bool` | `host.block_entity` | same as endgame |
| `container_slots(host, dim, pos, face)` / `container_extract(host, dim, pos, face, slot, max)` | `LevelRef::capability(ITEMS)` size, amount, resource, extract | `native_container_slots`, `native_extract_item` (same as endgame) |
| `component(stack, id)` / `set_component(stack, id, tag)` | `ItemStack::components` / `apply_components` | stack data of the porters (same as draconic) |
| `declare_component_energy(r, item, component, capacity, rate)` | `Registrar::item_capability(ITEM_ENERGY)` | `native_item_energy_buffer` (same as endgame) |
| `force_chunk(host, controller, dim, owner, chunk, hold)` / `register_ticket_controller(r, name)` | `ChunkRef::set_mod_forced` / `register_ticket_controller` | `native_force_chunk` (same as xutils) |
| `machine_break(host, dim, pos, tool) -> Option<Vec<ItemStack>>` | `LevelRef::destroy_block` | `native_machine_destroy_block` (same as xutils) |
| `hardness(host, dim, pos) -> f32` / `property(host, dim, pos, key)` | `HostBlockStates::destroy_speed` / `LevelRef::block_property` | block hardness and `native_block_property` (same as xutils/endgame) |
| `set_enchants_in(stack, component, &levels) -> bool` | `apply_components` | `set_crafting_enchantments` (same as draconic) |
| `day_time(host, dim) -> i64` | `LevelRef::day_time` | `game.world.day_time` (Clock module) |
| `custom_name(&ItemStack) -> Option<String>` | `minecraft:custom_name` component | `stack.custom_name()` (module labels) |
| `sync(host, pos)` | `ServerHost::block_entity_sync` | `native_block_entity_sync` (same as storage_qol, utility) |
| `energy_at(host, dim, pos, side) -> Option<(u32, u32)>` | `ENERGY` capability amount, capacity | `native_energy` |
| `fluid_tanks(host, dim, pos, side) -> Option<Vec<(Option<String>, u32, u32)>>` | `FLUIDS` capability, every slot | `native_fluid_tanks` |
| `draw_quad(draw, sprite, corners, tint)` / `draw_text(draw, text, rgb)` | `BlockEntityDrawContext::quad` / `text` | `native_draw_quad` / `native_draw_text` |

## Behaviour differences

- **One entity type for all machines** (`sf3_rftools:machine`); old `rftools:*` entity ids are not migrated.
- **Powercell wrench side** is the face really clicked (`click.hit.face`); the old port used the face toward the player's eyes.
- **Clicks write with `be_merge`** (changed keys only), never `be_update`, so a machine's item slots are never rewritten from a stale read.
- **Syringe**: any entity but a player or item entity takes the essence (the old code asked the mob table).
- **Environmental Controller** gives potion effects as ambient, no particles, to every player (old host got hidden effects); players come from
  `online_players` of the controller's level (the old code scanned a list of riders). Flight can now be given to the single-player host.
- **Matter Beamer -> Spawner**: the spawner's slot is read and its matter merged through the adapter (`item_slot`, `be_merge`) instead of one
  closure on both entities; nothing else changed.
- Explosions: the drop reads the entity in `loot_drops` (the old code did the same through `native_loot_drops`); not checked that the entity is
  still readable there.
- A creative break leaves a break note unused; it is dropped after 1200 ticks or by the next break at the place.
- **Second round, shared**: other machines are read and written with `be_data` / `be_merge` (changed keys only) and, for item slots, `be_items` / `be_set_items`;
  no closure runs on two entities at once.
- **Teleports across levels**: the receiver is read and paid through its own block entity wherever its chunk is loaded (the old code kept a table of receivers
  seen and a debt table for other levels); a receiver in an unloaded chunk says "The destination receiver is not loaded". The Dialing Device still lists
  receivers from a table their ticks fill (fresh for 100 ticks).
- **Porter energy** is the Int component `sf3:energy` (the old one was the engine's item energy); old porters in saved worlds start empty.
- **Logic blocks** read their input with `LevelRef::signal` on the input side; the old "own output taken away" sampling is not needed.
- **Storage Scanner** finds inventories by asking every position of the cube (4 to 20 blocks) for an item handler, cached 20 ticks (a level's block entities
  cannot be listed): a radius-20 click asks about 69,000 positions once. Items it takes that do not fit are thrown at the player instead of at the scanner.
- **Shield filter**: the engine gives no spawn category, so "hostile" is a list of 22 vanilla monsters, any other living thing is "passive".
- **Protector blast size** is always a TNT's (4); creeper 3, crystal 6 and fireball 1 are no longer told apart.
- **Builder** drops mined blocks into the buffer through `LevelRef::destroy_block` (loot rolled with a diamond pickaxe, Silk Touch or Fortune III by card).
- Shield and builder cells are placed with `h::set_block` (flags 3), the old code used flags 2.

## Degraded or dropped

0. Screen text has no drop shadow (the stable `text` has glowing and outline, no shadow); lines are drawn plain. Screen controller drop now carries its infusion (the old hook returned before that).

1. Options > Mods entry: dropped (decided).
2. **Charging an energy item in a machine's slot** (Coal Generator slot 1, Powercell slot): dropped. `ITEM_ENERGY` needs an `ItemPlace`, and the
   machine's slots are the tick's own copy while it ticks. The slot still holds items; nothing charges them. Old: `charge`.
3. **Hopper/pipe veto per slot** (`native_container_accepts`): dropped, as in storage_qol. A hopper can put a wrong item in a slot; players are
   still refused by the menu rule where there is one (storage, spawner, controller).
4. (done in round 2) Remote Storage link: converted in `remote.rs`.
5. (done in round 2) Block Protector break and blast checks: converted; the blast size is fixed (see differences).
6. **Hopper veto for the Builder slot** (`native_container_accepts`, slot 0 only shape cards): dropped like the others; the menu rule keeps players right.
7. **Shield filter classes** by a monster list, not the spawn category.
8. **Protector blast size** fixed at a TNT's.
9. **Scanner overflow** goes to the player, not to the scanner's top.

## Not converted

None. (The old function names `screen_tick` ... `block_entity_submit` are all in `src/screens.rs`.)

## In-game checklist (29 items; ids and expected numbers from `docs/PLAYTEST_LOG.md` 2026-11-17 and `SF3_REGISTRY.md`)

Instance with `sf3_rftools` and `rftools` on; creative unless said; status lines are in the action bar.
1. `/setblock ~ ~ ~2 rftools:coalgenerator`; `/data get block` shows id `sf3_rftools:machine`, `energy` 0. Right click opens the 2-slot menu.
2. Coal Generator: 2 coal in slot 0: burns 600 ticks at 60 RF/t (about 1,320 RF after 22 ticks); a `rftools:powercell_simple` beside it fills from it
   (about 9,780 RF in 40 ticks; the cell's side facing the generator must be in Input mode).
3. Infused generator (`data merge ... {infused:200}`): 834 ticks per coal at about 107 RF/t; broken in survival it drops carrying `custom_data.infused` 200;
   placed again the entity reads `infused` 200; the item's tooltip shows "Infused: 78%" in yellow.
4. Machine Infuser (`rftools:machine_infuser`) with RF and shards: put a generator item in slot 0 and 3 `rftools:dimensional_shard` in slot 1: the item
   gets `custom_data.infused` 3.
5. Powercell: two cells 6 blocks apart linked by one `rftools:powercell_card` (click each; blank card gets a network id) share 100,000 RF as 50,000 each;
   sneak with the card unlinks; sneak with an empty hand shows "Powercell: N RF, network ..." with the side modes. Smart Wrench (`rftools:smartwrench`)
   on a face toggles that side's mode (None, Input, Output) and the line names it. Stand close: the click goes to the block under the crosshair.
6. Powercell drop (survival, diamond pickaxe): a cell with 123,456 RF drops one item with `custom_data` `energy` 123456; placed, the cell reads 123,456.
7. Crafters `rftools:crafter1..3`: planks in hotbar slots 1 and 4, sneak click with an empty hand: "Crafter recipe 1: minecraft:stick x4"; 10 planks in
   the input become 20 sticks for 500 RF in the output slots; paper cycles the mode, a feather keep-one, a clock Slow/Fast.
8. Modular Storage (`rftools:modular_storage`): menu has a module slot, a filter slot and 254 stack slots; only `rftools:storage_module_tier_N` goes in
   slot 0; with a module, stacks fit up to its capacity; remove the module: stacks past capacity pop out above; a comparator beside reads 0 empty and rises.
9. Filter Module (`rftools:filter_module`) sneak-clicked on the storage: "Filter Module set to <first item>"; empty storage clears it.
10. Spawner (`rftools:spawner`, menu takes only `rftools:syringe`): hit a mob 10 times with the Syringe: "Mob: ..., essence level: 100%"; with matter
    and RF the mob appears above the spawner. Matter Beamer (`rftools:matter_beamer`): Smart Wrench the beamer, then the spawner (within 8 blocks): "feeds the
    spawner"; with a redstone signal and an item in its slot the spawner's `matter0..2` rise every 20 ticks.
11. Environmental Controller (`rftools:environmental_controller`): menu takes only the 17 modules; sneak click with an empty hand cycles radius
    (5, 10, 25, 50, 75, 100) and says the RF/t, sneak with a clock the height; with RF and a speed module a player inside gets Speed for 540 ticks.
12. Flight module: a survival player inside may fly; leave the area: flight and then slow falling 100 ticks after about 60 ticks. Peaceful module:
    no monsters spawn in the cylinder. No Teleport module: an ender pearl thrown out of or into the area is cancelled.
13. Save and quit, reload: energy, `infused`, Crafter recipes, Powercell `net` and modes, Modular Storage stacks are kept.
14. Endergenic (`rftools:endergenic`, 5,000,000 RF cap): two of them within 12 blocks; Smart Wrench the first, then the second: "Endergenic x,y,z sends its pearls to ...";
    a redstone pulse on the first charges it; a second pulse at the right moment (charge tick) fires a pearl; the second gains `RF_PER_HIT` RF; sneak wrench clears the link.
    Pearl Injector (`rftools:pearl_injector`) beside an Endergenic: an ender pearl click stocks it ("holds 1 pearls"); a pulse fires one through the Endergenic.
    Ender Monitor (`rftools:ender_monitor`) beside an Endergenic: sneak click cycles "a pearl is lost / fired / arrives"; a comparator or lamp gets a 2-tick pulse.
15. Logic blocks (`rftools:timer_block`, `counter_block`, `sequencer_block`, `redstone_transmitter_block`, `redstone_receiver_block`): the output faces away from the player
    that placed it; a lever on the back side starts it; Timer click cycles its delay, Counter its target, Sequencer its pattern (clock: its delay, sneak: once/loop);
    a Redstone Transmitter and a Receiver on the same channel (click both to the same number) pass the signal across any distance within loaded chunks.
16. Block Protector (`rftools:protector`, 500,000 RF): Smart Wrench on it: "Block Protector picked"; the wrench on a stone 3 blocks away: "Protected: 1 blocks"; mining it
    with a diamond pickaxe leaves it standing and costs about 2,000 RF; a TNT 1 block away spares it for about 3,000 RF while unprotected dirt beside it goes
    (log 2026-11-17 and the older Protector entry).
17. Remote Storage (`rftools:remote_storage`, 100,000 RF, a `storage_module_tier_1` in slot 0-3): a `storage_module_remote` right-clicked on it: "Remote Storage module linked to x y z";
    in a Modular Storage's slot 0 the storage shows the Remote Storage's stacks (`linked`, `rcap`); change a count in either and the other follows within a few ticks; breaking
    the linked storage in survival drops only the block and the module (no dupe).
18. Storage Scanner (`rftools:storage_scanner`, 50,000 RF): empty hand: "Scanner r8: N inventories ..."; sneak empty hand cycles radius 4, 8, 12, 16, 20; a held diamond requests
    a stack (100 RF) into the inventory; sneak with a held item stores it (20 RF); a first click with radius 20 may pause a moment.
19. Elevator (`rftools:elevator`, 100,000 RF): two 10 blocks apart in a column; empty hand rides up (sneak down); the block clicked pays 500 RF a block x (2 - infusion) / 2
    (log: 4,500 RF for 9 blocks); a block above the stop refuses with "The elevator stop is blocked".
20. Matter Transmitter (`rftools:matter_transmitter`, 200,000 RF) with `dest` `minecraft:overworld 50,100,90` by `data merge`, Matter Receiver (`rftools:matter_receiver`) there with RF:
    stand on the pad: "Start teleportation..." and you arrive at 50.5 101 90.5 within a few seconds; the receiver pays (log: 5,000 RF); an unpowered receiver says
    "The matter receiver has run out of power!". Receiver in the Nether (`minecraft:the_nether 0,70,0` after a `/data merge`): the same across levels.
21. Dialing Device (`rftools:dialing_device`, 50,000 RF) beside a transmitter: sneak empty hand picks the next receiver heard ("Receiver selected: ..."), an empty click dials the
    transmitter for 1,000 RF.
22. Charged Porter (`rftools:charged_porter`, give with `{"minecraft:custom_data":{dest:"minecraft:overworld 50,100,90"},"sf3:energy":200000}` or charge in a machine): right click a Matter Receiver
    sets the target ("Porter target: receiver at ..."); a right click in the air teleports for the whole teleport RF (the porter loses it, the receiver pays); with too little: "Not enough power: ...".
23. Builder (`rftools:builder`, 10,000,000 RF): a `rftools:shape_card_quarry` in slot 0 (only shape cards go in); it mines the area below, 8 + 20 x infusion blocks a tick, mined blocks
    become dirt, drops go to the 8 buffer slots and out to a chest above or beside it once a second; sneak with an empty hand cycles the area 8, 16, 32, 64, 128 and restarts;
    breaking it lets its chunk go.
24. Shield projector (`rftools:shield_block1..4`, 200,000+ RF): a wall of blue shield templates beside it; an empty hand composes (T1 up to 256 blocks, log), the templates vanish
    and shield blocks fill in; a second click within 2 seconds takes it apart and gives the templates back; sneak toggles visible/invisible, sneak with a clock steps the filter;
    preset 3 damages a passive mob on the shield (T3: 5 x 4 = 20 damage for 2,000 RF a hit, log 2026-11-18).
25. Break each new block in survival: the machine item drops (infused ones with `custom_data.infused`), a Pearl Injector's pearls come out as stacks, a projector's templates come back.
26. Save and quit, reload: logic blocks keep their delay and pattern, a composed shield keeps its record and refills, an Endergenic keeps its link.

27. Screens: `rftools:screen` placed facing you; `/data get block` shows `scr` 1, `face`, `size` 1. A `rftools:text_module` renamed in an anvil, put in by a click with it in hand: "Module put in line 1"; empty hand: "Screen 1 x 1: 1 modules, 0 RF/t, no power ...". A `rftools:creative_screen` shows the text on its front face at once (white on dark green panel, readable from the front, none from behind); a clock module shows the time and moves.
28. Screen Controller (`rftools:screen_controller`, 60,000 RF) within 32 blocks of a plain screen with an energy module: after about 40 ticks the screen turns on; the empty-hand click on the controller says "N screens connected"; energy module, sneak-clicked on a `powercell`/generator first ("Module points at ..."), shows "x/y RF" with a bar; energy plus shows "+n/t"; fluid, inventory (`inventoryplus` shows "N items used/slots" and a bar) and counter modules (on a `rftools:counter_block`) likewise; a target in another level: "Other dimension".
29. Big screens: sneak + `minecraft:clock` on a screen: 2 x 2 then 3 x 3, `rftools:screen_hitblock` cells fill to the right and up, the text grows over them; a click on a hit block acts as on the screen; break a hit block: the screen goes back to 1 x 1; break the screen: its hit blocks vanish; save and reload keeps size and lines (the first lines arrive with the chunk).

## Gates (run in `mods/sf3_rftools`, final lines)

- `cargo check`: `Finished `dev` profile [unoptimized + debuginfo] target(s) in 0.08s` (no warnings)
- `cargo test -- --skip the_slot_rule_module_ids_match_the_runtime_tables`: `test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out` for the
  doc-tests; the lib line above it is `test result: ok. 86 passed; 0 failed; 0 ignored; 0 measured; 1 filtered out` (71 runtime + 15 glue; 3 new screen tests).
  The skipped test reads the old bundle's `slots.rs`, which cannot live in the mod (`cargo horizon-mod check` refuses a `.rs` outside `src/`); decided: runtime.rs stays
  as it is and the gate is run with the skip. A plain `cargo test` ends `test result: FAILED. 83 passed; 1 failed`.
- `cargo horizon-mod check`: passes; notes only (`Block` is `TicketOwner::Block`, `ModContainer`, `ModEnergyBuffer`, `Screen` built with `..`; `Recipe` is our own runtime struct).
- `cmp` of `runtime.rs` against the old file and `sf3_host.rs` against `mods/sf3_host/sf3_host.rs`: no output (identical).

## Not checked

- Anything in game.
- Screens: that `block_entity_submit` / `block_entity_render_bounding_box` fire for a block entity type shared by 40 blocks (non-screens `keep()` an empty draw), that `block_entity_sync` called inside the entity's own tick sends the data written back after the tick, that `text` at scale `px` (about 0.01) is legible and faces out on all four sides (the yaw table is the old one), that the `scr` marker reaches the client copy, that a hit block removing itself in its own tick is allowed, the controller reading screens' stale table after a reload (screens re-register within 10 ticks), `minecraft:custom_name` being a plain String tag, `ENERGY` / `FLUIDS` capability answers on every face, and that `FakeHost` cannot run `screen_tick` (game time panics: no tick test).
- `py -I tools/mods_ids_check.py sf3_rftools` lists 2 missing ids (`rftools:storage_module_tier_` is a prefix, `sf3:energy` is a component), none of them screen blocks.
- That `block_entity_type(..).blocks(..)` takes the 15 `rftools` blocks of a content mod, and that `block_container` with 256 slots (Modular Storage)
  and 30 slots (Crafters) opens the content menus.
- Whether `RecipeInput::Crafting` matching (`recipe_for`) answers for the crafters' taught grids and what `remainders` returns for buckets.
- That the engine drops a mod container's slots when its block is broken, and that `loot_drops` still sees the entity after an explosion.
- `ItemStack::shrink` returning the remainder (used as in `sf3_host::insert_item`), and `h::be_merge` merging ints into a compound that also
  holds `Items`.
- `click.hit.face` as an index into `m::SIDES`; the Powercell pool state after a world reload (cleared on close; cells rejoin on their next tick).
- Client-side `claims`: `h::player` and the sneak key on the client host (if absent, the client lets the click go on; the server still acts).
- The Spawner reading `item_slot` 0 of another entity during the beamer's own tick.
- Second round, all of it: nothing ran in game. Specifically:
  - `BlockPart::block_signal` `face` meaning (taken as the side of our block that touches the reader, as the old comment) and that `LevelRef::signal(neighbour, direction)` reads the
    neighbour as the logic blocks assume; the logic output could be mirrored.
  - Cross-entity `be_merge` / `be_set_items` from another entity's tick (Endergenic pearls, Remote Storage sync, Dialing Device) and across levels (receiver in another level).
  - `ItemStack::set_count` and `shrink` used for `Counted` and `consume_main_hand`; `ItemStack` equality ignoring count by `with_count(1)`.
  - Chunk ticket under controller `quarry` and that a block entity tick may break blocks (`destroy_block`) in other chunks.
  - Shield `h::is_loaded` for unloaded chunks, `EntityRef::hurt("minecraft:generic")` as a valid damage type, entity lists in a box around the shape.
  - The `sf3:energy` component type registered by this mod and by endgame at once (the type list is deduplicated here, not checked there).
  - The Scanner's 69,000-position scan time at radius 20.
  - `explosion_detonate` before the blocks are rolled when the protector's entity is read.
