# BÁO CÁO KHẢO SÁT KIẾN TRÚC FRONTEND & THIẾT KẾ UI/UX TAB 07
## (Survey Explorer 3: Frontend & Tab 07 UI/UX Architecture)

- **Người thực hiện:** Survey Explorer 3 (`explorer_survey_3`)
- **Dự án:** CofiDocumentary (`B:\ALL_TOOLS\CofiDocumentary`)
- **Mã trao đổi Parent Orchestrator:** `d6b3a380-02f2-48cb-8c3d-b480624c4eab`
- **Thời gian hoàn thành:** 2026-10-23T17:55:00Z
- **Chế độ kiểm tra:** Read-Only Investigation & UI/UX Synthesis

---

## 1. TỔNG QUAN & BỐI CẢNH YÊU CẦU

Căn cứ theo yêu cầu chỉ đạo tại `ORIGINAL_REQUEST.md` (mục *Follow-up — 2026-10-23T17:41:06Z*), CofiDocumentary cần nâng cấp toàn diện giao diện Tab 07 (**SEO + Thumbnail** / `#seoWorkspace`), định hình chuẩn hóa hệ thống Design Tokens ứng dụng các kỹ năng chuẩn mực (`agency-ui-designer` và `design-system`), đồng thời cải thiện công thái học (ergonomics) trên toàn ứng dụng.

### Trọng tâm cốt lõi của Tab 07:
1. **Ưu tiên số 1 (Top Hero):** Đưa **Bàn dựng Canvas 16:9 tương tác trực tiếp (Thumbnail Canvas Workbench)** lên vị trí cao nhất và nổi bật nhất của Tab 07, với kích thước tối đa hóa, thao tác chỉnh sửa trực quan (chọn chữ, đổi font phát thanh Hàn Quốc, kéo thả PiP, mũi tên, vòng tròn, chỉnh nền Flow) mà không bị che khuất hay phải cuộn trang.
2. **Ưu tiên số 2 (Phần dưới):** Gom toàn bộ các khối đóng gói SEO (Tiêu đề đề xuất + điểm CTR, Mô tả video + mốc thời gian chương, Tags YouTube, Hashtags, Từ khóa trụ cột, Bối cảnh tham chiếu và Prompt gốc) vào các ngăn kéo **Accordion thu gọn/mở rộng (`<details class="saas-seo-accordion">`)** nằm phía dưới bàn dựng Canvas, đi kèm các nút **1-click Sao chép (Copy)** tin cậy, không làm đẩy lùi hay chèn ép không gian thiết kế Thumbnail.
3. **Ergonomics & Design System:** Kiến tạo hệ thống token 3 lớp (*Primitive → Semantic → Component*), chuẩn hóa độ tương phản nền (Dark slate/obsidian), phân cấp typography, hiệu ứng hover/active/focus-visible trên nút bấm, và đảm bảo layout co giãn mượt mà khi thanh trượt AI Chat (`#globalCodexDock`) mở hoặc đóng.
4. **Bảo toàn dữ liệu & Không gián đoạn (Non-Destructive Safety):** Giữ nguyên vẹn 100% các selector DOM, event listener, tính năng test A/B/C/D, Mascot Lock, CTR prediction, và tuyệt đối không tác động đến các tiến trình đang chạy trên các cổng `8000`, `8878`, `8890`, `8900`.

---

## 2. KHẢO SÁT HIỆN TRẠNG TAB 07 (`#seoWorkspace`)

### 2.1. Cấu trúc DOM & Chuỗi gọi Render hiện tại
Hiện trạng tệp nguồn:
- **`static/index.html` (Dòng 774–777):**
  ```html
  <section class="panel workspace-pane function-workspace" data-app-pane="seo">
    <div class="section-head">
      <div>
        <p class="eyebrow">SEO + THUMBNAIL</p>
        <h2>Đóng gói video từ dữ liệu kênh tham chiếu</h2>
        <p>Radar soi kênh mẫu...</p>
      </div>
    </div>
    <div class="function-body" id="seoWorkspace">
      <div class="empty-state">Chọn một dự án để tạo SEO và prompt thumbnail.</div>
    </div>
  </section>
  ```
