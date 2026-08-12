import logging
import httpx
from typing import Optional, Dict, Any
from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.bot.command_handler import BotCommandHandler

logger = logging.getLogger(__name__)

class WhatsAppAdapter:
    @staticmethod
    async def process_webhook_payload(payload: Dict[str, Any]) -> Optional[str]:
        """
        Process Evolution API incoming WhatsApp webhook payload.
        Calls shared BotCommandHandler.
        """
        try:
            data = payload.get("data", {})
            key = data.get("key", {})

            # Ignore messages sent by bot itself
            if key.get("fromMe"):
                return None

            remote_jid = key.get("remoteJid", "")
            sender_id = remote_jid.split("@")[0] if "@" in remote_jid else remote_jid
            push_name = data.get("pushName") or "WhatsApp Agent"

            message = data.get("message", {})
            raw_text = (
                message.get("conversation") or
                message.get("extendedTextMessage", {}).get("text") or
                ""
            )

            if not raw_text or not sender_id:
                return None

            async with AsyncSessionLocal() as db:
                response_text = await BotCommandHandler.handle_incoming_message(
                    db=db,
                    channel="whatsapp",
                    sender_id=sender_id,
                    sender_name=push_name,
                    raw_text=raw_text
                )

            if response_text:
                await WhatsAppAdapter.send_message(sender_id, response_text)

            return response_text
        except Exception as e:
            logger.error(f"[WhatsAppAdapter] Webhook error: {e}")
            return None

    @staticmethod
    async def send_message(phone_number: str, text: str) -> bool:
        """Send a WhatsApp message via Evolution API REST endpoint."""
        if not settings.EVOLUTION_API_URL:
            logger.warning("[WhatsAppAdapter] EVOLUTION_API_URL not set.")
            return False

        clean_number = phone_number.replace("+", "").replace(" ", "")
        base_url = settings.EVOLUTION_API_URL or "http://evolution:8080"
        if "localhost" in base_url or "127.0.0.1" in base_url:
            base_url = "http://evolution:8080"
        base_url = base_url.rstrip("/")

        url = f"{base_url}/message/sendText/{settings.EVOLUTION_INSTANCE_NAME}"
        headers = {"Content-Type": "application/json"}
        if settings.EVOLUTION_API_KEY:
            headers["apikey"] = str(settings.EVOLUTION_API_KEY)

        body = {
            "number": clean_number,
            "options": {"delay": 1200, "presence": "composing"},
            "textMessage": {"text": text}
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(url, json=body, headers=headers)
                if res.status_code in [200, 201]:
                    logger.info(f"[WhatsAppAdapter] Message sent successfully to {clean_number}")
                    return True
                else:
                    logger.error(f"[WhatsAppAdapter] Failed to send message: {res.status_code} {res.text}")
                    return False
        except Exception as e:
            logger.error(f"[WhatsAppAdapter] HTTP exception sending message: {e}")
            return False
