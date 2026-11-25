# fault - StP - LIGHTKRAVTE 한국어 패치 — 재번역·후속 교정 작업물 (미완성)

**미완성입니다.** 출시된 한국어 패치 v1.0.0 은 따로 있는 저장소 `fault-stp-lightkravte-korean-patch` 에 있다. 이 저장소는 그 뒤에 하다 멈춘 일을 모은 것이다(2026-08-29 ~ 09-08). 게임 폴더와 배포본은 아직 갱신하지 않았다.

## 어디까지 했나
| 갈래 | 상태 |
|---|---|
| 제미나이 재번역(일본어 원문 기준) | 93패킷 **6,746/6,746행 완주**, 기계 검수(구조·정렬·잠긴 고유명사 56·숫자·일본어 잔류·길이비·옛 번역 재사용·열람 범위) 전부 통과 — `gemini-results/` |
| 재번역 → 빌드 | **막힘**: ruby 판정 43행(46태그)이 모두 pending 이라 `finalize_ruby_for_korean.py` 가 출력을 안 만든다. 용어 38개·화자 프로필 22개 pending — `fault-stp-lightkravte-codex-handoff.md` |
| 기존 번역 후속 교정 | 확정 교정 16행 + 09-08 추가 5행·클록스 표기 통일 반영, 재빌드 구조검사 93파일·6,746행 issues 0 — 게임·배포본 미반영(`correction-list-2026-09-03/`, `asset-review-2026-09-04/`) |
| 그림·영상 한국어화 검수 | 09-08 검수 체크포인트(크레딧·OP 등 후보), 완료본 아님 — `asset-review-2026-09-04/production_2026-09-08`, 그림은 `assets-ko/` |

즉 지금 바로 빌드해 깔 수 있는 새 판은 없다. 다음에 할 일: ruby 43행 판정 → 재번역판과 기존판 중 어느 쪽을 반입할지 결정 → 그림 검수 확정 → 빌드·실기 확인.

## 폴더와 원래 위치 (`P:\AI\Codex\projects\` 아래)
`gemini-scenario-kit-2026-08-29/`(재번역 킷: 일본어 원문 패킷·용어·검증기), `gemini-results/`, `gemini-run/`(배급기), `gemini-eval-2026-08-29/`, `quality-comparison-2026-08-30/`, `correction-list-2026-09-03/`, `asset-review-2026-09-04/`, 인계서 `fault-stp-lightkravte-codex-handoff.md`, 프롬프트 `fault-stp-lightkravte-gemini-prompt.md`. 원본 게임 파일은 넣지 않았다.
