<p align="center">
  <img src="docs/assets/recipetap-banner.svg" alt="RecipeTap: an offline home for your recipes" width="100%">
</p>

<h1 align="center">RecipeTap</h1>

<p align="center">Your recipe collection, organized and available offline on Android.</p>

<p align="center">
  <kbd>Android 8.0+</kbd>&nbsp;&nbsp;
  <kbd>Offline first</kbd>&nbsp;&nbsp;
  <kbd>Bring your own recipes</kbd>&nbsp;&nbsp;
  <kbd>Source build</kbd>
</p>

RecipeTap is an **Android only** recipe organizer. It runs with an empty library for new recipes, or you can build it with your own ChefTap HTML export and optional local developer snapshot. It runs as a separate app and does not change the installed ChefTap app. This project is independent and is not affiliated with ChefTap or its developer. There is no iOS, desktop, browser, or Play Store release.

## What it does

- Browse and search recipes; filter by tags and favorites.
- Read prep details, ingredients, directions, and notes in a sectioned recipe view. The original exported text remains available below the structured view.
- Show recovered recipe photos from the app's own storage, with no connection needed while viewing.
- Open a recipe's source URL in the phone's browser.
- Add, edit, duplicate, delete, and favorite recipes.
- Build shopping lists, plan meals, and group recipes into menus.
- Receive shared text from Android for manual recipe entry.

ChefTap's cloud sync and website clipping are **not** implemented. RecipeTap does not have the Android `INTERNET` permission. Changes made in RecipeTap live in the app's local storage; installing an update over the same package keeps them, but uninstalling the app removes them. There is not yet a RecipeTap backup or restore feature.

## Build for Android

The current build is Windows native. You need:

- Windows with PowerShell 7 (`pwsh`), Python 3, and a JDK with `javac` and `keytool` on `PATH`.
- Android SDK Platform 36, Build-Tools 36.0.0, and Platform-Tools (`adb` on `PATH`). Set `ANDROID_HOME` to your SDK directory.
- Optionally, your own ChefTap HTML export ZIP if you want to migrate existing recipes. No personal or sample recipe data is in this repository.

Install the Python dependency and build. A clean checkout produces a working app with an empty library and an Add Recipe button:

```powershell
python -m pip install -r .\requirements.txt
pwsh -File .\build.ps1
adb install -r .\build\RecipeTap.apk
```

`build.ps1` produces `build/RecipeTap.apk` and signs it with the standard Android **debug key**. It is a sideloaded development build, not a release signed Play Store package. Android may show a sideload or Play Protect warning.

To include your ChefTap recipes, place your HTML export at the project root as `cheftap_export.zip` and build again. The build reports whether it found an export. It never inserts synthetic recipe content. An empty or invalid export causes a build error.

### Restore more from a local snapshot

The HTML export provides recipe text. For exact favorite flags, saved notes, structured recipe sections, and photo links, place the extracted developer snapshot database at `data/neussenombox.db` before building. A collected preference file can be placed at `data/cheftap_settings.json`. Without those files, the build announces what is unavailable and uses only the real export data. If a snapshot is present without the HTML export, the build stops rather than silently discarding that data.

If the snapshot contains media links, recover and verify the images **before** building so the generated recipe data includes them:

```powershell
python .\recover_photos.py
pwsh -File .\build.ps1
adb install -r .\build\RecipeTap.apk
python .\push_photos.py
```

`recover_photos.py` downloads images from the URLs in your snapshot into `data/photos/`, identifies their actual format from their bytes, and fails if any image cannot be recovered. `push_photos.py` copies those files over USB to RecipeTap's app storage on the connected phone and checks the transferred filenames. These images are not bundled into the APK.

## Project layout

| Path | Purpose |
| --- | --- |
| `app/src/main/` | Android activity, manifest, and local HTML/CSS/JavaScript UI |
| `generate_recipes.py` | Converts the owner's export and optional snapshot into the generated app asset |
| `build.ps1` | Builds and debug signs the APK with Android SDK tools |
| `recover_photos.py`, `push_photos.py` | Recover and transfer the owner's recipe photos |
| `data/` | Local snapshots, photos, and reports; ignored by Git |

Personal exports, the snapshot database, photos, generated `recipes.js`, and APKs are intentionally excluded from Git. Check `git status` before committing if you add other local files.

## Current scope

This is a personal work alike app, not a byte for byte ChefTap replacement. It has no ChefTap account login, cloud sync, automatic website clipping, or backup of RecipeTap edits. The source is provided so the owner can keep using and improving the app without depending on access to the original service.
