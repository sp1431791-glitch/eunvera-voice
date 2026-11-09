/* EUNVERA VOICE - client app: on-device STT/TTS + server brain, premium orb */
const $ = (id) => document.getElementById(id);
const S = Object.assign({
  backend: (location.origin.startsWith("http") && !location.protocol.startsWith("file")) ? location.origin : "http://localhost:8766",
  lang: "hi-IN", replyLang: "auto", rate: 1.0, vol: 1.0, continuous: false, wake: false,
  session: "default", theme: "dark", briefTime: "09:00", briefAuto: false
}, JSON.parse(localStorage.getItem("eunvera_voice") || "{}"));
const save = () => localStorage.setItem("eunvera_voice", JSON.stringify(S));
let listening = false, speaking = false, recog = null, audioCtx = null, analyser = null, wakeArmed = false;

/* ---------- orb animation ---------- */
function orb(canvas, getMode) {
  const ctx = canvas.getContext("2d");
  let t = 0;
  function draw() {
    const w = canvas.width = canvas.clientWidth * 2, h = canvas.height = canvas.clientHeight * 2;
    t += 0.02;
    ctx.clearRect(0, 0, w, h);
    const cx = w / 2, cy = h / 2, base = Math.min(w, h) * 0.28;
    const mode = getMode();
    const speed = mode === "listening" ? 2.2 : mode === "thinking" ? 3.2 : mode === "speaking" ? 2.6 : 1;
    const breathe = 1 + Math.sin(t * speed) * (mode === "idle" ? 0.05 : 0.13);
    for (let i = 3; i >= 0; i--) {
      const r = base * breathe * (1 + i * 0.28);
      const g = ctx.createRadialGradient(cx, cy, r * 0.2, cx, cy, r);
      const hue = 215 + Math.sin(t + i) * 14;
      g.addColorStop(0, "hsla(" + hue + ",95%,62%," + (0.5 - i * 0.1) + ")");
      g.addColorStop(1, "hsla(" + hue + ",95%,55%,0)");
      ctx.beginPath(); ctx.arc(cx, cy, r, 0, 7); ctx.fillStyle = g; ctx.fill();
    }
    // swirling core arcs
    for (let k = 0; k < 5; k++) {
      ctx.beginPath();
      const rr = base * breathe * (0.5 + k * 0.12), a0 = t * (1 + k * 0.35);
      ctx.arc(cx, cy, rr, a0, a0 + 2.2);
      ctx.strokeStyle = "hsla(" + (205 + k * 12) + ",95%," + (60 + k * 6) + ",%," + (0.55 - k * 0.08) + ")";
      ctx.lineWidth = (5 - k) * 2.4; ctx.stroke();
    }
    requestAnimationFrame(draw);
  }
  draw();
}
let orbMode = "idle";
orb($("orbHome"), () => orbMode);
orb($("orbVoice"), () => orbMode);

/* ---------- screens ---------- */
document.querySelectorAll("#nav button").forEach(b => b.onclick = () => {
  document.querySelectorAll("#nav button").forEach(x => x.classList.remove("on"));
  b.classList.add("on");
  document.querySelectorAll(".screen").forEach(s => s.classList.remove("active"));
  $("scr-" + b.dataset.scr).classList.add("active");
  if (b.dataset.scr === "history") loadHistory();
  if (b.dataset.scr === "memory") loadMemory();
  if (b.dataset.scr === "models") loadModels();
  if (b.dataset.scr === "skills") loadSkills();
  if (b.dataset.scr === "automation") loadReminders();
  if (b.dataset.scr === "settings") loadAudit();
});

/* ---------- api ---------- */
const api = (path, opt) => fetch(S.backend.replace(/\/$/, "") + path, Object.assign({ headers: { "Content-Type": "application/json" } }, opt))
  .then(r => r.json()).catch(e => { sysStatus(false); throw e; });
function sysStatus(ok, label) {
  $("sysDot").className = "dot " + (ok ? "ok" : "bad");
  $("sysText").textContent = label || (ok ? "brain online" : "backend offline");
}

