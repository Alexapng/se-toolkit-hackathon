const USER_NAME_KEY = "habitbot_user_name";

const state = {
  activeUserId: null,
  activeUserName: "",
  habits: [],
  status: null,
};

const refs = {
  userNameInput: document.getElementById("userNameInput"),
  useNameBtn: document.getElementById("useNameBtn"),
  currentUserText: document.getElementById("currentUserText"),
  statusDateInput: document.getElementById("statusDateInput"),
  refreshStatusBtn: document.getElementById("refreshStatusBtn"),
  completedCount: document.getElementById("completedCount"),
  totalCount: document.getElementById("totalCount"),
  habitsList: document.getElementById("habitsList"),
  newHabitInput: document.getElementById("newHabitInput"),
  addHabitBtn: document.getElementById("addHabitBtn"),
};

function currentDateValue() {
  if (!refs.statusDateInput.value) {
    refs.statusDateInput.value = new Date().toISOString().slice(0, 10);
  }
  return refs.statusDateInput.value;
}

async function request(path, options = {}) {
  const response = await fetch(path, options);
  let payload = {};
  try {
    payload = await response.json();
  } catch (err) {
    payload = {};
  }

  if (!response.ok) {
    const message = payload.error || `Request failed (${response.status})`;
    throw new Error(message);
  }
  return payload;
}

function updateCurrentUserText() {
  if (!state.activeUserId) {
    refs.currentUserText.textContent = "No user selected yet.";
    return;
  }
  refs.currentUserText.textContent = `Using: ${state.activeUserName}`;
}

function setBusy(isBusy) {
  refs.useNameBtn.disabled = isBusy;
  refs.addHabitBtn.disabled = isBusy;
  refs.refreshStatusBtn.disabled = isBusy;
}

function renderHabits() {
  refs.habitsList.innerHTML = "";
  const habits = state.habits;
  const statusByHabitId = new Map(
    (state.status?.habits || []).map((item) => [item.habit_id, item.completed]),
  );

  if (habits.length === 0) {
    const empty = document.createElement("p");
    empty.textContent = "No habits yet. Add your first one below.";
    refs.habitsList.appendChild(empty);
    refs.completedCount.textContent = "0";
    refs.totalCount.textContent = "0";
    return;
  }

  let completed = 0;
  for (const habit of habits) {
    const isDone = Boolean(statusByHabitId.get(habit.id));
    if (isDone) {
      completed += 1;
    }

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

    const button = document.createElement("button");
    button.className = "btn";
    button.type = "button";
    button.textContent = isDone ? "Checked in" : "Check in";
    button.disabled = isDone;
    button.addEventListener("click", async () => {
      await checkInHabit(habit.id);
    });

    row.appendChild(left);
    row.appendChild(button);
    refs.habitsList.appendChild(row);
  }

  refs.completedCount.textContent = String(completed);
  refs.totalCount.textContent = String(habits.length);
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

async function applyUserName() {
  const name = refs.userNameInput.value.trim();
  if (!name) {
    alert("Enter your name first.");
    return;
  }

  setBusy(true);
  try {
    const user = await resolveOrCreateUser(name);
    state.activeUserId = user.id;
    state.activeUserName = user.name;
    localStorage.setItem(USER_NAME_KEY, user.name);
    await loadDashboard();
    updateCurrentUserText();
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
    alert("Set your name first.");
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
  refs.useNameBtn.addEventListener("click", async () => {
    try {
      await applyUserName();
    } catch (err) {
      alert(err.message);
    }
  });

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

  refs.userNameInput.addEventListener("keydown", async (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      try {
        await applyUserName();
      } catch (err) {
        alert(err.message);
      }
    }
  });
}

async function start() {
  currentDateValue();
  bindEvents();
  updateCurrentUserText();

  const savedName = localStorage.getItem(USER_NAME_KEY);
  if (savedName) {
    refs.userNameInput.value = savedName;
    try {
      await applyUserName();
    } catch (err) {
      alert(err.message);
    }
  } else {
    renderHabits();
  }
}

start();

