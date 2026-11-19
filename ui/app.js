// 单页交互：对话 / 采集 / 线索 / 开发信 / 调试 / 配置
const $ = (id) => document.getElementById(id);

const PREFS_KEY = "lead_ui_prefs";
const DEFAULT_PREFS = { refresh: 10000, enter: true, rawOpen: false, start: 1, end: 3 };

function loadPrefs() {
  try {
    return { ...DEFAULT_PREFS, ...JSON.parse(localStorage.getItem(PREFS_KEY) || "{}") };
  } catch (e) {
    return { ...DEFAULT_PREFS };
  }
}
let prefs = loadPrefs();
function savePrefs() {
  localStorage.setItem(PREFS_KEY, JSON.stringify(prefs));
}

// 会话 ID：保存在浏览器，便于短期记忆串起来
let sessionId = localStorage.getItem("lead_session") || "";
if (!sessionId) {
  sessionId = Math.random().toString(36).slice(2, 10);
  localStorage.setItem("lead_session", sessionId);
}

function esc(text) {
  return String(text == null ? "" : text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}
function pct(value) {
  return (Number(value || 0) * 100).toFixed(1) + "%";
}
async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch (e) {
    return false;
  }
}

// ---------------- 标签页 ----------------

function switchTab(name) {
  document.querySelectorAll(".tab").forEach((b) => b.classList.toggle("active", b.dataset.tab === name));
  document.querySelectorAll(".pane").forEach((p) => p.classList.toggle("active", p.id === "pane-" + name));
  if (name === "debug") loadTail();
  if (name === "config") loadConfig();
  if (name === "leads") loadLeads();
}
document.querySelectorAll(".tab").forEach((b) => b.addEventListener("click", () => switchTab(b.dataset.tab)));

// ---------------- 看板 ----------------

async function loadStats() {
  try {
    const resp = await fetch("/api/stats");
    if (!resp.ok) throw new Error("stats " + resp.status);
    const data = await resp.json();

    const leads = data.leads || {};
    $("leads-raw").textContent = leads.raw ?? 0;
    $("leads-clean").textContent = leads.clean ?? 0;
    $("leads-sent").textContent = leads.sent ?? 0;

    const crawl = data.crawl || {};
    const by = crawl.by_status || {};
    $("crawl-total").textContent = crawl.total ?? 0;
    $("crawl-ok").textContent = by.ok ?? 0;
    $("crawl-failed").textContent = (by.failed ?? 0) + (by.blocked_by_robots ?? 0);
    $("crawl-last").textContent = crawl.last_ts || "—";
    const fails = crawl.recent_failed || [];
    $("crawl-fail").innerHTML = fails.length
      ? fails.map((f) => `<li>${esc(f.url || "-")}<b>${esc(f.error || f.status || "失败")}</b></li>`).join("")
      : '<li class="muted">暂无记录</li>';

    const mail = data.mail || {};
    $("mail-sent").textContent = mail.sent ?? 0;
    $("mail-replied").textContent = mail.replied ?? 0;
    $("mail-rate").textContent = pct(mail.reply_rate);

    $("conn-badge").textContent = "已连接";
    $("conn-badge").className = "badge on";
  } catch (err) {
    $("conn-badge").textContent = "未连接";
    $("conn-badge").className = "badge off";
  }
}

async function loadLeads() {
  const tbody = $("leads-table").querySelector("tbody");
  try {
    const resp = await fetch("/api/leads?limit=20");
    const data = await resp.json();
    const rows = data.leads || [];
    if (!rows.length) {
      tbody.innerHTML = '<tr><td colspan="4" class="empty">暂无数据：先抓取或上传线索表</td></tr>';
      return;
    }
    tbody.innerHTML = rows
      .map(
        (row) =>
          `<tr><td>${esc(row.company) || "—"}</td><td>${esc(row.website) || "—"}</td>` +
          `<td>${esc(row.contact_email) || "—"}</td><td>${esc(row.email_status) || "unknown"}</td></tr>`
      )
      .join("");
  } catch (err) {
    tbody.innerHTML = '<tr><td colspan="4" class="empty">读取失败</td></tr>';
  }
}

// ---------------- 对话 ----------------

function addMsg(text, role) {
  const div = document.createElement("div");
  div.className = "msg " + role;
  div.textContent = text;
  $("chat-log").appendChild(div);
  $("chat-log").scrollTop = $("chat-log").scrollHeight;
  return div;
}

function renderSteps(trace, agent) {
  const box = $("step-bar");
  const head = `<span class="muted">智能体：${esc(agent || "-")}</span>`;
  if (!trace || !trace.length) {
    box.innerHTML = head + '<span class="muted">｜无工具调用</span>';
    return;
  }
  box.innerHTML =
    head +
    trace
      .map((step) =>
        step.action === "route"
          ? `<span class="step route">路由 → ${esc(step.result)}</span>`
          : `<span class="step ${step.ok === false ? "bad" : ""}">${step.ok === false ? "✗" : "✓"} ${esc(step.action)}</span>`
      )
      .join("");
}

