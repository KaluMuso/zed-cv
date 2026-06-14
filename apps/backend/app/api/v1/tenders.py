"""Tenders routes — matches and ingests tenders."""
from __future__ import annotations

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client

from app.core.deps import (
    get_current_user_id,
    get_supabase,
    require_admin_api_key_or_superadmin,
)
from app.services.embedding import generate_embedding
from app.schemas.tenders import (
    TenderIngestRequest,
    TenderIngestResponse,
    TenderIngestErrorItem,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tenders", tags=["Tenders"])

# Similarity floor for the match_tenders RPC. Lower → more recall,
# higher → more precision. Extracted from the hardcoded 0.40 so we can
# A/B as the corpus grows. Will move to Settings once we have a few
# weeks of telemetry on what users actually click through.
_TENDER_MATCH_SIMILARITY_FLOOR = 0.40

# Cap on how many matched tenders the RPC returns. Frontend dashboard
# is paginated so a higher number doesn't hurt UX; 25 was clipping
# legitimate matches for users with broad industry_tags.
_TENDER_MATCH_COUNT_CAP = 50


@router.get("/matches")
async def get_tender_matches(
    current_user_id: str = Depends(get_current_user_id),
    supabase: Client = Depends(get_supabase),
) -> list[dict]:
    """Calculate and return AI-matched procurement opportunities for the user's business profile."""
    # 1. Fetch user's business profile
    try:
        profile_res = (
            supabase.table("business_profiles")
            .select("*")
            .eq("id", current_user_id)
            .execute()
        )
    except Exception as exc:
        logger.exception("Failed to query business profile for user=%s", current_user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving business profile.",
        ) from exc

    if not profile_res.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business profile not found. Complete your profile setup to fetch matches.",
        )

    profile = profile_res.data[0]

    # 2. Build semantic text context to embed.
    # PR R: use .get() with defaults for ALL profile fields so a partial
    # business_profile row (missing company_name etc. via direct insert or
    # future setup-wizard step) doesn't 500 with a KeyError.
    company_name = profile.get("company_name") or "Unnamed company"
    bio = profile.get("company_bio") or ""
    tags = ", ".join(profile.get("industry_tags") or [])
    embed_text = f"Company: {company_name}. Description: {bio}. Industries: {tags}."

    # 3. Generate embedding vector via gemini-embedding-001 (768 dimensions)
    try:
        query_embedding = await generate_embedding(embed_text, supabase=supabase)
    except Exception as e:
        logger.exception("Failed to generate match embedding for user=%s", current_user_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to generate match embedding.",
        ) from e

    # 4. Invoke PostgreSQL RPC
    try:
        rpc_res = supabase.rpc(
            "match_tenders",
            {
                "p_query_embedding": query_embedding,
                "p_match_threshold": _TENDER_MATCH_SIMILARITY_FLOOR,
                "p_match_count": _TENDER_MATCH_COUNT_CAP,
                "p_industry_tags": profile.get("industry_tags") or [],
                "p_provinces": profile.get("operating_provinces") or [],
            },
        ).execute()
    except Exception as exc:
        logger.exception("match_tenders RPC failed for user=%s", current_user_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Tender matching is temporarily unavailable.",
        ) from exc

    # Return matches, falling back to empty list if none
    return rpc_res.data or []


@router.post("/ingest", response_model=TenderIngestResponse)
async def ingest_tenders(
    body: TenderIngestRequest,
    supabase: Client = Depends(get_supabase),
    # Require admin/service API key or superadmin role
    _auth=Depends(require_admin_api_key_or_superadmin),
) -> TenderIngestResponse:
    """Bulk-ingest tenders from n8n scraper.

    Auth: X-INGEST-API-KEY / ADMIN_API_KEY header.
    Returns details on ingested, duplicates, and errors.
    """
    ingested = 0
    duplicates = 0
    errors: list[TenderIngestErrorItem] = []

    for idx, raw_tender in enumerate(body.tenders):
        try:
            # 1. Deduplicate by procuring_entity, title, and closing_date
            closing_str = raw_tender.closing_date.isoformat()
            
            existing = (
                supabase.table("tenders")
                .select("id")
                .eq("procuring_entity", raw_tender.procuring_entity)
                .eq("title", raw_tender.title)
                .eq("closing_date", closing_str)
                .execute()
            )
            
            if existing.data:
                duplicates += 1
                continue
                
            # 2. Insert tender metadata
            insert_data = {
                "procuring_entity": raw_tender.procuring_entity,
                "title": raw_tender.title,
                "category": raw_tender.category,
                "description": raw_tender.description,
                "requirements": raw_tender.requirements,
                "closing_date": closing_str,
                "province": raw_tender.province,
                "source_url": raw_tender.source_url,
            }
            
            res = supabase.table("tenders").insert(insert_data).execute()
            if not res.data:
                raise Exception("Failed to insert tender metadata")
                
            tender_id = res.data[0]["id"]
            
            # 3. Build text for embedding
            desc = raw_tender.description or ""
            reqs = raw_tender.requirements or ""
            embed_text = (
                f"Tender: {raw_tender.title}\n"
                f"Procuring Entity: {raw_tender.procuring_entity}\n"
                f"Category: {raw_tender.category}\n"
                f"Province: {raw_tender.province}\n"
                f"Description: {desc}\n"
                f"Requirements: {reqs}"
            )
            
            # 4. Generate embedding (using gemini-embedding-001 768 dimensions)
            try:
                embedding = await generate_embedding(embed_text, supabase=supabase)
            except Exception as e:
                # Cleanup metadata if embedding fails
                supabase.table("tenders").delete().eq("id", tender_id).execute()
                raise Exception(f"Failed to generate embedding: {str(e)}") from e
                
            # 5. Insert embedding
            embed_res = (
                supabase.table("tender_embeddings")
                .insert({
                    "tender_id": tender_id,
                    "embedding": embedding,
                    "content_chunk": embed_text
                })
                .execute()
            )
            if not embed_res.data:
                raise Exception("Failed to insert tender embedding")
                
            ingested += 1
            
        except Exception as exc:
            logger.exception("Failed to ingest tender at index %d: %s", idx, str(exc))
            errors.append(
                TenderIngestErrorItem(
                    index=idx,
                    title=raw_tender.title,
                    reason=str(exc)
                )
            )
            
    return TenderIngestResponse(
        ingested=ingested,
        duplicates=duplicates,
        errors=errors
    )
