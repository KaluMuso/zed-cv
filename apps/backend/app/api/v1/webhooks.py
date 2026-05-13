"""Webhook handlers for WAHA WhatsApp and DPO Pay."""
import logging
from fastapi import APIRouter, Request, Depends
from app.core.config import get_settings
from app.core.deps import get_supabase
from app.schemas.subscription import TIER_LIMITS, TIER_PRICES
from app.services.whatsapp import send_whatsapp_message, send_match_digest
from app.services.email import send_payment_confirmation_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

COMMANDS = {"hi": "welcome", "hello": "welcome", "menu": "menu", "help": "menu",
            "matches": "matches", "jobs": "matches", "cv": "cv_info", "plan": "subscription", "upgrade": "subscription", "more": "more_matches"}

# Human-readable tier labels used in WhatsApp + email payment-confirmation
# copy. Kept at module level so DPO and Lenco webhooks render the exact same
# wording — drift between the two would surface as inconsistent receipts.
# Prices match TIER_PRICES in app.schemas.subscription (ngwee → "K{kwacha}").
TIER_DISPLAY_NAMES = {
    "starter": "Starter (K125/mo)",
    "professional": "Professional (K250/mo)",
    "super_standard": "Super Standard (K500/mo)",
}

# Subscription plan info shown to users via WhatsApp "plan" / "upgrade"
# command. Free tier included since it's a valid state the user might be in.
PLAN_INFO_BY_TIER = {
    "free": "Free - 10 matches/month",
    "starter": "Starter (K125/mo) - 50 matches/month",
    "professional": "Professional (K250/mo) - 125 matches/month",
    "super_standard": "Super Standard (K500/mo) - Unlimited matches",
}


async def _handle_channel_message(payload: dict, supabase, settings) -> dict:
    """Slice F: extract a job from a channel post and feed it to the
    same ingest pipeline as the n8n scraper.

    Returns a status dict (WAHA logs the webhook response, so the ops
    team can read "ingested" / "duplicate" / "not_a_job" counts from
    the webhook tail). Never raises — channel messages aren't user
    requests, and a 500 here would have WAHA back off the entire
    webhook URL, breaking real user commands too.
    """
    from pydantic import ValidationError
    from app.services.job_extractor import extract_job_from_message
    from app.api.v1.jobs import _ingest_one_job, _build_aggregator_blacklist
    from app.schemas.jobs import JobCreate, JobSource

    raw_body = payload.get("body", "")
    msg_id = payload.get("id") or payload.get("messageId") or ""

    try:
        extracted = await extract_job_from_message(raw_body, supabase)
    except ValueError as e:
        # Hard infra failure (auth, rate limit) — log and let WAHA retry.
        logger.error("Slice F: extractor infrastructure failure: %s", e)
        return {"status": "extract_unavailable", "detail": str(e)[:120]}

    if extracted is None:
        # Below confidence floor, too short to be a job, or model said
        # "not a job". Quiet ignore — channel traffic is mostly non-job.
        return {"status": "not_a_job"}

    source_url = f"whatsapp://channel/{settings.whatsapp_channel_jobs_id}/{msg_id}"
    try:
        job_create = JobCreate(
            title=extracted.title,
            company=extracted.company,
            location=extracted.location,
            description=extracted.description,
            apply_url=extracted.apply_url,
            apply_email=extracted.apply_email,
            closing_date=extracted.closing_date,
            skills_required=extracted.skills_required,
            source=JobSource.scraper,
            source_url=source_url,
        )
    except ValidationError as ve:
        logger.warning(
            "Slice F: extractor output rejected by JobCreate validators: %s",
            ve.errors()[:2],
        )
        return {"status": "validation_failed"}

    blacklist = _build_aggregator_blacklist(settings)
    result, detail = await _ingest_one_job(supabase, job_create, blacklist)
    logger.info(
        "Slice F: channel msg %s → %s (title=%r)",
        msg_id, result, extracted.title,
    )
    return {
        "status": "ok",
        "ingest_result": result,
        "detail": detail or None,
        "title": extracted.title,
    }


