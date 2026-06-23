(() => {
  const DEFAULT_SERVER_URL = "http://127.0.0.1:8765";
  const TOKEN_HEADER = "X-Local-LeetCode-Token";
  const BRIDGE_SOURCE = "local-leetcode-sync-content";
  const PAGE_SOURCE = "local-leetcode-sync-page";

  if (window.__localLeetcodeSyncContentInstalled) {
    return;
  }
  window.__localLeetcodeSyncContentInstalled = true;

  function getStorage(defaults) {
    return new Promise((resolve) => chrome.storage.local.get(defaults, resolve));
  }

  function setStorage(values) {
    return new Promise((resolve) => chrome.storage.local.set(values, resolve));
  }

  function injectBridge() {
    if (document.getElementById("local-leetcode-sync-bridge")) {
      return;
    }
    const script = document.createElement("script");
    script.id = "local-leetcode-sync-bridge";
    script.src = chrome.runtime.getURL("page_bridge.js");
    script.onload = () => script.remove();
    (document.head || document.documentElement).appendChild(script);
  }

  function requestEditorData() {
    injectBridge();
    return new Promise((resolve) => {
      const requestId = `${Date.now()}-${Math.random()}`;
      const timeout = window.setTimeout(() => {
        window.removeEventListener("message", onMessage);
        resolve(null);
      }, 1200);

      function onMessage(event) {
        if (event.source !== window) {
          return;
        }
        const message = event.data || {};
        if (
          message.source !== PAGE_SOURCE ||
          message.type !== "EDITOR_DATA" ||
          message.requestId !== requestId
        ) {
          return;
        }
        window.clearTimeout(timeout);
        window.removeEventListener("message", onMessage);
        resolve(message.payload || null);
      }

      window.addEventListener("message", onMessage);
      window.postMessage(
        {
          source: BRIDGE_SOURCE,
          type: "GET_EDITOR",
          requestId
        },
        "*"
      );
    });
  }

  function titleSlugFromUrl() {
    const match = window.location.pathname.match(/^\/problems\/([^/]+)/);
    return match ? match[1] : "";
  }

  async function fetchQuestion(titleSlug) {
    const query = `
      query localLeetCodeQuestion($titleSlug: String!) {
        question(titleSlug: $titleSlug) {
          questionFrontendId
          title
          titleSlug
          difficulty
          topicTags { name slug }
        }
      }
    `;
    const response = await fetch("https://leetcode.com/graphql/", {
      method: "POST",
      credentials: "include",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        query,
        variables: { titleSlug }
      })
    });
    if (!response.ok) {
      throw new Error(`LeetCode GraphQL failed with ${response.status}`);
    }
    const data = await response.json();
    if (data.errors && data.errors.length) {
      throw new Error(data.errors.map((error) => error.message).join("; "));
    }
    const question = data.data && data.data.question;
    if (!question) {
      throw new Error("LeetCode question data was not found.");
    }
    return question;
  }

  function fallbackQuestion(titleSlug) {
    const heading =
      document.querySelector('[data-cy="question-title"]') ||
      document.querySelector("h1") ||
      document.querySelector("title");
    const title = heading ? heading.textContent.trim().replace(/^\d+\.\s*/, "") : titleSlug;
    const idMatch = document.body.innerText.match(/\b(\d+)\.\s+[A-Z][^\n]+/);
    const difficultyMatch = document.body.innerText.match(/\b(Easy|Medium|Hard)\b/);
    return {
      questionFrontendId: idMatch ? idMatch[1] : "",
      title,
      titleSlug,
      difficulty: difficultyMatch ? difficultyMatch[1] : "",
      topicTags: []
    };
  }

  function textOf(element) {
    if (!element) {
      return "";
    }
    if ("value" in element) {
      return String(element.value || "").trim();
    }
    return String(element.innerText || element.textContent || "").trim();
  }

  function visible(element) {
    const rect = element.getBoundingClientRect();
    const style = window.getComputedStyle(element);
    return rect.width > 0 && rect.height > 0 && style.visibility !== "hidden" && style.display !== "none";
  }

  function collectVisibleNotes() {
    const candidates = Array.from(
      document.querySelectorAll("textarea, [contenteditable='true'], [role='textbox']")
    )
      .filter(visible)
      .map(textOf)
      .filter((value) => value.length >= 12);

    const noteLike = candidates.find((value) => /approach|complexity|time|space|o\(/i.test(value));
    return noteLike || "";
  }

  function collectFallbackCode() {
    const textareas = Array.from(document.querySelectorAll("textarea"))
      .filter(visible)
      .map(textOf)
      .filter((value) => value.includes("class Solution") || value.includes("def ") || value.length > 80);
    return textareas[0] || "";
  }

  function parseMetric(text, label, unit) {
    const compact = text.replace(/\s+/g, " ");
    const withBeats = new RegExp(`${label}\\s+([0-9.]+)\\s*${unit}\\s+Beats\\s+([0-9.]+)%`, "i");
    const simple = new RegExp(`${label}\\s+([0-9.]+)\\s*${unit}`, "i");
    const beatMatch = compact.match(withBeats);
    if (beatMatch) {
      return { value: beatMatch[1], unit, beats: beatMatch[2] };
    }
    const simpleMatch = compact.match(simple);
    if (simpleMatch) {
      return { value: simpleMatch[1], unit, beats: "" };
    }
    return null;
  }

  function trimNumber(value) {
    if (!value) {
      return "";
    }
    return String(Number(value)).replace(/\.0+$/, "");
  }

  function formatMetric(metric) {
    if (!metric) {
      return "";
    }
    const value = trimNumber(metric.value);
    const beats = trimNumber(metric.beats);
    return beats ? `${value} ${metric.unit} (${beats}%)` : `${value} ${metric.unit}`;
  }

  function defaultCommitMessage(runtime, memory) {
    const runtimeText = formatMetric(runtime);
    const memoryText = formatMetric(memory);
    if (!runtimeText || !memoryText) {
      return "";
    }
    return `Time: ${runtimeText}, Space: ${memoryText}`;
  }

  function splitTopics(value) {
    return value
      .split(",")
      .map((topic) => topic.trim())
      .filter(Boolean);
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  async function collectPageData() {
    const titleSlug = titleSlugFromUrl();
    if (!titleSlug) {
      throw new Error("Open a LeetCode problem page before saving.");
    }

    let question;
    try {
      question = await fetchQuestion(titleSlug);
    } catch (error) {
      question = fallbackQuestion(titleSlug);
    }

    const editor = (await requestEditorData()) || {};
    const pageText = document.body.innerText || "";
    const runtime = parseMetric(pageText, "Runtime", "ms");
    const memory = parseMetric(pageText, "Memory", "MB");
    const code = String(editor.code || collectFallbackCode() || "");
    const langSlug = String(editor.languageId || "");
    const notes = collectVisibleNotes();

    return {
      question,
      code,
      langSlug,
      notes,
      runtime,
      memory,
      accepted: /\bAccepted\b/i.test(pageText),
      commitMessage: defaultCommitMessage(runtime, memory)
    };
  }

  function problemFolder(question) {
    const id = String(question.questionFrontendId || "").trim();
    const slug = String(question.titleSlug || titleSlugFromUrl()).trim();
    return id && /^\d+$/.test(id) ? `${String(Number(id)).padStart(4, "0")}-${slug}` : slug;
  }

  async function postLocal(path, payload, options) {
    const serverUrl = (options.serverUrl || DEFAULT_SERVER_URL).replace(/\/$/, "");
    const response = await fetch(`${serverUrl}${path}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        [TOKEN_HEADER]: options.token || ""
      },
      body: JSON.stringify(payload)
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok || data.ok === false) {
      throw new Error(data.error || `Local server returned ${response.status}`);
    }
    return data;
  }

  function buildPayloadFromForm(modal) {
    return {
      problem: {
        frontendId: modal.querySelector("[name='frontendId']").value.trim(),
        title: modal.querySelector("[name='title']").value.trim(),
        slug: modal.querySelector("[name='slug']").value.trim(),
        difficulty: modal.querySelector("[name='difficulty']").value,
        topics: splitTopics(modal.querySelector("[name='topics']").value)
      },
      language: modal.querySelector("[name='language']").value.trim(),
      langSlug: modal.querySelector("[name='langSlug']").value.trim(),
      code: modal.querySelector("[name='code']").value,
      readmeContent: modal.querySelector("[name='readme']").value,
      commitMessage: modal.querySelector("[name='commitMessage']").value.trim(),
      overwrite: modal.querySelector("[name='overwrite']").checked
    };
  }

  function setStatus(modal, text) {
    modal.querySelector(".lls-status").textContent = text;
  }

  function setPreviewState(modal, preview) {
    const confirmRow = modal.querySelector(".lls-confirm-row");
    const overwrite = modal.querySelector("[name='overwrite']");
    if (preview && preview.exists) {
      confirmRow.hidden = false;
      overwrite.checked = false;
    } else {
      confirmRow.hidden = true;
      overwrite.checked = false;
    }
  }

  async function preview(modal) {
    const options = {
      serverUrl: modal.querySelector("[name='serverUrl']").value.trim(),
      token: modal.querySelector("[name='token']").value.trim()
    };
    await setStorage(options);
    const payload = buildPayloadFromForm(modal);
    const result = await postLocal("/preview", payload, options);
    setPreviewState(modal, result.preview);
    setStatus(modal, JSON.stringify(result.preview, null, 2));
    return result.preview;
  }

  async function save(modal) {
    const options = {
      serverUrl: modal.querySelector("[name='serverUrl']").value.trim(),
      token: modal.querySelector("[name='token']").value.trim()
    };
    await setStorage(options);
    const payload = buildPayloadFromForm(modal);
    if (!payload.readmeContent.trim()) {
      throw new Error("README notes are required. Paste or type your LeetCode note first.");
    }
    if (!payload.commitMessage.trim()) {
      throw new Error("Commit message is required. Use the Time/Space result format.");
    }

    const currentPreview = await preview(modal);
    if (currentPreview.exists && !payload.overwrite) {
      throw new Error("This problem folder exists. Confirm overwrite before saving.");
    }

    const result = await postLocal("/save", payload, options);
    setStatus(modal, JSON.stringify(result, null, 2));
  }

  async function showModal(pageData) {
    const options = await getStorage({
      serverUrl: DEFAULT_SERVER_URL,
      token: ""
    });
    const question = pageData.question;
    const topics = (question.topicTags || []).map((topic) => topic.name).join(", ");
    const difficulty = String(question.difficulty || "Medium").toLowerCase();
    const folder = problemFolder(question);

    const overlay = document.createElement("div");
    overlay.className = "lls-overlay";
    overlay.innerHTML = `
      <section class="lls-modal" role="dialog" aria-modal="true">
        <header>
          <h2>Save ${escapeHtml(folder || "LeetCode problem")}</h2>
          <button class="lls-secondary" data-action="close" type="button">Close</button>
        </header>
        <div class="lls-grid">
          <label>
            Server URL
            <input name="serverUrl" type="text" value="${escapeHtml(options.serverUrl || DEFAULT_SERVER_URL)}">
          </label>
          <label>
            Local token
            <input name="token" type="password" value="${escapeHtml(options.token || "")}">
          </label>
          <label>
            Frontend ID
            <input name="frontendId" type="text" value="${escapeHtml(question.questionFrontendId || "")}">
          </label>
          <label>
            Slug
            <input name="slug" type="text" value="${escapeHtml(question.titleSlug || titleSlugFromUrl())}">
          </label>
          <label>
            Title
            <input name="title" type="text" value="${escapeHtml(question.title || "")}">
          </label>
          <label>
            Difficulty
            <select name="difficulty">
              <option value="easy"${difficulty === "easy" ? " selected" : ""}>easy</option>
              <option value="medium"${difficulty === "medium" ? " selected" : ""}>medium</option>
              <option value="hard"${difficulty === "hard" ? " selected" : ""}>hard</option>
            </select>
          </label>
          <label class="lls-full">
            Topics, comma separated
            <input name="topics" type="text" value="${escapeHtml(topics)}">
          </label>
          <label>
            Language
            <input name="language" type="text" value="${escapeHtml(pageData.langSlug || "")}" placeholder="python3">
          </label>
          <label>
            Internal language slug
            <input name="langSlug" type="text" value="${escapeHtml(pageData.langSlug || "")}" placeholder="python3">
          </label>
          <label class="lls-full">
            Commit message
            <input name="commitMessage" type="text" value="${escapeHtml(pageData.commitMessage || "")}" placeholder="Time: 0 ms (100%), Space: 20.6 MB (8.11%)">
          </label>
          <label class="lls-full">
            README notes
            <textarea name="readme" placeholder="Paste your LeetCode note here.">${escapeHtml(pageData.notes || "")}</textarea>
          </label>
          <label class="lls-full">
            Solution code
            <textarea class="lls-code" name="code">${escapeHtml(pageData.code || "")}</textarea>
          </label>
          <label class="lls-confirm-row lls-full" hidden>
            <input name="overwrite" type="checkbox">
            Existing folder found. Confirm overwrite.
          </label>
        </div>
        <pre class="lls-status">${escapeHtml(
          pageData.accepted
            ? "Ready. Click Preview to check the local repo, then Save."
            : "Accepted status was not detected. You can still preview and save manually."
        )}</pre>
        <footer>
          <span>${escapeHtml(folder)}</span>
          <div class="lls-actions">
            <button class="lls-secondary" data-action="preview" type="button">Preview</button>
            <button data-action="save" type="button">Save and commit</button>
          </div>
        </footer>
      </section>
    `;
    document.body.appendChild(overlay);

    const modal = overlay.querySelector(".lls-modal");
    overlay.addEventListener("click", (event) => {
      if (event.target === overlay || event.target.dataset.action === "close") {
        overlay.remove();
      }
    });
    modal.querySelector("[data-action='preview']").addEventListener("click", async () => {
      try {
        setStatus(modal, "Previewing...");
        await preview(modal);
      } catch (error) {
        setStatus(modal, `Preview failed: ${error.message}`);
      }
    });
    modal.querySelector("[data-action='save']").addEventListener("click", async () => {
      try {
        setStatus(modal, "Saving...");
        await save(modal);
      } catch (error) {
        setStatus(modal, `Save failed: ${error.message}`);
      }
    });
  }

  function installButton() {
    if (document.querySelector(".lls-save-button")) {
      return;
    }
    const button = document.createElement("button");
    button.className = "lls-save-button";
    button.type = "button";
    button.textContent = "Save to Local Repo";
    button.addEventListener("click", async () => {
      button.disabled = true;
      button.textContent = "Reading...";
      try {
        const data = await collectPageData();
        await showModal(data);
      } catch (error) {
        window.alert(`Local LeetCode Sync failed: ${error.message}`);
      } finally {
        button.disabled = false;
        button.textContent = "Save to Local Repo";
      }
    });
    document.documentElement.appendChild(button);
  }

  injectBridge();
  installButton();
  new MutationObserver(installButton).observe(document.documentElement, {
    childList: true,
    subtree: true
  });
})();
