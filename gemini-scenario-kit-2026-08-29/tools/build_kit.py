from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path


SOURCE_ROOT = Path(r"P:\AI\Codex\projects\_migrated_c_documents_codex\2026-07-25\new-chat\work")
OUT = Path(r"P:\AI\Codex\projects\fault-stp-lightkravte-gemini-scenario-kit-2026-08-29")
ZIP_PATH = OUT.with_suffix(".zip")
QUALITY_SOURCE = Path(r"P:\AI\Codex\skills\contextual-game-localization\references\translation-quality.md")
NOW = datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")
THREAD_ID = "019f98c4-2d2a-7502-b05c-6a79321fe89e"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8", newline="\n")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def normalized_pos(category: str) -> str:
    if category in {"character", "character_full", "place", "geography", "institution", "organization", "publication"}:
        return "proper_noun"
    if category in {"rank", "display_role", "family", "social"}:
        return "title_or_role"
    return "noun"


def runtime_function(category: str) -> str:
    return {
        "character": "대사·이름표에 쓰이는 인물명",
        "character_full": "인물의 풀네임",
        "display_role": "이름표 또는 화자 역할명",
        "place": "장소·시설명",
        "geography": "지리·국가·지역명",
        "institution": "기관명",
        "organization": "조직명",
        "rank": "직위·호칭",
        "mana": "마나크래프트 체계 용어",
        "kravte": "크라프트·유리 공예 체계 용어",
        "optics": "광학·시각 현상 용어",
        "sense": "감각·인지 관련 설정 용어",
        "vehicle": "이동 수단명",
        "creature": "생물명",
        "food": "음식명",
        "item": "물품명",
        "publication": "서적·간행물명",
        "culture": "문화·관습 용어",
        "family": "가족 관계 호칭",
        "social": "사회 관계·계층 용어",
    }.get(category, "작중 고유 용어")


