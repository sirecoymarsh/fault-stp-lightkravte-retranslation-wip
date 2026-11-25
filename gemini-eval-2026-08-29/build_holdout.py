from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path


KIT = Path(r"P:\AI\Codex\projects\fault-stp-lightkravte-gemini-scenario-kit-2026-08-29")
KIT_ZIP = KIT.with_suffix(".zip")
WORK = Path(r"P:\AI\Codex\projects\_migrated_c_documents_codex\2026-07-25\new-chat\work")
OUT = Path(r"P:\AI\Codex\projects\fault-stp-lightkravte-gemini-eval-2026-08-29")
SEED = "fault-stp-lightkravte-holdout-v1-2026-08-29"
TARGET_SIZE = 200
NOW = datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")
TAG_RE = re.compile(r"<[^>]+>")


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def write(path: Path, value: str) -> None:
    path.write_text(value.rstrip() + "\n", encoding="utf-8", newline="\n")


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def digest(path: Path) -> str:
    return digest_bytes(path.read_bytes())


def stable_score(text: str) -> int:
    return int(hashlib.sha256((SEED + "\0" + text).encode("utf-8")).hexdigest(), 16)


def text_length(row) -> int:
    return len(TAG_RE.sub("", row["ja"]).strip())


def length_bucket(row) -> str:
    n = text_length(row)
    if n <= 12:
        return "short_1_12"
    if n <= 32:
        return "medium_13_32"
    return "long_33_plus"


def distribute_script_quotas(candidates_by_script):
    scripts = sorted(candidates_by_script)
    quota = {s: min(2, len(candidates_by_script[s])) for s in scripts}
    remaining = TARGET_SIZE - sum(quota.values())
    capacity = {s: len(candidates_by_script[s]) - quota[s] for s in scripts}
    total_capacity = sum(capacity.values())
    raw = {s: (remaining * capacity[s] / total_capacity if total_capacity else 0) for s in scripts}
    for s in scripts:
        add = min(capacity[s], math.floor(raw[s]))
        quota[s] += add
    left = TARGET_SIZE - sum(quota.values())
    order = sorted(scripts, key=lambda s: (-(raw[s] - math.floor(raw[s])), stable_score("quota:" + s)))
    while left:
        progressed = False
        for s in order:
            if quota[s] < len(candidates_by_script[s]):
                quota[s] += 1
                left -= 1
                progressed = True
                if not left:
                    break
        if not progressed:
            raise RuntimeError("insufficient candidates")
    return quota


def choose_within_script(rows, count):
    rows = sorted(rows, key=lambda r: stable_score(r["uid"]))
    selected = []
    speakers = Counter()
    length_buckets = Counter()
    token_flags = Counter()
    quartiles = Counter()
    max_seq = max(r["sequence"] for r in rows) or 1
    while len(selected) < count:
        best = None
        best_key = None
        for r in rows:
            if r in selected:
                continue
            speaker = r["speaker_id"] or "<narration>"
            lb = length_bucket(r)
            tf = "has_tokens" if r.get("required_tokens") else "plain"
            q = min(3, int((r["sequence"] / max_seq) * 4))
            coverage = (
                10 * (speakers[speaker] == 0)
                + 6 * (quartiles[q] == 0)
                + 4 * (length_buckets[lb] == 0)
                + 3 * (token_flags[tf] == 0)
                - 2 * speakers[speaker]
                - length_buckets[lb]
            )
            key = (coverage, -stable_score("pick:" + r["uid"]))
            if best_key is None or key > best_key:
                best, best_key = r, key
        if best is None:
            raise RuntimeError("selection stalled")
        selected.append(best)
        speakers[best["speaker_id"] or "<narration>"] += 1
        length_buckets[length_bucket(best)] += 1
        token_flags["has_tokens" if best.get("required_tokens") else "plain"] += 1
        quartiles[min(3, int((best["sequence"] / max_seq) * 4))] += 1
    return selected


