const state = {
  lastSequence: 0,
  session: null,
  snapshot: null,
  events: [],
};

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const payload = await response.json();
  if (!payload.ok) {
    const error = new Error(payload.error?.message || "Request failed");
    error.code = payload.error?.code || "UNKNOWN_ERROR";
    error.category = payload.error?.category || "internal";
    error.details = payload.error?.details || {};
    throw error;
  }
  return payload.data;
}

async function createSession() {
  const payload = {
    mode: document.getElementById("mode").value,
    review_enabled: document.getElementById("reviewEnabled").checked,
    review_mode: document.getElementById("reviewMode").value,
    detect_loopholes: document.getElementById("detectLoopholes").checked,
  };
  const humanPlayerId = document.getElementById("humanPlayerId").value.trim();
  if (humanPlayerId) {
    payload.human_player_id = Number(humanPlayerId);
  }
  await api("/api/session", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  state.lastSequence = 0;
  state.events = [];
  await refreshAll();
}

async function startSession() {
  await api("/api/session/start", { method: "POST" });
  await refreshAll();
}

async function refreshSession() {
  try {
    state.session = await api("/api/session");
    return true;
  } catch (error) {
    if (error.code === "SESSION_NOT_FOUND") {
      state.session = null;
      state.snapshot = null;
      state.events = [];
      state.lastSequence = 0;
      document.getElementById("errorBox").textContent = "No active session yet";
      return false;
    }
    throw error;
  }
}

async function refreshState() {
  state.snapshot = await api("/api/state?view_type=god");
}

async function refreshEvents() {
  const data = await api(`/api/events?last_sequence=${state.lastSequence}&limit=200`);
  state.lastSequence = data.last_sequence || state.lastSequence;
  if (data.window_expired) {
    state.events = [];
  }
  state.events.push(...(data.events || []));
  state.events = state.events.slice(-300);
}

async function refreshReview() {
  const review = await api("/api/review");
  renderReview(review);
}

function renderSessionAndState() {
  const snapshot = state.snapshot;
  const session = state.session;
  if (!snapshot || !session) {
    return;
  }

  document.getElementById("sessionId").textContent = session.session_id || "-";
  document.getElementById("gameId").textContent = snapshot.game_id || "-";
  document.getElementById("lifecycleStatus").textContent = snapshot.lifecycle_status || "-";
  document.getElementById("phase").textContent = snapshot.phase || "-";
  document.getElementById("dayNight").textContent = `${snapshot.day_number || 0} / ${snapshot.night_number || 0}`;
  document.getElementById("presidentId").textContent = snapshot.president_id ?? "-";
  document.getElementById("aliveCount").textContent = (snapshot.alive_player_ids || []).length;

  const tbody = document.getElementById("playersBody");
  tbody.innerHTML = "";
  for (const player of snapshot.players || []) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${player.player_id}</td>
      <td>${player.is_alive ? "Alive" : "Dead"}</td>
      <td>${player.role || "-"}</td>
      <td>${player.camp || "-"}</td>
      <td>${player.is_president ? "Yes" : ""}</td>
    `;
    tbody.appendChild(tr);
  }

  const pending = snapshot.pending_input ? JSON.stringify(snapshot.pending_input, null, 2) : "No pending input";
  const errorText = snapshot.lifecycle_status === "error"
    ? JSON.stringify(snapshot.meta || {}, null, 2)
    : pending;
  document.getElementById("errorBox").textContent = errorText;
}

function classifyEvent(event) {
  const type = event.event_type;
  if (["speech", "pk_speech", "president_candidate_speech", "president_pk_speech", "last_words"].includes(type)) return "speech";
  if (["vote", "vote_result", "president_changed"].includes(type)) return "vote";
  if (["night_action_result", "death"].includes(type)) return "night";
  return "system";
}

function renderEvents() {
  const filter = document.getElementById("eventFilter").value;
  const container = document.getElementById("timeline");
  container.innerHTML = "";
  const events = [...state.events].reverse().filter((event) => filter === "all" || classifyEvent(event) === filter);
  for (const event of events) {
    const div = document.createElement("div");
    div.className = "timeline-item";
    div.innerHTML = `
      <div class="timeline-head">
        <span class="badge">${event.event_type}</span>
        <span class="sequence">#${event.sequence}</span>
      </div>
      <div class="timeline-time">${event.timestamp || "-"}</div>
      <pre>${JSON.stringify(event.payload, null, 2)}</pre>
    `;
    container.appendChild(div);
  }
}

function renderReview(review) {
  const box = document.getElementById("reviewStatus");
  box.innerHTML = `
    <p><strong>Status:</strong> ${review.status || "-"}</p>
    <p><strong>Summary:</strong> ${review.summary || "-"}</p>
    <p><strong>Paths:</strong> ${review.paths ? JSON.stringify(review.paths) : "-"}</p>
    <p><strong>Error:</strong> ${review.error || "-"}</p>
  `;
}

function renderFatalError(error) {
  const detail = error.details && Object.keys(error.details).length
    ? `\n${JSON.stringify(error.details, null, 2)}`
    : "";
  document.getElementById("errorBox").textContent = `${error.message} [${error.code || "UNKNOWN_ERROR"}]${detail}`;
}

async function refreshAll() {
  try {
    const hasSession = await refreshSession();
    if (!hasSession) {
      renderEvents();
      renderReview({ status: "-", summary: "-", paths: null, error: null });
      return;
    }
    await refreshState();
    await refreshEvents();
    await refreshReview();
    renderSessionAndState();
    renderEvents();
  } catch (error) {
    renderFatalError(error);
  }
}

document.getElementById("createBtn").addEventListener("click", createSession);
document.getElementById("startBtn").addEventListener("click", startSession);
document.getElementById("refreshBtn").addEventListener("click", refreshAll);
document.getElementById("eventFilter").addEventListener("change", renderEvents);

document.getElementById("mode").addEventListener("change", (event) => {
  const isPlayer = event.target.value === "player";
  document.getElementById("humanPlayerId").disabled = !isPlayer;
});
document.getElementById("humanPlayerId").disabled = true;

setInterval(refreshAll, 2500);
refreshAll();
