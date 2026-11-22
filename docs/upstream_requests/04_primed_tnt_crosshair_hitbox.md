# Draft 04: new issue on horizon-rust/horizon

**Title:** `parity(entities): a player's crosshair does not pick a primed TNT (PrimedTnt.isPickable)`

**Labels:** `bug`, `parity` (this is a vanilla difference; existing ones are titled `parity(entities): ...` with those labels).

**Duplicate check (2026-11-20):** no match. Nearby and different: horizon-rust/horizon#18964 and #18965 (set fuse, detonate), #16524 and #17269 (TNT rotation and tick parity).

---

> 🤖 Filed by `<your GitHub handle>`'s AI agent (Claude Code), not by `<your GitHub handle>` personally.

**Ask.** The crosshair picks a lit TNT as vanilla does, so a left click attacks it and a right click interacts with it, and mods hear the usual hooks.

**Why.** Charset's "hit TNT" (hit a primed TNT to make it react) cannot trigger: nothing the player aims at a lit TNT reaches an attack or interact hook.

**Vanilla.** `PrimedTnt.isPickable()` is `!isRemoved()`, so `ProjectileUtil.getEntityHitResult` includes it.

**Horizon today** (engine `04a26210e3`):
- The player's pick, `Game::mob_hit_within` (`game.rs:7329-7347`), loops over `self.mobs` only; `self.tnts` is never consulted.
- Projectiles do pick TNT: `pickable_object_targets` (`game/creatures.rs:5168-5173`) lists boats, minecarts and `self.tnts`. So the pickable boxes exist, but only for the projectile path.
- Not re-checked on main `084ae44e40` (the pick code was not read there).

**Proposed.** Add `self.tnts` (`t.bounds()`) to the candidates of `mob_hit_within` and route the hit through the same attack and use paths a mob hit takes. It needs a harness: a probe for "crosshair on a primed TNT", extending the existing pick harness.

**Workaround.** None. Charset's hit TNT stays coded and unit-tested only (`MASS_PORT_PLAN.md`, Batch 9, 9J).
