# fault - StP - LIGHTKRAVTE Gemini 시나리오 재번역 키트

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

- 시나리오: 46개
- 번역 엔트리: 6,746개
- 패킷: 93개
- 용어: 161개 (`locked` 123, `pending` 38)
- 화자: 35명/역할 (`pending` 프로필 22)
- 생성 시각: 2026-08-29T18:09:15+09:00

## 검증기 사용 예

```
python tools/validate_gemini_result.py packets/ch01/ch01-00.part01.json results/ch01-00.part01.ko.jsonl --ko-map <원본작업지>/localization/build/ko_map.json
```

`--ko-map`은 검수자만 씁니다. 기존 한국어 완성본과의 유사도를 재고 재사용을 잡아냅니다. 키트에 넣지 않으므로 Gemini에게는 절대 전달하지 않습니다.
종료 코드: `0` 통과, `1` 구조 실패, `2` 유사도 게이트 실패.
