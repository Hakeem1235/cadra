(function () {
  var API_BASE = window.API_BASE || "http://127.0.0.1:8000";
  var SAMPLES = {};
  var currentResult = null;

  function init() {
    loadSamples();
    healthCheck();
    setInterval(healthCheck, 30000);
    document.getElementById("loadSample").addEventListener("change", function (e) {
      loadSample(e.target.value);
    });
    document.getElementById("runBtn").addEventListener("click", runCheck);
    document.getElementById("copyBtn").addEventListener("click", copyReply);
    document.getElementById("toggleJSON").addEventListener("click", toggleJSON);
    document.getElementById("attachment").addEventListener("change", handleFilePick);
  }

  function loadSamples() {
    var sel = document.getElementById("loadSample");
    var d = document.createElement("option");
    d.value = ""; d.textContent = "Load sample request...";
    sel.appendChild(d);
    var xhr = new XMLHttpRequest();
    xhr.open("GET", "samples.json", true);
    xhr.onload = function () {
      if (xhr.status === 200) {
        var data;
        try { data = JSON.parse(xhr.responseText); } catch(e) { return; }
        SAMPLES = data;
        for (var k in data) {
          var o = document.createElement("option");
          o.value = k; o.textContent = k + ": " + data[k].subject.substring(0, 60);
          sel.appendChild(o);
        }
      }
    };
    xhr.send();
  }

  function loadSample(key) {
    if (!key || !SAMPLES[key]) return;
    var s = SAMPLES[key];
    setField("from", s.from);
    setField("subject", s.subject);
    setField("received_at", s.received_at);
    setField("body", s.body);
    var badge = document.getElementById("attachBadge");
    if (s.attachments && s.attachments.length > 0) {
      badge.textContent = s.attachments.length + " file(s)";
    } else {
      badge.textContent = "None";
    }
  }

  function setField(id, val) {
    var el = document.getElementById(id);
    if (el) el.value = val || "";
  }

  function getField(id) {
    var el = document.getElementById(id);
    return el ? el.value : "";
  }

  function handleFilePick(e) {
    var files = e.target.files;
    var badge = document.getElementById("attachBadge");
    if (files && files.length > 0) {
      badge.textContent = files.length + " file(s) selected";
    } else {
      badge.textContent = "None";
    }
  }

  function runCheck() {
    var payload = buildPayload();
    if (!payload) return;
    var btn = document.getElementById("runBtn");
    var loader = document.getElementById("loader");
    btn.disabled = true;
    loader.classList.add("active");
    document.getElementById("resultPane").innerHTML =
      '<div class="empty-state"><div class="loader active"></div></div>';

    var xhr = new XMLHttpRequest();
    xhr.open("POST", API_BASE + "/requests", true);
    xhr.setRequestHeader("Content-Type", "application/json");
    xhr.onload = function () {
      loader.classList.remove("active");
      btn.disabled = false;
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          var data = JSON.parse(xhr.responseText);
          currentResult = data;
          renderResult(data);
        } catch (e) {
          showError("Failed to parse response: " + e.message);
        }
      } else {
        showError("HTTP " + xhr.status + ": " + xhr.responseText);
      }
    };
    xhr.onerror = function () {
      loader.classList.remove("active");
      btn.disabled = false;
      showError("Network error - could not reach " + API_BASE);
    };
    xhr.send(JSON.stringify(payload));
  }

  function buildPayload() {
    var from = getField("from");
    var subject = getField("subject");
    var body = getField("body");
    var received_at = getField("received_at");
    var rid = getField("request_id");
    if (!from || !subject || !body || !received_at) {
      showError("Please fill in from, subject, received_at, and body.");
      return null;
    }
    var payload = {
      request_id: rid || "ui_" + Date.now(),
      received_at: received_at,
      channel: "email",
      from: from,
      subject: subject,
      body: body,
      attachments: []
    };
    return payload;
  }

  function renderResult(data) {
    var pane = document.getElementById("resultPane");
    var outcome = data.outcome || "PEND";
    var outcomeLabel = outcome.replace(/_/g, " ");
    var humanApproval = data.human_approval_required;
    var approverRole = data.approver_role;

    var html = "";

    // Outcome badge
    html += '<div style="display:flex;align-items:center;gap:12px;margin-bottom:8px;">';
    html += '<span class="outcome-badge outcome-' + outcome + '">' + outcomeLabel + "</span>";
    if (data.resolved) {
      var r = data.resolved;
      html += '<span style="font-size:12px;color:#64748b;">';
      if (r.amc_code) html += r.amc_code + " &middot; ";
      if (r.folio_no) html += r.folio_no;
      html += "</span>";
    }
    html += "</div>";

    // Reason codes
    if (data.reason_codes && data.reason_codes.length > 0) {
      html += '<div class="reason-chips">';
      for (var i = 0; i < data.reason_codes.length; i++) {
        html += '<span class="reason-chip">' + data.reason_codes[i] + "</span>";
      }
      html += "</div>";
    }

    // Approval banner
    if (humanApproval) {
      html += '<div class="approval-banner">Human approval required';
      if (approverRole) html += " &mdash; " + approverRole;
      html += "</div>";
    }

    // Checks table
    if (data.checks && data.checks.length > 0) {
      html += '<table class="checks-table"><thead><tr><th>Check</th><th>Result</th><th>Evidence</th></tr></thead><tbody>';
      for (var i = 0; i < data.checks.length; i++) {
        var c = data.checks[i];
        var cid = typeof c === "string" ? c : (c.check_id || "?");
        var res = typeof c === "string" ? "?" : (c.result || "?");
        var evLen = (c.evidence && c.evidence.length) || 0;
        html += "<tr>";
        html += "<td>" + cid + "</td>";
        html += '<td><span class="check-result check-' + res + '">' + res + "</span></td>";
        html += "<td>";
        if (evLen > 0) {
          html +=
            '<button class="evidence-toggle" onclick="toggleEvidence(this)">Show ' +
            evLen +
            " item(s)</button>";
          html += '<div class="evidence-detail">';
          for (var j = 0; j < c.evidence.length; j++) {
            var ev = c.evidence[j];
            html +=
              "<strong>" +
              (ev.source || "?") +
              "</strong> &rarr; " +
              (ev.value || "") +
              (ev.ref ? " <em>(" + ev.ref + ")</em>" : "") +
              "<br>";
          }
          html += "</div>";
        } else {
          html += "&mdash;";
        }
        html += "</td></tr>";
      }
      html += "</tbody></table>";
    }

    // Draft reply card
    if (data.draft_reply && data.draft_reply.body) {
      var dr = data.draft_reply;
      html += '<div class="draft-card">';
      html += '<div class="draft-label">Draft Reply</div>';
      if (dr.to) html += "<div><strong>To:</strong> " + dr.to + "</div>";
      if (dr.subject) html += "<div><strong>Subject:</strong> " + dr.subject + "</div>";
      html += '<div class="draft-body" id="draftBody">' + escapeHtml(dr.body) + "</div>";
      html +=
        '<button class="btn btn-secondary btn-small" id="copyBtn" onclick="window.copyReply()">Copy reply</button>';
      html += "</div>";
    }

    // Trace
    if (data.trace) {
      html += '<details class="trace-panel"><summary>Trace &mdash; ' +
        data.trace.latency_ms + 'ms &middot; $' +
        (data.trace.cost_usd || 0).toFixed(4) +
        "</summary>";
      html += '<div class="trace-content">';
      if (data.trace.tools_called && data.trace.tools_called.length > 0) {
        html += "<div><strong>Tools:</strong> " + data.trace.tools_called.join(", ") + "</div>";
      }
      if (data.trace.documents_used && data.trace.documents_used.length > 0) {
        html += "<div><strong>Docs:</strong></div><ul>";
        for (var i = 0; i < data.trace.documents_used.length; i++) {
          var d = data.trace.documents_used[i];
          html += "<li>" + (d.document || "?") + " v" + (d.version || "?") + "</li>";
        }
        html += "</ul>";
      }
      html += "</div></details>";
    }

    // View raw JSON toggle
    html +=
      '<button class="btn btn-secondary btn-small" onclick="window.toggleJSON()">View raw JSON</button>';
    html += '<div class="json-panel" id="jsonPanel"><pre>' + escapeHtml(JSON.stringify(data, null, 2)) + "</pre></div>";

    pane.innerHTML = html;
  }

  function toggleEvidence(btn) {
    var detail = btn.nextElementSibling;
    if (detail) {
      var open = detail.classList.toggle("open");
      btn.textContent = open ? "Hide evidence" : "Show " + (detail.textContent.length > 0 ? "evidence" : "0 items");
    }
  }

  function toggleJSON() {
    var panel = document.getElementById("jsonPanel");
    if (panel) panel.classList.toggle("open");
  }

  function copyReply() {
    var body = document.getElementById("draftBody");
    if (!body) return;
    var text = body.textContent;
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(function () {
        showToast("Copied!");
      })["catch"](function () {
        fallbackCopy(text);
      });
    } else {
      fallbackCopy(text);
    }
  }

  function fallbackCopy(text) {
    var ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed"; ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.select();
    document.execCommand("copy");
    document.body.removeChild(ta);
    showToast("Copied!");
  }

  function showToast(msg) {
    var t = document.getElementById("toast");
    if (!t) {
      t = document.createElement("div");
      t.id = "toast";
      t.style.cssText = "position:fixed;bottom:24px;left:50%;transform:translateX(-50%);background:#1a1a2e;color:#fff;padding:8px 20px;border-radius:8px;font-size:13px;z-index:999;opacity:0;transition:opacity 0.2s;";
      document.body.appendChild(t);
    }
    t.textContent = msg;
    t.style.opacity = "1";
    setTimeout(function () { t.style.opacity = "0"; }, 2000);
  }

  function healthCheck() {
    var dot = document.getElementById("healthDot");
    dot.className = "health-dot loading";
    var xhr = new XMLHttpRequest();
    xhr.open("GET", API_BASE + "/health", true);
    xhr.timeout = 5000;
    xhr.onload = function () {
      dot.className = xhr.status === 200 ? "health-dot ok" : "health-dot error";
    };
    xhr.onerror = function () {
      dot.className = "health-dot error";
    };
    xhr.send();
  }

  function showError(msg) {
    var pane = document.getElementById("resultPane");
    pane.innerHTML =
      '<div style="padding:20px;border:1px solid #fee2e2;background:#fef2f2;border-radius:8px;color:#991b1b;">' +
      escapeHtml(msg) +
      "</div>";
  }

  function escapeHtml(s) {
    if (!s) return "";
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  window.loadSample = loadSample;
  window.runCheck = runCheck;
  window.renderResult = renderResult;
  window.copyReply = copyReply;
  window.toggleJSON = toggleJSON;
  window.healthCheck = healthCheck;
  window.toggleEvidence = toggleEvidence;
  window.init = init;
})();