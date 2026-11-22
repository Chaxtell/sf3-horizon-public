# `sf3_host` API (2026-11-20)

Every function of `mods/sf3_host/sf3_host.rs` (SDK build 0a875da). Each mod carries a byte-identical copy at
`src/sf3_host.rs`. Reads take `&dyn Host` (a `&mut dyn ServerHost` or `&mut dyn ClientHost` coerces); writes take
`&mut dyn ServerHost`. Levels are passed by name (`minecraft:the_nether`); a hook handed a `LevelRef` turns it into the
name with `level_name`. Writes return `bool` and drop the SDK's refusal reason.

| Signature | What it does | Wraps (SDK) | Replaces (old) |
|---|---|---|---|
| `on(host: &dyn Host, mod_id: &str) -> bool` | Whether the player left the mod on in Options > Mods | `Host::on` | `native_on` |
| `dimension(host: &dyn Host) -> &'static str` | The level in place, for a hook that names none | `Host::dimension` | the implicit level of the old calls; `NativeServerPlayer.dimension` |
| `level_name(host: &dyn Host, level: LevelRef) -> Option<String>` | The name of a level a hook was handed (`level_tick_post`'s `event.level`) | `LevelRef::dimension` + `DimensionKey::id` | the `dimension` argument of `native_level_tick_post` |
| `block_id(host: &dyn Host, dim: &str, pos: [i32; 3]) -> Option<String>` | The block at `pos`; None for an unknown level | `Host::level` + `LevelRef::block` + `BlockKey::id` | `native_block` |
| `state_id(host: &dyn Host, state: BlockState) -> String` | The block of a state a hook was given | `BlockState::block` + `BlockKey::id` | `registry.state(state).name` |
| `set_block(host: &mut dyn ServerHost, dim: &str, pos: [i32; 3], block: &str) -> bool` | Sets the block's default state, flags 3. Whether it changed | `block_key` + `block_state_default` + `LevelRef::set_block` (`NEIGHBORS \| CLIENTS`) | `native_default_state` + `native_set_block` |
| `be_data(host: &dyn Host, dim: &str, pos: [i32; 3]) -> Option<Compound>` | The block entity's saved data; None when there is none | `block_entity` + `BlockEntityRef::data` | `native_mod_block_entity`, `native_block_entity_tag` |
| `be_merge(host: &mut dyn ServerHost, dim: &str, pos: [i32; 3], data: Compound) -> bool` | Merges keys into the block entity (`/data merge block`). Whether it changed | `block_entity` + `BlockEntityRef::merge_data` | `native_with_mod_block_entity` (add or overwrite only) |
| `be_update(host: &mut dyn ServerHost, dim: &str, pos: [i32; 3], change: impl FnOnce(&mut Compound)) -> bool` | Read-modify-write: reads the data, `change` edits it (keys may be removed, nested values changed), written back once whole. Whether there was a block entity | `block_entity` + `BlockEntityRef::data` + `BlockEntityRef::replace_data` | `native_with_mod_block_entity` |
| `acting_player(host: &dyn ServerHost) -> Option<PlayerRef>` | The player whose action the running hook hears | `players().acting_player()` | `native_acting_player` |
| `player(host: &dyn Host, uuid: u128) -> Option<PlayerRef>` | The online player `uuid` | `Host::player` | the uuid argument of the old player calls |
| `game_mode(host: &dyn Host, player: PlayerRef) -> Option<GameMode>` | The player's game mode | `PlayerRef::game_mode` | `NativeServerPlayer.game_mode` |
| `main_hand(host: &dyn Host, player: PlayerRef) -> Option<ItemStack>` | The main-hand stack; None when empty | `living` + `LivingRef::hand_item(Hand::Main)` | `game.held()` |
| `tell(host: &mut dyn ServerHost, player: PlayerRef, line: &str) -> bool` | A system chat line. Whether it was shown | `PlayerRef::tell` | `native_tell` (the `native_chat` fallback dropped) |
| `inventory_slots(host: &dyn Host, player: PlayerRef) -> Vec<(u32, ItemStack)>` | Non-empty slots by number (0-35 main) | `PlayerRef::inventory_slots` | `native_inventory(.., Player)` |
| `set_slot(host: &mut dyn ServerHost, player: PlayerRef, slot: u32, stack: Option<ItemStack>) -> bool` | Writes one slot (None empties it). Whether it was written | `PlayerRef::set_inventory_slot` | `native_set_inventory_slot` |
| `give(host: &mut dyn ServerHost, player: PlayerRef, stack: ItemStack) -> bool` | `/give`; overflow is thrown at the player. Whether it was given | `PlayerRef::give_stack` | `native_give_stack` + `spawn_item` for the leftover |
| `add_effect(host: &mut dyn ServerHost, player: PlayerRef, id: &str, amplifier: i32, duration: i32) -> bool` | Adds an effect with particles. Whether it was added | `effect_key` + `living` + `LivingRef::add_effect` | `native_add_effect` |
| `spawn_mob(host: &mut dyn ServerHost, dim: &str, kind: &str, at: [f64; 3], name: Option<&str>) -> bool` | Command spawn (finalizeSpawn runs), optionally named. Whether it spawned | `LevelRef::spawn_mob(SpawnReason::Command)` + `set_custom_name` | `native_spawn_mob` |
| `summon(host: &mut dyn ServerHost, dim: &str, kind: &str, at: [f64; 3], nbt: Compound) -> bool` | `/summon` in the level in place. Whether it joined | `ServerHost::summon` | `native_summon` |
| `run_command(host: &mut dyn ServerHost, line: &str) -> bool` | Console command, permission 4. Whether it ran | `commands().run_command` | `native_run_command` |
| `item_id(host: &dyn Host, stack: &ItemStack) -> String` | The stack's item id | `ItemStack::item` + `ItemKey::id` | `stack.item` |
| `stack(host: &dyn Host, id: &str, count: u32) -> Option<ItemStack>` | A new stack; None for an unknown item or count 0 | `Identifier::parse` + `item_key` + `ItemStack::new` | `ItemStack::new(id, count)` |
| `is_food(host: &dyn Host, stack: &ItemStack) -> bool` | Whether the stack or its item's default has `minecraft:food` | `ItemStack::components` + `item_default_component` | `game.items().get(id).food` |
| `custom_data(stack: &ItemStack) -> Option<Compound>` | The stack's `minecraft:custom_data` | `ItemStack::components` + `as_nbt` | `stack.custom_data()` |
| `set_custom_data(stack: &mut ItemStack, data: Compound) -> bool` | Replaces `minecraft:custom_data`. Whether the stack took it | `ItemStack::apply_components` | `stack.data_mut().set_other(..)` |
| `compound(entries: &[(&str, Tag)]) -> Compound` | Builds a compound (summon NBT, block-entity or item data) | `Compound: FromIterator` | `JavaString`-keyed inserts in glue code |
| `nbt_get<K>(c: &BTreeMap<K, Tag>, key: &str) -> Option<&Tag>` | `c[key]` by `&str` | `BTreeMap::get` | `nbt.get(&JavaString::from(key))` |

### Added for machines (bundle 12, `mods/sf3_envtech`)

No existing signature changed; `mods/sf3_chance/src/sf3_host.rs` was recopied byte-identical and its `cargo test` still passes.

| Signature | What it does | Wraps (SDK) | Replaces (old) |
|---|---|---|---|
| `day_time(host: &dyn Host, dim: &str) -> i64` | Time of day in ticks (shared by all levels); 0 for an unknown level | `LevelRef::day_time` | `native_day_time` |
| `weather(host: &dyn Host, dim: &str) -> (bool, bool)` | Raining, thundering. Yes/no only: the SDK has no 0..1 levels | `LevelRef::is_raining` + `is_thundering` | `native_weather` (0..1 levels) |
| `has_signal(host: &dyn Host, dim: &str, pos: [i32; 3]) -> bool` | Whether a neighbour powers the block | `LevelRef::has_neighbor_signal` | `native_neighbor_signal(..) > 0` |
| `sky_light(host: &dyn Host, dim: &str, pos: [i32; 3]) -> i32` | Stored sky light 0..15; 0 where not loaded | `LevelRef::brightness(LightLayer::Sky)` | `native_light(..).1` |
| `is_loaded(host: &dyn Host, dim: &str, pos: [i32; 3]) -> bool` | Inside the height and its chunk loaded | `LevelRef::is_loaded` | `native_chunk_is_loaded` |
| `min_y(host: &dyn Host, dim: &str) -> Option<i32>` | Lowest block y | `LevelRef::height` | `native_world_height().0` |
| `has_collision(host: &dyn Host, dim: &str, pos: [i32; 3]) -> bool` | Whether the block's collision shape is not empty | `LevelRef::block_state` + `block_shape(Collision)` | `!native_block_collision(..).is_empty()` |
| `is_block(host: &dyn Host, id: &str) -> bool` | Whether `id` names a block (an item that places one) | `Host::block_key` | `native_default_state(..).is_some()` |
| `strike_lightning(host: &mut dyn ServerHost, dim: &str, at: [f64; 3]) -> bool` | A real bolt. Whether it struck | `LevelRef::strike_lightning(.., false)` | `native_lightning_bolt(.., false)` |
| `entities_in(host: &dyn Host, dim: &str, min: [f64; 3], max: [f64; 3]) -> Vec<EntityRef>` | Entities whose boxes meet the box | `LevelRef::entities_in` | `native_entities_in` + `native_entity` |
| `entity_kind(host: &dyn Host, entity: EntityRef) -> Option<String>` | The entity's type id | `EntityRef::kind` + `EntityTypeKey::id` | `native_entity_kind` |
| `set_velocity(host: &mut dyn ServerHost, entity: EntityRef, velocity: [f64; 3]) -> bool` | Sets velocity; a player through its own handle | `EntityRef::set_velocity`, else `uuid` + `PlayerRef::set_velocity` | `native_entity_set_velocity` (refused players) |
| `sneaking(host: &dyn Host, player: PlayerRef) -> bool` | Sneak key held | `EntityRef::is_shift_key_down` | `native_sneaking` |
| `permission(host: &dyn Host, player: PlayerRef) -> Option<u8>` | Permission level | `PlayerRef::permission_level` | `NativeServerPlayer.permission` |
| `may_fly(host: &dyn Host, player: PlayerRef) -> Option<bool>` | Whether the player may start flying | `PlayerRef::may_fly` | `NativeServerPlayer.may_fly` |
| `set_may_fly(host: &mut dyn ServerHost, player: PlayerRef, may_fly: bool) -> bool` | Grants or takes flight (taking also lands). Whether written | `PlayerRef::abilities` + `set_abilities` | `native_set_flight(uuid, allow, false)` |
| `action_bar(host: &mut dyn ServerHost, player: PlayerRef, line: &str) -> bool` | A line over the hotbar. Whether shown | `PlayerRef::action_bar` | `native_action_bar` + `native_client_action_bar` |
| `add_effect_ambient(host: &mut dyn ServerHost, player: PlayerRef, id: &str, amplifier: i32, duration: i32) -> bool` | Effect as a beacon gives it: ambient, no particles, icon shown. Whether added | `effect_key` + `LivingRef::add_effect` | `native_add_effect` (ambient), `add_player_effect` (host) |
| `max_stack(host: &dyn Host, stack: &ItemStack) -> u32` | `minecraft:max_stack_size` of the stack or its item; 64 without | `ItemStack::components` + `item_default_component` | `native_max_stack_size` |
| `energy_insert(host: &mut dyn ServerHost, dim: &str, pos: [i32; 3], side: Direction, amount: i32) -> i32` | Energy into a neighbour's `ENERGY` handler (any mod's), in one transaction. How much went | `LevelRef::capability(&ENERGY)` + `HostTransaction::transaction` + `EnergyHandler::insert` | `native_energy` + `native_energy_insert` |
| `insert_item(host: &mut dyn ServerHost, dim: &str, pos: [i32; 3], side: Direction, stack: ItemStack) -> Option<ItemStack>` | A stack into a neighbour's `ITEMS` handler (chest, hopper, pipe). What did not go in | `LevelRef::capability(&ITEMS)` + `ResourceHandler::insert_any` | `native_insert_item` |
| `declare_energy(r: &mut dyn Registrar, block: &str, buffer: ModEnergyBuffer)` | Registration: a mod block's energy buffer, answered by the game's `ENERGY` from `nbt.energy` | `block_key` + `block_energy` | `native_block_entity_energy` injection |
| `declare_container(r: &mut dyn Registrar, block: &str, container: ModContainer)` | Registration: a mod block's slots and menu, answered by the game's `ITEMS` | `block_key` + `block_container` | `native_block_entity_container` injection |

