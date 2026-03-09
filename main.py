import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters


load_dotenv()

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("tg-bot")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
PUBLIC_URL = (os.getenv("PUBLIC_URL") or os.getenv("RENDER_EXTERNAL_URL") or "").strip()
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "").strip()

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is required (set it in .env)")


async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_chat:
        return
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Привет! Я бот на Python.\n\nКоманды:\n/start\n/ping",
    )


async def ping_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_chat:
        return
    await context.bot.send_message(chat_id=update.effective_chat.id, text="pong")


# Маршруты пересылки:
# Ключ — ID чата-источника.
# Значение:
#   - target_chat_id — ID чата-получателя
#   - topic_id       — ID темы (message_thread_id) в чате-получателе, либо None
#
# Примеры (раскомментируй и подставь свои ID):
# ROUTES: dict[int, dict[str, int | None]] = {
#     -1001111111111: {"target_chat_id": -1002222222222, "topic_id": 10},
#     -1003333333333: {"target_chat_id": -1002222222222, "topic_id": 15},
# }

# Текущая реальная схема маршрутизации:
ROUTES: dict[int, dict[str, int | None]] = {
    -2705141042: {
        "target_chat_id": -1002290371611,
        "topic_id": 11,
    },
    -4973230673: {
        "target_chat_id": -1002290371611,
        "topic_id": 2,
    },
}


async def route_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_chat or not update.message or not update.message.text:
        return

    src_chat_id = update.effective_chat.id
    src_thread_id = update.message.message_thread_id
    text = update.message.text

    logger.info(
        "Incoming message: chat_id=%s thread_id=%s text=%r",
        src_chat_id,
        src_thread_id,
        text[:100],
    )

    route = ROUTES.get(src_chat_id)
    if not route:
        return

    target_chat_id = route["target_chat_id"]
    topic_id = route.get("topic_id")

    send_kwargs: dict = {}
    if topic_id is not None:
        send_kwargs["message_thread_id"] = topic_id

    # Отправляем текст от имени бота, без пометки "переслано"
    await context.bot.send_message(
        chat_id=target_chat_id,
        text=text,
        **send_kwargs,
    )


telegram_app = (
    Application.builder()
    .token(BOT_TOKEN)
    .build()
)
telegram_app.add_handler(CommandHandler("start", start_cmd))
telegram_app.add_handler(CommandHandler("ping", ping_cmd))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, route_message))


def _webhook_url() -> str:
    if not PUBLIC_URL:
        raise RuntimeError("PUBLIC_URL is required for webhook mode")
    if not WEBHOOK_SECRET:
        raise RuntimeError("WEBHOOK_SECRET is required for webhook mode")
    return f"{PUBLIC_URL.rstrip('/')}/webhook/{WEBHOOK_SECRET}"


async def _startup_webhook() -> None:
    await telegram_app.initialize()
    await telegram_app.start()

    url = _webhook_url()
    await telegram_app.bot.set_webhook(url=url, drop_pending_updates=True)
    logger.info("Webhook set to %s", url)


async def _shutdown_webhook() -> None:
    try:
        await telegram_app.bot.delete_webhook(drop_pending_updates=False)
    except Exception:
        logger.exception("Failed to delete webhook")

    await telegram_app.stop()
    await telegram_app.shutdown()


app = FastAPI()


@app.on_event("startup")
async def _on_startup() -> None:
    if PUBLIC_URL:
        await _startup_webhook()
    else:
        logger.info("PUBLIC_URL not set: webhook mode disabled (use polling for local run).")


@app.on_event("shutdown")
async def _on_shutdown() -> None:
    if PUBLIC_URL:
        await _shutdown_webhook()


@app.get("/")
async def root() -> dict:
    return {"ok": True, "mode": "webhook" if PUBLIC_URL else "idle", "health": "/healthz"}


@app.get("/healthz")
async def healthz() -> dict:
    return {"ok": True}


@app.post("/webhook/{secret}")
async def telegram_webhook(secret: str, request: Request) -> dict:
    if not PUBLIC_URL:
        return {"ok": False, "error": "Webhook mode is disabled (PUBLIC_URL is not set)."}

    if secret != WEBHOOK_SECRET:
        return {"ok": False, "error": "Invalid secret."}

    payload = await request.json()
    update = Update.de_json(payload, telegram_app.bot)
    await telegram_app.process_update(update)
    return {"ok": True}


def run_polling() -> None:
    telegram_app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    # Local dev: create .env from .env.example and keep PUBLIC_URL empty.
    # Then run: python main.py
    run_polling()
