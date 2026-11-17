# COFI DOCUMENTARY — Quy tắc sản xuất

COFI DOCUMENTARY là hệ điều hành sản xuất video tài liệu dùng tư liệu thật, dành cho video 2–30 phút.

1. Luồng chuẩn có phase chung `plan -> voice -> visuals`, sau đó rẽ nhánh theo `visual_strategy`: Full AI = `ai_visual -> edit -> seo -> qc`; Full Footage = `footage -> edit -> seo -> qc`; Hybrid = `footage -> ai_visual -> edit -> seo -> qc`; Bằng chứng + AI (`evidence_footage`) = `footage -> ai_visual -> edit -> seo -> qc`. Không dùng tỷ lệ AI/Footage cố định cho Hybrid.
2. `visual_manifest.json`, `beats_index.json`, `beats/<beat_id>.json` và `beat_id` là trục đồng bộ. Sau Voice, `visuals`/STP chia 100% lời thoại thành các visual ngắn đủ nghĩa, một dòng một prompt, không được bỏ text; mỗi visual giữ liên kết về `beat_id` gốc và tự động tách mảnh theo từng beat (`beats/<beat_id>.json`) để tra cứu và chỉnh sửa phẫu thuật từng cảnh mà không cần đọc lại toàn bộ manifest.
3. COFI RADAR là đầu vào tìm chủ đề cho kênh mới hoặc video tiếp theo; không sao chép engine Radar vào repo này.
4. Codex CLI hoặc Gemini CLI đảm nhiệm nghiên cứu + kịch bản + chia cảnh. Tìm tư liệu mặc định dùng cả Codex và Gemini để tăng độ phủ và đối chiếu.
5. Kết quả tìm kiếm chỉ là ứng viên. Trước khi chấp nhận phải kiểm tra video thật hoặc các khung hình đại diện và ghi đoạn thời gian dùng được, nguồn, mức khớp hình, chất lượng, watermark/logo và rủi ro quyền sử dụng.
6. Không kéo dài video bằng tư liệu không liên quan. Full AI bỏ qua Footage và tạo media cho toàn bộ visual; Full Footage bỏ qua AI Visual; Hybrid route từng visual theo cốt truyện; Bằng chứng + AI (`evidence_footage`) chỉ dùng Footage cho bằng chứng/nhân vật 100% xác thực (ảnh thẻ/chân dung thật, tài liệu lưu trữ gốc, bản án, văn bản chính thức có dấu mộc), toàn bộ cảnh bối cảnh/tái hiện/không gian dùng AI Visual (ảnh/video). Media AI phải được ghi nhãn là minh hoạ tái dựng và không được giả làm tư liệu thật.
7. Dùng CofiVoice để tạo giọng đọc + SRT theo đoạn. Dùng CofiRemotion để dựng, xem trước và kết xuất. Đọc `B:\ALL_TOOLS\CofiRemotion\AGENTS.md` trước khi sửa mã dựng hoặc kiểm tra video cuối.
8. Mã dựng, sổ nhớ tiến độ (`.producer/state_ledger.json`) và điểm lưu phải nằm trong workspace của dự án để khi mất kết nối hoặc xoay phiên có thể mở lại và tiếp tục chính xác từ phase/beat đang dở mà không đọc quét lại dự án.
9. Bản kết xuất chỉ được chấp nhận sau khi kiểm tra MP4 cuối và hợp đồng chất lượng đạt yêu cầu.
10. Các trường liên quan bản quyền/nội dung tái sử dụng chỉ là tín hiệu rủi ro; không được tuyên bố chắc chắn về fair use hay khả năng kiếm tiền.
11. **Nguyên tắc 3 Trụ cột Theo Hồ Sơ Kênh (`editing_dna`): Kiến Trúc Thị Giác 3 Tầng (`semantic_verified_footage_routing` + `TACTILE_VOX_EDITORIAL_DESK_AND_3D_GIS_VOX` + `10 Editorial Desk Archetypes`), Motion-Bound SFX & Story-Arc BGM**:
   - **Cách Ly Tuyệt Đối Theo Hồ Sơ Kênh (`channel_profile`)**: Mọi chất liệu thị giác, bảng màu, tỷ lệ phối trộn và ngôn ngữ đọc đều lấy từ `editing_dna` / `editorial_dna` của hồ sơ kênh đang chọn (`0%` trộn chéo giao diện hay ngôn ngữ giữa các kênh; các kênh tâm linh `sacred_devotional` giữ `0%` Vox).
   - **Thứ Tự Ưu Tiên Thị Giác 3 Tầng Khi Hồ Sơ Bật Điều Tra / Vox (`semantic_verified_footage_routing`)**:
     + **Ưu tiên số 1 (`REAL_FTG`)**: Tư liệu video/ảnh thật của chính vụ án khớp ngữ nghĩa 100% với `voice_text`, soi mắt trên Storyboard + lưới `100px` + Contact Sheet 3-frame (`15%-50%-85%`), cắt sạch 100% logo/watermark/phụ đề ngoại ngữ/MC trường quay (`0%` cắt mù tự động `blind_auto_offset`, `max_uses = 1`).
     + **Ưu tiên số 2 (`VOX` + `FramelessCinemaTextBeat.tsx`)**: Ở các phân đoạn không có tư liệu thật khớp 100% câu nói, triển khai Bàn Biên Tập Cắt Dán Vox (`src/vox-studio/vox-editorial-desk/index.tsx`, luân phiên `10 Editorial Desk Archetypes`, vùng an toàn `[60..1860, 40..820]`) theo quy trình 4 bước: (1) Đọc hiểu nghĩa câu voice để xác định vật chứng cụ thể -> (2) Vẽ vật chứng bằng Google Flow & tách nền RGBA (`rembg`) -> (3) Đặt Video hoặc Ảnh tư liệu thật ở trung tâm (ưu tiên Video nếu có) và xếp vật chứng cắt dán + thẻ hồ sơ + con dấu cân đối xung quanh (`0%` đè chồng) -> (4) **Khóa tĩnh camera mặt bàn `z = 1.0` (`transform: 'none'`, `0%` zoom-in/zoom-out)** và tùy biến chuyển động xuất hiện 12fps (`<SlideIn>`, `<RedCircle>`, `<OpticalLoupe>`, `<Highlight>`, `<Stamp>`) theo điểm rơi từng câu nói; riêng câu lộ trình di chuyển dùng Bản đồ vệ tinh 3D `<GeoJson3DMapStage>` dẫn đường theo tuyến OSRM/OSM thực tế, vượt cổng kiểm định AST `validate-vox-newsroom-ast.mjs`.
     + **Ưu tiên số 3 (`AI_4D`)**: Ảnh/video AI dự phòng góc kín kèm nhãn minh bạch theo đúng ngôn ngữ kênh khi cả tư liệu thật lẫn VOX đều không phù hợp.
   - **SFX (`100%` AST Motion-Bound SFX)**: Tắt hoàn toàn đoán SFX theo từ khóa kịch bản và tắt SFX trên cảnh `REAL_FTG` / `AI_4D` tĩnh. SFX chỉ gắn khi parser AST phát hiện component chuyển động vật lý thật trên cảnh VOX, bản đồ 3D hoặc `FramelessCinemaTextBeat`, đo khớp sóng âm `onset_frame_30fps = 0`.
   - **BGM (8 Nhóm Cảm Xúc + Story-Arc 8–12 Đoạn)**: Chia tập phim dài thành 8–12 đoạn cảm xúc (~2–3.5 phút/đoạn, Crossfade 3s, chuẩn hóa theo `target_lufs` của kênh, giữ nền `-41dBFS` ở điểm lặng trước twist, giữ trọn câu kết + `3.8s` fade-out; tự động tìm nhạc mới qua `search_and_fetch_contextual_bgm` nếu trùng tập trước trong `data/bgm_usage_history.json`).
