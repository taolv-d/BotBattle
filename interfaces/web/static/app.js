const state = {
  session: null,
  snapshot: null,
  review: null,
  events: [],
  lastSequence: 0,
  refreshTimer: null,
  busy: false,
  latestHint: "",
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
  "player_input_timeout",
  "player_input_received",
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

function buildCreatePayload(mode) {
  const payload = {
    mode,
    review_enabled: document.getElementById("reviewEnabled").checked,
    review_mode: document.getElementById("reviewMode").value,
    detect_loopholes: document.getElementById("detectLoopholes").checked,
  };
  if (mode === "player") {
    payload.human_player_id = Number(document.getElementById("humanPlayerId").value || 1);
  }
  return payload;
}

async function createAndStartGame(mode) {
  if (state.busy) return;
  state.busy = true;
  setHint(mode === "observer" ? "正在启动上帝后台..." : "正在启动玩家参与对局...");
  try {
    await api("/api/session", {
      method: "POST",
      body: JSON.stringify(buildCreatePayload(mode)),
    });
    await api("/api/session/start", { method: "POST" });
    state.events = [];
    state.lastSequence = 0;
    setHint("对局已启动。", false);
    await refreshAll();
  } catch (error) {
    setHint(`启动失败：${error.message}`, true);
  } finally {
    state.busy = false;
  }
}

async function joinGame() {
  try {
    await api("/api/session/join", { method: "POST", body: JSON.stringify({}) });
  } catch (error) {
    setHint(`加入游戏暂未开放：${error.message}`, true);
  }
}

async function submitPlayerInput(contentOverride = null) {
  const pending = state.snapshot?.pending_input;
  if (!pending) {
    setHint("当前没有等待中的输入请求。", true);
    return;
  }

  const content = contentOverride !== null ? contentOverride : document.getElementById("playerInputBox").value.trim();
  try {
    await api("/api/input", {
      method: "POST",
      body: JSON.stringify({
        request_id: pending.request_id,
        player_id: state.session?.human_player_id,
        content,
      }),
    });
    setHint("输入已提交，游戏将继续推进。", false);
    document.getElementById("playerInputBox").value = "";
    await refreshAll();
  } catch (error) {
    setHint(`提交失败：${error.message}`, true);
  }
}

async function refreshSession() {
  try {
    state.session = await api("/api/session");
    return true;
  } catch (error) {
    if (error.code === "SESSION_NOT_FOUND") {
      state.session = null;
      state.snapshot = null;
      state.review = null;
      state.events = [];
      state.lastSequence = 0;
      return false;
    }
    throw error;
  }
}

async function refreshState() {
  if (!state.session) return;
  if (state.session.mode === "player") {
    state.snapshot = await api(`/api/state?view_type=player&viewer_player_id=${state.session.human_player_id}`);
  } else {
    state.snapshot = await api("/api/state?view_type=god");
  }
}

async function refreshEvents() {
  if (!state.session) return;
  let path = `/api/events?last_sequence=${state.lastSequence}&limit=200`;
  if (state.session.mode === "player") {
    path += `&view_type=player&viewer_player_id=${state.session.human_player_id}`;
  } else {
    path += "&view_type=god";
  }
  const data = await api(path);
  state.lastSequence = data.last_sequence || state.lastSequence;
  if (data.window_expired) {
    state.events = [];
  }
  state.events.push(...(data.events || []));
  state.events = state.events.slice(-500);
}

async function refreshReview() {
  if (!state.session) return;
  state.review = await api("/api/review");
}

async function refreshAll() {
  try {
    const hasSession = await refreshSession();
    if (!hasSession) {
      showScreen("landingPage");
      renderLanding();
      return;
    }
    await refreshState();
    await refreshEvents();
    await refreshReview();
    renderApp();
  } catch (error) {
    setHint(`刷新失败：${error.message}`, true);
  }
}

function renderApp() {
  if (!state.session) {
    showScreen("landingPage");
    renderLanding();
    return;
  }

  const lifecycle = state.snapshot?.lifecycle_status || state.session.lifecycle_status;
  if (["finished", "review_running", "review_ready"].includes(lifecycle)) {
    showScreen("reviewPage");
    renderReviewPage();
    return;
  }

  showScreen("gamePage");
  renderGamePage();
}

function renderLanding() {
  const hint = document.getElementById("landingHint");
  if (hint && !state.session) {
    hint.textContent = state.latestHint || "";
  }
}

function renderGamePage() {
  const snapshot = state.snapshot || {};
  document.getElementById("sessionId").textContent = state.session?.session_id || "-";
  document.getElementById("gameId").textContent = snapshot.game_id || "-";
  document.getElementById("modeText").textContent = state.session?.mode === "player" ? "玩家参与" : "上帝后台";
  document.getElementById("phaseText").textContent = describePhase(snapshot.phase || "-");
  document.getElementById("dayNightText").textContent = `${snapshot.day_number || 0} / ${snapshot.night_number || 0}`;
  document.getElementById("lifecycleText").textContent = snapshot.lifecycle_status || "-";

  const isPlayer = state.session?.mode === "player";
  document.getElementById("playerSidePanel").style.display = isPlayer ? "block" : "none";
  document.getElementById("observerSidePanel").style.display = isPlayer ? "none" : "block";

  renderChatFeed();
  if (isPlayer) {
    renderAssistant();
  } else {
    renderObserverPanel();
  }
}

function renderChatFeed() {
  const feed = document.getElementById("chatFeed");
  feed.innerHTML = "";
  const entries = buildChatEntries(state.events);
  if (!entries.length) {
    feed.innerHTML = `<div class="empty-box">当前还没有可展示的消息。</div>`;
    return;
  }

  for (const entry of entries) {
    const item = document.createElement("div");
    item.className = `chat-item ${entry.system ? "system" : ""}`;
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
    feed.appendChild(item);
  }
  feed.scrollTop = feed.scrollHeight;
}

function renderAssistant() {
  const pending = state.snapshot?.pending_input;
  const privateInfo = state.snapshot?.private_info;
  const privateBox = document.getElementById("assistantPrivateInfo");
  const stateBox = document.getElementById("assistantState");
  const suggestionBox = document.getElementById("assistantSuggestion");
  const hintBox = document.getElementById("assistantHint");
  const inputBox = document.getElementById("playerInputBox");
  const useBtn = document.getElementById("useSuggestionBtn");
  const submitBtn = document.getElementById("submitInputBtn");

  privateBox.innerHTML = renderPrivateInfo(privateInfo);

  if (!pending) {
    stateBox.innerHTML = `<strong>当前状态</strong><div>游戏正在自动推进，暂时不需要你的输入。</div>`;
    suggestionBox.innerHTML = `<strong>Agent 建议</strong><div class="empty-box">轮到你时，这里会显示 Agent 给出的建议。</div>`;
    hintBox.textContent = state.latestHint || "等待下一次决策节点...";
    inputBox.value = "";
    inputBox.disabled = true;
    useBtn.disabled = true;
    submitBtn.disabled = true;
    inputBox.placeholder = "轮到你时再输入...";
    return;
  }

  const secondsLeft = Math.max(0, pending.expires_at - Date.now() / 1000).toFixed(1);
  stateBox.innerHTML = `
    <strong>${escapeHtml(describeInputType(pending.input_type))}</strong>
    <div>${escapeHtml(pending.prompt || "")}</div>
    <div class="muted">剩余时间：${secondsLeft} 秒</div>
  `;
  suggestionBox.innerHTML = `
    <strong>Agent 建议</strong>
    <div>${escapeHtml(pending.suggestion_label || "-")}</div>
  `;
  hintBox.textContent = state.latestHint || "你可以直接采用建议，也可以自己输入。超时会自动采用 Agent 建议。";
  inputBox.disabled = false;
  useBtn.disabled = false;
  submitBtn.disabled = false;
  inputBox.placeholder = getInputPlaceholder(pending.input_type);
}

function renderObserverPanel() {
  const snapshot = state.snapshot || {};
  const players = snapshot.players || [];
  const aliveCount = players.filter((player) => player.is_alive).length;
  const deadCount = players.length - aliveCount;
  document.getElementById("observerSummary").innerHTML = `
    <strong>运行状态</strong>
    <p>生命周期：${escapeHtml(snapshot.lifecycle_status || "-")}</p>
    <p>阶段：${escapeHtml(describePhase(snapshot.phase || "-"))}</p>
    <p>存活：${aliveCount}，死亡：${deadCount}</p>
    <p>警长：${snapshot.president_id ? `${snapshot.president_id}号` : "无"}</p>
  `;
  document.getElementById("observerPlayers").innerHTML = `
    <strong>玩家状态</strong>
    <ul>${players.map((player) => `<li>${buildAvatar(player.player_id, player)} ${player.player_id}号 ${formatRole(player.role)} ${player.camp || ""} ${player.is_president ? "警长" : ""} ${player.is_alive ? "存活" : "死亡"}</li>`).join("")}</ul>
  `;
  const review = state.review || {};
  document.getElementById("observerReview").innerHTML = `
    <strong>复盘状态</strong>
    <p>状态：${escapeHtml(review.status || "-")}</p>
    <p>报告：${escapeHtml(review.paths?.markdown || "-")}</p>
    <p>错误：${escapeHtml(review.error || "-")}</p>
  `;
}

function renderReviewPage() {
  const result = state.snapshot?.result || {};
  const review = state.review || {};
  document.getElementById("resultSummary").innerHTML = `
    <h3>胜负结果</h3>
    <p>胜利阵营：${escapeHtml(result.winner || "-")}</p>
    <p>结束原因：${escapeHtml(result.reason || "-")}</p>
  `;
  document.getElementById("reviewSummary").innerHTML = `
    <h3>复盘摘要</h3>
    <p>${escapeHtml(review.summary || "复盘尚未生成完成。")}</p>
  `;
  document.getElementById("reviewStatusBox").innerHTML = `
    <p>状态：<span class="status-pill">${escapeHtml(review.status || "-")}</span></p>
    <p>Markdown：${escapeHtml(review.paths?.markdown || "-")}</p>
    <p>JSON：${escapeHtml(review.paths?.json || "-")}</p>
    <p>错误：${escapeHtml(review.error || "-")}</p>
  `;
}

function renderPrivateInfo(privateInfo) {
  if (!privateInfo) {
    return `<strong>你的私有信息</strong><div class="empty-box">当前没有可展示的私有信息。</div>`;
  }

  const lines = [];
  lines.push(`身份：${formatRole(privateInfo.role)}`);
  lines.push(`阵营：${privateInfo.camp || "-"}`);

  if (privateInfo.wolf_teammates?.length) {
    lines.push(`狼人队友：${privateInfo.wolf_teammates.map((item) => `${item.player_id}号${item.is_alive ? "" : "（已死亡）"}`).join("、")}`);
  }
  if (privateInfo.checked_results?.length) {
    lines.push(`查验结果：${privateInfo.checked_results.map((item) => `${item.player_id}号=${formatRole(item.role)}${item.is_alive ? "" : "（已死亡）"}`).join("、")}`);
  }
  if (privateInfo.guarded_players?.length) {
    lines.push(`最近守护：${privateInfo.guarded_players.map((item) => `${item}号`).join("、")}`);
  }
  if (privateInfo.role === "witch") {
    lines.push(`解药：${privateInfo.heal_used ? "已使用" : "未使用"}`);
    lines.push(`毒药：${privateInfo.poison_used ? "已使用" : "未使用"}`);
  }

  return `<strong>你的私有信息</strong><ul>${lines.map((line) => `<li>${escapeHtml(line)}</li>`).join("")}</ul>`;
}

function buildChatEntries(events) {
  const entries = [];
  for (const event of events) {
    if (SPEECH_EVENT_TYPES.has(event.event_type)) {
      const playerId = event.payload?.player_id;
      const player = getPlayerById(playerId);
      entries.push({
        avatar: buildAvatar(playerId, player),
        name: buildPlayerLabel(playerId, player),
        tag: getSpeechTag(event.event_type),
        timestamp: formatTimestamp(event.timestamp),
        content: event.payload?.content || "",
        system: false,
      });
      continue;
    }

    if (!CHAT_SYSTEM_EVENT_TYPES.has(event.event_type)) {
      continue;
    }
    const message = buildSystemMessage(event, events);
    if (!message) {
      continue;
    }
    entries.push({
      avatar: "📢",
      name: "系统消息",
      tag: message.tag,
      timestamp: formatTimestamp(event.timestamp),
      content: message.content,
      system: true,
    });
  }
  return entries;
}

function buildSystemMessage(event, events) {
  const payload = event.payload || {};
  if (event.event_type === "phase_changed") {
    return buildPhaseChangedMessage(payload, events, event.sequence);
  }
  if (event.event_type === "vote_result") {
    if (payload.eliminated) return { tag: "系统播报", content: `${payload.eliminated}号玩家被放逐出局。` };
    if (payload.is_tie) return { tag: "系统播报", content: `投票出现平票，候选玩家为：${formatCandidates(payload.candidates)}。` };
  }
  if (event.event_type === "death") {
    const cause = describeDeathCause(payload.cause);
    return { tag: "系统播报", content: cause ? `${payload.player_id}号玩家死亡，原因：${cause}。` : `${payload.player_id}号玩家死亡。` };
  }
  if (event.event_type === "president_changed") {
    return payload.president_id
      ? { tag: "警长变更", content: `${payload.president_id}号玩家成为警长。` }
      : { tag: "警长变更", content: "当前没有警长。" };
  }
  if (event.event_type === "game_finished") {
    return { tag: "游戏结束", content: `游戏结束，胜利阵营：${payload.winner_camp || payload.winner || "未知"}。` };
  }
  if (event.event_type === "player_input_timeout") {
    return { tag: "系统播报", content: `${payload.player_id}号玩家超时，系统已采用 Agent 建议。` };
  }
  if (event.event_type === "player_input_received") {
    return { tag: "系统播报", content: `${payload.player_id}号玩家已提交输入。` };
  }
  return null;
}

function buildPhaseChangedMessage(payload, events, sequence) {
  const phase = payload.phase;
  const dayNumber = payload.day_number;
  const nightNumber = payload.night_number;
  const details = payload.details || {};

  if (phase === "president_election_speech") return { tag: "系统播报", content: `开始警长竞选发言，参选玩家：${formatCandidates(details.candidates)}。` };
  if (phase === "president_election_vote") return { tag: "系统播报", content: `警长竞选发言结束，开始投票，候选玩家：${formatCandidates(details.candidates)}。` };
  if (phase === "president_election_pk") return { tag: "系统播报", content: `警长竞选进入 PK，候选玩家：${formatCandidates(details.candidates)}。` };
  if (phase === "day_discussion") {
    const nightDeaths = collectNightDeaths(events, sequence);
    if (nightDeaths.length) return { tag: "天亮了", content: `第${dayNumber || "?"}天开始。昨夜死亡玩家：${nightDeaths.map((id) => `${id}号`).join("、")}。` };
    return { tag: "天亮了", content: `第${dayNumber || "?"}天开始。昨夜是平安夜。` };
  }
  if (phase === "day_vote") return { tag: "系统播报", content: `第${dayNumber || "?"}天开始投票。` };
  if (phase === "day_vote_pk") return { tag: "系统播报", content: `投票进入 PK 环节，候选玩家：${formatCandidates(details.candidates)}。` };
  if (phase === "last_words" && details.player_id) return { tag: "系统播报", content: `${details.player_id}号玩家开始发表遗言。` };
  if (phase === "night_guard") return { tag: "入夜了", content: `第${nightNumber || "?"}夜开始，守卫行动。` };
  if (phase === "night_wolf") return { tag: "入夜了", content: `第${nightNumber || "?"}夜，狼人开始行动。` };
  if (phase === "night_witch") return { tag: "入夜了", content: `第${nightNumber || "?"}夜，女巫开始行动。` };
  if (phase === "night_seer") return { tag: "入夜了", content: `第${nightNumber || "?"}夜，预言家开始行动。` };
  if (phase === "hunter_skill") return { tag: "系统播报", content: "猎人技能阶段开始。" };
  if (phase === "game_over") return { tag: "游戏结束", content: "对局结束，正在等待最终结果。" };
  return null;
}

function collectNightDeaths(events, sequence) {
  const deaths = [];
  for (let index = events.length - 1; index >= 0; index -= 1) {
    const event = events[index];
    if (event.sequence >= sequence) continue;
    if (event.event_type === "phase_changed" && event.payload?.phase === "day_discussion") break;
    if (event.event_type === "death" && event.payload?.player_id) deaths.push(event.payload.player_id);
  }
  return [...new Set(deaths)].reverse();
}

function formatCandidates(candidates) {
  const items = Array.isArray(candidates) ? candidates : [];
  if (!items.length) return "暂无";
  return items.map((id) => `${id}号`).join("、");
}

function describeDeathCause(cause) {
  const causeMap = {
    vote_out: "投票放逐",
    wolf_attack: "狼人袭击",
    poison: "女巫毒杀",
    hunter_shot: "猎人开枪",
    self_explode: "狼人自爆",
    duel: "决斗出局",
    same_night_save_conflict: "同守同救冲突",
  };
  return causeMap[String(cause || "").toLowerCase()] || String(cause || "");
}

function getPlayerById(playerId) {
  return (state.snapshot?.players || []).find((player) => player.player_id === playerId) || null;
}

function buildAvatar(playerId, player) {
  const role = player?.role;
  const knownIcons = {
    werewolf: ["🐺", "🐕", "🐻", "🐱"],
    villager: ["🙂", "😊", "😄", "🧑"],
    seer: ["🔮", "✨"],
    witch: ["🧪", "🌿"],
    hunter: ["🎯", "🏹"],
    guard: ["🛡️", "🚪"],
  };
  const unknownIcons = ["😶", "😑", "🫥", "👤", "🧍", "🧍‍♂️"];
  const icons = knownIcons[role] || unknownIcons;
  const index = playerId ? (playerId - 1) % icons.length : 0;
  return icons[index];
}

function buildPlayerLabel(playerId, player) {
  const dead = player && !player.is_alive ? " · 已死亡" : "";
  if (playerId === state.session?.human_player_id) return `${playerId}号玩家（你）${dead}`;
  return `${playerId}号玩家${dead}`;
}

function getSpeechTag(eventType) {
  const tagMap = {
    speech: "白天发言",
    pk_speech: "PK 发言",
    president_candidate_speech: "竞选发言",
    president_pk_speech: "警长 PK",
    last_words: "遗言",
  };
  return tagMap[eventType] || eventType;
}

function describeInputType(inputType) {
  const map = {
    day_speech: "轮到你白天发言",
    last_words: "轮到你发表遗言",
    day_vote: "轮到你投票",
    guard_action: "轮到你守护",
    wolf_action: "轮到你选择狼人目标",
    witch_action: "轮到你使用女巫技能",
    seer_action: "轮到你查验",
    hunter_skill: "轮到你发动猎人技能",
    president_speech: "轮到你竞选警长发言",
    president_vote: "轮到你进行警长投票",
    president_pk_speech: "轮到你进行警长 PK 发言",
  };
  return map[inputType] || inputType;
}

function getInputPlaceholder(inputType) {
  const map = {
    day_speech: "输入你的发言内容...",
    last_words: "输入你的遗言...",
    day_vote: "输入玩家编号，例如 3；或输入 pass 弃票",
    guard_action: "输入守护目标编号；或输入 pass",
    wolf_action: "输入袭击目标编号；或输入 pass",
    witch_action: "输入 save、poison 3、save poison 4 或 pass",
    seer_action: "输入查验目标编号；或输入 pass",
    hunter_skill: "输入带走目标编号；或输入 pass",
    president_speech: "输入你的竞选发言内容...",
    president_vote: "输入候选玩家编号；或输入 pass",
    president_pk_speech: "输入你的 PK 发言内容...",
  };
  return map[inputType] || "输入你的内容...";
}

function describePhase(phase) {
  const map = {
    setup: "准备中",
    president_election_speech: "警长竞选发言",
    president_election_vote: "警长竞选投票",
    president_election_pk: "警长竞选 PK",
    day_discussion: "白天讨论",
    day_vote: "白天投票",
    day_vote_pk: "白天 PK",
    last_words: "遗言",
    night_guard: "守卫行动",
    night_wolf: "狼人行动",
    night_witch: "女巫行动",
    night_seer: "预言家行动",
    hunter_skill: "猎人技能",
    game_over: "游戏结束",
  };
  return map[phase] || phase || "-";
}

function formatRole(role) {
  const map = {
    werewolf: "狼人",
    villager: "村民",
    seer: "预言家",
    witch: "女巫",
    hunter: "猎人",
    guard: "守卫",
  };
  return map[role] || role || "-";
}

function formatTimestamp(timestamp) {
  if (!timestamp) return "-";
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) return timestamp;
  return date.toLocaleTimeString("zh-CN", { hour12: false });
}

