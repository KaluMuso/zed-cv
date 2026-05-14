"""DPO Pay (3G Direct Pay) integration for mobile money payments in Zambia.

DPO Pay uses an XML-based API. The flow:
1. Create payment token → returns TransToken + redirect URL
2. User completes payment on DPO's hosted page (or USSD push for mobile money)
3. DPO sends webhook to our /webhooks/dpo endpoint
4. We verify the transaction and update subscription

API docs: https://docs.dpogroup.com/
"""
import logging

import httpx
from defusedxml import ElementTree as ET

from app.core.config import get_settings

logger = logging.getLogger(__name__)


async def create_payment_token(
    amount_zmw: float,
    phone: str,
    description: str,
    payment_ref: str,
) -> dict:
    """Create a DPO payment token. Returns {token, redirect_url} or raises ValueError."""
    settings = get_settings()

    if not settings.dpo_pay_company_token:
        raise ValueError("DPO Pay is not configured. Please contact support.")

    # DPO requires amount as a string with 2 decimal places
    amount_str = f"{amount_zmw:.2f}"

    xml_payload = f"""<?xml version="1.0" encoding="utf-8"?>
<API3G>
  <CompanyToken>{settings.dpo_pay_company_token}</CompanyToken>
  <Request>createToken</Request>
  <Transaction>
    <PaymentAmount>{amount_str}</PaymentAmount>
    <PaymentCurrency>ZMW</PaymentCurrency>
    <CompanyRef>{payment_ref}</CompanyRef>
    <RedirectURL>https://zedcv.vercel.app/payment/success</RedirectURL>
    <BackURL>https://zedcv.vercel.app/payment/cancel</BackURL>
    <CompanyRefUnique>1</CompanyRefUnique>
    <PTL>24</PTL>
  </Transaction>
  <Services>
    <Service>
      <ServiceType>{settings.dpo_pay_service_type}</ServiceType>
      <ServiceDescription>{description}</ServiceDescription>
      <ServiceDate>{_today_str()}</ServiceDate>
    </Service>
  </Services>
</API3G>"""

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                settings.dpo_pay_api_url,
                content=xml_payload,
                headers={"Content-Type": "application/xml"},
                timeout=15.0,
            )
            response.raise_for_status()
    except httpx.HTTPError as e:
        logger.error(f"DPO Pay API request failed: {e}")
        raise ValueError("Payment service is temporarily unavailable. Please try again.")

    root = ET.fromstring(response.text)
    result_code = root.findtext("Result", "")
    result_explanation = root.findtext("ResultExplanation", "Unknown error")

    if result_code != "000":
        logger.error(f"DPO Pay createToken failed: {result_code} - {result_explanation}")
        raise ValueError(f"Payment could not be initiated: {result_explanation}")

    trans_token = root.findtext("TransToken", "")
    if not trans_token:
        raise ValueError("Payment service returned an invalid response.")

    redirect_url = f"https://secure.3gdirectpay.com/payv3.php?ID={trans_token}"

    return {"token": trans_token, "redirect_url": redirect_url}


async def verify_payment(transaction_token: str) -> dict:
    """Verify a payment with DPO Pay. Returns parsed status dict."""
    settings = get_settings()

    xml_payload = f"""<?xml version="1.0" encoding="utf-8"?>
<API3G>
  <CompanyToken>{settings.dpo_pay_company_token}</CompanyToken>
  <Request>verifyToken</Request>
  <TransactionToken>{transaction_token}</TransactionToken>
</API3G>"""

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                settings.dpo_pay_api_url,
                content=xml_payload,
                headers={"Content-Type": "application/xml"},
                timeout=15.0,
            )
            response.raise_for_status()
    except httpx.HTTPError as e:
        logger.error(f"DPO Pay verify request failed: {e}")
        raise ValueError("Could not verify payment status.")

    root = ET.fromstring(response.text)

    result_code = root.findtext("Result", "")
    result_explanation = root.findtext("ResultExplanation", "")
    transaction_ref = root.findtext("TransactionRef", "")
    customer_phone = root.findtext("CustomerPhone", "")
    transaction_amount = root.findtext("TransactionAmount", "0")
    transaction_currency = root.findtext("TransactionCurrency", "ZMW")

    # Result codes:
    # 000 = Transaction paid
    # 001 = Transaction authorized (pending settlement)
    # 002 = Transaction declined
    # 003 = Transaction pending
    is_paid = result_code in ("000", "001")

    return {
        "is_paid": is_paid,
        "result_code": result_code,
        "result_explanation": result_explanation,
        "transaction_ref": transaction_ref,
        "customer_phone": customer_phone,
        "amount": transaction_amount,
        "currency": transaction_currency,
    }


def parse_dpo_webhook_xml(body: bytes) -> dict:
    """Parse a DPO Pay webhook XML payload into a dict."""
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        logger.error(f"Failed to parse DPO webhook XML: {body[:500]}")
        return {}

    return {
        "company_ref": root.findtext("CompanyRef", ""),
        # CompanyToken is the shared secret between us and DPO. The webhook
        # signature-verification layer compares this against
        # settings.dpo_pay_company_token (task #75). DPO embeds our merchant
        # token in every webhook body; absence or mismatch means the
        # request is either misrouted or forged.
        "company_token": root.findtext("CompanyToken", ""),
        "transaction_token": root.findtext("TransactionToken", ""),
        "transaction_ref": root.findtext("TransactionRef", ""),
        "transaction_amount": root.findtext("TransactionAmount", "0"),
        "transaction_currency": root.findtext("TransactionCurrency", "ZMW"),
        "result_code": root.findtext("Result", ""),
        "result_explanation": root.findtext("ResultExplanation", ""),
        "customer_phone": root.findtext("CustomerPhone", ""),
    }


def _today_str() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y/%m/%d %H:%M")
