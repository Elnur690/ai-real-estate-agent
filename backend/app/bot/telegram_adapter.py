import os
import logging
from typing import Optional
from telegram import Update, Bot, InputMediaPhoto
from telegram.request import HTTPXRequest
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.bot.command_handler import BotCommandHandler

logger = logging.getLogger(__name__)

class TransientNetworkFilter(logging.Filter):
    """Downgrades transient polling connection hiccups from noisy ERROR traceback to single clean WARNING."""
    def filter(self, record: logging.LogRecord) -> bool:
        msg = str(record.getMessage() or "")
        if record.exc_info:
            msg += f" {record.exc_info}"
        if any(err_kw in msg for err_kw in ["ConnectError", "NetworkError", "timed out", "RemoteProtocolError", "NameResolutionError"]):
            record.levelno = logging.WARNING
            record.levelname = "WARNING"
        return True

# Attach filter to python-telegram-bot's Updater logger
logging.getLogger("telegram.ext.Updater").addFilter(TransientNetworkFilter())

def get_telegram_request() -> HTTPXRequest:
    return HTTPXRequest(
        connection_pool_size=16,
        read_timeout=30.0,
        write_timeout=30.0,
        connect_timeout=30.0,
        pool_timeout=30.0,
        http_version="1.1"
    )

async def telegram_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_message or not update.effective_user or not update.effective_chat:
        return

    chat_id = str(update.effective_chat.id)
    user_name = update.effective_user.username or update.effective_user.first_name or "Agent"
    raw_text = update.effective_message.text or ""

    async with AsyncSessionLocal() as db:
        response_text = await BotCommandHandler.handle_incoming_message(
            db=db,
            channel="telegram",
            sender_id=chat_id,
            sender_name=user_name,
            raw_text=raw_text
        )

    if response_text:
        try:
            await update.effective_message.reply_text(response_text, parse_mode="Markdown")
        except Exception:
            # Fallback to plain text if Markdown parser encounters unmatched characters
            await update.effective_message.reply_text(response_text)


async def send_telegram_notification(chat_id: str, message_text: str) -> bool:
    """Send an async Telegram notification to an agent with markdown fallback resilience."""
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.warning("[TelegramAdapter] TELEGRAM_BOT_TOKEN not configured.")
        return False
    try:
        req = get_telegram_request()
        bot = Bot(token=settings.TELEGRAM_BOT_TOKEN, request=req)
        async with bot:
            try:
                await bot.send_message(chat_id=chat_id, text=message_text, parse_mode="Markdown", disable_web_page_preview=True)
                return True
            except Exception as e:
                logger.warning(f"[TelegramAdapter] Markdown parsing failed, retrying plain text: {e}")
                await bot.send_message(chat_id=chat_id, text=message_text, disable_web_page_preview=True)
                return True
    except Exception as e:
        logger.error(f"[TelegramAdapter] Failed to send notification to {chat_id}: {e}")
        return False


async def send_telegram_media_group(chat_id: str, image_paths: list[str], caption: str = "") -> bool:
    """Send multiple clean photos as a Telegram Media Group Album."""
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.warning("[TelegramAdapter] TELEGRAM_BOT_TOKEN not configured.")
        return False
    try:
        req = get_telegram_request()
        bot = Bot(token=settings.TELEGRAM_BOT_TOKEN, request=req)
        
        media = []
        opened_files = []
        for idx, path in enumerate(image_paths[:10]):
            try:
                f = open(path, "rb")
                opened_files.append(f)
                media_cap = caption if idx == 0 else None
                media.append(InputMediaPhoto(media=f, caption=media_cap))
            except Exception as e_file:
                logger.warning(f"[TelegramAdapter] Failed to open image {path}: {e_file}")

        try:
            if media:
                async with bot:
                    await bot.send_media_group(chat_id=chat_id, media=media)
                return True
        finally:
            for f in opened_files:
                try:
                    f.close()
                except Exception:
                    pass
    except Exception as e:
        logger.error(f"[TelegramAdapter] Failed to send media group to {chat_id}: {e}")
        return False


async def send_telegram_document(chat_id: str, document_path: str, caption: str = "", filename: Optional[str] = None) -> bool:
    """Send a PDF or document file directly to a Telegram chat."""
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.warning("[TelegramAdapter] TELEGRAM_BOT_TOKEN not configured.")
        return False
    try:
        req = get_telegram_request()
        bot = Bot(token=settings.TELEGRAM_BOT_TOKEN, request=req)
        with open(document_path, "rb") as doc_f:
            async with bot:
                await bot.send_document(
                    chat_id=chat_id,
                    document=doc_f,
                    filename=filename or os.path.basename(document_path),
                    caption=caption
                )
        return True
    except Exception as e:
        logger.error(f"[TelegramAdapter] Failed to send document to {chat_id}: {e}")
        return False


async def telegram_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Catches and suppresses transient network / DNS polling blips."""
    err = context.error
    if err:
        err_str = str(err).lower()
        if "name resolution" in err_str or "connecterror" in err_str or "timed out" in err_str or "networkerror" in err_str:
            logger.warning(f"[TelegramAdapter] Transient network/DNS notice during polling: {err}")
            return
        logger.error(f"[TelegramAdapter] Unhandled bot exception: {err}")


def build_telegram_app() -> Optional[Application]:
    if not settings.TELEGRAM_BOT_TOKEN:
        return None
    req = get_telegram_request()
    app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).request(req).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, telegram_message_handler))
    app.add_handler(CommandHandler("start", telegram_message_handler))
    app.add_handler(CommandHandler("help", telegram_message_handler))
    app.add_error_handler(telegram_error_handler)
    return app