RELATIONS = {
    "kaj": [
        {"addressee": "self_or_reader", "group": "독백·서술", "level": "해라체/내적 구어", "address": [], "first": ["나"], "second": [], "endings": ["-다", "-지", "-나"], "rhythm": "짧고 주저하는 호흡. 원문에 있는 말더듬과 망설임만 자연스럽게 재현.", "warmth": "내향적·자기검열", "command": "낮음", "variants": {"panic": "문장을 짧게 끊되 의미를 추가하지 않는다.", "confidence": "성장 국면에서도 과장된 영웅 말투를 피한다."}},
        {"addressee": "flo", "group": "플로라", "level": "존댓말", "address": ["플로라 님"], "first": ["저"], "second": ["플로라 님"], "endings": ["-요", "-습니다"], "rhythm": "친밀하지만 공손하고 다소 서툰 말투.", "warmth": "높음", "command": "낮음", "variants": {"panic": "더듬음 허용", "serious": "간결한 존댓말"}},
        {"addressee": "sel", "group": "왕족", "level": "높임말", "address": ["셀피네 공주님", "전하"], "first": ["저"], "second": ["공주님", "전하"], "endings": ["-습니다", "-십니까", "-요"], "rhythm": "격식을 우선하고 긴장감을 원문만큼만 반영.", "warmth": "존경", "command": "매우 낮음", "variants": {"private": "상황이 허락해도 기본 높임을 유지"}},
        {"addressee": "oug", "group": "부친", "level": "가족 간 반말", "address": ["아버지"], "first": ["나"], "second": ["아버지"], "endings": ["-어", "-잖아", "-지"], "rhythm": "주눅 들거나 반발하는 아들 말투.", "warmth": "복합적", "command": "낮음", "variants": {"conflict": "반발은 가능하나 모욕 어휘를 임의로 세게 만들지 않는다."}},
        {"addressee": "elders_and_craftsmen", "group": "켄드리드·리그스·유리 장인·연장자", "level": "존댓말", "address": ["선생님", "어르신", "이름+님(원문 근거 시)"], "first": ["저"], "second": [], "endings": ["-요", "-습니다"], "rhythm": "질문과 사과가 많은 공손한 말투.", "warmth": "존중", "command": "낮음", "variants": {"urgent": "급박해도 반말로 바꾸지 않는다."}},
        {"addressee": "peers", "group": "리토나·미샤·소네타 등 또래/지인", "level": "관계별 존댓말 우선", "address": ["이름+씨/님(원문 관계에 따름)"], "first": ["저", "나"], "second": [], "endings": ["-요", "-어"], "rhythm": "장면의 기존 관계와 직전 호칭을 우선한다.", "warmth": "중립~친근", "command": "낮음", "variants": {"uncertain": "반말/존댓말이 모호하면 존댓말 쪽으로 보수적으로 처리하고 issues에 기록."}},
    ],
    "<narration>": [
        {"addressee": "reader", "group": "서술·카지 내면", "level": "담백한 해라체", "address": [], "first": ["나"], "second": [], "endings": ["-다", "-었다"], "rhythm": "원문의 관찰 순서와 정보량을 지키는 자연스러운 한국어 문장.", "warmth": "중립", "command": "없음", "variants": {"lyrical": "원문에 없는 분위기·심리·수식어를 보태지 않는다."}},
    ],
    "flo": [
        {"addressee": "kaj", "group": "카지", "level": "친근한 반말", "address": ["카지 군"], "first": ["나"], "second": ["카지 군", "너"], "endings": ["-어", "-지", "-니?"], "rhythm": "밝고 솔직하며 템포가 빠르다.", "warmth": "높음", "command": "낮음~중간", "variants": {"public": "공적인 자리에서는 존댓말 전환 가능", "worry": "다정함을 유지하되 감정을 원문보다 키우지 않는다."}},
        {"addressee": "royalty_or_public", "group": "왕족·공적 상대", "level": "존댓말", "address": ["공주님", "이름+님"], "first": ["저"], "second": [], "endings": ["-요", "-습니다"], "rhythm": "밝음을 유지한 공손한 말투.", "warmth": "예의 바름", "command": "낮음", "variants": {}},
    ],
    "rit": [
        {"addressee": "kaj", "group": "카지", "level": "거친 반말", "address": ["카지"], "first": ["나"], "second": ["너"], "endings": ["-어", "-지", "-냐"], "rhythm": "짧고 직설적. 욕설과 공격성은 원문 강도 이상으로 올리지 않는다.", "warmth": "낮음~숨은 배려", "command": "중간", "variants": {"protective": "배려를 설명문처럼 덧붙이지 않고 행동/대사에 드러난 만큼만 번역."}},
        {"addressee": "son", "group": "소네타", "level": "반말", "address": ["소네타"], "first": ["나"], "second": ["너"], "endings": ["-어", "-지", "-냐"], "rhythm": "‘선배’ 호칭을 귀찮아하거나 제지하는 날카로운 템포.", "warmth": "낮음", "command": "중간", "variants": {}},
        {"addressee": "sel", "group": "왕족", "level": "절제된 존댓말", "address": ["공주님", "전하"], "first": ["저"], "second": [], "endings": ["-습니다", "-습니까"], "rhythm": "무뚝뚝하되 예법은 지킨다.", "warmth": "절제", "command": "낮음", "variants": {}},
    ],
    "oug": [
        {"addressee": "kaj", "group": "아들 카지", "level": "거친 반말", "address": ["카지", "녀석"], "first": ["나"], "second": ["너"], "endings": ["-다", "-냐", "-해"], "rhythm": "권위적이고 직설적인 아버지 말투.", "warmth": "낮음~내재", "command": "높음", "variants": {"anger": "욕설·모욕은 원문 범위를 넘기지 않는다."}},
        {"addressee": "adult_peers", "group": "동료 장인·성인", "level": "거친 반말 또는 해라체", "address": [], "first": ["나"], "second": ["자네", "너"], "endings": ["-다", "-지"], "rhythm": "단정적이고 현실적.", "warmth": "중립", "command": "중간", "variants": {}},
    ],
    "mis": [{"addressee": "kaj_and_peers", "group": "카지·또래", "level": "남성적인 반말", "address": ["카지"], "first": ["나"], "second": ["너"], "endings": ["-어", "-냐", "-지"], "rhythm": "거칠고 활달하되 원문에 없는 욕설을 넣지 않는다.", "warmth": "친근", "command": "중간", "variants": {}}],
    "son": [
        {"addressee": "kaj", "group": "카지", "level": "친근한 존댓말", "address": ["카지 씨"], "first": ["미치", "저"], "second": ["카지 씨"], "endings": ["-요", "-죠"], "rhythm": "발랄하고 장난스럽다. 자기 지칭 ‘미치’는 원문 용례에 맞춰 유지.", "warmth": "높음", "command": "낮음", "variants": {}},
        {"addressee": "rit", "group": "리토나", "level": "존댓말", "address": ["리토나 선배"], "first": ["미치", "저"], "second": ["리토나 선배"], "endings": ["-요", "-죠"], "rhythm": "상대가 싫어해도 ‘선배’ 호칭을 쓰는 장난기.", "warmth": "높음", "command": "낮음", "variants": {}},
    ],
    "ken": [{"addressee": "kaj_or_juniors", "group": "카지·후배", "level": "연장자의 거친 반말", "address": ["카지", "애송이(원문 근거 시)"], "first": ["나"], "second": ["너"], "endings": ["-다", "-냐", "-해라"], "rhythm": "짧고 퉁명스럽고 단정적.", "warmth": "낮음", "command": "높음", "variants": {}}],
    "rig": [{"addressee": "kaj_or_juniors", "group": "카지·후배", "level": "차분한 하대", "address": ["카지 군", "자네"], "first": ["나"], "second": ["자네"], "endings": ["-군", "-지", "-다"], "rhythm": "이성적이고 설명적이며 감정 과장을 피한다.", "warmth": "중립", "command": "중간", "variants": {}}],
    "sel": [
        {"addressee": "citizens_or_audience", "group": "백성·공적 청중", "level": "군주다운 격식체", "address": ["여러분", "그대들(원문 근거 시)"], "first": ["저", "짐(원문 근거 시)"], "second": [], "endings": ["-습니다", "-십시오"], "rhythm": "우아하고 또렷하며 공적 책임감이 드러난다.", "warmth": "절제", "command": "중간~높음", "variants": {"monarch": "위엄을 강화하되 고어체를 임의로 만들지 않는다."}},
        {"addressee": "trusted_companions", "group": "측근·동행", "level": "품위 있는 존댓말", "address": ["이름+님/씨(원문에 따름)"], "first": ["저"], "second": [], "endings": ["-요", "-습니다"], "rhythm": "사적인 온기를 조금 보이되 왕족의 품위를 유지.", "warmth": "중간", "command": "낮음", "variants": {}},
    ],
    "qla": [{"addressee": "kaj", "group": "카지", "level": "친근한 반말", "address": ["카지 오빠"], "first": ["나"], "second": ["오빠"], "endings": ["-어", "-지", "-지?"], "rhythm": "어리고 솔직한 호흡.", "warmth": "높음", "command": "낮음", "variants": {}}],
    "mer": [{"addressee": "kaj", "group": "카지", "level": "가까운 연장자의 반말", "address": ["카지야"], "first": ["나"], "second": ["카지", "너"], "endings": ["-어", "-렴", "-구나"], "rhythm": "부드럽고 돌보는 듯한 말투.", "warmth": "높음", "command": "낮음~중간", "variants": {}}],
    "cer": [{"addressee": "interlocutor", "group": "대화 상대", "level": "우아한 존댓말", "address": [], "first": ["저"], "second": [], "endings": ["-군요", "-겠어요", "-랍니다"], "rhythm": "세련되고 불길한 여운. 원문에 없는 시적 수식은 금지.", "warmth": "표면상 친절", "command": "낮음", "variants": {"menace": "위협을 노골적인 욕설로 바꾸지 않는다."}}],
}


ADDRESSEE_JA_HINTS = {
    "kaj": ["カージ"], "flo": ["フローラ"], "rit": ["リトナ"], "oug": ["オーグス", "親父", "父さん"],
    "mis": ["ミシャ"], "son": ["ソネッタ"], "ken": ["ケンドリッド"], "rig": ["リグス"],
    "sel": ["セルフィーネ", "姫", "殿下"], "qla": ["クァラ"], "mer": ["メルリサ"], "cer": ["セラロ"],
}

