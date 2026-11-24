# Conversion note: bundle 13 `sf3_draconic` -> `mods/sf3_draconic` (2026-11-20)

Converted by the recipe in `conversion_recipe.md`. Layout: `src/lib.rs` (Hooks, helpers), `gear.rs`, `machines.rs`, `clicks.rs`,
`loot.rs`, `portal.rs`, `reactor.rs`, `chaos.rs`, `worldgen.rs`, `parts.rs`, `host_ext.rs`, `glue_tests.rs`, `island.rs` (old pure
file; `comet_for_start` added), `runtime.rs` and `sf3_host.rs` (byte-identical copies, `cmp` passes). Data:
`data/sf3_draconic/worldgen/{structure,structure_set}/{chaos_island,ender_comet}.json`. No `[[native.mixin]]` row. Needs the content
mod `draconicevolution` (`mod.draconicevolution:true`). Fusion crafting and the energy infuser are bundle 06 (`sf3_endgame`), not
here; this bundle has the Upgrade Modifier, the reactor, the machines, gear and the End generation.

One block entity type, `sf3_draconic:machine`, carries all 27 machine blocks (3 relay + 3 IO + 3 wireless crystals, Disenchanter,
Generator, Grinder, Spawner, Draconium Chest, Rain Sensor, Potentiometer, Detector, Celestial Manipulator, Flux and Fluid Gate,
Reactor Core and Injector, Chaos Crystal, Pedestal, Receptacle, Upgrade Modifier). `Machines` is its `BlockEntityPart` and `BlockPart`;
the mod makes no `block_part` call (trap 1) and `glue_tests` checks the list has each block once (trap 2). Item Parts: `Placed` (Grinder,
Flux Gate, Fluid Gate, Chest item) and `Gear` (tools, armour, bows, capacitors, magnets, Info Tablet, Dislocators; disjoint from the
machine blocks, tested).

## Hook table (old attach point -> new)

| Old | New |
|---|---|
| `native_mods` | dropped (no Options > Mods entry) |
| `native_block_entity`, `_ticks`, `_tick` | `BlockEntityPart::block_entity`, `block_entity_ticks`, `block_entity_tick` (`machines::tick` dispatches by block id) |
| `native_block_entity_energy`, `_container` | `Registrar::block_energy` / `block_container` through `h::declare_energy` / `declare_container` (`parts::energy_buffer`, `parts::container`) |
| `native_screen` | `BlockEntityPart::screen` (`parts::screen_of`: Generator, Disenchanter, Chest) |
| `native_container_accepts` | none (see differences) |
| `native_block_signal`, `native_is_signal_source` | `BlockPart::block_signal`, `is_signal_source` on `Machines` |
| `native_player_tick` | `player_tick_post` (server): `gear::player_tick` (shield, flight, modifiers, night vision) |
| `native_living_incoming_damage` | `living_incoming_damage`: shield (`gear::incoming_damage`) and the Guardian's damage scale (`chaos::guardian_damage`) |
| `native_living_death`, `mob_death_canceled` | `living_death` -> `chaos::living_death` |
| `native_inventory_tick` | `ItemPart::inventory_tick` (capacitor charging, Magnet pull) |
| `native_use_item` | `ItemPart::use_item` (Info Tablet, Magnet toggle, capacitor mode, Dislocators); server only, main hand |
| `native_use_duration`, `native_release_using` | `ItemPart::use_duration`, `release_using` (bows) |
| `native_tooltip` | `ItemPart::tooltip` |
| `native_right_click_block_v2` | `right_click_block`: client `clicks::claims`, server `clicks::server_click` (Hoe, Binder, machines, reactor, Upgrade Modifier) |
| `native_place_block` | `ItemPart::on_block_placed_by` (`loot::placed`) |
| `native_destroy_block` | `break_block` (`loot::break_block`: spawner note, chest retention, crystal hold, portal off) |
| `native_loot_drops` | `loot_drops` (`loot::loot_drops`) |
| `native_break_speed` | `player_break_speed` (speed 0 for a held Chaos Crystal) |
| `native_dragon_egg_form` | `dragon_egg_form` -> `chaos::note_heart` |
| `native_level_tick_pre` / `native_server_about_to_start` / `native_player_tick` world drive | `level_tick_post` per level: `chaos::drive` (bars, crystals, implosions, hearts, crater carving) |
| `native_chunk_generate` | structure types `sf3_draconic:chaos_island`, `sf3_draconic:ender_comet` + JSON (`worldgen.rs`) |
| `native_run_command` queue for attribute modifiers | `LivingRef::add_attribute_modifier` / `remove_attribute_modifier` directly |

## `host_ext.rs` functions (all new; shared names repeat the other mods')

