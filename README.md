# EUNVERA VOICE
A real, working premium AI voice assistant for Android. Hindi / English / Hinglish.
Free stack: on-device STT+TTS, FastAPI brain, free Gemini tier, free tools.

## Run (2 minutes)
```
cd backend
pip install -r requirements.txt
python run.py
```
Open http://localhost:8766 in Chrome (desktop or phone). Tap the mic and speak.
Without any API key it runs in honest OFFLINE mode: notes, tasks, reminders,
memory, weather, translate, time, app opening, briefing. Add a FREE Gemini key
(copy backend/.env.example to backend/.env) for full natural reasoning.

## APK
Every push builds a debug APK automatically (GitHub Actions, free):
Actions tab > latest run > Artifacts > eunvera-voice-apk. Full details in docs/APK_BUILD.md.

## Full docs
docs/PHASE1_ANALYSIS.md (architecture + roadmap) | docs/APK_BUILD.md (APK) |
docs/TESTING.md (test log) | docs/SECURITY.md | scripts/ (helpers)
