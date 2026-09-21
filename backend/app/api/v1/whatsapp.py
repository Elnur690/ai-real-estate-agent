import logging
import asyncio
import httpx
from typing import Optional, Dict, Any, Tuple
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.models.user import User
from app.models.tenant import Tenant
from app.models.seller import Seller

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/whatsapp", tags=["WhatsApp Evolution API"])


class ConnectWhatsAppRequest(BaseModel):
    instance_name: Optional[str] = None
    phone_number: Optional[str] = None
    webhook_url: Optional[str] = None
    renew: Optional[bool] = False


class WhatsAppStatusResponse(BaseModel):
    instance_name: str
    state: str  # open | connecting | close | error
    connected: bool
    phone_number: Optional[str] = None


def get_evolution_headers() -> dict:
    headers = {"Content-Type": "application/json"}
    if settings.EVOLUTION_API_KEY:
        headers["apikey"] = str(settings.EVOLUTION_API_KEY)
    return headers


def get_evolution_url() -> str:
    url = settings.EVOLUTION_API_URL or "http://evolution:8080"
    # If running inside backend container and url points to localhost/127.0.0.1, convert to container hostname
    if "localhost" in url or "127.0.0.1" in url:
        return "http://evolution:8080"
    return url.rstrip("/")


async def verify_whatsapp_instance_access(
    instance_name: str,
    current_user: User,
    db: AsyncSession
) -> None:
    """Verify that current_user has permission to inspect or manage the WhatsApp instance."""
    if current_user.role == "admin":
        return

    if current_user.role == "seller":
        if not instance_name.startswith("tenant_"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Yalnız öz agentlərinizin WhatsApp bağlantısına baxa bilərsiniz."
            )
        try:
            tenant_id = int(instance_name.replace("tenant_", ""))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Yanlış WhatsApp instance identifikatoru."
            )

        # Get seller profile of current user
        s_stmt = select(Seller.id).where(Seller.user_id == current_user.id)
        s_res = await db.execute(s_stmt)
        seller_id = s_res.scalar_one_or_none()
        if not seller_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Satıcı profili tapılmadı."
            )

        # Ensure agent belongs to this seller
        t_stmt = select(Tenant.id).where(Tenant.id == tenant_id, Tenant.seller_id == seller_id)
        t_res = await db.execute(t_stmt)
        if not t_res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bu agent sizin satıcı profilinizə aid deyil."
            )
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="WhatsApp bağlantısını idarə etmək üçün icazəniz yoxdur."
    )


