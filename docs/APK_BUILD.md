# Build the EUNVERA VOICE APK (free)

## Route A - GitHub Actions (recommended, zero installs)
1. This repo's `.github/workflows/apk.yml` builds `app-debug.apk` on every push.
2. Open the Actions tab, open the latest run, download the artifact `eunvera-voice-apk`.
3. Install it on the phone (allow unknown sources).

## Route B - Your laptop (Windows/Mac/Linux)
Needs: Node 20+, JDK 17, Android SDK (Android Studio installs it).
```
cd eunvera-voice
node scripts/setup-android.js        # creates the Capacitor android project
cd android && ./gradlew assembleDebug   # Windows: gradlew.bat assembleDebug
# APK at android/app/build/outputs/apk/debug/app-debug.apk
```

## Route C - Android Studio
Run `node scripts/setup-android.js`, then open the `android/` folder in
Android Studio and press Run - it installs directly to a connected phone.

After install: app Settings > Backend URL = http://<your-PC-LAN-IP>:8766
(or open the same URL in Chrome - the backend serves the full UI).
