# Stable API map: our attach points and engine calls on Horizon main

Date: 2026-11-20. Engine: `horizon/` at `084ae44e40` (upstream main). Our bundles target `04a26210e3`.
Read-only research. Nothing was built or changed. This replaces the name-only matching in
`stable_api_fit_2026-11-20.md` with a check against source.

## How this was made

- Our lists come from a script over the real files: every `target = "..."` of an `[[injection]]` in
  `native/NN_sf3_*/mixins/*/horizon-mixin.toml`, and every call `native_xxx(` (comments stripped) in all
  `.rs` files under `native/NN_sf3_*/mixins/` (glue.rs plus the small helper files the toml names).
- Result: 457 injections over 118 distinct targets (matches the survey). 3388 calls to 183 distinct
  `native_*` names. Three of those are our own helpers in 07_sf3_jei, not engine calls: `native_size`
  (glue.rs:162), `native_key` (glue.rs:133), `native_stack` (a closure, glue.rs:667). So the real count is
  **3384 calls to 180 engine functions**. The survey's 3,397 / 184 also counted comments.
- Old signatures: read from git at `04a26210e3` (`git show`, no checkout). Old side and contract: the old
  `native-hooks.json` at that revision. Main signatures: `horizon/crates/horizon-mod-vocab/src/hooks/*.rs`
  (the `#[hook]` attributes and declared parameters). Where a hook declares no parameters, they come from
  the game function it names, so I compared against `crates/horizon-client/src/game/native_hooks/*.rs` on main.
  Host methods: `horizon-mod-vocab/src/host/*.rs`, every trait, parsed by script; file:line given per row.
- `hk/` below means `horizon/crates/horizon-mod-vocab/src/hooks/`. Host paths are under `horizon/crates/horizon-mod-vocab/src/`.
- Every hook and host method named in a row was opened (declaration and signature). Things I did not open are
  marked "not checked" in the row: the fields of renamed structs (`LootDrops`, `Dispensed`, `Screen`, `Command`,
  `Clock`, `Hit`, `ExperienceOrb`), what a hook's `version = 2..4` changed when the declared parameters look the
  same, and the per-handle method names (`PlayerRef::tell` etc.). Host backend methods (`*Backend`, `*BackendMut`)
  are not called directly: a mod calls them through the handle (`PlayerRef`, `LevelRef`, `EntityRef`,
  `BlockEntityRef`...). The rows name the backend method because that is where the signature lives.

### Verdicts

- **SAME**: same name and same parameters (only type names changed, such as `NativeX` -> `mod_api::X`), same contract.
- **RENAMED**: other name, same parameters and contract.
- **DIFFERENT SHAPE**: a stable route exists, but parameters, return, side or contract changed, or it moved from a
  hook to a registration (Part, Capability). Code must change, not just names.
- **NONE**: no stable route found.

### Three facts that apply to many rows

1. **Scoped hooks are Part methods.** Every hook with `scope = ...` (block, block_entity, item, menu) is only
   reachable as a method of `BlockPart`, `BlockEntityPart`, `ItemPart` or `MenuPart`, registered per type in
   `Hooks::register` (docs concepts/hooks-and-the-host.md:137, concepts/parts.md). The old hooks were global and
   fired for every block or item; a row marked SAME + Part keeps its arguments but needs a Part per type, and does
   not fire for types you did not register (vanilla items included).
2. **Old target paths are all stale.** On main `native_hooks.rs` became the folder `game/native_hooks/` (`base.rs`,
   `shared.rs`, one file per newer hook), and `game/` has area folders (`interface/`, `blocks/`, `modding/`, `mobs/`,
   ... each with a `.game-area`) that are not modules. So even where the function survives, the old
   `horizon_client::game::native_hooks::Game<'_>::native_x` path is wrong; it is now
   `horizon_client::game::native_hooks::base::Game<'_>::native_x` or similar (docs concepts/native-route/2-mixins.md,
   "Naming the target"). `[[native.mixin]]` still exists on main (same doc), in `horizon-mod.toml`.
3. **Handles instead of strings and uuids.** Most old calls took a `uuid: u128`, a `dimension: &str` or used the
   level/player "in place". Main takes `PlayerRef`, `LevelRef`, `EntityRef`, `LivingRef`, `MobRef`,
   `BlockSide` handles, and writes to storage take a `&Transaction`. This alone makes most Table B rows DIFFERENT SHAPE.

## Table A: attach-point targets (118)

Uses = injections / bundles. Bundles are by number (01 = 01_sf3_skyblock). Old target prefix
`horizon_client::game::native_hooks::Game<'_>::` is left out; `GameLevel` ones are marked (L).

