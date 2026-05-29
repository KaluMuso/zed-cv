"""Payment invoice rendering from completed payments (no separate invoices table)."""
from __future__ import annotations

from datetime import datetime, timezone
from html import escape
from typing import Any

from supabase import Client

from app.core.config import get_settings
from app.services.tier_config import get_tier_prices

TIER_LABELS = {
    "starter": "Starter",
    "professional": "Professional",
    "super_standard": "Super Standard",
    "free": "Free",
}


def invoice_number(payment_id: str) -> str:
    clean = payment_id.replace("-", "").upper()
    return f"ZED-{clean[:8]}"


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def _resolve_tier_from_payment(
    payment: dict[str, Any], tier_prices: dict[str, int]
) -> str:
    webhook = payment.get("webhook_data") or {}
    if isinstance(webhook, dict):
        resolved = webhook.get("_resolved_tier")
        if isinstance(resolved, str) and resolved in tier_prices:
            return resolved

    amount = int(payment.get("amount") or 0)
    if amount in tier_prices.values():
        for tier, price in tier_prices.items():
            if price == amount and tier != "free":
                return tier

    paid = {
        price: tier for tier, price in tier_prices.items() if tier != "free"
    }
    sorted_paid = sorted(paid.items())
    return next(
        (tier for price, tier in reversed(sorted_paid) if price <= amount),
        "starter",
    )


async def load_payment_invoice(
    supabase: Client,
    *,
    user_id: str,
    payment_id: str,
) -> dict[str, Any] | None:
    """Load payment + user fields needed for an invoice."""
    pay_res = (
        supabase.table("payments")
        .select(
            "id, user_id, amount, currency, payment_method, provider, "
            "provider_ref, status, created_at, completed_at, webhook_data"
        )
        .eq("id", payment_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not pay_res.data:
        return None

    payment = pay_res.data[0]
    user_res = (
        supabase.table("users")
        .select("full_name, email, phone")
        .eq("id", user_id)
        .limit(1)
        .execute()
    )
    user = (user_res.data or [{}])[0]
    tier_prices = await get_tier_prices(supabase)
    tier = _resolve_tier_from_payment(payment, tier_prices)
    issued_at = _parse_dt(payment.get("completed_at") or payment.get("created_at"))
    settings = get_settings()

    amount_ngwee = int(payment["amount"])
    return {
        "invoice_number": invoice_number(payment_id),
        "payment_id": payment_id,
        "user_id": user_id,
        "reference": payment.get("provider_ref") or payment_id,
        "status": payment.get("status") or "pending",
        "amount_ngwee": amount_ngwee,
        "amount_kwacha": amount_ngwee // 100,
        "currency": payment.get("currency") or "ZMW",
        "tier": tier,
        "tier_label": TIER_LABELS.get(tier, tier),
        "payment_method": payment.get("payment_method") or "lenco",
        "provider": payment.get("provider") or "lenco",
        "issued_at": issued_at.isoformat() if issued_at else None,
        "customer_name": user.get("full_name") or "Zed Apply customer",
        "customer_email": user.get("email"),
        "customer_phone": user.get("phone"),
        "company_name": "Zed Apply (Vergeo Company)",
        "company_email": settings.contact_email,
        "app_url": settings.app_url,
    }


def render_invoice_html(invoice: dict[str, Any]) -> str:
    """Self-contained HTML invoice suitable for download or email."""
    issued = invoice.get("issued_at") or datetime.now(timezone.utc).isoformat()
    try:
        issued_label = datetime.fromisoformat(
            str(issued).replace("Z", "+00:00")
        ).strftime("%d %b %Y")
    except (TypeError, ValueError):
        issued_label = str(issued)[:10]

    amount = int(invoice["amount_ngwee"])
    kwacha = amount // 100
    ref = escape(str(invoice.get("reference") or ""))
    inv_no = escape(str(invoice["invoice_number"]))
    tier = escape(str(invoice.get("tier_label") or ""))
    name = escape(str(invoice.get("customer_name") or ""))
    email = escape(str(invoice.get("customer_email") or "—"))
    phone = escape(str(invoice.get("customer_phone") or "—"))
    method = escape(str(invoice.get("payment_method") or "").replace("_", " "))
    provider = escape(str(invoice.get("provider") or ""))
    company = escape(str(invoice.get("company_name") or "Zed Apply"))
    support = escape(str(invoice.get("company_email") or ""))
    app_url = escape(str(invoice.get("app_url") or "https://zedapply.com"))

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>Invoice {inv_no}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; color: #111; max-width: 640px; margin: 2rem auto; }}
    h1 {{ font-size: 1.5rem; margin: 0 0 0.25rem; }}
    .muted {{ color: #666; font-size: 0.875rem; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 1.5rem; }}
    th, td {{ text-align: left; padding: 0.5rem 0; border-bottom: 1px solid #eee; }}
    .total {{ font-weight: 700; font-size: 1.125rem; }}
    footer {{ margin-top: 2rem; font-size: 0.75rem; color: #666; }}
  </style>
</head>
<body>
  <h1>Tax invoice / receipt</h1>
  <p class="muted">{company}</p>
  <p><strong>Invoice #</strong> {inv_no}<br/>
     <strong>Date</strong> {escape(issued_label)}<br/>
     <strong>Reference</strong> {ref}</p>
  <p><strong>Bill to</strong><br/>{name}<br/>{email}<br/>{phone}</p>
  <table>
    <thead><tr><th>Description</th><th>Amount</th></tr></thead>
    <tbody>
      <tr>
        <td>Zed Apply — {tier} plan (30 days)</td>
        <td>K{kwacha:,}</td>
      </tr>
      <tr class="total"><td>Total ({escape(str(invoice.get("currency") or "ZMW"))})</td><td>K{kwacha:,}</td></tr>
    </tbody>
  </table>
  <p class="muted">Paid via {method} ({provider}). Status: {escape(str(invoice.get("status") or ""))}.</p>
  <footer>
    Questions: {support} · <a href="{app_url}/settings/billing">Billing settings</a>
  </footer>
</body>
</html>"""
