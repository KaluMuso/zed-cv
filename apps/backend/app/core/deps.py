"""Shared FastAPI dependencies."""
from functools import lru_cache
from typing import Callable

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from supabase import Client, create_client

from app.core.admin_auth import _admin_key_matches
from app.core.config import Settings, get_settings
from app.core.tier_gating import verify_tier_access

security = HTTPBearer()
security_optional = HTTPBearer(auto_error=False)


@lru_cache(maxsize=1)
def get_supabase() -> Client:
    """Cached Supabase client — single instance reused across all requests."""
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_key)


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    settings: Settings = Depends(get_settings),
) -> str:
    try:
        payload = jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token: missing subject")
        return user_id
    except JWTError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {str(e)}")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    settings: Settings = Depends(get_settings),
    supabase: Client = Depends(get_supabase),
) -> dict:
    """Return full user dict including role. Use this when you need role checks."""
    try:
        payload = jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except JWTError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {str(e)}")

    result = supabase.table("users").select("id, phone, role").eq("id", user_id).limit(1).execute()
    if not result.data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return result.data[0]


def is_superadmin(user: dict) -> bool:
    """Check if user has superadmin role."""
    return user.get("role") == "superadmin"


def is_admin_or_superadmin(user: dict) -> bool:
    """Check if user has admin-level access."""
    return user.get("role") in {"admin", "superadmin"}


async def require_superadmin(current_user: dict = Depends(get_current_user)) -> dict:
    """Dependency that 403s if the caller is not a superadmin."""
    if not is_superadmin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superadmin only")
    return current_user


async def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """Dependency that 403s if the caller is not admin or superadmin."""
    if not is_admin_or_superadmin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return current_user


def _ingest_key_matches(
    settings: Settings,
    ingest_api_key: str | None,
    x_ingest_api_key: str | None,
) -> bool:
    supplied = ingest_api_key or x_ingest_api_key
    return bool(settings.ingest_api_key and supplied == settings.ingest_api_key)


async def require_admin_api_key_or_superadmin(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_optional),
    admin_api_key: str | None = Header(None, alias="ADMIN_API_KEY"),
    x_admin_api_key: str | None = Header(None, alias="X-ADMIN-API-KEY"),
    ingest_api_key: str | None = Header(None, alias="INGEST_API_KEY"),
    x_ingest_api_key: str | None = Header(None, alias="X-INGEST-API-KEY"),
    settings: Settings = Depends(get_settings),
    supabase: Client = Depends(get_supabase),
) -> dict:
    """Superadmin Bearer JWT or admin/service API key (ADMIN_API_KEY / INGEST_API_KEY)."""
    if _admin_key_matches(
        settings,
        admin_api_key,
        x_admin_api_key,
        ingest_api_key,
        x_ingest_api_key,
    ):
        return {"auth": "api_key", "id": None, "role": "service"}

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Superadmin token or admin API key required",
        )

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
            )
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {str(e)}"
        )

    result = (
        supabase.table("users").select("id, phone, role").eq("id", user_id).limit(1).execute()
    )
    if not result.data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    user = result.data[0]
    if not is_superadmin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superadmin only")
    return user


async def require_admin_or_ingest_key(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_optional),
    ingest_api_key: str | None = Header(None, alias="INGEST_API_KEY"),
    x_ingest_api_key: str | None = Header(None, alias="X-INGEST-API-KEY"),
    settings: Settings = Depends(get_settings),
    supabase: Client = Depends(get_supabase),
) -> dict:
    """Admin JWT (Bearer) or n8n/service ingest key (INGEST_API_KEY header)."""
    if _ingest_key_matches(settings, ingest_api_key, x_ingest_api_key):
        return {"auth": "ingest", "role": "service"}

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin token or ingest API key required",
        )

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
            )
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {str(e)}"
        )

    result = (
        supabase.table("users").select("id, phone, role").eq("id", user_id).limit(1).execute()
    )
    if not result.data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    user = result.data[0]
    if not is_admin_or_superadmin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return user


def require_tier_access(required_feature: str) -> Callable:
    """FastAPI dependency factory for subscription tier gates.

    Usage:
        @router.get("/...", dependencies=[Depends(require_tier_access("job_matches"))])
    """

    async def _dependency(
        user_id: str = Depends(get_current_user_id),
        supabase: Client = Depends(get_supabase),
        current_user: dict = Depends(get_current_user),
    ) -> str:
        return await verify_tier_access(
            required_feature,
            user_id,
            supabase,
            is_superadmin=is_superadmin(current_user),
        )

    return _dependency