| Our target | Uses | Bundles | Stable route on main | Signature difference | Behaviour difference | Verdict |
|---|---|---|---|---|---|---|
| `native_mods` | 19 | 19: 01 02 03 04 05 06 08 09 10 11 12 13 14 15 16 17 19 20 21 | none. Options > Mods list of native mods is gone; a mod is its manifest `[mod]` plus `Hooks::register` | - | - | NONE |
| `native_block_entity` | 18 | 18: 02 03 04 05 06 08 09 10 11 12 13 14 15 16 17 19 20 21 | `block_entity` (hk/block_entity.rs), BlockEntityPart method | out `Option<(String, Compound)>` -> `Option<Compound>` (type id no longer returned); adds `state` | both sides, replace; target moved to `GameLevel::native_block_entity` | DIFFERENT SHAPE |
| `native_destroy_block` | 18 | 18: 01 02 03 04 06 08 09 10 11 12 13 14 15 16 17 19 20 21 | `break_block` (hk/break_block.rs) | adds `exp_to_drop: &mut Option<u32>` | server, cancel: same | DIFFERENT SHAPE |
| `native_block_entity_container` | 16 | 16: 03 04 05 06 08 09 10 11 12 13 14 15 16 17 19 20 | No hook. Registration: `r.block_container(&block, ModContainer)` (vocab parts/default_capabilities.rs:36) | same `ModContainer` struct, given once at registration | fixed at load, not asked per call; mod blocks only | DIFFERENT SHAPE |
| `native_block_entity_tick` | 16 | 16: 02 03 04 05 06 08 09 10 11 12 13 14 15 16 17 20 | `block_entity_tick` (hk/block_entity_tick.rs), BlockEntityPart | adds `reply: &mut BlockEntityTickReply`; entity is a `ModBlockEntityView` (`id()` method, fields `nbt/items/data`, no `id` field) | server, listen; `Unchanged` reply discards this Part's edits | DIFFERENT SHAPE |
| `native_block_entity_ticks` | 16 | 16: 02 03 04 05 06 08 09 10 11 12 13 14 15 16 17 20 | `block_entity_ticks` (hk/block_entity_ticks.rs), BlockEntityPart | none | server, read-only host | SAME |
| `native_loot_drops` | 16 | 16: 02 03 04 05 06 09 10 11 12 13 14 15 16 19 20 21 | `loot_drops` (hk/loot_drops.rs) | context type `NativeLootDrops` -> `LootDrops` (fields not checked) | server, collect | SAME |
| `native_use_item` | 15 | 15: 01 03 04 05 06 08 09 10 11 13 14 15 16 17 19 | `use_item` v2 (hk/use_item.rs), ItemPart | adds `hand`, `player: u128`, `player_entity_id`; out `claimed: bool` -> `result: &mut Option<InteractionResult>` | server cancel -> both sides replace; client prediction runs too | DIFFERENT SHAPE |
| `native_right_click_block_v2` | 12 | 12: 05 09 10 11 12 13 14 16 17 19 20 21 | `right_click_block` (hk/right_click_block.rs) | as above; hand is inside `BlockClick` (not checked) | both sides | DIFFERENT SHAPE |
| `native_screen` | 12 | 12: 03 04 05 06 08 10 11 12 13 15 17 20 | `screen` (hk/screen.rs), BlockEntityPart | `NativeScreen` -> `mod_api::Screen` (fields not checked) | both, replace, read-only host | SAME |
| `native_place_block` | 11 | 11: 03 04 06 11 12 13 15 16 17 20 21 | `on_block_placed_by` (hk/on_block_placed_by.rs), ItemPart; or global `entity_place` (hk/entity_place.rs, cancel) | adds `placer: Option<PlayerRef>`, `face`, `click`; `state: BlockState` | server, listen; ItemPart = only registered items | DIFFERENT SHAPE |
| `native_block_entity_energy` | 9 | 9: 04 05 06 08 11 12 13 16 17 | No hook. `r.block_energy(&block, ModEnergyBuffer)` (parts/default_capabilities.rs:40) | same `ModEnergyBuffer` struct | fixed at load; mod blocks only | DIFFERENT SHAPE |
| `native_block_entity_fluids` | 9 | 9: 04 05 06 08 10 14 15 16 17 | No hook. `r.block_fluids(&block, ModFluidTanks)` (parts/default_capabilities.rs:38) | same struct, now `#[non_exhaustive]` (build from `Default`) | fixed at load; mod blocks only | DIFFERENT SHAPE |
| `native_block_signal (L)` | 9 | 9: 03 04 06 09 11 13 16 17 20 | `block_signal` (hk/block_signal.rs), BlockPart | none | server, listen | SAME |
| `native_inventory_tick` | 9 | 9: 03 04 05 09 10 13 16 17 19 | `inventory_tick` (hk/inventory_tick.rs), ItemPart | adds `stack: &ItemStack` (read-only; old code changed it via `native_carried_stack`) | server, listen; only registered items | DIFFERENT SHAPE |
| `native_container_accepts` | 8 | 8: 03 04 05 08 11 13 15 17 | No hook. `ITEMS` capability: `r.block_entity_capability_before_game(&ITEMS, ...)` with `is_valid`/`insert` (concepts/capabilities.md) | whole handler instead of a per-slot veto | replaces the game's handler for that type, so you also redo face/slot rules | DIFFERENT SHAPE |
| `native_tooltip` | 8 | 8: 04 05 06 10 11 13 14 16 | `tooltip` (hk/tooltip.rs), ItemPart | none | client, collect; only registered items (vanilla items need a Part too) | SAME |
| `native_use_item_on` | 8 | 8: 03 04 05 08 09 10 16 17 | `use_on` v2 (hk/use_item.rs), ItemPart. NOT main's `use_item_on` (hk/block_use_item_on.rs), which is the block's `useItemOn` (BlockPart, keyed by state) | adds `hand`, `hit`, `player`, `player_entity_id`; out `claimed` -> `result: &mut Option<InteractionResult>` | server cancel -> both sides replace | DIFFERENT SHAPE |
| `native_is_signal_source (L)` | 7 | 7: 04 09 11 13 16 17 20 | `is_signal_source` (hk/is_signal_source.rs), BlockPart | none | server, listen | SAME |
| `native_level_tick_post` | 7 | 7: 02 05 06 09 15 17 19 | `level_tick_post` (hk/level_tick_post.rs) | `dimension: &str` -> `level: LevelRef` | server -> both sides: check the side | DIFFERENT SHAPE |
| `native_player_tick` | 7 | 7: 05 09 10 13 14 16 19 | `player_tick_post` (hk/entity_join_level.rs) | `()` -> `player: PlayerRef` | server -> both sides; no player state is swapped in | DIFFERENT SHAPE |
| `native_right_click_block` | 7 | 7: 01 02 03 04 05 06 15 | `right_click_block` (hk/right_click_block.rs) | `pos, face` -> `click: &BlockClick`; adds `use_block`, `use_item: &mut TriState`, `cancellation_result` | server -> both sides | DIFFERENT SHAPE |
| `native_server_tick` | 7 | 7: 01 09 10 11 14 16 21 | `server_tick` (hk/server_tick.rs) | `NativeLifecycleContext` -> `LifecycleContext` | server, listen | SAME |
| `native_block_entity_accepts_fluid` | 6 | 6: 04 05 08 15 16 17 | No hook. `FLUIDS` capability: `r.block_entity_capability(&FLUIDS, ...)` with your `ResourceHandler<FluidResource>` (`is_valid`/`insert`) (docs concepts/capabilities.md) | whole handler instead of a yes/no per tank | a provider answers every lookup, not just fills | DIFFERENT SHAPE |
| `native_item_energy_buffer` | 6 | 6: 04 05 06 11 16 19 | No hook. `r.item_capability(&ITEM_ENERGY, item, provider)` -> your `EnergyHandler` (vocab item/energy_capability.rs:42, parts/items.rs:112) | you write the handler and where the energy lives (component), not a buffer spec | reached through `ItemPlace::capability`, splits one item off a stack | DIFFERENT SHAPE |
| `native_living_incoming_damage` | 6 | 6: 04 05 09 10 13 14 | `living_incoming_damage` (hk/entity_leave_level.rs; target `HitLevel::native_living_incoming_damage`) | `damage_type, causing, direct, amount: &mut f32` -> `source: &HurtSource, victim: &Victim, weapon, container: &mut DamageContainer` | server, cancel, level host | DIFFERENT SHAPE |
| `native_recipe_categories` | 6 | 6: 02 04 05 08 09 10 | none. `recipe_book_categories` is the vanilla recipe book, not viewer tabs | - | - | NONE |
| `native_use_duration` | 6 | 6: 05 09 10 13 17 19 | `use_duration` (hk/use_duration.rs), ItemPart | none | both, listen, read-only host | SAME |
| `native_break_speed` | 5 | 5: 04 06 10 13 14 | `player_break_speed` (hk/player_break_speed.rs) | adds `player: u32`, `canceled`; `state` is `u32`; `original`->`original_speed`, `speed`->`new_speed` | now both sides and cancellable | DIFFERENT SHAPE |
| `horizon_client_lib::menu::native_menu_slot_rules` | 5 | 5: 03 04 05 08 11 | `menu_slot_rules` v4 (hk/menu_slot_rules.rs), MenuPart | adds `container: MenuContainer`, `context: &MenuSlotContext`; free fn in horizon-client-lib -> method | server -> both sides; MenuPart = mod menu types only | DIFFERENT SHAPE |
| `native_potential_spawns` | 5 | 5: 01 04 09 11 16 | `potential_spawns` (hk/native_potential_spawns.rs) | none | server, cancel, read-only host | SAME |
| `native_attack_entity` | 4 | 4: 11 14 16 20 | `attack_entity` (hk/attack_entity.rs) | adds `dimension: &str` first | server, cancel: same | DIFFERENT SHAPE |
| `native_block_entity_inside` | 4 | 4: 02 04 16 17 | `entity_inside` (hk/entity_inside.rs), BlockPart method | `state: BlockState`, `pos: BlockPos`; adds `precise`, out `effects: &mut InsideEffects`, `writes: &mut Vec<InsideWrite>` | listen -> collect: effects are returned, not done directly; level host | DIFFERENT SHAPE |
| `native_living_entity_use_item_finish` | 4 | 4: 09 10 16 19 | `living_entity_use_item_finish` (hk/living_entity_use_item_finish.rs) | none | old catalog said server; main says both sides | SAME |
| `native_random_tick (L)` | 4 | 4: 02 05 14 17 | `random_tick` (hk/random_tick.rs), BlockPart | none | server, cancel | SAME |
| `native_screen_draw` | 4 | 4: 04 05 08 15 | `screen_draw` (hk/screen_draw.rs), BlockEntityPart | none (`batch` renamed `draw`) | client, listen | SAME |
| `native_analog_output (L)` | 3 | 3: 03 06 11 | `analog_output` (hk/analog_output.rs), BlockPart | none | server, collect | SAME |
| `native_chorus_fruit_teleport` | 3 | 3: 04 11 16 | `item_consumption_teleport` v2 (hk/item_consumption_teleport.rs) | `player: u128, name` -> `consumer: LivingRef, consumed: &ItemStack` | server, cancel; fires for any living consumer, not just players | DIFFERENT SHAPE |
| `native_client_tick_post` | 3 | 3: 10 16 17 | `client_tick_post` (hk/client_tick_post.rs) | none | client, listen | SAME |
| `native_ender_pearl_teleport` | 3 | 3: 04 11 16 | `ender_pearl_teleport` v3 (hk/entities_load.rs) | `player: u128, name` -> `owner: EntityRef`; adds `hit_entity`, `hit_block`, `hit_face`, `hit_at` | server, cancel | DIFFERENT SHAPE |
| `native_explosion_detonate` | 3 | 3: 03 04 11 | `explosion_detonate` v2 (hk/explosion_detonate.rs) | `source: Option<(u32,&str)>` removed; adds `entities: &mut Vec<EntityRef>` | server, collect | DIFFERENT SHAPE |
| `native_has_analog_output (L)` | 3 | 3: 03 06 11 | `has_analog_output` (hk/has_analog_output.rs), BlockPart | none | server, collect | SAME |
| `native_hurt_enemy` | 3 | 3: 06 10 17 | `hurt_enemy` (hk/hurt_enemy.rs), ItemPart | none | server, listen; only registered items | SAME |
| `native_menu_button` | 3 | 3: 04 05 15 | `menu_button` (hk/menu_button.rs), BlockEntityPart | `pos, id` -> `context: &MenuButtonContext`; adds `carried: &mut Option<ItemStack>` | server, listen | DIFFERENT SHAPE |
| `native_menu_input_closed` | 3 | 3: 15 17 19 | none found. `menu_closed` has no slots | - | - | NONE |
| `native_perform_command` | 3 | 3: 01 09 19 | `run_mod_command` (hk/run_mod_command.rs) for commands from `register_commands`; `command` (hk/command.rs) is client-only | `player: &NativeServerPlayer, command: &str` -> `source: &CommandSource, command: &CommandInvocation` | server, cancel | DIFFERENT SHAPE |
| `native_register_commands` | 3 | 3: 01 09 19 | `register_commands` v2 (hk/register_commands.rs) | `Vec<NativeCommand>` -> `Vec<mod_api::Command>` (fields not checked) | server, collect | DIFFERENT SHAPE |
| `native_release_using` | 3 | 3: 10 13 17 | `release_using` (hk/release_using.rs), ItemPart | none | both, listen | SAME |
| `native_screen_click` | 3 | 3: 04 05 15 | `screen_click` (hk/screen_click.rs), BlockEntityPart | none | client, replace | SAME |
| `native_world_lifecycle` | 3 | 3: 01 11 21 | `world_lifecycle` v2 (hk/world_lifecycle.rs) | same params on main (`LifecycleContext`); what v2 changed not checked | server, listen | SAME |
| `horizon_client::game::stations::Game<'_>::draw_stack_tooltip_with` | 2 | 1: 07 | none. Still on main at game/blocks/stations/tooltip.rs:87 | same | - | NONE |
| `native_block_entity_submit` | 2 | 2: 03 11 | `block_entity_submit` (hk/block_entity_submit.rs), BlockEntityPart | none | client, listen | SAME |
| `native_block_entity_update_tag` | 2 | 2: 03 11 | `block_entity_update_tag` (hk/block_entity_update_tag.rs), BlockEntityPart | none | server, replace; also runs off-thread for far chunks (no host) | SAME |
| `horizon_world::worldgen::native_generate::native_chunk_generate` | 2 | 2: 01 13 | none (no chunk generation hook; `horizon_world::worldgen::native_generate` is gone) | - | - | NONE |
| `native_entity_tick_listened` | 2 | 2: 04 10 | `entity_tick_listened` (hk/entity_tick_listened.rs) | none | server, collect | SAME |
| `native_entity_tick_pre` | 2 | 2: 04 10 | `entity_tick_pre` (hk/entity_tick_pre.rs) | none | server, cancel | SAME |
| `native_is_bonemeal_success (L)` | 2 | 2: 05 17 | `is_bonemeal_success` (hk/is_bonemeal_success.rs), BlockPart | none | server, collect | SAME |
| `native_is_valid_bonemeal_target (L)` | 2 | 2: 05 17 | `is_valid_bonemeal_target` (hk/is_valid_bonemeal_target.rs), BlockPart | none | both, replace | SAME |
| `native_item_bar` | 2 | 2: 06 09 | `item_bar` (hk/item_bar.rs), ItemPart | none | client, listen | SAME |
| `native_left_click_block` | 2 | 2: 03 09 | `left_click_block` (hk/left_click_block.rs) | none | server, cancel | SAME |
| `native_level_tick_pre` | 2 | 2: 04 13 | `level_tick_pre` (hk/level_tick_pre.rs) | `dimension: &str` -> `level: LevelRef` | server -> both sides | DIFFERENT SHAPE |
| `native_living_experience_drop` | 2 | 2: 14 16 | `living_experience_drop` (hk/living_experience_drop.rs) | `xp` -> `amount`; adds `attacking_player`, `original`, `cancel` | listen -> cancel | DIFFERENT SHAPE |
| `horizon_world::loot::native_loot_table_load` | 2 | 2: 05 15 | `loot_table_load` v2 (hk/loot_table_load.rs; target `horizon_world::loot::native_loot_table_load`) | adds `context: &LoadContext` | server, collect, data-load phase | DIFFERENT SHAPE |
| `native_on_use_tick` | 2 | 2: 05 09 | `on_use_tick` (hk/on_use_tick.rs), ItemPart | none | both, listen | SAME |
| `native_perform_bonemeal (L)` | 2 | 2: 05 17 | `perform_bonemeal` (hk/perform_bonemeal.rs), BlockPart | none | server, listen | SAME |
| `native_state_for_placement (L)` | 2 | 2: 03 04 | `state_for_placement` (hk/state_for_placement.rs), BlockPart | `FluidState` -> `mod_api::FluidState` | server, replace | SAME |
| `native_use_animation` | 2 | 2: 09 19 | `use_animation` (hk/use_animation.rs), ItemPart | none | client, listen | SAME |
| `native_world_saved` | 2 | 2: 10 15 | `world_saved` (hk/world_saved.rs) | none | server, listen | SAME |
| `horizon_client::game::creative_screen::Game<'_>::draw_creative` | 1 | 1: 07 | none checked. Still on main at game/interface/creative_screen.rs:108 | same | - | NONE |
| `horizon_client::game::Game<'_>::draw_inventory` | 1 | 1: 07 | none checked. Raw game function, still on main at game/interface/inventory_slots.rs:422 | same signature | - | NONE |
| `horizon_client::game::native_panel::Game<'_>::draw_mod_browser` | 1 | 1: 07 | none. Still on main at game/modding/native_panel.rs:641 | now returns `Option<BrowserTooltip>` | - | NONE |
| `horizon_client::game::options::Game<'_>::draw_options` | 1 | 1: 07 | none. Still on main at game/interface/options.rs:181 | same | - | NONE |
| `horizon_client::game::creatures::Game<'_>::mob_death_canceled` | 1 | 1: 13 | none as a hook (it gates whether `living_death` fires). Still on main at game/native_hooks/living_death.rs:61 | param `m: &Mob` -> `mob: &horizon_client::mobs::Mob` | - | NONE |
| `horizon_client::game::native_panel::Game<'_>::mod_browser_closed` | 1 | 1: 07 | none. Still on main at game/modding/native_panel.rs:881 | same | - | NONE |
| `native_apply_effect_tick` | 1 | 1: 09 | `apply_effect_tick` (hk/on_effect_added.rs) | `effect: &str` -> `EffectKey`; adds `holder: LivingRef`, `health`, `max_health`, `food`, `changes: &mut Vec<EffectTickChange>` | server, listen, read-only host: writes go through `changes`, not the host | DIFFERENT SHAPE |
| `native_block_clone_item` | 1 | 1: 05 | `clone_item_stack` (hk/clone_item_stack.rs), BlockPart method | adds `dimension`, `include_data`; `pos` is `BlockPos` | server, replace, read-only host; only for blocks you register a BlockPart on | DIFFERENT SHAPE |
| `native_block_entity_render_bounding_box` | 1 | 1: 11 | `block_entity_render_bounding_box` (hk/block_entity_render_bounding_box.rs), BlockEntityPart | none | client, collect | SAME |
| `native_block_exp (L)` | 1 | 1: 14 | `exp_drop` (hk/exp_drop.rs), BlockPart | `block: &str, experience: &mut u32` -> `state: BlockState, block_entity, breaker, tool, experience: &mut Option<i32>` | listen -> replace | DIFFERENT SHAPE |
| `native_can_survive (L)` | 1 | 1: 17 | `can_survive` (hk/can_survive.rs), BlockPart | none | server, replace | SAME |
| `native_chunk_load` | 1 | 1: 01 | `chunk_load` (hk/chunk_load.rs) | none | server, listen | SAME |
| `native_component_types` | 1 | 1: 06 | `component_types` (hk/component_types.rs) | adds `context: &RegistrationContext` | both, collect, registration phase | DIFFERENT SHAPE |
| `native_dispense_item` | 1 | 1: 16 | `dispense_item` (hk/dispense_item.rs), ItemPart | answer type `NativeDispensed` -> `mod_api::Dispensed` (fields not checked) | server, replace; only items you register a Part on | SAME |
| `native_dragon_egg_form (L)` | 1 | 1: 13 | `dragon_egg_form` (hk/dragon_egg_form.rs) | none | server, cancel | SAME |
| `native_explosion_knockback` | 1 | 1: 04 | `explosion_knockback` (hk/explosion_knockback.rs) | none | server, collect | SAME |
| `native_explosion_prime` | 1 | 1: 04 | `explosion_prime` (hk/explosion_prime.rs) | none | server, listen | SAME |
| `native_hears_projectile_impacts` | 1 | 1: 05 | `hears_projectile_impacts` (hk/hears_projectile_impacts.rs) | none | server, collect | SAME |
| `native_interact_entity` | 1 | 1: 05 | `entity_interact` v2 (hk/entity_interact.rs) | adds `dimension`, `hand`; out `claimed: bool` -> `result: &mut Option<InteractionResult>` | server -> both sides; cancel -> replace | DIFFERENT SHAPE |
| `native_interact_entity_v2` | 1 | 1: 16 | `entity_interact` v2 (hk/entity_interact.rs) | adds `dimension`; out `cancel: bool` -> `result: &mut Option<InteractionResult>` | both sides; replace | DIFFERENT SHAPE |
| `native_item_damaged` | 1 | 1: 09 | `damage_item` v2 (hk/damage_item.rs), ItemPart | `player, name, item: &str` -> `stack: &ItemStack, entity: Option<LivingRef>`; adds `break_now` | server, cancel; only registered items | DIFFERENT SHAPE |
| `native_item_fluid_tank` | 1 | 1: 05 | No hook. `r.item_capability(&ITEM_FLUIDS, ...)` (block/fluid_capability.rs:305) | handler instead of a capacity number | as above | DIFFERENT SHAPE |
| `native_level_load` | 1 | 1: 16 | `level_load` (hk/level_load.rs) | none | server, listen | SAME |
| `native_living_change_target` | 1 | 1: 10 | `living_change_target` (hk/living_change_target.rs) | `dimension, entity, kind, target: Option<u128>, target_mob` -> `mob: MobRef, original_target, new_target: &mut Option<LivingRef>, is_brain` | server, cancel, read-only host; can now redirect the target | DIFFERENT SHAPE |
| `native_living_death` | 1 | 1: 13 | `living_death` v2 (hk/living_death.rs) | `damage_type: &str, attacker: u32` -> `source: &HurtSource, weapon: Option<&ItemStack>` | server, cancel | DIFFERENT SHAPE |
| `native_living_entity_use_item_start` | 1 | 1: 05 | `living_entity_use_item_start` (hk/living_entity_use_item_start.rs) | none | both, cancel | SAME |
| `native_living_entity_use_item_tick` | 1 | 1: 05 | `living_entity_use_item_tick` (hk/living_entity_use_item_tick.rs) | none | both, cancel | SAME |
| `native_living_knockback_v2` | 1 | 1: 14 | `living_knockback` (hk/experience_orb_can_merge.rs; target `HitLevel::native_living_knockback`) | adds `source: &HurtSource`, `entry: KnockbackEntry` | server, cancel, level host | DIFFERENT SHAPE |
| `horizon_world::worldgen::native_generate::native_lod_column` | 1 | 1: 01 | none (gone with `native_generate`) | - | - | NONE |
| `native_may_place_on (L)` | 1 | 1: 05 | `may_place_on` (hk/may_place_on.rs), BlockPart | none | server, replace | SAME |
| `native_menu_clicked` | 1 | 1: 06 | `menu_clicked` (hk/menu_clicked.rs) | none | server, listen | SAME |
| `native_menu_closed` | 1 | 1: 06 | `menu_closed` (hk/menu_closed.rs) | none | server, listen | SAME |
| `native_menu_links` | 1 | 1: 05 | `menu_links` (hk/menu_links.rs) | none | server, collect | SAME |
| `native_mob_killed` | 1 | 1: 10 | `mob_killed` (hk/mob_killed.rs) | none | server, listen | SAME |
| `native_mob_spawned` | 1 | 1: 04 | `mob_spawned` (hk/mob_spawned.rs) | none | server, listen | SAME |
| `horizon_client_lib::lan::hub::chat::native_player_chat` | 1 | 1: 09 | `server_chat` (hk/server_chat.rs) | adds `player_id`, `raw_text`; `message: &str` -> `message: &mut Text` | server, cancel; message can now be edited | DIFFERENT SHAPE |
| `native_player_died` | 1 | 1: 19 | `player_died` (hk/player_died.rs) | none | server, listen | SAME |
| `native_player_input` | 1 | 1: 16 | `player_input` (hk/player_input.rs) | none | server, listen | SAME |
| `native_player_load_from_file` | 1 | 1: 01 | `player_load_from_file` (hk/player_load_from_file.rs) | none | server, listen | SAME |
| `native_player_respawn_position` | 1 | 1: 04 | `player_respawn_position` (hk/player_respawned.rs) | `player: u128, name, dimension: &mut String` -> `player: PlayerRef, level: &mut LevelDimension`; adds `original_*`, `missing_respawn_block`, `copy_original_spawn_position` | server, listen | DIFFERENT SHAPE |
| `native_projectile_impact` | 1 | 1: 05 | `projectile_impact` v2 (hk/interaction_key_mapping_triggered.rs) | declared params match ours; what v2 changed not checked | server, cancel | SAME |
| `native_recipe_sources` | 1 | 1: 05 | `recipe_sources` (hk/recipe_sources.rs) | none | server, collect | SAME |
| `native_screen_tooltip` | 1 | 1: 04 | `screen_tooltip` (hk/screen_tooltip.rs), BlockEntityPart | none | client, collect | SAME |
| `native_server_about_to_start` | 1 | 1: 13 | `server_about_to_start` (hk/server_about_to_start.rs) | none | server, listen | SAME |
| `native_should_apply_effect_tick_this_tick` | 1 | 1: 09 | `should_apply_effect_tick_this_tick` (hk/should_apply_effect_tick_this_tick.rs) | `effect: &str` -> `EffectKey` | server, listen, read-only host | DIFFERENT SHAPE |
| `native_tooltip_render_pre` | 1 | 1: 07 | `render_tooltip_pre` (hk/render_tooltip_pre.rs) | `batch: &mut HudBatch, x, y` -> `draw: &mut dyn DrawContext, screen_width/height, elements, place: &mut TooltipPlace` | client, cancel | DIFFERENT SHAPE |
| `native_world_primitives` | 1 | 1: 08 | none as a hook. Nearest: `render_level_stage` (hk/render_level_stage.rs) or `world_drawn` (hk/world_drawn.rs, target in `mod_render`, not opened) | different draw API (`WorldGeometry`/`WorldDrawContext` lines and quads) | client | NONE |
| `horizon_client::game::natural_spawning::<GameLevel<'_,'_> as NaturalLevel>::spawn_hooks` | 1 | 1: 04 | none (gate for `potential_spawns`). Still on main at game/mobs/natural_spawning.rs:882 | same | - | NONE |
| `horizon_client::game::stations::Game<'_>::tooltip_box` | 1 | 1: 07 | none. Still on main at game/blocks/stations.rs:2154 | same | - | NONE |
| `horizon_client::game::stations::Game<'_>::tooltip_text` | 1 | 1: 07 | none. Still on main at game/blocks/stations.rs:2209 | same | - | NONE |

