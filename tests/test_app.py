"""Tests API ciblés sans dépendance au réseau."""

import sqlite3

import pytest

import app as app_module
from services import storage, translator, tts


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(app_module, "translate_text", lambda text, source, target: (f"{text} ({target})", None if source == "auto" else source))
    monkeypatch.setattr(app_module, "generate_speech", lambda text, language, slow=False: b"fake-mp3")
    application = app_module.create_app(
        {
            "TESTING": True,
            "DATABASE_PATH": tmp_path / "test.sqlite3",
            "RATE_LIMIT_REQUESTS": 1000,
        }
    )
    return application.test_client()


def test_home_and_language_catalog(client):
    home = client.get("/")
    assert home.status_code == 200
    assert b"/static/js/app.js?v=" in home.data
    assert b"/static/js/speech.js?v=" in home.data
    assert b"/static/css/style.css?v=" in home.data
    response = client.get("/api/languages")
    assert response.status_code == 200
    languages = response.get_json()["languages"]
    assert len(languages) >= 15
    french = next(language for language in languages if language["code"] == "fr")
    assert french["recognition"] == "fr-FR"


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"text": "", "source": "fr", "target": "en"}, "vide"),
        ({"text": "x" * 501, "source": "fr", "target": "en"}, "500"),
        ({"text": "Bonjour", "source": "xx", "target": "en"}, "source"),
        ({"text": "Bonjour", "source": "fr", "target": "xx"}, "cible"),
        ({"text": "Bonjour", "source": "fr", "target": "fr"}, "différentes"),
    ],
)
def test_translate_validation(client, payload, message):
    response = client.post("/api/translate", json=payload)
    assert response.status_code == 400
    assert message in response.get_json()["error"]


def test_translation_adds_to_history(client):
    response = client.post("/api/translate", json={"text": "Bonjour", "source": "auto", "target": "en"})
    assert response.status_code == 200
    assert response.get_json() == {
        "translation": "Bonjour (en)",
        "detected_source": None,
        "history_id": 1,
    }
    history = client.get("/api/history").get_json()["history"]
    assert len(history) == 1
    assert history[0]["text"] == "Bonjour"


def test_local_source_detection_for_browser_fallback(client):
    response = client.post(
        "/api/languages/detect",
        json={"text": "Bonjour, comment allez-vous aujourd’hui ?"},
    )
    assert response.status_code == 200
    assert response.get_json() == {"detected_source": "fr"}
    ambiguous = client.post("/api/languages/detect", json={"text": "Hola"})
    assert ambiguous.status_code == 400


def test_browser_fallback_can_persist_translation_in_history(client):
    response = client.post(
        "/api/history",
        json={
            "text": "Bonjour",
            "translation": "Hello",
            "source": "fr",
            "target": "en",
        },
    )
    assert response.status_code == 201
    history = client.get("/api/history").get_json()["history"]
    assert history[0]["id"] == response.get_json()["history_id"]
    assert history[0]["translation"] == "Hello"


def test_history_deletion(client):
    item_id = client.post(
        "/api/translate", json={"text": "Bonjour", "source": "fr", "target": "en"}
    ).get_json()["history_id"]
    assert client.delete(f"/api/history/{item_id}").get_json() == {"deleted": True}
    assert client.delete("/api/history/999").status_code == 404
    assert client.get("/api/history").get_json()["history"] == []


def test_favorites_add_idempotently_and_delete(client):
    payload = {
        "text": "Bonjour",
        "translation": "Hello",
        "source": "fr",
        "target": "en",
    }
    first = client.post("/api/favorites", json=payload)
    second = client.post("/api/favorites", json=payload)
    assert first.status_code == 201
    assert second.status_code == 200
    assert first.get_json()["id"] == second.get_json()["id"]
    assert client.get("/api/favorites").get_json()["favorites"][0]["translation"] == "Hello"
    assert client.delete(f"/api/favorites/{first.get_json()['id']}").get_json() == {"deleted": True}


