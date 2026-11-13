"""Read ChefTap's full recipe list through Android UI automation.

Start ChefTap's Recipes screen with SORT BY > Favorites selected before running.
Uses slow fixed-distance drags and requires overlapping rows. The developer
snapshot is a faster and more exact source when it is available.
"""
import json
import re
import subprocess
import time
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "cheftap_favorites.json"


def adb(*args):
    result = subprocess.run(["adb", *args], capture_output=True, check=True)
    return result.stdout


def rows():
    adb("shell", "uiautomator", "dump", "/sdcard/window.xml")
    xml = adb("exec-out", "cat", "/sdcard/window.xml")
    root = ET.fromstring(xml)
    current_sort = [n.get("text") for n in root.iter("node") if n.get("resource-id", "").endswith("current_sort")]
    if "Favorites" not in current_sort:
        raise RuntimeError(f"ChefTap is not sorted by Favorites: {current_sort}")
    found = []
    for group in root.iter("node"):
        title = next((n.get("text") for n in group if n.get("resource-id", "").endswith("recipe_list_item_title")), None)
        favorite = next((n.get("checked") == "true" for n in group if n.get("resource-id", "").endswith("recipe_list_item_fav")), None)
        if title is not None and favorite is not None:
            found.append((title, favorite))
    return found


def main():
    OUT.parent.mkdir(exist_ok=True)
    titles = []
    seen = set()
    all_seen = set()
    previous = set()
    unchanged = 0
    for page in range(1000):
        visible = rows()
        if not visible:
            raise RuntimeError("No recipe rows visible; stopping without inventing results.")
        visible_titles = {title for title, _ in visible}
        if previous and not previous.intersection(visible_titles):
            raise RuntimeError(f"No overlap after drag at page {page + 1}; stopping to avoid missed hearts.")
        previous = visible_titles
        before = len(all_seen)
        for title, checked in visible:
            all_seen.add(title)
            if checked and title not in seen:
                titles.append(title)
                seen.add(title)
        OUT.write_text(json.dumps({"complete": False, "favorites": titles, "titles_seen": len(all_seen)}, ensure_ascii=False, indent=2), encoding="utf-8")
        unchanged = unchanged + 1 if len(all_seen) == before else 0
        print(f"Page {page + 1}: {len(all_seen)} titles, {len(titles)} favorites", flush=True)
        if unchanged >= 3:
            OUT.write_text(json.dumps({"complete": True, "favorites": titles, "titles_seen": len(all_seen)}, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"Complete UI scan: {len(all_seen)} titles, {len(titles)} favorites", flush=True)
            return
        adb("shell", "input", "swipe", "700", "2300", "700", "1000", "1000")
        time.sleep(0.1)
    raise RuntimeError("Reached page limit before the end of the list.")


if __name__ == "__main__":
    main()
