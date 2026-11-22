# Conversion note: `native/09_sf3_botania` -> `mods/sf3_botania` (2026-11-20)

Rules (`runtime.rs`, 75 tests) copied unchanged (`cmp` ok). `sf3_host.rs` byte-identical. New adapter calls are in `src/host_ext.rs`
(every one repeats a name and signature already in another mod's `host_ext.rs`; nothing new). 6 `FakeHost`/pure glue tests added (81 in
all). Needs the content mod `botania` on in the instance, and `mods/sf3_player` (the worn accessories). Block entity types registered:
the 21 old ids `sf3_botania:<name>` (pool, spreader, endoflame, pure_daisy, apothecary, runic_altar, flower, terra_plate, alfheim_portal,
enchanter, brewery, detector, prism, spark_changer, fluxfield, bifrost, cell, crystal_cube, corporea_funnel, corporea_interceptor,
corporea_retainer), one Part (`Ent`) for blocks and block entities, so no `r.block_part` call anywhere. Item Parts: `Wand` (the twig wand)
and `GearItem` on every item `gear::wanted` picks (about 120 of the 331 `botania` items; `src/items.rs` lists the content mod's items and
must be regenerated when it grows).

## How the glue was converted

The old `glue.rs` (4,043 lines) called one big `Game`. `src/ctx.rs` is a `Ctx` with the same method names (`native_block`,
`native_with_mod_block_entity`, `native_item_entities`, `native_mobs`, `held`, `consume_held`, ...), each a few lines over `sf3_host` and
`host_ext`, so the machine and flower code is the old code with mechanical edits. Files: `machines.rs` (pools, spreaders and lenses,
Endoflame, Pure Daisy, Apothecary, Runic Altar, Terrestrial Plate, Alfheim Portal, Brewery, Enchanter, Detector, Prism, Changer,
Fluxfield, Dandelifeon cells, Bifrost), `flowers.rs` (the flowers), `network.rs` (Corporea), `interact.rs` (block right clicks and the Wand),
`gear.rs` (tools, rods, rings, relics, mirror, brews, Gaia, worn accessories), `util.rs`, `lib.rs` (Hooks and Parts).

## Hook by hook (old attach points, 31)

| Old attach point | New | Notes |
|---|---|---|
| `native_mods` | dropped | no stable route (decided) |
| `native_block_entity` | `BlockEntityPart::block_entity` (`initial`) | same starting numbers |
| `native_block_entity_container` | `h::declare_container` (Enchanter, 1 slot) | |
| `native_block_entity_ticks` | `BlockEntityPart::block_entity_ticks` | cells and cube do not tick |
| `native_block_entity_tick` | `BlockEntityPart::block_entity_tick` | works on a copy of `nbt`/`items`, written back whole |
| `native_use_item_on` | `ItemPart::use_on` on `Wand`, and on `GearItem` | server only |
| `native_right_click_block_v2` | `Hooks::right_click_block` | server, main hand; the client ends the click too for the handled blocks with an item in hand |
| `native_item_bar` | `ItemPart::item_bar` (client) | Tablet, rings, mirror |
| `native_recipe_categories` | not converted | the recipe viewer is the JEI step (`jei_stable_route.md`); `runtime::view` is untouched |
| `native_inventory_tick` | `ItemPart::inventory_tick` | edits written back with `set_slot` (`Ctx::edit_slot` re-reads the slot first) |
| `native_item_damaged` | `ItemPart::damage_item` | wear paid in mana: `amount = 0`, `Cancel` |
| `native_destroy_block` | `Hooks::break_block` | items kept in the block entity's data fall out; Terra Shatterer / Axe areas through `break_as` |
| `native_loot_drops` | `Hooks::loot_drops` | Elementium Pick/Axe, Guardian loot, Soul Cross |
| `native_use_item` | `ItemPart::use_item` | server only; no more "block click stamp" (a claimed block click does not also send the use) |
| `native_player_tick` | `Hooks::player_tick_post` | worn rings, worn gear, Gaia fights, effect stamps |
| `native_block_signal` / `native_is_signal_source` | `BlockPart::block_signal` / `is_signal_source` on `Ent` | see differences (dimension) |
| `native_should_apply_effect_tick_this_tick`, `native_apply_effect_tick` | replaced: `player_tick_post` stamps Feather Feet and Emptiness drinkers (`effect_left`) | the effect hooks have another shape |
| `native_potential_spawns` | `Hooks::potential_spawns` | Emptiness |
| `native_living_incoming_damage` | `Hooks::living_incoming_damage` | cloaks, laurel, Feather Feet; reads the cache, edits `container.new_damage` |
| `native_use_duration` / `native_use_animation` | `ItemPart::use_duration` / `use_animation` | rods, brews |
| `native_on_use_tick` | `ItemPart::on_use_tick` | Molten Core, Terra Firma |
| `native_left_click_block` | `Hooks::left_click_block` | Shifting Crust |
| `native_living_entity_use_item_finish` | `Hooks::living_entity_use_item_finish` | brew swig |
| `native_player_chat` (client queue `sf3_botania_chat`) | `Hooks::server_chat` | see Corporea chat |
| `native_server_tick` | not needed | the chat queue is read on `level_tick_post`; the belt modifiers on `player_tick_post` |
| `native_register_commands` / `native_perform_command` | `register_commands` / `run_mod_command` | `/corporea <request:text>` kept |
| `native_level_tick_post` | `Hooks::level_tick_post` | queued Corporea requests; the 20-tick worn cache moved into `player_tick_post` |

