/* ==========================================================================
   history.js - History page
   Lists saved resume reports and career plans, lets you reopen or delete them.
   ========================================================================== */
(function () {
  "use strict";

  const listBox = document.getElementById("history-list");
  if (!listBox) return;

  const detailBox = document.getElementById("history-detail");
  const loading = document.getElementById("history-loading");
  const statusBox = document.getElementById("history-error");
  const tabs = document.querySelectorAll(".tab");

  /* Each tab describes how to fetch, render and label its records. */
  const TABLES = {
    analyses: {
      listUrl: "/api/resume/analyses",
      itemUrl: function (id) { return "/api/resume/analyses/" + encodeURIComponent(id); },
      collection: "analyses",
      pick: function (response) { return response.analysis; },
      render: function (record) { return Render.analysis(record); },
      empty: "No resume reports yet. Analyze a resume to create your first one.",
      emptyIcon: "📄",
    },
    plans: {
      listUrl: "/api/career/plans",
      itemUrl: function (id) { return "/api/career/plans/" + encodeURIComponent(id); },
      collection: "plans",
      pick: function (response) { return response.plan; },
      render: function (record) { return Render.plan(record); },
      empty: "No career plans yet. Build one on the Career Guide page.",
      emptyIcon: "🧭",
    },
  };

  let active = "analyses";

  /* --------------------------------------------------------------- rows */
  function analysisRow(item) {
    const score = (item.ats_score === null || item.ats_score === undefined)
      ? "-"
      : item.ats_score;
    return (
      '<div class="history-row" data-id="' + App.escapeHtml(item.id) + '">' +
        '<div class="row-score">' + App.escapeHtml(score) + "</div>" +
        '<div class="row-main">' +
          "<h4>" + App.escapeHtml(item.target_role || "Untitled role") + "</h4>" +
          "<small>" + App.escapeHtml(item.file_name || "resume") +
            (item.score_label ? " · " + App.escapeHtml(item.score_label) : "") +
            " · " + App.escapeHtml(App.formatDate(item.created_at)) + "</small>" +
        "</div>" +
        '<div class="row-actions">' +
          '<button class="btn btn-sm btn-soft" type="button" data-action="view">View report</button>' +
          '<button class="btn btn-sm btn-danger" type="button" data-action="delete">Delete</button>' +
        "</div>" +
      "</div>"
    );
  }

  function planRow(item) {
    return (
      '<div class="history-row" data-id="' + App.escapeHtml(item.id) + '">' +
        '<div class="row-score">🧭</div>' +
        '<div class="row-main">' +
          "<h4>" + App.escapeHtml(item.target_role || "Career plan") + "</h4>" +
          "<small>" +
            (item.experience_level ? App.escapeHtml(item.experience_level) + " · " : "") +
            (item.time_per_day ? App.escapeHtml(item.time_per_day) + " per day · " : "") +
            App.escapeHtml(App.formatDate(item.created_at)) +
          "</small>" +
        "</div>" +
        '<div class="row-actions">' +
          '<button class="btn btn-sm btn-soft" type="button" data-action="view">View plan</button>' +
          '<button class="btn btn-sm btn-danger" type="button" data-action="delete">Delete</button>' +
        "</div>" +
      "</div>"
    );
  }

  /* -------------------------------------------------------------- list */
  async function loadList() {
    const table = TABLES[active];
    App.clearAlert(statusBox);
    detailBox.classList.add("hidden");
    detailBox.innerHTML = "";
    listBox.innerHTML = "";
    loading.classList.remove("hidden");

    try {
      const response = await App.get(table.listUrl);
      const items = response[table.collection] || [];

      if (!items.length) {
        listBox.innerHTML =
          '<div class="empty"><span class="empty-icon">' + table.emptyIcon + "</span>" +
          "<strong>Nothing saved yet</strong><p>" + App.escapeHtml(table.empty) + "</p></div>";
        return;
      }

      const builder = active === "analyses" ? analysisRow : planRow;
      listBox.innerHTML = items.map(builder).join("");
    } catch (error) {
      App.showAlert(statusBox, error.message);
      listBox.innerHTML = "";
    } finally {
      loading.classList.add("hidden");
    }
  }

  /* ------------------------------------------------------------ detail */
  async function viewItem(id) {
    const table = TABLES[active];
    App.clearAlert(statusBox);
    loading.classList.remove("hidden");

    try {
      const response = await App.get(table.itemUrl(id));
      detailBox.innerHTML = table.render(table.pick(response));
      detailBox.classList.remove("hidden");
      detailBox.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (error) {
      App.showAlert(statusBox, error.message);
    } finally {
      loading.classList.add("hidden");
    }
  }

  /* ------------------------------------------------------------ delete */
  async function removeItem(id) {
    const table = TABLES[active];
    const label = active === "analyses" ? "resume report" : "career plan";
    if (!window.confirm("Delete this " + label + "? This cannot be undone.")) return;

    App.clearAlert(statusBox);
    try {
      await App.del(table.itemUrl(id));
      await loadList();
      App.showAlert(statusBox, "Deleted.", "ok");
    } catch (error) {
      App.showAlert(statusBox, error.message);
    }
  }

  /* ------------------------------------------------------------- events */
  listBox.addEventListener("click", function (event) {
    const button = event.target.closest("[data-action]");
    if (!button) return;

    const row = button.closest(".history-row");
    if (!row) return;

    if (button.dataset.action === "view") {
      viewItem(row.dataset.id);
    } else if (button.dataset.action === "delete") {
      removeItem(row.dataset.id);
    }
  });

  tabs.forEach(function (tab) {
    tab.addEventListener("click", function () {
      active = tab.dataset.tab;
      tabs.forEach(function (other) {
        other.classList.toggle("is-active", other === tab);
      });
      loadList();
    });
  });

  loadList();
})();