/* ---------- TTS (on-device, free) ---------- */
function speak(text, onend) {
  if (!("speechSynthesis" in window)) { onend && onend(); return; }
  speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text.replace(/__META__.*$/, ""));
  u.lang = S.lang; u.rate = S.rate; u.volume = S.vol;
  const voices = speechSynthesis.getVoices();
  const v = voices.find(v => v.lang.replace("_", "-").startsWith(S.lang)) || voices.find(v => /hi|en-IN/.test(v.lang));
  if (v) u.voice = v;
  orbMode = "speaking"; speaking = true; $("stateLabel").textContent = "speaking";
  u.onend = u.onerror = () => { speaking = false; orbMode = listening ? "listening" : "idle"; $("stateLabel").textContent = listening ? "listening" : "tap the mic"; onend && onend(); };
  speechSynthesis.speak(u);
}
$("stopBtn").onclick = () => { speechSynthesis.cancel(); };

/* ---------- STT (on-device, free) ---------- */
const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
function startListening() {
  if (!SR) { addMsg("sys", "This browser/WebView has no speech engine. Use text input, or Chrome on Android."); return; }
  recog = new SR();
  recog.lang = S.lang; recog.interimResults = true; recog.continuous = S.wake || S.continuous;
  let final = "";
  recog.onstart = () => { listening = true; orbMode = "listening"; $("stateLabel").textContent = S.wake && !wakeArmed ? "waiting for \"eunvera\"" : "listening"; $("micBtn").classList.add("listening"); startWave(); };
  recog.onresult = (e) => {
    let interim = "";
    for (let i = e.resultIndex; i < e.results.length; i++) {
      const r = e.results[i];
      if (r.isFinal) final += r.transcript; else interim += r.transcript;
    }
    const shown = (final + " " + interim).trim();
    if (S.wake && !wakeArmed) {
      if (/eunvera|\u092f\u0942\u0928\u0935\u0947\u0930\u093e|\u0909\u0928\u0935\u0947\u0930\u093e/i.test(shown)) { wakeArmed = true; $("stateLabel").textContent = "listening"; }
      return;
    }
    $("stateLabel").textContent = shown ? "\u201C" + shown + "\u201D" : "listening";
    if (speaking) { speechSynthesis.cancel(); } // barge-in
    if (e.results[e.results.length - 1].isFinal && shown) { final = ""; wakeArmed = false; handleTurn(shown.trim()); }
  };
  recog.onerror = (e) => { if (e.error !== "aborted") $("stateLabel").textContent = "mic error: " + e.error; };
  recog.onend = () => {
    listening = false; $("micBtn").classList.remove("listening"); stopWave();
    orbMode = "idle"; $("stateLabel").textContent = "tap the mic";
    if (S.continuous && !speaking) setTimeout(() => { if (!speaking) startListening(); }, 400);
  };
  try { recog.start(); } catch (e) {}
}
$("micBtn").onclick = () => { if (listening) { recog && recog.stop(); } else startListening(); };
$("homeMic").onclick = () => { document.querySelector('[data-scr="voice"]').click(); setTimeout(startListening, 250); };
document.querySelectorAll(".chips button[data-say]").forEach(b => b.onclick = () => { document.querySelector('[data-scr="voice"]').click(); handleTurn(b.dataset.say); });

/* ---------- waveform ---------- */
async function startWave() {
  try {
    audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const src = audioCtx.createMediaStreamSource(stream);
    analyser = audioCtx.createAnalyser(); analyser.fftSize = 256;
    src.connect(analyser);
    const c = $("wave"), ctx = c.getContext("2d");
    const buf = new Uint8Array(analyser.frequencyBinCount);
    (function loop() {
      if (!analyser) return;
      analyser.getByteFrequencyData(buf);
      const w = c.width = c.clientWidth * 2, h = c.height = 112;
      ctx.clearRect(0, 0, w, h);
      const n = 48;
      for (let i = 0; i < n; i++) {
        const v = buf[i * 2] / 255, bh = 6 + v * (h - 10);
        const x = i * (w / n);
        ctx.fillStyle = "rgba(110,231,255," + (0.25 + v * 0.7) + ")";
        ctx.fillRect(x + 2, (h - bh) / 2, w / n - 6, bh);
      }
      requestAnimationFrame(loop);
    })();
  } catch (e) { /* mic denied: transcript-only mode */ }
}
function stopWave() { analyser = null; const c = $("wave"); c.getContext("2d").clearRect(0, 0, c.width, c.height); }

