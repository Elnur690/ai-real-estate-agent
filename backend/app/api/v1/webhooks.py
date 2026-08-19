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


@router.post("/facebook")
async def facebook_webhook(request: Request):
    """
    Real-time webhook ingestion for Facebook Groups & Pages.
    Receives incoming Facebook real estate post payloads and immediately evaluates criteria & dispatches alerts.
    """
    from app.db.session import AsyncSessionLocal
    from app.scrapers.facebook_scraper import FacebookScraper
    from app.services.ingestion import IngestionService

    payload: Dict[str, Any] = await request.json()

    text = payload.get("text") or payload.get("message") or payload.get("content") or ""
    post_url = payload.get("post_url") or payload.get("url") or payload.get("permalink_url") or "https://facebook.com"
    post_id = str(payload.get("post_id") or payload.get("id") or hash(text[:100]))
    group_name = payload.get("group_name") or payload.get("page_name") or "Facebook"
    photos = payload.get("photos") or payload.get("images") or []

    parsed_item = FacebookScraper.parse_facebook_post_text(
        text=text,
        post_url=post_url,
        post_id=f"fb_{post_id}",
        source_name=f"Facebook ({group_name})",
        photos=photos if isinstance(photos, list) else []
    )

    if not parsed_item:
        return {"status": "ignored", "reason": "Text too short or not real estate content"}

    async with AsyncSessionLocal() as db:
        db_listing = await IngestionService._ingest_single_raw_item(db, parsed_item, source_id=1)
        if db_listing:
            delivered_count = await IngestionService._evaluate_and_deliver_matches(db, db_listing)
            return {"status": "success", "listing_id": db_listing.id, "matches_delivered": delivered_count}

    return {"status": "success", "matches_delivered": 0}