@router.post("/whatsapp")
async def whatsapp_webhook(request: Request, supabase=Depends(get_supabase)):
    body = await request.json()
    if body.get("event") != "message":
        return {"status": "ignored"}

    payload = body.get("payload", {})

    # Slice F: WhatsApp channel ingest branch. When the configured jobs
    # channel posts a message AND the feature flag is on, route to the
    # structured-output extractor → _ingest_one_job pipeline instead of
    # the user-command handler. Channel chatIds end in `@newsletter`,
    # not `@c.us`, so they would otherwise fall through to the
    # "I didn't understand that" reply at the bottom of this handler.
    settings = get_settings()
    chat_id = payload.get("from") or payload.get("chatId") or ""
    if (
        settings.whatsapp_jobs_ingest_enabled
        and settings.whatsapp_channel_jobs_id
        and settings.whatsapp_channel_jobs_id in chat_id
    ):
        return await _handle_channel_message(payload, supabase, settings)

    message_body = payload.get("body", "").strip().lower()
    from_number = payload.get("from", "").replace("@c.us", "")
    if not from_number or not message_body:
        return {"status": "ignored"}

    phone = f"+{from_number}"
    command = COMMANDS.get(message_body, "unknown")

    if command == "welcome":
        await send_whatsapp_message(phone, "*Welcome to Zed CV!*\n\nI help you find jobs that match your skills in Zambia.\n\nCommands:\n*matches* - See your job matches\n*cv* - Check your CV status\n*plan* - View subscription info\n*help* - Show this menu")
    elif command == "menu":
        await send_whatsapp_message(phone, "*Zed CV Menu*\n\n*matches* - See your job matches\n*cv* - Check CV status\n*plan* - View your plan\n*upgrade* - Upgrade plan")
    elif command == "matches":
        user = supabase.table("users").select("id").eq("phone", phone).limit(1).execute()
        if not user.data:
            await send_whatsapp_message(phone, "You haven't signed up yet! Visit zedcv.com to create your account.")
        else:
            mr = supabase.table("matches").select("*, jobs(title, company)").eq("user_id", user.data[0]["id"]).order("score", desc=True).limit(5).execute()
            if mr.data:
                await send_match_digest(phone, [{"title": m.get("jobs", {}).get("title", "?"), "company": m.get("jobs", {}).get("company", "?"), "score": m["score"], "matched_skills": m.get("matched_skills", [])} for m in mr.data])
            else:
                await send_whatsapp_message(phone, "No matches yet. Upload your CV at zedcv.com and we'll start matching!")
    elif command == "subscription":
        user = supabase.table("users").select("id, subscription_tier").eq("phone", phone).limit(1).execute()
        if user.data:
            tier = user.data[0]["subscription_tier"]
            await send_whatsapp_message(phone, f"*Your Plan:* {PLAN_INFO_BY_TIER.get(tier, tier)}\n\nVisit zedcv.com/pricing to upgrade.")
    elif message_body.isdigit() and 1 <= int(message_body) <= get_settings().whatsapp_reply_max_index:
        await send_whatsapp_message(phone, f"Opening job #{message_body} details...\nVisit zedcv.com/matches for full details.")
    else:
        await send_whatsapp_message(phone, "I didn't understand that. Reply *help* to see available commands.")
    return {"status": "ok"}


