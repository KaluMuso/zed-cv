# Bwana FAQ intents

Scripted FAQ patterns for the **ZedApply - Bwana Chat Pipeline** (n8n) and
`app/services/bwana_faq.py`. Matching is case-insensitive substring on the
user message (after trim).

| Intent ID | Trigger patterns (any match) | Response summary |
| --- | --- | --- |
| `apply` | how do i apply, how to apply, apply for jobs | Upload CV → matches → reply on WhatsApp digest |
| `pricing` | price, pricing, cost, how much, tier, plan, k125, k250, k500 | Free / Starter / Pro / Super Standard tiers |
| `cancel` | cancel, unsubscribe, stop subscription | Settings → subscription; WhatsApp Kaluba |
| `cv_location` | where is my cv, my cv, upload cv, cv status | Link to `/profile` CV tab |
| `matches` | my matches, job matches, no matches | `/matches`; improve CV skills |
| `digest` | digest, whatsapp time, daily message, 07:00 | Daily digest ~07:00 CAT via WAHA |
| `payment` | pay, lenco, mtn, airtel, mobile money, dpo | Lenco MTN/Airtel + card via DPO |
| `algorithm` | how matching works, match score, algorithm | 60% semantic + 30% skills + 10% bonus |
| `cover_letter` | cover letter | Professional tier; per-match generation |
| `tailored_cv` | tailored cv, rewrite cv, cv generator | Starter+ tailored CV feature |
| `otp` | otp, verification code, login code | WhatsApp OTP; 5 min expiry |
| `settings` | settings, account, profile settings | `/settings` preferences |
| `support_hours` | hours, when open, response time | Kaluba escalation within 24h |
| `free_tier` | free plan, free tier, 10 matches | Free: 10 matches/mo K0 |
| `starter_tier` | starter | Starter K125, 50 matches/mo |
| `professional_tier` | professional, pro plan | Professional K250, 125 matches/mo |
| `super_tier` | super standard, unlimited | Super Standard K500 unlimited |
| `interview` | interview prep, bwana interview | Super Standard `/interview-prep` |
| `privacy` | privacy, data, delete account | `/legal/privacy`; contact form |
| `hello` | hi, hello, hey bwana, good morning | Short greeting + what Bwana can do |

## Escalation keywords (not FAQ)

If the message contains any of: `talk to human`, `speak to a human`, `human support`,
`real person`, `support agent`, `customer support`, `kaluba`, or equals `support` /
`agent` (word boundary), route to **escalated** (WAHA to admin phone).

## LLM fallback

Any message that does not match FAQ or escalation goes to OpenRouter
(`google/gemini-2.0-flash-001`) with the Bwana system prompt and the last five
turns from `ai_cache` (`cache_type = bwana_chat`).
