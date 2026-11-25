"""한 칸 밀림 검출기.

uid/source_hash 는 제자리에 맞게 붙어 있고 target_ko 만 이웃 행 것이 붙은 경우를 잡는다.
킷 검증기는 이 결함을 통과시킨다 - 줄 단위로는 모든 계약이 지켜지기 때문이다.

원리: 정렬이 맞으면 ja 길이와 ko 길이의 로그비 오차가 offset 0 에서 가장 작다.
100행쯤 모으면 개별 행의 잡음이 상쇄되고 밀림은 offset +-1 쪽이 뚜렷하게 좋아진다.
숫자 보존은 독립 신호로 같이 본다 - 숫자는 번역돼도 살아남는다.
"""
from __future__ import annotations
import argparse, json, math, re, sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

TAG_RE = re.compile(r"<[^>]+>")
DIGIT_RE = re.compile(r"[0-9\uff10-\uff19]")
FULLWIDTH = {chr(0xff10 + i): str(i) for i in range(10)}


def bare(s: str) -> str:
    return TAG_RE.sub("", s).strip()


def digits(s: str) -> str:
    return "".join(sorted(FULLWIDTH.get(c, c) for c in DIGIT_RE.findall(s)))


def length_error(ja: str, ko: str) -> float:
    return abs(math.log((len(bare(ko)) + 1) / (len(bare(ja)) + 1)))


def score(jas, kos, offset: int):
    """offset 만큼 밀어 짝지었을 때의 평균 길이오차와 숫자 불일치 수."""
    errs, digit_bad, n = [], 0, 0
    for i, ja in enumerate(jas):
        j = i + offset
        if not (0 <= j < len(kos)):
            continue
        n += 1
        errs.append(length_error(ja, kos[j]))
        if digits(ja) != digits(kos[j]):
            digit_bad += 1
    if not n:
        return None
    return {"mean_len_error": sum(errs) / n, "digit_mismatch": digit_bad, "compared": n}


def check(packet_path: Path, result_path: Path, margin: float = 0.06, min_rows: int = 12):
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    entries = packet["entries"]
    recs = [json.loads(x) for x in result_path.read_text(encoding="utf-8-sig").splitlines() if x.strip()]
    if len(recs) != len(entries):
        return {"verdict": "SKIP", "reason": f"row count differs ({len(entries)} vs {len(recs)}) - run the kit validator first"}
    jas = [e["ja"] for e in entries]
    kos = [r.get("target_ko", "") for r in recs]
    if len(jas) < min_rows:
        return {"verdict": "SKIP", "reason": f"only {len(jas)} rows, below the {min_rows}-row floor for this test"}
    s0, sm, sp = score(jas, kos, 0), score(jas, kos, -1), score(jas, kos, 1)
    out = {"rows": len(jas), "offset_0": s0, "offset_-1": sm, "offset_+1": sp}
    hits = []
    for name, s in (("-1", sm), ("+1", sp)):
        if not s:
            continue
        if s["mean_len_error"] + margin < s0["mean_len_error"]:
            hits.append(f"offset {name} fits better by length ({s['mean_len_error']:.3f} vs {s0['mean_len_error']:.3f})")
        # 숫자 신호는 넓게 잡으면 정상 번역을 문다 - 실제 완주본에서 1건 오탐이 났다.
        # 어긋남이 여러 줄에 걸쳐 있고, 밀었을 때 절반 이하로 줄 때만 발화시킨다.
        if s0["digit_mismatch"] >= 3 and s["digit_mismatch"] * 2 <= s0["digit_mismatch"]:
            hits.append(f"offset {name} fits better by digits ({s['digit_mismatch']} vs {s0['digit_mismatch']})")
    out["verdict"] = "SHIFTED" if hits else "ALIGNED"
    out["evidence"] = hits
    return out


def main():
    ap = argparse.ArgumentParser(description="off-by-one alignment check for Gemini JSONL results")
    ap.add_argument("packet", type=Path)
    ap.add_argument("result", type=Path)
    ap.add_argument("--margin", type=float, default=0.06)
    ap.add_argument("--quiet", action="store_true")
    ns = ap.parse_args()
    r = check(ns.packet, ns.result, ns.margin)
    if not ns.quiet:
        print(json.dumps(r, ensure_ascii=False, indent=1))
    else:
        print(r["verdict"])
    return 2 if r["verdict"] == "SHIFTED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