`hand_item`, `set_hand`, `is_plain`, `spawn_item`, `game_time`, `component`, `set_component`, `enchantments`, `set_enchants_in`,
`nbt_remove`, `entity_by_id` (i32), `player_of`, `position`, `eye`, `rotation`, `player_name`, `player_dimension`, `players_in`,
`teleport_player` (`EntityRef::teleport_to_level`), `teleport_entity` (`teleport_to`), `experience_level`, `set_experience_level`,
`add_levels`, `experience_orbs`, `all_entities`, `mobs` (living non-players: id, type, position, health, max health), `hurt`,
`set_health`, `set_attribute_base`, `remove_entity`, `set_modifier`, `drop_modifier`, `item_entities`, `property`, `neighbor_signal`,
`update_neighbors`, `set_block_flags`, `light`, `world_height`, `set_day_time` (`time set`), `set_weather` (`LevelRef::set_weather`),
`explode` (`LevelRef::explode`), `be_items`, `be_set_items`, `has_block_entity`, `move_energy` (two `ENERGY` handlers in one
transaction, the refused part goes back), `takes_energy`, `move_fluids`, `show_bar`, `hide_bar`, `drop_bar` (boss bars),
`burn_time` (`item_burn_time`), `remainder`, `smelts` (`recipes_of_type`), `is_monster`, `is_living`, `stack_to_nbt`,
`stack_from_nbt`, `spawn_mob_id` (`LevelRef::spawn_mob`), `lightning`.

## Behaviour differences

- **Hoppers and pipes** may put any item in any slot of the Generator, Disenchanter and Chest (old `native_container_accepts` vetoed
  non-fuel, non-smeltable and so on). Slot faces still limit which slots a pipe reaches; a bad item in the chest's smelting slots is
  simply not smelted; a non-fuel in the Generator is not burned.
- The one-stamp guard against a claimed block click's item use (`BLOCK_CLICK_AT`) is gone: the click ends with `Cancel` + `Success`.
- Armour speed, jump and step are attribute modifiers set in the player's own tick, not queued commands.
- Shield entries are keyed by player uuid and found by entity id; LAN-guest handling of the old bundle is gone (the API has no host/guest).
- Magnet pulls by teleporting item entities onto the holder; thrown items are told by `owner()`.
- XP orbs near a Grinder are aged through `set_experience_orb` as before; Magnets still do not pull orbs.
- Disenchanter: the enchantment's max level is not readable, so the cost uses level / level (the full share of `disenchant_cost`).
- Wireless binding tests "has an energy buffer on that face" (capacity above 0), not `can_insert`.
- The Chaos Guardian bar is one boss bar per crystal (`sf3_draconic:guardian_x_y_z`) shown to players in range; the old bar was per player.
- Messages to everyone (reactor, guardian, implosion) go through `tellraw @a`.
- Spawner "monsters only in the dark" uses a list of 30 vanilla hostile ids (the API gives the class of a live entity only); the
  Detector uses the live class.
- A crater is carved with `CLIENTS | KNOWN_SHAPE` (old flags 18); explosions use default settings.
- Ender Comets: spacing 63 chunks (about 1 start per 3,969 chunks, was 1 in 4,000), the comet is shifted so its midpoint is in the start
  chunk (a start is referenced only from chunks within 8), so positions differ from the old bundle's. Chaos Islands: same 10,000-block
  grid, none at the origin. Both are in the `sf3_draconic` namespace (`/locate structure sf3_draconic:chaos_island`), not `draconicevolution`.
  The crystal's block entity is made by the piece (`PieceContext::block_entity`); `ensure_crystals` stays as a safety net in the End.
- Weather is yes/no (no 0..1 levels); time is set with the `time set` command.

## Degraded or dropped

Dropped: Options > Mods entry; `native_container_accepts` vetoes; the block-click stamp; LAN host/guest special cases; the
`native_chunk_generate` hook (replaced, not dropped). Degraded: the items above. Kept shortcuts of the old bundle: no flight energy cost,
plain arrows only for bows, no draw pose.

Not converted: none left (every old function has a home above). Not checked in play: everything (workers do not run the game).

## Play checklist (14)

