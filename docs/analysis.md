# Analysis — Expected results per request

## R00 (Worked example from CURRENT_WORKFLOW.docx)
- Folio: 40166450/93 (NMF, Ravi Kumar Bhat)
- Request: Additional purchase
- Expected: PROCEED (all checks PASS)

## R01 — SIP Registration Arjun Nair
- Folio: 40118823/23 (NMF, Arjun Nair, PAN GDHPN**79U)
- KYC: 307 → VALIDATED (PASS)
- Distributor: ARN-145023 ACTIVE till 2028, empanelled NMF
- Request type: SIP_REGISTRATION
- TPP: OTM/NACH on registered a/c ending 4908 → PASS
- Outcome: **PROCEED**

## R02 — Grandson investment (minor)
- Folio: 40173612/78 (NMF, Ishaan Kulkarni MINOR DOB 2015-03-02)
- Payer: Vasant Kulkarni (grandfather) → TPP per v4.1 5.4
- Minor: Ishaan, guardian Rohan (FATHER) → minor check NOT_APPLICABLE
- **Under v4.1**: grandparent = TPP, no exception → REJECT (TPP_NO_EXCEPTION)
- **Under v3.2**: related person allowed → PROCEED (version difference)
- Received 2026-10-06 ≥ 2026-08-01 → v4.1 applies
- Outcome: **REJECT** (TPP_NO_EXCEPTION)

## R03 — Payroll SIP Sandeep Yadav (TMF)
- Folio: 71138631/21 (TMF, Sandeep Yadav, PAN BARPY**69Z)
- KYC: 507 → VALIDATED (PASS)
- Employer Deccan Polymers paying → TPP exception 5.3 with docs
- Request type: SIP_REGISTRATION/DIRECT
- Direct plan → distributor: NOT_APPLICABLE
- Docs: TPP Declaration + confirmation letter attached → PROCEED_MODIFIED if docs missing, PROCEED if complete
- Outcome: **PROCEED** or **PROCEED_MODIFIED**

## R04 — Additional purchase Farhan Siddiqui
- Folio: 40120238/73 (NMF, Farhan Siddiqui, PAN UXFPS**09F)
- KYC: 303 → ON HOLD → purchase not accepted per 4.4
- Outcome: **REJECT** (KYC_ON_HOLD)

## R05 — New investment (no TMF folio)
- No valid TMF folio number provided
- Investor has NMF folio 40104822/68 (Lakshmi Venkataraman, KYC REGISTERED)
- Outcome: **INVALID_REQUEST** (FOLIO_NOT_FOUND)

## R06 — Additional purchase Neha Agarwal (unregistered account)
- Folio: 40159954/10 (NMF, Neha Agarwal, PAN RBKPA**61M)
- KYC: 307 → VALIDATED (PASS)
- Payment from Vindhya Bank a/c ending 5879 (own but unregistered)
- Per 5.6: own unregistered account needs proof → PEND (BANK_PROOF_REQUIRED)
- Outcome: **PEND**

## R07 — Joint folio Srinivasan
- Folio: 40112665/21 (NMF, Priya Raghavan first holder, PAN ERUPR**36W)
- Second holder Srinivasan paying from personal account
- TPP check needed: is second holder a recognized payer?
- KYC: 307 (Priya) → VALIDATED
- Outcome: **PROCEED** (second holder payment is not TPP if named on account)

## R08 — Aditi Menon fresh purchase (TMF, expired ARN)
- Folio: 71167297/25 (TMF, Aditi Menon, PAN KUEPM**77N)
- KYC: 007 → VALIDATED (PASS)
- ARN-207791: EXPIRED (valid till 2026-08-14)
- Regular plan with invalid ARN → PROCEED_MODIFIED (ARN_INVALID_DIRECT)
- Outcome: **PROCEED_MODIFIED**

## R09 — Kiran Reddy additional purchase
- Folio: 40131574/17 (NMF, Kiran Reddy, PAN HMAPR**16L)
- KYC: 399 → "KRA web service not reachable" → UNABLE_TO_VERIFY
- Outcome: **PEND** (KYC_UNABLE_TO_VERIFY)

## R10 — Sunita Iyer redemption + COB
- Folio: 40115267/30 (NMF, Sunita Iyer, PAN MYGPI**72Y)
- KYC: 007 → VALIDATED (PASS)
- REDEMPTION + Change of Bank (COB)
- Contact changed: 2026-10-02 (within 30 days before COB on 4 Oct)
- Redemption: requesting to pay to new account
- COB_COOLING: 10-day cooling applies
- HIGH_RISK_CONTACT_COB: contact changed within 30d before COB + redemption during cooling
- Outcome: **HOLD_AND_REFER** (HIGH_RISK_CONTACT_COB, COB_COOLING)

## v3.2 vs v4.1 diff
| Clause | v3.2 | v4.1 |
|--------|------|------|
| 5.4 (Minor TPP) | "related persons" allowed | Only minor/parent/guardian; grandparent=TPP |
| 6.5 (Contact+COB) | Not present | Added: HIGH_RISK_CONTACT_COB |
| Addendum handling | Not specified | AMC addenda prevail (TMF-ADD-02) |

## Data issues
1. T181000029: negative units/NAV
2. R40131574/17 KRA code "399" (web service not reachable — 3-digit but last two digits 99)
3. KRA entries with code "7" (single digit, ambiguous KRA) — several PANs