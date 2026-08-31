import os
import re
import logging
import asyncio
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
            import re
            from sqlalchemy import select
            from app.models.tenant import Tenant

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

            # Skip outbound bot messages to prevent echo loops
            if from_me and msg_id in SENT_BOT_MESSAGE_IDS:
                try:
                    SENT_BOT_MESSAGE_IDS.remove(msg_id)
                except KeyError:
                    pass
                logger.info(f"[WhatsAppAdapter] Skipping outbound bot response (msg_id={msg_id})")
                return None

            is_group = "@g.us" in remote_jid
            group_metadata = payload.get("data", {}).get("groupMetadata", {})
            group_subject = (
                group_metadata.get("subject")
                or payload.get("data", {}).get("groupName")
                or (data.get("pushName") if not is_group else "")
                or "İşçi WhatsApp Qrupu"
            )

            # 1. Extract message text
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

            # 2. Check for voice note / audio message
            audio_msg = message.get("audioMessage") or message.get("pttMessage")
            if not raw_text and audio_msg and isinstance(audio_msg, dict):
                audio_url = audio_msg.get("url")
                if audio_url:
                    from app.services.audio_transcriber import AudioTranscriberService
                    headers = {}
                    if settings.EVOLUTION_API_KEY:
                        headers["apikey"] = str(settings.EVOLUTION_API_KEY)
                    audio_mime = audio_msg.get("mimetype") or "audio/ogg"
                    logger.info(f"[WhatsAppAdapter] Voice note received ({audio_mime}). Transcribing audio...")
                    transcribed = await AudioTranscriberService.transcribe_audio_url(audio_url, headers=headers, mime_type=audio_mime)
                    if transcribed:
                        raw_text = transcribed

            if not raw_text:
                return None

            clean_digits = re.sub(r'\D', '', remote_jid.split("@")[0])
            sender_id = remote_jid if is_group else (clean_digits or remote_jid)
            sender_name = group_subject if is_group else (data.get("pushName") or "Agent")

            logger.info(f"[WhatsAppAdapter] Processing incoming message from {sender_name} ({sender_id}) via instance '{instance_name}': '{raw_text}'")

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
    def normalize_recipient(phone_number: str) -> str:
        """Normalizes any Azerbaijani phone number (e.g. 0501234567 -> 994501234567) or preserves group JID."""
        if not phone_number:
            return ""
        if "@g.us" in phone_number:
            return phone_number.strip()
        digits = re.sub(r'\D', '', str(phone_number).split("@")[0])
        if digits.startswith("0") and len(digits) == 10:
            digits = "994" + digits[1:]
        elif not digits.startswith("994") and len(digits) == 9:
            digits = "994" + digits
        return digits

    @staticmethod
    async def resolve_active_instance(instance_name: Optional[str] = None, base_url: str = "http://evolution:8080", headers: dict = {}) -> str:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{base_url}/instance/fetchInstances", headers=headers)
                if res.status_code == 200:
                    instances = res.json()
                    if isinstance(instances, list) and len(instances) > 0:
                        # 1. If explicit instance requested, check if it is active and open
                        if instance_name:
                            for item in instances:
                                inst_obj = item.get("instance", {}) if isinstance(item, dict) else {}
                                name = inst_obj.get("instanceName") or item.get("name")
                                status = inst_obj.get("status") or item.get("connectionStatus")
                                if name == instance_name and status in ["open", "connecting"]:
                                    return name

                        # 2. Otherwise find any connected/open instance
                        for item in instances:
                            inst_obj = item.get("instance", {}) if isinstance(item, dict) else {}
                            status = inst_obj.get("status") or item.get("connectionStatus")
                            if status == "open":
                                name = inst_obj.get("instanceName") or item.get("name")
                                if name:
                                    return name

                        # 3. First available instance
                        first_name = instances[0].get("instance", {}).get("instanceName") or instances[0].get("name")
                        if first_name:
                            return first_name
        except Exception as e:
            logger.debug(f"[WhatsAppAdapter] resolve_active_instance lookup notice: {e}")

        return instance_name or settings.EVOLUTION_INSTANCE_NAME or "default"

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
        clean_recipient = WhatsAppAdapter.normalize_recipient(phone_number)
        if not clean_recipient:
            logger.warning(f"[WhatsAppAdapter] Cannot send message: invalid recipient '{phone_number}'")
            return False

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

    @staticmethod
    async def send_text(phone_number: str, text: str, instance_name: Optional[str] = None) -> bool:
        """Alias for send_message."""
        return await WhatsAppAdapter.send_message(phone_number=phone_number, text=text, instance_name=instance_name)

    @staticmethod
    async def send_media_image(phone_number: str, image_path: str, caption: str = "", instance_name: Optional[str] = None) -> bool:
        """Send an image with caption via Evolution API."""
        import base64
        base_url = settings.EVOLUTION_API_URL or "http://evolution:8080"
        if "localhost" in base_url or "127.0.0.1" in base_url:
            base_url = "http://evolution:8080"
        base_url = base_url.rstrip("/")

        headers = {"Content-Type": "application/json"}
        if settings.EVOLUTION_API_KEY:
            headers["apikey"] = str(settings.EVOLUTION_API_KEY)

        inst = await WhatsAppAdapter.resolve_active_instance(instance_name, base_url, headers)
        clean_recipient = WhatsAppAdapter.normalize_recipient(phone_number)
        if not clean_recipient:
            logger.warning(f"[WhatsAppAdapter] Cannot send media: invalid recipient '{phone_number}'")
            return False

        try:
            with open(image_path, "rb") as img_f:
                b64_data = base64.b64encode(img_f.read()).decode("utf-8")

            # Evolution API validator requires pure base64 string or URL
            raw_b64 = b64_data.split(",")[-1] if "," in b64_data else b64_data
            file_name = os.path.basename(image_path)

            url = f"{base_url}/message/sendMedia/{inst}"
            body = {
                "number": clean_recipient,
                "mediatype": "image",
                "mediaType": "image",
                "mimetype": "image/jpeg",
                "mimeType": "image/jpeg",
                "caption": caption,
                "media": raw_b64,
                "fileName": file_name,
                "options": {
                    "delay": 1200,
                    "presence": "composing"
                }
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
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
                    return True
                else:
                    logger.error(f"[WhatsAppAdapter] Failed to send media image via instance '{inst}': status {res.status_code}, response: {res.text}")
                    return False
        except Exception as e:
            logger.error(f"[WhatsAppAdapter] Failed to send media image via instance '{inst}': {e}")
            return False

    @staticmethod
    async def send_document(phone_number: str, document_path: str, caption: str = "", filename: Optional[str] = None, instance_name: Optional[str] = None) -> bool:
        """Send a PDF or document via Evolution API."""
        import base64
        base_url = settings.EVOLUTION_API_URL or "http://evolution:8080"
        if "localhost" in base_url or "127.0.0.1" in base_url:
            base_url = "http://evolution:8080"
        base_url = base_url.rstrip("/")

        headers = {"Content-Type": "application/json"}
        if settings.EVOLUTION_API_KEY:
            headers["apikey"] = str(settings.EVOLUTION_API_KEY)

        inst = await WhatsAppAdapter.resolve_active_instance(instance_name, base_url, headers)
        clean_recipient = WhatsAppAdapter.normalize_recipient(phone_number)
        if not clean_recipient:
            logger.warning(f"[WhatsAppAdapter] Cannot send document: invalid recipient '{phone_number}'")
            return False

        try:
            with open(document_path, "rb") as doc_f:
                b64_data = base64.b64encode(doc_f.read()).decode("utf-8")

            raw_b64 = b64_data.split(",")[-1] if "," in b64_data else b64_data
            doc_filename = filename or "buklet.pdf"

            url = f"{base_url}/message/sendMedia/{inst}"
            body = {
                "number": clean_recipient,
                "mediatype": "document",
                "mediaType": "document",
                "mimetype": "application/pdf",
                "mimeType": "application/pdf",
                "caption": caption,
                "fileName": doc_filename,
                "media": raw_b64,
                "options": {
                    "delay": 1200,
                    "presence": "composing"
                }
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
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
                    return True
                else:
                    logger.error(f"[WhatsAppAdapter] Failed to send document via instance '{inst}': status {res.status_code}, response: {res.text}")
                    return False
        except Exception as e:
            logger.error(f"[WhatsAppAdapter] Failed to send document via instance '{inst}': {e}")
            return False