Verdicts, Table A: SAME 56 (169 injections), RENAMED 0 (0 injections), DIFFERENT SHAPE 46 (245 injections), NONE 16 (43 injections).

## Table B: engine functions our glue calls (180)

Calls = call sites / bundles. Route names the host method; file:line and trait are from the parse.

| Our call | Calls | Bundles | Stable route on main | Signature difference | Verdict |
|---|---|---|---|---|---|
| `native_block` | 475 | 19 | `level_block` (or `LevelHost`/`LevelRef` block reads in level hooks) (host/levels.rs:351, LevelsBackend) | implicit level / dimension &str -> LevelRef; String -> Option<BlockKey> | DIFFERENT SHAPE |
| `native_with_mod_block_entity` | 369 | 18 | `block_entity(level,pos)` + `BlockEntityRef` reads/writes; in its own tick, the `block_entity_tick` Part arg; see the block-entity section (host/block_entities.rs:11, BlockEntitiesHost) | closure over `&mut ModBlockEntity` -> separate data/item/data-slot calls | DIFFERENT SHAPE |
| `native_on` | 222 | 20 | `on` (host/config.rs:27, ConfigHost) | none | SAME |
| `native_acting_id` | 191 | 18 | `players().acting_player()`, or the `player: u128` hook arg (use_item, use_on) (host/services.rs:240, Players) | u128 (host when none) -> Option<PlayerRef>; no host fallback | DIFFERENT SHAPE |
| `native_acting_player` | 114 | 19 | `players().acting_player()` + `player_*` reads on the handle (host/services.rs:240, Players) | `NativeServerPlayer` snapshot (x, y, z, yaw, sneaking...) -> handle; each field is its own read | DIFFERENT SHAPE |
| `native_mod_block_entity` | 95 | 12 | `block_entity(level,pos)` + `block_entity_data` / `block_entity_item_slot` / `block_entity_data_slots`; see the block-entity section (host/block_entities.rs:11, BlockEntitiesHost) | pos only -> LevelRef + pos; one `ModBlockEntity` copy -> three reads | DIFFERENT SHAPE |
| `native_default_state` | 80 | 17 | `block_state_default` (host/block_states.rs:39, BlockStatesHost) | block &str -> BlockKey; BlockStateId -> BlockState | DIFFERENT SHAPE |
| `native_fill` | 79 | 4 | `DrawContext::fill` (host/draw.rs:43, DrawContext) | `batch: &mut HudBatch` -> draw context receiver | RENAMED |
| `native_carried_stack` | 71 | 9 | none as a `&mut`. Read the `stack` arg of `inventory_tick`, write with `player_set_inventory_slot` (host/players.rs:1186, PlayersBackendMut) | `Option<&mut ItemStack>` (edit in place) -> read copy + explicit write | DIFFERENT SHAPE |
| `native_set_block` | 70 | 17 | `level_set_block` (host/levels.rs:937, LevelsBackendMut) | dimension -> LevelRef; BlockStateId -> BlockState; flags i32 -> BlockUpdateFlags; bool -> Result | DIFFERENT SHAPE |
| `native_sneaking` | 69 | 17 | `entity_is_shift_key_down` / `player_is_secondary_use_active` on the acting player (host/players.rs:314, PlayersBackend) | implicit acting player -> PlayerRef; bool -> Option<bool> | DIFFERENT SHAPE |
| `native_give_stack` | 52 | 19 | `player_give_stack` (host/players.rs:1214, PlayersBackendMut) | uuid u128 -> PlayerRef; leftover Option<ItemStack> -> Result<(), PlayerDataRefusal> (leftover handling not checked) | DIFFERENT SHAPE |
| `native_block_property` | 46 | 11 | `level_block_property` (host/levels.rs:357, LevelsBackend) | implicit level / dimension &str -> LevelRef | DIFFERENT SHAPE |
| `native_action_bar` | 44 | 15 | `player_action_bar` (host/players.rs:599, PlayersBackendMut) | uuid u128 -> PlayerRef; bool -> Result<bool, TextFormError> | DIFFERENT SHAPE |
| `native_neighbor_signal` | 44 | 11 | `level_best_neighbor_signal` (host/levels.rs:524, LevelsBackend) | dimension -> LevelRef; i32 -> Option<i32> | DIFFERENT SHAPE |
| `native_state_block` | 42 | 7 | `block_state_string` / `LevelHost` state reads (host/block_states.rs:33, BlockStatesHost) | BlockStateId -> BlockState; name -> full state string | DIFFERENT SHAPE |
| `native_text` | 42 | 3 | `DrawContext::text` (host/draw.rs:70, DrawContext) | batch -> receiver; `rgb` -> `argb` | RENAMED |
| `native_server_players` | 39 | 13 | `players().server_players()` + reads (host/services.rs:219, Players) | `Vec<NativeServerPlayer>` snapshots -> `Vec<PlayerRef>` | DIFFERENT SHAPE |
| `native_player` | 37 | 11 | `local_player()` (client) or `players().acting_player()` + reads (host/menus.rs:67, MenusClientHost) | `NativePlayer` snapshot -> handle | DIFFERENT SHAPE |
| `native_energy_insert` | 36 | 9 | `energy_insert` / `ENERGY` handler `insert` (host/fluids_energy.rs:48, FluidsEnergyBackendMut) | implicit level -> BlockSide; i32 + `simulate` -> u32 + Transaction | DIFFERENT SHAPE |
| `native_held` | 36 | 8 | `living_hand_item(player, Hand::Main)` (host/living.rs:199, LivingBackend) | implicit player -> LivingRef; (item, count, plain) -> ItemStack | DIFFERENT SHAPE |
| `native_set_block_property` | 34 | 9 | `set_block_property` (host/block_states.rs:69, BlockStatesServerHost) | `ticks: &mut Ticks` and `flags` params gone | DIFFERENT SHAPE |
| `native_entity` | 31 | 9 | `entity(id)` (host/entities.rs:14, EntitiesHost) | none | SAME |
| `native_tell` | 28 | 10 | `player_tell` (host/players.rs:593, PlayersBackendMut) | uuid u128 -> PlayerRef; bool -> Result<bool, TextFormError> | DIFFERENT SHAPE |
| `native_block_entity_sync` | 26 | 7 | `block_entity_sync` (host/block_entities.rs:35, BlockEntitiesServerHost) | none | SAME |
| `native_insert_item` | 26 | 9 | `container_insert` / `ITEMS` handler (host/items.rs:410, ItemsBackendMut) | pos, face -> BlockSide + slot; stack -> ItemResource + amount + Transaction | DIFFERENT SHAPE |
| `native_container_slots` | 25 | 6 | `container_size` + `container_stack` / `container_listing` on a `BlockSide`, or the `ITEMS` capability (host/items.rs:264, ItemsBackend) | dimension, pos, face -> BlockSide; `NativeContainerSlot` list -> stacks | DIFFERENT SHAPE |
| `native_max_stack_size` | 25 | 12 | `max_stack_size` (host/items.rs:12, ItemsHost) | item &str -> ItemKey | DIFFERENT SHAPE |
| `native_hurt_entity` | 24 | 11 | `entity_hurt` (host/entities.rs:629, EntitiesBackendMut) | dimension + id -> EntityRef; attacker u32 -> direct/causing EntityRef; bool -> Option<bool> | DIFFERENT SHAPE |
| `native_mobs` | 24 | 5 | `level_all_entities` + `mob` (host/levels.rs:288, LevelsBackend) | `Vec<NativeMob>` -> handles | DIFFERENT SHAPE |
| `native_item_entities` | 23 | 8 | `level_entities_in` + `item_entity` + `item_entity_stack` (host/item_entities.rs:21, ItemEntitiesBackend) | one list of `NativeItemEntity` -> per-entity reads | DIFFERENT SHAPE |
| `native_level_entities` | 23 | 10 | `level_all_entities` (host/levels.rs:288, LevelsBackend) | (id, kind, pos) tuples -> EntityRef list | DIFFERENT SHAPE |
| `native_take_items` | 23 | 9 | none direct: `player_inventory` + `player_set_inventory_slot` (host/players.rs:1186, PlayersBackendMut) | one call -> read, compute, write per slot | DIFFERENT SHAPE |
| `native_item_energy` | 22 | 6 | `ItemPlace::capability(host, &ITEM_ENERGY)` -> `EnergyHandler::amount/capacity` | works on a free stack -> needs an ItemPlace (a slot) | DIFFERENT SHAPE |
| `native_level_random` | 21 | 3 | `level_random`, or the `LevelRandomHost` a level hook gets (host/levels.rs:633, LevelsBackend) | `&mut LegacyRandom` (draws advance the level) -> `Option<LegacyRandom>` copy (not checked whether draws write back) | DIFFERENT SHAPE |
| `native_set_item_entity` | 21 | 8 | `item_entity_set_stack` (host/item_entities.rs:67, ItemEntitiesBackendMut) | dimension + id -> ItemEntityRef; bool -> Result<bool, _> | DIFFERENT SHAPE |
| `native_update_signal_neighbors` | 21 | 8 | `level_update_neighbors` / `level_neighbor_changed` (host/levels.rs:1531, LevelsBackendMut) | as above | DIFFERENT SHAPE |
| `native_run_command` | 20 | 7 | `commands().run_command` (host/services.rs:145, Commands) | none | SAME |
| `native_summon` | 19 | 9 | `summon` (host/entities.rs:63, EntitiesServerHost) | none | SAME |
| `native_add_effect` | 17 | 11 | `living_add_effect` (host/living.rs:357, LivingBackendMut) | uuid u128 -> PlayerRef (LivingRef); `NativeEffect` -> `ActiveEffect` | DIFFERENT SHAPE |
| `native_client_action_bar` | 17 | 12 | none found on the client host (only server `player_action_bar`) | - | NONE |
| `native_energy` | 16 | 6 | `energy_amount` + `energy_capacity`, or `ENERGY` capability (host/fluids_energy.rs:15, FluidsEnergyBackend) | dimension, pos, face -> BlockSide; `NativeEnergy` -> two u32 reads | DIFFERENT SHAPE |
| `native_fluid_insert` | 15 | 6 | `fluid_tank_insert` / `FLUIDS` handler (host/fluids_energy.rs:62, FluidsEnergyBackendMut) | pos, face -> BlockSide + tank index; fluid &str + i32 -> FluidStack; Transaction | DIFFERENT SHAPE |
| `native_machine_destroy_block` | 15 | 7 | `level_destroy_block` (host/levels.rs:978, LevelsBackendMut) | implicit level / dimension &str -> LevelRef; adds `drop`; Option<Vec> -> Result<Option<Vec>, _> | DIFFERENT SHAPE |
| `native_set_flight` | 14 | 7 | `player_abilities` + `player_set_abilities` (host/players.rs:784, PlayersBackendMut) | uuid u128 -> PlayerRef; (allow, flying) -> whole `PlayerAbilities` struct | DIFFERENT SHAPE |
| `native_set_player_status` | 14 | 6 | `living_set_health` + `player_set_food_level`/`_saturation`/`_exhaustion` + `player_set_experience_points`/`_levels` (host/players.rs:917, PlayersBackendMut) | one call with three optional groups -> up to six calls | DIFFERENT SHAPE |
| `native_weather` | 13 | 6 | `level_weather` (host/levels.rs:600, LevelsBackend) | implicit level -> LevelRef; Option | DIFFERENT SHAPE |
| `native_day_time` | 12 | 5 | `level_day_time` (host/levels.rs:432, LevelsBackend) | implicit level / dimension &str -> LevelRef; i64 -> Option<i64> | DIFFERENT SHAPE |
| `native_player_food` | 12 | 5 | `player_food` (host/players.rs:422, PlayersBackend) | uuid u128 -> PlayerRef; (i32, f32, f32) -> `PlayerFood` | DIFFERENT SHAPE |
| `native_attribute` | 11 | 2 | `living_attribute_base` + `living_attribute_value` (host/living.rs:157, LivingBackend) | uuid u128 -> PlayerRef; one call returning (base, value) -> two calls | DIFFERENT SHAPE |
| `native_change_mod_block_entity` | 11 | 1 | `block_entity(level,pos)` + `block_entity_merge_data`/`replace_data`/`set_item_slot`/`set_data_slot`; see the block-entity section (host/block_entities.rs:126, BlockEntitiesBackendMut) | closure over `&mut ModBlockEntity` -> separate writes; items need a Transaction | DIFFERENT SHAPE |
| `native_extract_item` | 11 | 6 | `container_extract` (host/items.rs:422, ItemsBackendMut) | dimension, pos, face -> BlockSide; count u32 -> max u32 + Transaction | DIFFERENT SHAPE |
| `native_light` | 11 | 6 | `level_brightness` (twice, per `LightLayer`) (host/levels.rs:379, LevelsBackend) | implicit level / dimension &str -> LevelRef; (u8, u8) -> two Option<i32> calls | DIFFERENT SHAPE |
| `native_fluid_tanks` | 10 | 6 | `fluid_tank_count` + `fluid_tank` + `fluid_tank_capacity` (host/fluids_energy.rs:29, FluidsEnergyBackend) | one list -> per-tank reads | DIFFERENT SHAPE |
| `native_item_from_snbt` | 10 | 3 | `item_from_snbt` (host/items.rs:64, ItemsHost) | none | SAME |
| `native_level` | 10 | 4 | `level(dimension)` (host/entities.rs:39, EntitiesHost) | none | SAME |
| `native_player_persistent_data` | 10 | 4 | `player_persistent_data` (host/players.rs:399, PlayersBackend) | uuid u128 -> PlayerRef; Tag -> Compound | DIFFERENT SHAPE |
| `native_text_width` | 10 | 3 | `DrawContext::text_width` (host/draw.rs:96, DrawContext) | none | SAME |
| `native_chunk_is_loaded` | 9 | 4 | `chunk_loaded` (via `level.chunk(...)`) (host/levels.rs:231, LevelsBackend) | dimension &str + [i32;2] -> ChunkRef | DIFFERENT SHAPE |
| `native_count_items` | 9 | 5 | none direct: `player_inventory` and count yourself (host/players.rs:378, PlayersBackend) | count of an item -> full inventory list | DIFFERENT SHAPE |
| `native_item_energy_insert` | 9 | 4 | `ITEM_ENERGY` handler `insert` | as above | DIFFERENT SHAPE |
| `native_sprite` | 9 | 1 | `DrawContext::sprite` (host/draw.rs:60, DrawContext) | batch -> receiver; adds `tint: Option<u32>` | DIFFERENT SHAPE |
| `native_world_dir` | 9 | 5 | `world_dir` (host/config.rs:168, ConfigServerHost) | none | SAME |
| `native_world_height` | 9 | 5 | `level_height` (host/levels.rs:386, LevelsBackend) | implicit level -> LevelRef; Option | DIFFERENT SHAPE |
| `native_acting_entity` | 8 | 4 | `players().acting_player()` then the player's entity, or the hook's own `player_entity_id` arg (host/services.rs:240, Players) | u32 (0 = none) -> Option<PlayerRef>; entity id from the hook args | DIFFERENT SHAPE |
| `native_explode` | 8 | 5 | `level_explode` (host/levels.rs:1347, LevelsBackendMut) | implicit level / dimension &str -> LevelRef; `NativeBlast` -> `ExplosionInteraction` + `ExplosionSettings`; adds `source`; bool -> Result | DIFFERENT SHAPE |
| `native_fluid_extract` | 8 | 6 | `fluid_tank_extract` / `FLUIDS` handler (host/fluids_energy.rs:74, FluidsEnergyBackendMut) | BlockSide + tank index + Transaction; (String, i32) -> FluidStack | DIFFERENT SHAPE |
| `native_mob` | 8 | 3 | `mob(entity)` + `mob_*` / `living_*` reads (host/mobs.rs:12, MobsHost) | dimension + id -> EntityRef -> MobRef; `NativeMob` snapshot -> per-field reads | DIFFERENT SHAPE |
| `native_player_break_block` | 8 | 7 | `player_destroy_block` (host/players.rs:1081, PlayersBackendMut) | uuid u128 -> PlayerRef | DIFFERENT SHAPE |
| `native_push_mob` | 8 | 2 | `entity_push` / `entity_set_velocity` (host/entities.rs:643, EntitiesBackendMut) | dimension + id -> EntityRef | DIFFERENT SHAPE |
| `native_remove_mob` | 8 | 5 | `entity_discard` (host/entities.rs:784, EntitiesBackendMut) | dimension + id -> EntityRef | DIFFERENT SHAPE |
| `native_set_inventory_slot` | 8 | 4 | `player_set_inventory_slot` / `player_set_ender_chest_slot` (host/players.rs:1186, PlayersBackendMut) | uuid u128 -> PlayerRef; no `expected` compare-and-swap; no kind; returns () not the old stack | DIFFERENT SHAPE |
| `native_boss_bar` | 7 | 2 | `boss_bar`/`create_boss_bar` + `boss_bar_*` handle writes (host/boss_bars.rs:23, BossBarsServerHost) | one upsert call with `NativeBossBar` -> handle and one call per field | DIFFERENT SHAPE |
| `native_entity_nbt_in` | 7 | 5 | `entity(id)` + `entity_nbt` (host/entities.rs:547, EntitiesBackendMut) | dimension + id -> EntityRef | DIFFERENT SHAPE |
| `native_give_items` | 7 | 3 | none direct: build a stack, `player_give_stack` (host/players.rs:1214, PlayersBackendMut) | item &str + count, returns given -> stack, Result<(), _> | DIFFERENT SHAPE |
| `native_item_energy_extract` | 7 | 4 | `ITEM_ENERGY` handler `extract` in a Transaction | returns (moved, new stack) -> handler rewrites the item at its place | DIFFERENT SHAPE |
| `native_play_sound_in_place` | 7 | 3 | `level_play_sound` (host/levels.rs:1236, LevelsBackendMut) | implicit level -> LevelRef; `source: usize` -> `SoundSource` | DIFFERENT SHAPE |
| `native_set_block_entity` | 7 | 3 | `block_entity(level,pos)` + `block_entity_replace_data` (host/block_entities.rs:126, BlockEntitiesBackendMut) | SNBT &str -> Compound; needs an existing block entity | DIFFERENT SHAPE |
| `native_teleport_player` | 7 | 4 | `entity_teleport_to_level` (host/entities.rs:684, EntitiesBackendMut) | uuid u128 -> PlayerRef (EntityRef); yaw, pitch -> Option<[f32;2]> | DIFFERENT SHAPE |
| `native_block_collision` | 6 | 4 | `block_collision` (host/client_view.rs:10, ClientViewHost) | none | SAME |
| `native_effects` | 6 | 5 | `living_effects` (host/living.rs:37, LivingBackend) | uuid u128 -> PlayerRef; `NativeEffect` -> `ActiveEffect` | DIFFERENT SHAPE |
| `native_entity_nbt` | 6 | 3 | `entity_nbt` (host/entities.rs:547, EntitiesBackendMut) | none | SAME |
| `native_entity_set_fire` | 6 | 2 | `entity_set_remaining_fire_ticks` (host/entities.rs:893, EntitiesBackendMut) | none | RENAMED |
| `native_entity_set_velocity` | 6 | 3 | `entity_set_velocity` (host/entities.rs:643, EntitiesBackendMut) | none | SAME |
| `native_give_experience` | 6 | 4 | `player_give_experience_points` (host/players.rs:1014, PlayersBackendMut) | uuid u128 -> PlayerRef | DIFFERENT SHAPE |
| `native_inventory` | 6 | 3 | `player_inventory` / `player_ender_chest` (host/players.rs:378, PlayersBackend) | uuid u128 -> PlayerRef; `NativeInventoryKind` -> one method per kind | DIFFERENT SHAPE |
| `native_level_set_weather` | 6 | 4 | `level_set_weather` (host/levels.rs:1098, LevelsBackendMut) | none | SAME |
| `native_player_equipment` | 6 | 3 | `living_equipment` (host/living.rs:195, LivingBackend) | uuid u128 -> PlayerRef | DIFFERENT SHAPE |
| `native_biome` | 5 | 3 | `level_biome_at` (host/levels.rs:108, LevelsBackend) | implicit level / dimension &str -> LevelRef | DIFFERENT SHAPE |
| `native_entity_uuid` | 5 | 3 | `entity_uuid` (host/entities.rs:600, EntitiesBackendMut) | none | SAME |
| `native_experience_orbs` | 5 | 4 | `experience_orbs` (host/entities.rs:91, EntitiesServerHost) | `NativeExperienceOrb` -> `ExperienceOrb` (fields not checked) | SAME |
| `native_force_chunk_in` | 5 | 2 | `chunk_set_mod_forced` (host/levels.rs:924, LevelsBackendMut) | as above, with a level | DIFFERENT SHAPE |
| `native_held_stack` | 5 | 3 | `living_hand_item` (host/living.rs:199, LivingBackend) | uuid u128 -> PlayerRef + hand | DIFFERENT SHAPE |
| `native_level_block_entities` | 5 | 4 | `level_block_entities` (host/levels.rs:84, LevelsBackend) | whole level -> min/max box; (pos, id) -> `BlockEntityAt` | DIFFERENT SHAPE |
| `native_lightning_bolt` | 5 | 3 | `level_strike_lightning` (host/levels.rs:1443, LevelsBackendMut) | dimension -> LevelRef | DIFFERENT SHAPE |
| `native_send_particles` | 5 | 3 | `level_send_particles` (host/levels.rs:1254, LevelsBackendMut) | implicit level / dimension &str -> LevelRef; BlockStateId -> BlockState | DIFFERENT SHAPE |
| `native_set_experience_orb` | 5 | 3 | `set_experience_orb` (host/entities.rs:75, EntitiesServerHost) | `value: Option<u32>` -> `Option<i32>` | SAME |
| `native_set_mob_health` | 5 | 3 | `living_set_health` (host/living.rs:436, LivingBackendMut) | dimension + id -> LivingRef | DIFFERENT SHAPE |
| `native_spawn_mob` | 5 | 3 | `level_spawn_mob` (host/levels.rs:845, LevelsBackendMut) | dimension -> LevelRef; `NativeSpawn` options -> `SpawnReason`; u32 -> EntityRef | DIFFERENT SHAPE |
| `native_block_entity_nbt` | 4 | 4 | `block_entity(level, pos)` + `block_entity_data` (host/block_entities.rs:58, BlockEntitiesBackend) | implicit level / dimension &str -> LevelRef; SNBT String -> Compound | DIFFERENT SHAPE |
| `native_block_entity_tag` | 4 | 2 | `block_entity(level, pos)` + `block_entity_data` (host/block_entities.rs:58, BlockEntitiesBackend) | implicit level / dimension &str -> LevelRef; Tag -> Compound | DIFFERENT SHAPE |
| `native_clock` | 4 | 2 | `clock` (client) (host/client_view.rs:53, ClientViewClientHost) | `NativeClock` -> `Clock` (fields not checked) | SAME |
| `native_entity_kind` | 4 | 4 | `entity_kind` (host/entities.rs:168, EntitiesBackend) | Option<String> -> Option<EntityTypeKey> | DIFFERENT SHAPE |
| `native_entity_velocity` | 4 | 2 | `entity_velocity` (host/entities.rs:234, EntitiesBackend) | none | SAME |
| `native_give_levels` | 4 | 2 | `player_give_levels` (host/players.rs:1020, PlayersBackendMut) | uuid u128 -> PlayerRef | DIFFERENT SHAPE |
| `native_item_fluid_drain` | 4 | 3 | `ITEM_FLUIDS` handler `extract` | free stack -> ItemPlace + Transaction | DIFFERENT SHAPE |
| `native_level_is_raining` | 4 | 2 | `level_is_raining` (host/levels.rs:604, LevelsBackend) | none | SAME |
| `native_may_build` | 4 | 2 | `player_may_build` (vanilla ability only) (host/players.rs:416, PlayersBackend) | old asked every mod's `can_build` for a pos and action; new takes only the player | DIFFERENT SHAPE |
| `native_merge_entity_nbt` | 4 | 3 | `entity(id)` + `entity_merge_nbt` (host/entities.rs:556, EntitiesBackendMut) | dimension + id -> EntityRef | DIFFERENT SHAPE |
| `native_move_fluids` | 4 | 3 | `mod_api::move_resources` with two `FLUIDS` capabilities (content/resource.rs:590) | as above | DIFFERENT SHAPE |
| `native_move_items` | 4 | 2 | `mod_api::move_resources` with two `ITEMS` capabilities (content/resource.rs:590) | as above; item filter is a closure | DIFFERENT SHAPE |
| `native_pick_block` | 4 | 3 | `level_clip` (host/levels.rs:477, LevelsBackend) | eye + dir + range -> from/to; `fluids: bool` -> `ClipBlock`/`ClipFluid`; `NativeHit` -> `ClipHit` | DIFFERENT SHAPE |
| `native_push_player` | 4 | 3 | `push_player` (client) (host/players.rs:69, PlayersClientHost) | none | SAME |
| `native_set_player_persistent_data` | 4 | 3 | `player_set_persistent_data` (host/players.rs:1231, PlayersBackendMut) | uuid u128 -> PlayerRef; Tag -> Compound; bool -> Result | DIFFERENT SHAPE |
| `native_set_setting` | 4 | 1 | `set_setting` (host/config.rs:38, ConfigHost) | none | SAME |
| `native_chat` | 3 | 3 | `send_chat` (client) (host/network.rs:53, NetworkClientHost) | () -> Result<(), String> | RENAMED |
| `native_component` | 3 | 2 | `ItemStack::components()` (vocab item/item_stack.rs:334) | per-id `Result<Option<&Tag>>` -> whole `Components` view (lookup API not checked) | DIFFERENT SHAPE |
| `native_energy_extract` | 3 | 1 | `energy_extract` / `ENERGY` handler `extract` (host/fluids_energy.rs:54, FluidsEnergyBackendMut) | i32 + `simulate` -> u32 in a Transaction (simulate = abort) | DIFFERENT SHAPE |
| `native_entity_position` | 3 | 3 | `entity_position` (host/entities.rs:153, EntitiesBackend) | none | SAME |
| `native_item_fluid` | 3 | 2 | `ItemPlace::capability(host, &ITEM_FLUIDS)` | free stack -> ItemPlace | DIFFERENT SHAPE |
| `native_level_is_thundering` | 3 | 2 | `level_is_thundering` (host/levels.rs:620, LevelsBackend) | none | SAME |
| `native_level_open` | 3 | 1 | `level(dimension).is_some()` / `level_in_place` (host/levels.rs:365, LevelsBackend) | dimension &str -> LevelRef | DIFFERENT SHAPE |
| `native_level_set_day_time` | 3 | 2 | `level_set_clock_time` (host/levels.rs:1009, LevelsBackendMut) | none | RENAMED |
| `native_open_menu_with_input` | 3 | 3 | none (no input-slot range; see `menu_input_closed`). Nearest: a MenuPart mod menu via `player_open_mod_menu` (host/players.rs:732, PlayersBackendMut) | - | NONE |
| `native_raycast` | 3 | 2 | `raycast` (client) (host/client_view.rs:57, ClientViewClientHost) | `NativeHit` -> `Hit` (fields not checked) | SAME |
| `native_remove_entity` | 3 | 3 | `entity_discard` / `entity_remove` (host/entities.rs:784, EntitiesBackendMut) | dimension + id -> EntityRef | DIFFERENT SHAPE |
| `native_set_block_property_with` | 3 | 1 | `set_block_property_with` (host/block_states.rs:77, BlockStatesServerHost) | none | SAME |
| `native_set_component` | 3 | 2 | `ItemStack::set_components(patch)` (vocab item/item_stack.rs:387) | per-id set -> component patch Compound | DIFFERENT SHAPE |
| `native_update_output_neighbors` | 3 | 3 | `level_update_neighbors` (host/levels.rs:1531, LevelsBackendMut) | dimension -> LevelRef; adds `source: BlockState`, `update: NeighbourUpdate`; bool -> Result | DIFFERENT SHAPE |
| `native_block_name_in_tag` | 2 | 2 | `block_in_tag` (host/tags.rs:21, TagsHost) | block &str -> BlockKey; Result<bool, _> -> Option<bool> | DIFFERENT SHAPE |
| `native_block_state_property` | 2 | 2 | `block_metadata_property` (or `LevelHost` state reads) (host/block_states.rs:97, BlockStatesBackend) | BlockStateId -> BlockStateRecord; Option -> Result<Option, _> | DIFFERENT SHAPE |
| `native_draw_quad` | 2 | 2 | `BlockEntityDrawContext::quad` (host/draw.rs:275, BlockEntityDrawContext) | `draw` arg becomes the receiver | RENAMED |
| `native_draw_text` | 2 | 2 | `BlockEntityDrawContext::text` (host/draw.rs:380, BlockEntityDrawContext) | receiver; `outline: u32` -> `Option<u32>`; f32 -> Result<f32, _> | DIFFERENT SHAPE |
| `native_entities_in` | 2 | 2 | `level_entities_in` (host/levels.rs:308, LevelsBackend) | implicit level / dimension &str -> LevelRef; Vec<u32> -> Option<Vec<EntityRef>> | DIFFERENT SHAPE |
| `native_entity_block_position` | 2 | 1 | `entity_block_position` (host/entities.rs:158, EntitiesBackend) | none | SAME |
| `native_entity_push` | 2 | 1 | `entity_push` (host/entities.rs:750, EntitiesBackendMut) | none | SAME |
| `native_entity_set_attribute_base` | 2 | 2 | `living_set_attribute_base` (host/living.rs:521, LivingBackendMut) | EntityRef -> LivingRef | RENAMED |
| `native_force_chunk` | 2 | 1 | `chunk_set_mod_forced` (host/levels.rs:924, LevelsBackendMut) | owner &str + [i32;2] -> ChunkRef + TicketController + TicketOwner | DIFFERENT SHAPE |
| `native_item` | 2 | 2 | `DrawContext::item` (host/draw.rs:65, DrawContext) | batch -> receiver; item &str -> ItemKey | DIFFERENT SHAPE |
| `native_item_fluid_fill` | 2 | 2 | `ITEM_FLUIDS` handler `insert` | as above | DIFFERENT SHAPE |
| `native_loot_odds` | 2 | 1 | none (`level_roll_loot` rolls, gives no odds) | - | NONE |
| `native_mob_navigate` | 2 | 2 | `mob_move_to` (host/mobs.rs:312, MobsBackendMut) | ids -> MobRef; `reach` param gone | DIFFERENT SHAPE |
| `native_move_energy` | 2 | 2 | `mod_api::move_energy` with two `ENERGY` capabilities (vocab item/energy_capability.rs:72) | positions + faces -> two Capability handles + Transaction; Result<u32, Overanswered> | DIFFERENT SHAPE |
| `native_player_compound` | 2 | 2 | none found (no player save-NBT read). Not checked: whether `entity_nbt` takes a player | - | NONE |
| `native_recipe_categories_version` | 2 | 1 | none (recipe viewer categories are gone) | - | NONE |
| `native_remove_effect` | 2 | 2 | `living_remove_effect` (host/living.rs:368, LivingBackendMut) | uuid u128 -> PlayerRef; id &str -> EffectKey | DIFFERENT SHAPE |
| `native_set_attributes` | 2 | 2 | none direct: `living_set_attribute_base` per attribute (host/living.rs:521, LivingBackendMut) | a saved attribute list Tag -> one call per attribute; modifiers via `living_add_attribute_modifier` (not checked) | DIFFERENT SHAPE |
| `native_setting` | 2 | 1 | `setting` (host/config.rs:32, ConfigHost) | none | SAME |
| `native_settings_refresh` | 2 | 1 | none (Options > Mods pages are gone) | - | NONE |
| `native_state_with_property` | 2 | 2 | `block_metadata_with` (or `LevelHost::state_with_property`) (host/block_states.rs:105, BlockStatesBackend) | BlockStateId -> BlockStateRecord; Option -> Result | DIFFERENT SHAPE |
| `native_teleport_mob` | 2 | 2 | `entity_teleport_to` (host/entities.rs:651, EntitiesBackendMut) | dimension + id -> EntityRef; adds rotation | DIFFERENT SHAPE |
| `native_use_as_player` | 2 | 1 | `fake_player` + `player_perform_action` (not checked that it covers useItemOn) (host/players.rs:26, PlayersServerHost) | one call -> make a fake player, then act | DIFFERENT SHAPE |
| `native_apply_screen_blur` | 1 | 1 | `apply_screen_blur` (host/screens.rs:53, ScreensClientHost) | none | SAME |
| `native_as_player` | 1 | 1 | none direct. `player_perform_action_scoped` runs a fixed `PlayerAction`, not a closure (not checked further) (host/players.rs:804, PlayersBackendMut) | closure with the player's state swapped in -> fixed action enum | NONE |
| `native_broadcast` | 1 | 1 | `messages().broadcast` (host/services.rs:206, Messages) | now returns Result<(), TextFormError> | SAME |
| `native_collect_recipe_categories` | 1 | 1 | none (recipe viewer categories are gone) | - | NONE |
| `native_config_dir` | 1 | 1 | `config_files()` (a `ConfigFiles` store, not a path) (host/config.rs:50, ConfigHost) | PathBuf -> `&dyn ConfigFiles` (API not checked) | DIFFERENT SHAPE |
| `native_cursor` | 1 | 1 | `cursor` (client input) (host/client_input.rs:18, ClientInputClientHost) | none | SAME |
| `native_data_dir` | 1 | 1 | `data_files()` (store) or `instance_dir()` (host/config.rs:57, ConfigHost) | per-mod PathBuf -> `&dyn ConfigFiles` (not checked) | DIFFERENT SHAPE |
| `native_draw_item` | 1 | 1 | `BlockEntityDrawContext::item` (the draw context is the receiver) (host/draw.rs:315, BlockEntityDrawContext) | `draw` arg becomes the receiver; `DisplayContext` -> `ItemDisplayContext` | RENAMED |
| `native_entity_dimensions` | 1 | 1 | `entity_dimensions` (host/entities.rs:332, EntitiesBackend) | none | SAME |
| `native_entity_eye_height` | 1 | 1 | `entity_eye_height` (host/entities.rs:252, EntitiesBackend) | none | SAME |
| `native_entity_fire_ticks` | 1 | 1 | `entity_fire_ticks` (host/entities.rs:486, EntitiesBackend) | none | SAME |
| `native_entity_merge_nbt` | 1 | 1 | `entity_merge_nbt` (host/entities.rs:556, EntitiesBackendMut) | none | SAME |
| `native_equipment` | 1 | 1 | `living_equipment` on the acting/local player (host/living.rs:195, LivingBackend) | implicit player -> LivingRef | DIFFERENT SHAPE |
| `native_feedback` | 1 | 1 | `commands().feedback` (host/services.rs:130, Commands) | now returns Result | SAME |
| `native_fluid_flow` | 1 | 1 | `level_fluid_flow` (host/levels.rs:454, LevelsBackend) | implicit level / dimension &str -> LevelRef; [f64;3] -> Vec3 | DIFFERENT SHAPE |
| `native_has_played_before` | 1 | 1 | none found. Option: a Player attachment flag set on first join | - | NONE |
| `native_kill_mob` | 1 | 1 | `kill_mob` (host/mobs.rs:21, MobsServerHost) | none | SAME |
| `native_mob_attack` | 1 | 1 | `mob_set_target` (host/mobs.rs:404, MobsBackendMut) | ids -> MobRef + LivingRef | DIFFERENT SHAPE |
| `native_mob_look_at` | 1 | 1 | `mob_look_at` (host/mobs.rs:458, MobsBackendMut) | dimension + id -> MobRef | DIFFERENT SHAPE |
| `native_mod_key` | 1 | 1 | `mod_key` (client) (host/client_input.rs:22, ClientInputClientHost) | `default` param gone; String -> Option<(String, ClientModifiers)> | DIFFERENT SHAPE |
| `native_muffle_sounds` | 1 | 1 | `muffle_sounds` (client) (host/effects.rs:20, EffectsClientHost) | none | SAME |
| `native_open_menu` | 1 | 1 | `open_menu` (host/menus.rs:20, MenusServerHost) | adds `replace: MenuReplace`; Option<i32> -> Result<Option<i32>, _> | DIFFERENT SHAPE |
| `native_player_stacks` | 1 | 1 | `player_inventory_slots` (host/players.rs:387, PlayersBackend) | uuid u128 -> PlayerRef; 36 slots `Vec<Option<ItemStack>>` -> `Vec<(u32, ItemStack)>` | DIFFERENT SHAPE |
| `native_recipes` | 1 | 1 | `recipes_of_type` / `known_recipes` (host/recipes.rs:29, RecipesHost) | one `Arc<NativeRecipes>` of everything -> per-type `Arc<[Recipe]>` | DIFFERENT SHAPE |
| `native_set_menu_items` | 1 | 1 | `menu_set_items` (host/menus.rs:54, MenusServerHost) | adds `window`; () -> Result | DIFFERENT SHAPE |
| `native_spawn_falling_block` | 1 | 1 | `spawn_falling_block` (host/entities.rs:103, EntitiesServerHost) | BlockStateId -> BlockState; `NativeFalling` -> `Falling` | SAME |
| `native_window` | 1 | 1 | `dist()` (host/config.rs:10, ConfigHost) | bool -> `Dist` enum | RENAMED |
| `native_world_seed` | 1 | 1 | `level_seed` (host/levels.rs:552, LevelsBackend) | implicit -> LevelRef | DIFFERENT SHAPE |

