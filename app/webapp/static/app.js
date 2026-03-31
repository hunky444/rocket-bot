const tg = window.Telegram?.WebApp;
if (tg) {
  tg.ready();
  tg.expand();
}

const state = {
  userId: null,
  currency: "XTR",
  round: null,
  pollTimer: null,
  animationFrame: null,
  audioContext: null,
  initData: "",
  profile: null,
  defaultAutoCashout: null,
  visual: {
    multiplier: 1,
    rocketX: 0,
    rocketY: 0,
    lastFrame: 0,
    roundReceivedAt: 0,
  },
};

const els = {
  starsBalance: document.getElementById("starsBalance"),
  tonBalance: document.getElementById("tonBalance"),
  multiplier: document.getElementById("multiplier"),
  roundMeta: document.getElementById("roundMeta"),
  statusLine: document.getElementById("statusLine"),
  authBadge: document.getElementById("authBadge"),
  currencyBadge: document.getElementById("currencyBadge"),
  rocket: document.getElementById("rocket"),
  rocketShadow: document.getElementById("rocketShadow"),
  trailMain: document.getElementById("trailMain"),
  trailGlow: document.getElementById("trailGlow"),
  defaultAutoCashout: document.getElementById("defaultAutoCashout"),
  saveDefaultAutoCashout: document.getElementById("saveDefaultAutoCashout"),
  startRound: document.getElementById("startRound"),
  playerName: document.getElementById("playerName"),
  planBadge: document.getElementById("planBadge"),
  profileStats: document.getElementById("profileStats"),
  walletDeposits: document.getElementById("walletDeposits"),
  walletWithdraws: document.getElementById("walletWithdraws"),
  walletStats: document.getElementById("walletStats"),
  walletHistory: document.getElementById("walletHistory"),
  resetWallet: document.getElementById("resetWallet"),
  statsCards: document.getElementById("statsCards"),
  leaderboard: document.getElementById("leaderboard"),
  history: document.getElementById("history"),
  referralCards: document.getElementById("referralCards"),
  referralCode: document.getElementById("referralCode"),
  referralInput: document.getElementById("referralInput"),
  referralList: document.getElementById("referralList"),
  copyReferral: document.getElementById("copyReferral"),
  activateReferral: document.getElementById("activateReferral"),
  chips: [...document.querySelectorAll(".chip")],
  tabs: [...document.querySelectorAll(".top-tab")],
  panels: [...document.querySelectorAll(".tab-panel")],
  flashLayer: document.getElementById("flashLayer"),
  impactRing: document.getElementById("impactRing"),
  crashBanner: document.getElementById("crashBanner"),
  loadingScreen: document.getElementById("loadingScreen"),
  loadingStatus: document.getElementById("loadingStatus"),
  appShell: document.getElementById("appShell"),
  slotInputs: [
    {
      bet: document.getElementById("betAmount1"),
      auto: document.getElementById("autoCashout1"),
      meta: document.getElementById("slotMeta1"),
      status: document.getElementById("slotStatus1"),
      cashout: document.getElementById("cashout1"),
    },
    {
      bet: document.getElementById("betAmount2"),
      auto: document.getElementById("autoCashout2"),
      meta: document.getElementById("slotMeta2"),
      status: document.getElementById("slotStatus2"),
      cashout: document.getElementById("cashout2"),
    },
  ],
};

function resolveUserId() {
  const url = new URL(window.location.href);
  const queryUserId = url.searchParams.get("user_id");
  const tgUserId = tg?.initDataUnsafe?.user?.id;
  return Number(queryUserId || tgUserId || 1);
}

async function api(path, options = {}) {
  const url = new URL(path, window.location.origin);
  if (!state.initData) {
    url.searchParams.set("user_id", state.userId);
  }

  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...(state.initData ? { "X-Telegram-Init-Data": state.initData } : {}),
      ...options.headers,
    },
    ...options,
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "request_failed");
  }
  return data;
}

function formatMoney(amount, currency) {
  return currency === "XTR" ? `${Math.round(amount)} Stars` : `${Number(amount).toFixed(2)} TON`;
}

