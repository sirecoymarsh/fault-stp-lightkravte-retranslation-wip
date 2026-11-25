from __future__ import annotations

import collections
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


WORK = Path(r"P:\AI\Codex\projects\_migrated_c_documents_codex\2026-07-25\new-chat\work")
GAME = Path(r"Y:\GAME\Fault StP LIGHTKRAVTE")
OUT = Path(r"P:\AI\Codex\projects\fault-stp-lightkravte-asset-review-2026-09-04")
sys.path[:0] = [str(WORK / "python_deps_local"), str(WORK / "typetree_deps_local")]

import UnityPy  # noqa: E402
from UnityPy.helpers.TypeTreeGenerator import TypeTreeGenerator  # noqa: E402
from UnityPy.helpers.TypeTreeHelper import TypeTreeConfig, read_value  # noqa: E402
from UnityPy.streams import EndianBinaryReader  # noqa: E402


JP_OR_CJK = re.compile(r"[\u3040-\u30ff\u31f0-\u31ff\u3400-\u4dbf\u4e00-\u9fff]")
HANGUL = re.compile(r"[\u1100-\u11ff\u3130-\u318f\uac00-\ud7a3]")
DISPLAY_FIELD = re.compile(
    r"(?:^|_)(?:text|title|label|caption|message|placeholder|tooltip|description|"
    r"displayname|display_name|header|content|value)(?:$|_)",
    re.IGNORECASE,
)


def flatten_strings(value: Any, prefix: str = ""):
    if isinstance(value, str):
        yield prefix, value
    elif isinstance(value, dict):
        for key, child in value.items():
            yield from flatten_strings(child, f"{prefix}.{key}" if prefix else str(key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from flatten_strings(child, f"{prefix}[{index}]")


def asset_file_name(obj: Any) -> str:
    return str(getattr(getattr(obj, "assets_file", None), "name", ""))


def parse_header(obj: Any) -> dict:
    raw = obj.get_raw_data()
    reader = EndianBinaryReader(raw, endian="<")
    game_file_id = reader.read_int()
    game_path_id = reader.read_long()
    enabled = reader.read_u_byte()
    reader.align_stream()
    script_file_id = reader.read_int()
    script_path_id = reader.read_long()
    name = reader.read_aligned_string()
    return {
        "game_file_id": game_file_id,
        "game_path_id": game_path_id,
        "script_file_id": script_file_id,
        "script_path_id": script_path_id,
        "enabled": enabled,
        "name": name,
    }


def mono_script_record(data: Any) -> dict:
    namespace = str(getattr(data, "m_Namespace", "") or "")
    class_name = str(getattr(data, "m_ClassName", "") or "")
    return {
        "assembly": str(getattr(data, "m_AssemblyName", "") or ""),
        "class": class_name,
        "namespace": namespace,
        "fullname": f"{namespace}.{class_name}" if namespace else class_name,
    }


def main() -> None:
    data_root = GAME / "LIGHTKRAVTE_Data"
    inputs = [
        data_root / "level0",
        data_root / "resources.assets",
        data_root / "sharedassets0.assets",
        *sorted((data_root / "StreamingAssets" / "aa" / "StandaloneWindows64").glob("*.bundle")),
    ]

    globals_env = UnityPy.load(str(data_root / "globalgamemanagers.assets"))
    global_scripts = {
        int(obj.path_id): mono_script_record(obj.read())
        for obj in globals_env.objects
        if obj.type.name == "MonoScript"
    }
    generator = TypeTreeGenerator("2020.3.7f1")
    generator.load_local_game(str(GAME))

    records = []
    errors = []
    stats = collections.Counter()
    for file_index, path in enumerate(inputs, 1):
        print(f"[{file_index}/{len(inputs)}] {path.name}", flush=True)
        env = UnityPy.load(str(path))
        local_scripts = {}
        game_objects = {}
        containers = collections.defaultdict(list)
        for container_path, obj in env.container.items():
            containers[(asset_file_name(obj), int(obj.path_id))].append(container_path)
        for obj in env.objects:
            if obj.type.name == "MonoScript":
                try:
                    local_scripts[(asset_file_name(obj), int(obj.path_id))] = mono_script_record(obj.read())
                except Exception:
                    pass
            elif obj.type.name == "GameObject":
                try:
                    game_objects[(asset_file_name(obj), int(obj.path_id))] = str(obj.read().m_Name)
                except Exception:
                    pass

        for obj in env.objects:
            if obj.type.name != "MonoBehaviour":
                continue
            stats["monobehaviours"] += 1
            source_file = asset_file_name(obj)
            try:
                head = parse_header(obj)
            except Exception as exc:
                errors.append({"asset": str(path), "path_id": obj.path_id, "stage": "header", "error": f"{type(exc).__name__}: {exc}"})
                continue
            script = None
            if head["script_file_id"] == 0:
                script = local_scripts.get((source_file, head["script_path_id"]))
            elif head["script_file_id"] > 0:
                try:
                    external = obj.assets_file.externals[head["script_file_id"] - 1]
                    external_path = str(getattr(external, "path", ""))
                except Exception:
                    external_path = ""
                if external_path.lower().endswith("globalgamemanagers.assets"):
                    script = global_scripts.get(head["script_path_id"])
            if not script:
                errors.append(
                    {
                        "asset": str(path),
                        "assets_file": source_file,
                        "path_id": obj.path_id,
                        "stage": "script_resolution",
                        "header": head,
                    }
                )
                continue
            try:
                node = generator.get_nodes_up(script["assembly"], script["fullname"])
                reader = EndianBinaryReader(obj.get_raw_data(), endian="<")
                tree = read_value(node, reader, TypeTreeConfig(True, obj.assets_file, True))
                if reader.Position != len(obj.get_raw_data()):
                    raise ValueError(f"parser stopped at {reader.Position}/{len(obj.get_raw_data())}")
                stats["parsed"] += 1
            except Exception as exc:
                errors.append(
                    {
                        "asset": str(path),
                        "assets_file": source_file,
                        "path_id": obj.path_id,
                        "stage": "generated_typetree",
                        "script": script,
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )
                continue

            game_object = ""
            if head["game_file_id"] == 0 and head["game_path_id"]:
                game_object = game_objects.get((source_file, head["game_path_id"]), "")
            for field, value in flatten_strings(tree):
                if not value or len(value) > 500000:
                    continue
                leaf = re.split(r"[.\[]", field)[-1].rstrip("]0123456789")
                has_cjk = bool(JP_OR_CJK.search(value))
                is_display = bool(DISPLAY_FIELD.search(leaf)) or leaf.lower() in {"m_text", "text"}
                if not has_cjk and not is_display:
                    continue
                records.append(
                    {
                        "asset": str(path),
                        "assets_file": source_file,
                        "path_id": int(obj.path_id),
                        "container_paths": sorted(containers.get((source_file, int(obj.path_id)), [])),
                        "game_object": game_object,
                        "script": script,
                        "object_name": head["name"],
                        "field": field,
                        "value": value,
                        "has_jp_or_cjk": has_cjk,
                        "has_hangul": bool(HANGUL.search(value)),
                    }
                )

    payload = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "game_root": str(GAME),
        "method": "Independent MonoBehaviour parse with generated type trees from shipped managed assemblies.",
        "stats": dict(stats),
        "records": records,
        "errors": errors,
    }
    destination = OUT / "generated_typetree_string_audit.json"
    destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"destination": str(destination), "stats": dict(stats), "records": len(records), "errors": len(errors)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
