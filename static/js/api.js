/* ==========================================================================
   api.js - shared helpers used by every page
   Exposes a single global object:  App
   ========================================================================== */
const App = (function () {
  "use strict";

  const ALLOWED_EXTENSIONS = [".pdf", ".docx"];

  /* ------------------------------------------------------------ escaping */
  function escapeHtml(value) {
    if (value === null || value === undefined) return "";
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  /* ------------------------------------------------------ fetch wrapper */
  async function request(url, options) {
    let response;
    try {
      response = await fetch(url, options || {});
    } catch (error) {
      throw new Error(
        "Could not reach the server. Please make sure app.py is still running, then try again."
      );
    }

    const contentType = response.headers.get("content-type") || "";
    let payload = {};
    if (contentType.indexOf("application/json") !== -1) {
      try {
        payload = await response.json();
      } catch (error) {
        payload = {};
      }
    }

    if (!response.ok) {
      throw new Error(
        payload.error || "The request failed (HTTP " + response.status + ")."
      );
    }
    return payload;
  }

  const get = (url) => request(url);
  const del = (url) => request(url, { method: "DELETE" });
  const postJson = (url, body) =>
    request(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  const postForm = (url, formData) => request(url, { method: "POST", body: formData });

  /* ------------------------------------------------------------- alerts */
  const ICONS = { error: "!", ok: "✓", warn: "!", info: "i" };

  function showAlert(container, message, type) {
    if (!container) return;
    const kind = type || "error";
    container.innerHTML =
      '<div class="alert alert-' + kind + '">' +
      '<span class="alert-icon">' + (ICONS[kind] || "!") + "</span>" +
      "<p>" + escapeHtml(message) + "</p>" +
      "</div>";
  }

  function clearAlert(container) {
    if (container) container.innerHTML = "";
  }

  /* -------------------------------------------------------------- buttons */
  function setBusy(button, busy, busyLabel) {
    if (!button) return;
    if (busy) {
      if (!button.dataset.idleLabel) button.dataset.idleLabel = button.textContent;
      button.classList.add("is-busy");
      button.disabled = true;
      button.textContent = busyLabel || "Working...";
    } else {
      button.classList.remove("is-busy");
      button.disabled = false;
      if (button.dataset.idleLabel) button.textContent = button.dataset.idleLabel;
    }
  }

  /* ----------------------------------------------------------- formatting */
  function formatDate(iso) {
    if (!iso) return "";
    const date = new Date(iso);
    if (isNaN(date.getTime())) return String(iso);
    return date.toLocaleString(undefined, {
      day: "numeric",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  function scoreClass(score) {
    const value = Number(score);
    if (isNaN(value)) return "";
    if (value >= 75) return "";
    return value >= 50 ? "mid" : "low";
  }

  function priorityPill(priority) {
    const key = String(priority || "").toLowerCase();
    const cls =
      key === "high" ? "pill-high" : key === "medium" ? "pill-medium" : "pill-low";
    return '<span class="pill ' + cls + '">' + escapeHtml(priority || "Medium") + "</span>";
  }

  function urlLabel(url) {
    return escapeHtml(url).replace(/^https?:\/\//, "");
  }

  /* ------------------------------------------------------------- file check */
  function validateFile(file) {
    if (!file) return "Please choose a resume file first.";
    const name = file.name || "";
    const dot = name.lastIndexOf(".");
    const extension = dot === -1 ? "" : name.slice(dot).toLowerCase();
    if (ALLOWED_EXTENSIONS.indexOf(extension) === -1) {
      return "Only PDF and DOCX resumes are supported. Please upload a .pdf or .docx file.";
    }
    return "";
  }

  /* -------------------------------------------------------------- layout */
  function activateNav() {
    const page = document.body.dataset.page;
    if (!page) return;
    document.querySelectorAll("[data-nav]").forEach(function (link) {
      if (link.dataset.nav === page) link.classList.add("is-active");
    });
  }

  async function loadHealth() {
    const banner = document.getElementById("health-banner");
    try {
      const health = await get("/api/health");
      if (health.ai_configured) return;
      if (!banner) return;
      banner.classList.remove("hidden");
      banner.innerHTML =
        "<span>⚠️ AI features are switched off because no Gemini API key was found. " +
        "Open <code>.env</code> in the project folder, add your key after " +
        "<code>GEMINI_API_KEY=</code>, then restart the server.</span>";
    } catch (error) {
      /* The banner is only a nicety - never block the page for it. */
    }
  }

  /* ----------------------------------------------------------------- init */
  function init() {
    activateNav();
    loadHealth();
  }

  document.addEventListener("DOMContentLoaded", init);

  return {
    escapeHtml: escapeHtml,
    get: get,
    del: del,
    postJson: postJson,
    postForm: postForm,
    showAlert: showAlert,
    clearAlert: clearAlert,
    setBusy: setBusy,
    formatDate: formatDate,
    scoreClass: scoreClass,
    priorityPill: priorityPill,
    urlLabel: urlLabel,
    validateFile: validateFile,
  };
})();
