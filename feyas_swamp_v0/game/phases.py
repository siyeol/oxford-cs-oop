from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from .core import Phase, ROUNDS

if TYPE_CHECKING:
    from .engine import Engine


class PhaseState(ABC):
    __slots__ = ()

    @property
    @abstractmethod
    def phase(self) -> Phase: ...

    @property
    def allows_draft(self) -> bool:
        return False

    @property
    def allows_placement(self) -> bool:
        return False

    @property
    def allows_turn(self) -> bool:
        return False

    @abstractmethod
    def advance(self, engine: Engine) -> PhaseState: ...


class DraftPhase(PhaseState):
    __slots__ = ()

    @property
    def phase(self) -> Phase:
        return Phase.DRAFT

    @property
    def allows_draft(self) -> bool:
        return True

    def advance(self, engine: Engine) -> PhaseState:
        engine._finish_drafting()
        return PlacementPhase()


class PlacementPhase(PhaseState):
    __slots__ = ()

    @property
    def phase(self) -> Phase:
        return Phase.PLACEMENT

    @property
    def allows_placement(self) -> bool:
        return True

    def advance(self, engine: Engine) -> PhaseState:
        engine._begin_play()
        return TurnsPhase()


class TurnsPhase(PhaseState):
    __slots__ = ()

    @property
    def phase(self) -> Phase:
        return Phase.TURNS

    @property
    def allows_turn(self) -> bool:
        return True

    def advance(self, engine: Engine) -> PhaseState:
        if engine._round >= ROUNDS:
            engine._run_final_scoring()
            return GameOverState()
        engine._advance_round()
        return TurnsPhase()


class GameOverState(PhaseState):
    __slots__ = ()

    @property
    def phase(self) -> Phase:
        return Phase.OVER

    def advance(self, engine: Engine) -> PhaseState:
        return self