ROLE_DEFAULTS = {
    "adi": ("동료 또는 지인", "장면 관계에 맞는 자연스러운 구어체"),
    "ban": ("고객·다른 장인", "성인 남성 장인의 현장 말투"),
    "dil": ("장면 상대", "원문의 거리감을 보존하는 자연스러운 구어체"),
    "tos": ("장면 상대", "원문의 태도와 위계를 우선"),
    "gla": ("고객·다른 장인", "장인의 실무적 말투"),
    "old": ("젊은이·다른 장인", "연배 있는 장인의 말투"),
    "mil": ("장면 상대", "원문의 연령과 관계를 보수적으로 반영"),
    "jil": ("장면 상대", "원문의 연령과 관계를 보수적으로 반영"),
    "???": ("미상 상대", "화자와 수신자를 확정하지 말고 중립 문장 사용"),
    "mel": ("카지·주변 인물", "보호자/연장자 맥락의 차분한 말투"),
    "red": ("장면 상대", "신원이 확정되기 전 고유 보이스를 임의 부여하지 않음"),
    "gua2": ("시민·방문객", "직무상 공손하거나 명령적인 말투"),
    "mobf1": ("방문객", "접수 업무의 공손한 존댓말"),
    "gua": ("시민·방문객", "경비 업무의 간결한 존댓말/명령체"),
    "coo": ("손님·동료", "요리사의 실무적이고 친근한 말투"),
    "fha": ("장면 상대", "원문의 위계·관계를 우선"),
    "girl": ("카지·어른", "어린 소녀의 자연스러운 말투; 과도한 유아어 금지"),
    "mhi": ("장면 상대", "원문의 관계를 우선"),
    "医療班": ("환자·동료", "의료진의 침착하고 명료한 존댓말"),
    "ruk": ("장면 상대", "원문의 관계를 우선"),
    "wig": ("장면 상대", "원문의 위계와 감정 강도를 우선"),
}


