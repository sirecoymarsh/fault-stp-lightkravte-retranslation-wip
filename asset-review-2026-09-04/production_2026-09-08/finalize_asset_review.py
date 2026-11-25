"""Persist reviewed verdicts and a user-review checkpoint, never a release."""
from pathlib import Path
from datetime import datetime, timezone
import json, hashlib, shutil, html
from PIL import Image

ROOT=Path(r'P:\AI\Codex\projects\fault-stp-lightkravte-asset-review-2026-09-04')
OUT=ROOT/'production_2026-09-08'
LOC=Path(r'P:\AI\Codex\projects\_migrated_c_documents_codex\2026-07-25\new-chat\work\localization')
CAND=Path(r'P:\AI\Codex\projects\fault-stp-lightkravte-correction-list-2026-09-03\correction_candidates.json')
VERDICTS={
 'anime_dmitry':('FAIL_CLEAN_PLATE','x240~940,y40~115: 매끈한 회보라 패치·세로 경계 반복. 원문 V 위치에 큰 패치.'),
 'anime_hare':('BLOCKED_NO_CLEAN_PLATE','흰 영문 잔재는 없지만 x580~650,y40~90 상단 붓 가장자리에 각진 홈·선형 이음. 승인 보류.'),
 'Dmitry_c':('FAIL_CLEAN_PLATE','역할문 x70~1020,y21~68 및 인명 x68~960,y93~167: 글자 모양 밝기 얼룩·사각 격자.'),
 'Kawamura_C':('FAIL_CLEAN_PLATE','x300~1060,y42~117: 넓은 단색 패치, 검은 삼각 홈, 각진 결합부.'),
 'Misaki_C':('FAIL_CLEAN_PLATE','x95~935,y160~234: EYMARD 자리에 큰 획 형태의 밝은 패치·반복 결. 역할문 수평 복제 흔적.'),
 'Munisix_C':('FAIL_CLEAN_PLATE','x355~373,y105~146: 작은 검은 삼각형 반복. 역할문·인명에 가는 수평선.'),
 'Nyantastic_C':('BLOCKED_NO_CLEAN_PLATE','흰 영문 잔재는 없지만 x200~278,y53~87 상단 평행 홈과 하단 채움 경계가 인위적. 승인 보류.'),
 'Oda_C':('FAIL_CLEAN_PLATE','x478~580,y30~104: IS 주변 사각 구멍·단색 패치, 붓결 연결 끊김.'),
 'Sakamoto_c':('FAIL_RESIDUE','x162~542,y118~166: PHOENIXX 로고가 아닌 인명 자리의 밝은 영문 조각 345픽셀 잔존.'),
 'splash_aero_txt_jp':('PASS_STATIC_VISUAL','일본어 잔재·한국어 잘림 없음. 투명 글자층의 두 줄 문구 검수 통과. 실기 미검증.'),
 'AiD_Splash_2022':('PASS_STATIC_VISUAL','일반 밝기에서 원문 세 언어 잔재·한국어 잘림 없음. 어두운 실루엣의 글자 아래 부분은 추정 복원이며 원본 픽셀 회수는 아님. 실기 미검증.'),
}
OP_NOTES={
 'music':'대표 프레임에 부분 패치 흔적. 전체 출현·소멸 프레임 미생성.',
 'art_assist':'YAE 원문 일부가 마스크에서 누락되어 잔존. 초점이 다른 donor 사용.',
 'morale':'원문 조각 잔존. donor에 표시 중인 글자 또는 다른 배경이 섞임.',
 'lead_background':'배경 정합 실패(4 inliers); 검은 글자형 패치.',
 'background':'배경 정합 실패(4 inliers); 원문 모양의 패치.',
 'programming':'배경 정합 실패(0 inliers); 어두운 글자형 패치.',
 'scripting':'배경 정합 실패(0 inliers); 글자형 패치.',
 'art_direction':'대표 프레임만 양호. 전체 프레임·출현/소멸 애니메이션 미검증.',
 'director':'건물의 밝은 부분이 글리프로 오검출돼 마스크·타깃 크기 오류.',
}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def esc(s):return html.escape(str(s))

