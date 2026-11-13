"""Classify early failed ChefTap media URLs with small read-only HEAD checks."""
import sqlite3
import json
import urllib.error
import urllib.request
from pathlib import Path

root = Path(__file__).resolve().parents[1]
db = sqlite3.connect(f"file:{root / 'data/neussenombox.db'}?mode=ro", uri=True)
missing = [(photo_id, url) for photo_id, url in db.execute(
    "select photo_id,link from media_id where date_deleted is null and link is not null limit 500"
) if not (root / "data/photos" / f"{photo_id}.png").exists()][:10]
for photo_id, url in missing:
    try:
        with urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=10) as response:
            print(photo_id, response.status, response.headers.get("Content-Type"))
    except urllib.error.HTTPError as error:
        print(photo_id, error.code, error.headers.get("Content-Type"))
    except Exception as error:
        print(photo_id, type(error).__name__, str(error)[:80])
if missing:
    photo_id, url = missing[0]
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "RecipeTap photo recovery"}), timeout=35) as response:
            print("GET", photo_id, response.status, response.headers.get("Content-Type"), response.headers.get("Content-Length"), response.read(32))
    except Exception as error:
        print("GET", photo_id, type(error).__name__, str(error)[:120])
for photo_id in json.loads((root / "data/photo_failures.json").read_text(encoding="utf-8")):
    url = db.execute("select link from media_id where photo_id=?", (photo_id,)).fetchone()[0]
    try:
        with urllib.request.urlopen(url, timeout=15) as response:
            print("FAILED", photo_id, response.headers.get("Content-Type"), response.headers.get("Content-Length"), response.read(32))
    except Exception as error:
        print("FAILED", photo_id, type(error).__name__, str(error)[:120])
