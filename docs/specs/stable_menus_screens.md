# Menus and screens on the stable API (Phase 2.3 design note, 2026-11-20)

Question: how do our menus and screens move from the retired engine patches to Horizon's stable mod API?

Sources read: `migration_stable_api_plan.md`, `api_map.md`, `stable_api_data_design.md`, `pilot_chance_design.md`;
engine docs under `horizon/docs/modding/src`; the SDK at build `0a875da` (the scratch mod's
`.horizon/sdk/api/crates/horizon-mod-vocab/`, shortened below to `vocab/`); our old bundles under `native/`.
Engine source was read at `horizon/` checkout `084ae44e40` (newer than `0a875da`) only where the SDK left a
question open; those claims are marked "(engine)".

Compile check: every skeleton below that says "compiled" is in the scratch mod
`C:\Users\chaxt\.sf3-tools\scratch_menus\src\lib.rs`. `cargo check` and `cargo horizon-mod check` both pass
(the tool reports "302 items of the API ... 17 hooks ... Made for 0a875da"). Nothing was run in game.

## 0. Corrections to earlier notes

1. **`stable_api_data_design.md` §3 is wrong on one point.** `player_back_mod_menu_slots` does not take "any
   `ItemPlace`, including `ItemPlace::Mod`". It takes `MenuSlotPlace`, which has two variants only: `HeldItem`
   and `EntityItems` (`vocab/src/item/menu_slot_place.rs:16-39`). A `PlaceProvider` cannot back menu slots.
2. **`api_map.md` says Options > Mods is gone.** The mod *list* hook (`native_mods`) is gone, but each mod still has a
   page in Options > Mods, filled by `Registrar::register_setting(SettingSpec)` (`vocab/src/parts/settings.rs:21`;
   `horizon/docs/modding/src/how-to/mod-settings.md`, section "Settings"). Our 19 `native_mods` rows only pushed a
   name, version and description (`native/12_sf3_envtech/mixins/sf3_envtech/list.rs`); the manifest gives those now.
3. **"Menus with input slots: no stable route" is too strong.** A blockless menu can be backed by a held item
   (pattern B). Only storage that is neither a held item nor an entity's inventory lacks a direct route (15's
   frequency storage, 19's accessories).
4. **JEI's 10 raw draw patches are not needed.** Stable hooks cover each of them (pattern D table). The brief's
   "8 draw mixins" is 10 `target =` rows in `native/07_sf3_jei/mixins/justenoughitems/horizon-mixin.toml`.
5. **The client action bar is not a feature.** All 17 `native_client_action_bar` calls are a fallback after
   `native_action_bar` failed for the single-player host (comment repeated in each bundle's `say`, e.g.
   `native/12_sf3_envtech/mixins/sf3_envtech/glue.rs:63-66`), plus 4 one-off lines.

## 1. Survey: what we have

Counted from `native/NN_sf3_*/mixins/*/` (hook files by name, calls by grep of `name(`).

| Use | Bundles | Pattern |
|---|---|---|
| `screen` hook (layout) | 12: 03 04 05 06 08 10 11 12 13 15 17 20 | A |
| `screen_draw` (bars, textures) | 4: 04 05 08 15 | A |
| `screen_click` / `menu_button` | 3: 04 05 15 / 3: 04 05 15 | A |
| `screen_tooltip` | 1: 04 | A |
| `menu_slot_rules` (horizon-client-lib free fn + `slots.rs` helper) | 5: 03 04 05 08 11 | A |
| `container_accepts` (per-slot automation veto) | 8: 03 04 05 08 11 13 15 17 | A |
| `menu_links` | 1: 05 | A |
| draw calls: `native_fill` 79, `native_text` 42, `native_text_width` 10, `native_sprite` 9, `native_item` 2 | 04 05 08 15 | A |
| `native_open_menu_with_input` + `menu_input_closed` | 15 Ender Pouch, 17 Bag of Holding | B |
| same | 19 Accessories (`/baubles`) | C |
| `native_open_menu` + `menu_clicked` + `menu_closed` + `native_set_menu_items` | 06 wireless grid | C (same mechanism) |
| 07 JEI: 23 injections, 10 raw targets, 7,421 lines | 07 | D |
| `native_mods` list row | 19: all but 07 | D |
| `native_settings_refresh` (2), JEI `settings` / `settings_click` | 07 | D |
| `native_action_bar` (44 calls) | 15: 01 04 05 06 09 10 11 12 13 14 15 16 17 19 20 | E |
| `native_client_action_bar` (17 calls) | 12: 06 09 10 11 12 13 14 15 16 17 19 20 | E |
| `native_tooltip` (ItemPart) | 8: 04 05 06 10 11 13 14 16 (+ 07's `tooltip` hook) | F |

Bundles 16 (utility) has no machine screen; 12 (envtech) has only `screen`. The brief's pattern A list (04 08 11 12
16 17) is corrected to the 12 `screen` bundles above.

