const state = {
  lastSequence: 0,
  session: null,
  snapshot: null,
  events: [],
};

const SPEECH_EVENT_TYPES = new Set([
  "speech",
  "pk_speech",
  "president_candidate_speech",
  "president_pk_speech",
  "last_words",
]);

const CHAT_SYSTEM_EVENT_TYPES = new Set([
  "phase_changed",
  "vote_result",
  "death",
  "president_changed",
  "game_finished",
]);

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
  if (SPEECH_EVENT_TYPES.has(type)) return "speech";
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

function renderSpeechFeed() {
  const container = document.getElementById("speechFeed");
  container.innerHTML = "";

  const chatEntries = buildChatEntries(state.events);
  if (!chatEntries.length) {
    container.innerHTML = `<div class="chat-empty">${u("\u5f53\u524d\u8fd8\u6ca1\u6709\u53ef\u5c55\u793a\u7684\u804a\u5929\u6d88\u606f\u3002")}</div>`;
    return;
  }

  for (const entry of chatEntries) {
    const item = document.createElement("div");
    item.className = "chat-item";
    item.innerHTML = `
      <div class="chat-avatar">${entry.avatar}</div>
      <div class="chat-main">
        <div class="chat-meta">
          <span class="chat-name">${escapeHtml(entry.name)}</span>
          <span class="chat-tag">${escapeHtml(entry.tag)}</span>
          <span>${escapeHtml(entry.timestamp || "-")}</span>
        </div>
        <div class="chat-bubble">${escapeHtml(entry.content)}</div>
      </div>
    `;
    container.appendChild(item);
  }
}

function buildChatEntries(events) {
  const entries = [];
  for (let index = 0; index < events.length; index += 1) {
    const event = events[index];
    if (SPEECH_EVENT_TYPES.has(event.event_type)) {
      const playerId = event.payload?.player_id;
      const player = getPlayerById(playerId);
      entries.push({
        avatar: buildAvatar(playerId, player),
        name: buildPlayerLabel(playerId, player),
        tag: getSpeechTag(event.event_type),
        timestamp: event.timestamp || "-",
        content: event.payload?.content || "",
      });
      continue;
    }

    if (!CHAT_SYSTEM_EVENT_TYPES.has(event.event_type)) {
      continue;
    }

    const message = buildSystemMessage(event, index, events);
    if (!message) {
      continue;
    }

    entries.push({
      avatar: "\uD83D\uDCE3",
      name: u("\u7cfb\u7edf\u6d88\u606f"),
      tag: message.tag,
      timestamp: event.timestamp || "-",
      content: message.content,
    });
  }
  return entries;
}

function getPlayerById(playerId) {
  return (state.snapshot?.players || []).find((player) => player.player_id === playerId) || null;
}

function buildAvatar(playerId, player) {
  const role = player?.role;
  const iconMap = {
    werewolf: ["\uD83D\uDC3A", "\uD83D\uDC15", "\uD83D\uDC3B", "\uD83D\uDC08"],
    villager: ["\uD83D\uDE42", "\uD83D\uDE0A", "\uD83D\uDE04", "\uD83E\uDDD1"],
    seer: ["\uD83D\uDD2E", "\u2728"],
    witch: ["\uD83E\uDDEA", "\u2697\uFE0F"],
    hunter: ["\uD83D\uDD2B", "\uD83C\uDFF9"],
    guard: ["\uD83D\uDEE1\uFE0F", "\uD83E\uDE96"],
  };
  const icons = iconMap[role] || ["\uD83D\uDC64", "\uD83D\uDC65", "\uD83D\uDC64"];
  const iconIndex = playerId ? (playerId - 1) % icons.length : 0;
  return icons[iconIndex];
}

function buildPlayerLabel(playerId, player) {
  const role = player?.role ? ` ${u("\u00b7")} ${player.role}` : "";
  const dead = player && !player.is_alive ? ` ${u("\u00b7")} ${u("\u5df2\u6b7b\u4ea1")}` : "";
  return `${playerId ?? "?"}${u("\u53f7\u73a9\u5bb6")}${role}${dead}`;
}

function getSpeechTag(eventType) {
  const tagMap = {
    speech: u("\u767d\u5929\u53d1\u8a00"),
    pk_speech: "PK " + u("\u53d1\u8a00"),
    president_candidate_speech: u("\u7ade\u9009\u53d1\u8a00"),
    president_pk_speech: u("\u8b66\u957f PK"),
    last_words: u("\u9057\u8a00"),
  };
  return tagMap[eventType] || eventType;
}

