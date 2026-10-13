#!/usr/bin/env python3
"""Eval runner: submit requests against base URL and score results."""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BASE_URL = os.environ.get("EVAL_BASE_URL", "http://127.0.0.1:8000")
OUT_DIR = os.path.join(ROOT, "eval", "results")


def load_inbox() -> list[dict]:
    path = os.path.join(ROOT, "Data", "inbox", "requests.json")
    with open(path) as f:
        return json.load(f)


def load_cases() -> list[dict]:
    cases_dir = os.path.join(ROOT, "eval", "cases")
    cases = []
    if os.path.isdir(cases_dir):
        for fn in sorted(os.listdir(cases_dir)):
            if fn.endswith(".json"):
                with open(os.path.join(cases_dir, fn)) as f:
                    cases.append(json.load(f))
    return cases


def main():
    import httpx
    os.makedirs(OUT_DIR, exist_ok=True)
    inbox = load_inbox()
    cases = load_cases()

    results = []
    client = httpx.Client(timeout=30.0)

    # Build expected map from cases by request_id
    expected_map = {}
    for c in cases:
        rid = c.get("request_id", "")
        if rid:
            expected_map[rid] = c

    # Run inbox requests
    for item in inbox:
        req = item.get("request", item)
        request_id = req.get("request_id", "unknown")
        try:
            resp = client.post(f"{BASE_URL}/requests", json=req)
            data = resp.json() if resp.status_code < 500 else {"error": f"HTTP {resp.status_code}", "outcome": "PEND"}
            data["_http_status"] = resp.status_code
        except Exception as e:
            data = {"error": str(e), "outcome": "PEND", "_http_status": 0}
        expected = item.get("expected", {}) or expected_map.get(request_id, {})
        if expected:
            score = score_one(data, expected)
            data["_score"] = score
        data["_request_id"] = request_id
        data["_elapsed"] = time.perf_counter()
        results.append(data)
        score_str = ""
        if data.get("_score"):
            s = data["_score"]
            score_str = f" [outcome={'✓' if s['outcome_match'] else '✗'} reasons={'✓' if s['reason_codes']['match'] else '✗'}]"
        print(f"  {request_id}: {data.get('outcome','?')} (HTTP {data.get('_http_status','?')}){score_str}")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(OUT_DIR, f"{timestamp}.json")
    with open(out_path, "w") as f:
        json.dump({"timestamp": timestamp, "base_url": BASE_URL, "results": results}, f, indent=2, default=str)
    print(f"\nResults written to {out_path}")
    print(f"Total: {len(results)} requests")

    outcomes = {}
    pass_count = 0
    fail_count = 0
    for r in results:
        o = r.get("outcome", "?")
        outcomes[o] = outcomes.get(o, 0) + 1
        s = r.get("_score", {})
        if s.get("outcome_match") and s.get("reason_codes", {}).get("match"):
            pass_count += 1
        elif s:
            fail_count += 1
    print(f"Outcomes: {outcomes}")
    print(f"Scored: {pass_count} passed, {fail_count} failed")


def score_one(actual: dict, expected: dict) -> dict:
    score = {"outcome_match": False, "reason_codes": {"expected": [], "actual": [], "match": False}}
    exp_outcome = expected.get("outcome", "")
    act_outcome = actual.get("outcome", "")
    score["outcome_match"] = exp_outcome == act_outcome
    exp_reasons = expected.get("reason_codes", [])
    act_reasons = actual.get("reason_codes", [])
    score["reason_codes"]["expected"] = exp_reasons
    score["reason_codes"]["actual"] = act_reasons
    score["reason_codes"]["match"] = set(exp_reasons) == set(act_reasons)
    unsafe = exp_outcome not in ("PROCEED", "PROCEED_MODIFIED") and act_outcome in ("PROCEED", "PROCEED_MODIFIED")
    overcautious = exp_outcome == "PROCEED" and act_outcome != "PROCEED"
    score["unsafe"] = unsafe
    score["overcautious"] = overcautious
    # Score per-check if checks provided
    exp_checks = expected.get("checks", {})
    act_checks_raw = actual.get("checks", [])
    act_checks = {}
    if isinstance(act_checks_raw, list):
        for c in act_checks_raw:
            if isinstance(c, dict):
                act_checks[c.get("check_id", "")] = c.get("result", "")
            else:
                act_checks[getattr(c, "check_id", "")] = getattr(c, "result", "")
    elif isinstance(act_checks_raw, dict):
        act_checks = act_checks_raw
    check_scores = {}
    for cid, exp_val in exp_checks.items():
        act_val = act_checks.get(cid, "MISSING")
        check_scores[cid] = {"expected": exp_val, "actual": act_val, "match": exp_val == act_val}
    score["checks"] = check_scores
    return score


if __name__ == "__main__":
    main()