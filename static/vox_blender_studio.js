/* ============================================================================
 * COFI DOCUMENTARY — BLENDER 4.2 3D EEVEE & VOX SATELLITE 24-ARCHETYPE STUDIO
 * Integrated directly into Tab 06 (Edit) & Project Detail of CofiDocumentary
 * ============================================================================ */
(function () {
  "use strict";

  const BLENDER_3D_VIDEOS = [
    {
      id: "vox_5min_master",
      code: "MASTER 5M",
      badgeColor: "#facc15",
      title: "🎬 Phim Master 5 Phút (24 Kiểu Vox Duyệt + Bản Đồ Vệ Tinh Thật + 80 Clips + 34 SFX)",
      subtitle: "Ưu tiên 1: Video Footage -> 2: Ảnh Footage -> 3: Vox (chỉ khi khớp câu voice, 30fps mượt) -> 4: Ảnh AI",
      videoUrl: "/static/vox_studio/vox_5min_studio_master.mp4",
      thumbUrl: "/static/vox_studio/preview_02_school_store_map.jpg",
      durationLabel: "05:03 · 1080p 30fps Smooth",
      markers: [
        { sec: 9.15, label: "① 0:09 · #D1: 230,000 Vân Tay vs 0 Trùng Khớp" },
        { sec: 38.71, label: "② 0:38 · #M1: Vệ Tinh Z16 Đột Kích Căng Tin" },
        { sec: 121.23, label: "③ 2:01 · #D2: 2 Khuôn Mặt Cao Thừa Dũng" },
        { sec: 140.82, label: "④ 2:20 · #M2: Vệ Tinh Địa Hình Cam Túc Z6" },
        { sec: 188.43, label: "⑤ 3:08 · #D3: Hồ Sơ 3 Vật Chứng Hiện Trường" },
        { sec: 217.71, label: "⑥ 3:37 · #M3: Vệ Tinh Z9 Vùng Mù Hộ Khẩu" },
        { sec: 240.01, label: "⑦ 4:00 · #P1: Báo Chí 6 Năm Bốc Hơi (1988–1994)" },
        { sec: 290.15, label: "⑧ 4:50 · #M4: Bảng Ghim Vệ Tinh 4 Vụ 1998" },
      ],
    },
  ];

  const CATALOG_24_ARCHETYPES = [
    // 8 Real Satellite Map Archetypes (#M1..#M8)
    { id: "#M1", cluster: "map", name: "Urban Satellite Z14 + Rooftop Loupe Z16", viDesc: "Đường đột kích GPS nét đứt chạy dọc phố + Kính lúp vệ tinh ZOOM ×16 soi thẳng mái nhà hiện trường", img: "/static/vox_studio/preview_02_school_store_map.jpg", zoom: "Esri Z14 + Z16", jumpSec: 38.71 },
    { id: "#M2", cluster: "map", name: "Orbital Macro Terrain Z6 + GeoJSON Boundary", viDesc: "Bản đồ vệ tinh địa hình cấp tỉnh Z6 + Quét sáng ranh giới hành chính GeoJSON & khoanh đỏ tâm chấn", img: "/static/vox_studio/preview_04_gansu_baiyin_gis.jpg", zoom: "Esri Z6 Terrain", jumpSec: 140.82 },
    { id: "#M3", cluster: "map", name: "Dual-Zone Radar Sweep vs. Escape Vector", viDesc: "Radar xanh lục bảo xoay 360° ở nội đô + Đường tên lửa đứt nét vượt sông sang vùng mù hộ khẩu 100km", img: "/static/vox_studio/preview_06_hukou_blindspot_gis.jpg", zoom: "Esri Z9 Regional", jumpSec: 217.71 },
    { id: "#M4", cluster: "map", name: "Detective Corkboard + Real Satellite Matrix", viDesc: "Bản đồ vệ tinh thật ghim trên bảng gỗ bần + 4 đinh ghim đỏ nối dây chỉ đỏ căng qua 4 hiện trường", img: "/static/vox_studio/preview_09_1998_four_cases_map.jpg", zoom: "Esri Z14 + Pinboard", jumpSec: 290.15 },
    { id: "#M5", cluster: "map", name: "2.5D Tilted Satellite Slab + 3D Beacons", viDesc: "Mặt phẳng vệ tinh nghiêng 2.5D có độ dày khối đá + Cột sáng 3D dựng đứng từ tọa độ + Quỹ đạo Parabol", img: "/static/vox_studio/exp_m5_25d_tilted_satellite.jpg", zoom: "2.5D Perspective Z14" },
    { id: "#M6", cluster: "map", name: "Split-Screen Dual Satellite (Z9 ↔ Z16)", viDesc: "Chia đôi màn hình: Bên trái vệ tinh vùng Z9 bắn tia laser sang bên phải vệ tinh cận cảnh mái nhà Z16", img: "/static/vox_studio/exp_m6_split_dual_satellite.jpg", zoom: "Dual Z9 ↔ Z16" },
    { id: "#M7", cluster: "map", name: "Night-Ops Thermal/IR Curfew Lockdown", viDesc: "Bản đồ vệ tinh chuyển sang chế độ hồng ngoại ban đêm + Vòng vây giới nghiêm bán kính 3km & 4 chốt chặn", img: "/static/vox_studio/exp_m7_night_ops_satellite.jpg", zoom: "Night Thermal Z14" },
    { id: "#M8", cluster: "map", name: "Chronological Multi-Stop GPS Trajectory", viDesc: "Đường truy vết GPS đa điểm theo thanh thời gian 1988 → 1994 → 1998 → 2002 → 2016 trên nền vệ tinh thật", img: "/static/vox_studio/preview_08_1998_four_cases_map.jpg", zoom: "Multi-Stop GPS Z14" },

    // 10 Forensic Dossier & Biometric Lab Archetypes (#D1..#D10)
    { id: "#D1", cluster: "dossier", name: "Manila Case Folder + 84-Cell Fingerprint Grid", viDesc: "Bìa hồ sơ Manila mở đôi + Lưới 84 ô vân tay thật quét đỏ & bộ đếm 230,000장 -> 일치자 0명", img: "/static/vox_studio/preview_01_fingerprint_paradox.jpg", zoom: "AFIS 84-Grid", jumpSec: 9.15 },
    { id: "#D2", cluster: "dossier", name: "Dual-Identity Personnel Card vs. Black Dossier", viDesc: "Đối xứng 2 mặt: Thẻ nhân sự gương mẫu [A] đối đầu Hồ sơ thú tội bìa đen [B] trên bàn gỗ óc chó", img: "/static/vox_studio/preview_03_duality_collage.jpg", zoom: "Split Duality", jumpSec: 121.23 },
    { id: "#D3", cluster: "dossier", name: "35mm Kodak Negative Strip + 3 Kraft Envelopes", viDesc: "Dải phim âm bản Kodak 35mm + 3 túi giấy Kraft niêm phong vật chứng buộc dây cúc đồng (지문 · DNA · 족적)", img: "/static/vox_studio/preview_05_three_clues_dossier.jpg", zoom: "3 Evidence Bags", jumpSec: 188.43 },
    { id: "#D4", cluster: "dossier", name: "Y-STR DNA Backlit Lightbox + Family Pedigree", viDesc: "Bàn đèn y khoa phát sáng + Băng điện di gen DYS19..DYS439 (99.9998%) & Sơ đồ phả hệ dòng họ", img: "/static/vox_studio/exp_d4_ydna_lightbox.jpg", zoom: "Y-STR Gel Lab" },
    { id: "#D5", cluster: "dossier", name: "Brushed Aluminum Clipboard Q&A + Voiceprint", viDesc: "Bìa kẹp nhôm biên bản hỏi cung tô bút dạ vàng + Máy hiện sóng âm thanh lời thú tội REC", img: "/static/vox_studio/exp_d5_clipboard_interrogation.jpg", zoom: "Audio Waveform" },
    { id: "#D6", cluster: "dossier", name: "Class-A Red Wanted Warrant + Sketch Grid", viDesc: "Lệnh truy nã đỏ cấp A Bộ Công An + Lưới nhân trắc học đối chiếu phác họa Sketch và ảnh thật", img: "/static/vox_studio/exp_d6_wanted_warrant_sketch.jpg", zoom: "Biometric Sketch" },
    { id: "#D7", cluster: "dossier", name: "Crime Scene Blueprint Floorplan + Vectors", viDesc: "Bản vẽ mặt bằng hiện trường Blueprint + Vector hướng di chuyển, vết chân và vị trí thu mẫu", img: "/static/vox_studio/preview_05_three_clues_dossier.jpg", zoom: "Blueprint Vector" },
    { id: "#D8", cluster: "dossier", name: "Suspect Chronological Age Progression Strip", viDesc: "Dải đối chiếu biến đổi nhân dạng nghi phạm qua 3 thập kỷ (24세 → 34세 → 52세)", img: "/static/vox_studio/preview_03_duality_collage.jpg", zoom: "Age Strip 28Y" },
    { id: "#D9", cluster: "dossier", name: "Dual-Ocular Forensic Microscope Comparator", viDesc: "Ống ngắm kính hiển vi quang học đôi + Tia laser nối 14 điểm đặc trưng vân tay (14/14 · 100.0% 일치)", img: "/static/vox_studio/exp_d9_microscope_minutiae.jpg", zoom: "14-Pt Minutiae" },
    { id: "#D10", cluster: "dossier", name: "Archival Steel Filing Cabinet Drawer Pull-Out", viDesc: "Ngăn kéo tủ sắt lưu trữ hồ sơ án treo (1988–2016 미제사건 캐비닛) với các tab năm bật sáng", img: "/static/vox_studio/preview_01_fingerprint_paradox.jpg", zoom: "Cold Case Vault" },

    // 6 Archival Press & 1990s Broadcast Archetypes (#P1..#P6)
    { id: "#P1", cluster: "press", name: "Morning Broadsheet Front Page + 6-Year Bar", viDesc: "Trang nhất báo giấy khổ lớn ố vàng + Bút dạ vàng quét tít báo & Thanh timeline 6 năm (1988–1994)", img: "/static/vox_studio/preview_07_six_year_timeline.jpg", zoom: "Broadsheet 1994", jumpSec: 240.01 },
    { id: "#P2", cluster: "press", name: "Police Red Curfew Notice + 3 Press Clippings", viDesc: "Thông cáo giới nghiêm viền đỏ của Công an + 3 mảnh báo cắt dán nghiêng gây chấn động dư luận", img: "/static/vox_studio/preview_08_newspaper_panic.jpg", zoom: "Curfew Notice", jumpSec: 274.09 },
    { id: "#P3", cluster: "press", name: "1990s CRT TV News Broadcast Monitor", viDesc: "Màn hình tivi CRT thập niên 1990 có sọc quét Scanlines, nhãn LIVE, băng chữ chạy Chyron & sổ trực VHS", img: "/static/vox_studio/exp_p3_90s_tv_broadcast.jpg", zoom: "90s CRT Broadcast" },
    { id: "#P4", cluster: "press", name: "Microfiche Green-Phosphor Reader Archive", viDesc: "Máy đọc vi phim Microfilm phốt-pho xanh tra cứu kho lưu trữ báo cũ thập niên 1990", img: "/static/vox_studio/preview_07_six_year_timeline.jpg", zoom: "Microfilm Reader" },
    { id: "#P5", cluster: "press", name: "Tear-Off Wall Calendar Montage (10,318 Days)", viDesc: "Lịch treo tường lật qua 28 năm (1988 → 2016 · 10,318일의 추적) đếm ngược ngày phá án", img: "/static/vox_studio/preview_08_newspaper_panic.jpg", zoom: "10,318 Days Counter" },
    { id: "#P6", cluster: "press", name: "Supreme Court Verdict & Execution Decree", viDesc: "Văn bản tuyên án của Tòa án Nhân dân Tối cao đóng dấu mộc đỏ tươi (최고인민법원 판결문)", img: "/static/vox_studio/exp_p3_90s_tv_broadcast.jpg", zoom: "Court Verdict" },
  ];

  const state = {
    activeVideoId: "vox_5min_master",
    activeFilter: "all",
    viewMode: localStorage.getItem("cofi-edit-engine-mode") || "split", // 'vox_blender' | 'remotion' | 'split'
    lightboxImg: null,
    lightboxTitle: "",
    lightboxSub: "",
    jobId: null,
    voxManifest: null,
    visualManifest: null,
  };

  function esc(str) {
    return String(str ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function injectStyles() {
    if (document.getElementById("cofiVoxBlenderStudioStyles")) return;
    const style = document.createElement("style");
    style.id = "cofiVoxBlenderStudioStyles";
    style.textContent = `
      .vox-blender-mode-bar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 10px;
        flex-wrap: wrap;
        padding: 10px 14px;
        margin: 8px 0 12px;
        background: linear-gradient(90deg, rgba(15, 23, 42, 0.96), rgba(20, 29, 49, 0.96));
        border: 1px solid rgba(250, 204, 21, 0.38);
        border-left: 5px solid #facc15;
        border-radius: 10px;
      }
      .vox-mode-tabs {
        display: inline-flex;
        gap: 6px;
        flex-wrap: wrap;
      }
      .vox-mode-tab {
        height: 32px;
        min-height: 32px !important;
        padding: 0 12px !important;
        border-radius: 7px !important;
        font-size: 12px !important;
        font-weight: 800 !important;
        border: 1px solid rgba(148, 163, 184, 0.25) !important;
        background: rgba(15, 23, 42, 0.85) !important;
        color: #cbd5e1 !important;
        cursor: pointer;
        display: inline-flex;
        align-items: center;
        gap: 6px;
      }
      .vox-mode-tab.active {
        background: linear-gradient(135deg, #facc15, #f59e0b) !important;
        color: #090d16 !important;
        border-color: #fde047 !important;
        box-shadow: 0 4px 14px rgba(250, 204, 21, 0.28);
      }
      .vox-blender-studio-shell {
        background: #0b101b;
        border: 1px solid rgba(56, 189, 248, 0.26);
        border-radius: 12px;
        padding: 14px;
        margin-bottom: 14px;
        box-shadow: 0 14px 36px rgba(0, 0, 0, 0.45);
      }
      .vox-blender-top-grid {
        display: grid;
        grid-template-columns: minmax(0, 1.45fr) minmax(320px, 1fr);
        gap: 14px;
        align-items: start;
      }
      @media (max-width: 1180px) {
        .vox-blender-top-grid {
          grid-template-columns: 1fr;
        }
      }
      .vox-video-stage-card {
        background: #111827;
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        padding: 12px;
      }
      .vox-video-player-wrap {
        width: 100%;
        aspect-ratio: 16 / 9;
        background: #000;
        border-radius: 8px;
        overflow: hidden;
        border: 2px solid rgba(250, 204, 21, 0.4);
        position: relative;
      }
      .vox-video-player-wrap video {
        width: 100%;
        height: 100%;
        display: block;
        object-fit: contain;
        background: #000;
      }
      .vox-scene-playlist {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(225px, 1fr));
        gap: 7px;
        margin-top: 10px;
      }
      .vox-playlist-btn {
        text-align: left;
        padding: 7px 9px !important;
        border-radius: 8px !important;
        background: rgba(30, 41, 59, 0.78) !important;
        border: 1px solid rgba(148, 163, 184, 0.2) !important;
        color: #f1f5f9 !important;
        cursor: pointer;
        display: flex;
        align-items: center;
        gap: 8px;
        transition: all 0.14s ease;
      }
      .vox-playlist-btn:hover {
        border-color: #38bdf8 !important;
        background: rgba(30, 41, 59, 0.98) !important;
      }
      .vox-playlist-btn.active {
        background: rgba(250, 204, 21, 0.14) !important;
        border-color: #facc15 !important;
        box-shadow: 0 0 0 1px rgba(250, 204, 21, 0.35);
      }
      .vox-playlist-thumb {
        width: 58px;
        height: 34px;
        border-radius: 4px;
        object-fit: cover;
        flex-shrink: 0;
        border: 1px solid rgba(255, 255, 255, 0.18);
      }
      .vox-marker-pills {
        display: flex;
        flex-wrap: wrap;
        gap: 5px;
        margin-top: 9px;
      }
      .vox-marker-pill {
        height: 26px !important;
        min-height: 26px !important;
        padding: 0 9px !important;
        border-radius: 6px !important;
        font-size: 11px !important;
        font-weight: 700 !important;
        background: rgba(15, 23, 42, 0.9) !important;
        border: 1px solid rgba(56, 189, 248, 0.3) !important;
        color: #e2e8f0 !important;
        cursor: pointer;
      }
      .vox-marker-pill:hover {
        border-color: #facc15 !important;
        color: #fde047 !important;
      }
      .vox-beat-router-card {
        background: #111827;
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        padding: 12px;
        display: flex;
        flex-direction: column;
        gap: 8px;
      }
      .vox-beat-router-list {
        max-height: 430px;
        overflow-y: auto;
        display: flex;
        flex-direction: column;
        gap: 6px;
        padding-right: 4px;
      }
      .vox-beat-item {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 7px 9px;
        background: rgba(15, 23, 42, 0.86);
        border: 1px solid rgba(148, 163, 184, 0.18);
        border-radius: 8px;
      }
      .vox-beat-item img {
        width: 68px;
        height: 38px;
        object-fit: cover;
        border-radius: 4px;
        border: 1px solid rgba(255, 255, 255, 0.16);
        cursor: zoom-in;
        flex-shrink: 0;
      }
      .vox-catalog-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
        gap: 10px;
        margin-top: 10px;
      }
      .vox-arch-card {
        background: #111827;
        border: 1px solid rgba(148, 163, 184, 0.22);
        border-radius: 9px;
        overflow: hidden;
        display: flex;
        flex-direction: column;
        transition: transform 0.14s ease, border-color 0.14s ease;
      }
      .vox-arch-card:hover {
        transform: translateY(-2px);
        border-color: #facc15;
      }
      .vox-arch-card-thumb {
        width: 100%;
        aspect-ratio: 16 / 9;
        background: #000;
        position: relative;
        cursor: zoom-in;
        overflow: hidden;
      }
      .vox-arch-card-thumb img {
        width: 100%;
        height: 100%;
        object-fit: cover;
        display: block;
      }
      .vox-arch-badge {
        position: absolute;
        top: 6px;
        left: 6px;
        padding: 2px 7px;
        border-radius: 4px;
        font-size: 10.5px;
        font-weight: 900;
        background: rgba(9, 13, 22, 0.9);
        color: #facc15;
        border: 1px solid rgba(250, 204, 21, 0.5);
      }
      .vox-arch-zoom-tag {
        position: absolute;
        bottom: 6px;
        right: 6px;
        padding: 1px 6px;
        border-radius: 4px;
        font-size: 10px;
        font-weight: 700;
        background: rgba(9, 13, 22, 0.88);
        color: #38bdf8;
      }
      .vox-arch-card-body {
        padding: 8px 10px;
        display: flex;
        flex-direction: column;
        gap: 4px;
        flex: 1;
      }
      .vox-lightbox-backdrop {
        position: fixed;
        inset: 0;
        z-index: 99999;
        background: rgba(5, 8, 15, 0.92);
        backdrop-filter: blur(8px);
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 24px;
      }
      .vox-lightbox-modal {
        max-width: 1180px;
        width: 100%;
        background: #0f172a;
        border: 1px solid rgba(250, 204, 21, 0.45);
        border-radius: 12px;
        padding: 14px;
        box-shadow: 0 24px 64px rgba(0, 0, 0, 0.85);
      }
    `;
    document.head.appendChild(style);
  }

  function applyEditorVisibilityMode(hostContainer) {
    const parentShell = hostContainer.closest(".persistent-editor-shell") || document;
    const remotionBody = parentShell.querySelector(".editor-body");
    const voxShell = hostContainer.querySelector("#cofiVoxBlenderMainPanel");
    if (voxShell) {
      voxShell.style.display = state.viewMode === "remotion" ? "none" : "block";
    }
    if (remotionBody) {
      remotionBody.style.display = state.viewMode === "vox_blender" ? "none" : "";
    }
  }

  function renderDom(hostContainer) {
    if (!hostContainer) return;
    injectStyles();

    const activeVid = BLENDER_3D_VIDEOS.find((v) => v.id === state.activeVideoId) || BLENDER_3D_VIDEOS[0];
    const beats = state.voxManifest?.beats || [];
    const mapCount = beats.filter((b) => String(b.scene_archetype || "").startsWith("#M")).length;
    const dossierCount = beats.filter((b) => String(b.scene_archetype || "").startsWith("#D")).length;
    const pressCount = beats.filter((b) => String(b.scene_archetype || "").startsWith("#P")).length;

    const filteredCatalog = CATALOG_24_ARCHETYPES.filter((item) => {
      if (state.activeFilter === "all") return true;
      return item.cluster === state.activeFilter;
    });

    const playlistHtml = BLENDER_3D_VIDEOS.map((v) => {
      const isAct = v.id === activeVid.id;
      return `<button type="button" class="vox-playlist-btn ${isAct ? "active" : ""}" data-select-vox-video="${esc(v.id)}">
        <img class="vox-playlist-thumb" src="${esc(v.thumbUrl)}" alt="${esc(v.code)}" loading="lazy" />
        <div style="min-width:0;flex:1;">
          <div style="display:flex;align-items:center;gap:5px;">
            <span style="font-size:10px;font-weight:900;padding:1px 5px;border-radius:3px;background:${esc(v.badgeColor)};color:#090d16;">${esc(v.code)}</span>
            <span style="font-size:10px;color:#94a3b8;">${esc(v.durationLabel)}</span>
          </div>
          <div style="font-size:11.5px;font-weight:800;color:#f8fafc;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-top:2px;">${esc(v.title.replace(/^[^\s]+\s/, ""))}</div>
        </div>
      </button>`;
    }).join("");

    const markersHtml = (activeVid.markers || [])
      .map(
        (m) =>
          `<button type="button" class="vox-marker-pill" data-jump-video-sec="${m.sec}">⏱ ${esc(m.label)}</button>`
      )
      .join("");

    const beatRowsHtml = beats.length
      ? beats
          .slice(0, 60)
          .map((b) => {
            const arch = String(b.scene_archetype || "cinema_full");
            const archMeta = CATALOG_24_ARCHETYPES.find((a) => a.id === arch);
            const previewUrl = b.preview_url || archMeta?.img || "/static/vox_studio/preview_00_cinema_open.jpg";
            const badgeBg = arch.startsWith("#M")
              ? "#0284c7"
              : arch.startsWith("#D")
              ? "#dc2626"
              : arch.startsWith("#P")
              ? "#d97706"
              : "#475569";
            return `<div class="vox-beat-item">
              <img src="${esc(previewUrl)}" alt="${esc(arch)}" data-vox-lightbox-img="${esc(previewUrl)}" data-vox-lightbox-title="${esc(b.beat_id)} · ${esc(arch)} (${esc(b.archetype_label || "")})" data-vox-lightbox-sub="${esc(b.narration_excerpt || "")}" />
              <div style="min-width:0;flex:1;">
                <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;">
                  <strong style="font-size:11.5px;color:#f8fafc;">${esc(b.beat_id)}</strong>
                  <span style="font-size:10.5px;font-weight:900;padding:1px 6px;border-radius:4px;background:${badgeBg};color:#fff;">${esc(arch)}</span>
                  <span style="font-size:11px;font-weight:700;color:#fde047;">${esc(b.archetype_label || archMeta?.name || "Cinema Archival")}</span>
                  ${b.blender_3d_scene ? `<button type="button" class="ghost compact" data-select-vox-video="${esc(b.blender_3d_scene)}" style="height:20px;min-height:20px;padding:0 6px;font-size:10px;color:#38bdf8;border-color:rgba(56,189,248,0.4);">🧊 Xem 3D Blender</button>` : ""}
                </div>
                <div style="font-size:11.5px;color:#cbd5e1;margin-top:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;" title="${esc(b.narration_excerpt || "")}">
                  🎙 ${esc(b.narration_excerpt || "Tư liệu hiện trường / Dẫn chuyện")}
                </div>
              </div>
            </div>`;
          })
          .join("")
      : `<div style="padding:18px;text-align:center;color:#94a3b8;font-size:12.5px;">Dự án đã sẵn sàng bộ định tuyến 24 Archetypes theo giọng đọc. Khi chạy bước Visuals / Edit, từng câu thoại sẽ tự động gắn Bản đồ Vệ tinh thật (#M1-#M8), Hồ sơ Pháp y (#D1-#D10) & Cảnh 3D Blender.</div>`;

    const catalogCardsHtml = filteredCatalog
      .map((item) => {
        const clusterBadge =
          item.cluster === "map"
            ? "🛰️ Vệ tinh thật"
            : item.cluster === "dossier"
            ? "🗂️ Hồ sơ Pháp y"
            : "📰 Báo chí & CRT";
        return `<article class="vox-arch-card">
          <div class="vox-arch-card-thumb" data-vox-lightbox-img="${esc(item.img)}" data-vox-lightbox-title="${esc(item.id)} · ${esc(item.name)}" data-vox-lightbox-sub="${esc(item.viDesc)}">
            <img src="${esc(item.img)}" alt="${esc(item.name)}" loading="lazy" />
            <span class="vox-arch-badge">${esc(item.id)} · ${clusterBadge}</span>
            <span class="vox-arch-zoom-tag">${esc(item.zoom)}</span>
          </div>
          <div class="vox-arch-card-body">
            <strong style="font-size:12px;color:#f8fafc;line-height:1.35;">${esc(item.name)}</strong>
            <p style="font-size:11px;color:#94a3b8;line-height:1.4;margin:0;flex:1;">${esc(item.viDesc)}</p>
            <div style="display:flex;gap:6px;margin-top:6px;">
              <button type="button" class="ghost compact" data-vox-lightbox-img="${esc(item.img)}" data-vox-lightbox-title="${esc(item.id)} · ${esc(item.name)}" data-vox-lightbox-sub="${esc(item.viDesc)}" style="flex:1;height:26px;min-height:26px;font-size:11px;">🔍 Phóng to 1080p</button>
              ${
                typeof item.jumpSec === "number"
                  ? `<button type="button" class="primary compact" data-jump-master-sec="${item.jumpSec}" style="flex:1;height:26px;min-height:26px;font-size:11px;">▶ Xem Motion</button>`
                  : ""
              }
            </div>
          </div>
        </article>`;
      })
      .join("");

    const lightboxHtml = state.lightboxImg
      ? `<div class="vox-lightbox-backdrop" id="cofiVoxLightboxBackdrop">
          <div class="vox-lightbox-modal">
            <div style="display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:10px;">
              <div>
                <strong style="font-size:15px;color:#facc15;">${esc(state.lightboxTitle)}</strong>
                <div style="font-size:12.5px;color:#cbd5e1;margin-top:2px;">${esc(state.lightboxSub)}</div>
              </div>
              <button type="button" class="ghost compact" id="cofiVoxCloseLightboxBtn">✕ Đóng (Esc)</button>
            </div>
            <div style="width:100%;aspect-ratio:16/9;background:#000;border-radius:8px;overflow:hidden;border:1px solid rgba(255,255,255,0.15);">
              <img src="${esc(state.lightboxImg)}" alt="${esc(state.lightboxTitle)}" style="width:100%;height:100%;object-fit:contain;display:block;" />
            </div>
          </div>
        </div>`
      : "";

    hostContainer.innerHTML = `
      <!-- THANH CHUYỂN ĐỔI ENGINE DỰNG VIDEO: BLENDER 3D + VOX SATELLITE vs REMOTION -->
      <div class="vox-blender-mode-bar">
        <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
          <span style="background:#facc15;color:#090d16;font-weight:900;font-size:11px;padding:3px 8px;border-radius:4px;letter-spacing:0.04em;">BLENDER 4.2 + VOX GIS</span>
          <div>
            <strong style="font-size:13.5px;color:#f8fafc;">Hệ Thống Dựng True Crime: Blender 3D EEVEE + Bản Đồ Vệ Tinh Thật Esri &amp; 24 Archetypes</strong>
            <div style="font-size:11.5px;color:#94a3b8;">Tự động phân cảnh theo giọng đọc (Voice-Driven Semantic Router) · Chống lặp bố cục · Kết hợp 100% với Remotion Timeline</div>
          </div>
        </div>
        <div class="vox-mode-tabs">
          <button type="button" class="vox-mode-tab ${state.viewMode === "split" ? "active" : ""}" data-set-edit-mode="split">⚡ Mở Cả Hai (Blender/Vox + Remotion)</button>
          <button type="button" class="vox-mode-tab ${state.viewMode === "vox_blender" ? "active" : ""}" data-set-edit-mode="vox_blender">🧊🛰️ Chỉ Mở Blender 3D &amp; Vox Studio</button>
          <button type="button" class="vox-mode-tab ${state.viewMode === "remotion" ? "active" : ""}" data-set-edit-mode="remotion">🎬 Chỉ Mở Remotion Timeline</button>
        </div>
      </div>

      <div class="vox-blender-studio-shell" id="cofiVoxBlenderMainPanel" style="display:${state.viewMode === "remotion" ? "none" : "block"};">
        <div class="vox-blender-top-grid">
          <!-- CỘT TRÁI: TRÌNH PHÁT VIDEO MASTER 5 PHÚT & 4 ĐẠI CẢNH 3D BLENDER 4.2 EEVEE -->
          <div class="vox-video-stage-card">
            <div style="display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:8px;flex-wrap:wrap;">
              <div>
                <span style="font-size:10.5px;font-weight:900;color:#facc15;letter-spacing:0.05em;">TRÌNH PHÁT BLENDER 4.2 EEVEE &amp; VOX SATELLITE MASTER</span>
                <h4 style="margin:2px 0 0;font-size:14px;color:#f8fafc;">${esc(activeVid.title)}</h4>
              </div>
              <span style="font-size:11px;font-weight:800;padding:3px 9px;border-radius:6px;background:rgba(34,197,94,0.16);color:#4ade80;border:1px solid rgba(34,197,94,0.4);">✓ Đã tích hợp Blender 4.2 + Esri GIS</span>
            </div>

            <div class="vox-video-player-wrap">
              <video id="cofiVoxBlenderVideoPlayer" controls playsinline preload="metadata" poster="${esc(activeVid.thumbUrl)}" src="${esc(activeVid.videoUrl)}"></video>
            </div>

            <p style="font-size:11.5px;color:#94a3b8;margin:7px 0 0;">${esc(activeVid.subtitle)}</p>

            ${
              markersHtml
                ? `<div class="vox-marker-pills">
                    <span style="font-size:11px;font-weight:800;color:#fde047;display:inline-flex;align-items:center;margin-right:4px;">⚡ Nhảy nhanh tới đại cảnh:</span>
                    ${markersHtml}
                  </div>`
                : ""
            }

            <div style="margin-top:10px;font-size:11px;font-weight:800;color:#38bdf8;text-transform:uppercase;">🎞 Chọn Xem Phim Master 5 Phút Hoặc Từng Đại Cảnh 3D Blender EEVEE:</div>
            <div class="vox-scene-playlist">
              ${playlistHtml}
            </div>
          </div>

          <!-- CỘT PHẢI: BỘ ĐỊNH TUYẾN PHÂN CẢNH THEO GIỌNG ĐỌC (VOICE-DRIVEN SEMANTIC ROUTER) -->
          <div class="vox-beat-router-card">
            <div style="display:flex;align-items:center;justify-content:space-between;gap:8px;flex-wrap:wrap;">
              <div>
                <span style="font-size:10.5px;font-weight:900;color:#38bdf8;letter-spacing:0.05em;">VOICE-DRIVEN SEMANTIC ROUTER</span>
                <h4 style="margin:2px 0 0;font-size:13.5px;color:#f8fafc;">Phân Cảnh Tự Động Theo Giọng Đọc (${beats.length} Beats)</h4>
              </div>
              <div style="display:flex;gap:5px;flex-wrap:wrap;">
                <span style="font-size:10.5px;font-weight:800;padding:2px 7px;border-radius:4px;background:rgba(2,132,199,0.2);color:#38bdf8;border:1px solid rgba(56,189,248,0.35);">🛰️ ${mapCount} Bản đồ</span>
                <span style="font-size:10.5px;font-weight:800;padding:2px 7px;border-radius:4px;background:rgba(220,38,38,0.2);color:#fca5a5;border:1px solid rgba(239,68,68,0.35);">🗂️ ${dossierCount} Hồ sơ</span>
                <span style="font-size:10.5px;font-weight:800;padding:2px 7px;border-radius:4px;background:rgba(217,119,6,0.2);color:#fde047;border:1px solid rgba(245,158,11,0.35);">📰 ${pressCount} Báo/CRT</span>
              </div>
            </div>
            <small style="font-size:11.5px;color:#94a3b8;">Hệ thống đọc từ khóa địa lý (Cam Túc, Bạch Ngân, Hoàng Hà...), pháp y (vân tay, Y-STR DNA, kính hiển vi...) và thời gian (1988, 1994, 1998, 28 năm...) trong câu thoại để tự chọn đúng kiểu bản đồ vệ tinh thật hoặc cảnh 3D Blender mà không bao giờ lặp lại 2 cảnh liền kề.</small>

            <div class="vox-beat-router-list">
              ${beatRowsHtml}
            </div>
          </div>
        </div>

        <!-- THƯ VIỆN 24 ARCHETYPES TRỰC QUAN (8 BẢN ĐỒ VỆ TINH THẬT + 10 HỒ SƠ PHÁP Y + 6 BÁO CHÍ/CRT) -->
        <details style="margin-top:14px;background:#111827;border:1px solid rgba(255,255,255,0.1);border-radius:10px;padding:10px 12px;" open>
          <summary style="cursor:pointer;font-size:13px;font-weight:800;color:#f8fafc;display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap;list-style:none;">
            <span>🛰️🗂️📰 THƯ VIỆN 24 ARCHETYPES ĐÃ TÍCH HỢP (8 BẢN ĐỒ VỆ TINH THẬT · 10 HỒ SƠ PHÁP Y &amp; LAB · 6 BÁO CHÍ &amp; CRT 90S)</span>
            <div style="display:inline-flex;gap:5px;flex-wrap:wrap;" onclick="event.stopPropagation();">
              <button type="button" class="ghost compact ${state.activeFilter === "all" ? "primary" : ""}" data-vox-filter="all" style="height:26px;min-height:26px;font-size:11px;">Tất cả (24)</button>
              <button type="button" class="ghost compact ${state.activeFilter === "map" ? "primary" : ""}" data-vox-filter="map" style="height:26px;min-height:26px;font-size:11px;">🛰️ 8 Bản đồ Vệ tinh (#M1-#M8)</button>
              <button type="button" class="ghost compact ${state.activeFilter === "dossier" ? "primary" : ""}" data-vox-filter="dossier" style="height:26px;min-height:26px;font-size:11px;">🗂️ 10 Hồ sơ Pháp y (#D1-#D10)</button>
              <button type="button" class="ghost compact ${state.activeFilter === "press" ? "primary" : ""}" data-vox-filter="press" style="height:26px;min-height:26px;font-size:11px;">📰 6 Báo chí &amp; CRT (#P1-#P6)</button>
            </div>
          </summary>
          <div class="vox-catalog-grid">
            ${catalogCardsHtml}
          </div>
        </details>
      </div>
      ${lightboxHtml}
    `;

    applyEditorVisibilityMode(hostContainer);

    // Bind events
    hostContainer.querySelectorAll("[data-set-edit-mode]").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.viewMode = btn.dataset.setEditMode || "split";
        localStorage.setItem("cofi-edit-engine-mode", state.viewMode);
        renderDom(hostContainer);
      });
    });

    hostContainer.querySelectorAll("[data-select-vox-video]").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.activeVideoId = btn.dataset.selectVoxVideo;
        renderDom(hostContainer);
        const vidEl = hostContainer.querySelector("#cofiVoxBlenderVideoPlayer");
        if (vidEl) {
          vidEl.play().catch(() => {});
        }
      });
    });

    hostContainer.querySelectorAll("[data-jump-video-sec]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const sec = Number(btn.dataset.jumpVideoSec || 0);
        const vidEl = hostContainer.querySelector("#cofiVoxBlenderVideoPlayer");
        if (vidEl) {
          vidEl.currentTime = sec;
          vidEl.play().catch(() => {});
        }
      });
    });

    hostContainer.querySelectorAll("[data-jump-master-sec]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const sec = Number(btn.dataset.jumpMasterSec || 0);
        state.activeVideoId = "vox_5min_master";
        renderDom(hostContainer);
        const vidEl = hostContainer.querySelector("#cofiVoxBlenderVideoPlayer");
        if (vidEl) {
          vidEl.addEventListener(
            "loadedmetadata",
            () => {
              vidEl.currentTime = sec;
              vidEl.play().catch(() => {});
            },
            { once: true }
          );
          vidEl.currentTime = sec;
          vidEl.play().catch(() => {});
        }
      });
    });

    hostContainer.querySelectorAll("[data-vox-filter]").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        state.activeFilter = btn.dataset.voxFilter || "all";
        renderDom(hostContainer);
      });
    });

    hostContainer.querySelectorAll("[data-vox-lightbox-img]").forEach((el) => {
      el.addEventListener("click", (e) => {
        e.stopPropagation();
        state.lightboxImg = el.dataset.voxLightboxImg;
        state.lightboxTitle = el.dataset.voxLightboxTitle || "Archetype Preview";
        state.lightboxSub = el.dataset.voxLightboxSub || "";
        renderDom(hostContainer);
      });
    });

    hostContainer.querySelector("#cofiVoxCloseLightboxBtn")?.addEventListener("click", () => {
      state.lightboxImg = null;
      renderDom(hostContainer);
    });
    hostContainer.querySelector("#cofiVoxLightboxBackdrop")?.addEventListener("click", (e) => {
      if (e.target.id === "cofiVoxLightboxBackdrop") {
        state.lightboxImg = null;
        renderDom(hostContainer);
      }
    });
  }

  window.mountCofiVoxBlenderStudio = async function (jobId, hostContainer) {
    if (!hostContainer) return;
    state.jobId = jobId;
    renderDom(hostContainer);

    if (jobId) {
      try {
        const resp = await fetch(`/api/jobs/${encodeURIComponent(jobId)}/artifacts/vox_scene_manifest.json?t=${Date.now()}`);
        if (resp.ok) {
          const payload = await resp.json();
          const parsed = typeof payload?.content === "string" ? JSON.parse(payload.content) : payload;
          if (parsed && Array.isArray(parsed.beats)) {
            state.voxManifest = parsed;
            renderDom(hostContainer);
            return;
          }
        }
      } catch (_) {}

      try {
        const vmResp = await fetch(`/api/jobs/${encodeURIComponent(jobId)}/artifacts/visual_manifest.json?t=${Date.now()}`);
        if (vmResp.ok) {
          const vmPayload = await vmResp.json();
          const vmParsed = typeof vmPayload?.content === "string" ? JSON.parse(vmPayload.content) : vmPayload;
          if (vmParsed && Array.isArray(vmParsed.beats)) {
            state.voxManifest = {
              job_id: jobId,
              beats: vmParsed.beats.map((b, idx) => ({
                beat_index: idx,
                beat_id: b.beat_id || b.id || `B${String(idx + 1).padStart(3, "0")}`,
                scene_archetype: b.scene_archetype || "cinema_full",
                archetype_label: b.archetype_label || "",
                archetype_cluster: b.archetype_cluster || "cinema",
                narration_excerpt: b.narration || b.voice_text || b.text || b.script_text || "",
              })),
            };
            renderDom(hostContainer);
          }
        }
      } catch (_) {}
    }
  };
})();
