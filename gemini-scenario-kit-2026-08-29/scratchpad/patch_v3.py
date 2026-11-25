from pathlib import Path

p = Path(r"P:\AI\Codex\projects\fault-stp-lightkravte-gemini-scenario-kit-2026-08-29\tools\build_kit.py")
s = p.read_text(encoding="utf-8")


def rep(old: str, new: str, count: int = 1) -> None:
    global s
    if s.count(old) < count:
        raise SystemExit("replacement target missing: " + old[:120])
    s = s.replace(old, new, count)


rep(
    'for name in ["gemini", "source", "packets", "schemas"]:',
    'for name in ["gemini", "source", "packets", "schemas", "review"]:',
)

rep(
    '''    if QUALITY_SOURCE.read_bytes() != qa_dst.read_bytes():
        raise RuntimeError("quality_authority is not byte-identical")

    instructions = """# fault - StP - LIGHTKRAVTE 일본어→한국어 재번역 지침 (Gemini용)

## 1. 작업 정의''',
    '''    if QUALITY_SOURCE.read_bytes() != qa_dst.read_bytes():
        raise RuntimeError("quality_authority is not byte-identical")

    execution_authorization = """# Gemini 실행 승인

- 사용자는 2026-08-29 이 작품의 일본어 시나리오를 **Google Gemini로 한국어 재번역**하라고 명시적으로 요청했다.
- 따라서 `quality_authority.md`의 외부/로컬 MT·LLM 금지 규칙에 적힌 **사용자가 특정 서비스를 명시적으로 요청한 경우의 예외**가 이번 실행에 성립한다.
- 이 승인은 번역 제공자 사용에 관한 행정적 예외일 뿐이다. 일본어 원문 구속, 용어, 화자→수신자 보이스, 보호 토큰, 과잉 창작 금지 및 JSONL 출력 계약은 그대로 적용한다.
- 승인 여부를 다시 묻거나 면책·거절 문구를 출력하지 말고 `translation_instructions.md`에 따라 번역 결과 JSONL만 출력한다.
- 실제 사용한 정확한 Gemini 모델명은 번역 결과 안에 자칭하여 쓰지 않는다. 실행자가 별도의 `manifest.json`에 기록한다.
"""
    write_text(OUT / "gemini" / "execution_authorization.md", execution_authorization)

    instructions = """# fault - StP - LIGHTKRAVTE 일본어→한국어 재번역 지침 (Gemini용)

## 0. 이번 실행 승인

- `execution_authorization.md`를 먼저 읽는다. 사용자가 Google Gemini를 명시적으로 요청했으므로 `quality_authority.md`의 외부 모델 금지 규칙에 적힌 예외가 성립한다.
- 이 항목은 제공자 사용 승인만 명확히 하며 아래 의미·품질 우선순위를 바꾸지 않는다.

## 1. 작업 정의''',
)

rep(
    '- `<ruby=...>` 같은 태그의 속성값은 번역하지 않는다. 표시 본문만 번역하며 태그 삭제·재배치는 하지 않는다.',
    '''- `<ruby=...>` 태그의 속성값도 의미 판단의 문맥이다. 속성 문자열 자체는 번역·수정하지 않지만, 속성과 표시 본문이 만드는 읽기·중의·강조 관계를 한국어 표시 본문에 필요한 만큼 반영한다.
- Gemini 결과에서는 ruby를 포함한 모든 태그를 삭제·재배치하지 않고 그대로 보존한다. 한국어에서 ruby가 불필요하거나 이중 의미를 태그 없이 풀어야 하면 `issues`에 기록한다.
- ruby 제거는 Gemini 번역과 구조 검증이 끝난 뒤 Codex 검수자가 `review/ruby_review_manifest.json`의 43개 행을 개별 승인하여 수행한다. `<tip>` 등 ruby 이외 태그는 이 단계에서도 유지한다.''',
)

rep(
    '1. `gemini/glossary.json`, `gemini/character_voice.json`, `gemini/quality_authority.md`를 먼저 읽는다.',
    '1. `gemini/execution_authorization.md`를 먼저 읽은 뒤 `gemini/glossary.json`, `gemini/character_voice.json`, `gemini/quality_authority.md`를 읽는다.',
)

