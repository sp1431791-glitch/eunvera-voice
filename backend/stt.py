# STT is modular. Default provider runs ON THE PHONE (free, on-device):
#   Android WebView / Chrome SpeechRecognition (Web Speech API) - no key, no cost.
# Optional local server provider (free, open source, heavier):
#   faster-whisper - install with: pip install faster-whisper
import os

def available_stt_providers():
    provs = [{"id": "webspeech", "name": "On-device Web Speech (Android/Chrome)", "free": True, "on_server": False}]
    try:
        import faster_whisper  # noqa
        provs.append({"id": "faster-whisper", "name": "faster-whisper (local, open source)", "free": True, "on_server": True})
    except Exception:
        pass
    return provs
