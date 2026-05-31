# Feya's Swamp — Object‑Oriented Python API Design

A design blueprint for an OOP backend library that lets a frontend/server play a
simplified-but-complete fragment of the board game **Feya's Swamp** (El Pantano de
Feya). The library exposes a single **Façade** class, `Game`, and delegates all
logic to encapsulated sub‑components.

> This is an internal **design document**, not the submission `README.md`.
> The submission `README.md` is a separate, word‑limited artefact; a compliant
> draft of it is included in §16. This document itself is free to use Markdown
> formatting, code fences, and tables — the constraints in §2 apply only to the
> *submitted code and README*, never to this planning file.

---

## 0. Source hierarchy (which input governs what)

| Source | Role in this design | Authority |
|---|---|---|
| **`requirement.pdf`** | The OOP assignment brief: packaging, type‑safety, encapsulation, allowed modules, pattern list, scoring of the *submission*. | **SOURCE OF TRUTH.** Every rule here is binding. Where anything below conflicts with it, it loses. |
| **`Feyas_Swamp_Rulebook.pdf`** | The *domain* to model: components, setup, phases, actions, scoring of the *game*. | Defines **what** to build. May be simplified per the brief (§1.1 of the requirement). |
| **`SESSION.md`** | A transcript of the professor live‑coding an analogous library (an Oxford marketplace). Reveals **expected coding idioms, patterns, and workflow**. | **Style/idiom reference**, appended to the requirement. Note: it is a *different domain* and predates two rules that this assignment adds — see §3.3. |
| **`pyproject.toml`** | The professor's tool configuration (Python 3.14, `mypy --strict`, `black`, `__init__.py`‑based versioning). | **Tooling reference.** Mirror the tool setup; **rename the package to `game`** (the toml's `deliverox` is the marketplace project, not ours). |

---

## 1. What the library must be (requirement §1.2–1.4)

1. **A library, not an app.** No console I/O, no UI of any kind. (`print`, `input`
   are *forbidden imports/functions* anyway — §2.) The deliverable is a backend
   that "sits behind an API endpoint on a server."
2. **A Façade.** The public class `Game` is the *only* non‑builtin class a user
   ever instantiates. Everything else is reached through `Game`'s public
   properties and methods. (Structural pattern: **Facade**.)
3. **Multiple independent instances.** `Game()` must be reentrant — no shared
   mutable global state. (This is *why* Singleton is the one banned pattern: the
   brief wants N concurrent online games.)
4. **Fully programmatic.** Every legal move is callable; every piece of game
   information is readable — programmatically, with no UI in the loop.
5. **Impossible to misuse.** Illegal actions must either *fail to type‑check* or
   *raise at runtime*. Read‑only views must not leak mutable internals.

---

## 2. Hard constraints checklist (requirement §2–3) — binding on the code

These are copied out so the implementation can be checked against them line by line.

### Packaging (§3.2)
- [ ] One package named **`game`**. Flat: **no sub‑folders**, only `.py` modules.
- [ ] **All module names public** — no leading underscore on filenames.
- [ ] **Relative** intra‑package imports: `from .board import Swamp`.
- [ ] `game/__init__.py` exports **`Game` and nothing else**.
- [ ] `from game import Game` works with no side effects/errors.

### Formatting / size (§3.3)
- [ ] Format with `black game`.
- [ ] **≤ 3000 lines total** across all modules (after black). LOC = `len(list(f))`.
- [ ] **≤ 500 lines per module** (a ceiling, not a target).
- [ ] No `;` multi‑statement lines.
- [ ] **No comments. No docstrings.** (Naming and types must carry all meaning.)

### Type‑checking (§3.4)
- [ ] `mypy --strict game` is clean (errors heavily penalised).
- [ ] **Annotate every attribute explicitly** in the class body.
- [ ] **Constructors via `__new__`**; **never define `__init__`** anywhere.
- [ ] **No `Any`, no `object`, no `Callable[..., T]`** (ellipsis form). No `# type: ignore`.

### Allowed imports only (§3.5)
```
typing, types, collections.abc, abc, numbers
collections, heapq, array, bisect, graphlib
dataclasses, enum
fractions, decimal, math, cmath, random
re, string, unicodedata
datetime, zoneinfo, calendar
contextlib, functools, itertools, operator, weakref, uuid
```
**Forbidden functions** (this is a critical list — it shapes the design):
- File system: `open`. CLI: `print`, `input`. Code exec: `compile`, `exec`, `eval`.
- **Object internals: `dir`, `globals`, `locals`, `vars`, `getattr`, `setattr`,
  `hasattr`, `delattr`.**

### Encapsulation (§2.2)
- [ ] **No public attributes.** All state private (`__x`) or protected (`_x`),
      exposed via read‑only `@property`.
- [ ] No class attributes for defaults; if used, non‑public + `ClassVar`.
- [ ] Public module variables must be **`UPPERCASE` + `Final`**.
- [ ] Read‑only properties must not hand back mutable internals (return copies,
      `tuple`, `frozenset`, `MappingProxyType`, or a read‑only `Protocol` view).

### Validation (§2.3)
- [ ] Dynamically validate every public method's arguments.
- [ ] Dynamically validate game **staging** (right action, right phase, right order).
- [ ] **Validate first** — all checks at the top of the method, before any mutation.

---

## 3. Style & idiom contract (from `SESSION.md` + Python 3.14)

The session transcript shows exactly how the professor expects idiomatic code to
look. We adopt all of it, **except** the two items in §3.3.

### 3.1 Idioms to reproduce
- **`__new__` constructors** with the explicit shape:
  ```python
  class Boat:
      __owner: ClanColor
      __position: SpaceId
      def __new__(cls, owner: ClanColor, position: SpaceId) -> Self:
          self = super().__new__(cls)
          self.__owner = owner
          self.__position = position
          return self
  ```
- **`__slots__` + explicit body annotations** on every class. Mixins own
  `__weakref__` only where they sit at the top of a hierarchy; collapse mixins
  into a single slotted base chain to avoid the "multiple bases with slots"
  error the professor hit in `SESSION.md`.
- **Private `__attr` (name‑mangled) + public `@property` getters.** Protected
  `_helper()` for subclass‑internal sharing (e.g. `_init_base`, `_new`).
- **PEP 695** type parameters and aliases: `class Graph[N]: ...`,
  `type SpaceId = int`, `type Listing = Draft | Active | ...`.
