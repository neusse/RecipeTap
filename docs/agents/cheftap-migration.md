# ChefTap to RecipeTap migration runbook

Use this when an AI assistant is asked to recover the owner's ChefTap data,
merge it into RecipeTap, compile an APK, and install it on the owner's Android
phone. Work from the repository root on Windows. Every recipe, favorite, note,
photo, and setting must come from a real export, snapshot, or visible phone UI.
Never invent replacements or silently report a partial import as complete.

## What still needs a person

| Action | Why the assistant cannot assume it happened |
| --- | --- |
| Unlock the phone, connect USB, and approve the USB debugging prompt | `adb` cannot authorize itself on the phone. |
| Open ChefTap and initiate its **HTML recipe export** | The export lives behind the old app's UI. A ZIP labelled `text` is not the HTML archive consumed by the build. |
| Open ChefTap's **Developer Snapshot** action and share its ZIP to RecipeTap | Android does not grant `adb` access to ChefTap's private app directory, even with Developer Options enabled. The app's menu label or location may vary. |
| Open ChefTap's Settings screen for preference capture | The settings collector reads only what is visibly present. |
| Approve sideload/install warnings if Android presents them | `build.ps1` creates a debug-signed APK, not a Play Store release. |

If a user has already saved either ZIP in the workspace or sent it by email,
locate that actual attachment and verify its contents. Do not repeat the phone
step just to recreate a file that is already present. Ask for help only when a
required UI action cannot be completed or a real file cannot be found.

## Inputs and outputs

| Path | Source and role |
| --- | --- |
| `cheftap_export.zip` | Owner's ChefTap **HTML** export; formatted recipe text. |
| `data/cheftap-snapshot.zip` | Optional Developer Snapshot shared from ChefTap to RecipeTap or saved from an attachment. |
| `data/neussenombox.db` | SQLite database extracted and checked by `scripts/extract_snapshot.py`; recipe IDs, favorites, notes, structured items, tags, and photo links. |
| `data/cheftap_settings.json` | Optional values read from the visible ChefTap Settings screen. |
| `data/photos/` | Verified images downloaded from the snapshot's media links. |
| `app/src/main/assets/recipes.js` | Generated private seed data used by the APK. |
| `build/RecipeTap.apk` | Debug-signed Android package to install. |

All of these owner data and build outputs are ignored by Git. Check
`git status --short` before any commit or push. The source repository must
remain usable without populated data.

## 1. Check tools and the connected phone

Use Python and PowerShell 7. Check `ANDROID_HOME`, Python, `javac`, `keytool`,
Android SDK Platform 36, Build-Tools 36.0.0, and `adb`. Use the repository's
`requirements.txt` for Beautiful Soup. Confirm exactly one intended device is
connected and shows as `device`, not `unauthorized`:

```powershell
python -m pip install -r .\requirements.txt
adb devices -l
```

If USB authorization is pending, have the owner accept the prompt on the
unlocked phone. Do not guess a device serial or operate another connected
device.

## 2. Get the HTML export

Have the owner use ChefTap's export/share flow to produce the HTML recipe ZIP.
Save the real archive as `cheftap_export.zip` in the repository root. If it
arrived by email, download the actual attachment to that path. Check that it
opens as ZIP and contains `.html` entries. The separate text export is not
read by `scripts/generate_recipes.py`; renaming it will not make it an HTML
export.

The build can run without an export as an **empty, usable** recipe app. It
prints that it is building an empty library. If a snapshot database is already
present but its HTML export is missing, generation stops instead of dropping
the snapshot data.

## 3. Get the optional Developer Snapshot

For a full migration, RecipeTap must already be installed as an Android share
target. If it is not installed yet, build and install it first using step 6.
Without an export yet, that build will be an empty app, which is enough to
receive the share. Keep any real files already present; never remove them to
force an empty build.

Have the owner open ChefTap's **Developer Snapshot** action and share the ZIP
to **RecipeTap** in Android's share sheet. RecipeTap should show a “Saved
ChefTap snapshot locally” toast and write the bytes to its own external app
directory. Pull that exact file over USB:

