"""Adaptateur de traduction, isolé pour faciliter le remplacement du fournisseur."""

import logging
from functools import lru_cache

from deep_translator import GoogleTranslator, MyMemoryTranslator
from langdetect import DetectorFactory, LangDetectException, detect_langs

from config import TRANSLATION_CACHE_SIZE

logger = logging.getLogger(__name__)

DetectorFactory.seed = 0

MYMEMORY_LANGUAGES = {
    "fr": "french",
    "en": "english",
    "es": "spanish",
    "de": "german",
    "it": "italian",
    "pt": "portuguese",
    "ar": "arabic",
    "zh-CN": "chinese simplified",
    "ja": "japanese",
    "ko": "korean",
    "ru": "russian",
    "tr": "turkish",
    "hi": "hindi",
    "sw": "swahili",
    "nl": "dutch",
}


class TranslationUnavailableError(RuntimeError):
    """Les fournisseurs de traduction ne peuvent pas traiter la demande."""

    def __init__(self, *, quota_exceeded: bool = False):
        self.quota_exceeded = quota_exceeded
        super().__init__("Le fournisseur de traduction de secours est indisponible.")


def _detect_language(text: str) -> str:
    if len(text.strip()) < 12:
        raise TranslationUnavailableError()
    try:
        candidates = detect_langs(text)
    except LangDetectException as error:
        raise TranslationUnavailableError() from error
    if not candidates or candidates[0].prob < 0.8:
        raise TranslationUnavailableError()
    code = candidates[0].lang
    if code == "zh":
        code = "zh-CN"
    if code not in MYMEMORY_LANGUAGES:
        raise TranslationUnavailableError()
    return code

@lru_cache(maxsize=TRANSLATION_CACHE_SIZE)
def _translate_cached(text: str, source: str, target: str) -> tuple[str, str | None]:
    try:
        return GoogleTranslator(source=source, target=target).translate(text), None
    except Exception:
        logger.exception("Google Translate indisponible (%s vers %s); essai MyMemory", source, target)

    detected_source = _detect_language(text) if source == "auto" else source
    try:
        translation = MyMemoryTranslator(
            source=MYMEMORY_LANGUAGES[detected_source],
            target=MYMEMORY_LANGUAGES[target],
        ).translate(text)
    except Exception as error:
        logger.exception("MyMemory indisponible (%s vers %s)", detected_source, target)
        from deep_translator.exceptions import TooManyRequests

        raise TranslationUnavailableError(quota_exceeded=isinstance(error, TooManyRequests)) from error
    return translation, detected_source if source == "auto" else None


def translate_text(text: str, source: str, target: str) -> tuple[str, str | None]:
    """Traduit le texte et renvoie la source connue, ou None en détection auto.

    GoogleTranslator accepte la détection automatique mais ne fournit pas le code
    effectivement détecté dans sa réponse publique. La valeur None évite d'inventer
    une langue lorsque source vaut « auto ».
    """
    try:
        return _translate_cached(text, source, target)
    except Exception:
        logger.exception("Échec du fournisseur de traduction (%s vers %s)", source, target)
        raise


def clear_translation_cache() -> None:
    """Vide le cache, notamment utile lors des tests."""
    _translate_cached.cache_clear()
