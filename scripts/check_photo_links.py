"""Check a few saved ChefTap media URLs with read-only HEAD requests."""
import sqlite3
import urllib.error
import urllib.request
from pathlib import Path


db_path = Path(__file__).resolve().parents[1] / "data/neussenombox.db"
if not db_path.exists():
    raise SystemExit("ChefTap snapshot database is missing")
db = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
rows = db.execute("select photo_id,link from media_id where link is not null limit 5").fetchall()
for photo_id, url in rows:
    request = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "RecipeTap local recovery check"})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            print(photo_id, response.status, response.headers.get("Content-Type"), response.headers.get("Content-Length"))
    except urllib.error.HTTPError as error:
        print(photo_id, error.code, error.headers.get("Content-Type"))
    except Exception as error:
        print(photo_id, type(error).__name__, str(error)[:100])
