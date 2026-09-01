# `core` layer

`001_build_core.sql` defines reusable entities:

- event and 30-minute session facts;
- one row per distinct `transactionid`;
- generic item-property history and typed category/availability histories;
- event-time ASOF item context, which prevents future leakage;
- recursive anonymous category depth, root, path, cycle, and orphan flags.