@router.post("/dpo")
async def dpo_webhook(request: Request, supabase=Depends(get_supabase)):
    """Process DPO Pay webhook — verify payment and upgrade subscription."""
    from app.services.dpo_pay import parse_dpo_webhook_xml, verify_payment

    body = await request.body()
    logging.info(f"DPO webhook received: {body[:500]}")

    parsed = parse_dpo_webhook_xml(body)
    if not parsed or not parsed.get("transaction_token"):
        logging.warning("DPO webhook: missing or unparseable payload")
        return {"status": "ignored"}

    # Verify the payment with DPO
    try:
        verification = await verify_payment(parsed["transaction_token"])
    except ValueError as e:
        logging.error(f"DPO verification failed: {e}")
        return {"status": "verification_failed"}

    # Find payment record by provider_ref (transaction token)
    payment_result = (
        supabase.table("payments")
        .select("*, subscriptions(id, user_id, tier, current_period_end)")
        .eq("provider_ref", parsed["transaction_token"])
        .limit(1)
        .execute()
    )

    # If no match by token, try by payment ID in company_ref
    if not payment_result.data and parsed.get("company_ref"):
        payment_result = (
            supabase.table("payments")
            .select("*, subscriptions(id, user_id, tier, current_period_end)")
            .eq("id", parsed["company_ref"])
            .limit(1)
            .execute()
        )

    if not payment_result.data:
        logging.warning(f"DPO webhook: no matching payment for token={parsed['transaction_token']}")
        return {"status": "no_matching_payment"}

    payment = payment_result.data[0]
    payment_id = payment["id"]
    user_id = payment["user_id"]

    # Idempotency: a webhook for an already-completed payment must not re-upgrade
    # the subscription. DPO can replay or duplicate callbacks, and without this
    # guard a duplicate would re-run the upgrade and reset matches_used to 0.
    if payment.get("status") == "completed":
        logging.info(f"DPO webhook: payment {payment_id} already processed, skipping")
        return {"status": "already_processed"}

    if verification["is_paid"]:
        from datetime import datetime, timedelta, timezone

        # Update payment as completed
        supabase.table("payments").update({
            "status": "completed",
            "provider_ref": parsed.get("transaction_ref", parsed["transaction_token"]),
            "webhook_data": parsed,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", payment_id).execute()

        # Determine tier from payment amount (ngwee). Reverse-lookup against
        # the canonical TIER_PRICES dict — exact-match wins, otherwise fall
        # back defensively to the highest paid tier whose price <= amount and
        # mark the payment as needing review.
        amount_ngwee = payment["amount"]
        paid_tiers = {price: tier for tier, price in TIER_PRICES.items() if tier != "free"}
        new_tier = paid_tiers.get(amount_ngwee)
        if new_tier is None:
            logging.warning(
                f"DPO webhook: unknown amount {amount_ngwee} ngwee for payment {payment_id}, "
                f"falling back to highest tier <= amount"
            )
            sorted_paid = sorted(paid_tiers.items())  # ascending by price
            new_tier = next(
                (tier for price, tier in reversed(sorted_paid) if price <= amount_ngwee),
                "starter",
            )
            # Cheap audit trail — preserved by the webhook_data update below.
            parsed["_inexact_amount_match"] = True
            parsed["_resolved_tier"] = new_tier
        new_limit = TIER_LIMITS[new_tier]
        now = datetime.now(timezone.utc)

        # Period-end safety: if a webhook arrives mid-cycle (e.g. early renewal
        # or duplicate that bypassed the idempotency guard via a different
        # token), stack the new 30 days on top of any remaining paid days
        # rather than truncating the cycle.
        existing_end_str = (payment.get("subscriptions") or {}).get("current_period_end")
        existing_end = None
        if existing_end_str:
            try:
                existing_end = datetime.fromisoformat(existing_end_str.replace("Z", "+00:00"))
            except (TypeError, ValueError):
                existing_end = None
        base = existing_end if (existing_end and existing_end > now) else now
        new_period_end = base + timedelta(days=get_settings().subscription_period_days)

        # Upgrade subscription
        supabase.table("subscriptions").update({
            "tier": new_tier,
            "status": "active",
            "matches_limit": new_limit,
            "matches_used": 0,
            "current_period_start": now.isoformat(),
            "current_period_end": new_period_end.isoformat(),
        }).eq("user_id", user_id).execute()

        # Update user's subscription_tier field
        supabase.table("users").update({
            "subscription_tier": new_tier,
        }).eq("id", user_id).execute()

        # Send WhatsApp + email confirmation
        user = supabase.table("users").select("phone").eq("id", user_id).single().execute()
        if user.data:
            tier_name = TIER_DISPLAY_NAMES.get(new_tier, new_tier)
            try:
                await send_whatsapp_message(
                    user.data["phone"],
                    f"*Zed CV - Payment Confirmed!*\n\n"
                    f"Your payment of K{amount_ngwee // 100} has been received.\n"
                    f"You are now on the *{tier_name}* plan.\n\n"
                    f"Reply *matches* to see your job matches!"
                )
            except Exception as e:
                logging.error(f"Failed to send payment confirmation WhatsApp: {e}")

        try:
            await send_payment_confirmation_email(user_id, new_tier, amount_ngwee, supabase)
        except Exception as e:
            logging.error(f"Failed to send payment confirmation email: {e}")

        logging.info(f"Payment completed: user={user_id}, tier={new_tier}")
        return {"status": "completed"}

    else:
        # Payment failed or declined
        supabase.table("payments").update({
            "status": "failed",
            "webhook_data": parsed,
        }).eq("id", payment_id).execute()

        logging.info(f"Payment failed: user={user_id}, code={verification['result_code']}")
        return {"status": "failed"}


@router.post("/lenco")
async def lenco_webhook(request: Request, supabase=Depends(get_supabase)):
    """Process Lenco v2 webhook with HMAC-SHA512 signature verification.

    Signature is verified against `lenco_webhook_secret` first, then falls
    back to `lenco_api_key` (Lenco's documented default when no dedicated
    secret is provisioned). On valid signature + paid status, mirrors the
    DPO upgrade flow including idempotency + period-end stacking safety.

    Returns 401 on missing/invalid signature so Lenco retries (per their
    delivery semantics). Returns 200 with a status field on all valid-sig
    outcomes so Lenco stops retrying once delivery succeeded.
    """
    from fastapi import HTTPException
    from datetime import datetime, timedelta, timezone
    from app.core.config import get_settings
    from app.services.lenco_webhook import verify_signature, extract_event_fields

    settings = get_settings()
    raw_body = await request.body()
    signature = request.headers.get("x-lenco-signature", "")

    if not verify_signature(
        raw_body=raw_body,
        provided_signature=signature,
        webhook_secret=settings.lenco_webhook_secret,
        api_key=settings.lenco_api_key,
    ):
        logging.warning("Lenco webhook: signature verification failed")
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Signature ok — safe to parse JSON.
    import json
    try:
        payload = json.loads(raw_body.decode("utf-8") or "{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        logging.error("Lenco webhook: signed but unparseable body")
        return {"status": "invalid_payload"}

    fields = extract_event_fields(payload)
    logging.info(
        "Lenco webhook: event=%s status=%s ref=%s",
        fields.get("event"), fields.get("status_raw"), fields.get("company_ref"),
    )

    company_ref = fields.get("company_ref")
    if not company_ref:
        # No company_ref — can't match to a payment row. Acknowledge so
        # Lenco stops retrying.
        return {"status": "no_company_ref"}

    # Look up the payment by company_ref (which we set when initiating).
    payment_result = (
        supabase.table("payments")
        .select("*, subscriptions(id, user_id, tier, current_period_end)")
        .eq("id", company_ref)
        .limit(1)
        .execute()
    )
    if not payment_result.data:
        # Try by provider_ref as a fallback (in case we used Lenco's ref).
        if fields.get("lenco_ref"):
            payment_result = (
                supabase.table("payments")
                .select("*, subscriptions(id, user_id, tier, current_period_end)")
                .eq("provider_ref", fields["lenco_ref"])
                .limit(1)
                .execute()
            )

    if not payment_result.data:
        logging.warning("Lenco webhook: no matching payment for ref=%s", company_ref)
        return {"status": "no_matching_payment"}

    payment = payment_result.data[0]
    payment_id = payment["id"]
    user_id = payment["user_id"]

    # Idempotency: a webhook for a completed payment must not re-upgrade.
    # Lenco can replay deliveries, and without this guard a duplicate
    # would reset matches_used to 0 mid-cycle.
    if payment.get("status") == "completed":
        logging.info("Lenco webhook: payment %s already processed", payment_id)
        return {"status": "already_processed"}

    if fields["is_paid"]:
        amount_ngwee = fields["amount_ngwee"] or payment["amount"]
        now = datetime.now(timezone.utc)

        supabase.table("payments").update({
            "status": "completed",
            "provider_ref": fields.get("lenco_ref") or company_ref,
            "webhook_data": payload,
            "completed_at": now.isoformat(),
        }).eq("id", payment_id).execute()

        # Resolve tier from amount — same logic as DPO. Exact match wins;
        # otherwise the highest paid tier whose price <= amount, flagged
        # for audit.
        paid_tiers = {price: tier for tier, price in TIER_PRICES.items() if tier != "free"}
        new_tier = paid_tiers.get(amount_ngwee)
        if new_tier is None:
            logging.warning(
                "Lenco webhook: unknown amount %s ngwee for payment %s",
                amount_ngwee, payment_id,
            )
            sorted_paid = sorted(paid_tiers.items())
            new_tier = next(
                (tier for price, tier in reversed(sorted_paid) if price <= amount_ngwee),
                "starter",
            )
        new_limit = TIER_LIMITS[new_tier]

        # Period-end safety: stack on top of any remaining paid days.
        existing_end_str = (payment.get("subscriptions") or {}).get("current_period_end")
        existing_end = None
        if existing_end_str:
            try:
                existing_end = datetime.fromisoformat(existing_end_str.replace("Z", "+00:00"))
            except (TypeError, ValueError):
                existing_end = None
        base = existing_end if (existing_end and existing_end > now) else now
        new_period_end = base + timedelta(days=settings.subscription_period_days)

        supabase.table("subscriptions").update({
            "tier": new_tier,
            "status": "active",
            "matches_limit": new_limit,
            "matches_used": 0,
            "current_period_start": now.isoformat(),
            "current_period_end": new_period_end.isoformat(),
        }).eq("user_id", user_id).execute()

        supabase.table("users").update({
            "subscription_tier": new_tier,
        }).eq("id", user_id).execute()

        # Notify on WhatsApp + email — best-effort, never fail the webhook.
        user = supabase.table("users").select("phone").eq("id", user_id).single().execute()
        if user.data:
            tier_name = TIER_DISPLAY_NAMES.get(new_tier, new_tier)
            try:
                await send_whatsapp_message(
                    user.data["phone"],
                    f"*Zed CV - Payment Confirmed!*\n\n"
                    f"Your payment of K{amount_ngwee // 100} via Lenco has been received.\n"
                    f"You are now on the *{tier_name}* plan.\n\n"
                    f"Reply *matches* to see your job matches!"
                )
            except Exception as e:
                logging.error(f"Failed to send Lenco payment WhatsApp: {e}")

        try:
            await send_payment_confirmation_email(user_id, new_tier, amount_ngwee, supabase)
        except Exception as e:
            logging.error(f"Failed to send Lenco payment email: {e}")

        logging.info("Lenco payment completed: user=%s tier=%s", user_id, new_tier)
        return {"status": "completed"}

    elif fields["is_failed"]:
        supabase.table("payments").update({
            "status": "failed",
            "webhook_data": payload,
        }).eq("id", payment_id).execute()
        logging.info("Lenco payment failed: user=%s", user_id)
        return {"status": "failed"}

    # Pending / unrecognised status — store the webhook for audit but don't
    # change the payment yet.
    supabase.table("payments").update({
        "webhook_data": payload,
    }).eq("id", payment_id).execute()
    return {"status": "pending"}
