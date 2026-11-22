# JEI on the stable API (design note, 2026-11-20)

Question: how does `native/07_sf3_jei` (our port of Just Enough Items) move to Horizon's stable mod API, and where do
the machine recipe tabs go?

Sources read: `migration_stable_api_plan.md`, `api_map.md`, `stable_menus_screens.md` (pattern D), `sf3_host_api.md`;
the old bundle `native/07_sf3_jei/` (README, `horizon-mixin.toml`, `glue.rs`, the `h_*.rs` helpers); the six feeder
helpers `native/{02,04,05,08,09,10}_*/mixins/*/recipe_categories.rs` and `04`'s `glue.rs:2547`; the pilot
`mods/sf3_chance`; Horizon's archived Recipes viewer `horizon-mods/native/recipes/`.

Short names below:

- `vocab/` = the SDK at build `0a875da`, `C:\Users\chaxt\.sf3-tools\scratch_jei\.horizon\sdk\api\crates\horizon-mod-vocab\src\`.
- `gen.rs` = `...\horizon-mod-vocab\generated\mod_api_generated.rs` (same SDK).
- `eng/` = engine source `horizon/crates/horizon-client/src/game/` at checkout `084ae44e40` (newer than `0a875da`).
- `docs/` = `horizon/docs/modding/src/`.

Compile check: the skeleton in section 2.4 is `C:\Users\chaxt\.sf3-tools\scratch_jei\src\lib.rs`. `cargo check`,
`cargo test` (1 test) and `cargo horizon-mod check` pass ("111 items of the API ... 6 hooks ... Made for 0a875da").
Nothing was run in game.

## 0. Two facts that change the picture

1. **The engine hook our machine tabs used is gone.** All six feeder bundles inject at
   `native_hooks::Game::native_recipe_categories` (e.g. `native/04_sf3_tech_power/mixins/sf3_tech_power/horizon-mixin.toml:188-196`),
   and 07 reads them with `native_collect_recipe_categories` / `native_recipe_categories_version` (`glue.rs:472-480`).
   None of the three names appears anywhere under `horizon/crates` or `horizon/docs` on `084ae44e40` (grep). So the tab
   feed must be rebuilt, not just re-pointed (`api_map.md` rows 87, 332, 343, 426 agree).
2. **The engine has no recipe viewer of its own.** It has the *item panel widget* (engine draws it, a mod fills it), but
   Horizon's official Recipes viewer is a separate mod, archived as legacy `.hnmod` ("Launchers from 0.2.70 on can't
   load it ... A port to the new mod SDK is tracked in #1214", `horizon-mods/native/recipes/README.md:3-5`). With no mod
   filling it, nothing shows. So "the engine's own JEI-style panel" in `stable_menus_screens.md` means the widget only.

## 1. What bundle 07 does today (from the code)

7,421 lines (`wc -l native/07_sf3_jei/mixins/justenoughitems/*.rs`): `glue.rs` 1921, `config.rs` 1886, `runtime.rs`
1480, `view.rs` 1154, `sprites.rs` 257, `options.rs` 256, `defer.rs` 155, `config_sprites.rs` 133, 23 `h_*.rs`
helpers (about 180). Wiring: 8 modules and 23 injections in `horizon-mixin.toml`, 10 of them raw `target =` rows.

| Feature | How it works now | Where |
|---|---|---|
| Item list panel | JEI draws its own list right of every container screen and the creative inventory, in place of the game's panel (cancels `draw_mod_browser`). List = the creative search tab's items (subtypes: enchanted books, potions, tipped arrows) then every item in the recipe tables | `horizon-mixin.toml` injection `draw`; `glue.rs:628-664` (`build`), `:566` (`tab_titles`) |
| Search | JEI grammar: words, `"phrases"`, `-not`, `a \| b`, `@mod`, `#tooltip`, `$tag`, `%creative tab`, `&id`. Pure code with tests | `runtime.rs`; tooltip text from `glue.rs:1130` (`tooltips`) |
| Recipe lookup (R / left click) and uses (U / right click) | Over the list, bookmarks, recipe slots or any screen slot. Index built from the game's own recipe tables (`game.native_recipes()`), by kind: crafting, smelting, blasting, smoking, campfire, stonecutting, smithing, brewing | `glue.rs:460`, `:678-717`; slot keys `:1425` (`slot_key`, uses `game.slot_at`, `game.slot_view`) |
| Recipes JEI writes itself | Tipped arrows, shield patterns, firework rockets, anvil (repairs, every enchanted book with cost), grindstone, fuel per furnace, composting | `glue.rs:785` (`made_up_recipes`), `:944` (`extra_recipes`), `:1095` |
| Recipes screen | JEI's look: category tabs with station icon, catalysts on the left, pages, cycling ingredients, Backspace back, Esc/E close; drawn with JEI's sprites as pixel runs | `view.rs`, `sprites.rs`; opened with `game.mod_recipe_screen` |
| Per-machine categories | Not from JEI. Each machine bundle hard-codes its recipes in Rust in its own `runtime.rs` (e.g. Ex Nihilo `view_categories`, `native/02_sf3_exnihilo/mixins/sf3_exnihilo/runtime.rs:2618`; SAG Mill etc. as `category: "sf3_tech_power:sag_mill"`, `native/04_.../runtime.rs:1351`) and converts them to `NativeRecipeCategory` in its glue (`native/04_.../glue.rs:2547-2590`). JEI turns them into tabs: one slot per output with chance and count in its tooltip, notes under the recipe | `glue.rs:495-563` (`add_native_categories`) |
| Feeders | 02 sieve/hammer/crook/compost/barrel/crucible; 04 SAG Mill, Alloy Smelter, Slice'N'Splice, crusher, powered furnace, seed reprocessor; 05 roost laying and breeding; 08 steel chain; 09 Pure Daisy, Apothecary, Runic Altar, infusion; 10 Blood Altar, Hellfire Forge, roots | the six `recipe_categories.rs` helpers |
| Second category route | `register_category(PluginCategory)` that another native module calls directly. No SF3 bundle uses it (grep over `native/*/mixins`) | `glue.rs:44-90` |
| "+" transfer | Moves items into the inventory or crafting-table grid by ordinary slot clicks (`game.menu_click`), Shift = as many as possible; notes "missing" / "no room" | `glue.rs:1287-1408` |
| Bookmarks | Left of the screen; A over an item toggles it; saved to `config/justenoughitems/bookmarks.txt` | `glue.rs:410-445` |
| Cheat items in | Config button with Ctrl, or its key; creative: `game.give(stack)`, else `/give @s <key> <count>` by `game.send_command` | `glue.rs:1261-1280` |
| Tooltips | (a) mod name in blue italics at the foot of item tooltips (`tooltip` hook, `h_tooltip.rs`); (b) the game's tooltips moved over the overlays: 6 raw mixins note the tooltip vertices and redraw them last (`defer.rs`, `h_screen_*`, `h_tooltip_box/text/stack_*`); (c) game tooltips hidden under the recipes screen (`h_tooltip_hide.rs`) | `horizon-mixin.toml` rows `tooltip` ... `tooltip_hide` |
| Key binds | R, U, A over items; Ctrl+O hide overlays, Ctrl+F focus search, Page Up/Down, Backspace, Esc/E; cheat key. Keys listed on Options > Mods (`game.native_mod_key`, `game.settings.keys`) | `h_key.rs`, `h_char.rs`, `h_key_released.rs`; `glue.rs` |
| Config screen | A full MezzConfig GUI clone (category tree, search, check boxes, drop-downs, Undo) drawn over the Options screen, which is cancelled (`draw_options`) | `config.rs`, `options.rs`, `config_sprites.rs`, rows `render`, `options_cover`, `settings`, `settings_click`, `list` |
| Clipboard | Ctrl+V / Ctrl+C in the search box | `glue.rs:1226-1235` |
| Room on screen | Keeps clear of the recipe book, effect bars and toasts (`game.recipe_book_shift`, `game.toast_slots_used`) | `glue.rs`, `view.rs` |

## 2. What the engine gives, and how a mod adds recipe tabs

### 2.1 Free from the engine (stable)

| Piece | Stable API | Source |
|---|---|---|
| The panel itself: drawing, pages, page buttons, search box, JEI 1.12 layout | `ClientHost::panel_items(mod_id, Vec<Stack>)` (max 8192), `panel_style(mod_id, PanelStyle::Classic{..})` | `vocab/host/recipes.rs:62-88`; `vocab/client/types.rs:885-912`; `docs/how-to/items/panel-style.md` |
| Clicks, search text, keys over **any** item (panel or a screen slot) | `panel_event` hook, `PanelEvent::{Clicked, Search, Key{key, stack}}` | `vocab/hooks/panel_event.rs`; `vocab/client/types.rs:917-934` |
| "+" into the crafting grid and into machine menus | `transfer_recipe_id(recipe, max)`, `transfer_recipe_check`, `MenuPart::menu_transfer` | `vocab/host/recipes.rs:89-120`; `docs/concepts/capabilities/menu-slots.md` |
| Vanilla recipe data (crafting, cooking, stonecutting, smithing, mod types) | `Host::recipes_of_type(kind)` -> `Arc<[Recipe]>`; ingredients via `recipe_ingredient` | `vocab/host/recipes.rs:29`, `vocab/item/crafting.rs:146` |
| Our own recipe screen | `mod_screen_open` / `mod_screen` / `mod_screen_close`, draw in `screen_render_post` | `vocab/host/screens.rs:60-118` |
| Giving items | creative: `ClientHost::give(item, count)`; else `send_chat("/give @s ...")` | `vocab/host/items.rs:144`; `vocab/host/network.rs:53` |
| Mod name in tooltips | `item_tooltip` hook (`lines: &mut Vec<(Text, u32)>`) | `vocab/hooks/item_tooltip.rs`; `gen.rs:16013` |
| Rebindable keys | `Registrar::register_key_mapping(KeyRegistration)` | `vocab/parts/key_mappings.rs:11`; `vocab/client/key_mapping.rs:40` |
| Keys on our screens | `screen_key_pressed_pre`, `screen_char_typed_pre` | `gen.rs:2764`; `stable_menus_screens.md` D |
| Settings page | `register_setting(SettingSpec)` on Options > Mods | `vocab/parts/settings.rs:21`; `docs/how-to/mod-settings.md` |
| Bookmarks file | `Host::config_files()` | `vocab/host/config.rs:50` |
| Clipboard | `clipboard_text`, `set_clipboard_text` | `vocab/host/client_input.rs:93,99` |
| Names, tags, fuel, compost, enchantments | `hover_name`, `tags()`, `item_burn_time`, `item_compost_chance`, `enchantments`, `enchantment_min_cost`, `item_resource_repairable`, `item_keys`, `registry_entries` | `vocab/host/items.rs:36,41,151-163,178`; `vocab/host/tags.rs:11`; `vocab/host/keys.rs:38,60` |
| Overlay layering, room, exclusion | `screen_render_foreground`, `render_tooltip_pre`, `screen_room`, `screen_exclusion` | `stable_menus_screens.md` D table |

What is **not** free: the list's contents, the search grammar (we get the raw text), the recipe index, the recipe
screen drawing, bookmarks, the JEI-made recipes, and every machine tab. Those are our code either way.

Also free but not used here: `recipe_book_categories` puts a custom recipe type into the **vanilla recipe book** of a
mod menu (`docs/how-to/items/recipe-book-categories.md`). It needs a registered menu and recipe book type and uses
vanilla layouts only (shaped, shapeless, furnace, stonecutter, smithing), so chance outputs and notes don't fit. Not a
JEI tab.

### 2.2 No stable recipe-category API

There is no host call or hook to hand the engine recipe tabs. The engine still has a recipe page renderer inside the
panel, `Game::native_panel_recipes(mod_id, title, tabs, tab, views)` (`eng/native_hooks/shared.rs:2288`;
`eng/modding/native_panel_recipes.rs`), and the stable `PanelEvent` already has its answers (`SlotClicked`, `Action`,
`Page`, `Back`, `Tab`, `vocab/client/types.rs:935-958`), but the call itself is not on `ClientHost` (its only mention in
the SDK is the doc comment at `vocab/client/types.rs:937`).

### 2.3 How a machine mod adds its tabs: a code dependency on `sf3_jei`

`docs/concepts/dependencies.md`: "A mod can publish functions and statics from its root crate for another mod to
call." The machine mod declares `sf3_jei` as an optional dependency in `horizon-mod.toml` and calls it behind
`mod_api::if_installed!` (macro exported, `vocab/exports/horizon_mod_api_macros.rs:58`). So:

- `mods/sf3_jei/src/lib.rs` publishes `pub fn register_category(Category)` and the `Category` / `ViewRecipe` /
  `Output` types (the same fields as the old `NativeRecipeCategory`, so each bundle's existing `view_categories` maps
  across one to one).
- Each machine mod, in `register`:

```toml
# mods/sf3_tech_power/horizon-mod.toml
[dependencies]
sf3_jei = { version = "^0.1", optional = true, side = "client" }
```

```rust
// mods/sf3_tech_power/src/lib.rs, inside Hooks::register (host form not checked: see "Not checked")
mod_api::if_installed!(host, sf3_jei, {
    for c in runtime::view_categories() { sf3_jei::register_category(c.into()); }
});
```

The recipe data stays where it lives today, in the machine's `runtime.rs` tables, which also drive the machine.
Data-pack-driven alternative (only if a bundle moves its recipes to JSON anyway): `register_recipe_type` +
`register_raw_recipe_serializer` (`vocab/parts/crafting_recipes.rs:181`, `vocab/parts/recipe_serializers.rs:66-75`),
files in `data/<ns>/recipe/*.json`, and `sf3_jei` reads them with `recipes_of_type("<ns>:<type>")`. That needs no code
dependency but still needs tab titles and icons from somewhere, so it is the second choice.

### 2.4 Compiled skeleton

`C:\Users\chaxt\.sf3-tools\scratch_jei\src\lib.rs` (passes `cargo check`, `cargo test`, `cargo horizon-mod check`).
The machine side is a module in the same crate, so the cross-crate call and `if_installed!` are **not compiled**.

```rust
pub struct Category { pub id: String, pub title: String, pub icon: String,
                      pub catalysts: Vec<String>, pub recipes: Vec<ViewRecipe> }
static CATEGORIES: Mutex<Vec<Category>> = Mutex::new(Vec::new());
pub fn register_category(c: Category) { /* replace by id, push */ }

