"""The marketplace façade."""

from collections.abc import Callable
from typing import Self

from .listings import DraftListing, Listing, ListingFolder, ListingUID
from .users import Buyer, Seller


type OnDraftListingCallback = Callable[[DraftListing], None]


class Marketplace:
    """A marketplace."""

    # Factory pattern
    # Construction of an instance of a class A is delegated
    # to a method of another class B (the factory method),
    # because some information/action managed by class B is
    # required as part of the construction of class A instances.
    # E.g. creating listins requires a Marketplace-managed UID,
    # and involves storaged by marketplace for fast retrieval.

    __slots__ = (
        "__weakref__",
        "__next_uid",
        "__listings",
        "__buyers",
        "__sellers",
        "__on_draft_listing",
    )

    __next_uid: ListingUID
    __listings: ListingFolder
    __buyers: dict[str, Buyer]
    __sellers: dict[str, Seller]
    __on_draft_listing: list[OnDraftListingCallback]

    def __new__(cls) -> Self:
        instance = object.__new__(cls)
        instance.__next_uid = 0
        instance.__listings = ListingFolder()
        instance.__buyers = {}
        instance.__sellers = {}
        instance.__on_draft_listing = []
        return instance

    def draft_listing(self, seller: Seller) -> DraftListing:
        """Create a new draft listing for the given seller, with a freshly-allocated uid."""
        uid = self.__next_uid
        self.__next_uid += 1
        draft = DraftListing._new(uid, seller)
        self.__listings.add(draft)
        for callback in self.__on_draft_listing:
            callback(draft)
        return draft

    def listing(self, uid: ListingUID) -> Listing:
        """Return the listing with the given uid. Raises :class:`KeyError` if no such listing exists."""
        return self.__listings.get(uid)

    def buyer(self, username: str) -> Buyer:
        """Return the buyer with the given username, creating one if it doesn't exist yet."""
        if username not in self.__buyers:
            self.__buyers[username] = Buyer(username, self)
        return self.__buyers[username]

    def seller(self, username: str) -> Seller:
        """Return the seller with the given username, creating one if it doesn't exist yet."""
        if username not in self.__sellers:
            self.__sellers[username] = Seller(username, self)
        return self.__sellers[username]

    # Publish-Subscribe Pattern

    def on_draft_listing(self, callback: OnDraftListingCallback) -> None:
        """Register a callback to be invoked when a new draft listing is created."""
        self.__on_draft_listing.append(callback)
