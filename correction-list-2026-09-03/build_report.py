from pathlib import Path
from collections import Counter
import copy, hashlib, json, re

ROOT=Path(__file__).resolve().parent
WORK=Path(r"P:\AI\Codex\projects\_migrated_c_documents_codex\2026-07-25\new-chat\work")
def read(p): return json.loads(p.read_text(encoding="utf-8-sig"))
def write(p,x): p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
source_context=read(ROOT/"source_context.json")
decisions=read(ROOT/"decisions.json")
provenance=read(ROOT/"provenance.json")
old=read(WORK/"localization/build/ko_map.json")
raw={}; scripts={}
for path in sorted((WORK/"script_audit/catalogs/ja").glob("ch*.json")):
    obj=read(path); rs=[]
    for r in obj["records"]:
        if r.get("command_type")!="PrintText" or not r.get("text"): continue
        uid=f"{obj['script']}:{r['line_index']}:{r['line_hash']}"
        e={"uid":uid,"script":obj["script"],"line_index":r["line_index"],"speaker_id":r.get("author_id",""),"ja":r["text"],"existing":old[uid]["ko"],"source_hash":r["line_hash"]}
        raw[uid]=e; rs.append(e)
    scripts[obj["script"]]=rs
for d in decisions:
    if d["index"]<=56: continue
    r=raw[d["uid"]]; seq=scripts[r["script"]]; i=next(i for i,x in enumerate(seq) if x["uid"]==r["uid"])
    source_context.append({"index":d["index"],**r,"gemini":None,"previous_preferred":None,"previous_reason":None,"previous_severity":None,"origin":"context_expansion","before":seq[max(0,i-4):i],"after":seq[i+1:i+5]})
by_index={r["index"]:r for r in source_context}
records=[]
for d in decisions:
    r={**by_index[d["index"]],**d}
    r["source_hash"]=r["uid"].rsplit(":",1)[1]
    r["origin"]=r.get("origin","follow_up_of_prior_comparison")
    r["proposed_ko"]=r.get("proposed_ko")
    r["translator_model"]="Codex internal" if r["proposed_ko"] is not None else None
    r["reviewer_model"]="Codex internal"
    r["applied"]=False
    records.append(r)
expected_uids={r["uid"] for r in records}
tags=lambda s: Counter(re.findall(r"<[^>]+>",s))
def validate(rs):
    errors=[]
    ids=[r["uid"] for r in rs]
    if len(ids)!=len(set(ids)): errors.append("duplicate_uid")
    if set(ids)!=expected_uids or len(rs)!=61: errors.append("coverage_mismatch")
    for r in rs:
        uid=r["uid"]
        if uid not in raw: errors.append("unknown_uid"); continue
        if r["ja"]!=raw[uid]["ja"] or r["existing"]!=raw[uid]["existing"]: errors.append("source_mutation:"+uid)
        if r["status"] not in {"fix","optional","hold","keep"}: errors.append("unknown_status:"+uid)
        if not r["reason"].strip(): errors.append("empty_reason:"+uid)
        if r["status"] in {"fix","optional"} and not r.get("proposed_ko"): errors.append("missing_proposal:"+uid)
        if r["status"]=="keep" and r.get("proposed_ko") is not None: errors.append("keep_has_replacement:"+uid)
        if r.get("proposed_ko") is not None:
            if tags(r["proposed_ko"])!=tags(r["existing"]): errors.append("tag_mismatch:"+uid)
            if r["proposed_ko"]==r["existing"]: errors.append("unchanged_proposal:"+uid)
            if r["translator_model"]!="Codex internal": errors.append("missing_authorship:"+uid)
        if r["applied"]: errors.append("unexpected_applied_state:"+uid)
    return errors
healthy=validate(records)
if healthy: raise RuntimeError(healthy)
negative={}
bad=copy.deepcopy(records); bad.append(copy.deepcopy(bad[0]))
negative["duplicate_uid"]=bool(validate(bad))
bad=copy.deepcopy(records); bad[0]["ja"]+="x"
negative["source_mutation"]=bool(validate(bad))
bad=copy.deepcopy(records)
target=next(x for x in bad if x["status"]=="fix" and "<br>" in (x.get("proposed_ko") or ""))
target["proposed_ko"]=target["proposed_ko"].replace("<br>","",1)
negative["missing_protected_tag"]=bool(validate(bad))
assert all(negative.values())
for p,h in provenance["input_hashes"].items():
    assert sha(Path(p))==h, "input changed: "+p
