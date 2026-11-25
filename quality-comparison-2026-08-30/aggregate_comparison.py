from __future__ import annotations

import hashlib
import json
import math
import random
import statistics
from collections import Counter
from pathlib import Path


ROOT = Path(r"P:\AI\Codex\projects\fault-stp-lightkravte-quality-comparison-2026-08-30")
RUBRIC = ["fidelity", "naturalness", "directed_voice", "no_unsupported_addition"]


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sign_test_two_sided(a: int, b: int) -> float:
    n = a + b
    k = min(a, b)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / (2 ** n)
    return min(1.0, 2 * tail)


def bootstrap_ci(diffs, iterations=20000):
    rng = random.Random(20260830)
    vals = []
    n = len(diffs)
    for _ in range(iterations):
        vals.append(sum(diffs[rng.randrange(n)] for _ in range(n)) / n)
    vals.sort()
    return vals[int(iterations * .025)], vals[int(iterations * .975)]


def summarize(rows):
    prefs = Counter(r["preferred"] for r in rows)
    result = {"count": len(rows), "preference": dict(prefs)}
    result["non_tie_existing_share"] = prefs["existing"] / (prefs["existing"] + prefs["gemini"]) if prefs["existing"] + prefs["gemini"] else None
    result["paired_sign_test_p"] = sign_test_two_sided(prefs["existing"], prefs["gemini"])
    result["provider"] = {}
    for provider in ["gemini", "existing"]:
        result["provider"][provider] = {
            "mean_scores": {k: statistics.mean(r["scores"][provider][k] for r in rows) for k in RUBRIC},
            "any_score_le_2": sum(any(r["scores"][provider][k] <= 2 for k in RUBRIC) for r in rows),
            "score_le_2_by_dimension": {k: sum(r["scores"][provider][k] <= 2 for r in rows) for k in RUBRIC},
            "mean_total_16": statistics.mean(sum(r["scores"][provider][k] for k in RUBRIC) for r in rows),
        }
    diffs = [sum(r["scores"]["existing"][k] - r["scores"]["gemini"][k] for k in RUBRIC) for r in rows]
    result["existing_minus_gemini_total_mean"] = statistics.mean(diffs)
    result["existing_minus_gemini_total_bootstrap_95ci"] = bootstrap_ci(diffs)
    result["major_difference_preferred"] = dict(Counter(r["preferred"] for r in rows if r["severity"] == "major"))
    result["major_difference_loser"] = {
        "gemini": sum(r["severity"] == "major" and r["preferred"] == "existing" for r in rows),
        "existing": sum(r["severity"] == "major" and r["preferred"] == "gemini" for r in rows),
    }
    return result