## A. Machine menu (block-entity slots, bars, buttons)

**Verdict: full stable route, same shape as today.**

| Old | Stable | Source |
|---|---|---|
| `screen` | `BlockEntityPart::screen(&self, &dyn Host, &mut ScreenEvent) -> Option<Screen>` | `vocab/src/hooks/screen.rs`; struct `vocab/src/client/types.rs:842` |
| `screen_draw` | `BlockEntityPart::screen_draw`, event has `data: &[i32]`, `draw: &mut dyn DrawContext`, `origin` | `vocab/src/hooks/screen_draw.rs`; draw methods `vocab/src/host/draw.rs:39-206` |
| `screen_click` -> `menu_button` | `screen_click` returns `Option<i32>`; `menu_button(&mut dyn ServerHost, &mut MenuButtonEvent)` | `vocab/src/hooks/screen_click.rs`, `menu_button.rs` |
| `screen_tooltip` | `BlockEntityPart::screen_tooltip`, push `String` lines | `vocab/src/hooks/screen_tooltip.rs` |
| `menu_slot_rules` | `MenuPart::menu_slot_rules`, attached by `r.menu_part("ns:menu", Part)`; gets `context` (player, pos, menu slots) | `vocab/src/parts/menus.rs:35`; `horizon/docs/modding/src/concepts/capabilities/menu-slots.md` |
| `container_accepts` | `ITEMS` capability handler (`is_valid` / `insert`) | `api_map.md` row `native_container_accepts` |
| `menu_links` | `menu_links` hook, same shape | `vocab/src/hooks/menu_links.rs` |
| progress bars | `entity.set_data_slots` / `set_data_slot` on the server; `data` in `screen_draw` | `horizon/docs/modding/src/how-to/world/machine-menu-data.md` |
| shift-click routing | `menu_quick_move` | `vocab/src/hooks/menu_quick_move.rs` |
| JEI "+" into a machine | `MenuPart::menu_transfer` | `menu-slots.md`, section "Recipe transfer into a mod menu" |

The old `slots.rs` workaround ("horizon-client-lib cannot reach the game") goes away: `menu_slot_rules` is now a
Part method with a read-only `Host`.

Skeleton (compiled):

