"""Scripted FAQ intents for Bwana chat (sync fast path)."""
import re
from dataclasses import dataclass

from app.schemas.subscription import TIER_LIMITS, TIER_PRICES
from app.services.tier_marketing import TIER_WHATSAPP_BLURB

_ESCALATION_PHRASES = (
    "talk to human",
    "speak to a human",
    "human support",
    "real person",
    "support agent",
    "customer support",
    "kaluba",
)
_ESCALATION_WORDS = re.compile(
    r"\b(support|agent)\b", re.IGNORECASE
)


@dataclass(frozen=True)
class FaqMatch:
    intent_id: str
    response: str


def _kwacha(ngwee: int) -> str:
    if ngwee == 0:
        return "K0"
    return f"K{ngwee // 100}"


def _pricing_block() -> str:
    return (
        "ZedApply plans (ZMW/month):\n"
        f"• Free — {_kwacha(TIER_PRICES['free'])}, {TIER_LIMITS['free']} matches/mo\n"
        f"• Starter — {_kwacha(TIER_PRICES['starter'])}, {TIER_LIMITS['starter']} matches/mo\n"
        f"• Professional — {_kwacha(TIER_PRICES['professional'])}, "
        f"{TIER_LIMITS['professional']} matches/mo (+ cover letters)\n"
        f"• Super Standard — {_kwacha(TIER_PRICES['super_standard'])}, "
        "unlimited matches + Bwana Interview\n"
        "Upgrade at /pricing. Pay with MTN/Airtel (Lenco) or card (DPO)."
    )


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(n in text for n in needles)


def is_escalation_request(message: str) -> bool:
    """True when the user asks for a human."""
    norm = message.strip().lower()
    if _contains_any(norm, _ESCALATION_PHRASES):
        return True
    return bool(_ESCALATION_WORDS.search(norm))