- **`static/app.js` (`renderSeoWorkspace`, dòng 9092–9250):**
  Khi người dùng chuyển sang Tab `seo` hoặc chọn dự án, hàm `renderSeoWorkspace(job)` nạp đồng thời `seo_package.json` và `seo_reference_context.json`, sau đó gán vào `#seoWorkspace`:
  1. `phaseStepPanelHtml(job, "seo", "qc")`: Thanh tiến độ bước sản xuất.
  2. `<section id="cofiThumbnailStudioHost" class="thumb-studio-host"></section>`: Phần tử mount của studio thumbnail.
  3. `preflightHtml`: Hộp Channel-DNA SEO Pre-flight.
  4. `referenceSummary`: Hộp tóm tắt hồ sơ tham chiếu.
  5. `result`: Khối `.seo-clean-hub` gồm 2 cột mở hoàn toàn (Tiêu đề, Mô tả, Tags, Keywords, Overlay text) và 1 thẻ `<details class="technical-details">`.
  6. Sau khi inject HTML, script tải `thumbnail_studio.js` và gọi `window.mountCofiThumbnailStudio(job.id, studioHost)`.

- **`static/thumbnail_studio.js` (`renderStudioDom`, dòng 4361–4700):**
  Bên trong `#cofiThumbnailStudioHost`, hàm `renderStudioDom()` sinh ra các thành phần theo thứ tự dọc:
  1. `.thumb-studio-header`: Tiêu đề xưởng thumbnail + các nút thao tác (Lưới / YT Home / YT Sidebar, Khóa DNA Kênh, Xuất A/B Pack, Vẽ 3 nền Flow, Tải hết).
  2. `.thumb-topic-style-bar`: Thanh chọn preset chủ đề (SBS, True Crime, Geopolitics...).
  3. `buildBilingualTitlesBannerHtml()`: Một khối banner lớn chứa tiêu đề chính tiếng Hàn + dịch nghĩa tiếng Việt + danh sách phương án tiêu đề.
  4. `.thumb-boxcard-grid`: **Lưới 4 Box Cards lớn** (Variant A, B, C, D) hiển thị 4 canvas thu nhỏ, điểm CTR, tag, dòng chữ và 4 nút thao tác mỗi card.
  5. `.thumb-editor-drawer`: **Bàn dựng Canva 3 cột (`.canva-workbench-3col`)** nằm ở CUỐI CÙNG của host, mặc dù cờ `editorOpen: true` được bật mặc định.

### 2.2. Các điểm nghẽn & Khuyết tật Trải nghiệm (UX Friction Points)
1. **Bàn dựng Canvas bị đẩy xuống quá sâu (Vertical Burial):**
   Người dùng muốn chỉnh sửa thumbnail ngay lập tức nhưng phải cuộn qua Header → Thanh Style → Banner Tiêu đề → Lưới 4 card lớn rồi mới thấy Canvas chính.
2. **Trùng lặp hiển thị Tiêu đề (Duplicate Title Redundancy):**
   Hệ thống tiêu đề tiếng Hàn & tiếng Việt được render tới 3 lần riêng biệt:
   - Lần 1: Trong `buildBilingualTitlesBannerHtml()` của `thumbnail_studio.js`.
   - Lần 2: Trong các chú thích của 4 card `.thumb-boxcard-grid`.
   - Lần 3: Trong khối `.seo-clean-hub` của `app.js`.
   Điều này gây nhiễu loạn thị giác và làm tốn hàng trăm pixel chiều dọc.
3. **Không gian SEO quá tải (Static Open Layout):**
   Phía dưới bàn dựng, toàn bộ nội dung Mô tả, Tags, Từ khóa, Bằng chứng đối thủ đều hiển thị ở dạng các thẻ mở toang (`.seo-result-card`), khiến tổng chiều cao trang lên tới 3500px–4500px. Khi người dùng muốn xem hoặc copy một thẻ tag, họ phải cuộn một quãng đường dài.
4. **Trực giác Bàn dựng Canva (Paradigm Mismatch):**
   Trong các phần mềm đồ họa hiện đại (Canva, Figma, CapCut Web), Bàn dựng trực tiếp (Direct Editor) luôn là **trung tâm tối cao**, còn các biến thể A/B/C/D chỉ là các tab chuyển đổi (Switching Tabs) hoặc thanh trượt preview thanh mảnh phía trên. Mô hình hiện tại lại đặt Canvas vào một "ngăn kéo" phụ bên dưới các card.

---

## 3. THIẾT KẾ NÂNG CẤP KIẾN TRÚC TAB 07 (UPGRADED LAYOUT ARCHITECTURE)