/* ---------- conversation ---------- */
function addMsg(who, text) {
  const d = document.createElement("div");
  d.className = "msg " + (who === "you" ? "you" : "");
  const name = who === "you" ? "You" : who === "sys" ? "System" : "EUNVERA";
  d.innerHTML = "<b>" + name + "</b><br>" + text.replace(/</g, "&lt;");
  $("transcript").appendChild(d);
  $("transcript").scrollTop = 1e9;
}
async function handleTurn(text) {
  if (!text) return;
  addMsg("you", text);
  orbMode = "thinking"; $("stateLabel").textContent = "thinking";
  try {
    const r = await api("/api/chat", { method: "POST", body: JSON.stringify({ message: text, session: S.session, lang: S.replyLang }) });
    sysStatus(true, "brain: " + (r.meta && r.meta.provider || "ok"));
    addMsg("ev", r.reply);
    speak(r.reply, () => { if (S.continuous && !listening) startListening(); });
  } catch (e) {
    sysStatus(false);
    addMsg("sys", "Backend nahi mila. Settings me Backend URL check karo aur phone/PC ek hi WiFi par ho.");
    $("stateLabel").textContent = "backend offline";
    orbMode = "idle";
  }
}
$("sendBtn").onclick = () => { const v = $("textIn").value.trim(); $("textIn").value = ""; handleTurn(v); };
$("textIn").addEventListener("keydown", e => { if (e.key === "Enter") $("sendBtn").click(); });

/* ---------- history / memory / models / skills ---------- */
async function loadHistory() {
  const ss = await api("/api/sessions").catch(() => []);
  $("sessionList").innerHTML = (ss || []).map(s => "<div class='item'><span>" + s.session + " <small>" + s.n + " messages</small></span></div>").join("") || "<div class='muted'>no sessions yet</div>";
  const rows = await api("/api/history?limit=60").catch(() => []);
  $("historyBody").innerHTML = (rows || []).map(m => "<div class='item'><span><b>" + (m.role === "user" ? "You" : "EUNVERA") + "</b> " + m.content.replace(/</g, "&lt;") + "</span></div>").join("");
}
async function loadMemory() {
  const mem = await api("/api/memory").catch(() => []);
  $("memList").innerHTML = (mem || []).map(m => "<div class='item'><span><b>" + m.key + "</b> " + m.value + "</span><button class=x data-mem=" + m.id + ">✕</button></div>").join("");
  document.querySelectorAll("[data-mem]").forEach(b => b.onclick = () => api("/api/memory/" + b.dataset.mem, { method: "DELETE" }).then(loadMemory));
  const tk = await api("/api/tasks").catch(() => []);
  $("taskList").innerHTML = (tk || []).map(t => "<div class='item'><span>" + (t.done ? "✓ " : "") + t.text + "</span>" + (t.done ? "" : "<button class=x data-task=" + t.id + ">✓</button>") + "</div>").join("");
  document.querySelectorAll("[data-task]").forEach(b => b.onclick = () => api("/api/tasks/" + b.dataset.task + "/done", { method: "POST" }).then(loadMemory));
  const nt = await api("/api/notes").catch(() => []);
  $("noteList").innerHTML = (nt || []).map(n => "<div class='item'><span><b>" + n.title + "</b><small>" + n.body + "</small></span></div>").join("");
}
$("memAdd").onclick = () => { api("/api/memory", { method: "POST", body: JSON.stringify({ key: $("memKey").value, value: $("memVal").value }) }).then(() => { $("memKey").value = ""; $("memVal").value = ""; loadMemory(); }); };
$("wipeBtn").onclick = () => { if (confirm("Delete EVERYTHING (chats, memory, tasks, notes, audit)? This cannot be undone.")) api("/api/wipe", { method: "POST" }).then(() => { addMsg("sys", "All data deleted."); loadMemory(); }); };
async function loadModels() {
  const st = await api("/api/status").catch(() => null);
  if (!st) { sysStatus(false); $("modelList").innerHTML = "<div class='item'>backend offline</div>"; return; }
  sysStatus(true, "brain: " + st.active_provider);
  $("modelList").innerHTML = st.providers.map(p =>
    "<div class='item'><span><b>" + p.name + "</b><small>" + p.model + " · free tier: " + p.free_tier + "</small></span><span>" + (p.connected ? "🟢 connected" : "⚪ not connected") + "</span></div>").join("");
}
async function loadSkills() {
  const st = await api("/api/status").catch(() => null);
  const tools = st ? st.tools : [];
  $("skillList").innerHTML = tools.map(t =>
    "<div class='item'><span><b>" + t.name + "</b><small>" + t.desc + "</small></span></div>").join("") ||
    "<div class='muted'>backend offline</div>";
}

