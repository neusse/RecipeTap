"""Capture the connected Android screen for visual app verification."""
import shutil
import subprocess
from pathlib import Path

adb = shutil.which("adb")
if not adb:
    raise SystemExit("adb was not found on PATH; install Android SDK Platform-Tools first.")
target = Path(__file__).parent / "data/phone-screen.png"
target.write_bytes(subprocess.check_output([adb, "exec-out", "screencap", "-p"]))
print(target)
