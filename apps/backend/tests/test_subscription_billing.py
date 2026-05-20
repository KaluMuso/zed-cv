"""Tests for subscription billing-period activation and match counting."""
import asyncio
from datetime import datetime, timezone
from unittest.mock import MagicMock

from tests.conftest import FakeSupabaseQuery
from app.services.matching import get_credited_match_count, _billing_period_start
from app.services.subscription_billing import activate_subscription_after_payment


class TrackingQuery(FakeSupabaseQuery):
    """Captures filter/update args for assertions."""

    def __init__(self, data=None, count=None):
        super().__init__(data=data, count=count)
        self.updates: list[dict] = []
        self.gte_filters: list[tuple] = []

    def update(self, data):
        self.updates.append(data)
        return self

    def gte(self, col, val):
        self.gte_filters.append((col, val))
        return self


class RpcFakeSupabase:
    """Minimal client that records activate_subscription_after_payment RPC calls."""

    def __init__(self, rpc_result: dict):
        self.rpc_calls: list[tuple[str, dict]] = []
        self._rpc_result = rpc_result

    def rpc(self, name, args):
        self.rpc_calls.append((name, args))
        return MagicMock(
            execute=MagicMock(
                return_value=MagicMock(data=self._rpc_result),
            )
        )


class TestActivateSubscriptionAfterPayment:
    def test_delegates_to_postgres_rpc(self, monkeypatch):
        monkeypatch.setenv("SUBSCRIPTION_PERIOD_DAYS", "30")
        from app.core.config import get_settings
        get_settings.cache_clear()

        fake = RpcFakeSupabase(
            {
                "subscription_id": "sub-1",
                "period_start": "2026-05-20T12:00:00+00:00",
                "period_end": "2026-06-19T12:00:00+00:00",
            }
        )
        now = datetime(2026, 5, 20, 12, 0, tzinfo=timezone.utc)
        result = activate_subscription_after_payment(
            fake,  # type: ignore[arg-type]
            user_id="user-1",
            payment_id="pay-1",
            new_tier="starter",
            subscription_row={"id": "sub-1", "current_period_end": None},
            lenco_subscription_ref="LEN-abc",
            now=now,
        )

        assert fake.rpc_calls[0][0] == "activate_subscription_after_payment"
        args = fake.rpc_calls[0][1]
        assert args["p_user_id"] == "user-1"
        assert args["p_payment_id"] == "pay-1"
        assert args["p_new_tier"] == "starter"
        assert args["p_subscription_id"] == "sub-1"
        assert args["p_lenco_subscription_ref"] == "LEN-abc"
        assert result["end"] == "2026-06-19T12:00:00+00:00"


class TestBillingPeriodMatchCount:
    def test_uses_subscription_current_period_start(self, fake_supabase):
        period_start = "2026-05-10T00:00:00+00:00"
        matches_q = TrackingQuery(data=[{"id": "m1"}], count=3)
        fake_supabase.set_table(
            "subscriptions",
            FakeSupabaseQuery(
                data=[{"status": "active", "current_period_start": period_start}]
            ),
        )
        fake_supabase.set_table("matches", matches_q)

        used = asyncio.run(get_credited_match_count("user-1", fake_supabase))
        assert used == 3
        assert ("credited_at", period_start) in matches_q.gte_filters

    def test_billing_period_start_from_subscription(self, fake_supabase):
        period_start = "2026-04-15T08:00:00+00:00"
        fake_supabase.set_table(
            "subscriptions",
            FakeSupabaseQuery(
                data=[{"status": "active", "current_period_start": period_start}]
            ),
        )
        start = asyncio.run(_billing_period_start("user-1", fake_supabase))
        assert start.isoformat().startswith("2026-04-15")


class TestMigration035ActivateRpc:
    @staticmethod
    def _sql_path() -> str:
        from pathlib import Path

        return str(
            Path(__file__).resolve().parents[3]
            / "infra"
            / "supabase"
            / "migrations"
            / "035_activate_subscription_rpc.sql"
        )

    def test_migration_defines_activate_rpc(self):
        from pathlib import Path

        sql = Path(self._sql_path()).read_text()
        assert "CREATE OR REPLACE FUNCTION public.activate_subscription_after_payment" in sql
        assert "subscription_started_at" in sql
        assert "subscription_expires_at" in sql
        assert "p_existing_period_end" in sql
        assert "make_interval(days => p_period_days)" in sql


class TestMigration036DropCounters:
    @staticmethod
    def _sql_path() -> str:
        from pathlib import Path

        return str(
            Path(__file__).resolve().parents[3]
            / "infra"
            / "supabase"
            / "migrations"
            / "036_drop_subscription_match_counters.sql"
        )

    def test_migration_drops_legacy_counters(self):
        from pathlib import Path

        sql = Path(self._sql_path()).read_text()
        assert "DROP COLUMN IF EXISTS matches_used" in sql
        assert "DROP COLUMN IF EXISTS matches_limit" in sql
