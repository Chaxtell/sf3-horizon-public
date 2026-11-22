# Migration plan: SF3 on Horizon's stable mod API (draft for review, 2026-11-20)

Status: **reviewed with the user 2026-11-20; Phase 0 (fact-finding, no bundle code changes) started.** Phase 1
waits for review point A.

## Goal

A fully working SkyFactory 3 modpack that installs and plays in the current Horizon launcher, built so that
future Horizon updates cost a small repin instead of a rewrite.

## Why we broke, and the rule that prevents it

All 20 bundles patch the engine's internal functions (old `horizon-mixin.toml` format, 457 attach points, about
3,400 engine calls). Horizon retired that format and moved the files. Horizon's docs say internal patches carry
no promise across updates; the stable route is `mod_api::Hooks`, Parts, Capabilities and Attachments.

Rules for everything we write from now on:

1. **Stable API first.** A hook, Part, Capability or Attachment whenever one exists.
2. **One adapter crate (`sf3_host`).** Bundles never call the engine directly; they call our thin adapter, which
   calls Horizon. An upstream rename is then fixed in one file, not 3,400 call sites.
3. **Native patches are the exception, and each is tracked.** Every remaining `[[native.mixin]]` row goes in a
   ledger with the reason and the upstream issue asking for a stable hook.
4. **Logic stays engine-free.** Each bundle's `runtime.rs` (pure rules, unit-tested) is kept as is; only the
   `glue.rs` layer is rewritten. Glue gets tests on Horizon's `FakeHost`.
5. **Small, frequent repins.** A scheduled "canary" moves the pin to the newest Nightly, builds and runs tests,
   so breakage shows up one week at a time.

## What is known and what is not

Known (survey `docs/specs/stable_api_fit_2026-11-20.md`): about 75% of attach points have a stable hook by name;
machines' storage maps to Capabilities (`ITEMS`, fluids, energy) and `BlockEntityPart`; Horizon ships a
`FakeHost` for tests, a `.hpack` modpack format, and `cargo horizon-mod` / `horizon-launcher native-build`.

Not known yet (Phase 0 answers these): whether signatures and behaviour match, not just names; how our
machines' saved data maps to block-entity data or Attachments; whether our custom screens and menus have
stable routes; whether the 71 content mods (`.hmod` data) still pass the new tool's checks; whether the Windows
native build works end to end here; host flight on the new engine.

## Roles

- **Claude (this session):** planner and integrator. Writes briefs, runs every gate and build itself, play-tests in
  game, reviews diffs, keeps the board. Never trusts an agent's own "done".
- **Opus agents:** design and judgement: the API mapping, the adapter and machine framework design, the hard
  bundles, and code review of each converted bundle.
- **Sonnet agents:** conversion work per bundle against a fixed recipe, tests, data checks.

## Phases

### Phase 0: Ground truth (no bundle code changes)

| # | Task | Who | Done when |
|---|---|---|---|
| 0.1 | Tooling: current launcher, an SF3 test instance, `cargo horizon-mod` at the current Nightly; build and run the official native template mod on this PC | Claude | template mod runs in the launcher |
| 0.2 | Content check: build and `check` all 71 content mods with the new tool; list schema breaks | Sonnet | report: pass/fail per mod |
| 0.3 | API mapping: every one of our 118 hooks and 184 engine calls -> stable hook / host method / Part / Capability, with signature differences, or "none" | Opus | `docs/specs/api_map.md`, reviewed by Claude against source |
| 0.4 | Data design: machines' saved data, menus, screens, energy/fluid/item storage on the stable API | Opus | design note with one worked example |
| 0.5 | Gap list: what has no stable route; file upstream issues (drafts already in `docs/upstream_requests/`), re-test host flight | Claude | ledger started |

**Review point A (user):** mapping coverage and the real gaps. Go / no-go for the pilot.

### Phase 1: Pilot (one small bundle, end to end)

