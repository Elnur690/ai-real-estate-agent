from typing import Dict, Any
from fastapi import APIRouter, Request, HTTPException, status

from app.core.config import settings
from app.bot.whatsapp_adapter import WhatsAppAdapter

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

@router.post("/whatsapp")
async def whatsapp_webhook(request: Request):
    """Receive Evolution API WhatsApp webhooks."""
    payload: Dict[str, Any] = await request.json()

    # Optional Webhook Secret Verification
    if settings.WEBHOOK_SECRET:
        token = (
            request.headers.get("X-Webhook-Secret") or
            request.headers.get("apikey") or
            request.query_params.get("secret") or
            payload.get("apikey")
        )
        valid_tokens = [settings.WEBHOOK_SECRET]
        if settings.EVOLUTION_API_KEY:
            valid_tokens.append(settings.EVOLUTION_API_KEY)

        # Allow if token is valid OR if payload comes from valid Evolution API instance
        if token and token not in valid_tokens and not payload.get("instance"):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook secret signature")

    response_text = await WhatsAppAdapter.process_webhook_payload(payload)
    return {"status": "ok", "response_sent": response_text is not None}
