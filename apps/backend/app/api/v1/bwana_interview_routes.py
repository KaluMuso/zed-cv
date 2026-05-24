"""Bwana Interview — mock interview chat and aptitude test packs (Super Standard)."""

import random
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.core.deps import get_current_user, get_supabase, require_tier_access
from app.core.rate_limit import limiter
from app.core.tier_gating import FEATURE_INTERVIEW_PREP
from app.services.bwana_interview import (
    MOCK_QUESTION_COUNT,
    PACK_TIME_LIMITS,
    aptitude_percentile,
    generate_final_summary,
    generate_first_question,
    generate_next_question,
    score_answer,
)

router = APIRouter(prefix="/interview", tags=["Interview"])

AptitudePack = Literal["numerical", "verbal", "abstract"]


class MockStartRequest(BaseModel):
    role_label: str = Field(..., min_length=1, max_length=200)


class MockStartResponse(BaseModel):
    session_id: str
    question: str
    question_number: int
    total_questions: int = MOCK_QUESTION_COUNT


class MockAnswerRequest(BaseModel):
    session_id: str
    answer: str = Field(..., min_length=1, max_length=8000)


class MockAnswerProgress(BaseModel):
    star_score: float
    feedback: str
    question_number: int
    total_questions: int = MOCK_QUESTION_COUNT


class MockFinalSummary(BaseModel):
    overall_score: float
    strengths: list[str]
    improvements: list[str]
    practice_areas: list[str]


class MockAnswerResponse(BaseModel):
    session_id: str
    progress: MockAnswerProgress | None = None
    next_question: str | None = None
    final_summary: MockFinalSummary | None = None


class AptitudeOption(BaseModel):
    label: str
    value: str


class AptitudeQuestion(BaseModel):
    id: str
    question_text: str
    options: list[AptitudeOption]


class AptitudePackResponse(BaseModel):
    pack: AptitudePack
    time_limit_seconds: int
    questions: list[AptitudeQuestion]


class AptitudeAnswerItem(BaseModel):
    question_id: str
    value: str


class AptitudeScoreRequest(BaseModel):
    pack: AptitudePack
    answers: list[AptitudeAnswerItem]
    elapsed_seconds: int = Field(..., ge=0, le=7200)


class AptitudeScoreResponse(BaseModel):
    pack: AptitudePack
    score: float
    percentile: float
    correct_count: int
    total_questions: int


class InterviewHistorySession(BaseModel):
    id: str
    role_label: str
    overall_score: float | None
    created_at: str | None


class InterviewHistoryAptitude(BaseModel):
    id: str
    pack: str
    score: float
    percentile: float | None
    elapsed_seconds: int | None
    completed_at: str | None


class InterviewHistoryResponse(BaseModel):
    mock_sessions: list[InterviewHistorySession]
    aptitude_scores: list[InterviewHistoryAptitude]