| # | Task | Who | Done when |
|---|---|---|---|
| 1.1 | `sf3_host` adapter crate, only what the pilot needs | Opus designs, Sonnet builds | unit tests on `FakeHost` |
| 1.2 | Convert `21_sf3_chance` (8 attach points, 32 calls) to a flat native mod using hooks + adapter | Sonnet | builds with `native-build`, old `runtime.rs` tests pass |
| 1.3 | Review | Opus | findings fixed |
| 1.4 | Play-test in the new launcher against the bundle's `PLAYTEST_LOG` entries | Claude | same results as before |
| 1.5 | Write the conversion recipe and measure cost (agent time per attach point) | Claude | recipe + estimate for the rest |

**Review point B (user):** pilot result, cost estimate, go / no-go for the full migration.

### Phase 2: Shared foundations

| # | Task | Who |
|---|---|---|
| 2.1 | Grow `sf3_host` to the full mapping (grouped: world, players, items, entities, messages) | Sonnet, Opus review |
| 2.2 | Machine framework: one `BlockEntityPart` + Capabilities pattern for items / fluids / energy, with saved data | Opus designs, Sonnet builds |
| 2.3 | Menu and screen pattern (machine menus, `/baubles`, JEI-style lists) | Opus |
| 2.4 | Convert one machine bundle as the framework's proof: `12_sf3_envtech` | Sonnet, Claude plays |

### Phase 3: Bundle waves (one Sonnet agent per bundle, disjoint folders, 2-3 at a time)

Each bundle: convert glue -> keep `runtime.rs` tests -> add `FakeHost` tests -> Claude runs build and gates ->
Opus review -> Claude play-tests from that bundle's `PLAYTEST_LOG` entries -> ledger updated.

- **Wave A (small):** 20 charset, 01 skyblock, 02 exnihilo, 03 storage_qol, 19 player, 15 logistics
- **Wave B (medium):** 14 tinkers, 06 endgame, 13 draconic, 11 rftools, 17 xutils, 16 utility
- **Wave C (heavy, Opus-led):** 05 farming, 09 botania, 10 bloodmagic, 08 immersive, 04 tech_power
- **Wave D (special):** 07 jei and the 10 draw/tooltip patches (stay native mixins unless a stable route exists)

### Phase 4: Pack assembly and acceptance

