import logging
import httpx
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_admin
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/whatsapp", tags=["WhatsApp Evolution API"])


class ConnectWhatsAppRequest(BaseModel):
    instance_name: Optional[str] = None
    phone_number: Optional[str] = None
    webhook_url: Optional[str] = None


class WhatsAppStatusResponse(BaseModel):
    instance_name: str
    state: str  # open | connecting | close
    connected: bool
    phone_number: Optional[str] = None


@router.get("/status", response_model=WhatsAppStatusResponse)
async def get_whatsapp_status(
    instance_name: Optional[str] = None,
    current_admin = Depends(get_current_admin)
):
    """Check connection status of Evolution API WhatsApp instance."""
    inst = instance_name or settings.EVOLUTION_INSTANCE_NAME
    if not settings.EVOLUTION_API_URL:
        return WhatsAppStatusResponse(
            instance_name=inst,
            state="disabled",
            connected=False
        )

    url = f"{settings.EVOLUTION_API_URL}/instance/connectionState/{inst}"
    headers = {"apikey": settings.EVOLUTION_API_KEY}

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
    body: ConnectWhatsAppRequest,
    current_admin = Depends(get_current_admin)
):
    """Create Evolution API instance and return base64 QR code or pairing code for WhatsApp scanning."""
    inst = body.instance_name or settings.EVOLUTION_INSTANCE_NAME
    if not settings.EVOLUTION_API_URL:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="EVOLUTION_API_URL is not configured in backend environment."
        )

    headers = {
        "apikey": settings.EVOLUTION_API_KEY,
        "Content-Type": "application/json"
    }

    # Step 1: Ensure Instance Exists
    create_url = f"{settings.EVOLUTION_API_URL}/instance/create"
    create_body = {
        "instanceName": inst,
        "qrcode": True,
        "integration": "WHATSAPP-BAILEYS"
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            await client.post(create_url, json=create_body, headers=headers)
        except Exception:
            pass  # Instance may already exist

        # Step 2: Set Webhook automatically
        webhook_target = body.webhook_url or "https://realtor-api.erma.shop/api/v1/webhooks/whatsapp"
        webhook_url = f"{settings.EVOLUTION_API_URL}/webhook/set/{inst}"
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

        # Step 3: Fetch QR Code or Pairing Code
        connect_url = f"{settings.EVOLUTION_API_URL}/instance/connect/{inst}"
        try:
            res = await client.get(connect_url, headers=headers)
            if res.status_code in [200, 201]:
                data = res.json()
                qrcode = data.get("base64") or data.get("code") or data.get("qrcode", {}).get("base64")
                pairing_code = data.get("pairingCode")
                return {
                    "instance_name": inst,
                    "status": "qr_ready",
                    "qrcode": qrcode,
                    "pairing_code": pairing_code,
                    "webhook_url": webhook_target
                }
            else:
                return {
                    "instance_name": inst,
                    "status": "already_connected_or_error",
                    "detail": res.text
                }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to connect to Evolution API: {str(e)}")


@router.post("/disconnect")
async def disconnect_whatsapp(
    body: ConnectWhatsAppRequest,
    current_admin = Depends(get_current_admin)
):
    """Disconnect/Logout a WhatsApp instance."""
    inst = body.instance_name or settings.EVOLUTION_INSTANCE_NAME
    url = f"{settings.EVOLUTION_API_URL}/instance/logout/{inst}"
    headers = {"apikey": settings.EVOLUTION_API_KEY}

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            res = await client.delete(url, headers=headers)
            return {"message": f"WhatsApp instance '{inst}' logged out successfully.", "response": res.json() if res.status_code == 200 else res.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Disconnect error: {str(e)}")
