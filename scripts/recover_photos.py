"""Resume and verify ChefTap photo downloads from links in the owner's snapshot."""
import json
import sqlite3
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data/neussenombox.db"
PHOTOS = ROOT / "data/photos"
FAILURES = ROOT / "data/photo_failures.json"
if not DB.exists():
    raise SystemExit(f"Missing real snapshot database: {DB}")
PHOTOS.mkdir(parents=True, exist_ok=True)
db = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
items = db.execute("select photo_id,link from media_id where date_deleted is null and link is not null").fetchall()
if not items:
    raise SystemExit("Snapshot contains no linked photos; stopping.")


def recover(item):
    photo_id, url = item
    for extension, signature in (("png", b"\x89PNG\r\n\x1a\n"), ("jpg", b"\xff\xd8\xff"), ("gif", b"GIF8"), ("webp", b"RIFF")):
        target = PHOTOS / f"{photo_id}.{extension}"
        if target.exists() and target.stat().st_size > 8:
            with target.open("rb") as stream:
                if stream.read(8).startswith(signature):
                    return photo_id, "cached", None
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname not in {"s3-us-west-2.amazonaws.com", "media.cheftap.com"}:
        return photo_id, "failed", "Unexpected media host or scheme"
    request = urllib.request.Request(url, headers={"User-Agent": "RecipeTap photo recovery"})
    try:
        with urllib.request.urlopen(request, timeout=35) as response:
            content_type = response.headers.get("Content-Type", "")
            if response.status != 200 or not content_type.startswith("image/"):
                raise ValueError(f"Unexpected response {response.status} {content_type}")
            data = response.read(20_000_001)
            if len(data) > 20_000_000:
                raise ValueError("Oversized image")
            if data.startswith(b"\x89PNG\r\n\x1a\n"):
                extension = "png"
            elif data.startswith(b"\xff\xd8\xff"):
                extension = "jpg"
            elif data.startswith((b"GIF87a", b"GIF89a")):
                extension = "gif"
            elif data.startswith(b"RIFF") and data[8:12] == b"WEBP":
                extension = "webp"
            else:
                raise ValueError("Unrecognized image bytes")
        target = PHOTOS / f"{photo_id}.{extension}"
        temporary = target.with_suffix(".part")
        temporary.write_bytes(data)
        temporary.replace(target)
        return photo_id, "downloaded", None
    except Exception as error:
        return photo_id, "failed", f"{type(error).__name__}: {str(error)[:160]}"


results = {"cached": 0, "downloaded": 0, "failed": 0}
failures = {}
with ThreadPoolExecutor(max_workers=8) as pool:
    futures = [pool.submit(recover, item) for item in items]
    for index, future in enumerate(as_completed(futures), 1):
        photo_id, status, error = future.result()
        results[status] += 1
        if error:
            failures[photo_id] = error
        if index % 100 == 0 or index == len(items):
            print(f"{index}/{len(items)}: {results}", flush=True)
FAILURES.write_text(json.dumps(failures, indent=2), encoding="utf-8")
print(f"Total bytes: {sum(path.stat().st_size for path in PHOTOS.iterdir() if path.suffix in ('.png', '.jpg', '.gif', '.webp')):,}")
if failures:
    raise SystemExit(f"{len(failures)} photos failed; see {FAILURES}. Rerun to retry.")
