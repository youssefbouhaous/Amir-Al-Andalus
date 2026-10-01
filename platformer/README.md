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

**Level Select** lets you revisit completed chapters or play the next unlocked
chapter. Use Up/Down to choose, Left/Right to change pages, Enter to play, and
Escape to return; mouse selection and gamepad navigation work too. Each chapter
shows collected manuscript pages, best time, and a standalone replay-score record,
with goals for missing pages and personal bests. Replay scores start at zero and
are tracked separately from historical journey totals. Finishing a replay returns
to Level Select, and better records/pages are saved without resetting your journey.

### Courtyard of Wonders (optional)

Open **Level Select**, go to the last page, and choose **Courtyard of Wonders**.
It is available even on a new save and does not advance or complete the main journey.
All 15 existing maps, their controls and their original animation frames are preserved.

Only in this playground, the prince gains scarf grappling and ledge vaults, with
new sand-slide, spinning launch, wall-kick and landing poses layered onto his rig:

- **Tap Up / W in mid-air** near a golden rosette to grapple. Left/Right pumps the
  swing; Jump launches, Dash releases into a dash, and Down drops. Up + Dash still
  aims a normal upward dash. Hooks refill the air dash, like existing swing rings.
- **Fall toward a ledge** to catch it. Keep pushing toward it, or press Jump/Up to
  vault; hold Down to drop. Low ceilings and hazardous ledges cannot be grabbed.
- **Run + Down, then Jump** chains the sand slide into a scarf-trailing somersault.
  Landing poses are visual only: steering, jumps and attacks remain responsive.

Meet four new opponents: flank the **Mirror Duelist** or strike after its lunge;
wait for the **Sand Burrower** to surface after its warning ripples; defeat the
**Lantern Thief** to recover its borrowed dash light (it also returns after four
seconds); strike the **Clockwork Guardian** when its bronze armor opens.

Three manuscript detours combine these moves. A continuous lower floor catches
missed swings, and checkpoints sit between encounter areas. Rebuild **only** this
map with `python -m tools.build_wonders --force`. Supplemental player/enemy frames
are generated once and cached; no image-generation or runtime download is needed.

Run the automated scene-flow and audio checks without opening a window:

```bash
python -m unittest discover -s tests -v
```

Regenerate the tileset and the six campaign maps (overwrites `.tmx` files):

```bash
python -m tools.build_assets --force
python -m tools.build_assets --force --export-sprites   # + sprite templates
```

The advanced continuation chapter is generated separately so the original
six maps are never overwritten:

```bash
python -m tools.build_bonus_assets --force
```

## Controls

### The story

The journey now connects all fifteen chapters: Amir leaves the failing orange
orchard in search of the Sword of Light, finds the silent blade at the summit,
and follows the constellation trials to awaken it. Opening its second seal frees
the Ifrit and begins Book II's stolen night. The final confrontation brings the
story back to the lantern left burning in the orchard.

A 70-second opening film, **The Lantern Promise**, begins the journey. Amir tells
his story in first-person subtitles while running through the orchard, jumping a
water channel, catching the fountain's last drop, accepting the gardener's map,
and lighting a lantern before leaving. A moving camera, new acting poses, a
traced route across the map, music and timed sound effects stage the story in the
game's existing art style. The failed fountains give him a reason to seek the
Sword, while a torn warning foreshadows what he will release later.

