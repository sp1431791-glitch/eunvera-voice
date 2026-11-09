# Security model
- Microphone: only while the mic button is active or continuous mode is on IN
  THE APP. No background recording. Wake word runs in-app only.
- All data stays in your own backend's SQLite file. Nothing is sent anywhere
  except the AI provider you configure.
- API keys live in backend/.env only - never in the app, never in chat.
- Every tool call and chat turn is written to an audit log (Settings > Audit log).
- One tap in Memory Manager deletes everything (chats, memory, tasks, notes,
  reminders, audit).
- Android permissions are runtime-requested (RECORD_AUDIO, optional
  notifications). No accessibility-service tricks, no security bypasses.
