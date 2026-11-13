"""Read visible ChefTap preference values from its Settings sheet.

Open ChefTap > Recipes > More > Settings first. This script changes nothing.
"""
import json
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).parent
subprocess.run(["adb", "shell", "uiautomator", "dump", "/sdcard/window.xml"], check=True, capture_output=True)
xml = subprocess.run(["adb", "exec-out", "cat", "/sdcard/window.xml"], check=True, capture_output=True).stdout
root = ET.fromstring(xml)
values = {}
for group in root.iter("node"):
    title = next((n.get("text") for n in group if n.get("resource-id", "").endswith("/title")), None)
    checkbox = next((n.get("checked") == "true" for n in group if n.get("resource-id", "").endswith("/checkbox")), None)
    if title and checkbox is not None:
        values[title] = checkbox
required = {"Keep screen on", "Fast scrolling"}
if not required.issubset(values):
    raise RuntimeError(f"Settings sheet was not fully visible; found {sorted(values)}")
output = {"keepScreenOn": values["Keep screen on"], "fastScrolling": values["Fast scrolling"]}
destination = ROOT / "data" / "cheftap_settings.json"
destination.parent.mkdir(exist_ok=True)
destination.write_text(json.dumps(output, indent=2), encoding="utf-8")
print(output)
