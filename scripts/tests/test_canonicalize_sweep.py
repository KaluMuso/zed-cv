"""Tests for canonicalize_skills_sweep.py — dry-run cluster logic."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "apps" / "backend"))
sys.path.insert(0, str(REPO_ROOT / "apps" / "backend" / "scripts"))

from apps.backend.scripts.canonicalize_skills_sweep import (
    _levenshtein,
    _cosine_similarity,
    _token_overlap,
    _both_have_different_digits,
    _is_denied,
    _is_merge_candidate,
    _build_clusters,
    _pick_canonical,
    _format_cluster_report,
    run_sweep,
)


class TestLevenshtein:
    def test_identical(self):
        assert _levenshtein("hello", "hello") == 0

    def test_one_change(self):
        assert _levenshtein("cat", "car") == 1

    def test_empty(self):
        assert _levenshtein("abc", "") == 3

    def test_excel_microsoft_excel(self):
        assert _levenshtein("excel", "microsoft excel") == 10


class TestCosineSimilarity:
    def test_identical(self):
        v = [1.0, 2.0, 3.0]
        assert abs(_cosine_similarity(v, v) - 1.0) < 1e-9

    def test_orthogonal(self):
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        assert abs(_cosine_similarity(a, b)) < 1e-9

    def test_zero_vector(self):
        assert _cosine_similarity([0.0, 0.0], [1.0, 1.0]) == 0.0


class TestTokenOverlap:
    def test_identical(self):
        assert _token_overlap("machine learning", "machine learning") == 1.0

    def test_partial(self):
        assert _token_overlap("microsoft excel", "excel") == 1.0

    def test_no_overlap(self):
        assert _token_overlap("python", "javascript") == 0.0


class TestEdgeCaseRules:
    def test_different_digits_rejected(self):
        assert _both_have_different_digits("python 2", "python 3")

    def test_same_digits_allowed(self):
        assert not _both_have_different_digits("python 3", "python 3")

    def test_one_has_no_digits(self):
        assert not _both_have_different_digits("python", "python 3")

    def test_deny_pair(self):
        assert _is_denied("monitoring", "monitoring and evaluation")
        assert _is_denied("Monitoring and Evaluation", "monitoring")

    def test_non_denied(self):
        assert not _is_denied("python", "javascript")


class TestMergeCandidate:
    def test_high_cosine_low_lev(self):
        assert _is_merge_candidate("excel", "excell", 0.95, 1)

    def test_high_cosine_high_lev_with_token_overlap(self):
        assert _is_merge_candidate(
            "microsoft excel", "excel", 0.91, 10
        )

    def test_low_cosine_rejected(self):
        assert not _is_merge_candidate("python", "java", 0.60, 4)

    def test_medium_cosine_high_lev_no_overlap(self):
        assert not _is_merge_candidate("abcdef", "zyxwvu", 0.86, 6)

    def test_denied_pair_rejected(self):
        assert not _is_merge_candidate(
            "monitoring", "monitoring and evaluation", 0.95, 18
        )

    def test_different_digits_rejected(self):
        assert not _is_merge_candidate("python 2", "python 3", 0.99, 1)


class TestBuildClusters:
    def _make_skill(self, name: str, embedding: list[float], skill_id: str = ""):
        return {
            "id": skill_id or f"id-{name}",
            "name": name,
            "embedding": embedding,
            "canonical_of": None,
        }

    def test_clusters_similar_skills(self):
        base = [1.0] * 768
        slight_diff = [1.0] * 767 + [0.99]
        far = [0.0] * 767 + [1.0]

        skills = [
            self._make_skill("excel", base, "id-excel"),
            self._make_skill("excell", slight_diff, "id-excell"),
            self._make_skill("python", far, "id-python"),
        ]
        clusters = _build_clusters(skills)
        assert len(clusters) == 1
        names_in_cluster = {s["name"] for s in clusters[0]}
        assert names_in_cluster == {"excel", "excell"}

    def test_no_clusters_when_dissimilar(self):
        v1 = [1.0, 0.0] + [0.0] * 766
        v2 = [0.0, 1.0] + [0.0] * 766
        skills = [
            self._make_skill("python", v1, "id-py"),
            self._make_skill("javascript", v2, "id-js"),
        ]
        clusters = _build_clusters(skills)
        assert len(clusters) == 0

    def test_deny_list_prevents_cluster(self):
        base = [1.0] * 768
        slight = [1.0] * 767 + [0.999]
        skills = [
            self._make_skill("monitoring", base, "id-m"),
            self._make_skill("monitoring and evaluation", slight, "id-me"),
        ]
        clusters = _build_clusters(skills)
        assert len(clusters) == 0


class TestPickCanonical:
    def test_picks_longest_name(self):
        cluster = [
            {"id": "a", "name": "excel", "_ref_count": 10},
            {"id": "b", "name": "microsoft excel", "_ref_count": 5},
        ]
        ref_counts = {"a": 10, "b": 5}
        result = _pick_canonical(cluster, ref_counts)
        assert result["name"] == "microsoft excel"

    def test_tiebreak_by_refs(self):
        cluster = [
            {"id": "a", "name": "react", "_ref_count": 5},
            {"id": "b", "name": "react", "_ref_count": 20},
        ]
        ref_counts = {"a": 5, "b": 20}
        result = _pick_canonical(cluster, ref_counts)
        assert result["id"] == "b"


class TestFormatReport:
    def test_report_structure(self):
        canonical = {"id": "c1", "name": "microsoft excel"}
        members = [
            ({"id": "m1", "name": "excel", "_ref_count": 5}, 0.91, 10),
            ({"id": "m2", "name": "ms excel", "_ref_count": 3}, 0.94, 12),
        ]
        report = _format_cluster_report([(canonical, members)])
        assert 'Canonical: "microsoft excel"' in report
        assert "merging: \"excel\"" in report
        assert "merging: \"ms excel\"" in report
        assert "Summary: 1 clusters, 2 skills to merge" in report


class TestRunSweepDryRun:
    def test_dry_run_with_fixture_data(self):
        base = [1.0] * 768
        slight1 = [1.0] * 767 + [0.99]
        slight2 = [1.0] * 767 + [0.98]
        far = [0.0] * 767 + [1.0]

        mock_skills = [
            {"id": "s1", "name": "excel", "embedding": base, "canonical_of": None},
            {"id": "s2", "name": "excell", "embedding": slight1, "canonical_of": None},
            {"id": "s3", "name": "excels", "embedding": slight2, "canonical_of": None},
            {"id": "s4", "name": "monitoring", "embedding": far, "canonical_of": None},
            {"id": "s5", "name": "monitoring and evaluation", "embedding": [0.0] * 767 + [0.999], "canonical_of": None},
        ]

        mock_refs_user = [
            {"skill_id": "s1"},
            {"skill_id": "s1"},
            {"skill_id": "s2"},
        ]
        mock_refs_job = [
            {"skill_id": "s1"},
        ]

        supabase = MagicMock()

        def mock_table(name):
            mock_query = MagicMock()
            if name == "skills":
                mock_query.select.return_value = mock_query
                mock_query.is_.return_value = mock_query
                mock_query.execute.return_value = MagicMock(data=mock_skills)
            elif name == "user_skills":
                mock_query.select.return_value = mock_query
                mock_query.in_.return_value = mock_query
                mock_query.execute.return_value = MagicMock(data=mock_refs_user, count=3)
            elif name == "job_skills":
                mock_query.select.return_value = mock_query
                mock_query.in_.return_value = mock_query
                mock_query.execute.return_value = MagicMock(data=mock_refs_job, count=1)
            return mock_query

        supabase.table = mock_table

        report, stats = run_sweep(supabase, apply=False)

        assert stats is None
        assert "Canonical:" in report
        assert "monitoring" not in report.lower() or "monitoring and evaluation" not in report
        assert "Summary:" in report