let lastCall = null;

function renderDebug() {
  if (!lastCall) {
    $("dbg-time").textContent = "—";
    $("dbg-ms").textContent = "—";
    $("dbg-agent").textContent = "—";
    $("dbg-session").textContent = sessionId;
    $("trace-table").querySelector("tbody").innerHTML = '<tr><td colspan="4" class="empty">还没有调用</td></tr>';
    $("raw-box").textContent = "—";
    return;
  }
  $("dbg-time").textContent = lastCall.ts;
  $("dbg-ms").textContent = lastCall.ms + " ms";
  $("dbg-agent").textContent = lastCall.agent || "—";
  $("dbg-session").textContent = sessionId;

  const trace = (lastCall.data && lastCall.data.trace) || [];
  const tbody = $("trace-table").querySelector("tbody");
  tbody.innerHTML = trace.length
    ? trace
        .map(
          (s, i) =>
            `<tr><td>${i + 1}</td><td><code>${esc(s.action)}</code></td>` +
            `<td class="${s.ok === false ? "bad" : "ok"}">${s.ok === false ? "失败" : "成功"}</td>` +
            `<td><details><summary>查看</summary><pre>${esc(
              JSON.stringify({ args: s.args, result: s.result }, null, 2)
            )}</pre></details></td></tr>`
        )
        .join("")
    : '<tr><td colspan="4" class="empty">无工具调用</td></tr>';

  $("raw-box").textContent = JSON.stringify(lastCall.data, null, 2);
  $("raw-box").classList.toggle("hidden", !prefs.rawOpen);
  $("toggle-raw").textContent = prefs.rawOpen ? "收起" : "展开";
}

async function ask(text) {
  if (!text.trim()) return;
  addMsg(text, "user");
  const pending = addMsg("思考中…", "bot pending");
  $("send-btn").disabled = true;
  const t0 = performance.now();

  try {
    const resp = await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, session_id: sessionId }),
    });
    const data = await resp.json();
    const ms = Math.round(performance.now() - t0);
    pending.remove();
    if (!resp.ok) throw new Error(data.detail || "HTTP " + resp.status);

    addMsg(data.answer || "（无回答）", "bot");
    $("agent-badge").textContent = data.agent || "agent";
    renderSteps(data.trace, data.agent);
    lastCall = { ts: new Date().toLocaleTimeString(), ms, agent: data.agent, data };
    renderDebug();
    if (data.agent === "outreach" || text.includes("开发信")) {
      $("draft-box").textContent = data.answer || "";
    }
  } catch (err) {
    pending.remove();
    addMsg("请求失败：" + err.message, "bot error");
  } finally {
    $("send-btn").disabled = false;
    loadStats();
  }
}

// ---------------- 采集 / 上传 ----------------

$("chat-form").addEventListener("submit", (e) => {
  e.preventDefault();
  const input = $("chat-input");
  const text = input.value;
  input.value = "";
  ask(text);
});

$("chat-input").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !prefs.enter) e.preventDefault();
});

$("gen-form").addEventListener("submit", (e) => {
  e.preventDefault();
  const base = $("base-url").value.trim();
  const pattern = $("list-pattern").value.trim();
  const start = Math.max(1, Number($("gen-start").value) || 1);
  const end = Math.max(start, Number($("gen-end").value) || start);
  if (!base) {
    $("base-url").focus();
    return;
  }
  switchTab("chat");
  ask(`为 ${base} 生成第 ${start} 到 ${end} 页的待抓 URL，分页规则是 ${pattern || "（无，取首页）"}，只生成不抓取。`);
});

$("upload-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const file = $("upload-file").files[0];
  if (!file) return;
  const form = new FormData();
  form.append("file", file);
  try {
    const resp = await fetch("/api/upload", { method: "POST", body: form });
    const data = await resp.json();
    $("upload-hint").textContent = `已上传 ${data.filename}（${data.size} 字节）`;
    loadStats();
  } catch (err) {
    $("upload-hint").textContent = "上传失败：" + err.message;
  }
});

// ---------------- 调试 ----------------

async function loadTail() {
  const box = $("tail-box");
  try {
    const resp = await fetch("/api/debug/tail?n=30");
    const data = await resp.json();
    const events = data.events || [];
    box.textContent = events.length ? events.map((e) => JSON.stringify(e)).join("\n") : "暂无遥测记录";
  } catch (err) {
    box.textContent = "读取失败：" + err.message;
  }
}

$("toggle-raw").addEventListener("click", () => {
  prefs.rawOpen = !prefs.rawOpen;
  savePrefs();
  $("cfg-raw").checked = prefs.rawOpen;
  renderDebug();
});