## Corporea chat

The chat hook now fires for every mod, so the old "type `<count> <item name>` near a sparked Index" request is back beside the command.
`server_chat` runs with no level in place, so it only queues the line (when `corporea::parse_request` accepts it; the line is not
cancelled, other players still read it); the player's level tick answers it (`network::chat_request`, same rules as before: sparked Index
within `CHAT_RANGE`, item matched by name, delivered over the Index, answer on the action bar). `/corporea <request>` queues the same way.

## Worn accessories: names and layout relied on

- Attachment `sf3_player:baubles` (player, saved, `copy_on_death`): a compound with keys `"0"`..`"6"`, each item NBT (`id`, `count`,
  `components`); only `id` is read here. Declared in `gear.rs` as `WORN: AttachmentType<Worn>` with the same namespace, name, codec and
  flags as in `mods/sf3_player` (its `Worn(Vec<Option<Compound>>)`); read with `x::attachment_get`. Test: the codec round trip.
- Attachment `sf3_player:laurel_used` (`bool`, codec `{used: 1b}`, not copied on death): written with `x::attachment_set(.., true)` when a
  Golden Laurel saved its wearer; that mod empties the head slot and removes it. Same declaration as there.
- Not checked: that two mods declaring one Attachment key with their own Rust type agree for the engine (both note it).

## `host_ext.rs` (merge into `sf3_host` after the wave)

