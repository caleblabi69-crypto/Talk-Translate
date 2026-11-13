/* La reconnaissance reste dans le navigateur : ce module ne transmet pas d'audio. */
(function () {
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  let recognition = null;
  let active = false;

  function isSupported() {
    return Boolean(Recognition);
  }

  function start(language, handlers) {
    if (!Recognition) {
      handlers.onError("unsupported");
      return false;
    }
    if (active) stop();
    recognition = new Recognition();
    recognition.lang = language;
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;
    recognition.onstart = function () {
      active = true;
      handlers.onState("listening");
    };
    recognition.onresult = function (event) {
      let interim = "";
      let finalText = "";
      for (let index = event.resultIndex; index < event.results.length; index += 1) {
        const result = event.results[index];
        if (result.isFinal) finalText += result[0].transcript;
        else interim += result[0].transcript;
      }
      if (interim) handlers.onInterim(interim);
      if (finalText.trim()) handlers.onResult(finalText.trim());
    };
    recognition.onerror = function (event) {
      const knownErrors = ["not-allowed", "service-not-allowed", "no-speech", "audio-capture", "network", "aborted"];
      handlers.onError(knownErrors.includes(event.error) ? event.error : "unknown");
    };
    recognition.onend = function () {
      active = false;
      handlers.onEnd();
    };
    try {
      recognition.start();
      return true;
    } catch (error) {
      active = false;
      handlers.onError("start-failed");
      return false;
    }
  }

  function stop() {
    if (recognition && active) recognition.stop();
    active = false;
  }

  window.TalkSpeech = { isSupported, start, stop, isActive: function () { return active; } };
}());
