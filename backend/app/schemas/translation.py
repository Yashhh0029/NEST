import uuid
from typing import Optional
from pydantic import BaseModel, Field

SUPPORTED_LANGUAGES = {
    "en": "English",
    "hi": "Hindi",
    "ml": "Malayalam",
    "mr": "Marathi",
    "ta": "Tamil",
    "te": "Telugu",
    "kn": "Kannada",
    "bn": "Bengali",
    "gu": "Gujarati",
    "pa": "Punjabi",
    "ur": "Urdu",
}


def normalize_language_code(lang: str) -> str:
    """Normalize language name or code to ISO 639-1 code."""
    cleaned = lang.strip().lower()
    if cleaned in SUPPORTED_LANGUAGES:
        return cleaned

    name_to_code = {v.lower(): k for k, v in SUPPORTED_LANGUAGES.items()}
    return name_to_code.get(cleaned, cleaned)


class TranslateMessageRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000, description="Message text to translate")
    target_language: str = Field(..., description="Target language code or name (e.g. 'ml', 'Malayalam', 'hi', 'Hindi')")
    source_language: Optional[str] = Field("auto", description="Source language code or 'auto'")
    message_id: Optional[uuid.UUID] = Field(None, description="Optional ID of message being translated")


class TranslateMessageResponse(BaseModel):
    original_text: str
    translated_text: str
    detected_source_language: str
    target_language: str
    message_id: Optional[uuid.UUID] = None
    provider: str = "Google Translate"
