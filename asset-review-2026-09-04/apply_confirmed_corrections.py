from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


WORK = Path(r"P:\AI\Codex\projects\_migrated_c_documents_codex\2026-07-25\new-chat\work")
LOC = WORK / "localization"
TRANSLATIONS = LOC / "translations_ko"
CORRECTIONS = Path(r"P:\AI\Codex\projects\fault-stp-lightkravte-correction-list-2026-09-03\correction_candidates.json")
BACKUP = LOC / "backups" / "2026-09-04-confirmed-corrections"
REPORT = LOC / "reports" / "codex_confirmed_corrections_2026-09-04.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    text = "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows)
    path.write_text(text, encoding="utf-8")


def main() -> None:
    data = json.loads(CORRECTIONS.read_text(encoding="utf-8"))
    fixes = [row for row in data["records"] if row.get("status") == "fix"]
    if len(fixes) != 16:
        raise SystemExit(f"Expected 16 confirmed fixes, got {len(fixes)}")
    if any(not row.get("proposed_ko") for row in fixes):
        raise SystemExit("A confirmed fix is missing proposed_ko")

    uid_index: dict[str, tuple[Path, int, dict]] = {}
    duplicates: set[str] = set()
    for chapter in ("ch01", "ch02", "ch03"):
        for path in sorted((TRANSLATIONS / chapter).glob("*.jsonl")):
            for index, row in enumerate(read_jsonl(path)):
                uid = row.get("uid")
                if not uid:
                    raise SystemExit(f"Missing UID field: {path}:{index + 1}")
                if uid in uid_index:
                    duplicates.add(uid)
                uid_index[uid] = (path, index, row)
    if duplicates:
        raise SystemExit(f"Duplicate translation UIDs: {sorted(duplicates)[:10]}")

    touched: dict[Path, list[dict]] = {}
    log: list[dict] = []
    for fix in fixes:
        uid = fix["uid"]
        if uid not in uid_index:
            raise SystemExit(f"Missing UID: {uid}")
        path, index, indexed_row = uid_index[uid]
        rows = touched.setdefault(path, read_jsonl(path))
        current = rows[index].get("ko")
        expected = fix["existing"]
        proposed = fix["proposed_ko"]
        if current == proposed:
            state = "already_applied"
        elif current == expected:
            rows[index]["ko"] = proposed
            state = "applied"
        else:
            raise SystemExit(
                f"Refusing stale correction {uid}: current={current!r}, expected={expected!r}"
            )
        log.append(
            {
                "uid": uid,
                "file": str(path.relative_to(LOC)),
                "priority": fix.get("priority"),
                "category": fix.get("category"),
                "before": current,
                "after": proposed,
                "state": state,
            }
        )

    BACKUP.mkdir(parents=True, exist_ok=True)
    pre_hashes: dict[str, str] = {}
    post_hashes: dict[str, str] = {}
    for path, rows in sorted(touched.items()):
        rel = path.relative_to(LOC)
        dst = BACKUP / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if not dst.exists():
            shutil.copy2(path, dst)
        pre_hashes[str(rel)] = sha256(path)
        write_jsonl(path, rows)
        post_hashes[str(rel)] = sha256(path)

    build_map = LOC / "build" / "ko_map.json"
    if build_map.exists():
        dst = BACKUP / "build" / "ko_map.json"
        dst.parent.mkdir(parents=True, exist_ok=True)
        if not dst.exists():
            shutil.copy2(build_map, dst)

    report = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "translator_model": "Codex internal",
        "reviewer_model": "Codex internal",
        "thread_id": "019f98c4-2d2a-7502-b05c-6a79321fe89e",
        "source_list": str(CORRECTIONS),
        "scope": "Only records marked status=fix were applied; optional and hold records were not changed.",
        "confirmed_fix_count": len(fixes),
        "applied_count": sum(item["state"] == "applied" for item in log),
        "already_applied_count": sum(item["state"] == "already_applied" for item in log),
        "backup_root": str(BACKUP),
        "pre_hashes": pre_hashes,
        "post_hashes": post_hashes,
        "corrections": log,
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(REPORT), "count": len(log), "files": len(touched)}, ensure_ascii=False))


if __name__ == "__main__":
    main()