```rust
struct Machine;
#[mod_api::horizon_part] impl BlockPart for Machine {}
#[mod_api::horizon_part]
impl BlockEntityPart for Machine {
    fn screen(&self, _: &dyn Host, _: &mut ScreenEvent<'_>) -> Option<Screen> {
        Some(Screen { width: 176.0, height: 166.0,
            slots: vec![Some([56.0, 17.0]), Some([56.0, 53.0]), Some([116.0, 35.0])],
            inventory_y: 84.0, inventory_x: 8.0, ..Default::default() })
    }
    fn screen_draw(&self, _: &dyn ClientHost, e: &mut ScreenDrawEvent<'_>) {
        let [x, y] = e.origin;
        let progress = e.data.first().copied().unwrap_or(0) as f32;
        e.draw.fill([x + 79.0, y + 34.0, progress, 16.0], 0xFF_FF_FF_FF);
    }
    fn screen_click(&self, _: &dyn ClientHost, e: &mut ScreenClickEvent<'_>) -> Option<i32> {
        let [x, y] = e.at;
        ((150.0..166.0).contains(&x) && (5.0..21.0).contains(&y)).then_some(0)
    }
    fn screen_tooltip(&self, _: &dyn ClientHost, e: &mut ScreenTooltipEvent<'_>) { /* push lines */ }
    fn menu_button(&self, _: &mut dyn ServerHost, e: &mut MenuButtonEvent<'_>) { /* e.context, e.entity, e.carried */ }
}
struct MachineSlots;
#[mod_api::horizon_part]
impl MenuPart for MachineSlots {
    fn menu_slot_rules(&self, _: &dyn Host, e: &mut MenuSlotRulesEvent<'_>) {
        if e.slot == 2 { e.may_place = false; }
    }
}
// register: let kind = r.block_entity_type_key("ns:machine"); r.block_entity_part(&kind, Machine)?;
//           r.menu_part("ns:machine", MachineSlots);
```

Shape changes to absorb in `sf3_host` or per bundle: draw calls move from free functions with `batch` to
`DrawContext` methods (`fill`, `text`, `sprite` gains `tint: Option<u32>`, `item` takes `ItemKey`; `api_map.md`
rows `native_fill`, `native_text`, `native_sprite`, `native_item`); text colour is `0xAARRGGBB`, so an old `rgb`
value without alpha draws nothing (`vocab/src/hooks/notes.rs:2750-2760`, "draws nothing for a fully transparent one").

Not possible: nothing found. Gaps belong to the machine data side (`api_map.md`), not to menus.

## B. Blockless menu backed by a held item (15 Ender Pouch, 17 Bag of Holding)

**Verdict: stable route for 17; 15 needs a stand-in.**

Mechanism: `host.open_menu(uuid, rows, title, items, replace)` opens a vanilla chest menu
(`vocab/src/host/menus.rs:20`), then `player.back_mod_menu_slots(host, window, places)` with
`MenuSlotPlace::HeldItem { hand, slot }` makes each slot read and write the held stack's `ITEM_ITEMS` handler
(`vocab/src/host/players.rs:742-762`, `vocab/src/item/menu_slot_place.rs`). Clicks and shift-clicks then go through
that handler, journalled; the menu closes when the bag leaves the hand; the bag's own hotbar slot is locked
(`menu-slots.md`, "Slots backed by a held item or an entity's handler"). The bag gets its handler from
`r.item_container(&item, |_: &dyn Host| Some(27))`, which makes the game serve its `minecraft:container`
component (`vocab/src/parts/default_capabilities.rs:22`; `concepts/capabilities/item-places-and-components.md`).
Nothing goes back on close: the slots *are* the storage, so `menu_input_closed` has no job left.

Why a chest menu and not `player_open_mod_menu`: (engine) a mod menu type gets a screen only through the `screen`
hook of the block at the target position, or a screen registered with `menu_recipe_book`; with no block the client
closes the window again (`horizon/crates/horizon-client/src/game/native_hooks/shared/book_screen/open.rs:32-72`,
`.../network/remote/mod.rs:9576-9590`). The engine's own test backs a chest menu opened with `open_menu`
(`.../modding/native_menu_places.rs:518-538`). So: chest menu (rows 1-6) is the route; 17's `BAG_ROWS` and 15's
6 rows fit.

Skeleton (compiled):

```rust
fn open_bag(host: &mut dyn ServerHost, player: PlayerRef) -> bool {
    let Ok(Some(window)) = host.open_menu(player.uuid(), 3, Text::literal("Bag".to_string()),
        Vec::new(), MenuReplace::CloseFirst) else { return false };
    let places = (0..27).map(|slot| MenuSlotPlace::HeldItem { hand: Hand::Main, slot }).collect();
    player.back_mod_menu_slots(host, window, places).is_ok()
}
// register: let bag = r.item_key("ns:bag"); r.item_container(&bag, |_: &dyn Host| Some(27));
```

