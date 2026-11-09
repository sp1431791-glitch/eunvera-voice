import os

def _e(k, d=""):
    return os.environ.get(k, d)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG = {
    "gemini_key": _e("GEMINI_API_KEY"),
    "gemini_model": _e("GEMINI_MODEL", "gemini-1.5-flash"),
    "openai_key": _e("OPENAI_API_KEY"),
    "openai_base": _e("OPENAI_BASE_URL", "https://api.openai.com/v1"),
    "openai_model": _e("OPENAI_MODEL", "gpt-4o-mini"),
    "anthropic_key": _e("ANTHROPIC_API_KEY"),
    "anthropic_model": _e("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest"),
    "db_path": _e("EUNVERA_DB", os.path.join(BASE_DIR, "eunvera_voice.db")),
    "port": int(_e("PORT", "8766")),
}
