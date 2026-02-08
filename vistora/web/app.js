const state = {
  jobs: [],
  modelCatalog: null,
};

function $(id) {
  return document.getElementById(id);
}

async function request(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const payload = await res.json().catch(() => ({}));
    throw new Error(payload.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

function toast(text, isError = false) {
  const el = $("toast");
  el.textContent = text;
  el.style.borderColor = isError ? "rgba(255,111,128,0.5)" : "rgba(130,195,208,0.4)";
  el.classList.add("show");
  window.setTimeout(() => el.classList.remove("show"), 2400);
}

function setBusy(btn, busy) {
  if (!btn) return;
  if (!btn.dataset.defaultText) {
    btn.dataset.defaultText = btn.textContent;
  }
  if (busy) {
    btn.disabled = true;
    btn.textContent = "处理中...";
  } else {
    btn.disabled = false;
    btn.textContent = btn.dataset.defaultText;
  }
}

function statusTag(status) {
  if (status === "failed" || status === "canceled") return `<span style="color:#ffdbe1">${status}</span>`;
  if (status === "done") return `<span style="color:#cbfbe8">${status}</span>`;
  return status;
}

function fmtTime(v) {
  return v ? new Date(v).toLocaleTimeString() : "-";
}

function fillModelSelect(selectId, cards) {
  const select = $(selectId);
  select.innerHTML = "";

  const autoOption = document.createElement("option");
  autoOption.value = "";
  autoOption.textContent = "auto by quality tier";
  select.appendChild(autoOption);

  for (const card of cards) {
    const option = document.createElement("option");
    option.value = card.id;
    option.textContent = `${card.id} (${card.maturity})`;
    select.appendChild(option);
  }
}

function applyQualityPreset() {
  if (!state.modelCatalog) return;
  const tier = $("quality_tier").value;
  const preset = (state.modelCatalog.quality_presets || []).find((x) => x.tier === tier);
  if (!preset) return;
  $("detector_model").value = preset.detector_model || "";
  $("restorer_model").value = preset.restorer_model || "";
  $("refiner_model").value = preset.refiner_model || "";
}

async function loadModelCatalog() {
  const catalog = await request("/api/v1/models/catalog");
  state.modelCatalog = catalog;
  const cards = catalog.cards || [];
  fillModelSelect("detector_model", cards.filter((c) => c.role === "detector"));
  fillModelSelect("restorer_model", cards.filter((c) => c.role === "restorer"));
  fillModelSelect("refiner_model", cards.filter((c) => c.role === "refiner"));
  applyQualityPreset();
}

async function refreshJobs() {
  const payload = await request("/api/v1/jobs");
  const jobs = payload.jobs || [];
  state.jobs = jobs.sort((a, b) => {
    const ta = new Date(a.updated_at || 0).getTime();
    const tb = new Date(b.updated_at || 0).getTime();
    return tb - ta;
  });
  renderJobs();
}

function renderJobs() {
  const body = $("job_rows");
  body.innerHTML = "";

  let queued = 0;
  let running = 0;
  let done = 0;
  let failed = 0;

  for (const job of state.jobs) {
    if (job.status === "queued") queued += 1;
    if (job.status === "running") running += 1;
    if (job.status === "done") done += 1;
    if (job.status === "failed") failed += 1;

    const tr = document.createElement("tr");
    const canCancel = job.status === "queued";
    const modelText = `${job.detector_model} / ${job.restorer_model}${job.refiner_model ? ` / ${job.refiner_model}` : ""}`;
    const progressPct = Math.round((job.progress || 0) * 100);
    tr.innerHTML = `
      <td class="mono">${job.id.slice(0, 8)}</td>
      <td>${job.user_id}</td>
      <td>${statusTag(job.status)}</td>
      <td>${job.quality_tier}</td>
      <td class="mono">${modelText}</td>
      <td>${job.stage}</td>
      <td class="progress-shell">
        <div class="progress-bar"><div class="progress-fill" style="width:${progressPct}%"></div></div>
        <span>${progressPct}%</span>
      </td>
      <td>${job.credits_reserved}</td>
      <td>${fmtTime(job.updated_at)}</td>
      <td><button ${canCancel ? "" : "disabled"} data-id="${job.id}" class="${canCancel ? "danger" : "secondary"}">Cancel</button></td>
    `;
    body.appendChild(tr);
  }

  $("s-queued").textContent = String(queued);
  $("s-running").textContent = String(running);
  $("s-done").textContent = String(done);
  $("s-failed").textContent = String(failed);

  body.querySelectorAll("button[data-id]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      try {
        await request(`/api/v1/jobs/${btn.dataset.id}/cancel`, { method: "POST" });
        toast("cancel requested");
        await refreshJobs();
      } catch (err) {
        toast(err.message, true);
      }
    });
  });
}

function parseJsonInput(id) {
  const raw = $(id).value.trim();
  if (!raw) return {};
  return JSON.parse(raw);
}

