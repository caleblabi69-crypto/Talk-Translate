# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Voyageurs qui échangent avec une personne parlant une autre langue, notamment pendant un déplacement et sur un téléphone.

## Product Purpose

Permettre à deux personnes de se comprendre en parlant ou en saisissant du texte, avec une traduction et sa lecture audio.

## Positioning

La reconnaissance vocale est effectuée dans le navigateur, tandis qu'un mode conversation fait alterner les tours de parole entre les langues choisies.

## Operating Context

Usage ponctuel ou fréquent en déplacement, parfois sur un petit écran et avec un accès réseau variable. Le navigateur doit autoriser le microphone et fournir la Web Speech API pour la saisie vocale.

## Capabilities and Constraints

Le serveur Flask traduit avec GoogleTranslator via deep-translator, génère l'audio avec gTTS et conserve localement les 50 traductions les plus récentes et les favoris dans SQLite. Le texte saisi ou reconnu est limité à 500 caractères. Quinze langues sont prévues. La reconnaissance vocale dépend du navigateur et de son service vocal; l'audio n'est pas envoyé par l'application elle-même, mais le texte transcrit est envoyé aux fournisseurs de traduction et de synthèse vocale. Aucune clé API n'est requise. L'API GoogleTranslator ne fournit pas de code de langue source détecté, et l'application doit signaler honnêtement cette limite. Aucun compte n'est prévu; une instance publiée partage l'historique entre ses utilisateurs.

## Brand Commitments

Le nom du dépôt est Talk-Translate. L'interface et sa documentation sont en français.

## Evidence on Hand

Aucune donnée réelle, étude utilisateur ou identité de marque n'est fournie. Ne pas inventer de témoignage, de statistique ou de preuve commerciale.

## Product Principles

- Garder la prise de parole et la réponse traduite au centre de l'usage.
- Rendre les tours de parole en conversation faciles à distinguer.
- Ne jamais prétendre que le navigateur ou le fournisseur a détecté une langue si l'API ne la révèle pas.
- Expliquer clairement les erreurs de micro, réseau et traduction et proposer une autre voie.
- Conserver historique et favoris sur l'instance locale, sans envoyer la reconnaissance vocale par l'application.

## Accessibility & Inclusion

Respecter le clavier et les lecteurs d'écran avec des libellés, états annoncés et contrôles accessibles; prendre en charge le contraste WCAG AA et la préférence de réduction des animations.