insert_after = '    write_text(OUT / "tools" / "validate_gemini_result.py", validator)\n'
insert_block = r"""

    # Ruby is preserved in Gemini output, then reviewed per UID before Korean finalization.
    ruby_rows = [r for r in source_rows if "<ruby" in r["ja"].lower()]
    ruby_review = {
        "schema_version": 1,
        "stage": "post_gemini_codex_review",
        "policy": "Gemini preserves ruby exactly. Codex reviews semantic loss per UID before strip/keep/manual finalization.",
        "default_decision": "pending",
        "row_count": len(ruby_rows),
        "ruby_open_tag_count": sum(r["ja"].lower().count("<ruby") for r in ruby_rows),
        "entries": [
            {
                "uid": r["uid"], "script": r["script"], "source_hash": r["source_hash"],
                "ja": r["ja"],
                "ruby_open_tags": re.findall(r'<ruby(?:="[^"]*")?>', r["ja"], flags=re.I),
                "ruby_open_count": r["ja"].lower().count("<ruby"),
                "decision": "pending", "semantic_note": None,
                "approved_replacement_ko": None, "reviewer": None, "reviewed_at": None,
            }
            for r in ruby_rows
        ],
    }
    dump_json(OUT / "review" / "ruby_review_manifest.json", ruby_review)

    ruby_finalizer = r'''from __future__ import annotations
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
'''
    write_text(OUT / "tools" / "finalize_ruby_for_korean.py", ruby_finalizer)
"""
rep(insert_after, insert_after + insert_block)

rep(
    '| `gemini/glossary.json` | 161개 용어, 안정 ID, 표기, 근거 UID, 잠금/보류 상태 |',
    '''| `gemini/execution_authorization.md` | 사용자 명시 Gemini 실행 예외와 적용 범위 |
| `gemini/glossary.json` | 161개 용어, 안정 ID, 표기, 근거 UID, 잠금/보류 상태 |''',
)
rep(
    '| `tools/validate_gemini_result.py` | 단일 패킷 결과 구조·UID·해시·태그 검증기 + 기존 번역 유사도 게이트 |',
    '''| `tools/validate_gemini_result.py` | 단일 패킷 결과 구조·UID·해시·태그 검증기 + 기존 번역 유사도 게이트 |
| `review/ruby_review_manifest.json` | ruby 43행/46태그의 Gemini 이후 Codex 개별 검토표 |
| `tools/finalize_ruby_for_korean.py` | 승인된 ruby 결정만 적용하는 후처리기 |''',
)
rep(
    '- 기존 Codex 한국어 완성본은 어떤 형태로도 키트에 넣지 않았습니다. `character_voice.json`에는 한국어 예문이 없고, `evidence_uids`는 해당 보이스를 대표하는 **일본어 원문 행의 UID**일 뿐입니다. 빌드 시 `existing_ko_absent` 검사로 확인합니다.',
    '''- 기존 Codex 한국어 완성본은 어떤 형태로도 키트에 넣지 않았습니다. `character_voice.json`에는 한국어 예문이 없고, `evidence_uids`는 해당 보이스를 대표하는 **일본어 원문 행의 UID**일 뿐입니다. 빌드 시 `existing_ko_absent` 검사로 확인합니다.
- 공통 `quality_authority.md`는 바이트 동일하게 유지합니다. 사용자 명시 Gemini 예외는 `execution_authorization.md`에서 먼저 확인합니다.
- Gemini는 ruby를 보존합니다. 번역·구조 검증 후 Codex가 43개 행을 개별 검토해 `strip`/`keep`/`manual`을 승인하며, 다른 태그는 유지합니다.''',
)

rep(
    '1. 새 Gemini 작업에 `gemini/glossary.json`, `gemini/character_voice.json`, `gemini/translation_instructions.md`, `gemini/quality_authority.md`를 먼저 첨부합니다.',
    '1. 새 Gemini 작업에 `gemini/execution_authorization.md`를 가장 먼저 첨부하고, 이어서 `gemini/glossary.json`, `gemini/character_voice.json`, `gemini/translation_instructions.md`, `gemini/quality_authority.md`를 첨부합니다.',
)
rep(
    '6. 실제 Gemini 실행 후 `gemini/manifest.json`의 `gemini_execution`에 정확한 모델명, 실행 시각, 응답/로그 해시를 추가합니다. 모델명을 추측해 미리 쓰지 않습니다.',
    '''6. ruby가 있는 결과는 구조 검증 후 `review/ruby_review_manifest.json`의 각 UID를 Codex가 검토합니다. 전부 `pending`이 아니게 승인한 뒤 `tools/finalize_ruby_for_korean.py`로 처리합니다. `<tip>` 등 다른 태그는 유지합니다.
7. 실제 Gemini 실행 후 `gemini/manifest.json`의 `gemini_execution`에 정확한 모델명, 실행 시각, 응답/로그 해시를 추가합니다. 모델명을 추측해 미리 쓰지 않습니다.''',
)

