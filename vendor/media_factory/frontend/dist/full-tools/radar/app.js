(() => {
  "use strict";

  const STALE_AFTER_HOURS = 6;

  const ROUTES = {
    dashboard: { title: "Tổng quan", canonical: "dashboard" },
    trend: { title: "Radar xu hướng", canonical: "trend" },
    radar: { title: "Radar xu hướng", canonical: "trend" },
    "trend/radar": { title: "Radar xu hướng", canonical: "trend" },
    niches: { title: "Phòng thí nghiệm ngách", canonical: "niches" },
    channels: { title: "Kênh của tôi", canonical: "channels" },
    plan: { title: "30 video", canonical: "plan" },
    today: { title: "Hôm nay", canonical: "today" },
    evidence: { title: "Thư viện bằng chứng", canonical: "evidence" },
    sources: { title: "Nguồn dữ liệu", canonical: "sources" },
    settings: { title: "Cài đặt", canonical: "settings" },
  };

  const els = {
    view: document.getElementById("appView"),
    title: document.getElementById("viewTitle"),
    apiState: document.getElementById("apiState"),
    refresh: document.getElementById("refreshButton"),
    scanShortcut: document.getElementById("scanShortcut"),
    scannerDot: document.getElementById("scannerDot"),
    scannerState: document.getElementById("scannerState"),
    scannerMarket: document.getElementById("scannerMarket"),
    scannerMeta: document.getElementById("scannerMeta"),
    toastRegion: document.getElementById("toastRegion"),
    channelProfileDialog: document.getElementById("channelProfileDialog"),
    channelProfileDialogTitle: document.getElementById("channelProfileDialogTitle"),
    channelProfileDialogBody: document.getElementById("channelProfileDialogBody"),
    closeChannelProfileDialog: document.getElementById("closeChannelProfileDialog"),
  };

  const state = {
    route: "dashboard",
    renderToken: 0,
    controller: null,
    selectedNicheId: null,
    channels: [],
    selectedChannelId: null,
  };

  class ApiError extends Error {
    constructor(message, status, payload) {
      super(message);
      this.name = "ApiError";
      this.status = status;
      this.payload = payload;
    }
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function attr(value) {
    return escapeHtml(value).replaceAll("`", "&#096;");
  }

  function firstDefined(...values) {
    return values.find((value) => value !== undefined && value !== null);
  }

  function arrayFrom(payload, ...keys) {
    if (Array.isArray(payload)) return payload;
    for (const key of keys) {
      if (Array.isArray(payload?.[key])) return payload[key];
    }
    for (const key of ["items", "results", "records", "data"]) {
      if (Array.isArray(payload?.[key])) return payload[key];
    }
    return [];
  }

  function fmtNumber(value, options = {}) {
    if (value === null || value === undefined || value === "") return "—";
    const n = Number(value);
    if (!Number.isFinite(n)) return escapeHtml(value);
    return new Intl.NumberFormat("vi-VN", options).format(n);
  }

  function fmtCompact(value) {
    if (value === null || value === undefined || value === "") return "—";
    const n = Number(value);
    if (!Number.isFinite(n)) return escapeHtml(value);
    return new Intl.NumberFormat("vi-VN", { notation: "compact", maximumFractionDigits: 1 }).format(n);
  }

  function fmtScore(value) {
    if (value === null || value === undefined || value === "") return "—";
    const n = Number(value);
    return Number.isFinite(n) ? n.toFixed(n % 1 ? 1 : 0) : escapeHtml(value);
  }

  function fmtRatio(value) {
    if (value === null || value === undefined || value === "") return "—";
    const n = Number(value);
    return Number.isFinite(n) ? `${n.toFixed(1)}×` : escapeHtml(value);
  }

  function fmtDate(value, withTime = false) {
    if (!value) return "—";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return escapeHtml(value);
    return new Intl.DateTimeFormat("vi-VN", withTime
      ? { dateStyle: "short", timeStyle: "short" }
      : { dateStyle: "medium" }).format(date);
  }

  function freshness(value, staleHours = STALE_AFTER_HOURS) {
    if (!value) return null;
    const time = new Date(value).getTime();
    if (Number.isNaN(time)) return null;
    const ageMs = Date.now() - time;
    return {
      stale: ageMs > staleHours * 60 * 60 * 1000,
      hours: Math.max(0, ageMs / 3_600_000),
    };
  }

  function relativeAge(value) {
    const info = freshness(value, Number.POSITIVE_INFINITY);
    if (!info) return "—";
    if (info.hours < 1) return `${Math.max(1, Math.round(info.hours * 60))} phút trước`;
    if (info.hours < 24) return `${Math.round(info.hours)} giờ trước`;
    return `${Math.round(info.hours / 24)} ngày trước`;
  }

  function statusPill(status) {
    const normalized = String(status || "unknown").toLowerCase();
    const map = {
      completed: ["Hoàn tất", "completed"],
      complete: ["Hoàn tất", "completed"],
      running: ["Đang chạy", "running"],
      pending: ["Đang chờ", "running"],
      queued: ["Đang chờ", "running"],
      failed: ["Lỗi", "failed"],
      error: ["Lỗi", "failed"],
      ready: ["Sẵn sàng", "ready"],
      doing: ["Đang làm", "doing"],
      done: ["Hoàn tất", "completed"],
      skipped: ["Bỏ qua", "skipped"],
      healthy: ["Hoạt động", "ok"],
      ok: ["Hoạt động", "ok"],
    };
    const [label, klass] = map[normalized] || [status ? String(status) : "Chưa rõ", "neutral"];
    return `<span class="pill pill--${klass}">${escapeHtml(label)}</span>`;
  }

  function riskPill(risk) {
    const value = String(risk || "").toLowerCase();
    if (!value) return '<span class="pill pill--neutral">—</span>';
    if (["low", "thấp", "safe"].includes(value)) return '<span class="pill pill--low">Thấp</span>';
    if (["high", "cao"].includes(value)) return '<span class="pill pill--high">Cao</span>';
    if (["medium", "mid", "moderate", "trung bình"].includes(value)) return '<span class="pill pill--medium">Trung bình</span>';
    return `<span class="pill pill--neutral">${escapeHtml(risk)}</span>`;
  }

  function safeLink(url, label = "Mở ↗") {
    if (!url || !/^https?:\/\//i.test(String(url))) return '<span class="muted">—</span>';
    return `<a class="evidence-link" href="${attr(url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(label)}</a>`;
  }

  function youtubeChannelUrl(channelId) {
    const value = String(channelId || "").trim();
    return /^UC[A-Za-z0-9_-]{20,}$/.test(value) ? `https://www.youtube.com/channel/${encodeURIComponent(value)}` : null;
  }

  function youtubeThumbnail(videoId) {
    const value = String(videoId || "").trim();
    return /^[A-Za-z0-9_-]{6,}$/.test(value) ? `https://i.ytimg.com/vi/${encodeURIComponent(value)}/hqdefault.jpg` : null;
  }

  function safeImage(url, alt, className = "") {
    if (!url || !/^https?:\/\//i.test(String(url))) return `<div class="media-placeholder ${attr(className)}" aria-hidden="true">◫</div>`;
    return `<img class="${attr(className)}" src="${attr(url)}" alt="${attr(alt || "Hình minh họa")}" loading="lazy" referrerpolicy="no-referrer">`;
  }

  function contentTypeLabel(value) {
    const normalized = String(value || "").toLowerCase();
    const labels = {
      factual_documentary: "Tài liệu / kiến thức",
      news_analysis: "Tin tức phân tích / giải thích",
      fiction: "Hư cấu",
      ai_storytelling: "Kể chuyện bằng AI",
      hybrid: "Kết hợp nhiều dạng",
      clip_compilation: "Tổng hợp clip",
      auto: "Tự động nhận diện",
      generic: "Tự động nhận diện",
    };
    return labels[normalized] || (value ? String(value) : "Tự động / chưa phân loại");
  }

  function containsKorean(value) {
    return /[\uac00-\ud7af]/.test(String(value || ""));
  }

  function translatedText(item) {
    return firstDefined(
      item?.title_vi,
      item?.translated_text,
      item?.translated_title,
      item?.translation_vi,
      item?.label_vi,
      item?.translated_label,
      item?.name_vi,
    );
  }

  function bilingualCopy(item, fallback = "Chưa có tiêu đề") {
    const original = firstDefined(item?.title_original, item?.original_text, item?.title, item?.label, item?.name, fallback);
    const translated = translatedText(item);
    const hasTranslation = translated && String(translated).trim() && String(translated).trim() !== String(original).trim();
    const translationLine = hasTranslation
      ? escapeHtml(translated)
      : containsKorean(original) ? "Chưa có bản dịch" : "";
    return `<div class="bilingual-copy"><strong class="bilingual-copy__original">${escapeHtml(original)}</strong>${translationLine ? `<span class="bilingual-copy__translation">${translationLine}</span>` : ""}</div>`;
  }

  function ageDuration(value) {
    if (!value) return "—";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "—";
    const days = Math.max(0, (Date.now() - date.getTime()) / 86_400_000);
    if (days < 30) return `${Math.max(1, Math.round(days))} ngày`;
    if (days < 365) return `${Math.max(1, Math.round(days / 30.4))} tháng`;
    return `${Math.max(1, Math.round(days / 365.25 * 10) / 10)} năm`;
  }

  async function api(path, options = {}) {
    const request = {
      method: options.method || "GET",
      headers: { Accept: "application/json", ...(options.headers || {}) },
      signal: options.signal,
    };
    if (options.body !== undefined) {
      request.headers["Content-Type"] = "application/json";
      request.body = JSON.stringify(options.body);
    }
    let response;
    try {
      response = await fetch(path, request);
    } catch (error) {
      if (error?.name === "AbortError") throw error;
      throw new ApiError("Không kết nối được tới API COFI RADAR.", 0, null);
    }
    const contentType = response.headers.get("content-type") || "";
    let payload = null;
    if (response.status !== 204) {
      if (contentType.includes("application/json")) {
        payload = await response.json().catch(() => null);
      } else {
        payload = await response.text().catch(() => null);
      }
    }
    if (!response.ok) {
      const detail = typeof payload === "object" ? firstDefined(payload?.detail, payload?.error, payload?.message) : payload;
      throw new ApiError(detail ? String(detail) : `API trả về HTTP ${response.status}.`, response.status, payload);
    }
    return payload;
  }

  async function apiFallback(paths, options = {}) {
    let lastError;
    for (const path of paths) {
      try {
        return await api(path, options);
      } catch (error) {
        lastError = error;
        if (!(error instanceof ApiError) || error.status !== 404) throw error;
      }
    }
    throw lastError;
  }

  function toast(message, type = "info") {
    const node = document.createElement("div");
    node.className = `toast toast--${type}`;
    node.textContent = message;
    els.toastRegion.appendChild(node);
    window.setTimeout(() => node.remove(), 4200);
  }

  function loadingState(message = "Đang tải dữ liệu thật từ COFI RADAR…") {
    return `<section class="card"><div class="state-panel"><div class="state-panel__inner"><div class="spinner" aria-hidden="true"></div><h3>Đang tải</h3><p>${escapeHtml(message)}</p></div></div></section>`;
  }

  function emptyState(title, message, actionHtml = "") {
    return `<section class="card"><div class="state-panel"><div class="state-panel__inner"><div class="state-icon" aria-hidden="true">○</div><h3>${escapeHtml(title)}</h3><p>${escapeHtml(message)}</p>${actionHtml}</div></div></section>`;
  }

  function errorState(error, retry = true) {
    const status = error?.status ? `HTTP ${error.status} · ` : "";
    return `<section class="card"><div class="state-panel"><div class="state-panel__inner"><div class="state-icon" aria-hidden="true">!</div><h3>Không tải được dữ liệu</h3><p>${escapeHtml(status + (error?.message || "Đã xảy ra lỗi không xác định."))}</p>${retry ? '<button class="button button--ghost" type="button" data-action="retry">Thử lại</button>' : ""}</div></div></section>`;
  }

  function staleNotice(timestamp, label = "Dữ liệu") {
    const info = freshness(timestamp);
    if (!info?.stale) return "";
    return `<div class="notice notice--warn"><span aria-hidden="true">◷</span><span><strong>${escapeHtml(label)} có thể đã cũ theo ngưỡng freshness ${STALE_AFTER_HOURS} giờ của giao diện.</strong> Lần cập nhật gần nhất: ${escapeHtml(relativeAge(timestamp))}. Hãy quét/làm mới trước khi ra quyết định.</span></div>`;
  }

  function pageHead(title, description, actions = "") {
    return `<div class="page-head"><div><h2>${escapeHtml(title)}</h2><p>${escapeHtml(description)}</p></div>${actions ? `<div class="page-actions">${actions}</div>` : ""}</div>`;
  }

  function parseRoute() {
    const raw = location.hash.replace(/^#\/?/, "").replace(/\/$/, "") || "dashboard";
    const route = ROUTES[raw] || ROUTES.dashboard;
    return route.canonical;
  }

  function updateChrome(route) {
    state.route = route;
    const meta = ROUTES[route] || ROUTES.dashboard;
    els.title.textContent = meta.title;
    document.title = `${meta.title} — COFI RADAR`;
    document.querySelectorAll(".nav-item").forEach((link) => {
      const active = link.dataset.route === route;
      link.classList.toggle("active", active);
      if (active) link.setAttribute("aria-current", "page");
      else link.removeAttribute("aria-current");
    });
    els.scanShortcut.hidden = route === "trend";
  }

  function updateApiState(ok, label) {
    els.apiState.classList.toggle("ok", ok === true);
    els.apiState.classList.toggle("error", ok === false);
    els.apiState.querySelector("span").textContent = label;
  }

  function updateScanner(scan) {
    els.scannerDot.className = "status-dot";
    if (!scan) {
      els.scannerState.textContent = "Chưa có dữ liệu quét gần nhất";
      els.scannerMarket.textContent = "—";
      els.scannerMeta.textContent = "API chưa cung cấp bản ghi quét gần nhất.";
      return;
    }
    const status = String(scan.status || "").toLowerCase();
    if (["failed", "error"].includes(status)) {
      els.scannerDot.classList.add("error");
      els.scannerState.textContent = "Lần quét lỗi";
    } else if (["running", "pending", "queued"].includes(status)) {
      els.scannerDot.classList.add("busy");
      els.scannerState.textContent = "Máy quét đang chạy";
    } else if (["completed", "complete", "done", "ready", "ok", "healthy"].includes(status)) {
      els.scannerDot.classList.add("ok");
      els.scannerState.textContent = status === "ready" ? "Máy quét sẵn sàng" : "Lần quét hoàn tất";
    } else {
      els.scannerState.textContent = status ? `Trạng thái: ${status}` : "Chưa có trạng thái";
    }
    els.scannerMarket.textContent = scan.market || "—";
    const when = firstDefined(scan.completed_at, scan.updated_at, scan.started_at, scan.created_at);
    els.scannerMeta.textContent = when ? `Lần quét gần nhất: ${relativeAge(when)}` : "Có bản ghi quét, chưa có thời gian cập nhật.";
  }

  function dashboardStats(data) {
    const counts = data?.counts || data?.stats || {};
    const latest = data?.latest_scan || data?.scan || null;
    const candidates = [
      ["Video đã lưu", firstDefined(counts.videos, counts.video_count, data?.videos_count), "Dữ liệu công khai đã lưu"],
      ["Ngách đã phân tích", firstDefined(counts.niches, counts.niche_count, data?.niches_count), "Điểm COFI RADAR, không phải số liệu YouTube"],
      ["Lần quét", firstDefined(counts.scans, counts.scan_count, data?.scans_count), latest ? `Gần nhất: ${relativeAge(firstDefined(latest.completed_at, latest.started_at))}` : "API chưa cung cấp lần quét gần nhất"],
      ["Kế hoạch", firstDefined(counts.plans, counts.plan_count, data?.plans_count), "Kế hoạch dựa trên bằng chứng đã lưu"],
      ["Kênh của tôi", firstDefined(counts.my_channels, counts.channels, data?.my_channels_count), "Kênh được thêm để theo dõi"],
    ];
    return candidates.map(([label, value, note]) => `<article class="stat-card"><div class="stat-label">${escapeHtml(label)}</div><div class="stat-value">${fmtNumber(value)}</div><div class="stat-note">${escapeHtml(note)}</div></article>`).join("");
  }

  function nicheRows(niches) {
    return niches.map((niche, index) => {
      const evidence = niche.evidence || {};
      const winningChannels = firstDefined(niche.winning_channels, evidence.winning_channels, evidence.small_winning_channels);
      const newChannels = firstDefined(niche.new_winning_channels, evidence.new_winning_channels);
      const winningVideos = firstDefined(niche.breakout_videos, niche.winning_videos, evidence.breakout_videos, evidence.winning_videos);
      const outlier = firstDefined(niche.median_outlier, evidence.median_outlier);
      return `<tr data-action="open-niche" data-id="${attr(niche.id)}" tabindex="0">
        <td>${String(index + 1).padStart(2, "0")}</td>
        <td><span class="cell-main">${escapeHtml(firstDefined(niche.label, niche.name, niche.key, "Ngách chưa đặt tên"))}</span><span class="cell-sub">${escapeHtml(firstDefined(niche.description, niche.key, "Điểm dẫn xuất từ bằng chứng đã lưu"))}</span></td>
        <td><span class="score-badge">${fmtScore(firstDefined(niche.score, niche.opportunity_score))}</span></td>
        <td class="num">${fmtNumber(winningChannels)}</td>
        <td class="positive">${fmtNumber(newChannels)}</td>
        <td class="num">${fmtNumber(winningVideos)}</td>
        <td class="positive">${fmtRatio(outlier)}</td>
        <td>${riskPill(firstDefined(niche.competition, niche.competition_level, niche.competition_risk))}</td>
        <td>${riskPill(firstDefined(niche.ypp_risk, niche.ypp))}</td>
        <td><button class="button button--small" type="button" data-action="open-niche" data-id="${attr(niche.id)}">Xem</button></td>
      </tr>`;
    }).join("");
  }

  function nicheCards(niches) {
    return `<div class="niche-card-grid">${niches.map((niche, index) => {
      const evidence = niche.evidence || {};
      const winningChannels = firstDefined(niche.winning_channels, evidence.winning_channels, evidence.small_winning_channels);
      const newChannels = firstDefined(niche.new_winning_channels, evidence.new_winning_channels);
      const winningVideos = firstDefined(niche.breakout_videos, niche.winning_videos, evidence.breakout_videos, evidence.winning_videos);
      const outlier = firstDefined(niche.median_outlier, evidence.median_outlier);
      const labelItem = {
        title: firstDefined(niche.label, niche.name, niche.key, "Ngách chưa đặt tên"),
        title_vi: firstDefined(niche.label_vi, niche.translated_label, niche.name_vi),
      };
      return `<article class="niche-card" data-action="open-niche" data-id="${attr(niche.id)}" tabindex="0">
        <div class="niche-card__top"><span class="niche-rank">#${String(index + 1).padStart(2, "0")}</span><span class="score-badge">${fmtScore(firstDefined(niche.score, niche.opportunity_score))}</span></div>
        ${bilingualCopy(labelItem, "Ngách chưa đặt tên")}
        <div class="niche-card__metrics">
          <div><span>Kênh đang thắng</span><strong>${fmtNumber(winningChannels)}</strong></div>
          <div><span>Kênh mới</span><strong>${fmtNumber(newChannels)}</strong></div>
          <div><span>Video bứt phá</span><strong>${fmtNumber(winningVideos)}</strong></div>
          <div><span>Outlier trung vị</span><strong>${fmtRatio(outlier)}</strong></div>
        </div>
        <div class="niche-card__footer"><span>Cạnh tranh ${riskPill(firstDefined(niche.competition, niche.competition_level, niche.competition_risk))}</span><span>YPP ${riskPill(firstDefined(niche.ypp_risk, niche.ypp))}</span><button class="button button--small" type="button" data-action="open-niche" data-id="${attr(niche.id)}">Phân tích sâu</button></div>
      </article>`;
    }).join("")}</div>`;
  }

  function isActionableNiche(niche) {
    const evidence = niche?.evidence || {};
    if (typeof evidence.actionable_niche === "boolean") return evidence.actionable_niche;
    const videos = Number(evidence.videos);
    const channels = Array.isArray(evidence.channel_proof)
      ? evidence.channel_proof.length
      : Number(firstDefined(evidence.winning_channels, evidence.channels));
    const confidence = Number(evidence.confidence);
    const longevity = Number(firstDefined(niche?.longevity, evidence.longevity));
    if (Number.isFinite(videos) && videos < 2) return false;
    if (Number.isFinite(channels) && channels < 2) return false;
    if (Number.isFinite(confidence) && confidence < 35) return false;
    if (Number.isFinite(longevity) && longevity < 25) return false;
    return true;
  }

  function actionableNiches(niches) {
    return niches.filter(isActionableNiche);
  }

  function nicheTable(niches, subtitle = "Dữ liệu thật từ lần quét gần nhất") {
    if (!niches.length) return emptyState("Chưa có ngách", "Hãy chạy Radar xu hướng trước. COFI RADAR sẽ không điền số minh họa vào bảng trống.", '<a class="button button--primary" href="#/trend">Mở Radar xu hướng</a>');
    return `<section class="card"><div class="card-head"><div><h3>Cơ hội ngách</h3><p>${escapeHtml(subtitle)}</p></div><span class="pill pill--neutral">${fmtNumber(niches.length)} ngách</span></div><div class="card-body">${nicheCards(niches)}</div></section>`;
  }

  async function renderDashboard(signal) {
    const data = await api("/api/dashboard", { signal });
    updateApiState(true, "Dịch vụ hoạt động");
    const latest = data?.latest_scan || data?.scan || null;
    updateScanner(latest);
    const niches = actionableNiches(arrayFrom(data?.top_niches || data?.niches || [], "top_niches", "niches"));
    const timestamp = firstDefined(latest?.completed_at, latest?.updated_at, data?.updated_at, data?.fetched_at);
    return `${pageHead("Bảng cơ hội", "Tổng hợp trạng thái quét, ngách và kế hoạch. Mọi con số hiển thị bên dưới phải đến từ API.")}
      ${staleNotice(timestamp, "Bảng tổng quan")}
      <section class="mode-grid" aria-label="Hai luồng vận hành">
        <article class="mode-card mode-card--active"><div class="mode-tag">Chế độ 01 · Bắt đầu từ số 0</div><h3>TÌM NGÁCH ĐỂ XÂY KÊNH MỚI</h3><p>Quét thị trường → xác minh kênh nhỏ/kênh mới → đánh giá rủi ro → lập kế hoạch dựa trên bằng chứng.</p><div class="flow"><span>Quét thị trường</span>→<span>Điểm ngách</span>→<span>Bằng chứng</span>→<span>30 video</span></div></article>
        <article class="mode-card"><div class="mode-tag">Chế độ 02 · Đã có kênh</div><h3>PHÁT TRIỂN KÊNH ĐANG CÓ</h3><p>Lưu kênh đang vận hành, dùng dữ liệu và bằng chứng hiện có để ưu tiên việc nên làm hôm nay.</p><div class="flow"><span>Kênh của tôi</span>→<span>Độ khớp</span>→<span>Hôm nay</span>→<span>Sản xuất</span></div></article>
      </section>
      <section class="stats-grid">${dashboardStats(data)}</section>
      ${nicheTable(niches, "Xếp theo dữ liệu API; điểm là chỉ số dẫn xuất của COFI RADAR")}`;
  }

  function scanForm() {
    return `<section class="card scan-card"><div class="card-head"><div><h3>Quét cơ hội thị trường</h3><p>Radar ưu tiên video đang tăng trên YouTube trước, sau đó mới tách chủ đề nóng và ngách đủ bền.</p></div></div><div class="card-body"><form id="scanForm">
      <div class="scan-mode-switch" role="radiogroup" aria-label="Chế độ quét">
        <label class="scan-mode-option"><input type="radio" name="scan_mode" value="market" checked><span><strong>Quét toàn thị trường</strong><small>Tìm video đang tăng, không cần từ khóa</small></span></label>
        <label class="scan-mode-option"><input type="radio" name="scan_mode" value="directed"><span><strong>Quét có định hướng</strong><small>Có thể thêm từ khóa để khoanh vùng nhanh hơn</small></span></label>
        <label class="scan-mode-option scan-mode-option--ai"><input type="radio" name="scan_mode" value="ai"><span><strong>Trend sản xuất bằng AI</strong><small>Ưu tiên trend có thể dựng bằng voice, ảnh/video AI, visual giải thích, motion hoặc Remotion/Codex.</small></span></label>
        <label class="scan-mode-option scan-mode-option--transformative"><input type="radio" name="scan_mode" value="transformative"><span><strong>Content + Footage</strong><small>Tìm trend phù hợp commentary/phân tích mới, dùng footage như bằng chứng hoặc minh họa thay vì reup nhẹ.</small></span></label>
      </div>
      <div class="form-grid">
        <div class="field"><label for="scanMarket">Thị trường</label><select id="scanMarket" name="market"><option value="KR">Hàn Quốc (KR)</option><option value="JP">Nhật Bản (JP)</option><option value="VN">Việt Nam (VN)</option><option value="US">Hoa Kỳ (US)</option></select></div>
        <div class="field"><label for="scanDays">Khoảng thời gian</label><select id="scanDays" name="days"><option value="2">48 giờ</option><option value="7" selected>7 ngày · khuyến nghị</option><option value="14">14 ngày</option><option value="30">30 ngày</option><option value="90">90 ngày</option></select></div>
        <div class="field"><label for="scanMaxVideos">Giới hạn video</label><input id="scanMaxVideos" name="max_videos" type="number" min="10" max="500" inputmode="numeric" value="60"><span class="field-help">60 video đủ để quét nhanh; tăng khi cần mở rộng bằng chứng.</span></div>
      </div>
      <div class="directed-scan-fields" id="directedScanFields" hidden>
        <div class="form-grid form-grid--two">
          <div class="field"><label for="scanContentType">Loại nội dung (tùy chọn)</label><select id="scanContentType" name="content_type"><option value="">Tự động nhận diện sau khi quét</option><option value="factual_documentary">Tài liệu / kiến thức</option><option value="news_analysis">Tin tức phân tích / giải thích</option><option value="fiction">Hư cấu</option><option value="ai_storytelling">Kể chuyện bằng AI</option><option value="hybrid">Kết hợp nhiều dạng</option><option value="clip_compilation">Tổng hợp clip</option></select></div>
          <div class="field"><label for="scanSeeds">Từ khóa hoặc chủ đề (tùy chọn)</label><textarea id="scanSeeds" name="seeds" placeholder="Mỗi dòng một từ khóa hoặc chủ đề"></textarea><span class="field-help">Để trống nếu chưa có ý tưởng. Khi quét không từ khóa, hệ thống tự khám phá bằng ngôn ngữ của thị trường.</span></div>
        </div>
      </div>
      <div id="scanProgress" class="notice" hidden><span aria-hidden="true">↻</span><span>Đang quét YouTube…</span></div>
      <div class="form-actions"><button class="button button--primary" id="scanSubmitButton" type="submit">QUÉT TOÀN THỊ TRƯỜNG</button></div>
    </form></div></section>`;
  }

  function scanRows(scans) {
    return scans.map((scan) => `<tr>
      <td class="num">${escapeHtml(firstDefined(scan.id, "—"))}</td>
      <td>${escapeHtml(firstDefined(scan.market, "—"))}</td>
      <td>${fmtNumber(scan.days)}</td>
      <td>${escapeHtml(Array.isArray(scan.seeds) && scan.seeds.length ? scan.seeds.join(", ") : firstDefined(scan.seeds_text, "Tự khám phá"))}</td>
      <td>${escapeHtml(contentTypeLabel(scan.content_type))}</td>
      <td>${statusPill(scan.status)}</td>
      <td>${fmtDate(firstDefined(scan.completed_at, scan.started_at, scan.created_at), true)}</td>
      <td>${scan.error ? `<span class="danger">${escapeHtml(scan.error)}</span>` : '<span class="muted">—</span>'}</td>
    </tr>`).join("");
  }

  async function renderTrend(signal) {
    const payload = await api("/api/scans", { signal });
    updateApiState(true, "Dịch vụ hoạt động");
    const scans = arrayFrom(payload, "scans");
    updateScanner(scans[0] || null);
    const latestMarketScan = scans.find((scan) => scan.kind === "market" || scan.market !== "channel");
    let trendVideos = [];
    if (latestMarketScan?.id) {
      try {
        trendVideos = arrayFrom(await api(`/api/scans/${encodeURIComponent(latestMarketScan.id)}/videos`, { signal }), "videos");
      } catch (error) {
        if (error?.name === "AbortError") throw error;
      }
    }
    const productionMode = String(firstDefined(latestMarketScan?.production_mode, latestMarketScan?.source_summary?.production_mode, "") || "").toLowerCase();
    const aiMode = productionMode === "ai";
    const transformativeMode = productionMode === "transformative";
    const rankedVideos = (aiMode || transformativeMode) ? [...trendVideos] : [...trendVideos].sort((left, right) => {
      const vph = Number(right?.vph || 0) - Number(left?.vph || 0);
      if (vph) return vph;
      const outlier = Number(right?.outlier || 0) - Number(left?.outlier || 0);
      if (outlier) return outlier;
      return Number(right?.views || 0) - Number(left?.views || 0);
    });
    const aiRecommended = aiMode ? rankedVideos.filter((video) => video?.ai_production_fit?.recommended === true) : [];
    const aiRejected = aiMode ? rankedVideos.filter((video) => video?.ai_production_fit?.recommended !== true) : [];
    const transformativeRecommended = transformativeMode ? rankedVideos.filter((video) => video?.transformative_fit?.recommended === true && video?.transformative_fit?.copyright_risk !== "high" && video?.transformative_fit?.production_recipe?.producer_ready === true) : [];
    const transformativeRejected = transformativeMode ? rankedVideos.filter((video) => !transformativeRecommended.includes(video)) : [];
    const signals = latestMarketScan ? (aiMode
      ? `${aiRecommended.length
          ? `<section class="card"><div class="card-head"><div><h3>Trend sản xuất được bằng AI</h3><p>Lần quét #${escapeHtml(latestMarketScan.id)} · chỉ đưa các trend đạt AI Fit ≥70 vào danh sách chính, đồng thời vẫn giữ VPH/Outlier trong xếp hạng.</p></div><span class="pill pill--ai">${fmtNumber(aiRecommended.length)} phù hợp</span></div><div class="card-body">${videoEvidence(aiRecommended)}</div></section>`
          : emptyState("Chưa có trend đạt AI Fit ≥70", `Lần quét #${latestMarketScan.id} có ${rankedVideos.length} video đang tăng nhưng chưa có chủ đề nào đủ phù hợp với pipeline AI hiện tại. Hãy quét lại sau hoặc mở rộng cửa sổ thời gian.`)}
        ${aiRejected.length ? `<div style="height:11px"></div><section class="card"><div class="card-head"><div><h3>Trend nóng nhưng khó sản xuất bằng AI</h3><p>Các video này vẫn có tín hiệu tăng, nhưng giá trị hiện tại phụ thuộc nhiều hơn vào footage/chương trình/khoảnh khắc gốc hoặc chưa đủ tín hiệu AI-production.</p></div><span class="pill pill--neutral">${fmtNumber(aiRejected.length)} tham khảo</span></div><div class="card-body">${videoEvidence(aiRejected.slice(0, 5))}</div></section>` : ""}`
      : transformativeMode
        ? `${transformativeRecommended.length
            ? `<section class="card"><div class="card-head"><div><h3>Trend phù hợp Content + Footage</h3><p>Lần quét #${escapeHtml(latestMarketScan.id)} · chỉ đưa trend Transformative Fit ≥70 và không ở mức copyright risk cao vào danh sách chính.</p></div><span class="pill pill--transformative">${fmtNumber(transformativeRecommended.length)} phù hợp</span></div><div class="card-body">${videoEvidence(transformativeRecommended)}</div></section>`
            : emptyState("Chưa có trend Transformative đủ an toàn để ưu tiên", `Lần quét #${latestMarketScan.id} có ${rankedVideos.length} video đang tăng nhưng chưa có video nào đồng thời đạt Transformative Fit ≥70 và tránh mức copyright risk cao.`)}
          <div class="notice notice--warn"><span aria-hidden="true">!</span><span><strong>Đây là heuristic sản xuất, không phải kết luận fair use.</strong> Reused content/YPP và copyright là hai lớp đánh giá khác nhau; quyền sử dụng vẫn phải được kiểm tra cho từng nguồn.</span></div>
          ${transformativeRejected.length ? `<div style="height:11px"></div><section class="card"><div class="card-head"><div><h3>Trend nóng nhưng rủi ro cao / ít giá trị biến đổi</h3><p>Giữ để tham khảo, không tự động coi là cơ hội sản xuất. Có thể phụ thuộc highlight, chương trình, màn trình diễn hoặc chưa cho thấy phần commentary mới đủ mạnh.</p></div><span class="pill pill--neutral">${fmtNumber(transformativeRejected.length)} tham khảo</span></div><div class="card-body">${videoEvidence(transformativeRejected.slice(0, 5))}</div></section>` : ""}`
      : `<section class="card"><div class="card-head"><div><h3>Video đang chạy</h3><p>Tín hiệu thô từ lần quét #${escapeHtml(latestMarketScan?.id)} · xếp theo VPH, sau đó Outlier. Đây là nơi xem trend trước khi gọi một chủ đề là ngách.</p></div><span class="pill pill--neutral">${fmtNumber(rankedVideos.length)} video</span></div><div class="card-body">${videoEvidence(rankedVideos)}</div></section>`)
      : "";
    const history = scans.length
      ? `<section class="card"><div class="card-head"><div><h3>Lịch sử quét</h3><p>Trạng thái và lỗi được lấy trực tiếp từ máy chủ.</p></div><span class="pill pill--neutral">${fmtNumber(scans.length)} bản ghi</span></div><div class="table-wrap"><table><thead><tr><th>ID</th><th>Thị trường</th><th>Ngày</th><th>Từ khóa</th><th>Loại nội dung</th><th>Trạng thái</th><th>Thời gian</th><th>Lỗi</th></tr></thead><tbody>${scanRows(scans)}</tbody></table></div></section>`
      : emptyState("Chưa có lần quét", "Điền cấu hình phía trên để tạo lần quét đầu tiên. Không có lịch sử demo.");
    return `${pageHead("Radar xu hướng", "Xem video đang tăng trước, rồi mới xác minh chủ đề nào đủ bằng chứng để trở thành ngách.")}${scanForm()}${signals ? `<div style="height:11px"></div>${signals}` : ""}<div style="height:11px"></div>${history}`;
  }

  function nicheDetailMetrics(niche) {
    const evidence = niche?.evidence || {};
    return [
      ["Nhu cầu", firstDefined(niche?.demand, evidence.demand)],
      ["Kênh nhỏ", firstDefined(niche?.small_channel_proof, evidence.small_channel_proof)],
      ["Kênh mới", firstDefined(niche?.new_channel_proof, evidence.new_channel_proof)],
      ["Độ mở cạnh tranh", firstDefined(niche?.competition_openness, evidence.competition_openness)],
      ["Lặp lại", firstDefined(niche?.repeatability, evidence.repeatability)],
      ["Độ bền", firstDefined(niche?.longevity, evidence.longevity)],
    ].map(([label, value]) => `<div class="metric-box"><span>${escapeHtml(label)}</span><strong>${fmtScore(value)}</strong></div>`).join("");
  }

  function channelEvidence(channels) {
    if (!channels.length) return '<p class="muted">Chưa có bằng chứng kênh cho ngách này.</p>';
    return `<div class="evidence-card-list">${channels.slice(0, 8).map((channel) => {
      const winRateRaw = firstDefined(channel.win_rate, channel.evidence?.win_rate);
      const winRate = Number(winRateRaw);
      const winRateLabel = Number.isFinite(winRate) ? `${Math.round((winRate <= 1 ? winRate * 100 : winRate) * 10) / 10}%` : "—";
      const avatar = firstDefined(channel.thumbnail_url, channel.avatar_url, channel.avatar);
      return `<article class="evidence-card evidence-card--channel">
        <div class="evidence-card__avatar">${safeImage(avatar, firstDefined(channel.title, channel.name, "Ảnh kênh"), "evidence-avatar")}</div>
        <div class="evidence-card__body">
          <strong class="evidence-card__title">${escapeHtml(firstDefined(channel.title, channel.name, channel.label, channel.id, "Kênh"))}</strong>
          <div class="evidence-card__metrics"><span>Người đăng ký <b>${fmtCompact(firstDefined(channel.subscribers, channel.subscriber_count))}</b></span><span>Tuổi kênh <b>${ageDuration(channel.published_at)}</b></span><span>Tổng video <b>${fmtNumber(firstDefined(channel.total_videos, channel.video_count))}</b></span><span>Video thắng <b>${fmtNumber(firstDefined(channel.win_count, channel.evidence?.win_count))}</b></span><span>Tỷ lệ thắng <b>${winRateLabel}</b></span><span>Outlier trung vị <b>${fmtRatio(firstDefined(channel.median_outlier, channel.evidence?.median_outlier))}</b></span></div>
          <div class="evidence-card__actions">${safeLink(firstDefined(channel.url, channel.channel_url), "Mở kênh ↗")}</div>
        </div>
      </article>`;
    }).join("")}</div>`;
  }

  function videoEvidence(videos) {
    if (!videos.length) return '<p class="muted">Chưa có video bằng chứng cho ngách này.</p>';
    const aiBandLabels = { very_high: "Rất phù hợp", high: "Phù hợp", medium: "Cân nhắc", low: "Khó phù hợp" };
    const transformativeBandLabels = { very_high: "Rất phù hợp", high: "Phù hợp", medium: "Cần biến đổi thêm", low: "Không ưu tiên" };
    return `<div class="evidence-card-list">${videos.slice(0, 10).map((video) => {
      const fit = video?.ai_production_fit;
      const fitReasons = Array.isArray(fit?.reasons) ? fit.reasons.slice(0, 2) : [];
      const fitBlock = fit && typeof fit === "object"
        ? `<div class="ai-fit ${fit.recommended ? "ai-fit--recommended" : ""}"><div class="ai-fit__top"><strong>AI Fit ${fmtScore(fit.score)}</strong><span>${escapeHtml(aiBandLabels[fit.band] || "Đang đánh giá")}</span></div>${fitReasons.length ? `<p>${escapeHtml(fitReasons.join(" · "))}</p>` : ""}</div>`
        : "";
      const transformativeFit = video?.transformative_fit;
      const transformativeReasons = Array.isArray(transformativeFit?.reasons) ? transformativeFit.reasons.slice(0, 2) : [];
      const productionFormat = transformativeFit?.production_recipe?.recommended_format;
      const transformativeBlock = transformativeFit && typeof transformativeFit === "object"
        ? `<div class="transformative-fit ${transformativeFit?.production_recipe?.producer_ready ? "transformative-fit--recommended" : ""}"><div class="transformative-fit__top"><strong>Transformative Fit ${fmtScore(transformativeFit.score)}</strong><span>${escapeHtml(transformativeBandLabels[transformativeFit.band] || "Đang đánh giá")}</span></div><div class="transformative-fit__meta"><span>Copyright risk <b>${escapeHtml(String(transformativeFit.copyright_risk || "unknown").toUpperCase())}</b></span><span>Reused risk <b>${escapeHtml(String(transformativeFit.reused_content_risk || "unknown").toUpperCase())}</b></span>${productionFormat ? `<span>Format <b>${escapeHtml(productionFormat)}</b></span>` : ""}</div>${transformativeReasons.length ? `<p>${escapeHtml(transformativeReasons.join(" · "))}</p>` : ""}</div>`
        : "";
      return `<article class="evidence-card">
      <div class="evidence-card__thumb">${safeImage(firstDefined(video.thumbnail_url, youtubeThumbnail(firstDefined(video.id, video.video_id))), firstDefined(video.title_original, video.title, "Thumbnail video"), "evidence-thumb")}</div>
      <div class="evidence-card__body">
        ${bilingualCopy(video, "Video")}
        <span class="evidence-card__channel">${escapeHtml(firstDefined(video.channel_title, video.channel_name, "Kênh chưa rõ"))}</span>
        <div class="evidence-card__metrics"><span>Lượt xem <b>${fmtCompact(video.views)}</b></span><span>VPH <b>${fmtCompact(video.vph)}</b></span><span>Outlier <b>${fmtRatio(video.outlier)}</b></span><span>Đăng <b>${escapeHtml(relativeAge(video.published_at))}</b></span></div>
        ${fitBlock}
        ${transformativeBlock}
        <div class="evidence-card__actions">${safeLink(firstDefined(video.url, video.video_url), "Mở video ↗")}</div>
      </div>
    </article>`;
    }).join("")}</div>`;
  }

  function yppAssessmentPanel(niche) {
    const ypp = firstDefined(niche?.evidence?.ypp, niche?.ypp);
    if (!ypp || typeof ypp !== "object") {
      return '<section class="detail-section"><h4>YPP · lớp cảnh báo</h4><p class="muted">Chưa có dữ liệu đánh giá YPP chi tiết cho ngách này.</p></section>';
    }
    const labels = {
      originality_authenticity: "Nguyên bản / xác thực",
      reused_content: "Tái sử dụng / biến đổi",
      ad_suitability: "Phù hợp quảng cáo",
      synthetic_disclosure: "Khai báo AI chân thực",
    };
    const dimensions = Object.entries(ypp.dimensions || {}).map(([key, item]) => {
      const reasons = Array.isArray(item?.reasons) ? item.reasons.slice(0, 2) : [];
      return `<article class="ypp-dimension"><div class="ypp-dimension__top"><strong>${escapeHtml(labels[key] || key)}</strong>${riskPill(item?.risk)}</div><div class="ypp-score">${fmtScore(item?.risk_score)}/100${item?.action_required ? ' · <span class="danger">Cần xử lý</span>' : ""}</div>${reasons.length ? `<ul>${reasons.map((reason) => `<li>${escapeHtml(reason)}</li>`).join("")}</ul>` : '<p class="muted">Chưa có cảnh báo cụ thể.</p>'}</article>`;
    }).join("");
    const coverage = Number(ypp.signal_coverage);
    const coverageLabel = Number.isFinite(coverage) ? `${Math.round(Math.max(0, Math.min(1, coverage)) * 100)}% tín hiệu` : "Chưa rõ độ phủ";
    const stateLabels = {
      insufficient_signals: "Chưa đủ tín hiệu để kết luận",
      partial: "Đánh giá một phần",
      assessed: "Đã có đủ tín hiệu chính",
    };
    const assessmentLabel = stateLabels[ypp.assessment_state] || "Đánh giá tham khảo";
    const warning = ypp.assessment_state === "insufficient_signals"
      ? '<div class="notice notice--warn"><span aria-hidden="true">!</span><span>Điểm YPP đang ở mức trung tính vì chưa có đủ tín hiệu thực tế. Cần rà soát cách sản xuất trước khi dùng nó để quyết định xây kênh.</span></div>'
      : "";
    return `<section class="detail-section"><h4>YPP · lớp cảnh báo</h4>${warning}<div class="ypp-meta"><span>${escapeHtml(assessmentLabel)}</span><span>${escapeHtml(coverageLabel)}</span><span>Rà soát chính sách: ${escapeHtml(firstDefined(ypp.policy_reviewed_at, "—"))}</span></div><div class="ypp-grid">${dimensions}</div><p class="ypp-note">${escapeHtml(firstDefined(ypp.note, "Đây là đánh giá tham khảo, không phải quyết định của YouTube."))}</p></section>`;
  }

  function nicheDetailPanel(niche, videos, channels, detailErrors = {}) {
    if (!niche) return `<aside class="detail-panel"><div class="state-panel"><div class="state-panel__inner"><div class="state-icon">↗</div><h3>Chọn một ngách</h3><p>Chọn hàng trong bảng để mở bằng chứng kênh/video và hành động lập 30 video.</p></div></div></aside>`;
    const timestamp = firstDefined(niche.updated_at, niche.created_at, videos[0]?.fetched_at, channels[0]?.fetched_at);
    const errorNotices = [
      detailErrors.channels ? `<div class="notice notice--error"><span aria-hidden="true">!</span><span>Không tải được bằng chứng kênh: ${escapeHtml(detailErrors.channels.message || "Lỗi API")}</span></div>` : "",
      detailErrors.videos ? `<div class="notice notice--error"><span aria-hidden="true">!</span><span>Không tải được bằng chứng video: ${escapeHtml(detailErrors.videos.message || "Lỗi API")}</span></div>` : "",
    ].join("");
    return `<aside class="detail-panel" aria-label="Chi tiết ngách"><div class="detail-panel__head"><span class="eyebrow">Phân tích cơ hội</span><h3>${escapeHtml(firstDefined(niche.label, niche.name, niche.key, "Ngách"))}</h3><p>Điểm COFI RADAR là chỉ số dẫn xuất; số liệu nguồn giữ theo bản ghi API.</p><div class="metric-grid"><div class="metric-box"><span>Điểm cơ hội</span><strong>${fmtScore(firstDefined(niche.score, niche.opportunity_score))}</strong></div><div class="metric-box"><span>YPP</span><strong>${escapeHtml(firstDefined(niche.ypp_risk, "—"))}</strong></div><div class="metric-box"><span>Cập nhật</span><strong>${escapeHtml(relativeAge(timestamp))}</strong></div></div><div class="metric-grid">${nicheDetailMetrics(niche)}</div></div>
      <div class="detail-panel__body">${staleNotice(timestamp, "Bằng chứng ngách")}${errorNotices}${yppAssessmentPanel(niche)}<section class="detail-section"><h4>Kênh đang hỗ trợ bằng chứng</h4>${channelEvidence(channels)}</section><section class="detail-section"><h4>Video đang hỗ trợ bằng chứng</h4>${videoEvidence(videos)}</section></div>
      <div class="detail-panel__footer"><button class="button" type="button" data-action="save-niche-evidence" data-id="${attr(niche.id)}">Lưu bằng chứng</button><button class="button button--primary" type="button" data-action="build-plan" data-id="${attr(niche.id)}">Xây kênh → 30 video</button></div></aside>`;
  }

  async function loadNicheDetail(id, signal) {
    const [nicheResult, videosResult, channelsResult] = await Promise.allSettled([
      api(`/api/niches/${encodeURIComponent(id)}`, { signal }),
      api(`/api/niches/${encodeURIComponent(id)}/videos`, { signal }),
      api(`/api/niches/${encodeURIComponent(id)}/channels`, { signal }),
    ]);
    if (nicheResult.status === "rejected") throw nicheResult.reason;
    return {
      niche: nicheResult.value,
      videos: videosResult.status === "fulfilled" ? arrayFrom(videosResult.value, "videos") : [],
      channels: channelsResult.status === "fulfilled" ? arrayFrom(channelsResult.value, "channels") : [],
      errors: {
        videos: videosResult.status === "rejected" ? videosResult.reason : null,
        channels: channelsResult.status === "rejected" ? channelsResult.reason : null,
      },
    };
  }

  async function renderNiches(signal) {
    const payload = await api("/api/niches", { signal });
    updateApiState(true, "Dịch vụ hoạt động");
    const allNiches = arrayFrom(payload, "niches");
    const niches = actionableNiches(allNiches);
    const hiddenRawTrends = Math.max(0, allNiches.length - niches.length);
    if (!niches.length) {
      const rawNote = hiddenRawTrends ? `<div class="notice notice--warn"><span>!</span><span>${fmtNumber(hiddenRawTrends)} chủ đề nóng đã được giữ ở Radar nhưng chưa đủ độ bền/bằng chứng để gọi là ngách.</span></div>` : "";
      return `${pageHead("Phòng thí nghiệm ngách", "Chỉ giữ các cơ hội đã vượt qua lớp kiểm tra độ bền và bằng chứng.")}${rawNote}${emptyState("Chưa có ngách đủ bằng chứng", "Mở Radar để xem các video đang tăng hoặc quét thêm dữ liệu. Hệ thống không nâng một sự kiện nóng đơn lẻ thành ngách.", '<a class="button button--primary" href="#/trend">Mở Radar xu hướng</a>')}`;
    }
    if (!state.selectedNicheId || !niches.some((item) => String(item.id) === String(state.selectedNicheId))) state.selectedNicheId = niches[0].id;
    let detail = { niche: niches[0], videos: [], channels: [], errors: {} };
    try { detail = await loadNicheDetail(state.selectedNicheId, signal); }
    catch (error) {
      detail = { niche: niches.find((item) => String(item.id) === String(state.selectedNicheId)) || niches[0], videos: [], channels: [], errors: {} };
      if (error?.name !== "AbortError") toast(`Không tải đủ chi tiết ngách: ${error.message}`, "error");
    }
    const rawNote = hiddenRawTrends ? `<div class="notice"><span>i</span><span>Đã ẩn ${fmtNumber(hiddenRawTrends)} chủ đề nóng/ngắn hạn khỏi danh sách ngách. Chúng vẫn còn trong Radar để theo dõi trend.</span></div><div style="height:11px"></div>` : "";
    return `${pageHead("Phòng thí nghiệm ngách", "Chỉ so sánh các cơ hội đã có đủ tín hiệu để cân nhắc xây kênh.")}${rawNote}<div class="layout-split"><div>${nicheTable(niches, "Đã qua lớp kiểm tra bằng chứng và độ bền")}</div>${nicheDetailPanel(detail.niche, detail.videos, detail.channels, detail.errors)}</div>`;
  }

  function channelKey(channel) {
    return String(firstDefined(channel?.channel_id, channel?.id, channel?.url, channel?.channel_url, ""));
  }

  function channelProfileSummary(channel) {
    const dna = channel?.dna && typeof channel.dna === "object" ? channel.dna : {};
    const winRate = Number.isFinite(Number(dna.win_rate)) ? `${Math.round(Number(dna.win_rate) * 100)}%` : "—";
    if (!dna.sampled_videos) return "Chưa đủ dữ liệu DNA";
    return `${fmtNumber(dna.sampled_videos)} video DNA · ${winRate} thắng · momentum ${fmtNumber(dna.momentum)}/100`;
  }

  function channelProfileDialogHtml(channel) {
    const dna = channel?.dna && typeof channel.dna === "object" ? channel.dna : {};
    const winnerTerms = Array.isArray(dna.winner_terms) ? dna.winner_terms.slice(0, 12) : [];
    const winnerTitles = Array.isArray(dna.winner_titles) ? dna.winner_titles.slice(0, 5) : [];
    const winRate = Number.isFinite(Number(dna.win_rate)) ? `${Math.round(Number(dna.win_rate) * 100)}%` : "—";
    const id = channelKey(channel);
    const youtubeUrl = firstDefined(channel.url, channel.channel_url, youtubeChannelUrl(channel.channel_id));
    const sourceLabel = firstDefined(channel.label, channel.title, channel.name, channel.channel_id, "Kênh");
    const dnaBody = dna.sampled_videos
      ? `<section class="channel-profile-dialog__section">
          <h3>DNA kênh</h3>
          <div class="channel-profile-dialog__stats">
            <div><span>Video đã đọc</span><strong>${fmtNumber(dna.sampled_videos)}</strong></div>
            <div><span>Video thắng</span><strong>${fmtNumber(dna.win_count)}</strong></div>
            <div><span>Tỷ lệ thắng</span><strong>${winRate}</strong></div>
            <div><span>Momentum</span><strong>${fmtNumber(dna.momentum)}/100</strong></div>
          </div>
          ${winnerTerms.length ? `<div class="channel-profile-dialog__copy"><strong>Cụm từng thắng</strong><p>${escapeHtml(winnerTerms.join(" · "))}</p></div>` : ""}
          ${winnerTitles.length ? `<div class="channel-profile-dialog__copy"><strong>Ví dụ video thắng</strong><div class="channel-profile-winners">${winnerTitles.map((item, index) => `<article><span>${String(index + 1).padStart(2, "0")}</span><div><b>${escapeHtml(firstDefined(item?.title, "Video thắng"))}</b><small>${fmtCompact(item?.views)} lượt xem · ${fmtRatio(item?.outlier)} Outlier</small></div></article>`).join("")}</div></div>` : ""}
          ${dna.limitation ? `<div class="notice notice--warn channel-profile-dialog__notice"><span>!</span><span>${escapeHtml(dna.limitation)}</span></div>` : ""}
        </section>`
      : `<section class="channel-profile-dialog__section"><h3>DNA kênh</h3><p class="channel-profile-dialog__empty">Chưa đủ lịch sử video công khai để tạo hồ sơ DNA chi tiết.</p></section>`;
    return `<div class="channel-profile-dialog__overview">
        <div class="channel-profile-dialog__identity">
          ${safeImage(firstDefined(channel.thumbnail_url, channel.avatar_url), sourceLabel, "channel-profile-dialog__avatar")}
          <div><strong>${escapeHtml(sourceLabel)}</strong><span>${escapeHtml(contentTypeLabel(channel.content_type))}</span></div>
        </div>
        ${statusPill(channel.status)}
      </div>
      <div class="channel-profile-dialog__stats channel-profile-dialog__stats--main">
        <div><span>Người đăng ký</span><strong>${fmtCompact(firstDefined(channel.subscribers, channel.subscriber_count))}</strong></div>
        <div><span>Tổng video</span><strong>${fmtNumber(firstDefined(channel.video_count, channel.total_videos))}</strong></div>
        <div><span>Tuổi kênh</span><strong>${escapeHtml(ageDuration(channel.published_at))}</strong></div>
        <div><span>Lần quét</span><strong>${fmtDate(firstDefined(channel.last_scan_at, channel.fetched_at), true)}</strong></div>
      </div>
      ${dnaBody}
      <div class="channel-profile-dialog__actions">
        ${youtubeUrl ? `<a class="button button--ghost" href="${attr(youtubeUrl)}" target="_blank" rel="noopener noreferrer">Mở YouTube ↗</a>` : ""}
        <button class="button button--primary" type="button" data-action="open-channel-plan" data-id="${attr(id)}">Lập 30 video</button>
        <button class="button button--ghost" type="button" data-action="open-channel-today" data-id="${attr(id)}">Mở Hôm nay</button>
      </div>`;
  }

  function openChannelProfile(channelId) {
    const channel = state.channels.find((item) => channelKey(item) === String(channelId));
    if (!channel || !els.channelProfileDialog || !els.channelProfileDialogBody) return;
    state.selectedChannelId = channelKey(channel);
    els.channelProfileDialogTitle.textContent = firstDefined(channel.label, channel.title, channel.name, channel.channel_id, "Hồ sơ kênh");
    els.channelProfileDialogBody.innerHTML = channelProfileDialogHtml(channel);
    if (!els.channelProfileDialog.open) els.channelProfileDialog.showModal();
  }

  function closeChannelProfileDialog() {
    if (els.channelProfileDialog?.open) els.channelProfileDialog.close();
  }

  function channelCards(channels) {
    if (!channels.length) return emptyState("Chưa có kênh của tôi", "Thêm URL hoặc ID kênh để hệ thống lưu kênh và dùng cho luồng Hôm nay.");
    return `<div class="channel-grid">${channels.map((channel) => {
      const id = channelKey(channel);
      return `<article class="mini-card channel-profile-card" tabindex="0" role="button" data-action="open-channel-profile" data-id="${attr(id)}" aria-label="Mở hồ sơ ${attr(firstDefined(channel.label, channel.title, channel.name, channel.channel_id, "kênh"))}"><div class="mini-card__top"><div class="channel-card-heading">${safeImage(firstDefined(channel.thumbnail_url, channel.avatar_url), firstDefined(channel.label, channel.title, "Ảnh kênh"), "channel-card-avatar")}<div><h3>${escapeHtml(firstDefined(channel.label, channel.title, channel.name, channel.channel_id, "Kênh"))}</h3><p>${escapeHtml(contentTypeLabel(channel.content_type))}</p></div></div>${statusPill(channel.status)}</div><dl><div><dt>Người đăng ký</dt><dd>${fmtCompact(firstDefined(channel.subscribers, channel.subscriber_count))}</dd></div><div><dt>Tổng video</dt><dd>${fmtNumber(firstDefined(channel.video_count, channel.total_videos))}</dd></div><div><dt>Tuổi kênh</dt><dd>${escapeHtml(ageDuration(channel.published_at))}</dd></div><div><dt>Lần quét</dt><dd>${fmtDate(firstDefined(channel.last_scan_at, channel.fetched_at), true)}</dd></div></dl><div class="channel-profile-card__summary">${escapeHtml(channelProfileSummary(channel))}</div><div class="channel-profile-card__hint">Bấm để xem hồ sơ chi tiết →</div></article>`;
    }).join("")}</div>`;
  }

  async function renderChannels(signal) {
    const payload = await api("/api/my-channels", { signal });
    updateApiState(true, "Dịch vụ hoạt động");
    const channels = arrayFrom(payload, "channels", "my_channels");
    state.channels = channels;
    return `${pageHead("Kênh của tôi", "Lưu các kênh bạn vận hành để dùng làm ngữ cảnh cho kế hoạch và hàng đợi Hôm nay.")}
      <section class="card"><div class="card-head"><div><h3>Thêm kênh</h3><p>Máy chủ sẽ xác minh và lưu dữ liệu công khai khi nguồn hỗ trợ.</p></div></div><div class="card-body"><form id="channelForm"><div class="form-grid"><div class="field field--wide"><label for="channelRef">URL hoặc ID kênh</label><input id="channelRef" name="channel_ref" required placeholder="https://www.youtube.com/@... hoặc UC..."></div><div class="field"><label for="channelLabel">Nhãn nội bộ</label><input id="channelLabel" name="label" placeholder="Tên kênh của tôi"></div><div class="field"><label for="channelType">Loại nội dung</label><select id="channelType" name="content_type"><option value="factual_documentary">Tài liệu / kiến thức</option><option value="news_analysis">Tin tức phân tích / giải thích</option><option value="fiction">Hư cấu</option><option value="ai_storytelling">Kể chuyện bằng AI</option><option value="hybrid">Kết hợp nhiều dạng</option><option value="clip_compilation">Tổng hợp clip</option></select></div></div><div class="form-actions"><button class="button button--primary" type="submit">Thêm kênh</button></div></form></div></section>
      <div style="height:11px"></div>${channelCards(channels)}`;
  }

  function planCards(plans) {
    if (!plans.length) return emptyState("Chưa có kế hoạch", "Chọn một ngách có bằng chứng rồi tạo kế hoạch. Nếu bằng chứng chỉ đủ cho ít hơn 30 chủ đề, giao diện sẽ giữ đúng số được hệ thống hỗ trợ.");
    return `<div class="plan-grid">${plans.map((plan) => `<article class="mini-card"><div class="mini-card__top"><div><h3>${escapeHtml(firstDefined(plan.niche_label, plan.label, `Kế hoạch #${firstDefined(plan.id, "—")}`))}</h3><p>Tạo ${fmtDate(firstDefined(plan.created_at, plan.updated_at), true)}</p></div><span class="score-badge">${fmtNumber(firstDefined(plan.supported_count, plan.items_count))}</span></div><dl><div><dt>Yêu cầu</dt><dd>${fmtNumber(plan.requested_count)}</dd></div><div><dt>Đủ bằng chứng</dt><dd>${fmtNumber(firstDefined(plan.supported_count, plan.items_count))}</dd></div><div><dt>ID ngách</dt><dd>${escapeHtml(firstDefined(plan.niche_id, "—"))}</dd></div><div><dt>Kênh</dt><dd>${escapeHtml(firstDefined(plan.my_channel_id, "—"))}</dd></div></dl>${plan.evidence_gap ? `<div class="notice notice--warn" style="margin:10px 0 0"><span>!</span><span>${escapeHtml(plan.evidence_gap)}</span></div>` : ""}<div class="mini-card__actions"><button class="button button--small" type="button" data-action="build-today" data-id="${attr(plan.id)}">Đưa vào Hôm nay</button></div></article>`).join("")}</div>`;
  }

  function planItemRows(items) {
    return items.map((item, index) => {
      const channelId = firstDefined(item.evidence_channel_id, item.channel_id);
      const sourceAge = item.evidence_published_at ? `${fmtDate(item.evidence_published_at, true)} · ${relativeAge(item.evidence_published_at)}` : "Không có ngày đăng";
      const fit = Number(firstDefined(item.channel_fit, 0));
      const fitClass = fit >= 60 ? "positive" : fit >= 30 ? "warning" : "muted";
      const evidenceVideoId = firstDefined(item.evidence_video_id, item.video_id);
      const evidenceItem = {
        title: firstDefined(item.evidence_title, "Bằng chứng"),
        title_original: firstDefined(item.evidence_title_original, item.evidence_title),
        title_vi: firstDefined(item.evidence_title_vi, item.translated_evidence_title),
      };
      return `<tr>
        <td class="num">${fmtNumber(firstDefined(item.position, index + 1))}</td>
        <td><span class="cell-main plan-topic">${escapeHtml(firstDefined(item.topic_anchor, item.title, "Chủ đề"))}</span>${item.production_brief ? `<span class="cell-sub">${escapeHtml(item.production_brief)}</span>` : ""}</td>
        <td><div class="plan-evidence-wrap"><div class="plan-evidence-thumb">${safeImage(youtubeThumbnail(evidenceVideoId), firstDefined(item.evidence_title, "Thumbnail bằng chứng"), "plan-thumb")}</div><div>${bilingualCopy(evidenceItem, "Bằng chứng")}<span class="cell-sub">${escapeHtml(sourceAge)}</span><span class="cell-sub">${safeLink(firstDefined(item.evidence_url, item.url), "Mở video bằng chứng ↗")}</span></div></div></td>
        <td><span class="cell-main">${escapeHtml(channelId || "—")}</span><span class="cell-sub">${safeLink(youtubeChannelUrl(channelId), "Mở kênh ↗")}</span></td>
        <td class="num">${fmtCompact(item.evidence_views)}</td>
        <td class="num">${fmtCompact(item.evidence_vph)}</td>
        <td class="num">${fmtRatio(item.evidence_outlier)}</td>
        <td><span class="${fitClass}">${fmtScore(fit)}/100</span>${item.note ? `<span class="cell-sub plan-fit-reason">${escapeHtml(item.note)}</span>` : ""}</td>
        <td>${statusPill(item.status)}</td>
      </tr>`;
    }).join("");
  }

  function planItemPanels(plans, itemResults) {
    if (!plans.length) return "";
    return `<div class="plan-detail-list">${plans.map((plan, index) => {
      const result = itemResults[index];
      const items = result?.status === "fulfilled" ? arrayFrom(result.value, "items") : [];
      const label = firstDefined(plan.niche_label, plan.label, `Kế hoạch #${plan.id}`);
      const body = result?.status === "rejected"
        ? `<div class="notice notice--warn"><span>!</span><span>Không tải được chủ đề của kế hoạch #${escapeHtml(plan.id)}: ${escapeHtml(result.reason?.message || "Lỗi không xác định")}</span></div>`
        : items.length
          ? `<div class="table-wrap plan-items-table"><table><thead><tr><th>#</th><th>Chủ đề sản xuất</th><th>Bằng chứng gốc / độ mới</th><th>Kênh nguồn</th><th>Lượt xem</th><th>VPH</th><th>Outlier</th><th>Độ khớp kênh / vì sao</th><th>Trạng thái</th></tr></thead><tbody>${planItemRows(items)}</tbody></table></div>`
          : `<div class="muted">Kế hoạch này chưa có item được lưu.</div>`;
      return `<details class="plan-details" ${index === 0 ? "open" : ""}><summary><span><strong>${escapeHtml(label)}</strong><small>Kế hoạch #${escapeHtml(plan.id)} · ${fmtNumber(items.length)} chủ đề · ${fmtDate(firstDefined(plan.created_at, plan.updated_at), true)}</small></span><span class="score-badge">${fmtNumber(firstDefined(plan.supported_count, plan.items_count, items.length))}</span></summary><div class="plan-details__body"><div class="plan-details__meta"><span>Kênh tham chiếu: <strong>${escapeHtml(firstDefined(plan.my_channel_id, "Kênh mới"))}</strong></span><button class="button button--small" type="button" data-action="build-today" data-id="${attr(plan.id)}">Đưa kế hoạch này vào Hôm nay</button></div>${body}</div></details>`;
    }).join("")}</div>`;
  }

  async function renderPlan(signal) {
    const [plansResult, nichesResult, channelsResult] = await Promise.allSettled([
      api("/api/plans", { signal }), api("/api/niches", { signal }), api("/api/my-channels", { signal }),
    ]);
    if (plansResult.status === "rejected") throw plansResult.reason;
    updateApiState(true, "Dịch vụ hoạt động");
    const plans = arrayFrom(plansResult.value, "plans");
    const planItemResults = await Promise.allSettled(plans.map((plan) => api(`/api/plans/${encodeURIComponent(plan.id)}/items`, { signal })));
    const niches = nichesResult.status === "fulfilled" ? arrayFrom(nichesResult.value, "niches") : [];
    const channels = channelsResult.status === "fulfilled" ? arrayFrom(channelsResult.value, "channels", "my_channels") : [];
    const options = niches.map((niche) => `<option value="${attr(niche.id)}">${escapeHtml(firstDefined(niche.label, niche.name, niche.key, `Ngách ${niche.id}`))}</option>`).join("");
    const channelOptions = ['<option value="">Kênh mới / không dùng hồ sơ kênh cũ</option>', ...channels.map((channel) => {
      const id = channelKey(channel);
      return `<option value="${attr(id)}"${state.selectedChannelId === id ? " selected" : ""}>${escapeHtml(firstDefined(channel.label, channel.title, channel.channel_id, "Kênh"))}</option>`;
    })].join("");
    const channelWarning = channelsResult.status === "rejected" ? `<div class="notice notice--warn"><span aria-hidden="true">!</span><span>Không tải được danh sách kênh. Bạn vẫn có thể lập 30 video cho một kênh mới.</span></div>` : "";
    const builder = nichesResult.status === "rejected"
      ? errorState(nichesResult.reason, false)
      : niches.length
        ? `<section class="card"><div class="card-head"><div><h3>Xây kênh → lập 30 video</h3><p>Mỗi chủ đề phải dựa trên video bằng chứng. Nếu chọn kênh đang vận hành, từng chủ đề sẽ được chấm độ phù hợp riêng theo hồ sơ kênh.</p></div></div><div class="card-body">${channelWarning}<form id="planForm"><div class="form-grid"><div class="field"><label for="planNiche">Ngách</label><select id="planNiche" name="niche_id" required>${options}</select></div><div class="field"><label for="planChannel">Kênh tham chiếu</label><select id="planChannel" name="my_channel_id">${channelOptions}</select></div><div class="field"><label for="planCount">Số video mục tiêu</label><input id="planCount" name="requested_count" type="number" min="1" max="30" value="30" required></div></div><div class="form-actions"><button class="button button--primary" type="submit">Tạo kế hoạch từ bằng chứng</button></div></form></div></section>`
        : emptyState("Chưa có ngách để lập kế hoạch", "Hãy quét thị trường và phân tích ngách trước.", '<a class="button button--primary" href="#/trend">Mở Radar</a>');
    const details = plans.length
      ? `<section class="card"><div class="card-head"><div><h3>Chủ đề thực tế trong từng kế hoạch</h3><p>Mỗi dòng giữ nguyên video bằng chứng, số liệu nguồn và độ phù hợp kênh đã lưu; kế hoạch mới nhất được mở sẵn.</p></div></div><div class="card-body">${planItemPanels(plans, planItemResults)}</div></section>`
      : "";
    return `${pageHead("30 video", "Lập kế hoạch khởi động từ bằng chứng thực tế; nếu chưa đủ 30 chủ đề, giao diện giữ nguyên phần thiếu bằng chứng thay vì tự lấp dữ liệu.")}${builder}<div style="height:11px"></div>${planCards(plans)}${details ? `<div style="height:11px"></div>${details}` : ""}`;
  }

  function todayItems(items) {
    if (!items.length) return emptyState("Hôm nay chưa có việc", "Tạo hàng đợi từ một kế hoạch đã lưu. COFI RADAR không tự sinh việc khi thiếu bằng chứng.");
    return `<div class="queue-list">${items.map((item, index) => {
      const evidenceVideoId = firstDefined(item.evidence_video_id, item.video_id);
      const evidenceItem = {
        title: firstDefined(item.evidence_title, item.topic_anchor, "Bằng chứng"),
        title_original: firstDefined(item.evidence_title_original, item.evidence_title),
        title_vi: firstDefined(item.evidence_title_vi, item.translated_evidence_title),
      };
      return `<article class="queue-item"><div class="queue-rank">${fmtNumber(firstDefined(item.priority, index + 1))}</div><div class="queue-thumb">${safeImage(youtubeThumbnail(evidenceVideoId), firstDefined(item.evidence_title, item.topic_anchor, "Thumbnail bằng chứng"), "queue-thumb__img")}</div><div><h3 class="queue-title">${escapeHtml(firstDefined(item.topic_anchor, item.title, item.production_brief, "Chủ đề"))}</h3><div class="queue-evidence-copy">${bilingualCopy(evidenceItem, "Bằng chứng")}</div><div class="queue-meta"><span>Ngách: ${escapeHtml(firstDefined(item.niche_label, item.niche_name, "—"))}</span><span>Outlier: ${fmtRatio(item.evidence_outlier)}</span><span>VPH: ${fmtCompact(item.evidence_vph)}</span>${item.note ? `<span>Độ khớp kênh: ${fmtNumber(item.channel_fit)}/100</span>` : ""}<span>${safeLink(firstDefined(item.evidence_url, item.url), "Bằng chứng ↗")}</span></div>${item.note ? `<p class="muted"><strong>Vì sao phù hợp:</strong> ${escapeHtml(item.note)}</p>` : ""}${item.production_brief ? `<p class="muted">${escapeHtml(item.production_brief)}</p>` : ""}</div><div class="queue-actions"><span>${statusPill(item.status)}</span><button class="button button--small" type="button" data-action="today-status" data-id="${attr(firstDefined(item.plan_item_id, item.id))}" data-status="doing">Đang làm</button><button class="button button--small button--success" type="button" data-action="today-status" data-id="${attr(firstDefined(item.plan_item_id, item.id))}" data-status="done">Xong</button><button class="button button--small" type="button" data-action="today-status" data-id="${attr(firstDefined(item.plan_item_id, item.id))}" data-status="skipped">Bỏ qua</button></div></article>`;
    }).join("")}</div>`;
  }

  async function renderToday(signal) {
    const [todayResult, plansResult, channelsResult] = await Promise.allSettled([
      api("/api/today", { signal }), api("/api/plans", { signal }), api("/api/my-channels", { signal }),
    ]);
    if (todayResult.status === "rejected") throw todayResult.reason;
    updateApiState(true, "Dịch vụ hoạt động");
    const items = arrayFrom(todayResult.value, "items", "today", "queue");
    const plans = plansResult.status === "fulfilled" ? arrayFrom(plansResult.value, "plans") : [];
    const channels = channelsResult.status === "fulfilled" ? arrayFrom(channelsResult.value, "channels", "my_channels") : [];
    const planOptions = plans.map((plan) => `<option value="${attr(plan.id)}">${escapeHtml(firstDefined(plan.niche_label, plan.label, `Kế hoạch #${plan.id}`))}</option>`).join("");
    const channelOptions = ['<option value="">Không gắn kênh</option>', ...channels.map((channel) => {
      const id = channelKey(channel);
      return `<option value="${attr(id)}"${state.selectedChannelId === id ? " selected" : ""}>${escapeHtml(firstDefined(channel.label, channel.title, channel.channel_id, "Kênh"))}</option>`;
    })].join("");
    const channelWarning = channelsResult.status === "rejected" ? `<div class="notice notice--warn"><span aria-hidden="true">!</span><span>Không tải được danh sách kênh; bạn vẫn có thể tạo Hôm nay mà không gắn kênh.</span></div>` : "";
    const builder = plansResult.status === "rejected"
      ? errorState(plansResult.reason, false)
      : plans.length
        ? `<section class="card"><div class="card-head"><div><h3>Tạo ưu tiên hôm nay</h3><p>Chọn kế hoạch và tùy chọn kênh để hệ thống xếp hạng các việc ưu tiên.</p></div></div><div class="card-body">${channelWarning}<form id="todayForm"><div class="form-grid"><div class="field"><label for="todayPlan">Kế hoạch</label><select id="todayPlan" name="plan_id" required>${planOptions}</select></div><div class="field"><label for="todayChannel">Kênh</label><select id="todayChannel" name="my_channel_id">${channelOptions}</select></div><div class="field"><label for="todayLimit">Số việc</label><input id="todayLimit" name="limit" type="number" min="1" max="10" value="5"></div></div><div class="form-actions"><button class="button button--primary" type="submit">Xếp hàng Hôm nay</button></div></form></div></section>`
        : emptyState("Chưa có kế hoạch nguồn", "Tạo kế hoạch 30 video trước khi xếp hàng Hôm nay.", '<a class="button button--primary" href="#/plan">Mở 30 video</a>');
    const updated = firstDefined(todayResult.value?.updated_at, items[0]?.queue_date, items[0]?.created_at);
    return `${pageHead("Hôm nay", "Hàng đợi sản xuất ưu tiên theo bằng chứng và độ mới; trạng thái được lưu bởi hệ thống.")}${staleNotice(updated, "Hàng đợi Hôm nay")}${builder}<div style="height:11px"></div>${todayItems(items)}`;
  }

  function evidenceRows(items) {
    return items.map((item) => `<tr><td>${escapeHtml(firstDefined(item.kind, item.type, "—"))}</td><td><span class="cell-main">${escapeHtml(firstDefined(item.label, item.title, item.name, item.ref_id, "Bằng chứng"))}</span><span class="cell-sub">${escapeHtml(firstDefined(item.note, item.source, ""))}</span></td><td>${escapeHtml(firstDefined(item.ref_id, item.id, "—"))}</td><td>${fmtDate(firstDefined(item.saved_at, item.created_at, item.fetched_at), true)}</td><td>${safeLink(firstDefined(item.url, item.video_url, item.channel_url, item.source_url), "Mở nguồn ↗")}</td></tr>`).join("");
  }

  async function renderEvidence(signal) {
    const payload = await api("/api/evidence", { signal });
    updateApiState(true, "Dịch vụ hoạt động");
    const items = arrayFrom(payload, "evidence");
    const body = items.length ? `<section class="card"><div class="card-head"><div><h3>Bằng chứng đã lưu</h3><p>Liên kết nguồn mở trong tab mới khi hệ thống cung cấp URL.</p></div><span class="pill pill--neutral">${fmtNumber(items.length)} mục</span></div><div class="table-wrap"><table><thead><tr><th>Loại</th><th>Nhãn</th><th>ID tham chiếu</th><th>Đã lưu</th><th>Nguồn</th></tr></thead><tbody>${evidenceRows(items)}</tbody></table></div></section>` : emptyState("Thư viện đang trống", "Lưu video, kênh hoặc ngách từ các màn phân tích. Không có bằng chứng mẫu.");
    return `${pageHead("Thư viện bằng chứng", "Kho lưu các nguồn đã xác minh để quay lại kiểm tra khi lập kế hoạch hoặc sản xuất.")}${body}`;
  }

  function sourceCards(payload) {
    const sources = arrayFrom(payload, "sources", "items", "providers");
    if (sources.length) {
      return `<div class="source-grid">${sources.map((source) => `<article class="mini-card"><div class="mini-card__top"><div><h3>${escapeHtml(firstDefined(source.name, source.source, source.id, "Nguồn"))}</h3><p>${escapeHtml(firstDefined(source.description, source.detail, "Nguồn dữ liệu công khai"))}</p></div>${statusPill(firstDefined(source.status, source.health))}</div><dl><div><dt>Lần kiểm tra</dt><dd>${fmtDate(firstDefined(source.checked_at, source.updated_at, source.fetched_at), true)}</dd></div><div><dt>Chế độ</dt><dd>${escapeHtml(firstDefined(source.mode, source.provider, "—"))}</dd></div></dl>${source.error ? `<div class="notice notice--error" style="margin:10px 0 0"><span>!</span><span>${escapeHtml(source.error)}</span></div>` : ""}${source.url ? `<div class="mini-card__actions">${safeLink(source.url, "Mở nguồn ↗")}</div>` : ""}</article>`).join("")}</div>`;
    }
    if (payload && typeof payload === "object" && Object.keys(payload).length) {
      return `<section class="card"><div class="table-wrap"><table><thead><tr><th>Nguồn / khóa</th><th>Trạng thái / giá trị</th></tr></thead><tbody>${Object.entries(payload).map(([key, value]) => `<tr><td class="cell-main">${escapeHtml(key)}</td><td>${escapeHtml(typeof value === "object" ? JSON.stringify(value) : value)}</td></tr>`).join("")}</tbody></table></div></section>`;
    }
    return emptyState("Chưa có trạng thái nguồn", "Máy chủ chưa trả về nguồn dữ liệu nào.");
  }

  async function renderSources(signal) {
    const payload = await api("/api/sources", { signal });
    updateApiState(true, "Dịch vụ hoạt động");
    const sources = arrayFrom(payload, "sources", "items", "providers");
    const timestamp = firstDefined(payload?.updated_at, payload?.checked_at, sources[0]?.checked_at, sources[0]?.updated_at, sources[0]?.fetched_at);
    return `${pageHead("Nguồn dữ liệu", "Theo dõi trạng thái nguồn công khai và lỗi kết nối. Giao diện không suy đoán nguồn đang hoạt động nếu máy chủ không xác nhận.")}${staleNotice(timestamp, "Trạng thái nguồn")}${sourceCards(payload)}`;
  }

  function settingsTable(payload) {
    if (!payload || typeof payload !== "object" || !Object.keys(payload).length) return emptyState("Chưa có cấu hình công khai", "Máy chủ chưa trả về trạng thái cài đặt. Giao diện không hiển thị khóa bí mật hoặc giá trị giả.");
    const rows = Object.entries(payload).filter(([key]) => !/(key|secret|token|password)/i.test(key)).map(([key, value]) => `<tr><td class="cell-main">${escapeHtml(key)}</td><td>${escapeHtml(typeof value === "object" ? JSON.stringify(value) : value)}</td></tr>`).join("");
    return `<section class="card"><div class="card-head"><div><h3>Trạng thái cấu hình</h3><p>Chỉ hiển thị trường an toàn do API trả về; trường có tên gợi ý secret/token/key bị ẩn phía client.</p></div></div><div class="table-wrap"><table><thead><tr><th>Thuộc tính</th><th>Giá trị</th></tr></thead><tbody>${rows || '<tr><td colspan="2" class="muted">Không có trường an toàn để hiển thị.</td></tr>'}</tbody></table></div></section>`;
  }

  async function renderSettings(signal) {
    const payload = await apiFallback(["/api/settings", "/api/health"], { signal });
    updateApiState(true, "Dịch vụ hoạt động");
    return `${pageHead("Cài đặt", "Kiểm tra trạng thái dịch vụ và cấu hình không nhạy cảm. Khóa API không được hiển thị ở frontend.")}${settingsTable(payload)}`;
  }

  async function renderRoute() {
    const route = parseRoute();
    updateChrome(route);
    state.renderToken += 1;
    const token = state.renderToken;
    if (state.controller) state.controller.abort();
    state.controller = new AbortController();
    const { signal } = state.controller;
    els.view.setAttribute("aria-busy", "true");
    els.view.innerHTML = loadingState();
    try {
      let html;
      if (route === "dashboard") html = await renderDashboard(signal);
      else if (route === "trend") html = await renderTrend(signal);
      else if (route === "niches") html = await renderNiches(signal);
      else if (route === "channels") html = await renderChannels(signal);
      else if (route === "plan") html = await renderPlan(signal);
      else if (route === "today") html = await renderToday(signal);
      else if (route === "evidence") html = await renderEvidence(signal);
      else if (route === "sources") html = await renderSources(signal);
      else html = await renderSettings(signal);
      if (token !== state.renderToken) return;
      els.view.innerHTML = html;
      els.view.setAttribute("aria-busy", "false");
      bindForms();
    } catch (error) {
      if (error?.name === "AbortError" || token !== state.renderToken) return;
      updateApiState(false, "Dịch vụ có lỗi");
      els.view.innerHTML = `${pageHead((ROUTES[route] || ROUTES.dashboard).title, "Không thể hiển thị dữ liệu hiện tại.")}${errorState(error)}`;
      els.view.setAttribute("aria-busy", "false");
    }
  }

  function setBusy(form, busy) {
    form?.querySelectorAll("button, input, select, textarea").forEach((element) => { element.disabled = busy; });
  }

  function formValues(form) {
    return Object.fromEntries(new FormData(form).entries());
  }

  async function submitScan(form) {
    const values = formValues(form);
    const mode = ["directed", "ai", "transformative"].includes(values.scan_mode) ? values.scan_mode : "market";
    const seeds = mode === "directed"
      ? String(values.seeds || "").split(/[\n,]+/).map((seed) => seed.trim()).filter(Boolean)
      : [];
    const body = {
      market: values.market,
      days: Number(values.days),
      seeds,
    };
    if (mode === "directed" && values.content_type) body.content_type = values.content_type;
    if (mode === "ai") body.production_mode = "ai";
    if (mode === "transformative") body.production_mode = "transformative";
    if (values.max_videos) body.max_videos = Number(values.max_videos);
    const progress = document.getElementById("scanProgress");
    const submitButton = document.getElementById("scanSubmitButton");
    const originalButtonText = submitButton?.textContent || "QUÉT";
    const startedAt = Date.now();
    let progressTimer = null;
    if (progress) {
      progress.hidden = false;
      const updateProgress = () => {
        const seconds = Math.max(0, Math.floor((Date.now() - startedAt) / 1000));
        progress.lastElementChild.textContent = mode === "ai"
          ? `Đang quét trend và chấm khả năng sản xuất bằng AI… ${seconds}s`
          : mode === "transformative"
            ? `Đang quét trend và chấm Transformative Fit + copyright risk… ${seconds}s`
            : `Đang quét YouTube và xác minh bằng chứng… ${seconds}s`;
      };
      updateProgress();
      progressTimer = window.setInterval(updateProgress, 1000);
    }
    if (submitButton) submitButton.textContent = mode === "ai" ? "ĐANG QUÉT AI FIT…" : mode === "transformative" ? "ĐANG QUÉT TRANSFORMATIVE…" : "ĐANG QUÉT…";
    setBusy(form, true);
    try {
      const result = await api("/api/scans", { method: "POST", body });
      const videoCount = firstDefined(result?.source_summary?.videos, result?.videos);
      toast(result?.message || (videoCount !== undefined ? `Quét hoàn tất · ${fmtNumber(videoCount)} video đã xác minh.` : "Quét hoàn tất."), "success");
      await renderRoute();
    } catch (error) {
      toast(`Không thể bắt đầu quét: ${error.message}`, "error");
    } finally {
      if (progressTimer) window.clearInterval(progressTimer);
      if (progress) progress.hidden = true;
      if (submitButton) submitButton.textContent = originalButtonText;
      setBusy(form, false);
    }
  }

  async function submitChannel(form) {
    const values = formValues(form);
    const body = { channel_ref: values.channel_ref.trim(), label: values.label?.trim() || null, content_type: values.content_type };
    setBusy(form, true);
    try {
      const result = await api("/api/my-channels", { method: "POST", body });
      toast(result?.message || "Đã thêm kênh.", "success");
      await renderRoute();
    } catch (error) { toast(`Không thể thêm kênh: ${error.message}`, "error"); }
    finally { setBusy(form, false); }
  }

  async function createPlan(nicheId, requestedCount = 30, channelId = null, form = null) {
    if (!nicheId) return;
    if (form) setBusy(form, true);
    try {
      const body = { niche_id: Number.isNaN(Number(nicheId)) ? nicheId : Number(nicheId), requested_count: Number(requestedCount) || 30 };
      if (channelId) body.my_channel_id = channelId;
      const result = await api("/api/plans", { method: "POST", body });
      const supported = firstDefined(result?.supported_count, result?.supported, result?.items?.length);
      toast(supported !== undefined ? `Đã tạo kế hoạch với ${supported} chủ đề đủ bằng chứng.` : (result?.message || "Đã tạo kế hoạch."), "success");
      location.hash = "#/plan";
      if (state.route === "plan") await renderRoute();
    } catch (error) { toast(`Không thể tạo kế hoạch: ${error.message}`, "error"); }
    finally { if (form) setBusy(form, false); }
  }

  async function submitPlan(form) {
    const values = formValues(form);
    await createPlan(values.niche_id, values.requested_count, values.my_channel_id || null, form);
  }

  async function buildToday(planId, channelId = null, limit = 5, form = null) {
    if (!planId) return;
    if (form) setBusy(form, true);
    try {
      const body = { plan_id: Number.isNaN(Number(planId)) ? planId : Number(planId), limit: Number(limit) || 5 };
      if (channelId) body.my_channel_id = channelId;
      const result = await api("/api/today", { method: "POST", body });
      toast(result?.message || "Đã cập nhật hàng đợi Hôm nay.", "success");
      location.hash = "#/today";
      if (state.route === "today") await renderRoute();
    } catch (error) { toast(`Không thể tạo hàng đợi Hôm nay: ${error.message}`, "error"); }
    finally { if (form) setBusy(form, false); }
  }

  async function submitToday(form) {
    const values = formValues(form);
    await buildToday(values.plan_id, values.my_channel_id || null, values.limit, form);
  }

  async function saveNicheEvidence(nicheId) {
    try {
      await api("/api/evidence", { method: "POST", body: { kind: "niche", ref_id: String(nicheId) } });
      toast("Đã lưu ngách vào thư viện bằng chứng.", "success");
    } catch (error) { toast(`Không thể lưu bằng chứng: ${error.message}`, "error"); }
  }

  async function updateTodayStatus(itemId, status) {
    if (!itemId) return;
    const paths = [`/api/today/${encodeURIComponent(itemId)}`, `/api/today/items/${encodeURIComponent(itemId)}`];
    try {
      await apiFallback(paths, { method: "PATCH", body: { status } });
      toast("Đã cập nhật trạng thái.", "success");
      await renderRoute();
    } catch (error) { toast(`Không thể cập nhật trạng thái: ${error.message}`, "error"); }
  }

  function bindForms() {
    const scanFormEl = document.getElementById("scanForm");
    if (scanFormEl) {
      const directedFields = document.getElementById("directedScanFields");
      const submitButton = document.getElementById("scanSubmitButton");
      const syncScanMode = () => {
        const selected = scanFormEl.querySelector('input[name="scan_mode"]:checked')?.value || "market";
        const directed = selected === "directed";
        const ai = selected === "ai";
        const transformative = selected === "transformative";
        if (directedFields) directedFields.hidden = !directed;
        if (submitButton) submitButton.textContent = directed ? "QUÉT CÓ ĐỊNH HƯỚNG" : ai ? "TÌM TREND SẢN XUẤT BẰNG AI" : transformative ? "TÌM TREND CONTENT + FOOTAGE" : "QUÉT TOÀN THỊ TRƯỜNG";
      };
      scanFormEl.querySelectorAll('input[name="scan_mode"]').forEach((input) => input.addEventListener("change", syncScanMode));
      syncScanMode();
      scanFormEl.addEventListener("submit", (event) => { event.preventDefault(); submitScan(scanFormEl); });
    }
    const channelFormEl = document.getElementById("channelForm");
    if (channelFormEl) channelFormEl.addEventListener("submit", (event) => { event.preventDefault(); submitChannel(channelFormEl); });
    const planFormEl = document.getElementById("planForm");
    if (planFormEl) planFormEl.addEventListener("submit", (event) => { event.preventDefault(); submitPlan(planFormEl); });
    const todayFormEl = document.getElementById("todayForm");
    if (todayFormEl) todayFormEl.addEventListener("submit", (event) => { event.preventDefault(); submitToday(todayFormEl); });
  }

  async function handleAction(target) {
    const actionEl = target.closest("[data-action]");
    if (!actionEl) return;
    const action = actionEl.dataset.action;
    const id = actionEl.dataset.id;
    if (action === "retry") return renderRoute();
    if (action === "open-niche") {
      state.selectedNicheId = id;
      return renderRoute();
    }
    if (action === "build-plan") return createPlan(id, 30);
    if (action === "save-niche-evidence") return saveNicheEvidence(id);
    if (action === "build-today") return buildToday(id);
    if (action === "today-status") return updateTodayStatus(id, actionEl.dataset.status);
    if (action === "open-channel-profile") return openChannelProfile(id);
    if (action === "open-channel-plan") {
      state.selectedChannelId = String(id || "");
      closeChannelProfileDialog();
      location.hash = "#/plan";
      return;
    }
    if (action === "open-channel-today") {
      state.selectedChannelId = String(id || "");
      closeChannelProfileDialog();
      location.hash = "#/today";
      return;
    }
  }

  document.addEventListener("click", (event) => { handleAction(event.target); });
  document.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" && event.key !== " ") return;
    const row = event.target.closest('[data-action="open-niche"][tabindex], [data-action="open-channel-profile"][tabindex]');
    if (!row || event.target.closest("button, a, input, select, textarea")) return;
    event.preventDefault();
    if (row.dataset.action === "open-channel-profile") {
      openChannelProfile(row.dataset.id);
      return;
    }
    state.selectedNicheId = row.dataset.id;
    renderRoute();
  });

  els.closeChannelProfileDialog?.addEventListener("click", closeChannelProfileDialog);
  els.channelProfileDialog?.addEventListener("click", (event) => {
    if (event.target === els.channelProfileDialog) closeChannelProfileDialog();
  });

  els.refresh.addEventListener("click", () => renderRoute());
  window.addEventListener("hashchange", renderRoute);

  if (!location.hash) location.replace("#/dashboard");
  else renderRoute();
})();
