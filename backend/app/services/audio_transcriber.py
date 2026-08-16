import logging
import httpx
import tempfile
import os
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

class AudioTranscriberService:
    @staticmethod
    async def transcribe_audio_url(audio_url: str, headers: dict = {}, mime_type: str = "audio/ogg") -> Optional[str]:
        """
        Download voice note audio from WhatsApp/Telegram URL and transcribe using Gemini Audio API.
        """
        if not audio_url:
            return None

        try:
            async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
                res = await client.get(audio_url, headers=headers)
                if res.status_code == 200:
                    detected_mime = res.headers.get("Content-Type") or mime_type or "audio/ogg"
                    return await AudioTranscriberService.transcribe_audio_bytes(res.content, mime_type=detected_mime)
                else:
                    logger.error(f"[AudioTranscriber] Failed to download audio from {audio_url}: status {res.status_code}")
        except Exception as e:
            logger.error(f"[AudioTranscriber] HTTP error fetching audio: {e}")
        return None

    @staticmethod
    async def transcribe_audio_bytes(audio_bytes: bytes, mime_type: str = "audio/ogg") -> Optional[str]:
        """
        Transcribe raw audio bytes using Google Gemini Audio / GenAI API.
        Supports inline bytes transmission and File API fallback with proper MIME types.
        """
        if not audio_bytes:
            return None

        if not settings.GEMINI_API_KEY:
            logger.warning("[AudioTranscriber] GEMINI_API_KEY not configured for voice note transcription.")
            return None

        clean_mime = (mime_type or "audio/ogg").split(";")[0].strip().lower()
        if not clean_mime or "/" not in clean_mime:
            clean_mime = "audio/ogg"

        prompt = (
            "Transcribe this real estate agent's voice message accurately. "
            "The spoken language is Azerbaijani, Russian, or English. "
            "Return ONLY the verbatim transcript text without commentary or quotation marks."
        )

        from google import genai
        from google.genai import types

        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        candidate_models = ["gemini-3.5-flash", "gemini-3.6-flash", "gemini-3.7-flash"]

        gen_config = types.GenerateContentConfig(
            temperature=0.0,
        )

        # Method 1: Inline binary part (Fastest, zero temp files, no upload delay)
        for model_name in candidate_models:
            try:
                part = types.Part.from_bytes(
                    data=audio_bytes,
                    mime_type=clean_mime
                )

                response = client.models.generate_content(
                    model=model_name,
                    contents=[part, prompt],
                    config=gen_config
                )

                transcript = response.text.strip() if response and response.text else None
                if transcript:
                    logger.info(f"[AudioTranscriber] Audio transcribed successfully with {model_name} via inline bytes: '{transcript}'")
                    return transcript
            except Exception as e:
                logger.warning(f"[AudioTranscriber] Inline audio transcription attempt with {model_name} failed ({e}).")

        logger.info("[AudioTranscriber] Trying File API fallback across candidate models...")

        # Method 2: Temporary File Upload with explicit UploadFileConfig MIME type
        ext = ".ogg"
        if "mp4" in clean_mime or "m4a" in clean_mime:
            ext = ".m4a"
        elif "mp3" in clean_mime or "mpeg" in clean_mime:
            ext = ".mp3"
        elif "wav" in clean_mime:
            ext = ".wav"
        elif "aac" in clean_mime:
            ext = ".aac"

        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                tmp.write(audio_bytes)
                temp_path = tmp.name

            try:
                audio_file = client.files.upload(
                    file=temp_path,
                    config=types.UploadFileConfig(mime_type=clean_mime)
                )
            except Exception:
                audio_file = client.files.upload(file=temp_path)

            for model_name in candidate_models:
                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=[audio_file, prompt],
                        config=gen_config
                    )

                    transcript = response.text.strip() if response and response.text else None
                    if transcript:
                        logger.info(f"[AudioTranscriber] Audio transcribed successfully with {model_name} via File API: '{transcript}'")
                        return transcript
                except Exception as e:
                    logger.warning(f"[AudioTranscriber] File API transcription attempt with {model_name} failed ({e}).")
            return None
        except Exception as e:
            logger.error(f"[AudioTranscriber] Gemini audio transcription error: {e}", exc_info=True)
            return None
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
