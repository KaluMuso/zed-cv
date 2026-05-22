"""Webhook handlers for WAHA WhatsApp and DPO Pay."""
import hmac
import logging
from fastapi import APIRouter, HTTPException, Request, Depends
from app.core.config import get_settings
from app.core.deps import get_supabase
from app.services.tier_config import (
    build_plan_info_by_tier,
    build_tier_display_names,
    get_tier_prices,
)
from app.services.whatsapp import send_whatsapp_message, send_match_digest
from app.services.email import send_payment_confirmation_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

COMMANDS = {"hi": "welcome", "hello": "welcome", "menu": "menu", "help": "menu",
            "matches": "matches", "jobs": "matches", "cv": "cv_info", "plan": "subscription", "upgrade": "subscription", "more": "more_matches"}


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
            # task #60: pass the new structured fields through. Pydantic
            # enum coercion handles string → EmploymentType / WorkArrangement
            # if the extractor returns a known value; an unknown value is
            # rejected here and the whole row falls into the ValidationError
            # branch below (safer than silently ingesting bad enum values).
            employment_type=extracted.employment_type,
            work_arrangement=extracted.work_arrangement,
            hybrid_days_per_week=extracted.hybrid_days_per_week,
            benefits=extracted.benefits,
            application_instructions=extracted.application_instructions,
            reporting_structure=extracted.reporting_structure,
            manages_others=extracted.manages_others,
            interview_process=extracted.interview_process,
            tools_tech_stack=extracted.tools_tech_stack,
            success_metrics=extracted.success_metrics,
            company_description=extracted.company_description,
            reference_number=extracted.reference_number,
            currency=extracted.currency,
            pay_frequency=extracted.pay_frequency,
            bonus_structure=extracted.bonus_structure,
            equity_offered=extracted.equity_offered,
            salary_text=extracted.salary_text,
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
    settings = get_settings()

    # Shared-secret auth. WAHA pins X-Webhook-Token via its customHeaders
    # config; we reject anything that doesn't match. Without this any
    # public caller could forge digest sends, enumerate phones, and (with
    # channel ingest on) inject jobs. Empty secret means dev/test only —
    # the warning is loud so the gap is obvious in logs.
    if settings.waha_webhook_secret:
        provided = request.headers.get("x-webhook-token", "")
        if not hmac.compare_digest(provided, settings.waha_webhook_secret):
            logger.warning("WhatsApp webhook: invalid or missing X-Webhook-Token")
            raise HTTPException(status_code=401, detail="Invalid webhook token")
    else:
        logger.warning(
            "WhatsApp webhook: WAHA_WEBHOOK_SECRET unset — accepting "
            "unauthenticated delivery (must be set in production)"
        )

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
            plan_info = await build_plan_info_by_tier(supabase)
            await send_whatsapp_message(
                phone,
                f"*Your Plan:* {plan_info.get(tier, tier)}\n\nVisit zedcv.com/pricing to upgrade.",
            )
    elif message_body.isdigit() and 1 <= int(message_body) <= get_settings().whatsapp_reply_max_index:
        await send_whatsapp_message(phone, f"Opening job #{message_body} details...\nVisit zedcv.com/matches for full details.")
    else:
        await send_whatsapp_message(phone, "I didn't understand that. Reply *help* to see available commands.")
    return {"status": "ok"}


