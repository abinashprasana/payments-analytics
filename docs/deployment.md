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
