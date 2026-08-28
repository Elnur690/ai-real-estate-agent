import time
import base64
from typing import Optional
from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.ai_config import AIProviderConfig, AICallLog
from app.ai.base import AIProvider
from app.ai.gemini_provider import GeminiProvider
from app.ai.claude_provider import ClaudeProvider
from app.ai.gpt_provider import GPTProvider

def get_fernet() -> Fernet:
    key = settings.ENCRYPTION_KEY
    # Ensure key is valid Fernet key (32 url-safe base64-encoded bytes)
    if len(key) < 32:
        key = key.ljust(32, '=')
    encoded = base64.urlsafe_b64encode(key[:32].encode())
    return Fernet(encoded)

def encrypt_key(plain_key: str) -> str:
    if not plain_key:
        return ""
    f = get_fernet()
    return f.encrypt(plain_key.encode()).decode()

def decrypt_key(encrypted_key: str) -> str:
    if not encrypted_key:
        return ""
    try:
        f = get_fernet()
        return f.decrypt(encrypted_key.encode()).decode()
    except Exception as e:
        print(f"[Crypto] Decryption failed: {e}")
        return ""

class ProviderFactory:
    @staticmethod
    async def get_provider(
        db: Optional[AsyncSession] = None,
        task_type: str = "criteria_parsing",
        tenant_id: Optional[int] = None
    ) -> AIProvider:
        """
        Config resolution order:
        1. Tenant-specific override (ai_provider_config.tenant_id == tenant_id)
        2. Global default (ai_provider_config.tenant_id IS NULL)
        3. Hard fallback: Gemini free tier / default key
        """
        config = None
        if db:
            # 1. Tenant override
            if tenant_id:
                stmt = select(AIProviderConfig).where(
                    AIProviderConfig.tenant_id == tenant_id,
                    AIProviderConfig.task_type == task_type,
                    AIProviderConfig.is_active == True
                )
                res = await db.execute(stmt)
                config = res.scalars().first()

            # 2. Global default
            if not config:
                stmt = select(AIProviderConfig).where(
                    AIProviderConfig.tenant_id.is_(None),
                    AIProviderConfig.task_type == task_type,
                    AIProviderConfig.is_active == True
                )
                res = await db.execute(stmt)
                config = res.scalars().first()

        if config:
            provider_type = config.provider.lower()
            plain_key = decrypt_key(config.api_key_encrypted) if config.api_key_encrypted else (settings.GEMINI_API_KEY or "")
            model_name = config.model_name

            if provider_type == "claude":
                return ClaudeProvider(api_key=plain_key, model_name=model_name)
            elif provider_type == "gpt":
                return GPTProvider(api_key=plain_key, model_name=model_name)
            else:
                return GeminiProvider(api_key=plain_key, model_name=model_name)

        # 3. Hard fallback
        return GeminiProvider(api_key=settings.GEMINI_API_KEY, model_name="gemini-3.5-flash")

    @staticmethod
    async def log_call(
        db: AsyncSession,
        provider: str,
        task_type: str,
        model_name: str,
        status: str,
        latency_ms: float,
        tenant_id: Optional[int] = None,
        error_message: Optional[str] = None
    ):
        try:
            log_entry = AICallLog(
                tenant_id=tenant_id,
                provider=provider,
                task_type=task_type,
                model_name=model_name,
                status=status,
                latency_ms=latency_ms,
                error_message=error_message
            )
            db.add(log_entry)
            await db.commit()
        except Exception as e:
            print(f"[ProviderFactory] Call log error: {e}")
