"""Tests for production_readiness_audit root discovery."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_AUDIT_SCRIPT = (
    Path(__file__).resolve().parents[1] / "scripts" / "production_readiness_audit.py"
)
_WORKSPACE_ROOT = Path(__file__).resolve().parents[3]


def _load_audit_module():
    spec = importlib.util.spec_from_file_location(
        "production_readiness_audit_under_test",
        _AUDIT_SCRIPT,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def audit_module():
    return _load_audit_module()


class TestFindRepoOrBackendRoot:
    def test_find_root_works_in_repo(self, audit_module):
        backend_script = _AUDIT_SCRIPT
        root = audit_module._find_repo_or_backend_root(backend_script)
        assert (root / "CLAUDE.md").is_file() or (root / "AGENTS.md").is_file()
        assert (root / "docs" / "openapi.yaml").is_file() or (root / "CLAUDE.md").is_file()
        assert root == _WORKSPACE_ROOT

    def test_find_root_works_in_container(self, audit_module, tmp_path: Path):
        app_root = tmp_path / "app"
        scripts_dir = app_root / "scripts"
        scripts_dir.mkdir(parents=True)
        (app_root / "main.py").write_text("# stub\n", encoding="utf-8")
        (app_root / "requirements.txt").write_text("fastapi\n", encoding="utf-8")
        (app_root / "Dockerfile").write_text("FROM python:3.11-slim\n", encoding="utf-8")
        script_path = scripts_dir / "production_readiness_audit.py"
        script_path.write_text("# stub\n", encoding="utf-8")

        root = audit_module._find_repo_or_backend_root(script_path)
        assert root == app_root
        assert (root / "main.py").is_file()
        assert (root / "requirements.txt").is_file()

    def test_migration_check_skips_when_no_migrations_dir(self, audit_module):
        result = audit_module.check_migration_files()
        if audit_module.MIGRATIONS_DIR is None:
            assert result.status == "yellow"
            assert "not container" in result.detail
        else:
            assert result.status in ("green", "red")


class TestSchemaSentinels081To085:
    """Column/RPC sentinels for migrations 081–085."""

    def test_welcome_email_sent_sentinel(self, audit_module):
        assert ("users", "welcome_email_sent") in audit_module.SCHEMA_SENTINELS

    def test_schema_guard_alignment_sentinels(self, audit_module):
        for pair in (
            ("cv_generations", "cv_id"),
            ("users", "whatsapp_alerts"),
            ("users", "language"),
            ("users", "referral_match_bonus"),
        ):
            assert pair in audit_module.SCHEMA_SENTINELS

    def test_security_invoker_view_names(self, audit_module):
        assert audit_module.SECURITY_INVOKER_VIEWS == ("public_jobs", "llm_usage_daily")


class TestProductionRedisCheck:
    def test_redis_yellow_when_unset_dev_mode(self, audit_module, monkeypatch):
        monkeypatch.delenv("REDIS_URL", raising=False)
        result = audit_module.check_redis_url(production=False)
        assert result.status == "yellow"

    def test_redis_red_when_unset_production_mode(self, audit_module, monkeypatch):
        monkeypatch.delenv("REDIS_URL", raising=False)
        result = audit_module.check_redis_url(production=True)
        assert result.status == "red"
        assert "production" in result.detail

    def test_redis_green_when_set(self, audit_module, monkeypatch):
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
        result = audit_module.check_redis_url(production=True)
        assert result.status == "green"


class TestEmployerRlsTables:
    def test_rls_tables_include_employer_portal(self, audit_module):
        for table in ("employers", "employer_subscriptions", "cv_access_audit"):
            assert table in audit_module.RLS_TABLES
        assert len(audit_module.RLS_TABLES) == 13


class TestAuditRpcChecks:
    def test_check_schema_guard_columns_rpc_green(self, audit_module):
        class _Rpc:
            def execute(self):
                return type("R", (), {"data": [{"table_name": "users", "column_name": "id"}]})()

        class _Sb:
            def rpc(self, name, _payload):
                assert name == "schema_guard_columns"
                return _Rpc()

        result = audit_module.check_schema_guard_columns_rpc(_Sb())
        assert result.status == "green"
        assert "083" in result.name

    def test_check_security_invoker_views_red_when_off(self, audit_module):
        class _Rpc:
            def execute(self):
                return type(
                    "R",
                    (),
                    {
                        "data": [
                            {"view_name": "public_jobs", "security_invoker": False},
                            {"view_name": "llm_usage_daily", "security_invoker": True},
                        ]
                    },
                )()

        class _Sb:
            def rpc(self, name, _payload):
                assert name == "schema_guard_security_invoker_views"
                return _Rpc()

        result = audit_module.check_security_invoker_views(_Sb())
        assert result.status == "red"
        assert "public_jobs" in result.detail

    def test_check_rls_employer_tables(self, audit_module):
        rows = [
            {"table_name": t, "rls_enabled": True} for t in audit_module.RLS_TABLES
        ]

        class _Rpc:
            def execute(self):
                return type("R", (), {"data": rows})()

        class _Sb:
            def rpc(self, name, _payload):
                assert name == "schema_guard_rls"
                return _Rpc()

        result = audit_module.check_rls(_Sb())
        assert result.status == "green"
        assert "13" in result.detail
