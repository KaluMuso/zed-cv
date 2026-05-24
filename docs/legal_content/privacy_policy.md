# Privacy Policy

**Last updated:** 2026-05-24 · **Version:** 1.0.0

**Zed Apply** (ZedApply) is operated by **Vergeo Group**, a Zambian company based in Lusaka. Zed Apply is a subsidiary of Vergeo Group. This Privacy Policy explains how we collect, use, store, share, and protect your personal data when you use our job-matching platform, in compliance with the **Zambia Data Protection Act, 2021** ("ZDPA").

If you do not agree with this policy, please do not use the Service.

**Contact:** [convergeozambia@gmail.com](mailto:convergeozambia@gmail.com) (subject line: "Privacy request") · Lusaka, Zambia

## 1. Who is the data controller?

Vergeo Group (trading as Zed Apply / ZedApply) is the **data controller** for personal data described here. We determine the purposes and means of processing. Some providers listed below act as **data processors** on our instructions.

## 2. Personal data we collect

We collect only what we need to run the Service:

| Category | Examples |
| --- | --- |
| **Identity & account** | Name, Zambian mobile number (+260…), optional email |
| **Authentication** | OTP codes (hashed), verification timestamps |
| **CV & profile** | CV text, skills, experience, location and salary preferences |
| **Matching** | Match scores, explanations, saved/applied/dismissed jobs |
| **Payments** | Transaction references, amounts in ngwee, tier, status — not full card or PIN data |
| **WhatsApp** | Message content and metadata where you use our WhatsApp number |
| **Email** | Address and delivery metadata for transactional email |
| **Technical** | IP address, browser user agent, logs, security events |

We do **not** knowingly collect special-category data (health, ethnicity, political views, etc.). **Do not** include national registration numbers, bank details, or similar identifiers in your CV.

## 3. How we use AI on your CV

When you upload a CV we:

1. **Parse** text using AI models routed via **OpenRouter**, including **Google Gemini Flash**, to extract structured fields (skills, roles, education).
2. **Embed** a numerical vector representation (768 dimensions, cosine similarity) using **Google Gemini embedding** (`gemini-embedding-001`) for job matching.
3. **Generate** optional explanations, interview prep, tailored CVs, and cover letters on paid tiers.

CV text and derivatives are stored in **Supabase** (PostgreSQL). Embeddings are stored as vectors for matching only — they are not a complete copy of your CV but are derived from it.

Inputs are sent to AI providers under their enterprise/API terms. We configure providers not to use your content to train public foundation models where those controls exist.

## 4. Purposes of processing

- Deliver job matching, scores, and alerts (WhatsApp and email)
- Authenticate you via WhatsApp OTP
- Process subscriptions and enforce tier limits
- Prevent fraud, fake jobs, and abuse
- Comply with law (tax, accounting, lawful requests)
- Improve the Service using **de-identified, aggregated** statistics

## 5. Legal bases under the ZDPA

We rely on:

- **Contract** — account, matching, paid features, transactional WhatsApp/email
- **Legal obligation** — payment and tax records
- **Legitimate interests** — security, fraud prevention, service improvement (where not overridden by your rights)
- **Consent** — optional marketing and any non-essential analytics (withdraw anytime)

## 6. Recipients and processors

We use a limited set of processors:

- **Supabase** — database, authentication, file storage (including CV files)
- **OpenRouter** / **Google Gemini** — CV parsing, embeddings, explanations, interview prep, document generation
- **Lenco** — mobile-money payments
- **DPO Pay** — card and alternative payment flows
- **Resend** — transactional email
- **WAHA** — WhatsApp API gateway
- **n8n** — internal workflow automation (scraping orchestration, heartbeat, alerts)
- **Vercel** — frontend hosting

We do **not** sell your personal data to advertisers.

We may disclose data where required by Zambian law or to protect rights, safety, or security.

## 7. International transfers

Some processors are located outside Zambia (e.g. United States, EU). Where we transfer data abroad, we use safeguards permitted under the ZDPA, including contractual commitments on security and confidentiality. By using Zed Apply you acknowledge such transfers for the purposes above.

## 8. Retention

| Data | Retention |
| --- | --- |
| CV, profile, matches | Until account deletion; removed from active systems within **30 days**; backups may persist up to **90 days** |
| Payment records | **7 years** (tax/accounting) |
| Security / auth logs | **30 days** |
| WhatsApp records | Account lifetime, then deleted with account |
| De-identified analytics | May be retained indefinitely |

## 9. Your rights (data subject rights)

Under the ZDPA you may have the right to:

- **Access** — confirmation and copy of your data
- **Rectification** — correct inaccurate data
- **Erasure** — deletion subject to legal retention
- **Portability** — machine-readable export where feasible
- **Object** — to legitimate-interest processing, including marketing
- **Withdraw consent** — where processing is consent-based
- **Restrict or complain** — contact us first; you may lodge a complaint with the **Office of the Data Protection Commissioner** of Zambia

Exercise rights via account tools (export/delete where available) or email [convergeozambia@gmail.com](mailto:convergeozambia@gmail.com) with your registered phone number. We respond within **30 days**, subject to identity verification.

## 10. Security

Measures include TLS in transit, encryption at rest on Supabase, access controls, hashed OTPs, and processor due diligence. No system is perfectly secure. If a breach likely affects your rights, we will notify you and the Commissioner without undue delay as required by law.

## 11. WhatsApp and email channels

- **WhatsApp:** OTPs, match digests, and service messages to your registered +260 number. You can stop non-essential messages by adjusting preferences or contacting us.
- **Email:** Used when you provide an address (receipts, account notices). Marketing email requires consent where applicable.

## 12. Children

The Service is for adults (**18+**). We do not knowingly collect children's data. Contact us to delete inadvertent collection.

## 13. Cookies and similar technologies

See our [Cookie Policy](/legal/cookies) for browser storage we use. We do not use third-party advertising cookies today.

## 14. Changes

We may update this policy. The "Last updated" date shows the revision date. Material changes will be notified in-app or via WhatsApp at least **14 days** before effect, where practicable.

## 15. Contact

[convergeozambia@gmail.com](mailto:convergeozambia@gmail.com)