def main():
 now=datetime.now(timezone.utc).isoformat()
 m=json.loads((OUT/'texture_manifest.json').read_text('utf-8'))
 prefabs=json.loads((ROOT/'credit_prefab_inventory.json').read_text('utf-8'))
 reviewdir=OUT/'user_review';reviewdir.mkdir(exist_ok=True)
 ledger=[]
 for a in m['assets']:
  status,note=VERDICTS[a['name']]
  a.update(visual_status=status,visual_note_ko=note,visual_reviewed_at=now,visual_reviewer='Codex internal: primary + read-only raster_review',user_approval='PENDING',release_ready=False,runtime_status='NOT_RUN',clean_plate_reviewed_sha256=sha(OUT/'textures'/a['name']/'clean_plate.png'))
  a['consumer_references']=[p for p in prefabs if any(s['texture_path_id']==a['path_id'] for s in p['sprites'])]
  a['scenario_referenced']=a['name'] not in ('Dmitry_c','Munisix_C','Nyantastic_C')
  if status=='PASS_STATIC_VISUAL':
   dest=reviewdir/a['name'];dest.mkdir(exist_ok=True)
   for fn in ('source.png','clean_plate.png','korean_layer.png','ko.png','comparison.png','source_glyph_mask.png'):shutil.copy2(OUT/'textures'/a['name']/fn,dest/fn)
   im=Image.open(dest/'ko.png').convert('RGBA');bg=Image.new('RGBA',im.size,(0,0,0,255));bg.alpha_composite(im);bg.convert('RGB').save(dest/'preview_black.png')
  else:
   write(OUT/'textures'/a['name']/'NOT_FOR_BUILD.json',{'status':status,'reason':note,'release_ready':False})
  ledger.append({k:a[k] for k in ['name','path_id','width','height','source_sha256','output_sha256','visual_status','visual_note_ko','scenario_referenced','lines','release_ready','runtime_status','user_approval']})
 m['delivery']='Review checkpoint only. No game-ready archive or installer. Failed assets excluded from user_review.'
 write(OUT/'texture_manifest.json',m)
 op=json.loads((OUT/'op/reference_manifest.json').read_text('utf-8'))
 op.update(status='BLOCKED_NO_CLEAN_PLATE_AND_STATE_CLOSURE',full_video_generated=False,runtime_status='NOT_RUN',release_ready=False)
 for g in op['groups']:
  g.update(status='BLOCKED_STATE_CLOSURE' if g['id'] in ('music','art_direction') else 'FAIL_REFERENCE_FRAME',note_ko=OP_NOTES[g['id']],release_ready=False)
 write(OUT/'op/reference_manifest.json',op)
 write(OUT/'op/NOT_FOR_BUILD.json',{'status':op['status'],'full_video_generated':False,'reason':'대표 프레임 진단 시안뿐이며 전체 영상이 아님. 원문 제거·배경 정합·애니메이션 미완성.'})
 ledger.append({'name':'LIGHTKRAVTE_OP_Final_1080','path_id':7307858261213983060,'width':1920,'height':1080,'frames':1792,'fps':24,'source_sha256':op['source_sha256'],'groups':op['groups'],'visual_status':op['status'],'release_ready':False,'runtime_status':'NOT_RUN'})
 write(OUT/'asset_localization_ledger.json',{'created_at':now,'translator_model':'Codex internal','thread_id':'019f98c4-2d2a-7502-b05c-6a79321fe89e','scope':'11 texture targets (8 scenario-referenced, 3 unreferenced credits) + 1 OP with 9 credit groups. People names transliterated per user; brands preserved.','phonetic_name_status':'Proposed Hangul readings; not a claim of official Korean spellings.','assets':ledger,'preserved':['ALICE IN DISSONANCE','fault / LIGHTKRAVTE logos','PHOENIXX INC','PROJECT WRITTEN','STUDIO FUJI','FOXTAIL-GRASS STUDIO','fictional-language surfaces incl splash_aero_txt_x / sa','physical key labels','unreferenced ev_20 development note'],'prior_inventory':str(ROOT/'UNTRANSLATED_ASSET_INVENTORY.json')})
 # Persist independently reviewed scope, not a blanket 6,746-line quality claim.
 s=json.loads((LOC/'source_index.json').read_text('utf-8'));idx={r['uid']:i for i,r in enumerate(s)}
 candidates=json.loads(CAND.read_text('utf-8'))['records'];reviewed=set()
 for c in candidates:
  i=idx[c['uid']];reviewed.update(r['uid'] for r in s[max(0,i-3):i+4])
 assert len(reviewed)==401
 reviewed.update(r['uid'] for r in s if 'クロックス' in r['ja'] or '通信ライン' in r['ja'] or r['script']=='ch01-08d' or r['speaker_id']=='cer')
 assert len(reviewed)==422
 current=json.loads((LOC/'build/ko_map.json').read_text('utf-8'))
 write(OUT/'semantic_review_scope.json',{'reviewer':'Codex internal / read-only review_61','method':'61 candidate UIDs +/-3 source_index rows =401; union クロックス/通信ライン/ch01-08d/speaker cer =422; Japanese and speaker cross-checked against original JA catalogs by reviewer.','candidate_count':61,'reviewed_uid_count':len(reviewed),'corpus_uid_count':6746,'not_reviewed_count':6746-len(reviewed),'source_index_sha256':sha(LOC/'source_index.json'),'current_ko_map_sha256':sha(LOC/'build/ko_map.json'),'uids':[r['uid'] for r in s if r['uid'] in reviewed]})
 fix=json.loads((OUT/'codex_reviewed_followup_2026-09-08.json').read_text('utf-8'))
 for c in fix['corrections']:assert current[c['uid']]['ko']==c['after']
 validation=json.loads((LOC/'reports/validation_all.json').read_text('utf-8'))
 write(OUT/'verification_summary.json',{'created_at':now,'translator_model':'Codex internal','current_ko_map_sha256':sha(LOC/'build/ko_map.json'),'current_scenario_entries':len(current),'structural_validation_complete':validation['complete'],'structural_issues':validation['issues'],'warning_counts':{k:len(v) for k,v in validation['warnings'].items()},'source_review':{'candidate_rows':61,'contextual_unique_uids':422,'not_full_semantic_review':True},'followup_read_only_verification':{'backup_to_current_map_changed_uids':5,'built_script_changes_verified':5,'previous_fixes_retained':16,'cloqks_occurrences_verified':10},'raster_review':{'static_visual_pass':2,'fail':7,'needs_review':2,'all_credits_blocked':9},'video_review':{'reference_groups':9,'full_video_generated':False},'game_installed':False,'git_published':False,'user_review_pending':True})
 report='''# 재개 작업 결과 — 사용자 검수용 (2026-09-08)

**완료본이 아니라 검수 체크포인트입니다. 게임 폴더와 배포본은 변경하지 않았습니다.**

## 대사

- 기존 Codex 번역본을 유지하고 추가 **5행**을 교정·재빌드했습니다. Gemini 완성본을 통째로 반입한 것이 아닙니다.
- 기관명 `クロックス` 10행의 표기를 **클록스**로 통일했습니다. 혼용 3행만 수정했고 `클, 클록스`의 말더듬은 보존했습니다.
- `통신 라인을 맺으셨죠??` → `통신 라인은 연결해 두셨죠??`; 이어지는 답변도 `맺기는 했지만` → `연결하긴 했지만`으로 함께 바꿨습니다.
- 이전 확정 교정 16행은 전부 유지했습니다. 현재 작업 맵과 이전 백업의 차이는 정확히 5 UID이며 빌드된 스크립트에도 5/5 반영됐습니다.
- 재빌드 구조검사: **93파일·6,746행·issues 0·complete=true**. 의도된 ruby 제거·문장부호 원문 동일·강조점 ruby 등의 경고는 별도 기록이며 경고 0이라는 뜻은 아닙니다.
- 이번 의미 검수: 후보 **61행**과 주변 문맥 등 **422개 고유 UID**. **6,746행 전량 의미 검수 완료가 아닙니다.**
- 백업: `'''+str(LOC/'backups/2026-09-08-reviewed-followup')+'''`

## 미번역 애셋

인명 독음 추가 요청을 반영한 현재 범위는 **텍스처 11개(활성 8·미참조 크레딧 3) + OP 영상 1개(크레딧 9구간)**입니다. 예전 인벤토리의 “인명 보존/활성 5개” 기준을 이 목록이 대체합니다.

### 사용자에게 보여드릴 수 있는 화면 2개

1. 시작 기록문: `본 기록은 ALICE IN DISSONANCE가` / `루젠하이드에서 일어난 일을 관찰하고 편집한 것입니다.`
2. 면책문 B안: `이 이야기는 현재로서는 허구입니다.` / `실존하는 개인 및 단체와는 아직 아무런 관련이 없습니다.`

원본 크기·글자 영역 밖 픽셀 동일·잘림 검사를 통과했고, 원문과 한국어를 독립 시각 검수했습니다. 두 화면은 **정적 시각 검수 통과**이며 사용자 승인·KoreanActive 조건부 교체·실기 검증은 남아 있습니다. 면책문 글자 아래의 어두운 실루엣은 주변으로 복원한 부분이지 원래 가려졌던 픽셀을 회수한 것은 아닙니다.

### 반입하지 않은 크레딧 9개와 OP

크레딧은 7개 불합격·2개 승인 보류입니다. 흰 영문을 제거했어도 알파 복원에서 글자 모양 얼룩·격자·단색 패치가 생깁니다. Sakamoto 인명에는 실제 흰 조각도 남습니다. **크기와 픽셀 차이 검사만 통과했다고 완성품으로 내보내지 않았습니다.**

OP는 대표 프레임 9구간 진단 시안만 만들었습니다. 초점·카메라 차이와 글리프 오검출로 원문 잔재와 패치가 남아 전체 영상은 만들지 않았습니다. `ko.png`는 완성 영상이나 반입 승인 파일이 아닙니다.

보류 기준: `P:\\AI\\Codex\\skills\\contextual-game-localization\\SKILL.md`의 래스터 계약을 적용했습니다. 상세 규칙은 `references\\raster-asset-geometry-contract.md` §3의 “패치·번짐·비슷한 생성 배경을 clean plate로 인정하지 않고, 근거 있는 복원이 없으면 원본을 유지하고 blocked로 보고”입니다. 현재 붓결이 깨졌다는 판정은 실제 합성판을 본 두 검수자의 판단입니다.

다음 필요 작업: 글자 없는 원본 붓 레이어/PSD 또는 같은 붓의 검증 가능한 대응 영역 확보 → 크레딧 clean plate 재제작. OP는 무자막 마스터나 검증 가능한 동일 장면 프레임 정합이 필요합니다. 대사 전량 의미 검수와 실제 런타임 검증도 아직 남아 있습니다.

## 파일 구분

- `index.html`: 화면별 검수판과 교정 내역. 먼저 열 파일.
- `user_review/`: 정적 시각 검수를 통과한 시작 화면 2개만. 설치 패키지 아님.
- `textures/`: 원본/마스크/배경 복원/한국어 레이어/합성 시안. 불합격 폴더는 NOT_FOR_BUILD.json 표시.
- `op/`: 대표 프레임 진단 시안. NOT_FOR_BUILD.json 표시.
- `asset_localization_ledger.json`: 변경 대상·보존 대상·한국어 문구·판정.
- `semantic_review_scope.json`: 이번 의미 검수 UID 422개.
- `codex_reviewed_followup_2026-09-08.json`: 5행의 일본어·수정 전후·근거·백업 해시.
- `verification_summary.json`: 완료와 미완료를 분리한 검증 요약.

번역·표기 작성: **Codex internal**. 인명은 제안 독음이며 공식 한국어 표기 검증을 주장하지 않습니다. 외부 번역 모델은 사용하지 않았습니다.
'''
 (OUT/'REVIEW_KO.md').write_text(report,encoding='utf-8')
 sections=[]
 for a in sorted(m['assets'],key=lambda a:(not a['visual_status'].startswith('PASS'),a['name'])):
  ok=a['visual_status'].startswith('PASS');cls='pass' if ok else 'fail'
  lines=a['lines'];rows=[]
  for l in lines:
   if isinstance(l,str):rows.append('<li>'+esc(l)+'</li>')
   else:rows.append('<li>'+esc(l['source'])+' → <b>'+esc(l['ko'] if l['ko'] is not None else '원문 보존')+'</b></li>')
  sections.append(f'<section><h2>{esc(a["name"])} <span class="{cls}">{esc(a["visual_status"])}</span></h2><p>{esc(a["visual_note_ko"])}</p><ul>{"".join(rows)}</ul><p>{a["width"]}×{a["height"]} · 영역 밖 변경 {a["outside_owned_pixel_diff"]} px · 실기 미검증 · 사용자 승인 대기</p><a href="textures/{a["name"]}/comparison.png"><img loading="lazy" src="textures/{a["name"]}/comparison.png" alt="원본 / 배경 복원 / 한국어 비교"></a></section>')
 rows=''.join('<tr><td>'+esc(c['uid'])+'</td><td>'+esc(c['ja'])+'</td><td>'+esc(c['before'])+'</td><td>'+esc(c['after'])+'</td></tr>' for c in fix['corrections'])
 page='''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>LIGHTKRAVTE 한국어화 검수</title><style>body{margin:36px auto;max-width:1250px;padding:0 24px;background:#111317;color:#eceef2;font:16px/1.65 "Malgun Gothic",sans-serif}h1,h2{line-height:1.3}section{margin:30px 0;padding:22px;border:1px solid #38404e;border-radius:12px}img{max-width:100%;height:auto;background:#18181b}a{color:#9bc9ff}.pass{color:#85dab1}.fail{color:#ffae9c}span{font-size:14px}table{border-collapse:collapse;width:100%;font-size:13px}td,th{border:1px solid #465064;padding:12px;vertical-align:top}td{overflow-wrap:anywhere}.banner{background:#263348;padding:18px;border-radius:8px}</style><h1>LIGHTKRAVTE 한국어화 검수</h1><div class="banner"><b>정적 시각 검수 통과 2개 · 크레딧 9개 반입 보류 · OP 미완성</b><br>이 자료는 설치 패키지가 아닙니다. 게임 폴더 미변경. 실패 시안은 상태를 명시해 별도 표시합니다.</div><p><a href="REVIEW_KO.md">상세 보고서</a> · <a href="asset_localization_ledger.json">전체 애셋 장부</a> · <a href="verification_summary.json">검증 요약</a></p><h2>대사 추가 교정 5행</h2><p>이전 교정 16행 유지. 후보61 + 문맥 422UID 독립 검수. 전량 6,746행 의미 검수 완료를 뜻하지 않습니다.</p><table><tr><th>UID</th><th>일본어</th><th>수정 전</th><th>수정 후</th></tr>'''+rows+'</table>'+''.join(sections)+'''<section><h2>OP 영상 — 반입 불가</h2><p>9개 구간의 대표 프레임만 처리한 실패/진단 시안입니다. 전체 영상 생성과 애니메이션 검증은 하지 않았습니다.</p><a href="op/reference_manifest.json">구간별 문구·실패 원인</a><br><a href="op/credit_crop_comparison.png"><img loading="lazy" src="op/credit_crop_comparison.png" alt="오프닝 대표 프레임 진단 비교, 반입 금지"></a></section></html>'''
 (OUT/'index.html').write_text(page,encoding='utf-8')
 shutil.copy2(__file__,OUT/Path(__file__).name)
 write(reviewdir/'REVIEW_ONLY.json',{'translator_model':'Codex internal','status':'USER_REVIEW_PENDING','release_ready':False,'files':[{ 'path':str(p.relative_to(reviewdir)), 'sha256':sha(p)} for p in sorted(reviewdir.rglob('*.png'))]})
 (OUT/'REVIEW_SHA256SUMS.txt').write_text(''.join(f'{sha(p)}  {p.relative_to(OUT).as_posix()}\n' for p in sorted([OUT/'index.html',OUT/'REVIEW_KO.md',OUT/'asset_localization_ledger.json',OUT/'verification_summary.json',OUT/'semantic_review_scope.json',OUT/'texture_manifest.json',OUT/'op/reference_manifest.json']+list(reviewdir.rglob('*.png')))),encoding='utf-8')
 print(json.dumps({'index':str(OUT/'index.html'),'static_visual_pass':2,'credits_blocked':9,'op_full_video':False,'additional_corrections':5,'reviewed_uids':422},ensure_ascii=False))

if __name__=='__main__':main()
