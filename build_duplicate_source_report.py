"""Build a private, browsable map of ChefTap source URLs to recipes."""
import csv
import html
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlsplit

root = Path(__file__).parent
database = root / "data/neussenombox.db"
if not database.exists():
    raise SystemExit(f"Missing real ChefTap snapshot: {database}")
db = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
groups = defaultdict(list)
for recipe_id, title, source_url, favorite in db.execute(
    "select id,title,source_url,favorite from recipes "
    "where date_deleted is null and source_url is not null and trim(source_url) <> ''"
):
    groups[source_url.strip()].append({"id": recipe_id, "title": title or "(untitled)", "favorite": bool(favorite)})
groups = [(url, recipes) for url, recipes in groups.items() if len(recipes) > 1]
groups.sort(key=lambda item: (-len(item[1]), item[0].casefold()))
if not groups:
    raise SystemExit("No repeated source URLs in the snapshot")

out = root / "data"
out.mkdir(exist_ok=True)
csv_path = out / "duplicate_source_relationships.csv"
with csv_path.open("w", encoding="utf-8-sig", newline="") as stream:
    writer = csv.writer(stream)
    writer.writerow(("source_url", "group_size", "recipe_title", "same_title_count", "favorite", "recipe_id"))
    for url, recipes in groups:
        titles = Counter(recipe["title"].strip() for recipe in recipes)
        for recipe in recipes:
            writer.writerow((url, len(recipes), recipe["title"], titles[recipe["title"].strip()], int(recipe["favorite"]), recipe["id"]))

cards = []
exact_groups = 0
for index, (url, recipes) in enumerate(groups, 1):
    titles = Counter(recipe["title"].strip() for recipe in recipes)
    has_exact = any(count > 1 for count in titles.values())
    exact_groups += has_exact
    parsed = urlsplit(url)
    display = parsed.netloc + parsed.path if parsed.netloc else url
    display = display[:130] + ("…" if len(display) > 130 else "")
    safe_url = html.escape(url, quote=True)
    link = f'<a href="{safe_url}" target="_blank" rel="noopener noreferrer">{safe_url}</a>' if parsed.scheme in ("http", "https") else html.escape(url)
    items = []
    for recipe in sorted(recipes, key=lambda value: value["title"].casefold()):
        title = recipe["title"]
        badges = []
        if titles[title.strip()] > 1:
            badges.append('<span class="badge exact">exact title match</span>')
        if re.search(r"\s+version\s+\d+$", title, re.I):
            badges.append('<span class="badge version">version label</span>')
        if recipe["favorite"]:
            badges.append('<span class="badge favorite">♥ favorite</span>')
        items.append(f'<li><span class="recipeTitle">{html.escape(title)}</span>{"".join(badges)}<small>ID: {html.escape(recipe["id"])}</small></li>')
    cards.append(
        f'<details class="group" data-exact="{int(has_exact)}" '
        f'data-search="{html.escape((url + " " + " ".join(r["title"] for r in recipes)).casefold(), quote=True)}" '
        f'{"open" if index <= 5 else ""}>'
        f'<summary><strong>{len(recipes)} recipes</strong><span>{html.escape(display)}</span>'
        f'{"<em>exact title match</em>" if has_exact else ""}</summary>'
        f'<div class="source"><b>Source URL</b>{link}</div><ol>{"".join(items)}</ol></details>'
    )

report = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>RecipeTap · Shared source URLs</title>
<style>
:root{{font-family:Arial,sans-serif;color:#263128;background:#f5f7f2}}*{{box-sizing:border-box}}body{{margin:0}}
header{{background:#628c35;color:white;padding:22px max(20px,calc((100vw - 1050px)/2))}}h1{{margin:0 0 7px;font-size:1.7rem}}header p{{margin:0;line-height:1.45}}
main{{max-width:1050px;margin:auto;padding:20px}}.stats{{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:16px}}.stat{{background:white;border:1px solid #dce4d5;border-radius:10px;padding:12px 16px;min-width:130px}}.stat b{{display:block;font-size:1.5rem;color:#4c7626}}.stat span{{font-size:.86rem;color:#526052}}
.controls{{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin:14px 0}}input[type=search]{{flex:1;min-width:230px;padding:11px;border:1px solid #b8c6af;border-radius:8px;font:inherit}}button{{padding:10px 13px;border:1px solid #a8ba9b;background:white;border-radius:8px;cursor:pointer}}label{{white-space:nowrap}}#visible{{color:#637063;font-size:.9rem}}
.group{{background:white;border:1px solid #dce4d5;border-radius:10px;margin:9px 0;overflow:hidden}}summary{{display:flex;align-items:center;gap:12px;cursor:pointer;padding:13px 16px;list-style:none}}summary::-webkit-details-marker{{display:none}}summary:before{{content:'▸';color:#628c35}}details[open] summary:before{{content:'▾'}}summary strong{{min-width:90px;color:#4c7626}}summary span{{overflow-wrap:anywhere;flex:1}}summary em{{font-size:.75rem;color:#a14f35;font-style:normal;background:#fff0e8;padding:4px 7px;border-radius:5px}}.source{{padding:0 18px 14px;border-top:1px solid #edf0e9;display:grid;gap:4px}}.source b{{margin-top:12px;font-size:.8rem;color:#697669}}a{{color:#496f24;overflow-wrap:anywhere}}ol{{margin:0;padding:0 18px 12px 45px}}li{{padding:9px 0;border-top:1px solid #eff2ed}}.recipeTitle{{font-weight:600}}small{{display:block;color:#8a9388;margin-top:3px;font-size:.7rem}}.badge{{font-size:.72rem;padding:3px 6px;margin-left:7px;border-radius:4px;white-space:nowrap}}.exact{{background:#fff0e8;color:#a14f35}}.version{{background:#eaf0fa;color:#4c6483}}.favorite{{background:#fbe8ef;color:#9c3a62}}
.note{{font-size:.9rem;line-height:1.5;color:#596659;margin:12px 0 18px}}
</style></head><body>
<header><h1>Shared source URLs</h1><p>ChefTap snapshot · each card connects one exact source URL to every recipe saved from it</p></header>
<main><div class="stats"><div class="stat"><b>{len(groups)}</b><span>shared URLs</span></div><div class="stat"><b>{sum(len(recipes) for _, recipes in groups)}</b><span>linked recipes</span></div><div class="stat"><b>{sum(len(recipes)-1 for _, recipes in groups)}</b><span>entries beyond one per URL</span></div><div class="stat"><b>{exact_groups}</b><span>groups with exact title matches</span></div></div>
<p class="note">A shared URL can be a page containing several different recipes. “Exact title match” identifies recipes with the same title under that URL. “Version label” only reflects the saved title; it does not establish identical content.</p>
<div class="controls"><input id="search" type="search" placeholder="Find a source URL or recipe title" aria-label="Search URLs and titles"><label><input id="exactOnly" type="checkbox"> Exact title matches only</label><button id="expand" type="button">Expand visible</button><button id="collapse" type="button">Collapse all</button><span id="visible"></span></div>
<section id="groups">{''.join(cards)}</section></main>
<script>
const groups=[...document.querySelectorAll('.group')];const search=document.getElementById('search');const exact=document.getElementById('exactOnly');const visible=document.getElementById('visible');
function filter(){{const q=search.value.trim().toLowerCase();let n=0;for(const group of groups){{const show=(!q||group.dataset.search.includes(q))&&(!exact.checked||group.dataset.exact==='1');group.hidden=!show;if(show)n++;}}visible.textContent=`${{n}} of ${{groups.length}} groups`;}}
search.addEventListener('input',filter);exact.addEventListener('change',filter);document.getElementById('expand').onclick=()=>groups.filter(g=>!g.hidden).forEach(g=>g.open=true);document.getElementById('collapse').onclick=()=>groups.forEach(g=>g.open=false);filter();
</script></body></html>'''
report_path = out / "duplicate_source_relationships.html"
report_path.write_text(report, encoding="utf-8")
print(f"Wrote {report_path} ({len(groups)} URLs, {sum(len(r) for _, r in groups)} recipes)")
print(f"Wrote {csv_path}")