12. **Luật Điều Phối 4 Luồng Rõ Ràng, Sổ Nhớ Tiến Độ (`state_ledger.json`) & Chỉnh Sửa Phẫu Thuật Từng Beat (`beats/<beat_id>.json`)**:
   - **15 Phòng Ban Chuyên Môn (`documentary/agent_departments.py`)**: Toàn bộ 15 tác tử (`@orchestrator`, `@radar`, `@research`, `@script`, `@voice`, `@visuals`, `@footage`, `@ai_visual`, `@vox`, `@edit`, `@seo`, `@evidence_qa`, `@qc`, `@dev`, `@debug`) vận hành theo đúng biên giới quyền hạn và artifact từng phòng ban.
   - **Phân Tách 4 Luồng Thực Thi — Không Mâu Thuẫn, Không Đọc Quét Dư Thừa**:
     1. **Hỏi trạng thái / tiến độ dự án**: Đọc trực tiếp từ `CURRENT APP CONTEXT` và `.producer/state_ledger.json` để trả lời ngay (`0` lệnh đọc mã nguồn, `0` lệnh quét thư mục).
     2. **Chạy phase sản xuất video (`plan -> voice -> visuals -> footage / ai_visual / vox -> edit -> seo -> qc`)**: Kích hoạt worker nền qua API (`/run/{phase}`, `/rerun/{phase}`, `/pipeline/{from}/{through}`, `/approve-next`) hoặc ủy nhiệm Phòng Ban chuyên môn (`POST /api/agency/delegate`, `POST /api/agency/delegate-squad` với `verify_with_qa: true`), sau đó **kết thúc lượt chat ngay lập tức** — **CẤM TUYỆT ĐỐI chạy vòng lặp poll `GET /api/jobs/{id}` trong phiên LLM** và cấm tự viết tay cả bộ `script.md` / `visual_manifest.json` dài hàng trăm beat ngay trong hộp chat.
     3. **Chỉnh sửa phẫu thuật 1 câu / 1 cảnh / 1 beat cụ thể**: Tra cứu chỉ mục nhẹ `beats_index.json` (`GET /api/jobs/{id}/beats?q=...`) và chỉ đọc/vá đúng mảnh `beats/<beat_id>.json` (`PATCH /api/jobs/{id}/beats/{beat_id}` hoặc `/edit-chat` kèm `beat_id`) — **CẤM đọc lại toàn bộ `visual_manifest.json` / `visual_prompts.json` nhiều MB khi chỉ sửa vài beat**.
     4. **Quét đề tài (`@radar`) hoặc sửa mã nguồn ứng dụng (`@dev`, `@debug`)**: Thực hiện trực tiếp trên luồng chính (`verify_with_qa: false`), bắt buộc tra đồ thị `.trail/cache/` (`trail ask "<query>" --source` hoặc `trail skeleton <file>`) trước khi mở đúng khoảng dòng cần sửa (`0` đọc trọn file `documentary/service.py` hay `app.py`).

