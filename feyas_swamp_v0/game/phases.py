from abc import ABC, abstractmethod

from .core import Phase


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


class DraftPhase(PhaseState):
    __slots__ = ()

    @property
    def phase(self) -> Phase:
        return Phase.DRAFT

    @property
    def allows_draft(self) -> bool:
        return True


class PlacementPhase(PhaseState):
    __slots__ = ()

    @property
    def phase(self) -> Phase:
        return Phase.PLACEMENT

    @property
    def allows_placement(self) -> bool:
        return True


class TurnsPhase(PhaseState):
    __slots__ = ()

    @property
    def phase(self) -> Phase:
        return Phase.TURNS

    @property
    def allows_turn(self) -> bool:
        return True


class GameOverState(PhaseState):
    __slots__ = ()

    @property
    def phase(self) -> Phase:
        return Phase.OVER
