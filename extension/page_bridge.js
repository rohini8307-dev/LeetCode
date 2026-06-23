(function () {
  if (window.__localLeetcodeSyncBridgeInstalled) {
    return;
  }
  window.__localLeetcodeSyncBridgeInstalled = true;

  function largestModel(models) {
    return models.reduce((best, model) => {
      if (!best) {
        return model;
      }
      const bestLength = String(best.getValue ? best.getValue() : "").length;
      const nextLength = String(model.getValue ? model.getValue() : "").length;
      return nextLength > bestLength ? model : best;
    }, null);
  }

  function readMonaco() {
    const monaco = window.monaco;
    const editors = monaco && monaco.editor;
    if (!editors || typeof editors.getModels !== "function") {
      return null;
    }

    const models = editors.getModels();
    if (!models || !models.length) {
      return null;
    }

    const model = largestModel(models);
    if (!model || typeof model.getValue !== "function") {
      return null;
    }

    return {
      code: model.getValue(),
      languageId: typeof model.getLanguageId === "function" ? model.getLanguageId() : "",
      uri: model.uri && typeof model.uri.toString === "function" ? model.uri.toString() : ""
    };
  }

  window.addEventListener("message", (event) => {
    if (event.source !== window) {
      return;
    }
    const message = event.data || {};
    if (message.source !== "local-leetcode-sync-content" || message.type !== "GET_EDITOR") {
      return;
    }

    window.postMessage(
      {
        source: "local-leetcode-sync-page",
        type: "EDITOR_DATA",
        requestId: message.requestId,
        payload: readMonaco()
      },
      "*"
    );
  });
})();
