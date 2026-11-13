"""Validate a ChefTap developer snapshot and extract its SQLite database safely."""
import argparse
import hashlib
import shutil
import sqlite3
import zipfile
from contextlib import closing
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARCHIVE = ROOT / "data/cheftap-snapshot.zip"
DATABASE = ROOT / "data/neussenombox.db"


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", nargs="?", type=Path, default=DEFAULT_ARCHIVE)
    args = parser.parse_args()
    archive_path = args.archive.resolve()
    if not archive_path.is_file():
        raise SystemExit(f"Snapshot archive not found: {archive_path}")
    DATABASE.parent.mkdir(parents=True, exist_ok=True)
    temporary = DATABASE.with_suffix(".db.part")
    try:
        with zipfile.ZipFile(archive_path) as archive:
            matches = [item for item in archive.infolist() if Path(item.filename).name == "neussenombox.db" and not item.is_dir()]
            if len(matches) != 1:
                raise SystemExit(f"Expected one neussenombox.db in snapshot; found {len(matches)}")
            with archive.open(matches[0]) as source, temporary.open("wb") as target:
                shutil.copyfileobj(source, target)
        with closing(sqlite3.connect(temporary)) as db:
            if db.execute("pragma quick_check").fetchone()[0] != "ok":
                raise SystemExit("Snapshot SQLite integrity check failed")
            recipes = db.execute("select count(*) from recipes where date_deleted is null").fetchone()[0]
            favorites = db.execute("select count(*) from recipes where date_deleted is null and favorite=1").fetchone()[0]
        if DATABASE.exists():
            if digest(DATABASE) != digest(temporary):
                raise SystemExit(f"A different database already exists at {DATABASE}; preserve or rename it before importing this snapshot")
            print(f"Snapshot already extracted: {recipes} recipes, {favorites} favorites")
        else:
            temporary.replace(DATABASE)
            print(f"Extracted snapshot: {recipes} recipes, {favorites} favorites -> {DATABASE}")
    finally:
        temporary.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
