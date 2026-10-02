/* ==========================================================================
   career.js - AI Career Guide page
   Collects the learner profile, calls POST /api/career/plan and renders the plan.
   ========================================================================== */
(function () {
  "use strict";

  const form = document.getElementById("career-form");
  if (!form) return;

  const submitBtn = document.getElementById("career-submit");
  const statusBox = document.getElementById("career-error");
  const loading = document.getElementById("career-loading");
  const resultBox = document.getElementById("career-result");

  const REQUIRED_FIELDS = [
    ["education", "education"],
    ["skills", "your current skills"],
    ["target_role", "your target role"],
    ["experience_level", "your experience level"],
    ["time_per_day", "how much time you have per day"],
  ];

  /* ------------------------------------------------- load dropdown options */
  App.get("/api/target-roles")
    .then(function (data) {
      const list = document.getElementById("role-options");
      if (list && data.roles) {
        list.innerHTML = data.roles.map(function (role) {
          return '<option value="' + App.escapeHtml(role) + '"></option>';
        }).join("");
      }

      const select = document.getElementById("experience_level");
      if (select && data.experience_levels) {
        select.innerHTML =
          '<option value="">Please choose...</option>' +
          data.experience_levels.map(function (level) {
            return '<option value="' + App.escapeHtml(level) + '">' +
              App.escapeHtml(level) + "</option>";
          }).join("");
      }
    })
    .catch(function () {
      /* Suggestions are optional - the fields still work without them. */
    });

  /* ------------------------------------------------------------ helpers */
  function clearInvalid() {
    form.querySelectorAll(".invalid").forEach(function (element) {
      element.classList.remove("invalid");
    });
  }

  /* ------------------------------------------------------------- submit */
  form.addEventListener("submit", async function (event) {
    event.preventDefault();
    App.clearAlert(statusBox);
    clearInvalid();

    const payload = {};
    let firstInvalid = null;

    REQUIRED_FIELDS.forEach(function (entry) {
      const field = form.elements[entry[0]];
      const value = (field && field.value ? field.value : "").trim();
      payload[entry[0]] = value;
      if (!value) {
        if (field) field.classList.add("invalid");
        if (!firstInvalid) firstInvalid = field;
      }
    });

    if (firstInvalid) {
      App.showAlert(
        statusBox,
        "Please fill in the fields highlighted in pink, then try again."
      );
      firstInvalid.focus();
      return;
    }

    payload.interests = (form.elements.interests.value || "").trim();
    payload.extra_notes = (form.elements.extra_notes.value || "").trim();

    App.setBusy(submitBtn, true, "Building your plan...");
    loading.classList.remove("hidden");
    resultBox.classList.add("hidden");

    try {
      const response = await App.postJson("/api/career/plan", payload);
      resultBox.innerHTML = Render.plan(response.plan);
      resultBox.classList.remove("hidden");
      App.showAlert(statusBox, "Your plan is ready and has been saved to History.", "ok");
      resultBox.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (error) {
      App.showAlert(statusBox, error.message);
    } finally {
      loading.classList.add("hidden");
      App.setBusy(submitBtn, false);
    }
  });

  /* -------------------------------------------------------------- reset */
  form.addEventListener("reset", function () {
    clearInvalid();
    App.clearAlert(statusBox);
    resultBox.classList.add("hidden");
    resultBox.innerHTML = "";
  });
})();
