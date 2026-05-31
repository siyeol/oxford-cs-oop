"""Bid data structure for listings."""

from collections.abc import Callable
from typing import TYPE_CHECKING, Self

from .utils import Perishable, WithdrawableStack

if TYPE_CHECKING:
    from .users import Bid, Buyer


type OnBidSubmitCallback = Callable[[Bid], None]
type OnBidWithdrawCallback = Callable[[Bid], None]


# "Composition over inheritance"
# A Bids object is similar to a WithdrawableStack of bids,
# but not quite the a special case of that, so by the Liskov substitution principle
# it shouldn't be implemneted as a subclass.
# Instead of inheritance, we use another code reuse pattern called "composition",
# whereby a class is used internally to another class to supply part of its
# required functionality.


class Bids(Perishable):
    """The bids on a listing. Marked stale when the parent listing sells or is cancelled."""

    __slots__ = (
        "__weakref__",
        "__stack",
        "__by_buyer",
        "__on_submit",
        "__on_withdraw",
    )

    __stack: WithdrawableStack[Bid]
    __by_buyer: dict[Buyer, Bid]
    __on_submit: list[OnBidSubmitCallback]
    __on_withdraw: list[OnBidWithdrawCallback]

    def __new__(cls) -> Self:
        instance = object.__new__(cls)
        instance.__stack = WithdrawableStack()
        instance.__by_buyer = {}
        instance.__on_submit = []
        instance.__on_withdraw = []
        return instance

    @property
    @Perishable.not_stale
    def top(self) -> Bid:
        """The current top bid. Raises :class:`IndexError` if there are no bids."""
        # Pass-through implementation (common in composition over inheritance)
        return self.__stack.peek()

    @Perishable.not_stale
    def submit(self, bid: Bid) -> None:
        """Submit a new bid.

        Raises :class:`ValueError` if the buyer already has a bid, or if the bid amount is not strictly higher than the current top bid.
        """
        if bid.buyer in self.__by_buyer:
            self.withdraw(bid.buyer)  # delegate withdrawal logic to withdraw method.
        if self.__by_buyer:
            current_top = self.__stack.peek()
            if bid.amount <= current_top.amount:
                raise ValueError(
                    f"new bid {bid.amount} is not higher than current top bid {current_top.amount}"
                )
        self.__stack.push(bid)
        self.__by_buyer[bid.buyer] = bid
        for callback in self.__on_submit:
            callback(bid)

    @Perishable.not_stale
    def withdraw(self, buyer: Buyer) -> None:
        """Withdraw a buyer's bid. Raises :class:`KeyError` if the buyer has no bid."""
        if buyer not in self.__by_buyer:
            raise KeyError(buyer)
        bid = self.__by_buyer.pop(
            buyer
        )  # dict.pop = remove key-val pair and return val
        self.__stack.remove(bid)
        for callback in self.__on_withdraw:
            callback(bid)

    @Perishable.not_stale
    def get(self, buyer: Buyer) -> Bid | None:
        """Return the buyer's bid, or :data:`None` if they have no bid."""
        return self.__by_buyer.get(buyer)

    @Perishable.not_stale
    def __contains__(self, buyer: Buyer) -> bool:
        return buyer in self.__by_buyer

    @Perishable.not_stale
    def __getitem__(self, buyer: Buyer) -> Bid:
        return self.__by_buyer[buyer]

    @Perishable.not_stale
    def __len__(self) -> int:
        return len(self.__by_buyer)

    # Publish-Subscribe Pattern
    # Exposes a way for other classes to "subscribe" to an event,
    # which is "published" internally when certain things happen.
    # Here, we have e.g. the on_submit method to subscribe to bid submission,
    # and in the submid method we publish the event.

    @Perishable.not_stale
    def on_submit(self, callback: OnBidSubmitCallback) -> None:
        """Register a callback to be invoked when a bid is submitted."""
        self.__on_submit.append(callback)

    @Perishable.not_stale
    def on_withdraw(self, callback: OnBidWithdrawCallback) -> None:
        """Register a callback to be invoked when a bid is withdrawn."""
        self.__on_withdraw.append(callback)
