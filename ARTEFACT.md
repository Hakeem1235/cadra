# Artefact — TCC Compliance Agent

## Data preparation

| Extract | Rows loaded | Notes |
|---|---|---|
| `folio_master.csv` | 83 | NMF folios start 401, TMF start 711 |
| `kra_kyc_snapshot.csv` | 95 | One row per PAN |
| `bank_mandates.csv` | 105 | Per-folio account records |
| `transactions.csv` | 522 | ~12 months of history + pending items |
| `distributor_master.csv` | 32 | ARN + EUIN records |

**Data issues found** — 1 (logged in `build/data_issues.json`):
- T181000029: negative units (-682,982.356) and NAV (-0.8785) — flagged, not deleted.

## Policy documents ingested

| Document | Version | Effective | Status | Applied to |
|---|---|---|---|---|
| `Validus_TCC_SOP_v4.1.docx` | 4.1 | 2026-08-01 | Current | All folios |
| `Validus_TCC_SOP_v3.2.pdf` | 3.2 | 2025-01-01 | Superseded | Requests before 2026-08-01 |
| `Tungabhadra_MF_Client_Addendum_TMF-ADD-02.pdf` | 1.0 | 2026-09-15 | Current | TMF folios only |

**Version selection logic:** `received_at ≥ effective_from` picks the latest matching SOP version. If AMC == TMF and received_at ≥ 2026-09-15, the addendum is also applied. No addendum for NMF.

## Evaluation

| Metric | Value |
|---|---|
| Test cases (unit) | 18 (all pass) |
| Eval cases planned | 30+ covering every reason code |
| Unsafe errors | See eval/results/ |
| Over-cautious errors | See eval/results/ |
| Median cost/request | TBD (requires LLM key) |

## System architecture

- **Pipeline:** S1 Intake → S2 Extract → S3 Resolve → S4 Policy → S5 Checks (8) → S6 Decide → S7 Reply → S8 Trace
- **Deterministic code** for all checks, outcome, approver selection (never the LLM)
- **LLM used for:** extraction (JSON mode), image transcription, draft replies
- **Policy is data:** versioned SOPs + addenda with date-based selection, no hardcoded rules

## Not built / fragile / next steps

- **S9 Human queue:** designed, not built — the API returns the proposal but does not send email
- **UI:** designed, not built — `/ui` directory is placeholder
- **Policy-update assistant:** designed, not built — `scripts/policy_update.py` is placeholder
- **LLM integration:** requires `LLM_API_KEY`, `LLM_PROVIDER`, `LLM_MODEL` env vars — without them, extraction falls back to regex-only and replies use templates
- **Full eval set:** custom eval cases covering all reason codes not yet written
- **Deployment:** Dockerfile + `railway.json` ready but not deployed