def main():
    blind_key = load(ROOT / "private" / "blind_key.json")
    meta = {}
    for path in sorted((ROOT / "blind_packets").glob("packet_*.json")):
        for entry in load(path)["entries"]:
            meta[entry["uid"]] = entry

    rows = []
    for path in sorted((ROOT / "judgments").glob("packet_*.json")):
        packet = load(path)
        if packet.get("review_status") != "complete_blind":
            raise RuntimeError(f"incomplete blind review: {path}")
        for judgment in packet["entries"]:
            uid = judgment["uid"]
            entry = meta[uid]
            mapping = blind_key[uid]
            scores = {mapping["A"]: judgment["A"], mapping["B"]: judgment["B"]}
            preferred = "tie" if judgment["preferred"] == "tie" else mapping[judgment["preferred"]]
            candidates = {
                mapping["A"]: entry["candidate_A"],
                mapping["B"]: entry["candidate_B"],
            }
            rows.append({
                "uid": uid, "script": entry["script"], "line_index": entry["line_index"],
                "speaker_id": entry["speaker_id"], "panel": entry["selection_panel"][0],
                "selection_reason": entry["selection_reason"],
                "ja": entry["ja"], "context_before": entry["context_before"], "context_after": entry["context_after"],
                "gemini": candidates["gemini"], "existing": candidates["existing"],
                "preferred": preferred, "severity": judgment["severity"], "reason_blind": judgment["reason"],
                "scores": scores,
            })
    if len(rows) != 200 or len({r["uid"] for r in rows}) != 200:
        raise RuntimeError("review row count/identity mismatch")

    representative = [r for r in rows if r["panel"] == "representative"]
    risk = [r for r in rows if r["panel"] == "risk"]
    ruby = [r for r in rows if "<ruby" in r["ja"].lower()]
    summary = {
        "schema_version": 1,
        "reviewer": "Codex internal",
        "review_method": "Blind paired semantic comparison; provider key opened only after all 200 judgments were written",
        "semantic_authority": "Japanese raw catalog text and its independently extracted neighboring PrintText records",
        "existing_translation_role": "comparison candidate only, not meaning authority",
        "panels": {
            "all": summarize(rows),
            "representative": summarize(representative),
            "risk": summarize(risk),
            "ruby_subset": summarize(ruby),
        },
        "input_hashes": {
            "selection_manifest.json": sha(ROOT / "selection_manifest.json"),
            "blind_key.json": sha(ROOT / "private" / "blind_key.json"),
            **{f"judgments/{p.name}": sha(p) for p in sorted((ROOT / "judgments").glob("packet_*.json"))},
        },
        "verdict": {
            "better_base": "existing",
            "confidence": "high for base-selection decision; not a substitute for full 6,746-line semantic QA",
            "recommended_use": "Retain existing translation as base. Use Gemini as a secondary comparison source and adopt only line-level improvements confirmed against Japanese.",
        },
    }
    dump(ROOT / "unblinded_results.json", {"summary": summary, "entries": rows})
    dump(ROOT / "comparison_summary.json", summary)

    rep = summary["panels"]["representative"]
    allp = summary["panels"]["all"]
    riskp = summary["panels"]["risk"]
    rubyp = summary["panels"]["ruby_subset"]
    eg = rep["provider"]["existing"]
    gg = rep["provider"]["gemini"]
    report = f"""# fault - StP - LIGHTKRAVTE 번역 품질 비교

## 결론

**기존 번역본이 재번역본보다 전체 교체의 기반으로 더 낫다.**

Gemini 번역을 통째로 채택하지 않는다. 기존 번역을 유지하고, Gemini가 실제로 더 나았던 행만 일본어 원문 대조 후 선별 반입하는 편이 품질과 수정량 모두에서 유리하다.

## 비교 설계

- 의미 기준: 일본어 원본 카탈로그
- 기존 `ko_map.json`: 의미의 근거가 아니라 비교 후보로만 사용
- 원문 문맥: 검수 하네스가 아니라 46개 원본 카탈로그의 `records`를 별도 코드로 직접 파싱
- 블라인드: 두 번역을 A/B로 무작위 배치하고 200행 판정을 모두 기록한 뒤 제공자 키를 개봉
- 대표 표본: 150행, 46개 스크립트에서 최소 3행씩 포함
- 위험 표본: 50행 — Gemini issues 11행, ruby 15행, 3인 이상 화자 창 15행, 낮은 후보 유사도·길이 차이 포함
- 채점: 의미 충실도, 자연스러움, 화자→수신자 보이스, 원문 비근거 증설 억제 — 각 0~4점

## 결과

| 패널 | 기존 우세 | Gemini 우세 | 동률 | 비동률 중 기존 비율 |
|---|---:|---:|---:|---:|
| 대표 150행 | {rep['preference'].get('existing', 0)} | {rep['preference'].get('gemini', 0)} | {rep['preference'].get('tie', 0)} | {rep['non_tie_existing_share']:.1%} |
| 위험 50행 | {riskp['preference'].get('existing', 0)} | {riskp['preference'].get('gemini', 0)} | {riskp['preference'].get('tie', 0)} | {riskp['non_tie_existing_share']:.1%} |
| 합계 200행 | {allp['preference'].get('existing', 0)} | {allp['preference'].get('gemini', 0)} | {allp['preference'].get('tie', 0)} | {allp['non_tie_existing_share']:.1%} |

대표 표본의 비동률 100행에서는 기존 번역이 63 대 37로 우세했다. 대응 부호검정의 양측 p값은 `{rep['paired_sign_test_p']:.4f}`다. 대표 표본의 16점 만점 총점 차이는 기존 번역이 평균 `{rep['existing_minus_gemini_total_mean']:.3f}`점 높았고, 결정적 bootstrap 95% 구간은 `{rep['existing_minus_gemini_total_bootstrap_95ci'][0]:.3f}~{rep['existing_minus_gemini_total_bootstrap_95ci'][1]:.3f}`점이다.

### 대표 표본 평균 점수

| 기준 | 기존 번역 | Gemini |
|---|---:|---:|
| 의미 충실도 | {eg['mean_scores']['fidelity']:.3f} | {gg['mean_scores']['fidelity']:.3f} |
| 자연스러움 | {eg['mean_scores']['naturalness']:.3f} | {gg['mean_scores']['naturalness']:.3f} |
| 화자→수신자 보이스 | {eg['mean_scores']['directed_voice']:.3f} | {gg['mean_scores']['directed_voice']:.3f} |
| 원문 비근거 증설 억제 | {eg['mean_scores']['no_unsupported_addition']:.3f} | {gg['mean_scores']['no_unsupported_addition']:.3f} |
| 합계 / 16 | {eg['mean_total_16']:.3f} | {gg['mean_total_16']:.3f} |

전체 200행에서 한 기준이라도 2점 이하인 후보는 기존 번역 25행, Gemini 51행이었다. 큰 차이로 패한 사례는 기존 번역 19행, Gemini 40행이다.

| 2점 이하 결함 유형 | 기존 번역 | Gemini |
|---|---:|---:|
| 의미 충실도 | {allp['provider']['existing']['score_le_2_by_dimension']['fidelity']} | {allp['provider']['gemini']['score_le_2_by_dimension']['fidelity']} |
| 자연스러움 | {allp['provider']['existing']['score_le_2_by_dimension']['naturalness']} | {allp['provider']['gemini']['score_le_2_by_dimension']['naturalness']} |
| 관계 보이스 | {allp['provider']['existing']['score_le_2_by_dimension']['directed_voice']} | {allp['provider']['gemini']['score_le_2_by_dimension']['directed_voice']} |
| 비근거 증설 | {allp['provider']['existing']['score_le_2_by_dimension']['no_unsupported_addition']} | {allp['provider']['gemini']['score_le_2_by_dimension']['no_unsupported_addition']} |

## 관찰된 차이

### Gemini가 반복해서 약했던 부분

- 원문에 없는 감정·평가·설명 추가: `따위`, `든든하게`, 감사 이유, 고통 신음, 문학적 일반화
- 일본어 구조를 살린 어색한 한국어: `난폭하게 생각했다`, `믿겨져`, 불필요한 문어체
- 카지 독백·편지·기록의 존대 단계가 구간별로 바뀜
- 화자→수신자 호칭 누락 또는 변경: `공주님`→`님`, `카지 군` 누락, 부자 관계의 `응`→`네`
- 장면 핵심어를 일반화하거나 구체화: 형태로 만들다→결과물을 내다, 현재 이용 가능한 파리너→일반 파리너
- `決まった時間`을 정해진 시각이 아닌 일정 시간 동안으로 오독

### 기존 번역도 실제로 진 부분

- 일부 기록·편지·독백의 존댓말 단계 오류
- `ぐー`를 `드르렁`으로 과장하거나 `ったく`을 `젠장`으로 강화
- 의도적인 더듬음·깨진 발화를 정상화한 행
- `カージくん`의 `군`을 누락하거나 호칭을 중복한 행
- 일부 문장이 번역투인 행

즉 Gemini 결과는 무가치하지 않다. 대표 표본에서도 37행, 전체 표본에서는 55행에서 더 나았다. 다만 **교체본으로는 열세이고, 기존 번역의 오류를 찾는 대조 후보로 가치가 높다.**

### 원문 대조 사례

| UID | 일본어 핵심 | 기존 번역 | Gemini | 판정 |
|---|---|---|---|---|
| `ch01-02d:25:99fc1a6a` | `毎日決まった時間` | `매일 정해진 시간에` | `매일 정해진 시간 동안` | 기존 우세 — 시각을 지속시간으로 오독 |
| `ch01-03:348:884b8c71` | `ただの白い布` | `그저 하얀 천` | `힘 따위` | 기존 우세 — `따위`의 경멸을 힘에 비근거 추가 |
| `ch01-12d:17:fbf8f728` | 카지의 평서형 기록 | `…거짓말이야` | `…거짓말이겠죠` | 기존 우세 — 독백 존대 단계가 바뀜 |
| `ch01-00:237:ce4cb594` | `ぐー…ぐー…` | `드르렁…` | `쿨…` | Gemini 우세 — 기존이 코골이 강도를 과장 |
| `ch01-08d:20:f7ae9609` | 어머니에게 쓰는 `書けません` | `못 쓰겠어` | `쓸 수가 없어요` | Gemini 우세 — 기존이 편지 존댓말을 반말로 변경 |
| `ch02-07:37:16ff3daf` | `ば ばい…！ カージじでず` | 정상화된 자기소개 | 더듬고 뭉개진 발화 보존 | Gemini 우세 — 기존이 의도적 발화 훼손을 평탄화 |

## Ruby 부분집합

표본에 들어온 ruby 15행에서는 기존 번역 10행, Gemini 5행이 우세했다. 이 비교는 최종 태그 정책이 아니라 일본어의 base/아테지 의미가 한국어 문장에 얼마나 잘 반영됐는지만 평가했다. 실제 반입 전에는 43행 전부를 `strip`/`keep`/`manual`로 별도 확정해야 한다.

## 권고

1. 최종 번역 맵의 기반은 기존 `ko_map.json`으로 되돌린다.
2. 이번 블라인드 검수에서 Gemini 우세로 판정된 55행부터 일본어 원문과 재확인해 선택 반입한다.
3. Gemini 전량을 기존 번역 위에 덮어쓰지 않는다.
4. 이후 의미 검수는 Gemini 쪽에서 많이 나온 네 유형—증설, 번역투, 존대 단계, 호칭/수신자—을 우선 탐색한다.
5. 이 200행 평가는 기반 선택에는 충분하지만 6,746행 전량의 최종 승인을 대신하지 않는다.

## 산출물

- `selection_manifest.json`: 표본 선정과 원본 카탈로그 해시
- `blind_packets/`: 제공자명을 숨긴 비교 입력
- `judgments/`: 키 개봉 전에 작성한 200행 판정
- `private/blind_key.json`: A/B 제공자 키
- `unblinded_results.json`: 후보·점수·판정을 합친 상세 결과
- `comparison_summary.json`: 집계 수치
"""
    (ROOT / "QUALITY_COMPARISON_KO.md").write_text(report, encoding="utf-8", newline="\n")
    print(json.dumps({
        "status": "PASS", "better_base": "existing",
        "all_preference": allp["preference"], "representative_preference": rep["preference"],
        "representative_sign_test_p": rep["paired_sign_test_p"],
        "representative_total_difference": rep["existing_minus_gemini_total_mean"],
        "report": str(ROOT / "QUALITY_COMPARISON_KO.md"),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
