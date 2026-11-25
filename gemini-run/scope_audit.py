"""AG 가 열람 범위를 지켰는지 감사한다.

재사용은 유사도 통계로 추정할 수 있을 뿐이지만, 열람 범위는 사실로 확인된다.
AG 가 옛 번역 파일을 연 적이 없으면 베낄 방법이 없다. 이쪽이 결정적 검사다.
근거는 AG 자신의 보고가 아니라 런타임이 남긴 트랜스크립트다.
"""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BRAIN = Path.home() / ".gemini" / "antigravity" / "brain"
ALLOWED = re.compile(r"fault-stp-lightkravte-gemini-(scenario-kit|run|results)", re.I)
FORBIDDEN = re.compile(r"ko_map|_migrated|managed_ko|Korean_v1|release_build|localization[\/]build", re.I)
PATH_KEYS = ("AbsolutePath", "TargetFile", "FilePath", "file_path", "Path", "SearchDirectory")


def audit(conv_id: str):
    log = BRAIN / conv_id / ".system_generated" / "logs" / "transcript_full.jsonl"
    if not log.exists():
        return {"error": f"트랜스크립트 없음: {log}"}
    cmds, paths = [], []
    for line in log.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except Exception:
            continue
        for tc in (rec.get("tool_calls") or []):
            a = tc.get("args") or {}
            if a.get("CommandLine"):
                cmds.append(str(a["CommandLine"]))
            for k in PATH_KEYS:
                if a.get(k):
                    paths.append(str(a[k]))
    forbidden = [x for x in cmds + paths if FORBIDDEN.search(x)]
    outside = [x for x in paths if not ALLOWED.search(x)]
    return {"commands": len(cmds), "file_access": len(paths),
            "forbidden": forbidden, "outside": outside}


def main():
    ap = argparse.ArgumentParser(description="AG 열람 범위 감사")
    ap.add_argument("conversation_id")
    ns = ap.parse_args()
    r = audit(ns.conversation_id)
    if "error" in r:
        print(r["error"])
        return 1
    print(f"명령 {r['commands']}건 · 파일 접근 {r['file_access']}건")
    print(f"옛 번역 경로 접근: {len(r['forbidden'])}건")
    print(f"허용 폴더 밖 접근: {len(r['outside'])}건")
    for x in (r["forbidden"] + r["outside"])[:8]:
        print("  ", x[:150])
    return 2 if (r["forbidden"] or r["outside"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
