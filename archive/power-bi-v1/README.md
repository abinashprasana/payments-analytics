# Power BI v1 archive

This directory preserves the original Power BI report and its four exported screenshots as a historical appendix. It is not part of the Payments Analytics v2 public navigation or release acceptance.

## Why it is archived

Power BI v1 predates the canonical settlement-reconciliation marts and therefore carries metric definitions that are no longer supported:

- monetary values from EUR, GBP, AUD, and CAD can be combined and labelled as though they share one currency;
- `settled_amount` is described as merchant revenue even though it is the net payout after fees;
- gross completed spend is presented as customer lifetime value without a contribution or margin definition;
- settlement status counts do not implement the v2 match identity, effective merchant terms, or SLA contract;
- its fraud outcomes are based on the original randomly assigned synthetic flags.

The `.pbix` file remains available for provenance. A future Power BI edition should consume the exported canonical marts rather than reconstructing business rules in DAX or Power Query.
