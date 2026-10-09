import html
import json
import logging
import urllib.parse
from collections import OrderedDict
from typing import Optional, Tuple
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.schemas.translation import SUPPORTED_LANGUAGES, normalize_language_code

logger = logging.getLogger(__name__)


class TranslationService:
    """
    Production-grade multilingual translation service for NEST chat.
    Supports English and 10 regional Indian languages (Hindi, Malayalam, Marathi,
    Tamil, Telugu, Kannada, Bengali, Gujarati, Punjabi, Urdu) with automatic source
    language detection, connection pooling, multi-provider fallback, and LRU caching.
    """

    def __init__(self, cache_size: int = 500, timeout_seconds: float = 6.0):
        self.timeout_seconds = timeout_seconds
        self.cache_size = cache_size
        self._cache: OrderedDict[Tuple[str, str, str], Tuple[str, str]] = OrderedDict()

        # Resilient requests session with connection pooling and retry on connection resets
        self.session = requests.Session()
        retries = Retry(
            total=2,
            backoff_factor=0.3,
            status_forcelist=[500, 502, 503, 504],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(pool_connections=10, pool_maxsize=20, max_retries=retries)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
        })

    def _get_from_cache(self, text: str, source_code: str, target_code: str) -> Optional[Tuple[str, str]]:
        key = (text.strip(), source_code, target_code)
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        return None

    def _put_to_cache(self, text: str, source_code: str, target_code: str, result: Tuple[str, str]):
        key = (text.strip(), source_code, target_code)
        self._cache[key] = result
        if len(self._cache) > self.cache_size:
            self._cache.popitem(last=False)

    def _translate_gtx(self, text: str, source_code: str, target_code: str) -> Tuple[str, str]:
        encoded = urllib.parse.quote(text.strip())
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl={source_code}&tl={target_code}&dt=t&q={encoded}"
        resp = self.session.get(url, timeout=self.timeout_seconds)
        resp.raise_for_status()
        data = resp.json()
        chunks = []
        if data and isinstance(data, list) and len(data) > 0 and isinstance(data[0], list):
            for chunk in data[0]:
                if chunk and len(chunk) > 0 and chunk[0]:
                    chunks.append(chunk[0])
        translated = "".join(chunks) if chunks else text
        detected = data[2] if len(data) > 2 and data[2] else source_code
        return html.unescape(translated), detected

    def _translate_dict_chrome(self, text: str, source_code: str, target_code: str) -> Tuple[str, str]:
        encoded = urllib.parse.quote(text.strip())
        url = f"https://clients5.google.com/translate_a/t?client=dict-chrome-ex&sl={source_code}&tl={target_code}&q={encoded}"
        resp = self.session.get(url, timeout=self.timeout_seconds)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list) and len(data) > 0:
            if isinstance(data[0], list) and len(data[0]) > 0:
                return html.unescape(str(data[0][0])), source_code
            return html.unescape(str(data[0])), source_code
        raise RuntimeError("dict-chrome-ex returned invalid payload")

    def _translate_mymemory(self, text: str, source_code: str, target_code: str) -> Tuple[str, str]:
        encoded = urllib.parse.quote(text.strip())
        sl = "auto" if source_code == "auto" else source_code
        url = f"https://api.mymemory.translated.net/get?q={encoded}&langpair={sl}|{target_code}"
        resp = self.session.get(url, timeout=self.timeout_seconds)
        resp.raise_for_status()
        data = resp.json()
        res = data.get("responseData", {})
        translated = res.get("translatedText")
        if translated and translated.strip():
            return html.unescape(translated.strip()), source_code
        raise RuntimeError("MyMemory returned empty translation")

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

        # Check in-memory cache
        cached = self._get_from_cache(text, source_code, target_code)
        if cached:
            return cached

        # Provider pipeline with ordered fallbacks
        providers = [
            ("Google GTX", self._translate_gtx),
            ("Google Dict", self._translate_dict_chrome),
            ("MyMemory", self._translate_mymemory),
        ]

        last_error = None
        for provider_name, provider_fn in providers:
            try:
                translated_text, detected_lang = provider_fn(text, source_code, target_code)
                if translated_text and translated_text.strip():
                    result = (translated_text.strip(), detected_lang or source_code)
                    self._put_to_cache(text, source_code, target_code, result)
                    return result
            except Exception as exc:
                last_error = exc
                logger.warning(f"[TranslationService] Provider '{provider_name}' failed: {exc}. Trying fallback...")
                continue

        logger.error(f"[TranslationService] All translation providers failed: {last_error}")
        raise RuntimeError(f"Translation upstream providers temporarily unavailable: {last_error}") from last_error


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
