"""Application Flask de traduction vocale Talk-Translate."""

import logging
import os
import threading
import time
import uuid
from collections import defaultdict, deque
from io import BytesIO
from pathlib import Path
from typing import Any

from flask import Flask, Response, current_app, jsonify, render_template, request, send_file, session
from flask.typing import ResponseReturnValue
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.exceptions import RequestEntityTooLarge

import config
from services import storage
from services.languages import get_languages, is_supported_language
from services.translator import translate_text
from services.tts import generate_speech

logger = logging.getLogger(__name__)
_rate_lock = threading.Lock()
_rate_buckets: dict[str, deque[float]] = defaultdict(deque)


def _error(message: str, status: int) -> tuple[Response, int]:
    return jsonify({"error": message}), status


def _request_data() -> dict[str, Any] | None:
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else None


def _validate_text(text: object) -> str | None:
    if not isinstance(text, str) or not text.strip():
        return "Le texte ne peut pas être vide."
    if len(text) > current_app.config["MAX_TEXT_LENGTH"]:
        return f"Le texte ne doit pas dépasser {current_app.config['MAX_TEXT_LENGTH']} caractères."
    return None


def _database_path() -> Path:
    return Path(current_app.config["DATABASE_PATH"])


def _owner_id() -> str:
    owner_id = session.get("owner_id")
    if not isinstance(owner_id, str) or len(owner_id) != 32:
        owner_id = uuid.uuid4().hex
        session["owner_id"] = owner_id
    session.permanent = True
    return owner_id


def _rate_limit_exceeded() -> bool:
    now = time.monotonic()
    window = current_app.config["RATE_LIMIT_WINDOW_SECONDS"]
    key = f"{current_app.config['RATE_LIMIT_BUCKET_ID']}:{request.remote_addr or 'unknown'}"
    with _rate_lock:
        requests = _rate_buckets[key]
        while requests and now - requests[0] >= window:
            requests.popleft()
        if len(requests) >= current_app.config["RATE_LIMIT_REQUESTS"]:
            return True
        requests.append(now)
        if len(_rate_buckets) > 1024:
            stale = [
                address
                for address, bucket in _rate_buckets.items()
                if not bucket or now - bucket[-1] >= window
            ]
            for address in stale:
                _rate_buckets.pop(address, None)
    return False


