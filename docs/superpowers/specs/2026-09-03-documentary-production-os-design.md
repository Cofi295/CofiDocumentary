# COFI DOCUMENTARY Production OS Design

## Mục tiêu

COFI DOCUMENTARY là một xưởng sản xuất documentary/footage hoàn chỉnh. Người dùng có thể lấy chủ đề từ COFI RADAR hoặc nhập thủ công, sau đó hệ thống điều phối nghiên cứu/kịch bản, voice + SRT, tìm footage bằng Codex CLI và Gemini CLI, kiểm tra coverage, dựng bằng CofiRemotion, xem preview trực tiếp và tiếp tục từ checkpoint nếu phiên AI bị ngắt.

## Luồng chuẩn

`RADAR -> PLAN -> VOICE -> FOOTAGE -> PREFLIGHT -> EDIT -> QC`

1. **RADAR**: lấy niche/chủ đề cho kênh mới hoặc video tiếp theo cho kênh đang chạy; cũng cho phép nhập chủ đề thủ công.
2. **PLAN**: Codex CLI hoặc Gemini CLI nghiên cứu, viết `research.md`, `script.md` và `visual_manifest.json`. Mọi visual beat có `beat_id` ổn định.
3. **VOICE**: gọi CofiVoice theo script/beat, lưu voice theo beat, voice tổng và sinh `subtitles.srt` từ duration thực tế của từng beat.
4. **FOOTAGE**: chia beat cho Codex CLI + Gemini CLI tìm song song; mỗi worker phải preview/kiểm tra asset thật trước ACCEPT; merge về registry chung.
5. **PREFLIGHT**: kiểm tra đủ visual cho 100% beat, đủ source diversity, voice/SRT/timeline đồng bộ và assets tồn tại trước khi cho phép edit.
6. **EDIT**: CofiRemotion là source of truth. Mỗi job có composition/project riêng, preview trong app và checkpoint trên disk sau các thay đổi quan trọng.
7. **QC**: kiểm tra render thật, metrics và xuất final manifest.

## Engines

- **COFI RADAR**: `http://127.0.0.1:8876`; dùng API market/channel/niches/plans/today/my-channels.
- **Codex CLI**: engine chính cho research/script, một worker footage và edit/QC.
- **Gemini CLI**: engine thứ hai; có thể làm PLAN theo lựa chọn và chạy worker footage song song với Codex.
- **CofiVoice**: gọi FastAPI hiện có, ưu tiên `/api/job` cho script dài; Documentary copy kết quả vào workspace bền vững.
- **CofiRemotion**: project edit/render; Remotion Studio chạy nền và Documentary hiển thị preview. `@remotion/player`/Studio URL có thể dùng cho preview, nhưng source files và checkpoint trên disk mới là trạng thái bền vững.

## Trạng thái bền vững

Mỗi job lưu ở `data/jobs/<job_id>/job.json` và `workspaces/<job_id>/`.

Artifacts tối thiểu:

- PLAN: `research.md`, `script.md`, `visual_manifest.json`
- VOICE: `voice_manifest.json`, `subtitles.srt`, `audio/narration.wav`
- FOOTAGE: `footage_codex.json`, `footage_gemini.json`, `footage_review.json`, `asset_registry.json`
- PREFLIGHT: `coverage_matrix.json`, `preflight_report.json`
- EDIT: `edit_session.json`, `edit_checkpoint.json`, `render_manifest.json`
- QC: `director_report.md`, `final_manifest.json`

Một phase đã `succeeded` không chạy lại khi Resume Full Pipeline, trừ khi người dùng chủ động reset/rerun phase đó. Khi app khởi động lại, trạng thái `running/queued` cũ được chuyển sang `interrupted` để người dùng Resume thay vì mắc kẹt vĩnh viễn.

## Timeline contract

`visual_manifest.json` là timeline logic gốc. Mỗi beat có narration và target visual. Sau Voice, `voice_manifest.json` bổ sung `start_sec`, `end_sec`, `duration_sec` thực. SRT dùng cùng các mốc này. Footage/Remotion phải tham chiếu `beat_id`, không tự chia timeline mới nếu không cập nhật manifest.

## Footage dual-worker

Coordinator chia beat xen kẽ/đều theo duration cho Codex và Gemini. Mỗi worker ghi file riêng, không cùng sửa một registry. Sau khi cả hai kết thúc, coordinator merge, loại duplicate, kiểm tra local files/preview evidence và tạo coverage matrix. Nếu một engine thiếu, UI báo rõ và có thể chạy single-worker; dual mode mặc định khi cả hai Ready.

## Remotion preview và resume

Mỗi job có thư mục edit riêng hoặc một composition có props trỏ tới workspace. Documentary chạy/khám phá Remotion Studio server và hiển thị preview trong panel của job. App lưu:

- `composition_id`
- `project_path`
- `studio_url`
- `last_edit_at`
- file hashes của source chính
- render/preview gần nhất
- note bước edit hiện tại

Mất kết nối AI không làm mất source Remotion. Khi nối lại, Codex đọc `edit_checkpoint.json`, source hiện tại và manifest trước khi tiếp tục.

## UI

Toàn bộ copy hiển thị bằng tiếng Việt. Giao diện tối, rõ, ít thuật ngữ kỹ thuật, gồm:

- Tổng quan trạng thái Radar / Codex / Gemini / Voice / Remotion.
- Hai đường vào: `Tìm chủ đề bằng Radar` và `Tạo từ chủ đề có sẵn`.
- Wizard tạo job: kênh/market, chủ đề, ngôn ngữ, thời lượng, engine viết, voice/profile.
- Pipeline 7 bước dạng progress bar với nút Chạy/Tiếp tục/Chạy lại.
- Tab `Kịch bản`, `Voice & SRT`, `Footage`, `Dựng & Preview`, `Nhật ký`.
- Dựng & Preview hiển thị Remotion preview và checkpoint/resume status.

## Tiêu chí hoàn thành

- Gemini CLI cài và `gemini --version` chạy được.
- Documentary health hiển thị Radar, Codex, Gemini, CofiVoice, CofiRemotion.
- Radar có thể cấp dữ liệu chủ đề vào job.
- Phases mới và resume tồn tại trên disk.
- Voice/SRT chia theo beat ID và timestamp thực tế.
- Footage có hai worker độc lập và merge/coverage gate.
- Remotion preview endpoint/session hoạt động và edit checkpoint tồn tại.
- UI full tiếng Việt.
- Test suite backend/UI contract xanh và compile/import thành công.