| # | Task | Who |
|---|---|---|
| 4.1 | `.hpack` manifest: all content mods + native mods, load order, dependencies | Sonnet |
| 4.2 | Install into a fresh launcher instance; new-world smoke test | Claude |
| 4.3 | Progression playthrough by stage (the coverage doc's 106 builds as the checklist) | Claude |
| 4.4 | Fix round | Sonnet / Opus as needed |

### Phase 5: Keep it working

| # | Task | Who |
|---|---|---|
| 5.1 | Weekly canary: repin to newest Nightly, build, run tests, report | scheduled, Claude reviews |
| 5.2 | Native-patch ledger with upstream issue links; remove a patch when its hook lands | Claude |
| 5.3 | Update `CLAUDE.md`, `MASS_PORT_PLAN.md` and build tools to the new layout; retire `tools/native_win.py` | Claude |

## Safety during the migration

- The old build (pin `04a26210e3`, `native/`) stays untouched and playable until the new pack passes Phase 4.
  New mods go in a new folder (`mods/`), so nothing is overwritten.
- Old and new mods cannot run in the same game (different engine versions), so the new pack is tested in its own
  instance and world.
- No commits unless the user says so (current rule).

## User answers (2026-11-20)

1. **Worlds:** old-build worlds not carrying over is fine.
2. **Feature freeze:** yes, new SF3 feature work is paused during the migration.
3. **Pace:** at most 3 agents at once.
4. **Upstream issues:** open. The four drafts in `docs/upstream_requests/` stay unposted until the user decides.

## Phase 0 results (2026-11-20), for review point A

Reports: `api_map.md` (0.3), `stable_api_data_design.md` (0.4), `content_mods_check_2026-11-20.md` (0.2). Claude
spot-checked API names in each against Horizon source; the reports' own "not checked" rows stand.

- **Mapping, checked against source (replaces the survey's 75% name match):** of 457 attach points, 169 are the
  same, 245 exist with a different shape, 43 have no stable route. Of 3,384 engine call sites, 584 are the same or
  renamed, 2,769 have a different shape, 31 have none. So every `glue.rs` is rewritten, not renamed.
- **Two shape changes carry most of it:** block-entity data access (475 calls; handle plus read/write methods
  instead of one closure) and the "acting player" calls (about 520; the player now comes from the hook). Both can
  be hidden in `sf3_host`, which makes rule 2 the main cost saver.
- **No stable route:** JEI (recipe categories, 8 draw mixins, Mods list), world generation (01 void world and
  island, 13 Chaos Islands), menus with input slots (15, 17, 19), the client action bar (12 bundles).
- **Data model:** unchanged in substance (`nbt`, `items`, `data` on a block entity; Capabilities take the structs we
  already fill; Attachments for player data).
- **Rule 4 weakened:** `FakeHost` cannot simulate time, weather, light, redstone or block-entity reads. Glue tests
  cover item and energy moves only; machine ticks are verified in play.
- **Content mods:** 118 (not 71). 105 pass on main; 13 fail on two key changes (`place_block` -> `block`, 145
  files, one script; fluid keys, 64 files, per-mod choice in 6 mods).
- **Tooling (0.1), partly done:** main's `cargo horizon-mod` built into `C:\Users\chaxt\.sf3-tools\main`; the official
  native template creates, compiles and passes `check` here. Not done: `native-build` and running in game, which
  need launcher 0.2.92 (installed: 0.2.69). Launcher update waits for the user.
- **Plan changes proposed:** pilot stays `21_sf3_chance`. Add to Phase 0.5 the ledger entries above. Wave D grows:
  01's world generation and the input-slot menus join JEI as "native mixin or upstream request".

## Phase 0.1 closed, Phase 1 tooling notes (2026-11-20)

- Launcher updated 0.2.69 -> 0.2.93 (user approved). The update deleted `versions/nightly-2026-11-08-fdc87ae`;
  restored from `C:\Users\chaxt\.sf3-tools\backup\` (31,542 files, counts match). Keep that backup.
- New test instance `SF3 Pilot` on `nightly-2026-11-20-0a875da`. `horizon-launcher native-build <folder> --instance
  "SF3 Pilot" --version nightly-2026-11-20-0a875da --trust-native-code` built the official template mod in 41 s
  (the game is prebuilt; only mods compile). In world `PilotTest` the mod's join greeting appeared in chat: a
  stable-API native mod builds and runs on this PC.
- Before the first build: `horizon-launcher prepare --version nightly-2026-11-20-0a875da`.
- Game control for the new engine: `py C:\Users\chaxt\.sf3-tools\bin\hz.py <tool> '<json>' [timeout]` calls one tool
  of the new launcher's MCP server (`play`, `game_wait_ready`, `game_messages`, `game_command`, `game_quit`...).
  The session's own `horizon` MCP connection still runs the old launcher process and refuses the new version.
- Mod tool for main: `C:\Users\chaxt\.sf3-tools\main\bin` first on PATH; `check` needs rustup target
  `wasm32-unknown-unknown` (installed).

## Phase 1 pilot result (2026-11-20), for review point B

`21_sf3_chance` runs on the stable API in the new launcher: `mods/sf3_chance/` (flat native mod; `runtime.rs`
byte-identical to the old one, 28 tests pass) plus the content mod `chancecubes` as a `.hmod`. Design and step
list: `pilot_chance_design.md`. Code review: `pilot_chance_review.md` (pending when this was written).

Played in instance `SF3 Pilot`, world `PilotTest`, engine `nightly-2026-11-20-0a875da`: cube placed with block entity
`sf3_chance:cube`; Scanner read the same chance twice (64) and another cube's (-79); Silk Touch Pendant break
dropped the cube with no reward; empty-hand survival breaks ran Roosevelt's_Stick (item), Book_Of_Memes (delayed
chat), Cats_And_Dogs (3 cats found; no wolf found, not followed up) and one more. No error line in the log.
Not played: creative breaks, giant cubes, a second player, relog with queued rewards.

Found on the way (add to the conversion recipe):
- A content `.hmod` copied into the instance's `horizon-mods/` is ignored until `mod.<id>:true` is in
  `horizon-mods.txt`. Without it the native mod crashed the game at start ("is not a block").
- `[dependencies] chancecubes = "^0.1"` in the native mod makes launcher 0.2.93's `native-build` fail with
  "requires missing mod", even with the content mod enabled. Left out; noted in the manifest.
- A world saved with a mod that is later removed opens only after a confirm dialog.
- `cargo horizon-mod check` warns about "built field by field" on our own enum patterns; false alarm.

### Cost figure

One data point, the smallest bundle (8 attach points, 32 engine calls, 333 lines of glue):

| Step | Who | Cost |
|---|---|---|
| Design + full conversion + adapter (25 functions), compile-checked | Opus agent | 298k tokens, 19 min |
| Code review | Opus agent | see review file |
| Install, launcher build (22 s), play-test, two launch fixes | Claude | about 35 tool calls |

That is about 37k agent tokens per attach point and 9k per engine call. Scaled plainly to all 20 bundles (457
attach points, 3,384 calls): 17M to 31M agent tokens and about 18 agent-hours of conversion, so 6 to 8 hours of
wall time at 3 agents, plus Claude's build and play-test per bundle (the larger share of wall time: 20 bundles,
106 builds in the coverage checklist).

Why the real number can be lower: the pilot paid for the layout, the adapter and API discovery once; the two big
shape changes (block-entity data, acting player) get solved once in `sf3_host`. Why it can be higher: the pilot
has no machine, no menu, no screen and no capability; bundles 04, 07, 09 and 10 do, and 43 attach points have no
stable route. Phase 2 (machine framework proved on `12_sf3_envtech`) is the next measurement and the one that
decides the heavy bundles' cost.

### Pilot code review (Opus, 166k tokens, 7 min): `pilot_chance_review.md`

18 findings: 1 high, 4 medium, 13 low. None fixed yet; they are the first Phase 2 tasks because most change
`sf3_host`'s shape.

- **High:** delayed reward steps run from `server_tick`, where the SDK does not define which level is in place;
  mob, entity and block steps for a cube broken outside the overworld are likely to fail silently (overworld
  worked in play; other dimensions not played). Fix: run due jobs from `level_tick_post` per level.
- **Medium:** client side returns Continue, so the off hand still acts after a Scanner click; `sf3_host` lacks a
  block-entity read-modify-write (the old call is used 369 times across bundles) and a level handle; NBT for
  summons is built in `lib.rs` instead of the adapter.
- **`sf3_host` as a real library mod:** allowed by the docs (`concepts/dependencies.md`), but one compile failure
  would drop all 20 dependents, and native-to-native dependencies are unproven on launcher 0.2.93 (a content-mod
  dependency already failed there). Keep identical copies until two mods prove it.
- The design's two `FakeHost` glue tests were not carried into `mods/sf3_chance`; only the 28 runtime tests run.

Pilot total agent cost with review: 464k tokens, 26 min.

## Phase 2 notes (2026-11-20)

- **Content on main:** `py -I tools/content_for_main.py` copies each content mod outside the repo, rewrites
  `place_block` -> `block` and fluid files to `{"sprite": ...}`, builds with main's tool: 118 of 118 pass
  (`docs/specs/content_for_main.md`). `content/` itself stays in the old format for the old build. Smoke test: all
  118 `.hmod` enabled in instance `SF3 Pilot` with `sf3_chance`; the world opened. Log errors: only unresolved
  recipe tags (`#sf3:ore/substance_ebony`, `substance_ivory`, `particle_customizer`, `slimeball_*`, `cast`,
  `#extrautils2:angelring`). Not checked: whether the old build logs the same, fluid behaviour in game.
- Old build re-launched after the folder restore: world `Island1118` opens, commands run.
  The unresolved tags have no tag file in `content/sf3_content/data/sf3/tags/` (checked `substance_ebony`): a content gap that predates the migration, not a format break.
- **Pilot review fixes (Opus, 158k tokens, 8 min):** delayed jobs run from `level_tick_post` per level; client
  cancels a main-hand Scanner click; `sf3_host` gained `be_update`, `level_name`, `compound`; 31 tests (3 on
  `FakeHost`). Claude re-ran the gates and built with the launcher (19 s). Played in the Nether, survival: 7 cube
  breaks ran Fighter, Thrown_In_Air, Redstone_Diamond, Pig_Of_Destiny, Tnt_Structure; one non-player entity was
  present afterwards. Not isolated: which of those used a Mob/Block step rather than a command. Not played: the
  End, off-hand torch while scanning, a second player.
- **Menus and screens (Opus, 248k tokens, 12 min): `stable_menus_screens.md`.** All six patterns compile in a
  scratch mod. Machine menus, item tooltips, the action bar and the JEI screen pieces have stable routes (the
  earlier map was too strict). No clean route: `/baubles` and 06's wireless grid (slots cannot be backed by storage
  a mod keeps; stand-in: a chest menu our code syncs to a player attachment; upstream issue drafted in the spec),
  and 15's Ender Pouch (per-frequency storage cannot roll back in a transaction: duplication risk). The 19
  Options > Mods rows are dropped. Not checked: slot backing for the single-player host, JEI recipe categories.
