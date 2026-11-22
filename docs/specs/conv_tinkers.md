# Conversion note: `native/14_sf3_tinkers` -> `mods/sf3_tinkers` (2026-11-20)

Recipe: `conversion_recipe.md`. Nothing here was played; every in-game statement below is a thing to check.
Gates (inside `mods/sf3_tinkers`): `cargo check` ok, `cargo test` 85 passed (78 `runtime.rs` tests, unchanged, plus 7 `FakeHost`
tests in `glue_tests.rs`), `cargo horizon-mod check` ok. `runtime.rs` and `sf3_host.rs` are byte-identical copies (`cmp`).
The mod needs the content mod `tconstruct` on (comment in `horizon-mod.toml`). Content ids are the old ones.

## Files

`lib.rs` (types, registration, the `Hooks` impl), `machines.rs` (smeltery, casting, faucet, drying rack, spills), `tables.rs`
(station, forge, part builder, stencil table, chests), `tools.rs` (a built tool: dig speed, XP, area, drops, tooltip), `combat.rs`
(damage traits and what they queue), `slime.rs` (sapling), `host_ext.rs`.

## Hook-by-hook

| Old attach point (`horizon-mixin.toml`) | New |
|---|---|
| `native_mods` (Options > Mods entry) | dropped (decided) |
| `native_block_entity`, `_ticks`, `_tick` | `BlockEntityPart` `Machines` on 8 types registered in `register`: `sf3_tinkers:smeltery` (controller), `casting` (table, basin), `faucet`, `rack`, `station` (station, forge), `part_builder`, `tool_chest` (both chests), `tank` (3 seared tanks). Same NBT layouts. Ticks: controller, table, basin, faucet, rack, station, forge, part builder |
| `native_block_entity_container` | `h::declare_container` per tool table block in `register` (`tables::container`, same slots, faces and vanilla menu names) |
| `native_block_entity_fluids` | `host_ext::declare_fluids` for the 3 tanks (4000 mB), table (1296), basin (6000) |
| `native_right_click_block_v2` + `native_use_item` guard | `Hooks::right_click_block`. Server: main hand only, runs the click, `cancellation_result = Success` + `Flow::Cancel`. Client: ends the click for the same blocks (by block id; table/basin not with a bucket; rack not sneaking). The tick-stamp item-use guard is gone (see differences) |
| `native_destroy_block` | `Hooks::break_block`: tool tables and smeltery/table/basin/rack give back their contents; every other block is the held tool's dig (`tools::tool_dig`: XP, 3x3 area, trait effects) |
| `native_break_speed` | `Hooks::player_break_speed` (both sides; entity id, position and `new_speed`) |
| `native_attack_entity` | `Hooks::attack_entity` (`combat::attack_entity`: scouts armour, fire and full health for Crude, Superheat, Coldblooded) |
| `native_living_incoming_damage` | `Hooks::living_incoming_damage` (`combat::damage`): the weapon is `event.weapon`, the damage is `container.set_new_damage` |
| `native_living_knockback_v2` | `Hooks::living_knockback` (`event.strength`, `attacker_main`) |
| `native_living_experience_drop` | `Hooks::living_experience_drop` (`attacking_player` -> its tool, `amount` from `original`) |
| `native_block_exp` (Established) | no per-block route; folded into `tool_dig` (see degraded) |
| `native_loot_drops` | `Hooks::loot_drops` (`tools::loot_drops`; tool from `context.tool`, mob killer from `context.player`) |
| `native_tooltip` | `ItemPart::tooltip` on `tconstruct:<tool id>` for every tool in `tinker::TOOLS` |
| `native_random_tick` (sapling) | `BlockPart::random_tick` on `tconstruct:slime_sapling` (`slime.rs`, `LevelWriteHost`) |
| `native_player_tick` | `Hooks::player_tick_post` (server): hit XP, Ecological, Necrotic healing, Magnetic |
| `native_server_tick` (trait tick, commands, held snapshots) | `Hooks::server_tick` only keeps the tick clock (`context.tick`); after-hit effects run in `Hooks::level_tick_post`; the held-tool snapshots and the command queue are gone |

## `host_ext.rs` (Claude merges into `sf3_host`)

Copied unchanged in name and signature from the other mods: `game_time`, `spawn_item` (6 args), `hand_item`, `shrink_hand`,
`set_main_hand`, `position`, `entity_by_id`, `entity_nbt`, `player_of`, `item_from_snbt`, `break_as`, `can_harvest`, `pick`,
`be_items`, `be_set_items`, `fluid_tank`, `fluid_insert`, `fluid_extract`, `declare_fluids`, `player_dimension`,
`give_experience`, `inventory_insert`.

