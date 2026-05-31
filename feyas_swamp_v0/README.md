Design

Feya's Swamp is exposed through one facade class, Game, the only class a user instantiates. The user passes a player count and drives everything through values returned by Game's read-only properties. Game delegates to an Engine that coordinates the subsystems and holds no rules itself beyond staging.

The Swamp models the board as a graph of spaces of three kinds: water, spirit, and temple. Settlements and added spirit tiles are overlays on spaces. Islands are connected components of land spaces, recomputed with union-find, which also detects illegal island joins. Boats move by bounded breadth-first search across water.

Each Player owns a wallet, boats, workers, a sailing track, a settlement supply, a current and a next guide, collected temples, and a score. A Bank holds the shared neutral-worker pool. Guides are flyweight records carrying initiative, settlement value, sailing range, and an ability strategy applied during income, turns, or passing.

The Engine runs four rounds as a phase state machine: setup, which is guide drafting then starting placement, then turns, then game over. Income and maintenance run automatically at round boundaries. A turn becomes a command built on a boat or ground template; it validates through a chain of single-rule checks, then executes against the board, players, and bank, recording a memento so the last action can be undone, and notifying score observers.

Final scoring sums island value, two score-card strategies, and leftover resources. Everything Game exposes is read-only: scalars, tuples, frozensets, mapping proxies, or protocol views, so information is complete yet immutable. Multiple independent games coexist because all state lives on the instance.

Validation

All state is private and reachable only through read-only properties. Collections leave as tuples, frozensets, or mapping proxies, and sub-objects leave behind read-only protocols, so callers cannot mutate internals. There are no public attributes and no setters.

Staging is enforced by the phase state machine and a turn cursor. Drafting, placement, actions, and passing each check that the game is in the correct phase and that the acting clan is the current actor; otherwise a specific error is raised, such as wrong phase, not your turn, or illegal setup.

Every action validates before mutating. Boat actions confirm that a worker is available, each named boat is owned, each destination is within sailing range, and the per-action target is legal. Placement legality runs through an ordered chain of single-rule checks covering free water, adjacency, island joins, and totem rules. Resource costs are checked before any spending, raising on insufficient gold, fish, mana, or workers.

Because validation precedes mutation and the engine snapshots state before each action, a failed action leaves the game unchanged. Illegal arguments are also constrained at the type level through enumerated clans, guides, and actions and integer identifiers obtained from the board.

Object-oriented Patterns

Facade: Game is the sole entry point, hiding the engine, board, players, guides, and scoring.
State: phase objects for setup, turns, and over vary which operations are legal.
Command: each turn action is an object with validate and execute steps.
Template method: boat actions share a skeleton of validate, place worker, move each boat, and apply effect, and subclasses supply the effect.
Chain of responsibility: placement legality is an ordered chain of single-rule handlers.
Strategy: guide abilities and score cards are interchangeable algorithms.
Observer: score changes are published to subscribers.
Memento: the engine snapshots state so the last action can be undone.
Factory method and builder: a builder assembles the board, players, guide offer, and score cards behind the constructor.
Composite: islands compose spaces and are scored uniformly.
Proxy: protocol views and mapping proxies guard exposed state.
Flyweight: guide cards are shared immutable records.
Mediator: the engine coordinates players, board, and bank so they never reference one another.

Reusable Generic Data Structures

Graph: a generic undirected graph parameterised by node type, offering neighbour access and bounded breadth-first traversal. It models the swamp topology and boat reachability.
UnionFind: a generic disjoint-set structure with union by rank and path compression. It groups land spaces into islands, detects when a placement would merge islands, and finds a clan's largest connected settlement group.
Bag: a generic multiset backed by a counter, with guarded addition and removal and a total count. It backs each clan's wallet of gold, mana, and fish.
Stack: a generic last-in first-out stack with push, pop, peek, and snapshot or replace for state capture. It backs temple-tile piles and the fish stacked on settlements.
All four are parametrically polymorphic and free of any game concept, so they are reusable in other projects.

Advanced Language Features

Generic classes and type aliases use the modern type-parameter syntax. Structural typing through protocols provides read-only views and decouples strategies from the engine. The code uses abstract base classes, frozen dataclasses, enumerations, and the Self type. Dunder methods such as iter, len, contains, bool, and getitem make the data structures idiomatic. Iterators and generators express breadth-first search and traversals, and comprehensions express scoring sums. Tagged unions over enumerations are matched exhaustively under strict typing, and constants are Final.
