# TCC Compliance Agent — Validus F1 Capstone

An AI-powered HTTP service that automates the Transaction Compliance Check (TCC) desk of Validus, a mutual-fund RTA. Built for the Cadra F1 capstone assessment using OpenCode with the Cadra provider.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run data preparation

```bash
python scripts/prepare_data.py
```

## Run the API

```bash
# With LLM (Gemini):
export LLM_API_KEY=your-gemini-key
export LLM_PROVIDER=gemini
export LLM_MODEL=gemini-2.0-flash
python -m app.main

# Without LLM (regex-only fallback + templates):
python -m app.main
```

The API serves at `http://0.0.0.0:8000`. Healthcheck: `GET /health`.

## API Contract

### `POST /requests`

```json
{
  "request_id": "R01",
  "received_at": "2026-10-06T10:30:00",
  "channel": "email",
  "from": "investor@email.com",
  "subject": "Investment for grandson",
  "body": "...",
  "attachments": [{"file_name": "advice.pdf", "content_type": "application/pdf", "content_base64": "..."}]
}
```

See `app/schemas.py` for the full `ResponseOut` model.

## Project layout

```
.
├── app/                    # Application package
│   ├── main.py            # FastAPI routes
│   ├── schemas.py         # Pydantic models (request/response + records)
│   ├── pipeline.py        # Orchestrator: S1 → S8
│   ├── s1_intake.py       # Attachment decoding
│   ├── s2_extract.py      # Field extraction + classification
│   ├── s3_resolve.py      # Folio/identity resolution
│   ├── s4_policy.py       # Policy version selection
│   ├── s6_decide.py       # Outcome + approver
│   ├── s7_reply.py        # Reply drafting
│   ├── trace.py           # Trace collector
│   ├── llm.py             # LLM provider wrapper
│   ├── tools/             # Data lookup tools
│   │   ├── kra.py, folio.py, bank.py, txn.py, distributor.py
│   ├── checks/            # 8 compliance checks
│   │   ├── identity.py, kyc.py, tpp.py, bank_mandate.py, cob.py, distributor.py, minor.py, referral.py
│   └── policy/
│       ├── rules.yaml     # Rule definitions linked to SOP clauses
│       └── selector.py    # Version-aware selection
├── scripts/
│   └── prepare_data.py    # Data prep: CSVs → in-memory + issues
├── eval/
│   ├── run_eval.py        # Eval runner
│   ├── cases/             # Expected results (to fill)
│   └── results/           # Timestamped eval outputs
├── tests/
│   └── test_tools.py      # 18 unit tests
├── Data/                  # Synthetic data room
├── Dockerfile
├── railway.json
├── opencode.json
├── FUTURE_WORKFLOW.md
├── APPROACH.md
├── ARTEFACT.md
└── requirements.txt
```

## Environment variables

| Variable | Purpose |
|---|---|
| `LLM_API_KEY` | Gemini API key |
| `LLM_PROVIDER` | `gemini` (default) |
| `LLM_MODEL` | `gemini-2.0-flash` (default) |
| `ALLOWED_ORIGINS` | CORS origins (comma-separated, default `*`) |
| `PORT` | Server port (Railway injects this) |
| `EVAL_BASE_URL` | Base URL for eval runner |

## Extra response fields

- `resolved.amc_code` — AMC identifier (NMF/TMF/null)
- `trace.latency_ms` — wall-clock time in milliseconds
- `trace.model_calls[]` — model name + token counts from API metadata
- `trace.documents_used[]` — SOP documents + versions selected

## Deploy

### Railway (backend)

```bash
railway login
railway init
railway up
```

Set `LLM_API_KEY`, `LLM_PROVIDER`, `LLM_MODEL` as Railway secrets. The `railway.json` and `Dockerfile` are configured.

### Netlify (UI — optional)

```bash
cd ui
# Build and deploy ui/ directory
```

## Run tests

```bash
pytest tests/
```

## Eval

```bash
python eval/run_eval.py --url https://your-app.railway.app
```