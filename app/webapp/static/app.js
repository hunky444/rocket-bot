const tg = window.Telegram?.WebApp;
if (tg) {
  tg.ready();
  tg.expand();
}

const state = {
  userId: null,
  currency: "XTR",
  round: null,
  timer: null,
  audioContext: null,
  initData: "",
};

const els = {
  starsBalance: document.getElementById("starsBalance"),
  tonBalance: document.getElementById("tonBalance"),
  multiplier: document.getElementById("multiplier"),
  statusLine: document.getElementById("statusLine"),
  authBadge: document.getElementById("authBadge"),
  rocket: document.getElementById("rocket"),
  betAmount: document.getElementById("betAmount"),
  autoCashout: document.getElementById("autoCashout"),
  autoCashoutBadge: document.getElementById("autoCashoutBadge"),
  startRound: document.getElementById("startRound"),
  cashout: document.getElementById("cashout"),
  profileStats: document.getElementById("profileStats"),
  leaderboard: document.getElementById("leaderboard"),
  history: document.getElementById("history"),
  chips: [...document.querySelectorAll(".chip")],
  flashLayer: document.getElementById("flashLayer"),
  impactRing: document.getElementById("impactRing"),
  crashBanner: document.getElementById("crashBanner"),
  stage: document.getElementById("stage"),
  loadingScreen: document.getElementById("loadingScreen"),
  loadingStatus: document.getElementById("loadingStatus"),
  appShell: document.getElementById("appShell"),
};

function resolveUserId() {
  const url = new URL(window.location.href);
  const queryUserId = url.searchParams.get("user_id");
  const tgUserId = tg?.initDataUnsafe?.user?.id;
  return Number(queryUserId || tgUserId || 1);
}

async function api(path, options = {}) {
  const url = new URL(path, window.location.origin);
  if (!state.initData) url.searchParams.set("user_id", state.userId);
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...(state.initData ? { "X-Telegram-Init-Data": state.initData } : {}),
      ...options.headers,
    },
    ...options,
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "request_failed");
  return data;
}

function item(title, body) {
  return `<div class="item">${title}<small>${body}</small></div>`;
}

function formatMoney(amount, currency) {
  return currency === "XTR" ? `${Math.round(amount)} Stars` : `${Number(amount).toFixed(2)} TON`;
}

function formatSignedMoney(amount, currency) {
  const num = currency === "XTR" ? Math.round(amount) : Number(amount).toFixed(2);
  return `${amount >= 0 ? "+" : ""}${num} ${currency === "XTR" ? "Stars" : "TON"}`;
}

function renderBalances(balances) {
  els.starsBalance.textContent = balances.stars;
  els.tonBalance.textContent = Number(balances.ton).toFixed(2);
}

function renderProfile(data) {
  els.authBadge.textContent = data.auth_mode === "telegram" ? "Auth Telegram" : "Auth DEV";
  els.profileStats.innerHTML = [
    item(`Раунды: <b>${data.stats.rounds_total}</b>`, `Wins ${data.stats.wins_total} / Losses ${data.stats.losses_total}`),
    item(`Лучший x: <b>${Number(data.stats.best_multiplier).toFixed(2)}</b>`, `Профит: ${data.stats.profit_stars} Stars / ${Number(data.stats.profit_ton).toFixed(2)} TON`),
    item(`Auto Stars: <b>${data.user.auto_cashout_xtr ? Number(data.user.auto_cashout_xtr).toFixed(2) + "x" : "OFF"}</b>`, `Auto TON: ${data.user.auto_cashout_ton ? Number(data.user.auto_cashout_ton).toFixed(2) + "x" : "OFF"}`),
  ].join("");

  els.history.innerHTML = data.history.length
    ? data.history.map((row) => item(
        `${row.status} • <b>${formatMoney(row.bet_amount, row.currency)}</b>`,
        `Выход ${row.exit_multiplier ? row.exit_multiplier.toFixed(2) + "x" : "boom"} • ${formatSignedMoney(row.profit_amount, row.currency)}`
      )).join("")
    : item("Пока нет раундов", "Сыграй первый раунд");

  els.leaderboard.innerHTML = data.leaderboard.length
    ? data.leaderboard.map((row, index) => item(
        `${index + 1}. <b>${row.name}</b>`,
        `Раунды ${row.rounds_total} • Wins ${row.wins_total} • ${row.profit_stars} Stars • ${Number(row.profit_ton).toFixed(2)} TON • best ${Number(row.best_multiplier).toFixed(2)}x`
      )).join("")
    : item("Лидерборд пуст", "Сыграй первый раунд");

  const preferred = state.currency === "TON" ? data.user.auto_cashout_ton : data.user.auto_cashout_xtr;
  els.autoCashout.value = preferred ? String(preferred) : "";
  updateAutoBadge(preferred);
}

