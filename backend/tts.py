# TTS is modular. Default provider runs ON THE PHONE (free, offline voices):
#   Android/Chrome SpeechSynthesis - no key, no cost, supports hi-IN and en-IN.
# Optional server providers (free):
#   edge-tts  (pip install edge-tts) - Microsoft neural voices, free public endpoint
#   Piper     (open source, fully offline) - optional, not bundled here
import os, tempfile

def available_tts_providers():
    provs = [{"id": "webspeech", "name": "On-device SpeechSynthesis (Android/Chrome)", "free": True, "on_server": False}]
    try:
        import edge_tts  # noqa
        provs.append({"id": "edge-tts", "name": "edge-tts neural voices (free)", "free": True, "on_server": True})
    except Exception:
        pass
    return provs

def synth_to_file(text, lang="hi-IN", voice=None):
    """Returns a wav/mp3 path using edge-tts when installed; raises otherwise."""
    import asyncio, edge_tts
    voice = voice or ("hi-IN-MadhurNeural" if lang.startswith("hi") else "en-IN-PrabhatNeural")
    out = os.path.join(tempfile.gettempdir(), "eunvera_tts.mp3")
    async def go():
        ch = edge_tts.Communicate(text, voice)
        await ch.save(out)
    asyncio.run(go())
    return out