def create_app(test_config: dict[str, Any] | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config)
    if test_config:
        app.config.update(test_config)
    if not app.config.get("SECRET_KEY"):
        app.config["SECRET_KEY"] = os.urandom(32)
    if app.config.get("TRUST_PROXY"):
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1)
    app.config["RATE_LIMIT_BUCKET_ID"] = uuid.uuid4().hex
    app.config["DATABASE_PATH"] = str(app.config["DATABASE_PATH"])
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    storage.initialize_database(app.config["DATABASE_PATH"])

    @app.before_request
    def apply_api_rate_limit() -> ResponseReturnValue | None:
        if request.path.startswith("/api/") and _rate_limit_exceeded():
            return _error("Trop de requêtes. Réessayez dans une minute.", 429)
        return None

    @app.errorhandler(RequestEntityTooLarge)
    def request_too_large(_error_value: RequestEntityTooLarge) -> ResponseReturnValue:
        return _error("La requête est trop volumineuse.", 413)

    @app.errorhandler(404)
    def not_found(_error_value: Exception) -> ResponseReturnValue:
        if request.path.startswith("/api/"):
            return _error("Ressource introuvable.", 404)
        return "Page introuvable", 404

    @app.errorhandler(405)
    def method_not_allowed(_error_value: Exception) -> ResponseReturnValue:
        if request.path.startswith("/api/"):
            return _error("Méthode non autorisée pour cette route.", 405)
        return "Méthode non autorisée.", 405

    @app.errorhandler(500)
    def internal_error(error_value: Exception) -> ResponseReturnValue:
        logger.error("Erreur interne: %s", error_value)
        if request.path.startswith("/api/"):
            return _error("Une erreur interne est survenue. Réessayez plus tard.", 500)
        return "Une erreur interne est survenue.", 500

    @app.get("/")
    def index() -> str:
        return render_template("index.html", max_text_length=app.config["MAX_TEXT_LENGTH"])

    @app.get("/api/languages")
    def languages() -> ResponseReturnValue:
        return jsonify({"languages": get_languages()})

    @app.post("/api/translate")
    def translate() -> ResponseReturnValue:
        data = _request_data()
        if data is None:
            return _error("Envoyez un objet JSON valide.", 400)
        text, source, target = data.get("text"), data.get("source"), data.get("target")
        validation_error = _validate_text(text)
        if validation_error:
            return _error(validation_error, 400)
        if not is_supported_language(source, allow_auto=True):
            return _error("La langue source est inconnue.", 400)
        if not is_supported_language(target):
            return _error("La langue cible est inconnue.", 400)
        if source == target:
            return _error("Choisissez deux langues différentes.", 400)
        try:
            owner_id = _owner_id()
            translation, detected_source = translate_text(text.strip(), source, target)
            history_id = storage.add_history(
                _database_path(),
                owner_id,
                text.strip(),
                translation,
                source,
                target,
                app.config["HISTORY_LIMIT"],
            )
        except Exception:
            logger.exception("La traduction a échoué")
            return _error("La traduction a échoué. Vérifiez votre connexion puis réessayez.", 502)
        return jsonify(
            {
                "translation": translation,
                "detected_source": detected_source,
                "history_id": history_id,
            }
        )

    @app.post("/api/tts")
    def text_to_speech() -> ResponseReturnValue:
        data = _request_data()
        if data is None:
            return _error("Envoyez un objet JSON valide.", 400)
        text, language = data.get("text"), data.get("lang")
        if not isinstance(text, str) or not text.strip():
            return _error("Le texte ne peut pas être vide.", 400)
        if len(text) > app.config["MAX_TTS_LENGTH"]:
            return _error(f"Le texte audio ne doit pas dépasser {app.config['MAX_TTS_LENGTH']} caractères.", 400)
        if not is_supported_language(language):
            return _error("La langue audio est inconnue.", 400)
        slow = data.get("slow", False)
        if not isinstance(slow, bool):
            return _error("Le paramètre slow doit être un booléen.", 400)
        try:
            audio = generate_speech(text.strip(), language, slow)
        except Exception:
            logger.exception("La synthèse vocale a échoué")
            return _error("La génération audio a échoué. Vérifiez votre connexion puis réessayez.", 502)
        return send_file(
            BytesIO(audio),
            mimetype="audio/mpeg",
            as_attachment=False,
            download_name="traduction.mp3",
            max_age=3600,
        )

    @app.get("/api/history")
    def history() -> ResponseReturnValue:
        return jsonify(
            {"history": storage.list_history(_database_path(), _owner_id(), app.config["HISTORY_LIMIT"])}
        )

    @app.delete("/api/history/<int:item_id>")
    def remove_history_item(item_id: int) -> ResponseReturnValue:
        if not storage.delete_history_item(_database_path(), _owner_id(), item_id):
            return _error("Cette entrée d'historique est introuvable.", 404)
        return jsonify({"deleted": True})

    @app.delete("/api/history")
    def remove_history() -> ResponseReturnValue:
        return jsonify({"deleted": storage.clear_history(_database_path(), _owner_id())})

    @app.get("/api/favorites")
    def favorites() -> ResponseReturnValue:
        return jsonify({"favorites": storage.list_favorites(_database_path(), _owner_id())})

    @app.post("/api/favorites")
    def save_favorite() -> ResponseReturnValue:
        data = _request_data()
        if data is None:
            return _error("Envoyez un objet JSON valide.", 400)
        text, translation = data.get("text"), data.get("translation")
        validation_error = _validate_text(text)
        if validation_error:
            return _error(validation_error, 400)
        if not isinstance(translation, str) or not translation.strip():
            return _error("La traduction ne peut pas être vide.", 400)
        if len(translation) > app.config["MAX_TEXT_LENGTH"] * 4:
            return _error("La traduction est trop longue.", 400)
        source, target = data.get("source"), data.get("target")
        if not is_supported_language(source, allow_auto=True):
            return _error("La langue source est inconnue.", 400)
        if not is_supported_language(target):
            return _error("La langue cible est inconnue.", 400)
        item_id, created = storage.add_favorite(
            _database_path(), _owner_id(), text.strip(), translation.strip(), source, target
        )
        return jsonify({"id": item_id, "created": created}), 201 if created else 200

    @app.delete("/api/favorites/<int:item_id>")
    def remove_favorite(item_id: int) -> ResponseReturnValue:
        if not storage.delete_favorite(_database_path(), _owner_id(), item_id):
            return _error("Ce favori est introuvable.", 404)
        return jsonify({"deleted": True})

    @app.delete("/api/favorites")
    def remove_favorites() -> ResponseReturnValue:
        return jsonify({"deleted": storage.clear_favorites(_database_path(), _owner_id())})

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=app.config["DEBUG"])
