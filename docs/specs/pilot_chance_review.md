# Pilot review: `mods/sf3_chance` against `native/21_sf3_chance` (2026-11-20)

Read-only review. Sources: `mods/sf3_chance/src/lib.rs`, `src/sf3_host.rs` (byte-identical to `mods/sf3_host/sf3_host.rs`,
checked with `fc /b`), `horizon-mod.toml`, `Cargo.toml`; old `mixins/sf3_chance/glue.rs`, `horizon-mixin.toml` and the
helper files; SDK `mods/sf3_chance/.horizon/sdk` (build 0a875da); docs `horizon/docs/modding/src`. Nothing was run.

## 1. Behaviour differences

- mods/sf3_chance/src/lib.rs:209: high: delayed jobs run from `server_tick`, where "which level self.world holds here is not defined" (SDK `hooks/server_tick.rs`), and the calls they use refuse a level not in place: `LevelRef::spawn_mob` returns None for "a level not in place", `summon` None "for another dimension" (SDK `host/entities.rs:53-61`), `set_block` returns typed errors for unavailable levels. So Mob, Entity (anvil, TNT, XP, armour stand), Block, Replace and Torches steps of a cube broken outside the level in place (Nether, End, a second player's level) can fail silently. Only Command steps are safe (`render` adds `execute in <dim>`). Play covered summons, not the dimension (not checked in play). Fix: run due jobs from `level_tick_post` (server side, `event.level: LevelRef`), each level taking only jobs whose `dimension` matches; keep `server_tick` only to update `NOW`.
- mods/sf3_chance/src/lib.rs:193: medium: the client side now returns `Continue`, so the client sees `Pass` on the main hand and goes on to the off hand, sending a second use packet. The server cancels only the hand that holds the Scanner, so an off-hand block or item still gets used on the cube (a torch placed, a second Scanner telling the chance twice). The old hook was server-only and the old engine's client path was not read (not checked). Fix: on `HostSide::Client` also return `Flow::Cancel` with `InteractionResult::Success` when `click.stack` is the Scanner and `h::block_id` is the cube (all `h::` reads take `&dyn Host`, and `ClientHost: Host`).
- mods/sf3_chance/src/lib.rs:195: low: an off-hand Scanner with an empty main hand now scans (the hook fires once per hand, and the main hand passes). The old code read only `game.held()`. Accept it or check `click.hand == Hand::Main`.
- mods/sf3_chance/src/lib.rs:191: low: `right_click_block` fires for spectators too (hook doc), so a spectator holding a Scanner scans and gets the chat line. Fix: skip `GameMode::Spectator`.
- mods/sf3_chance/src/lib.rs:158: low: delay-0 steps can now run one tick earlier. The old clock was `game_time` read during the break (`due = game_time + 1`). The new one is `NOW`, which is last tick's `ServerTickEnd` value, so `due = NOW + 1` is the current tick and the step runs at the end of the break's own tick. The cube is already removed by then, so the header promise still holds (not checked in play). Fix if needed: `now + 2`.
- mods/sf3_chance/src/lib.rs:277: low: `give` (`give_stack`) refuses a `Dead` player and drops nothing. The old code dropped the leftover at the cube with `spawn_item`. A Give step that lands while the player is dead is lost.
- mods/sf3_chance/src/lib.rs:86: low: if `set_slot` refuses the damaged pendant (`PlayerDataRefusal::Stack`: "damage the item does not allow"), the bonus still applies and the pendant never wears out. Whether the content pendants carry `max_damage` is not checked. Fix: return the bonus only when `set_slot` succeeded, or check the pendant item's `max_damage`.
- mods/sf3_chance/src/lib.rs:168: low, unchanged from old: `loot_drops` and `on_block_placed_by` do not check `h::on`, so with the mod switched off a cube still drops nothing (only the Silk Touch Pendant gets it back). Fix: `if !h::on(host, m::ID) { return }` first.
- mods/sf3_chance/src/lib.rs:175: low, unchanged from old: `BROKEN` is keyed by position only. `event.context.dimension` is available now, so key by `(dimension, pos)`.
- Creative and spectator breaks: same as old (lib.rs:144). `loot_drops` does not hear creative breaks, so the stale `BROKEN` entry is cleared once the list passes 16, as before.
- Giant and compact cubes (`chancecubes:giant_chance_cube`, `compact_giant_chance_cube` exist in `content/chancecubes`): ignored by old and new alike. Not a regression.
- Multiplayer guests: `break_block` and `right_click_block` swap the acting player's state in (SDK `host/services.rs:236-240`), so `h::dimension` there is the breaker's level, the same as the old `player.dimension`. `click.dimension` and `context.dimension` would say it explicitly.
- World unload: the same three phases clear `JOBS`, `BROKEN` and `LAST` (lib.rs:121), as before.

## 2. Bugs

- mods/sf3_chance/src/lib.rs:38: low: `NOW` is not reset when the world closes, while `LifecycleContext::tick` restarts at 0 on each open (SDK `world/types.rs:1160`). A break before the new world's first `ServerTickEnd` would get `due` values from the old world's clock and wait that long. That is unlikely but free to prevent. Fix: `NOW.store(0)` in the same `world_lifecycle` branch.
- mods/sf3_chance/src/lib.rs:42: low: the RNG is seeded once per process from `NOW`, a small per-open tick count. Two worlds opened in a session share the stream, and an early first break seeds near 0. The old seed (`game_time`) had the same once-per-process shape. Fix (optional): also reset `RNG` on close.
- Locks: none is held across a host call (`JOBS` is dropped before `run`; `rng`, `LAST` and `BROKEN` guards are short). Poisoning is handled with `into_inner` throughout. No panics found: no `unwrap`, `expect` or slice indexing on host data.
- mods/sf3_chance/src/lib.rs:9: low: design step 6 asks for `src/glue_tests.rs` (FakeHost tests: the Command job and the custom-data round trip). The file and the `mod glue_tests;` line are missing, so only the 28 runtime tests run. Fix: add them as the design says.

## 3. `sf3_host` as the shared adapter

- mods/sf3_chance/src/sf3_host.rs:54: medium: `be_merge` can only add or overwrite keys. The old `native_with_mod_block_entity` (369 calls across the bundles' mixin `.rs` files, the most used write after `native_block`) is a read-modify-write that can also remove keys and change nested values. Fix: add `be_update(host, dim, pos, |c: &mut Compound|)` (read with `data`, write the whole compound with `merge_data`). Key removal through merge is not checked in the SDK; if merge cannot delete, say so in the doc line.
- mods/sf3_chance/src/sf3_host.rs:20: medium: everything takes a dimension `&str` and resolves it with `host.level(dim)`, but several hooks hand a `LevelRef` (`level_tick_post`, which the high fix above needs) or a `LevelDimension` (`BlockClick.dimension`). There is no `LevelRef -> &str` helper and no `LevelRef`-taking variant, so bundles will call host methods directly or convert by hand. Fix: add `level_name(host, LevelRef) -> String` (or make the functions take `LevelRef`) before the next bundle.
- mods/sf3_chance/src/lib.rs:52: low: building NBT (`tags`, `entity_nbt`) uses `Compound` as a `BTreeMap` with `.into()` keys in mod code. The same `JavaString` gap `nbt_get` works around applies to writes. Fix: move `tags` into `sf3_host` as `compound(&[(&str, Tag)])` next to `nbt_get`, so a change to the key type touches one file.
- mods/sf3_chance/src/sf3_host.rs:38: low: `set_block` takes only a block id (default state, fixed flags 3). The bundles use `native_block_property` and `native_set_block_property` 80 times. Fix: add `block_property`, `set_block_property`, and a `set_block` that takes flags, when the first bundle needs them.
- mods/sf3_chance/src/sf3_host.rs:76: low: `main_hand` only. `right_click_block` is per hand, so bundles will need `hand_item(host, player, Hand)`.
- mods/sf3_chance/src/sf3_host.rs:81: low: every write returns `bool` and drops the refusal (`PlayerDataRefusal`, `BlockEntityError`, `TextFormError`), and there is no log helper. Debugging 19 bundles in play will need the reason. Fix: one `log` helper, and log the `Err` inside each wrapper before turning it into `false`.
- Missing, by call counts across `native/*/mixins/*/*.rs` (expected in later bundles, not needed here): sneaking (69), carried stack (71), action bar (54 + 17 client), the online players (45), redstone signal (44 + 22), block entity sync (26), container slots and item insertion (26 + 26), item entities (24 + 22), entity hurt (25), level random (21).
- Naming and thinness: each function is one host call or a short chain, named after what it does. The SDK value types it returns (`ItemStack`, `PlayerRef`, `Compound`, `Tag`, `GameMode`, `BlockState`) are allowed by the design rule. Wrapping them would cost more than it saves.

## 4. `sf3_host` as a library mod

Yes. Make `sf3_host` a library mod once two converted mods use it, and prove it with a two-mod `native-build` before the
other bundles convert.

- `concepts/dependencies.md:3-4`: "A mod can publish functions and statics from its root crate for another mod to call. Declare dependencies in `horizon-mod.toml`". `sf3_host` is stateless public functions, which is exactly this.
- `:31-32`: the launcher adds the path dependency itself, so the "paths escaping the mod" refusal (`how-to/native-mods/01-the-mods-crate.md:43-45`) that drove the copy design does not apply.
- `how-to/wasm-mods.md:102-107` (native rules are the same): "Ordinary Rust calls such as `my_library::function()`, statics, generics and owned Rust types need no generated interface", so the generic `nbt_get` works across the boundary.

Limits:

- `:14-15`: "Code dependencies additionally require API packages for the dependent and every installed dependency". `sf3_host` becomes an installed mod with its own `horizon-mod.toml`, version and Mods row, and `side = "both"`.
- `:27`: "A code dependency still links dependency-first or is refused by name".
- `reference/sdk/04-fit.md:27`: a mod whose library does not fit a build is left out. One `sf3_host` that fails to compile drops all 20 bundles at once, where copies fail one by one.
- `:43`: "Do not define these dependencies or features yourself in `Cargo.toml`". So whether a plain `cargo check` or `cargo test` inside a dependent resolves `sf3_host` without the launcher's staging is not checked. That is the main cost to the edit-test loop.
- `mods/sf3_chance/horizon-mod.toml` records that launcher 0.2.93 answered "requires missing mod" for a dependency on a content mod. Whether native-to-native code dependencies work on the installed launcher is not checked.
- A dependency adds dispatch ordering (`:47`). That is harmless here, because the library has no hooks.

Until that proof, the byte-identical copy plus the `fc /b` acceptance check is a working fallback.

## Verdict

Port is faithful for the overworld single-player paths already played. One high risk: delayed world-changing steps run
from `server_tick`, where the level in place is undefined, so Nether and End rewards (and a guest in another level) are
likely to fail silently. Move job execution to `level_tick_post`. Two medium items:

- the client-side `Pass` lets the off hand act after a Scanner click;
- `sf3_host` lacks a read-modify-write for block entities and a `LevelRef` entry, and both are needed before the next
  bundle.

The rest is low.
