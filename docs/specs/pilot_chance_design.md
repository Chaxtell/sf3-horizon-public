# Pilot design: `21_sf3_chance` on Horizon's stable mod API (2026-11-20)

Phase 1 steps 1.1 and 1.2 of `migration_stable_api_plan.md`. Design only: nothing in the project was changed except this
file.

Ground truth used:

- SDK of build `0a875da91dbb0fdcb7ba8c42c11341aa229af51a`, as fetched into
  `C:\Users\chaxt\.sf3-tools\pilot_tpl\.horizon\sdk`. Below, `vocab/` means
  `...\.horizon\sdk\api\crates\horizon-mod-vocab\`, and `gen-host` means
  `vocab/generated/mod_api_generated_host.rs` (the handle methods), `gen-hooks` means
  `vocab/generated/mod_api_generated.rs` (the `Hooks` trait and event structs).
- Docs: `horizon/docs/modding/src` (upstream main, `084ae44e40`; the SDK is a later build, so where the two could differ
  I read the SDK).
- Tool: `C:\Users\chaxt\.sf3-tools\main\bin\cargo-horizon-mod.exe`.
- Old bundle: `native/21_sf3_chance` (all files read), `docs/PLAYTEST_LOG.md` (lines 298-299, 499, 575, 1286),
  `SF3_REGISTRY.md` section "Slice 10M" (line 4002 on), `content/chancecubes/`.

**Everything marked "compiled" was built in the scratch mod `C:\Users\chaxt\.sf3-tools\scratch_design`** (a copy of the
template with id `sf3_chance`). There, the whole converted mod (`src/lib.rs` 352 lines, `src/sf3_host.rs`, the unchanged
`src/runtime.rs`, `src/fake_probe.rs`) passes `cargo check`, `cargo test` (30 tests: the 28 old ones plus 2 FakeHost
tests), `cargo horizon-mod check`, `cargo horizon-mod build` and `cargo horizon-mod check <the .hmod>`. That
`src/lib.rs` is the reference conversion; this file holds the parts that carry the design, in case the scratch folder
goes away.

Not checked anywhere: `horizon-launcher native-build` (needs launcher 0.2.92, installed 0.2.69) and any in-game
behaviour.

## 1. Target layout

```text
sf3-horizon/
  mods/
    sf3_host/
      sf3_host.rs          # the canonical adapter: one plain Rust module file, no Cargo.toml
    sf3_chance/            # one flat native mod, id `sf3_chance`
      horizon-mod.toml
      Cargo.toml
      Cargo.lock           # from `cargo horizon-mod new`
      .gitignore           # /target, /.horizon (from the template)
      src/
        lib.rs             # impl Hooks + ItemPart (the old glue.rs, rewritten)
        runtime.rs         # byte-identical copy of native/21_sf3_chance/mixins/sf3_chance/runtime.rs
        sf3_host.rs        # byte-identical copy of mods/sf3_host/sf3_host.rs
        glue_tests.rs      # FakeHost tests (#[cfg(test)])
  content/chancecubes/     # unchanged: the blocks and items stay a separate content mod
```

**Path dependency outside the mod: not allowed.** `how-to/native-mods/01-the-mods-crate.md` lines 43-45: "paths
escaping the mod, linked dependency paths, `[patch]`, `[replace]` ... are refused". `how-to/native-mods/03-data-files.md`
"Package contents": the archive takes only the manifest, root `Cargo.toml`/`Cargo.lock`/`build.rs`, `.rs` and `.toml`
under `src/`, `assets/`, `data/` and root text files; anything else refuses the archive. I also tried it: with
`sf3_host_probe = { path = "../scratch_pathdep" }` in the scratch mod, `cargo horizon-mod build` and `check` both still
passed and the `.hmod` held none of the dependency's code. So the tool does not catch it; the launcher would (per the
docs; not run).

**Alternative chosen: a shared source file copied into each mod.** `mods/sf3_host/sf3_host.rs` is the one place it is
edited; each mod carries a byte-identical copy at `src/sf3_host.rs` and declares `mod sf3_host;`. An acceptance check
compares the bytes (step 8). Why not the other routes:

- `#[path = "../../sf3_host/sf3_host.rs"] mod sf3_host;` compiles with cargo but the file is outside the package, so the
  launcher's build would not have it.
- A local crate inside the mod (`src/sf3_host/Cargo.toml`, allowed by "Local crates inside the mod are traversed") is
  still one copy per mod, plus a second Cargo package. No gain over one `.rs` file.
- `sf3_host` as its own mod that others depend on (`concepts/dependencies.md`, published root functions) works at run
  time but needs "API packages for the dependent and every installed dependency" and makes the adapter a runtime mod
  of its own. Too much for a thin adapter. Reconsider in Phase 2 if the copies become a burden.

The SDK itself is fetched per mod into `mods/sf3_chance/.horizon/sdk` by any `cargo horizon-mod` command
(`reference/sdk/03-in-a-project.md`); `Cargo.toml` must name it as `{ path = ".horizon/sdk/api/crates/horizon-mod-api" }`,
the only form the launcher accepts.

## 2. `sf3_host`: the minimal API for this bundle (25 functions, all compiled)