def test_tts_returns_mp3_and_validates_language(client):
    response = client.post("/api/tts", json={"text": "Hello", "lang": "en", "slow": True})
    assert response.status_code == 200
    assert response.mimetype == "audio/mpeg"
    assert response.data == b"fake-mp3"
    invalid = client.post("/api/tts", json={"text": "Hello", "lang": "nope"})
    assert invalid.status_code == 400
    long_audio = client.post("/api/tts", json={"text": "x" * 501, "lang": "en"})
    assert long_audio.status_code == 200


def test_history_is_limited_and_can_be_cleared(tmp_path, monkeypatch):
    monkeypatch.setattr(app_module, "translate_text", lambda text, source, target: (text, source))
    limited_history = app_module.create_app(
        {
            "TESTING": True,
            "DATABASE_PATH": tmp_path / "short-history.sqlite3",
            "HISTORY_LIMIT": 3,
            "RATE_LIMIT_REQUESTS": 1000,
        }
    ).test_client()
    for index in range(5):
        response = limited_history.post(
            "/api/translate",
            json={"text": f"message {index}", "source": "fr", "target": "en"},
        )
        assert response.status_code == 200
    history = limited_history.get("/api/history").get_json()["history"]
    assert [item["text"] for item in history] == ["message 4", "message 3", "message 2"]
    assert limited_history.delete("/api/history").get_json()["deleted"] == 3


def test_favorites_can_be_cleared(client):
    client.post(
        "/api/favorites",
        json={"text": "Bonjour", "translation": "Hello", "source": "fr", "target": "en"},
    )
    assert client.delete("/api/favorites").get_json()["deleted"] == 1
    assert client.get("/api/favorites").get_json()["favorites"] == []


def test_history_and_favorites_are_isolated_between_browsers(client):
    other_browser = client.application.test_client()
    history_id = client.post(
        "/api/translate", json={"text": "Bonjour", "source": "fr", "target": "en"}
    ).get_json()["history_id"]
    assert other_browser.get("/api/history").get_json()["history"] == []
    assert other_browser.delete(f"/api/history/{history_id}").status_code == 404
    other_history_id = other_browser.post(
        "/api/translate", json={"text": "Good morning", "source": "en", "target": "fr"}
    ).get_json()["history_id"]
    assert client.delete("/api/history").get_json()["deleted"] == 1
    assert other_browser.get("/api/history").get_json()["history"][0]["id"] == other_history_id

    favorite = {
        "text": "Bonjour",
        "translation": "Hello",
        "source": "fr",
        "target": "en",
    }
    first = client.post("/api/favorites", json=favorite)
    second = other_browser.post("/api/favorites", json=favorite)
    assert first.status_code == second.status_code == 201
    assert first.get_json()["id"] != second.get_json()["id"]
    assert client.get("/api/favorites").get_json()["favorites"][0]["id"] == first.get_json()["id"]
    assert other_browser.get("/api/favorites").get_json()["favorites"][0]["id"] == second.get_json()["id"]
    assert other_browser.delete(f"/api/favorites/{first.get_json()['id']}").status_code == 404
    assert client.delete("/api/favorites").get_json()["deleted"] == 1
    assert other_browser.get("/api/favorites").get_json()["favorites"][0]["id"] == second.get_json()["id"]


def test_existing_database_records_are_kept_in_an_unassigned_partition(tmp_path):
    database = tmp_path / "legacy.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.executescript(
            """
            CREATE TABLE history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                translation TEXT NOT NULL,
                source TEXT NOT NULL,
                target TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            INSERT INTO history(text, translation, source, target, created_at)
            VALUES ('Bonjour', 'Hello', 'fr', 'en', '2026-01-01T00:00:00+00:00');
            CREATE TABLE favorites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                translation TEXT NOT NULL,
                source TEXT NOT NULL,
                target TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(text, translation, source, target)
            );
            INSERT INTO favorites(text, translation, source, target, created_at)
            VALUES ('Bonjour', 'Hello', 'fr', 'en', '2026-01-01T00:00:00+00:00');
            """
        )

    storage.initialize_database(database)
    assert storage.list_history(database, "new-browser", 50) == []
    assert storage.list_favorites(database, "new-browser") == []
    assert storage.list_history(database, "legacy-unassigned", 50)[0]["text"] == "Bonjour"
    assert storage.list_favorites(database, "legacy-unassigned")[0]["translation"] == "Hello"
    new_id, created = storage.add_favorite(
        database, "new-browser", "Bonjour", "Hello", "fr", "en"
    )
    assert created is True
    assert new_id != 1


