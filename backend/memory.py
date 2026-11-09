import sqlite3, threading, time, json
from config import CONFIG

_lock = threading.Lock()

def _conn():
    c = sqlite3.connect(CONFIG["db_path"])
    c.row_factory = sqlite3.Row
    return c

class Memory:
    def __init__(self):
        c = _conn()
        c.executescript("""
        CREATE TABLE IF NOT EXISTS messages(
            id INTEGER PRIMARY KEY AUTOINCREMENT, session TEXT, role TEXT,
            content TEXT, ts REAL);
        CREATE TABLE IF NOT EXISTS memory_items(
            id INTEGER PRIMARY KEY AUTOINCREMENT, key TEXT, value TEXT, ts REAL);
        CREATE TABLE IF NOT EXISTS tasks(
            id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT, done INTEGER DEFAULT 0,
            due REAL, created REAL);
        CREATE TABLE IF NOT EXISTS notes(
            id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, body TEXT, created REAL);
        CREATE TABLE IF NOT EXISTS reminders(
            id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT, due REAL, fired INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS audit(
            id INTEGER PRIMARY KEY AUTOINCREMENT, action TEXT, detail TEXT, ts REAL);
        """)
        c.commit(); c.close()

    def _run(self, sql, params=()):
        with _lock:
            c = _conn(); c.execute(sql, params); c.commit(); c.close()

    def _fetch(self, sql, params=()):
        c = _conn(); rows = [dict(r) for r in c.execute(sql, params).fetchall()]; c.close(); return rows

    # audit
    def audit(self, action, detail=""):
        self._run("INSERT INTO audit(action,detail,ts) VALUES(?,?,?)", (action, detail[:500], time.time()))

    def get_audit(self, limit=100):
        return self._fetch("SELECT * FROM audit ORDER BY id DESC LIMIT ?", (limit,))

    # chat history
    def add_message(self, session, role, content):
        self._run("INSERT INTO messages(session,role,content,ts) VALUES(?,?,?,?)", (session, role, content, time.time()))

    def history(self, session, n=12):
        rows = self._fetch("SELECT role, content FROM messages WHERE session=? ORDER BY id DESC LIMIT ?", (session, n))
        return list(reversed(rows))

    def sessions(self):
        return self._fetch("SELECT session, COUNT(*) AS n, MAX(ts) AS last FROM messages GROUP BY session ORDER BY last DESC LIMIT 50")

    def wipe_messages(self):
        self._run("DELETE FROM messages")

    # long-term memory
    def remember(self, key, value):
        self._run("INSERT INTO memory_items(key,value,ts) VALUES(?,?,?)", (key, value, time.time()))
        self.audit("memory.add", key)

    def forget(self, item_id):
        self._run("DELETE FROM memory_items WHERE id=?", (item_id,))
        self.audit("memory.forget", str(item_id))

    def recall(self, q=None, limit=50):
        if q:
            return self._fetch("SELECT * FROM memory_items WHERE key LIKE ? OR value LIKE ? ORDER BY id DESC LIMIT ?", ("%"+q+"%","%"+q+"%",limit))
        return self._fetch("SELECT * FROM memory_items ORDER BY id DESC LIMIT ?", (limit,))

    def memory_context(self, limit=10):
        rows = self.recall(limit=limit)
        return "; ".join(r["key"] + ": " + r["value"] for r in rows) if rows else ""

    # tasks
    def add_task(self, text, due=None):
        self._run("INSERT INTO tasks(text,due,created) VALUES(?,?,?)", (text, due, time.time()))
        self.audit("task.add", text)
        return self._fetch("SELECT * FROM tasks ORDER BY id DESC LIMIT 1")[0]

    def tasks(self, include_done=False):
        sql = "SELECT * FROM tasks ORDER BY done, id DESC"
        return self._fetch(sql)

    def complete_task(self, task_id):
        self._run("UPDATE tasks SET done=1 WHERE id=?", (task_id,))

    # notes
    def add_note(self, title, body):
        self._run("INSERT INTO notes(title,body,created) VALUES(?,?,?)", (title, body, time.time()))
        self.audit("note.add", title)

    def notes(self):
        return self._fetch("SELECT * FROM notes ORDER BY id DESC LIMIT 100")

    # reminders
    def add_reminder(self, text, due):
        self._run("INSERT INTO reminders(text,due) VALUES(?,?)", (text, due))
        self.audit("reminder.add", text)

    def due_reminders(self):
        return self._fetch("SELECT * FROM reminders WHERE fired=0 AND due<=?", (time.time(),))

    def mark_fired(self, rid):
        self._run("UPDATE reminders SET fired=1 WHERE id=?", (rid,))

    def reminders(self):
        return self._fetch("SELECT * FROM reminders ORDER BY fired, due LIMIT 100")

    def wipe_all(self):
        for t in ["messages","memory_items","tasks","notes","reminders","audit"]:
            self._run("DELETE FROM " + t)
        self.audit("wipe", "all data deleted by user")