counts=Counter(r["status"] for r in records)
assert counts==Counter(fix=16,optional=14,hold=5,keep=26), counts
term_rows=[r for r in raw.values() if "クロックス" in r["ja"]]
cer_rows=[r for r in raw.values() if r["speaker_id"]=="cer"]
assert len(term_rows)==10 and len(cer_rows)==16
evidence={
"cloqks":{"source_expression":"クロックス","glossary_status_at_review":"pending","glossary_term_id":"TERM-0079","recommended_dialogue_spelling":"클록스","adopted":False,"occurrences":term_rows},
"cer":{"scope":"All 16 cer source lines, all in ch03-10, were read for source register switches. Change only 5 marked-polite lines, not all 16.","proposed_changed_uids":[r["uid"] for r in records if r["speaker_id"]=="cer" and r["status"]=="fix"],"occurrences":cer_rows},
"diary":{"source_ch01_05d":scripts["ch01-05d"],"source_ch01_08d":scripts["ch01-08d"],"ch02_13_register_boundary":[r for r in scripts["ch02-13"] if 38<=r["line_index"]<=66]},
"stammer_scene":[r for r in scripts["ch02-07"] if 35<=r["line_index"]<=43],
"communication_line":[r for r in raw.values() if "通信ライン" in r["ja"]]
}
write(ROOT/"source_evidence.json",evidence)
provenance["follow_up_scope"]={"prior_candidates_rechecked":56,"additional_context_candidates":5,"total":61,"all_prior_semantic_scores_recomputed":False,"source_text_authority":"Japanese raw catalogs","old_map_and_game_modified":False}
write(ROOT/"provenance.json",provenance)
write(ROOT/"correction_candidates.json",{"schema_version":1,"provenance":provenance,"counts":dict(counts),"records":records})
def inline(s): return s.replace("|","\\|").replace("\n"," ").replace("<","&lt;").replace(">","&gt;")
md=["# fault - StP - LIGHTKRAVTE 교정 후보 목록",
"",
"**기존 번역본을 대상으로 한 교정 제안이다. 번역 맵·게임 파일·Gemini 결과에는 반영하지 않았다.**",
"",
"## 범위와 결론",
"",
"- 이전 200행 비교에서 Gemini 우세였던 55행과 기존문 저점 1행을 합친 **56행을 재검토**했다.",
"- 일본어 원본 카탈로그를 직접 읽어 문맥을 확장했고, 세라로의 정중체 전환 4행과 기관명 혼용 1행을 추가했다.",
"- 총 **61행: 우선 교정 16 / 선택 개선 14 / 연계 결정 보류 5 / 유지·제외 26**.",
"- 우선 교정 16행 중 기관명 표기가 걸린 1행은 TERM-0079 확정과 연동한다. 세라로 5행은 한 묶음으로 검토한다.",
"- 제안문은 Codex internal이 일본어 원문을 기준으로 작성했다. Gemini 문장을 자동 채택하지 않았다.",
"- 6,746행 전체 의미 검수나 패치 적용 완료를 뜻하지 않는다. 이번 범위 밖에서 추가 결함이 없다는 판단은 하지 않았다.",
"",
"## 이전 비교에서 바로잡는 점",
"",
"1. ch01-05d는 ‘엄마에게’라고 명시된 기록이다. 두 행의 존댓말을 독백 오류라며 반말로 바꾸려던 판정을 철회한다.",
"2. ぐー→드르렁, ‘생각하기도 전에 몸이 먼저 움직였다’, 이름을 주어로 한 직접 발화, 부친의 -어/-다 혼용을 확정 오역으로 세지 않는다.",
"3. 소네타의 미안함다/물건임다/건투를 빔다, 카지의 더듬음과 리토나의 뭉개진 발화는 인물 기능을 보존한다. 표준어·가독성만을 이유로 평탄화하지 않는다.",
"4. CLOQKS（クロックス）는 현재 용어집에서 **pending**이다. 이전 ‘잠긴 표기 위반’ 설명은 잘못됐다. 실제 문제는 세 가지 표기의 혼용이다.",
"5. 세라로는 원문에서 평체와 정중·겸양체를 오간다. 전 대사를 존댓말로 통일하는 대신, 원문이 정중해지는 5행을 복원한다.",
"",
"이 목록은 교정 여부를 새로 판정한 것이며 이전 200행 승패·점수·p값을 재산정한 보고서가 아니다. 이전의 ‘Gemini 우세 55행’을 곧바로 ‘기존 번역 오류 55건’으로 해석하면 안 된다.",
"",
"## 우선 교정 16행",
"",
"| 번호 | UID | 우선순위 | 유형 | 적용 연동 |",
"|---|---|---|---|---|"]
fixes=[r for r in records if r["status"]=="fix"]
for r in fixes:
    md.append(f"| C{r['index']:02} | {r['uid']} | {r['priority']} | {r['category']} | {r.get('dependency','없음')} |")
