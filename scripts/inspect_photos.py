"""Report recoverability of photo references in the local ChefTap snapshot."""
import sqlite3
from pathlib import Path


database = Path(__file__).resolve().parents[1] / "data/neussenombox.db"
if not database.exists():
    raise SystemExit(f"Missing real snapshot database: {database}")
db = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
db.row_factory = sqlite3.Row
summary = db.execute("""
    select count(*) as photos,
           sum(file_name is not null and trim(file_name)<>'') as named,
           sum(source is not null and trim(source)<>'') as sourced,
           count(distinct recipe_id) as recipes
    from recipe_photos where date_deleted is null
""").fetchone()
print(dict(summary))
print("source_examples", [row[0] for row in db.execute("select source from recipe_photos where source is not null and trim(source)<>'' limit 8")])
blobs = []
for row in db.execute("select name from sqlite_master where type='table'"):
    for column in db.execute(f'pragma table_info("{row[0]}")'):
        if "BLOB" in column[2].upper():
            blobs.append((row[0], column[1]))
print("blob_columns", blobs)
