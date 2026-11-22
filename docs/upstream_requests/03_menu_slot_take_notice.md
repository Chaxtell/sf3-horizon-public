# Draft 03: new issue on horizon-rust/horizon (cites arismoko/horizon#4300)

**Title:** `Mod menus: a server-side take notice (menu_slot_take) for block-entity menus`

**Labels:** none needed.

**Duplicate check (2026-11-20):** arismoko/horizon#4300 asks for exactly this (same title) and is CLOSED, but its PR arismoko/horizon#4465 was closed unmerged, and main has no `menu_slot_take` (code search of horizon-rust/horizon: no hit; `hooks/menu_slot_rules.rs` and `item/menu_slot.rs` carry the pickup rule only). So this is a new issue that cites it. If you prefer a comment, post the "Why" and "Horizon today" parts on #4300 and ask for it to be reopened.

---

> 🤖 Filed by `<your GitHub handle>`'s AI agent (Claude Code), not by `<your GitHub handle>` personally.

**Ask.** Nothing runs on the server when a player takes a stack out of a mod menu's slot. A mod needs a notice after the take, with the player, the menu, the slot and the stack, to spend inputs and refresh a preview. The contract is the one designed in arismoko/horizon#4300 ("Contract: `menu_slot_take`": a listen-only notice after the take; fields player, menu type, slot index, `taken`, `left`; fired once per take, and once per craft on a shift-click).

**Why.** Block-entity menus with a result slot (crafting stations and machines in our port) show a preview in the result slot and must consume the input stacks, and run side effects, only when the result is taken. Today the only way is to poll the slots every tick and infer a take from a changed result slot.

**NeoForge counterpart.** `Slot.onTake(Player, ItemStack)` (a method the menu's slot class overrides; no event). `item_crafted` and `item_smelted` cover only the crafting grid and furnaces.

**Horizon today** (engine `04a26210e3`): no hook for it. The nearest are `native_menu_clicked` (`game/native_hooks.rs:8053`, the raw click at its start, cannot know whether anything was taken) and `native_menu_quick_move` (`:4328`). A grep for `slot_take`, `menu_take`, `may_pickup` finds nothing under `game/`. Main (`084ae44e40`) has `native_hooks/menu_slot_rules.rs` (pickup rule) but, as far as searched, no take notice.

**Proposed.** `native_menu_slot_take(player: u128, menu: &str, pos: [i32; 3], slot: i32, taken: &ItemStack, left: Option<&ItemStack>)`, server side, listen-only, as #4300 specifies (fires after the move, not on a refused pickup). No cancel: refusing belongs to the pickup rule.

**Workaround.** Poll the menu's result slot each server tick and treat a drop in its count as a take (misses a take and refill within one tick; cannot see a quick-move's repeat count).
