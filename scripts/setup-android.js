/* Creates the Capacitor Android project for EUNVERA VOICE (run once, needs Node 20+). */
const { execSync } = require("child_process");
const fs = require("fs");
const path = require("path");
const root = path.resolve(__dirname, "..");
process.chdir(root);
const pkg = { name: "eunvera-voice", version: "0.1.0",
  dependencies: { "@capacitor/core": "^6.0.0", "@capacitor/android": "^6.0.0", "@capacitor/app": "^6.0.0" },
  devDependencies: { "@capacitor/cli": "^6.0.0" } };
fs.writeFileSync("package.json", JSON.stringify(pkg, null, 2));
fs.rmSync("android", { recursive: true, force: true });
execSync("npm install", { stdio: "inherit" });
fs.writeFileSync("capacitor.config.json", JSON.stringify({
  appId: "com.eunvera.voice", appName: "EUNVERA VOICE", webDir: "frontend" }, null, 2));
execSync("npx cap add android", { stdio: "inherit" });
// mic + speech permissions
const mf = "android/app/src/main/AndroidManifest.xml";
let xml = fs.readFileSync(mf, "utf8");
const perms = ["RECORD_AUDIO", "INTERNET", "VIBRATE", "POST_NOTIFICATIONS"]
  .map(p => `    <uses-permission android:name="android.permission.${p}" />`).join("\n");
xml = xml.replace("<application", perms + "\n    <application");
fs.writeFileSync(mf, xml);
execSync("npx cap sync android", { stdio: "inherit" });
console.log("Done. cd android && ./gradlew assembleDebug");
