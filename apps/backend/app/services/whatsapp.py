"""WAHA WhatsApp integration."""
import httpx
from app.core.config import get_settings


async def send_whatsapp_message(phone: str, text: str) -> dict:
    settings = get_settings()
    chat_id = phone.replace("+", "") + "@c.us"
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.waha_api_url}/api/sendText",
            json={"chatId": chat_id, "text": text, "session": "default"},
            headers={"X-Api-Key": settings.waha_api_key},
            timeout=10.0,
        )
        response.raise_for_status()
        return response.json()


async def send_whatsapp_otp(phone: str, code: str) -> dict:
    return await send_whatsapp_message(
        phone,
        f"*Zed CV* - Your verification code\n\nYour OTP code is: *{code}*\n\n"
        f"This code expires in 5 minutes.\nDo not share this code with anyone.",
    )


async def send_match_digest(phone: str, matches: list[dict]) -> dict:
    if not matches:
        return await send_whatsapp_message(
            phone, "No new job matches today. We'll keep looking! Update your CV for better results."
        )
    lines = ["*Zed CV* - Your Daily Job Matches\n"]
    for i, m in enumerate(matches[:5], 1):
        lines.append(f"{i}. *{m.get('title', 'Unknown')}* at {m.get('company', 'Unknown')}")
        lines.append(f"   Match: {round(m.get('score', 0))}%")
        skills = m.get("matched_skills", [])
        if skills:
            lines.append(f"   Skills: {', '.join(skills[:3])}")
        lines.append("")
    lines.append("Reply with a number (1-5) to see details.\nReply *MORE* for more matches.")
    return await send_whatsapp_message(phone, "\n".join(lines))


async def check_waha_health() -> bool:
    settings = get_settings()
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{settings.waha_api_url}/api/sessions",
                headers={"X-Api-Key": settings.waha_api_key},
                timeout=5.0,
            )
            return r.status_code == 200
    except Exception:
        return False
