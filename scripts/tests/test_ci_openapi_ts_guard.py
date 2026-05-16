"""OpenAPI ↔ TypeScript guard tests."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from ci_openapi_ts_guard import (
    _candidate_schema_names,
    _find_matching_brace,
    _parse_interface_fields,
    check,
    find_response_types,
    load_openapi,
    parse_interfaces,
)


SPEC = """
openapi: 3.1.0
info: { title: Test, version: "0.1" }
components:
  schemas:
    UserProfile:
      type: object
      properties:
        id: { type: string }
        phone: { type: string }
    CVUploadResponse:
      type: object
      properties:
        cv_id: { type: string }
        parsed_skills: { type: array, items: { type: string } }
"""


def _write(tmp_path: Path, name: str, body: str) -> Path:
    p = tmp_path / name
    p.write_text(textwrap.dedent(body), encoding="utf-8")
    return p


# ── Unit helpers ──


def test_parse_interface_fields_handles_nested_object():
    body = """
        id: string;
        job: {
            id: string;
            title: string;
        };
        score: number;
    """
    assert _parse_interface_fields(body) == ["id", "job", "score"]


def test_parse_interface_fields_handles_optional_and_readonly():
    body = """
        id: string;
        title?: string;
        readonly created_at: string;
    """
    assert _parse_interface_fields(body) == ["id", "title", "created_at"]


def test_find_matching_brace_respects_template_literals():
    src = "x = { y: `hello ${world}` };"
    start = src.index("{")
    end = _find_matching_brace(src, start)
    assert src[end] == "}"
    assert src[start : end + 1] == "{ y: `hello ${world}` }"


def test_candidate_schema_names_includes_result_response_swap():
    assert "CVUploadResponse" in _candidate_schema_names("CVUploadResult")
    assert "FooResult" in _candidate_schema_names("FooResponse")


# ── End-to-end ──


def test_clean_api_ts_passes(tmp_path):
    spec = _write(tmp_path, "openapi.yaml", SPEC)
    api = _write(
        tmp_path,
        "api.ts",
        """
        export interface UserProfile {
          id: string;
          phone: string;
        }
        export const profile = {
          get: () => apiFetch<UserProfile>("/profile"),
        };
        """,
    )
    drifts, unmapped = check(api, spec, {})
    assert drifts == []
    assert unmapped == []


def test_extra_ts_field_is_drift(tmp_path):
    """The PR #24 bug, exactly: TS interface declares a field the
    OpenAPI / backend schema doesn't emit."""
    spec = _write(tmp_path, "openapi.yaml", SPEC)
    api = _write(
        tmp_path,
        "api.ts",
        """
        // @openapi CVUploadResponse
        export interface CVUploadResult {
          cv_id?: string;
          skills_extracted?: string[];
          parsed_skills?: string[];
        }
        export const cv = {
          upload: () => apiFetch<CVUploadResult>("/cv/upload"),
        };
        """,
    )
    drifts, unmapped = check(api, spec, {})
    assert unmapped == []
    drift_fields = sorted(d.ts_field for d in drifts)
    assert drift_fields == ["skills_extracted"]
    assert drifts[0].matched_schema == "CVUploadResponse"


def test_openapi_extra_field_is_ok(tmp_path):
    """OpenAPI may carry fields TS doesn't read. That's not drift."""
    spec = _write(tmp_path, "openapi.yaml", SPEC)
    api = _write(
        tmp_path,
        "api.ts",
        """
        export interface UserProfile {
          id: string;
        }
        export const x = {
          go: () => apiFetch<UserProfile>("/profile"),
        };
        """,
    )
    drifts, _ = check(api, spec, {})
    assert drifts == []


