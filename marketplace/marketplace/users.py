"""Users of the marketplace."""

from collections.abc import Mapping, Sequence
from decimal import Decimal
from types import MappingProxyType
from typing import TYPE_CHECKING, Self

from .listings import ListingFolder

if TYPE_CHECKING:
    from .listings import (
        ActiveListing,
        DraftListing,
        ListingFolderView,
        SoldListing,
    )
    from .marketplace import Marketplace


class _BaseUser:
    """Base class for users, holding identity (username + marketplace)."""

    __slots__ = (
        "__weakref__",
        "__username",
        "__marketplace",
    )

    __username: str
    __marketplace: Marketplace

    def __new__(cls, username: str, marketplace: Marketplace) -> Self:
        instance = object.__new__(cls)
        instance.__username = username
        instance.__marketplace = marketplace
        return instance

    @property
    def username(self) -> str:
        """The username of this user."""
        return self.__username

    @property
    def marketplace(self) -> Marketplace:
        """The marketplace this user belongs to."""
        return self.__marketplace


class Seller(_BaseUser):
    """A seller in the marketplace."""

    __slots__ = (
        "__folder",
        "__amount_earned",
    )

    __folder: ListingFolder
    __amount_earned: Decimal

    def __new__(cls, username: str, marketplace: Marketplace) -> Self:
        instance = _BaseUser.__new__(cls, username, marketplace)
        instance.__folder = ListingFolder()
        instance.__amount_earned = Decimal("0")
        marketplace.on_draft_listing(instance._on_draft_listing)
        return instance

    @property
    def folder(self) -> ListingFolderView:
        """A readonly view of this seller's listing folder."""
        return self.__folder

    @property
    def amount_earned(self) -> Decimal:
        """The total amount this seller has earned from sold listings."""
        return self.__amount_earned

    def draft_listing(self) -> DraftListing:
        """Create a new draft listing on this seller's marketplace, for this seller."""
        return self.marketplace.draft_listing(self)

    def _on_draft_listing(self, draft: DraftListing) -> None:
        """Callback: handle a new draft listing if it was created for this seller."""
        if draft.seller is not self:
            return
        self.__folder.add(draft)
        draft.on_activate(self._on_activate)

    def _on_activate(self, active: ActiveListing) -> None:
        """Callback: handle the activation of one of this seller's drafts."""
        active.on_sell(self._on_sell)

    def _on_sell(self, sold: SoldListing) -> None:
        """Callback: update money earned when one of this seller's listings is sold."""
        self.__amount_earned += sold.sold_price


class Buyer(_BaseUser):
    """A buyer in the marketplace."""

    __slots__ = (
        "__money_spent",
        "__listings_with_callbacks",
        "__bought",
        "__active_bids",
        "__money_on_active_bids",
    )

    __money_spent: Decimal
    __listings_with_callbacks: set[ActiveListing]
    __bought: list[SoldListing]
    __active_bids: dict[ActiveListing, Bid]
    __money_on_active_bids: Decimal

    def __new__(cls, username: str, marketplace: Marketplace) -> Self:
        instance = _BaseUser.__new__(cls, username, marketplace)
        instance.__money_spent = Decimal("0")
        instance.__listings_with_callbacks = set()
        instance.__bought = []
        instance.__active_bids = {}
        instance.__money_on_active_bids = Decimal("0")
        return instance

    @property
    def money_spent(self) -> Decimal:
        """The total amount this buyer has spent on bought listings."""
        return self.__money_spent

    @property
    def bought(self) -> Sequence[SoldListing]:
        """The sold listings this buyer has won, in the order they were won."""
        return tuple(self.__bought)

    @property
    def active_bids(self) -> Mapping[ActiveListing, Bid]:
        """A readonly view of this buyer's current bids on still-active listings."""
        return MappingProxyType(self.__active_bids)

    @property
    def money_on_active_bids(self) -> Decimal:
        """The total amount this buyer currently has on bids for still-active listings."""
        return self.__money_on_active_bids

    def bid(self, listing: ActiveListing, amount: Decimal) -> Bid:
        """Place a bid on the given active listing for the given amount.

        On the first bid this buyer places on a given listing, registers callbacks for bid events on the listing's bids and for the listing's :meth:`on_sell` event.
        """
        new_bid = Bid._new(self, amount)
        if listing not in self.__listings_with_callbacks:
            listing.bids.on_submit(lambda b: self._on_bid_submit(listing, b))
            listing.bids.on_withdraw(lambda b: self._on_bid_withdraw(listing, b))
            listing.on_sell(lambda s: self._on_sell(listing, s))
            self.__listings_with_callbacks.add(listing)
        listing.bids.submit(new_bid)
        return new_bid

    def _on_bid_submit(self, listing: ActiveListing, bid: Bid) -> None:
        """Callback: a bid was submitted on a listing this buyer has bid on."""
        if bid.buyer is self:
            self.__active_bids[listing] = bid
            self.__money_on_active_bids += bid.amount

    def _on_bid_withdraw(self, listing: ActiveListing, bid: Bid) -> None:
        """Callback: a bid was withdrawn from a listing this buyer has bid on."""
        if bid.buyer is self and self.__active_bids.get(listing) is bid:
            del self.__active_bids[listing]
            self.__money_on_active_bids -= bid.amount

    def _on_sell(self, listing: ActiveListing, sold: SoldListing) -> None:
        """Callback: an active listing this buyer has bid on was sold."""
        if listing in self.__active_bids:
            losing_bid = self.__active_bids.pop(listing)
            self.__money_on_active_bids -= losing_bid.amount
        if sold.buyer is self:
            self.__money_spent += sold.sold_price
            self.__bought.append(sold)


class Bid:
    """A bid on a listing: a buyer and the amount they bid."""

    __slots__ = (
        "__weakref__",
        "__buyer",
        "__amount",
    )

    __buyer: Buyer
    __amount: Decimal

    def __new__(cls) -> Self:
        raise TypeError("Bids are not constructed directly.")

    @classmethod
    def _new(cls, buyer: Buyer, amount: Decimal) -> Self:
        """Protected constructor, for internal use."""
        instance = object.__new__(cls)
        instance.__buyer = buyer
        instance.__amount = amount
        return instance

    @property
    def buyer(self) -> Buyer:
        """The buyer who placed this bid."""
        return self.__buyer

    @property
    def amount(self) -> Decimal:
        """The amount of this bid."""
        return self.__amount
