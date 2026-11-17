# COFI DOCUMENTARY — Bộ Nhớ Kiến Trúc & Định Tuyến Luồng Thực Thi

## 1. Phân Tách Cứng 2 Chế Độ Trong Chat (TUYỆT ĐỐI KHÔNG NHẦM LẪN)

### Chế độ A — Thực Thi & Xử Lý Lỗi Dây Chuyền Sản Xuất Video (Mặc định khi đang chọn `selected_job`)
- Khi người dùng hỏi tiến độ, sửa nội dung (`script`, `voice`, `footage`, `vox`, `subtitle`, `thumbnail`) hoặc báo lỗi các khâu sản xuất (`preview edit không thấy gì`, `xuất video lỗi`, `lệch đồng bộ`, `voice lỗi`, `footage dính logo`...):
  1. **CẤM TUYỆT ĐỐI đọc mã nguồn hệ thống & thư viện lõi** (`documentary/*.py`, `services/*.py`, `static/*.js`, `COFI_BRAIN/*.py`, `CofiRemotion/scripts/*`, hoặc đọc tràn các thư viện lõi `CofiRemotion/src/vox-studio/vox-editorial-desk/index.tsx` [7.500+ dòng], `src/vox-studio/china-crime-newsroom/*` [2.000+ dòng], `src/components/*`, `src/utils/*`, hay thư mục của vụ án khác).
  2. Đọc trực tiếp **`TRẠNG THÁI APP HIỆN TẠI`** (`selected_job.state_ledger`, `selected_job.live_diagnostics`, `live_progress`) và **`🎯 ĐỊNH VỊ PHẪU THUẬT TỰ ĐỘNG TRÊN ĐĨA`** đã được bơm sẵn trong prompt.
  3. Chỉ thao tác trên đúng thư mục dự án đang mở: `workspaces/<job_id>/` (và duy nhất bộ file của chính dự án đó tại `CofiRemotion/src/<ThisCase>*.tsx` + `src/vox-studio/<this-case>/`). Nếu vướng lỗi prop/TypeScript Remotion: chỉ đọc lát cắt 25 dòng tại đúng số dòng báo lỗi trong `part-0001.log` và chạy đúng 1 lệnh `npx tsc --noEmit` trong `B:\ALL_TOOLS\CofiRemotion` để bắt toàn bộ lỗi kiểu dữ liệu trong 3 giây (cấm đọc dò bằng mắt hàng nghìn dòng thư viện!).

| Khâu Pipeline | File Dữ Liệu & Log Của Dự Án (`workspaces/<job_id>/`) | API Điều Khiển Tức Thì (`http://127.0.0.1:8878`) |
| :--- | :--- | :--- |
| **1. Kịch bản (`plan`)** | `input.json`, `research.md`, `outline.json`, `script.md`, `.producer/plan/events.jsonl` | `PUT /api/jobs/{id}/script`, `PATCH /api/jobs/{id}/outline`, `POST /api/jobs/{id}/rerun/plan` |
| **2. Giọng đọc (`voice`)** | `voice_manifest.json`, `narration.srt`, `audio/beats_raw/<Bxxx>.wav`, `audio/beats/<Bxxx>.wav`, `voice_qc_report.json` | `PATCH /api/jobs/{id}/voice`, `POST /api/jobs/{id}/rerun/voice` (CofiVoice port `8000`) |
| **3. Phân cảnh (`visuals`)** | `visual_manifest.json`, chỉ mục nhẹ `beats_index.json`, mảnh lẻ `beats/<beat_id>.json` | `GET/PATCH /api/jobs/{id}/beats/{beat_id}` (chỉ đọc/sửa đúng mảnh beat cần sửa) |
| **4A. Tư liệu (`footage`)** | `footage_approved_live.json`, `footage_hygiene_report.json`, `media/footage/sources/`, `media/footage/probes/` | `python -m documentary.edit_footage_fetcher`, `POST /api/jobs/{id}/rerun/footage` |
| **4B. Ảnh/Video AI (`ai_visual`)** | `ai_visual_manifest.json`, `media/ai_visual/` | `POST /api/jobs/{id}/rerun/ai_visual` |
| **5. Dựng & Preview (`edit` / `vox`)** | `edit_progress.json`, `edit_checkpoint.json`, `timeline.json` + file riêng của job tại `CofiRemotion/src/<Case>.tsx`, `<Case>Data.ts`, `src/vox-studio/<case>/` | `GET /api/jobs/{id}/remotion`, `POST /api/jobs/{id}/remotion/start` (Preview port `8890`), `POST /api/jobs/{id}/edit-chat` |
| **6. SEO & Thumbnail (`seo`)** | `seo_package.json`, `thumbnail_design.json`, `thumbnail.jpg`, `media/thumbnail/thumbnail_v1..v4.jpg` | `GET /api/jobs/{id}/thumbnail-studio`, `POST .../thumbnail-studio/auto-design`, `POST /api/jobs/{id}/rerun/seo` |
| **7. Xuất MP4 (`qc`)** | `export_progress.json`, `.render_cache/logs/part-0001.log`, `logs/qc.log`, `final_manifest.json`, `release/video.mp4` | `GET /api/jobs/{id}/export-progress`, `GET /api/jobs/{id}/logs/qc`, `POST /api/jobs/{id}/rerun/qc` |

---

