from typing import Dict, Any
from fastapi import APIRouter, Request, HTTPException, status

from app.core.config import settings
from app.bot.whatsapp_adapter import WhatsAppAdapter

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

@router.post("/whatsapp")
async def whatsapp_webhook(request: Request):
    """Receive Evolution API WhatsApp webhooks."""
    if settings.WEBHOOK_SECRET:
        token = request.headers.get("X-Webhook-Secret") or request.query_params.get("secret")
        if token != settings.WEBHOOK_SECRET:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook secret signature")

    payload: Dict[str, Any] = await request.json()
    response_text = await WhatsAppAdapter.process_webhook_payload(payload)
    return {"status": "ok", "response_sent": response_text is not None}
