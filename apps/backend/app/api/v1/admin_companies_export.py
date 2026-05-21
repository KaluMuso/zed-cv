"""Admin CSV export: companies aggregated from jobs."""
from __future__ import annotations

import csv
import io
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from app.core.deps import get_supabase, require_admin

CSV_COLUMNS = (
    "company",
    "primary_apply_email",
    "primary_apply_url",
    "primary_phone",
    "total_jobs",
    "active_jobs",
    "review_required_jobs",
    "latest_posted_at",
    "source_url_sample",
)

router = APIRouter(
    prefix="/admin/export",
    tags=["Admin"],
    dependencies=[Depends(require_admin)],
)


def _format_cell(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _rows_to_csv(rows: list[dict[str, Any]]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(CSV_COLUMNS)
    for row in rows:
        writer.writerow([_format_cell(row.get(col)) for col in CSV_COLUMNS])
    return buf.getvalue()


@router.get("/companies.csv")
async def export_companies_csv(supabase=Depends(get_supabase)) -> Response:
    """Download CSV of all companies with job counts and contact info."""
    result = supabase.rpc("admin_export_companies").execute()
    data = result.data if result.data is not None else []
    if not isinstance(data, list):
        data = []
    body = _rows_to_csv(data)
    return Response(
        content=body,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="companies.csv"',
            "Cache-Control": "no-store",
        },
    )
