from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path


WORK = Path(r"P:\AI\Codex\projects\_migrated_c_documents_codex\2026-07-25\new-chat\work")
RESULTS = Path(r"P:\AI\Codex\projects\fault-stp-lightkravte-gemini-results")
KIT = Path(r"P:\AI\Codex\projects\fault-stp-lightkravte-gemini-scenario-kit-2026-08-29")
OUT = Path(r"P:\AI\Codex\projects\fault-stp-lightkravte-quality-comparison-2026-08-30")
SEED = "fault-lightkravte-blind-comparison-v1-2026-08-30"
REPRESENTATIVE_N = 150
RISK_N = 50
TAG_RE = re.compile(r"<[^>]+>")


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def stable(text: str) -> int:
    return int(hashlib.sha256((SEED + "\0" + text).encode("utf-8")).hexdigest(), 16)


def visible(text: str) -> str:
    return TAG_RE.sub("", text).strip()


def norm(text: str) -> str:
    return re.sub(r"[\s\W_]+", "", visible(text), flags=re.UNICODE)


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, norm(a), norm(b)).ratio()


def independent_catalog_extract():
    """Read raw catalog records directly; do not use the run harness or source_index context."""
    rows = []
    by_script = {}
    catalog_hashes = {}
    cat_dir = WORK / "script_audit" / "catalogs" / "ja"
    for path in sorted(cat_dir.glob("ch*.json")):
        obj = load(path)
        script = obj["script"]
        records = obj["records"]
        visible_records = []
        for rec in records:
            if rec.get("command_type") != "PrintText" or not rec.get("text"):
                continue
            uid = f'{script}:{rec["line_index"]}:{rec["line_hash"]}'
            item = {
                "uid": uid,
                "script": script,
                "line_index": rec["line_index"],
                "source_hash": rec["line_hash"],
                "speaker_id": rec.get("author_id", ""),
                "printer_id": rec.get("printer_id", ""),
                "ja": rec["text"],
            }
            rows.append(item)
            visible_records.append(item)
        by_script[script] = visible_records
        catalog_hashes[path.name] = sha(path)
    return rows, by_script, catalog_hashes


def load_gemini():
    result = {}
    source_file = {}
    for path in sorted(RESULTS.rglob("*.ko.jsonl")):
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            result[rec["uid"]] = rec
            source_file[rec["uid"]] = path.relative_to(RESULTS).as_posix()
    return result, source_file


def distribute(rows_by_script, target):
    scripts = sorted(rows_by_script)
    quota = {s: min(3, len(rows_by_script[s])) for s in scripts}
    left = target - sum(quota.values())
    cap = {s: len(rows_by_script[s]) - quota[s] for s in scripts}
    total = sum(cap.values())
    raw = {s: left * cap[s] / total for s in scripts}
    for s in scripts:
        add = min(cap[s], math.floor(raw[s]))
        quota[s] += add
    left = target - sum(quota.values())
    for s in sorted(scripts, key=lambda x: (-(raw[x] - math.floor(raw[x])), stable("quota:" + x))):
        if not left:
            break
        if quota[s] < len(rows_by_script[s]):
            quota[s] += 1
            left -= 1
    if left:
        raise RuntimeError("quota allocation failed")
    return quota


def choose_representative(rows_by_script, quota):
    chosen = []
    for script in sorted(rows_by_script):
        pool = rows_by_script[script]
        max_pos = max(1, len(pool) - 1)
        selected = []
        speakers = Counter()
        lengths = Counter()
        quartiles = Counter()
        exacts = Counter()
        while len(selected) < quota[script]:
            best = None
            best_key = None
            for i, row in enumerate(pool):
                if row in selected:
                    continue
                speaker = row["speaker_id"] or "<narration>"
                n = len(visible(row["ja"]))
                lb = "short" if n <= 12 else "medium" if n <= 32 else "long"
                q = min(3, int(i / max_pos * 4))
                ex = "same" if row["same_target"] else "different"
                coverage = (
                    9 * (speakers[speaker] == 0)
                    + 6 * (quartiles[q] == 0)
                    + 4 * (lengths[lb] == 0)
                    + 2 * (exacts[ex] == 0)
                    - 2 * speakers[speaker]
                )
                key = (coverage, -stable("rep:" + row["uid"]))
                if best_key is None or key > best_key:
                    best, best_key = row, key
            selected.append(best)
            speaker = best["speaker_id"] or "<narration>"
            n = len(visible(best["ja"]))
            lb = "short" if n <= 12 else "medium" if n <= 32 else "long"
            i = pool.index(best)
            q = min(3, int(i / max_pos * 4))
            ex = "same" if best["same_target"] else "different"
            speakers[speaker] += 1
            lengths[lb] += 1
            quartiles[q] += 1
            exacts[ex] += 1
        chosen.extend(selected)
    return chosen


