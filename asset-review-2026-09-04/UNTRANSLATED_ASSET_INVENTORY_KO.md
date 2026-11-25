# fault - StP - LIGHTKRAVTE 미번역 애셋 검수 목록

작성일: 2026-09-04  
번역 작성: **Codex internal**  
상태: **검수용 초안만 생성. 게임 폴더·배포본에는 아직 반입하지 않음.**

## 1. 먼저 끝낸 대사 교정

- 사용자가 확인한 `status=fix` **16행만** 작업 번역본에 반영했다.
- `optional` 14행과 `hold` 5행은 건드리지 않았다.
- 재빌드 검증: **93파일 / 6,746행 / 누락 0 / 오류 0 / complete=true**.
- 기록: `P:\AI\Codex\projects\_migrated_c_documents_codex\2026-07-25\new-chat\work\localization\reports\codex_confirmed_corrections_2026-09-04.json`

## 2. 독립 애셋 감사 범위

| 범위 | 결과 |
|---|---:|
| Unity 입력 파일 | 16 |
| Unity 오브젝트 | 24,968 |
| Texture2D | 1,226 |
| 렌더·육안 확인한 비폰트 텍스처 | **1,213장 / 26시트** |
| TextAsset | 71 (Spine atlas 54, 관리 문자열 15, 줄바꿈표 2) |
| VideoClip | **11개 전부 확인** |
| OP 세부 확인 | 1초 간격 75프레임 / 9시트 |
| MonoBehaviour | 5,221 (생성 typetree로 5,054 파싱) |
| 이미 번역된 표시 문자열 | 시나리오 6,746 + 관리 문자열 425 |

`MonoBehaviour` 미파싱 167개는 144개 Naninovel 시나리오 직렬화와 23개 관리참조형 설정/UI다. 시나리오는 원본 카탈로그 46개로, 표시 UI는 관리 문자열 425개와 런타임 표시 감사로 별도 교차 확인했다.

## 3. 실제로 한국어판 처리가 필요한 활성 애셋 — 5개

| ID | 애셋 | 노출 | 번역/처리안 |
|---|---|---|---|
| IMG-001 | `sharedassets0.assets` Texture2D 13 `splash_aero_txt_jp` | 시작 연출 | `본 기록은 ALICE IN DISSONANCE가` / `루젠하이드에서 일어난 일을 관찰하고 편집한 것입니다.` |
| IMG-002 | `sharedassets0.assets` Texture2D 21 `AiD_Splash_2022` | 시작 면책문 | `이 이야기는 현재로서는 허구입니다.` / `실존하는 개인 및 단체와는 아직 아무런 관련이 없습니다.` |
| IMG-003 | 주 번들 Texture2D -3364026802204621321 `anime hare` | ch01-02d 크레딧 | `캐릭터 애니메이터` / 이름 보존 |
| IMG-004 | 주 번들 Texture2D 1441106173844391157 `Misaki_C` | ch01-02d 크레딧 | `수석 캐릭터 애니메이터` / 이름 보존 |
| VID-001 | 주 번들 VideoClip 7307858261213983060 `LIGHTKRAVTE_OP_Final_1080` | 오프닝 | 역할명 9블록만 번역, 인명·브랜드 보존 |

### 시작 연출에서 새로 확인한 구조

`splash_aero_txt_x`는 zh-TW 자리가 아니다. `level0`의 GameObject 이름이 **`sa`**이고, `SplashObjectShowWhite` 애니메이션은 `sa → en → jp → zh-CN` 네 표시층을 다룬다. 이 층은 산아리즈타계 가상문자이므로 보존한다.

한국어판에서는 원본 파일을 전역 교체하지 않고 **KoreanActive일 때만 `jp` 표시층을 한국어로 바꾸는 방식**을 제안한다. 다른 언어를 선택하면 원본 텍스처가 그대로 보여야 한다.

## 4. 번역 가능하지만 현재 시나리오에서 미참조 — 4개

| ID | 애셋 | 제안 |
|---|---|---|
| DEAD-IMG-001 | `Dmitry_c` — ENVIRONMENTAL ANIMATION BY | `환경 애니메이션` |
| DEAD-IMG-002 | `Munisix_C` — FAULT SERIES CREATED BY | `fault 시리즈 원작` |
| DEAD-IMG-003 | `Nyantastic_C` — MORALE OFFICERS | `사기 진작 담당` |
| DEAD-DEV-001 | `ev_20 無力なカージ`의 일본어 제작 메모 | 정확한 `ev_20`은 미참조. 노출되면 번역하지 말고 메모 제거 |

미사용 3개 크레딧도 번들 일관성을 위해 같이 한국어화할 수 있으나 런타임 효과는 없다. `ev_20-1`, `ev_20-2` 등 실제 장면과 제작 메모가 든 정확한 `ev_20`은 서로 다른 애셋이다.

## 5. 미번역으로 세지 않는 보존 대상

- `splash_aero_txt_x`, `ev_06-1_read_text_oldbook` 2개, `kenlens_test_text`, `2_think_text`: 작중 가상문자·필기.
- `fault`, `LIGHTKRAVTE`, `ALICE IN DISSONANCE`, `PHOENIXX`, `PROJECT WRITTEN`: 로고/브랜드.
- 크레딧 인명·스튜디오명: 원문 로마자 표기 유지.
- `key_nav_icons`의 W/A/S/D/R/B: 물리 키 표기.
- 나머지 렌더 확인 텍스처: 배경·인물·이펙트·UI 장식으로 번역할 글자 없음.
- 나머지 10개 영상: 장면/타임랩스/효과 또는 로고 영상이며 번역할 문장 없음.
- `LIGHTKRAVTE.exe` VersionInfo: 번역할 제품 설명 문자열 없음. `app.info`는 브랜드명뿐.

## 6. 오프닝 역할명 번역안

| 원문 | 제안 |
|---|---|
| MUSIC BY | 음악 |
| ART ASSISTANCE BY | 아트 지원 |
| MORALE OFFICERS | 사기 진작 담당 |
| LEAD BACKGROUND ARTIST | 수석 배경 아티스트 |
| BACKGROUND ARTISTS | 배경 아티스트 |
| PROGRAMMING BY | 프로그래밍 |
| SCRIPTING BY | 스크립팅 |
| ART DIRECTION BY | 아트 디렉션 |
| WRITTEN AND DIRECTED BY | 각본·감독 |

## 7. 사용자 검수 요청

1. IMG-001 문구 및 **한국어 모드에서 jp층만 조건부 교체** 승인 여부.
2. 면책문 목업: **A(한·영·중 유지)** 또는 **B(한국어만, 권장)**.
3. 크레딧 역할명: 활성 2개와 미사용 3개를 모두 바꿀지.
4. OP 역할명 9개를 영상에 합성할지.
5. 미사용 `ev_20` 제작 메모는 그대로 둘지(권장: 그대로 둠).

승인 전에는 `Y:\GAME\Fault StP LIGHTKRAVTE`와 배포 패키지에 아무 애셋도 넣지 않는다.