1. New End world: `/locate structure sf3_draconic:chaos_island` finds 10000 0 (also at 0 10000, never at 0 0); `tp` there: obsidian lens, crystal at y 80.
2. Ender Comet: fly the End at 500+ blocks from the origin; `/locate structure sf3_draconic:ender_comet` finds one; core obsidian, ore, trail of end stone.
3. Chaos Crystal: right-click says "shielded by its Guardian"; it cannot be broken (digging speed 0) until the Guardian dies, then breaking it starts "implode in 5 seconds" and carves a radius-32 crater.
4. Guardian: a Ghast named "Chaos Guardian" within 64 blocks, boss bar with health, 21 End crystals round the island (Guardian Crystals heal it).
5. Reactor (from the 2026-11-17 log): core + 4 Stabilizers 5 out round one axis + an Injector; right-clicks with `draconic_block`/ingots put fuel in, sneak-click charges, then activates; status line on an empty-hand click; a Flux Gate behind a Stabilizer passes the output.
6. Upgrade Modifier: `tool_upgrade_arrow_speed` in the main hand and a `draconic_bow` in the off hand gives `up_arrow_speed: 1`; cost comes from the block's RF.
7. Draconic Chestplate (powered): flight in survival; legs speed and boots jump/step modifiers; shield value on the armour tooltip; a lethal hit leaves 10 or 1 health ("last stand").
8. Draconium Capacitor: sneak-use cycles the mode (message); in mode 1 it charges the hotbar tools. Magnet: use toggles; active, drops within 8 blocks come to you.
9. Dislocator: first use binds, sneak rebinds, use teleports (20 uses); the Advanced one needs and spends an Ender Pearl.
10. Dislocator Pedestal/Receptacle/portal (from 17A of the log): a bound Dislocator in the Receptacle with an Infused Obsidian frame lights `draconicevolution:portal`; stepping in teleports; breaking a frame block puts it out.
11. Draconic Bow: draw 1.5 s with arrows takes about 240 RF and one arrow, the arrow flies; the Hoe tills a (2n+1) square at `up_dig_aoe` n.
12. Generator burns fuel and gives 1,000 RF/t to neighbours; Grinder kills mobs in its box; Stabilized Spawner takes a Mob Soul (right-click) and cores (tiers); a mob kill by a player may drop a `mob_soul`.
13. Draconium Chest: contents and RF survive breaking and placing; smelting slots work with a capacitor.
14. Crystals: Binder links two crystals (range, link count), sneak-click cuts; Wireless crystal links blocks within 127; Rain Sensor, Potentiometer and Entity Detector give redstone; Celestial Manipulator changes weather and time; Flux/Fluid Gates move energy and fluid.

## Gates (2026-11-20)

`cargo check` Finished; `cargo test` 40 passed (30 old runtime tests, 10 new glue tests: Flux Gate moves, NBT and item
data, shield lookup, unique block lists, comet and island shape); `cargo horizon-mod check` passes ("uses 937 items of the API ... Made
for 0a875da"; the lints left are `FoundStructure` and `StructureError` literals built field by field, which have no `..` form).

## Played (2026-11-22, build native-0a875da-199cf35987cc, world SkyVoid, single player, survival)

- Pass: items 1, 2, 4, 6, 8, 9; item 3 (crystal shield, Guardian kill, implosion crater); item 11 Hoe; item 13 break and place (contents
  and RF kept).
- Item 7: the shield, last stand and leg/boot modifiers work. Flight is not playable by the agent (it cannot double-jump).
- Item 12: the Generator burned coal at 84 RF/t (burn speed 6 x 14 RF) and pushed it into the chest beside it. The checklist's
  "1,000 RF/t" is the output cap (`GEN_OUT`), not the rate. The Grinder killed a NoAI zombie in its box for 1,760 RF
  (20 x 1.1 x 80) and the rotten flesh dropped. The Stabilized Spawner took a pig Mob Soul, a Wyvern Core set tier 1, and pigs
  spawned (the grinder then killed them: porkchops piled up). A `mob_soul` drop from a player kill was not played.
- Item 14: the Potentiometer (click to power 2) and the Entity Detector lit a lamp. The Celestial Manipulator in "stop rain"
  spent 256,000 RF and the storm faded; in "sunrise" it warped the time and spent 330,560 RF. Rain Sensor: see the fix below.
- Fixed while playing:
  - Draconic Bow (and the xutils Compound Bow): `release_using` gets no entity in this engine, so nothing fired. Both now find the
    player with `acting_player(host)`.
  - Chaos Crystal: the "implode in 5 seconds" warning went to nobody; now sent to the breaker.
  - Rain Sensor gave no signal in a storm under open sky (the first one stood under old glass and stone, sky light 14: correct; the
    second one had sky light 15 and still gave 0). It now asks the engine's `is_raining_at` above it (rain, open sky, a biome with
    rain), and logs each change.
- Not played: item 5 (reactor), item 10 (pedestal, receptacle, portal), item 13 smelting, the Crystal Binder, the Wireless crystal
  and the Flux/Fluid Gates.
- Item 13 smelting could not be set up: `item replace` fails for chest slots above 53, and `data merge` on `Items` does not reach the
  live slots of a mod block entity (Slot is read as a signed int, outside 0..size is dropped). The 256-slot chest screen is taller than
  the 720p window.
- The bow took 1,920 RF per full draw, not the "about 240" above.
- Replay (build native-0a875da-77e23cf3100b): the Rain Sensor lit its lamp in a thunderstorm (pass). The Wyvern Bow fires in survival
  on build native-0a875da-0d550df9e362 (pass): a full draw spent 1,920 RF (1,000,000 to 998,080) and one arrow (16 to 15). The
  earlier "fires nothing" was test setup: the test bow carried energy in `custom_data`, not the `sf3:energy` component.
  The Chaos Crystal warning was not replayed.