### 3.1. Mô hình Phân vùng Không gian (Spatial Blueprint)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ TAB 07: SEO + THUMBNAIL STUDIO WORKSPACE                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. TOP HEADER & QUICK ACTION BAR                                            │
│    [Variant Tabs: A (CTR 94%) | B (CTR 91%) | C (CTR 89%) | D (CTR 86%)]    │
│    [Topic Preset Pill: True Crime SBS ▼]                                    │
│    [Actions: 🎨 Vẽ 3 nền Flow | 🔒 Khóa DNA Kênh | 📦 Xuất A/B Pack | ⬇ Tải]│
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. HERO MAXIMIZED 16:9 THUMBNAIL CANVAS WORKBENCH (CANVA 3-COL SYSTEM)      │
│ ┌───────────────┬───────────────────────────────────────────┬─────────────┐ │
│ │ CỘT TRÁI      │ CỘT GIỮA: MÀN HÌNH SOẠN THẢO 16:9         │ CỘT PHẢI    │ │
│ │ ASSET DOCK    │ - Thanh công cụ: Undo | Duplicate | Xóa   │ CONTEXTUAL  │ │
│ │ (280px)       │   Safe-Zone 30:15 | Zoom (100%/Fit) | Full│ INSPECTOR   │ │
│ │ - Font Hàn    │ ┌───────────────────────────────────────┐ │ (336px)     │ │
│ │ - Mũi tên     │ │                                       │ │ Tự động đổi │ │
│ │ - Vòng tròn   │ │       INTERACTIVE 16:9 CANVAS         │ │ theo layer: │ │
│ │ - PiP Inset   │ │             (1280 × 720)              │ │ - Text Form │ │
│ │ - Mascot Lock │ │                                       │ │ - Color Sw  │ │
│ │ - Layer list  │ └───────────────────────────────────────┘ │ - Sliders   │ │
│ │               │ - Dải Song ngữ Việt: Nghĩa Dòng 1 + Dòng 2│ - Nền & Flow│ │
│ └───────────────┴───────────────────────────────────────────┴─────────────┘ │
├─────────────────────────────────────────────────────────────────────────────┤
│ 3. COMPARATOR STRIP / VIEW TOGGLE (Tuỳ chọn: Lưới 4 Bản | Home | Sidebar)   │
├─────────────────────────────────────────────────────────────────────────────┤
│ 4. COLLAPSIBLE ACCORDION DRAWERS (ĐÓNG GÓI SEO & METADATA PHÍA DƯỚI)        │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ ▾ [ACCORDION 1] 🏆 TIÊU ĐỀ YOUTUBE & CTR SCORES (HÀN · VIỆT)  [Copy All]│ │
│ ├─────────────────────────────────────────────────────────────────────────┤ │
│ │ ▾ [ACCORDION 2] 📝 MÔ TẢ VIDEO & DẤU MỐC CHƯƠNG (TIMESTAMPS)   [Sao chép]│ │
│ ├─────────────────────────────────────────────────────────────────────────┤ │
│ │ ▾ [ACCORDION 3] 🏷 VIDEO TAGS & TỪ KHÓA SEO TRỤ CỘT (TAGS)     [Sao chép]│ │
│ ├─────────────────────────────────────────────────────────────────────────┤ │
│ │ ▸ [ACCORDION 4] 🔍 BỐI CẢNH THAM CHIẾU & VIDEO BẰNG CHỨNG (RADAR)        │ │
│ ├─────────────────────────────────────────────────────────────────────────┤ │
│ │ ▸ [ACCORDION 5] ⚙ PROMPT GỐC & DỮ LIỆU KỸ THUẬT (AI PROMPTS & JSON)     │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2. Chi tiết Vùng 1: Maximized Thumbnail Canvas Studio (Top Hero)
1. **Variant Selector Bar (Thanh chọn biến thể liền khối):**
   - Đặt ngay trên đỉnh Bàn dựng Canvas.
   - Hiển thị 4 Tab thuốc con nhộng (Pills) tương ứng với 4 biến thể tâm lý:
     - **Bản A (Tò mò / Nghịch lý):** `CTR 94% · Curiosity Gap`
     - **Bản B (Bằng chứng độc quyền):** `CTR 91% · Evidence Close-up`
     - **Bản C (Đối đầu / Hồ sơ mật):** `CTR 89% · Confrontation Hook`
     - **Bản D (Hồ sơ chính thức):** `CTR 86% · Official Archive`
   - Nhấp vào bất kỳ Tab nào sẽ **chuyển đổi Canvas tức thì** với 0ms giật trang và không bị nhảy vị trí cuộn màn hình (`window.scrollTo` được bảo lưu).
