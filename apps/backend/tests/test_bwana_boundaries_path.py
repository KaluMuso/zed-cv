"""Bwana knowledge boundaries must load in Docker (/app) and monorepo dev layouts."""
from pathlib import Path

from app.services import bwana_config


def test_bwana_config_module_imports():
    """Regression: parents[4] raised IndexError in Docker (/app/app/services/...)."""
    assert bwana_config._resolve_boundaries_path() is not None


def test_load_knowledge_boundaries_non_empty():
    text = bwana_config._load_knowledge_boundaries()
    assert "Never disclose" in text or "Never reveal" in text


def test_boundaries_bundled_copy_exists():
    bundled = (
        Path(bwana_config.__file__).resolve().parent.parent
        / "data"
        / "BWANA_KNOWLEDGE_BOUNDARIES.md"
    )
    assert bundled.is_file()
