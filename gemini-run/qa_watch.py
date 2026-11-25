"""산출물 감시. 새로 생긴 것만 알린다.

두 가지를 거른다.
- 같은 사실 반복 통보: 이미 알린 것은 다시 내지 않는다.
- 방금 쓴 파일을 읽어 생기는 헛알람: 문제를 보면 40초 뒤 다시 확인하고, 사라졌으면 넘어간다.
"""
from __future__ import annotations
import json, re, subprocess, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
except Exception:
    pass

RUN = Path(__file__).parent
KIT = Path(r"P:\AI\Codex\projects\fault-stp-lightkravte-gemini-scenario-kit-2026-08-29")
RESULTS = Path(r"P:\AI\Codex\projects\fault-stp-lightkravte-gemini-results")
KO_MAP = Path(r"P:\AI\Codex\projects\_migrated_c_documents_codex\2026-07-25\new-chat\work\localization\build\ko_map.json")
TOTAL = 93
PERIOD = 120
STALL = 600


def dispatch():
    r = subprocess.run([sys.executable, str(RUN / "next.py")], capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    out = r.stdout or ""
    m = re.search(r"통과 (\d+)/(\d+) 패킷, (\d+)/(\d+)행", out)
    passed = int(m.group(1)) if m else 0
    rows = int(m.group(3)) if m else 0
    back = re.search(r"=== 되돌림: (\S+) \((\w+)\) ===\n((?:  .*\n)*)", out)
    returned = (back.group(1), back.group(2), back.group(3).strip().splitlines()[:2]) if back else None
    return passed, rows, returned


CONV_ID = "f1dc4050-c943-48ba-866f-64a28b5530b3"


def reuse_new(seen: set):
    """기존 완성본 재사용. 변별력 8자 이상인 줄만 세고, 20행 이상인 패킷만 판정한다."""
    import importlib, json as _json
    import reuse_check as R
    R = importlib.reload(R)
    R.measure.km = _json.loads(R.KO_MAP.read_text(encoding="utf-8"))
    out = []
    for f in sorted(RESULTS.glob("*.ko.jsonl")):
        stem = f.name[:-9]
        m = R.measure(stem, 8)
        if not m or m["n"] < 20:
            continue
        if m["rate"] > 0.30 or m["mean"] > 0.90:
            key = (stem, round(m["rate"], 3))
            if key not in seen:
                seen.add(key)
                out.append(f"재사용 {stem}: {m['exact']}/{m['n']}={m['rate']:.1%} 평균 {m['mean']:.3f}")
    return out


def scope_new(seen: set):
    """열람 범위 감사. 통계가 아니라 사실이다. 여기가 물면 진짜다."""
    import importlib
    import scope_audit as S
    S = importlib.reload(S)
    r = S.audit(CONV_ID)
    if "error" in r:
        return []
    out = []
    for x in (r.get("forbidden") or []) + (r.get("outside") or []):
        if x not in seen:
            seen.add(x)
            out.append(f"범위 위반 접근: {x[:130]}")
    return out


def fidelity_new(seen_findings: set):
    """일본어 원문 기준 충실도 게이트. 새로 생긴 지적만 돌려준다."""
    import importlib
    import ja_fidelity as F
    F = importlib.reload(F)      # 게이트를 고치면 감시를 재시작하지 않아도 반영된다
    rows = F.collect()
    f = F.run(rows, F.load_terms(), 0, 24)
    fresh = []
    for kind in ("glossary", "digits", "residue", "length", "repeat"):
        for uid, why, ja, ko in f.get(kind, []):
            key = (kind, uid, why)
            if key in seen_findings:
                continue
            seen_findings.add(key)
            fresh.append(f"{kind} {uid}: {why} | KO: {ko[:60]}")
    return fresh


def main():
    reported, last_pass, last_move, stalled = set(), -1, time.time(), False
    seen_findings, seen_reuse, seen_scope = set(), set(), set()
    fidelity_new(seen_findings)   # 이미 보고한 것은 다시 내지 않는다
    reuse_new(seen_reuse)
    scope_new(seen_scope)
    print(f"감시 시작 - {PERIOD}초 주기, 무진전 {STALL//60}분이면 알림")
    while True:
        passed, rows, returned = dispatch()

        if returned and returned[0] not in reported:
            time.sleep(40)                                   # 저쪽이 고치는 중일 수 있다
            p2, r2, ret2 = dispatch()
            if ret2 and ret2[0] == returned[0]:
                reported.add(returned[0])
                print(f"되돌림 {ret2[0]} ({ret2[1]}): {' / '.join(ret2[2])}")
            passed, rows = p2, r2

        for msg in reuse_new(seen_reuse):
            print(msg)
        for msg in scope_new(seen_scope):
            print(msg)

        for msg in fidelity_new(seen_findings):
            print(f"충실도 {msg}")

        if passed != last_pass:
            if last_pass >= 0 and passed // 20 > last_pass // 20:
                print(f"진행 {passed}/{TOTAL} 패킷, {rows}/6746행")
            last_pass, last_move, stalled = passed, time.time(), False
        elif not stalled and time.time() - last_move > STALL:
            stalled = True
            print(f"무진전 {STALL//60}분: {passed}/{TOTAL} 패킷에서 멈춤")

        if passed >= TOTAL:
            print(f"전량 통과 {passed}/{TOTAL} 패킷 6746행. 최종 검수 필요.")
            return 0
        time.sleep(PERIOD)


if __name__ == "__main__":
    raise SystemExit(main())