17 Bag of Holding: contents move from our own NBT to `minecraft:container`. Old worlds do not carry over (user
answer 1, `migration_stable_api_plan.md`), so no conversion. The old "empty the bag while open, deposit on close"
code (`native/17_sf3_xutils/mixins/sf3_xutils/glue.rs:1777-1790`) is deleted.

15 Ender Pouch: contents live in mod state keyed by frequency, not in the pouch
(`native/15_sf3_logistics/mixins/sf3_logistics/glue.rs:611-620`). A custom `ITEM_ITEMS` provider over that state
would compile (`r.item_capability`, `vocab/src/parts/items.rs:110`), but the transaction journal covers only game
storages (table in `horizon/docs/modding/src/concepts/transactions.md`), so an aborted click could not undo our
write: dupe risk. Least-bad: treat it as pattern C (mod-driven chest menu, the frequency store written after each
click), or store the pouch's view in the item and sync it to the frequency store on close. Upstream request in C
covers it.

Not checked: whether `back_mod_menu_slots` works for the single-player host's own player. (engine) Its
implementation looks the player up through LAN guest records (`native_menu_places.rs:69-110`). `player.tell`, which
goes through a similar lookup (`native_server.rs:1279-1290`), worked for the host in the pilot, which is the only
evidence.

## C. Player accessory menu (19 `/baubles`), also 06's wireless grid

**Verdict: no direct route; degraded stand-in on stable calls; upstream request.**

`MenuSlotPlace` has no variant for mod-kept storage, and `EntityItems` with the player would reach the game's own
player inventory provider first (`concepts/capabilities/entity-items.md`, "Custom providers": first handler wins).
`ItemPlace::Mod` + `PlaceProvider` exists for "an accessory slot" (`vocab/src/block/item_place.rs:102-109,282`) but
only for item moves, not for menu slots.

Stand-in (all stable, 06 already works this way): `host.open_menu` chest menu showing the worn items;
`menu_clicked` gets `uuid, window, slot, button, mode` for clicks "which moved nothing" (`vocab/src/hooks/menu_clicked.rs`);
the mod moves the stack itself between `menu.cursor()` and `ItemPlace::MenuSlot { menu, slot }` in a transaction,
writes the worn list to a player Attachment, and refreshes with `host.menu_set_items` (`vocab/src/host/menus.rs:54`).
`menu_closed` carries only `uuid, window` (generated `MenuClosedEvent`), so state must already be saved per click.
Drags, number-key swaps and double-click collect are the mod's to refuse or handle (`menu-slots.md`).

Skeleton (compiled):

```rust
fn open_accessories(host: &mut dyn ServerHost, uuid: u128, worn: Vec<Option<ItemStack>>) -> Option<i32> {
    host.open_menu(uuid, 1, Text::literal("Accessories".to_string()), worn, MenuReplace::CloseFirst).ok().flatten()
}
fn menu_clicked(&self, host: &mut dyn ServerHost, e: &mut MenuClickedEvent) {
    if let Some(menu) = host.menu(e.uuid, e.window) {
        let slot = mod_api::ItemPlace::MenuSlot { menu, slot: e.slot.max(0) as usize };
        let _ = (slot, menu.cursor()); // transaction: cursor <-> slot, then save to the attachment
    }
}
```

Not compiled: the transaction body and the Attachment write (Attachments are in `stable_api_data_design.md` §4).

Upstream request (draft):

