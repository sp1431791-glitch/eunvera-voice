import json, re, urllib.request
from config import CONFIG
from tools import ToolBox

SYSTEM_PROMPT = """You are EUNVERA VOICE, a warm, human-like personal voice assistant.
Speak naturally, like a friendly person on a call. Keep spoken answers short (2-5 sentences) unless asked for detail.
Reply in the SAME language the user used: Hindi, English or Hinglish.
You can run ONE tool per turn. Available tools: {tools}
Always answer with STRICT JSON only, no markdown fences:
{{"reply": "<what you say out loud>", "tool": null or "<tool_name>", "args": {{...}}}}
Never invent tool results. If unsure, set tool null."""

class Brain:
    def __init__(self, mem, toolbox: ToolBox):
        self.mem = mem
        self.tools = toolbox
        self.tool_names = [t["name"] for t in toolbox.list_tools()]

    # ---------- provider plumbing ----------
    def _post(self, url, headers, body, timeout=45):
        req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", "replace"))

    def provider_status(self):
        st = []
        st.append({"id": "gemini", "name": "Google Gemini", "free_tier": True,
                   "connected": bool(CONFIG["gemini_key"]), "model": CONFIG["gemini_model"]})
        st.append({"id": "openai", "name": "OpenAI-compatible", "free_tier": "depends on base_url",
                   "connected": bool(CONFIG["openai_key"]), "model": CONFIG["openai_model"]})
        st.append({"id": "anthropic", "name": "Anthropic Claude", "free_tier": False,
                   "connected": bool(CONFIG["anthropic_key"]), "model": CONFIG["anthropic_model"]})
        st.append({"id": "offline", "name": "Offline mode (built-in)", "free_tier": True,
                   "connected": True, "model": "rule-based intents"})
        return st

    def active_provider(self):
        for k in ["gemini", "openai", "anthropic"]:
            if CONFIG.get(k + "_key"): return k
        return "offline"

    def _call_gemini(self, msgs):
        url = "https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent?key=%s" % (CONFIG["gemini_model"], CONFIG["gemini_key"])
        body = {"system_instruction": {"parts": [{"text": SYSTEM_PROMPT.format(tools=", ".join(self.tool_names))}]},
                "contents": [{"role": "user" if m["role"] != "assistant" else "model", "parts": [{"text": m["content"]}]} for m in msgs],
                "generationConfig": {"temperature": 0.7, "maxOutputTokens": 800}}
        j = self._post(url, {"Content-Type": "application/json"}, body)
        parts = j["candidates"][0]["content"]["parts"]
        return "".join(p.get("text", "") for p in parts)

    def _call_openai(self, msgs):
        sys = {"role": "system", "content": SYSTEM_PROMPT.format(tools=", ".join(self.tool_names))}
        j = self._post(CONFIG["openai_base"].rstrip("/") + "/chat/completions",
                       {"Content-Type": "application/json", "Authorization": "Bearer " + CONFIG["openai_key"]},
                       {"model": CONFIG["openai_model"], "messages": [sys] + msgs, "max_tokens": 800})
        return j["choices"][0]["message"]["content"]

    def _call_anthropic(self, msgs):
        sys = SYSTEM_PROMPT.format(tools=", ".join(self.tool_names))
        j = self._post("https://api.anthropic.com/v1/messages",
                       {"Content-Type": "application/json", "x-api-key": CONFIG["anthropic_key"], "anthropic-version": "2023-06-01"},
                       {"model": CONFIG["anthropic_model"], "max_tokens": 800, "system": sys, "messages": msgs})
        return "".join(b.get("text", "") for b in j.get("content", []))

    # ---------- parsing ----------
    def _parse(self, raw):
        raw = raw.strip()
        raw = re.sub(r"^```(json)?|```$", "", raw, flags=re.M).strip()
        try:
            j = json.loads(raw)
            if isinstance(j, dict) and "reply" in j: return j
        except Exception:
            pass
        m = re.search(r"\{.*\}", raw, flags=re.S)
        if m:
            try:
                j = json.loads(m.group(0))
                if isinstance(j, dict) and "reply" in j: return j
            except Exception: pass
        return {"reply": raw, "tool": None, "args": {}}

    # ---------- respond ----------
    def respond(self, text, session="default", lang="en"):
        self.mem.add_message(session, "user", text)
        hist = self.mem.history(session, n=10)
        msgs = [{"role": m["role"], "content": m["content"]} for m in hist]
        memctx = self.mem.memory_context()
        if memctx: msgs.insert(0, {"role": "system", "content": "Known facts about the user: " + memctx})
        prov = self.active_provider()
        tool_result = None
        if prov == "offline":
            j = self._offline(text, lang)
        else:
            fn = {"gemini": self._call_gemini, "openai": self._call_openai, "anthropic": self._call_anthropic}[prov]
            try:
                j = self._parse(fn(msgs))
            except Exception as e:
                j = {"reply": "(Provider call failed: %s. Switching to offline mode for this turn.)" % e}
                off = self._offline(text, lang); j["reply"] += " " + off["reply"]
        if j.get("tool"):
            tool_result = self.tools.run(j["tool"], j.get("args", {}))
            extra = json.dumps(tool_result, ensure_ascii=False)[:900]
            j["reply"] = (j.get("reply") or "") + "\n" + extra
        reply = (j.get("reply") or "").strip() or "(empty reply)"
        self.mem.add_message(session, "assistant", reply)
        self.mem.audit("chat", prov)
        return reply, {"provider": prov, "tool": j.get("tool"), "tool_result": tool_result}

    def respond_stream(self, text, session="default", lang="en"):
        reply, meta = self.respond(text, session, lang)
        for word in reply.split(" "):
            yield word + " "
        yield "\n__META__" + json.dumps(meta)

    # ---------- offline rule-based brain (honest, no fake AI) ----------
    def _offline(self, text, lang):
        t = text.lower().strip()

        def r(hi, en): return {"reply": (hi + " / " + en) if lang == "auto" else (hi if lang.startswith("hi") else en)}

        if any(k in t for k in ["mausam", "weather", "\u092e\u094c\u0938\u092e"]):
            stop = {"mausam", "weather", "kaisa", "kaisa hai", "hai", "ka", "ki", "ke", "in", "of", "the", "aaj", "kya", "batao", "bata", "abhi", "is"}
            words = [w.strip(",.?!") for w in t.split() if w.strip(",.?!") and w not in stop and not w.isdigit()]
            out = self.tools.t_weather({"city": words[-1] if words else "Amritsar"})
            if "error" in out: return {"reply": "Weather nahi mil paaya: " + out["error"]}
            return {"reply": "%s me abhi %.0f\u00b0C hai, hawa %.0f km/h." % (out["city"], out["temp_c"] or 0, out["wind_kmh"] or 0)}
        if t.startswith(("note ", "make a note", "\u0928\u094b\u091f")):
            body = re.sub(r"^(note|make a note|\u0928\u094b\u091f)\s*(that|ki)?\s*", "", t)
            self.tools.t_create_note({"title": body[:60], "body": body}); return r("Note save ho gaya.", "Note saved.")
        if any(k in t for k in ["remember", "\u092f\u093e\u0926"]):
            v = re.sub(r".*?(remember|\u092f\u093e\u0926)\s*(that|ki)?\s*", "", t)
            self.tools.t_remember({"key": v[:60], "value": v}); return r("Yaad rakh liya.", "Noted, I will remember that.")
        if any(k in t for k in ["task", "kaam", "\u0915\u093e\u092e"]) and any(k in t for k in ["add", "banao", "my", "\u092e\u0947\u0930\u0947", "show", "bata"]):
            if any(k in t for k in ["show", "bata", "list", "my tasks", "\u092c\u0924\u093e"]):
                rows = self.tools.t_list_tasks({})["tasks"]
                if not rows: return r("Koi khula kaam nahi hai.", "No open tasks.")
                return {"reply": "Aapke kaam: " + "; ".join(x["text"] for x in rows)}
            body = re.sub(r".*?(task|kaam)\s*(add|banao|hai|:)?\s*", "", t)
            self.tools.t_create_task({"text": body}); return r("Task add ho gaya.", "Task added.")
        if any(k in t for k in ["briefing", "my day", "\u0906\u091c \u0915\u0947"]):
            b = self.tools.t_daily_briefing({})
            s = "Briefing: "
            if "temp_c" in (b["weather"] or {}): s += "bahar %.0f\u00b0C. " % b["weather"]["temp_c"]
            s += "Kaam: %s. " % ("; ".join(b["tasks"]) if b["tasks"] else "koi nahi")
            s += "Reminders: %s." % ("; ".join(b["reminders"]) if b["reminders"] else "koi nahi")
            return {"reply": s}
        if any(k in t for k in ["translate", "\u0905\u0928\u0941\u0935\u093e\u0926"]):
            return {"reply": "Boliye kya translate karna hai? Format: translate <text> to hi / en."}
        m = re.search(r"translate\s+(.*?)\s+to\s+(hi|en)", t)
        if m:
            out = self.tools.t_translate({"text": m.group(1), "langpair": "en|hi" if m.group(2) == "hi" else "hi|en"})
            return {"reply": out.get("translated") or "translate fail"}
        if any(k in t for k in ["time", "\u0938\u092e\u092f"]):
            out = self.tools.t_what_time({}); return {"reply": "Abhi " + out["datetime"] + " hai."}
        if any(k in t for k in ["open ", "kholo", "\u0916\u094b\u0932\u094b"]):
            out = self.tools.t_open_app({"app": t})
            if "error" not in out: return {"reply": out["app"] + " khol diya ja raha hai aapke phone par."}
        if any(k in t for k in ["hello", "hi", "hey", "namaste", "\u0928\u092e\u0938\u094d\u0924\u0947"]):
            return r("Namaste! Main EUNVERA VOICE hoon. Bataiye, kya karna hai?", "Hello! I am EUNVERA VOICE. What can I do for you?")
        return r("Main offline mode me limited hoon (notes, tasks, reminders, weather, translate, time, apps). Full reasoning ke liye backend .env me ek free Gemini key daalein.", "I am in offline mode right now: notes, tasks, reminders, weather, translate, time and app opening. Add a free Gemini key in the backend .env for full reasoning.")