def match_faq(message: str) -> FaqMatch | None:
    """Return a canned FAQ answer when the message matches a known intent."""
    norm = message.strip().lower()
    if not norm:
        return None

    if _contains_any(norm, ("how do i apply", "how to apply", "apply for job")):
        return FaqMatch(
            "apply",
            "To apply through ZedApply: upload your CV on /profile, wait for parsing "
            "(~1 min), then check /matches. Reply to your daily WhatsApp digest (around "
            "07:00) with 1–5 to see job details. Starter+ can generate tailored CVs per job.",
        )

    if _contains_any(
        norm,
        ("price", "pricing", "cost", "how much", " tier", "plan", "k125", "k250", "k500"),
    ):
        return FaqMatch("pricing", _pricing_block())

    if _contains_any(norm, ("cancel", "unsubscribe", "stop subscription", "stop paying")):
        return FaqMatch(
            "cancel",
            "Manage or cancel your plan in /settings → Subscription. Paid tiers renew "
            "monthly until you cancel. For billing help, type \"talk to human\" and "
            "Kaluba will WhatsApp you within 24 hours.",
        )

    if _contains_any(norm, ("where is my cv", "my cv", "upload cv", "cv status", "cv upload")):
        return FaqMatch(
            "cv_location",
            "Your CV lives on your profile: open /profile → CV & Skills. Upload PDF or "
            "DOCX there; we'll parse skills and refresh your matches.",
        )

    if _contains_any(norm, ("my matches", "job matches", "no matches", "see matches")):
        return FaqMatch(
            "matches",
            "View saved and fresh matches at /matches. If results are thin, add skills "
            "on /profile or upload a fuller CV — matching is 60% semantic fit + 30% skills.",
        )

    if _contains_any(norm, ("digest", "whatsapp time", "daily message", "07:00", "7am")):
        return FaqMatch(
            "digest",
            "We send a WhatsApp digest of your top matches around 07:00 CAT when you have "
            "new hits. Reply 1–5 for details, or MORE for extra matches.",
        )

    if _contains_any(norm, ("lenco", "mtn", "airtel", "mobile money", "dpo", "pay with")):
        return FaqMatch(
            "payment",
            "Pay in kwacha via Lenco (MTN or Airtel mobile money) or card through DPO on "
            "/pricing. You'll get a receipt on WhatsApp when payment confirms.",
        )

    if _contains_any(norm, ("matching works", "match score", "algorithm", "how do you match")):
        return FaqMatch(
            "algorithm",
            "Scores blend 60% CV–job semantic similarity (Gemini embeddings), 30% skill "
            "overlap, and 10% bonus signals (location, seniority). Scores ≥50% surface in "
            "your digest and /matches.",
        )

    if _contains_any(norm, ("cover letter",)):
        return FaqMatch(
            "cover_letter",
            "Cover letters are on the Professional plan (K250/mo): open a match → Generate "
            "cover letter. Each letter is ~200–250 words, editable, export PDF.",
        )

    if _contains_any(norm, ("tailored cv", "rewrite cv", "cv generator")):
        return FaqMatch(
            "tailored_cv",
            "Tailored CVs start on Starter (K125/mo): pick a job on /matches → Tailored CV. "
            "We reshape your CV for that role while keeping facts accurate.",
        )

    if _contains_any(norm, ("otp", "verification code", "login code")):
        return FaqMatch(
            "otp",
            "Sign in with your +260 number — we WhatsApp a 6-digit OTP (expires in 5 min). "
            "Request a new code after the cooldown if it doesn't arrive.",
        )

    if _contains_any(norm, ("settings", "account settings", "preferences")):
        return FaqMatch(
            "settings",
            "Update phone, digest preferences, and subscription at /settings.",
        )

    if _contains_any(norm, ("hours", "when open", "response time")):
        return FaqMatch(
            "support_hours",
            "Bwana is instant 24/7 for FAQs. Human support (Kaluba) replies on WhatsApp "
            "within 24h — type \"talk to human\" to escalate.",
        )

    if _contains_any(norm, ("free plan", "free tier", "10 matches")):
        return FaqMatch(
            "free_tier",
            f"Free tier: {_kwacha(TIER_PRICES['free'])}/mo, {TIER_LIMITS['free']} matches, "
            "CV upload + WhatsApp digest. Upgrade anytime on /pricing.",
        )

    if "starter" in norm and "professional" not in norm:
        return FaqMatch(
            "starter_tier",
            f"Starter: {_kwacha(TIER_PRICES['starter'])}/mo, {TIER_LIMITS['starter']} matches, "
            f"{TIER_WHATSAPP_BLURB['starter']}. Tailored CVs from Professional. See /pricing.",
        )

    if _contains_any(norm, ("professional", " pro plan", "pro tier")):
        return FaqMatch(
            "professional_tier",
            f"Professional: {_kwacha(TIER_PRICES['professional'])}/mo, "
            f"{TIER_LIMITS['professional']} matches, {TIER_WHATSAPP_BLURB['professional']}.",
        )

    if _contains_any(norm, ("super standard", "unlimited matches")):
        return FaqMatch(
            "super_tier",
            f"Super Standard: {_kwacha(TIER_PRICES['super_standard'])}/mo, unlimited matches, "
            "Bwana Interview prep at /interview-prep.",
        )

    if _contains_any(norm, ("interview prep", "bwana interview")):
        return FaqMatch(
            "interview",
            "Bwana Interview (quizzes, dress code, likely questions) is included on Super "
            "Standard (K500/mo) at /interview-prep.",
        )

    if _contains_any(norm, ("privacy", "delete account", "my data")):
        return FaqMatch(
            "privacy",
            "Read how we handle data at /legal/privacy. To delete your account or export "
            "data, use /contact or escalate to a human.",
        )

    if _contains_any(norm, ("hi", "hello", "hey bwana", "good morning", "good afternoon")):
        return FaqMatch(
            "hello",
            "Hey — I'm Bwana, ZedApply's career assistant. Ask about pricing, your CV, "
            "matches, or interview tips. Type \"talk to human\" for Kaluba.",
        )

    return None
