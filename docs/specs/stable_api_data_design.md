# How our mods hold and expose data on the stable mod API (design, 2026-11-20)

Read-only design research. Nothing was built or migrated. Engine: `horizon/` on upstream main.
Paths below are relative to `D:\ClaudeProjects\horizon-workspace\`. "Not checked" means I did not
find the name in source and the snippet may need fixing.

Companion files: `sf3-horizon/docs/specs/stable_api_fit_2026-11-20.md` (name-level survey) and
`sf3-horizon/docs/specs/migration_stable_api_plan.md` (the migration plan).

## The short version

- The stable API keeps the model our glue already uses. A mod block entity is still a
  `ModBlockEntity` with `nbt` (saved compound), `items` (slots) and `data` (menu data slots), and the
  game still saves it, ticks it and answers hoppers/pipes for it. What changes is the entry point:
  we register a `BlockEntityPart` instead of injecting into `native_block_entity*`.
- Storage for automation is declared once at registration: `r.block_container`, `r.block_fluids`,
  `r.block_energy` take the same `ModContainer` / `ModFluidTanks` / `ModEnergyBuffer` structs our
  `block_entity_container` / `_fluids` / `_energy` injections fill today. The amounts live in the
  entity's `nbt` under `energy` and `fluids`, as today.
- Other blocks are reached through Capabilities: `level.capability(host, &ENERGY | &ITEMS | &FLUIDS, pos, side)`,
  inside `host.transaction(...)`.
- Per-player and per-entity data moves to `AttachmentType` (with codec, `copy_on_death`, `sync`).
- Per-item data uses item components (`ItemStack::get/set`, `ItemComponentEnergy`).
- `FakeHost` can test storage moves and attachments, but not time, weather, light or redstone.

## 1. Machine saved data (today: `native_with_mod_block_entity` / `native_mod_block_entity`)

**Stable mechanism.**

- Declare the type and attach the Part in `Hooks::register`:
  `r.block_entity_type("controller").blocks(&[...]).build()` then `r.block_entity_part(&kind, Part)`.
  The type id is qualified with our namespace. Source: `horizon/docs/modding/src/concepts/parts/block-entity-types.md`,
  `horizon/crates/horizon-mod-vocab/src/parts/block_entities.rs` (`block_entity_type`, `block_entity_part`).
- `BlockEntityPart` extends `BlockPart`; both impls need `#[mod_api::horizon_part]`.
  Source: `horizon/docs/modding/src/concepts/parts.md`.
- Initial data: `fn block_entity(&self, _: LevelSide<'_>, _: &mut BlockEntityEvent<'_>) -> Option<Compound>`.
  Source: `horizon/crates/horizon-client/src/game/native_hooks/block_entity_on_load_routes_tests.rs:24`.
- Ticking: `fn block_entity_ticks(&self, _: &dyn Host, event: &mut BlockEntityTicksEvent<'_>) { event.ticks = true; }`
  and `fn block_entity_tick(&self, host: &mut dyn ServerHost, event: &mut BlockEntityTickEvent<'_>)`.
  The event carries `event.pos` and `event.entity` (a `ModBlockEntity`: `nbt`, `items`, `data`).
  Source: `horizon/crates/horizon-mod-api/src/parts/block_entities.rs:193-260` (test Parts `Press`, `Hoard`),
  hook text `horizon/crates/horizon-mod-vocab/src/hooks/block_entity_tick.rs`,
  fields `horizon/crates/horizon-mod-vocab/src/item/containers.rs:29` (`ModBlockEntityFields`).
  During its own tick the entity is out of the world; `*event.reply = BlockEntityTickReply::Unchanged`
  skips the write-back when nothing changed (same hook file).