Not engine calls (excluded): `native_size` (local helper fn in 07_sf3_jei glue.rs:162); `native_key` (local helper fn in 07_sf3_jei glue.rs:133); `native_stack` (local closure in 07_sf3_jei glue.rs:667).

Verdicts, Table B: SAME 39 (445 calls), RENAMED 9 (139 calls), DIFFERENT SHAPE 123 (2769 calls), NONE 9 (31 calls).

## Mod block entities: what replaces `native_with_mod_block_entity` and `native_mod_block_entity`

Our use: 369 calls to `native_with_mod_block_entity(pos, |be| ...)` in 18 bundles, 95 to `native_mod_block_entity(pos)`
in 12, and 11 to `native_change_mod_block_entity` (1 bundle). Old shape: one closure gets `&mut ModBlockEntity` with
public fields `id`, `nbt: Compound`, `items: Vec<Option<ItemStack>>`, `data: Vec<i32>`, at a position in the level
"in place".

On main:

- `ModBlockEntity` lives in `horizon-mod-vocab/src/item/containers.rs:13`. Its fields are private. The part you can
  edit is `ModBlockEntityFields { nbt, items, data }`. There is no `id` field any more: the id is fixed when the entity
  is made.
- **Inside the block entity's own tick**, the `block_entity_tick` BlockEntityPart method gets the entity as a
  `ModBlockEntityView` (vocab `block/types.rs:64`). It derefs to `ModBlockEntityFields`, so `view.nbt`, `view.items`
  and `view.data` read and write as before, plus `set_client_update_fields`. A `BlockEntityTickReply::Unchanged` reply
  throws away this Part's edits. `menu_button` also still gets `entity: &mut ModBlockEntity`. These tick-side uses
  port with little change.
