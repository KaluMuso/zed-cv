-- 063 — Seed legal_docs with ZDPA-compliant Zed Apply policies
-- Source of truth: docs/legal_content/*.md
-- Idempotent: upserts by slug so re-run is safe.

BEGIN;

-- terms_of_service.md -> slug 'terms'
INSERT INTO legal_docs (slug, version, content_md, content_html, last_modified_at)
VALUES (
  'terms',
  '1.0.0',
  $md_terms$
# Terms of Service

**Last updated:** 2026-05-24 · **Version:** 1.0.0

These Terms of Service ("Terms") govern your access to and use of **Zed Apply** (also branded **ZedApply**) — the website, mobile experience, WhatsApp channel, email notifications, and related services (together, "the Service"). Zed Apply is a subsidiary of **Vergeo Group**, based in Lusaka, Zambia.

By creating an account or otherwise using the Service, you agree to be bound by these Terms. If you do not agree, do not use the Service.

## 1. The Service

Zed Apply is an AI-powered job-matching platform for the Zambian market. We help you:

- upload or build a CV;
- parse and score your CV against open jobs in Zambia using vector similarity, skill overlap, experience, location, and recency signals;
- view tailored match explanations and (on paid tiers) interview preparation and AI-written application materials;
- receive job alerts via **WhatsApp** and, where you provide an email address, **transactional email**.

We may add, change, or remove features at any time. We will give reasonable notice for material changes that reduce paid features you are currently entitled to during an active billing period.

## 2. Eligibility

To use the Service you must:

- be at least **18 years old**;
- be a Zambian resident, or be actively seeking employment in Zambia;
- have the legal capacity to enter into a binding contract under Zambian law; and
- not be barred from using the Service under any applicable law or by a previous suspension of your account.

By using the Service you represent that you meet these requirements.

## 3. Your account

You sign in using your Zambian mobile phone number in **+260XXXXXXXXX** format and a one-time password ("OTP") delivered via WhatsApp. You are responsible for:

- providing **accurate and current** information (name, contact details, work experience, skills);
- keeping your phone number, WhatsApp account, and device secure;
- treating each OTP as a credential — never sharing it with anyone, including someone claiming to be from Zed Apply;
- promptly notifying us at [convergeozambia@gmail.com](mailto:convergeozambia@gmail.com) if you suspect unauthorised access.

You are responsible for all activity under your account.

## 4. Acceptable use

You agree **not** to:

- impersonate any person or misrepresent your affiliation;
- upload a CV that is not yours, or that contains false or misleading information;
- post, list, or promote fake jobs, scams, pyramid schemes, or unlawful opportunities;
- scrape, crawl, or harvest data from the Service in bulk without our written permission;
- reverse-engineer or disrupt the Service or related infrastructure;
- use the Service to send spam, harass others, or distribute malware;
- violate Zambian law or any other law applicable to you.

We may suspend or terminate accounts that breach this section.

## 5. Paid tiers, billing, and refunds

Paid subscription tiers, limits, and list prices are shown at [/pricing](/pricing). Checkout may reflect promotional pricing shown at purchase.

**Payment processors.** Payments are processed in Zambian Kwacha (ZMW) by **Lenco** (mobile money) and **DPO Pay** (cards and other methods). You authorise us, via these processors, to charge the payment method you choose. We do not store full card numbers or mobile-money PINs.

**Renewal and cancellation.** Paid tiers renew automatically at the end of each billing period unless you cancel. Cancellation stops future charges; paid access continues until the end of the current period. Cancel from account settings or email [convergeozambia@gmail.com](mailto:convergeozambia@gmail.com).

**Refund policy.** Detailed rules — including our **7-day money-back guarantee** for eligible first-time upgrades where no AI documents have been used — are in our standalone [Refund Policy](/legal/refund). That policy forms part of these Terms. In summary:

- eligible new paid subscriptions may receive a **full refund within 7 calendar days** if you have **not** generated AI documents (tailored CVs, cover letters, or similar) on your account;
- fees are generally **non-refundable** once AI documents have been generated or after the 7-day window;
- renewals are generally non-refundable once a new period starts.

**Failed payments.** If a payment fails, we may retry the charge and may downgrade your account to the free tier until payment succeeds.

## 6. Intellectual property

**Your content.** You retain ownership of CVs and other content you upload. You grant Zed Apply a non-exclusive licence to host, copy, process, transmit, and display that content **only to operate the Service for you** — including matching, explanations, WhatsApp delivery, and de-identified analytics. This licence ends when you delete content or your account, subject to retention in our [Privacy Policy](/legal/privacy).

**Our content.** The Service software, interface, branding, scores, and explanations are owned by Vergeo Group / Zed Apply and protected by intellectual property laws. You receive a personal, revocable licence to use the Service under these Terms.

## 7. AI-generated output

Match scores, explanations, interview notes, and AI-written CV or cover-letter drafts are provided **for your information only**. They are not legal, career, or financial advice. You are responsible for reviewing all materials before submitting them to employers.

## 8. WhatsApp and email

By opting in to WhatsApp delivery, you consent to receive transactional messages (OTPs, match digests, payment confirmations) on the number you register. Marketing messages require separate consent where required by law.

Email is used for account-related messages when you provide an address. See our [Privacy Policy](/legal/privacy) for how we process contact data.

## 9. Disclaimers

The Service is provided **"as is"** and **"as available"**. We do not guarantee that you will obtain employment, interviews, or any particular outcome. Job listings originate from third parties; we strive to filter scams but cannot warrant the accuracy of every posting.

To the fullest extent permitted by Zambian law, we disclaim implied warranties of merchantability, fitness for a particular purpose, and non-infringement.

## 10. Limitation of liability

To the fullest extent permitted by law, Vergeo Group, Zed Apply, and our officers, employees, and suppliers are not liable for indirect, incidental, special, consequential, or punitive damages, or for loss of profits, data, or goodwill, arising from your use of the Service.

Our aggregate liability for any claim arising from these Terms or the Service is limited to the greater of (a) the fees you paid to us in the **12 months** before the claim, or (b) **K50** (fifty Zambian Kwacha).

Nothing in these Terms limits liability that cannot be limited under Zambian law (including liability for fraud or personal injury caused by our negligence).

## 11. Indemnity

You agree to indemnify Vergeo Group and Zed Apply against claims arising from your breach of these Terms, your content, or your misuse of the Service, except where caused by our intentional misconduct.

## 12. Governing law and disputes

These Terms are governed by the laws of **Zambia**. You agree to the exclusive jurisdiction of the courts of Zambia, subject to any mandatory rights you have under consumer protection law.

Before formal proceedings, please contact [convergeozambia@gmail.com](mailto:convergeozambia@gmail.com) so we can try to resolve the dispute informally.

## 13. Changes to these Terms

We may update these Terms from time to time. The "Last updated" date at the top shows when they were last revised. Material changes will be notified in-app or via WhatsApp at least **14 days** before they take effect, where practicable. Continued use after the effective date constitutes acceptance.

## 14. Contact

Questions about these Terms: [convergeozambia@gmail.com](mailto:convergeozambia@gmail.com).

Related policies: [Privacy Policy](/legal/privacy), [Refund Policy](/legal/refund), [Cookie Policy](/legal/cookies).

$md_terms$,
  $html_terms$
<h1>Terms of Service</h1>
<p><strong>Last updated:</strong> 2026-05-24 · <strong>Version:</strong> 1.0.0</p>
<p>These Terms of Service ("Terms") govern your access to and use of <strong>Zed Apply</strong> (also branded <strong>ZedApply</strong>) — the website, mobile experience, WhatsApp channel, email notifications, and related services (together, "the Service"). Zed Apply is a subsidiary of <strong>Vergeo Group</strong>, based in Lusaka, Zambia.</p>
<p>By creating an account or otherwise using the Service, you agree to be bound by these Terms. If you do not agree, do not use the Service.</p>
<h2>1. The Service</h2>
<p>Zed Apply is an AI-powered job-matching platform for the Zambian market. We help you:</p>
<ul>
<li>upload or build a CV;</li>
<li>parse and score your CV against open jobs in Zambia using vector similarity, skill overlap, experience, location, and recency signals;</li>
<li>view tailored match explanations and (on paid tiers) interview preparation and AI-written application materials;</li>
<li>receive job alerts via <strong>WhatsApp</strong> and, where you provide an email address, <strong>transactional email</strong>.</li>
</ul>
<p>We may add, change, or remove features at any time. We will give reasonable notice for material changes that reduce paid features you are currently entitled to during an active billing period.</p>
<h2>2. Eligibility</h2>
<p>To use the Service you must:</p>
<ul>
<li>be at least <strong>18 years old</strong>;</li>
<li>be a Zambian resident, or be actively seeking employment in Zambia;</li>
<li>have the legal capacity to enter into a binding contract under Zambian law; and</li>
<li>not be barred from using the Service under any applicable law or by a previous suspension of your account.</li>
</ul>
<p>By using the Service you represent that you meet these requirements.</p>
<h2>3. Your account</h2>
<p>You sign in using your Zambian mobile phone number in <strong>+260XXXXXXXXX</strong> format and a one-time password ("OTP") delivered via WhatsApp. You are responsible for:</p>
<ul>
<li>providing <strong>accurate and current</strong> information (name, contact details, work experience, skills);</li>
<li>keeping your phone number, WhatsApp account, and device secure;</li>
<li>treating each OTP as a credential — never sharing it with anyone, including someone claiming to be from Zed Apply;</li>
<li>promptly notifying us at <a href="mailto:convergeozambia@gmail.com">convergeozambia@gmail.com</a> if you suspect unauthorised access.</li>
</ul>
<p>You are responsible for all activity under your account.</p>
<h2>4. Acceptable use</h2>
<p>You agree <strong>not</strong> to:</p>
<ul>
<li>impersonate any person or misrepresent your affiliation;</li>
<li>upload a CV that is not yours, or that contains false or misleading information;</li>
<li>post, list, or promote fake jobs, scams, pyramid schemes, or unlawful opportunities;</li>
<li>scrape, crawl, or harvest data from the Service in bulk without our written permission;</li>
<li>reverse-engineer or disrupt the Service or related infrastructure;</li>
<li>use the Service to send spam, harass others, or distribute malware;</li>
<li>violate Zambian law or any other law applicable to you.</li>
</ul>
<p>We may suspend or terminate accounts that breach this section.</p>
<h2>5. Paid tiers, billing, and refunds</h2>
<p>Paid subscription tiers, limits, and list prices are shown at <a href="/pricing">/pricing</a>. Checkout may reflect promotional pricing shown at purchase.</p>
<p><strong>Payment processors.</strong> Payments are processed in Zambian Kwacha (ZMW) by <strong>Lenco</strong> (mobile money) and <strong>DPO Pay</strong> (cards and other methods). You authorise us, via these processors, to charge the payment method you choose. We do not store full card numbers or mobile-money PINs.</p>
<p><strong>Renewal and cancellation.</strong> Paid tiers renew automatically at the end of each billing period unless you cancel. Cancellation stops future charges; paid access continues until the end of the current period. Cancel from account settings or email <a href="mailto:convergeozambia@gmail.com">convergeozambia@gmail.com</a>.</p>
<p><strong>Refund policy.</strong> Detailed rules — including our <strong>7-day money-back guarantee</strong> for eligible first-time upgrades where no AI documents have been used — are in our standalone <a href="/legal/refund">Refund Policy</a>. That policy forms part of these Terms. In summary:</p>
<ul>
<li>eligible new paid subscriptions may receive a <strong>full refund within 7 calendar days</strong> if you have <strong>not</strong> generated AI documents (tailored CVs, cover letters, or similar) on your account;</li>
<li>fees are generally <strong>non-refundable</strong> once AI documents have been generated or after the 7-day window;</li>
<li>renewals are generally non-refundable once a new period starts.</li>
</ul>
<p><strong>Failed payments.</strong> If a payment fails, we may retry the charge and may downgrade your account to the free tier until payment succeeds.</p>
<h2>6. Intellectual property</h2>
<p><strong>Your content.</strong> You retain ownership of CVs and other content you upload. You grant Zed Apply a non-exclusive licence to host, copy, process, transmit, and display that content <strong>only to operate the Service for you</strong> — including matching, explanations, WhatsApp delivery, and de-identified analytics. This licence ends when you delete content or your account, subject to retention in our <a href="/legal/privacy">Privacy Policy</a>.</p>
<p><strong>Our content.</strong> The Service software, interface, branding, scores, and explanations are owned by Vergeo Group / Zed Apply and protected by intellectual property laws. You receive a personal, revocable licence to use the Service under these Terms.</p>
<h2>7. AI-generated output</h2>
<p>Match scores, explanations, interview notes, and AI-written CV or cover-letter drafts are provided <strong>for your information only</strong>. They are not legal, career, or financial advice. You are responsible for reviewing all materials before submitting them to employers.</p>
<h2>8. WhatsApp and email</h2>
<p>By opting in to WhatsApp delivery, you consent to receive transactional messages (OTPs, match digests, payment confirmations) on the number you register. Marketing messages require separate consent where required by law.</p>
<p>Email is used for account-related messages when you provide an address. See our <a href="/legal/privacy">Privacy Policy</a> for how we process contact data.</p>
<h2>9. Disclaimers</h2>
<p>The Service is provided <strong>"as is"</strong> and <strong>"as available"</strong>. We do not guarantee that you will obtain employment, interviews, or any particular outcome. Job listings originate from third parties; we strive to filter scams but cannot warrant the accuracy of every posting.</p>
<p>To the fullest extent permitted by Zambian law, we disclaim implied warranties of merchantability, fitness for a particular purpose, and non-infringement.</p>
<h2>10. Limitation of liability</h2>
<p>To the fullest extent permitted by law, Vergeo Group, Zed Apply, and our officers, employees, and suppliers are not liable for indirect, incidental, special, consequential, or punitive damages, or for loss of profits, data, or goodwill, arising from your use of the Service.</p>
<p>Our aggregate liability for any claim arising from these Terms or the Service is limited to the greater of (a) the fees you paid to us in the <strong>12 months</strong> before the claim, or (b) <strong>K50</strong> (fifty Zambian Kwacha).</p>
<p>Nothing in these Terms limits liability that cannot be limited under Zambian law (including liability for fraud or personal injury caused by our negligence).</p>
<h2>11. Indemnity</h2>
<p>You agree to indemnify Vergeo Group and Zed Apply against claims arising from your breach of these Terms, your content, or your misuse of the Service, except where caused by our intentional misconduct.</p>
<h2>12. Governing law and disputes</h2>
<p>These Terms are governed by the laws of <strong>Zambia</strong>. You agree to the exclusive jurisdiction of the courts of Zambia, subject to any mandatory rights you have under consumer protection law.</p>
<p>Before formal proceedings, please contact <a href="mailto:convergeozambia@gmail.com">convergeozambia@gmail.com</a> so we can try to resolve the dispute informally.</p>
<h2>13. Changes to these Terms</h2>
<p>We may update these Terms from time to time. The "Last updated" date at the top shows when they were last revised. Material changes will be notified in-app or via WhatsApp at least <strong>14 days</strong> before they take effect, where practicable. Continued use after the effective date constitutes acceptance.</p>
<h2>14. Contact</h2>
<p>Questions about these Terms: <a href="mailto:convergeozambia@gmail.com">convergeozambia@gmail.com</a>.</p>
<p>Related policies: <a href="/legal/privacy">Privacy Policy</a>, <a href="/legal/refund">Refund Policy</a>, <a href="/legal/cookies">Cookie Policy</a>.</p>
$html_terms$,
  NOW()
)
ON CONFLICT (slug) DO UPDATE SET
  version = EXCLUDED.version,
  content_md = EXCLUDED.content_md,
  content_html = EXCLUDED.content_html,
  last_modified_at = EXCLUDED.last_modified_at;

-- privacy_policy.md -> slug 'privacy'
INSERT INTO legal_docs (slug, version, content_md, content_html, last_modified_at)
VALUES (
  'privacy',
  '1.0.0',
  $md_privacy$
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

$md_privacy$,
  $html_privacy$
<h1>Privacy Policy</h1>
<p><strong>Last updated:</strong> 2026-05-24 · <strong>Version:</strong> 1.0.0</p>
<p><strong>Zed Apply</strong> (ZedApply) is operated by <strong>Vergeo Group</strong>, a Zambian company based in Lusaka. Zed Apply is a subsidiary of Vergeo Group. This Privacy Policy explains how we collect, use, store, share, and protect your personal data when you use our job-matching platform, in compliance with the <strong>Zambia Data Protection Act, 2021</strong> ("ZDPA").</p>
<p>If you do not agree with this policy, please do not use the Service.</p>
<p><strong>Contact:</strong> <a href="mailto:convergeozambia@gmail.com">convergeozambia@gmail.com</a> (subject line: "Privacy request") · Lusaka, Zambia</p>
<h2>1. Who is the data controller?</h2>
<p>Vergeo Group (trading as Zed Apply / ZedApply) is the <strong>data controller</strong> for personal data described here. We determine the purposes and means of processing. Some providers listed below act as <strong>data processors</strong> on our instructions.</p>
<h2>2. Personal data we collect</h2>
<p>We collect only what we need to run the Service:</p>
<table>
<thead>
<tr>
<th>Category</th>
<th>Examples</th>
</tr>
</thead>
<tbody>
<tr>
<td><strong>Identity &amp; account</strong></td>
<td>Name, Zambian mobile number (+260…), optional email</td>
</tr>
<tr>
<td><strong>Authentication</strong></td>
<td>OTP codes (hashed), verification timestamps</td>
</tr>
<tr>
<td><strong>CV &amp; profile</strong></td>
<td>CV text, skills, experience, location and salary preferences</td>
</tr>
<tr>
<td><strong>Matching</strong></td>
<td>Match scores, explanations, saved/applied/dismissed jobs</td>
</tr>
<tr>
<td><strong>Payments</strong></td>
<td>Transaction references, amounts in ngwee, tier, status — not full card or PIN data</td>
</tr>
<tr>
<td><strong>WhatsApp</strong></td>
<td>Message content and metadata where you use our WhatsApp number</td>
</tr>
<tr>
<td><strong>Email</strong></td>
<td>Address and delivery metadata for transactional email</td>
</tr>
<tr>
<td><strong>Technical</strong></td>
<td>IP address, browser user agent, logs, security events</td>
</tr>
</tbody>
</table>
<p>We do <strong>not</strong> knowingly collect special-category data (health, ethnicity, political views, etc.). <strong>Do not</strong> include national registration numbers, bank details, or similar identifiers in your CV.</p>
<h2>3. How we use AI on your CV</h2>
<p>When you upload a CV we:</p>
<ol>
<li><strong>Parse</strong> text using AI models routed via <strong>OpenRouter</strong>, including <strong>Google Gemini Flash</strong>, to extract structured fields (skills, roles, education).</li>
<li><strong>Embed</strong> a numerical vector representation (768 dimensions, cosine similarity) using <strong>Google Gemini embedding</strong> (<code>gemini-embedding-001</code>) for job matching.</li>
<li><strong>Generate</strong> optional explanations, interview prep, tailored CVs, and cover letters on paid tiers.</li>
</ol>
<p>CV text and derivatives are stored in <strong>Supabase</strong> (PostgreSQL). Embeddings are stored as vectors for matching only — they are not a complete copy of your CV but are derived from it.</p>
<p>Inputs are sent to AI providers under their enterprise/API terms. We configure providers not to use your content to train public foundation models where those controls exist.</p>
<h2>4. Purposes of processing</h2>
<ul>
<li>Deliver job matching, scores, and alerts (WhatsApp and email)</li>
<li>Authenticate you via WhatsApp OTP</li>
<li>Process subscriptions and enforce tier limits</li>
<li>Prevent fraud, fake jobs, and abuse</li>
<li>Comply with law (tax, accounting, lawful requests)</li>
<li>Improve the Service using <strong>de-identified, aggregated</strong> statistics</li>
</ul>
<h2>5. Legal bases under the ZDPA</h2>
<p>We rely on:</p>
<ul>
<li><strong>Contract</strong> — account, matching, paid features, transactional WhatsApp/email</li>
<li><strong>Legal obligation</strong> — payment and tax records</li>
<li><strong>Legitimate interests</strong> — security, fraud prevention, service improvement (where not overridden by your rights)</li>
<li><strong>Consent</strong> — optional marketing and any non-essential analytics (withdraw anytime)</li>
</ul>
<h2>6. Recipients and processors</h2>
<p>We use a limited set of processors:</p>
<ul>
<li><strong>Supabase</strong> — database, authentication, file storage (including CV files)</li>
<li><strong>OpenRouter</strong> / <strong>Google Gemini</strong> — CV parsing, embeddings, explanations, interview prep, document generation</li>
<li><strong>Lenco</strong> — mobile-money payments</li>
<li><strong>DPO Pay</strong> — card and alternative payment flows</li>
<li><strong>Resend</strong> — transactional email</li>
<li><strong>WAHA</strong> — WhatsApp API gateway</li>
<li><strong>n8n</strong> — internal workflow automation (scraping orchestration, heartbeat, alerts)</li>
<li><strong>Vercel</strong> — frontend hosting</li>
</ul>
<p>We do <strong>not</strong> sell your personal data to advertisers.</p>
<p>We may disclose data where required by Zambian law or to protect rights, safety, or security.</p>
<h2>7. International transfers</h2>
<p>Some processors are located outside Zambia (e.g. United States, EU). Where we transfer data abroad, we use safeguards permitted under the ZDPA, including contractual commitments on security and confidentiality. By using Zed Apply you acknowledge such transfers for the purposes above.</p>
<h2>8. Retention</h2>
<table>
<thead>
<tr>
<th>Data</th>
<th>Retention</th>
</tr>
</thead>
<tbody>
<tr>
<td>CV, profile, matches</td>
<td>Until account deletion; removed from active systems within <strong>30 days</strong>; backups may persist up to <strong>90 days</strong></td>
</tr>
<tr>
<td>Payment records</td>
<td><strong>7 years</strong> (tax/accounting)</td>
</tr>
<tr>
<td>Security / auth logs</td>
<td><strong>30 days</strong></td>
</tr>
<tr>
<td>WhatsApp records</td>
<td>Account lifetime, then deleted with account</td>
</tr>
<tr>
<td>De-identified analytics</td>
<td>May be retained indefinitely</td>
</tr>
</tbody>
</table>
<h2>9. Your rights (data subject rights)</h2>
<p>Under the ZDPA you may have the right to:</p>
<ul>
<li><strong>Access</strong> — confirmation and copy of your data</li>
<li><strong>Rectification</strong> — correct inaccurate data</li>
<li><strong>Erasure</strong> — deletion subject to legal retention</li>
<li><strong>Portability</strong> — machine-readable export where feasible</li>
<li><strong>Object</strong> — to legitimate-interest processing, including marketing</li>
<li><strong>Withdraw consent</strong> — where processing is consent-based</li>
<li><strong>Restrict or complain</strong> — contact us first; you may lodge a complaint with the <strong>Office of the Data Protection Commissioner</strong> of Zambia</li>
</ul>
<p>Exercise rights via account tools (export/delete where available) or email <a href="mailto:convergeozambia@gmail.com">convergeozambia@gmail.com</a> with your registered phone number. We respond within <strong>30 days</strong>, subject to identity verification.</p>
<h2>10. Security</h2>
<p>Measures include TLS in transit, encryption at rest on Supabase, access controls, hashed OTPs, and processor due diligence. No system is perfectly secure. If a breach likely affects your rights, we will notify you and the Commissioner without undue delay as required by law.</p>
<h2>11. WhatsApp and email channels</h2>
<ul>
<li><strong>WhatsApp:</strong> OTPs, match digests, and service messages to your registered +260 number. You can stop non-essential messages by adjusting preferences or contacting us.</li>
<li><strong>Email:</strong> Used when you provide an address (receipts, account notices). Marketing email requires consent where applicable.</li>
</ul>
<h2>12. Children</h2>
<p>The Service is for adults (<strong>18+</strong>). We do not knowingly collect children's data. Contact us to delete inadvertent collection.</p>
<h2>13. Cookies and similar technologies</h2>
<p>See our <a href="/legal/cookies">Cookie Policy</a> for browser storage we use. We do not use third-party advertising cookies today.</p>
<h2>14. Changes</h2>
<p>We may update this policy. The "Last updated" date shows the revision date. Material changes will be notified in-app or via WhatsApp at least <strong>14 days</strong> before effect, where practicable.</p>
<h2>15. Contact</h2>
<p><a href="mailto:convergeozambia@gmail.com">convergeozambia@gmail.com</a></p>
$html_privacy$,
  NOW()
)
ON CONFLICT (slug) DO UPDATE SET
  version = EXCLUDED.version,
  content_md = EXCLUDED.content_md,
  content_html = EXCLUDED.content_html,
  last_modified_at = EXCLUDED.last_modified_at;

-- refund_policy.md -> slug 'refund'
INSERT INTO legal_docs (slug, version, content_md, content_html, last_modified_at)
VALUES (
  'refund',
  '1.0.0',
  $md_refund$
# Refund Policy

**Last updated:** 2026-05-24 · **Version:** 1.0.0

This Refund Policy applies to subscription fees paid to **Zed Apply** (ZedApply), a subsidiary of **Vergeo Group**, through our payment partners **Lenco** (mobile money) and **DPO Pay** (cards). All amounts are in **Zambian Kwacha (ZMW)**; internal records use **ngwee** (1 ZMW = 100 ngwee).

This policy supplements our [Terms of Service](/legal/terms). If there is a conflict on refunds, **this policy prevails** for refund eligibility.

**Contact:** [convergeozambia@gmail.com](mailto:convergeozambia@gmail.com) · In-app: open **Bwana** chat and type **talk to human** for billing help.

## 1. Overview

We want you to be confident upgrading to a paid tier. Refunds are handled fairly and consistently with the rules below. Promotional checkout prices (e.g. first-month discounts) do not change your right to an eligible refund under §2 — refunds are based on the amount actually charged.

## 2. Seven-day money-back guarantee (no AI documents used)

If you upgrade to a paid tier and **have not generated any AI documents** on your account after that charge, you may request a **full refund within 7 calendar days** of the payment date.

**AI documents** include, without limitation:

- AI-generated tailored CVs
- AI-generated cover letters
- Other AI-written application or interview materials delivered through Zed Apply

Our systems record successful generations against your user ID. If any AI document generation appears after the charge date, **§2 does not apply** — see §4.

No detailed justification is required for eligible §2 requests.

## 3. Prorated refund on tier downgrade

If you **downgrade** to a lower paid tier or to **Free** during an active billing period (before renewal), you may request a **prorated refund** for the unused portion of the higher tier, at our discretion and subject to processor rules.

- Proration runs from the downgrade date to the end of the current paid period.
- Mobile-money reversals may take **3–10 business days** to appear.
- Downgrading alone does **not** automatically refund — you must request under §6.

## 4. Non-refundable when AI documents were generated

Subscription fees are **non-refundable** once you have **generated AI documents** during the billing period in question, **even within 7 days of payment**, because the paid feature has been consumed.

This includes partial use (e.g. one cover letter).

## 5. Renewals, cancellations, and repeat refunds

- **Automatic renewals** are generally **non-refundable** once the new period starts.
- **Cancellation** stops future charges; it does not refund the current period unless you qualify under §2, §3, or §7.
- Accounts that already received a §2 refund may **not** claim another 7-day no-questions refund on a later plan.
- Failed or duplicate charges: contact us promptly; we will correct processor errors.

## 6. How to request a refund

1. **In-app (preferred):** Bwana chat → **talk to human**. Include your phone (+260…), charge date, tier, and whether you used AI documents.
2. **Email:** [convergeozambia@gmail.com](mailto:convergeozambia@gmail.com) with the same details.

We aim to respond within **2 business days**. Approved refunds are returned to the **original payment method** where the processor allows; otherwise we agree an alternative (e.g. Lenco reversal).

## 7. Material service unavailability

We may issue partial or full refunds at our discretion if paid features were **materially unavailable** for a sustained period due to a fault on our side (not due to your device, network, or WhatsApp account issues). Contact us under §6 with dates and symptoms.

## 8. Chargebacks

Contact us **before** initiating a bank or mobile-money chargeback. Chargebacks for legitimately delivered paid features may lead to account suspension pending investigation.

## 9. Free tier and promotional pricing

The free tier (K0) involves no payment and no refund. Promotional half-price checkout does not waive §2 eligibility — you may still qualify for a full refund of the amount paid within 7 days if §2 conditions are met.

## 10. Tax and records

Refunds may be net of non-recoverable processor fees where permitted. We retain payment records as required by Zambian law.

## 11. Changes

We may update this policy. Material changes will be posted at [/legal/refund](/legal/refund) with an updated "Last updated" date. Continued use of paid tiers after the effective date constitutes acceptance.

## 12. Related documents

- [Terms of Service](/legal/terms) — billing, cancellation, liability
- [Privacy Policy](/legal/privacy) — how we process your data

$md_refund$,
  $html_refund$
<h1>Refund Policy</h1>
<p><strong>Last updated:</strong> 2026-05-24 · <strong>Version:</strong> 1.0.0</p>
<p>This Refund Policy applies to subscription fees paid to <strong>Zed Apply</strong> (ZedApply), a subsidiary of <strong>Vergeo Group</strong>, through our payment partners <strong>Lenco</strong> (mobile money) and <strong>DPO Pay</strong> (cards). All amounts are in <strong>Zambian Kwacha (ZMW)</strong>; internal records use <strong>ngwee</strong> (1 ZMW = 100 ngwee).</p>
<p>This policy supplements our <a href="/legal/terms">Terms of Service</a>. If there is a conflict on refunds, <strong>this policy prevails</strong> for refund eligibility.</p>
<p><strong>Contact:</strong> <a href="mailto:convergeozambia@gmail.com">convergeozambia@gmail.com</a> · In-app: open <strong>Bwana</strong> chat and type <strong>talk to human</strong> for billing help.</p>
<h2>1. Overview</h2>
<p>We want you to be confident upgrading to a paid tier. Refunds are handled fairly and consistently with the rules below. Promotional checkout prices (e.g. first-month discounts) do not change your right to an eligible refund under §2 — refunds are based on the amount actually charged.</p>
<h2>2. Seven-day money-back guarantee (no AI documents used)</h2>
<p>If you upgrade to a paid tier and <strong>have not generated any AI documents</strong> on your account after that charge, you may request a <strong>full refund within 7 calendar days</strong> of the payment date.</p>
<p><strong>AI documents</strong> include, without limitation:</p>
<ul>
<li>AI-generated tailored CVs</li>
<li>AI-generated cover letters</li>
<li>Other AI-written application or interview materials delivered through Zed Apply</li>
</ul>
<p>Our systems record successful generations against your user ID. If any AI document generation appears after the charge date, <strong>§2 does not apply</strong> — see §4.</p>
<p>No detailed justification is required for eligible §2 requests.</p>
<h2>3. Prorated refund on tier downgrade</h2>
<p>If you <strong>downgrade</strong> to a lower paid tier or to <strong>Free</strong> during an active billing period (before renewal), you may request a <strong>prorated refund</strong> for the unused portion of the higher tier, at our discretion and subject to processor rules.</p>
<ul>
<li>Proration runs from the downgrade date to the end of the current paid period.</li>
<li>Mobile-money reversals may take <strong>3–10 business days</strong> to appear.</li>
<li>Downgrading alone does <strong>not</strong> automatically refund — you must request under §6.</li>
</ul>
<h2>4. Non-refundable when AI documents were generated</h2>
<p>Subscription fees are <strong>non-refundable</strong> once you have <strong>generated AI documents</strong> during the billing period in question, <strong>even within 7 days of payment</strong>, because the paid feature has been consumed.</p>
<p>This includes partial use (e.g. one cover letter).</p>
<h2>5. Renewals, cancellations, and repeat refunds</h2>
<ul>
<li><strong>Automatic renewals</strong> are generally <strong>non-refundable</strong> once the new period starts.</li>
<li><strong>Cancellation</strong> stops future charges; it does not refund the current period unless you qualify under §2, §3, or §7.</li>
<li>Accounts that already received a §2 refund may <strong>not</strong> claim another 7-day no-questions refund on a later plan.</li>
<li>Failed or duplicate charges: contact us promptly; we will correct processor errors.</li>
</ul>
<h2>6. How to request a refund</h2>
<ol>
<li><strong>In-app (preferred):</strong> Bwana chat → <strong>talk to human</strong>. Include your phone (+260…), charge date, tier, and whether you used AI documents.</li>
<li><strong>Email:</strong> <a href="mailto:convergeozambia@gmail.com">convergeozambia@gmail.com</a> with the same details.</li>
</ol>
<p>We aim to respond within <strong>2 business days</strong>. Approved refunds are returned to the <strong>original payment method</strong> where the processor allows; otherwise we agree an alternative (e.g. Lenco reversal).</p>
<h2>7. Material service unavailability</h2>
<p>We may issue partial or full refunds at our discretion if paid features were <strong>materially unavailable</strong> for a sustained period due to a fault on our side (not due to your device, network, or WhatsApp account issues). Contact us under §6 with dates and symptoms.</p>
<h2>8. Chargebacks</h2>
<p>Contact us <strong>before</strong> initiating a bank or mobile-money chargeback. Chargebacks for legitimately delivered paid features may lead to account suspension pending investigation.</p>
<h2>9. Free tier and promotional pricing</h2>
<p>The free tier (K0) involves no payment and no refund. Promotional half-price checkout does not waive §2 eligibility — you may still qualify for a full refund of the amount paid within 7 days if §2 conditions are met.</p>
<h2>10. Tax and records</h2>
<p>Refunds may be net of non-recoverable processor fees where permitted. We retain payment records as required by Zambian law.</p>
<h2>11. Changes</h2>
<p>We may update this policy. Material changes will be posted at <a href="/legal/refund">/legal/refund</a> with an updated "Last updated" date. Continued use of paid tiers after the effective date constitutes acceptance.</p>
<h2>12. Related documents</h2>
<ul>
<li><a href="/legal/terms">Terms of Service</a> — billing, cancellation, liability</li>
<li><a href="/legal/privacy">Privacy Policy</a> — how we process your data</li>
</ul>
$html_refund$,
  NOW()
)
ON CONFLICT (slug) DO UPDATE SET
  version = EXCLUDED.version,
  content_md = EXCLUDED.content_md,
  content_html = EXCLUDED.content_html,
  last_modified_at = EXCLUDED.last_modified_at;

-- cookie_policy.md -> slug 'cookies'
INSERT INTO legal_docs (slug, version, content_md, content_html, last_modified_at)
VALUES (
  'cookies',
  '1.0.0',
  $md_cookies$
# Cookie Policy

**Last updated:** 2026-05-24 · **Version:** 1.0.0

This Cookie Policy explains how **Zed Apply** (ZedApply), a subsidiary of **Vergeo Group**, uses cookies and similar browser technologies on our website. Read it together with our [Privacy Policy](/legal/privacy).

We audited the frontend codebase on **2026-05-24**. Zed Apply does **not** set classic HTTP cookies via `document.cookie` or Next.js `cookies()` for authentication today. Instead, we use **browser local storage** and **session storage** for the items below. Under this policy, "cookies" includes those technologies unless we say otherwise.

## 1. What are cookies and similar technologies?

A **cookie** is a small file stored by your browser. **Local storage** and **session storage** hold data in your browser without automatically sending it on every request — but they serve a similar purpose (remembering sign-in, preferences, and UI state).

## 2. Cookies and storage we set

### Strictly necessary (no consent required)

These are required for core functionality. Blocking them will break sign-in or core pages.

| Name | Type | Purpose | Duration |
| --- | --- | --- | --- |
| `zed_cv_token` | localStorage | JWT access token after WhatsApp OTP sign-in | Until sign-out or you clear site data |
| `zed_cv_user_id` | localStorage | Your user ID paired with the token | Until sign-out or you clear site data |
| `zedapply_matches_cache_v1` | sessionStorage | Short-lived cache of match list to improve page load | Until browser tab/session ends |

**Note:** Authentication uses **localStorage**, not an HttpOnly cookie. This means any script running on our origin could theoretically read the token — we mitigate this with strict content security, no third-party ad scripts, and sanitised legal/admin content. Sign out clears `zed_cv_token` and `zed_cv_user_id`.

### Preferences (no separate banner today)

| Name | Type | Purpose | Duration |
| --- | --- | --- | --- |
| `zed_cv_theme` | localStorage | Light/dark theme choice | Until you change theme or clear site data |
| `zedcv:preferences:expanded` | localStorage | Which sections are expanded on the profile preferences tab | Until cleared |
| `zedapply_pwa_install_dismissed` | localStorage | Remembers if you dismissed the "install app" prompt | Until cleared |

### Functional (logged-in features)

| Name | Type | Purpose | Duration |
| --- | --- | --- | --- |
| `zedapply_bwana_session_id` | localStorage | Anonymous session ID for Bwana support chat | Until cleared or you start a new chat session |
| `zedcv_aptitude_session` | localStorage | In-progress aptitude test state (Interview Prep) | Until test completes or you clear site data |

### Admin-only (superadmin job wizard)

| Name | Type | Purpose | Duration |
| --- | --- | --- | --- |
| `zedcv:admin:job-draft:v1` | localStorage | Draft job form for admins | Up to **7 days**, then auto-discarded |

Regular job seekers will not see admin drafts.

### Analytics and marketing

We **do not** currently load Google Analytics, Meta Pixel, or other third-party analytics/marketing scripts. We **do not** set advertising cookies.

When we add product analytics, we will:

- ask for **opt-in consent** via a banner before loading scripts;
- update this policy; and
- list each new cookie by name.

## 3. Third-party cookies

We do **not** currently allow third parties to set cookies on zedapply.com when you browse our pages.

Payment (**Lenco**, **DPO Pay**) and WhatsApp (**WAHA**) run as **back-end processors** — they do not set cookies on your device when you simply view Zed Apply. When you complete checkout, you may interact with a processor-hosted page that sets its own cookies under **their** policies.

## 4. How to control cookies and storage

- **Browser settings:** View and delete cookies and site data (often under Privacy → Cookies / Site data). Deleting data for our site signs you out and clears preferences.
- **Sign out:** Removes `zed_cv_token` and `zed_cv_user_id`.
- **Private / incognito mode:** Usually clears session storage when you close the window; localStorage may still persist until the private session ends (browser-dependent).
- **Theme toggle:** Updates `zed_cv_theme` immediately.

When we launch an analytics consent banner, you will be able to change analytics choices in-app.

## 5. Relationship to the ZDPA

Where storage identifies you (e.g. auth token), it processes personal data under our [Privacy Policy](/legal/privacy) and the **Zambia Data Protection Act, 2021**. Strictly necessary storage is based on **contract** and **legitimate interests**; optional analytics will rely on **consent**.

## 6. Changes

We may update this policy when we add cookies or change storage keys. The "Last updated" date shows the revision date.

## 7. Contact

[convergeozambia@gmail.com](mailto:convergeozambia@gmail.com)

$md_cookies$,
  $html_cookies$
<h1>Cookie Policy</h1>
<p><strong>Last updated:</strong> 2026-05-24 · <strong>Version:</strong> 1.0.0</p>
<p>This Cookie Policy explains how <strong>Zed Apply</strong> (ZedApply), a subsidiary of <strong>Vergeo Group</strong>, uses cookies and similar browser technologies on our website. Read it together with our <a href="/legal/privacy">Privacy Policy</a>.</p>
<p>We audited the frontend codebase on <strong>2026-05-24</strong>. Zed Apply does <strong>not</strong> set classic HTTP cookies via <code>document.cookie</code> or Next.js <code>cookies()</code> for authentication today. Instead, we use <strong>browser local storage</strong> and <strong>session storage</strong> for the items below. Under this policy, "cookies" includes those technologies unless we say otherwise.</p>
<h2>1. What are cookies and similar technologies?</h2>
<p>A <strong>cookie</strong> is a small file stored by your browser. <strong>Local storage</strong> and <strong>session storage</strong> hold data in your browser without automatically sending it on every request — but they serve a similar purpose (remembering sign-in, preferences, and UI state).</p>
<h2>2. Cookies and storage we set</h2>
<h3>Strictly necessary (no consent required)</h3>
<p>These are required for core functionality. Blocking them will break sign-in or core pages.</p>
<table>
<thead>
<tr>
<th>Name</th>
<th>Type</th>
<th>Purpose</th>
<th>Duration</th>
</tr>
</thead>
<tbody>
<tr>
<td><code>zed_cv_token</code></td>
<td>localStorage</td>
<td>JWT access token after WhatsApp OTP sign-in</td>
<td>Until sign-out or you clear site data</td>
</tr>
<tr>
<td><code>zed_cv_user_id</code></td>
<td>localStorage</td>
<td>Your user ID paired with the token</td>
<td>Until sign-out or you clear site data</td>
</tr>
<tr>
<td><code>zedapply_matches_cache_v1</code></td>
<td>sessionStorage</td>
<td>Short-lived cache of match list to improve page load</td>
<td>Until browser tab/session ends</td>
</tr>
</tbody>
</table>
<p><strong>Note:</strong> Authentication uses <strong>localStorage</strong>, not an HttpOnly cookie. This means any script running on our origin could theoretically read the token — we mitigate this with strict content security, no third-party ad scripts, and sanitised legal/admin content. Sign out clears <code>zed_cv_token</code> and <code>zed_cv_user_id</code>.</p>
<h3>Preferences (no separate banner today)</h3>
<table>
<thead>
<tr>
<th>Name</th>
<th>Type</th>
<th>Purpose</th>
<th>Duration</th>
</tr>
</thead>
<tbody>
<tr>
<td><code>zed_cv_theme</code></td>
<td>localStorage</td>
<td>Light/dark theme choice</td>
<td>Until you change theme or clear site data</td>
</tr>
<tr>
<td><code>zedcv:preferences:expanded</code></td>
<td>localStorage</td>
<td>Which sections are expanded on the profile preferences tab</td>
<td>Until cleared</td>
</tr>
<tr>
<td><code>zedapply_pwa_install_dismissed</code></td>
<td>localStorage</td>
<td>Remembers if you dismissed the "install app" prompt</td>
<td>Until cleared</td>
</tr>
</tbody>
</table>
<h3>Functional (logged-in features)</h3>
<table>
<thead>
<tr>
<th>Name</th>
<th>Type</th>
<th>Purpose</th>
<th>Duration</th>
</tr>
</thead>
<tbody>
<tr>
<td><code>zedapply_bwana_session_id</code></td>
<td>localStorage</td>
<td>Anonymous session ID for Bwana support chat</td>
<td>Until cleared or you start a new chat session</td>
</tr>
<tr>
<td><code>zedcv_aptitude_session</code></td>
<td>localStorage</td>
<td>In-progress aptitude test state (Interview Prep)</td>
<td>Until test completes or you clear site data</td>
</tr>
</tbody>
</table>
<h3>Admin-only (superadmin job wizard)</h3>
<table>
<thead>
<tr>
<th>Name</th>
<th>Type</th>
<th>Purpose</th>
<th>Duration</th>
</tr>
</thead>
<tbody>
<tr>
<td><code>zedcv:admin:job-draft:v1</code></td>
<td>localStorage</td>
<td>Draft job form for admins</td>
<td>Up to <strong>7 days</strong>, then auto-discarded</td>
</tr>
</tbody>
</table>
<p>Regular job seekers will not see admin drafts.</p>
<h3>Analytics and marketing</h3>
<p>We <strong>do not</strong> currently load Google Analytics, Meta Pixel, or other third-party analytics/marketing scripts. We <strong>do not</strong> set advertising cookies.</p>
<p>When we add product analytics, we will:</p>
<ul>
<li>ask for <strong>opt-in consent</strong> via a banner before loading scripts;</li>
<li>update this policy; and</li>
<li>list each new cookie by name.</li>
</ul>
<h2>3. Third-party cookies</h2>
<p>We do <strong>not</strong> currently allow third parties to set cookies on zedapply.com when you browse our pages.</p>
<p>Payment (<strong>Lenco</strong>, <strong>DPO Pay</strong>) and WhatsApp (<strong>WAHA</strong>) run as <strong>back-end processors</strong> — they do not set cookies on your device when you simply view Zed Apply. When you complete checkout, you may interact with a processor-hosted page that sets its own cookies under <strong>their</strong> policies.</p>
<h2>4. How to control cookies and storage</h2>
<ul>
<li><strong>Browser settings:</strong> View and delete cookies and site data (often under Privacy → Cookies / Site data). Deleting data for our site signs you out and clears preferences.</li>
<li><strong>Sign out:</strong> Removes <code>zed_cv_token</code> and <code>zed_cv_user_id</code>.</li>
<li><strong>Private / incognito mode:</strong> Usually clears session storage when you close the window; localStorage may still persist until the private session ends (browser-dependent).</li>
<li><strong>Theme toggle:</strong> Updates <code>zed_cv_theme</code> immediately.</li>
</ul>
<p>When we launch an analytics consent banner, you will be able to change analytics choices in-app.</p>
<h2>5. Relationship to the ZDPA</h2>
<p>Where storage identifies you (e.g. auth token), it processes personal data under our <a href="/legal/privacy">Privacy Policy</a> and the <strong>Zambia Data Protection Act, 2021</strong>. Strictly necessary storage is based on <strong>contract</strong> and <strong>legitimate interests</strong>; optional analytics will rely on <strong>consent</strong>.</p>
<h2>6. Changes</h2>
<p>We may update this policy when we add cookies or change storage keys. The "Last updated" date shows the revision date.</p>
<h2>7. Contact</h2>
<p><a href="mailto:convergeozambia@gmail.com">convergeozambia@gmail.com</a></p>
$html_cookies$,
  NOW()
)
ON CONFLICT (slug) DO UPDATE SET
  version = EXCLUDED.version,
  content_md = EXCLUDED.content_md,
  content_html = EXCLUDED.content_html,
  last_modified_at = EXCLUDED.last_modified_at;

COMMIT;
