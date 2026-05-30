import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.environ["BOT_TOKEN"]
CHECK_INTERVAL: int = int(os.getenv("CHECK_INTERVAL", "3600"))
MIN_DISCOUNT: int = int(os.getenv("MIN_DISCOUNT", "50"))
MAX_GAMES: int = int(os.getenv("MAX_GAMES", "100"))
DB_PATH: str = os.getenv("DB_PATH", "steam_bot.db")