def main():
    raw_rows, raw_by_script, catalog_hashes = independent_catalog_extract()
    gemini, result_files = load_gemini()
    existing = load(WORK / "localization" / "build" / "ko_map.json")

    raw_by_uid = {r["uid"]: r for r in raw_rows}
    # This is extraction provenance, not a rerun of the already-passed result harness.
    missing = [uid for uid in gemini if uid not in raw_by_uid]
    if missing:
        raise RuntimeError(f"raw-catalog extraction cannot resolve {len(missing)} Gemini UIDs")

    enriched_by_script = defaultdict(list)
    for script, rows in raw_by_script.items():
        for i, row0 in enumerate(rows):
            uid = row0["uid"]
            if uid not in gemini or uid not in existing:
                continue
            row = dict(row0)
            row["gemini"] = gemini[uid]["target_ko"]
            row["existing"] = existing[uid]["ko"]
            row["issues"] = gemini[uid].get("issues", [])
            row["same_target"] = row["gemini"] == row["existing"]
            row["pair_similarity"] = similarity(row["gemini"], row["existing"])
            row["ruby"] = "<ruby" in row["ja"].lower()
            prev_speakers = {x["speaker_id"] for x in rows[max(0, i - 4):i + 5] if x["speaker_id"]}
            row["multi_party_risk"] = len(prev_speakers) >= 3
            row["context_before"] = [
                {"line_index": x["line_index"], "speaker_id": x["speaker_id"], "ja": x["ja"]}
                for x in rows[max(0, i - 2):i]
            ]
            row["context_after"] = [
                {"line_index": x["line_index"], "speaker_id": x["speaker_id"], "ja": x["ja"]}
                for x in rows[i + 1:i + 3]
            ]
            row["result_file"] = result_files[uid]
            enriched_by_script[script].append(row)

    quota = distribute(enriched_by_script, REPRESENTATIVE_N)
    representative = choose_representative(enriched_by_script, quota)
    selected = {r["uid"] for r in representative}
    for r in representative:
        r["selection_panel"] = ["representative"]
        r["selection_reason"] = ["script/position/speaker/length/exactness stratification"]

    all_rows = [r for rows in enriched_by_script.values() for r in rows]
    risk_pool = []
    for row in all_rows:
        if row["uid"] in selected:
            continue
        reasons = []
        if row["issues"]:
            reasons.append("Gemini issue record")
        if row["ruby"]:
            reasons.append("ruby semantic risk")
        if row["multi_party_risk"]:
            reasons.append("3+ speaker window")
        if row["pair_similarity"] < 0.32 and len(visible(row["ja"])) >= 10:
            reasons.append("low A/B lexical similarity")
        la, lb = len(visible(row["gemini"])), len(visible(row["existing"]))
        if min(la, lb) and max(la, lb) / min(la, lb) >= 1.65:
            reasons.append("large A/B length disparity")
        if reasons:
            row["selection_reason"] = reasons
            priority = (
                20 * bool(row["issues"])
                + 9 * bool(row["ruby"])
                + 6 * bool(row["multi_party_risk"])
                + 5 * (row["pair_similarity"] < 0.32)
                + 3 * ("large A/B length disparity" in reasons)
            )
            risk_pool.append((priority, row))
    risk_pool.sort(key=lambda x: (-x[0], stable("risk:" + x[1]["uid"])))
    risk = []
    # Cap any single risk family so ruby does not consume the panel.
    ruby_count = issue_count = multi_count = 0
    for _, row in risk_pool:
        if len(risk) >= RISK_N:
            break
        if row["ruby"] and not row["issues"] and ruby_count >= 15:
            continue
        if row["multi_party_risk"] and not row["issues"] and not row["ruby"] and multi_count >= 15:
            continue
        risk.append(row)
        selected.add(row["uid"])
        row["selection_panel"] = ["risk"]
        ruby_count += int(row["ruby"])
        issue_count += int(bool(row["issues"]))
        multi_count += int(row["multi_party_risk"])
    if len(risk) != RISK_N:
        raise RuntimeError(f"risk selection short: {len(risk)}")

    sample = representative + risk
    sample.sort(key=lambda r: (r["script"], r["line_index"], r["uid"]))
    blind_key = {}
    blind_rows = []
    for row in sample:
        swap = stable("blind:" + row["uid"]) % 2 == 1
        a = row["existing"] if swap else row["gemini"]
        b = row["gemini"] if swap else row["existing"]
        blind_key[row["uid"]] = {"A": "existing" if swap else "gemini", "B": "gemini" if swap else "existing"}
        blind_rows.append({
            "uid": row["uid"], "script": row["script"], "line_index": row["line_index"],
            "source_hash": row["source_hash"], "speaker_id": row["speaker_id"],
            "selection_panel": row["selection_panel"], "selection_reason": row["selection_reason"],
            "context_before": row["context_before"], "ja": row["ja"], "context_after": row["context_after"],
            "candidate_A": a, "candidate_B": b,
        })

    packet_size = 25
    for i in range(0, len(blind_rows), packet_size):
        chunk = blind_rows[i:i + packet_size]
        n = i // packet_size + 1
        dump(OUT / "blind_packets" / f"packet_{n:02d}.json", {
            "schema_version": 1,
            "instructions": "Judge A and B only against Japanese and raw-catalog context. Do not infer provider. Scores 0-4: fidelity, naturalness, directed_voice, no_unsupported_addition. preferred=A/B/tie.",
            "entries": chunk,
        })
        dump(OUT / "judgments" / f"packet_{n:02d}.json", {
            "schema_version": 1,
            "reviewer": "Codex internal",
            "entries": [
                {
                    "uid": x["uid"], "preferred": None,
                    "A": {"fidelity": None, "naturalness": None, "directed_voice": None, "no_unsupported_addition": None, "issues": []},
                    "B": {"fidelity": None, "naturalness": None, "directed_voice": None, "no_unsupported_addition": None, "issues": []},
                    "severity": None, "reason": None,
                }
                for x in chunk
            ],
        })

    dump(OUT / "private" / "blind_key.json", blind_key)
    dump(OUT / "selection_manifest.json", {
        "schema_version": 1,
        "method": "Codex-authored blinded paired comparison against independently parsed raw Japanese catalogs",
        "seed": SEED,
        "sample": {"total": len(sample), "representative": len(representative), "risk": len(risk), "packet_count": math.ceil(len(sample) / packet_size)},
        "risk_counts": {
            "issues": sum(bool(r["issues"]) for r in risk), "ruby": sum(r["ruby"] for r in risk),
            "multi_party": sum(r["multi_party_risk"] for r in risk),
            "low_similarity": sum(r["pair_similarity"] < 0.32 for r in risk),
        },
        "sample_distribution": {
            "chapter": dict(Counter(r["script"][:4] for r in sample)),
            "script": dict(Counter(r["script"] for r in sample)),
            "speaker": dict(Counter(r["speaker_id"] or "<narration>" for r in sample)),
            "same_target": dict(Counter(str(r["same_target"]) for r in sample)),
        },
        "source": {
            "raw_catalog_directory": str(WORK / "script_audit" / "catalogs" / "ja"),
            "catalog_hashes": catalog_hashes,
            "gemini_results_directory": str(RESULTS),
            "existing_ko_map": str(WORK / "localization" / "build" / "ko_map.json"),
            "existing_ko_map_role": "comparison candidate only; never semantic authority",
        },
        "rubric": {
            "fidelity": "0 meaning wrong/unsupported, 4 precise nuance and information budget",
            "naturalness": "0 broken/translationese, 4 natural Korean for text function",
            "directed_voice": "0 wrong relationship/register, 4 fits speaker→addressee/context",
            "no_unsupported_addition": "0 material invention, 4 no unsupported content",
        },
    })
    print(json.dumps({
        "status": "READY_FOR_BLIND_REVIEW", "sample": len(sample), "representative": len(representative),
        "risk": len(risk), "packets": math.ceil(len(sample) / packet_size),
        "risk_counts": {"issues": sum(bool(r["issues"]) for r in risk), "ruby": sum(r["ruby"] for r in risk), "multi_party": sum(r["multi_party_risk"] for r in risk)},
        "out": str(OUT),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
