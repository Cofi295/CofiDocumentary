# Producer Standards — CofiDocumentary Broadcast Quality Rules

## 1. Nguyên tắc Cốt lõi: Lore là DNA Mẫu — Tuyệt đối Cấm Lười Biếng Rập Khuôn
- **Lore / Editing DNA của kênh chỉ là khung tiêu chuẩn chất lượng**, không phải khuôn mẫu cứng nhắc bắt mọi video hay mọi phân cảnh phải lặp đi lặp lại 1–2 kiểu thiết kế.
- **Đa dạng hóa Bố cục Vox & Bản đồ (`10+ Archetypes`)**:
  - **Bản đồ Full Màn Hình `1920x1080` (`S3_FULLSCREEN_GIS_FLIGHT`, `S4_FULLSCREEN_SATELLITE_RECON`)**: Dùng khi lời thoại miêu tả hành trình liên tỉnh (ví dụ Bắc Kinh → Vân Nam), di lý giữa các trại giam (Trại 1 → Trại 2), hoặc mở rộng địa bàn toàn đô thị. Bản đồ mở full 100% khung hình `1920x1080` với camera bay mượt từ A sang B, vẽ đường lộ trình vàng `0% → 100%`, vòng sóng radar nở tại điểm đến, ghim `① → ② → ③` bật tuần tự theo giọng đọc, cửa sổ PiP video góc trên phải và thanh highlight câu thoại ở đáy.
  - **Bản đồ Chia Cột (`S1_KUNMING_SATELLITE_MAP`, `S2_DUAL_SATELLITE_ROUTE`)**: Dùng khi cần đặt bản đồ vệ tinh cạnh tờ báo hoặc hồ sơ pháp y để đối chiếu trực tiếp.
  - **Báo chí & Hồ sơ Pháp y Đa Kiểu (`N1..N6`)**: Xoay vòng linh hoạt Trang nhất Báo chí, Bản án Tòa án Tối cao, Hồ sơ Trại giam, Bản vẽ Bằng sáng chế, Trục thời gian đa mốc và Bảng đối chứng vật chứng.

## 2. Chuẩn Thị Giác Dịu Mắt Cho Khán Giả Lớn Tuổi (45–70 Tuổi)
- **Chỉ 1 Intro Êm Dịu ở Đầu Video (`00:00`)**: Tuyệt đối không dùng hiệu ứng chớp nháy (strobe/flash) hay lặp lại intro chuyển chương gây mỏi mắt.
- **Không Xé Giấy Lẹm Vào Nhân Vật**: Ảnh và video tư liệu đặt trong khung chữ nhật viền rõ nét kèm nhãn chú thích tiếng Hàn dễ đọc (`40–66px` trên nền giấy kem ấm `#EDE5D2`).
- **Chống Trùng Lặp Tuyệt Đối (`max_uses = 1`)**: Mọi đoạn video footage thật (`S_F*.mp4`), ảnh tư liệu (`S_A*.jpg`), clip Vox (`VOX_*.mp4`) và ảnh AI (`<beat_id>_ai_keyframe.jpg`) chỉ xuất hiện 1 lần duy nhất.

## 3. Kho Âm Thanh Động 28+ SFX Theo Ngữ Cảnh & 5 BGM Theo Cảm Xúc (`documentary/audio_library_manager.py`)
- **2 Sự kiện SFX Foley / Clip theo đúng hoàn cảnh**: Búa tòa án (`sfx_wooden_gavel.mp3`), cửa sắt & bước chân trại giam (`sfx_iron_lock_latch.mp3`, `sfx_prison_corridor_steps.mp3`), sóng radar & gió bay bản đồ (`sfx_radar_sonar_ping.mp3`, `sfx_map_flight_sweep.mp3`), bộ đàm cảnh sát & còi hụ xa (`sfx_police_scanner_radio.mp3`, `sfx_distant_siren.mp3`), bút dạ quang & lật báo (`sfx_feltpen_highlight.mp3`, `sfx_newspaper_unfold.mp3`), đóng dấu đỏ (`sfx_dossier_stamp.mp3`), đồng hồ tích tắc (`sfx_clock_tick_tense.mp3`).
- **5 Bản Nhạc Nền BGM Theo Tâm Trạng Từng Chương**: Tự động chuyển đổi theo 5 hồi cảm xúc và hạ âm lượng mượt mà (`ducking`) khi có giọng đọc.
- **Tự Động Tải Thêm Nhạc / SFX Mới Về Kho (`fetch_missing_audio_asset`)**: Khi kịch bản có bối cảnh hoặc cảm xúc mới chưa có trong kho, AI tự động tải âm thanh CC0 từ Wikimedia Commons, chuẩn hóa âm lượng `-16 LUFS` và lưu vĩnh viễn vào `presets/audio_library/` & `public/audio_library/`.
