"""Adaptateur de traduction, isolé pour faciliter le remplacement du fournisseur."""

import logging
from functools import lru_cache

from deep_translator import GoogleTranslator

from config import TRANSLATION_CACHE_SIZE

logger = logging.getLogger(__name__)


@lru_cache(maxsize=TRANSLATION_CACHE_SIZE)
def _translate_cached(text: str, source: str, target: str) -> str:
    return GoogleTranslator(source=source, target=target).translate(text)


def translate_text(text: str, source: str, target: str) -> tuple[str, str | None]:
    """Traduit le texte et renvoie la source connue, ou None en détection auto.

    GoogleTranslator accepte la détection automatique mais ne fournit pas le code
    effectivement détecté dans sa réponse publique. La valeur None évite d'inventer
    une langue lorsque source vaut « auto ».
    """
    try:
        translation = _translate_cached(text, source, target)
    except Exception:
        logger.exception("Échec du fournisseur de traduction (%s vers %s)", source, target)
        raise
    return translation, None if source == "auto" else source


def clear_translation_cache() -> None:
    """Vide le cache, notamment utile lors des tests."""
    _translate_cached.cache_clear()
