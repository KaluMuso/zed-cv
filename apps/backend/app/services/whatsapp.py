"""WAHA WhatsApp integration service."""

import httpx

from app.core.config import get_settings


async def send_whatsapp_message(phone: str, text: str) -> dict:
    """Send a text message via WAHA API.

    Args:
        phone: Phone number in format +260XXXXXXXXX
        text: Message content
    """
    settings = get_settings()
    chat_id = phone.replace("+", "") + "@c.us"

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.waha_api_url}/api/sendText",
            json={
                "chatId": chat_id,
                "text": text,
                "session": "default",
            },
            headers={"Authorization": f"Bearer {settings.waha_api_key}"},
            timeout=10.0,
        )
        response.raise_for_status()
        return response.json()


async def send_whatsapp_otp(phone: str, code: str) -> dict:
    """Send OTP code via WhatsApp."""
    message = (
        f"*Zed CV* - Your verification code\n\n"
        f"Your OTP code is: *{code}*\n\n"
        f"This code expires in 5 minutes.\n"
        f"Do not share this code with anyone."
    )
    return await send_whatsapp_message(phone, message)


async def send_match_digest(phone: str, matches: list[dict]) -> dict:
    """Send daily job match digest via WhatsApp."""
    if not matches:
        return await send_whatsapp_message(
            phone,
            "No new job matches today. We'll keep looking! Update your CV for better results.",
        )

    lines = ["*Zed CV* - Your Daily Job Matches\n"]
    for i, match in enumerate(matches[:5], 1):
        score = round(match.get("score", 0))
        title = match.get("title", "Unknown Position")
        company = match.get("company", "Unknown Company")
        lines.append(f"{i}. *{title}* at {company}")
        lines.append(f"   Match: {score}%")
        matched = match.get("matched_skills", [])
        if matched:
            lines.append(f"   Skills: {', '.join(matched[:3])}")
        lines.append("")

    lines.append("Reply with a number (1-5) to see details.")
    lines.append("Reply *MORE* for more matches.")

    return await send_whatsapp_message(phone, "\n".join(lines))


async def check_waha_health() -> bool:
    """Check if WAHA is running and connected."""
    settings = get_settings()
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.waha_api_url}/api/sessions",
                headers={"Authorization": f"Bearer {settings.waha_api_key}"},
                timeout=5.0,
            )
            return response.status_code == 200
    except Exception:
        return False
