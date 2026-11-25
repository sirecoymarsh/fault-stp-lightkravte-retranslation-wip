from __future__ import annotations

import json
import re
import sys
from pathlib import Path


WORK = Path(r"P:\AI\Codex\projects\_migrated_c_documents_codex\2026-07-25\new-chat\work")
ROOT = Path(r"P:\AI\Codex\projects\fault-stp-lightkravte-asset-review-2026-09-04")
GAME = Path(r"Y:\GAME\Fault StP LIGHTKRAVTE")
sys.path.insert(0, str(WORK / "python_deps_local"))

import UnityPy  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402


PATTERN = re.compile(
    r"(?:text|txt|title|credit|logo|banner|button|menu|label|dic|splash|project|staff|team|"
    r"language|read[_-]?text|think[_-]?text)",
    re.IGNORECASE,
)


def safe_filename(value: str) -> str:
    value = re.sub(r"[^0-9A-Za-z._-]+", "_", value).strip("._")
    return value[:100] or "unnamed"


def checker(size: tuple[int, int]) -> Image.Image:
    out = Image.new("RGBA", size, (224, 224, 224, 255))
    draw = ImageDraw.Draw(out)
    step = 16
    for y in range(0, size[1], step):
        for x in range(0, size[0], step):
            if (x // step + y // step) % 2:
                draw.rectangle((x, y, x + step - 1, y + step - 1), fill=(184, 184, 184, 255))
    return out


def main() -> None:
    inventory = json.loads((ROOT / "unity_asset_inventory.json").read_text(encoding="utf-8"))
    selected = []
    for file in inventory["files"]:
        for item in file.get("textures", []):
            name = item.get("name", "")
            paths = " ".join(item.get("container_paths", []))
            if PATTERN.search(name + " " + paths) and name != "Font Texture":
                selected.append((file["path"], int(item["path_id"]), name, item["width"], item["height"]))

    out_dir = ROOT / "raster_review" / "original"
    out_dir.mkdir(parents=True, exist_ok=True)
    exported = []
    by_file = {}
    for record in selected:
        by_file.setdefault(record[0], []).append(record)
    for file_index, (asset_path, rows) in enumerate(sorted(by_file.items()), 1):
        print(f"[{file_index}/{len(by_file)}] {Path(asset_path).name}", flush=True)
        env = UnityPy.load(asset_path)
        objects = {int(obj.path_id): obj for obj in env.objects if obj.type.name == "Texture2D"}
        for _, path_id, name, width, height in rows:
            obj = objects.get(path_id)
            if obj is None:
                continue
            try:
                image = obj.read().image.convert("RGBA")
            except Exception as exc:
                exported.append({"asset": asset_path, "path_id": path_id, "name": name, "error": f"{type(exc).__name__}: {exc}"})
                continue
            filename = f"{safe_filename(Path(asset_path).stem)}__{path_id}__{safe_filename(name)}.png"
            destination = out_dir / filename
            image.save(destination)
            exported.append(
                {
                    "asset": asset_path,
                    "path_id": path_id,
                    "name": name,
                    "width": width,
                    "height": height,
                    "png": str(destination),
                }
            )

    cards = [row for row in exported if row.get("png")]
    cell_w, cell_h = 420, 300
    cols = 4
    rows_per_page = 4
    pages = []
    font = ImageFont.load_default()
    for page_index in range(0, len(cards), cols * rows_per_page):
        page_rows = cards[page_index : page_index + cols * rows_per_page]
        page = Image.new("RGB", (cols * cell_w, rows_per_page * cell_h), "#202020")
        draw = ImageDraw.Draw(page)
        for index, record in enumerate(page_rows):
            x = (index % cols) * cell_w
            y = (index // cols) * cell_h
            source = Image.open(record["png"]).convert("RGBA")
            source.thumbnail((cell_w - 20, cell_h - 62), Image.Resampling.LANCZOS)
            bg = checker((cell_w - 20, cell_h - 62))
            bg.alpha_composite(source, ((bg.width - source.width) // 2, (bg.height - source.height) // 2))
            page.paste(bg.convert("RGB"), (x + 10, y + 10))
            label = f"{record['name']} | {record['width']}x{record['height']} | {record['path_id']}"
            draw.text((x + 10, y + cell_h - 45), label[:66], font=font, fill="white")
            draw.text((x + 10, y + cell_h - 28), Path(record["asset"]).name[:48], font=font, fill="#bbbbbb")
        page_path = ROOT / "raster_review" / f"candidate_contact_sheet_{len(pages)+1:02d}.png"
        page.save(page_path)
        pages.append(str(page_path))

    manifest = {
        "schema_version": 1,
        "selection_pattern": PATTERN.pattern,
        "selected": len(selected),
        "exported": len(cards),
        "records": exported,
        "contact_sheets": pages,
    }
    (ROOT / "raster_review" / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"selected": len(selected), "exported": len(cards), "sheets": len(pages)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
