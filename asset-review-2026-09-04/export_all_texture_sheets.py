from __future__ import annotations

import json
import sys
from pathlib import Path


WORK = Path(r"P:\AI\Codex\projects\_migrated_c_documents_codex\2026-07-25\new-chat\work")
ROOT = Path(r"P:\AI\Codex\projects\fault-stp-lightkravte-asset-review-2026-09-04")
sys.path.insert(0, str(WORK / "python_deps_local"))

import UnityPy  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402


COLS, ROWS = 8, 6
CELL_W, CELL_H = 240, 180
THUMB_W, THUMB_H = 226, 132


def alpha_preview(image: Image.Image) -> Image.Image:
    image = image.convert("RGBA")
    image.thumbnail((THUMB_W, THUMB_H), Image.Resampling.LANCZOS)
    bg = Image.new("RGBA", (THUMB_W, THUMB_H), (220, 220, 220, 255))
    draw = ImageDraw.Draw(bg)
    step = 12
    for y in range(0, THUMB_H, step):
        for x in range(0, THUMB_W, step):
            if (x // step + y // step) % 2:
                draw.rectangle((x, y, x + step - 1, y + step - 1), fill=(175, 175, 175, 255))
    bg.alpha_composite(image, ((THUMB_W - image.width) // 2, (THUMB_H - image.height) // 2))
    return bg.convert("RGB")


def main() -> None:
    inventory = json.loads((ROOT / "unity_asset_inventory.json").read_text(encoding="utf-8"))
    out_dir = ROOT / "raster_review" / "all_texture_sheets"
    out_dir.mkdir(parents=True, exist_ok=True)
    font = ImageFont.load_default()
    page = None
    draw = None
    page_items = []
    pages = []
    errors = []
    ordinal = 0

    def flush_page() -> None:
        nonlocal page, draw, page_items
        if page is None:
            return
        page_no = len(pages) + 1
        path = out_dir / f"all_textures_{page_no:03d}.jpg"
        page.save(path, quality=90, subsampling=0)
        pages.append({"page": page_no, "path": str(path), "items": page_items})
        page = None
        draw = None
        page_items = []

    for file_index, file in enumerate(inventory["files"], 1):
        texture_meta = {int(item["path_id"]): item for item in file.get("textures", [])}
        if not texture_meta:
            continue
        print(f"[{file_index}/{len(inventory['files'])}] {Path(file['path']).name}", flush=True)
        env = UnityPy.load(file["path"])
        objects = sorted(
            (obj for obj in env.objects if obj.type.name == "Texture2D" and int(obj.path_id) in texture_meta),
            key=lambda obj: (str(texture_meta[int(obj.path_id)].get("name", "")).lower(), int(obj.path_id)),
        )
        for obj in objects:
            meta = texture_meta[int(obj.path_id)]
            if meta.get("name") == "Font Texture" or not meta.get("width") or not meta.get("height"):
                continue
            if page is None:
                page = Image.new("RGB", (COLS * CELL_W, ROWS * CELL_H), "#202020")
                draw = ImageDraw.Draw(page)
            cell = len(page_items)
            x = (cell % COLS) * CELL_W
            y = (cell // COLS) * CELL_H
            try:
                thumb = alpha_preview(obj.read().image)
                page.paste(thumb, (x + 7, y + 7))
            except Exception as exc:
                errors.append({"asset": file["path"], "path_id": int(obj.path_id), "name": meta.get("name"), "error": f"{type(exc).__name__}: {exc}"})
                draw.rectangle((x + 7, y + 7, x + 7 + THUMB_W, y + 7 + THUMB_H), fill="#660000")
            label = f"{ordinal:04d} {meta.get('name','')}"[:38]
            detail = f"{meta.get('width')}x{meta.get('height')} #{int(obj.path_id)}"[:38]
            draw.text((x + 7, y + 143), label, font=font, fill="white")
            draw.text((x + 7, y + 158), detail, font=font, fill="#bbbbbb")
            page_items.append(
                {
                    "ordinal": ordinal,
                    "asset": file["path"],
                    "path_id": int(obj.path_id),
                    "name": meta.get("name", ""),
                    "width": meta.get("width"),
                    "height": meta.get("height"),
                }
            )
            ordinal += 1
            if len(page_items) == COLS * ROWS:
                flush_page()
    flush_page()
    manifest = {"schema_version": 1, "textures_rendered": ordinal, "pages": pages, "errors": errors}
    (out_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"textures_rendered": ordinal, "pages": len(pages), "errors": len(errors)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
