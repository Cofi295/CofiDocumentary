# COFI DOCUMENTARY — Quy tắc sản xuất

COFI DOCUMENTARY là hệ điều hành sản xuất video tài liệu dùng tư liệu thật, dành cho video 2–30 phút.

1. Luồng chuẩn có phase chung `plan -> voice -> visuals`, sau đó rẽ nhánh theo `visual_strategy`: Full AI = `ai_visual -> edit -> seo -> qc`; Full Footage = `footage -> edit -> seo -> qc`; Hybrid = `footage -> ai_visual -> edit -> seo -> qc`; Bằng chứng + AI (`evidence_footage`) = `footage -> ai_visual -> edit -> seo -> qc`. Không dùng tỷ lệ AI/Footage cố định cho Hybrid.
2. `visual_manifest.json` và `beat_id` là trục đồng bộ. Sau Voice, `visuals`/STP phải chia 100% lời thoại thành các visual ngắn đủ nghĩa, một dòng một prompt, không được bỏ text; mỗi visual giữ liên kết về beat gốc.
3. COFI RADAR là đầu vào tìm chủ đề cho kênh mới hoặc video tiếp theo; không sao chép engine Radar vào repo này.
4. Codex CLI hoặc Gemini CLI đảm nhiệm nghiên cứu + kịch bản + chia cảnh. Tìm tư liệu mặc định dùng cả Codex và Gemini để tăng độ phủ và đối chiếu.
5. Kết quả tìm kiếm chỉ là ứng viên. Trước khi chấp nhận phải kiểm tra video thật hoặc các khung hình đại diện và ghi đoạn thời gian dùng được, nguồn, mức khớp hình, chất lượng, watermark/logo và rủi ro quyền sử dụng.
6. Không kéo dài video bằng tư liệu không liên quan. Full AI bỏ qua Footage và tạo media cho toàn bộ visual; Full Footage bỏ qua AI Visual; Hybrid route từng visual theo cốt truyện; Bằng chứng + AI (`evidence_footage`) chỉ dùng Footage cho bằng chứng/nhân vật 100% xác thực (ảnh thẻ/chân dung thật, tài liệu lưu trữ gốc, bản án, văn bản chính thức có dấu mộc), toàn bộ cảnh bối cảnh/tái hiện/không gian dùng AI Visual (ảnh/video). Media AI phải được ghi nhãn là minh hoạ tái dựng và không được giả làm tư liệu thật.
7. Dùng CofiVoice để tạo giọng đọc + SRT theo đoạn. Dùng CofiRemotion để dựng, xem trước và kết xuất. Đọc `B:\ALL_TOOLS\CofiRemotion\AGENTS.md` trước khi sửa mã dựng hoặc kiểm tra video cuối.
8. Mã dựng và điểm lưu phải nằm trong workspace của dự án để khi mất kết nối có thể mở lại và tiếp tục từ trạng thái đã lưu.
9. Bản kết xuất chỉ được chấp nhận sau khi kiểm tra MP4 cuối và hợp đồng chất lượng đạt yêu cầu.
10. Các trường liên quan bản quyền/nội dung tái sử dụng chỉ là tín hiệu rủi ro; không được tuyên bố chắc chắn về fair use hay khả năng kiếm tiền.
11. **Nguyên tắc Linh hoạt Lore/DNA & Chống Lười Biếng (Flexible Editing DNA & Context-Adaptive Vox/Map/SFX/BGM)**: Lore kênh chỉ là DNA mẫu tham chiếu chất lượng, TUYỆT ĐỐI KHÔNG rập khuôn 1–2 mẫu Vox hay 1–2 tiếng SFX lặp đi lặp lại suốt video. Phải tự động biến hóa giữa **Bản đồ Full Màn Hình `1920x1080` bay camera A→B (`S3_FULLSCREEN_GIS_FLIGHT`, `S4_FULLSCREEN_SATELLITE_RECON`)**, **Bản đồ Chia Cột (`S1`, `S2`)**, và **6+ bố cục Báo chí / Bản án / Hồ sơ Trại giam / Bằng sáng chế (`N1..N6`)** dịu mắt cho khán giả 45–70 tuổi (chỉ 1 intro êm dịu, không nháy strobe, không xé lẹm mặt người). Sử dụng `documentary/audio_library_manager.py` để gán **28+ SFX Foley thực tế khớp ngữ cảnh** (2 sự kiện/clip), **5 nhạc nền BGM theo cảm xúc từng hồi**, và tự động tải thêm nhạc/SFX mới về kho (`fetch_missing_audio_asset`) khi gặp bối cảnh mới.

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
