# Talk Translate

Application web de traduction vocale conçue pour aider les voyageurs à échanger en face à face. Parlez dans le navigateur ou saisissez un texte, écoutez la traduction et utilisez le mode conversation pour alterner les tours de parole. Le serveur Flask utilise `deep-translator` (Google Translate sans clé API), `gTTS` pour produire les MP3 et SQLite pour l'historique et les favoris.

## Fonctionnalités

- 15 langues disponibles : français, anglais, espagnol, allemand, italien, portugais, arabe, chinois, japonais, coréen, russe, turc, hindi, swahili et néerlandais.
- Reconnaissance vocale via la Web Speech API du navigateur, sans téléversement audio par l'application.
- Traduction à la fin de la reconnaissance, à la demande, avec `Ctrl+Entrée` ou après 500 ms de pause pendant la saisie.
- Mode conversation avec deux tours de parole qui alternent automatiquement entre les langues choisies.
- Lecture audio normale ou lente, pause/reprise et arrêt.
- Copie, partage, favoris et historique local des 50 dernières traductions.
- Thème clair/sombre suivant les préférences système, avec bascule mémorisée dans le navigateur.
- Limitation en mémoire à 60 appels API par minute et par adresse IP.

## Installation locale

Python 3.10 ou plus récent est requis.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Sur macOS ou Linux :

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Ouvrez <http://127.0.0.1:5000>. Le serveur écoute sur `0.0.0.0` pour les essais sur le réseau local; configurez `PORT` pour changer le port. `FLASK_DEBUG=1` active le mode debug, à réserver au développement. SQLite crée `instance/talk_translate.sqlite3` automatiquement. `TALK_TRANSLATE_DATABASE` permet de choisir un autre chemin de base de données.

## Reconnaissance vocale et confidentialité

La reconnaissance se fait dans le navigateur via Web Speech API. La prise en charge, les langues offertes et le traitement audio varient selon le navigateur et son service vocal; Chrome et Edge sont généralement les mieux équipés. L'application n'enregistre ni n'envoie le flux audio elle-même, mais le navigateur peut transmettre l'audio à son propre service de reconnaissance. Le texte transcrit est envoyé au serveur Flask puis à GoogleTranslator pour traduction; le texte traduit est envoyé à gTTS pour produire l'audio. L'historique et les favoris sont conservés dans le fichier SQLite de l'instance.

Il n'y a pas de compte : chaque navigateur reçoit un identifiant aléatoire conservé dans un cookie signé, HttpOnly et isolé de ceux des autres navigateurs. Historique et favoris sont séparés entre navigateurs, mais restent enregistrés sur le serveur; effacer les cookies du navigateur fait perdre l'accès à ses anciennes entrées. N'utilisez pas une instance publique pour des conversations sensibles.

Le navigateur exige une permission micro et un contexte sécurisé. `localhost` est autorisé pour les essais sur l'ordinateur. Sur un téléphone, une adresse IP locale en HTTP ne garantit pas l'accès au micro : testez la saisie texte sur le réseau local ou utilisez une adresse HTTPS (par exemple l'URL HTTPS d'un déploiement Render).

## API JSON

Les erreurs ont le format `{ "error": "message explicite" }`. Les codes de langue doivent appartenir au catalogue ci-dessus. Les champs texte d'entrée et favoris sont limités à 500 caractères; la synthèse vocale accepte jusqu'à 2 000 caractères pour accommoder les traductions plus longues.

| Méthode | Route | Entrée / résultat |
|---|---|---|
| `GET` | `/` | Interface principale |
| `GET` | `/api/languages` | `{ "languages": [...] }` |
| `POST` | `/api/translate` | `{ "text": "...", "source": "fr" ou "auto", "target": "en" }` → traduction, langue détectée (ou `null`), ID d'historique |
| `POST` | `/api/tts` | `{ "text": "...", "lang": "en", "slow": false }` → audio `audio/mpeg` |
| `GET` | `/api/history` | Les 50 traductions les plus récentes |
| `DELETE` | `/api/history` | Efface tout l'historique |
| `DELETE` | `/api/history/<id>` | Efface une entrée |
| `GET` | `/api/favorites` | Liste les favoris |
| `POST` | `/api/favorites` | `{ "text": "...", "translation": "...", "source": "fr", "target": "en" }` |
| `DELETE` | `/api/favorites` | Efface tous les favoris |
| `DELETE` | `/api/favorites/<id>` | Efface un favori |

Quand la source est `auto`, `detected_source` vaut `null` : l'API publique de GoogleTranslator n'expose pas le code de langue effectivement détecté. L'application n'invente donc pas cette information.

## Tests

Les appels aux services de traduction et de synthèse vocale sont simulés dans les tests pour ne pas dépendre du réseau :

```bash
python -m pytest
```

## Déploiement gratuit

### Render

Le dépôt contient `render.yaml` pour créer automatiquement le Web Service. Dans Render, choisissez **New > Blueprint**, connectez le dépôt GitHub et sélectionnez la branche `caleblabi69-crypto-traduction-vocale`. Le Blueprint génère la clé de signature des cookies et configure HTTPS; Render fournit ensuite une URL publique `https://…onrender.com`. Le service utilise `gunicorn` et écoute sur le port fourni par Render.

Le niveau gratuit peut s'endormir et son système de fichiers est éphémère : les historiques SQLite peuvent être perdus lors d'un redémarrage ou redéploiement. Pour garder ces données durablement, utilisez un stockage persistant ou une base adaptée et configurez `TALK_TRANSLATE_DATABASE`. Le service de traduction et gTTS ont besoin d'un accès réseau sortant.

### PythonAnywhere

Créez une application Web Flask et un environnement virtuel Python 3.10+. Installez les paquets avec `pip install -r requirements.txt`, puis configurez le fichier WSGI pour ajouter le dossier du projet à `sys.path` et importer `app` depuis `app.py`. Définissez `TALK_TRANSLATE_DATABASE` vers un chemin inscriptible et persistant.

## Remplacer GoogleTranslator

Le fournisseur se trouve dans `services/translator.py`. Remplacez l'appel dans `_translate_cached` par l'adaptateur de votre choix en conservant `translate_text(text, source, target) -> (translation, detected_source)`. Le cache en mémoire évite de répéter les mêmes appels; `clear_translation_cache()` le vide, notamment pour les tests. `services/tts.py` applique le même principe au MP3.
