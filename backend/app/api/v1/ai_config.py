import time
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_admin
from app.models.ai_config import AIProviderConfig, AICallLog
from app.ai.factory import ProviderFactory, encrypt_key, decrypt_key

router = APIRouter(prefix="/ai-config", tags=["AI Provider Config"])

class SaveAIConfigRequest(BaseModel):
    task_type: str = "criteria_parsing" # criteria_parsing | listing_parsing | match_scoring
    provider: str = "gemini"            # gemini | claude | gpt
    model_name: str = "gemini-2.5-flash"
    api_key: Optional[str] = None
    tenant_id: Optional[int] = None

class TestConnectionRequest(BaseModel):
    provider: str
    model_name: str
    api_key: Optional[str] = None

@router.get("")
async def get_ai_configs(db: AsyncSession = Depends(get_db), current_admin = Depends(get_current_admin)):
    stmt = select(AIProviderConfig).order_by(AIProviderConfig.task_type)
    res = await db.execute(stmt)
    configs = res.scalars().all()

    # Mask API keys for security
    result = []
    for c in configs:
        plain_key = decrypt_key(c.api_key_encrypted) if c.api_key_encrypted else ""
        masked_key = f"{plain_key[:4]}...{plain_key[-4:]}" if len(plain_key) > 8 else ("****" if plain_key else "")
        result.append({
            "id": c.id,
            "tenant_id": c.tenant_id,
            "task_type": c.task_type,
            "provider": c.provider,
            "model_name": c.model_name,
            "api_key_masked": masked_key,
            "is_active": c.is_active,
            "updated_at": c.updated_at
        })
    return result


@router.post("")
async def save_ai_config(body: SaveAIConfigRequest, db: AsyncSession = Depends(get_db), current_admin = Depends(get_current_admin)):
    # Check if config exists for task_type and tenant_id
    stmt = select(AIProviderConfig).where(
        AIProviderConfig.task_type == body.task_type,
        AIProviderConfig.tenant_id == body.tenant_id if body.tenant_id else AIProviderConfig.tenant_id.is_(None)
    )
    res = await db.execute(stmt)
    existing = res.scalars().first()

    encrypted = encrypt_key(body.api_key) if body.api_key else (existing.api_key_encrypted if existing else None)

    if existing:
        existing.provider = body.provider
        existing.model_name = body.model_name
        if body.api_key:
            existing.api_key_encrypted = encrypted
        existing.is_active = True
        existing.updated_by = current_admin.id
        config_obj = existing
    else:
        config_obj = AIProviderConfig(
            tenant_id=body.tenant_id,
            task_type=body.task_type,
            provider=body.provider,
            model_name=body.model_name,
            api_key_encrypted=encrypted,
            is_active=True,
            updated_by=current_admin.id
        )
        db.add(config_obj)

    await db.commit()
    await db.refresh(config_obj)
    return {"status": "saved", "config_id": config_obj.id}


@router.post("/test-connection")
async def test_ai_connection(body: TestConnectionRequest, db: AsyncSession = Depends(get_db), current_admin = Depends(get_current_admin)):
    start_time = time.time()
    try:
        if body.provider.lower() == "gemini":
            from app.ai.gemini_provider import GeminiProvider
            prov = GeminiProvider(api_key=body.api_key, model_name=body.model_name)
        elif body.provider.lower() == "claude":
            from app.ai.claude_provider import ClaudeProvider
            prov = ClaudeProvider(api_key=body.api_key, model_name=body.model_name)
        else:
            from app.ai.gpt_provider import GPTProvider
            prov = GPTProvider(api_key=body.api_key, model_name=body.model_name)

        parsed = await prov.parse_search_criteria("Yasamalda 3 otaqlı mənzil")
        latency = round((time.time() - start_time) * 1000, 2)

        return {
            "success": True,
            "provider": body.provider,
            "model_name": body.model_name,
            "latency_ms": latency,
            "test_output": parsed.summary_az
        }
    except Exception as e:
        latency = round((time.time() - start_time) * 1000, 2)
        return {
            "success": False,
            "provider": body.provider,
            "model_name": body.model_name,
            "latency_ms": latency,
            "error": str(e)
        }


@router.get("/logs")
async def get_ai_call_logs(limit: int = 50, db: AsyncSession = Depends(get_db), current_admin = Depends(get_current_admin)):
    stmt = select(AICallLog).order_by(AICallLog.id.desc()).limit(limit)
    res = await db.execute(stmt)
    logs = res.scalars().all()
    return logs