def test_suffix_swap_matches_response(tmp_path):
    """`CVUploadResult` should match `CVUploadResponse` automatically."""
    spec = _write(tmp_path, "openapi.yaml", SPEC)
    api = _write(
        tmp_path,
        "api.ts",
        """
        export interface CVUploadResult {
          cv_id?: string;
          parsed_skills?: string[];
        }
        export const x = { go: () => apiFetch<CVUploadResult>("/cv/upload") };
        """,
    )
    drifts, unmapped = check(api, spec, {})
    assert drifts == []
    assert unmapped == []


def test_unmapped_interface_is_warn_only(tmp_path):
    spec = _write(tmp_path, "openapi.yaml", SPEC)
    api = _write(
        tmp_path,
        "api.ts",
        """
        export interface OrphanResult {
          foo: string;
        }
        export const x = { go: () => apiFetch<OrphanResult>("/whatever") };
        """,
    )
    drifts, unmapped = check(api, spec, {})
    assert drifts == []
    assert [u.ts_interface for u in unmapped] == ["OrphanResult"]


def test_allowlist_silences_specific_drift(tmp_path):
    spec = _write(tmp_path, "openapi.yaml", SPEC)
    api = _write(
        tmp_path,
        "api.ts",
        """
        // @openapi CVUploadResponse
        export interface CVUploadResult {
          cv_id?: string;
          queued?: boolean;
        }
        export const cv = { upload: () => apiFetch<CVUploadResult>("/cv/upload") };
        """,
    )
    allowlist = {
        "ignore": [{"interface": "CVUploadResult", "field": "queued", "reason": "x"}]
    }
    drifts, _ = check(api, spec, allowlist)
    assert drifts == []


def test_unmapped_ok_silences_warning(tmp_path):
    spec = _write(tmp_path, "openapi.yaml", SPEC)
    api = _write(
        tmp_path,
        "api.ts",
        """
        export interface OrphanResult { foo: string; }
        export const x = { go: () => apiFetch<OrphanResult>("/whatever") };
        """,
    )
    allowlist = {"unmapped_ok": ["OrphanResult"]}
    drifts, unmapped = check(api, spec, allowlist)
    assert drifts == []
    assert unmapped == []


def test_oneof_schema_unions_fields(tmp_path):
    spec_text = """
        openapi: 3.1.0
        info: { title: T, version: "0.1" }
        components:
          schemas:
            A:
              type: object
              properties:
                a: { type: string }
            B:
              type: object
              properties:
                b: { type: string }
            Either:
              oneOf:
                - $ref: '#/components/schemas/A'
                - $ref: '#/components/schemas/B'
        """
    spec = _write(tmp_path, "openapi.yaml", spec_text)
    schemas = load_openapi(spec)
    assert schemas["Either"] == {"a", "b"}


def test_apifetch_with_template_literal_url(tmp_path):
    """The real api.ts uses `apiFetch<X>(\\`/foo/${id}\\`, ...)`. The
    detector must catch that too, not just plain string URLs."""
    spec = _write(tmp_path, "openapi.yaml", SPEC)
    api = _write(
        tmp_path,
        "api.ts",
        """
        export interface UserProfile { id: string; phone: string; }
        export const x = {
          get: (id: string) => apiFetch<UserProfile>(`/profile/${id}`),
        };
        """,
    )
    types = find_response_types(api.read_text())
    assert "UserProfile" in types


def test_interface_with_inline_object_field(tmp_path):
    """Real api.ts MatchData has `job: { id: string; ... }` inline. The
    top-level field name must be `job`, not the nested keys."""
    spec_text = """
        openapi: 3.1.0
        info: { title: T, version: "0.1" }
        components:
          schemas:
            MatchResult:
              type: object
              properties:
                id: { type: string }
                job: { type: object }
        """
    spec = _write(tmp_path, "openapi.yaml", spec_text)
    api = _write(
        tmp_path,
        "api.ts",
        """
        // @openapi MatchResult
        export interface MatchData {
          id: string;
          job: {
            id: string;
            title: string;
          };
        }
        export const x = { go: () => apiFetch<MatchData>("/matches") };
        """,
    )
    drifts, _ = check(api, spec, {})
    assert drifts == []