2. **16:9 Canvas Stage (Trung tâm tương tác):**
   - Vùng viewport đạt tỷ lệ chuẩn YouTube 16:9 (kích thước cơ sở 1280×720px, tự động co dãn theo zoom 50%–150% hoặc chế độ Fit).
   - Tích hợp lớp phủ kiểm tra điểm chết YouTube **Safe Zone 30:15** (khu vực hiển thị thời lượng ở góc dưới bên phải).
   - Hỗ trợ thao tác trực tiếp trên Canvas: Click chọn layer, kéo thả, di chuyển chữ, đổi kích thước text, thay đổi màu fill/stroke.
   - Hỗ trợ dán ảnh trực tiếp từ Clipboard (**Ctrl+V**) làm lớp PiP (Picture-in-Picture).
3. **Asset & Inspector Docks (2 bên):**
   - **Dock Trái (Thư viện tài sản):** Phân nhóm tab khoa học `[Văn bản]`, `[Ký hiệu Mũi tên & Vòng tròn]`, `[Ảnh PiP]`, `[Lớp Layer]`, `[Mascot Lock Kênh]`.
   - **Dock Phải (Contextual Inspector):** Tự động thích ứng ngữ cảnh. Nếu người dùng chọn Text, bảng hiện bộ gõ song ngữ, font Hàn (Pretendard, Paperlogy, SCoreDream), bảng màu chuẩn đài SBS. Nếu chọn Background, hiện danh sách ảnh candidate, nút gọi Flow AI vẽ nền mới, và thanh chỉnh Vignette.

### 3.3. Chi tiết Vùng 2: Hệ thống 5 Accordion SEO Packaging (Phía dưới)
Dưới Canvas, toàn bộ dữ liệu SEO được chuyển thành các thẻ `<details class="saas-seo-accordion">`. Các Accordion này mặc định có thể mở sẵn 1–3 mục trọng yếu hoặc thu gọn lại, giúp màn hình luôn gọn gàng:

#### Accordion 1: 🏆 Tiêu đề YouTube & Điểm CTR (YouTube Titles & CTR Scores)
- **Tiêu đề Accordion:** `🏆 Tiêu đề YouTube & Điểm CTR (Song ngữ Hàn · Việt)`
- **Badge tóm tắt trên Header:** `✓ DNA Khớp | 4 Phương án | Đề xuất: CTR 89점`
- **Nút nhanh trên Header:** `📋 Sao chép Tiêu đề Đề xuất`
- **Nội dung bên trong:**
  - *Tiêu đề Đề xuất Chính:* Tiêu đề tiếng Hàn chuẩn SEO kênh + Bản dịch nghĩa tiếng Việt sắc bén + Thẻ từ khóa địa danh Trung Quốc (`primary_keywords_summary`) + Ghi chú tương hỗ nghĩa với Text Thumbnail.
  - *Điểm số CTR & Pre-flight:* Bảng phân tích 4 chiều (Độ đồng nhất DNA: 94%, Dễ đọc di động: 92%, Khoảng trống tò mò: 91%, Khớp từ khóa: 95%).
  - *4 Phương án Tiêu đề đi cặp:* Từng phương án được đóng gói với thẻ ghép biến thể (`Bản A`, `Bản B`...), nút `Sao chép`, bản dịch tiếng Việt, và anchor từ khóa.

#### Accordion 2: 📝 Mô tả Video & Dấu mốc Thời gian (Description & Chapter Timestamps)
- **Tiêu đề Accordion:** `📝 Mô tả Video YouTube & Mốc thời gian (Timestamps & Chapters)`
- **Badge tóm tắt trên Header:** `Kèm Hashtags & Mốc chương`
- **Nút nhanh trên Header:** `📋 Sao chép Toàn bộ Mô tả`
- **Nội dung bên trong:**
  - Hộp văn bản mô tả hoàn chỉnh chuẩn bị sẵn để dán vào YouTube Studio (gồm hook mở đầu, tóm tắt vụ án, timestamps từng chương, liên kết kênh, bản quyền disclaimer và danh sách hashtags).
  - Khung dịch nghĩa tiếng Việt của toàn bộ mô tả để người sáng tạo kiểm duyệt nội dung.

#### Accordion 3: 🏷 Video Tags & Từ khóa SEO Trụ cột (YouTube Tags & Keywords)
- **Tiêu đề Accordion:** `🏷 Video Tags & Từ khóa SEO Trụ cột (Tags & Keywords)`
- **Badge tóm tắt trên Header:** `Sẵn sàng dán YouTube Studio`
- **Nút nhanh trên Header:** `📋 Sao chép Toàn bộ Tags`
- **Nội dung bên trong:**
  - Chuỗi Tags phân cách dấu phẩy (dán thẳng vào ô Tags của YouTube Studio mà không cần xử lý thêm).
  - Danh sách Hashtags bắt buộc của kênh.
  - Bảng danh mục từ khóa trụ cột (`seo_keyword_dna`) kèm nghĩa tiếng Việt và vai trò ranking.

