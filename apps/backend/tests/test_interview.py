"""Bwana Interview — mock chat, aptitude packs, tier gate, history."""
from unittest.mock import AsyncMock, patch

import pytest

from tests.conftest import FakeSupabaseQuery


def _seed_user(fake_supabase, subscription_tier="super_standard"):
    fake_supabase.set_table(
        "users",
        FakeSupabaseQuery(
            data=[
                {
                    "id": "test-user-id",
                    "phone": "+260971234567",
                    "role": "user",
                    "subscription_tier": subscription_tier,
                    "matches_viewed_this_month": 0,
                    "billing_cycle_reset": "2099-06-01",
                }
            ]
        ),
    )


def _aptitude_bank_rows(pack: str, count: int = 25):
    return [
        {
            "id": f"{pack}-q-{i}",
            "pack": pack,
            "question_text": f"Question {i}?",
            "options": [
                {"label": "A", "value": "a"},
                {"label": "B", "value": "b"},
            ],
            "correct_value": "a",
        }
        for i in range(count)
    ]


@pytest.fixture
def mock_interview_llm():
    with (
        patch(
            "app.api.v1.bwana_interview_routes.generate_first_question",
            new_callable=AsyncMock,
            return_value="Tell me about a time you led a team.",
        ),
        patch(
            "app.api.v1.bwana_interview_routes.score_answer",
            new_callable=AsyncMock,
            return_value={"star_score": 7.5, "feedback": "Strong action; add metrics."},
        ),
        patch(
            "app.api.v1.bwana_interview_routes.generate_next_question",
            new_callable=AsyncMock,
            return_value="Describe a technical challenge you solved.",
        ),
        patch(
            "app.api.v1.bwana_interview_routes.generate_final_summary",
            new_callable=AsyncMock,
            return_value={
                "overall_score": 72.0,
                "strengths": ["Clarity", "Ownership", "Technical depth"],
                "improvements": ["Metrics", "Result framing", "Brevity"],
                "practice_areas": ["STAR drills", "System design", "Stakeholder updates"],
            },
        ),
    ):
        yield


class TestInterviewMock:
    def test_mock_start_returns_question(
        self, client, auth_headers, fake_supabase, mock_interview_llm
    ):
        _seed_user(fake_supabase)
        fake_supabase.set_table("interview_sessions", FakeSupabaseQuery())

        resp = client.post(
            "/api/v1/interview/mock/start",
            headers=auth_headers,
            json={"role_label": "Software Engineer"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["session_id"]
        assert "led a team" in body["question"]
        assert body["question_number"] == 1

    def test_mock_answer_returns_score_and_next_question(
        self, client, auth_headers, fake_supabase, mock_interview_llm
    ):
        _seed_user(fake_supabase)
        fake_supabase.set_table(
            "interview_sessions",
            FakeSupabaseQuery(
                data=[
                    {
                        "id": "sess-1",
                        "user_id": "test-user-id",
                        "role_label": "Software Engineer",
                        "questions": [{"question": "Q1?"}],
                    }
                ]
            ),
        )

        resp = client.post(
            "/api/v1/interview/mock/answer",
            headers=auth_headers,
            json={"session_id": "sess-1", "answer": "I led a migration project."},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["progress"]["star_score"] == 7.5
        assert body["next_question"]
        assert body["final_summary"] is None

    def test_mock_after_7_returns_summary(
        self, client, auth_headers, fake_supabase, mock_interview_llm
    ):
        _seed_user(fake_supabase)
        questions = [{"question": f"Q{i}?", "user_answer": "A", "star_score": 6, "feedback": "ok"} for i in range(6)]
        questions.append({"question": "Q7?"})
        fake_supabase.set_table(
            "interview_sessions",
            FakeSupabaseQuery(
                data=[
                    {
                        "id": "sess-7",
                        "user_id": "test-user-id",
                        "role_label": "Analyst",
                        "questions": questions,
                    }
                ]
            ),
        )

        resp = client.post(
            "/api/v1/interview/mock/answer",
            headers=auth_headers,
            json={"session_id": "sess-7", "answer": "Final answer with STAR."},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["final_summary"]["overall_score"] == 72.0
        assert len(body["final_summary"]["strengths"]) == 3
        assert body["next_question"] is None


class TestInterviewAptitude:
    def test_aptitude_pack_returns_20_questions(self, client, auth_headers, fake_supabase):
        _seed_user(fake_supabase)
        fake_supabase.set_table(
            "aptitude_question_bank",
            FakeSupabaseQuery(data=_aptitude_bank_rows("numerical")),
        )

        resp = client.get(
            "/api/v1/interview/aptitude/pack/numerical",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["pack"] == "numerical"
        assert len(body["questions"]) == 20
        assert body["time_limit_seconds"] == 1200

    def test_aptitude_score_calculates_percentile(self, client, auth_headers, fake_supabase):
        _seed_user(fake_supabase)
        rows = _aptitude_bank_rows("verbal", 20)
        fake_supabase.set_table(
            "aptitude_question_bank",
            FakeSupabaseQuery(data=rows),
        )
        fake_supabase.set_table("aptitude_scores", FakeSupabaseQuery())

        answers = [{"question_id": r["id"], "value": "a"} for r in rows]
        resp = client.post(
            "/api/v1/interview/aptitude/score",
            headers=auth_headers,
            json={"pack": "verbal", "answers": answers, "elapsed_seconds": 600},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["score"] == 100.0
        assert body["percentile"] > 99
        assert body["correct_count"] == 20


class TestInterviewTierGate:
    def test_tier_gate_blocks_starter_user(self, client, auth_headers, fake_supabase):
        _seed_user(fake_supabase, subscription_tier="starter")

        resp = client.post(
            "/api/v1/interview/mock/start",
            headers=auth_headers,
            json={"role_label": "Engineer"},
        )
        assert resp.status_code == 403
        assert "Super Standard" in resp.json()["detail"]


class TestInterviewHistory:
    def test_history_returns_sessions(self, client, auth_headers, fake_supabase):
        _seed_user(fake_supabase)
        fake_supabase.set_table(
            "interview_sessions",
            FakeSupabaseQuery(
                data=[
                    {
                        "id": "s1",
                        "role_label": "Dev",
                        "overall_score": 80,
                        "created_at": "2026-05-01T00:00:00Z",
                    }
                ]
            ),
        )
        fake_supabase.set_table(
            "aptitude_scores",
            FakeSupabaseQuery(
                data=[
                    {
                        "id": "a1",
                        "pack": "numerical",
                        "score": 65,
                        "percentile": 84.1,
                        "elapsed_seconds": 900,
                        "completed_at": "2026-05-02T00:00:00Z",
                    }
                ]
            ),
        )

        resp = client.get("/api/v1/interview/history", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["mock_sessions"]) == 1
        assert body["mock_sessions"][0]["role_label"] == "Dev"
        assert len(body["aptitude_scores"]) == 1


class TestAptitudeSeedScript:
    def test_aptitude_seed_script_idempotent(self, fake_supabase, monkeypatch):
        from scripts import seed_aptitude_bank as mod

        fake_supabase.set_table(
            "aptitude_question_bank",
            FakeSupabaseQuery(data=[{"pack": "numerical"}] * 60),
        )

        async def _noop_generate(*_a, **_k):
            return [], []

        monkeypatch.setattr(mod, "_generate_pack_questions", _noop_generate)
        monkeypatch.setattr(mod, "get_supabase", lambda: fake_supabase)

        import asyncio

        result = asyncio.run(mod.seed_pack("numerical", target=60))
        assert result == 0
