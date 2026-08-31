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
            "You are a speech-to-text transcriber for Azerbaijani real estate voice notes. "
            "Transcribe this voice message accurately into plain text in Azerbaijani (or Russian/English if spoken). "
            "If the audio contains only silence, background noise, static, or unintelligible sounds, respond ONLY with 'NO_SPEECH'. "
            "Return ONLY the spoken words, without any explanations, formatting, markdown bullets, or quotation marks."
        )

        from google import genai
        from google.genai import types

        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        candidate_models = [
            "gemini-3.6-flash",
            "gemini-3.5-flash-lite",
            "gemini-3.5-flash",
            "gemini-3.7-flash",
            "gemini-3.5-pro"
        ]

        gen_config = types.GenerateContentConfig(
            temperature=0.0,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True) if hasattr(types, 'AutomaticFunctionCallingConfig') else None
        )

        def _is_valid_transcript(text: Optional[str]) -> bool:
            if not text:
                return False
            clean = text.strip().strip('"').strip("'")
            if not clean or clean.upper() == "NO_SPEECH":
                return False
            # Ensure it contains actual words/letters and not just random symbols or markdown bullets
            alpha_chars = sum(1 for c in clean if c.isalnum())
            if alpha_chars < 3 or (alpha_chars / max(len(clean), 1)) < 0.35:
                return False
            return True

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
                if _is_valid_transcript(transcript):
                    clean_t = transcript.strip().strip('"').strip("'")
                    logger.info(f"[AudioTranscriber] Audio transcribed successfully with {model_name} via inline bytes: '{clean_t}'")
                    return clean_t
                elif transcript:
                    logger.info(f"[AudioTranscriber] Filtered out noise/unintelligible transcript from {model_name}: '{transcript[:60]}...'")
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
                    if _is_valid_transcript(transcript):
                        clean_t = transcript.strip().strip('"').strip("'")
                        logger.info(f"[AudioTranscriber] Audio transcribed successfully with {model_name} via File API: '{clean_t}'")
                        return clean_t
                except Exception as e:
                    logger.warning(f"[AudioTranscriber] File API transcription attempt with {model_name} failed ({e}).")

            # Method 3: OpenAI Whisper fallback (if OPENAI_API_KEY configured)
            if settings.OPENAI_API_KEY and temp_path and os.path.exists(temp_path):
                try:
                    from openai import OpenAI
                    oa_client = OpenAI(api_key=settings.OPENAI_API_KEY)
                    with open(temp_path, "rb") as f_audio:
                        whisper_res = oa_client.audio.transcriptions.create(
                            model="whisper-1",
                            file=f_audio
                        )
                    if whisper_res and whisper_res.text:
                        clean_w = whisper_res.text.strip()
                        if _is_valid_transcript(clean_w):
                            logger.info(f"[AudioTranscriber] Audio transcribed successfully with OpenAI Whisper: '{clean_w}'")
                            return clean_w
                except Exception as e_w:
                    logger.warning(f"[AudioTranscriber] OpenAI Whisper fallback failed: {e_w}")

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
