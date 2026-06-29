let lastEventId = 0;
let actionPending = false;

const state = {
  running: false,
  config: {},
};

const $ = (id) => document.getElementById(id);

function text(value) {
  return String(value ?? "");
}

function setStatus(status) {
  state.running = Boolean(status.running);
  state.config = status.config || state.config;
  $("status-pill").textContent = state.running ? "listening" : "stopped";
  $("status-pill").className = `pill ${state.running ? "ok" : ""}`;
  $("meter").textContent = `RMS ${Number(status.last_rms || 0).toFixed(3)}`;
  if (status.suggestions_language) {
    $("suggestions-language-select").value = status.suggestions_language;
  }
  updateControls();
  renderSettings(status);
}

function updateControls() {
  $("start-btn").disabled = actionPending || state.running;
  $("stop-btn").disabled = actionPending || !state.running;
}

function renderSettings(status) {
  const config = status.config || {};
  const rows = [
    ["Source", config.source_language],
    ["Target", config.target_language],
    ["Speaker", config.speaker_name],
    ["Audio window", `${config.chunk_seconds}s + ${config.audio_overlap_seconds}s overlap`],
    ["Audio queue", `${config.audio_queue_max_chunks} chunks`],
    ["STT", `${config.stt_provider} / ${config.stt_model}`],
    ["Text AI", `${config.text_provider} / ${config.text_model}`],
    ["Base URL", config.base_url],
    ["RAG", config.rag_suggestions ? "on" : "off"],
    ["General advice", config.general_advice ? "on" : "off"],
    ["Suggestions language", status.suggestions_language_label || config.suggestions_language],
    ["Transcript log", config.transcript_log ? status.transcript_log_path || config.transcript_log_dir : "off"],
    ["Knowledge chunks", status.knowledge_chunks],
    ["API key", config.api_key_present ? "present" : "missing"],
  ];
  $("settings").innerHTML = rows
    .map(([key, value]) => `<dt>${escapeHtml(key)}</dt><dd>${escapeHtml(value)}</dd>`)
    .join("");
}

function escapeHtml(value) {
  return text(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function appendEvent(event) {
  lastEventId = Math.max(lastEventId, event.id);
  if (event.kind === "utterance") {
    appendUtterance(event);
    appendSuggestions(event.payload.suggestions || []);
    return;
  }
  appendSystem(event);
}

function appendUtterance(event) {
  const item = document.createElement("article");
  item.className = "event utterance";
  item.innerHTML = `
    <div class="event-time">${new Date(event.created_at).toLocaleTimeString()}</div>
    <div class="original">${escapeHtml(event.payload.original)}</div>
    <div class="translation">${escapeHtml(event.payload.translated)}</div>
  `;
  prependLimited($("events"), item, 80);
}

function appendSystem(event) {
  const item = document.createElement("article");
  item.className = `event ${event.kind}`;
  item.innerHTML = `
    <div class="event-time">${new Date(event.created_at).toLocaleTimeString()}</div>
    <div>${escapeHtml(event.payload.message || event.kind)}</div>
  `;
  prependLimited($("events"), item, 80);
}

function appendSuggestions(suggestions) {
  if (!suggestions.length) {
    return;
  }
  for (const suggestion of suggestions.slice().reverse()) {
    const item = document.createElement("div");
    item.className = `suggestion ${suggestion.mode || "general"}`;
    item.innerHTML = `
      <span>${escapeHtml(suggestion.mode || "ai")}</span>
      <p>${escapeHtml(suggestion.text)}</p>
    `;
    prependLimited($("suggestions"), item, 40);
  }
}

function prependLimited(parent, child, limit) {
  parent.prepend(child);
  while (parent.children.length > limit) {
    parent.removeChild(parent.lastElementChild);
  }
}

async function post(url, payload = null) {
  const options = { method: "POST" };
  if (payload) {
    options.headers = { "Content-Type": "application/json" };
    options.body = JSON.stringify(payload);
  }
  const response = await fetch(url, options);
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

async function refreshStatus() {
  const response = await fetch("/api/status");
  setStatus(await response.json());
}

async function pollEvents() {
  const response = await fetch(`/api/events?after=${lastEventId}`);
  const payload = await response.json();
  for (const event of payload.events || []) {
    appendEvent(event);
  }
}

async function tick() {
  try {
    await refreshStatus();
    await pollEvents();
  } catch (error) {
    console.error(error);
  }
}

$("start-btn").addEventListener("click", async () => {
  if (state.running || actionPending) {
    return;
  }
  actionPending = true;
  updateControls();
  try {
    await post("/api/start");
    await tick();
  } finally {
    actionPending = false;
    updateControls();
  }
});

$("stop-btn").addEventListener("click", async () => {
  if (!state.running || actionPending) {
    return;
  }
  actionPending = true;
  updateControls();
  try {
    await post("/api/stop");
    await tick();
  } finally {
    actionPending = false;
    updateControls();
  }
});

$("clear-conversation-btn").addEventListener("click", () => {
  $("events").innerHTML = "";
});

$("clear-suggestions-btn").addEventListener("click", () => {
  $("suggestions").innerHTML = "";
});

$("suggestions-language-select").addEventListener("change", async (event) => {
  await post("/api/suggestions/language", { language: event.target.value });
  await tick();
});

$("refresh-kb-btn").addEventListener("click", async () => {
  await post("/api/knowledge/refresh");
  await tick();
});

updateControls();
tick();
setInterval(tick, 1200);