- **PEP 649** lazy annotations: never stringify annotations (Python 3.14).
- **`Literal` tags + tagged unions + `match`** for state discrimination.
- **`TypedDict`** (`total=False`/`total=True`) + **`Unpack`** for structured kwargs.
- **`@dataclass(frozen=True, slots=True)`** for immutable value objects;
  **`enum.Enum`/`IntEnum`** for fixed sets; `Protocol` for read‑only views;
  `MappingProxyType` for read‑only dict exposure.
- **Generic, reusable data structures** (the session built a
  `WithdrawableStack[T: Hashable]`); we do the same — see §11.
- **Behavioural patterns wired explicitly**: State (transition methods),
  Memento (`info`/`set`/`undo`), Observer (`on_*` registries), Factory.
- **Construction gating** via a `Lock` utility + `@lock.is_set` decorator and a
  `with lock.set():` context manager, so domain objects can only be built from
  inside their owning module.

### 3.2 Decisions inherited from the session
- Integer money/points instead of `Decimal` (the game uses whole gold/VP/mana/
  fish). `fractions.Fraction` only if an exchange ever needs exact ratios.
- Mixins for cross‑cutting concerns (`Perishable` → staleness after a state
  transition; `Lockable` → freeze transitions while observers fire).
- Read‑only `Protocol` "views" + `MappingProxyType` to expose collections safely.

### 3.3 Two deliberate deviations from `SESSION.md` (the brief overrides it)
1. **No `hasattr`/`getattr`.** The session's `Perishable.not_stale` and
   `Lockable.not_locked` test `hasattr(self, "_Perishable__is_stale")`. That is
   **forbidden here** (§2, object‑internals ban). Replacement design:
   > Every flag is a real slot, **always initialised in `__new__`** to a
   > definite `bool` (e.g. `self.__stale = False`), and checked **directly**
   > (`if self.__stale: raise StaleError(...)`). "Absence means fresh" becomes
   > "the slot is `False`". This is cleaner *and* compliant.
2. **No comments, no docstrings.** The session uses `# Publish‑Subscribe Pattern`
   section headers and method docstrings. **Both are banned** in the submission
   (§3.3). All patterns are documented **only** in `README.md` (§2.4 of the
   brief is explicit: marks are awarded *only* for README documentation). Code
   communicates through precise names and types alone.

Also note: `@dataclass` synthesises an `__init__`. The brief endorses dataclasses
(§2.1) yet bans hand‑written `__init__` (§3.4). We read "do not *define* `__init__`"
as "do not hand‑write one"; a `@dataclass(frozen=True, slots=True)` is the
intended, endorsed exception. Where we want zero ambiguity for a plain record we
prefer `typing.NamedTuple` (immutable, hashable, no `__init__` authored by us).

---

## 4. Scope: what we implement (requirement §1.1 lets us simplify)

The full game is large (asymmetric clan boards, 10 guides, temples, spirits,
race/score/bonus/fish cards, 2‑player neutral settlements…). The 3000‑LOC ceiling
**forces** a simplification. We implement a **coherent, fully‑working core** and
document the rest as out of scope.

### 4.1 In scope (the "Core")
- **2–4 players**, 4 clans (Crocodile/blue, Turtle/green, Frog/red, Salamander/
  yellow), **normal (symmetric) clan board** only.
- **4 rounds × 3 phases** (Income → Turns → Maintenance) + final scoring, as a
  **State machine**.
- **Swamp board** modelled as a generic **graph of spaces** (water / spirit /
  settlement‑slot / temple), built by a **Builder** — *not* a pixel‑accurate hex
  reproduction. Islands are connected components computed with **Union‑Find**.
- **Resources**: gold, mana gems, fish; an unlimited **Bank** + per‑clan
  **Wallet**. Plus the anytime exchanges (2 mana→neutral worker, worker→mana).
- **Pieces**: clan workers + neutral workers, boats, settlement tiles, spirit
  tiles, temple tiles; a per‑clan **sailing track**.
- **Guides**: the 10 guide cards as **flyweight data** + their abilities as
  **Strategy** objects (income/turn/pass hooks). Drafting + initiative turn order.
- **All 7 actions + Pass**, each a **Command** built on a **Template Method**
  skeleton and validated by a **Chain of Responsibility**:
  Fish, Build Settlement, Sail, Trade (boat actions); Improve Sailing, Celebrate,
  Add Spirit Worship (ground actions); Pass.
- **Scoring**: live VP track (**Observer**) + end‑game island scoring + leftover
  resources + **2 Score cards** as **Strategy** objects.
- **Encapsulation**: read‑only **Proxy** views for everything `Game` exposes.

### 4.2 Out of scope (documented, not stubbed — §1.1 forbids stub code)
Advanced/asymmetric clan boards & Salamander tiles; the Leader blocking piece;
2‑player neutral settlements; full Race‑card race; all four Round‑Bonus tiers;
the precise printed hex geometry; fish‑card per‑round colour decks beyond a single
"fish of the season" marker. Each omission is a *clean cut*, never a stub.

> **LOC budgeting:** §6 gives a module budget that lands the Core under 3000.
> If it runs hot, cut in this order: Race cards → Round‑bonus tiers → Score‑card
> variety (keep 2 of 6) → temple variety → guides (keep 6 of 10).

---

## 5. Architecture overview

```
                         ┌───────────────────────────────────────────┐
   user / server  ─────► │                  Game                      │   ← Facade
   (only imports         │  (facade.py)  public properties + methods  │   (the ONLY
    this class)          └───────────────────────────────────────────┘    class users
                              │ delegates (Mediator: nobody below holds    instantiate)
                              │ refs to siblings; Game wires them)
        ┌─────────────┬───────┴───────┬───────────────┬──────────────┐
        ▼             ▼               ▼               ▼              ▼
   ┌─────────┐  ┌──────────┐    ┌──────────┐    ┌──────────┐   ┌──────────┐
   │ Engine  │  │  Swamp   │    │ Player×N │    │  Guides  │   │  Bank    │
   │rounds/  │  │ board    │    │ (clan)   │    │ + cards  │   │ resources│
   │phases   │  │ graph+   │    │ wallet,  │    │ Strategy │   │ flyweight│
   │ State   │  │ islands  │    │ pieces,  │    │ Flyweight│   └──────────┘
   │ machine │  │ Composite│    │ folder,  │    └──────────┘
   └────┬────┘  └────┬─────┘    │ score    │
        │            │          └────┬─────┘
        │      ┌─────┴──────┐        │
        │      │ Actions    │ Command + Template Method + Chain of Responsibility
        │      │ (Fish/Build│◄───────┘  (a turn = build a Command, validate via the
        │      │ /Sail/Trade│            chain, execute against board+player+bank,
        │      │ /Improve/  │            emit a Memento for undo, fire Observers)
        │      │ Celebrate/ │
        │      │ AddSpirit/ │
        │      │ Pass)      │
        │      └────────────┘
        ▼
   ┌──────────────────────────────────────────────────────────────────┐
   │ structures.py — generic, reusable: Graph[N], UnionFind[T],         │
   │ Bag[T] (multiset), Stack[T]   |   core.py — enums, errors, mixins  │
   │ (Observable[T], Perishable, Lockable, construction Lock)           │
   └──────────────────────────────────────────────────────────────────┘
```

