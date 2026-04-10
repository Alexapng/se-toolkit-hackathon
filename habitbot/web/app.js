const state = {
  activeUserId: null,
  activeUserName: "",
  telegramUsername: "",
  habits: [],
  status: null,
  isBusy: false,
};

const DEFAULT_REQUEST_TIMEOUT_MS = 8000;

const refs = {
  currentUserText: document.getElementById("currentUserText"),
  statusDateInput: document.getElementById("statusDateInput"),
  refreshStatusBtn: document.getElementById("refreshStatusBtn"),
  completedCount: document.getElementById("completedCount"),
  totalCount: document.getElementById("totalCount"),
  streakCount: document.getElementById("streakCount"),
  streakMessage: document.getElementById("streakMessage"),
  habitsList: document.getElementById("habitsList"),
  newHabitInput: document.getElementById("newHabitInput"),
  addHabitBtn: document.getElementById("addHabitBtn"),
};

function readTelegramUsername() {
  const telegram = window.Telegram?.WebApp;
  if (!telegram) {
    return null;
  }

  try {
    telegram.ready();
    telegram.expand();
  } catch (_err) {
    // Ignore optional Telegram WebApp API errors.
  }

  const username = String(telegram.initDataUnsafe?.user?.username || "").trim();
  return username || null;
}

function currentDateValue() {
  if (!refs.statusDateInput.value) {
    refs.statusDateInput.value = new Date().toISOString().slice(0, 10);
  }
  return refs.statusDateInput.value;
}

async function request(path, options = {}, timeoutMs = DEFAULT_REQUEST_TIMEOUT_MS) {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);

  let response;
  try {
    response = await fetch(path, { ...options, signal: controller.signal });
  } catch (err) {
    if (err?.name === "AbortError") {
      throw new Error(
        "Request timed out. Check tunnel/backend service, then try again.",
      );
    }
    throw new Error("Network error. Check tunnel/backend service, then try again.");
  } finally {
    window.clearTimeout(timeoutId);
  }

  let payload = {};
  try {
    payload = await response.json();
  } catch (_err) {
    payload = {};
  }

  if (!response.ok) {
    const message = payload.error || `Request failed (${response.status})`;
    throw new Error(message);
  }
  return payload;
}

function setBusy(isBusy) {
  state.isBusy = isBusy;
  const hasUser = Boolean(state.activeUserId);
  refs.newHabitInput.disabled = !hasUser;
  refs.addHabitBtn.disabled = isBusy || !hasUser;
  refs.refreshStatusBtn.disabled = isBusy || !hasUser;
}

function updateCurrentUserText() {
  if (!state.activeUserId) {
    refs.currentUserText.textContent =
      "Open this page from Telegram Mini App. Telegram @username is required.";
    return;
  }

  refs.currentUserText.textContent = `Using Telegram @${state.telegramUsername}`;
}

function renderHabits() {
  refs.habitsList.innerHTML = "";
  const habits = state.habits;
  const statusByHabitId = new Map(
    (state.status?.habits || []).map((item) => [item.habit_id, item.completed]),
  );
  const fallbackCompleted = habits.reduce(
    (count, habit) => count + (statusByHabitId.get(habit.id) ? 1 : 0),
    0,
  );

  const completed = state.status?.summary?.completed_habits ?? fallbackCompleted;
  const total = state.status?.summary?.total_habits ?? habits.length;
  const streakDays = state.status?.streak?.current_streak_days ?? 0;
  const streakMessage =
    state.status?.message || "Keep going. Complete all habits today to build your streak.";

  refs.completedCount.textContent = String(completed);
  refs.totalCount.textContent = String(total);
  refs.streakCount.textContent = `${streakDays} day${streakDays === 1 ? "" : "s"}`;
  refs.streakMessage.textContent = streakMessage;

  if (!state.activeUserId) {
    const empty = document.createElement("p");
    empty.textContent = "Telegram profile is not linked yet.";
    refs.habitsList.appendChild(empty);
    return;
  }

  if (habits.length === 0) {
    const empty = document.createElement("p");
    empty.textContent = "No habits yet. Add your first one below.";
    refs.habitsList.appendChild(empty);
    return;
  }

  for (const habit of habits) {
    const isDone = Boolean(statusByHabitId.get(habit.id));

    const row = document.createElement("div");
    row.className = "habit-row";

    const left = document.createElement("div");
    const title = document.createElement("span");
    title.className = "habit-title";
    title.textContent = habit.name;

    const tag = document.createElement("span");
    tag.className = `tag ${isDone ? "" : "pending"}`.trim();
    tag.textContent = isDone ? "done" : "pending";

    left.appendChild(title);
    left.appendChild(tag);

    const actions = document.createElement("div");
    actions.className = "habit-actions";

    const checkButton = document.createElement("button");
    checkButton.className = "btn";
    checkButton.type = "button";
    checkButton.textContent = isDone ? "Checked in" : "Check in";
    checkButton.disabled = isDone || state.isBusy;
    checkButton.addEventListener("click", async () => {
      try {
        await checkInHabit(habit.id);
      } catch (err) {
        alert(err.message);
      }
    });

    const deleteButton = document.createElement("button");
    deleteButton.className = "btn danger";
    deleteButton.type = "button";
    deleteButton.textContent = "Delete";
    deleteButton.disabled = state.isBusy;
    deleteButton.addEventListener("click", async () => {
      const confirmed = window.confirm(`Delete habit "${habit.name}"?`);
      if (!confirmed) {
        return;
      }
      try {
        await deleteHabit(habit.id);
      } catch (err) {
        alert(err.message);
      }
    });

    actions.appendChild(checkButton);
    actions.appendChild(deleteButton);

    row.appendChild(left);
    row.appendChild(actions);
    refs.habitsList.appendChild(row);
  }
}

