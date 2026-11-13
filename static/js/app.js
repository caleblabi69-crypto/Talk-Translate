(function () {
  "use strict";

  const $ = (selector) => document.querySelector(selector);
  const elements = {
    source: $("#source-language"),
    target: $("#target-language"),
    sourceFlag: $("#source-flag"),
    targetFlag: $("#target-flag"),
    sourceText: $("#source-text"),
    charCount: $("#char-count"),
    clearText: $("#clear-text"),
    translateButton: $("#translate-button"),
    mic: $("#microphone"),
    voiceStatus: $("#voice-status"),
    speechPreview: $("#speech-preview"),
    error: $("#error-message"),
    translationCard: $("#translation-card"),
    translationText: $("#translation-text"),
    detected: $("#detected-label"),
    translationLanguages: $("#translation-languages"),
    audioStatus: $("#audio-status"),
    favorite: $("#favorite-button"),
    historyPanel: $("#history-panel"),
    panelList: $("#panel-list"),
    backdrop: $("#panel-backdrop"),
    clearList: $("#clear-list"),
    historyTab: $("#history-tab"),
    favoritesTab: $("#favorites-tab"),
    conversationPanel: $("#conversation-panel")
  };
  const state = {
    languages: [],
    translation: "",
    translationSource: null,
    translationTarget: null,
    currentHistoryId: null,
    currentFavoriteId: null,
    debounce: null,
    audio: null,
    audioUrl: null,
    audioRequest: 0,
    busy: false,
    panelMode: "history",
    conversation: false,
    conversationSide: "source",
    conversationStarting: false,
    translationRequest: 0
  };

  function showError(message) {
    elements.error.textContent = message;
    elements.error.hidden = false;
  }

  function clearError() {
    elements.error.hidden = true;
    elements.error.textContent = "";
  }

  async function request(url, options) {
    let response;
    try {
      response = await fetch(url, options);
    } catch (_error) {
      throw new Error("Connexion impossible. Vérifiez votre réseau puis réessayez.");
    }
    if (!response.ok) {
      let message = "Une erreur est survenue.";
      try {
        const payload = await response.json();
        if (payload.error) message = payload.error;
      } catch (_error) {
        message = "Le serveur a renvoyé une réponse illisible.";
      }
      throw new Error(message);
    }
    return response;
  }

  async function jsonRequest(url, method, data) {
    const response = await request(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: data === undefined ? undefined : JSON.stringify(data)
    });
    return response.json();
  }

  function language(code) {
    return state.languages.find((item) => item.code === code);
  }

  function languageName(code) {
    if (code === "auto") return "Détection auto";
    return language(code)?.name || code;
  }

  function updateLanguageDisplay() {
    elements.sourceFlag.textContent = language(elements.source.value)?.flag || "✨";
    elements.targetFlag.textContent = language(elements.target.value)?.flag || "🇬🇧";
    $("#conversation-source-name").textContent = languageName(elements.source.value === "auto" ? "fr" : elements.source.value);
    $("#conversation-target-name").textContent = languageName(elements.target.value);
  }

  async function loadLanguages() {
    const result = await jsonRequest("/api/languages", "GET");
    state.languages = result.languages;
    result.languages.forEach((item) => {
      elements.target.add(new Option(item.name, item.code));
      elements.source.add(new Option(item.name, item.code));
    });
    elements.target.value = "en";
    updateLanguageDisplay();
  }

  function updateTextMeta() {
    const maxLength = Number(elements.sourceText.maxLength);
    elements.charCount.textContent = `${elements.sourceText.value.length} / ${maxLength}`;
    elements.clearText.disabled = elements.sourceText.value.length === 0;
    elements.translateButton.disabled = elements.sourceText.value.trim().length === 0;
  }

  function setMicState(status, message) {
    elements.mic.classList.toggle("is-listening", status === "listening");
    elements.mic.classList.toggle("is-processing", status === "processing");
    elements.mic.setAttribute("aria-pressed", status === "listening" ? "true" : "false");
    elements.mic.setAttribute("aria-busy", status === "processing" ? "true" : "false");
    elements.mic.setAttribute(
      "aria-label",
      status === "listening" ? "Arrêter la reconnaissance vocale" : "Démarrer la reconnaissance vocale"
    );
    elements.voiceStatus.textContent = message;
  }

  function speechError(code) {
    const messages = {
      unsupported: "La reconnaissance vocale n’est pas disponible dans ce navigateur. Essayez Chrome ou Edge, ou saisissez votre texte.",
      "not-allowed": "L’accès au microphone est bloqué. Autorisez-le dans les réglages de votre navigateur.",
      "service-not-allowed": "Le service de reconnaissance vocale n’est pas autorisé par le navigateur.",
      "no-speech": "Aucune parole détectée. Réessayez en parlant un peu plus près du micro.",
      "audio-capture": "Aucun microphone n’a été trouvé sur cet appareil.",
      network: "Le service de reconnaissance vocale est indisponible sur le réseau. Vous pouvez saisir votre texte.",
      aborted: "Écoute interrompue.",
      "start-failed": "Le microphone n’a pas pu démarrer. Vérifiez qu’une autre application ne l’utilise pas.",
      unknown: "La reconnaissance vocale a échoué. Vous pouvez saisir votre texte."
    };
    showError(messages[code] || messages.unknown);
    setMicState("idle", "Touchez pour parler");
  }

  function recognitionLanguage(side) {
    const selected = side === "target" ? elements.target.value : elements.source.value;
    if (selected !== "auto") return language(selected)?.recognition || "fr-FR";
    const locale = navigator.language.toLowerCase();
    const browserLanguage = state.languages.find((item) =>
      item.code.toLowerCase() === locale || item.recognition.toLowerCase() === locale ||
      item.recognition.toLowerCase().split("-")[0] === locale.split("-")[0]
    );
    return browserLanguage?.recognition || "fr-FR";
  }

  function listen(side) {
    clearError();
    state.conversationSide = side;
    document.querySelectorAll(".conversation-mic").forEach((button) => {
      button.classList.toggle("active", button.dataset.side === side);
      button.setAttribute("aria-pressed", String(button.dataset.side === side));
    });
    state.conversationStarting = true;
    const started = window.TalkSpeech.start(recognitionLanguage(side), {
      onState(status) {
        state.conversationStarting = false;
        if (status === "listening") {
          setMicState(status, state.conversation
            ? (side === "source" ? "À vous de parler" : "À votre interlocuteur")
            : "Je vous écoute…");
        }
      },
      onInterim(text) {
        elements.speechPreview.textContent = text;
      },
      onResult(text) {
        elements.speechPreview.textContent = "";
        const maxLength = Number(elements.sourceText.maxLength);
        if (text.length > maxLength) {
          elements.sourceText.value = text.slice(0, maxLength);
          updateTextMeta();
          showError(`La phrase dépasse la limite de ${maxLength} caractères. Les premiers caractères sont conservés.`);
          if (state.conversation) stopConversation();
          return;
        }
        state.translation = "";
        state.translationSource = null;
        state.translationTarget = null;
        state.currentHistoryId = null;
        state.currentFavoriteId = null;
        elements.translationCard.hidden = true;
        elements.favorite.setAttribute("aria-pressed", "false");
        elements.sourceText.value = text;
        updateTextMeta();
        if (state.conversation) {
          void processConversation(text, side);
          window.TalkSpeech.stop();
        } else {
          void translate(text);
        }
      },
      onError(code) {
        state.conversationStarting = false;
        speechError(code);
        if (state.conversation) stopConversation();
      },
      onEnd() {
        state.conversationStarting = false;
        elements.speechPreview.textContent = "";
        if (state.conversation && !state.busy && state.conversationSide === side) {
          setTimeout(() => {
            if (state.conversation && state.conversationSide === side) {
              listen(side === "source" ? "target" : "source");
            }
          }, 300);
        } else if (!state.conversation && !state.busy) {
          setMicState("idle", "Touchez pour parler");
        }
      }
    });
    if (!started) state.conversationStarting = false;
  }

  async function translate(text, overrides) {
    const content = (text || "").trim();
    if (!content) return;
    if (content.length > Number(elements.sourceText.maxLength)) {
      showError(`Le texte ne doit pas dépasser ${elements.sourceText.maxLength} caractères.`);
      return;
    }
    clearError();
    stopAudio();
    const requestId = ++state.translationRequest;
    state.busy = true;
    elements.translationCard.hidden = true;
    setMicState("processing", "Traduction en cours…");
    try {
      const source = overrides?.source || elements.source.value;
      const target = overrides?.target || elements.target.value;
      const result = await jsonRequest("/api/translate", "POST", { text: content, source, target });
      if (requestId !== state.translationRequest) return;
      state.translation = result.translation;
      state.translationSource = source;
      state.translationTarget = target;
      state.currentHistoryId = result.history_id;
      elements.translationText.textContent = result.translation;
      elements.translationCard.hidden = false;
      elements.detected.textContent = result.detected_source
        ? `· ${languageName(result.detected_source)} détecté`
        : source === "auto" ? "· détection automatique" : "";
      elements.translationLanguages.textContent = `${languageName(source)} → ${languageName(target)}`;
      elements.audioStatus.textContent = "";
      await syncFavoriteState();
      if (state.panelMode === "history") void loadPanelList();
    } catch (error) {
      if (requestId === state.translationRequest) showError(error.message);
    } finally {
      if (requestId === state.translationRequest) {
        state.busy = false;
        if (!state.conversation) setMicState("idle", "Touchez pour parler");
      }
    }
  }

  async function processConversation(text, side) {
    state.busy = true;
    try {
      if (side === "source") {
        await translate(text);
      } else {
        const source = elements.target.value;
        const target = effectiveSourceCode();
        await translate(text, { source, target });
      }
    } finally {
      state.busy = false;
      if (state.conversation) listen(side === "source" ? "target" : "source");
    }
  }

  function effectiveSourceCode() {
    if (elements.source.value !== "auto") return elements.source.value;
    const locale = navigator.language.toLowerCase();
    const match = state.languages.find((item) =>
      item.code.toLowerCase() === locale ||
      item.recognition.toLowerCase() === locale ||
      item.recognition.toLowerCase().split("-")[0] === locale.split("-")[0]
    );
    return match?.code || "fr";
  }

  function stopConversation() {
    state.conversation = false;
    state.busy = false;
    state.conversationStarting = false;
    window.TalkSpeech.stop();
    elements.conversationPanel.hidden = true;
    $("#conversation-toggle").setAttribute("aria-pressed", "false");
    setMicState("idle", "Touchez pour parler");
  }

  async function playTranslation(slow) {
    if (!state.translation) return;
    if (state.audio) state.audio.pause();
    const requestId = ++state.audioRequest;
    clearError();
    elements.audioStatus.textContent = "Préparation de l’audio…";
    $("#speak-button").classList.add("is-playing");
    try {
      const response = await request("/api/tts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: state.translation, lang: state.translationTarget || elements.target.value, slow })
      });
      if (requestId !== state.audioRequest) return;
      const blob = await response.blob();
      if (requestId !== state.audioRequest) return;
      if (state.audioUrl) URL.revokeObjectURL(state.audioUrl);
      state.audioUrl = URL.createObjectURL(blob);
      state.audio = new Audio(state.audioUrl);
      state.audio.onended = function () {
        if (requestId !== state.audioRequest) return;
        elements.audioStatus.textContent = "";
        $("#speak-button").classList.remove("is-playing");
      };
      state.audio.onerror = function () {
        if (requestId !== state.audioRequest) return;
        elements.audioStatus.textContent = "";
        $("#speak-button").classList.remove("is-playing");
        showError("La lecture audio a échoué.");
      };
      elements.audioStatus.textContent = slow ? "Lecture lente…" : "Lecture…";
      await state.audio.play();
    } catch (error) {
      if (requestId !== state.audioRequest) return;
      elements.audioStatus.textContent = "";
      $("#speak-button").classList.remove("is-playing");
      showError(error.message);
    }
  }

  function stopAudio() {
    state.audioRequest += 1;
    if (state.audio) {
      state.audio.pause();
      state.audio.currentTime = 0;
    }
    elements.audioStatus.textContent = "";
    $("#speak-button").classList.remove("is-playing");
  }

  async function syncFavoriteState() {
    if (!state.translation) return;
    try {
      const result = await jsonRequest("/api/favorites", "GET");
      const favorite = result.favorites.find((item) =>
        item.text === elements.sourceText.value.trim() &&
        item.translation === state.translation &&
        item.source === state.translationSource &&
        item.target === state.translationTarget
      );
      state.currentFavoriteId = favorite?.id || null;
      elements.favorite.setAttribute("aria-pressed", state.currentFavoriteId ? "true" : "false");
      elements.favorite.title = state.currentFavoriteId ? "Retirer des favoris" : "Ajouter aux favoris";
      elements.favorite.setAttribute("aria-label", elements.favorite.title);
    } catch (error) {
      showError(error.message);
    }
  }

  async function toggleFavorite() {
    if (!state.translation) return;
    try {
      if (state.currentFavoriteId) {
        await jsonRequest(`/api/favorites/${state.currentFavoriteId}`, "DELETE");
        state.currentFavoriteId = null;
        elements.favorite.setAttribute("aria-pressed", "false");
      } else {
        const result = await jsonRequest("/api/favorites", "POST", {
          text: elements.sourceText.value.trim(),
          translation: state.translation,
          source: state.translationSource || elements.source.value,
          target: state.translationTarget || elements.target.value
        });
        state.currentFavoriteId = result.id;
        elements.favorite.setAttribute("aria-pressed", "true");
      }
      await loadPanelList();
    } catch (error) {
      showError(error.message);
    }
  }

  async function loadPanelList() {
    try {
      const endpoint = state.panelMode === "history" ? "/api/history" : "/api/favorites";
      const key = state.panelMode === "history" ? "history" : "favorites";
      const result = await jsonRequest(endpoint, "GET");
      renderPanelList(result[key] || []);
    } catch (error) {
      elements.panelList.replaceChildren();
      const message = document.createElement("p");
      message.className = "empty-state";
      message.textContent = error.message;
      elements.panelList.append(message);
    }
  }

  function renderPanelList(items) {
    elements.panelList.replaceChildren();
    elements.clearList.textContent = state.panelMode === "history" ? "Vider l’historique" : "Vider les favoris";
    elements.clearList.hidden = items.length === 0;
    if (!items.length) {
      const empty = document.createElement("p");
      empty.className = "empty-state";
      empty.textContent = state.panelMode === "history"
        ? "Vos traductions récentes apparaîtront ici."
        : "Enregistrez une traduction avec l’étoile pour la retrouver ici.";
      elements.panelList.append(empty);
      return;
    }
    items.forEach((item) => {
      const card = document.createElement("article");
      card.className = "history-item";
      const head = document.createElement("div");
      head.className = "history-item-head";
      const pair = document.createElement("span");
      pair.textContent = `${languageName(item.source)} → ${languageName(item.target)}`;
      const actions = document.createElement("div");
      actions.className = "history-item-actions";
      const reuse = document.createElement("button");
      reuse.type = "button";
      reuse.setAttribute("aria-label", "Réutiliser cette traduction");
      reuse.title = "Réutiliser";
      reuse.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 12a8 8 0 0 1 14-5l2 2m0-5v5h-5m5 3a8 8 0 0 1-14 5l-2-2m0 5v-5h5"/></svg>';
      reuse.addEventListener("click", () => reuseTranslation(item));
      const remove = document.createElement("button");
      remove.type = "button";
      remove.setAttribute("aria-label", state.panelMode === "history" ? "Supprimer de l’historique" : "Supprimer des favoris");
      remove.title = "Supprimer";
      remove.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16m-10 4v6m4-6v6M6 7l1 14h10l1-14M9 7V4h6v3"/></svg>';
      remove.addEventListener("click", () => void removeItem(item.id));
      actions.append(reuse, remove);
      head.append(pair, actions);
      const source = document.createElement("p");
      source.className = "history-source";
      source.textContent = item.text;
      const translation = document.createElement("p");
      translation.className = "history-translation";
      translation.textContent = item.translation;
      card.append(head, source, translation);
      elements.panelList.append(card);
    });
  }

  function reuseTranslation(item) {
    elements.source.value = item.source;
    elements.target.value = item.target;
    elements.sourceText.value = item.text;
    state.translation = item.translation;
    state.translationSource = item.source;
    state.translationTarget = item.target;
    state.currentHistoryId = item.id;
    elements.translationText.textContent = item.translation;
    elements.translationCard.hidden = false;
    elements.detected.textContent = "";
    elements.translationLanguages.textContent = `${languageName(item.source)} → ${languageName(item.target)}`;
    updateLanguageDisplay();
    updateTextMeta();
    void syncFavoriteState();
    closeHistory();
  }

  async function removeItem(itemId) {
    try {
      await jsonRequest(state.panelMode === "history" ? `/api/history/${itemId}` : `/api/favorites/${itemId}`, "DELETE");
      await loadPanelList();
      if (state.panelMode === "favorites" && itemId === state.currentFavoriteId) {
        state.currentFavoriteId = null;
        elements.favorite.setAttribute("aria-pressed", "false");
      }
    } catch (error) {
      showError(error.message);
    }
  }

  function openHistory() {
    elements.historyPanel.classList.add("is-open");
    elements.historyPanel.setAttribute("aria-hidden", "false");
    elements.backdrop.hidden = false;
    $("body").classList.add("panel-active");
    $("#history-toggle").setAttribute("aria-expanded", "true");
    $("#close-history").focus();
    void loadPanelList();
  }

  function closeHistory() {
    elements.historyPanel.classList.remove("is-open");
    elements.historyPanel.setAttribute("aria-hidden", "true");
    elements.backdrop.hidden = true;
    $("body").classList.remove("panel-active");
    $("#history-toggle").setAttribute("aria-expanded", "false");
    $("#history-toggle").focus();
  }

  function selectPanel(mode) {
    state.panelMode = mode;
    const historyActive = mode === "history";
    elements.historyTab.classList.toggle("active", historyActive);
    elements.favoritesTab.classList.toggle("active", !historyActive);
    elements.historyTab.setAttribute("aria-selected", String(historyActive));
    elements.favoritesTab.setAttribute("aria-selected", String(!historyActive));
    elements.panelList.setAttribute("aria-labelledby", historyActive ? "history-tab" : "favorites-tab");
    void loadPanelList();
  }

  async function clearPanelList() {
    const endpoint = state.panelMode === "history" ? "/api/history" : "/api/favorites";
    try {
      await jsonRequest(endpoint, "DELETE");
      if (state.panelMode === "favorites") {
        state.currentFavoriteId = null;
        elements.favorite.setAttribute("aria-pressed", "false");
      }
      await loadPanelList();
    } catch (error) {
      showError(error.message);
    }
  }

  function initializeTheme() {
    let saved = null;
    try {
      saved = localStorage.getItem("talk-translate-theme");
    } catch (_error) {
      saved = null;
    }
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    function setTheme(theme) {
      document.documentElement.dataset.theme = theme;
      $("#theme-toggle").setAttribute("aria-label", `Activer le thème ${theme === "dark" ? "clair" : "sombre"}`);
      document.querySelector('meta[name="theme-color"]').content = theme === "dark" ? "#121915" : "#f5f7f4";
    }
    if (saved === "dark" || saved === "light") {
      setTheme(saved);
    } else {
      setTheme(media.matches ? "dark" : "light");
      media.addEventListener("change", (event) => {
        let preference = null;
        try {
          preference = localStorage.getItem("talk-translate-theme");
        } catch (_error) {
          preference = null;
        }
        if (!preference) setTheme(event.matches ? "dark" : "light");
      });
    }
    $("#theme-toggle").addEventListener("click", () => {
      const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
      setTheme(next);
      try {
        localStorage.setItem("talk-translate-theme", next);
      } catch (_error) {
        showError("Le thème est modifié, mais ne peut pas être mémorisé sur cet appareil.");
      }
    });
  }

  function bindEvents() {
    elements.source.addEventListener("change", () => {
      updateLanguageDisplay();
      if (elements.sourceText.value.trim()) void translate(elements.sourceText.value);
    });
    elements.target.addEventListener("change", () => {
      updateLanguageDisplay();
      if (elements.sourceText.value.trim()) void translate(elements.sourceText.value);
    });
    $("#swap-languages").addEventListener("click", () => {
      if (elements.source.value === "auto") {
        showError("Choisissez une langue source avant de l’inverser.");
        return;
      }
      window.clearTimeout(state.debounce);
      state.translationRequest += 1;
      stopAudio();
      const previousText = elements.sourceText.value;
      const previousTranslation = state.translation;
      const previousSource = elements.source.value;
      const previousTarget = elements.target.value;
      elements.source.value = previousTarget;
      elements.target.value = previousSource;
      elements.sourceText.value = previousTranslation || previousText;
      state.translation = previousTranslation ? previousText : "";
      state.translationSource = previousTranslation ? previousTarget : null;
      state.translationTarget = previousTranslation ? previousSource : null;
      updateLanguageDisplay();
      updateTextMeta();
      if (state.translation) {
        elements.translationText.textContent = state.translation;
        elements.translationLanguages.textContent = `${languageName(previousTarget)} → ${languageName(previousSource)}`;
        elements.translationCard.hidden = false;
        void syncFavoriteState();
      } else {
        elements.translationCard.hidden = true;
        state.currentFavoriteId = null;
        elements.favorite.setAttribute("aria-pressed", "false");
      }
      clearError();
    });
    elements.sourceText.addEventListener("input", () => {
      updateTextMeta();
      clearError();
      window.clearTimeout(state.debounce);
      state.translationRequest += 1;
      state.busy = false;
      stopAudio();
      state.translation = "";
      state.translationSource = null;
      state.translationTarget = null;
      state.currentHistoryId = null;
      state.currentFavoriteId = null;
      elements.favorite.setAttribute("aria-pressed", "false");
      if (!elements.sourceText.value.trim()) {
        elements.translationCard.hidden = true;
        return;
      }
      elements.translationCard.hidden = true;
      state.debounce = window.setTimeout(() => void translate(elements.sourceText.value), 500);
    });
    elements.sourceText.addEventListener("keydown", (event) => {
      if (event.ctrlKey && event.key === "Enter") {
        event.preventDefault();
        window.clearTimeout(state.debounce);
        void translate(elements.sourceText.value);
      }
    });
    elements.translateButton.addEventListener("click", () => {
      window.clearTimeout(state.debounce);
      void translate(elements.sourceText.value);
    });
    elements.clearText.addEventListener("click", () => {
      stopAudio();
      elements.sourceText.value = "";
      state.translation = "";
      state.translationSource = null;
      state.translationTarget = null;
      state.currentHistoryId = null;
      state.currentFavoriteId = null;
      elements.favorite.setAttribute("aria-pressed", "false");
      state.translationRequest += 1;
      elements.translationCard.hidden = true;
      updateTextMeta();
      clearError();
      elements.sourceText.focus();
    });
    elements.mic.addEventListener("click", () => {
      if (state.conversation) {
        stopConversation();
      } else if (window.TalkSpeech.isActive() || state.conversationStarting) {
        window.TalkSpeech.stop();
        setMicState("idle", "Touchez pour parler");
      } else {
        if (!window.TalkSpeech.isSupported()) {
          speechError("unsupported");
          return;
        }
        listen("source");
      }
    });
    $("#conversation-toggle").addEventListener("click", () => {
      if (state.conversation) {
        stopConversation();
        return;
      }
      if (!window.TalkSpeech.isSupported()) {
        speechError("unsupported");
        return;
      }
      state.conversation = true;
      elements.conversationPanel.hidden = false;
      $("#conversation-toggle").setAttribute("aria-pressed", "true");
      listen("source");
    });
    document.querySelectorAll(".conversation-mic").forEach((button) => {
      button.addEventListener("click", () => {
        if (state.conversation) {
          window.TalkSpeech.stop();
          listen(button.dataset.side);
        }
      });
    });
    $("#speak-button").addEventListener("click", () => {
      if (state.audio) {
        if (!state.audio.paused) {
          state.audio.pause();
          elements.audioStatus.textContent = "En pause";
          $("#speak-button").classList.remove("is-playing");
          return;
        }
        if (state.audio.currentTime > 0) {
          state.audio.play().then(() => {
            elements.audioStatus.textContent = "Lecture…";
            $("#speak-button").classList.add("is-playing");
          }).catch(() => showError("La lecture audio a échoué."));
          return;
        }
      }
      void playTranslation(false);
    });
    $("#audio-stop-button").addEventListener("click", stopAudio);
    $("#slow-speak-button").addEventListener("click", () => void playTranslation(true));
    $("#copy-button").addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(state.translation);
        elements.audioStatus.textContent = "Copié !";
        setTimeout(() => { elements.audioStatus.textContent = ""; }, 1600);
      } catch (_error) {
        showError("La copie est indisponible. Sélectionnez le texte pour le copier.");
      }
    });
    elements.favorite.addEventListener("click", () => void toggleFavorite());
    $("#share-button").addEventListener("click", async () => {
      const shareData = { title: "Ma traduction", text: `${elements.sourceText.value.trim()}\n→ ${state.translation}` };
      try {
        if (navigator.share) await navigator.share(shareData);
        else if (navigator.clipboard) {
          await navigator.clipboard.writeText(shareData.text);
          elements.audioStatus.textContent = "Texte copié pour le partager.";
          setTimeout(() => { elements.audioStatus.textContent = ""; }, 1800);
        } else {
          showError("Le partage n’est pas disponible sur cet appareil.");
        }
      } catch (error) {
        if (error.name !== "AbortError") showError("Le partage n’est pas disponible sur cet appareil.");
      }
    });
    $("#history-toggle").addEventListener("click", openHistory);
    $("#close-history").addEventListener("click", closeHistory);
    elements.backdrop.addEventListener("click", closeHistory);
    elements.historyTab.addEventListener("click", () => selectPanel("history"));
    elements.favoritesTab.addEventListener("click", () => selectPanel("favorites"));
    elements.clearList.addEventListener("click", () => void clearPanelList());
    document.addEventListener("keydown", (event) => {
      if (event.key === "Tab" && elements.historyPanel.classList.contains("is-open")) {
        const focusable = elements.historyPanel.querySelectorAll(
          "button:not([disabled]):not([hidden]), a[href], select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex='-1'])"
        );
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last?.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first?.focus();
        }
        return;
      }
      if (event.key === "Escape" && elements.historyPanel.classList.contains("is-open")) closeHistory();
      else if (event.key === "Escape" && state.audio && !state.audio.paused) stopAudio();
      if (event.code === "Space" && !event.repeat && !["TEXTAREA", "INPUT", "SELECT", "BUTTON"].includes(document.activeElement.tagName)) {
        event.preventDefault();
        elements.mic.click();
      }
      if (event.ctrlKey && event.key.toLowerCase() === "l") {
        event.preventDefault();
        elements.clearText.click();
      }
    });
  }

  async function initialize() {
    initializeTheme();
    bindEvents();
    updateTextMeta();
    try {
      await loadLanguages();
    } catch (error) {
      showError(error.message);
      elements.source.disabled = true;
      elements.target.disabled = true;
    }
  }

  void initialize();
}());