function showScreen(screenId) {
  for (const element of document.querySelectorAll(".screen")) {
    element.classList.toggle("active", element.id === screenId);
  }
}

function setHint(message, isError = false) {
  state.latestHint = message;
  const landingHint = document.getElementById("landingHint");
  const assistantHint = document.getElementById("assistantHint");
  for (const hintBox of [landingHint, assistantHint]) {
    if (!hintBox) continue;
    hintBox.textContent = message;
    hintBox.style.color = isError ? "#a2341e" : "";
  }
}

function escapeHtml(text) {
  return String(text || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function restartPolling() {
  if (state.refreshTimer) clearInterval(state.refreshTimer);
  state.refreshTimer = setInterval(refreshAll, 300);
}

document.getElementById("startObserverBtn").addEventListener("click", () => createAndStartGame("observer"));
document.getElementById("startPlayerBtn").addEventListener("click", () => createAndStartGame("player"));
document.getElementById("joinGameBtn").addEventListener("click", joinGame);
document.getElementById("globalRefreshBtn").addEventListener("click", refreshAll);
document.getElementById("useSuggestionBtn").addEventListener("click", () => {
  const pending = state.snapshot?.pending_input;
  if (!pending) return;
  document.getElementById("playerInputBox").value = pending.suggestion_submit_value || "";
  submitPlayerInput(pending.suggestion_submit_value || "");
});
document.getElementById("submitInputBtn").addEventListener("click", () => submitPlayerInput());
document.getElementById("backToLandingBtn").addEventListener("click", () => {
  showScreen("landingPage");
  setHint("当前对局已结束。刷新页面可以重新创建对局。", false);
});

restartPolling();
refreshAll();