$("copy-json").addEventListener("click", async () => {
  if (!lastCall) return;
  const ok = await copyText(JSON.stringify(lastCall.data, null, 2));
  $("copy-json").textContent = ok ? "已复制" : "复制失败";
  setTimeout(() => ($("copy-json").textContent = "复制 JSON"), 1200);
});

$("clear-debug").addEventListener("click", () => {
  lastCall = null;
  renderDebug();
  $("tail-box").textContent = "—";
});

$("clear-chat").addEventListener("click", () => {
  $("chat-log").innerHTML =
    '<div class="msg bot">对话已清空。试试输入「走一遍全流程」。</div>';
  $("step-bar").innerHTML = '<span class="muted">暂无工具调用</span>';
});

// ---------------- 配置 ----------------

const ENV_KEYS = [
  "LLM_MODEL",
  "LLM_BASE_URL",
  "AGENT_PERMISSION_MODE",
  "TOOL_NET_POLICY",
  "TOOL_NET_ALLOWLIST",
  "MAX_TOOL_CALLS",
  "DAILY_MAIL_LIMIT",
  "DRY_RUN_MAIL",
];

async function loadConfig() {
  try {
    const resp = await fetch("/api/config");
    const data = await resp.json();
    const env = data.env || {};
    const form = $("env-form");
    ENV_KEYS.forEach((k) => {
      const el = form.elements[k];
      if (el && env[k] !== undefined) el.value = env[k];
    });
    $("env-hint").textContent =
      (env.LLM_API_KEY_SET ? "已检测到 LLM_API_KEY。" : "未检测到 LLM_API_KEY，当前走规则兜底。") +
      "保存后重启服务生效。";
  } catch (err) {
    $("env-hint").textContent = "读取后端配置失败：" + err.message;
  }
}

$("env-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.target;
  const values = {};
  ENV_KEYS.forEach((k) => {
    if (form.elements[k]) values[k] = form.elements[k].value;
  });
  try {
    const resp = await fetch("/api/config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ values }),
    });
    const data = await resp.json();
    const changed = [...(data.updated || []), ...(data.added || [])];
    $("env-hint").textContent = changed.length
      ? `已写入：${changed.join(", ")}。重启服务后生效。`
      : "没有变化。";
  } catch (err) {
    $("env-hint").textContent = "保存失败：" + err.message;
  }
});

function applyPrefsToUI() {
  $("cfg-refresh").value = String(prefs.refresh);
  $("cfg-enter").checked = !!prefs.enter;
  $("cfg-raw").checked = !!prefs.rawOpen;
  $("cfg-start").value = prefs.start;
  $("cfg-end").value = prefs.end;
  $("gen-start").value = prefs.start;
  $("gen-end").value = prefs.end;
  $("cfg-session").value = sessionId;
  $("raw-box").classList.toggle("hidden", !prefs.rawOpen);
  $("toggle-raw").textContent = prefs.rawOpen ? "收起" : "展开";
}

let refreshTimer = null;
function startAutoRefresh() {
  if (refreshTimer) clearInterval(refreshTimer);
  if (prefs.refresh > 0) refreshTimer = setInterval(loadStats, prefs.refresh);
}

$("cfg-refresh").addEventListener("change", (e) => {
  prefs.refresh = Number(e.target.value) || 0;
  savePrefs();
  startAutoRefresh();
});
$("cfg-enter").addEventListener("change", (e) => {
  prefs.enter = e.target.checked;
  savePrefs();
});
$("cfg-raw").addEventListener("change", (e) => {
  prefs.rawOpen = e.target.checked;
  savePrefs();
  renderDebug();
});
$("cfg-start").addEventListener("change", (e) => {
  prefs.start = Math.max(1, Number(e.target.value) || 1);
  $("gen-start").value = prefs.start;
  savePrefs();
});
$("cfg-end").addEventListener("change", (e) => {
  prefs.end = Math.max(1, Number(e.target.value) || 1);
  $("gen-end").value = prefs.end;
  savePrefs();
});
$("copy-session").addEventListener("click", async () => {
  const ok = await copyText(sessionId);
  $("copy-session").textContent = ok ? "已复制" : "复制失败";
  setTimeout(() => ($("copy-session").textContent = "复制"), 1200);
});
$("reset-session").addEventListener("click", () => {
  sessionId = Math.random().toString(36).slice(2, 10);
  localStorage.setItem("lead_session", sessionId);
  $("cfg-session").value = sessionId;
});

// ---------------- 其他按钮 ----------------

$("draft-btn").addEventListener("click", () => {
  switchTab("chat");
  ask("为第一条有效线索写一封开发信");
});
$("refresh-leads").addEventListener("click", loadLeads);
$("refresh-crawl").addEventListener("click", loadStats);
$("refresh-tail").addEventListener("click", loadTail);

// ---------------- 初始化 ----------------

applyPrefsToUI();
renderDebug();
loadStats();
loadLeads();
startAutoRefresh();