def build() -> None:
    loc = SOURCE_ROOT / "localization"
    source_rows = read_json(loc / "source_index.json")
    terminology = read_json(loc / "terminology.json")
    ko_map = read_json(loc / "build" / "ko_map.json")
    old_manifest = read_json(loc / "packet_manifest.json")
    by_script = defaultdict(list)
    for row in source_rows:
        by_script[row["script"]].append(row)
    for rows in by_script.values():
        rows.sort(key=lambda x: x["sequence"])

    # Rebuild only generated areas, leaving this builder in tools/.
    for name in ["gemini", "source", "packets", "schemas", "review"]:
        p = OUT / name
        if p.exists():
            shutil.rmtree(p)
    for name in ["README_KO.md", "UPLOAD_ORDER.md", "packet_manifest.json", "SHA256SUMS.txt", "VALIDATION_REPORT.json", "test.txt"]:
        p = OUT / name
        if p.exists():
            p.unlink()
    pycache = OUT / "tools" / "__pycache__"
    if pycache.exists():
        shutil.rmtree(pycache)

    # Canonical, byte-identical Japanese scenario catalogs (PrintText and commands).
    catalog_src = SOURCE_ROOT / "script_audit" / "catalogs" / "ja"
    catalog_dst = OUT / "source" / "original_ja_catalogs"
    catalog_dst.mkdir(parents=True, exist_ok=True)
    scenario_scripts = sorted(by_script)
    catalog_hashes = {}
    for script in scenario_scripts:
        src = catalog_src / f"{script}.json"
        if not src.exists():
            raise FileNotFoundError(src)
        dst = catalog_dst / src.name
        shutil.copyfile(src, dst)
        if src.read_bytes() != dst.read_bytes():
            raise RuntimeError(f"byte copy mismatch: {script}")
        catalog_hashes[src.name] = sha256(dst)

    # JA-only source index, deliberately excluding English/Chinese references.
    ja_index = []
    for row in source_rows:
        ja_index.append({
            "uid": row["uid"], "script": row["script"], "sequence": row["sequence"],
            "source_line": row["source_line"], "source_hash": row["source_hash"],
            "speaker_id": row["speaker_id"], "printer_id": row["printer_id"],
            "voice_id": row["voice_id"], "ja": row["ja"],
            "required_tokens": row.get("required_tokens", []),
        })
    dump_json(OUT / "source" / "source_index_ja.json", ja_index)
    write_text(OUT / "source" / "README.md", """# 원본 일본어 시나리오

- `original_ja_catalogs/`: 46개 시나리오 카탈로그의 바이트 동일 복사본입니다. 명령·메타데이터를 포함한 원본 근거용이며 직접 수정하지 않습니다.
- `source_index_ja.json`: 실제 번역 소유권을 갖는 6,746개 표시 문자열의 JA 전용 안정 ID 인덱스입니다.
- `Init.json`, `Title.json`은 표시 시나리오 엔트리가 0개이므로 범위에서 제외했습니다.
- 영어·중국어 참조문은 오염 방지를 위해 키트에 넣지 않았습니다. 의미 판단의 유일한 원문은 일본어입니다.
""")

    # Glossary.
    evidence_by_term = {}
    for idx, term in enumerate(terminology["entries"], 1):
        needle = term["ja"]
        evidence = [r["uid"] for r in source_rows if needle and needle in r["ja"]][:8]
        evidence_by_term[idx] = evidence
    glossary_entries = []
    for idx, term in enumerate(terminology["entries"], 1):
        evidence = evidence_by_term[idx]
        pending = (not evidence) or ("확인" in term.get("note", "") and "실제" in term.get("note", ""))
        glossary_entries.append({
            "term_id": f"TERM-{idx:04d}",
            "source": term["ja"],
            "target": term["ko"],
            "category": term["category"],
            "part_of_speech": normalized_pos(term["category"]),
            "canonical_spelling": term["ko"],
            "meaning_and_runtime_use": (term.get("note") or runtime_function(term["category"])),
            "runtime_function": runtime_function(term["category"]),
            "allowed_variants": [],
            "forbidden_or_deprecated": ([term.get("en_reference")] if term.get("en_reference") else []),
            "evidence_uids": evidence,
            "status": "pending" if pending else "locked",
            "pending_reason": "원문 표시 근거 또는 실제 표시 확인이 더 필요함" if pending else None,
        })
    glossary = {
        "schema_version": 1,
        "work_id": "fault-stp-lightkravte-ja-ko-gemini-retranslation",
        "source_locale": "ja",
        "target_locale": "ko",
        "semantic_authority": "Japanese source only",
        "preparation_model": "Codex internal (GPT-5.5 runtime)",
        "precedence": "locked 항목은 반드시 따르고 pending 항목은 추정 확정하지 말고 issues에 기록",
        "entries": glossary_entries,
    }
    dump_json(OUT / "gemini" / "glossary.json", glossary)

    # Voice evidence: UID pointers into the JA source only. No existing Korean enters the kit.
    rows_by_speaker = defaultdict(list)
    for row in source_rows:
        sid = row["speaker_id"] or "<narration>"
        rows_by_speaker[sid].append(row)

    def samples(sid: str, limit: int = 3):
        candidates = rows_by_speaker.get(sid, [])
        picks = []
        seen = set()
        for row in candidates:
            if len(picks) >= limit:
                break
            ja = row["ja"]
            if ja in seen or len(re.sub(r"<[^>]+>", "", ja)) < 4:
                continue
            seen.add(ja)
            picks.append({"uid": row["uid"], "ja": ja})
        return picks

    def relationship_samples(sid: str, addressee: str, fallback, limit: int = 3):
        hints = ADDRESSEE_JA_HINTS.get(addressee, [])
        picks = []
        if hints:
            for row in rows_by_speaker.get(sid, []):
                if not any(h in row["ja"] for h in hints):
                    continue
                picks.append({"uid": row["uid"], "ja": row["ja"]})
                if len(picks) >= limit:
                    break
        return (picks, "relationship_name_or_addressing") if picks else (fallback[:limit], "speaker_style_fallback")

    profiles = []
    for sp in terminology["speakers"]:
        sid = sp["id"]
        rels = RELATIONS.get(sid)
        status = "locked"
        if rels is None:
            group, desc = ROLE_DEFAULTS.get(sid, ("장면 상대", "원문의 위계와 관계를 우선"))
            rels = [{
                "addressee": "context_resolved_interlocutor", "group": group,
                "speech_level": "장면 문맥에서 판정", "address_terms": [],
                "first_person": [], "second_person": [], "preferred_endings": [],
                "rhythm": desc, "warmth": "원문 준거", "command_strength": "원문 준거",
                "emotional_variants": {"uncertain": "보수적으로 중립 처리하고 issues에 기록"},
                "status": "pending",
            }]
            status = "pending"
        normalized_rels = []
        for rel in rels:
            if "speech_level" in rel:
                normalized_rels.append(rel)
            else:
                normalized_rels.append({
                    "addressee": rel["addressee"], "group": rel["group"],
                    "speech_level": rel["level"], "address_terms": rel["address"],
                    "first_person": rel["first"], "second_person": rel["second"],
                    "preferred_endings": rel["endings"], "rhythm": rel["rhythm"],
                    "warmth": rel["warmth"], "command_strength": rel["command"],
                    "emotional_variants": rel["variants"], "status": "locked",
                })
        ev = samples(sid)
        for relation in normalized_rels:
            rel_examples, evidence_scope = relationship_samples(sid, relation["addressee"], ev)
            relation["evidence_uids"] = [x["uid"] for x in rel_examples]
            relation["evidence_scope"] = evidence_scope
        profiles.append({
            "speaker_id": sid, "display_name": sp["name"], "source_line_count": sp["count"],
            "baseline_voice": sp["voice"], "baseline_rules": sp["rules"],
            "directed_relationships": normalized_rels,
            "plot_phase_changes": [{"phase": "ch01-ch03", "rule": "변화는 해당 패킷의 원문 근거와 직전 대화에서 확인될 때만 적용"}],
            "prohibited_carryover": [
                "다른 수신자에게 쓰는 호칭·존대 단계를 자동 전이하지 않는다.",
                "감정 장면의 거친 어조를 평상 장면으로 전이하지 않는다.",
                "정체가 숨겨진 화자에게 후반부 정체의 말버릇을 선행 노출하지 않는다.",
            ],
            "evidence_uids": [x["uid"] for x in ev],
            "status": status,
        })
    voice = {
        "schema_version": 1,
        "work_id": "fault-stp-lightkravte-ja-ko-gemini-retranslation",
        "preparation_model": "Codex internal (GPT-5.5 runtime)",
        "use_rule": "현재 화자와 실제 수신자의 directed_relationships를 우선한다. 수신자가 모호하면 직전/직후 문맥으로 판정하고 확정 불가 시 issues에 기록한다.",
        "global_prohibitions": [
            "화자 전체의 말투를 모든 상대에게 복사하지 않는다.",
            "3인 이상 대화에서 직전 화자를 수신자로 자동 가정하지 않는다.",
            "원문에 없는 성격·심리·친밀도·적대감을 새로 만들지 않는다.",
        ],
        "profiles": profiles,
    }
    dump_json(OUT / "gemini" / "character_voice.json", voice)

    # Packet construction from the original 100-row ownership chunks.
    speaker_name = {x["id"]: x["name"] for x in terminology["speakers"]}
    packet_records = []
    uid_owners = {}
    scripts_manifest = []
    for script_meta in old_manifest["scripts"]:
        script = script_meta["script"]
        if script not in by_script:
            continue
        rows = by_script[script]
        pos = {r["uid"]: i for i, r in enumerate(rows)}
        chapter = script[:4]
        out_chunks = []
        for chunk in script_meta["chunks"]:
            src_packet = loc / chunk["file"]
            owned = [json.loads(line) for line in src_packet.read_text(encoding="utf-8").splitlines() if line.strip()]
            first_i, last_i = pos[owned[0]["uid"]], pos[owned[-1]["uid"]]
            before = rows[max(0, first_i - 5):first_i]
            after = rows[last_i + 1:last_i + 6]
            entries = []
            for row in owned:
                uid = row["uid"]
                if uid in uid_owners:
                    raise RuntimeError(f"duplicate owner: {uid}")
                uid_owners[uid] = chunk["file"]
                entries.append({
                    "uid": uid, "source_hash": row["source_hash"], "sequence": row["sequence"],
                    "source_line": row["source_line"], "speaker_id": row["speaker_id"],
                    "speaker_name": speaker_name.get(row["speaker_id"], "서술/미지정" if not row["speaker_id"] else row["speaker_id"]),
                    "voice_id": row["voice_id"], "ja": row["ja"],
                    "required_tokens": row.get("required_tokens", []), "target_ko": "",
                })
            def ctx_item(r):
                return {"uid": r["uid"], "speaker_id": r["speaker_id"], "speaker_name": speaker_name.get(r["speaker_id"], "서술/미지정"), "ja": r["ja"], "do_not_translate": True}
            packet_id = Path(chunk["file"]).stem
            packet = {
                "schema_version": 1, "packet_id": packet_id, "script": script,
                "chapter": chapter, "story_phase": {"ch01": "도입·관계 형성", "ch02": "전개·갈등 심화", "ch03": "후반·위기와 결말"}.get(chapter, "미상"),
                "semantic_source": "ja", "target_locale": "ko",
                "instructions": "entries만 번역하고 boundary_context는 문맥 참조만 한다. 결과는 gemini_response.schema.json의 JSONL 형식으로 낸다.",
                "boundary_context": {"before": [ctx_item(r) for r in before], "after": [ctx_item(r) for r in after]},
                "entries": entries,
            }
            out_rel = Path("packets") / chapter / f"{packet_id}.json"
            dump_json(OUT / out_rel, packet)
            ph = sha256(OUT / out_rel)
            packet_records.append({"packet_id": packet_id, "file": out_rel.as_posix(), "script": script, "entries": len(entries), "first_uid": entries[0]["uid"], "last_uid": entries[-1]["uid"], "sha256": ph})
            out_chunks.append(packet_records[-1])
        scripts_manifest.append({"script": script, "chapter": chapter, "entries": len(rows), "source_catalog": f"source/original_ja_catalogs/{script}.json", "source_catalog_sha256": catalog_hashes[f"{script}.json"], "packets": out_chunks})
    if set(uid_owners) != {r["uid"] for r in source_rows}:
        missing = {r["uid"] for r in source_rows} - set(uid_owners)
        raise RuntimeError(f"packet ownership mismatch, missing={len(missing)}")

    packet_manifest = {
        "schema_version": 1, "created_at": NOW, "semantic_source": "ja", "target": "ko",
        "entry_count": len(source_rows), "script_count": len(by_script), "packet_count": len(packet_records),
        "ownership_rule": "각 uid는 정확히 한 패킷의 entries에만 속한다. boundary_context는 번역·출력 금지.",
        "packets": packet_records, "scripts": scripts_manifest,
    }
    dump_json(OUT / "packet_manifest.json", packet_manifest)

    response_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Gemini Korean translation JSONL record",
        "type": "object", "additionalProperties": False,
        "required": ["uid", "source_hash", "target_ko", "issues"],
        "properties": {
            "uid": {"type": "string"}, "source_hash": {"type": "string"},
            "target_ko": {"type": "string", "minLength": 1},
            "issues": {"type": "array", "items": {"type": "string"}},
        },
    }
    dump_json(OUT / "schemas" / "gemini_response.schema.json", response_schema)

    # Exact common quality authority.
    qa_dst = OUT / "gemini" / "quality_authority.md"
    qa_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(QUALITY_SOURCE, qa_dst)
    if QUALITY_SOURCE.read_bytes() != qa_dst.read_bytes():
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

