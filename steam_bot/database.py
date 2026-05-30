import aiosqlite
from config import DB_PATH


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS subscribers (
                chat_id     INTEGER PRIMARY KEY,
                min_discount INTEGER NOT NULL DEFAULT 50,
                active      INTEGER NOT NULL DEFAULT 1,
                joined_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS sent_deals (
                appid   INTEGER NOT NULL,
                chat_id INTEGER NOT NULL,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (appid, chat_id)
            )
        """)
        await db.commit()


async def add_subscriber(chat_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO subscribers (chat_id) VALUES (?)", (chat_id,)
        )
        await db.execute(
            "UPDATE subscribers SET active=1 WHERE chat_id=?", (chat_id,)
        )
        await db.commit()


async def remove_subscriber(chat_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE subscribers SET active=0 WHERE chat_id=?", (chat_id,)
        )
        await db.commit()


async def get_active_subscribers() -> list[tuple[int, int]]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT chat_id, min_discount FROM subscribers WHERE active=1"
        ) as cursor:
            return await cursor.fetchall()


async def set_min_discount(chat_id: int, discount: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE subscribers SET min_discount=? WHERE chat_id=?",
            (discount, chat_id),
        )
        await db.commit()


async def is_deal_sent(appid: int, chat_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT 1 FROM sent_deals WHERE appid=? AND chat_id=?", (appid, chat_id)
        ) as cursor:
            return await cursor.fetchone() is not None


async def mark_deal_sent(appid: int, chat_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO sent_deals (appid, chat_id) VALUES (?, ?)",
            (appid, chat_id),
        )
        await db.commit()


async def cleanup_old_deals(days: int = 30) -> None:
    """Remove deal records older than N days to keep DB small."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM sent_deals WHERE sent_at < datetime('now', ?)",
            (f"-{days} days",),
        )
        await db.commit()