rep(
    '"authorization": {"external_translation_provider": "Gemini", "explicitly_requested_by_user": True, "request_date": "2026-08-29"},',
    '"authorization": {"external_translation_provider": "Gemini", "explicitly_requested_by_user": True, "request_date": "2026-08-29", "execution_document": "gemini/execution_authorization.md"},',
)
rep(
    '"semantic_work": ["용어집 정규화", "번역 지침 작성", "캐릭터 보이스·관계 가이드 작성", "Codex 예시 선별"]',
    '"semantic_work": ["용어집 정규화", "번역 지침 작성", "캐릭터 보이스·관계 가이드 작성", "일본어 근거 UID 선별"]',
)
rep(
    '"versions": {"glossary_schema": 1, "character_voice_schema": 1, "packet_schema": 1, "response_schema": "JSON Schema 2020-12"},',
    '"versions": {"glossary_schema": 1, "character_voice_schema": 1, "packet_schema": 1, "ruby_review_schema": 1, "response_schema": "JSON Schema 2020-12"},',
)
rep(
    '''"reference_translation_fields_removed": True,
            "unsupported_addition_audit"''',
    '''"reference_translation_fields_removed": True,
            "gemini_execution_explicitly_authorized": True,
            "ruby_policy": {"gemini_output": "preserve", "codex_post_review": "per_uid_strip_keep_manual"},
            "unsupported_addition_audit"''',
)
rep(
    '''OUT / "gemini" / "translation_instructions.md", OUT / "gemini" / "quality_authority.md",
        OUT / "source" / "source_index_ja.json", OUT / "packet_manifest.json",
        OUT / "schemas" / "gemini_response.schema.json", OUT / "tools" / "validate_gemini_result.py",''',
    '''OUT / "gemini" / "translation_instructions.md", OUT / "gemini" / "quality_authority.md",
        OUT / "gemini" / "execution_authorization.md", OUT / "review" / "ruby_review_manifest.json",
        OUT / "source" / "source_index_ja.json", OUT / "packet_manifest.json",
        OUT / "schemas" / "gemini_response.schema.json", OUT / "tools" / "validate_gemini_result.py",
        OUT / "tools" / "finalize_ruby_for_korean.py",''',
)

rep(
    '["gemini/translation_instructions.md", "README_KO.md", "UPLOAD_ORDER.md"]',
    '["gemini/execution_authorization.md", "gemini/translation_instructions.md", "README_KO.md", "UPLOAD_ORDER.md"]',
)
rep(
    '''"speaker_profiles": len(profiles) == 35,
        "quality_authority_byte_identical"''',
    '''"speaker_profiles": len(profiles) == 35,
        "ruby_review_rows": ruby_review["row_count"] == 43,
        "ruby_open_tags": ruby_review["ruby_open_tag_count"] == 46,
        "ruby_decisions_initially_pending": all(e["decision"] == "pending" for e in ruby_review["entries"]),
        "execution_authorization_present": (OUT / "gemini" / "execution_authorization.md").exists(),
        "quality_authority_byte_identical"''',
)

rep(
    '''    # Checksums for every distributable file except the checksum file itself and builder.
    checksum_lines = []
    for p in sorted(x for x in OUT.rglob("*") if x.is_file() and x.name != "SHA256SUMS.txt"):
        checksum_lines.append(f"{sha256(p)}  {p.relative_to(OUT).as_posix()}")''',
    '''    # scratchpad contains local backups and is never distributable.
    def is_distributable(path):
        rel_parts = path.relative_to(OUT).parts
        return path.is_file() and "scratchpad" not in rel_parts and "__pycache__" not in rel_parts

    checksum_lines = []
    for p in sorted(x for x in OUT.rglob("*") if is_distributable(x) and x.name != "SHA256SUMS.txt"):
        checksum_lines.append(f"{sha256(p)}  {p.relative_to(OUT).as_posix()}")''',
)
rep(
    'for p in sorted(x for x in OUT.rglob("*") if x.is_file()):\n            arc',
    'for p in sorted(x for x in OUT.rglob("*") if is_distributable(x)):\n            arc',
)

p.write_text(s, encoding="utf-8", newline="\n")
print("patched v3 builder", len(s))