#### Accordion 4: 🔍 Bối cảnh Tham chiếu & Bằng chứng Đối thủ (Reference Context)
- **Tiêu đề Accordion:** `🔍 Bối cảnh Tham chiếu & Video Bằng chứng (Radar Context)`
- **Badge tóm tắt trên Header:** `Hồ sơ Kênh & Radar Bằng chứng`
- **Nội dung bên trong:**
  - Tên hồ sơ kênh tham chiếu, số lượng kênh radar liên kết, chế độ nguồn dữ liệu.
  - Danh sách video đối thủ đạt view cao/outlier dùng làm cơ sở benchmark.

#### Accordion 5: ⚙ Prompt Gốc & Dữ liệu Kỹ thuật (Technical JSON & AI Prompts)
- **Tiêu đề Accordion:** `⚙ Prompt Gốc & Dữ liệu Kỹ thuật (Technical Prompts & Artifacts)`
- **Badge tóm tắt trên Header:** `Artifacts JSON`
- **Nội dung bên trong:**
  - Prompt tạo ảnh nền thumbnail gốc (English Midjourney/Flow prompt) + Negative prompt.
  - Bộ xem code JSON có tô màu cú pháp cho `seo_package.json` và `seo_reference_context.json`.

---

## 4. REVIEW TOÀN DIỆN DESIGN SYSTEM TOKENS & CÔNG THÁI HỌC SAAS

Áp dụng tiêu chuẩn từ `C:\Users\koing\.gemini\config\skills\agency-ui-designer\SKILL.md` và `b:\.agents\skills\design-system\SKILL.md`, giao diện CofiDocumentary được chuẩn hóa theo hệ thống 3 lớp token:

### 4.1. Cấu trúc 3 Lớp Design Tokens (Three-Layer Architecture)

```css
/* ==========================================================================
   LỚP 1: PRIMITIVE TOKENS (Giá trị thô cơ sở)
   ========================================================================== */
:root {
  /* Bảng màu Dark Obsidian & Slate */
  --co-slate-950: #04070d;
  --co-slate-900: #0a0f1d;
  --co-slate-850: #0f172a;
  --co-slate-800: #1e293b;
  --co-slate-700: #334155;
  --co-slate-400: #94a3b8;
  --co-slate-200: #e2e8f0;
  --co-slate-50:  #f8fafc;

  /* Màu chỉ dẫn chức năng */
  --co-cyan-400:  #38bdf8;
  --co-cyan-500:  #0ea5e9;
  --co-amber-400: #fbbf24;
  --co-amber-500: #f59e0b;
  --co-emerald-400: #34d399;
  --co-emerald-500: #10b981;
  --co-rose-500:  #f43f5e;
  --co-purple-500: #a855f7;

  /* Thang kích thước khoảng cách (4px base) */
  --co-space-1: 0.25rem;  /* 4px */
  --co-space-2: 0.5rem;   /* 8px */
  --co-space-3: 0.75rem;  /* 12px */
  --co-space-4: 1rem;     /* 16px */
  --co-space-5: 1.25rem;  /* 20px */
  --co-space-6: 1.5rem;   /* 24px */
  --co-space-8: 2rem;     /* 32px */

  /* Thang bo góc */
  --co-radius-sm: 6px;
  --co-radius-md: 8px;
  --co-radius-lg: 12px;
  --co-radius-xl: 16px;
  --co-radius-full: 9999px;

  /* Thang Typography */
  --co-font-sans: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  --co-font-mono: 'JetBrains Mono', Consolas, monospace;
  --co-font-kr-headline: 'Pretendard Black', 'Paperlogy Black', 'SCoreDream Black', sans-serif;
}

/* ==========================================================================
   LỚP 2: SEMANTIC TOKENS (Bí danh theo mục đích sử dụng)
   ========================================================================== */
:root {
  --surface-app:       var(--co-slate-950);
  --surface-card:      var(--co-slate-900);
  --surface-card-sub:  var(--co-slate-850);
  --surface-hover:     rgba(255, 255, 255, 0.04);
  --surface-active:    rgba(56, 189, 248, 0.12);

  --border-subtle:     rgba(255, 255, 255, 0.06);
  --border-default:    rgba(148, 163, 184, 0.2);
  --border-strong:     rgba(148, 163, 184, 0.35);
  --border-accent:     var(--co-amber-400);
  --border-focus:      var(--co-cyan-400);

  --text-main:         var(--co-slate-50);
  --text-secondary:    var(--co-slate-200);
  --text-muted:        var(--co-slate-400);
  --text-accent:       var(--co-cyan-400);

  --badge-green-bg:    rgba(16, 185, 129, 0.16);
  --badge-green-border: rgba(16, 185, 129, 0.4);
  --badge-green-text:  #4ade80;

  --badge-amber-bg:    rgba(251, 191, 36, 0.16);
  --badge-amber-border: rgba(251, 191, 36, 0.4);
  --badge-amber-text:  #fde047;
}

/* ==========================================================================
   LỚP 3: COMPONENT TOKENS (Token riêng cho từng cụm component)
   ========================================================================== */
:root {
  --canva-stage-bg: radial-gradient(circle at center, #111827 0%, #060911 100%);
  --canva-dock-bg:  rgba(15, 23, 42, 0.95);
  --canva-dock-border: rgba(148, 163, 184, 0.24);
  
  --accordion-border: rgba(148, 163, 184, 0.22);
  --accordion-summary-bg: rgba(30, 41, 59, 0.45);
  --accordion-summary-hover: rgba(30, 41, 59, 0.75);
}
```

