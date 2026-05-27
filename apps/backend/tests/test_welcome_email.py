"""Welcome email on OTP signup (BackgroundTasks + welcome_email_sent dedupe)."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.conftest import FakeSupabaseQuery


class TestSendWelcomeEmail:
    @pytest.mark.asyncio
    @patch("app.services.email._send", return_value=True)
    @patch("app.services.email.get_supabase")
    async def test_sends_and_sets_welcome_email_sent(
        self, mock_get_supabase, mock_send
    ):
        from app.services import email as email_mod

        supabase = MagicMock()
        mock_get_supabase.return_value = supabase
        update_chain = MagicMock()
        supabase.table.return_value.update.return_value.eq.return_value = update_chain

        await email_mod.send_welcome_email(
            "user-abc",
            "Jane Banda",
            "jane@example.com",
        )

        mock_send.assert_called_once()
        args = mock_send.call_args
        assert args[0][0] == "jane@example.com"
        assert args[0][1] == "Welcome to ZedApply"
        assert "Jane" in args[0][2]
        assert args[1]["idempotency_key"] == "welcome-email/user-abc"
        supabase.table.assert_called_with("users")
        supabase.table.return_value.update.assert_called_with(
            {"welcome_email_sent": True}
        )
        update_chain.execute.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.services.email._send", return_value=True)
    async def test_first_name_fallback_to_there(self, mock_send):
        from app.services import email as email_mod

        with patch("app.services.email.get_supabase", return_value=MagicMock()):
            await email_mod.send_welcome_email("user-abc", None, "jane@example.com")

        html = mock_send.call_args[0][2]
        assert "Hi there," in html

    @pytest.mark.asyncio
    async def test_noop_without_email(self):
        from app.services import email as email_mod

        with patch("app.services.email._send") as mock_send:
            await email_mod.send_welcome_email("user-abc", "Jane", None)
        mock_send.assert_not_called()

    @pytest.mark.asyncio
    @patch("app.services.email._send", return_value=False)
    async def test_does_not_set_flag_on_send_failure(self, mock_send):
        from app.services import email as email_mod

        with patch("app.services.email.get_supabase") as mock_get_supabase:
            await email_mod.send_welcome_email("user-abc", "Jane", "jane@example.com")
            mock_get_supabase.assert_not_called()


class TestOTPVerifyWelcomeScheduling:
    def _seed_new_user_verify(self, fake_supabase):
        fake_supabase.set_table(
            "otp_codes",
            FakeSupabaseQuery(
                data=[
                    {
                        "id": "otp-1",
                        "phone": "+260971234567",
                        "code": "123456",
                        "verified": False,
                        "attempts": 0,
                        "expires_at": "2099-12-31T00:00:00Z",
                    }
                ]
            ),
        )
        fake_supabase.set_table("users", FakeSupabaseQuery(data=[]))
        fake_supabase.set_table(
            "subscriptions",
            FakeSupabaseQuery(data=[{"id": "sub-1", "user_id": "fake-uuid-001"}]),
        )

    @patch("app.api.v1.auth.send_welcome_email", new_callable=AsyncMock)
    def test_new_user_schedules_welcome_email_background(
        self, mock_welcome, client, fake_supabase
    ):
        """New signup enqueues welcome email without blocking the 200 response."""
        self._seed_new_user_verify(fake_supabase)
        resp = client.post(
            "/api/v1/auth/otp/verify",
            json={
                "phone": "+260971234567",
                "code": "123456",
                "consent_accepted": True,
                "email": "newuser@example.com",
            },
        )
        assert resp.status_code == 200
        mock_welcome.assert_awaited_once_with(
            "fake-uuid-001",
            None,
            "newuser@example.com",
        )

    @patch("app.api.v1.auth.send_welcome_email", new_callable=AsyncMock)
    def test_existing_user_does_not_schedule_welcome_email(
        self, mock_welcome, client, fake_supabase
    ):
        """Re-login must not enqueue another welcome email."""
        fake_supabase.set_table(
            "otp_codes",
            FakeSupabaseQuery(
                data=[
                    {
                        "id": "otp-2",
                        "phone": "+260971234567",
                        "code": "123456",
                        "verified": False,
                        "attempts": 0,
                        "expires_at": "2099-12-31T00:00:00Z",
                    }
                ]
            ),
        )
        fake_supabase.set_table(
            "users",
            FakeSupabaseQuery(
                data=[
                    {
                        "id": "existing-uuid-9",
                        "role": "user",
                        "email": "existing@example.com",
                        "full_name": "Existing User",
                        "welcome_email_sent": True,
                    }
                ]
            ),
        )
        resp = client.post(
            "/api/v1/auth/otp/verify",
            json={"phone": "+260971234567", "code": "123456"},
        )
        assert resp.status_code == 200
        mock_welcome.assert_not_awaited()

    @patch("app.api.v1.auth.BackgroundTasks.add_task")
    def test_background_tasks_add_task_called_for_new_user(
        self, mock_add_task, client, fake_supabase
    ):
        """Verify OTP wires send_welcome_email through BackgroundTasks.add_task."""
        self._seed_new_user_verify(fake_supabase)
        resp = client.post(
            "/api/v1/auth/otp/verify",
            json={
                "phone": "+260971234567",
                "code": "123456",
                "consent_accepted": True,
                "email": "newuser@example.com",
            },
        )
        assert resp.status_code == 200
        mock_add_task.assert_called_once()
        task_fn, user_id, full_name, email = mock_add_task.call_args[0]
        from app.services.email import send_welcome_email

        assert task_fn is send_welcome_email
        assert user_id == "fake-uuid-001"
        assert full_name is None
        assert email == "newuser@example.com"
