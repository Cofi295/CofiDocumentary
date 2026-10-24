# Visual Pipeline + Full AI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Nâng cấp CofiDocumentary thành pipeline ba nhánh Full AI / Full Footage / Hybrid, thêm phase Visuals/STP sau Voice, cấu hình phong cách ngay khi tạo dự án, và mở AI chat thành trợ lý tổng quát có quyền xử lý mọi yêu cầu trong app.

**Architecture:** `plan -> voice -> visuals -> (footage/ai_visual theo chiến lược) -> edit -> seo -> qc`. `visuals` là nguồn authoritative cho các visual unit bám 100% script, dùng timing Voice/SRT và chia ngắn theo dấu câu, dấu phẩy hoặc cụm nghĩa; Full AI bỏ Footage, Full Footage bỏ AI Visual, Hybrid route từng unit theo nội dung mà không dùng tỷ lệ cứng.

**Tech Stack:** Python 3 + FastAPI/Pydantic, JSON manifests, CofiVoice/CofiStudio integration, vanilla HTML/CSS/JS, pytest, Node syntax check.

## Global Constraints

- UI tiếng Việt, luồng phải nhìn ra ngay nhánh nào sẽ chạy và bước nào bị bỏ qua.
- Full AI có 3 chế độ media: `image`, `video`, `mixed`.
- Hybrid chọn Footage/AI theo câu chuyện, không có quota 80/20.
- Script giữ tự nhiên; Visuals mới chia ngắn để tạo prompt.
- 100% nội dung script phải được ánh xạ vào visual units, không mất câu/đoạn.
- Tích hợp logic STP cục bộ; không gọi API sang app SRT-To-Prompt.
- AI chat không bị khóa role “producer”; phải xử lý được code, nội dung, pipeline, UI, phân tích và thao tác dự án trong cùng session.

---

### Task 1: Recipe + Project Configuration

**Files:** `app.py`, `documentary/quality.py`, `documentary/service.py`, `tests/test_visual_strategy.py`, `tests/test_api.py`.

- [ ] Viết test RED cho ba strategy, Full AI media mode, hybrid không có tỷ lệ cứng và dữ liệu style ở create API.
- [ ] Chạy focused tests để xác nhận fail vì backend còn dùng `footage_first/hybrid`.
- [ ] Đổi normalize/create model sang schema mới; giữ migration cho job cũ `footage_first -> full_footage`.
- [ ] Lưu `ai_media_mode`, style preset/custom/reference settings và coverage phù hợp strategy.
- [ ] Chạy focused tests đến GREEN.

### Task 2: Visuals/STP Phase

**Files:** create `documentary/visuals.py`, modify `documentary/models.py`, `documentary/service.py`, `documentary/prompts.py`, create `tests/test_visuals.py`, modify `tests/test_seo_packaging.py`.

- [ ] Viết test RED cho segmentation giữ 100% normalized script, chia theo punctuation/clause, prompt một dòng một unit và timing tăng dần.
- [ ] Viết test RED cho PHASES có `visuals` ngay sau `voice` và artifact contract mới.
- [ ] Port logic chia nghĩa tối thiểu từ STP thành module cục bộ, không import runtime app cũ.
- [ ] Implement `VisualsCoordinator.run()` đọc SRT/script, tạo visual units và prompt seed/style direction.
- [ ] Wire `visuals` vào service `_run_phase` và artifact validation.
- [ ] Chạy tests đến GREEN.

### Task 3: Branch-aware Pipeline Routing

**Files:** `documentary/service.py`, `documentary/quality.py`, `documentary/prompts.py`, `documentary/ai_visual.py`, `tests/test_service.py`, `tests/test_visual_strategy.py`.

- [ ] Viết test RED cho `next_phase`, previous-phase validation, run_pipeline và resume trên từng strategy.
- [ ] Implement `effective_phases(job)` và dùng nó trong start/resume/run_pipeline/progress thay vì PHASES cứng.
- [ ] Phase bị bỏ qua phải không gọi engine và không chặn downstream.
- [ ] Update prompts/quality để Hybrid story-driven và Full AI media mode điều khiển image/video/mixed.
- [ ] Chạy focused service/strategy tests đến GREEN.

### Task 4: UI Flow + General-purpose AI

**Files:** `static/index.html`, `static/app.js`, `static/styles.css`, `documentary/prompts.py`, `AGENTS.md`, `tests/test_api.py`, `tests/test_seo_packaging.py`.

- [ ] Viết test RED cho HTML/JS có 3 strategy, Full AI submodes, style/reference controls, `visuals` phase label và dynamic flow text.
- [ ] Viết test RED khẳng định AI chat không tự giới hạn scope vào “application itself/producer” và action schema có `visuals`.
- [ ] Nâng create UI thành các card branch rõ ràng; ẩn/hiện cấu hình AI theo strategy và hiển thị flow theo lựa chọn.
- [ ] Gửi payload mới khi tạo project; reference image dùng endpoint/settings hiện hữu sau khi job tạo khi có file.
- [ ] Đổi AI chat prompt thành trợ lý tổng quát full-access, giữ control JSON chỉ làm giao thức host.
- [ ] Update AGENTS.md contract.
- [ ] Chạy syntax checks, pytest focused rồi regression liên quan.
- [ ] Kiểm tra port 8878, restart đúng app nếu cần và xác minh `/api/health` + create-job thật.

