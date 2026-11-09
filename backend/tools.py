import time, re, json, urllib.request, urllib.parse
from memory import Memory

def _http_json(url, timeout=12):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))

def _http_get(url, timeout=12):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 EUNVERA_VOICE"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")

APP_ALIASES = {
    "youtube": "YouTube", "chrome": "Chrome", "settings": "Settings", "camera": "Camera",
    "whatsapp": "WhatsApp", "instagram": "Instagram", "gmail": "Gmail", "maps": "Maps",
    "phone": "Phone", "gallery": "Gallery", "playstore": "Play Store", "telegram": "Telegram",
}

class ToolBox:
    def __init__(self, mem: Memory):
        self.mem = mem

    def list_tools(self):
        return [
            {"name": "create_note", "desc": "Save a note (title + body)"},
            {"name": "create_task", "desc": "Add a task / to-do"},
            {"name": "list_tasks", "desc": "Show open tasks"},
            {"name": "set_reminder", "desc": "Set a reminder (text + minutes from now or due epoch)"},
            {"name": "remember", "desc": "Save a long-term memory fact (key + value)"},
            {"name": "recall", "desc": "Search long-term memory"},
            {"name": "weather", "desc": "Live weather for a city (Open-Meteo, free, no key)"},
            {"name": "translate", "desc": "Translate text (MyMemory, free tier)"},
            {"name": "web_search", "desc": "Quick internet search (DuckDuckGo, free)"},
            {"name": "open_app", "desc": "Open an installed Android app (executed on the phone)"},
            {"name": "daily_briefing", "desc": "Today: weather + tasks + reminders + notes"},
            {"name": "what_time", "desc": "Current date and time"},
        ]

    def run(self, name, args):
        fn = getattr(self, "t_" + name, None)
        if not fn:
            return {"error": "unknown tool: " + str(name)}
        try:
            out = fn(args or {})
            self.mem.audit("tool." + name, json.dumps(args or {})[:200])
            return out
        except Exception as e:
            return {"error": str(e)}

    # ---- tools ----
    def t_create_note(self, a):
        title = str(a.get("title", "Note"))[:120]; body = str(a.get("body", ""))
        self.mem.add_note(title, body); return {"ok": True, "saved": title}

    def t_create_task(self, a):
        t = self.mem.add_task(str(a.get("text", ""))[:300], a.get("due"))
        return {"ok": True, "task": t}

    def t_list_tasks(self, a):
        rows = [r for r in self.mem.tasks() if not r["done"]]
        return {"tasks": rows[:15]}

    def t_set_reminder(self, a):
        mins = float(a.get("minutes", 0) or 0)
        due = a.get("due") or (time.time() + mins * 60)
        self.mem.add_reminder(str(a.get("text", "Reminder"))[:300], due)
        return {"ok": True, "due": due}

    def t_remember(self, a):
        k = str(a.get("key", "fact"))[:120]; v = str(a.get("value", ""))[:600]
        self.mem.remember(k, v); return {"ok": True, "remembered": k}

    def t_recall(self, a):
        return {"items": self.mem.recall(a.get("q"), limit=8)}

    def t_weather(self, a):
        city = str(a.get("city", "Amritsar"))
        g = _http_json("https://geocoding-api.open-meteo.com/v1/search?name=" + urllib.parse.quote(city) + "&count=1&language=en")
        if not g.get("results"): return {"error": "city not found: " + city}
        r = g["results"][0]
        w = _http_json("https://api.open-meteo.com/v1/forecast?latitude=%s&longitude=%s&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m&daily=temperature_2m_max,temperature_2m_min&timezone=auto" % (r["latitude"], r["longitude"]))
        c = w.get("current", {}); d = (w.get("daily") or {})
        return {"city": r.get("name"), "temp_c": c.get("temperature_2m"), "humidity": c.get("relative_humidity_2m"),
                "wind_kmh": c.get("wind_speed_10m"), "code": c.get("weather_code"),
                "today_max": (d.get("temperature_2m_max") or [None])[0], "today_min": (d.get("temperature_2m_min") or [None])[0]}

    def t_translate(self, a):
        text = str(a.get("text", "")); pair = str(a.get("langpair", "en|hi"))
        u = "https://api.mymemory.translated.net/get?q=" + urllib.parse.quote(text[:450]) + "&langpair=" + urllib.parse.quote(pair)
        j = _http_json(u)
        return {"translated": j.get("responseData", {}).get("translatedText", ""), "langpair": pair}

    def t_web_search(self, a):
        q = str(a.get("q", ""))[:200]
        html = _http_get("https://duckduckgo.com/html/?q=" + urllib.parse.quote(q))
        out = []
        for m in re.findall(r'class="result__a"[^>]*>(.*?)</a>', html)[:5]:
            out.append(re.sub("<.*?>", "", m))
        return {"results": out if out else ["(no readable results right now)"]}

    def t_open_app(self, a):
        name = str(a.get("app", "")).lower().strip()
        for k, v in APP_ALIASES.items():
            if k in name:
                return {"ok": True, "app": v, "on_device": "the phone UI opens it via the Android bridge"}
        return {"error": "app not in supported list: " + name}

    def t_what_time(self, a):
        import datetime
        now = datetime.datetime.now()
        return {"datetime": now.strftime("%A, %d %B %Y, %I:%M %p")}

    def t_daily_briefing(self, a):
        tasks = [r["text"] for r in self.mem.tasks() if not r["done"]][:8]
        rem = [r["text"] for r in self.mem.reminders() if not r["fired"]][:5]
        notes = [r["title"] for r in self.mem.notes()][:5]
        try: w = self.t_weather({"city": a.get("city", "Amritsar")})
        except Exception as e: w = {"error": str(e)}
        return {"tasks": tasks, "reminders": rem, "notes": notes, "weather": w}