**Layering rule:** dependencies point *down only*. `structures.py`/`core.py`
depend on nothing in the package; domain modules depend on those; `engine`/
`actions` depend on domain; `facade` depends on everything and is depended on by
nobody but `__init__`. This keeps imports acyclic (the session hit a circular
import; we avoid it structurally, with `TYPE_CHECKING`‑only imports for pure
annotations where a cycle would otherwise form).

---

## 6. Module layout & LOC budget (flat `game/` package)

| # | Module | Responsibility | Budget (LOC) |
|---|---|---|---|
| 1 | `__init__.py` | `from .facade import Game`; `__all__ = ["Game"]` | 5 |
| 2 | `core.py` | Enums (`ClanColor`, `Resource`, `Phase`, `ActionKind`, `GuideKind`, `SpaceKind`), type aliases, error hierarchy, mixins (`Observable[T]`, `Perishable`, `Lockable`), construction `Lock` | 360 |
| 3 | `structures.py` | Generic reusable: `Graph[N]`, `UnionFind[T]`, `Bag[T]`, `Stack[T]` | 320 |
| 4 | `board.py` | `Space`, `Island` (Composite), `Swamp` (graph+islands+placement legality), `BoardView` Proxy | 480 |
| 5 | `pieces.py` | `Boat`, `Worker`/`NeutralWorker`, `SettlementTile`, `SpiritTile`, `TempleTile`; `ClanFactory` (Abstract Factory); `Wallet`/`Bank` over `Bag` | 430 |
| 6 | `guides.py` | `GuideCard` data (Flyweight) + `GuideAbility` Strategies; `ScoreCard` Strategies; draft/turn‑order helpers | 420 |
| 7 | `actions.py` | `Action` (Command) hierarchy; `BoatAction`/`GroundAction` Template Methods; concrete 7+Pass; validator **Chain**; `ActionMemento` | 490 |
| 8 | `players.py` | `Player` aggregate (wallet, pieces, sailing track, settlement folder, score), `PlayerView` Proxy | 320 |
| 9 | `engine.py` | Phase **State** machine, `TurnManager` (Mediator), income/maintenance, end‑game scoring **Visitor** | 470 |
| 10 | `facade.py` | `Game` Facade + `GameBuilder` (Builder) | 290 |
| | **Total** | | **~3585 → trim to ≤3000 by §4.2 cut‑list** |

The raw sum exceeds 3000 on purpose: it is the *design* surface. The realised
Core lands under 3000 by applying §4.2 (most cheaply: drop race cards and three
round‑bonus tiers entirely, hold guides at 6, score cards at 2). Each module
stays under its 500 ceiling with margin.

---

## 7. The `Game` façade — public API

`Game` exposes **complete information** (read‑only) and **every legal move**
(validated). It holds no game logic itself beyond delegation + staging checks —
"implementing most logic in the Game class is unlikely to earn high marks" (§2.1).

### 7.1 Construction (Builder behind the Façade)
```python
class Game:
    def __new__(
        cls,
        clans: Sequence[ClanColor],          # 2..4 distinct colours, turn-seed order
        *,
        seed: int | None = None,             # deterministic shuffles (random module)
        board: BoardKind = BoardKind.STANDARD # which built-in topology the Builder uses
    ) -> Self: ...
```
The user passes only builtins/enums. `__new__` drives a private `GameBuilder`
that assembles board, banks, players, guide pool, and card rows. No other class
is constructed by the user.

### 7.2 Read‑only information (properties → Proxy/immutable)
```python
@property round_number(self) -> int                         # 1..4
@property phase(self) -> Phase                              # INCOME | TURNS | MAINTENANCE | OVER
@property is_over(self) -> bool
@property clans(self) -> tuple[ClanColor, ...]
@property players(self) -> Mapping[ClanColor, PlayerView]   # MappingProxyType
@property turn_order(self) -> tuple[ClanColor, ...]         # by initiative (asc)
@property current_player(self) -> ClanColor | None          # whose turn (TURNS phase)
@property board(self) -> BoardView                          # read-only Protocol
@property guide_offer(self) -> tuple[GuideView, ...]        # face-up guides to draft
@property score_cards(self) -> tuple[GuideView, ...]        # active end-game scorers (view)
@property scores(self) -> Mapping[ClanColor, int]           # live VP
@property winners(self) -> frozenset[ClanColor]            # only meaningful when is_over
@property legal_actions(self) -> frozenset[ActionKind]      # what current_player may do now
```
Every collection is returned as `tuple`, `frozenset`, or `MappingProxyType`; every
sub‑object (`PlayerView`, `BoardView`, `GuideView`) is a **read‑only Protocol**
(Proxy pattern). No setter is ever exposed.

### 7.3 Setup moves (pre‑round, staged)
```python
def draft_guide(self, clan: ClanColor, guide: GuideKind) -> None
def place_starting_settlement(self, clan: ClanColor, space: SpaceId) -> None
```

### 7.4 Turn moves (validated; one per turn except exchanges)
Direct, fully‑typed methods are the public surface (keeps the Façade bulletproof:
the user never holds a Command instance). Internally each builds the matching
**Command**.
```python
# Boat actions — 'moves' maps each of your boats to its destination space.
def fish(self, clan: ClanColor, moves: Mapping[BoatId, SpaceId]) -> None
def build_settlement(self, clan: ClanColor, moves: Mapping[BoatId, SpaceId]) -> None
def sail(self, clan: ClanColor, moves: Mapping[BoatId, SpaceId]) -> None
def trade(self, clan: ClanColor,
          moves: Mapping[BoatId, SpaceId],
          placements: Mapping[BoatId, Sequence[SpaceId]]) -> None   # fish onto adj. settlements

# Ground actions
def improve_sailing(self, clan: ClanColor) -> None
def celebrate(self, clan: ClanColor, island: IslandId) -> None
def add_spirit_worship(self, clan: ClanColor, space: SpaceId) -> None

# Worker source for an action space: which worker token to spend.
#   (overloaded so a clan worker or a neutral worker can be named precisely)
@overload
def use_worker(self, clan: ClanColor, *, neutral: Literal[True]) -> None
@overload
def use_worker(self, clan: ClanColor, *, neutral: Literal[False] = ...) -> None

# Anytime exchanges
def exchange_mana_for_neutral(self, clan: ClanColor) -> None   # 2 mana -> 1 neutral worker
def exchange_worker_for_mana(self, clan: ClanColor) -> None    # 1 worker -> 1 mana

# End the turn
def pass_turn(self, clan: ClanColor) -> None

# Optional headline: undo the last applied command this turn (Command + Memento)
def undo(self) -> None
```

