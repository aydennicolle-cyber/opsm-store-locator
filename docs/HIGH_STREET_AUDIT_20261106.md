# High Street classification check · 6 November 2026

This local audit started with 774 stores labelled High Street on street-address evidence alone. We reviewed stores, not a sample of shopping centres. Distances are approximate distances to the centre's mapped point, not to its boundary. No store was assigned to a centre by distance alone.

| Selection | Checked | Shopping centre | Other setting | High Street supported | Still unclear |
|---|---:|---:|---:|---:|---:|
| Highest risk and priority areas | 59 | 27 | 2 | 10 | 20 |
| Random sample of remaining 715 | 30 | 7 | 3 | 11 | 9 |
| Two additional cases found during checks | 2 | 2 | 0 | 0 | 0 |

The first group included stores within 100 metres of a mapped shopping centre point, stores with Bridgepoint, Westfield, Plaza, Shopping Centre/Center or Mall in their name, and stores with Balwyn in their address. The random sample was drawn before checking websites, by sorting the remaining stores by ID and using Python's random.Random(20261106).sample over 30 distinct stores. The two extra cases were related findings rather than random selections.

The random sample found seven confirmed centre tenants beyond the targeted group. Nine decisions are still open. These results justify checking street-address-only claims at shortlisted sites; they do not measure the error rate for the entire tool. A missing competitor or centre on the map is not evidence of absence.

For site screening, use the map to find competitors and build a shortlist. Before relying on a particular centre's tenant count, check its operator directory, nearby street-address-only stores and any unresolved stores in the shopping area. Record uncertain cases explicitly. Stop once the competitors that could change the decision for that site are either supported or identified as unknown.

[Store-by-store evidence](HIGH_STREET_AUDIT_20261106.csv)

All 91 decisions matched the rebuilt store records. No other store's place assignment changed and the original store list was unchanged. There are now 56 explicitly unresolved store-to-place links, including the 29 reopened here; 683 other High Street labels still rest on a street address alone. Local browser checks confirmed that OPSM Mosman Bridgepoint displays Bridgepoint Shopping Centre and Eyecare Plus Balwyn East displays Belmore Plaza.
