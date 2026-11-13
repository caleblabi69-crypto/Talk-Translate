"""Catalogue des langues disponibles pour la traduction et la reconnaissance."""

from typing import TypedDict


class Language(TypedDict):
    code: str
    name: str
    recognition: str
    flag: str


LANGUAGES: tuple[Language, ...] = (
    {"code": "fr", "name": "Français", "recognition": "fr-FR", "flag": "🇫🇷"},
    {"code": "en", "name": "Anglais", "recognition": "en-US", "flag": "🇬🇧"},
    {"code": "es", "name": "Espagnol", "recognition": "es-ES", "flag": "🇪🇸"},
    {"code": "de", "name": "Allemand", "recognition": "de-DE", "flag": "🇩🇪"},
    {"code": "it", "name": "Italien", "recognition": "it-IT", "flag": "🇮🇹"},
    {"code": "pt", "name": "Portugais", "recognition": "pt-PT", "flag": "🇵🇹"},
    {"code": "ar", "name": "Arabe", "recognition": "ar-SA", "flag": "🇸🇦"},
    {"code": "zh-CN", "name": "Chinois", "recognition": "zh-CN", "flag": "🇨🇳"},
    {"code": "ja", "name": "Japonais", "recognition": "ja-JP", "flag": "🇯🇵"},
    {"code": "ko", "name": "Coréen", "recognition": "ko-KR", "flag": "🇰🇷"},
    {"code": "ru", "name": "Russe", "recognition": "ru-RU", "flag": "🇷🇺"},
    {"code": "tr", "name": "Turc", "recognition": "tr-TR", "flag": "🇹🇷"},
    {"code": "hi", "name": "Hindi", "recognition": "hi-IN", "flag": "🇮🇳"},
    {"code": "sw", "name": "Swahili", "recognition": "sw-KE", "flag": "🇰🇪"},
    {"code": "nl", "name": "Néerlandais", "recognition": "nl-NL", "flag": "🇳🇱"},
)

LANGUAGE_BY_CODE = {language["code"]: language for language in LANGUAGES}


def get_languages() -> list[Language]:
    """Retourne une copie JSON-compatible du catalogue."""
    return [dict(language) for language in LANGUAGES]


def is_supported_language(code: object, *, allow_auto: bool = False) -> bool:
    """Vérifie un code sans accepter de valeur arbitraire."""
    if not isinstance(code, str):
        return False
    if allow_auto and code == "auto":
        return True
    return code in LANGUAGE_BY_CODE


def recognition_code(code: str) -> str:
    """Retourne le code BCP 47 utilisé par SpeechRecognition."""
    return LANGUAGE_BY_CODE[code]["recognition"]