function formatSignedMoney(amount, currency) {
  const value = currency === "XTR" ? Math.round(amount) : Number(amount).toFixed(2);
  return `${amount >= 0 ? "+" : ""}${value} ${currency === "XTR" ? "Stars" : "TON"}`;
}

function item(title, body) {
  return `<div class="item"><strong>${title}</strong><small>${body}</small></div>`;
}

function statCard(label, value, hint) {
  return `<div class="stat-card"><span>${label}</span><strong>${value}</strong><small>${hint}</small></div>`;
}

function updateStatus(message) {
  els.statusLine.textContent = message;
}

function updateBalances(balances) {
  els.starsBalance.textContent = Math.round(balances.stars);
  els.tonBalance.textContent = Number(balances.ton).toFixed(2);
}

function formulaMultiplier(elapsedSeconds) {
  return 1 + (elapsedSeconds * 0.42) + ((elapsedSeconds ** 1.45) * 0.08);
}

function getDefaultAutoFromProfile(profile) {
  if (!profile) return null;
  return state.currency === "TON" ? profile.user.auto_cashout_ton : profile.user.auto_cashout_xtr;
}

function getSlotDrafts() {
  return els.slotInputs
    .map((slot, index) => ({
      slotIndex: index + 1,
      betAmount: Number(slot.bet.value || 0),
      autoCashout: slot.auto.value ? Number(slot.auto.value) : state.defaultAutoCashout,
    }))
    .filter((slot) => slot.betAmount > 0);
}

function updateCurrencyUI() {
  els.currencyBadge.textContent = state.currency === "TON" ? "TON" : "Stars";
  els.chips.forEach((node) => node.classList.toggle("active", node.dataset.currency === state.currency));
  state.defaultAutoCashout = getDefaultAutoFromProfile(state.profile);
  els.defaultAutoCashout.value = state.defaultAutoCashout ? String(state.defaultAutoCashout) : "";
  if (Number(els.slotInputs[0].bet.value || 0) <= 0) {
    els.slotInputs[0].bet.value = state.currency === "TON" ? "0.5" : "100";
  }
  if (Number(els.slotInputs[1].bet.value || 0) < 0) {
    els.slotInputs[1].bet.value = "0";
  }
}

function renderWalletButtons(wallet) {
  const depositPresets = state.currency === "TON" ? wallet.deposit_presets_ton : wallet.deposit_presets_stars;
  const withdrawPresets = state.currency === "TON" ? wallet.withdraw_presets_ton : wallet.withdraw_presets_stars;
  const currencyLabel = state.currency === "TON" ? "TON" : "Stars";

  els.walletDeposits.innerHTML = depositPresets
    .map((amount) => `<button class="ghost wallet-action" data-action="deposit" data-amount="${amount}">Пополнить на ${amount} ${currencyLabel}</button>`)
    .join("");
  els.walletWithdraws.innerHTML = withdrawPresets
    .map((amount) => `<button class="ghost wallet-action" data-action="withdraw" data-amount="${amount}">Вывести ${amount} ${currencyLabel}</button>`)
    .join("");

  document.querySelectorAll(".wallet-action").forEach((button) => {
    button.addEventListener("click", () => handleWalletAction(button.dataset.action, Number(button.dataset.amount)).catch(handleError));
  });

  const summary = wallet.summary;
  els.walletStats.innerHTML = [
    statCard("Пополнено", `${summary.deposit_total_stars} Stars`, `${summary.deposit_total_ton.toFixed(2)} TON`),
    statCard("Выведено", `${summary.withdraw_total_stars} Stars`, `${summary.withdraw_total_ton.toFixed(2)} TON`),
  ].join("");

  els.walletHistory.innerHTML = wallet.transactions.length
    ? wallet.transactions.map((row) => item(
        `${row.action} • ${formatSignedMoney(row.amount, row.currency)}`,
        `${row.note || "Операция кошелька"} • Баланс после: ${formatMoney(row.balance_after, row.currency)}`
      )).join("")
    : item("Операций еще нет", "Пополнение, вывод и бонусы появятся здесь.");
}