```powershell
New-Item -ItemType Directory -Force .\data
adb pull /sdcard/Android/data/com.recipetap/files/cheftap-snapshot.zip .\data\cheftap-snapshot.zip
python .\scripts\extract_snapshot.py
```

The extractor checks the ZIP contains one `neussenombox.db`, runs SQLite
`quick_check`, and prints active recipe and favorite counts. It refuses to
overwrite a different existing database. If the snapshot was saved directly
to the PC, place it at `data/cheftap-snapshot.zip` and run the same extractor.
If extraction fails, preserve both files and investigate; do not substitute
data or rename an unrelated archive.

The snapshot ZIP contains the database, not photo bytes. The old app's private
directory is not reachable with ordinary `adb`, and ChefTap cloud sync may be
blocked by the site's access rules. Neither is required for this path.

## 4. Capture settings and recover photos when available

For the two known preference flags, have the owner open ChefTap's Settings
sheet, with **Keep screen on** and **Fast scrolling** visible, then run:

```powershell
python .\scripts\collect_cheftap_settings.py
```

The script fails if those controls are not visible and writes only the values
it actually read. If the snapshot has media links, download the linked images
before building so the generated seed includes local filenames:

```powershell
python .\scripts\recover_photos.py
```

This can transfer gigabytes and may take time. It verifies PNG, JPEG, GIF, and
WebP bytes even when a server labels everything as PNG. A failed run leaves a
report at `data/photo_failures.json`; rerun to retry. If any link remains
unavailable, state the missing count explicitly and do not claim every photo
was recovered. The build includes only image files that exist locally.

`scripts/collect_cheftap_favorites.py` is a read-only UI fallback if the
snapshot is unavailable. It uses fixed-distance drags and checks screen
overlap, but its title list is **not** automatically merged by the current
generator. Do not promise exact favorite import without a snapshot.

## 5. Understand and verify the merge

`scripts/generate_recipes.py`, called by `build.ps1`, matches HTML entries to
active snapshot rows using title and source URL, then source URL, then a
normalized title. It retains the formatted HTML and adds the snapshot's stable
IDs, favorite flags, notes, tags, structured ingredients and directions, and
available local photo filenames. Snapshot-only recipes use their real
structured text. The generator stops if an HTML recipe cannot be matched.

Use an HTML export and snapshot from the same ChefTap collection when
possible. Read the generator's actual counts and check a few recipes, including
a favorite and a photo. Do not merge or delete recipes merely because they
share a source URL: one source page may contain several distinct recipes.

There are two separate layers of state:

1. The generated seed inside the APK comes from the export and snapshot.
2. RecipeTap's additions, edits, deletions, favorite toggles, shopping lists,
   plans, and menus are stored locally on the phone in WebView storage.

`adb install -r` with the same package name and signing key preserves the
local layer. On its first snapshot import, the app maps old export IDs to
snapshot IDs and imports snapshot favorites. This is a **one-time import**, not
ongoing two-way sync: a later snapshot's changed favorite flags are not
automatically reconciled. Never run `adb uninstall`, `pm clear`, or switch
signing keys as a routine update; those actions can lose local data or block
an in-place install. RecipeTap does not yet export its own local edits.

## 6. Build and install

Run from the repository root. In this owner's environment, use the global
PowerShell runner; elsewhere, `pwsh -File .\build.ps1` is equivalent:

```powershell
safe-pwsh --file .\build.ps1
adb install -r .\build\RecipeTap.apk
```

If installation reports a signing mismatch, stop and preserve the installed
app and its data. Do not uninstall it automatically. Have the owner resolve
the signing key or data backup choice.

If photos were recovered, transfer them to RecipeTap's app storage after the
APK is installed:

```powershell
python .\scripts\push_photos.py
```

The transfer checks filenames on the phone. Open RecipeTap and verify the
recipe count, a favorite, formatted ingredients and directions, a clickable
source, and a local photo. Report actual counts, any failed links, and any
manual step that remains. Leave the original ChefTap app and its data intact.
