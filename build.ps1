$ErrorActionPreference = 'Stop'
$root = (Get-Location).Path
$sdk = $env:ANDROID_HOME
if (-not $sdk) { throw 'ANDROID_HOME is not set.' }
$tools = Join-Path $sdk 'build-tools\36.0.0'
$androidJar = Join-Path $sdk 'platforms\android-36\android.jar'
$out = Join-Path $root 'build'
New-Item -ItemType Directory -Force -Path $out, (Join-Path $out 'classes') | Out-Null
python (Join-Path $root 'generate_recipes.py')
if ($LASTEXITCODE -ne 0) { throw 'Recipe generation failed.' }
& (Join-Path $tools 'aapt2.exe') link -o (Join-Path $out 'base.apk') --manifest (Join-Path $root 'app\src\main\AndroidManifest.xml') -I $androidJar -A (Join-Path $root 'app\src\main\assets') --min-sdk-version 26 --target-sdk-version 34
if ($LASTEXITCODE -ne 0) { throw 'Resource packaging failed.' }
& javac --release 8 -cp $androidJar -d (Join-Path $out 'classes') (Join-Path $root 'app\src\main\java\com\recipetap\MainActivity.java')
if ($LASTEXITCODE -ne 0) { throw 'Java compilation failed.' }
$classFiles = @(Get-ChildItem -LiteralPath (Join-Path $out 'classes\com\recipetap') -Filter '*.class' | ForEach-Object FullName)
& (Join-Path $tools 'd8.bat') --lib $androidJar --output $out $classFiles
if ($LASTEXITCODE -ne 0) { throw 'Dex compilation failed.' }
Copy-Item (Join-Path $out 'base.apk') (Join-Path $out 'unsigned.apk') -Force
Push-Location $out
try { & (Join-Path $tools 'aapt.exe') add 'unsigned.apk' 'classes.dex' }
finally { Pop-Location }
if ($LASTEXITCODE -ne 0) { throw 'APK assembly failed.' }
$key = Join-Path $env:USERPROFILE '.android\debug.keystore'
if (-not (Test-Path $key)) {
    New-Item -ItemType Directory -Force -Path (Split-Path $key) | Out-Null
    & keytool -genkeypair -keystore $key -storepass android -alias androiddebugkey -keypass android -dname 'CN=Android Debug,O=Android,C=US' -keyalg RSA -keysize 2048 -validity 10000
    if ($LASTEXITCODE -ne 0) { throw 'Debug key generation failed.' }
}
& (Join-Path $tools 'apksigner.bat') sign --ks $key --ks-key-alias androiddebugkey --ks-pass pass:android --key-pass pass:android --out (Join-Path $out 'RecipeTap.apk') (Join-Path $out 'unsigned.apk')
if ($LASTEXITCODE -ne 0) { throw 'APK signing failed.' }
Write-Output (Join-Path $out 'RecipeTap.apk')
