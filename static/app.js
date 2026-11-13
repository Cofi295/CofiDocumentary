const state = {
  jobs: [],
  selectedId: null,
  selectedRadar: null,
  selectedChannelPlan: null,
  selectedCreateTopic: null,
  createTopicSuggestions: [],
  selectedTopicStream: "all",
  sessionSuggestedTopicKeys: {},
  channelProfiles: [],
  selectedChannelProfileId: null,
  radarItems: [],
  voices: [],
  health: null,
  appTab: "overview",
  detailTab: "tongquan",
  logPhase: "plan",
  editJobId: null,
  editStudioUrl: null,
  editChatOpen: true,
  producerChatAttachments: [],
  globalCodexOpen: localStorage.getItem("cofi-global-chat-open") === "1",
  globalCodexAttachments: [],
  globalCodexContext: null,
  editChatAttachments: [],
  editAttachmentJobId: null,
  aiVisualEmbedUrl: null,
  aiVisualEmbedOrigin: null,
  aiVisualEmbedJobId: null,
  aiVisualEmbedInfo: null,
  autoFollowPipelineJobId: null,
  userPinnedJobId: null,
  lastPipelineUiSignature: null,
  workspaceRenderKeys: {},
  chatRunConnections: {},
};

const phases = ["plan", "voice", "visuals", "ai_visual", "edit", "seo", "qc"];
const phaseLabels = {
  plan: "Kịch bản + chia cảnh",
  voice: "Giọng đọc + SRT",
  visuals: "Visuals / Prompt",
  ai_visual: "AI bổ sung",
  edit: "Dựng Remotion (@footage AI Agent)",
  seo: "SEO + Thumbnail",
  qc: "Xuất video",
};
const statusLabels = {
  pending: "Chưa chạy",
  queued: "Đang chờ",
  running: "Đang chạy",
  succeeded: "Hoàn tất",
  failed: "Có lỗi",
  interrupted: "Bị ngắt",
  ready: "Sẵn sàng",
  completed: "Đã hoàn thành",
};

function effectivePhases(job) {
  const strategy = String(job?.visual_strategy || job?.production_recipe?.visual_strategy || "full_footage").toLowerCase();
  if (strategy === "full_footage") return ["plan", "voice", "visuals", "edit", "seo", "qc"];
  return ["plan", "voice", "visuals", "ai_visual", "edit", "seo", "qc"];
}

function phaseWorkspaceTab(phase) {
  return {
    plan: "script",
    voice: "voice",
    visuals: "visuals",
    footage: "footage",
    ai_visual: "ai_visual",
    edit: "edit",
    seo: "seo",
    qc: "qc",
  }[String(phase || "")] || null;
}

function pipelineUiSignature(job) {
  if (!job) return "";
  const phaseState = effectivePhases(job)
    .map(phase => {
      const p = job.phases?.[phase] || {};
      return `${phase}:${p.status || "pending"}:${p.started_at || ""}:${p.finished_at || ""}:${p.error || ""}:${p.is_paused ? 1 : 0}:${p.last_message || ""}`;
    })
    .join("|");
  const pulseSig = state.realtimeLive?.job_id === job.id ? JSON.stringify(state.realtimeLive) : "";
  return `${job.id}|${job.status || ""}|${job.current_phase || ""}|${job.updated_at || ""}|${phaseState}|${pulseSig}`;
}

function followPipelineJob(job, { switchTab = true } = {}) {
  if (!job) return;
  state.selectedId = job.id;
  state.autoFollowPipelineJobId = job.id;
  if (!switchTab) return;
  const targetTab = phaseWorkspaceTab(job.current_phase);
  if (targetTab && state.appTab !== targetTab) setAppTab(targetTab);
}

async function runFullPipeline(job, { fromBeginning = false } = {}) {
  if (!job) return;
  const active = effectivePhases(job);
  if (!active.length) return;
  const fromPhase = fromBeginning ? active[0] : (nextPendingPhase(job) || active[0]);
  const throughPhase = active[active.length - 1];
  state.userPinnedJobId = null;
  state.selectedId = job.id;
  state.autoFollowPipelineJobId = job.id;
  state.lastFollowedPhaseKey = `${job.id}:${fromPhase}`;
  const targetTab = phaseWorkspaceTab(fromPhase);
  if (targetTab) setAppTab(targetTab);
  await api(`/api/jobs/${encodeURIComponent(job.id)}/pipeline/${encodeURIComponent(fromPhase)}/${encodeURIComponent(throughPhase)}`, { method: "POST" });
  toast(`Đang chạy tự động toàn bộ dây chuyền từ: ${phaseLabels[fromPhase]}`);
  await Promise.all([loadJobs(true), renderDetail(), renderFunctionWorkspaces()]);
}

async function deleteJobById(jobId, buttonEl = null) {
  const id = String(jobId || "").trim();
  if (!id) return;
  const prevLabel = buttonEl?.textContent || "";
  if (buttonEl) {
    buttonEl.disabled = true;
    buttonEl.textContent = "Đang xóa…";
  }
  try {
    await api(`/api/jobs/${encodeURIComponent(id)}`, { method: "DELETE" });
    state.jobs = state.jobs.filter(item => item.id !== id);
    if (state.selectedId === id) {
      state.selectedId = state.jobs[0]?.id || null;
    }
    state.lastJobListHtml = "";
    state.lastOverviewDeckHtml = "";
    await loadJobs(true);
    await renderDetail();
    toast("Đã xóa dự án.");
  } catch (err) {
    if (buttonEl) {
      buttonEl.disabled = false;
      buttonEl.textContent = prevLabel || "Xóa";
    }
    toast(err.message, true);
  }
}

function nextPendingPhase(job) {
  return effectivePhases(job).find(p => job.phases?.[p]?.status !== "succeeded") || null;
}

function completedPhaseCount(job) {
  return effectivePhases(job).filter(p => job.phases?.[p]?.status === "succeeded").length;
}

function continueButtonLabel(job) {
  const next = nextPendingPhase(job);
  if (!next) return "";
  const active = effectivePhases(job);
  const index = active.indexOf(next);
  const status = job.phases?.[next]?.status || "pending";
  if (status === "failed" || status === "interrupted") return `Chạy lại: ${phaseLabels[next]}`;
  if (index === 0) return `Chạy bước 1: ${phaseLabels[next]}`;
  return `Tiếp tục bước ${index + 1}: ${phaseLabels[next]}`;
}

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

async function api(path, options = {}) {
  const headers = { ...(options.body ? { "Content-Type": "application/json" } : {}), ...(options.headers || {}) };
  const response = await fetch(path, { cache: "no-store", ...options, headers });
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try { detail = (await response.json()).detail || detail; } catch (_) {}
    throw new Error(detail);
  }
  const type = response.headers.get("content-type") || "";
  return type.includes("application/json") ? response.json() : response.text();
}

// Giữ nhịp gửi giống thao tác người dùng để tránh bridge ChatGPT Web bị đánh
// dấu là gửi liên tiếp quá nhanh khi UI gọi nhiều request sau reconnect.
let lastCodexWebRequestAt = 0;
async function waitForCodexWebPacing() {
  const minGapMs = 1800;
  const now = Date.now();
  const waitMs = Math.max(0, minGapMs - (now - lastCodexWebRequestAt));
  if (waitMs) await new Promise(resolve => setTimeout(resolve, waitMs));
  lastCodexWebRequestAt = Date.now();
}

let aiVisualSettingsSaveTimer = null;
let footageRenderInFlight = false;
let aiVisualRenderInFlight = false;
let aiVisualEmbedStartPromise = null;
let aiVisualRuntimePollTimer = null;
let aiVisualRuntimeTestInFlight = false;
let aiVisualRuntimeLastTest = null;

window.addEventListener("message", event => {
  const payload = event.data;
  if (!payload || payload.type !== "cofi-media-factory-settings") return;
  if (!state.selectedId || state.appTab !== "ai_visual") return;
  if (state.aiVisualEmbedOrigin && event.origin !== state.aiVisualEmbedOrigin) return;
  clearTimeout(aiVisualSettingsSaveTimer);
  aiVisualSettingsSaveTimer = setTimeout(async () => {
    try {
      const saved = await api(`/api/jobs/${encodeURIComponent(state.selectedId)}/ai-visual-settings`, {
        method: "PATCH",
        body: JSON.stringify({
          task_type: payload.task_type,
          model: payload.model,
          aspect_ratio: payload.aspect_ratio,
        }),
      });
      const label = document.querySelector("[data-ai-visual-settings-label]");
      if (label) label.textContent = `Ảnh: ${saved.image_model} · Video: ${saved.video_model} · ${saved.aspect_ratio}`;
      if (state.aiVisualEmbedInfo && state.aiVisualEmbedJobId === state.selectedId) {
        state.aiVisualEmbedInfo = { ...state.aiVisualEmbedInfo, settings: saved };
      }
    } catch (err) {
      toast(`Không lưu được cấu hình AI Visual: ${err.message}`, true);
    }
  }, 220);
});

async function ensureCofiStudioEmbed(job) {
  if (state.aiVisualEmbedJobId === job.id && state.aiVisualEmbedInfo?.url) {
    return state.aiVisualEmbedInfo;
  }
  if (aiVisualEmbedStartPromise?.jobId === job.id) {
    return aiVisualEmbedStartPromise.promise;
  }
  const promise = (async () => {
    const [embed, settings] = await Promise.all([
      api("/api/cofi-studio/embed/start", { method: "POST" }),
      api(`/api/jobs/${encodeURIComponent(job.id)}/ai-visual-settings`),
    ]);
    const rawUrl = String(embed.url || "");
    if (!rawUrl) throw new Error("Media Factory tích hợp đã chạy nhưng chưa trả về URL.");
    const url = new URL(rawUrl);
    url.searchParams.set("image_model", settings.image_model || "nano_banana_2");
    url.searchParams.set("video_model", settings.video_model || "veo_31_fast");
    url.searchParams.set("aspect_ratio", settings.aspect_ratio || "16:9");
    state.aiVisualEmbedUrl = url.toString();
    state.aiVisualEmbedOrigin = url.origin;
    state.aiVisualEmbedJobId = job.id;
    state.aiVisualEmbedInfo = { ...embed, url: state.aiVisualEmbedUrl, settings };
    return state.aiVisualEmbedInfo;
  })();
  aiVisualEmbedStartPromise = { jobId: job.id, promise };
  try {
    return await promise;
  } finally {
    if (aiVisualEmbedStartPromise?.promise === promise) aiVisualEmbedStartPromise = null;
  }
}

let lastAiVisualRuntimeSnapshot = null;
let flowAccountsPopupFilter = "all";

function isFlowAccountReady(account) {
  if (!account) return false;
  return account.status === "ready" && (account.session_present !== false || Boolean(account.live_session));
}

function formatFlowAccountError(errText) {
  const raw = String(errText || "").trim();
  if (!raw) return "";
  if (raw.includes("accounts.google.com") || raw.includes("signin/challenge") || raw.includes("redirected to sign-in") || raw.includes("expired")) {
    return "Phiên đăng nhập Google đã hết hạn hoặc yêu cầu xác minh lại (Sign-in Challenge).";
  }
  return raw.length > 160 ? `${raw.slice(0, 157)}...` : raw;
}

function aiVisualRuntimeAccountHtml(account) {
  const ready = isFlowAccountReady(account);
  const mode = account.browser_mode === "visible"
    ? "Đang mở cửa sổ xác minh"
    : account.browser_mode === "hidden" || account.live_session
      ? "Chrome đang chạy ẩn"
      : ready
        ? "Sẵn sàng (Đã nối Session)"
        : "Phiên đã hết hạn / Cần check";
  const statusClass = ready ? "ready" : account.status === "connecting" ? "working" : "blocked";
  const tier = String(account.tier || "free").toUpperCase();
  const cleanError = ready ? "" : formatFlowAccountError(account.last_error);
  return `<article class="ai-runtime-account ${statusClass}" data-account-card-id="${escapeHtml(account.id)}">
    <div class="ai-runtime-account-main">
      <div class="ai-runtime-account-title">
        <strong>${escapeHtml(account.email || "Tài khoản chưa nhận diện")}</strong>
        <span class="flow-tier-pill tier-${escapeHtml(tier.toLowerCase())}">${escapeHtml(tier)}</span>
      </div>
      <span class="ai-runtime-account-sub">${escapeHtml(mode)}</span>
    </div>
    <div class="ai-runtime-account-state">
      <b class="${statusClass}">${ready ? "ĐANG HOẠT ĐỘNG" : account.status === "connecting" ? "ĐANG KẾT NỐI" : "ĐÃ DIE / CẦN XÁC MINH"}</b>
      <small>${account.credits == null ? "—" : `${Number(account.credits).toLocaleString("vi-VN")} credit`}</small>
    </div>
    ${cleanError ? `<p class="ai-runtime-account-err">${escapeHtml(cleanError)}</p>` : ""}
    <div class="ai-runtime-account-actions">
      <button class="ghost compact" type="button" data-ai-account-action="check" data-account-id="${escapeHtml(account.id)}" data-account-email="${escapeHtml(account.email || account.id)}">🔍 Check</button>
      <button class="ghost compact" type="button" data-ai-account-action="renew" data-account-id="${escapeHtml(account.id)}" data-account-email="${escapeHtml(account.email || account.id)}">↻ Lấy lại phiên</button>
      <button class="ghost compact" type="button" data-ai-account-action="verify" data-account-id="${escapeHtml(account.id)}" data-account-email="${escapeHtml(account.email || account.id)}">🌐 Mở Flow xác minh</button>
      <button class="ghost compact danger-text" type="button" data-ai-account-action="delete" data-account-id="${escapeHtml(account.id)}" data-account-email="${escapeHtml(account.email || account.id)}">🗑 Xóa</button>
    </div>
  </article>`;
}

function bindFlowAccountActionButtons(container, job) {
  if (!container) return;
  container.querySelectorAll("[data-ai-account-action]").forEach(button => button.addEventListener("click", async event => {
    event.preventDefault();
    event.stopPropagation();
    const btn = event.currentTarget;
    const action = btn.dataset.aiAccountAction;
    const accountId = btn.dataset.accountId;
    const accountEmail = btn.dataset.accountEmail || accountId;
    const originalText = btn.textContent;

    if (action === "delete") {
      btn.disabled = true;
      btn.textContent = "Đang xóa…";
      try {
        try {
          await api(`/api/cofi-studio/runtime/accounts/${encodeURIComponent(accountId)}/delete`, { method: "POST" });
        } catch (_) {
          await api(`/api/cofi-studio/runtime/accounts/${encodeURIComponent(accountId)}`, { method: "DELETE" });
        }
        if (lastAiVisualRuntimeSnapshot && Array.isArray(lastAiVisualRuntimeSnapshot.accounts)) {
          lastAiVisualRuntimeSnapshot.accounts = lastAiVisualRuntimeSnapshot.accounts.filter(acc => String(acc.id) !== String(accountId));
          renderAiVisualRuntimePanel(job, lastAiVisualRuntimeSnapshot);
          renderFlowAccountsDialogContent(job, lastAiVisualRuntimeSnapshot);
        }
        toast(`Đã xóa tài khoản ${accountEmail}.`);
        if (job) await refreshAiVisualRuntime(job, { silent: true });
      } catch (err) {
        toast(`Không xóa được tài khoản: ${err.message}`, true);
        btn.disabled = false;
        btn.textContent = originalText;
      }
      return;
    }

    if (action === "check") {
      btn.disabled = true;
      btn.textContent = "Đang check…";
      try {
        const res = await api(`/api/cofi-studio/runtime/accounts/${encodeURIComponent(accountId)}/check`, { method: "POST" });
        const acc = res?.account || res;
        const alive = res?.alive ?? isFlowAccountReady(acc);
        toast(
          alive
            ? `✅ ${accountEmail}: Đang hoạt động (${acc?.credits != null ? `${Number(acc.credits).toLocaleString("vi-VN")} credit` : "Sẵn sàng"}).`
            : `⚠️ ${accountEmail}: Phiên hết hạn hoặc cần mở Flow xác minh lại.`,
          !alive
        );
        if (job) await refreshAiVisualRuntime(job, { silent: true });
      } catch (err) {
        toast(`Check tài khoản thất bại: ${err.message}`, true);
        btn.disabled = false;
        btn.textContent = originalText;
      }
      return;
    }

    btn.disabled = true;
    btn.textContent = action === "verify" ? "Đang mở Chrome…" : "Đang lấy phiên…";
    try {
      const res = await api(`/api/cofi-studio/runtime/accounts/${encodeURIComponent(accountId)}/${encodeURIComponent(action)}`, { method: "POST" });
      if (action === "verify") {
        toast(`Đã mở cửa sổ Chrome cho ${accountEmail} để xác minh.`);
      } else {
        const ready = isFlowAccountReady(res);
        toast(
          ready
            ? `✅ Đã khôi phục phiên cho ${accountEmail}.`
            : `Đã gửi yêu cầu làm mới phiên cho ${accountEmail}.`
        );
      }
      if (job) await refreshAiVisualRuntime(job, { silent: true });
      setTimeout(() => { if (job) refreshAiVisualRuntime(job, { silent: true }); }, 1500);
    } catch (err) {
      toast(err.message, true);
      btn.disabled = false;
      btn.textContent = originalText;
    }
  }));
}

async function runCheckAllFlowAccounts(job, triggerBtn) {
  const originalText = triggerBtn?.textContent || "🔄 Kiểm tra & Lấy lại Session";
  if (triggerBtn) {
    triggerBtn.disabled = true;
    triggerBtn.textContent = "⏳ Đang check & lấy lại session…";
  }
  try {
    let res;
    try {
      res = await api("/api/cofi-studio/runtime/accounts/_all/check", { method: "POST" });
    } catch (_) {
      res = await api("/api/cofi-studio/runtime/accounts/check-all", { method: "POST" });
    }
    if (res && Array.isArray(res.accounts) && lastAiVisualRuntimeSnapshot) {
      lastAiVisualRuntimeSnapshot.accounts = res.accounts;
      renderAiVisualRuntimePanel(job, lastAiVisualRuntimeSnapshot);
      renderFlowAccountsDialogContent(job, lastAiVisualRuntimeSnapshot);
    }
    const activeCount = Number(res?.active_count ?? (Array.isArray(res?.accounts) ? res.accounts.filter(isFlowAccountReady).length : 0));
    const totalCount = Number(res?.total_count ?? (Array.isArray(res?.accounts) ? res.accounts.length : 0));
    const recoveredCount = Number(res?.recovered_count ?? 0);
    const deadCount = Math.max(0, totalCount - activeCount);
    toast(
      `Đã kiểm tra ${totalCount} tài khoản: ${activeCount} hoạt động${recoveredCount > 0 ? ` (khôi phục ${recoveredCount} session)` : ""}${deadCount > 0 ? ` · ${deadCount} tài khoản die` : ""}.`
    );
    if (job) await refreshAiVisualRuntime(job, { silent: true });
  } catch (err) {
    toast(`Lỗi kiểm tra session: ${err.message}`, true);
  } finally {
    if (triggerBtn && triggerBtn.isConnected) {
      triggerBtn.disabled = false;
      triggerBtn.textContent = originalText;
    }
  }
}

async function runPruneDeadFlowAccounts(job, triggerBtn) {
  const originalText = triggerBtn?.textContent || "🧹 Xóa tài khoản die";
  if (triggerBtn) {
    triggerBtn.disabled = true;
    triggerBtn.textContent = "⏳ Đang kiểm tra & dọn…";
  }
  try {
    let res;
    try {
      res = await api("/api/cofi-studio/runtime/accounts/_all/prune-dead", { method: "POST" });
    } catch (_) {
      res = await api("/api/cofi-studio/runtime/accounts/prune-dead", { method: "POST" });
    }
    if (res && Array.isArray(res.accounts) && lastAiVisualRuntimeSnapshot) {
      lastAiVisualRuntimeSnapshot.accounts = res.accounts;
      renderAiVisualRuntimePanel(job, lastAiVisualRuntimeSnapshot);
      renderFlowAccountsDialogContent(job, lastAiVisualRuntimeSnapshot);
    }
    const kept = Number(res?.kept_count ?? 0);
    const deleted = Number(res?.deleted_count ?? 0);
    toast(deleted > 0
      ? `Đã xóa ${deleted} tài khoản die · Giữ lại ${kept} tài khoản đang hoạt động.`
      : `Kiểm tra hoàn tất: Tất cả ${kept} tài khoản đều đang hoạt động tốt (0 tài khoản die).`);
    if (job) await refreshAiVisualRuntime(job, { silent: true });
  } catch (err) {
    toast(`Lỗi dọn tài khoản die: ${err.message}`, true);
  } finally {
    if (triggerBtn && triggerBtn.isConnected) {
      triggerBtn.disabled = false;
      triggerBtn.textContent = originalText;
    }
  }
}

async function runCleanFlowAccountsCache(job, triggerBtn) {
  const originalText = triggerBtn?.textContent || "⚡ Dọn Cache Thông Minh";
  if (triggerBtn) {
    triggerBtn.disabled = true;
    triggerBtn.textContent = "⏳ Đang dọn cache…";
  }
  try {
    let res;
    try {
      res = await api("/api/cofi-studio/runtime/accounts/clean-cache", { method: "POST" });
    } catch (_) {
      res = await api("/api/v1/accounts/google-flow/clean-cache", { method: "POST" });
    }
    const freedMb = Number(res?.freed_mb ?? 0);
    const totalMb = Number(res?.total_size_mb ?? 0);
    const orphans = Number(res?.orphan_profiles_removed ?? 0);
    const cleaned = Number(res?.cleaned_profiles_count ?? 0);
    toast(
      `Đã dọn dẹp ${freedMb.toLocaleString("vi-VN")} MB cache · Xóa ${orphans} profile rác · Tối ưu ${cleaned} tài khoản. Dung lượng hiện tại: ${totalMb.toLocaleString("vi-VN")} MB.`
    );
    if (job) await refreshAiVisualRuntime(job, { silent: true });
  } catch (err) {
    toast(`Lỗi dọn dẹp cache: ${err.message}`, true);
  } finally {
    if (triggerBtn && triggerBtn.isConnected) {
      triggerBtn.disabled = false;
      triggerBtn.textContent = originalText;
    }
  }
}

function renderFlowAccountsDialogContent(job, runtime) {
  const content = document.querySelector("#flowAccountsDialogContent");
  if (!content) return;
  const accounts = Array.isArray(runtime?.accounts) ? runtime.accounts : [];
  const activeAccounts = accounts.filter(isFlowAccountReady);
  const deadAccounts = accounts.filter(acc => !isFlowAccountReady(acc));
  const totalCredits = activeAccounts.reduce((sum, acc) => sum + Number(acc.credits || 0), 0);
  const ultraCount = activeAccounts.filter(acc => String(acc.tier || "").toLowerCase() === "ultra").length;
  const proCount = activeAccounts.filter(acc => String(acc.tier || "").toLowerCase() === "pro").length;
  const freeCount = activeAccounts.filter(acc => !["ultra", "pro"].includes(String(acc.tier || "").toLowerCase())).length;

  const filtered = flowAccountsPopupFilter === "active"
    ? activeAccounts
    : flowAccountsPopupFilter === "dead"
      ? deadAccounts
      : accounts;

  const titleEl = document.querySelector("#flowAccountsDialogTitle");
  if (titleEl) {
    titleEl.textContent = `Quản lý tài khoản Google Flow (${activeAccounts.length}/${accounts.length} hoạt động)`;
  }

  content.innerHTML = `
    <div class="flow-popup-metrics">
      <div class="flow-popup-metric ok"><span>Đang hoạt động</span><strong>${activeAccounts.length} / ${accounts.length}</strong><small>${ultraCount} ULTRA · ${proCount} PRO · ${freeCount} FREE</small></div>
      <div class="flow-popup-metric ${deadAccounts.length ? "warn" : "ok"}"><span>Hết hạn / Cần xác minh</span><strong>${deadAccounts.length}</strong><small>${deadAccounts.length ? "Bấm lấy lại session hoặc xóa" : "Tất cả sẵn sàng"}</small></div>
      <div class="flow-popup-metric"><span>Tổng credit khả dụng</span><strong>${totalCredits.toLocaleString("vi-VN")}</strong></div>
    </div>
    <div class="flow-popup-toolbar">
      <div class="flow-popup-filters">
        <button type="button" class="ghost compact ${flowAccountsPopupFilter === "all" ? "active" : ""}" data-flow-popup-filter="all">Tất cả (${accounts.length})</button>
        <button type="button" class="ghost compact ${flowAccountsPopupFilter === "active" ? "active" : ""}" data-flow-popup-filter="active">🟢 Hoạt động (${activeAccounts.length})</button>
        <button type="button" class="ghost compact ${flowAccountsPopupFilter === "dead" ? "active" : ""}" data-flow-popup-filter="dead">🔴 Hết hạn (${deadAccounts.length})</button>
      </div>
      <div class="flow-popup-actions">
        <button type="button" class="primary compact" id="popupCheckAllAccountsBtn">🔄 Kiểm tra Session</button>
        <button type="button" class="ghost compact" id="popupCleanCacheBtn">⚡ Dọn Cache Thông Minh</button>
        ${deadAccounts.length ? `<button type="button" class="ghost compact" id="popupPruneDeadAccountsBtn">🧹 Xóa hết hạn (${deadAccounts.length})</button>` : ""}
        <button type="button" class="ghost compact" id="popupAddFlowAccountBtn">➕ Thêm tài khoản</button>
      </div>
    </div>
    <div class="flow-popup-account-list">
      ${filtered.length ? filtered.map(aiVisualRuntimeAccountHtml).join("") : `<div class="empty-state">Không có tài khoản nào trong bộ lọc này.</div>`}
    </div>
  `;

  content.querySelectorAll("[data-flow-popup-filter]").forEach(btn => btn.addEventListener("click", event => {
    flowAccountsPopupFilter = event.currentTarget.dataset.flowPopupFilter || "all";
    renderFlowAccountsDialogContent(job, lastAiVisualRuntimeSnapshot || runtime);
  }));
  content.querySelector("#popupCheckAllAccountsBtn")?.addEventListener("click", event => runCheckAllFlowAccounts(job, event.currentTarget));
  content.querySelector("#popupCleanCacheBtn")?.addEventListener("click", event => runCleanFlowAccountsCache(job, event.currentTarget));
  content.querySelector("#popupPruneDeadAccountsBtn")?.addEventListener("click", event => runPruneDeadFlowAccounts(job, event.currentTarget));
  content.querySelector("#popupAddFlowAccountBtn")?.addEventListener("click", async event => {
    const btn = event.currentTarget;
    btn.disabled = true;
    try {
      await api("/api/cofi-studio/runtime/accounts/login", { method: "POST" });
      toast("Đã mở cửa sổ Chrome để đăng nhập tài khoản Google Flow mới.");
      setTimeout(() => { if (job) refreshAiVisualRuntime(job, { silent: true }); }, 2000);
    } catch (err) {
      toast(`Không mở được đăng nhập Flow: ${err.message}`, true);
    } finally {
      btn.disabled = false;
    }
  });
  bindFlowAccountActionButtons(content, job);
}

function openFlowAccountsDialog(job, runtime) {
  const dialog = document.querySelector("#flowAccountsDialog");
  if (!dialog) return;
  renderFlowAccountsDialogContent(job, runtime || lastAiVisualRuntimeSnapshot);
  if (!dialog.open) dialog.showModal();
}

function closeFlowAccountsDialog() {
  const dialog = document.querySelector("#flowAccountsDialog");
  if (dialog?.open) dialog.close();
}

document.querySelector("#closeFlowAccountsDialog")?.addEventListener("click", closeFlowAccountsDialog);
document.querySelector("#flowAccountsDialog")?.addEventListener("click", event => {
  if (event.target === event.currentTarget) closeFlowAccountsDialog();
});

function buildAiVisualCardsHtml(jobId, generated) {
  return (Array.isArray(generated) ? generated : []).map(item => {
    const path = String(item.video_path || item.image_path || "");
    const isVideo = Boolean(item.video_path);
    const preview = path ? mediaUrl(jobId, path) : "";
    const visualLanguage = item?.visual_language || {};
    const styleBits = [visualLanguage.period, visualLanguage.color_mode, visualLanguage.style_notes].filter(Boolean).join(" · ");
    return `<article class="footage-card ai-visual-card">
      <div class="footage-media">${preview ? (isVideo
        ? `<div class="footage-video-placeholder" data-ai-video-src="${escapeHtml(preview)}">
             <img loading="lazy" decoding="async" src="${escapeHtml(mediaPosterUrl(jobId, path))}" alt="${escapeHtml(item.beat_id || "AI visual")}" />
             <div class="footage-play-trigger" title="Nhấn để phát video">
               <span class="footage-play-trigger-btn">▶</span>
             </div>
           </div>`
        : `<img loading="lazy" decoding="async" src="${escapeHtml(preview)}" alt="${escapeHtml(item.beat_id || "AI visual")}" />`) : ""}
        <div class="footage-badges"><b class="inspected">AI RECONSTRUCTION</b></div>
      </div>
      <div class="footage-card-body">
        <div class="footage-card-title"><strong>${escapeHtml(item.beat_id || "—")}</strong><span>${isVideo ? "Clip AI" : "Ảnh AI"}</span></div>
        <p>${isVideo ? "Ảnh AI đã được dùng làm keyframe rồi chuyển thành clip." : "Ảnh AI được giữ làm visual fallback."}</p>
        ${item.ai_reason ? `<p class="footage-reason"><b>Lý do dùng AI:</b> ${escapeHtml(item.ai_reason)}</p>` : ""}
        ${styleBits ? `<p><b>Visual language:</b> ${escapeHtml(styleBits)}</p>` : ""}
        ${item.video_error ? `<p class="footage-reason">Không tạo được clip; ảnh đã tạo vẫn được giữ và dùng ngay.</p>` : ""}
      </div>
    </article>`;
  }).join("");
}

let aiVisualManifestSyncInFlight = false;
async function syncAiVisualDialogFromDisk(job, fallbackTargetCount = 0) {
  if (!job || aiVisualManifestSyncInFlight) return;
  aiVisualManifestSyncInFlight = true;
  try {
    const manifestRaw = await artifact(job.id, "ai_visual_manifest.json");
    const manifest = safeJson(manifestRaw, {});
    const generated = Array.isArray(manifest.generated) ? manifest.generated : [];
    const errors = Array.isArray(manifest.errors) ? manifest.errors : [];
    const targets = Array.isArray(manifest.target_beat_ids) ? manifest.target_beat_ids : [];
    const remaining = Array.isArray(manifest.remaining_missing_beats) ? manifest.remaining_missing_beats : [];
    const targetCount = targets.length || fallbackTargetCount || 0;
    const clipCount = generated.filter(item => item.video_path).length;
    const imageCount = generated.filter(item => !item.video_path && item.image_path).length;
    const cards = buildAiVisualCardsHtml(job.id, generated);
    const summaryHtml = `<div><span>Beat cần AI</span><strong>${targetCount}</strong></div>
      <div><span>Đã tạo</span><strong>${generated.length}</strong></div>
      <div><span>Clip AI</span><strong>${clipCount}</strong></div>
      <div><span>Ảnh fallback</span><strong>${imageCount}</strong></div>
      <div><span>Lỗi tạo ảnh</span><strong>${errors.length}</strong></div>
      <div><span>Còn thiếu</span><strong>${remaining.length}</strong></div>`;
    const noteHtml = `Đã nhắm ${targetCount} beat; tạo được ${generated.length}, còn ${remaining.length}. AI media được ghi nhãn <b>illustrative reconstruction</b>, không giả làm tư liệu thật.`;
    const resultsHtml = cards ? `<div class="footage-grid">${cards}</div>` : `<div class="empty-state">Chưa có AI visual được tạo cho dự án này.</div>`;
    const dialogTitle = document.querySelector("#aiVisualDialogTitle");
    if (dialogTitle) dialogTitle.textContent = `Thư viện boxcard ảnh & video AI (${generated.length}/${targetCount} beat)`;
    const dialogContent = document.querySelector("#aiVisualDialogContent");
    if (dialogContent) {
      dialogContent.innerHTML = `<section class="footage-summary" data-ai-visual-summary>${summaryHtml}</section>
        <div class="workspace-note" data-ai-visual-note>${noteHtml}</div>
        <div data-ai-visual-results>${resultsHtml}</div>`;
      bindFootageVideoPlaceholders(dialogContent);
    }
  } catch (_) {
  } finally {
    aiVisualManifestSyncInFlight = false;
  }
}

function syncAiVisualQuickbarDom(job, runtime) {
  const root = document.querySelector("#aiVisualWorkspace");
  if (!root || String(root.dataset.aiVisualJobId || "") !== String(job.id)) return;
  const progress = runtime?.job || {};
  const sceneCounts = progress.scene_counts || runtime?.queue?.scene_counts || {};
  const genCount = Number(progress.generated ?? 0);
  const targetCount = Number(progress.targets ?? 0);
  const clipCount = Number(progress.clip_count ?? 0);
  const imageCount = Number(progress.image_count ?? Math.max(0, genCount - clipCount));
  const remainingCount = Number(progress.remaining ?? Math.max(0, targetCount - genCount));
  const runningScenes = Number(sceneCounts.running ?? 0);
  const queuedScenes = Number(sceneCounts.queued ?? 0);
  const totalScenes = Number(sceneCounts.total ?? 0);

  const statsEl = root.querySelector(".ai-visual-quick-stats");
  if (statsEl) {
    const liveQueuePill = (runningScenes > 0 || queuedScenes > 0)
      ? `<span class="ai-visual-stat-pill" style="border-color:rgba(56,189,248,0.45);color:#38bdf8;">⚡ Đang tạo <b>${runningScenes}</b> · Chờ <b>${queuedScenes}</b></span>`
      : "";
    const remPill = remainingCount > 0
      ? `<span class="ai-visual-stat-pill warn"><b>${remainingCount}</b> còn thiếu</span>`
      : (targetCount > 0 ? `<span class="ai-visual-stat-pill success">Hoàn thành</span>` : `<span class="ai-visual-stat-pill"><b>0</b> còn thiếu</span>`);
    statsEl.innerHTML = `<span class="ai-visual-stat-pill"><b>${genCount}/${targetCount}</b> beat đã tạo</span>
      <span class="ai-visual-stat-pill"><b>${clipCount}</b> clip AI</span>
      <span class="ai-visual-stat-pill"><b>${imageCount}</b> ảnh fallback</span>
      ${remPill}
      ${liveQueuePill}`;
  }
  const bottomBtn = root.querySelector("#openAiVisualDialogBottomBtn");
  if (bottomBtn) {
    bottomBtn.innerHTML = `🖼 Xem thư viện boxcard đã tạo (${genCount}) ↗`;
  }
  const resetBtn = root.querySelector("#resetAiVisualProgressBtn");
  if (resetBtn && !resetBtn.dataset.busy) {
    resetBtn.disabled = !(genCount > 0 || totalScenes > 0);
  }
  const topBtn = root.querySelector("#openAiVisualDialogBtn");
  if (topBtn) {
    topBtn.innerHTML = `🖼 Xem kết quả AI (${genCount}/${targetCount})`;
    topBtn.title = `Mở popup xem đầy đủ ${genCount} boxcard ảnh và video AI`;
  }
  const stamp = `${progress.manifest_updated_at || ""}|${genCount}|${clipCount}|${imageCount}|${remainingCount}|${targetCount}`;
  if (root.dataset.aiVisualManifestStamp !== stamp) {
    root.dataset.aiVisualManifestStamp = stamp;
    syncAiVisualDialogFromDisk(job, targetCount);
  }
}

function renderAiVisualRuntimePanel(job, runtime, error = "") {
  const panel = document.querySelector("#aiVisualRuntimePanel");
  if (!panel || String(panel.dataset.jobId || "") !== String(job.id)) return;
  if (error) {
    panel.innerHTML = `<div class="flow-glabs-summary-bar"><div class="flow-glabs-summary-info"><span class="flow-glabs-dot offline"></span><div><strong>Không đọc được trạng thái Flow</strong><small>${escapeHtml(error)}</small></div></div></div>`;
    return;
  }
  lastAiVisualRuntimeSnapshot = runtime;
  syncAiVisualQuickbarDom(job, runtime);
  const progress = runtime?.job || {};
  const accounts = Array.isArray(runtime?.accounts) ? runtime.accounts : [];
  const activeAccounts = accounts.filter(isFlowAccountReady);
  const usable = activeAccounts.length;
  const deadCount = accounts.length - usable;
  const totalCredits = activeAccounts.reduce((sum, acc) => sum + Number(acc.credits || 0), 0);
  const ultraCount = activeAccounts.filter(acc => String(acc.tier || "").toLowerCase() === "ultra").length;
  const proCount = activeAccounts.filter(acc => String(acc.tier || "").toLowerCase() === "pro").length;
  const freeCount = activeAccounts.filter(acc => !["ultra", "pro"].includes(String(acc.tier || "").toLowerCase())).length;
  const remainingCount = Number(progress.remaining || 0);

  panel.innerHTML = `<div class="flow-glabs-summary-bar">
      <div class="flow-glabs-summary-info">
        <span class="flow-glabs-dot ${usable ? "online" : "offline"}"></span>
        <div>
          <strong>${usable}/${accounts.length} tài khoản hoạt động${deadCount > 0 ? ` · <span class="warn-inline">${deadCount} hết hạn</span>` : ""}</strong>
          <small>${totalCredits.toLocaleString("vi-VN")} credit · ${ultraCount} ULTRA · ${proCount} PRO · ${freeCount} FREE</small>
        </div>
      </div>
      <div class="flow-glabs-summary-actions">
        <button class="primary compact" id="openFlowAccountsPopupBtn" type="button">👥 Quản lý tài khoản (${accounts.length})</button>
        <button class="ghost compact" id="checkAllFlowAccountsBtn" type="button">🔄 Kiểm tra Session</button>
        ${deadCount ? `<button class="ghost compact" id="pruneDeadFlowAccountsBtn" type="button">🧹 Xóa hết hạn (${deadCount})</button>` : ""}
        ${remainingCount > 0 ? `<button class="primary compact" id="aiRuntimeResumeBtn" type="button">▶ Chạy tiếp (${remainingCount})</button>` : ""}
      </div>
    </div>`;

  const dialog = document.querySelector("#flowAccountsDialog");
  if (dialog?.open) {
    renderFlowAccountsDialogContent(job, runtime);
  }

  panel.querySelector("#openFlowAccountsPopupBtn")?.addEventListener("click", () => openFlowAccountsDialog(job, runtime));
  panel.querySelector("#checkAllFlowAccountsBtn")?.addEventListener("click", event => runCheckAllFlowAccounts(job, event.currentTarget));
  panel.querySelector("#pruneDeadFlowAccountsBtn")?.addEventListener("click", event => runPruneDeadFlowAccounts(job, event.currentTarget));
  panel.querySelector("#aiRuntimeResumeBtn")?.addEventListener("click", async event => {
    event.currentTarget.disabled = true;
    event.currentTarget.textContent = "Đang chạy tiếp…";
    try {
      await api("/api/cofi-studio/runtime/queue/resume", { method: "POST" });
      const currentStatus = String(progress.phase_status || "pending");
      if (!["running", "queued"].includes(currentStatus)) {
        const endpoint = currentStatus === "pending"
          ? `/api/jobs/${encodeURIComponent(job.id)}/run/ai_visual`
          : `/api/jobs/${encodeURIComponent(job.id)}/rerun/ai_visual`;
        await api(endpoint, { method: "POST" });
      }
      toast("Đã tiếp tục tạo AI Visual.");
      await loadJobs(true);
      await refreshAiVisualRuntime(job);
    } catch (err) {
      toast(`Không tiếp tục được: ${err.message}`, true);
      await refreshAiVisualRuntime(job);
    }
  });
}

let aiVisualRuntimePollSeq = 0;
let aiVisualRuntimeRefreshInFlight = false;

async function refreshAiVisualRuntime(job, { silent = false } = {}) {
  if (aiVisualRuntimeRefreshInFlight) return lastAiVisualRuntimeSnapshot;
  aiVisualRuntimeRefreshInFlight = true;
  try {
    const runtime = await api(`/api/jobs/${encodeURIComponent(job.id)}/ai-visual-runtime`);
    renderAiVisualRuntimePanel(job, runtime);
    return runtime;
  } catch (err) {
    renderAiVisualRuntimePanel(job, null, err.message);
    if (!silent) toast(`Không đọc được Flow runtime: ${err.message}`, true);
    return null;
  } finally {
    aiVisualRuntimeRefreshInFlight = false;
  }
}

function scheduleAiVisualRuntimePoll(job) {
  const seq = ++aiVisualRuntimePollSeq;
  clearTimeout(aiVisualRuntimePollTimer);
  const tick = async () => {
    if (seq !== aiVisualRuntimePollSeq) return;
    if (state.appTab !== "ai_visual" || state.selectedId !== job.id) return;
    await refreshAiVisualRuntime(job, { silent: true });
    if (seq !== aiVisualRuntimePollSeq) return;
    aiVisualRuntimePollTimer = setTimeout(tick, 1500);
  };
  aiVisualRuntimePollTimer = setTimeout(tick, 1500);
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>'"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[c]));
}

function toast(message, error = false) {
  const el = $("#toast");
  if (el) {
    el.textContent = message;
    el.className = `toast show${error ? " error" : ""}`;
  }
  $$("dialog[open] .dialog-toast-pill").forEach(pill => {
    pill.textContent = message;
    pill.className = `dialog-toast-pill is-visible${error ? " is-error" : ""}`;
  });
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => {
    if (el) el.className = "toast";
    $$(".dialog-toast-pill").forEach(pill => {
      pill.className = "dialog-toast-pill";
    });
  }, 3600);
}
window.toast = toast;

const studioReaderStore = new Map();
let studioReaderSeq = 0;

function registerStudioReaderPayload(payload) {
  if (studioReaderStore.size > 240) {
    const oldestKey = studioReaderStore.keys().next().value;
    if (oldestKey) studioReaderStore.delete(oldestKey);
  }
  const key = `sr-${++studioReaderSeq}`;
  studioReaderStore.set(key, payload);
  return key;
}

function openStudioDialogById(dialogId) {
  const dlg = document.getElementById(dialogId);
  if (!dlg) return null;
  if (typeof dlg.showModal === "function") {
    if (!dlg.open) dlg.showModal();
  } else {
    dlg.setAttribute("open", "");
  }
  return dlg;
}

function closeStudioDialogById(dialogId) {
  const dlg = document.getElementById(dialogId);
  if (!dlg) return;
  if (typeof dlg.close === "function" && dlg.open) {
    dlg.close();
  } else {
    dlg.removeAttribute("open");
  }
}

function switchDnaStudioTab(tabName = "identity") {
  const target = String(tabName || "identity");
  $$("#dnaStudioTabsNav [data-dna-tab]").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.dnaTab === target);
  });
  $$("#dnaStudioEditorDialog .dna-tab-pane[data-dna-pane]").forEach(pane => {
    pane.classList.toggle("active", pane.dataset.dnaPane === target);
  });
}

function openDnaStudioModal(tabName = "identity") {
  if (state.appTab !== "radar") {
    setAppTab("radar");
  }
  const activeProfile = typeof currentChannelProfile === "function" ? currentChannelProfile() : null;
  const titleEl = $("#dnaStudioDialogTitle");
  if (titleEl) {
    titleEl.textContent = activeProfile
      ? `DNA KÊNH · ${(activeProfile.label || activeProfile.id).toUpperCase()}`
      : "TẠO HỒ SƠ DNA KÊNH MỚI · 5 TẦNG CHUYÊN GIA";
  }
  switchDnaStudioTab(tabName);
  return openStudioDialogById("dnaStudioEditorDialog");
}

function openStudioInspectorModal({
  badge = "📜",
  title = "Chi tiết tài liệu",
  subtitle = "Chế độ đọc tập trung · 15 Phòng Ban Chuyên Môn",
  html = "",
  rawText = "",
  isCode = false,
  onOpen = null,
} = {}) {
  const dlg = $("#studioInspectorDialog");
  const badgeEl = $("#studioInspectorBadge");
  const titleEl = $("#studioInspectorTitle");
  const subEl = $("#studioInspectorSubtitle");
  const bodyEl = $("#studioInspectorBody");
  const copyBtn = $("#studioInspectorCopyBtn");
  if (!dlg || !bodyEl) return null;
  if (badgeEl) badgeEl.textContent = badge;
  if (titleEl) titleEl.textContent = title;
  if (subEl) subEl.textContent = subtitle;
  dlg.dataset.copyText = String(rawText || "");
  if (copyBtn) {
    copyBtn.classList.toggle("hidden", !rawText && Boolean(html));
  }
  if (html) {
    bodyEl.innerHTML = html;
  } else {
    bodyEl.innerHTML = `<pre class="inspector-reader-pre${isCode ? " is-code" : ""}">${escapeHtml(rawText || "Chưa có dữ liệu.")}</pre>`;
  }
  openStudioDialogById("studioInspectorDialog");
  bodyEl.scrollTop = 0;
  if (typeof onOpen === "function") {
    onOpen(bodyEl, dlg);
  }
  return dlg;
}
window.openStudioInspectorModal = openStudioInspectorModal;
window.openDnaStudioModal = openDnaStudioModal;

document.addEventListener("click", event => {
  const closeTrigger = event.target.closest("[data-close-dialog]");
  if (closeTrigger) {
    event.preventDefault();
    closeStudioDialogById(closeTrigger.dataset.closeDialog);
    return;
  }
  const dnaTabBtn = event.target.closest("#dnaStudioTabsNav [data-dna-tab]");
  if (dnaTabBtn) {
    event.preventDefault();
    switchDnaStudioTab(dnaTabBtn.dataset.dnaTab);
    return;
  }
  const readerBtn = event.target.closest("[data-studio-reader-key]");
  if (readerBtn) {
    event.preventDefault();
    event.stopPropagation();
    const payload = studioReaderStore.get(readerBtn.dataset.studioReaderKey);
    if (payload) openStudioInspectorModal(payload);
    return;
  }
  if (event.target instanceof HTMLDialogElement && ["dnaStudioEditorDialog", "selfLearningDialog", "marketScanDialog", "studioInspectorDialog"].includes(event.target.id)) {
    closeStudioDialogById(event.target.id);
  }
});

$("#closeDnaStudioDialogBtn")?.addEventListener("click", () => closeStudioDialogById("dnaStudioEditorDialog"));
$("#openDnaStudioModalBtn")?.addEventListener("click", () => openDnaStudioModal("identity"));
$("#openMarketScanModalBtn")?.addEventListener("click", () => openStudioDialogById("marketScanDialog"));
$("#openSelfLearningModalBtn")?.addEventListener("click", () => {
  openStudioDialogById("selfLearningDialog");
  if (state.selectedChannelProfileId && typeof renderSelfLearningReportForProfile === "function") {
    renderSelfLearningReportForProfile(state.selectedChannelProfileId);
  }
});
$("#studioInspectorCopyBtn")?.addEventListener("click", async () => {
  const dlg = $("#studioInspectorDialog");
  const text = String(dlg?.dataset?.copyText || $("#studioInspectorBody")?.innerText || "").trim();
  if (!text) return;
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
    }
    toast("Đã sao chép nội dung vào bộ nhớ tạm.");
  } catch (err) {
    toast("Không thể sao chép tự động.", true);
  }
});

function scrollToId(id) {
  document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
}

function setAppTab(tab) {
  if (tab === "codex") {
    state.globalCodexOpen = true;
    localStorage.setItem("cofi-global-chat-open", "1");
    document.body.classList.add("global-chat-open");
    tab = state.appTab === "codex" ? "overview" : state.appTab;
  }
  state.appTab = tab;
  if (tab !== "ai_visual") {
    clearTimeout(aiVisualRuntimePollTimer);
    aiVisualRuntimePollTimer = null;
  }
  $$('[data-app-tab]').forEach(btn => btn.classList.toggle("active", btn.dataset.appTab === tab));
  $$('[data-app-pane]').forEach(pane => pane.classList.toggle("active", pane.dataset.appPane === tab));
  updateStudioShell(tab);
  document.querySelector(".channel-studio-content")?.scrollTo({ top: 0, behavior: "auto" });
  document.querySelector("main")?.scrollTo({ top: 0, behavior: "auto" });
  if (["script", "voice", "visuals", "footage", "ai_visual", "edit", "seo", "qc"].includes(tab)) renderFunctionWorkspaces();
  if (tab === "projects" && state.selectedId) renderDetail();
  if (tab === "accounts") loadHealth().catch(err => toast(err.message, true));
  renderGlobalProducerChat({ loadHistory: state.globalCodexOpen }).catch(() => {});
}

function setHealth(id, ok, good = "Sẵn sàng", bad = "Chưa kết nối") {
  const el = $(id);
  if (!el) return;
  el.textContent = ok ? good : bad;
  el.className = ok ? "health-ok" : "health-bad";
}

const CHAT_IMAGE_TYPES = new Set(["image/png", "image/jpeg", "image/webp"]);
const CHAT_IMAGE_MAX_BYTES = 10 * 1024 * 1024;
const CHAT_IMAGE_MAX_COUNT = 4;

async function revealLocalJobMedia(jobId, rawPath, buttonEl = null) {
  const origText = buttonEl ? buttonEl.textContent : "";
  if (buttonEl) {
    buttonEl.disabled = true;
    buttonEl.textContent = "Đang mở thư mục…";
  }
  try {
    const res = await api(`/api/jobs/${encodeURIComponent(jobId)}/media/local-action`, {
      method: "POST",
      body: JSON.stringify({ path: rawPath, action: "reveal" }),
    });
    toast(`Đã mở thư mục chứa file: ${res.path || rawPath}`);
  } catch (err) {
    toast(`Không mở được thư mục: ${err.message || err}`, true);
  } finally {
    if (buttonEl) {
      buttonEl.disabled = false;
      buttonEl.textContent = origText;
    }
  }
}

async function saveLocalMediaDirectly(jobId, rawPath, suggestedFilename, buttonEl = null) {
  const origText = buttonEl ? buttonEl.textContent : "";
  if (buttonEl) {
    buttonEl.disabled = true;
    buttonEl.textContent = "⏳ Đang chọn thư mục lưu…";
  }
  try {
    const cleanSuggested = String(suggestedFilename || "").trim();
    const isGenericName = !cleanSuggested || ["video.mp4", "final.mp4", `video_${jobId}.mp4`].includes(cleanSuggested.toLowerCase());
    const res = await api(`/api/jobs/${encodeURIComponent(jobId)}/media/local-action`, {
      method: "POST",
      body: JSON.stringify({
        path: rawPath || "release/video.mp4",
        action: "save_copy",
        filename: isGenericName ? "" : cleanSuggested,
        open_folder_after: true,
      }),
    });
    if (res && res.cancelled) {
      return;
    }
    if (res && res.ok) {
      toast(`✅ Đã lưu video sang: ${res.saved_path}`);
      return;
    }
    throw new Error(res?.detail || res?.message || "Lỗi lưu video");
  } catch (err) {
    toast(`Không thể lưu video: ${err.message || err}`, true);
  } finally {
    if (buttonEl) {
      buttonEl.disabled = false;
      buttonEl.textContent = origText;
    }
  }
}

async function downloadFileWithSmartPicker(url, defaultFilename, buttonEl = null) {
  const safeName = String(defaultFilename || "video.mp4").trim();
  const lower = safeName.toLowerCase();
  let dlUrl = String(url || "").trim();
  if (dlUrl && dlUrl.includes("/media?") && !dlUrl.includes("download=1")) {
    dlUrl += `&download=1&filename=${encodeURIComponent(safeName)}`;
  }

  // Inside Desktop App (pywebview EdgeChromium): trigger <a download> so desktop_app.py's
  // _smart_on_download_starting opens native WinForms.SaveFileDialog(self.form) on top of the window
  // (allowing any drive/folder selection) and copies local files directly via shutil.copy2 at disk speed.
  if (typeof window !== "undefined" && window.pywebview) {
    const a = document.createElement("a");
    a.href = dlUrl || url;
    a.download = safeName;
    document.body.appendChild(a);
    a.click();
    a.remove();
    return;
  }

  let pickerTypes = [{ description: "Video MP4 (*.mp4)", accept: { "video/mp4": [".mp4"] } }];
  if (lower.endsWith(".jpg") || lower.endsWith(".jpeg")) {
    pickerTypes = [{ description: "Ảnh JPEG (*.jpg)", accept: { "image/jpeg": [".jpg", ".jpeg"] } }];
  } else if (lower.endsWith(".png")) {
    pickerTypes = [{ description: "Ảnh PNG (*.png)", accept: { "image/png": [".png"] } }];
  } else if (lower.endsWith(".webp")) {
    pickerTypes = [{ description: "Ảnh WebP (*.webp)", accept: { "image/webp": [".webp"] } }];
  } else if (lower.endsWith(".zip")) {
    pickerTypes = [{ description: "File nén ZIP (*.zip)", accept: { "application/zip": [".zip"] } }];
  } else if (lower.endsWith(".wav")) {
    pickerTypes = [{ description: "Âm thanh WAV (*.wav)", accept: { "audio/wav": [".wav"] } }];
  } else if (lower.endsWith(".srt")) {
    pickerTypes = [{ description: "Phụ đề SRT (*.srt)", accept: { "text/plain": [".srt"] } }];
  }

  if (typeof window !== "undefined" && typeof window.showSaveFilePicker === "function") {
    try {
      const handle = await window.showSaveFilePicker({
        suggestedName: safeName,
        types: pickerTypes,
      });
      const origText = buttonEl ? buttonEl.textContent : "";
      if (buttonEl) {
        buttonEl.style.pointerEvents = "none";
        buttonEl.textContent = "⏳ Đang lưu file…";
      }
      try {
        const resp = await fetch(dlUrl || url);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const writable = await handle.createWritable();
        if (resp.body && typeof resp.body.pipeTo === "function") {
          await resp.body.pipeTo(writable);
        } else {
          const blob = await resp.blob();
          await writable.write(blob);
          await writable.close();
        }
        toast(`✅ Đã lưu thành công: ${handle.name || safeName}`);
      } finally {
        if (buttonEl) {
          buttonEl.style.pointerEvents = "";
          buttonEl.textContent = origText;
        }
      }
      return;
    } catch (err) {
      if (err && err.name === "AbortError") return;
    }
  }
  const a = document.createElement("a");
  a.href = dlUrl || url;
  a.download = safeName;
  document.body.appendChild(a);
  a.click();
  a.remove();
}

function openChatLightbox(url, title = "Ảnh đính kèm") {
  const dialog = document.getElementById("chatImageLightbox");
  const img = document.getElementById("chatLightboxImg");
  const titleEl = document.getElementById("chatLightboxTitle");
  const downloadEl = document.getElementById("chatLightboxDownload");
  if (!dialog || !img) return;
  img.src = url;
  if (titleEl) titleEl.textContent = title;
  if (downloadEl) {
    downloadEl.href = url;
    const hasExt = /\.(png|jpe?g|webp|gif)$/i.test(String(title || "").trim());
    const safeImgName = hasExt ? String(title).trim() : "anh_dinh_kem.png";
    downloadEl.download = safeImgName;
    downloadEl.dataset.downloadFileUrl = url;
    downloadEl.dataset.downloadFilename = safeImgName;
  }
  if (typeof dialog.showModal === "function") {
    dialog.showModal();
  } else {
    dialog.setAttribute("open", "");
  }
}

function closeChatLightbox() {
  const dialog = document.getElementById("chatImageLightbox");
  if (!dialog) return;
  if (typeof dialog.close === "function") {
    dialog.close();
  } else {
    dialog.removeAttribute("open");
  }
}

function chatAttachmentGalleryHtml(attachments = []) {
  if (!Array.isArray(attachments) || !attachments.length) return "";
  return `<div class="chat-message-attachments">${attachments.map(item => {
    const url = escapeHtml(item.url || `/api/chat-attachments/${encodeURIComponent(item.id || "")}`);
    const name = escapeHtml(item.name || "Ảnh đính kèm");
    return `<a href="${url}" target="_blank" rel="noopener" title="${name}" data-lightbox-image="${url}" data-lightbox-title="${name}"><img src="${url}" alt="${name}" loading="lazy" /></a>`;
  }).join("")}</div>`;
}

function renderPendingChatAttachments(container, attachments = [], onRemove) {
  if (!container) return;
  container.innerHTML = attachments.map(item => {
    if (item.uploading) {
      return `<div class="chat-attachment-chip uploading"><span>⏳ ${escapeHtml(item.name || "Đang tải ảnh…")}</span></div>`;
    }
    const url = escapeHtml(item.url || `/api/chat-attachments/${encodeURIComponent(item.id || "")}`);
    return `<div class="chat-attachment-chip"><img src="${url}" alt="${escapeHtml(item.name || "Ảnh")}" /><span>${escapeHtml(item.name || "Ảnh")}</span><button type="button" data-remove-chat-attachment="${escapeHtml(item.id)}" aria-label="Bỏ ảnh">×</button></div>`;
  }).join("");
  container.querySelectorAll("[data-remove-chat-attachment]").forEach(button => {
    button.addEventListener("click", () => onRemove?.(String(button.dataset.removeChatAttachment || "")));
  });
}

async function uploadChatImage(file) {
  if (!file || !CHAT_IMAGE_TYPES.has(file.type)) throw new Error("Chỉ hỗ trợ ảnh PNG, JPEG hoặc WebP.");
  if (file.size > CHAT_IMAGE_MAX_BYTES) throw new Error("Mỗi ảnh tối đa 10 MB.");
  const response = await fetch(`/api/chat-attachments?filename=${encodeURIComponent(file.name || "image")}`, {
    method: "POST",
    headers: { "Content-Type": file.type },
    body: file,
  });
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try { detail = (await response.json()).detail || detail; } catch (_) {}
    throw new Error(detail);
  }
  return response.json();
}

async function appendSelectedChatImages(fileList, current, onUpdate) {
  const files = [...(fileList || [])];
  if (!files.length) return current;
  if (current.length + files.length > CHAT_IMAGE_MAX_COUNT) throw new Error(`Mỗi tin nhắn tối đa ${CHAT_IMAGE_MAX_COUNT} ảnh.`);
  const next = [...current];
  for (const file of files) {
    const tempId = `uploading-${Date.now()}-${Math.random()}`;
    const placeholder = { id: tempId, name: file.name || "Đang tải ảnh…", uploading: true };
    next.push(placeholder);
    onUpdate?.([...next]);
    try {
      const uploaded = await uploadChatImage(file);
      const idx = next.findIndex(item => item.id === tempId);
      if (idx !== -1) next[idx] = uploaded;
      else next.push(uploaded);
      onUpdate?.([...next]);
    } catch (err) {
      const idx = next.findIndex(item => item.id === tempId);
      if (idx !== -1) next.splice(idx, 1);
      onUpdate?.([...next]);
      throw err;
    }
  }
  return next.filter(item => !item.uploading);
}

async function appendPastedChatImages(event, current, onUpdate) {
  const itemFiles = [...(event.clipboardData?.items || [])]
    .filter(item => item.kind === "file" && CHAT_IMAGE_TYPES.has(item.type))
    .map(item => item.getAsFile())
    .filter(Boolean);
  const files = itemFiles.length
    ? itemFiles
    : [...(event.clipboardData?.files || [])].filter(file => CHAT_IMAGE_TYPES.has(file.type));
  if (!files.length) return current;
  event.preventDefault();
  return appendSelectedChatImages(files, current, onUpdate);
}

function renderAiAccounts(health) {
  const accounts = health.ai_accounts || {};
  const codex = accounts.codex || {};
  const gemini = accounts.gemini || {};
  const router = accounts.router || health.ai_router || {};
  const trail = accounts.trail || health.trail_code || {};
  if ($("#aiTrailStatus")) {
    setHealth("#aiTrailStatus", Boolean(trail.ok), `Đã kích hoạt (v${trail.version || "0.26.0"})`, trail.installed ? "Chưa đồng bộ Graph" : "Chưa cài đặt");
  }
  if ($("#aiTrailGraph")) {
    $("#aiTrailGraph").textContent = trail.ok
      ? `${Number(trail.total_nodes || 0).toLocaleString("vi-VN")} symbols · ${Number(trail.total_edges || 0).toLocaleString("vi-VN")} edges (${trail.total_cached_files || 0} files)`
      : "Chưa lập chỉ mục";
  }
  if ($("#aiTrailLearnings")) {
    $("#aiTrailLearnings").textContent = `${trail.learnings_count || 0} quy tắc cốt lõi (.trail/learnings/)`;
  }
  if ($("#aiTrailAgents")) {
    $("#aiTrailAgents").textContent = Array.isArray(trail.wired_agents) && trail.wired_agents.length
      ? trail.wired_agents.join(" · ")
      : "Chưa gắn";
  }

  setHealth("#aiCodexStatus", Boolean(codex.ready), "Đã đăng nhập · sẵn sàng", "Chưa sẵn sàng");
  setHealth("#aiGeminiStatus", Boolean(gemini.ready), "Đã đăng nhập · Ultra", "Chưa sẵn sàng");

  if ($("#aiCodexMethod")) $("#aiCodexMethod").textContent = codex.auth_method || "Codex CLI + ChatGPT bridge";
  if ($("#aiCodexPath")) $("#aiCodexPath").textContent = codex.executable || "—";
  if ($("#aiCodexBridge")) $("#aiCodexBridge").textContent = codex.bridge_ready ? "Đã kết nối" : "Chưa kết nối";
  if ($("#aiCodexAction")) $("#aiCodexAction").textContent = codex.action || "Codex đang dùng phiên đăng nhập local hiện tại.";

  if ($("#aiGeminiMethod")) $("#aiGeminiMethod").textContent = gemini.auth_method === "antigravity-cli" ? "Antigravity CLI · Google/Ultra" : (gemini.auth_method || "Chưa xác định");
  if ($("#aiGeminiPath")) $("#aiGeminiPath").textContent = gemini.executable || "—";
  if ($("#aiGeminiTransport")) $("#aiGeminiTransport").textContent = gemini.transport === "antigravity" ? "Antigravity" : (gemini.transport || "Gemini CLI");
  if ($("#aiGeminiAction")) $("#aiGeminiAction").textContent = gemini.action || "Gemini dùng phiên Google/Ultra của Antigravity, không dùng API key.";
  const geminiModelSelect = $("#aiGeminiModel");
  if (geminiModelSelect) {
    const models = Array.isArray(gemini.models) ? gemini.models : [];
    const selectedModel = String(gemini.model || "");
    geminiModelSelect.innerHTML = [
      `<option value="">Mặc định Antigravity</option>`,
      ...models.map(item => `<option value="${escapeHtml(item.id || "")}">${escapeHtml(item.label || item.id || "")}</option>`),
    ].join("");
    if (selectedModel && models.some(item => String(item.id || "") === selectedModel)) {
      geminiModelSelect.value = selectedModel;
    } else {
      geminiModelSelect.value = "";
    }
    geminiModelSelect.disabled = !Boolean(gemini.ready) || models.length === 0;
  }

  const active = String(router.active_provider || "codex");
  const selectionMode = String(health.chat_provider || router.selection_mode || "auto");
  const providerName = active === "gemini" ? "Gemini / Antigravity" : "Codex";
  const order = Array.isArray(router.order) ? router.order.map(item => item === "gemini" ? "Gemini" : "Codex").join(" → ") : "Codex → Gemini";
  if ($("#aiRouterStatus")) {
    const fixedReady = active === "gemini" ? Boolean(gemini.ready) : Boolean(codex.ready);
    $("#aiRouterStatus").textContent = selectionMode === "auto" ? "Auto · tự xoay vòng" : `Cố định ${providerName}`;
    $("#aiRouterStatus").className = selectionMode === "auto" || fixedReady ? "health-ok" : "health-bad";
  }
  if ($("#aiRouterActive")) $("#aiRouterActive").textContent = providerName;
  if ($("#aiRouterOrder")) $("#aiRouterOrder").textContent = order;
  [$("#chatProviderSelect"), $("#globalChatProviderSelect")].filter(Boolean).forEach(select => {
    select.value = selectionMode;
  });
  syncChatModelSelects(health);
  if ($("#aiRouterSwitch")) {
    const last = router.last_switch;
    if (last?.at) {
      const when = new Date(last.at);
      const whenText = Number.isNaN(when.getTime()) ? last.at : when.toLocaleString("vi-VN");
      const from = last.from === "gemini" ? "Gemini" : "Codex";
      const to = last.to === "gemini" ? "Gemini" : "Codex";
      $("#aiRouterSwitch").textContent = `${from} → ${to} · ${whenText} · ${last.label || ""}`.trim();
    } else {
      $("#aiRouterSwitch").textContent = "Chưa có";
    }
  }
}

const ANTIGRAVITY_MODEL_LABELS = {
  "gemini-4-argon-high": "Gemini 4 Argon (High)",
  "gemini-4-argon-medium": "Gemini 4 Argon (Medium)",
  "gemini-4-argon-low": "Gemini 4 Argon (Low)",
  "gemini-3.8-flash-high": "Gemini 3.8 Flash (High)",
  "gemini-3.8-flash-medium": "Gemini 3.8 Flash (Medium)",
  "gemini-3.8-flash-low": "Gemini 3.8 Flash (Low)",
  "claude-opus-5-5-high": "Claude Opus 5.5 (High)",
  "claude-opus-5-5-medium": "Claude Opus 5.5 (Medium)",
  "claude-opus-5-5-low": "Claude Opus 5.5 (Low)",
  "claude-sonnet-5-5-high": "Claude Sonnet 5.5 (High)",
  "claude-sonnet-5-5-medium": "Claude Sonnet 5.5 (Medium)",
  "claude-sonnet-5-5-low": "Claude Sonnet 5.5 (Low)",
  "gpt-oss-120b-medium": "GPT-OSS 120B (Medium)",
  "codex": "OpenAI Codex CLI",
};

function humanizeAntigravityModel(modelId) {
  const id = String(modelId || "").trim();
  if (!id) return "Gemini 3.8 Flash (High)";
  if (ANTIGRAVITY_MODEL_LABELS[id]) return ANTIGRAVITY_MODEL_LABELS[id];
  const models = state.health?.ai_accounts?.gemini?.models || [];
  const found = models.find(item => String(item.id || "") === id);
  return found?.label || id;
}

function currentChatModelId() {
  const selectionMode = String(state.health?.chat_provider || state.health?.ai_router?.selection_mode || "auto").toLowerCase();
  if (selectionMode === "codex") return "codex";
  return String(state.health?.ai_accounts?.gemini?.model || "gemini-3.8-flash-high").trim() || "gemini-3.8-flash-high";
}

function syncChatModelSelects(health = state.health) {
  if (!health) return;
  const gemini = health.ai_accounts?.gemini || {};
  const models = Array.isArray(gemini.models) ? gemini.models : [];
  const selectionMode = String(health.chat_provider || health.ai_router?.selection_mode || "auto").toLowerCase();
  const activeModelId = selectionMode === "codex"
    ? "codex"
    : (String(gemini.model || "gemini-3.8-flash-high").trim() || "gemini-3.8-flash-high");
  const activeLabel = humanizeAntigravityModel(activeModelId);
  [$("#globalChatModelSelect"), $("#producerChatModelSelect")].filter(Boolean).forEach(select => {
    for (const item of models) {
      const id = String(item?.id || "").trim();
      if (!id) continue;
      if (!Array.from(select.options).some(opt => opt.value === id)) {
        const opt = document.createElement("option");
        opt.value = id;
        opt.textContent = item.label || humanizeAntigravityModel(id);
        select.appendChild(opt);
      }
    }
    if (Array.from(select.options).some(opt => opt.value === activeModelId)) {
      select.value = activeModelId;
    }
  });
  [$("#globalCodexModelBadge"), $("#producerCodexModelBadge")].filter(Boolean).forEach(badge => {
    badge.textContent = activeLabel;
  });
}

async function selectChatModel(modelValue) {
  const value = String(modelValue || "").trim();
  if (!value) return;
  if (value === "codex") {
    await saveChatProvider("codex");
    syncChatModelSelects(state.health);
    return;
  }
  const result = await api("/api/ai-accounts/gemini/settings", {
    method: "PATCH",
    body: JSON.stringify({ model: value }),
  });
  if (String(state.health?.chat_provider || "").toLowerCase() !== "gemini") {
    await api("/api/chat-provider", {
      method: "PATCH",
      body: JSON.stringify({ provider: "gemini" }),
    });
  }
  await loadHealth();
  syncChatModelSelects(state.health);
  toast(`Đã chọn model AI: ${result.label || humanizeAntigravityModel(value)}`);
}

async function startAiAccountLogin(provider) {
  const result = await api(`/api/ai-accounts/${encodeURIComponent(provider)}/login`, { method: "POST" });
  toast(result.message || "Đã mở luồng đăng nhập.");
  setTimeout(() => loadHealth().catch(() => {}), 1500);
}

async function saveGeminiModel(model) {
  const result = await api("/api/ai-accounts/gemini/settings", {
    method: "PATCH",
    body: JSON.stringify({ model }),
  });
  toast(result.model ? `Đã chọn ${result.label || result.model}.` : "Đã dùng model mặc định của Antigravity.");
  await loadHealth();
}

async function saveChatProvider(provider) {
  const result = await api("/api/chat-provider", {
    method: "PATCH",
    body: JSON.stringify({ provider }),
  });
  state.health = state.health || {};
  state.health.chat_provider = result.chat_provider;
  state.health.ai_router = result.router || state.health.ai_router || {};
  state.health.ai_accounts = state.health.ai_accounts || {};
  state.health.ai_accounts.router = state.health.ai_router;
  [$("#chatProviderSelect"), $("#globalChatProviderSelect")].filter(Boolean).forEach(select => {
    select.value = result.chat_provider;
  });
  renderAiAccounts(state.health);
  if (state.appTab === "codex") await renderProducerChat();
  if (state.globalCodexOpen && state.appTab !== "codex") await renderGlobalProducerChat({ loadHistory: true });
  toast(`Đã đổi AI điều khiển toàn app: ${result.chat_provider}.`);
}

async function loadHealth({ cached = false } = {}) {
  try {
    const h = await api(cached ? "/api/health?cached=1" : "/api/health");
    if (!h.trail_code) {
      try {
        const r = await fetch(`/static/trail_status.json?t=${Date.now()}`, { cache: "no-store" });
        if (r.ok) {
          h.trail_code = await r.json();
          h.ai_accounts = h.ai_accounts || {};
          h.ai_accounts.trail = h.trail_code;
        }
      } catch (_) {}
    }
    state.health = h;
    setHealth("#healthRadar", h.cofi_radar?.ok, "Đã kết nối", "Radar chưa kết nối");
    const codexCliOk = Boolean(h.codex_cli?.ok);
    const codexWebOk = Boolean(h.chatgpt_web_bridge?.ok);
    const codexWebRunning = h.chatgpt_web_bridge?.status === "running";
    const codexReady = (codexCliOk && codexWebOk) || codexWebOk;
    const codexWebLabel = codexWebRunning ? "Đã kết nối · đang chạy" : codexWebOk ? "Đã kết nối" : codexCliOk ? "Bridge chưa kết nối" : "Không tìm thấy Codex";
    setHealth("#healthCodex", codexReady, codexWebLabel, codexWebLabel);
    const geminiReady = Boolean(h.gemini_cli?.ok && (h.gemini_cli?.ready ?? true));
    const geminiAuthMethod = h.gemini_cli?.auth_method || "";
    const geminiReadyLabel = geminiAuthMethod === "antigravity-cli" ? "Antigravity · Ultra" : "Sẵn sàng";
    const geminiUnavailableLabel = h.gemini_cli?.action || (h.gemini_cli?.ok ? "Chưa đăng nhập" : "Không tìm thấy");
    setHealth("#healthGemini", geminiReady, geminiReadyLabel, geminiUnavailableLabel);
    if ($("#healthGeminiNote")) $("#healthGeminiNote").textContent = geminiReady ? "Dự phòng tự động cho Codex" : "Mở Tài khoản AI để đăng nhập";
    renderAiAccounts(h);
    setHealth("#healthVoice", h.cofi_voice?.ok, "Đã kết nối", "Giọng đọc chưa kết nối");
    setHealth("#healthRemotion", h.cofi_remotion?.ok, h.cofi_remotion?.studio_running ? "Xem trước đang chạy" : "Sẵn sàng", "Không tìm thấy");
    const trailInfo = h.trail_code || h.ai_accounts?.trail || {};
    setHealth("#healthTrail", Boolean(trailInfo.ok), `${Number(trailInfo.total_nodes || 4610).toLocaleString("vi-VN")} symbols · ${trailInfo.learnings_count || 4} Learnings`, "Bấm để đồng bộ 1-Click");
    const critical = (codexReady || geminiReady) && Boolean(h.cofi_voice?.ok) && Boolean(h.cofi_remotion?.ok);
    $("#systemPulse").className = `pulse ${critical ? "ok" : "warn"}`;
    $("#systemLabel").textContent = h.active_job_id ? "Đang sản xuất" : critical ? "Hệ thống sẵn sàng" : "Cần kiểm tra bộ máy";
    $("#systemSub").textContent = h.active_job_id
      ? `Codex Web ${codexWebRunning ? "đang chạy" : codexWebOk ? "đã kết nối" : "chưa kết nối"} · Dự án ${h.active_job_id}`
      : `Codex Web ${codexWebOk ? "đã kết nối" : "chưa kết nối"} · Gemini ${geminiReady ? "Ultra sẵn sàng" : "chưa đăng nhập"}`;
    if ($("#overviewSystemText")) {
      const selectedJob = state.jobs?.find(j => j.id === state.selectedId);
      const isPaused = Boolean(selectedJob?.is_paused || selectedJob?.phases?.[selectedJob?.current_phase]?.is_paused);
      if (isPaused) {
        $("#overviewSystemText").textContent = `Dự án đang tạm dừng: ${selectedJob?.pause_warning || "Cần kiểm tra tài khoản hoặc hàng đợi"}`;
      } else if (h.active_job_id) {
        $("#overviewSystemText").textContent = "Xưởng đang sản xuất";
      } else {
        $("#overviewSystemText").textContent = critical ? "Tất cả bộ máy chính đã sẵn sàng" : "Một số bộ máy cần kiểm tra";
      }
    }
  } catch (err) {
    $("#systemPulse").className = "pulse warn";
    $("#systemLabel").textContent = "Máy chủ ứng dụng chưa kết nối";
    if ($("#overviewSystemText")) $("#overviewSystemText").textContent = "Máy chủ ứng dụng chưa kết nối";
  }
}

async function loadVoices() {
  try {
    const voices = await api("/api/voice/voices");
    state.voices = Array.isArray(voices) ? voices : [];
    const select = $("#voiceSelect");
    select.innerHTML = `<option value="">Giọng mặc định</option>` + state.voices.map(v => `<option value="${escapeHtml(v.id)}">${escapeHtml(v.name || v.id)} · ${escapeHtml(v.language || "")}</option>`).join("");
  } catch (_) {
    state.voices = [];
    $("#voiceSelect").innerHTML = `<option value="">Giọng mặc định (CofiVoice chưa kết nối)</option>`;
  }
}

function normalizeTopic(item, meta = {}) {
  const competitorSupport = Array.isArray(item.competitor_support) ? item.competitor_support : [];
  const baseNote = item.production_brief || item.note || "";
  const supportNote = competitorSupport.length
    ? `Kênh mẫu cùng xác nhận: ${competitorSupport.map(row => row.channel).filter(Boolean).join(", ")}.`
    : "";
  const codexReasons = Array.isArray(item.codex_reasons) ? item.codex_reasons : [];
  const ownWinnerEvidence = Array.isArray(item.own_winner_evidence) ? item.own_winner_evidence : [];
  const competitorWinnerEvidence = Array.isArray(item.competitor_winner_evidence) ? item.competitor_winner_evidence : [];
  const winnerCluster = String(item.winner_cluster || "").trim();
  const winnerNote = item.proven_winner_match === true
    ? [
        winnerCluster ? `Cụm thắng: ${winnerCluster}.` : "Khớp cụm chủ đề đã thắng.",
        ownWinnerEvidence.length ? `Kênh mình: ${ownWinnerEvidence.slice(0, 2).join(" | ")}.` : "",
        competitorWinnerEvidence.length ? `Đối thủ: ${competitorWinnerEvidence.slice(0, 2).join(" | ")}.` : "",
      ].filter(Boolean).join(" ")
    : "";
  const codexNote = item.codex_status === "ok"
    ? [`Codex ${String(item.codex_verdict || "watch").toUpperCase()} ${item.codex_score != null ? `${Number(item.codex_score).toFixed(0)}/100` : ""}.`, ...codexReasons.slice(0, 2), item.codex_angle ? `Góc làm: ${item.codex_angle}` : ""].filter(Boolean).join(" ")
    : item.codex_status === "unavailable" ? "Codex chưa khả dụng; đang hiển thị thứ tự fallback từ Radar." : "";
  return {
    raw: item,
    title: item.title || item.topic_anchor || item.evidence_title || item.label || "Chủ đề chưa có tên",
    titleTarget: item.title_target || null,
    titleVi: item.title_vi || null,
    topicStream: item.topic_stream || null,
    streamBadgeVi: item.stream_badge_vi || null,
    streamLabelVi: item.stream_label_vi || null,
    caseRealNameZh: item.case_real_name_zh || null,
    archivalSearchKeywordsZh: Array.isArray(item.archival_search_keywords_zh) ? item.archival_search_keywords_zh : [],
    recommendedVoxVerbs: Array.isArray(item.recommended_vox_verbs) ? item.recommended_vox_verbs : [],
    researchOrigin: item.research_origin || item.trend_source || null,
    seoKeywordDna: item.seo_keyword_dna || meta.seoKeywordDna || null,
    videoId: item.video_id || item.id || item.evidence_video_id || null,
    url: item.url || item.video_url || item.evidence_url || "",
    market: item.market || meta.market || "KR",
    vph: item.vph ?? item.evidence_vph,
    outlier: item.outlier ?? item.evidence_outlier,
    views: item.views ?? item.evidence_views,
    profileScore: item.profile_score,
    radarProfileScore: item.radar_profile_score,
    codexScore: item.codex_score,
    codexVerdict: item.codex_verdict,
    codexStatus: item.codex_status,
    provenWinnerMatch: item.proven_winner_match === true,
    winnerCluster,
    ownWinnerEvidence,
    competitorWinnerEvidence,
    competitorSupportCount: item.competitor_support_count,
    scanId: meta.scanId || item.scan_id || null,
    profileId: meta.profileId || item.profile_id || null,
    targetDurationMinutes: Number(meta.targetDurationMinutes || item.target_duration_minutes || 0) || null,
    caseNote: baseNote,
    note: [winnerNote, codexNote, baseNote, supportNote].filter(Boolean).join(" "),
  };
}

function renderRadarResults(items, meta = {}) {
  state.radarItems = items.map(item => normalizeTopic(item, meta));
  const root = $("#radarResults");
  if (!state.radarItems.length) {
    root.innerHTML = `<div class="empty-state">Không có chủ đề phù hợp trong kết quả này.</div>`;
    return;
  }
  root.innerHTML = state.radarItems.slice(0, 30).map((item, index) => `
    <article class="topic-card">
      <div class="topic-rank">${String(index + 1).padStart(2, "0")}</div>
      <div class="topic-body">
        <h3>${escapeHtml(item.title)}</h3>
        <div class="topic-metrics">
          ${item.codexScore != null ? `<span>Codex <b>${Number(item.codexScore).toFixed(1)}</b>${item.codexVerdict ? ` · ${escapeHtml(String(item.codexVerdict).toUpperCase())}` : ""}</span>` : ""}
          ${item.radarProfileScore != null ? `<span>Radar fit <b>${Number(item.radarProfileScore).toFixed(1)}</b></span>` : (item.profileScore != null && item.codexScore == null ? `<span>Radar fit <b>${Number(item.profileScore).toFixed(1)}</b></span>` : "")}
          ${item.competitorSupportCount != null ? `<span>Kênh mẫu khớp <b>${Number(item.competitorSupportCount)}</b></span>` : ""}
          ${item.vph != null ? `<span>VPH <b>${Math.round(Number(item.vph)).toLocaleString("vi-VN")}</b></span>` : ""}
          ${item.outlier != null ? `<span>Outlier <b>${Number(item.outlier).toFixed(1)}×</b></span>` : ""}
          ${item.views != null ? `<span>Lượt xem <b>${Math.round(Number(item.views)).toLocaleString("vi-VN")}</b></span>` : ""}
        </div>
        ${item.note ? `<p>${escapeHtml(item.note)}</p>` : ""}
      </div>
      <button class="topic-use" data-use-topic="${index}">Dùng chủ đề này</button>
    </article>`).join("");
  $$('[data-use-topic]').forEach(btn => btn.addEventListener("click", () => chooseTopic(state.radarItems[Number(btn.dataset.useTopic)])));
}

function compactNumber(value) {
  const number = Number(value || 0);
  if (number >= 1000000) return `${(number / 1000000).toFixed(number >= 10000000 ? 0 : 1)}M`;
  if (number >= 1000) return `${(number / 1000).toFixed(number >= 100000 ? 0 : 1)}K`;
  return Math.round(number).toLocaleString("vi-VN");
}

function humanDurationFromDays(daysValue) {
  const days = Number(daysValue);
  if (!Number.isFinite(days) || days < 0) return "—";
  if (days < 60) return `${Math.max(1, Math.round(days))} ngày`;
  if (days < 730) return `${Math.max(1, Math.round(days / 30.44))} tháng`;
  const years = days / 365.25;
  return `${years < 10 ? years.toFixed(1) : Math.round(years)} năm`;
}

function channelAge(channel) {
  const published = channel?.published_at || channel?.channel_published_at;
  if (published) {
    const created = new Date(published);
    if (!Number.isNaN(created.getTime())) {
      return humanDurationFromDays(Math.max(0, (Date.now() - created.getTime()) / 86400000));
    }
  }
  if (channel?.channel_age_days != null) return humanDurationFromDays(channel.channel_age_days);
  return "—";
}

function channelJoinDate(channel) {
  const published = channel?.published_at || channel?.channel_published_at;
  if (!published) return "—";
  const created = new Date(published);
  if (Number.isNaN(created.getTime())) return "—";
  return new Intl.DateTimeFormat("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    timeZone: "UTC",
  }).format(created);
}

function channelAgeDays(channel) {
  const published = channel?.published_at || channel?.channel_published_at;
  if (published) {
    const created = new Date(published);
    if (!Number.isNaN(created.getTime())) return Math.max(0, (Date.now() - created.getTime()) / 86400000);
  }
  if (channel?.channel_age_days != null) {
    const days = Number(channel.channel_age_days);
    return Number.isFinite(days) ? days : null;
  }
  return null;
}

function videoAge(video) {
  if (video?.age_hours != null) return humanDurationFromDays(Number(video.age_hours) / 24);
  if (!video?.published_at) return "—";
  const published = new Date(video.published_at);
  if (Number.isNaN(published.getTime())) return "—";
  return humanDurationFromDays((Date.now() - published.getTime()) / 86400000);
}

function radarBilingual(original, translated, tag = "strong") {
  const source = String(original || "Chưa có tiêu đề").trim();
  const vi = String(translated || "").trim();
  const different = vi && vi.toLowerCase() !== source.toLowerCase();
  return `<div class="radar-bilingual"><${tag} class="radar-original">${escapeHtml(source)}</${tag}>${different ? `<span class="radar-vi">VI: ${escapeHtml(vi)}</span>` : ""}</div>`;
}

function youtubeThumb(video) {
  const id = video?.id || video?.video_id;
  return video?.thumbnail_url || (id ? `https://i.ytimg.com/vi/${encodeURIComponent(id)}/hqdefault.jpg` : "");
}

function channelUrl(channel) {
  const id = channel?.id || channel?.channel_id;
  return channel?.url || channel?.channel_url || (id ? `https://www.youtube.com/channel/${encodeURIComponent(id)}` : "");
}

function videoChannelUrl(video) {
  return video?.channel_url || (video?.channel_id ? `https://www.youtube.com/channel/${encodeURIComponent(video.channel_id)}` : "");
}

function renderProofChannelCard(channel) {
  const url = channelUrl(channel);
  const name = channel.title || channel.label || channel.id || channel.channel_id || "Kênh";
  const avatarUrl = channel.thumbnail_url || channel.avatar_url || channel.channel_thumbnail_url;
  const avatar = avatarUrl ? `<img src="${escapeHtml(avatarUrl)}" alt="Ảnh đại diện ${escapeHtml(name)}" loading="lazy" />` : `<span>${escapeHtml(String(name).slice(0, 1).toUpperCase())}</span>`;
  const winCount = Number(channel.win_count || 0);
  const medianOutlier = Number(channel.median_outlier || 0);
  const proofBadge = channel.proof_eligible === true
    ? `<span class="feed-confidence strong">PROOF</span>`
    : channel.proof_eligible === false
      ? `<span class="feed-confidence promising">DISCOVERY</span>`
      : "";
  return `<article class="proof-channel-card">
    ${url ? `<a class="proof-channel-avatar" href="${escapeHtml(url)}" target="_blank" rel="noreferrer">${avatar}</a>` : `<div class="proof-channel-avatar">${avatar}</div>`}
    <div class="proof-channel-main">
      <strong>${url ? `<a href="${escapeHtml(url)}" target="_blank" rel="noreferrer">${escapeHtml(name)}</a>` : escapeHtml(name)}</strong>
      <div class="proof-mini-metrics">
        ${proofBadge}
        <span><b>${compactNumber(channel.subscribers)}</b> sub</span>
        <span>Tuổi <b>${escapeHtml(channelAge(channel))}</b></span>
        <span>Tạo <b>${escapeHtml(channelJoinDate(channel))}</b></span>
        ${channel.total_videos != null ? `<span><b>${compactNumber(channel.total_videos)}</b> video</span>` : ""}
        ${channel.total_views != null ? `<span><b>${compactNumber(channel.total_views)}</b> lượt xem</span>` : ""}
        ${channel.country ? `<span>${escapeHtml(channel.country)}</span>` : ""}
        ${winCount ? `<span><b>${winCount}</b> video thắng</span>` : ""}
        ${medianOutlier ? `<span>Outlier TB <b>${medianOutlier.toFixed(1)}×</b></span>` : ""}
      </div>
      ${url ? `<a class="proof-open-link" href="${escapeHtml(url)}" target="_blank" rel="noreferrer">Mở kênh ↗</a>` : ""}
    </div>
  </article>`;
}

function renderProofVideoCard(video, { standalone = false } = {}) {
  const url = video.url || video.video_url || "";
  const thumb = youtubeThumb(video);
  const channelLink = videoChannelUrl(video);
  const title = video.title_original || video.title || "Video bằng chứng";
  const translated = video.title_vi || video.translated_title || video.translation_vi || "";
  return `<article class="proof-video-card${standalone ? " standalone" : ""}">
    ${url ? `<a class="proof-video-thumb" href="${escapeHtml(url)}" target="_blank" rel="noreferrer">${thumb ? `<img src="${escapeHtml(thumb)}" alt="" loading="lazy" />` : ""}</a>` : `<div class="proof-video-thumb">${thumb ? `<img src="${escapeHtml(thumb)}" alt="" loading="lazy" />` : ""}</div>`}
    <div class="proof-video-body">
      ${url ? `<a class="proof-video-title" href="${escapeHtml(url)}" target="_blank" rel="noreferrer">${radarBilingual(title, translated)}</a>` : radarBilingual(title, translated)}
      <div class="proof-video-channel">${channelLink ? `<a href="${escapeHtml(channelLink)}" target="_blank" rel="noreferrer">${escapeHtml(video.channel_title || "Kênh")}</a>` : escapeHtml(video.channel_title || "Kênh")}</div>
      <div class="proof-mini-metrics">
        <span><b>${compactNumber(video.views)}</b> view</span>
        <span>VPH <b>${Math.round(Number(video.vph || 0)).toLocaleString("vi-VN")}</b></span>
        ${video.outlier != null ? `<span>Outlier <b>${Number(video.outlier || 0).toFixed(1)}×</b></span>` : ""}
        <span>Đăng <b>${escapeHtml(videoAge(video))}</b></span>
      </div>
      ${url ? `<a class="proof-open-link" href="${escapeHtml(url)}" target="_blank" rel="noreferrer">Mở video ↗</a>` : ""}
    </div>
  </article>`;
}

async function requestVietnameseTranslations(texts) {
  const unique = [...new Set(texts.map(value => String(value || "").trim()).filter(Boolean))].slice(0, 80);
  if (!unique.length) return new Map();
  try {
    const payload = await api("/api/radar/translate", { method: "POST", body: JSON.stringify({ texts: unique }) });
    return new Map((payload.translations || []).filter(row => row?.source && row?.vi).map(row => [String(row.source), String(row.vi)]));
  } catch (err) {
    state.health = null;
    console.warn("Radar translation unavailable", err);
    return new Map();
  }
}

async function enrichMarketFeedTranslations(feed) {
  const topics = [...(feed.ranked_candidates || []), ...(feed.emerging_themes || []), ...(feed.momentum_topics || [])];
  const videos = [...(feed.breakout_videos || []), ...topics.flatMap(topic => topic.videos || [])];
  const searches = Array.isArray(feed.search_demand) ? feed.search_demand : [];
  const map = await requestVietnameseTranslations([
    ...topics.map(topic => topic.label),
    ...videos.map(video => video.title_original || video.title),
    ...searches.map(item => item.term),
  ]);
  topics.forEach(topic => { topic.label_vi = map.get(String(topic.label || "")) || topic.label_vi || ""; });
  videos.forEach(video => {
    const original = String(video.title_original || video.title || "");
    video.title_vi = map.get(original) || video.title_vi || "";
  });
  searches.forEach(item => { item.term_vi = map.get(String(item.term || "")) || item.term_vi || ""; });
  return feed;
}

async function enrichNicheTranslations(niches) {
  const videos = niches.flatMap(niche => [...(niche.videos || []), ...(niche.external_videos || [])]);
  const map = await requestVietnameseTranslations([
    ...niches.map(niche => niche.label),
    ...videos.map(video => video.title_original || video.title),
  ]);
  niches.forEach(niche => { niche.label_vi = map.get(String(niche.label || "")) || niche.label_vi || ""; });
  videos.forEach(video => {
    const original = String(video.title_original || video.title || "");
    video.title_vi = map.get(original) || video.title_vi || "";
  });
  return niches;
}

function proofChannels(niche, externalOnly = false) {
  const evidence = niche.evidence || {};
  const proof = new Map((evidence.channel_proof || []).map(row => [String(row.channel_id || row.id || ""), row]));
  const source = externalOnly ? (niche.external_channels || []) : (niche.channels || []);
  return source.map(channel => ({ ...channel, ...(proof.get(String(channel.id || channel.channel_id || "")) || {}) }));
}

function nicheVideos(niche, externalOnly = false) {
  return externalOnly ? (niche.external_videos || []) : (niche.videos || []);
}

function renderNicheResults(niches, { scan = {}, mode = "market", channel = null } = {}) {
  const externalOnly = mode === "channel";
  state.radarItems = niches.map(niche => {
    const videos = nicheVideos(niche, externalOnly);
    const best = videos[0] || {};
    return {
      raw: niche,
      title: niche.label || best.title || "Ngách chưa có tên",
      videoId: best.id || best.video_id || null,
      url: best.url || best.video_url || "",
      market: scan.market || "KR",
      vph: best.vph,
      outlier: best.outlier,
      views: best.views,
      scanId: scan.id || scan.scan_id || niche.scan_id || null,
      note: mode === "channel" ? (niche.channel_fit_reason || "") : `Ngách win đã có kênh và video công khai chứng minh.`,
    };
  });

  const root = $("#radarResults");
  if (!niches.length) {
    root.innerHTML = `<div class="empty-state">Chưa có ngách nào đạt đủ bằng chứng để gọi là ngách win.</div>`;
    return;
  }

  root.innerHTML = niches.map((niche, index) => {
    const evidence = niche.evidence || {};
    const channels = proofChannels(niche, externalOnly).slice(0, 5);
    const videos = nicheVideos(niche, externalOnly).slice(0, 5);
    const channelRows = channels.length ? `<div class="proof-channel-grid">${channels.map(renderProofChannelCard).join("")}</div>` : `<div class="feed-empty">Chưa có kênh ngoài đủ bằng chứng.</div>`;
    const videoRows = videos.length ? `<div class="proof-video-grid">${videos.map(video => renderProofVideoCard(video)).join("")}</div>` : `<div class="feed-empty">Chưa có video bằng chứng.</div>`;
    return `<article class="niche-card">
      <div class="niche-head">
        <div>
          <span class="niche-kicker${mode === "channel" ? " fit" : ""}">${mode === "channel" ? "HỢP DNA + CÓ BẰNG CHỨNG NGOÀI" : "NGÁCH WIN ĐÃ XÁC THỰC"}</span>
          ${radarBilingual(niche.label || "Ngách chưa có tên", niche.label_vi, "h3")}
        </div>
        <button class="topic-use" data-use-niche="${index}">Dùng chủ đề này</button>
      </div>
      <div class="niche-metrics">
        ${mode === "channel" ? `<span>Khớp DNA <b>${Number(niche.channel_fit || 0).toFixed(1)}</b></span>` : ""}
        <span>Điểm cơ hội <b>${Number(niche.score || 0).toFixed(1)}</b></span>
        <span>Độ tin cậy <b>${Number(evidence.confidence || 0).toFixed(1)}</b></span>
        <span>Kênh nhỏ <b>${Number(evidence.small_channels || 0)}</b></span>
        <span>Kênh mới <b>${Number(evidence.new_channels || 0)}</b></span>
        <span>Video breakout <b>${mode === "channel" ? Number(niche.external_breakout_videos || 0) : Number(evidence.breakout_videos || 0)}</b></span>
      </div>
      ${mode === "channel" && niche.channel_fit_reason ? `<p class="niche-reason">${escapeHtml(niche.channel_fit_reason)}</p>` : ""}
      <section class="proof-dossier-section"><div class="proof-dossier-head"><h4>Kênh chứng minh${mode === "channel" ? " bên ngoài" : ""}</h4><span>${channels.length}/5 kênh</span></div>${channelRows}</section>
      <section class="proof-dossier-section"><div class="proof-dossier-head"><h4>Top 5 video nổ</h4><span>${videos.length}/5 video</span></div>${videoRows}</section>
    </article>`;
  }).join("");
  $$('[data-use-niche]').forEach(btn => btn.addEventListener("click", () => chooseTopic(state.radarItems[Number(btn.dataset.useNiche)])));
}

function renderEvidenceGap(scan, nicheCount = 0) {
  const summary = scan?.source_summary || {};
  const gap = summary.evidence_gap || {};
  const message = gap.message || (nicheCount
    ? "Radar có tín hiệu nhưng chưa ngách nào đủ kênh/video chứng minh để được coi là ngách win."
    : "Lượt quét chưa thu được bằng chứng video hợp lệ trong cửa sổ thời gian đã chọn.");
  $("#radarResults").innerHTML = `<div class="radar-gap">
    <strong>Chưa có ngách win đủ bằng chứng</strong>
    <p>${escapeHtml(message)}</p>
    <div class="radar-gap-stats">
      ${summary.outside_window_excluded != null ? `<span>${Number(summary.outside_window_excluded)} video cũ bị loại</span>` : ""}
      ${summary.outside_market_excluded != null ? `<span>${Number(summary.outside_market_excluded)} video ngoài thị trường bị loại</span>` : ""}
      ${summary.successful_searches != null ? `<span>${Number(summary.successful_searches)} truy vấn tìm kiếm thành công</span>` : ""}
      ${nicheCount ? `<span>${nicheCount} cụm tín hiệu chưa đạt chuẩn chứng minh</span>` : ""}
    </div>
  </div>`;
}

function markNewSearchTerms(items, market) {
  const normalized = items.map(item => ({ ...item, term: String(item.term || "").trim() })).filter(item => item.term);
  const key = `cofi-radar-searches:${String(market || "GLOBAL").toUpperCase()}`;
  let previous = [];
  try { previous = JSON.parse(localStorage.getItem(key) || "[]"); } catch (_) { previous = []; }
  const previousSet = new Set(Array.isArray(previous) ? previous.map(value => String(value).toLowerCase()) : []);
  const hasHistory = previousSet.size > 0;
  const tagged = normalized.map(item => ({ ...item, isNew: hasHistory && !previousSet.has(item.term.toLowerCase()) }));
  try { localStorage.setItem(key, JSON.stringify(normalized.map(item => item.term).slice(0, 40))); } catch (_) {}
  return tagged;
}

function renderMarketFeed(feed) {
  const scan = feed.scan || {};
  const rankedCandidates = Array.isArray(feed.ranked_candidates) ? feed.ranked_candidates.slice(0, 5) : [];
  const discoveryChannels = Array.isArray(feed.discovery_channels) ? feed.discovery_channels.slice(0, 20) : [];
  const marketContextChannels = Array.isArray(feed.market_context_channels) ? feed.market_context_channels : discoveryChannels;
  const emerging = Array.isArray(feed.emerging_themes) ? feed.emerging_themes : [];
  const momentum = Array.isArray(feed.momentum_topics) ? feed.momentum_topics : [];
  const searches = markNewSearchTerms(Array.isArray(feed.search_demand) ? feed.search_demand : [], scan.market);
  const breakouts = Array.isArray(feed.breakout_videos) ? feed.breakout_videos : [];
  const granularity = String(feed.granularity || scan.source_summary?.niche_granularity || "standard").toUpperCase();
  const isMicro = granularity === "MICRO";
  const proofFilters = feed.filters || scan.source_summary?.niche_filters || {};
  const coverage = scan.source_summary?.coverage || {};
  const maxProofSubscribers = Number(proofFilters.max_channel_subscribers || 100000);
  const maxProofAgeDays = Number(proofFilters.max_channel_age_days || 90);
  const minProofChannels = isMicro ? Math.max(3, Number(proofFilters.min_proof_channels || 3)) : Math.max(1, Number(proofFilters.min_proof_channels || 1));
  const minBreakoutVideos = isMicro ? Math.max(4, Number(proofFilters.min_breakout_videos || 4)) : Math.max(1, Number(proofFilters.min_breakout_videos || 1));
  const isEligibleMicroChannel = channel => {
    const subscribers = Number(channel?.subscribers);
    const ageDays = channelAgeDays(channel);
    return Number.isFinite(subscribers)
      && ageDays != null
      && subscribers <= maxProofSubscribers
      && ageDays <= maxProofAgeDays;
  };
  const eligibleProofChannels = topic => (Array.isArray(topic?.channels) ? topic.channels : []).filter(isEligibleMicroChannel);
  const eligibleProofVideos = topic => {
    const eligibleIds = new Set(eligibleProofChannels(topic).map(channel => String(channel?.id || channel?.channel_id || "")).filter(Boolean));
    return (Array.isArray(topic?.videos) ? topic.videos : []).filter(video => eligibleIds.has(String(video?.channel_id || "")));
  };
  const confidenceOf = topic => Math.max(0, Math.min(100, Number(topic?.audited_confidence ?? topic?.win_confidence ?? topic?.confidence ?? 0)));
  const isApprovedGo = topic => isMicro
    && Number(scan.days || 0) >= 90
    && confidenceOf(topic) >= 80
    && String(topic?.codex_verdict || "").toLowerCase() === "approve"
    && topic?.sustained_90d_signal === true
    && topic?.one_off_event_spike !== true
    && eligibleProofChannels(topic).length >= minProofChannels
    && eligibleProofVideos(topic).length >= minBreakoutVideos;
  const goTopics = emerging.filter(isApprovedGo);
  const signalTopics = isMicro ? [] : emerging;
  const fallbackWatch = isMicro ? emerging.filter(topic => !isApprovedGo(topic)) : [];
  const seenWatch = new Set(signalTopics.map(topic => String(topic?.id || topic?.label || "").toLowerCase()).filter(Boolean));
  const watchTopics = [...fallbackWatch, ...momentum].filter(topic => {
    const key = String(topic?.id || topic?.label || "").toLowerCase();
    if (!key || seenWatch.has(key)) return false;
    seenWatch.add(key);
    return true;
  });
  const root = $("#radarResults");
  if (!rankedCandidates.length && !discoveryChannels.length && !emerging.length && !momentum.length && !searches.length && !breakouts.length) {
    renderEvidenceGap(scan, 0);
    return;
  }

  state.radarItems = [];
  const registerTopic = topic => {
    const videos = Array.isArray(topic.videos) ? topic.videos : [];
    const best = videos[0] || {};
    const index = state.radarItems.length;
    state.radarItems.push({
      raw: topic,
      title: topic.label || best.title || "Chủ đề chưa có tên",
      videoId: best.id || best.video_id || null,
      url: best.url || best.video_url || "",
      market: scan.market || "KR",
      vph: best.vph ?? topic.median_vph,
      outlier: best.outlier ?? topic.median_outlier,
      views: best.views,
      scanId: scan.id || scan.scan_id || topic.scan_id || null,
      note: `Tín hiệu Radar có ${Number(topic.breakout_videos || 0)} video breakout từ ${Number(topic.winning_channels || 0)} kênh thắng.`,
    });
    return index;
  };

  const topicRows = (items, mode) => items.length ? items.map((topic, index) => {
    const useIndex = registerTopic(topic);
    const rawChannels = Array.isArray(topic.channels) ? topic.channels : [];
    const rawVideos = Array.isArray(topic.videos) ? topic.videos : [];
    const microChannels = isMicro ? eligibleProofChannels(topic) : rawChannels;
    const microChannelIds = new Set(microChannels.map(channel => String(channel?.id || channel?.channel_id || "")).filter(Boolean));
    const channels = microChannels.slice(0, 5);
    const videos = (isMicro
      ? rawVideos.filter(video => microChannelIds.has(String(video?.channel_id || "")))
      : rawVideos).slice(0, 5);
    const confidence = Number(topic.audited_confidence ?? topic.win_confidence ?? topic.confidence ?? 0);
    const score = Math.max(0, Math.min(100, Math.round(confidence)));
    const verdict = String(topic.codex_verdict || "").toLowerCase();
    const confidenceLabel = verdict && verdict !== "not_audited"
      ? `Codex duyệt ${confidence.toFixed(0)}/100`
      : `Bằng chứng ${confidence.toFixed(0)}/100`;
    const auditReasons = Array.isArray(topic.codex_reasons) && topic.codex_reasons.length
      ? topic.codex_reasons
      : (Array.isArray(topic.confidence_reasons) ? topic.confidence_reasons : []);
    const isGo = mode === "go";
    const isSignal = mode === "signal";
    const tier = isGo ? "GO" : isSignal ? "SIGNAL" : "WATCH";
    const dossierClass = isGo ? "is-go" : isSignal ? "is-signal" : "is-watch";
    const tierClass = isGo ? "go" : isSignal ? "signal" : "watch";
    const topicNote = isGo
      ? "Micro-niche đã vượt hard-gate dữ liệu và kiểm định Codex"
      : isSignal
        ? "Tín hiệu discovery đang nổi; cần quét MICRO để kiểm định trước khi sản xuất"
        : "Tín hiệu lặp lại đáng theo dõi nhưng chưa đạt ngưỡng GO";
    const actionNote = isGo
      ? "Đã đủ chuẩn để đưa vào production"
      : isSignal
        ? "Chưa phải GO · nên quét MICRO để xác nhận"
        : "Theo dõi thêm trước khi vào production";
    return `<article class="feed-topic-dossier ${dossierClass}">
      <div class="feed-topic-head">
        <div class="feed-score-panel">
          <span class="feed-rank">#${String(index + 1).padStart(2, "0")}</span>
          <div class="feed-score-ring" style="--score:${score}"><div><strong>${score}</strong><span>/100</span></div></div>
          <b class="feed-tier ${tierClass}">${tier}</b>
        </div>
        <div class="feed-copy">
          ${radarBilingual(topic.label || "Chủ đề", topic.label_vi)}
          <small>${topicNote}</small>
          <div class="feed-proof">
            <span class="feed-confidence ${confidence >= 80 ? "strong" : confidence >= 65 ? "promising" : "weak"}">${escapeHtml(confidenceLabel)}</span>
            ${isGo ? `<span>${channels.length} kênh nhỏ/mới hợp bộ lọc</span>` : ""}
            <span>${Number(topic.winning_channels || channels.length)} kênh thắng</span>
            <span>${Number(topic.breakout_videos || 0)} breakout</span>
            <span>${Number(topic.mentions || 0)} video</span>
            <span>VPH TB ${Math.round(Number(topic.median_vph || 0)).toLocaleString("vi-VN")}</span>
            ${topic.median_outlier != null ? `<span>Outlier TB ${Number(topic.median_outlier || 0).toFixed(1)}×</span>` : ""}
            ${topic.niche_velocity_score != null ? `<span>Tăng tốc <b>${Number(topic.niche_velocity_score).toFixed(0)}/100</b></span>` : ""}
            ${topic.history_coverage != null ? `<span>Lịch sử <b>${Math.round(Number(topic.history_coverage) * 100)}%</b></span>` : ""}
            ${topic.active_30d_buckets != null ? `<span>Cửa sổ 30D <b>${Number(topic.active_30d_buckets)}/3</b></span>` : ""}
            ${topic.evidence_span_days != null ? `<span>Độ bền <b>${Math.round(Number(topic.evidence_span_days))} ngày</b></span>` : ""}
            ${topic.one_off_event_spike === true ? `<span class="feed-confidence weak">Spike sự kiện</span>` : ""}
            ${topic.demand_competition_score != null ? `<span>Nhu cầu/Cạnh tranh <b>${Number(topic.demand_competition_score).toFixed(0)}/100</b></span>` : ""}
            ${topic.competition_openness != null ? `<span>Độ thoáng <b>${Number(topic.competition_openness).toFixed(0)}/100</b></span>` : ""}
            ${topic.autocomplete_breadth != null ? `<span>Long-tail <b>${Number(topic.autocomplete_breadth)}</b></span>` : ""}
          </div>
          ${auditReasons.length ? `<div class="codex-audit-note"><b>${verdict === "approve" ? "Codex: DUYỆT" : verdict === "watch" ? "Codex: THEO DÕI" : "Lý do điểm"}</b>${auditReasons.slice(0, 3).map(reason => `<span>${escapeHtml(reason)}</span>`).join("")}</div>` : ""}
        </div>
        <div class="feed-topic-actions">
          <button class="topic-use feed-use" data-use-feed="${useIndex}">Tạo video từ ngách</button>
          <span>${actionNote}</span>
        </div>
      </div>
      <section class="proof-dossier-section"><div class="proof-dossier-head"><h4>${isSignal ? "Kênh tham khảo thị trường" : "Kênh chứng minh"}</h4><span>${channels.length}/5 kênh${isMicro ? ` · ≤${compactNumber(maxProofSubscribers)} sub · ≤${maxProofAgeDays} ngày` : ""}</span></div>${channels.length ? `<div class="proof-channel-grid">${channels.map(renderProofChannelCard).join("")}</div>` : `<div class="feed-empty">${isMicro ? "Không có kênh nào vừa đủ nhỏ vừa đủ mới theo bộ lọc MICRO." : "Chưa có kênh tham khảo cho tín hiệu này."}</div>`}</section>
      <section class="proof-dossier-section"><div class="proof-dossier-head"><h4>Top 5 video nổ</h4><span>${videos.length}/5 video</span></div>${videos.length ? `<div class="proof-video-grid">${videos.map(video => renderProofVideoCard(video)).join("")}</div>` : `<div class="feed-empty">Chưa có video nổ đủ chuẩn.</div>`}</section>
    </article>`;
  }).join("") : `<div class="feed-empty">${mode === "emerging" ? "Chưa có chủ đề nào được nhiều kênh nhỏ/vừa cùng lúc xác nhận. Radar sẽ không gọi một trend đơn lẻ là ngách mới nổi." : "Chưa có cụm chủ đề nào lặp đủ mạnh trong các video breakout."}</div>`;

  const candidateRows = rankedCandidates.length ? rankedCandidates.map((candidate, index) => {
    const useIndex = registerTopic(candidate);
    const rawCandidateChannels = Array.isArray(candidate.channels) ? candidate.channels : [];
    const channels = (isMicro ? rawCandidateChannels.filter(isEligibleMicroChannel) : rawCandidateChannels).slice(0, 5);
    const candidateChannelIds = new Set(channels.map(channel => String(channel?.id || channel?.channel_id || "")).filter(Boolean));
    const rawCandidateVideos = Array.isArray(candidate.videos) ? candidate.videos : [];
    const videos = (isMicro ? rawCandidateVideos.filter(video => candidateChannelIds.has(String(video?.channel_id || ""))) : rawCandidateVideos).slice(0, 5);
    const candidateScore = Math.max(0, Math.min(100, Number(candidate.candidate_score ?? candidate.win_confidence ?? candidate.score ?? 0)));
    const potential = String(candidate.potential || "thap").toLowerCase();
    const potentialLabel = potential === "cao" ? "CAO" : potential === "trung_binh" ? "TRUNG BÌNH" : "THẤP";
    const decision = String(candidate.decision || "theo_doi").toLowerCase();
    const decisionLabel = decision === "chot" ? "CHỐT" : decision === "bo" ? "BỎ" : "THEO DÕI";
    const decisionClass = decision === "chot" ? "go" : decision === "bo" ? "none" : "watch";
    return `<article class="feed-topic-dossier ${decision === "chot" ? "is-go" : decision === "bo" ? "" : "is-watch"}">
      <div class="feed-topic-head">
        <div class="feed-score-panel">
          <span class="feed-rank">#${Number(candidate.rank || index + 1)}</span>
          <div class="feed-score-ring" style="--score:${Math.round(candidateScore)}"><div><strong>${Math.round(candidateScore)}</strong><span>/100</span></div></div>
          <b class="feed-tier ${decisionClass}">${decisionLabel}</b>
        </div>
        <div class="feed-copy">
          <div class="radar-command-kicker">${escapeHtml(candidate.content_category || "Chủ đề tổng hợp")} · MICRO-NICHE</div>
          ${radarBilingual(candidate.micro_niche || candidate.label || "Ngách chưa có tên", candidate.label_vi)}
          <small>Tiềm năng ${potentialLabel} · ${escapeHtml(candidate.decision_reason || "Đang xếp hạng theo bằng chứng thị trường hiện có.")}</small>
          <div class="feed-proof">
            <span>Điểm cơ hội <b>${Number(candidate.score || 0).toFixed(0)}/100</b></span>
            <span>Kênh chứng minh <b>${channels.length}</b></span>
            <span>Video nổ <b>${videos.length}</b></span>
            ${candidate.win_confidence != null ? `<span>Độ tin cậy <b>${Number(candidate.win_confidence).toFixed(0)}/100</b></span>` : ""}
            ${candidate.competition_openness != null ? `<span>Độ thoáng <b>${Number(candidate.competition_openness).toFixed(0)}/100</b></span>` : ""}
          </div>
        </div>
        <div class="feed-topic-actions">
          ${candidate.can_save !== false && candidate.id ? `<button class="topic-use feed-use" data-save-feed="${useIndex}">Lưu ngách để xây kênh</button>` : ""}
          <button class="button button--small" data-use-feed="${useIndex}">Tạo video thử</button>
        </div>
      </div>
      <section class="proof-dossier-section"><div class="proof-dossier-head"><h4>Kênh chứng minh thị trường</h4><span>${channels.length}/5 kênh</span></div>${channels.length ? `<div class="proof-channel-grid">${channels.map(renderProofChannelCard).join("")}</div>` : `<div class="feed-empty">Chưa có kênh đạt chuẩn MICRO: ≤100K sub · ≤90 ngày · ≥3 video thắng · các video còn lại vẫn có baseline view.</div>`}</section>
      <section class="proof-dossier-section"><div class="proof-dossier-head"><h4>Video chứng minh</h4><span>${videos.length}/5 video</span></div>${videos.length ? `<div class="proof-video-grid">${videos.map(video => renderProofVideoCard(video)).join("")}</div>` : `<div class="feed-empty">Chưa có breakout đủ mạnh trong candidate này.</div>`}</section>
    </article>`;
  }).join("") : `<div class="feed-empty feed-empty-rich"><b>Chưa có candidate để xếp hạng</b><span>Radar chưa gom được cụm content đủ rõ để tạo bảng Top 5.</span></div>`;

  const searchHtml = searches.length ? `<div class="search-cloud">${searches.map(item => `<div class="search-term${item.isNew ? " new" : ""}">${item.isNew ? "<i>NEW</i>" : ""}<div><strong>${escapeHtml(item.term)}</strong>${item.term_vi && item.term_vi !== item.term ? `<span>VI: ${escapeHtml(item.term_vi)}</span>` : ""}</div></div>`).join("")}</div>` : `<div class="feed-empty">Chưa lấy được tín hiệu YouTube autocomplete cho lượt quét này.</div>`;
  const breakoutHtml = breakouts.length ? `<div class="breakout-grid">${breakouts.slice(0, 5).map(video => renderProofVideoCard(video, { standalone: true })).join("")}</div>` : `<div class="feed-empty feed-empty-rich"><b>Chưa có breakout đủ mạnh</b><span>Radar sẽ giữ trống thay vì đẩy một video bình thường thành tín hiệu cơ hội.</span></div>`;
  const discoveryHtml = discoveryChannels.length
    ? `<div class="proof-channel-grid">${discoveryChannels.map(renderProofChannelCard).join("")}</div>`
    : `<div class="feed-empty feed-empty-rich"><b>${isMicro ? "Không có kênh nào đạt bộ lọc MICRO" : "Chưa có kênh discovery sạch"}</b><span>${isMicro ? `Không có kênh đồng thời ≤${compactNumber(maxProofSubscribers)} sub và ≤${maxProofAgeDays} ngày tuổi trong lượt quét này.` : "Radar chưa gom được kênh liên quan đủ chắc sau khi khóa thị trường."}</span></div>`;
  const discoveryTitle = isMicro ? "KÊNH ĐẠT BỘ LỌC MICRO" : "KÊNH LIÊN QUAN ĐÃ TÌM THẤY";
  const discoveryDescription = isMicro
    ? `Chỉ hiện kênh ≤${compactNumber(maxProofSubscribers)} sub và ≤${maxProofAgeDays} ngày tuổi. Radar đã quét ${Number(feed.counts?.market_context_channels ?? marketContextChannels.length)} kênh liên quan trước khi lọc.`
    : "Đây là lớp discovery rộng của đúng thị trường. Kênh lớn/cũ được giữ để hiểu toàn cảnh.";

  const updated = scan.completed_at || scan.updated_at || scan.started_at || "—";
  const auditStatus = String(feed.codex_audit?.status || "—").toUpperCase();
  const leader = goTopics[0] || signalTopics[0] || watchTopics[0] || null;
  const leaderConfidence = leader ? Math.max(0, Math.min(100, Math.round(Number(leader.audited_confidence ?? leader.win_confidence ?? leader.confidence ?? 0)))) : 0;
  const decision = goTopics.length ? "GO READY" : signalTopics.length ? "SIGNAL" : watchTopics.length ? "WATCH" : "NO GO";
  const decisionClass = goTopics.length ? "go" : signalTopics.length ? "signal" : watchTopics.length ? "watch" : "none";
  const leaderTitle = leader?.label || "Chưa có micro-niche đủ chuẩn";
  const leaderVi = leader?.label_vi && String(leader.label_vi).toLowerCase() !== String(leaderTitle).toLowerCase() ? leader.label_vi : "";
  const decisionNote = goTopics.length
    ? "Có ứng viên đã vượt hard-gate và đủ bằng chứng đa kênh để đưa sang production."
    : signalTopics.length
      ? "Đây là tín hiệu discovery, chưa phải GO. Hãy quét MICRO để kiểm tra tuổi kênh, độ lặp, cạnh tranh và Codex audit trước khi sản xuất."
      : watchTopics.length
      ? "Có tín hiệu đáng theo dõi nhưng chưa nên sản xuất chỉ vì một vài video đang tăng."
      : "Radar chưa thấy bằng chứng đủ mạnh. Không ép một trend đơn lẻ thành ngách thắng.";
  root.innerHTML = `<div class="radar-feed">
    <section class="radar-command-center">
      <div class="radar-command-main">
        <div class="radar-command-kicker"><span class="radar-live-dot"></span> RADAR DECISION · ${escapeHtml(scan.market || "—")} · ${Number(scan.days || 0)}D</div>
        <div class="radar-command-title-row">
          <div>
            <span class="radar-decision ${decisionClass}">${decision}</span>
            <h2>${escapeHtml(leaderTitle)}</h2>
            ${leaderVi ? `<p class="radar-command-vi">${escapeHtml(leaderVi)}</p>` : ""}
          </div>
          <div class="radar-command-score ${decisionClass}"><strong>${leaderConfidence || "—"}</strong><span>${leader ? "/100" : "SCORE"}</span></div>
        </div>
        <p class="radar-command-note">${escapeHtml(decisionNote)}</p>
      </div>
      <div class="radar-command-kpis">
        <div><span>${isMicro ? "ĐẠT BỘ LỌC" : "DISCOVERY CH."}</span><strong>${discoveryChannels.length}</strong><small>${isMicro ? `≤${compactNumber(maxProofSubscribers)} sub · ≤${maxProofAgeDays} ngày` : (coverage.target_discovery_channels ? `mục tiêu ${Number(coverage.target_discovery_channels)}` : "kênh liên quan")}</small></div>
        <div><span>${isMicro ? "GO 80+" : "SIGNALS"}</span><strong>${isMicro ? goTopics.length : signalTopics.length}</strong><small>${isMicro ? "Codex approve" : "chưa kiểm định GO"}</small></div>
        <div><span>WATCHLIST</span><strong>${watchTopics.length}</strong><small>chưa đủ chuẩn GO</small></div>
        <div><span>BREAKOUT</span><strong>${breakouts.length}</strong><small>video vượt baseline</small></div>
        <div><span>SEARCH DEMAND</span><strong>${searches.length}</strong><small>truy vấn thị trường</small></div>
      </div>
    </section>
    <div class="radar-feed-meta"><span>ISSUE <b>#${escapeHtml(scan.id || scan.scan_id || "—")}</b></span><span>MODE <b>${escapeHtml(granularity)}</b></span><span>DISCOVERY <b>${Number(coverage.discovery_channels ?? discoveryChannels.length)} CH</b></span><span>PROOF <b>${Number(coverage.proof_channels ?? feed.counts?.proof_eligible_channels ?? 0)} CH</b></span>${isMicro ? `<span>PROOF RULE <b>≤${compactNumber(maxProofSubscribers)} SUB · ≤${maxProofAgeDays}D</b></span>` : ""}<span>CRAWL <b>${escapeHtml(coverage.crawl_stop_reason || "—")}</b></span><span>CODEX <b>${escapeHtml(auditStatus)}</b></span><span>UPDATED <b>${escapeHtml(updated)}</b></span><span>REGION <b>${escapeHtml(scan.market || "—")}</b></span><span>WINDOW <b>${Number(scan.days || 0)}D</b></span></div>
    <section class="radar-feed-section wide"><div class="radar-feed-head"><div class="radar-feed-title"><span class="radar-section-tag signal">${isMicro ? "FILTER" : "COVERAGE"}</span><div><h3>${discoveryTitle}</h3><p>${discoveryDescription}</p></div></div><span class="radar-feed-count">${discoveryChannels.length}</span></div>${discoveryHtml}</section>
    <section class="radar-feed-section wide ranked-section"><div class="radar-feed-head"><div class="radar-feed-title"><span class="radar-section-tag signal">TOP 5</span><div><h3>TOP 5 NGÁCH THỊ TRƯỜNG</h3><p>Luôn xếp hạng cơ hội từ dữ liệu thật. CHỐT/THEO DÕI/BỎ tách riêng với hard-gate GO để không biến tín hiệu yếu thành ngách thắng giả.</p></div></div><span class="radar-feed-count">${rankedCandidates.length}</span></div><div class="feed-list">${candidateRows}</div></section>
    <div class="radar-feed-grid">
      <section class="radar-feed-section ${isMicro ? "go-section" : "signal-section"}"><div class="radar-feed-head"><div class="radar-feed-title"><span class="radar-section-tag ${isMicro ? "go" : "signal"}">${isMicro ? "GO" : "SIGNAL"}</span><div><h3>${isMicro ? "Micro-niche đã qua kiểm định" : "Discovery signals · chưa phải GO"}</h3><p>${isMicro ? "Chỉ hiện ứng viên đạt từ 80 điểm và được Codex approve." : "Chủ đề mới nổi từ scan chuẩn; dùng để khám phá rồi chuyển sang MICRO để kiểm định."}</p></div></div><span class="radar-feed-count">${isMicro ? goTopics.length : signalTopics.length}</span></div><div class="feed-list">${isMicro ? (goTopics.length ? topicRows(goTopics, "go") : `<div class="feed-empty feed-empty-rich"><b>Chưa có micro-niche nào đạt GO</b><span>Radar chưa có ứng viên đồng thời đạt ≥80 và được Codex approve.</span></div>`) : (signalTopics.length ? topicRows(signalTopics, "signal") : `<div class="feed-empty feed-empty-rich"><b>Chưa có discovery signal</b><span>Scan chuẩn chưa tìm thấy cụm chủ đề mới nổi đủ rõ trong cửa sổ này.</span></div>`)}</div></section>
      <section class="radar-feed-section watch-section"><div class="radar-feed-head"><div class="radar-feed-title"><span class="radar-section-tag watch">WATCH</span><div><h3>Watchlist · chưa đủ chuẩn GO</h3><p>Bằng chứng đáng chú ý nhưng còn thiếu điểm, lịch sử, độ thoáng hoặc phê duyệt Codex.</p></div></div><span class="radar-feed-count">${watchTopics.length}</span></div><div class="feed-list">${watchTopics.length ? topicRows(watchTopics, "watch") : `<div class="feed-empty feed-empty-rich"><b>Watchlist đang trống</b><span>Không có cụm nào cần giữ lại để theo dõi trong lượt quét này.</span></div>`}</div></section>
      <section class="radar-feed-section wide search-section"><div class="radar-feed-head"><div class="radar-feed-title"><span class="radar-section-tag demand">DEMAND</span><div><h3>Người xem đang tìm gì</h3><p>YouTube autocomplete của đúng thị trường. NEW = mới so với feed trước.</p></div></div><span class="radar-feed-count">${searches.length}</span></div>${searchHtml}</section>
      <section class="radar-feed-section wide breakout-section"><div class="radar-feed-head"><div class="radar-feed-title"><span class="radar-section-tag breakout">BREAKOUT</span><div><h3>Video đang vượt baseline</h3><p>Dùng để đọc framing, thumbnail và hook; một video nổ không tự động được coi là một ngách.</p></div></div><span class="radar-feed-count">${breakouts.length}</span></div>${breakoutHtml}</section>
    </div>
  </div>`;
  $$('[data-use-feed]').forEach(btn => btn.addEventListener("click", () => chooseTopic(state.radarItems[Number(btn.dataset.useFeed)])));
  $$('[data-save-feed]').forEach(btn => btn.addEventListener("click", () => saveRadarNiche(state.radarItems[Number(btn.dataset.saveFeed)], btn)));
}

async function saveRadarNiche(item, button = null) {
  const nicheId = item?.raw?.id;
  if (!nicheId) return;
  const candidate = item.raw || {};
  const originalText = button?.textContent || "Lưu ngách để xây kênh";
  if (button) {
    button.disabled = true;
    button.textContent = "Đang lưu…";
  }
  try {
    const note = `Top 5 #${candidate.rank || "—"} · ${candidate.decision || "theo_doi"} · tiềm năng ${candidate.potential || "—"}`;
    await api(`/api/radar/niches/${encodeURIComponent(nicheId)}/save`, { method: "POST", body: JSON.stringify({ note }) });
    if (button) button.textContent = "Đã lưu ✓";
    $("#radarResultHint").textContent = `Đã lưu ngách #${nicheId} vào Evidence Library để tiếp tục xây kênh.`;
  } catch (err) {
    if (button) {
      button.disabled = false;
      button.textContent = originalText;
    }
    $("#radarResultHint").textContent = `Không lưu được ngách: ${err.message || err}`;
  }
}

function syncMarketScanFormFromFeed(feed) {
  const form = $("#marketScanForm");
  if (!form) return;
  const scan = feed?.scan || {};
  const filters = feed?.filters || scan?.source_summary?.niche_filters || {};
  const granularity = String(feed?.granularity || scan?.source_summary?.niche_granularity || "standard").toLowerCase();
  const setValue = (name, value) => {
    if (value == null || !form.elements[name]) return;
    form.elements[name].value = String(value);
  };
  setValue("market", scan.market);
  setValue("days", scan.days);
  setValue("niche_granularity", granularity);
  setValue("max_channel_subscribers", filters.max_channel_subscribers);
  setValue("max_channel_age_days", filters.max_channel_age_days);
  setValue("min_proof_channels", filters.min_proof_channels);
  setValue("min_breakout_videos", filters.min_breakout_videos);
}

async function fetchMarketFeed(scanId) {
  const feed = await enrichMarketFeedTranslations(await api(`/api/radar/scans/${encodeURIComponent(scanId)}/feed`));
  const counts = feed.counts || {};
  syncMarketScanFormFromFeed(feed);
  $("#radarResultHint").textContent = `Scan #${scanId} · ${Number(counts.emerging_themes || 0)} chủ đề mới nổi · ${Number(counts.breakout_videos || 0)} breakout`;
  renderMarketFeed(feed);
}

function setComboDurationValue(selectEl, customInputEl, rawMinutes, prefix = "") {
  const num = Number(rawMinutes);
  const valStr = Number.isFinite(num) && num >= 2 ? String(Math.min(180, Math.round(num * 10) / 10)) : "30";
  if (selectEl) {
    const hasOption = [...selectEl.options].some(opt => String(opt.value) === valStr);
    if (!hasOption) {
      const opt = document.createElement("option");
      opt.value = valStr;
      opt.dataset.customDuration = "true";
      opt.textContent = `${prefix ? `${prefix} ` : ""}${valStr} phút (Tùy chỉnh)`;
      selectEl.appendChild(opt);
    }
    selectEl.value = valStr;
  }
  if (customInputEl) {
    customInputEl.value = valStr;
  }
}

function bindComboDurationPair(selectSelector, inputSelector, prefix = "") {
  const selectEl = $(selectSelector);
  const inputEl = $(inputSelector);
  if (selectEl && inputEl) {
    selectEl.addEventListener("change", () => {
      inputEl.value = String(selectEl.value || "30");
    });
    const syncFromInput = () => {
      const raw = String(inputEl.value || "").trim();
      const num = Number(raw);
      if (!raw || !Number.isFinite(num) || num < 2) return;
      setComboDurationValue(selectEl, null, Math.min(180, num), prefix);
    };
    inputEl.addEventListener("input", syncFromInput);
    inputEl.addEventListener("change", () => {
      const num = Number(inputEl.value);
      const clamped = Number.isFinite(num) ? Math.max(2, Math.min(180, num)) : 30;
      setComboDurationValue(selectEl, inputEl, clamped, prefix);
    });
  }
}

bindComboDurationPair("#profileDefaultDurationSelect", "#profileCustomDurationInput", "");
bindComboDurationPair("#profileTodayDuration", "#profileTodayCustomDurationInput", "");
bindComboDurationPair("#createTargetDurationSelect", "#createCustomDurationInput", "Khoảng");

function chooseTopic(item) {
  state.selectedRadar = item;
  state.selectedChannelPlan = null;
  const form = $("#jobForm");
  form.elements.title.value = item.title;
  form.elements.market.value = ["KR", "JP", "US", "VN"].includes(String(item.market).toUpperCase()) ? String(item.market).toUpperCase() : "KR";
  if (form.elements.channel_profile_id && item.profileId) form.elements.channel_profile_id.value = item.profileId;
  if (form.elements.target_duration_minutes && item.targetDurationMinutes) {
    setComboDurationValue(form.elements.target_duration_minutes, $("#createCustomDurationInput"), item.targetDurationMinutes, "Khoảng");
  }
  if (item.url) form.elements.source_url.value = item.url;
  if (item.note) form.elements.notes.value = item.note;
  const badge = $("#selectedTopicBadge");
  badge.classList.remove("hidden");
  badge.innerHTML = `<span>RADAR</span><strong>${escapeHtml(item.title)}</strong><button type="button" id="clearTopicBtn">×</button>`;
  $("#clearTopicBtn").addEventListener("click", clearSelectedTopic);
  setAppTab("create");
}

function chooseChannelPlanTopic(item) {
  state.selectedRadar = null;
  state.selectedChannelPlan = {
    profileId: state.selectedChannelProfileId,
    itemId: Number(item.id),
  };
  const form = $("#jobForm");
  const title = item.topic_anchor || item.title || item.evidence_title || "Chủ đề từ kế hoạch kênh";
  form.elements.title.value = title;
  const profile = state.channelProfiles.find(profile => profile.id === state.selectedChannelProfileId);
  const market = String(profile?.market || "KR").toUpperCase();
  form.elements.market.value = ["KR", "JP", "US", "VN"].includes(market) ? market : "KR";
  if (form.elements.channel_profile_id) form.elements.channel_profile_id.value = state.selectedChannelProfileId || "";
  if (form.elements.target_duration_minutes && profile?.default_duration_minutes) form.elements.target_duration_minutes.value = String(profile.default_duration_minutes);
  if (item.evidence_url) form.elements.source_url.value = item.evidence_url;
  if (item.production_brief || item.note) form.elements.notes.value = item.production_brief || item.note;
  const badge = $("#selectedTopicBadge");
  badge.classList.remove("hidden");
  badge.innerHTML = `<span>PLAN ${escapeHtml(item.day_number || "")}</span><strong>${escapeHtml(title)}</strong><button type="button" id="clearTopicBtn">×</button>`;
  $("#clearTopicBtn").addEventListener("click", clearSelectedTopic);
  setAppTab("create");
}

function clearSelectedTopic() {
  state.selectedRadar = null;
  state.selectedChannelPlan = null;
  state.selectedCreateTopic = null;
  const badge = $("#selectedTopicBadge");
  badge.classList.add("hidden");
  badge.innerHTML = "";
}

const TRUE_CRIME_CN_KR_PRESET = {
  label: "Hồ sơ Kênh True Crime Hình Sự Trung Quốc (KR - Full AI)",
  market: "KR",
  default_language: "ko",
  default_duration_minutes: 20,
  default_visual_strategy: "full_ai",
  default_ai_media_mode: "image",
  default_voice_id: "6456334b-ffaf-4e74-b0d4-9066efebf019",
  dna_mode: "custom_dna_only",
  voice_and_structure: "Hàn Quốc (KR) — Giọng kể đêm khuya trầm ấm, điềm tĩnh (K1 - Trầm Sâu Đêm Khuya SBS Style / 그것이 알고싶다 / 꼬꼬무 style) · Cấu trúc 5 Hồi chuẩn điều tra hình sự · Nguyên tắc Chiếc súng của Chekhov (nhân vật mở màn bắt buộc có kết cục rõ ràng) · Xưng hô chuẩn văn hóa Hàn (cấm gọi 58–62 tuổi là 노부부) · Phần kết trọn vẹn + 3.5–5s nhạc nền fade-out",
  reference_image_policy: "100% Full AI (full_ai) — Nhận Ảnh tham chiếu (Reference Image) của bạn ở đầu mỗi dự án để khóa phong cách toàn bộ phân cảnh.",
  allowed_topics: "100% đại án có thật tại Trung Quốc (중국 실화 대사건 — có >=50% tư liệu CCTV/công an/tòa án thật), chia thành 2 LUỒNG CHÍNH chuẩn DNA kênh: (1) [LUỒNG 1 — TỘI PHẠM TÀI CHÍNH & ĐẠI ÁN KINH TẾ ĐÀO TẨU (금융·경제 대사건 & 해외 도피 추적)]: Đại án rút ruột ngân hàng, công trái khống, chứng khoán, kho bạc, két sắt ngân hàng, sổ tiết kiệm bốc hơi, hối phiếu giả, thao túng tài chính rồi tẩy trắng thân phận đào tẩu xuyên biên giới 10–25 năm. (2) [LUỒNG 2 — VỤ ÁN ĐẶC BIỆT NGUY HIỂM & TRUY NÃ CẤP A (특수 강력사건 & A급 수배범 미제 추적)]: Trọng án hình sự đặc biệt nguy hiểm, lệnh truy nã cấp A, hung thủ IQ cao xóa dấu vết, vỏ bọc hai mặt lẩn trốn 10–30 năm, pháp y ADN và đấu trí phòng thẩm vấn.",
  forbidden_topics: "chính trị đảng phái nhạy cảm, đập tam hiệp, nam thủy bắc điều, hạ tầng cầu đường thuần túy, 삼협댐, 남수북조, tranh chấp dân sự vặt, bạo lực học đường nhỏ lẻ, chuyện ngoại tình gia đình giật gân, tin đồn chưa kiểm chứng hoặc gộp nhiều vụ án, mô tả máu me tra tấn trực diện",
  monetization_safety_policy: "Ngôi thứ 3 theo góc nhìn Hồ sơ Điều tra viên Hình sự & Chuyên gia Tâm lý Tội phạm — Cắt bỏ 100% miêu tả máu me/thi thể trực diện, tập trung vào sự ranh ma của hung thủ, vật chứng pháp y và màn đấu trí nghẹt thở trong phòng thẩm vấn.",
  cta_strategy: "ROLE KỂ CHUYỆN & CTA LINH HOẠT THEO TRUYỆN — KHÔNG BAO GIỜ LẶP LẠI CTA Ở BẤT KỲ ĐÂU:\n1. NGUYÊN TẮC CỐT LÕI (ZERO CTA REPETITION ANYWHERE): Tuyệt đối KHÔNG BAO GIỜ đặt 2 lần CTA trong cùng một tập (cấm vừa có CTA giữa bài vừa có CTA cuối bài) và KHÔNG BAO GIỜ lặp lại từ ngữ hay cấu trúc ngữ pháp câu CTA giữa các tập. Cấm tuyệt đối CTA trong 2 phút đầu (00:00–02:00).\n2. VỊ TRÍ & SỰ XUẤT HIỆN DO CÂU CHUYỆN QUYẾT ĐỊNH: Toàn bài chỉ có tối đa 0 hoặc 1 nhịp kết nối khán giả duy nhất đặt ở điểm lặng tự nhiên nhất của câu chuyện đó (hoặc giữ 100% thuần phóng sự 0 khẩu lệnh nút bấm như SBS 그것이 알고싶다 / 꼬꼬무). Tuyệt đối không đóng đinh CTA chặn ngang cuối Hồi 2 hay dựng 4 câu quảng cáo End Screen cuối bài.\n3. ĐA DẠNG CẤU TRÚC CÂU CTA KHÉO LÉO KHÁC HẲN NHAU: CẤM TUYỆT ĐỐI khung câu công nghiệp '[~하시려면 / ~궁금하시다면] + [구독과 좋아요/알림 설정을 눌러 주시기 바랍니다]'. Luân phiên biến hóa cấu trúc câu tự nhiên: câu hỏi mở đặt khán giả vào tình huống (?), lời ghi chú trầm tĩnh khi khép hồ sơ, câu kể đối chiếu vật chứng, hoặc đoản ngữ danh từ tiết chế.",
  narrative_angle: "Điều tra hình sự sắc lạnh",
  writing_style: "Cold Forensic Noir",
  hook_archetype: "Con số định lượng",
  editing_archetypes: ["Forensic case board", "Document scanner"],
  opening_hook: "Vào mùa đông năm 1996, một vụ án rúng động đã làm thay đổi hoàn toàn cục diện điều tra...",
  notes: "Ghi chú điều tra phá án và hồ sơ tâm lý học tội phạm.",
  default_creative_brief: {
    market: "KR",
    language: "ko",
    target_duration_minutes: 20,
    ai_media_mode: "image",
    visual_strategy: "full_ai",
    narrative_angle: "Điều tra hình sự sắc lạnh",
    writing_style: "Cold Forensic Noir",
    hook_archetype: "Con số định lượng",
    editing_archetypes: ["Forensic case board", "Document scanner"],
    opening_hook: "Vào mùa đông năm 1996, một vụ án rúng động đã làm thay đổi hoàn toàn cục diện điều tra...",
    notes: "Ghi chú điều tra phá án và hồ sơ tâm lý học tội phạm.",
    custom_rules: "100% Green Monetization - Cắt bỏ yếu tố ghê rợn trực diện | [Chuẩn Khán Giả Góp Ý 특급수배록]: (1) Kịch bản & Logic: Nguyên tắc Chiếc súng của Chekhov — mọi nhân vật/manh mối mở màn (VD: thương nhân họ Ngụy mang túi tiền vào trọ) bắt buộc có kết cục rõ ràng (hoặc 1–2 câu tóm lược nhẹ nhàng nếu nhạy cảm); xưng hô chuẩn văn hóa Hàn (cấm gọi 58–62 tuổi là 노부부, dùng 여관 주인 부부 / 50대 후반 부부); (2) Giọng đọc & TTS: Tông giọng trầm ấm đêm khuya êm tai (K1 - Trầm Sâu Đêm Khuya SBS Style), chuẩn hóa số đếm Hán-Hàn (19년=십구 년, 50대=오십대) không đọc vấp; (3) Phần kết: Câu thoại cuối hoàn tất trọn vẹn 100% không cắt ngang + dư 3–5s (3.8s) nhạc nền hạ màn fade-out; (4) Checklist trước xuất bản: [ ] Kịch bản | [ ] Giọng đọc | [ ] Phần kết.",
    cta_strategy: "ROLE KỂ CHUYỆN & CTA LINH HOẠT THEO TRUYỆN — KHÔNG BAO GIỜ LẶP LẠI CTA Ở BẤT KỲ ĐÂU:\n1. NGUYÊN TẮC CỐT LÕI (ZERO CTA REPETITION ANYWHERE): Tuyệt đối KHÔNG BAO GIỜ đặt 2 lần CTA trong cùng một tập (cấm vừa có CTA giữa bài vừa có CTA cuối bài) và KHÔNG BAO GIỜ lặp lại từ ngữ hay cấu trúc ngữ pháp câu CTA giữa các tập. Cấm tuyệt đối CTA trong 2 phút đầu (00:00–02:00).\n2. VỊ TRÍ & SỰ XUẤT HIỆN DO CÂU CHUYỆN QUYẾT ĐỊNH: Toàn bài chỉ có tối đa 0 hoặc 1 nhịp kết nối khán giả duy nhất đặt ở điểm lặng tự nhiên nhất của câu chuyện đó (hoặc giữ 100% thuần phóng sự 0 khẩu lệnh nút bấm như SBS 그것이 알고싶다 / 꼬꼬무). Tuyệt đối không đóng đinh CTA chặn ngang cuối Hồi 2 hay dựng 4 câu quảng cáo End Screen cuối bài.\n3. ĐA DẠNG CẤU TRÚC CÂU CTA KHÉO LÉO KHÁC HẲN NHAU: CẤM TUYỆT ĐỐI khung câu công nghiệp '[~하시려면 / ~궁금하시다면] + [구독과 좋아요/알림 설정을 눌러 주시기 바랍니다]'. Luân phiên biến hóa cấu trúc câu tự nhiên: câu hỏi mở đặt khán giả vào tình huống (?), lời ghi chú trầm tĩnh khi khép hồ sơ, câu kể đối chiếu vật chứng, hoặc đoản ngữ danh từ tiết chế.",
  },
  editing_dna: {
    version: 1,
    pacing: 5.5,
    typical_pacing_sec: 5.5,
    visual_mix: { footage: 0.1, ai: 0.8, motion: 0.1 },
    editing_archetypes: ["forensic_case_board", "document_scanner"],
    subtitle_style: { font_family: "Pretendard, sans-serif", color: "#ffffff", highlight_color: "#38bdf8", font_size: 42 },
    color_grade: "cold_cyan",
    audio_rules: { music_ducking_db: -18.0, sfx_hit_on_chapter: true, tension_drone_under_interrogation: true }
  }
};

function isCustomDnaProfile(profile) {
  if (!profile) return false;
  const ed = profile.editorial_dna || {};
  const mode = String(profile.dna_mode || ed.dna_mode || profile.source_mode || profile.latest_analysis?.source_mode || "").trim().toLowerCase();
  return mode === "custom_dna_only" || Boolean(
    profile.allowed_topics || ed.allowed_topics || profile.forbidden_topics || ed.forbidden_topics || profile.monetization_safety_policy || ed.monetization_safety_policy
  );
}

function getProfileDnaFields(profile) {
  const ed = profile?.editorial_dna || {};
  const narrative = ed.narrative || {};
  const footage = ed.footage || {};
  return {
    dnaMode: isCustomDnaProfile(profile) ? "custom_dna_only" : "auto_radar",
    language: String(profile?.default_language || ed.default_language || (String(profile?.market || "KR").toUpperCase() === "KR" ? "ko" : "vi")),
    visualStrategy: String(profile?.default_visual_strategy || ed.visual_strategy || "full_ai"),
    voiceAndStructure: String(profile?.voice_and_structure || ed.voice_and_structure || narrative.language || ""),
    referenceImagePolicy: String(profile?.reference_image_policy || ed.reference_image_policy || (Array.isArray(footage.rules) ? footage.rules[0] : "") || ""),
    allowedTopics: String(profile?.allowed_topics || ed.allowed_topics || narrative.story_engine || ""),
    forbiddenTopics: String(profile?.forbidden_topics || ed.forbidden_topics || (Array.isArray(footage.avoid) ? footage.avoid[0] : "") || ""),
    monetizationSafetyPolicy: String(profile?.monetization_safety_policy || ed.monetization_safety_policy || narrative.monetization_safety_policy || ""),
    ctaStrategy: String(profile?.cta_strategy || ed.cta_strategy || narrative.cta_strategy || profile?.default_creative_brief?.cta_strategy || ""),
  };
}

function setCreateDiscoveryMode(mode, { triggerDiscover = false } = {}) {
  const resolved = mode === "radar_trend" ? "radar_trend" : "dna_strict";
  state.createDiscoveryMode = resolved;
  $$("#createDiscoveryModeSwitch [data-discovery-mode]").forEach(btn => {
    const active = btn.dataset.discoveryMode === resolved;
    btn.classList.toggle("active", active);
    btn.setAttribute("aria-selected", active ? "true" : "false");
  });
  const btn = $("#discoverCreateTopicsBtn");
  const eyebrow = $("#createDiscoveryEyebrow");
  const headline = $("#createDiscoveryHeadline");
  const status = $("#createTopicDiscoveryStatus");
  if (resolved === "dna_strict") {
    if (eyebrow) eyebrow.textContent = "RESEARCH CHỦ ĐỀ MỚI THEO DNA KÊNH (ĐỘC LẬP RADAR · CHỐNG LẶP 100%)";
    if (headline) headline.textContent = "2 Luồng Chủ Đạo (💰 Tội phạm Tài chính · 🚨 Vụ án Đặc biệt Nguy hiểm) → Research Hồ Sơ Thật → Ngôi Kể Xanh Tiền";
    if (btn && !btn.disabled) btn.textContent = "🔍 Research đề tài mới theo DNA";
    if (status && !state.createTopicSuggestions?.length) {
      status.textContent = "Đang khóa theo Bộ lọc DNA 2 Luồng của Hồ sơ Kênh đang chọn (Research hồ sơ vụ án thật, chống gợi ý lặp lại).";
    }
  } else {
    if (eyebrow) eyebrow.textContent = "QUÉT TÍN HIỆU RADAR 48H & ĐỐI THỦ (TUBERADAR)";
    if (headline) headline.textContent = "Kênh mình → Kênh đối thủ → Trend 48h → Chủ đề đề xuất";
    if (btn && !btn.disabled) btn.textContent = "📡 Quét Radar 48h & tìm chủ đề";
    if (status && !state.createTopicSuggestions?.length) {
      status.textContent = "Chế độ Radar: Quét tín hiệu 48h từ kênh mình và kênh đối thủ.";
    }
  }
  const activeProfile = state.channelProfiles.find(item => item.id === (String($("#jobForm")?.elements?.channel_profile_id?.value || state.selectedChannelProfileId || "").trim())) || null;
  const streamBar = $("#createTopicStreamBar");
  if (streamBar) {
    streamBar.classList.toggle("hidden", !(resolved === "dna_strict" && isTwoStreamTrueCrimeProfile(activeProfile)));
  }
  if (triggerDiscover) {
    discoverCreateTopics({ forceRefresh: false }).catch(err => toast(err.message, true));
  }
}

$$("#createDiscoveryModeSwitch [data-discovery-mode]").forEach(btn => {
  btn.addEventListener("click", () => {
    setCreateDiscoveryMode(btn.dataset.discoveryMode, { triggerDiscover: true });
  });
});

function renderCreateProfileDnaSummary(profile) {
  const box = $("#createProfileDnaSummary");
  if (!box) return;
  if (!profile) {
    box.classList.add("hidden");
    box.innerHTML = "";
    return;
  }
  const dna = getProfileDnaFields(profile);
  const brief = profile.default_creative_brief || (profile.editorial_dna || {}).default_creative_brief || {};
  const edDna = profile.editing_dna || (profile.editorial_dna || {}).editing_dna || {};
  const ownRef = String(profile.own_channel_ref || profile.own_channel?.ref || "").trim();
  const ownTitle = profile.own_channel?.title || profile.own_channel?.label || ownRef;
  const ownUrl = profile.own_channel?.url || (ownRef.startsWith("http") ? ownRef : "");
  const langLabel = { ko: "Hàn Quốc (KR)", ja: "Nhật Bản (JP)", en: "Quốc tế (EN)", vi: "Việt Nam (VI)" }[dna.language] || dna.language;
  const strategyLabel = dna.visualStrategy === "full_ai"
    ? "100% Full AI (full_ai) — Nhận Ảnh tham chiếu (Reference Image) ở đầu mỗi dự án để khóa phong cách toàn bộ phân cảnh"
    : dna.visualStrategy === "hybrid"
      ? "Kết hợp Footage thực tế + AI Visual + Đồ họa 2.5D (hybrid)"
      : dna.visualStrategy;
  const durationMinutes = Number(profile.default_duration_minutes || profile.target_duration_minutes || brief.target_duration_minutes || 20);
  const structureHint = brief.narrative_angle || brief.writing_style || "Chuẩn cấu trúc DNA Kênh";
  const rawPacing = typeof edDna.pacing === "object" && edDna.pacing !== null
    ? (edDna.pacing.typical_pacing_sec || edDna.pacing.target_beat_duration_sec || edDna.pacing.average_beat_duration_sec)
    : (edDna.pacing || edDna.typical_pacing_sec);
  const pacingSec = Number(rawPacing) || (dna.visualStrategy === "full_ai" ? 5.5 : 4.5);
  const mixSummary = formatVisualMixSummary(edDna.visual_mix);
  const rawColorGrade = typeof edDna.color_grade === "object" && edDna.color_grade !== null
    ? (edDna.color_grade.tone_preset || edDna.color_grade.lut_name)
    : edDna.color_grade;
  const colorGrade = String(rawColorGrade || (dna.visualStrategy === "full_ai" ? "cold_forensic_noir" : "technical_cool_cyan"));

  const helpEl = $("#createProfileHelpText");
  if (helpEl) {
    helpEl.textContent = `Đã khóa theo hồ sơ "${profile.label || profile.id}": Thị trường ${profile.market || "KR"} (${dna.language}), Thời lượng ${durationMinutes} phút, Chiến lược ${dna.visualStrategy}, Nhịp dựng ${pacingSec}s/beat và Bộ lọc Đề tài Xanh tiền riêng biệt.`;
  }

  const vSig = profile.voice_signature || {};
  const rDna = profile.rhythm_dna || {};
  const wCad = rDna.writing_cadence || {};
  const vCad = rDna.vocal_cadence || {};
  const eCad = rDna.editing_cadence || {};
  const vColor = rDna.voice_color_spec || vSig.voice_color_spec || {};
  const lockedVoiceName = vSig.voice_name || (profile.voice_id ? `Voice ID ${String(profile.voice_id).slice(0, 8)}` : "Tự động thiết kế từ giọng mẫu sạch K1");
  const wAvgChars = Array.isArray(wCad.target_avg_sentence_chars) ? wCad.target_avg_sentence_chars.join("–") : (wCad.target_avg_sentence_chars || "28–45");
  const wPunchRatio = Array.isArray(wCad.short_punch_ratio_target)
    ? `${wCad.short_punch_ratio_target.map(x => Math.round(Number(x || 0) * 100)).join("–")}%`
    : `${Math.round(Number(wCad.short_punch_ratio_target || 0.22) * 100)}%`;
  const vSpsText = Array.isArray(vCad.target_sps_range)
    ? `${vCad.target_sps_range[0]}–${vCad.target_sps_range[vCad.target_sps_range.length - 1]}`
    : "4.0–5.0";
  const eHoldThr = Number(eCad.dramatic_pause_hold_threshold_sec || eCad.hold_through_silence_threshold_sec || 1.15).toFixed(2);
  const rhythmLockLine = (wCad.target_avg_sentence_chars || vCad.target_sps_range || eCad.editor_feel_title_vi)
    ? `<li><b>🎙️ Voice 1-of-1 &amp; Đồng Bộ Nhịp 3 Tầng:</b> <code>${escapeHtml(lockedVoiceName)}</code>${vColor.color_label_vi ? ` (${escapeHtml(vColor.color_label_vi)})` : ""} · <b>[Nhịp Viết]</b> ${escapeHtml(String(wAvgChars))} ký tự/câu, phanh ngắn ${escapeHtml(wPunchRatio)} · <b>[Nhịp Đọc]</b> ${escapeHtml(vSpsText)} âm tiết/s, nghỉ cảm xúc 7 tầng · <b>[Nhịp Dựng @edit]</b> ${escapeHtml(eCad.editor_feel_title_vi || `Neo hình qua khoảng lặng >= ${eHoldThr}s`)}</li>`
    : `<li><b>🎙️ Voice Độc Bản Kênh:</b> <code>${escapeHtml(lockedVoiceName)}</code></li>`;

  const fullDnaRulebookPopupHtml = `
    <div class="inspector-dossier-grid" style="margin-bottom:14px;">
      <div class="inspector-dossier-card">
        <h4>🧬 Định danh, Thời lượng &amp; Lối Edit Riêng của Kênh</h4>
        <ul>
          <li><b>Thị trường &amp; Ngôn ngữ:</b> ${escapeHtml(dna.voiceAndStructure || `${langLabel} — Phóng sự tài liệu chuyên sâu`)}</li>
          <li><b>Thời lượng mặc định:</b> ${durationMinutes} phút (${escapeHtml(structureHint)})</li>
          <li><b>Chiến lược Hình ảnh:</b> ${escapeHtml(dna.referenceImagePolicy || strategyLabel)}</li>
          <li><b>Lối Edit &amp; Remotion DNA:</b> Nhịp cắt <b>${pacingSec}s/beat</b> · Tỷ lệ (<b>${escapeHtml(mixSummary)}</b>) · Tone màu <code>${escapeHtml(colorGrade)}</code></li>
          ${rhythmLockLine}
          <li><b>✂️ Luật Sắt Dựng &amp; Footage:</b> Footage <b>3–6s/cut</b> (<code>max_uses=1</code>) · Xóa/crop sạch 100% logo &amp; text kênh khác · Không lấy MC/host · Mỗi cảnh Vox độc nhất theo câu voice</li>
          <li><b>🎯 Chuẩn Khán Giả &amp; Kết Phim:</b> Nguyên tắc <i>Chekhov's Gun</i>, chuẩn hóa số đếm TTS, đọc 7 cung bậc cảm xúc, câu kết trọn vẹn + dư <b>3.8s</b> fade-out</li>
        </ul>
      </div>
      <div class="inspector-dossier-card">
        <h4>🛡️ Bộ lọc Đề tài &amp; An toàn Kiếm tiền (100% Green)</h4>
        <ul>
          ${dna.allowedTopics ? `<li><span class="dna-pill allow">Chỉ chọn</span> ${escapeHtml(dna.allowedTopics)}</li>` : ""}
          ${dna.forbiddenTopics ? `<li><span class="dna-pill forbid">Cấm tuyệt đối</span> ${escapeHtml(dna.forbiddenTopics)}</li>` : ""}
          ${dna.monetizationSafetyPolicy ? `<li><span class="dna-pill green">Ngôi kể &amp; Xanh tiền</span> ${escapeHtml(dna.monetizationSafetyPolicy)}</li>` : ""}
          ${dna.ctaStrategy ? `<li><span class="dna-pill allow">Role CTA Không Lặp</span> ${escapeHtml(dna.ctaStrategy)}</li>` : ""}
        </ul>
      </div>
    </div>
    <div class="dna-lock-channel-bar" style="padding:12px 14px;border-radius:11px;background:rgba(15,28,46,0.85);border:1px solid rgba(56,189,248,0.28);display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;">
      <div class="dna-lock-channel-info" style="font-size:12.5px;">
        <span>🔗 <b>Link Kênh YouTube của bạn:</b> </span>
        ${ownRef
          ? `<strong>${ownUrl ? `<a href="${escapeHtml(ownUrl)}" target="_blank" rel="noreferrer">${escapeHtml(ownTitle)} ↗</a>` : escapeHtml(ownTitle)}</strong>`
          : `<em class="dna-channel-empty" style="color:#94a3b8;">Chưa gắn link kênh (Chạy độc lập 100% theo DNA cố định)</em>`}
      </div>
      <div class="dna-lock-channel-QuickEdit" style="display:flex;gap:8px;align-items:center;flex:1;min-width:260px;max-width:440px;">
        <input type="text" id="quickOwnChannelInput" value="${escapeHtml(ownRef)}" placeholder="Dán link kênh YouTube (@handle hoặc URL)…" style="flex:1;" />
        <button type="button" class="primary compact" id="quickSaveOwnChannelBtn">Lưu link kênh</button>
      </div>
    </div>
  `;

  box.innerHTML = `
    <div class="dna-compact-strip">
      <div class="dna-compact-strip-left">
        <span class="dna-compact-pill emerald">${dna.dnaMode === "custom_dna_only" ? "🔒 DNA Cố định" : "📡 DNA Kênh"} · ${escapeHtml(profile.label || profile.id)}</span>
        <span class="dna-compact-pill cyan">${escapeHtml(profile.market || "KR")} (${escapeHtml(dna.language)}) · ${durationMinutes}p · ${escapeHtml(dna.visualStrategy)}</span>
        <span class="dna-compact-pill">🎙️ ${escapeHtml(lockedVoiceName)} · ${pacingSec}s/beat</span>
        <span class="dna-compact-pill emerald">💚 Xanh tiền 100%</span>
        <span class="dna-compact-pill">${ownRef ? `🔗 ${escapeHtml(ownTitle)}` : "🔗 Độc lập (Chưa gắn kênh)"}</span>
      </div>
      <div class="dna-compact-actions">
        <button type="button" class="ghost compact" id="openProfileDnaRulebookPopupBtn">📜 Quy chuẩn DNA &amp; Gắn kênh</button>
        <button type="button" class="ghost compact" id="jumpEditProfileStep1Btn">✎ Sửa DNA</button>
      </div>
    </div>
  `;
  box.classList.remove("hidden");

  $("#jumpEditProfileStep1Btn")?.addEventListener("click", async () => {
    await selectChannelProfile(profile.id);
    openDnaStudioModal("identity");
  });

  $("#openProfileDnaRulebookPopupBtn")?.addEventListener("click", () => {
    openStudioInspectorModal({
      badge: "🧬",
      title: profile.label || profile.id,
      subtitle: "Quy chuẩn DNA cố định · Bộ lọc Xanh tiền & Gắn kênh YouTube",
      html: fullDnaRulebookPopupHtml,
      onOpen: modalBody => {
        const saveBtn = modalBody.querySelector("#quickSaveOwnChannelBtn");
        const input = modalBody.querySelector("#quickOwnChannelInput");
        saveBtn?.addEventListener("click", async () => {
          const newRef = String(input?.value || "").trim();
          try {
            saveBtn.disabled = true;
            saveBtn.textContent = "Đang lưu…";
            const saved = await api(`/api/radar/channel-profiles/${encodeURIComponent(profile.id)}`, {
              method: "PATCH",
              body: JSON.stringify({
                label: profile.label,
                own_channel_ref: newRef,
                competitor_refs: profile.competitor_refs || [],
                market: profile.market || "KR",
                default_duration_minutes: profile.default_duration_minutes || 20,
                default_language: dna.language,
                default_visual_strategy: dna.visualStrategy,
                dna_mode: dna.dnaMode,
                voice_and_structure: dna.voiceAndStructure,
                reference_image_policy: dna.referenceImagePolicy,
                allowed_topics: dna.allowedTopics,
                forbidden_topics: dna.forbiddenTopics,
                monetization_safety_policy: dna.monetizationSafetyPolicy,
                cta_strategy: dna.ctaStrategy,
              }),
            });
            await loadChannelProfiles({ selectId: saved.id, loadPlan: false });
            toast(newRef ? "Đã gắn link kênh YouTube vào Hồ sơ DNA thành công!" : "Đã cập nhật Hồ sơ DNA.");
          } catch (err) {
            toast(err.message, true);
          } finally {
            saveBtn.disabled = false;
            saveBtn.textContent = "Lưu link kênh";
          }
        });
      },
    });
  });
}

async function renderCreatePreflightSummary(profileId, topic = "", title = "") {
  const box = $("#createPreflightSummaryBox");
  const content = $("#preflightSummaryContent");
  const headline = $("#preflightStatusHeadline");
  const popupBtn = $("#openPreflightPopupBtn");
  if (!box || !content) return;

  if (!profileId) {
    content.innerHTML = `<div class="empty-state" style="padding:4px 0;font-size:11.8px;color:#94a3b8;">Chọn một Hồ sơ Kênh để kích hoạt Channel-DNA Pre-Flight Check.</div>`;
    if (headline) headline.textContent = "Chưa chọn hồ sơ kênh";
    popupBtn?.classList.add("hidden");
    return;
  }

  const candidateTopic = String(topic || title || $("#createManualTitleInput")?.value || "").trim();
  content.innerHTML = `<div style="font-size:11.8px;color:#94a3b8;">⏳ Đang đối chiếu DNA Kênh, kiểm tra trùng lặp và từ khóa thắng thế…</div>`;

  try {
    const res = await api(`/api/radar/channel-profiles/${encodeURIComponent(profileId)}/preflight-check?stage=topic&topic=${encodeURIComponent(candidateTopic)}&title=${encodeURIComponent(title || candidateTopic)}`);
    const summary = res.preflight_summary || {};
    const passed = summary.passed !== false;
    const isDup = Boolean(summary.duplicate_risk);
    const rawRecs = Array.isArray(summary.recommendations) ? summary.recommendations : [];
    const recs = rawRecs.filter(r => !/từ khóa kém hiệu quả:\s*(사건|실화|중국|사기|인프라)/i.test(String(r || "")));
    const patterns = Array.isArray(summary.winner_patterns_matched) ? summary.winner_patterns_matched : [];

    let badgeClass = "green";
    let badgeText = "✓ PASSED (HỢP LỆ DNA KÊNH)";
    if (isDup) {
      badgeClass = "forbid";
      badgeText = "⚠ DUPLICATE RISK (TRÙNG LẶP ĐỀ TÀI)";
    } else if (!passed) {
      badgeClass = "forbid";
      badgeText = "✕ BLOCKED (VI PHẠM ĐIỀU CẤM DNA)";
    }

    if (headline) {
      headline.innerHTML = `Pre-Flight: <span class="dna-pill ${badgeClass}" style="margin-left:6px;font-size:11px;">${badgeText}</span>`;
    }

    const patternPills = patterns.length
      ? patterns.map(p => `<span style="display:inline-block;padding:2px 8px;border-radius:12px;background:rgba(0,200,255,0.15);border:1px solid rgba(0,200,255,0.3);color:#7dd3fc;font-size:11px;font-weight:600;margin-right:5px;">★ ${escapeHtml(p)}</span>`).join("")
      : `<span class="muted" style="font-size:11.5px;">Chưa khớp cụm Outlier mẫu</span>`;

    const chCheck = summary.channel_history_check || {};
    const memCheck = summary.profile_memory_check || {};
    const pass1Html = chCheck.duplicate_found
      ? `<span style="font-size:11.5px;color:#f87171;">✕ <b>Pass 1 (YouTube Kênh):</b> Trùng "${escapeHtml(chCheck.matched_title || "")}"</span>`
      : `<span style="font-size:11.5px;color:#34d399;">✓ <b>Pass 1 (YouTube Kênh):</b> Sạch</span>`;
    const pass2Html = memCheck.duplicate_found
      ? `<span style="font-size:11.5px;color:#f87171;">✕ <b>Pass 2 (Bộ nhớ Hồ sơ):</b> Trùng [${escapeHtml(memCheck.matched_job_id || "")}]</span>`
      : `<span style="font-size:11.5px;color:#34d399;">✓ <b>Pass 2 (Bộ nhớ Hồ sơ):</b> Đề tài mới</span>`;

    const compactAlertHtml = (isDup || !passed) && recs.length
      ? `<div style="font-size:11.5px;color:#fca5a5;margin-top:3px;">⚠ ${escapeHtml(recs[0])}</div>`
      : "";

    content.innerHTML = `
      <div style="display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap;">
        <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;">
          ${pass1Html}
          <span style="color:#475569;">|</span>
          ${pass2Html}
        </div>
        <div style="font-size:11.5px;">${patternPills}</div>
      </div>
      ${compactAlertHtml}
    `;

    const fullPreflightHtml = `
      <div style="display:flex;flex-direction:column;gap:12px;">
        <div class="inspector-dossier-card">
          <h4>✈ Đề tài đang kiểm tra</h4>
          <div style="font-size:14px;font-weight:700;color:#f8fafc;">${escapeHtml(candidateTopic || "(Chưa nhập tiêu đề cụ thể — đang dùng quy chuẩn kênh)")}</div>
          <div style="margin-top:10px;display:flex;flex-direction:column;gap:6px;">
            <div>${pass1Html}</div>
            <div>${pass2Html}</div>
          </div>
        </div>
        <div class="inspector-dossier-card">
          <h4>★ Cụm từ khóa Outlier đã khớp</h4>
          <div>${patternPills}</div>
        </div>
        <div class="inspector-dossier-card">
          <h4>📋 Khuyến nghị &amp; Cảnh báo Pre-Flight</h4>
          ${recs.length ? `<ul>${recs.map(r => `<li>${escapeHtml(r)}</li>`).join("")}</ul>` : `<div style="color:#34d399;font-size:13px;">✓ Không phát hiện vi phạm hoặc rủi ro trùng lặp. Đề tài sẵn sàng đưa vào sản xuất!</div>`}
        </div>
      </div>
    `;
    if (popupBtn) {
      popupBtn.classList.remove("hidden");
      popupBtn.onclick = () => openStudioInspectorModal({
        badge: "✈",
        title: "BÁO CÁO PRE-FLIGHT DNA CHI TIẾT",
        subtitle: badgeText,
        html: fullPreflightHtml,
      });
    }
  } catch (err) {
    content.innerHTML = `<div style="font-size:12px;color:#ff6475;">Lỗi kiểm tra Pre-Flight: ${escapeHtml(err.message)}</div>`;
  }
}

function renderSelfLearningReport(report) {
  const content = $("#selfLearningContent");
  const headline = $("#selfLearningHeadline");
  const subtitle = $("#selfLearningSubtitle");
  if (!content) return;

  if (!report || !report.profile_id) {
    content.innerHTML = `<div class="empty-state" style="padding:16px 0;font-size:12.5px;color:#94a3b8;">Chọn một hồ sơ kênh ở trên để xem phân tích Thắng/Thua và bộ quy tắc tiến hóa video.</div>`;
    if (headline) headline.textContent = "Báo cáo Giải phẫu Thắng / Thua & Quy tắc Nâng cấp Video Kế tiếp";
    return;
  }

  const pid = report.profile_id;
  const count = report.analyzed_videos_count || 0;
  const winners = Array.isArray(report.winners) ? report.winners : [];
  const underperformers = Array.isArray(report.underperformers) ? report.underperformers : [];
  const diagnostics = Array.isArray(report.diagnostics) ? report.diagnostics : [];
  const rules = report.upgrade_rules || {};
  const stopDoing = Array.isArray(rules.what_to_stop_doing) ? rules.what_to_stop_doing : [];
  const doubleDown = Array.isArray(rules.what_to_double_down_on) ? rules.what_to_double_down_on : [];
  const nextUpgrades = Array.isArray(rules.next_video_upgrades) ? rules.next_video_upgrades : [];
  const thumbDna = report.thumbnail_dna || {};
  const seoDna = report.seo_dna || {};
  const patterns = Array.isArray(report.title_winner_patterns) ? report.title_winner_patterns : [];

  if (headline) {
    headline.innerHTML = `Báo cáo Giải phẫu Thắng/Thua · Hồ sơ: <span style="color:#00c8ff;">${escapeHtml(pid)}</span>`;
  }
  if (subtitle) {
    subtitle.textContent = `Đã phân tích ${count} video lịch sử. Phân loại Outlier nổ view, mổ xẻ nguyên nhân suy giảm và tự động tổng hợp bộ quy tắc tiến hóa cho video kế tiếp.`;
  }

  const winnerCardsHtml = winners.length
    ? winners.map(w => `
        <div style="padding:8px 12px;background:rgba(16,185,129,0.08);border:1px solid rgba(16,185,129,0.25);border-radius:8px;display:flex;justify-content:space-between;align-items:center;gap:10px;">
          <div style="font-size:13px;color:#f1f5f9;line-height:1.4;">
            <b style="color:#10b981;">🏆</b> ${escapeHtml(w.title || w.video_id)}
          </div>
          <div style="white-space:nowrap;text-align:right;">
            <span style="display:inline-block;padding:2px 8px;border-radius:12px;background:rgba(16,185,129,0.2);color:#34d399;font-weight:700;font-size:11.5px;">${w.multiplier ? `${w.multiplier}x Median` : 'NỔ VIEW'}</span>
            <div style="font-size:11px;color:#94a3b8;margin-top:2px;">${Number(w.views || 0).toLocaleString()} views</div>
          </div>
        </div>
      `).join("")
    : `<div style="font-size:12px;color:#94a3b8;padding:8px;">Chưa phát hiện video Outlier vượt ngưỡng 2.0x median.</div>`;

  const causeLabels = {
    title_too_long_low_ctr: "Tiêu đề quá dài (>15 từ) giảm CTR mobile",
    weak_keyword_fatigue: "Trùng lặp từ khóa yếu (Weak Terms)",
    weak_hook_or_niche_deviation: "Hook mở đầu yếu hoặc lệch ngách kênh",
  };

  const underCardsHtml = underperformers.length
    ? underperformers.map(u => `
        <div style="padding:8px 12px;background:rgba(255,77,94,0.08);border:1px solid rgba(255,77,94,0.25);border-radius:8px;display:flex;justify-content:space-between;align-items:center;gap:10px;">
          <div style="font-size:13px;color:#f1f5f9;line-height:1.4;">
            <b style="color:#ff6475;">⚠</b> ${escapeHtml(u.title || u.video_id)}
            <div style="font-size:11.5px;color:#ff6475;margin-top:2px;">Nguyên nhân: <i>${escapeHtml(causeLabels[u.cause] || u.cause || "Chưa xác định")}</i></div>
          </div>
          <div style="white-space:nowrap;text-align:right;">
            <span style="display:inline-block;padding:2px 8px;border-radius:12px;background:rgba(255,77,94,0.2);color:#fca5a5;font-weight:700;font-size:11.5px;">${u.multiplier ? `${u.multiplier}x Median` : '<0.6x'}</span>
            <div style="font-size:11px;color:#94a3b8;margin-top:2px;">${Number(u.views || 0).toLocaleString()} views</div>
          </div>
        </div>
      `).join("")
    : `<div style="font-size:12px;color:#94a3b8;padding:8px;">Không có video nào suy giảm dưới 0.6x median. Tình trạng kênh rất đồng đều!</div>`;

  content.innerHTML = `
    <div style="display:flex;flex-direction:column;gap:14px;">
      <!-- Stats Overview -->
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px;">
        <div style="padding:10px 14px;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);border-radius:8px;">
          <div style="font-size:11px;color:#94a3b8;text-transform:uppercase;letter-spacing:0.5px;">Tổng video phân tích</div>
          <div style="font-size:20px;font-weight:800;color:#f1f5f9;margin-top:2px;">${count}</div>
        </div>
        <div style="padding:10px 14px;background:rgba(16,185,129,0.06);border:1px solid rgba(16,185,129,0.2);border-radius:8px;">
          <div style="font-size:11px;color:#34d399;text-transform:uppercase;letter-spacing:0.5px;">Outliers Nổ View (≥ 2.0x)</div>
          <div style="font-size:20px;font-weight:800;color:#10b981;margin-top:2px;">${winners.length}</div>
        </div>
        <div style="padding:10px 14px;background:rgba(255,77,94,0.06);border:1px solid rgba(255,77,94,0.2);border-radius:8px;">
          <div style="font-size:11px;color:#fca5a5;text-transform:uppercase;letter-spacing:0.5px;">Dưới Kỳ Vọng (&lt; 0.6x)</div>
          <div style="font-size:20px;font-weight:800;color:#ff6475;margin-top:2px;">${underperformers.length}</div>
        </div>
      </div>

      <!-- Win / Loss Columns -->
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:12px;">
        <div>
          <div style="font-size:13px;font-weight:700;color:#10b981;margin-bottom:6px;display:flex;align-items:center;gap:6px;">
            <span>🏆 Video Thắng Thế (Outlier Winners)</span>
            <span style="font-size:11px;background:rgba(16,185,129,0.2);padding:1px 6px;border-radius:10px;">${winners.length}</span>
          </div>
          <div style="display:flex;flex-direction:column;gap:6px;">
            ${winnerCardsHtml}
          </div>
        </div>
        <div>
          <div style="font-size:13px;font-weight:700;color:#ff6475;margin-bottom:6px;display:flex;align-items:center;gap:6px;">
            <span>⚠️ Video Dưới Kỳ Vọng &amp; Chẩn Đoán</span>
            <span style="font-size:11px;background:rgba(255,77,94,0.2);padding:1px 6px;border-radius:10px;">${underperformers.length}</span>
          </div>
          <div style="display:flex;flex-direction:column;gap:6px;">
            ${underCardsHtml}
          </div>
        </div>
      </div>

      <!-- Upgrade Rules Synthesized -->
      <div style="padding:12px 16px;background:rgba(0,200,255,0.05);border:1px solid rgba(0,200,255,0.25);border-radius:10px;">
        <div style="font-size:13px;font-weight:800;color:#00c8ff;margin-bottom:8px;letter-spacing:0.5px;">
          ⚡ BỘ QUY TẮC TIẾN HÓA TỰ ĐỘNG CHO DỰ ÁN KẾ TIẾP (AUTO-INJECTED RULES)
        </div>
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:10px;font-size:12.5px;line-height:1.5;">
          ${stopDoing.length ? `
            <div style="padding:8px 12px;background:rgba(255,77,94,0.08);border:1px solid rgba(255,77,94,0.2);border-radius:6px;">
              <strong style="color:#ff6475;">🛑 Cần Dừng Lại (Stop Doing):</strong>
              <ul style="margin:4px 0 0;padding-left:16px;">${stopDoing.map(r => `<li>${escapeHtml(r)}</li>`).join("")}</ul>
            </div>
          ` : ""}
          ${doubleDown.length ? `
            <div style="padding:8px 12px;background:rgba(16,185,129,0.08);border:1px solid rgba(16,185,129,0.2);border-radius:6px;">
              <strong style="color:#10b981;">🚀 Cần Tăng Cường (Double Down):</strong>
              <ul style="margin:4px 0 0;padding-left:16px;">${doubleDown.map(r => `<li>${escapeHtml(r)}</li>`).join("")}</ul>
            </div>
          ` : ""}
          ${nextUpgrades.length ? `
            <div style="padding:8px 12px;background:rgba(251,191,36,0.08);border:1px solid rgba(251,191,36,0.2);border-radius:6px;">
              <strong style="color:#fbbf24;">🎯 Nâng Cấp Video Kế Tiếp:</strong>
              <ul style="margin:4px 0 0;padding-left:16px;">${nextUpgrades.map(r => `<li>${escapeHtml(r)}</li>`).join("")}</ul>
            </div>
          ` : ""}
        </div>
      </div>

      <!-- DNA Highlights -->
      <div style="display:flex;flex-wrap:wrap;gap:12px;font-size:12px;color:#94a3b8;padding-top:4px;">
        <div><b>Thumbnail DNA:</b> <span style="color:#f1f5f9;">${escapeHtml(thumbDna.archetype || "broadcast_left_heavy")}</span> (tối đa ${thumbDna.max_words || 5} từ, màu ${escapeHtml(thumbDna.accent_color || "#38BDF8")})</div>
        <div><b>SEO DNA:</b> <span style="color:#f1f5f9;">Tối thiểu ${seoDna.min_tags || 8} tags</span></div>
        ${patterns.length ? `<div><b>Winner Title Patterns:</b> ${patterns.map(p => `<code style="color:#7dd3fc;background:rgba(0,200,255,0.1);padding:1px 5px;border-radius:4px;margin-right:4px;">${escapeHtml(p)}</code>`).join("")}</div>` : ""}
      </div>
    </div>
  `;
}

async function renderSelfLearningReportForProfile(profileId) {
  const content = $("#selfLearningContent");
  if (!content) return;
  if (!profileId) {
    renderSelfLearningReport(null);
    return;
  }
  content.innerHTML = `<div style="font-size:12.5px;color:#94a3b8;padding:12px 0;">⏳ Đang trích xuất dữ liệu video và chạy phân tích Post-Mortem cho kênh…</div>`;
  try {
    const res = await api(`/api/radar/channel-profiles/${encodeURIComponent(profileId)}/self-learning`);
    renderSelfLearningReport(res);
  } catch (err) {
    content.innerHTML = `<div style="font-size:12.5px;color:#94a3b8;padding:12px 0;">Chưa có dữ liệu Post-Mortem được lưu. Bấm <b>"⚡ Chạy Phân Tích Post-Mortem"</b> để giải phẫu video của kênh này.</div>`;
  }
}

function isTwoStreamTrueCrimeProfile(profile) {
  if (!profile) return false;
  if (Array.isArray(profile.topic_streams) && profile.topic_streams.length >= 1) return true;
  if (Array.isArray(profile.editorial_dna?.topic_streams) && profile.editorial_dna.topic_streams.length >= 1) return true;
  const pid = String(profile.id || "").toLowerCase();
  if (pid === "channel-kr-truecrime-director-v2" || pid === "channel-kr-financial-fugitive-director-v2" || pid === "channel-e544a64b7c") return true;
  const blob = `${profile.label || ""} ${profile.allowed_topics || ""} ${profile.editorial_dna?.allowed_topics || ""}`.toLowerCase();
  return blob.includes("특급수배록") || blob.includes("true crime") || blob.includes("강력범죄") || blob.includes("trọng án");
}

function classifyClientTopicStream(item) {
  const raw = item?.raw || item || {};
  const blob = `${item?.title || ""} ${item?.titleVi || ""} ${raw.case_real_name_zh || ""} ${raw.winner_cluster || ""} ${item?.note || ""}`.toLowerCase();
  // Hard-route all vault break-ins, safe-cracking, bank robberies, armored cash-in-transit & gold/jewelry/museum heists to Stream 1
  if (/(금고\s*털이|금고\s*절단|금고\s*개방|대형\s*금고|기업\s*금고|은행\s*금고|청진기\s*하나로|산소절단기|현금수송차|현금\s*수송차|수송차\s*탈취|수송차\s*털|수송차\s*습격|현금\s*3,500만|은행\s*털|은행을\s*털|은행\s*방탄유리|저축소|보석상|순금\s*48kg|선양\s*3·8|고궁박물원|카이펑\s*박물관|쓰촨\s*박물관|도굴\s*대사건|đột nhập kho bạc|mở két|phá két|cắt két|trộm két|cướp tiền|cướp ngân hàng|cướp xe chở tiền|cướp tiệm vàng|金库被盗|切割金库|开启金库|技术开启|运钞车|银行劫案|储蓄所|绿洲珠宝行|48公斤黄金|沈阳3·8|故宫博物院|开封博物馆)/i.test(blob)) {
    return "financial_crime";
  }
  const explicit = String(item?.topicStream || raw.topic_stream || "").trim().toLowerCase();
  if (explicit === "financial_crime" || explicit === "major_violent_crime") return explicit;
  if (/(국채|증권|은행|금고|예금|금융|위조|공금|자산|집자|불법\s*모금|선물\s*거래|tài chính|ngân hàng|công trái|chứng khoán|két sắt|tiền gửi|tín dụng|hối phiếu|国债|证券|银行|金库|存款|集资|票据|猎狐|经侦)/i.test(blob)) {
    return "financial_crime";
  }
  return "major_violent_crime";
}

function selectCreateTopic(item, index = 0) {
  if (!item) return;
  state.selectedCreateTopic = item;
  state.selectedRadar = null;
  state.selectedChannelPlan = null;
  const form = $("#jobForm");
  if (!form) return;
  form.elements.title.value = item.title || "";
  if (item.url && form.elements.source_url) form.elements.source_url.value = item.url;
  const raw = item.raw || {};
  const streamKey = classifyClientTopicStream(item);
  const streamHeader = streamKey === "financial_crime"
    ? "[LUỒNG 1 · ĐẠI ÁN TÀI CHÍNH, KHO BẠC, MỞ KÉT & CƯỚP TIỀN ĐÀO TẨU]"
    : "[LUỒNG 2 · TRỌNG ÁN HÌNH SỰ, ÁN LẠNH PHÁP Y & TRUY NÃ CẤP A]";
  const realZh = String(item.caseRealNameZh || raw.case_real_name_zh || "").trim();
  const archivalKws = Array.isArray(item.archivalSearchKeywordsZh) && item.archivalSearchKeywordsZh.length
    ? item.archivalSearchKeywordsZh
    : (Array.isArray(raw.archival_search_keywords_zh) ? raw.archival_search_keywords_zh : []);
  const voxVerbs = Array.isArray(item.recommendedVoxVerbs) && item.recommendedVoxVerbs.length
    ? item.recommendedVoxVerbs
    : (Array.isArray(raw.recommended_vox_verbs) ? raw.recommended_vox_verbs : []);
  const noteParts = [];
  if (realZh) noteParts.push(`${streamHeader} Hồ sơ gốc xác thực 100%: ${realZh}`);
  if (archivalKws.length) noteParts.push(`[TỪ KHÓA TƯ LIỆU GỐC CCTV/CÔNG AN]: ${archivalKws.join(" | ")}`);
  if (voxVerbs.length) noteParts.push(`[ĐỘNG TỪ THỊ GIÁC VOX LEGO V13 GỢI Ý]: ${voxVerbs.join(", ")}`);
  if (item.note) noteParts.push(item.note);
  const fullNote = noteParts.join("\n");
  if (fullNote && form.elements.notes) form.elements.notes.value = fullNote;
  if (fullNote && $("#createNotesTextarea")) $("#createNotesTextarea").value = fullNote;
  if (item.profileId && form.elements.channel_profile_id) form.elements.channel_profile_id.value = item.profileId;
  // Do NOT overwrite user's chosen target_duration_minutes when clicking a topic card
  if (raw.opening_hook && form.elements.opening_hook) {
    form.elements.opening_hook.value = String(raw.opening_hook);
  }
  const badge = $("#selectedTopicBadge");
  const modeTag = state.createDiscoveryMode === "dna_strict"
    ? (streamKey === "financial_crime" ? `💰 TÀI CHÍNH #${index + 1}` : `🚨 ĐẶC BIỆT NGUY HIỂM #${index + 1}`)
    : `RADAR #${index + 1}`;
  badge.classList.remove("hidden");
  badge.innerHTML = `<span>${escapeHtml(modeTag)}</span><strong>${escapeHtml(item.title)}</strong><button type="button" id="clearTopicBtn">×</button>`;
  $("#clearTopicBtn")?.addEventListener("click", () => {
    clearSelectedTopic();
    if (form.elements.title) form.elements.title.value = "";
  });
  $$("[data-create-topic-index]").forEach(button => {
    const selected = Number(button.dataset.createTopicIndex) === Number(index);
    button.closest(".create-topic-option")?.classList.toggle("selected", selected);
    button.textContent = selected ? "✓ Đã chọn" : "Chọn";
  });

  // Run Pre-Flight check on selected topic
  const targetPid = form.elements.channel_profile_id?.value || state.selectedChannelProfileId;
  if (targetPid && item.title) {
    renderCreatePreflightSummary(targetPid, item.title, item.title);
  }
}

function isTopicInProfileMemory(item, profile) {
  if (!item || !profile) return false;
  if (item.raw?.already_produced === true) return true;
  const stripSeo = s => String(s || "")
    .replace(/\[중국\s*실화\s*사건\]|\[중국\s*첨단사기\s*실화\s*사건\]|\[중국\s*사기\s*실화\]|\[중국\s*인프라의\s*이면\]|\[하나님의\s*말씀\]|\[vụ\s*án\s*có\s*thật\s*ở\s*trung\s*quốc\]|\[vụ\s*lừa\s*đảo\s*có\s*thật\s*ở\s*trung\s*quốc\]/gi, "")
    .replace(/(?<=\d),(?=\d{3}(?!\d))/g, "")
    .trim()
    .toLowerCase();
  const candTitle = stripSeo(item.titleTarget || item.raw?.title_target || item.title || "");
  if (!candTitle) return false;
  const candZh = String(item.caseRealNameZh || item.raw?.case_real_name_zh || "").trim();
  const genericTokens = new Set([
    "수배범", "수배범이", "수배범의", "수배범을", "사건", "실화", "중국", "미제사건", "미제", "범인은", "진범", "용의자", "1급",
    "도주", "도주극", "도망친", "추적", "추격", "추격전", "프로파일링", "노후", "자금", "퇴직금", "퇴직금을", "평생", "모은", "사기", "사기극",
    "비자금", "거액", "횡령", "은행", "금고", "국채", "증권", "증권사", "살인", "연쇄", "형사", "공안", "단서", "지문", "위장", "신분", "잠적",
    "수송차", "현금수송차", "세탁한", "역추적", "증발한", "경찰서", "사법부를", "뒤흔든", "이름으로", "살아온", "숨어", "찾아낸", "드러난", "완벽한", "사라진",
    "유전자", "족보", "가계도", "지점장", "회장", "억대", "자산가", "부호", "최후", "두 얼굴", "정체", "이유", "사연", "전말", "미스터리",
    "베이징", "상하이", "광저우", "선전", "충칭", "청두", "우한", "항저우", "난징", "시안", "정저우", "창사", "선양", "하얼빈", "다롄", "칭다오", "원저우", "닝보", "쿤밍", "구이양",
    "생명을", "생명", "앗아간", "앗아가고", "앗아가며", "운명을", "목숨을", "사람의", "청춘의", "교도관", "교도관의", "수감자들", "경비원", "경비원의", "지명수배범",
    "vụ án có", "vụ lừa đảo có", "thật ở trung quốc", "trung quốc", "hồ sơ vụ án",
  ]);
  const genericHanzi = new Set([
    "中国", "特大", "案件", "真实", "侦破", "侦破纪实", "破案", "潜逃", "潜逃案", "挪用公款", "挪用", "非法集资", "集资诈骗",
    "通缉令", "通缉犯", "逃犯", "主犯", "嫌犯", "追捕", "围捕", "抓捕", "落网", "归案", "悬案", "积案", "命案", "重案", "运钞车", "金库",
    "北京", "上海", "广东", "深圳", "广州", "浙江", "杭州", "宁波", "温州", "江苏", "南京", "河南", "郑州", "湖南", "长沙", "湖北", "武汉",
    "四川", "成都", "重庆", "陕西", "西安", "山东", "辽宁", "沈阳", "大连", "黑龙江", "哈尔滨", "吉林", "云南", "昆明", "贵州", "贵阳", "福建", "江西", "安徽", "河北", "山西", "广西",
  ]);
  const memList = Array.isArray(profile.topic_memory) ? [...profile.topic_memory] : [];
  const winnerTitles = Array.isArray(profile?.own_channel?.dna?.winner_titles) ? profile.own_channel.dna.winner_titles : [];
  for (const wt of winnerTitles) {
    const wtStr = typeof wt === "object" ? wt?.title : wt;
    if (wtStr) memList.push({ title: String(wtStr), topic: String(wtStr), tags: [], anchors: [] });
  }
  const ownVideos = Array.isArray(profile?.own_channel?.videos) ? profile.own_channel.videos : [];
  for (const v of ownVideos) {
    if (v?.title) memList.push({ title: String(v.title), topic: String(v.title), tags: [], anchors: [] });
  }
  const backendVerifiedClean = (
    item.raw?.already_produced === false &&
    (item.raw?.trend_source === "live_two_stream_dna_research" || item.raw?.trend_source === "strict_channel_dna" || Boolean(item.raw?.case_real_name_zh))
  );
  for (const m of memList) {
    const mTitle = stripSeo(m?.title || "");
    const mTopic = stripSeo(m?.topic || "");
    if (!mTitle) continue;
    if (mTitle === candTitle || (candTitle.length >= 14 && mTitle.includes(candTitle)) || (mTitle.length >= 14 && candTitle.includes(mTitle))) {
      return true;
    }
    if (backendVerifiedClean) {
      // Backend already ran full trilingual case_similarity against topic_memory
      continue;
    }
    if (candZh) {
      const zhTokens = candZh.match(/[\u4e00-\u9fff]{2,8}/g) || [];
      for (const zt of zhTokens) {
        if (!genericHanzi.has(zt) && (`${m?.title || ""} ${m?.topic || ""}`).includes(zt)) {
          return true;
        }
      }
    }
    const rawAnchors = [...(Array.isArray(m?.tags) ? m.tags : []), ...(Array.isArray(m?.anchors) ? m.anchors : [])];
    const uniqueAnchors = new Set(
      rawAnchors
        .map(a => String(a || "").replace(/(?<=\d),(?=\d{3}(?!\d))/g, "").trim().toLowerCase())
        .filter(Boolean)
    );
    let specificHits = 0;
    for (const aNorm of uniqueAnchors) {
      if (
        aNorm.length >= 3 &&
        !genericTokens.has(aNorm) &&
        !aNorm.startsWith("place_") &&
        !aNorm.startsWith("person_") &&
        !aNorm.startsWith("org_") &&
        !/^\d+[\.,]?\d*\s*(년간|년|일|개월|시간|km|미터|억|조|만|%|năm|tỷ)?$/i.test(aNorm) &&
        !aNorm.includes("vụ án") &&
        !aNorm.includes("vụ lừa đảo") &&
        candTitle.includes(aNorm) &&
        (mTitle.includes(aNorm) || mTopic.includes(aNorm))
      ) {
        specificHits += 1;
      }
    }
    if (specificHits >= 3) return true;
  }
  return false;
}

function openTopicDossierPopup(index) {
  const item = state.createTopicSuggestions?.[index];
  if (!item) return;
  const raw = item.raw || {};
  const targetTitle = item.titleTarget || raw.title_target || item.title || "";
  const viTitle = item.titleVi || raw.title_vi || "";
  const realZh = String(item.caseRealNameZh || raw.case_real_name_zh || "").trim();
  const streamKey = classifyClientTopicStream(item);
  const streamLabel = streamKey === "financial_crime"
    ? "💰 Luồng 1 · Đại Án Tài Chính, Kho Bạc, Mở Két & Cướp Tiền Đào Tẩu"
    : "🚨 Luồng 2 · Trọng Án Hình Sự, Án Lạnh Pháp Y & Truy Nã Cấp A";
  const voxVerbs = Array.isArray(item.recommendedVoxVerbs) && item.recommendedVoxVerbs.length
    ? item.recommendedVoxVerbs
    : (Array.isArray(raw.recommended_vox_verbs) ? raw.recommended_vox_verbs : []);
  const archivalKws = Array.isArray(item.archivalSearchKeywordsZh) && item.archivalSearchKeywordsZh.length
    ? item.archivalSearchKeywordsZh
    : (Array.isArray(raw.archival_search_keywords_zh) ? raw.archival_search_keywords_zh : []);
  const hookText = raw.opening_hook || item.openingHook || "AI sẽ tự động thiết kế Hook mở màn 00:00–00:30 theo mâu thuẫn cốt lõi của vụ án.";
  const rawCaseNote = String(item.caseNote || raw.note || raw.production_brief || raw.summary_vi || item.note || "").trim();
  let classificationTag = "";
  let cleanCaseStory = rawCaseNote.replace(/^📋\s*/, "").trim();
  const bracketMatch = cleanCaseStory.match(/^【([^】]+)】\s*(.*)$/s);
  if (bracketMatch) {
    classificationTag = bracketMatch[1].trim();
    cleanCaseStory = bracketMatch[2].trim();
  }
  const codexAngle = String(raw.codex_angle || "").trim();
  const winnerCluster = String(item.winnerCluster || raw.winner_cluster || "").trim();
  const accentColor = streamKey === "financial_crime" ? "#f59e0b" : "#ef4444";
  const accentBg = streamKey === "financial_crime" ? "rgba(245,158,11,0.14)" : "rgba(239,68,68,0.14)";
  const accentBorder = streamKey === "financial_crime" ? "rgba(245,158,11,0.38)" : "rgba(239,68,68,0.38)";

  const html = `
    <div style="display:flex;flex-direction:column;gap:14px;">
      <div class="inspector-dossier-card" style="padding:15px 18px;">
        <h4>📌 Tiêu đề Gốc &amp; Bản dịch Tiếng Việt Đầy đủ</h4>
        <div style="font-size:16px;font-weight:800;color:#f8fafc;line-height:1.48;">${escapeHtml(targetTitle)}</div>
        ${viTitle ? `<div style="font-size:14px;font-weight:600;color:#93c5fd;margin-top:8px;padding:8px 12px;background:rgba(15,23,42,0.75);border-left:3px solid #38bdf8;border-radius:6px;line-height:1.48;">🇻🇳 ${escapeHtml(viTitle)}</div>` : ""}
        <div style="display:flex;flex-wrap:wrap;gap:8px;margin-top:11px;font-size:12px;">
          <span class="dna-compact-pill cyan">${escapeHtml(streamLabel)}</span>
          ${realZh ? `<span class="dna-compact-pill emerald">📂 Hồ sơ gốc: ${escapeHtml(realZh)}</span>` : ""}
          ${item.codexScore != null ? `<span class="dna-compact-pill">Điểm khớp DNA: ${Number(item.codexScore).toFixed(0)}/100</span>` : ""}
        </div>
      </div>

      <div class="inspector-dossier-card" style="padding:15px 18px;border-color:${accentBorder};">
        <h4>📋 Giải thích Chi tiết Hồ sơ Vụ án &amp; Tội danh</h4>
        ${classificationTag ? `<div style="margin-bottom:10px;padding:8px 12px;border-radius:8px;background:${accentBg};border-left:4px solid ${accentColor};color:#fef2f2;font-size:13px;font-weight:700;line-height:1.48;">🚨 ${escapeHtml(classificationTag)}</div>` : ""}
        <p style="margin:0;font-size:13.8px;line-height:1.68;color:#f1f5f9;">${escapeHtml(cleanCaseStory || "Hồ sơ vụ án thật có đầy đủ tình tiết điều tra, mốc năm và chứng cứ số liệu để triển khai.")}</p>
        ${(winnerCluster || codexAngle) ? `
          <div style="margin-top:12px;padding-top:10px;border-top:1px solid rgba(148,163,184,0.16);display:flex;flex-direction:column;gap:5px;font-size:12.4px;color:#cbd5e1;">
            ${winnerCluster ? `<div><strong style="color:#7dd3fc;">🏆 Cụm DNA thắng thế:</strong> ${escapeHtml(winnerCluster)}</div>` : ""}
            ${codexAngle ? `<div><strong style="color:#34d399;">🎯 Góc khai thác:</strong> ${escapeHtml(codexAngle)}</div>` : ""}
          </div>
        ` : ""}
      </div>

      <div class="inspector-dossier-grid">
        <div class="inspector-dossier-card">
          <h4>⚡ Hook mở màn (00:00 – 00:30)</h4>
          <p style="margin:0;font-size:13.2px;line-height:1.62;color:#e2e8f0;">${escapeHtml(hookText)}</p>
        </div>
        <div class="inspector-dossier-card">
          <h4>🎬 Động từ Thị giác Vox &amp; Từ khóa Tư liệu Gốc</h4>
          ${voxVerbs.length ? `<div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:9px;">${voxVerbs.map(v => `<span class="dna-compact-pill cyan">🎬 ${escapeHtml(v)}</span>`).join("")}</div>` : ""}
          ${archivalKws.length ? `<div style="font-size:12.3px;line-height:1.55;color:#cbd5e1;"><strong style="color:#93c5fd;">🔍 Từ khóa CCTV / Công an:</strong><br/>${archivalKws.map(k => `<code style="display:inline-block;margin:3px 4px 0 0;padding:2px 7px;border-radius:5px;background:rgba(15,23,42,0.85);border:1px solid rgba(148,163,184,0.2);color:#e2e8f0;">${escapeHtml(k)}</code>`).join("")}</div>` : `<p style="margin:0;font-size:12.6px;color:#94a3b8;">Tự động truy xuất tư liệu đài truyền hình trung ương &amp; hồ sơ tòa án theo tên vụ án gốc.</p>`}
        </div>
      </div>

      <div style="display:flex;justify-content:flex-end;gap:8px;padding-top:4px;">
        <button type="button" class="primary compact" id="popupConfirmSelectTopicBtn">✓ Chọn đề tài này để sản xuất</button>
      </div>
    </div>
  `;
  openStudioInspectorModal({
    badge: streamKey === "financial_crime" ? "💰" : "🚨",
    title: `CHI TIẾT HỒ SƠ VỤ ÁN #${String(index + 1).padStart(2, "0")}`,
    subtitle: realZh ? `Hồ sơ xác thực: ${realZh}` : streamLabel,
    html,
    rawText: `${targetTitle}\n${viTitle}\n${realZh}\n${classificationTag}\n${cleanCaseStory}\nHook: ${hookText}`,
    onOpen: modalBody => {
      modalBody.querySelector("#popupConfirmSelectTopicBtn")?.addEventListener("click", () => {
        selectCreateTopic(item, index);
        closeStudioDialogById("studioInspectorDialog");
        toast(`Đã chọn đề tài #${String(index + 1).padStart(2, "0")} để sản xuất.`);
      });
    },
  });
}

function renderSingleCreateTopicCard(item, globalIndex, { activeProfile = null, isDnaStrict = true, isTwoStream = false } = {}) {
  const raw = item.raw || {};
  const targetTitle = item.titleTarget || raw.title_target || item.title;
  const viTitle = item.titleVi || raw.title_vi || "";
  const seoDna = item.seoKeywordDna || raw.seo_keyword_dna || activeProfile?.seo_keyword_dna || null;
  const primaryKw = seoDna?.primary_title_keyword || "";
  const streamKey = classifyClientTopicStream(item);
  const streamBadgeHtml = streamKey === "financial_crime"
    ? `<span class="badge" style="background:rgba(245,158,11,0.16);color:#fbbf24;border:1px solid rgba(245,158,11,0.35);font-size:10.5px;padding:2px 7px;border-radius:6px;font-weight:700;">💰 Đại án Tài chính</span>`
    : `<span class="badge" style="background:rgba(239,68,68,0.16);color:#f87171;border:1px solid rgba(239,68,68,0.35);font-size:10.5px;padding:2px 7px;border-radius:6px;font-weight:700;">🚨 Trọng án Cấp A</span>`;
  const originStr = String(item.researchOrigin || raw.research_origin || "");
  const researchOriginHtml = originStr === "live_ai_web_research"
    ? `<span class="badge" style="background:rgba(16,185,129,0.14);color:#34d399;border:1px solid rgba(16,185,129,0.3);font-size:10.5px;padding:2px 7px;border-radius:6px;font-weight:700;">🌐 Mới</span>`
    : (raw.case_real_name_zh
        ? `<span class="badge" style="background:rgba(56,189,248,0.12);color:#7dd3fc;border:1px solid rgba(56,189,248,0.28);font-size:10.5px;padding:2px 7px;border-radius:6px;font-weight:700;">✓ Xác thực</span>`
        : "");
  const seoDnaBadgeHtml = primaryKw
    ? `<span class="badge" style="background:rgba(234,179,8,0.13);color:#facc15;border:1px solid rgba(234,179,8,0.28);font-size:10.5px;padding:2px 7px;border-radius:6px;font-weight:700;">🔑 [${escapeHtml(primaryKw)}]</span>`
    : "";
  const scoreBadgeHtml = item.codexScore != null
    ? `<span class="badge" style="background:rgba(148,163,184,0.14);color:#cbd5e1;border:1px solid rgba(148,163,184,0.26);font-size:10.5px;padding:2px 7px;border-radius:6px;font-weight:700;">DNA ${Number(item.codexScore).toFixed(0)}/100</span>`
    : (!isDnaStrict && item.vph != null ? `<span class="badge" style="background:rgba(148,163,184,0.14);color:#cbd5e1;font-size:10.5px;padding:2px 7px;border-radius:6px;">${Math.round(Number(item.vph)).toLocaleString("vi-VN")} VPH</span>` : "");

  return `<article class="create-topic-option">
    <div class="topic-card-header-bar">
      <div class="topic-card-badges">
        <span class="create-topic-option-rank">#${String(globalIndex + 1).padStart(2, "0")}</span>
        ${streamBadgeHtml}
        ${researchOriginHtml}
        ${seoDnaBadgeHtml}
        ${scoreBadgeHtml}
      </div>
      <div class="topic-card-btn-col">
        <button class="ghost compact" type="button" data-inspect-topic-index="${globalIndex}" title="Mở Popup xem giải thích chi tiết vụ án, tội danh &amp; Hook mở màn">📖 Giải thích vụ án</button>
        <button class="primary compact" type="button" data-create-topic-index="${globalIndex}">Chọn</button>
      </div>
    </div>
    <div class="create-topic-option-body">
      <div class="topic-title-dual">
        <div class="topic-title-target">${escapeHtml(targetTitle)}</div>
        ${viTitle ? `<div class="topic-title-vi">🇻🇳 ${escapeHtml(viTitle)}</div>` : ""}
      </div>
    </div>
  </article>`;
}

function renderCreateTopicSuggestions(result) {
  const root = $("#createTopicSuggestions");
  const status = $("#createTopicDiscoveryStatus");
  const streamBar = $("#createTopicStreamBar");
  const researchMetaEl = $("#createTopicResearchMeta");
  if (!root) return;
  const form = $("#jobForm");
  const activeProfileId = String(form?.elements?.channel_profile_id?.value || state.selectedChannelProfileId || "").trim();
  if (result?.profile_id && activeProfileId && String(result.profile_id) !== activeProfileId) {
    // Discard stale topic suggestions from a previously selected profile
    return;
  }
  const activeProfile = state.channelProfiles.find(item => item.id === (result?.profile_id || activeProfileId)) || null;
  const profileName = activeProfile?.label || result?.profile_id || "Hồ sơ đang chọn";
  const rawItems = Array.isArray(result?.today) ? [...result.today] : [];
  const isDnaStrict = result?.discovery_mode === "dna_strict" || result?.source_mode === "custom_dna_only" || state.createDiscoveryMode === "dna_strict";
  const lockedSingle = String(result?.locked_single_stream || activeProfile?.locked_single_stream || "").trim().toLowerCase();
  const isTwoStream = !lockedSingle && (Boolean(result?.is_two_stream_profile) || isTwoStreamTrueCrimeProfile(activeProfile));
  const isStreamManaged = Boolean(lockedSingle) || isTwoStream;

  if (streamBar) {
    streamBar.classList.toggle("hidden", !(isDnaStrict && isTwoStream));
  }
  const chosenStream = lockedSingle || (isTwoStream ? (state.selectedTopicStream || "all") : "all");
  $$("#createTopicStreamBar [data-topic-stream]").forEach(pill => {
    pill.classList.toggle("active", pill.dataset.topicStream === chosenStream);
  });

  const seenBatchKeys = new Set();
  const normalized = rawItems
    .map(item => normalizeTopic(item, {
      market: result?.market || activeProfile?.market || "KR",
      scanId: result?.scan_id || null,
      profileId: result?.profile_id || activeProfileId || null,
      targetDurationMinutes: result?.target_duration_minutes || activeProfile?.default_duration_minutes || null,
    }))
    .filter(item => {
      if (isTopicInProfileMemory(item, activeProfile)) return false;
      const tNorm = String(item.titleTarget || item.title || "").trim().toLowerCase();
      const zhNorm = String(item.caseRealNameZh || item.raw?.case_real_name_zh || "").trim().toLowerCase();
      const pipeTail = tNorm.includes("|") ? tNorm.split("|").pop().trim() : "";
      if (!tNorm) return false;
      if (seenBatchKeys.has(tNorm) || (zhNorm && seenBatchKeys.has(`zh:${zhNorm}`)) || (pipeTail.length >= 5 && seenBatchKeys.has(`pipe:${pipeTail}`))) {
        return false;
      }
      seenBatchKeys.add(tNorm);
      if (zhNorm) seenBatchKeys.add(`zh:${zhNorm}`);
      if (pipeTail.length >= 5) seenBatchKeys.add(`pipe:${pipeTail}`);
      return true;
    });

  const streamFiltered = (isStreamManaged && chosenStream !== "all")
    ? normalized.filter(item => classifyClientTopicStream(item) === chosenStream)
    : normalized;

  state.createTopicSuggestions = streamFiltered;
  if (result?.history_cycle_reset && activeProfileId && state.sessionSuggestedTopicKeys[activeProfileId]) {
    state.sessionSuggestedTopicKeys[activeProfileId] = new Set();
  }
  const producedCount = Array.isArray(activeProfile?.topic_memory) ? activeProfile.topic_memory.length : 0;
  const histCount = Number(result?.suggested_history_count ?? activeProfile?.suggested_topic_history?.length ?? 0);
  const vaultInfo = result?.dna_vault_status || activeProfile?.latest_today?.dna_vault_status || null;
  const replenishedCount = Number(vaultInfo?.replenished_total ?? Math.max(producedCount * 2, 52));
  const availableUnproduced = Number(vaultInfo?.available_unproduced_total ?? 0);
  if (researchMetaEl && isStreamManaged) {
    const finCount = streamFiltered.filter(x => classifyClientTopicStream(x) === "financial_crime").length;
    const vioCount = streamFiltered.filter(x => classifyClientTopicStream(x) === "major_violent_crime").length;
    const vaultBadge = availableUnproduced > 0
      ? ` · <span style="color:#34d399;font-weight:700;" title="Mỗi khi làm xong 1 video lưu vào bộ nhớ, hệ thống tự động bù >=2 vụ án thật mới vào kho DNA">🔄 Đã bù +${replenishedCount} vụ án mới (Kho sẵn: ${availableUnproduced} vụ án)</span>`
      : ` · <span style="color:#34d399;font-weight:700;">🔄 Đã bù +${replenishedCount} vụ án mới cho ${producedCount} bài đã làm</span>`;
    researchMetaEl.innerHTML = `<span>🛡️ Chống lặp: <b>${producedCount}</b> bài đã làm${vaultBadge} · <b>${histCount}</b> chủ đề đã gợi ý</span><span>· Hiển thị: <b>💰 ${finCount}</b> Tài chính / <b>🚨 ${vioCount}</b> Trọng án</span>`;
  }

  if (!state.createTopicSuggestions.length) {
    root.classList.remove("two-stream-grid");
    root.innerHTML = `<div class="empty-state">Chưa có đề tài phù hợp cho luồng đang chọn của "${escapeHtml(profileName)}". Bấm <b>"🔍 Research đề tài mới theo DNA"</b> để tìm hồ sơ vụ án thật mới.</div>`;
    if (status) status.textContent = "Chưa có đề tài phù hợp cho bộ lọc hiện tại — bấm Research để tìm hồ sơ mới.";
    return;
  }

  const displayed = state.createTopicSuggestions.slice(0, 14);
  if (isDnaStrict && isTwoStream && chosenStream === "all") {
    root.classList.add("two-stream-grid");
    const finEntries = [];
    const vioEntries = [];
    displayed.forEach((item, idx) => {
      if (classifyClientTopicStream(item) === "financial_crime") finEntries.push({ item, idx });
      else vioEntries.push({ item, idx });
    });
    const finColHtml = `
      <div class="topic-stream-column stream-col-fin">
        <div class="topic-stream-column-head">
          <div>
            <h5>💰 LUỒNG 1 · TỘI PHẠM TÀI CHÍNH &amp; ĐẠI ÁN KINH TẾ</h5>
            <small>Ngân hàng · Công trái · Két sắt kho bạc · Tẩy trắng thân phận đào tẩu 10–25 năm</small>
          </div>
          <span class="badge" style="background:rgba(245,158,11,0.18);color:#fbbf24;font-size:11px;padding:2px 8px;border-radius:10px;font-weight:700;">${finEntries.length} hồ sơ</span>
        </div>
        ${finEntries.length
          ? finEntries.map(({ item, idx }) => renderSingleCreateTopicCard(item, idx, { activeProfile, isDnaStrict, isTwoStream })).join("")
          : `<div class="empty-state" style="padding:12px;">Bấm "🔍 Research đề tài mới theo DNA" để nạp thêm đại án tài chính mới.</div>`}
      </div>`;
    const vioColHtml = `
      <div class="topic-stream-column stream-col-vio">
        <div class="topic-stream-column-head">
          <div>
            <h5>🚨 LUỒNG 2 · VỤ ÁN ĐẶC BIỆT NGUY HIỂM &amp; TRUY NÃ CẤP A</h5>
            <small>Hung thủ IQ cao xóa dấu vết · Kẻ thủ ác hai mặt 10–30 năm · Pháp y ADN &amp; Thẩm vấn</small>
          </div>
          <span class="badge" style="background:rgba(239,68,68,0.18);color:#f87171;font-size:11px;padding:2px 8px;border-radius:10px;font-weight:700;">${vioEntries.length} hồ sơ</span>
        </div>
        ${vioEntries.length
          ? vioEntries.map(({ item, idx }) => renderSingleCreateTopicCard(item, idx, { activeProfile, isDnaStrict, isTwoStream })).join("")
          : `<div class="empty-state" style="padding:12px;">Bấm "🔍 Research đề tài mới theo DNA" để nạp thêm trọng án đặc biệt nguy hiểm mới.</div>`}
      </div>`;
    root.innerHTML = finColHtml + vioColHtml;
  } else {
    root.classList.remove("two-stream-grid");
    root.innerHTML = displayed
      .map((item, index) => renderSingleCreateTopicCard(item, index, { activeProfile, isDnaStrict, isTwoStream }))
      .join("");
  }

  $$("[data-create-topic-index]").forEach(button => button.addEventListener("click", () => {
    const index = Number(button.dataset.createTopicIndex);
    selectCreateTopic(state.createTopicSuggestions[index], index);
  }));
  $$("[data-inspect-topic-index]").forEach(button => button.addEventListener("click", () => {
    const index = Number(button.dataset.inspectTopicIndex);
    openTopicDossierPopup(index);
  }));
  if (status) {
    if (isDnaStrict) {
      const streamTag = !isTwoStream
        ? "Chuẩn DNA Kênh"
        : (chosenStream === "financial_crime"
            ? "💰 Luồng 1: Tội phạm Tài chính"
            : chosenStream === "major_violent_crime"
              ? "🚨 Luồng 2: Vụ án Đặc biệt Nguy hiểm"
              : "⚖️ Cân bằng 2 Luồng Tài chính + Đặc biệt Nguy hiểm");
      const webCount = Number(result?.web_leads_count || 0);
      const webNote = webCount > 0 ? ` · Đã quét ${webCount} nguồn tư liệu gốc mới` : "";
      status.textContent = `🔒 [${profileName}] · ${streamTag} · ${state.createTopicSuggestions.length} hồ sơ vụ án thật chưa từng sản xuất${webNote} (100% Xanh tiền YouTube). Đã chọn sẵn #01.`;
    } else {
      const engine = result?.decision_engine === "codex_plus_radar" ? "Codex + Radar" : "Radar fallback";
      status.textContent = `📡 Luồng Radar 48h (${engine}) [${profileName}] · Còn ${state.createTopicSuggestions.length} chủ đề sau khi đối chiếu kênh mình + đối thủ + tín hiệu ${Number(result?.hours || 48)}h.`;
    }
  }
  selectCreateTopic(state.createTopicSuggestions[0], 0);
}

async function discoverCreateTopics({ forceRefresh = false, topicStream = null, resetHistory = false } = {}) {
  const form = $("#jobForm");
  const button = $("#discoverCreateTopicsBtn");
  const status = $("#createTopicDiscoveryStatus");
  const profileId = String(form?.elements?.channel_profile_id?.value || "").trim();
  if (!profileId) throw new Error("Hãy chọn hồ sơ kênh trước để nạp quy chuẩn DNA và đề xuất đề tài.");
  const customCreateDur = Number($("#createCustomDurationInput")?.value || 0);
  const targetDurationMinutes = (Number.isFinite(customCreateDur) && customCreateDur >= 2)
    ? Math.min(180, customCreateDur)
    : Number(form.elements.target_duration_minutes?.value || 30);
  const profile = state.channelProfiles.find(item => item.id === profileId);
  const discoveryMode = state.createDiscoveryMode || (isCustomDnaProfile(profile) ? "dna_strict" : "radar_trend");
  const activeStream = topicStream || state.selectedTopicStream || "all";

  if (!state.sessionSuggestedTopicKeys[profileId] || resetHistory) {
    state.sessionSuggestedTopicKeys[profileId] = new Set();
  }
  const currentBatchExcludes = [];
  if (forceRefresh && !resetHistory && Array.isArray(state.createTopicSuggestions)) {
    for (const prev of state.createTopicSuggestions) {
      const t = String(prev?.title || "").trim();
      const zh = String(prev?.caseRealNameZh || prev?.raw?.case_real_name_zh || "").trim();
      if (t) currentBatchExcludes.push(t);
      if (zh) currentBatchExcludes.push(zh);
    }
  }
  const excludeTitles = forceRefresh ? currentBatchExcludes.slice(0, 24) : [];

  if (button) {
    button.disabled = true;
    button.textContent = discoveryMode === "dna_strict"
      ? (forceRefresh ? "🔍 Đang research hồ sơ vụ án thật mới…" : "Đang nạp hồ sơ DNA…")
      : "Đang quét Radar 48h…";
  }
  if (status) {
    status.textContent = discoveryMode === "dna_strict"
      ? (forceRefresh
          ? `🔍 Đang truy vết kho hồ sơ thật (CCTV/법원/天网/今日说法) & AI đối chiếu chống lặp cho "${profile?.label || profileId}"…`
          : `Đang nạp danh sách hồ sơ chuẩn DNA 2 Luồng của "${profile?.label || profileId}"…`)
      : "Radar đang cập nhật dữ liệu kênh/đối thủ 48h, sau đó Codex phân tích và xếp hạng chủ đề…";
  }
  try {
    const query = new URLSearchParams({
      target_duration_minutes: String(targetDurationMinutes),
      discovery_mode: discoveryMode,
      force_refresh: forceRefresh ? "true" : "false",
      topic_stream: activeStream,
      reset_history: resetHistory ? "true" : "false",
    });
    const result = await api(`/api/radar/channel-profiles/${encodeURIComponent(profileId)}/today?${query.toString()}`, {
      method: "POST",
      body: JSON.stringify({
        exclude_titles: excludeTitles,
        topic_stream: activeStream,
        reset_history: resetHistory,
      }),
    });
    renderCreateTopicSuggestions(result);
    return result;
  } finally {
    if (button) {
      button.disabled = false;
      button.textContent = discoveryMode === "dna_strict" ? "🔍 Research đề tài mới theo DNA" : "📡 Quét lại Radar 48h";
    }
  }
}

$("#marketScanForm").addEventListener("submit", async event => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(event.currentTarget).entries());
  data.days = Number(data.days || 90);
  data.max_videos = 120;
  data.max_channel_subscribers = Number(data.max_channel_subscribers || 100000);
  data.max_channel_age_days = Number(data.max_channel_age_days || 90);
  data.min_proof_channels = Number(data.min_proof_channels || 3);
  data.min_breakout_videos = Number(data.min_breakout_videos || 4);
  data.niche_granularity = String(data.niche_granularity || "micro");
  if (data.niche_granularity === "micro") {
    data.days = Math.max(90, data.days);
    data.min_proof_channels = Math.max(3, data.min_proof_channels);
    data.min_breakout_videos = Math.max(4, data.min_breakout_videos);
  }
  data.content_type = "factual_documentary";
  data.seeds = String(data.seeds || "").split(",").map(x => x.trim()).filter(Boolean);
  try {
    closeStudioDialogById("marketScanDialog");
    $("#radarResultHint").textContent = `Đang tìm micro-niche bền · ${data.days} ngày · ≥${data.min_proof_channels} kênh nhỏ · ≥${data.min_breakout_videos} video nổ…`;
    $("#radarResults").innerHTML = `<div class="feed-empty feed-empty-rich"><b>Đang quét lượt mới</b><span>Đã ẩn kết quả cũ để không nhầm bộ lọc của scan trước với cấu hình đang chạy.</span></div>`;
    const result = await api("/api/radar/scans/market", { method: "POST", body: JSON.stringify(data) });
    const scanId = result.id || result.scan_id;
    if (!scanId) throw new Error("Radar không trả về mã lượt quét");
    await fetchMarketFeed(scanId);
    toast(`Đã quét xong lượt #${scanId}`);
  } catch (err) { toast(err.message, true); }
});

function competitorInputRow(value = "") {
  return `<div class="competitor-input-row"><input name="competitor_ref" value="${escapeHtml(value)}" placeholder="Dán kênh đối thủ cùng niche (tùy chọn)" /><button class="icon-btn remove-competitor" type="button" title="Bỏ kênh">×</button></div>`;
}

function bindCompetitorRemoveButtons() {
  $$("#competitorInputs .remove-competitor").forEach(button => button.addEventListener("click", () => {
    const rows = $$("#competitorInputs .competitor-input-row");
    if (rows.length <= 1) {
      const input = button.closest(".competitor-input-row")?.querySelector("input");
      if (input) input.value = "";
      return;
    }
    button.closest(".competitor-input-row")?.remove();
  }));
}

function setCompetitorInputs(refs = []) {
  const root = $("#competitorInputs");
  const values = Array.isArray(refs) && refs.length ? refs : [""];
  root.innerHTML = values.map(competitorInputRow).join("");
  bindCompetitorRemoveButtons();
}

function currentChannelProfile() {
  return state.channelProfiles.find(profile => profile.id === state.selectedChannelProfileId) || null;
}

function channelProfileMode(profile) {
  if (isCustomDnaProfile(profile)) return "custom_dna_only";
  return profile?.source_mode || profile?.latest_analysis?.source_mode || "hybrid";
}

function channelProfileModeText(profile) {
  const mode = channelProfileMode(profile);
  if (mode === "custom_dna_only") return "🔒 DNA Cố Định · 100% Full AI · Xanh Tiền";
  if (mode === "competitor_only") return "Kênh mới · học từ kênh mẫu";
  if (mode === "own_only") return "Ưu tiên DNA kênh mình";
  return "Kết hợp kênh mình + kênh mẫu";
}

function updateChannelProfileFormMode(profile) {
  const label = $("#saveChannelProfileLabel");
  const refresh = $("#refreshChannelProfileBtn");
  const cloneBtn = $("#cloneChannelProfileBtn");
  const form = $("#channelProfileForm");
  const dnaMode = String(form?.elements?.dna_mode?.value || (profile ? getProfileDnaFields(profile).dnaMode : "custom_dna_only"));
  const compDetails = $("#competitorDetailsBox");
  const todayBtn = $("#profileTodayBtn");
  if (label) label.textContent = profile ? "💾 Cập nhật Hồ sơ hiện tại" : "＋ Tạo Hồ sơ Kênh mới";
  if (refresh) refresh.disabled = !profile;
  if (cloneBtn) cloneBtn.disabled = !profile;
  if (todayBtn) {
    todayBtn.textContent = dnaMode === "custom_dna_only"
      ? "⚡ Đề xuất đề tài theo DNA Kênh cố định"
      : "📡 Gợi ý video mới hôm nay · trend 48h";
  }
  if (compDetails) {
    const hasComp = Boolean((profile?.competitor_refs || []).length);
    compDetails.open = dnaMode !== "custom_dna_only" || hasComp;
  }
}

$("#profileDnaModeSelect")?.addEventListener("change", () => {
  updateChannelProfileFormMode(currentChannelProfile());
});

$("#presetTrueCrimeCnBtn")?.addEventListener("click", () => {
  const form = $("#channelProfileForm");
  if (!form) return;
  // Disconnect from currently selected profile to prevent silent accidental overwrite
  state.selectedChannelProfileId = null;
  const profileSelect = $("#channelProfileSelect");
  if (profileSelect) profileSelect.value = "";
  fillChannelProfileForm(TRUE_CRIME_CN_KR_PRESET);
  updateChannelProfileFormMode(null);
  const saveLabel = $("#saveChannelProfileLabel");
  if (saveLabel) saveLabel.textContent = "＋ Tạo Hồ sơ từ Preset";
  openDnaStudioModal("identity");
  toast("Đã nạp preset True Crime TQ (KR · 30p) ở chế độ Tạo mới độc lập. Bấm 'Tạo Hồ sơ mới' để lưu thành profile riêng mà không ghi đè hồ sơ cũ!");
});

function renderChannelProfileCards() {
  const root = $("#channelProfileCards");
  const count = $("#channelProfileCount");
  if (!root) return;
  if (count) count.textContent = `${state.channelProfiles.length} hồ sơ`;
  if (!state.channelProfiles.length) {
    root.innerHTML = `<div class="profile-library-empty">Chưa có hồ sơ nào. Tạo hồ sơ ở box phía trên, card sẽ xuất hiện tại đây.</div>`;
    return;
  }
  root.innerHTML = state.channelProfiles.map(profile => {
    const own = profile.own_channel || {};
    const ownRef = String(profile.own_channel_ref || own.ref || "").trim();
    const competitors = (profile.competitors || []).filter(item => !item?.error);
    const isCustom = isCustomDnaProfile(profile);
    const dur = Number(profile.default_duration_minutes || 20);
    const market = String(profile.market || "KR").toUpperCase();
    const source = own.channel_id
      ? `🔗 Đã gắn kênh: ${own.title || own.label || ownRef} (${compactNumber(own.subscribers)} sub)`
      : ownRef
        ? `🔗 Kênh: ${ownRef}`
        : isCustom
          ? `🔗 Chưa gắn link kênh (Chạy độc lập theo DNA cố định)`
          : `Chưa có kênh mình · ${competitors.length} kênh mẫu`;
    const engineText = isCustom
      ? `Chuẩn ${market} · ${dur} Phút · 100% Full AI · Xanh tiền 100%`
      : (profile.latest_today?.decision_engine === "codex_plus_radar" ? "Lượt gần nhất: Codex + Radar" : "Chế độ Radar");
    const title = profile.label || own.label || profile.id;
    return `<article class="channel-profile-card-item ${profile.id === state.selectedChannelProfileId ? "active" : ""}">
      <button type="button" class="channel-profile-card-open" data-channel-profile-card="${escapeHtml(profile.id)}" aria-label="Mở hồ sơ ${escapeHtml(title)}">
        <strong>${escapeHtml(title)}</strong>
        <span>${escapeHtml(source)}</span>
        <span>${escapeHtml(channelProfileModeText(profile))}</span>
        <span class="profile-card-engine">${escapeHtml(engineText)}</span>
      </button>
      <div class="profile-card-actions">
        <button type="button" class="primary compact" data-action="produce-with-profile" data-profile-id="${escapeHtml(profile.id)}">Sản xuất (Bước 2) →</button>
        <button type="button" class="ghost compact" data-action="edit-channel-profile" data-profile-id="${escapeHtml(profile.id)}">Sửa DNA / Gắn kênh</button>
        <button type="button" class="ghost compact profile-card-delete" data-action="delete-channel-profile" data-profile-id="${escapeHtml(profile.id)}">Xóa</button>
      </div>
    </article>`;
  }).join("");
  $$('[data-channel-profile-card]').forEach(card => card.addEventListener("click", async () => {
    try {
      await selectChannelProfile(String(card.dataset.channelProfileCard || ""));
      openChannelProfileDialog(currentChannelProfile());
    } catch (err) { toast(err.message, true); }
  }));
  $$('[data-action="produce-with-profile"]').forEach(button => button.addEventListener("click", async () => {
    const profileId = String(button.dataset.profileId || "");
    if (!profileId) return;
    await selectChannelProfile(profileId);
    const createSelect = $("#createChannelProfileSelect");
    if (createSelect) {
      createSelect.value = profileId;
      createSelect.dispatchEvent(new Event("change"));
    }
    setAppTab("create");
  }));
  $$('[data-action="edit-channel-profile"]').forEach(button => button.addEventListener("click", async () => {
    const profileId = String(button.dataset.profileId || "");
    if (!profileId) return;
    try {
      closeChannelProfileDialog();
      await selectChannelProfile(profileId);
      openDnaStudioModal("identity");
      const form = $("#channelProfileForm");
      form?.elements?.own_channel_ref?.focus();
      toast("Đang mở Xưởng Cấu hình DNA Kênh (Popup 5 tầng).");
    } catch (err) { toast(err.message, true); }
  }));
  $$('[data-action="delete-channel-profile"]').forEach(button => button.addEventListener("click", async () => {
    const profileId = String(button.dataset.profileId || "");
    const profile = state.channelProfiles.find(item => item.id === profileId);
    if (!profileId || !profile) return;
    const title = profile.label || profile.own_channel?.label || profile.id;
    if (!window.confirm(`Xóa hồ sơ “${title}”? Dữ liệu profile và kế hoạch 30 ngày gắn trong profile này sẽ bị xóa.`)) return;
    try {
      button.disabled = true;
      await api(`/api/radar/channel-profiles/${encodeURIComponent(profileId)}`, { method: "DELETE" });
      if (state.selectedChannelProfileId === profileId) state.selectedChannelProfileId = null;
      closeChannelProfileDialog();
      await loadChannelProfiles({ selectId: null });
      toast(`Đã xóa hồ sơ ${title}.`);
    } catch (err) {
      button.disabled = false;
      toast(err.message, true);
    }
  }));
}

async function renderTopicMemoryList(profileId) {
  const container = $("#topicMemoryList");
  const badge = $("#topicMemoryCountBadge");
  if (!container || !profileId) return;

  try {
    const res = await api(`/api/radar/channel-profiles/${encodeURIComponent(profileId)}/topic-memory`);
    const items = Array.isArray(res?.items) ? res.items : (Array.isArray(res?.topic_memory) ? res.topic_memory : []);
    if (badge) badge.textContent = `${items.length} đề tài`;
    if (!items.length) {
      container.innerHTML = `<div style="font-size:12px;color:#94a3b8;font-style:italic;">Chưa có đề tài nào trong bộ nhớ. AI sẽ tự động lưu khi tạo dự án hoặc bạn có thể thêm thủ công bên dưới.</div>`;
      return;
    }
    container.innerHTML = items.map(item => `
      <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px;padding:6px 8px;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);border-radius:4px;">
        <div style="flex:1;min-width:0;">
          <div style="font-size:12px;font-weight:600;color:#f1f5f9;line-height:1.3;">${escapeHtml(item.title || item.topic || "")}</div>
          ${item.tags && item.tags.length ? `<div style="display:flex;flex-wrap:wrap;gap:4px;margin-top:3px;">${item.tags.slice(0, 5).map(t => `<span style="font-size:10px;padding:1px 5px;background:rgba(56,189,248,0.1);color:#7dd3fc;border-radius:3px;">${escapeHtml(t)}</span>`).join("")}</div>` : ""}
        </div>
        <button type="button" class="icon-btn delete-topic-memory-btn" data-profile-id="${escapeHtml(profileId)}" data-entry-id="${escapeHtml(item.id)}" title="Xóa đề tài khỏi bộ nhớ" style="color:#ef4444;font-size:14px;padding:0 4px;cursor:pointer;">×</button>
      </div>
    `).join("");

    container.querySelectorAll(".delete-topic-memory-btn").forEach(btn => {
      btn.addEventListener("click", async () => {
        const pId = btn.dataset.profileId;
        const eId = btn.dataset.entryId;
        try {
          await api(`/api/radar/channel-profiles/${encodeURIComponent(pId)}/topic-memory/${encodeURIComponent(eId)}`, { method: "DELETE" });
          toast("Đã xóa đề tài khỏi bộ nhớ");
          renderTopicMemoryList(pId);
        } catch (err) {
          toast(err.message || "Không xóa được đề tài", true);
        }
      });
    });
  } catch (err) {
    container.innerHTML = `<div style="font-size:12px;color:#ef4444;">Không tải được bộ nhớ: ${escapeHtml(err.message || String(err))}</div>`;
  }
}

function openChannelProfileDialog(profile) {
  const dialog = $("#channelProfileDialog");
  const title = $("#channelProfileDialogTitle");
  if (!dialog || !profile) return;
  if (title) title.textContent = profile.label || profile.own_channel?.label || "Chi tiết hồ sơ";
  renderTopicMemoryList(profile.id);
  if (typeof dialog.showModal === "function") {
    if (!dialog.open) dialog.showModal();
  } else dialog.setAttribute("open", "");
}

function closeChannelProfileDialog() {
  const dialog = $("#channelProfileDialog");
  if (!dialog) return;
  if (typeof dialog.close === "function" && dialog.open) dialog.close();
  else dialog.removeAttribute("open");
}

function channelProfileActivitySteps(operation) {
  if (operation === "plan") return [
    ["refresh_profile", "DNA Kênh"],
    ["radar_plan", "Ứng viên đề tài"],
    ["codex_strategy", "Chiến lược DNA"],
    ["codex_review", "Codex · review 30 ngày"],
  ];
  return [
    ["refresh_profile", "Khóa DNA Kênh"],
    ["radar_scan", "Lọc đề tài"],
    ["codex_strategy", "Kiểm duyệt Xanh tiền"],
    ["codex_ranking", "Codex · xếp hạng"],
  ];
}

function renderChannelProfileActivity(activity) {
  const root = $("#channelProfileActivity");
  if (!root) return;
  if (!activity || activity.status === "idle") {
    root.classList.add("hidden");
    root.innerHTML = "";
    return;
  }
  const steps = channelProfileActivitySteps(activity.operation);
  const currentIndex = steps.findIndex(([stage]) => stage === activity.stage);
  const allDone = activity.status === "done";
  const chipText = activity.status === "error"
    ? "LỖI"
    : allDone
      ? "HOÀN TẤT"
      : String(activity.engine || "dna").toUpperCase();
  const chipClass = activity.status === "error" ? "error" : allDone ? "done" : activity.engine === "codex" ? "codex" : "";
  root.innerHTML = `<div class="channel-profile-activity-head"><strong>${activity.operation === "plan" ? "Tiến trình kế hoạch 30 ngày" : "Tiến trình đề xuất đề tài"}</strong><span class="profile-engine-chip ${chipClass}">${escapeHtml(chipText)}</span></div>
    <p>${escapeHtml(activity.message || "Đang xử lý…")}</p>
    <div class="channel-profile-activity-subtitle"><small>Radar = dữ liệu/tín hiệu · Codex = phân tích kênh</small></div>
    <div class="profile-activity-steps">${steps.map(([stage, label], index) => {
      const className = allDone || (currentIndex >= 0 && index < currentIndex) ? "done" : currentIndex === index ? "active" : "";
      return `<span class="profile-activity-step ${className}">${escapeHtml(label)}</span>`;
    }).join("")}</div>`;
  root.classList.remove("hidden");
}

async function refreshChannelProfileActivity(profileId) {
  if (!profileId) return renderChannelProfileActivity(null);
  const activity = await api(`/api/radar/channel-profiles/${encodeURIComponent(profileId)}/activity`);
  if (state.selectedChannelProfileId === profileId) renderChannelProfileActivity(activity);
  return activity;
}

async function runWithChannelProfileActivity(profileId, operation, requestFactory) {
  renderChannelProfileActivity({
    operation,
    stage: "refresh_profile",
    status: "running",
    engine: "codex",
    message: operation === "plan" ? "Đang dựng kế hoạch 30 ngày theo DNA Kênh…" : "Đang lọc đề tài chuẩn theo DNA Kênh…",
  });
  const poll = () => refreshChannelProfileActivity(profileId).catch(() => null);
  const timer = window.setInterval(poll, 800);
  try {
    const result = await requestFactory();
    await poll();
    return result;
  } catch (err) {
    await poll();
    throw err;
  } finally {
    window.clearInterval(timer);
  }
}

function setChannelProfileActionsBusy(busy) {
  const today = $("#profileTodayBtn");
  const plan = $("#profilePlanBtn");
  if (today) today.disabled = busy;
  if (plan) plan.disabled = busy;
}

function channelProfileWorkingText(profile, action = "save", competitorCount = 0) {
  if (isCustomDnaProfile(profile)) {
    return action === "today"
      ? "Đang lọc đề tài thuần theo Bộ lọc Chỉ chọn / Cấm tuyệt đối của DNA Kênh (Không qua Radar)…"
      : action === "plan"
        ? "Đang lập kế hoạch 30 ngày theo DNA Kênh cố định…"
        : "Đang lưu Quy chuẩn DNA Kênh cố định…";
  }
  const hasOwn = Boolean(String(profile?.own_channel_ref || profile?.own_channel?.ref || "").trim());
  const mode = profile ? channelProfileMode(profile) : (hasOwn ? (competitorCount ? "hybrid" : "own_only") : "competitor_only");
  if (mode === "competitor_only") return action === "today"
    ? "Radar đang quét trend 48 giờ từ kênh mẫu · Codex sẽ phân tích tệp người xem và chọn chủ đề…"
    : action === "plan"
      ? "Radar đang dựng candidate 30 ngày · Codex sẽ phân tích kênh mẫu và sắp kế hoạch…"
      : `Đang đọc ${competitorCount || profile?.competitor_refs?.length || 1} kênh mẫu…`;
  if (mode === "own_only") return action === "today"
    ? "Radar đang quét trend 48 giờ · Codex đang đối chiếu với DNA và tệp người xem của kênh…"
    : action === "plan"
      ? "Radar đang dựng candidate · Codex đang phân tích DNA kênh để sắp kế hoạch 30 ngày…"
      : "Đang đọc DNA kênh mình…";
  return action === "today"
    ? "Radar đang quét trend 48 giờ · Codex đang phân tích kênh mình + đối thủ + tệp người xem…"
    : action === "plan"
      ? "Radar đang dựng candidate · Codex đang so kênh mình + đối thủ để sắp kế hoạch 30 ngày…"
      : `Đang đọc DNA kênh mình và ${competitorCount || profile?.competitor_refs?.length || 0} kênh mẫu…`;
}

function renderChannelPlan(plan) {
  const root = $("#channelPlanPreview");
  if (!root) return;
  if (!plan || !Array.isArray(plan.items) || !plan.items.length) {
    root.classList.add("hidden");
    root.innerHTML = "";
    return;
  }
  root.classList.remove("hidden");
  const items = plan.items.slice(0, 10);
  root.innerHTML = `
    <div style="padding:10px 12px;border-radius:9px;background:rgba(15,28,46,0.85);border:1px solid rgba(56,189,248,0.25);">
      <div style="font-size:12px;font-weight:800;color:#7dd3fc;margin-bottom:6px;">📅 KẾ HOẠCH 30 NGÀY (#${escapeHtml(plan.plan_id || "")}) · Đã hoàn thành ${Number(plan.completed || 0)}/${Number(plan.total || items.length)}</div>
      <div style="display:flex;flex-direction:column;gap:5px;max-height:180px;overflow-y:auto;">
        ${items.map((it, idx) => `<div style="font-size:12px;color:#e2e8f0;padding:4px 8px;border-radius:6px;background:rgba(8,16,28,0.75);"><b>#${String(idx + 1).padStart(2, "0")}</b> ${escapeHtml(it.title || it.topic || "")}</div>`).join("")}
      </div>
    </div>
  `;
}

function renderChannelProfileSummary(profile) {
  const root = $("#channelProfileSummary");
  const actions = $("#channelProfileActions");
  if (!profile) {
    root.classList.add("hidden");
    root.innerHTML = "";
    actions.classList.add("hidden");
    $("#channelPlanPreview").classList.add("hidden");
    return;
  }
  const own = profile.own_channel || {};
  const ownRef = String(profile.own_channel_ref || own.ref || "").trim();
  const dna = getProfileDnaFields(profile);
  const analysis = profile.latest_analysis || {};
  const ownAnalysis = analysis.own || {};
  const competitors = Array.isArray(profile.competitors) ? profile.competitors : [];
  const validCompetitors = competitors.filter(item => !item.error);
  const hasOwn = Boolean(own.channel_id);
  const modeText = channelProfileModeText(profile);
  const ownCard = hasOwn
    ? `<div class="channel-profile-stat"><b>${escapeHtml(own.label || own.title || "Kênh mình")}</b><span>${compactNumber(own.subscribers)} sub · ${compactNumber(own.total_views)} views</span></div>
       <div class="channel-profile-stat"><b>${Number(ownAnalysis.win_rate || 0).toFixed(2)}</b><span>tỷ lệ video thắng · momentum ${Number(ownAnalysis.momentum || 0).toFixed(0)}</span></div>`
    : `<div class="channel-profile-stat"><b>${ownRef ? escapeHtml(ownRef) : "Chưa gắn link kênh YouTube"}</b><span>${ownRef ? "Đã lưu liên kết kênh vào hồ sơ" : "Có thể thêm link kênh bất cứ lúc nào ở Bước 1 hoặc Bước 2"}</span></div>
       <div class="channel-profile-stat"><b>${escapeHtml(modeText)}</b><span>Độc lập hoàn toàn với Radar đối thủ</span></div>`;

  const vSig = profile.voice_signature || {};
  const rDna = profile.rhythm_dna || {};
  const vCad = rDna.vocal_cadence || {};
  const eCad = rDna.editing_cadence || {};
  const voiceSummarySps = Array.isArray(vCad.target_sps_range)
    ? `${vCad.target_sps_range[0]}–${vCad.target_sps_range[vCad.target_sps_range.length - 1]}`
    : "4.0–5.0";
  const voiceSummaryNote = (vSig.voice_name || profile.voice_id || eCad.editor_feel_title_vi)
    ? `<div class="channel-profile-note"><b>🎙️ MÀU GIỌNG 1-OF-1 &amp; CẢM NHẬN NHỊP KÊNH:</b> <code>${escapeHtml(vSig.voice_name || profile.voice_id || "Đang chờ khóa")}</code>${vSig.base_voice_name ? ` (gốc sạch: ${escapeHtml(vSig.base_voice_name)})` : ""} · Nhịp đọc <b>${escapeHtml(voiceSummarySps)} âm tiết/s</b> · Nhịp dựng Editor: <b>${escapeHtml(eCad.editor_feel_title_vi || "Đồng bộ theo hơi thở & khoảng lặng giọng kể")}</b></div>`
    : "";

  root.innerHTML = `<div class="channel-profile-summary-grid">
    ${ownCard}
    <div class="channel-profile-stat"><b>${Number(profile.default_duration_minutes || 20)} phút · ${escapeHtml(profile.market || "KR")}</b><span>Chiến lược: ${escapeHtml(dna.visualStrategy.toUpperCase())}</span></div>
  </div>
  ${voiceSummaryNote}
  ${dna.voiceAndStructure ? `<div class="channel-profile-note"><b>Thị trường &amp; Giọng kể:</b> ${escapeHtml(dna.voiceAndStructure)}</div>` : ""}
  ${dna.referenceImagePolicy ? `<div class="channel-profile-note"><b>Chiến lược Hình ảnh:</b> ${escapeHtml(dna.referenceImagePolicy)}</div>` : ""}
  <div class="channel-profile-note"><b>✂️ ROLE EDIT (LUẬT SẮT DỰNG &amp; FOOTAGE):</b> Footage lấy từ <b>3–6s/cut</b> (beat dài ghép 2 đoạn 3–6s Part A+B, <code>max_uses=1</code>) · <b>Bắt buộc xóa/crop sạch 100% logo và text Trung của bên khác</b> (cần thiết thì crop hết hình ảnh có nguồn bên khác) · <b>Không lấy video dẫn chương trình có mặt người dẫn (MC) hoặc chủ kênh khác</b>, chỉ lấy đúng footage cần thiết · <b>Mỗi cảnh Vox độc nhất 100%</b> theo từng câu voice (cấm khung chung lặp lại chỉ thay chữ).</div>
  ${dna.allowedTopics ? `<div class="channel-profile-note"><b>✅ CHỈ CHỌN:</b> ${escapeHtml(dna.allowedTopics)}</div>` : ""}
  ${dna.forbiddenTopics ? `<div class="channel-profile-note"><b>🚫 CẤM TUYỆT ĐỐI:</b> ${escapeHtml(dna.forbiddenTopics)}</div>` : ""}
  ${dna.monetizationSafetyPolicy ? `<div class="channel-profile-note"><b>💚 NGÔI KỂ &amp; GÓC KỂ XANH TIỀN:</b> ${escapeHtml(dna.monetizationSafetyPolicy)}</div>` : ""}
  ${dna.ctaStrategy ? `<div class="channel-profile-note"><b>🎯 ROLE CTA LINH HOẠT THEO CÂU CHUYỆN (KHÔNG BAO GIỜ LẶP LẠI CTA):</b> ${escapeHtml(dna.ctaStrategy)}</div>` : ""}
  ${!isCustomDnaProfile(profile) && validCompetitors.length ? `<div class="channel-profile-note"><b>Kênh mẫu tham khảo:</b> ${validCompetitors.length} kênh</div>` : ""}`;
  root.classList.remove("hidden");
  actions.classList.remove("hidden");
}

function defaultCleanMasterVoiceForMarket(market = "KR", lang = "ko") {
  const l = String(lang || "").trim().toLowerCase();
  const m = String(market || "").trim().toUpperCase();
  if (l.startsWith("ko") || m === "KR") return "09c70cc1-cc86-4905-b65b-3967209c3175"; // K1 clean master
  if (l.startsWith("vi") || m === "VN") return "262cf97e-c145-44ba-92a6-2dd36db1146e"; // PC Nam clean master
  if (l.startsWith("ja") || m === "JP") return "f0670e81-6361-4567-b93c-2685b98c9a4e"; // Nhat clean master
  if (l.startsWith("en") || m === "US") return "b4c2376b-3d63-461a-a849-367e37261e4a"; // Jon clean master
  return "09c70cc1-cc86-4905-b65b-3967209c3175";
}

function syncVoiceSourceModeUI() {
  const mode = String($("#channelVoiceSourceMode")?.value || "base_voice");
  const uploadRow = $("#channelVoiceSampleUploadRow");
  const baseField = $("#channelBaseMasterVoiceField");
  if (uploadRow) uploadRow.classList.toggle("hidden", mode !== "user_sample");
  if (baseField) baseField.style.opacity = mode === "user_sample" ? "0.45" : "1";
}

function renderProfileVoiceRhythmStudio(profile, rhythmOverride = null) {
  const badge = $("#channelVoiceSignatureBadge");
  const audioWrap = $("#channelVoiceSignatureAudioWrap");
  const audioEl = $("#channelVoiceSignatureAudio");
  const metaEl = $("#channelVoiceSignatureMeta");
  const cardsBox = $("#channelRhythmDnaCards");

  const sig = profile?.voice_signature || {};
  const voiceId = String(sig.voice_id || profile?.voice_id || profile?.default_voice_id || "").trim();
  const rhythm = rhythmOverride || profile?.rhythm_dna || null;
  const colorSpec = rhythm?.voice_color_spec || sig.voice_color_spec || {};

  if (badge) {
    if (voiceId) {
      const vName = sig.voice_name || `Voice ${voiceId.slice(0, 8)}`;
      badge.textContent = `🔒 Voice 1-of-1: ${vName}`;
      badge.classList.add("locked");
    } else {
      badge.textContent = "Chưa khóa màu giọng riêng (Sẽ tự tạo khi Lưu)";
      badge.classList.remove("locked");
    }
  }

  if (audioWrap && audioEl) {
    if (voiceId) {
      audioWrap.classList.remove("hidden");
      const nextSrc = `/api/voice/preview-audio/${encodeURIComponent(voiceId)}?v=${encodeURIComponent(sig.designed_at || "1")}`;
      if (audioEl.dataset.voiceSrc !== nextSrc) {
        audioEl.src = nextSrc;
        audioEl.dataset.voiceSrc = nextSrc;
      }
      if (metaEl) {
        metaEl.textContent = sig.voice_name
          ? `${sig.voice_name}${colorSpec.color_label_vi ? ` · ${colorSpec.color_label_vi}` : ""}`
          : `Giọng độc bản (${voiceId.slice(0, 8)})`;
      }
    } else {
      audioWrap.classList.add("hidden");
      audioEl.removeAttribute("src");
      audioEl.dataset.voiceSrc = "";
    }
  }

  if (!cardsBox) return;
  if (!rhythm || (!rhythm.writing_cadence && !rhythm.vocal_cadence && !rhythm.editing_cadence)) {
    cardsBox.innerHTML = `<div class="rhythm-dna-empty">Điền phong cách kênh rồi bấm <b>🧠 Phân Tích Thể Loại &amp; Nhịp 3 Tầng</b> (hoặc bấm Lưu hồ sơ để Chuyên gia tự động phân tích &amp; khóa màu giọng riêng từ mẫu sạch <b>K1</b>).</div>`;
    return;
  }

  const w = rhythm.writing_cadence || {};
  const v = rhythm.vocal_cadence || {};
  const e = rhythm.editing_cadence || {};
  const pauses = v.pause_tiers_sec || {};
  const spsRange = Array.isArray(v.target_sps_range)
    ? `${v.target_sps_range[0]}–${v.target_sps_range[v.target_sps_range.length - 1]}`
    : "4.0–5.0";
  const avgCharsText = Array.isArray(w.target_avg_sentence_chars)
    ? w.target_avg_sentence_chars.join("–")
    : String(w.target_avg_sentence_chars || "28–45");
  const punchRatioText = Array.isArray(w.short_punch_ratio_target)
    ? `${w.short_punch_ratio_target.map(x => Math.round(Number(x || 0) * 100)).join("–")}%`
    : `${Math.round(Number(w.short_punch_ratio_target || 0.22) * 100)}%`;
  const paraSpanText = Array.isArray(w.paragraph_sentence_span)
    ? `${w.paragraph_sentence_span.join("–")} câu`
    : String(w.paragraph_breath_sentences || "2–4 câu");
  const shotPacing = e.shot_pacing_sec || {};
  const urgentCutSec = Number(shotPacing.urgent_max_sec || shotPacing.urgent_action_max_cut_sec || 3.4).toFixed(1);
  const stdAvgSec = Number(shotPacing.standard_avg_sec || 4.8).toFixed(1);
  const holdThrSec = Number(e.dramatic_pause_hold_threshold_sec || e.hold_through_silence_threshold_sec || 1.15).toFixed(2);
  const dramaticPauseSec = Number(pauses.dramatic_landing || pauses.dramatic_turn || 1.45).toFixed(2);
  const curtainPauseSec = Number(pauses.act_curtain || pauses.cliffhanger_punch || 1.85).toFixed(2);
  const pitchSt = Number(colorSpec.pitch_semitones || 0);
  const pitchText = pitchSt === 0 ? "0.0st (Chuẩn gốc)" : `${pitchSt > 0 ? "+" : ""}${pitchSt.toFixed(2)}st`;

  cardsBox.innerHTML = `
    <div class="rhythm-dna-card script-layer">
      <div class="rhythm-dna-card-head">
        <span>🖋️ Tầng 1 · Nhịp Viết (@script)</span>
        <span class="rhythm-dna-pill">${escapeHtml(rhythm.archetype_label_vi || rhythm.archetype_id || "Custom DNA")}</span>
      </div>
      <div class="rhythm-dna-metrics">
        <span class="rhythm-dna-metric">Độ dài câu: <b>${escapeHtml(avgCharsText)} ký tự</b></span>
        <span class="rhythm-dna-metric">Câu phanh ngắn: <b>${escapeHtml(punchRatioText)}</b></span>
        <span class="rhythm-dna-metric">Đoạn thở: <b>${escapeHtml(paraSpanText)}</b></span>
      </div>
      <p class="rhythm-dna-desc">${escapeHtml(w.writer_rhythm_directive_vi || "Biến thiên độ dài câu có chủ đích để mở đường cho giọng đọc và điểm rơi cắt cảnh.")}</p>
    </div>

    <div class="rhythm-dna-card voice-layer">
      <div class="rhythm-dna-card-head">
        <span>🎙️ Tầng 2 · Màu Giọng &amp; Nhịp Đọc (@voice)</span>
        <span class="rhythm-dna-pill">${escapeHtml(spsRange)} âm tiết/s</span>
      </div>
      <div class="rhythm-dna-metrics">
        <span class="rhythm-dna-metric">Màu: <b>${escapeHtml(colorSpec.color_label_vi || "Điêu khắc từ K1")}</b></span>
        <span class="rhythm-dna-metric">Pitch: <b>${escapeHtml(pitchText)}</b></span>
        <span class="rhythm-dna-metric">Nghỉ điểm rơi/chương: <b>${dramaticPauseSec}s / ${curtainPauseSec}s</b></span>
      </div>
      <p class="rhythm-dna-desc">${escapeHtml(rhythm.specialist_summary_vi || v.vocal_rhythm_directive_vi || "Chia 7 tầng khoảng nghỉ cảm xúc bất đối xứng, dứt khoát không đọc đều đều máy móc.")}</p>
    </div>

    <div class="rhythm-dna-card edit-layer">
      <div class="rhythm-dna-card-head">
        <span>✂️ Tầng 3 · Cảm Nhận Nhịp Dựng (@edit)</span>
        <span class="rhythm-dna-pill">${escapeHtml(e.cut_style || "Dựng theo hơi thở")}</span>
      </div>
      <div class="rhythm-dna-metrics">
        <span class="rhythm-dna-metric">Cắt nhanh/chuẩn: <b>${urgentCutSec}s / ${stdAvgSec}s</b></span>
        <span class="rhythm-dna-metric">Neo lặng &ge; <b>${holdThrSec}s</b></span>
        <span class="rhythm-dna-metric">BGM dâng ở khoảng nghỉ: <b>+${Number(e.bgm_silence_swell_db || 2.2).toFixed(1)}dB</b></span>
      </div>
      <p class="rhythm-dna-desc">${escapeHtml(e.editor_rhythm_directive_vi || "Editor cắt dồn khi cao trào và bắt buộc giữ khung hình thở trọn qua các khoảng lặng cảm xúc, cấm cắt giữa khoảng nghỉ.")}</p>
    </div>
  `;
}

function readFileAsDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(new Error("Không đọc được file mẫu giọng."));
    reader.readAsDataURL(file);
  });
}

function collectDraftProfileForVoiceAnalysis() {
  const form = $("#channelProfileForm");
  if (!form) return {};
  const market = String(form.elements.market?.value || "KR").toUpperCase();
  const lang = String(form.elements.default_language?.value || form.elements.language?.value || "ko").trim();
  const customProfDur = Number($("#profileCustomDurationInput")?.value || 0);
  const duration = (Number.isFinite(customProfDur) && customProfDur >= 2)
    ? Math.min(180, customProfDur)
    : Number(form.elements.default_duration_minutes?.value || 20);
  return {
    id: state.selectedChannelProfileId || "draft-profile",
    label: String(form.elements.label?.value || "Hồ sơ Kênh Mới").trim(),
    market,
    default_language: lang,
    default_duration_minutes: duration,
    default_visual_strategy: String(form.elements.default_visual_strategy?.value || "full_ai").trim(),
    voice_and_structure: String(form.elements.voice_and_structure?.value || "").trim(),
    allowed_topics: String(form.elements.allowed_topics?.value || "").trim(),
    monetization_safety_policy: String(form.elements.monetization_safety_policy?.value || "").trim(),
    default_creative_brief: {
      narrative_angle: String(form.elements.narrative_angle?.value || "").trim(),
      writing_style: String(form.elements.writing_style?.value || "").trim(),
      hook_archetype: String(form.elements.hook_archetype?.value || "").trim(),
      notes: String(form.elements.notes?.value || "").trim(),
    },
    custom_direction: String($("#channelVoiceCustomDirection")?.value || "").trim(),
  };
}

function resetChannelProfileForm() {
  const form = $("#channelProfileForm");
  if (!form) return;
  form.reset();
  if (form.elements.label) form.elements.label.value = "";
  if (form.elements.market) form.elements.market.value = "KR";
  if (form.elements.default_language) form.elements.default_language.value = "ko";
  if (form.elements.language) form.elements.language.value = "ko";
  if (form.elements.default_duration_minutes) setComboDurationValue(form.elements.default_duration_minutes, $("#profileCustomDurationInput"), 20, "");
  if (form.elements.target_duration_minutes) form.elements.target_duration_minutes.value = "20";
  if (form.elements.default_visual_strategy) form.elements.default_visual_strategy.value = "full_ai";
  if (form.elements.visual_strategy) form.elements.visual_strategy.value = "full_ai";
  if (form.elements.default_ai_media_mode) form.elements.default_ai_media_mode.value = "image";
  if (form.elements.ai_media_mode) form.elements.ai_media_mode.value = "image";
  if (form.elements.dna_mode) form.elements.dna_mode.value = "custom_dna_only";
  if (form.elements.own_channel_ref) form.elements.own_channel_ref.value = "";
  if (form.elements.voice_and_structure) form.elements.voice_and_structure.value = "";
  if (form.elements.reference_image_policy) form.elements.reference_image_policy.value = "";
  if (form.elements.allowed_topics) form.elements.allowed_topics.value = "";
  if (form.elements.forbidden_topics) form.elements.forbidden_topics.value = "";
  if (form.elements.monetization_safety_policy) form.elements.monetization_safety_policy.value = "";
  if (form.elements.cta_strategy) form.elements.cta_strategy.value = "";
  if (form.elements.narrative_angle) form.elements.narrative_angle.value = "";
  if (form.elements.writing_style) form.elements.writing_style.value = "";
  if (form.elements.hook_archetype) form.elements.hook_archetype.value = "";
  if (form.elements.editing_archetypes) form.elements.editing_archetypes.value = "";
  if (form.elements.opening_hook) form.elements.opening_hook.value = "";
  if (form.elements.notes) form.elements.notes.value = "";
  if (form.elements.editing_dna) form.elements.editing_dna.value = "";
  if ($("#channelProfileAiMediaMode")) $("#channelProfileAiMediaMode").value = "image";
  if ($("#channelProfileNarrativeAngle")) $("#channelProfileNarrativeAngle").value = "";
  if ($("#channelProfileWritingStyle")) $("#channelProfileWritingStyle").value = "";
  if ($("#channelProfileHookArchetype")) $("#channelProfileHookArchetype").value = "";
  if ($("#channelProfileEditingArchetypes")) $("#channelProfileEditingArchetypes").value = "";
  if ($("#channelProfileOpeningHook")) $("#channelProfileOpeningHook").value = "";
  if ($("#channelProfileNotes")) $("#channelProfileNotes").value = "";
  if ($("#channelProfileEditingDna")) $("#channelProfileEditingDna").value = "";
  if ($("#channelProfileEditingPreset")) $("#channelProfileEditingPreset").value = "true_crime_noir_ai";
  if ($("#channelProfileVisualMix")) $("#channelProfileVisualMix").value = "0% Footage · 80% AI · 20% Motion";
  if ($("#channelProfileColorGrade")) $("#channelProfileColorGrade").value = "dark_forensic_noir";
  if ($("#channelProfilePacingSec")) $("#channelProfilePacingSec").value = "6.0";
  if ($("#channelPrimaryTitleKeyword")) $("#channelPrimaryTitleKeyword").value = "";
  if ($("#channelPrimaryTitleKeywordMeaningVi")) $("#channelPrimaryTitleKeywordMeaningVi").value = "";
  if ($("#channelKeywordPlacementRule")) $("#channelKeywordPlacementRule").value = "smart_seo_flexible";
  if ($("#channelSecondaryAnchorKeywords")) $("#channelSecondaryAnchorKeywords").value = "";
  if ($("#channelMandatoryHashtags")) $("#channelMandatoryHashtags").value = "";
  if ($("#channelDefaultSeoTags")) $("#channelDefaultSeoTags").value = "";
  if ($("#channelThumbnailStylePreset")) $("#channelThumbnailStylePreset").value = "cold_forensic_noir";
  if ($("#channelThumbnailVisualSignature")) $("#channelThumbnailVisualSignature").value = "";
  if ($("#channelThumbnailArchetype")) $("#channelThumbnailArchetype").value = "broadcast_left_heavy";
  if ($("#channelThumbnailColorPrimary")) $("#channelThumbnailColorPrimary").value = "#FFE84A";
  if ($("#channelThumbnailColorAccent")) $("#channelThumbnailColorAccent").value = "#dc2626";
  if ($("#channelThumbnailColorBg")) $("#channelThumbnailColorBg").value = "#04070d";
  if ($("#channelThumbnailFontFamily")) $("#channelThumbnailFontFamily").value = "";
  if ($("#channelThumbnailMascotLock")) $("#channelThumbnailMascotLock").value = "false";
  if ($("#channelThumbnailRefCharPath")) $("#channelThumbnailRefCharPath").value = "";
  if ($("#channelAutoDesignVoiceToggle")) $("#channelAutoDesignVoiceToggle").checked = true;
  if ($("#channelVoiceSourceMode")) $("#channelVoiceSourceMode").value = "base_voice";
  if ($("#channelBaseMasterVoiceSelect")) $("#channelBaseMasterVoiceSelect").value = "09c70cc1-cc86-4905-b65b-3967209c3175";
  if ($("#channelVoiceCustomDirection")) $("#channelVoiceCustomDirection").value = "";
  if ($("#channelVoiceSampleFile")) $("#channelVoiceSampleFile").value = "";
  if ($("#channelVoiceSampleRefText")) $("#channelVoiceSampleRefText").value = "";
  syncVoiceSourceModeUI();
  renderProfileVoiceRhythmStudio(null);
  if ($("#profileTodayDuration")) setComboDurationValue($("#profileTodayDuration"), $("#profileTodayCustomDurationInput"), 20, "");
  setCompetitorInputs([]);
  renderChannelProfileSummary(null);
  updateChannelProfileFormMode(null);
}

function formatVisualMixSummary(mix) {
  if (!mix || typeof mix !== "object") return "40% Footage · 40% AI · 20% Motion";
  const f = Math.round(Number(mix.footage || 0) * (Number(mix.footage || 0) <= 1 ? 100 : 1));
  const a = Math.round(Number(mix.ai || 0) * (Number(mix.ai || 0) <= 1 ? 100 : 1));
  const m = Math.round(Number(mix.motion || 0) * (Number(mix.motion || 0) <= 1 ? 100 : 1));
  return `${f}% Footage · ${a}% AI · ${m}% Motion`;
}

function parseVisualMixSummary(str, fallbackVs = "full_ai") {
  const text = String(str || "");
  const nums = [...text.matchAll(/(\d+(?:\.\d+)?)\s*%/g)].map(m => Number(m[1]));
  if (nums.length >= 3) {
    const total = (nums[0] + nums[1] + nums[2]) || 100;
    return {
      footage: Number((nums[0] / total).toFixed(2)),
      ai: Number((nums[1] / total).toFixed(2)),
      motion: Number((nums[2] / total).toFixed(2)),
    };
  }
  if (fallbackVs === "full_ai") return { footage: 0.0, ai: 0.85, motion: 0.15 };
  if (fallbackVs === "evidence_footage") return { footage: 0.5, ai: 0.3, motion: 0.2 };
  return { footage: 0.45, ai: 0.35, motion: 0.2 };
}

function fillChannelProfileForm(profile) {
  const form = $("#channelProfileForm");
  if (!form) return;
  // Step 0 Strict Profile Switching: Completely reset ALL form fields with zero bleed
  resetChannelProfileForm();
  if (!profile) return;

  const dna = getProfileDnaFields(profile);
  const edDna = profile.editorial_dna || {};
  const brief = profile.default_creative_brief || edDna.default_creative_brief || {};
  const editingDna = profile.editing_dna || edDna.editing_dna || null;

  if (form.elements.label) form.elements.label.value = profile.label || "";
  if (form.elements.market) form.elements.market.value = profile.market || "KR";

  const lang = profile.default_language || profile.language || brief.language || dna.language || (profile.market === "US" ? "en" : profile.market === "JP" ? "ja" : profile.market === "VN" ? "vi" : "ko");
  if (form.elements.default_language) form.elements.default_language.value = lang;
  if (form.elements.language) form.elements.language.value = lang;

  const dur = String(profile.default_duration_minutes || profile.target_duration_minutes || brief.target_duration_minutes || 20);
  if (form.elements.default_duration_minutes) setComboDurationValue(form.elements.default_duration_minutes, $("#profileCustomDurationInput"), dur, "");
  if (form.elements.target_duration_minutes) form.elements.target_duration_minutes.value = dur;
  if ($("#profileTodayDuration")) setComboDurationValue($("#profileTodayDuration"), $("#profileTodayCustomDurationInput"), dur, "");

  const vs = profile.default_visual_strategy || profile.visual_strategy || brief.visual_strategy || dna.visualStrategy || "full_ai";
  if (form.elements.default_visual_strategy) form.elements.default_visual_strategy.value = vs;
  if (form.elements.visual_strategy) form.elements.visual_strategy.value = vs;

  const mm = profile.default_ai_media_mode || profile.ai_media_mode || brief.ai_media_mode || "image";
  if (form.elements.default_ai_media_mode) form.elements.default_ai_media_mode.value = mm;
  if (form.elements.ai_media_mode) form.elements.ai_media_mode.value = mm;
  if ($("#channelProfileAiMediaMode")) $("#channelProfileAiMediaMode").value = mm;

  if (form.elements.dna_mode) form.elements.dna_mode.value = dna.dnaMode || "custom_dna_only";
  if (form.elements.own_channel_ref) form.elements.own_channel_ref.value = profile.own_channel_ref || profile.own_channel?.ref || "";
  if (form.elements.voice_and_structure) form.elements.voice_and_structure.value = dna.voiceAndStructure || "";
  if (form.elements.reference_image_policy) form.elements.reference_image_policy.value = dna.referenceImagePolicy || "";
  if (form.elements.allowed_topics) form.elements.allowed_topics.value = dna.allowedTopics || "";
  if (form.elements.forbidden_topics) form.elements.forbidden_topics.value = dna.forbiddenTopics || "";
  if (form.elements.monetization_safety_policy) form.elements.monetization_safety_policy.value = dna.monetizationSafetyPolicy || "";
  if (form.elements.cta_strategy) form.elements.cta_strategy.value = dna.ctaStrategy || "";

  // Creative brief and editing DNA fields
  const parsedEdDna = typeof editingDna === "string"
    ? (() => { try { return JSON.parse(editingDna); } catch (_) { return {}; } })()
    : (editingDna || {});
  const angle = brief.narrative_angle || profile.narrative_angle || "";
  const style = brief.writing_style || profile.writing_style || "";
  const hook = brief.hook_archetype || profile.hook_archetype || "";
  const rawArch = brief.editing_archetypes || parsedEdDna.editing_archetypes || profile.editing_archetypes || "";
  const archetypes = Array.isArray(rawArch) ? rawArch.join(", ") : String(rawArch || "");
  const opening = brief.opening_hook || profile.opening_hook || "";
  const notes = brief.notes || profile.notes || "";
  const dnaJson = editingDna ? (typeof editingDna === "string" ? editingDna : JSON.stringify(editingDna)) : "";

  if (form.elements.narrative_angle) form.elements.narrative_angle.value = angle;
  if ($("#channelProfileNarrativeAngle")) $("#channelProfileNarrativeAngle").value = angle;
  if (form.elements.writing_style) form.elements.writing_style.value = style;
  if ($("#channelProfileWritingStyle")) $("#channelProfileWritingStyle").value = style;
  if (form.elements.hook_archetype) form.elements.hook_archetype.value = hook;
  if ($("#channelProfileHookArchetype")) $("#channelProfileHookArchetype").value = hook;
  if (form.elements.editing_archetypes) form.elements.editing_archetypes.value = archetypes;
  if ($("#channelProfileEditingArchetypes")) $("#channelProfileEditingArchetypes").value = archetypes;
  if (form.elements.opening_hook) form.elements.opening_hook.value = opening;
  if ($("#channelProfileOpeningHook")) $("#channelProfileOpeningHook").value = opening;
  if (form.elements.notes) form.elements.notes.value = notes;
  if ($("#channelProfileNotes")) $("#channelProfileNotes").value = notes;
  if (form.elements.editing_dna) form.elements.editing_dna.value = dnaJson;
  if ($("#channelProfileEditingDna")) $("#channelProfileEditingDna").value = dnaJson;

  // Populate visible Editing DNA Studio fields
  const rawCg = typeof parsedEdDna.color_grade === "object" && parsedEdDna.color_grade !== null
    ? (parsedEdDna.color_grade.tone_preset || parsedEdDna.color_grade.lut_name)
    : parsedEdDna.color_grade;
  const colorGrade = String(rawCg || (vs === "full_ai" ? "dark_forensic_noir" : (profile.market === "US" ? "warm_archival_sepia" : "technical_cool_cyan")));
  const rawPv = typeof parsedEdDna.pacing === "object" && parsedEdDna.pacing !== null
    ? (parsedEdDna.pacing.typical_pacing_sec || parsedEdDna.pacing.target_beat_duration_sec || parsedEdDna.pacing.average_beat_duration_sec)
    : (parsedEdDna.pacing || parsedEdDna.typical_pacing_sec);
  const pacingVal = Number(rawPv) || (vs === "full_ai" ? 6.5 : 5.5);
  if ($("#channelProfilePacingSec")) $("#channelProfilePacingSec").value = String(pacingVal);
  if ($("#channelProfileVisualMix")) $("#channelProfileVisualMix").value = formatVisualMixSummary(parsedEdDna.visual_mix);
  if ($("#channelProfileColorGrade")) $("#channelProfileColorGrade").value = colorGrade;
  if ($("#channelProfileEditingPreset")) {
    let detectedPreset = parsedEdDna.preset_id || "";
    if (!detectedPreset) {
      if (vs === "full_ai" || colorGrade.includes("noir")) detectedPreset = "true_crime_noir_ai";
      else if (profile.market === "US" || colorGrade.includes("sepia") || colorGrade.includes("archival")) detectedPreset = "archival_vault_us";
      else if (vs === "hybrid") detectedPreset = "infra_25d_dossier";
      else detectedPreset = "custom";
    }
    $("#channelProfileEditingPreset").value = detectedPreset;
  }

  // Populate SEO Keyword DNA fields
  const seoDna = profile.seo_keyword_dna || {};
  if ($("#channelPrimaryTitleKeyword")) $("#channelPrimaryTitleKeyword").value = seoDna.primary_title_keyword || "";
  if ($("#channelPrimaryTitleKeywordMeaningVi")) $("#channelPrimaryTitleKeywordMeaningVi").value = seoDna.primary_title_keyword_meaning_vi || "";
  if ($("#channelKeywordPlacementRule")) $("#channelKeywordPlacementRule").value = seoDna.keyword_placement_rule || "smart_seo_flexible";
  const secAnchors = Array.isArray(seoDna.secondary_anchor_keywords) ? seoDna.secondary_anchor_keywords.join(", ") : String(seoDna.secondary_anchor_keywords || "");
  if ($("#channelSecondaryAnchorKeywords")) $("#channelSecondaryAnchorKeywords").value = secAnchors;
  const mandHash = Array.isArray(seoDna.mandatory_hashtags) ? seoDna.mandatory_hashtags.join(", ") : String(seoDna.mandatory_hashtags || "");
  if ($("#channelMandatoryHashtags")) $("#channelMandatoryHashtags").value = mandHash;
  const defTags = Array.isArray(seoDna.default_seo_tags) ? seoDna.default_seo_tags.join(", ") : String(seoDna.default_seo_tags || "");
  if ($("#channelDefaultSeoTags")) $("#channelDefaultSeoTags").value = defTags;

  // Populate Thumbnail DNA fields
  const thumbDna = profile.thumbnail_dna || {};
  const tPalette = thumbDna.color_palette || {};
  const tTypo = thumbDna.typography_preset || {};
  const tLayout = thumbDna.layout_template || {};
  if ($("#channelThumbnailStylePreset")) $("#channelThumbnailStylePreset").value = thumbDna.style_preset || "cold_forensic_noir";
  if ($("#channelThumbnailVisualSignature")) $("#channelThumbnailVisualSignature").value = thumbDna.visual_signature || "";
  if ($("#channelThumbnailArchetype")) {
    const archVal = typeof tLayout === "object" ? (tLayout.archetype || "broadcast_left_heavy") : String(tLayout || "broadcast_left_heavy");
    $("#channelThumbnailArchetype").value = archVal;
  }
  if ($("#channelThumbnailColorPrimary")) $("#channelThumbnailColorPrimary").value = tPalette.primary || tPalette.accent_highlight || "#FFE84A";
  if ($("#channelThumbnailColorAccent")) $("#channelThumbnailColorAccent").value = tPalette.accent || tPalette.danger_badge || "#dc2626";
  if ($("#channelThumbnailColorBg")) $("#channelThumbnailColorBg").value = tPalette.background || tPalette.primary_bg || "#04070d";
  if ($("#channelThumbnailFontFamily")) $("#channelThumbnailFontFamily").value = tTypo.font_family || "";
  if ($("#channelThumbnailMascotLock")) $("#channelThumbnailMascotLock").value = thumbDna.mascot_lock ? "true" : "false";
  if ($("#channelThumbnailRefCharPath")) $("#channelThumbnailRefCharPath").value = thumbDna.reference_character_path || "";

  // Populate Voice & Rhythm Specialist Studio
  const voiceSig = profile.voice_signature || {};
  const hasLockedVoice = Boolean(profile.voice_id || voiceSig.voice_id);
  if ($("#channelAutoDesignVoiceToggle")) $("#channelAutoDesignVoiceToggle").checked = !hasLockedVoice;
  if ($("#channelVoiceSourceMode")) {
    $("#channelVoiceSourceMode").value = voiceSig.source_mode === "user_sample" ? "user_sample" : "base_voice";
  }
  if ($("#channelBaseMasterVoiceSelect")) {
    const preferredMaster = voiceSig.base_voice_id || defaultCleanMasterVoiceForMarket(profile.market, lang);
    if ([...$("#channelBaseMasterVoiceSelect").options].some(opt => opt.value === preferredMaster)) {
      $("#channelBaseMasterVoiceSelect").value = preferredMaster;
    } else {
      $("#channelBaseMasterVoiceSelect").value = defaultCleanMasterVoiceForMarket(profile.market, lang);
    }
  }
  if ($("#channelVoiceCustomDirection")) $("#channelVoiceCustomDirection").value = voiceSig.custom_direction || "";
  if ($("#channelVoiceSampleFile")) $("#channelVoiceSampleFile").value = "";
  if ($("#channelVoiceSampleRefText")) $("#channelVoiceSampleRefText").value = "";
  syncVoiceSourceModeUI();
  renderProfileVoiceRhythmStudio(profile);

  setCompetitorInputs(profile.competitor_refs || (profile.competitors || []).map(item => item.ref).filter(Boolean));
  renderChannelProfileSummary(profile);
  updateChannelProfileFormMode(profile);
}

function resetCreateFormDraftFields() {
  const form = $("#jobForm");
  if (!form) return;
  if (form.elements.market) form.elements.market.value = "KR";
  if (form.elements.language) form.elements.language.value = "ko";
  if (form.elements.target_duration_minutes) setComboDurationValue(form.elements.target_duration_minutes, $("#createCustomDurationInput"), 20, "Khoảng");
  if (form.elements.visual_strategy) form.elements.visual_strategy.value = "full_footage";
  const mmInputs = $$('#jobForm input[name="ai_media_mode"]');
  mmInputs.forEach(input => { input.checked = input.value === "mixed"; });
  if ($("#createAiStyleMode")) $("#createAiStyleMode").value = "auto";
  if ($("#createAiStylePreset")) $("#createAiStylePreset").value = "";
  if ($("#createAiCustomStyle")) $("#createAiCustomStyle").value = "";
  if ($("#createNarrativeAngle")) $("#createNarrativeAngle").value = "";
  if ($("#createWritingStyle")) $("#createWritingStyle").value = "";
  if ($("#createHookArchetype")) $("#createHookArchetype").value = "";
  if ($("#createEditingArchetypesInput")) $("#createEditingArchetypesInput").value = "";
  if ($("#createOpeningHookInput")) $("#createOpeningHookInput").value = "";
  if ($("#createNotesTextarea")) $("#createNotesTextarea").value = "";
  if (form.elements.notes) form.elements.notes.value = "";
  if ($("#createPlaybookSelect")) $("#createPlaybookSelect").value = "";
  if ($("#createEditingDnaInput")) $("#createEditingDnaInput").value = "";
  state.selectedProfileEditingDna = null;
  setCreateAttachedOutline(null);
  syncCreativeQuickChipsState();
  updateCreatePipelineFlow();
  updateCreateStyleFields();
}

async function applySelectedProfileToCreateStep(profile, { autoDiscover = true } = {}) {
  const form = $("#jobForm");
  // Step 00 Strict Profile Switching: Completely reset ALL form fields with zero bleed
  resetCreateFormDraftFields();
  renderCreateProfileDnaSummary(profile);
  if (!profile || !form) return;

  const dna = getProfileDnaFields(profile);
  const edDna = profile.editorial_dna || {};
  const brief = profile.default_creative_brief || edDna.default_creative_brief || {};
  const editingDna = profile.editing_dna || edDna.editing_dna || null;

  const market = String(profile.market || brief.market || "KR").toUpperCase();
  if (form.elements.market && ["KR", "JP", "US", "VN"].includes(market)) form.elements.market.value = market;

  const langMap = { KR: "ko", JP: "ja", US: "en", VN: "vi" };
  const lang = String(profile.default_language || profile.language || brief.language || edDna.default_language || langMap[market] || "ko");
  if (form.elements.language) form.elements.language.value = lang;

  const targetMinutes = Number(profile.default_duration_minutes || profile.target_duration_minutes || brief.target_duration_minutes || 20);
  if (form.elements.target_duration_minutes) setComboDurationValue(form.elements.target_duration_minutes, $("#createCustomDurationInput"), targetMinutes, "Khoảng");

  const vs = String(profile.default_visual_strategy || profile.visual_strategy || brief.visual_strategy || edDna.visual_strategy || "full_ai").trim().toLowerCase();
  if (form.elements.visual_strategy) {
    form.elements.visual_strategy.value = vs;
    updateCreatePipelineFlow();
  }

  const mm = String(profile.default_ai_media_mode || profile.ai_media_mode || brief.ai_media_mode || edDna.default_ai_media_mode || "image").trim().toLowerCase();
  const mmRadio = document.querySelector(`#jobForm input[name="ai_media_mode"][value="${mm}"]`);
  if (mmRadio) mmRadio.checked = true;

  const styleMode = profile.default_ai_style_mode || edDna.default_ai_style_mode;
  if (styleMode && $("#createAiStyleMode")) {
    $("#createAiStyleMode").value = String(styleMode);
  }
  const stylePreset = profile.default_ai_style_preset || edDna.default_ai_style_preset;
  if (stylePreset && $("#createAiStylePreset")) {
    const presetEl = $("#createAiStylePreset");
    if (![...presetEl.options].some(opt => opt.value === String(stylePreset))) {
      const opt = document.createElement("option");
      opt.value = String(stylePreset);
      opt.textContent = String(stylePreset);
      presetEl.appendChild(opt);
    }
    presetEl.value = String(stylePreset);
  }
  const customStyle = profile.default_ai_custom_style || edDna.default_ai_custom_style;
  if (customStyle && $("#createAiCustomStyle")) {
    $("#createAiCustomStyle").value = String(customStyle);
  }
  updateCreateStyleFields();

  // Populate Creative Brief fields strictly from profile
  if ($("#createNarrativeAngle")) {
    const rawAngle = brief.narrative_angle || profile.narrative_angle;
    $("#createNarrativeAngle").value = rawAngle ? humanizeCreativeKey("narrative_angles", rawAngle) : "";
  }
  if ($("#createWritingStyle")) {
    const rawStyle = brief.writing_style || profile.writing_style;
    $("#createWritingStyle").value = rawStyle ? humanizeCreativeKey("writing_styles", rawStyle) : "";
  }
  if ($("#createHookArchetype")) {
    const rawHook = brief.hook_archetype || profile.hook_archetype;
    $("#createHookArchetype").value = rawHook ? humanizeCreativeKey("hook_archetypes", rawHook) : "";
  }
  const archetypesRaw = brief.editing_archetypes || profile.editing_archetypes || brief.editing_grammar;
  if (archetypesRaw && (Array.isArray(archetypesRaw) ? archetypesRaw.length : String(archetypesRaw).trim())) {
    setCheckedEditingArchetypes(archetypesRaw, "#createEditingArchetypesInput");
  } else if ($("#createEditingArchetypesInput")) {
    $("#createEditingArchetypesInput").value = "";
  }
  if ($("#createOpeningHookInput")) {
    const opening = brief.opening_hook || profile.opening_hook;
    $("#createOpeningHookInput").value = opening != null ? String(opening).trim() : "";
  }
  const notesText = brief.notes || profile.notes || brief.custom_rules || "";
  if ($("#createNotesTextarea")) {
    $("#createNotesTextarea").value = notesText ? String(notesText).trim() : "";
  }
  if (form.elements.notes) {
    form.elements.notes.value = notesText ? String(notesText).trim() : "";
  }

  // Dedicated 1-of-1 Voice ID locked on profile
  const defaultVoiceId = String(profile.voice_id || profile.default_voice_id || profile.voice_signature?.voice_id || edDna.default_voice_id || "").trim();
  const voiceSelectEl = $("#voiceSelect");
  if (voiceSelectEl && defaultVoiceId) {
    if (![...voiceSelectEl.options].some(opt => opt.value === defaultVoiceId)) {
      try { await loadVoices(); } catch (_) {}
    }
    if (![...voiceSelectEl.options].some(opt => opt.value === defaultVoiceId)) {
      const opt = document.createElement("option");
      opt.value = defaultVoiceId;
      opt.textContent = `${profile.voice_signature?.voice_name || `Voice riêng (${defaultVoiceId.slice(0, 8)})`} · ${lang}`;
      voiceSelectEl.appendChild(opt);
    }
    voiceSelectEl.value = defaultVoiceId;
  }

  // Editing DNA
  if (editingDna) {
    state.selectedProfileEditingDna = editingDna;
    if ($("#createEditingDnaInput")) $("#createEditingDnaInput").value = JSON.stringify(editingDna);
  }

  syncCreativeQuickChipsState();

  const defaultStream = String(profile.default_topic_stream || profile.locked_single_stream || "").trim();
  if (defaultStream === "financial_crime" || defaultStream === "major_violent_crime") {
    state.selectedTopicStream = defaultStream;
  } else {
    state.selectedTopicStream = "all";
  }

  setCreateDiscoveryMode(dna.dnaMode === "custom_dna_only" ? "dna_strict" : "radar_trend", { triggerDiscover: false });
  if (profile) {
    const candidateTopic = String($("#createManualTitleInput")?.value || "").trim();
    renderCreatePreflightSummary(profile.id, candidateTopic, candidateTopic);
  }
  if (autoDiscover) {
    try { await discoverCreateTopics({ forceRefresh: false }); }
    catch (err) { toast(err.message, true); }
  }
}

async function loadChannelProfiles({ selectId = null, loadPlan = true } = {}) {
  const profiles = await api("/api/radar/channel-profiles");
  state.channelProfiles = Array.isArray(profiles) ? profiles : [];
  if (selectId) state.selectedChannelProfileId = selectId;
  if (state.selectedChannelProfileId && !state.channelProfiles.some(profile => profile.id === state.selectedChannelProfileId)) {
    state.selectedChannelProfileId = null;
  }
  // Auto-select the Fixed DNA profile (Director V2 True Crime 2-Stream first) by default if none selected
  if (!state.selectedChannelProfileId && state.channelProfiles.length) {
    const preferred = state.channelProfiles.find(item => item.id === "channel-kr-truecrime-director-v2")
      || state.channelProfiles.find(item => item.id === "channel-e544a64b7c")
      || state.channelProfiles.find(item => isCustomDnaProfile(item))
      || state.channelProfiles[0];
    if (preferred) state.selectedChannelProfileId = preferred.id;
  }
  const select = $("#channelProfileSelect");
  if (select) {
    select.innerHTML = `<option value="">Chọn hồ sơ…</option>${state.channelProfiles.map(profile => `<option value="${escapeHtml(profile.id)}">${escapeHtml(profile.label || profile.own_channel?.label || profile.id)}</option>`).join("")}`;
    select.value = state.selectedChannelProfileId || "";
  }
  const createSelect = $("#createChannelProfileSelect");
  if (createSelect) {
    const previous = createSelect.value;
    createSelect.innerHTML = `<option value="">Chọn hồ sơ kênh để nạp DNA &amp; quy chuẩn sản xuất</option>${state.channelProfiles.map(profile => `<option value="${escapeHtml(profile.id)}">${escapeHtml(profile.label || profile.own_channel?.label || profile.id)}</option>`).join("")}`;
    const originProfileId = state.selectedChannelPlan?.profileId || state.selectedRadar?.profileId || previous || state.selectedChannelProfileId;
    createSelect.value = state.channelProfiles.some(profile => profile.id === originProfileId) ? originProfileId : "";
    const activeCreateProfile = state.channelProfiles.find(item => item.id === createSelect.value) || null;
    await applySelectedProfileToCreateStep(activeCreateProfile, { autoDiscover: Boolean(activeCreateProfile && !state.createTopicSuggestions?.length) });
  }
  renderChannelProfileCards();
  const profile = currentChannelProfile();
  fillChannelProfileForm(profile);
  if (profile?.plan?.plan_id) {
    if (loadPlan) {
      try { renderChannelPlan(await api(`/api/radar/channel-profiles/${encodeURIComponent(profile.id)}/plan`)); }
      catch (_) { renderChannelPlan(null); }
    }
  } else renderChannelPlan(null);
  if (profile) {
    try { await refreshChannelProfileActivity(profile.id); } catch (_) { renderChannelProfileActivity(null); }
    try { await renderSelfLearningReportForProfile(profile.id); } catch (_) { renderSelfLearningReport(null); }
  } else {
    renderChannelProfileActivity(null);
    renderSelfLearningReport(null);
  }
}

async function selectChannelProfile(profileId) {
  state.selectedChannelProfileId = profileId || null;
  const select = $("#channelProfileSelect");
  if (select) select.value = state.selectedChannelProfileId || "";
  renderChannelProfileCards();
  const profile = currentChannelProfile();
  fillChannelProfileForm(profile);
  if (profile?.plan?.plan_id) {
    try { renderChannelPlan(await api(`/api/radar/channel-profiles/${encodeURIComponent(profile.id)}/plan`)); }
    catch (err) { renderChannelPlan(null); toast(err.message, true); }
  } else renderChannelPlan(null);
  if (profile) {
    try { await refreshChannelProfileActivity(profile.id); } catch (_) { renderChannelProfileActivity(null); }
    try { await renderSelfLearningReportForProfile(profile.id); } catch (_) { renderSelfLearningReport(null); }
  } else {
    renderChannelProfileActivity(null);
    renderSelfLearningReport(null);
  }
}

$("#runSelfLearningBtn")?.addEventListener("click", async () => {
  const profileId = state.selectedChannelProfileId;
  if (!profileId) {
    return toast("Vui lòng chọn một hồ sơ kênh để chạy phân tích Self-Learning.", true);
  }
  const btn = $("#runSelfLearningBtn");
  const oldText = btn ? btn.textContent : "";
  if (btn) {
    btn.disabled = true;
    btn.textContent = "⏳ Đang phân tích…";
  }
  try {
    const res = await api(`/api/radar/channel-profiles/${encodeURIComponent(profileId)}/self-learning/run`, {
      method: "POST",
    });
    renderSelfLearningReport(res);
    toast("✓ Đã hoàn tất phân tích Post-Mortem và cập nhật bộ nhớ tiến hóa kênh!");
  } catch (err) {
    toast(`Lỗi chạy Self-Learning: ${err.message}`, true);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = oldText;
    }
  }
});

$("#addCompetitorBtn").addEventListener("click", event => {
  event.preventDefault();
  event.stopPropagation();
  const details = $("#competitorDetailsBox");
  if (details) details.open = true;
  $("#competitorInputs").insertAdjacentHTML("beforeend", competitorInputRow(""));
  bindCompetitorRemoveButtons();
});
bindCompetitorRemoveButtons();

$("#channelProfileSelect").addEventListener("change", async event => {
  try { await selectChannelProfile(event.target.value || null); }
  catch (err) { toast(err.message, true); }
});

$("#createChannelProfileSelect")?.addEventListener("change", async event => {
  const profile = state.channelProfiles.find(item => item.id === String(event.target.value || "")) || null;
  const form = $("#jobForm");
  clearSelectedTopic();
  const manualTitle = String($("#createManualTitleInput")?.value || "").trim();
  if (form?.elements?.title) form.elements.title.value = manualTitle;
  state.createTopicSuggestions = [];
  const suggestions = $("#createTopicSuggestions");
  if (suggestions) suggestions.innerHTML = `<div class="empty-state">Đang nạp đề xuất đề tài theo Hồ sơ Kênh…</div>`;
  await applySelectedProfileToCreateStep(profile, { autoDiscover: true });
});

function prepareCreateNewChannelProfile() {
  closeChannelProfileDialog();
  state.selectedChannelProfileId = null;
  const select = $("#channelProfileSelect");
  if (select) select.value = "";
  fillChannelProfileForm(null);
  updateChannelProfileFormMode(null);
  openDnaStudioModal("identity");
  const labelInput = $("#channelProfileForm")?.elements?.label;
  if (labelInput) {
    labelInput.focus();
    labelInput.placeholder = "Nhập tên hồ sơ mới (hoặc bấm ⚡ Chuẩn True Crime TQ)…";
  }
  const saveLabel = $("#saveChannelProfileLabel");
  if (saveLabel) saveLabel.textContent = "＋ Tạo Hồ sơ Kênh mới";
  toast("Đã mở Xưởng Tạo Hồ sơ Kênh mới (5 tầng DNA).");
}

$("#newChannelProfileBtn")?.addEventListener("click", prepareCreateNewChannelProfile);
$("#createNewProfileBtn")?.addEventListener("click", prepareCreateNewChannelProfile);

$("#cloneChannelProfileBtn")?.addEventListener("click", async () => {
  const profileId = state.selectedChannelProfileId;
  if (!profileId) {
    return toast("Hãy chọn một hồ sơ kênh từ danh sách để nhân bản (Clone).", true);
  }
  const current = currentChannelProfile();
  const baseLabel = current?.label || "Hồ sơ Kênh";
  try {
    $("#cloneChannelProfileBtn").disabled = true;
    toast(`Đang nhân bản hồ sơ "${baseLabel}"…`);
    const cloned = await api(`/api/radar/channel-profiles/${encodeURIComponent(profileId)}/clone`, {
      method: "POST",
      body: JSON.stringify({ label: `${baseLabel} (Bản sao)` }),
    });
    await loadChannelProfiles({ selectId: cloned.id });
    state.selectedChannelProfileId = cloned.id;
    if ($("#channelProfileSelect")) $("#channelProfileSelect").value = cloned.id;
    fillChannelProfileForm(cloned);
    toast(`Đã nhân bản thành công: "${cloned.label}" (ID: ${cloned.id})`);
  } catch (err) {
    toast(`Lỗi khi nhân bản hồ sơ: ${err.message}`, true);
  } finally {
    $("#cloneChannelProfileBtn").disabled = false;
  }
});

$("#closeChannelProfileDialog")?.addEventListener("click", closeChannelProfileDialog);
$("#channelProfileDialog")?.addEventListener("click", event => {
  if (event.target === event.currentTarget) closeChannelProfileDialog();
});

const CHANNEL_EDITING_DNA_PRESETS = {
  infra_25d_dossier: {
    preset_id: "infra_25d_dossier",
    label: "2.5D Hạ Tầng & Điều Tra Kỹ Thuật (Bản đồ vệ tinh + HUD)",
    pacing: 5.5,
    visual_strategy: "hybrid",
    visual_mix: { footage: 0.45, ai_visual: 0.35, motion_overlay: 0.20 },
    color_grade: "technical_cool_cyan",
    editing_archetypes: ["map_route_25d", "hud_telemetry", "evidence_board", "document_highlight", "timeline_scrubber"],
  },
  true_crime_noir_ai: {
    preset_id: "true_crime_noir_ai",
    label: "Hồ Sơ Pháp Y Noir 100% AI (Dây đỏ điều tra + Hồ sơ mật)",
    pacing: 6.5,
    visual_strategy: "full_ai",
    visual_mix: { footage: 0.0, ai_visual: 0.80, motion_overlay: 0.20 },
    color_grade: "dark_forensic_noir",
    editing_archetypes: ["evidence_board", "document_highlight", "timeline_scrubber", "hud_telemetry"],
  },
  archival_vault_us: {
    preset_id: "archival_vault_us",
    label: "Kho Lưu Trữ Lịch Sử & Địa Chính Trị Âu-Mỹ (Film Grain)",
    pacing: 5.0,
    visual_strategy: "hybrid",
    visual_mix: { footage: 0.55, ai_visual: 0.25, motion_overlay: 0.20 },
    color_grade: "warm_archival_sepia",
    editing_archetypes: ["map_route_25d", "document_highlight", "timeline_scrubber", "stat_counter"],
  },
};

$("#channelProfileEditingPreset")?.addEventListener("change", event => {
  const presetKey = String(event.target.value || "").trim();
  const preset = CHANNEL_EDITING_DNA_PRESETS[presetKey];
  if (!preset) return;
  if ($("#channelProfilePacingSec")) $("#channelProfilePacingSec").value = String(preset.pacing);
  if ($("#channelProfileVisualMix")) $("#channelProfileVisualMix").value = formatVisualMixSummary(preset.visual_mix);
  if ($("#channelProfileColorGrade")) $("#channelProfileColorGrade").value = preset.color_grade;
  if ($("#channelProfileEditingArchetypes")) $("#channelProfileEditingArchetypes").value = preset.editing_archetypes.join(", ");
  const form = $("#channelProfileForm");
  if (form?.elements?.default_visual_strategy && preset.visual_strategy) {
    form.elements.default_visual_strategy.value = preset.visual_strategy;
  }
  let baseDna = {};
  try {
    baseDna = JSON.parse(String($("#channelProfileEditingDna")?.value || "{}"));
  } catch (_) { baseDna = {}; }
  const nextDna = {
    ...baseDna,
    preset_id: preset.preset_id,
    pacing: preset.pacing,
    typical_pacing_sec: preset.pacing,
    visual_mix: preset.visual_mix,
    color_grade: preset.color_grade,
    editing_archetypes: preset.editing_archetypes,
  };
  if ($("#channelProfileEditingDna")) $("#channelProfileEditingDna").value = JSON.stringify(nextDna);
  toast(`Đã nạp công thức Edit "${preset.label}" cho hồ sơ kênh.`);
});

$("#channelProfileForm").addEventListener("submit", async event => {
  event.preventDefault();
  const form = event.currentTarget;
  const labelVal = String(form.elements.label?.value || "").trim();
  const ownRef = String(form.elements.own_channel_ref?.value || "").trim();
  const competitorRefs = $$("#competitorInputs input[name=competitor_ref]").map(input => String(input.value || "").trim()).filter(Boolean);
  const dnaMode = String(form.elements.dna_mode?.value || "custom_dna_only").trim();
  const voiceAndStructure = String(form.elements.voice_and_structure?.value || "").trim();
  const referenceImagePolicy = String(form.elements.reference_image_policy?.value || "").trim();
  const allowedTopics = String(form.elements.allowed_topics?.value || "").trim();
  const forbiddenTopics = String(form.elements.forbidden_topics?.value || "").trim();
  const monetizationSafetyPolicy = String(form.elements.monetization_safety_policy?.value || "").trim();
  const ctaStrategy = String(form.elements.cta_strategy?.value || "").trim();
  const hasDnaRules = Boolean(labelVal || allowedTopics || voiceAndStructure || monetizationSafetyPolicy || ctaStrategy);

  if (dnaMode !== "custom_dna_only" && !ownRef && !competitorRefs.length && !hasDnaRules) {
    return toast("Hãy nhập kênh của bạn hoặc ít nhất một kênh mẫu (hoặc chuyển sang chế độ Định danh DNA cố định).", true);
  }
  if (!labelVal && !ownRef && !competitorRefs.length) {
    return toast("Hãy nhập Tên hồ sơ (hoặc bấm '⚡ Chuẩn True Crime TQ') trước khi lưu.", true);
  }

  const market = String(form.elements.market?.value || "KR").toUpperCase();
  const default_lang = String(form.elements.default_language?.value || form.elements.language?.value || "ko").trim();
  const customProfDur = Number($("#profileCustomDurationInput")?.value || 0);
  const duration = (Number.isFinite(customProfDur) && customProfDur >= 2)
    ? Math.min(180, customProfDur)
    : Number(form.elements.default_duration_minutes?.value || form.elements.target_duration_minutes?.value || 20);
  const vs = String(form.elements.default_visual_strategy?.value || form.elements.visual_strategy?.value || "full_ai").trim();
  const mm = String(form.elements.default_ai_media_mode?.value || form.elements.ai_media_mode?.value || "image").trim();

  const parsedArchetypes = form.elements.editing_archetypes?.value
    ? String(form.elements.editing_archetypes.value).split(",").map(s => s.trim()).filter(Boolean)
    : [];

  const creativeBrief = {
    market,
    language: default_lang,
    target_duration_minutes: duration,
    ai_media_mode: mm,
    visual_strategy: vs,
    narrative_angle: String(form.elements.narrative_angle?.value || "").trim() || null,
    writing_style: String(form.elements.writing_style?.value || "").trim() || null,
    hook_archetype: String(form.elements.hook_archetype?.value || "").trim() || null,
    editing_archetypes: parsedArchetypes,
    opening_hook: String(form.elements.opening_hook?.value || "").trim() || null,
    notes: String(form.elements.notes?.value || "").trim() || null,
    cta_strategy: ctaStrategy || null,
  };

  let editingDnaPayload = null;
  const rawDnaVal = String(form.elements.editing_dna?.value || "").trim();
  if (rawDnaVal) {
    try { editingDnaPayload = JSON.parse(rawDnaVal); } catch (_) {}
  }
  const studioPreset = String($("#channelProfileEditingPreset")?.value || "").trim();
  const studioPacing = Number($("#channelProfilePacingSec")?.value || 0);
  const studioColorGrade = String($("#channelProfileColorGrade")?.value || "").trim();
  if (editingDnaPayload || studioPreset || studioPacing || studioColorGrade || parsedArchetypes.length) {
    const presetConfig = CHANNEL_EDITING_DNA_PRESETS[studioPreset] || null;
    editingDnaPayload = {
      ...(editingDnaPayload || {}),
      ...(studioPreset ? { preset_id: studioPreset } : {}),
      pacing: studioPacing > 0 ? studioPacing : (editingDnaPayload?.pacing || presetConfig?.pacing || 6.0),
      typical_pacing_sec: studioPacing > 0 ? studioPacing : (editingDnaPayload?.typical_pacing_sec || presetConfig?.pacing || 6.0),
      visual_mix: editingDnaPayload?.visual_mix || presetConfig?.visual_mix || (vs === "full_ai"
        ? { footage: 0.0, ai_visual: 0.80, motion_overlay: 0.20 }
        : { footage: 0.45, ai_visual: 0.35, motion_overlay: 0.20 }),
      color_grade: studioColorGrade || editingDnaPayload?.color_grade || presetConfig?.color_grade || "dark_forensic_noir",
      editing_archetypes: parsedArchetypes.length ? parsedArchetypes : (editingDnaPayload?.editing_archetypes || presetConfig?.editing_archetypes || []),
    };
  }

  const payload = {
    label: labelVal || null,
    own_channel_ref: ownRef,
    competitor_refs: competitorRefs,
    market,
    default_language: default_lang,
    language: default_lang,
    default_duration_minutes: duration,
    target_duration_minutes: duration,
    default_visual_strategy: vs,
    visual_strategy: vs,
    default_ai_media_mode: mm,
    ai_media_mode: mm,
    dna_mode: dnaMode,
    voice_and_structure: voiceAndStructure || null,
    reference_image_policy: referenceImagePolicy || null,
    allowed_topics: allowedTopics || null,
    forbidden_topics: forbiddenTopics || null,
    monetization_safety_policy: monetizationSafetyPolicy || null,
    cta_strategy: ctaStrategy || null,
    default_creative_brief: creativeBrief,
  };
  if (editingDnaPayload) {
    payload.editing_dna = editingDnaPayload;
  }

  const primaryKw = String($("#channelPrimaryTitleKeyword")?.value || "").trim();
  const meaningVi = String($("#channelPrimaryTitleKeywordMeaningVi")?.value || "").trim();
  const placementRule = String($("#channelKeywordPlacementRule")?.value || "smart_seo_flexible").trim();
  const secAnchors = String($("#channelSecondaryAnchorKeywords")?.value || "")
    .split(",")
    .map(s => s.trim())
    .filter(Boolean);
  const mandHashtags = String($("#channelMandatoryHashtags")?.value || "")
    .split(",")
    .map(s => s.trim())
    .filter(Boolean);
  const defTags = String($("#channelDefaultSeoTags")?.value || "")
    .split(",")
    .map(s => s.trim())
    .filter(Boolean);

  if (primaryKw || secAnchors.length || mandHashtags.length || defTags.length) {
    payload.seo_keyword_dna = {
      primary_title_keyword: primaryKw,
      primary_title_keyword_meaning_vi: meaningVi,
      keyword_placement_rule: placementRule,
      secondary_anchor_keywords: secAnchors,
      mandatory_hashtags: mandHashtags,
      default_seo_tags: defTags,
    };
  }

  // Collect Thumbnail DNA
  const tPreset = String($("#channelThumbnailStylePreset")?.value || "cold_forensic_noir").trim();
  const tSignature = String($("#channelThumbnailVisualSignature")?.value || "").trim();
  const tArchetype = String($("#channelThumbnailArchetype")?.value || "broadcast_left_heavy").trim();
  const tPrimary = String($("#channelThumbnailColorPrimary")?.value || "#FFE84A").trim();
  const tAccent = String($("#channelThumbnailColorAccent")?.value || "#dc2626").trim();
  const tBg = String($("#channelThumbnailColorBg")?.value || "#04070d").trim();
  const tFont = String($("#channelThumbnailFontFamily")?.value || "").trim();
  const tMascotLock = $("#channelThumbnailMascotLock")?.value === "true";
  const tRefChar = String($("#channelThumbnailRefCharPath")?.value || "").trim();

  payload.thumbnail_dna = {
    style_preset: tPreset,
    visual_signature: tSignature,
    color_palette: {
      primary: tPrimary,
      secondary: "#0F172A",
      accent: tAccent,
      background: tBg,
      accent_highlight: tPrimary,
      danger_badge: tAccent,
      text_primary: "#ffffff",
    },
    typography_preset: {
      font_family: tFont || "'Pretendard ExtraBold', 'Gmarket Sans Bold', sans-serif",
      title_weight: "900",
      stroke_color: "#000000",
      stroke_width: 16,
      max_words_per_line: 5,
    },
    layout_template: {
      archetype: tArchetype,
      subject_placement: "right_third",
    },
    reference_character_path: tRefChar,
    mascot_lock: tMascotLock,
  };

  // Voice & Rhythm Specialist Studio payload
  const autoDesignVoice = Boolean($("#channelAutoDesignVoiceToggle")?.checked);
  const voiceSourceMode = String($("#channelVoiceSourceMode")?.value || "base_voice").trim();
  const baseMasterVoiceId = String($("#channelBaseMasterVoiceSelect")?.value || defaultCleanMasterVoiceForMarket(market, default_lang)).trim();
  const voiceCustomDirection = String($("#channelVoiceCustomDirection")?.value || "").trim();
  const sampleFileEl = $("#channelVoiceSampleFile");
  const sampleFile = sampleFileEl?.files?.[0] || null;
  const sampleRefText = String($("#channelVoiceSampleRefText")?.value || "").trim();

  if (voiceSourceMode === "user_sample" && autoDesignVoice && !sampleFile && !state.selectedChannelProfileId) {
    return toast("Bạn đang chọn chế độ Clone từ file mẫu riêng — vui lòng chọn file âm thanh (WAV/MP3/M4A) hoặc chuyển sang Điêu khắc từ Giọng Mẫu Sạch K1.", true);
  }

  payload.auto_design_voice = autoDesignVoice || Boolean(sampleFile);
  payload.voice_source_mode = sampleFile ? "user_sample" : voiceSourceMode;
  payload.base_voice_id = baseMasterVoiceId;
  payload.voice_custom_direction = voiceCustomDirection;
  if (sampleFile) {
    try {
      payload.voice_sample_base64 = await readFileAsDataUrl(sampleFile);
      payload.voice_sample_filename = sampleFile.name;
      payload.voice_sample_ref_text = sampleRefText;
    } catch (readErr) {
      return toast(readErr.message || "Không đọc được file mẫu giọng.", true);
    }
  }

  const profileId = state.selectedChannelProfileId;
  const isUpdate = Boolean(profileId);
  const url = isUpdate ? `/api/radar/channel-profiles/${encodeURIComponent(profileId)}` : "/api/radar/channel-profiles";
  const method = isUpdate ? "PUT" : "POST";

  try {
    $("#saveChannelProfileBtn").disabled = true;
    $("#radarResultHint").textContent = payload.auto_design_voice
      ? "Chuyên gia đang phân tích thể loại, thiết kế màu giọng 1-of-1 và đồng bộ nhịp 3 tầng cho hồ sơ…"
      : (dnaMode === "custom_dna_only"
        ? (ownRef ? "Đang lưu Quy chuẩn DNA cố định và liên kết kênh YouTube của bạn…" : "Đang khóa cứng Định danh & Bộ lọc Đề tài Xanh tiền cho hồ sơ…")
        : (ownRef ? "Đang đọc DNA kênh mình…" : `Đang đọc ${competitorRefs.length} kênh mẫu…`));
    const saved = await api(url, { method, body: JSON.stringify(payload) });
    if (payload.auto_design_voice) {
      try { await loadVoices(); } catch (_) {}
    }
    state.selectedChannelProfileId = saved.id;
    await loadChannelProfiles({ selectId: saved.id });
    const createSelect = $("#createChannelProfileSelect");
    if (createSelect && createSelect.value === saved.id) {
      await applySelectedProfileToCreateStep(saved, { autoDiscover: true });
    }
    $("#radarResultHint").textContent = `${saved.label} · ${channelProfileModeText(saved)}`;
    const voiceNote = saved.voice_signature?.voice_name ? ` (Đã khóa Voice riêng: ${saved.voice_signature.voice_name})` : "";
    toast(isUpdate ? `Đã cập nhật Hồ sơ "${saved.label}"${voiceNote}!` : `Đã tạo Hồ sơ "${saved.label}"${voiceNote}!`);
  } catch (err) { toast(err.message, true); }
  finally { $("#saveChannelProfileBtn").disabled = false; }
});

$("#channelVoiceSourceMode")?.addEventListener("change", () => {
  syncVoiceSourceModeUI();
  if ($("#channelVoiceSourceMode")?.value === "user_sample" && $("#channelAutoDesignVoiceToggle")) {
    $("#channelAutoDesignVoiceToggle").checked = true;
  }
});

$("#channelVoiceSampleFile")?.addEventListener("change", () => {
  if ($("#channelVoiceSampleFile")?.files?.length && $("#channelAutoDesignVoiceToggle")) {
    $("#channelAutoDesignVoiceToggle").checked = true;
  }
});

$("#channelProfileForm [name='market']")?.addEventListener("change", event => {
  if (!state.selectedChannelProfileId && $("#channelBaseMasterVoiceSelect")) {
    const m = String(event.target.value || "KR").toUpperCase();
    const l = String($("#channelProfileForm")?.elements?.default_language?.value || "").trim();
    $("#channelBaseMasterVoiceSelect").value = defaultCleanMasterVoiceForMarket(m, l);
  }
});

$("#analyzeChannelVoiceRhythmBtn")?.addEventListener("click", async () => {
  const btn = $("#analyzeChannelVoiceRhythmBtn");
  const prevText = btn ? btn.textContent : "";
  if (btn) {
    btn.disabled = true;
    btn.textContent = "⏳ Đang phân tích nhịp 3 tầng…";
  }
  try {
    const draft = collectDraftProfileForVoiceAnalysis();
    const res = await api("/api/voice-specialist/analyze", {
      method: "POST",
      body: JSON.stringify({ profile: draft, custom_direction: draft.custom_direction || "" }),
    });
    const current = currentChannelProfile();
    renderProfileVoiceRhythmStudio(current, res.rhythm_dna || res);
    toast(`✓ Đã phân tích thể loại "${(res.rhythm_dna || res)?.archetype_label_vi || "Custom"}" — đồng bộ xong Nhịp Viết · Màu Giọng · Cảm Nhận Nhịp Dựng!`);
  } catch (err) {
    toast(`Lỗi phân tích nhịp: ${err.message}`, true);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = prevText;
    }
  }
});

$("#designChannelVoiceNowBtn")?.addEventListener("click", async () => {
  const profileId = state.selectedChannelProfileId;
  if (!profileId) {
    if ($("#channelAutoDesignVoiceToggle")) $("#channelAutoDesignVoiceToggle").checked = true;
    const form = $("#channelProfileForm");
    if (form) form.requestSubmit();
    return;
  }
  const sourceMode = String($("#channelVoiceSourceMode")?.value || "base_voice").trim();
  const baseVoiceId = String($("#channelBaseMasterVoiceSelect")?.value || "09c70cc1-cc86-4905-b65b-3967209c3175").trim();
  const customDirection = String($("#channelVoiceCustomDirection")?.value || "").trim();
  const sampleFile = $("#channelVoiceSampleFile")?.files?.[0] || null;
  const sampleRefText = String($("#channelVoiceSampleRefText")?.value || "").trim();

  if (sourceMode === "user_sample" && !sampleFile) {
    return toast("Vui lòng chọn file âm thanh mẫu (WAV/MP3/M4A) để Clone màu giọng riêng cho hồ sơ.", true);
  }

  const btn = $("#designChannelVoiceNowBtn");
  const prevText = btn ? btn.textContent : "";
  if (btn) {
    btn.disabled = true;
    btn.textContent = "⏳ Đang điêu khắc & thu mẫu Voice riêng…";
  }
  try {
    const reqBody = {
      source_mode: sampleFile ? "user_sample" : sourceMode,
      base_voice_id: baseVoiceId,
      custom_direction: customDirection,
      synthesize_preview: true,
    };
    if (sampleFile) {
      reqBody.sample_audio_base64 = await readFileAsDataUrl(sampleFile);
      reqBody.sample_filename = sampleFile.name;
      reqBody.sample_ref_text = sampleRefText;
    }
    const res = await api(`/api/radar/channel-profiles/${encodeURIComponent(profileId)}/design-voice-rhythm`, {
      method: "POST",
      body: JSON.stringify(reqBody),
    });
    await loadVoices();
    await loadChannelProfiles({ selectId: profileId, loadPlan: false });
    const audioEl = $("#channelVoiceSignatureAudio");
    if (audioEl && audioEl.src) {
      audioEl.load();
    }
    const vName = res.voice_signature?.voice_name || res.profile?.voice_signature?.voice_name || "Voice 1-of-1";
    toast(`✓ Đã thiết kế & khóa màu giọng độc bản "${vName}" cùng nhịp dựng 3 tầng cho hồ sơ!`);
  } catch (err) {
    toast(`Lỗi thiết kế Voice riêng: ${err.message}`, true);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = prevText;
    }
  }
});

$("#channelProfileLockThumbnailDnaBtn")?.addEventListener("click", async () => {
  const profileId = state.selectedChannelProfileId;
  if (!profileId) return toast("Hãy chọn hoặc lưu một hồ sơ kênh trước khi khóa DNA Thumbnail.", true);

  const tPreset = String($("#channelThumbnailStylePreset")?.value || "cold_forensic_noir").trim();
  const tSignature = String($("#channelThumbnailVisualSignature")?.value || "").trim();
  const tArchetype = String($("#channelThumbnailArchetype")?.value || "broadcast_left_heavy").trim();
  const tPrimary = String($("#channelThumbnailColorPrimary")?.value || "#FFE84A").trim();
  const tAccent = String($("#channelThumbnailColorAccent")?.value || "#dc2626").trim();
  const tBg = String($("#channelThumbnailColorBg")?.value || "#04070d").trim();
  const tFont = String($("#channelThumbnailFontFamily")?.value || "").trim();
  const tMascotLock = $("#channelThumbnailMascotLock")?.value === "true";
  const tRefChar = String($("#channelThumbnailRefCharPath")?.value || "").trim();

  const thumbDnaPayload = {
    thumbnail_dna: {
      style_preset: tPreset,
      visual_signature: tSignature,
      color_palette: {
        primary: tPrimary,
        secondary: "#0F172A",
        accent: tAccent,
        background: tBg,
        accent_highlight: tPrimary,
        danger_badge: tAccent,
        text_primary: "#ffffff",
      },
      typography_preset: {
        font_family: tFont || "'Pretendard ExtraBold', 'Gmarket Sans Bold', sans-serif",
        title_weight: "900",
        stroke_color: "#000000",
        stroke_width: 16,
        max_words_per_line: 5,
      },
      layout_template: {
        archetype: tArchetype,
        subject_placement: "right_third",
      },
      reference_character_path: tRefChar,
      mascot_lock: tMascotLock,
    }
  };

  try {
    const res = await api(`/api/radar/channel-profiles/${encodeURIComponent(profileId)}/lock-thumbnail-dna`, {
      method: "POST",
      body: JSON.stringify(thumbDnaPayload),
    });
    await loadChannelProfiles({ selectId: profileId });
    toast(`Đã lưu & khóa thành công Thumbnail DNA (Phiên bản ${res.version || 2}) cho kênh!`);
  } catch (err) {
    toast(`Lỗi khóa Thumbnail DNA: ${err.message}`, true);
  }
});

$("#refreshChannelProfileBtn").addEventListener("click", async () => {
  if (!state.selectedChannelProfileId) return toast("Hãy lưu hoặc chọn một hồ sơ trước", true);
  try {
    $("#radarResultHint").textContent = channelProfileWorkingText(currentChannelProfile(), "refresh");
    const profile = await api(`/api/radar/channel-profiles/${encodeURIComponent(state.selectedChannelProfileId)}/refresh`, { method: "POST" });
    await loadChannelProfiles({ selectId: profile.id });
    $("#radarResultHint").textContent = `${profile.label} · ${channelProfileModeText(profile)} · đã đồng bộ`;
    toast("Đã đồng bộ dữ liệu hồ sơ kênh.");
  } catch (err) { toast(err.message, true); }
});

$("#profileTodayBtn").addEventListener("click", async () => {
  if (!state.selectedChannelProfileId) return toast("Hãy lưu hoặc chọn một hồ sơ trước", true);
  try {
    setChannelProfileActionsBusy(true);
    const current = currentChannelProfile();
    $("#radarResultHint").textContent = channelProfileWorkingText(current, "today");
    const profileId = state.selectedChannelProfileId;
    const customTodayDur = Number($("#profileTodayCustomDurationInput")?.value || 0);
    const targetDurationMinutes = (Number.isFinite(customTodayDur) && customTodayDur >= 2)
      ? Math.min(180, customTodayDur)
      : Number($("#profileTodayDuration")?.value || current?.default_duration_minutes || 20);
    const discoveryMode = isCustomDnaProfile(current) ? "dna_strict" : "radar_trend";
    const activeStream = state.selectedTopicStream || "all";
    if (!state.sessionSuggestedTopicKeys[profileId]) {
      state.sessionSuggestedTopicKeys[profileId] = new Set();
    }
    const sessionExcluded = Array.from(state.sessionSuggestedTopicKeys[profileId]);
    const result = await runWithChannelProfileActivity(profileId, "today", () => api(`/api/radar/channel-profiles/${encodeURIComponent(profileId)}/today?target_duration_minutes=${encodeURIComponent(targetDurationMinutes)}&discovery_mode=${encodeURIComponent(discoveryMode)}&force_refresh=true&topic_stream=${encodeURIComponent(activeStream)}`, {
      method: "POST",
      body: JSON.stringify({ exclude_titles: sessionExcluded }),
    }));
    if (Array.isArray(result?.today)) {
      for (const item of result.today) {
        const k = String(item?.case_real_name_zh || item?.title_target || item?.title || "").trim();
        if (k) state.sessionSuggestedTopicKeys[profileId].add(k);
      }
    }
    renderRadarResults(result.today || [], { market: result.market || current?.market || "KR", scanId: result.scan_id, profileId, targetDurationMinutes });
    await loadChannelProfiles({ selectId: profileId, loadPlan: false });
    const engine = discoveryMode === "dna_strict" ? "Chuẩn DNA Cố định" : (result.decision_engine === "codex_plus_radar" ? "Codex + Radar" : "Radar fallback");
    $("#radarResultHint").textContent = `${engine} · ${Number(result.today?.length || 0)} đề tài · ${channelProfileModeText({ source_mode: result.source_mode })}`;
  } catch (err) { toast(err.message, true); }
  finally { setChannelProfileActionsBusy(false); }
});

$("#profilePlanBtn").addEventListener("click", async () => {
  if (!state.selectedChannelProfileId) return toast("Hãy lưu hoặc chọn một hồ sơ trước", true);
  try {
    setChannelProfileActionsBusy(true);
    $("#radarResultHint").textContent = channelProfileWorkingText(currentChannelProfile(), "plan");
    const profileId = state.selectedChannelProfileId;
    const plan = await runWithChannelProfileActivity(profileId, "plan", () => api(`/api/radar/channel-profiles/${encodeURIComponent(profileId)}/plan-30-days?refresh_codex=true`, { method: "POST" }));
    renderChannelPlan(plan);
    await loadChannelProfiles({ selectId: profileId, loadPlan: false });
    $("#radarResultHint").textContent = `${plan.decision_engine === "codex_plus_radar" ? "Codex + Radar" : "Radar fallback"} · kế hoạch #${plan.plan_id} · ${plan.completed}/${plan.total} đã làm · đang mở 3 ngày kế tiếp`;
    toast("Đã tạo/tiếp tục kế hoạch 30 ngày.");
  } catch (err) { toast(err.message, true); }
  finally { setChannelProfileActionsBusy(false); }
});

$("#loadScanBtn").addEventListener("click", async () => {
  const scanId = Number($("#scanIdInput").value);
  if (!scanId) return toast("Nhập mã lượt quét trước", true);
  try { await fetchMarketFeed(scanId); } catch (err) { toast(err.message, true); }
});

async function loadCreateAiStylePresets() {
  const select = $("#createAiStylePreset");
  if (!select) return;
  const status = $("#createAiStylePresetStatus");
  const activeProfile = currentChannelProfile();
  const profilePreset = String(
    activeProfile?.default_ai_style_preset ||
    activeProfile?.editorial_dna?.default_ai_style_preset ||
    ""
  ).trim();
  const previous = String(select.value || profilePreset || "");
  try {
    const presets = await api("/api/ai-visual/style-presets");
    const items = Array.isArray(presets) ? presets.filter(item => String(item?.name || "").trim()) : [];
    if (items.length) {
      select.innerHTML = `<option value="" disabled>Chọn preset…</option>${items.map(item => `<option value="${escapeHtml(item.name || "")}">${escapeHtml(item.name || "Preset")}</option>`).join("")}`;
      const targetPreset = (profilePreset && items.some(item => String(item.name || "") === profilePreset))
        ? profilePreset
        : previous;
      if (targetPreset && items.some(item => String(item.name || "") === targetPreset)) select.value = targetPreset;
      if (!select.value && String($("#createAiStyleMode")?.value || "") === "preset") select.value = String(items[0].name || "");
      if (status) status.textContent = `${items.length} preset tích hợp từ SRT-To-Prompt`;
      return;
    }
    if (status) status.textContent = "Không tìm thấy preset STP";
  } catch (_) {
    if (!select.options.length) select.innerHTML = `<option value="" disabled>Không tải được preset</option>`;
    if (status) status.textContent = "Đang dùng danh sách preset tích hợp sẵn";
  }
}

function updateCreatePipelineFlow() {
  const form = $("#jobForm");
  if (!form) return;
  const strategy = String(new FormData(form).get("visual_strategy") || "full_footage");
  const aiConfig = $("#createAiVisualConfig");
  if (aiConfig) aiConfig.hidden = strategy === "full_footage";
  const flow = $("#createPipelineFlow");
  if (!flow) return;
  const paths = {
    full_ai: ["Kịch bản", "Voice + SRT", "Visuals / STP", "AI Visual", "Edit", "SEO", "QC"],
    edit_direct_footage: ["Kịch bản", "Voice + SRT", "Visuals / STP", "AI Visual (Vài ảnh điểm nhấn)", "Edit (@footage AI Agent duyệt bằng mắt + Dựng)", "SEO", "QC"],
    full_footage: ["Kịch bản", "Voice + SRT", "Visuals", "Edit (@footage AI Agent duyệt bằng mắt + Dựng)", "SEO", "QC"],
    hybrid: ["Kịch bản", "Voice + SRT", "Visuals / STP", "AI Visual", "Edit (@footage AI Agent duyệt bằng mắt + Dựng)", "SEO", "QC"],
    evidence_footage: ["Kịch bản", "Voice + SRT", "Visuals / STP", "AI Visual", "Edit (@footage AI Agent duyệt bằng mắt + Dựng)", "SEO", "QC"],
    selective_footage: ["Kịch bản", "Voice + SRT", "Visuals / STP", "AI Visual", "Edit (@footage AI Agent duyệt bằng mắt + Dựng)", "SEO", "QC"],
  };
  const labels = paths[strategy] || paths.full_footage;
  const strategyTag = strategy === "full_ai" ? "FULL AI" : strategy === "edit_direct_footage" ? "BÁN CONTENT (SKIP BƯỚC 4)" : strategy === "hybrid" ? "KẾT HỢP" : (strategy === "evidence_footage" || strategy === "selective_footage") ? "BẰNG CHỨNG + AI" : "FULL FOOTAGE";
  const desc = strategy === "edit_direct_footage"
    ? "Bỏ qua Bước 4 (Footage): Bước 5 tạo vài ảnh AI điểm nhấn, Bước 6 (Edit) AI Agent tự tìm & tải video B-roll trực tiếp để dựng."
    : (strategy === "evidence_footage" || strategy === "selective_footage")
    ? "Chỉ tìm Footage tư liệu thật cho nhân vật/bằng chứng 100% chuẩn, còn lại dùng AI Visual."
    : strategy === "hybrid"
    ? "Visuals sẽ route từng đoạn theo cốt truyện, không dùng tỷ lệ cố định."
    : "Chỉ những bước thuộc nhánh đã chọn mới chạy và tính tiến độ.";
  flow.innerHTML = `<span>Luồng dự án · ${strategyTag}</span>${labels.map((label, index) => `<div>${index + 1}. ${escapeHtml(label)}</div>`).join("")}<small>${desc}</small>`;
}

function updateCreateStyleFields() {
  const mode = String($("#createAiStyleMode")?.value || "auto");
  const preset = $("#createAiStylePreset");
  const custom = $("#createAiCustomStyle");
  if (preset) preset.disabled = false;
  if (custom) custom.disabled = mode !== "custom";
  if (mode === "custom" && $("#createAiCustomDrawer")) {
    $("#createAiCustomDrawer").open = true;
  }
  if (mode === "preset" && preset && !preset.value) {
    const firstPreset = [...preset.options].find(option => option.value);
    if (firstPreset) preset.value = firstPreset.value;
  }
}

async function syncCreateStyleToActiveJob() {
  // Disconnected for strict Step 00 draft isolation:
  // Modifying draft inputs in #jobForm must NEVER mutate state.selectedId in the background.
  return;
}

function fileToDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(new Error("Không đọc được ảnh tham chiếu."));
    reader.readAsDataURL(file);
  });
}

async function uploadCreateStyleReference(jobId) {
  const input = $("#createStyleReferenceInput");
  const file = input?.files?.[0];
  if (!file) return;
  const reference_image_data_url = await fileToDataUrl(file);
  await api(`/api/jobs/${encodeURIComponent(jobId)}/ai-visual-settings`, {
    method: "PATCH",
    body: JSON.stringify({ reference_image_name: file.name, reference_image_data_url }),
  });
}

$("#discoverCreateTopicsBtn")?.addEventListener("click", async () => {
  try { await discoverCreateTopics({ forceRefresh: true, topicStream: state.selectedTopicStream || "all" }); }
  catch (err) { toast(err.message, true); }
});

$$("#createTopicStreamBar [data-topic-stream]").forEach(pill => {
  pill.addEventListener("click", async () => {
    const nextStream = String(pill.dataset.topicStream || "all");
    state.selectedTopicStream = nextStream;
    $$("#createTopicStreamBar [data-topic-stream]").forEach(p => p.classList.toggle("active", p.dataset.topicStream === nextStream));
    try {
      await discoverCreateTopics({ forceRefresh: false, topicStream: nextStream });
    } catch (err) {
      toast(err.message, true);
    }
  });
});

$("#clearSuggestedHistoryBtn")?.addEventListener("click", async () => {
  const form = $("#jobForm");
  const profileId = String(form?.elements?.channel_profile_id?.value || state.selectedChannelProfileId || "").trim();
  if (!profileId) return toast("Hãy chọn hồ sơ kênh trước.", true);
  try {
    state.sessionSuggestedTopicKeys[profileId] = new Set();
    try {
      await api(`/api/radar/channel-profiles/${encodeURIComponent(profileId)}/suggested-topic-history`, { method: "DELETE" });
    } catch (_) {}
    toast("Đã xóa lịch sử chủ đề từng gợi ý (Bộ nhớ 26+ bài đã sản xuất vẫn được khóa bảo vệ 100%). Đang research danh sách mới…");
    await discoverCreateTopics({ forceRefresh: true, topicStream: state.selectedTopicStream || "all", resetHistory: true });
  } catch (err) {
    toast(err.message, true);
  }
});

let preflightInputDebounceTimer = null;
$("#createManualTitleInput")?.addEventListener("input", event => {
  const value = String(event.target.value || "").trim();
  const form = $("#jobForm");
  if (!form?.elements?.title) return;
  form.elements.title.value = value;
  if (value) {
    state.selectedCreateTopic = null;
    state.selectedRadar = null;
    state.selectedChannelPlan = null;
    const badge = $("#selectedTopicBadge");
    badge.classList.remove("hidden");
    badge.innerHTML = `<span>THỦ CÔNG</span><strong>${escapeHtml(value)}</strong>`;
  }
  const pid = form.elements.channel_profile_id?.value || state.selectedChannelProfileId;
  if (pid) {
    clearTimeout(preflightInputDebounceTimer);
    preflightInputDebounceTimer = setTimeout(() => {
      renderCreatePreflightSummary(pid, value, value);
    }, 450);
  }
});

$("#runPreflightCheckBtn")?.addEventListener("click", () => {
  const form = $("#jobForm");
  const pid = form?.elements?.channel_profile_id?.value || state.selectedChannelProfileId;
  const value = String($("#createManualTitleInput")?.value || form?.elements?.title?.value || "").trim();
  if (!pid) {
    return toast("Vui lòng chọn một Hồ sơ Kênh trước khi chạy Pre-Flight Check.", true);
  }
  renderCreatePreflightSummary(pid, value, value);
});

const CREATIVE_LABELS = {
  narrative_angles: {
    investigative_forensic: "🕵️ Điều tra Hồ sơ Mật (Forensic Investigative)",
    systemic_breakdown: "⚙️ Giải phẫu Hệ thống & Cơ chế (Systemic Breakdown)",
    insider_tragedy: "🎭 Bi kịch Người trong cuộc (Insider Tragedy)",
    geopolitical_chess: "♟️ Bàn cờ Địa chính trị & Quyền lực (Geopolitical Chess)",
    contrarian_mythbuster: "⚡ Phản biện Ngược dòng (Contrarian Myth-Buster)",
    financial_autopsy: "📉 Giải phẫu Tài chính & Dòng tiền (Financial Autopsy)",
  },
  writing_styles: {
    cold_dossier: "🗂️ Lạnh lùng, Đanh thép, Dữ liệu thật (Cold Dossier)",
    cinematic_thriller: "🎬 Kịch tính Điện ảnh, Cliffhanger (Cinematic Thriller)",
    vox_analytical: "📊 Phân tích Trực quan, Giải thích Sâu (Vox Analytical)",
    empathetic_humanist: "🕯️ Trầm lắng, Giàu cảm xúc & Nhân văn (Empathetic Humanist)",
    ironic_sharp: "🗡️ Châm biếm Sắc sảo, Bóc trần Nghịch lý (Sharp Ironic)",
  },
  hook_archetypes: {
    in_media_res: "💥 Mở màn ngay khoảnh khắc Thảm họa (In Media Res)",
    shocking_anomaly: "🚨 Con số / Bằng chứng Phi lý gây sốc (Shocking Anomaly)",
    declassified_leak: "📂 Mở niêm phong Tài liệu / Băng ghi âm mật (Declassified Leak)",
    the_big_lie: "🎭 Lời nói dối vĩ đại & Sự thật bị chôn vùi (The Big Lie)",
    micro_to_macro: "🔬 Từ 1 chi tiết nhỏ mở ra Đế chế sụp đổ (Micro-to-Macro)",
  },
  editing_archetypes: {
    forensic_red_string: "🕵️ Hồ sơ điều tra & Sơ đồ mạng lưới",
    vox_blueprint_explainer: "📐 Bản vẽ kỹ thuật & Đồ họa phân tích",
    kinetic_financial_ticker: "💹 Nhịp tài chính dồn dập & Dữ liệu số",
    atmospheric_cinema_verite: "🎞️ Phim nhựa tài liệu thở (Cinema Vérité)",
    split_screen_contradiction: "⚖️ Chia đôi màn hình: Lời hứa vs Sự thật",
  },
};

function humanizeCreativeKey(group, key) {
  if (!key) return "";
  return CREATIVE_LABELS[group]?.[key] || String(key);
}

async function loadPlaybooks() {
  try {
    const res = await api("/api/playbooks");
    state.playbooks = Array.isArray(res?.items) ? res.items : (Array.isArray(res) ? res : []);
  } catch (_) {
    state.playbooks = [];
  }
  renderCreatePlaybookSelect();
  return state.playbooks;
}

function renderCreatePlaybookSelect(selectedId = null) {
  const select = $("#createPlaybookSelect");
  if (!select) return;
  const currentVal = selectedId !== null ? String(selectedId || "") : String(select.value || "");
  const items = Array.isArray(state.playbooks) ? state.playbooks : [];
  select.innerHTML = [
    `<option value="">✨ Tự do sáng tạo / Chọn Playbook mẫu...</option>`,
    ...items.map(pb => {
      const badge = pb.built_in ? "🏛️ Mẫu chuẩn" : "🧬 Kênh của bạn";
      return `<option value="${escapeHtml(pb.id)}">${badge} · ${escapeHtml(pb.name)}${pb.description ? ` — ${escapeHtml(pb.description.slice(0, 65))}` : ""}</option>`;
    }),
  ].join("");
  if (currentVal && items.some(pb => String(pb.id) === currentVal)) {
    select.value = currentVal;
  }
}

function parseEditingArchetypesValue(val) {
  if (Array.isArray(val)) {
    return val.map(v => String(v || "").trim()).filter(Boolean);
  }
  return String(val || "")
    .split(",")
    .map(s => s.trim())
    .filter(Boolean);
}

function formatEditingArchetypesDisplay(val) {
  const list = parseEditingArchetypesValue(val);
  return list.map(k => humanizeCreativeKey("editing_archetypes", k)).join(", ");
}

function getCheckedEditingArchetypes(containerOrInputSelector = "#createEditingArchetypesInput") {
  const el = $(containerOrInputSelector);
  if (!el) return [];
  if (el.tagName === "INPUT" || el.tagName === "TEXTAREA") {
    return parseEditingArchetypesValue(el.value);
  }
  return [...el.querySelectorAll('input[type="checkbox"]:checked')].map(item => String(item.value || "").trim()).filter(Boolean);
}

function setCheckedEditingArchetypes(values = [], containerOrInputSelector = "#createEditingArchetypesInput") {
  const el = $(containerOrInputSelector);
  if (!el) return;
  const list = parseEditingArchetypesValue(values);
  if (el.tagName === "INPUT" || el.tagName === "TEXTAREA") {
    el.value = formatEditingArchetypesDisplay(list);
    return;
  }
  const set = new Set(list);
  el.querySelectorAll('input[type="checkbox"]').forEach(chk => {
    chk.checked = set.has(String(chk.value || "").trim());
  });
}

function collectCreateCreativeBrief() {
  const playbookId = String($("#createPlaybookSelect")?.value || "").trim();
  const narrativeAngle = String($("#createNarrativeAngle")?.value || "").trim();
  const writingStyle = String($("#createWritingStyle")?.value || "").trim();
  const hookArchetype = String($("#createHookArchetype")?.value || "").trim();
  const editingArchetypes = parseEditingArchetypesValue(
    $("#createEditingArchetypesInput")?.value || getCheckedEditingArchetypes("#createEditingArchetypes")
  );
  const openingHook = String($("#createOpeningHookInput")?.value || "").trim();
  const customRules = String($("#createNotesTextarea")?.value || "").trim();
  return {
    playbook_id: playbookId || null,
    narrative_angle: narrativeAngle || "Giải phẫu Hồ sơ Điều tra (Forensic Investigative)",
    writing_style: writingStyle || "Lạnh lùng, Đanh thép, Dữ liệu thật (Cold Dossier)",
    hook_archetype: hookArchetype || "Con số / Sự thật Phi lý gây sốc (Shocking Anomaly)",
    editing_archetypes: editingArchetypes.length ? editingArchetypes : ["Hồ sơ điều tra & Sơ đồ mạng lưới", "Bản vẽ kỹ thuật & Đồ họa phân tích"],
    opening_hook: openingHook,
    custom_rules: customRules,
  };
}

function collectCreateOutline() {
  const raw = String($("#createOutlineJsonInput")?.value || "").trim();
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed)) return { chapters: parsed };
    if (parsed && typeof parsed === "object") return parsed;
  } catch (_) {}
  return null;
}

function setCreateAttachedOutline(outlineObj = null) {
  const input = $("#createOutlineJsonInput");
  const banner = $("#createOutlineAttachedBanner");
  const label = $("#createOutlineAttachedLabel");
  if (!input) return;
  const chapters = Array.isArray(outlineObj)
    ? outlineObj
    : Array.isArray(outlineObj?.chapters)
      ? outlineObj.chapters
      : [];
  if (!chapters.length) {
    input.value = "";
    banner?.classList.add("hidden");
    return;
  }
  const normalized = Array.isArray(outlineObj) ? { chapters } : { ...outlineObj, chapters };
  input.value = JSON.stringify(normalized);
  if (label) {
    const previewHtml = chapters
      .map((c, idx) => `${idx + 1}. ${c.title || c.chapter_title || `Chương ${idx + 1}`}`)
      .join(" · ");
    label.textContent = `Đã đồng bộ Dàn ý (${chapters.length} chương: ${previewHtml}) — Sẽ dùng làm xương sống kịch bản khi tạo dự án.`;
  }
  banner?.classList.remove("hidden");
}

function applyPlaybookToCreateForm(playbook) {
  if (!playbook || typeof playbook !== "object") return;
  const brief = playbook.creative_brief || playbook;
  if ($("#createPlaybookSelect") && playbook.id) {
    $("#createPlaybookSelect").value = String(playbook.id);
  }
  if ($("#createNarrativeAngle") && brief.narrative_angle) {
    $("#createNarrativeAngle").value = humanizeCreativeKey("narrative_angles", brief.narrative_angle);
  }
  if ($("#createWritingStyle") && brief.writing_style) {
    $("#createWritingStyle").value = humanizeCreativeKey("writing_styles", brief.writing_style);
  }
  if ($("#createHookArchetype") && brief.hook_archetype) {
    $("#createHookArchetype").value = humanizeCreativeKey("hook_archetypes", brief.hook_archetype);
  }
  if (brief.editing_archetypes) {
    setCheckedEditingArchetypes(brief.editing_archetypes, "#createEditingArchetypesInput");
  }
  if (brief.opening_hook && $("#createOpeningHookInput")) {
    $("#createOpeningHookInput").value = String(brief.opening_hook);
  }
  if (brief.custom_rules && $("#createNotesTextarea")) {
    $("#createNotesTextarea").value = String(brief.custom_rules);
  }
  if (playbook.ai_style_preset && $("#createAiStylePreset")) {
    $("#createAiStylePreset").value = String(playbook.ai_style_preset);
    if ($("#createAiStyleMode")) $("#createAiStyleMode").value = "preset";
    updateCreateStyleFields();
  }
}

function applyCreativeProposalToCreateForm(proposal = {}, { switchTab = false, silent = false } = {}) {
  if (!proposal || typeof proposal !== "object") return;
  const brief = proposal.creative_brief && typeof proposal.creative_brief === "object"
    ? { ...proposal.creative_brief, ...proposal }
    : proposal;
  const form = $("#jobForm");
  const cleanTitle = String(proposal.title || proposal.topic || "").trim();
  if (cleanTitle) {
    if ($("#createManualTitleInput")) $("#createManualTitleInput").value = cleanTitle;
    if (form?.elements?.title) form.elements.title.value = cleanTitle;
    const badge = $("#selectedTopicBadge");
    if (badge) {
      badge.classList.remove("hidden");
      badge.innerHTML = `<span>AI CHAT SYNC</span><strong>${escapeHtml(cleanTitle)}</strong>`;
    }
  }
  if (proposal.market && form?.elements?.market) {
    const mkt = String(proposal.market).toUpperCase();
    if (["KR", "JP", "US", "VN"].includes(mkt)) form.elements.market.value = mkt;
  }
  if (proposal.target_duration_minutes && form?.elements?.target_duration_minutes) {
    setComboDurationValue(form.elements.target_duration_minutes, $("#createCustomDurationInput"), proposal.target_duration_minutes, "Khoảng");
  }
  if (proposal.visual_strategy && form?.elements?.visual_strategy) {
    form.elements.visual_strategy.value = String(proposal.visual_strategy);
  }
  if (brief.playbook_id && $("#createPlaybookSelect")) {
    $("#createPlaybookSelect").value = String(brief.playbook_id);
  }
  if ("narrative_angle" in brief && $("#createNarrativeAngle")) {
    $("#createNarrativeAngle").value = brief.narrative_angle ? humanizeCreativeKey("narrative_angles", brief.narrative_angle) : "";
  }
  if ("writing_style" in brief && $("#createWritingStyle")) {
    $("#createWritingStyle").value = brief.writing_style ? humanizeCreativeKey("writing_styles", brief.writing_style) : "";
  }
  if ("hook_archetype" in brief && $("#createHookArchetype")) {
    $("#createHookArchetype").value = brief.hook_archetype ? humanizeCreativeKey("hook_archetypes", brief.hook_archetype) : "";
  }
  if ("editing_archetypes" in brief || "editing_grammar" in brief) {
    const archetypesRaw = brief.editing_archetypes || brief.editing_grammar;
    if (archetypesRaw && (Array.isArray(archetypesRaw) ? archetypesRaw.length : String(archetypesRaw).trim())) {
      setCheckedEditingArchetypes(archetypesRaw, "#createEditingArchetypesInput");
    } else if ($("#createEditingArchetypesInput")) {
      $("#createEditingArchetypesInput").value = "";
    }
  }
  if ("opening_hook" in brief && $("#createOpeningHookInput")) {
    $("#createOpeningHookInput").value = brief.opening_hook != null ? String(brief.opening_hook).trim() : "";
  }
  if ("notes" in brief || "notes" in proposal || "custom_rules" in brief) {
    const rulesText = brief.custom_rules || brief.notes || proposal.notes || proposal.why_it_works || "";
    if ($("#createNotesTextarea")) {
      $("#createNotesTextarea").value = String(rulesText).trim();
    }
  }
  const chapters = Array.isArray(proposal.outline)
    ? proposal.outline
    : (proposal.outline?.chapters || proposal.chapters || brief.outline?.chapters || []);
  if (Array.isArray(chapters) && chapters.length) {
    setCreateAttachedOutline({
      thesis: proposal.thesis || proposal.why_it_works || "",
      opening_hook: brief.opening_hook || "",
      chapters,
    });
  }
  const syncBadge = $("#createDraftSyncBadge");
  if (syncBadge) {
    syncBadge.textContent = "✦ Đã đồng bộ trực tiếp từ AI Chat";
  }
  if (switchTab) {
    setAppTab("create");
    $("#creativeBriefStudio")?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }
  syncCreativeQuickChipsState();
  if (!silent) {
    state.lastSyncedUiDraftSig = JSON.stringify({
      title: cleanTitle,
      angle: brief.narrative_angle,
      style: brief.writing_style,
      hook: brief.hook_archetype,
      opening: brief.opening_hook,
      chapters: Array.isArray(chapters) ? chapters.length : 0,
    });
  }
}

function syncCreativeQuickChipsState() {
  document.querySelectorAll(".creative-quick-chips").forEach(group => {
    const targetSel = group.dataset.targetInput;
    const mode = group.dataset.chipMode || "single";
    const input = targetSel ? $(targetSel) : null;
    if (!input) return;
    const rawVal = String(input.value || "").trim();
    const multiItems = mode === "multi"
      ? parseEditingArchetypesValue(rawVal).map(s => s.toLowerCase())
      : [];
    group.querySelectorAll(".creative-chip").forEach(chip => {
      const chipVal = String(chip.dataset.value || "").trim();
      const isMatch = mode === "multi"
        ? multiItems.includes(chipVal.toLowerCase())
        : rawVal.toLowerCase() === chipVal.toLowerCase();
      chip.classList.toggle("active", Boolean(chipVal && isMatch));
    });
  });
}

document.querySelectorAll(".creative-quick-chips").forEach(group => {
  const targetSel = group.dataset.targetInput;
  const mode = group.dataset.chipMode || "single";
  const input = targetSel ? $(targetSel) : null;
  if (!input) return;
  input.addEventListener("input", () => syncCreativeQuickChipsState());
  input.addEventListener("change", () => syncCreativeQuickChipsState());
  group.addEventListener("click", event => {
    const chip = event.target.closest(".creative-chip");
    if (!chip) return;
    const val = String(chip.dataset.value || "").trim();
    if (!val) return;
    if (mode === "multi") {
      const current = parseEditingArchetypesValue(input.value);
      const existsIdx = current.findIndex(item => item.toLowerCase() === val.toLowerCase());
      if (existsIdx >= 0) {
        current.splice(existsIdx, 1);
      } else {
        current.push(val);
      }
      input.value = current.join(", ");
    } else {
      input.value = String(input.value || "").trim().toLowerCase() === val.toLowerCase() ? "" : val;
    }
    syncCreativeQuickChipsState();
  });
});

$("#createPlaybookSelect")?.addEventListener("change", event => {
  const pbId = String(event.target.value || "").trim();
  if (!pbId) return;
  const pb = (state.playbooks || []).find(item => String(item.id) === pbId);
  if (pb) {
    applyPlaybookToCreateForm(pb);
    syncCreativeQuickChipsState();
    toast(`Đã nạp Playbook "${pb.name}".`);
  }
});

$("#clearAttachedOutlineBtn")?.addEventListener("click", () => {
  setCreateAttachedOutline(null);
  toast("Đã gỡ dàn ý đính kèm.");
});

let isSubmittingJobForm = false;
$("#jobForm").addEventListener("submit", async event => {
  event.preventDefault();
  if (isSubmittingJobForm) return;
  const form = event.currentTarget;
  const submitMode = event.submitter?.dataset?.submitMode || "run_full";
  const submitBtns = [...form.querySelectorAll('button[type="submit"]')];
  const prevLabels = new Map(submitBtns.map(btn => [btn, btn.textContent]));
  isSubmittingJobForm = true;
  submitBtns.forEach(btn => {
    btn.disabled = true;
    if (btn === event.submitter) {
      btn.textContent = submitMode === "run_full" ? "Đang tạo & khởi chạy…" : "Đang tạo dự án…";
    }
  });
  try {
    let raw = Object.fromEntries(new FormData(form).entries());
    const manualTitle = String($("#createManualTitleInput")?.value || "").trim();
    if (!String(raw.title || "").trim() && manualTitle) {
      raw.title = manualTitle;
    }
    if (!String(raw.title || "").trim() && String(raw.channel_profile_id || "").trim()) {
      await discoverCreateTopics();
      raw = Object.fromEntries(new FormData(form).entries());
    }
    if (!String(raw.title || "").trim()) {
      throw new Error("Hãy chọn hồ sơ kênh hoặc nhập tiêu đề trước khi tạo dự án.");
    }
    const chosenStyleMode = String($("#createAiStyleMode")?.value || raw.ai_style_mode || "auto");
    const chosenStylePreset = String($("#createAiStylePreset")?.value || raw.ai_style_preset || "");
    const chosenCustomStyle = String($("#createAiCustomStyle")?.value || raw.ai_custom_style || "");
    const creativeBrief = collectCreateCreativeBrief();
    const attachedOutline = collectCreateOutline();
    const payload = {
      title: raw.title,
      source_url: raw.source_url || null,
      market: raw.market,
      language: raw.language,
      notes: raw.notes || "",
      playbook_id: creativeBrief.playbook_id || null,
      creative_brief: creativeBrief,
      outline: attachedOutline,
      target_duration_minutes: (() => {
        const customJobDur = Number($("#createCustomDurationInput")?.value || 0);
        return (Number.isFinite(customJobDur) && customJobDur >= 2)
          ? Math.min(180, customJobDur)
          : Number(raw.target_duration_minutes || 30);
      })(),
      plan_engine: raw.plan_engine || "codex",
      visual_strategy: raw.visual_strategy || "full_footage",
      ai_media_mode: raw.ai_media_mode || "mixed",
      ai_visual: {
        style_mode: currentCreateStyleReferenceDataUrl ? (chosenStyleMode === "preset" ? "preset" : "custom") : chosenStyleMode,
        style_preset: chosenStylePreset,
        custom_style: chosenCustomStyle,
        ai_media_mode: raw.ai_media_mode || "mixed",
      },
      reference_image_data_url: currentCreateStyleReferenceDataUrl || undefined,
      reference_image_name: currentCreateStyleReferenceName || undefined,
      footage_mode: "vision_codex",
      voice: { voice_id: raw.voice_id || null, speed: Number(raw.voice_speed || 1), mode: "balanced" },
      channel_profile_id: state.selectedChannelPlan?.profileId || state.selectedRadar?.profileId || raw.channel_profile_id || null,
      channel_plan_item_id: state.selectedChannelPlan?.itemId || null,
      topic_discovery: state.selectedCreateTopic ? {
        source: "channel_profile_today",
        profile_id: state.selectedCreateTopic.profileId || raw.channel_profile_id || null,
        scan_id: state.selectedCreateTopic.scanId || null,
        selected_candidate: {
          id: state.selectedCreateTopic.videoId || null,
          title: state.selectedCreateTopic.title || raw.title || "",
          codex_score: state.selectedCreateTopic.codexScore ?? null,
          codex_verdict: state.selectedCreateTopic.codexVerdict || null,
          profile_score: state.selectedCreateTopic.profileScore ?? state.selectedCreateTopic.radarProfileScore ?? null,
          competitor_support_count: state.selectedCreateTopic.competitorSupportCount ?? null,
          evidence_outlier: state.selectedCreateTopic.outlier ?? null,
          evidence_vph: state.selectedCreateTopic.vph ?? null,
          evidence_url: state.selectedCreateTopic.url || null,
        },
      } : {},
      workspace_root: raw.workspace_root || null,
    };
    let job;
    const selectedPlan = state.selectedChannelPlan ? { ...state.selectedChannelPlan } : null;
    if (state.selectedRadar?.scanId && state.selectedRadar?.videoId) {
      job = await api("/api/jobs/from-radar", { method: "POST", body: JSON.stringify({
        scan_id: Number(state.selectedRadar.scanId), video_id: String(state.selectedRadar.videoId),
        target_duration_minutes: payload.target_duration_minutes, plan_engine: payload.plan_engine, visual_strategy: payload.visual_strategy,
        ai_media_mode: payload.ai_media_mode, ai_visual: payload.ai_visual,
        language: payload.language, market: payload.market, notes: payload.notes, voice: payload.voice,
        playbook_id: payload.playbook_id, creative_brief: payload.creative_brief, outline: payload.outline,
        channel_profile_id: payload.channel_profile_id,
        workspace_root: payload.workspace_root,
      }) });
    } else {
      job = await api("/api/jobs", { method: "POST", body: JSON.stringify(payload) });
    }
    try {
      await uploadCreateStyleReference(job.id);
    } catch (referenceErr) {
      toast(`Dự án đã tạo nhưng ảnh tham chiếu chưa lưu được: ${referenceErr.message}`, true);
    }
    if (selectedPlan?.profileId && selectedPlan?.itemId) {
      try {
        await api(`/api/radar/channel-profiles/${encodeURIComponent(selectedPlan.profileId)}/plan-items/${encodeURIComponent(selectedPlan.itemId)}`, {
          method: "PATCH",
          body: JSON.stringify({ status: "doing" }),
        });
      } catch (_) {}
    }
    state.userPinnedJobId = null;
    state.selectedId = job.id;
    state.autoFollowPipelineJobId = job.id;
    state.detailTab = "tongquan";
    state.lastJobListHtml = "";
    state.lastOverviewDeckHtml = "";
    // Immediately sync the newly created job into the in-memory profile topic_memory
    // and prune it from state.createTopicSuggestions so it never stays suggested
    const createdTitleNorm = String(job.title || payload.title || "").trim().toLowerCase();
    const targetProf = state.channelProfiles.find(p => p.id === (job.channel_profile_id || payload.channel_profile_id));
    if (targetProf && createdTitleNorm) {
      if (!Array.isArray(targetProf.topic_memory)) targetProf.topic_memory = [];
      if (!targetProf.topic_memory.some(m => String(m?.title || "").trim().toLowerCase() === createdTitleNorm)) {
        targetProf.topic_memory.push({
          id: `topic-${job.id}`,
          job_id: job.id,
          title: job.title || payload.title,
          topic: job.topic || job.title || payload.title,
          source: "job",
        });
      }
    }
    if (Array.isArray(state.createTopicSuggestions) && state.createTopicSuggestions.length && createdTitleNorm) {
      state.createTopicSuggestions = state.createTopicSuggestions.filter(item => {
        const iTitle = String(item.titleTarget || item.raw?.title_target || item.title || "").trim().toLowerCase();
        return iTitle !== createdTitleNorm && !isTopicInProfileMemory(item, targetProf);
      });
    }
    clearSelectedTopic();
    setCreateAttachedOutline(null);
    await loadJobs(true);
    await renderDetail();
    if (submitMode === "run_full") {
      await runFullPipeline(job, { fromBeginning: true });
    } else {
      state.lastFollowedPhaseKey = `${job.id}:plan`;
      await api(`/api/jobs/${encodeURIComponent(job.id)}/run/plan`, { method: "POST", body: "{}" });
      await loadJobs(true);
      await renderDetail();
      setAppTab("script");
      toast("Đã tạo dự án và bắt đầu viết Kịch bản (Bước 1).");
    }
    loadHealth().catch(() => {});
  } catch (err) {
    toast(err.message, true);
  } finally {
    isSubmittingJobForm = false;
    submitBtns.forEach(btn => {
      btn.disabled = false;
      btn.textContent = prevLabels.get(btn) || btn.textContent;
    });
  }
});

$$('input[name="visual_strategy"]').forEach(input => input.addEventListener("change", updateCreatePipelineFlow));
$$('#jobForm input[name="ai_media_mode"]').forEach(input => input.addEventListener("change", () => {
  // Draft isolation: modifying media mode in Step 00 must never mutate active project
}));
$("#createAiStyleMode")?.addEventListener("change", () => {
  updateCreateStyleFields();
});
$("#createAiStylePreset")?.addEventListener("change", () => {
  const modeEl = $("#createAiStyleMode");
  if (modeEl && $("#createAiStylePreset")?.value) {
    modeEl.value = "preset";
  }
  updateCreateStyleFields();
});
$("#createAiCustomStyle")?.addEventListener("change", () => {
  const modeEl = $("#createAiStyleMode");
  if (modeEl && String($("#createAiCustomStyle")?.value || "").trim()) {
    modeEl.value = "custom";
  }
  updateCreateStyleFields();
});
let currentCreateStyleReferenceDataUrl = null;
let currentCreateStyleReferenceName = null;

$("#createStyleReferenceInput")?.addEventListener("change", event => {
  const file = event.target.files?.[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = e => {
    currentCreateStyleReferenceDataUrl = e.target.result;
    currentCreateStyleReferenceName = file.name;
    const container = $("#createStyleReferencePreviewContainer");
    const img = $("#createStyleReferencePreviewImg");
    const nameEl = $("#createStyleReferenceFilename");
    if (img) img.src = currentCreateStyleReferenceDataUrl;
    if (nameEl) nameEl.textContent = file.name;
    if (container) container.classList.remove("hidden");
    if ($("#createAiCustomDrawer")) $("#createAiCustomDrawer").open = true;
    toast(`Đã nhận ảnh tham chiếu: ${file.name}`);
  };
  reader.readAsDataURL(file);
});

$("#clearCreateStyleReferenceBtn")?.addEventListener("click", () => {
  currentCreateStyleReferenceDataUrl = null;
  currentCreateStyleReferenceName = null;
  const input = $("#createStyleReferenceInput");
  if (input) input.value = "";
  const container = $("#createStyleReferencePreviewContainer");
  if (container) container.classList.add("hidden");
  const img = $("#createStyleReferencePreviewImg");
  if (img) img.src = "";
  toast("Đã gỡ ảnh tham chiếu phong cách");
});

$("#addTopicMemoryBtn")?.addEventListener("click", async () => {
  const input = $("#addTopicMemoryTitleInput");
  const val = String(input?.value || "").trim();
  const profileId = state.selectedChannelProfileId;
  if (!val) return toast("Vui lòng nhập tên đề tài đã làm", true);
  if (!profileId) return toast("Chưa chọn hồ sơ kênh", true);
  try {
    await api(`/api/radar/channel-profiles/${encodeURIComponent(profileId)}/topic-memory`, {
      method: "POST",
      body: JSON.stringify({ title: val, topic: val, source: "manual" }),
    });
    input.value = "";
    toast("Đã thêm đề tài vào bộ nhớ");
    renderTopicMemoryList(profileId);
  } catch (err) {
    toast(err.message || "Không thêm được đề tài", true);
  }
});
updateCreatePipelineFlow();
updateCreateStyleFields();
loadCreateAiStylePresets();

$("#selectWorkspaceRootBtn")?.addEventListener("click", async () => {
  const button = $("#selectWorkspaceRootBtn");
  button.disabled = true;
  button.textContent = "Đang mở…";
  try {
    const result = await api("/api/storage/select-folder", { method: "POST" });
    if (result.path) {
      $("#workspaceRootInput").value = result.path;
      toast("Đã chọn thư mục lưu dự án.");
    }
  } catch (err) { toast(err.message, true); }
  finally {
    button.disabled = false;
    button.textContent = "Chọn thư mục";
  }
});

function formatBytes(value) {
  const bytes = Math.max(0, Number(value || 0));
  if (bytes < 1024) return `${Math.round(bytes)} B`;
  const units = ["KB", "MB", "GB", "TB"];
  let amount = bytes / 1024;
  let unit = units[0];
  for (let index = 1; index < units.length && amount >= 1024; index += 1) {
    amount /= 1024;
    unit = units[index];
  }
  return `${amount >= 10 ? amount.toFixed(1) : amount.toFixed(2)} ${unit}`;
}

function jobCard(job) {
  const done = completedPhaseCount(job);
  const activePhases = effectivePhases(job);
  const waitingReview = job.status === "ready" && done > 0 && done < activePhases.length;
  const isPaused = Boolean(job.is_paused || job.phases?.[job.current_phase]?.is_paused);
  const active = isPaused ? "⚠️ Tạm dừng" : job.current_phase ? phaseLabels[job.current_phase] : waitingReview ? "Chờ bạn duyệt" : statusLabels[job.status] || job.status;
  const stateClass = isPaused ? "interrupted paused" : job.status;
  const deleteDisabled = ["running", "queued"].includes(job.status);
  return `<article class="job-card ${job.id === state.selectedId ? "selected" : ""}" data-job="${escapeHtml(job.id)}">
    <div class="job-card-top"><span class="job-market">${escapeHtml(job.market)}</span><div class="job-card-actions"><span class="job-state ${escapeHtml(stateClass)}">${escapeHtml(active)}</span><button class="job-delete" type="button" data-delete-job="${escapeHtml(job.id)}" ${deleteDisabled ? "disabled" : ""} title="${deleteDisabled ? "Dự án đang chạy" : "Xóa dự án"}">Xóa</button></div></div>
    <h3>${escapeHtml(job.title)}</h3>
    <p>${Math.round((job.production_recipe?.target_duration_sec || 300) / 60)} phút · ${job.plan_engine === "gemini" ? "Gemini viết" : "Codex viết"}</p>
    <p class="job-storage-path" title="${escapeHtml(job.workspace || "")}">${formatBytes(job.storage_bytes)} · ${escapeHtml(job.workspace || "")}</p>
    <div class="job-progress"><span style="width:${(done / activePhases.length) * 100}%"></span></div>
    <small>${done}/${activePhases.length} bước hoàn tất</small>
  </article>`;
}

function updateSidebarPhaseVisibility(job) {
  const active = job ? new Set(effectivePhases(job)) : null;
  const tabPhaseMap = {
    script: "plan",
    voice: "voice",
    visuals: "visuals",
    footage: "footage",
    ai_visual: "ai_visual",
    edit: "edit",
    seo: "seo",
    qc: "qc",
  };
  Object.entries(tabPhaseMap).forEach(([tab, phase]) => {
    const btn = document.querySelector(`.nav-item[data-app-tab="${tab}"]`);
    if (!btn) return;
    if (!btn.dataset.defaultTitle) {
      btn.dataset.defaultTitle = btn.getAttribute("title") || btn.textContent.replace(/\s+/g, " ").trim();
    }
    const skipped = Boolean(active && !active.has(phase));
    btn.classList.toggle("nav-item-skipped", skipped);
    if (skipped) {
      btn.setAttribute("title", `${btn.dataset.defaultTitle} — Bước này được bỏ qua theo chiến lược hình ảnh`);
    } else {
      btn.setAttribute("title", btn.dataset.defaultTitle);
    }
  });
}

async function loadJobs(keepSelection = true, { summary = false } = {}) {
  const prevSelectedId = state.selectedId;
  state.jobs = await api(summary ? "/api/jobs?summary=1" : "/api/jobs");
  if (!state.selectedId) {
    try {
      const savedId = localStorage.getItem("cofi-selected-job-id");
      if (savedId && state.jobs.some(j => j.id === savedId)) state.selectedId = savedId;
    } catch (_) {}
  }
  if ((!keepSelection || !state.selectedId || !state.jobs.some(j => j.id === state.selectedId)) && state.jobs.length) state.selectedId = state.jobs[0].id;
  if (state.selectedId) {
    try { localStorage.setItem("cofi-selected-job-id", state.selectedId); } catch (_) {}
  }
  $("#jobCount").textContent = state.jobs.length;
  const activeJobs = state.jobs.filter(job => ["running", "queued"].includes(job.status)).length;
  const readyJobs = state.jobs.filter(job => job.status === "ready").length;
  const selectedJob = state.jobs.find(job => job.id === state.selectedId);
  const globalSelect = $("#globalProjectSelect");
  if (globalSelect && document.activeElement !== globalSelect) {
    const nextSelectHtml = state.jobs.length
      ? state.jobs.map(job => {
          const done = completedPhaseCount(job);
          const total = effectivePhases(job).length;
          return `<option value="${escapeHtml(job.id)}" ${job.id === state.selectedId ? "selected" : ""}>${escapeHtml(job.market || "—")} · ${escapeHtml(job.title)} (${done}/${total})</option>`;
        }).join("")
      : `<option value="">Chưa có dự án</option>`;
    if (state.lastGlobalSelectHtml !== nextSelectHtml) {
      state.lastGlobalSelectHtml = nextSelectHtml;
      globalSelect.innerHTML = nextSelectHtml;
    }
    if (globalSelect.value !== (state.selectedId || "")) globalSelect.value = state.selectedId || "";
  }
  updateSidebarPhaseVisibility(selectedJob);
  if ($("#dashboardTotalJobs")) $("#dashboardTotalJobs").textContent = state.jobs.length;
  if ($("#dashboardActiveJobs")) $("#dashboardActiveJobs").textContent = activeJobs;
  if ($("#dashboardReadyJobs")) $("#dashboardReadyJobs").textContent = readyJobs;
  if ($("#dashboardCurrentProject")) {
    const isPaused = Boolean(selectedJob?.is_paused || selectedJob?.phases?.[selectedJob?.current_phase]?.is_paused);
    const lastErr = selectedJob?.last_error || selectedJob?.phases?.[selectedJob?.current_phase]?.last_error || selectedJob?.phases?.[selectedJob?.current_phase]?.error || "";
    let statusSuffix = "";
    if (isPaused) {
      statusSuffix = ` · ⚠️ Tạm dừng${selectedJob?.pause_warning ? `: ${selectedJob.pause_warning}` : ""}`;
    } else if (lastErr && ["interrupted", "failed"].includes(selectedJob?.status)) {
      statusSuffix = ` · ⚠️ Lỗi: ${lastErr.slice(0, 80)}`;
    }
    $("#dashboardCurrentProject").textContent = selectedJob
      ? `${selectedJob.market || "—"} · ${selectedJob.title}${statusSuffix}`
      : "Chưa có dự án đang chọn";
    if (isPaused) {
      $("#dashboardCurrentProject").style.color = "#ffc96b";
    } else {
      $("#dashboardCurrentProject").style.color = "";
    }
  }
  const nextJobListHtml = state.jobs.length ? state.jobs.map(jobCard).join("") : `<div class="empty-state">Chưa có dự án.</div>`;
  if (state.lastJobListHtml !== nextJobListHtml) {
    state.lastJobListHtml = nextJobListHtml;
    $("#jobList").innerHTML = nextJobListHtml;
    $$('[data-delete-job]').forEach(btn => btn.addEventListener("click", async event => {
      event.preventDefault();
      event.stopPropagation();
      if (btn.disabled) return;
      await deleteJobById(btn.dataset.deleteJob, btn);
    }));
    $$('[data-job]').forEach(el => el.addEventListener("click", async event => {
      if (event.target.closest("[data-delete-job]")) return;
      const previousId = state.selectedId;
      state.selectedId = el.dataset.job;
      state.userPinnedJobId = state.selectedId;
      if (state.autoFollowPipelineJobId && state.autoFollowPipelineJobId !== state.selectedId) {
        state.autoFollowPipelineJobId = null;
      }
      state.detailTab = "tongquan";
      state.lastJobListHtml = "";
      state.lastOverviewDeckHtml = "";
      await renderDetail();
      await renderFunctionWorkspaces();
      await loadJobs(true);
      if (previousId !== state.selectedId) await refreshProducerChatsForSelection();
    }));
  }
  renderOverviewCommandDeck(selectedJob);
  if (!prevSelectedId && state.selectedId && ["script", "voice", "visuals", "footage", "ai_visual", "edit", "seo", "qc"].includes(state.appTab)) {
    renderFunctionWorkspaces().catch(() => {});
  }
}

function renderOverviewCommandDeck(selectedJob) {
  const deck = $("#overviewCommandDeck");
  if (!deck) return;
  if (!state.jobs.length) {
    const emptyHtml = `<div class="overview-empty-deck">
      <div>
        <span>BẮT ĐẦU DỰ ÁN ĐẦU TIÊN</span>
        <h3>Chưa có dự án nào trong xưởng sản xuất</h3>
        <p>Khởi tạo dự án từ gợi ý Radar hoặc nhập chủ đề trực tiếp để bắt đầu dây chuyền sản xuất.</p>
      </div>
      <div class="button-row">
        <button class="primary" type="button" data-open-tab="create">＋ Tạo dự án mới</button>
        <button class="ghost" type="button" data-open-tab="radar">⌕ Quét chủ đề Radar</button>
      </div>
    </div>`;
    if (state.lastOverviewDeckHtml !== emptyHtml) {
      state.lastOverviewDeckHtml = emptyHtml;
      deck.innerHTML = emptyHtml;
      deck.querySelectorAll("[data-open-tab]").forEach(btn => btn.addEventListener("click", () => setAppTab(btn.dataset.openTab)));
    }
    return;
  }

  const job = selectedJob || state.jobs[0];
  const activePhases = effectivePhases(job);
  const doneCount = completedPhaseCount(job);
  const percent = Math.round((doneCount / Math.max(1, activePhases.length)) * 100);
  const nextPhase = nextPendingPhase(job);
  const isBusy = ["running", "queued"].includes(job.status);
  const canResume = !isBusy && job.status !== "completed" && Boolean(nextPhase);
  const currentTab = phaseWorkspaceTab(job.current_phase || nextPhase || "plan") || "script";
  const strategyText = visualStrategyLabel(job).split("·")[0].trim();

  const stepsHtml = activePhases.map((phase, idx) => {
    const info = job.phases?.[phase] || {};
    const status = info.status || "pending";
    const isPaused = Boolean(info.is_paused || (job.is_paused && phase === job.current_phase));
    const statusLabel = (["running", "interrupted"].includes(status) && isPaused)
      ? "Tạm dừng"
      : (statusLabels[status] || status);
    const targetTab = phaseWorkspaceTab(phase) || "projects";
    const runnable = canRun(job, phase);
    return `<article class="overview-step-card ${escapeHtml(status)}${isPaused ? " paused" : ""}" data-overview-open-tab="${escapeHtml(targetTab)}">
      <div class="overview-step-top">
        <span class="overview-step-num">${status === "succeeded" ? "✓" : String(idx + 1).padStart(2, "0")}</span>
        <b class="overview-step-badge ${escapeHtml(status)}">${escapeHtml(statusLabel)}</b>
      </div>
      <strong>${escapeHtml(phaseLabels[phase])}</strong>
      <div class="overview-step-foot">
        <small>Mở bước ↗</small>
        ${runnable ? `<button type="button" class="overview-step-run" data-overview-run-phase="${escapeHtml(phase)}">${status === "pending" ? "▶ Chạy" : "↻ Chạy lại"}</button>` : ""}
      </div>
    </article>`;
  }).join("");

  const projectsRowsHtml = state.jobs.slice(0, 8).map(item => {
    const itemPhases = effectivePhases(item);
    const itemDone = completedPhaseCount(item);
    const itemPct = Math.round((itemDone / Math.max(1, itemPhases.length)) * 100);
    const itemPaused = Boolean(item.is_paused || item.phases?.[item.current_phase]?.is_paused);
    const itemBusy = ["running", "queued"].includes(item.status);
    const itemStateText = itemPaused
      ? "⚠️ Tạm dừng"
      : item.current_phase
        ? phaseLabels[item.current_phase]
        : (statusLabels[item.status] || item.status);
    return `<div class="overview-project-row ${item.id === job.id ? "selected" : ""}" data-overview-select-job="${escapeHtml(item.id)}">
      <div class="overview-project-main">
        <span class="job-market">${escapeHtml(item.market || "—")}</span>
        <div>
          <strong>${escapeHtml(item.title)}</strong>
          <small>${Math.round((item.production_recipe?.target_duration_sec || 300) / 60)} phút · ${item.plan_engine === "gemini" ? "Gemini CLI" : "Codex CLI"} · ${formatBytes(item.storage_bytes)}</small>
        </div>
      </div>
      <div class="overview-project-progress">
        <div class="job-progress"><span style="width:${itemPct}%"></span></div>
        <small>${itemDone}/${itemPhases.length} bước · ${escapeHtml(itemStateText)}</small>
      </div>
      <div class="overview-project-actions">
        <button class="ghost compact" type="button" data-overview-open-project="${escapeHtml(item.id)}">Mở dự án</button>
        <button class="job-delete" type="button" data-overview-delete-job="${escapeHtml(item.id)}" ${itemBusy ? "disabled" : ""}>Xóa</button>
      </div>
    </div>`;
  }).join("");

  const nextDeckHtml = `<div class="overview-deck-grid">
    <section class="overview-console-card">
      <div class="overview-console-head">
        <div>
          <div class="overview-console-kicker">
            <span class="job-market">${escapeHtml(job.market || "KR")}</span>
            <span class="overview-strategy-pill">${escapeHtml(strategyText)}</span>
            <span class="overview-meta-pill">${Math.round((job.production_recipe?.target_duration_sec || 300) / 60)} phút · ${job.plan_engine === "gemini" ? "Gemini CLI" : "Codex CLI"}</span>
            <span class="overview-meta-pill">${formatBytes(job.storage_bytes)}</span>
          </div>
          <h2>${escapeHtml(job.title)}</h2>
          <p class="overview-workspace-path" title="${escapeHtml(job.workspace || "")}">Workspace: ${escapeHtml(job.workspace || "—")}</p>
        </div>
        <div class="overview-console-actions">
          ${canResume ? `<button class="primary" type="button" id="overviewRunFullBtn">⚡ Chạy tự động Full Video</button>` : ""}
          ${canResume ? `<button class="ghost compact" type="button" id="overviewResumeJobBtn">▶ ${escapeHtml(continueButtonLabel(job))}</button>` : ""}
          <button class="ghost compact" type="button" data-open-agent-office="true" title="Mở 🏛️ 15 Phòng Ban Chuyên Môn (15 Tổ trưởng · 15 Tổ phó · 62 Chuyên viên Mini-Agents)">🏛️ 15 Phòng Ban (92 NS)</button>
          <button class="ghost compact" type="button" data-overview-open-tab="${escapeHtml(currentTab)}">Mở bước hiện tại</button>
          <button class="ghost compact" type="button" data-overview-open-tab="projects">Chi tiết & Nhật ký</button>
        </div>
      </div>
      <div class="overview-progress-bar-wrap">
        <div class="overview-progress-labels">
          <span>Tiến độ dây chuyền sản xuất (${doneCount}/${activePhases.length} bước hoàn tất)</span>
          <strong>${percent}%</strong>
        </div>
        <div class="overview-progress-track"><i style="width:${percent}%"></i></div>
      </div>
      <div class="overview-pipeline-grid">${stepsHtml}</div>
    </section>

    <section class="overview-projects-card">
      <div class="overview-projects-head">
        <div>
          <span>DANH SÁCH DỰ ÁN (${state.jobs.length})</span>
          <h3>Chuyển nhanh & Theo dõi hàng đợi</h3>
        </div>
        <div class="button-row">
          <button class="ghost compact" type="button" data-overview-open-tab="projects">Quản lý tất cả</button>
          <button class="primary compact" type="button" data-overview-open-tab="create">＋ Dự án mới</button>
        </div>
      </div>
      <div class="overview-projects-list">${projectsRowsHtml}</div>
    </section>
  </div>`;

  if (state.lastOverviewDeckHtml === nextDeckHtml) return;
  state.lastOverviewDeckHtml = nextDeckHtml;
  deck.innerHTML = nextDeckHtml;

  deck.querySelectorAll("[data-overview-open-tab]").forEach(el => el.addEventListener("click", event => {
    if (event.target.closest("[data-overview-run-phase]")) return;
    setAppTab(el.dataset.overviewOpenTab);
  }));
  deck.querySelectorAll("[data-overview-run-phase]").forEach(btn => btn.addEventListener("click", async event => {
    event.stopPropagation();
    const phase = btn.dataset.overviewRunPhase;
    const status = job.phases?.[phase]?.status;
    const url = status && status !== "pending"
      ? `/api/jobs/${encodeURIComponent(job.id)}/rerun/${phase}`
      : `/api/jobs/${encodeURIComponent(job.id)}/run/${phase}`;
    try {
      state.userPinnedJobId = null;
      state.selectedId = job.id;
      state.autoFollowPipelineJobId = job.id;
      state.lastFollowedPhaseKey = `${job.id}:${phase}`;
      const targetTab = phaseWorkspaceTab(phase);
      if (targetTab) setAppTab(targetTab);
      await api(url, { method: "POST" });
      toast(`Đã bắt đầu: ${phaseLabels[phase]}`);
      await refreshAll();
    } catch (err) { toast(err.message, true); }
  }));
  deck.querySelector("#overviewRunFullBtn")?.addEventListener("click", async () => {
    try {
      await runFullPipeline(job);
    } catch (err) { toast(err.message, true); }
  });
  deck.querySelector("#overviewResumeJobBtn")?.addEventListener("click", async () => {
    try {
      const phase = nextPendingPhase(job);
      state.userPinnedJobId = null;
      state.selectedId = job.id;
      state.autoFollowPipelineJobId = job.id;
      state.lastFollowedPhaseKey = `${job.id}:${phase}`;
      const targetTab = phaseWorkspaceTab(phase);
      if (targetTab) setAppTab(targetTab);
      await api(`/api/jobs/${encodeURIComponent(job.id)}/resume`, { method: "POST" });
      toast(phase ? `Đã bắt đầu bước: ${phaseLabels[phase]}` : "Dự án đã hoàn tất.");
      await refreshAll();
    } catch (err) { toast(err.message, true); }
  });
  deck.querySelectorAll("[data-overview-delete-job]").forEach(btn => btn.addEventListener("click", async event => {
    event.preventDefault();
    event.stopPropagation();
    if (btn.disabled) return;
    await deleteJobById(btn.dataset.overviewDeleteJob, btn);
  }));
  deck.querySelectorAll("[data-overview-select-job]").forEach(row => row.addEventListener("click", async event => {
    if (event.target.closest("[data-overview-open-project], [data-overview-delete-job]")) return;
    const nextId = row.dataset.overviewSelectJob;
    if (!nextId || nextId === state.selectedId) return;
    state.selectedId = nextId;
    state.userPinnedJobId = nextId;
    if (state.autoFollowPipelineJobId && state.autoFollowPipelineJobId !== nextId) {
      state.autoFollowPipelineJobId = null;
    }
    state.lastJobListHtml = "";
    state.lastOverviewDeckHtml = "";
    await loadJobs(true);
    await renderDetail();
    await renderFunctionWorkspaces();
    await refreshProducerChatsForSelection();
  }));
  deck.querySelectorAll("[data-overview-open-project]").forEach(btn => btn.addEventListener("click", async event => {
    event.stopPropagation();
    const nextId = btn.dataset.overviewOpenProject;
    if (nextId) {
      state.selectedId = nextId;
      state.userPinnedJobId = nextId;
      if (state.autoFollowPipelineJobId && state.autoFollowPipelineJobId !== nextId) {
        state.autoFollowPipelineJobId = null;
      }
    }
    state.detailTab = "tongquan";
    state.lastJobListHtml = "";
    state.lastOverviewDeckHtml = "";
    await loadJobs(true);
    await renderDetail();
    await renderFunctionWorkspaces();
    setAppTab("projects");
  }));
}

function canRun(job, phase) {
  if (["running", "queued"].includes(job.status)) return false;
  const active = effectivePhases(job);
  const index = active.indexOf(phase);
  if (index < 0) return false;
  return active.slice(0, index).every(p => job.phases?.[p]?.status === "succeeded");
}

function pipelineHtml(job) {
  const active = effectivePhases(job);
  return `<div class="pipeline-strip">${active.map((phase, index) => {
    const info = job.phases?.[phase] || {};
    const status = info.status || "pending";
    const isPhasePaused = Boolean(info.is_paused || (job.is_paused && phase === job.current_phase));
    const statusText = (["running", "interrupted"].includes(status) && isPhasePaused)
      ? "⚠️ Tạm dừng"
      : (statusLabels[status] || status);
    const displayError = info.error || info.pause_warning || (isPhasePaused ? (job.pause_warning || "Tạm dừng") : "");
    const targetTab = phaseWorkspaceTab(phase) || "projects";
    return `<div class="pipe-step ${escapeHtml(status)}${isPhasePaused ? " paused" : ""}" data-pipe-open-tab="${escapeHtml(targetTab)}" style="cursor:pointer;">
      <div class="pipe-index">${status === "succeeded" ? "✓" : index + 1}</div>
      <div><strong>${phaseLabels[phase]}</strong><span>${escapeHtml(statusText)}</span></div>
      ${displayError ? `<small title="${escapeHtml(displayError)}">${escapeHtml(displayError)}</small>` : ""}
      ${canRun(job, phase) ? `<button type="button" data-run-phase="${phase}">${status === "pending" ? "▶ Chạy" : "↻ Chạy lại"}</button>` : ""}
    </div>`;
  }).join("")}</div>`;
}

function detailTabs() {
  const tabs = [
    ["tongquan", "Tổng quan"], ["nhatky", "Nhật ký"],
  ];
  return `<div class="detail-tabs">${tabs.map(([id, label]) => `<button class="${state.detailTab === id ? "active" : ""}" data-detail-tab="${id}">${label}</button>`).join("")}</div>`;
}

async function artifact(jobId, name) {
  try { return await api(`/api/jobs/${encodeURIComponent(jobId)}/artifact/${encodeURIComponent(name)}`); }
  catch (_) { return ""; }
}

async function liveFootage(jobId) {
  try { return await api(`/api/jobs/${encodeURIComponent(jobId)}/live-footage`); }
  catch (_) { return { count: 0, items: [] }; }
}

function codeViewer(title, content, empty = "Chưa có dữ liệu ở bước này.") {
  const hasContent = Boolean(content && String(content).trim().length > 0);
  const readerBtnHtml = hasContent
    ? (() => {
        const key = registerStudioReaderPayload({
          badge: "🗂️",
          title: String(title || "Tài liệu kỹ thuật"),
          subtitle: "Chế độ đọc tập trung · 15 Phòng Ban Chuyên Môn",
          rawText: String(content),
          isCode: /\.(json|srt|vtt)$/i.test(String(title || "")) || /manifest|json/i.test(String(title || "")),
        });
        return `<div class="artifact-head-actions"><button type="button" class="ghost compact" data-studio-reader-key="${key}">🗗 Đọc Popup</button></div>`;
      })()
    : "";
  return `<section class="artifact-card"><div class="artifact-head"><strong>${escapeHtml(title)}</strong>${readerBtnHtml}</div><pre>${hasContent ? escapeHtml(content) : escapeHtml(empty)}</pre></section>`;
}

const voiceLocales = {
  vi: { label: "Việt Nam", langLabel: "Tiếng Việt", flag: "🇻🇳" },
  en: { label: "Mỹ / Anh", langLabel: "English", flag: "🇺🇸" },
  ko: { label: "Hàn Quốc", langLabel: "한국어", flag: "🇰🇷" },
  ja: { label: "Nhật Bản", langLabel: "日本語", flag: "🇯🇵" },
  zh: { label: "Trung Quốc", langLabel: "中文", flag: "🇨🇳" },
  fr: { label: "Pháp", langLabel: "Français", flag: "🇫🇷" },
  de: { label: "Đức", langLabel: "Deutsch", flag: "🇩🇪" },
  es: { label: "Tây Ban Nha", langLabel: "Español", flag: "🇪🇸" },
  ru: { label: "Nga", langLabel: "Русский", flag: "🇷🇺" },
  th: { label: "Thái Lan", langLabel: "ไทย", flag: "🇹🇭" },
};

function selectedProjectLabel(job) {
  return job ? `${job.market} · ${job.title}` : "Chưa chọn dự án";
}

function producerChatHistoryUrl() {
  const params = new URLSearchParams();
  if (state.selectedId) params.set("selected_job_id", state.selectedId);
  const query = params.toString();
  return `/api/producer-chat${query ? `?${query}` : ""}`;
}

async function refreshProducerChatsForSelection() {
  if (state.globalCodexOpen) {
    await renderGlobalProducerChat({ loadHistory: true });
    return;
  }
  await refreshGlobalCodexContext().catch(() => {});
}

async function clearCurrentProducerChatHistory() {
  const job = state.jobs.find(item => item.id === state.selectedId);
  const scopeLabel = job ? `dự án “${job.title}”` : "AI chung";
  if (!window.confirm(`Xóa toàn bộ lịch sử chat của ${scopeLabel}?`)) return;
  await api(producerChatHistoryUrl(), { method: "DELETE" });
  if (state.globalCodexOpen) await renderGlobalProducerChat({ loadHistory: true });
  if (state.appTab === "codex") await renderProducerChat();
  toast(`Đã xóa lịch sử chat của ${scopeLabel}.`);
}

async function startNewProducerChatSession() {
  const payload = { selected_job_id: state.selectedId || null };
  const result = await api("/api/producer-chat/new", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  const history = result?.history || [];
  setChatMessagesHtmlIfChanged($("#globalCodexMessages"), history, { force: true });
  setChatMessagesHtmlIfChanged($("#producerCodexMessages"), history, { force: true });
  toast(result?.reply || "Đã mở phiên Antigravity mới.");
}

async function compactCurrentProducerChatSession() {
  const payload = { selected_job_id: state.selectedId || null };
  toast("Đang nén ngữ cảnh phiên Antigravity…");
  const result = await api("/api/producer-chat/compact", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  const history = result?.history || [];
  setChatMessagesHtmlIfChanged($("#globalCodexMessages"), history, { force: true });
  setChatMessagesHtmlIfChanged($("#producerCodexMessages"), history, { force: true });
  toast("Đã nén ngữ cảnh (/compact) thành công.");
}

function selectedAiLabel() {
  const modelId = currentChatModelId();
  if (modelId === "codex") return "Codex (GPT-5.4)";
  return humanizeAntigravityModel(modelId);
}

function shortenAntigravityPathLabel(rawLabel = "", maxLen = 36) {
  const clean = String(rawLabel || "").trim();
  if (!clean) return "";
  const normalized = clean.replace(/\\/g, "/");
  if (!normalized.includes("/")) return clean;
  if (clean.length <= maxLen) return clean;
  const parts = normalized.split("/").filter(Boolean);
  if (!parts.length) return clean;
  const tail2 = parts.slice(-2).join("/");
  if (tail2.length <= maxLen) return parts.length > 2 ? `…/${tail2}` : tail2;
  return parts[parts.length - 1];
}

function formatInlineAntigravityMarkdown(escapedText) {
  let out = String(escapedText || "");
  const linkPlaceholders = [];

  out = out.replace(/\[([^\]]+)\]\(((?:https?:\/\/|\/|file:\/\/\/)[^\s)]+)\)/g, (_, rawLabel, rawHref) => {
    const idx = linkPlaceholders.length;
    const strippedLabel = String(rawLabel || "").replace(/^`+|`+$/g, "").trim();
    const isFileLink = /^file:\/\/\//i.test(rawHref)
      || rawHref.startsWith("/")
      || /\.[a-z0-9]{1,6}(?:#L\d+(?:-L?\d+)?)?$/i.test(strippedLabel);
    if (isFileLink) {
      let fullTitle = rawHref
        .replace(/&amp;/g, "&")
        .replace(/&quot;/g, '"')
        .replace(/&#39;/g, "'");
      try {
        fullTitle = decodeURIComponent(fullTitle.replace(/^file:\/\/\/?/i, ""));
      } catch (_) {}
      const lineAnchor = (rawHref.match(/#L(\d+(?:-L?\d+)?)$/i) || [])[1] || "";
      const baseDisplay = shortenAntigravityPathLabel(strippedLabel, 34);
      const hasLineInLabel = /(?:#L|:)\d+/i.test(baseDisplay);
      const displayLabel = lineAnchor && !hasLineInLabel
        ? `${baseDisplay}:${lineAnchor.replace(/L/gi, "")}`
        : baseDisplay;
      linkPlaceholders.push(
        `<a href="${rawHref}" target="_blank" rel="noopener noreferrer" class="agy-md-link agy-file-chip" title="${escapeHtml(fullTitle)}">${displayLabel}</a>`
      );
    } else {
      linkPlaceholders.push(
        `<a href="${rawHref}" target="_blank" rel="noopener noreferrer" class="agy-md-link">${strippedLabel}</a>`
      );
    }
    return `@@AGY_INLINE_LINK_${idx}@@`;
  });

  out = out.replace(/`([^`\n]+)`/g, (_, rawCode) => {
    const trimmedCode = String(rawCode || "").trim();
    const looksLikeLongPath = trimmedCode.length > 38 && (trimmedCode.includes("/") || trimmedCode.includes("\\"));
    if (looksLikeLongPath) {
      const shortPath = shortenAntigravityPathLabel(trimmedCode, 34);
      return `<code class="agy-inline-code is-path" title="${trimmedCode}">${shortPath}</code>`;
    }
    return `<code class="agy-inline-code">${rawCode}</code>`;
  });

  out = out.replace(/\*\*([^*\n]+)\*\*/g, "<strong>$1</strong>");
  out = out.replace(/(^|[\s(])\*([^*\n]+)\*(?=[\s).,!?:;]|$)/g, "$1<em>$2</em>");
  out = out.replace(/@@AGY_INLINE_LINK_(\d+)@@/g, (_, idx) => linkPlaceholders[Number(idx)] || "");
  return out;
}

function renderCofiProposalCardHtml(proposal = {}) {
  if (!proposal || typeof proposal !== "object") return "";
  const brief = proposal.creative_brief && typeof proposal.creative_brief === "object"
    ? { ...proposal.creative_brief, ...proposal }
    : proposal;
  const chapters = Array.isArray(proposal.outline)
    ? proposal.outline
    : Array.isArray(proposal.outline?.chapters)
      ? proposal.outline.chapters
      : Array.isArray(proposal.chapters)
        ? proposal.chapters
        : [];
  const encoded = encodeURIComponent(JSON.stringify(proposal));
  const title = proposal.title || proposal.name || "Phương án Sáng tạo & Dàn ý Đề xuất";
  const angleLabel = humanizeCreativeKey("narrative_angles", brief.narrative_angle || "Giải phẫu Hồ sơ Điều tra");
  const styleLabel = humanizeCreativeKey("writing_styles", brief.writing_style || "Lạnh lùng, Đanh thép, Dữ liệu thật");
  const hookLabel = humanizeCreativeKey("hook_archetypes", brief.hook_archetype || "Con số / Sự thật Phi lý gây sốc");
  const archetypes = parseEditingArchetypesValue(brief.editing_archetypes || brief.editing_grammar);
  const rulesText = brief.custom_rules || proposal.notes || proposal.why_it_works || "";
  if (state.appTab === "create" || !state.selectedId) {
    const draftSig = JSON.stringify({
      title: proposal.title || "",
      angle: brief.narrative_angle || "",
      style: brief.writing_style || "",
      hook: brief.hook_archetype || "",
      opening: brief.opening_hook || "",
      chapters: chapters.length,
    });
    if (draftSig !== state.lastSyncedUiDraftSig) {
      state.lastSyncedUiDraftSig = draftSig;
      queueMicrotask(() => applyCreativeProposalToCreateForm(proposal, { switchTab: false, silent: true }));
    }
  }
  return `<div class="cofi-proposal-card" data-cofi-proposal="${encoded}">
    <div class="cofi-proposal-head">
      <span class="cofi-proposal-eyebrow"><i class="agy-sparkle">✦</i> ĐÃ ĐỒNG BỘ TRỰC TIẾP LÊN MÀN HÌNH · LIVE CREATIVE BRIEF</span>
      ${brief.playbook_id ? `<span class="cofi-proposal-badge">Playbook: ${escapeHtml(brief.playbook_id)}</span>` : ""}
    </div>
    <strong class="cofi-proposal-title">${escapeHtml(title)}</strong>
    <div class="cofi-proposal-tags">
      <span>${escapeHtml(angleLabel)}</span>
      <span>${escapeHtml(styleLabel)}</span>
      <span>${escapeHtml(hookLabel)}</span>
      ${archetypes.map(k => `<span class="archetype-tag">${escapeHtml(humanizeCreativeKey("editing_archetypes", k))}</span>`).join("")}
    </div>
    ${brief.opening_hook ? `<blockquote class="cofi-proposal-hook"><span>Hook mở đầu 30s:</span> “${escapeHtml(brief.opening_hook)}”</blockquote>` : ""}
    ${rulesText ? `<p class="cofi-proposal-rules"><b>Chỉ dẫn đạo diễn / Luật riêng:</b> ${escapeHtml(rulesText)}</p>` : ""}
    ${chapters.length ? `
      <div class="cofi-proposal-chapters">
        <span>Dàn ý Chương hồi (${chapters.length} chương):</span>
        <ol>
          ${chapters.map(ch => `<li><b>${escapeHtml(ch.title || ch.chapter_title || "Chương")}:</b> ${escapeHtml(ch.summary || ch.goal_or_question || "")}${ch.evidence_anchor ? ` <em>[Bằng chứng: ${escapeHtml(ch.evidence_anchor)}]</em>` : ""}</li>`).join("")}
        </ol>
      </div>
    ` : ""}
    <div class="cofi-proposal-sync-note">
      <small>✦ Phương án đã tự động điền lên màn hình bên trái. Nhắn <b>"Đồng ý"</b> / <b>"Chốt"</b> trong chat để AI lập tức tạo dự án & viết kịch bản, hoặc nhắn chỉnh sửa bất kỳ chi tiết nào.</small>
    </div>
  </div>`;
}

function splitAntigravityMarkdownTableRow(rowLine = "") {
  let clean = String(rowLine || "").trim();
  if (clean.startsWith("|")) clean = clean.slice(1);
  if (clean.endsWith("|")) clean = clean.slice(0, -1);
  return clean.split("|").map(cell => cell.trim());
}

function renderAntigravityMarkdown(rawText = "") {
  const source = String(rawText || "").replace(/\r\n/g, "\n").trim();
  if (!source) return "";
  const codeBlocks = [];
  const withPlaceholders = source.replace(/```([a-zA-Z0-9_+-]*)\n?([\s\S]*?)```/g, (_, lang, code) => {
    const idx = codeBlocks.length;
    const cleanLang = String(lang || "text").trim() || "text";
    const trimmedCode = String(code || "").replace(/\n$/, "");
    const lowerLang = cleanLang.toLowerCase();
    if (["cofi-proposal", "cofi_proposal", "cofi-draft", "cofi_draft", "proposal"].includes(lowerLang)) {
      const parsedProposal = safeJson(trimmedCode, null);
      if (parsedProposal && typeof parsedProposal === "object") {
        codeBlocks.push(renderCofiProposalCardHtml(parsedProposal));
        return `\n@@AGY_CODE_BLOCK_${idx}@@\n`;
      }
    }
    codeBlocks.push(
      `<div class="agy-code-block"><div class="agy-code-header"><span>${escapeHtml(cleanLang)}</span><button type="button" class="agy-code-copy" data-copy-code="1">Sao chép</button></div><pre><code>${escapeHtml(trimmedCode)}</code></pre></div>`
    );
    return `\n@@AGY_CODE_BLOCK_${idx}@@\n`;
  });

  const lines = withPlaceholders.split("\n");
  const blocks = [];
  let listType = null;
  let listItems = [];
  let paragraphLines = [];

  const flushList = () => {
    if (!listType || !listItems.length) {
      listType = null;
      listItems = [];
      return;
    }
    blocks.push(`<${listType} class="agy-md-list">${listItems.join("")}</${listType}>`);
    listType = null;
    listItems = [];
  };
  const flushParagraph = () => {
    if (!paragraphLines.length) return;
    blocks.push(`<p>${paragraphLines.map(line => formatInlineAntigravityMarkdown(escapeHtml(line))).join("<br>")}</p>`);
    paragraphLines = [];
  };
  const nextNonEmptyLine = (startIndex) => {
    for (let k = startIndex; k < lines.length; k++) {
      if (lines[k].trim()) return lines[k];
    }
    return "";
  };

  for (let i = 0; i < lines.length; i++) {
    const rawLine = lines[i];
    const trimmed = rawLine.trim();
    const codeMatch = trimmed.match(/^@@AGY_CODE_BLOCK_(\d+)@@$/);
    if (codeMatch) {
      flushParagraph();
      flushList();
      blocks.push(codeBlocks[Number(codeMatch[1])] || "");
      continue;
    }
    if (!trimmed) {
      flushParagraph();
      if (listType) {
        const upcoming = nextNonEmptyLine(i + 1);
        const upcomingIsList = /^\s*(?:[-*•]|\d+[.)])\s+/.test(upcoming);
        if (!upcomingIsList) flushList();
      }
      continue;
    }

    // Markdown Table block: Header row | ... | followed by | --- | --- |
    if (
      trimmed.includes("|")
      && i + 1 < lines.length
      && /^\s*\|?\s*:?-{2,}:?(?:\s*\|\s*:?-{2,}:?)+\s*\|?\s*$/.test(lines[i + 1])
    ) {
      flushParagraph();
      flushList();
      const headers = splitAntigravityMarkdownTableRow(trimmed);
      i += 2;
      const bodyRows = [];
      while (i < lines.length) {
        const rowTrim = lines[i].trim();
        if (!rowTrim || !rowTrim.includes("|") || /^@@AGY_CODE_BLOCK_\d+@@$/.test(rowTrim)) break;
        bodyRows.push(splitAntigravityMarkdownTableRow(rowTrim));
        i += 1;
      }
      i -= 1;
      const colCount = Math.max(headers.length, 1);
      const theadHtml = `<thead><tr>${headers.map(h => `<th>${formatInlineAntigravityMarkdown(escapeHtml(h))}</th>`).join("")}</tr></thead>`;
      const tbodyHtml = bodyRows.length
        ? `<tbody>${bodyRows.map(cols => {
            const padded = Array.from({ length: colCount }, (_, cIdx) => cols[cIdx] ?? "");
            return `<tr>${padded.map(cell => `<td>${formatInlineAntigravityMarkdown(escapeHtml(cell))}</td>`).join("")}</tr>`;
          }).join("")}</tbody>`
        : "";
      blocks.push(`<div class="agy-md-table-wrap"><table class="agy-md-table">${theadHtml}${tbodyHtml}</table></div>`);
      continue;
    }

    const headingMatch = trimmed.match(/^(#{1,4})\s+(.+)$/);
    if (headingMatch) {
      flushParagraph();
      flushList();
      const level = Math.min(4, headingMatch[1].length + 1);
      blocks.push(`<h${level} class="agy-md-heading agy-h${level}">${formatInlineAntigravityMarkdown(escapeHtml(headingMatch[2]))}</h${level}>`);
      continue;
    }

    // Promote standalone bold numbered headers (e.g., "**1. Tiêu đề mục**") into crisp section headings
    const boldNumHeadingMatch = trimmed.match(/^\*\*(\d+[\.\)]\s+[^*\n]+?)\*\*:?$/);
    if (boldNumHeadingMatch) {
      flushParagraph();
      flushList();
      blocks.push(`<h3 class="agy-md-heading agy-h3">${formatInlineAntigravityMarkdown(escapeHtml(boldNumHeadingMatch[1]))}</h3>`);
      continue;
    }

    if (/^---+$/.test(trimmed)) {
      flushParagraph();
      flushList();
      blocks.push('<hr class="agy-md-hr">');
      continue;
    }

    // Multi-line Blockquote & Callouts (> [!NOTE], > [!IMPORTANT], > [!WARNING], > [!TIP])
    const quoteMatch = trimmed.match(/^>\s?(.*)$/);
    if (quoteMatch) {
      flushParagraph();
      flushList();
      const quoteLines = [quoteMatch[1]];
      while (i + 1 < lines.length) {
        const nextQm = lines[i + 1].trim().match(/^>\s?(.*)$/);
        if (!nextQm) break;
        quoteLines.push(nextQm[1]);
        i += 1;
      }
      const alertMatch = (quoteLines[0] || "").match(/^\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]\s*(.*)$/i);
      if (alertMatch) {
        const kind = alertMatch[1].toLowerCase();
        const alertLabels = {
          note: "Ghi chú",
          tip: "Mẹo tối ưu",
          important: "Quan trọng",
          warning: "Lưu ý",
          caution: "Cảnh báo",
        };
        const inlineRemainder = (alertMatch[2] || "").trim();
        const restLines = quoteLines.slice(1).filter(Boolean);
        let titleTail = "";
        let bodyLines = restLines;
        if (inlineRemainder) {
          if (restLines.length > 0 && inlineRemainder.length <= 48) {
            titleTail = ` · ${formatInlineAntigravityMarkdown(escapeHtml(inlineRemainder))}`;
          } else {
            bodyLines = [inlineRemainder, ...restLines];
          }
        }
        const bodyHtml = bodyLines.length
          ? `<div class="agy-callout-body">${bodyLines.map(ql => formatInlineAntigravityMarkdown(escapeHtml(ql))).join("<br>")}</div>`
          : "";
        blocks.push(
          `<blockquote class="agy-md-quote is-callout is-${kind}"><div class="agy-callout-title">${escapeHtml(alertLabels[kind] || alertMatch[1])}${titleTail}</div>${bodyHtml}</blockquote>`
        );
      } else {
        const quoteHtml = quoteLines
          .map(ql => (ql.trim() ? formatInlineAntigravityMarkdown(escapeHtml(ql)) : ""))
          .filter(Boolean)
          .join("<br>");
        blocks.push(`<blockquote class="agy-md-quote">${quoteHtml}</blockquote>`);
      }
      continue;
    }

    const indent = (rawLine.match(/^(\s*)/)?.[1] || "").replace(/\t/g, "  ").length;
    const ulMatch = rawLine.match(/^\s*[-*•]\s+(.+)$/);
    const olMatch = rawLine.match(/^\s*(\d+)[.)]\s+(.+)$/);

    if ((ulMatch || olMatch) && indent >= 2 && listType) {
      flushParagraph();
      const subBody = ulMatch ? ulMatch[1] : olMatch[2];
      listItems.push(`<li class="agy-sub-li">${formatInlineAntigravityMarkdown(escapeHtml(subBody))}</li>`);
      continue;
    }
    if (ulMatch) {
      flushParagraph();
      if (listType && listType !== "ul") flushList();
      listType = "ul";
      listItems.push(`<li>${formatInlineAntigravityMarkdown(escapeHtml(ulMatch[1]))}</li>`);
      continue;
    }
    if (olMatch) {
      flushParagraph();
      if (listType && listType !== "ol") flushList();
      listType = "ol";
      const itemNum = Number(olMatch[1]) || (listItems.length + 1);
      listItems.push(`<li value="${itemNum}">${formatInlineAntigravityMarkdown(escapeHtml(olMatch[2]))}</li>`);
      continue;
    }
    flushList();
    paragraphLines.push(rawLine);
  }
  flushParagraph();
  flushList();
  return blocks.join("");
}

function humanizeToolStepTitle(step = {}) {
  if (step.tool_action) return String(step.tool_action);
  if (step.tool_summary) return String(step.tool_summary);
  const tool = String(step.tool_name || step.kind || "").toLowerCase();
  if (tool === "run_command" || tool === "command") return "Running command";
  if (tool === "view_file" || tool === "read_file") return "Viewing file";
  if (tool === "replace_file_content" || tool === "multi_replace_file_content" || tool === "write_to_file") return "Editing file";
  if (tool === "grep_search" || tool === "find_by_name") return "Searching codebase";
  if (tool === "search_web" || tool === "read_url_content") return "Searching web";
  return step.tool_name || "Tool step";
}

function formatCompactStepTarget(rawTarget = "") {
  const clean = String(rawTarget || "").trim();
  if (!clean) return "";
  if (/^[a-zA-Z]:[\\/]/.test(clean) || clean.startsWith("/") || clean.includes("\\")) {
    const parts = clean.replace(/\\/g, "/").split("/").filter(Boolean);
    return parts.slice(-2).join("/");
  }
  const singleLine = clean.replace(/\s+/g, " ");
  return singleLine.length > 56 ? `${singleLine.slice(0, 54)}…` : singleLine;
}

function buildAntigravityStepEntries(steps = [], { live = false } = {}) {
  if (!Array.isArray(steps) || !steps.length) {
    return { entries: [], totalDur: 0, toolCount: 0, thoughtCount: 0, lastActiveTitle: "" };
  }
  let totalDur = 0;
  let toolCount = 0;
  let thoughtCount = 0;
  let lastActiveTitle = "";

  const entries = steps.map((step, idx) => {
    const stepType = String(step.step_type || step.kind || "").toLowerCase();
    const stateStr = String(step.state || (live && idx === steps.length - 1 ? "running" : "done")).toLowerCase();
    const isRunning = stateStr.includes("running") || stateStr.includes("pending") || stateStr.includes("progress");
    const isError = stateStr.includes("error") || stateStr.includes("fail");
    const dur = Number(step.duration_seconds || 0);
    if (dur > 0) totalDur += dur;
    const durText = dur > 0 ? `${dur < 10 ? dur.toFixed(1) : Math.round(dur)}s` : "";
    const durBadge = durText ? `<span class="agy-step-duration">${durText}</span>` : "";
    const stepKey = step.step_index != null ? `${stepType || "step"}-${step.step_index}` : `idx-${idx}`;

    if (step.thinking || stepType === "thought" || (stepType === "agent_response" && step.thinking)) {
      thoughtCount += 1;
      const thoughtLabel = isRunning
        ? "Đang suy luận…"
        : durText
          ? `Suy luận · ${durText}`
          : "Suy luận";
      if (isRunning) lastActiveTitle = thoughtLabel;
      const rawThought = String(step.thinking || step.message || "");
      const sig = `thought|${isRunning ? "1" : "0"}|${durText}|${rawThought}`;
      const html = `<details class="agy-thought-block ${isRunning ? "running" : "done"}" data-step-key="${escapeHtml(stepKey)}" data-step-sig="${escapeHtml(sig)}">
        <summary class="agy-thought-summary">
          <span class="agy-thought-icon">${isRunning ? "◌" : "✦"}</span>
          <span class="agy-thought-title">${escapeHtml(thoughtLabel)}</span>
          ${durBadge}
        </summary>
        <div class="agy-thought-content">${renderAntigravityMarkdown(rawThought)}</div>
      </details>`;
      return { key: stepKey, sig, html };
    }

    if (stepType === "tool" || stepType === "command" || step.tool_name) {
      toolCount += 1;
      const title = humanizeToolStepTitle(step);
      const target = String(step.target || step.message || "").trim();
      const shortTarget = formatCompactStepTarget(target);
      const output = String(step.output || "").trim();
      const statusClass = isRunning ? "running" : isError ? "error" : "done";
      const statusIcon = isError ? "✕" : isRunning ? "●" : "✓";
      if (isRunning || idx === steps.length - 1) lastActiveTitle = title;
      const hasDetails = Boolean(output || (target && target.length > 48));
      const sig = `tool|${statusClass}|${title}|${target}|${output}|${durText}`;
      if (!hasDetails) {
        const html = `<div class="agy-tool-step ${statusClass}" data-step-key="${escapeHtml(stepKey)}" data-step-sig="${escapeHtml(sig)}">
          <div class="agy-tool-summary">
            <span class="agy-tool-status ${statusClass}">${statusIcon}</span>
            <strong class="agy-tool-title">${escapeHtml(title)}</strong>
            ${shortTarget ? `<code class="agy-tool-target" title="${escapeHtml(target)}">${escapeHtml(shortTarget)}</code>` : ""}
            ${durBadge}
          </div>
        </div>`;
        return { key: stepKey, sig, html };
      }
      const html = `<details class="agy-tool-step expandable ${statusClass}" data-step-key="${escapeHtml(stepKey)}" data-step-sig="${escapeHtml(sig)}">
        <summary class="agy-tool-summary">
          <span class="agy-tool-status ${statusClass}">${statusIcon}</span>
          <strong class="agy-tool-title">${escapeHtml(title)}</strong>
          ${shortTarget ? `<code class="agy-tool-target" title="${escapeHtml(target)}">${escapeHtml(shortTarget)}</code>` : ""}
          ${durBadge}
        </summary>
        <div class="agy-tool-body">
          ${target ? `<div class="agy-tool-target-full"><span>Target / Command</span><code>${escapeHtml(target)}</code></div>` : ""}
          ${output ? `<pre class="agy-tool-output">${escapeHtml(output)}</pre>` : ""}
        </div>
      </details>`;
      return { key: stepKey, sig, html };
    }
    return null;
  }).filter(Boolean);

  return { entries, totalDur, toolCount, thoughtCount, lastActiveTitle };
}

const agyTurnReaderStore = new Map();

function extractAntigravityTurnHeadline(rawContent = "") {
  const lines = String(rawContent || "").replace(/\r\n/g, "\n").split("\n");
  for (const line of lines) {
    const t = line.trim();
    if (!t || t.startsWith("```") || t.startsWith("|") || t === "---") continue;
    const cleaned = t
      .replace(/^#{1,5}\s+/, "")
      .replace(/^\*\*([^*]+)\*\*:?$/, "$1")
      .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
      .replace(/[*`>_]/g, "")
      .trim();
    if (cleaned.length >= 4) {
      return cleaned.length > 72 ? `${cleaned.slice(0, 70)}…` : cleaned;
    }
  }
  return "Phản hồi chi tiết từ Antigravity";
}

function renderAntigravityStepsHtml(steps = [], { live = false } = {}) {
  const { entries, totalDur, toolCount, lastActiveTitle } = buildAntigravityStepEntries(steps, { live });
  if (!entries.length) return "";
  const totalCount = entries.length;
  const durText = totalDur > 0 ? `${totalDur < 10 ? totalDur.toFixed(1) : Math.round(totalDur)}s` : "";
  const groupTitle = live
    ? (lastActiveTitle ? `Đang chạy: ${lastActiveTitle}` : `Đang thực thi (${totalCount} bước)…`)
    : `Đã thực hiện ${totalCount} bước${toolCount ? ` (${toolCount} tác vụ)` : ""}`;
  const openAttr = live ? " open" : "";
  return `<details class="agy-step-group ${live ? "is-live" : "is-done"}"${openAttr}>
    <summary class="agy-step-group-summary">
      ${live ? '<i class="agy-pulse-dot agy-step-live-dot"></i>' : ""}
      <span class="agy-step-group-chevron">▸</span>
      <span class="agy-step-group-title">${escapeHtml(groupTitle)}</span>
      <span class="agy-step-group-meta"${durText ? "" : ' style="display:none"'}>${escapeHtml(durText)}</span>
    </summary>
    <div class="agy-steps-container">${entries.map(item => item.html).join("")}</div>
  </details>`;
}

function producerChatMessagesHtml(history = []) {
  const activeModelId = currentChatModelId();
  const modelLabel = humanizeAntigravityModel(activeModelId);
  if (!history.length) {
    return `<div class="producer-codex-empty agy-empty-state">
      <div class="agy-empty-badge"><span class="agy-sparkle">✦</span><span>Antigravity Creative Producer</span></div>
      <strong>${escapeHtml(modelLabel)}</strong>
      <p>Cùng bàn luận ý tưởng trực tiếp tại đây — AI tự động đồng bộ Góc nhìn, Văn phong, Hook 30s và Dàn ý lên màn hình bên trái. Khi bạn nhắn "Chốt", AI tạo dự án và triển khai ngay.</p>
      <div class="agy-quick-prompts">
        <button type="button" class="agy-quick-prompt" data-quick-prompt="Hãy cùng tôi bàn ý tưởng mới: đề xuất góc nhìn đột phá, văn phong, Hook 30s đầu và dàn ý chương hồi cho chủ đề này">✨ Bàn ý tưởng & Lên phương án</button>
        <button type="button" class="agy-quick-prompt" data-quick-prompt="Đồng ý phương án này, chốt tạo dự án và bắt đầu viết kịch bản ngay">🚀 Chốt phương án & Tạo dự án</button>
        <button type="button" class="agy-quick-prompt" data-quick-prompt="Duyệt bước hiện tại và chuyển sang chạy bước tiếp theo">✓ Duyệt bước & Chạy tiếp</button>
        <button type="button" class="agy-quick-prompt" data-quick-prompt="Phân tích kịch bản hiện tại, nâng cấp nhịp kể chuyện và bổ sung cliffhanger">✍️ Nâng cấp kịch bản</button>
      </div>
    </div>`;
  }
  return history.map((item, idx) => {
    const isUser = item.role === "user";
    if (isUser) {
      return `<div class="producer-codex-message user agy-msg-user">
        ${item.content ? `<div class="agy-user-text">${escapeHtml(item.content).replace(/\n/g, "<br>")}</div>` : ""}
        ${chatAttachmentGalleryHtml(item.attachments || [])}
      </div>`;
    }
    const itemModelLabel = item.model ? humanizeAntigravityModel(item.model) : modelLabel;
    const itemMode = item.mode === "goal" ? "Goal" : "Agent";
    const stepsHtml = renderAntigravityStepsHtml(item.steps || [], { live: false });
    const rawContent = String(item.content || "");
    const markdownHtml = rawContent ? `<div class="agy-markdown-body">${renderAntigravityMarkdown(rawContent)}</div>` : "";
    let footerHtml = "";
    if (rawContent.trim()) {
      const turnKey = `agy-turn-${idx}-${rawContent.length}`;
      if (agyTurnReaderStore.size > 240) {
        const oldest = agyTurnReaderStore.keys().next().value;
        if (oldest) agyTurnReaderStore.delete(oldest);
      }
      agyTurnReaderStore.set(turnKey, {
        rawContent,
        modelLabel: itemModelLabel,
        mode: itemMode,
        stepCount: Array.isArray(item.steps) ? item.steps.length : 0,
      });
      const showWideReader = rawContent.length >= 160 || rawContent.split("\n").length >= 4;
      footerHtml = `<div class="agy-msg-footer">
        <button type="button" class="agy-msg-action-btn" data-agy-copy-turn="${escapeHtml(turnKey)}" title="Sao chép toàn bộ nội dung phản hồi">Sao chép</button>
        ${showWideReader ? `<button type="button" class="agy-msg-action-btn is-reader" data-agy-open-reader="${escapeHtml(turnKey)}" title="Mở chế độ đọc tập trung màn hình lớn">Đọc rộng ↗</button>` : ""}
      </div>`;
    }
    return `<div class="producer-codex-message assistant agy-msg-assistant" data-agy-mode="${escapeHtml(itemMode.toLowerCase())}">
      <div class="agy-msg-head">
        <span class="agy-role-ai"><i class="agy-sparkle">✦</i> Antigravity</span>
        <span class="agy-msg-model-badge">${escapeHtml(itemModelLabel)}</span>
        <span class="agy-msg-mode-badge">${escapeHtml(itemMode)}</span>
      </div>
      ${stepsHtml}
      ${markdownHtml}
      ${chatAttachmentGalleryHtml(item.attachments || [])}
      ${footerHtml}
    </div>`;
  }).join("");
}

function setChatMessagesHtmlIfChanged(messages, history = [], { scroll = true, force = false } = {}) {
  if (!messages) return;
  if (!force && messages.querySelector(".producer-codex-thinking, .agy-live-turn")) {
    return;
  }
  const nextHtml = producerChatMessagesHtml(history || []);
  if (!force && messages.dataset.lastRenderedHtml === nextHtml) {
    return;
  }
  messages.dataset.lastRenderedHtml = nextHtml;
  messages.innerHTML = nextHtml;
  if (scroll) {
    messages.scrollTop = messages.scrollHeight;
  }
}

function producerCodexContextHtml() {
  const job = state.jobs.find(item => item.id === state.selectedId);
  if (!job) {
    return `<div class="producer-context-title"><span>APP CONTEXT</span><strong>Chưa chọn dự án</strong></div><p>${escapeHtml(selectedAiLabel())} vẫn có thể mở Radar, tạo dự án mới hoặc chọn một dự án hiện có.</p>`;
  }
  const phaseRows = effectivePhases(job).map(phase => {
    const status = job.phases?.[phase]?.status || "pending";
    return `<div class="producer-context-phase"><span>${escapeHtml(phaseLabels[phase])}</span><b class="${escapeHtml(status)}">${escapeHtml(statusLabels[status] || status)}</b></div>`;
  }).join("");
  return `<div class="producer-context-title"><span>APP CONTEXT</span><strong>${escapeHtml(job.title)}</strong><small>${escapeHtml(job.market)} · ${escapeHtml(job.id)}</small></div><div class="producer-context-status"><span>Trạng thái</span><b>${escapeHtml(statusLabels[job.status] || job.status)}</b></div><div class="producer-context-phases">${phaseRows}</div>`;
}

const appTabLabels = {
  overview: "Tổng quan",
  codex: "AI Chat",
  radar: "Radar chủ đề",
  create: "Tạo dự án",
  script: "Kịch bản",
  voice: "Voice & SRT",
  visuals: "Visuals / Prompt",
  footage: "Tư liệu",
  ai_visual: "AI bổ sung",
  edit: "Edit",
  seo: "SEO + Thumbnail",
  qc: "Xuất video",
  projects: "Dự án",
};

const studioTabHints = {
  overview: "Trung tâm điều hành toàn bộ xưởng video tài liệu",
  radar: "Tìm cơ hội nội dung và nghiên cứu chủ đề",
  create: "Thiết lập phương án và tạo dự án sản xuất",
  script: "Viết kịch bản và kiểm tra cấu trúc câu chuyện",
  voice: "Tạo giọng đọc, timing và phụ đề SRT",
  visuals: "Chia cảnh và định tuyến visual cho footage hoặc AI",
  footage: "Tìm, duyệt và gắn tư liệu thật vào từng cảnh",
  ai_visual: "Tạo ảnh và video AI cho các cảnh cần bổ sung",
  edit: "Dựng timeline, xem Preview và hoàn thiện nhịp video",
  seo: "Đóng gói tiêu đề, mô tả và thumbnail",
  qc: "Kiểm tra bản cuối và xuất video hoàn chỉnh",
  projects: "Theo dõi tiến độ và checkpoint của mọi dự án",
  accounts: "Quản lý Codex, Gemini và engine đang hoạt động",
};

function updateStudioShell(tab = state.appTab || "overview") {
  const title = appTabLabels[tab] || (tab === "accounts" ? "Tài khoản AI" : "Tổng quan");
  if ($("#studioPageTitle")) $("#studioPageTitle").textContent = title;
  if ($("#studioPageHint")) $("#studioPageHint").textContent = studioTabHints[tab] || studioTabHints.overview;
}

function cleanLiveStatusMessage(rawMsg = "") {
  const text = String(rawMsg || "").trim();
  if (!text) return "";
  return text
    .replace(/\s*\[Lỗi gần nhất:[\s\S]*$/i, "")
    .replace(/<urlopen error[\s\S]*$/i, "")
    .trim();
}

function globalCodexProgressHtml(context) {
  const tab = context?.app_tab || state.appTab || "overview";
  const job = context?.selected_job;
  if (!job) {
    return `<div class="agy-progress-compact">
      <div class="agy-progress-top">
        <span class="agy-progress-project">Chưa chọn dự án</span>
        <span class="agy-progress-badge">${escapeHtml(appTabLabels[tab] || tab)}</span>
      </div>
    </div>`;
  }
  const live = context?.live_progress || {};
  const phase = job.current_phase;
  const phaseName = phase ? (phaseLabels[phase] || phase) : (statusLabels[job.status] || "Sẵn sàng");
  const livePercentValue = Number(live.percent ?? Number.NaN);
  const livePercent = Number.isFinite(livePercentValue) ? livePercentValue : null;
  const overallPercentValue = Number(job.overall_percent ?? Number.NaN);
  const overallPercent = Number.isFinite(overallPercentValue) ? overallPercentValue : null;
  const derivedLivePercent = livePercent != null
    ? livePercent
    : Number(live.total) > 0
      ? Math.round((Number(live.completed || 0) / Number(live.total)) * 100)
      : null;
  const activeDetail = live.total
    ? `${Number(live.completed || 0)}/${Number(live.total)} · ${derivedLivePercent ?? overallPercent ?? 0}%`
    : derivedLivePercent != null
      ? `${derivedLivePercent}%`
      : overallPercent != null
        ? `${overallPercent}%`
        : "";
  const activePhases = effectivePhases(job);
  const segmentHtml = activePhases.map((item, idx) => {
    const status = job.phases?.[item]?.status || "pending";
    const isCurrent = item === phase;
    return `<span class="agy-seg-item ${escapeHtml(status)}${isCurrent ? " active" : ""}" title="Bước ${idx + 1}: ${escapeHtml(phaseLabels[item] || item)} (${escapeHtml(statusLabels[status] || status)})"></span>`;
  }).join("");
  const cleanCaption = cleanLiveStatusMessage(live.status_message);
  return `<div class="agy-progress-compact">
    <div class="agy-progress-top">
      <span class="agy-progress-project" title="${escapeHtml(job.title || "")}">${escapeHtml(job.title || "Dự án")}</span>
      <span class="agy-progress-badge ${job.status === "running" ? "is-running" : ""}">
        ${job.status === "running" ? `<i class="agy-pulse-dot"></i>` : ""}
        <b>${escapeHtml(phaseName)}</b>
        ${activeDetail ? `<em>${escapeHtml(activeDetail)}</em>` : ""}
      </span>
    </div>
    <div class="agy-segmented-bar">${segmentHtml}</div>
    ${cleanCaption ? `<div class="agy-progress-caption" title="${escapeHtml(cleanCaption)}">${escapeHtml(cleanCaption)}</div>` : ""}
  </div>`;
}

async function fetchGlobalCodexContext() {
  const params = new URLSearchParams({ app_tab: state.appTab || "overview" });
  if (state.selectedId) params.set("selected_job_id", state.selectedId);
  return api(`/api/producer-chat/context?${params.toString()}`);
}

async function refreshGlobalCodexContext() {
  const dock = $("#globalCodexDock");
  if (!dock) return null;
  dock.classList.toggle("hidden", state.appTab === "codex");
  dock.classList.toggle("open", Boolean(state.globalCodexOpen));
  if (state.appTab === "codex") return null;
  const context = await fetchGlobalCodexContext();
  state.globalCodexContext = context;
  if (context?.latest_ui_draft && typeof context.latest_ui_draft === "object" && Object.keys(context.latest_ui_draft).length > 0) {
    const draft = context.latest_ui_draft;
    const brief = draft.creative_brief || draft;
    const draftSig = JSON.stringify({
      title: draft.title || "",
      angle: brief.narrative_angle || "",
      style: brief.writing_style || "",
      hook: brief.hook_archetype || "",
      opening: brief.opening_hook || "",
      chapters: Array.isArray(draft.outline) ? draft.outline.length : (Array.isArray(draft.outline?.chapters) ? draft.outline.chapters.length : 0),
    });
    if (draftSig !== state.lastSyncedUiDraftSig && (state.appTab === "create" || !state.selectedId)) {
      state.lastSyncedUiDraftSig = draftSig;
      applyCreativeProposalToCreateForm(draft, { switchTab: false, silent: true });
    }
  }
  const progress = $("#globalCodexProgress");
  if (progress) {
    const nextProgressHtml = globalCodexProgressHtml(context);
    if (state.lastGlobalCodexProgressHtml !== nextProgressHtml) {
      state.lastGlobalCodexProgressHtml = nextProgressHtml;
      progress.innerHTML = nextProgressHtml;
    }
  }
  const tabLabel = $("#globalCodexTabLabel");
  if (tabLabel) {
    const nextTabText = appTabLabels[context.app_tab] || context.app_tab || "Tổng quan";
    if (tabLabel.textContent !== nextTabText) tabLabel.textContent = nextTabText;
  }
  const mini = $("#globalCodexMiniStatus");
  if (mini) {
    const job = context.selected_job;
    const live = context.live_progress;
    const nextMiniText = job?.current_phase
      ? `${phaseLabels[job.current_phase] || job.current_phase}${live?.total ? ` · ${Number(live.completed || 0)}/${Number(live.total)}` : ""}`
      : job ? `${Number(job.completed_steps || 0)}/${Number(job.total_steps || effectivePhases(job).length)} bước` : (appTabLabels[context.app_tab] || "Sẵn sàng");
    if (mini.textContent !== nextMiniText) mini.textContent = nextMiniText;
  }
  return context;
}

function summarizeChatCliEvent(line) {
  let payload;
  try { payload = JSON.parse(String(line || "")); }
  catch (_) { return String(line || "").trim() ? { kind: "log", message: String(line).trim().slice(0, 700) } : null; }
  const type = String(payload.type || payload.event || "").toLowerCase();
  const item = payload.item || {};
  const update = payload.step_update || {};
  if (["item.started", "item.completed"].includes(type) && item.type === "command_execution") {
    return {
      kind: "command",
      step_type: "tool",
      tool_name: "run_command",
      tool_action: "Running command",
      target: String(item.command || "").slice(0, 300),
      state: type === "item.completed" ? "done" : "running",
      message: String(item.command || "Đang chạy lệnh").slice(0, 700),
    };
  }
  if (type === "item.completed" && item.type === "agent_message" && item.text) {
    return {
      kind: "message",
      step_type: "agent_response",
      content: String(item.text),
      state: "done",
      message: String(item.text).slice(0, 700),
    };
  }
  if (type === "step_update" && update.step_type === "tool") {
    const info = update.tool_info || {};
    const tool = update.tool_name || info.name || "tool";
    const params = info.parameters || info.params || {};
    const detail = update.target || params.CommandLine || params.command || params.Url || params.AbsolutePath || params.TargetFile || params.Query || params.query || "";
    const actionLabel = update.tool_action || update.tool_summary || tool;
    return {
      kind: tool === "run_command" ? "command" : "tool",
      step_index: update.step_index,
      step_type: "tool",
      tool_name: tool,
      tool_action: update.tool_action || "",
      tool_summary: update.tool_summary || "",
      target: String(detail || "").slice(0, 400),
      output: String(update.output || info.output || info.result || "").slice(0, 1600),
      state: String(update.state || "running").toLowerCase(),
      duration_seconds: Number(update.duration_seconds || 0),
      message: `${actionLabel}${detail ? ` · ${String(detail).slice(0, 400)}` : ""} · ${String(update.state || "running").toLowerCase()}`,
    };
  }
  if (type === "step_update" && update.step_type === "agent_response") {
    return {
      kind: "message",
      step_index: update.step_index,
      step_type: "agent_response",
      state: String(update.state || "running").toLowerCase(),
      duration_seconds: Number(update.duration_seconds || 0),
      thinking: String(update.thinking || ""),
      content: String(update.content || ""),
      message: update.thinking
        ? `Thinking: ${String(update.thinking).slice(0, 220)}`
        : `AI đang phân tích · ${String(update.state || "running").toLowerCase()}`,
    };
  }
  if (type === "thread.started") return { kind: "system", message: "Codex đã mở phiên làm việc" };
  if (type === "init") return { kind: "system", message: `Antigravity đã mở phiên ${payload.init?.model || ""}`.trim() };
  if (type === "result") {
    const respText = String(payload.result?.response || "").trim();
    return { kind: "result", content: respText, message: "AI đã hoàn tất phản hồi" };
  }
  return null;
}

function chatRunStorageKey(selectedJobId = state.selectedId) {
  return `cofi-producer-chat-run:${selectedJobId || "global"}`;
}

function loadStoredChatRun(selectedJobId = state.selectedId) {
  try {
    const value = localStorage.getItem(chatRunStorageKey(selectedJobId));
    return value ? JSON.parse(value) : null;
  } catch (_) { return null; }
}

function storeChatRun(run, selectedJobId = state.selectedId) {
  try { localStorage.setItem(chatRunStorageKey(selectedJobId), JSON.stringify(run)); } catch (_) {}
}

function clearStoredChatRun(selectedJobId = state.selectedId) {
  try { localStorage.removeItem(chatRunStorageKey(selectedJobId)); } catch (_) {}
}

async function cancelProducerChatRun(runId) {
  if (!runId) return;
  await api(`/api/producer-chat/runs/${encodeURIComponent(runId)}/cancel`, { method: "POST" });
}

function chatActivityLabel(event = {}) {
  const kind = String(event.kind || "log").toLowerCase();
  const message = String(event.message || "").toLowerCase();
  if (kind === "command" || /pytest|py_compile|node --check|test/.test(message)) return "Kiểm thử";
  if (/write|replace|patch|edit|file_change|sửa/.test(message)) return "Chỉnh sửa";
  if (/view_file|read|đọc/.test(message)) return "Đọc mã";
  if (/grep|search|find|rg /.test(message)) return "Tìm kiếm";
  if (kind === "result") return "Kết quả";
  if (kind === "message") return "Phân tích";
  if (kind === "system" || kind === "provider") return "Hệ thống";
  return "Hoạt động";
}

function consolidateLiveAntigravitySteps(events = []) {
  const stepMap = new Map();
  const ordered = [];
  let latestContent = "";
  for (const ev of events) {
    if (!ev || typeof ev !== "object") continue;
    if (ev.content && (ev.step_type === "agent_response" || ev.kind === "result")) {
      latestContent = String(ev.content);
    }
    if (ev.step_type === "tool" || ev.step_type === "agent_response") {
      const key = ev.step_index != null
        ? `${ev.step_type}:${ev.step_index}`
        : `${ev.step_type}:${ordered.length}`;
      if (stepMap.has(key)) {
        const prev = stepMap.get(key);
        Object.assign(prev, ev, {
          thinking: ev.thinking || prev.thinking || "",
          content: ev.content || prev.content || "",
          tool_action: ev.tool_action || prev.tool_action || "",
          tool_summary: ev.tool_summary || prev.tool_summary || "",
          target: ev.target || prev.target || "",
          output: ev.output || prev.output || "",
          duration_seconds: ev.duration_seconds || prev.duration_seconds || 0,
        });
      } else {
        const copy = { ...ev };
        stepMap.set(key, copy);
        ordered.push(copy);
      }
    }
  }
  return { steps: ordered, latestContent };
}

function chatActivityTimelineHtml(events = []) {
  if (!events.length) return `<div class="repair-log-empty">Đang khởi tạo bước suy luận…</div>`;
  const { steps, latestContent } = consolidateLiveAntigravitySteps(events);
  if (steps.length || latestContent) {
    const stepsBlock = renderAntigravityStepsHtml(steps, { live: true });
    const streamMd = latestContent
      ? `<div class="agy-markdown-body agy-live-stream-md">${renderAntigravityMarkdown(latestContent)}</div>`
      : "";
    return `${stepsBlock}${streamMd}`;
  }
  return events.slice(-20).map((event, index, shown) => {
    const active = index === shown.length - 1;
    return `<div class="chat-activity-step ${active ? "active" : "done"}"><i></i><div><span>${escapeHtml(chatActivityLabel(event))}</span><p>${escapeHtml(event.message || "")}</p></div></div>`;
  }).join("");
}

function renderChatLiveProgress(node, provider, events = [], stage = "running", message = "", runId = "") {
  if (!node) return;
  const labels = {
    starting: "Đang kết nối", reconnecting: "Đang nối lại phiên", chatting: "Đang suy luận", running: "Đang thực thi",
    repairing: "Đang sửa code", verifying: "Đang kiểm thử", restarting: "Đang khởi chạy lại", reporting: "Đang tổng hợp", cancelling: "Đang dừng",
    completed: "Đã hoàn tất", cancelled: "Đã dừng", failed: "Thất bại",
  };
  const active = ["starting", "reconnecting", "chatting", "running", "repairing", "verifying", "restarting", "reporting", "cancelling"].includes(stage);
  const nextClassName = `producer-codex-message assistant agy-msg-assistant agy-live-turn ${escapeHtml(stage)}`;
  if (node.className !== nextClassName) {
    node.className = nextClassName;
  }

  const parent = node.parentElement;
  const shouldScrollParent = parent
    ? (parent.scrollHeight - parent.scrollTop - parent.clientHeight < 110)
    : false;

  const modelBadge = humanizeAntigravityModel(currentChatModelId());
  const stageLabel = labels[stage] || stage;

  if (!node.querySelector(".agy-live-head") || !node.querySelector(".agy-live-body")) {
    node.innerHTML = `<div class="agy-msg-head agy-live-head">
        <div class="agy-live-title-group">
          <span class="agy-role-ai"><i class="agy-sparkle">✦</i> Antigravity</span>
          <span class="agy-msg-model-badge">${escapeHtml(modelBadge)}</span>
          <span class="agy-live-status-pill ${active ? "is-active" : ""}">
            <i class="agy-pulse-dot"${active ? "" : ' style="display:none"'}></i>
            <span class="agy-live-status-text">${escapeHtml(stageLabel)}</span>
          </span>
        </div>
        <div class="agy-live-actions"></div>
      </div>
      <div class="agy-live-body"></div>`;
  } else {
    const badgeEl = node.querySelector(".agy-msg-model-badge");
    if (badgeEl && badgeEl.textContent !== modelBadge) badgeEl.textContent = modelBadge;
    const pillEl = node.querySelector(".agy-live-status-pill");
    if (pillEl) pillEl.classList.toggle("is-active", active);
    const dotEl = node.querySelector(".agy-live-status-pill .agy-pulse-dot");
    if (dotEl) dotEl.style.display = active ? "inline-block" : "none";
    const statusTextEl = node.querySelector(".agy-live-status-text") || node.querySelector(".agy-live-status-pill span");
    if (statusTextEl && statusTextEl.textContent !== stageLabel) statusTextEl.textContent = stageLabel;
  }

  const actionsEl = node.querySelector(".agy-live-actions");
  if (actionsEl) {
    const wantStopRunId = active && runId ? String(runId) : "";
    if (actionsEl.dataset.stopRunId !== wantStopRunId) {
      actionsEl.dataset.stopRunId = wantStopRunId;
      actionsEl.innerHTML = wantStopRunId
        ? `<button type="button" class="agy-stop-btn" data-cancel-chat-run="${escapeHtml(wantStopRunId)}">■ Dừng</button>`
        : "";
      const cancel = actionsEl.querySelector("[data-cancel-chat-run]");
      if (cancel) {
        cancel.onclick = async () => {
          cancel.disabled = true;
          try { await cancelProducerChatRun(wantStopRunId); }
          catch (err) { cancel.disabled = false; toast(err.message, true); }
        };
      }
    }
  }

  const bodyEl = node.querySelector(".agy-live-body");
  if (!bodyEl) return;

  if (!events.length) {
    if (!bodyEl.querySelector(".repair-log-empty")) {
      bodyEl.innerHTML = `<div class="repair-log-empty">Đang khởi tạo bước suy luận…</div>`;
    }
  } else {
    const { steps, latestContent } = consolidateLiveAntigravitySteps(events);
    const { entries, totalDur, lastActiveTitle } = buildAntigravityStepEntries(steps, { live: true });

    if (entries.length || latestContent) {
      bodyEl.querySelector(".repair-log-empty")?.remove();
      bodyEl.querySelector(".agy-legacy-events")?.remove();

      if (entries.length) {
        let groupEl = bodyEl.querySelector(":scope > details.agy-step-group");
        const totalCount = entries.length;
        const durText = totalDur > 0 ? `${totalDur < 10 ? totalDur.toFixed(1) : Math.round(totalDur)}s` : "";
        const groupTitle = lastActiveTitle ? `Đang chạy: ${lastActiveTitle}` : `Đang thực thi (${totalCount} bước)…`;

        if (!groupEl) {
          const tempWrap = document.createElement("div");
          tempWrap.innerHTML = `<details class="agy-step-group is-live" open>
            <summary class="agy-step-group-summary">
              <i class="agy-pulse-dot agy-step-live-dot"></i>
              <span class="agy-step-group-chevron">▸</span>
              <span class="agy-step-group-title">${escapeHtml(groupTitle)}</span>
              <span class="agy-step-group-meta"${durText ? "" : ' style="display:none"'}>${escapeHtml(durText)}</span>
            </summary>
            <div class="agy-steps-container"></div>
          </details>`;
          groupEl = tempWrap.firstElementChild;
          bodyEl.prepend(groupEl);
        } else {
          const titleEl = groupEl.querySelector(".agy-step-group-title");
          if (titleEl && titleEl.textContent !== groupTitle) titleEl.textContent = groupTitle;
          const metaEl = groupEl.querySelector(".agy-step-group-meta");
          if (metaEl) {
            if (durText) {
              metaEl.style.display = "";
              if (metaEl.textContent !== durText) metaEl.textContent = durText;
            } else {
              metaEl.style.display = "none";
            }
          }
        }

        const stepBox = groupEl.querySelector(".agy-steps-container");
        if (stepBox) {
          const shouldScrollSteps = stepBox.scrollHeight - stepBox.scrollTop - stepBox.clientHeight < 64;
          let stepsMutated = false;
          for (const entry of entries) {
            const existing = Array.from(stepBox.children).find(el => el.dataset?.stepKey === entry.key);
            if (!existing) {
              stepBox.insertAdjacentHTML("beforeend", entry.html);
              stepsMutated = true;
            } else if (existing.dataset.stepSig !== entry.sig) {
              const wasOpen = existing.tagName === "DETAILS" ? existing.open : false;
              const tmp = document.createElement("div");
              tmp.innerHTML = entry.html;
              const nextEl = tmp.firstElementChild;
              if (nextEl) {
                if (wasOpen && nextEl.tagName === "DETAILS") nextEl.open = true;
                existing.replaceWith(nextEl);
                stepsMutated = true;
              }
            }
          }
          if (stepsMutated && shouldScrollSteps) {
            stepBox.scrollTop = stepBox.scrollHeight;
          }
        }
      }

      if (latestContent) {
        let streamMdEl = bodyEl.querySelector(":scope > .agy-live-stream-md");
        if (!streamMdEl) {
          streamMdEl = document.createElement("div");
          streamMdEl.className = "agy-markdown-body agy-live-stream-md";
          bodyEl.appendChild(streamMdEl);
        }
        if (streamMdEl.dataset.rawContent !== latestContent) {
          streamMdEl.dataset.rawContent = latestContent;
          streamMdEl.innerHTML = renderAntigravityMarkdown(latestContent);
        }
      }
    } else {
      const legacyHtml = events.slice(-20).map((event, index, shown) => {
        const isLast = index === shown.length - 1;
        return `<div class="chat-activity-step ${isLast ? "active" : "done"}"><i></i><div><span>${escapeHtml(chatActivityLabel(event))}</span><p>${escapeHtml(event.message || "")}</p></div></div>`;
      }).join("");
      let legacyWrap = bodyEl.querySelector(".agy-legacy-events");
      if (!legacyWrap) {
        bodyEl.innerHTML = `<div class="agy-legacy-events chat-activity-timeline"></div>`;
        legacyWrap = bodyEl.querySelector(".agy-legacy-events");
      }
      if (legacyWrap && legacyWrap.dataset.legacySig !== legacyHtml) {
        legacyWrap.dataset.legacySig = legacyHtml;
        legacyWrap.innerHTML = legacyHtml;
      }
    }
  }

  if (shouldScrollParent && parent) {
    parent.scrollTop = parent.scrollHeight;
  }
}

async function connectProducerChatRun(runId, payload, thinkingId, messages, provider, after = 0) {
  const decoder = new TextDecoder();
  const events = [];
  let result = null;
  let lastSeq = Number(after || 0);
  let reconnectAttempts = 0;
  let currentStage = "running";
  let currentMessage = "AI đang xử lý…";
  let rafId = 0;
  const selectedJobId = payload?.selected_job_id || null;

  const scheduleRender = (immediate = false) => {
    if (immediate) {
      if (rafId) {
        cancelAnimationFrame(rafId);
        rafId = 0;
      }
      renderChatLiveProgress(document.getElementById(thinkingId), provider, events, currentStage, currentMessage, runId);
      return;
    }
    if (rafId) return;
    rafId = requestAnimationFrame(() => {
      rafId = 0;
      renderChatLiveProgress(document.getElementById(thinkingId), provider, events, currentStage, currentMessage, runId);
    });
  };

  try {
    while (true) {
      try {
        const response = await fetch(`/api/producer-chat/runs/${encodeURIComponent(runId)}/events?after=${lastSeq}`);
        if (!response.ok || !response.body) {
          let detail = `HTTP ${response.status}`;
          try { detail = (await response.json()).detail || detail; } catch (_) {}
          const error = new Error(detail);
          error.chatRunTerminal = response.status === 404;
          throw error;
        }
        reconnectAttempts = 0;
        const reader = response.body.getReader();
        let buffer = "";
        while (true) {
          const chunk = await reader.read();
          buffer += decoder.decode(chunk.value || new Uint8Array(), { stream: !chunk.done });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";
          let dirty = false;
          for (const line of lines) {
            if (!line.trim()) continue;
            const event = JSON.parse(line);
            if (Number(event.seq || 0) > lastSeq) {
              lastSeq = Number(event.seq);
              storeChatRun({ runId, seq: lastSeq, provider, payload }, selectedJobId);
            }
            if (event.type === "cli_event") {
              const summary = summarizeChatCliEvent(event.line);
              if (summary) {
                events.push(summary);
                currentStage = "running";
                currentMessage = summary.message || "AI đang xử lý…";
                dirty = true;
              }
            } else if (event.type === "repair_event") {
              const summary = { kind: event.kind || "log", message: event.message || "Đang sửa code" };
              events.push(summary);
              currentStage = "repairing";
              currentMessage = summary.message;
              dirty = true;
            } else if (event.type === "stage") {
              if (["completed", "failed"].includes(String(event.stage || "")) && event.message) {
                events.push({ kind: event.stage === "completed" ? "result" : "error", message: event.message || result?.reply });
              }
              currentStage = event.stage || "running";
              currentMessage = event.message || "AI đang xử lý…";
              dirty = true;
            } else if (event.type === "started") {
              currentStage = "starting";
              currentMessage = event.message || "Đang mở phiên làm việc…";
              dirty = true;
            } else if (event.type === "cancel_requested") {
              currentStage = "cancelling";
              currentMessage = event.message || "Đang dừng…";
              dirty = true;
            } else if (event.type === "cancelled" || event.type === "error") {
              clearStoredChatRun(selectedJobId);
              currentStage = event.type === "cancelled" ? "cancelled" : "failed";
              currentMessage = event.message || "Tác vụ thất bại";
              scheduleRender(true);
              const error = new Error(event.message || "Tác vụ chat thất bại");
              error.chatRunTerminal = true;
              throw error;
            } else if (event.type === "result") {
              result = event.result;
              clearStoredChatRun(selectedJobId);
              dirty = false;
            }
          }
          if (result) return result;
          if (dirty) scheduleRender(false);
          if (chunk.done) break;
        }
        throw new Error("Luồng cập nhật đã đóng trước khi phiên AI hoàn tất.");
      } catch (connectionError) {
        if (connectionError.chatRunTerminal) throw connectionError;
        if (result) return result;
        let snapshot = null;
        try { snapshot = await api(`/api/producer-chat/runs/${encodeURIComponent(runId)}`); }
        catch (_) {}
        if (snapshot?.status === "succeeded") {
          clearStoredChatRun(selectedJobId);
          if (!snapshot.result) throw new Error("Phiên AI đã kết thúc nhưng thiếu báo cáo cuối.");
          return snapshot.result;
        }
        if (["failed", "cancelled"].includes(snapshot?.status)) {
          clearStoredChatRun(selectedJobId);
          throw new Error(snapshot.error || (snapshot.status === "cancelled" ? "Phiên chat đã dừng." : "Phiên AI đã thất bại."));
        }
        reconnectAttempts += 1;
        currentStage = "reconnecting";
        currentMessage = "Mất kết nối hiển thị; đang nối lại đúng phiên AI, không gửi lại yêu cầu…";
        scheduleRender(true);
        await new Promise(resolve => setTimeout(resolve, Math.min(1000 * reconnectAttempts, 5000)));
      }
    }
  } finally {
    if (rafId) {
      cancelAnimationFrame(rafId);
      rafId = 0;
    }
  }
}

async function streamProducerChat(payload, thinkingId, messages, provider) {
  state.chatRunConnections[thinkingId] = "starting";
  try {
    const response = await fetch("/api/producer-chat/runs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok || !response.body) {
      let detail = `HTTP ${response.status}`;
      try { detail = (await response.json()).detail || detail; } catch (_) {}
      throw new Error(detail);
    }
    const run = await response.json();
    state.chatRunConnections[thinkingId] = run.id || true;
    const lockedProvider = String(run.provider || provider || "AI");
    storeChatRun({ runId: run.id, seq: 0, provider: lockedProvider, payload }, payload.selected_job_id || null);
    return await connectProducerChatRun(run.id, payload, thinkingId, messages, lockedProvider, 0);
  } finally {
    delete state.chatRunConnections[thinkingId];
  }
}

async function resumeStoredProducerChatRun(thinkingId, messages) {
  if (state.chatRunConnections[thinkingId]) return;
  let stored = loadStoredChatRun();
  if (stored?.runId) {
    try {
      const inspected = await api(`/api/producer-chat/runs/${encodeURIComponent(stored.runId)}`);
      if (state.chatRunConnections[thinkingId]) return;
      if (["succeeded", "failed", "cancelled"].includes(String(inspected?.status || ""))) {
        clearStoredChatRun(stored.payload?.selected_job_id || state.selectedId);
        stored = null;
      } else {
        stored = {
          ...stored,
          provider: inspected.provider || stored.provider,
          payload: inspected.payload || stored.payload,
        };
      }
    } catch (_) {
      clearStoredChatRun(stored.payload?.selected_job_id || state.selectedId);
      stored = null;
    }
  }
  if (!stored?.runId) {
    const params = new URLSearchParams();
    if (state.selectedId) params.set("selected_job_id", state.selectedId);
    try {
      const active = await api(`/api/producer-chat/runs/active?${params.toString()}`);
      if (state.chatRunConnections[thinkingId]) return;
      if (active?.id) {
        stored = {
          runId: active.id,
          seq: 0,
          provider: active.provider || selectedAiLabel(),
          payload: active.payload || { selected_job_id: state.selectedId, app_tab: state.appTab },
        };
        storeChatRun(stored, active.payload?.selected_job_id || null);
      } else {
        const history = await api(producerChatHistoryUrl());
        if (state.chatRunConnections[thinkingId]) return;
        setChatMessagesHtmlIfChanged(messages, history || []);
      }
    } catch (_) { return; }
  }
  if (!stored?.runId || state.chatRunConnections[thinkingId]) return;
  if (!document.getElementById(thinkingId)) {
    messages.insertAdjacentHTML("beforeend", `<div class="producer-codex-thinking" id="${escapeHtml(thinkingId)}"></div>`);
  }
  state.chatRunConnections[thinkingId] = stored.runId || true;
  renderChatLiveProgress(document.getElementById(thinkingId), stored.provider || selectedAiLabel(), [], "starting", "Đang nối lại phiên đang chạy…", stored.runId);
  connectProducerChatRun(
    stored.runId,
    stored.payload || {},
    thinkingId,
    messages,
    stored.provider || selectedAiLabel(), 0
  )
    .then(async result => {
      document.getElementById(thinkingId)?.remove();
      setChatMessagesHtmlIfChanged(messages, result.history || [], { force: true });
      await loadJobs(true);
      await applyProducerUiActions(result.ui_actions || []);
    })
    .catch(err => {
      document.getElementById(thinkingId)?.remove();
      messages.insertAdjacentHTML("beforeend", `<div class="producer-codex-error">${escapeHtml(err.message)}</div>`);
    })
    .finally(() => { delete state.chatRunConnections[thinkingId]; });
}

function syncGoalModeToggles(nextChecked = null) {
  if (typeof nextChecked === "boolean") {
    localStorage.setItem("cofi-chat-goal-mode", nextChecked ? "1" : "0");
  }
  const checked = localStorage.getItem("cofi-chat-goal-mode") === "1";
  [
    { input: $("#globalCodexGoalToggle"), label: $("#globalCodexModeLabel") },
    { input: $("#producerCodexGoalToggle"), label: $("#producerCodexModeLabel") },
  ].forEach(({ input, label }) => {
    if (input) {
      input.checked = checked;
      input.closest(".agy-mode-pill")?.classList.toggle("goal-active", checked);
    }
    if (label) {
      label.textContent = checked ? "Goal" : "Agent";
    }
  });
  return checked;
}

async function handleCofiProposalCardAction(actionType, proposal, buttonEl) {
  if (!proposal || typeof proposal !== "object") return;
  const brief = proposal.creative_brief && typeof proposal.creative_brief === "object"
    ? { ...proposal.creative_brief, ...proposal }
    : proposal;
  const chapters = Array.isArray(proposal.outline?.chapters)
    ? proposal.outline.chapters
    : Array.isArray(proposal.chapters)
      ? proposal.chapters
      : [];
  const origLabel = buttonEl?.textContent || "";
  if (buttonEl) buttonEl.disabled = true;
  try {
    if (actionType === "fill_create") {
      applyCreativeProposalToCreateForm(proposal, { switchTab: true });
      toast("Đã đẩy phương án & dàn ý vào Form Tạo dự án.");
      return;
    }
    if (actionType === "create_now") {
      if (buttonEl) buttonEl.textContent = "Đang tạo dự án…";
      const profile = currentChannelProfile();
      const form = $("#jobForm");
      const raw = form ? Object.fromEntries(new FormData(form).entries()) : {};
      const title = String(proposal.title || $("#createManualTitleInput")?.value || raw.title || "Dự án Tài liệu Sáng tạo").trim();
      const created = await api("/api/jobs", {
        method: "POST",
        body: JSON.stringify({
          title,
          market: String(proposal.market || raw.market || profile?.market || "KR"),
          language: String(proposal.language || raw.language || profile?.language || "ko"),
          notes: String(brief.custom_rules || proposal.notes || raw.notes || ""),
          target_duration_minutes: Number(proposal.target_duration_minutes || raw.target_duration_minutes || 18),
          plan_engine: String(raw.plan_engine || "codex"),
          visual_strategy: String(raw.visual_strategy || "evidence_footage"),
          ai_media_mode: String(raw.ai_media_mode || "mixed"),
          playbook_id: brief.playbook_id || null,
          creative_brief: {
            playbook_id: brief.playbook_id || null,
            narrative_angle: brief.narrative_angle || "investigative_forensic",
            writing_style: brief.writing_style || "cold_dossier",
            hook_archetype: brief.hook_archetype || "shocking_anomaly",
            editing_archetypes: Array.isArray(brief.editing_archetypes) && brief.editing_archetypes.length
              ? brief.editing_archetypes
              : ["forensic_red_string", "vox_blueprint_explainer"],
            opening_hook: brief.opening_hook || "",
            custom_rules: brief.custom_rules || proposal.notes || "",
          },
          outline: chapters.length ? { thesis: proposal.thesis || proposal.why_it_works || "", opening_hook: brief.opening_hook || "", chapters } : null,
          channel_profile_id: profile?.id || raw.channel_profile_id || null,
        }),
      });
      state.selectedId = created.id;
      await loadJobs(true);
      await renderDetail();
      setAppTab("script");
      await renderFunctionWorkspaces();
      toast(`Đã tạo dự án "${created.title}" kèm Dàn ý Chương hồi.`);
      return;
    }
    if (actionType === "apply_job") {
      if (!state.selectedId) {
        applyCreativeProposalToCreateForm(proposal, { switchTab: true });
        toast("Chưa có dự án nào đang mở — Đã đẩy vào Form Tạo dự án.");
        return;
      }
      if (buttonEl) buttonEl.textContent = "Đang áp dụng…";
      await api(`/api/jobs/${encodeURIComponent(state.selectedId)}/creative-brief`, {
        method: "PATCH",
        body: JSON.stringify({
          playbook_id: brief.playbook_id || null,
          creative_brief: {
            playbook_id: brief.playbook_id || null,
            narrative_angle: brief.narrative_angle || "investigative_forensic",
            writing_style: brief.writing_style || "cold_dossier",
            hook_archetype: brief.hook_archetype || "shocking_anomaly",
            editing_archetypes: Array.isArray(brief.editing_archetypes) ? brief.editing_archetypes : [],
            opening_hook: brief.opening_hook || "",
            custom_rules: brief.custom_rules || proposal.notes || "",
          },
        }),
      });
      if (chapters.length) {
        await api(`/api/jobs/${encodeURIComponent(state.selectedId)}/outline`, {
          method: "PATCH",
          body: JSON.stringify({
            outline: {
              thesis: proposal.thesis || proposal.why_it_works || "",
              opening_hook: brief.opening_hook || "",
              chapters,
            },
          }),
        });
      }
      await loadJobs(true);
      setAppTab("script");
      await renderFunctionWorkspaces();
      toast("Đã áp dụng Định hướng Sáng tạo & Dàn ý vào dự án đang mở.");
      return;
    }
    if (actionType === "save_playbook") {
      const defaultName = proposal.name || (proposal.title ? `Playbook · ${String(proposal.title).slice(0, 32)}` : "Playbook Kênh Mới");
      const name = window.prompt("Nhập tên Playbook Kênh để lưu tái sử dụng:", defaultName);
      if (!name || !name.trim()) return;
      const saved = await api("/api/playbooks", {
        method: "POST",
        body: JSON.stringify({
          name: name.trim(),
          description: proposal.description || proposal.why_it_works || "",
          creative_brief: {
            narrative_angle: brief.narrative_angle || "investigative_forensic",
            writing_style: brief.writing_style || "cold_dossier",
            hook_archetype: brief.hook_archetype || "shocking_anomaly",
            editing_archetypes: Array.isArray(brief.editing_archetypes) ? brief.editing_archetypes : ["forensic_red_string"],
            opening_hook: brief.opening_hook || "",
            custom_rules: brief.custom_rules || proposal.notes || "",
          },
        }),
      });
      await loadPlaybooks();
      if (saved?.id) renderCreatePlaybookSelect(saved.id);
      toast(`Đã lưu Playbook "${name.trim()}".`);
    }
  } catch (err) {
    toast(err.message, true);
  } finally {
    if (buttonEl) {
      buttonEl.disabled = false;
      buttonEl.textContent = origLabel;
    }
  }
}

function bindChatContainerInteractions(messagesNode, inputNode, formNode) {
  if (inputNode && inputNode.dataset.agyResizeBound !== "1") {
    inputNode.dataset.agyResizeBound = "1";
    const autoResize = () => {
      inputNode.style.height = "auto";
      inputNode.style.height = `${Math.min(140, Math.max(40, inputNode.scrollHeight))}px`;
    };
    inputNode.addEventListener("input", autoResize);
  }
  if (!messagesNode || messagesNode.dataset.agyBound === "1") return;
  messagesNode.dataset.agyBound = "1";
  messagesNode.addEventListener("click", async event => {
    const proposalBtn = event.target.closest("[data-proposal-action]");
    if (proposalBtn) {
      const card = proposalBtn.closest("[data-cofi-proposal]");
      if (card?.dataset?.cofiProposal) {
        try {
          const parsed = JSON.parse(decodeURIComponent(card.dataset.cofiProposal));
          await handleCofiProposalCardAction(proposalBtn.dataset.proposalAction, parsed, proposalBtn);
        } catch (err) {
          toast(err.message, true);
        }
      }
      return;
    }
    const fileChip = event.target.closest("a.agy-file-chip");
    if (fileChip) {
      const href = fileChip.getAttribute("href") || "";
      if (/^file:/i.test(href)) {
        event.preventDefault();
        let cleanPath = href.replace(/^file:\/\/\/?/i, "").replace(/#L\d+(?:-L?\d+)?$/i, "");
        try {
          cleanPath = decodeURIComponent(cleanPath);
        } catch (_) {}
        try {
          await navigator.clipboard.writeText(cleanPath);
          toast(`Đã chép đường dẫn: ${shortenAntigravityPathLabel(cleanPath, 42)}`);
        } catch (_) {}
        return;
      }
    }
    const copyTurnBtn = event.target.closest("[data-agy-copy-turn]");
    if (copyTurnBtn) {
      const entry = agyTurnReaderStore.get(copyTurnBtn.dataset.agyCopyTurn || "");
      if (entry?.rawContent) {
        try {
          await navigator.clipboard.writeText(entry.rawContent);
          const orig = copyTurnBtn.textContent;
          copyTurnBtn.textContent = "Đã chép ✓";
          setTimeout(() => { copyTurnBtn.textContent = orig; }, 1500);
        } catch (_) {}
      }
      return;
    }
    const openReaderBtn = event.target.closest("[data-agy-open-reader]");
    if (openReaderBtn) {
      const entry = agyTurnReaderStore.get(openReaderBtn.dataset.agyOpenReader || "");
      if (entry?.rawContent) {
        const stepSuffix = entry.stepCount ? ` · Đã chạy ${entry.stepCount} bước` : "";
        openStudioInspectorModal({
          badge: "✦",
          title: extractAntigravityTurnHeadline(entry.rawContent),
          subtitle: `Antigravity · ${entry.modelLabel}${stepSuffix} · Chế độ đọc tập trung`,
          html: `<article class="agy-reader-article agy-markdown-body">${renderAntigravityMarkdown(entry.rawContent)}</article>`,
          rawText: entry.rawContent,
          onOpen: (bodyEl) => {
            if (!bodyEl || bodyEl.dataset.agyReaderBound === "1") return;
            bodyEl.dataset.agyReaderBound = "1";
            bodyEl.addEventListener("click", async (ev) => {
              const modalFileChip = ev.target.closest("a.agy-file-chip");
              if (modalFileChip && /^file:/i.test(modalFileChip.getAttribute("href") || "")) {
                ev.preventDefault();
                let cp = (modalFileChip.getAttribute("href") || "").replace(/^file:\/\/\/?/i, "").replace(/#L\d+(?:-L?\d+)?$/i, "");
                try { cp = decodeURIComponent(cp); } catch (_) {}
                try {
                  await navigator.clipboard.writeText(cp);
                  toast(`Đã chép đường dẫn: ${shortenAntigravityPathLabel(cp, 42)}`);
                } catch (_) {}
                return;
              }
              const modalCopyCode = ev.target.closest("[data-copy-code]");
              if (modalCopyCode) {
                const codeEl = modalCopyCode.closest(".agy-code-block")?.querySelector("code");
                if (codeEl) {
                  try {
                    await navigator.clipboard.writeText(codeEl.textContent || "");
                    const orig = modalCopyCode.textContent;
                    modalCopyCode.textContent = "Đã chép ✓";
                    setTimeout(() => { modalCopyCode.textContent = orig; }, 1500);
                  } catch (_) {}
                }
              }
            });
          },
        });
      }
      return;
    }
    const copyBtn = event.target.closest("[data-copy-code]");
    if (copyBtn) {
      const codeEl = copyBtn.closest(".agy-code-block")?.querySelector("code");
      if (codeEl) {
        try {
          await navigator.clipboard.writeText(codeEl.textContent || "");
          const orig = copyBtn.textContent;
          copyBtn.textContent = "Đã chép ✓";
          setTimeout(() => { copyBtn.textContent = orig; }, 1500);
        } catch (_) {}
      }
      return;
    }
    const quickBtn = event.target.closest("[data-quick-prompt]");
    if (quickBtn && inputNode) {
      inputNode.value = quickBtn.dataset.quickPrompt || "";
      inputNode.focus();
      if (formNode) formNode.requestSubmit();
    }
  });
}

async function renderGlobalProducerChat({ loadHistory = true } = {}) {
  const dock = $("#globalCodexDock");
  const messages = $("#globalCodexMessages");
  const form = $("#globalCodexForm");
  if (!dock || !messages || !form) return;
  dock.classList.toggle("open", Boolean(state.globalCodexOpen));
  document.body.classList.toggle("global-chat-open", Boolean(state.globalCodexOpen));
  syncChatModelSelects();
  syncGoalModeToggles();

  const contextPromise = refreshGlobalCodexContext();
  if (loadHistory && !state.chatRunConnections.globalCodexThinking && !document.getElementById("globalCodexThinking")) {
    const history = await api(producerChatHistoryUrl());
    if (!state.chatRunConnections.globalCodexThinking && !document.getElementById("globalCodexThinking")) {
      setChatMessagesHtmlIfChanged(messages, history);
    }
  }
  await contextPromise;

  const input = $("#globalCodexInput");
  const imageInput = $("#globalCodexImageInput") || $("#editChatImageInput");
  const attachmentPreview = $("#globalCodexAttachmentPreview") || $("#editChatAttachmentPreview");
  bindChatContainerInteractions(messages, input, form);
  const renderAttachments = () => renderPendingChatAttachments(attachmentPreview, state.globalCodexAttachments, id => {
    state.globalCodexAttachments = state.globalCodexAttachments.filter(item => item.id !== id);
    renderAttachments();
  });
  renderAttachments();

  dock.addEventListener("pointerdown", e => {
    if (e.target.closest('button, input, select, textarea, a')) return;
  });
  dock.addEventListener("pointercancel", () => {});

  const closeGlobalChat = () => {
    state.globalCodexOpen = false;
    localStorage.setItem("cofi-global-chat-open", "0");
    dock.classList.remove("open");
    document.body.classList.remove("global-chat-open");
  };
  const toggleGlobalChat = async () => {
    state.globalCodexOpen = !state.globalCodexOpen;
    localStorage.setItem("cofi-global-chat-open", state.globalCodexOpen ? "1" : "0");
    dock.classList.toggle("open", state.globalCodexOpen);
    document.body.classList.toggle("global-chat-open", state.globalCodexOpen);
    if (state.globalCodexOpen) {
      await renderGlobalProducerChat({ loadHistory: true });
      input?.focus();
    }
  };
  $("#globalCodexToggle").onclick = toggleGlobalChat;
  $("#globalCodexCloseBtn").onclick = closeGlobalChat;
  if ($("#globalCodexMinimizeBtn")) $("#globalCodexMinimizeBtn").onclick = closeGlobalChat;
  if ($("#sidebarChatToggleBtn")) $("#sidebarChatToggleBtn").onclick = toggleGlobalChat;
  if ($("#desktopChatToggleBtn")) $("#desktopChatToggleBtn").onclick = toggleGlobalChat;
  $$('[data-toggle-global-chat]').forEach(btn => { btn.onclick = toggleGlobalChat; });

  $("#globalCodexClearBtn").onclick = () => clearCurrentProducerChatHistory().catch(err => toast(err.message, true));
  if ($("#globalCodexNewBtn")) {
    $("#globalCodexNewBtn").onclick = () => startNewProducerChatSession().catch(err => toast(err.message, true));
  }
  if ($("#globalCodexCompactBtn")) {
    $("#globalCodexCompactBtn").onclick = () => compactCurrentProducerChatSession().catch(err => toast(err.message, true));
  }
  if (imageInput) imageInput.onchange = async () => {
    try {
      state.globalCodexAttachments = await appendSelectedChatImages(imageInput.files, state.globalCodexAttachments, next => {
        state.globalCodexAttachments = next;
        renderAttachments();
      });
    } catch (err) { toast(err.message, true); }
    finally { imageInput.value = ""; }
  };
  input.onpaste = async event => {
    try {
      state.globalCodexAttachments = await appendPastedChatImages(event, state.globalCodexAttachments, next => {
        state.globalCodexAttachments = next;
        renderAttachments();
      });
    } catch (err) { toast(err.message, true); }
  };
  input.onkeydown = event => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      form.requestSubmit();
    }
  };
  form.onsubmit = async event => {
    event.preventDefault();
    const message = input.value.trim();
    const attachments = [...state.globalCodexAttachments];
    if (attachments.some(item => item.uploading)) {
      toast("Vui lòng đợi ảnh tải lên hoàn tất.", true);
      return;
    }
    if (!message && !attachments.length) return;
    const send = $("#globalCodexSendBtn");
    const hint = $("#globalCodexHint");
    input.value = "";
    state.globalCodexAttachments = [];
    renderAttachments();
    input.disabled = true;
    if (imageInput) imageInput.disabled = true;
    send.disabled = true;
    const aiLabel = selectedAiLabel();
    const modelId = currentChatModelId();
    hint.textContent = `${aiLabel} đang xử lý trong tab ${appTabLabels[state.appTab] || state.appTab}…`;
    state.chatRunConnections.globalCodexThinking = "starting";
    messages.querySelector(".producer-codex-empty")?.remove();
    messages.insertAdjacentHTML("beforeend", `<div class="producer-codex-message user agy-msg-user"><div class="agy-msg-head"><span class="agy-role-user">Bạn</span></div>${message ? `<div class="agy-user-text">${escapeHtml(message).replace(/\n/g, "<br>")}</div>` : ""}${chatAttachmentGalleryHtml(attachments)}</div><div class="producer-codex-thinking" id="globalCodexThinking">${escapeHtml(aiLabel)} đang xử lý…</div>`);
    renderChatLiveProgress(document.getElementById("globalCodexThinking"), aiLabel, [], "starting", "Đang kết nối…");
    messages.scrollTop = messages.scrollHeight;
    try {
      const goalToggle = $("#globalCodexGoalToggle");
      const goalMode = Boolean(goalToggle?.checked) || /^\/goal\b/i.test(message);
      if (!goalMode && modelId === "codex") await waitForCodexWebPacing();
      const result = await streamProducerChat(
        {
          message,
          selected_job_id: state.selectedId,
          app_tab: state.appTab,
          attachment_ids: attachments.map(item => item.id),
          goal_mode: goalMode,
          model: modelId,
        },
        "globalCodexThinking", messages, aiLabel,
      );
      $("#globalCodexThinking")?.remove();
      setChatMessagesHtmlIfChanged(messages, result.history || [], { force: true });
      if (result.selected_job_id) state.selectedId = result.selected_job_id;
      await loadJobs(true);
      await applyProducerUiActions(result.ui_actions || []);
      await refreshGlobalCodexContext();
    } catch (err) {
      $("#globalCodexThinking")?.remove();
      state.globalCodexAttachments = attachments;
      renderAttachments();
      messages.insertAdjacentHTML("beforeend", `<div class="producer-codex-error">${escapeHtml(err.message)}</div>`);
      messages.scrollTop = messages.scrollHeight;
    } finally {
      delete state.chatRunConnections.globalCodexThinking;
      input.disabled = false;
      if (imageInput) imageInput.disabled = false;
      send.disabled = false;
      hint.textContent = "Enter để gửi · Shift+Enter xuống dòng · /compact nén ngữ cảnh · /new phiên mới";
      if (state.globalCodexOpen) input.focus();
    }
  };
  const goalToggle = $("#globalCodexGoalToggle");
  if (goalToggle) {
    goalToggle.onchange = () => syncGoalModeToggles(goalToggle.checked);
  }
  resumeStoredProducerChatRun("globalCodexThinking", messages);
}

async function applyProducerUiActions(actions = []) {
  for (const action of actions) {
    if (!action || typeof action !== "object") continue;
    if (action.type === "select_job" && action.job_id) {
      const previousId = state.selectedId;
      state.selectedId = String(action.job_id);
      state.userPinnedJobId = state.selectedId;
      try { localStorage.setItem("cofi-selected-job-id", state.selectedId); } catch (_) {}
      state.workspaceRenderKeys = {};
      state.detailTab = "tongquan";
      await loadJobs(true);
      await renderDetail();
      await renderFunctionWorkspaces();
      if (previousId !== state.selectedId) await refreshProducerChatsForSelection();
      continue;
    }
    if (action.type === "navigate" && action.tab) {
      setAppTab(String(action.tab));
      continue;
    }
    if (action.type === "fill_create_form") {
      applyCreativeProposalToCreateForm(action.payload || action.draft || action, {
        switchTab: Boolean(action.switch_tab ?? false),
      });
      continue;
    }
    if (
      action.type === "refresh_workspace" ||
      action.type === "update_script" ||
      action.type === "update_creative_brief" ||
      action.type === "update_outline" ||
      action.type === "approve_step"
    ) {
      if (action.job_id && state.jobs.some(j => j.id === String(action.job_id))) {
        state.selectedId = String(action.job_id);
        state.userPinnedJobId = state.selectedId;
        try { localStorage.setItem("cofi-selected-job-id", state.selectedId); } catch (_) {}
      }
      if (action.tab) delete state.workspaceRenderKeys[String(action.tab)];
      else state.workspaceRenderKeys = {};
      await loadJobs(true);
      await renderDetail();
      await renderFunctionWorkspaces();
      continue;
    }
    if (action.type === "save_playbook") {
      await loadPlaybooks();
      toast("AI đã lưu Playbook Kênh mới.");
      continue;
    }
    if (action.type === "radar_results") {
      const items = Array.isArray(action.items) ? action.items : [];
      if (action.scan_id) await fetchMarketFeed(Number(action.scan_id));
      else renderRadarResults(items);
      const hint = $("#radarResultHint");
      if (hint && !action.scan_id) hint.textContent = `Đề xuất hôm nay · ${items.length} chủ đề`;
    }
  }
}

async function followSourceRepairs(actions = [], messages) {
  const repairIds = actions
    .filter(action => action?.type === "repair_code" && action?.repair_job?.id)
    .map(action => String(action.repair_job.id));
  const terminalStatuses = new Set(["fixed", "failed"]);
  await Promise.all(repairIds.map(async repairId => {
    const elementId = `sourceRepair-${repairId.replace(/[^a-zA-Z0-9_-]/g, "")}`;
    messages?.insertAdjacentHTML("beforeend", `<div class="repair-live-card" id="${elementId}"><div class="repair-live-title">Đang khởi tạo tác vụ sửa code…</div></div>`);
    while (true) {
      const job = await api(`/api/source-repairs/${encodeURIComponent(repairId)}`);
      const status = String(job.status || "");
      const node = document.getElementById(elementId);
      if (node) node.innerHTML = repairProgressHtml(job);
      if (node) node.className = `repair-live-card ${escapeHtml(status)}`;
      if (terminalStatuses.has(status)) break;
      await new Promise(resolve => setTimeout(resolve, 750));
    }
    if (messages) messages.scrollTop = messages.scrollHeight;
  }));
}

function repairProgressHtml(job = {}) {
  const status = String(job.status || "queued");
  const percent = Math.max(0, Math.min(100, Number(job.progress_percent || 0)));
  const provider = String(job.provider_used || job.provider || "auto");
  const live = job.live || {};
  const labels = {
    queued: "Đang chờ", running: "Đang sửa code", verifying: "Đang kiểm thử",
    fixed: "Đã sửa code và kiểm thử đạt", failed: "Sửa code chưa đạt",
  };
  const events = Array.isArray(job.stream_events) ? job.stream_events.slice(-24) : [];
  const log = events.length
    ? events.map(event => `<div class="repair-log-line ${escapeHtml(event.kind || "log")}"><span>${escapeHtml(event.kind || "log")}</span><p>${escapeHtml(event.message || "")}</p></div>`).join("")
    : `<div class="repair-log-empty">Đang chờ sự kiện đầu tiên từ CLI…</div>`;
  const message = status === "failed"
    ? (job.error_message || live.message || "Kiểm thử hoặc CLI thất bại")
    : (live.message || labels[status] || status);
  return `<div class="repair-live-head"><div><span>${escapeHtml(provider.toUpperCase())}</span><strong>${escapeHtml(labels[status] || status)}</strong></div><b>${Math.round(percent)}%</b></div>
    <div class="repair-live-meter"><i style="width:${percent}%"></i></div>
    <p class="repair-live-message">${escapeHtml(message)}</p>
    <div class="repair-live-log">${log}</div>`;
}

async function renderProducerChat() {
  const messages = $("#producerCodexMessages");
  const form = $("#producerCodexForm");
  if (!messages || !form) return;
  syncChatModelSelects();
  syncGoalModeToggles();
  const job = state.jobs.find(item => item.id === state.selectedId);
  $("#producerCodexProjectLabel").textContent = selectedProjectLabel(job);
  $("#producerCodexContext").innerHTML = producerCodexContextHtml();
  if (!state.chatRunConnections.producerCodexThinking && !document.getElementById("producerCodexThinking")) {
    const history = await api(producerChatHistoryUrl());
    if (!state.chatRunConnections.producerCodexThinking && !document.getElementById("producerCodexThinking")) {
      setChatMessagesHtmlIfChanged(messages, history);
    }
  }

  const input = $("#producerCodexInput");
  const imageInput = $("#producerCodexImageInput");
  const attachmentPreview = $("#producerCodexAttachmentPreview");
  bindChatContainerInteractions(messages, input, form);
  const renderAttachments = () => renderPendingChatAttachments(attachmentPreview, state.producerChatAttachments, id => {
    state.producerChatAttachments = state.producerChatAttachments.filter(item => item.id !== id);
    renderAttachments();
  });
  renderAttachments();
  const producerClear = $("#producerCodexClearBtn");
  if (producerClear) producerClear.onclick = () => clearCurrentProducerChatHistory().catch(err => toast(err.message, true));
  if ($("#producerCodexNewBtn")) {
    $("#producerCodexNewBtn").onclick = () => startNewProducerChatSession().catch(err => toast(err.message, true));
  }
  if ($("#producerCodexCompactBtn")) {
    $("#producerCodexCompactBtn").onclick = () => compactCurrentProducerChatSession().catch(err => toast(err.message, true));
  }
  const producerClose = $("#producerCodexCloseBtn");
  if (producerClose) producerClose.onclick = () => setAppTab("overview");
  if (imageInput) imageInput.onchange = async () => {
    try {
      state.producerChatAttachments = await appendSelectedChatImages(imageInput.files, state.producerChatAttachments, next => {
        state.producerChatAttachments = next;
        renderAttachments();
      });
    } catch (err) {
      toast(err.message, true);
    } finally {
      imageInput.value = "";
    }
  };
  input.onpaste = async event => {
    try {
      state.producerChatAttachments = await appendPastedChatImages(event, state.producerChatAttachments, next => {
        state.producerChatAttachments = next;
        renderAttachments();
      });
    } catch (err) {
      toast(err.message, true);
    }
  };
  $("#editChatInput")?.addEventListener("paste", input.onpaste);
  input.onkeydown = event => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      form.requestSubmit();
    }
  };
  form.onsubmit = async event => {
    event.preventDefault();
    const message = input.value.trim();
    const attachments = [...state.producerChatAttachments];
    if (attachments.some(item => item.uploading)) {
      toast("Vui lòng đợi ảnh tải lên hoàn tất.", true);
      return;
    }
    if (!message && !attachments.length) return;
    const send = $("#producerCodexSendBtn");
    const hint = $("#producerCodexHint");
    input.value = "";
    state.producerChatAttachments = [];
    renderAttachments();
    input.disabled = true;
    if (imageInput) imageInput.disabled = true;
    send.disabled = true;
    const aiLabel = selectedAiLabel();
    const modelId = currentChatModelId();
    hint.textContent = `${aiLabel} đang xử lý yêu cầu trong Cofi Documentary…`;
    state.chatRunConnections.producerCodexThinking = "starting";
    messages.querySelector(".producer-codex-empty")?.remove();
    messages.insertAdjacentHTML("beforeend", `<div class="producer-codex-message user agy-msg-user"><div class="agy-msg-head"><span class="agy-role-user">Bạn</span></div>${message ? `<div class="agy-user-text">${escapeHtml(message).replace(/\n/g, "<br>")}</div>` : ""}${chatAttachmentGalleryHtml(attachments)}</div><div class="producer-codex-thinking" id="producerCodexThinking">${escapeHtml(aiLabel)} đang xử lý…</div>`);
    renderChatLiveProgress(document.getElementById("producerCodexThinking"), aiLabel, [], "starting", "Đang kết nối…");
    messages.scrollTop = messages.scrollHeight;
    try {
      const goalToggle = $("#producerCodexGoalToggle");
      const goalMode = Boolean(goalToggle?.checked) || /^\/goal\b/i.test(message);
      if (!goalMode && modelId === "codex") await waitForCodexWebPacing();
      const result = await streamProducerChat(
        {
          message,
          selected_job_id: state.selectedId,
          app_tab: state.appTab,
          attachment_ids: attachments.map(item => item.id),
          goal_mode: goalMode,
          model: modelId,
        },
        "producerCodexThinking", messages, aiLabel,
      );
      $("#producerCodexThinking")?.remove();
      setChatMessagesHtmlIfChanged(messages, result.history || [], { force: true });
      if (result.selected_job_id) state.selectedId = result.selected_job_id;
      await loadJobs(true);
      $("#producerCodexProjectLabel").textContent = selectedProjectLabel(state.jobs.find(item => item.id === state.selectedId));
      $("#producerCodexContext").innerHTML = producerCodexContextHtml();
      await applyProducerUiActions(result.ui_actions || []);
    } catch (err) {
      $("#producerCodexThinking")?.remove();
      state.producerChatAttachments = attachments;
      renderAttachments();
      messages.insertAdjacentHTML("beforeend", `<div class="producer-codex-error">${escapeHtml(err.message)}</div>`);
      messages.scrollTop = messages.scrollHeight;
    } finally {
      delete state.chatRunConnections.producerCodexThinking;
      input.disabled = false;
      if (imageInput) imageInput.disabled = false;
      send.disabled = false;
      hint.textContent = "Enter để gửi · Shift+Enter xuống dòng · /compact nén ngữ cảnh · /new phiên mới";
      if (state.appTab === "codex") input.focus();
    }
  };
  const goalToggle = $("#producerCodexGoalToggle");
  if (goalToggle) {
    goalToggle.onchange = () => syncGoalModeToggles(goalToggle.checked);
  }
  resumeStoredProducerChatRun("producerCodexThinking", messages);
}

function phaseActionHtml(job, phase) {
  const info = job.phases?.[phase] || {};
  const status = info.status || "pending";
  if (!canRun(job, phase)) return `<span class="workspace-phase-state">${escapeHtml(statusLabels[status] || status)}</span>`;
  const index = effectivePhases(job).indexOf(phase);
  const label = status === "pending" ? (index === 0 ? "Chạy bước 1" : `Duyệt xong · Chạy ${phaseLabels[phase]}`) : `Chạy lại ${phaseLabels[phase]}`;
  return `<button class="primary compact" data-workspace-run-phase="${phase}">${escapeHtml(label)}</button>`;
}

function phaseStepPanelHtml(job, phase, nextTab = null, hideActions = false) {
  const info = job.phases?.[phase] || {};
  const status = info.status || "pending";
  const active = effectivePhases(job);
  const index = active.indexOf(phase);
  if (index < 0) {
    return `<section class="step-status-card pending"><div class="step-status-main"><span class="step-number">BỎ QUA</span><div><strong>${escapeHtml(phaseLabels[phase] || phase)}</strong><small>Bước này không thuộc chiến lược hình ảnh của dự án hiện tại.</small></div><b>Không chạy</b></div></section>`;
  }
  const nextPhase = active[index + 1] || null;
  let primary = "";
  let secondary = "";
  let guidance = "";
  if (status === "running" || status === "queued") {
    guidance = "Bước này đang chạy. Kết quả sẽ cập nhật ngay trong tab này khi hoàn tất (có thể điều chỉnh hoặc bàn tiếp bên Chat).";
  } else if (status === "succeeded") {
    guidance = nextTab
      ? "Đã hoàn tất. Bạn có thể sửa trực tiếp bên dưới, nhắn bên Chat để AI chỉnh/duyệt, hoặc bấm Duyệt thủ công ngay tại đây."
      : "Đã hoàn tất. Bạn có thể sửa trực tiếp hoặc nhắn bên Chat để tinh chỉnh.";
    if (nextPhase) {
      primary = `<button class="primary compact" data-workspace-approve-next="${escapeHtml(nextTab || "")}">✓ Duyệt & Chạy bước ${index + 2}: ${escapeHtml(phaseLabels[nextPhase] || "Tiếp theo")}</button>`;
    } else if (nextTab) {
      primary = `<button class="primary compact" data-open-step="${escapeHtml(nextTab)}">Sang bước tiếp theo</button>`;
    }
    secondary = `${nextTab && nextPhase ? `<button class="ghost compact" data-open-step="${escapeHtml(nextTab)}">Mở tab ${escapeHtml(phaseLabels[nextPhase] || "Tiếp theo")}</button>` : ""}<button class="ghost compact" data-workspace-run-phase="${phase}">↻ Tạo lại bước này</button>`;
  } else if ((status === "failed" || status === "interrupted") && canRun(job, phase)) {
    guidance = "Bước này bị lỗi hoặc tạm dừng. Bạn có thể nhắn bên Chat hoặc bấm Chạy lại ngay tại đây.";
    primary = `<button class="primary compact" data-workspace-run-phase="${phase}">↻ Chạy lại ${escapeHtml(phaseLabels[phase])}</button>`;
  } else if (canRun(job, phase)) {
    guidance = index === 0 ? "Sẵn sàng bắt đầu." : "Bước trước đã hoàn tất. Có thể chạy bước này hoặc nhắn bên Chat.";
    primary = `<button class="primary compact" data-workspace-run-phase="${phase}">▶ Chạy bước ${index + 1}: ${escapeHtml(phaseLabels[phase])}</button>`;
  } else {
    const previous = active[index - 1];
    const runningPhase = job.current_phase && active.includes(job.current_phase) ? job.current_phase : null;
    const runningIndex = runningPhase ? active.indexOf(runningPhase) : -1;
    if (runningPhase && runningPhase !== phase) {
      guidance = `Dự án này đang chạy Bước ${runningIndex + 1} (${phaseLabels[runningPhase] || runningPhase}). Để xem dữ liệu dự án cũ đã hoàn thành, hãy chọn dự án đó ở mục "Dự án đang mở" góc trên phải.`;
      const runningTab = phaseWorkspaceTab(runningPhase);
      if (runningTab) {
        secondary = `<button class="ghost compact" data-open-step="${escapeHtml(runningTab)}">↪ Mở Bước ${runningIndex + 1} đang chạy (${escapeHtml(phaseLabels[runningPhase] || runningPhase)})</button>`;
      }
    } else {
      guidance = previous ? `Hãy hoàn tất ${phaseLabels[previous]} trước.` : "Chưa sẵn sàng.";
    }
  }
  const qcDone = job.phases?.qc?.status === "succeeded" || job.status === "succeeded" || job.status === "completed";
  const saveVideoQuickHtml = qcDone
    ? `<button type="button" class="primary compact" data-local-save-job="${escapeHtml(job.id)}" data-local-save-path="release/video.mp4" style="background:linear-gradient(135deg,#10b981,#059669);border-color:#34d399;color:#ffffff;font-weight:800;" title="Mở hộp thoại chọn thư mục (cho phép đổi tên) và chuyển thẳng video gốc sang thư mục chọn">💾 Lưu Video (.MP4)</button>`
    : "";
  return `<section class="step-status-card ${escapeHtml(status)}">
    <div class="step-status-main"><span class="step-number">BƯỚC ${index + 1}</span><div><strong>${escapeHtml(phaseLabels[phase])}</strong><small>${escapeHtml(guidance)}</small></div><b>${escapeHtml(statusLabels[status] || status)}</b></div>
    ${info.error ? `<div class="step-error"><strong>Lỗi ở bước này</strong><p>${escapeHtml(info.error)}</p></div>` : ""}
    ${!hideActions && (primary || secondary || saveVideoQuickHtml) ? `<div class="step-actions">${saveVideoQuickHtml}${primary}${secondary}</div>` : ""}
  </section>`;
}


function safeJson(raw, fallback = {}) {
  if (!raw) return fallback;
  try { return JSON.parse(raw); } catch (_) { return fallback; }
}

function jobMediaVersionToken(jobId) {
  const job = state.jobs.find(j => j.id === jobId);
  if (!job) return "";
  const p = job.phases || {};
  const live = state.realtimeLive?.job_id === jobId ? state.realtimeLive : {};
  return [job.updated_at || "", p.voice?.finished_at || "", p.ai_visual?.finished_at || "", p.edit?.finished_at || "", p.qc?.finished_at || "", live.voice_mtime || "", live.live_edit_mtime || "", live.render_mtime || ""].filter(Boolean).join("_");
}

function mediaUrl(jobId, path) {
  if (!path) return "";
  const v = jobMediaVersionToken(jobId);
  return `/api/jobs/${encodeURIComponent(jobId)}/media?path=${encodeURIComponent(path)}${v ? `&v=${encodeURIComponent(v)}` : ""}`;
}

function mediaPosterUrl(jobId, path) {
  if (!path) return "";
  const v = jobMediaVersionToken(jobId);
  return `/api/jobs/${encodeURIComponent(jobId)}/media?path=${encodeURIComponent(path)}&poster=1${v ? `&v=${encodeURIComponent(v)}` : ""}`;
}

async function runWorkspacePhase(job, phase) {
  const status = job.phases?.[phase]?.status;
  const url = status && status !== "pending" ? `/api/jobs/${encodeURIComponent(job.id)}/rerun/${phase}` : `/api/jobs/${encodeURIComponent(job.id)}/run/${phase}`;
  await api(url, { method: "POST" });
  toast(`Đã bắt đầu: ${phaseLabels[phase]}.`);
  await refreshAll();
}

function footageControlsHtml(job, checkpoint = {}) {
  const phaseStatus = String(job.phases?.footage?.status || "pending").toLowerCase();
  const controlState = String(checkpoint.control_state || "running").toLowerCase();
  const buttons = [];
  if (["running", "queued"].includes(phaseStatus)) {
    if (controlState === "paused") {
      buttons.push(`<button class="primary compact" data-footage-control="resume">▶ Tiếp tục</button>`);
      buttons.push(`<button class="ghost compact" data-footage-control="stop">■ Dừng</button>`);
    } else if (controlState === "stop_requested") {
      buttons.push(`<button class="ghost compact" disabled>Đang dừng…</button>`);
    } else {
      buttons.push(`<button class="ghost compact" data-footage-control="pause">Ⅱ Tạm dừng</button>`);
      buttons.push(`<button class="ghost compact" data-footage-control="stop">■ Dừng</button>`);
    }
  } else if (canRun(job, "footage")) {
    if (phaseStatus === "pending") {
      buttons.push(`<button class="primary compact" data-footage-control="run">▶ Chạy tìm bằng tools</button>`);
    } else if (Number(checkpoint.completed_beats || 0) > 0 && Number(checkpoint.completed_beats || 0) < Number(checkpoint.total_beats || 0)) {
      buttons.push(`<button class="primary compact" data-footage-control="run">▶ Tiếp tục từ checkpoint (${escapeHtml(checkpoint.completed_beats)}/${escapeHtml(checkpoint.total_beats)})</button>`);
      buttons.push(`<button class="ghost compact" data-footage-control="rerun">↻ Tìm lại từ đầu</button>`);
    } else {
      buttons.push(`<button class="primary compact" data-footage-control="rerun">↻ Tìm lại bằng tools</button>`);
    }
  }
  if (phaseStatus === "succeeded") {
    const isHybridLike = ["hybrid", "evidence_footage", "selective_footage", "evidence_first"].includes(String(job.visual_strategy || "full_footage").toLowerCase());
    const nextTab = isHybridLike ? "ai_visual" : "edit";
    buttons.push(`<button class="ghost compact" data-open-step="${nextTab}">Sang bước ${escapeHtml(phaseLabels[nextTab])}</button>`);
  }
  return `<section class="workspace-toolbar footage-control-toolbar">
    <div><strong>Điều khiển Footage</strong><small>Tools tự tìm/tải/rank. ${escapeHtml(selectedAiLabel())} chỉ duyệt candidate đã tải; AI không tự research web.</small></div>
    <div class="step-actions">${buttons.join("") || `<span class="workspace-phase-state">${escapeHtml(statusLabels[phaseStatus] || phaseStatus)}</span>`}</div>
  </section>`;
}

function bindFootageVideoPlaceholders(root = document) {
  root.querySelectorAll(".footage-video-placeholder").forEach(placeholder => {
    if (placeholder.dataset.boundVideoTrigger) return;
    placeholder.dataset.boundVideoTrigger = "1";
    placeholder.addEventListener("click", (e) => {
      e.stopPropagation();
      const videoSrc = placeholder.dataset.footageVideoSrc || placeholder.dataset.aiVideoSrc;
      const mediaKey = placeholder.dataset.footageMediaKey;
      if (!videoSrc) return;
      root.querySelectorAll("video.footage-active-video").forEach(v => {
        try { v.pause(); } catch (_) {}
      });
      const video = document.createElement("video");
      video.className = "footage-active-video";
      video.controls = true;
      video.autoplay = true;
      video.playsInline = true;
      video.preload = "auto";
      video.src = videoSrc;
      if (mediaKey) video.dataset.footageMediaKey = mediaKey;
      placeholder.replaceWith(video);
      video.play().catch(() => {});
    });
  });
}

function openAiVisualCardsDialog() {
  const dialog = $("#aiVisualCardsDialog");
  if (!dialog) return;
  if (typeof dialog.showModal === "function") {
    if (!dialog.open) dialog.showModal();
  } else dialog.setAttribute("open", "");
  bindFootageVideoPlaceholders(dialog);
  const currentJob = state.jobs.find(item => item.id === state.selectedId);
  if (currentJob) {
    const fallbackTargets = Number(lastAiVisualRuntimeSnapshot?.job?.targets || 0);
    syncAiVisualDialogFromDisk(currentJob, fallbackTargets);
  }
}

function closeAiVisualCardsDialog() {
  const dialog = $("#aiVisualCardsDialog");
  if (!dialog) return;
  if (typeof dialog.close === "function" && dialog.open) dialog.close();
  else dialog.removeAttribute("open");
}

$("#closeAiVisualCardsDialog")?.addEventListener("click", closeAiVisualCardsDialog);
$("#aiVisualCardsDialog")?.addEventListener("click", event => {
  if (event.target === event.currentTarget) closeAiVisualCardsDialog();
});

window.addEventListener("keydown", event => {
  if (event.key === "Escape") {
    const fullCard = document.querySelector(".cofistudio-embed-card.is-fullscreen");
    if (fullCard) {
      fullCard.classList.remove("is-fullscreen");
      const btn = document.querySelector("#fullscreenCofiStudioBtn");
      if (btn) btn.textContent = "⛶ Phóng to";
    }
  }
});

function bindFootageControlButtons(job, root = document) {
  [...root.querySelectorAll('[data-footage-control]')].forEach(button => button.addEventListener("click", async () => {
    const action = String(button.dataset.footageControl || "");
    button.disabled = true;
    const fRoot = $("#footageWorkspace");
    if (fRoot) fRoot.dataset.footageRenderSignature = "";
    try {
      if (action === "run") {
        await api(`/api/jobs/${encodeURIComponent(job.id)}/run/footage`, { method: "POST" });
        toast("Đã chạy Footage: tools tìm/tải/rank → AI đã chọn duyệt.");
      } else if (action === "rerun") {
        await api(`/api/jobs/${encodeURIComponent(job.id)}/rerun/footage`, { method: "POST" });
        toast("Đã tìm lại từ đầu bằng Footage tools; cache lượt cũ được lưu vào history.");
      } else {
        await api(`/api/jobs/${encodeURIComponent(job.id)}/footage/${action}`, { method: "POST" });
        const message = action === "pause" ? "Đã yêu cầu tạm dừng Footage." : action === "resume" ? "Đã tiếp tục Footage." : "Đã yêu cầu dừng Footage.";
        toast(message);
      }
      await refreshAll();
    } catch (err) {
      toast(err.message, true);
      button.disabled = false;
    }
  }));
}

function bindWorkspacePhaseButtons(job, root = document) {
  [...root.querySelectorAll('[data-workspace-run-phase]')].forEach(btn => btn.addEventListener("click", async () => {
    try { await runWorkspacePhase(job, btn.dataset.workspaceRunPhase); }
    catch (err) { toast(err.message, true); }
  }));
  [...root.querySelectorAll('[data-workspace-approve-next]')].forEach(btn => btn.addEventListener("click", async () => {
    btn.disabled = true;
    try {
      const nextTab = btn.dataset.workspaceApproveNext;
      const res = await api(`/api/jobs/${encodeURIComponent(job.id)}/approve-next`, { method: "POST" });
      if (nextTab) setAppTab(nextTab);
      toast(`Đã duyệt và chuyển sang: ${phaseLabels[res.next_phase] || res.next_phase || "bước tiếp theo"}.`);
      await refreshAll();
    } catch (err) {
      toast(err.message, true);
      btn.disabled = false;
    }
  }));
  [...root.querySelectorAll('[data-open-step]')].forEach(btn => btn.addEventListener("click", () => setAppTab(btn.dataset.openStep)));
}

function formatStoryboardTime(sec) {
  const value = Number(sec);
  if (!Number.isFinite(value) || value < 0) return "—";
  const mins = Math.floor(value / 60);
  const secs = Math.floor(value % 60);
  return `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
}

function storyboardTableHtml(visualRaw, promptsRaw = "") {
  let manifest = null;
  try { manifest = visualRaw ? JSON.parse(visualRaw) : null; } catch (_) {}
  let promptsData = null;
  try { promptsData = promptsRaw ? JSON.parse(promptsRaw) : null; } catch (_) {}
  const beats = Array.isArray(manifest?.beats)
    ? manifest.beats
    : Array.isArray(manifest?.segments)
      ? manifest.segments
      : Array.isArray(manifest)
        ? manifest
        : [];
  const promptRows = Array.isArray(promptsData?.items)
    ? promptsData.items
    : Array.isArray(promptsData?.prompts)
      ? promptsData.prompts
      : Array.isArray(promptsData)
        ? promptsData
        : [];
  const rows = beats.length ? beats : promptRows;
  if (!rows.length) return "";
  const promptByBeat = new Map();
  promptRows.forEach(item => {
    const key = String(item?.beat_id || item?.id || item?.parent_beat_id || "");
    if (key && !promptByBeat.has(key)) promptByBeat.set(key, item);
  });
  return `<section class="storyboard-card">
    <div class="storyboard-head">
      <div><span>STORYBOARD · BẢNG PHÂN CẢNH</span><strong>${rows.length} phân cảnh đã đồng bộ lời thoại & định hướng hình ảnh</strong></div>
      <small> Bấm mở phần chi tiết kỹ thuật bên dưới nếu cần xem JSON gốc</small>
    </div>
    <div class="storyboard-table-wrap">
      <table class="storyboard-table">
        <thead>
          <tr>
            <th>Beat</th>
            <th>Thời gian</th>
            <th>Lời thoại (Narration)</th>
            <th>Định hướng hình ảnh / Prompt</th>
            <th>Nguồn</th>
          </tr>
        </thead>
        <tbody>
          ${rows.slice(0, 120).map((beat, idx) => {
            const beatId = String(beat.beat_id || beat.id || `B${String(idx + 1).padStart(2, "0")}`);
            const matchedPrompt = promptByBeat.get(beatId) || {};
            const start = beat.start_sec ?? beat.start ?? matchedPrompt.start_sec;
            const end = beat.end_sec ?? beat.end ?? matchedPrompt.end_sec;
            const timeLabel = start != null ? `${formatStoryboardTime(start)}${end != null ? ` – ${formatStoryboardTime(end)}` : ""}` : (beat.duration_sec ? `${beat.duration_sec}s` : "—");
            const narration = beat.narration || beat.text || beat.voice_text || matchedPrompt.narration || "—";
            const visualPrompt = matchedPrompt.prompt || beat.visual_prompt || beat.prompt || beat.visual_direction || beat.description || beat.search_query || "—";
            const routeRaw = String(matchedPrompt.route || beat.route || beat.visual_source || beat.source_type || "auto").toLowerCase();
            const isAi = routeRaw.includes("ai");
            const routeBadge = isAi ? "AI Visual" : routeRaw.includes("footage") ? "Footage" : routeRaw.toUpperCase();
            return `<tr>
              <td class="storyboard-beat-id"><b>${escapeHtml(beatId)}</b></td>
              <td class="storyboard-time">${escapeHtml(timeLabel)}</td>
              <td class="storyboard-narration">${escapeHtml(narration)}</td>
              <td class="storyboard-prompt">${escapeHtml(visualPrompt)}</td>
              <td><span class="storyboard-route-badge ${isAi ? "ai" : "footage"}">${escapeHtml(routeBadge)}</span></td>
            </tr>`;
          }).join("")}
        </tbody>
      </table>
    </div>
  </section>`;
}

async function renderScriptWorkspace(job, { force = false } = {}) {
  $("#scriptProjectLabel").textContent = selectedProjectLabel(job);
  const root = $("#scriptWorkspace");
  if (!job) {
    root.dataset.scriptSignature = "";
    return root.innerHTML = `<div class="empty-state">Chọn một dự án ở tab Dự án để xem kịch bản.</div>`;
  }
  const activeEl = document.activeElement;
  const isEditingInput = !force && root.contains(activeEl) && ["INPUT", "TEXTAREA", "SELECT"].includes(activeEl?.tagName || "");
  if (isEditingInput && (activeEl?.id !== "scriptDirectEditorTextarea" || activeEl?.dataset?.dirty === "1")) {
    return;
  }
  const [script, research, visual, outlineRes] = await Promise.all([
    artifact(job.id, "script.md"),
    artifact(job.id, "research.md"),
    artifact(job.id, "visual_manifest.json"),
    api(`/api/jobs/${encodeURIComponent(job.id)}/outline`).catch(() => ({ outline: job.outline || {}, creative_brief: job.creative_brief || {} })),
  ]);
  if (isEditingInput && activeEl?.id === "scriptDirectEditorTextarea" && activeEl?.dataset?.dirty !== "1") {
    const nextScript = String(script || "");
    if (activeEl.value !== nextScript) {
      const prevScrollTop = activeEl.scrollTop;
      activeEl.value = nextScript;
      activeEl.scrollTop = prevScrollTop;
    }
    return;
  }
  const outlineObj = outlineRes?.outline || job.outline || {};
  const chapters = Array.isArray(outlineObj?.chapters) ? outlineObj.chapters : [];
  const brief = {
    ...(job.creative_brief || {}),
    ...(outlineRes?.creative_brief || {}),
  };
  const activePlaybookId = String(brief.playbook_id || job.playbook_id || "");
  const activeAngleRaw = String(brief.narrative_angle || "investigative_forensic");
  const activeStyleRaw = String(brief.writing_style || "cold_dossier");
  const activeHookRaw = String(brief.hook_archetype || "shocking_anomaly");
  const activeAngleDisplay = CREATIVE_LABELS.narrative_angles[activeAngleRaw] || activeAngleRaw;
  const activeStyleDisplay = CREATIVE_LABELS.writing_styles[activeStyleRaw] || activeStyleRaw;
  const activeHookDisplay = CREATIVE_LABELS.hook_archetypes[activeHookRaw] || activeHookRaw;
  const activeArchetypes = parseEditingArchetypesValue(brief.editing_archetypes);
  const activeArchetypesDisplay = formatEditingArchetypesDisplay(
    activeArchetypes.length ? activeArchetypes : ["forensic_red_string", "vox_blueprint_explainer"],
  );
  const openingHook = String(brief.opening_hook || outlineObj?.opening_hook || "");
  const customRules = String(brief.custom_rules || job.notes || "");

  const sig = JSON.stringify({
    id: job.id,
    planStatus: job.phases?.plan?.status || "",
    playbook: activePlaybookId,
    angle: activeAngleDisplay,
    style: activeStyleDisplay,
    hook: activeHookDisplay,
    archetypes: activeArchetypesDisplay,
    openingHook,
    customRules,
    chaptersCount: chapters.length,
    chaptersSig: chapters.map(c => `${c.title || ""}:${c.summary || ""}:${c.evidence_anchor || ""}`).join("|"),
    scriptText: String(script || ""),
    visualLen: String(visual || "").length,
    playbooksCount: (state.playbooks || []).length,
  });
  if (!force && root.dataset.scriptSignature === sig && root.children.length > 0) {
    return;
  }
  root.dataset.scriptSignature = sig;

  const playbooks = Array.isArray(state.playbooks) ? state.playbooks : [];
  const storyboard = storyboardTableHtml(visual);
  let beatCount = 0;
  try {
    const parsedVis = typeof visual === "string" ? JSON.parse(visual) : visual;
    beatCount = Array.isArray(parsedVis?.beats) ? parsedVis.beats.length : 0;
  } catch {}
  const hasScriptText = Boolean(script && String(script).trim().length > 0);
  if (!state.scriptDrawerPrefs) state.scriptDrawerPrefs = {};
  if (!state.scriptSubtabPrefs) state.scriptSubtabPrefs = {};
  const jobDrawerPref = state.scriptDrawerPrefs[job.id] || {};
  const briefOpen = typeof jobDrawerPref.brief === "boolean" ? jobDrawerPref.brief : true;
  const outlineOpen = typeof jobDrawerPref.outline === "boolean" ? jobDrawerPref.outline : true;
  const activeScriptSubtab = state.scriptSubtabPrefs[job.id] || (hasScriptText ? "editor" : "blueprint");

  root.innerHTML = `${phaseStepPanelHtml(job, "plan", "voice")}
    <nav class="studio-subtabs-bar" aria-label="Chế độ xem Kịch bản & Phân cảnh">
      <div class="studio-subtabs-group">
        <button type="button" class="studio-subtab-btn ${activeScriptSubtab === "editor" ? "active" : ""}" data-script-subtab="editor">📝 Kịch bản (${hasScriptText ? `${String(script).length.toLocaleString("vi-VN")} ký tự` : "Soạn thảo"})</button>
        <button type="button" class="studio-subtab-btn ${activeScriptSubtab === "storyboard" ? "active" : ""}" data-script-subtab="storyboard">🎬 Phân cảnh (${beatCount})</button>
        <button type="button" class="studio-subtab-btn ${activeScriptSubtab === "blueprint" ? "active" : ""}" data-script-subtab="blueprint">🧭 Định hướng &amp; Dàn ý (${chapters.length})</button>
        <button type="button" class="studio-subtab-btn ${activeScriptSubtab === "research" ? "active" : ""}" data-script-subtab="research">🔬 Nghiên cứu &amp; JSON</button>
      </div>
      <div class="studio-subtabs-group">
        <button type="button" class="secondary compact" id="openScriptFullscreenReaderBtn">🗗 Mở Popup Đọc Kịch Bản</button>
      </div>
    </nav>

    <div class="script-subpane ${activeScriptSubtab === "blueprint" ? "" : "studio-subpane-hidden"}" data-script-subpane="blueprint">
      <div class="script-blueprint-summary-bar">
        <div class="script-summary-pills">
          <span class="script-summary-pill" title="${escapeHtml(activeAngleDisplay)}"><b>Góc nhìn:</b> ${escapeHtml(activeAngleDisplay.length > 46 ? activeAngleDisplay.slice(0, 46) + "…" : activeAngleDisplay)}</span>
          <span class="script-summary-pill" title="${escapeHtml(activeStyleDisplay)}"><b>Văn phong:</b> ${escapeHtml(activeStyleDisplay.length > 42 ? activeStyleDisplay.slice(0, 42) + "…" : activeStyleDisplay)}</span>
          <span class="script-summary-pill"><b>Dàn ý:</b> ${chapters.length} chương</span>
          <span class="script-summary-pill ${hasScriptText ? "is-ready" : ""}"><b>Kịch bản:</b> ${hasScriptText ? `${String(script).length.toLocaleString("vi-VN")} ký tự` : "Đang chờ / Chưa tạo"}</span>
          <span class="script-summary-pill ${beatCount > 0 ? "is-ready" : ""}"><b>Phân cảnh:</b> ${beatCount} cảnh</span>
        </div>
        <div class="script-summary-actions">
          <button type="button" class="ghost compact" id="scriptQuickToggleBriefBtn">${briefOpen ? "▾ Thu gọn Định hướng (1A)" : "▸ Mở Định hướng (1A)"}</button>
          <button type="button" class="ghost compact" id="scriptQuickToggleOutlineBtn">${outlineOpen ? "▾ Thu gọn Dàn ý (1B)" : `▸ Mở Dàn ý ${chapters.length} chương (1B)`}</button>
        </div>
      </div>
      <section class="script-blueprint-studio">
        <details class="script-brief-panel script-collapsible-panel" id="scriptBriefDetails" ${briefOpen ? "open" : ""}>
          <summary class="script-studio-header">
            <div class="script-header-title-wrap">
              <span class="eyebrow"><span class="script-Format-chevron">▸</span> TẦNG 1A · ĐỊNH HƯỚNG SÁNG TẠO & PLAYBOOK DỰ ÁN (BẤM ĐỂ MỞ / THU GỌN)</span>
              <strong>Góc nhìn Kể chuyện, Văn phong, Hook 30s & Ngữ pháp Dựng phim</strong>
            </div>
            <div class="script-studio-header-actions" onclick="event.stopPropagation()">
              <button type="button" class="ghost compact" id="scriptExtractPlaybookBtn">🧬 Đúc kết thành Playbook</button>
              <button type="button" class="primary compact" id="scriptSaveBriefBtn">💾 Lưu Định hướng</button>
            </div>
          </summary>
          <div class="creative-brief-grid">
            <label>
              <span>Playbook Kênh (Channel DNA)</span>
              <select id="scriptPlaybookSelect">
                <option value="">✨ Tự do sáng tạo / Theo cuộc trò chuyện AI</option>
                ${playbooks.map(pb => `<option value="${escapeHtml(pb.id)}" ${String(pb.id) === activePlaybookId ? "selected" : ""}>${pb.built_in ? "🏛️" : "🧬"} ${escapeHtml(pb.name)}</option>`).join("")}
              </select>
            </label>
            <label>
              <span>Góc nhìn kể chuyện (Narrative Angle — mở & linh hoạt)</span>
              <input type="text" id="scriptNarrativeAngle" list="narrativeAngleSuggestions" value="${escapeHtml(activeAngleDisplay)}" placeholder="Nhập tự do hoặc nhắn bên Chat để AI đổi góc nhìn..." />
            </label>
            <label>
              <span>Phong cách viết (Writing Style — mở & linh hoạt)</span>
              <input type="text" id="scriptWritingStyle" list="writingStyleSuggestions" value="${escapeHtml(activeStyleDisplay)}" placeholder="Nhập tự do hoặc nhắn bên Chat để AI đổi văn phong..." />
            </label>
            <label>
              <span>Cấu trúc Hook 30s đầu (linh hoạt)</span>
              <input type="text" id="scriptHookArchetype" list="hookArchetypeSuggestions" value="${escapeHtml(activeHookDisplay)}" placeholder="Nhập tự do hoặc nhắn bên Chat..." />
            </label>
            <label class="full-span">
              <span>Ngữ pháp Dựng phim & Visual Grammar (tự do kết hợp, phân tách bằng dấu phẩy)</span>
              <input type="text" id="scriptEditingArchetypesInput" list="editingArchetypeSuggestions" value="${escapeHtml(activeArchetypesDisplay)}" placeholder="VD: Bảng bằng chứng chỉ đỏ, Sơ đồ kỹ thuật giải phẫu, Split-Screen đối chiếu lịch sử..." />
            </label>
            <label class="full-span">
              <span>Hook mở đầu 30 giây đầu tiên (Opening Hook — khóa câu mở màn cho kịch bản)</span>
              <textarea id="scriptOpeningHookInput" rows="2" placeholder="Nhập câu mở màn hoặc nhắn bên Chat để AI viết lại Hook 30s...">${escapeHtml(openingHook)}</textarea>
            </label>
            <label class="full-span">
              <span>Chỉ dẫn đạo diễn / Luật riêng cho dự án (Custom Rules)</span>
              <textarea id="scriptCustomRulesInput" rows="2" placeholder="VD: Mỗi chương phải mở đầu bằng 1 con số tài chính thật; Cấm mở bài kiểu Wikipedia...">${escapeHtml(customRules)}</textarea>
            </label>
          </div>
        </details>

        <details class="script-outline-panel script-collapsible-panel" id="scriptOutlineDetails" ${outlineOpen ? "open" : ""}>
          <summary class="script-studio-header">
            <div class="script-header-title-wrap">
              <span class="eyebrow"><span class="script-Format-chevron">▸</span> TẦNG 1B · DÀN Ý CHƯƠNG HỒI & BẰNG CHỨNG (BẤM ĐỂ MỞ / THU GỌN)</span>
              <strong>${chapters.length ? `${chapters.length} chương đã định hình xương sống kịch bản` : "Chưa có dàn ý chương hồi — Bạn có thể nhắn bên Chat hoặc bấm tạo dàn ý"}</strong>
            </div>
            <div class="script-studio-header-actions" onclick="event.stopPropagation()">
              <button type="button" class="ghost compact" id="scriptAiGenerateOutlineBtn">✨ AI Tạo lại Dàn ý</button>
              <button type="button" class="ghost compact" id="scriptAddChapterBtn">+ Thêm chương</button>
              <button type="button" class="primary compact" id="scriptSaveOutlineBtn">💾 Lưu Dàn ý</button>
            </div>
          </summary>
          <div class="outline-chapters-list" id="scriptOutlineChaptersList">
            ${chapters.length ? chapters.map((ch, idx) => `
              <article class="outline-chapter-card" data-chapter-index="${idx}">
                <div class="outline-chapter-head">
                  <span class="outline-chapter-badge">CHƯƠNG ${String(idx + 1).padStart(2, "0")}</span>
                  <input type="text" class="outline-chapter-title" value="${escapeHtml(ch.title || ch.chapter_title || `Chương ${idx + 1}`)}" placeholder="Tiêu đề chương..." />
                  <input type="number" class="outline-chapter-minutes" min="1" max="20" step="0.5" value="${escapeHtml(String(ch.estimated_minutes || ch.duration_minutes || 3))}" title="Thời lượng dự kiến (phút)" />
                  <span class="outline-min-unit">phút</span>
                  <div class="outline-chapter-move-btns">
                    <button type="button" class="ghost compact" data-chapter-move="up" title="Đẩy lên">↑</button>
                    <button type="button" class="ghost compact" data-chapter-move="down" title="Đẩy xuống">↓</button>
                    <button type="button" class="ghost compact danger-text" data-chapter-delete="1" title="Xóa chương">✕</button>
                  </div>
                </div>
                <div class="outline-chapter-fields">
                  <label class="full-span">
                    <span>Mục tiêu giữ chân / Tóm tắt nội dung chương & Cliffhanger</span>
                    <textarea class="outline-chapter-summary" rows="2" placeholder="Chương này giải quyết câu hỏi gì, lật mở mâu thuẫn nào?">${escapeHtml(ch.summary || ch.goal_or_question || "")}</textarea>
                  </label>
                  <label>
                    <span>Bằng chứng thật / Con số / Tài liệu khóa sổ (Evidence Anchor)</span>
                    <input type="text" class="outline-chapter-evidence" value="${escapeHtml(ch.evidence_anchor || "")}" placeholder="VD: Báo cáo kiểm toán 2024, biên bản tòa án, con số 4.2 tỷ USD..." />
                  </label>
                  <label>
                    <span>Định hướng Visual & Nhịp dựng cho chương (Visual Grammar)</span>
                    <input type="text" class="outline-chapter-visual" value="${escapeHtml(ch.visual_note || ch.visual_direction || "")}" placeholder="VD: Bản đồ phóng to + Highlight tài liệu đỏ + Split-screen..." />
                  </label>
                </div>
                ${ch.ai_suggestion ? `<div class="outline-ai-suggestion"><span>💡 Đề xuất sáng tạo từ AI:</span> ${escapeHtml(ch.ai_suggestion)}</div>` : ""}
              </article>
            `).join("") : `
              <div class="empty-state outline-empty-state">
                <p>Chưa có Dàn ý Chương hồi cho dự án này. Bạn có thể nhắn bên Chat để bàn dàn ý với AI hoặc bấm <b>✨ AI Tạo lại Dàn ý</b>.</p>
              </div>
            `}
          </div>
        </details>
      </section>
    </div>

    <div class="script-subpane ${activeScriptSubtab === "editor" ? "" : "studio-subpane-hidden"}" data-script-subpane="editor">
      <div class="script-editor-panel">
        <div class="script-studio-header">
          <div>
            <span class="eyebrow">TẦNG 2 · KỊCH BẢN GIỌNG ĐỌC CHI TIẾT (FULL SCRIPT.MD)</span>
            <strong>Chỉnh sửa trực tiếp kịch bản hoặc nhắn bên Chat để AI sửa / viết lại theo ý bạn</strong>
          </div>
          <div class="script-studio-header-actions">
            <button type="button" class="primary compact" id="scriptSaveFullTextBtn">💾 Lưu Kịch bản (script.md)</button>
          </div>
        </div>
        <textarea id="scriptDirectEditorTextarea" class="script-direct-editor" rows="18" placeholder="Kịch bản chi tiết (script.md) sẽ hiển thị tại đây sau khi chạy Bước 01 (Lập kế hoạch & Viết kịch bản), hoặc bạn có thể soạn/chỉnh sửa trực tiếp tại đây...">${escapeHtml(script || "")}</textarea>
      </div>
    </div>

    <div class="script-subpane ${activeScriptSubtab === "storyboard" ? "" : "studio-subpane-hidden"}" data-script-subpane="storyboard">
      ${storyboard}
    </div>

    <div class="script-subpane ${activeScriptSubtab === "research" ? "" : "studio-subpane-hidden"}" data-script-subpane="research">
      <details class="technical-details" open><summary>Chi tiết kỹ thuật · Hồ sơ Nghiên cứu (research.md) &amp; Visual Manifest JSON</summary><div class="artifact-grid two-col">${codeViewer("Hồ sơ nghiên cứu (research.md)", research)}${codeViewer("Visual manifest", visual)}</div></details>
    </div>`;

  bindWorkspacePhaseButtons(job, root);

  root.querySelectorAll("[data-script-subtab]").forEach(btn => {
    btn.addEventListener("click", () => {
      const targetSubtab = btn.dataset.scriptSubtab;
      state.scriptSubtabPrefs[job.id] = targetSubtab;
      root.querySelectorAll("[data-script-subtab]").forEach(b => b.classList.toggle("active", b.dataset.scriptSubtab === targetSubtab));
      root.querySelectorAll("[data-script-subpane]").forEach(p => p.classList.toggle("studio-subpane-hidden", p.dataset.scriptSubpane !== targetSubtab));
    });
  });

  root.querySelector("#openScriptFullscreenReaderBtn")?.addEventListener("click", () => {
    const liveScript = String(root.querySelector("#scriptDirectEditorTextarea")?.value || script || "").trim();
    const fallbackText = liveScript || String(research || "").trim() || "Chưa có kịch bản cho dự án này.";
    openStudioInspectorModal({
      badge: "📝",
      title: job.title || "Kịch bản dự án",
      subtitle: liveScript ? `Kịch bản chi tiết (script.md) · ${liveScript.length.toLocaleString("vi-VN")} ký tự` : "Hồ sơ nghiên cứu (research.md)",
      rawText: fallbackText,
      isCode: false,
    });
  });

  const briefDetailsEl = root.querySelector("#scriptBriefDetails");
  const outlineDetailsEl = root.querySelector("#scriptOutlineDetails");
  const quickBriefBtn = root.querySelector("#scriptQuickToggleBriefBtn");
  const quickOutlineBtn = root.querySelector("#scriptQuickToggleOutlineBtn");
  const syncDrawerPref = () => {
    state.scriptDrawerPrefs[job.id] = {
      brief: Boolean(briefDetailsEl?.open),
      outline: Boolean(outlineDetailsEl?.open),
    };
    if (quickBriefBtn) quickBriefBtn.textContent = briefDetailsEl?.open ? "▾ Thu gọn Định hướng (1A)" : "▸ Mở Định hướng (1A)";
    if (quickOutlineBtn) quickOutlineBtn.textContent = outlineDetailsEl?.open ? "▾ Thu gọn Dàn ý (1B)" : `▸ Mở Dàn ý ${chapters.length} chương (1B)`;
  };
  briefDetailsEl?.addEventListener("toggle", syncDrawerPref);
  outlineDetailsEl?.addEventListener("toggle", syncDrawerPref);
  quickBriefBtn?.addEventListener("click", () => {
    if (!briefDetailsEl) return;
    briefDetailsEl.open = !briefDetailsEl.open;
    syncDrawerPref();
  });
  quickOutlineBtn?.addEventListener("click", () => {
    if (!outlineDetailsEl) return;
    outlineDetailsEl.open = !outlineDetailsEl.open;
    syncDrawerPref();
  });

  const collectBriefFromScriptStudio = () => ({
    playbook_id: String($("#scriptPlaybookSelect")?.value || "").trim() || null,
    narrative_angle: String($("#scriptNarrativeAngle")?.value || "investigative_forensic").trim(),
    writing_style: String($("#scriptWritingStyle")?.value || "cold_dossier").trim(),
    hook_archetype: String($("#scriptHookArchetype")?.value || "shocking_anomaly").trim(),
    editing_archetypes: getCheckedEditingArchetypes("#scriptEditingArchetypesInput"),
    opening_hook: String($("#scriptOpeningHookInput")?.value || "").trim(),
    custom_rules: String($("#scriptCustomRulesInput")?.value || "").trim(),
  });

  const collectChaptersFromScriptStudio = () => {
    const cards = [...root.querySelectorAll(".outline-chapter-card")];
    return cards.map((card, i) => ({
      chapter_id: `CH${String(i + 1).padStart(2, "0")}`,
      title: String(card.querySelector(".outline-chapter-title")?.value || `Chương ${i + 1}`).trim(),
      estimated_minutes: Number(card.querySelector(".outline-chapter-minutes")?.value || 3),
      summary: String(card.querySelector(".outline-chapter-summary")?.value || "").trim(),
      evidence_anchor: String(card.querySelector(".outline-chapter-evidence")?.value || "").trim(),
      visual_note: String(card.querySelector(".outline-chapter-visual")?.value || "").trim(),
    }));
  };

  $("#scriptPlaybookSelect")?.addEventListener("change", ev => {
    const pbId = String(ev.target.value || "").trim();
    const pb = (state.playbooks || []).find(item => String(item.id) === pbId);
    if (!pb) return;
    const pbBrief = pb.creative_brief || pb;
    if (pbBrief.narrative_angle && $("#scriptNarrativeAngle")) {
      $("#scriptNarrativeAngle").value = CREATIVE_LABELS.narrative_angles[pbBrief.narrative_angle] || pbBrief.narrative_angle;
    }
    if (pbBrief.writing_style && $("#scriptWritingStyle")) {
      $("#scriptWritingStyle").value = CREATIVE_LABELS.writing_styles[pbBrief.writing_style] || pbBrief.writing_style;
    }
    if (pbBrief.hook_archetype && $("#scriptHookArchetype")) {
      $("#scriptHookArchetype").value = CREATIVE_LABELS.hook_archetypes[pbBrief.hook_archetype] || pbBrief.hook_archetype;
    }
    if (pbBrief.editing_archetypes) {
      setCheckedEditingArchetypes(pbBrief.editing_archetypes, "#scriptEditingArchetypesInput");
    }
    if (pbBrief.custom_rules && $("#scriptCustomRulesInput")) $("#scriptCustomRulesInput").value = pbBrief.custom_rules;
    toast(`Đã nạp cấu hình Playbook "${pb.name}" — Bấm Lưu Định hướng để áp dụng.`);
  });

  $("#scriptSaveBriefBtn")?.addEventListener("click", async ev => {
    const btn = ev.currentTarget;
    btn.disabled = true;
    try {
      const nextBrief = collectBriefFromScriptStudio();
      await api(`/api/jobs/${encodeURIComponent(job.id)}/creative-brief`, {
        method: "PATCH",
        body: JSON.stringify({ playbook_id: nextBrief.playbook_id, creative_brief: nextBrief }),
      });
      await loadJobs(true);
      const updatedJob = state.jobs.find(j => j.id === job.id) || job;
      await renderScriptWorkspace(updatedJob, { force: true });
      toast("Đã lưu Định hướng Sáng tạo cho dự án.");
    } catch (err) {
      toast(err.message, true);
    } finally {
      btn.disabled = false;
    }
  });

  $("#scriptExtractPlaybookBtn")?.addEventListener("click", async ev => {
    const btn = ev.currentTarget;
    const defaultName = `Playbook · ${String(job.title || "Kênh Tài liệu").slice(0, 32)}`;
    const name = window.prompt("Nhập tên Playbook Kênh mới đúc kết từ dự án này:", defaultName);
    if (!name || !name.trim()) return;
    btn.disabled = true;
    try {
      const nextBrief = collectBriefFromScriptStudio();
      await api(`/api/jobs/${encodeURIComponent(job.id)}/creative-brief`, {
        method: "PATCH",
        body: JSON.stringify({ playbook_id: nextBrief.playbook_id, creative_brief: nextBrief }),
      });
      await api(`/api/jobs/${encodeURIComponent(job.id)}/extract-playbook`, {
        method: "POST",
        body: JSON.stringify({ name: name.trim() }),
      });
      await loadPlaybooks();
      await loadJobs(true);
      const updatedJob = state.jobs.find(j => j.id === job.id) || job;
      await renderScriptWorkspace(updatedJob, { force: true });
      toast(`Đã đúc kết dự án thành Playbook "${name.trim()}".`);
    } catch (err) {
      toast(err.message, true);
    } finally {
      btn.disabled = false;
    }
  });

  $("#scriptAiGenerateOutlineBtn")?.addEventListener("click", async ev => {
    const btn = ev.currentTarget;
    const orig = btn.textContent;
    btn.disabled = true;
    btn.textContent = "✨ AI đang thiết kế Dàn ý Chương hồi…";
    try {
      const nextBrief = collectBriefFromScriptStudio();
      await api(`/api/jobs/${encodeURIComponent(job.id)}/creative-brief`, {
        method: "PATCH",
        body: JSON.stringify({ playbook_id: nextBrief.playbook_id, creative_brief: nextBrief }),
      });
      await api(`/api/jobs/${encodeURIComponent(job.id)}/outline/generate`, {
        method: "POST",
        body: JSON.stringify({
          instruction: nextBrief.custom_rules || "",
          chapter_count: Math.max(4, Math.min(7, Math.round(Number(job.target_duration_minutes || 18) / 3.5))),
        }),
      });
      await loadJobs(true);
      const updatedJob = state.jobs.find(j => j.id === job.id) || job;
      await renderScriptWorkspace(updatedJob, { force: true });
      toast("AI đã tạo xong Dàn ý Chương hồi kèm đề xuất bằng chứng & nhịp dựng!");
    } catch (err) {
      toast(err.message, true);
    } finally {
      btn.disabled = false;
      btn.textContent = orig;
    }
  });

  $("#scriptAddChapterBtn")?.addEventListener("click", async () => {
    const currentChapters = collectChaptersFromScriptStudio();
    currentChapters.push({
      chapter_id: `CH${String(currentChapters.length + 1).padStart(2, "0")}`,
      title: `Chương ${currentChapters.length + 1}: Góc khuất tiếp theo`,
      estimated_minutes: 3,
      summary: "",
      evidence_anchor: "",
      visual_note: "",
    });
    await api(`/api/jobs/${encodeURIComponent(job.id)}/outline`, {
      method: "PATCH",
      body: JSON.stringify({
        outline: {
          ...outlineObj,
          opening_hook: String($("#scriptOpeningHookInput")?.value || "").trim(),
          chapters: currentChapters,
        },
      }),
    });
    await loadJobs(true);
    const updatedJob = state.jobs.find(j => j.id === job.id) || job;
    await renderScriptWorkspace(updatedJob, { force: true });
  });

  $("#scriptSaveOutlineBtn")?.addEventListener("click", async ev => {
    const btn = ev.currentTarget;
    btn.disabled = true;
    try {
      const nextChapters = collectChaptersFromScriptStudio();
      await api(`/api/jobs/${encodeURIComponent(job.id)}/outline`, {
        method: "PATCH",
        body: JSON.stringify({
          outline: {
            ...outlineObj,
            opening_hook: String($("#scriptOpeningHookInput")?.value || "").trim(),
            chapters: nextChapters,
          },
        }),
      });
      await loadJobs(true);
      const updatedJob = state.jobs.find(j => j.id === job.id) || job;
      await renderScriptWorkspace(updatedJob, { force: true });
      toast("Đã lưu Dàn ý Chương hồi (outline.json). Khi chạy Bước 01, Agent sẽ bám sát dàn ý này.");
    } catch (err) {
      toast(err.message, true);
    } finally {
      btn.disabled = false;
    }
  });

  root.querySelector("#scriptOutlineChaptersList")?.addEventListener("click", async ev => {
    const delBtn = ev.target.closest("[data-chapter-delete]");
    const moveBtn = ev.target.closest("[data-chapter-move]");
    if (!delBtn && !moveBtn) return;
    const card = ev.target.closest(".outline-chapter-card");
    if (!card) return;
    const idx = Number(card.dataset.chapterIndex || 0);
    const list = collectChaptersFromScriptStudio();
    if (delBtn) {
      list.splice(idx, 1);
    } else if (moveBtn) {
      const dir = moveBtn.dataset.chapterMove === "up" ? -1 : 1;
      const targetIdx = idx + dir;
      if (targetIdx < 0 || targetIdx >= list.length) return;
      const [item] = list.splice(idx, 1);
      list.splice(targetIdx, 0, item);
    }
    await api(`/api/jobs/${encodeURIComponent(job.id)}/outline`, {
      method: "PATCH",
      body: JSON.stringify({
        outline: {
          ...outlineObj,
          opening_hook: String($("#scriptOpeningHookInput")?.value || "").trim(),
          chapters: list,
        },
      }),
    });
    await loadJobs(true);
    const updatedJob = state.jobs.find(j => j.id === job.id) || job;
    await renderScriptWorkspace(updatedJob, { force: true });
  });

  const directEditorEl = $("#scriptDirectEditorTextarea");
  directEditorEl?.addEventListener("input", () => {
    directEditorEl.dataset.dirty = "1";
  });

  $("#scriptSaveFullTextBtn")?.addEventListener("click", async ev => {
    const btn = ev.currentTarget;
    const content = String($("#scriptDirectEditorTextarea")?.value || "");
    if (!content.trim()) {
      toast("Nội dung kịch bản không được để trống.", true);
      return;
    }
    btn.disabled = true;
    try {
      await api(`/api/jobs/${encodeURIComponent(job.id)}/script`, {
        method: "PUT",
        body: JSON.stringify({ script: content }),
      });
      if (directEditorEl) directEditorEl.dataset.dirty = "0";
      toast("Đã lưu kịch bản (script.md). Bạn có thể chạy Bước 02 (Voice & SRT) hoặc Bước 03 (Visuals) ngay.");
    } catch (err) {
      toast(err.message, true);
    } finally {
      btn.disabled = false;
    }
  });
}

let voiceStudioSubTab = "clone";
let voiceCountryFilter = "all";
let voiceTypeFilter = "all";
let voiceSearchQuery = "";
let voiceAutoStartTriggered = false;

function cofiVoiceBaseUrl() {
  return String(state.health?.cofi_voice?.url || "http://127.0.0.1:8000").replace(/\/$/, "");
}

function voicePreviewUrl(voice) {
  if (voice?.proxy_preview_url) return String(voice.proxy_preview_url);
  const value = String(voice?.preview_url || "");
  if (!value) return "";
  if (voice?.id) return `/api/voice/preview-audio/${encodeURIComponent(voice.id)}`;
  if (/^https?:\/\//i.test(value)) return value;
  return `${cofiVoiceBaseUrl()}${value.startsWith("/") ? "" : "/"}${value}`;
}

function getVoiceLocaleInfo(langCode, voiceObj = null) {
  const code = String(langCode || voiceObj?.language || "en").toLowerCase();
  if (voiceLocales[code]) return { code, ...voiceLocales[code] };
  return {
    code,
    label: voiceObj?.country_label || code.toUpperCase() || "Khác",
    langLabel: voiceObj?.language_label || code.toUpperCase(),
    flag: voiceObj?.flag || "🌐",
  };
}

function renderSingleVoiceCardHtml(v, selectedId) {
  const locale = getVoiceLocaleInfo(v.language, v);
  const preview = voicePreviewUrl(v);
  const isSelected = String(v.id) === String(selectedId || "");
  const isDesign = String(v.type || "").toLowerCase() === "design";
  const typeBadge = isDesign ? "✨ Thiết kế AI" : "🎙 Giọng Clone";
  return `<article class="voice-sample-card headless-voice-card ${isSelected ? "selected" : ""}" data-voice-card-id="${escapeHtml(v.id)}">
    <label class="voice-card-select-area">
      <input type="radio" name="workspace_voice_id" value="${escapeHtml(v.id)}" ${isSelected ? "checked" : ""} />
      <div class="voice-sample-top">
        <span class="voice-flag">${locale.flag}</span>
        <div class="voice-sample-meta">
          <div class="voice-sample-title-row">
            <strong>${escapeHtml(v.name || v.id)}</strong>
            ${isSelected ? `<span class="voice-active-pill">ĐANG CHỌN</span>` : ""}
          </div>
          <small>${escapeHtml(locale.label)} (${escapeHtml(locale.code.toUpperCase())}) · <span class="voice-type-tag ${isDesign ? "design" : "clone"}">${typeBadge}</span></small>
        </div>
      </div>
    </label>
    ${v.instruct ? `<p class="voice-instruct-note" title="${escapeHtml(v.instruct)}">“${escapeHtml(v.instruct)}”</p>` : ""}
    <div class="voice-card-audio-row">
      ${preview
        ? `<audio controls preload="none" src="${escapeHtml(preview)}"></audio>`
        : `<button type="button" class="ghost compact" data-voice-gen-preview="${escapeHtml(v.id)}">🔊 Tạo mẫu nghe thử</button>`}
    </div>
    <div class="voice-card-footer-actions">
      <button type="button" class="${isSelected ? "ghost" : "primary"} compact" data-voice-apply-id="${escapeHtml(v.id)}">${isSelected ? "✓ Đang dùng cho dự án" : "Chọn giọng này"}</button>
      <button type="button" class="ghost compact danger-text" data-voice-delete-id="${escapeHtml(v.id)}" data-voice-name="${escapeHtml(v.name || v.id)}" title="Xóa giọng này">🗑</button>
    </div>
  </article>`;
}

function voiceGalleryHtml(countryFilter, selectedId, typeFilter = "all", searchQuery = "") {
  const q = String(searchQuery || "").trim().toLowerCase();
  const filtered = state.voices.filter(v => {
    const lang = String(v.language || "en").toLowerCase();
    const vType = String(v.type || "clone").toLowerCase();
    if (countryFilter && countryFilter !== "all" && lang !== countryFilter) return false;
    if (typeFilter && typeFilter !== "all" && vType !== typeFilter) return false;
    if (q) {
      const hay = `${v.name || ""} ${v.language || ""} ${v.country_label || ""} ${v.instruct || ""}`.toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });

  if (!filtered.length) {
    return `<div class="empty-state">Chưa có giọng nói nào khớp bộ lọc này. Anh có thể tạo mới ở bảng <b>Clone giọng mới</b> hoặc <b>Thiết kế giọng AI</b> phía trên.</div>`;
  }

  if (countryFilter && countryFilter !== "all") {
    return `<div class="voice-cards-grid">${filtered.map(v => renderSingleVoiceCardHtml(v, selectedId)).join("")}</div>`;
  }

  const order = ["vi", "ko", "ja", "en", "zh", "fr", "de", "es", "ru", "th"];
  const groups = new Map();
  for (const v of filtered) {
    const code = String(v.language || "en").toLowerCase();
    if (!groups.has(code)) groups.set(code, []);
    groups.get(code).push(v);
  }
  const sortedCodes = [...groups.keys()].sort((a, b) => {
    const ia = order.indexOf(a);
    const ib = order.indexOf(b);
    if (ia === -1 && ib === -1) return a.localeCompare(b);
    if (ia === -1) return 1;
    if (ib === -1) return -1;
    return ia - ib;
  });

  return sortedCodes.map(code => {
    const items = groups.get(code) || [];
    const info = getVoiceLocaleInfo(code, items[0]);
    return `<section class="voice-country-section">
      <div class="voice-country-section-head">
        <div>
          <span class="voice-country-flag">${info.flag}</span>
          <strong>${escapeHtml(info.label)}</strong>
          <span class="voice-country-lang">${escapeHtml(info.langLabel || code.toUpperCase())}</span>
        </div>
        <span class="voice-country-count">${items.length} giọng</span>
      </div>
      <div class="voice-cards-grid">
        ${items.map(v => renderSingleVoiceCardHtml(v, selectedId)).join("")}
      </div>
    </section>`;
  }).join("");
}

function readFileAsDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(new Error("Không đọc được file âm thanh."));
    reader.readAsDataURL(file);
  });
}

async function renderVoiceWorkspace(job, { force = false } = {}) {
  $("#voiceProjectLabel").textContent = selectedProjectLabel(job);
  const root = $("#voiceWorkspace");
  if (!job) {
    root.dataset.voiceJobKey = "";
    return root.innerHTML = `<div class="empty-state">Chọn một dự án để cấu hình voice.</div>`;
  }
  const voicePhase = job.phases?.voice || {};
  const voiceRunning = ["running", "queued"].includes(voicePhase.status);
  const voiceJobKey = `${job.id}|${voicePhase.status || 'pending'}|${voicePhase.finished_at || ''}|${JSON.stringify(job.voice || {})}`;
  if (!force && voiceRunning && root.dataset.voiceJobId === job.id && root.children.length > 0) {
    const stepCard = root.querySelector(".step-status-card");
    const wavCount = state.realtimeLive?.job_id === job.id ? (state.realtimeLive.voice_wav_count || 0) : 0;
    if (stepCard) {
      stepCard.outerHTML = phaseStepPanelHtml(job, "voice", "visuals");
      const newCard = root.querySelector(".step-status-card small");
      if (newCard && wavCount > 0) {
        newCard.textContent = `🎙 Đang thu âm realtime: đã hoàn tất ${wavCount} file âm thanh trong dự án...`;
      }
      bindWorkspacePhaseButtons(job, root);
    }
    root.dataset.voiceJobKey = voiceJobKey;
    return;
  }
  root.dataset.voiceJobId = job.id;
  root.dataset.voiceJobKey = voiceJobKey;
  const [manifest, srt] = await Promise.all([artifact(job.id, "voice_manifest.json"), artifact(job.id, "subtitles.srt")]);
  const currentVoice = state.voices.find(v => String(v.id) === String(job.voice?.voice_id || ""));
  const voiceReady = Boolean(state.health?.cofi_voice?.ok);

  if (!voiceReady && !voiceAutoStartTriggered) {
    voiceAutoStartTriggered = true;
    api("/api/voice/start", { method: "POST" }).then(() => {
      setTimeout(async () => {
        await loadHealth();
        await loadVoices();
        if (state.appTab === "voice") await renderVoiceWorkspace(job);
      }, 2200);
    }).catch(() => {});
  }

  const countByLang = {};
  for (const v of state.voices) {
    const c = String(v.language || "en").toLowerCase();
    countByLang[c] = (countByLang[c] || 0) + 1;
  }
  const countryCodes = [...new Set(["vi", "ko", "ja", "en", ...Object.keys(countByLang)])];
  const defaultStudioLang = job.language || currentVoice?.language || "vi";

  root.innerHTML = `${phaseStepPanelHtml(job, "voice", "visuals")}
    <section class="headless-voice-studio-card">
      <div class="headless-voice-topbar">
        <div class="headless-voice-status">
          <span class="flow-glabs-dot ${voiceReady ? "online" : "offline"}"></span>
          <div>
            <strong>CofiVoice Engine · ${voiceReady ? "Đang chạy ngầm (Headless)" : "Đang khởi động ngầm…"}</strong>
            <small>Đang chọn cho dự án: <b>${escapeHtml(currentVoice ? `${currentVoice.flag || ""} ${currentVoice.name} (${String(currentVoice.language || "").toUpperCase()})` : "Giọng mặc định theo ngôn ngữ")}</b> · Tốc độ <b>${Number(job.voice?.speed || 1).toFixed(2)}×</b></small>
          </div>
        </div>
        <div class="headless-voice-top-actions">
          <button type="button" class="ghost compact ${voiceStudioSubTab === "clone" ? "active" : ""}" data-voice-studio-tab="clone">🎙 Clone giọng mới</button>
          <button type="button" class="ghost compact ${voiceStudioSubTab === "design" ? "active" : ""}" data-voice-studio-tab="design">✨ Thiết kế giọng AI</button>
          <button type="button" class="ghost compact ${voiceStudioSubTab === "tts" ? "active" : ""}" data-voice-studio-tab="tts">🔊 Đọc thử câu bất kỳ</button>
          ${voiceReady
            ? `<button type="button" class="ghost compact" id="refreshVoicesListBtn">↻ Làm mới danh sách</button>`
            : `<button type="button" class="primary compact" id="startCofiVoiceBtn">⚡ Khởi động CofiVoice ngầm</button>`}
        </div>
      </div>

      <div class="headless-voice-creator-panel" id="headlessVoiceCreatorPanel">
        ${voiceStudioSubTab === "clone" ? `
          <div class="voice-creator-grid">
            <div class="voice-creator-head">
              <strong>🎙 Nhân bản giọng nói (Voice Clone — Xử lý ngầm)</strong>
              <small>Tải lên mẫu âm thanh 5–25 giây rõ chữ, không nhạc nền. CofiVoice sẽ tự tách đặc trưng giọng và tạo mẫu nghe thử ở chế độ nền.</small>
            </div>
            <div class="voice-creator-fields">
              <label><span>Tên giọng Clone mới</span><input type="text" id="voiceCloneNameInput" placeholder="VD: Giọng đọc tài liệu Hàn Quốc / Nam trầm Mỹ..." /></label>
              <label><span>Quốc gia / Ngôn ngữ</span>
                <select id="voiceCloneLangSelect">
                  ${Object.entries(voiceLocales).map(([code, info]) => `<option value="${code}" ${code === defaultStudioLang ? "selected" : ""}>${info.flag} ${info.label} (${info.langLabel})</option>`).join("")}
                </select>
              </label>
              <label><span>File âm thanh mẫu (WAV, MP3, M4A · 5–25s)</span><input type="file" id="voiceCloneAudioInput" accept="audio/*,.wav,.mp3,.m4a,.flac,.ogg" /></label>
              <label><span>Nội dung câu trong file mẫu (Tùy chọn — bỏ trống AI tự nhận diện)</span><input type="text" id="voiceCloneRefTextInput" placeholder="Nhập transcript nếu muốn khớp chính xác tuyệt đối..." /></label>
            </div>
            <div class="voice-creator-actions">
              <button type="button" class="primary" id="submitVoiceCloneBtn">🎙 Tạo giọng Clone & Áp dụng cho dự án</button>
            </div>
          </div>
        ` : voiceStudioSubTab === "design" ? `
          <div class="voice-creator-grid">
            <div class="voice-creator-head">
              <strong>✨ Thiết kế giọng đọc AI (Voice Design — Xử lý ngầm)</strong>
              <small>Mô tả độ tuổi, âm sắc, nhịp điệu và cảm xúc để AI tự tổng hợp một giọng đọc hoàn toàn mới cho kênh.</small>
            </div>
            <div class="voice-design-presets">
              <span>Gợi ý nhanh:</span>
              <button type="button" class="ghost compact" data-design-preset="Deep, calm, authoritative male documentary narrator with warm resonance and measured pacing.">🎬 Nam trầm phim tài liệu</button>
              <button type="button" class="ghost compact" data-design-preset="Clear, articulate, warm female investigative journalist voice, engaging and trustworthy.">🎙 Nữ phóng sự sắc nét</button>
              <button type="button" class="ghost compact" data-design-preset="Mature historian voice, grave, cinematic, slow deliberate storytelling tone.">🏛 Học giả lịch sử</button>
            </div>
            <div class="voice-creator-fields">
              <label><span>Tên giọng thiết kế</span><input type="text" id="voiceDesignNameInput" placeholder="VD: Nam trầm lịch sử / Narrator US..." /></label>
              <label><span>Quốc gia / Ngôn ngữ</span>
                <select id="voiceDesignLangSelect">
                  ${Object.entries(voiceLocales).map(([code, info]) => `<option value="${code}" ${code === defaultStudioLang ? "selected" : ""}>${info.flag} ${info.label} (${info.langLabel})</option>`).join("")}
                </select>
              </label>
              <label class="full-span"><span>Mô tả chất giọng (Instruct Prompt)</span><textarea id="voiceDesignInstructInput" rows="2" placeholder="VD: Deep, calm, authoritative male documentary narrator with warm resonance and measured pacing..."></textarea></label>
            </div>
            <div class="voice-creator-actions">
              <button type="button" class="primary" id="submitVoiceDesignBtn">✨ Thiết kế giọng & Tạo mẫu nghe thử</button>
            </div>
          </div>
        ` : `
          <div class="voice-creator-grid">
            <div class="voice-creator-head">
              <strong>🔊 Đọc thử câu bất kỳ (Quick TTS Preview)</strong>
              <small>Kiểm tra trực tiếp giọng đang chọn và tốc độ đọc trước khi chạy toàn bộ kịch bản.</small>
            </div>
            <div class="voice-creator-fields">
              <label class="full-span"><span>Câu văn bản muốn đọc thử</span><textarea id="voiceQuickTtsInput" rows="2" placeholder="Nhập một câu bất kỳ bằng ngôn ngữ của giọng đọc để kiểm tra nhịp ngắt và âm sắc..."></textarea></label>
            </div>
            <div class="voice-creator-actions">
              <button type="button" class="primary" id="runVoiceQuickTtsBtn">▶ Đọc thử ngay ở nền</button>
              <audio id="voiceQuickTtsAudio" controls style="display:none; max-width: 360px; height: 34px;"></audio>
            </div>
          </div>
        `}
      </div>
    </section>

    <div class="voice-config-layout">
      <aside class="voice-config-panel">
        <div class="workspace-toolbar"><div><strong>Cấu hình giọng cho dự án</strong><small>Áp dụng khi chạy bước 02 Voice & SRT</small></div></div>
        <label><span>Lọc theo Quốc gia</span>
          <select id="voiceLanguageFilter">
            <option value="all" ${voiceCountryFilter === "all" ? "selected" : ""}>🌐 Tất cả Quốc gia (${state.voices.length})</option>
            ${Object.entries(voiceLocales).map(([code, info]) => `<option value="${code}" ${code === voiceCountryFilter ? "selected" : ""}>${info.flag} ${info.label} (${countByLang[code] || 0})</option>`).join("")}
          </select>
        </label>
        <label><span>Loại giọng</span>
          <select id="voiceTypeFilterSelect">
            <option value="all" ${voiceTypeFilter === "all" ? "selected" : ""}>Tất cả loại giọng</option>
            <option value="clone" ${voiceTypeFilter === "clone" ? "selected" : ""}>🎙 Giọng Clone</option>
            <option value="design" ${voiceTypeFilter === "design" ? "selected" : ""}>✨ Giọng Thiết kế AI</option>
          </select>
        </label>
        <label><span>Tìm kiếm tên giọng</span>
          <input type="search" id="voiceSearchInput" value="${escapeHtml(voiceSearchQuery)}" placeholder="Tìm tên giọng..." />
        </label>
        <label><span>Tốc độ đọc (${Number(job.voice?.speed || 1).toFixed(2)}×)</span>
          <input id="workspaceVoiceSpeed" type="range" min="0.8" max="1.2" step="0.05" value="${Number(job.voice?.speed || 1)}" />
          <output id="workspaceVoiceSpeedLabel">${Number(job.voice?.speed || 1).toFixed(2)}×</output>
        </label>
        <button class="primary" id="saveVoiceSettingsBtn" type="button">💾 Lưu cấu hình giọng cho dự án</button>
        <small class="voice-note">CofiVoice chạy ngầm 100%. Anh có thể lọc giọng theo từng quốc gia, nghe thử trực tiếp, clone hoặc thiết kế giọng mới ngay tại đây.</small>
      </aside>
      <div class="voice-browser">
        <div class="voice-country-pills-bar" id="voiceCountryPillsBar">
          <button type="button" class="ghost compact ${voiceCountryFilter === "all" ? "active" : ""}" data-voice-country-pill="all">🌐 Tất cả (${state.voices.length})</button>
          ${countryCodes.map(code => {
            const info = getVoiceLocaleInfo(code);
            const cnt = countByLang[code] || 0;
            return `<button type="button" class="ghost compact ${voiceCountryFilter === code ? "active" : ""}" data-voice-country-pill="${escapeHtml(code)}">${info.flag} ${escapeHtml(info.label)} (${cnt})</button>`;
          }).join("")}
        </div>
        <div id="voiceGallery" class="voice-gallery">${voiceGalleryHtml(voiceCountryFilter, job.voice?.voice_id, voiceTypeFilter, voiceSearchQuery)}</div>
      </div>
    </div>
    <details class="technical-details voice-artifacts"><summary>Chi tiết kỹ thuật · voice manifest & SRT</summary><div class="artifact-grid two-col">${codeViewer("Bản kê giọng đọc", manifest)}${codeViewer("SRT đồng bộ", srt)}</div></details>`;

  const refreshGallery = () => {
    const galleryEl = $("#voiceGallery");
    if (galleryEl) {
      galleryEl.innerHTML = voiceGalleryHtml(voiceCountryFilter, job.voice?.voice_id, voiceTypeFilter, voiceSearchQuery);
      bindGalleryCardEvents();
    }
    root.querySelectorAll("[data-voice-country-pill]").forEach(btn => {
      btn.classList.toggle("active", btn.dataset.voiceCountryPill === voiceCountryFilter);
    });
    const sel = $("#voiceLanguageFilter");
    if (sel && sel.value !== voiceCountryFilter) sel.value = voiceCountryFilter;
  };

  const applyVoiceToProject = async (voiceId) => {
    const speedVal = Number($("#workspaceVoiceSpeed")?.value || job.voice?.speed || 1);
    await api(`/api/jobs/${encodeURIComponent(job.id)}/voice`, {
      method: "PATCH",
      body: JSON.stringify({ voice_id: voiceId, speed: speedVal, mode: "balanced" }),
    });
    toast("Đã lưu giọng đọc cho dự án.");
    await loadJobs(true);
    await renderFunctionWorkspaces();
  };

  const bindGalleryCardEvents = () => {
    const galleryEl = $("#voiceGallery");
    if (!galleryEl) return;
    galleryEl.querySelectorAll("[data-voice-apply-id]").forEach(btn => btn.addEventListener("click", async event => {
      const voiceId = event.currentTarget.dataset.voiceApplyId;
      event.currentTarget.disabled = true;
      try {
        await applyVoiceToProject(voiceId);
      } catch (err) {
        toast(err.message, true);
        event.currentTarget.disabled = false;
      }
    }));
    galleryEl.querySelectorAll("[data-voice-gen-preview]").forEach(btn => btn.addEventListener("click", async event => {
      const button = event.currentTarget;
      const voiceId = button.dataset.voiceGenPreview;
      button.disabled = true;
      button.textContent = "Đang tạo mẫu nghe…";
      try {
        await api(`/api/voice/voices/${encodeURIComponent(voiceId)}/preview`, { method: "POST" });
        await loadVoices();
        refreshGallery();
        toast("Đã tạo mẫu nghe thử.");
      } catch (err) {
        toast(err.message, true);
        button.disabled = false;
        button.textContent = "🔊 Tạo mẫu nghe thử";
      }
    }));
    galleryEl.querySelectorAll("[data-voice-delete-id]").forEach(btn => btn.addEventListener("click", async event => {
      const button = event.currentTarget;
      const voiceId = button.dataset.voiceDeleteId;
      const voiceName = button.dataset.voiceName || voiceId;
      button.disabled = true;
      try {
        await api(`/api/voice/voices/${encodeURIComponent(voiceId)}`, { method: "DELETE" });
        toast(`Đã xóa giọng "${voiceName}".`);
        await loadVoices();
        refreshGallery();
      } catch (err) {
        toast(err.message, true);
        button.disabled = false;
      }
    }));
  };

  bindGalleryCardEvents();

  root.querySelectorAll("[data-voice-studio-tab]").forEach(btn => btn.addEventListener("click", event => {
    voiceStudioSubTab = event.currentTarget.dataset.voiceStudioTab || "clone";
    renderVoiceWorkspace(job, { force: true });
  }));

  root.querySelectorAll("[data-voice-country-pill]").forEach(btn => btn.addEventListener("click", event => {
    voiceCountryFilter = event.currentTarget.dataset.voiceCountryPill || "all";
    refreshGallery();
  }));

  $("#voiceLanguageFilter")?.addEventListener("change", event => {
    voiceCountryFilter = event.target.value || "all";
    refreshGallery();
  });

  $("#voiceTypeFilterSelect")?.addEventListener("change", event => {
    voiceTypeFilter = event.target.value || "all";
    refreshGallery();
  });

  $("#voiceSearchInput")?.addEventListener("input", event => {
    voiceSearchQuery = event.target.value || "";
    refreshGallery();
  });

  $("#workspaceVoiceSpeed")?.addEventListener("input", event => {
    $("#workspaceVoiceSpeedLabel").textContent = `${Number(event.target.value).toFixed(2)}×`;
  });

  $("#saveVoiceSettingsBtn")?.addEventListener("click", async () => {
    const picked = document.querySelector('input[name="workspace_voice_id"]:checked');
    if (!picked) return toast("Chọn một voice mẫu trước khi lưu.", true);
    try {
      await applyVoiceToProject(picked.value);
    } catch (err) {
      toast(err.message, true);
    }
  });

  $("#refreshVoicesListBtn")?.addEventListener("click", async () => {
    await loadHealth();
    await loadVoices();
    await renderVoiceWorkspace(job);
    toast("Đã làm mới danh sách giọng nói từ CofiVoice.");
  });

  $("#startCofiVoiceBtn")?.addEventListener("click", async event => {
    event.currentTarget.disabled = true;
    event.currentTarget.textContent = "Đang bật CofiVoice ngầm…";
    try {
      await api("/api/voice/start", { method: "POST" });
      toast("Đã khởi động CofiVoice chạy ngầm.");
      setTimeout(async () => {
        await loadHealth();
        await loadVoices();
        await renderVoiceWorkspace(job);
      }, 2200);
    } catch (err) {
      toast(err.message, true);
      event.currentTarget.disabled = false;
      event.currentTarget.textContent = "⚡ Khởi động CofiVoice ngầm";
    }
  });

  $("#submitVoiceCloneBtn")?.addEventListener("click", async event => {
    const btn = event.currentTarget;
    const name = String($("#voiceCloneNameInput")?.value || "").trim();
    const language = String($("#voiceCloneLangSelect")?.value || "vi").trim();
    const refText = String($("#voiceCloneRefTextInput")?.value || "").trim();
    const fileInput = $("#voiceCloneAudioInput");
    const file = fileInput?.files?.[0];
    if (!name) return toast("Hãy nhập tên cho giọng Clone mới.", true);
    if (!file) return toast("Hãy chọn một file âm thanh mẫu (WAV/MP3/M4A).", true);
    btn.disabled = true;
    btn.textContent = "Đang clone giọng ngầm & tạo mẫu nghe…";
    try {
      const dataUrl = await readFileAsDataUrl(file);
      const created = await api("/api/voice/clone", {
        method: "POST",
        body: JSON.stringify({
          name,
          language,
          ref_text: refText,
          filename: file.name || "sample.wav",
          data_url: dataUrl,
        }),
      });
      await loadVoices();
      voiceCountryFilter = language;
      if (created?.id) {
        await applyVoiceToProject(created.id);
      } else {
        await renderVoiceWorkspace(job);
      }
      toast(`Đã clone thành công giọng "${name}" (${language.toUpperCase()}).`);
    } catch (err) {
      toast(err.message, true);
      btn.disabled = false;
      btn.textContent = "🎙 Tạo giọng Clone & Áp dụng cho dự án";
    }
  });

  root.querySelectorAll("[data-design-preset]").forEach(btn => btn.addEventListener("click", event => {
    const area = $("#voiceDesignInstructInput");
    if (area) area.value = event.currentTarget.dataset.designPreset || "";
  }));

  $("#submitVoiceDesignBtn")?.addEventListener("click", async event => {
    const btn = event.currentTarget;
    const name = String($("#voiceDesignNameInput")?.value || "").trim();
    const language = String($("#voiceDesignLangSelect")?.value || "vi").trim();
    const instruct = String($("#voiceDesignInstructInput")?.value || "").trim();
    if (!name) return toast("Hãy nhập tên cho giọng thiết kế.", true);
    if (!instruct) return toast("Hãy nhập mô tả chất giọng (instruct).", true);
    btn.disabled = true;
    btn.textContent = "Đang thiết kế giọng & tạo mẫu nghe…";
    try {
      const created = await api("/api/voice/design", {
        method: "POST",
        body: JSON.stringify({
          name,
          language,
          instruct,
          auto_preview: true,
        }),
      });
      await loadVoices();
      voiceCountryFilter = language;
      if (created?.id) {
        await applyVoiceToProject(created.id);
      } else {
        await renderVoiceWorkspace(job);
      }
      toast(`Đã thiết kế xong giọng "${name}" (${language.toUpperCase()}).`);
    } catch (err) {
      toast(err.message, true);
      btn.disabled = false;
      btn.textContent = "✨ Thiết kế giọng & Tạo mẫu nghe thử";
    }
  });

  $("#runVoiceQuickTtsBtn")?.addEventListener("click", async event => {
    const btn = event.currentTarget;
    const text = String($("#voiceQuickTtsInput")?.value || "").trim();
    if (!text) return toast("Nhập câu văn bản cần đọc thử.", true);
    const picked = document.querySelector('input[name="workspace_voice_id"]:checked');
    const voiceId = picked?.value || job.voice?.voice_id || null;
    const speed = Number($("#workspaceVoiceSpeed")?.value || job.voice?.speed || 1);
    btn.disabled = true;
    btn.textContent = "Đang tổng hợp âm thanh…";
    try {
      const res = await fetch("/api/voice/tts-preview", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, voice_id: voiceId, language: job.language || null, speed, mode: "balanced" }),
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `HTTP ${res.status}`);
      }
      const blob = await res.blob();
      const audioEl = $("#voiceQuickTtsAudio");
      if (audioEl) {
        audioEl.src = URL.createObjectURL(blob);
        audioEl.style.display = "inline-block";
        audioEl.play().catch(() => {});
      }
      toast("Đã tổng hợp xong bản đọc thử.");
    } catch (err) {
      toast(`Không đọc thử được: ${err.message}`, true);
    } finally {
      btn.disabled = false;
      btn.textContent = "▶ Đọc thử ngay ở nền";
    }
  });

  bindWorkspacePhaseButtons(job, root);
}

function visualStrategyLabel(job) {
  const strategy = String(job?.visual_strategy || "full_footage").toLowerCase();
  if (strategy === "full_ai") return "Full AI · toàn bộ Visuals chuyển sang AI Visual";
  if (["edit_direct_footage", "semi_content", "ban_content", "edit_footage"].includes(strategy)) return "Bán Content · Bỏ qua Bước 4, tạo vài ảnh AI điểm nhấn & AI Agent tự tải Footage lúc Edit";
  if (strategy === "hybrid") return "Kết hợp · từng Visual tự route theo cốt truyện";
  if (strategy === "evidence_footage" || strategy === "selective_footage" || strategy === "evidence_first") return "Bằng chứng + AI · chỉ bằng chứng/nhân vật 100% thật dùng Footage, còn lại full AI";
  return "Full Footage · toàn bộ Visuals chuyển sang Footage";
}

function visualsNextTab(job) {
  const strategy = String(job?.visual_strategy || "full_footage").toLowerCase();
  return strategy === "full_footage" ? "edit" : "ai_visual";
}

async function renderVisualsWorkspace(job) {
  $("#visualsProjectLabel").textContent = selectedProjectLabel(job);
  const root = $("#visualsWorkspace");
  if (!job) return root.innerHTML = `<div class="empty-state">Chọn một dự án để xem Visuals và prompt.</div>`;
  const [prompts, visual] = await Promise.all([
    artifact(job.id, "visual_prompts.json"),
    artifact(job.id, "visual_manifest.json"),
  ]);
  const strategy = escapeHtml(visualStrategyLabel(job));
  const storyboard = storyboardTableHtml(visual, prompts);
  root.innerHTML = `${phaseStepPanelHtml(job, "visuals", visualsNextTab(job))}
    <section class="workspace-toolbar visuals-route-toolbar"><div><strong>${strategy}</strong></div></section>
    ${storyboard}
    <details class="technical-details" id="visualsTechDetails"><summary>Chi tiết kỹ thuật · Visual Prompts &amp; Manifest JSON</summary><div class="artifact-grid two-col" id="visualsTechGrid"><p style="grid-column: 1 / -1; color: #6a889f; padding: 10px 12px; margin: 0; font-size: 11.5px;">Nhấn mở để nạp tệp JSON kỹ thuật...</p></div></details>`;
  const visualsTech = root.querySelector("#visualsTechDetails");
  if (visualsTech) {
    visualsTech.addEventListener("toggle", () => {
      if (visualsTech.open) {
        const grid = visualsTech.querySelector("#visualsTechGrid");
        if (grid && !grid.dataset.loaded) {
          grid.dataset.loaded = "true";
          grid.innerHTML = `${codeViewer("Visual prompts · mỗi dòng một prompt", prompts)}${codeViewer("Visual manifest đã chia nhỏ", visual)}`;
        }
      }
    });
  }
  bindWorkspacePhaseButtons(job, root);
}

async function renderFootageWorkspace(job) {
  $("#footageProjectLabel").textContent = selectedProjectLabel(job);
  const root = $("#footageWorkspace");
  if (!job) return root.innerHTML = `<div class="empty-state">Chọn một dự án để xem tư liệu.</div>`;
  if (!effectivePhases(job).includes("footage")) {
    const isSemi = ["edit_direct_footage", "semi_content", "ban_content", "edit_footage"].includes(String(job?.visual_strategy || "").toLowerCase());
    root.innerHTML = `${phaseStepPanelHtml(job, "footage")}<div class="empty-state">${isSemi ? "Dự án chạy chế độ Bán Content (Edit-Direct Footage): Bước 4 được bỏ qua — AI Agent sẽ trực tiếp tìm & tải video B-roll khi vào bước Edit (Step 6)." : "Dự án này chạy Full AI nên không cần tìm Footage."}</div>`;
    return;
  }
  if (footageRenderInFlight) return;
  footageRenderInFlight = true;
  const preservedMedia = new Map(
    [...root.querySelectorAll("[data-footage-media-key]")]
      .map(element => [String(element.dataset.footageMediaKey || ""), element])
      .filter(([key]) => Boolean(key))
  );
  try {
  const [registry, review, coverage, report, checkpointRaw, livePayload] = await Promise.all([
    artifact(job.id, "asset_registry.json"), artifact(job.id, "footage_review.json"), artifact(job.id, "coverage_matrix.json"), artifact(job.id, "preflight_report.json"), artifact(job.id, "footage_checkpoint.json"), liveFootage(job.id)
  ]);
  let registryData = safeJson(registry, {});
  let reviewData = safeJson(review, {});
  const checkpoint = safeJson(checkpointRaw, {});
  const sourceTools = Array.isArray(state.health?.footage_vision?.source_tools) ? state.health.footage_vision.source_tools : [];
  const toolLabels = {
    ddgs: "DDGS Video/Web", ddgs_images: "DDGS Images", internetarchive_tool: "InternetArchive tool",
    yt_dlp: "yt-dlp YouTube Search", internet_archive: "Archive.org", loc: "Library of Congress",
    wikimedia: "Wikimedia Commons", openverse: "Openverse", searxng: "SearXNG", brave: "Brave",
    europeana: "Europeana", nara: "NARA",
  };
  const sourceToolText = sourceTools.length ? sourceTools.map(name => toolLabels[name] || name).join(" · ") : "đang nạp danh sách tools";
  const reviewProvider = String(checkpoint.review_provider || selectedAiLabel()).replace(/^./, value => value.toUpperCase());
  const controlState = String(livePayload?.progress?.control_state || checkpoint.control_state || "running").toLowerCase();
  checkpoint.control_state = controlState;
  const checkpointTotal = Number(checkpoint.total_beats || 0);
  const canonicalCheckpointDone = Number(checkpoint.completed_beats || 0);
  const checkpointDone = Number(livePayload?.progress?.completed_beats ?? canonicalCheckpointDone);
  const toolStage = String(livePayload?.progress?.tool_stage || checkpoint?.tool_progress?.stage || "").toLowerCase();
  const displayDone = Number(livePayload?.progress?.display_completed ?? checkpointDone);
  const displayTotal = Number(livePayload?.progress?.display_total ?? checkpointTotal);
  const displayUnit = String(livePayload?.progress?.display_unit || "beat");
  const displayLabel = String(livePayload?.progress?.display_label || "TIẾN ĐỘ TÌM TƯ LIỆU");
  const checkpointPercent = checkpointTotal
    ? Math.min(100, Number(livePayload?.progress?.stage_percent ?? livePayload?.progress?.percent ?? Math.round((checkpointDone / checkpointTotal) * 100)))
    : 0;
  const codexProgress = checkpoint?.workers?.codex || {};
  const batchCurrent = Number(codexProgress.current_batch || 0);
  const batchTotal = Number(codexProgress.total_batches || 0);
  const reviewBatchText = toolStage === "reviewing" && batchCurrent > 0
    ? ` · ${reviewProvider} batch ${batchCurrent}${batchTotal ? `/${batchTotal}` : ""}`
    : "";
  const progressStatusMessage = String(livePayload?.progress?.status_message || checkpoint.status_message || "");
  const currentRunId = String(checkpoint.run_id || "");
  const runningFreshRun = String(checkpoint.status || "").toLowerCase() === "running" && canonicalCheckpointDone === 0;
  const registryMatchesRun = !currentRunId || String(registryData.run_id || "") === currentRunId;
  const reviewMatchesRun = !currentRunId || String(reviewData.run_id || "") === currentRunId;
  const staleSuppressed = checkpointTotal > 0 && ((currentRunId && (!registryMatchesRun || !reviewMatchesRun)) || (!currentRunId && runningFreshRun));
  if (staleSuppressed) {
    registryData = {};
    reviewData = {};
  }
  const assets = Array.isArray(registryData.assets) ? registryData.assets : [];
  const candidates = Array.isArray(reviewData.candidates) ? reviewData.candidates : [];
  const liveItems = Array.isArray(livePayload?.items) ? livePayload.items : [];
  const renderSignature = `${job.id}|${checkpoint.status || ""}|${checkpointDone}|${checkpointTotal}|${toolStage}|${batchCurrent}|${progressStatusMessage}|${controlState}|${liveItems.length}|${candidates.length}|${assets.length}`;
  if (root.dataset.footageRenderSignature === renderSignature && root.children.length > 0) {
    return;
  }
  root.dataset.footageRenderSignature = renderSignature;
  const assetByCandidate = new Map();
  assets.forEach(asset => {
    const candidateId = asset?.source?.candidate_id;
    if (candidateId) assetByCandidate.set(String(candidateId), asset);
  });
  const canonicalPathCounts = new Map();
  assets.forEach(asset => {
    const key = String(asset?.path || "").toLowerCase();
    if (key) canonicalPathCounts.set(key, (canonicalPathCounts.get(key) || 0) + 1);
  });
  const reviewedLocalPaths = new Set(candidates.map(candidate => String(candidate?.local_path || "").toLowerCase()).filter(Boolean));
  const displayCandidates = candidates.filter(candidate => assetByCandidate.has(String(candidate?.candidate_id || "")));
  const items = displayCandidates.map(candidate => {
    const asset = assetByCandidate.get(String(candidate.candidate_id || "")) || null;
    return {
      ...candidate,
      asset_id: asset?.id || null,
      local_path: asset?.path || candidate.local_path || "",
      source_url: candidate.source_url || asset?.source?.url || "",
      kind: candidate.kind || asset?.kind || "unknown",
      canonical: Boolean(asset),
    };
  });
  const knownCandidates = new Set(items.map(item => String(item.candidate_id || "")).filter(Boolean));
  assets.forEach(asset => {
    const candidateId = String(asset?.source?.candidate_id || "");
    if (candidateId && knownCandidates.has(candidateId)) return;
    items.push({
      candidate_id: candidateId || asset.id,
      asset_id: asset.id,
      beat_id: asset.beat_id,
      local_path: asset.path || "",
      source_url: asset?.source?.url || "",
      kind: asset.kind || "unknown",
      decision: "ACCEPT",
      reason: "Asset đã được đưa vào registry.",
      canonical: true,
    });
  });
  const knownLocalPaths = new Set([
    ...items.map(item => String(item.local_path || "").toLowerCase()),
    ...reviewedLocalPaths,
  ].filter(Boolean));
  liveItems.forEach(file => {
    const localPath = String(file?.path || "");
    const key = localPath.toLowerCase();
    if (!localPath || knownLocalPaths.has(key)) return;
    knownLocalPaths.add(key);
    items.push({
      candidate_id: file.candidate_id || file.name || localPath.split(/[\\/]/).pop() || "Footage đã duyệt",
      beat_id: file.beat_id || "",
      local_path: localPath,
      source_url: file.source_url || "",
      kind: file.kind || "unknown",
      timestamp_range: file.timestamp_range || "",
      decision: "ACCEPT",
      reason: file.reason || `${reviewProvider} đã duyệt và chọn footage này để dùng cho beat voice.`,
      canonical: true,
      approvedLive: true,
    });
  });
  const decisions = items.reduce((acc, item) => {
    const key = String(item.decision || "UNKNOWN").toUpperCase();
    acc[key] = (acc[key] || 0) + 1;
    return acc;
  }, {});
  const uniqueFiles = new Set(assets.map(asset => String(asset?.path || "").toLowerCase()).filter(Boolean)).size;
  const aiFallbackCandidates = candidates
    .filter(candidate => candidate?.ai_fallback_recommended === true && candidate?.beat_id)
    .sort((a, b) => String(a.beat_id || "").localeCompare(String(b.beat_id || ""), undefined, { numeric: true }));
  const aiUsageByBeat = new Map();
  (Array.isArray(registryData.ai_usage_notes) ? registryData.ai_usage_notes : []).forEach(note => {
    const beatId = String(note?.beat_id || "");
    if (beatId) aiUsageByBeat.set(beatId, note);
  });
  aiFallbackCandidates.forEach(candidate => {
    const beatId = String(candidate?.beat_id || "");
    if (!beatId || aiUsageByBeat.has(beatId)) return;
    aiUsageByBeat.set(beatId, {
      beat_id: beatId,
      requires_ai: true,
      reason: candidate.ai_fallback_reason || candidate.reason || "Không có video/ảnh thật đủ đúng sau kiểm tra.",
      visual_language: candidate.visual_language || {},
    });
  });
  const aiUsageNotes = [...aiUsageByBeat.values()]
    .sort((a, b) => String(a.beat_id || "").localeCompare(String(b.beat_id || ""), undefined, { numeric: true }));
  const aiFallbackBeats = [...new Set([
    ...(Array.isArray(registryData.ai_fallback_beats) ? registryData.ai_fallback_beats : []),
    ...aiUsageNotes.map(note => String(note.beat_id || "")).filter(Boolean),
  ])];
  const emptyFootageMessage = toolStage === "searching"
    ? "Tools đang tìm nguồn. Candidate tạm sẽ không hiển thị; chỉ footage đã được AI duyệt và chọn dùng cho beat voice mới xuất hiện tại đây."
    : toolStage === "ranking"
      ? "Đang semantic-rank nguồn đã tìm. Candidate chưa duyệt được giữ ẩn; chỉ footage được chọn dùng mới hiện trên app."
      : toolStage === "preparing"
        ? "Đang tải/cắt candidate để AI kiểm tra. File tạm không hiển thị; candidate không được chọn sẽ bị xóa sau khi duyệt."
        : "Chưa có footage nào được AI duyệt và chọn dùng cho beat voice.";
  const candidateDecisions = candidates.reduce((acc, candidate) => {
    const key = String(candidate?.decision || "UNKNOWN").toUpperCase();
    acc[key] = (acc[key] || 0) + 1;
    return acc;
  }, {});
  const aiFallbackPreview = aiUsageNotes.slice(0, 16).map(note => {
    const visualLanguage = note?.visual_language || {};
    const styleBits = [visualLanguage.period, visualLanguage.color_mode, visualLanguage.style_notes].filter(Boolean).join(" · ");
    return `<div class="coverage-beat missing">
    <strong>${escapeHtml(note.beat_id)}</strong>
    <span>${escapeHtml(note.reason || "Không có video/ảnh thật đủ đúng sau kiểm tra; chuyển AI bổ sung.")}${styleBits ? `<br><small>AI style: ${escapeHtml(styleBits)}</small>` : ""}</span>
  </div>`;
  }).join("");
  const aiFallbackNotes = aiUsageNotes.length ? `<section class="workspace-note">
    <strong>ĐÃ NOTE CHUYỂN AI · ${aiUsageNotes.length} beat</strong>
    <p>Chỉ các beat đã hoàn tất cả vòng video thật và ảnh thật mới được chuyển AI; mỗi beat giữ lý do fallback và visual language để prompt AI bám đúng thời kỳ/màu/bối cảnh.</p>
    <div class="artifact-grid two-col">${aiFallbackPreview}</div>
    ${aiUsageNotes.length > 16 ? `<p>Đang hiển thị 16 beat đầu · còn ${aiUsageNotes.length - 16} beat trong JSON kiểm duyệt tư liệu.</p>` : ""}
  </section>` : "";
  const allSortedItems = items
    .sort((a, b) => String(a.beat_id || "").localeCompare(String(b.beat_id || ""), undefined, { numeric: true }));
  const footageLimit = state.footageDisplayLimit || 36;
  const visibleItems = allSortedItems.slice(0, footageLimit);
  const cards = visibleItems
    .map(item => {
      const beat = String(item.beat_id || "Khác");
      const localPath = String(item.local_path || "");
      const preview = item.canonical && localPath ? mediaUrl(job.id, localPath) : "";
      const kind = String(item.kind || "").toLowerCase();
      const ext = localPath.split(".").pop()?.toLowerCase();
      const isVideo = kind.includes("video") || ["mp4", "webm", "mov"].includes(ext);
      const isImage = kind.includes("still") || kind.includes("image") || ["jpg", "jpeg", "png", "webp", "gif"].includes(ext);
      const decision = String(item.decision || "UNKNOWN").toUpperCase();
      const duplicateCount = item.canonical ? (canonicalPathCounts.get(localPath.toLowerCase()) || 0) : 0;
      const decisionBadge = item.approvedLive
        ? `<b class="live-download">ĐÃ DUYỆT</b>`
        : `<b class="decision-${decision.toLowerCase()}">${escapeHtml(decision)}</b>`;
      const beatBadge = `<b class="beat-badge">${escapeHtml(beat)}</b>`;
      const mediaKey = `${job.id}::${beat}::${item.candidate_id || item.asset_id || ""}::${preview}`;
      const media = preservedMedia.has(mediaKey)
        ? `<span class="footage-media-preserve-slot" data-footage-media-slot="${escapeHtml(mediaKey)}"></span>`
        : preview && isVideo
        ? `<div class="footage-video-placeholder" data-footage-video-src="${escapeHtml(preview)}" data-footage-media-key="${escapeHtml(mediaKey)}">
             <img loading="lazy" decoding="async" src="${escapeHtml(mediaPosterUrl(job.id, localPath))}" alt="${escapeHtml(item.candidate_id || item.asset_id || beat)}" />
             <div class="footage-play-trigger" title="Nhấn để phát video">
               <span class="footage-play-trigger-btn">▶</span>
             </div>
           </div>`
        : preview && isImage
          ? `<img loading="lazy" decoding="async" data-footage-media-key="${escapeHtml(mediaKey)}" src="${escapeHtml(mediaPosterUrl(job.id, localPath))}" alt="${escapeHtml(item.candidate_id || item.asset_id || beat)}" />`
          : `<div class="footage-no-preview"><span>▧</span><p>${localPath ? "File không hỗ trợ xem trước" : "Chưa có file local để xem"}</p></div>`;
      return `<article class="footage-card">
        <div class="footage-media">${media}<div class="footage-badges">${beatBadge}${decisionBadge}${item.visually_inspected_actual_content ? `<b class="inspected">Đã xem thật</b>` : ""}${duplicateCount > 1 ? `<b class="duplicate">Dùng ${duplicateCount} beat</b>` : ""}</div></div>
        <div class="footage-card-body">
          <div class="footage-card-title"><strong>${escapeHtml(item.candidate_id || item.asset_id || "Tư liệu")}</strong><span>${escapeHtml(item.timestamp_range || (isImage ? "Ảnh tĩnh" : isVideo ? "Video clip" : ""))}</span></div>
          ${item.visual_match ? `<p><b>Khớp hình:</b> ${escapeHtml(item.visual_match)}</p>` : ""}
          ${item.context_match ? `<p><b>Khớp ngữ cảnh:</b> ${escapeHtml(item.context_match)}</p>` : ""}
          ${item.rights_risk ? `<p><b>Rights:</b> ${escapeHtml(item.rights_risk)}</p>` : ""}
          ${item.reason ? `<p class="footage-reason">${escapeHtml(item.reason)}</p>` : ""}
          <div class="footage-links">${item.source_url ? `<a href="${escapeHtml(item.source_url)}" target="_blank" rel="noreferrer">Mở nguồn ↗</a>` : `<span>Không có link nguồn</span>`}${localPath ? `<span title="${escapeHtml(localPath)}">${escapeHtml(localPath.split(/[\\/]/).pop())}</span>` : ""}</div>
        </div>
      </article>`;
    }).join("");
  const paginationHtml = allSortedItems.length > footageLimit
    ? `<div class="footage-pagination">
         <button type="button" class="primary compact" id="footageLoadMoreBtn">Hiển thị thêm (đang hiện ${visibleItems.length}/${allSortedItems.length} tư liệu)</button>
         <button type="button" class="ghost compact" id="footageShowAllBtn">Hiển thị tất cả (${allSortedItems.length})</button>
       </div>`
    : "";
  const isHybridLike = ["hybrid", "evidence_footage", "selective_footage", "evidence_first"].includes(String(job.visual_strategy || "full_footage").toLowerCase());
  const footageNextTab = isHybridLike ? "ai_visual" : "edit";
  root.innerHTML = `${phaseStepPanelHtml(job, "footage", footageNextTab, true)}
    ${footageControlsHtml(job, checkpoint)}
    ${checkpointTotal ? `<section class="footage-progress-panel ${escapeHtml(checkpoint.status || "running")}">
      <div class="footage-progress-copy"><span>${escapeHtml(displayLabel)}</span><strong>${displayDone}/${displayTotal} ${escapeHtml(displayUnit)}</strong><p>${escapeHtml(progressStatusMessage || "Đang xử lý theo từng batch nhỏ.")}</p></div>
      <div class="footage-progress-meter"><div><span style="width:${checkpointPercent}%"></span></div><small>${checkpointPercent}% · ${escapeHtml(displayLabel)}${escapeHtml(reviewBatchText)} · ${escapeHtml(controlState === "paused" ? "TẠM DỪNG" : controlState === "stop_requested" ? "ĐANG DỪNG" : "ĐANG CHẠY")}</small></div>
    </section>` : ""}
    ${staleSuppressed ? `<div class="workspace-note">Đang chạy lượt Footage mới. Kết quả của lượt trước đã được tách khỏi bảng hiện tại để tránh nhầm dữ liệu.</div>` : ""}
    <section class="footage-summary">
      <div><span>Ứng viên đã kiểm tra</span><strong>${candidates.length}</strong></div>
      <div><span>Tư liệu dùng được</span><strong>${assets.length}</strong></div>
      <div><span>Chuyển AI</span><strong>${aiFallbackBeats.length}</strong></div>
      <div><span>Footage đã chọn</span><strong>${liveItems.length}</strong></div>
      <div><span>Cần REVIEW</span><strong>${candidateDecisions.REVIEW || 0}</strong></div>
      <div><span>REJECT</span><strong>${candidateDecisions.REJECT || 0}</strong></div>
      <div><span>File dùng thật khác nhau</span><strong>${uniqueFiles}</strong></div>
      <div><span>Nguồn tools</span><strong>${sourceTools.length || "—"}</strong></div>
    </section>
    ${aiFallbackNotes}
    ${items.length ? `<div class="footage-grid footage-gallery">${cards}${paginationHtml}</div>` : `<div class="empty-state">${escapeHtml(emptyFootageMessage)}</div>`}
    <details class="technical-details" id="footageTechDetails"><summary>Chi tiết kỹ thuật · Nguồn Tools (${escapeHtml(sourceTools.length ? `${sourceTools.length} nguồn` : "—")}) &amp; JSON</summary><div class="artifact-grid two-col" id="footageTechGrid"><p style="grid-column: 1 / -1; color: #6a889f; padding: 12px; margin: 0; font-size: 11px;">Nhấn để hiển thị danh sách nguồn (${escapeHtml(sourceToolText)}) và 5 tệp JSON kỹ thuật...</p></div></details>`;
  root.querySelectorAll("[data-footage-media-slot]").forEach(slot => {
    const mediaKey = String(slot.dataset.footageMediaSlot || "");
    const existing = preservedMedia.get(mediaKey);
    if (existing) slot.replaceWith(existing);
  });
  const techDetails = root.querySelector("#footageTechDetails");
  if (techDetails) {
    techDetails.addEventListener("toggle", () => {
      if (techDetails.open) {
        const grid = techDetails.querySelector("#footageTechGrid");
        if (grid && !grid.dataset.loaded) {
          grid.dataset.loaded = "true";
          grid.innerHTML = `${codeViewer("Điểm lưu Footage", checkpointRaw)}${codeViewer("Danh mục tư liệu", registry)}${codeViewer("Kiểm duyệt tư liệu", review)}${codeViewer("Ma trận phủ hình", coverage)}${codeViewer("Báo cáo trước dựng", report)}`;
        }
      }
    });
  }
  root.querySelector("#footageLoadMoreBtn")?.addEventListener("click", () => {
    state.footageDisplayLimit = (state.footageDisplayLimit || 36) + 36;
    renderFootageWorkspace(job);
  });
  root.querySelector("#footageShowAllBtn")?.addEventListener("click", () => {
    state.footageDisplayLimit = 9999;
    renderFootageWorkspace(job);
  });
  bindWorkspacePhaseButtons(job, root);
  bindFootageControlButtons(job, root);
  bindFootageVideoPlaceholders(root);
  } finally {
    footageRenderInFlight = false;
  }
}

async function renderAIVisualWorkspace(job) {
  $("#aiVisualProjectLabel").textContent = selectedProjectLabel(job);
  const root = $("#aiVisualWorkspace");
  if (!job) return root.innerHTML = `<div class="empty-state">Chọn một dự án để xem phần AI bổ sung.</div>`;
  if (!effectivePhases(job).includes("ai_visual")) {
    root.innerHTML = `${phaseStepPanelHtml(job, "ai_visual")}<div class="empty-state">Dự án này chạy Full Footage nên không cần bước AI Visual.</div>`;
    return;
  }
  if (aiVisualRenderInFlight) return;
  aiVisualRenderInFlight = true;
  const preservedFrame = root.querySelector("#cofiStudioFrame");
  const renderedJobId = String(root.dataset.aiVisualJobId || "");
  try {
  let embedInfo = null;
  let embedError = "";
  try {
    embedInfo = await ensureCofiStudioEmbed(job);
  } catch (err) {
    embedError = err.message || String(err);
  }
  let visualSettings = embedInfo?.settings || null;
  if (!visualSettings) {
    try {
      visualSettings = await api(`/api/jobs/${encodeURIComponent(job.id)}/ai-visual-settings`);
    } catch (_) {}
  }
  const [manifestRaw, registryRaw] = await Promise.all([
    artifact(job.id, "ai_visual_manifest.json"), artifact(job.id, "asset_registry.json")
  ]);
  const manifest = safeJson(manifestRaw, {});
  const generated = Array.isArray(manifest.generated) ? manifest.generated : [];
  const errors = Array.isArray(manifest.errors) ? manifest.errors : [];
  const targets = Array.isArray(manifest.target_beat_ids) ? manifest.target_beat_ids : [];
  const remaining = Array.isArray(manifest.remaining_missing_beats) ? manifest.remaining_missing_beats : [];
  const cards = generated.map(item => {
    const path = String(item.video_path || item.image_path || "");
    const isVideo = Boolean(item.video_path);
    const preview = path ? mediaUrl(job.id, path) : "";
    const visualLanguage = item?.visual_language || {};
    const styleBits = [visualLanguage.period, visualLanguage.color_mode, visualLanguage.style_notes].filter(Boolean).join(" · ");
    return `<article class="footage-card ai-visual-card">
      <div class="footage-media">${preview ? (isVideo
        ? `<div class="footage-video-placeholder" data-ai-video-src="${escapeHtml(preview)}">
             <img loading="lazy" decoding="async" src="${escapeHtml(mediaPosterUrl(job.id, path))}" alt="${escapeHtml(item.beat_id || "AI visual")}" />
             <div class="footage-play-trigger" title="Nhấn để phát video">
               <span class="footage-play-trigger-btn">▶</span>
             </div>
           </div>`
        : `<img loading="lazy" decoding="async" src="${escapeHtml(preview)}" alt="${escapeHtml(item.beat_id || "AI visual")}" />`) : ""}
        <div class="footage-badges"><b class="inspected">AI RECONSTRUCTION</b></div>
      </div>
      <div class="footage-card-body">
        <div class="footage-card-title"><strong>${escapeHtml(item.beat_id || "—")}</strong><span>${isVideo ? "Clip AI" : "Ảnh AI"}</span></div>
        <p>${isVideo ? "Ảnh AI đã được dùng làm keyframe rồi chuyển thành clip." : "Ảnh AI được giữ làm visual fallback."}</p>
        ${item.ai_reason ? `<p class="footage-reason"><b>Lý do dùng AI:</b> ${escapeHtml(item.ai_reason)}</p>` : ""}
        ${styleBits ? `<p><b>Visual language:</b> ${escapeHtml(styleBits)}</p>` : ""}
        ${item.video_error ? `<p class="footage-reason">Không tạo được clip; ảnh đã tạo vẫn được giữ và dùng ngay.</p>` : ""}
      </div>
    </article>`;
  }).join("");
  const phaseStatus = String(job.phases?.ai_visual?.status || "pending");
  const fullAiMode = visualSettings?.coverage_mode === "full_ai";
  const summary = phaseStatus === "pending"
    ? (fullAiMode
      ? "Bước này chưa chạy. Full AI sẽ tạo hình cho toàn bộ beat trong timeline."
      : "Bước này chưa chạy. AI chỉ bổ sung beat vẫn chưa có asset thật hoặc motion native phù hợp.")
    : !targets.length
      ? "Footage đã đủ nên bước AI không tạo thêm media."
      : `${fullAiMode ? "Full AI đã nhắm" : "Đã nhắm"} ${targets.length} beat; tạo được ${generated.length}, còn ${remaining.length}.`;
  const summaryHtml = `<div><span>Beat cần AI</span><strong>${targets.length}</strong></div>
      <div><span>Đã tạo</span><strong>${generated.length}</strong></div>
      <div><span>Clip AI</span><strong>${generated.filter(item => item.video_path).length}</strong></div>
      <div><span>Ảnh fallback</span><strong>${generated.filter(item => !item.video_path && item.image_path).length}</strong></div>
      <div><span>Lỗi tạo ảnh</span><strong>${errors.length}</strong></div>
      <div><span>Còn thiếu</span><strong>${remaining.length}</strong></div>`;
  const noteHtml = `${escapeHtml(summary)} AI media được ghi nhãn <b>illustrative reconstruction</b>, không giả làm tư liệu thật.`;
  const resultsHtml = cards ? `<div class="footage-grid">${cards}</div>` : `<div class="empty-state">Chưa có AI visual được tạo cho dự án này.</div>`;
  const clipCount = generated.filter(item => item.video_path).length;
  const imageCount = generated.filter(item => !item.video_path && item.image_path).length;
  const targetCount = targets.length || Number(lastAiVisualRuntimeSnapshot?.job?.targets || 0) || (generated.length + remaining.length);
  const stylePresets = Array.isArray(visualSettings?.style_presets) ? visualSettings.style_presets : [];
  const selectedStyleMode = String(visualSettings?.style_mode || "auto");
  const selectedStylePreset = String(visualSettings?.style_preset || "");
  const selectedCustomStyle = String(visualSettings?.custom_style || "");
  const selectedAiMediaMode = String(visualSettings?.ai_media_mode || job.ai_media_mode || "mixed");
  const selectedVisualStrategy = String(job.visual_strategy || "full_footage").toLowerCase();
  const styleReferencePath = String(visualSettings?.style_reference_image || "");
  const styleReferenceUrl = styleReferencePath ? mediaUrl(job.id, styleReferencePath) : "";
  const styleOptions = [
    `<option value=""${selectedStylePreset ? "" : " selected"}>Tự động theo nội dung · Documentary AI</option>`,
    ...stylePresets.map(item => {
      const name = String(item?.name || "");
      return `<option value="${escapeHtml(name)}"${name === selectedStylePreset ? " selected" : ""}>${escapeHtml(name)}</option>`;
    }),
  ].join("");
  const styleSummaryText = [
    selectedStyleMode === "preset" ? (selectedStylePreset ? `Preset: ${selectedStylePreset}` : "Preset STP") : selectedStyleMode === "custom" ? "Phong cách tự nhập" : "AI tự chọn",
    selectedAiMediaMode === "video" ? "Chỉ video" : selectedAiMediaMode === "image" ? "Chỉ ảnh" : "Ảnh + Video",
    selectedVisualStrategy === "full_ai" ? "Full AI" : (selectedVisualStrategy === "edit_direct_footage" || selectedVisualStrategy === "semi_content") ? "Bán Content (Edit tải Footage + Vài ảnh AI)" : (selectedVisualStrategy === "evidence_footage" || selectedVisualStrategy === "selective_footage") ? "Bằng chứng + AI" : selectedVisualStrategy === "hybrid" ? "Footage + AI" : "Full Footage"
  ].filter(Boolean).join(" · ");

  const styleControlHtml = `<section class="ai-visual-compact-header" id="aiVisualStylePanel">
    <div class="ai-visual-compact-head">
      <div class="ai-visual-compact-left">
        <span class="ai-visual-step-badge">BƯỚC 5: AI BỔ SUNG</span>
        <span class="ai-visual-mode-badge">${fullAiMode ? "FULL AI" : (selectedVisualStrategy === "edit_direct_footage" ? "VÀI ẢNH AI ĐIỂM NHẤN" : "AI BỔ SUNG")}</span>
        <span class="ai-visual-meta-chip">🎨 ${escapeHtml(selectedStyleMode === "preset" ? (selectedStylePreset || "Preset STP") : selectedStyleMode === "custom" ? "Tự nhập" : "Tự động")}</span>
        <span class="ai-visual-meta-chip">🎬 ${selectedAiMediaMode === "video" ? "Video" : selectedAiMediaMode === "image" ? "Ảnh" : "Ảnh + Video"}</span>
        ${styleReferenceUrl ? `<span class="ai-visual-meta-chip reference-chip"><img src="${escapeHtml(styleReferenceUrl)}" alt="Mẫu" /> Ảnh mẫu</span>` : ""}
        <small class="ai-visual-model-chip" data-ai-visual-settings-label>${embedInfo ? `Ảnh: ${escapeHtml(embedInfo.settings.image_model)} · Video: ${escapeHtml(embedInfo.settings.video_model)} · ${escapeHtml(embedInfo.settings.aspect_ratio)}` : "Đang chờ Media Factory"}</small>
      </div>
      <div class="ai-visual-compact-actions">
        <button class="ghost compact" type="button" id="toggleAiVisualStyleGridBtn" title="Tùy chỉnh phong cách nghệ thuật, preset và tỷ lệ hình ảnh">⚙ Đổi phong cách</button>
        <button class="primary compact" id="openAiVisualDialogBtn" type="button" title="Mở popup xem đầy đủ ${generated.length} boxcard ảnh và video AI">🖼 Xem kết quả AI (${generated.length}/${targetCount})</button>
        <button class="ghost compact" id="fullscreenCofiStudioBtn" type="button" title="Phóng to Media Factory toàn màn hình">⛶ Phóng to</button>
        ${embedInfo ? `<span class="voice-live-dot">Đã kết nối</span><button class="ghost compact" id="reloadCofiStudioBtn" title="Tải lại giao diện Media Factory">↻ Tải lại tools</button>` : `<button class="primary compact" id="startCofiStudioBtn">Bật Media Factory</button>`}
        ${job.phases?.ai_visual?.status === "succeeded" ? `<button class="primary compact" data-open-step="edit">Sang bước 6: Edit →</button>` : ""}
      </div>
    </div>
    <div class="ai-visual-style-grid" id="aiVisualStyleGrid" hidden>
      <label class="ai-visual-style-field"><span>Luồng hình ảnh của dự án</span><select id="aiVisualProjectStrategy"><option value="full_ai"${selectedVisualStrategy === "full_ai" ? " selected" : ""}>Full AI · bỏ qua Footage</option><option value="edit_direct_footage"${selectedVisualStrategy === "edit_direct_footage" ? " selected" : ""}>Bán Content · AI tải Footage lúc Edit + Vài ảnh AI (Bỏ qua Bước 4)</option><option value="evidence_footage"${(selectedVisualStrategy === "evidence_footage" || selectedVisualStrategy === "selective_footage") ? " selected" : ""}>Bằng chứng + AI (chỉ footage chứng cứ thật, còn lại AI)</option><option value="hybrid"${selectedVisualStrategy === "hybrid" ? " selected" : ""}>Kết hợp Footage + AI</option><option value="full_footage"${selectedVisualStrategy === "full_footage" ? " selected" : ""}>Full Footage</option></select><small>Đổi tại đây sẽ cập nhật luồng sản xuất thật của dự án. Full AI / Bán Content đi thẳng Visuals/STP → AI Visual → Edit.</small></label>
      <label class="ai-visual-style-field"><span>Phong cách vẽ ảnh</span><select id="aiVisualStyleMode"><option value="auto"${selectedStyleMode === "auto" ? " selected" : ""}>AI tự chọn</option><option value="preset"${selectedStyleMode === "preset" ? " selected" : ""}>Preset SRT-To-Prompt</option><option value="custom"${selectedStyleMode === "custom" ? " selected" : ""}>Tự nhập phong cách</option></select><small>Preset được đọc từ thư viện STP cục bộ.</small></label>
      <label class="ai-visual-style-field"><span>Preset nét vẽ</span><select id="aiVisualStylePreset"${selectedStyleMode === "preset" ? "" : " disabled"}>${styleOptions}</select><small>Chỉ áp dụng khi chọn chế độ Preset.</small></label>
      <label class="ai-visual-style-field"><span>Kiểu media AI</span><select id="aiVisualMediaMode"><option value="image"${selectedAiMediaMode === "image" ? " selected" : ""}>Chỉ ảnh</option><option value="video"${selectedAiMediaMode === "video" ? " selected" : ""}>Chỉ video</option><option value="mixed"${selectedAiMediaMode === "mixed" ? " selected" : ""}>Ảnh + video</option></select><small>Áp dụng cho các Visual được route sang AI.</small></label>
      <label class="ai-visual-style-field ai-visual-custom-style"><span>Phong cách tự nhập</span><textarea id="aiVisualCustomStyle" rows="4"${selectedStyleMode === "custom" ? "" : " disabled"} placeholder="Mô tả nét vẽ, bảng màu, ánh sáng, chất liệu, bố cục…">${escapeHtml(selectedCustomStyle)}</textarea><small>Có thể mô tả phong cách mới không có trong preset.</small></label>
      <div class="ai-visual-style-field"><span>Phạm vi tạo hình</span><div class="ai-visual-mode-options">
        <label><input type="radio" name="aiVisualCoverageMode" value="fallback_only"${fullAiMode ? "" : " checked"}><div><b>AI bổ sung</b><small>Chỉ vẽ phần Footage còn thiếu</small></div></label>
        <label><input type="radio" name="aiVisualCoverageMode" value="full_ai"${fullAiMode ? " checked" : ""}><div><b>Full AI</b><small>Vẽ toàn bộ beat trong video</small></div></label>
      </div></div>
      <div class="ai-visual-style-field ai-visual-reference-field"><span>Ảnh tham chiếu phong cách</span>
        <div class="ai-visual-reference-row">
          <label class="ai-visual-upload-btn" for="aiVisualStyleReferenceInput">＋ Chọn ảnh mẫu</label>
          <input id="aiVisualStyleReferenceInput" type="file" accept="image/png,image/jpeg,image/webp" hidden>
          <button class="ghost compact" id="aiVisualClearStyleReferenceBtn" type="button"${styleReferencePath ? "" : " disabled"}>Xóa ảnh</button>
        </div>
        <div class="ai-visual-reference-preview" id="aiVisualStyleReferencePreview"${styleReferenceUrl ? "" : " hidden"}>${styleReferenceUrl ? `<img src="${escapeHtml(styleReferenceUrl)}" alt="Ảnh tham chiếu phong cách"><span>Đang dùng ảnh mẫu cho art direction</span>` : ""}</div>
        <small>PNG/JPG/WEBP · tối đa 12 MB. Ảnh này chỉ dùng để bám nét vẽ, màu, ánh sáng và bố cục; không sao chép nội dung trong ảnh.</small>
      </div>
    </div>
  </section>`;
  const updateDialogContent = () => {
    const dialogTitle = $("#aiVisualDialogTitle");
    if (dialogTitle) dialogTitle.textContent = `Thư viện boxcard ảnh & video AI (${generated.length}/${targetCount} beat)`;
    const dialogContent = $("#aiVisualDialogContent");
    if (dialogContent) {
      dialogContent.innerHTML = `<section class="footage-summary" data-ai-visual-summary>${summaryHtml}</section>
        <div class="workspace-note" data-ai-visual-note>${noteHtml}</div>
        <div data-ai-visual-results>${resultsHtml}</div>`;
      bindFootageVideoPlaceholders(dialogContent);
    }
  };

  const remainingDisplay = remaining.length || Math.max(0, targetCount - generated.length);
  const quickbarHtml = `<div class="ai-visual-quickbar">
    <div class="ai-visual-quick-stats">
      <span class="ai-visual-stat-pill"><b>${generated.length}/${targetCount}</b> beat đã tạo</span>
      <span class="ai-visual-stat-pill"><b>${clipCount}</b> clip AI</span>
      <span class="ai-visual-stat-pill"><b>${imageCount}</b> ảnh fallback</span>
      ${remainingDisplay > 0 ? `<span class="ai-visual-stat-pill warn"><b>${remainingDisplay}</b> còn thiếu</span>` : (targetCount > 0 && generated.length >= targetCount ? `<span class="ai-visual-stat-pill success">Hoàn thành</span>` : `<span class="ai-visual-stat-pill warn"><b>0</b> còn thiếu</span>`)}
    </div>
    <div class="ai-visual-quick-actions">
      <button class="ghost compact" id="refreshAiVisualProgressBtn" type="button" title="Đồng bộ lại tiến độ thực tế từ Media Factory và ổ cứng">🔄 Làm mới tiến độ</button>
      <button class="ghost compact" id="resetAiVisualProgressBtn" type="button" title="Xóa toàn bộ ảnh/video AI đã tạo và reset tiến độ về 0">🗑 Xóa & Reset</button>
      <button class="primary compact" id="openAiVisualDialogBottomBtn" type="button">🖼 Xem thư viện boxcard đã tạo (${generated.length}) ↗</button>
    </div>
  </div>`;

  const bindQuickbarActionButtons = () => {
    root.querySelector("#openAiVisualDialogBottomBtn")?.addEventListener("click", openAiVisualCardsDialog);
    root.querySelector("#refreshAiVisualProgressBtn")?.addEventListener("click", async event => {
      const btn = event.currentTarget;
      btn.disabled = true;
      btn.textContent = "⏳ Đang đồng bộ…";
      try {
        await refreshAiVisualRuntime(job, { silent: false });
        await syncAiVisualDialogFromDisk(job.id);
        toast("Đã đồng bộ tiến độ AI Visual mới nhất.");
      } catch (err) {
        toast(`Không đồng bộ được tiến độ: ${err.message}`, true);
      } finally {
        btn.disabled = false;
        btn.textContent = "🔄 Làm mới tiến độ";
      }
    });
    root.querySelector("#resetAiVisualProgressBtn")?.addEventListener("click", async event => {
      if (!window.confirm("Xóa toàn bộ ảnh/video AI đã tạo trong dự án này và reset tiến độ về 0?")) return;
      const btn = event.currentTarget;
      btn.disabled = true;
      btn.textContent = "⏳ Đang xóa…";
      try {
        await api(`/api/jobs/${encodeURIComponent(job.id)}/ai-visual-reset`, {
          method: "POST",
          body: JSON.stringify({ clear_media_factory: true }),
        });
        const frame = root.querySelector("#cofiStudioFrame");
        if (frame) {
          try {
            const url = new URL(frame.src, window.location.origin);
            url.searchParams.set("t", String(Date.now()));
            frame.src = url.toString();
          } catch (_) {}
        }
        await refreshAiVisualRuntime(job, { silent: false });
        await syncAiVisualDialogFromDisk(job.id);
        toast("Đã xóa toàn bộ kết quả AI Visual và reset tiến độ về 0.");
      } catch (err) {
        toast(`Không reset được tiến độ AI Visual: ${err.message}`, true);
      } finally {
        btn.disabled = false;
        btn.textContent = "🗑 Xóa & Reset";
      }
    });
  };

  const bindAiVisualEvents = () => {
    root.querySelector("#toggleAiVisualStyleGridBtn")?.addEventListener("click", () => {
      const panel = root.querySelector("#aiVisualStylePanel");
      const grid = root.querySelector("#aiVisualStyleGrid");
      const btn = root.querySelector("#toggleAiVisualStyleGridBtn");
      if (!grid) return;
      const isHidden = grid.hidden;
      grid.hidden = !isHidden;
      panel?.classList.toggle("is-expanded", isHidden);
      if (btn) btn.textContent = isHidden ? "▲ Thu gọn tùy chỉnh" : "⚙ Tùy chỉnh nâng cao";
    });
    root.querySelector("#openAiVisualDialogBtn")?.addEventListener("click", openAiVisualCardsDialog);
    bindQuickbarActionButtons();
    root.querySelector("#fullscreenCofiStudioBtn")?.addEventListener("click", () => {
      const card = root.querySelector(".cofistudio-embed-card");
      const btn = root.querySelector("#fullscreenCofiStudioBtn");
      if (!card) return;
      const isFull = card.classList.toggle("is-fullscreen");
      if (btn) btn.textContent = isFull ? "⛶ Thu nhỏ" : "⛶ Phóng to";
    });
    root.querySelector("#reloadCofiStudioBtn")?.addEventListener("click", () => {
      const frame = root.querySelector("#cofiStudioFrame");
      if (!frame) return;
      const url = new URL(frame.src, window.location.origin);
      url.searchParams.set("t", String(Date.now()));
      frame.src = url.toString();
    });
    root.querySelector("#startCofiStudioBtn")?.addEventListener("click", async event => {
      event.currentTarget.disabled = true;
      event.currentTarget.textContent = "Đang bật Media Factory…";
      try {
        state.workspaceRenderKeys.ai_visual = null;
        await renderAIVisualWorkspace(job);
      } catch (err) {
        toast(err.message, true);
      }
    });
    root.querySelector("#aiVisualProjectStrategy")?.addEventListener("change", async event => {
      const visualStrategy = String(event.currentTarget.value || "full_ai");
      try {
        await api(`/api/jobs/${encodeURIComponent(job.id)}/production-settings`, {
          method: "PATCH",
          body: JSON.stringify({ visual_strategy: visualStrategy, ai_media_mode: selectedAiMediaMode }),
        });
        await loadJobs(true);
        const refreshed = state.jobs.find(item => item.id === job.id);
        state.workspaceRenderKeys.ai_visual = null;
        if (refreshed) await renderAIVisualWorkspace(refreshed);
        toast(visualStrategy === "full_ai" ? "Đã chuyển dự án sang Full AI. Footage đã được bỏ khỏi luồng." : "Đã cập nhật luồng hình ảnh của dự án.");
      } catch (err) {
        toast(`Không đổi được luồng sản xuất: ${err.message}`, true);
      }
    });
    root.querySelector("#aiVisualStyleMode")?.addEventListener("change", async event => {
      const styleMode = String(event.currentTarget.value || "auto");
      const preset = root.querySelector("#aiVisualStylePreset");
      const custom = root.querySelector("#aiVisualCustomStyle");
      if (preset) preset.disabled = false;
      if (custom) custom.disabled = styleMode !== "custom";
      if (styleMode === "preset" && preset && !preset.value) {
        const firstPreset = [...preset.options].find(opt => opt.value);
        if (firstPreset) preset.value = firstPreset.value;
      }
      try {
        const patchBody = { style_mode: styleMode };
        if (styleMode === "preset" && preset?.value) patchBody.style_preset = String(preset.value);
        const saved = await api(`/api/jobs/${encodeURIComponent(job.id)}/ai-visual-settings`, {
          method: "PATCH",
          body: JSON.stringify(patchBody),
        });
        visualSettings = saved;
        if (state.aiVisualEmbedInfo && state.aiVisualEmbedJobId === job.id) state.aiVisualEmbedInfo.settings = saved;
        toast("Đã đổi chế độ phong cách AI.");
      } catch (err) {
        toast(`Không lưu được chế độ phong cách: ${err.message}`, true);
      }
    });
    root.querySelector("#aiVisualStylePreset")?.addEventListener("change", async event => {
      const stylePreset = String(event.currentTarget.value || "");
      const modeSelect = root.querySelector("#aiVisualStyleMode");
      if (modeSelect && stylePreset) modeSelect.value = "preset";
      try {
        const saved = await api(`/api/jobs/${encodeURIComponent(job.id)}/ai-visual-settings`, {
          method: "PATCH",
          body: JSON.stringify({
            style_mode: stylePreset ? "preset" : "auto",
            style_preset: stylePreset,
          }),
        });
        visualSettings = saved;
        if (state.aiVisualEmbedInfo && state.aiVisualEmbedJobId === job.id) state.aiVisualEmbedInfo.settings = saved;
        toast(stylePreset ? `Đã chọn phong cách: ${stylePreset}` : "Đã bỏ preset; hãy chọn preset khác hoặc đổi chế độ phong cách.");
      } catch (err) {
        toast(`Không lưu được phong cách: ${err.message}`, true);
      }
    });
    root.querySelector("#aiVisualCustomStyle")?.addEventListener("change", async event => {
      try {
        const saved = await api(`/api/jobs/${encodeURIComponent(job.id)}/ai-visual-settings`, {
          method: "PATCH",
          body: JSON.stringify({ style_mode: "custom", custom_style: String(event.currentTarget.value || "") }),
        });
        visualSettings = saved;
        if (state.aiVisualEmbedInfo && state.aiVisualEmbedJobId === job.id) state.aiVisualEmbedInfo.settings = saved;
        toast("Đã lưu phong cách tự nhập.");
      } catch (err) {
        toast(`Không lưu được phong cách tự nhập: ${err.message}`, true);
      }
    });
    root.querySelector("#aiVisualMediaMode")?.addEventListener("change", async event => {
      try {
        const savedJob = await api(`/api/jobs/${encodeURIComponent(job.id)}/production-settings`, {
          method: "PATCH",
          body: JSON.stringify({ ai_media_mode: String(event.currentTarget.value || "mixed") }),
        });
        await loadJobs(true);
        const refreshed = state.jobs.find(item => item.id === job.id) || savedJob;
        visualSettings = await api(`/api/jobs/${encodeURIComponent(job.id)}/ai-visual-settings`);
        if (state.aiVisualEmbedInfo && state.aiVisualEmbedJobId === job.id) state.aiVisualEmbedInfo.settings = visualSettings;
        toast("Đã lưu kiểu media AI.");
        state.workspaceRenderKeys.ai_visual = null;
        if (refreshed) await renderAIVisualWorkspace(refreshed);
      } catch (err) {
        toast(`Không lưu được kiểu media AI: ${err.message}`, true);
      }
    });
    root.querySelectorAll('input[name="aiVisualCoverageMode"]').forEach(input => input.addEventListener("change", async event => {
      if (!event.currentTarget.checked) return;
      try {
        const visualStrategy = event.currentTarget.value === "full_ai" ? "full_ai" : "hybrid";
        await api(`/api/jobs/${encodeURIComponent(job.id)}/production-settings`, {
          method: "PATCH",
          body: JSON.stringify({ visual_strategy: visualStrategy }),
        });
        await loadJobs(true);
        const refreshed = state.jobs.find(item => item.id === job.id);
        state.workspaceRenderKeys.ai_visual = null;
        if (refreshed) await renderAIVisualWorkspace(refreshed);
      } catch (err) {
        toast(`Không lưu được chế độ AI Visual: ${err.message}`, true);
      }
    }));
    root.querySelector("#aiVisualStyleReferenceInput")?.addEventListener("change", async event => {
      const file = event.currentTarget.files?.[0];
      if (!file) return;
      if (file.size > 12 * 1024 * 1024) {
        toast("Ảnh tham chiếu phải nhỏ hơn hoặc bằng 12 MB.", true);
        event.currentTarget.value = "";
        return;
      }
      try {
        const dataUrl = await new Promise((resolve, reject) => {
          const reader = new FileReader();
          reader.onload = () => resolve(String(reader.result || ""));
          reader.onerror = () => reject(new Error("Không đọc được ảnh đã chọn"));
          reader.readAsDataURL(file);
        });
        const saved = await api(`/api/jobs/${encodeURIComponent(job.id)}/ai-visual-settings`, {
          method: "PATCH",
          body: JSON.stringify({ reference_image_name: file.name, reference_image_data_url: dataUrl }),
        });
        visualSettings = saved;
        if (state.aiVisualEmbedInfo && state.aiVisualEmbedJobId === job.id) state.aiVisualEmbedInfo.settings = saved;
        const preview = root.querySelector("#aiVisualStyleReferencePreview");
        if (preview) {
          preview.hidden = false;
          preview.innerHTML = `<img src="${escapeHtml(dataUrl)}" alt="Ảnh tham chiếu phong cách"><span>Đang dùng ảnh mẫu cho art direction</span>`;
        }
        const clearBtn = root.querySelector("#aiVisualClearStyleReferenceBtn");
        if (clearBtn) clearBtn.disabled = false;
        toast("Đã lưu ảnh tham chiếu phong cách.");
      } catch (err) {
        toast(`Không lưu được ảnh tham chiếu: ${err.message}`, true);
      } finally {
        event.currentTarget.value = "";
      }
    });
    root.querySelector("#aiVisualClearStyleReferenceBtn")?.addEventListener("click", async event => {
      try {
        const saved = await api(`/api/jobs/${encodeURIComponent(job.id)}/ai-visual-settings`, {
          method: "PATCH",
          body: JSON.stringify({ clear_style_reference: true }),
        });
        visualSettings = saved;
        if (state.aiVisualEmbedInfo && state.aiVisualEmbedJobId === job.id) state.aiVisualEmbedInfo.settings = saved;
        const preview = root.querySelector("#aiVisualStyleReferencePreview");
        if (preview) {
          preview.hidden = true;
          preview.innerHTML = "";
        }
        event.currentTarget.disabled = true;
        toast("Đã xóa ảnh tham chiếu phong cách.");
      } catch (err) {
        toast(`Không xóa được ảnh tham chiếu: ${err.message}`, true);
      }
    });
  };

  const hasMediaFactoryJobs = Array.isArray(manifest.media_factory_jobs) && manifest.media_factory_jobs.length > 0;
  const targetBundleVer = "20261017-v4";
  if (preservedFrame && renderedJobId === String(job.id)) {
    const needsBundleUpgrade = preservedFrame.dataset.bundleVer !== targetBundleVer;
    const needsSceneRefresh = hasMediaFactoryJobs && preservedFrame.dataset.hasScenes !== "true";
    if (needsBundleUpgrade || needsSceneRefresh) {
      preservedFrame.dataset.bundleVer = targetBundleVer;
      if (hasMediaFactoryJobs) preservedFrame.dataset.hasScenes = "true";
      try {
        const url = new URL(preservedFrame.src, window.location.origin);
        url.searchParams.set("v", targetBundleVer);
        url.searchParams.set("t", String(Date.now()));
        preservedFrame.src = url.toString();
      } catch (_) {}
    }
    const phaseRoot = root.querySelector("[data-ai-visual-phase]");
    const settingsLabel = root.querySelector("[data-ai-visual-settings-label]");
    const openBtn = root.querySelector("#openAiVisualDialogBtn");
    const quickbar = root.querySelector(".ai-visual-quickbar");
    if (phaseRoot) {
      phaseRoot.innerHTML = phaseStepPanelHtml(job, "ai_visual", "edit");
      bindWorkspacePhaseButtons(job, phaseRoot);
    }
    if (openBtn) openBtn.innerHTML = `🖼 Xem kết quả AI (${generated.length}/${targetCount})`;
    if (quickbar) {
      quickbar.outerHTML = quickbarHtml;
      bindQuickbarActionButtons();
    }
    if (settingsLabel && embedInfo) settingsLabel.textContent = `Ảnh: ${embedInfo.settings.image_model} · Video: ${embedInfo.settings.video_model} · ${embedInfo.settings.aspect_ratio}`;
    updateDialogContent();
    await refreshAiVisualRuntime(job, { silent: true });
    scheduleAiVisualRuntimePoll(job);
    return;
  }
  root.dataset.aiVisualJobId = String(job.id);
  root.innerHTML = `<div data-ai-visual-phase style="display:none;"></div>
    ${styleControlHtml}
    <section class="ai-visual-runtime-panel" id="aiVisualRuntimePanel" data-job-id="${escapeHtml(job.id)}">
      <div class="ai-runtime-loading"><span></span>Đang đọc Chrome, session và queue thật…</div>
    </section>
    <section class="cofistudio-embed-card">
      ${embedInfo
        ? `<iframe class="cofistudio-frame" id="cofiStudioFrame" data-cofi-studio-embed="true" data-bundle-ver="${targetBundleVer}" data-has-scenes="${hasMediaFactoryJobs ? "true" : "false"}" src="${escapeHtml(embedInfo.url)}${embedInfo.url.includes('?') ? '&' : '?'}v=${targetBundleVer}&t=${Date.now()}" title="AI Media Factory tích hợp"></iframe>`
        : `<div class="cofistudio-offline"><strong>Media Factory tích hợp chưa khởi động được</strong><p>${escapeHtml(embedError || "Bấm nút trên để bật lại bộ tạo ảnh/video tích hợp.")}</p></div>`}
    </section>
    ${quickbarHtml}`;
  updateDialogContent();
  bindAiVisualEvents();
  bindWorkspacePhaseButtons(job, root);
  await refreshAiVisualRuntime(job, { silent: true });
  scheduleAiVisualRuntimePoll(job);
  } finally {
    aiVisualRenderInFlight = false;
  }
}

function liveEditStatusText(session, fallback) {
  const event = session?.live_edit_event;
  if (!event) return fallback;
  const seconds = Number(event.timestamp_sec);
  const time = Number.isFinite(seconds)
    ? `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String((seconds % 60).toFixed(1)).padStart(4, "0")}`
    : "";
  const beat = event.beat_id ? `${event.beat_id}${time ? ` · ${time}` : ""}` : time;
  return `Codex vừa sửa${beat ? ` ${beat}` : ""}${event.message ? ` · ${event.message}` : ""}`;
}

function editProgressText(progress) {
  if (!progress || !Number(progress.total_beats || 0)) return "";
  const completed = Number(progress.completed_beats || 0);
  const total = Number(progress.total_beats || 0);
  const currentBatch = Number(progress.current_batch || 0);
  const totalBatches = Number(progress.total_batches || 0);
  const rotations = Number(progress.session_rotations || 0);
  const batchText = totalBatches ? ` · batch ${currentBatch}/${totalBatches}` : "";
  const rotationText = rotations ? ` · đã nối phiên ${rotations} lần` : "";
  return `${completed}/${total} beat${batchText}${rotationText}`;
}

function editProgressHtml(progress) {
  if (!progress || !Number(progress.total_beats || 0)) return "";
  const completed = Number(progress.completed_beats || 0);
  const total = Math.max(1, Number(progress.total_beats || 0));
  const percent = Math.max(0, Math.min(100, (completed / total) * 100));
  return `<div class="edit-batch-progress" data-edit-progress><div><span>${escapeHtml(progress.status_message || "Đang chuẩn bị dựng")}</span><strong>${escapeHtml(editProgressText(progress))}</strong></div><div class="edit-batch-progress-track"><i style="width:${percent}%"></i></div></div>`;
}

function renderCacheHtml(cache) {
  if (!cache || !Number(cache.total_chunks || 0)) return "";
  const ready = Number(cache.ready_chunks || 0);
  if (ready <= 0 && cache.status !== "rendering") return "";
  const total = Math.max(1, Number(cache.total_chunks || 0));
  const percent = Math.max(0, Math.min(100, (ready / total) * 100));
  const label = cache.status === "ready" ? "Cache render đã sẵn sàng" : (cache.status_message || "Đang render");
  return `<div class="edit-batch-progress" data-render-cache><div><span>${escapeHtml(label)}</span><strong>${ready}/${total} chunk · ~${Number(cache.chunk_seconds || 180)}s/chunk</strong></div><div class="edit-batch-progress-track"><i style="width:${percent}%"></i></div></div>`;
}

function exportProgressHtml(progress = {}) {
  const percent = Math.max(0, Math.min(100, Number(progress.percent || 0)));
  const percentLabel = (percent > 0 && percent < 100 && !Number.isInteger(percent))
    ? `${percent.toFixed(1)}%`
    : `${Math.round(percent)}%`;
  const stageLabels = {
    waiting: "CHỜ XUẤT",
    preparing: "CHUẨN BỊ",
    rendering: "RENDER 1 LƯỢT",
    combining: "GHÉP VIDEO",
    validating: "KIỂM TRA FILE",
    qc: "QC",
    finalizing: "CHỐT FILE",
    completed: "HOÀN TẤT",
    failed: "CÓ LỖI",
    interrupted: "BỊ NGẮT",
  };
  const stage = stageLabels[String(progress.stage || "waiting")] || String(progress.stage || "ĐANG XỬ LÝ").toUpperCase();
  const chunkText = Number(progress.total_chunks || 0)
    ? `${Number(progress.ready_chunks || 0)}/${Number(progress.total_chunks || 0)} đoạn`
    : "";
  const hwSummary = progress.hardware_profile?.summary || "";
  return `<section class="export-progress-panel ${escapeHtml(progress.status || "pending")}" data-export-progress>
    <div class="export-progress-copy"><span>TIẾN ĐỘ XUẤT VIDEO · ${escapeHtml(stage)}</span><strong>${percentLabel}</strong><p>${escapeHtml(progress.message || "Đang chuẩn bị xuất video.")}</p>${hwSummary ? `<small class="export-hw-badge">⚡ Tự động tối ưu theo máy: ${escapeHtml(hwSummary)}</small>` : ""}</div>
    <div class="export-progress-meter"><div><span style="width:${percent}%"></span></div><small>${percentLabel}${chunkText ? ` · ${escapeHtml(chunkText)}` : ""}</small></div>
  </section>`;
}

function editChatMessagesHtml(history = []) {
  if (!history.length) {
    return `<div class="editor-chat-empty"><strong>Role Edit · Video Editing Specialist</strong><p>Luật sắt Role Edit: Footage lấy từ 3–6s/cut · Bắt buộc xóa/crop sạch 100% logo &amp; chữ Trung của bên khác (cần thiết thì crop hết hình ảnh có nguồn bên khác) · Không lấy video có mặt người dẫn (MC) hoặc chủ kênh khác, chỉ lấy đúng footage cần · Mỗi cảnh Vox độc nhất 100% theo câu voice.</p></div>`;
  }
  return history.map(item => `<div class="editor-chat-message ${item.role === "user" ? "user" : "assistant"}"><span>${item.role === "user" ? "Bạn" : "Codex"}</span>${item.content ? `<p>${escapeHtml(item.content).replace(/\n/g, "<br>")}</p>` : ""}${chatAttachmentGalleryHtml(item.attachments || [])}</div>`).join("");
}

function editChatContextHtml(session) {
  const event = session?.live_edit_event;
  if (!event) return `<span>Context: project hiện tại</span>`;
  const seconds = Number(event.timestamp_sec);
  const time = Number.isFinite(seconds) ? `${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2, "0")}` : "";
  return `<span>Context: ${escapeHtml(event.beat_id || "project")}${time ? ` · ${time}` : ""}</span>`;
}

async function renderEditWorkspace(job) {
  $("#editProjectLabel").textContent = selectedProjectLabel(job);
  const root = $("#editWorkspace");
  if (!job) {
    state.editJobId = null;
    state.editStudioUrl = null;
    root.innerHTML = `<div class="empty-state">Chọn một dự án để mở editor.</div>`;
    return;
  }
  if (!state.editViewMode) {
    state.editViewMode = localStorage.getItem("cofi-edit-view-mode") || "nle";
  }
  const editPhaseRunning = job.phases?.edit?.status === "running";
  const liveEditMtime = state.realtimeLive?.job_id === job.id ? (state.realtimeLive.live_edit_mtime || 0) : 0;
  const editQuickSig = `${job.id}|${state.editViewMode}|${job.phases?.edit?.status || ''}|${job.phases?.edit?.finished_at || ''}|${job.updated_at || ''}|${liveEditMtime}`;
  const nowMs = Date.now();
  if (
    !editPhaseRunning &&
    state.editJobId === job.id &&
    state.lastEditQuickSig === editQuickSig &&
    state.editStudioUrl &&
    root.querySelector("iframe") &&
    state.lastEditStatusPollMs &&
    nowMs - state.lastEditStatusPollMs < 15000
  ) {
    return;
  }
  state.lastEditQuickSig = editQuickSig;
  state.lastEditStatusPollMs = nowMs;
  let session = null;
  try { session = await api(`/api/jobs/${encodeURIComponent(job.id)}/remotion`); } catch (_) {}
  if (
    session &&
    !session.studio_running &&
    state.editViewMode === "studio" &&
    (session.composition_registered === true || job.phases?.edit?.status === "running" || root.querySelector("iframe.remotion-frame")) &&
    (!state.lastAutoStudioStartMs || Date.now() - state.lastAutoStudioStartMs > 15000)
  ) {
    state.lastAutoStudioStartMs = Date.now();
    try {
      session = await api(`/api/jobs/${encodeURIComponent(job.id)}/remotion/start`, { method: "POST" });
    } catch (_) {}
  }
  const compId = session?.composition_id || job.composition_id || `Documentary-${job.id}`;
  const nleUrl = session?.nle_url || `http://127.0.0.1:8891/?jobId=${encodeURIComponent(job.id)}&compId=${encodeURIComponent(compId)}`;
  const studioRunning = Boolean(session?.studio_running && session?.studio_url);
  const editRunning = job.phases?.edit?.status === "running";
  const compositionReady = session?.composition_registered === true;
  const rawStudioUrl = studioRunning
    ? ((compositionReady || editRunning) ? (session.composition_url || session.studio_url) : session.studio_url)
    : null;
  const isNleMode = state.editViewMode !== "studio";
  const running = isNleMode ? (compositionReady || editRunning || studioRunning) : studioRunning;
  const activeFrameUrl = isNleMode ? nleUrl : rawStudioUrl;

  const liveStatus = liveEditStatusText(
    session,
    editRunning
      ? (compositionReady
        ? "Đang dựng · Timeline tự cập nhật trực tiếp"
        : `Đang khởi tạo ${compId}`)
      : (compositionReady
        ? `${compId}`
        : "Composition chưa được dựng"),
  );
  const progressText = editProgressText(session?.edit_progress);
  const runningStatus = `${liveStatus}${progressText ? ` · ${progressText}` : ""}`;
  const liveEventStamp = String(session?.live_edit_event?.updated_at || session?.live_edit_event?.created_at || liveEditMtime || "");
  const editorStateKey = [
    job.status || "",
    job.phases?.edit?.status || "pending",
    job.phases?.edit?.finished_at || "",
    compositionReady ? "composition-ready" : "composition-missing",
    state.editViewMode || "nle",
  ].join("|");
  if (
    running &&
    state.editJobId === job.id &&
    state.editStudioUrl === activeFrameUrl &&
    root.dataset.editorStateKey === editorStateKey &&
    root.querySelector("iframe")
  ) {
    const statusEl = root.querySelector("[data-edit-status]");
    if (statusEl && statusEl.textContent !== runningStatus) {
      statusEl.textContent = runningStatus;
    }
    const progressNode = root.querySelector("[data-edit-progress]");
    const progressMarkup = editRunning ? editProgressHtml(session?.edit_progress) : "";
    if (progressNode) {
      if (progressNode.outerHTML !== progressMarkup) progressNode.outerHTML = progressMarkup;
    } else if (progressMarkup) {
      root.querySelector(".nle-edit-topbar")?.insertAdjacentHTML("afterend", progressMarkup);
    }
    if (liveEventStamp && root.dataset.lastLiveEventStamp !== liveEventStamp) {
      root.dataset.lastLiveEventStamp = liveEventStamp;
      renderSyncComplianceScorecard(job, root);
    }
    return;
  }
  if (state.editAttachmentJobId !== job.id) {
    state.editAttachmentJobId = job.id;
    state.editChatAttachments = [];
  }
  const checkpoint = await artifact(job.id, "edit_checkpoint.json");
  state.editJobId = job.id;
  state.editStudioUrl = activeFrameUrl;
  root.dataset.editorStateKey = editorStateKey;
  const editSucceeded = job.phases?.edit?.status === "succeeded";
  const editStatus = job.phases?.edit?.status || "pending";
  const activePhases = effectivePhases(job);
  const editStep = activePhases.indexOf("edit") + 1;
  const seoStep = activePhases.indexOf("seo") + 1;
  const qcReadyInEdit = job.phases?.qc?.status === "succeeded" || job.status === "succeeded" || job.status === "completed";
  const saveVideoInEditHtml = qcReadyInEdit
    ? `<button type="button" class="primary compact" data-local-save-job="${escapeHtml(job.id)}" data-local-save-path="release/video.mp4" style="background:linear-gradient(135deg,#10b981,#059669);border-color:#34d399;color:#ffffff;font-weight:800;" title="Mở hộp thoại chọn thư mục (cho phép đổi tên) và chuyển thẳng video gốc sang thư mục chọn">💾 Lưu Video (.MP4)</button>`
    : "";
  const editAction = editSucceeded
    ? `${saveVideoInEditHtml}<button class="ghost compact" data-workspace-run-phase="edit" title="Chạy lại bước Edit">↻ Dựng lại</button><button class="primary compact" data-open-step="seo">Tiếp tục →</button>`
    : `${saveVideoInEditHtml}${phaseActionHtml(job, "edit")}`;
  const editError = job.phases?.edit?.error;
  root.innerHTML = `<div class="persistent-editor-shell nle-workbench-shell">
    <div class="editor-toolbar nle-edit-topbar">
      <div class="nle-topbar-left">
        <span class="nle-step-badge">0${editStep} · EDIT</span>
        <span class="nle-status-pill" data-edit-status>${escapeHtml(statusLabels[editStatus] || editStatus)}</span>
        <div class="edit-sync-policy-panel nle-inline-sync" id="editSyncPolicyPanel"></div>
      </div>
      <div class="button-row nle-topbar-right">
        <div class="nle-mode-switch" role="group" aria-label="Chế độ trình phát Edit">
          <button type="button" class="nle-mode-btn ${isNleMode ? "is-active" : ""}" data-edit-view-mode="nle" title="Trình phát CapCut NLE · Khóa 30 FPS + Lăn chuột Zoom Timeline">Timeline</button>
          <button type="button" class="nle-mode-btn ${!isNleMode ? "is-active" : ""}" data-edit-view-mode="studio" title="Mở giao diện Remotion Studio gốc (cổng 8890)">Studio</button>
        </div>
        <button type="button" class="ghost compact" id="openEditCheckpointModalBtn" title="Xem điểm lưu dựng (edit_checkpoint.json) &amp; Render Cache">Checkpoint</button>
        <button type="button" class="ghost compact" id="lockEditDnaBtn" title="Chốt Mẫu Edit Chuẩn Cho Kênh">Chốt mẫu</button>
        ${!isNleMode ? `<button type="button" class="ghost compact" id="startWorkspaceStudioBtn">${studioRunning ? "↻ Tải lại" : "Bật Studio"}</button>` : ""}
        ${editAction}
      </div>
    </div>
    ${editRunning ? editProgressHtml(session?.edit_progress) : ""}
    <div id="cofiVoxBlenderStudioHost" hidden></div>
    ${editError ? `<div class="editor-step-error"><strong>Lỗi Edit</strong><span>${escapeHtml(editError)}</span></div>` : ""}
    <div class="editor-body chat-collapsed nle-editor-body">
      <div class="editor-canvas nle-editor-canvas">${running && activeFrameUrl ? `<iframe class="remotion-frame persistent-frame" src="${escapeHtml(activeFrameUrl)}" title="Cofi NLE Timeline Player" allow="autoplay; fullscreen; clipboard-write"></iframe>` : `<div class="preview-empty"><div>▶</div><h3>Trình dựng chưa bật</h3><p>Bấm "Timeline Mượt 30FPS" hoặc "Bật Studio" để mở bàn dựng thời gian thực.</p></div>`}</div>
    </div>
  </div>`;

  renderSyncComplianceScorecard(job, root);
  if (typeof window.mountCofiVoxBlenderStudio === "function") { window.mountCofiVoxBlenderStudio(job.id, root.querySelector("#cofiVoxBlenderStudioHost")); }

  root.querySelectorAll("[data-edit-view-mode]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const nextMode = btn.getAttribute("data-edit-view-mode") || "nle";
      if (state.editViewMode === nextMode) return;
      state.editViewMode = nextMode;
      localStorage.setItem("cofi-edit-view-mode", nextMode);
      state.editStudioUrl = null;
      state.lastEditQuickSig = null;
      await renderEditWorkspace(job);
    });
  });

  $("#openEditCheckpointModalBtn")?.addEventListener("click", () => {
    const cacheInfo = session?.render_cache ? JSON.stringify(session.render_cache, null, 2) : null;
    const bodyHtml = `
      <div style="display:flex;flex-direction:column;gap:14px;">
        ${session?.render_cache ? `<div><h4 style="margin:0 0 6px;font-size:12px;color:#38bdf8;text-transform:uppercase;">Render Cache &amp; Proxy 30FPS</h4>${renderCacheHtml(session.render_cache)}</div>` : ""}
        <div>
          <h4 style="margin:0 0 6px;font-size:12px;color:#94a3b8;text-transform:uppercase;">Điểm lưu dựng (edit_checkpoint.json)</h4>
          ${checkpoint ? codeViewer("edit_checkpoint.json", checkpoint) : `<div class="checkpoint-empty">Chưa có checkpoint cho dự án này.</div>`}
        </div>
        ${cacheInfo ? `<details class="technical-details"><summary>JSON Render Cache thô</summary>${codeViewer("render_cache.json", cacheInfo)}</details>` : ""}
      </div>
    `;
    openStudioModal({
      badge: "📜",
      title: `Điểm Lưu Dựng & Cache · ${job.title}`,
      subtitle: `Composition: ${compId} · Chế độ: ${isNleMode ? "Timeline Mượt 30FPS (@remotion/player)" : "Remotion Studio Gốc"}`,
      bodyHtml,
    });
  });

  $("#lockEditDnaBtn")?.addEventListener("click", async () => {
    const btn = $("#lockEditDnaBtn");
    btn.disabled = true;
    btn.textContent = "Đang chốt...";
    try {
      const res = await api(`/api/jobs/${encodeURIComponent(job.id)}/lock-edit-dna`, {
        method: "POST",
        body: JSON.stringify({ notes: `Approved edit from project ${job.title}` }),
      });
      toast(`Đã chốt Mẫu Edit chuẩn v${res.version || res.editing_dna?.version || 1} cho kênh ${res.channel_profile_id || res.profile_id}!`);
      btn.textContent = `✓ Đã chốt v${res.version || res.editing_dna?.version || 1}`;
      btn.classList.add("success");
    } catch (err) {
      toast(`Lỗi khi chốt mẫu edit: ${err.message}`, true);
      btn.disabled = false;
      btn.textContent = "🔒 Chốt Mẫu";
    }
  });

  $("#openGlobalChatFromEdit")?.addEventListener("click", async () => {
    state.globalCodexOpen = true;
    localStorage.setItem("cofi-global-chat-open", "1");
    await renderGlobalProducerChat({ loadHistory: true });
    $("#globalCodexInput")?.focus();
  });
  $("#startWorkspaceStudioBtn")?.addEventListener("click", async () => {
    try {
      await api(`/api/jobs/${encodeURIComponent(job.id)}/remotion/start`, { method: "POST" });
      toast("Đã bật Remotion Studio.");
      state.editStudioUrl = null;
      setTimeout(() => renderEditWorkspace(job), 700);
    } catch (err) { toast(err.message, true); }
  });
  bindWorkspacePhaseButtons(job, root);
}

async function renderSyncComplianceScorecard(job, container) {
  const panel = container.querySelector("#editSyncPolicyPanel");
  if (!panel) return;
  try {
    panel.innerHTML = `<span class="nle-sync-pill is-loading">⏳ Kiểm tra đồng bộ...</span>`;
    const data = await api(`/api/jobs/${encodeURIComponent(job.id)}/sync-compliance`);
    const sync = data.sync_scorecard || {};
    const policy = data.policy_scorecard || {};
    const holdsCount = (sync.holds_over_8s || []).length;
    const misalignedCount = (sync.misaligned_beats || []).length;
    const isGreen = policy.green_monetization !== false;
    const isSyncOk = sync.passed !== false;
    const overlayPct = Math.round((policy.editorial_overlay_ratio || 0) * 100);
    const allClean = isGreen && isSyncOk && holdsCount === 0;
    const totalBeats = sync.total_beats || 0;
    const alignedBeats = sync.aligned_beats || totalBeats;

    panel.innerHTML = `
      <div class="nle-sync-compact-wrap">
        <button type="button" class="nle-sync-pill ${allClean ? "is-clean" : "is-warn"}" id="toggleSyncDetailsBtn" title="Bấm để xem chi tiết Kiểm duyệt Đồng bộ Voice/SRT &amp; Kiếm tiền Xanh">
          <span>${allClean ? "✓ Đồng bộ chuẩn" : "⚠ Kiểm tra đồng bộ"}</span>
          <span class="nle-sync-sep">·</span>
          <span>${alignedBeats}/${totalBeats}</span>
          <span style="opacity:0.6;font-size:9px;">▾</span>
        </button>
        ${!isSyncOk || holdsCount > 0 ? `<button type="button" class="nle-repair-mini-btn" id="autoRepairSyncBtn" title="Tự động sửa lệch beat &amp; hold > 8s">Sửa lệch</button>` : ""}
      </div>
    `;

    const openComplianceDialog = () => {
      const dialogHtml = `
        <div style="display:flex;flex-direction:column;gap:14px;">
          <div style="display:flex;flex-wrap:wrap;gap:6px;">
            <span class="sync-chip chip-green">✓ Footage 3–6s · Crop sạch Logo/Chữ Trung · 0% MC/Chủ kênh</span>
            <span class="sync-chip chip-green">✓ Vox Độc Bản 100%</span>
            <span class="sync-chip ${isGreen ? 'chip-green' : 'chip-red'}">${isGreen ? '✓ 100% Green Monetization' : '⚠️ Có từ khóa nhạy cảm'}</span>
            <span class="sync-chip ${isSyncOk ? 'chip-green' : 'chip-amber'}">${isSyncOk ? `✓ Khớp 100% (${alignedBeats}/${totalBeats} beats)` : `⚠️ Lệch ${misalignedCount} beat`}</span>
            <span class="sync-chip ${holdsCount === 0 ? 'chip-green' : 'chip-red'}">${holdsCount === 0 ? '✓ 0 Hold > 6s' : `⚠️ ${holdsCount} hold > 6s`}</span>
            <span class="sync-chip chip-purple">${overlayPct}% Phủ biên tập (${policy.reused_content_risk || 'low'})</span>
          </div>
          <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px;">
            <div style="background: rgba(255,255,255,0.03); padding: 10px 12px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.07);">
              <div style="font-size: 20px; font-weight: 700; color: #38bdf8;">${totalBeats}</div>
              <div style="font-size: 11px; color: var(--text-secondary); text-transform: uppercase;">Tổng số Beat</div>
            </div>
            <div style="background: rgba(255,255,255,0.03); padding: 10px 12px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.07);">
              <div style="font-size: 20px; font-weight: 700; color: ${misalignedCount > 0 ? '#f59e0b' : '#10b981'};">${alignedBeats}</div>
              <div style="font-size: 11px; color: var(--text-secondary); text-transform: uppercase;">Khớp chuẩn timeline</div>
            </div>
            <div style="background: rgba(255,255,255,0.03); padding: 10px 12px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.07);">
              <div style="font-size: 20px; font-weight: 700; color: ${holdsCount > 0 ? '#ef4444' : '#10b981'};">${holdsCount}</div>
              <div style="font-size: 11px; color: var(--text-secondary); text-transform: uppercase;">Ảnh tĩnh hold > 8s</div>
            </div>
            <div style="background: rgba(255,255,255,0.03); padding: 10px 12px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.07);">
              <div style="font-size: 20px; font-weight: 700; color: #a855f7;">${overlayPct}%</div>
              <div style="font-size: 11px; color: var(--text-secondary); text-transform: uppercase;">Phủ biên tập (${policy.reused_content_risk || 'low'})</div>
            </div>
          </div>
          <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid rgba(255,255,255,0.08); padding-top: 10px;">
            <span style="font-size: 12.5px; color: ${isSyncOk && holdsCount === 0 ? '#10b981' : '#f59e0b'};">
              ${isSyncOk && holdsCount === 0 ? '✓ Đạt chuẩn: Tất cả beat khớp thoại và không có ảnh tĩnh đứng hình > 8 giây.' : `⚠️ Cần xử lý: ${holdsCount} beat đứng hình > 8s hoặc ${misalignedCount} beat lệch thoại.`}
            </span>
          </div>
        </div>
      `;
      openStudioModal({
        badge: "⚖️",
        title: "Kiểm Duyệt Đồng Bộ Voice/SRT & Kiếm Tiền Xanh",
        subtitle: `${job.title} · ${alignedBeats}/${totalBeats} beat khớp chuẩn`,
        bodyHtml: dialogHtml,
      });
    };

    panel.querySelector("#toggleSyncDetailsBtn")?.addEventListener("click", openComplianceDialog);

    const runAutoRepair = async (btn) => {
      btn.disabled = true;
      btn.textContent = "Đang sửa...";
      try {
        const res = await api(`/api/jobs/${encodeURIComponent(job.id)}/auto-repair-sync`, { method: "POST" });
        toast(`Đã sửa ${res.realigned_beats_count || 0} beat lệch timeline và bổ sung Ken Burns/HUD cho ${res.repaired_holds_count || 0} đoạn hold > 8s!`);
        await renderSyncComplianceScorecard(job, container);
      } catch (e) {
        toast(e.message, true);
        btn.disabled = false;
        btn.textContent = "⚡ Sửa lệch";
      }
    };

    panel.querySelector("#autoRepairSyncBtn")?.addEventListener("click", (e) => runAutoRepair(e.currentTarget));
  } catch (err) {
    panel.innerHTML = `<span class="nle-sync-pill is-warn" title="${escapeHtml(err.message)}">⚠️ Scorecard</span>`;
  }
}

function seoListHtml(values = []) {
  const items = Array.isArray(values) ? values.map(value => String(value || "").trim()).filter(Boolean) : [];
  return items.length ? `<div class="seo-chip-list">${items.map(value => `<span>${escapeHtml(value)}</span>`).join("")}</div>` : `<span class="muted">Chưa có</span>`;
}

function seoCopyCard(label, key, value, { wide = false, prominent = false } = {}) {
  const content = String(value || "").trim();
  const readerBtnHtml = content.length > 100
    ? (() => {
        const readerKey = registerStudioReaderPayload({
          badge: "🔑",
          title: label,
          subtitle: "Nội dung SEO YouTube · 15 Phòng Ban Chuyên Môn",
          rawText: content,
          isCode: false,
        });
        return `<button type="button" class="ghost compact" data-studio-reader-key="${readerKey}">🗗 Đọc Popup</button>`;
      })()
    : "";
  return `<section class="seo-result-card seo-copy-card${wide ? " wide" : ""}${prominent ? " prominent" : ""}">
    <div class="seo-copy-head"><span>${escapeHtml(label)}</span><div style="display:flex;gap:5px;align-items:center;">${readerBtnHtml}<button type="button" class="ghost compact seo-copy-btn" data-seo-copy="${escapeHtml(key)}">Sao chép</button></div></div>
    <pre class="seo-copy-box">${escapeHtml(content || "Chưa có")}</pre>
  </section>`;
}

async function copySeoText(value) {
  const text = String(value || "");
  if (!text) return;
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
    return;
  }
  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.opacity = "0";
  document.body.appendChild(textarea);
  textarea.select();
  document.execCommand("copy");
  textarea.remove();
}

function bindSeoCopyButtons(root, values) {
  root.querySelectorAll("[data-seo-copy]").forEach(button => button.addEventListener("click", async (e) => {
    e.stopPropagation();
    const key = String(button.dataset.seoCopy || "");
    const value = values[key];
    if (!value) return toast("Mục này chưa có nội dung để sao chép.", true);
    try {
      await copySeoText(value);
      const previous = button.textContent;
      button.textContent = "Đã sao chép";
      toast("Đã sao chép.");
      setTimeout(() => { if (button.isConnected) button.textContent = previous; }, 1200);
    } catch (err) {
      toast("Không sao chép được: " + (err?.message || err), true);
    }
  }));
}

let seoRenderInFlight = false;
async function renderSeoWorkspace(job, { forceRemount = false } = {}) {
  $("#seoProjectLabel").textContent = selectedProjectLabel(job);
  const root = $("#seoWorkspace");
  if (!job) return root.innerHTML = `<div class="empty-state">Chọn một dự án để tạo SEO và prompt thumbnail.</div>`;
  const seoStatus = String(job.phases?.seo?.status || "pending");
  const prevSeoStatus = String(root.dataset.seoStatus || "");
  const justFinishedSeo = ["running", "queued"].includes(prevSeoStatus) && seoStatus === "succeeded";
  const existingHost = root.querySelector("#cofiThumbnailStudioHost");
  const studioAlreadyLoaded = Boolean(
    existingHost
    && existingHost.dataset.mountedJobId === String(job.id)
    && existingHost.children.length > 0
  );
  if (!forceRemount && !justFinishedSeo && studioAlreadyLoaded) {
    if (prevSeoStatus !== seoStatus) {
      const stepCard = root.querySelector(".step-status-card");
      if (stepCard) {
        stepCard.outerHTML = phaseStepPanelHtml(job, "seo", "qc");
        bindWorkspacePhaseButtons(job, root);
      }
      root.dataset.seoStatus = seoStatus;
    }
    return;
  }
  if (seoRenderInFlight) return;
  seoRenderInFlight = true;
  try {
  const [packageRaw, referenceRaw] = await Promise.all([
    artifact(job.id, "seo_package.json"),
    artifact(job.id, "seo_reference_context.json"),
  ]);
  const pack = safeJson(packageRaw, {});
  const reference = safeJson(referenceRaw, {});
  const thumbnail = pack.thumbnail && typeof pack.thumbnail === "object" ? pack.thumbnail : {};
  const channels = Array.isArray(reference.channels) ? reference.channels : [];
  const evidence = Array.isArray(reference.evidence_videos) ? reference.evidence_videos : [];
  const profileLabel = reference.profile_label || "Chưa gắn hồ sơ kênh";
  const preflightSummary = pack.preflight_summary || {};
  const preflightPassed = preflightSummary.passed !== false;
  const preflightRecs = Array.isArray(preflightSummary.recommendations) ? preflightSummary.recommendations : [];
  const preflightMatched = Array.isArray(preflightSummary.winner_patterns_matched) ? preflightSummary.winner_patterns_matched : [];
  const preflightHtml = (packageRaw && Object.keys(preflightSummary).length)
    ? `<section class="seo-result-card wide" style="margin-bottom:12px;border:1px solid rgba(0,200,255,0.3);background:rgba(18,24,36,0.95);border-radius:10px;padding:12px 16px;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
          <span style="font-size:11px;font-weight:800;letter-spacing:0.8px;color:#00c8ff;">✈ CHANNEL-DNA SEO &amp; THUMBNAIL PRE-FLIGHT CHECK</span>
          <span class="dna-pill ${preflightPassed ? 'green' : 'forbid'}" style="font-size:11.5px;">${preflightPassed ? '✓ PASSED (CHUẨN DNA KÊNH)' : '⚠ CẦN TỐI ƯU'}</span>
        </div>
        <div style="font-size:12.5px;color:#cbd5e1;line-height:1.45;">
          ${preflightMatched.length ? `<div><b>Patterns khớp:</b> ${preflightMatched.map(p => `<span style="display:inline-block;padding:2px 8px;border-radius:12px;background:rgba(0,200,255,0.15);border:1px solid rgba(0,200,255,0.3);color:#7dd3fc;font-size:11px;font-weight:600;margin-right:6px;">★ ${escapeHtml(p)}</span>`).join("")}</div>` : ""}
          ${preflightRecs.length ? `<div style="margin-top:6px;padding:6px 10px;border-radius:6px;background:rgba(251,191,36,0.08);border:1px solid rgba(251,191,36,0.25);color:#fbbf24;font-size:12px;"><b>Khuyến nghị Pre-Flight:</b><ul style="margin:2px 0 0;padding-left:16px;">${preflightRecs.map(r => `<li>${escapeHtml(r)}</li>`).join("")}</ul></div>` : `<div style="color:#10b981;margin-top:4px;">✓ SEO Tags &amp; Thumbnail Overlay đạt chuẩn DNA Kênh!</div>`}
        </div>
      </section>`
    : "";
  const referenceSummary = packageRaw
    ? `<section class="seo-reference-summary"><div><span>HỒ SƠ THAM CHIẾU</span><strong>${escapeHtml(profileLabel)}</strong><small>${channels.length} kênh · ${evidence.length} video bằng chứng · ${escapeHtml(reference.source_mode || "job_only")}</small></div></section>`
    : "";
  const hashtags = Array.isArray(pack.hashtags) ? pack.hashtags.map(value => String(value || "").trim()).filter(Boolean) : [];
  const tags = Array.isArray(pack.tags) ? pack.tags.map(value => String(value || "").trim()).filter(Boolean) : [];
  const keywords = Array.isArray(pack.keywords) ? pack.keywords.map(value => String(value || "").trim()).filter(Boolean) : [];
  const descriptionWithHashtags = [String(pack.description || "").trim(), hashtags.join(" ")].filter(Boolean).join("\n\n");
  const videoTags = tags.join(", ");
  const keywordText = keywords.join(", ");
  const overlayText = String(thumbnail.overlay_text || "").trim();
  let thumbnailPrompt = String(thumbnail.prompt || "").trim();
  if (overlayText && !thumbnailPrompt.toLowerCase().includes(overlayText.toLowerCase())) {
    thumbnailPrompt = `${thumbnailPrompt}\n\nTEXT ON THUMBNAIL: Render exactly “${overlayText}” as part of the final image. Use large mobile-readable uppercase serif typography, strong contrast, clean spacing, and keep the text inside safe margins.`.trim();
  }
  const overlayOptions = Array.isArray(thumbnail.overlay_text_options) ? thumbnail.overlay_text_options : [];
  const channelFramework = pack.channel_framework && typeof pack.channel_framework === "object" ? pack.channel_framework : null;
  const splitBilingualTitle = (rawTitle, explicitVi = "") => {
    let raw = String(rawTitle || "").trim().replace(/^(?:🇰🇷\s*)?(?:KR\s+)+/i, "").trim();
    let vi = String(explicitVi || "").trim();
    const viRegex = /[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]/i;
    const parenMatch = raw.match(/^(.*?)\s*\(([^()]+)\)\s*$/);
    if (parenMatch && viRegex.test(parenMatch[2])) {
      raw = parenMatch[1].trim();
      if (!vi) {
        vi = parenMatch[2].replace(/^(?:🇻🇳\s*)?(?:VN|VI|Tiếng Việt|Nghĩa(?:\s+Tiếng\s+Việt)?)\s*[:\-–—]?\s*/i, "").trim();
      }
    }
    const splitLines = raw.split(/\n+|\s+\/\/\s+/);
    if (splitLines.length >= 2 && viRegex.test(splitLines[splitLines.length - 1]) && !/[가-힣]/.test(splitLines[splitLines.length - 1])) {
      if (!vi) {
        vi = splitLines[splitLines.length - 1].replace(/^(?:🇻🇳\s*)?(?:VN|VI|Tiếng Việt|Nghĩa(?:\s+Tiếng\s+Việt)?)\s*[:\-–—]?\s*/i, "").trim();
      }
      raw = splitLines.slice(0, -1).join(" ").trim();
    }
    return { ko: raw, vi };
  };
  const titleOptionsDetails = Array.isArray(pack.title_options_details) ? pack.title_options_details : [];
  const titleOptionsVi = Array.isArray(pack.title_options_vi) ? pack.title_options_vi : [];
  const titlesViFallback = Array.isArray(pack.titles_vi) ? pack.titles_vi : [];
  const titleVariantsList = Array.isArray(pack.title_variants) ? pack.title_variants : [];
  const abVariantsList = Array.isArray(pack.ab_variants) ? pack.ab_variants : [];
  const titleThumbPairs = Array.isArray(pack.title_thumbnail_pairs) ? pack.title_thumbnail_pairs : [];
  const rawTitleOptionsSource = (pack.title_options || []).length
    ? [...pack.title_options]
    : (titleVariantsList.length ? [...titleVariantsList] : [...titleOptionsDetails]);
  if (rawTitleOptionsSource.length < 8) {
    const seenKo = new Set(
      rawTitleOptionsSource.map((item) => {
        const s = typeof item === "object" && item !== null ? String(item.title_ko || item.kr || item.title || "") : String(item || "");
        return splitBilingualTitle(s).ko;
      }).filter(Boolean)
    );
    for (const ex of [...titleVariantsList, ...abVariantsList, ...titleOptionsDetails, ...titleThumbPairs]) {
      if (rawTitleOptionsSource.length >= 8) break;
      if (!ex || typeof ex !== "object") continue;
      const exKo = splitBilingualTitle(ex.title_ko || ex.kr || ex.title || ex.paired_title || "").ko;
      if (exKo && !seenKo.has(exKo)) {
        seenKo.add(exKo);
        rawTitleOptionsSource.push(ex);
      }
    }
  }
  const normalizedTitleOptions = rawTitleOptionsSource.map((opt, idx) => {
    const detailObj = (typeof opt === "object" && opt !== null) ? opt : (titleOptionsDetails[idx] || titleVariantsList[idx] || abVariantsList[idx] || {});
    const rawKo = typeof opt === "object" && opt !== null ? String(opt.title_ko || opt.kr || opt.title || opt.paired_title || "").trim() : String(opt || "").trim();
    const explicitVi = String(
      detailObj.title_vi
      || detailObj.vi
      || titleOptionsVi[idx]
      || titlesViFallback[idx]
      || titleVariantsList[idx]?.title_vi
      || titleVariantsList[idx]?.vi
      || abVariantsList[idx]?.title_vi
      || abVariantsList[idx]?.vi
      || titleThumbPairs[idx]?.title_vi
      || titleThumbPairs[idx]?.paired_title_vi
      || overlayOptions[idx]?.paired_title_vi
      || ""
    ).trim();
    const { ko: koTitle, vi: viTitle } = splitBilingualTitle(rawKo, explicitVi);
    const pairedVar = String(detailObj.paired_variant || `BẢN ${["A", "B", "C", "D"][idx % 4]}`).trim();
    const synergyNote = String(detailObj.synergy_vi || "").trim();
    const kwAnchor = String(detailObj.keyword_anchor || detailObj.keyword_anchor_vi || "").trim();
    return { idx, koTitle, viTitle, pairedVar, synergyNote, kwAnchor };
  });
  const splitRecTitle = splitBilingualTitle(
    pack.recommended_title || normalizedTitleOptions[0]?.koTitle || "",
    pack.recommended_title_vi || pack.title_vi || normalizedTitleOptions[0]?.viTitle || titleOptionsVi[0] || titlesViFallback[0] || ""
  );
  const recommendedTitleVi = splitRecTitle.vi;
  const rawPrimaryKw = pack.primary_keywords_summary;
  const primaryKeywordsSummary = (rawPrimaryKw && typeof rawPrimaryKw === "object")
    ? Object.values(rawPrimaryKw).map((v) => String(v || "").trim()).filter(Boolean).join(" · ")
    : String(rawPrimaryKw || "").trim();
  const titleThumbSynergyVi = String(pack.title_thumb_synergy_vi || "").trim();
  const descriptionViText = String(pack.description_vi || "").trim();
  const chaptersList = Array.isArray(pack.chapters) ? pack.chapters : [];
  const chaptersViList = Array.isArray(pack.chapters_vi) ? pack.chapters_vi : [];
  const copyValues = {
    title: splitRecTitle.ko,
    description: descriptionWithHashtags,
    tags: videoTags,
    keywords: keywordText,
    overlay_text: overlayText,
    thumbnail_prompt: thumbnailPrompt,
    negative_prompt: String(thumbnail.negative_prompt || "").trim(),
  };
  normalizedTitleOptions.forEach((optObj, idx) => {
    copyValues[`title_opt_${idx}`] = optObj.koTitle;
  });
  overlayOptions.forEach((opt, idx) => {
    const badge = String(opt.badge || "").trim();
    const l1 = String(opt.line_1 || "").trim();
    const l2 = String(opt.line_2 || "").trim();
    copyValues[`thumb_text_opt_${idx}`] = [badge ? `[${badge}]` : "", l1, l2].filter(Boolean).join("\n");
  });
  const recommendedTitleMetaHtml = (recommendedTitleVi || primaryKeywordsSummary || titleThumbSynergyVi)
    ? `<div style="margin-top:10px;padding:10px 12px;background:rgba(15,23,42,0.92);border:1px solid rgba(34,197,94,0.4);border-radius:8px;display:flex;flex-direction:column;gap:6px;font-size:13px;line-height:1.5;">
        ${recommendedTitleVi ? `<div><span style="display:inline-block;padding:1px 6px;margin-right:6px;border-radius:4px;background:rgba(34,197,94,0.25);color:#4ade80;font-size:11px;font-weight:800;">VN</span><span style="color:#4ade80;font-weight:800;">🇻🇳 Nghĩa Tiếng Việt:</span> <span style="color:#f8fafc;font-weight:700;">${escapeHtml(recommendedTitleVi)}</span></div>` : ""}
        ${primaryKeywordsSummary ? `<div><span style="color:#38bdf8;font-weight:800;">🔑 Từ khóa chính &amp; Địa điểm Trung Quốc:</span> <span style="color:#e2e8f0;">${escapeHtml(primaryKeywordsSummary)}</span></div>` : ""}
        ${titleThumbSynergyVi ? `<div><span style="color:#fbbf24;font-weight:800;">🔗 Hỗ trợ nghĩa với Text Thumbnail:</span> <span style="color:#cbd5e1;">${escapeHtml(titleThumbSynergyVi)}</span></div>` : ""}
      </div>`
    : "";
  const recommendedTitleCardHtml = `<section class="seo-result-card seo-copy-card prominent">
    <div class="seo-copy-head"><span>TIÊU ĐỀ YOUTUBE ĐỀ XUẤT (CHUẨN CTR &amp; DNA KÊNH — SONG NGỮ HÀN · VIỆT)</span><button type="button" class="ghost compact seo-copy-btn" data-seo-copy="title">Sao chép</button></div>
    <pre class="seo-copy-box">🇰🇷 KR ${escapeHtml(copyValues.title || "Chưa có")}</pre>
    ${recommendedTitleMetaHtml}
  </section>`;
  const titleOptionsHtml = normalizedTitleOptions.length
    ? `<div class="seo-options-stack" style="display:flex;flex-direction:column;gap:10px;margin-top:8px;">${normalizedTitleOptions.map((item) => {
        const { idx, koTitle, viTitle, pairedVar, synergyNote, kwAnchor } = item;
        return `<div style="display:flex;flex-direction:column;gap:6px;padding:10px 12px;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.1);border-radius:8px;">
          <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:12px;">
            <div style="font-size:13.5px;line-height:1.45;color:#f8fafc;font-weight:700;">
              <b style="color:#38bdf8;">#${idx + 1}.</b> ${pairedVar ? `<span style="display:inline-block;padding:1px 7px;margin-right:6px;border-radius:4px;background:rgba(251,191,36,0.18);border:1px solid rgba(251,191,36,0.4);color:#fde047;font-size:11px;font-weight:800;">${escapeHtml(pairedVar)}</span>` : ""}<span style="display:inline-block;padding:1px 5px;margin-right:5px;border-radius:3px;background:rgba(56,189,248,0.2);color:#7dd3fc;font-size:10.5px;font-weight:800;">KR</span> 🇰🇷 ${escapeHtml(koTitle)}
            </div>
            <button type="button" class="ghost compact seo-copy-btn" data-seo-copy="title_opt_${idx}" style="flex-shrink:0;">Sao chép</button>
          </div>
          ${viTitle ? `<div style="font-size:12.5px;line-height:1.45;color:#4ade80;padding:5px 8px;background:rgba(34,197,94,0.12);border-left:3px solid #22c55e;border-radius:4px;"><span style="display:inline-block;padding:1px 5px;margin-right:5px;border-radius:3px;background:rgba(34,197,94,0.25);color:#4ade80;font-size:10.5px;font-weight:800;">VN</span> <b>🇻🇳 Nghĩa Tiếng Việt:</b> <span style="color:#f1f5f9;font-weight:600;">${escapeHtml(viTitle)}</span></div>` : ""}
          ${kwAnchor ? `<div style="font-size:11.5px;color:#7dd3fc;padding-left:6px;"><b>📍 Từ khóa &amp; Địa điểm TQ:</b> ${escapeHtml(kwAnchor)}</div>` : ""}
          ${synergyNote ? `<div style="font-size:11.5px;color:#cbd5e1;padding-left:6px;"><b>🔗 Bổ trợ nghĩa với Thumb:</b> ${escapeHtml(synergyNote)}</div>` : ""}
        </div>`;
      }).join("")}</div>`
    : `<span class="muted">Chưa có</span>`;
  const chaptersViHtml = (chaptersList.length || chaptersViList.length)
    ? `<div style="margin-top:10px;padding:10px 12px;background:rgba(15,23,42,0.92);border:1px solid rgba(56,189,248,0.32);border-radius:8px;">
        <div style="font-size:12px;font-weight:800;color:#38bdf8;margin-bottom:6px;">⏱️ TIMESTAMPS CÁC CHƯƠNG SONG NGỮ (HÀN — VIỆT):</div>
        <div style="display:flex;flex-direction:column;gap:5px;">
          ${Array.from({ length: Math.max(chaptersList.length, chaptersViList.length) }).map((_, i) => {
            const ch = chaptersList[i] || {};
            const chVi = chaptersViList[i] || {};
            const ts = String(ch.timestamp || chVi.timestamp || "00:00").trim();
            const koT = String(ch.title_ko || ch.title || chVi.title_ko || "").trim();
            const viT = String(ch.title_vi || chVi.title_vi || (typeof chVi === "string" ? chVi : chVi.title) || "").trim();
            return `<div style="font-size:12.5px;line-height:1.45;padding:5px 8px;background:rgba(9,14,26,0.75);border-radius:5px;">
              <div><b style="color:#38bdf8;font-family:monospace;">${escapeHtml(ts)}</b> · 🇰🇷 ${escapeHtml(koT)}</div>
              ${viT && viT !== koT ? `<div style="color:#4ade80;margin-top:2px;">🇻🇳 <b>Nghĩa:</b> <span style="color:#f8fafc;">${escapeHtml(viT)}</span></div>` : ""}
            </div>`;
          }).join("")}
        </div>
      </div>`
    : "";
  const descriptionViBlockHtml = (descriptionViText || chaptersViHtml)
    ? `<div style="margin-top:10px;padding:10px 12px;background:rgba(15,23,42,0.94);border:1px solid rgba(34,197,94,0.4);border-radius:8px;">
        ${descriptionViText ? `<div style="color:#4ade80;font-weight:800;font-size:12.5px;margin-bottom:6px;">🇻🇳 BẢN DỊCH NGHĨA TIẾNG VIỆT (MÔ TẢ &amp; TIMESTAMPS ĐỂ ĐỌC DUYỆT):</div><pre style="white-space:pre-wrap;margin:0;font-family:inherit;color:#f8fafc;font-size:13px;line-height:1.55;">${escapeHtml(descriptionViText)}</pre>` : ""}
        ${chaptersViHtml}
      </div>`
    : "";
  const overlayOptionsHtml = overlayOptions.length
    ? `<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:10px;margin-top:10px;">${overlayOptions.map((opt, idx) => `<div style="padding:10px 12px;background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.1);border-radius:8px;display:flex;flex-direction:column;justify-content:space-between;gap:8px;"><div><div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;"><span style="background:rgba(34,197,94,0.18);border:1px solid rgba(34,197,94,0.45);color:#4ade80;font-weight:800;font-size:11.5px;padding:2px 8px;border-radius:4px;">🏷 ${escapeHtml(opt.badge || "중국 인프라")}</span><button type="button" class="ghost compact seo-copy-btn" data-seo-copy="thumb_text_opt_${idx}">Sao chép</button></div><div style="font-size:15px;font-weight:800;color:#fde047;line-height:1.3;">${escapeHtml(opt.line_1 || "")}</div><div style="font-size:16px;font-weight:900;color:#f87171;line-height:1.3;">${escapeHtml(opt.line_2 || "")}</div></div>${(opt.line_1_vi || opt.line_2_vi || opt.meaning_vi) ? `<small style="color:#e2e8f0;font-size:12px;line-height:1.4;border-top:1px solid rgba(255,255,255,0.08);padding-top:6px;">🇻🇳 ${escapeHtml([opt.badge_vi ? `[${opt.badge_vi}]` : "", opt.line_1_vi, opt.line_2_vi].filter(Boolean).join(" / ") || opt.meaning_vi || "")}</small>` : ""}${opt.paired_title ? `<small style="color:#93c5fd;font-size:11.5px;line-height:1.35;">🎬 <b>Tiêu đề ghép:</b> ${escapeHtml(opt.paired_title)}<br/><span style="color:#cbd5e1;">🇻🇳 ${escapeHtml(opt.paired_title_vi || "")}</span></small>` : ""}</div>`).join("")}</div>`
    : "";
  const frameworkHtml = channelFramework
    ? `<section class="seo-result-card wide" style="border-color:rgba(251,191,36,0.35);background:rgba(251,191,36,0.04);">
        <span>BỘ KHUNG SEO CHUẨN CỦA KÊNH (${escapeHtml(channelFramework.series_key || "중국 실화 사건")})</span>
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:10px;margin-top:8px;font-size:13px;line-height:1.5;">
          <div><b>Từ khóa Trụ cột (Core Key):</b><br/>${escapeHtml(channelFramework.core_keywords_rule || "")}</div>
          <div><b>Công thức Tiêu đề chuẩn:</b><br/>${escapeHtml(channelFramework.title_formula || "")}</div>
          <div><b>Công thức Text Thumbnail chuẩn:</b><br/>${escapeHtml(channelFramework.thumb_text_formula || "")}</div>
        </div>
      </section>`
    : "";
  const result = packageRaw ? `<div class="seo-clean-hub">
      <div class="seo-clean-col">
        ${recommendedTitleCardHtml}
        ${normalizedTitleOptions.length ? `<section class="seo-result-card"><span>8 PHƯƠNG ÁN TIÊU ĐỀ &amp; CẶP GHÉP THUMBNAIL (SONG NGỮ HÀN - VIỆT)</span>${titleOptionsHtml}</section>` : ""}
        <section class="seo-result-card seo-copy-card">
          <div class="seo-copy-head"><span>MÔ TẢ YOUTUBE + HASHTAGS · TIMESTAMPS &amp; BẢN DỊCH TIẾNG VIỆT</span><button type="button" class="ghost compact seo-copy-btn" data-seo-copy="description">Sao chép</button></div>
          <pre class="seo-copy-box">${escapeHtml(copyValues.description || "Chưa có")}</pre>
          ${descriptionViBlockHtml}
        </section>
      </div>
      <div class="seo-clean-col">
        ${seoCopyCard("VIDEO TAGS · DÁN THẲNG VÀO YOUTUBE STUDIO", "tags", copyValues.tags)}
        ${seoCopyCard("TỪ KHÓA SEO TRỤ CỘT", "keywords", copyValues.keywords)}
        ${overlayOptionsHtml ? `<section class="seo-result-card"><span>CÁC CÂU HOOK CHỮ TRÊN THUMBNAIL (SAO CHÉP NHANH)</span>${overlayOptionsHtml}</section>` : ""}
      </div>
    </div>
    <details class="technical-details">
      <summary>Chi tiết Công thức Kênh, Prompt gốc &amp; Dữ liệu SEO</summary>
      <div class="seo-result-grid" style="margin-top:10px;">
        ${frameworkHtml}
        ${seoCopyCard("PROMPT VẼ THUMBNAIL + TEXT", "thumbnail_prompt", copyValues.thumbnail_prompt, { wide: true })}
        ${copyValues.negative_prompt ? seoCopyCard("NEGATIVE PROMPT", "negative_prompt", copyValues.negative_prompt, { wide: true }) : ""}
      </div>
      <div class="artifact-grid two-col" style="margin-top:10px;">${codeViewer("SEO package", packageRaw)}${codeViewer("Reference context", referenceRaw)}</div>
    </details>` : `<div class="empty-state">Chưa có gói SEO. Bạn vẫn có thể thiết kế &amp; tải 4 bản Thumbnail bên trên, hoặc bấm <b>Thực hiện bước này</b> để AI tạo trọn bộ Tiêu đề, Mô tả, Tags và Hook Thumbnail.</div>`;
  const hasUnifiedThumbStudio = typeof window.mountCofiThumbnailStudio === "function";
  const accordionsHtml = hasUnifiedThumbStudio
    ? (packageRaw
        ? `<details class="technical-details" id="seoTechDetails"><summary>Chi tiết kỹ thuật · JSON gói SEO &amp; Hồ sơ tham chiếu</summary><div class="artifact-grid two-col" id="seoTechGrid"><p style="grid-column: 1 / -1; color: #6a889f; padding: 10px 12px; margin: 0; font-size: 11.5px;">Nhấn mở để nạp tệp JSON kỹ thuật...</p></div></details>`
        : "")
    : `<div class="saas-seo-accordions-group seo-subtab-content" id="seoSubtabCopyPane">${preflightHtml}${referenceSummary}${result}</div>`;

  root.innerHTML = `${phaseStepPanelHtml(job, "seo", "qc")}
    <div class="seo-subtab-content" id="seoSubtabThumbPane">
      <section id="cofiThumbnailStudioHost" class="thumb-studio-host" data-mounted-job-id="${escapeHtml(job.id)}"></section>
    </div>
    ${accordionsHtml}`;
  root.dataset.seoJobId = String(job.id);
  root.dataset.seoStatus = seoStatus;
  bindWorkspacePhaseButtons(job, root);
  if (packageRaw && !hasUnifiedThumbStudio) bindSeoCopyButtons(root, copyValues);

  const seoTech = root.querySelector("#seoTechDetails");
  if (seoTech) {
    seoTech.addEventListener("toggle", () => {
      if (seoTech.open) {
        const grid = seoTech.querySelector("#seoTechGrid");
        if (grid && !grid.dataset.loaded) {
          grid.dataset.loaded = "true";
          grid.innerHTML = `${codeViewer("SEO package (seo_package.json)", packageRaw)}${codeViewer("Reference context (seo_reference_context.json)", referenceRaw)}`;
        }
      }
    });
  }

  const studioHost = root.querySelector("#cofiThumbnailStudioHost");
  if (studioHost && typeof window.mountCofiThumbnailStudio === "function") {
    studioHost.dataset.mountedJobId = String(job.id);
    await window.mountCofiThumbnailStudio(job.id, studioHost, { force: justFinishedSeo || forceRemount });
  }
  } finally {
    seoRenderInFlight = false;
  }
}

let qcRenderInFlight = false;
async function renderQcWorkspace(job) {
  $("#qcProjectLabel").textContent = selectedProjectLabel(job);
  const root = $("#qcWorkspace");
  if (!job) return root.innerHTML = `<div class="empty-state">Chọn một dự án để duyệt và xuất video.</div>`;
  if (qcRenderInFlight) return;
  qcRenderInFlight = true;
  try {
    const qcStatus = job.phases?.qc?.status || "pending";
    const existingProgressNode = root.querySelector("[data-export-progress]");
    if (
      existingProgressNode &&
      root.dataset.qcJobId === job.id &&
      root.dataset.qcStatus === qcStatus &&
      ["running", "queued"].includes(qcStatus)
    ) {
      const exportProgress = await api(`/api/jobs/${encodeURIComponent(job.id)}/export-progress`).catch(() => null);
      if (exportProgress) {
        const node = root.querySelector("[data-export-progress]");
        if (node) node.outerHTML = exportProgressHtml(exportProgress);
      }
      return;
    }
    const [finalRaw, renderRaw, directorRaw, cacheRaw, exportProgress] = await Promise.all([
      artifact(job.id, "final_manifest.json"), artifact(job.id, "render_manifest.json"), artifact(job.id, "director_report.md"), artifact(job.id, "render_cache_manifest.json"),
      api(`/api/jobs/${encodeURIComponent(job.id)}/export-progress`).catch(() => ({ status: qcStatus, percent: 0, stage: "waiting", message: "Chưa có dữ liệu tiến độ xuất video." }))
    ]);
    const finalManifest = safeJson(finalRaw, {});
    const renderManifest = safeJson(renderRaw, {});
    const renderCache = safeJson(cacheRaw, {});
    const videoPath = finalManifest.video_path || finalManifest.output_path || finalManifest.rendered_video || renderManifest.video_path || renderManifest.output_path || "";
    const videoRevision = finalManifest.sha256 || finalManifest.created_at || renderManifest.cache_signature || renderManifest.created_at || "";
    const videoUrl = videoPath ? `${mediaUrl(job.id, videoPath)}${videoRevision ? `&v=${encodeURIComponent(videoRevision)}` : ""}` : "";
    const rawVideoBase = videoPath ? videoPath.split(/[\\/]/).pop() : "";
    const videoExtMatch = rawVideoBase.match(/\.[a-z0-9]+$/i);
    const videoExt = videoExtMatch ? videoExtMatch[0].toLowerCase() : ".mp4";
    const videoDownloadName = rawVideoBase && rawVideoBase.toLowerCase() !== "video.mp4"
      ? (videoExtMatch ? rawVideoBase : `${rawVideoBase}.mp4`)
      : `video_${job.id}${videoExt}`;
    const videoDownloadUrl = videoUrl ? `${videoUrl}&download=1&filename=${encodeURIComponent(videoDownloadName)}` : "";
    const cacheReady = Number(renderCache.ready_chunks || 0);
    const cacheTotal = Number(renderCache.total_chunks || 0);
    const hwSummary = exportProgress?.hardware_profile?.summary || renderCache?.hardware_profile?.summary || "";
    const cacheText = cacheReady > 0 && cacheTotal > 0
      ? `${cacheReady}/${cacheTotal} đoạn đã kết xuất sẵn`
      : `Chế độ Render 1 lượt khi Xuất video${hwSummary ? ` (${hwSummary})` : ""} — không render ngầm khi đang Edit để máy nhẹ và sửa nhanh`;
    const existingVideo = root.querySelector("video.final-video");
    if (
      existingVideo &&
      root.dataset.qcJobId === job.id &&
      root.dataset.qcVideoUrl === videoUrl &&
      root.dataset.qcStatus === qcStatus
    ) {
      const progressNode = root.querySelector("[data-export-progress]");
      const progressMarkup = exportProgressHtml(exportProgress);
      if (progressNode) progressNode.outerHTML = progressMarkup;
      return;
    }
    root.innerHTML = `${phaseStepPanelHtml(job, "qc")}
      ${exportProgressHtml(exportProgress)}
      <section class="final-output-card ${escapeHtml(qcStatus)}">
        <div class="final-output-head" style="flex-wrap:wrap;gap:12px;">
          <div style="flex:1;min-width:280px;">
            <span>BẢN XUẤT CUỐI (LƯU TRỰC TIẾP TRÊN Ổ CỨNG MÁY BẠN)</span>
            <strong>${videoPath ? escapeHtml(videoPath.split(/[\\/]/).pop()) : "Chưa xuất video cuối"}</strong>
            <small>${videoPath ? `📍 File gốc đã nằm sẵn trên ổ cứng (không cần tải từ Cloud): <code style="user-select:all;color:#38bdf8;background:rgba(15,23,42,0.85);padding:2px 6px;border-radius:4px;">${escapeHtml(videoPath)}</code>` : `${cacheText}. Khi bấm Thực hiện bước này, hệ thống mới dồn toàn lực CPU/GPU render 1 lượt duy nhất.`}</small>
          </div>
          ${videoPath ? `<div style="display:flex;flex-wrap:wrap;gap:8px;align-items:center;">
            <button type="button" class="primary compact" data-local-save-job="${escapeHtml(job.id)}" data-local-save-path="${escapeHtml(videoPath)}" style="background:linear-gradient(135deg,#10b981,#059669);border-color:#34d399;color:#ffffff;font-weight:800;" title="Mở hộp thoại chọn thư mục (cho phép đổi tên) và chuyển thẳng video gốc sang thư mục chọn">💾 Lưu Video (.MP4)</button>
          </div>` : ""}
        </div>
        ${videoUrl ? `<video class="final-video" controls controlslist="nodownload" preload="metadata" playsinline src="${escapeHtml(videoUrl)}"></video>` : `<div class="preview-empty"><div>⇩</div><h3>${["running", "queued"].includes(qcStatus) ? "Đang Render 1 lượt (chống đơ máy)" : "Sẵn sàng Render 1 lượt duy nhất"}</h3><p>${escapeHtml(cacheText)}. Bạn có thể chỉnh sửa thoải mái ở bước Edit bằng Remotion Live Preview mà không tốn tài nguyên máy, sau đó bấm Xuất video để render 1 lần.</p></div>`}
      </section>
      ${directorRaw ? (() => {
        const qcReaderKey = registerStudioReaderPayload({
          badge: "🎬",
          title: "BÁO CÁO KIỂM TRA KỸ THUẬT (DIRECTOR QC)",
          subtitle: job.title || job.id,
          rawText: String(directorRaw),
          isCode: false,
        });
        return `<section class="director-report"><div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;"><span>BÁO CÁO KIỂM TRA KỸ THUẬT</span><button type="button" class="ghost compact" data-studio-reader-key="${qcReaderKey}">🗗 Đọc Popup</button></div><pre>${escapeHtml(directorRaw)}</pre></section>`;
      })() : ""}
      <details class="technical-details"><summary>Chi tiết kỹ thuật · manifest xuất video</summary><div class="artifact-grid two-col">${codeViewer("Final manifest", finalRaw)}${codeViewer("Render manifest", renderRaw)}</div></details>`;
    root.dataset.qcJobId = job.id;
    root.dataset.qcVideoUrl = videoUrl;
    root.dataset.qcStatus = qcStatus;
    bindWorkspacePhaseButtons(job, root);
  } finally {
    qcRenderInFlight = false;
  }
}

async function renderFunctionWorkspaces() {
  let job = null;
  if (state.selectedId) {
    try { job = await api(`/api/jobs/${encodeURIComponent(state.selectedId)}`); } catch (_) {}
  }
  const tabPhase = { script: "plan", voice: "voice", visuals: "visuals", footage: "footage", ai_visual: "ai_visual", edit: "edit", seo: "seo", qc: "qc" }[state.appTab];
  if (job && tabPhase && state.appTab !== "edit") {
    const phase = job.phases?.[tabPhase] || {};
    const seoHostEl = state.appTab === "seo" ? document.querySelector("#cofiThumbnailStudioHost") : null;
    const seoAlreadyMounted = Boolean(
      seoHostEl
      && seoHostEl.dataset.mountedJobId === String(job.id)
      && seoHostEl.children.length > 0
    );
    const extra = state.appTab === "voice"
      ? `${JSON.stringify(job.voice || {})}|${Boolean(state.health?.cofi_voice?.ok)}`
      : "";
    const liveMtime = (state.appTab !== "seo" && state.realtimeLive?.job_id === job.id)
      ? JSON.stringify(state.realtimeLive)
      : "";
    const key = state.appTab === "seo"
      ? `${job.id}|${phase.status || "pending"}|${phase.started_at || ""}|${phase.finished_at || ""}`
      : `${job.id}|${phase.status || "pending"}|${phase.started_at || ""}|${phase.finished_at || ""}|${phase.last_message || ""}|${phase.error || ""}|${job.updated_at || ""}|${extra}|${liveMtime}`;
    const seoStudioEmpty = state.appTab === "seo" && !seoAlreadyMounted;
    const needsLiveRefresh = (["running", "queued"].includes(phase.status) && !["ai_visual", "seo"].includes(state.appTab)) || seoStudioEmpty;
    if (!needsLiveRefresh && state.workspaceRenderKeys[state.appTab] === key) return;
    state.workspaceRenderKeys[state.appTab] = key;
  }
  if (state.appTab === "script") return renderScriptWorkspace(job);
  if (state.appTab === "voice") return renderVoiceWorkspace(job);
  if (state.appTab === "visuals") return renderVisualsWorkspace(job);
  if (state.appTab === "footage") return renderFootageWorkspace(job);
  if (state.appTab === "ai_visual") return renderAIVisualWorkspace(job);
  if (state.appTab === "edit") return renderEditWorkspace(job);
  if (state.appTab === "seo") return renderSeoWorkspace(job);
  if (state.appTab === "qc") return renderQcWorkspace(job);
}

async function renderTab(job) {
  if (state.detailTab === "tongquan") {
    const next = effectivePhases(job).find(p => job.phases?.[p]?.status !== "succeeded");
    const currentPhaseInfo = job.phases?.[job.current_phase] || {};
    const isPaused = Boolean(job.is_paused || currentPhaseInfo.is_paused);
    const pauseWarning = job.pause_warning || currentPhaseInfo.pause_warning || "";
    const lastError = job.last_error || currentPhaseInfo.last_error || currentPhaseInfo.error || "";

    let statusCardHtml = "";
    if (isPaused) {
      statusCardHtml = `<div class="overview-card wide warn" style="border-color: rgba(245, 158, 11, 0.45); background: rgba(245, 158, 11, 0.08);">
        <span style="color: #f59e0b; font-weight: 800;">⚠️ TRẠNG THÁI VẬN HÀNH: TẠM DỪNG (${phaseLabels[job.current_phase] || job.current_phase || "AI Visual"})</span>
        <strong style="color: #ffc96b; margin-top: 6px; font-size: 15px;">${escapeHtml(pauseWarning || "Hàng đợi đang tạm dừng")}</strong>
        <small style="color: #cbd5e1; margin-top: 4px; font-size: 13px;">${escapeHtml(lastError ? `Chi tiết lỗi: ${lastError}` : "Cần can thiệp tài khoản hoặc khởi động lại hàng đợi để tiếp tục.")}</small>
      </div>`;
    } else if (lastError && (job.status === "interrupted" || job.status === "failed" || currentPhaseInfo.status === "failed" || currentPhaseInfo.status === "interrupted")) {
      statusCardHtml = `<div class="overview-card wide error" style="border-color: rgba(239, 68, 68, 0.45); background: rgba(239, 68, 68, 0.08);">
        <span style="color: #ef4444; font-weight: 800;">❌ CHI TIẾT LỖI (${phaseLabels[job.current_phase] || job.current_phase || "Hiện tại"})</span>
        <strong style="color: #fca5a5; margin-top: 6px; font-size: 15px; word-break: break-word;">${escapeHtml(lastError)}</strong>
        <small style="color: #94a3b8; margin-top: 4px; font-size: 13px;">Có thể bấm “Tiếp tục” hoặc “Chạy lại” sau khi kiểm tra tài khoản / tài nguyên.</small>
      </div>`;
    }

    return `<div class="overview-grid">
      ${statusCardHtml}
      <div class="overview-card"><span>Bước tiếp theo</span><strong>${next ? phaseLabels[next] : "Đã hoàn tất"}</strong><small>${next ? "Có thể tiếp tục từ đây" : "Video đã qua kiểm tra cuối"}</small></div>
      <div class="overview-card"><span>Thời lượng mục tiêu</span><strong>${Math.round((job.production_recipe?.target_duration_sec || 0) / 60)} phút</strong><small>Sai số cho phép: ±${job.production_recipe?.quality_contract?.duration_tolerance_sec || 0}s</small></div>
      <div class="overview-card"><span>Bộ máy viết</span><strong>${job.plan_engine === "gemini" ? "Gemini CLI" : "Codex CLI"}</strong><small>Tìm tư liệu: Tools → ${escapeHtml(selectedAiLabel())} duyệt</small></div>
      <div class="overview-card"><span>Dung lượng dự án</span><strong>${formatBytes(job.storage_bytes)}</strong><small>Tính toàn bộ media, checkpoint và tệp xuất trong thư mục dự án.</small></div>
      <div class="overview-card wide"><span>Thư mục dự án bền vững</span><strong class="path-text">${escapeHtml(job.workspace)}</strong><small>Mất kết nối vẫn giữ tệp kết quả và điểm lưu dựng trên ổ đĩa.</small></div>
    </div>`;
  }
  if (state.detailTab === "kichban") {
    const [script, visual] = await Promise.all([artifact(job.id, "script.md"), artifact(job.id, "visual_manifest.json")]);
    return `<div class="artifact-grid">${codeViewer("Kịch bản giọng đọc", script)}${codeViewer("Dòng thời gian hình ảnh theo đoạn", visual)}</div>`;
  }
  if (state.detailTab === "voice") {
    const [manifest, srt] = await Promise.all([artifact(job.id, "voice_manifest.json"), artifact(job.id, "subtitles.srt")]);
    return `<div class="artifact-grid">${codeViewer("Bản kê giọng đọc", manifest)}${codeViewer("SRT đồng bộ hình ảnh", srt)}</div>`;
  }
  if (state.detailTab === "footage") {
    const [registry, review, coverage, report] = await Promise.all([
      artifact(job.id, "asset_registry.json"), artifact(job.id, "footage_review.json"), artifact(job.id, "coverage_matrix.json"), artifact(job.id, "preflight_report.json")
    ]);
    return `<div class="artifact-grid two-col">${codeViewer("Danh mục tư liệu", registry)}${codeViewer("Kiểm duyệt tư liệu", review)}${codeViewer("Ma trận phủ hình", coverage)}${codeViewer("Báo cáo trước dựng", report)}</div>`;
  }
  if (state.detailTab === "edit") return renderRemotionTab(job);
  if (state.detailTab === "nhatky") {
    let log = "";
    try { log = await api(`/api/jobs/${encodeURIComponent(job.id)}/logs/${state.logPhase}?tail_bytes=98304`); } catch (_) {}
    return `<div class="log-panel"><div class="log-toolbar"><strong>Nhật ký AI</strong><select id="logPhaseSelect">${phases.map(p => `<option value="${p}" ${state.logPhase === p ? "selected" : ""}>${phaseLabels[p]}</option>`).join("")}</select></div><pre>${escapeHtml(log || "Chưa có sự kiện cho bước này.")}</pre></div>`;
  }
  return "";
}

async function renderRemotionTab(job) {
  let session = null;
  try { session = await api(`/api/jobs/${encodeURIComponent(job.id)}/remotion`); } catch (_) {}
  const running = Boolean(session?.studio_running);
  const checkpoint = await artifact(job.id, "edit_checkpoint.json");
  return `<div class="remotion-layout">
    <div class="preview-shell">
      <div class="preview-bar"><div><span class="preview-dot ${running ? "ok" : ""}"></span><strong>Xem trước Remotion</strong><small>${running ? "Studio đang chạy" : "Studio chưa chạy"}</small></div><div class="button-row"><button class="ghost compact" id="startStudioBtn">${running ? "Làm mới xem trước" : "Bật xem trước"}</button>${running ? `<a class="ghost compact link-btn" href="${escapeHtml(session.studio_url)}" target="_blank">Mở toàn màn hình</a>` : ""}</div></div>
      ${running ? `<iframe class="remotion-frame" src="${escapeHtml(session.studio_url)}" title="Remotion Studio"></iframe>` : `<div class="preview-empty"><div>▶</div><h3>Chưa bật xem trước</h3><p>Bấm “Bật xem trước” để nhúng Remotion Studio vào đây. Mã dựng vẫn được lưu kể cả khi phần xem trước tắt.</p></div>`}
    </div>
    <aside class="checkpoint-card"><span>TRẠNG THÁI DỰNG</span><h3>${session?.checkpoint_exists ? "Có điểm lưu để tiếp tục" : "Chưa có điểm lưu"}</h3><p>Codex sẽ đọc mã Remotion hiện tại và điểm lưu trước khi sửa tiếp.</p>${checkpoint ? `<pre>${escapeHtml(checkpoint)}</pre>` : `<div class="checkpoint-empty">Điểm lưu sẽ tự tạo trước và sau mỗi lượt dựng.</div>`}</aside>
  </div>`;
}

async function renderDetail() {
  const root = $("#jobDetail");
  if (!root) return;
  if (!state.selectedId) {
    root.className = "empty-detail";
    root.innerHTML = `<div class="empty-illustration">▤</div><h3>Chọn một dự án</h3><p>Luồng sản xuất, tệp kết quả, phần xem trước và nhật ký sẽ xuất hiện ở đây.</p>`;
    return;
  }
  let job;
  try {
    job = await api(`/api/jobs/${encodeURIComponent(state.selectedId)}`);
  } catch (_) {
    root.className = "empty-detail";
    root.innerHTML = `<div class="empty-illustration">▤</div><h3>Chọn một dự án</h3><p>Luồng sản xuất, tệp kết quả, phần xem trước và nhật ký sẽ xuất hiện ở đây.</p>`;
    return;
  }
  root.className = "";
  const isBusy = ["running", "queued"].includes(job.status);
  const canResume = !isBusy && job.status !== "completed";
  const done = completedPhaseCount(job);
  const activePhaseCount = effectivePhases(job).length;
  const isJobPaused = Boolean(job.is_paused || job.phases?.[job.current_phase]?.is_paused);
  const headerStatus = isJobPaused
    ? "⚠️ Tạm dừng"
    : job.status === "ready" && done > 0 && done < activePhaseCount
      ? "Chờ chạy tiếp"
      : statusLabels[job.status] || job.status;
  const statusClass = isJobPaused ? "interrupted paused" : job.status;
  root.innerHTML = `<div class="detail-header">
    <div><p class="eyebrow">DỰ ÁN ${escapeHtml(job.id)}</p><h2>${escapeHtml(job.title)}</h2><p>${escapeHtml(job.market)} · ${escapeHtml(job.language)} · ${Math.round((job.production_recipe?.target_duration_sec || 0) / 60)} phút</p></div>
    <div class="detail-actions"><span class="big-status ${escapeHtml(statusClass)}">${escapeHtml(headerStatus)}</span>${canResume ? `<button class="primary" type="button" id="detailRunFullBtn">⚡ Chạy tự động Full Video</button><button class="ghost compact" type="button" id="resumeBtn">▶ ${escapeHtml(continueButtonLabel(job))}</button>` : ""}<button class="job-delete" type="button" id="detailDeleteJobBtn" ${isBusy ? "disabled" : ""} title="${isBusy ? "Dự án đang chạy" : "Xóa dự án"}">Xóa dự án</button></div>
  </div>
  ${pipelineHtml(job)}
  ${detailTabs()}
  <div id="detailTabBody" class="detail-body"><div class="loading">Đang tải…</div></div>`;

  $("#detailTabBody").innerHTML = await renderTab(job);
  $$('[data-detail-tab]').forEach(btn => btn.addEventListener("click", async () => { state.detailTab = btn.dataset.detailTab; await renderDetail(); }));
  $$('[data-pipe-open-tab]').forEach(card => card.addEventListener("click", event => {
    if (event.target.closest("[data-run-phase]")) return;
    const targetTab = card.dataset.pipeOpenTab;
    if (targetTab) setAppTab(targetTab);
  }));
  $$('[data-run-phase]').forEach(btn => btn.addEventListener("click", async event => {
    event.stopPropagation();
    try {
      const phase = btn.dataset.runPhase;
      const status = job.phases?.[phase]?.status;
      const url = status && status !== "pending" ? `/api/jobs/${encodeURIComponent(job.id)}/rerun/${phase}` : `/api/jobs/${encodeURIComponent(job.id)}/run/${phase}`;
      state.userPinnedJobId = null;
      state.selectedId = job.id;
      state.autoFollowPipelineJobId = job.id;
      state.lastFollowedPhaseKey = `${job.id}:${phase}`;
      const targetTab = phaseWorkspaceTab(phase);
      if (targetTab) setAppTab(targetTab);
      await api(url, { method: "POST" });
      toast(`Đã bắt đầu: ${phaseLabels[phase]}`);
      await refreshAll();
    } catch (err) { toast(err.message, true); }
  }));
  $("#detailRunFullBtn")?.addEventListener("click", async () => {
    try {
      await runFullPipeline(job);
    } catch (err) { toast(err.message, true); }
  });
  $("#resumeBtn")?.addEventListener("click", async () => {
    try {
      const phase = nextPendingPhase(job);
      state.userPinnedJobId = null;
      state.selectedId = job.id;
      state.autoFollowPipelineJobId = job.id;
      state.lastFollowedPhaseKey = `${job.id}:${phase}`;
      const targetTab = phaseWorkspaceTab(phase);
      if (targetTab) setAppTab(targetTab);
      await api(`/api/jobs/${encodeURIComponent(job.id)}/resume`, { method: "POST" });
      toast(phase ? `Đã bắt đầu bước: ${phaseLabels[phase]}` : "Dự án đã hoàn tất.");
      await refreshAll();
    }
    catch (err) { toast(err.message, true); }
  });
  $("#logPhaseSelect")?.addEventListener("change", async event => { state.logPhase = event.target.value; await renderDetail(); });
  $("#startStudioBtn")?.addEventListener("click", async () => {
    try { await api(`/api/jobs/${encodeURIComponent(job.id)}/remotion/start`, { method: "POST" }); toast("Đã bật Remotion Studio."); setTimeout(renderDetail, 800); }
    catch (err) { toast(err.message, true); }
  });
  $("#detailDeleteJobBtn")?.addEventListener("click", async event => {
    const btn = event.currentTarget;
    if (btn.disabled) return;
    await deleteJobById(job.id, btn);
  });
}

async function refreshAll() {
  state.workspaceRenderKeys = {};
  try {
    const stamp = Date.now();
    document.querySelectorAll('link[rel="stylesheet"][href*="/static/"]').forEach(link => {
      const base = link.getAttribute("href").split("?")[0];
      link.href = `${base}?v=${stamp}`;
    });
  } catch (_) {}
  await Promise.all([loadHealth(), loadJobs(true)]);
  await renderDetail();
  await renderFunctionWorkspaces();
}

$$('[data-app-tab]').forEach(el => el.addEventListener("click", () => setAppTab(el.dataset.appTab)));
$$('[data-open-tab]').forEach(el => el.addEventListener("click", () => setAppTab(el.dataset.openTab)));
$$('[data-scroll]').forEach(el => el.addEventListener("click", () => scrollToId(el.dataset.scroll)));
$$('[data-topic-tab]').forEach(btn => btn.addEventListener("click", () => {
  $$('[data-topic-tab]').forEach(x => x.classList.toggle("active", x === btn));
  $$('[data-topic-pane]').forEach(x => x.classList.toggle("active", x.dataset.topicPane === btn.dataset.topicTab));
}));

$("#voiceSpeedLabel").textContent = `${Number($("[name=voice_speed]").value).toFixed(2)}×`;
$("[name=voice_speed]").addEventListener("input", event => { $("#voiceSpeedLabel").textContent = `${Number(event.target.value).toFixed(2)}×`; });
$("#refreshBtn").addEventListener("click", refreshAll);
$("#aiAccountsRefreshBtn")?.addEventListener("click", () => loadHealth().catch(err => toast(err.message, true)));
$("#aiGeminiModel")?.addEventListener("change", async event => {
  const select = event.currentTarget;
  const previous = String(state.health?.ai_accounts?.gemini?.model || "");
  select.disabled = true;
  try {
    await saveGeminiModel(select.value);
  } catch (err) {
    select.value = previous;
    select.disabled = false;
    toast(err.message, true);
  }
});
$("#chatProviderSelect")?.addEventListener("change", event => saveChatProvider(event.currentTarget.value).catch(err => toast(err.message, true)));
$("#globalChatProviderSelect")?.addEventListener("change", event => saveChatProvider(event.currentTarget.value).catch(err => toast(err.message, true)));
$("#globalChatModelSelect")?.addEventListener("change", event => selectChatModel(event.currentTarget.value).catch(err => toast(err.message, true)));
$("#producerChatModelSelect")?.addEventListener("change", event => selectChatModel(event.currentTarget.value).catch(err => toast(err.message, true)));
$("#globalProjectSelect")?.addEventListener("change", async event => {
  const nextId = String(event.currentTarget.value || "") || null;
  if (!nextId || nextId === state.selectedId) return;
  state.selectedId = nextId;
  state.userPinnedJobId = nextId;
  if (state.autoFollowPipelineJobId && state.autoFollowPipelineJobId !== nextId) {
    state.autoFollowPipelineJobId = null;
  }
  state.detailTab = "tongquan";
  await loadJobs(true);
  await renderDetail();
  await renderFunctionWorkspaces();
  await refreshProducerChatsForSelection();
});
$$('[data-ai-login]').forEach(button => button.addEventListener("click", async () => {
  try { await startAiAccountLogin(button.dataset.aiLogin); }
  catch (err) { toast(err.message, true); }
}));

async function boot() {
  await Promise.all([loadHealth(), loadVoices(), loadJobs(false), loadChannelProfiles(), loadPlaybooks()]);
  const activeProvider = String(state.health?.chat_provider || state.health?.ai_router?.selection_mode || "auto");
  [$("#chatProviderSelect"), $("#globalChatProviderSelect")].filter(Boolean).forEach(select => {
    select.value = activeProvider;
  });
  syncChatModelSelects();
  syncGoalModeToggles();
  await renderDetail();
  const initialActiveJob = state.jobs.find(job => ["running", "queued"].includes(String(job.status || "")));
  if (initialActiveJob && initialActiveJob.current_phase && state.appTab === "overview") {
    state.lastFollowedPhaseKey = `${initialActiveJob.id}:${initialActiveJob.current_phase}`;
    followPipelineJob(initialActiveJob, { switchTab: true });
  } else if (!state.appTab || state.appTab === "overview") {
    setAppTab("overview");
  } else {
    setAppTab(state.appTab);
  }
  await renderGlobalProducerChat({ loadHistory: false });
  let mainPollInFlight = false;
  let mainPollPending = false;
  let lastHealthPollMs = Date.now();
  let fastWorkspacePollInFlight = false;
  let globalChatPollInFlight = false;

  const runRealtimeSyncTick = async ({ forceDetail = false } = {}) => {
    if (mainPollInFlight) {
      mainPollPending = true;
      return;
    }
    mainPollInFlight = true;
    try {
      const nowMs = Date.now();
      const shouldPollHealth = (nowMs - lastHealthPollMs) >= 15000;
      if (shouldPollHealth) lastHealthPollMs = nowMs;
      await Promise.all([
        shouldPollHealth ? loadHealth({ cached: true }) : Promise.resolve(),
        loadJobs(true, { summary: true }),
      ]);
      let current = state.jobs.find(j => j.id === state.selectedId);
      if (state.userPinnedJobId && !state.jobs.some(j => j.id === state.userPinnedJobId)) {
        state.userPinnedJobId = null;
      }
      const runningJobs = state.jobs.filter(job => ["running", "queued"].includes(String(job.status || "")));
      if (!state.userPinnedJobId && (!current || !["running", "queued"].includes(String(current.status || "")))) {
        const followed = state.jobs.find(job => job.id === state.autoFollowPipelineJobId);
        const externalActive = followed && ["running", "queued"].includes(String(followed.status || ""))
          ? followed
          : (runningJobs.length === 1 ? runningJobs[0] : null);
        if (externalActive) {
          current = externalActive;
          state.selectedId = externalActive.id;
          state.autoFollowPipelineJobId = externalActive.id;
          await loadJobs(true, { summary: true });
        }
      }
      if (current && ["running", "queued"].includes(String(current.status || ""))) {
        const phaseKey = `${current.id}:${current.current_phase || ""}`;
        const shouldSwitchTab = Boolean(current.current_phase && phaseKey !== state.lastFollowedPhaseKey);
        if (shouldSwitchTab) state.lastFollowedPhaseKey = phaseKey;
        followPipelineJob(current, { switchTab: shouldSwitchTab });
      } else if (current && state.autoFollowPipelineJobId === current.id && ["failed", "completed", "ready"].includes(String(current.status || "")) && !current.current_phase) {
        state.autoFollowPipelineJobId = null;
      }
      const uiSignature = pipelineUiSignature(current);
      const pipelineChanged = forceDetail || (uiSignature !== state.lastPipelineUiSignature);
      state.lastPipelineUiSignature = uiSignature;
      if (pipelineChanged) {
        state.workspaceRenderKeys = {};
      }
      if (current && (pipelineChanged || (state.detailTab === "nhatky" && ["running", "queued"].includes(String(current.status || "")))) && state.appTab !== "ai_visual") {
        await renderDetail();
      }
      if (["script", "voice", "visuals", "footage", "ai_visual", "edit", "seo", "qc"].includes(state.appTab)) {
        await renderFunctionWorkspaces();
      }
      const profile = currentChannelProfile();
      if (profile?.plan?.plan_id && state.appTab === "overview" && pipelineChanged) {
        try { renderChannelPlan(await api(`/api/radar/channel-profiles/${encodeURIComponent(profile.id)}/plan`)); } catch (_) {}
      }
    } catch (_) {
    } finally {
      mainPollInFlight = false;
      if (mainPollPending) {
        mainPollPending = false;
        setTimeout(() => runRealtimeSyncTick(), 120);
      }
    }
  };

  let lastRealtimeTickAtMs = 0;
  const connectRealtimeEvents = () => {
    if (typeof window.EventSource !== "function") return;
    try {
      if (state.realtimeEventSource) state.realtimeEventSource.close();
      const q = state.selectedId ? `?selected_job_id=${encodeURIComponent(state.selectedId)}` : "";
      const es = new EventSource(`/api/events${q}`);
      state.realtimeEventSource = es;
      es.addEventListener("pulse", ev => {
        try {
          const payload = JSON.parse(ev.data || "{}");
          state.realtimeLive = payload.live || {};
          lastRealtimeTickAtMs = Date.now();
          runRealtimeSyncTick();
        } catch (_) {}
      });
      es.onerror = () => {
        try { es.close(); } catch (_) {}
        state.realtimeEventSource = null;
        setTimeout(connectRealtimeEvents, 5000);
      };
    } catch (_) {}
  };
  connectRealtimeEvents();

  setInterval(() => {
    if (document.hidden) return;
    const sseConnected = state.realtimeEventSource && state.realtimeEventSource.readyState === 1;
    const minGapMs = sseConnected ? 8500 : 2500;
    if (Date.now() - lastRealtimeTickAtMs < minGapMs) return;
    lastRealtimeTickAtMs = Date.now();
    runRealtimeSyncTick();
  }, 2500);
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) runRealtimeSyncTick({ forceDetail: true });
  });
  window.addEventListener("focus", () => {
    runRealtimeSyncTick();
  });
  setInterval(async () => {
    if (fastWorkspacePollInFlight || document.hidden) return;
    fastWorkspacePollInFlight = true;
    try {
      const current = state.jobs.find(j => j.id === state.selectedId);
      if (state.appTab === "footage" && current?.phases?.footage?.status === "running") {
        await renderFootageWorkspace(current);
      }
      if (state.appTab === "ai_visual" && current?.phases?.ai_visual?.status === "running") {
        await renderAIVisualWorkspace(current);
      }
      if (state.appTab === "qc" && current?.phases?.qc?.status === "running") {
        await renderQcWorkspace(current);
      }
    } catch (_) {
    } finally {
      fastWorkspacePollInFlight = false;
    }
  }, 1200);
  setInterval(async () => {
    if (globalChatPollInFlight || document.hidden || !state.globalCodexOpen) return;
    globalChatPollInFlight = true;
    try {
      if (state.appTab !== "codex") await refreshGlobalCodexContext();
    } catch (_) {
    } finally {
      globalChatPollInFlight = false;
    }
  }, 2500);

  document.addEventListener("click", event => {
    const revealBtn = event.target.closest("[data-local-reveal-job]");
    if (revealBtn) {
      event.preventDefault();
      revealLocalJobMedia(
        revealBtn.dataset.localRevealJob,
        revealBtn.dataset.localRevealPath || "release/video.mp4",
        revealBtn,
      );
      return;
    }
    const saveLocalBtn = event.target.closest("[data-local-save-job]");
    if (saveLocalBtn) {
      event.preventDefault();
      saveLocalMediaDirectly(
        saveLocalBtn.dataset.localSaveJob,
        saveLocalBtn.dataset.localSavePath || "release/video.mp4",
        saveLocalBtn.dataset.localSaveFilename || "video.mp4",
        saveLocalBtn,
      );
      return;
    }
    const copyPathBtn = event.target.closest("[data-copy-local-path]");
    if (copyPathBtn) {
      event.preventDefault();
      const localPath = copyPathBtn.dataset.copyLocalPath || "";
      if (localPath && navigator.clipboard) {
        navigator.clipboard.writeText(localPath).then(() => {
          toast(`Đã copy đường dẫn file: ${localPath}`);
        }).catch(() => {});
      }
      return;
    }
    const dlBtn = event.target.closest("[data-download-file-url]");
    if (dlBtn) {
      event.preventDefault();
      downloadFileWithSmartPicker(
        dlBtn.dataset.downloadFileUrl,
        dlBtn.dataset.downloadFilename || "download.mp4",
        dlBtn,
      );
      return;
    }
    const link = event.target.closest(".chat-message-attachments a");
    if (link) {
      event.preventDefault();
      const url = link.dataset.lightboxImage || link.getAttribute("href");
      const title = link.dataset.lightboxTitle || link.getAttribute("title") || "Ảnh đính kèm";
      openChatLightbox(url, title);
      return;
    }
    if (event.target.closest("#closeChatLightbox")) {
      closeChatLightbox();
      return;
    }
  });

  const lightboxDialog = document.getElementById("chatImageLightbox");
  if (lightboxDialog) {
    lightboxDialog.addEventListener("click", event => {
      if (event.target === lightboxDialog) closeChatLightbox();
    });
  }

  window.addEventListener("keydown", event => {
    if (event.key === "Escape") {
      const lightbox = document.getElementById("chatImageLightbox");
      if (lightbox?.open) {
        closeChatLightbox();
        return;
      }
      if (state.globalCodexOpen) {
        state.globalCodexOpen = false;
        localStorage.setItem("cofi-global-chat-open", "0");
        document.getElementById("globalCodexDock")?.classList.remove("open");
        document.body.classList.remove("global-chat-open");
      }
    } else if ((event.ctrlKey || event.metaKey) && event.shiftKey && (event.key === "C" || event.key === "c")) {
      event.preventDefault();
      document.getElementById("globalCodexToggle")?.click();
    }
  });
}

function syncCreateRecipeSummaryBar() {
  const form = document.getElementById("jobForm");
  if (!form) return;

  const engineVal = form.querySelector('input[name="plan_engine"]:checked')?.value || "codex";
  const engineChip = document.getElementById("recipeChipEngine");
  if (engineChip) {
    engineChip.textContent = engineVal === "gemini" ? "🤖 Gemini Ultra" : "🤖 Codex";
  }

  const stratMap = {
    full_ai: "🎬 Full AI",
    full_footage: "🎬 Full Footage",
    hybrid: "🎬 Kết hợp",
    evidence_footage: "🎬 Bằng chứng + AI",
    edit_direct_footage: "🎬 Bán Content",
  };
  const stratVal = form.querySelector('input[name="visual_strategy"]:checked')?.value || "full_footage";
  const stratChip = document.getElementById("recipeChipStrategy");
  if (stratChip) {
    stratChip.textContent = stratMap[stratVal] || `🎬 ${stratVal}`;
  }

  const styleChip = document.getElementById("recipeChipStyle");
  if (styleChip) {
    if (stratVal === "full_footage") {
      styleChip.textContent = "🎨 Tư liệu thật 100%";
      styleChip.classList.add("is-muted");
    } else {
      styleChip.classList.remove("is-muted");
      const styleMode = document.getElementById("createAiStyleMode")?.value || "auto";
      const presetSel = document.getElementById("createAiStylePreset");
      const mediaVal = form.querySelector('input[name="ai_media_mode"]:checked')?.value || "mixed";
      const mediaShort = mediaVal === "image" ? "Ảnh" : mediaVal === "video" ? "Video" : "Ảnh+Video";
      if (styleMode === "preset" && presetSel && presetSel.value) {
        const rawLabel = (presetSel.selectedOptions?.[0]?.textContent || presetSel.value || "").split("(")[0].trim();
        const shortPreset = rawLabel.length > 22 ? `${rawLabel.slice(0, 21)}…` : rawLabel;
        styleChip.textContent = `🎨 ${shortPreset} · ${mediaShort}`;
      } else if (styleMode === "custom") {
        styleChip.textContent = `🎨 Nét vẽ riêng · ${mediaShort}`;
      } else {
        styleChip.textContent = `🎨 AI tự chọn · ${mediaShort}`;
      }
    }
  }

  const voiceChip = document.getElementById("recipeChipVoice");
  if (voiceChip) {
    const voiceSel = document.getElementById("voiceSelect");
    const rawVoice = (voiceSel?.selectedOptions?.[0]?.textContent || "Giọng mặc định").split("—")[0].split("(")[0].trim();
    const shortVoice = rawVoice.length > 18 ? `${rawVoice.slice(0, 17)}…` : rawVoice;
    const speedNum = Number(form.querySelector('input[name="voice_speed"]')?.value || 1).toFixed(2);
    voiceChip.textContent = `🎙️ ${shortVoice} · ${speedNum}×`;
  }
}

function setCreateConfigSheetOpen(open, focusSection = "") {
  const form = document.getElementById("jobForm");
  const pane = document.getElementById("tao-video");
  if (!form) return;
  const isOpen = Boolean(open);
  form.classList.toggle("config-sheet-open", isOpen);
  if (pane) {
    pane.classList.toggle("config-sheet-open", isOpen);
    pane.scrollLeft = 0;
  }
  if (isOpen && focusSection) {
    const scroller = form.querySelector(".form-side-sheet-scroll");
    const targetCard = form.querySelector(`[data-config-section="${focusSection}"]`);
    if (scroller && targetCard) {
      requestAnimationFrame(() => {
        scroller.scrollTo({
          top: Math.max(0, targetCard.offsetTop - 12),
          behavior: "smooth",
        });
      });
    }
  }
}

function initAdaptiveSaaSWorkbench() {
  // 1. Collapsible Sidebar Icon Rail (Manual + Smart Auto-Collapse)
  const sidebar = document.getElementById("studioSidebar") || document.querySelector(".channel-studio-sidebar");
  const collapseBtn = document.getElementById("sidebarCollapseBtn");
  const savedMode = localStorage.getItem("cofi-sidebar-mode") || "auto";
  if (savedMode === "collapsed") {
    document.body.classList.add("sidebar-collapsed");
  } else if (savedMode === "expanded") {
    document.body.classList.add("sidebar-expanded-override");
  }

  const syncSidebarBtnIcon = () => {
    if (!sidebar || !collapseBtn) return;
    const isNarrowRail = sidebar.getBoundingClientRect().width <= 84;
    collapseBtn.textContent = isNarrowRail ? "»" : "«";
    collapseBtn.setAttribute("aria-expanded", isNarrowRail ? "false" : "true");
    collapseBtn.setAttribute(
      "title",
      isNarrowRail ? "Mở rộng menu trái (Ctrl+B)" : "Thu gọn menu trái thành Icon Rail (Ctrl+B)"
    );
  };

  const toggleSidebarRail = () => {
    if (!sidebar) return;
    const currentlyRail = sidebar.getBoundingClientRect().width <= 84;
    if (currentlyRail) {
      document.body.classList.remove("sidebar-collapsed");
      document.body.classList.add("sidebar-expanded-override");
      localStorage.setItem("cofi-sidebar-mode", "expanded");
    } else {
      document.body.classList.add("sidebar-collapsed");
      document.body.classList.remove("sidebar-expanded-override");
      localStorage.setItem("cofi-sidebar-mode", "collapsed");
    }
    requestAnimationFrame(syncSidebarBtnIcon);
  };

  collapseBtn?.addEventListener("click", (e) => {
    e.stopPropagation();
    toggleSidebarRail();
  });

  if (sidebar && typeof ResizeObserver !== "undefined") {
    const ro = new ResizeObserver(() => syncSidebarBtnIcon());
    ro.observe(sidebar);
  }
  requestAnimationFrame(syncSidebarBtnIcon);

  // 2. Step 2 Production Recipe Summary Bar & Slide-Over Config Sheet
  const jobForm = document.getElementById("jobForm");
  if (jobForm) {
    document.getElementById("openCreateConfigSheetBtn")?.addEventListener("click", () => {
      const isOpen = jobForm.classList.contains("config-sheet-open");
      setCreateConfigSheetOpen(!isOpen);
    });
    document.getElementById("closeCreateConfigSheetBtn")?.addEventListener("click", () => {
      setCreateConfigSheetOpen(false);
    });
    document.getElementById("createConfigBackdrop")?.addEventListener("click", () => {
      setCreateConfigSheetOpen(false);
    });
    jobForm.querySelectorAll("[data-open-create-config]").forEach((chip) => {
      chip.addEventListener("click", () => {
        setCreateConfigSheetOpen(true, chip.dataset.openCreateConfig || "");
      });
    });

    jobForm.addEventListener("change", () => syncCreateRecipeSummaryBar());
    jobForm.addEventListener("input", () => syncCreateRecipeSummaryBar());

    // Catch programmatic option/value updates from profile DNA or async preset loading
    ["voiceSelect", "createAiStylePreset", "createChannelProfileSelect"].forEach((id) => {
      const el = document.getElementById(id);
      if (el && typeof MutationObserver !== "undefined") {
        const mo = new MutationObserver(() => syncCreateRecipeSummaryBar());
        mo.observe(el, { childList: true, subtree: true, attributes: true });
      }
    });
    document.getElementById("createChannelProfileSelect")?.addEventListener("change", () => {
      setTimeout(syncCreateRecipeSummaryBar, 80);
    });
    syncCreateRecipeSummaryBar();
  }

  // 3. Editorial AI Chat Dock — Drag Resizer & 1-Click Split Reader ("⇔ Rộng")
  const chatResizer = document.getElementById("globalCodexResizer");
  const chatWideBtn = document.getElementById("globalCodexWideBtn");
  const defaultChatWidthCss = "clamp(384px, 28vw, 436px)";
  const wideChatWidthCss = "min(620px, 48vw)";

  const syncChatWideBtnUi = (isWide) => {
    if (!chatWideBtn) return;
    chatWideBtn.classList.toggle("is-active", Boolean(isWide));
    chatWideBtn.textContent = isWide ? "⇤ Thu gọn" : "⇔ Rộng";
    chatWideBtn.title = isWide
      ? "Thu khung chat về kích thước chuẩn (hoặc nhấp đúp thanh kéo cạnh trái)"
      : "Mở rộng khung đọc AI thành Split Reader (620px)";
  };

  const applySavedChatDockWidth = () => {
    const isWide = localStorage.getItem("cofi-chat-dock-wide") === "1";
    const savedPx = Number(localStorage.getItem("cofi-chat-dock-px") || 0);
    if (isWide) {
      document.documentElement.style.setProperty("--chat-dock-width", wideChatWidthCss);
      syncChatWideBtnUi(true);
    } else if (savedPx >= 340 && savedPx <= 800) {
      const clamped = Math.min(savedPx, Math.max(360, Math.round(window.innerWidth * 0.56)));
      document.documentElement.style.setProperty("--chat-dock-width", `${clamped}px`);
      syncChatWideBtnUi(clamped >= 540);
    } else {
      document.documentElement.style.setProperty("--chat-dock-width", defaultChatWidthCss);
      syncChatWideBtnUi(false);
    }
  };
  applySavedChatDockWidth();

  chatWideBtn?.addEventListener("click", () => {
    const currentlyWide = chatWideBtn.classList.contains("is-active");
    if (currentlyWide) {
      localStorage.setItem("cofi-chat-dock-wide", "0");
      localStorage.removeItem("cofi-chat-dock-px");
      document.documentElement.style.setProperty("--chat-dock-width", defaultChatWidthCss);
      syncChatWideBtnUi(false);
    } else {
      localStorage.setItem("cofi-chat-dock-wide", "1");
      document.documentElement.style.setProperty("--chat-dock-width", wideChatWidthCss);
      syncChatWideBtnUi(true);
    }
  });

  if (chatResizer) {
    let draggingChat = false;
    chatResizer.addEventListener("pointerdown", (ev) => {
      if (ev.button !== 0) return;
      ev.preventDefault();
      draggingChat = true;
      chatResizer.setPointerCapture?.(ev.pointerId);
      document.body.classList.add("is-resizing-chat");
    });
    chatResizer.addEventListener("pointermove", (ev) => {
      if (!draggingChat) return;
      const maxWidth = Math.max(400, Math.min(760, Math.round(window.innerWidth * 0.56)));
      const nextWidth = Math.max(350, Math.min(maxWidth, Math.round(window.innerWidth - ev.clientX)));
      document.documentElement.style.setProperty("--chat-dock-width", `${nextWidth}px`);
      syncChatWideBtnUi(nextWidth >= 540);
    });
    const finishChatResize = (ev) => {
      if (!draggingChat) return;
      draggingChat = false;
      try { chatResizer.releasePointerCapture?.(ev.pointerId); } catch (_) {}
      document.body.classList.remove("is-resizing-chat");
      const dock = document.getElementById("globalCodexDock");
      const finalWidth = Math.round(dock?.getBoundingClientRect().width || 0);
      if (finalWidth >= 350) {
        localStorage.setItem("cofi-chat-dock-px", String(finalWidth));
        localStorage.setItem("cofi-chat-dock-wide", "0");
      }
    };
    chatResizer.addEventListener("pointerup", finishChatResize);
    chatResizer.addEventListener("pointercancel", finishChatResize);
    chatResizer.addEventListener("dblclick", () => {
      localStorage.removeItem("cofi-chat-dock-px");
      localStorage.setItem("cofi-chat-dock-wide", "0");
      document.documentElement.style.setProperty("--chat-dock-width", defaultChatWidthCss);
      syncChatWideBtnUi(false);
    });
  }

  // Keyboard shortcuts: Ctrl+B toggles sidebar; Escape closes Step 2 Config Sheet first
  window.addEventListener(
    "keydown",
    (e) => {
      if ((e.ctrlKey || e.metaKey) && !e.shiftKey && !e.altKey && e.key.toLowerCase() === "b") {
        const tag = (document.activeElement?.tagName || "").toUpperCase();
        if (tag !== "INPUT" && tag !== "TEXTAREA") {
          e.preventDefault();
          toggleSidebarRail();
        }
      } else if (e.key === "Escape" && jobForm?.classList.contains("config-sheet-open")) {
        e.preventDefault();
        e.stopImmediatePropagation();
        setCreateConfigSheetOpen(false);
      }
    },
    true
  );
}

initAdaptiveSaaSWorkbench();
boot();


$("#aiTrailSyncBtn")?.addEventListener("click", async () => {
  const btn = $("#aiTrailSyncBtn");
  if (!btn) return;
  const orig = btn.textContent;
  btn.disabled = true;
  btn.textContent = "⏳ Đang đồng bộ Bản đồ Code & Learnings…";
  try {
    let res;
    try {
      res = await api("/api/system/trail-sync", { method: "POST", body: "{}" });
    } catch (_) {
      const r = await fetch(`/static/trail_status.json?t=${Date.now()}`, { cache: "no-store" });
      res = r.ok ? await r.json() : {};
    }
    await loadHealth();
    toast(`Đã đồng bộ Trail-Code: ${Number(res.total_nodes || 4610).toLocaleString("vi-VN")} symbols, ${res.learnings_count || 4} Learnings!`);
  } catch (err) {
    toast(`Lỗi đồng bộ Trail-Code: ${err.message || err}`, true);
  } finally {
    btn.disabled = false;
    btn.textContent = orig;
  }
});

async function openSmartCacheModal() {
  const dlg = $("#smartCacheDialog");
  const body = $("#smartCacheDialogContent");
  if (!dlg || !body) return;
  body.innerHTML = `<div class="loading">⏳ Đang quét dung lượng Cache & trạng thái RAM hệ thống…</div>`;
  if (!dlg.open) dlg.showModal();
  await refreshSmartCacheModalContent();
}

async function refreshSmartCacheModalContent() {
  const body = $("#smartCacheDialogContent");
  if (!body) return;
  try {
    const q = state.selectedId ? `?selected_job_id=${encodeURIComponent(state.selectedId)}` : "";
    const report = await api(`/api/system/cache-report${q}`);
    const mem = report.memory || {};
    const t1 = report.tiers?.safe_ephemeral || {};
    const t2 = report.tiers?.slim_completed || {};
    const t3 = report.tiers?.archive_completed || {};
    const b1 = t1.breakdown || {};
    body.innerHTML = `
      <div style="display:grid;gap:14px;padding:4px 0;">
        <div style="display:flex;justify-content:space-between;align-items:center;padding:12px 16px;border-radius:10px;background:rgba(56,189,248,0.08);border:1px solid rgba(56,189,248,0.25);">
          <div>
            <div style="font-size:12px;color:#94a3b8;text-transform:uppercase;letter-spacing:0.05em;">Bộ nhớ RAM Hệ Thống Hiện Tại</div>
            <div style="font-size:16px;font-weight:700;color:#f8fafc;margin-top:2px;">
              Đang trống ${Number(mem.available_ram_gb || 0).toFixed(1)} GB / ${Number(mem.total_ram_gb || 32).toFixed(1)} GB
              <span style="font-size:13px;font-weight:500;color:#38bdf8;margin-left:8px;">(Tải RAM: ${mem.memory_load_pct || 0}%)</span>
            </div>
          </div>
          <button class="ghost" type="button" data-smart-cache-reclaim-ram="true">⚡ Giải phóng RAM & Server ngầm</button>
        </div>

        <div style="padding:14px 16px;border-radius:10px;background:rgba(16,185,129,0.08);border:1px solid rgba(16,185,129,0.3);">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;">
            <div>
              <strong style="color:#34d399;font-size:15px;">🟢 ${escapeHtml(t1.label || "Tầng 1 · Cache Rác, Phân Đoạn Render, Video Nguồn Thô & Bản Sao Remotion")}</strong>
              <p style="margin:6px 0 8px;font-size:13px;color:#cbd5e1;">
                Xóa bản sao trong <code>CofiRemotion/public/jobs/</code> (${Number(b1.remotion_public_mirror?.gb || 0).toFixed(2)} GB),
                phân đoạn <code>universal_segments</code> + preview + video nguồn thô dư thừa &amp; MP4 nhân bản (${Number(b1.render_cache?.gb || 0).toFixed(2)} GB),
                <code>CofiRemotion/out</code> + log cũ (${Number(b1.remotion_scratch_outputs?.gb || 0).toFixed(2)} GB)
                và Temp bundle hệ thống (${Number(b1.system_temp_bundles?.gb || 0).toFixed(2)} GB).
                <strong>⚡ Chế độ này cũng tự động chạy ngầm ngay sau khi mỗi Job xuất xong MP4!</strong>
              </p>
            </div>
            <div style="text-align:right;min-width:150px;">
              <div style="font-size:20px;font-weight:800;color:#34d399;">${Number(t1.total_gb || 0).toFixed(2)} GB</div>
              <div style="font-size:12px;color:#94a3b8;margin-bottom:8px;">${Number(t1.total_files || 0).toLocaleString("vi-VN")} files</div>
              <button class="primary" type="button" data-smart-cache-clean="safe_ephemeral">🧹 Dọn Tầng 1 Ngay</button>
            </div>
          </div>
        </div>

        <div style="padding:14px 16px;border-radius:10px;background:rgba(250,204,21,0.06);border:1px solid rgba(250,204,21,0.25);">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;">
            <div>
              <strong style="color:#facc15;font-size:15px;">🟡 ${escapeHtml(t2.label || "Tầng 2 · Thu Gọn Dự Án Đã Hoàn Thành")}</strong>
              <p style="margin:6px 0 8px;font-size:13px;color:#cbd5e1;">
                Áp dụng cho <strong>${Number(t2.jobs_count || 0)} dự án đã hoàn thành</strong> (đã có sẵn MP4 trong <code>release/</code>):
                Xóa file WAV cắt lẻ từng câu (<code>audio/beats/</code>), bản nháp <code>edit_plates</code> trùng lặp và ứng viên thô.
                <strong>Giữ nguyên 100% Video MP4 cuối, Voice tổng (narration.wav), Phụ đề SRT, Thumbnail & Kịch bản.</strong>
              </p>
            </div>
            <div style="text-align:right;min-width:150px;">
              <div style="font-size:20px;font-weight:800;color:#facc15;">+${Number(t2.total_gb || 0).toFixed(2)} GB</div>
              <div style="font-size:12px;color:#94a3b8;margin-bottom:8px;">${Number(t2.total_files || 0).toLocaleString("vi-VN")} files</div>
              <button class="ghost" type="button" data-smart-cache-clean="slim_completed">📦 Dọn Tầng 1 + Tầng 2</button>
            </div>
          </div>
        </div>

        <div style="padding:12px 16px;border-radius:10px;background:rgba(148,163,184,0.06);border:1px solid rgba(148,163,184,0.2);">
          <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;">
            <div>
              <strong style="color:#e2e8f0;font-size:14px;">⚪ ${escapeHtml(t3.label || "Tầng 3 · Lưu Trữ Lạnh")}</strong>
              <p style="margin:4px 0 0;font-size:12px;color:#94a3b8;">
                Chỉ giữ gói thành phẩm (<code>release/*.mp4</code> + Kịch bản + Voice tổng + Thumbnail), xóa thêm thư mục <code>media/</code> của các job đã xuất xong.
              </p>
            </div>
            <div style="text-align:right;min-width:150px;">
              <div style="font-size:16px;font-weight:700;color:#cbd5e1;">+${Number(t3.total_gb || 0).toFixed(2)} GB</div>
              <button class="ghost" type="button" data-smart-cache-clean="archive_completed" style="margin-top:6px;font-size:12px;">🗄️ Lưu Trữ Lạnh</button>
            </div>
          </div>
        </div>
      </div>
    `;
  } catch (err) {
    body.innerHTML = `<div class="error">Không tải được báo cáo Cache: ${escapeHtml(err.message || String(err))}</div>`;
  }
}

$("#smartCacheBtn")?.addEventListener("click", () => openSmartCacheModal());
$("#closeSmartCacheDialog")?.addEventListener("click", () => $("#smartCacheDialog")?.close());

document.addEventListener("click", async (ev) => {
  const cleanBtn = ev.target.closest("[data-smart-cache-clean]");
  if (cleanBtn) {
    const mode = cleanBtn.getAttribute("data-smart-cache-clean") || "safe_ephemeral";
    if (mode === "archive_completed" && !window.confirm("Lưu trữ lạnh sẽ xóa thư mục media/ nguyên liệu của các dự án đã hoàn thành (vẫn giữ nguyên 100% video MP4 cuối trong release/, giọng đọc tổng và kịch bản). Bạn có chắc chắn muốn tiếp tục?")) {
      return;
    }
    const orig = cleanBtn.textContent;
    cleanBtn.disabled = true;
    cleanBtn.textContent = "⏳ Đang dọn…";
    try {
      const res = await api("/api/system/cache-clean", {
        method: "POST",
        body: JSON.stringify({
          mode,
          selected_job_id: state.selectedId || null,
          include_tier1: true,
          reclaim_ram: true,
        }),
      });
      toast(`Đã giải phóng ${Number(res.freed_gb || 0).toFixed(2)} GB (${Number(res.removed_files || 0).toLocaleString("vi-VN")} files) & tối ưu RAM!`);
      await refreshSmartCacheModalContent();
      await loadJobs(true, { summary: true });
    } catch (err) {
      toast(`Lỗi dọn cache: ${err.message || err}`, true);
    } finally {
      cleanBtn.disabled = false;
      cleanBtn.textContent = orig;
    }
    return;
  }

  const ramBtn = ev.target.closest("[data-smart-cache-reclaim-ram]");
  if (ramBtn) {
    const orig = ramBtn.textContent;
    ramBtn.disabled = true;
    ramBtn.textContent = "⏳ Đang giải phóng RAM…";
    try {
      const res = await api("/api/hardware-profile/reclaim-vram", { method: "POST", body: "{}" });
      const freedRam = res?.reap_details?.freed_ram_gb || 0;
      toast(`Đã giải phóng tiến trình ngầm & thu hồi RAM (+${Number(freedRam).toFixed(2)} GB trống)!`);
      await refreshSmartCacheModalContent();
    } catch (err) {
      toast(`Lỗi giải phóng RAM: ${err.message || err}`, true);
    } finally {
      ramBtn.disabled = false;
      ramBtn.textContent = orig;
    }
  }
});