@router.post("/dpo")
async def dpo_webhook(request: Request, supabase=Depends(get_supabase)):
    """Process DPO Pay webhook — verify payment and upgrade subscription.

    Authenticity verification (task #75) — two layers:
      1. CompanyToken in the XML body must match settings.dpo_pay_company_token
         (shared secret; an attacker without it can't forge a payload).
      2. verify_payment() callback to DPO's verifyToken API — DPO only
         returns "paid" for transactions it actually processed.

    Plus optional layer 3: if settings.dpo_pay_webhook_secret is set AND
    DPO ever starts emitting a signature header, verify HMAC-SHA256.
    Currently DPO doesn't sign webhooks, so this layer is opt-in.

    Mismatched CompanyToken → 401. The route purposely does not echo
    parse details on auth failure — minimises information leak to a
    probing attacker.
    """
    from fastapi import HTTPException
    from app.services.dpo_pay import parse_dpo_webhook_xml, verify_payment
    from app.services.dpo_webhook import (
        verify_company_token,
        verify_hmac_signature,
    )
    from app.core.config import get_settings

    settings = get_settings()
    raw_body = await request.body()
    logging.info(f"DPO webhook received: {raw_body[:500]}")

    parsed = parse_dpo_webhook_xml(raw_body)
    if not parsed or not parsed.get("transaction_token"):
        logging.warning("DPO webhook: missing or unparseable payload")
        return {"status": "ignored"}

    # Layer 1: CompanyToken verification. Required when we have a
    # configured token (which we always do in any environment running
    # paid flows). Empty configured token would be a misconfiguration —
    # log + reject so we fail loud rather than silently accepting
    # everything.
    if not settings.dpo_pay_company_token:
        logging.error(
            "DPO webhook: dpo_pay_company_token not configured — "
            "rejecting all webhooks until env is set"
        )
        raise HTTPException(status_code=503, detail="DPO not configured")
    if not verify_company_token(
        parsed.get("company_token", ""),
        settings.dpo_pay_company_token,
    ):
        logging.warning(
            "DPO webhook: CompanyToken mismatch — possible forgery, rejecting"
        )
        raise HTTPException(status_code=401, detail="Invalid CompanyToken")

    # Layer 1b (optional): HMAC signature header. Only verified when
    # settings.dpo_pay_webhook_secret is set AND DPO emits a signature.
    # When the secret is set but the header is missing → still reject
    # (deliberate: opting into HMAC means demanding it).
    if settings.dpo_pay_webhook_secret:
        provided_sig = request.headers.get("x-dpo-signature", "")
        if not verify_hmac_signature(
            raw_body, provided_sig, settings.dpo_pay_webhook_secret
        ):
            logging.warning(
                "DPO webhook: HMAC signature verification failed despite "
                "secret being configured — rejecting"
            )
            raise HTTPException(status_code=401, detail="Invalid Lenco signature")

    # Layer 2: Callback to DPO's verifyToken API. This is the strongest
    # check — only transactions DPO actually processed return "paid".
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
        from datetime import datetime, timezone

        # Determine tier from payment amount (ngwee). Reverse-lookup against
        # the canonical TIER_PRICES dict — exact-match wins, otherwise fall
        # back defensively to the highest paid tier whose price <= amount and
        # mark the payment as needing review. Done BEFORE the claim UPDATE
        # so the audit-trail flags land in the same write.
        amount_ngwee = payment["amount"]
        tier_prices = await get_tier_prices(supabase)
        paid_tiers = {
            price: tier
            for tier, price in tier_prices.items()
            if tier != "free"
        }
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
        now = datetime.now(timezone.utc)

        # Atomic idempotency: only complete the payment if it's still pending.
        # The SELECT-time check above handles the easy case (replay arrives
        # well after first completion). This conditional UPDATE handles the
        # hard case — two webhooks delivered within milliseconds both see
        # status='pending' at SELECT, both proceed; whichever loses the
        # race here matches 0 rows and bails out without re-upgrading the
        # subscription or re-stacking the period_end.
        claim_result = (
            supabase.table("payments").update({
                "status": "completed",
                "provider_ref": parsed.get("transaction_ref", parsed["transaction_token"]),
                "webhook_data": parsed,
                "completed_at": now.isoformat(),
            })
            .eq("id", payment_id)
            .eq("status", "pending")
            .execute()
        )
        if not claim_result.data:
            logging.info(
                f"DPO webhook: payment {payment_id} already claimed by concurrent delivery, skipping"
            )
            return {"status": "already_processed"}

        from app.services.subscription_billing import activate_subscription_after_payment

        activate_subscription_after_payment(
            supabase,
            user_id=user_id,
            payment_id=payment_id,
            new_tier=new_tier,
            subscription_row=payment.get("subscriptions"),
            now=now,
        )

        # Send WhatsApp + email confirmation
        user = supabase.table("users").select("phone").eq("id", user_id).single().execute()
        if user.data:
            display_names = await build_tier_display_names(supabase)
            tier_name = display_names.get(new_tier, new_tier)
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
    """Process Lenco v2 webhooks with mandatory HMAC-SHA512 signature verification.

    Signature key: sha256(LENCO_API_KEY).hexdigest() per Lenco docs.
    Handles collection.successful, collection.failed, and collection.settled.
    """
    from fastapi import HTTPException
    from datetime import datetime, timezone
    from app.core.config import get_settings
    from app.services.lenco_webhook import (
        verify_lenco_signature,
        extract_event_fields,
    )

    settings = get_settings()
    raw_body = await request.body()
    signature = request.headers.get("x-lenco-signature", "")

    if not settings.lenco_api_key:
        logging.error("Lenco webhook: LENCO_API_KEY not configured")
        raise HTTPException(
            status_code=500,
            detail="Lenco webhook verification not configured",
        )

    if not verify_lenco_signature(raw_body, signature, settings.lenco_api_key):
        logging.warning("lenco_webhook_invalid_signature")
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Safe to parse JSON.
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

    # Widget flow stores the widget reference on provider_ref; legacy rows
    # used payment id as company_ref.
    payment_result = (
        supabase.table("payments")
        .select("*, subscriptions(id, user_id, tier, current_period_end)")
        .eq("provider_ref", company_ref)
        .limit(1)
        .execute()
    )
    if not payment_result.data:
        payment_result = (
            supabase.table("payments")
            .select("*, subscriptions(id, user_id, tier, current_period_end)")
            .eq("id", company_ref)
            .limit(1)
            .execute()
        )
    if not payment_result.data and fields.get("lenco_ref"):
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

    if fields.get("is_settled"):
        supabase.table("payments").update({
            "webhook_data": payload,
        }).eq("id", payment_id).execute()
        logging.info("Lenco webhook: collection.settled for payment %s", payment_id)
        return {"status": "settled"}

    # Idempotency: a webhook for a completed payment must not re-upgrade.
    # Lenco can replay deliveries, and without this guard a duplicate
    # would reset matches_used to 0 mid-cycle.
    if payment.get("status") == "completed":
        logging.info("Lenco webhook: payment %s already processed", payment_id)
        return {"status": "already_processed"}

    if fields["is_paid"]:
        amount_ngwee = fields["amount_ngwee"] or payment["amount"]
        now = datetime.now(timezone.utc)

        # Resolve tier from amount — same logic as DPO. Exact match wins;
        # otherwise the highest paid tier whose price <= amount, flagged
        # for audit. Resolved here so the audit fields land in the same
        # write as the claim.
        tier_prices = await get_tier_prices(supabase)
        paid_tiers = {
            price: tier
            for tier, price in tier_prices.items()
            if tier != "free"
        }
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
        # Atomic idempotency — see DPO handler for the full reasoning. The
        # SELECT-time check above catches the easy replay case; this
        # conditional UPDATE handles concurrent deliveries that both saw
        # status='pending' at SELECT.
        claim_result = (
            supabase.table("payments").update({
                "status": "completed",
                "provider_ref": fields.get("lenco_ref") or company_ref,
                "webhook_data": payload,
                "completed_at": now.isoformat(),
            })
            .eq("id", payment_id)
            .eq("status", "pending")
            .execute()
        )
        if not claim_result.data:
            logging.info(
                "Lenco webhook: payment %s already claimed by concurrent delivery",
                payment_id,
            )
            return {"status": "already_processed"}

        from app.services.subscription_billing import activate_subscription_after_payment

        activate_subscription_after_payment(
            supabase,
            user_id=user_id,
            payment_id=payment_id,
            new_tier=new_tier,
            subscription_row=payment.get("subscriptions"),
            lenco_subscription_ref=fields.get("lenco_ref"),
            now=now,
        )

        # Notify on WhatsApp + email — best-effort, never fail the webhook.
        user = supabase.table("users").select("phone").eq("id", user_id).single().execute()
        if user.data:
            display_names = await build_tier_display_names(supabase)
            tier_name = display_names.get(new_tier, new_tier)
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