function renderProfile(profile) {
  state.profile = profile;
  state.defaultAutoCashout = getDefaultAutoFromProfile(profile);
  els.defaultAutoCashout.value = state.defaultAutoCashout ? String(state.defaultAutoCashout) : "";
  updateBalances({ stars: profile.user.stars_balance, ton: profile.user.ton_balance });

  const displayName = profile.user.first_name || profile.user.username || `Игрок #${profile.user.telegram_user_id}`;
  els.playerName.textContent = displayName;
  els.planBadge.textContent = String(profile.user.plan || "free").toUpperCase();
  els.authBadge.textContent = profile.auth_mode === "telegram" ? "Auth Telegram" : "Auth DEV";

  els.profileStats.innerHTML = [
    statCard("Stars баланс", `${Math.round(profile.user.stars_balance)}`, "Доступно для ставок и кошелька"),
    statCard("TON баланс", `${Number(profile.user.ton_balance).toFixed(2)}`, "Вторая игровая валюта"),
    statCard("Win Rate", `${profile.stats.win_rate}%`, `${profile.stats.wins_total} побед / ${profile.stats.losses_total} поражений`),
    statCard("Лучший множитель", `${Number(profile.stats.best_multiplier).toFixed(2)}x`, `Всего ставок: ${profile.stats.rounds_total}`),
  ].join("");

  els.statsCards.innerHTML = [
    statCard("Ставок", `${profile.stats.rounds_total}`, `Выплаты: ${profile.stats.payout_stars} Stars / ${Number(profile.stats.payout_ton).toFixed(2)} TON`),
    statCard("Оборот", `${profile.stats.wagered_stars} Stars`, `${Number(profile.stats.wagered_ton).toFixed(2)} TON`),
    statCard("Профит", `${profile.stats.profit_stars} Stars`, `${Number(profile.stats.profit_ton).toFixed(2)} TON`),
    statCard("Средний результат", `${profile.stats.average_profit_stars} Stars`, `${Number(profile.stats.average_profit_ton).toFixed(2)} TON за ставку`),
  ].join("");

  els.history.innerHTML = profile.history.length
    ? profile.history.map((row) => item(
        `Слот ${row.slot_index} • ${row.status.toUpperCase()} • ${formatMoney(row.bet_amount, row.currency)}`,
        `Выход: ${row.exit_multiplier ? `${row.exit_multiplier.toFixed(2)}x` : "boom"} • ${formatSignedMoney(row.profit_amount, row.currency)}`
      )).join("")
    : item("Пока нет ставок", "Сыграй первый раунд, и история появится здесь.");

  els.leaderboard.innerHTML = profile.leaderboard.length
    ? profile.leaderboard.map((row, index) => item(
        `${index + 1}. ${row.name}`,
        `Ставок ${row.rounds_total} • Побед ${row.wins_total} • ${row.profit_stars} Stars • ${Number(row.profit_ton).toFixed(2)} TON`
      )).join("")
    : item("Лидерборд пуст", "Начни играть, чтобы попасть в рейтинг.");

  els.referralCards.innerHTML = [
    statCard("Приглашено", `${profile.referrals.invited_total}`, "Игроков по твоему коду"),
    statCard("Бонусы Stars", `${profile.referrals.earned_stars}`, "Заработано по рефералам"),
    statCard("Бонусы TON", `${Number(profile.referrals.earned_ton).toFixed(2)}`, "Реферальные выплаты"),
    statCard("Код", profile.user.referral_code, "Отправляй друзьям или в чаты"),
  ].join("");
  els.referralCode.textContent = profile.user.referral_code;
  els.referralList.innerHTML = profile.referrals.invited.length
    ? profile.referrals.invited.map((row) => item(
        `${row.invited_name || `Игрок #${row.invited_user_id}`}`,
        `Бонус: ${row.bonus_stars} Stars и ${Number(row.bonus_ton).toFixed(2)} TON`
      )).join("")
    : item("Пока никто не приглашен", "Поделись кодом и активируй рост реферального блока.");

  renderWalletButtons(profile.wallet);
  updateCurrencyUI();
}

