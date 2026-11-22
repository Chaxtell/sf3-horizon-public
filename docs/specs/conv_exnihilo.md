# Conversion note: bundle 02 `sf3_exnihilo` -> `mods/sf3_exnihilo` (2026-11-20)

Hammers, Crooks, Chicken Stick, Sieves, Heavy Sieves, Barrels, Crucibles, Wooden Crucibles, Baits, Infested Leaves, Witchwater.
`src/runtime.rs` is byte-identical to the old one (all 29 runtime tests pass unchanged, plus 4 glue tests (33 in all)). Needs the content mods
`exnihiloadscensio` and `excompressum` on. Block entity types are `sf3_exnihilo:{sieve,heavy_sieve,barrel,crucible,wooden_crucible,bait,infested}`
(the old ids `sf3:sieve` etc. in `runtime` are only used to pick the rules; saves of the old bundle do not carry over).

## Hook by hook

| Old attach point | New |
|---|---|
| `native_mods` | dropped (Options > Mods entry: no stable route, decided) |
| `native_block_entity` | `BlockEntityPart::block_entity` -> `fresh_nbt(block)` (the runtime's `save()` of a default state) |
| `native_block_entity_ticks` | `BlockEntityPart::block_entity_ticks` |
| `native_block_entity_tick` | `BlockEntityPart::block_entity_tick` -> `tick()`; the kind is picked from the block at `pos` (`block_entity_for`), not from the entity id |
| `native_right_click_block` | `Hooks::right_click_block` (both sides; the client only cancels with `Success`) |
| `native_destroy_block` | `Hooks::break_block` (notes infested leaves' progress, while the block entity is readable) |
| `native_loot_drops` | `Hooks::loot_drops` |
| `native_random_tick` | `BlockPart::random_tick` on `infested_leaves` returning `Flow::Cancel` |
| `native_block_entity_inside` | `BlockPart::entity_inside` on `witchwater` (queue) |
| `native_level_tick_post` | `Hooks::level_tick_post` (server side, per level; settles the queue) |
| `native_recipe_categories` | dropped (see below) |

Native calls: `native_block`/`set_block`/`summon`/`tell`/`give`/`add_effect`/`sneaking`/`inventory` -> `sf3_host`. `native_with_mod_block_entity` ->
`h::be_update` (read-modify-write of the saved data, one write back). `native_block_entity_sync` is not needed: a replaced
or ticked block entity is synced by the engine.

## `host_ext.rs` (new, for merging into `sf3_host`)

| Function | SDK call | Replaces |
|---|---|---|
| `hand_item(host, player, hand)` | `LivingRef::hand_item` | `native_held`, `game.offhand` |
| `is_plain(stack)` | `ItemStack::damage`, `components` | the `plain` flag of `native_held` |
| `take_items(host, player, id, n) -> u32` | `inventory_slots` + `set_inventory_slot` (selected slot first, plain stacks only) | `native_take_items` |
| `count_items(host, player, id)` | `inventory_slots` | `native_count_items` |
| `shrink_hand(host, player, hand)` | `LivingRef::set_hand_item` | `consume_held` |
| `enchant_level(stack, ids)`, `set_enchants(stack, levels)` | `components()` read, `apply_components` write of `minecraft:enchantments` | `stack.enchantment_level`, `stack.enchant` |
| `spawn_item(host, dim, stack, at, motion, delay)` | `LevelRef::spawn_item_with_motion` | `Game::spawn_item` |
| `raining_at(host, dim, pos)` | `LevelRef::is_raining_at` | `raining_at` |
| `game_time(host, dim)` | `LevelRef::game_time` | `game.world.game_time` |
| `block_drops(host, dim, pos, tool)` | `LevelRef::block_drops` | `items.block_drops` (Crook re-rolls) |
| `play_sound(host, dim, at, sound, vol, pitch)` | `LevelRef::play_sound`, `SoundSource::Neutral` | `native_play_sound_in_place` |
| `entity_by_id`, `entity_position`, `entity_nbt`, `merge_entity_nbt`, `discard`, `player_of` | `host.entity`, `EntityRef::{position,nbt,merge_nbt,discard,uuid}` | `native_mob`, `native_entity_nbt_in`, `native_merge_entity_nbt`, `native_remove_mob`, `native_server_players` id lookup |

Mobs and players around a bait use `sf3_host::entities_in` + `entity_kind` (+ `entity_position`) in place of `native_mobs` and `native_server_players`.

## Behaviour differences

- **Hands.** Clicks on bundle blocks run on the main hand's event; an empty main hand falls back to the off hand's item, then the empty hand,
  as the old main-hand turn did. A silkworm acts in whichever hand holds it. A held block no longer needs the old inventory-resync trick: a cancelled
  click with `Success` ends it (`cancel_needs_resync` is unused now).
- **Items given back** (`give`) that do not fit are thrown at the player (`/give`), not dropped on the block. A sieve's own drops and a mesh with no room still pop out on top.
- **Buckets and held items** are taken from the inventory by item id (selected slot first, plain stacks only), as `native_take_items` did.
- **Rain** is `is_raining_at(pos + up)` (rain, open sky, biome) directly.
- **Crook extra rolls** call `LevelRef::block_drops` three times, with a guard flag so the loot hook it triggers does not recurse. If the leaves are
  already gone when the hook runs, the drops rolled once are repeated three times instead (same mean, more variance). Not played: which case happens.
- **Witchwater** contacts come from `entity_inside` on the witchwater block. They are settled one level tick later and only if the entity's feet are still in
  witchwater. If a fluid block does not fire `entity_inside`, conversions and the player debuffs will not happen (the most likely thing to fail in play).
- **Bait that spawns its animal** removes its own block while its block entity is ticking; the engine writes the tick back to a block entity that is gone.
- Infested leaves' random tick is cancelled with no `on` check (the Part has no host).
- Mesh enchantments are read as `{id: level}` or `{levels: {id: level}}` under `minecraft:enchantments`, and written back as `{id: level}`.

## Dropped or degraded

- Options > Mods entry: dropped (decided).
- Recipe viewer categories (`native_recipe_categories`: sieve, hammer, crook, composting, barrel fluids, crucible and heat tabs): dropped, no stable
  route (api_map: NONE). The tables stay in `runtime::view_categories` for `docs/specs/jei_stable_route.md`.
- Compressed Crook durability constant (`COMPRESSED_CROOK_DURABILITY`) was never used by the glue; unchanged.

## In-game checklist (10)

1. `exnihiloadscensio:sieve` (oak mesh item in hand): click with string mesh installs it; click with gravel loads it; clicking 10 times gives drops on top (PLAYTEST_LOG 2026-11-18: flint, ore pieces). Sneak + empty hand returns the mesh. A mesh with Efficiency II and Luck of the Sea III goes in and comes back enchanted.
2. Sieve sibling turn: two sieves loaded the same way within 2 blocks both advance on one click.
3. `excompressum:heavy_sieve_oak`: flint mesh then `extrautils2:compressedgravel` done within 14 clicks; max 6 clicks per second.
4. `exnihiloadscensio:wooden_barrel` under open sky, `/weather rain`: about 1 mB/tick (184 mB after 200 ticks, 787 after 800); water bucket in/out gives the empty/full bucket; dirt compost gives dirt after 600 ticks; sneak-less click with sapling composts.
5. Barrel of water over a 5x5 of mycelium becomes witchwater (`/tick sprint`); sand dropped in it gives `minecraft:soul_sand`; doll_blaze in a stone barrel of lava gives a blaze after 30 s.
6. `exnihiloadscensio:crucible` on a heat source: cobblestone melts to lava; empty bucket on it gives a lava bucket. `excompressum:wooden_crucible_oak`: oak leaves give about 48 mB water in 6 s; bucket gives water; dust plus 1000 mB water gives clay.
7. `excompressum:bait_cow` on grass with water and no player within 6 blocks: a cow spawns and the bait goes; a click shows the status line.
8. Hammer (and `excompressum:chicken_stick`): cobblestone gives gravel, gravel sand, sand dust; compressed hammer on compressed cobblestone gives 9 gravel.
9. Crook on oak leaves: more saplings and sticks than by hand; occasional `exnihiloadscensio:silkworm`. Silkworm on leaves (either hand) infests them; leaves spread; breaking them gives string only; infested leaves do not decay.
10. Witchwater with `NoAI` mobs (peaceful world): skeleton, creeper, spider, squid, villager, pig, mooshroom convert within 3 s; a survival player gets Blindness, Weakness III, Wither, Slowness for 210 ticks.
    Also check no template menu opens on any of these blocks and creative clicks keep the held stack.

## Not checked

Nothing in game. Not built into a launcher mod, no `--dev-mod` run. Unverified assumptions: `entity_inside` fires for the witchwater block; `block_drops` still rolls for leaves inside `loot_drops`; the block entity write-back after a bait removes its block; a nested block entity compound with `Timer` survives the engine's data write; `FakeHost` cannot run clicks or ticks, so only the data helpers have glue tests.

## Played 2026-11-21 (Claude, launcher build `native-0a875da-b18c8a2650b2`, world `SkyVoid`, survival)

- Item 8: Diamond Hammer cobblestone -> gravel -> sand -> dust; Chicken Stick cobblestone -> gravel. Pass. Compressed hammer not played.
- Item 9: Wooden Crook on 46 oak leaves: 5 saplings, 1 silkworm. Pass. Infesting and spread not played.
- Item 6: crucible over a torch: 4 cobblestone = 1000 solid, melts 0.1 mB a tick, empty bucket at 1000 mB gives a lava bucket. Pass. Wooden crucible not played.
- Item 4: water bucket in and out of a wooden barrel; 8 saplings fill it, dirt after 600 ticks, empty hand takes the dirt. Pass. Rain not played.
- Item 2: two sieves side by side, string mesh and gravel in each; one click moves both to Progress 10. Pass.
- Item 3: heavy sieve, flint mesh, compressed gravel; done within 14 clicks (5 ticks apart), ore pieces dropped. Pass. Click-rate cap not tested.
- Item 5: water barrel over 5x5 mycelium turns to witchwater (`A` 648 then 1000); sand gives soul sand; stone barrel of lava plus doll_blaze gives a blaze after about 30 s. Pass.
- Item 7: cow bait on 22 grass with water, player 13 blocks off: cow spawned and the bait went within about 800 ticks; a click says "Animals will spawn here when you are not looking.". Pass.
- Item 9 (rest): silkworm on oak leaves infests them; broken, they drop 1 string. Pass. Spread not seen in 3500 ticks (expected about one).
- Item 6 (rest): wooden crucible takes oak leaves and makes water (80 mB after 120 ticks). Pass. Bucket and clay not played.
- Item 10: in witchwater, skeleton becomes wither skeleton, pig zombified piglin, villager witch, creeper charges; the player gets Wither, Blindness, Weakness III, Slowness. Pass. Spider, squid, mooshroom not played. Converted hostiles despawn in Peaceful and when the player dies far away (vanilla).
- Item 1 was played 2026-11-20 (sieve, drops on top). Not played: compressed hammer, rain on barrels, wooden crucible bucket and clay.