All repeat existing names and signatures: `property`, `set_property`, `neighbor_signal`, `update_neighbors`, `items_near`,
`set_item_entity` (tinkers' `EntityRef, Option<ItemStack>`), `spawn_item` (6 args), `mobs`, `hurt`, `entity_by_id`, `entity_nbt`, `push`,
`summon_id`, `container_slots`, `container_extract`, `is_plain`, `data_int/str`, `set_data_int/str`, `burn_time`, `explode`, `game_time`,
`can_harvest`, `machine_break`, `block_in_tag`, `block_item_id`, `smelts`, `play_sound`, `give_or_throw`, `attachment_get/has/set/remove`,
`position`, `health`, `hand_item`, `set_hand`, `shrink_hand`, `selected_slot`, `inventory_stack`, `add_effect_with`, `food`, `set_food`,
`heal`, `item_from_snbt`, `block_entity_replace`, `enchantments`, `set_enchants`, `set_enchants_in`, `enchant_level`, `state_at`,
`set_state`, `entity_position`, `all_entities`, `players_in`, `inventory_insert`, `set_main_hand`, `be_items`, `be_set_items`, `world_dir`,
`state_block`, `state_property`, `player_dimension`, `hardness`, `has_block_entity`, `pick`, `view`, `rotation`, `eye`, `set_health`,
`set_modifier`, `break_as`, `effect_left`, `inventory_index`, `food_values`, `show_bar`, `hide_bar`, `drop_bar`, `player_name`,
`full_cube`, `player_of`, `component`, `set_component`, `property_in`. Some are unused for now (kept for the merge).

## Behaviour differences

- Particles: the sparkles of bursts, flowers and altars are not drawn (`Ctx::sparkle` is empty): the stable API needs a registered particle
  key and no mod has one yet (a refused key might refuse the mod). Everything else is as before.
- Block entities in a level are not listed by the stable API: pools, Terrestrial Plates and Enchanters register themselves when they tick
  (`Ctx::register_live`); flowers and sparks search that set. A pool is found one tick after the world loads.
- Detector and Interceptor signals: the signal hook names no dimension, so a place matches in any dimension (the same x, y, z in two
  dimensions would both give 15).
- Mana Enchanter: the stable API has no enchantment table. An enchantment is accepted for any item that is "enchantable" (the
  `minecraft:enchantable` component) and that agrees with the ones chosen (the vanilla exclusive sets, listed in `machines.rs`); whether it
  applies to the item is not checked. Weights are vanilla 1.21's; treasure is the four known ones.
- Lenses: Piston moves the block's state (kept); Weight spawns a falling block from the block id only (properties lost); the Firework lens
  summons the rocket as before; Explosive uses `explode`. "Replaceable" is the `minecraft:replaceable` tag. Bore breaks with `machine_break`
  and drops the stacks where the block stood.
- Exoflame reads and writes the furnace's data as a compound (`lit_time_remaining`, `cooking_time_spent`, `lit_total_time`, `Items` slot 0),
  not as text.
- Rod of the Shifting Crust: "storable" is no block entity, a full cube and an item; swap cells are "covered" when the next cell is a full cube.
- Rod of the Molten Core: the block's item and `smelts` decide what it turns into (a block id only). Terra Firma: "open" is air, the
  replaceable tag, or a non-full flower.
- Belts and the Reach Ring: modifiers are transient (`set_modifier`), written when the wanted amount changes and again every 200 ticks.
  The mana ring worn in a slot is not a mana source (its mana is in the stack `mods/sf3_player` keeps), as before.
- Rings, belts, cloaks, laurel: the worn set is read every 20 ticks per player in that player's own tick (the old design read it on the
  level tick); the damage hook works from the cache.
- Gaia Guardian: boss bar through `show_bar` (id `sf3_botania:gaia_<x>_<y>_<z>`). Stand-in mob and waves as before.
- Brew drink "PotionClear" runs `/effect clear <name>`.
- The twig wand and Gear Parts answer on the server only; the client sees the server's answer. The Wand's client side does not end the
  click, so the off hand's use can follow it (the old bundle's block-click stamp is gone).
- Food: Terrasteel set heals through `heal` (one point) while 1 to 17 food and health under 20.

## Features degraded or dropped

Options > Mods entry (decided). Recipe viewer categories (`native_recipe_categories`: JEI step). Particles. Enchanter applicability check.
Not converted: nothing else of the old glue is missing (every function of `glue.rs` has a counterpart, `native_*` calls with no stable route
are replaced as above).

## In-game checklist (14 items; ids from `SF3_REGISTRY.md` 2.9, `PLAYTEST_LOG.md` 2026-11-17/18 entries)

