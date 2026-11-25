from __future__ import annotations
import argparse, difflib, json, re, statistics, unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def load(path): return json.loads(path.read_text(encoding="utf-8"))
def norm(s):
    s = unicodedata.normalize("NFKC", s)
    return "".join(ch for ch in s if not ch.isspace() and not unicodedata.category(ch).startswith("P"))
def ngrams(s, n=3):
    s = norm(s)
    if len(s) < n: return {s} if s else set()
    return {s[i:i+n] for i in range(len(s)-n+1)}
def jaccard(a,b):
    x,y=ngrams(a),ngrams(b)
    return len(x&y)/len(x|y) if x or y else 1.0
def metrics(a,b):
    na,nb=norm(a),norm(b)
    return {"exact": a==b, "normalized_exact": na==nb,
            "sequence_ratio": difflib.SequenceMatcher(None,na,nb).ratio(),
            "trigram_jaccard": jaccard(a,b)}
def summarize(rows):
    if not rows: return {"available":0}
    ratios=[r["sequence_ratio"] for r in rows]; jacs=[r["trigram_jaccard"] for r in rows]
    return {"available":len(rows), "exact_rate":sum(r["exact"] for r in rows)/len(rows),
            "normalized_exact_rate":sum(r["normalized_exact"] for r in rows)/len(rows),
            "sequence_ratio_mean":statistics.mean(ratios), "sequence_ratio_median":statistics.median(ratios),
            "trigram_jaccard_mean":statistics.mean(jacs), "similarity_ge_0_90":sum(x>=.90 for x in ratios)/len(rows),
            "similarity_ge_0_95":sum(x>=.95 for x in ratios)/len(rows)}
def main():
    ap=argparse.ArgumentParser(description="노출 예문군과 숨은 대조군의 Codex 대비 유사도 비교")
    ap.add_argument("results_dir",type=Path)
    ap.add_argument("--out",type=Path,default=ROOT/"similarity_report.json")
    ns=ap.parse_args()
    got={}; errors=[]
    for p in sorted(ns.results_dir.rglob("*.jsonl")):
        for i,line in enumerate(p.read_text(encoding="utf-8-sig").splitlines(),1):
            if not line.strip(): continue
            try: r=json.loads(line)
            except Exception as e: errors.append(f"{p}:{i}: {e}"); continue
            uid=r.get("uid")
            if uid in got: errors.append(f"duplicate uid: {uid}")
            got[uid]=r.get("target_ko","")
    hold=load(ROOT/"private_reference_holdout.json")["entries"]
    exposed=load(ROOT/"private_reference_exposed_examples.json")["entries"]
    details={"holdout":[],"exposed_example":[]}; missing={"holdout":[],"exposed_example":[]}
    for group,refs in [("holdout",hold),("exposed_example",exposed)]:
        for ref in refs:
            if ref["uid"] not in got: missing[group].append(ref["uid"]); continue
            row={"uid":ref["uid"], **metrics(got[ref["uid"]],ref["ko_codex_reference"])}
            details[group].append(row)
    summaries={k:summarize(v) for k,v in details.items()}
    delta={}
    if summaries["holdout"].get("available") and summaries["exposed_example"].get("available"):
        for key in ["exact_rate","normalized_exact_rate","sequence_ratio_mean","trigram_jaccard_mean","similarity_ge_0_90","similarity_ge_0_95"]:
            delta[key]=summaries["exposed_example"][key]-summaries["holdout"][key]
    report={"status":"PASS" if not errors else "RESULT_PARSE_ERRORS", "interpretation":"양의 delta가 크면 예문 노출군의 복사 가능성이 커졌다는 신호다. 단독으로 표절을 확정하지는 않는다.",
            "summaries":summaries,"exposed_minus_holdout":delta,"missing":missing,"errors":errors,"details":details}
    ns.out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k!="details"},ensure_ascii=False,indent=2))
    return 0 if not errors else 1
if __name__=="__main__": raise SystemExit(main())
