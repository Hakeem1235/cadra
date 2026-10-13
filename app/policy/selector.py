from __future__ import annotations

from datetime import datetime
from app.schemas import AmcCode
from app.trace import TraceCollector


SOP_VERSIONS = [
    {"doc_id": "VAL-OPS-TCC-SOP", "version": "4.1", "effective_from": "2026-08-01", "status": "Current", "file": "Validus_TCC_SOP_v4.1.docx"},
    {"doc_id": "VAL-OPS-TCC-SOP", "version": "3.2", "effective_from": "2025-01-01", "status": "Superseded", "file": "Validus_TCC_SOP_v3.2.pdf"},
]

ADDENDA = [
    {"doc_id": "TMF-ADD-02", "version": "1.0", "effective_from": "2026-09-15", "applies_to_amc": "TMF", "prevails_over_sop": True, "file": "Tungabhadra_MF_Client_Addendum_TMF-ADD-02.pdf"},
]


def select_policies(received_at: datetime, amc_code: AmcCode | None, trace: TraceCollector | None = None) -> tuple[list[dict], list[dict]]:
    received_date = received_at.date().isoformat()
    applicable = [s for s in SOP_VERSIONS if s["effective_from"] <= received_date]
    selected = sorted(applicable, key=lambda s: s["effective_from"], reverse=True)[:1]
    for s in selected:
        if trace:
            trace.record_doc(s["file"], s["version"])
    selected_addenda = []
    if amc_code == AmcCode.TMF:
        applicable_add = [a for a in ADDENDA if a["applies_to_amc"] == "TMF" and a["effective_from"] <= received_date]
        if applicable_add:
            selected_addenda = sorted(applicable_add, key=lambda a: a["effective_from"], reverse=True)[:1]
            for a in selected_addenda:
                if trace:
                    trace.record_doc(a["file"], a["version"])
    return selected, selected_addenda