function resetStageState() {
  els.flashLayer.classList.remove("active");
  els.impactRing.classList.remove("active");
  els.crashBanner.classList.remove("show");
  els.rocket.classList.remove("exploded");
  document.body.classList.remove("crash-shake");
}

function applyRocketVisual() {
  const x = state.visual.rocketX;
  const y = state.visual.rocketY;
  els.rocket.style.transform = `translate(${x}px, ${-y}px) rotate(-22deg)`;
  els.rocketShadow.style.transform = `translate(${Math.max(0, x * 0.32)}px, 0) scale(${Math.max(0.45, 1 - y / 430)})`;
  els.trailMain.style.width = `${Math.max(120, 140 + x * 0.45)}px`;
  els.trailGlow.style.width = `${Math.max(120, 140 + x * 0.45)}px`;
  els.trailMain.style.transform = `rotate(${-Math.min(42, 12 + y / 10)}deg)`;
  els.trailGlow.style.transform = `rotate(${-Math.min(42, 12 + y / 10)}deg)`;
  els.multiplier.textContent = `${state.visual.multiplier.toFixed(2)}x`;
}

function getPredictedMultiplier() {
  if (!state.round) {
    return 1;
  }
  if (state.round.status === "crashed" || state.round.status === "finished") {
    return state.round.current_multiplier;
  }
  const localElapsed = (performance.now() - state.visual.roundReceivedAt) / 1000;
  const predicted = formulaMultiplier((state.round.elapsed_seconds || 0) + Math.max(0, localElapsed));
  return Math.min(predicted, state.round.crash_multiplier);
}

function animate(timestamp) {
  const lastFrame = state.visual.lastFrame || timestamp;
  const delta = Math.min(32, timestamp - lastFrame);
  state.visual.lastFrame = timestamp;

  const targetMultiplier = getPredictedMultiplier();
  state.visual.multiplier += (targetMultiplier - state.visual.multiplier) * Math.min(1, delta / 150);

  const progress = Math.max(0, state.visual.multiplier - 1);
  const targetX = Math.min(progress * 58, 540);
  const targetY = Math.min(progress * 28 + (progress ** 1.16) * 10, 330);
  state.visual.rocketX += (targetX - state.visual.rocketX) * Math.min(1, delta / 120);
  state.visual.rocketY += (targetY - state.visual.rocketY) * Math.min(1, delta / 120);

  applyRocketVisual();
  state.animationFrame = requestAnimationFrame(animate);
}

function renderSlotCard(index, slot) {
  const card = els.slotInputs[index - 1];
  if (!card) return;

  if (!slot) {
    card.status.textContent = index === 1 ? "Готов" : "Отключен";
    card.meta.textContent = index === 1 ? "Слот ждет ставку" : "Второй слот можно включить отдельной ставкой";
    card.cashout.disabled = true;
    return;
  }

  if (slot.status === "flying") {
    card.status.textContent = "Летит";
    card.meta.textContent = `Ставка ${formatMoney(slot.bet_amount, state.round.currency)} • сейчас ${slot.current_multiplier.toFixed(2)}x`;
    card.cashout.disabled = false;
    return;
  }

  if (slot.status === "cashed_out") {
    card.status.textContent = "Забран";
    card.meta.textContent = `Выплата ${formatMoney(slot.payout_amount, state.round.currency)} на ${slot.current_multiplier.toFixed(2)}x`;
    card.cashout.disabled = true;
    return;
  }

  card.status.textContent = "Сгорел";
  card.meta.textContent = `Краш на ${slot.current_multiplier.toFixed(2)}x • слот проигран`;
  card.cashout.disabled = true;
}