function updateAutoBadge(value) {
  els.autoCashoutBadge.textContent = value ? `Auto ${Number(value).toFixed(2)}x` : "Auto OFF";
}

function resetStageState() {
  els.flashLayer.classList.remove("active");
  els.impactRing.classList.remove("active");
  els.crashBanner.classList.remove("show");
  els.rocket.classList.remove("exploded");
  document.body.classList.remove("crash-shake");
}

function updateRocket(round) {
  if (!round) return;
  const x = Math.min((round.current_multiplier - 1) * 28, 290);
  const y = Math.min((round.current_multiplier - 1) * 20, 205);
  els.rocket.style.transform = `translate(${x}px, ${-y}px) rotate(-18deg)`;
  els.rocket.classList.toggle("boosting", round.status === "flying");
  els.multiplier.textContent = `${round.current_multiplier.toFixed(2)}x`;
  updateAutoBadge(round.auto_cashout_multiplier);
}

function triggerCrashEffects() {
  els.flashLayer.classList.add("active");
  els.impactRing.classList.remove("active");
  void els.impactRing.offsetWidth;
  els.impactRing.classList.add("active");
  els.crashBanner.classList.add("show");
  els.rocket.classList.add("exploded");
  document.body.classList.add("crash-shake");
  playCrashSound();
  if (navigator.vibrate) navigator.vibrate([90, 40, 140]);
  if (tg?.HapticFeedback?.impactOccurred) tg.HapticFeedback.impactOccurred("heavy");
  setTimeout(() => {
    els.flashLayer.classList.remove("active");
    document.body.classList.remove("crash-shake");
  }, 320);
}

function triggerCashoutEffects() {
  if (tg?.HapticFeedback?.notificationOccurred) tg.HapticFeedback.notificationOccurred("success");
  playCashoutSound();
}

function ensureAudioContext() {
  if (!state.audioContext) {
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (AudioCtx) state.audioContext = new AudioCtx();
  }
  return state.audioContext;
}

function playTone({ frequency, duration, type, gain, rampTo = 0.001 }) {
  const ctx = ensureAudioContext();
  if (!ctx) return;
  const osc = ctx.createOscillator();
  const amp = ctx.createGain();
  osc.type = type;
  osc.frequency.value = frequency;
  amp.gain.value = gain;
  osc.connect(amp);
  amp.connect(ctx.destination);
  const now = ctx.currentTime;
  osc.start(now);
  amp.gain.exponentialRampToValueAtTime(rampTo, now + duration);
  osc.stop(now + duration);
}

function playCrashSound() {
  playTone({ frequency: 140, duration: 0.35, type: "sawtooth", gain: 0.12 });
  setTimeout(() => playTone({ frequency: 68, duration: 0.42, type: "triangle", gain: 0.08 }), 50);
}

function playCashoutSound() {
  playTone({ frequency: 540, duration: 0.12, type: "triangle", gain: 0.08 });
  setTimeout(() => playTone({ frequency: 780, duration: 0.15, type: "triangle", gain: 0.06 }), 90);
}