New (name, wraps, replaces):

| Function | Wraps | Old call |
|---|---|---|
| `block_in_tag(host: &dyn Host, block: &str, tag: &str) -> bool` | `Host::block_key` + `block_in_tag` | `native_block_name_in_tag`, `res.items().block_in_tag` |
| `tool_speed(tool: &Compound, block, in_tag: &dyn Fn(&str)->bool) -> f32` (pure) | parses `minecraft:tool` rules | `items().mining_speed(stack, name)` |
| `tool_component(host, stack) -> Option<Compound>` | stack's `minecraft:tool`, else `item_default_component` | (same) |
| `hand_of_entity(host: &dyn Host, id: u32) -> Option<ItemStack>` | `host.entity` + `living.hand_item(Main)` (works client side) | `game.held()` in the dig hook |
| `smelt_result(host, item: &str) -> Option<String>` | `recipes_of_type("minecraft:smelting")`, first ingredient's `items` set | `recipes().cook` |
| `add_effect_to(host, entity: EntityRef, id, amplifier, duration) -> bool` | `living.add_effect` | `native_run_command("effect give ...")` |
| `hurt(host, entity, damage_type, amount) -> bool` | `entity.hurt` (no attacker) | `native_hurt_entity` |
| `fire_ticks(host, entity) -> Option<i32>` | `entity.fire_ticks` | `native_entity_fire_ticks` |
| `heal(host, entity, amount) -> bool` | `living.heal` | Instant Health through a command |
| `health(host, entity) -> Option<f32>` | `living.health` | `mob_state` Health |
| `items_near(host, dim, min, max) -> Vec<(EntityRef, ItemStack, i32)>` | `entities_in` + `item_entity` stack and pickup delay | `native_item_entities` |
| `set_item_entity(host, entity, Option<ItemStack>) -> bool` | `item_entity.set_stack`, or `discard` for None | `native_set_item_entity` |

## Per-item data

Kept as `minecraft:custom_data` on the stack (`Tinker` compound: `Tool`, `Materials`, `Mods`, `Modifiers`, `ToolLevel`, `Xp`,
`RepairCount`; parts `Material`; patterns `Part`), which is an item component. Reads are `h::custom_data`, writes
`h::set_custom_data` (`tools::set_tinker`). No typed component was registered: the stacks are built from SNBT by `runtime.rs`
(`tool_snbt_with`, `part_snbt`, `pattern_snbt`) through `item_from_snbt`, and a typed component would change that runtime.

## Behaviour differences

- **Damage hooks fire for every mod** (old engine gated by mod). `living_incoming_damage` has no `ServerHost`, so it cannot test `h::on`: it
  acts on any `minecraft:player_attack` whose weapon is a tinker tool (nothing else carries `Tinker` data).
- **Weapon source.** The old glue read a per-tick snapshot of the attacker's hand; now `event.weapon` ("the direct entity's
  weapon when known"). If the engine gives `None` for a player's melee, no trait applies (not checked).
- **Everyone is a player.** Hit XP, Momentum, Insatiable, Magnetic, Ecological are keyed by player entity id and paid in that
  player's own `player_tick_post`; the old host-only limits (guests' hits gave no XP, Momentum/Ecological host only) are gone.
- **After-hit effects** (Poisonous, Sharp bleed, Prickly, Slimey on a kill, Shulking, Webbed, delayed damage) run from
  `level_tick_post` of the level the attacker (or later the victim) is in; entries older than 100 ticks are dropped.
  Shulking and Webbed now use the exact tick counts (the old `effect give` rounded to seconds); Poisonous is 100 ticks.
- **Necrotic** heals the whole earned amount in the next player tick (`living.heal`), not 4 points at a time as Instant Health.
- **Right click.** Both hands: only the main hand acts; a claimed click ends there. The old 4-tick stamp that swallowed the
  client's same-click item use is gone (Success + cancel is the stable route; to check: a bucket on a table/basin still goes to
  the engine, a block in hand is not placed on a controller).
- **Break speed** is the engine's `new_speed` times the tool's own speed over the speed of the tool component the stack digs with
  (its own, else its item default), so it is a no-op if the engine already reads the stack's component.
- **Faucet and smeltery fuel** read the first tank of a block through the `FLUIDS` handler (seared tanks have one); the old
  `can_drain` filter is not asked.
- A tool table break gives back slots through `be_set_items` then `spawn_item`; the smeltery's items and a table's cast items
  as before.