## 1. 작업 정의

- 소스 언어: 일본어 (`ja`)
- 목표 언어: 한국어 (`ko`)
- 범위: `packets/**.json`의 `entries` 6,746개. `boundary_context`와 원본 카탈로그의 명령·메타데이터는 번역하지 않는다.
- 대상: 일본 비주얼노벨 독자. 게임의 원래 수위와 정보량을 유지하며 욕설·폭력·성적 농담을 임의 순화하거나 강화하지 않는다.
- 의미 판단의 유일한 권위는 `ja`다. 영어·중국어 번역은 이 키트에 없으며 추측 근거로 삼지 않는다.
- 목표는 검수 전 초벌이 아니라, 문맥·보이스·용어가 갖춰진 거의 최종 품질의 첫 번역이다.

## 2. 우선순위

1. 일본어 원문 의미와 화행
2. `quality_authority.md`
3. `glossary.json`의 `locked` 항목
4. `character_voice.json`의 현재 화자→실제 수신자 관계
5. 패킷 내 앞뒤 문맥과 장면의 기존 용례
6. 자연스러운 한국어

충돌 시 상위 규칙을 따르고 `issues`에 한 줄로 기록한다. `pending` 항목은 임의 확정하지 않는다.

## 3. 소스 구속·과잉 창작 금지

- 원문에 없는 수식어, 분위기, 심리, 몸짓, 동기, 인과, 친밀도, 적대감, 감정 강도, 문학적 장식을 추가하지 않는다.
- 생략된 주어·목적어·수신자는 문맥상 필수일 때만 최소한으로 보충한다.
- 다의적 문장은 장면과 설정으로 판정하되 확정 불가하면 가장 중립적이고 안전한 표현을 쓰고 `issues`에 기록한다.
- 설명을 더 친절하게 만들기 위한 문장 증설, 캐릭터성을 살린다는 명목의 유행어·욕설 추가, 일본어에 없는 의성어 추가를 금지한다.
- 초벌이 끝난 뒤 각 행을 원문과 대조해 명사구·동사·수식어·양상·강도·화행이 모두 원문에 근거하는지 무음 modifier audit를 수행한다.

## 4. 캐릭터 보이스와 수신자 추적

- `speaker_id`만 보고 말투를 고정하지 말고, 실제 수신자를 패킷의 대화 흐름에서 판정한다.
- 3인 이상 장면에서는 직전 화자를 자동 수신자로 가정하지 않는다. 호명, 질문-응답, 시선/동작 명령, 주제 지속성을 종합한다.
- 수신자별 존대 단계, 호칭, 1·2인칭, 어미, 리듬은 `character_voice.json`의 directed relationship을 따른다.
- `character_voice.json`에 한국어 예문은 없다. `evidence_uids`는 그 보이스를 대표하는 **일본어 원문 행**의 UID이며, 그 행 역시 번역 대상이다.
- 감정 상태가 바뀌어도 관계별 기본 존대와 호칭을 이유 없이 무너뜨리지 않는다.