Needs `botania` and `sf3_player` on. Survival unless stated; `/data get block x y z` shows the numbers.
1. `botania:pool_mana` and `botania:spreader_mana` 4 apart, Wand sneak-click the spreader then the pool: "Spreader bound"; `/data merge block` the spreader `mana` 1000: bursts land, pool `mana` rises; Wand on the pool reads "Mana Pool: n / 1000000".
2. A `minecraft:iron_ingot` dropped on a pool holding 3000 mana (over `minecraft:air`, the plain infusion) becomes `botania:mana_resource_manasteel`.
3. `botania:endoflame` within 6 of a spreader, drop `minecraft:coal`: `mana` rises, the spreader gets it; `botania:pure_daisy` beside `minecraft:stone` turns it into `botania:livingrock` (a log into `botania:livingwood`).
4. `botania:altar_petal` (Apothecary): water bucket, petals, a `minecraft:wheat_seeds` craft a flower; sneak with an empty hand takes the last petal.
5. `botania:rune_altar` with ingredients and livingrock thrown on it, mana in (`data merge` `mana`), Wand: the rune is made.
6. Flowers: `botania:floating_hydroangeas` beside water with a spreader in range links (`linked: 1`); `botania:agricarnation` grows crops; `botania:exoflame` beside a lit furnace.
7. Corporea: two `botania:corporea_spark` items used on a chest and on `botania:corporea_index`; type `2 cobblestone` in chat within 8 blocks of the Index, then `/corporea 1 stick`: the items drop over the Index; a Funnel and an Interceptor with a Retainer behave as in the old log.
8. `botania:mana_tablet` carried: bar shows; it repairs a damaged `botania:manasteel_pick` (1 durability a tick for 120 mana); using the pick costs mana instead of durability.
9. `botania:terra_pick` charged to 10,000 (`data merge`): right click toggles "Terra Shatterer: on"; breaking a stone block breaks the 3x3 box.
10. Rods: `botania:dirt_rod` places dirt (75 mana), `botania:rainbow_rod` builds a bifrost road, `botania:divining_rod` counts ores, `botania:tornado_rod` lifts, `botania:smelt_rod` held on cobblestone smelts it after ten ticks.
11. `botania:exchange_rod`: sneak-click a block stores it, right-click a block starts a swap, left click swaps one block.
12. `botania:aura_ring` in the hotbar, or worn via `/baubles`: a carried tablet gains mana; `botania:magnet_ring` pulls dropped items; `botania:holy_cloak` worn cancels non-magic damage; `botania:golden_laurel` worn saves from a lethal hit once and then leaves the slot.
13. `botania:brewery` with a `botania:brew_vial` and ingredients: a brew item comes out; drinking it gives the effect, one swig per use; `botania:dice` rolls once (a relic).
14. Gaia: four `botania:pylon_gaia` round a `minecraft:beacon`, a Terrasteel Ingot used on the beacon: the guardian rises after 160 ticks with a boss bar and drops its loot.

## Played 2026-11-21 (build `native-0a875da-ee418ffc49f2`, world `SkyVoid`)