- Game control helper: `. C:/Users/chaxt/.sf3-tools/bin/h.sh; h <tool> '<json>' [chars] [timeout]`. Teleport into a
  new dimension, then `game_wait_ready`, then build the floor: a `fill` before the chunks load fails silently and
  the player falls.

## Phase 2 result: machine framework proved on `12_sf3_envtech` (2026-11-20)

`mods/sf3_envtech` (Opus, 312k tokens, 21 min; 14 attach points, 968 lines of old glue -> 1,024 lines of `lib.rs`;
`runtime.rs` byte-identical; 26 tests, 6 on `FakeHost`). `sf3_host` grew by 23 functions to 342 lines. Notes:
`envtech_conversion.md` (24-item play checklist), `sf3_host_api.md`. Claude re-ran the gates and built both mods
with `horizon-launcher native-build mods` (a folder build replaces the instance's whole native set, so all our
mods are always built together from `mods/`; `mods/sf3_host/` holding only a `.rs` file is skipped without error).

Played in `SF3 Pilot` (checklist numbers): 1 block entity with its ints; 2 Assembler placed 29 parts, "Solar Array
T1 is complete", cells 9; 3 energy reached 6480 at noon; 4 a Launcher west of the controller filled while the
controller stayed at 0; 8 Void Ore Miner T1: Assembler placed 47 parts, with 1,000,000 RF and an open column it
mined coal ore in 400 ticks for about 320,000 RF; 13 a solid column gave `see` 0; 9 an empty-hand click opened the
slot menu and a chest on top received coal ore and `immersiveengineering:ore_aluminum`; 14 Launcher at `up` 7 sent
a pig from y 154 to above y 405 within 40 ticks (old record: about y 260; height difference not followed up).
Not played: 5-7, 10-12, 15-24 (piezo, redstone, Lightning Rod, lenses and modifiers, Resource Miner, Beacon and
its flight, Lunar Panel, Digital Guide, shared structure blocks).

