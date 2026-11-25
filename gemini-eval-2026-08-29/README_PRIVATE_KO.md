# v3 상태

현재 키트 `83ffe7c8103dc0a9fc0004877d057500774ddba562aa3a77626e6a27a54458b6`에서는 한국어 보이스 예문이 전부 제거됐다. 따라서 이 폴더의 200개 숨은 대조군은 일반적인 독립 품질 표본으로 계속 쓸 수 있지만, `exposed_example` 대비 복사 탐지 비교는 v1/v2 결과에만 의미가 있다. v3 결과에 노출군-대조군 delta를 복사 증거로 해석하지 않는다.

# Gemini 번역 독립 평가용 비공개 대조군

**이 폴더는 Gemini에 첨부하지 않는다.** 기존 키트 ZIP은 수정하지 않았다.

## 고정 결과

- 숨은 대조군: 200 UID
- 보이스 예문 발생: 224건
- 보이스 예문 고유 UID: 125개
- 대조군과 예문 UID 교집합: 0개
- 기존 키트 ZIP SHA-256: `9be5640b93abe6aa0661c1cc70c6f379bfb5ebf46b89af7444dc65bbda700a82`

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
