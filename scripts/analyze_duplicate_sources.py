"""Count active ChefTap recipes that share an exact source URL."""
import sqlite3
from pathlib import Path

database = Path(__file__).resolve().parents[1] / "data/neussenombox.db"
if not database.is_file():
    raise SystemExit(f"Missing ChefTap snapshot: {database}")
db = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
rows = db.execute(
    "select trim(source_url) as url, count(*) as n, group_concat(title, ' | ') as titles "
    "from recipes where date_deleted is null and source_url is not null "
    "and trim(source_url) <> '' group by trim(source_url) having count(*) > 1 "
    "order by n desc, url"
).fetchall()
total = db.execute("select count(*) from recipes where date_deleted is null").fetchone()[0]
with_url = db.execute(
    "select count(*) from recipes where date_deleted is null and source_url is not null and trim(source_url) <> ''"
).fetchone()[0]
print(f"active_recipes={total}")
print(f"with_source_url={with_url}")
print(f"duplicate_url_groups={len(rows)}")
print(f"recipes_in_duplicate_groups={sum(row[1] for row in rows)}")
print(f"extra_copies_beyond_one_per_url={sum(row[1] - 1 for row in rows)}")
print(f"largest_group={rows[0][1] if rows else 0}")
same_title = db.execute(
    "select count(*) as groups, coalesce(sum(n),0) as recipes, coalesce(sum(n-1),0) as extras "
    "from (select trim(source_url), trim(title), count(*) as n from recipes "
    "where date_deleted is null and source_url is not null and trim(source_url) <> '' "
    "group by trim(source_url), trim(title) having count(*) > 1)"
).fetchone()
print(f"same_url_and_exact_title_groups={same_title[0]}")
print(f"same_url_and_exact_title_recipes={same_title[1]}")
print(f"same_url_and_exact_title_extras={same_title[2]}")
for url, count, titles in rows[:10]:
    print(f"{count} | {url} | {titles[:250]}")
