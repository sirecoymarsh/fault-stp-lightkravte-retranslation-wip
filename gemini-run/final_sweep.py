"""완주 후 일괄 훑기. 검수 중 쌓인 지적을 uid 단위로 고친다.

AG 에게는 "이미 통과한 패킷을 다시 내지 마라"고 했다. 재제출은 검수를 처음부터
다시 하게 만든다. 대신 여기서 해당 행만 고치고 전체 게이트를 다시 돌린다.

원칙 - 태그 다중집합과 uid/source_hash 는 건드리지 않는다. 3인칭을 푸는 교정에서
글자 수를 줄이지 않는다. 줄이면 화면 호흡이 원문보다 빨라진다.
"""
from __future__ import annotations
import json, re, sys
from collections import Counter
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

RESULTS = Path(r"P:\AI\Codex\projects\fault-stp-lightkravte-gemini-results")
TAG_RE = re.compile(r"<[^>]+>")

# uid -> (사유, 고친 문장). 원문 대조는 아래 검증에서 다시 한다.
FIXES = {
    # 장음부호 ー 와 촉음 ッ 를 한글 모음 연장으로 푼다. 원문의 늘어진 길이를 유지한다.
    "ch01-03:75:bf3cba22":
        ("가나 잔류 ー", "아아아앗!<br>벌써 들켜 버렸네!!!"),
    "ch01-03:385:470217e5":
        ("가나 잔류 ー", "으, 으워어어어어어어어어어어어어어어어어이이익!?"),
    "ch01-03:391:78121dda":
        ("가나 잔류 ー", "꺄이이이이이이이이이이이이이잉!?"),
    "ch01-03:397:2d3e3002":
        ("가나 잔류 ー ッ", "뷜세리오오오오오오옷!!"),
    # 독백의 3인칭 대명사를 지시어로 푼다. 글자 수를 줄이지 않는다.
    "ch01-03:335:fb80f192":
        # 그녀 -> 저 사람. 다른 부분은 손대지 않는다. 글자 수는 오히려 +1 이다.
        ("3인칭 대명사 그녀", "절세미녀라는 말은<br>저 사람 같은 이를 위해 존재하는 것이 틀림없다."),
    # 같은 원문이 두 갈래로 갈렸다. 원문에 더 붙는 쪽으로 통일한다.
    # そうだったんですね 의 んです 어감은 "거군요" 쪽이 살린다. 짧은 쪽으로 깎지 않는다.
    "ch01-00:321:5b7bb93b":
        ("반복 원문 통일", "그, 그랬던 거군요…"),
    "ch01-11:520:5b7bb93b":
        ("반복 원문 통일", "그, 그랬던 거군요…"),
    # ドラマチックなこと 에 없는 수식어 "거창하고" 가 붙었다. 원문에 없는 것은 뺀다.
    "ch03-02:596:d8e62c26":
        ("원문에 없는 수식어", "너무 드라마틱한 소리는 하고 싶지 않지만 말이야,"),
}


def main():
    applied, skipped = [], []
    for rf in sorted(RESULTS.glob("*.ko.jsonl")):
        lines = [json.loads(x) for x in rf.read_text(encoding="utf-8-sig").splitlines() if x.strip()]
        changed = False
        for rec in lines:
            fix = FIXES.get(rec["uid"])
            if not fix:
                continue
            why, new = fix
            old = rec["target_ko"]
            if old == new:
                skipped.append((rec["uid"], "이미 그 값"))
                continue
            if Counter(TAG_RE.findall(old)) != Counter(TAG_RE.findall(new)):
                skipped.append((rec["uid"], "태그 다중집합이 달라져 적용 안 함"))
                continue
            rec["target_ko"] = new
            changed = True
            applied.append((rec["uid"], why, old, new, len(TAG_RE.sub("", new)) - len(TAG_RE.sub("", old))))
        if changed:
            rf.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in lines),
                          encoding="utf-8", newline="\n")

    print(f"적용 {len(applied)}건 / 건너뜀 {len(skipped)}건")
    for uid, why, old, new, d in applied:
        print(f"  {uid} [{why}] 표시길이 {d:+d}자")
        print(f"    전: {old}")
        print(f"    후: {new}")
    for uid, why in skipped:
        print(f"  건너뜀 {uid}: {why}")
    missing = set(FIXES) - {a[0] for a in applied} - {s[0] for s in skipped}
    if missing:
        print(f"\n산출물에서 못 찾은 uid: {sorted(missing)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