> **Back a blockless menu's slots with a mod's `PlaceProvider`.** `player_back_mod_menu_slots` takes
> `MenuSlotPlace::HeldItem` and `EntityItems` (`menu_slot_place.rs`). Accessory and ender-storage mods keep stacks
> in player attachments or world state, already exposed as `ItemPlace::Mod { provider, key }`, but cannot show
> them in a menu with vanilla click handling; today they reimplement pickup, shift-click and drag in
> `menu_clicked`. Proposal: `MenuSlotPlace::Mod { provider: &'static str, key: u64 }`, routed through the
> provider's `stack` / `insert` / `extract`, closing the menu when `stack` stops resolving. For rollback, either
> journal Attachments written inside the provider (the journal already records player persistent data and block
> entity attachments, `concepts/transactions.md`) or document that the provider must write only on commit. This is
> NeoForge's `ResourceHandlerSlot` over a mod handler, as Curios and ender-pouch mods use it.

`[[native.mixin]]` alternative: none worth it; the old target `native_menu_input_closed` is gone (`api_map.md`).

## D. List and browser screens (07 JEI, Options > Mods)

**Verdict: stable route for every screen piece; recipe data side not checked.**

| JEI piece (old) | Stable | Source |
|---|---|---|
| item list beside containers (`draw_mod_browser`, `mod_browser_closed`) | `ClientHost::panel_items(mod_id, Vec<Stack>)` + `panel_style(mod_id, PanelStyle::Classic{..})` ("JEI's list on Minecraft 1.12"); clicks, search, keys in `panel_event`; close in `screen_closing` | `vocab/src/host/recipes.rs:62-88`, `vocab/src/client/types.rs:884-945`, `vocab/src/hooks/panel_event.rs`, `screen_closing.rs` |
| recipe screen | `ClientHost::mod_screen_open(mod_id)`, draw in `screen_render_post` when `screen.id == "mod"` and `mod_screen() == Some(id)`; input from `screen_*_pre` | `vocab/src/host/screens.rs` (`mod_screen_open`, `mod_screen`, `mod_screen_close`) |
| tooltips over overlays (`draw_inventory`, `draw_creative`, `tooltip_box`, `tooltip_text`, 2x `draw_stack_tooltip_with`) | draw overlays in `screen_render_foreground` ("Tooltips, the dragged stack ... draw over this hook") | `vocab/src/hooks/screen_render_stages.rs` |
| hide game tooltips under the recipe screen (`native_tooltip_render_pre`) | `render_tooltip_pre` cancel | `vocab/src/hooks/notes.rs:1739`, `api_map.md` row |
| cover over Options (`draw_options`) | `screen_render_pre` returning `Flow::Cancel` when `screen.id == "options"`, then `screen_render_post` | `screen_render_stages.rs`; ids in `vocab/src/client/types.rs:748` |
| room beside the window | `screen_room`, `screen_exclusion()`, `screen_exclusion_areas` | `vocab/src/hooks/screen_room.rs`, `vocab/src/host/screens.rs` |
| hovered item for look-ups | `screen_hovered_item()`, `menu.slot_boxes(host)` | `vocab/src/host/screens.rs`, `vocab/src/host/menus.rs` |
| "+" transfer | `transfer_recipe_id`, `transfer_recipe_check`, `MenuPart::menu_transfer` | `vocab/src/host/recipes.rs` |
| buttons, text fields | `DrawContext::widget_button`, `widget_text_field` | `vocab/src/host/draw.rs:191,206` |
| JEI config page (`settings`, `settings_click`, `native_settings_refresh`) | `register_setting` page in Options > Mods; or JEI's own screen via `mod_screen_open` | `how-to/mod-settings.md` |
| 19 `native_mods` rows | drop: manifest `[mod]` | `api_map.md` row `native_mods` |
| `frame` hook | `render_frame_pre` | `vocab/src/hooks/render_frame_pre.rs` |

Skeleton (compiled): `screen_render_post`, `screen_render_foreground`, `screen_render_pre` (cancel on Options),
`screen_room`, `panel_event` (opening the mod screen), and `show_list` calling `panel_style` + `panel_items`.