Rule: mod code calls `sf3_host`, never a host method or handle method. It may still use API value types (`PlayerRef`,
`ItemStack`, `Compound`, `Tag`, `BlockState`, events) and their plain value methods (`player.uuid()`,
`stack.damage()`, `stack.count()`), and it implements `Hooks` / `ItemPart`. The scratch `lib.rs` has no `host.` call
(grep).

Signatures use `&dyn Host` for reads (works with any `&mut dyn ServerHost` by reborrow) and `&mut dyn ServerHost` for
writes. Dimensions are passed as `&str` (`minecraft:overworld`), as the old calls took them; the function turns it into a
`LevelRef` with `host.level(dim)`.

| Function | Wraps (SDK) | Replaces (old) |
|---|---|---|
| `on(host: &dyn Host, mod_id: &str) -> bool` | `ConfigHost::on`, `vocab/src/host/config.rs:27` | `native_on` |
| `dimension(host: &dyn Host) -> &'static str` | `ConfigHost::dimension` ("the level in place, for a hook that isn't told"), `config.rs:62` | the implicit level of the old calls; `NativeServerPlayer.dimension` |
| `block_id(host: &dyn Host, dim: &str, pos: [i32;3]) -> Option<String>` | `EntitiesHost::level` (`host/entities.rs:39`) + `LevelRef::block` (`gen-host`, backend `level_block`, `host/levels.rs:336`) + `BlockKey::id` | `native_block` |
| `state_id(host: &dyn Host, state: BlockState) -> String` | `BlockState::block()` + `BlockKey::id` | `game.pack.assets.registry.state(state).name` |
| `set_block(host: &mut dyn ServerHost, dim, pos, block: &str) -> bool` | `KeysHost::block_key` (`host/keys.rs:22`) + `BlockStatesHost::block_state_default` (`host/block_states.rs:39`) + `LevelRef::set_block` (backend `level_set_block`, `levels.rs:922`), flags `NEIGHBORS \| CLIENTS` (= old 3) | `native_default_state` + `native_set_block` |
| `be_data(host: &dyn Host, dim, pos) -> Option<Compound>` | `BlockEntitiesHost::block_entity` (`host/block_entities.rs:11`) + `BlockEntityRef::data` (`block_entities.rs:58`) | `native_mod_block_entity`, `native_block_entity_tag` |
| `be_merge(host: &mut dyn ServerHost, dim, pos, data: Compound) -> bool` | `block_entity` + `BlockEntityRef::merge_data` (`block_entities.rs:116`) | `native_with_mod_block_entity` |
| `acting_player(host: &dyn ServerHost) -> Option<PlayerRef>` | `ServicesServerHost::players()` + `Players::acting_player` (`host/services.rs:240`) | `native_acting_player` |
| `player(host: &dyn Host, uuid: u128) -> Option<PlayerRef>` | `PlayersHost::player` (`host/players.rs:18`) | the uuid argument of the old player calls |
| `game_mode(host: &dyn Host, p: PlayerRef) -> Option<GameMode>` | `PlayerRef::game_mode` (backend `players.rs:404`) | `NativeServerPlayer.game_mode` (1, 3) |
| `main_hand(host: &dyn Host, p: PlayerRef) -> Option<ItemStack>` | `LivingHost::living` (`host/living.rs:15`) + `LivingRef::hand_item(Hand::Main)` (`living.rs:199`) | `game.held()` |
| `tell(host: &mut dyn ServerHost, p, line: &str) -> bool` | `PlayerRef::tell` (`players.rs:593`) | `native_tell` (+ the `native_chat` fallback, dropped) |
| `inventory_slots(host: &dyn Host, p) -> Vec<(u32, ItemStack)>` | `PlayerRef::inventory_slots` (`players.rs:387`): non-empty slots by number, 0-35 main | `native_inventory(.., Player)` |
| `set_slot(host: &mut dyn ServerHost, p, slot: u32, stack: Option<ItemStack>) -> bool` | `PlayerRef::set_inventory_slot` (`players.rs:1186`) | `native_set_inventory_slot` |
| `give(host: &mut dyn ServerHost, p, stack: ItemStack) -> bool` | `PlayerRef::give_stack` (`players.rs:1214`; overflow is thrown at the player) | `native_give_stack` + `game.spawn_item` for the leftover |
| `add_effect(host: &mut dyn ServerHost, p, id: &str, amplifier: i32, duration: i32) -> bool` | `KeysHost::effect_key` (`keys.rs:28`) + `living` + `LivingRef::add_effect` (`living.rs:357`), `ActiveEffect::new(key, duration, amplifier, false, true, true)` | `native_add_effect` + `NativeEffect` |
| `spawn_mob(host: &mut dyn ServerHost, dim, kind, at: [f64;3], name: Option<&str>) -> bool` | `LevelRef::spawn_mob(.., SpawnReason::Command)` (`levels.rs:830`) + `EntityRef::set_custom_name` (`entities.rs:576`) | `native_spawn_mob` + `NativeSpawn { name }` |
| `summon(host: &mut dyn ServerHost, dim, kind, at, nbt: Compound) -> bool` | `EntitiesServerHost::summon` (`entities.rs:63`) | `native_summon` |
| `run_command(host: &mut dyn ServerHost, line: &str) -> bool` | `commands()` + `Commands::run_command` (`services.rs:145`) | `native_run_command` |
| `item_id(host: &dyn Host, stack: &ItemStack) -> String` | `ItemStack::item()` + `ItemKey::id` | `stack.item` (was a `&str`) |
| `stack(host: &dyn Host, id: &str, count: u32) -> Option<ItemStack>` | `Identifier::parse` + `ItemsHost::item_key` (`host/items.rs:22`) + `ItemStack::new` | `ItemStack::new(id, count)` |
| `is_food(host: &dyn Host, stack: &ItemStack) -> bool` | the stack's component patch + `ItemsHost::item_default_component(item, "minecraft:food")` (`items.rs:30`) | `game.items().get(id).food` |
| `custom_data(stack: &ItemStack) -> Option<Compound>` | `ItemStack::components()` + `Components::as_nbt` (`vocab/src/item/item_stack.rs`) | `stack.custom_data()` |
| `set_custom_data(stack: &mut ItemStack, data: Compound) -> bool` | `ItemStack::apply_components` (`item_stack.rs:341`) | `stack.data_mut().set_other("minecraft:custom_data", ..)` |
| `nbt_get(c: &Compound, key: &str) -> Option<&Tag>` | `BTreeMap::get` | `nbt.get(&JavaString::from(key))`: the SDK does not export `JavaString` (only `Compound`, `vocab/generated/mod_api_exports_root.rs:149`), so a key cannot be named |

