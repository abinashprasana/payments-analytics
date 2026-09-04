# Legacy SQL v1

The eight original portfolio queries are preserved here for provenance but retired from the v2 analytical path. They are not executed by the case study, workbench, artifact generator, or CI.

Known issues include nominal mixed-currency totals labelled as a single currency, net settlement described as revenue, gross spend described as customer lifetime value, an incomplete cohort grid, and row-count windows described as calendar-day windows.

The authoritative v2 implementation lives in [`sql/models`](../../sql/models) and is exercised through the strict query registry.