- Messages go to the action bar of the player (the old host fallback `native_client_action_bar` is not needed).

## Degraded or dropped

- Options > Mods entry: dropped.
- **Established block XP:** the stable `break_block` gives no way to add to the vanilla sample (`exp_to_drop = None` keeps
  sampling), so the tool gives its own +1 point at 33 percent (`give_experience`); the 3 percent case of a zero sample is folded in.
- **Slime sapling light:** the day's darkening is not asked (`raw_brightness(.., 0)`): a sapling under open sky also grows at night.
  The growth roll and tree height use this mod's xorshift, not the level's random.
- **Magnetic** still picks up at once; the old note stays.
- Momentum is per player but not synced to guests' clients (the dig hook runs where the player is; as before for guests).
- Unchanged old shortcuts: no Cheap trait in repairs, no Baconlicious, no furnace XP on Autosmelt, no tool picker screens.

## Play checklist (ids from `SF3_REGISTRY.md` 8E-8H and `PLAYTEST_LOG.md` 2026-11-17/18)

1. `tconstruct:smeltery_controller` beside a seared room (3x3 floor of `tconstruct:seared_*`, walls two high, one
   `tconstruct:seared_tank`): `data get block` shows `active:1`, `cap` 20736 for 3x3x2.
2. Fuel: lava in the seared tank, put a `minecraft:iron_ingot` in by right click; after a while `liquids` holds `tconstruct:molten_iron`;
   an empty-hand right click prints the status line; a sneaking empty-hand click returns unmelted items.
3. `tconstruct:faucet` against a smeltery drain (`tconstruct:smeltery_io`) over a `tconstruct:casting_table` holding a
   `tconstruct:part_cast_pick_head`... right click the faucet: the table fills, a pick head appears after the timer; empty-hand click takes it.
4. Casting basin: pour 1296 mB molten gold, gold block cast; a bucket right click on a table/basin goes to the engine, not to us.
5. Break a table/basin/controller holding items: they drop (built parts keep their material).
6. `tconstruct:tooltables_toolstation` (hopper menu): pick head + rod + binding of iron: pickaxe in slot 4, parts used; forge-only
   tools need `tconstruct:toolforge`: iron tough rod, hammer head, two large plates -> Iron Hammer (582 durability, level 2).
7. `tconstruct:tooltables_partbuilder` (furnace menu): `tconstruct:pattern` (`Part` data) + material items -> the part in slot 2.
   `tconstruct:tooltables_stenciltable`: pattern in hand, right click cycles the part (sneak backwards).
8. Station with a built tool and a modifier item (diamond, redstone, ...) -> rebuilt tool in slot 4 with free slots down; broken
   pattern/part chests give their contents back.
9. Hammer on the middle of a 3x3 stone wall: all nine break (cobblestone x9); `Xp` rises; the level-up message shows once.
10. A `tconstruct:pickaxe` with `Tinker{Tool:"pickaxe",Materials:[iron x3],Mods:"exnihilo_smashing=1"}` on lone cobblestone drops gravel.
11. Tooltip of any tool shows level, XP, modifiers, damage, durability (client).
12. A tool with Jagged (prismarine head) hits a zombie harder when worn; Squeaky (sponge) deals 0; hit XP appears on the tool.
13. Poisonous, Sharp, Prickly, Splintering, Insatiable, Crude on a cleaver/broadsword with the matching materials; Shulking and
    Webbed items give Levitation and Slowness II on the target; Necrotic heals.
14. Dig speed: a tool of a level below the block's tier does not dig it; Momentum/Stonebound change the speed; Autosmelt
    cooks drops, Silk Touch stops it; Beheading drops a head; Knockback pushes further.
15. `tconstruct:rack_drying`: rotten flesh -> `Max` 6000; `Time` 5995 -> `tconstruct:jerky_monster`, taken by an empty-hand click.
16. `tconstruct:slime_sapling` on `tconstruct:slime_dirt_blue`, `random_tick_speed` 3000: trunk `slime_congealed_green` and
    `slime_leaves_blue` within 600 ticks.

## Not checked

Everything in game. In code: whether `event.weapon` is `Some` for a player's melee; whether `player_break_speed` and the
stack's `minecraft:tool` double-apply; that client `right_click_block` ends the same-click item use; that `level_tick_post`
resolves `entity_by_id` for entities of that level; `entity.hurt` with no attacker on the cactus/generic types;
`FakeHost` covers none of the machines' fluid, slot, tag, time or snbt reads.
