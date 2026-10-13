#!/usr/bin/env python3
"""Prepare data: load CSVs, ingest policies (parse PDF/DOCX into clause index), detect data issues."""

from __future__ import annotations

import csv
import json
import os
import re
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "Data", "data")
POLICY_DIR = os.path.join(ROOT, "Data", "policies")
OUT_DIR = os.path.join(ROOT, "build")


def load_csv(filename: str) -> list[dict]:
    path = os.path.join(DATA_DIR, filename)
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def parse_docx(path: str) -> str:
    from docx import Document
    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs)


def parse_pdf(path: str) -> str:
    import pdfplumber
    with pdfplumber.open(path) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


CLAUSE_PAT = re.compile(r"^(\d+(?:\.\d+)?)\s+(.+)$", re.MULTILINE)

def chunk_by_clause(text: str, doc_id: str, version: str, effective_from: str) -> list[dict]:
    chunks = []
    lines = text.split("\n")
    current_clause = None
    current_title = ""
    current_lines = []
    for line in lines:
        m = CLAUSE_PAT.match(line.strip())
        if m:
            if current_clause and current_lines:
                chunks.append({
                    "chunk_id": f"{doc_id}_{version}_{current_clause}",
                    "doc_id": doc_id,
                    "version": version,
                    "effective_from": effective_from,
                    "clause_id": current_clause,
                    "title": current_title,
                    "text": " ".join(current_lines).strip(),
                })
            current_clause = m.group(1)
            current_title = m.group(2)
            current_lines = []
        elif current_clause:
            current_lines.append(line.strip())
    if current_clause and current_lines:
        chunks.append({
            "chunk_id": f"{doc_id}_{version}_{current_clause}",
            "doc_id": doc_id,
            "version": version,
            "effective_from": effective_from,
            "clause_id": current_clause,
            "title": current_title,
            "text": " ".join(current_lines).strip(),
        })
    return chunks


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    data_issues = []
    counts = {}

    # 1. Folio master
    folio_rows = load_csv("folio_master.csv")
    counts["folio_master"] = len(folio_rows)
    for r in folio_rows:
        flag = r.get("folio_flag", "").strip().upper()
        if flag and flag not in ("NONE", "STOP_LOCK", ""):
            data_issues.append({"type": "UNEXPECTED_FOLIO_FLAG", "ref": r.get("folio_no"), "value": r.get("folio_flag")})

    # 2. KRA KYC
    kra_rows = load_csv("kra_kyc_snapshot.csv")
    counts["kra_kyc"] = len(kra_rows)
    for r in kra_rows:
        code = r.get("kra_status_code", "").strip()
        text = r.get("kra_status", "").strip().lower()
        if code and text:
            text_map = {"validated": "07", "registered": "02", "on hold": "03",
                        "rejected": "04", "under process": "01", "not available": "05"}
            if text in text_map and text_map[text] != code[-2:]:
                data_issues.append({"type": "KRA_CODE_TEXT_MISMATCH", "ref": r.get("pan_masked"), "value": f"code={code}, text={text}"})
        if code and len(code) == 1:
            data_issues.append({"type": "KRA_SINGLE_DIGIT_CODE", "ref": r.get("pan_masked"), "value": f"code={code}"})

    # 3. Bank mandates
    bank_rows = load_csv("bank_mandates.csv")
    counts["bank_mandates"] = len(bank_rows)

    # 4. Transactions
    txn_rows = load_csv("transactions.csv")
    counts["transactions"] = len(txn_rows)
    for t in txn_rows:
        try:
            u = float(t.get("units", 0) or 0)
            n = float(t.get("nav", 0) or 0)
            if u < 0 or n < 0:
                data_issues.append({"type": "NEGATIVE_UNITS_OR_NAV", "ref": t.get("txn_id"), "value": f"units={t['units']}, nav={t['nav']}"})
        except ValueError:
            pass

    # 5. Distributor master
    dist_rows = load_csv("distributor_master.csv")
    counts["distributor_master"] = len(dist_rows)

    # 6. Policy ingestion (chunk by clause)
    policy_docs = [
        ("Validus_TCC_SOP_v4.1.docx", "VAL-OPS-TCC-SOP", "4.1", "2026-08-01", "Current"),
        ("Validus_TCC_SOP_v3.2.pdf", "VAL-OPS-TCC-SOP", "3.2", "2025-01-01", "Superseded"),
        ("Tungabhadra_MF_Client_Addendum_TMF-ADD-02.pdf", "TMF-ADD-02", "1.0", "2026-09-15", "Current"),
    ]
    all_clauses = []
    for fname, doc_id, version, eff_date, status in policy_docs:
        path = os.path.join(POLICY_DIR, fname)
        if not os.path.exists(path):
            continue
        if fname.endswith(".docx"):
            text = parse_docx(path)
        else:
            text = parse_pdf(path)
        text = re.sub(r"[Ee]\s*[Dd]\s*$", "", text, flags=re.MULTILINE)
        text = re.sub(r"Uncontrolled when printed.*", "", text)
        chunks = chunk_by_clause(text, doc_id, version, eff_date)
        for c in chunks:
            c["status"] = status
        all_clauses.extend(chunks)
        print(f"  {fname}: {len(chunks)} clauses")

    policy_registry = [
        {"doc_id": did, "version": v, "effective_from": e, "status": s, "file": fn}
        for fn, did, v, e, s in policy_docs
    ]

    # Write artifacts
    with open(os.path.join(OUT_DIR, "data_issues.json"), "w") as f:
        json.dump(data_issues, f, indent=2)
    with open(os.path.join(OUT_DIR, "counts.json"), "w") as f:
        json.dump(counts, f, indent=2)
    with open(os.path.join(OUT_DIR, "policy_index.json"), "w") as f:
        json.dump({"clauses": all_clauses, "total": len(all_clauses)}, f, indent=2)
    with open(os.path.join(OUT_DIR, "policy_registry.json"), "w") as f:
        json.dump(policy_registry, f, indent=2)

    print(f"\n=== Data Preparation Complete ===")
    print(f"Folio master:     {counts['folio_master']} rows")
    print(f"KRA KYC:          {counts['kra_kyc']} rows")
    print(f"Bank mandates:    {counts['bank_mandates']} rows")
    print(f"Transactions:     {counts['transactions']} rows")
    print(f"Distributor:      {counts['distributor_master']} rows")
    print(f"Policy clauses:   {len(all_clauses)}")
    print(f"Data issues:      {len(data_issues)}")
    for di in data_issues:
        print(f"  [{di['type']}] {di.get('ref','')}: {di.get('value','')}")


if __name__ == "__main__":
    main()