# Draft 01: new issue on horizon-rust/horizon

**Title:** `Native mods: chat, entity join and incoming-damage v2/v3 hooks never run for a mixin-only mod (gated on mods().is_empty())`

**Labels:** none needed (upstream mod-API issues carry none; `claimed` appears only after a `/claim` comment). If a label picker exists: `enhancement`, `mods`.

**Duplicate check (2026-11-20):** no open or closed issue in horizon-rust/horizon or arismoko/horizon covers it. Related and closed: horizon-rust/horizon#17200 (v4 damage hook), #14519 (per-recipient chat).

---

> 🤖 Filed by `<your GitHub handle>`'s AI agent (Claude Code), not by `<your GitHub handle>` personally.

**Ask.** A native mod that is only mixins (a `horizon-mixin.toml` bundle, no API mod) hears the same hooks as one that registers hooks. Today several dispatch sites are skipped when `mod_api::mods()` is empty, and a mixin bundle registers no API mod, so a mixin on the hook function is never reached.

**Why.** Our SkyFactory 3 port (about 20 mixin bundles) needs: player chat (Botania Corporea chat requests), `entity_join_level` (Ender IO Relocator and spawn guards), and `incoming_damage` v2/v3 (Draconic Evolution armour shield, Blood Magic Sacrifice Pack).

**NeoForge counterpart.** `ServerChatEvent`, `ClientChatReceivedEvent`, `EntityJoinLevelEvent`, `LivingIncomingDamageEvent`: all fire whatever mods are installed.

**Horizon today** (engine `04a26210e3`; the same gates are still on main `084ae44e40`, 2026-11-20, where checked):
- Server chat: `lan/hub/chat.rs:277` `if self.mods_loaded { native_player_chat ... native_player_chat_v2 ... native_chat_decorate }`; `mods_loaded` is set at `game/lan.rs:2453` and `:2804` as `!horizon_client::mod_api::mods().is_empty()`. Main: `lan/hub/chat.rs:250` `if crate::native_client_hooks::has_mods()`, defined in `entry.rs:286` as `!mod_api::__private::mods().is_empty()`.
- Client chat: `game/remote.rs:2037` `chat_received` returns early when `mods().is_empty()`, so `native_client_chat_received` (`native_hooks.rs:6537`) is never called. Main: `game/network/remote/chat_received.rs:58` returns early unless `listened(HookId::ClientChatReceived)`, which a mixin does not set.
- Entity join: `game/native_entities.rs:516` `native_joins_flush` returns when `mods().is_empty()`. Main: `game/modding/native_entities.rs:209`.
- Damage v2: `game/mace.rs:211` `if !mods().is_empty() && ...` before `native_living_incoming_damage_v2` (`:216`).
- Damage v3: `game/native_hooks.rs:9890-9893` builds the parties only when `mods()` is not empty, and the v3 call at `:9937` needs them. v1 does run (`:9930`).
- Same pattern, same cause, already worked around by us: `natural_spawning.rs:479` (`spawn_hooks`), `creatures.rs:1663` (`mob_death_canceled`), `native_hooks.rs:9792` (knockback), `lan.rs:2322-2352` (sneak and others).

**Proposed.** One predicate for "a native mod is loaded", true for API mods and for mixin bundles, used at every one of these sites instead of `mods().is_empty()`:

```rust
/// True when an API mod or any native mixin bundle is loaded. API @API:mods_loaded@.
pub fn native_active() -> bool;
```

The launcher's generated executable already tells `mod_api` the bundles' ids before `entry::main_with` (`mod_api.rs:1023-1027`, `MOD_IDS`); it can set the flag at the same point. The dispatch cost is one relaxed load. A finer form, if wanted: the bundle lists the hooks it injects in `horizon-mixin.toml` (`listens = ["player_chat", ...]`) and each site tests its own hook, as `listened(HookId)` does on main.

**Workaround.** Per hook: the bundle overwrites the guard function (`spawn_hooks` returns true), injects HEAD on the caller (`mob_death_canceled`), or uses v1 (`native_living_incoming_damage`). Chat: a `/corporea <request>` command stands in for typing the request in chat. Entity join has none: no join-time spawn guard, and Draconic Evolution's Dragon Heart drops only on the first dragon kill.