function buildSystemMessage(event, index, events) {
  const payload = event.payload || {};

  if (event.event_type === "phase_changed") {
    return buildPhaseChangedMessage(payload, index, events);
  }

  if (event.event_type === "vote_result") {
    if (payload.eliminated) {
      return {
        tag: u("\u7cfb\u7edf\u64ad\u62a5"),
        content: `${payload.eliminated}${u("\u53f7\u73a9\u5bb6\u88ab\u653e\u9010\u51fa\u5c40\u3002")}`,
      };
    }
    if (payload.is_tie) {
      return {
        tag: u("\u7cfb\u7edf\u64ad\u62a5"),
        content: `${u("\u6295\u7968\u51fa\u73b0\u5e73\u7968\uff0c\u5019\u9009\u73a9\u5bb6\u4e3a\uff1a")}${formatCandidates(payload.candidates)}${u("\u3002")}`,
      };
    }
    return null;
  }

  if (event.event_type === "death") {
    const playerId = payload.player_id;
    if (!playerId) {
      return null;
    }
    const cause = describeDeathCause(payload.cause);
    return {
      tag: u("\u7cfb\u7edf\u64ad\u62a5"),
      content: cause
        ? `${playerId}${u("\u53f7\u73a9\u5bb6\u6b7b\u4ea1\uff0c\u539f\u56e0\uff1a")}${cause}${u("\u3002")}`
        : `${playerId}${u("\u53f7\u73a9\u5bb6\u6b7b\u4ea1\u3002")}`,
    };
  }

  if (event.event_type === "president_changed") {
    if (payload.president_id) {
      return {
        tag: u("\u8b66\u957f\u53d8\u66f4"),
        content: `${payload.president_id}${u("\u53f7\u73a9\u5bb6\u6210\u4e3a\u8b66\u957f\u3002")}`,
      };
    }
    return {
      tag: u("\u8b66\u957f\u53d8\u66f4"),
      content: u("\u5f53\u524d\u6ca1\u6709\u8b66\u957f\u3002"),
    };
  }

  if (event.event_type === "game_finished") {
    const winner = payload.winner_camp || payload.winner || u("\u672a\u77e5");
    return {
      tag: u("\u6e38\u620f\u7ed3\u675f"),
      content: `${u("\u6e38\u620f\u7ed3\u675f\uff0c\u80dc\u5229\u9635\u8425\uff1a")}${winner}${u("\u3002")}`,
    };
  }

  return null;
}

