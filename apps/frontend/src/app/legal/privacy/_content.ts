// Static markdown source for the Privacy Policy. Kept in a dedicated
// module so task #62's WYSIWYG/DB-backed editor can swap the import for
// a server fetch without rewriting the page component.
export const VERSION = "1.0";
export const LAST_UPDATED = "2026-05-14";

export const PRIVACY_MARKDOWN = `# Privacy Policy

**Last updated:** ${LAST_UPDATED} &middot; **Version:** ${VERSION}

ZedApply ("ZedApply", "we", "us", "our") respects your privacy and is
committed to handling your personal data lawfully, fairly and
transparently. This Privacy Policy explains what personal data we
collect when you use the ZedApply platform, why we collect it, how we
use it, who we share it with, and the choices and rights you have. It
is written to comply with the **Zambia Data Protection Act, 2021** and
reflects general best practice.

If you do not agree with this Privacy Policy, please do not use the
ZedApply platform.

## 1. Who we are

ZedApply is operated by **Vergeo** ("the data controller"), based in
Lusaka, Zambia.

- **Contact email:** [convergeozambia@gmail.com](mailto:convergeozambia@gmail.com)
- **Postal contact:** Lusaka, Zambia

For privacy-related requests, please write to us at the email address
above with the subject line "Privacy request".

## 2. Personal data we collect

We collect only the data we need to deliver the service. Categories
include:

- **Account & identity data:** your Zambian mobile phone number (in
  E.164 format, e.g. +260XXXXXXXXX), and optionally your name and
  email address.
- **Authentication data:** one-time passwords (OTPs) sent via WhatsApp
  and the timestamp / status of each verification attempt.
- **CV content:** the text of any CV you upload, including work
  history, education, skills, certifications and any other information
  you choose to include. **We strongly advise against including
  national registration numbers, banking details or other sensitive
  identifiers in your CV.**
- **Skills and profile data:** structured skills, seniority, location
  and salary preferences derived from your CV or entered manually.
- **Job-matching data:** the matches we compute for you, the scores
  and reasons attached to them, and any actions you take (saved
  matches, applications, dismissals).
- **Payment data:** transaction references, amounts (in ZMW ngwee),
  status and timestamps when you purchase a paid tier. **We do not
  store full card numbers, mobile-money PINs or banking credentials.**
  Card and mobile-money data is handled directly by our payment
  processors.
- **WhatsApp messages:** the content and metadata of messages you send
  to or receive from our WhatsApp number, where you have opted in to
  WhatsApp delivery.
- **Device & log data:** IP address, browser user agent, pages visited,
  and timestamps. We use this to operate the service, debug issues and
  detect abuse.

We do not knowingly collect any "special personal data" (such as data
about health, ethnicity or political views) and we ask that you do not
include such information in your CV.

## 3. Why we use your data (purposes)

We use your personal data for the following purposes:

- **Service delivery:** matching your CV against open jobs, generating
  match scores and explanations, and showing you relevant results.
- **Account management:** creating and authenticating your account via
  WhatsApp OTP, and remembering your settings.
- **Paid feature delivery:** processing subscription payments, granting
  access to tier-locked features (e.g. interview prep notes), and
  managing renewals and cancellations.
- **Communication:** sending you transactional WhatsApp messages
  (e.g. match alerts, payment confirmations) and, where you have
  separately consented, marketing messages.
- **Fraud prevention and security:** detecting fake jobs, fake
  accounts, abuse of free tiers and other misuse of the platform.
- **Legal compliance:** keeping records we are required to keep, and
  responding to lawful requests.
- **Service improvement:** producing aggregate, de-identified
  statistics about how the platform is used, in order to improve
  matching quality and user experience.

## 4. Legal bases for processing

Under the Zambia Data Protection Act, 2021, we process your personal
data on the following legal bases:

- **Performance of a contract** with you (our Terms of Service): for
  account creation, job matching, paid feature delivery, transactional
  WhatsApp messages and customer support.
- **Compliance with a legal obligation:** for retaining payment
  records for tax and accounting purposes.
- **Legitimate interests:** for security, fraud prevention, log keeping
  and aggregated analytics, where these interests are not overridden
  by your rights.
- **Consent:** for any marketing messages and for any optional
  analytics cookies. You can withdraw consent at any time (see
  Section 7).

## 5. Who we share your data with (recipients)

We use a small number of carefully selected service providers
("processors") to operate the platform. Each acts only on our
instructions and is bound by appropriate confidentiality and security
commitments.

- **Supabase** &mdash; database, file storage and authentication
  infrastructure. Stores your account, CV text and match history.
- **Google Gemini** (Google LLC) &mdash; AI processing used to extract
  structured data from CVs and to produce job-match explanations and
  interview prep notes. Inputs are not used to train Google's
  foundation models, per Google's enterprise terms.
- **OpenRouter** &mdash; AI routing layer used for some inference
  workloads as a fallback to Gemini.
- **DPO Pay** &mdash; primary payment processor for card and mobile-money
  payments. Handles card data directly; we receive only a transaction
  reference and status.
- **Lenco** &mdash; secondary payment processor used for selected
  payouts and mobile-money flows.
- **Resend** &mdash; transactional email delivery, where email is used
  (e.g. receipts).
- **WAHA** &mdash; WhatsApp HTTP API gateway used to send and receive
  WhatsApp messages on our behalf.
- **n8n** &mdash; workflow automation used internally to orchestrate
  job ingestion, alerts and heartbeat tasks.

We do **not** sell your personal data, and we do not share it with
advertising networks.

We may disclose personal data where we are legally required to do so,
or where we believe in good faith that disclosure is necessary to
protect our rights, your safety or the safety of others.

## 6. Cross-border transfers

Some of the processors listed in Section 5 are located outside Zambia
(for example, in the United States or the European Union). When we
transfer personal data outside Zambia, we rely on the safeguards
permitted by the Data Protection Act, 2021, including contractual
commitments from our processors to apply security and confidentiality
standards equivalent to those required under Zambian law.

By using ZedApply, you acknowledge that your personal data may be
processed outside Zambia for the purposes described in this Privacy
Policy.

## 7. Your rights

Subject to the Data Protection Act, 2021, you have the following
rights in respect of your personal data:

- **Right of access** &mdash; to obtain confirmation that we process
  your data and a copy of it.
- **Right to rectification** &mdash; to have inaccurate or incomplete
  data corrected.
- **Right to erasure ("right to be forgotten")** &mdash; to have your
  data deleted, subject to legal retention requirements (for example,
  payment records we must keep for tax purposes).
- **Right to data portability** &mdash; to receive your data in a
  structured, machine-readable format and, where technically feasible,
  to have it transmitted to another controller.
- **Right to object** &mdash; to processing based on our legitimate
  interests, including for marketing.
- **Right to withdraw consent** &mdash; for any processing based on
  consent, at any time, without affecting the lawfulness of processing
  before withdrawal.

Self-service controls for some of these rights (account export and
deletion) will be available in your account settings; until then, you
can exercise any of these rights by emailing
[convergeozambia@gmail.com](mailto:convergeozambia@gmail.com) with
your registered phone number and a description of your request. We
will respond within the timeframes required by law (and in any case
within 30 days, subject to verification of your identity).

## 8. Retention

We retain personal data only as long as we need it for the purposes
described above:

- **CV content, profile data and match history:** retained until you
  delete your account. After account deletion, we remove this data
  from active systems within 30 days. Encrypted backups may retain
  copies for up to a further 90 days before they are overwritten.
- **Payment records:** retained for **7 years** after the transaction,
  to comply with Zambian tax and accounting obligations.
- **Authentication logs and security logs:** retained for **30 days**.
- **WhatsApp message records:** retained for the lifetime of your
  account, then deleted with the rest of your account data.
- **Aggregate, de-identified analytics:** may be retained indefinitely
  as they no longer identify you.

## 9. Security

We apply appropriate technical and organisational measures to protect
your personal data, including:

- TLS encryption for all network traffic between your device, our
  servers and our processors.
- Encryption at rest for data stored in our database and file storage.
- Strict access controls and audit logging for personnel and admin
  tooling.
- WhatsApp OTP-based authentication, with no password to be guessed,
  reused or phished.
- Regular review of our processors' security posture.

No system can be made absolutely secure. We will notify affected users
and the Data Protection Commissioner without undue delay if we become
aware of a personal data breach that is likely to result in a risk to
your rights and freedoms.

## 10. Cookies

We use a small number of strictly necessary cookies to keep you signed
in and to remember your preferences. For full details, including
optional analytics cookies and how to control them, see our
[Cookie Policy](/legal/cookies).

## 11. Children

ZedApply is intended for adults seeking employment. The service is
**not** directed at children, and you must be **at least 18 years
old** to create an account. If you believe we have inadvertently
collected personal data from a child, please contact us and we will
delete the data.

## 12. Complaints and the Data Protection Commissioner

If you believe we have not handled your personal data in accordance
with the Data Protection Act, 2021, please contact us first &mdash; we
will do our best to address your concern.

You also have the right to lodge a complaint with the **Office of the
Data Protection Commissioner** of Zambia. Up-to-date contact details
for the Commissioner are published by the Ministry of Technology and
Science of Zambia.

## 13. Changes to this Privacy Policy

We may update this Privacy Policy from time to time, for example to
reflect new features, new processors or changes in the law. The
"Last updated" date at the top of this page shows when the policy was
last revised. For material changes, we will notify you in-app or via
WhatsApp at least 14 days before the changes take effect.

## 14. Contact

If you have any questions about this Privacy Policy or your personal
data, please contact us at
[convergeozambia@gmail.com](mailto:convergeozambia@gmail.com).
`;
