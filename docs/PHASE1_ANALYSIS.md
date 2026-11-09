# EUNVERA VOICE - Phase 1 Analysis, Architecture & Roadmap

## 1. Requirements analysis
EUNVERA VOICE is a real Android voice assistant: mic -> speech-to-text -> AI brain
(+tools) -> text-to-speech, with memory, Hindi/English/Hinglish, Android app
control, premium UI, and a zero-budget stack. It must be honest: no fake demos,
no placeholder AI, no silent recording.

## 2. Architecture (hybrid)
```
[Phone: Android app (Capacitor WebView)]
  On-device STT  (Android speech engine via Web Speech API - free, no key)
  On-device TTS  (SpeechSynthesis voices hi-IN / en-IN - free, offline-capable)
  UI: orb, waveform, transcript, 9 screens
        |  HTTP/WebSocket (LAN)
[Brain server: Python FastAPI]
  brain.py    - provider registry: Gemini / OpenAI-compatible / Claude / OFFLINE
                auto-selection by which key is present, JSON tool-calling
  tools.py    - notes, tasks, reminders, memory, weather (Open-Meteo, no key),
                translate (MyMemory free), web search (DuckDuckGo), open_app,
                daily briefing, time
  memory.py   - SQLite: chats, memory items, tasks, notes, reminders, audit log
  tts.py/stt.py - modular provider registries (optional server voices)
```
Key design choice: STT and TTS default to ON-DEVICE Android/Chrome engines.
They are genuinely free, work offline-ish, support hi-IN, and add zero server
load. Server providers (edge-tts, faster-whisper) are optional upgrades.

## 3. Free tools & APIs used
- Android/Chrome speech recognition + speech synthesis: free, on-device.
- Google Gemini API: free tier key from aistudio.google.com (rate-limited, NOT unlimited).
- Open-Meteo weather: free, no key.
- MyMemory translate: free tier (~limits per day).
- DuckDuckGo HTML search: free, unofficial.
- SQLite, FastAPI, Capacitor: open source.
- APK builds: GitHub Actions free tier, or Android Studio on a laptop.

## 4. Technical limitations (honest)
- Web Speech STT inside the packaged Android WebView: on many devices the
  recognition engine needs the Google app / network. If a device's WebView
  lacks it, the app falls back to text input. Server STT (faster-whisper) is
  the escape hatch.
- True background wake word ("always listening") is restricted by Android.
  Implemented as an in-app wake word; reliable 24/7 background listening
  needs a foreground service (Phase 7) or the Accessibility route (rejected:
  bypasses spirit of security rules).
- Free API tiers are rate-limited; offline mode always exists as fallback.
- MyMemory/edge-tts are third-party free services; they can change. Local
  alternatives documented.

## 5. Roadmap (test each phase before the next)
- Phase 1 DONE: structure, brain + tools + memory, premium UI, voice loop, docs.
- Phase 2: deeper UI polish, light theme audit, onboarding screen.
- Phase 3: STT hardening (device matrix, faster-whisper route, punctuation).
- Phase 4: server TTS option (edge-tts), voice picking UI, prosody pauses.
- Phase 5: real Gemini key testing, streaming, multi-model auto-failover.
- Phase 6: smarter memory (summarized rolling context, memory categories).
- Phase 7: Android integrations (foreground service, notifications reader,
  alarm/calendar intents, call/SMS with explicit confirmations).
- Phase 8: skills marketplace-style UI, custom user-defined skills.
- Phase 9: security audit, tests, backup/export.
- Phase 10: APK release via GitHub Actions + Play-style signing notes.

## 6. Build & test from your phone TODAY (no PC needed on phone side)
1. Phone + PC on same WiFi. On PC: `cd backend && pip install -r requirements.txt && python run.py`
2. Find PC IP (ipconfig/ifconfig), e.g. 192.168.1.5.
3. Install the APK (see docs/APK_BUILD.md), open EUNVERA VOICE > Settings >
   Backend URL = http://192.168.1.5:8766.
4. Or open http://192.168.1.5:8766/ in Chrome directly - the backend serves the UI too.
5. Tap the mic, speak Hindi/English, watch transcript + hear the reply.