#[mod_api::horizon_mod]
impl Hooks for Mod {
    fn register(&self, r: &mut dyn Registrar, _: &RegistrationContext) {
        r.register_key_mapping(KeyRegistration::new("recipe", "key.keyboard.r").context(KeyConflictContext::Gui));
        r.register_key_mapping(KeyRegistration::new("uses", "key.keyboard.u").context(KeyConflictContext::Gui));
    }
    fn panel_event(&self, host: &mut dyn ClientHost, e: &mut PanelEventEvent<'_>) {
        if e.mod_id != MOD_ID { return; }
        match e.event {
            PanelEvent::Search(text) => { /* runtime.rs filter, then panel_items again */ }
            PanelEvent::Key { key, stack } => {
                let id = stack.item.id(&*host);
                if key == "key.keyboard.r" && !recipes_making(&id).is_empty() { let _ = host.mod_screen_open(MOD_ID); }
            }
            _ => {}
        }
    }
    fn screen_render_post(&self, host: &dyn ClientHost, e: &mut ScreenRenderPostEvent<'_>) {
        if e.screen.id == "mod" && host.mod_screen() == Some(MOD_ID) { /* draw the recipe page */ }
    }
    fn screen_key_pressed_pre(&self, _: &dyn ClientHost, e: &mut ScreenKeyPressedPreEvent<'_>) -> Flow { .. }
    fn item_tooltip(&self, host: &dyn ClientHost, e: &mut ItemTooltipEvent<'_>) {
        let ns = e.stack.item().id(host); /* push the mod name line */
    }
}
pub fn show_list(host: &mut dyn ClientHost, items: Vec<mod_api::Stack>) {
    host.panel_style(MOD_ID, PanelStyle::Classic { centred_search: false, window_width: 0 });
    host.panel_items(MOD_ID, items);
}
```

## 3. Features with no clean stable route

| Feature | Least-bad option | Why |
|---|---|---|
| Recipe pages inside the panel (engine-drawn) | **Degrade**: draw our own recipe screen on `mod_screen_open` (stable, section 2.1). Optional later: a `[[native.mixin]]` row whose helper calls `game.native_panel_recipes(..)`; target `eng/native_hooks/shared.rs:2288` exists, format in `docs/concepts/native-route/2-mixins.md`. Plus the upstream request below | The old bundle drew its own screen anyway, so the stable route is the same work |
| Creative-tab subtypes and `%tab` search | **Degrade**: list = `item_keys()` plus subtypes we build (potions from `registry_entries("minecraft:potion")`, books from `enchantments()`); drop the `%` prefix | No host read of creative tab contents; `build_creative_mode_tab_contents` only adds items (`vocab/hooks/build_creative_mode_tab_contents.rs`) |
| Brewing tab | **Degrade**: hard-code vanilla's brewing mixes in `runtime.rs` (fixed in vanilla) | No stable brewing read (grep of `vocab/host`); brewing is not a data recipe type |
| Game tooltips over our overlays | **Degrade** first: draw overlays in `screen_render_foreground`, hide under our screen with `render_tooltip_pre`. If play shows wrong layering: the 6 raw mixins, targets confirmed on `084ae44e40`: `eng/interface/inventory_slots.rs:422`, `eng/interface/creative_screen.rs:108`, `eng/blocks/stations.rs:2154` and `:2209`, `eng/blocks/stations/tooltip.rs:87` | `stable_menus_screens.md` D |
| MezzConfig-style config screen | **Drop**: settings on the `register_setting` page; Classic's wrench already opens it (`docs/how-to/items/panel-style.md`) | 2,275 lines for a look-alike; `draw_options` (`eng/interface/options.rs:181`) would stay a raw mixin otherwise |
| Avoiding toasts | **Drop** | No toast read on the host (grep) |
| Bookmarks as a second item list | Stable but our own drawing: `DrawContext::item_stack` in `screen_render_post`, clicks in `screen_mouse_button_pressed_pre`, room via `screen_exclusion_areas` | Only one mod panel shows at a time (`vocab/host/recipes.rs:62-68`) |

Upstream request draft (one paragraph, for #1214 or a new issue on `horizon-rust/horizon`):

> **ClientHost::panel_recipes for recipe viewers.** The stable item panel (`panel_items`, `panel_style`, `panel_event`)
> already answers recipe-page input (`PanelEvent::SlotClicked`, `Action`, `Page`, `Back`, `Tab`), and the engine
> already lays recipe pages out (`Game::native_panel_recipes`, `game/native_hooks/shared.rs`), but no stable call shows
> a page, so a viewer ported to the SDK (the official Recipes viewer, #1214, or a JEI port) must draw recipe pages
> itself. Please add `RecipesClientHost::panel_recipes(mod_id, title, tabs: Vec<Stack>, tab: u32,
> recipes: Vec<RecipeView>)` with `RecipeView` = the `NativeRecipeView` shape (slots of alternative stacks, results
> with chance and count range, notes, layout), plus a read of the creative inventory's built tab contents so a viewer
> can list subtypes without rebuilding them. A pack with many machines would then share one renderer and one look.

## 4. Internal engine calls in 07 with no `sf3_host` or stable equivalent

From `grep -ohE "game\.[a-z_]+" native/07_sf3_jei/mixins/justenoughitems/*.rs` (66 distinct names, counts in the
first table of the grep) and the `horizon_client::` paths. Rows with a stable replacement are listed so the gap is
clear; "none" rows are the real list.

| Old call | Replacement |
|---|---|
| `game.native_recipes()`, `NativeRecipeKind` | `recipes_of_type` per kind (`vocab/host/recipes.rs:29`); brewing: none (section 3) |
| `native_collect_recipe_categories`, `native_recipe_categories_version` | none in the engine; `sf3_jei::register_category` (section 2.3) |
| `game.creative_screen.search_items()`, `.tabs`, `creative_tab_title` | none (section 3) |
| `game.res.items()` (exists, max stack) | `item_keys`, `max_stack_size` (`vocab/host/keys.rs:60`, `vocab/host/items.rs:12`) |
| `game.res.providers`, `game.pack.names`, `item_tooltip::name_line` | `hover_name`, `translate` (`vocab/host/items.rs:151`, `vocab/host/config.rs:198`) |
| `game.enchantments()`, `game.potions.effects` | `enchantments()`; potions: `registry_entries("minecraft:potion")` (not checked for effect details) |
| `stations::is_valid_repair_item` | `item_resource_repairable` (`vocab/host/items.rs:178`) |
| `item_data::decode_components`, `command_components` | none as such; `Stack.components` is a string already (`vocab/client/types.rs:873-883`); the `/give` key stays our string building |
| `game.slot_view`, `game.slot_at`, `game.cursor` | `PanelEvent::Key` gives the stack under the pointer; `screen_hovered_item`, `menu.slot_boxes`, `cursor()` (`vocab/host/screens.rs:46`, `vocab/host/client_input.rs:18`) |
| `game.menu_click`, `game.carried`, `game.craft_size` | `transfer_recipe_id` replaces the hand-made transfer; `menu_click`, `menu_carried` if needed (`vocab/host/menus.rs:97,157`) |
| `game.give`, `game.send_command`, `game.creative` | `give`, `send_chat`, `player_is_creative` (`vocab/host/items.rs:144`, `network.rs:53`, `players.rs:408`) |
| `game.clipboard.get/set` | `clipboard_text` / `set_clipboard_text` |
| `game.translate`, `horizon_client::lang::code` | `translate`; `client_language` (`vocab/host/services.rs:68`) |
| `game.mod_recipe_screen`, `game.screen`, `game.title`, `game.container`, `game.station*` | `ScreenView.id` in screen hooks, `observed_screen_id` (`vocab/host/screens.rs:131`) |
| `game.draw_tooltip_lines`, `game.stack_tooltip`, `game.draw_stack_tooltip_with`, `game.draw_item`, `game.draw_carried` | `DrawContext::gui_tooltip`, `item_stack`, `gui_draw_item_with` (`vocab/host/draw.rs:78,92,182`); the carried stack is drawn by the game over `screen_render_foreground` |
| `game.gui.atlas`, `HudBatch`, `HudAtlas`, `ui::nine_slice`, `ui::menu_background` | `DrawContext::sprite`, `gui_nine_slice`, `draw_menu_background`, `fill` (`vocab/host/draw.rs:43-177`) |
| `ui::EditBox`, `game.recipe_search_focused`, `game.station_typing` | `widget_text_field` (`vocab/host/draw.rs:206`); the panel's own search box replaces ours |
| `game.audio.play_button_click` | `play_local_sound` (`vocab/host/effects.rs:38`) |
| `game.native_setting`, `native_set_setting`, `game.native_on` | `setting`, `set_setting`, `on` (`vocab/host/config.rs:27-38`) |
| `game.native_data_dir`, `native_data` | `config_files()` / `data_files()` (`vocab/host/config.rs:50,57`) |
| `game.native_mod_key`, `game.settings.keys`, `keybinds::key_code` | `register_key_mapping`; reading the player's rebinding inside `panel_event`: not checked |
| `game.native_apply_screen_blur` | `apply_screen_blur` (`vocab/host/screens.rs:53`) |
| `game.recipe_book_shift` | `screen_exclusion()` (does it include the recipe book? not checked) |
| `game.toast_slots_used` | none (drop) |
| `game.list_native_mods`, `game.settings.mods`, `native_settings_refresh`, `open_options_at`, `options_ui::Page::NativeMod`, `game.ui.options`, `game.handle_option_events`, `game.settings.file`, `game.panel.recipes_settings_return` | none; the config screen is dropped, the settings page is the engine's |
| `game.mod_browser_closed`, `draw_mod_browser` | none needed: the engine panel is ours through `panel_items`; close via `screen_closing` |
| `game.renderer` (screen size) | `DrawContext::size()` (`vocab/host/draw.rs:28`) |
| `game.player.is_none/is_some` | `client_level_load` hook / `WorldOnly` access refusing (`gen.rs:3130`) |

## 5. Recommended design for `mods/sf3_jei`

**Contains** (one native stable mod, client side, layout as `mods/sf3_chance`: `src/lib.rs` hooks, `src/runtime.rs`
pure, plus `src/view.rs`, `src/sprites.rs`):

- `runtime.rs`: the old file nearly as is (search grammar, index, lookups, bookmarks list, its tests); remove its use of
  creative-tab titles.
- `lib.rs`: the public `register_category` registry; `register` (keys, settings); `panel_event` (search, R/U/A,
  clicks, cheat give); `screen_render_post` (recipe screen, bookmarks); input hooks; `item_tooltip`; `screen_closing`.
- `glue` part inside `lib.rs` or `glue.rs`: build the list (`item_keys` + built subtypes), the vanilla recipes from
  `recipes_of_type`, JEI's made-up recipes (`made_up_recipes`, `extra_recipes` moved across), plugin categories.
- `view.rs` + `sprites.rs`: the recipe screen with JEI's look through `DrawContext`.
- No mixins at the start. Tooltip layering mixins only if play shows they are needed.

**Moves into each machine mod** (02, 04, 05, 08, 09, 10, when that bundle is converted): an optional `sf3_jei`
dependency and an `if_installed!` call that registers the categories its own `view_categories` already builds. The
old `recipe_categories.rs` helper and the `NativeRecipeCategory` conversion in its glue (about 40 lines in
`native/04_.../glue.rs:2547-2590`) are deleted. Exnihilo's `items` argument (tagged items) becomes a `tags()` read in
that mod.

**Size against the old bundle** (estimate, not written): runtime ~1,400 (was 1,480), glue ~700 (was 1,921: no table
building from the engine's raw tables, no hand-made transfer, no config wiring), view ~600 (was 1,154: the engine draws
the list and search box), sprites 257 (kept), lib ~250. About **3,200 lines, ~45% of 7,421**. Dropped outright:
`config.rs`, `options.rs`, `config_sprites.rs`, `defer.rs`, all 23 `h_*.rs` helpers (about 2,600 lines). Each machine
mod gains ~15 lines and loses ~40.

**Steps:**

1. Convert the pilot pattern: `cargo horizon-mod new`-style folder `mods/sf3_jei` with `sf3_host.rs` copy, manifest
   `side = "client"` (check the manifest key for a client-only mod; not checked), id `sf3_jei`.
2. Move `runtime.rs` across; `cargo test` green.
3. Item list: `item_keys` + subtypes -> `panel_items` with `PanelStyle::Classic`; search through `PanelEvent::Search`.
4. Vanilla recipes from `recipes_of_type` for the 8 kinds; move `made_up_recipes` / `extra_recipes`; hard-code brewing.
5. Recipe screen on `mod_screen_open`: tabs, catalysts, pages, cycling; R/U/Backspace/E; "+" by `transfer_recipe_id`.
6. Publish `register_category`; unit test it (the scratch test is the model).
7. Bookmarks (own drawing, `config_files`), cheat give, clipboard, mod-name tooltip line, settings page.
8. First feeder: `04_sf3_tech_power` when it converts: optional dependency + `if_installed!`; check the launcher
   builds a native-to-native code dependency (the pilot notes launcher 0.2.93 refuses a *content* mod dependency,
   `mods/sf3_chance/horizon-mod.toml`).
9. Remaining feeders 02, 05, 08, 09, 10 as each bundle converts.
10. Play test: list, search, R/U on panel and slots, a machine tab, "+" in a crafting table, tooltip layering. Only then
    decide on the raw tooltip mixins and file the upstream request.
11. Retire `native/07_sf3_jei`.

## Not checked

- Nothing was run in game.
- Cross-mod code dependency between two native stable mods: `if_installed!` form inside `register` (it takes `host`;
  which value to pass in `register` is not checked), whether the launcher builds it, whether a public `static` is shared
  across the two compiled mods (`docs/concepts/dependencies.md` says statics are published; not tried).
- Whether `PanelEvent::Key` fires for keys over the screen's own slots in practice (doc says so,
  `vocab/client/types.rs:927-929`) and how to read the player's rebinding of a registered key there.
- Whether `transfer_recipe_id` works for crafting recipes the player's book doesn't hold (doc says it doesn't need the
  recipe learned for `transfer_recipe`, `vocab/host/recipes.rs:97-98`).
- Potion and tipped-arrow subtypes from `registry_entries` (component strings for `Stack`).
- `screen_exclusion()` covering the recipe book.
- The manifest key for a client-only mod and the dependency `side` field values (`docs/reference/manifest.md` not read).
- The size estimate is from line counts, not written code.
- Engine source read at `084ae44e40`, SDK at `0a875da`; the three `native_recipe_categor*` names may have been removed
  between them or before; either way they are absent on both the SDK and the engine checkout.
