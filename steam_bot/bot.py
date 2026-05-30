import asyncio
import logging
import sys

import aiohttp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

import config
import database as db
from steam_api import SteamDeal, build_deal, fetch_discounted_appids

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

WAITING_DISCOUNT = 1


# ── helpers ──────────────────────────────────────────────────────────────────

def deal_caption(deal: SteamDeal) -> str:
    lines = [
        f"🎮 <b>{_esc(deal.name)}</b>",
        f"🔥 Скидка: <b>{deal.discount}%</b>",
        f"💰 Цена: <s>{_esc(deal.original_price)}</s> → <b>{_esc(deal.final_price)}</b>",
    ]
    if deal.description:
        lines.append(f"\n📝 {_esc(deal.description)}")
    return "\n".join(lines)


def _esc(text: str) -> str:
    for ch in ("&", "<", ">"):
        text = text.replace(ch, {"&": "&amp;", "<": "&lt;", ">": "&gt;"}[ch])
    return text


def store_button(deal: SteamDeal) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("🛒 Открыть в Steam", url=deal.store_url)]]
    )


async def send_deal(bot, chat_id: int, deal: SteamDeal) -> bool:
    caption = deal_caption(deal)
    markup = store_button(deal)
    try:
        if deal.image_url:
            await bot.send_photo(
                chat_id=chat_id,
                photo=deal.image_url,
                caption=caption,
                parse_mode=ParseMode.HTML,
                reply_markup=markup,
            )
        else:
            await bot.send_message(
                chat_id=chat_id,
                text=caption,
                parse_mode=ParseMode.HTML,
                reply_markup=markup,
                disable_web_page_preview=False,
            )
        return True
    except TelegramError as exc:
        logger.warning("Failed to send deal %s to %s: %s", deal.appid, chat_id, exc)
        return False


# ── command handlers ──────────────────────────────────────────────────────────

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    await db.add_subscriber(chat_id)
    await update.message.reply_text(
        "✅ <b>Подписка активирована!</b>\n\n"
        "Я буду присылать тебе скидки в Steam как только они появятся.\n\n"
        "📌 Команды:\n"
        "/deals — показать текущие скидки прямо сейчас\n"
        "/filter — изменить минимальный % скидки\n"
        "/stop — отписаться от уведомлений\n"
        "/status — текущие настройки",
        parse_mode=ParseMode.HTML,
    )


async def cmd_stop(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await db.remove_subscriber(update.effective_chat.id)
    await update.message.reply_text("🚫 Уведомления отключены. /start — чтобы включить снова.")


async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    subs = await db.get_active_subscribers()
    entry = next((s for s in subs if s[0] == chat_id), None)
    if entry:
        await update.message.reply_text(
            f"✅ Подписка активна\n"
            f"🔻 Минимальная скидка: <b>{entry[1]}%</b>\n"
            f"⏱ Проверка каждые: <b>{config.CHECK_INTERVAL // 60} мин</b>",
            parse_mode=ParseMode.HTML,
        )
    else:
        await update.message.reply_text("❌ Подписка не активна. /start — чтобы включить.")


async def cmd_filter_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Введи минимальный процент скидки (число от 1 до 99):\n"
        "Например: <b>70</b> — только скидки 70% и выше",
        parse_mode=ParseMode.HTML,
    )
    return WAITING_DISCOUNT


async def cmd_filter_receive(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if not text.isdigit() or not (1 <= int(text) <= 99):
        await update.message.reply_text("❌ Введи число от 1 до 99.")
        return WAITING_DISCOUNT
    discount = int(text)
    await db.add_subscriber(update.effective_chat.id)
    await db.set_min_discount(update.effective_chat.id, discount)
    await update.message.reply_text(
        f"✅ Буду слать скидки от <b>{discount}%</b>", parse_mode=ParseMode.HTML
    )
    return ConversationHandler.END


async def cmd_filter_cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Отмена.")
    return ConversationHandler.END


async def cmd_deals(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    subs = await db.get_active_subscribers()
    entry = next((s for s in subs if s[0] == chat_id), None)
    min_discount = entry[1] if entry else config.MIN_DISCOUNT

    msg = await update.message.reply_text("🔍 Ищу актуальные скидки в Steam...")

    async with aiohttp.ClientSession() as session:
        raw_list = await fetch_discounted_appids(session, max_count=20)
        filtered = [r for r in raw_list if r["discount"] >= min_discount]

    if not filtered:
        await msg.edit_text(f"😕 Скидок от {min_discount}% сейчас не найдено.")
        return

    await msg.edit_text(f"🎉 Найдено {len(filtered)} скидок (от {min_discount}%). Отправляю...")

    async with aiohttp.ClientSession() as session:
        for raw in filtered[:10]:
            deal = await build_deal(session, raw)
            if deal:
                await send_deal(ctx.bot, chat_id, deal)
                await asyncio.sleep(0.3)


# ── background monitor ────────────────────────────────────────────────────────

async def monitor_loop(app: Application) -> None:
    logger.info("Monitor started (interval=%ds)", config.CHECK_INTERVAL)
    await asyncio.sleep(10)  # brief startup delay

    while True:
        try:
            await db.cleanup_old_deals(days=30)
            subscribers = await db.get_active_subscribers()

            if not subscribers:
                logger.info("No active subscribers, skipping Steam check.")
                await asyncio.sleep(config.CHECK_INTERVAL)
                continue

            logger.info("Checking Steam deals for %d subscriber(s)...", len(subscribers))

            async with aiohttp.ClientSession() as session:
                raw_list = await fetch_discounted_appids(session, max_count=config.MAX_GAMES)

            for chat_id, min_discount in subscribers:
                filtered = [r for r in raw_list if r["discount"] >= min_discount]
                new_deals = []
                for raw in filtered:
                    if not await db.is_deal_sent(raw["appid"], chat_id):
                        new_deals.append(raw)

                if not new_deals:
                    continue

                logger.info("Sending %d new deals to %s", len(new_deals), chat_id)
                async with aiohttp.ClientSession() as session:
                    for raw in new_deals:
                        deal = await build_deal(session, raw)
                        if deal:
                            ok = await send_deal(app.bot, chat_id, deal)
                            if ok:
                                await db.mark_deal_sent(deal.appid, chat_id)
                            await asyncio.sleep(0.5)

        except Exception as exc:
            logger.error("Monitor error: %s", exc, exc_info=True)

        await asyncio.sleep(config.CHECK_INTERVAL)


async def post_init(app: Application) -> None:
    await db.init_db()
    asyncio.create_task(monitor_loop(app))


# ── entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    app = (
        Application.builder()
        .token(config.BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    filter_conv = ConversationHandler(
        entry_points=[CommandHandler("filter", cmd_filter_start)],
        states={WAITING_DISCOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, cmd_filter_receive)]},
        fallbacks=[CommandHandler("cancel", cmd_filter_cancel)],
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("stop", cmd_stop))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("deals", cmd_deals))
    app.add_handler(filter_conv)

    logger.info("Bot starting...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