async function resolveOrCreateUser(name) {
  const encodedName = encodeURIComponent(name);
  try {
    return await request(`/users/lookup?name=${encodedName}`);
  } catch (err) {
    if (err.message !== "user not found") {
      throw err;
    }
  }

  return request("/users", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
}

async function bootstrapTelegramUser() {
  const telegramUsername = readTelegramUsername();
  if (!telegramUsername) {
    state.activeUserId = null;
    state.activeUserName = "";
    state.telegramUsername = "";
    state.habits = [];
    state.status = null;
    setBusy(false);
    updateCurrentUserText();
    renderHabits();
    return;
  }

  setBusy(true);
  try {
    const user = await resolveOrCreateUser(telegramUsername);
    state.activeUserId = user.id;
    state.activeUserName = user.name;
    state.telegramUsername = telegramUsername;
    updateCurrentUserText();
    await loadDashboard();
  } finally {
    setBusy(false);
  }
}

async function loadDashboard() {
  if (!state.activeUserId) {
    state.habits = [];
    state.status = null;
    renderHabits();
    return;
  }

  const date = currentDateValue();
  const [habitsData, statusData] = await Promise.all([
    request(`/habits?user_id=${state.activeUserId}`),
    request(`/status?user_id=${state.activeUserId}&date=${date}`),
  ]);
  state.habits = habitsData.habits || [];
  state.status = statusData;
  renderHabits();
}

async function addHabit() {
  if (!state.activeUserId) {
    alert("Open this app from Telegram first.");
    return;
  }

  const name = refs.newHabitInput.value.trim();
  if (!name) {
    alert("Enter a habit name first.");
    return;
  }

  setBusy(true);
  try {
    await request("/habits", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: state.activeUserId, name }),
    });
    refs.newHabitInput.value = "";
    await loadDashboard();
  } finally {
    setBusy(false);
  }
}

async function deleteHabit(habitId) {
  if (!state.activeUserId) {
    return;
  }

  let deleted = false;
  setBusy(true);
  try {
    const userId = encodeURIComponent(String(state.activeUserId));
    const encodedHabitId = encodeURIComponent(String(habitId));
    await request(`/habits?user_id=${userId}&habit_id=${encodedHabitId}`, {
      method: "DELETE",
    }, 8000);
    deleted = true;

    // Keep UI responsive even if a follow-up refresh request fails.
    state.habits = state.habits.filter((habit) => habit.id !== habitId);
    if (state.status?.habits) {
      state.status.habits = state.status.habits.filter((habit) => habit.habit_id !== habitId);
    }
  } finally {
    setBusy(false);
  }

  if (!deleted) {
    return;
  }

  // Render once after unlock so habit action buttons are not stuck disabled.
  renderHabits();

  // Refresh in background so buttons/inputs are not locked by network delay.
  loadDashboard().catch((refreshErr) => {
    console.warn("Post-delete refresh failed:", refreshErr);
  });
}

async function checkInHabit(habitId) {
  const date = currentDateValue();
  setBusy(true);
  try {
    await request("/checkins", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ habit_id: habitId, date }),
    });
    await loadDashboard();
  } finally {
    setBusy(false);
  }
}

function bindEvents() {
  refs.addHabitBtn.addEventListener("click", async () => {
    try {
      await addHabit();
    } catch (err) {
      alert(err.message);
    }
  });

  refs.refreshStatusBtn.addEventListener("click", async () => {
    try {
      await loadDashboard();
    } catch (err) {
      alert(err.message);
    }
  });

  refs.statusDateInput.addEventListener("change", async () => {
    try {
      await loadDashboard();
    } catch (err) {
      alert(err.message);
    }
  });

  refs.newHabitInput.addEventListener("keydown", async (event) => {
    if (event.key !== "Enter") {
      return;
    }
    event.preventDefault();
    try {
      await addHabit();
    } catch (err) {
      alert(err.message);
    }
  });
}

async function start() {
  currentDateValue();
  bindEvents();
  renderHabits();
  updateCurrentUserText();

  try {
    await bootstrapTelegramUser();
  } catch (err) {
    alert(err.message);
    setBusy(false);
  }
}

start();