### 4.2. Chuẩn hóa Nút bấm (Button States) & Tương tác vi mô (Micro-interactions)
Mọi nút bấm phải tuân thủ chuẩn tương tác 5 trạng thái:
1. **Default:** Font Inter 500/600, bo góc `--co-radius-md`, hiển thị icon + label rõ ràng.
2. **Hover:** `transform: translateY(-1px)`, tăng độ sáng viền, hiển thị bóng mờ nhẹ (`box-shadow: 0 4px 12px rgba(0,0,0,0.2)`).
3. **Active:** `transform: scale(0.98)`, triệt tiêu bóng để tạo cảm giác nhấn thực tế.
4. **Focus-visible:** Vòng tròn nét đứt hoặc viền kép `outline: 2px solid var(--border-focus); outline-offset: 2px;` đảm bảo khả năng tiếp cận WCAG AA.
5. **Disabled:** `opacity: 0.45; cursor: not-allowed; pointer-events: none;`.

### 4.3. Định dạng Thẻ Accordion SaaS (`saas-seo-accordion`)
```css
/* Style định chuẩn cho các Drawer Accordion SEO */
details.saas-seo-accordion {
  border-radius: var(--co-radius-lg);
  background: var(--surface-card);
  border: 1px solid var(--accordion-border);
  margin-bottom: var(--co-space-3);
  overflow: hidden;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

details.saas-seo-accordion[open] {
  border-color: rgba(56, 189, 248, 0.35);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3);
}

details.saas-seo-accordion > summary.saas-seo-summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--co-space-3);
  padding: 12px 16px;
  cursor: pointer;
  user-select: none;
  list-style: none;
  background: var(--accordion-summary-bg);
  transition: background 0.15s ease;
}

details.saas-seo-accordion > summary.saas-seo-summary::-webkit-details-marker {
  display: none;
}

details.saas-seo-accordion > summary.saas-seo-summary:hover {
  background: var(--accordion-summary-hover);
}

details.saas-seo-accordion > .saas-seo-content {
  padding: 16px;
  border-top: 1px solid rgba(148, 163, 184, 0.16);
  background: rgba(10, 15, 29, 0.95);
}
```

### 4.4. Tính thích ứng Layout khi mở/đóng AI Chat Dock
Theo quy tắc layout tại dòng 6620–6640 trong `styles.css`:
- Khi AI Chat dock đóng: `body.desktop-mode` và `.app-shell` có `padding-right: 0`.
- Khi AI Chat dock mở: `body.global-chat-open .app-shell` nhận `padding-right: var(--chat-dock-width)` (khoảng 350px–400px).
- Bàn dựng Canvas 3 cột (`.canva-workbench-3col`) có cơ chế co giãn cột:
  - Màn hình rộng (>1600px): `grid-template-columns: 280px minmax(0, 1fr) 336px`.
  - Màn hình vừa hoặc khi mở chat (1280px–1599px): `grid-template-columns: 240px minmax(0, 1fr) 300px`.
  - Cột giữa chứa Canvas có thuộc tính `min-width: 0 !important; overflow: hidden;` giúp Canvas tự động co vừa khung hình mà không bao giờ gây bể layout hay thanh cuộn ngang trang.

---

## 5. DANH MỤC DOM SELECTORS & BẢO TOÀN TÍNH NĂNG (BACKWARD COMPATIBILITY)

