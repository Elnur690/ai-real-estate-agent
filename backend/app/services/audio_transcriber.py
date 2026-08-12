import logging
import httpx
import tempfile
import os
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

class AudioTranscriberService:
    @staticmethod
    async def transcribe_audio_url(audio_url: str, headers: dict = {}) -> Optional[str]:
        """
        Download voice note audio from WhatsApp/Telegram URL and transcribe using Gemini Audio API.
        """
        if not audio_url:
            return None

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.get(audio_url, headers=headers)
                if res.status_code == 200:
                    return await AudioTranscriberService.transcribe_audio_bytes(res.content, mime_type="audio/ogg")
                else:
                    logger.error(f"[AudioTranscriber] Failed to download audio from {audio_url}: status {res.status_code}")
        except Exception as e:
            logger.error(f"[AudioTranscriber] HTTP error fetching audio: {e}")
        return None

    @staticmethod
    async def transcribe_audio_bytes(audio_bytes: bytes, mime_type: str = "audio/ogg") -> Optional[str]:
        """
        Transcribe raw audio bytes using Google Gemini Audio / GenAI API.
        """
        if not audio_bytes:
            return None

        if not settings.GEMINI_API_KEY:
            logger.warning("[AudioTranscriber] GEMINI_API_KEY not configured for voice note transcription.")
            return None

        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as tmp:
                tmp.write(audio_bytes)
                temp_path = tmp.name

            from google import genai
            client = genai.Client(api_key=settings.GEMINI_API_KEY)

            # Upload audio file to Gemini File API
            audio_file = client.files.upload(file=temp_path)

            prompt = (
                "Transcribe this real estate agent's voice message accurately. "
                "The spoken language is Azerbaijani, Russian, or English. "
                "Return ONLY the verbatim transcript text without commentary or quotation marks."
            )

            response = client.models.generate_content(
                model="gemini-1.5-flash",
                contents=[audio_file, prompt]
            )

            transcript = response.text.strip() if response and response.text else None
            logger.info(f"[AudioTranscriber] Audio transcribed successfully: '{transcript}'")
            return transcript
        except Exception as e:
            logger.error(f"[AudioTranscriber] Gemini audio transcription error: {e}", exc_info=True)
            return None
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