### 7.5 Why this is a Façade (requirement §1.2)
- The user imports and instantiates **only** `Game`.
- All sub‑components (`Swamp`, `Player`, `Boat`, `GuideCard`, `Action`, …) are
  *used* but reached **only** through `Game`'s properties/methods.
- The Façade performs **staging validation** (right phase, right player, action
  legal *now*) then delegates the heavy lifting to the right sub‑component — it is
  a thin coordinator (Mediator), not a god object.

---

## 8. Domain model (private state, exposed via views)

All attributes are private + annotated + slotted. Shown below as
`name: type` (the `__` mangling and `@property` getters are implied per §3.1).

### 8.1 `core.py`
```python
class ClanColor(Enum):  CROCODILE="blue"; TURTLE="green"; FROG="red"; SALAMANDER="yellow"
class Resource(Enum):   GOLD; MANA; FISH
class Phase(Enum):      INCOME; TURNS; MAINTENANCE; OVER
class SpaceKind(Enum):  WATER; SPIRIT; SETTLEMENT; TEMPLE
class ActionKind(Enum): FISH; BUILD; SAIL; TRADE; IMPROVE_SAILING; CELEBRATE; ADD_SPIRIT; PASS
class GuideKind(Enum):  LEADER; SAILOR; FISHERMAN; MONK; STORYTELLER; BUILDER; \
                        WARRIOR; MERCHANT; ARTIST; WISEMAN

type SpaceId = int
type IslandId = int
type BoatId = int
type WorkerId = int

# Error hierarchy — no authored __init__; message passed straight to Exception.
class GameError(Exception): ...
class IllegalSetup(GameError): ...
class IllegalMove(GameError): ...
class WrongPhase(IllegalMove): ...
class NotYourTurn(IllegalMove): ...
class InsufficientResources(IllegalMove): ...
class OccupiedSpace(IllegalMove): ...
class IllegalPlacement(IllegalMove): ...      # joins islands / blocks boat or temple
class StaleError(GameError): ...
class LockedError(GameError): ...

# Mixins (no hasattr — flags are real, always-initialised slots).
class Observable[T]:                      # Observer infrastructure
    __subs: list[Callable[[T], None]]     # precise Callable, never Callable[..., T]
    def _subscribe(self, cb: Callable[[T], None]) -> None
    def _emit(self, event: T) -> None
class Perishable:                         # set stale on transition; guard methods
    __stale: bool                         # initialised False in __new__
    def _make_stale(self) -> None
    @staticmethod def not_stale[**P, R](m: Callable[Concatenate[Perishable, P], R]) -> ...
class Lockable:                           # freeze transitions during observer dispatch
    __locked: bool
    def _lock(self) -> None
    def _unlock(self) -> None
    @staticmethod def not_locked[**P, R](...) -> ...
class Lock:                               # module-construction gate (contextmanager)
    __set: bool
    @contextmanager def set(self) -> Iterator[None]
    def is_set[**P, R](self, fn: Callable[P, R]) -> Callable[P, R]
```

### 8.2 `board.py` — the Swamp (Composite + Proxy)
```python
class Space:                              # a node in the swamp graph (value-ish, but has logic)
    __id: SpaceId
    __kind: SpaceKind
    __fish_season: bool                   # carries 'fish of the season' (FISH targets)
    __boat: BoatId | None                 # at most one boat ends here
    __settlement: SettlementTile | None   # built tile, if a SETTLEMENT slot
    __fish_stack: Stack[ClanColor]        # fish pieces stacked here (Trade), max 3
    @property kind / occupied / buildable ...

class Island:                            # Composite: a connected group of land spaces
    __spaces: frozenset[SpaceId]
    __has_totem: bool
    @property spirit_count(self) -> int   # spirit spaces on the island (build cost + scoring)
    def settlements_of(self, clan) -> int

class Swamp:
    __graph: Graph[SpaceId]               # generic adjacency (water+land), reusable structure
    __spaces: dict[SpaceId, Space]
    __union: UnionFind[SpaceId]           # island membership / "don't join islands" check
    __totem: SpaceId
    # queries (Iterator pattern via generators):
    def reachable(self, start: SpaceId, steps: int) -> Iterator[SpaceId]   # BFS ≤ range, water-only
    def islands(self) -> Iterator[Island]
    def island_of(self, space: SpaceId) -> IslandId
    # legality (used by the validator chain):
    def would_join_islands(self, space: SpaceId) -> bool
    def would_block(self, space: SpaceId) -> bool        # boat or temple access
    # mutation is *protected* (only actions, via the construction Lock, may call):
    def _build(self, space, tile) -> None
    def _add_spirit(self, space, tile) -> None
```
`BoardView` is a `Protocol` exposing only the query side, returned by
`Game.board`. The dict/graph internals are never handed out raw.

### 8.3 `pieces.py`
```python
class Wallet:                            # per-clan resources, validated
    __bag: Bag[Resource]                  # generic multiset (reusable structure)
    def _add(self, r: Resource, n: int) -> None
    def _spend(self, r: Resource, n: int) -> None   # raises InsufficientResources first
    @property gold / mana / fish (self) -> int

class Bank:                              # unlimited common reserve (Flyweight source)
    def draw(self, r, n) / def deposit(self, r, n) -> None

@dataclass(frozen=True, slots=True)
class GuideCard:                         # Flyweight: shared immutable intrinsic data
    kind: GuideKind; initiative: int; settlement_value: int; sailing_range: int
    # ability is a Strategy object held in the GUIDES registry (see guides.py)

class Boat:        __id; __owner: ClanColor; __position: SpaceId
class Worker:      __id; __owner: ClanColor | None      # None == neutral (axolotl)
class SettlementTile:  __owner: ClanColor; __bonus: TileBonus | None
class SpiritTile / TempleTile: small frozen records (NamedTuple/dataclass)

class ClanFactory:                       # Abstract Factory: a family of pieces per colour
    def make_boats(self) -> tuple[Boat, ...]
    def make_workers(self) -> tuple[Worker, ...]
    def make_settlements(self) -> tuple[SettlementTile, ...]
    def make_sailing_track(self) -> SailingTrack
```

