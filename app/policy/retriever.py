from __future__ import annotations

import json
import os
import re
from app.trace import TraceCollector

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
INDEX_PATH = os.path.join(ROOT, "build", "policy_index.json")

_clause_cache: dict | None = None


def _load_index() -> dict[str, list[dict]]:
    global _clause_cache
    if _clause_cache is not None:
        return _clause_cache
    if os.path.exists(INDEX_PATH):
        with open(INDEX_PATH) as f:
            _clause_cache = json.load(f)
    else:
        _clause_cache = {"clauses": []}
    return _clause_cache


def get_clause(doc_id: str, version: str, clause_id: str) -> dict | None:
    idx = _load_index()
    for c in idx.get("clauses", []):
        if c.get("doc_id") == doc_id and c.get("version") == version and c.get("clause_id") == clause_id:
            return c
    return None


def search(query: str, filters: dict | None = None, top_k: int = 3) -> list[dict]:
    idx = _load_index()
    clauses = idx.get("clauses", [])
    if filters:
        doc_filter = filters.get("doc")
        ver_filter = filters.get("version")
        if doc_filter:
            clauses = [c for c in clauses if c.get("doc_id") == doc_filter]
        if ver_filter:
            clauses = [c for c in clauses if c.get("version") == ver_filter]
    q = query.lower()
    scored = []
    for c in clauses:
        text = (c.get("text", "") + " " + c.get("title", "") + " " + c.get("clause_id", "")).lower()
        score = sum(1 for w in q.split() if w in text)
        if score > 0:
            scored.append((score, c))
    scored.sort(key=lambda x: -x[0])
    return [s[1] for s in scored[:top_k]]