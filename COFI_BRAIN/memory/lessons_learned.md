# COFI Lessons Learned — Production Memory

## 1. Bài học về Thiết kế Vox & Bản đồ cho Tệp Khán Giả 45–70 Tuổi (2026-10-25)
- **Vấn đề trước đây**:
  1. Lặp đi lặp lại 1–2 mẫu giấy báo xé rách lẹm vào mặt nhân vật, chớp nháy intro nhiều lần gây mỏi mắt cho người xem lớn tuổi (45–70 tuổi).
  2. Bản đồ vệ tinh và bản đồ hành chính bị nhốt cố định trong khung nhỏ hoặc vẽ tĩnh ngay từ frame đầu (đường lộ trình vàng, vòng tròn đỏ và ghim `①, ②, ③` đứng yên).
  3. Âm thanh SFX lặp đi lặp lại chỉ 1–2 tiếng động máy móc suốt cả video.
- **Giải pháp đã khóa vĩnh viễn vào hệ thống**:
  1. **Chỉ 1 Intro Êm Dịu + 10+ Kiểu Vox Đa Dạng (`N1..N6`, `S1..S4`)**: Nền giấy kem ấm `#EDE5D2`, khung ảnh vuông vắn có nhãn chú thích tiếng Hàn, không xé giấy lẹm vào người.
  2. **Linh hoạt Bản đồ Full Màn Hình `1920x1080` (`S3_FULLSCREEN_GIS_FLIGHT`, `S4_FULLSCREEN_SATELLITE_RECON`) vs. Bản đồ Chia Cột (`S1`, `S2`)**: Khi lời thoại nói về điều động liên tỉnh (Bắc Kinh → Vân Nam), chuyển trại giam (Trại 1 → Trại 2) hoặc mở rộng địa bàn toàn thành phố, bản đồ bung ra Full Màn Hình `1920x1080`, camera bay mượt từ A sang B, đường lộ trình vàng tự vẽ `0% → 100%`, vòng sóng radar nở tại điểm đến, và ghim `① → ② → ③` bật tuần tự theo giọng đọc.
  3. **Kho 28+ SFX Foley Thực Tế & 5 BGM Đa Cảm Xúc + Tự Động Tải Audio Mới (`documentary/audio_library_manager.py`)**: Mỗi cảnh tự động chọn cặp 2 SFX khớp chính xác hoàn cảnh (búa tòa, khóa sắt trại giam, bước chân hành lang, bộ đàm cảnh sát, sóng radar, gió bay bản đồ, bút dạ quang...) và tự động tải thêm âm thanh mới về kho khi cần.