### 8.4 `players.py`
```python
class SailingTrack:
    __value: int                          # additive to guide sailing_range
    def _advance(self) -> int             # returns VP gained by the step
class Player:
    __color: ClanColor
    __wallet: Wallet
    __boats: dict[BoatId, Boat]
    __workers_available: int
    __neutral_available: int
    __supply: Stack[SettlementTile]       # the 4 clan-board tracks, simplified to a supply
    __sailing: SailingTrack
    __guide: GuideCard | None             # this round's drafted guide
    __passed: bool
    __folder: SettlementFolder            # Observer-synced view of own settlements by island
    __score: int
    # public read-only via PlayerView Protocol: color, gold, mana, fish, score,
    #   sailing_value, guide (GuideView), boats (tuple of read-only boat views),
    #   workers_available, passed, settlements (mapping island->count).
```

### 8.5 `engine.py`
```python
class PhaseState(ABC):                    # State pattern
    @abstractmethod def legal(self) -> frozenset[ActionKind]
    @abstractmethod def advance(self, game) -> PhaseState
class IncomePhase(PhaseState): ...        # apply income strategies, then -> TurnsPhase
class TurnsPhase(PhaseState): ...         # owns TurnManager; -> MaintenancePhase when all passed
class MaintenancePhase(PhaseState): ...   # collect workers, swap guides, reorder; -> next Income
class GameOver(PhaseState): ...           # absorbing; legal() == empty
class TurnManager:                        # Mediator over players<->board<->bank
    __order: tuple[ClanColor, ...]
    __cursor: int
    def current(self) -> ClanColor
    def advance(self) -> None             # skip passed players; round ends when all passed
class EndGameScorer:                      # Visitor over islands/settlements + score-card Strategies
    def score(self, game) -> Mapping[ClanColor, int]
```

---

## 9. Encapsulation & validation strategy (requirement §1.4, §2.2, §2.3)

This is the most heavily‑weighted axis. Four mechanisms, layered:

1. **Private state + read‑only views (Proxy).**
   Every attribute is `__private` and slotted; nothing public is writable.
   Collections leave the boundary only as `tuple`/`frozenset`/`MappingProxyType`
   or behind a read‑only `Protocol` (`BoardView`, `PlayerView`, `GuideView`).
   → Directly answers "Read‑only properties expose objects which can themselves
   be illegally modified."

2. **Construction gating (Lock + decorator).**
   Domain constructors are wrapped with `@_lock.is_set`; they raise `LockedError`
   unless called inside `with _lock.set():`, which only the owning module's
   factories/transitions do. → Enforces "users instantiate only `Game`" at runtime.
   (Module‑level lock is safe across concurrent `Game` instances: it is only ever
   held across a *synchronous* construction block, so instances never interleave.)

3. **Staging via the State machine + turn cursor.**
   `Game` first asks the current `PhaseState.legal()` and the `TurnManager`
   whether this `(clan, action)` is allowed *now*; wrong phase → `WrongPhase`,
   wrong player → `NotYourTurn`, illegal action kind → `IllegalMove`. → Answers
   "Methods can be successfully invoked … in illegal order."

4. **Validate‑first inside every action (Chain of Responsibility).**
   Each `Action.validate()` runs an ordered chain of single‑rule links *before*
   any mutation. Example (Build): `WorkerAvailable → SlotChosenFree → BoatsCanReach
   → PlacementLegal(no‑join, no‑block) → CanAfford`. The first failing link raises
   the specific `IllegalMove` subclass; only if the whole chain passes does
   `execute()` mutate state. → Answers "Methods can be invoked with illegal
   parameters" and "Validate at the start, before any computation."

**Static prevention where feasible.** Beyond runtime checks, types make many
illegal calls *fail to type‑check*: `Literal`/`Enum` parameters (no free‑form
strings), no public setters at all, `@overload` on `use_worker` so the
clan/neutral distinction is type‑level, and tagged unions so `match` is
exhaustive (mypy `--strict` flags a missing case).

**Error model.** One `GameError` root; specific subclasses (§8.1) carry a plain
message via inherited `Exception` (no authored `__init__`). Callers can catch
broadly (`GameError`) or precisely (`InsufficientResources`).

---

## 10. Design‑pattern map (requirement §2.4 — documented for the README)

Patterns must be *natural*, not forced. **Core** = load‑bearing in the design;
**Supporting** = genuine but smaller; we will only claim what we actually use.

### Core
| Pattern | Category | Where / why |
|---|---|---|
| **Facade** | Structural | `Game` is the sole entry point; hides board/engine/players/cards. |
| **State** | Behavioural | `PhaseState` (Income/Turns/Maintenance/Over); per‑round behaviour switch; also `Perishable` stale‑after‑transition. |
| **Command** | Behavioural | Each turn action is an `Action` object: `validate()`+`execute()`; uniform handling, enables undo. |
| **Template Method** | Behavioural | `BoatAction.execute()` skeleton (validate → place worker → per‑boat move+`_effect` → notify); `Fish/Build/Sail/Trade` fill `_effect`. |
| **Chain of Responsibility** | Behavioural | `validate()` is an ordered chain of one‑rule validators; reused across actions. |
| **Strategy** | Behavioural | Guide abilities (income/turn/pass) and Score‑card scorers are interchangeable algorithms. |
| **Observer** | Behavioural | `Observable[T]` pub/sub: VP/score track, settlement folder auto‑sync, frontend hooks. |
| **Memento** | Behavioural | `ActionMemento` snapshots minimal state so `Game.undo()` reverts the last command. |
| **Factory Method / Abstract Factory** | Creational | `Game` makes `Player`s; `ClanFactory` makes the per‑colour family (boats/workers/tiles/track). |
| **Builder** | Creational | `GameBuilder` assembles the initial board + setup behind `Game.__new__`. |