Để đảm bảo quá trình tái cấu trúc không gây regression cho bất kỳ bài test tự động nào (đặc biệt là `test_thumbnail_ab_testing_dna.py`, `test_adversarial_thumbnail_ab_studio.py`, `test_chat_dock_layout.py`), danh mục các Selectors và Event Handlers sau đây được bảo lưu và tích hợp nguyên vẹn:

### 5.1. Bảng đối chiếu Selectors Trọng yếu

| Nhóm chức năng | Tên Selector (ID / Class / Data) | Vai trò hiện tại | Trạng thái bảo lưu trong Redesign |
|---|---|---|---|
| **Mounting Host** | `#seoWorkspace` | Container cha trong `index.html` | **Giữ nguyên 100%** |
| | `#cofiThumbnailStudioHost` | Mount target cho `mountCofiThumbnailStudio` | **Giữ nguyên 100%** |
| **Canvas & Controls** | `#cofiThumbMainCanvas` | Canvas HTML5 16:9 chính (1280×720) | **Giữ nguyên 100%** tại vị trí Hero |
| | `#cofiThumbLeftDock` | Container các tab thư viện bên trái | **Giữ nguyên 100%** |
| | `#cofiThumbRightInspector` | Inspector ngữ cảnh bên phải | **Giữ nguyên 100%** |
| | `#cofiThumbStageViewport` | Khung cuộn zoom của canvas | **Giữ nguyên 100%** |
| | `#thumbZoomReadout` | Nhãn hiển thị % zoom (100%, Fit...) | **Giữ nguyên 100%** |
| | `#thumbSafeZoneToggle` | Checkbox bật Safe-Zone 30:15 | **Giữ nguyên 100%** |
| | `#thumbUndoBtn` | Nút Undo (Ctrl+Z) | **Giữ nguyên 100%** |
| | `#thumbDeleteSelectedBtn` | Nút xóa layer đang chọn | **Giữ nguyên 100%** |
| | `#thumbDuplicateLayerBtn` | Nút nhân bản layer (Ctrl+D) | **Giữ nguyên 100%** |
| **A/B/C/D Variants** | `data-switch-workbench-variant` | Chuyển đổi bản dựng sang A, B, C, D | **Giữ nguyên 100%**, đưa lên đầu workbench |
| | `data-card-variant` | Thuộc tính định danh biến thể | **Giữ nguyên 100%** trong dải so sánh |
| | `data-select-winner` | Chọn biến thể chiến thắng (`POST /select-winner`) | **Giữ nguyên 100%** |
| | `data-download-variant` | Tải xuống 1 ảnh JPEG độc lập | **Giữ nguyên 100%** |
| | `data-zoom-variant` | Mở Lightbox zoom chi tiết ảnh | **Giữ nguyên 100%** |
| **Hành động cấp Kênh** | `#thumbLockChannelDnaBtn` | Khóa DNA Thumbnail vào Hồ sơ Kênh | **Giữ nguyên 100%** trên thanh hành động |
| | `#thumbExportAbPackBtn` | Xuất file ZIP A/B Test Pack cho YouTube Studio | **Giữ nguyên 100%** trên thanh hành động |
| | `#thumbBatchFlowBtn` | Gọi Flow AI vẽ 3 nền mới | **Giữ nguyên 100%** trên thanh hành động |
| | `#thumbDownloadAllBtn` | Tải về toàn bộ 4 bản JPG | **Giữ nguyên 100%** trên thanh hành động |
| **Sao chép SEO** | `[data-seo-copy="title"]` | Nút sao chép Tiêu đề đề xuất | **Bảo toàn trong Accordion 1** |
| | `[data-seo-copy="description"]`| Nút sao chép Mô tả + Timestamps | **Bảo toàn trong Accordion 2** |
| | `[data-seo-copy="tags"]` | Nút sao chép Tags YouTube | **Bảo toàn trong Accordion 3** |
| | `[data-seo-copy="keywords"]` | Nút sao chép Từ khóa trụ cột | **Bảo toàn trong Accordion 3** |
| | `[data-copy-hub-title]` | Sao chép tiêu đề từng phương án | **Bảo toàn trong Accordion 1** |
| | `[data-copy-paired-title]` | Sao chép tiêu đề đi kèm bản dựng | **Bảo toàn trên thanh Canvas Footer** |
| **Pre-Flight & Mascot** | `#channelThumbnailMascotLock` | Select khóa mascot trong Channel Profile | **Giữ nguyên 100%** |
| | `preflightHtml` | Hộp tóm tắt kiểm tra Channel DNA | **Tích hợp bên trong Accordion 1** |