- 1 pass: Wand sneak-click spreader then pool says "Spreader bound" (`tx`/`has_target` set); spreader `mana` 1000 by `data merge`: pool 0 to 960 in 200 ticks; plain Wand click reads the spreader. Tool note: `game_interact` does not carry sneak; use `game_key shift down` + `game_mouse right click`. `data merge` of `tx`/`has_target` is overwritten by the runtime copy.
- 2 partial: an iron ingot inside the pool block becomes manasteel and costs 3000 mana. Bug: a dropped ingot rests on top of the pool (y 82.0, full-cube collision) and is never infused, since `pool_tick` only looks inside the block. Backlog.
- 3 pass: Endoflame burns dropped coal (`burn` 573), `linked: 1`, the spreader gains mana. Pure Daisy turns stone into livingrock and an oak log into livingwood after 1200 ticks.
- 4 pass: Apothecary takes a water bucket (bucket dropped back), 4 white petals and wheat seeds: a Pure Daisy. Sneak right-click with an empty hand returns the last petal.
- 5 pass: the Rune Altar took 5 ingredients (`goal` 5200); with `mana` 5200 and livingrock, the Wand made the rune.
- 6 pass: Hydroangeas ate a water source (`linked: 1`, spreader mana rose); Agricarnation grew wheat; Exoflame not separately checked.
- 7 pass (build `native-0a875da-90e32ec2c75e`): sneak-use put a spark on the chest and on the Index (plain use opens the chest first, as in vanilla). Within 2.5 blocks of the Index, chat `2 cobblestone` and `/corporea 1 stick` dropped 2 cobblestone and 1 stick over it, taken from the chest; the action bar said "Corporea Index: 1 x stick". 3 blocks away nothing happens (range). Funnel, Interceptor and Retainer not replayed (passed 2026-11-18).
- 8 pass (survival): a tablet repaired `manasteel_pick` damage 100 to 0 for exactly 120 mana per durability; mining costs mana, not durability.
- 9 pass: right click toggles `enabled:1`; at 1,000,000 mana a 3x3 box breaks, at 10k-20k a 1x3 column (matches the 1.10.2 level rule).
- 10 partial: dirt (75), divining ("2 ores within 15 blocks", 3000), smelt (cobblestone to stone to smooth stone, furnace recipes every 10 ticks) and rainbow (750, bifrost road at y 81) pass. Tornado bug: lift 0.4 is added each tick for `FLY_TIME` 20, so the player rose about 78 blocks and the landing killed them in survival. Backlog.
- 11 pass: sneak-click stored oak planks; right click on cobblestone swapped the connected run (3 blocks) from inventory. Single left-click swap untested (creative broke the block).
- 12 partial: aura ring in the hotbar charged a tablet (22 mana in 200 ticks); magnet ring pulled an item from 5 blocks (control without it did not). Holy cloak FAIL: worn in Body slot 314 (kept after reopening `/baubles`), survival, `/damage @s 4 minecraft:mob_attack` and a fall both took 4, not cancelled. Cause not found (GEAR cache refresh or the `living_incoming_damage` route). Laurel not played. Later the same day, pass after the fix: the worn list is now one shared `Worn` type in `sf3_player`, `sf3_botania` and `sf3_farming` (the reads failed with TypeMismatch); the holy cloak cancels the hit.
- 13 pass after a fix: the Brewery (vial, nether wart, cod, quartz, golden carrot, goal 2000, `mana` 2000 by `data merge`) made an Allure Brew (`swigs` 4). First drink did nothing: the use-item hooks give `entity: None` for the single-player host. With an `h::acting_player` fallback, a 2.2 s hold gave `botania:allure` 4760 ticks and left `swigs` 3. The same fallback went into the use hooks of `sf3_bloodmagic` (Draft/Poultice, dagger/digger/staff release), `sf3_player` (baconator) and `sf3_utility` (imbue). The dice is soulbound; a roll gave `botania:king_key`.
- 14 pass: beacon at 30 90 30, pylons at (±4, +1, ±4); the Terrasteel Ingot used on the beacon said "The Gaia Guardian stirs..." and was used up. The guardian (wither skeleton stand-in, 320 HP) rose with the "Gaia Guardian" boss bar, and skeleton and spider waves came. It killed the player in survival; after that death no bar showed for that fight (not reproduced; a fresh fight had its bar). Killed by `/damage ... minecraft:player_attack by @s`: 6 `botania:mana_resource_life_essence` dropped and the bar went away.

## Not checked

Nothing was run in the game. Unverified against the real engine: that the `block_entity_tick` copy of `nbt`/`items` written back whole
does not lose a write another block entity made to it in the same tick (only the Dandelifeon and burst deliveries write other entities,
never the ticking one); that `replace_data` on a neighbour per burst is cheap; that `right_click_block` on the client with an item in hand
does not hide a server-side click this mod declines; `living_incoming_damage` for the single-player host's own damage (the old note said it
did not reach the hook); `damage_item` firing for tool wear from block breaks; `on_use_tick`'s `remaining` counting down from 72000 as the
old hook did; that `inventory_tick` fires for armour slots 100-103 and the off hand; the `Attachment` types agreeing with `mods/sf3_player`;
that `x::push` moves a player (Tornado Rod); `show_bar` for a player's own bar. FakeHost cannot read blocks, players, time or
block entities, so the machines have no unit test; the ids, the block/entity map, the gear picker, the codec and the stack data do (6 tests).