The last three need no host; they are in `sf3_host` because every bundle uses custom data and the `JavaString` gap
hits every NBT read.

The full file (compiled; copy it to `mods/sf3_host/sf3_host.rs`):

```rust
// sf3_host: the only file of an SF3 mod that calls Horizon's host. Canonical copy: sf3-horizon/mods/sf3_host/sf3_host.rs;
// each mod carries a byte-identical copy at src/sf3_host.rs (the launcher refuses paths outside the mod).
// Grown per bundle: a function is added only when a converted glue needs it.
#![allow(dead_code)]

use mod_api::{
    BlockState, BlockUpdateFlags, Compound, GameMode, Hand, Host, Identifier, ItemStack, PlayerRef, ServerHost,
    SpawnReason, Tag, Text,
};
use std::collections::BTreeMap;

// --- mods and levels ---

/// Whether the player left `mod_id` on in Options > Mods.
pub fn on(host: &dyn Host, mod_id: &str) -> bool {
    host.on(mod_id)
}

/// The level in place (`minecraft:overworld`), for a hook that names none.
pub fn dimension(host: &dyn Host) -> &'static str {
    host.dimension()
}

// --- blocks ---

/// The block at `pos` in `dim` (`minecraft:stone`); None for an unknown level.
pub fn block_id(host: &dyn Host, dim: &str, pos: [i32; 3]) -> Option<String> {
    let block = host.level(dim)?.block(host, pos)?;
    Some(block.id(host))
}

/// The block of a state a hook was given (`chancecubes:chance_cube`).
pub fn state_id(host: &dyn Host, state: BlockState) -> String {
    state.block().id(host)
}

/// Sets `block`'s default state at `pos` (vanilla flags 3: neighbours and clients). Whether it changed.
pub fn set_block(host: &mut dyn ServerHost, dim: &str, pos: [i32; 3], block: &str) -> bool {
    let Some(level) = host.level(dim) else { return false };
    let Some(state) = host.block_key(block).and_then(|key| host.block_state_default(key)) else { return false };
    level
        .set_block(host, pos, state, BlockUpdateFlags::NEIGHBORS | BlockUpdateFlags::CLIENTS)
        .unwrap_or(false)
}

// --- block entities ---

/// The saved data of the block entity at `pos`, None when there is none.
pub fn be_data(host: &dyn Host, dim: &str, pos: [i32; 3]) -> Option<Compound> {
    host.block_entity(host.level(dim)?, pos)?.data(host)
}

/// Merges `data` into the block entity at `pos` (`/data merge block`: one save, one client update). Whether it changed.
pub fn be_merge(host: &mut dyn ServerHost, dim: &str, pos: [i32; 3], data: Compound) -> bool {
    let Some(entity) = host.level(dim).and_then(|level| host.block_entity(level, pos)) else { return false };
    entity.merge_data(host, data).unwrap_or(false)
}

// --- players ---

/// The player whose action the running hook hears (`break_block`, `right_click_block`...).
pub fn acting_player(host: &dyn ServerHost) -> Option<PlayerRef> {
    host.players().acting_player()
}

/// The online player `uuid`.
pub fn player(host: &dyn Host, uuid: u128) -> Option<PlayerRef> {
    host.player(uuid)
}

pub fn game_mode(host: &dyn Host, player: PlayerRef) -> Option<GameMode> {
    player.game_mode(host)
}

/// The main-hand stack, None when empty.
pub fn main_hand(host: &dyn Host, player: PlayerRef) -> Option<ItemStack> {
    host.living(player.entity())?.hand_item(host, Hand::Main)
}

/// A system line in the player's chat. Whether it was shown.
pub fn tell(host: &mut dyn ServerHost, player: PlayerRef, line: &str) -> bool {
    player.tell(host, Text::literal(line.to_string())).unwrap_or(false)
}

/// The non-empty inventory slots, by number (0-35 main, 0-8 hotbar; 36-42 armour, off hand, body, saddle).
pub fn inventory_slots(host: &dyn Host, player: PlayerRef) -> Vec<(u32, ItemStack)> {
    player.inventory_slots(host).unwrap_or_default()
}

/// Puts `stack` (None empties it) in slot `slot`. No compare-and-swap. Whether it was written.
pub fn set_slot(host: &mut dyn ServerHost, player: PlayerRef, slot: u32, stack: Option<ItemStack>) -> bool {
    player.set_inventory_slot(host, slot, stack).is_ok()
}

/// `/give`: what does not fit is thrown at the player. Whether it was given.
pub fn give(host: &mut dyn ServerHost, player: PlayerRef, stack: ItemStack) -> bool {
    player.give_stack(host, stack).is_ok()
}

/// Effect `id` (`minecraft:speed`), amplifier from 0, duration in ticks, with particles. Whether it was added.
pub fn add_effect(host: &mut dyn ServerHost, player: PlayerRef, id: &str, amplifier: i32, duration: i32) -> bool {
    let (Some(key), Some(living)) = (host.effect_key(id), host.living(player.entity())) else { return false };
    living.add_effect(host, &mod_api::ActiveEffect::new(key, duration, amplifier, false, true, true))
}

// --- entities and commands ---

/// Spawns mob `kind` as a command spawn (finalizeSpawn runs), named `name`. Whether it spawned.
pub fn spawn_mob(host: &mut dyn ServerHost, dim: &str, kind: &str, at: [f64; 3], name: Option<&str>) -> bool {
    let Some(level) = host.level(dim) else { return false };
    let Some(mob) = level.spawn_mob(host, kind, at, SpawnReason::Command) else { return false };
    if let Some(name) = name {
        let _named = mob.set_custom_name(host, Some(Text::literal(name.to_string())));
    }
    true
}

/// `/summon kind at nbt` in `dim` (must be the level in place). Whether it joined.
pub fn summon(host: &mut dyn ServerHost, dim: &str, kind: &str, at: [f64; 3], nbt: Compound) -> bool {
    host.summon(dim, kind, at, nbt).is_some()
}

/// A console command (no slash, permission 4). Whether it ran without failing.
pub fn run_command(host: &mut dyn ServerHost, line: &str) -> bool {
    host.commands().run_command(line)
}

// --- items ---

/// The stack's item (`minecraft:apple`).
pub fn item_id(host: &dyn Host, stack: &ItemStack) -> String {
    stack.item().id(host)
}

/// `count` of item `id`; None for an unknown item or a count of 0.
pub fn stack(host: &dyn Host, id: &str, count: u32) -> Option<ItemStack> {
    let id = Identifier::parse(id).ok()?;
    ItemStack::new(host.item_key(&id)?, count)
}

/// Whether the stack is food (`minecraft:food`, on the stack or the item's default).
pub fn is_food(host: &dyn Host, stack: &ItemStack) -> bool {
    let own = stack.components().is_some_and(|c| nbt_get(c.as_nbt(), "minecraft:food").is_some());
    own || host.item_default_component(stack.item(), "minecraft:food").is_some()
}

/// The stack's `minecraft:custom_data` compound.
pub fn custom_data(stack: &ItemStack) -> Option<Compound> {
    match nbt_get(stack.components()?.as_nbt(), "minecraft:custom_data")? {
        Tag::Compound(c) => Some(c.clone()),
        _ => None,
    }
}

/// Replaces the stack's `minecraft:custom_data`. Whether the stack took it.
pub fn set_custom_data(stack: &mut ItemStack, data: Compound) -> bool {
    let patch = Compound::from([("minecraft:custom_data".into(), Tag::Compound(data))]);
    stack.apply_components(&patch).is_ok()
}

// --- nbt ---

/// `c[key]`. The SDK does not export the key type (`JavaString`), so this takes a `&str`.
pub fn nbt_get<'a, K: Ord + for<'s> From<&'s str>>(c: &'a BTreeMap<K, Tag>, key: &str) -> Option<&'a Tag> {
    c.get(&K::from(key))
}
```