### Chế độ B — Sửa Code / Nâng Cấp Ứng Dụng (`@dev` / `@debug` — Chỉ bật khi người dùng yêu cầu fix app / sửa code)
- Khi người dùng yêu cầu sửa tính năng/giao diện/bug mã nguồn của app:
  1. Tra ngay **Cây Thư Mục Bộ Nhớ Mã Nguồn** dưới đây + tọa độ dòng `StartLine..EndLine` trong **`🛠️ BẢN ĐỒ ĐỊNH VỊ MÃ NGUỒN PHẪU THUẬT`** (`.producer/repo_code_index.json`).
  2. Chỉ dùng `read_file(Path, StartLine, EndLine)` mở đúng **1–2 file trực tiếp phụ trách** tính năng đó. **CẤM TUYỆT ĐỐI** đọc trọn file lớn (`service.py`, `app.js`, `prompts.py`) hoặc quét hàng loạt file trong repo!

```text
B:\ALL_TOOLS\CofiDocumentary\                  # Root ứng dụng điều phối sản xuất
├── app.py / server.py / desktop_app.py        # FastAPI routes (/api/*) & cửa sổ PyWebView desktop
├── documentary/
│   ├── service.py                             # DocumentaryService: vòng đời job, API handlers, context chat, export finalize
│   ├── goal_session.py                        # Phiên Antigravity CLI liên tục, nén chat (/compact), xoay phiên & handoff_summary.txt
│   ├── workspace_ledger.py                    # Sổ cái state_ledger.json, beat shards (beats/<id>.json), chẩn đoán lỗi & định vị code
│   ├── prompts.py                             # Prompt builder cho 8 phase sản xuất & điều phối chat
│   ├── hot_reload.py                          # Tự động nạp nóng (2s/lần) mã nguồn Python & vá JS trực tiếp không tắt app
│   ├── radar.py / topic_research.py           # Quét chủ đề CofiRadar, lọc trùng Topic Memory & kiểm chứng tên vụ án thật
│   ├── script.py                              # Xử lý dàn ý 5 Hồi (outline.json) & kịch bản văn nói (script.md)
│   ├── voice.py / editorial_voice_cutter.py   # Gọi CofiVoice TTS, cắt nhịp thở tự nhiên & đồng bộ voice_manifest.json + SRT
│   ├── visuals.py                             # Chia beat 1-1 theo câu thoại & định tuyến 3 tầng (REAL_FTG -> VOX -> AI_4D)
│   ├── footage.py / edit_footage_fetcher.py   # Tải nguồn, tạo bảng lưới 100px STORYBOARD/GRID & cắt clip tư liệu sạch logo
│   ├── ai_visual.py / cofi_studio_embed.py    # Điều khiển Google Labs Flow tạo ảnh/video AI & tách nền vật chứng RGBA
│   ├── vox_engine/                            # Composable scene graph, semantic router & 10 Editorial Desk archetypes cho VOX
│   ├── edit.py / remotion.py                  # Dựng timeline Remotion, kiểm tra đồng bộ beat & quản lý Remotion Studio Preview
│   ├── render_cache.py / render_progress.py   # Render phân mảnh nền, quản trị phần cứng CPU/VRAM & theo dõi tiến độ xuất MP4
│   ├── thumbnail_studio.py / seo.py           # Thiết kế Thumbnail phân lớp (PIL + Fabric.js), kiểm tra CTR 168x94 & đóng gói SEO
│   ├── critic_loops.py / quality.py           # Cảm biến kiểm định tự động từng bước (ASR, Motion Energy, dHash, LUFS, QC MP4)
│   └── agent_manager.py / nexus_coordinator.py# Quản lý 15 Agent chuyên trách (agents/<division>/<id>.md) & Handoff Bus
├── services/                                  # Hồ sơ kênh cách ly (channel_profile_service.py), editing_dna_service.py, case_similarity.py
├── COFI_BRAIN/                                # chat_run_manager.py (luồng SSE chat), permission_gateway.py, source_repair_agent.py
└── static/
    ├── app.js / styles.css                    # Giao diện chính (Sidebar, 8 Tab sản xuất, Hộp Chat Antigravity bên phải)
    └── thumbnail_studio.js                    # Canvas chỉnh sửa Thumbnail đa lớp Fabric.js

B:\ALL_TOOLS\CofiRemotion\                     # Engine dựng & kết xuất video Remotion
├── src/vox-studio/vox-editorial-desk/index.tsx# Component chuẩn Bàn biên tập cắt dán 12fps (<Desk>, <SlideIn>, <OpticalLoupe>...)
├── src/components/                            # GeoJson3DMapStage.tsx (Bản đồ 3D), FramelessCinemaTextBeat.tsx, SubtitleOverlay.tsx
└── scripts/                                   # turbo-nvenc-export.mjs (Xuất NVENC đa luồng), validate-vox-newsroom-ast.mjs (Cổng AST)
```

<!-- trail:start -->
## Trail — BẮT BUỘC Tra cứu Đồ thị Ký hiệu & Learnings Trước Khi Đọc Code (Chế độ B)
- Khi cần tìm hàm, luồng gọi hoặc schema chưa có sẵn tọa độ dòng trong `repo_code_index.json`, **BẮT BUỘC gọi MCP `trail` (`CofiDocumentary`) hoặc `trail_remotion` (`CofiRemotion`) trước tiên** (gọi thẳng `call_mcp_tool`, không cần đọc lại file schema JSON):
  - `trail_file_api`: `{"file": "documentary/service.py"}` (lấy toàn bộ chữ ký hàm + `Lstart-Lend`, rẻ hơn ~12× so với đọc file).
  - `trail_find_code`: `{"query": "<từ khóa hoặc tên hàm>", "limit": 5}` (lấy kèm `.trail/learnings/` + đoạn code trọng tâm).
  - `trail_find_all`: `{"pattern": "<tên_biến_hoặc_hàm>"}` | `trail_trace_calls`: `{"symbol": "<tên_hàm>", "direction": "in"}`.
- Tuyệt đối không chạy `rg` / `Select-String` quét mù hay `read_file` nguyên file lớn khi chưa tra `trail`.
<!-- trail:end -->
