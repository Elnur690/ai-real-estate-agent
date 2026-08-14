import logging
import httpx
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.api.deps import get_current_admin
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/whatsapp", tags=["WhatsApp Evolution API"])


class ConnectWhatsAppRequest(BaseModel):
    instance_name: Optional[str] = None
    phone_number: Optional[str] = None
    webhook_url: Optional[str] = None


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


@router.get("/status", response_model=WhatsAppStatusResponse)
async def get_whatsapp_status(
    instance_name: Optional[str] = None,
    current_admin = Depends(get_current_admin)
):
    """Check connection status of Evolution API WhatsApp instance."""
    inst = instance_name or settings.EVOLUTION_INSTANCE_NAME
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


@router.post("/qrcode")
async def get_whatsapp_qrcode(
    body: Optional[ConnectWhatsAppRequest] = None,
    instance_name: Optional[str] = None,
    current_admin = Depends(get_current_admin)
):
    """Create Evolution API instance and return base64 QR code or pairing code for WhatsApp scanning."""
    inst = (body.instance_name if body else None) or instance_name or settings.EVOLUTION_INSTANCE_NAME
    base_url = get_evolution_url()
    headers = get_evolution_headers()

    qrcode = None
    pairing_code = None

    # Step 1: Ensure Instance Exists or Create it
    create_url = f"{base_url}/instance/create"
    create_body = {
        "instanceName": inst,
        "token": str(settings.EVOLUTION_API_KEY or "42960a4e6597e231787c5e0124a06248"),
        "qrcode": True,
        "integration": "WHATSAPP-BAILEYS"
    }

    async with httpx.AsyncClient(timeout=12.0) as client:
        try:
            res_c = await client.post(create_url, json=create_body, headers=headers)
            logger.info(f"[WhatsApp API] Instance create status: {res_c.status_code}")
            if res_c.status_code in [200, 201]:
                c_data = res_c.json()
                if isinstance(c_data, dict):
                    qrcode = c_data.get("qrcode", {}).get("base64") if isinstance(c_data.get("qrcode"), dict) else c_data.get("base64")
                    pairing_code = c_data.get("pairingCode")
        except Exception as e:
            logger.warning(f"[WhatsApp API] Instance creation check notice: {e}")

        # Step 2: Set Webhook automatically
        webhook_target = (body.webhook_url if body else None) or "https://realtor-api.erma.shop/api/v1/webhooks/whatsapp"
        webhook_url = f"{base_url}/webhook/set/{inst}"
        webhook_body = {
            "webhook": {
                "enabled": True,
                "url": webhook_target,
                "byEvents": False,
                "events": ["MESSAGES_UPSERT"]
            }
        }
        try:
            await client.post(webhook_url, json=webhook_body, headers=headers)
        except Exception as e:
            logger.warning(f"[WhatsApp API] Could not set webhook: {e}")

        # Step 3: Fetch QR Code or Connection Details if not already returned in create
        if not qrcode:
            connect_url = f"{base_url}/instance/connect/{inst}"
            try:
                res = await client.get(connect_url, headers=headers)
                if res.status_code in [200, 201]:
                    data = res.json()
                    if isinstance(data, dict):
                        qrcode = data.get("base64") or data.get("code") or (data.get("qrcode", {}).get("base64") if isinstance(data.get("qrcode"), dict) else data.get("qrcode"))
                        pairing_code = data.get("pairingCode") or pairing_code
                else:
                    logger.warning(f"[WhatsApp API] Connect endpoint returned {res.status_code}: {res.text}")
            except Exception as e:
                logger.error(f"[WhatsApp API] Connection error: {e}")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Evolution API is unreachable. Please verify container 'realestate_evolution' is running. Error: {str(e)}"
                )

        # Normalize QR code base64 format for frontend rendering
        if qrcode and isinstance(qrcode, str):
            if not qrcode.startswith("data:image"):
                qrcode = f"data:image/png;base64,{qrcode}"

        return {
            "instance_name": inst,
            "status": "qr_ready" if qrcode else "initializing",
            "qrcode": qrcode,
            "pairing_code": pairing_code,
            "webhook_url": webhook_target
        }


@router.post("/disconnect")
async def disconnect_whatsapp(
    body: ConnectWhatsAppRequest,
    current_admin = Depends(get_current_admin)
):
    """Disconnect/Logout a WhatsApp instance."""
    inst = body.instance_name or settings.EVOLUTION_INSTANCE_NAME
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
