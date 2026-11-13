---
name: cofi-vox-blender-director
description: "Flow-First RGBA Evidence Cutouts, Center Real-Footage Hero (Video Prioritized or Photo) & Precision 3D Satellite Cartography Director (CofiStudioMediaFactoryRunner + rembg -> src/vox-studio/vox-editorial-desk/index.tsx + <GeoJson3DMapStage> — Priority #2 After Real Footage, 0% Camera Zoom, Context-Adaptive Entrance & Vocal Emphasis Motions)."
---

# Flow-First Cutout Evidence, Center-Footage Tactile Desk & 3D Satellite Cartography Director (`@vox`)

## 1. Thứ Tự Ưu Tiên Thị Giác 3 Tầng (`0%` Khóa Số Mẫu, `0%` Rải Theo Chu Kỳ)
1. **Ưu tiên số 1 (`REAL_FTG`)**: Tư liệu video thật của chính vụ án (`footage/S_F*.mp4`) đã soi mắt 3-frame và cắt sạch 4 cạnh ở những câu có tư liệu thật khớp 100% ngữ nghĩa.
2. **Ưu tiên số 2 (Bắt buộc ở mọi phân đoạn không có Footage thật) — Đồ Họa VOX Minh Họa Độc Bản (`src/vox-studio/vox-editorial-desk/index.tsx` & `<GeoJson3DMapStage>`)**:
   - Không khóa cố định bao nhiêu mẫu VOX và không rải theo chu kỳ `idx % N`. Ở những đoạn không có footage thật, bắt buộc dùng VOX minh họa làm ưu tiên số 2 (trước khi xét đến ảnh AI).
3. **Điểm Nhấn Motion Text Không Khung (`src/components/FramelessCinemaTextBeat.tsx`)**:
   - Gắn tại đúng điểm rơi câu chuyện (câu hỏi nghịch lý `?`, con số chấn động, phán quyết cao trào, `0` đặt 2 beat liền kề), đa dạng hóa `showroomRenderer`, `fontStyle`, `accentColor`, `layoutVariant` khớp 100% nghĩa câu.
4. **Ưu tiên số 3 (Sau cuối cùng mới là Ảnh AI) — Ảnh AI Góc Kín (`AI_4D` / `{bid}_ai_keyframe.jpg`)**:
   - Chỉ dùng làm phương án cuối cùng khi cả tư liệu thật lẫn VOX minh họa đều không thể hiện được góc khuất tâm lý đóng kín.

---

## 2. QUY TRÌNH 4 BƯỚC BẤT DI BẤT DỊCH KHI LÀM CẢNH BÀN BIÊN TẬP `<Desk>` (`VẼ BẰNG FLOW TRƯỚC -> TÁCH NỀN RGBA -> VIDEO HOẶC ẢNH FOOTAGE THẬT Ở TRUNG TÂM [ƯU TIÊN VIDEO NẾU CÓ] + VẬT CHỨNG CẮT DÁN Ở XUNG QUANH -> MOTIONS XUẤT HIỆN & CÁCH NHẤN MẠNH TÙY BIẾN THEO CÂU VOICE, 0% ZOOM`)
1. **Bước 1 — Đọc Hiểu Câu Voice & Xác Định Đúng Vật Chứng (`100% Sentence-Specific Evidence`)**:
   - Đọc kỹ câu thoại (`voice_text`) và các cụm từ (`t1 -> t2 -> t3`) để xác định chính xác câu đó đang nói về hiện trường gì và những vật chứng/đạo cụ cụ thể nào.
   - **CẤM TUYỆT ĐỐI** râu ông nọ cắm cằm bà kia (cấm dùng lại vật chứng của câu khác, cấm thêm bừa đạo cụ trang trí không có trong câu nói).
2. **Bước 2 — BẮT BUỘC Vẽ Vật Chứng Bằng Google Flow Trước (`CofiStudioMediaFactoryRunner`) & Tách Nền Cắt Dán RGBA (`rembg`)**:
   - **Trước khi viết code cảnh VOX**, bắt buộc gọi Google Flow (`CofiStudioMediaFactoryRunner`) vẽ riêng từng ảnh vật chứng/đạo cụ cụ thể của câu thoại trên nền sáng đồng nhất (`isolated on pure solid light warm cream background, studio forensic macro photography, no text, no watermark`), sau đó chạy `rembg` tách nền trong suốt RGBA sắc nét (`prop_XX.png`, `cutout_XX.png`) và soi mắt từng file PNG bằng `read_file`.
   - Chuẩn bị tư liệu/footage thật của vụ án khớp với câu nói và đã crop sạch 100% logo/phụ đề gốc (ưu tiên clip video sạch `video_XX.mp4` nếu có, hoặc khung hình ảnh `plate_XX.jpg`).
   - **CẤM TUYỆT ĐỐI** vẽ hình giả bằng PIL/Python, cấm dùng hộp sơ đồ hình học SVG lặp đi lặp lại (`<BespokeSentenceDiagramByIndex>` / `renderSentenceIllustrationSvg`), và cấm dùng lại ảnh cắt dán giữa các cảnh (`max_uses = 1`).
