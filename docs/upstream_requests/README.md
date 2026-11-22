# Upstream requests for Horizon

Posted 2026-11-21, re-checked against main `73123121c7`:
- 01: https://github.com/horizon-rust/horizon/issues/19568
- 03: https://github.com/horizon-rust/horizon/issues/19569
- 04: https://github.com/horizon-rust/horizon/issues/19570 (labels `bug`, `parity` could not be added: no permission)
- 02: not posted. Main no longer has `native_menu_input_closed` (only `native_menu_closed(uuid, window)`), so the draft does not apply; redo it against main's menu hooks if still needed.

Earlier note: Checked 2026-11-20, read only. Our pinned engine is `04a26210e3` (2026-11-11); upstream main was `084ae44e40` (2026-11-20), so main has moved a lot (many files reorganised, e.g. `game/modding/`, `game/native_hooks/<hook>.rs`).

## Where to submit

**https://github.com/horizon-rust/horizon/issues** (new issue). How this was determined:
- Main `CONTRIBUTING.md` (fetched from main) says mod-related work, "the mod API, native hooks and events for mods, native mods, ... mixins", is handled in this repository. Our pinned local copy still pointed mod PRs at the fork `arismoko/horizon`; main dropped that.
- It also says ideas go to the suggestion queue (https://playhorizon.dev/hub, or `/suggest` on Discord) and issues are for bugs. In practice mod-API requests are filed as plain issues: about 220 issues titled `Mod API: ...` / `mod API: ...` / `Native mod API: ...` exist, many opened on 2026-11-20, and PRs for them land in horizon-rust/horizon (e.g. #19042 fixed by PR #19052). The fork `arismoko/horizon` (issues enabled, discussions off) holds an older set of the same kind (about 110).
- Discord: https://discord.gg/playhorizon (the contributing page's place for questions).

## Template

None. No `.github/ISSUE_TEMPLATE` in horizon-rust/horizon, in `horizon-rust/.github` (only FUNDING.yml) or in the fork; only a pull request template. Discussions are enabled on horizon-rust/horizon but nobody uses them for hook requests that I found.

## Labels

Mod-API issues are almost all unlabelled. `claimed` is added after a `/claim` comment (the contributor then opens the PR). Existing repo labels that may fit: `bug`, `enhancement`, `feature`, `parity-regression`, `from-discord`. Do not use `roadmap:*`.

## Conventions seen in example issues

- Title: `Mod API: <what, with the function name in parentheses>` or `Native mod API: ...`.
- First line, for agent-written issues: `> 🤖 Filed by <handle>'s AI agent (Claude Code, <model>), not by <handle> personally.` The drafts use a placeholder handle: fill it in (or delete the line) yourself.
- Body: Ask, Why or Use case, NeoForge counterpart, Horizon today (file:line), Proposed shape (often a Rust signature), sometimes a note that the author will open a PR and `/claim`. Mirror the existing `native_*` naming and doc style.
- Examples: horizon-rust/horizon#19042 (remove a block entity), #19001 (powder snow hook), #17200 (v4 damage hook, closest to our draft 01), #5727 (a native port's list of needed hooks); arismoko/horizon#4752, #4456, #4300 (full contract), #4821.
- Maintainers expect a requester to offer a PR; each draft is request-only. Say so if asked.

## Drafts (new issues, impact order)

| File | Title | Type |
|---|---|---|
| `01_hooks_gated_on_api_mods.md` | Chat, entity join and incoming-damage v2/v3 never run for a mixin-only mod | new issue |
| `02_menu_input_closed_host_reach.md` | native_menu_input_closed cannot reach persistent data or native_tell | new issue |
| `03_menu_slot_take_notice.md` | Mod menus: server-side take notice (menu_slot_take) | new issue, cites arismoko/horizon#4300 (closed, its PR #4465 closed unmerged) |
| `04_primed_tnt_crosshair_hitbox.md` | A player's crosshair does not pick a primed TNT | new issue |

No duplicates found for any of them in either repo (title and body searches; the search is not exhaustive).

## Claude's review note (2026-11-20)

- Host flight (gap 1) was seen failing in play on the pinned engine on 2026-11-20: a full Supremium set (bundle 05 calls `native_set_flight(uuid, true, false)` from `native_player_tick`) left `data get entity @s abilities` at `mayfly: 0b`. The source reading below says it should reach the host, so the cause is unconfirmed (engine queue path from a player hook, or our bundle). Re-test after an engine pin bump before filing; if it still fails, file it with that repro.
- Same for the level-tick host state (gap 6): in play on 2026-11-20 the worn Magnet and XP rings did nothing while they ran on the level tick, and worked once moved to `native_player_tick`. Re-test on main before filing.
- Four gaps (7, 8, 10, 12) are already on main: bumping our pinned engine is the bigger win than filing.

## Requested gaps not drafted, and why

- **1, host flight, and 6, host state on level tick:** not reproduced from source. Single player runs an integrated server and the owner is a placed hub guest (`game/integrated.rs:1-12`, `game/lan.rs:247`, `:329-336`), so `native_flight_now` (`native_travel.rs:344-358`) and `native_as_player` / `native_give_stack` / `native_give_experience` (`native_server.rs:1328`, `:1478`, `:1499`) reach the host. `HOOK_REQUESTS.md` 13 and 17 record it resolved in play on 2026-11-19. The queue branch at `native_travel.rs:337` only applies to a game with no hub. `native_clock` (`native_hooks.rs:11489`) is documented as the client window's clock, so None on the server is by design. If a fresh play-test still shows the host unable to fly, tell me and a draft can be written.
- **2-4 server side:** these are in draft 01; client chat is there too.
- **7, register a dimension:** exists on main: `host.runtime_levels()` (`game/world/runtime_levels.rs`, `docs/modding/src/how-to/world/runtime-levels.md`, arismoko/horizon#3790). Pinned engine has only `enum Dim { Overworld, Nether, End }` (`game.rs:3156-3160`). Needs an engine pin bump, not a request. Not checked: fixed ids like 66, 99, -9999 (HR 36).
- **8, spawn a projectile:** main has `spawn_projectile_from_rotation(owner: LivingRef, entity_type, stack, offset, power, inaccuracy)` (`horizon-mod-vocab/src/host/projectiles.rs:33`). Covers an owned projectile; an ownerless one at a position, and a custom boss entity (HR 25), are not checked.
- **10, enchant power above 1:** main has `native_enchant_power_bonus(state, pos, table_pos, &mut f32)` (`game/native_hooks/enchant_power_bonus.rs`). Pin bump.
- **12, cross-dimension mob teleport:** main's `entity_teleport_to_level` (`horizon-mod-vocab/src/host/entities.rs:684`) moves any entity except armor stands, falling blocks, pearls, wind charges and undisplayed kinds. Pin bump. Not checked: whether it is reachable from a mixin bundle as a `native_*` call.

## Not verified

- Main-side line numbers in draft 01 come from fetched files at `084ae44e40`; the damage v2/v3 gates were not re-read on main (v3 was split into hook files; #17200 says v3 fires on every route).
- Draft 04 was not checked against main's pick code.
- Draft 03's "no take notice on main" rests on code search plus two files read.
- The workaround lines in drafts 02 and 03 are plans or approximations, not shipped code; confirm against the bundles before posting.