### Supporting
| Pattern | Category | Where / why |
|---|---|---|
| **Composite** | Structural | `Island` composes `Space`s; `Swamp` composes `Island`s; scoring treats them uniformly. |
| **Proxy** | Structural | Read‑only `BoardView`/`PlayerView`/`GuideView` + `MappingProxyType` protect exposed state. |
| **Decorator** | Structural | Round‑bonus tiles wrap a `Action` to tweak it for one turn (+range, pay‑less); plus the `@not_stale`/`@is_set` function decorators. |
| **Flyweight** | Structural | `GuideCard`/tile descriptors are shared immutable intrinsics; gold/mana/fish are counts, not objects. |
| **Mediator** | Behavioural | `TurnManager`/`Game` coordinate players↔board↔bank so siblings never reference each other. |
| **Iterator** | Behavioural | Generators for BFS reachability, island traversal, cyclic turn order. |
| **Visitor** | Behavioural | `EndGameScorer` visits islands/settlements; score‑card strategies as visit operations. |
| **Prototype** | Creational | Tile templates cloned from a registry; `Memento`/snapshot ties in. |

> Singleton is **excluded** by the brief and by requirement 3 (multiple `Game`s).

---

## 11. Reusable generic data structures (requirement §2.5 — README documented)

Each is **generic** (parametrically polymorphic, PEP 695) and **reusable** (no
game concept inside). Documented in README; used by the domain.

```python
class Graph[N]:                          # undirected adjacency; the swamp topology
    __adj: dict[N, set[N]]
    def add_node(self, n: N) -> None
    def add_edge(self, a: N, b: N) -> None
    def neighbours(self, n: N) -> Iterator[N]
    def bfs(self, start: N, max_depth: int) -> Iterator[tuple[N, int]]
    def __contains__(self, n: N) -> bool
    def __len__(self) -> int

class UnionFind[T]:                       # island connectivity / join-detection
    __parent: dict[T, T]; __rank: dict[T, int]
    def find(self, x: T) -> T
    def union(self, a: T, b: T) -> None
    def connected(self, a: T, b: T) -> bool
    def components(self) -> Iterator[frozenset[T]]

class Bag[T]:                             # multiset; wallet/bank counts, fish stacks
    __counts: Counter[T]                  # collections.Counter
    def add(self, item: T, n: int = 1) -> None
    def remove(self, item: T, n: int = 1) -> None   # raises on overdraw
    def __getitem__(self, item: T) -> int
    def __contains__(self, item: T) -> bool
    def __len__(self) -> int
    def __iter__(self) -> Iterator[T]

class Stack[T]:                           # temple-tile stacks, settlement fish stacks
    __items: list[T]
    def push(self, item: T) -> None
    def pop(self) -> T
    def peek(self) -> T
    def __len__(self) -> int
    def __bool__(self) -> bool
```
(Optional `WithdrawableStack[T: Hashable]` — straight from `SESSION.md` — if a
remove‑from‑middle stack is needed; otherwise omitted to save LOC.)

---

## 12. Advanced language features (requirement §2.6 — README documented)

- **Generics (PEP 695):** all of §11; `Observable[T]`; `Concatenate`/`ParamSpec`
  in mixin decorators.
- **Structural typing:** `Protocol` views (`BoardView`, `PlayerView`,
  `GuideView`, `GuideAbility`, `ScoringStrategy`).
- **Method overloads:** `@overload` on `use_worker` (clan vs neutral) and on a
  `board.space()` accessor.
- **Dunder methods:** `__iter__`, `__len__`, `__contains__`, `__getitem__`,
  `__bool__`; `__lt__` on guide for initiative sort.
- **Iterators / generators / comprehensions:** BFS, island traversal, turn cycle,
  scoring sums.
- **Function objects / callables:** Commands and Strategies as callables;
  `functools.reduce`/`partial`, `operator.attrgetter`, `itertools.groupby`/
  `combinations`.
- **Tagged unions + `match`:** `SpaceKind`/`ActionKind`/`Phase` discriminated
  unions, exhaustively matched (mypy‑checked).
- **`TypedDict` + `Unpack`:** structured optional inputs (e.g. trade placements,
  setup options); `Final`/`ClassVar`; `Self`; `@dataclass(frozen, slots)`; ABCs.

---

## 13. Game rules captured (traceability to the rulebook)

A condensed but complete record of the modelled rules, so the implementation can
be checked against the source.

### 13.1 Structure
- 2–4 players; 4 rounds; each round = **Income → Turns → Maintenance** (Maintenance
  skipped after round 4 → End of Game). Most VP wins; **ties are shared**.

### 13.2 Setup (modelled subset)
- Choose clan boards (normal side). Each clan starts: **20 gold, 1 mana, 3 fish**,
  3 workers in reserve (+2 pre‑placed on worker‑granting tiles), 3 boats on
  boat‑granting tiles, sailing piece on track, score marker at 0 VP.
- **Draft starting guide** (clockwise from last to "play in the mud"); a fish is
  put on each un‑drafted guide. **Turn order** = ascending **initiative**.
- **Place 3 starting settlements** per clan, in turn order. Placement rules:
  (1) any water space adjacent to a spirit space; (2) the 3 must be on **3
  different islands** / no island where you already have presence;
  (3) must **not join two islands**; (4) a tile that comes with a boat places that
  boat on top.

### 13.3 Income phase
- Each clan gains resources from **unlocked** clan‑board income spaces (a
  settlement must have been built over the entrance in a prior round) + guide
  income skill. Round 1: only **1 mana** (from the starting settlement).
  Simultaneous.

### 13.4 Turns phase — one action per turn
**Anytime exchanges:** 2 mana → 1 neutral worker (if available); 1 worker → 1 mana.
Before ending a turn, check Race objectives (Core: optional).

**Worker placement:** boat/ground actions require placing one available worker
(clan or neutral) on a free action space; **never occupy an occupied space**; some
spaces cost mana or grant rewards.

**Boat actions** (each available boat moves ≤ **Sailing Range** = guide range +
sailing‑track value + bonuses, water‑only, may pass through but not end on another
boat, then **must perform the action** where it stops):
- **FISH:** end on a "fish of the season" space; gain **fishing‑capacity** fish per
  boat (clan board + Fisherman guide; +bonus tiles).
- **BUILD SETTLEMENT:** end on a free space adjacent to an island; build one tile
  there unless it **joins ≥2 islands** or **blocks a boat/temple**. Cost =
  **3 gold × (spirit spaces on that island) + guide Settlement Value**; tile bonus
  applied immediately; a boat‑bearing tile places that boat.
- **SAIL:** move to any free water space (the only move without a second action);
  3–4‑player map adds **+2** movement per boat; the only way to reach **Temple**
  spaces (movement ends; take top temple tile + reward; one of each temple type per
  game).
- **TRADE:** end adjacent to ≥1 settlement; place reserve fish on adjacent tiles
  (≤3 stacked). On **another clan's** tile, gain gold by stack position **4/3/2**;
  on your **own** colour, no gold now (VP via Celebrate); **+1 gold** per fish if
  the island holds the **Island Totem**.