@router.get("/status", response_model=WhatsAppStatusResponse)
async def get_whatsapp_status(
    instance_name: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Check connection status of Evolution API WhatsApp instance."""
    inst = instance_name or settings.EVOLUTION_INSTANCE_NAME
    await verify_whatsapp_instance_access(inst, current_user, db)

    base_url = get_evolution_url()
    headers = get_evolution_headers()
    url = f"{base_url}/instance/connectionState/{inst}"

    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            res = await client.get(url, headers=headers)
            if res.status_code == 200:
                data = res.json()
                state_obj = data.get("instance", {})
                state = state_obj.get("state", "close")
                return WhatsAppStatusResponse(
                    instance_name=inst,
                    state=state,
                    connected=(state == "open"),
                    phone_number=data.get("ownerJid", "").split("@")[0] if data.get("ownerJid") else None
                )
            else:
                return WhatsAppStatusResponse(instance_name=inst, state="close", connected=False)
    except Exception as e:
        logger.error(f"[WhatsApp API] Error checking status: {e}")
        return WhatsAppStatusResponse(instance_name=inst, state="error", connected=False)


def extract_qr_and_pairing(data: Any) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Extracts (base64_qr_image, raw_pairing_string, pairing_code) from Evolution API response dict.
    Guarantees that base64_qr_image is genuinely a base64 image and NOT a raw pairing string.
    """
    if not isinstance(data, dict):
        return None, None, None

    qr_obj = data.get("qrcode")
    raw_base64 = data.get("base64")
    raw_code = data.get("code")
    pairing_code = data.get("pairingCode")

    if isinstance(qr_obj, dict):
        raw_base64 = raw_base64 or qr_obj.get("base64")
        raw_code = raw_code or qr_obj.get("code")
        pairing_code = pairing_code or qr_obj.get("pairingCode")
    elif isinstance(qr_obj, str):
        if qr_obj.startswith("data:image") or "@" not in qr_obj:
            raw_base64 = raw_base64 or qr_obj
        else:
            raw_code = raw_code or qr_obj

    formatted_base64 = None
    if raw_base64 and isinstance(raw_base64, str):
        cleaned = raw_base64.strip()
        if cleaned.startswith("data:image"):
            formatted_base64 = cleaned
        elif "@" not in cleaned and len(cleaned) > 20:
            formatted_base64 = f"data:image/png;base64,{cleaned}"

    return formatted_base64, raw_code, pairing_code


@router.post("/qrcode")
async def get_whatsapp_qrcode(
    body: Optional[ConnectWhatsAppRequest] = None,
    instance_name: Optional[str] = None,
    renew: Optional[bool] = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create or reconnect Evolution API instance and return base64 QR code or pairing code.
    Supports renewing/refreshing expired QR codes and reporting live status with reliable retry.
    """
    inst = (body.instance_name if body else None) or instance_name or settings.EVOLUTION_INSTANCE_NAME
    await verify_whatsapp_instance_access(inst, current_user, db)

    is_renew = bool((body.renew if body else False) or renew)
    base_url = get_evolution_url()
    headers = get_evolution_headers()

    qrcode = None
    raw_code = None
    pairing_code = None
    already_connected = False
    phone_number = None

    async with httpx.AsyncClient(timeout=20.0) as client:
        # Step 0: Check current state
        curr_state = "close"
        try:
            st_res = await client.get(f"{base_url}/instance/connectionState/{inst}", headers=headers)
            if st_res.status_code == 200:
                st_data = st_res.json()
                curr_state = st_data.get("instance", {}).get("state", "close")
                if curr_state == "open":
                    already_connected = True
                    phone_number = st_data.get("ownerJid", "").split("@")[0] if st_data.get("ownerJid") else None
                    if not is_renew:
                        return {
                            "instance_name": inst,
                            "status": "already_connected",
                            "connected": True,
                            "phone_number": phone_number,
                            "qrcode": None,
                            "raw_code": None,
                            "pairing_code": None,
                            "expires_in": 0,
                            "message": "WhatsApp instance is already connected."
                        }
        except Exception as e:
            logger.debug(f"[WhatsApp API] Check connection state notice: {e}")

        # If renewal requested OR if instance is stuck in stale 'close' state, restart to wake Baileys up
        needs_restart = is_renew or curr_state == "close"
        if needs_restart:
            try:
                logger.info(f"[WhatsApp API] Resetting/Restarting instance '{inst}' (renew={is_renew}, state={curr_state})...")
                r_res = await client.post(f"{base_url}/instance/restart/{inst}", headers=headers)
                if r_res.status_code not in [200, 201]:
                    await client.delete(f"{base_url}/instance/logout/{inst}", headers=headers)
            except Exception as e:
                logger.warning(f"[WhatsApp API] Restart/logout notice during renew: {e}")

        # Step 1: Ensure Instance Exists or Create it
        create_url = f"{base_url}/instance/create"
        create_body = {
            "instanceName": inst,
            "token": str(settings.EVOLUTION_API_KEY or "42960a4e6597e231787c5e0124a06248"),
            "qrcode": True,
            "integration": "WHATSAPP-BAILEYS"
        }

        try:
            res_c = await client.post(create_url, json=create_body, headers=headers)
            logger.info(f"[WhatsApp API] Instance create status: {res_c.status_code}")
            if res_c.status_code in [200, 201]:
                c_data = res_c.json()
                qrcode, raw_code, pairing_code = extract_qr_and_pairing(c_data)
        except Exception as e:
            logger.warning(f"[WhatsApp API] Instance creation check notice: {e}")

        # Step 2: Set Webhook automatically
        default_wh = f"{settings.PUBLIC_BASE_URL.rstrip('/')}/api/v1/webhooks/whatsapp"
        webhook_target = (body.webhook_url if body else None) or default_wh
        webhook_url = f"{base_url}/webhook/set/{inst}"
        webhook_body = {
            "webhook": {
                "enabled": True,
                "url": webhook_target,
                "byEvents": False,
                "events": ["MESSAGES_UPSERT", "QRCODE_UPDATED", "CONNECTION_UPDATE"]
            }
        }
        try:
            await client.post(webhook_url, json=webhook_body, headers=headers)
        except Exception as e:
            logger.warning(f"[WhatsApp API] Could not set webhook: {e}")

        # Step 3: Fetch QR Code with asynchronous retry loop to eliminate race condition
        connect_url = f"{base_url}/instance/connect/{inst}"
        if not qrcode and not raw_code:
            # Baileys takes 1-2.5s after restart to establish WhatsApp Web socket & emit the QR code
            max_attempts = 4
            for attempt in range(max_attempts):
                try:
                    res = await client.get(connect_url, headers=headers)
                    if res.status_code in [200, 201]:
                        data = res.json()
                        if isinstance(data, dict):
                            # If connection completed in background
                            if data.get("instance", {}).get("state") == "open":
                                already_connected = True
                                phone_number = data.get("ownerJid", "").split("@")[0] if data.get("ownerJid") else None
                                break

                            b64, r_code, p_code = extract_qr_and_pairing(data)
                            if b64:
                                qrcode = b64
                                raw_code = r_code
                                pairing_code = p_code or pairing_code
                                break
                            elif r_code:
                                raw_code = r_code
                                pairing_code = p_code or pairing_code
                                break
                    elif res.status_code == 404:
                        # Instance might still be registering
                        pass
                except Exception as e:
                    logger.debug(f"[WhatsApp API] Connection polling attempt {attempt + 1} notice: {e}")

                if attempt < max_attempts - 1:
                    await asyncio.sleep(1.0)

        is_ready = bool(qrcode or raw_code)
        return {
            "instance_name": inst,
            "status": "qr_ready" if is_ready else ("already_connected" if already_connected else "initializing"),
            "connected": already_connected,
            "phone_number": phone_number,
            "qrcode": qrcode,
            "raw_code": raw_code,
            "pairing_code": pairing_code,
            "expires_in": 45 if is_ready else 0,
            "webhook_url": webhook_target
        }



@router.post("/disconnect")
async def disconnect_whatsapp(
    body: ConnectWhatsAppRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Disconnect/Logout a WhatsApp instance."""
    inst = body.instance_name or settings.EVOLUTION_INSTANCE_NAME
    await verify_whatsapp_instance_access(inst, current_user, db)

    base_url = get_evolution_url()
    headers = get_evolution_headers()
    url = f"{base_url}/instance/logout/{inst}"

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            res = await client.delete(url, headers=headers)
            return {
                "message": f"WhatsApp instance '{inst}' logged out successfully.",
                "response": res.json() if res.status_code == 200 else res.text
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Disconnect error: {str(e)}")
