---
name: cofi-thumbnail-designer
description: Specialist skill for designing high-CTR YouTube documentary & True Crime thumbnails (1280x720) in CofiDocumentary: mandatory Channel DNA pre-check, 4 candid situational facial expressions of the culprit (courtroom, arrest, interrogation, disguise) with ZERO reference-pose/expression cloning, and mandatory redraw/rendering via the in-app Thumbnail Studio Engine (documentary/thumbnail_studio.py + static/thumbnail_studio.js Fabric.js Layer Engine + PIL Multi-Layer Renderer + NanoThumbnail).
---

# COFI Thumbnail Designer Skill (100% Clean Role — Channel DNA + 4 Candid Culprit Expressions + In-App Thumbnail Studio Redraw Engine)

Use this skill whenever designing, critiquing, or updating YouTube thumbnails in **COFI DOCUMENTARY** (Phase `seo` or via AI Chat requests on Tab `SEO + Thumbnail`).

---

## 1. Luật Bắt Buộc Số 1: Kiểm Tra & Khóa Chặt DNA Kênh Trước Khi Làm Thumbnail (`Channel DNA Pre-Check`)

Trước khi lên ý tưởng, viết prompt tạo ảnh nền hoặc dựng bất kỳ layer thumbnail nào, AI Agent **BẮT BUỘC** phải kiểm tra hồ sơ DNA của kênh đang chạy:
1. **Đọc dữ liệu DNA Kênh**:
   - Đọc `data/channel_profiles.json` (`thumbnail_dna`, `seo_keyword_dna`), `workspace/seo_reference_context.json` (`channel_inspection_report`, `evidence_videos`), và kiểm tra bằng mắt các ảnh mẫu trong `workspace/seo_reference_thumbnails/*` (ưu tiên `own_channel_*`, sau đó đến `competitor_*` / `reference_*`).
2. **Khóa đúng cấu trúc thị giác của kênh**:
   - Bám sát 100% `layout_template` (bố cục chữ/nhân vật/khung PiP), `color_palette` (màu chữ chính, màu nhấn cảnh báo, màu nền), `typography_preset` (phông chữ, độ dày viền đen), và `badge_text_default` của đúng kênh đó.
   - **CẤM TUYỆT ĐỐI** lấy nhãn (badge), màu sắc hoặc công thức chữ của kênh khác gắn sang kênh hiện tại.
3. **Chỉ lấy DNA Bố Cục — CẤM Sao Chép Mặt Hay Dáng Của Ảnh Mẫu Kênh**:
   - Khi xem `seo_reference_thumbnails/*`, chỉ trích xuất quy luật bố cục, tỷ lệ chữ và độ tương phản.
   - **CẤM TUYỆT ĐỐI** vẽ lại khuôn mặt, biểu cảm, góc nghiêng đầu hay dáng đứng của nhân vật trong ảnh mẫu kênh trước đó.

---

## 2. Luật Bắt Buộc Số 2: Tái Hiện 4 Mẫu Khuôn Mặt & Biểu Cảm Tự Nhiên Nhất Của Hung Thủ (`4 Candid Situational Culprit Expressions`) — CẤM Làm Mặt Hay Dáng Như Ảnh Mẫu

Đối với các tập phim tài liệu tội phạm / hồ sơ vụ án có nhân vật trung tâm là hung thủ/nghi phạm, khi tạo bộ **4 phương án Thumbnail (`BẢN A / v1`, `BẢN B / v2`, `BẢN C / v3`, `BẢN D / v4`)**, AI Agent **BẮT BUỘC** phải tái hiện **4 khoảnh khắc khuôn mặt và biểu cảm đời thực tự nhiên nhất của hung thủ** theo từng tình huống cụ thể của vụ án:

1. **Mẫu 1 (`BẢN A / v1`) — Khoảnh Khắc Ra Tòa Nhận Phán Quyết (`Courtroom Verdict Moment`)**:
   - **Tình huống & Biểu cảm**: Hung thủ đứng trước vành móng ngựa trong phiên tòa xét xử khi nghe tuyên án. Biểu cảm tự nhiên, sống động như phóng sự thật: ánh mắt sững sờ, mí mắt trĩu nặng, nét mặt suy sụp, bàng hoàng hoặc cúi đầu nặng nề dưới ánh đèn phòng xử án.
2. **Mẫu 2 (`BẢN B / v2`) — Khoảnh Khắc Bị Bắt Giữ / Lột Trần Vỏ Bọc (`Arrest & Unmasking Moment`)**:
   - **Tình huống & Biểu cảm**: Khoảnh khắc cảnh sát hình sự ập vào khống chế, khóa tay tại hiện trường. Biểu cảm tự nhiên ngay giây phút bị bắt: vẻ mặt chết lặng, choáng váng, mồ hôi lạnh, đôi mắt mở lớn hoặc thất thần khi lớp ngụy trang nhiều năm sụp đổ.
3. **Mẫu 3 (`BẢN C / v3`) — Khoảnh Khắc Thẩm Vấn Đối Chất (`Interrogation Room Confrontation`)**:
   - **Tình huống & Biểu cảm**: Hung thủ ngồi trong phòng thẩm vấn đối diện điều tra viên và hồ sơ vật chứng. Biểu cảm tâm lý chân thực: ánh mắt căng thẳng, môi mím chặt, cơ mặt co nhẹ, vẻ mặt giằng xé giữa sự quanh co và nỗi sợ hãi bị vạch trần dưới ánh đèn bàn hỏi cung lạnh lẽo.
