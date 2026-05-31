# OOP Market Mini-project

This week's exercises will guide you through the implementation of a backend for online marketplaces.
In tackling the exercises, you might wish to follow the specifications given in the [Sample Assignment](./2026-05-oop-assignment-sample.pdf).

# Specification

There are two kinds of users in a marketplace, identified by a unique username:

- sellers, who list items for sale
- buyers, who bid on items

A buyer and a seller can have the same username, and they need not be related as far as this specification is concerned.
Below is the typical lifecycle of a listing in a marketplace:

1. A seller creates the listing (in draft state).
   At creation, the listing is assigned a Unique ID within a marketplace.
   The following data needs to be specified for a listing:

   - title, a string of max length 50
   - start price
   - description, a string of max length 500
   - min bidding time

   Some or all of this data can be specified and modified after creation.

2. The seller can change the listing state from draft to active at any time, as long as all data from point 1 above has been specified. Alternatively, the seller can change the lifting state from draft to cancelled.

3. When the listing is active, buyers can submit bids. Only the current highest bid is visible to buyers. Each buyer can have at most one bid on the listing at any time and can withdraw their bid at any time. A new bid can be submitted only if it is higher than the highest current bid.

4. After the minimum bidding time has elapsed from the moment the listing has become active, the seller can change the listing state from active to sold, as long as at least one bid is present: when this happens, the buyer with the highest bid has bought the item. At any time when no bids are present, the seller can change the listing state from active to cancelled.

A `Marketplace` class should act as the entry point to your library, such that all data and actions for a single marketplace should ultimately be accessible starting from a corresponding `Marketplace` instance.
This is an example of the **Façade Pattern**, where a library or application has a single entry point which provides access to all of its functionality.

The library should offer the following core functionality:

- Creation of listings, either brand new or from existing listings.
- Access to marketplace listings by ID.
- Editing of listing data, with undo functionality.
- Changes to listing state.
- Submission and management of bids on a listing.
- Access to the draft, active, sold and cancelled listings of a seller.
- Access the current bids on active listings of a buyer, and the listings that a buyer has bought.
- Event subscription functionality, where can request to be notified of the following events:
  - changes in state for a listing
  - changes in bids for a listing
- Keeping track of the total amount of money that a seller has made from sold listing.
- Keeping track of the total amount of money that a buyer has spent on bought listings, and the total amount of money that a buyer currently has on highest bids for active listings.

Data management and actions for distinct clusters of marketplace functionality should be delegated to distinct classes.
This is according to the **Single Responsibility Principle**: every component &mdash; module, class, method, function &mdash; should have a single well-defined responsibility (at the corresponding level of abstraction).

Some interesting stretch goals:

- Currenty-aware pricing with exchange rate management.
- Support for safe data serialisation.
