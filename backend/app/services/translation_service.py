import json
import logging
import urllib.parse
import urllib.request
from typing import Tuple
from app.schemas.translation import SUPPORTED_LANGUAGES, normalize_language_code

logger = logging.getLogger(__name__)


class TranslationService:
    """
    Real-time multilingual translation service for NEST chat.
    Enables newcomers and local helpers to communicate seamlessly across language barriers
    (e.g., Hindi speaker moving to Kochi communicating with a Malayalam-speaking helper).
    """

    def translate(
        self,
        text: str,
        target_language: str,
        source_language: str = "auto",
    ) -> Tuple[str, str]:
        """
        Translate message text into target language and detect source language.
        Returns: (translated_text, detected_source_language)
        """
        if not text or not text.strip():
            return "", source_language

        target_code = normalize_language_code(target_language)
        if target_code not in SUPPORTED_LANGUAGES:
            raise ValueError(
                f"Unsupported target language '{target_language}'. Supported: {', '.join(SUPPORTED_LANGUAGES.keys())}"
            )

        source_code = "auto" if source_language == "auto" else normalize_language_code(source_language)

        # Optimization: if source and target are the same, return text as is
        if source_code != "auto" and source_code == target_code:
            return text, source_code

        try:
            encoded_query = urllib.parse.quote(text.strip())
            url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl={source_code}&tl={target_code}&dt=t&q={encoded_query}"
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "application/json",
                },
            )

            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            # Format returned by Google Translate gtx:
            # [[['translated chunk 1', 'orig chunk 1', ...], ...], None, 'detected_lang', ...]
            translated_chunks = []
            if data and isinstance(data, list) and len(data) > 0 and isinstance(data[0], list):
                for chunk in data[0]:
                    if chunk and len(chunk) > 0 and chunk[0]:
                        translated_chunks.append(chunk[0])

            translated_text = "".join(translated_chunks) if translated_chunks else text
            detected_lang = data[2] if len(data) > 2 and data[2] else source_code

            return translated_text, detected_lang

        except Exception as exc:
            logger.error(f"[TranslationService] Translation request failed: {exc}")
            raise RuntimeError(f"Translation upstream provider error: {exc}") from exc


class VoiceTranslationExtensionPoint:
    """
    Future-ready extension architecture for voice translation:
    Speech (Audio) -> STT (Speech-to-Text) -> Language Detection -> Translation -> TTS (Text-to-Speech).
    Designed to cleanly plug into Google Cloud Speech / Whisper / Web Audio API without breaking changes.
    """

    def speech_to_text(self, audio_bytes: bytes, audio_format: str = "webm") -> str:
        """Extension point for Speech-to-Text transcription."""
        raise NotImplementedError("Voice STT extension point ready for Whisper/Google Speech integration.")

    def text_to_speech(self, text: str, language_code: str) -> bytes:
        """Extension point for Text-to-Speech audio synthesis."""
        raise NotImplementedError("Voice TTS extension point ready for Google TTS integration.")


translation_service = TranslationService()
voice_translation_service = VoiceTranslationExtensionPoint()