**Ground actions:**
- **IMPROVE SAILING:** sailing piece +1 right; immediately gain that step's VP;
  the new value adds to range thereafter.
- **CELEBRATE:** pick an island; **+1 VP** per settlement‑with‑fish on it (any
  colour); **+3 VP** if it holds the Totem; then **each** player gains **+1 VP**
  per fish on **their own** colour tiles there; finally **all fish on the island
  return to the bank**.
- **ADD SPIRIT WORSHIP:** place a spirit tile on an empty space adjacent to a
  settlement/spirit tile; not on a Totem island; must not join ≥2 islands or block
  a settlement/temple; then **move the Totem** to the new spirit tile.

**Pass:** take a Round‑Bonus tile; collect guide pass bonus; return guide and draw
a different one for next round (taking any fish on it); flip it as "done". The
**last** to pass also places the round's spirit tile (Add‑Spirit rules). The last
player may take several solo turns while others have passed.

### 13.5 Maintenance phase
Collect workers; neutral workers → bank; flip the round's fish card; put a fish on
each un‑drafted guide; reveal new guides; recompute turn order by new initiatives.

### 13.6 Guide cards (Initiative / Settlement Value / Sailing Range / Skill)
```
LEADER     1 / 7 / 5  income: reserve one action space for yourself (blocking piece)
SAILOR     2 / 6 / 5  income: sailing +1 (+VP)
FISHERMAN  3 / 5 / 4  turn:   +fishing capacity per boat
MONK       4 / 4 / 4  income: +2 mana
STORYTELLER5 / 3 / 3  pass:   +3 VP per temple tile held
BUILDER    6 / 3 / 3  turn:   exclusive BUILD action space
WARRIOR    7 / 3 / 2  income: +2 neutral workers
MERCHANT   8 / 2 / 2  income: +8 gold
ARTIST     9 / 2 / 1  pass:   +3 VP then CELEBRATE
WISEMAN   10 / 1 / 1  pass:   +3 VP per island where you (incl. tie) lead in settlements
```
Each Skill is a **Strategy** with an `apply(game, player)` hook bound to the right
phase (income / turn / pass).

### 13.7 End‑game scoring
1. **Islands:** per island, each clan scores `(its settlements on the island) ×
   (spirit spaces on the island)`.
2. **Score cards (2 active)** — each a Strategy; the six possible cards:
   - `n²` of the clan's **largest connected** settlement group.
   - **5 VP** per settlement next to a **Temple** space.
   - **3 VP** per island where the clan leads (incl. tie) in settlements.
   - **5 VP** per island where the clan has **exactly 1** settlement.
   - **4 VP** per settlement on the **largest** island(s).
   - **4 VP** per settlement on the **smallest** island(s).
3. **+1 VP** per fish still on the clan's settlements.
4. **+1 VP** per mana gem in reserve.
5. **+1 VP** per **10 gold** in reserve.

### 13.8 Other content (data‑driven; Core keeps a subset)
- **Round‑Bonus tiles** (earned on Pass, usable once later; multiple per turn) —
  Round I: +3/+2 sailing range, +1 fishing, −3/−2 build cost; Round II: free
  Build/Fish/Trade/Celebrate/Improve action; Round III: exchanges
  (1 mana→neutral, 4 gold→neutral, 6 gold→2 mana, 2 mana→4 fish, 3 mana→16 gold);
  Round IV: immediate VP. Implemented as **Decorators** over actions / exchange
  helpers. *(Core: a thin subset.)*
- **Race cards** (first to achieve marks VP): ≥1 settlement per island; ≥5 on one
  island; ≥2 on five islands; reach +4 sailing; ≥3 on three islands; unlock 2
  workers; fish ≥7 in one turn; ≥30 gold in one Trade. *(Core: optional.)*

---

## 14. Worked flow — `Game.build_settlement` end to end

Shows the layers cooperating and the validate‑first discipline.

```
Game.build_settlement(clan, moves)                         # facade.py
 ├─ staging: phase is TURNS? current_player is clan?       # State + TurnManager (Mediator)
 │     else raise WrongPhase / NotYourTurn
 ├─ build a BuildSettlement command (Command)              # actions.py
 ├─ command.validate():                                    # Chain of Responsibility
 │     WorkerAvailable(player)                             #   else IllegalMove
 │     ActionSpaceFree(ActionKind.BUILD)                   #   else OccupiedSpace
 │     for each boat in moves:
 │        BoatReaches(swamp, boat, dest, range)            #   BFS ≤ range  → else IllegalMove
 │        DestAdjacentToIsland(swamp, dest)                #   else IllegalPlacement
 │        NotJoinIslands(swamp, dest)                      #   UnionFind   → else IllegalPlacement
 │        NotBlocking(swamp, dest)                         #   else IllegalPlacement
 │     CanAfford(player, 3*spirit_count + guide.value*k)   #   else InsufficientResources
 ├─ command.execute():                                     # Template Method body
 │     snapshot = ActionMemento(...)  ──────────────►  Game caretaker (for undo)   # Memento
 │     place worker on BUILD space     (player._use_worker)
 │     for each boat: swamp._build(dest, player._next_tile())   # under `with _lock.set():`
 │        apply tile bonus; place carried boat if any
 │        player._wallet._spend(GOLD, cost)
 │     player._folder.sync(); player._score change          # Observer fires → scores update
 └─ TurnManager.advance()                                  # next player / end round
```

---

## 15. Example usage (programmatic, no UI)

