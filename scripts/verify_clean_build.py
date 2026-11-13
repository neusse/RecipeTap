"""Verify the committed source builds without any private recipe files."""
import os
import subprocess
import tempfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
if not os.environ.get("ANDROID_HOME"):
    raise SystemExit("ANDROID_HOME is missing from this process")
with tempfile.TemporaryDirectory(prefix="recipetap-clean-") as temporary:
    clone = Path(temporary) / "repo"
    subprocess.run(["git", "clone", "--quiet", "--no-local", str(root), str(clone)], check=True)
    if (clone / "cheftap_export.zip").exists() or (clone / "data").exists():
        raise SystemExit("Clean clone unexpectedly contains personal recipe data")
    result = subprocess.run(["pwsh", "-File", "build.ps1"], cwd=clone, capture_output=True, text=True)
    print(result.stdout[-1500:])
    if result.returncode:
        print(result.stderr[-1500:])
        raise SystemExit(f"Clean build failed: {result.returncode}")
    generated = (clone / "app/src/main/assets/recipes.js").read_text(encoding="utf-8")
    if not generated.startswith("window.SEED_RECIPES=[];"):
        raise SystemExit("Clean build did not produce an empty library")
    apk = clone / "build/RecipeTap.apk"
    if not apk.is_file() or apk.stat().st_size == 0:
        raise SystemExit("Clean build did not produce an APK")
    print(f"Clean clone APK built: {apk.stat().st_size:,} bytes")
