# Power BI v1 status

The original Power BI report is retained only as a historical appendix at [`archive/power-bi-v1`](../archive/power-bi-v1/README.md).

Payments Analytics v2 does not maintain a separate DAX metric layer. The canonical settlement logic now lives in the portable SQL model chain and is executed by both DuckDB and PostgreSQL. This avoids presenting a third dashboard with definitions that can drift from the case study and the Settlement Operations Workbench.

If a future Power BI report is created, it should import exported canonical marts (`mart_daily_close`, `mart_exception_queue`, `mart_merchant_health`, and `mart_payment_trace`) and treat the SQL metric catalogue as authoritative.
