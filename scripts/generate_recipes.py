"""Convert the owner's ChefTap exports and optional local snapshot into app data."""
import html
import json
import re
import sqlite3
import unicodedata
import zipfile
from collections import defaultdict
from pathlib import Path

from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "cheftap_export.zip"
TARGET = ROOT / "app/src/main/assets/recipes.js"
SNAPSHOT = ROOT / "data/neussenombox.db"
SETTINGS = ROOT / "data/cheftap_settings.json"


def extract(name, raw):
    soup = BeautifulSoup(raw, "html.parser")
    for node in soup(["script", "style", "iframe", "form", "object"]):
        node.decompose()
    for node in soup.find_all(True):
        for key in list(node.attrs):
            if key.lower().startswith("on"):
                del node.attrs[key]
        if node.name == "a" and str(node.get("href", "")).lower().startswith("javascript:"):
            del node.attrs["href"]
    title_node = soup.find("h1")
    title = title_node.get_text(" ", strip=True) if title_node else Path(name).stem.replace("_", " ")
    original = soup.find("a", string=re.compile("Original Article", re.I))
    source = original.get("href", "") if original else ""
    if original:
        original.decompose()
    if title_node:
        title_node.decompose()
    body = soup.body or soup
    paragraphs = body.find_all("p")
    tags = []
    candidate = ""
    if paragraphs:
        first = paragraphs[0].get_text(" ", strip=True)
        if "•" in first and len(first) < 180:
            tags = [x.strip() for x in first.split("•") if x.strip()]
            paragraphs[0].decompose()
        elif len(first) < 50 and first != title:
            candidate = first
    content = str(body).replace("<body>", "").replace("</body>", "")
    content = re.sub(r"(?:<br\s*/?>\s*){3,}", "<br><br>", content, flags=re.I)
    return {"id": name, "title": html.unescape(title), "tags": tags, "source": source, "html": content, "_candidate": candidate}


