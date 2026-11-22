# Draft 02: new issue on horizon-rust/horizon

**Title:** `Native mods: native_menu_input_closed cannot reach the player's persistent data or native_tell`

**Labels:** none needed.

**Duplicate check (2026-11-20):** nothing found in either repo (searched menu_input, input_closed, persistent_data, native_tell).

---

> 🤖 Filed by `<your GitHub handle>`'s AI agent (Claude Code), not by `<your GitHub handle>` personally.

**Ask.** In `native_menu_input_closed` a mod can still read and write the player's persistent data and send them a line, as it can in any other player hook.

**Why.** A mod menu with input slots (a pouch or crafting-style menu) decides what to keep when it closes: it records the result on the player (persistent data) and tells them what happened. Our Ender Pouch and Corporea request menus need both at that moment.

**NeoForge counterpart.** `AbstractContainerMenu.removed(Player)`: the player is a live `ServerPlayer`, so `getPersistentData()` and `sendSystemMessage` just work.

**Horizon today** (engine `04a26210e3`):
- The hook's doc says it itself: "The hub may be out of the game's hands and a player's state swapped in ..., so answer through `slots`; the helpers that take a UUID may see nothing" (`game/native_hooks.rs:7950-7957`).
- It is called at `game/native_menus.rs:516` and `:538` while the hub `host: &mut LanHost` is borrowed out of `self.lan`.
- `native_player_persistent_data` / `native_set_player_persistent_data` go through `native_place` (`game/native_player_state.rs:140-151`, `:506-513`), which needs `self.lan.as_ref()?` and returns None.
- `native_tell` (`game/native_server.rs:411`) goes through `native_send`, which needs the hub too.

**Proposed.** Mirror `native_player_chat`'s reply list (`lan/hub/chat.rs:20-27`), so the engine applies the answer once the hub is back:

```rust
/// API @API:menu_input_v2@. Like `native_menu_input_closed`, and the engine applies
/// `replies` (system lines to the player) and `data` (the player's persistent data,
/// read in, written back when changed) after the hub is back.
fn native_menu_input_closed_v2(player: u128, window: i32, slots: &mut Vec<Option<ItemStack>>,
    data: &mut Compound, replies: &mut Vec<Text>);
```

Additive; v1 stays. Alternative: run the hook after the hub is put back, if the item return can be ordered after it.

**Workaround.** Not written yet; we would queue the data write and the line in a static and apply them from the next player tick hook (one tick late, lost if the player leaves first).
