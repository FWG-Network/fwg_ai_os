const state = {
  apiBase: "http://localhost:8000",
};

function getApiBase() {
  const override = new URLSearchParams(window.location.search).get("api");
  return override || state.apiBase;
}

function setApiBase(value) {
  state.apiBase = value;
  document.getElementById("api-base").value = value;
}

function renderOutput(id, payload) {
  const el = document.getElementById(id);
  el.textContent = JSON.stringify(payload, null, 2);
}

async function requestJson(path, options = {}) {
  const url = `${getApiBase()}${path}`;
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const text = await response.text();
  let data;
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    data = { raw: text };
  }
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${JSON.stringify(data)}`);
  }
  return data;
}

async function runDiscover() {
  const topic = document.getElementById("discover-topic").value;
  const mode = document.getElementById("discover-mode").value;
  const data = await requestJson(`/api/v1/discovery/discover?mode=${mode}`, {
    method: "POST",
    body: JSON.stringify({ topic, user_id: "dashboard-user" }),
  });
  renderOutput("discover-output", data);
}

async function runRank() {
  const payload = JSON.parse(document.getElementById("ranking-input").value);
  const data = await requestJson("/api/v1/ranking/rank", {
    method: "POST",
    body: JSON.stringify({ candidates: payload, user_id: "dashboard-user" }),
  });
  renderOutput("ranking-output", data);
}

async function runFeedback() {
  const data = await requestJson("/api/v1/feedback/", {
    method: "POST",
    body: JSON.stringify({
      user_id: document.getElementById("feedback-user").value,
      item_id: document.getElementById("feedback-item").value,
      event_type: document.getElementById("feedback-event").value,
      value: Number(document.getElementById("feedback-value").value),
    }),
  });
  renderOutput("feedback-output", data);
}

async function runLlm() {
  const prompt = document.getElementById("llm-prompt").value;
  const data = await requestJson("/api/v1/generate", {
    method: "POST",
    body: JSON.stringify({ prompt }),
  });
  renderOutput("llm-output", data);
}

async function runOsPlan() {
  const goal = document.getElementById("os-goal").value;
  const data = await requestJson("/api/v1/os/plan", {
    method: "POST",
    body: JSON.stringify({ command: goal, user_id: "dashboard-user" }),
  });
  renderOutput("os-output", data);
}

async function runOsExecute() {
  const goal = document.getElementById("os-goal").value;
  const data = await requestJson("/api/v1/os/execute", {
    method: "POST",
    body: JSON.stringify({ command: goal, user_id: "dashboard-user" }),
  });
  renderOutput("os-output", data);
}

async function runMemoryAdd() {
  const text = document.getElementById("memory-text").value;
  const data = await requestJson("/api/v1/add", {
    method: "POST",
    body: JSON.stringify({ text, metadata: { source: "dashboard" } }),
  });
  renderOutput("memory-output", data);
}

async function runMemorySearch() {
  const query = document.getElementById("memory-query").value;
  const data = await requestJson(`/api/v1/search?query=${encodeURIComponent(query)}&top_k=3`, {
    method: "POST",
  });
  renderOutput("memory-output", data);
}

async function runTrendScan() {
  const data = await requestJson("/api/v1/scan", {
    method: "POST",
  });
  renderOutput("trend-output", data);
}

async function runTrendBriefing() {
  const data = await requestJson("/api/v1/briefing");
  renderOutput("trend-output", data);
}

async function runHealthCheck() {
  try {
    const data = await requestJson("/api/v1/os/status");
    renderOutput("discover-output", data);
  } catch (error) {
    renderOutput("discover-output", { error: error.message });
  }
}

function wireActions() {
  document.querySelectorAll("button[data-action]").forEach((button) => {
    button.addEventListener("click", async () => {
      const action = button.getAttribute("data-action");
      try {
        switch (action) {
          case "discover": await runDiscover(); break;
          case "rank": await runRank(); break;
          case "feedback": await runFeedback(); break;
          case "llm": await runLlm(); break;
          case "os-plan": await runOsPlan(); break;
          case "os-execute": await runOsExecute(); break;
          case "memory-add": await runMemoryAdd(); break;
          case "memory-search": await runMemorySearch(); break;
          case "trend-scan": await runTrendScan(); break;
          case "trend-briefing": await runTrendBriefing(); break;
        }
      } catch (error) {
        const targetId = {
          discover: "discover-output",
          rank: "ranking-output",
          feedback: "feedback-output",
          llm: "llm-output",
          "os-plan": "os-output",
          "os-execute": "os-output",
          "memory-add": "memory-output",
          "memory-search": "memory-output",
          "trend-scan": "trend-output",
          "trend-briefing": "trend-output",
        }[action];
        if (targetId) {
          renderOutput(targetId, { error: error.message });
        }
      }
    });
  });

  document.getElementById("api-base").addEventListener("change", (event) => {
    setApiBase(event.target.value);
  });

  document.getElementById("health-check").addEventListener("click", runHealthCheck);
}

window.addEventListener("DOMContentLoaded", wireActions);
