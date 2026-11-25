from __future__ import annotations
import argparse, json, re
from pathlib import Path

OPEN_RE = re.compile(r'<ruby(?:="[^"]*")?>', re.I)
CLOSE_RE = re.compile(r'</ruby>', re.I)

def main():
    ap = argparse.ArgumentParser(description="Apply reviewer-approved Korean ruby decisions to Gemini JSONL")
    ap.add_argument("result", type=Path)
    ap.add_argument("review_manifest", type=Path)
    ap.add_argument("out", type=Path)
    ns = ap.parse_args()
    review = json.loads(ns.review_manifest.read_text(encoding="utf-8"))
    decisions = {e["uid"]: e for e in review["entries"]}
    records = [json.loads(x) for x in ns.result.read_text(encoding="utf-8-sig").splitlines() if x.strip()]
    errors = []
    changed = 0
    for rec in records:
        uid, target = rec.get("uid"), rec.get("target_ko", "")
        decision = decisions.get(uid)
        if not decision:
            if OPEN_RE.search(target) or CLOSE_RE.search(target):
                errors.append(f"{uid}: ruby target has no review-manifest entry")
            continue
        mode = decision.get("decision", "pending")
        if mode == "pending":
            errors.append(f"{uid}: review decision is pending")
            continue
        if not decision.get("reviewer") or not decision.get("reviewed_at") or not decision.get("semantic_note"):
            errors.append(f"{uid}: reviewer/reviewed_at/semantic_note required")
            continue
        if mode == "keep":
            if len(OPEN_RE.findall(target)) != decision["ruby_open_count"] or len(CLOSE_RE.findall(target)) != decision["ruby_open_count"]:
                errors.append(f"{uid}: keep decision but ruby count differs")
        elif mode == "strip":
            if len(OPEN_RE.findall(target)) != decision["ruby_open_count"] or len(CLOSE_RE.findall(target)) != decision["ruby_open_count"]:
                errors.append(f"{uid}: strip decision but ruby count differs")
                continue
            rec["target_ko"] = CLOSE_RE.sub("", OPEN_RE.sub("", target))
            changed += 1
        elif mode == "manual":
            replacement = decision.get("approved_replacement_ko")
            if not isinstance(replacement, str) or not replacement:
                errors.append(f"{uid}: manual decision requires approved_replacement_ko")
                continue
            rec["target_ko"] = replacement
            changed += 1
        else:
            errors.append(f"{uid}: invalid decision {mode!r}")
    if errors:
        print("FAIL")
        for e in errors: print(e)
        return 1
    ns.out.write_text("".join(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n" for r in records), encoding="utf-8", newline="\n")
    print(f"PASS: {len(records)} records, {changed} ruby rows finalized")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