Also settled the same day:
- **A native mod can call another native mod.** Two test mods (`C:\Users\chaxt\.sf3-tools\deptest`): `dep_b` with
  `[dependencies] dep_a = "^0.1"` called `dep_a::greeting`; the launcher built both and the line showed in chat.
  So `sf3_host` can become a real library mod, and `sf3_jei` can publish `register_category`. Not done yet:
  the copies stay until Wave A is in, then one change converts all mods.
- **JEI (Opus, 217k tokens): `jei_stable_route.md`.** The engine draws the item panel, search and the "+" button;
  we write the recipe index and recipe screen in `mods/sf3_jei` (about 3,200 lines against 7,421) with no mixins;
  each machine mod registers its own tabs. No route: engine-drawn recipe pages, creative-tab contents, brewing
  recipes (degrade), JEI config screen (drop).
- **World generation (Opus, 264k tokens): `worldgen_stable_route.md`.** Stable routes for all of it: mod chunk
  generators for the void Overworld, Nether and End; a world preset as Create World's default;
  `create_spawn_position`; Chaos Islands as mod structure types. Gap: a dedicated server cannot name a mod preset
  (upstream request drafted). Hand-written `[[native.mixin]]` rows are unproven with the current tool.

### Cost so far (agent tokens, agent minutes)