Shape notes that change the glue: there is no compare-and-swap on `set_slot` (the old call passed the expected stack);
`give` drops the leftover itself, so the old `spawn_item` fallback goes; `tell` has no client-chat fallback; item and block
ids are now looked up by name through the host (`item_id`, `block_id`) because stacks and levels carry keys, not
strings. `block_id` allocates a `String` per call, as the old `native_block` did; the Torches reward reads up to
65^3 cells this way (unchanged cost model, not measured).

## 3. Hook-by-hook conversion

| Old attach point (helper file -> glue fn) | New route (compiled signature) | Differences that matter |
|---|---|---|
| `native_mods` (`list.rs`, pushes a `NativeMod`) | none; dropped | Options > Mods is built from the manifest. `on("sf3_chance")` still answers the player's switch (`config.rs:22-27`: "check this first in each hook"). `runtime::NAME/VERSION/DESCRIPTION` become unused (`#[allow(dead_code)]` on the `mod runtime;` line). |
| `native_block_entity` (`block_entity.rs` -> `glue::block_entity`: `Some(("sf3_chance:cube", {}))` for the cube) | a declaration in `Hooks::register`: `r.block_entity_type("cube").blocks(&[m::CUBE]).build()` (`vocab/src/parts/block_entities.rs:141`) | The type id is qualified with the mod's namespace, so `"cube"` is `sf3_chance:cube`, the same as `runtime::ENTITY`. The block is another mod's (`chancecubes:chance_cube`); full ids are kept as given (engine `horizon-mod-api/src/parts/block_entities.rs:381`, upstream main), and `owned_namespaces.rs` says "Parts may attach to vanilla or another mod's existing content". The `block_entity` Part method (`fn block_entity(&self, level: LevelSide, event: &mut BlockEntityEvent) -> Option<Compound>`, both sides, replace) is not needed: "other declared types start with an empty compound" (`vocab/src/hooks/block_entity.rs`). Not checked in game: that the template-dirt cube gets the entity with no Part attached. Fallback, compiled: an empty `struct CubeEntity;` with `#[mod_api::horizon_part] impl mod_api::BlockPart` and `impl mod_api::BlockEntityPart`, attached with `r.block_entity_part(&cube, CubeEntity).expect(..)`. |
| `native_destroy_block` (`destroy_block.rs` -> `glue::destroy_block(game, pos, canceled: &bool)`) | `fn break_block(&self, host: &mut dyn ServerHost, event: &mut BreakBlockEvent<'_>) -> Flow` (`gen-hooks:2077`; event fields `pos`, `state: BlockState`, `exp_to_drop: &mut Option<u32>`, `cancelled`) | Server, cancel, same moment (`ServerPlayerGameMode.destroyBlock` start). Cancelled events are not delivered unless `#[listener(receive_cancelled)]`, so the old `if *canceled { return }` goes. The block arrives as `event.state` (use `state_id`). No player in the event: `acting_player(host)` ("the helpers read the acting one", `hooks/break_block.rs`). No level in the event: `dimension(host)`. We never cancel; return `Flow::Continue`. `exp_to_drop` ignored. |
| `native_loot_drops` (`loot_drops.rs` -> `glue::loot_drops(game, context: &NativeLootDrops, drops)`) | `fn loot_drops(&self, host: &mut dyn ServerHost, event: &mut LootDropsEvent<'_>)` (`gen-hooks:2499`; `event.context: &LootDrops`, `event.drops: &mut Vec<ItemStack>`) | Server, collect. `LootDrops` fields read (`vocab/src/item/types.rs:122`): `block: Option<([i32;3], BlockState)>`, `tool: Option<&ItemStack>`, `player: Option<u128>`, `table`, `dimension`... The glue uses `block` and `tool` as before. Changed `drops` are validated by the game; a refused list is put back with a log line (`gen-hooks` `dispatch_loot_drops`). Doc: "A block's stacks get its block entity's data ... after this" (not checked whether that touches the cube item). |
| `native_right_click_block_v2` (`right_click_block_v2.rs` -> `glue::right_click_block_v2(game, pos, cancel: &mut bool)`) | `fn right_click_block(&self, host: HostSide, event: &mut RightClickBlockEvent<'_>) -> Flow` (`gen-hooks:2116`; `event.click: &BlockClick` with `side`, `dimension`, `pos`, `hit`, `hand`, `stack: Option<&ItemStack>`, `player: u128`; `event.cancellation_result: &mut InteractionResult`) | **Both sides now**: match `HostSide::Server(host)` and return `Flow::Continue` on the client. **Once per hand**: the held stack is `click.stack` for that hand (old code read `game.held()`, the main hand). Cancel is `Flow::Cancel` plus a result: the design sets `*event.cancellation_result = InteractionResult::Success` (ends the click as used, client swing). `Pass`, the default, would go on to the item's own use and the other hand. The old contract of `cancel = true` was not read at `04a26210e3`, so "Success" is a choice, not a copy. |
| `native_place_block` (`place_block.rs` -> `glue::place_block(game, stack, pos)`, fired for every placement) | `ItemPart::on_block_placed_by(&self, host: &mut dyn ServerHost, event: &mut OnBlockPlacedByEvent<'_>)` (`gen-hooks:9625`; `stack`, `placer: Option<PlayerRef>`, `pos`, `state`, `face`, `click`), attached with `r.item_part(r.item_key(m::CUBE), CubeItem)` (`vocab/src/parts/items.rs:105`) | Server, listen. Scoped: fires only for the cube item, so the old `stack.item != CUBE` filter goes. Runs after the block entity and stack data exist (`hooks/on_block_placed_by.rs` notes), so `be_merge` there is not overwritten. A dispenser placement has `placer = None`; the glue does not need the placer. Level from `dimension(host)`. The global alternative `entity_place` fires before the block is written, too early. |
| `native_server_tick` (`tick.rs` -> `glue::server_tick(game, phase)`) | `fn server_tick(&self, host: &mut dyn ServerHost, event: &mut ServerTickEvent<'_>)` (`gen-hooks:1962`; `event.context: &LifecycleContext`, `event.phase: ServerTickPhase`) | Server, listen, same phases (`ServerTickEnd { world_running }`). The jobs' clock moves from `game.world.game_time` to `event.context.tick.get()` (non-paused ticks since the world opened), stored in a `static NOW: AtomicU64`; `break_block` reads `NOW`, so no `game_time` host call is needed. The RNG seed uses `NOW` the same way. Hook doc: "which level self.world holds here is not defined" (see section 7). |
| `native_world_lifecycle` (`lifecycle.rs` -> `glue::world_lifecycle(phase)`) | `fn world_lifecycle(&self, host: &mut dyn ServerHost, event: &mut WorldLifecycleEvent<'_>)` (`gen-hooks:1912`; `context`, `phase: WorldPhase`, `error_text`) | Server, listen, version 2. Same three phases used (`WorldOpenFailed`, `WorldCloseFinal`, `WorldCloseFailed`; `WorldPhase` is `#[non_exhaustive]`, use `matches!`). |

