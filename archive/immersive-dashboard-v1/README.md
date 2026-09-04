# Immersive dashboard v1 archive

This directory preserves the original Pandas analytical helpers, monolithic UI layer, bundled OGL reactor runtime, screenshots, and legacy case-study media from the checkpointed dashboard redesign.

They are retired from v2 because the visual reactor dominated the investigation path and the Python helpers independently implemented joins and KPIs that are now authoritative in SQL. The active Streamlit application imports `dashboard/workbench_ui.py` and `scripts/analytics_engine.py` only.
