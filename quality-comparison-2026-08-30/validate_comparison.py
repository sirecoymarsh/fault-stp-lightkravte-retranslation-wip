from __future__ import annotations

import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent
GEMINI_DIR = Path(r"P:\AI\Codex\projects\fault-stp-lightkravte-gemini-results")
OLD_MAP = Path(
    r"P:\AI\Codex\projects\_migrated_c_documents_codex\2026-07-25\new-chat"
    r"\work\localization\build\ko_map.json"
)
RAW_DIR = Path(
    r"P:\AI\Codex\projects\_migrated_c_documents_codex\2026-07-25\new-chat"
    r"\work\script_audit\catalogs\ja"
)


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sign_test_two_sided(left: int, right: int) -> float:
    n = left + right
    k = min(left, right)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / (2**n)
    return min(1.0, 2 * tail)


manifest = read_json(ROOT / "selection_manifest.json")
key = read_json(ROOT / "private" / "blind_key.json")
summary = read_json(ROOT / "comparison_summary.json")
unblinded = read_json(ROOT / "unblinded_results.json")

packets = []
for path in sorted((ROOT / "blind_packets").glob("packet_*.json")):
    packet = read_json(path)
    packets.extend(packet["entries"])

judgments = []
judgment_files = sorted((ROOT / "judgments").glob("packet_*.json"))
for path in judgment_files:
    data = read_json(path)
    if data.get("reviewer") != "Codex internal":
        raise AssertionError(f"unexpected reviewer: {path}")
    assert data.get("review_status") == "complete_blind"
    assert data.get("entries_reviewed") == len(data["entries"])
    judgments.extend(data["entries"])

packet_by_uid = {row["uid"]: row for row in packets}
judgment_by_uid = {row["uid"]: row for row in judgments}

assert len(packets) == 200 == len(packet_by_uid)
assert len(judgments) == 200 == len(judgment_by_uid)
assert set(packet_by_uid) == set(judgment_by_uid) == set(key)
assert len(list((ROOT / "blind_packets").glob("packet_*.json"))) == 8
assert len(judgment_files) == 8

panels = Counter()
preferences = Counter()
representative_preferences = Counter()
for uid, packet in packet_by_uid.items():
    judgment = judgment_by_uid[uid]
    assert judgment["preferred"] in {"A", "B", "tie"}
    assert judgment.get("reason", "").strip()
    for side in ("A", "B"):
        scores = judgment[side]
        for dimension in (
            "fidelity",
            "naturalness",
            "directed_voice",
            "no_unsupported_addition",
        ):
            assert isinstance(scores[dimension], int)
            assert 0 <= scores[dimension] <= 4
    assert set(key[uid].values()) == {"existing", "gemini"}
    for panel in packet["selection_panel"]:
        panels[panel] += 1
    if judgment["preferred"] == "tie":
        provider = "tie"
    else:
        provider = key[uid][judgment["preferred"]]
    preferences[provider] += 1
    if "representative" in packet["selection_panel"]:
        representative_preferences[provider] += 1

assert panels == Counter({"representative": 150, "risk": 50})
assert preferences == Counter({"existing": 93, "gemini": 55, "tie": 52})
assert representative_preferences == Counter({"existing": 63, "tie": 50, "gemini": 37})

# Re-read the two current candidate sources and prove that every judged Korean
# string is exactly the one selected from that source at sampling time.
existing_raw = read_json(OLD_MAP)
existing = {uid: value["ko"] for uid, value in existing_raw.items()}
gemini = {}
gemini_files = sorted(GEMINI_DIR.glob("*.ko.jsonl"))
assert len(gemini_files) == 93
for path in gemini_files:
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row["uid"] in gemini:
            raise AssertionError(f"duplicate Gemini UID: {row['uid']}")
        gemini[row["uid"]] = row["target_ko"]
assert len(gemini) == 6746

for uid, packet in packet_by_uid.items():
    for side in ("A", "B"):
        provider = key[uid][side]
        expected = existing[uid] if provider == "existing" else gemini[uid]
        assert packet[f"candidate_{side}"] == expected, (uid, side, provider)

# Re-hash every raw catalog and compare with the pre-review manifest.
catalog_hashes = manifest["source"]["catalog_hashes"]
assert len(catalog_hashes) == 46
for name, expected_hash in catalog_hashes.items():
    assert sha256(RAW_DIR / name) == expected_hash, name

summary_preferences = summary["panels"]["all"]["preference"]
assert summary_preferences == {"gemini": 55, "existing": 93, "tie": 52}
independent_p = sign_test_two_sided(93, 55)
assert abs(independent_p - summary["panels"]["all"]["paired_sign_test_p"]) < 1e-15

unblinded_rows = unblinded["entries"]
assert len(unblinded_rows) == 200
assert len({row["uid"] for row in unblinded_rows}) == 200

source_hashes = {
    "existing_ko_map.json": sha256(OLD_MAP),
    **{f"gemini/{path.name}": sha256(path) for path in gemini_files},
    **{f"raw_catalog/{name}": catalog_hashes[name] for name in sorted(catalog_hashes)},
}
(ROOT / "INPUT_SHA256SUMS.txt").write_text(
    "".join(f"{digest}  {name}\n" for name, digest in source_hashes.items()),
    encoding="utf-8",
)

artifact_paths = sorted(
    path
    for path in ROOT.rglob("*")
    if path.is_file()
    and path.name not in {"SHA256SUMS.txt", "VALIDATION_REPORT.json"}
    and "__pycache__" not in path.parts
)
(ROOT / "SHA256SUMS.txt").write_text(
    "".join(f"{sha256(path)}  {path.relative_to(ROOT).as_posix()}\n" for path in artifact_paths),
    encoding="utf-8",
)

report = {
    "status": "PASS",
    "independent_validator": "validate_comparison.py",
    "checks": {
        "blind_packets": 8,
        "judgment_packets": 8,
        "unique_uids": 200,
        "complete_blind_judgments": 200,
        "representative_rows": 150,
        "risk_rows": 50,
        "raw_catalog_hashes_verified": 46,
        "gemini_source_files": 93,
        "gemini_source_rows": 6746,
        "sampled_candidate_strings_match_current_sources": 400,
        "preference_existing": 93,
        "preference_gemini": 55,
        "preference_tie": 52,
        "all_non_tie_sign_test_p": independent_p,
    },
    "verdict": summary["verdict"],
}
(ROOT / "VALIDATION_REPORT.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
print(json.dumps(report, ensure_ascii=False, indent=2))
