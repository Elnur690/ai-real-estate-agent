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

            # Resolve tenant for this WhatsApp instance
            async with AsyncSessionLocal() as db:
                tenant = None
                if instance_name and instance_name.startswith("tenant_"):
                    try:
                        t_id = int(instance_name.replace("tenant_", ""))
                        stmt_id = select(Tenant).where(Tenant.id == t_id)
                        res_id = await db.execute(stmt_id)
                        tenant = res_id.scalars().first()
                    except ValueError:
                        pass

                if not tenant:
                    clean_remote = re.sub(r'\D', '', remote_jid.split("@")[0])
                    stmt_w = select(Tenant)
                    res_w = await db.execute(stmt_w)
                    all_w = res_w.scalars().all()
                    for t in all_w:
                        t_wa = re.sub(r'\D', '', t.whatsapp_number or "")
                        t_ph = re.sub(r'\D', '', t.phone or "")
                        if (t_wa and (t_wa in clean_remote or clean_remote in t_wa)) or (t_ph and (t_ph in clean_remote or clean_remote in t_ph)):
                            tenant = t
                            break

                if not tenant:
                    logger.info(f"[WhatsAppAdapter] No registered tenant found for instance '{instance_name}' / remote '{remote_jid}'. Ignoring.")
                    return None

                # STRICT SENDER PRIVACY CHECK (Step 1: Check authorization before downloading/transcribing any data)
                allowed_groups = list(tenant.allowed_group_jids or [])
                remote_digits = re.sub(r'\D', '', remote_jid.split("@")[0])
                tenant_digits = [
                    re.sub(r'\D', '', t.whatsapp_number or "") for t in [tenant] if t.whatsapp_number
                ] + [
                    re.sub(r'\D', '', t.phone or "") for t in [tenant] if t.phone
                ]
                tenant_digits = [d for d in tenant_digits if d]
                is_self_chat = any(td and (td in remote_digits or remote_digits in td) for td in tenant_digits)

                # Case A: 1-on-1 Direct Chat -> MUST ONLY BE AGENT'S OWN NUMBER (Self-chat)
                if not is_group:
                    if not is_self_chat:
                        # Private conversation between agent and a 3rd party (client, friend, family). SILENTLY DROP!
                        return None
                    sender_id = remote_digits
                    sender_name = data.get("pushName") or tenant.name or "Agent"

                # Case B: WhatsApp Group Chat (@g.us)
                else:
                    sender_id = remote_jid
                    sender_name = group_subject or "WhatsApp Group"

                # Extract message text
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
                text_lower = raw_text.strip().lower()

                # Group Pairing Filter
                if is_group and remote_jid not in allowed_groups:
                    is_pair_cmd = any(cmd in text_lower for cmd in ["/pair_group", "/set_group", "/bot_here", "/group_pair", "pair group", "bot qoş", "bot qos", "bot burda", "bot burada"])
                    is_unpair_cmd = any(cmd in text_lower for cmd in ["/unpair_group", "/remove_group", "/bot_leave", "/leave_group", "/bot_exit", "bot ayır", "bot ayir", "bot çıx", "bot cix", "bot sil", "botu çıxar", "botu cixar"])
                    if not is_pair_cmd and not is_unpair_cmd:
                        # Un-paired group and not a pairing command -> SILENTLY DROP without downloading media!
                        return None

                # Check for voice note / audio message (Only for authorized self-chat or paired group!)
                audio_msg = message.get("audioMessage") or message.get("pttMessage")
                if not raw_text and audio_msg and isinstance(audio_msg, dict):
                    audio_url = audio_msg.get("url")
                    if audio_url:
                        from app.services.audio_transcriber import AudioTranscriberService
                        headers = {}
                        if settings.EVOLUTION_API_KEY:
                            headers["apikey"] = str(settings.EVOLUTION_API_KEY)
                        audio_mime = audio_msg.get("mimetype") or "audio/ogg"
                        logger.info(f"[WhatsAppAdapter] Authorized voice note received ({audio_mime}). Transcribing audio...")
                        transcribed = await AudioTranscriberService.transcribe_audio_url(audio_url, headers=headers, mime_type=audio_mime)
                        if transcribed:
                            raw_text = transcribed

                if not raw_text:
                    return None

                logger.info(f"[WhatsAppAdapter] Processing valid agent message from {sender_name} ({sender_id}): '{raw_text}'")

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

    @staticmethod
    async def resolve_active_instance(instance_name: Optional[str] = None, base_url: str = "http://evolution:8080", headers: dict = {}) -> str:
        if instance_name:
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
        if "@g.us" in phone_number:
            clean_recipient = phone_number
        else:
            clean_recipient = re.sub(r'\D', '', phone_number.split("@")[0])

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
        if "@g.us" in phone_number:
            clean_recipient = phone_number
        else:
            clean_recipient = re.sub(r'\D', '', phone_number.split("@")[0])

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

