const state = {
  users: [],
  activeUserId: null,
  habits: [],
  status: null,
};

const refs = {
  userSelect: document.getElementById("userSelect"),
  refreshUsersBtn: document.getElementById("refreshUsersBtn"),
  newUserInput: document.getElementById("newUserInput"),
  createUserBtn: document.getElementById("createUserBtn"),
  statusDateInput: document.getElementById("statusDateInput"),
  refreshStatusBtn: document.getElementById("refreshStatusBtn"),
  completedCount: document.getElementById("completedCount"),
  totalCount: document.getElementById("totalCount"),
  habitsList: document.getElementById("habitsList"),
  newHabitInput: document.getElementById("newHabitInput"),
  addHabitBtn: document.getElementById("addHabitBtn"),
  feedbackMessage: document.getElementById("feedbackMessage"),
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

function setMessage(message, isError = false) {
  refs.feedbackMessage.textContent = message;
  refs.feedbackMessage.classList.toggle("error", isError);
}

function renderUsers() {
  refs.userSelect.innerHTML = "";
  if (state.users.length === 0) {
    const option = document.createElement("option");
    option.textContent = "No users yet";
    option.value = "";
    refs.userSelect.appendChild(option);
    refs.userSelect.disabled = true;
    return;
  }

  refs.userSelect.disabled = false;
  for (const user of state.users) {
    const option = document.createElement("option");
    option.value = String(user.id);
    option.textContent = `#${user.id} ${user.name}`;
    refs.userSelect.appendChild(option);
  }

  if (!state.activeUserId) {
    state.activeUserId = state.users[0].id;
  }
  refs.userSelect.value = String(state.activeUserId);
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

async function loadUsers() {
  const data = await request("/users");
  state.users = data.users || [];

  if (
    state.activeUserId &&
    !state.users.find((user) => user.id === state.activeUserId)
  ) {
    state.activeUserId = null;
  }

  renderUsers();
  if (state.activeUserId) {
    await loadDashboard();
  } else {
    state.habits = [];
    state.status = null;
    renderHabits();
  }
}

async function loadDashboard() {
  if (!state.activeUserId) {
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

async function createUser() {
  const name = refs.newUserInput.value.trim();
  if (!name) {
    setMessage("Enter a user name first.", true);
    return;
  }
  const user = await request("/users", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  refs.newUserInput.value = "";
  state.activeUserId = user.id;
  await loadUsers();
  setMessage(`Created user "${user.name}".`);
}

async function addHabit() {
  if (!state.activeUserId) {
    setMessage("Create or select a user first.", true);
    return;
  }
  const name = refs.newHabitInput.value.trim();
  if (!name) {
    setMessage("Enter a habit name first.", true);
    return;
  }
  const habit = await request("/habits", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: state.activeUserId, name }),
  });
  refs.newHabitInput.value = "";
  await loadDashboard();
  setMessage(`Added habit "${habit.name}".`);
}

async function checkInHabit(habitId) {
  const date = currentDateValue();
  await request("/checkins", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ habit_id: habitId, date }),
  });
  await loadDashboard();
  setMessage(`Check-in saved for ${date}.`);
}

function bindEvents() {
  refs.userSelect.addEventListener("change", async () => {
    state.activeUserId = Number(refs.userSelect.value) || null;
    await loadDashboard();
    setMessage("Active user updated.");
  });

  refs.refreshUsersBtn.addEventListener("click", async () => {
    await loadUsers();
    setMessage("Users reloaded.");
  });

  refs.createUserBtn.addEventListener("click", async () => {
    try {
      await createUser();
    } catch (err) {
      setMessage(err.message, true);
    }
  });

  refs.addHabitBtn.addEventListener("click", async () => {
    try {
      await addHabit();
    } catch (err) {
      setMessage(err.message, true);
    }
  });

  refs.refreshStatusBtn.addEventListener("click", async () => {
    try {
      await loadDashboard();
      setMessage("Status reloaded.");
    } catch (err) {
      setMessage(err.message, true);
    }
  });
}

async function start() {
  currentDateValue();
  bindEvents();
  try {
    await loadUsers();
    setMessage("Web app is ready.");
  } catch (err) {
    setMessage(err.message, true);
  }
}

start();