## 5. 보호 토큰과 구조

- 각 `uid`, `source_hash`, 입력 순서와 소유권을 바꾸지 않는다.
- `required_tokens`의 태그/제어코드는 종류·개수·속성값을 정확히 보존한다.
- `<ruby=...>` 태그의 속성값도 의미 판단의 문맥이다. 속성 문자열 자체는 번역·수정하지 않지만, 속성과 표시 본문이 만드는 읽기·중의·강조 관계를 한국어 표시 본문에 필요한 만큼 반영한다.
- Gemini 결과에서는 ruby를 포함한 모든 태그를 삭제·재배치하지 않고 그대로 보존한다. 한국어에서 ruby가 불필요하거나 이중 의미를 태그 없이 풀어야 하면 `issues`에 기록한다.
- ruby 제거는 Gemini 번역과 구조 검증이 끝난 뒤 Codex 검수자가 `review/ruby_review_manifest.json`의 43개 행을 개별 승인하여 수행한다. `<tip>` 등 ruby 이외 태그는 이 단계에서도 유지한다.
- 숫자, 기호, 인용부호의 의미를 바꾸지 않는다. 문장부호는 한국어 호흡에 맞게 다듬을 수 있으나 태그와 결합 구조는 유지한다.
- 한 입력 행을 임의로 여러 행으로 쪼개거나 여러 입력 행을 합치지 않는다.

## 6. 패킷 작업 순서

1. `gemini/execution_authorization.md`를 먼저 읽은 뒤 `gemini/glossary.json`, `gemini/character_voice.json`, `gemini/quality_authority.md`를 읽는다.
2. 패킷 하나를 열고 `boundary_context.before`→`entries`→`boundary_context.after` 순으로 장면을 파악한다.
3. `entries`만 번역한다. `boundary_context`는 출력하지 않는다.
4. 첫 번역에서 곧바로 자연스러운 한국어 대사/서술을 만든다. 일본어 어순을 임시로 옮긴 직역 초벌을 제출하지 않는다.
5. 용어, 수신자, 존대, 생략 주어, 태그, 숫자, 과잉 수식어를 일괄 재검사한다.
6. 아래 형식의 JSONL만 출력한다. 설명문·마크다운·코드 펜스를 붙이지 않는다.

## 7. 출력 형식

각 입력 `entries` 1개당 정확히 1줄:

`{"uid":"ch01-00:28:6d375c5c","source_hash":"6d375c5c","target_ko":"여기에 그 행의 한국어 번역만 넣는다","issues":[]}`

(위 `target_ko`는 형식 예시일 뿐 번역 예시가 아니다. 이 키트는 어떤 한국어 예문도 제공하지 않는다.)

- 키는 `uid`, `source_hash`, `target_ko`, `issues` 네 개만 쓴다.
- `issues`는 문제가 없으면 `[]`; 용어/수신자/중의성/손상 원문 등 검수 필요 사항만 짧은 한국어 문자열로 적는다.
- 입력 개수와 출력 줄 수는 반드시 같아야 한다.
- 번역 결과를 스스로 최종 확정했다고 주장하지 않는다. 결과는 Codex의 독립 검수와 런타임 검증을 거친다.

## 8. 실패·모호성 처리

- 원문이 잘리거나 망가졌으면 추측 복원하지 말고 가능한 부분만 중립적으로 번역하고 `issues`에 적는다.
- 용어집과 실제 문맥이 충돌하면 원문 의미를 지키고 충돌을 `issues`에 적는다.
- 화자 또는 수신자를 확정할 수 없으면 성별·관계가 덜 드러나는 중립 문장을 택하고 `issues`에 적는다.
- 패킷 길이 때문에 한 번에 처리하지 못하면 임의 생략하지 말고 그 패킷을 더 작은 안정 ID 범위로 나눠 달라고 요청한다.
"""
    write_text(OUT / "gemini" / "translation_instructions.md", instructions)

    validator = r'''from __future__ import annotations
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
'''
    write_text(OUT / "tools" / "validate_gemini_result.py", validator)


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

    readme = f"""# fault - StP - LIGHTKRAVTE Gemini 시나리오 재번역 키트

이 묶음은 사용자가 명시적으로 허용한 Gemini 재번역을 위해 Codex 내부 모델이 준비한 입력 키트입니다. Gemini 호출이나 의미 번역은 아직 실행하지 않았습니다.

## 구성

| 경로 | 내용 |
|---|---|
| `gemini/execution_authorization.md` | 사용자 명시 Gemini 실행 예외와 적용 범위 |
| `gemini/glossary.json` | 161개 용어, 안정 ID, 표기, 근거 UID, 잠금/보류 상태 |
| `gemini/character_voice.json` | 35개 화자, 화자→수신자 관계별 보이스 규칙. 한국어 예문 없음, 근거는 JA 원문 UID |
| `gemini/translation_instructions.md` | Gemini 작업 지침과 JSONL 출력 계약 |
| `gemini/quality_authority.md` | 공통 일본어 VN 번역 품질 규칙의 바이트 동일 복사본 |
| `source/original_ja_catalogs/` | 46개 원본 일본어 시나리오 카탈로그의 바이트 동일 복사본 |
| `source/source_index_ja.json` | 6,746개 표시 문자열의 JA 전용 안정 ID 인덱스 |
| `packets/` | 93개 Gemini 입력 패킷. 5행 앞뒤 경계 문맥 포함 |
| `schemas/gemini_response.schema.json` | 결과 JSONL 레코드 스키마 |
| `tools/validate_gemini_result.py` | 단일 패킷 결과 구조·UID·해시·태그 검증기 + 기존 번역 유사도 게이트 |
| `review/ruby_review_manifest.json` | ruby 43행/46태그의 Gemini 이후 Codex 개별 검토표 |
| `tools/finalize_ruby_for_korean.py` | 승인된 ruby 결정만 적용하는 후처리기 |
| `packet_manifest.json` | 패킷 소유권과 원본/패킷 해시 |
| `SHA256SUMS.txt` | 배포 파일 무결성 목록 |

## 중요한 원칙

