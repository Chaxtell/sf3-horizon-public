> **Historical, implemented.** Design note written before bundle 02 was built. Not a plan: what to do next is in `MASS_PORT_PLAN.md`. Line numbers and the bundle names in section 5 are out of date; current wiring is in `SF3_REGISTRY.md` section 2.

# 02_sf3_exnihilo Hook Selection & Architecture Plan

Pinned engine commit: `horizon/` at `04a26210e3`. Host hooks live in `horizon/crates/horizon-client/src/game/native_hooks.rs` unless noted.

## 1. Hook Mapping (a) & `horizon-mixin.toml` Pattern

Follow `sf3-horizon/native/01_sf3_skyblock/mixins/sf3_skyblock/horizon-mixin.toml:29-106`: each `[[injection]]` defines `id`, `kind = "HEAD"`, `target = "horizon_client::game::native_hooks::<SelfTy>::<fn>"`, `helper = "<file>.rs"`, and `bindings`:
- `Game<'_>` hooks bind `{ name = "game", ty = "&mut crate::game::Game<'_>", value = "&mut *self" }` (or `&*self` for `&self`).
- `GameLevel<'_>` (`native_random_tick`) binds `{ name = "level", ty = "&mut crate::game::GameLevel<'_>", value = "&mut *self" }`.
- Static `native_block_entity_update_tag` binds parameters directly with no `self` binding.
- Out-params written by the mod must bind `&mut bool` with `value = "&mut *canceled"` (unlike `01_sf3_skyblock`'s read-only `&bool`).

| Mechanic | Hook(s) | `native-hooks.json` | Side | Exact Rust Signature (`native_hooks.rs`) | Out-param |
|---|---|---|---|---|---|
| **Hammer** (`exnihiloadscensio:hammer_*` on stone/cobble/gravel/sand) & **Crook** (sapling/silkworm on leaves) | `native_loot_drops` (+ `native_destroy_block` if handling creative/non-harvest tool breaks) | `loot_drops:1709` (`destroy_block:1149`) | `server` (`server`) | `pub(super) fn native_loot_drops(&mut self, context: &NativeLootDrops<'_>, drops: &mut Vec<ItemStack>)` (`9200-9204`); `pub(super) fn native_destroy_block(&mut self, pos: [i32; 3], state: BlockStateId, canceled: &mut bool)` (`8437-8443`) | `drops` (`collect`); `canceled` |
| **Silkworm** used on leaves -> `exnihiloadscensio:infested_leaves` | `native_use_item_on` | `use_item_on:1128` | `server` (`8154`) | `pub(super) fn native_use_item_on(&mut self, stack: &ItemStack, pos: [i32; 3], face: [i32; 3], claimed: &mut bool)` (`8156-8162`) | `claimed: &mut bool` |
| **Infested Leaves** spread & string drop | `native_random_tick` (spread) + `native_loot_drops` (string drops) | `random_tick:870`, `loot_drops:1709` | server level / `server` | `pub(super) fn native_random_tick(&mut self, ticks: &mut Ticks, dimension: LevelDimension, pos: BlockPos, state: BlockStateId, handled: &mut bool)` (`1580-1587`, on `GameLevel<'_>`) | `handled: &mut bool` |
| **Oak/Stone Barrel**, **Oak Sieve**, **Crucible** clicks | `native_right_click_block` | `right_click_block:1172` | `server` | `pub(super) fn native_right_click_block(&mut self, pos: [i32; 3], face: [i32; 3], canceled: &mut bool)` (`8464-8469`) | `canceled: &mut bool` |
| **Barrel / Sieve / Crucible** state & timers | `native_block_entity`, `_ticks`, `_tick`, `_update_tag` | `992, 1001, 1009, 1017` | server / chunk | `native_block_entity(&mut self, block: &str, entity: &mut Option<(String, Compound)>)` (`3214`); `native_block_entity_ticks(&self, block: &str, ticks: &mut bool)` (`3233`); `native_block_entity_tick(&mut self, pos: [i32; 3], entity: &mut ModBlockEntity)` (`3450`); `native_block_entity_update_tag(pos: [i32; 3], entity: &ModBlockEntity, tag: &mut Option<Compound>)` (`3472`) | `entity`, `ticks`, `entity` (mut), `tag` |

## 2. Host APIs Callable from Injected `crate::game` (b)

- **Read block / block below**:
  - `Game::native_block(&self, pos: [i32; 3]) -> String` (`native_hooks.rs:11390`), `Game::native_block_property(&self, pos: [i32; 3], key: &str) -> Option<String>` (`11422`), `Game::native_server_block(&self, context: &NativeLifecycleContext, dimension: &str, pos: [i32; 3]) -> Result<BlockState, NativeBlockReadError>` (`native_world_read.rs:106`). Query block below via `[pos[0], pos[1] - 1, pos[2]]`.
  - On `GameLevel<'_>` (`native_random_tick`): `self.block_state(at)` (`native_hooks.rs:10202`) + `self.registry.state(id)` (`10273`).
- **Set block**:
  - On `Game`: `Game::native_default_state(&self, block: &str) -> Option<BlockStateId>` (`native_hooks.rs:10753`) + `Game::native_set_block(&mut self, dimension: &str, pos: [i32; 3], state: BlockStateId, flags: i32) -> bool` (`10662`); `Game::native_set_block_property_with(&mut self, pos: [i32; 3], key: &str, value: &str, flags: i32) -> bool` (`10855`, or `native_set_block_property` at `10842`).
  - On `GameLevel<'_>`: `self.registry.default_state(block)` (`10222`) + `self.behaviours.set_block(self, ticks, at, id, flags)` (`10206-10207`), or `GameLevel::native_set_block_property(&mut self, ticks: &mut Ticks, pos: [i32; 3], key: &str, value: &str, flags: i32) -> bool` (`10190`).
- **Held item read / consume / damage**:
  - Read: `Game::native_held(&self) -> Option<(String, u32, bool)>` (`native_server.rs:1253`), `Game::native_held_stack(&self, uuid: u128) -> Option<ItemStack>` (`native_player_reads.rs:178`), `Game::native_equipment(&self, slot: EquipmentSlot) -> Option<ItemStack>` (`native_host_bridge.rs:97`).
  - Consume one: internal `pub(super)` `Game::consume_held(&mut self)` (`using_item.rs:57`, respects creative) or `Game::native_take_items(&mut self, item: &str, count: u32) -> u32` (`native_server.rs:1278`, plain items).
  - Damage tool: no `native_damage_*` public helper exists; call internal `pub(super)` `Game::damage_held(&mut self, amount: u32) -> bool` (`item_durability.rs:184`, respects creative & Unbreaking) or replace via `Game::native_living_set_equipment` (`native_living_refs.rs:124`).
- **Spawn item entity / give item to player**:
  - Give: `Game::native_give_items(&mut self, item: &str, count: u32) -> u32` (`native_server.rs:1303`) or `Game::native_give_stack(&mut self, uuid: u128, mut stack: ItemStack) -> Option<ItemStack>` (`1328`).
  - Spawn entity: internal `pub(super)` `Game::spawn_item(&mut self, stack: ItemStack, position: [f64; 3], velocity: [f64; 3], pickup_delay: u32)` (`item_entities.rs:649-656`), or `Game::native_summon(&mut self, dimension: &str, kind: &str, pos: [f64; 3], nbt: Compound) -> Option<u32>` (`native_entities.rs:215`; `commands/data.rs:1537` spawns `Target::Item`). In `native_loot_drops`, append directly to `drops`.
- **Particles / Sound**:
  - `Game::native_play_sound_in_place(&mut self, sound: &str, at: [f64; 3], source: usize, volume: f32, pitch: f32) -> bool` (`native_host_bridge.rs:55`) & `Game::native_send_particles_in_place(&mut self, options: &ParticleOptions, state: Option<BlockStateId>, at: [f64; 3], spread: [f64; 3], speed: f64, count: i32) -> bool` (`75`).
  - `GameLevel::native_play_sound(...)` (`native_hooks.rs:10119`) & `GameLevel::native_send_particles(...)` (`10149`).
- **Random source**: `Game::native_level_random(&mut self, dimension: &str) -> Option<&mut LegacyRandom>` (`native_hooks.rs:10763`), `GameLevel::native_level_random(&mut self) -> Option<&mut LegacyRandom>` (`10280`), or a deterministic local RNG (`01_sf3_skyblock/runtime.rs:112`).
- **Per-tick work**: `native_block_entity_ticks` + `native_block_entity_tick` (ticks loaded barrels/crucibles only), `GameLevel::native_schedule_block_tick(&self, ticks: &mut Ticks, pos: [i32; 3], block: &str, delay: i32) -> bool` (`native_hooks.rs:10215`) + `native_tick_block` (`1691`), or `native_server_tick` (`2464`).

## 3. Per-Block State & Persistence (c)

- **Built-in chunk NBT persistence**: Returning `Some((id, compound))` from `native_block_entity` (`native_hooks.rs:3214`) attaches a `ModBlockEntity` (`chunk/block_entity.rs:120-138`: `fields.id`, `nbt: Compound`, `items: Vec<Option<ItemStack>>`, `data: Vec<i32>`). `BlockEntity::Mod` is serialized/deserialized automatically in chunk NBT (`save.rs:638-648, 945-950`) across save/load and works on any `.hmod` template (`native_hooks.rs:3208-3213`).
- Read/mutate from interaction hooks via `Game::native_mod_block_entity(&self, pos: [i32; 3]) -> Option<&ModBlockEntity>` (`native_host_bridge.rs:26`), `Game::native_with_mod_block_entity(&mut self, pos: [i32; 3], f: impl FnOnce(&mut ModBlockEntity) -> R) -> Option<R>` (`native_hooks.rs:10932`, marks chunk modified), and `Game::native_block_entity_sync(&mut self, pos: [i32; 3]) -> bool` (`10962`) + `native_block_entity_update_tag` (`3472`).
- **World-dir fallback** (only needed for global/cross-chunk state in 04/06): `Game::native_world_dir(&self) -> Option<PathBuf>` (`native_server.rs:1117`), loaded/saved in `native_world_lifecycle` (`2287`: `WorldOpenReady` / `WorldCloseFinal`) and `native_world_saved` (`6472`).

## 4. `.hmod` Template Behaviour (d) & Random Tick (e)

- **(d) Template vanilla behavior**:
  - `exnihiloadscensio:wooden_barrel` (`template = "minecraft:barrel"`): inherits `Class::Barrel`; `interact.rs:432` emits `OpenMenu` (`game.rs:4939`) and short-circuits `use_hand.rs:202` before `native_use_item_on`. **Must** handle in `native_right_click_block` with `*canceled = true`.
  - `exnihiloadscensio:sieve` (`template = "minecraft:composter"`): `composter.rs:18` checks `!= "minecraft:composter"` and `interact.rs:300` only acts at `level == 8`; still cancel in `native_right_click_block` to prevent item/block fallthrough.
  - `exnihiloadscensio:stone_barrel`, `exnihiloadscensio:crucible` (`template = "minecraft:cauldron"`): `cauldron_at` (`game.rs:7805`) checks `ends_with("cauldron")`, so vanilla cauldron logic skips them, **but** right-clicking with water/lava buckets falls through to `BucketItem.use` (`use_hand.rs:280`, `game.rs:8083-8100`) and dumps fluids unless canceled in `native_right_click_block`.
- **(e) Random tick**: `native_random_tick` (`native_hooks.rs:1580`) exists and fires for `.hmod` blocks (`block_ticks.rs:249-262`, `game.rs:1308`) when `Behaviours::is_randomly_ticking` (`horizon-world/src/level/mod.rs:978`) is true, configured via `properties.random_ticks` (`horizon-mods/src/content.rs:90, 120-133`) or inherited from template. `exnihiloadscensio:infested_leaves` currently omits `random_ticks` so it inherits `minecraft:oak_leaves` decay; set `*handled = true` in `native_random_tick` (or override `random_ticks`) to suppress unwanted decay while spreading.

## 5. Bundles 03..06 Hook Plan (Hooks Only)

- **03_sf3_storage_tools** (Cobble gen, Drawers, Builder Wand): `native_world_lifecycle`, `native_block_entity`, `native_block_entity_ticks`, `native_block_entity_tick`, `native_block_entity_container`, `native_right_click_block`, `native_use_item_on`, `native_destroy_block`.
- **04_sf3_tech** (Energy graph, Generators): `native_world_lifecycle`, `native_world_saved`, `native_server_tick`, `native_block_entity`, `native_block_entity_ticks`, `native_block_entity_tick`, `native_block_entity_energy`, `native_block_entity_container`, `native_right_click_block`.
- **05_sf3_farming** (Roost, Crop growth): `native_random_tick`, `native_block_grow`, `native_block_entity`, `native_block_entity_ticks`, `native_block_entity_tick`, `native_block_entity_container`, `native_right_click_block`.
- **06_sf3_rs** (Refined Storage network & grid): `native_world_lifecycle`, `native_world_saved`, `native_server_tick`, `native_block_entity`, `native_block_entity_container`, `native_right_click_block`, `native_screen`, `native_screen_draw`, `native_screen_click`.
