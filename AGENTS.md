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
11. **Nguyên tắc 3 Trụ cột: Kiến Trúc Vox 2 Lớp (`Voice-to-Vox Semantic Analyzer` × `Fixed-Style Tactile Vox Editorial Desk` + Cắt Dán Ảnh Flow/Tư Liệu Độc Bản Theo Từng Câu Voice + Bản Đồ Vệ Tinh 3D `<GeoJson3DMapStage>`), BGM Story-Arc & Motion-Bound SFX**:
   - **Vox (Kiến Trúc 2 Lớp — Phong Cách Bàn Biên Tập Cắt Dán Cố Định `src/vox-studio/vox-editorial-desk/index.tsx` × Phân Tích Nghĩa Từng Câu Voice Để Thiết Kế Ảnh Flow Cắt Dán, Nhãn, Bố Cục & Chuyển Động Độc Lập 100% + Bản Đồ Vệ Tinh 3D `<GeoJson3DMapStage>`)**:
     + **Lớp 1 — Cách Ly Chất Liệu, Bảng Màu & Thứ Tự Ưu Tiên Thị Giác 3 Tầng Theo Hồ Sơ Kênh (`0%` trộn chéo giao diện giữa các kênh, `0%` khóa cố định số mẫu hay vị trí rải VOX)**:
       * Kênh `channel-kr-financial-fugitive-director-v2` (`forensic_noir_director_v2`), `channel-kr-truecrime-director-v2` (`forensic_noir_director_v2`) & `channel-e544a64b7c` (`forensic_noir`): **Ưu tiên số 1 (`REAL_FTG`)** là tư liệu video thật sạch 3-frame của chính vụ án khớp ngữ nghĩa 100% với `voice_text` (`0%` logo/chữ chạy bên khác, `0%` dùng code tự động cắt/ghép, `0%` cắt tịnh tiến hàng loạt một video nguồn [`<= 12` clip hoặc `<= 25%`/nguồn], `0%` nối đuôi `— 대사 문맥: ...` vào `observed_content`); **Ưu tiên số 2 bắt buộc (`VOX`)** ở mọi phân đoạn không có tư liệu thật khớp 100% câu nói là **Bàn Biên Tập Cắt Dán Chuẩn Vox `src/vox-studio/vox-editorial-desk/index.tsx` (`0%` cuộn 4 góc / băng dính 4 góc, `0%` zoom-in / zoom-out camera) & Bản Đồ Vệ Tinh 3D Dẫn Đường `<GeoJson3DMapStage>`** (chất liệu bàn giấy biên tập ấm `#E4DDCF` + hạt giấy tĩnh `#voxGrain` `opacity: 0.22` + thẻ đen tương phản `<BlackCard inset={38}>` `#1B1B1A`, 3 màu trung tính `#EEEDED/#1B1B1A/#171716` + 2 màu nhấn `#B8433F` đỏ manh mối & `#DACF08` vàng dạ quang `multiply`, linh hoạt 100% theo nghĩa câu thoại [0% cố định số mẫu hay vị trí rải], vùng an toàn `[60..1860, 40..820]`) + **`FramelessCinemaTextBeat.tsx` (chữ chuyển động linh hoạt tại điểm rơi câu chuyện, `0%` rập khuôn 1 mẫu)**; **Ưu tiên số 3 cuối cùng (`AI_4D`)** mới là Ảnh AI dự phòng góc kín khi cả Footage thật lẫn VOX minh họa đều không phù hợp.
       * Kênh `channel-cn-cyber-finance-kr` (`financial_forensic_vox`): **`~50%`** tư liệu thật đúng vụ án (`semantic_verified_footage_routing`) + **Vox Bảng Điện Kiểm Toán Tối (`~24%–30%`, chất liệu `#040C18/#38BDF8/#FACC15/#EF4444`, `JetBrains Mono` + `Pretendard`, `y <= 835px`)** + **`FramelessCinemaTextBeat.tsx` (`~8%–10%`)** + **Ảnh AI 4D (`~10%–15%`)**.
       * Các hồ sơ khác có bật Vox (`investigative_counterpoint_vn`, `2.5d_technical`, `archival_historical`) giữ riêng chất liệu/màu sắc của `preset_id` đó; kênh tâm linh (`channel-kr-grace-letter-60m` / `sacred_devotional`) giữ **`0%` Vox**.
     + **Lớp 2 — Quy Trình 4 Bước Bắt Buộc Cho Từng Câu Voice Cần VOX (`Đọc Hiểu Câu Voice -> Vẽ Vật Chứng Bằng Google Flow Trước & Tách Nền RGBA -> Video Hoặc Ảnh Footage Thật Ở Trung Tâm [Ưu Tiên Video Nếu Có] + Vật Chứng Cắt Dán Ở Xung Quanh -> Motions Xuất Hiện & Cách Nhấn Mạnh Tùy Biến Theo Bối Cảnh Câu Voice, 0% Zoom Camera`)**:
       * **QUY TRÌNH CHUẨN 100% NHƯ BẢN VỪA EDIT (`xudapeng-v24`)**: Với mỗi câu nói sử dụng VOX trên bàn giấy `<Desk>`: (1) **Đọc hiểu câu voice (`voice_meaning` & `illustration_content`)**: Xác định đúng vật chứng cụ thể trong câu nói (`0%` râu ông nọ cắm cằm bà kia, `0%` dùng lại vật chứng câu khác); (2) **BẮT BUỘC vẽ ảnh vật chứng bằng Google Flow trước (`CofiStudioMediaFactoryRunner`) & tách nền RGBA (`rembg`)**: Vẽ riêng các vật chứng (`prop_XX.png`, `cutout_XX.png`) trên nền trơn sáng, tách nền RGBA sắc nét, soi mắt kiểm tra từng file PNG bằng `read_file`, và chuẩn bị tư liệu Footage thật của vụ án (clip video sạch hoặc khung hình `plate_XX.jpg` đã cắt sạch logo/phụ đề) — **CẤM TUYỆT ĐỐI dùng hộp sơ đồ hình học lặp lại (`<BespokeSentenceDiagramByIndex>` / `renderSentenceIllustrationSvg`) hoặc vẽ hình giả bằng PIL**; (3) **Bố cục chuẩn `1920×1080`: Video hoặc Ảnh Footage thật ở trung tâm (Ưu tiên Video nếu có) + Vật chứng cắt dán ở xung quanh**: Giữ đúng phong cách và bố cục hiện tại — đặt **1 khung tư liệu/footage thật lớn của vụ án ở chính giữa trung tâm** (`w = 620..660, h = 395..420`, `left = 620..665, top = 200..235`), **có thể là Video hoặc Ảnh nhưng ƯU TIÊN VIDEO (`<VoxVideoPaper>`, `<VoxPhotoPaper videoSrc={...}>` hoặc `<RedBackedTornPhoto videoSrc={...}>`) nếu có clip tư liệu thật phù hợp**, nếu không có video mới dùng ảnh tĩnh (`<VoxPhotoPaper>` / `<RedBackedTornPhoto>`), và bố trí cân đối ở **4 góc xung quanh** (`left: 64..106` bên trái & `left: 1350..1385` bên phải) gồm **2 ảnh vật chứng Flow cắt dán RGBA cỡ lớn (`<DieCutSticker w={450..465} h={330..335} />`)**, **1 thẻ hồ sơ / báo xé / nhãn ghim tiếng Hàn (`<IndexCard>`, `<TornClipping>`, `<TornPostageStrip>`, `<EyeletArchiveTag>`, `<Label>`) chữ to rõ sát nghĩa câu nói**, và **1 con dấu (`<Stamp size={36} />`)** (`0%` đè chồng che khuất, nằm gọn trong `[60..1860, 38..845]`); (4) **Motions xuất hiện & cách nhấn mạnh 12fps tùy biến linh hoạt theo bối cảnh từng câu voice**: Giữ nguyên chất liệu mặt bàn và khóa tĩnh camera (`0%` zoom), còn **motions xuất hiện (`<SlideIn from="..." at={...}>` — thứ tự vào trước/sau tại `at={0}`, `t1`, `t2`, `t3` và kiểu trượt/đập/bóc dán) cùng cách nhấn mạnh (`<RedCircle>`, `<OpticalLoupe>`, `<TwistedRedYarn>`, `<RedLine>`, `<DimensionBracket>`, `<Highlight>`, `<Underline>`, `<Stamp>`) được tùy biến linh hoạt theo bối cảnh và cách nhấn mạnh khác nhau của từng câu voice**.
       * **0% Zoom Trên Bàn Giấy `<Desk>` & Bản Đồ Vệ Tinh 3D Dẫn Đường (`<GeoJson3DMapStage>`)**: Trên bàn giấy `<Desk>/<World>` camera khóa tĩnh 100% (`z = 1.0`, `transform: 'none'`, `0%` zoom-in / zoom-out, `0%` 4 góc cuộn lại), còn trên Bản đồ vệ tinh 3D `<GeoJson3DMapStage>` (chỉ gắn đúng câu voice nhắc đến lộ trình di chuyển của hung thủ hoặc cảnh sát) camera 3D nghiêng (`pitchDeg`, `bearingDeg`) dẫn đường mượt dọc tuyến đường thực OSRM/OSM kèm tọa độ nói trong voice, mũi tên hướng đi rõ ràng và chữ chú thích không đóng hộp thô phong cách AI; vượt qua cổng kiểm định AST `validate-vox-newsroom-ast.mjs` và soi mắt Contact Sheet (`VERIFY_CENTER_HERO_*_DESK_VOX.jpg`).
   - **SFX (`100%` AST Motion-Bound SFX + Earshot Waveform + Audio Listener — Role bắt buộc `cofi-agency-sfx` của `@edit` / `@edit_motion_sfx_rigger`)**: **XÓA SỔ 100% đoán SFX bằng từ khóa kịch bản (`VOX_GRAPHIC_MOTION_RULES` / `fallback_pool`) & TẮT HOÀN TOÀN SFX trên các cảnh Tư liệu thật (`REAL_FTG`) và Ảnh AI tĩnh (`AI_4D`)**. SFX chỉ được sinh ra khi parser AST đọc thấy **component chuyển động vật lý thật** trong code cảnh (`extract_vox_scene_component_motions` trên `VoxScenes*.tsx`: `<SlideIn>`, `<DieCutSticker>`, `<Stamp>`, `<RedCircle>`, `<Highlight>`, `<OpticalLoupe>`, `<GeoJson3DMapStage>`) hoặc chuyển động chữ thực tế của `FramelessCinemaTextBeat` (`extract_cinema_text_motions` trên `CinemaTextSpecs.ts` — cảnh có N chuyển động phát đúng N tiếng, đứng yên phát 0 tiếng); bắt buộc đo sóng âm `inspect_sfx_waveform_earshot` (`onset_frame_30fps = 0`, `peak_frame_30fps`) khớp 0ms và tự động săn + nghe thẩm định bằng `read_file` qua `search_and_fetch_verified_sfx` khi cần âm thanh mới.
   - **BGM (8 Nhóm Cảm Xúc + Story-Arc 8–12 Đoạn + Tự Động Tìm & Tải Ngay Khi Không Hợp)**: Chia tập phim 25–30 phút thành **8–12 đoạn cảm xúc theo diễn biến câu chuyện** (~2–3.5 phút/đoạn, chuyển bài bằng Crossfade 3s, chuẩn hóa theo `target_lufs` của hồ sơ kênh; ở các cú ngắt nhạc trước twist lớn giữ nền room-tone analog êm `-41dBFS` / `volume: 0.015` thay vì rơi về `0.000` số học để tránh hẫng âm thanh và lỗi dead-air QC). **Nếu nhạc trong kho không hợp bối cảnh hoặc đã dùng ở tập trước (`data/bgm_usage_history.json`), BẮT BUỘC gọi `search_and_fetch_contextual_bgm` để tìm và tải thêm nhạc mới ngay lập tức, tuyệt đối không mặc định dùng lại bài cũ**.
