/* ==========================================================================
   analyzer.js - Resume Analyzer page
   Uploads a PDF/DOCX resume + target role to POST /api/resume/analyze
   and renders the ATS report.
   ========================================================================== */
(function () {
  "use strict";

  const form = document.getElementById("analyzer-form");
  if (!form) return;

  const fileInput = document.getElementById("resume");
  const fileName = document.getElementById("file-name");
  const dropzone = document.getElementById("dropzone");
  const roleInput = document.getElementById("target_role");
  const submitBtn = document.getElementById("analyzer-submit");
  const statusBox = document.getElementById("analyzer-error");
  const loading = document.getElementById("analyzer-loading");
  const resultBox = document.getElementById("analyzer-result");
  const TEMPORARY_UNAVAILABLE_MESSAGE =
    "Gemini is temporarily unavailable. Please try again in a moment.";

  let maxBytes = 5 * 1024 * 1024; // replaced with the real limit from /api/health

  /* --------------------------------------------------- target role options */
  App.get("/api/target-roles")
    .then(function (data) {
      const list = document.getElementById("role-options");
      if (list && data.roles) {
        list.innerHTML = data.roles.map(function (role) {
          return '<option value="' + App.escapeHtml(role) + '"></option>';
        }).join("");
      }
    })
    .catch(function () {
      /* Suggestions are optional. */
    });

  /* -------------------------------------------------------- upload limit */
  App.get("/api/health")
    .then(function (health) {
      if (health && health.max_upload_mb) {
        maxBytes = health.max_upload_mb * 1024 * 1024;
        const hint = document.getElementById("upload-limit");
        if (hint) {
          hint.textContent =
            "PDF or DOCX only - maximum " + health.max_upload_mb + " MB";
        }
      }
    })
    .catch(function () {
      /* Keep the default text. */
    });

  /* ------------------------------------------------------------ file label */
  function showFileName() {
    const file = fileInput.files && fileInput.files[0];
    fileName.textContent = file ? file.name : "";
  }

  function showTemporaryUnavailable() {
    statusBox.innerHTML =
      '<div class="analyzer-error-card" role="alert">' +
        '<span class="analyzer-error-icon" aria-hidden="true">' +
          '<svg viewBox="0 0 32 32" fill="none">' +
            '<path d="M16 4.5 28 26H4L16 4.5Z" />' +
            '<path d="M16 12v6m0 3.5v.1" />' +
          '</svg>' +
        '</span>' +
        '<div class="analyzer-error-copy">' +
          '<h2>AI Analysis is temporarily unavailable</h2>' +
          '<p>Gemini is currently experiencing high demand. Please try again after a short while.</p>' +
          '<p class="analyzer-error-note">Your resume was not lost. You can safely try again later.</p>' +
        '</div>' +
        '<button class="btn analyzer-retry" type="submit" form="analyzer-form">Try Again</button>' +
      '</div>';
  }

  fileInput.addEventListener("change", function () {
    showFileName();
    App.clearAlert(statusBox);
    fileInput.classList.remove("invalid");
  });

  /* ------------------------------------------------------- drag and drop */
  ["dragenter", "dragover"].forEach(function (eventName) {
    dropzone.addEventListener(eventName, function (event) {
      event.preventDefault();
      dropzone.classList.add("is-drag");
    });
  });

  ["dragleave", "drop"].forEach(function (eventName) {
    dropzone.addEventListener(eventName, function (event) {
      event.preventDefault();
      dropzone.classList.remove("is-drag");
    });
  });

  dropzone.addEventListener("drop", function (event) {
    const dropped = event.dataTransfer && event.dataTransfer.files;
    if (!dropped || !dropped.length) return;

    const problem = App.validateFile(dropped[0]);
    if (problem) {
      App.showAlert(statusBox, problem);
      return;
    }

    const transfer = new DataTransfer();
    transfer.items.add(dropped[0]);
    fileInput.files = transfer.files;
    showFileName();
    App.clearAlert(statusBox);
  });

  /* ------------------------------------------------------------- submit */
  form.addEventListener("submit", async function (event) {
    event.preventDefault();
    App.clearAlert(statusBox);

    const file = fileInput.files && fileInput.files[0];
    const fileProblem = App.validateFile(file);
    if (fileProblem) {
      fileInput.classList.add("invalid");
      App.showAlert(statusBox, fileProblem);
      dropzone.scrollIntoView({ behavior: "smooth", block: "center" });
      return;
    }

    if (file.size > maxBytes) {
      App.showAlert(
        statusBox,
        "That file is too large (" + (file.size / 1024 / 1024).toFixed(1) +
          " MB). The maximum size is " + (maxBytes / 1024 / 1024).toFixed(0) + " MB."
      );
      return;
    }

    if (file.size === 0) {
      App.showAlert(statusBox, "That file is empty. Please choose a different resume.");
      return;
    }

    const role = (roleInput.value || "").trim();
    if (!role) {
      roleInput.classList.add("invalid");
      App.showAlert(statusBox, "Please choose or type the target job role first.");
      roleInput.focus();
      return;
    }

    const formData = new FormData();
    formData.append("resume", file);
    formData.append("target_role", role);

    App.setBusy(submitBtn, true, "Analyzing...");
    loading.classList.remove("hidden");
    resultBox.classList.add("hidden");

    try {
      const response = await App.postForm("/api/resume/analyze", formData);
      resultBox.innerHTML = Render.analysis(response.analysis);
      resultBox.classList.remove("hidden");
      App.showAlert(statusBox, "Report saved to History.", "ok");
      resultBox.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (error) {
      if (error.message === TEMPORARY_UNAVAILABLE_MESSAGE) {
        showTemporaryUnavailable();
      } else {
        App.showAlert(statusBox, error.message);
      }
    } finally {
      loading.classList.add("hidden");
      App.setBusy(submitBtn, false);
    }
  });

  /* -------------------------------------------------------------- reset */
  form.addEventListener("reset", function () {
    App.clearAlert(statusBox);
    fileInput.classList.remove("invalid");
    roleInput.classList.remove("invalid");
    resultBox.classList.add("hidden");
    resultBox.innerHTML = "";
    /* The reset happens after this handler, so clear the label next tick. */
    window.setTimeout(showFileName, 0);
  });
})();