```rust
fn screen_render_post(&self, host: &dyn ClientHost, e: &mut ScreenRenderPostEvent<'_>) {
    if e.screen.id == "mod" && host.mod_screen() == Some(MOD_ID) {
        let [x, y, w, h] = e.screen.rect;
        e.draw.fill([x, y, w, h], 0xC0_00_00_00);
        e.draw.text("Recipes", [x + 4.0, y + 4.0], 0xFF_FF_FF_FF, true);
    }
}
fn screen_render_pre(&self, _: &dyn ClientHost, e: &mut ScreenRenderPreEvent<'_>) -> Flow {
    if e.screen.id == "options" { Flow::Cancel } else { Flow::Continue }
}
pub fn show_list(host: &mut dyn ClientHost, items: Vec<mod_api::Stack>) {
    host.panel_style(MOD_ID, PanelStyle::Classic { centred_search: false, window_width: 0 });
    host.panel_items(MOD_ID, items);
}
```

Limits: `panel_items` takes at most 8192 items and only one mod's panel shows at a time (`host/recipes.rs:62-68`).
There is no recipe-page API on the host (`native_panel_recipes` is named only in a doc comment,
`vocab/src/client/types.rs:937`), so recipe pages stay our own drawing. `mod_screen_open` gamepads can close but not
click (`host/screens.rs`).

`[[native.mixin]]` fallback, if a stable hook turns out not to be enough in play: all old targets still exist on
`horizon/` `084ae44e40`: `interface/inventory_slots.rs:422`, `interface/creative_screen.rs:108`,
`interface/options.rs:181`, `modding/native_panel.rs:641` (now returns `Option<BrowserTooltip>`) and `:881`,
`blocks/stations/tooltip.rs:87`, `blocks/stations.rs:2154` and `:2209`; the tooltip hook is now
`native_hooks/render_tooltip_pre.rs:9` `native_render_tooltip_pre` (renamed). Paths relative to
`horizon/crates/horizon-client/src/game/`.

## E. Action bar and HUD text (15 bundles)

**Verdict: stable route; drop the client fallback.**

`player.action_bar(host, Text)` (`vocab/src/host/players.rs:594-599`). (engine) It goes through the same player
lookup and send as `player.tell` (`horizon/crates/horizon-client/src/game/modding/native_server.rs:1279-1302`), and
`tell` reached the single-player host in the pilot. So the `say` fallback to `native_client_action_bar` is deleted in
all 12 bundles. The 4 one-off client lines (12's two "engine cannot ..." notes, 10 and 16's first line after chat)
become `action_bar` or `tell` on the server.

If a status line must live on the client (a mana or LP readout every frame): `gui_layer_post` on layer
`minecraft:overlay_message` with `DrawContext::text` (`vocab/src/hooks/gui_layer_post.rs`; layer ids in
`vocab/src/hooks/notes.rs:2283`). The value must reach the client by synced data; not designed here.

Skeleton (compiled): `action_bar(host, player, line)` and a `gui_layer_post` drawing on `overlay_message`.

## F. Item tooltips

**Verdict: stable route, same shape.**

`ItemPart::tooltip(&self, &dyn ClientHost, &mut TooltipEvent)` pushes `(Text, u32)` lines for our own items
(`vocab/src/hooks/tooltip.rs`; generated trait `ItemPart`). For vanilla items or every item (07's "mod name at the
foot"): `Hooks::item_tooltip` (`vocab/src/hooks/item_tooltip.rs`, event has `stack`, `advanced`, `creative`,
`lines`). Reorder or add images: `render_tooltip_gather_components` (`notes.rs:1737`).

Skeleton (compiled): `ItemPart for Tip` pushing one line, attached with `r.item_part(bag, Tip)`; `item_tooltip`.

## Recommended `sf3_host` helpers (thin wrappers, signatures only)