- **Anywhere else** (right click, wrench, a neighbour machine, a command): `host.block_entity(level, pos)`
  (`host/block_entities.rs:11`, `BlockEntitiesHost`) gives a `BlockEntityRef` handle. Through that handle:
  - read: `block_entity_data` (the saved compound, vanilla's `saveWithoutMetadata`; line 58),
    `block_entity_item_slot(slot)` (line 88, returns `Result<Option<ItemStack>, BlockEntityItemError>`),
    `block_entity_data_slots` (line 83);
  - write: `block_entity_merge_data` and `block_entity_replace_data` (lines 116 and 126),
    `block_entity_set_item_slot(tx, slot, stack)` (needs a `&Transaction`), `block_entity_set_data_slot(s)`,
    `block_entity_set_changed`;
  - `block_entity_sync` (line 35) is unchanged.
- **Differences that matter:**
  1. There is no single closure. A read-modify-write becomes read, compute, write. It is not atomic unless you wrap
     it in `host.transaction`.
  2. `merge_data` and `replace_data` work like `/data merge block`: each call loads the compound, calls `setChanged`
     and sends a block update to clients (their doc comment, just above line 116). Some of our machines call
     `native_with_mod_block_entity` several times a tick, and done this way each call would send an update. Batch the
     changes, or move the logic into the `block_entity_tick` Part, where edits cost nothing extra.
  3. **Not checked:** whether `block_entity_data` of a mod block entity returns exactly our `nbt` compound without
     `Items`. The doc says it is the vanilla save form, and for vanilla that includes `Items`.
  4. You must name the level (`LevelRef`). The old call used the level in place.
- The old private helper is still on main, as `pub(super) fn native_with_mod_block_entity` in
  `horizon-client/src/game/native_hooks/shared.rs:2074`, now taking `EngineBlockEntity`. It is not stable API. Only a
  `[[native.mixin]]` helper or support module inside that module's scope can reach it.

Verdict for all three: DIFFERENT SHAPE. The tick-side uses port easily. The rest is the largest single rewrite in this
map.

## No stable route

This lists every NONE row: what we use it for, and the least-bad option. "Target exists" means the function is still
on main, so a `[[native.mixin]]` row can still name it, with the new module path.

### Attach points (Table A)

| Target | Bundles and feature | Least-bad option |
|---|---|---|
| `native_mods` (19) | Every bundle except 07: lists the mod in Options > Mods (on/off switch, settings page) | Drop it. On main a mod is defined by its manifest. `on(mod_id)` (host/config.rs:27) still answers, and settings go through the `register_configs` hook (hk/mod_configs.rs, both sides, collects `Vec<mod_api::Config>`). The target is gone, so no mixin is possible. |
| `native_recipe_categories` (6) | 02 sieve/hammer/crook/barrel/crucible, 04 SAG Mill, 05 chickens, 08 steel chain, 09 Botania machines, 10 Blood Altar: JEI tabs | Target gone. Ask upstream for a recipe-viewer category hook, or let 07_sf3_jei own a registry that the other bundles call through a mod dependency (docs concepts/dependencies.md, not checked). |
| `native_menu_input_closed` (3) | 15 frequency pouch, 17 Bag of Holding, 19 accessory menu: items left in input slots go back to storage when the menu closes | Target gone. Try a MenuPart on a mod menu type (`player_open_mod_menu`, host/players.rs:732, plus `menu_slot_rules` and `menu_closed`), keeping the items in an attachment. Not checked whether `menu_closed` lets you read the slots. Otherwise ask upstream. |
| `native_world_primitives` (1) | 08 Immersive Engineering wires between connectors | Target gone. `render_level_stage` (hk/render_level_stage.rs, client side) draws into `WorldGeometry`. The host's `WorldDrawContext` has `lines` and `quads` (host/draw.rs). Not checked: which hook hands out a `WorldDrawContext`. |
| `native_chunk_generate` (2) | 01 void Overworld and starting island; 13 Chaos Islands and Ender Comets in the End | Target gone: `horizon_world::worldgen::native_generate` does not exist on main. For the void, use a data-driven flat/void dimension (main has `worldgen/generator/flat.rs`). Place the island and the Chaos Islands after generation with `edit_blocks` or `structure_template` (host/world_edit.rs), from `level_load` or `chunk_load` (`new = true`). Behaviour differs: blocks are placed after the chunk exists, on the server thread. A mixin into the generator internals is possible, but no target was checked. |
| `native_lod_column` (1) | 01 far-terrain LOD for the void world | Target gone. If the void comes from a real flat/void dimension, the LOD should follow it (not checked). |
| `draw_inventory`, `draw_creative`, `draw_options`, `draw_mod_browser`, `mod_browser_closed`, `draw_stack_tooltip_with` (2), `tooltip_box`, `tooltip_text` | 07 JEI overlay over container screens, cover over the options screen, tooltip ordering | Keep them as native mixins. All targets exist on main: `interface/inventory_slots.rs:422`, `interface/creative_screen.rs:108`, `interface/options.rs:181`, `modding/native_panel.rs:641` and `:881`, `blocks/stations/tooltip.rs:87`, `blocks/stations.rs:2154` and `:2209`. Their module paths drop the area folder. `draw_mod_browser` now returns `Option<BrowserTooltip>`, so its helper must change. Stable hooks worth trying first: `screen_render_post` (client side; gets `draw: &mut HudBatch` and `screen: &ScreenView`), `render_tooltip_pre`, `gui_layer_post`. Not checked whether they are enough. |
| `mob_death_canceled` | 13 Chaos Guardian death | Native mixin. The target exists at `native_hooks/living_death.rs:61` (its parameter is renamed `mob`). This mixin only forces `living_death` to fire. Not checked: whether a registered `living_death` listener is enough on main. |
| `spawn_hooks` (OVERWRITE) | 04 Spawn Guard and Relocator | Native mixin. The target exists at `mobs/natural_spawning.rs:882` with the same signature. It only forces the game to ask the spawn hooks. Not checked: whether a registered `potential_spawns` listener makes it unneeded. |

### Engine calls (Table B)

| Call | Bundles and feature | Least-bad option |
|---|---|---|
| `native_client_action_bar` (17 calls) | 06, 09, 10, 11, 12, 13, 14, 15, 16, 17, 19, 20: client-side status lines (mana, LP, energy readouts) | Send them from the server with `player_action_bar` (host/players.rs:599), or draw them in `gui_layer_post` for the `overlay_message` layer (hk/gui_layer_post.rs, not opened in detail). |
| `native_open_menu_with_input` (3) | 15, 17, 19: the menus above | Same as `native_menu_input_closed`. |
| `native_collect_recipe_categories`, `native_recipe_categories_version` (3) | 07: JEI reads every mod's categories | Same as `native_recipe_categories`. |
| `native_settings_refresh` (2) | 07: JEI's options page relabels mod pages | Gone along with Options > Mods. Drop it. |
| `native_player_compound` (2) | 09, 10: read saved attributes to restore them | Use `living_attribute_base`/`_value` and `living_attribute_modifiers` (host/living.rs) instead of the save compound. Not checked whether they cover modifiers. |
| `native_loot_odds` (2) | 04: drops of a block broken with no tool; fishing net | There is no odds API. `level_roll_loot` (host/levels.rs:1164) rolls a table, so you can sample rolls instead of computing odds (behaviour differs). Otherwise ask upstream. |
| `native_has_played_before` (1) | 01: starting kit on first join | Set a `Holder::Player` attachment flag on first join (concepts/attachments.md). |
| `native_as_player` (1) | 01 Veinminer: break the vein as the player, over several ticks | Call `player_destroy_block(player, pos, into_inventory)` (host/players.rs:1081) per block. It takes the player directly, so no state swap is needed. |

## Summary

These counts come from the script that wrote the tables:

| | SAME | RENAMED | DIFFERENT SHAPE | NONE |
|---|---|---|---|---|
| Table A targets (118) | 56 | 0 | 46 | 16 |
| Table A injections (457) | 169 | 0 | 245 | 43 |
| Table B engine functions (180) | 39 | 9 | 123 | 9 |
| Table B call sites (3,384) | 445 | 139 | 2,769 | 31 |

About a third of the injections (169 of 457) and about a sixth of the call sites (584 of 3,384, SAME plus RENAMED)
need only a rename or a path change. The survey said 63 functions and 1,426 calls match by name. That overstated it: most host methods with
the same name now take handles (`PlayerRef`, `LevelRef`, `BlockSide`) and return `Result`, so the call site changes.

### Top 10 risks

1. **Mod block entity access** (475 calls, 18 bundles). Outside the tick there is no closure over
   `&mut ModBlockEntity`, every `merge_data` sends a client update, and item writes need a transaction. This is the
   biggest rewrite (04 alone has 664 engine calls).
2. **The "acting player" model is gone.** About 520 calls read the player whose state was swapped in:
   `native_acting_id` (191), `native_acting_player` (114), `native_carried_stack` (71), `native_sneaking` (69),
   `native_player` (37), `native_held` (36). On main the player comes in the hook arguments, or
   `players().acting_player()` returns a handle. Snapshots such as `NativeServerPlayer` no longer exist.
3. **Name trap: `use_item_on`.** Our `native_use_item_on` (8 bundles) is vanilla's `ItemStack.useOn`. On main that is
   `use_on` (ItemPart). Main's `use_item_on` is a different event, the block's `useItemOn`. The survey's name match was
   wrong here.
4. **Item and block hooks became Parts** (block_entity_*, use_*, tooltip, the block hooks...). They fire only for the
   types we register. Global listeners that also handled vanilla items or blocks need a Part per vanilla type.
5. **Side and contract changes.** `use_item`, `use_on`, `right_click_block`, `entity_interact`, `player_tick_post`,
   `level_tick_pre`/`_post` and `player_break_speed` now run on both sides. Several moved from cancel to replace
   (`Option<InteractionResult>`). Server-only logic that now also runs on the client is a silent bug.
6. **07_sf3_jei has no stable route at all**: recipe categories (6 bundles feed it), 8 raw draw mixins, the mod
   browser. It stays a native-mixin bundle with new target paths, and `draw_mod_browser` changed its return type.
7. **World generation hooks are gone** (`native_chunk_generate`, `native_lod_column`). This hits 01's void world and
   island and 13's Chaos Islands. It needs a data-driven void dimension plus placement after generation, or a mixin
   into the generator internals.
8. **Storage became capabilities with transactions.** Container, fluid and energy declarations move to registration.
   Per-slot and per-tank vetoes (`container_accepts` in 8 bundles, `block_entity_accepts_fluid` in 6) need full
   handlers. `simulate` flags become aborted transactions. `native_energy_insert` (36 calls), `native_insert_item`
   (26) and similar calls all change shape.
9. **Item energy and fluids need an `ItemPlace`.** `ITEM_ENERGY` and `ITEM_FLUIDS` work on an item in a slot, not on a
   free stack (`native_item_energy*` 38 calls, `native_item_fluid*` 9). Code that charges stacks in a menu or a list
   must find the slot first.
10. **Menus with input slots** (15 pouch, 17 Bag of Holding, 19 accessories) and the **client action bar** (12
    bundles) have no stable route. Both need a design change or a request upstream.

### Not checked

- Fields of renamed structs (`LootDrops`, `Dispensed`, `Screen`, `Command`, `Clock`, `Hit`, `ExperienceOrb`,
  `Falling`, `PlayerFood`, `PlayerAbilities`) and of `BlockClick`.
- What `version = 2/3/4` changed on `projectile_impact`, `world_lifecycle` and `register_commands`, beyond the
  declared parameters.
- What the game returns from `block_entity_data` for mod block entities (whether `Items` is included).
- Names of the handle methods (`PlayerRef::tell`, `LevelRef::set_block`...) that wrap the backend methods named here.
- Stable alternatives for the JEI draw mixins, `world_primitives` and `menu_input_closed`, and mixin targets inside
  the world generator.