def test_invalid_json_has_a_clear_error(client):
    response = client.post("/api/translate", data="invalid", content_type="text/plain")
    assert response.status_code == 400
    assert response.get_json() == {"error": "Envoyez un objet JSON valide."}


def test_api_wrong_method_uses_json_error(client):
    response = client.put("/api/history")
    assert response.status_code == 405
    assert response.get_json() == {"error": "Méthode non autorisée pour cette route."}


def test_api_rate_limit(client, tmp_path, monkeypatch):
    limited = app_module.create_app(
        {
            "TESTING": True,
            "DATABASE_PATH": tmp_path / "limited.sqlite3",
            "RATE_LIMIT_REQUESTS": 1,
        }
    ).test_client()
    assert limited.get("/api/languages").status_code == 200
    response = limited.get("/api/languages")
    assert response.status_code == 429
    assert "error" in response.get_json()


def test_translation_service_caches_results(monkeypatch):
    calls = []

    class FakeTranslator:
        def __init__(self, source, target):
            calls.append((source, target))

        def translate(self, text):
            return f"{text} translated"

    monkeypatch.setattr(translator, "GoogleTranslator", FakeTranslator)
    translator.clear_translation_cache()
    try:
        assert translator.translate_text("hello", "en", "fr")[0] == "hello translated"
        assert translator.translate_text("hello", "en", "fr")[0] == "hello translated"
        assert calls == [("en", "fr")]
    finally:
        translator.clear_translation_cache()


def test_translation_uses_mymemory_when_google_is_unavailable(monkeypatch):
    calls = []

    class FailedGoogleTranslator:
        def __init__(self, source, target):
            pass

        def translate(self, text):
            raise RuntimeError("Google unavailable")

    class FakeMyMemoryTranslator:
        def __init__(self, source, target):
            calls.append((source, target))

        def translate(self, text):
            return "Hello, how are you?"

    monkeypatch.setattr(translator, "GoogleTranslator", FailedGoogleTranslator)
    monkeypatch.setattr(translator, "MyMemoryTranslator", FakeMyMemoryTranslator)
    translator.clear_translation_cache()
    try:
        result = translator.translate_text(
            "Bonjour, comment allez-vous ?", "auto", "en"
        )
        assert result == ("Hello, how are you?", "fr")
        assert calls == [("french", "english")]
    finally:
        translator.clear_translation_cache()


def test_mymemory_fallback_requests_manual_source_for_ambiguous_short_text(monkeypatch):
    class FailedGoogleTranslator:
        def __init__(self, source, target):
            pass

        def translate(self, text):
            raise RuntimeError("Google unavailable")

    class UnusedMyMemoryTranslator:
        def __init__(self, source, target):
            raise AssertionError("A source should be detected before contacting MyMemory")

    monkeypatch.setattr(translator, "GoogleTranslator", FailedGoogleTranslator)
    monkeypatch.setattr(translator, "MyMemoryTranslator", UnusedMyMemoryTranslator)
    translator.clear_translation_cache()
    try:
        with pytest.raises(translator.TranslationUnavailableError):
            translator.translate_text("Hola", "auto", "en")
    finally:
        translator.clear_translation_cache()


def test_audio_service_caches_mp3(monkeypatch):
    calls = []

    class FakeTTS:
        def __init__(self, text, lang, slow):
            calls.append((text, lang, slow))

        def write_to_fp(self, output):
            output.write(b"fake-mp3")

    monkeypatch.setattr(tts, "gTTS", FakeTTS)
    tts.clear_audio_cache()
    try:
        assert tts.generate_speech("hello", "en") == b"fake-mp3"
        assert tts.generate_speech("hello", "en") == b"fake-mp3"
        assert calls == [("hello", "en", False)]
    finally:
        tts.clear_audio_cache()
