import sys
import os
import pytest

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.translation_service import TranslationService
from app.schemas.translation import SUPPORTED_LANGUAGES, normalize_language_code

def test_language_normalization():
    assert normalize_language_code("Hindi") == "hi"
    assert normalize_language_code("ml") == "ml"
    assert normalize_language_code("Malayalam") == "ml"
    assert normalize_language_code("English") == "en"
    assert normalize_language_code("mr") == "mr"

def test_empty_and_same_language():
    svc = TranslationService()
    assert svc.translate("", "hi") == ("", "auto")
    assert svc.translate("   ", "ml") == ("", "auto")
    assert svc.translate("Hello world", "en", "en") == ("Hello world", "en")

def test_unsupported_language_raises_value_error():
    svc = TranslationService()
    with pytest.raises(ValueError) as exc:
        svc.translate("Hello", "klingon")
    assert "Unsupported target language" in str(exc.value)

def test_live_translation_english_to_hindi():
    svc = TranslationService()
    text = "Hello, welcome to our neighborhood."
    translated, detected = svc.translate(text, "hi", "en")
    assert len(translated) > 0
    assert "नमस्ते" in translated or "स्वागत" in translated
    assert detected in ["en", "auto"]

def test_live_translation_hindi_to_english():
    svc = TranslationService()
    text = "नमस्ते, मुझे मदद चाहिए"
    translated, detected = svc.translate(text, "en", "auto")
    assert len(translated) > 0
    assert "help" in translated.lower() or "need" in translated.lower()
    assert detected == "hi"

def test_caching_behavior():
    svc = TranslationService()
    text = "Good morning!"
    res1 = svc.translate(text, "hi", "en")
    assert (text.strip(), "en", "hi") in svc._cache
    res2 = svc.translate(text, "hi", "en")
    assert res1 == res2

def test_fallback_when_primary_fails(monkeypatch):
    svc = TranslationService()
    # Force primary gtx to fail
    def failing_gtx(text, sl, tl):
        raise ConnectionError("Simulated GTX network failure")
    monkeypatch.setattr(svc, "_translate_gtx", failing_gtx)

    translated, detected = svc.translate("Where is the hospital?", "hi", "en")
    assert len(translated) > 0
    assert "अस्पताल" in translated or "हॉस्पिटल" in translated

def test_all_providers_failing_raises_runtime_error(monkeypatch):
    svc = TranslationService()
    def fail(*args):
        raise RuntimeError("Outage")
    monkeypatch.setattr(svc, "_translate_gtx", fail)
    monkeypatch.setattr(svc, "_translate_dict_chrome", fail)
    monkeypatch.setattr(svc, "_translate_mymemory", fail)

    with pytest.raises(RuntimeError) as exc:
        svc.translate("Hello", "hi", "en")
    assert "temporarily unavailable" in str(exc.value)

if __name__ == "__main__":
    test_language_normalization()
    test_empty_and_same_language()
    test_unsupported_language_raises_value_error()
    test_live_translation_english_to_hindi()
    test_live_translation_hindi_to_english()
    test_caching_behavior()
    class DummyMonkeyPatch:
        def setattr(self, target, name, value):
            setattr(target, name, value)

    mp = DummyMonkeyPatch()
    test_fallback_when_primary_fails(mp)
    test_all_providers_failing_raises_runtime_error(mp)
    print("All direct unit tests PASSED successfully!")
