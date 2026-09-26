# Free deployment and rollback

Payments Analytics v2 uses only free public services.

## Case study: GitHub Pages

The Next.js site is a static export at `site/out` with the `/payments-analytics` base path. `.github/workflows/pages.yml` builds and publishes it to:

<https://abinashprasana.github.io/payments-analytics/>

The site has no server-side routes, runtime headers, remote database, or paid hosting dependency.

## Workbench: Streamlit Community Cloud

The operational workbench remains at:

<https://abinashprasana-payments-analytics-dashboardapp-mrsz1m.streamlit.app/>

It builds a cached in-memory DuckDB database from the committed synthetic snapshot and executes the same SQL models used in compatibility checks. Community Cloud may wake the application after a period of inactivity; that is normal for the free tier.

## PostgreSQL compatibility

PostgreSQL remains the documented local, production-shaped runtime. CI starts an ephemeral PostgreSQL service, loads the same snapshot atomically, executes the model chain, and compares its public results with DuckDB. No hosted PostgreSQL service is required.

## Ask Claude: MCP server on Render

The read-only MCP endpoint is a free Render web service defined in [`render.yaml`](../render.yaml). It serves the same three tools as the local stdio server, over stateless Streamable HTTP at `/mcp`, and answers Render's health check at `/healthz`.

It has to be created once by hand: in the Render dashboard, choose New → Blueprint, pick this repository, and apply. After that Render redeploys on its own, but only once GitHub checks pass on `main` (`autoDeployTrigger: checksPass`) and only when a file the server reads has changed (`buildFilter`). The service name `settlement-gap-mcp` should give `https://settlement-gap-mcp.onrender.com/mcp`. If Render hands out a different hostname, set `NEXT_PUBLIC_MCP_URL` for the Pages build and `MCP_PUBLIC_URL` for the workbench.

The free instance sleeps when idle, and the first call after that wakes it in 30 to 60 seconds. It uses about 150 MB of its 512 MB. Requests must carry an allowed Host and Origin (Render's own hostname is added from `RENDER_EXTERNAL_HOSTNAME`), bodies are capped at 16 KB, and each caller gets 30 calls a minute. Every call writes one audit line to the service log. The blueprint generates `SETTLEMENT_GAP_AUDIT_SALT`, so the caller hashes in those lines can't be reversed into addresses.

To roll back, redeploy the previous commit from the Render dashboard or revert on `main`. The `mcp-server` CI job runs `uv sync --locked` and `uv run pytest`, which covers both transports, the pinned tool definitions, and the check that the case-study replay still matches the tool.

## Release and rollback

Release in two deliberate stages:

1. finish the local Python, browser, Lighthouse, payload-drift, and PostgreSQL parity checks;
2. create the local release commit and annotated tag without deleting the rollback tag;
3. only after the repository owner approves publication, push that verified revision to remote `main`;
4. let remote CI gate the Pages build while Streamlit Community Cloud rebuilds the same revision;
5. run the read-only deployment smoke check and verify both surfaces show the same dataset version, as-of date, and commit SHA.

Rollback is a normal revert on `main`, followed by the same checks. Tags remain immutable evidence of the previous working snapshots.

## Platform references

- [GitHub Pages custom workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)
- [Next.js static exports](https://nextjs.org/docs/app/guides/static-exports)
- [Streamlit Community Cloud app management and sleep behavior](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app)
- [DuckDB PostgreSQL compatibility](https://duckdb.org/docs/stable/sql/dialect/postgresql_compatibility.html)
