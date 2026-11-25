# Gemini 업로드 순서

1. 새 Gemini 작업에 `gemini/execution_authorization.md`를 가장 먼저 첨부하고, 이어서 `gemini/glossary.json`, `gemini/character_voice.json`, `gemini/translation_instructions.md`, `gemini/quality_authority.md`를 첨부합니다.
2. `packet_manifest.json`을 첨부해 전체 범위와 패킷 소유권을 알립니다.
3. `packets/ch01`부터 파일 **한 개씩** 처리합니다. 매번 결과를 파일명과 같은 stem의 `.ko.jsonl`로 저장합니다.
4. 긴 장면의 경계는 패킷 내부 `boundary_context`로 확인합니다. 이 문맥 행은 번역 결과에 포함하지 않습니다.
5. 각 결과에 `tools/validate_gemini_result.py`를 실행하고 PASS인 결과만 다음 검수 단계로 넘깁니다.
   검수자는 `--ko-map <원본작업지>/localization/build/ko_map.json`을 함께 주어 기존 한국어 완성본과의 유사도 게이트까지 통과시킵니다. 이 파일은 키트 밖에 있으며 Gemini에게 전달하지 않습니다. 종료 코드 `0` 통과 / `1` 구조 실패 / `2` 유사도 실패.
6. ruby가 있는 결과는 구조 검증 후 `review/ruby_review_manifest.json`의 각 UID를 Codex가 검토합니다. 전부 `pending`이 아니게 승인한 뒤 `tools/finalize_ruby_for_korean.py`로 처리합니다. `<tip>` 등 다른 태그는 유지합니다.
7. 실제 Gemini 실행 후 `gemini/manifest.json`의 `gemini_execution`에 정확한 모델명, 실행 시각, 응답/로그 해시를 추가합니다. 모델명을 추측해 미리 쓰지 않습니다.