| Work | Tokens | Minutes |
|---|---|---|
| Pilot: design + conversion, review, fixes | 622k | 34 |
| envtech conversion + adapter growth | 312k | 21 |
| Design research (data, menus, JEI, worldgen, API map) | about 1.2M | 79 |
| Content check + build script | 221k | 17 |

Per unit after two bundles: 37k tokens per attach point on the pilot, 22k on envtech (14 points), with the adapter
growing each time. Revised whole-migration estimate: 20 bundles, 457 attach points at 20k to 35k each = 9M to 16M
tokens of conversion, plus about the same again for reviews and fix rounds; conversion agent time 10 to 15 hours,
3 at a time.

## Phase 3, Wave A (2026-11-20, in progress)

Sonnet, one agent per bundle, from `conversion_recipe.md`. Claude re-ran tests and `cmp` on each and builds all
finished mods together with `sh C:/Users/chaxt/.sf3-tools/bin/stage.sh <mods...>` (copies them to a clean folder,
so half-written mods of running agents stay out of the build).

| Bundle | Tokens | Min | Tests | Note | Played |
|---|---|---|---|---|---|
| 20 charset | 256k | 8 | 22 | `conv_charset.md` (13 checks) | crate block entity keeps items, menu opens |
| 02 exnihilo | 257k | 8 | 33 | `conv_exnihilo.md` (10 checks) | sieve takes mesh and gravel, 12 clicks empty it; **no drop seen in one run: re-test** |
| 01 skyblock | 269k | 10 | 47 | `conv_skyblock.md` (13 checks) | see below |

Skyblock played (world `SkyVoid`): world type "SkyFactory Void" gives void Overworld and Nether, spawn on the tree
at 0.5 71 0.5, kit in the inventory (coffee, toast, iron nugget, stick, torch, book). **Not the default:** Create
World opens on "Default" and the launcher's quick world create (`play --world NAME`) makes a normal world; the
preset must be picked by hand (fifth in the cycle). To fix in the tag or by an upstream request. Not played: the
End, island contents, Twerk, Veinminer, challenge book, Achievement Stand, Void Cup.

Sonnet cost: about 260k tokens and 8 to 10 minutes per small bundle (400 to 1,000 lines of old glue), close to
Opus's cost on envtech. Running: 03 storage_qol, 19 player, 15 logistics.
| 19 player | 311k | 12 | 30 | `conv_player.md` (12 checks) | played 2026-11-21: 7, 9-12 pass, 8 engine gap (`/kill` no `living_drops`), 1-6 not ticked one by one |

Open cross-mod point from 19: worn accessories now live in the player Attachment `sf3_player:baubles`; other bundles that read the old `sf3_baubles` data (worn rings, cloaks, laurel) must read that Attachment, which needs the shared library mod.
| 03 storage_qol | 381k | 16 | 68 | `conv_storage_qol.md` (14 checks) | after Claude's fix: drawer took cobblestone (Count 80), Cobble Gen made 11 in 200 ticks |
| 15 logistics | 463k | 20 | 48 | `conv_logistics.md` (20 checks) | not played yet |

Wave A is converted (6 bundles, 1.94M tokens, 74 agent minutes). Seven mods build and start together in `SkyVoid`.
`/baubles` opens its chest-style menu (worn effects not played).
Found in play: `sf3_storage_qol` crashed the game at start ("Mod parts refused: ... attached twice", 254 blocks):
a block entity Part is also the block Part, so the extra `r.block_part` call was a duplicate. Claude fixed
`lib.rs` (skip blocks that have an entity type) and added the trap to the recipe.
Running: 14 tinkers, 06 endgame, 13 draconic (Sonnet). Then: merge `host_ext.rs` files into `sf3_host` and turn it
into a library mod (Opus), which also carries the shared accessory Attachment.