function buildPhaseChangedMessage(payload, index, events) {
  const phase = payload.phase;
  const dayNumber = payload.day_number;
  const nightNumber = payload.night_number;
  const details = payload.details || {};

  if (phase === "president_election_speech") {
    return {
      tag: u("\u7cfb\u7edf\u64ad\u62a5"),
      content: `${u("\u5f00\u59cb\u8b66\u957f\u7ade\u9009\u53d1\u8a00\uff0c\u53c2\u9009\u73a9\u5bb6\uff1a")}${formatCandidates(details.candidates)}${u("\u3002")}`,
    };
  }

  if (phase === "president_election_vote") {
    return {
      tag: u("\u7cfb\u7edf\u64ad\u62a5"),
      content: `${u("\u8b66\u957f\u7ade\u9009\u53d1\u8a00\u7ed3\u675f\uff0c\u5f00\u59cb\u6295\u7968\uff0c\u5019\u9009\u73a9\u5bb6\uff1a")}${formatCandidates(details.candidates)}${u("\u3002")}`,
    };
  }

  if (phase === "president_election_pk") {
    return {
      tag: u("\u7cfb\u7edf\u64ad\u62a5"),
      content: `${u("\u8b66\u957f\u7ade\u9009\u8fdb\u5165 PK\uff0c\u5019\u9009\u73a9\u5bb6\uff1a")}${formatCandidates(details.candidates)}${u("\u3002")}`,
    };
  }

  if (phase === "day_discussion") {
    const nightDeaths = collectNightDeaths(index, events);
    if (nightDeaths.length) {
      return {
        tag: u("\u5929\u4eae\u4e86"),
        content: `${u("\u7b2c")}${dayNumber || "?"}${u("\u5929\u5f00\u59cb\u3002\u6628\u591c\u6b7b\u4ea1\u73a9\u5bb6\uff1a")}${nightDeaths.map((playerId) => `${playerId}${u("\u53f7")}`).join(u("\u3001"))}${u("\u3002")}`,
      };
    }
    return {
      tag: u("\u5929\u4eae\u4e86"),
      content: `${u("\u7b2c")}${dayNumber || "?"}${u("\u5929\u5f00\u59cb\u3002\u6628\u591c\u662f\u5e73\u5b89\u591c\u3002")}`,
    };
  }

  if (phase === "day_vote") {
    return {
      tag: u("\u7cfb\u7edf\u64ad\u62a5"),
      content: `${u("\u7b2c")}${dayNumber || "?"}${u("\u5929\u5f00\u59cb\u6295\u7968\u3002")}`,
    };
  }

  if (phase === "day_vote_pk") {
    return {
      tag: u("\u7cfb\u7edf\u64ad\u62a5"),
      content: `${u("\u6295\u7968\u8fdb\u5165 PK \u73af\u8282\uff0c\u5019\u9009\u73a9\u5bb6\uff1a")}${formatCandidates(details.candidates)}${u("\u3002")}`,
    };
  }

  if (phase === "last_words" && details.player_id) {
    return {
      tag: u("\u7cfb\u7edf\u64ad\u62a5"),
      content: `${details.player_id}${u("\u53f7\u73a9\u5bb6\u5f00\u59cb\u53d1\u8868\u9057\u8a00\u3002")}`,
    };
  }

  if (phase === "night_guard") {
    return {
      tag: u("\u5165\u591c\u4e86"),
      content: `${u("\u7b2c")}${nightNumber || "?"}${u("\u591c\u5f00\u59cb\uff0c\u5b88\u536b\u884c\u52a8\u3002")}`,
    };
  }

  if (phase === "night_wolf") {
    return {
      tag: u("\u5165\u591c\u4e86"),
      content: `${u("\u7b2c")}${nightNumber || "?"}${u("\u591c\uff0c\u72fc\u4eba\u5f00\u59cb\u884c\u52a8\u3002")}`,
    };
  }

  if (phase === "night_witch") {
    return {
      tag: u("\u5165\u591c\u4e86"),
      content: `${u("\u7b2c")}${nightNumber || "?"}${u("\u591c\uff0c\u5973\u5deb\u5f00\u59cb\u884c\u52a8\u3002")}`,
    };
  }

  if (phase === "night_seer") {
    return {
      tag: u("\u5165\u591c\u4e86"),
      content: `${u("\u7b2c")}${nightNumber || "?"}${u("\u591c\uff0c\u9884\u8A00\u5BB6\u5F00\u59CB\u884C\u52A8\u3002")}`,
    };
  }

  if (phase === "hunter_skill" && details.player_id) {
    return {
      tag: u("\u7cfb\u7edf\u64ad\u62a5"),
      content: `${details.player_id}${u("\u53f7\u730E\u4EBA\u53D1\u52A8\u6280\u80FD\u3002")}`,
    };
  }

  if (phase === "game_over") {
    return {
      tag: u("\u6e38\u620f\u7ed3\u675f"),
      content: u("\u5bf9\u5c40\u7ed3\u675f\uff0c\u6b63\u5728\u7b49\u5f85\u6700\u7ec8\u7ed3\u679c\u3002"),
    };
  }

  return null;
}

function collectNightDeaths(currentIndex, events) {
  const deaths = [];
  for (let index = currentIndex - 1; index >= 0; index -= 1) {
    const event = events[index];
    if (event.event_type === "phase_changed" && event.payload?.phase === "day_discussion") {
      break;
    }
    if (event.event_type === "death" && event.payload?.player_id) {
      deaths.push(event.payload.player_id);
    }
  }
  return [...new Set(deaths)].reverse();
}

function formatCandidates(candidates) {
  const items = Array.isArray(candidates) ? candidates : [];
  if (!items.length) {
    return u("\u6682\u65E0");
  }
  return items.map((playerId) => `${playerId}${u("\u53f7")}`).join(u("\u3001"));
}

function describeDeathCause(cause) {
  const causeMap = {
    vote_out: u("\u6295\u7968\u653E\u9010"),
    wolf_attack: u("\u72FC\u4EBA\u88AD\u51FB"),
    poison: u("\u5973\u5DEB\u6BD2\u6740"),
    hunter_shot: u("\u730E\u4EBA\u5F00\u67AA"),
    self_explode: u("\u72FC\u4EBA\u81EA\u7206"),
    duel: u("\u51B3\u6597\u51FA\u5C40"),
    same_night_save_conflict: u("\u540C\u5B88\u540C\u6551\u51B2\u7A81"),
  };
  return causeMap[String(cause || "").toLowerCase()] || String(cause || "");
}

function escapeHtml(text) {
  return String(text || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
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
      renderSpeechFeed();
      renderReview({ status: "-", summary: "-", paths: null, error: null });
      return;
    }
    await refreshState();
    await refreshEvents();
    await refreshReview();
    renderSessionAndState();
    renderEvents();
    renderSpeechFeed();
  } catch (error) {
    renderFatalError(error);
  }
}

function u(value) {
  return value;
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