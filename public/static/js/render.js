/* ==========================================================================
   render.js - turns saved records into HTML.
   Exposes a single global object:  Render
   Used by analyzer.js, career.js and history.js so results always look the same.
   ========================================================================== */
const Render = (function () {
  "use strict";

  const esc = App.escapeHtml;

  /* ------------------------------------------------------------ primitives */
  function section(icon, title, inner) {
    if (!inner) return "";
    return (
      '<section class="result-section">' +
      '<h3><span class="icon">' + icon + "</span>" + esc(title) + "</h3>" +
      inner +
      "</section>"
    );
  }

  function bullets(items, pink) {
    if (!items || !items.length) return "";
    return (
      '<ul class="item-list' + (pink ? " pinkish" : "") + '">' +
      items.map(function (item) {
        return "<li>" + esc(item) + "</li>";
      }).join("") +
      "</ul>"
    );
  }

  function chips(items, extraClass) {
    if (!items || !items.length) return "";
    return items.map(function (item) {
      return '<span class="chip ' + (extraClass || "") + '">' + esc(item) + "</span>";
    }).join("");
  }

  function bars(rows) {
    if (!rows || !rows.length) return "";
    return rows.map(function (row) {
      const max = Number(row.max_score) || 100;
      const value = Math.max(0, Math.min(max, Number(row.score) || 0));
      const percent = Math.round((value / max) * 100);
      return (
        '<div class="meter-row">' +
          '<div class="meter-top"><span>' + esc(row.category || "Category") +
            "</span><span>" + value + "/" + max + "</span></div>" +
          '<div class="bar"><div class="bar-fill" style="width:' + percent + '%"></div></div>' +
          (row.comment
            ? '<p style="margin:.3rem 0 0;font-size:.85rem;color:#64748b">' +
              esc(row.comment) + "</p>"
            : "") +
        "</div>"
      );
    }).join("");
  }

  function scoreRing(score, caption) {
    const value = Number(score);
    const safe = isNaN(value) ? 0 : Math.max(0, Math.min(100, Math.round(value)));
    return (
      '<div class="score-ring ' + App.scoreClass(safe) + '" style="--value:' + safe + '">' +
        '<span class="score-ring-inner"><b>' + safe + "</b><small>" +
        esc(caption || "out of 100") + "</small></span>" +
      "</div>"
    );
  }

  function miniGrid(cards) {
    return cards && cards.length ? '<div class="mini-grid">' + cards.join("") + "</div>" : "";
  }

  /* --------------------------------------------------------- resume result */
  function analysis(record) {
    const result = record.result || {};
    const out = [];

    /* Header: score + meta */
    out.push(
      '<div class="card"><div class="score-panel">' +
        scoreRing(result.ats_score, "ATS score") +
        "<div class=\"score-meters\"><h3 style=\"margin:0 0 .5rem\">" +
          esc((result.score_label ? result.score_label + " - " : "") + "ATS score") +
        "</h3>" +
        '<dl class="kv">' +
          "<dt>Target role</dt><dd>" + esc(record.target_role || "-") + "</dd>" +
          "<dt>Resume file</dt><dd>" + esc(record.file_name || "-") + "</dd>" +
          "<dt>Analysed</dt><dd>" + esc(App.formatDate(record.created_at)) + "</dd>" +
          (result.target_role_comparison
            ? "<dt>Role match</dt><dd>" +
              esc(result.target_role_comparison.match_percentage) + "%</dd>"
            : "") +
        "</dl></div>" +
      "</div></div>"
    );

    out.push(
      section("📝", "Resume summary",
        '<div class="card"><p style="margin:0">' + esc(result.resume_summary || "-") + "</p></div>")
    );

    out.push(
      section("📊", "How the score breaks down",
        '<div class="card" style="display:grid;gap:.9rem">' + bars(result.score_breakdown) + "</div>")
    );

    const scoreExplanation = result.ats_score_explanation;
    if (scoreExplanation) {
      const factors = [
        ["Role and keyword match", scoreExplanation.role_keyword_match],
        ["Skills match", scoreExplanation.skills_match],
        ["Projects and experience relevance", scoreExplanation.projects_experience_relevance],
        ["Clarity and structure", scoreExplanation.clarity_structure],
      ].filter(function (factor) { return factor[1]; });
      out.push(section("🧾", "Why this ATS score", bullets(factors.map(function (factor) {
        return factor[0] + ": " + factor[1];
      }))));
    }

    if (result.detected_skills && result.detected_skills.length) {
      out.push(
        section("✅", "Skills detected in your resume",
          '<div class="card">' + chips(result.detected_skills, "ok") + "</div>")
      );
    }

    if (result.weak_skills && result.weak_skills.length) {
      const cards = result.weak_skills.map(function (item) {
        return (
          '<div class="mini-card">' +
            "<h4>" + esc(item.skill) + "</h4>" +
            "<p><strong>Resume evidence:</strong> " + esc(item.resume_evidence) + "</p>" +
            "<p><strong>Strengthen it:</strong> " + esc(item.how_to_strengthen) + "</p>" +
          "</div>"
        );
      });
      out.push(section("🧩", "Skills that need stronger evidence", miniGrid(cards)));
    }

    /* Missing skills */
    if (result.missing_skills && result.missing_skills.length) {
      const cards = result.missing_skills.map(function (item) {
        return (
          '<div class="mini-card pink">' +
            '<div class="meta">' + esc(item.priority || "Medium") + " priority</div>" +
            "<h4>" + esc(item.skill) + "</h4>" +
            "<p>" + esc(item.why_it_matters) + "</p>" +
          "</div>"
        );
      });
      out.push(section("🎯", "Skills you are missing", miniGrid(cards)));
    }

    /* Missing keywords */
    if (result.missing_keywords && result.missing_keywords.length) {
      out.push(
        section("🔍", "Missing ATS keywords",
          '<div class="card"><p style="margin:0 0 .6rem;font-size:.9rem;color:#64748b">' +
          "Adding these words honestly to your resume helps ATS software match you:</p>" +
          chips(result.missing_keywords, "gray") + "</div>")
      );
    }

    if (result.weak_keywords && result.weak_keywords.length) {
      const cards = result.weak_keywords.map(function (item) {
        return (
          '<div class="mini-card">' +
            "<h4>" + esc(item.keyword) + "</h4>" +
            "<p><strong>Resume evidence:</strong> " + esc(item.resume_evidence) + "</p>" +
            "<p><strong>Strengthen it:</strong> " + esc(item.how_to_strengthen) + "</p>" +
          "</div>"
        );
      });
      out.push(section("🔎", "Role keywords to reinforce", miniGrid(cards)));
    }

    /* Certifications */
    if (result.certification_suggestions && result.certification_suggestions.length) {
      const cards = result.certification_suggestions.map(function (item) {
        return (
          '<div class="mini-card">' +
            '<div class="meta">' + esc(item.priority || "Medium") + " priority</div>" +
            "<h4>" + esc(item.name) + "</h4>" +
            "<p>" + esc(item.why) + "</p>" +
            '<div class="tag-row"><span class="chip soft">' + esc(item.provider) + "</span></div>" +
          "</div>"
        );
      });
      out.push(section("🎓", "Certification suggestions", miniGrid(cards)));
    }

    /* Project improvements */
    if (result.project_improvement_suggestions && result.project_improvement_suggestions.length) {
      const cards = result.project_improvement_suggestions.map(function (item) {
        return (
          '<div class="mini-card pink">' +
            "<h4>" + esc(item.title) + "</h4>" +
            "<p>" + esc(item.what_to_add) + "</p>" +
            '<p style="color:#15803d"><strong>Why it helps:</strong> ' +
              esc(item.impact) + "</p>" +
          "</div>"
        );
      });
      out.push(section("🛠️", "Project improvement suggestions", miniGrid(cards)));
    }

    if (result.section_feedback && result.section_feedback.length) {
      const cards = result.section_feedback.map(function (item) {
        return (
          '<div class="mini-card">' +
            "<h4>" + esc(item.section) + "</h4>" +
            "<p><strong>Observation:</strong> " + esc(item.observation) + "</p>" +
            "<p><strong>Next step:</strong> " + esc(item.suggestion) + "</p>" +
          "</div>"
        );
      });
      out.push(section("📚", "Section-by-section feedback", miniGrid(cards)));
    }

    if (result.bullet_rewrites && result.bullet_rewrites.length) {
      const cards = result.bullet_rewrites.map(function (item) {
        return (
          '<div class="mini-card pink">' +
            '<div class="meta">' + esc(item.section) + "</div>" +
            "<p><strong>Original:</strong> " + esc(item.original_bullet) + "</p>" +
            "<p><strong>Suggested rewrite:</strong> " + esc(item.improved_bullet) + "</p>" +
          "</div>"
        );
      });
      out.push(section("🖊️", "Resume bullet improvements", miniGrid(cards)));
    }

    /* Formatting + content */
    out.push(section("📐", "Formatting improvements", bullets(result.formatting_suggestions)));
    out.push(section("✍️", "Content improvements", bullets(result.content_suggestions, true)));

    /* Target role comparison */
    const cmp = result.target_role_comparison;
    if (cmp) {
      const inner =
        '<div class="card"><div class="score-panel" style="margin-bottom:1rem">' +
          scoreRing(cmp.match_percentage, "match") +
          '<div class="score-meters"><h3 style="margin:0 0 .35rem">Match with ' +
            esc(cmp.target_role || record.target_role || "target role") + "</h3>" +
            '<p style="margin:0;color:#64748b;font-size:.92rem">' +
            esc(cmp.verdict || "") + "</p></div>" +
        "</div>" +
        '<div class="grid grid-2">' +
          "<div><h4>✅ Matching strengths</h4>" +
            bullets(cmp.matching_strengths) + "</div>" +
          "<div><h4>⚠️ Gaps to close</h4>" +
            bullets(cmp.gaps, true) + "</div>" +
        "</div></div>";
      out.push(section("🧭", "Target role comparison", inner));
    }

    /* Job portals */
    if (result.job_portal_suggestions && result.job_portal_suggestions.length) {
      const cards = result.job_portal_suggestions.map(function (item) {
        const url = String(item.url || "");
        const href = /^https?:\/\//i.test(url) ? url : "#";
        return (
          '<div class="mini-card">' +
            "<h4>" + esc(item.name) + "</h4>" +
            "<p>" + esc(item.why) + "</p>" +
            '<a href="' + esc(href) + '" target="_blank" rel="noopener noreferrer">' +
              App.urlLabel(url) + "</a>" +
          "</div>"
        );
      });
      out.push(section("🌐", "Where to apply", miniGrid(cards)));
    }

    /* Action steps */
    const actionPlan = result.prioritized_action_plan;
    if (actionPlan) {
      const groups = [
        ["High Priority", actionPlan.high_priority],
        ["Medium Priority", actionPlan.medium_priority],
        ["Low Priority", actionPlan.low_priority],
      ].filter(function (group) { return group[1] && group[1].length; });
      out.push(section("📌", "Prioritized action plan", miniGrid(groups.map(function (group) {
        return (
          '<div class="mini-card pink"><h4>' + esc(group[0]) + "</h4>" +
          bullets(group[1]) + "</div>"
        );
      }))));
    }
    out.push(section("🚀", "Your top action steps", bullets(result.action_steps, true)));

    return out.join("");
  }

  /* --------------------------------------------------------- career result */
  function plan(record) {
    const result = record.result || {};
    const profile = record.profile || {};
    const out = [];

    out.push(
      '<div class="card">' +
        '<div class="card-head"><div>' +
          '<h2 style="margin:0">Your personalised career plan</h2>' +
          "<small>Generated " + esc(App.formatDate(record.created_at)) + "</small>" +
        "</div>" +
        '<span class="chip pink">' + esc(profile.target_role || "Target role") + "</span></div>" +
        '<p style="margin:0">' + esc(result.career_summary || "-") + "</p>" +
        '<div class="tag-row" style="margin-top:.9rem">' +
          (profile.experience_level
            ? '<span class="chip soft">' + esc(profile.experience_level) + "</span>"
            : "") +
          (profile.time_per_day
            ? '<span class="chip soft">' + esc(profile.time_per_day) + " per day</span>"
            : "") +
        "</div>" +
      "</div>"
    );

    out.push(
      section("👤", "The profile you submitted",
        '<div class="card"><dl class="kv">' +
          "<dt>Education</dt><dd>" + esc(profile.education || "-") + "</dd>" +
          "<dt>Skills</dt><dd>" + esc(profile.skills || "-") + "</dd>" +
          (profile.interests
            ? "<dt>Interests</dt><dd>" + esc(profile.interests) + "</dd>"
            : "") +
        "</dl></div>")
    );

    if (result.recommended_roles && result.recommended_roles.length) {
      const cards = result.recommended_roles.map(function (item) {
        return (
          '<div class="mini-card">' +
            '<div class="meta">' + esc(item.entry_level) + "</div>" +
            "<h4>" + esc(item.title) + "</h4>" +
            "<p>" + esc(item.why_it_fits) + "</p>" +
            '<div class="tag-row"><span class="chip soft">Next: ' +
              esc(item.growth_path) + "</span></div>" +
          "</div>"
        );
      });
      out.push(section("🧭", "Recommended roles", miniGrid(cards)));
    }

    if (result.recommended_skills && result.recommended_skills.length) {
      const cards = result.recommended_skills.map(function (item) {
        return (
          '<div class="mini-card' + (item.learn_first ? " pink" : "") + '">' +
            '<div class="meta">' + esc(item.category || "Skill") + "</div>" +
            "<h4>" + esc(item.name) + "</h4>" +
            "<p>" + esc(item.why) + "</p>" +
            '<div class="tag-row">' + App.priorityPill(item.priority) +
              (item.learn_first ? '<span class="chip pink">Learn first</span>' : "") +
            "</div>" +
          "</div>"
        );
      });
      out.push(section("💡", "Recommended skills", miniGrid(cards)));
    }

    if (result.learning_priorities && result.learning_priorities.length) {
      const cards = result.learning_priorities.map(function (item, index) {
        return (
          '<div class="mini-card pink">' +
            '<div class="meta">Step ' + esc(item.order || index + 1) + "</div>" +
            "<h4>" + esc(item.focus) + "</h4>" +
            "<p>" + esc(item.reason) + "</p>" +
            '<div class="tag-row"><span class="chip soft">~' +
              esc(item.estimated_hours) + " hours</span></div>" +
          "</div>"
        );
      });
      out.push(section("📌", "Learning priorities", miniGrid(cards)));
    }

    if (result.thirty_day_plan && result.thirty_day_plan.length) {
      const blocks = result.thirty_day_plan.map(function (block) {
        return (
          '<div class="day-block">' +
            '<div class="day-head">' +
              '<span class="period">' + esc(block.period) + "</span>" +
              "<strong>" + esc(block.focus) + "</strong>" +
              '<span class="chip soft">' + esc(block.estimated_time) + "</span>" +
            "</div>" +
            (block.tasks && block.tasks.length
              ? "<ul>" + block.tasks.map(function (task) {
                  return "<li>" + esc(task) + "</li>";
                }).join("") + "</ul>"
              : "") +
            (block.deliverable
              ? '<p class="deliverable" style="margin:0">Deliverable: ' +
                esc(block.deliverable) + "</p>"
              : "") +
          "</div>"
        );
      }).join("");
      out.push(section("🗓️", "Your 30-day learning plan", blocks));
    }

    if (result.learning_resources && result.learning_resources.length) {
      const cards = result.learning_resources.map(function (item) {
        const url = String(item.url || "");
        const href = /^https?:\/\//i.test(url) ? url : "#";
        return (
          '<div class="mini-card">' +
            '<div class="meta">' + esc(item.type) + " • " + esc(item.provider) + "</div>" +
            "<h4>" + esc(item.title) + "</h4>" +
            "<p>" + esc(item.why) + "</p>" +
            '<a href="' + esc(href) + '" target="_blank" rel="noopener noreferrer">' +
              App.urlLabel(url) + "</a>" +
          "</div>"
        );
      });
      out.push(section("📚", "Learning resources", miniGrid(cards)));
    }

    if (result.project_suggestions && result.project_suggestions.length) {
      const cards = result.project_suggestions.map(function (item) {
        return (
          '<div class="mini-card pink">' +
            '<div class="meta">' + esc(item.difficulty) + "</div>" +
            "<h4>" + esc(item.title) + "</h4>" +
            "<p>" + esc(item.description) + "</p>" +
            '<div class="tag-row">' +
              chips(item.skills_practiced, "soft") +
            "</div>" +
          "</div>"
        );
      });
      out.push(section("🧪", "Project suggestions", miniGrid(cards)));
    }

    out.push(section("⭐", "Career preparation tips", bullets(result.preparation_tips)));
    out.push(section("🎤", "Interview preparation", bullets(result.interview_preparation, true)));
    out.push(section("🚀", "Do these next", bullets(result.next_steps, true)));

    return out.join("");
  }

  return {
    analysis: analysis,
    plan: plan,
    section: section,
    bullets: bullets,
    chips: chips,
    bars: bars,
    scoreRing: scoreRing,
    miniGrid: miniGrid,
  };
})();