4. **Mẫu 4 (`BẢN D / v4`) — Khoảnh Khắc Đời Thực Trong Vỏ Bọc / Hiện Trường (`Candid Disguise / Paradox Moment`)**:
   - **Tình huống & Biểu cảm**: Hung thủ trong vỏ bọc đời thường đặc trưng của vụ án (ví dụ: đang cầm hoa hồng/micro trên sân khấu truyền hình, làm MC đám cưới, hoặc xuất hiện tại hiện trường) với biểu cảm tự nhiên nhưng ẩn chứa ánh nhìn sắc lạnh, bất an hoặc sự đối lập tâm lý.

### 🚫 Quy Tắc Chống Sao Chép Dáng & Biểu Cảm Ảnh Mẫu (`Zero Reference-Pose / Expression Cloning`)
- Khi sử dụng ảnh tư liệu thật của hung thủ (`identity_references`) hoặc ảnh khóa nhân vật (`style_reference.png`):
  - **CHỈ DÙNG** ảnh tham chiếu để giữ đúng **đặc điểm nhận dạng cốt lõi của khuôn mặt** (cấu trúc xương mặt, tỷ lệ mắt-mũi-miệng, đường chân tóc, độ tuổi).
  - **CẤM TUYỆT ĐỐI** làm mặt đơ hay giữ nguyên dáng đứng/tư thế chụp ảnh thẻ, ảnh truy nã tĩnh, hoặc dáng đứng thẳng T-pose trong tờ `style_reference.png`!
  - Mọi phương án phải xoay góc cơ thể, góc đầu, hướng nhìn và cơ mặt hoàn toàn tự nhiên theo đúng hành động thực tế (đang đứng trước vành móng ngựa, đang bị cảnh sát giữ vai còng tay, đang ngồi ghế thẩm vấn, đang hoạt động trong vỏ bọc).

---

## 3. Luật Bắt Buộc Số 3: Luôn Dùng Bộ Phần Mềm Vẽ Lại Thumbnail Tích Hợp Sẵn Trong App (`COFI Thumbnail Studio Engine`)

**CẤM TUYỆT ĐỐI** để AI vẽ trực tiếp chữ tiếng Hàn/tiếng Việt vào ảnh nền bằng mô hình sinh ảnh thô. Mọi thumbnail **BẮT BUỘC** phải được vẽ lại và kết xuất qua bộ engine có sẵn của app:
- **Backend Engine (`B:\ALL_TOOLS\CofiDocumentary\documentary\thumbnail_studio.py`)**:
  - `build_default_thumbnail_design(job_id, workspace, job, seo_pack=..., thumbnail_dna=...)`: Tự động dựng cấu trúc 4 phương án (`v1..v4`) chuẩn Fabric.js JSON Layer theo đúng `thumbnail_dna` của kênh.
  - `render_variant_to_pil(workspace, design, variant)` & `render_design_thumbnails_to_disk(workspace, design)`: Engine đồ họa PIL/Vector tích hợp sẵn của app tự động vẽ lại toàn bộ các lớp (`vignette`, khung ảnh tư liệu `inset_photo` / `inset_photo_2` kiểu `cctv_hud`, `caution_tape`, `torn_newspaper`, `amber_glow_double`, `financial_audit_hud`, vòng tròn pháp y `forensic_circle`, mũi tên 3D `forensic_arrow`, nhãn `badge`, 2 dòng chữ `line_1` + `line_2` viền đen dày đa sắc) và xuất ra `workspace/thumbnails/thumbnail_v1..v4.jpg` + `workspace/thumbnail.jpg`.
  - `evaluate_thumbnail_ctr(design, channel_dna=...)`: Chấm điểm vùng an toàn YouTube (`NanoThumbnail Safe-Zone`) và độ rõ `168x94` trên di động.
- **Frontend Interactive Workbench (`B:\ALL_TOOLS\CofiDocumentary\static\thumbnail_studio.js`)**:
  - Giao diện **COFI Thumbnail Studio v2 (Fabric.js JSON Layer Canvas + Multi-Card A/B/C/D Test Gallery)** cho phép kéo thả, chỉnh sửa từng lớp độc lập.
- **API Điều Khiển Trực Tiếp Trong App (`http://127.0.0.1:8878`)**:
  - `GET /api/jobs/{job_id}/thumbnail-studio` — Đọc trạng thái `thumbnail_design.json`, danh sách ảnh nền và điểm CTR.
  - `POST /api/jobs/{job_id}/thumbnail-studio/generate-bg` — Gọi Google Labs Flow tạo ảnh nền sạch `16:9` không chữ (`thumb_bg_v1..v4.jpg`).
  - `POST /api/jobs/{job_id}/thumbnail-studio/auto-design` — Vẽ lại toàn bộ 4 phương án `v1..v4` bằng engine `thumbnail_studio.py` theo đúng DNA kênh.
  - `POST /api/jobs/{job_id}/thumbnail-studio/design` — Lưu chỉnh sửa layer JSON và tự động kết xuất lại file `.jpg`.
