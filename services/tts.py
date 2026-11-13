"""Génération et mise en cache des fichiers audio MP3."""

import logging
import threading
from collections import OrderedDict
from io import BytesIO

from gtts import gTTS

from config import TTS_CACHE_SIZE

logger = logging.getLogger(__name__)
_cache: OrderedDict[tuple[str, str, bool], bytes] = OrderedDict()
_cache_lock = threading.Lock()


def generate_speech(text: str, language: str, slow: bool = False) -> bytes:
    """Génère un MP3, réutilisant les octets déjà produits pour la même demande."""
    key = (text, language, slow)
    with _cache_lock:
        cached = _cache.get(key)
        if cached is not None:
            _cache.move_to_end(key)
            return cached

    try:
        audio = BytesIO()
        gTTS(text=text, lang=language, slow=slow).write_to_fp(audio)
        result = audio.getvalue()
    except Exception:
        logger.exception("Échec de la génération audio en %s", language)
        raise

    with _cache_lock:
        _cache[key] = result
        _cache.move_to_end(key)
        while len(_cache) > TTS_CACHE_SIZE:
            _cache.popitem(last=False)
    return result


def clear_audio_cache() -> None:
    """Vide le cache audio."""
    with _cache_lock:
        _cache.clear()
