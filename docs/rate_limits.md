# Rate limits (SlowAPI)

Server-side rate limiting protects public/auth surfaces before Lenco production
cutover. Limits are enforced in `apps/backend` via [SlowAPI](https://github.com/laurentS/slowapi).

## Storage backend

| Environment | Backend | Behaviour |
|-------------|---------|-----------|
| `REDIS_URL` set | Redis (optional Upstash) | Shared across replicas; survives container restart |
| `REDIS_URL` unset | In-memory | Resets on `docker compose up --force-recreate`; not shared across replicas |

Set `REDIS_URL` in production so OTP brute-force windows are not wiped by deploys.
See `apps/backend/.env.example`.

## Client identity

- **IP**: First hop in `X-Forwarded-For` (Caddy), else `request.client.host`.
- **Phone**: JSON `phone` on OTP routes (parsed by `RateLimitBodyMiddleware`).
- **User**: JWT `sub` from `Authorization: Bearer` when present; else IP.

## Enforced limits

| Method | Path | Limit | Key | Reason |
|--------|------|-------|-----|--------|
| POST | `/api/v1/auth/otp/request` | 5/hour | phone | Stops WAHA cost-burn / SMS spam per victim number |
| POST | `/api/v1/auth/otp/request` | 20/hour | IP | Caps distributed attacks across many numbers |
| POST | `/api/v1/auth/otp/verify` | 10/hour | phone | Brute-force guard on 6-digit codes (plus DB attempt counter) |
| POST | `/api/v1/auth/otp/verify` | 30/hour | IP | NAT/shared-office ceiling |
| POST | `/api/v1/cv/upload` | 3/day | user | Gemini parse+embed cost per account |
| POST | `/api/v1/cv/upload` | 5/day | IP | Shared-NAT abuse without auth rotation |
| POST | `/api/v1/matches/refresh` | 10/day | user | On-demand RPC is expensive; nightly batch covers normal use |
| POST | `/api/v1/bwana/chat` | 30/hour | user | LLM/webhook cost per subscriber |
| POST | `/api/v1/bwana/chat` | 5/minute | user | Burst guard against runaway client loops |
| POST | `/api/v1/subscription/verify-payment` | 30/hour | user | Lenco status polling after widget pay; blocks reference brute-force |
| POST | `/api/v1/webhooks/lenco` | *(none)* | — | HMAC-SHA512 verifies authenticity; Lenco retries need 2xx |

**Also limited elsewhere (unchanged in this pass):**

| Method | Path | Limit | Notes |
|--------|------|-------|-------|
| POST | `/api/v1/contact` | 2/hour | IP — public spam surface |
| GET | `/api/v1/me/export` | 1/hour | user — GDPR export cost |
| POST | `/api/v1/subscription/pay` | 3/minute | user — deprecated 410 route |

Global default: **200/minute per IP** on routes without explicit decorators.

## 429 response shape

Rate limit hits return **RFC 7807** `application/problem+json` with `type`
`https://api.zedapply.com/errors/too_many_requests`, plus standard SlowAPI
`Retry-After` / `X-RateLimit-*` headers when window stats are available.

## Manual verification (post-deploy)

OTP request (6th call should be 429):

```bash
for i in $(seq 1 6); do
  curl -X POST https://api.zedapply.com/api/v1/auth/otp/request \
    -H 'Content-Type: application/json' \
    -d '{"phone":"+260911000099"}' -o /dev/null -w "Attempt $i: %{http_code}\n"
  sleep 0.5
done
```

Expect `429` on attempt 6 with `Content-Type: application/problem+json` and
`Retry-After` present.

## Routes that may need limits later

| Route | Concern |
|-------|---------|
| `POST /api/v1/auth/login` | Not on `develop` yet; when added, use **30/hour per IP** for trusted-device bypass |
| `POST /api/v1/matches/trigger` | Superadmin/on-demand matching; currently 3/minute — consider aligning with `/refresh` daily cap for non-admins |
| `POST /api/v1/webhooks/dpo` | Signature optional today; add IP allowlist or low rate if DPO starts unsigned callbacks |
| `POST /api/v1/cv/analyze`, `/generate` | Gemini spend; authenticated users only |
| `POST /api/v1/jobs/*/apply` | Scraping / spam applications |

Do not loosen OTP or payment limits without a security review and Redis in prod.