function updateRound(round) {
  state.round = round;
  state.visual.roundReceivedAt = performance.now();
  els.rocket.classList.toggle("boosting", Boolean(round && round.status === "flying"));

  if (!round) {
    els.roundMeta.textContent = "Ожидание нового раунда";
    renderSlotCard(1, null);
    renderSlotCard(2, null);
    return;
  }

  els.roundMeta.textContent = round.status === "crashed"
    ? `Краш на ${Number(round.crash_multiplier).toFixed(2)}x`
    : `Текущий полет • краш на ${Number(round.crash_multiplier).toFixed(2)}x`;

  renderSlotCard(1, round.slots.find((slot) => slot.slot_index === 1));
  renderSlotCard(2, round.slots.find((slot) => slot.slot_index === 2));
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
  const profile = await api("/api/profile");
  renderProfile(profile);
}

async function saveDefaultAutoCashout() {
  const value = els.defaultAutoCashout.value || null;
  const result = await api("/api/preferences/auto-cashout", {
    method: "POST",
    body: JSON.stringify({
      user_id: state.userId,
      currency: state.currency,
      multiplier: value,
    }),
  });

  if (state.profile) {
    if (state.currency === "TON") {
      state.profile.user.auto_cashout_ton = result.multiplier;
    } else {
      state.profile.user.auto_cashout_xtr = result.multiplier;
    }
  }
  state.defaultAutoCashout = result.multiplier;
  updateStatus(result.multiplier ? `Автокэшаут по умолчанию: ${Number(result.multiplier).toFixed(2)}x` : "Автокэшаут отключен.");
}

async function handleWalletAction(action, amount) {
  const payload = {
    user_id: state.userId,
    currency: state.currency,
    action: action === "deposit" ? "add" : "withdraw",
    amount,
  };
  const result = await api("/api/wallet", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  updateBalances(result.balances);
  updateStatus(action === "deposit" ? `Баланс пополнен на ${formatMoney(amount, state.currency)}` : `Вывод выполнен на ${formatMoney(amount, state.currency)}`);
  await refreshProfile();
}

async function resetWallet() {
  const result = await api("/api/wallet", {
    method: "POST",
    body: JSON.stringify({ user_id: state.userId, action: "reset", currency: state.currency, amount: 0 }),
  });
  updateBalances(result.balances);
  updateStatus("Demo-баланс сброшен.");
  await refreshProfile();
}

function stopPolling() {
  if (state.pollTimer) {
    clearInterval(state.pollTimer);
    state.pollTimer = null;
  }
}

async function pollRound() {
  const data = await api("/api/rocket/state");
  updateBalances(data.balances);

  if (!data.round) {
    updateRound(null);
    updateStatus("Раунд завершен. Можно запускать новый.");
    stopPolling();
    await refreshProfile();
    return;
  }

  const previousRound = state.round;
  updateRound(data.round);

  if (data.round.status === "crashed") {
    updateStatus("Ракета взорвалась.");
    if (previousRound?.status !== "crashed") {
      triggerCrashEffects();
    }
    stopPolling();
    await refreshProfile();
    return;
  }

  if (!data.round.slots.some((slot) => slot.status === "flying")) {
    updateStatus("Все слоты завершены.");
    stopPolling();
    await refreshProfile();
    return;
  }

  updateStatus(`Раунд идет. Активных слотов: ${data.round.slots.filter((slot) => slot.status === "flying").length}`);
}

async function startRound() {
  const slots = getSlotDrafts().map((slot) => ({
    bet_amount: slot.betAmount,
    auto_cashout_multiplier: slot.autoCashout,
  }));
  if (!slots.length) {
    throw new Error("add_bet_first");
  }

  resetStageState();
  const data = await api("/api/rocket/start", {
    method: "POST",
    body: JSON.stringify({
      user_id: state.userId,
      currency: state.currency,
      slots,
    }),
  });

  updateBalances(data.balances);
  updateRound(data.round);
  updateStatus("Раунд запущен.");
  stopPolling();
  state.pollTimer = setInterval(() => {
    pollRound().catch(handleError);
  }, 220);
}

async function cashout(slotIndex) {
  const data = await api("/api/rocket/cashout", {
    method: "POST",
    body: JSON.stringify({ user_id: state.userId, slot_index: slotIndex }),
  });

  updateBalances(data.balances);
  if (data.round?.status === "crashed") {
    updateStatus("Поздно, ракета уже взорвалась.");
    triggerCrashEffects();
  } else {
    updateStatus(`Слот ${slotIndex} успешно забран.`);
    triggerCashoutEffects();
  }

  updateRound(data.round || null);
  if (!data.round || !data.round.slots.some((slot) => slot.status === "flying")) {
    stopPolling();
    await refreshProfile();
  }
}

async function activateReferral() {
  const referralCode = els.referralInput.value.trim();
  if (!referralCode) {
    throw new Error("enter_referral_code");
  }
  await api("/api/referrals/activate", {
    method: "POST",
    body: JSON.stringify({ user_id: state.userId, referral_code: referralCode }),
  });
  els.referralInput.value = "";
  updateStatus("Реферальный код активирован.");
  await refreshProfile();
}

function setupCurrencyChips() {
  els.chips.forEach((chip) => {
    chip.addEventListener("click", () => {
      state.currency = chip.dataset.currency;
      updateCurrencyUI();
      updateStatus(`Выбрана валюта ${state.currency === "XTR" ? "Stars" : "TON"}.`);
    });
  });
}

function setupTabs() {
  els.tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      const panelName = tab.dataset.tab;
      els.tabs.forEach((node) => node.classList.toggle("active", node === tab));
      els.panels.forEach((panel) => panel.classList.toggle("active", panel.dataset.panel === panelName));
    });
  });
}

