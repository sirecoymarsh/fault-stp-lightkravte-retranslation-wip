"""일본어 원문에 걸리는 충실도 게이트.

기존 한국어 완성본은 쓰지 않는다. 판단의 근거는 패킷의 ja 필드뿐이다.
옛 번역 대조 게이트가 "베꼈나"를 본다면 이쪽은 "맞게 옮겼나"를 본다.

검사 다섯:
  glossary  잠긴 고유명사가 원문에 있는데 번역문에 대응 표기가 없다
  digits    원문 숫자가 번역문에서 사라졌다
  residue   번역문 표시부에 일본어 문자가 남았다 (태그 속성값은 제외)
  length    길이비가 코퍼스 분포에서 크게 벗어난다 (누락·증설 후보)
  repeat    같은 원문이 다른 번역으로 갈렸다

용어 검사는 part_of_speech=proper_noun 인 locked 항목만 본다. 일반 명사를 문자열로
박으면 활용형에서 깨진다.
"""
from __future__ import annotations
import argparse, json, re, sys
from collections import defaultdict
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

KIT = Path(r"P:\AI\Codex\projects\fault-stp-lightkravte-gemini-scenario-kit-2026-08-29")
RESULTS = Path(r"P:\AI\Codex\projects\fault-stp-lightkravte-gemini-results")

TAG_RE = re.compile(r"<[^>]+>")
KANA_RE = re.compile(r"[\u3041-\u309f\u30a1-\u30ff]")
HAN_RE = re.compile(r"[\u4e00-\u9fff]")
DIGIT_RE = re.compile(r"[0-9\uff10-\uff19]")
FW = {chr(0xff10 + i): str(i) for i in range(10)}


def strip_tags(s: str) -> str:
    return TAG_RE.sub("", s)


def norm_digits(s: str) -> str:
    return "".join(sorted(FW.get(c, c) for c in DIGIT_RE.findall(s)))


# 한국어는 수를 고유어로도 적는다. 二回 -> "두 번", 20人 -> "스무 명", 14歳 -> "열네 살".
# 자릿수로 쪼개면 20 을 2 와 0 으로 보게 되므로 숫자 덩어리 단위로 본다.
_ONE = {1: ("하나", "한"), 2: ("둘", "두"), 3: ("셋", "세"), 4: ("넷", "네"), 5: ("다섯",),
        6: ("여섯",), 7: ("일곱",), 8: ("여덟",), 9: ("아홉",)}
# 한국어 관용 수사. 三四倍 -> "서너 배", 一日 -> "하루".
_IDIOM = {1: ("하루", "한번"), 2: ("이틀", "두세"), 3: ("사흘", "서너", "두세", "사나흘"),
          4: ("나흘", "서너", "네댓", "사나흘"), 5: ("닷새", "네댓", "대여섯"),
          6: ("엿새", "대여섯", "예닐곱"), 7: ("이레", "예닐곱"), 8: ("여드레",),
          9: ("아흐레",), 10: ("열흘",)}
# 서수. 一 -> "첫 번째", 二 -> "둘째".
_ORD = {1: ("첫", "첫째"), 2: ("둘째", "두번째"), 3: ("셋째",), 4: ("넷째",), 5: ("다섯째",),
        6: ("여섯째",), 7: ("일곱째",), 8: ("여덟째",), 9: ("아홉째",), 10: ("열째",)}
_TEN = {10: ("열",), 20: ("스물", "스무"), 30: ("서른",), 40: ("마흔",), 50: ("쉰",),
        60: ("예순",), 70: ("일흔",), 80: ("여든",), 90: ("아흔",)}
_SINO = "영일이삼사오육칠팔구"


