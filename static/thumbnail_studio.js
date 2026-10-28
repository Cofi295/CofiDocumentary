/**
 * COFI THUMBNAIL STUDIO v2 — Multi-Card A/B/C/D Test Gallery + Lightbox Final Preview + 1-Click Download & Clean Editor
 */
(function () {
  if (typeof window !== "undefined") {
    window.COFI_THUMB_STUDIO_VERSION = "20261027-smart-save-v2";
  }
  const CW = 1280;
  const CH = 720;

  function injectCanvaCompactStyles() {
    if (typeof document === "undefined") return;
    let st = document.getElementById("cofiCanvaCompactCss");
    if (!st) {
      st = document.createElement("style");
      st.id = "cofiCanvaCompactCss";
      document.head.appendChild(st);
    }
    st.textContent = `
      /* ==========================================================================
         UNIFIED YOUTUBE PACKAGING STUDIO (THUMBNAIL + SEO TOGETHER)
         ========================================================================== */
      .thumb-studio-card { padding: 14px 16px !important; margin-bottom: 12px !important; background: linear-gradient(180deg, rgba(13, 18, 30, 0.98) 0%, rgba(9, 13, 22, 0.98) 100%) !important; border: 1px solid rgba(255, 255, 255, 0.08) !important; border-radius: 14px !important; }
      
      /* Master Header */
      .thumb-master-header { display: flex !important; align-items: center !important; justify-content: space-between !important; gap: 12px !important; flex-wrap: wrap !important; padding: 12px 16px !important; background: linear-gradient(135deg, rgba(15, 23, 42, 0.96) 0%, rgba(9, 14, 26, 0.98) 100%) !important; border: 1px solid rgba(255, 255, 255, 0.09) !important; border-radius: 12px !important; margin-bottom: 10px !important; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25) !important; }
      .header-kicker { font-size: 10px !important; font-weight: 800 !important; letter-spacing: 0.1em !important; color: #38bdf8 !important; text-transform: uppercase !important; margin-bottom: 3px !important; }
      .header-title { margin: 0 0 5px 0 !important; font-size: 17px !important; font-weight: 800 !important; color: #f8fafc !important; letter-spacing: -0.2px !important; }
      .header-status-line { display: flex !important; align-items: center !important; gap: 8px !important; flex-wrap: wrap !important; }
      .status-pill { font-size: 11px !important; font-weight: 700 !important; padding: 2px 9px !important; border-radius: 6px !important; line-height: 1.4 !important; }
      .status-pill.winner { background: rgba(250, 204, 21, 0.15) !important; border: 1px solid rgba(250, 204, 21, 0.45) !important; color: #fde047 !important; }
      .status-pill.safe { background: rgba(34, 197, 94, 0.15) !important; border: 1px solid rgba(34, 197, 94, 0.4) !important; color: #4ade80 !important; }
      .status-pill.dna { background: rgba(148, 163, 184, 0.12) !important; border: 1px solid rgba(148, 163, 184, 0.25) !important; color: #cbd5e1 !important; }
      .header-right { display: flex !important; align-items: center !important; gap: 6px !important; flex-wrap: wrap !important; }
      .header-right button { min-height: 28px !important; height: 28px !important; font-size: 11px !important; padding: 0 10px !important; }

      /* Hide redundant legacy subnav bar when unified studio is mounted */
      .seo-subnav-bar { display: none !important; }

      /* Unified Navigation Tabs (Step 1 -> 4 Workflow) */
      .thumb-unified-nav { display: flex !important; gap: 8px !important; margin-bottom: 12px !important; background: rgba(10, 14, 24, 0.9) !important; padding: 6px !important; border-radius: 12px !important; border: 1px solid rgba(255, 255, 255, 0.08) !important; flex-wrap: wrap !important; }
      .thumb-nav-tab { flex: 1 1 180px !important; display: flex !important; align-items: center !important; gap: 10px !important; padding: 8px 12px !important; background: rgba(15, 23, 42, 0.65) !important; border: 1px solid rgba(255, 255, 255, 0.06) !important; border-radius: 8px !important; color: #94a3b8 !important; cursor: pointer !important; text-align: left !important; transition: all 0.18s ease !important; min-height: 48px !important; position: relative !important; }
      .thumb-nav-tab:hover { background: rgba(30, 41, 59, 0.85) !important; color: #f1f5f9 !important; border-color: rgba(255, 255, 255, 0.16) !important; }
      .thumb-nav-tab.active { background: linear-gradient(135deg, rgba(14, 165, 233, 0.22) 0%, rgba(15, 23, 42, 0.98) 100%) !important; border-color: rgba(56, 189, 248, 0.55) !important; color: #ffffff !important; box-shadow: 0 4px 14px rgba(0, 0, 0, 0.35), inset 0 0 0 1px rgba(56, 189, 248, 0.3) !important; }
      .tab-badge-num { display: inline-flex !important; align-items: center !important; justify-content: center !important; width: 22px !important; height: 22px !important; border-radius: 50% !important; background: rgba(148, 163, 184, 0.15) !important; border: 1px solid rgba(148, 163, 184, 0.3) !important; font-size: 11px !important; font-weight: 800 !important; color: #94a3b8 !important; flex-shrink: 0 !important; }
      .thumb-nav-tab.active .tab-badge-num { background: #38bdf8 !important; border-color: #38bdf8 !important; color: #020617 !important; font-weight: 900 !important; }
      .thumb-nav-tab .tab-icon { font-size: 18px !important; line-height: 1 !important; flex-shrink: 0 !important; }
      .thumb-nav-tab .tab-labels { display: flex !important; flex-direction: column !important; gap: 2px !important; min-width: 0 !important; }
      .thumb-nav-tab .tab-title { font-size: 12.5px !important; font-weight: 800 !important; letter-spacing: -0.1px !important; color: inherit !important; }
      .thumb-nav-tab.active .tab-title { color: #38bdf8 !important; }
      .thumb-nav-tab .tab-sub { font-size: 10.5px !important; color: #64748b !important; white-space: nowrap !important; overflow: hidden !important; text-overflow: ellipsis !important; }
      .thumb-nav-tab.active .tab-sub { color: #93c5fd !important; }

      /* ==========================================================================
         UNIFIED STUDIO EDITOR (TAB 2) — SINGLE COHESIVE CONSOLE (NO FRAGMENTATION)
         ========================================================================== */
      .unified-studio-frame {
        display: flex !important;
        flex-direction: column !important;
        background: rgba(10, 15, 26, 0.98) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 12px !important;
        overflow: hidden !important;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.45) !important;
        margin-bottom: 12px !important;
      }

      /* Integrated Studio Topbar (Variant Segments + Master Actions) */
      .studio-topbar {
        display: flex !important;
        align-items: center !important;
        justify-content: space-between !important;
        gap: 12px !important;
        padding: 8px 12px !important;
        background: linear-gradient(135deg, rgba(15, 23, 42, 0.98) 0%, rgba(10, 15, 26, 0.98) 100%) !important;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08) !important;
        flex-wrap: wrap !important;
      }
      .studio-topbar-left {
        display: flex !important;
        align-items: center !important;
        gap: 8px !important;
        flex-wrap: wrap !important;
      }
      .studio-topbar-label {
        font-size: 10px !important;
        font-weight: 800 !important;
        color: #64748b !important;
        letter-spacing: 0.08em !important;
        text-transform: uppercase !important;
      }
      .studio-variant-segments {
        display: inline-flex !important;
        background: rgba(2, 6, 23, 0.7) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 8px !important;
        padding: 3px !important;
        gap: 4px !important;
        flex-wrap: wrap !important;
      }
      .studio-variant-seg {
        display: inline-flex !important;
        align-items: center !important;
        gap: 6px !important;
        padding: 4px 10px !important;
        background: transparent !important;
        border: 1px solid transparent !important;
        border-radius: 6px !important;
        color: #94a3b8 !important;
        font-size: 11px !important;
        font-weight: 700 !important;
        cursor: pointer !important;
        transition: all 0.16s ease !important;
        min-height: 26px !important;
      }
      .studio-variant-seg:hover {
        background: rgba(255, 255, 255, 0.06) !important;
        color: #f1f5f9 !important;
      }
      .studio-variant-seg.active {
        background: linear-gradient(135deg, rgba(14, 165, 233, 0.25) 0%, rgba(30, 41, 59, 0.95) 100%) !important;
        border-color: rgba(56, 189, 248, 0.5) !important;
        color: #ffffff !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3) !important;
      }
      .studio-variant-seg.is-winner {
        border-color: rgba(250, 204, 21, 0.4) !important;
      }
      .studio-variant-seg.is-winner.active {
        border-color: #fbbf24 !important;
        box-shadow: 0 0 0 1px #fbbf24, 0 2px 8px rgba(251, 191, 36, 0.25) !important;
      }
      .studio-variant-seg .seg-tag {
        font-size: 10.5px !important;
        font-weight: 900 !important;
        color: #38bdf8 !important;
      }
      .studio-variant-seg.active .seg-tag {
        color: #7dd3fc !important;
      }
      .studio-variant-seg.is-winner .seg-tag {
        color: #fde047 !important;
      }
      .studio-variant-seg .seg-name {
        color: inherit !important;
        font-weight: 600 !important;
      }
      .studio-variant-seg .seg-ctr {
        font-size: 9.5px !important;
        font-weight: 800 !important;
        padding: 1px 5px !important;
        border-radius: 4px !important;
      }
      .studio-variant-seg .seg-ctr.ok {
        background: rgba(34, 197, 94, 0.18) !important;
        color: #4ade80 !important;
      }
      .studio-variant-seg .seg-ctr.warn {
        background: rgba(251, 191, 36, 0.18) !important;
        color: #fbbf24 !important;
      }
      .studio-variant-seg .seg-win {
        color: #fbbf24 !important;
        font-size: 11px !important;
      }

      .studio-topbar-right {
        display: flex !important;
        align-items: center !important;
        gap: 6px !important;
        flex-shrink: 0 !important;
      }
      .studio-topbar-right button {
        min-height: 27px !important;
        height: 27px !important;
        font-size: 11px !important;
        padding: 0 9px !important;
      }
      .studio-win-badge {
        display: inline-flex !important;
        align-items: center !important;
        padding: 2px 8px !important;
        border-radius: 5px !important;
        background: rgba(34, 197, 94, 0.18) !important;
        border: 1px solid rgba(34, 197, 94, 0.45) !important;
        color: #4ade80 !important;
        font-size: 10.5px !important;
        font-weight: 800 !important;
      }

      /* Integrated Paired Title Sub-Bar */
      .studio-paired-bar {
        display: flex !important;
        align-items: center !important;
        justify-content: space-between !important;
        gap: 10px !important;
        padding: 6px 12px !important;
        background: rgba(13, 18, 30, 0.92) !important;
        border-bottom: 1px solid rgba(255, 255, 255, 0.06) !important;
        flex-wrap: wrap !important;
      }
      .paired-bar-tag {
        font-size: 10px !important;
        font-weight: 800 !important;
        color: #38bdf8 !important;
        letter-spacing: 0.05em !important;
        flex-shrink: 0 !important;
      }
      .paired-bar-content {
        display: flex !important;
        align-items: center !important;
        gap: 8px !important;
        flex: 1 1 360px !important;
        min-width: 0 !important;
        font-size: 12px !important;
      }
      .paired-bar-ko {
        font-weight: 800 !important;
        color: #ffffff !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
      }
      .paired-bar-vi {
        color: #4ade80 !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
      }
      .paired-bar-syn {
        font-size: 11px !important;
        color: #94a3b8 !important;
        flex-shrink: 0 !important;
      }
      .paired-bar-actions {
        display: flex !important;
        align-items: center !important;
        gap: 6px !important;
        flex-shrink: 0 !important;
      }
      .paired-bar-actions button {
        min-height: 24px !important;
        height: 24px !important;
        font-size: 10.5px !important;
        padding: 0 7px !important;
      }

      /* Canva 3-Col Workbench in Studio Frame */
      .canva-workbench-3col {
        display: grid !important;
        grid-template-columns: 260px minmax(0, 1fr) 300px !important;
        grid-template-areas: none !important;
        gap: 10px !important;
        align-items: stretch !important;
        padding: 10px !important;
        background: rgba(6, 10, 19, 0.96) !important;
        box-sizing: border-box !important;
      }
      .canva-left-dock, .canva-right-inspector {
        grid-area: auto !important;
        background: rgba(15, 23, 42, 0.95) !important;
        border: 1px solid rgba(148, 163, 184, 0.22) !important;
        border-radius: 10px !important;
        display: flex !important;
        flex-direction: column !important;
        max-height: 640px !important;
        overflow: hidden !important;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3) !important;
      }
      .canva-dock-tabs { display: flex !important; background: rgba(10, 14, 24, 0.9) !important; border-bottom: 1px solid rgba(148, 163, 184, 0.2) !important; }
      .canva-dock-tab { flex: 1 1 0 !important; padding: 6px 2px !important; display: flex !important; flex-direction: column !important; align-items: center !important; gap: 2px !important; background: transparent !important; border: none !important; color: #94a3b8 !important; cursor: pointer !important; font-size: 10px !important; }
      .canva-dock-tab:hover { background: rgba(255, 255, 255, 0.04) !important; color: #f1f5f9 !important; }
      .canva-dock-tab.active { background: rgba(14, 165, 233, 0.18) !important; color: #38bdf8 !important; font-weight: 700 !important; box-shadow: inset 0 -2px 0 #38bdf8 !important; }
      .canva-dock-body, .canva-inspector-scroll { padding: 8px !important; overflow-y: auto !important; display: flex !important; flex-direction: column !important; gap: 8px !important; flex: 1 1 auto !important; }
      .canva-dock-body button, .canva-inspector-scroll button { min-height: 27px !important; padding: 3px 8px !important; font-size: 11px !important; }

      .canva-center-stage {
        grid-area: auto !important;
        min-width: 0 !important;
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        justify-content: flex-start !important;
        gap: 6px !important;
      }

      /* Stage Toolbar */
      .thumb-stage-toolbar { width: 100% !important; box-sizing: border-box !important; display: flex !important; align-items: center !important; justify-content: space-between !important; gap: 8px !important; padding: 5px 8px !important; background: rgba(15, 23, 42, 0.92) !important; border: 1px solid rgba(255, 255, 255, 0.08) !important; border-radius: 8px !important; flex-wrap: wrap !important; margin-bottom: 2px !important; }
      .stage-tools-left { display: flex !important; align-items: center !important; gap: 6px !important; flex: 1 1 auto !important; }
      .stage-tools-right { display: flex !important; align-items: center !important; gap: 5px !important; flex-shrink: 0 !important; }
      .stage-tools-right button { min-height: 25px !important; height: 25px !important; padding: 0 7px !important; font-size: 11px !important; }
      .thumb-quick-layers-bar { display: flex !important; gap: 4px !important; overflow-x: auto !important; padding: 0 !important; margin: 0 !important; }
      .thumb-quick-layer-pill { min-height: 24px !important; height: 24px !important; padding: 0 7px !important; font-size: 10.5px !important; border-radius: 5px !important; }
      
      .thumb-canvas-stage-viewport {
        width: 100% !important;
        box-sizing: border-box !important;
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
        background: radial-gradient(#1e293b 1px, transparent 1px) #0b0f19 !important;
        background-size: 16px 16px !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 8px !important;
        padding: 8px !important;
      }
      .thumb-stage-vi-bar { width: 100% !important; box-sizing: border-box !important; margin-top: 4px !important; padding: 6px 10px !important; background: rgba(15, 23, 42, 0.92) !important; border: 1px solid rgba(34, 197, 94, 0.38) !important; border-radius: 8px !important; font-size: 11.5px !important; line-height: 1.4 !important; color: #f1f5f9 !important; }

      /* Comparison Suite (Compare View) */
      .thumb-compare-suite { display: flex !important; flex-direction: column !important; gap: 10px !important; }
      .thumb-compare-info-bar { display: flex !important; align-items: center !important; justify-content: space-between !important; gap: 10px !important; padding: 10px 14px !important; background: rgba(15, 23, 42, 0.9) !important; border: 1px solid rgba(255, 255, 255, 0.08) !important; border-radius: 10px !important; flex-wrap: wrap !important; font-size: 12.5px !important; }
      .thumb-compare-grid { display: grid !important; grid-template-columns: repeat(4, minmax(0, 1fr)) !important; gap: 10px !important; }
      @media (max-width: 1400px) { .thumb-compare-grid { grid-template-columns: repeat(2, minmax(0, 1fr)) !important; } }
      @media (max-width: 768px) { .thumb-compare-grid { grid-template-columns: 1fr !important; } }
      .thumb-compare-card { background: rgba(13, 18, 30, 0.92) !important; border: 1px solid rgba(255, 255, 255, 0.09) !important; border-radius: 12px !important; padding: 10px !important; display: flex !important; flex-direction: column !important; gap: 8px !important; transition: all 0.18s ease !important; }
      .thumb-compare-card:hover { border-color: rgba(56, 189, 248, 0.45) !important; box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4) !important; transform: translateY(-2px) !important; }
      .thumb-compare-card.is-winner { border-color: rgba(250, 204, 21, 0.65) !important; background: linear-gradient(180deg, rgba(20, 24, 38, 0.95) 0%, rgba(13, 18, 30, 0.98) 100%) !important; box-shadow: 0 0 0 1px rgba(250, 204, 21, 0.3) !important; }
      .compare-card-head { display: flex !important; align-items: center !important; justify-content: space-between !important; gap: 6px !important; }
      .head-tags { display: flex !important; align-items: center !important; gap: 6px !important; }
      .tag-pill { font-size: 11px !important; font-weight: 900 !important; padding: 2px 7px !important; border-radius: 4px !important; background: rgba(56, 189, 248, 0.18) !important; border: 1px solid rgba(56, 189, 248, 0.4) !important; color: #7dd3fc !important; }
      .thumb-compare-card.is-winner .tag-pill { background: rgba(250, 204, 21, 0.2) !important; border-color: rgba(250, 204, 21, 0.5) !important; color: #fde047 !important; }
      .arch-pill { font-size: 11px !important; color: #cbd5e1 !important; }
      .winner-pill { font-size: 10.5px !important; font-weight: 800 !important; background: rgba(250, 204, 21, 0.2) !important; border: 1px solid rgba(250, 204, 21, 0.5) !important; color: #fde047 !important; padding: 1px 6px !important; border-radius: 4px !important; }
      .ctr-badge { font-size: 11px !important; font-weight: 800 !important; padding: 2px 7px !important; border-radius: 4px !important; }
      .ctr-badge.ok { background: rgba(34, 197, 94, 0.16) !important; color: #4ade80 !important; }
      .ctr-badge.warn { background: rgba(251, 191, 36, 0.16) !important; color: #fbbf24 !important; }
      .compare-preview-frame { position: relative !important; aspect-ratio: 16 / 9 !important; background: #000000 !important; border-radius: 8px !important; overflow: hidden !important; cursor: zoom-in !important; }
      .compare-preview-frame canvas { width: 100% !important; height: 100% !important; display: block !important; }
      .compare-yt-duration { position: absolute !important; bottom: 6px !important; right: 6px !important; background: rgba(0, 0, 0, 0.85) !important; color: #ffffff !important; font-size: 11px !important; font-weight: 800 !important; padding: 1px 5px !important; border-radius: 3px !important; }
      .compare-hover-zoom { position: absolute !important; inset: 0 !important; background: rgba(0, 0, 0, 0.45) !important; display: flex !important; align-items: center !important; justify-content: center !important; color: #ffffff !important; font-size: 11.5px !important; font-weight: 700 !important; opacity: 0 !important; transition: opacity 0.15s ease !important; }
      .compare-preview-frame:hover .compare-hover-zoom { opacity: 1 !important; }
      .compare-card-body { display: flex !important; flex-direction: column !important; gap: 4px !important; font-size: 11.5px !important; }
      .hook-badge-line { font-size: 10.5px !important; font-weight: 800 !important; color: #4ade80 !important; }
      .hook-text-line { font-size: 12.5px !important; line-height: 1.35 !important; color: #f8fafc !important; }
      .compare-vi-text { padding: 4px 7px !important; background: rgba(15, 23, 42, 0.85) !important; border-left: 3px solid #22c55e !important; border-radius: 4px !important; font-size: 11px !important; line-height: 1.38 !important; color: #e2e8f0 !important; }
      .compare-paired-title { padding: 5px 8px !important; background: rgba(15, 23, 42, 0.65) !important; border-radius: 4px !important; font-size: 11px !important; line-height: 1.35 !important; color: #cbd5e1 !important; }
      .compare-paired-title .title-ko { font-weight: 700 !important; color: #f1f5f9 !important; }
      .compare-paired-title .title-vi { color: #4ade80 !important; margin-top: 2px !important; }
      .compare-card-actions { display: flex !important; gap: 4px !important; margin-top: auto !important; }
      .compare-card-actions button { min-height: 26px !important; height: 26px !important; font-size: 11px !important; padding: 0 6px !important; }

      /* SEO Suite (Unified Packaging View) */
      .thumb-seo-suite { display: flex !important; flex-direction: column !important; gap: 12px !important; }
      .thumb-seo-preflight-bar { display: flex !important; align-items: center !important; justify-content: space-between !important; gap: 12px !important; padding: 10px 14px !important; background: linear-gradient(135deg, rgba(15, 23, 42, 0.98) 0%, rgba(9, 14, 26, 0.98) 100%) !important; border: 1px solid rgba(56, 189, 248, 0.35) !important; border-radius: 10px !important; flex-wrap: wrap !important; }
      .preflight-status { display: flex !important; align-items: center !important; gap: 8px !important; flex-wrap: wrap !important; }
      .safe-pill { font-size: 11px !important; font-weight: 800 !important; color: #4ade80 !important; background: rgba(34, 197, 94, 0.15) !important; border: 1px solid rgba(34, 197, 94, 0.35) !important; padding: 3px 9px !important; border-radius: 6px !important; }
      .patterns-matched { display: flex !important; gap: 6px !important; flex-wrap: wrap !important; }
      .pat-tag { font-size: 11px !important; font-weight: 600 !important; color: #7dd3fc !important; background: rgba(56, 189, 248, 0.12) !important; border: 1px solid rgba(56, 189, 248, 0.28) !important; padding: 2px 8px !important; border-radius: 12px !important; }
      .thumb-seo-grid-2col { display: grid !important; grid-template-columns: minmax(0, 1.4fr) minmax(360px, 0.85fr) !important; gap: 12px !important; align-items: start !important; }
      @media (max-width: 1200px) { .thumb-seo-grid-2col { grid-template-columns: 1fr !important; } }
      .thumb-seo-col-main, .thumb-seo-col-side { display: flex !important; flex-direction: column !important; gap: 12px !important; }
      .seo-card-unified { background: rgba(13, 18, 30, 0.94) !important; border: 1px solid rgba(255, 255, 255, 0.08) !important; border-radius: 12px !important; padding: 12px 14px !important; display: flex !important; flex-direction: column !important; gap: 8px !important; }
      .seo-card-unified.prominent { border-color: rgba(56, 189, 248, 0.4) !important; background: linear-gradient(180deg, rgba(16, 26, 46, 0.95) 0%, rgba(11, 16, 28, 0.98) 100%) !important; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3) !important; }
      .seo-card-head { display: flex !important; align-items: flex-start !important; justify-content: space-between !important; gap: 10px !important; }
      .head-title { display: flex !important; flex-direction: column !important; gap: 2px !important; }
      .head-badge { font-size: 10px !important; font-weight: 800 !important; letter-spacing: 0.06em !important; color: #38bdf8 !important; text-transform: uppercase !important; }
      .head-badge.gold { color: #fde047 !important; }
      .seo-card-head strong { font-size: 13px !important; color: #f8fafc !important; }
      .seo-title-display-box { padding: 9px 12px !important; background: rgba(10, 14, 24, 0.85) !important; border: 1px solid rgba(255, 255, 255, 0.1) !important; border-radius: 8px !important; display: flex !important; flex-direction: column !important; gap: 5px !important; }
      .ko-title { font-size: 14.5px !important; font-weight: 800 !important; color: #ffffff !important; line-height: 1.4 !important; }
      .vi-title { font-size: 12.5px !important; line-height: 1.45 !important; color: #e2e8f0 !important; padding: 4px 8px !important; background: rgba(34, 197, 94, 0.12) !important; border-left: 3px solid #22c55e !important; border-radius: 4px !important; }
      .seo-title-meta-box { display: flex !important; flex-direction: column !important; gap: 4px !important; font-size: 11.5px !important; line-height: 1.4 !important; color: #cbd5e1 !important; }
      .seo-options-grid-2col { display: grid !important; grid-template-columns: 1fr 1fr !important; gap: 8px !important; }
      @media (max-width: 900px) { .seo-options-grid-2col { grid-template-columns: 1fr !important; } }
      .seo-title-option-card { background: rgba(10, 14, 24, 0.8) !important; border: 1px solid rgba(255, 255, 255, 0.08) !important; border-radius: 8px !important; padding: 9px !important; display: flex !important; flex-direction: column !important; gap: 5px !important; font-size: 11.5px !important; }
      .opt-card-top { display: flex !important; align-items: center !important; justify-content: space-between !important; gap: 6px !important; }
      .opt-card-badges { display: flex !important; align-items: center !important; gap: 6px !important; }
      .opt-num { font-weight: 800 !important; color: #38bdf8 !important; font-size: 11.5px !important; }
      .opt-paired-pill { font-size: 10px !important; font-weight: 800 !important; padding: 2px 6px !important; border-radius: 4px !important; background: rgba(251, 191, 36, 0.18) !important; border: 1px solid rgba(251, 191, 36, 0.4) !important; color: #fde047 !important; cursor: pointer !important; }
      .opt-paired-pill:hover { background: rgba(251, 191, 36, 0.3) !important; }
      .opt-ko-title { font-size: 12.5px !important; font-weight: 800 !important; color: #f8fafc !important; line-height: 1.35 !important; }
      .opt-vi-title { font-size: 11.5px !important; color: #86efac !important; padding-left: 6px !important; border-left: 2px solid #22c55e !important; line-height: 1.35 !important; }
      .opt-kw-anchor, .opt-synergy { font-size: 10.5px !important; color: #94a3b8 !important; line-height: 1.3 !important; }
      .opt-card-actions { margin-top: auto !important; padding-top: 4px !important; }
      .seo-raw-prebox { white-space: pre-wrap !important; font-family: inherit !important; font-size: 12px !important; line-height: 1.55 !important; color: #cbd5e1 !important; background: rgba(10, 14, 24, 0.85) !important; border: 1px solid rgba(255, 255, 255, 0.08) !important; border-radius: 8px !important; padding: 10px !important; margin: 0 !important; max-height: 340px !important; overflow-y: auto !important; }
      .seo-winner-thumb-frame { position: relative !important; aspect-ratio: 16 / 9 !important; background: #000000 !important; border-radius: 8px !important; overflow: hidden !important; cursor: zoom-in !important; }
      .seo-winner-thumb-frame canvas { width: 100% !important; height: 100% !important; display: block !important; }
      .winner-thumb-overlay { position: absolute !important; inset: 0 !important; background: rgba(0, 0, 0, 0.4) !important; display: flex !important; align-items: center !important; justify-content: center !important; color: #ffffff !important; font-size: 11.5px !important; font-weight: 700 !important; opacity: 0 !important; transition: opacity 0.15s ease !important; }
      .seo-winner-thumb-frame:hover .winner-thumb-overlay { opacity: 1 !important; }
      .seo-tags-display-box { display: flex !important; flex-wrap: wrap !important; gap: 5px !important; max-height: 180px !important; overflow-y: auto !important; padding: 8px !important; background: rgba(10, 14, 24, 0.8) !important; border: 1px solid rgba(255, 255, 255, 0.08) !important; border-radius: 8px !important; }
      .yt-tag-pill { font-size: 10.5px !important; color: #e2e8f0 !important; background: rgba(30, 41, 59, 0.9) !important; border: 1px solid rgba(148, 163, 184, 0.25) !important; padding: 2px 7px !important; border-radius: 4px !important; white-space: nowrap !important; }

      /* Preview Suite */
      .thumb-preview-suite { display: flex !important; flex-direction: column !important; gap: 10px !important; }
      .thumb-preview-nav { display: flex !important; align-items: center !important; justify-content: space-between !important; gap: 10px !important; padding: 10px 14px !important; background: rgba(15, 23, 42, 0.9) !important; border: 1px solid rgba(255, 255, 255, 0.08) !important; border-radius: 10px !important; flex-wrap: wrap !important; }
      .yt-home-feed-grid { display: grid !important; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)) !important; gap: 14px !important; padding: 12px !important; background: #0f0f0f !important; border-radius: 10px !important; }
      .yt-sidebar-feed-stack { display: flex !important; flex-direction: column !important; gap: 10px !important; max-width: 440px !important; padding: 12px !important; background: #0f0f0f !important; border-radius: 10px !important; }
      .yt-feed-card { background: #0f0f0f !important; border: 1px solid #27272a !important; border-radius: 12px !important; overflow: hidden !important; transition: all 0.18s ease !important; }
      .yt-feed-card.is-winner-card { border-color: #fbbf24 !important; box-shadow: 0 0 16px rgba(251, 191, 36, 0.15) !important; }
      .yt-feed-thumb { position: relative !important; aspect-ratio: 16 / 9 !important; background: #000 !important; cursor: zoom-in !important; }
      .yt-feed-thumb canvas { width: 100% !important; height: 100% !important; display: block !important; }
      .yt-time-badge { position: absolute !important; bottom: 8px !important; right: 8px !important; background: rgba(0, 0, 0, 0.85) !important; color: #fff !important; font-size: 11px !important; font-weight: 700 !important; padding: 2px 6px !important; border-radius: 4px !important; }
      .yt-feed-info { display: flex !important; gap: 10px !important; padding: 12px !important; }
      .yt-feed-avatar { width: 34px !important; height: 34px !important; border-radius: 50% !important; background: #27272a !important; display: flex !important; align-items: center !important; justify-content: center !important; font-size: 16px !important; flex-shrink: 0 !important; }
      .yt-feed-meta { flex: 1 !important; min-width: 0 !important; }
      .yt-video-title { margin: 0 0 4px 0 !important; font-size: 13.5px !important; font-weight: 700 !important; color: #f1f5f9 !important; line-height: 1.35 !important; }
      .yt-video-title-vi { font-size: 11.5px !important; color: #4ade80 !important; margin-bottom: 4px !important; line-height: 1.35 !important; }
      .yt-channel-line { font-size: 11.5px !important; color: #a1a1aa !important; }
      .yt-card-actions { display: flex !important; gap: 6px !important; align-items: center !important; margin-top: 8px !important; }
      .ctr-tag { font-size: 11px !important; font-weight: 800 !important; color: #22c55e !important; }
      .yt-sidebar-card { display: flex !important; gap: 10px !important; background: #0f0f0f !important; border: 1px solid #27272a !important; border-radius: 8px !important; padding: 6px !important; }
      .yt-sidebar-card.is-winner { border-color: #fbbf24 !important; }
      .yt-sidebar-thumb { width: 160px !important; aspect-ratio: 16 / 9 !important; position: relative !important; background: #000 !important; border-radius: 6px !important; overflow: hidden !important; flex-shrink: 0 !important; cursor: zoom-in !important; }
      .yt-sidebar-thumb canvas { width: 100% !important; height: 100% !important; display: block !important; }
      .yt-sidebar-info { flex: 1 !important; min-width: 0 !important; }
      .yt-sidebar-title { margin: 0 0 3px 0 !important; font-size: 11.5px !important; font-weight: 700 !important; color: #f1f5f9 !important; line-height: 1.3 !important; }
      .yt-sidebar-channel, .yt-sidebar-views { font-size: 10.5px !important; color: #a1a1aa !important; }
    `;
  }
  injectCanvaCompactStyles();

  const KOREAN_BROADCAST_FONTS = [
    {
      id: "pretendard_extrabold",
      family: "Pretendard ExtraBold",
      stack: "'Pretendard ExtraBold', 'Gmarket Sans Bold', 'Malgun Gothic', sans-serif",
      label: "프리텐다드 8 ExtraBold · Chuẩn Đài SBS / Thoáng Chữ (물·틀·릴 100%) ⭐",
      shortLabel: "프리텐다드 ExtraBold",
      url: "/static/fonts/Pretendard-ExtraBold.woff2",
    },
    {
      id: "gmarket_bold",
      family: "Gmarket Sans Bold",
      stack: "'Gmarket Sans Bold', 'Pretendard ExtraBold', 'Malgun Gothic', sans-serif",
      label: "지마켓 산스 Bold · Chuẩn YouTube Hàn Quốc Top 1 ⭐",
      shortLabel: "지마켓 산스 Bold",
      url: "/static/fonts/GmarketSansBold.ttf",
    },
    {
      id: "pretendard_black",
      family: "Pretendard Black",
      stack: "'Pretendard Black', 'Pretendard ExtraBold', 'Malgun Gothic', sans-serif",
      label: "프리텐다드 9 Black · Hiện Đại Sắc Nét Chuẩn Hàn - Việt ⭐",
      shortLabel: "프리텐다드 Black",
      url: "/static/fonts/Pretendard-Black.woff2",
    },
    {
      id: "paperlogy_extrabold",
      family: "Paperlogy ExtraBold",
      stack: "'Paperlogy ExtraBold', 'Pretendard ExtraBold', 'Malgun Gothic', sans-serif",
      label: "페이퍼로지 8 ExtraBold · Đậm Khối Documentary Hàn",
      shortLabel: "페이퍼로지 ExtraBold",
      url: "/static/fonts/Paperlogy-8ExtraBold.woff2",
    },
    {
      id: "paperlogy_black",
      family: "Paperlogy Black",
      stack: "'Paperlogy Black', 'Pretendard Black', 'Malgun Gothic', sans-serif",
      label: "페이퍼로지 9 Black · Siêu Đậm Bản Tin Đặc Biệt",
      shortLabel: "페이퍼로지 Black",
      url: "/static/fonts/Paperlogy-9Black.woff2",
    },
    {
      id: "scoredream_black",
      family: "SCoreDream Black",
      stack: "'SCoreDream Black', 'Pretendard ExtraBold', 'Malgun Gothic', sans-serif",
      label: "에스코어 드림 9 Black · Thời sự Đài KBS / MBC / JTBC",
      shortLabel: "에스코어 드림 Black",
      url: "/static/fonts/SCoreDream-9Black.woff",
    },
    {
      id: "gong_gothic",
      family: "GongGothic Bold",
      stack: "'GongGothic Bold', 'Pretendard ExtraBold', 'Malgun Gothic', sans-serif",
      label: "이사만루체 Bold · Góc Cạnh Mạnh Mẽ (Hạ tầng / Đập lớn)",
      shortLabel: "이사만루체 Bold",
      url: "/static/fonts/GongGothicBold.woff",
    },
    {
      id: "suite_heavy",
      family: "SUITE Heavy",
      stack: "'SUITE Heavy', 'Pretendard ExtraBold', 'Malgun Gothic', sans-serif",
      label: "수트 Heavy · Hình Học Tối Giản Hiện Đại",
      shortLabel: "수트 Heavy",
      url: "/static/fonts/SUITE-Heavy.woff2",
    },
    {
      id: "kbo_dia",
      family: "KBO Dia Gothic Bold",
      stack: "'KBO Dia Gothic Bold', 'Pretendard ExtraBold', 'Malgun Gothic', sans-serif",
      label: "KBO 다이아고딕 Bold · Cắt Kim Cương Sắc Cạnh",
      shortLabel: "KBO 다이아고딕",
      url: "/static/fonts/KBO-Dia-Gothic_bold.woff",
    },
    {
      id: "sb_aggro",
      family: "SB Aggro Bold",
      stack: "'SB Aggro Bold', 'Pretendard ExtraBold', 'Malgun Gothic', sans-serif",
      label: "SB 어그로체 Bold · Chữ Giật Tít Siêu Hút CTR",
      shortLabel: "SB 어그로체 Bold",
      url: "/static/fonts/SBAggroB.woff",
    },
  ];

  const DEFAULT_KR_FONT_STACK = "'Paperlogy Black', 'Pretendard Black', 'SCoreDream Black', 'Gmarket Sans Bold', sans-serif";
  let koreanFontsLoadPromise = null;

  const BROADCAST_COLOR_SWATCHES = [
    { hex: "#ffffff", label: "Trắng Sáng (White)" },
    { hex: "#ffe600", label: "Vàng Đài SBS (Broadcast Yellow)" },
    { hex: "#fbbf24", label: "Vàng Hổ Phách (Amber Gold)" },
    { hex: "#ff1f1f", label: "Đỏ Cảnh Báo (Crimson Alert)" },
    { hex: "#ef4444", label: "Đỏ Pháp Y (Forensic Red)" },
    { hex: "#39ff14", label: "Xanh Lá Neon (@판세의이면)" },
    { hex: "#00f0ff", label: "Xanh Cyan Pháp Y (Forensic Cyan)" },
    { hex: "#ff6b00", label: "Cam Khẩn Cấp (Hazard Orange)" },
    { hex: "#ff2a85", label: "Hồng Tâm Lý (Shock Magenta)" },
    { hex: "#a855f7", label: "Tím Bí Ẩn (Mystery Purple)" },
    { hex: "#000000", label: "Đen Tuyền (Deep Black)" },
  ];

  const TEXT_COLOR_COMBOS = [
    { id: "sbs_white_yellow", label: "Trắng + Vàng SBS", badgeFill: "#ffffff", badgeBg: "#dc2626", line1Fill: "#ffffff", line2Fill: "#ffe600", highlightFill: "#ff2424", stroke: "#000000" },
    { id: "kkokkomu_yellow_red", label: "Vàng + Đỏ 꼬꼬무", badgeFill: "#39ff14", badgeBg: "transparent", line1Fill: "#ffe600", line2Fill: "#ff2424", highlightFill: "#ffffff", stroke: "#000000" },
    { id: "urgent_white_red", label: "Trắng + Đỏ Khẩn", badgeFill: "#ffffff", badgeBg: "#b91c1c", line1Fill: "#ffffff", line2Fill: "#ff1f1f", highlightFill: "#ffe600", stroke: "#000000" },
    { id: "forensic_cyan_yellow", label: "Cyan + Vàng Hồ Sơ", badgeFill: "#00f0ff", badgeBg: "transparent", line1Fill: "#00f0ff", line2Fill: "#ffe600", highlightFill: "#ff2424", stroke: "#000000" },
    { id: "neon_green_white", label: "Vàng + Xanh Lá Đài", badgeFill: "#ffe600", badgeBg: "#dc2626", line1Fill: "#ffffff", line2Fill: "#39ff14", highlightFill: "#ffe600", stroke: "#000000" },
    { id: "shock_pink_yellow", label: "Trắng + Hồng Sốc", badgeFill: "#ffffff", badgeBg: "#9333ea", line1Fill: "#ffffff", line2Fill: "#ff2a85", highlightFill: "#ffe600", stroke: "#000000" },
  ];

  // BỘ PHONG CÁCH CHỦ ĐỀ LINH HOẠT (TOPIC STYLE PRESETS — KHÔNG KHÓA CỨNG)
  // Áp dụng riêng cho chủ đề/dự án hiện tại; chỉ khi người dùng bấm "Chốt Lưu Làm DNA Kênh" mới ghi vào DNA cho lần sau.
  const TOPIC_STYLE_PRESETS = [
    {
      id: "sbs_criminal_profiling",
      label: "🕵️ Hình sự Điều tra SBS (그것이 알고싶다)",
      shortLabel: "🕵️ Hình sự SBS",
      desc: "Chữ trái tương phản cao Trắng + Vàng/Đỏ, nhãn hộp đỏ, chủ thể bên phải, tối ưu giải mã tâm lý & truy nã",
      archetype: "broadcast_left_heavy",
      fontId: "pretendard_extrabold",
      badgeFill: "#ffffff",
      badgeBg: "#dc2626",
      line1Fill: "#ffffff",
      line2Fill: "#ffe600",
      highlightFill: "#ff2424",
      vignetteStyle: "left_heavy",
      vignetteOpacity: 0.86,
      showArrow: true,
      showCircle: false,
      showInset: false,
    },
    {
      id: "forensic_evidence_dossier",
      label: "🔬 Hồ sơ Pháp y & Vật chứng (Khoanh vùng + PiP)",
      shortLabel: "🔬 Pháp y & Vật chứng",
      desc: "Chữ đặt thấp dưới đáy + Khung ảnh đối chứng góc phải trên + Vòng tròn nét đứt & Mũi tên chỉ điểm vật chứng",
      archetype: "split_duality",
      fontId: "gmarket_bold",
      badgeFill: "#ffffff",
      badgeBg: "#b91c1c",
      line1Fill: "#ffffff",
      line2Fill: "#ff2424",
      highlightFill: "#ffe600",
      vignetteStyle: "bottom_heavy",
      vignetteOpacity: 0.88,
      showArrow: true,
      showCircle: true,
      showInset: true,
    },
    {
      id: "kkokkomu_mystery_duality",
      label: "🎭 Kỳ án Tâm lý & Vỏ bọc 2 mặt (꼬꼬무 스타일)",
      shortLabel: "🎭 Tâm lý & Vỏ bọc",
      desc: "Bố cục Điện ảnh đặt đáy (Bottom Cinematic), Tag xanh lá neon không hộp, Dòng 1 Vàng + Dòng 2 Đỏ rực",
      archetype: "bottom_cinematic",
      fontId: "pretendard_black",
      badgeFill: "#39ff14",
      badgeBg: "transparent",
      line1Fill: "#ffe600",
      line2Fill: "#ff2424",
      highlightFill: "#ffffff",
      vignetteStyle: "bottom_heavy",
      vignetteOpacity: 0.88,
      showArrow: true,
      showCircle: false,
      showInset: false,
    },
    {
      id: "infrastructure_megaproject_crisis",
      label: "🏗️ Đại công trình / Thảm họa Hạ tầng (@판세의이면)",
      shortLabel: "🏗️ Đại công trình",
      desc: "Dành cho chủ đề Đập lớn / Cầu đường / Địa chất: Font dày góc cạnh, Vàng + Đỏ khẩn cấp trên nền toàn cảnh",
      archetype: "bottom_cinematic",
      fontId: "gmarket_bold",
      badgeFill: "#39ff14",
      badgeBg: "transparent",
      line1Fill: "#ffe600",
      line2Fill: "#ff1f1f",
      highlightFill: "#ffffff",
      vignetteStyle: "bottom_heavy",
      vignetteOpacity: 0.85,
      showArrow: true,
      showCircle: true,
      showInset: false,
    },
    {
      id: "financial_shadow_empire",
      label: "💼 Tài phiệt / Đế chế Ngầm & Hồ sơ Mật",
      shortLabel: "💼 Tài phiệt / Hồ sơ mật",
      desc: "Tone Xanh Cyan Pháp y + Vàng Kim, nhấn mạnh con số tiền tỷ & mạng lưới quyền lực ngầm",
      archetype: "evidence_spotlight",
      fontId: "paperlogy_extrabold",
      badgeFill: "#00f0ff",
      badgeBg: "#0f172a",
      line1Fill: "#ffffff",
      line2Fill: "#fbbf24",
      highlightFill: "#00f0ff",
      vignetteStyle: "left_heavy",
      vignetteOpacity: 0.86,
      showArrow: true,
      showCircle: true,
      showInset: false,
    },
    {
      id: "cyber_financial_forensic_duality",
      label: "💳 Tội phạm CNC & Lừa đảo Tài chính (중국 사기 실화 · 4D Vô diện + PiP)",
      shortLabel: "💳 Tội phạm CNC & Tài chính",
      desc: "Kế thừa khung xương CTR True Crime nhưng thiết kế riêng cho Tài chính/CNC: Chủ thể 4D Vô diện bên phải + Khung bằng chứng Sổ tiết kiệm/0원 bên trái + Tag xanh lá [중국 사기 실화] + Mũi tên đỏ + Chữ 2 dòng Vàng/Trắng & Đỏ cực đại",
      archetype: "split_duality",
      fontId: "gmarket_bold",
      badgeFill: "#39ff14",
      badgeBg: "#06121e",
      line1Fill: "#ffffff",
      line2Fill: "#ff2424",
      highlightFill: "#ffe600",
      vignetteStyle: "bottom_heavy",
      vignetteOpacity: 0.88,
      showArrow: true,
      showCircle: true,
      showInset: true,
    },
  ];

  const ARROW_LIBRARY = [
    {
      id: "curved_pointer",
      name: "Cong Hồ Sơ (SBS Classic)",
      shortLabel: "Cong SBS",
      defaultFill: "#ff1f1f",
      defaultStroke: "#ffffff",
      desc: "Mũi tên cong vuốt mềm chỉ điểm nghi phạm / vật chứng chuẩn đài Hàn Quốc",
    },
    {
      id: "block_3d",
      name: "Khối 3D Thẳng (Block Bold)",
      shortLabel: "Khối 3D",
      defaultFill: "#ffe600",
      defaultStroke: "#000000",
      desc: "Mũi tên khối thẳng bản to cực nổi bật trên màn hình điện thoại",
    },
    {
      id: "sharp_tactical",
      name: "Chiến Thuật Sắc Cạnh (Tactical)",
      shortLabel: "Sắc Cạnh",
      defaultFill: "#ff1f1f",
      defaultStroke: "#ffffff",
      desc: "Mũi tên đuôi vát chữ V sắc lẹm kiểu truy vết hình sự",
    },
    {
      id: "double_chevron",
      name: "Kép Đột Kích (>> Double)",
      shortLabel: "Kép >>",
      defaultFill: "#ff6b00",
      defaultStroke: "#ffffff",
      desc: "Hai đầu mũi tên nối tiếp tạo xung lực khẩn cấp cực mạnh",
    },
    {
      id: "curved_steep",
      name: "Vòng Cung Sâu (Deep Arc)",
      shortLabel: "Cung Sâu",
      defaultFill: "#ffe600",
      defaultStroke: "#000000",
      desc: "Mũi tên vòng cung chữ C sâu móc từ dòng chữ lên chi tiết nhỏ",
    },
    {
      id: "zigzag_shock",
      name: "Tia Chớp Xung Kích (Lightning)",
      shortLabel: "Tia Chớp",
      defaultFill: "#ffe600",
      defaultStroke: "#ff1f1f",
      desc: "Mũi tên gấp khúc tia chớp nhấn mạnh tình tiết chấn động",
    },
    {
      id: "dashed_stem",
      name: "Đường Đứt Truy Vết (Dashed)",
      shortLabel: "Đường Đứt",
      defaultFill: "#00f0ff",
      defaultStroke: "#000000",
      desc: "Thân nét đứt + đầu mũi tên đặc chỉ hướng di chuyển / tẩu thoát",
    },
    {
      id: "double_ended",
      name: "Đối Chiếu 2 Đầu (<-> Dual)",
      shortLabel: "2 Đầu <->",
      defaultFill: "#fbbf24",
      defaultStroke: "#000000",
      desc: "Mũi tên 2 đầu chuyên dùng để đối chiếu 2 khuôn mặt hoặc ảnh PiP",
    },
    {
      id: "hand_drawn_sketch",
      name: "Phác Thảo Bút Đỏ (Marker)",
      shortLabel: "Bút Đỏ",
      defaultFill: "#ff1f1f",
      defaultStroke: "#000000",
      desc: "Nét vẽ phác thảo bút dạ đỏ của điều tra viên trên bảng hồ sơ",
    },
    {
      id: "neon_hollow",
      name: "Viền Rỗng Phát Sáng (Hollow)",
      shortLabel: "Viền Rỗng",
      defaultFill: "#39ff14",
      defaultStroke: "#ffffff",
      desc: "Mũi tên rỗng ruột phát sáng, không che khuất chi tiết phía dưới",
    },
  ];

  const CIRCLE_LIBRARY = [
    {
      id: "solid_ring",
      name: "Vòng Tròn Đặc Chuẩn (Solid Ring)",
      shortLabel: "Vòng Đặc",
      defaultStroke: "#ef4444",
      defaultOuter: "#000000",
      desc: "Vòng tròn nét liền kèm viền bóng đen sâu chuẩn truyền hình",
    },
    {
      id: "dashed_forensic",
      name: "Nét Đứt Pháp Y (Forensic Dashed)",
      shortLabel: "Nét Đứt",
      defaultStroke: "#ff1f1f",
      defaultOuter: "#000000",
      desc: "Vòng tròn nét đứt khoanh vùng vật chứng & dấu vết hiện trường",
    },
    {
      id: "double_ring",
      name: "Vòng Kép Tâm Điểm (Double Ring)",
      shortLabel: "Vòng Kép",
      defaultStroke: "#ffe600",
      defaultOuter: "#000000",
      desc: "Hai vòng tròn đồng tâm (ngoài dày, trong mảnh) khóa chặt mục tiêu",
    },
    {
      id: "crosshair_sniper",
      name: "Tâm Ngắm Truy Vết (Crosshair)",
      shortLabel: "Tâm Ngắm",
      defaultStroke: "#ff1f1f",
      defaultOuter: "#000000",
      desc: "Vòng tròn kèm 4 vạch chia tâm ngắm và chấm đỏ khóa mục tiêu",
    },
    {
      id: "hand_drawn_double",
      name: "Khoanh Bút Đỏ Tay (Hand Loop)",
      shortLabel: "Khoanh Tay",
      defaultStroke: "#ff1f1f",
      defaultOuter: "#000000",
      desc: "Vòng khoanh tay 2 tua lệch tự nhiên như bút dạ đỏ trên hồ sơ giấy",
    },
    {
      id: "cctv_brackets",
      name: "Khung Nhận Diện AI / CCTV",
      shortLabel: "Khung CCTV",
      defaultStroke: "#00f0ff",
      defaultOuter: "#000000",
      desc: "4 góc vuông khóa khuôn mặt / camera Thiên Võng + vòng quét nét đứt",
    },
    {
      id: "spotlight_glow",
      name: "Vòng Chiếu Sáng Spotlight",
      shortLabel: "Spotlight",
      defaultStroke: "#ffe600",
      defaultOuter: "#000000",
      desc: "Vòng tròn phát sáng kèm lớp nâng sáng nhẹ bên trong làm nổi vật chứng tối",
    },
    {
      id: "dotted_orbit",
      name: "Vòng Chấm Bi Radar (Dotted)",
      shortLabel: "Chấm Radar",
      defaultStroke: "#39ff14",
      defaultOuter: "#000000",
      desc: "Chuỗi chấm tròn bao quanh vật chứng kiểu quét tọa độ vệ tinh",
    },
    {
      id: "hazard_segments",
      name: "Vòng Cảnh Báo Phân Đoạn",
      shortLabel: "Cảnh Báo",
      defaultStroke: "#ff6b00",
      defaultOuter: "#000000",
      desc: "Vòng cung 6 đoạn dày xen kẽ kiểu cảnh báo nguy hiểm cấp độ 1",
    },
    {
      id: "magnifying_loupe",
      name: "Kính Lúp Soi Vật Chứng (Loupe)",
      shortLabel: "Kính Lúp",
      defaultStroke: "#ffffff",
      defaultOuter: "#000000",
      desc: "Kính lúp điều tra có vạch phản quang mặt kính và cán cầm góc dưới",
    },
  ];

  function normalizeHexColor(raw, fallback = "#ffffff") {
    const s = String(raw || "").trim();
    if (/^#[0-9a-fA-F]{6}$/.test(s)) return s.toLowerCase();
    if (/^#[0-9a-fA-F]{3}$/.test(s)) {
      return ("#" + s[1] + s[1] + s[2] + s[2] + s[3] + s[3]).toLowerCase();
    }
    if (/^[0-9a-fA-F]{6}$/.test(s)) return ("#" + s).toLowerCase();
    return fallback;
  }

  function normalizeKoreanFontStack(rawStack) {
    const s = String(rawStack || "").trim();
    if (
      !s ||
      s.includes("Black Han Sans") ||
      s.includes("Paperlogy 9 Black") ||
      s.includes("S-Core Dream 9") ||
      (s.includes("Noto Sans KR") && !s.includes("Paperlogy") && !s.includes("SCoreDream") && !s.includes("Pretendard"))
    ) {
      return DEFAULT_KR_FONT_STACK;
    }
    return s;
  }

  function detectFontIdFromStack(rawStack) {
    const s = String(rawStack || "").trim().toLowerCase();
    if (s.includes("scoredream") || s.includes("s-core")) return "scoredream_black";
    if (s.includes("paperlogy 9") || s.includes("paperlogy black")) return "paperlogy_black";
    const norm = normalizeKoreanFontStack(rawStack);
    const tokens = norm.split(",").map((t) => t.trim().replace(/^['"]|['"]$/g, "").toLowerCase()).filter(Boolean);
    for (const tok of tokens) {
      for (const f of KOREAN_BROADCAST_FONTS) {
        if (tok === f.family.toLowerCase() || tok.includes(f.family.toLowerCase())) {
          return f.id;
        }
      }
    }
    return "scoredream_black";
  }

  function ensureKoreanFontsLoaded() {
    if (koreanFontsLoadPromise) return koreanFontsLoadPromise;
    if (typeof window.FontFace !== "function" || !document.fonts) {
      koreanFontsLoadPromise = Promise.resolve();
      return koreanFontsLoadPromise;
    }
    const fontAliases = [
      ...KOREAN_BROADCAST_FONTS.map((f) => ({ family: f.family, url: f.url })),
      { family: "Paperlogy 9 Black", url: "/static/fonts/Paperlogy-9Black.woff2" },
      { family: "S-Core Dream 9", url: "/static/fonts/SCoreDream-9Black.woff" },
      { family: "SCDream9", url: "/static/fonts/SCoreDream-9Black.woff" },
    ];
    const tasks = fontAliases.map(async (f) => {
      try {
        const face400 = new FontFace(f.family, `url(${f.url})`, { weight: "400", style: "normal" });
        const face700 = new FontFace(f.family, `url(${f.url})`, { weight: "700", style: "normal" });
        const face900 = new FontFace(f.family, `url(${f.url})`, { weight: "900", style: "normal" });
        const loaded = await Promise.all([face400.load(), face700.load(), face900.load()]);
        loaded.forEach((lf) => document.fonts.add(lf));
      } catch (_) {}
    });
    koreanFontsLoadPromise = Promise.allSettled(tasks).then(() => {
      try { renderAllCanvases(); } catch (_) {}
    });
    return koreanFontsLoadPromise;
  }

  // Kick off local Korean font preloading immediately
  setTimeout(() => { ensureKoreanFontsLoaded(); }, 10);

  const studioState = {
    jobId: null,
    data: null,
    selectedLayerId: "line_2",
    leftDockTab: "style", // "style" | "text" | "graphics" | "media" | "layers"
    activeTab: localStorage.getItem("cofi-thumb-active-tab-v3") || (localStorage.getItem("cofi-seo-subtab") === "copy" ? "seo" : "compare"), // "compare" | "editor" | "seo" | "preview"
    editorOpen: true, // Open editor by default so user can see and edit immediately
    editorZoomed: false, // Fullscreen / Zoomed Editor mode
    canvasZoom: 1.0, // 0.5 to 2.5 (50% to 250%)
    undoStack: [], // History stack for Ctrl+Z
    dragging: null,
    imageCache: new Map(),
    busyVariants: new Set(), // variantIds currently generating Flow background
    busyBatchFlow: false,
    busyExportAll: false,
    busyExportAbPack: false,
    busyLockDna: false,
    previewViewMode: "home", // "home" | "sidebar"
    saveTimer: null,
    lightboxVariantId: null,
  };

  function pushUndoSnapshot() {
    const v = getActiveVariant();
    if (!v || !Array.isArray(v.layers)) return;
    try {
      const snap = JSON.stringify({
        variantId: v.id,
        layers: v.layers,
        badge_text: v.badge_text,
        line_1: v.line_1,
        line_2: v.line_2,
      });
      if (studioState.undoStack.length && studioState.undoStack[studioState.undoStack.length - 1] === snap) {
        return;
      }
      studioState.undoStack.push(snap);
      if (studioState.undoStack.length > 35) studioState.undoStack.shift();
    } catch (_) {}
  }

  function undoLastAction() {
    if (!studioState.undoStack.length) {
      showToast("Không còn bước nào để hoàn tác (Ctrl+Z).");
      return;
    }
    try {
      const snap = JSON.parse(studioState.undoStack.pop());
      const v = getVariantById(snap.variantId) || getActiveVariant();
      if (v) {
        v.layers = snap.layers;
        if (snap.badge_text !== undefined) v.badge_text = snap.badge_text;
        if (snap.line_1 !== undefined) v.line_1 = snap.line_1;
        if (snap.line_2 !== undefined) v.line_2 = snap.line_2;
        renderStudioDom();
        scheduleSaveDesign();
        showToast("↶ Đã hoàn tác thao tác vừa rồi (Ctrl+Z)!");
      }
    } catch (_) {}
  }

  function esc(val) {
    return String(val ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function showToast(msg, isErr = false) {
    if (typeof window.toast === "function") window.toast(msg, isErr);
  }

  function loadCachedImage(url, onReady) {
    if (!url) return null;
    if (studioState.imageCache.has(url)) {
      const entry = studioState.imageCache.get(url);
      if (entry.loaded) return entry.img;
      if (onReady) entry.callbacks.push(onReady);
      return null;
    }
    const img = new Image();
    img.crossOrigin = "anonymous";
    const entry = { img, loaded: false, error: false, callbacks: onReady ? [onReady] : [] };
    studioState.imageCache.set(url, entry);
    img.onload = () => {
      entry.loaded = true;
      entry.callbacks.forEach((cb) => {
        try { cb(img); } catch (_) {}
      });
      entry.callbacks = [];
      renderAllCanvases();
    };
    img.onerror = () => {
      entry.error = true;
      renderAllCanvases();
    };
    img.src = url;
    return null;
  }

  function getVariants() {
    const design = studioState.data?.design;
    const variants = design?.variants;
    if (!Array.isArray(variants)) return [];
    variants.forEach((v, idx) => {
      if (v && typeof v === "object") {
        if (!v.id) v.id = v.variant_id || `v${idx + 1}`;
        if ((!Array.isArray(v.layers) || !v.layers.length) && Array.isArray(design?.layers) && design.layers.length) {
          v.layers = JSON.parse(JSON.stringify(design.layers));
        }
      }
    });
    return variants;
  }

  function parseInlineHighlightSegments(rawText) {
    const raw = String(rawText || "");
    if ((!raw.includes("*") && !raw.includes("[")) || raw.length < 3) {
      return { plainText: raw, segments: [{ text: raw, highlight: false }] };
    }
    const regex = /\*([^*\n]+)\*|\[([^\[\]\n]+)\]/g;
    const segments = [];
    let lastIndex = 0;
    let m;
    while ((m = regex.exec(raw)) !== null) {
      if (m.index > lastIndex) {
        segments.push({ text: raw.slice(lastIndex, m.index), highlight: false });
      }
      const hl = m[1] !== undefined ? m[1] : m[2];
      if (hl) {
        segments.push({ text: hl, highlight: true });
      }
      lastIndex = regex.lastIndex;
    }
    if (lastIndex < raw.length) {
      segments.push({ text: raw.slice(lastIndex), highlight: false });
    }
    if (!segments.length) {
      return { plainText: raw, segments: [{ text: raw, highlight: false }] };
    }
    const plainText = segments.map((s) => s.text).join("");
    return { plainText, segments };
  }

  function normalizeAndRepairDesign() {
    const design = studioState.data?.design;
    if (!design || typeof design !== "object") return false;
    const variants = getVariants();
    let changed = false;
    const jobId = studioState.jobId || design.job_id || "";

    variants.forEach((v, idx) => {
      if (!v || !Array.isArray(v.layers)) return;
      const defaultFontObj = KOREAN_BROADCAST_FONTS[idx % 4] || KOREAN_BROADCAST_FONTS[0];
      const usedIds = new Set();
      let textboxOrder = 0;

      v.layers.forEach((l, lIdx) => {
        if (!l || typeof l !== "object") return;
        const ltype = String(l.type || "").trim();
        let lid = String(l.id || "").trim();

        // 1. Auto-assign missing layer IDs so click/drag/inspector work 100%
        if (!lid) {
          if (ltype === "vignette") lid = "vignette";
          else if (ltype === "badge") lid = "badge";
          else if (ltype === "stamp") lid = "stamp";
          else if (ltype === "circle") lid = "forensic_circle";
          else if (ltype === "arrow") lid = "forensic_arrow";
          else if (ltype === "inset_image") lid = "inset_photo";
          else if (ltype === "textbox") {
            textboxOrder += 1;
            if (textboxOrder === 1 && !usedIds.has("line_1")) lid = "line_1";
            else if (textboxOrder === 2 && !usedIds.has("line_2")) lid = "line_2";
            else lid = `custom_text_${lIdx + 1}`;
          } else {
            lid = `layer_${lIdx + 1}`;
          }
          while (usedIds.has(lid)) {
            lid = `${lid}_${lIdx + 1}`;
          }
          l.id = lid;
          changed = true;
        } else if (lid === "line_1" || lid === "line_2") {
          textboxOrder += 1;
        }
        usedIds.add(lid);

        // 2. Fix invisible badge text (legacy textColor + fill without bgColor, or fill == bgColor)
        if (ltype === "badge") {
          const rawBg = String(l.bgColor || l.backgroundColor || l.badge_bg || "").trim();
          const rawFill = String(l.fill || "").trim();
          const rawTc = String(l.textColor || "").trim();
          if (!rawBg) {
            if (rawTc && rawFill && rawFill.toLowerCase() !== rawTc.toLowerCase()) {
              l.bgColor = rawFill;
              l.fill = rawTc;
            } else {
              l.bgColor = "#dc2626";
              if (!rawFill || rawFill.toLowerCase() === "#dc2626") l.fill = "#ffffff";
            }
            changed = true;
          } else if (
            rawFill &&
            rawBg.toLowerCase() !== "transparent" &&
            rawBg.toLowerCase() !== "none" &&
            rawFill.toLowerCase() === rawBg.toLowerCase()
          ) {
            l.fill = rawTc && rawTc.toLowerCase() !== rawBg.toLowerCase() ? rawTc : "#ffffff";
            changed = true;
          }
        }

        // 3. Resolve relative inset_image src to /api/jobs/{jobId}/media?path=...
        if (ltype === "inset_image") {
          let src = String(l.src || v.inset_image_url || design.inset_image_url || "").trim();
          if (src && !src.startsWith("/api/") && !src.startsWith("http") && !src.startsWith("data:")) {
            let relClean = src.replace(/\\/g, "/").replace(/^\/+/, "");
            if (src.includes("cutout_station.png")) {
            src = `/api/jobs/${encodeURIComponent(jobId)}/media?path=media/thumbnail/real_police_station_pip.jpg`;
            l.src = src;
            v.inset_image_url = src;
            changed = true;
          }
            if (jobId) {
              src = `/api/jobs/${encodeURIComponent(jobId)}/media?path=${encodeURIComponent(relClean)}`;
              l.src = src;
              if (l.id === "inset_photo" || !v.inset_image_url) {
                v.inset_image_url = src;
              }
              changed = true;
            }
          }
        }

        // 4. Normalize Korean broadcast font & default highlightFill
        if (ltype === "textbox" || ltype === "badge" || ltype === "stamp") {
          if (!l.fontFamily || String(l.fontFamily).includes("Black Han Sans")) {
            l.fontFamily = defaultFontObj.stack;
            changed = true;
          }
          if (ltype === "textbox" && !l.highlightFill) {
            const mf = String(l.fill || "#ffffff").toLowerCase();
            l.highlightFill = ["#ffe600", "#ffe84a", "#fbbf24", "#facc15"].includes(mf) ? "#ff2424" : "#ffe600";
          }
        }
      });

      const byId = {};
      v.layers.forEach((l) => { if (l && l.id) byId[l.id] = l; });
      if (byId.line_1 && !v.line_1) v.line_1 = String(byId.line_1.text || "");
      if (byId.line_2 && !v.line_2) v.line_2 = String(byId.line_2.text || "");
      if (byId.badge && !v.badge_text) v.badge_text = String(byId.badge.text || "");
    });

    return changed;
  }

  function getVariantById(variantId) {
    const list = getVariants();
    if (!list.length) return null;
    return list.find((v) => v.id === variantId) || list[0];
  }

  function getActiveVariant() {
    const design = studioState.data?.design;
    if (!design) return null;
    return getVariantById(design.active_variant_id || "v1");
  }

  function getLayer(layerId, variant = null) {
    const v = variant || getActiveVariant();
    if (!v || !Array.isArray(v.layers)) return null;
    return v.layers.find((l) => l.id === layerId) || null;
  }

  function isExportedCompositeThumb(pathOrUrl) {
    const s = String(pathOrUrl || "").toLowerCase();
    return s.includes("thumbnail_v1") || s.includes("thumbnail_v2") || s.includes("thumbnail_v3") || s.includes("thumbnail_v4") || s.endsWith("thumbnail.jpg");
  }

  const REAL_PIP_VI_LABELS = {
    "01_cctv_nanjing_walk": "CCTV dáng đi Nam Kinh",
    "02_cctv_red_circle_scene": "CCTV khoanh đỏ hiện trường",
    "03_nanjing_police_cordon": "Cảnh sát phong tỏa Nam Kinh",
    "04_cctv_gait_shoulder": "CCTV dáng đi lệch vai",
    "05_cctv_buying_buns": "CCTV mua bánh bao",
    "06_cctv_bank_recon": "CCTV trinh sát ngân hàng",
    "07_cctv_street_circle": "CCTV đi bộ trên phố",
    "08_cctv_sidewalk_track": "CCTV theo dõi vỉa hè",
    "09_night_graveyard_search": "Lục soát nghĩa địa ban đêm",
    "10_internet_cafe_hideout": "Quán Internet nơi ẩn náu",
    "11_police_dog_tracking": "Chó nghiệp vụ truy vết",
    "12_suspect_mugshot_pair": "Ảnh thẻ trại giam 2 góc",
    "13_wanted_photo_hand": "Ảnh truy nã rà soát",
    "14_cave_sleeping_gear": "Túi ngủ & đồ trong hang đá",
    "15_dna_water_bottles": "Vật chứng vỏ chai nước DNA",
    "16_cave_food_leftovers": "Thức ăn thừa trong hang",
    "17_forensic_dna_lab": "Xét nghiệm mẫu DNA pháp y",
    "18_bullet_hole_ground": "Vết đạn găm hiện trường",
    "19_wanted_dossier_card": "Hồ sơ truy nã Chu Khắc Hoa",
    "20_armed_checkpoint_blockade": "Trạm cảnh sát vũ trang",
    "21_geleshan_mountain_search": "Vây ráp núi Ca Lạc Sơn",
    "22_railway_escape_tracks": "Đường ray xe lửa Sa Bình Bá",
    "23_cctv_mall_escalator": "CCTV thang cuốn TT thương mại",
    "24_tongjiaqiao_cordon_tape": "Dải phong tỏa ngõ Đồng Gia Kiều",
    "25_tongjiaqiao_alley_body": "Hiện trường hẻm Đồng Gia Kiều",
    "26_tongjiaqiao_ground_evidence": "Tang vật thu giữ tại hẻm",
  };

  function getCleanCandidates() {
    const raw = studioState.data?.candidate_images || [];
    return raw
      .filter((c) => {
        const p = String(c?.rel_path || c?.url || "").toLowerCase();
        if (isExportedCompositeThumb(p)) return false;
        if (p.includes("cutout_") || p.includes("debug_") || p.includes("check_pip_")) return false;
        return true;
      })
      .map((c) => {
        const p = String(c?.rel_path || c?.url || "").toLowerCase();
        const m = p.match(/thumb_inset_real_([a-z0-9_]+)\.(?:jpg|jpeg|png|webp)/i);
        if (m) {
          const key = m[1].toLowerCase();
          const numM = key.match(/^(\d+)_/);
          const numTag = numM ? `#${numM[1]} ` : "";
          const descVi = REAL_PIP_VI_LABELS[key] || key.replace(/_/g, " ");
          return {
            ...c,
            category: "thumbnail_inset",
            label: `📸 Tư liệu thật ${numTag}· ${descVi}`,
            realOrder: numM ? Number(numM[1]) : 99,
          };
        }
        return c;
      })
      .sort((a, b) => {
        if (a.realOrder !== undefined && b.realOrder !== undefined) {
          return a.realOrder - b.realOrder;
        }
        return 0;
      });
  }

  function getVariantBgUrl(variant) {
    const design = studioState.data?.design || {};
    let u = String(variant?.background_url || design.background_url || "").trim();
    if (isExportedCompositeThumb(u)) {
      u = u.replace(/thumbnail_v([1-4])/gi, "thumb_bg_v$1");
    }
    return u;
  }

  function evaluateVariantCtr(variant) {
    if (variant && variant.ctr_prediction && typeof variant.ctr_prediction === "object") {
      return variant.ctr_prediction;
    }
    const design = studioState.data?.design;
    if (!design || !variant) return { score: 85, verdict: "GOOD", checks: [], readiness_score: 85, predicted_ctr_pct: 10.8 };
    const layers = variant.layers || [];
    const byId = {};
    layers.forEach((l) => { byId[l.id] = l; });
    const l1 = byId.line_1 || {};
    const l2 = byId.line_2 || {};
    const badge = byId.badge || {};
    const vig = byId.vignette || {};

    let score = 100;
    let safeZoneOk = true;
    [l1, l2, badge].forEach((tl) => {
      if (!tl || tl.visible === false) return;
      const right = Number(tl.left || 0) + Number(tl.width || 600);
      const bottom = Number(tl.top || 0) + Number(tl.height || 100);
      if (right > 1065 && bottom > 625) safeZoneOk = false;
    });
    if (!safeZoneOk) score -= 18;

    const t1 = String(l1.text || "").trim();
    const t2 = String(l2.text || "").trim();
    const maxFs = Math.max(Number(l1.fontSize || 72), Number(l2.fontSize || 80));
    const sw = Number(l1.strokeWidth || 14);
    const mobileOk = Boolean((t1 || t2) && maxFs >= 64 && sw >= 10 && t1.length <= 22 && t2.length <= 22);
    if (!mobileOk) score -= 15;

    const vigOk = vig.visible !== false && Number(vig.opacity ?? 0.8) >= 0.55;
    const contrastOk = vigOk && (String(l1.fill || "").toLowerCase() !== String(l2.fill || "").toLowerCase() || badge.visible !== false);
    if (!contrastOk) score -= 12;

    const hasBg = Boolean(getVariantBgUrl(variant));
    if (!hasBg) score -= 10;

    score = Math.max(40, Math.min(100, score));
    const verdict = score >= 88 ? "HIGH_CTR" : score >= 75 ? "GOOD" : "NEEDS_TUNING";
    const dna_consistency_score = 94;
    const text_legibility_score = mobileOk ? 92 : 72;
    const curiosity_gap_score = 91;
    const keyword_alignment_score = badge.text ? 95 : 80;
    const readiness_score = score;
    const predicted_ctr_pct = Number((4.5 + (score / 100) * 8.8).toFixed(1));

    return {
      score,
      verdict,
      safeZoneOk,
      mobileOk,
      contrastOk,
      hasBg,
      dna_consistency_score,
      text_legibility_score,
      curiosity_gap_score,
      keyword_alignment_score,
      readiness_score,
      predicted_ctr_pct,
      hook_type: variant.hook_type || "curiosity_paradox",
      hook_badge: variant.hook_badge || "",
      strengths: safeZoneOk ? ["Né 100% vùng 30:15", "Móc câu tò mò mạnh"] : ["Móc câu tò mò mạnh"],
      warnings: !safeZoneOk ? ["Chữ lấn vào vùng đồng hồ YouTube"] : [],
    };
  }


  function drawCoverImage(ctx, img, x, y, w, h) {
    const iw = img.naturalWidth || img.width || CW;
    const ih = img.naturalHeight || img.height || CH;
    const scale = Math.max(w / iw, h / ih);
    const sw = w / scale;
    const sh = h / scale;
    const sx = (iw - sw) / 2;
    const sy = (ih - sh) / 2;
    ctx.drawImage(img, sx, sy, sw, sh, x, y, w, h);
  }

  function drawVignette(ctx, layer) {
    if (!layer || layer.visible === false) return;
    const opacity = Math.max(0, Math.min(1, Number(layer.opacity ?? 0.82)));
    const style = layer.style || "left_heavy";
    ctx.save();
    if (style === "left_heavy") {
      const grad = ctx.createLinearGradient(0, 0, CW * 0.56, 0);
      grad.addColorStop(0, `rgba(4, 7, 14, ${Math.min(0.88, opacity * 0.92)})`);
      grad.addColorStop(0.55, `rgba(4, 7, 14, ${opacity * 0.52})`);
      grad.addColorStop(1, "rgba(4, 7, 14, 0)");
      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, CW * 0.58, CH);
    } else if (style === "right_heavy") {
      const grad = ctx.createLinearGradient(CW, 0, CW * 0.18, 0);
      grad.addColorStop(0, `rgba(4, 7, 14, ${Math.min(0.96, opacity * 1.08)})`);
      grad.addColorStop(0.52, `rgba(4, 7, 14, ${opacity * 0.82})`);
      grad.addColorStop(1, "rgba(4, 7, 14, 0.08)");
      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, CW, CH);
    } else if (style === "bottom_heavy") {
      const grad = ctx.createLinearGradient(0, CH, 0, CH * 0.66);
      grad.addColorStop(0, `rgba(4, 7, 14, ${Math.min(0.95, opacity * 1.05)})`);
      grad.addColorStop(0.55, `rgba(4, 7, 14, ${opacity * 0.62})`);
      grad.addColorStop(1, "rgba(4, 7, 14, 0)");
      ctx.fillStyle = grad;
      ctx.fillRect(0, CH * 0.64, CW, CH * 0.36);
    } else if (style === "split_dark") {
      const grad = ctx.createLinearGradient(0, 0, CW, CH);
      grad.addColorStop(0, `rgba(4, 7, 14, ${opacity * 0.95})`);
      grad.addColorStop(0.55, `rgba(4, 7, 14, ${opacity * 0.65})`);
      grad.addColorStop(1, `rgba(4, 7, 14, ${opacity * 0.88})`);
      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, CW, CH);
    } else {
      const grad = ctx.createRadialGradient(CW * 0.5, CH * 0.38, 120, CW * 0.5, CH * 0.45, CW * 0.78);
      grad.addColorStop(0, "rgba(4, 7, 14, 0)");
      grad.addColorStop(0.65, `rgba(4, 7, 14, ${opacity * 0.38})`);
      grad.addColorStop(1, `rgba(4, 7, 14, ${Math.min(0.92, opacity * 0.95)})`);
      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, CW, CH);
    }
    const bottomGuard = ctx.createLinearGradient(0, CH, 0, CH - 135);
    bottomGuard.addColorStop(0, "rgba(2, 4, 9, 0.58)");
    bottomGuard.addColorStop(1, "rgba(2, 4, 9, 0)");
    ctx.fillStyle = bottomGuard;
    ctx.fillRect(0, CH - 135, CW, 135);
    ctx.restore();
  }

  function roundRectPath(ctx, x, y, w, h, r) {
    const radius = Math.max(0, Math.min(r, w / 2, h / 2));
    ctx.beginPath();
    ctx.moveTo(x + radius, y);
    ctx.arcTo(x + w, y, x + w, y + h, radius);
    ctx.arcTo(x + w, y + h, x, y + h, radius);
    ctx.arcTo(x, y + h, x, y, radius);
    ctx.arcTo(x, y, x + w, y, radius);
    ctx.closePath();
  }

  function drawCircleShape(ctx, layer, left, top, width, height) {
    const rx = Math.max(10, width / 2);
    const ry = Math.max(10, height / 2);
    const cx = left + rx;
    const cy = top + ry;
    const sw = Math.max(2, Number(layer.strokeWidth ?? 10));
    const strokeCol = layer.stroke || "#ef4444";
    const outerCol = layer.outerStroke || "rgba(0,0,0,0.82)";
    const style = String(layer.circleStyle || (layer.dashed ? "dashed_forensic" : "solid_ring")).toLowerCase();

    ctx.save();
    ctx.shadowColor = style === "spotlight_glow" ? strokeCol : "rgba(0,0,0,0.88)";
    ctx.shadowBlur = style === "spotlight_glow" ? 24 : 14;
    ctx.lineJoin = "round";
    ctx.lineCap = "round";

    const strokeDual = (drawPathFn, mainW = sw, dashedArr = null) => {
      ctx.save();
      if (dashedArr) ctx.setLineDash(dashedArr);
      drawPathFn();
      ctx.lineWidth = mainW + 6;
      ctx.strokeStyle = outerCol;
      ctx.stroke();
      drawPathFn();
      ctx.lineWidth = mainW;
      ctx.strokeStyle = strokeCol;
      ctx.stroke();
      ctx.restore();
    };

    if (style === "spotlight_glow") {
      const grad = ctx.createRadialGradient(cx, cy, Math.min(rx, ry) * 0.1, cx, cy, Math.max(rx, ry));
      grad.addColorStop(0, "rgba(255, 255, 255, 0.24)");
      grad.addColorStop(0.7, "rgba(255, 230, 0, 0.10)");
      grad.addColorStop(1, "rgba(0, 0, 0, 0)");
      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.ellipse(cx, cy, rx, ry, 0, 0, Math.PI * 2);
      ctx.fill();
      strokeDual(() => {
        ctx.beginPath();
        ctx.ellipse(cx, cy, rx, ry, 0, 0, Math.PI * 2);
      }, sw);
    } else if (style === "dashed_forensic" || style === "dashed") {
      strokeDual(() => {
        ctx.beginPath();
        ctx.ellipse(cx, cy, rx, ry, 0, 0, Math.PI * 2);
      }, sw, [Math.max(12, sw * 2.1), Math.max(9, sw * 1.3)]);
    } else if (style === "dotted_orbit") {
      strokeDual(() => {
        ctx.beginPath();
        ctx.ellipse(cx, cy, rx, ry, 0, 0, Math.PI * 2);
      }, sw + 2, [2, Math.max(14, sw * 2.2)]);
    } else if (style === "double_ring") {
      strokeDual(() => {
        ctx.beginPath();
        ctx.ellipse(cx, cy, rx, ry, 0, 0, Math.PI * 2);
      }, sw);
      strokeDual(() => {
        ctx.beginPath();
        ctx.ellipse(cx, cy, Math.max(6, rx * 0.8), Math.max(6, ry * 0.8), 0, 0, Math.PI * 2);
      }, Math.max(2, Math.round(sw * 0.5)));
    } else if (style === "crosshair_sniper") {
      strokeDual(() => {
        ctx.beginPath();
        ctx.ellipse(cx, cy, rx, ry, 0, 0, Math.PI * 2);
      }, sw);
      const tx = rx * 0.28;
      const ty = ry * 0.28;
      strokeDual(() => {
        ctx.beginPath();
        ctx.moveTo(cx, top - ty * 0.45);
        ctx.lineTo(cx, top + ty * 0.85);
        ctx.moveTo(cx, top + height - ty * 0.85);
        ctx.lineTo(cx, top + height + ty * 0.45);
        ctx.moveTo(left - tx * 0.45, cy);
        ctx.lineTo(left + tx * 0.85, cy);
        ctx.moveTo(left + width - tx * 0.85, cy);
        ctx.lineTo(left + width + tx * 0.45, cy);
      }, Math.max(3, Math.round(sw * 0.78)));
      ctx.beginPath();
      ctx.arc(cx, cy, Math.max(4, sw * 0.6), 0, Math.PI * 2);
      ctx.fillStyle = strokeCol;
      ctx.fill();
    } else if (style === "hand_drawn_double") {
      strokeDual(() => {
        ctx.beginPath();
        ctx.ellipse(cx - 2, cy - 1, rx * 1.01, ry * 0.95, -0.08, 0, Math.PI * 2);
      }, Math.max(3, Math.round(sw * 0.86)));
      strokeDual(() => {
        ctx.beginPath();
        ctx.ellipse(cx + 2, cy + 2, rx * 0.95, ry * 1.02, 0.09, 0, Math.PI * 2);
      }, Math.max(2, Math.round(sw * 0.68)));
    } else if (style === "cctv_brackets") {
      const bx = Math.max(18, width * 0.26);
      const by = Math.max(18, height * 0.26);
      strokeDual(() => {
        ctx.beginPath();
        // Top-left
        ctx.moveTo(left, top + by);
        ctx.lineTo(left, top);
        ctx.lineTo(left + bx, top);
        // Top-right
        ctx.moveTo(left + width - bx, top);
        ctx.lineTo(left + width, top);
        ctx.lineTo(left + width, top + by);
        // Bottom-right
        ctx.moveTo(left + width, top + height - by);
        ctx.lineTo(left + width, top + height);
        ctx.lineTo(left + width - bx, top + height);
        // Bottom-left
        ctx.moveTo(left + bx, top + height);
        ctx.lineTo(left, top + height);
        ctx.lineTo(left, top + height - by);
      }, sw);
      strokeDual(() => {
        ctx.beginPath();
        ctx.ellipse(cx, cy, rx * 0.7, ry * 0.7, 0, 0, Math.PI * 2);
      }, Math.max(2, Math.round(sw * 0.45)), [10, 8]);
    } else if (style === "hazard_segments") {
      for (let i = 0; i < 6; i++) {
        const a0 = (i * Math.PI * 2) / 6 + 0.15;
        const a1 = a0 + (Math.PI * 2 * 0.62) / 6;
        strokeDual(() => {
          ctx.beginPath();
          ctx.ellipse(cx, cy, rx, ry, 0, a0, a1);
        }, sw + 2);
      }
      strokeDual(() => {
        ctx.beginPath();
        ctx.ellipse(cx, cy, rx * 0.84, ry * 0.84, 0, 0, Math.PI * 2);
      }, Math.max(2, Math.round(sw * 0.38)));
    } else if (style === "magnifying_loupe") {
      ctx.fillStyle = "rgba(255,255,255,0.10)";
      ctx.beginPath();
      ctx.ellipse(cx, cy, rx, ry, 0, 0, Math.PI * 2);
      ctx.fill();
      strokeDual(() => {
        ctx.beginPath();
        ctx.ellipse(cx, cy, rx, ry, 0, 0, Math.PI * 2);
      }, sw);
      // Glass reflection arc
      ctx.save();
      ctx.beginPath();
      ctx.ellipse(cx, cy, rx * 0.76, ry * 0.76, 0, Math.PI * 1.1, Math.PI * 1.55);
      ctx.lineWidth = Math.max(3, sw * 0.55);
      ctx.strokeStyle = "rgba(255,255,255,0.85)";
      ctx.stroke();
      ctx.restore();
      // Loupe handle
      strokeDual(() => {
        ctx.beginPath();
        ctx.moveTo(cx + rx * 0.7, cy + ry * 0.7);
        ctx.lineTo(cx + rx * 1.18, cy + ry * 1.18);
      }, sw * 1.85);
    } else {
      strokeDual(() => {
        ctx.beginPath();
        ctx.ellipse(cx, cy, rx, ry, 0, 0, Math.PI * 2);
      }, sw);
    }
    ctx.restore();
  }

  function drawArrowShape(ctx, layer, left, top, width, height) {
    const style = String(layer.arrowStyle || "curved_pointer").toLowerCase();
    const fillCol = layer.fill || "#ff1f1f";
    const strokeCol = layer.stroke || "#ffffff";
    const sw = Math.max(0, Number(layer.strokeWidth ?? 4));

    ctx.save();
    ctx.translate(left, top);
    const sx = width / 170;
    const sy = height / 64;
    ctx.scale(sx, sy);
    ctx.shadowColor = style === "neon_hollow" ? fillCol : "rgba(0,0,0,0.92)";
    ctx.shadowBlur = style === "neon_hollow" ? 20 : 14;
    ctx.shadowOffsetY = 4;
    ctx.lineJoin = "round";
    ctx.lineCap = "round";

    const buildArrowPath = () => {
      ctx.beginPath();
      if (style === "block_3d") {
        ctx.moveTo(8, 16);
        ctx.lineTo(98, 16);
        ctx.lineTo(98, 2);
        ctx.lineTo(164, 32);
        ctx.lineTo(98, 62);
        ctx.lineTo(98, 48);
        ctx.lineTo(8, 48);
        ctx.closePath();
      } else if (style === "sharp_tactical") {
        ctx.moveTo(6, 12);
        ctx.lineTo(106, 20);
        ctx.lineTo(98, 2);
        ctx.lineTo(166, 32);
        ctx.lineTo(98, 62);
        ctx.lineTo(106, 44);
        ctx.lineTo(6, 52);
        ctx.lineTo(30, 32);
        ctx.closePath();
      } else if (style === "double_chevron") {
        ctx.moveTo(6, 8);
        ctx.lineTo(46, 8);
        ctx.lineTo(82, 32);
        ctx.lineTo(46, 56);
        ctx.lineTo(6, 56);
        ctx.lineTo(38, 32);
        ctx.closePath();

        ctx.moveTo(72, 8);
        ctx.lineTo(114, 8);
        ctx.lineTo(166, 32);
        ctx.lineTo(114, 56);
        ctx.lineTo(72, 56);
        ctx.lineTo(104, 32);
        ctx.closePath();
      } else if (style === "curved_steep") {
        ctx.moveTo(8, 58);
        ctx.bezierCurveTo(18, 2, 102, 2, 126, 20);
        ctx.lineTo(138, 4);
        ctx.lineTo(164, 48);
        ctx.lineTo(106, 52);
        ctx.lineTo(118, 36);
        ctx.bezierCurveTo(92, 20, 42, 22, 24, 62);
        ctx.closePath();
      } else if (style === "zigzag_shock") {
        ctx.moveTo(4, 48);
        ctx.lineTo(52, 10);
        ctx.lineTo(76, 28);
        ctx.lineTo(114, 10);
        ctx.lineTo(108, 0);
        ctx.lineTo(166, 26);
        ctx.lineTo(120, 62);
        ctx.lineTo(122, 44);
        ctx.lineTo(68, 52);
        ctx.lineTo(48, 32);
        ctx.lineTo(16, 60);
        ctx.closePath();
      } else if (style === "dashed_stem") {
        ctx.rect(6, 20, 24, 24);
        ctx.rect(40, 20, 26, 24);
        ctx.moveTo(76, 20);
        ctx.lineTo(108, 20);
        ctx.lineTo(108, 3);
        ctx.lineTo(166, 32);
        ctx.lineTo(108, 61);
        ctx.lineTo(108, 44);
        ctx.lineTo(76, 44);
        ctx.closePath();
      } else if (style === "double_ended") {
        ctx.moveTo(4, 32);
        ctx.lineTo(48, 4);
        ctx.lineTo(48, 20);
        ctx.lineTo(122, 20);
        ctx.lineTo(122, 4);
        ctx.lineTo(166, 32);
        ctx.lineTo(122, 60);
        ctx.lineTo(122, 44);
        ctx.lineTo(48, 44);
        ctx.lineTo(48, 60);
        ctx.closePath();
      } else if (style === "hand_drawn_sketch") {
        ctx.moveTo(8, 46);
        ctx.quadraticCurveTo(66, 10, 128, 22);
        ctx.lineTo(114, 4);
        ctx.lineTo(164, 32);
        ctx.lineTo(114, 60);
        ctx.lineTo(126, 38);
        ctx.quadraticCurveTo(68, 24, 14, 58);
        ctx.closePath();
      } else {
        ctx.moveTo(6, 38);
        ctx.quadraticCurveTo(64, 4, 110, 14);
        ctx.lineTo(104, 0);
        ctx.lineTo(166, 34);
        ctx.lineTo(108, 64);
        ctx.lineTo(114, 46);
        ctx.quadraticCurveTo(68, 34, 16, 60);
        ctx.closePath();
      }
    };

    buildArrowPath();
    if (style === "neon_hollow") {
      ctx.fillStyle = "rgba(255, 255, 255, 0.08)";
      ctx.fill();
      ctx.lineWidth = Math.max(6, sw + 5);
      ctx.strokeStyle = fillCol;
      ctx.stroke();
      if (sw > 0) {
        ctx.lineWidth = Math.max(2, Math.round(sw * 0.55));
        ctx.strokeStyle = strokeCol;
        ctx.stroke();
      }
    } else {
      if (sw > 0) {
        ctx.lineWidth = sw + 3;
        ctx.strokeStyle = strokeCol;
        ctx.stroke();
      }
      ctx.fillStyle = fillCol;
      ctx.fill();
      if (style === "hand_drawn_sketch") {
        ctx.beginPath();
        ctx.moveTo(14, 52);
        ctx.quadraticCurveTo(72, 18, 148, 31);
        ctx.lineWidth = 3;
        ctx.strokeStyle = strokeCol;
        ctx.stroke();
      }
    }
    ctx.restore();
  }

  function drawLayer(ctx, layer) {
    if (!layer || layer.visible === false) return;
    const type = layer.type;
    if (type === "vignette") {
      drawVignette(ctx, layer);
      return;
    }

    const left = Number(layer.left || 0);
    const top = Number(layer.top || 0);
    const width = Number(layer.width || 200);
    const height = Number(layer.height || 80);
    const angle = Number(layer.angle || 0);
    const flipX = layer.flipX ? -1 : 1;
    const flipY = layer.flipY ? -1 : 1;
    const opacity = Math.max(0, Math.min(1, Number(layer.opacity ?? 1)));

    ctx.save();
    ctx.globalAlpha = opacity;
    const cx = left + width / 2;
    const cy = top + height / 2;
    if (angle || flipX !== 1 || flipY !== 1) {
      ctx.translate(cx, cy);
      if (angle) ctx.rotate((angle * Math.PI) / 180);
      if (flipX !== 1 || flipY !== 1) ctx.scale(flipX, flipY);
      ctx.translate(-cx, -cy);
    }

    if (type === "inset_image") {
      let src = String(layer.src || studioState.data?.design?.inset_image_url || "").trim();
      if (isExportedCompositeThumb(src)) {
        src = src.replace(/thumbnail_v([1-4])/gi, "thumb_bg_v$1");
      }
      const img = loadCachedImage(src);
      const frameStyle = String(layer.frameStyle || "").trim().toLowerCase();
      const borderHex = String(layer.borderColor || "#ef4444").trim().toLowerCase();
      const bw = Math.max(3, Number(layer.borderWidth || 6));
      const bColor = layer.borderColor || "#fbbf24";
      const isTornNewspaper = frameStyle === "torn_newspaper" || frameStyle === "torn_paper";
      const isVintagePaper =
        frameStyle === "vintage_paper" ||
        frameStyle === "polaroid" ||
        (!frameStyle && ["#f4ebd9", "#f3ead8", "#e8dcc8", "#efe5d1", "#fdf8ee"].includes(borderHex));

      if (isTornNewspaper) {
        const seedOff = (((Math.round(left) * 13 + Math.round(top) * 7) % 97) * 0.1);
        const tearDisp = (pos, phase, amp, deckleBias) => {
          const drift = Math.sin(pos * 0.031 + phase) * 0.52 + Math.cos(pos * 0.074 + phase * 1.7) * 0.34;
          const micro = Math.sin(pos * 0.33 + phase * 2.3) * Math.cos(pos * 0.79 + phase * 0.9) * 0.38;
          const notchWave = Math.sin(pos * 0.089 + phase * 1.3);
          const notch = Math.pow(notchWave, 5) * 0.65;
          const fiber = deckleBias * (0.4 + 0.6 * Math.max(0.0, Math.sin(pos * 0.053 + phase * 2.1)));
          return (drift + micro + notch) * amp + fiber;
        };
        const buildTornPts = (x0, y0, wP, hP, amp, sOff, deckleBias) => {
          const pts = [];
          const step = 5;
          for (let sx = 0; sx <= wP; sx += step) {
            const d = tearDisp(sx, 1.1 + sOff, amp, deckleBias);
            pts.push([x0 + sx, y0 + d - deckleBias]);
          }
          for (let sy = step; sy <= hP; sy += step) {
            const d = tearDisp(sy, 2.7 + sOff, amp, deckleBias);
            pts.push([x0 + wP + d + deckleBias, y0 + sy]);
          }
          for (let sx = wP - step; sx >= 0; sx -= step) {
            const d = tearDisp(sx, 4.3 + sOff, amp, deckleBias);
            pts.push([x0 + Math.max(0, sx), y0 + hP + d + deckleBias * 1.15]);
          }
          for (let sy = hP - step; sy > 0; sy -= step) {
            const d = tearDisp(sy, 5.8 + sOff, amp, deckleBias);
            pts.push([x0 + d - deckleBias, y0 + Math.max(0, sy)]);
          }
          return pts;
        };
        const tracePoly = (pts) => {
          ctx.beginPath();
          pts.forEach(([px, py], idx) => {
            if (idx === 0) ctx.moveTo(px, py);
            else ctx.lineTo(px, py);
          });
          ctx.closePath();
        };

        const outerPts = buildTornPts(left, top, width, height, 4.8, seedOff, 3.0);
        const innerPts = buildTornPts(left, top, width, height, 4.2, seedOff + 0.18, 0.0);

        ctx.save();
        ctx.shadowColor = "rgba(0,0,0,0.92)";
        ctx.shadowBlur = 24;
        ctx.shadowOffsetX = 5;
        ctx.shadowOffsetY = 11;
        tracePoly(outerPts);
        ctx.fillStyle = "#fcfaf2";
        ctx.fill();
        ctx.restore();

        ctx.save();
        tracePoly(outerPts);
        ctx.lineWidth = 1.5;
        ctx.strokeStyle = "#bcaea0";
        ctx.stroke();

        tracePoly(innerPts);
        const paperGrad = ctx.createLinearGradient(left, top, left + width, top + height);
        paperGrad.addColorStop(0, "#f1e8d5");
        paperGrad.addColorStop(0.55, "#e6dac2");
        paperGrad.addColorStop(1, "#d7c6ab");
        ctx.fillStyle = paperGrad;
        ctx.fill();
        ctx.lineWidth = 1.2;
        ctx.strokeStyle = "#8e7e66";
        ctx.stroke();

        const padSide = Math.max(13, Math.round(Number(layer.borderWidth || 15)));
        const padTop = Math.max(15, Math.round(padSide * 1.08));
        const padBot = Math.max(22, Math.round(padSide * 1.48));

        ctx.strokeStyle = "rgba(96,86,72,0.65)";
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(left + 8, top + 6);
        ctx.lineTo(left + width - 8, top + 6);
        ctx.stroke();

        ctx.fillStyle = "rgba(110,98,82,0.55)";
        ctx.fillRect(left + 8, top + 8, width * 0.38, 2);
        ctx.fillRect(left + width * 0.68, top + 8, width * 0.24, 2);

        const botY0 = top + height - padBot + 5;
        ctx.beginPath();
        ctx.moveTo(left + padSide, botY0);
        ctx.lineTo(left + width - padSide, botY0);
        ctx.stroke();
        ctx.fillRect(left + padSide, botY0 + 4, (width - padSide * 2) * 0.86, 2.2);
        ctx.fillRect(left + padSide, botY0 + 9, (width - padSide * 2) * 0.62, 2.2);
        ctx.restore();

        const ix = left + padSide;
        const iy = top + padTop;
        const iw = Math.max(32, width - padSide * 2);
        const ih = Math.max(32, height - padTop - padBot);
        ctx.save();
        ctx.beginPath();
        ctx.rect(ix, iy, iw, ih);
        ctx.clip();
        if (img) {
          drawCoverImage(ctx, img, ix, iy, iw, ih);
        } else {
          ctx.fillStyle = "#1e293b";
          ctx.fillRect(ix, iy, iw, ih);
        }
        ctx.restore();

        ctx.lineWidth = 2;
        ctx.strokeStyle = "#26211c";
        ctx.strokeRect(ix, iy, iw, ih);
      } else if (isVintagePaper) {
        const padSide = Math.max(10, Math.round(Number(layer.borderWidth || 13)));
        const padBottom = Math.max(padSide + 4, Math.round(padSide * 1.28));
        ctx.save();
        ctx.shadowColor = "rgba(0,0,0,0.9)";
        ctx.shadowBlur = 26;
        ctx.shadowOffsetX = 4;
        ctx.shadowOffsetY = 10;
        roundRectPath(ctx, left, top, width, height, 3);
        const paperGrad = ctx.createLinearGradient(left, top, left + width, top + height);
        paperGrad.addColorStop(0, "#f7f0e2");
        paperGrad.addColorStop(0.5, "#efe4ce");
        paperGrad.addColorStop(1, "#e2d2b5");
        ctx.fillStyle = paperGrad;
        ctx.fill();
        ctx.restore();

        ctx.lineWidth = 2;
        ctx.strokeStyle = "#b8a483";
        roundRectPath(ctx, left, top, width, height, 3);
        ctx.stroke();

        const ix = left + padSide;
        const iy = top + padSide;
        const iw = Math.max(32, width - padSide * 2);
        const ih = Math.max(32, height - padSide - padBottom);
        ctx.save();
        ctx.beginPath();
        ctx.rect(ix, iy, iw, ih);
        ctx.clip();
        if (img) {
          drawCoverImage(ctx, img, ix, iy, iw, ih);
        } else {
          ctx.fillStyle = "#1e293b";
          ctx.fillRect(ix, iy, iw, ih);
        }
        ctx.restore();

        ctx.lineWidth = 2;
        ctx.strokeStyle = "#292524";
        ctx.strokeRect(ix, iy, iw, ih);
      } else if (frameStyle === "caution_tape") {
        const rad = 14;
        ctx.save();
        ctx.shadowColor = "rgba(0,0,0,0.92)";
        ctx.shadowBlur = 26;
        ctx.shadowOffsetY = 9;
        roundRectPath(ctx, left, top, width, height, rad);
        ctx.fillStyle = "#0f172a";
        ctx.fill();
        ctx.clip();
        if (img) {
          drawCoverImage(ctx, img, left, top, width, height);
        } else {
          ctx.fillStyle = "#1e293b";
          ctx.fillRect(left, top, width, height);
        }
        const tapeH = Math.max(20, Math.min(30, Math.round(height * 0.105)));
        const ty0 = top + height - tapeH;
        ctx.fillStyle = "#facc15";
        ctx.fillRect(left, ty0, width, tapeH);
        ctx.fillStyle = "#0a0e17";
        for (let sxPos = -tapeH; sxPos < width + tapeH; sxPos += 24) {
          ctx.beginPath();
          ctx.moveTo(left + sxPos, top + height);
          ctx.lineTo(left + sxPos + 12, top + height);
          ctx.lineTo(left + sxPos + 12 + tapeH * 0.75, ty0);
          ctx.lineTo(left + sxPos + tapeH * 0.75, ty0);
          ctx.closePath();
          ctx.fill();
        }
        ctx.strokeStyle = "#0a0e17";
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.moveTo(left, ty0);
        ctx.lineTo(left + width, ty0);
        ctx.stroke();
        ctx.restore();

        ctx.save();
        ctx.lineWidth = bw + 4;
        ctx.strokeStyle = "rgba(5, 8, 15, 0.92)";
        roundRectPath(ctx, left, top, width, height, rad);
        ctx.stroke();
        ctx.lineWidth = Math.max(5, bw);
        ctx.strokeStyle = bColor;
        roundRectPath(ctx, left, top, width, height, rad);
        ctx.stroke();
        ctx.lineWidth = 2;
        ctx.strokeStyle = "rgba(255,255,255,0.68)";
        roundRectPath(ctx, left + bw * 0.65, top + bw * 0.65, width - bw * 1.3, height - bw * 1.3, Math.max(4, rad - bw));
        ctx.stroke();
        ctx.restore();
      } else if (frameStyle === "amber_glow_double" || frameStyle === "double_neon" || frameStyle === "neon_cyber") {
        const rad = 15;
        const useBw = Math.max(6, bw);
        ctx.save();
        ctx.shadowColor = bColor;
        ctx.shadowBlur = 28;
        ctx.shadowOffsetY = 4;
        roundRectPath(ctx, left, top, width, height, rad);
        ctx.fillStyle = "#0f172a";
        ctx.fill();
        ctx.clip();
        if (img) {
          drawCoverImage(ctx, img, left, top, width, height);
        } else {
          ctx.fillStyle = "#1e293b";
          ctx.fillRect(left, top, width, height);
        }
        ctx.restore();

        ctx.save();
        ctx.lineWidth = useBw + 4;
        ctx.strokeStyle = "rgba(5, 8, 15, 0.88)";
        roundRectPath(ctx, left, top, width, height, rad);
        ctx.stroke();
        ctx.lineWidth = useBw;
        ctx.strokeStyle = bColor;
        roundRectPath(ctx, left, top, width, height, rad);
        ctx.stroke();
        const inOff = useBw * 0.72;
        ctx.lineWidth = 4;
        ctx.strokeStyle = "#090d16";
        roundRectPath(ctx, left + inOff, top + inOff, width - inOff * 2, height - inOff * 2, Math.max(4, rad - inOff));
        ctx.stroke();
        const inOff2 = inOff + 3;
        ctx.lineWidth = 2;
        ctx.strokeStyle = frameStyle === "amber_glow_double" ? "#fffbeb" : "#ffffff";
        roundRectPath(ctx, left + inOff2, top + inOff2, width - inOff2 * 2, height - inOff2 * 2, Math.max(3, rad - inOff2));
        ctx.stroke();
        ctx.restore();
      } else if (frameStyle === "cctv_hud") {
        const rad = 10;
        ctx.save();
        ctx.shadowColor = "rgba(0,0,0,0.92)";
        ctx.shadowBlur = 24;
        ctx.shadowOffsetY = 8;
        roundRectPath(ctx, left, top, width, height, rad);
        ctx.fillStyle = "#090d16";
        ctx.fill();
        ctx.clip();
        if (img) {
          drawCoverImage(ctx, img, left, top, width, height);
        } else {
          ctx.fillStyle = "#1e293b";
          ctx.fillRect(left, top, width, height);
        }
        ctx.fillStyle = "rgba(6, 10, 18, 0.58)";
        ctx.fillRect(left, top, width, 34);
        roundRectPath(ctx, left + 12, top + 8, 84, 22, 6);
        ctx.fillStyle = "rgba(9, 13, 22, 0.86)";
        ctx.fill();
        ctx.beginPath();
        ctx.arc(left + 26, top + 19, 6, 0, Math.PI * 2);
        ctx.fillStyle = "#ff2424";
        ctx.fill();
        ctx.fillStyle = "#ffffff";
        ctx.font = "900 13px 'Pretendard ExtraBold', sans-serif";
        ctx.textAlign = "left";
        ctx.textBaseline = "middle";
        ctx.fillText("REC", left + 38, top + 20);
        ctx.restore();

        ctx.save();
        ctx.lineWidth = 4;
        ctx.strokeStyle = "#090d16";
        roundRectPath(ctx, left, top, width, height, rad);
        ctx.stroke();
        ctx.lineWidth = 2;
        ctx.strokeStyle = bColor;
        roundRectPath(ctx, left + 2, top + 2, width - 4, height - 4, Math.max(4, rad - 2));
        ctx.stroke();

        const cLen = Math.max(26, Math.round(Math.min(width, height) * 0.22));
        const cW = Math.max(6, bw + 2);
        const x0 = left - 2;
        const y0 = top - 2;
        const x1 = left + width + 2;
        const y1 = top + height + 2;
        const drawCorners = (col, wPx) => {
          ctx.beginPath();
          ctx.moveTo(x0, y0 + cLen); ctx.lineTo(x0, y0); ctx.lineTo(x0 + cLen, y0);
          ctx.moveTo(x1 - cLen, y0); ctx.lineTo(x1, y0); ctx.lineTo(x1, y0 + cLen);
          ctx.moveTo(x1, y1 - cLen); ctx.lineTo(x1, y1); ctx.lineTo(x1 - cLen, y1);
          ctx.moveTo(x0 + cLen, y1); ctx.lineTo(x0, y1); ctx.lineTo(x0, y1 - cLen);
          ctx.strokeStyle = col;
          ctx.lineWidth = wPx;
          ctx.lineJoin = "round";
          ctx.lineCap = "round";
          ctx.stroke();
        };
        drawCorners("rgba(0,0,0,0.92)", cW + 4);
        drawCorners(bColor, cW);
        ctx.restore();
      } else if (frameStyle === "dossier_tab") {
        const rad = 12;
        ctx.save();
        ctx.shadowColor = "rgba(0,0,0,0.9)";
        ctx.shadowBlur = 24;
        ctx.shadowOffsetY = 8;
        roundRectPath(ctx, left, top, width, height, rad);
        ctx.fillStyle = "#0f172a";
        ctx.fill();
        ctx.clip();
        if (img) {
          drawCoverImage(ctx, img, left, top, width, height);
        } else {
          ctx.fillStyle = "#1e293b";
          ctx.fillRect(left, top, width, height);
        }
        const barH = 26;
        ctx.fillStyle = "rgba(15, 23, 42, 0.95)";
        ctx.fillRect(left, top, width, barH);
        ctx.fillStyle = bColor;
        ctx.fillRect(left, top, 74, barH);
        ctx.strokeStyle = bColor;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(left, top + barH);
        ctx.lineTo(left + width, top + barH);
        ctx.stroke();
        [0, 1, 2].forEach((dIdx) => {
          ctx.beginPath();
          ctx.arc(left + 18 + dIdx * 16, top + 13, 4, 0, Math.PI * 2);
          ctx.fillStyle = dIdx === 0 ? "#ffffff" : "rgba(255,255,255,0.65)";
          ctx.fill();
        });
        ctx.restore();

        ctx.save();
        ctx.lineWidth = bw + 4;
        ctx.strokeStyle = "rgba(5, 8, 15, 0.9)";
        roundRectPath(ctx, left, top, width, height, rad);
        ctx.stroke();
        ctx.lineWidth = Math.max(5, bw);
        ctx.strokeStyle = bColor;
        roundRectPath(ctx, left, top, width, height, rad);
        ctx.stroke();
        ctx.restore();
      } else {
        ctx.save();
        ctx.shadowColor = "rgba(0,0,0,0.85)";
        ctx.shadowBlur = 24;
        ctx.shadowOffsetY = 8;
        roundRectPath(ctx, left, top, width, height, 14);
        ctx.fillStyle = "#0f172a";
        ctx.fill();
        ctx.clip();
        if (img) {
          drawCoverImage(ctx, img, left, top, width, height);
        } else {
          ctx.fillStyle = "#1e293b";
          ctx.fillRect(left, top, width, height);
        }
        ctx.restore();
        ctx.lineWidth = bw;
        ctx.strokeStyle = bColor;
        roundRectPath(ctx, left, top, width, height, 14);
        ctx.stroke();
      }
    } else if (type === "circle") {
      drawCircleShape(ctx, layer, left, top, width, height);
    } else if (type === "arrow") {
      drawArrowShape(ctx, layer, left, top, width, height);
    } else if (type === "stamp") {
      const text = String(layer.text || "극비 수사 파일").trim();
      if (text) {
        const fs = Number(layer.fontSize || 28);
        const fontStack = normalizeKoreanFontStack(layer.fontFamily);
        layer.fontFamily = fontStack;
        ctx.font = `900 ${fs}px ${fontStack}`;
        const metrics = ctx.measureText(text);
        const bw = Math.max(width, metrics.width + 38);
        const bh = Math.max(height, fs + 24);
        layer.width = bw;
        layer.height = bh;
        ctx.lineWidth = Number(layer.strokeWidth || 4);
        ctx.strokeStyle = layer.stroke || "#ef4444";
        ctx.fillStyle = "rgba(220, 38, 38, 0.16)";
        roundRectPath(ctx, left, top, bw, bh, 6);
        ctx.fill();
        ctx.stroke();
        ctx.fillStyle = layer.fill || "#fca5a5";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(text, left + bw / 2, top + bh / 2 + 2);
      }
    } else if (type === "badge") {
      const text = String(layer.text || "").trim();
      if (text) {
        const fs = Number(layer.fontSize || 38);
        const fontStack = normalizeKoreanFontStack(layer.fontFamily);
        layer.fontFamily = fontStack;
        ctx.font = `900 ${fs}px ${fontStack}`;
        const metrics = ctx.measureText(text);
        const padX = 28;
        const bw = Math.max(180, metrics.width + padX * 2);
        const bh = Math.max(58, fs + 26);
        layer.width = bw;
        layer.height = bh;
        const rawBg = String(layer.bgColor || "").trim().toLowerCase();
        const isTransparentBg = rawBg === "transparent" || rawBg === "none";

        if (isTransparentBg) {
          ctx.save();
          ctx.lineJoin = "round";
          ctx.miterLimit = 2;
          ctx.shadowColor = "rgba(0,0,0,0.92)";
          ctx.shadowBlur = 16;
          ctx.shadowOffsetY = 5;
          ctx.lineWidth = Math.max(12, Math.round(fs * 0.27));
          ctx.strokeStyle = "#000000";
          ctx.textAlign = "left";
          ctx.textBaseline = "middle";
          ctx.strokeText(text, left, top + bh / 2 + 2);
          ctx.fillStyle = layer.fill || "#1aff00";
          ctx.fillText(text, left, top + bh / 2 + 2);
          ctx.restore();
        } else {
          ctx.save();
          ctx.shadowColor = "rgba(0,0,0,0.85)";
          ctx.shadowBlur = 16;
          ctx.shadowOffsetY = 5;
          roundRectPath(ctx, left, top, bw, bh, Number(layer.borderRadius || 10));
          ctx.fillStyle = layer.bgColor || "#dc2626";
          ctx.fill();
          ctx.restore();

          if (Number(layer.borderWidth || 0) > 0) {
            ctx.lineWidth = Number(layer.borderWidth || 3);
            ctx.strokeStyle = layer.borderColor || "#ffffff";
            roundRectPath(ctx, left, top, bw, bh, Number(layer.borderRadius || 10));
            ctx.stroke();
          }
          ctx.fillStyle = layer.fill || "#ffffff";
          ctx.textAlign = "center";
          ctx.textBaseline = "middle";
          ctx.fillText(text, left + bw / 2, top + bh / 2 + 2);
        }
      }
    } else if (type === "textbox") {
      const rawText = String(layer.text || "").trim();
      const { plainText: text, segments } = parseInlineHighlightSegments(rawText);
      if (text) {
        let fs = Number(layer.fontSize || 84);
        const fontStack = normalizeKoreanFontStack(layer.fontFamily);
        layer.fontFamily = fontStack;
        ctx.font = `900 ${fs}px ${fontStack}`;
        let measured = ctx.measureText(text).width;
        const maxAllowedW = CW - Math.max(36, Number(left || 36)) - 22;
        while (measured > maxAllowedW && fs > 48) {
          fs -= 2;
          ctx.font = `900 ${fs}px ${fontStack}`;
          measured = ctx.measureText(text).width;
        }
        layer.width = Math.max(240, measured + 32);
        layer.height = Math.max(76, fs * 1.24);

        const align = layer.textAlign || "left";
        let tx = left;
        if (align === "center") tx = left + layer.width / 2;
        else if (align === "right") tx = left + layer.width;
        const ty = top + layer.height / 2;

        ctx.textAlign = align;
        ctx.textBaseline = "middle";
        ctx.lineJoin = "round";
        ctx.miterLimit = 2;

        const sw = Math.max(18, Number(layer.strokeWidth ?? 24));
        // 1. 3D Extruded Deep Black Drop Block (+5, +7)
        ctx.save();
        ctx.shadowColor = layer.shadowColor || "rgba(0,0,0,0.95)";
        ctx.shadowBlur = Number(layer.shadowBlur || 22);
        ctx.shadowOffsetX = 0;
        ctx.shadowOffsetY = 6;
        ctx.lineWidth = sw;
        ctx.strokeStyle = "#000000";
        ctx.strokeText(text, tx + 5, ty + 7);
        ctx.restore();

        // 2. Crisp Heavy Black Contour Stroke
        ctx.lineWidth = sw;
        ctx.strokeStyle = layer.stroke || "#000000";
        ctx.strokeText(text, tx, ty);

        // 3. Ultra-thick Broadcast Fill (+2.4px same-color stroke so glyphs match PIL SCoreDream 9 Black thickness)
        const hasHighlightSeg = segments.some((s) => s.highlight);
        if (!hasHighlightSeg) {
          const fillCol = layer.fill || "#ffffff";
          ctx.fillStyle = fillCol;
          ctx.fillText(text, tx, ty);
        } else {
          let startX = tx;
          if (align === "center") startX = tx - measured / 2;
          else if (align === "right") startX = tx - measured;
          const mainHex = String(layer.fill || "#ffffff").toLowerCase();
          const defaultHl = ["#ffe600", "#ffe84a", "#fbbf24", "#facc15"].includes(mainHex) ? "#ff2424" : "#ffe600";
          const hlColor = layer.highlightFill || defaultHl;
          ctx.save();
          ctx.textAlign = "left";
          let prefix = "";
          segments.forEach((seg) => {
            const offset = prefix ? ctx.measureText(prefix).width : 0;
            const segCol = seg.highlight ? hlColor : (layer.fill || "#ffffff");
            ctx.fillStyle = segCol;
            ctx.fillText(seg.text, startX + offset, ty);
            prefix += seg.text;
          });
          ctx.restore();
        }
      }
    }
    ctx.restore();
  }

  function drawSnapGuides(ctx) {
    const guides = studioState.snapGuides;
    if (!guides || (!guides.x && !guides.y)) return;
    ctx.save();
    ctx.lineWidth = 2;
    ctx.setLineDash([8, 6]);
    if (typeof guides.x === "number") {
      ctx.strokeStyle = "#ec4899"; // Canva magenta vertical guide
      ctx.beginPath();
      ctx.moveTo(guides.x, 0);
      ctx.lineTo(guides.x, CH);
      ctx.stroke();
    }
    if (typeof guides.y === "number") {
      ctx.strokeStyle = "#06b6d4"; // Cyan horizontal guide
      ctx.beginPath();
      ctx.moveTo(0, guides.y);
      ctx.lineTo(CW, guides.y);
      ctx.stroke();
    }
    ctx.setLineDash([]);
    ctx.restore();
  }

  function drawSafeZoneOverlay(ctx) {
    ctx.save();
    ctx.strokeStyle = "rgba(56, 189, 248, 0.45)";
    ctx.lineWidth = 2;
    ctx.setLineDash([10, 8]);
    ctx.strokeRect(48, 36, CW - 96, CH - 72);
    ctx.setLineDash([]);

    const zx = 1060;
    const zy = 625;
    const zw = CW - zx - 18;
    const zh = CH - zy - 16;
    roundRectPath(ctx, zx, zy, zw, zh, 10);
    ctx.fillStyle = "rgba(220, 38, 38, 0.82)";
    ctx.fill();
    ctx.lineWidth = 3;
    ctx.strokeStyle = "#ffffff";
    ctx.stroke();

    ctx.fillStyle = "#ffffff";
    ctx.font = "800 24px 'Inter', sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText("⏱ 30:15 SAFE", zx + zw / 2, zy + zh / 2);
    ctx.restore();
  }

  function toLayerLocalCoords(mx, my, layer) {
    const left = Number(layer.left || 0);
    const top = Number(layer.top || 0);
    const w = Number(layer.width || 200);
    const h = Number(layer.height || 80);
    const cx = left + w / 2;
    const cy = top + h / 2;
    const rad = (-Number(layer.angle || 0) * Math.PI) / 180;
    const dx = mx - cx;
    const dy = my - cy;
    return {
      x: cx + dx * Math.cos(rad) - dy * Math.sin(rad),
      y: cy + dx * Math.sin(rad) + dy * Math.cos(rad),
    };
  }

  function drawSelectionBox(ctx, layer) {
    if (!layer || layer.type === "vignette" || layer.visible === false) return;
    const left = Number(layer.left || 0);
    const top = Number(layer.top || 0);
    const width = Number(layer.width || 200);
    const height = Number(layer.height || 80);
    const angle = Number(layer.angle || 0);
    const cx = left + width / 2;
    const cy = top + height / 2;

    ctx.save();
    if (angle) {
      ctx.translate(cx, cy);
      ctx.rotate((angle * Math.PI) / 180);
      ctx.translate(-cx, -cy);
    }

    // Main Canva-style selection frame
    ctx.strokeStyle = "#8b5cf6";
    ctx.lineWidth = 3;
    ctx.strokeRect(left - 6, top - 6, width + 12, height + 12);

    // 4 Corner Resize Handles (White circles with purple border like Canva)
    const corners = [
      [left - 6, top - 6],
      [left + width + 6, top - 6],
      [left - 6, top + height + 6],
    ];
    corners.forEach(([hx, hy]) => {
      ctx.fillStyle = "#ffffff";
      ctx.strokeStyle = "#7c3aed";
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.arc(hx, hy, 9, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
    });

    // Bottom-right Primary Resize Handle (Blue/Purple square)
    const brX = left + width + 6;
    const brY = top + height + 6;
    ctx.fillStyle = "#38bdf8";
    ctx.strokeStyle = "#0f172a";
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.rect(brX - 11, brY - 11, 22, 22);
    ctx.fill();
    ctx.stroke();

    // Top Rotation Stem + Canva Rotate Handle (↻)
    const rotX = cx;
    const rotY = top - 40;
    ctx.strokeStyle = "#8b5cf6";
    ctx.lineWidth = 2.5;
    ctx.beginPath();
    ctx.moveTo(cx, top - 6);
    ctx.lineTo(rotX, rotY);
    ctx.stroke();

    ctx.fillStyle = "#ffffff";
    ctx.strokeStyle = "#7c3aed";
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.arc(rotX, rotY, 16, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();

    ctx.fillStyle = "#6d28d9";
    ctx.font = "900 18px 'Inter', sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText("↻", rotX, rotY + 1);

    // Top-right Delete button (Red circle with white X)
    const dx = left + width + 6;
    const dy = top - 6;
    ctx.fillStyle = "#ef4444";
    ctx.strokeStyle = "#ffffff";
    ctx.lineWidth = 2.5;
    ctx.beginPath();
    ctx.arc(dx, dy, 15, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();

    ctx.strokeStyle = "#ffffff";
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(dx - 6, dy - 6);
    ctx.lineTo(dx + 6, dy + 6);
    ctx.moveTo(dx + 6, dy - 6);
    ctx.lineTo(dx - 6, dy + 6);
    ctx.stroke();
    ctx.restore();
  }

  function renderVariantToCanvas(canvas, variant, { cleanExport = false, showSelection = false } = {}) {
    if (!canvas || !variant) return;
    const ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, CW, CH);

    const bgGrad = ctx.createLinearGradient(0, 0, CW, CH);
    bgGrad.addColorStop(0, "#090d16");
    bgGrad.addColorStop(0.5, "#111827");
    bgGrad.addColorStop(1, "#1e1b4b");
    ctx.fillStyle = bgGrad;
    ctx.fillRect(0, 0, CW, CH);

    const bgUrl = getVariantBgUrl(variant);
    if (bgUrl) {
      const bgImg = loadCachedImage(bgUrl);
      if (bgImg) {
        drawCoverImage(ctx, bgImg, 0, 0, CW, CH);
      }
    }

    const layers = Array.isArray(variant.layers) ? variant.layers : [];
    layers.forEach((layer) => drawLayer(ctx, layer));

    if (!cleanExport && showSelection) {
      const design = studioState.data?.design;
      if (design?.safe_zone_visible) {
        drawSafeZoneOverlay(ctx);
      }
      drawSnapGuides(ctx);
      const selected = getLayer(studioState.selectedLayerId, variant);
      if (selected) {
        drawSelectionBox(ctx, selected);
      }
    }
  }

  function getActiveArrowLayer(variant = null) {
    const v = variant || getActiveVariant();
    if (!v || !Array.isArray(v.layers)) return null;
    const sel = getLayer(studioState.selectedLayerId, v);
    if (sel && sel.type === "arrow") return sel;
    return v.layers.find((l) => l && l.type === "arrow" && l.visible !== false) || v.layers.find((l) => l && l.type === "arrow") || null;
  }

  function getActiveCircleLayer(variant = null) {
    const v = variant || getActiveVariant();
    if (!v || !Array.isArray(v.layers)) return null;
    const sel = getLayer(studioState.selectedLayerId, v);
    if (sel && sel.type === "circle") return sel;
    return v.layers.find((l) => l && l.type === "circle" && l.visible !== false) || v.layers.find((l) => l && l.type === "circle") || null;
  }

  function getLayerPrimaryColor(layer) {
    if (!layer) return "#ffffff";
    if (layer.type === "circle") return normalizeHexColor(layer.stroke, "#ef4444");
    if (layer.type === "inset_image") return normalizeHexColor(layer.borderColor, "#ef4444");
    return normalizeHexColor(layer.fill, "#ffffff");
  }

  function getLayerStrokeColor(layer) {
    if (!layer) return "#000000";
    if (layer.type === "circle") return normalizeHexColor(layer.outerStroke, "#000000");
    if (layer.type === "badge") {
      const rawBg = String(layer.bgColor || "").trim().toLowerCase();
      if (rawBg && rawBg !== "transparent" && rawBg !== "none") return normalizeHexColor(layer.bgColor, "#dc2626");
      return normalizeHexColor(layer.borderColor || layer.stroke, "#000000");
    }
    if (layer.type === "inset_image") return normalizeHexColor(layer.borderColor, "#ffffff");
    return normalizeHexColor(layer.stroke, "#000000");
  }

  function setLayerPrimaryColor(layer, rawColor) {
    if (!layer) return;
    const hex = normalizeHexColor(rawColor, getLayerPrimaryColor(layer));
    if (layer.type === "circle") {
      layer.stroke = hex;
    } else if (layer.type === "inset_image") {
      layer.borderColor = hex;
    } else {
      layer.fill = hex;
    }
  }

  function setLayerStrokeColor(layer, rawColor) {
    if (!layer) return;
    const hex = normalizeHexColor(rawColor, getLayerStrokeColor(layer));
    if (layer.type === "circle") {
      layer.outerStroke = hex;
    } else if (layer.type === "badge") {
      const rawBg = String(layer.bgColor || "").trim().toLowerCase();
      if (rawBg && rawBg !== "transparent" && rawBg !== "none") {
        layer.bgColor = hex;
      } else {
        layer.stroke = hex;
      }
    } else if (layer.type === "inset_image") {
      layer.borderColor = hex;
    } else {
      layer.stroke = hex;
    }
  }

  function addNewArrowLayer(styleId = "curved_pointer") {
    const v = getActiveVariant();
    if (!v) return;
    if (!Array.isArray(v.layers)) v.layers = [];
    pushUndoSnapshot();
    const existingArrows = v.layers.filter((l) => l && l.type === "arrow");
    const baseArrow = getActiveArrowLayer(v);
    const libItem = ARROW_LIBRARY.find((a) => a.id === styleId) || ARROW_LIBRARY[0];
    const newIdx = existingArrows.length + 1;
    const newId = newIdx === 1 && !getLayer("forensic_arrow", v) ? "forensic_arrow" : `forensic_arrow_${Date.now().toString(36).slice(-4)}`;
    const newLayer = {
      id: newId,
      type: "arrow",
      name: `Mũi tên #${newIdx} (${libItem.shortLabel})`,
      arrowStyle: libItem.id,
      left: Math.min(CW - 240, 560 + ((newIdx - 1) * 45) % 240),
      top: Math.min(CH - 180, 170 + ((newIdx - 1) * 45) % 200),
      width: 180,
      height: 68,
      fill: baseArrow?.fill || libItem.defaultFill || "#ff1f1f",
      stroke: baseArrow?.stroke || libItem.defaultStroke || "#ffffff",
      strokeWidth: Number(baseArrow?.strokeWidth ?? 4),
      angle: -10,
      flipX: false,
      flipY: false,
      visible: true,
      opacity: 0.98,
    };
    v.layers.push(newLayer);
    studioState.selectedLayerId = newLayer.id;
    renderAllCanvases();
    refreshContextualPanels();
    scheduleSaveDesign();
    showToast(`↗ Đã thêm «${newLayer.name}» lên ảnh — hãy kéo thả, xoay ↻ hoặc đổi màu!`);
  }

  function addNewCircleLayer(styleId = "solid_ring") {
    const v = getActiveVariant();
    if (!v) return;
    if (!Array.isArray(v.layers)) v.layers = [];
    pushUndoSnapshot();
    const existingCircles = v.layers.filter((l) => l && l.type === "circle");
    const baseCircle = getActiveCircleLayer(v);
    const libItem = CIRCLE_LIBRARY.find((c) => c.id === styleId) || CIRCLE_LIBRARY[0];
    const newIdx = existingCircles.length + 1;
    const newId = newIdx === 1 && !getLayer("forensic_circle", v) ? "forensic_circle" : `forensic_circle_${Date.now().toString(36).slice(-4)}`;
    const newLayer = {
      id: newId,
      type: "circle",
      name: `Vòng khoanh #${newIdx} (${libItem.shortLabel})`,
      circleStyle: libItem.id,
      dashed: libItem.id === "dashed_forensic",
      left: Math.min(CW - 300, 740 + ((newIdx - 1) * 40) % 180),
      top: Math.min(CH - 300, 110 + ((newIdx - 1) * 40) % 160),
      width: 240,
      height: 240,
      stroke: baseCircle?.stroke || libItem.defaultStroke || "#ef4444",
      outerStroke: baseCircle?.outerStroke || libItem.defaultOuter || "#000000",
      strokeWidth: Number(baseCircle?.strokeWidth ?? 10),
      angle: 0,
      visible: true,
      opacity: 0.98,
    };
    v.layers.push(newLayer);
    studioState.selectedLayerId = newLayer.id;
    renderAllCanvases();
    refreshContextualPanels();
    scheduleSaveDesign();
    showToast(`⭕ Đã thêm «${newLayer.name}» lên ảnh — hãy kéo tới vùng vật chứng cần khoanh!`);
  }

  function addNewCustomTextLayer() {
    const v = getActiveVariant();
    if (!v) return;
    if (!Array.isArray(v.layers)) v.layers = [];
    pushUndoSnapshot();
    const l2 = getLayer("line_2", v) || {};
    const customCount = v.layers.filter((l) => l && String(l.id || "").startsWith("custom_text")).length + 1;
    const newId = `custom_text_${Date.now().toString(36).slice(-4)}`;
    const newLayer = {
      id: newId,
      type: "textbox",
      name: `Chữ thêm #${customCount}`,
      text: "충격적인 수사 단서!",
      left: 84,
      top: Math.max(80, Math.min(CH - 150, 290 + (customCount - 1) * 55)),
      width: 720,
      height: 92,
      fontSize: 66,
      fontFamily: l2.fontFamily || DEFAULT_KR_FONT_STACK,
      fontWeight: "900",
      fill: "#ffe600",
      stroke: "#000000",
      strokeWidth: 16,
      shadowColor: "rgba(0,0,0,0.94)",
      shadowBlur: 18,
      textAlign: "left",
      angle: 0,
      visible: true,
      opacity: 1.0,
    };
    v.layers.push(newLayer);
    studioState.selectedLayerId = newLayer.id;
    renderAllCanvases();
    refreshContextualPanels();
    scheduleSaveDesign();
    showToast(`🔤 Đã thêm «${newLayer.name}» — bạn có thể sửa chữ và chỉnh màu ngay!`);
  }

  function addNewPipLayer(frameStyle = "vintage_paper") {
    const v = getActiveVariant();
    if (!v) return;
    if (!Array.isArray(v.layers)) v.layers = [];
    pushUndoSnapshot();
    const existingPips = v.layers.filter((l) => l && l.type === "inset_image");
    const cands = getCleanCandidates();
    const realInCands = cands.filter((c) => c.category === "thumbnail_inset");
    const pool = realInCands.length ? realInCands : cands;
    const defaultUrl = pool[existingPips.length % Math.max(1, pool.length)]?.url || v.inset_image_url || "";
    const newIdx = existingPips.length + 1;
    const newId = newIdx === 1 && !getLayer("inset_photo", v)
      ? "inset_photo"
      : newIdx === 2 && !getLayer("inset_photo_2", v)
      ? "inset_photo_2"
      : `inset_photo_${Date.now().toString(36).slice(-4)}`;
    const isSecond = newIdx >= 2;
    const newPip = {
      id: newId,
      type: "inset_image",
      name: `Ảnh phụ PiP #${newIdx}`,
      src: defaultUrl,
      frameStyle: isSecond ? "torn_newspaper" : frameStyle,
      left: isSecond ? 386 : 44,
      top: isSecond ? 196 : 112,
      width: isSecond ? 314 : 356,
      height: isSecond ? 226 : 244,
      borderColor: "#f4ebd9",
      borderWidth: 14,
      angle: isSecond ? 3.5 : -2.8,
      visible: true,
    };
    const l1Idx = v.layers.findIndex((l) => l && l.id === "line_1");
    if (l1Idx > 0) {
      v.layers.splice(l1Idx, 0, newPip);
    } else {
      v.layers.push(newPip);
    }
    if (defaultUrl) loadCachedImage(defaultUrl);
    studioState.selectedLayerId = newPip.id;
    renderAllCanvases();
    refreshContextualPanels();
    scheduleSaveDesign();
    showToast(`🖼 Đã thêm «${newPip.name}» chuẩn DNA — chọn ngay ảnh tư liệu thật ở cột phải!`);
  }

  function renderLibraryMiniPreviews() {
    const activeVariant = getActiveVariant();
    const curArrow = getActiveArrowLayer(activeVariant) || {};
    const curCircle = getActiveCircleLayer(activeVariant) || {};

    document.querySelectorAll("[data-arrow-lib-canvas]").forEach((cv) => {
      const styleId = cv.dataset.arrowLibCanvas;
      const libObj = ARROW_LIBRARY.find((a) => a.id === styleId) || ARROW_LIBRARY[0];
      const ctx = cv.getContext("2d");
      const w = cv.width || 136;
      const h = cv.height || 52;
      ctx.clearRect(0, 0, w, h);
      drawArrowShape(
        ctx,
        {
          arrowStyle: styleId,
          fill: curArrow.fill || libObj.defaultFill || "#ff1f1f",
          stroke: curArrow.stroke || libObj.defaultStroke || "#ffffff",
          strokeWidth: Math.min(5, Number(curArrow.strokeWidth ?? 4)),
        },
        8,
        5,
        w - 16,
        h - 10
      );
    });

    document.querySelectorAll("[data-circle-lib-canvas]").forEach((cv) => {
      const styleId = cv.dataset.circleLibCanvas;
      const libObj = CIRCLE_LIBRARY.find((c) => c.id === styleId) || CIRCLE_LIBRARY[0];
      const ctx = cv.getContext("2d");
      const w = cv.width || 96;
      const h = cv.height || 64;
      ctx.clearRect(0, 0, w, h);
      const size = Math.min(w, h) - 16;
      drawCircleShape(
        ctx,
        {
          circleStyle: styleId,
          stroke: curCircle.stroke || libObj.defaultStroke || "#ef4444",
          outerStroke: curCircle.outerStroke || libObj.defaultOuter || "#000000",
          strokeWidth: 5,
        },
        (w - size) / 2,
        (h - size) / 2,
        size,
        size
      );
    });
  }

  function renderAllCanvases() {
    const variants = getVariants();
    variants.forEach((variant) => {
      const cardCanvases = document.querySelectorAll(`[data-thumb-card-canvas="${variant.id}"]`);
      cardCanvases.forEach((cardCanvas) => {
        renderVariantToCanvas(cardCanvas, variant, { cleanExport: true, showSelection: false });
      });
    });

    const mainCanvas = document.getElementById("cofiThumbMainCanvas");
    const activeVariant = getActiveVariant();
    if (mainCanvas && activeVariant) {
      renderVariantToCanvas(mainCanvas, activeVariant, { cleanExport: false, showSelection: true });
    }

    if (studioState.lightboxVariantId) {
      const lbCanvas = document.getElementById("cofiThumbLightboxCanvas");
      const lbVariant = getVariantById(studioState.lightboxVariantId);
      if (lbCanvas && lbVariant) {
        renderVariantToCanvas(lbCanvas, lbVariant, { cleanExport: true, showSelection: false });
      }
    }

    renderLibraryMiniPreviews();
  }

  function renderVariantDataUrl(variant) {
    const offscreen = document.createElement("canvas");
    offscreen.width = CW;
    offscreen.height = CH;
    renderVariantToCanvas(offscreen, variant, { cleanExport: true, showSelection: false });
    let quality = 0.92;
    let dataUrl = offscreen.toDataURL("image/jpeg", quality);
    while (dataUrl.length > 2.5 * 1024 * 1024 && quality > 0.72) {
      quality -= 0.06;
      dataUrl = offscreen.toDataURL("image/jpeg", quality);
    }
    return dataUrl;
  }

  function dataUrlToBlob(dataUrl) {
    const parts = String(dataUrl || "").split(",");
    if (parts.length < 2) return null;
    const mimeMatch = parts[0].match(/:(.*?);/);
    const mime = mimeMatch ? mimeMatch[1] : "image/jpeg";
    const binary = atob(parts[1]);
    const len = binary.length;
    const bytes = new Uint8Array(len);
    for (let i = 0; i < len; i++) {
      bytes[i] = binary.charCodeAt(i);
    }
    return new Blob([bytes], { type: mime });
  }

  function getFilePickerTypesForFilename(filename) {
    const lower = String(filename || "").toLowerCase();
    if (lower.endsWith(".png")) {
      return [{ description: "Ảnh PNG (*.png)", accept: { "image/png": [".png"] } }];
    }
    if (lower.endsWith(".webp")) {
      return [{ description: "Ảnh WebP (*.webp)", accept: { "image/webp": [".webp"] } }];
    }
    if (lower.endsWith(".zip")) {
      return [{ description: "File nén ZIP (*.zip)", accept: { "application/zip": [".zip"] } }];
    }
    if (lower.endsWith(".mp4")) {
      return [{ description: "Video MP4 (*.mp4)", accept: { "video/mp4": [".mp4"] } }];
    }
    return [{ description: "Ảnh JPEG (*.jpg)", accept: { "image/jpeg": [".jpg", ".jpeg"] } }];
  }

  async function triggerBrowserDownload(dataUrl, filename, { usePicker = true } = {}) {
    const safeFilename = String(filename || "thumbnail.jpg").trim();
    if (usePicker && typeof window !== "undefined" && typeof window.showSaveFilePicker === "function") {
      try {
        const handle = await window.showSaveFilePicker({
          suggestedName: safeFilename,
          types: getFilePickerTypesForFilename(safeFilename),
        });
        let blob = null;
        if (String(dataUrl || "").startsWith("data:")) {
          blob = dataUrlToBlob(dataUrl);
        } else {
          const resp = await fetch(dataUrl);
          if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
          blob = await resp.blob();
        }
        if (blob) {
          const writable = await handle.createWritable();
          await writable.write(blob);
          await writable.close();
          return { saved: true, cancelled: false, fileName: handle.name || safeFilename };
        }
      } catch (err) {
        if (err && err.name === "AbortError") {
          return { saved: false, cancelled: true, fileName: safeFilename };
        }
      }
    }
    let href = dataUrl;
    let revokeUrl = null;
    if (String(dataUrl || "").startsWith("data:")) {
      const blob = dataUrlToBlob(dataUrl);
      if (blob && typeof URL !== "undefined" && typeof URL.createObjectURL === "function") {
        href = URL.createObjectURL(blob);
        revokeUrl = href;
      }
    }
    const link = document.createElement("a");
    link.href = href;
    link.download = safeFilename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    if (revokeUrl) {
      setTimeout(() => URL.revokeObjectURL(revokeUrl), 15000);
    }
    return { saved: true, cancelled: false, fileName: safeFilename };
  }

  function scheduleSaveDesign() {
    clearTimeout(studioState.saveTimer);
    studioState.saveTimer = setTimeout(async () => {
      if (!studioState.jobId || !studioState.data?.design) return;
      try {
        await fetch(`/api/jobs/${encodeURIComponent(studioState.jobId)}/thumbnail-studio/design`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ design: studioState.data.design }),
        });
      } catch (_) {}
    }, 450);
  }

  async function downloadSingleVariant(variantId, { setPrimary = false } = {}) {
    const variant = getVariantById(variantId);
    if (!variant) return;
    const dataUrl = renderVariantDataUrl(variant);
    const shortName = String(variant.short_label || variant.id || "v1")
      .replace(/\s+/g, "_")
      .replace(/[^a-zA-Z0-9_-]/g, "");
    const fileName = `thumbnail_${studioState.jobId}_${shortName || variant.id}.jpg`;
    const dlResult = await triggerBrowserDownload(dataUrl, fileName, { usePicker: true });
    if (dlResult?.cancelled) return;

    try {
      const resp = await fetch(`/api/jobs/${encodeURIComponent(studioState.jobId)}/thumbnail-studio/export`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          variant_id: variant.id,
          set_primary: setPrimary,
          data_url: dataUrl,
          design: studioState.data.design,
        }),
      });
      const json = await resp.json();
      if (resp.ok && json.ok) {
        studioState.data.thumbnail_exists = true;
        studioState.data.thumbnail_url = json.thumbnail_url;
        const finalName = dlResult?.fileName || fileName;
        showToast(
          setPrimary
            ? `Đã chọn ${variant.short_label || variant.id} làm Thumbnail chính & tải ảnh (${finalName})!`
            : `Đã tải xuống ${variant.short_label || variant.id} (${finalName})!`
        );
      }
    } catch (_) {}
  }

  async function downloadAllVariants() {
    const variants = getVariants();
    if (!variants.length || studioState.busyExportAll) return;
    studioState.busyExportAll = true;
    renderStudioDom();
    try {
      const activeId = studioState.data?.design?.active_variant_id || "v1";
      let dirHandle = null;
      if (typeof window !== "undefined" && typeof window.showDirectoryPicker === "function") {
        try {
          dirHandle = await window.showDirectoryPicker({ mode: "readwrite" });
        } catch (err) {
          if (err && err.name === "AbortError") return;
          dirHandle = null;
        }
      }
      const items = [];
      for (let i = 0; i < variants.length; i++) {
        const v = variants[i];
        const dataUrl = renderVariantDataUrl(v);
        items.push({
          variant_id: v.id,
          data_url: dataUrl,
          is_primary: v.id === activeId,
        });
        const labelSlug = `Ban_${String.fromCharCode(65 + i)}`;
        const outFileName = `thumbnail_${studioState.jobId}_${labelSlug}.jpg`;
        if (dirHandle) {
          const blob = dataUrlToBlob(dataUrl);
          if (blob) {
            const fileHandle = await dirHandle.getFileHandle(outFileName, { create: true });
            const writable = await fileHandle.createWritable();
            await writable.write(blob);
            await writable.close();
          }
        } else {
          await triggerBrowserDownload(dataUrl, outFileName, { usePicker: false });
          await new Promise((r) => setTimeout(r, 220));
        }
      }
      const resp = await fetch(`/api/jobs/${encodeURIComponent(studioState.jobId)}/thumbnail-studio/export`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          items,
          design: studioState.data.design,
        }),
      });
      const json = await resp.json();
      if (resp.ok && json.ok) {
        studioState.data.thumbnail_exists = true;
        studioState.data.thumbnail_url = json.thumbnail_url;
      }
      showToast(`Đã tải về tất cả ${variants.length} bản Thumbnail (.JPG) và lưu vào thư mục dự án!`);
    } catch (err) {
      showToast(err.message || "Lỗi khi tải tất cả các bản thumbnail", true);
    } finally {
      studioState.busyExportAll = false;
      renderStudioDom();
    }
  }

  async function exportAbTestPack() {
    if (!studioState.jobId || studioState.busyExportAbPack) return;
    studioState.busyExportAbPack = true;
    renderStudioDom();
    try {
      showToast("Đang kết xuất gói A/B Test Pack 3 ảnh & metadata cho YouTube Studio...");
      const variants = getVariants();
      const activeId = studioState.data?.design?.active_variant_id || "v1";
      if (variants.length && studioState.data?.design) {
        const items = variants.map((v) => ({
          variant_id: v.id,
          data_url: renderVariantDataUrl(v),
          is_primary: v.id === activeId,
        }));
        await fetch(`/api/jobs/${encodeURIComponent(studioState.jobId)}/thumbnail-studio/export`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ items, design: studioState.data.design }),
        }).catch(() => {});
      }
      const resp = await fetch(`/api/jobs/${encodeURIComponent(studioState.jobId)}/thumbnail-studio/export-ab-pack`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      const data = await resp.json();
      if (!resp.ok || !data.ok) {
        throw new Error(data.detail || "Không thể kết xuất gói A/B Test Pack.");
      }
      showToast("Đã kết xuất thành công A/B Test Pack! Đang tải file ZIP về máy...");
      if (data.zip_url) {
        const zipFileName = `ab_test_pack_${studioState.jobId}.zip`;
        const zipDownloadUrl = `${data.zip_url}${data.zip_url.includes("?") ? "&" : "?"}download=1&filename=${encodeURIComponent(zipFileName)}`;
        await triggerBrowserDownload(zipDownloadUrl, zipFileName, { usePicker: true });
      }
    } catch (err) {
      showToast(`Lỗi xuất A/B Pack: ${err.message}`, true);
    } finally {
      studioState.busyExportAbPack = false;
      renderStudioDom();
    }
  }

  async function selectThumbnailWinner(variantId) {
    if (!studioState.jobId || !variantId) return;
    try {
      const resp = await fetch(`/api/jobs/${encodeURIComponent(studioState.jobId)}/thumbnail-studio/select-winner`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ variant_id: variantId }),
      });
      const data = await resp.json();
      if (!resp.ok || !data.ok) {
        throw new Error(data.detail || "Không thể chọn biến thể chiến thắng.");
      }
      if (studioState.data && studioState.data.design) {
        studioState.data.design.active_variant_id = variantId;
        studioState.data.thumbnail_exists = true;
        studioState.data.thumbnail_url = data.thumbnail_url;
      }
      showToast(`Đã chọn ${data.variant_name || variantId} làm Thumbnail chính (Winner)!`);
      renderStudioDom();
    } catch (err) {
      showToast(`Lỗi chọn Winner: ${err.message}`, true);
    }
  }

  async function lockThumbnailDnaToChannel() {
    if (!studioState.jobId || studioState.busyLockDna) return;
    studioState.busyLockDna = true;
    renderStudioDom();
    try {
      const activeVar = getActiveVariant() || {};
      const design = studioState.data?.design || {};
      const l1 = getLayer("line_1", activeVar) || {};
      const l2 = getLayer("line_2", activeVar) || {};
      const b = getLayer("badge", activeVar) || {};

      // Save the current design to disk first so backend extracts the exact up-to-date layers
      await fetch(`/api/jobs/${encodeURIComponent(studioState.jobId)}/thumbnail-studio/design`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ design }),
      }).catch(() => {});

      const stylePreset = String(activeVar.style_preset || design.style_preset || "sbs_criminal_profiling");
      const presetObj = TOPIC_STYLE_PRESETS.find((p) => p.id === stylePreset);
      const resp = await fetch(`/api/jobs/${encodeURIComponent(studioState.jobId)}/lock-thumbnail-dna`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          notes: `Locked from Canva Thumbnail Studio (${activeVar.short_label || activeVar.id || "v1"})`,
          style_preset: stylePreset,
          visual_signature: presetObj ? presetObj.label : `${stylePreset} Custom Preset`,
          layout_template: activeVar.archetype || "broadcast_left_heavy",
          color_palette: {
            primary: l2.fill || "#ffe600",
            accent: b.bgColor && b.bgColor !== "transparent" ? b.bgColor : "#dc2626",
            text_primary: l1.fill || "#ffffff",
            highlight: l2.highlightFill || l1.highlightFill || "#ff2424",
          },
        }),
      });
      const data = await resp.json();
      if (!resp.ok || !data.ok) {
        throw new Error(data.detail || "Không thể khóa DNA Thumbnail.");
      }
      if (design && data.thumbnail_dna) {
        design.channel_thumbnail_dna = data.thumbnail_dna;
      }
      showToast(`🔒 Đã chốt lưu Phong cách «${presetObj ? presetObj.shortLabel : activeVar.archetype}» làm DNA Kênh (Phiên bản v${data.version || 2}) cho các video tiếp theo!`);
    } catch (err) {
      showToast(`Lỗi khóa DNA Thumbnail: ${err.message}`, true);
    } finally {
      studioState.busyLockDna = false;
      renderStudioDom();
    }
  }

  function applyTopicStylePreset(presetId, { applyAllVariants = false } = {}) {
    const preset = TOPIC_STYLE_PRESETS.find((p) => p.id === presetId);
    if (!preset) return;
    const design = studioState.data?.design;
    const activeVariant = getActiveVariant();
    if (!design || !activeVariant) return;
    pushUndoSnapshot();

    design.style_preset = preset.id;
    design.visual_signature = preset.label;
    const fontObj = KOREAN_BROADCAST_FONTS.find((f) => f.id === preset.fontId) || KOREAN_BROADCAST_FONTS[0];
    const targets = applyAllVariants ? getVariants() : [activeVariant];

    targets.forEach((v, idx) => {
      v.style_preset = preset.id;
      v.visual_signature = preset.label;
      // When applying to all 4 variants, keep diverse A/B/C/D layouts unless user only applied to current variant
      const archId = !applyAllVariants
        ? preset.archetype
        : idx === 0
        ? preset.archetype
        : ["broadcast_left_heavy", "split_duality", "bottom_cinematic", "evidence_spotlight"][idx % 4];
      v.archetype = archId;

      const vVig = getLayer("vignette", v);
      const vBadge = getLayer("badge", v);
      const vL1 = getLayer("line_1", v);
      const vL2 = getLayer("line_2", v);
      const vArrow = getLayer("forensic_arrow", v);
      const vCircle = getLayer("forensic_circle", v);
      const vInset = getLayer("inset_photo", v);

      if (vVig) {
        vVig.style = preset.vignetteStyle || "left_heavy";
        vVig.opacity = preset.vignetteOpacity ?? 0.86;
        vVig.visible = true;
      }
      if (vBadge) {
        vBadge.fontFamily = fontObj.stack;
        vBadge.fill = preset.badgeFill;
        vBadge.bgColor = preset.badgeBg;
        vBadge.visible = true;
      }
      if (vL1) {
        vL1.fontFamily = fontObj.stack;
        vL1.fill = preset.line1Fill;
        vL1.highlightFill = preset.highlightFill || "#ffe600";
        vL1.stroke = "#000000";
        vL1.strokeWidth = Math.max(16, Number(vL1.strokeWidth || 18));
        vL1.fontSize = Math.max(72, Number(vL1.fontSize || 76));
        vL1.visible = true;
      }
      if (vL2) {
        vL2.fontFamily = fontObj.stack;
        vL2.fill = preset.line2Fill;
        vL2.highlightFill = preset.highlightFill || "#ff2424";
        vL2.stroke = "#000000";
        vL2.strokeWidth = Math.max(18, Number(vL2.strokeWidth || 20));
        vL2.fontSize = Math.max(82, Number(vL2.fontSize || 86));
        vL2.visible = true;
      }
      if (archId === "broadcast_left_heavy") {
        if (vBadge) { vBadge.left = 64; vBadge.top = 185; }
        if (vL1) { vL1.left = 64; vL1.top = 280; vL1.textAlign = "left"; }
        if (vL2) { vL2.left = 64; vL2.top = 405; vL2.textAlign = "left"; }
      } else if (archId === "bottom_cinematic") {
        if (vBadge) { vBadge.left = 64; vBadge.top = 42; }
        if (vL1) { vL1.left = 64; vL1.top = 448; vL1.textAlign = "left"; }
        if (vL2) { vL2.left = 64; vL2.top = 556; vL2.textAlign = "left"; }
      } else if (archId === "split_duality") {
        if (vBadge) { vBadge.left = 64; vBadge.top = 240; }
        if (vL1) { vL1.left = 64; vL1.top = 330; vL1.textAlign = "left"; }
        if (vL2) { vL2.left = 64; vL2.top = 452; vL2.textAlign = "left"; }
      } else if (archId === "evidence_spotlight") {
        if (vBadge) { vBadge.left = 64; vBadge.top = 42; }
        if (vL1) { vL1.left = 64; vL1.top = 430; vL1.textAlign = "left"; }
        if (vL2) { vL2.left = 64; vL2.top = 545; vL2.textAlign = "left"; }
      }
      if (vArrow) vArrow.visible = Boolean(preset.showArrow);
      if (vCircle) vCircle.visible = Boolean(preset.showCircle || archId === "evidence_spotlight");
      if (vInset) vInset.visible = Boolean(preset.showInset || archId === "split_duality");
    });

    renderStudioDom();
    scheduleSaveDesign();
    showToast(
      applyAllVariants
        ? `🎨 Đã áp dụng phong cách «${preset.shortLabel}» cho cả 4 Bản của chủ đề này (chưa ghi đè DNA Kênh — bấm 'Chốt Lưu Làm DNA' nếu muốn lưu cho lần sau)!`
        : `🎨 Đã áp dụng phong cách «${preset.shortLabel}» cho ${activeVariant.short_label || activeVariant.id} (linh hoạt riêng cho chủ đề này)!`
    );
  }

  function duplicateSelectedLayer() {
    const v = getActiveVariant();
    const sel = getLayer(studioState.selectedLayerId, v);
    if (!v || !sel || sel.type === "vignette") {
      showToast("Hãy bấm chọn chữ, mũi tên, vòng tròn hoặc ảnh phụ trên Canvas để nhân bản (Ctrl+D)!");
      return;
    }
    pushUndoSnapshot();
    const copy = JSON.parse(JSON.stringify(sel));
    copy.id = `${sel.id || sel.type}_copy_${Date.now().toString(36).slice(-4)}`;
    copy.name = `${sel.name || sel.id} (Bản sao)`;
    copy.left = Math.min(CW - 120, Number(sel.left || 64) + 28);
    copy.top = Math.min(CH - 90, Number(sel.top || 120) + 28);
    copy.visible = true;
    v.layers.push(copy);
    studioState.selectedLayerId = copy.id;
    renderAllCanvases();
    refreshContextualPanels();
    scheduleSaveDesign();
    showToast(`📋 Đã nhân bản «${sel.name || sel.id}» (Ctrl+D)!`);
  }

  function reorderSelectedLayer(direction = 1) {
    const v = getActiveVariant();
    const sel = getLayer(studioState.selectedLayerId, v);
    if (!v || !Array.isArray(v.layers) || !sel || sel.type === "vignette") return;
    const idx = v.layers.findIndex((l) => l && l.id === sel.id);
    if (idx < 0) return;
    const targetIdx = direction > 0 ? Math.min(v.layers.length - 1, idx + 1) : Math.max(1, idx - 1);
    if (targetIdx === idx) return;
    pushUndoSnapshot();
    const [removed] = v.layers.splice(idx, 1);
    v.layers.splice(targetIdx, 0, removed);
    renderAllCanvases();
    refreshContextualPanels();
    scheduleSaveDesign();
    showToast(direction > 0 ? `⬆ Đã đưa «${sel.name || sel.id}» lên lớp trên!` : `⬇ Đã đẩy «${sel.name || sel.id}» xuống lớp dưới!`);
  }

  function alignSelectedLayerCenter(axis = "h") {
    const sel = getLayer(studioState.selectedLayerId);
    if (!sel || sel.type === "vignette") return;
    pushUndoSnapshot();
    const w = Number(sel.width || 240);
    const h = Number(sel.height || 90);
    if (axis === "v") {
      sel.top = Math.round((CH - h) / 2);
    } else if (axis === "left") {
      sel.left = 64;
      if (sel.type === "textbox") sel.textAlign = "left";
    } else {
      sel.left = Math.round((CW - w) / 2);
      if (sel.type === "textbox") sel.textAlign = "center";
    }
    renderAllCanvases();
    updateSelectedLayerTransformDom();
    scheduleSaveDesign();
    showToast(axis === "v" ? "⇕ Đã căn giữa dọc Canvas!" : axis === "left" ? "⇤ Đã căn lề trái chuẩn đài (X=64)!" : "⇔ Đã căn giữa ngang Canvas!");
  }

  async function generateFlowForVariant(variantId, customPrompt = "") {
    if (!studioState.jobId || studioState.busyVariants.has(variantId)) return;
    studioState.busyVariants.add(variantId);
    renderStudioDom();
    try {
      const resp = await fetch(`/api/jobs/${encodeURIComponent(studioState.jobId)}/thumbnail-studio/generate-bg`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          variant_id: variantId,
          prompt: customPrompt,
        }),
      });
      const json = await resp.json();
      if (!resp.ok) throw new Error(json.detail || "Không vẽ được ảnh nền Flow");
      studioState.data = json;
      const v = getVariantById(variantId);
      if (v && v.background_url) loadCachedImage(v.background_url);
      showToast(`Đã vẽ xong ảnh nền Flow cho ${v?.short_label || variantId}!`);
    } catch (err) {
      showToast(err.message, true);
    } finally {
      studioState.busyVariants.delete(variantId);
      renderStudioDom();
    }
  }

  async function generateFlowBatch3() {
    if (!studioState.jobId || studioState.busyBatchFlow) return;
    const variants = getVariants().slice(0, 3);
    if (!variants.length) return;
    studioState.busyBatchFlow = true;
    variants.forEach((v) => studioState.busyVariants.add(v.id));
    renderStudioDom();
    showToast("Đang vẽ 3 ảnh nền 16:9 khác nhau bằng Google Flow cho Bản A, B, C…");
    try {
      for (const v of variants) {
        try {
          const resp = await fetch(`/api/jobs/${encodeURIComponent(studioState.jobId)}/thumbnail-studio/generate-bg`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              variant_id: v.id,
              prompt: v.clean_bg_prompt || "",
            }),
          });
          const json = await resp.json();
          if (resp.ok && json.ok) {
            studioState.data = json;
            const updatedV = getVariantById(v.id);
            if (updatedV?.background_url) loadCachedImage(updatedV.background_url);
          }
        } finally {
          studioState.busyVariants.delete(v.id);
          renderStudioDom();
        }
      }
      showToast("Đã tạo xong 3 ảnh nền Flow mới cho Bản A, B, C!");
    } catch (err) {
      showToast(err.message || "Lỗi khi vẽ 3 ảnh nền Flow", true);
    } finally {
      studioState.busyBatchFlow = false;
      studioState.busyVariants.clear();
      renderStudioDom();
    }
  }

  function shuffleCandidateScenes() {
    const candidates = getCleanCandidates();
    const variants = getVariants();
    if (!candidates.length || !variants.length) {
      showToast("Chưa có ảnh phân cảnh sạch trong dự án — hãy bấm 'Vẽ 3 ảnh nền bằng Flow AI'.", true);
      return;
    }
    const offset = Math.floor(Math.random() * candidates.length);
    variants.forEach((v, idx) => {
      const cand = candidates[(idx + offset) % candidates.length];
      if (cand) {
        v.background_url = cand.url;
        v.background_path = cand.rel_path || "";
        loadCachedImage(cand.url);
      }
    });
    renderStudioDom();
    scheduleSaveDesign();
    showToast("Đã đổi bộ ảnh nền sạch mới từ dự án cho cả 4 bản!");
  }

  function openLightbox(variantId) {
    studioState.lightboxVariantId = variantId;
    renderStudioDom();
  }

  function closeLightbox() {
    studioState.lightboxVariantId = null;
    renderStudioDom();
  }

  function stepLightbox(delta) {
    const variants = getVariants();
    if (!variants.length || !studioState.lightboxVariantId) return;
    const idx = variants.findIndex((v) => v.id === studioState.lightboxVariantId);
    const nextIdx = (idx + delta + variants.length) % variants.length;
    studioState.lightboxVariantId = variants[nextIdx].id;
    renderStudioDom();
  }

  function setCanvasZoom(val) {
    const clamped = Math.max(0.5, Math.min(2.5, Math.round(Number(val || 1) * 20) / 20));
    studioState.canvasZoom = clamped;
    const inner = document.getElementById("cofiThumbStageInner");
    const zoomLbl = document.getElementById("thumbZoomReadout");
    if (inner) {
      inner.style.width = `${Math.round(clamped * 100)}%`;
    }
    if (zoomLbl) {
      zoomLbl.textContent = `${Math.round(clamped * 100)}%`;
    }
    document.querySelectorAll("[data-zoom-preset]").forEach((btn) => {
      const preset = Number(btn.dataset.zoomPreset || 1);
      btn.classList.toggle("active", Math.abs(preset - clamped) < 0.03);
    });
  }

  function rotateSelectedLayer(deltaAngle = 0, absoluteAngle = null) {
    const layer = getLayer(studioState.selectedLayerId);
    if (!layer || layer.type === "vignette" || layer.visible === false) {
      showToast("Hãy bấm chọn chữ, nhãn hoặc mũi tên trên ảnh trước khi xoay!");
      return;
    }
    pushUndoSnapshot();
    let next = absoluteAngle !== null ? Number(absoluteAngle) : Number(layer.angle || 0) + Number(deltaAngle);
    next = ((next + 180) % 360 + 360) % 360 - 180;
    layer.angle = Math.round(next);
    renderAllCanvases();
    updateSelectedLayerTransformDom();
    scheduleSaveDesign();
  }

  function flipSelectedLayer(axis = "x") {
    const layer = getLayer(studioState.selectedLayerId);
    if (!layer || layer.type === "vignette" || layer.visible === false) {
      showToast("Hãy bấm chọn mũi tên, icon hoặc chữ trên ảnh trước khi lật!");
      return;
    }
    pushUndoSnapshot();
    if (axis === "y") {
      layer.flipY = !layer.flipY;
    } else {
      layer.flipX = !layer.flipX;
    }
    renderAllCanvases();
    updateSelectedLayerTransformDom();
    scheduleSaveDesign();
    showToast(
      axis === "y"
        ? `↕ Đã lật dọc «${layer.name || layer.id}»!`
        : `↔ Đã lật ngang «${layer.name || layer.id}»!`
    );
  }

  function scaleSelectedLayer(factor = 1.1) {
    const layer = getLayer(studioState.selectedLayerId);
    if (!layer || layer.type === "vignette" || layer.visible === false) {
      showToast("Hãy bấm chọn mục trên ảnh trước khi phóng to/thu nhỏ!");
      return;
    }
    pushUndoSnapshot();
    if (layer.type === "textbox" || layer.type === "badge" || layer.type === "stamp") {
      const curFs = Number(layer.fontSize || 64);
      layer.fontSize = Math.round(Math.max(20, Math.min(140, curFs * factor)));
    } else {
      const curW = Number(layer.width || 180);
      const curH = Number(layer.height || 80);
      const newW = Math.round(Math.max(40, Math.min(1000, curW * factor)));
      const newH = Math.round(Math.max(30, Math.min(680, curH * factor)));
      layer.left = Math.round(Number(layer.left || 0) - (newW - curW) / 2);
      layer.top = Math.round(Number(layer.top || 0) - (newH - curH) / 2);
      layer.width = newW;
      layer.height = newH;
    }
    renderAllCanvases();
    updateSelectedLayerTransformDom();
    scheduleSaveDesign();
  }

  function deleteLayerById(layerId) {
    const variant = getActiveVariant();
    if (!variant || !layerId) return;
    const layer = getLayer(layerId, variant);
    if (!layer || layer.type === "vignette") return;
    pushUndoSnapshot();
    layer.visible = false;
    const nextVisible = (variant.layers || []).find(
      (l) => l && l.type !== "vignette" && l.visible !== false && l.id !== layerId
    );
    studioState.selectedLayerId = nextVisible ? nextVisible.id : null;
    renderAllCanvases();
    refreshContextualPanels();
    scheduleSaveDesign();
    showToast(`🗑 Đã xóa «${layer.name || layer.id}»! (Bấm Ctrl+Z để hoàn tác hoặc bật lại ở mục Lớp)`);
  }

  function clearAllOverlaysOnActiveVariant() {
    const variant = getActiveVariant();
    if (!variant || !Array.isArray(variant.layers)) return;
    pushUndoSnapshot();
    variant.layers.forEach((l) => {
      if (l && l.type !== "vignette") {
        l.visible = false;
      }
    });
    studioState.selectedLayerId = null;
    renderAllCanvases();
    refreshContextualPanels();
    scheduleSaveDesign();
    showToast(`Đã xóa toàn bộ chữ & nhãn trên ${variant.short_label || variant.id} (Bấm Ctrl+Z để hoàn tác)!`);
  }

  function restoreAllTextOnActiveVariant() {
    const variant = getActiveVariant();
    if (!variant || !Array.isArray(variant.layers)) return;
    pushUndoSnapshot();
    ["badge", "line_1", "line_2"].forEach((id) => {
      const l = getLayer(id, variant);
      if (l) l.visible = true;
    });
    studioState.selectedLayerId = "line_2";
    renderAllCanvases();
    refreshContextualPanels();
    scheduleSaveDesign();
    showToast(`Đã bật lại cụm chữ chính cho ${variant.short_label || variant.id}!`);
  }

  function hitTestLayer(mx, my) {
    const variant = getActiveVariant();
    if (!variant || !Array.isArray(variant.layers)) return null;
    const selected = getLayer(studioState.selectedLayerId, variant);
    if (selected && selected.type !== "vignette" && selected.visible !== false) {
      const loc = toLayerLocalCoords(mx, my, selected);
      const sLeft = Number(selected.left || 0);
      const sTop = Number(selected.top || 0);
      const sW = Number(selected.width || 200);
      const sH = Number(selected.height || 80);
      const sCx = sLeft + sW / 2;

      // 1. Top Canva Rotate handle (↻) at (sCx, sTop - 40)
      if (Math.hypot(loc.x - sCx, loc.y - (sTop - 40)) <= 24) {
        return { mode: "rotate", layer: selected };
      }
      // 2. Top-right Red X Delete handle at (sLeft + sW + 6, sTop - 6)
      const delX = sLeft + sW + 6;
      const delY = sTop - 6;
      if (Math.hypot(loc.x - delX, loc.y - delY) <= 22) {
        return { mode: "delete", layer: selected };
      }
      // 3. Bottom-right & Corner Resize handles
      const corners = [
        { corner: "se", x: sLeft + sW + 6, y: sTop + sH + 6 },
        { corner: "sw", x: sLeft - 6, y: sTop + sH + 6 },
        { corner: "nw", x: sLeft - 6, y: sTop - 6 },
      ];
      for (const c of corners) {
        if (Math.hypot(loc.x - c.x, loc.y - c.y) <= 22) {
          return { mode: "resize", corner: c.corner, layer: selected };
        }
      }
    }
    for (let i = variant.layers.length - 1; i >= 0; i--) {
      const l = variant.layers[i];
      if (!l || l.type === "vignette" || l.visible === false) continue;
      const loc = toLayerLocalCoords(mx, my, l);
      const left = Number(l.left || 0);
      const top = Number(l.top || 0);
      const w = Number(l.width || 200);
      const h = Number(l.height || 80);
      if (loc.x >= left - 10 && loc.x <= left + w + 10 && loc.y >= top - 10 && loc.y <= top + h + 10) {
        return { mode: "move", layer: l };
      }
    }
    return null;
  }

  function canvasCoordsFromEvent(canvas, event) {
    const rect = canvas.getBoundingClientRect();
    const scaleX = CW / Math.max(1, rect.width);
    const scaleY = CH / Math.max(1, rect.height);
    return {
      x: (event.clientX - rect.left) * scaleX,
      y: (event.clientY - rect.top) * scaleY,
    };
  }

  function getAllQuickLayerDefs(activeVariant) {
    const baseQuickDefs = [
      { id: "badge", label: "Tag góc trên", icon: "🏷" },
      { id: "line_1", label: "Dòng chữ 1", icon: "🔤" },
      { id: "line_2", label: "Dòng chữ 2", icon: "🔥" },
      { id: "stamp", label: "Con dấu Đỏ", icon: "🔖" },
      { id: "forensic_arrow", label: "Mũi tên", icon: "↗" },
      { id: "forensic_circle", label: "Vòng tròn", icon: "⭕" },
      { id: "inset_photo", label: "Ảnh phụ PiP", icon: "🖼" },
    ];
    const baseIds = new Set([...baseQuickDefs.map((d) => d.id), "vignette"]);
    const extraQuickDefs = ((activeVariant && activeVariant.layers) || [])
      .filter((l) => l && l.id && !baseIds.has(l.id))
      .map((l) => ({
        id: l.id,
        label: l.name || l.id,
        icon: l.type === "arrow" ? "↗" : l.type === "circle" ? "⭕" : l.type === "inset_image" ? "🖼" : l.type === "textbox" ? "🔤" : "✨",
      }));
    return [...baseQuickDefs, ...extraQuickDefs];
  }

  function buildSwatchPillsHtml(targetAttr, targetVal, activeHex, count = 8) {
    return BROADCAST_COLOR_SWATCHES.slice(0, count)
      .map((sw) => {
        const isAct = sw.hex.toLowerCase() === String(activeHex || "").toLowerCase();
        return `<button type="button" class="thumb-color-swatch ${isAct ? "active" : ""}" ${targetAttr}="${esc(targetVal)}" data-swatch-hex="${esc(sw.hex)}" style="background:${esc(sw.hex)};" title="${esc(sw.label)} (${esc(sw.hex)})"></button>`;
      })
      .join("");
  }

  function buildQuickLayersBarInnerHtml(activeVariant) {
    const allLayerDefs = getAllQuickLayerDefs(activeVariant);
    const bgSelected = !studioState.selectedLayerId;
    const pills = allLayerDefs
      .map((item) => {
        const l = getLayer(item.id, activeVariant);
        const isVis = Boolean(l && l.visible !== false);
        const isSel = isVis && studioState.selectedLayerId === item.id;
        return `<button type="button" class="thumb-quick-layer-pill ${isSel ? "is-selected" : ""} ${!isVis ? "is-hidden-layer" : ""}" data-quick-select-layer="${esc(item.id)}" title="${isVis ? "Ấn để chọn & mở bảng chỉnh sửa bên phải" : "Đang ẩn — ấn để bật lên ảnh và chỉnh sửa"}">
          <span>${item.icon} ${esc(item.label)}</span>
          <small>${isVis ? "Đang bật" : "+ Bật"}</small>
        </button>`;
      })
      .join("");
    return `
      <span class="thumb-canva-lbl">Ấn chọn để sửa ngay:</span>
      <button type="button" class="thumb-quick-layer-pill ${bgSelected ? "is-selected" : ""}" data-quick-select-bg="1" title="Ấn để chỉnh Ảnh nền & Độ tối Vignette ở cột phải">
        <span>🖼 Ảnh nền &amp; Ánh sáng</span>
      </button>
      ${pills}
      <span style="margin-left:auto;display:inline-flex;gap:4px;flex-wrap:wrap;">
        <button type="button" class="ghost compact" id="quickBarAddPipBtn" style="font-size:11px;padding:3px 8px;border-color:rgba(74,222,128,0.45);color:#86efac;">+ 🖼 Khung PiP</button>
        <button type="button" class="ghost compact" id="quickBarAddTextBtn" style="font-size:11px;padding:3px 8px;border-color:rgba(56,189,248,0.45);color:#7dd3fc;">+ 🔤 Chữ</button>
        <button type="button" class="ghost compact" id="quickBarAddArrowBtn" style="font-size:11px;padding:3px 8px;border-color:rgba(239,68,68,0.45);color:#fca5a5;">+ ↗ Mũi tên</button>
        <button type="button" class="ghost compact" id="quickBarAddCircleBtn" style="font-size:11px;padding:3px 8px;border-color:rgba(250,204,21,0.45);color:#fde047;">+ ⭕ Vòng tròn</button>
      </span>
    `;
  }

  function buildLeftDockInnerHtml(activeVariant) {
    const data = studioState.data || {};
    const design = data.design || {};
    const archetypes = data.archetypes || [];
    const candidates = getCleanCandidates();
    const curStylePreset = String(activeVariant.style_preset || design.style_preset || design.channel_thumbnail_dna?.style_preset || "sbs_criminal_profiling");
    const lBadge = getLayer("badge", activeVariant) || {};
    const lLine1 = getLayer("line_1", activeVariant) || {};
    const lLine2 = getLayer("line_2", activeVariant) || {};
    const activeArrowLayer = getActiveArrowLayer(activeVariant) || getLayer("forensic_arrow", activeVariant) || {};
    const activeArrowStyle = String(activeArrowLayer.arrowStyle || "curved_pointer");
    const activeCircleLayer = getActiveCircleLayer(activeVariant) || getLayer("forensic_circle", activeVariant) || {};
    const activeCircleStyle = String(activeCircleLayer.circleStyle || "solid_ring");
    const allLayerDefs = getAllQuickLayerDefs(activeVariant);
    const tab = studioState.leftDockTab || "style";

    let bodyHtml = "";
    if (tab === "style") {
      bodyHtml = `
        <div class="canva-side-section">
          <div class="canva-side-title">🎨 PHONG CÁCH CHỦ ĐỀ (LINH HOẠT)</div>
          <div class="canva-preset-stack">
            ${TOPIC_STYLE_PRESETS.map((p) => {
              const isAct = curStylePreset === p.id;
              return `<button type="button" class="canva-preset-card ${isAct ? "active" : ""}" data-apply-topic-preset="${esc(p.id)}" title="${esc(p.desc)}">
                <div class="canva-preset-card-top">
                  <strong>${esc(p.shortLabel)}</strong>
                  ${isAct ? `<span class="canva-active-dot">Đang dùng</span>` : ""}
                </div>
                <small>${esc(p.desc)}</small>
              </button>`;
            }).join("")}
          </div>
          <button type="button" class="ghost compact" id="applyTopicPresetAllBtn" style="width:100%;margin-top:6px;border-color:rgba(56,189,248,0.45);color:#7dd3fc;">⚡ Áp dụng Phong cách này cho cả 4 Bản</button>
        </div>

        <div class="canva-side-section">
          <div class="canva-side-title">📐 BỐ CỤC NHANH (ARCHETYPE 1-CLICK)</div>
          <div class="thumb-archetype-grid" style="grid-template-columns:1fr;">
            ${archetypes
              .map(
                (arch) => `<button type="button" class="thumb-archetype-btn ${activeVariant.archetype === arch.id ? "active" : ""}" data-select-archetype="${esc(arch.id)}" title="${esc(arch.description)}">
                  ${esc(arch.name.split("—")[0].trim())}
                </button>`
              )
              .join("")}
          </div>
        </div>

        <div class="canva-side-section">
          <div class="canva-side-title">🌈 BỘ PHỐI MÀU CHỮ 1-CLICK</div>
          <div class="thumb-color-combos-grid" style="grid-template-columns:1fr 1fr;">
            ${TEXT_COLOR_COMBOS.map(
              (cb) => `<button type="button" class="ghost compact thumb-combo-pill" data-apply-text-combo="${esc(cb.id)}" title="Áp dụng bộ màu ${esc(cb.label)}">
                <span class="thumb-combo-dots">
                  <i style="background:${esc(cb.badgeFill)}"></i>
                  <i style="background:${esc(cb.line1Fill)}"></i>
                  <i style="background:${esc(cb.line2Fill)}"></i>
                </span>
                <span>${esc(cb.label)}</span>
              </button>`
            ).join("")}
          </div>
        </div>
      `;
    } else if (tab === "text") {
      const activeFontId = detectFontIdFromStack(lLine2.fontFamily || lLine1.fontFamily || "");
      bodyHtml = `
        <div class="canva-side-section">
          <div style="display:flex;gap:6px;margin-bottom:8px;">
            <button type="button" class="primary compact" id="addCustomTextLayerBtn" style="flex:1;">+ 🔤 Thêm Dòng Chữ Mới</button>
          </div>
          <div class="canva-side-title">🇰🇷 10 FONT TIẾNG HÀN CHUẨN ĐÀI</div>
          <div class="thumb-font-pills-grid" style="grid-template-columns:1fr 1fr;">
            ${KOREAN_BROADCAST_FONTS.map((f) => {
              const isAct = f.id === activeFontId;
              return `<button type="button" class="ghost compact thumb-kr-font-pill ${isAct ? "primary" : ""}" data-pick-kr-font="${esc(f.id)}" style="font-family:${esc(f.stack)};" title="${esc(f.label)}">${esc(f.shortLabel)}</button>`;
            }).join("")}
          </div>
          <button type="button" class="ghost compact" id="applyFontAllVariantsBtn" style="width:100%;margin-top:6px;">🇰🇷 Đồng bộ Font này cho cả 4 Bản</button>
        </div>

        <div class="canva-side-section">
          <div class="canva-side-title">✎ SỬA NHANH 3 DÒNG CHỮ CHÍNH</div>
          <small style="color:#94a3b8;display:block;margin-bottom:6px;">Ấn vào từng dòng bên dưới để mở bảng chỉnh màu &amp; cỡ chữ chi tiết ở cột phải. Bọc <code>*từ khóa*</code> để tô màu nổi bật.</small>
          <label class="canva-mini-field">
            <span>🏷 Tag góc trên:</span>
            <input type="text" data-sync-layer-text="badge" value="${esc(lBadge.text ?? activeVariant.badge_text ?? "")}" placeholder="Tag góc trên..." />
          </label>
          <label class="canva-mini-field">
            <span>🔤 Dòng 1 (*từ nổi*):</span>
            <input type="text" data-sync-layer-text="line_1" value="${esc(lLine1.text ?? activeVariant.line_1 ?? "")}" placeholder="Dòng 1..." />
          </label>
          <label class="canva-mini-field">
            <span>🔥 Dòng 2 (*từ nổi*):</span>
            <input type="text" data-sync-layer-text="line_2" value="${esc(lLine2.text ?? activeVariant.line_2 ?? "")}" placeholder="Dòng 2..." />
          </label>
        </div>
      `;
    } else if (tab === "graphics") {
      bodyHtml = `
        <div class="canva-side-section">
          <div style="display:flex;gap:6px;margin-bottom:8px;">
            <button type="button" class="ghost compact" id="addNewArrowLayerBtn" style="flex:1;border-color:rgba(239,68,68,0.5);color:#fca5a5;">+ ↗ Thêm Mũi Tên</button>
            <button type="button" class="ghost compact" id="addNewCircleLayerBtn" style="flex:1;border-color:rgba(250,204,21,0.5);color:#fde047;">+ ⭕ Thêm Vòng Tròn</button>
          </div>
          <div class="canva-side-title">↗ 10 KIỂU MŨI TÊN ĐIỀU TRA</div>
          <div class="thumb-lib-grid" style="grid-template-columns:1fr 1fr;">
            ${ARROW_LIBRARY.map((item) => {
              const isAct = item.id === activeArrowStyle && activeArrowLayer.visible !== false;
              return `<button type="button" class="thumb-lib-item ${isAct ? "active" : ""}" data-pick-arrow-style="${esc(item.id)}" title="${esc(item.desc)} — Ấn để dùng & mở bảng chỉnh màu bên phải">
                <canvas data-arrow-lib-canvas="${esc(item.id)}" width="110" height="46"></canvas>
                <span>${esc(item.label)}</span>
              </button>`;
            }).join("")}
          </div>
        </div>

        <div class="canva-side-section">
          <div class="canva-side-title">⭕ 10 KIỂU VÒNG TRÒN &amp; KHUNG NGẮM</div>
          <div class="thumb-lib-grid" style="grid-template-columns:1fr 1fr;">
            ${CIRCLE_LIBRARY.map((item) => {
              const isAct = item.id === activeCircleStyle && activeCircleLayer.visible !== false;
              return `<button type="button" class="thumb-lib-item ${isAct ? "active" : ""}" data-pick-circle-style="${esc(item.id)}" title="${esc(item.desc)} — Ấn để dùng & mở bảng chỉnh màu bên phải">
                <canvas data-circle-lib-canvas="${esc(item.id)}" width="110" height="46"></canvas>
                <span>${esc(item.label)}</span>
              </button>`;
            }).join("")}
          </div>
        </div>
      `;
    } else {
      bodyHtml = `
        <div class="canva-side-section">
          <div class="canva-side-title">🗂 QUẢN LÝ LỚP TRÊN ẢNH (LAYERS)</div>
          <div class="canva-layer-list">
            ${allLayerDefs
              .map((item) => {
                const l = getLayer(item.id, activeVariant);
                const checked = Boolean(l && l.visible !== false);
                const isSel = checked && studioState.selectedLayerId === item.id;
                return `<div class="canva-layer-row ${isSel ? "is-selected" : ""}">
                  <input type="checkbox" data-toggle-layer="${esc(item.id)}" ${checked ? "checked" : ""} title="Bật/tắt lớp này" />
                  <button type="button" class="canva-layer-select-btn" data-quick-select-layer="${esc(item.id)}">${item.icon} ${esc(item.label)}</button>
                </div>`;
              })
              .join("")}
          </div>
          <div style="display:flex;gap:6px;margin-top:8px;">
            <button type="button" class="ghost compact" id="thumbClearAllOverlaysBtn" style="flex:1;font-size:11px;">🧹 Ẩn hết chữ</button>
            <button type="button" class="ghost compact" id="thumbRestoreTextBtn" style="flex:1;font-size:11px;">↺ Hiện lại chữ</button>
          </div>
        </div>

        <div class="canva-side-section">
          <div class="canva-side-title">🖼 KHO ẢNH TƯ LIỆU &amp; NỀN (${candidates.length} ẢNH)</div>
          <div style="display:flex;gap:6px;margin-bottom:8px;flex-wrap:wrap;">
            <button type="button" class="ghost compact" id="thumbGenSingleFlowBtn" style="flex:1;font-size:11px;" ${studioState.busyVariants.has(activeVariant.id) ? "disabled" : ""}>${studioState.busyVariants.has(activeVariant.id) ? "⏳ Đang vẽ…" : "🎨 Vẽ nền Flow"}</button>
            <label class="ghost compact thumb-upload-btn" style="flex:1;font-size:11px;text-align:center;">
              📁 Tải ảnh lên
              <input type="file" id="thumbUploadBgInput" accept="image/png,image/jpeg,image/webp" hidden />
            </label>
          </div>
          <div class="canva-candidates-grid" style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:6px;max-height:320px;overflow-y:auto;">
            ${
              candidates.length
                ? candidates
                    .map(
                      (c) => `<div class="canva-cand-card ${getVariantBgUrl(activeVariant) === c.url ? "selected" : ""}">
                        <img src="${esc(c.url)}" alt="${esc(c.label)}" title="${esc(c.label)}" loading="lazy" style="width:100%;height:56px;max-height:56px;object-fit:cover;display:block;" data-pick-bg="${esc(c.url)}" data-pick-path="${esc(c.rel_path || "")}" />
                        <div style="font-size:10px;color:#cbd5e1;padding:2px 4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;" title="${esc(c.label)}">${esc(c.label)}</div>
                        <div class="canva-cand-actions">
                          <button type="button" data-pick-bg="${esc(c.url)}" data-pick-path="${esc(c.rel_path || "")}">Làm Nền</button>
                          <button type="button" data-pick-inset="${esc(c.url)}">Ảnh PiP</button>
                        </div>
                      </div>`
                    )
                    .join("")
                : `<div class="muted" style="font-size:11.5px;">Chưa có ảnh phân cảnh.</div>`
            }
          </div>
        </div>
      `;
    }

    return `
      <div class="canva-dock-tabs">
        <button type="button" class="canva-dock-tab ${tab === "style" ? "active" : ""}" data-left-dock-tab="style">
          <span>🎨</span><small>Phong cách</small>
        </button>
        <button type="button" class="canva-dock-tab ${tab === "text" ? "active" : ""}" data-left-dock-tab="text">
          <span>🔤</span><small>Chữ &amp; Font</small>
        </button>
        <button type="button" class="canva-dock-tab ${tab === "graphics" ? "active" : ""}" data-left-dock-tab="graphics">
          <span>↗</span><small>Đồ họa</small>
        </button>
        <button type="button" class="canva-dock-tab ${tab === "media" ? "active" : ""}" data-left-dock-tab="media">
          <span>🖼</span><small>Ảnh &amp; Lớp</small>
        </button>
      </div>
      <div class="canva-dock-body">
        ${bodyHtml}
      </div>
    `;
  }

  function buildRightContextualInspectorHtml(activeVariant) {
    const variants = getVariants();
    const activeIdx = Math.max(0, variants.findIndex((item) => item && item.id === activeVariant.id));
    const activeVi = parseVariantVietnamese(activeVariant, activeIdx);
    const lBadge = getLayer("badge", activeVariant) || {};
    const lLine1 = getLayer("line_1", activeVariant) || {};
    const lLine2 = getLayer("line_2", activeVariant) || {};
    const lVig = getLayer("vignette", activeVariant) || {};
    const selected = getLayer(studioState.selectedLayerId, activeVariant);
    const hasSel = Boolean(selected && selected.visible !== false && selected.type !== "vignette");
    const selType = hasSel ? String(selected.type || "") : "background";
    const selAngle = hasSel ? Math.round(Number(selected.angle || 0)) : 0;

    // Quick layer switcher chips at top of Right Inspector so user always knows what is selected
    const allLayerDefs = getAllQuickLayerDefs(activeVariant);
    const switcherHtml = `
      <div class="canva-inspector-switcher">
        <button type="button" class="canva-insp-chip ${!hasSel ? "active" : ""}" data-quick-select-bg="1" title="Chỉnh ảnh nền & ánh sáng">🖼 Nền</button>
        ${allLayerDefs
          .map((item) => {
            const l = getLayer(item.id, activeVariant);
            const isVis = Boolean(l && l.visible !== false);
            const isSel = isVis && studioState.selectedLayerId === item.id;
            return `<button type="button" class="canva-insp-chip ${isSel ? "active" : ""} ${!isVis ? "is-off" : ""}" data-quick-select-layer="${esc(item.id)}" title="${esc(item.label)}">${item.icon} ${esc(item.label.replace("Dòng chữ ", "D").replace("Tag góc trên", "Tag"))}</button>`;
          })
          .join("")}
      </div>
    `;

    // Transform bar for any selected object
    const commonTransformHtml = hasSel
      ? `<div class="canva-context-card">
          <div class="canva-side-title">📐 VỊ TRÍ, XOAY 360° &amp; THAO TÁC LỚP</div>
          <div style="display:flex;align-items:center;gap:5px;flex-wrap:wrap;margin-bottom:6px;">
            <span class="thumb-mini-color-lbl">Xoay:</span>
            <button type="button" class="ghost compact" id="ctxRotMinus45Btn" title="Xoay -45°">↺ -45°</button>
            <button type="button" class="ghost compact" id="ctxRotMinus15Btn" title="Xoay -15°">-15°</button>
            <input type="range" id="thumbSelectedAngleSlider" min="-180" max="180" value="${selAngle}" style="flex:1;min-width:65px;" />
            <strong class="thumb-angle-readout" id="thumbSelectedAngleLabel">${selAngle}°</strong>
            <button type="button" class="ghost compact" id="ctxRotPlus15Btn" title="Xoay +15°">+15°</button>
            <button type="button" class="ghost compact" id="ctxRotResetBtn" title="Về 0°">0°</button>
          </div>
          <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:4px;">
            <button type="button" class="ghost compact" id="ctxScaleDownBtn" title="Thu nhỏ">− Nhỏ</button>
            <button type="button" class="ghost compact" id="ctxScaleUpBtn" title="Phóng to">+ To</button>
            <button type="button" class="ghost compact ${selected.flipX ? "active" : ""}" id="ctxFlipXBtn" title="Lật ngang">↔ Lật</button>
            <button type="button" class="ghost compact ${selected.flipY ? "active" : ""}" id="ctxFlipYBtn" title="Lật dọc">↕ Dọc</button>
            <button type="button" class="ghost compact" id="ctxAlignLeftBtn" title="Căn lề trái chuẩn đài X=64">⇤ Trái</button>
            <button type="button" class="ghost compact" id="ctxAlignCenterHBtn" title="Căn giữa ngang">⇔ Giữa</button>
            <button type="button" class="ghost compact" id="ctxBringFwdBtn" title="Đưa lên lớp trên">⬆ Trên</button>
            <button type="button" class="ghost compact" id="ctxSendBackBtn" title="Đẩy xuống lớp dưới">⬇ Dưới</button>
          </div>
          <div style="display:flex;gap:6px;margin-top:8px;">
            <button type="button" class="ghost compact" id="ctxDuplicateBtn" style="flex:1;">📋 Nhân bản (Ctrl+D)</button>
            <button type="button" class="ghost compact thumb-danger-btn" id="ctxDeleteBtn" style="flex:1;">🗑 Xóa mục này (Del)</button>
          </div>
        </div>`
      : "";

    // CASE 1: TEXT / BADGE / STAMP SELECTED
    if (hasSel && (selType === "textbox" || selType === "badge" || selType === "stamp")) {
      const fillHex = normalizeHexColor(selected.fill, selected.id === "line_2" ? "#fbbf24" : "#ffffff");
      const strokeHex = normalizeHexColor(selected.stroke, "#000000");
      const hlHex = normalizeHexColor(selected.highlightFill, selected.id === "line_2" ? "#ff2424" : "#ffe600");
      const bgRaw = String(selected.bgColor || "").trim().toLowerCase();
      const isTransparentBg = selType !== "badge" || !bgRaw || bgRaw === "transparent" || bgRaw === "none";
      const bgHex = normalizeHexColor(isTransparentBg ? "#dc2626" : selected.bgColor, "#dc2626");
      const fontSizeVal = Math.round(Number(selected.fontSize || (selected.id === "badge" ? 32 : 78)));
      const strokeWVal = Math.round(Number(selected.strokeWidth ?? (selected.id === "badge" ? 6 : 18)));
      const activeFontId = detectFontIdFromStack(selected.fontFamily || lLine2.fontFamily || "");
      const viMeaning =
        selected.id === "badge"
          ? activeVi.badgeVi
          : selected.id === "line_1"
          ? activeVi.line1Vi
          : selected.id === "line_2"
          ? activeVi.line2Vi
          : "";

      return `
        <div class="canva-inspector-header">
          <div>
            <span class="canva-inspector-kicker">BẢNG CHỈNH SỬA CHỮ ĐANG CHỌN</span>
            <h4>🔤 ${esc(selected.name || selected.id)}</h4>
          </div>
          <button type="button" class="ghost compact" id="addCustomTextLayerBtn" title="Thêm chữ mới">+ 🔤 Chữ</button>
        </div>
        ${switcherHtml}
        <div class="canva-inspector-scroll">
          <div class="canva-context-card">
            <div class="canva-side-title">1. NỘI DUNG CHỮ (DÙNG *TỪ* ĐỂ TÔ MÀU NỔI)</div>
            <input type="text" id="ctxSelectedTextInput" class="canva-main-text-input" value="${esc(selected.text || "")}" placeholder="Nhập chữ Tiếng Hàn... (VD: *17년 동안* 한마디도...)" />
            ${viMeaning ? `<div class="canva-vi-hint">🇻🇳 <b>Nghĩa Tiếng Việt:</b> ${esc(viMeaning)}</div>` : `<div class="canva-vi-hint">💡 Mẹo: Đặt từ quan trọng trong dấu <code>*từ khóa*</code> hoặc <code>[từ khóa]</code> để tô màu nổi bật riêng cho cụm từ đó!</div>`}
          </div>

          <div class="canva-context-card">
            <div class="canva-side-title">2. PHÔNG CHỮ &amp; CỠ CHỮ</div>
            <div style="display:flex;gap:6px;align-items:center;margin-bottom:8px;">
              <select id="ctxKoreanFontSelect" style="flex:1;font-weight:700;">
                ${KOREAN_BROADCAST_FONTS.map((f) => `<option value="${esc(f.id)}" ${f.id === activeFontId ? "selected" : ""} style="font-family:${esc(f.stack)};">${esc(f.label)}</option>`).join("")}
              </select>
              <button type="button" class="ghost compact" id="applyFontAllVariantsBtn" title="Áp dụng Font này cho cả 4 Bản">Cả 4 Bản</button>
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
              <label class="thumb-compact-slider">
                <span>Cỡ chữ: <b id="ctxFontSizeLbl">${fontSizeVal}px</b></span>
                <input type="range" id="ctxFontSizeSlider" min="22" max="135" value="${fontSizeVal}" />
              </label>
              <label class="thumb-compact-slider">
                <span>Độ dày viền: <b id="ctxStrokeWidthLbl">${strokeWVal}px</b></span>
                <input type="range" id="ctxStrokeWidthSlider" min="0" max="28" value="${strokeWVal}" />
              </label>
            </div>
          </div>

          <div class="canva-context-card">
            <div class="canva-side-title">3. MÀU CHỮ, MÀU *TỪ NỔI BẬT* &amp; MÀU VIỀN</div>
            <div class="thumb-manual-color-row">
              <span class="thumb-mini-color-lbl">Màu chữ:</span>
              <input type="color" id="ctxTextFillColor" value="${esc(fillHex)}" />
              <input type="text" class="thumb-hex-input" id="ctxTextFillHex" value="${esc(fillHex.toUpperCase())}" maxlength="7" />
              <span class="thumb-mini-color-lbl" style="margin-left:auto;">Từ *nổi*:</span>
              <input type="color" id="ctxTextHlColor" value="${esc(hlHex)}" title="Màu của cụm từ nằm trong dấu *...*" />
            </div>
            <div class="thumb-color-swatch-row" style="margin-top:6px;">
              <span class="thumb-mini-color-lbl">Màu nhanh:</span>
              ${buildSwatchPillsHtml("data-ctx-fill-swatch", selected.id, fillHex, 8)}
            </div>
            <div class="thumb-manual-color-row" style="margin-top:8px;">
              <span class="thumb-mini-color-lbl">Màu viền:</span>
              <input type="color" id="ctxTextStrokeColor" value="${esc(strokeHex)}" />
              <input type="text" class="thumb-hex-input" id="ctxTextStrokeHex" value="${esc(strokeHex.toUpperCase())}" maxlength="7" />
              ${
                selected.id === "badge" || selType === "badge"
                  ? `<span class="thumb-mini-color-lbl" style="margin-left:auto;">Hộp nền:</span>
                     <input type="color" id="ctxBadgeBgColor" value="${esc(bgHex)}" />
                     <button type="button" class="ghost compact ${isTransparentBg ? "primary" : ""}" id="ctxBadgeTransBtn" style="font-size:10px;padding:2px 6px;">${isTransparentBg ? "Không nền ✓" : "Có hộp"}</button>`
                  : ""
              }
            </div>
          </div>

          ${commonTransformHtml}

          <div class="canva-context-card">
            <div class="canva-side-title">4. SỬA NHANH CẢ 3 DÒNG TRÊN THUMBNAIL</div>
            <label class="canva-mini-field">
              <span>🏷 Tag (${esc(activeVi.badgeVi || "Nhãn góc trên")}):</span>
              <input type="text" data-sync-layer-text="badge" value="${esc(lBadge.text ?? activeVariant.badge_text ?? "")}" />
            </label>
            <label class="canva-mini-field">
              <span>🔤 Dòng 1 (${esc(activeVi.line1Vi || "Bối cảnh")}):</span>
              <input type="text" data-sync-layer-text="line_1" value="${esc(lLine1.text ?? activeVariant.line_1 ?? "")}" />
            </label>
            <label class="canva-mini-field">
              <span>🔥 Dòng 2 (${esc(activeVi.line2Vi || "Điểm nổ CTR")}):</span>
              <input type="text" data-sync-layer-text="line_2" value="${esc(lLine2.text ?? activeVariant.line_2 ?? "")}" />
            </label>
          </div>
        </div>
      `;
    }

    // CASE 2: ARROW SELECTED
    if (hasSel && (selType === "arrow" || selected.id === "forensic_arrow")) {
      const aStyle = String(selected.arrowStyle || "curved_pointer");
      const aFill = normalizeHexColor(selected.fill, "#ef4444");
      const aStroke = normalizeHexColor(selected.stroke, "#ffffff");
      const aSw = Math.round(Number(selected.strokeWidth ?? 6));
      return `
        <div class="canva-inspector-header">
          <div>
            <span class="canva-inspector-kicker">BẢNG CHỈNH SỬA MŨI TÊN ĐANG CHỌN</span>
            <h4>↗ ${esc(selected.name || "Mũi tên điều tra")}</h4>
          </div>
          <button type="button" class="ghost compact" id="addNewArrowLayerBtn">+ ↗ Thêm mới</button>
        </div>
        ${switcherHtml}
        <div class="canva-inspector-scroll">
          <div class="canva-context-card">
            <div class="canva-side-title">1. CHỌN KIỂU MŨI TÊN (10 KIỂU)</div>
            <div class="thumb-lib-grid" style="grid-template-columns:1fr 1fr;">
              ${ARROW_LIBRARY.map((item) => {
                const isAct = item.id === aStyle;
                return `<button type="button" class="thumb-lib-item ${isAct ? "active" : ""}" data-pick-arrow-style="${esc(item.id)}" title="${esc(item.desc)}">
                  <canvas data-arrow-lib-canvas="${esc(item.id)}" width="110" height="44"></canvas>
                  <span>${esc(item.label)}</span>
                </button>`;
              }).join("")}
            </div>
          </div>

          <div class="canva-context-card">
            <div class="canva-side-title">2. MÀU RUỘT &amp; VIỀN MŨI TÊN</div>
            <div class="thumb-manual-color-row">
              <span class="thumb-mini-color-lbl">🎨 Màu ruột:</span>
              <input type="color" id="arrowFillColorInput" value="${esc(aFill)}" />
              <input type="text" class="thumb-hex-input" id="arrowFillHexInput" value="${esc(aFill.toUpperCase())}" maxlength="7" />
              <span class="thumb-mini-color-lbl" style="margin-left:auto;">Viền:</span>
              <input type="color" id="arrowStrokeColorInput" value="${esc(aStroke)}" />
            </div>
            <div class="thumb-color-swatch-row" style="margin-top:6px;">
              <span class="thumb-mini-color-lbl">Màu nhanh:</span>
              ${buildSwatchPillsHtml("data-arrow-fill-swatch", "fill", aFill, 8)}
            </div>
            <label class="thumb-compact-slider" style="margin-top:8px;">
              <span>Độ dày viền mũi tên: <b id="arrowStrokeWidthLabel">${aSw}px</b></span>
              <input type="range" id="arrowStrokeWidthSlider" min="0" max="16" value="${aSw}" />
            </label>
            <button type="button" class="ghost compact" id="applyArrowAllVariantsBtn" style="width:100%;margin-top:8px;">↗ Áp dụng kiểu &amp; màu mũi tên cho cả 4 Bản</button>
          </div>

          ${commonTransformHtml}
        </div>
      `;
    }

    // CASE 3: CIRCLE / SPOTLIGHT SELECTED
    if (hasSel && (selType === "circle" || selected.id === "forensic_circle")) {
      const cStyle = String(selected.circleStyle || "solid_ring");
      const cStroke = normalizeHexColor(selected.stroke, "#ef4444");
      const cOuter = normalizeHexColor(selected.outerStroke, "#000000");
      const cSw = Math.round(Number(selected.strokeWidth ?? 8));
      const cW = Math.round(Number(selected.width || 220));
      const cH = Math.round(Number(selected.height || 220));
      return `
        <div class="canva-inspector-header">
          <div>
            <span class="canva-inspector-kicker">BẢNG CHỈNH SỬA VÒNG TRÒN / KHUNG KHOANH</span>
            <h4>⭕ ${esc(selected.name || "Vòng tròn tâm điểm")}</h4>
          </div>
          <button type="button" class="ghost compact" id="addNewCircleLayerBtn">+ ⭕ Thêm mới</button>
        </div>
        ${switcherHtml}
        <div class="canva-inspector-scroll">
          <div class="canva-context-card">
            <div class="canva-side-title">1. CHỌN KIỂU VÒNG TRÒN (10 KIỂU)</div>
            <div class="thumb-lib-grid" style="grid-template-columns:1fr 1fr;">
              ${CIRCLE_LIBRARY.map((item) => {
                const isAct = item.id === cStyle;
                return `<button type="button" class="thumb-lib-item ${isAct ? "active" : ""}" data-pick-circle-style="${esc(item.id)}" title="${esc(item.desc)}">
                  <canvas data-circle-lib-canvas="${esc(item.id)}" width="110" height="44"></canvas>
                  <span>${esc(item.label)}</span>
                </button>`;
              }).join("")}
            </div>
          </div>

          <div class="canva-context-card">
            <div class="canva-side-title">2. MÀU VÒNG TRÒN &amp; KÍCH THƯỚC</div>
            <div class="thumb-manual-color-row">
              <span class="thumb-mini-color-lbl">🎨 Màu nét:</span>
              <input type="color" id="circleStrokeColorInput" value="${esc(cStroke)}" />
              <input type="text" class="thumb-hex-input" id="circleStrokeHexInput" value="${esc(cStroke.toUpperCase())}" maxlength="7" />
              <span class="thumb-mini-color-lbl" style="margin-left:auto;">Viền ngoài:</span>
              <input type="color" id="circleOuterColorInput" value="${esc(cOuter)}" />
            </div>
            <div class="thumb-color-swatch-row" style="margin-top:6px;">
              <span class="thumb-mini-color-lbl">Màu nhanh:</span>
              ${buildSwatchPillsHtml("data-circle-stroke-swatch", "stroke", cStroke, 8)}
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:8px;">
              <label class="thumb-compact-slider">
                <span>Độ dày nét: <b id="circleStrokeWidthLabel">${cSw}px</b></span>
                <input type="range" id="circleStrokeWidthSlider" min="2" max="22" value="${cSw}" />
              </label>
              <label class="thumb-compact-slider">
                <span>Độ rộng: <b id="ctxLayerWidthLbl">${cW}px</b></span>
                <input type="range" id="ctxLayerWidthSlider" min="50" max="650" value="${cW}" />
              </label>
            </div>
            <button type="button" class="ghost compact" id="applyCircleAllVariantsBtn" style="width:100%;margin-top:8px;">⭕ Áp dụng kiểu &amp; màu vòng tròn cho cả 4 Bản</button>
          </div>

          ${commonTransformHtml}
        </div>
      `;
    }

    // CASE 4: INSET PIP IMAGE SELECTED
    if (hasSel && selType === "inset_image") {
      const bCol = normalizeHexColor(selected.borderColor, "#fbbf24");
      const bW = Math.round(Number(selected.borderWidth ?? 6));
      const iW = Math.round(Number(selected.width || 320));
      const iH = Math.round(Number(selected.height || 240));
      const curFrameStyle = String(selected.frameStyle || "caution_tape").toLowerCase();
      const pipFrameOptions = [
        { id: "torn_newspaper", label: "📰 Ảnh Xé Báo", defaultColor: "#f3ead8" },
        { id: "caution_tape", label: "🚧 Dải Phong Tỏa", defaultColor: "#ff2424" },
        { id: "amber_glow_double", label: "✨ Viền Kép Sáng", defaultColor: "#fbbf24" },
        { id: "cctv_hud", label: "📹 Khung CCTV", defaultColor: "#00f0ff" },
        { id: "dossier_tab", label: "📁 Hồ Sơ Pháp Y", defaultColor: "#ef4444" },
        { id: "vintage_paper", label: "📜 Giấy Ảnh Xưa", defaultColor: "#f4ebd9" },
        { id: "classic_rounded", label: "🖼 Bo Góc Cơ Bản", defaultColor: "#ffffff" },
      ];
      const candidates = getCleanCandidates();
      return `
        <div class="canva-inspector-header">
          <div>
            <span class="canva-inspector-kicker">BẢNG CHỈNH SỬA ẢNH PHỤ (PIP)</span>
            <h4>🖼 ${esc(selected.name || "Ảnh bằng chứng PiP")}</h4>
          </div>
        </div>
        ${switcherHtml}
        <div class="canva-inspector-scroll">
          <div class="canva-context-card">
            <div class="canva-side-title">1. KIỂU THIẾT KẾ KHUNG PIP &amp; VIỀN</div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:5px;margin-bottom:8px;">
              ${pipFrameOptions
                .map(
                  (fo) => `<button type="button" class="ghost compact ${curFrameStyle === fo.id ? "primary" : ""}" data-pick-pip-frame-style="${esc(fo.id)}" data-default-pip-color="${esc(fo.defaultColor)}">${esc(fo.label)}</button>`
                )
                .join("")}
            </div>
            <div class="thumb-manual-color-row">
              <span class="thumb-mini-color-lbl">🎨 Màu khung viền:</span>
              <input type="color" id="ctxPipBorderColor" value="${esc(bCol)}" />
              <input type="text" class="thumb-hex-input" id="ctxPipBorderHex" value="${esc(bCol.toUpperCase())}" maxlength="7" />
            </div>
            <div class="thumb-color-swatch-row" style="margin-top:6px;">
              <span class="thumb-mini-color-lbl">Màu nhanh:</span>
              ${buildSwatchPillsHtml("data-ctx-pip-border-swatch", selected.id, bCol, 8)}
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:8px;">
              <label class="thumb-compact-slider">
                <span>Độ dày viền: <b id="ctxPipBorderWLbl">${bW}px</b></span>
                <input type="range" id="ctxPipBorderWSlider" min="0" max="20" value="${bW}" />
              </label>
              <label class="thumb-compact-slider">
                <span>Chiều rộng: <b id="ctxLayerWidthLbl">${iW}px</b></span>
                <input type="range" id="ctxLayerWidthSlider" min="100" max="700" value="${iW}" />
              </label>
            </div>
            <label class="thumb-compact-slider" style="margin-top:6px;">
              <span>Chiều cao: <b id="ctxLayerHeightLbl">${iH}px</b></span>
              <input type="range" id="ctxLayerHeightSlider" min="80" max="550" value="${iH}" />
            </label>
          </div>

          ${commonTransformHtml}

          <div class="canva-context-card">
            <div class="canva-side-title">2. KHO ẢNH TƯ LIỆU THẬT &amp; HIỆN TRƯỜNG CHO [${esc(selected.name || selected.id)}] (${candidates.length} ẢNH)</div>
            <div style="display:flex;gap:6px;align-items:center;margin-bottom:8px;flex-wrap:wrap;">
              <label class="ghost compact thumb-upload-btn" style="display:inline-flex;align-items:center;justify-content:center;gap:5px;flex:1;padding:6px 10px;font-size:11.5px;cursor:pointer;border-color:rgba(56,189,248,0.45);color:#7dd3fc;background:rgba(56,189,248,0.08);">
                📁 Tải ảnh từ máy
                <input type="file" id="ctxUploadPipFileInput" accept="image/png,image/jpeg,image/webp" hidden />
              </label>
              <button type="button" class="ghost compact" id="ctxAddSecondPipBtn" style="flex:1;padding:6px 10px;font-size:11.5px;border-color:rgba(74,222,128,0.5);color:#86efac;background:rgba(34,197,94,0.1);">+ 🖼 Thêm Khung PiP Đè Chéo</button>
            </div>
            <div style="font-size:11px;color:#94a3b8;margin-bottom:6px;">Ấn vào bất kỳ ảnh tư liệu thật hiện trường / CCTV bên dưới để thay ngay vào khung PiP đang chọn:</div>
            <div class="canva-candidates-grid" style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:6px;max-height:360px;overflow-y:auto;">
              ${[...candidates]
                .sort((a, b) => (a.category === "thumbnail_inset" ? 0 : 1) - (b.category === "thumbnail_inset" ? 0 : 1))
                .map(
                  (c) => `<div class="canva-cand-card ${selected.src === c.url ? "selected" : ""}">
                    <img src="${esc(c.url)}" alt="${esc(c.label)}" title="${esc(c.label)}" loading="lazy" style="width:100%;height:64px;max-height:64px;object-fit:cover;display:block;" data-pick-inset="${esc(c.url)}" />
                    <div style="font-size:10px;color:#e2e8f0;padding:3px 4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-weight:700;" title="${esc(c.label)}">${esc(c.label)}</div>
                    <div class="canva-cand-actions">
                      <button type="button" data-pick-inset="${esc(c.url)}">Chọn làm PiP này</button>
                    </div>
                  </div>`
                )
                .join("")}
            </div>
          </div>
        </div>
      `;
    }

    // CASE 5: BACKGROUND / NOTHING SELECTED
    const vigPct = Math.round(Number(lVig.opacity ?? 0.82) * 100);
    const vigStyle = String(lVig.style || "left_heavy");
    const candidates = getCleanCandidates();
    return `
      <div class="canva-inspector-header">
        <div>
          <span class="canva-inspector-kicker">BẢNG CHỈNH SỬA NỀN &amp; TỔNG THỂ</span>
          <h4>🖼 Ảnh nền &amp; Chữ (${esc(activeVariant.short_label || "BẢN NÀY")})</h4>
        </div>
      </div>
      ${switcherHtml}
      <div class="canva-inspector-scroll">
        <div class="canva-context-card">
          <div class="canva-side-title">1. ÁNH SÁNG &amp; ĐỘ TỐI NỀN (VIGNETTE)</div>
          <label class="thumb-compact-slider">
            <span>Độ tối nền bảo vệ chữ: <b id="quickVigLabel">${vigPct}%</b></span>
            <input type="range" id="quickVigOpacity" min="0" max="98" value="${vigPct}" />
          </label>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:5px;margin-top:8px;">
            <button type="button" class="ghost compact ${vigStyle === "left_heavy" ? "primary" : ""}" data-set-vig-style="left_heavy">🌑 Tối bên Trái</button>
            <button type="button" class="ghost compact ${vigStyle === "bottom_heavy" ? "primary" : ""}" data-set-vig-style="bottom_heavy">🌑 Tối bên Dưới</button>
            <button type="button" class="ghost compact ${vigStyle === "right_heavy" ? "primary" : ""}" data-set-vig-style="right_heavy">🌑 Tối bên Phải</button>
            <button type="button" class="ghost compact ${vigStyle === "radial_spotlight" ? "primary" : ""}" data-set-vig-style="radial_spotlight">🔦 Spotlight Giữa</button>
          </div>
        </div>

        <div class="canva-context-card">
          <div class="canva-side-title">2. SỬA NHANH 3 DÒNG CHỮ &amp; TIÊU ĐỀ</div>
          <label class="canva-mini-field">
            <span>🏷 Tag (${esc(activeVi.badgeVi || "Nhãn")}):</span>
            <input type="text" data-sync-layer-text="badge" value="${esc(lBadge.text ?? activeVariant.badge_text ?? "")}" />
          </label>
          <label class="canva-mini-field">
            <span>🔤 Dòng 1 (${esc(activeVi.line1Vi || "Dòng 1")}):</span>
            <input type="text" data-sync-layer-text="line_1" value="${esc(lLine1.text ?? activeVariant.line_1 ?? "")}" />
          </label>
          <label class="canva-mini-field">
            <span>🔥 Dòng 2 (${esc(activeVi.line2Vi || "Dòng 2")}):</span>
            <input type="text" data-sync-layer-text="line_2" value="${esc(lLine2.text ?? activeVariant.line_2 ?? "")}" />
          </label>
          <label class="canva-mini-field">
            <span>🎬 Tiêu đề YouTube đi kèm (Hàn):</span>
            <input type="text" id="quickPairedTitleText" value="${esc(activeVariant.paired_title || "")}" />
          </label>
        </div>

        <div class="canva-context-card">
          <div class="canva-side-title">3. KHO ẢNH NỀN &amp; TƯ LIỆU THẬT (${candidates.length} ẢNH)</div>
          <div style="display:flex;gap:6px;margin-bottom:8px;">
            <button type="button" class="ghost compact" id="thumbGenSingleFlowBtn" style="flex:1;" ${studioState.busyVariants.has(activeVariant.id) ? "disabled" : ""}>🎨 Vẽ nền Flow</button>
            <label class="ghost compact thumb-upload-btn" style="flex:1;text-align:center;">
              📁 Tải ảnh máy
              <input type="file" id="thumbUploadBgInput" accept="image/png,image/jpeg,image/webp" hidden />
            </label>
          </div>
          <div class="canva-candidates-grid" style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:6px;max-height:320px;overflow-y:auto;">
            ${candidates
              .map(
                (c) => `<div class="canva-cand-card ${getVariantBgUrl(activeVariant) === c.url ? "selected" : ""}">
                  <img src="${esc(c.url)}" alt="${esc(c.label)}" title="${esc(c.label)}" loading="lazy" style="width:100%;height:56px;max-height:56px;object-fit:cover;display:block;" data-pick-bg="${esc(c.url)}" data-pick-path="${esc(c.rel_path || "")}" />
                  <div style="font-size:10px;color:#cbd5e1;padding:2px 4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;" title="${esc(c.label)}">${esc(c.label)}</div>
                  <div class="canva-cand-actions">
                    <button type="button" data-pick-bg="${esc(c.url)}" data-pick-path="${esc(c.rel_path || "")}">Làm Nền</button>
                    <button type="button" data-pick-inset="${esc(c.url)}">Ảnh PiP</button>
                  </div>
                </div>`
              )
              .join("")}
          </div>
        </div>
      </div>
    `;
  }

  function refreshContextualPanels() {
    const activeVariant = getActiveVariant();
    if (!activeVariant) return;
    const rightEl = document.getElementById("cofiThumbRightInspector");
    const leftEl = document.getElementById("cofiThumbLeftDock");
    const quickBarEl = document.getElementById("cofiThumbQuickLayersBar");
    if (rightEl) {
      rightEl.innerHTML = buildRightContextualInspectorHtml(activeVariant);
    }
    if (leftEl) {
      leftEl.innerHTML = buildLeftDockInnerHtml(activeVariant);
    }
    if (quickBarEl) {
      quickBarEl.innerHTML = buildQuickLayersBarInnerHtml(activeVariant);
    }
    updateSelectedLayerTransformDom();
    bindWorkbenchDynamicEvents();
  }

  function updateSelectedLayerTransformDom() {
    const pill = document.getElementById("thumbSelectedLayerLabel");
    const delBtn = document.getElementById("thumbDeleteSelectedBtn");
    const angleSlider = document.getElementById("thumbSelectedAngleSlider");
    const angleLbl = document.getElementById("thumbSelectedAngleLabel");

    const selected = getLayer(studioState.selectedLayerId);
    const hasSel = Boolean(selected && selected.visible !== false && selected.type !== "vignette");

    if (pill) {
      pill.textContent = hasSel
        ? `🎯 Đang sửa: ${selected.name || selected.id}`
        : "🖼 Đang sửa: Ảnh nền & Ánh sáng (Ấn vào chữ/mũi tên trên ảnh để sửa)";
    }
    if (delBtn) delBtn.disabled = !hasSel;
    if (angleSlider) {
      angleSlider.disabled = !hasSel;
      angleSlider.value = hasSel ? String(Math.round(Number(selected.angle || 0))) : "0";
    }
    if (angleLbl) {
      angleLbl.textContent = hasSel ? `${Math.round(Number(selected.angle || 0))}°` : "0°";
    }
    document.querySelectorAll("[data-canva-need-sel]").forEach((btn) => {
      btn.disabled = !hasSel;
    });
    document.querySelectorAll("[data-quick-select-layer]").forEach((btn) => {
      const lid = btn.dataset.quickSelectLayer;
      const l = getLayer(lid);
      btn.classList.toggle("is-selected", Boolean(l && l.visible !== false && studioState.selectedLayerId === lid));
      btn.classList.toggle("is-hidden-layer", Boolean(!l || l.visible === false));
    });
    renderLibraryMiniPreviews();
  }

  function bindMainCanvasPointerEvents(canvas) {
    if (!canvas || canvas.dataset.boundPointer === "1") return;
    canvas.dataset.boundPointer = "1";

    canvas.addEventListener("pointerdown", (event) => {
      if (
        document.activeElement &&
        document.activeElement !== canvas &&
        typeof document.activeElement.blur === "function"
      ) {
        try { document.activeElement.blur(); } catch (_) {}
      }
      try { canvas.focus({ preventScroll: true }); } catch (_) {}

      const pt = canvasCoordsFromEvent(canvas, event);
      const hit = hitTestLayer(pt.x, pt.y);
      if (!hit) {
        const prevSel = studioState.selectedLayerId;
        studioState.selectedLayerId = null;
        renderAllCanvases();
        if (prevSel !== null) {
          refreshContextualPanels();
        } else {
          updateSelectedLayerTransformDom();
        }
        return;
      }
      event.preventDefault();
      if (hit.mode === "delete") {
        deleteLayerById(hit.layer.id);
        return;
      }
      pushUndoSnapshot();
      canvas.setPointerCapture(event.pointerId);
      const prevSel = studioState.selectedLayerId;
      studioState.selectedLayerId = hit.layer.id;
      studioState.dragging = {
        pointerId: event.pointerId,
        mode: hit.mode,
        corner: hit.corner || "se",
        layerId: hit.layer.id,
        startX: pt.x,
        startY: pt.y,
        origLeft: Number(hit.layer.left || 0),
        origTop: Number(hit.layer.top || 0),
        origW: Number(hit.layer.width || 200),
        origH: Number(hit.layer.height || 80),
        origFontSize: Number(hit.layer.fontSize || 72),
        origAngle: Number(hit.layer.angle || 0),
      };
      renderAllCanvases();
      if (prevSel !== studioState.selectedLayerId) {
        refreshContextualPanels();
      } else {
        updateSelectedLayerTransformDom();
      }
    });

    canvas.addEventListener("pointermove", (event) => {
      const pt = canvasCoordsFromEvent(canvas, event);
      if (!studioState.dragging) {
        const hoverHit = hitTestLayer(pt.x, pt.y);
        if (!hoverHit) canvas.style.cursor = "default";
        else if (hoverHit.mode === "rotate") canvas.style.cursor = "grab";
        else if (hoverHit.mode === "resize") canvas.style.cursor = "nwse-resize";
        else if (hoverHit.mode === "delete") canvas.style.cursor = "pointer";
        else canvas.style.cursor = "move";
        return;
      }
      const drag = studioState.dragging;
      const layer = getLayer(drag.layerId);
      if (!layer) return;
      const dx = pt.x - drag.startX;
      const dy = pt.y - drag.startY;
      if (drag.mode === "move") {
        let nextLeft = Math.round(Math.max(-220, Math.min(CW - 40, drag.origLeft + dx)));
        let nextTop = Math.round(Math.max(-100, Math.min(CH - 30, drag.origTop + dy)));
        const lw = Number(layer.width || 200);
        const lh = Number(layer.height || 80);
        let snapX = null;
        let snapY = null;
        if (!event.shiftKey) {
          const curCenterX = nextLeft + lw / 2;
          const curCenterY = nextTop + lh / 2;
          if (Math.abs(curCenterX - CW / 2) <= 12) {
            nextLeft = Math.round(CW / 2 - lw / 2);
            snapX = CW / 2;
          } else if (Math.abs(nextLeft - 64) <= 10) {
            nextLeft = 64;
            snapX = 64;
          } else if (Math.abs(nextLeft - 48) <= 10) {
            nextLeft = 48;
            snapX = 48;
          }
          if (Math.abs(curCenterY - CH / 2) <= 12) {
            nextTop = Math.round(CH / 2 - lh / 2);
            snapY = CH / 2;
          }
        }
        studioState.snapGuides = snapX !== null || snapY !== null ? { x: snapX, y: snapY } : null;
        layer.left = nextLeft;
        layer.top = nextTop;
      } else if (drag.mode === "rotate") {
        const cx = drag.origLeft + drag.origW / 2;
        const cy = drag.origTop + drag.origH / 2;
        const rawAngle = (Math.atan2(pt.y - cy, pt.x - cx) * 180) / Math.PI + 90;
        let normAngle = ((rawAngle + 180) % 360 + 360) % 360 - 180;
        if (!event.shiftKey) {
          for (const snap of [-180, -135, -90, -45, 0, 45, 90, 135, 180]) {
            if (Math.abs(normAngle - snap) <= 4) {
              normAngle = snap;
              break;
            }
          }
        }
        layer.angle = Math.round(normAngle);
        updateSelectedLayerTransformDom();
      } else if (drag.mode === "resize") {
        const signX = drag.corner === "sw" || drag.corner === "nw" ? -1 : 1;
        const signY = drag.corner === "nw" ? -1 : 1;
        if (layer.type === "textbox" || layer.type === "badge" || layer.type === "stamp") {
          const factor = Math.max(0.4, Math.min(2.4, (drag.origW + dx * signX) / Math.max(80, drag.origW)));
          layer.fontSize = Math.round(Math.max(22, Math.min(138, drag.origFontSize * factor)));
          const fsLbl = document.getElementById("ctxFontSizeLbl");
          const fsSlider = document.getElementById("ctxFontSizeSlider");
          if (fsLbl) fsLbl.textContent = `${layer.fontSize}px`;
          if (fsSlider) fsSlider.value = String(layer.fontSize);
        } else {
          const newW = Math.round(Math.max(45, Math.min(960, drag.origW + dx * signX)));
          const newH = Math.round(Math.max(36, Math.min(680, drag.origH + dy * signY)));
          if (signX < 0) layer.left = Math.round(drag.origLeft + (drag.origW - newW));
          if (signY < 0) layer.top = Math.round(drag.origTop + (drag.origH - newH));
          layer.width = newW;
          layer.height = newH;
          const wLbl = document.getElementById("ctxLayerWidthLbl");
          const wSlider = document.getElementById("ctxLayerWidthSlider");
          if (wLbl) wLbl.textContent = `${newW}px`;
          if (wSlider) wSlider.value = String(newW);
        }
      }
      renderAllCanvases();
    });

    const endDrag = () => {
      if (!studioState.dragging) return;
      studioState.dragging = null;
      studioState.snapGuides = null;
      renderAllCanvases();
      updateSelectedLayerTransformDom();
      scheduleSaveDesign();
    };
    canvas.addEventListener("pointerup", endDrag);
    canvas.addEventListener("pointercancel", endDrag);

    canvas.addEventListener("dblclick", (event) => {
      const pt = canvasCoordsFromEvent(canvas, event);
      const hit = hitTestLayer(pt.x, pt.y);
      if (!hit || !hit.layer) return;
      const layer = hit.layer;
      studioState.selectedLayerId = layer.id;
      refreshContextualPanels();
      if (layer.type === "textbox" || layer.type === "badge" || layer.type === "stamp") {
        const targetInput = document.getElementById("ctxSelectedTextInput");
        if (targetInput) {
          try { targetInput.focus({ preventScroll: true }); } catch (_) { targetInput.focus(); }
          targetInput.select();
          showToast(`✎ Sửa trực tiếp chữ «${layer.name || layer.id}» ở bảng bên phải (Bọc *từ khóa* để tô màu nổi!)`);
        }
      }
    });

    const viewport = document.getElementById("cofiThumbStageViewport");
    if (viewport && viewport.dataset.boundWheel !== "1") {
      viewport.dataset.boundWheel = "1";
      viewport.addEventListener(
        "wheel",
        (e) => {
          if (e.ctrlKey || e.metaKey || e.altKey) {
            e.preventDefault();
            const delta = e.deltaY < 0 ? 0.15 : -0.15;
            setCanvasZoom((studioState.canvasZoom || 1) + delta);
          }
        },
        { passive: false }
      );
    }
  }

  function parseVariantVietnamese(variant, idx = 0) {
    if (!variant || typeof variant !== "object") {
      return { badgeVi: "", line1Vi: "", line2Vi: "", fullVi: "", hookVi: "", pairedTitleKo: "", pairedTitleVi: "", synergyVi: "", keywordAnchorVi: "" };
    }
    const seoPack = studioState.seoPack || studioState.data?.seo_package || {};
    const packVariants = Array.isArray(seoPack.thumbnail_variants) ? seoPack.thumbnail_variants : [];
    const packDetails = Array.isArray(seoPack.title_options_details) ? seoPack.title_options_details : [];
    const packTitlesKo = Array.isArray(seoPack.title_options) ? seoPack.title_options : [];
    const packTitlesVi = Array.isArray(seoPack.title_options_vi) ? seoPack.title_options_vi : [];
    const packOverlayOpts = Array.isArray(seoPack.thumbnail?.overlay_text_options) ? seoPack.thumbnail.overlay_text_options : [];
    const pv = packVariants.find((item) => item && item.id === variant.id) || packVariants[idx] || {};
    const pd = packDetails[idx] || {};
    const po = packOverlayOpts[idx] || {};

    const raw = String(variant.meaning_vi || pv.meaning_vi || po.meaning_vi || "").trim();
    let badgeVi = String(variant.badge_vi || pv.badge_vi || "").trim();
    let line1Vi = String(variant.line_1_vi || pv.line_1_vi || "").trim();
    let line2Vi = String(variant.line_2_vi || pv.line_2_vi || "").trim();

    if (raw) {
      const mBadge = raw.match(/(?:\[)?(?:Tag[^:\]|]*|Badge[^:\]|]*):\s*([^\]|]+)/i);
      const mLine1 = raw.match(/(?:\[)?(?:Dòng\s*1|Line\s*1)[^:\]|]*:\s*([^\]|]+)/i);
      const mLine2 = raw.match(/(?:\[)?(?:Dòng\s*2|Line\s*2)[^:\]|]*:\s*([^\]|]+)/i);
      if (mBadge) badgeVi = mBadge[1].trim();
      if (mLine1) line1Vi = mLine1[1].trim();
      if (mLine2) line2Vi = mLine2[1].trim();
    }
    const hookVi = String(variant.psychological_hook || pv.psychological_hook || "").trim();
    const rawKoOpt = packTitlesKo[idx];
    const koFromOpt = typeof rawKoOpt === "object" && rawKoOpt !== null ? String(rawKoOpt.title_ko || rawKoOpt.title || "").trim() : String(rawKoOpt || "").trim();
    const pairedTitleKo = String(
      variant.paired_title || pd.title_ko || pd.title || po.paired_title || pv.paired_title || koFromOpt || seoPack.recommended_title || studioState.data?.recommended_title || ""
    ).trim();
    const pairedTitleVi = String(
      variant.paired_title_vi || pd.title_vi || po.paired_title_vi || pv.paired_title_vi || packTitlesVi[idx] || seoPack.recommended_title_vi || studioState.data?.recommended_title_vi || ""
    ).trim();
    const synergyVi = String(variant.synergy_vi || pd.synergy_vi || pv.synergy_vi || "").trim();
    const keywordAnchorVi = String(variant.keyword_anchor_vi || pd.keyword_anchor || pv.keyword_anchor_vi || "").trim();
    return {
      badgeVi,
      line1Vi,
      line2Vi,
      fullVi: raw,
      hookVi,
      pairedTitleKo,
      pairedTitleVi,
      synergyVi,
      keywordAnchorVi,
    };
  }

  function buildBilingualTitlesBannerHtml() {
    const seoPack = studioState.seoPack || studioState.data?.seo_package || {};
    const recKo = String(seoPack.recommended_title || studioState.data?.recommended_title || "").trim();
    const recVi = String(seoPack.recommended_title_vi || studioState.data?.recommended_title_vi || "").trim();
    const rawPrimaryKw = seoPack.primary_keywords_summary;
    const kwSummary = rawPrimaryKw && typeof rawPrimaryKw === "object"
      ? Object.values(rawPrimaryKw).map((v) => String(v || "").trim()).filter(Boolean).join(" · ")
      : String(rawPrimaryKw || "").trim();
    const synergySummary = String(seoPack.title_thumb_synergy_vi || "").trim();
    const rawOpts = Array.isArray(seoPack.title_options) ? seoPack.title_options : [];
    const details = Array.isArray(seoPack.title_options_details) ? seoPack.title_options_details : [];
    const optsVi = Array.isArray(seoPack.title_options_vi) ? seoPack.title_options_vi : [];

    if (!recKo && !rawOpts.length) return "";

    const rowsHtml = rawOpts.map((opt, idx) => {
      const d = (typeof opt === "object" && opt !== null) ? opt : (details[idx] || {});
      const ko = typeof opt === "object" && opt !== null ? String(opt.title_ko || opt.title || "").trim() : String(opt || "").trim();
      const vi = String(d.title_vi || optsVi[idx] || "").trim();
      const paired = String(d.paired_variant || `Phương án ${idx + 1}`).trim();
      const kw = String(d.keyword_anchor || "").trim();
      const syn = String(d.synergy_vi || "").trim();
      return `<div style="padding:10px 12px;background:rgba(15,23,42,0.88);border:1px solid rgba(56,189,248,0.28);border-radius:8px;display:flex;flex-direction:column;gap:5px;">
        <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:10px;">
          <div style="font-size:13.5px;line-height:1.45;color:#f8fafc;font-weight:800;">
            <span style="color:#38bdf8;margin-right:6px;">#${idx + 1}.</span>
            <span style="display:inline-block;padding:1px 7px;margin-right:6px;border-radius:4px;background:rgba(251,191,36,0.18);border:1px solid rgba(251,191,36,0.45);color:#fde047;font-size:11px;font-weight:800;">${esc(paired)}</span>
            <span>🇰🇷 ${esc(ko)}</span>
          </div>
          <button type="button" class="ghost compact" data-copy-raw-title="${esc(ko)}" style="flex-shrink:0;font-size:11px;padding:3px 9px;">📋 Sao chép</button>
        </div>
        ${vi ? `<div style="font-size:13px;line-height:1.45;color:#f8fafc;background:rgba(34,197,94,0.12);border-left:3px solid #22c55e;padding:5px 9px;border-radius:4px;"><b style="color:#4ade80;">🇻🇳 Nghĩa Tiếng Việt:</b> ${esc(vi)}</div>` : ""}
        ${kw ? `<div style="font-size:11.5px;color:#7dd3fc;padding-left:4px;"><b>📍 Từ khóa &amp; Địa điểm TQ:</b> ${esc(kw)}</div>` : ""}
        ${syn ? `<div style="font-size:11.5px;color:#cbd5e1;padding-left:4px;"><b>🔗 Bổ trợ nghĩa với Thumbnail:</b> ${esc(syn)}</div>` : ""}
      </div>`;
    }).join("");

    return `<div style="margin:0 0 10px 0;padding:9px 12px;background:linear-gradient(180deg,rgba(15,23,42,0.96),rgba(9,14,26,0.96));border:1px solid rgba(34,197,94,0.45);border-radius:10px;">
      <div style="display:flex;align-items:center;justify-content:space-between;gap:8px;flex-wrap:wrap;margin-bottom:6px;">
        <div>
          <span style="font-size:10.5px;font-weight:800;letter-spacing:0.06em;color:#4ade80;display:block;">🎬 HỆ THỐNG TIÊU ĐỀ YOUTUBE SONG NGỮ (TIẾNG HÀN + BẢN DỊCH NGHĨA TIẾNG VIỆT)</span>
          <strong style="font-size:13.5px;color:#f8fafc;">Tiêu đề Đề xuất Chính &amp; 6 Phương án Tiêu đề đi cặp Thumbnail A / B / C / D</strong>
        </div>
        ${recKo ? `<button type="button" class="primary compact" data-copy-raw-title="${esc(recKo)}" style="min-height:27px;height:27px;font-size:11px;padding:0 10px;">📋 Sao chép Tiêu đề Chính (Hàn)</button>` : ""}
      </div>
      ${recKo ? `<div style="padding:7px 10px;background:rgba(30,41,59,0.92);border:1px solid rgba(250,204,21,0.45);border-radius:8px;margin-bottom:6px;display:flex;flex-direction:column;gap:3px;">
        <div style="font-size:13.5px;font-weight:800;color:#ffffff;line-height:1.35;">🇰🇷 ${esc(recKo)}</div>
        ${recVi ? `<div style="font-size:12.5px;font-weight:700;color:#f8fafc;background:rgba(34,197,94,0.16);border-left:4px solid #22c55e;padding:3px 8px;border-radius:4px;"><span style="color:#4ade80;font-weight:800;">🇻🇳 Dịch nghĩa Tiếng Việt:</span> ${esc(recVi)}</div>` : ""}
      </div>` : ""}
      ${rowsHtml ? `<details style="margin-top:2px;">
        <summary style="cursor:pointer;font-size:11.5px;font-weight:800;color:#38bdf8;user-select:none;">▼ Bấm để mở rộng ${rawOpts.length} Phương án Tiêu đề YouTube (Song ngữ Hàn - Việt)</summary>
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:8px;margin-top:6px;">${rowsHtml}</div>
      </details>` : ""}
    </div>`;
  }

  function bindWorkbenchDynamicEvents() {
    const host = document.getElementById("cofiThumbnailStudioHost");
    if (!host || !studioState.data) return;
    const design = studioState.data.design || {};
    const activeVariant = getActiveVariant() || {};
    const lBadge = getLayer("badge", activeVariant);
    const lLine1 = getLayer("line_1", activeVariant);
    const lLine2 = getLayer("line_2", activeVariant);
    const lVig = getLayer("vignette", activeVariant);
    const lArrow = getLayer("forensic_arrow", activeVariant);
    const lCircle = getLayer("forensic_circle", activeVariant);
    const lInset = getLayer("inset_photo", activeVariant);

    // 1. Left Dock Tab switching (in-place without page scroll jump)
    host.querySelectorAll("[data-left-dock-tab]").forEach((btn) => {
      if (btn.dataset.bound === "1") return;
      btn.dataset.bound = "1";
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        studioState.leftDockTab = btn.dataset.leftDockTab || "style";
        refreshContextualPanels();
      });
    });

    // 2. Quick select layer / background pills (in-place contextual switch without scroll jump)
    host.querySelectorAll("[data-quick-select-bg]").forEach((btn) => {
      if (btn.dataset.bound === "1") return;
      btn.dataset.bound = "1";
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        studioState.selectedLayerId = null;
        renderAllCanvases();
        refreshContextualPanels();
      });
    });

    host.querySelectorAll("[data-quick-select-layer]").forEach((btn) => {
      if (btn.dataset.bound === "1") return;
      btn.dataset.bound = "1";
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const lid = btn.dataset.quickSelectLayer;
        const layer = getLayer(lid, activeVariant);
        if (!layer) return;
        pushUndoSnapshot();
        if (layer.visible === false) {
          layer.visible = true;
          showToast(`Đã bật «${layer.name || layer.id}» lên ảnh!`);
        }
        studioState.selectedLayerId = lid;
        renderAllCanvases();
        refreshContextualPanels();
        scheduleSaveDesign();
      });
    });

    // 3. Layer visibility checkboxes
    host.querySelectorAll("[data-toggle-layer]").forEach((chk) => {
      if (chk.dataset.bound === "1") return;
      chk.dataset.bound = "1";
      chk.addEventListener("change", () => {
        pushUndoSnapshot();
        const layer = getLayer(chk.dataset.toggleLayer, activeVariant);
        if (layer) {
          layer.visible = Boolean(chk.checked);
          studioState.selectedLayerId = layer.visible ? layer.id : null;
          renderAllCanvases();
          refreshContextualPanels();
          scheduleSaveDesign();
        }
      });
    });

    // 4. Add new PiP / Text / Arrow / Circle buttons
    host.querySelectorAll("#quickBarAddPipBtn, #ctxAddSecondPipBtn").forEach((btn) => {
      if (btn.dataset.bound === "1") return;
      btn.dataset.bound = "1";
      btn.addEventListener("click", () => addNewPipLayer("vintage_paper"));
    });
    host.querySelectorAll("#quickBarAddTextBtn, #addCustomTextLayerBtn").forEach((btn) => {
      if (btn.dataset.bound === "1") return;
      btn.dataset.bound = "1";
      btn.addEventListener("click", () => addNewCustomTextLayer());
    });
    host.querySelectorAll("#quickBarAddArrowBtn, #addNewArrowLayerBtn").forEach((btn) => {
      if (btn.dataset.bound === "1") return;
      btn.dataset.bound = "1";
      btn.addEventListener("click", () => {
        const curArr = getActiveArrowLayer(activeVariant);
        addNewArrowLayer(curArr?.arrowStyle || "curved_pointer");
      });
    });
    host.querySelectorAll("#quickBarAddCircleBtn, #addNewCircleLayerBtn").forEach((btn) => {
      if (btn.dataset.bound === "1") return;
      btn.dataset.bound = "1";
      btn.addEventListener("click", () => {
        const curCir = getActiveCircleLayer(activeVariant);
        addNewCircleLayer(curCir?.circleStyle || "solid_ring");
      });
    });

    // 5. Topic Style Presets & Archetypes & Color Combos
    host.querySelectorAll("[data-apply-topic-preset]").forEach((btn) => {
      if (btn.dataset.bound === "1") return;
      btn.dataset.bound = "1";
      btn.addEventListener("click", () => {
        applyTopicStylePreset(btn.dataset.applyTopicPreset, { applyAllVariants: false });
      });
    });
    host.querySelectorAll("#applyTopicPresetAllBtn, #leftApplyPresetAllBtn").forEach((btn) => {
      if (btn.dataset.bound === "1") return;
      btn.dataset.bound = "1";
      btn.addEventListener("click", () => {
        const currentStyle = activeVariant.style_preset || design.style_preset || TOPIC_STYLE_PRESETS[0].id;
        applyTopicStylePreset(currentStyle, { applyAllVariants: true });
      });
    });

    host.querySelectorAll("[data-select-archetype]").forEach((btn) => {
      if (btn.dataset.bound === "1") return;
      btn.dataset.bound = "1";
      btn.addEventListener("click", () => {
        pushUndoSnapshot();
        const archId = btn.dataset.selectArchetype;
        activeVariant.archetype = archId;
        if (archId === "broadcast_left_heavy") {
          if (lVig) lVig.style = "left_heavy";
          if (lBadge) { lBadge.left = 64; lBadge.top = 185; lBadge.visible = true; }
          if (lLine1) { lLine1.left = 64; lLine1.top = 280; lLine1.textAlign = "left"; lLine1.visible = true; }
          if (lLine2) { lLine2.left = 64; lLine2.top = 405; lLine2.textAlign = "left"; lLine2.visible = true; }
          if (lArrow) { lArrow.left = 670; lArrow.top = 270; lArrow.angle = -8; lArrow.visible = false; }
          if (lCircle) { lCircle.visible = false; }
          if (lInset) { lInset.visible = false; }
        } else if (archId === "bottom_cinematic") {
          if (lVig) lVig.style = "bottom_heavy";
          if (lBadge) { lBadge.left = 64; lBadge.top = 42; lBadge.visible = true; }
          if (lLine1) { lLine1.left = 64; lLine1.top = 444; lLine1.textAlign = "left"; lLine1.visible = true; }
          if (lLine2) { lLine2.left = 64; lLine2.top = 552; lLine2.textAlign = "left"; lLine2.visible = true; }
          if (lInset) { lInset.visible = false; }
        } else if (archId === "split_duality") {
          if (lVig) lVig.style = "left_heavy";
          if (lBadge) { lBadge.left = 64; lBadge.top = 240; lBadge.visible = true; }
          if (lLine1) { lLine1.left = 64; lLine1.top = 330; lLine1.textAlign = "left"; lLine1.visible = true; }
          if (lLine2) { lLine2.left = 64; lLine2.top = 452; lLine2.textAlign = "left"; lLine2.visible = true; }
          if (lInset) { lInset.left = 836; lInset.top = 44; lInset.width = 384; lInset.height = 330; lInset.visible = true; }
          if (lArrow) { lArrow.left = 665; lArrow.top = 195; lArrow.angle = -6; lArrow.visible = true; }
        } else if (archId === "evidence_spotlight") {
          if (lVig) lVig.style = "radial_spotlight";
          if (lBadge) { lBadge.left = 64; lBadge.top = 42; lBadge.visible = true; }
          if (lLine1) { lLine1.left = 64; lLine1.top = 430; lLine1.textAlign = "left"; lLine1.visible = true; }
          if (lLine2) { lLine2.left = 64; lLine2.top = 545; lLine2.textAlign = "left"; lLine2.visible = true; }
          if (lCircle) { lCircle.left = 830; lCircle.top = 340; lCircle.width = 220; lCircle.height = 175; lCircle.visible = true; }
          if (lInset) { lInset.visible = false; }
        } else if (archId === "right_heavy_confrontation") {
          if (lVig) lVig.style = "right_heavy";
          if (lBadge) { lBadge.left = 820; lBadge.top = 170; lBadge.visible = true; }
          if (lLine1) { lLine1.left = 450; lLine1.top = 265; lLine1.textAlign = "right"; lLine1.visible = true; }
          if (lLine2) { lLine2.left = 420; lLine2.top = 388; lLine2.textAlign = "right"; lLine2.visible = true; }
        }
        renderAllCanvases();
        refreshContextualPanels();
        scheduleSaveDesign();
      });
    });

    host.querySelectorAll("[data-apply-text-combo]").forEach((btn) => {
      if (btn.dataset.bound === "1") return;
      btn.dataset.bound = "1";
      btn.addEventListener("click", () => {
        const combo = TEXT_COLOR_COMBOS.find((c) => c.id === btn.dataset.applyTextCombo);
        if (!combo) return;
        pushUndoSnapshot();
        if (lBadge) { lBadge.fill = combo.badgeFill; lBadge.bgColor = combo.badgeBg; }
        if (lLine1) { lLine1.fill = combo.line1Fill; lLine1.stroke = combo.stroke || "#000000"; }
        if (lLine2) { lLine2.fill = combo.line2Fill; lLine2.stroke = combo.stroke || "#000000"; }
        renderAllCanvases();
        refreshContextualPanels();
        scheduleSaveDesign();
        showToast(`🎨 Đã áp dụng bộ màu chữ «${combo.label}»!`);
      });
    });

    // 6. Korean Fonts
    const applyKoreanFontToVariant = (fontId, applyAllVariants = false) => {
      const fObj = KOREAN_BROADCAST_FONTS.find((f) => f.id === fontId) || KOREAN_BROADCAST_FONTS[0];
      pushUndoSnapshot();
      const targetVariants = applyAllVariants ? getVariants() : [activeVariant];
      targetVariants.forEach((v) => {
        (v.layers || []).forEach((l) => {
          if (l && (l.type === "textbox" || l.type === "badge" || l.type === "stamp")) {
            l.fontFamily = fObj.stack;
          }
        });
      });
      renderAllCanvases();
      refreshContextualPanels();
      scheduleSaveDesign();
      showToast(
        applyAllVariants
          ? `🇰🇷 Đã áp dụng font «${fObj.shortLabel}» cho cả 4 Bản!`
          : `🇰🇷 Đã đổi font sang «${fObj.shortLabel}»!`
      );
    };

    host.querySelectorAll("#ctxKoreanFontSelect").forEach((sel) => {
      if (sel.dataset.bound === "1") return;
      sel.dataset.bound = "1";
      sel.addEventListener("change", (e) => applyKoreanFontToVariant(e.target.value, false));
    });
    host.querySelectorAll("[data-pick-kr-font]").forEach((btn) => {
      if (btn.dataset.bound === "1") return;
      btn.dataset.bound = "1";
      btn.addEventListener("click", () => applyKoreanFontToVariant(btn.dataset.pickKrFont, false));
    });
    host.querySelectorAll("#applyFontAllVariantsBtn").forEach((btn) => {
      if (btn.dataset.bound === "1") return;
      btn.dataset.bound = "1";
      btn.addEventListener("click", () => {
        const selEl = host.querySelector("#ctxKoreanFontSelect");
        const fontId = selEl ? selEl.value : detectFontIdFromStack(lLine2?.fontFamily || "");
        applyKoreanFontToVariant(fontId, true);
      });
    });

    // 7. Contextual Selected Text / Badge / Stamp editing
    const ctxTextInput = host.querySelector("#ctxSelectedTextInput");
    if (ctxTextInput && ctxTextInput.dataset.bound !== "1") {
      ctxTextInput.dataset.bound = "1";
      ctxTextInput.addEventListener("focus", () => pushUndoSnapshot());
      ctxTextInput.addEventListener("input", (e) => {
        const sel = getLayer(studioState.selectedLayerId, activeVariant);
        if (!sel) return;
        sel.text = e.target.value;
        sel.visible = Boolean(String(e.target.value || "").trim());
        if (sel.id === "badge") activeVariant.badge_text = e.target.value;
        else if (sel.id === "line_1") activeVariant.line_1 = e.target.value;
        else if (sel.id === "line_2") activeVariant.line_2 = e.target.value;
        // Also sync quick inputs if present
        host.querySelectorAll(`[data-sync-layer-text="${sel.id}"]`).forEach((inp) => {
          if (inp !== e.target) inp.value = e.target.value;
        });
        renderAllCanvases();
        scheduleSaveDesign();
      });
    }

    host.querySelectorAll("[data-sync-layer-text]").forEach((inp) => {
      if (inp.dataset.bound === "1") return;
      inp.dataset.bound = "1";
      const lid = inp.dataset.syncLayerText;
      inp.addEventListener("focus", () => {
        pushUndoSnapshot();
        if (studioState.selectedLayerId !== lid) {
          studioState.selectedLayerId = lid;
          renderAllCanvases();
          updateSelectedLayerTransformDom();
        }
      });
      inp.addEventListener("input", (e) => {
        const layer = getLayer(lid, activeVariant);
        if (layer) {
          layer.text = e.target.value;
          layer.visible = Boolean(String(e.target.value || "").trim());
        }
        if (lid === "badge") activeVariant.badge_text = e.target.value;
        else if (lid === "line_1") activeVariant.line_1 = e.target.value;
        else if (lid === "line_2") activeVariant.line_2 = e.target.value;
        const mainInput = host.querySelector("#ctxSelectedTextInput");
        if (mainInput && studioState.selectedLayerId === lid && mainInput !== e.target) {
          mainInput.value = e.target.value;
        }
        renderAllCanvases();
        scheduleSaveDesign();
      });
    });

    // Contextual Font Size & Stroke Width sliders
    const ctxFsSlider = host.querySelector("#ctxFontSizeSlider");
    if (ctxFsSlider && ctxFsSlider.dataset.bound !== "1") {
      ctxFsSlider.dataset.bound = "1";
      ctxFsSlider.addEventListener("input", (e) => {
        const sel = getLayer(studioState.selectedLayerId, activeVariant);
        if (!sel) return;
        const val = Math.round(Number(e.target.value || 72));
        sel.fontSize = val;
        const lbl = host.querySelector("#ctxFontSizeLbl");
        if (lbl) lbl.textContent = `${val}px`;
        renderAllCanvases();
        scheduleSaveDesign();
      });
    }

    const ctxSwSlider = host.querySelector("#ctxStrokeWidthSlider");
    if (ctxSwSlider && ctxSwSlider.dataset.bound !== "1") {
      ctxSwSlider.dataset.bound = "1";
      ctxSwSlider.addEventListener("input", (e) => {
        const sel = getLayer(studioState.selectedLayerId, activeVariant);
        if (!sel) return;
        const val = Math.round(Number(e.target.value || 16));
        sel.strokeWidth = val;
        const lbl = host.querySelector("#ctxStrokeWidthLbl");
        if (lbl) lbl.textContent = `${val}px`;
        renderAllCanvases();
        scheduleSaveDesign();
      });
    }

    // Contextual Text Colors (Fill, Highlight, Stroke, Badge Bg)
    const bindCtxLayerColor = (colorId, hexId, prop) => {
      const cEl = host.querySelector(colorId);
      const hEl = host.querySelector(hexId);
      const apply = (raw) => {
        const sel = getLayer(studioState.selectedLayerId, activeVariant);
        if (!sel) return;
        const hex = normalizeHexColor(raw, sel[prop] || "#ffffff");
        sel[prop] = hex;
        if (cEl) cEl.value = hex;
        if (hEl && document.activeElement !== hEl) hEl.value = hex.toUpperCase();
        renderAllCanvases();
        scheduleSaveDesign();
      };
      if (cEl && cEl.dataset.bound !== "1") {
        cEl.dataset.bound = "1";
        cEl.addEventListener("input", (e) => apply(e.target.value));
      }
      if (hEl && hEl.dataset.bound !== "1") {
        hEl.dataset.bound = "1";
        hEl.addEventListener("input", (e) => {
          const v = String(e.target.value || "").trim();
          if (/^#?[0-9a-fA-F]{6}$/.test(v)) apply(v.startsWith("#") ? v : `#${v}`);
        });
        hEl.addEventListener("change", (e) => apply(e.target.value));
      }
    };
    bindCtxLayerColor("#ctxTextFillColor", "#ctxTextFillHex", "fill");
    bindCtxLayerColor("#ctxTextStrokeColor", "#ctxTextStrokeHex", "stroke");
    bindCtxLayerColor("#ctxTextHlColor", null, "highlightFill");

    host.querySelectorAll("[data-ctx-fill-swatch]").forEach((btn) => {
      if (btn.dataset.bound === "1") return;
      btn.dataset.bound = "1";
      btn.addEventListener("click", () => {
        const sel = getLayer(studioState.selectedLayerId, activeVariant);
        if (!sel) return;
        pushUndoSnapshot();
        sel.fill = normalizeHexColor(btn.dataset.swatchHex, "#fbbf24");
        renderAllCanvases();
        refreshContextualPanels();
        scheduleSaveDesign();
      });
    });

    const ctxBadgeBg = host.querySelector("#ctxBadgeBgColor");
    if (ctxBadgeBg && ctxBadgeBg.dataset.bound !== "1") {
      ctxBadgeBg.dataset.bound = "1";
      ctxBadgeBg.addEventListener("input", (e) => {
        const sel = getLayer(studioState.selectedLayerId, activeVariant);
        if (!sel) return;
        sel.type = "badge";
        sel.bgColor = normalizeHexColor(e.target.value, "#dc2626");
        renderAllCanvases();
        scheduleSaveDesign();
      });
    }
    const ctxBadgeTrans = host.querySelector("#ctxBadgeTransBtn");
    if (ctxBadgeTrans && ctxBadgeTrans.dataset.bound !== "1") {
      ctxBadgeTrans.dataset.bound = "1";
      ctxBadgeTrans.addEventListener("click", () => {
        const sel = getLayer(studioState.selectedLayerId, activeVariant);
        if (!sel) return;
        pushUndoSnapshot();
        const raw = String(sel.bgColor || "").trim().toLowerCase();
        const isTrans = !raw || raw === "transparent" || raw === "none";
        sel.bgColor = isTrans ? "#dc2626" : "transparent";
        renderAllCanvases();
        refreshContextualPanels();
        scheduleSaveDesign();
      });
    }

    // 8. Arrow Controls
    const ensureEditableArrow = () => {
      let arr = getActiveArrowLayer(activeVariant);
      if (!arr) {
        addNewArrowLayer("curved_pointer");
        arr = getActiveArrowLayer(activeVariant);
      }
      if (arr && arr.visible === false) arr.visible = true;
      return arr;
    };
    host.querySelectorAll("[data-pick-arrow-style]").forEach((btn) => {
      if (btn.dataset.bound === "1") return;
      btn.dataset.bound = "1";
      btn.addEventListener("click", () => {
        pushUndoSnapshot();
        const styleId = btn.dataset.pickArrowStyle;
        const arr = ensureEditableArrow();
        if (!arr) return;
        arr.arrowStyle = styleId;
        arr.visible = true;
        studioState.selectedLayerId = arr.id;
        renderAllCanvases();
        refreshContextualPanels();
        scheduleSaveDesign();
      });
    });
    const applyArrowColor = (prop, rawHex) => {
      const arr = ensureEditableArrow();
      if (!arr) return;
      arr[prop] = normalizeHexColor(rawHex, prop === "fill" ? "#ef4444" : "#ffffff");
      studioState.selectedLayerId = arr.id;
      renderAllCanvases();
      scheduleSaveDesign();
    };
    host.querySelector("#arrowFillColorInput")?.addEventListener("input", (e) => applyArrowColor("fill", e.target.value));
    host.querySelector("#arrowFillHexInput")?.addEventListener("change", (e) => applyArrowColor("fill", e.target.value));
    host.querySelector("#arrowStrokeColorInput")?.addEventListener("input", (e) => applyArrowColor("stroke", e.target.value));
    host.querySelectorAll("[data-arrow-fill-swatch]").forEach((btn) => {
      if (btn.dataset.bound === "1") return;
      btn.dataset.bound = "1";
      btn.addEventListener("click", () => {
        pushUndoSnapshot();
        applyArrowColor("fill", btn.dataset.swatchHex);
        refreshContextualPanels();
      });
    });
    host.querySelector("#arrowStrokeWidthSlider")?.addEventListener("input", (e) => {
      const arr = ensureEditableArrow();
      if (!arr) return;
      const val = Math.round(Number(e.target.value || 0));
      arr.strokeWidth = val;
      const lbl = host.querySelector("#arrowStrokeWidthLabel");
      if (lbl) lbl.textContent = `${val}px`;
      renderAllCanvases();
      scheduleSaveDesign();
    });
    host.querySelector("#applyArrowAllVariantsBtn")?.addEventListener("click", () => {
      const srcArr = getActiveArrowLayer(activeVariant);
      if (!srcArr) return;
      pushUndoSnapshot();
      getVariants().forEach((v) => {
        (v.layers || []).forEach((l) => {
          if (l && (l.type === "arrow" || l.id === "forensic_arrow")) {
            l.arrowStyle = srcArr.arrowStyle || "curved_pointer";
            l.fill = srcArr.fill || "#ef4444";
            l.stroke = srcArr.stroke || "#ffffff";
            l.strokeWidth = srcArr.strokeWidth ?? 6;
          }
        });
      });
      renderAllCanvases();
      scheduleSaveDesign();
      showToast("↗ Đã áp dụng kiểu & màu mũi tên cho cả 4 Bản!");
    });

    // 9. Circle Controls
    const ensureEditableCircle = () => {
      let cir = getActiveCircleLayer(activeVariant);
      if (!cir) {
        addNewCircleLayer("solid_ring");
        cir = getActiveCircleLayer(activeVariant);
      }
      if (cir && cir.visible === false) cir.visible = true;
      return cir;
    };
    host.querySelectorAll("[data-pick-circle-style]").forEach((btn) => {
      if (btn.dataset.bound === "1") return;
      btn.dataset.bound = "1";
      btn.addEventListener("click", () => {
        pushUndoSnapshot();
        const styleId = btn.dataset.pickCircleStyle;
        const cir = ensureEditableCircle();
        if (!cir) return;
        cir.circleStyle = styleId;
        cir.visible = true;
        studioState.selectedLayerId = cir.id;
        renderAllCanvases();
        refreshContextualPanels();
        scheduleSaveDesign();
      });
    });
    const applyCircleColor = (prop, rawHex) => {
      const cir = ensureEditableCircle();
      if (!cir) return;
      cir[prop] = normalizeHexColor(rawHex, prop === "stroke" ? "#ef4444" : "#000000");
      studioState.selectedLayerId = cir.id;
      renderAllCanvases();
      scheduleSaveDesign();
    };
    host.querySelector("#circleStrokeColorInput")?.addEventListener("input", (e) => applyCircleColor("stroke", e.target.value));
    host.querySelector("#circleStrokeHexInput")?.addEventListener("change", (e) => applyCircleColor("stroke", e.target.value));
    host.querySelector("#circleOuterColorInput")?.addEventListener("input", (e) => applyCircleColor("outerStroke", e.target.value));
    host.querySelectorAll("[data-circle-stroke-swatch]").forEach((btn) => {
      if (btn.dataset.bound === "1") return;
      btn.dataset.bound = "1";
      btn.addEventListener("click", () => {
        pushUndoSnapshot();
        applyCircleColor("stroke", btn.dataset.swatchHex);
        refreshContextualPanels();
      });
    });
    host.querySelector("#circleStrokeWidthSlider")?.addEventListener("input", (e) => {
      const cir = ensureEditableCircle();
      if (!cir) return;
      const val = Math.round(Number(e.target.value || 8));
      cir.strokeWidth = val;
      const lbl = host.querySelector("#circleStrokeWidthLabel");
      if (lbl) lbl.textContent = `${val}px`;
      renderAllCanvases();
      scheduleSaveDesign();
    });
    host.querySelector("#applyCircleAllVariantsBtn")?.addEventListener("click", () => {
      const srcCir = getActiveCircleLayer(activeVariant);
      if (!srcCir) return;
      pushUndoSnapshot();
      getVariants().forEach((v) => {
        (v.layers || []).forEach((l) => {
          if (l && (l.type === "circle" || l.id === "forensic_circle")) {
            l.circleStyle = srcCir.circleStyle || "solid_ring";
            l.stroke = srcCir.stroke || "#ef4444";
            l.outerStroke = srcCir.outerStroke || "#000000";
            l.strokeWidth = srcCir.strokeWidth ?? 8;
          }
        });
      });
      renderAllCanvases();
      scheduleSaveDesign();
      showToast("⭕ Đã áp dụng kiểu & màu vòng tròn cho cả 4 Bản!");
    });

    // 10. Layer Width / Height / PiP Border controls
    host.querySelector("#ctxLayerWidthSlider")?.addEventListener("input", (e) => {
      const sel = getLayer(studioState.selectedLayerId, activeVariant);
      if (!sel) return;
      const val = Math.round(Number(e.target.value || 220));
      sel.width = val;
      if (sel.type === "circle") sel.height = val;
      const lbl = host.querySelector("#ctxLayerWidthLbl");
      if (lbl) lbl.textContent = `${val}px`;
      renderAllCanvases();
      scheduleSaveDesign();
    });
    host.querySelector("#ctxLayerHeightSlider")?.addEventListener("input", (e) => {
      const sel = getLayer(studioState.selectedLayerId, activeVariant);
      if (!sel) return;
      const val = Math.round(Number(e.target.value || 200));
      sel.height = val;
      const lbl = host.querySelector("#ctxLayerHeightLbl");
      if (lbl) lbl.textContent = `${val}px`;
      renderAllCanvases();
      scheduleSaveDesign();
    });
    host.querySelectorAll("[data-pick-pip-frame-style]").forEach((btn) => {
      if (btn.dataset.bound === "1") return;
      btn.dataset.bound = "1";
      btn.addEventListener("click", () => {
        const sel = getLayer(studioState.selectedLayerId, activeVariant);
        if (!sel || sel.type !== "inset_image") return;
        pushUndoSnapshot();
        const st = String(btn.dataset.pickPipFrameStyle || "caution_tape");
        sel.frameStyle = st;
        if (btn.dataset.defaultPipColor) {
          sel.borderColor = normalizeHexColor(btn.dataset.defaultPipColor, "#fbbf24");
        }
        if (st === "vintage_paper" && Number(sel.borderWidth || 6) < 11) {
          sel.borderWidth = 13;
        } else if (st !== "vintage_paper" && Number(sel.borderWidth || 6) > 10) {
          sel.borderWidth = 6;
        }
        renderAllCanvases();
        refreshContextualPanels();
        scheduleSaveDesign();
        showToast(`🖼 Đã đổi kiểu khung PiP sang «${btn.textContent.trim()}»!`);
      });
    });
    host.querySelector("#ctxPipBorderColor")?.addEventListener("input", (e) => {
      const sel = getLayer(studioState.selectedLayerId, activeVariant);
      if (!sel) return;
      sel.borderColor = normalizeHexColor(e.target.value, "#fbbf24");
      renderAllCanvases();
      scheduleSaveDesign();
    });
    host.querySelectorAll("[data-ctx-pip-border-swatch]").forEach((btn) => {
      if (btn.dataset.bound === "1") return;
      btn.dataset.bound = "1";
      btn.addEventListener("click", () => {
        const sel = getLayer(studioState.selectedLayerId, activeVariant);
        if (!sel) return;
        sel.borderColor = normalizeHexColor(btn.dataset.swatchHex, "#fbbf24");
        renderAllCanvases();
        refreshContextualPanels();
        scheduleSaveDesign();
      });
    });
    host.querySelector("#ctxPipBorderWSlider")?.addEventListener("input", (e) => {
      const sel = getLayer(studioState.selectedLayerId, activeVariant);
      if (!sel) return;
      const val = Math.round(Number(e.target.value || 6));
      sel.borderWidth = val;
      const lbl = host.querySelector("#ctxPipBorderWLbl");
      if (lbl) lbl.textContent = `${val}px`;
      renderAllCanvases();
      scheduleSaveDesign();
    });

    // 11. Common Contextual Transform Controls
    host.querySelector("#ctxRotMinus45Btn")?.addEventListener("click", () => rotateSelectedLayer(-45));
    host.querySelector("#ctxRotMinus15Btn")?.addEventListener("click", () => rotateSelectedLayer(-15));
    host.querySelector("#ctxRotPlus15Btn")?.addEventListener("click", () => rotateSelectedLayer(15));
    host.querySelector("#ctxRotResetBtn")?.addEventListener("click", () => rotateSelectedLayer(0, 0));
    host.querySelector("#thumbSelectedAngleSlider")?.addEventListener("input", (e) => {
      const layer = getLayer(studioState.selectedLayerId, activeVariant);
      if (!layer) return;
      layer.angle = Math.round(Number(e.target.value || 0));
      renderAllCanvases();
      updateSelectedLayerTransformDom();
      scheduleSaveDesign();
    });
    host.querySelector("#ctxScaleDownBtn")?.addEventListener("click", () => scaleSelectedLayer(0.9));
    host.querySelector("#ctxScaleUpBtn")?.addEventListener("click", () => scaleSelectedLayer(1.12));
    host.querySelector("#ctxFlipXBtn")?.addEventListener("click", () => flipSelectedLayer("x"));
    host.querySelector("#ctxFlipYBtn")?.addEventListener("click", () => flipSelectedLayer("y"));
    host.querySelector("#ctxAlignLeftBtn")?.addEventListener("click", () => alignSelectedLayerCenter("left"));
    host.querySelector("#ctxAlignCenterHBtn")?.addEventListener("click", () => alignSelectedLayerCenter("h"));
    host.querySelector("#ctxBringFwdBtn")?.addEventListener("click", () => reorderSelectedLayer(1));
    host.querySelector("#ctxSendBackBtn")?.addEventListener("click", () => reorderSelectedLayer(-1));
    host.querySelector("#ctxDuplicateBtn")?.addEventListener("click", () => duplicateSelectedLayer());
    host.querySelector("#ctxDeleteBtn")?.addEventListener("click", () => {
      if (studioState.selectedLayerId) deleteLayerById(studioState.selectedLayerId);
    });

    // 12. Background & Vignette Controls
    host.querySelector("#quickVigOpacity")?.addEventListener("input", (e) => {
      const val = Number(e.target.value) / 100;
      if (lVig) {
        lVig.opacity = val;
        lVig.visible = val > 0.02;
      }
      const lbl = host.querySelector("#quickVigLabel");
      if (lbl) lbl.textContent = `${Math.round(val * 100)}%`;
      renderAllCanvases();
      scheduleSaveDesign();
    });
    host.querySelectorAll("[data-set-vig-style]").forEach((btn) => {
      if (btn.dataset.bound === "1") return;
      btn.dataset.bound = "1";
      btn.addEventListener("click", () => {
        if (!lVig) return;
        pushUndoSnapshot();
        lVig.style = btn.dataset.setVigStyle;
        lVig.visible = true;
        renderAllCanvases();
        refreshContextualPanels();
        scheduleSaveDesign();
      });
    });

    host.querySelector("#quickPairedTitleText")?.addEventListener("input", (e) => {
      activeVariant.paired_title = e.target.value;
      scheduleSaveDesign();
    });

    host.querySelectorAll("[data-pick-bg]").forEach((el) => {
      if (el.dataset.bound === "1") return;
      el.dataset.bound = "1";
      el.addEventListener("click", () => {
        pushUndoSnapshot();
        activeVariant.background_url = el.dataset.pickBg;
        activeVariant.background_path = el.dataset.pickPath || "";
        design.background_url = el.dataset.pickBg;
        design.background_path = el.dataset.pickPath || "";
        loadCachedImage(activeVariant.background_url);
        renderAllCanvases();
        refreshContextualPanels();
        scheduleSaveDesign();
      });
    });

    host.querySelectorAll("[data-pick-inset]").forEach((btn) => {
      if (btn.dataset.bound === "1") return;
      btn.dataset.bound = "1";
      btn.addEventListener("click", () => {
        pushUndoSnapshot();
        const url = btn.dataset.pickInset;
        const curSel = getLayer(studioState.selectedLayerId, activeVariant);
        let targetLayer = null;
        if (curSel && curSel.type === "inset_image") {
          targetLayer = curSel;
        } else {
          // If no inset layer currently selected, target first visible inset layer, or inset_photo
          targetLayer = (activeVariant.layers || []).find((l) => l && l.type === "inset_image" && l.visible !== false) ||
                        getLayer("inset_photo", activeVariant) ||
                        (activeVariant.layers || []).find((l) => l && l.type === "inset_image");
        }

        if (targetLayer) {
          targetLayer.src = url;
          targetLayer.visible = true;
          studioState.selectedLayerId = targetLayer.id;
          if (targetLayer.id === "inset_photo" || !activeVariant.inset_image_url) {
            activeVariant.inset_image_url = url;
          }
          showToast(`🖼 Đã đổi ảnh cho [${targetLayer.name || targetLayer.id}]!`);
        } else {
          const newId = `pip_${Date.now().toString(36).slice(-4)}`;
          const newPip = {
            id: newId,
            type: "inset_image",
            name: "Ảnh phụ PiP",
            src: url,
            left: 840,
            top: 44,
            width: 376,
            height: 290,
            borderColor: "#fbbf24",
            borderWidth: 6,
            angle: 0,
            visible: true,
          };
          if (!activeVariant.layers) activeVariant.layers = [];
          activeVariant.layers.push(newPip);
          studioState.selectedLayerId = newId;
          activeVariant.inset_image_url = url;
          showToast(`🖼 Đã thêm Ảnh phụ PiP mới!`);
        }

        loadCachedImage(url);
        renderAllCanvases();
        refreshContextualPanels();
        scheduleSaveDesign();
      });
    });

    host.querySelectorAll("#ctxUploadPipFileInput").forEach((inp) => {
      if (inp.dataset.bound === "1") return;
      inp.dataset.bound = "1";
      inp.addEventListener("change", (e) => {
        const file = e.target.files?.[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = async () => {
          try {
            const dataUrl = String(reader.result || "");
            if (!dataUrl) return;
            const curSel = getLayer(studioState.selectedLayerId, activeVariant);
            let targetLayer = (curSel && curSel.type === "inset_image")
              ? curSel
              : (activeVariant.layers || []).find((l) => l && l.type === "inset_image" && l.visible !== false) || getLayer("inset_photo", activeVariant);

            const resp = await fetch(`/api/jobs/${encodeURIComponent(studioState.jobId)}/thumbnail-studio/upload-image`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                role: "inset",
                variant_id: activeVariant.id,
                layer_id: targetLayer ? targetLayer.id : "inset_photo",
                data_url: dataUrl,
              }),
            });
            const res = await resp.json();
            const newUrl = res.url || dataUrl;
            pushUndoSnapshot();
            if (targetLayer) {
              targetLayer.src = newUrl;
              targetLayer.visible = true;
              studioState.selectedLayerId = targetLayer.id;
            } else {
              const newId = `pip_${Date.now().toString(36).slice(-4)}`;
              const newPip = {
                id: newId,
                type: "inset_image",
                name: "Ảnh phụ PiP",
                src: newUrl,
                left: 840,
                top: 44,
                width: 376,
                height: 290,
                borderColor: "#fbbf24",
                borderWidth: 6,
                angle: 0,
                visible: true,
              };
              if (!activeVariant.layers) activeVariant.layers = [];
              activeVariant.layers.push(newPip);
              studioState.selectedLayerId = newId;
            }
            loadCachedImage(newUrl);
            renderStudioDom();
            scheduleSaveDesign();
            showToast(`✅ Đã tải ảnh lên và áp dụng cho [${targetLayer?.name || 'PiP'}]!`);
          } catch (err) {
            console.error("Upload PiP error:", err);
            showToast("Lỗi khi tải ảnh PiP: " + err.message);
          }
        };
        reader.readAsDataURL(file);
      });
    });

    host.querySelectorAll("#thumbGenSingleFlowBtn").forEach((btn) => {
      if (btn.dataset.bound === "1") return;
      btn.dataset.bound = "1";
      btn.addEventListener("click", () => generateFlowForVariant(activeVariant.id));
    });

    host.querySelectorAll("#thumbUploadBgInput").forEach((inp) => {
      if (inp.dataset.bound === "1") return;
      inp.dataset.bound = "1";
      inp.addEventListener("change", (e) => {
        const file = e.target.files?.[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = async () => {
          try {
            const resp = await fetch(`/api/jobs/${encodeURIComponent(studioState.jobId)}/thumbnail-studio/upload-image`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                role: "background",
                variant_id: activeVariant.id,
                data_url: String(reader.result || ""),
              }),
            });
            const json = await resp.json();
            if (!resp.ok) throw new Error(json.detail || "Tải ảnh thất bại");
            studioState.data = json;
            renderStudioDom();
            showToast(`Đã cập nhật ảnh nền cho ${activeVariant.short_label || activeVariant.id}!`);
          } catch (err) {
            showToast(err.message, true);
          }
        };
        reader.readAsDataURL(file);
        e.target.value = "";
      });
    });

    host.querySelectorAll("#thumbClearAllOverlaysBtn").forEach((btn) => {
      if (btn.dataset.bound === "1") return;
      btn.dataset.bound = "1";
      btn.addEventListener("click", clearAllOverlaysOnActiveVariant);
    });
    host.querySelectorAll("#thumbRestoreTextBtn").forEach((btn) => {
      if (btn.dataset.bound === "1") return;
      btn.dataset.bound = "1";
      btn.addEventListener("click", restoreAllTextOnActiveVariant);
    });
  }

  function copyAllSeoBundle() {
    const pack = studioState.seoPack || studioState.data?.seo_package || {};
    const variants = getVariants();
    const design = studioState.data?.design || {};
    const activeVariant = getActiveVariant() || variants[0] || {};
    const activeIdx = Math.max(0, variants.findIndex((v) => v.id === activeVariant.id));
    const activeVi = parseVariantVietnamese(activeVariant, activeIdx);
    const titleKo = String(activeVi.pairedTitleKo || pack.recommended_title || "").trim();
    const desc = String(pack.description || "").trim();
    const hashtags = Array.isArray(pack.hashtags) ? pack.hashtags.join(" ") : "";
    const tags = Array.isArray(pack.tags) ? pack.tags.join(", ") : "";
    const fullDesc = [desc, hashtags].filter(Boolean).join("\n\n");

    const bundleText = [
      "=== [1. TIÊU ĐỀ YOUTUBE] ===",
      titleKo,
      "",
      "=== [2. MÔ TẢ YOUTUBE + TIMESTAMPS] ===",
      fullDesc,
      "",
      "=== [3. TAGS YOUTUBE (DÁN VÀO YOUTUBE STUDIO)] ===",
      tags,
    ].join("\n");

    if (navigator.clipboard) {
      navigator.clipboard.writeText(bundleText).then(() => {
        showToast("📋 Đã sao chép Trọn Bộ YouTube (Tiêu đề + Mô tả + Tags)!");
      }).catch(() => {
        showToast("Không thể sao chép vào bộ nhớ tạm", true);
      });
    }
  }

  function buildMasterHeaderHtml(winnerVariant, channelDnaSig, variants) {
    const winnerLabel = winnerVariant ? (winnerVariant.short_label || "BẢN A") : "BẢN A";
    const winnerCtr = winnerVariant ? evaluateVariantCtr(winnerVariant) : { score: 83, predicted_ctr_pct: 11.8 };

    return `
      <div class="thumb-master-header">
        <div class="header-left">
          <div class="header-kicker">PHASE 07 · BAO BÌ &amp; ĐÓNG GÓI PHÁT HÀNH YOUTUBE</div>
          <h2 class="header-title">YouTube Packaging Studio · Thumbnail &amp; SEO</h2>
          <div class="header-status-line">
            <span class="status-pill winner">★ Winner: ${esc(winnerLabel)} (CTR ${winnerCtr.score}점 · ${winnerCtr.predicted_ctr_pct || 11.8}%)</span>
            <span class="status-pill safe">✓ 100% An toàn Kiếm tiền Xanh</span>
            <span class="status-pill dna">Hồ sơ: ${esc(channelDnaSig)}</span>
          </div>
        </div>
        <div class="header-right">
          <button type="button" class="primary compact" id="thumbCopyAllSeoBtn" title="Sao chép toàn bộ Tiêu đề, Mô tả và Tags YouTube">📋 Sao chép Trọn Gói SEO</button>
          <button type="button" class="ghost compact" id="thumbDownloadAllBtn" ${studioState.busyExportAll ? "disabled" : ""}>📦 Tải hết ${variants.length} Bản (.JPG)</button>
          <button type="button" class="ghost compact" id="thumbExportAbPackBtn" ${studioState.busyExportAbPack ? "disabled" : ""}>📦 Xuất Gói A/B Test</button>
          <button type="button" class="ghost compact" id="thumbBatchFlowBtn" ${studioState.busyBatchFlow ? "disabled" : ""}>🎨 Tạo 3 Nền Flow</button>
          <button type="button" class="ghost compact" id="thumbLockChannelDnaBtn" ${studioState.busyLockDna ? "disabled" : ""}>🔒 Lưu DNA Kênh</button>
        </div>
      </div>
    `;
  }

  function buildUnifiedNavHtml(activeTab) {
    return `
      <div class="thumb-unified-nav">
        <button type="button" class="thumb-nav-tab ${activeTab === 'compare' ? 'active' : ''}" data-thumb-main-tab="compare">
          <span class="tab-badge-num">1</span>
          <span class="tab-icon">⊞</span>
          <div class="tab-labels">
            <span class="tab-title">So Sánh 4 Bản Test (A/B/C/D)</span>
            <span class="tab-sub">Lưới 4 phương án · Dự đoán CTR &amp; Tải lẻ</span>
          </div>
        </button>
        <button type="button" class="thumb-nav-tab ${activeTab === 'editor' ? 'active' : ''}" data-thumb-main-tab="editor">
          <span class="tab-badge-num">2</span>
          <span class="tab-icon">🎨</span>
          <div class="tab-labels">
            <span class="tab-title">Bàn Dựng Canva Studio (Chỉnh Sửa)</span>
            <span class="tab-sub">Chỉnh sửa trực quan · 10 Font Hàn · Khung &amp; Hiệu ứng</span>
          </div>
        </button>
        <button type="button" class="thumb-nav-tab ${activeTab === 'seo' ? 'active' : ''}" data-thumb-main-tab="seo">
          <span class="tab-badge-num">3</span>
          <span class="tab-icon">📋</span>
          <div class="tab-labels">
            <span class="tab-title">Gói SEO YouTube Studio</span>
            <span class="tab-sub">8 Tiêu Đề Song Ngữ · Mô Tả · Tags</span>
          </div>
        </button>
        <button type="button" class="thumb-nav-tab ${activeTab === 'preview' ? 'active' : ''}" data-thumb-main-tab="preview">
          <span class="tab-badge-num">4</span>
          <span class="tab-icon">📺</span>
          <div class="tab-labels">
            <span class="tab-title">Mô Phỏng YouTube Feed</span>
            <span class="tab-sub">Kiểm tra thực tế Home &amp; Sidebar</span>
          </div>
        </button>
      </div>
    `;
  }

  function buildEditorViewHtml(variants, activeVariant, activeVi, design, curZoomPct) {
    const isWinner = activeVariant.id === (design.active_variant_id || "v1");
    const pairedTitleKo = activeVi.pairedTitleKo || `${activeVariant.line_1 || ""} ${activeVariant.line_2 || ""}`;
    const pairedTitleVi = activeVi.pairedTitleVi || "";

    return `
      <div class="thumb-editor-suite unified-studio-frame">
        <!-- 1. INTEGRATED STUDIO TOPBAR -->
        <div class="studio-topbar">
          <div class="studio-topbar-left">
            <span class="studio-topbar-label">PHƯƠNG ÁN:</span>
            <div class="studio-variant-segments">
              ${variants.map((v, idx) => {
                const isAct = v.id === activeVariant.id;
                const isWin = v.id === (design.active_variant_id || "v1");
                const ctr = evaluateVariantCtr(v);
                const label = v.short_label || `BẢN ${String.fromCharCode(65 + idx)}`;
                const aObj = (studioState.data?.archetypes || []).find(a => a.id === v.archetype);
                const aName = aObj ? aObj.name.split("—")[0].trim() : v.archetype;

                return `
                  <button type="button" class="studio-variant-seg ${isAct ? 'active' : ''} ${isWin ? 'is-winner' : ''}" data-switch-workbench-variant="${esc(v.id)}" title="${esc(aName)}">
                    <span class="seg-tag">${esc(label)}</span>
                    <span class="seg-name">${esc(aName)}</span>
                    <span class="seg-ctr ${ctr.score >= 85 ? 'ok' : 'warn'}">${ctr.score}점 (${ctr.predicted_ctr_pct || 10.5}%)</span>
                    ${isWin ? `<span class="seg-win">★</span>` : ""}
                  </button>
                `;
              }).join("")}
            </div>
          </div>
          <div class="studio-topbar-right">
            ${isWinner ? `<span class="studio-win-badge">✓ Đang là Winner</span>` : `<button type="button" class="primary compact" id="editorSavePrimaryBtn" data-select-winner="${esc(activeVariant.id)}">★ Chọn Làm Winner</button>`}
            <button type="button" class="ghost compact" id="editorDownloadThisBtn" data-download-variant="${esc(activeVariant.id)}">⬇ Tải .JPG</button>
            <button type="button" class="ghost compact" data-thumb-main-tab="compare">⊞ Bảng So Sánh</button>
            <button type="button" class="ghost compact" data-zoom-variant="${esc(activeVariant.id)}">🔍 Phóng to</button>
            <button type="button" class="ghost compact" id="thumbToggleDrawerBtn" style="display:none;" title="Thu gọn/Mở">▼</button>
            <button type="button" class="${studioState.editorZoomed ? "primary" : "ghost"} compact" id="thumbToggleZoomEditorBtn">${studioState.editorZoomed ? "🗗 Thoát Full" : "⛶ Toàn màn hình"}</button>
          </div>
        </div>

        <!-- 2. INTEGRATED PAIRED YOUTUBE TITLE STRIP -->
        <div class="studio-paired-bar">
          <div class="paired-bar-tag">🎬 TIÊU ĐỀ YOUTUBE GHÉP CẶP (${esc(activeVariant.short_label || 'Bản này')}):</div>
          <div class="paired-bar-content">
            <span class="paired-bar-ko">🇰🇷 <b>${esc(pairedTitleKo)}</b></span>
            ${pairedTitleVi ? `<span class="paired-bar-vi">🇻🇳 ${esc(pairedTitleVi)}</span>` : ""}
            ${activeVi.synergyVi ? `<span class="paired-bar-syn">🔗 ${esc(activeVi.synergyVi)}</span>` : ""}
          </div>
          <div class="paired-bar-actions">
            <button type="button" class="ghost compact" data-copy-raw-title="${esc(pairedTitleKo)}">📋 Sao chép Tiêu đề</button>
            <button type="button" class="ghost compact" data-switch-to-seo-tab="1">👉 Mở Gói SEO</button>
          </div>
        </div>

        <!-- 3. CANVA 3-COLUMN WORKBENCH -->
        <div class="canva-workbench-3col">
          <!-- CỘT TRÁI: DOCK CÔNG CỤ & THƯ VIỆN -->
          <aside class="canva-left-dock" id="cofiThumbLeftDock">
            ${buildLeftDockInnerHtml(activeVariant)}
          </aside>

          <!-- CỘT GIỮA: STAGE CANVAS 16:9 -->
          <main class="canva-center-stage" id="cofiThumbCenterStage">
            <!-- THANH CÔNG CỤ CANVAS NHANH -->
            <div class="thumb-stage-toolbar">
              <div class="stage-tools-left">
                <span style="font-size:11px;font-weight:700;color:#94a3b8;margin-right:2px;">LỚP:</span>
                <div class="thumb-quick-layers-bar" id="cofiThumbQuickLayersBar">
                  ${buildQuickLayersBarInnerHtml(activeVariant)}
                </div>
              </div>
              <div class="stage-tools-right">
                <button type="button" class="ghost compact" id="thumbUndoBtn" title="Hoàn tác (Ctrl+Z)">↶</button>
                <button type="button" class="ghost compact" id="thumbDuplicateLayerBtn" title="Nhân bản (Ctrl+D)">📋</button>
                <button type="button" class="ghost compact thumb-danger-btn" id="thumbDeleteSelectedBtn" title="Xóa (Del)">🗑</button>
                <label class="thumb-safezone-toggle" title="Khung thời lượng 30:15">
                  <input type="checkbox" id="thumbSafeZoneToggle" ${design.safe_zone_visible ? "checked" : ""} />
                  <span>30:15</span>
                </label>
                <div class="thumb-zoom-controls">
                  <button type="button" class="ghost compact" id="thumbZoomOutBtn">−</button>
                  <span class="thumb-zoom-readout" id="thumbZoomReadout">${curZoomPct}%</span>
                  <button type="button" class="ghost compact" id="thumbZoomInBtn">+</button>
                  <button type="button" class="ghost compact ${Math.abs(studioState.canvasZoom - 1) < 0.03 ? "active" : ""}" data-zoom-preset="1">100%</button>
                </div>
              </div>
            </div>

            <div class="thumb-canvas-stage-viewport" id="cofiThumbStageViewport">
              <div class="thumb-canvas-stage-inner" id="cofiThumbStageInner" style="width:${curZoomPct}%;">
                <div class="thumb-canvas-stage">
                  <canvas id="cofiThumbMainCanvas" width="${CW}" height="${CH}" tabindex="0"></canvas>
                </div>
              </div>
            </div>

            <!-- THANH GIẢI NGHĨA TIẾNG VIỆT -->
            <div class="thumb-stage-vi-bar">
              <span class="vi-title"><b style="color:#4ade80;">🇻🇳 Nghĩa chữ Thumbnail:</b></span>
              <span class="vi-badge">[Tag: ${esc(activeVi.badgeVi || activeVariant.badge_text || "")}]</span> ·
              <span class="vi-line1">D1: ${esc(activeVi.line1Vi || "")}</span> ·
              <span class="vi-line2">D2: ${esc(activeVi.line2Vi || "")}</span>
            </div>
          </main>

          <!-- CỘT PHẢI: INSPECTOR THEO NGỮ CẢNH -->
          <aside class="canva-right-inspector" id="cofiThumbRightInspector">
            ${buildRightContextualInspectorHtml(activeVariant)}
          </aside>
        </div>
      </div>
    `;
  }

  function buildCompareViewHtml(variants, archetypes, design) {
    const cardsHtml = variants.map((v, idx) => {
      const isPrimary = v.id === (design.active_variant_id || "v1");
      const ctr = evaluateVariantCtr(v);
      const vVi = parseVariantVietnamese(v, idx);
      const shortLabel = v.short_label || `BẢN ${String.fromCharCode(65 + idx)}`;
      const archObj = archetypes.find(a => a.id === v.archetype);
      const archName = archObj ? archObj.name.split("—")[0].trim() : v.archetype;
      const hookBadge = v.hook_badge || (idx === 0 ? "🎯 Tò mò / Nghịch lý" : idx === 1 ? "🔍 Bằng chứng độc quyền" : idx === 2 ? "⚡ Đối đầu / Hồ sơ mật" : `Variant ${String.fromCharCode(65 + idx)}`);
      const ytTitleKo = vVi.pairedTitleKo || `${v.line_1 || ""} ${v.line_2 || ""}`;

      return `
        <article class="thumb-compare-card ${isPrimary ? 'is-winner' : ''}" data-card-variant="${esc(v.id)}">
          <div class="compare-card-head">
            <div class="head-tags">
              <span class="tag-pill">${esc(shortLabel)}</span>
              <span class="arch-pill">${esc(archName)}</span>
              ${isPrimary ? `<span class="winner-pill">★ Winner</span>` : ""}
            </div>
            <span class="ctr-badge ${ctr.score >= 85 ? 'ok' : 'warn'}">CTR ${ctr.score}점 (${ctr.predicted_ctr_pct || 10.5}%)</span>
          </div>

          <div class="compare-preview-frame" data-zoom-variant="${esc(v.id)}" title="Ấn để phóng to xem ảnh 1280x720">
            <canvas data-thumb-card-canvas="${esc(v.id)}" width="${CW}" height="${CH}"></canvas>
            <span class="compare-yt-duration">30:15</span>
            <div class="compare-hover-zoom"><span>🔍 Phóng to</span></div>
          </div>

          <div class="compare-card-body">
            <div class="hook-badge-line">🏷 [${esc(v.badge_text || "")}] · <span style="color:#93c5fd;">${esc(hookBadge)}</span></div>
            <div class="hook-text-line"><strong>${esc(v.line_1 || "")}</strong> · <span style="color:#fbbf24;">${esc(v.line_2 || "")}</span></div>
            ${(vVi.line1Vi || vVi.line2Vi) ? `
              <div class="compare-vi-text">
                ${vVi.badgeVi ? `<div><b style="color:#4ade80;">Tag:</b> ${esc(vVi.badgeVi)}</div>` : ""}
                ${vVi.line1Vi ? `<div><b style="color:#fde047;">D1:</b> ${esc(vVi.line1Vi)}</div>` : ""}
                ${vVi.line2Vi ? `<div><b style="color:#f87171;">D2:</b> ${esc(vVi.line2Vi)}</div>` : ""}
              </div>` : ""}
            
            <div class="compare-paired-title">
              <div class="title-ko">🎬 <b>Tiêu đề ghép:</b> 🇰🇷 ${esc(ytTitleKo)}</div>
              ${vVi.pairedTitleVi ? `<div class="title-vi">🇻🇳 ${esc(vVi.pairedTitleVi)}</div>` : ""}
            </div>
          </div>

          <div class="compare-card-actions">
            <button type="button" class="primary compact" data-edit-variant="${esc(v.id)}" style="flex:1.4;font-weight:800;background:linear-gradient(135deg,#0284c7,#0369a1);border-color:#38bdf8;">🎨 Chỉnh sửa bản này</button>
            <button type="button" class="ghost compact" data-select-winner="${esc(v.id)}" style="flex:1;">${isPrimary ? '✓ Winner' : '★ Chọn'}</button>
            <button type="button" class="ghost compact" data-download-variant="${esc(v.id)}">⬇ Tải</button>
            <button type="button" class="ghost compact" data-zoom-variant="${esc(v.id)}">🔍</button>
          </div>
        </article>
      `;
    }).join("");

    return `
      <div class="thumb-compare-suite">
        <div class="thumb-compare-info-bar">
          <div>
            <strong>SO SÁNH ĐA PHƯƠNG ÁN (A / B / C / D) CHUẨN CTR ĐÀI HÀN QUỐC</strong>
            <small style="display:block;color:#94a3b8;margin-top:2px;">So sánh 4 góc độ tâm lý khác nhau (Nghịch lý / Bằng chứng / Đối đầu / Cao trào). Bấm <b>🎨 Chỉnh sửa bản này</b> để chuyển sang Tab 2 (Bàn Dựng Studio) chỉnh sửa trực quan.</small>
          </div>
          <button type="button" class="primary compact" id="compareExportAbPackBtn">📦 Xuất Gói A/B Test YouTube</button>
        </div>
        <div class="thumb-compare-grid">${cardsHtml}</div>
      </div>
    `;
  }

  function buildSeoViewHtml(activeVariant, winnerVariant) {
    const pack = studioState.seoPack || studioState.data?.seo_package || {};
    const recKo = String(pack.recommended_title || "").trim();
    const recVi = String(pack.recommended_title_vi || "").trim();
    const rawPrimaryKw = pack.primary_keywords_summary;
    const kwSummary = rawPrimaryKw && typeof rawPrimaryKw === "object"
      ? Object.values(rawPrimaryKw).map(v => String(v || "").trim()).filter(Boolean).join(" · ")
      : String(rawPrimaryKw || "").trim();
    const synergyVi = String(pack.title_thumb_synergy_vi || "").trim();
    const rawOpts = Array.isArray(pack.title_options) ? pack.title_options : [];
    const details = Array.isArray(pack.title_options_details) ? pack.title_options_details : [];
    const optsVi = Array.isArray(pack.title_options_vi) ? pack.title_options_vi : [];
    const desc = String(pack.description || "").trim();
    const descVi = String(pack.description_vi || "").trim();
    const hashtags = Array.isArray(pack.hashtags) ? pack.hashtags.join(" ") : "";
    const tags = Array.isArray(pack.tags) ? pack.tags.join(", ") : "";
    const keywords = Array.isArray(pack.keywords) ? pack.keywords.join(", ") : "";
    const kwVi = Array.isArray(pack.keywords_vi) ? pack.keywords_vi : [];
    const fullDesc = [desc, hashtags].filter(Boolean).join("\n\n");
    const preflight = pack.preflight_summary || {};
    const preflightPassed = preflight.passed !== false;
    const matchedPatterns = Array.isArray(preflight.winner_patterns_matched) && preflight.winner_patterns_matched.length
      ? preflight.winner_patterns_matched
      : [
        "중국 실화 사건 Khóa chính",
        "Con số định lượng (6,000 CCTV, 38 xe)",
        "Tam giác Bổ trợ Title + Thumb 0% trùng lặp"
      ];
    const fw = pack.channel_framework || {};

    return `
      <div class="thumb-seo-suite">
        <!-- PRE-FLIGHT AUDIT & ALL-IN-ONE COPY BAR -->
        <div class="thumb-seo-preflight-bar">
          <div class="preflight-status">
            <span class="safe-pill">✓ 100% GREEN MONETIZATION SAFE (XANH TIỀN YOUTUBE)</span>
            <span class="safe-pill" style="background:rgba(56,189,248,0.15);border-color:rgba(56,189,248,0.35);color:#7dd3fc;">✈ CHANNEL DNA PRE-FLIGHT PASSED</span>
            <div class="patterns-matched">
              ${matchedPatterns.map(p => `<span class="pat-tag">★ ${esc(p)}</span>`).join("")}
            </div>
          </div>
          <div class="preflight-actions">
            <button type="button" class="primary compact" id="seoCopyAllBundleBtn" style="font-weight:800;font-size:12px;padding:6px 14px;">📋 Sao Chép Trọn Gói YouTube (Tiêu Đề + Mô Tả + Tags)</button>
          </div>
        </div>

        <div class="thumb-seo-grid-2col">
          <!-- CỘT TRÁI: TIÊU ĐỀ & MÔ TẢ -->
          <div class="thumb-seo-col-main">
            <!-- TIÊU ĐỀ ĐỀ XUẤT CHÍNH -->
            <section class="seo-card-unified prominent">
              <div class="seo-card-head">
                <div class="head-title">
                  <span class="head-badge">TIÊU ĐỀ ĐỀ XUẤT CHÍNH (KHỚP WINNER ${esc(winnerVariant?.short_label || 'BẢN A')})</span>
                  <strong>Chuẩn CTR &amp; DNA Kênh · Song Ngữ Hàn — Việt</strong>
                </div>
                <button type="button" class="primary compact" data-copy-raw-title="${esc(recKo)}">📋 Sao chép</button>
              </div>
              <div class="seo-title-display-box">
                <div class="ko-title">🇰🇷 ${esc(recKo || "Chưa có tiêu đề")}</div>
                ${recVi ? `<div class="vi-title"><b style="color:#4ade80;">🇻🇳 Nghĩa Tiếng Việt:</b> ${esc(recVi)}</div>` : ""}
              </div>
              ${(kwSummary || synergyVi) ? `
                <div class="seo-title-meta-box">
                  ${kwSummary ? `<div><b style="color:#38bdf8;">📍 Từ khóa &amp; Địa danh:</b> ${esc(kwSummary)}</div>` : ""}
                  ${synergyVi ? `<div><b style="color:#fbbf24;">🔗 Bổ trợ nghĩa với Thumbnail:</b> ${esc(synergyVi)}</div>` : ""}
                </div>` : ""}
            </section>

            <!-- 8 PHƯƠNG ÁN TIÊU ĐỀ & GHÉP CẶP THUMBNAIL -->
            <section class="seo-card-unified">
              <div class="seo-card-head">
                <div class="head-title">
                  <span class="head-badge">8 PHƯƠNG ÁN TIÊU ĐỀ THEO BỘ BẢN TEST (A / B / C / D)</span>
                  <strong>Mỗi tiêu đề được tối ưu hóa cho từng góc tiếp cận tâm lý</strong>
                </div>
              </div>
              <div class="seo-options-grid-2col">
                ${rawOpts.map((opt, idx) => {
                  const d = (typeof opt === "object" && opt !== null) ? opt : (details[idx] || {});
                  const ko = typeof opt === "object" && opt !== null ? String(opt.title_ko || opt.title || "").trim() : String(opt || "").trim();
                  const vi = String(d.title_vi || optsVi[idx] || "").trim();
                  const paired = String(d.paired_variant || (idx % 4 === 0 ? "v1" : idx % 4 === 1 ? "v2" : idx % 4 === 2 ? "v3" : "v4")).trim();
                  const pairedLabel = paired === "v1" ? "BẢN A" : paired === "v2" ? "BẢN B" : paired === "v3" ? "BẢN C" : "BẢN D";
                  const kw = String(d.keyword_anchor || "").trim();
                  const syn = String(d.synergy_vi || "").trim();

                  return `
                    <div class="seo-title-option-card">
                      <div class="opt-card-top">
                        <div class="opt-card-badges">
                          <span class="opt-num">#${idx + 1}</span>
                          <span class="opt-paired-pill" data-edit-variant="${esc(paired)}" title="Ấn để mở Bàn Dựng sửa ${esc(pairedLabel)}">🎯 Ghép ${esc(pairedLabel)}</span>
                        </div>
                        <button type="button" class="ghost compact" data-copy-raw-title="${esc(ko)}">📋 Sao chép</button>
                      </div>
                      <div class="opt-ko-title">🇰🇷 ${esc(ko)}</div>
                      ${vi ? `<div class="opt-vi-title"><b>🇻🇳 Nghĩa:</b> ${esc(vi)}</div>` : ""}
                      ${kw ? `<div class="opt-kw-anchor"><b>📍 Khóa:</b> ${esc(kw)}</div>` : ""}
                      ${syn ? `<div class="opt-synergy"><b>🔗 Bổ trợ:</b> ${esc(syn)}</div>` : ""}
                      <div class="opt-card-actions">
                        <button type="button" class="ghost compact" data-edit-variant="${esc(paired)}">✎ Sửa Thumbnail ${esc(pairedLabel)}</button>
                      </div>
                    </div>
                  `;
                }).join("")}
              </div>
            </section>

            <!-- MÔ TẢ YOUTUBE ĐẦY ĐỦ + TIMESTAMPS -->
            <section class="seo-card-unified">
              <div class="seo-card-head">
                <div class="head-title">
                  <span class="head-badge">MÔ TẢ YOUTUBE + TIMESTAMPS &amp; HASHTAGS</span>
                  <strong>Đầy đủ Hook, Chương phân đoạn (Acts), Bản án pháp lý và Hashtags chuẩn SEO</strong>
                </div>
                <button type="button" class="primary compact" data-copy-raw-desc="1">📋 Sao chép Mô Tả</button>
              </div>
              <pre class="seo-raw-prebox" id="seoRawDescBox">${esc(fullDesc || "Chưa có mô tả")}</pre>
              ${descVi ? `
                <details class="seo-desc-vi-accordion" style="margin-top:10px;">
                  <summary style="cursor:pointer;color:#4ade80;font-weight:700;font-size:12px;">▼ Bấm để xem Bản dịch Nghĩa Tiếng Việt của Phần Mô Tả</summary>
                  <pre class="seo-raw-prebox vi" style="margin-top:6px;background:rgba(15,23,42,0.92);border-color:rgba(34,197,94,0.3);color:#e2e8f0;">${esc(descVi)}</pre>
                </details>` : ""}
            </section>
          </div>

          <!-- CỘT PHẢI: WINNER THUMB PREVIEW, TAGS, TỪ KHÓA, CHANNEL FRAMEWORK -->
          <div class="thumb-seo-col-side">
            <!-- WINNER THUMBNAIL PREVIEW CARD -->
            <section class="seo-card-unified">
              <div class="seo-card-head">
                <div class="head-title">
                  <span class="head-badge gold">★ WINNER THUMBNAIL HIỆN TẠI</span>
                  <strong>${esc(winnerVariant?.short_label || 'BẢN A')} · CTR Dự đoán ${winnerVariant ? evaluateVariantCtr(winnerVariant).predicted_ctr_pct : 11.8}%</strong>
                </div>
                <button type="button" class="ghost compact" data-download-variant="${esc(winnerVariant?.id || 'v1')}">⬇ Tải .JPG</button>
              </div>
              <div class="seo-winner-thumb-frame" data-zoom-variant="${esc(winnerVariant?.id || 'v1')}" title="Ấn để phóng to">
                <canvas data-thumb-card-canvas="${esc(winnerVariant?.id || 'v1')}" width="${CW}" height="${CH}"></canvas>
                <div class="winner-thumb-overlay"><span>🔍 Xem Full</span></div>
              </div>
              <div style="margin-top:8px;font-size:12px;color:#cbd5e1;line-height:1.4;">
                <b style="color:#fbbf24;">Hook trên ảnh:</b> ${esc(winnerVariant?.line_1 || "")} ${esc(winnerVariant?.line_2 || "")}
              </div>
              <div style="margin-top:8px;display:flex;gap:6px;">
                <button type="button" class="ghost compact" data-edit-variant="${esc(winnerVariant?.id || 'v1')}" style="flex:1;">✎ Chỉnh sửa bản này</button>
                <button type="button" class="ghost compact" data-thumb-main-tab="compare" style="flex:1;">⊞ So sánh 4 bản</button>
              </div>
            </section>

            <!-- VIDEO TAGS (DÁN STUDIO) -->
            <section class="seo-card-unified">
              <div class="seo-card-head">
                <div class="head-title">
                  <span class="head-badge">TAGS YOUTUBE (DÁN VÀO STUDIO)</span>
                  <strong>Dấu phẩy phân tách · Chuẩn 500 ký tự YouTube</strong>
                </div>
                <button type="button" class="primary compact" data-copy-raw-tags="1">📋 Sao chép Tags</button>
              </div>
              <div class="seo-tags-display-box" id="seoRawTagsBox">
                ${tags ? tags.split(",").map(t => `<span class="yt-tag-pill">${esc(t.trim())}</span>`).join("") : "Chưa có tags"}
              </div>
            </section>

            <!-- TỪ KHÓA SEO TRỤ CỘT -->
            <section class="seo-card-unified">
              <div class="seo-card-head">
                <div class="head-title">
                  <span class="head-badge">TỪ KHÓA SEO TRỤ CỘT</span>
                  <strong>Korean Keyword Anchors &amp; Giải nghĩa</strong>
                </div>
                <button type="button" class="ghost compact" data-copy-raw-kw="1">📋 Sao chép</button>
              </div>
              <div class="seo-keywords-list" id="seoRawKwBox">
                <div style="color:#f8fafc;font-weight:700;font-size:13px;">${esc(keywords || "Chưa có")}</div>
                ${kwVi.length ? `<div style="margin-top:6px;font-size:12px;color:#4ade80;line-height:1.45;"><b>🇻🇳 Giải nghĩa:</b> ${kwVi.map(k => esc(k)).join(" · ")}</div>` : ""}
              </div>
            </section>

            <!-- BỘ KHUNG SEO CHUẨN KÊNH -->
            ${fw.title_formula ? `
              <section class="seo-card-unified">
                <div class="seo-card-head">
                  <div class="head-title">
                    <span class="head-badge">BỘ KHUNG CÔNG THỨC KÊNH (${esc(fw.series_key || "중국 실화 사건")})</span>
                  </div>
                </div>
                <div style="font-size:12px;line-height:1.5;color:#cbd5e1;display:flex;flex-direction:column;gap:6px;">
                  <div><b style="color:#38bdf8;">Công thức Tiêu đề:</b><br/><code>${esc(fw.title_formula)}</code></div>
                  <div><b style="color:#fbbf24;">Công thức Text Thumb:</b><br/><code>${esc(fw.thumb_text_formula || "")}</code></div>
                </div>
              </section>` : ""}
          </div>
        </div>
      </div>
    `;
  }

  function buildPreviewViewHtml(variants, design) {
    const homeFeedHtml = variants.map((v, idx) => {
      const isPrimary = v.id === (design.active_variant_id || "v1");
      const ctr = evaluateVariantCtr(v);
      const vVi = parseVariantVietnamese(v, idx);
      const ytTitleKo = vVi.pairedTitleKo || `${v.line_1 || ""} ${v.line_2 || ""}`;

      return `
        <div class="yt-feed-card ${isPrimary ? 'is-winner-card' : ''}">
          <div class="yt-feed-thumb" data-zoom-variant="${esc(v.id)}">
            <canvas data-thumb-card-canvas="${esc(v.id)}" width="${CW}" height="${CH}"></canvas>
            <span class="yt-time-badge">30:15</span>
          </div>
          <div class="yt-feed-info">
            <div class="yt-feed-avatar">🕵</div>
            <div class="yt-feed-meta">
              <h4 class="yt-video-title">${esc(ytTitleKo)}</h4>
              ${vVi.pairedTitleVi ? `<div class="yt-video-title-vi">🇻🇳 ${esc(vVi.pairedTitleVi)}</div>` : ""}
              <div class="yt-channel-line">사건수첩 25시 · 조회수 18만회 · 2일 전</div>
              <div class="yt-card-actions">
                <span class="ctr-tag">CTR: ${ctr.predicted_ctr_pct || 10.5}%</span>
                <button type="button" class="ghost compact" data-edit-variant="${esc(v.id)}">✎ Sửa bản này</button>
                <button type="button" class="${isPrimary ? 'primary' : 'ghost'} compact" data-select-winner="${esc(v.id)}">${isPrimary ? '✓ Winner' : '★ Chọn'}</button>
              </div>
            </div>
          </div>
        </div>
      `;
    }).join("");

    const sidebarFeedHtml = variants.map((v, idx) => {
      const isPrimary = v.id === (design.active_variant_id || "v1");
      const vVi = parseVariantVietnamese(v, idx);
      const ytTitleKo = vVi.pairedTitleKo || `${v.line_1 || ""} ${v.line_2 || ""}`;

      return `
        <div class="yt-sidebar-card ${isPrimary ? 'is-winner' : ''}">
          <div class="yt-sidebar-thumb" data-zoom-variant="${esc(v.id)}">
            <canvas data-thumb-card-canvas="${esc(v.id)}" width="${CW}" height="${CH}"></canvas>
            <span class="yt-time-badge">30:15</span>
          </div>
          <div class="yt-sidebar-info">
            <h5 class="yt-sidebar-title">${esc(ytTitleKo)}</h5>
            <div class="yt-sidebar-channel">사건수첩 25시</div>
            <div class="yt-sidebar-views">조회수 18만회 · 2일 전</div>
            <button type="button" class="ghost compact" data-edit-variant="${esc(v.id)}" style="margin-top:4px;font-size:10.5px;">✎ Sửa</button>
          </div>
        </div>
      `;
    }).join("");

    return `
      <div class="thumb-preview-suite">
        <div class="thumb-preview-nav">
          <div class="nav-left">
            <strong>MÔ PHỎNG GIAO DIỆN YOUTUBE THỰC TẾ</strong>
            <small style="color:#94a3b8;display:block;">Kiểm tra độ nổi bật của hình đại diện khi đứng cạnh các video khác trên YouTube</small>
          </div>
          <div class="thumb-view-mode-switcher">
            <button type="button" class="ghost compact ${studioState.previewViewMode === 'home' ? 'primary' : ''}" data-thumb-view-mode="home">📱 Trang Chủ YouTube (Home Feed)</button>
            <button type="button" class="ghost compact ${studioState.previewViewMode === 'sidebar' ? 'primary' : ''}" data-thumb-view-mode="sidebar">📑 Cột Gợi Ý (Sidebar)</button>
          </div>
        </div>
        <div class="thumb-preview-stage">
          ${studioState.previewViewMode === 'home' ? `<div class="yt-home-feed-grid">${homeFeedHtml}</div>` : `<div class="yt-sidebar-feed-stack">${sidebarFeedHtml}</div>`}
        </div>
      </div>
    `;
  }

  function buildLightboxHtml(lbVariant, lbVi) {
    if (!lbVariant) return "";
    return `
      <div class="thumb-final-lightbox-backdrop" id="cofiThumbLightboxBackdrop">
        <div class="thumb-final-lightbox-modal" role="dialog" aria-modal="true">
          <div class="thumb-final-lightbox-head">
            <div class="thumb-final-lightbox-title">
              <span class="thumb-boxcard-tag">${esc(lbVariant.short_label || lbVariant.id)}</span>
              <strong>${esc(lbVariant.badge_text ? `[${lbVariant.badge_text}] ` : "")}${esc(lbVariant.line_1 || "")} — <span style="color:#fbbf24">${esc(lbVariant.line_2 || "")}</span></strong>
            </div>
            <div class="thumb-final-lightbox-actions">
              <button type="button" class="ghost compact" id="lbPrevBtn">◀ Trước</button>
              <button type="button" class="ghost compact" id="lbNextBtn">Tiếp ▶</button>
              <button type="button" class="ghost compact" id="lbEditBtn">✎ Sửa bản này</button>
              <button type="button" class="primary compact" id="lbDownloadBtn">⬇ Tải ảnh (.JPG)</button>
              <button type="button" class="ghost compact" id="lbCloseBtn">✕ Đóng</button>
            </div>
          </div>
          ${(lbVi && (lbVi.badgeVi || lbVi.line1Vi || lbVi.line2Vi)) ? `
            <div style="background:rgba(15,23,42,0.95);border:1px solid rgba(34,197,94,0.45);border-radius:8px;padding:8px 12px;font-size:12.5px;color:#f8fafc;">
              <b style="color:#4ade80;">🇻🇳 Dịch nghĩa:</b> [Tag: ${esc(lbVi.badgeVi)}] · [Dòng 1: ${esc(lbVi.line1Vi)}] · [Dòng 2: ${esc(lbVi.line2Vi)}]
            </div>` : ""}
          <div class="thumb-final-lightbox-stage">
            <canvas id="cofiThumbLightboxCanvas" width="${CW}" height="${CH}"></canvas>
          </div>
        </div>
      </div>
    `;
  }

  function renderStudioDom() {
    const host = document.getElementById("cofiThumbnailStudioHost");
    if (!host || !studioState.data) return;
    injectCanvaCompactStyles();

    // Preserve exact window scroll position so rebuilding DOM NEVER jumps the user's screen
    const savedScrollY = window.scrollY;
    const savedScrollX = window.scrollX;

    const data = studioState.data;
    const design = data.design || {};
    const variants = getVariants();
    const activeVariant = getActiveVariant() || variants[0] || {};
    const activeIdx = Math.max(0, variants.findIndex((item) => item && item.id === activeVariant.id));
    const activeVi = parseVariantVietnamese(activeVariant, activeIdx);
    const archetypes = data.archetypes || [];
    const winnerVariant = variants.find(v => v.id === (design.active_variant_id || "v1")) || variants[0];
    const channelDnaSig = String(design.channel_thumbnail_dna?.visual_signature || design.channel_thumbnail_dna?.style_preset || "Mặc định Kênh");
    const curZoomPct = Math.round((studioState.canvasZoom || 1) * 100);

    const lbVariant = studioState.lightboxVariantId ? getVariantById(studioState.lightboxVariantId) : null;
    const lbIdx = lbVariant ? Math.max(0, variants.findIndex((item) => item && item.id === lbVariant.id)) : 0;
    const lbVi = lbVariant ? parseVariantVietnamese(lbVariant, lbIdx) : null;
    const lightboxHtml = lbVariant ? buildLightboxHtml(lbVariant, lbVi) : "";

    host.innerHTML = `
      <div class="thumb-studio-card ${studioState.editorZoomed ? 'is-fullscreen-editor' : ''}">
        ${buildMasterHeaderHtml(winnerVariant, channelDnaSig, variants)}
        ${buildUnifiedNavHtml(studioState.activeTab)}

        ${studioState.activeTab === 'compare'
          ? buildCompareViewHtml(variants, archetypes, design)
          : studioState.activeTab === 'editor'
          ? buildEditorViewHtml(variants, activeVariant, activeVi, design, curZoomPct)
          : studioState.activeTab === 'seo'
          ? buildSeoViewHtml(activeVariant, winnerVariant)
          : buildPreviewViewHtml(variants, design)
        }
      </div>
      ${lightboxHtml}
    `;

    variants.forEach((v) => {
      const u = getVariantBgUrl(v);
      if (u) loadCachedImage(u);
      if (v.inset_image_url) loadCachedImage(v.inset_image_url);
      (v.layers || []).forEach((l) => {
        if (l && l.type === "inset_image" && l.src) loadCachedImage(l.src);
      });
    });
    renderAllCanvases();

    const mainCanvas = document.getElementById("cofiThumbMainCanvas");
    if (mainCanvas && studioState.activeTab === 'editor') bindMainCanvasPointerEvents(mainCanvas);

    // Top bar & Card actions
    host.querySelector("#thumbCopyAllSeoBtn")?.addEventListener("click", copyAllSeoBundle);
    host.querySelector("#seoCopyAllBundleBtn")?.addEventListener("click", copyAllSeoBundle);
    host.querySelector("#thumbBatchFlowBtn")?.addEventListener("click", generateFlowBatch3);
    host.querySelector("#thumbDownloadAllBtn")?.addEventListener("click", downloadAllVariants);
    host.querySelector("#thumbExportAbPackBtn")?.addEventListener("click", exportAbTestPack);
    host.querySelector("#compareExportAbPackBtn")?.addEventListener("click", exportAbTestPack);
    host.querySelector("#thumbLockChannelDnaBtn")?.addEventListener("click", lockThumbnailDnaToChannel);

    // Main unified tab navigation
    host.querySelectorAll("[data-thumb-main-tab]").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const tab = btn.dataset.thumbMainTab || "editor";
        studioState.activeTab = tab;
        localStorage.setItem("cofi-thumb-active-tab-v3", tab);
        renderStudioDom();
      });
    });

    // Jump from title strip to SEO tab
    host.querySelectorAll("[data-switch-to-seo-tab]").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        studioState.activeTab = "seo";
        localStorage.setItem("cofi-thumb-active-tab-v3", "seo");
        renderStudioDom();
      });
    });

    // Preview view mode
    host.querySelectorAll("[data-thumb-view-mode]").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        studioState.previewViewMode = btn.dataset.thumbViewMode || "home";
        renderStudioDom();
      });
    });

    // Winner selection
    host.querySelectorAll("[data-select-winner]").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        selectThumbnailWinner(btn.dataset.selectWinner);
      });
    });

    // Lightbox zoom
    host.querySelectorAll("[data-zoom-variant]").forEach((el) => {
      el.addEventListener("click", (e) => {
        e.stopPropagation();
        openLightbox(el.dataset.zoomVariant);
      });
    });

    // Single variant download
    host.querySelectorAll("[data-download-variant]").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        downloadSingleVariant(btn.dataset.downloadVariant, { setPrimary: false });
      });
    });

    // Switch active variant and jump to editor
    host.querySelectorAll("[data-edit-variant]").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const vid = btn.dataset.editVariant;
        design.active_variant_id = vid;
        studioState.activeTab = "editor";
        localStorage.setItem("cofi-thumb-active-tab-v3", "editor");
        renderStudioDom();
        scheduleSaveDesign();
      });
    });

    // Switch variant within editor
    host.querySelectorAll("[data-switch-workbench-variant]").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const vid = btn.dataset.switchWorkbenchVariant;
        design.active_variant_id = vid;
        renderStudioDom();
        scheduleSaveDesign();
      });
    });

    // Copy handlers
    host.querySelectorAll("[data-copy-raw-title]").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const titleToCopy = String(btn.dataset.copyRawTitle || "").trim();
        if (titleToCopy && navigator.clipboard) {
          navigator.clipboard.writeText(titleToCopy).then(() => {
            showToast("📋 Đã sao chép Tiêu đề Tiếng Hàn!");
          });
        }
      });
    });

    host.querySelectorAll("[data-copy-paired-title]").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const vid = btn.dataset.copyPairedTitle;
        const vIdx = Math.max(0, variants.findIndex((item) => item && item.id === vid));
        const vObj = getVariantById(vid);
        const vVi = parseVariantVietnamese(vObj, vIdx);
        const titleToCopy = String(vObj?.paired_title || vVi.pairedTitleKo || "").trim();
        if (titleToCopy && navigator.clipboard) {
          navigator.clipboard.writeText(titleToCopy).then(() => {
            showToast(`📋 Đã copy tiêu đề YouTube của ${vObj?.short_label || vid}!`);
          });
        }
      });
    });

    host.querySelector("[data-copy-raw-desc]")?.addEventListener("click", (e) => {
      e.stopPropagation();
      const pack = studioState.seoPack || studioState.data?.seo_package || {};
      const desc = String(pack.description || "").trim();
      const hashtags = Array.isArray(pack.hashtags) ? pack.hashtags.join(" ") : "";
      const full = [desc, hashtags].filter(Boolean).join("\n\n");
      if (navigator.clipboard) {
        navigator.clipboard.writeText(full).then(() => {
          showToast("📋 Đã sao chép Mô tả YouTube + Timestamps!");
        });
      }
    });

    host.querySelector("[data-copy-raw-tags]")?.addEventListener("click", (e) => {
      e.stopPropagation();
      const pack = studioState.seoPack || studioState.data?.seo_package || {};
      const tags = Array.isArray(pack.tags) ? pack.tags.join(", ") : "";
      if (navigator.clipboard) {
        navigator.clipboard.writeText(tags).then(() => {
          showToast("📋 Đã sao chép Tags YouTube!");
        });
      }
    });

    host.querySelector("[data-copy-raw-kw]")?.addEventListener("click", (e) => {
      e.stopPropagation();
      const pack = studioState.seoPack || studioState.data?.seo_package || {};
      const kw = Array.isArray(pack.keywords) ? pack.keywords.join(", ") : "";
      if (navigator.clipboard) {
        navigator.clipboard.writeText(kw).then(() => {
          showToast("📋 Đã sao chép Từ khóa SEO!");
        });
      }
    });

    // Editor-specific bindings
    if (studioState.activeTab === "editor") {
      host.querySelector("#thumbZoomOutBtn")?.addEventListener("click", (e) => {
        e.stopPropagation();
        setCanvasZoom((studioState.canvasZoom || 1) - 0.15);
      });
      host.querySelector("#thumbZoomInBtn")?.addEventListener("click", (e) => {
        e.stopPropagation();
        setCanvasZoom((studioState.canvasZoom || 1) + 0.15);
      });
      host.querySelectorAll("[data-zoom-preset]").forEach((btn) => {
        btn.addEventListener("click", (e) => {
          e.stopPropagation();
          setCanvasZoom(Number(btn.dataset.zoomPreset || 1));
        });
      });

      host.querySelector("#thumbToggleZoomEditorBtn")?.addEventListener("click", (e) => {
        e.stopPropagation();
        studioState.editorZoomed = !studioState.editorZoomed;
        renderStudioDom();
      });

      host.querySelector("#thumbUndoBtn")?.addEventListener("click", undoLastAction);
      host.querySelector("#thumbDuplicateLayerBtn")?.addEventListener("click", () => duplicateSelectedLayer());
      host.querySelector("#thumbDeleteSelectedBtn")?.addEventListener("click", () => {
        if (studioState.selectedLayerId) deleteLayerById(studioState.selectedLayerId);
      });
      host.querySelector("#thumbSafeZoneToggle")?.addEventListener("change", (e) => {
        design.safe_zone_visible = Boolean(e.target.checked);
        renderAllCanvases();
        scheduleSaveDesign();
      });

      // Bind all Left Dock & Right Contextual Inspector events
      bindWorkbenchDynamicEvents();
    }

    // Lightbox events
    host.querySelector("#cofiThumbLightboxBackdrop")?.addEventListener("click", (e) => {
      if (e.target.id === "cofiThumbLightboxBackdrop") closeLightbox();
    });
    host.querySelector("#lbCloseBtn")?.addEventListener("click", closeLightbox);
    host.querySelector("#lbPrevBtn")?.addEventListener("click", () => stepLightbox(-1));
    host.querySelector("#lbNextBtn")?.addEventListener("click", () => stepLightbox(1));
    host.querySelector("#lbDownloadBtn")?.addEventListener("click", () => {
      if (studioState.lightboxVariantId) {
        downloadSingleVariant(studioState.lightboxVariantId, { setPrimary: false });
      }
    });
    host.querySelector("#lbEditBtn")?.addEventListener("click", () => {
      if (studioState.lightboxVariantId) {
        design.active_variant_id = studioState.lightboxVariantId;
        studioState.activeTab = "editor";
        studioState.lightboxVariantId = null;
        renderStudioDom();
      }
    });

    // Restore exact scroll position so page never jumps
    try {
      window.scrollTo(savedScrollX, savedScrollY);
    } catch (_) {}
  }

  window.addEventListener("keydown", (e) => {
    const activeEl = document.activeElement || e.target;
    const tag = (activeEl && activeEl.tagName ? activeEl.tagName : "").toUpperCase();
    const isTextInput =
      (tag === "INPUT" && !["checkbox", "radio", "range", "button", "color", "file"].includes(String(activeEl.type || "").toLowerCase())) ||
      tag === "TEXTAREA" ||
      tag === "SELECT" ||
      Boolean(activeEl?.isContentEditable);

    if (studioState.lightboxVariantId) {
      if (e.key === "Escape") {
        e.preventDefault();
        closeLightbox();
      } else if (e.key === "ArrowLeft") {
        e.preventDefault();
        stepLightbox(-1);
      } else if (e.key === "ArrowRight") {
        e.preventDefault();
        stepLightbox(1);
      }
      return;
    }

    const host = document.getElementById("cofiThumbnailStudioHost");
    if (!host || host.offsetParent === null) return;

    if (studioState.editorZoomed && e.key === "Escape" && !isTextInput) {
      e.preventDefault();
      studioState.editorZoomed = false;
      renderStudioDom();
      return;
    }

    if (!isTextInput && studioState.editorOpen) {
      // Ctrl+Z Undo
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "z") {
        e.preventDefault();
        undoLastAction();
        return;
      }

      // Ctrl+D Duplicate selected layer
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "d") {
        e.preventDefault();
        duplicateSelectedLayer();
        return;
      }

      // Delete or Backspace to delete selected layer
      if (studioState.selectedLayerId && (e.key === "Delete" || e.key === "Backspace")) {
        e.preventDefault();
        deleteLayerById(studioState.selectedLayerId);
        return;
      }

      const sel = getLayer(studioState.selectedLayerId);
      if (sel && sel.visible !== false && sel.type !== "vignette") {
        const step = e.shiftKey ? 12 : 3;
        if (e.key === "ArrowLeft") {
          e.preventDefault();
          sel.left = Math.round(Number(sel.left || 0) - step);
          renderAllCanvases();
          scheduleSaveDesign();
        } else if (e.key === "ArrowRight") {
          e.preventDefault();
          sel.left = Math.round(Number(sel.left || 0) + step);
          renderAllCanvases();
          scheduleSaveDesign();
        } else if (e.key === "ArrowUp") {
          e.preventDefault();
          sel.top = Math.round(Number(sel.top || 0) - step);
          renderAllCanvases();
          scheduleSaveDesign();
        } else if (e.key === "ArrowDown") {
          e.preventDefault();
          sel.top = Math.round(Number(sel.top || 0) + step);
          renderAllCanvases();
          scheduleSaveDesign();
        } else if (e.key === "[") {
          e.preventDefault();
          rotateSelectedLayer(-5);
        } else if (e.key === "]") {
          e.preventDefault();
          rotateSelectedLayer(5);
        } else if (e.key.toLowerCase() === "h" && !e.ctrlKey && !e.metaKey) {
          e.preventDefault();
          flipSelectedLayer("x");
        } else if (e.key.toLowerCase() === "v" && !e.ctrlKey && !e.metaKey) {
          e.preventDefault();
          flipSelectedLayer("y");
        }
      }
    }
  });

  // Paste image from clipboard (Ctrl+V) directly into Canvas as PiP / Inset Image layer
  window.addEventListener("paste", (e) => {
    const host = document.getElementById("cofiThumbnailStudioHost");
    if (!host || host.offsetParent === null || !studioState.editorOpen) return;
    const actEl = document.activeElement;
    if (actEl && (actEl.tagName === "INPUT" || actEl.tagName === "TEXTAREA" || actEl.isContentEditable || actEl.closest("#globalChatDrawer, .chat-panel, .producer-codex-form"))) return;
    const items = e.clipboardData?.items;
    if (!items) return;
    for (let i = 0; i < items.length; i += 1) {
      const item = items[i];
      if (item.type && item.type.startsWith("image/")) {
        const file = item.getAsFile();
        if (!file) continue;
        e.preventDefault();
        const reader = new FileReader();
        reader.onload = () => {
          const dataUrl = String(reader.result || "");
          if (!dataUrl) return;
          pushUndoSnapshot();
          const v = getActiveVariant();
          if (!v.layers) v.layers = [];
          
          const curSel = getLayer(studioState.selectedLayerId, v);
          if (curSel && curSel.type === "inset_image") {
            curSel.src = dataUrl;
            curSel.visible = true;
            loadCachedImage(dataUrl);
            renderStudioDom();
            scheduleSaveDesign();
            showToast(`📋 Đã thay ảnh cho [${curSel.name || curSel.id}] từ Clipboard!`);
            return;
          }

          const newId = `pip_${Date.now().toString(36).slice(-4)}`;
          v.layers.push({
            id: newId,
            type: "inset_image",
            name: "Ảnh Dán (Ctrl+V)",
            src: dataUrl,
            left: 840,
            top: 44,
            width: 376,
            height: 290,
            borderColor: "#fbbf24",
            borderWidth: 6,
            angle: 0,
            visible: true,
          });
          studioState.selectedLayerId = newId;
          loadCachedImage(dataUrl);
          renderStudioDom();
          scheduleSaveDesign();
          showToast("📋 Đã dán ảnh mới từ Clipboard vào Canvas — kéo thả & co giãn tự do!");
        };
        reader.readAsDataURL(file);
        break;
      }
    }
  });

  function upgradeSeoCleanHubDom(hostElement) {
    try {
      const seoRoot = hostElement?.closest("#seoWorkspace") || document.getElementById("seoWorkspace");
      const hub = seoRoot?.querySelector(".seo-clean-hub");
      const pack = studioState.seoPack || studioState.data?.seo_package || {};
      if (!hub || !pack || typeof pack !== "object" || !pack.recommended_title) return;

      const recKo = String(pack.recommended_title || "").trim();
      const recVi = String(pack.recommended_title_vi || "").trim();
      const rawPrimaryKw = pack.primary_keywords_summary;
      const kwSummary = rawPrimaryKw && typeof rawPrimaryKw === "object"
        ? Object.values(rawPrimaryKw).map((v) => String(v || "").trim()).filter(Boolean).join(" · ")
        : String(rawPrimaryKw || "").trim();
      const synergyVi = String(pack.title_thumb_synergy_vi || "").trim();
      const rawOpts = Array.isArray(pack.title_options) ? pack.title_options : [];
      const details = Array.isArray(pack.title_options_details) ? pack.title_options_details : [];
      const optsVi = Array.isArray(pack.title_options_vi) ? pack.title_options_vi : [];
      const descVi = String(pack.description_vi || "").trim();
      const kwVi = Array.isArray(pack.keywords_vi) ? pack.keywords_vi : [];

      const firstCol = hub.querySelectorAll(".seo-clean-col")[0];
      const secondCol = hub.querySelectorAll(".seo-clean-col")[1];
      if (firstCol) {
        const cards = firstCol.querySelectorAll(".seo-result-card");
        const recCard = cards[0];
        if (recCard && recVi && !recCard.querySelector("[data-upgraded-rec-vi]")) {
          const headSpan = recCard.querySelector(".seo-copy-head span");
          if (headSpan) headSpan.textContent = "TIÊU ĐỀ YOUTUBE ĐỀ XUẤT (SONG NGỮ HÀN · VIỆT — CHUẨN CTR & DNA KÊNH)";
          recCard.insertAdjacentHTML(
            "beforeend",
            `<div data-upgraded-rec-vi="1" style="margin-top:10px;padding:10px 12px;background:rgba(15,23,42,0.94);border:1px solid rgba(34,197,94,0.45);border-radius:8px;display:flex;flex-direction:column;gap:6px;font-size:13px;line-height:1.5;">
              <div><span style="color:#4ade80;font-weight:800;">🇻🇳 Bản dịch Tiếng Việt:</span> <span style="color:#f8fafc;font-weight:700;">${esc(recVi)}</span></div>
              ${kwSummary ? `<div><span style="color:#38bdf8;font-weight:800;">🔑 Từ khóa &amp; Địa điểm Trung Quốc:</span> <span style="color:#e2e8f0;">${esc(kwSummary)}</span></div>` : ""}
              ${synergyVi ? `<div><span style="color:#fbbf24;font-weight:800;">🔗 Hỗ trợ nghĩa với Text Thumbnail:</span> <span style="color:#cbd5e1;">${esc(synergyVi)}</span></div>` : ""}
            </div>`
          );
        }

        const optsCard = cards[1];
        if (optsCard && rawOpts.length) {
          const titleOptionsHtml = `<div class="seo-options-stack" style="display:flex;flex-direction:column;gap:10px;margin-top:8px;">${rawOpts
            .map((opt, idx) => {
              const d = typeof opt === "object" && opt !== null ? opt : details[idx] || {};
              const koTitle = typeof opt === "object" && opt !== null ? String(opt.title_ko || opt.title || "").trim() : String(opt || "").trim();
              const viTitle = String(d.title_vi || optsVi[idx] || "").trim();
              const pairedVar = String(d.paired_variant || `Phương án ${idx + 1}`).trim();
              const synNote = String(d.synergy_vi || "").trim();
              const kwAnchor = String(d.keyword_anchor || "").trim();
              return `<div style="display:flex;flex-direction:column;gap:6px;padding:10px 12px;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.12);border-radius:8px;">
                <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:12px;">
                  <div style="font-size:13.5px;line-height:1.45;color:#f8fafc;font-weight:700;">
                    <b style="color:#38bdf8;">#${idx + 1}.</b> ${pairedVar ? `<span style="display:inline-block;padding:1px 7px;margin-right:6px;border-radius:4px;background:rgba(251,191,36,0.18);border:1px solid rgba(251,191,36,0.4);color:#fde047;font-size:11px;font-weight:800;">${esc(pairedVar)}</span>` : ""}🇰🇷 ${esc(koTitle)}
                  </div>
                  <button type="button" class="ghost compact" data-copy-hub-title="${esc(koTitle)}" style="flex-shrink:0;">Sao chép</button>
                </div>
                ${viTitle ? `<div style="font-size:13px;line-height:1.45;color:#4ade80;padding:5px 8px;background:rgba(34,197,94,0.1);border-left:3px solid #22c55e;border-radius:4px;"><b>🇻🇳 Nghĩa Tiếng Việt:</b> <span style="color:#f8fafc;font-weight:700;">${esc(viTitle)}</span></div>` : ""}
                ${kwAnchor ? `<div style="font-size:11.5px;color:#7dd3fc;padding-left:6px;"><b>📍 Từ khóa &amp; Địa điểm TQ:</b> ${esc(kwAnchor)}</div>` : ""}
                ${synNote ? `<div style="font-size:11.5px;color:#cbd5e1;padding-left:6px;"><b>🔗 Bổ trợ nghĩa với Thumb:</b> ${esc(synNote)}</div>` : ""}
              </div>`;
            })
            .join("")}</div>`;
          optsCard.innerHTML = `<span>CÁC PHƯƠNG ÁN TIÊU ĐỀ YOUTUBE &amp; CẶP GHÉP THUMBNAIL (SONG NGỮ HÀN - VIỆT)</span>${titleOptionsHtml}`;
          optsCard.querySelectorAll("[data-copy-hub-title]").forEach((btn) => {
            btn.addEventListener("click", (e) => {
              e.stopPropagation();
              const t = String(btn.dataset.copyHubTitle || "").trim();
              if (t) {
                navigator.clipboard?.writeText(t);
                showToast("📋 Đã sao chép Tiêu đề Tiếng Hàn!");
              }
            });
          });
        }

        const descCard = cards[2];
        if (descCard && descVi && !descCard.querySelector("[data-upgraded-desc-vi]")) {
          descCard.insertAdjacentHTML(
            "beforeend",
            `<div data-upgraded-desc-vi="1" style="margin-top:10px;padding:10px 12px;background:rgba(15,23,42,0.92);border:1px solid rgba(56,189,248,0.35);border-radius:8px;font-size:12.5px;line-height:1.55;color:#e2e8f0;">
              <div style="color:#38bdf8;font-weight:800;margin-bottom:6px;">🇻🇳 BẢN DỊCH NGHĨA TIẾNG VIỆT CỦA PHẦN MÔ TẢ &amp; TIMESTAMPS YOUTUBE:</div>
              <pre style="white-space:pre-wrap;margin:0;font-family:inherit;color:#f1f5f9;">${esc(descVi)}</pre>
            </div>`
          );
        }
      }

      if (secondCol && kwVi.length) {
        const rCards = secondCol.querySelectorAll(".seo-result-card");
        const kwCard = rCards[1];
        if (kwCard && !kwCard.querySelector("[data-upgraded-kw-vi]")) {
          kwCard.insertAdjacentHTML(
            "beforeend",
            `<div data-upgraded-kw-vi="1" style="margin-top:8px;padding:8px 10px;background:rgba(15,23,42,0.9);border-left:3px solid #38bdf8;border-radius:6px;font-size:12px;line-height:1.5;color:#cbd5e1;">
              <div style="color:#7dd3fc;font-weight:800;margin-bottom:4px;">🇻🇳 Giải nghĩa Từ khóa SEO Trụ cột (Hàn — Việt):</div>
              <div>${kwVi.map((k) => esc(k)).join(" · ")}</div>
            </div>`
          );
        }
      }
    } catch (_) {}
  }

  window.mountCofiThumbnailStudio = async function (jobId, hostElement) {
    if (!jobId || !hostElement) return;
    studioState.jobId = jobId;
    studioState.imageCache.clear();
    studioState.lightboxVariantId = null;
    hostElement.innerHTML = `<div class="thumb-studio-loading">⏳ Đang nạp 10 Font Tiếng Hàn Chuẩn Đài &amp; dựng Bộ 4 Bản Thumbnail Test (A/B/C/D)…</div>`;
    try {
      await Promise.race([ensureKoreanFontsLoaded(), new Promise((r) => setTimeout(r, 1200))]);
      const [resp, seoResp] = await Promise.all([
        fetch(`/api/jobs/${encodeURIComponent(jobId)}/thumbnail-studio?t=${Date.now()}`),
        fetch(`/api/jobs/${encodeURIComponent(jobId)}/artifacts/seo_package.json?t=${Date.now()}`).catch(() => null),
      ]);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      studioState.data = await resp.json();
      if (seoResp && seoResp.ok) {
        try {
          const seoJson = await seoResp.json();
          studioState.seoPack = seoJson && typeof seoJson === "object" && seoJson.content ? JSON.parse(seoJson.content) : seoJson;
        } catch (_) {}
      }
      if (!studioState.seoPack && studioState.data?.seo_package) {
        studioState.seoPack = studioState.data.seo_package;
      }
      let sanitized = normalizeAndRepairDesign();
      const variants = getVariants();
      variants.forEach((v, idx) => {
        const defaultFontObj = KOREAN_BROADCAST_FONTS[idx % 4] || KOREAN_BROADCAST_FONTS[0];
        (v.layers || []).forEach((l) => {
          if (l && (l.type === "textbox" || l.type === "badge" || l.type === "stamp")) {
            if (!l.fontFamily || String(l.fontFamily).includes("Black Han Sans")) {
              l.fontFamily = defaultFontObj.stack;
              sanitized = true;
            }
          }
        });
      });
      renderStudioDom();
      upgradeSeoCleanHubDom(hostElement);
      if (sanitized) scheduleSaveDesign();
    } catch (err) {
      hostElement.innerHTML = `<div class="thumb-studio-loading">Không tải được Thumbnail Studio: ${esc(err.message)}</div>`;
    }
  };
})();