def main():
    source = load(WORK / "localization" / "source_index.json")
    ko_map = load(WORK / "localization" / "build" / "ko_map.json")
    voice = load(KIT / "gemini" / "character_voice.json")
    packet_manifest = load(KIT / "packet_manifest.json")
    packet_for_uid = {}
    for p in packet_manifest["packets"]:
        packet = load(KIT / p["file"])
        for e in packet["entries"]:
            packet_for_uid[e["uid"]] = p["file"]

    occurrences = []
    for profile in voice["profiles"]:
        for example_index, example in enumerate(profile.get("codex_authored_examples", [])):
            occurrences.append({
                "uid": example["uid"], "speaker_id": profile["speaker_id"],
                "location": "profile", "addressee": None, "relation_index": None,
                "example_index": example_index, "evidence_scope": "speaker_profile",
            })
        for relation_index, relation in enumerate(profile["directed_relationships"]):
            for example_index, example in enumerate(relation.get("codex_authored_examples", [])):
                occurrences.append({
                    "uid": example["uid"], "speaker_id": profile["speaker_id"],
                    "location": "directed_relationship", "addressee": relation["addressee"],
                    "relation_index": relation_index, "example_index": example_index,
                    "evidence_scope": relation.get("evidence_scope"),
                })
    exposed_uids = {x["uid"] for x in occurrences}
    source_by_uid = {r["uid"]: r for r in source}
    assert exposed_uids <= set(source_by_uid)

    candidates_by_script = defaultdict(list)
    for row in source:
        if row["uid"] not in exposed_uids:
            candidates_by_script[row["script"]].append(row)
    quotas = distribute_script_quotas(candidates_by_script)
    holdout = []
    for script in sorted(candidates_by_script):
        holdout.extend(choose_within_script(candidates_by_script[script], quotas[script]))
    holdout.sort(key=lambda r: (r["script"], r["sequence"], r["uid"]))
    holdout_uids = {r["uid"] for r in holdout}
    assert len(holdout) == TARGET_SIZE
    assert len(holdout_uids) == TARGET_SIZE
    assert not (holdout_uids & exposed_uids)

    public_rows = []
    private_rows = []
    for r in holdout:
        public_rows.append({
            "uid": r["uid"], "source_hash": r["source_hash"], "script": r["script"],
            "sequence": r["sequence"], "source_line": r["source_line"],
            "speaker_id": r["speaker_id"], "packet_file": packet_for_uid[r["uid"]],
            "length_bucket": length_bucket(r), "has_required_tokens": bool(r.get("required_tokens")),
        })
        private_rows.append({
            "group": "holdout", "uid": r["uid"], "source_hash": r["source_hash"],
            "script": r["script"], "speaker_id": r["speaker_id"], "ja": r["ja"],
            "ko_codex_reference": ko_map[r["uid"]]["ko"], "packet_file": packet_for_uid[r["uid"]],
        })
    exposed_private = []
    for uid in sorted(exposed_uids):
        r = source_by_uid[uid]
        exposed_private.append({
            "group": "exposed_example", "uid": uid, "source_hash": r["source_hash"],
            "script": r["script"], "speaker_id": r["speaker_id"], "ja": r["ja"],
            "ko_codex_reference": ko_map[uid]["ko"], "packet_file": packet_for_uid[uid],
            "reference_occurrences": sum(1 for x in occurrences if x["uid"] == uid),
        })

    chapter_counts = Counter(r["script"][:4] for r in holdout)
    script_counts = Counter(r["script"] for r in holdout)
    speaker_counts = Counter(r["speaker_id"] or "<narration>" for r in holdout)
    length_counts = Counter(length_bucket(r) for r in holdout)
    token_counts = Counter("has_tokens" if r.get("required_tokens") else "plain" for r in holdout)

    dump(OUT / "control_uids_200.json", {
        "schema_version": 1, "warning": "DO NOT UPLOAD TO GEMINI; 숨겨진 대조군 명단",
        "seed": SEED, "count": len(public_rows), "entries": public_rows,
    })
    dump(OUT / "private_reference_holdout.json", {
        "schema_version": 1, "warning": "DO NOT UPLOAD OR DISCLOSE TO GEMINI; Codex 기준 번역 포함",
        "count": len(private_rows), "entries": private_rows,
    })
    dump(OUT / "private_reference_exposed_examples.json", {
        "schema_version": 1, "warning": "DO NOT UPLOAD; 보이스 예문 노출군의 중복 제거 기준표",
        "reference_occurrences": len(occurrences), "unique_uid_count": len(exposed_private), "entries": exposed_private,
    })
    dump(OUT / "exposed_example_occurrences.json", {
        "schema_version": 1, "warning": "DO NOT UPLOAD; character_voice.json 내 예문 발생 위치",
        "occurrence_count": len(occurrences), "unique_uid_count": len(exposed_uids), "entries": occurrences,
    })

    compare_tool = r'''from __future__ import annotations
import argparse, difflib, json, re, statistics, unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def load(path): return json.loads(path.read_text(encoding="utf-8"))
def norm(s):
    s = unicodedata.normalize("NFKC", s)
    return "".join(ch for ch in s if not ch.isspace() and not unicodedata.category(ch).startswith("P"))
def ngrams(s, n=3):
    s = norm(s)
    if len(s) < n: return {s} if s else set()
    return {s[i:i+n] for i in range(len(s)-n+1)}
def jaccard(a,b):
    x,y=ngrams(a),ngrams(b)
    return len(x&y)/len(x|y) if x or y else 1.0
def metrics(a,b):
    na,nb=norm(a),norm(b)
    return {"exact": a==b, "normalized_exact": na==nb,
            "sequence_ratio": difflib.SequenceMatcher(None,na,nb).ratio(),
            "trigram_jaccard": jaccard(a,b)}
def summarize(rows):
    if not rows: return {"available":0}
    ratios=[r["sequence_ratio"] for r in rows]; jacs=[r["trigram_jaccard"] for r in rows]
    return {"available":len(rows), "exact_rate":sum(r["exact"] for r in rows)/len(rows),
            "normalized_exact_rate":sum(r["normalized_exact"] for r in rows)/len(rows),
            "sequence_ratio_mean":statistics.mean(ratios), "sequence_ratio_median":statistics.median(ratios),
            "trigram_jaccard_mean":statistics.mean(jacs), "similarity_ge_0_90":sum(x>=.90 for x in ratios)/len(rows),
            "similarity_ge_0_95":sum(x>=.95 for x in ratios)/len(rows)}
def main():
    ap=argparse.ArgumentParser(description="노출 예문군과 숨은 대조군의 Codex 대비 유사도 비교")
    ap.add_argument("results_dir",type=Path)
    ap.add_argument("--out",type=Path,default=ROOT/"similarity_report.json")
    ns=ap.parse_args()
    got={}; errors=[]
    for p in sorted(ns.results_dir.rglob("*.jsonl")):
        for i,line in enumerate(p.read_text(encoding="utf-8-sig").splitlines(),1):
            if not line.strip(): continue
            try: r=json.loads(line)
            except Exception as e: errors.append(f"{p}:{i}: {e}"); continue
            uid=r.get("uid")
            if uid in got: errors.append(f"duplicate uid: {uid}")
            got[uid]=r.get("target_ko","")
    hold=load(ROOT/"private_reference_holdout.json")["entries"]
    exposed=load(ROOT/"private_reference_exposed_examples.json")["entries"]
    details={"holdout":[],"exposed_example":[]}; missing={"holdout":[],"exposed_example":[]}
    for group,refs in [("holdout",hold),("exposed_example",exposed)]:
        for ref in refs:
            if ref["uid"] not in got: missing[group].append(ref["uid"]); continue
            row={"uid":ref["uid"], **metrics(got[ref["uid"]],ref["ko_codex_reference"])}
            details[group].append(row)
    summaries={k:summarize(v) for k,v in details.items()}
    delta={}
    if summaries["holdout"].get("available") and summaries["exposed_example"].get("available"):
        for key in ["exact_rate","normalized_exact_rate","sequence_ratio_mean","trigram_jaccard_mean","similarity_ge_0_90","similarity_ge_0_95"]:
            delta[key]=summaries["exposed_example"][key]-summaries["holdout"][key]
    report={"status":"PASS" if not errors else "RESULT_PARSE_ERRORS", "interpretation":"양의 delta가 크면 예문 노출군의 복사 가능성이 커졌다는 신호다. 단독으로 표절을 확정하지는 않는다.",
            "summaries":summaries,"exposed_minus_holdout":delta,"missing":missing,"errors":errors,"details":details}
    ns.out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k!="details"},ensure_ascii=False,indent=2))
    return 0 if not errors else 1
if __name__=="__main__": raise SystemExit(main())
'''
    write(OUT / "compare_similarity.py", compare_tool)

    kit_zip_before = digest(KIT_ZIP)
    manifest = {
        "schema_version": 1, "created_at": NOW, "purpose": "Gemini 보이스 예문 노출군과 비노출 대조군의 Codex 대비 유사도 차이 측정",
        "status": "READY_PRIVATE_DO_NOT_UPLOAD",
        "selection": {
            "seed": SEED, "target_size": TARGET_SIZE,
            "excluded_example_occurrences": len(occurrences), "excluded_example_unique_uids": len(exposed_uids),
            "overlap_with_exposed": len(holdout_uids & exposed_uids),
            "algorithm": "46개 스크립트에 최소 2개 배정 후 후보 수 비례 최대나머지 배분; 스크립트 안에서 화자·장면 사분위·문장 길이·보호 토큰 상태의 신규 범주를 우선하는 결정적 greedy 추출; SHA-256 seed로 동률 결정",
            "distribution": {"chapter": dict(sorted(chapter_counts.items())), "script": dict(sorted(script_counts.items())), "speaker": dict(sorted(speaker_counts.items())), "length": dict(sorted(length_counts.items())), "tokens": dict(sorted(token_counts.items()))},
        },
        "source_integrity": {
            "kit_zip_sha256_before": kit_zip_before,
            "kit_manifest_sha256": digest(KIT / "gemini" / "manifest.json"),
            "source_index_sha256": digest(WORK / "localization" / "source_index.json"),
            "ko_map_sha256": digest(WORK / "localization" / "build" / "ko_map.json"),
        },
        "files": {},
    }
    files = ["control_uids_200.json", "private_reference_holdout.json", "private_reference_exposed_examples.json", "exposed_example_occurrences.json", "compare_similarity.py"]
    manifest["files"] = {name: digest(OUT / name) for name in files}
    dump(OUT / "control_manifest.json", manifest)
    write(OUT / "DO_NOT_UPLOAD_TO_GEMINI.txt", """이 폴더 전체를 Gemini에 업로드하지 마십시오.

`control_uids_200.json`은 숨은 대조군의 정체를 담고 있고,
`private_reference_*.json`은 Codex 기준 번역문을 담고 있습니다.
Gemini 입력에는 기존 scenario kit ZIP만 사용합니다.
결과 수집이 끝난 뒤 `compare_similarity.py`에 결과 폴더를 지정해 노출군/대조군 차이를 계산합니다.
""")
    readme = f"""# Gemini 번역 독립 평가용 비공개 대조군

**이 폴더는 Gemini에 첨부하지 않는다.** 기존 키트 ZIP은 수정하지 않았다.

## 고정 결과

- 숨은 대조군: {len(holdout)} UID
- 보이스 예문 발생: {len(occurrences)}건
- 보이스 예문 고유 UID: {len(exposed_uids)}개
- 대조군과 예문 UID 교집합: 0개
- 기존 키트 ZIP SHA-256: `{kit_zip_before}`

## 파일

- `control_uids_200.json`: 대상과 층화 메타데이터. 한국어 기준 번역은 없음.
- `private_reference_holdout.json`: 대조군 일본어와 Codex 기준 번역.
- `private_reference_exposed_examples.json`: 노출 예문군의 중복 제거 기준표.
- `exposed_example_occurrences.json`: 보이스 파일 안의 예문 발생 위치 전부.
- `compare_similarity.py`: Gemini 결과 JSONL 폴더를 읽어 노출군과 대조군의 유사도 차이를 계산.
- `control_manifest.json`: 선택 알고리즘, 분포, 입력·파일 해시.

## 결과 수집 뒤 실행

`python compare_similarity.py <Gemini 결과 JSONL 폴더> --out similarity_report.json`

노출군-대조군의 exact match, 정규화 exact match, SequenceMatcher, 문자 3-gram Jaccard 차이를 함께 본다. 노출군만 크게 튀면 예문 복사의 신호로 해석하되, 차이 하나만으로 확정하지 않는다.
"""
    write(OUT / "README_PRIVATE_KO.md", readme)

    # Final manifest update with the two explanatory files, then re-check the untouched kit ZIP.
    manifest = load(OUT / "control_manifest.json")
    manifest["files"].update({
        "DO_NOT_UPLOAD_TO_GEMINI.txt": digest(OUT / "DO_NOT_UPLOAD_TO_GEMINI.txt"),
        "README_PRIVATE_KO.md": digest(OUT / "README_PRIVATE_KO.md"),
    })
    manifest["source_integrity"]["kit_zip_sha256_after"] = digest(KIT_ZIP)
    manifest["source_integrity"]["kit_zip_unchanged"] = manifest["source_integrity"]["kit_zip_sha256_before"] == manifest["source_integrity"]["kit_zip_sha256_after"]
    dump(OUT / "control_manifest.json", manifest)
    assert manifest["source_integrity"]["kit_zip_unchanged"]
    print(json.dumps({
        "status": "PASS", "holdout": len(holdout), "example_occurrences": len(occurrences),
        "example_unique_uids": len(exposed_uids), "overlap": 0,
        "kit_zip_unchanged": True, "kit_zip_sha256": digest(KIT_ZIP),
        "chapter_distribution": dict(sorted(chapter_counts.items())),
        "token_distribution": dict(sorted(token_counts.items())),
        "out": str(OUT),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