async function createJob(ev) {
  ev.preventDefault();
  const submitBtn = ev.submitter;
  setBusy(submitBtn, true);
  const estimatedCreditsRaw = $("estimated_credits").value.trim();
  const durationHintRaw = $("duration_hint_seconds").value.trim();

  const payload = {
    input_path: $("input_path").value.trim(),
    output_path: $("output_path").value.trim() || null,
    user_id: $("user_id").value.trim() || "anonymous",
    profile_name: $("profile_name").value.trim() || null,
    runner: $("runner").value,
    quality_tier: $("quality_tier").value,
    detector_model: $("detector_model").value || null,
    restorer_model: $("restorer_model").value || null,
    refiner_model: $("refiner_model").value || null,
    options: {},
  };

  if (estimatedCreditsRaw) {
    payload.estimated_credits = Number.parseInt(estimatedCreditsRaw, 10);
  }
  if (durationHintRaw) {
    payload.duration_hint_seconds = Number.parseInt(durationHintRaw, 10);
  }

  try {
    const job = await request("/api/v1/jobs", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    toast(`job created ${job.id.slice(0, 8)}`);
    await refreshJobs();
  } catch (err) {
    toast(err.message, true);
  } finally {
    setBusy(submitBtn, false);
  }
}

async function queryBalance() {
  const user = $("credit_user").value.trim() || "anonymous";
  try {
    const data = await request(`/api/v1/credits/${encodeURIComponent(user)}`);
    $("balance_view").textContent = `Balance: ${data.balance}`;
  } catch (err) {
    toast(err.message, true);
  }
}

async function topup(ev) {
  ev.preventDefault();
  const submitBtn = ev.submitter;
  setBusy(submitBtn, true);
  const user = $("credit_user").value.trim() || "anonymous";
  const payload = {
    amount: Number.parseInt($("credit_amount").value, 10),
    reason: $("credit_reason").value.trim() || "manual_topup",
  };
  try {
    const data = await request(`/api/v1/credits/${encodeURIComponent(user)}/topup`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
    $("balance_view").textContent = `Balance: ${data.balance.balance}`;
    toast("topup success");
  } catch (err) {
    toast(err.message, true);
  } finally {
    setBusy(submitBtn, false);
  }
}

async function saveProfile(ev) {
  ev.preventDefault();
  const submitBtn = ev.submitter;
  setBusy(submitBtn, true);
  const name = $("pf_name").value.trim();
  if (!name) {
    toast("profile name required", true);
    setBusy(submitBtn, false);
    return;
  }
  try {
    const settings = parseJsonInput("pf_json");
    await request(`/api/v1/profiles/${encodeURIComponent(name)}`, {
      method: "PUT",
      body: JSON.stringify({ settings }),
    });
    toast("profile saved");
    await refreshProfiles();
  } catch (err) {
    toast(err.message, true);
  } finally {
    setBusy(submitBtn, false);
  }
}

async function refreshProfiles() {
  try {
    const payload = await request("/api/v1/profiles");
    $("profiles_view").textContent = JSON.stringify(payload, null, 2);
  } catch (err) {
    toast(err.message, true);
  }
}

async function sendWebhook(ev) {
  ev.preventDefault();
  const submitBtn = ev.submitter;
  setBusy(submitBtn, true);
  const payload = {
    event: $("tg_event").value,
    user_id: $("tg_user").value.trim() || "anonymous",
    payload: parseJsonInput("tg_payload"),
  };
  try {
    const result = await request("/api/v1/tg/webhook", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    $("tg_result").textContent = JSON.stringify(result, null, 2);
    toast("webhook sent");
  } catch (err) {
    toast(err.message, true);
  } finally {
    setBusy(submitBtn, false);
  }
}

function startPoll() {
  setInterval(() => {
    refreshJobs().catch((err) => toast(err.message, true));
  }, 1500);
}

async function refreshServiceStatus() {
  const badge = $("service_status");
  try {
    await request("/healthz");
    badge.textContent = "online";
    badge.classList.remove("offline");
    badge.classList.add("online");
  } catch (_err) {
    badge.textContent = "offline";
    badge.classList.remove("online");
    badge.classList.add("offline");
  }
}

async function refreshAll() {
  await Promise.all([refreshServiceStatus(), loadModelCatalog(), refreshJobs(), refreshProfiles(), queryBalance()]);
}

async function bootstrap() {
  $("job-form").addEventListener("submit", createJob);
  $("refresh_jobs").addEventListener("click", () => refreshJobs().catch((err) => toast(err.message, true)));
  $("credit-form").addEventListener("submit", topup);
  $("query_balance").addEventListener("click", () => queryBalance().catch((err) => toast(err.message, true)));
  $("profile-form").addEventListener("submit", saveProfile);
  $("refresh_profiles").addEventListener("click", () => refreshProfiles().catch((err) => toast(err.message, true)));
  $("tg-form").addEventListener("submit", sendWebhook);
  $("quality_tier").addEventListener("change", applyQualityPreset);
  $("refresh_all").addEventListener("click", () => {
    refreshAll().catch((err) => toast(err.message, true));
  });

  await refreshAll();
  startPoll();
  setInterval(() => {
    refreshServiceStatus().catch(() => null);
  }, 5000);
}

bootstrap().catch((err) => toast(err.message, true));