- 일본어만 의미 원문으로 사용합니다. 기존 영어·중국어 번역은 키트에 포함하지 않았습니다.
- 기존 Codex 한국어 완성본은 어떤 형태로도 키트에 넣지 않았습니다. `character_voice.json`에는 한국어 예문이 없고, `evidence_uids`는 해당 보이스를 대표하는 **일본어 원문 행의 UID**일 뿐입니다. 빌드 시 `existing_ko_absent` 검사로 확인합니다.
- 공통 `quality_authority.md`는 바이트 동일하게 유지합니다. 사용자 명시 Gemini 예외는 `execution_authorization.md`에서 먼저 확인합니다.
- Gemini는 ruby를 보존합니다. 번역·구조 검증 후 Codex가 43개 행을 개별 검토해 `strip`/`keep`/`manual`을 승인하며, 다른 태그는 유지합니다.
- `locked` 용어와 확정된 관계 보이스는 준수합니다. `pending`은 Gemini가 마음대로 확정하지 않고 결과의 `issues`에 남깁니다.
- Gemini 결과는 최종본이 아닙니다. Codex가 일본어 원문에 대조하여 독립 검수하고, 태그·레이아웃·런타임을 확인한 뒤 채택합니다.

## 통계

- 시나리오: {len(by_script)}개
- 번역 엔트리: {len(source_rows):,}개
- 패킷: {len(packet_records)}개
- 용어: {len(glossary_entries)}개 (`locked` {sum(x['status']=='locked' for x in glossary_entries)}, `pending` {sum(x['status']=='pending' for x in glossary_entries)})
- 화자: {len(profiles)}명/역할 (`pending` 프로필 {sum(x['status']=='pending' for x in profiles)})
- 생성 시각: {NOW}

## 검증기 사용 예

```
python tools/validate_gemini_result.py packets/ch01/ch01-00.part01.json results/ch01-00.part01.ko.jsonl --ko-map <원본작업지>/localization/build/ko_map.json
```

`--ko-map`은 검수자만 씁니다. 기존 한국어 완성본과의 유사도를 재고 재사용을 잡아냅니다. 키트에 넣지 않으므로 Gemini에게는 절대 전달하지 않습니다.
종료 코드: `0` 통과, `1` 구조 실패, `2` 유사도 게이트 실패.
"""
    write_text(OUT / "README_KO.md", readme)
    write_text(OUT / "UPLOAD_ORDER.md", """# Gemini 업로드 순서

1. 새 Gemini 작업에 `gemini/execution_authorization.md`를 가장 먼저 첨부하고, 이어서 `gemini/glossary.json`, `gemini/character_voice.json`, `gemini/translation_instructions.md`, `gemini/quality_authority.md`를 첨부합니다.
2. `packet_manifest.json`을 첨부해 전체 범위와 패킷 소유권을 알립니다.
3. `packets/ch01`부터 파일 **한 개씩** 처리합니다. 매번 결과를 파일명과 같은 stem의 `.ko.jsonl`로 저장합니다.
4. 긴 장면의 경계는 패킷 내부 `boundary_context`로 확인합니다. 이 문맥 행은 번역 결과에 포함하지 않습니다.
5. 각 결과에 `tools/validate_gemini_result.py`를 실행하고 PASS인 결과만 다음 검수 단계로 넘깁니다.
   검수자는 `--ko-map <원본작업지>/localization/build/ko_map.json`을 함께 주어 기존 한국어 완성본과의 유사도 게이트까지 통과시킵니다. 이 파일은 키트 밖에 있으며 Gemini에게 전달하지 않습니다. 종료 코드 `0` 통과 / `1` 구조 실패 / `2` 유사도 실패.