def _load_session(supabase, session_id: str, user_id: str) -> dict[str, Any]:
    res = (
        supabase.table("interview_sessions")
        .select("*")
        .eq("id", session_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not res.data:
        raise HTTPException(status_code=404, detail="Interview session not found")
    return res.data[0]


def _completed_count(questions: list[dict[str, Any]]) -> int:
    return sum(1 for q in questions if q.get("user_answer"))


def _pending_question(questions: list[dict[str, Any]]) -> dict[str, Any] | None:
    for q in reversed(questions):
        if q.get("question") and not q.get("user_answer"):
            return q
    return None


@router.post(
    "/mock/start",
    response_model=MockStartResponse,
    dependencies=[Depends(require_tier_access(FEATURE_INTERVIEW_PREP))],
)
@limiter.limit("10/minute")
async def mock_start(
    request: Request,
    body: MockStartRequest,
    current_user: dict = Depends(get_current_user),
    supabase=Depends(get_supabase),
):
    del request
    user_id = current_user["id"]
    role = body.role_label.strip()
    try:
        first_q = await generate_first_question(role, user_id=user_id)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    row = (
        supabase.table("interview_sessions")
        .insert(
            {
                "user_id": user_id,
                "role_label": role,
                "questions": [{"question": first_q}],
            }
        )
        .execute()
    )
    session_id = row.data[0]["id"] if row.data else ""
    if not session_id:
        raise HTTPException(status_code=500, detail="Could not create interview session")

    return MockStartResponse(
        session_id=session_id,
        question=first_q,
        question_number=1,
    )


@router.post(
    "/mock/answer",
    response_model=MockAnswerResponse,
    dependencies=[Depends(require_tier_access(FEATURE_INTERVIEW_PREP))],
)
@limiter.limit("20/minute")
async def mock_answer(
    request: Request,
    body: MockAnswerRequest,
    current_user: dict = Depends(get_current_user),
    supabase=Depends(get_supabase),
):
    del request
    user_id = current_user["id"]
    session = _load_session(supabase, body.session_id, user_id)
    role = session["role_label"]
    questions: list[dict[str, Any]] = list(session.get("questions") or [])
    pending = _pending_question(questions)
    if not pending:
        raise HTTPException(status_code=400, detail="No pending question for this session")

    q_num = _completed_count(questions) + 1
    prior_turns: list[dict[str, str]] = []
    for row in questions:
        if row.get("user_answer"):
            prior_turns.append(
                {
                    "role": "assistant",
                    "content": f"Question: {row.get('question')}",
                }
            )
            prior_turns.append(
                {"role": "user", "content": str(row.get("user_answer"))},
            )

    try:
        scored = await score_answer(
            role=role,
            question=str(pending["question"]),
            answer=body.answer.strip(),
            question_number=q_num,
            prior_turns=prior_turns,
            user_id=user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    pending["user_answer"] = body.answer.strip()
    pending["star_score"] = scored.get("star_score")
    pending["feedback"] = scored.get("feedback")

    progress = MockAnswerProgress(
        star_score=float(scored.get("star_score") or 0),
        feedback=str(scored.get("feedback") or ""),
        question_number=q_num,
    )

    if q_num >= MOCK_QUESTION_COUNT:
        try:
            summary = await generate_final_summary(
                role=role, transcript=questions, user_id=user_id
            )
        except ValueError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        supabase.table("interview_sessions").update(
            {
                "questions": questions,
                "overall_score": summary.get("overall_score"),
                "strengths": summary.get("strengths"),
                "improvements": summary.get("improvements"),
                "practice_areas": summary.get("practice_areas"),
            }
        ).eq("id", body.session_id).execute()
        return MockAnswerResponse(
            session_id=body.session_id,
            progress=progress,
            final_summary=MockFinalSummary(
                overall_score=float(summary.get("overall_score") or 0),
                strengths=list(summary.get("strengths") or []),
                improvements=list(summary.get("improvements") or []),
                practice_areas=list(summary.get("practice_areas") or []),
            ),
        )

    try:
        next_q = await generate_next_question(
            role=role,
            question_number=q_num + 1,
            prior_turns=prior_turns
            + [
                {"role": "assistant", "content": f"Question: {pending['question']}"},
                {"role": "user", "content": body.answer.strip()},
            ],
            user_id=user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    questions.append({"question": next_q})
    supabase.table("interview_sessions").update({"questions": questions}).eq(
        "id", body.session_id
    ).execute()

    return MockAnswerResponse(
        session_id=body.session_id,
        progress=progress,
        next_question=next_q,
    )


@router.get(
    "/aptitude/pack/{pack}",
    response_model=AptitudePackResponse,
    dependencies=[Depends(require_tier_access(FEATURE_INTERVIEW_PREP))],
)
async def aptitude_pack(
    pack: AptitudePack,
    current_user: dict = Depends(get_current_user),
    supabase=Depends(get_supabase),
):
    del current_user
    res = (
        supabase.table("aptitude_question_bank")
        .select("id, question_text, options")
        .eq("pack", pack)
        .limit(200)
        .execute()
    )
    rows = list(res.data or [])
    if len(rows) < 20:
        raise HTTPException(
            status_code=503,
            detail=(
                f"Aptitude pack '{pack}' is not ready yet. "
                "Ask an admin to run seed_aptitude_bank.py."
            ),
        )
    picked = random.sample(rows, 20)
    questions: list[AptitudeQuestion] = []
    for row in picked:
        opts_raw = row.get("options") or []
        options = [
            AptitudeOption(label=str(o.get("label", "")), value=str(o.get("value", "")))
            for o in opts_raw
            if isinstance(o, dict)
        ]
        questions.append(
            AptitudeQuestion(
                id=str(row["id"]),
                question_text=str(row["question_text"]),
                options=options,
            )
        )
    return AptitudePackResponse(
        pack=pack,
        time_limit_seconds=PACK_TIME_LIMITS[pack],
        questions=questions,
    )


@router.post(
    "/aptitude/score",
    response_model=AptitudeScoreResponse,
    dependencies=[Depends(require_tier_access(FEATURE_INTERVIEW_PREP))],
)
@limiter.limit("15/minute")
async def aptitude_score(
    request: Request,
    body: AptitudeScoreRequest,
    current_user: dict = Depends(get_current_user),
    supabase=Depends(get_supabase),
):
    del request
    user_id = current_user["id"]
    if len(body.answers) != 20:
        raise HTTPException(status_code=422, detail="Exactly 20 answers are required")

    ids = [a.question_id for a in body.answers]
    bank = (
        supabase.table("aptitude_question_bank")
        .select("id, correct_value")
        .eq("pack", body.pack)
        .in_("id", ids)
        .execute()
    )
    correct_map = {str(r["id"]): str(r["correct_value"]) for r in (bank.data or [])}
    correct = 0
    for item in body.answers:
        if correct_map.get(item.question_id) == item.value:
            correct += 1

    score = round((correct / 20.0) * 100.0, 1)
    percentile = aptitude_percentile(score)

    supabase.table("aptitude_scores").insert(
        {
            "user_id": user_id,
            "pack": body.pack,
            "score": score,
            "percentile": percentile,
            "elapsed_seconds": body.elapsed_seconds,
        }
    ).execute()

    return AptitudeScoreResponse(
        pack=body.pack,
        score=score,
        percentile=percentile,
        correct_count=correct,
        total_questions=20,
    )


@router.get(
    "/history",
    response_model=InterviewHistoryResponse,
    dependencies=[Depends(require_tier_access(FEATURE_INTERVIEW_PREP))],
)
async def interview_history(
    current_user: dict = Depends(get_current_user),
    supabase=Depends(get_supabase),
):
    user_id = current_user["id"]
    sessions_res = (
        supabase.table("interview_sessions")
        .select("id, role_label, overall_score, created_at")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(50)
        .execute()
    )
    scores_res = (
        supabase.table("aptitude_scores")
        .select("id, pack, score, percentile, elapsed_seconds, completed_at")
        .eq("user_id", user_id)
        .order("completed_at", desc=True)
        .limit(50)
        .execute()
    )
    mock_sessions = [
        InterviewHistorySession(
            id=str(r["id"]),
            role_label=str(r.get("role_label") or ""),
            overall_score=r.get("overall_score"),
            created_at=r.get("created_at"),
        )
        for r in (sessions_res.data or [])
    ]
    aptitude_scores = [
        InterviewHistoryAptitude(
            id=str(r["id"]),
            pack=str(r.get("pack") or ""),
            score=float(r.get("score") or 0),
            percentile=r.get("percentile"),
            elapsed_seconds=r.get("elapsed_seconds"),
            completed_at=r.get("completed_at"),
        )
        for r in (scores_res.data or [])
    ]
    return InterviewHistoryResponse(
        mock_sessions=mock_sessions,
        aptitude_scores=aptitude_scores,
    )