def match_snapshot(exported):
    db = sqlite3.connect(f"file:{SNAPSHOT}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    rows = db.execute("select id,title,source_url,notes,favorite from recipes where date_deleted is null order by date_added,id").fetchall()
    by_pair = defaultdict(list)
    by_source = defaultdict(list)
    by_title = defaultdict(list)
    normalize = lambda text: re.sub(r"[^a-z0-9]+", "", unicodedata.normalize("NFKD", text or "").lower())
    for row in rows:
        by_pair[(row["title"], row["source_url"] or "")].append(row["id"])
        by_source[row["source_url"] or ""].append(row["id"])
        by_title[normalize(row["title"])].append(row["id"])
    unused = {row["id"] for row in rows}
    formatted = {}
    legacy = {}
    for recipe in exported:
        candidates = [key for key in by_pair[(recipe["title"], recipe["source"])] if key in unused]
        if not candidates and recipe["source"]:
            candidates = [key for key in by_source[recipe["source"]] if key in unused]
        if not candidates:
            candidates = [key for key in by_title[normalize(recipe["title"])] if key in unused]
        if not candidates:
            raise RuntimeError(f"Could not match export recipe: {recipe['id']}")
        chosen = candidates[0]
        unused.remove(chosen)
        formatted[chosen] = recipe["html"]
        legacy[recipe["id"]] = chosen
    if len(unused) != len(rows) - len(exported):
        raise RuntimeError("Snapshot and HTML export match count is inconsistent.")
    tags = defaultdict(list)
    for recipe_id, tag in db.execute("select rt.recipe_id,t.tag_text from recipe_tags rt join tags t on t.id=rt.tag_id where t.date_deleted is null"):
        tags[recipe_id].append(tag)
    recipe_items = defaultdict(list)
    for recipe_id, kind, value in db.execute(
        "select recipe_id,type,freetext from recipe_items "
        "where type in (1,2,4,5,6) and freetext is not null "
        "order by recipe_id,ordinal"
    ):
        if value.strip():
            recipe_items[recipe_id].append([kind, value.strip()])
    photos = defaultdict(list)
    for recipe_id, photo_id in db.execute(
        "select rp.recipe_id,rp.photo_id from recipe_photos rp "
        "join media_id m on m.photo_id=rp.photo_id "
        "where rp.date_deleted is null and m.date_deleted is null "
        "order by rp.is_main desc,rp.date_added"
    ):
        filename = next((f"{photo_id}.{suffix}" for suffix in ("png", "jpg", "gif", "webp")
                         if (ROOT / "data/photos" / f"{photo_id}.{suffix}").is_file()), None)
        if filename and filename not in photos[recipe_id]:
            photos[recipe_id].append(filename)
    def structured(recipe_id, title):
        parts = []
        for kind, value in db.execute("select type,freetext from recipe_items where recipe_id=? order by ordinal", (recipe_id,)):
            if not value or kind not in (1, 2, 4, 5, 6, 7) or (kind == 7 and value == title):
                continue
            tag = "h2" if kind in (1, 5, 7) else "p"
            parts.append(f"<{tag}>{html.escape(value)}</{tag}>")
        if not parts:
            raise RuntimeError(f"Snapshot recipe {recipe_id} has no readable content.")
        return "".join(parts)
    result = []
    favorites = []
    for row in rows:
        recipe_id = row["id"]
        content = formatted.get(recipe_id) or structured(recipe_id, row["title"])
        if row["notes"] and row["notes"].strip():
            content += "<h2>Notes</h2><p>" + html.escape(row["notes"]).replace("\n", "<br>") + "</p>"
        result.append({"id": recipe_id, "title": row["title"], "tags": tags[recipe_id], "source": row["source_url"] or "", "html": content, "photos": photos[recipe_id], "items": recipe_items[recipe_id], "notes": row["notes"] or ""})
        if row["favorite"]:
            favorites.append(recipe_id)
    print(f"Matched {len(formatted)} formatted exports; recovered {len(rows)} snapshot recipes, {len(favorites)} favorites, and {sum(map(len, photos.values()))} local photos")
    return result, favorites, legacy


def main():
    if SOURCE.exists():
        with zipfile.ZipFile(SOURCE) as archive:
            recipes = [extract(info.filename, archive.read(info)) for info in archive.infolist() if info.filename.lower().endswith(".html")]
        if not recipes:
            raise SystemExit("Export contained no HTML recipes.")
    else:
        if SNAPSHOT.exists():
            raise SystemExit(f"Snapshot exists at {SNAPSHOT}, but {SOURCE} is missing; refusing to ignore real snapshot data.")
        print("No ChefTap export found; building an empty recipe library. Add recipes in the app or supply your export later.")
        recipes = []
    known_tags = {tag for recipe in recipes for tag in recipe["tags"]}
    for recipe in recipes:
        candidate = recipe.pop("_candidate")
        if candidate in known_tags:
            recipe["tags"] = [candidate]
            body = BeautifulSoup(recipe["html"], "html.parser")
            first = body.find("p")
            if first:
                first.decompose()
            recipe["html"] = str(body)
    favorites = []
    legacy = {}
    if SNAPSHOT.exists():
        recipes, favorites, legacy = match_snapshot(recipes)
    elif recipes:
        print("ChefTap snapshot is absent; building HTML-only data without favorite flags.")
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    compact = lambda value: json.dumps(value, ensure_ascii=True, separators=(",", ":"))
    settings = json.loads(SETTINGS.read_text(encoding="utf-8")) if SETTINGS.exists() else {}
    if not settings:
        print("ChefTap settings were not collected; using RecipeTap defaults.")
    TARGET.write_text("window.SEED_RECIPES=" + compact(recipes) + ";window.SEED_FAVORITES=" + compact(favorites) + ";window.LEGACY_TO_NEW=" + compact(legacy) + ";window.SEED_SETTINGS=" + compact(settings) + ";", encoding="utf-8")
    print(f"Generated {len(recipes)} recipes ({TARGET.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
