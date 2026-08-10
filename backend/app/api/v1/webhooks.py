from typing import Dict, Any
from fastapi import APIRouter, Request, status

from app.bot.whatsapp_adapter import WhatsAppAdapter

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

@router.post("/whatsapp")
async def whatsapp_webhook(request: Request):
    """Receive Evolution API WhatsApp webhooks."""
    payload: Dict[str, Any] = await request.json()
    response_text = await WhatsAppAdapter.process_webhook_payload(payload)
    return {"status": "ok", "response_sent": response_text is not None}
