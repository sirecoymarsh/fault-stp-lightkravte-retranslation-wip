"""기존 완성본 재사용 검사 (검수자 전용).

킷 검증기의 유사도 게이트는 '태그 제거 후 12자 이상'으로 비교 대상을 골랐다.
그 기준은 「아아아아아아아아아아…」 같은 비명을 26자짜리 문장으로 취급한다.
번역 선택지가 하나뿐인 줄이라 우연히 같아지는데, 그게 재사용률을 밀어 올린다.

변별력을 글자 수가 아니라 '반복을 접은 뒤 남는 서로 다른 글자 수'로 잰다.
"""
from __future__ import annotations
import argparse, json, re, sys
from difflib import SequenceMatcher
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

KIT = Path(r"P:\AI\Codex\projects\fault-stp-lightkravte-gemini-scenario-kit-2026-08-29")
RESULTS = Path(r"P:\AI\Codex\projects\fault-stp-lightkravte-gemini-results")
KO_MAP = Path(r"P:\AI\Codex\projects\_migrated_c_documents_codex\2026-07-25\new-chat\work\localization\build\ko_map.json")
TAG_RE = re.compile(r"<[^>]+>")
RUN_RE = re.compile(r"(.)\1+")


def distinctness(s: str) -> int:
    """반복을 접고 남는 서로 다른 글자 수. 비명·말줄임은 여기서 걸러진다."""
    return len(set(RUN_RE.sub(r"\1", TAG_RE.sub("", s)).strip()))


def measure(stem: str, min_distinct: int):
    pf = KIT / "packets" / stem.split("-")[0] / f"{stem}.json"
    rf = RESULTS / f"{stem}.ko.jsonl"
    if not (pf.exists() and rf.exists()):
        return None
    km = measure.km
    recs = [json.loads(x) for x in rf.read_text(encoding="utf-8-sig").splitlines() if x.strip()]
    pairs = []
    for r in recs:
        old = km.get(r["uid"], {}).get("ko")
        new = r.get("target_ko", "")
        if not old or not new:
            continue
        if min(distinctness(old), distinctness(new)) < min_distinct:
            continue
        pairs.append((r["uid"], old, new, SequenceMatcher(None, old, new).ratio()))
    if not pairs:
        return None
    exact = [p for p in pairs if p[1] == p[2]]
    return {"stem": stem, "n": len(pairs), "exact": len(exact),
            "rate": len(exact) / len(pairs),
            "mean": sum(p[3] for p in pairs) / len(pairs),
            "exact_rows": [(p[0], p[1]) for p in exact]}


def main():
    ap = argparse.ArgumentParser(description="기존 완성본 재사용 검사")
    ap.add_argument("--min-distinct", type=int, default=8)
    ap.add_argument("--min-rows", type=int, default=20)
    ap.add_argument("--max-rate", type=float, default=0.20)
    ap.add_argument("--max-mean", type=float, default=0.90)
    ap.add_argument("--stem", default=None)
    ap.add_argument("--verbose", action="store_true")
    ns = ap.parse_args()
    measure.km = json.loads(KO_MAP.read_text(encoding="utf-8"))

    stems = [ns.stem] if ns.stem else sorted(f.name[:-9] for f in RESULTS.glob("*.ko.jsonl"))
    rows = [m for m in (measure(s, ns.min_distinct) for s in stems) if m]
    judged = [m for m in rows if m["n"] >= ns.min_rows]
    fail = [m for m in judged if m["rate"] > ns.max_rate or m["mean"] > ns.max_mean]

    tn = sum(m["n"] for m in rows)
    te = sum(m["exact"] for m in rows)
    print(f"패킷 {len(rows)} · 비교행 {tn} (변별력 {ns.min_distinct}자 이상) · 정확일치 {te} = {te/tn:.1%}")
    print(f"판정 대상 {len(judged)}패킷 (비교행 {ns.min_rows}행 이상) · 임계 초과 {len(fail)}패킷")
    if judged:
        rs = sorted(m["rate"] for m in judged)
        ms = sorted(m["mean"] for m in judged)
        print(f"  정확일치율 분포: 중앙 {rs[len(rs)//2]:.1%}, 최대 {rs[-1]:.1%}")
        print(f"  평균유사도 분포: 중앙 {ms[len(ms)//2]:.3f}, 최대 {ms[-1]:.3f}")
    for m in fail:
        print(f"\n초과 {m['stem']}: {m['exact']}/{m['n']}={m['rate']:.1%} 평균 {m['mean']:.3f}")
        for uid, ko in m["exact_rows"][:5]:
            print(f"    {uid} :: {ko[:70]}")
    if ns.verbose:
        for m in sorted(rows, key=lambda x: -x["rate"])[:10]:
            print(f"  {m['stem']:22s} {m['exact']:3d}/{m['n']:3d} = {m['rate']:5.1%}  평균 {m['mean']:.3f}")
    return 2 if fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