```rust
// A, machines
pub fn screen_layout(width: f32, height: f32, slots: &[[f32; 2]], inv: [f32; 2]) -> Screen;
pub fn data_at(data: &[i32], index: usize) -> i32;                    // 0 when the server has not sent it yet
pub fn bar_h(draw: &mut dyn DrawContext, origin: [f32; 2], rect: [f32; 4], value: i32, max: i32, argb: u32);
pub fn bar_v(draw: &mut dyn DrawContext, origin: [f32; 2], rect: [f32; 4], value: i32, max: i32, argb: u32);
pub fn text(draw: &mut dyn DrawContext, s: &str, at: [f32; 2], rgb: u32);          // adds 0xFF alpha
pub fn hit(at: [f32; 2], rect: [f32; 4]) -> bool;
pub fn set_menu_data(host: &mut dyn ServerHost, be: BlockEntityRef, values: &[i32]) -> bool;
// B and C, blockless menus
pub fn open_chest(host: &mut dyn ServerHost, player: PlayerRef, rows: u8, title: &str, items: Vec<Option<ItemStack>>) -> Option<i32>;
pub fn back_with_held(host: &mut dyn ServerHost, player: PlayerRef, window: i32, hand: Hand, slots: usize) -> bool;
pub fn set_menu_items(host: &mut dyn ServerHost, player: PlayerRef, window: i32, items: Vec<Option<ItemStack>>) -> bool;
pub fn menu_click_pickup(host: &mut dyn ServerHost, uuid: u128, window: i32, slot: usize, right: bool) -> Option<(Option<ItemStack>, Option<ItemStack>)>; // C: cursor/slot swap in one transaction, returns new (slot, cursor)
// D
pub fn show_panel(host: &mut dyn ClientHost, items: Vec<mod_api::Stack>);
pub fn own_screen_open(host: &mut dyn ClientHost) -> bool;
pub fn is_own_screen(host: &dyn ClientHost, view: &ScreenView<'_>) -> bool;
// E
pub fn action_bar(host: &mut dyn ServerHost, player: PlayerRef, line: &str) -> bool;
// F
pub fn tip(lines: &mut Vec<(Text, u32)>, s: &str, rgb: u32);
```

## Degrade or drop

- **Drop:** 19 `native_mods` list rows; `native_settings_refresh`; all 17 `native_client_action_bar` calls;
  17's "empty the bag while open, deposit on close" code; the `slots.rs` client-lib workaround in 03 04 05 08 11.
- **Degrade:** 19 Accessories and 15 Ender Pouch to a mod-driven chest menu (clicks handled in `menu_clicked`; drags,
  number keys and double-click collect refused at first). 15 Ender Pouch could instead keep its contents in the
  pouch and sync on close.
- **Degrade if play shows it is needed:** JEI's exact tooltip layering (draw in `screen_render_foreground`; fall
  back to the mixin targets listed in D).

## Not checked

- Nothing was played; every verdict above is from SDK source, engine docs and engine source.
- Whether `back_mod_menu_slots` and `open_menu` work for the single-player host's own player.
- Whether a backed chest menu (B) behaves on a dedicated server with a vanilla client (should not apply: Horizon
  client required for mod content).
- Whether the doc's claim that a blockless `player_open_mod_menu` serves "a backpack item's use"
  (`machine-menu-data.md`) holds with a block-less screen; engine source at `084ae44e40` says it closes without one.
- JEI's recipe-category feed from 6 bundles, and JEI's ~25 raw `game.*` helpers (`slot_view`, `menu_click`,
  `mod_recipe_screen`, `draw_tooltip_lines`...): only screen hooks were mapped here.
- 06's DE tool config GUI and 10's Forge/Table/Teleposer menus: only listed under A by their `screen` rows, not read.
- The `[[native.mixin]]` row format on main (`concepts/native-route/2-mixins.md` not read).
- `gui_layer_post` layer id spelling (`minecraft:overlay_message` taken from `notes.rs:2283`, which lists bare
  `overlay_message`; check which form the event carries).
- Whether `ScreenView.id` for our `mod_screen_open` screen is exactly `"mod"` in practice (doc says so,
  `host/screens.rs`).