- Saving: the game saves `event.entity.nbt` with the chunk. Nothing to do.
- Reading another block entity (our `claimed()` reads other controllers): `host.block_entity(level, pos)`
  gives a `BlockEntityRef`; `block_entity_data` reads its saved compound.
  Writing one outside its tick: `merge_data` / `replace_data` (transactional, syncs to clients).
  Source: `horizon/crates/horizon-mod-vocab/src/host/block_entities.rs` (methods `block_entity`,
  `block_entity_data`, `block_entity_merge_data`, `block_entity_replace_data`).
  The handle method names (`entity.data(host)`, `entity.replace_data(host, ..)`) are by pattern;
  `replace_data(host, data)` is named in `block-entity-types.md`, `data(host)` is not checked.
- Typed alternative: `BlockEntityPartState` stores one typed value per entity in its attachment map,
  saved with the chunk. It is server-only (never synced) and is read with
  `host.block_entity_identity(..)` during the tick. Source: `horizon/crates/horizon-mod-vocab/src/block/part_state.rs:40`.
- Sync to the client:
  - `block_entity_update_tag` hook: we set `tag` to what clients see; their copy merges it into `nbt`.
    Source: `horizon/crates/horizon-mod-vocab/src/hooks/block_entity_update_tag.rs`.
  - `host.block_entity_sync(pos)` resends it when the look changes (not every tick).
    Source: `horizon/crates/horizon-mod-vocab/src/host/block_entities.rs` (`BlockEntitiesServerHost`).
  - Progress bars use menu data slots (`event.entity.data`), which the menu sends on its own.
- Load notice: `block_entity_on_load`. Source: `horizon/docs/modding/src/concepts/attachments/block-entity-attachment.md`.

**Design decision.** Keep our state in `event.entity.nbt`, as today, not in `BlockEntityPartState`:
the game's default energy and fluid handlers read `nbt.energy` / `nbt.fluids`
(`horizon/crates/horizon-mod-vocab/src/item/containers.rs:214-245` doc comments), clients get it through
the update tag, and our `geti`/`put` helpers and `runtime.rs` stay as they are. The glue rewrite is mostly
mechanical: `entity: &mut ModBlockEntity` becomes `event.entity`, `game.native_*` reads become `level.*(host, ..)`.

**Today.** Injections `block_entity`, `block_entity_ticks`, `block_entity_tick` in each `horizon-mixin.toml`;
464 calls to `native_with_mod_block_entity` / `native_mod_block_entity` (survey).

## 2. Items, fluids, energy and automation: Capabilities

**Stable mechanism.**

- Declare default storage per block (mod blocks only):
  `r.block_container(&block, ModContainer)`, `r.block_fluids(&block, ModFluidTanks)`,
  `r.block_energy(&block, ModEnergyBuffer)`. `block` is a `BlockKey` from `r.block_key("ns:id")`.
  Source: `horizon/crates/horizon-mod-vocab/src/parts/default_capabilities.rs:32-41`,
  `horizon/docs/modding/src/concepts/capabilities.md`.
- `ModContainer { slots, faces: [Vec<usize>; 6], inputs, outputs, menu }` gives sided slots and which
  slots take input / give output. `ModEnergyBuffer { capacity, max_insert, max_extract, insert_faces, extract_faces }`.
  `ModFluidTanks { tanks, faces, inputs, outputs }`. All in
  `horizon/crates/horizon-mod-vocab/src/item/containers.rs:209-254`.
  These are field-for-field the structs our glue fills today.
- Custom handlers instead: `r.block_entity_capability(&ITEMS, &kind, |host, side| Some(Box::new(..)))`;
  `_before_game` to win over the game's provider. Source: `horizon/crates/horizon-mod-vocab/src/parts/block_entities.rs:176-210`.
- Keys: `ITEMS` (`item/capability.rs:96`), `FLUIDS` (`block/fluid_capability.rs:236`),
  `ENERGY` and `ITEM_ENERGY` (`item/energy_capability.rs:27,42`), all under `horizon/crates/horizon-mod-vocab/src/`.