## Phase 3, Wave B (2026-11-20, in progress)

| Bundle | Tokens | Min | Tests | Note | State |
|---|---|---|---|---|---|
| 14 tinkers | 393k | 17 | 85 | `conv_tinkers.md` (16 checks) | builds and starts with the others; not played |
| 06 endgame | 530k | 23 | 102 | `conv_endgame.md` (13 checks) | builds and starts with the others; not played |
| 13 draconic | 474k | 18 | 40 | `conv_draconic.md` (14 checks) | gates pass; not built with the others yet |
| 11 rftools | 326k | 14 | 78 (+1 skipped) | `conv_rftools.md` (13 checks) | **partly converted** (about 40%); second worker finishing it |

Running: 17 xutils, 16 utility, 11 rftools part 2.

- `sf3_logistics` had the same "attached twice" start crash as storage_qol; Claude removed the extra `r.block_part`.
  Ten mods then started together in `SkyVoid`.
- Sieve drops re-tested in survival: 3 gravel gave item entities on the sieve (`exnihiloadscensio:ore_copper_piece`
  x3). The earlier "no drop" was the test reading the inventory from out of pickup range. Pass.
- rftools decision: its runtime test `the_slot_rule_module_ids_match_the_runtime_tables` reads the old bundle's
  `slots.rs`, which cannot live in the new mod. `runtime.rs` stays byte-identical; the gate runs with
  `cargo test -- --skip the_slot_rule_module_ids_match_the_runtime_tables`.
| 11 rftools part 2 | 363k | 15 | 83 (+1 skipped) | `conv_rftools.md` (26 checks) | all but Screens, Screen Controller and screen modules (need a block-entity text renderer) |
| 17 xutils | 435k | 15 | 124 | `conv_xutils.md` (13 checks) | starts with the others after Claude's fix |
| 16 utility | 443k | 17 | 66 | `conv_utility.md` (14 checks) | starts with the others |

Wave B is converted (2.97M tokens, 119 agent minutes for six bundles). Wave C so far:

| Bundle | Tokens | Min | Tests | Note | State |
|---|---|---|---|---|---|
| 08 immersive | 427k | 15 | 93 | `conv_immersive.md` (14 checks) | starts with the others; wires drawn through the stable `submit_custom_geometry` (not seen in play) |

Fifteen mods build (launcher: about 13 s) and start together in `SkyVoid` with no error line. Running: 05 farming,
09 botania, 10 bloodmagic (Sonnet). Left: 04 tech_power (8,331-line `glue.rs`: Opus writes a split plan and the
shared skeleton, then workers take disjoint feature files), 07 jei, rftools Screens.

- `sf3_xutils` stopped the game at start: its block entity type named `extrautils2:passivegenerator_creative`,
  which `content/extrautils2` does not have. Claude removed it and wrote `tools/mods_ids_check.py` (lists content ids
  named in `mods/*/src` that no content mod defines; ids built from a prefix at run time and component ids such as
  `sf3:energy` are false alarms). Later briefs tell workers to run it.
- Not a crash, only warnings: `sf3_utility`'s Block Dispenser Part attaches to blocks that sit in two tags.
| 09 botania | 483k | 20 | 81 | `conv_botania.md` (14 checks) | starts with the others (16 mods); chat-driven Corporea is back beside `/corporea` |
| 05 farming part 1 | 351k | 14 | 144 | `conv_farming.md` (13 checks) | chickens, crops, armour; part 2 running (machines, cooking, trees, tools) |
| 10 bloodmagic part 1 | 433k | 16 | 114 | `conv_bloodmagic.md` (13 checks) | altar, network, sigils, rituals, forge; part 2 running (Roots, Alchemy Array, Demon Will, Living Armour) |

