from __future__ import annotations
import argparse, json, re, sys
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

TAG_RE = re.compile(r"<[^>]+>")

def bare(s: str) -> str:
    return TAG_RE.sub("", s).strip()

def main():
    ap = argparse.ArgumentParser(description="Gemini JSONL translation result validator")
    ap.add_argument("packet", type=Path)
    ap.add_argument("result", type=Path)
    ap.add_argument("--ko-map", type=Path, default=None,
                    help="reviewer only: existing Korean ko_map.json. Enables the reuse-similarity gate. Never ship this to the translator.")
    ap.add_argument("--min-len", type=int, default=12, help="gate ignores lines shorter than this (tag-stripped)")
    ap.add_argument("--max-exact-rate", type=float, default=0.20, help="gate fails above this exact-reuse rate")
    ap.add_argument("--max-mean-ratio", type=float, default=0.90, help="gate fails above this mean similarity")
    ap.add_argument("--show", type=int, default=10, help="how many most-similar lines to print")
    ns = ap.parse_args()
    packet = json.loads(ns.packet.read_text(encoding="utf-8"))
    expected = packet["entries"]
    lines = [x for x in ns.result.read_text(encoding="utf-8-sig").splitlines() if x.strip()]
    errors = []
    if len(lines) != len(expected): errors.append(f"count: expected {len(expected)}, got {len(lines)}")
    records = []
    for i, line in enumerate(lines, 1):
        try: rec = json.loads(line)
        except Exception as e:
            errors.append(f"line {i}: invalid json: {e}"); continue
        records.append(rec)
    for i, (src, rec) in enumerate(zip(expected, records), 1):
        if set(rec) != {"uid", "source_hash", "target_ko", "issues"}: errors.append(f"line {i}: wrong keys")
        if rec.get("uid") != src["uid"]: errors.append(f"line {i}: uid mismatch")
        if rec.get("source_hash") != src["source_hash"]: errors.append(f"line {i}: source_hash mismatch")
        if not isinstance(rec.get("target_ko"), str) or not rec.get("target_ko"): errors.append(f"line {i}: empty target_ko")
        if not isinstance(rec.get("issues"), list): errors.append(f"line {i}: issues must be array")
        target = rec.get("target_ko", "")
        for tok in src.get("required_tokens", []):
            if target.count(tok) != src["ja"].count(tok): errors.append(f"line {i}: protected token mismatch: {tok}")
        if Counter(TAG_RE.findall(target)) != Counter(TAG_RE.findall(src["ja"])):
            errors.append(f"line {i}: tag multiset mismatch")
    if errors:
        print("FAIL")
        for e in errors: print(e)
        return 1
    print(f"PASS: {len(expected)} records")

    # Reuse gate. The kit ships no existing Korean, so a high overlap here means the
    # translator reproduced the old translation instead of translating the Japanese.
    # Thresholds are deliberately loose: this catches wholesale reuse, not convergence.
    if ns.ko_map is None:
        print("SIMILARITY GATE: SKIPPED (no --ko-map given)")
        return 0
    ko_map = json.loads(ns.ko_map.read_text(encoding="utf-8"))
    pairs = []
    for src, rec in zip(expected, records):
        old = ko_map.get(src["uid"], {}).get("ko")
        if not old: continue
        new = rec["target_ko"]
        if len(bare(old)) < ns.min_len or len(bare(new)) < ns.min_len: continue
        pairs.append((src["uid"], old, new, SequenceMatcher(None, old, new).ratio()))
    if not pairs:
        print(f"SIMILARITY GATE: no comparable lines of {ns.min_len}+ chars")
        return 0
    exact = [x for x in pairs if x[1] == x[2]]
    ratios = sorted(x[3] for x in pairs)
    mean = sum(ratios) / len(ratios)
    p90 = ratios[min(len(ratios) - 1, int(len(ratios) * 0.9))]
    rate = len(exact) / len(pairs)
    print(f"SIMILARITY GATE: compared {len(pairs)} of {len(expected)} lines ({ns.min_len}+ chars)")
    print(f"  exact reuse : {len(exact)} / {len(pairs)} = {rate:.1%}   limit {ns.max_exact_rate:.0%}")
    print(f"  mean ratio  : {mean:.3f}   limit {ns.max_mean_ratio:.3f}")
    print(f"  p90 ratio   : {p90:.3f}")
    for uid, old, new, r in sorted(pairs, key=lambda x: -x[3])[:ns.show]:
        print(f"  [{'EXACT' if old == new else format(r, '.3f')}] {uid}")
        print(f"      old: {old[:90]}")
        print(f"      new: {new[:90]}")
    bad = []
    if rate > ns.max_exact_rate: bad.append(f"exact-reuse rate {rate:.1%} over {ns.max_exact_rate:.0%}")
    if mean > ns.max_mean_ratio: bad.append(f"mean similarity {mean:.3f} over {ns.max_mean_ratio:.3f}")
    if bad:
        print("SIMILARITY GATE: FAIL - " + "; ".join(bad))
        return 2
    print("SIMILARITY GATE: PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
