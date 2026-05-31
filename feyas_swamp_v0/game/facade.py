from collections.abc import Callable, Mapping, Sequence
from random import Random
from typing import Self

from .actions import (
    AddSpiritAction,
    BuildAction,
    CelebrateAction,
    FishAction,
    ImproveSailingAction,
    SailAction,
    TradeAction,
)
from .board import BoardView, build_swamp
from .core import (
    ActionKind,
    BOATS_PER_CLAN,
    BoatId,
    ClanColor,
    GUIDES_IN_OFFER,
    GuideKind,
    IllegalSetup,
    Phase,
    SCORE_CARDS_IN_PLAY,
    ScoreEvent,
    SpaceId,
)
from .engine import Engine
from .guides import GuideView
from .players import Bank, Player, PlayerView
from .scoring import SCORE_CARDS


class GameBuilder:
    @staticmethod
    def build(clans: Sequence[ClanColor], seed: int | None) -> Engine:
        rng = Random(seed)
        swamp = build_swamp(len(clans))
        bank = Bank()
        players: dict[ClanColor, Player] = {}
        next_boat = 0
        for color in clans:
            boats: tuple[BoatId, ...] = tuple(
                range(next_boat, next_boat + BOATS_PER_CLAN)
            )
            next_boat += BOATS_PER_CLAN
            players[color] = Player(color, boats)
        guides = list(GuideKind)
        rng.shuffle(guides)
        offer = guides[:GUIDES_IN_OFFER]
        cards = list(SCORE_CARDS)
        rng.shuffle(cards)
        score_cards = tuple(cards[:SCORE_CARDS_IN_PLAY])
        return Engine(swamp, bank, players, list(clans), offer, score_cards)


class Game:
    _engine: Engine

    def __new__(cls, players: int, *, seed: int | None = None) -> Self:
        if not 2 <= players <= 4:
            raise IllegalSetup("between 2 and 4 players are required")
        self = super().__new__(cls)
        self._engine = GameBuilder.build(list(ClanColor)[:players], seed)
        return self

    @property
    def round_number(self) -> int:
        return self._engine.round_number

    @property
    def phase(self) -> Phase:
        return self._engine.phase

    @property
    def is_over(self) -> bool:
        return self._engine.is_over

    @property
    def clans(self) -> tuple[ClanColor, ...]:
        return self._engine.colors

    @property
    def players(self) -> Mapping[ClanColor, PlayerView]:
        return self._engine.players_view()

    @property
    def turn_order(self) -> tuple[ClanColor, ...]:
        return self._engine.turn_order

    @property
    def current_player(self) -> ClanColor | None:
        return self._engine.current_actor()

    @property
    def board(self) -> BoardView:
        return self._engine.swamp

    @property
    def guide_offer(self) -> tuple[GuideView, ...]:
        return self._engine.offer

    @property
    def scores(self) -> Mapping[ClanColor, int]:
        return self._engine.scores()

    @property
    def winners(self) -> frozenset[ClanColor]:
        return self._engine.winners()

    @property
    def legal_actions(self) -> frozenset[ActionKind]:
        return self._engine.legal_actions()

    def draft_guide(self, clan: ClanColor, guide: GuideKind) -> None:
        self._engine.draft_guide(clan, guide)

    def place_starting_settlement(self, clan: ClanColor, space: SpaceId) -> None:
        self._engine.place_starting_settlement(clan, space)

    def fish(self, clan: ClanColor, moves: Mapping[BoatId, SpaceId]) -> None:
        self._engine.perform(FishAction(self._engine, clan, moves))

    def build_settlement(
        self, clan: ClanColor, moves: Mapping[BoatId, SpaceId]
    ) -> None:
        self._engine.perform(BuildAction(self._engine, clan, moves))

    def sail(self, clan: ClanColor, moves: Mapping[BoatId, SpaceId]) -> None:
        self._engine.perform(SailAction(self._engine, clan, moves))

    def trade(
        self,
        clan: ClanColor,
        moves: Mapping[BoatId, SpaceId],
        placements: Mapping[BoatId, Sequence[SpaceId]],
    ) -> None:
        self._engine.perform(TradeAction(self._engine, clan, moves, placements))

    def improve_sailing(self, clan: ClanColor) -> None:
        self._engine.perform(ImproveSailingAction(self._engine, clan))

    def celebrate(self, clan: ClanColor, anchor: SpaceId) -> None:
        self._engine.perform(CelebrateAction(self._engine, clan, anchor))

    def add_spirit_worship(self, clan: ClanColor, target: SpaceId) -> None:
        self._engine.perform(AddSpiritAction(self._engine, clan, target))

    def pass_turn(self, clan: ClanColor, next_guide: GuideKind | None = None) -> None:
        self._engine.pass_turn(clan, next_guide)

    def exchange_mana_for_neutral(self, clan: ClanColor) -> None:
        self._engine.exchange_mana_for_neutral(clan)

    def exchange_worker_for_mana(self, clan: ClanColor) -> None:
        self._engine.exchange_worker_for_mana(clan)

    def undo(self) -> None:
        self._engine.undo()

    def subscribe_scores(self, callback: Callable[[ScoreEvent], None]) -> None:
        self._engine.subscribe(callback)