def _korean_forms(n: int):
    """n 을 한국어로 적을 수 있는 표기들. 고유어와 한자어 둘 다."""
    out = set()
    if n == 0:
        return {"영", "공"}
    if n < 10:
        out |= set(_ONE.get(n, ())) | set(_IDIOM.get(n, ())) | set(_ORD.get(n, ()))
        out.add(_SINO[n])
    elif n < 100:
        t, o = (n // 10) * 10, n % 10
        for tw in _TEN.get(t, ()):
            out |= {tw + ow for ow in _ONE.get(o, ())} if o else {tw}
        sino = ("" if t == 10 else _SINO[t // 10]) + "십" + (_SINO[o] if o else "")
        out.add(sino)
        out |= set(_IDIOM.get(n, ())) | set(_ORD.get(n, ()))
    else:
        out.add(str(n))
    return {x for x in out if x}


NUM_RUN = re.compile(r"[0-9０-９]+")


def digits_missing(ja_disp: str, ko_disp: str) -> str:
    """원문 숫자 덩어리 중 번역문에서 자취를 찾을 수 없는 것만 돌려준다."""
    ko_norm = "".join(FW.get(c, c) for c in ko_disp)
    gone = []
    for run in NUM_RUN.findall(ja_disp):
        n = int("".join(FW.get(c, c) for c in run))
        if str(n) in ko_norm:
            continue
        if any(w in ko_disp for w in _korean_forms(n)):
            continue
        gone.append(str(n))
    return ",".join(dict.fromkeys(gone))


def load_terms():
    g = json.loads((KIT / "gemini" / "glossary.json").read_text(encoding="utf-8"))
    out = []
    for e in g["entries"]:
        if e["status"] != "locked" or e["part_of_speech"] != "proper_noun":
            continue
        forms = [e["target"], e.get("canonical_spelling") or ""] + list(e.get("allowed_variants") or [])
        out.append((e["term_id"], e["source"], [f for f in forms if f]))
    return out


def collect():
    rows = []
    for rf in sorted(RESULTS.glob("*.ko.jsonl")):
        stem = rf.name[:-9]
        pf = KIT / "packets" / stem.split("-")[0] / f"{stem}.json"
        if not pf.exists():
            continue
        E = {e["uid"]: e for e in json.loads(pf.read_text(encoding="utf-8"))["entries"]}
        for line in rf.read_text(encoding="utf-8-sig").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            src = E.get(r["uid"])
            if src:
                rows.append((stem, r["uid"], src["ja"], r.get("target_ko", ""), r.get("issues") or []))
    return rows


def run(rows, terms, z: float, min_len: int):
    findings = defaultdict(list)

    for stem, uid, ja, ko, issues in rows:
        ja_disp, ko_disp = strip_tags(ja), strip_tags(ko)

        for tid, src, forms in terms:
            if src in ja_disp and not any(f in ko_disp for f in forms):
                findings["glossary"].append((uid, f"{tid} {src} -> {forms[0]} 없음", ja, ko))

        missing = digits_missing(ja_disp, ko_disp)
        if missing:
            findings["digits"].append((uid, f"원문 {norm_digits(ja_disp)} 중 {missing} 사라짐", ja, ko))

        kana = KANA_RE.findall(ko_disp)
        han = HAN_RE.findall(ko_disp)
        if kana or han:
            findings["residue"].append((uid, f"kana={''.join(kana)[:12]} han={''.join(han)[:12]}", ja, ko))

    # 길이비는 코퍼스 평균으로 재면 결함이 평균을 같이 끌고 가서 눈이 먼다.
    # 실측(정상 출력 1,667행)에서 비율은 0.68~1.86 안에 들어왔다. 고정 띠로 본다.
    for _, uid, ja, ko, _ in rows:
        lj, lk = len(strip_tags(ja)), len(strip_tags(ko))
        if lj < min_len:
            continue
        ratio = (lk + 1) / (lj + 1)
        if ratio < 0.45:
            findings["length"].append((uid, f"번역이 원문의 {ratio:.2f}배 - 누락 의심", ja, ko))
        elif ratio > 2.2:
            findings["length"].append((uid, f"번역이 원문의 {ratio:.2f}배 - 증설 의심", ja, ko))

    by_ja = defaultdict(set)
    for _, uid, ja, ko, _ in rows:
        by_ja[ja].add(ko)
    for ja, kos in by_ja.items():
        if len(kos) > 1 and len(strip_tags(ja)) >= 12:
            findings["repeat"].append(("-", f"{len(kos)}가지로 갈림", ja, " || ".join(sorted(kos))[:160]))

    return findings


def main():
    ap = argparse.ArgumentParser(description="일본어 원문 기준 충실도 게이트")
    ap.add_argument("--min-len", type=int, default=24, help="길이 검사 최소 원문 길이")
    ap.add_argument("--show", type=int, default=4, help="종류별 출력 건수")
    ns = ap.parse_args()

    rows = collect()
    terms = load_terms()
    f = run(rows, terms, 0, ns.min_len)
    total = sum(len(v) for v in f.values())
    print(f"검사 {len(rows)}행 · 잠긴 고유명사 {len(terms)}개 · 지적 {total}건")
    for k in ("glossary", "digits", "residue", "length", "repeat"):
        v = f.get(k, [])
        rate = f" ({100*len(v)/len(rows):.2f}%)" if rows else ""
        print(f"\n[{k}] {len(v)}건{rate}")
        for uid, why, ja, ko in v[:ns.show]:
            print(f"  {uid} :: {why}")
            print(f"    JA: {ja[:88]}")
            print(f"    KO: {ko[:88]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
