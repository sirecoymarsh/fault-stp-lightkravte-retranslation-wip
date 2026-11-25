from pathlib import Path
import json, hashlib, sys
ROOT=Path(__file__).resolve().parent
WORK=Path(r'P:\AI\Codex\projects\_migrated_c_documents_codex\2026-07-25\new-chat\work')
COMPARISON=Path(r'P:\AI\Codex\projects\fault-stp-lightkravte-quality-comparison-2026-08-30\unblinded_results.json')
KIT=Path(r'P:\AI\Codex\projects\fault-stp-lightkravte-gemini-scenario-kit-2026-08-29\gemini')
def load(p): return json.loads(p.read_text(encoding='utf-8-sig'))
old=load(WORK/'localization/build/ko_map.json')
raw={}; scripts={}
for p in sorted((WORK/'script_audit/catalogs/ja').glob('ch*.json')):
    obj=load(p); rows=[]
    for r in obj['records']:
        if r.get('command_type')!='PrintText' or not r.get('text'): continue
        uid=f"{obj['script']}:{r['line_index']}:{r['line_hash']}"
        e=dict(uid=uid,script=obj['script'],line_index=r['line_index'],speaker_id=r.get('author_id',''),printer_id=r.get('printer_id',''),ja=r['text'],existing=old.get(uid,{}).get('ko'))
        rows.append(e); raw[uid]=e
    scripts[obj['script']]=rows
comparison=load(COMPARISON)['entries']
dims=('fidelity','naturalness','directed_voice','no_unsupported_addition')
selected=[e for e in comparison if e['preferred']=='gemini' or any(e['scores']['existing'][d]<=2 for d in dims)]
candidates=[]
for idx,e in enumerate(selected,1):
    r=raw[e['uid']]; seq=scripts[r['script']]; i=next(i for i,v in enumerate(seq) if v['uid']==r['uid'])
    assert r['ja']==e['ja'] and r['existing']==e['existing'], e['uid']
    candidates.append(dict(index=idx,**r,gemini=e['gemini'],previous_preferred=e['preferred'],previous_reason=e['reason_blind'],previous_severity=e['severity'],before=seq[max(0,i-4):i],after=seq[i+1:i+5]))
if len(sys.argv)>1 and sys.argv[1]=='script':
    for s in sys.argv[2:]:
        print('\n### '+s)
        for r in scripts[s]: print(r['uid'],r['speaker_id'],r['printer_id'],'\nJA',r['ja'],'\nKO',r['existing'])
elif len(sys.argv)>1 and sys.argv[1]=='candidates':
    lo=int(sys.argv[2]); hi=int(sys.argv[3])
    for e in candidates[lo-1:hi]:
        print('\n###',e['index'],e['uid'],'speaker',e['speaker_id'],'printer',e['printer_id'])
        for r in e['before']: print('BEFORE',r['uid'],r['speaker_id'],r['ja'])
        print('JA',e['ja'],'\nOLD',e['existing'],'\nGEM',e['gemini'])
        for r in e['after']: print('AFTER',r['uid'],r['speaker_id'],r['ja'])
elif len(sys.argv)>1 and sys.argv[1]=='speaker':
    ids=set(sys.argv[2:])
    for r in raw.values():
        if r['speaker_id'] in ids: print(r['uid'],'JA',r['ja'],'\nKO',r['existing'])
elif len(sys.argv)>1 and sys.argv[1]=='find':
    needles=sys.argv[2:]
    for r in raw.values():
        if any(n in r['ja'] for n in needles): print(r['uid'],r['speaker_id'],'JA',r['ja'],'\nKO',r['existing'])
else:
    (ROOT/'source_context.json').write_text(json.dumps(candidates,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    h=lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    inp=[COMPARISON,WORK/'localization/build/ko_map.json',KIT/'character_voice.json',KIT/'glossary.json',Path(r'P:\AI\Codex\skills\contextual-game-localization\references\translation-quality.md'),Path(r'P:\AI\Codex\skills\contextual-game-localization\references\gemini-translation-kit.md')]+sorted((WORK/'script_audit/catalogs/ja').glob('ch*.json'))
    provenance={'translator_model':'Codex internal','reviewer_model':'Codex internal','exact_model':None,'thread_id':'019f98c4-2d2a-7502-b05c-6a79321fe89e','date':'2026-09-03','scope':'56 follow-up candidates from the prior 200-line comparison; not full-corpus semantic QA','candidate_translation_source':'Japanese original and source context; Gemini text is an untrusted comparison only','source_files_unchanged':True,'input_hashes':{str(p):h(p) for p in inp}}
    (ROOT/'provenance.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('EXTRACTED',len(candidates))
