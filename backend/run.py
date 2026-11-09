from main import app
import uvicorn
from config import CONFIG
uvicorn.run(app, host="0.0.0.0", port=CONFIG["port"])
