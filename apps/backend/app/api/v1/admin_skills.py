"""Admin skill dictionary — pending raw skills and merge to canonical."""
from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.deps import get_supabase, require_admin
from app.schemas.skills_dictionary import (
    CanonicalSkill,
    MergeRawSkillRequest,
    MergeRawSkillResponse,
    PendingRawSkillRow,
    PendingRawSkillsResponse,
    RawSkillMapping,
)
from app.services import skills_dictionary

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin/skills",
    tags=["Admin"],
    dependencies=[Depends(require_admin)],
)


@router.get("/pending", response_model=PendingRawSkillsResponse)
async def list_pending_raw_skills(supabase=Depends(get_supabase)):
    """Raw scraper skills awaiting canonical mapping (by occurrences desc)."""
    rows = skills_dictionary.list_pending_raw_skills(supabase)
    return PendingRawSkillsResponse(
        pending=[PendingRawSkillRow(**row) for row in rows]
    )


@router.post("/merge", response_model=MergeRawSkillResponse)
async def merge_raw_skill(
    body: MergeRawSkillRequest,
    supabase=Depends(get_supabase),
):
    """Map a raw skill row to a canonical name (create canonical if missing)."""
    try:
        canon_row, mapping_row = skills_dictionary.merge_raw_to_canonical(
            supabase,
            body.raw_skill_id,
            body.canonical_skill_name,
        )
    except LookupError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Raw skill mapping not found",
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    except RuntimeError:
        logger.exception("merge_raw_skill failed for %s", body.raw_skill_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to merge skill mapping",
        )

    return MergeRawSkillResponse(
        raw_skill_id=body.raw_skill_id,
        canonical_skill=CanonicalSkill(**canon_row),
        mapping=RawSkillMapping(**mapping_row),
    )