The `Hooks` impl skeleton with the real event types (compiled; the bodies are in the scratch `lib.rs`):

```rust
#[allow(dead_code)] // NAME, VERSION, DESCRIPTION, ENTITY served the old Options > Mods entry
mod runtime;
mod sf3_host;
#[cfg(test)]
mod glue_tests;

use mod_api::{
    BreakBlockEvent, Compound, Flow, GameMode, HostSide, InteractionResult, ItemPart, LootDropsEvent,
    OnBlockPlacedByEvent, PlayerRef, Registrar, RegistrationContext, RightClickBlockEvent, ServerHost, ServerTickEvent,
    ServerTickPhase, Tag, WorldLifecycleEvent, WorldPhase,
};
use runtime::{self as m, Act, EntityTag};
use sf3_host as h;

#[derive(Default)]
struct Mod;

struct CubeItem;

#[mod_api::horizon_part]
impl ItemPart for CubeItem {
    fn on_block_placed_by(&self, host: &mut dyn ServerHost, event: &mut OnBlockPlacedByEvent<'_>) { /* custom_data Chance -> be_merge */ }
}

#[mod_api::horizon_mod]
impl mod_api::Hooks for Mod {
    fn register(&self, r: &mut dyn Registrar, _cx: &RegistrationContext) {
        let _cube = r.block_entity_type("cube").blocks(&[m::CUBE]).build();
        let item = r.item_key(m::CUBE);
        r.item_part(item, CubeItem);
    }
    fn world_lifecycle(&self, _host: &mut dyn ServerHost, event: &mut WorldLifecycleEvent<'_>) { /* clear JOBS, BROKEN, LAST */ }
    fn break_block(&self, host: &mut dyn ServerHost, event: &mut BreakBlockEvent<'_>) -> Flow { /* ... */ Flow::Continue }
    fn loot_drops(&self, host: &mut dyn ServerHost, event: &mut LootDropsEvent<'_>) { /* ... */ }
    fn right_click_block(&self, host: HostSide, event: &mut RightClickBlockEvent<'_>) -> Flow {
        let HostSide::Server(host) = host else { return Flow::Continue };
        /* ... */
        *event.cancellation_result = InteractionResult::Success;
        Flow::Cancel
    }
    fn server_tick(&self, host: &mut dyn ServerHost, event: &mut ServerTickEvent<'_>) {
        if !matches!(event.phase, ServerTickPhase::ServerTickEnd { world_running: true }) { return; }
        NOW.store(event.context.tick.get(), Ordering::Relaxed);
        /* take due JOBS, run each */
    }
}
```

