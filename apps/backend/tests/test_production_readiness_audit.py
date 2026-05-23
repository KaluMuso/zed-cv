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
