"""Sensitive-action OTP gate (Bucket 8.5 prerequisite for Bucket 9)."""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

from app.core.config import get_settings
from app.services.otp import (
    SENSITIVE_ACTIONS,
    hash_otp_code,
    requires_otp_for_action,
    verify_sensitive_action_otp,
)
from tests.conftest import FakeSupabaseQuery


def test_sensitive_actions_include_delete_and_export():
    assert "delete_account" in SENSITIVE_ACTIONS
    assert "export_data" in SENSITIVE_ACTIONS
    assert requires_otp_for_action("delete_account") is True
    assert requires_otp_for_action(None) is False


def test_verify_sensitive_action_otp_rejects_bad_code(fake_supabase):
    phone = "+260971234567"
    fake_supabase.set_table("otp_codes", FakeSupabaseQuery(data=[]))
    settings = get_settings()
    with pytest.raises(HTTPException) as exc:
        verify_sensitive_action_otp(
            user_phone=phone,
            otp_code="000000",
            action="delete_account",
            supabase=fake_supabase,
            settings=settings,
        )
    assert exc.value.status_code == 401


def test_verify_sensitive_action_otp_accepts_valid_code(fake_supabase):
    phone = "+260971234567"
    settings = get_settings()
    code = "654321"
    fake_supabase.set_table(
        "otp_codes",
        FakeSupabaseQuery(
            data=[{
                "id": "otp-x",
                "phone": phone,
                "code": hash_otp_code(code, phone, settings.jwt_secret),
                "verified": False,
                "attempts": 0,
                "expires_at": (
                    datetime.now(timezone.utc) + timedelta(minutes=5)
                ).isoformat(),
            }]
        ),
    )
    verify_sensitive_action_otp(
        user_phone=phone,
        otp_code=code,
        action="export_data",
        supabase=fake_supabase,
        settings=settings,
    )