3. **Bước 3 — Bố Cục Chuẩn Trên Mặt Bàn `1920×1080`: Video Hoặc Ảnh Footage Thật Ở Trung Tâm (Ưu Tiên Video Nếu Có) + Vật Chứng Cắt Dán Ở Xung Quanh**:
   - **Ở Trung Tâm Mặt Bàn (`Center Hero Real Footage Video or Photo — Ưu Tiên Video Nếu Có`)**: Giữ đúng phong cách và bố cục hiện tại — đặt **1 khung tư liệu/footage thật lớn của vụ án** (kích thước lớn rõ nét `w = 620..660, h = 395..420`, tọa độ chính giữa bàn `left = 620..665, top = 200..235`) làm tâm điểm thị giác. **Khung trung tâm này có thể là Video hoặc Ảnh, nhưng ƯU TIÊN VIDEO (`<VoxVideoPaper>`, `<VoxPhotoPaper videoSrc={...}>` hoặc `<RedBackedTornPhoto videoSrc={...}>`) nếu có clip tư liệu thật phù hợp**; chỉ khi không có video mới dùng ảnh tĩnh (`<VoxPhotoPaper>` hoặc `<RedBackedTornPhoto>`).
   - **Ở Xung Quanh 4 Góc (`Surrounding Flow Cutout Evidence & Notes`)**: Bố trí cân đối ở 4 góc bao quanh khung trung tâm (góc trên-trái `left: 64..106, top: 38..60`, góc dưới-trái `left: 64..106, top: 505..545`, góc trên-phải `left: 1350..1360, top: 38..60`, góc dưới-phải `left: 1350..1385, top: 505..565`) gồm:
     * **2 ảnh vật chứng Flow tách nền RGBA cỡ lớn** (`<DieCutSticker src={propAsset('prop_XX.png')} w={450..465} h={330..335} />` và `<DieCutSticker src={propAsset('cutout_XX.png')} w={445..460} h={325..335} />`) phóng to rõ ràng, dễ nhìn.
     * **1 thẻ hồ sơ / mảnh báo xé / nhãn ghim** (`<IndexCard>`, `<TornClipping>`, `<TornPostageStrip>`, `<EyeletArchiveTag>`, `<Label>`) ghi ngắn gọn, chữ to rõ (`fontSize: 20..24`), 100% đúng ngôn ngữ đích của kênh (`0%` chữ tiếng Anh mẫu).
     * **1 con dấu phân loại** (`<Stamp text="..." size={36} />`).
   - **Không Đè Chồng (`0%` Overlap)**: Giữ khoảng cách thoáng sạch quanh khung trung tâm, nằm gọn trong vùng an toàn `[60..1860, 38..845]`.
4. **Bước 4 — Chất Liệu Bàn Biên Tập Vox, `0%` Camera Zoom & Motions Xuất Hiện + Cách Nhấn Mạnh Tùy Biến Theo Bối Cảnh Từng Câu Voice (`t1 -> t2 -> t3`)**:
   - Nền bàn giấy ấm `#E4DDCF` + `#voxGrain` (`opacity: 0.22`), kết hợp `<ManilaKraftBoard inset={42} />` hoặc `<BlackCard inset={38} />` (`#1B1B1A`); bảng màu `#EEEDED`, `#1B1B1A`, đỏ manh mối `#B8433F`, bút dạ quang vàng `#DACF08` (`multiply`).
   - **CẤM TUYỆT ĐỐI Zoom Camera & Cuộn 4 Góc**: `<Desk>` và `<World>` khóa tĩnh 100% ở `z = 1.0` (`transform: 'none'`, `0%` `<PaperCurlCorners>`).
   - **Motions xuất hiện & cách nhấn mạnh tùy biến theo bối cảnh và câu voice**: Thứ tự xuất hiện (`at={0}`, `t1`, `t2`, `t3`), kiểu trượt/đập/bóc dán 12fps (`<SlideIn from="...">` — `left`, `right`, `top`, `bottom`, `scale`, `scissors_slide_left`, `scissors_slide_right`, `slap_drop_top`, `sticker_peel_up`, `unroll_scroll_down`, `accordion_fold_left`, `accordion_fold_right`, `diagonal_toss_spin`, `fan_deal_bottom`) và công cụ nhấn mạnh (`<RedCircle>` khi khoanh chỉ điểm mục tiêu, `<OpticalLoupe>` khi soi phóng đại, `<TwistedRedYarn>` / `<RedLine>` khi nối đầu mối nhân quả, `<DimensionBracket>` khi đo khoảng cách/phạm vi, `<Highlight>` / `<Underline>` / `<Stamp>` khi nhấn mạnh kết luận) được tùy biến linh hoạt theo bối cảnh và cách nhấn mạnh khác nhau của từng câu voice.

---

## 3. HIẾN CHƯƠNG BẢN ĐỒ VỆ TINH 3D (`<GeoJson3DMapStage>` — CHỈ GẮN ĐÚNG CÂU VOICE DI CHUYỂN, TỌA ĐỘ & ĐƯỜNG ĐI CHÍNH XÁC 100%)
1. **Chỉ Gắn Đúng Câu Voice Nhắc Đến Đường Di Chuyển Của Hung Thủ Hoặc Cảnh Sát (`0%` Rải Tự Động Theo Chu Kỳ)**:
   - Bản đồ vệ tinh `<GeoJson3DMapStage>` chỉ được phép gắn vào đúng câu voice mô tả đường đào tẩu/lẩn trốn/xâm nhập của hung thủ HOẶC đường xuất phát/truy lùng/bao vây/áp giải của cảnh sát.
2. **Tọa Độ Thực Tế & Đường Kẻ OSRM/OSM Chính Xác 100% (`0%` Ô Đen)**:
   - Tấm vệ tinh Esri (`*_sat_*.jpg`, `>= 3072x2048`) đầy đủ 100% ô tile (`0%` ô đen), khóa tọa độ thực `[lon, lat]` Web Mercator `0.00px`, đường kẻ thực tế (`>= 12..40` đỉnh thật, `0%` đường cong sin giả), mũi tên hướng đi rõ ràng và chữ không đóng hộp thô.
