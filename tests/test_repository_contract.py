"""Repository-level release and architecture guardrails for Payments Analytics v2."""

from __future__ import annotations

import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class RepositoryContractTests(unittest.TestCase):
    def test_v1_artifacts_are_preserved_but_not_active(self) -> None:
        self.assertTrue(
            (PROJECT_ROOT / "archive" / "power-bi-v1"
             / "payments_analytics_dashboard.pbix").is_file()
        )
        self.assertTrue(
            (PROJECT_ROOT / "archive" / "legacy-sql-v1"
             / "01_customer_segments.sql").is_file()
        )
        self.assertTrue(
            (PROJECT_ROOT / "archive" / "immersive-dashboard-v1"
             / "analytics.py").is_file()
        )
        self.assertFalse((PROJECT_ROOT / "dashboard" / "analytics.py").exists())
        self.assertFalse((PROJECT_ROOT / "dashboard" / "ui.py").exists())
        for retired_dir in (PROJECT_ROOT / "queries", PROJECT_ROOT / "Power BI"):
            self.assertTrue(
                not retired_dir.exists() or not any(retired_dir.iterdir()),
                str(retired_dir),
            )

    def test_duplicate_exporters_are_retired(self) -> None:
        scripts = PROJECT_ROOT / "scripts"
        self.assertFalse((scripts / "export_charts.py").exists())
        self.assertFalse((scripts / "export_site_data.py").exists())
        self.assertTrue((scripts / "generate_artifacts.py").is_file())

    def test_active_surfaces_do_not_reference_the_stale_vercel_site(self) -> None:
        roots = (
            PROJECT_ROOT / "README.md",
            PROJECT_ROOT / "DESIGN.md",
            PROJECT_ROOT / ".env.example",
            PROJECT_ROOT / "dashboard",
            PROJECT_ROOT / "docs",
            PROJECT_ROOT / "site",
            PROJECT_ROOT / ".github",
        )
        excluded_parts = {
            ".next",
            "node_modules",
            "playwright-report",
            "test-results",
        }
        text_suffixes = {
            ".css", ".example", ".html", ".js", ".json", ".md",
            ".mjs", ".py", ".sql", ".toml", ".ts", ".tsx", ".txt",
            ".yaml", ".yml",
        }
        offenders: list[str] = []
        for root in roots:
            paths = (root,) if root.is_file() else root.rglob("*")
            for path in paths:
                if not path.is_file() or any(part in excluded_parts for part in path.parts):
                    continue
                if path.name == "deployment-smoke.spec.ts":
                    # This test intentionally contains the stale hostname as a
                    # negative assertion against the deployed HTML.
                    continue
                if path.suffix.lower() not in text_suffixes:
                    continue
                if "payment-observatory.vercel.app" in path.read_text(
                    encoding="utf-8", errors="ignore"
                ):
                    offenders.append(str(path.relative_to(PROJECT_ROOT)))
        self.assertEqual(offenders, [])

    def test_ci_executes_payload_drift_and_cross_engine_parity(self) -> None:
        workflow = (PROJECT_ROOT / ".github" / "workflows" / "ci.yml").read_text(
            encoding="utf-8"
        )
        for marker in (
            "scripts/generate_artifacts.py --check",
            "image: postgres:16",
            "scripts/check_sql_parity.py",
            "npm run typecheck",
            "npm run test:e2e",
            "npm run test:lighthouse",
        ):
            self.assertIn(marker, workflow)

    def test_pages_publish_is_gated_by_verified_ci_and_uses_static_output(self) -> None:
        workflow = (
            PROJECT_ROOT / ".github" / "workflows" / "pages.yml"
        ).read_text(encoding="utf-8")
        for marker in (
            "workflow_run:",
            "- CI",
            "workflow_run.conclusion == 'success'",
            "scripts/generate_artifacts.py --build-sha",
            "actions/upload-pages-artifact@v4",
            "path: site/out",
            "actions/deploy-pages@v4",
        ):
            self.assertIn(marker, workflow)

    def test_public_runtime_has_no_hosted_database_dependency(self) -> None:
        app = (PROJECT_ROOT / "dashboard" / "app.py").read_text(encoding="utf-8")
        requirements = (PROJECT_ROOT / "requirements.txt").read_text(encoding="utf-8")
        self.assertIn("AnalyticsEngine", app)
        self.assertNotIn("get_connection", app)
        self.assertIn("duckdb==", requirements)
        self.assertNotIn("supabase", requirements.lower())
        self.assertNotIn("neon", requirements.lower())


if __name__ == "__main__":
    unittest.main()
