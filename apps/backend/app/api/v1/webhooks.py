"""Webhook handlers for DPO Pay and WAHA WhatsApp."""

from fastapi import APIRouter, Request, Depends

from app.core.deps import get_supabase
from app.services.whatsapp import send_whatsapp_message, send_match_digest

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


# ─── WAHA WhatsApp Webhook ───

WHATSAPP_COMMANDS = {
    "hi": "welcome",
    "hello": "welcome",
    "menu": "menu",
    "help": "menu",
    "matches": "matches",
    "jobs": "matches",
    "cv": "cv_info",
    "plan": "subscription",
    "upgrade": "subscription",
    "more": "more_matches",
}


@router.post("/whatsapp")
async def whatsapp_webhook(
    request: Request,
    supabase=Depends(get_supabase),
):
    """Handle incoming WhatsApp messages from WAHA."""
    body = await request.json()

    event = body.get("event")
    if event != "message":
        return {"status": "ignored"}

    payload = body.get("payload", {})
    message_body = payload.get("body", "").strip().lower()
    from_number = payload.get("from", "").replace("@c.us", "")

    if not from_number or not message_body:
        return {"status": "ignored"}

    phone = f"+{from_number}"

    # Route to handler
    command = WHATSAPP_COMMANDS.get(message_body, "unknown")

    if command == "welcome":
        await send_whatsapp_message(
            phone,
            "*Welcome to Zed CV!* \n\n"
            "I help you find jobs that match your skills in Zambia.\n\n"
            "Commands:\n"
            "*matches* - See your job matches\n"
            "*cv* - Check your CV status\n"
            "*plan* - View subscription info\n"
            "*help* - Show this menu",
        )

    elif command == "menu":
        await send_whatsapp_message(
            phone,
            "*Zed CV Menu*\n\n"
            "*matches* - See your job matches\n"
            "*cv* - Check your CV status\n"
            "*plan* - View your plan\n"
            "*upgrade* - Upgrade your plan",
        )

    elif command == "matches":
        # Find user
        user_result = (
            supabase.table("users")
            .select("id")
            .eq("phone", phone)
            .limit(1)
            .execute()
        )

        if not user_result.data:
            await send_whatsapp_message(
                phone,
                "You haven't signed up yet! Visit zedcv.com to create your account and upload your CV.",
            )
        else:
            user_id = user_result.data[0]["id"]
            matches_result = (
                supabase.table("matches")
                .select("*, jobs(title, company)")
                .eq("user_id", user_id)
                .order("score", desc=True)
                .limit(5)
                .execute()
            )

            if matches_result.data:
                match_list = []
                for m in matches_result.data:
                    job = m.get("jobs", {})
                    match_list.append(
                        {
                            "title": job.get("title", "Unknown"),
                            "company": job.get("company", "Unknown"),
                            "score": m["score"],
                            "matched_skills": m.get("matched_skills", []),
                        }
                    )
                await send_match_digest(phone, match_list)
            else:
                await send_whatsapp_message(
                    phone,
                    "No matches yet. Upload your CV at zedcv.com and we'll start matching!",
                )

    elif command == "subscription":
        user_result = (
            supabase.table("users")
            .select("id, subscription_tier")
            .eq("phone", phone)
            .limit(1)
            .execute()
        )

        if user_result.data:
            tier = user_result.data[0]["subscription_tier"]
            tier_info = {
                "mwana": "Mwana (Free) - 5 matches/month",
                "mwezi": "Mwezi (K79/mo) - 25 matches/month + CV generation",
                "bwino": "Bwino (K199/mo) - Unlimited matches + cover letters",
            }
            await send_whatsapp_message(
                phone,
                f"*Your Plan:* {tier_info.get(tier, tier)}\n\n"
                f"Visit zedcv.com/pricing to upgrade.",
            )

    else:
        # Try to parse as a number (job selection from digest)
        if message_body.isdigit():
            num = int(message_body)
            if 1 <= num <= 5:
                await send_whatsapp_message(
                    phone,
                    f"Opening job #{num} details...\nVisit zedcv.com/matches for full details and to apply.",
                )
                return {"status": "ok"}

        await send_whatsapp_message(
            phone,
            "I didn't understand that. Reply *help* to see available commands.",
        )

    return {"status": "ok"}


# ─── DPO Pay Webhook ───

@router.post("/dpo")
async def dpo_webhook(
    request: Request,
    supabase=Depends(get_supabase),
):
    """Handle DPO Pay payment confirmation webhook.

    DPO sends XML payloads. We verify the transaction and update subscription.
    """
    body = await request.body()
    # TODO: Parse XML, verify signature, extract transaction details
    # For now, log the raw payload for development
    import logging
    logging.info(f"DPO webhook received: {body[:500]}")

    # Placeholder — full implementation requires:
    # 1. Parse XML to get TransactionToken, TransactionRef, Result
    # 2. Verify with DPO API: POST /API/v6/verifyToken
    # 3. If Result == "000" (success):
    #    - Update payments table status to "completed"
    #    - Update subscription tier and period
    #    - Send WhatsApp confirmation to user

    return {"status": "received"}
