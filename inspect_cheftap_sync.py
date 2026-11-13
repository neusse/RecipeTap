"""Read public string constants in the installed ChefTap APK for sync clues."""
import re
import zipfile
from pathlib import Path


apk = Path(__file__).parent / "data/cheftap-original.apk"
if not apk.exists():
    raise SystemExit(f"Missing APK: {apk}")
matches = set()
with zipfile.ZipFile(apk) as archive:
    for name in archive.namelist():
        if not (name.endswith(".dex") or name == "resources.arsc"):
            continue
        data = archive.read(name)
        for raw in re.findall(rb"(?:https?://|wss?://)[\x21-\x7e]{4,220}", data):
            value = raw.decode("ascii", errors="ignore").split("\\u0000")[0]
            if "cheftap" in value.lower():
                matches.add(value)
for value in sorted(matches):
    print(value)
