from __future__ import annotations

import collections
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


WORK = Path(r"P:\AI\Codex\projects\_migrated_c_documents_codex\2026-07-25\new-chat\work")
GAME = Path(r"Y:\GAME\Fault StP LIGHTKRAVTE")
OUT = Path(r"P:\AI\Codex\projects\fault-stp-lightkravte-asset-review-2026-09-04")
sys.path.insert(0, str(WORK / "python_deps_local"))

import UnityPy  # noqa: E402


JP_OR_CJK = re.compile(r"[\u3040-\u30ff\u31f0-\u31ff\u3400-\u4dbf\u4e00-\u9fff]")
HANGUL = re.compile(r"[\u1100-\u11ff\u3130-\u318f\uac00-\ud7a3]")
DISPLAY_FIELD = re.compile(
    r"(?:^|_)(?:text|title|label|caption|message|placeholder|tooltip|description|"
    r"displayname|display_name|header|content|value)(?:$|_)",
    re.IGNORECASE,
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def asset_key(obj: Any) -> tuple[str, int]:
    source = getattr(getattr(obj, "assets_file", None), "name", "")
    return source, int(obj.path_id)


def flatten_strings(value: Any, prefix: str = ""):
    if isinstance(value, str):
        yield prefix, value
    elif isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            yield from flatten_strings(child, path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from flatten_strings(child, f"{prefix}[{index}]")


def pptr_key(obj: Any, pointer: Any) -> tuple[str, int] | None:
    if not isinstance(pointer, dict):
        return None
    path_id = pointer.get("m_PathID")
    file_id = pointer.get("m_FileID")
    if not path_id or file_id not in (0, None):
        return None
    return getattr(getattr(obj, "assets_file", None), "name", ""), int(path_id)


def safe_name(obj: Any) -> str:
    try:
        data = obj.read()
        return str(getattr(data, "m_Name", getattr(data, "name", "")) or "")
    except Exception:
        return ""


def inspect_file(path: Path) -> dict:
    env = UnityPy.load(str(path))
    objects = list(env.objects)
    type_counts = collections.Counter(obj.type.name for obj in objects)
    containers: dict[tuple[str, int], list[str]] = collections.defaultdict(list)
    for source_path, obj in env.container.items():
        containers[asset_key(obj)].append(source_path)

    names: dict[tuple[str, int], str] = {}
    for obj in objects:
        if obj.type.name in {"GameObject", "MonoScript"}:
            names[asset_key(obj)] = safe_name(obj)

    textures = []
    text_assets = []
    media = []
    string_candidates = []
    errors = []

    for obj in objects:
        kind = obj.type.name
        key = asset_key(obj)
        source_paths = sorted(containers.get(key, []))
        if kind == "Texture2D":
            try:
                data = obj.read()
                textures.append(
                    {
                        "assets_file": key[0],
                        "path_id": key[1],
                        "name": str(getattr(data, "m_Name", "")),
                        "width": int(getattr(data, "m_Width", 0)),
                        "height": int(getattr(data, "m_Height", 0)),
                        "format": str(getattr(data, "m_TextureFormat", "")),
                        "mip_count": int(getattr(data, "m_MipCount", 0)),
                        "container_paths": source_paths,
                    }
                )
            except Exception as exc:
                errors.append({"type": kind, "path_id": key[1], "error": f"{type(exc).__name__}: {exc}"})
        elif kind == "TextAsset":
            try:
                data = obj.read()
                raw_value = getattr(data, "m_Script", "")
                if isinstance(raw_value, bytes):
                    raw = raw_value
                    text = raw.decode("utf-8", errors="replace")
                else:
                    text = str(raw_value)
                    raw = text.encode("utf-8")
                text_assets.append(
                    {
                        "assets_file": key[0],
                        "path_id": key[1],
                        "name": str(getattr(data, "m_Name", "")),
                        "bytes": len(raw),
                        "sha256": hashlib.sha256(raw).hexdigest(),
                        "contains_jp_or_cjk": bool(JP_OR_CJK.search(text)),
                        "contains_hangul": bool(HANGUL.search(text)),
                        "container_paths": source_paths,
                        "preview": text[:1000],
                    }
                )
            except Exception as exc:
                errors.append({"type": kind, "path_id": key[1], "error": f"{type(exc).__name__}: {exc}"})
        elif kind in {"AudioClip", "VideoClip", "Font"}:
            try:
                data = obj.read()
                media.append(
                    {
                        "type": kind,
                        "assets_file": key[0],
                        "path_id": key[1],
                        "name": str(getattr(data, "m_Name", "")),
                        "container_paths": source_paths,
                    }
                )
            except Exception as exc:
                errors.append({"type": kind, "path_id": key[1], "error": f"{type(exc).__name__}: {exc}"})

        if kind != "MonoBehaviour":
            continue
        try:
            tree = obj.read_typetree()
            game_object_key = pptr_key(obj, tree.get("m_GameObject"))
            script_key = pptr_key(obj, tree.get("m_Script"))
            game_object = names.get(game_object_key or ("", 0), "")
            script = names.get(script_key or ("", 0), "")
            for field, value in flatten_strings(tree):
                if not value or len(value) > 500000:
                    continue
                leaf = re.split(r"[.\[]", field)[-1].rstrip("]0123456789")
                has_cjk = bool(JP_OR_CJK.search(value))
                display_field = bool(DISPLAY_FIELD.search(leaf)) or leaf.lower() in {"m_text", "text"}
                if not has_cjk and not display_field:
                    continue
                string_candidates.append(
                    {
                        "assets_file": key[0],
                        "path_id": key[1],
                        "container_paths": source_paths,
                        "game_object": game_object,
                        "script": script,
                        "field": field,
                        "value": value,
                        "has_jp_or_cjk": has_cjk,
                        "has_hangul": bool(HANGUL.search(value)),
                    }
                )
        except Exception as exc:
            errors.append(
                {
                    "type": kind,
                    "assets_file": key[0],
                    "path_id": key[1],
                    "container_paths": source_paths,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

    return {
        "path": str(path),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
        "object_count": len(objects),
        "type_counts": dict(type_counts),
        "container_count": len(env.container),
        "textures": textures,
        "text_assets": text_assets,
        "media": media,
        "string_candidates": string_candidates,
        "read_errors": errors,
    }


def main() -> None:
    data_root = GAME / "LIGHTKRAVTE_Data"
    inputs = [
        data_root / "globalgamemanagers",
        data_root / "globalgamemanagers.assets",
        data_root / "level0",
        data_root / "resources.assets",
        data_root / "sharedassets0.assets",
        *sorted((data_root / "StreamingAssets" / "aa" / "StandaloneWindows64").glob("*.bundle")),
    ]
    results = []
    for index, path in enumerate(inputs, 1):
        print(f"[{index}/{len(inputs)}] {path.name}", flush=True)
        try:
            results.append(inspect_file(path))
        except Exception as exc:
            results.append({"path": str(path), "fatal_error": f"{type(exc).__name__}: {exc}"})
    payload = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "game_root": str(GAME),
        "inputs": len(inputs),
        "files": results,
    }
    out_path = OUT / "unity_asset_inventory.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(out_path)


if __name__ == "__main__":
    main()