At the end of the orchard, the thief's players are draining its last water: they
have turned a fountain into the **Moon-Clock**, whose brass column pours the
water up into a floating moon. Three masked performers step down from it, each in
a bubble of moon-water hung from the moon on a glowing string: **Rashid the
Juggler** (slash his oranges back at him), **Zahra the Blossom Dancer** (watch for
petals gathering behind you) and **Layla the Water-Weaver** (her whip, and the
moon's tides). Cut a string with a jumping slash so its bubble can't heal, burst
the bubble with three blows, then strike. The level's three manuscript pages
teach the **Brass Nightingale**, which rides on Amir's shoulder: its song bursts
every bubble in reach, snaps the strings and stuns the performers while it pecks
one. Elsewhere it knocks creatures senseless and shakes golden fruit from the
orange trees.

On the last rooftop of **level 2, Above the Amber Market**, the thief's **Elephant
Clock** - a colossal brass elephant with a castle on its back, after al-Jazari's
most famous machine - holds the setting sun in its trunk so that sundown never
comes. Three **Gilded Thieves** leap down from its castle: **Tariq the
Mirror-Thief** (a burning lance of reflected sun, and a vanishing glint), **Samira
the Fire-Eater** (fire breath, whirling fire poi, burning embers) and **Hakim the
Snake-Charmer** (brass cobras from his baskets, and the basket trick). A beam of
the stolen sun follows each one: while it rests on him he is gold and blows ring
off. Get into the light beside him - your own body shades him - or strike when he
moves faster than the beam can follow. Every hour of the fight the elephant keeps
time: the phoenix turns, a falcon drops a golden ball, and the serpent hurls it
across the roof. The level's pages teach the **Night Qalam**, the scribe's pen
whose ink is the night itself: press **V / E** to write a stroke of starry ink
ahead of you. It blots a thief (the sun can't gild him while the ink lasts),
cuts the beams, the lance and the flame short, swallows the sun-balls, and hangs
in the air for a few seconds as a road you can stand on.

In **level 3, The Moonlit Library**, the three pages teach **The Folded Fulcrum**:
an ivory-and-oxblood spring jack that unfolds from Amir's cuff. Press **V / E**
on firm ground to raise a temporary step; its rising ribs also repel ordinary
creatures. Beside the finish stands al-Muqallid's **Castle of Borrowed Hours**, an
enchanted castle clock after al-Jazari's (1206): a zodiac arch where the sun and
the moon ride the same track, a gallery of twelve hour-doors, twelve night-lamps,
falcons over cymbals, and the library's gentle keeper, **the Silent Archivist** -
an automaton made like a book - chained into its works by three chains of glowing
script. Its arms are the clock's hands: they sweep low, press, and comb high
(jump, dodge and slide; the hands shove rather than take health).

Free a drive by **jumping, then pressing Down to pound its floor treadle** when
white light rises from its jaw: each stroke turns one of six teeth. The clock
**borrows hours**: every hour a door opens and an echo of Amir steps out, replaying
exactly what he did one, two or three hours before, in step with the clock. Echoes
are ghosts you pass through - one may even land a stroke you missed - but where you
once slashed, an echo's blade stings, and every sting or shove lights two of the
twelve lamps. Twelve lamps strike **midnight**, and the drive you were working
rewinds. Face an echo and strike to shatter it and take its hour back. With the
Fulcrum, use V beside the jaw: the clock **stops** - the world turns silver, echoes
stand as glass that any blow shatters - and one pound frees the whole drive. Free
all three and the doors open, the borrowed hours go home as light, the sun climbs
to stand beside the moon, and the keeper opens its book. Progress survives
checkpoint retries; the map files are unchanged.

To try just this encounter without touching your real save:

```bash
uv run --active python -m tools.preview_archivist
# The difficult route, with no manuscript power:
uv run --active python -m tools.preview_archivist --without-power
```

The Archivist and Fulcrum are fictional mechanical adaptations, not historical
reconstructions or quotations from al-Jazari. The builder is honoured, never the
villain; al-Muqallid misuses his work. Historical reference: the Met's
[water-clock manuscript folio](https://www.metmuseum.org/art/collection/search/451302).

Short animated interludes connect the later chapters using existing scenery.
The original title screen, chapter cards, HUD, pause menu, controls and map files
are unchanged. **Enter** advances a story beat; **Escape** skips the whole scene.
Scenes also advance automatically at a reading-friendly pace. Gameplay, hazards,
the flood and the level timer do not run during them.

Story scenes are remembered in your save and do not repeat on deaths or checkpoint
retries. Level Select replays skip them altogether. **New Journey** resets the
story along with the existing journey progress; older saves load normally.
On an older save, **Continue** shows the new opening once, then resumes the correct
chapter without erasing scores, completed levels or options.
Collected manuscript pages reveal brief lore through the existing HUD toast.
Pages are optional: none are required to see the complete ending.

Chapter story text lives in `core/story.py`; the opening's screenplay and actor
tracks live in `core/prologue.py`. Both are separate from all level geometry.

### Keyboard and gamepad

| Key | Action |
|---|---|
| A / D or Left / Right | Move |
| Space | Jump (hold for a higher jump) |
| X / J / Left Shift | Slash; the star robe also throws a star |
| C / L / Ctrl | **Dash** in any of 8 directions (one air dash; landing, rings and blue lanterns recharge it) |
| Down while running | **Slide** under blades; jump out of it for a long slide-jump |
| Down in mid-air | **Ground pound**: breaks cracked stone, bricks and crumbling slabs, presses bronze plates, super-launches off drums |
| Jump again in mid-air (hold) | **Glide** with the shawl; ride fountain updrafts |
| Touch a golden ring | **Swing**: Left/Right pump, Jump lets go with a kick, Dash flies off |
| V / E | Use the level's **manuscript power** once all three of its pages are found (level 1: the Brass Nightingale) |
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

## Book II - The Ifrit's Night (levels 11-15)

After the Sword of Light is claimed, the Ifrit sealed in its shrine breaks
free and steals the dawn. Book II teaches the new moves one by one, then
braids them together:

| Level | Idea |
|---|---|
| 11 The Djinn's Bazaar | Dash and slide school: blade alleys, cracked walls, the Lantern Road (chains of dash lanterns over two chasms), a pound-plate portcullis |
| 12 The Swinging Moons | Glide and rings: moon pools, fountain updrafts, ring chains, the Moon Orchard |
| 13 The Drowned Cistern | A vertical escape from rising water: wall-jump shaft, a tower of dash lanterns, updraft vent, cracked roof |
| 14 The Seven Gates of the Sierra | Seven portcullises, each opened a different way: pound-drum launches, timed plate races, pounding through slabs |
| 15 The Ifrit's Crown | Everything at once through the Alhambra, then the Ifrit boss fight in the Court of the Lions |

Book II maps are authored in `tools/levels/book_two.py` and written with
`python -m tools.build_book_two` (it never touches levels 1-10).

### Proving levels can be finished

`python -m tools.check_levels level11 level12 ...` (or `--all-book-two`)
explores a map with the game's real player physics: from every standable
spot it tries walks, jumps, dashes, dash chains, glides, updraft rides,
slide jumps, wall climbs, ring swings and pound launches, and reports
whether the goal, every page and every checkpoint are reachable, plus any
spots from which the goal can no longer be reached (soft-locks).
Levels 11-15 all pass.