Running: 05 part 2, 10 part 2 (Sonnet), 04 split plan and frame (Opus).
| 05 farming parts 2 and 3 | 375k + 337k | 14 + 14 | 166 | `conv_farming.md` (30 checks) | all converted but recipe viewer tabs; started with the others after part 2 |
| 10 bloodmagic part 2 | 454k | 16 | 119 | `conv_bloodmagic.md` (20 checks) | all converted but recipe viewer entries; Living Armour death guard carried over (`living.rs`); starts with the others |
| 04 tech_power plan + frame (Opus) | 352k | 18 | 398 | `conv_tech_power_plan.md` | six packages, one file each; `machines` done (349k, 9 min, 403 tests), `reactors`, `aa_tech`, `aa_world` running; `eio`, `mob_flux` next |

A world saved with a mod that the next build leaves out opens on a confirm dialog, and `game_wait_ready` then
waits forever at the title: read `game_ui` when a start seems to hang.

## State at 2026-11-21 (user: slow down, usage limits; one agent at a time from here)

All 20 bundles are converted to `mods/` (tests and `cmp` re-run by Claude on each; tech_power: 431 tests, six
package files; rftools Screens done through the stable `block_entity_submit`; `mods/sf3_jei`: 22 tests, client-only,
public `register_category`). All 20 mods built together and started in `SkyVoid` with no error line (build before
the JEI wiring pilot).

Played so far beyond start-up: chance, envtech (8 of 24), skyblock void world and kit, crate, sieve and its
drops, drawer, Cobble Gen, `/baubles` menu opens, Blood Altar status line, Botania pool infusion (iron ingot ->
Manasteel for 3000 mana, only when the item is inside the block: the pool block is a full cube in content, so a
dropped item rests on top; content gap, same in the old build).

Open, in order:
1. ~~JEI wiring~~ **done 2026-11-21:** `src/jei.rs` in the six mods that have viewer tables (immersive, exnihilo,
   farming, tech_power, botania, bloodmagic); all 20 build (`native-0a875da-1773efd78f1a`). Seen in game (survival
   inventory, U over an item): Coke Oven tab with 3 recipes, Ex Nihilo hammer tab, Blood Altar tab, Pure Daisy tab.
   Not looked at: farming and tech_power tabs one by one. The viewer's U/R keys do nothing in the creative inventory.
   Crash found and fixed the same day: `eprintln!` in `sf3_player` (`living_drops`) panicked with stderr closed and
   stopped the server; `sf3_player` and `sf3_draconic` now log through a `log!` macro that ignores the error.
2. Play pass: about 350 checklist items in the `conv_*.md` notes and `conv_tech_power_plan.md`. Each note gets a
   "Played" section; `conv_exnihilo.md`, `conv_skyblock.md` and `conv_storage_qol.md` played 2026-11-21; `conv_bloodmagic.md` played 2026-11-21 (items 13-20 this round; Repulsor and armour tooltip not played) (skyblock: stand fix; items 1, 2, 5, 13 need a new world; storage_qol: items 3, 4, 6, 8, 12, 13 not played); `conv_tech_power_plan.md` machines items 1-5, 9 and reactors items 7, 9 played 2026-11-21 (machines 6-8 and the other reactors items not played); `conv_farming.md` items 1-3, 9-12, 23, 24, 28 played 2026-11-21 (the rest not played); `conv_botania.md` all 14 items played 2026-11-21 (holy cloak and brew drink fixed; tornado rod and pool-top infusion bugs open); `conv_charset.md` items 1, 3-8, 10-13 played 2026-11-21 (gate chain conducted through the gate block, fixed; items 2, 9 and five gate kinds not played).; `conv_player.md` items 7, 9-12 played 2026-11-21 (8 waits on engine `living_drops` on `/kill`; 1-6 not ticked one by one).
3. Void world type is not the default; hopper/pipe item filter has no stable hook (one upstream request covers
   7 bundles); pending upstream drafts in `stable_menus_screens.md`, `jei_stable_route.md`, `worldgen_stable_route.md`.
4. Adapter merge (`host_ext.rs` files -> `sf3_host` library mod): deferred until after the play pass; the copies
   work, the merge is upkeep (decision logged).
5. Phase 4: `.hpack`, fresh instance, progression playthrough.

Agent cost so far: about 19M tokens.