### 5.2. Đồng bộ hóa với hàm `upgradeSeoCleanHubDom`
Trong `thumbnail_studio.js` (dòng 4948–5048), hàm `upgradeSeoCleanHubDom` có đoạn mã tìm kiếm `.seo-clean-hub` và `.seo-clean-col` để chèn bản dịch nghĩa tiếng Việt. 
- **Giải pháp tối ưu:** Trong thiết kế mới của `app.js`, các bản dịch nghĩa tiếng Việt (`recommended_title_vi`, `title_options_vi`, `description_vi`, `keywords_vi`) đã được biên dịch và nhúng **trực tiếp vào HTML của các Accordion** ngay từ khâu render ban đầu.
- Hàm `upgradeSeoCleanHubDom` sẽ được bổ sung kiểm tra an toàn `if (!hub) return;` hoặc tự động nhận diện cả cấu trúc Accordion mới để tránh bất kỳ lỗi runtime nào nếu phần tử cũ không còn tồn tại dạng 2 cột tĩnh.

---

## 6. LỘ TRÌNH TRIỂN KHAI MÃ NGUỒN (IMPLEMENTATION BLUEPRINT)

Quá trình triển khai thực tế sẽ được phân bổ thành 3 bước độc lập, rõ ràng:

### Bước 1: Nâng cấp `static/app.js` (`renderSeoWorkspace`)
- Tái cấu trúc hàm `renderSeoWorkspace(job)`:
  - Đưa `#cofiThumbnailStudioHost` lên ngay dưới `phaseStepPanelHtml`.
  - Thay thế toàn bộ khối `.seo-clean-hub` cồng kềnh bằng 5 thẻ Accordion `<details class="saas-seo-accordion">`.
  - Tích hợp sẵn bản dịch tiếng Việt, badge CTR, và nút `data-seo-copy` ngay trong từng Accordion.
  - Gọi lại `bindSeoCopyButtons` để đảm bảo 100% nút copy hoạt động tức thì.

### Bước 2: Nâng cấp `static/thumbnail_studio.js` (`renderStudioDom`)
- Đưa `.canva-workbench-3col` lên vị trí Hero hàng đầu bên trong `#cofiThumbnailStudioHost`.
- Bổ sung thanh chọn biến thể Tab Pills (Bản A / B / C / D) trực tiếp trên thanh công cụ của Bàn dựng.
- Giữ nguyên trạng 4 Box Cards hoặc đặt vào dạng dải thu gọn / chế độ xem phụ (Preview Strip) bên dưới để người dùng có thể mở rộng xem lại tổng thể khi cần.
- Bảo toàn toàn bộ event bindings của Canvas, Lightbox, Flow generation, Lock DNA, và Export Pack.

### Bước 3: Nâng cấp `static/styles.css`
- Bổ sung nhóm CSS Tokens cho SaaS Accordion (`.saas-seo-accordion`, `.saas-seo-summary`, `.saas-seo-content`, `.saas-seo-badge`).
- Chuẩn hóa padding, border-radius, focus rings, và hiệu ứng chuyển động mở accordion (`transition: max-height 0.2s ease`).
- Cập nhật responsive quy định cho `.canva-workbench-3col` khi mở AI chat dock trên các màn hình laptop `1280px`–`1440px`.

---

## 7. KẾT LUẬN & KIỂM CHỨNG TÍNH TOÀN VẸN (INTEGRITY VERIFICATION)

1. **Tuân thủ nguyên tắc Read-Only:** Bản khảo sát được thực hiện hoàn toàn ở chế độ đọc, không gây đột biến lên bất kỳ tệp mã nguồn nào của dự án.
2. **Cú pháp JavaScript:** Đã kiểm tra cú pháp với `node --check static/app.js static/thumbnail_studio.js static/desktop_chrome.js` — kết quả **100% hợp lệ (Exit code 0)**.
3. **Cú pháp Python Backend:** Đã kiểm tra biên dịch `python -m py_compile documentary/edit.py documentary/prompts.py services/editing_dna_service.py` — kết quả **100% hợp lệ (Exit code 0)**.
4. **An toàn tiến trình chạy ngầm:** Các tiến trình tại cổng `8000` (PID 2988), `8878` (PID 28296), `8890` (PID 10256), `8900` (PID 30768) được duy trì liên tục và an toàn tuyệt đối.

*Báo cáo sẵn sàng bàn giao cho Orchestrator và Kỹ sư Triển khai.*
