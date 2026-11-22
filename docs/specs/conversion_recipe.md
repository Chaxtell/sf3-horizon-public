# Conversion recipe: one old bundle -> one stable-API native mod (2026-11-20)

For the worker converting `native/NN_sf3_<name>` into `mods/sf3_<name>`. Two finished examples to copy from:
`mods/sf3_chance` (small, items and a block entity) and `mods/sf3_envtech` (machines, energy, item slots, menus).
Their notes: `pilot_chance_design.md`, `pilot_chance_review.md`, `envtech_conversion.md`. Maps: `api_map.md` (old hook
and engine call -> stable API), `sf3_host_api.md` (our adapter), `stable_api_data_design.md`,
`stable_menus_screens.md`, `worldgen_stable_route.md`, `jei_stable_route.md`. All in `docs/specs/`.

## Tools

- Put `C:\Users\chaxt\.sf3-tools\main\bin` first on PATH. Gates, run inside the mod folder: `cargo check`,
  `cargo test`, `cargo horizon-mod check`. The SDK (build 0a875da) lands in `.horizon/sdk` on the first
  `cargo horizon-mod` command; read its source there. `cargo horizon-mod hooks <text>` searches hooks.
- Engine docs: `D:\ClaudeProjects\horizon-workspace\horizon\docs\modding\src`.
- Workers do not run the launcher or the game. Claude builds and plays.

## Layout (copy `mods/sf3_envtech`)

```
mods/sf3_<name>/horizon-mod.toml   id sf3_<name>; same [native] pins as sf3_envtech; needed content mods in a comment
mods/sf3_<name>/Cargo.toml
mods/sf3_<name>/src/lib.rs         the Hooks impl and Parts; split into more files when long
mods/sf3_<name>/src/runtime.rs     byte-identical copy of the old runtime.rs (cmp it)
mods/sf3_<name>/src/sf3_host.rs    byte-identical copy of mods/sf3_host/sf3_host.rs (cmp it); do not edit
mods/sf3_<name>/src/host_ext.rs    new adapter functions this bundle needs (see rule 2)
mods/sf3_<name>/src/glue_tests.rs  FakeHost tests
```

## Rules

1. `runtime.rs` is not edited. All game rules stay there with their tests. If the old bundle has other rule files
   beside `runtime.rs`, copy them unchanged too.
2. Every engine call goes through the adapter. Use `sf3_host` functions where they exist. A call it lacks goes in
   your own `src/host_ext.rs` as a thin wrapper in the same style (name, one job, SDK types kept inside); never
   edit `sf3_host.rs`. Claude merges `host_ext.rs` files into `sf3_host` after the wave. The mod itself uses the
   SDK directly only to implement `Hooks` and Part traits and for event and value types.
3. Keep every feature of the old glue. Where the stable API cannot do it, pick the closest behaviour and list it.
   Drop the Options > Mods list entry (no stable route; decided).
4. Known traps:
   - A hook may now run on both client and server, and once per hand. Decide the side and the hand explicitly.
   - During `server_tick` no level is in place: per-level work runs from `level_tick_post` or the block
     entity's own tick.
   - Item and block hooks fire only for types the mod registers Parts for.
   - "Acting player" calls are gone: the player comes from the event.
   - A block entity Part is also its blocks' block Part: never also call `r.block_part` for a block that belongs to
     a block entity type you gave a Part (the game refuses to start: "attached twice"). Register each block once.
   - Do not declare content mods under `[dependencies]` (launcher 0.2.93 refuses it).
   - Never `eprintln!` or `println!` in a mod: it panics when stderr is a closed pipe and stops the server. Use the
     `log!` macro at the top of `mods/sf3_player/src/lib.rs`.
   - `data get block` shows a block entity's custom data; ints set with `data merge` are read by the mod.
5. Tests: old runtime tests keep passing; add `FakeHost` tests for glue paths `FakeHost` supports (it cannot do
   time, weather, light, redstone or block-entity reads).
6. Do not edit anything outside `mods/sf3_<name>/` and your one note file. Never `native/**`, `content/**`,
   `tools/**`, `MASS_PORT_PLAN.md`, other mods, or `..\horizon`. No state-changing git. UTF-8, LF.

## Note to write: `docs/specs/conv_<name>.md`

Hook-by-hook table (old attach point -> new hook or Part method); `host_ext.rs` functions (signature, SDK method
wrapped, old call replaced); behaviour differences; features degraded or dropped; a concrete in-game checklist
(block and item ids, commands, expected results taken from this bundle's entries in `docs/PLAYTEST_LOG.md` and
`SF3_REGISTRY.md`); "not checked".

## Done when

The three gates pass; `cmp` passes for `runtime.rs` and `sf3_host.rs`; the note is written. Paste the final line
of each command in the report. Never claim in-game behaviour.
