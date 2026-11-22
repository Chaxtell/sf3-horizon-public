# Conversion note: `native/07_sf3_jei` -> `mods/sf3_jei` (2026-11-21)

Design: `jei_stable_route.md`. Client-only native mod (`side = "client"`), no `[[native.mixin]]`. `runtime.rs` (search grammar, index,
recipes-screen model, settings, labels; 15 tests) and `sprites.rs` copied unchanged (`cmp` ok); `sf3_host.rs` byte-identical to
`mods/sf3_host/sf3_host.rs`. 7 new tests in `src/glue_tests.rs` (22 in all). New adapter calls in `src/host_ext.rs`.

Files: `lib.rs` (Hooks), `state.rs` (state, clicks, keys, search, panel push), `data.rs` (items and recipes into `runtime`'s model),
`view.rs` (overlay drawing on `DrawContext`), `api.rs` (public tab registry), `vanilla.rs` (brewing and anvil-cost tables),
`assets/sf3_jei/lang/en_us.json` (key and setting labels). 5,015 lines in `src/` (runtime + sprites + sf3_host copies 2,079 of them)
against 7,421 in the old bundle.

## Feature by feature

| Old | New | Notes |
|---|---|---|
| Ingredient list drawn by the bundle | engine panel: `panel_items` + `panel_style(Classic)` | list pushed when the search, settings or data change; max 8192 stacks |
| Search box + grammar (`@ # $ % & -`, quotes, `\|`) | engine box -> `PanelEvent::Search` -> `runtime::Query` | `#` tooltip text built once on first tooltip search (`ItemResource::tooltip`, plain text) |
| List order | registry order, each item followed by its subtypes (potions in 3 bottles, tipped arrows, enchanted books per level) | |
| Recipe index | `recipes_of_type` for crafting, stonecutting, smelting, smoking, blasting, campfire, smithing | shaped placement from the recipe file's `pattern`; shapeless; transmute; smithing transform/trim |
| JEI's own recipes | rebuilt in `data::made_up` | tipped arrows, shields, rockets, 3 fuel tabs, compost, anvil repair (`minecraft:repairable`) and books, grindstone |
| Brewing | `vanilla.rs` table | hard-coded (no stable brewing read) |
| Recipes screen (tabs, catalysts, pages, every layout, "+", history) | drawn over the container in `screen_render_foreground`, input via `screen_*_pre` returning `Cancel` | `mod_screen_open` refuses while a container is open, so not a mod screen; panel told the window width |
| Bookmarks | drawn left of the window; file `config/sf3_jei/bookmarks.txt` | same one-key-a-line format |
| Recipes / uses / bookmark keys (R, U, A) | over panel items and screen slots: `PanelEvent::Key`; over overlay slots: `screen_key_pressed_pre` | |
| Back, page up/down, Escape/E close | `screen_key_pressed_pre` while the recipes screen is open | |
| Ctrl+O overlay, cheat and bookmark toggles | key mappings (Options > Controls, GUI context) | |
| Cheat give | creative `give` for plain items; `/give @s <key> <n>` via chat for component stacks or survival | left = max stack, right = 1 |
| "+" transfer | `transfer_recipe_id(id, shift)` | 2x2 in the inventory, 3x3 at a crafting table |
| Tooltips | mod name line on every item tooltip (`item_tooltip`); overlay tooltips via `gui_tooltip`; game tooltips under the overlay hidden (`render_tooltip_pre`) | |
| JEI config screen | Options > Mods settings page: 7 toggles + 5 search-mode choices | read with `setting_bool` / `setting_choice` |
| `native_recipe_categories` (other bundles' tabs) | `sf3_jei::register_category` (below) | |

## Public API (root crate, `sf3_jei::`)

```rust
pub fn register_category(c: Category);            // add, or replace the tab with the same id
pub fn remove_category(id: &str) -> bool;
pub fn categories() -> (Vec<Category>, u64);      // tabs in order + registry version
pub fn category(id: &str, title: &str, subtitle: &str, icon: &str, catalysts: &[String],
                recipes: impl IntoIterator<Item = ViewRecipe>) -> Category;
pub fn recipe<I: Into<Input>, O: Into<Output>>(inputs: impl IntoIterator<Item = I>,
                outputs: impl IntoIterator<Item = O>, lines: impl Into<Lines>) -> ViewRecipe;
pub struct Category { id, title, icon, catalysts: Vec<String>, recipes: Vec<ViewRecipe> }
pub struct ViewRecipe { inputs: Vec<Input>, outputs: Vec<Output>, lines: Vec<String> }
pub struct Input { items: Vec<String>, count: u32 }               // From String, &str, Vec<String>, (String|Vec<String>, u32|i32)
pub struct Output { item, chance: f32, min: u32, max: u32, notes } // From (String, u32|i32), (String, u32|i32, f32), (String, f32, u32, u32, Vec<String>)
```

Items are named as `/give` names them (`minecraft:potion[...]`) or `#tag`. A mutex and a version counter: safe from any mod's `register`,
world-start or tick hook, either side, any order. The viewer rebuilds on the client tick after the version moves. On a server
without `sf3_jei` the call is skipped by `if_installed!`.

Machine mod, `horizon-mod.toml`:

```toml
[dependencies]
sf3_jei = { version = "^0.1", optional = true }
```

Rust (one line per tab, from the `view_categories` table its runtime already has; Immersive-style shape: `inputs` + `input_counts`,
outputs `(item, chance, min, max, notes)`):

```rust
mod_api::if_installed!(host, sf3_jei, {
    for c in runtime::view_categories() {
        sf3_jei::register_category(sf3_jei::category(&c.id, &c.title, &c.subtitle, &c.icon, &c.catalysts,
            c.recipes.into_iter().map(|r| sf3_jei::recipe(r.inputs.into_iter().zip(r.input_counts),
                r.outputs.into_iter().map(|o| (o.item, o.chance, o.min, o.max, o.notes)), r.notes))));
    }
});
```

Botania-style outputs `(String, i32)` go straight in: `r.outputs`.

## Degraded or dropped

- `%` creative-tab search never matches (no stable read of a tab's items).
- `$tag` search and the tag badge know only tags named by a recipe file or a registered tab (no item-to-tags read).
- Brewing: vanilla's mixes hard-coded; a mod's brews are missing. Anvil book costs: vanilla's `anvil_cost` table; a mod's enchantment costs 1.
- Smithing trim results drawn as the untrimmed base item.
- Creative give drops components, so component stacks go through `/give` (needs cheats/op).
- Ctrl+click on the wrench to toggle cheat dropped (the engine's wrench opens the settings page); use the key or settings.
- Ctrl+F focus search dropped (the panel's box takes no focus request).
- The engine list's own page keys and the toast avoidance: the engine's panel decides.
- The JEI config screen clone dropped: settings page instead (no "clear bookmarks" button; delete the file).
- Inventory key read as its default `E` to close the recipes screen.
- Overlay tooltips: name, `ItemResource` tooltip lines (mod tooltip callbacks skipped), extra lines, mod name.
- Clicks outside the overlay while the recipes screen is open still reach the container (only the overlay's own rectangles are taken).
- Toggles flipped by key are written with raw `set_setting(.., "true"/"false")`; value format of the settings file not verified.

## In-game checklist

1. Open the inventory: panel shows every item; type `stick`, `@minecraft`, `&oak`, `-log`, `#fire` (tooltip), `$logs`.
2. R / U on a panel item and on an inventory slot: recipes / uses open over the screen; tabs, arrows, wheel, title click (all recipes), Backspace, Escape.
3. Torch recipe in the crafting table: the 1x2 sits in the middle column; "+" fills the grid; Shift+"+" fills max.
4. Furnace tab: flame, arrow, time and XP; fuel tabs; brewing tab (water -> awkward -> potion); anvil books with cost colour; grindstone XP.
5. A bookmark: A over an item, the list left of the window, survives a restart (`config/sf3_jei/bookmarks.txt`).
6. Cheat key on, creative: left click gives a stack, right click one; a potion goes through `/give`.
7. Ctrl+O hides and shows the panel; settings page toggles and search modes act at once.
8. A machine mod calling `register_category`: its tab shows after vanilla's with catalysts and chance lines.
9. Mod name line in blue italics on a game tooltip; no game tooltip under the overlay.

## Not checked

Nothing ran in the game. Not checked: native-to-native call from a machine mod; panel layout beside the recipes window
(`window_width`); whether `transfer_recipe_id` accepts the made-up recipes' ids; the settings file's value format for raw writes;
the engine HUD sprites `horizon/jei/*` drawing from a mod's `DrawContext`; build time of the data on a large pack (once per world and
language).

## Machine mod wiring (pilot: sf3_immersive)

Steps (done in `mods/sf3_immersive`; repeat per mod):

1. `horizon-mod.toml`: add `[dependencies]` with `sf3_jei = { version = "^0.1", optional = true }`. Nothing in `Cargo.toml`: the launcher adds the
   path dependency and the Cargo feature `sf3_jei` at build time.
2. New `src/jei.rs`: `pub fn register(host: &dyn ClientHost)` with a `static DONE: AtomicBool` swap (once), then `mod_api::if_installed!(host, sf3_jei, { ... })`
   around the loop over `view_categories()`. Use `crate::runtime::...` by full path inside the block (a `use` would be unused when the block is compiled out).
3. `src/lib.rs`: `mod jei;` and, in `impl Hooks for Mod`, `fn client_tick_post(&self, host: &mut dyn ClientHost, _: &mut ClientTickPostEvent) { jei::register(host); }`
   (import `ClientTickPostEvent`). No world-start phase exists in the API; the viewer is client-only, so a client hook is the right one.
4. Output tuples: this runtime's outputs are `(item, count, chance)`, which `Output` takes as `(String, i32, f32)`: pass `r.outputs` straight in, not the
   five-field form above. Notes `String` goes in as `lines`.

Local gates: `cargo check`, `cargo test` and `cargo horizon-mod check` pass. Without the feature the `if_installed!` block is compiled out (`#[cfg(feature = "sf3_jei")]`), so
`sf3_jei::...` is never resolved or type-checked locally; `cargo check` warns `unexpected cfg condition value: sf3_jei` (the launcher declares the feature). Only a
launcher build with `sf3_jei` installed type-checks the block and shows whether the tabs appear.