<!-- trail:start -->
## Trail — repo context graph

This repo is indexed in `.trail/cache/`: small linked markdown nodes that explain each
system and carry exact file:line spans, kept in sync with the code through git.

For ANY task here — understanding how something works, finding where code lives,
or scoping a change — get context from the graph before grepping or opening
source files. Re-ask freely (it's cheap) and reuse literal identifiers you
already have (symbol, error string, file name) as the query. New to this repo?
Run `trail map` first — a token-budgeted orientation (dir clusters, hubs,
hotspots), no LLM, no key.

- Run `trail ask "<your question>" --source` → ranked nodes with the relevant
  code spans inlined (each hit's ≤8-line crux by default; `--full` for whole
  definitions when the crux isn't enough). Match the tool to the task shape:
  for understanding or editing, the top node IS the answer — cite its
  `covers:` file:line spans and edit straight from `--source`. For
  exhaustive tasks ("every occurrence / every caller of this pattern"), ranked
  results are top-N, not complete — run `trail grep "<literal>"` instead
  (exhaustive over indexed files, grouped by enclosing symbol), falling back
  to raw `grep -rn` only for unindexed files.
- `trail skeleton <file>` → every definition's signature + span, ~10× cheaper
  than reading the file; use it to skim an API surface.
- `trail callers <symbol>` gives precomputed, exact edges — who calls this.
  Add `--direction out` for what it calls, or `--depth N` to walk
  transitively for the full blast radius. For structural questions, skip
  ranking and use this directly.
- Or browse: `.trail/cache/INDEX.md` lists every node; follow the links.
- Monorepos and folders of multiple repos rank fairly across sub-projects —
  hits carry `[scope/]` labels naming which one they're from. Narrow with
  `trail ask "<task>" --in <scope>/` once you know where you're working.

If a returned span is truncated ("+N more lines"), open the file at that exact
range before finalizing. Only open source files when a node genuinely lacks a
needed detail, and then at the exact file:line the node points to — never
re-read whole files.

After big code changes, refresh the graph with `trail build` (deterministic,
no API key, $0).
<!-- trail:end -->