6. ruby가 있는 결과는 구조 검증 후 `review/ruby_review_manifest.json`의 각 UID를 Codex가 검토합니다. 전부 `pending`이 아니게 승인한 뒤 `tools/finalize_ruby_for_korean.py`로 처리합니다. `<tip>` 등 다른 태그는 유지합니다.
7. 실제 Gemini 실행 후 `gemini/manifest.json`의 `gemini_execution`에 정확한 모델명, 실행 시각, 응답/로그 해시를 추가합니다. 모델명을 추측해 미리 쓰지 않습니다.
""")

    # Manifest core hashes. Self/SHA256SUMS are intentionally excluded from recursive hashing.
    input_hashes = {
        "localization/source_index.json": sha256(loc / "source_index.json"),
        "localization/terminology.json": sha256(loc / "terminology.json"),
        "localization/packet_manifest.json": sha256(loc / "packet_manifest.json"),
        "translation-quality.md": sha256(QUALITY_SOURCE),
    }
    manifest = {
        "schema_version": 1,
        "work_id": "fault-stp-lightkravte-ja-ko-gemini-retranslation",
        "created_at": NOW,
        "languages": {"source": "ja", "target": "ko"},
        "scope": {"scenario_scripts": len(by_script), "entries": len(source_rows), "packets": len(packet_records), "excluded": ["Init.json", "Title.json", "비시나리오 UI/설정/팁 문자열"]},
        "authorization": {"external_translation_provider": "Gemini", "explicitly_requested_by_user": True, "request_date": "2026-08-29", "execution_document": "gemini/execution_authorization.md"},
        "preparation": {"translator_model": "Codex internal", "runtime_model": "GPT-5.5", "thread_id": THREAD_ID, "semantic_work": ["용어집 정규화", "번역 지침 작성", "캐릭터 보이스·관계 가이드 작성", "일본어 근거 UID 선별"]},
        "intended_provider": "Google Gemini",
        "gemini_execution": {"status": "not_run", "exact_model": None, "executed_at": None, "response_hashes": [], "note": "실제 실행 후에만 정확한 모델과 결과 provenance를 기록"},
        "semantic_authority": "Japanese source only",
        "input_hashes": input_hashes,
        "source_catalog_hashes": catalog_hashes,
        "versions": {"glossary_schema": 1, "character_voice_schema": 1, "packet_schema": 1, "ruby_review_schema": 1, "response_schema": "JSON Schema 2020-12"},
        "unresolved": {"glossary_pending": sum(x["status"] == "pending" for x in glossary_entries), "voice_profiles_pending": sum(x["status"] == "pending" for x in profiles), "exact_gemini_model": 1},
        "validation": {
            "quality_authority_byte_identical": True,
            "scenario_catalogs_byte_identical": True,
            "packet_uid_ownership_exact": True,
            "reference_translation_fields_removed": True,
            "gemini_execution_explicitly_authorized": True,
            "ruby_policy": {"gemini_output": "preserve", "codex_post_review": "per_uid_strip_keep_manual"},
            "unsupported_addition_audit": {"status": "required_after_gemini_run", "authority": "translation_instructions.md §3"},
            "gemini_output_independent_codex_review": "required",
        },
        "artifact_hashes": {},
    }
    core_files = [
        OUT / "gemini" / "glossary.json", OUT / "gemini" / "character_voice.json",
        OUT / "gemini" / "translation_instructions.md", OUT / "gemini" / "quality_authority.md",
        OUT / "gemini" / "execution_authorization.md", OUT / "review" / "ruby_review_manifest.json",
        OUT / "source" / "source_index_ja.json", OUT / "packet_manifest.json",
        OUT / "schemas" / "gemini_response.schema.json", OUT / "tools" / "validate_gemini_result.py",
        OUT / "tools" / "finalize_ruby_for_korean.py",
    ]
    manifest["artifact_hashes"] = {p.relative_to(OUT).as_posix(): sha256(p) for p in core_files}
    dump_json(OUT / "gemini" / "manifest.json", manifest)

    # Full internal validation.
    packet_files = sorted((OUT / "packets").rglob("*.json"))
    all_uids = []
    bad_ref_fields = 0
    empty_targets = 0
    for p in packet_files:
        packet = read_json(p)
        for e in packet["entries"]:
            all_uids.append(e["uid"])
            bad_ref_fields += int("en" in e or "zh_CN" in e or "zh-CN" in e)
            empty_targets += int(e["target_ko"] == "")
    # No string from the existing Korean completion may appear anywhere in the kit.
    def leaf_strings(o):
        if isinstance(o, str):
            yield o
        elif isinstance(o, dict):
            for v in o.values():
                yield from leaf_strings(v)
        elif isinstance(o, list):
            for v in o:
                yield from leaf_strings(v)

    # Probe only real Korean sentences; punctuation runs like "......" are identical in both languages.
    # The glossary is the one intended Korean channel, so its locked spellings are not leaks.
    hangul = re.compile("[가-힣]")
    ko_probe = {v["ko"] for v in ko_map.values()
                if v.get("ko") and hangul.search(v["ko"]) and len(re.sub(r"<[^>]+>", "", v["ko"]).strip()) >= 6}
    ko_probe -= {e["target"] for e in glossary_entries} | {e["canonical_spelling"] for e in glossary_entries}
    kit_strings = set(leaf_strings(voice))
    for pf in packet_files:
        kit_strings |= set(leaf_strings(read_json(pf)))
    prose = chr(10).join((OUT / rel).read_text(encoding="utf-8") for rel in
                      ["gemini/execution_authorization.md", "gemini/translation_instructions.md", "README_KO.md", "UPLOAD_ORDER.md"])
    existing_ko_leaks = sorted((kit_strings & ko_probe) | {x for x in ko_probe if x in prose})
    if existing_ko_leaks:
        raise RuntimeError({"existing_ko_leaks": existing_ko_leaks[:20], "total": len(existing_ko_leaks)})

    checks = {
        "existing_ko_absent": not existing_ko_leaks,
        "scenario_catalog_count": len(list(catalog_dst.glob("*.json"))) == 46,
        "scenario_catalogs_byte_identical": all((catalog_src / p.name).read_bytes() == p.read_bytes() for p in catalog_dst.glob("*.json")),
        "source_entry_count": len(source_rows) == 6746,
        "packet_count": len(packet_files) == 93,
        "packet_entry_count": len(all_uids) == 6746,
        "packet_uid_unique": len(set(all_uids)) == len(all_uids),
        "packet_uid_exact_set": set(all_uids) == {r["uid"] for r in source_rows},
        "reference_fields_absent": bad_ref_fields == 0,
        "all_target_placeholders_empty": empty_targets == 6746,
        "glossary_entries": len(glossary_entries) == 161,
        "speaker_profiles": len(profiles) == 35,
        "ruby_review_rows": ruby_review["row_count"] == 43,
        "ruby_open_tags": ruby_review["ruby_open_tag_count"] == 46,
        "ruby_decisions_initially_pending": all(e["decision"] == "pending" for e in ruby_review["entries"]),
        "execution_authorization_present": (OUT / "gemini" / "execution_authorization.md").exists(),
        "quality_authority_byte_identical": QUALITY_SOURCE.read_bytes() == qa_dst.read_bytes(),
    }
    if not all(checks.values()):
        raise RuntimeError({k: v for k, v in checks.items() if not v})
    report = {"created_at": NOW, "status": "PASS", "checks": checks, "counts": {"scripts": len(by_script), "entries": len(source_rows), "packets": len(packet_files), "glossary": len(glossary_entries), "speakers": len(profiles)}}
    dump_json(OUT / "VALIDATION_REPORT.json", report)

    # scratchpad contains local backups and is never distributable.
    def is_distributable(path):
        rel_parts = path.relative_to(OUT).parts
        return path.is_file() and "scratchpad" not in rel_parts and "__pycache__" not in rel_parts

    checksum_lines = []
    for p in sorted(x for x in OUT.rglob("*") if is_distributable(x) and x.name != "SHA256SUMS.txt"):
        checksum_lines.append(f"{sha256(p)}  {p.relative_to(OUT).as_posix()}")
    write_text(OUT / "SHA256SUMS.txt", "\n".join(checksum_lines))

    # Reproducible-enough ZIP (contains distributable files; builder included for auditability).
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9, allowZip64=True) as zf:
        for p in sorted(x for x in OUT.rglob("*") if is_distributable(x)):
            arc = f"{OUT.name}/{p.relative_to(OUT).as_posix()}"
            zf.write(p, arc)
    print(json.dumps({"status": "PASS", "out": str(OUT), "zip": str(ZIP_PATH), "zip_sha256": sha256(ZIP_PATH), "counts": report["counts"], "glossary_pending": manifest["unresolved"]["glossary_pending"], "voice_pending": manifest["unresolved"]["voice_profiles_pending"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    build()
