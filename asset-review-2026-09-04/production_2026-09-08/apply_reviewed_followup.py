"""Apply five source-reviewed corrections; no game or Gemini-result writes."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, shutil, re

LOC=Path(r'P:\AI\Codex\projects\_migrated_c_documents_codex\2026-07-25\new-chat\work\localization')
OUT=Path(r'P:\AI\Codex\projects\fault-stp-lightkravte-asset-review-2026-09-04\production_2026-09-08')
BACKUP=LOC/'backups/2026-09-08-reviewed-followup'
FIXES={
 'ch01-04:246:a65ec2e':('부, 불러 보시는 건 어떨까요?<br>통신 라인을 맺으셨죠??','부, 불러 보시는 건 어떨까요?<br>통신 라인은 연결해 두셨죠??','통신 라인과 결합하는 서술어를 연결로 통일. 카지→미샤의 존대와 말더듬 유지.'),
 'ch01-04:249:b28ccba8':('아니… 맺기는 했지만 이런 일로<br>콜을 걸 만큼 친한 사이는 아니라서.','아니… 연결하긴 했지만 이런 일로<br>콜을 걸 만큼 친한 사이는 아니라서.','바로 앞 질문의 結んでる를 받아 답하는 문답의 용어를 함께 수정. 미샤→카지의 반말 유지.'),
 'ch01-11:575:9b4ab831':('게다가 리그스 씨도 미샤 씨도<br>CLOQKS(클록스) 학생이시죠?','게다가 리그스 씨도 미샤 씨도<br>클록스 학생이시죠?','일본어 クロックス의 동일 기관명 표기 통일. 원문에 없는 로마자 병기 제거.'),
 'ch02-01:421:90434ee8':('라인바스타의 스승이라면… CLOQKS(클록스) 학원의<br>로아 리드사이드 선생님 아니에요?','라인바스타의 스승이라면… 클록스 학원의<br>로아 리드사이드 선생님 아니에요?','일본어 クロックス의 동일 기관명 표기 통일. 원문에 없는 로마자 병기 제거.'),
 'ch03-02:206:a28605e0':('그야, 나도 이래 봬도<br>CLOQKS 고등학원 학생인 모양이니까.','그야, 나도 이래 봬도<br>클록스 고등학원 학생인 모양이니까.','일본어 クロックス의 동일 기관명 표기 통일. 서술어와 인물 말투는 변경하지 않음.'),
}

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 source=json.loads((LOC/'source_index.json').read_text('utf-8'))
 si={r['uid']:r for r in source}
 parsed={p:[json.loads(l) for l in p.read_text('utf-8').splitlines() if l.strip()] for p in (LOC/'translations_ko').glob('ch0*/*.jsonl')}
 idx={r['uid']:(p,r) for p,rows in parsed.items() for r in rows}
 assert len(idx)==6746
 changes={};log=[]
 for uid,(before,after,reason) in FIXES.items():
  p,r=idx[uid]
  if r['ko'] not in (before,after):raise RuntimeError('Stale correction '+uid)
  assert re.findall(r'<[^>]+>',before)==re.findall(r'<[^>]+>',after)
  log.append({'uid':uid,'ja':si[uid]['ja'],'speaker_id':si[uid]['speaker_id'],'before':before,'after':after,'reason':reason,'state':'applied' if r['ko']==before else 'already_applied'})
  if r['ko']==before:
   lines=changes.setdefault(p,p.read_text('utf-8').splitlines(keepends=True))
   for i,l in enumerate(lines):
    if l.strip() and json.loads(l).get('uid')==uid:
     rr=json.loads(l);rr['ko']=after
     lines[i]=json.dumps(rr,ensure_ascii=False,separators=(',',':'))+'\n'
  r['ko']=after
 # Freeze the source alias rather than allowing Roman-only spelling in dialogue.
 tp=LOC/'terminology.json';term=json.loads(tp.read_text('utf-8'))
 for e in term['entries']:
  if e['ja']=='CLOQKS（クロックス）':
   e['ko']='클록스';e['source_variants']=['クロックス','CLOQKS（クロックス）']
   e['note']='2026-09-08: 일본어 시나리오 クロックス 10행은 클록스로 통일. ロ마자 병기나 CLOQKS 단독 대사 표기를 만들지 않음.'.replace('ロ마자','로마자')
   e['translator_model']='Codex internal'
 changes[tp]=[json.dumps(term,ensure_ascii=False,indent=2)+'\n']
 gp=LOC/'glossary.md';g=gp.read_text('utf-8')
 g=g.replace('| CLOQKS（クロックス） | CLOQKS(클록스) | CLOQKS | `tip:cloqks` |','| CLOQKS（クロックス） / クロックス | 클록스 | CLOQKS | `tip:cloqks`; 시나리오 10행 통일(2026-09-08) |')
 changes[gp]=[g]
 # Preflight everything before the first write. Backups are never overwritten.
 for p in list(changes)+[LOC/'build/ko_map.json',LOC/'build/manifest.json']:
  dst=BACKUP/p.relative_to(LOC);dst.parent.mkdir(parents=True,exist_ok=True)
  if p.exists() and not dst.exists():shutil.copy2(p,dst)
 hashes=[]
 for p,lines in changes.items():
  pre=sha(p);p.write_text(''.join(lines),encoding='utf-8',newline='')
  hashes.append({'path':str(p),'before_sha256':pre,'after_sha256':sha(p)})
 occurrences=[{'uid':r['uid'],'ja':r['ja'],'ko':idx[r['uid']][1]['ko']} for r in source if 'クロックス' in r['ja']]
 assert len(occurrences)==10
 assert all('클록스' in r['ko'] and 'CLOQKS' not in r['ko'] for r in occurrences)
 report={'created_at':datetime.now(timezone.utc).isoformat(),'translator_model':'Codex internal','thread_id':'019f98c4-2d2a-7502-b05c-6a79321fe89e','scope':'Existing Codex Korean baseline; five corrections only. No Gemini adoption, no game installation.','backup':str(BACKUP),'corrections':log,'files':hashes,'cloqks_occurrences':occurrences}
 dest=LOC/'reports/codex_reviewed_followup_2026-09-08.json'
 dest.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 shutil.copy2(dest,OUT/dest.name);shutil.copy2(__file__,OUT/Path(__file__).name)
 print(json.dumps({'report':str(dest),'corrections':len(log),'cloqks_occurrences':len(occurrences)},ensure_ascii=False))

if __name__=='__main__':main()