```python
from game import Game, ClanColor, GuideKind   # only Game is a class; the rest are enums

g = Game([ClanColor.FROG, ClanColor.SALAMANDER, ClanColor.TURTLE], seed=7)

# --- setup ---
for clan in g.turn_order:
    g.draft_guide(clan, _pick(g.guide_offer))          # frontend choice
for clan in g.turn_order:
    for _ in range(3):
        g.place_starting_settlement(clan, _choose(g.board.buildable_starts(clan)))

# --- a turn ---
assert g.phase is Phase.TURNS
me = g.current_player
plan = {boat: dest for boat, dest in _route(g.board, me)}
if ActionKind.BUILD in g.legal_actions:
    g.build_settlement(me, plan)            # raises IllegalMove if anything is illegal
g.pass_turn(me)

# --- information is fully readable, never mutable ---
print_state = g.scores                       # Mapping[ClanColor,int] (proxy) — read only
board = g.board                              # BoardView protocol; no setters exist
# board.spaces[0].kind  -> SpaceKind.WATER   (works)
# board.spaces[0] = ...                       -> TypeError at runtime / mypy error

while not g.is_over:
    ...                                      # drive rounds via the same calls
champions = g.winners                        # frozenset[ClanColor]
```
(`_pick`/`_choose`/`_route` are the *frontend's* concern — not part of the library.)

---

## 16. Submission `README.md` — compliant draft (requirement §3.1)

Plain text only; lists allowed; **no** other Markdown; each section within its word
cap. (Reproduced here so the budget is pre‑checked; the real file lives at
`game/`'s parent on submission.)

> **Design** (≤300 words). Feya's Swamp is exposed through one façade class, Game,
> the only class a user instantiates. Game coordinates five sub‑systems and holds
> no rules itself beyond staging. Swamp models the board as a generic graph of
> spaces; islands are connected components found with union‑find, and an Island
> composite answers spirit‑count and settlement queries. Each Player owns a wallet,
> boats, workers, a sailing track, a settlement supply, a settlement folder, and a
> score; a Bank is the unlimited reserve. Guides carry initiative, settlement
> value, sailing range, and an ability strategy. The Engine runs the round as a
> phase state machine (income, turns, maintenance, over) with a turn manager that
> mediates players, board, and bank. A turn is a command built on a boat/ground
> template; it validates through a chain of single‑rule checks, then executes,
> emitting a memento for undo and notifying observers that update scores and
> folders. Everything Game exposes is a read‑only view, so information is complete
> but immutable. (… responsibilities and interactions continue …)
>
> **Validation** (≤200 words). All state is private and slotted; nothing public is
> writable. Collections leave as tuples, frozensets, or mapping proxies; sub‑objects
> leave behind read‑only protocols. Domain constructors are gated by a lock, so only
> Game's factories build pieces. Staging is enforced by the phase state machine and
> turn cursor: wrong phase, wrong player, or wrong action raises a specific
> GameError. Every action validates first, through an ordered chain, before any
> mutation. Enum and literal parameters, overloads, and exhaustive matches push
> many illegal calls to compile time under mypy strict. (…)
>
> **Object‑oriented Patterns** (≤200 words). Facade (Game); state (phases);
> command (actions); template method (boat/ground skeletons); chain of
> responsibility (validators); strategy (guide abilities, score cards); observer
> (score and folder sync); memento (undo); factory method and abstract factory
> (players, per‑clan pieces); builder (setup). Supporting: composite (island,
> swamp), proxy (views), decorator (round‑bonus tiles), flyweight (guide/tile
> data), mediator (turn manager), iterator (traversals), visitor (scoring). (…)
>
> **Reusable Generic Data Structures** (≤200 words). Graph[N] (undirected
> adjacency with bounded BFS) models the swamp and reachability. UnionFind[T]
> tracks island connectivity and detects illegal island joins. Bag[T] is a
> multiset backing wallets and the bank. Stack[T] backs temple‑tile and fish
> stacks. All are parametric and free of any game concept. (…)
>
> **Advanced Language Features** (≤100 words). PEP 695 generics and aliases;
> protocols for structural views; overloads; dunder methods (iter, len, contains,
> getitem, lt); generators and comprehensions; tagged unions with exhaustive
> match; typed dicts with unpack; frozen slotted dataclasses; abstract base
> classes; Self, Final, ClassVar.

---

## 17. Build & verification plan

Mirror `pyproject.toml` (Python 3.14, `mypy --strict`, `black`), package renamed
`game`:
```
black game                       # format first (LOC counted after black)
mypy --strict game               # must be clean
python -c "from game import Game" # import smoke test
# LOC gate:
#   total = sum(len(list(open(m))) for m in game/*.py) <= 3000
#   each  = len(list(open(m)))                          <= 500
```
A small private test script (kept *outside* the `game` package, since only `game`
is marked) exercises the happy path end to end: build → fish → trade → celebrate →
pass → maintenance → end‑game scoring, asserting VP totals against §13.7.

---

## 18. Risks & open decisions

1. **LOC pressure** is the dominant risk; §4.2 cut‑list keeps the Core under 3000.
   Prefer folding `cards.py` into `guides.py`/`actions.py` over splitting modules.
2. **Board fidelity.** We model topology, not pixels. Decision: ship 2–3 named
   `BoardKind` topologies via the Builder; document that exact hex layout is out of
   scope.
3. **`__init__` vs dataclasses.** Resolved in §3.3: frozen slotted dataclasses /
   NamedTuples for records; `__new__` everywhere else; no hand‑written `__init__`.
4. **Action surface shape.** Decision: direct typed methods on `Game` (§7.4) over
   exposing Command objects, so the user never holds a non‑builtin instance.
5. **Undo depth.** Decision: single‑step `undo()` per turn (Command+Memento) — a
   clean, complete feature; multi‑level undo is a stretch.
6. **Guide/score‑card count.** Decision: implement all 10 guides if budget allows,
   else 6; always 2 score cards.

---

## 19. Requirement → design traceability (quick audit)

| Requirement | Satisfied by |
|---|---|
| §1.2 Façade, only `Game` instantiated | §7; construction Lock (§9.2) |
| §1.2 multiple independent instances | all state on the instance; no shared mutable globals (§5) |
| §1.3 programmatic play + full info | §7.2 properties (views) + §7.3–7.4 methods |
| §1.4 illegal actions blocked | §9 (4 layers: views, lock, state, chain) |
| §2.1 structure / delegation | §5–8; Game is thin; logic in sub‑components |
| §2.1 low‑level data as TypedDict/dataclass/Protocol | §3.1, §8.3 |
| §2.2 no public attrs, read‑only views, Final consts | §8 (`__` + property), §9.1, module `Final` registries |
| §2.3 validate‑first, dynamic + staging | §9.3–9.4 |
| §2.4 patterns (no singleton) | §10 |
| §2.5 reusable generic structures | §11 |
| §2.6 advanced features | §12 |
| §3.2 packaging (`game`, flat, relative, `__init__` exports Game) | §6 |
| §3.3 ≤3000/≤500 LOC, no `;`/comments/docstrings | §6 budget, §3.3 deviation |
| §3.4 `__new__` only, no Any/object/Callable[...], no ignores | §3.1, §8.1, §12 |
| §3.5 allowed imports / forbidden functions | §2 list; §3.3 no‑`hasattr` redesign |

---

*This design is intentionally a superset; the implemented Core is the subset in
§4.1, sized by §6, with the cut‑list in §4.2 as the release valve.*