async function refreshProfile() {
  const data = await api("/api/profile");
  renderBalances({ stars: data.user.stars_balance, ton: data.user.ton_balance });
  renderProfile(data);
}

async function saveAutoCashout() {
  const value = els.autoCashout.value || null;
  await api("/api/preferences/auto-cashout", {
    method: "POST",
    body: JSON.stringify({
      user_id: state.userId,
      currency: state.currency,
      multiplier: value,
    }),
  });
  updateAutoBadge(value);
}

async function pollRound() {
  const data = await api("/api/rocket/state");
  renderBalances(data.balances);
  if (!data.round) {
    state.round = null;
    els.statusLine.textContent = "Раунд завершен. Можно начинать заново.";
    clearInterval(state.timer);
    state.timer = null;
    await refreshProfile();
    return;
  }

  state.round = data.round;
  updateRocket(data.round);
  if (data.round.status === "cashed_out") {
    els.statusLine.textContent = "Кэш-аут выполнен.";
    triggerCashoutEffects();
    clearInterval(state.timer);
    state.timer = null;
    await refreshProfile();
    return;
  }
  if (data.round.status === "crashed") {
    els.statusLine.textContent = "Ракета взорвалась.";
    triggerCrashEffects();
    clearInterval(state.timer);
    state.timer = null;
    await refreshProfile();
    return;
  }
  els.statusLine.textContent = `Раунд идет. Потенциал: ${formatMoney(data.round.bet_amount * data.round.current_multiplier, data.round.currency)}`;
}

async function startRound() {
  resetStageState();
  const payload = {
    user_id: state.userId,
    currency: state.currency,
    bet_amount: Number(els.betAmount.value),
    auto_cashout_multiplier: els.autoCashout.value || null,
  };
  const data = await api("/api/rocket/start", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  state.round = data.round;
  renderBalances(data.balances);
  updateRocket(data.round);
  els.statusLine.textContent = "Ракета запущена.";
  clearInterval(state.timer);
  state.timer = setInterval(() => {
    pollRound().catch((error) => {
      els.statusLine.textContent = error.message;
      clearInterval(state.timer);
      state.timer = null;
    });
  }, 850);
}

async function cashout() {
  const data = await api("/api/rocket/cashout", {
    method: "POST",
    body: JSON.stringify({ user_id: state.userId }),
  });
  renderBalances(data.balances);
  if (data.round) {
    updateRocket(data.round);
    if (data.round.status === "crashed") {
      els.statusLine.textContent = "Поздно, ракета взорвалась.";
      triggerCrashEffects();
    } else {
      els.statusLine.textContent = "Выигрыш забран.";
      triggerCashoutEffects();
    }
  }
  clearInterval(state.timer);
  state.timer = null;
  await refreshProfile();
}

function setupCurrencyChips() {
  els.chips.forEach((chip) => {
    chip.addEventListener("click", async () => {
      state.currency = chip.dataset.currency;
      els.chips.forEach((node) => node.classList.toggle("active", node === chip));
      els.betAmount.value = state.currency === "XTR" ? "100" : "0.5";
      await refreshProfile();
    });
  });
}

async function init() {
  state.userId = resolveUserId();
  state.initData = tg?.initData || "";
  setupCurrencyChips();
  els.autoCashout.addEventListener("change", () => saveAutoCashout().catch((error) => {
    els.statusLine.textContent = error.message;
  }));
  els.startRound.addEventListener("click", () => startRound().catch((error) => {
    els.statusLine.textContent = error.message;
  }));
  els.cashout.addEventListener("click", () => cashout().catch((error) => {
    els.statusLine.textContent = error.message;
  }));
  els.loadingStatus.textContent = state.initData
    ? "Проверяем Telegram initData и загружаем профиль…"
    : "DEV-режим: запускаем локальную мини-апку…";
  await refreshProfile();
  els.loadingScreen.classList.add("hidden");
  els.appShell.classList.remove("hidden");
}

init().catch((error) => {
  els.statusLine.textContent = error.message;
});
