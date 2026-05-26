"""User profile routes."""
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ValidationError

from app.core.deps import get_supabase, get_current_user_id
from app.schemas.cv_sections import CVSections
from app.services.referral import count_referral_signups
from app.schemas.user import (
    UserProfile,
    UserProfileUpdate,
    NotificationPreferences,
    NotificationPreferencesUpdate,
    ProfileDeleted,
    UserSkill,
    UserSkillCreate,
    UserSkillUpdate,
    UserSkillsList,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/profile", tags=["Profile"])


def _extract_cv_sections(parsed_data) -> CVSections | None:
    """Pull the structured "sections" object out of cvs.parsed_data.

    Legacy parsed_data rows (pre-task #59) don't have this key. Reads
    null. If the key exists but doesn't validate, we log + return None
    rather than 500 the /profile call — graceful degradation matters
    here because /profile is on the hot path for every page that
    requires auth.
    """
    if not parsed_data or not isinstance(parsed_data, dict):
        return None
    raw = parsed_data.get("sections")
    if not raw:
        return None
    try:
        return CVSections.model_validate(raw)
    except ValidationError as e:
        logger.warning("Discarding malformed cv_sections from parsed_data: %s", e.errors()[:3])
        return None


def _build_profile(user_id: str, supabase) -> UserProfile:
    result = supabase.table("users").select("*").eq("id", user_id).single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="User not found")

    user = result.data

    skills_result = (
        supabase.table("user_skills")
        .select("skills(name)")
        .eq("user_id", user_id)
        .execute()
    )
    skills = [s["skills"]["name"] for s in (skills_result.data or []) if s.get("skills")]

    # Pull id AND parsed_data so we can also extract structured sections in
    # a single query — avoids a second round-trip on the hot /profile path.
    cv_result = (
        supabase.table("cvs")
        .select("id, parsed_data")
        .eq("user_id", user_id)
        .eq("is_primary", True)
        .limit(1)
        .execute()
    )
    cv_uploaded = bool(cv_result.data)
    cv_sections = (
        _extract_cv_sections(cv_result.data[0].get("parsed_data"))
        if cv_result.data
        else None
    )

    referral_code = user.get("referral_code") or ""
    referral_signups = count_referral_signups(user_id, supabase) if referral_code else 0
    referral_qualified = count_referral_qualified(user_id, supabase) if referral_code else 0

    return UserProfile(
        id=user["id"],
        phone=user["phone"],
        full_name=user.get("full_name"),
        email=user.get("email"),
        location=user.get("location"),
        years_experience=user.get("years_experience", 0),
        skills=skills,
        cv_uploaded=cv_uploaded,
        subscription_tier=user.get("subscription_tier", "free"),
        role=user.get("role", "user"),
        cv_sections=cv_sections,
        referral_code=referral_code,
        referral_signups_count=referral_signups,
        referral_qualified_count=referral_qualified,
    )


@router.get("", response_model=UserProfile)
async def get_profile(
    user_id: str = Depends(get_current_user_id),
    supabase=Depends(get_supabase),
):
    return _build_profile(user_id, supabase)


@router.patch("", response_model=UserProfile)
async def update_profile(
    body: UserProfileUpdate,
    user_id: str = Depends(get_current_user_id),
    supabase=Depends(get_supabase),
):
    update_data = body.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(status_code=422, detail="No fields to update")

    supabase.table("users").update(update_data).eq("id", user_id).execute()
    return _build_profile(user_id, supabase)


@router.delete("", response_model=ProfileDeleted)
async def delete_profile(
    user_id: str = Depends(get_current_user_id),
    supabase=Depends(get_supabase),
):
    """Hard-delete the caller's account.

    FK ON DELETE CASCADE on user_id columns handles user_skills, cvs, matches,
    subscriptions, payments, generated_documents, application_outcomes.
    """
    existing = supabase.table("users").select("id").eq("id", user_id).limit(1).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="User not found")

    supabase.table("users").delete().eq("id", user_id).execute()
    return ProfileDeleted(deleted=True, user_id=user_id)


@router.get("/preferences", response_model=NotificationPreferences)
async def get_preferences(
    user_id: str = Depends(get_current_user_id),
    supabase=Depends(get_supabase),
):
    result = (
        supabase.table("users")
        .select("whatsapp_alerts, email_notifications_enabled, language")
        .eq("id", user_id)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="User not found")
    return NotificationPreferences(
        whatsapp_alerts=result.data.get("whatsapp_alerts", True),
        email_notifications_enabled=result.data.get("email_notifications_enabled", True),
        language=result.data.get("language", "en"),
    )