Other glue changes, all in the scratch `lib.rs`: `Job.player` stays a `u128`, turned into a `PlayerRef` with `h::player`
when the job runs (an offline player's Say/Give/Effect/RottenFood steps are skipped); `pendant_bonus` and
`rotten_food` iterate `h::inventory_slots` and skip slots `>= 36`; a pendant's new damage is
`stack.clone()` + `set_damage`; NBT keys are written with `"Chance".into()` and read with `h::nbt_get`.

## 4. Content data and native code: two mods

- `content/chancecubes/` stays the content mod `chancecubes` (blocks, items, loot table, recipes; generated by
  `tools/extract_sf3_assets.py`, not hand-edited). It passed main's checks (`content_mods_check_2026-11-20.md`: not
  among the 13 failures).
- `mods/sf3_chance/` is a code-only native mod: no `assets/`, no `data/` (the template's empty folders are deleted).
  It names `chancecubes:*` ids only by string.

Why two and not one: the generator owns `content/chancecubes`; one merged folder would need the generator to write into
`mods/` or a hand copy. Nothing in the native code needs to own the `chancecubes` namespace (the block entity type is
`sf3_chance:cube`).

No `[dependencies]` entry on `chancecubes`. `r.item_key("chancecubes:chance_cube")` already refuses the load, naming
the mod and id, when the item is missing (`concepts/registry-keys.md`). A dependency row would add ordering only, and
"Code dependencies additionally require API packages for the dependent and every installed dependency"
(`concepts/dependencies.md`), whose effect on a content-only target I did not check.

`mods/sf3_chance/horizon-mod.toml` (the scratch copy with these fields passed `cargo horizon-mod check` and `build`):

```toml
id = "sf3_chance"
name = "SF3 Chance Cubes"
version = "0.1.0"
description = "Chance Cubes for SkyFactory 3: the cube's chance value and reward table, pendants, Scanner, Silk Touch Pendant."
authors = ["SF3-Horizon Cleanroom Team"]
api = "0.2"
side = "both"
capabilities = ["registries"]

[native]
game = "26.3"
horizon = "0a875da91dbb0fdcb7ba8c42c11341aa229af51a"
mixins = "e59da9094f0c2fdda6c627fe9eff22dec6a906f0"
```

- `capabilities = ["registries"]` is the only value the schema takes (`how-to/content-mods.md:115`), and the mod declares
  a block entity type.
- `side = "both"`: the block entity type must exist on the client too (`block_entity` fires "on a server and on a client
  of one").
- No `[[native.mixin]]`, `[[inject]]` or `internals`: everything is on stable hooks.
- `mods/sf3_chance/Cargo.toml`:

```toml
[package]
name = "mod-sf3_chance"
version = "0.1.0"
edition = "2024"

[dependencies]
horizon-mod-api = { path = ".horizon/sdk/api/crates/horizon-mod-api" }

[dev-dependencies]
horizon-mod-api = { path = ".horizon/sdk/api/crates/horizon-mod-api", features = ["testing"] }
```

The `testing` feature on a dev-dependency is allowed ("Features (`features = ["testing"]` on a dev-dependency) are
kept", `reference/sdk/03-in-a-project.md:13`); `E_NATIVE_FEATURES` refuses mod feature declarations, not this.

The old pins (`compatibility.lock.json`, `tools/native_win.py sync`, `compatibility.json`) do not apply to `mods/`: the pin
is `[native] horizon` and moves with `cargo horizon-mod update`.

## 5. `runtime.rs` unchanged

Copied byte for byte to `mods/sf3_chance/src/runtime.rs` and declared in `lib.rs` as:

```rust
#[allow(dead_code)] // NAME, VERSION, DESCRIPTION, ENTITY served the old Options > Mods entry
mod runtime;
```

It has no `crate::`/`super::` paths outside its own `mod tests` and no `//!` lines, so it works as a child module. Its
`#[cfg(test)] mod tests` runs under the mod's `cargo test`: in the scratch mod all 28 pass. The old crate under
`native/21_sf3_chance` stays as it is (the plan keeps the old build playable), so the copy is checked with `fc.exe /b`
(step 8). Tests must live under `src/`: a `tests/` folder is not a file the archive takes.

## 6. Tests on FakeHost

Probed in the scratch mod (`src/fake_probe.rs`): each `sf3_host` function called on `mod_api::testing::FakeHost`
(`vocab/src/testing.rs`), panics caught.

| Answers on FakeHost | Panics ("mod API X is unavailable during Packages": a method FakeHost does not implement) |
|---|---|
| `player`, `acting_player` (set `host.players.acting = Some(uuid)`), `stack`, `item_id`, `is_food` (after `host.registries.resolve_items`), `run_command` (lines kept in `host.commands.ran`), `custom_data`, `set_custom_data`, `nbt_get` | `on`, `dimension`, `be_data`, `be_merge`, `set_block` (`block_key`), `game_mode`, `main_hand` (`living`), `tell`, `inventory_slots`, `set_slot`, `give`, `add_effect` (`effect_key`), `spawn_mob`, `summon` |

`block_id` did not panic but returned `None` for a block set with `host.level.set_block([0,64,0], "minecraft:stone")`,
and so did a direct `LevelRef::block` on the fake level; the fake level is found by name. I did not find the setup that
resolves block keys in the fake.

So, glue paths:

- **Testable now:** the Command reward step (a due `Job` with `Act::Command` reaches `host.commands.ran` exactly as
  `runtime::render` writes it; compiled and passing as `a_command_job_runs_its_rendered_line`); the custom-data round
  trip used by the loot and place paths; `item_id`/`stack`/`is_food` used by Give and RottenFood.
- **Not testable on FakeHost:** `break_block` (needs `on`, `dimension`, `be_data`), the Scanner click, `loot_drops`
  (needs `state_id` and block keys), `on_block_placed_by` (`be_merge`), pendants and RottenFood (`inventory_slots`,
  `set_slot`), Say/Give/Effect/Mob/Entity/Block/Replace/Torches steps. These are covered by `runtime.rs` tests for the
  rules and by play (section 8).
- **Not checked:** driving a hook through `testing::with_mods` + `dispatch_<hook>`. The events hold
  `#[non_exhaustive]` types (`LifecycleContext`, `LootDrops`, `BlockClick`) that a mod cannot build, so the tests call
  the glue's own functions (`run`, `cube_chance`...) instead.

Writing our own test double for the missing methods (`concepts/testing.md` allows it) is possible but is speculative
work for one bundle; not proposed.

## 7. No stable route in this bundle, and the least-bad option

| What | Least-bad option |
|---|---|
| Options > Mods entry (`native_mods`) | Drop. The manifest names the mod; `on(id)` keeps the on/off switch. |
| `native_chat` fallback when `tell` fails (the client-local case) | Drop. On the server, `tell` false means the player is gone. |
| Compare-and-swap on inventory writes (old `expected` argument) | None in the API. The glue reads and writes in the same hook call, so nothing runs in between. |
| `NativeSpawn` defaults (old spawn reason) | Not read at `04a26210e3`. `SpawnReason::Command` (finalizeSpawn runs, as `/summon` would not). Change if mobs come out wrong in play. |
| The level in place during `server_tick` | `summon` takes a dimension but fails "for another dimension" than the level in place (`host/entities.rs:53-61`), and `LevelRef::set_block` can refuse a "nonactive write target" (`concepts/registry-keys.md`). `server_tick` says which level is in place "is not defined". The old bundle had the same shape and its rewards worked in play (PLAYTEST_LOG 575, 1286), so keep `server_tick`. If Entity, Block or Mob steps fail in play: run the jobs from `level_tick_post` (server side, gets the `LevelRef`) for the jobs of that level. Not compiled. |
| Whether `be_data` returns our `Chance`/`Scanned` keys at the top level | Not checked (`api_map.md`, block-entity section, point 3: the vanilla save form). Play-test step 2 below shows it. |
| Client side of the Scanner click | The client sees `Pass` and may predict nothing; the cube (dirt template) and the Scanner (iron ingot template) have no use of their own. Not checked in play. |
| `cargo horizon-mod check` warnings `Block` / `Command` "built field by field" | False positives: they point at our own `runtime::Act::Block` pattern and `Act::Command` value, which share names with API types. Nothing to fix. |

## 8. Steps for the conversion (Sonnet), and acceptance checks

Use PowerShell. Put the tool first on PATH in every shell:
`$env:PATH = "C:\Users\chaxt\.sf3-tools\main\bin;$env:PATH"`. Do not touch `native/21_sf3_chance`, `content/`,
`../horizon*`, `MASS_PORT_PLAN.md`. Reference: `C:\Users\chaxt\.sf3-tools\scratch_design\src\lib.rs` (compiled
conversion) and this file.

1. `cargo horizon-mod new mods\sf3_chance --name "SF3 Chance Cubes" --template native --horizon 0a875da91dbb0fdcb7ba8c42c11341aa229af51a`
   from `sf3-horizon/`. Expect `mods\sf3_chance\` with `horizon-mod.toml`, `Cargo.toml`, `Cargo.lock`, `src\lib.rs`, empty
   `assets\`, `data\`. (If `new` cannot fetch the SDK, copy `C:\Users\chaxt\.sf3-tools\pilot_tpl` without `target\` and
   rename the id; that is how the scratch mod was made.) Delete the empty `assets\` and `data\`.
2. Write `horizon-mod.toml` and `Cargo.toml` exactly as in section 4.
3. Create `mods\sf3_host\sf3_host.rs` with the code in section 2. Copy it to `mods\sf3_chance\src\sf3_host.rs`.
4. Copy `native\21_sf3_chance\mixins\sf3_chance\runtime.rs` to `mods\sf3_chance\src\runtime.rs` (`Copy-Item`, no edits).
5. Write `mods\sf3_chance\src\lib.rs`: the skeleton of section 3, with the bodies ported from the old `glue.rs` per the
   table in section 3 and the call table in section 2 (the scratch `lib.rs` is the worked answer). Rules: no `host.`
   call in `lib.rs`; every `native_*` becomes an `h::` call; LF line endings, UTF-8.
6. Write `mods\sf3_chance\src\glue_tests.rs` (`#[cfg(test)]`, declared in `lib.rs`): the test
   `a_command_job_runs_its_rendered_line` from the scratch `src\fake_probe.rs`, plus one test that
   `h::set_custom_data` then `h::custom_data` returns `Chance` = 5. Do not copy the probe test.
7. Run the checks below in `mods\sf3_chance` and fix until they pass.
8. Record the new mod in `SF3_REGISTRY.md` slice 10M (mod `sf3_chance` under `mods/`, its 5 hooks plus `register`, the cube's ItemPart, block entity
   type `sf3_chance:cube`), as project rule 4 asks. This design does not change the registry.

Acceptance checks (each run by Claude, not taken from the agent's report):

| Command (in `sf3-horizon\mods\sf3_chance` unless noted) | Expected |
|---|---|
| `fc.exe /b ..\..\native\21_sf3_chance\mixins\sf3_chance\runtime.rs src\runtime.rs` | `FC: no differences encountered` |
| `fc.exe /b ..\sf3_host\sf3_host.rs src\sf3_host.rs` | `FC: no differences encountered` |
| `Select-String -Path src\lib.rs -Pattern 'host\.'` | no output |
| `Select-String -Path src\*.rs -Pattern '\r'` | no output (LF only) |
| `cargo check` | finishes, no errors (no warnings expected) |
| `cargo test` | `test result: ok. 30 passed` for the lib (28 runtime + 2 glue), 0 failed |
| `cargo horizon-mod check` | `SF3 Chance Cubes uses N items of the API ... Made for 0a875da.`, plus at most the two known `Block`/`Command` lines |
| `cargo horizon-mod build` | `Built .\target/horizon-mod\sf3_chance.hmod` |
| `cargo horizon-mod check target\horizon-mod\sf3_chance.hmod` | `sf3_chance 0.1.0 (native-mod, format native-1/0a875da.../e59da90..., for 26.3)` |
| list the `.hmod` zip | only `horizon-mod.toml`, `Cargo.toml`, `Cargo.lock`, `src/*.rs`, `uses.json` |
| `horizon-launcher native-build mods\sf3_chance --instance <SF3 test instance> --trust-native-code` | builds (not checked: needs launcher 0.2.92) |

Then the play-test (plan step 1.4, Claude), from `SF3_REGISTRY.md` slice 10M steps 1-4 and the PLAYTEST_LOG entries:
survival break gives a chat line `[Chance Cubes] <name> (chance N)` and the reward; Scanner right click shows the chance
and a later break picks near it; a tier 3 pendant raises the chance by 50 and loses one use per cube; the Silk Touch
Pendant in hand drops the cube with no reward, and a scanned cube placed again keeps its chance;
`/give @s chancecubes:chance_cube[custom_data={Chance:-80}]`, place, break gives a reward from that window; one reward
of each step kind (Entity: anvil/TNT; Mob; Block; Command; RottenFood) works away from spawn and in the Nether.
