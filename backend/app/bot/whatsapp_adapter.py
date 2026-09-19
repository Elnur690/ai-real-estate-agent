import os
import re
import logging
import asyncio
import httpx
from typing import Optional, Dict, Any, List
from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.bot.command_handler import BotCommandHandler

logger = logging.getLogger(__name__)

SENT_BOT_MESSAGE_IDS = set()

# Bidirectional LID <-> Phone Number mapping cache
_LID_TO_PHONE_MAP: Dict[str, str] = {}
_PHONE_TO_LID_MAP: Dict[str, str] = {}
_GROUP_METADATA_FETCH_CACHE: Dict[str, float] = {}

class WhatsAppAdapter:
    @staticmethod
    def normalize_jid_or_phone(val: Optional[str]) -> tuple[Optional[str], Optional[str]]:
        """
        Given a JID or phone string (e.g. '994501234567@s.whatsapp.net' or '20585878929644@lid'),
        determines if it's a real phone number or a WhatsApp LID.
        Returns: (phone_digits, lid_digits)
        """
        if not val or not isinstance(val, str):
            return None, None
        val_clean = val.strip()
        digits = re.sub(r'\D', '', val_clean.split('@')[0])
        if not digits:
            return None, None
        if "@lid" in val_clean or val_clean.endswith(".lid"):
            return None, digits
        if "@s.whatsapp.net" in val_clean or "@c.us" in val_clean:
            return digits, None
        # WhatsApp LIDs are typically 14-16 digits starting with 1 or 2,
        # whereas Azerbaijani and standard international phone numbers are 9-12 digits.
        if len(digits) >= 14 and not digits.startswith("994"):
            return None, digits
        return digits, None

    @staticmethod
    def get_phone_for_lid(lid_digits: Optional[str]) -> Optional[str]:
        if not lid_digits:
            return None
        clean = re.sub(r'\D', '', str(lid_digits).split('@')[0])
        return _LID_TO_PHONE_MAP.get(clean)

    @staticmethod
    def get_lid_for_phone(phone_digits: Optional[str]) -> Optional[str]:
        if not phone_digits:
            return None
        clean = re.sub(r'\D', '', str(phone_digits).split('@')[0])
        lid = _PHONE_TO_LID_MAP.get(clean)
        if not lid and len(clean) >= 9:
            lid = _PHONE_TO_LID_MAP.get(clean[-9:])
        return lid

    @staticmethod
    def record_lid_phone_mapping(lid: Optional[str], phone: Optional[str]) -> None:
        """Records bidirectional mapping between a WhatsApp LID and a phone number."""
        if not lid or not phone:
            return
        clean_lid = re.sub(r'\D', '', str(lid).split('@')[0])
        clean_phone = re.sub(r'\D', '', str(phone).split('@')[0])
        if clean_lid and clean_phone and clean_lid != clean_phone:
            _LID_TO_PHONE_MAP[clean_lid] = clean_phone
            _PHONE_TO_LID_MAP[clean_phone] = clean_lid
            if len(clean_phone) >= 9:
                _PHONE_TO_LID_MAP[clean_phone[-9:]] = clean_lid
            logger.info(f"[WhatsAppAdapter] Mapped WhatsApp LID {clean_lid} <=> Phone +{clean_phone}")

    @staticmethod
    async def fetch_and_cache_group_participants(
        instance_name: Optional[str],
        group_jid: str,
        force: bool = False
    ) -> Dict[str, str]:
        """
        Fetches group participant info from Evolution API and caches LID <-> Phone mappings.
        Returns mapping of {lid_digits: phone_digits}.
        """
        if not group_jid or "@g.us" not in group_jid:
            return {}

        import time
        now = time.time()
        last_fetch = _GROUP_METADATA_FETCH_CACHE.get(group_jid, 0.0)
        if not force and (now - last_fetch) < 60.0:
            return {}

        _GROUP_METADATA_FETCH_CACHE[group_jid] = now
        base_url = settings.EVOLUTION_API_URL or "http://evolution:8080"
        target_instance = instance_name or settings.EVOLUTION_INSTANCE_NAME or "realestate_agent"

        headers = {"Content-Type": "application/json"}
        if settings.EVOLUTION_API_KEY:
            headers["apikey"] = str(settings.EVOLUTION_API_KEY)

        resolved: Dict[str, str] = {}
        try:
            url = f"{base_url.rstrip('/')}/group/findGroupInfos/{target_instance}"
            async with httpx.AsyncClient(timeout=4.0) as client:
                res = await client.get(url, params={"groupJid": group_jid}, headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    if isinstance(data, list) and data:
                        data = data[0]
                    participants = (
                        data.get("participants")
                        or (data.get("group", {}).get("participants") if isinstance(data, dict) else [])
                        or []
                    )
                    for p in participants:
                        if isinstance(p, dict):
                            p_id = str(p.get("id") or "")
                            p_lid = str(p.get("lid") or "")
                            p_phone = str(p.get("phoneNumber") or p.get("phone") or "")

                            cand_phone, _ = WhatsAppAdapter.normalize_jid_or_phone(p_id)
                            _, cand_lid = WhatsAppAdapter.normalize_jid_or_phone(p_lid)
                            if not cand_phone and p_phone:
                                cand_phone, _ = WhatsAppAdapter.normalize_jid_or_phone(p_phone)
                            if not cand_phone and "@lid" in p_id and "@s.whatsapp.net" in p_lid:
                                cand_phone, _ = WhatsAppAdapter.normalize_jid_or_phone(p_lid)
                                _, cand_lid = WhatsAppAdapter.normalize_jid_or_phone(p_id)

                            if cand_phone and cand_lid:
                                WhatsAppAdapter.record_lid_phone_mapping(cand_lid, cand_phone)
                                resolved[cand_lid] = cand_phone
        except Exception as e:
            logger.debug(f"[WhatsAppAdapter] Evolution group info lookup notice for {group_jid}: {e}")

        return resolved

    @staticmethod
    async def resolve_sender_participant(
        payload: Dict[str, Any],
        instance_name: Optional[str] = None,
        remote_jid: Optional[str] = None
    ) -> tuple[Optional[str], Optional[str]]:
        """
        Extracts and resolves the true sender phone number and LID from an incoming message payload.
        Returns: (phone_digits, lid_digits)
        """
        data = payload.get("data", {})
        if isinstance(data, list):
            data = data[0] if data else {}
        key = data.get("key", {}) if isinstance(data, dict) else {}

        candidates = [
            key.get("participantAlt"),
            data.get("participantAlt"),
            payload.get("data", {}).get("participantAlt") if isinstance(payload.get("data"), dict) else None,
            key.get("participant_alt"),
            data.get("participant_alt"),
            data.get("senderPn"),
            data.get("senderPhone"),
            key.get("remoteJidAlt"),
            data.get("remoteJidAlt"),
            data.get("sender"),
            key.get("participant"),
            data.get("participant"),
            payload.get("data", {}).get("participant") if isinstance(payload.get("data"), dict) else None,
        ]

        found_phone: Optional[str] = None
        found_lid: Optional[str] = None

        for c in candidates:
            if c and isinstance(c, str):
                p, l = WhatsAppAdapter.normalize_jid_or_phone(c)
                if p and not found_phone:
                    found_phone = p
                if l and not found_lid:
                    found_lid = l

        # If both found in payload, record mapping immediately
        if found_phone and found_lid:
            WhatsAppAdapter.record_lid_phone_mapping(found_lid, found_phone)
            return found_phone, found_lid

        # If phone found, check if we know its LID
        if found_phone:
            cached_lid = WhatsAppAdapter.get_lid_for_phone(found_phone)
            return found_phone, found_lid or cached_lid

        # If only LID found:
        if found_lid:
            cached_phone = WhatsAppAdapter.get_phone_for_lid(found_lid)
            if cached_phone:
                return cached_phone, found_lid

            # Check groupMetadata embedded in payload
            group_meta = data.get("groupMetadata") or (payload.get("data", {}).get("groupMetadata") if isinstance(payload.get("data"), dict) else {})
            if isinstance(group_meta, dict):
                participants = group_meta.get("participants", [])
                for p in participants:
                    if isinstance(p, dict):
                        p_id = str(p.get("id") or "")
                        p_lid = str(p.get("lid") or "")
                        p_phone = str(p.get("phoneNumber") or p.get("phone") or "")
                        p_cand, _ = WhatsAppAdapter.normalize_jid_or_phone(p_id)
                        _, l_cand = WhatsAppAdapter.normalize_jid_or_phone(p_lid)
                        if not p_cand and p_phone:
                            p_cand, _ = WhatsAppAdapter.normalize_jid_or_phone(p_phone)
                        if p_cand and l_cand:
                            WhatsAppAdapter.record_lid_phone_mapping(l_cand, p_cand)
                            if l_cand == found_lid:
                                found_phone = p_cand

            if found_phone:
                return found_phone, found_lid

            # Fetch from Evolution API if group message
            group_jid = remote_jid or key.get("remoteJid") or ""
            if group_jid and "@g.us" in group_jid:
                resolved_map = await WhatsAppAdapter.fetch_and_cache_group_participants(instance_name, group_jid)
                if found_lid in resolved_map:
                    return resolved_map[found_lid], found_lid

            return found_lid, found_lid

        raw_p = key.get("participant") or data.get("participant") or ""
        digits = re.sub(r'\D', '', str(raw_p).split('@')[0]) if raw_p else None
        return digits, None

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

            event = str(payload.get("event") or "").lower().strip()
            instance_name = payload.get("instance") or settings.EVOLUTION_INSTANCE_NAME
            logger.info(f"[WhatsAppAdapter] Received webhook event: '{event}', instance: '{instance_name}'")

            # Handle group-participants.update (detect unknown persons added/removed)
            if event in ["group-participants.update", "group_participants_update", "groupparticipants.update"]:
                return await WhatsAppAdapter._handle_group_participants_update(payload, instance_name)

            # Ignore calls, call offers, presence updates, contact syncing, chats updates, etc.
            if event and event not in ["messages.upsert", "messages_upsert", "send_message"]:
                logger.debug(f"[WhatsAppAdapter] Skipping non-message event '{event}'")
                return None

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

            # STRICT PRIVACY & PERSONAL ASSISTANT RULE:
            # Agents interact with our bot ONLY and ONLY in groups where /bot_here was sent.
            # In 1-on-1 personal chats, the bot MUST NEVER intercept, transcribe, or send any message to contacts.
            if not is_group:
                logger.debug(f"[WhatsAppAdapter] Silently ignoring 1-on-1 private chat with {remote_jid} to protect personal contacts.")
                return None

            # Skip outbound bot messages to prevent echo loops
            if from_me and msg_id in SENT_BOT_MESSAGE_IDS:
                try:
                    SENT_BOT_MESSAGE_IDS.remove(msg_id)
                except KeyError:
                    pass
                logger.info(f"[WhatsAppAdapter] Skipping outbound bot response (msg_id={msg_id})")
                return None

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

            # 2. Check for voice note / audio message (STRICT PRIVACY: ONLY incoming in verified paired groups)
            audio_msg = message.get("audioMessage") or message.get("pttMessage")
            if not raw_text and audio_msg and isinstance(audio_msg, dict):
                # Personal 1-on-1 chats: NEVER listen to or transcribe personal voice notes or calls!
                if not is_group:
                    logger.debug(f"[WhatsAppAdapter] Silently ignoring personal 1-on-1 voice note/call from {remote_jid}")
                    return None

                # Outbound voice notes/calls from self: NEVER transcribe!
                if from_me:
                    logger.debug(f"[WhatsAppAdapter] Silently ignoring outbound audio from self to {remote_jid}")
                    return None

                # In groups, verify that the group is EXPLICITLY paired (/bot_here) before downloading/transcribing media
                async with AsyncSessionLocal() as db:
                    stmt_t = select(Tenant).where(Tenant.status == "active")
                    t_res = await db.execute(stmt_t)
                    active_tenants = t_res.scalars().all()

                    is_paired = any(
                        remote_jid in (t.allowed_group_jids or [])
                        for t in active_tenants
                    )
                    if not is_paired:
                        logger.debug(f"[WhatsAppAdapter] Silently ignoring voice note in un-paired group {remote_jid}")
                        return None

                import base64
                from app.services.audio_transcriber import AudioTranscriberService
                audio_mime = audio_msg.get("mimetype") or "audio/ogg"
                audio_bytes = None

                # Source A: Check direct base64 in payload
                b64_str = (
                    audio_msg.get("base64") or
                    message.get("base64") or
                    data.get("base64") or
                    payload.get("base64")
                )
                if b64_str and isinstance(b64_str, str):
                    try:
                        clean_b64 = b64_str.split(",")[-1]
                        audio_bytes = base64.b64decode(clean_b64)
                    except Exception as e_b64:
                        logger.debug(f"[WhatsAppAdapter] Direct base64 decode notice: {e_b64}")

                # Source B: Fetch decrypted media via Evolution API /chat/getBase64FromMediaMessage
                if not audio_bytes and settings.EVOLUTION_API_URL and instance_name and data.get("key"):
                    try:
                        media_endpoint = f"{settings.EVOLUTION_API_URL.rstrip('/')}/chat/getBase64FromMediaMessage/{instance_name}"
                        headers = {"Content-Type": "application/json"}
                        if settings.EVOLUTION_API_KEY:
                            headers["apikey"] = str(settings.EVOLUTION_API_KEY)
                        async with httpx.AsyncClient(timeout=15.0) as client:
                            req_body = {
                                "message": {
                                    "key": data.get("key"),
                                    "message": message
                                },
                                "convertToMp4": False
                            }
                            res = await client.post(media_endpoint, json=req_body, headers=headers)
                            if res.status_code == 200:
                                res_json = res.json()
                                b64_res = res_json.get("base64")
                                if b64_res:
                                    clean_b64 = b64_res.split(",")[-1]
                                    audio_bytes = base64.b64decode(clean_b64)
                    except Exception as e_evo_media:
                        logger.debug(f"[WhatsAppAdapter] Evolution media endpoint notice: {e_evo_media}")

                # Source C: Download audio via URL
                audio_url = audio_msg.get("url")
                if not audio_bytes and audio_url:
                    headers = {}
                    if settings.EVOLUTION_API_KEY:
                        headers["apikey"] = str(settings.EVOLUTION_API_KEY)
                    try:
                        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                            res = await client.get(audio_url, headers=headers)
                            if res.status_code == 200:
                                audio_bytes = res.content
                    except Exception as e_dl:
                        logger.debug(f"[WhatsAppAdapter] HTTP audio download notice: {e_dl}")

                if audio_bytes:
                    logger.info(f"[WhatsAppAdapter] Voice note received in group {remote_jid} ({audio_mime}, {len(audio_bytes)} bytes). Transcribing audio with Gemini...")
                    transcribed = await AudioTranscriberService.transcribe_audio_bytes(audio_bytes, mime_type=audio_mime)
                    if transcribed:
                        raw_text = transcribed

            if not raw_text:
                return None

            clean_digits = re.sub(r'\D', '', remote_jid.split("@")[0])
            sender_id = remote_jid if is_group else (clean_digits or remote_jid)
            sender_name = group_subject if is_group else (data.get("pushName") or "Agent")

            logger.info(f"[WhatsAppAdapter] Processing incoming message from {sender_name} ({sender_id}) via instance '{instance_name}': '{raw_text}'")

            sender_participant, sender_lid = await WhatsAppAdapter.resolve_sender_participant(
                payload=payload,
                instance_name=instance_name,
                remote_jid=remote_jid if is_group else None
            )

            async with AsyncSessionLocal() as db:
                response_text = await BotCommandHandler.handle_incoming_message(
                    db=db,
                    channel="whatsapp",
                    sender_id=sender_id,
                    sender_name=sender_name,
                    raw_text=raw_text,
                    from_me=from_me,
                    instance_name=instance_name,
                    group_subject=group_subject,
                    sender_participant=sender_participant,
                    sender_lid=sender_lid
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
    async def _handle_group_participants_update(payload: Dict[str, Any], instance_name: Optional[str]) -> Optional[str]:
        """Handles group member additions/removals to enforce approved phone numbers security."""
        try:
            import re
            from sqlalchemy import select
            from app.models.tenant import Tenant
            from app.bot.group_security import lock_group_due_to_unapproved_person, unlock_group, get_group_lock_unapproved_phone

            data = payload.get("data", {})
            if isinstance(data, list):
                if not data:
                    return None
                data = data[0]

            group_jid = data.get("id") or data.get("jid") or ""
            if not group_jid or "@g.us" not in group_jid:
                return None

            action = str(data.get("action") or "").lower()
            participants = data.get("participants", [])

            async with AsyncSessionLocal() as db:
                stmt = select(Tenant).where(Tenant.status == "active")
                res = await db.execute(stmt)
                tenants = res.scalars().all()
                matched_tenant = next((t for t in tenants if group_jid in (t.allowed_group_jids or [])), None)
                if not matched_tenant:
                    return None

                approved_nums = matched_tenant.get_approved_phone_numbers()

                if action in ["add", "invite"]:
                    for p in participants:
                        p_str = str(p)
                        cand_phone, cand_lid = WhatsAppAdapter.normalize_jid_or_phone(p_str)
                        # If LID received, try resolving via cache or Evolution API
                        if not cand_phone and cand_lid:
                            cand_phone = WhatsAppAdapter.get_phone_for_lid(cand_lid)
                            if not cand_phone:
                                group_map = await WhatsAppAdapter.fetch_and_cache_group_participants(
                                    instance_name, group_jid, force=True
                                )
                                cand_phone = group_map.get(cand_lid)

                        digits = cand_phone or cand_lid or re.sub(r'\D', '', p_str.split('@')[0])
                        suffix = digits[-9:] if len(digits) >= 9 else digits

                        # Check if participant is approved
                        is_approved = (
                            digits in approved_nums or
                            suffix in approved_nums or
                            (cand_lid and cand_lid in approved_nums) or
                            any(
                                (lid in approved_nums or phone in approved_nums)
                                for lid, phone in _LID_TO_PHONE_MAP.items()
                                if (lid == digits or lid == cand_lid) and (phone in approved_nums or (len(phone) >= 9 and phone[-9:] in approved_nums))
                            )
                        )
                        if not is_approved:
                            lock_group_due_to_unapproved_person(group_jid, digits)
                            alert_text = (
                                f"⚠️ *TƏHLÜKƏSİZLİK XƏBƏRDARLIĞI: Qrupa Yeni Şəxs Əlavə Edildi!* (+{digits})\n\n"
                                "Bu nömrə təsdiqlənmiş agent heyəti siyahısında yoxdur. "
                                "Məxfilik və təhlükəsizlik səbəbindən bu qrupda elanların paylaşılması və bot əmrləri dayandırıldı.\n\n"
                                "📌 *Nə etməli?*\n"
                                f"1. Bu şəxs komandanızın üzvüdürsə, nömrəni təsdiqləyin: `/nomre_elave {digits}`\n"
                                "2. Və ya həmin şəxsi qrupdan çıxarın."
                            )
                            await WhatsAppAdapter.send_message(
                                phone_number=group_jid,
                                text=alert_text,
                                instance_name=instance_name or f"tenant_{matched_tenant.id}"
                            )
                            return alert_text

                elif action in ["remove", "leave"]:
                    for p in participants:
                        p_str = str(p)
                        cand_phone, cand_lid = WhatsAppAdapter.normalize_jid_or_phone(p_str)
                        resolved_phone = cand_phone or WhatsAppAdapter.get_phone_for_lid(cand_lid)
                        digits = resolved_phone or cand_lid or re.sub(r'\D', '', p_str.split('@')[0])
                        locked_phone = get_group_lock_unapproved_phone(group_jid)
                        if locked_phone:
                            locked_resolved = WhatsAppAdapter.get_phone_for_lid(locked_phone) or locked_phone
                            if (digits == locked_phone or digits.endswith(locked_phone) or locked_phone.endswith(digits)
                                or (cand_lid and cand_lid == locked_phone)
                                or (resolved_phone and (resolved_phone == locked_phone or resolved_phone.endswith(locked_phone)))
                                or (locked_resolved and (digits == locked_resolved or digits.endswith(locked_resolved)))):
                                unlock_group(group_jid)
                                clear_text = "✅ Tanınmayan şəxs qrupdan çıxarıldı. Botun bu qrupdakı fəaliyyəti və elan göndərişi tam bərpa edildi! 🚀"
                                await WhatsAppAdapter.send_message(
                                    phone_number=group_jid,
                                    text=clear_text,
                                    instance_name=instance_name or f"tenant_{matched_tenant.id}"
                                )
                                return clear_text
        except Exception as e:
            logger.debug(f"[WhatsAppAdapter] group-participants.update error: {e}")
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
    async def fetch_open_instances(base_url: str = "http://evolution:8080", headers: dict = {}) -> List[str]:
        """Fetch all currently open/connected instance names from Evolution API."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{base_url}/instance/fetchInstances", headers=headers)
                if res.status_code == 200:
                    instances = res.json()
                    if isinstance(instances, list):
                        open_list = []
                        for item in instances:
                            inst_obj = item.get("instance", {}) if isinstance(item, dict) else {}
                            name = inst_obj.get("instanceName") or item.get("name")
                            status = inst_obj.get("status") or item.get("connectionStatus")
                            if name and status == "open":
                                open_list.append(name)
                        return open_list
        except Exception as e:
            logger.debug(f"[WhatsAppAdapter] fetch_open_instances lookup notice: {e}")
        return []

    @staticmethod
    async def resolve_active_instance(instance_name: Optional[str] = None, base_url: str = "http://evolution:8080", headers: dict = {}) -> str:
        open_instances = await WhatsAppAdapter.fetch_open_instances(base_url, headers)
        if instance_name and instance_name in open_instances:
            return instance_name
        if open_instances:
            return open_instances[0]
        return instance_name or "default"

    @staticmethod
    async def send_message(phone_number: str, text: str, instance_name: Optional[str] = None) -> bool:
        """Send a WhatsApp message via Evolution API REST endpoint with verified open instance fallback."""
        base_url = settings.EVOLUTION_API_URL or "http://evolution:8080"
        if "localhost" in base_url or "127.0.0.1" in base_url:
            base_url = "http://evolution:8080"
        base_url = base_url.rstrip("/")

        headers = {"Content-Type": "application/json"}
        if settings.EVOLUTION_API_KEY:
            headers["apikey"] = str(settings.EVOLUTION_API_KEY)

        open_instances = await WhatsAppAdapter.fetch_open_instances(base_url, headers)
        if instance_name and instance_name in open_instances:
            inst = instance_name
        elif open_instances:
            inst = open_instances[0]
        else:
            inst = instance_name or "default"

        clean_recipient = WhatsAppAdapter.normalize_recipient(phone_number)
        if not clean_recipient:
            logger.warning(f"[WhatsAppAdapter] Cannot send message: invalid recipient '{phone_number}'")
            return False

        # STRICT PRIVACY & PERSONAL ASSISTANT RULE:
        # Agents interact with our bot ONLY and ONLY in groups where /bot_here was sent.
        # Personal contacts and 1-on-1 chats must NEVER receive any message from our bot!
        if "@g.us" not in clean_recipient:
            logger.warning(f"[WhatsAppAdapter] Refusing to deliver message to personal 1-on-1 recipient '{clean_recipient}'. Bot delivery is strictly restricted to paired groups (@g.us).")
            return False

        url = f"{base_url}/message/sendText/{inst}"
        body = {
            "number": clean_recipient,
            "text": text,
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

                # Only attempt fallback if another VERIFIED open instance actually exists
                other_open = [name for name in open_instances if name != inst]
                if other_open:
                    fallback_inst = other_open[0]
                    logger.warning(f"[WhatsAppAdapter] Delivery to {clean_recipient} failed via '{inst}' ({res.status_code}). Retrying via active open instance '{fallback_inst}'...")
                    fallback_url = f"{base_url}/message/sendText/{fallback_inst}"
                    res_fb = await client.post(fallback_url, json=body, headers=headers)
                    if res_fb.status_code in [200, 201]:
                        logger.info(f"[WhatsAppAdapter] Message sent successfully to {clean_recipient} via fallback instance '{fallback_inst}'")
                        return True
                    else:
                        logger.warning(f"[WhatsAppAdapter] Fallback delivery via '{fallback_inst}' also returned status {res_fb.status_code}: {res_fb.text}")
                else:
                    logger.warning(f"[WhatsAppAdapter] Delivery to {clean_recipient} via instance '{inst}' returned status {res.status_code}: {res.text}")

                return False
        except Exception as e:
            logger.warning(f"[WhatsAppAdapter] HTTP exception sending message via instance '{inst}': {e}")
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

        # STRICT PRIVACY & PERSONAL ASSISTANT RULE:
        # Agents interact with our bot ONLY and ONLY in groups where /bot_here was sent.
        # Personal contacts and 1-on-1 chats must NEVER receive any media from our bot!
        if "@g.us" not in clean_recipient:
            logger.warning(f"[WhatsAppAdapter] Refusing to deliver media to personal 1-on-1 recipient '{clean_recipient}'. Bot delivery is strictly restricted to paired groups (@g.us).")
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
                "mimetype": "image/jpeg",
                "caption": caption,
                "media": raw_b64,
                "fileName": file_name,
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

        # STRICT PRIVACY & PERSONAL ASSISTANT RULE:
        # Agents interact with our bot ONLY and ONLY in groups where /bot_here was sent.
        # Personal contacts and 1-on-1 chats must NEVER receive any document from our bot!
        if "@g.us" not in clean_recipient:
            logger.warning(f"[WhatsAppAdapter] Refusing to deliver document to personal 1-on-1 recipient '{clean_recipient}'. Bot delivery is strictly restricted to paired groups (@g.us).")
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
                "mimetype": "application/pdf",
                "caption": caption,
                "fileName": doc_filename,
                "media": raw_b64,
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