Capability lookups (`energy_insert`, `insert_item`) answer only in the level in place (`LevelRef::capability`), so call them
from the block entity's own tick or a hook of that level, never from `server_tick`. Machine progress bars and client sync
(`block_entity_sync`, menu data slots) are not wrapped yet: bundle 12 draws none and syncs nothing.

`compound` and `nbt_get` exist because the SDK does not export the compound key type (`JavaString`), so mod code cannot
name a key; with them a change to that type touches one file. To add keys inside `be_update`, `c.extend(compound(..))`;
removing a key from mod code is not checked (the key type cannot be named, and `remove` is generic over it); add an
`nbt_remove` next to `nbt_get` when the first bundle needs it.

## FakeHost tests (`mods/sf3_chance/src/glue_tests.rs`)

Both tests the design names run: a due Command job reaches `host.commands.ran` as `runtime::render` writes it, and a
chance survives the custom-data round trip. A third checks that a level tick takes only its own level's due jobs.
`level_name`, `be_update` and the other block-entity, level and player calls are not tested: FakeHost panics on them
("unavailable during Packages") or finds no block at the fake level (design section 6). Play covers them.

`mods/sf3_envtech/src/glue_tests.rs` (6 tests) runs `energy_insert` (into a `FakeBattery`, full and partial, top face
skipped), `insert_item` (into a `FakeContainer`, and with no neighbour), `max_stack` and the NBT helpers. The world reads
added for machines (time, weather, light, signal, collision, entities, players) are not tested on FakeHost.