- Pulling from another block (any mod's): `level.capability(host, &ENERGY, pos, Some(side))` returns
  `Option<Capability<dyn EnergyHandler>>`; move with `move_energy(host, &from, &to, max, tx)` or
  `move_resources(host, &from, &to, filter, max, tx)` inside `host.transaction(|host, tx| ...)`.
  No `simulate` flag: abort the transaction instead.
  Source: `horizon/crates/horizon-mod-vocab/src/item/capability.rs:175-200`, `item/energy_capability.rs:72`,
  `content/resource.rs:590`, `item/transaction.rs:146` (`HostTransaction::transaction`).
- Hoppers use the same capability path for mod blocks (rules in `capabilities.md`, "Hopper and dropper attempts").

**Design.** One machine = one `block_container` + `block_fluids` + `block_energy` declaration per block id,
built from the same `runtime.rs` tables we use now. Our "push out" loops (`push_out`) become
capability lookups on the six neighbours. Our own cables/pipes (bundle 04, 15) register providers for their
types and move with `move_energy` / `move_resources`.

**Today.** Injections `block_entity_container`, `block_entity_fluids`, `block_entity_energy`,
`block_entity_accepts_fluid`, `container_accepts`; calls `native_energy`, `native_energy_insert`, `native_insert_item`.

## 3. Menus and screens

**Stable mechanism.**

- Block menu: `ModContainer.menu` names the menu opened when the block is used (doc comment, `containers.rs:200-205`).
- Layout: `screen` hook fills a `Screen { width, height, slots, inventory_y, inventory_x, own_labels, own_background,
  recipe_book, recipe_book_toggle }`, keyed by block, asked on both sides.
  Source: `horizon/crates/horizon-mod-vocab/src/hooks/screen.rs`, struct `horizon/crates/horizon-mod-vocab/src/client/types.rs:842`.
  This is the same shape as our `NativeScreen` today.
- Progress bars: data slots `event.entity.data` on the server; `screen_draw` (client) draws from `data`.
  Drawing calls exist on `DrawContext`: `fill`, `fill_gradient`, `sprite`, `text`, `item_stack`, `fluid`,
  `gui_tooltip`, `push_clip`. Source: `horizon/crates/horizon-mod-vocab/src/hooks/screen_draw.rs`,
  `horizon/crates/horizon-mod-vocab/src/host/draw.rs`.
- Buttons and tooltips on our screens: `screen_click` (client) → `menu_button` (server, on the block entity),
  `screen_tooltip`. Source: `hooks/screen_click.rs`, `hooks/menu_button.rs`, `hooks/screen_tooltip.rs`.
- `MenuPart` (attach with `r.menu_part("ns:menu", Part)`, `horizon/crates/horizon-mod-vocab/src/parts/menus.rs:35`)
  covers slot rules (`menu_slot_rules`), keep-open range (`menu_still_valid`), quick-move, clicks, close.
  Source: `horizon/docs/modding/src/concepts/capabilities/menu-slots.md`, hooks `menu_*` in `hooks/`.
- Player accessory menu (`/baubles`): `player_open_mod_menu(player, menu, title, extra, pos, replace)` opens a mod
  menu with no block; `player_back_mod_menu_slots(.., places)` backs its slots with any `ItemPlace`, including
  `ItemPlace::Mod` served by our own `PlaceProvider` (`r.place_provider`, "as an accessory mod exposes its slots").
  Source: `horizon/crates/horizon-mod-vocab/src/host/players.rs:732,758`, `horizon/crates/horizon-mod-vocab/src/block/item_place.rs:282`,
  `horizon/crates/horizon-mod-vocab/src/parts/items.rs:201`.
- List screens (recipe viewer, bundle 07_sf3_jei): no "mod screen" type, but overlay routes exist:
  `screen_render_post` (draw over any open screen), `screen_room` (reserve a panel right of the window),
  `screen_mouse_*_pre`, `screen_key_pressed_pre`, `screen_char_typed_pre`, `render_tooltip_pre`, `item_tooltip`,
  and `recipes_received` + recipe helpers for the client's recipe list. Source: those files in
  `horizon/crates/horizon-mod-vocab/src/hooks/`; `host/recipes.rs:53` (`known_recipes`).

**Gaps.** The Mods options panel (`draw_mod_browser`) and the options screen (`draw_options`) that JEI patches
have no hook seen. Whether `screen_render_post` + the `_pre` input hooks can fully replace our raw patches of
`draw_inventory`, `draw_creative` and `tooltip_box` is not checked in depth.

**Today.** Injections `screen`, `menu_input_closed`, plus 10 raw patches of draw/tooltip functions (survey).

## 4. Per-player and per-entity data: Attachments

**Stable mechanism.**

- `static X: AttachmentType<T> = AttachmentType { namespace, name, default, codec, copy_on_death, sync };`
  then `X.get / set / has / get_existing / remove (host, Holder::Player(uuid) | Holder::Entity(id) | ...)`.
  Source: `horizon/docs/modding/src/concepts/attachments.md`; type in `horizon/crates/horizon-mod-runtime/src/attachments.rs:364`.
- Saving needs `codec: Some(AttachmentCodec { encode, decode })`; without it the value lasts the session.
- Death and respawn: `copy_on_death: true` (needs codec) copies on player respawn; mob conversions copy every
  codec entry. `player_clone` gives `event.original.attachment(host, &X)` for anything else.
- Sync: `sync: true` (needs codec) sends to tracking players at end of tick; `X.sync_data(host, holder)` on demand
  (`attachments.rs:495`). No partial updates or recipient filter.
- Typed per-entity Part state: `EntityPartState` (`horizon/crates/horizon-mod-vocab/src/entity/part_state.rs:51`).
- Level-wide data (our skyblock island registry etc.): `Holder::Level`, saved to `data/horizon/attachments.dat`.

**Design.** One `AttachmentType` per concern (e.g. accessories, blood-magic soul network, tinkers player
state), each with a codec. Accessory slots: `copy_on_death: false` (they drop), `sync: true` (the client draws them).

**Today.** `native_player_persistent_data` / `native_set_player_persistent_data` (25 call sites in glue),
`native_entity_nbt` / `native_merge_entity_nbt` for entity data.

## 5. Per-item data: item components

**Stable mechanism.**

- `ItemStack::get(&component)` / `set(&component, value)` / `remove`, with a `Component` descriptor
  (`id`, `decode`, `encode`). Source: `horizon/crates/horizon-mod-vocab/src/item/item_stack.rs:9,263,277,299`.
- Component ids: `ComponentId::new("mymod:charge")` (`horizon/crates/horizon-mod-vocab/src/content/resource.rs:16`).
- Item energy: `r.item_capability(&ITEM_ENERGY, "ns:item", |host, place| Some(Box::new(ItemComponentEnergy::new(place, id, cap, max_in, max_out))))`.
  Stored as an int component; absent reads 0. Source: `horizon/crates/horizon-mod-vocab/src/item/item_component_handlers.rs:55-80`,
  `horizon/docs/modding/src/concepts/capabilities/block-energy.md`.
- Item fluids: `ItemComponentFluidTank` under `ITEM_FLUIDS` (same doc).
- Writes go through `ItemPlace::exchange` in a transaction (`concepts/capabilities/item-places-and-components.md`).
- Tooltip lines for a component: registrar method at `horizon/crates/horizon-mod-vocab/src/parts/items.rs:205` (name not read).

**Gap.** I found no registrar call that declares a new component type. Whether an undeclared `sf3:energy`
component is kept, saved and synced is not checked. Fallback: `minecraft:custom_data` (works for tool modifiers,
not for `ItemComponentEnergy`, which wants an int component).

**Today.** `native_item_energy*` (about 440 calls), `native_component` / `native_set_component` (76).

## 6. Testing with `FakeHost`

**Can simulate** (`horizon/crates/horizon-mod-vocab/src/testing.rs:192`, `testing/level.rs`, `concepts/testing.md`):
blocks (`host.level.set_block`), block entities with items, tanks and energy (`FakeBattery`), the game's
capability lookup over them, transactions with rollback (`journal`), players and inventories, commands,
messages, sounds, game events, attachments (`host.attachments`), entities.

**Cannot simulate** (no fake answers; "an unsupported host method panics with its name"): day time, rain/thunder,
light and sky access, redstone signals, `block_entity_identity` / `block_entity_data` (so `BlockEntityPartState`
and reading other entities' data), client drawing (no client backend). Methods `FakeHost` implements in the level
area: `level`, `level_block`, `level_block_state`, `level_in_place`, fluids, sounds, game events, `energy_*`,
`block_entity`, `block_entity_kind` (grep of `testing.rs`).

**Design.** Keep rules in `runtime.rs` with plain unit tests (as now). Put each host-touching step (push energy,
eject items) in a small function that takes `&mut dyn ServerHost` and test that with `FakeHost`. Full ticks
need a hand-written host double (`testing::FakeJournal`) or the in-game tests we run today.

## Worked example: the Solar Array controller (bundle 12_sf3_envtech)

Today (`sf3-horizon/native/12_sf3_envtech/mixins/sf3_envtech/glue.rs`): one block entity `sf3_envtech:controller`
for every controller block. Each tick: `age += 1`; rescan the structure every 20/40 ticks (`refresh`); every 20
ticks count sky-lit cells; with no redstone signal add `solar::generate(..)` to `nbt.energy` up to `mach.buffer()`;
then `push_out` into neighbours on every face but the top. `block_entity_energy` declares an extract-only buffer.
No menu (only the miners have one). The rules (`Machine::from_block`, `buffer`, `solar::generate`, `layout`) are in
`runtime.rs` and stay unchanged.

### Registration

```rust
use mod_api::{Hooks, Registrar, RegistrationContext, ModEnergyBuffer};

#[derive(Default)]
struct EnvTech;
struct Controller;

const SOLAR: [&str; 4] = [
    "environmentaltech:controller_solar_1", "environmentaltech:controller_solar_2",
    "environmentaltech:controller_solar_3", "environmentaltech:controller_solar_4",
];

#[mod_api::horizon_mod]
impl Hooks for EnvTech {
    fn register(&self, r: &mut dyn Registrar, _: &RegistrationContext) {
        // Type id becomes `sf3_envtech:controller` (m::ENTITY). Our blocks are in the
        // `environmentaltech` namespace: the manifest must list it under `namespaces`.
        let controller = r.block_entity_type("controller").blocks(&SOLAR).build();
        r.block_entity_part(&controller, Controller).expect("native block entity type");
        for id in SOLAR {
            let mach = m::Machine::from_block(id).unwrap();
            let block = r.block_key(id);
            // Same literal as glue.rs block_entity_energy: extract only, not through the top.
            r.block_energy(&block, ModEnergyBuffer {
                capacity: mach.buffer(), max_insert: 0, max_extract: mach.buffer(),
                insert_faces: [false; 6], extract_faces: [true, false, true, true, true, true],
            });
        }
    }
}
```

Sources: `concepts/parts.md`, `concepts/parts/block-entity-types.md`, `parts/default_capabilities.rs:40`.
Not checked: whether `block_energy` is reachable on `dyn Registrar` without importing `DefaultCapabilitiesRegistrar`.

### State, initial data, tick

```rust
use mod_api::{BlockPart, BlockEntityPart, Compound, Host, LevelSide, ServerHost,
              BlockEntityEvent, BlockEntityTicksEvent, BlockEntityTickEvent};

#[mod_api::horizon_part]
impl BlockPart for Controller {}

#[mod_api::horizon_part]
impl BlockEntityPart for Controller {
    fn block_entity(&self, _: LevelSide<'_>, _: &mut BlockEntityEvent<'_>) -> Option<Compound> {
        let mut nbt = Compound::new(); // not checked: constructor name
        for k in ["energy", "formed", "age", "cells", "piezo"] { put(&mut nbt, k, 0); }
        Some(nbt)
    }
    fn block_entity_ticks(&self, _: &dyn Host, event: &mut BlockEntityTicksEvent<'_>) {
        event.ticks = true;
    }
    fn block_entity_tick(&self, host: &mut dyn ServerHost, event: &mut BlockEntityTickEvent<'_>) {
        let level = host.level(host.dimension()).unwrap();
        let pos = event.pos;
        let entity = &mut *event.entity;
        // Block id as text for runtime.rs: not checked (BlockKey -> id).
        let Some(mach) = block_id(host, level, pos).and_then(|b| m::Machine::from_block(&b)) else { return };
        let age = (geti(&entity.nbt, "age") + 1) % 1_000_000;
        put(&mut entity.nbt, "age", age);
        // refresh(..) and sky_cells(..) as today, with level.block(host, p) and
        // level.can_see_sky(host, p) in place of native_block / native_light.
        if geti(&entity.nbt, "formed") != 0 && !level.has_neighbor_signal(host, pos) {
            let rain = if level.is_raining(host) == Some(true) { 1.0 } else { 0.0 };
            let thunder = if level.is_thundering(host) == Some(true) { 1.0 } else { 0.0 };
            let day = level.day_time(host).unwrap_or(0);
            let gen = solar::generate(mach.tier, geti(&entity.nbt, "cells"), day, rain, thunder,
                                      geti(&entity.nbt, "piezo"));
            let stored = geti(&entity.nbt, "energy");
            put(&mut entity.nbt, "energy", stored.saturating_add(gen).min(mach.buffer()));
        }
        push_out(host, level, pos, entity, [true, false, true, true, true, true]);
    }
}
```

`level.day_time(host)` is used in the docs (`concepts/` grep). `has_neighbor_signal`, `is_raining`,
`is_thundering`, `can_see_sky` are host methods in `horizon/crates/horizon-mod-vocab/src/host/levels.rs`
(`level_has_neighbor_signal`, `level_is_raining`, ...); the `level.x(host)` handle form is by pattern, not checked.
Behaviour change: the stable API gives rain/thunder as booleans, our `solar::generate` takes the 0..1 levels.

### Capabilities (energy out)

```rust
use mod_api::{ENERGY, HostTransaction, LevelRef, ModBlockEntity, Direction};

fn push_out(host: &mut dyn ServerHost, level: LevelRef, pos: [i32; 3],
            entity: &mut ModBlockEntity, faces: [bool; 6]) {
    let mut left = geti(&entity.nbt, "energy");
    for side in 0..6 {
        if !faces[side] || left <= 0 { continue; }
        let to = add(pos, SIDES[side]);
        let Some(cap) = level.capability(host, &ENERGY, to, Some(DIRECTIONS[side ^ 1])) else { continue };
        let moved = host.transaction(|host, tx| Ok::<u32, ()>(cap.insert(host, tx, left as u32)));
        left -= moved.unwrap_or(0) as i32;
    }
    put(&mut entity.nbt, "energy", left);
}
```

We take the energy straight from our own `nbt` because the entity is out of the world during its tick; the
neighbour's handler is reached through the capability. Other mods' cables pull from us through the
`block_energy` declaration with no code of ours. Not checked: the `Direction` import path in `mod_api`.

### Menu

The Solar Array has none. For the miners (same type), today's `block_entity_container` and `screen` map 1:1:
`r.block_container(&block, ModContainer { slots: n, faces, inputs: vec![], outputs: all, menu: Some(id.into()) })`
at registration, and the `screen` hook fills `Screen { width: 176.0, height: 166.0, slots, inventory_y: 84.0,
inventory_x: 8.0, own_labels: false, own_background: false, .. }`. Not checked: which Part trait carries `screen`
and its exact signature; `Screen` has two more fields (`recipe_book`, `recipe_book_toggle`), set them to `None`.

### Save, load and sync

Nothing to write: `event.entity.nbt` is saved with the chunk and loaded back; `nbt.energy` is what the game's
`ENERGY` provider reads (`containers.rs:241` doc). If a client view ever needs `formed`, answer
`block_entity_update_tag` with it and call `host.block_entity_sync(pos)` when `formed` flips.

### One FakeHost test

```rust
#[cfg(test)]
mod tests {
    use super::*;
    use mod_api::testing::{FakeHost, FakeBattery};
    use mod_api::{ModBlockEntity, Tag};

    #[test]
    fn a_solar_controller_empties_its_buffer_into_the_battery_below() {
        let mut host = FakeHost::new();
        let level = host.level.level();
        host.level.block_entity([0, 63, 0]).energy = Some(FakeBattery::new(0, 1_000));
        let mut entity = ModBlockEntity::new("sf3_envtech:controller".into(), Default::default());
        entity.nbt.insert("energy".into(), Tag::Int(600));
        push_out(&mut host, level, [0, 64, 0], &mut entity, [true, false, true, true, true, true]);
        assert_eq!(geti(&entity.nbt, "energy"), 0);
        let below = host.level.block_entity_at([0, 63, 0]).unwrap();
        assert_eq!(below.energy.as_ref().unwrap().amount, 600);
    }
}
```

Sources: `concepts/testing.md` (FakeHost, `block_entity`, `block_entity_at`), `testing/level.rs:162,316`
(`energy`, `FakeBattery::new(amount, capacity)`), `item/containers.rs` (`ModBlockEntity::new`), `testing.rs:789`
(fake `energy_insert`). The full tick cannot run on `FakeHost`: `day_time`, weather, signal and sky reads panic.

## Things with no stable route found

1. Mods options panel and options screen drawing (`draw_mod_browser`, `mod_browser_closed`, `draw_options`; bundle 07).
2. Host flight, `sneaking`, `acting_id` (191 calls; from the survey, not rechecked here).
3. Declaring a new item component type (section 5).
4. Rain and thunder as levels (only `is_raining` / `is_thundering` booleans in `host/levels.rs`).
5. Opacity of a block (`void_clear` already works around this today; nothing new seen).
6. A full "mod screen" that is not a menu (recipe viewer list): only overlays on existing screens.
7. Synced typed Part state: `BlockEntityPartState` is server-only (`block/part_state.rs:36`).
8. The official template (`horizon-native-mod-template`) is still a mixins-only example (pinned
   `ba6344a5`); it shows no `Hooks`/Parts mod, no Cargo dependency on `horizon-mod-api`, and no `FakeHost` test.

## Open questions

1. How a native `Hooks` mod is packaged and depends on `horizon-mod-api` (Cargo, manifest `[native]`); the template does not show it.
2. `BlockKey` to id text: does `key.id(host)` exist as on `BlockEntityTypeKey`? Our `runtime.rs` matches on id strings.
3. `ModFluidTanks` is `#[non_exhaustive]` (`containers.rs:217`): how does a mod build one? No constructor found.
4. Which Part trait owns `screen`, `screen_draw`, `screen_click`, `screen_tooltip`, and their signatures.
5. Is the game's `ITEMS`/`ENERGY` provider for our own block usable while that block is out of the world for its tick (e.g. a pipe pulling from us in the same tick)?
6. Does a menu id in `ModContainer.menu` need a content (data) declaration of a mod menu type, or does a block id work as today?
7. Can a mod that owns `sf3_envtech` declare blocks in `environmentaltech:` (manifest `namespaces`) for every bundle that reuses original mod namespaces?
8. `BlockEntityTickEvent` field types (`pos` as `[i32; 3]`, `entity` as `&mut ModBlockEntity`) are inferred from tests, not read from the generated event.
9. `testing::with_mods` takes a `Mods` value: how a mod builds it to dispatch hooks through its own Parts in a test.
