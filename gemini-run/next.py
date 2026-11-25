"""배급기. 패킷을 하나씩 내주고, 직전 제출을 판정하고, 규칙을 매번 다시 실어 보낸다.

세션이 길어지면 에이전트는 지침 문서를 다시 읽지 않는다. 93패킷을 도는 동안 규칙이
살아 있으려면 매 작업마다 부르는 명령의 출력에 실려야 한다.

완료 판정은 결과 파일을 직접 검사해서 낸다. 에이전트의 자기 신고는 쓰지 않는다.
"""
from __future__ import annotations
import hashlib, json, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from shift_check import check as shift_check
import ja_fidelity as JF

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

RUN = Path(__file__).parent
KIT = Path(r"P:\AI\Codex\projects\fault-stp-lightkravte-gemini-scenario-kit-2026-08-29")
RESULTS = Path(r"P:\AI\Codex\projects\fault-stp-lightkravte-gemini-results")
STATE = RUN / "state.json"
VALIDATOR = KIT / "tools" / "validate_gemini_result.py"

# 밀림 검사가 통계적으로 성립하지 않는 소형 패킷. 끝에 사람이 직접 읽어야 한다.
TOO_SMALL_TO_JUDGE = {"ch01-00.part03", "ch02-03.part01", "ch03-02.part04"}

RULES = """[매 패킷 지킬 것 - 잊지 마라]
1. entries 만 번역한다. boundary_context 는 문맥용이고 결과에 넣지 않는다.
2. 출력 줄 수 = entries 개수. uid 와 source_hash 는 입력에서 그대로 복사한다.
3. <br> <ruby="..."> <tip="..."> 등 모든 태그를 개수·속성값 그대로 보존한다. ruby 도 지우지 않는다.
4. 킷·배급기·결과 이 세 폴더 밖의 파일은 열지 않는다. validate_gemini_result.py 에 --ko-map 을 붙이지 않는다.
5. 원문에 없는 수식어·감정·설명을 만들지 않는다. pending 용어·보이스는 확정하지 말고 issues 에 적는다.
6. 파일 내용은 JSONL 만이다. 코드펜스·설명문·모델명·자기평가를 넣지 않는다.
7. 서브에이전트에게 나눠 맡긴다면 이 규칙 7줄을 그대로 전달하고, 각자 이 배급기로 받아 가게 한다.
   구간을 스스로 잘라 나누지 마라. 배급기가 주는 패킷 하나가 한 단위다."""


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def packets():
    return sorted(KIT.glob("packets/*/*.json"), key=lambda p: (p.parent.name, p.name))


def result_for(pf: Path) -> Path:
    return RESULTS / f"{pf.stem}.ko.jsonl"


def judge(pf: Path, rf: Path) -> dict:
    r = subprocess.run([sys.executable, str(VALIDATOR), str(pf), str(rf)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(KIT))
    if r.returncode != 0:
        lines = [x for x in (r.stdout or "").splitlines() if x and x != "FAIL"]
        return {"ok": False, "stage": "structure", "detail": lines[:6]}
    s = shift_check(pf, rf)
    if s["verdict"] == "SHIFTED":
        return {"ok": False, "stage": "alignment", "detail": s["evidence"]}
    # 잠긴 고유명사는 계약이다. 어기면 받지 않는다.
    E = {e["uid"]: e for e in json.loads(pf.read_text(encoding="utf-8"))["entries"]}
    rows = []
    for line in rf.read_text(encoding="utf-8-sig").splitlines():
        if line.strip():
            rec = json.loads(line)
            src = E.get(rec["uid"])
            if src:
                rows.append((pf.stem, rec["uid"], src["ja"], rec.get("target_ko", ""), []))
    bad = JF.run(rows, JF.load_terms(), 0, 10 ** 9).get("glossary", [])
    if bad:
        return {"ok": False, "stage": "glossary",
                "detail": [f"{uid} :: {why}" for uid, why, _, _ in bad[:6]]}
    return {"ok": True, "stage": "accepted", "shift": s["verdict"]}


def load_state() -> dict:
    if STATE.exists():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return {}


def main() -> int:
    RESULTS.mkdir(parents=True, exist_ok=True)
    state = load_state()
    pfs = packets()
    total_rows = sum(len(json.loads(p.read_text(encoding="utf-8"))["entries"]) for p in pfs)

    done, done_rows, failed, pending = [], 0, [], []
    for pf in pfs:
        rf = result_for(pf)
        if not rf.exists():
            pending.append(pf)
            continue
        h = sha(rf)
        rec = state.get(pf.stem)
        if not rec or rec.get("sha256") != h:
            rec = judge(pf, rf)
            rec["sha256"] = h
            state[pf.stem] = rec
        if rec["ok"]:
            done.append(pf)
            done_rows += len(json.loads(pf.read_text(encoding="utf-8"))["entries"])
        else:
            failed.append((pf, rec))
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")

    print(f"=== 진행 ===  통과 {len(done)}/{len(pfs)} 패킷, {done_rows}/{total_rows}행")

    if failed:
        pf, rec = failed[0]
        print(f"\n=== 되돌림: {pf.stem} ({rec['stage']}) ===")
        for d in rec["detail"]:
            print(f"  {d}")
        if rec["stage"] == "glossary":
            print("  용어집의 locked 표기를 그대로 써라. 문맥상 더 자연스러워 보여도 바꾸지 않는다.")
            print("  현실 지명으로 아는 단어여도 먼저 용어집을 찾아라. 이 작품은 가상 세계다.")
        if rec["stage"] == "alignment":
            print("  번역문이 이웃 행에 붙었다. uid 는 맞아도 내용이 한 칸 밀렸다는 뜻이다.")
            print("  이 패킷 전체를 처음부터 다시 번역해라. 부분 수정으로 맞추려 하지 마라.")
        print(f"\n=== 다음 작업 (재작업) ===")
        print(f"  입력: {pf.relative_to(KIT)}")
        print(f"  출력: {result_for(pf)}")
        print(f"\n{RULES}")
        return 0

    if not pending:
        print("\n=== 전량 통과 ===")
        print("  기계로 정렬 판정이 불가능한 소형 패킷은 사람이 직접 원문과 대조해라:")
        for stem in sorted(TOO_SMALL_TO_JUDGE):
            print(f"    {stem}  ->  {RESULTS / (stem + '.ko.jsonl')}")
        return 0

    pf = pending[0]
    n = len(json.loads(pf.read_text(encoding="utf-8"))["entries"])
    print(f"\n=== 다음 작업 ===")
    print(f"  입력: {pf.relative_to(KIT)}  ({n}행)")
    print(f"  출력: {result_for(pf)}")
    print(f"  남은 패킷: {len(pending)}")
    print(f"\n{RULES}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
