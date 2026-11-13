"""Stream recovered photos to RecipeTap's app storage over the connected USB device."""
import argparse
import re
import shutil
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[1]
photos = root / "data/photos"
adb = shutil.which("adb")
if not adb:
    raise SystemExit("adb was not found on PATH; install Android SDK Platform-Tools first.")
destination = "/sdcard/Android/data/com.recipetap/files"
parser = argparse.ArgumentParser()
parser.add_argument("--limit", type=int, help="Transfer the first N images for a device test")
args = parser.parse_args()
files = sorted(path for path in photos.iterdir() if re.fullmatch(r"[0-9a-fA-F-]{36}\.(png|jpg|gif|webp)", path.name))
if not files:
    raise SystemExit("No verified photos found. Run scripts/recover_photos.py first.")
if args.limit:
    files = files[:args.limit]
subprocess.run([adb, "shell", "mkdir", "-p", destination + "/photos"], check=True)
log = root / "data/adb_photo_transfer.log"
with log.open("w", encoding="utf-8") as output:
    batches = [[adb, "push", str(photos), destination]] if args.limit is None else [
        [adb, "push", str(path), destination + "/photos/"] for path in files]
    for command in batches:
        process = subprocess.run(command, stdout=output, stderr=subprocess.STDOUT)
        if process.returncode:
            raise SystemExit(f"adb photo transfer failed ({process.returncode}): {log.read_text(errors='replace')[-1000:]}")
result = subprocess.run([adb, "shell", "find", destination + "/photos", "-type", "f"], capture_output=True, text=True, check=True)
on_phone = {line.strip().split("/")[-1] for line in result.stdout.splitlines()}
missing = {path.name for path in files} - on_phone
print(f"Verified {len(files) - len(missing)}/{len(files)} transferred photo filenames on phone")
if missing:
    raise SystemExit(f"{len(missing)} photos are missing on phone; rerun transfer")
