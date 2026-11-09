import os, json, asyncio
from typing import Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel
from brain import Brain
from memory import Memory
from tools import ToolBox
from stt import available_stt_providers
from tts import available_tts_providers
from config import CONFIG

app = FastAPI(title="EUNVERA VOICE Brain", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

MEM = Memory()
TOOLS = ToolBox(MEM)
BRAIN = Brain(MEM, TOOLS)

class ChatIn(BaseModel):
    message: str
    session: str = "default"
    lang: str = "en"

class ItemIn(BaseModel):
    key: Optional[str] = None
    value: Optional[str] = None
    id: Optional[int] = None
    title: Optional[str] = None
    body: Optional[str] = None
    text: Optional[str] = None
    minutes: Optional[float] = None

@app.get("/api/status")
def status():
    return {"name": "EUNVERA VOICE", "version": "0.1.0",
            "active_provider": BRAIN.active_provider(),
            "providers": BRAIN.provider_status(),
            "stt": available_stt_providers(), "tts": available_tts_providers(),
            "tools": TOOLS.list_tools()}

@app.post("/api/chat")
def chat(inp: ChatIn):
    reply, meta = BRAIN.respond(inp.message, inp.session, inp.lang)
    return {"reply": reply, "meta": meta}

@app.post("/api/chat/stream")
def chat_stream(inp: ChatIn):
    def gen():
        for chunk in BRAIN.respond_stream(inp.message, inp.session, inp.lang):
            yield chunk.encode("utf-8")
    return StreamingResponse(gen(), media_type="text/plain; charset=utf-8")

@app.get("/api/history")
def history(session: str = "default", limit: int = 100):
    return MEM.history(session, limit)

@app.get("/api/sessions")
def sessions():
    return MEM.sessions()

@app.get("/api/memory")
def memory(q: Optional[str] = None):
    return MEM.recall(q)

@app.post("/api/memory")
def memory_add(inp: ItemIn):
    if not inp.key or not inp.value: raise HTTPException(400, "key and value required")
    MEM.remember(inp.key, inp.value); return {"ok": True}

@app.delete("/api/memory/{item_id}")
def memory_del(item_id: int):
    MEM.forget(item_id); return {"ok": True}

@app.get("/api/tasks")
def tasks():
    return MEM.tasks()

@app.post("/api/tasks")
def tasks_add(inp: ItemIn):
    if not inp.text: raise HTTPException(400, "text required")
    return MEM.add_task(inp.text)

@app.post("/api/tasks/{task_id}/done")
def tasks_done(task_id: int):
    MEM.complete_task(task_id); return {"ok": True}

@app.get("/api/notes")
def notes():
    return MEM.notes()

@app.post("/api/notes")
def notes_add(inp: ItemIn):
    if not inp.title: raise HTTPException(400, "title required")
    MEM.add_note(inp.title, inp.body or ""); return {"ok": True}

@app.get("/api/reminders")
def reminders():
    return MEM.reminders()

@app.post("/api/reminders")
def reminders_add(inp: ItemIn):
    if not inp.text: raise HTTPException(400, "text required")
    import time
    due = time.time() + (inp.minutes or 5) * 60
    MEM.add_reminder(inp.text, due); return {"ok": True, "due": due}

@app.get("/api/reminders/due")
def reminders_due():
    rows = MEM.due_reminders()
    for r in rows: MEM.mark_fired(r["id"])
    return rows

@app.get("/api/audit")
def audit():
    return MEM.get_audit()

@app.post("/api/wipe")
def wipe():
    MEM.wipe_all(); return {"ok": True, "wiped": "all conversations, memory, tasks, notes, reminders, audit"}

@app.get("/api/tts")
def tts(text: str, lang: str = "hi-IN"):
    try:
        path = __import__("tts").synth_to_file(text, lang)
        return FileResponse(path, media_type="audio/mpeg", filename="eunvera_tts.mp3")
    except ImportError:
        raise HTTPException(501, "server TTS not installed; the app uses on-device voices (free). Install edge-tts to enable this.")

@app.post("/api/stt")
async def stt(file: UploadFile = File(None)):
    try:
        import faster_whisper  # noqa
    except ImportError:
        raise HTTPException(501, "server STT not installed; the app uses on-device speech recognition (free). Install faster-whisper to enable this.")

@app.websocket("/ws")
async def ws(sock: WebSocket):
    await sock.accept()
    session = "default"
    try:
        while True:
            data = json.loads(await sock.receive_text())
            if data.get("type") == "chat":
                session = data.get("session", session)
                reply, meta = BRAIN.respond(data.get("message", ""), session, data.get("lang", "en"))
                await sock.send_text(json.dumps({"type": "reply", "reply": reply, "meta": meta}))
    except WebSocketDisconnect:
        return

_FRONT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
if os.path.isdir(_FRONT):
    from fastapi.staticfiles import StaticFiles
    app.mount("/", StaticFiles(directory=_FRONT, html=True), name="ui")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=CONFIG["port"])