12. **Luật Hộp Chat Điều Phối Thuần Khiết & Cơ Cấu 15 Phòng Ban Chuyên Môn (`Tổ trưởng · Tổ phó · Nhóm Chuyên viên Mini-Agents`)**:
   - Phiên chat (`orchestrator` / `Executive Dispatcher`) **TUYỆT ĐỐI KHÔNG BAO GIỜ tự thực thi công việc sản xuất video trực tiếp trong hộp chat** (không tự viết kịch bản `script.md`, không tự sinh/sửa `visual_manifest.json`, không tự cắt footage, không tự viết code cảnh VOX `VoxScenes*.tsx`, không tự dựng timeline Remotion).
   - Toàn bộ 15 bộ phận (`@orchestrator`, `@radar`, `@research`, `@script`, `@voice`, `@visuals`, `@footage`, `@ai_visual`, `@vox`, `@edit`, `@seo`, `@evidence_qa`, `@qc`, `@dev`, `@debug`) được tổ chức thành **15 Phòng Ban Chuyên Môn (`documentary/agent_departments.py`)** gồm **Tổ trưởng (`lead`)**, **Tổ phó (`deputy`)** và **4–6 Chuyên viên Mini-Agents (`specialists`)** phối hợp dây chuyền nội bộ; đặc biệt **Phòng 08 · Phòng Thiết Kế Đồ Họa Điều Tra VOX (`@vox`)** vận hành bởi `@vox_lead`, `@vox_deputy` cùng 6 chuyên viên (`@vox_voice_reader`, `@vox_desk_designer`, `@vox_asset_creator`, `@vox_motion_designer`, `@vox_choreography_animator`, `@vox_spatial_locator`).
   - Khi người dùng giao việc, hộp chat chỉ làm đúng 2 nhiệm vụ: **(1) Điều phối & phân công 100% công việc chuyên môn cho đúng Phòng Ban / Agent trong đội ngũ 15 Phòng Ban qua API/subagent**, và **(2) Kiểm tra nghiệm thu chất lượng đầu ra cuối cùng (QA/QC & soi mắt frame thực tế) trước khi báo cáo người dùng**.

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
