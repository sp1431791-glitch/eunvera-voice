# Test log - Phase 1

Recorded on 9 Nov 2026 by running the backend live (offline mode, no keys):

- /api/status: OK. Reports active_provider=offline, 12 tools, provider table.
- /api/chat (Hinglish weather): OK. Real Open-Meteo call returned Amritsar temp.
- /api/chat (note): OK. Note saved and visible via /api/notes.
- /api/chat (remember): OK. Memory item stored, returned via /api/memory.
- /api/chat (tasks): OK. Task added/listed/completed via API.
- /api/reminders + /api/reminders/due: OK (due fires once, marks fired).
- /api/history + /api/sessions: OK.
- /api/wipe: OK (clears everything, writes audit entry).
- Frontend served at http://localhost:8766/: OK.
- On-device STT/TTS: verified in Chrome; packaged APK STT depends on the
  device WebView (documented fallback: text input / faster-whisper).
- Provider calls (Gemini/OpenAI/Claude): NOT tested here - no keys configured.
  Status honestly shows "not connected" until you add a free Gemini key.

Environment limits: Wajo's sandbox has no Android SDK, so no APK artifact was
built here; the GitHub Actions workflow in this repo builds it.
