"""Summarize ChefTap's stored media links without printing private tokens."""
import sqlite3
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit


db_path = Path(__file__).resolve().parents[1] / "data/neussenombox.db"
if not db_path.exists():
    raise SystemExit("ChefTap snapshot database is missing")
db = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
rows = db.execute("select photo_id,attachment_id,link,confirmed from media_id").fetchall()
print("media_rows", len(rows))
print("with_link", sum(bool(row[2]) for row in rows))
print("hosts", Counter(urlsplit(row[2]).hostname for row in rows if row[2]).most_common())
for photo_id, attachment_id, link, confirmed in rows[:5]:
    parsed = urlsplit(link or "")
    print({"photo_id": photo_id, "attachment_id": attachment_id, "host": parsed.hostname, "path": parsed.path, "has_query": bool(parsed.query), "confirmed": confirmed})
