# Amir Al-Andalus

A 2D side-scrolling platformer in Python + Pygame. A young prince crosses six
increasingly dangerous regions of al-Andalus to claim the legendary **Sword
of Light**: gardens, rooftops, fortress walls, aqueducts, a clockwork alcazar,
and the final summit.

All art and sound is original and procedurally generated in an Andalusian
style (zellige mosaics, Mudéjar brick, horseshoe arches, orange trees,
Hijaz-scale melodies), so the game runs with zero external assets.

## The world

| Game concept | In al-Andalus |
|---|---|
| Player / powered up | The prince / golden robe after eating a **pomegranate** (Granada's fruit) |
| Coins | Gold **dinars** (100 = extra life) |
| Mystery blocks | **Zellige** mosaic tiles; hit from below |
| Breakable blocks | **Mudéjar brick**; only the golden prince breaks them |
| Extra life | A magic **oil lamp** |
| Pipes | Tiled **wells**; press Down on top to travel |
| Checkpoints | **Lanterns** that light up |
| Level exit | A **horseshoe arch** gate; the last level ends at the **Sword of Light** |
| Traversal puzzles | Moving platforms, spring drums, timed fountains, wind corridors, water gaps, spikes, and shifting sun/moon blocks |
| Enemies | **Scorpions** (walk, some patrol ledges), haunted **clay jars** (hop), **jinn** wisps (fly), hedgehogs, bats, and ghuls |

## Setup and running (Ubuntu)

```bash
cd ~/py-game/platformer
python3 -m venv .venv          # needs: sudo apt install python3-venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

With the local virtual environment active, `uv run --active main.py` also
works. Install all packages in `requirements.txt`, including NumPy for the
procedural music and sound effects.

The title screen offers **Continue** after you start a journey. Completed
levels, best times, scores, and collected pages are saved when the results
screen appears. Continue starts the first unfinished level with fresh lives;
it does not restore a position within a level. **New Journey** asks before
replacing saved progress and keeps your options.

Run the automated scene-flow and audio checks without opening a window:

```bash
python -m unittest discover -s tests -v
```

Regenerate the tileset and the six campaign maps (overwrites `.tmx` files):

```bash
python -m tools.build_assets --force
python -m tools.build_assets --force --export-sprites   # + sprite templates
```

## Controls

| Key | Action |
|---|---|
| A / D or Left / Right | Move |
| Space | Jump (hold for a higher jump) |
| S / Down | Enter a tiled well (pipe) |
| Escape | Pause |
| Enter | Confirm in menus |
| F1 | Debug view (hitboxes, tile collision, velocity, camera) |
| F5 | Reload the current level file from disk (for editing in Tiled) |

## Project structure

```
main.py                    entry point: pygame init/shutdown, top-level errors
core/
  game.py                  window, clock, main loop (fixed sub-steps)
  settings.py              every tunable constant + physics dataclasses
  context.py               services shared by scenes (assets, audio, input...)
  input.py                 keys -> actions, held / pressed / released
  assets.py                cached image/sound loading with placeholder fallback
  events.py                gameplay events (COIN_COLLECTED, ENEMY_STOMPED...)
  session.py               score, coins, lives, checkpoint: pure logic
physics/
  body.py                  float position/velocity/size + contact flags
  collision.py             axis-separated move-and-collide, one-way platforms
world/
  collision_map.py         tile grid used for collision (spatial partition)
  level_loader.py          Tiled .tmx -> LevelData
  level_data.py            static, cached description of a level
  tile_layer.py            visual tile layer with camera culling
  world_builder.py         LevelData -> live World (Tiled type -> class)
  world.py                 live level state + update order
  interactions.py          player/enemy/item/trigger rules
entities/
  entity.py                minimal base: alive, rect, update, draw
  player.py                player physics + state machine
  player_controller.py     input -> PlayerIntent
  enemies/                 Enemy base, Walker, Hopper, Flyer + registry
  items.py                 Coin, PowerUp, ExtraLife, block contents
  effects.py               coin pop, brick debris, score popups
objects/
  block.py                 BrickBlock, QuestionBlock
  moving_platform.py       eased back-and-forth one-way platform
  triggers.py              Checkpoint, Goal, Door (pipes)
rendering/
  camera.py                world <-> screen transform, dead zone, bounds
  animation.py             Animation (shared frames) + Animator (playback)
  sprite_library.py        sprite sheet slicing with placeholder fallback
  sprite_specs.py          layout of every sprite sheet
  placeholder_art.py       procedural original Andalusian-style art
  background.py            sky gradient + parallax city skyline
  fade.py                  fade-to-black transitions
scenes/                    scene stack: menu, intro, game, pause, end screens
ui/                        HUD, buttons/menus, text, debug overlay
audio/                     AudioManager + synthesized placeholder sounds
tools/build_assets.py      generates tileset.png/.tsx and the starter .tmx maps
assets/
  images/                  tileset.png (+ your sprite sheets)
  maps/                    level1-3.tmx, tileset.tsx
  sounds/, music/          optional; drop files in to replace placeholders
```

### Why the major pieces exist

* **Game** only runs the loop. Everything else is a *scene*, so `Game` never
  grows.
* **SceneManager** is a stack. Pausing = pushing `PauseScene`; the game scene
  simply stops receiving `update()`, so there are no `if paused` checks.
* **World** simulates one level attempt and emits **events**. It knows nothing
  about score, sound or scenes. **GameScene** turns events into score (via
  `GameSession`), sounds (via `AudioManager`) and popups, and handles death,
  doors and level completion.
* **Body + move_body** are shared by player, enemies and items (composition),
  so there is exactly one collision implementation.
* **Player** has one `PlayerState` enum instead of many booleans; its
  animation is looked up from the state. **PlayerController** separates
  keyboard from player logic.
* **Enemy** subclasses only implement `behave()`. Player-enemy rules live in
  `interactions.py` and ask the enemy what happens (`on_stomped()`), so the
  Player class has no enemy-specific code.
* **LevelData vs World**: the map is parsed once; each respawn builds a fresh
  World from it, so enemies/coins reset cheaply.

## Key concepts

**Game loop and delta time.** Each frame: read input, update, draw. Movement
uses `position += velocity * dt` (pixels per second), so speed doesn't depend
on frame rate. Frames are split into sub-steps of at most 1/120 s, and a very
long frame is capped at 0.1 s, so jump height is consistent and fast objects
never move far enough in one step to pass through a tile.

**Collision resolution** (`physics/collision.py`). Move on X, push out of any
solid tile along X only; then move on Y, push out along Y. Because each axis
is resolved separately you always know which side was hit (wall, floor or
ceiling), and snapping exactly to the tile edge means no sinking into floors.
Positions are floats; `pygame.Rect` (integers) is only used for drawing.

**Spatial partitioning.** `CollisionMap` converts a body's bounds into tile
indices (`min_tx..max_tx`, `min_ty..max_ty`) and checks only those cells, so
cost is independent of level size. Tile drawing is culled the same way.

**World vs screen coordinates.** Nothing moves to fake scrolling.
`screen = world - camera.position`, applied at draw time. The camera follows
with a dead zone and exponential smoothing (`1 - exp(-k*dt)`), and is clamped
to the map (or to a camera zone), so it never shows outside the level.

**Moving platforms.** A platform's per-step displacement (`delta`) is added to
the movement of whatever stands on it and goes through normal collision, so a
platform can't carry you through a wall. Landing checks the platform's
*previous* top, which makes it work while the platform moves up or down.

**Variable jump, coyote time, jump buffer.** Releasing Space while rising
multiplies upward speed by 0.4. You can still jump 0.1 s after leaving a
ledge, and a jump pressed 0.12 s before landing still happens. All values are
in `PlayerPhysics` in `core/settings.py`.

## Designing levels in Tiled

1. Install Tiled (`sudo snap install tiled` or from mapeditor.org).
2. Open `assets/maps/level1.tmx`. The tileset `tileset.tsx` is already linked.
   Tiles are 32x32; the map should be 17 tiles tall (544 px) or more.
3. **Tile layers** (names matter):
   * `background` (clouds), `decorations` (bushes, grass): visual only.
   * `terrain`: every tile here collides. Tile property `collision` can be
     `solid` (default), `one_way` (the plank tile) or `none`.
   * `blocks`, `collectibles`: paint brick / question / coin tiles. These
     tiles have a `spawn` property in the tileset, so the game turns them into
     objects. The question tiles with a green/pink dot release a power-up /
     extra life (property `contents`); in game they all look the same.
   * optional `collision` (invisible colliders) and `foreground` (drawn in
     front of the player).
4. **Object layer** `entities`: insert rectangles and set their **Class**
   (called Type in older Tiled):

   | Class | Properties |
   |---|---|
   | `player_spawn` | - (one required) |
   | `enemy` | `kind` = scorpion / jar / jinn (or walker / hopper / flyer); `facing` = left / right; `edge_aware` (bool, walkers turn at ledges); `patrol_tiles` (float, flyers) |
   | `checkpoint` | - |
   | `goal` | `style` = gate (arch to the next level) or sword (final prize) |
   | `moving_platform` | `axis` = horizontal / vertical; `distance` (tiles, float); `speed` (px/s, float); `reverse` (bool). Rect width = platform width |
   | `door` | needs a **Name**. `target_door` = name of the arrival door; optional `target_level` = e.g. `level3.tmx`. Place it on top of a pipe; press Down to enter. A door without `target_door` is only an arrival point |
   | `camera_zone` | rectangle the camera is limited to while the player is inside (bonus rooms) |

   Objects are anchored at the bottom-centre of their rectangle, so a 32x32
   rectangle sitting on the ground puts the enemy on the ground.
5. **Map properties** (Map > Map Properties): `name` (shown in HUD),
   `subtitle` (shown on the level intro card), `next_level` (e.g.
   `level2.tmx`, empty = last level), `sky` = dawn / sunset / night, `music` (file name in `assets/music` without extension).
6. Save, then press **F5** in game to reload the level without restarting.

To add a level: copy a `.tmx`, change it, and point the previous level's
`next_level` at it.

## Replacing placeholder assets

* **Tiles**: edit `assets/images/tileset.png` (keep the 8-column layout).
* **Sprites**: `python -m tools.build_assets --force --export-sprites` writes
  templates to `assets/images/templates/`. Paint over one, and save it in
  `assets/images/` with the same name (e.g. `prince.png`, `scorpion.png`,
  `clay_jar.png`, `jinn.png`, `dinar.png`, `pomegranate.png`,
  `oil_lamp.png`). Layouts are in
  `rendering/sprite_specs.py`.
* **Objects**: `checkpoint.png`, `checkpoint_active.png`, `goal_gate.png`,
  `goal_sword.png`,
  `hud_coin.png`, `hud_heart.png` in `assets/images/`.
* **Sounds**: `assets/sounds/<name>.wav|ogg` where name is one of: jump, coin,
  stomp, kick, bump, break, item_appear, powerup, extra_life, hurt, death,
  checkpoint, level_complete, door, menu_move, menu_select, pause.
* **Music**: `assets/music/menu.ogg`, `level1.ogg`, `level2.ogg`,
  `level3.ogg`. Royalty-free oud or Andalusian-style tracks fit well.

## Manual test checklist

- [ ] Menu: Up/Down/Enter and mouse work; Controls screen opens and closes.
- [ ] Level intro card shows the level name and lives.
- [ ] Movement accelerates and slides to a stop; turning is snappy.
- [ ] Tap Space = small hop, hold = high jump; jump just after walking off a
      ledge still works; pressing jump just before landing still jumps.
- [ ] Never sink into floors, stick to walls or pass through ceilings (F1).
- [ ] Camera follows smoothly, never shows outside the map.
- [ ] Hit a zellige block: a dinar pops out and it turns to plain terracotta.
      Some release a pomegranate that slides; eating it turns the robe gold.
- [ ] The golden prince breaks bricks; otherwise they only bump.
- [ ] Jump on an enemy: it's squashed and you bounce. Touch it from the side:
      gold player shrinks and blinks, small player dies.
- [ ] Bumping a block knocks out an enemy standing on it.
- [ ] Fall into a pit: death, fade, respawn, one life lost.
- [ ] Touch a lantern (it lights up), die: respawn at the lantern.
- [ ] Level 2: ride the cedar beams; press Down on the first tiled well to
      reach the hidden dinar room, and take the other well back out.
- [ ] Walking through the arch: Level Complete screen, then next level.
- [ ] Losing the last life shows Game Over; reaching the Sword of Light at
      the end of level 3 shows the victory screen.
- [ ] Escape pauses and resumes; Main Menu returns to the title.
- [ ] Game runs with no sound device and with no files in `assets/sounds`.

## Not implemented yet

Controller support, a level timer, a sprint button, crouching, shooting
power-ups, enemy shells, slopes, saving progress, settings menu (volume, key
rebinding), and animated tiles from Tiled.