async function copyReferral() {
  const text = state.profile?.referrals?.share_text || state.profile?.user?.referral_code || "";
  if (!text) return;

  try {
    await navigator.clipboard.writeText(text);
  } catch (error) {
    const textarea = document.createElement("textarea");
    textarea.value = text;
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand("copy");
    textarea.remove();
  }

  if (tg?.HapticFeedback?.notificationOccurred) {
    tg.HapticFeedback.notificationOccurred("success");
  }
  updateStatus("Реферальный текст скопирован.");
}

function handleError(error) {
  const messages = {
    add_bet_first: "Добавь хотя бы одну ставку перед стартом.",
    bet_too_small: state.currency === "TON" ? "Минимальная ставка 0.5 TON." : "Минимальная ставка 100 Stars.",
    insufficient_balance: "Недостаточно баланса.",
    active_round: "Сначала заверши текущий раунд.",
    slot_not_available: "Этот слот уже недоступен.",
    invalid_auto_cashout: "Автокэшаут должен быть выше 1.00x.",
    invalid_referral_code: "Неверный реферальный код.",
    referral_not_applied: "Этот код нельзя применить.",
    enter_referral_code: "Введи реферальный код.",
  };
  updateStatus(messages[error.message] || error.message || "Произошла ошибка.");
}

async function init() {
  state.userId = resolveUserId();
  state.initData = tg?.initData || "";
  setupCurrencyChips();
  setupTabs();

  els.saveDefaultAutoCashout.addEventListener("click", () => saveDefaultAutoCashout().catch(handleError));
  els.startRound.addEventListener("click", () => startRound().catch(handleError));
  els.slotInputs[0].cashout.addEventListener("click", () => cashout(1).catch(handleError));
  els.slotInputs[1].cashout.addEventListener("click", () => cashout(2).catch(handleError));
  els.resetWallet.addEventListener("click", () => resetWallet().catch(handleError));
  els.copyReferral.addEventListener("click", () => copyReferral().catch(handleError));
  els.activateReferral.addEventListener("click", () => activateReferral().catch(handleError));

  els.loadingStatus.textContent = state.initData
    ? "Проверяем Telegram initData и загружаем профиль..."
    : "DEV-режим: запускаем мини-апку через браузер...";

  updateCurrencyUI();
  applyRocketVisual();
  state.animationFrame = requestAnimationFrame(animate);

  await refreshProfile();
  updateRound(null);
  els.loadingScreen.classList.add("hidden");
  els.appShell.classList.remove("hidden");
}

init().catch(handleError);