@router.patch("/preferences", response_model=NotificationPreferences)
async def update_preferences(
    body: NotificationPreferencesUpdate,
    user_id: str = Depends(get_current_user_id),
    supabase=Depends(get_supabase),
):
    update_data = body.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(status_code=422, detail="No fields to update")

    supabase.table("users").update(update_data).eq("id", user_id).execute()
    result = (
        supabase.table("users")
        .select("whatsapp_alerts, email_notifications_enabled, language")
        .eq("id", user_id)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="User not found")
    return NotificationPreferences(
        whatsapp_alerts=result.data.get("whatsapp_alerts", True),
        email_notifications_enabled=result.data.get("email_notifications_enabled", True),
        language=result.data.get("language", "en"),
    )


def _resolve_skill_id(name: str, supabase) -> str | None:
    """Look up a canonical skill_id by name, checking direct match then aliases.

    Returns None if the skill does not yet exist in the catalogue.
    """
    n = name.strip().lower()
    if not n:
        return None
    direct = supabase.table("skills").select("id").eq("name", n).limit(1).execute()
    if direct.data:
        return direct.data[0]["id"]
    alias = (
        supabase.table("skill_aliases").select("skill_id").eq("alias", n).limit(1).execute()
    )
    if alias.data:
        return alias.data[0]["skill_id"]
    return None


def _list_user_skills(user_id: str, supabase) -> list[UserSkill]:
    rows = (
        supabase.table("user_skills")
        .select("proficiency, source, skills(name)")
        .eq("user_id", user_id)
        .execute()
    )
    out: list[UserSkill] = []
    for r in rows.data or []:
        s = r.get("skills") or {}
        if not s.get("name"):
            continue
        out.append(
            UserSkill(
                name=s["name"],
                proficiency=r.get("proficiency") or "intermediate",
                source=r.get("source") or "manual",
            )
        )
    out.sort(key=lambda x: x.name)
    return out


@router.get("/skills", response_model=UserSkillsList)
async def list_skills(
    user_id: str = Depends(get_current_user_id),
    supabase=Depends(get_supabase),
):
    return UserSkillsList(skills=_list_user_skills(user_id, supabase))


@router.post("/skills", response_model=UserSkillsList, status_code=status.HTTP_201_CREATED)
async def add_skill(
    body: UserSkillCreate,
    user_id: str = Depends(get_current_user_id),
    supabase=Depends(get_supabase),
):
    name = body.name.strip().lower()
    if not name:
        raise HTTPException(status_code=422, detail="Skill name is required")

    skill_id = _resolve_skill_id(name, supabase)
    if not skill_id:
        created = supabase.table("skills").insert({"name": name}).execute()
        if not created.data:
            raise HTTPException(status_code=500, detail="Could not register skill")
        skill_id = created.data[0]["id"]

    supabase.table("user_skills").upsert(
        {
            "user_id": user_id,
            "skill_id": skill_id,
            "proficiency": body.proficiency,
            "source": "manual",
        },
        on_conflict="user_id,skill_id",
    ).execute()
    return UserSkillsList(skills=_list_user_skills(user_id, supabase))


@router.patch("/skills/{name}", response_model=UserSkillsList)
async def update_skill(
    name: str,
    body: UserSkillUpdate,
    user_id: str = Depends(get_current_user_id),
    supabase=Depends(get_supabase),
):
    skill_id = _resolve_skill_id(name, supabase)
    if not skill_id:
        raise HTTPException(status_code=404, detail="Skill not found")
    existing = (
        supabase.table("user_skills")
        .select("user_id")
        .eq("user_id", user_id)
        .eq("skill_id", skill_id)
        .limit(1)
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="Skill not on profile")
    supabase.table("user_skills").update({"proficiency": body.proficiency}).eq(
        "user_id", user_id
    ).eq("skill_id", skill_id).execute()
    return UserSkillsList(skills=_list_user_skills(user_id, supabase))


@router.delete("/skills/{name}", response_model=UserSkillsList)
async def remove_skill(
    name: str,
    user_id: str = Depends(get_current_user_id),
    supabase=Depends(get_supabase),
):
    skill_id = _resolve_skill_id(name, supabase)
    if not skill_id:
        raise HTTPException(status_code=404, detail="Skill not found")
    supabase.table("user_skills").delete().eq("user_id", user_id).eq(
        "skill_id", skill_id
    ).execute()
    return UserSkillsList(skills=_list_user_skills(user_id, supabase))