for r in fixes:
    md += ["",f"### C{r['index']:02} · {r['uid']} — {r['category']}","",
           f"- 화자: {r['speaker_id'] or '서술/기록'}",
           "- 일본어 원문:","~~~text",r["ja"],"~~~",
           "- 현재 번역:","~~~text",r["existing"],"~~~",
           "- 교정 제안:","~~~text",r["proposed_ko"],"~~~",
           "- 근거: "+r["reason"]]
    if r.get("dependency"): md.append("- 연동: "+r["dependency"])
md += ["","## 선택 개선 14행","",
"의미 오류로 확정하지 않는다. 아래는 읽는 맛·연결·용어 결합을 다듬는 선택지이며, 취향에 따라 기존문을 유지해도 된다.",""]
for r in [x for x in records if x["status"]=="optional"]:
    md += [f"### C{r['index']:02} · {r['uid']}","",
           "- 원문: "+inline(r["ja"]),
           "- 현재: "+inline(r["existing"]),
           "- 제안: "+inline(r["proposed_ko"]),
           "- 판정: "+r["reason"]]
    if r.get("dependency"): md.append("- 연동: "+r["dependency"])
    md.append("")
md += ["## 연계 결정 보류 5행",""]
for r in [x for x in records if x["status"]=="hold"]:
    md += [f"### C{r['index']:02} · {r['uid']} — {r['category']}","",
           "- 원문: "+inline(r["ja"]),
           "- 현재: "+inline(r["existing"]),
           "- 보류 이유: "+r["reason"],
           "- 다음 단계: "+r["next_action"]]
    if r["proposed_ko"] is not None: md += ["- **미승인 조건부 안:** "+inline(r["proposed_ko"])]
    md.append("")
md += ["## 유지 / 이전 지적 제외 26행","","| 번호 | UID | 유지 근거 |","|---|---|---|"]
for r in [x for x in records if x["status"]=="keep"]:
    md.append(f"| C{r['index']:02} | {r['uid']} | {inline(r['reason'])} |")
md += ["","## 연계 검토 범위","","### 기관명 표기",
"원문 クロックス는 10행이다. 현재 번역에는 클록스, CLOQKS(클록스), CLOQKS가 섞여 있다. 대사 표기는 **클록스**로 통일하는 방향을 제안하되 현재 pending을 임의로 locked로 바꾸지는 않았다.",""]
for r in term_rows: md.append(f"- {r['uid']}: {inline(r['existing'])}")
md += ["","### 세라로의 말투","16행 전 발생을 읽었다. ありましてね / ですか / 拝見させていただきましたよ / 入りましょうか / お時間頂きますよ가 있는 5행만 교정 대상으로 삼고, 나머지 11행은 일괄 존댓말화하지 않는다.","",
"### 보호 태그와 ruby","제안문은 현재 기존 번역의 br, tip, ruby 태그 다중집합을 그대로 유지한다. ruby를 strip/keep/manual로 판정한 것이 아니며, 이번 목록은 ruby 최종 승인과 폰트·런타임 검증을 대신하지 않는다.","",
"## 파일과 출처",""]
for name in ["correction_candidates.json","source_evidence.json","decisions.json","provenance.json","VALIDATION_REPORT.json","SHA256SUMS.txt"]:
    md.append("- "+str(ROOT/name))
(ROOT/"CORRECTION_LIST_KO.md").write_text("\n".join(md)+"\n",encoding="utf-8")
validation={"status":"PASS","scope":"New correction-list structural integrity only; not previously passed 6,746-line gates and not an automated semantic judgment","records":61,"counts":dict(counts),"proposals":sum(r["proposed_ko"] is not None for r in records),"input_hashes_unchanged":len(provenance["input_hashes"]),"protected_tag_multisets":"unchanged relative to existing text for all proposed replacements","negative_tests":negative,"applied_to_translation_map":False,"applied_to_game":False}
write(ROOT/"VALIDATION_REPORT.json",validation)
paths=sorted(p for p in ROOT.iterdir() if p.is_file() and p.name!="SHA256SUMS.txt")
(ROOT/"SHA256SUMS.txt").write_text("".join(f"{sha(p)}  {p.name}\n" for p in paths),encoding="utf-8")
print(json.dumps(validation,ensure_ascii=False,indent=2))

