import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent.parent
load_dotenv(BASE_DIR / ".env")

BOT_TOKEN: str = os.environ.get("DISCORD_BOT_TOKEN") or os.environ["DISCORD_NACRE_TOKEN"]
REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/1")
SOCKET_PATH: str = os.getenv("SOCKET_PATH", "/tmp/discord-notify.sock")
QUEUE_KEY = "discord_gateway:queue"
DEAD_LETTER_KEY = "discord_gateway:dead_letter"
