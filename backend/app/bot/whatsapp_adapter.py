import logging
import httpx
from typing import Optional, Dict, Any
from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.bot.command_handler import BotCommandHandler

logger = logging.getLogger(__name__)

SENT_BOT_MESSAGE_IDS = set()

class WhatsAppAdapter:
    @staticmethod
    async def process_webhook_payload(payload: Dict[str, Any]) -> Optional[str]:
        """
        Process Evolution API incoming WhatsApp webhook payload.
        Calls shared BotCommandHandler.
        """
        try:
            event = payload.get("event")
            instance_name = payload.get("instance") or settings.EVOLUTION_INSTANCE_NAME
            logger.info(f"[WhatsAppAdapter] Received webhook event: '{event}', instance: '{instance_name}'")

            data = payload.get("data", {})
            if isinstance(data, list):
                if not data:
                    return None
                data = data[0]

            if not isinstance(data, dict):
                return None

            key = data.get("key", {})
            msg_id = key.get("id")

            from_me = bool(key.get("fromMe"))
            remote_jid = key.get("remoteJid", "")
            if not remote_jid:
                return None

            is_group = "@g.us" in remote_jid
            group_subject = payload.get("data", {}).get("groupMetadata", {}).get("subject") or data.get("pushName") or ""

            # Check outbound bot message to prevent response loops
            if from_me:
                if msg_id in SENT_BOT_MESSAGE_IDS:
                    try:
                        SENT_BOT_MESSAGE_IDS.remove(msg_id)
                    except KeyError:
                        pass
                    logger.info(f"[WhatsAppAdapter] Skipping outbound bot response (msg_id={msg_id})")
                    return None

            # 1-on-1 Private Direct Chat Guard:
            # If someone else (from_me=False) messages the agent's personal WhatsApp 1-on-1,
            # DO NOT respond at all! Silently ignore so bot never sends welcome messages to private contacts.
            if not is_group and not from_me:
                logger.info(f"[WhatsAppAdapter] Ignoring 1-on-1 private message from 3rd party ({remote_jid}) on personal agent number.")
                return None

            # Determine recipient ID: for groups (@g.us), use full JID; for direct chat, extract phone number
            if is_group:
                sender_id = remote_jid
                sender_name = group_subject or "WhatsApp Group"
            else:
                sender_id = remote_jid.split("@")[0] if "@" in remote_jid else remote_jid
                sender_name = data.get("pushName") or "WhatsApp User"

            message = data.get("message", {})
            if not isinstance(message, dict):
                message = {}

            raw_text = (
                message.get("conversation") or
                message.get("extendedTextMessage", {}).get("text") or
                message.get("imageMessage", {}).get("caption") or
                message.get("videoMessage", {}).get("caption") or
                ""
            )

            # Check for voice note / audio message
            audio_msg = message.get("audioMessage") or message.get("pttMessage")
            if not raw_text and audio_msg and isinstance(audio_msg, dict):
                audio_url = audio_msg.get("url")
                if audio_url:
                    from app.services.audio_transcriber import AudioTranscriberService
                    headers = {}
                    if settings.EVOLUTION_API_KEY:
                        headers["apikey"] = str(settings.EVOLUTION_API_KEY)
                    logger.info(f"[WhatsAppAdapter] Voice note received from {sender_id}. Transcribing audio...")
                    transcribed = await AudioTranscriberService.transcribe_audio_url(audio_url, headers=headers)
                    if transcribed:
                        raw_text = transcribed

            if not raw_text or not sender_id:
                logger.info(f"[WhatsAppAdapter] Message missing text or sender_id. Text: '{raw_text}', Sender: '{sender_id}'")
                return None

            logger.info(f"[WhatsAppAdapter] Processing incoming message from {sender_name} ({sender_id}) [fromMe={from_me}, isGroup={is_group}]: '{raw_text}'")

            async with AsyncSessionLocal() as db:
                response_text = await BotCommandHandler.handle_incoming_message(
                    db=db,
                    channel="whatsapp",
                    sender_id=sender_id,
                    sender_name=sender_name,
                    raw_text=raw_text,
                    from_me=from_me,
                    instance_name=instance_name,
                    group_subject=group_subject
                )

            if response_text:
                logger.info(f"[WhatsAppAdapter] Sending AI response to {sender_id} via instance '{instance_name}'...")
                await WhatsAppAdapter.send_message(
                    phone_number=sender_id,
                    text=response_text,
                    instance_name=instance_name
                )

            return response_text
        except Exception as e:
            logger.error(f"[WhatsAppAdapter] Webhook error: {e}", exc_info=True)
            return None
            return None

    @staticmethod
    async def resolve_active_instance(instance_name: Optional[str] = None, base_url: str = "http://evolution:8080", headers: dict = {}) -> str:
        if instance_name and instance_name != settings.EVOLUTION_INSTANCE_NAME:
            return instance_name

        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{base_url}/instance/fetchInstances", headers=headers)
                if res.status_code == 200:
                    instances = res.json()
                    if isinstance(instances, list) and len(instances) > 0:
                        for item in instances:
                            inst_obj = item.get("instance", {}) if isinstance(item, dict) else {}
                            if inst_obj.get("status") == "open" or item.get("connectionStatus") == "open":
                                name = inst_obj.get("instanceName") or item.get("name")
                                if name:
                                    return name
                        first_name = instances[0].get("instance", {}).get("instanceName") or instances[0].get("name")
                        if first_name:
                            return first_name
        except Exception:
            pass
        return instance_name or settings.EVOLUTION_INSTANCE_NAME

    @staticmethod
    async def send_message(phone_number: str, text: str, instance_name: Optional[str] = None) -> bool:
        """Send a WhatsApp message via Evolution API REST endpoint."""
        base_url = settings.EVOLUTION_API_URL or "http://evolution:8080"
        if "localhost" in base_url or "127.0.0.1" in base_url:
            base_url = "http://evolution:8080"
        base_url = base_url.rstrip("/")

        headers = {"Content-Type": "application/json"}
        if settings.EVOLUTION_API_KEY:
            headers["apikey"] = str(settings.EVOLUTION_API_KEY)

        inst = await WhatsAppAdapter.resolve_active_instance(instance_name, base_url, headers)
        clean_recipient = phone_number if "@g.us" in phone_number else phone_number.replace("+", "").replace(" ", "")

        url = f"{base_url}/message/sendText/{inst}"
        body = {
            "number": clean_recipient,
            "text": text,
            "options": {"delay": 1200, "presence": "composing"},
            "textMessage": {"text": text}
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(url, json=body, headers=headers)
                if res.status_code in [200, 201]:
                    try:
                        res_data = res.json()
                        sent_id = res_data.get("key", {}).get("id")
                        if sent_id:
                            SENT_BOT_MESSAGE_IDS.add(sent_id)
                            if len(SENT_BOT_MESSAGE_IDS) > 2000:
                                SENT_BOT_MESSAGE_IDS.clear()
                    except Exception:
                        pass
                    logger.info(f"[WhatsAppAdapter] Message sent successfully to {clean_recipient} via instance '{inst}'")
                    return True
                else:
                    logger.error(f"[WhatsAppAdapter] Failed to send message via instance '{inst}': status {res.status_code}, response: {res.text}")
                    return False
        except Exception as e:
            logger.error(f"[WhatsAppAdapter] HTTP exception sending message via instance '{inst}': {e}")
            return False