/* ---------- reminders / automation ---------- */
async function loadReminders() {
  const r = await api("/api/reminders").catch(() => []);
  $("remList").innerHTML = (r || []).map(x => "<div class='item'><span>" + x.text + "<small>" + (x.fired ? "done" : new Date(x.due * 1000).toLocaleString()) + "</small></span></div>").join("");
}
$("remAdd").onclick = () => { api("/api/reminders", { method: "POST", body: JSON.stringify({ text: $("remText").value, minutes: +$("remMins").value || 5 }) }).then(loadReminders); };
setInterval(async () => {
  const due = await api("/api/reminders/due").catch(() => []);
  (due || []).forEach(r => { addMsg("sys", "⏰ Reminder: " + r.text); speak("Reminder: " + r.text); });
}, 30000);
setInterval(() => {
  if (!S.briefAuto) return;
  const now = new Date(), hm = String(now.getHours()).padStart(2, "0") + ":" + String(now.getMinutes()).padStart(2, "0");
  if (hm === S.briefTime && now.getSeconds() < 30 && !window.__briefFired) {
    window.__briefFired = true; handleTurn("aaj ka briefing batao");
    setTimeout(() => window.__briefFired = false, 65000);
  }
}, 15000);

/* ---------- android app opening (Capacitor bridge, graceful fallback) ---------- */
const APPS = ["YouTube", "Chrome", "Settings", "Camera", "WhatsApp", "Instagram", "Gmail", "Maps", "Phone", "Telegram"];
$("appBtns").innerHTML = APPS.map(a => "<button data-app=" + a + ">" + a + "</button>").join("");
document.querySelectorAll("[data-app]").forEach(b => b.onclick = async () => {
  const app = b.dataset.app;
  try {
    const cap = window.Capacitor && window.Capacitor.Plugins;
    if (cap && cap.App && cap.App.launchApp) { await cap.App.launchApp({ appName: app.toLowerCase() }); return; }
  } catch (e) {}
  addMsg("sys", app + " app-opening works in the installed Android app (Capacitor bridge). In a plain browser, Android security blocks direct app launch.");
});

/* ---------- settings binding ---------- */
function bind(id, key, fn) { const el = $(id); if (!el) return;
  if (el.type === "checkbox") { el.checked = !!S[key]; el.onchange = () => { S[key] = el.checked; save(); fn && fn(); }; }
  else { el.value = S[key]; el.oninput = el.onchange = () => { S[key] = el.value; save(); fn && fn(); }; }
}
bind("langSel", "lang"); bind("replyLang", "replyLang"); bind("rate", "rate"); bind("vol", "vol");
bind("wake", "wake"); bind("backend", "backend"); bind("session", "session");
bind("continuous", "continuous"); bind("briefAuto", "briefAuto"); bind("briefTime", "briefTime");
$("themeBtn").onclick = () => { S.theme = S.theme === "dark" ? "light" : "dark"; save(); applyTheme(); };
function applyTheme() { document.body.className = "theme-" + S.theme; }

async function loadAudit() {
  const a = await api("/api/audit").catch(() => []);
  $("auditList").innerHTML = (a || []).slice(0, 25).map(x => "<div class='item'><span>" + x.action + "<small>" + new Date(x.ts * 1000).toLocaleString() + "</small></span></div>").join("");
}

/* ---------- greeting + briefing ---------- */
(function init() {
  applyTheme();
  const h = new Date().getHours();
  $("greet").textContent = (h < 12 ? "Good morning" : h < 17 ? "Good afternoon" : "Good evening") + ", Shubham";
  if (speechSynthesis) speechSynthesis.getVoices(); // warm up voices
  api("/api/status").then(st => sysStatus(true, "brain: " + st.active_provider)).catch(() => sysStatus(false));
  api("/api/chat", { method: "POST", body: JSON.stringify({ message: "aaj ka briefing batao", session: "auto", lang: "auto" }) })
    .then(r => $("briefBody").textContent = r.reply.replace(/\n/g, " ").slice(0, 400)).catch(() => $("briefBody").textContent = "backend offline: start the server, then reopen.");
})();
