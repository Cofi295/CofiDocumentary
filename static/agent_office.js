(function () {
  "use strict";

  const STAGE_W = 1440;
  const STAGE_H = 740;

  // 15 Agent Departments (92 Personnel: 15 Leads · 15 Deputies · 62 Specialist Mini-Agents)
  const DIVISION_LABELS_VI = {
    executive: "Ban Chỉ Huy Tối Cao",
    intelligence: "Khối Tình Báo & Nội Dung",
    visual: "Khối Hình Ảnh & Đồ Họa Điều Tra",
    post: "Khối Dựng Phim & Phát Hành",
    quality: "Khối Pháp Y, Kiểm Định & Kỹ Thuật",
  };

  // Symmetric 3-Wing × 5-Column Architectural Studio Campus (15 Pods · 92 Staff)
  // Row 1 (Tầng Bắc · hy=118):   DEPT-00 ➔ DEPT-01 ➔ DEPT-02 ➔ DEPT-03 ➔ DEPT-04
  // Central Atrium (hy=260):     Espresso Bar · Liaison Concourse · Live Telemetry Wall
  // Row 2 (Tầng Trung · hy=410): DEPT-05 ➔ DEPT-06 ➔ DEPT-07 ➔ DEPT-08 (VOX 8NS) ➔ DEPT-09
  // Row 3 (Tầng Nam · hy=628):   DEPT-10 ➔ DEPT-11 ➔ DEPT-12 ➔ DEPT-13 ➔ DEPT-14
  const CHIBI_PROFILES = {
    orchestrator: {
      hx: 154, hy: 118, podW: 262, zone: "north", subZone: "direction", deptCode: "DEPT-00", headcount: 6,
      skin: "#fed7aa", hair: "#1e293b", hairStyle: "beret", hatColor: "#be123c",
      outfit: "#0284c7", accent: "#38bdf8", glasses: "none", prop: "📣",
      shortTitleVi: "Ban Điều Hành",
      nickVi: "DEPT-00 · Ban Điều Hành (6 NS)",
      greetVi: "Chào sếp! Phòng 00 (@orchestrator_lead · @orchestrator_deputy · 4 Chuyên viên) đang điều phối toàn bộ 15 Phòng Ban × 92 Nhân sự trong xưởng!",
      roleVi: "Tổ trưởng @orchestrator_lead giữ nhịp tổng thể 8 công đoạn, phân việc đúng Phòng Ban và kiểm soát bàn giao liên phòng.",
      chillVi: [
        "☕ Nhấp ngụm Espresso mà mắt vẫn dán vào bảng tiến độ 15 Phòng Ban!",
        "🎬 15 Phòng Ban · 92 Nhân sự phối hợp nhịp nhàng thế này là phim ra rạp nét căng!",
      ],
    },
    radar: {
      hx: 434, hy: 118, podW: 262, zone: "north", subZone: "direction", deptCode: "DEPT-01", headcount: 6,
      skin: "#fde68a", hair: "#0f766e", hairStyle: "spiky", hatColor: "#06b6d4",
      outfit: "#0d9488", accent: "#2dd4bf", glasses: "visor", prop: "📡",
      shortTitleVi: "Tình Báo Radar",
      nickVi: "DEPT-01 · Phòng Radar (6 NS)",
      greetVi: "Tín hiệu sóng sạch 100% sếp ơi! Phòng 01 (@radar_lead · @radar_deputy · 4 Chuyên viên) đã quét trùng lặp đề tài kỹ lưỡng!",
      roleVi: "Phòng Tình Báo Đề Tài & Radar săn đề tài đột phá theo từng hồ sơ kênh và chặn đứng mọi nguy cơ trùng lặp vụ án cũ.",
      chillVi: [
        "📡 Đề tài tập này qua Pre-Flight xanh mượt, giờ tôi pha ly trà hóng anh em dựng!",
        "🪴 Tưới cây xíu lấy cảm hứng săn vụ án tiếp theo cho kênh!",
      ],
    },
    research: {
      hx: 714, hy: 118, podW: 262, zone: "north", subZone: "editorial", deptCode: "DEPT-02", headcount: 6,
      skin: "#fed7aa", hair: "#451a03", hairStyle: "detective", hatColor: "#92400e",
      outfit: "#b45309", accent: "#fbbf24", glasses: "round", prop: "🔎",
      shortTitleVi: "Điều Tra Hồ Sơ",
      nickVi: "DEPT-02 · Phòng Hồ Sơ (6 NS)",
      greetVi: "Suỵt! Phòng 02 (@research_lead · @research_deputy · 4 Chuyên viên) đã đối chiếu chéo mọi mốc ngày giờ, biển số, con số trong hồ sơ gốc!",
      roleVi: "Phòng Điều Tra Hồ Sơ & Xác Thực Chứng Cứ đào tư liệu gốc đa nguồn, khóa chặt mốc thời gian, địa danh và chứng cứ xác thực 100%.",
      chillVi: [
        "🔎 Hồ sơ điều tra gốc đã bàn giao chắc nịch, ra sofa duỗi lưng chút nào!",
        "☕ Uống miếng cà phê đen cho tỉnh táo như thám tử thứ thiệt!",
      ],
    },
    script: {
      hx: 996, hy: 118, podW: 262, zone: "north", subZone: "editorial", deptCode: "DEPT-03", headcount: 6,
      skin: "#ffedd5", hair: "#312e81", hairStyle: "parted", hatColor: "#6366f1",
      outfit: "#4f46e5", accent: "#a5b4fc", glasses: "round", prop: "🖋️",
      shortTitleVi: "Biên Kịch",
      nickVi: "DEPT-03 · Phòng Biên Kịch (6 NS)",
      greetVi: "Chào sếp! Phòng 03 (@script_lead · @script_deputy · 4 Chuyên viên) đã gọt nhịp thở và phanh câu ngắn đúng điểm rơi cao trào!",
      roleVi: "Phòng Biên Kịch & Tự Sự Điện Ảnh chuyển hóa hồ sơ điều tra thành kịch bản văn nói truyền hình cuốn hút, chuẩn hóa 100% âm đọc cho TTS.",
      chillVi: [
        "🖋️ Gọt xong kịch bản ưng cái bụng quá, làm ngụm Latte ấm thôi!",
        "📄 Đứng xem bảng tiến độ nghe Phòng 04 @voice đọc thoại mình viết sướng rơn!",
      ],
    },
    voice: {
      hx: 1280, hy: 118, podW: 262, zone: "north", subZone: "editorial", deptCode: "DEPT-04", headcount: 6,
      skin: "#fde68a", hair: "#701a75", hairStyle: "headset", hatColor: "#ec4899",
      outfit: "#db2777", accent: "#f472b6", glasses: "none", prop: "🎙️",
      shortTitleVi: "Phòng Thu Voice",
      nickVi: "DEPT-04 · Phòng Thu Voice (6 NS)",
      greetVi: "Alo 1-2-3 ON AIR! Phòng 04 (@voice_lead · @voice_deputy · 4 Chuyên viên) đang giữ giọng đọc trầm ấm, tròn vành rõ chữ cho từng câu thoại!",
      roleVi: "Phòng Đạo Diễn Giọng Đọc & Thu Âm TTS thu âm từng câu trên GPU, nghe lại bằng Whisper để bắt lỗi vấp âm và khóa chuẩn SRT.",
      chillVi: [
        "🍵 Thu xong ca dài, ra quầy làm ngụm trà ấm giọng ngay!",
        "🎧 Phụ đề Whisper khớp từng chữ một rồi, nhường sân cho Khối Hình Ảnh trổ tài!",
      ],
    },
    visuals: {
      hx: 154, hy: 410, podW: 262, zone: "central", subZone: "cinema", deptCode: "DEPT-05", headcount: 6,
      skin: "#fed7aa", hair: "#1e3a8a", hairStyle: "cap", hatColor: "#2563eb",
      outfit: "#1d4ed8", accent: "#60a5fa", glasses: "none", prop: "🎬",
      shortTitleVi: "Phân Cảnh 1-1",
      nickVi: "DEPT-05 · Phòng Phân Cảnh (6 NS)",
      greetVi: "Action! Phòng 05 (@visuals_lead · @visuals_deputy · 4 Chuyên viên) chia mỗi câu thoại một cảnh riêng 1-1, điều phối chuẩn xác FTG / VOX / AI!",
      roleVi: "Phòng Đạo Diễn Phân Cảnh & Điều Phối Thị Giác chia Storyboard 1-1 khớp 100% kịch bản và điều phối tỷ lệ REAL_FTG / VOX / AI_4D.",
      chillVi: [
        "🎬 Bảng phân cảnh 1-1 đã giao tận tay Phòng 06, 07, 08, nghỉ tay uống ngụm nước mát!",
        "🛋️ Ngồi sofa ngắm xưởng vẽ lên hình từng khung cảnh đúng ý đồ đạo diễn!",
      ],
    },
    footage: {
      hx: 434, hy: 410, podW: 262, zone: "central", subZone: "cinema", deptCode: "DEPT-06", headcount: 6,
      skin: "#fde68a", hair: "#3f3f46", hairStyle: "parted", hatColor: "#0284c7",
      outfit: "#0369a1", accent: "#38bdf8", glasses: "square", prop: "🎞️",
      shortTitleVi: "Tư Liệu Thật",
      nickVi: "DEPT-06 · Phòng Tư Liệu (6 NS)",
      greetVi: "Phòng 06 (@footage_lead · @footage_deputy · 4 Chuyên viên) soi 3 khung hình 15%-50%-85%, clip nào dính logo hay sai vụ án là loại thẳng!",
      roleVi: "Phòng Săn Lùng & Kiểm Định Tư Liệu Thật kiểm định 3-Frame nghiêm ngặt, đảm bảo khung hình sạch sẽ, khớp ngữ nghĩa 100%.",
      chillVi: [
        "🎞️ Tư liệu thật đã cắt sạch 3-Frame và bàn giao sang Phòng 09 @edit!",
        "☕ Pha ly cà phê sữa đợi anh em bước Dựng Phim gọi là có mặt ngay!",
      ],
    },
    ai_visual: {
      hx: 714, hy: 410, podW: 262, zone: "central", subZone: "cinema", deptCode: "DEPT-07", headcount: 6,
      skin: "#ffedd5", hair: "#581c87", hairStyle: "beret", hatColor: "#9333ea",
      outfit: "#7e22ce", accent: "#d8b4fe", glasses: "none", prop: "🎨",
      shortTitleVi: "Điện Ảnh AI 4D",
      nickVi: "DEPT-07 · Phòng AI 4D (6 NS)",
      greetVi: "Phòng 07 (@ai_visual_lead · @ai_visual_deputy · 4 Chuyên viên) giữ ánh sáng điện ảnh 16:9 góc kín, không lộ mặt giả AI!",
      roleVi: "Phòng Thiết Kế Điện Ảnh AI 4D sinh ảnh/video tái dựng góc kín over-the-shoulder/silhouette chuẩn chất liệu hồ sơ kênh.",
      chillVi: [
        "🎨 Đang pha bảng màu ánh sáng điện ảnh chuẩn bị cho mẻ tranh tiếp theo!",
        "☕ Họa sĩ cũng cần chút caffeine để lên màu thật nghệ chứ ạ!",
      ],
    },
    vox: {
      hx: 998, hy: 410, podW: 274, zone: "central", subZone: "cinema", deptCode: "DEPT-08", headcount: 8,
      skin: "#fed7aa", hair: "#064e3b", hairStyle: "spiky", hatColor: "#10b981",
      outfit: "#059669", accent: "#6ee7b7", glasses: "visor", prop: "🗺️",
      shortTitleVi: "Đồ Họa VOX ⭐",
      nickVi: "DEPT-08 · Phòng Đồ Họa VOX (8 NS)",
      greetVi: "Phòng 08 (@vox_lead · @vox_deputy · 6 Chuyên viên) biên dịch từng câu thoại thành Bàn Giấy Cắt Dán 10 Archetypes & Bản Đồ 3D GIS, 12 Motion Verbs độc bản 0% copy-paste!",
      roleVi: "Phòng Thiết Kế Đồ Họa Điều Tra VOX (8 nhân sự) vận hành dây chuyền 6 chuyên viên: @vox_voice_reader → @vox_desk_designer → @vox_asset_creator → @vox_motion_designer → @vox_choreography_animator → @vox_spatial_locator.",
      chillVi: [
        "🗺️ 6 chuyên viên VOX đang ủ sa bàn 10 Editorial Desk Archetypes & 3D GIS cực ngầu!",
        "🪴 Đứng cạnh cây xanh nhẩm tính 12 Motion Verbs t1→t2→t3 cho từng câu thoại!",
      ],
    },
    edit: {
      hx: 1282, hy: 410, podW: 262, zone: "central", subZone: "cinema", deptCode: "DEPT-09", headcount: 6,
      skin: "#fde68a", hair: "#7c2d12", hairStyle: "headset", hatColor: "#ea580c",
      outfit: "#c2410c", accent: "#fdba74", glasses: "none", prop: "✂️",
      shortTitleVi: "Dựng Remotion",
      nickVi: "DEPT-09 · Phòng Dựng Phim (6 NS)",
      greetVi: "Phòng 09 (@edit_lead · @edit_deputy · 4 Chuyên viên) đã sẵn sàng lắp ráp Timeline Remotion, BGM Story-Arc 8–12 đoạn & Motion-Bound SFX!",
      roleVi: "Phòng Đạo Diễn Dựng Phim & Âm Thanh Remotion lắp ráp toàn bộ Tư liệu thật, VOX, AI 4D, giọng đọc, BGM Story-Arc và SFX gắn chuyển động.",
      chillVi: [
        "✂️ Đang khởi động sẵn máy dựng, chờ bàn giao đủ tư liệu là cắt phim liền!",
        "☕ Làm cốc cà phê đậm đặc trước khi vào ca dựng đại cảnh dài hơi!",
      ],
    },
    seo: {
      hx: 154, hy: 628, podW: 262, zone: "south", subZone: "cinema", deptCode: "DEPT-10", headcount: 6,
      skin: "#ffedd5", hair: "#831843", hairStyle: "bob", hatColor: "#e11d48",
      outfit: "#be123c", accent: "#fda4af", glasses: "round", prop: "🚀",
      shortTitleVi: "SEO & Thumbnail",
      nickVi: "DEPT-10 · Phòng SEO & Thumb (6 NS)",
      greetVi: "Phòng 10 (@seo_lead · @seo_deputy · 4 Chuyên viên) đóng gói Tiêu đề, Thumbnail tương phản cao chuẩn CTR!",
      roleVi: "Phòng Chiến Lược Phát Hành, SEO & Thumbnail tối ưu hóa siêu dữ liệu YouTube và thiết kế Thumbnail bắt mắt trên mọi kích thước màn hình.",
      chillVi: [
        "🚀 Đang nháp sẵn mấy bố cục Thumbnail cực hút mắt ở quầy cà phê!",
        "🛋️ Ngồi sofa nghiên cứu tâm lý cú click đầu tiên của khán giả!",
      ],
    },
    evidence_qa: {
      hx: 434, hy: 628, podW: 262, zone: "south", subZone: "qa", deptCode: "DEPT-11", headcount: 6,
      skin: "#fef3c7", hair: "#1e293b", hairStyle: "bun", hatColor: "#f59e0b",
      outfit: "#b45309", accent: "#fde68a", glasses: "square", prop: "⚖️",
      shortTitleVi: "Thanh Tra Pháp Y",
      nickVi: "DEPT-11 · Phòng Pháp Y QA (6 NS)",
      greetVi: "Phòng 11 (@evidence_qa_lead · @evidence_qa_deputy · 4 Chuyên viên) gác 8 cổng phản biện! Chưa đạt 100% là trả hồ sơ bắt tự sửa ngay!",
      roleVi: "Phòng Thanh Tra Pháp Y & Phản Biện Chất Lượng độc lập kiểm định đầu ra mọi phòng ban: đối chiếu hồ sơ gốc, soi 3-frame, bắt lỗi copy-paste motion VOX.",
      chillVi: [
        "⚖️ Lau kính lúp thật sáng, các Phòng Ban nộp bài lên là tôi soi từng chi tiết!",
        "☕ Uống trà nóng giữ cái đầu lạnh — không bao giờ duyệt ẩu!",
      ],
    },
    qc: {
      hx: 714, hy: 628, podW: 262, zone: "south", subZone: "qa", deptCode: "DEPT-12", headcount: 6,
      skin: "#fed7aa", hair: "#0f172a", hairStyle: "cap", hatColor: "#0284c7",
      outfit: "#0f766e", accent: "#5eead4", glasses: "square", prop: "🛡️",
      shortTitleVi: "Kiểm Định Master",
      nickVi: "DEPT-12 · Phòng Duyệt Master (6 NS)",
      greetVi: "Phòng 12 (@qc_lead · @qc_deputy · 4 Chuyên viên) soi từ frame 0.0s tới tận 3.8 giây nhạc kết cuối cùng mới cấp phép xuất xưởng!",
      roleVi: "Phòng Kiểm Định Xuất Xưởng Master MP4 đo chuẩn âm lượng LUFS, quét màn đen/dead-air, soi frame thực tế và bảo vệ đuôi nhạc kết.",
      chillVi: [
        "🛡️ Đang cân chỉnh máy chiếu Master và đồng hồ đo sóng âm cuối phim!",
        "🛋️ Chờ bản dựng hoàn chỉnh gửi sang là mở phòng chiếu kiểm định ngay!",
      ],
    },
    dev: {
      hx: 996, hy: 628, podW: 262, zone: "south", subZone: "qa", deptCode: "DEPT-13", headcount: 6,
      skin: "#fde68a", hair: "#1e3a8a", hairStyle: "hardhat", hatColor: "#eab308",
      outfit: "#334155", accent: "#94a3b8", glasses: "none", prop: "⚙️",
      shortTitleVi: "Kỹ Thuật Lõi",
      nickVi: "DEPT-13 · Phòng Kỹ Thuật (6 NS)",
      greetVi: "Phòng 13 (@dev_lead · @dev_deputy · 4 Chuyên viên) giữ hệ thống lõi và giao diện 15 Phòng Ban × 92 Nhân sự vận hành êm ru, tách biệt 100% với hồ sơ kênh!",
      roleVi: "Phòng Kỹ Thuật Lõi & Phát Triển Hệ Thống bảo trì hạ tầng công cụ, đồng bộ Backend-UI và chạy kiểm thử tự động.",
      chillVi: [
        "⚙️ Kiểm tra áp suất GPU mát rượi, ra làm ly cà phê với Phòng 14 @debug!",
        "📊 Đứng ngắm dây chuyền 15 Phòng Ban tự động chạy trơn tru!",
      ],
    },
    debug: {
      hx: 1280, hy: 628, podW: 262, zone: "south", subZone: "qa", deptCode: "DEPT-14", headcount: 6,
      skin: "#ffedd5", hair: "#14532d", hairStyle: "doctor", hatColor: "#22c55e",
      outfit: "#15803d", accent: "#86efac", glasses: "round", prop: "🩺",
      shortTitleVi: "Chẩn Đoán Cứu Hộ",
      nickVi: "DEPT-14 · Phòng Chẩn Đoán (6 NS)",
      greetVi: "Phòng 14 (@debug_lead · @debug_deputy · 4 Chuyên viên) trực cấp cứu kỹ thuật 24/7, bắt mạch gốc lỗi và khôi phục checkpoint an toàn!",
      roleVi: "Phòng Chẩn Đoán Sự Cố & Phục Hồi Khẩn Cấp khoanh vùng gốc lỗi (Root Cause) và tự động sửa chữa hạ tầng.",
      chillVi: [
        "🩺 Cả 15 Phòng Ban khỏe mạnh 0 ca cấp cứu, bác sĩ đi tưới cây thư giãn đây!",
        "☕ Ngồi nhâm nhi trà thảo mộc canh gác sự ổn định cho cả đoàn làm phim!",
      ],
    },
  };

  // Complete 92-Personnel Roster across all 15 Departments (15 Leads + 15 Deputies + 62 Specialists)
  const DEFAULT_DEPT_ROSTER_92 = {
    orchestrator: {
      lead: { id: "orchestrator_lead", handle: "@orchestrator_lead", shortTag: "👑 Trưởng", title_vi: "Tổ trưởng Ban Điều Hành Trung Tâm (Chief Executive Dispatcher)", role_vi: "Chỉ huy tổng thể 8 phase, phân công nhiệm vụ và ký duyệt bàn giao liên phòng." },
      deputy: { id: "orchestrator_deputy", handle: "@orchestrator_deputy", shortTag: "🛡️ Phó", title_vi: "Tổ phó Kiểm Soát Luồng Phase & Đồng Bộ Liên Phòng", role_vi: "Rà soát checklist đồng bộ giữa 15 phòng ban và kiểm soát hạn mức chất liệu." },
      specialists: [
        { id: "orchestrator_dna_binder", handle: "@orchestrator_dna_binder", shortTag: "L1 HồSơ", title_vi: "Chuyên viên Khóa Hồ Sơ Kênh & Cấu Hình Chuẩn", role_vi: "Đọc hồ sơ kênh, khóa bảng màu, giọng đọc và tỷ lệ hình ảnh." },
        { id: "orchestrator_phase_router", handle: "@orchestrator_phase_router", shortTag: "L2 Luồng", title_vi: "Chuyên viên Phân Luồng Phase & Cắt Việc Liên Phòng", role_vi: "Chia nhỏ yêu cầu sản xuất thành gói công việc gửi tới 14 phòng ban." },
        { id: "orchestrator_quota_balancer", handle: "@orchestrator_quota_balancer", shortTag: "L3 TỷLệ", title_vi: "Chuyên viên Cân Đối Ngân Sách Visual & Nhịp Độ", role_vi: "Giám sát tỷ lệ REAL_FTG / VOX / AI_4D / TEXT_BEAT theo ngưỡng kênh." },
        { id: "orchestrator_handoff_auditor", handle: "@orchestrator_handoff_auditor", shortTag: "L4 Giao", title_vi: "Chuyên viên Kiểm Soát Bàn Giao & Hồi Tiếp Sửa Lỗi", role_vi: "Thu thập biên bản nghiệm thu từ từng phòng ban và chuyển ký duyệt." },
      ],
    },
    radar: {
      lead: { id: "radar_lead", handle: "@radar_lead", shortTag: "👑 Trưởng", title_vi: "Tổ trưởng Trinh Sát Chủ Đề & Chiến Lược Tập Phim", role_vi: "Quyết định góc tiếp cận vụ án, duyệt chủ đề đột phá và chống trùng lặp." },
      deputy: { id: "radar_deputy", handle: "@radar_deputy", shortTag: "🛡️ Phó", title_vi: "Tổ phó Phân Tích Dữ Liệu Khán Giả & Đối Thủ", role_vi: "Kiểm tra độ phủ tư liệu thật và sức hút nghịch lý mở màn." },
      specialists: [
        { id: "radar_signal_scanner", handle: "@radar_signal_scanner", shortTag: "L1 Quét", title_vi: "Chuyên viên Quét Tín Hiệu Đột Biến (Outlier Scanner)", role_vi: "Quét dữ liệu các vụ án/sự kiện có lượng tương tác vượt chuẩn." },
        { id: "radar_competitor_analyst", handle: "@radar_competitor_analyst", shortTag: "L2 ĐốiThủ", title_vi: "Chuyên viên Mổ Xẻ Khoảng Trống Đối Thủ (Gap Analyst)", role_vi: "Phân tích video cùng chủ đề để tìm chi tiết đắt giá chưa ai khai thác." },
        { id: "radar_hook_architect", handle: "@radar_hook_architect", shortTag: "L3 MởMàn", title_vi: "Chuyên viên Thiết Kế Góc Mở Màn & Nghịch Lý Trung Tâm", role_vi: "Xây dựng câu hỏi nghịch lý 30 giây đầu khóa chặt sự chú ý." },
        { id: "radar_feasibility_scout", handle: "@radar_feasibility_scout", shortTag: "L4 Nguồn", title_vi: "Chuyên viên Thẩm Định Nguồn Tư Liệu Sơ Bộ", role_vi: "Kiểm tra nhanh khả năng tìm phóng sự truyền hình, ảnh hồ sơ và bản đồ." },
      ],
    },
    research: {
      lead: { id: "research_lead", handle: "@research_lead", shortTag: "👑 Trưởng", title_vi: "Tổ trưởng Điều Tra Hồ Sơ & Thẩm Định Sự Thật", role_vi: "Chỉ huy khai thác hồ sơ gốc và khóa biên bản sự thật vụ án." },
      deputy: { id: "research_deputy", handle: "@research_deputy", shortTag: "🛡️ Phó", title_vi: "Tổ phó Kiểm Chứng Chéo & Chuẩn Hóa Thực Thể", role_vi: "Rà soát chéo ngày giờ, con số, tên nhân vật và tọa độ địa lý." },
      specialists: [
        { id: "research_primary_harvester", handle: "@research_primary_harvester", shortTag: "L1 BảnÁn", title_vi: "Chuyên viên Khai Thác Tài Liệu Gốc & Bản Án", role_vi: "Truy tìm văn bản tòa án, thông cáo điều tra và báo chí lưu trữ." },
        { id: "research_timeline_reconstructor", handle: "@research_timeline_reconstructor", shortTag: "L2 MốcGiờ", title_vi: "Chuyên viên Dựng Trục Thời Gian Pháp Y", role_vi: "Sắp xếp toàn bộ diễn biến vụ án theo giờ/ngày/tháng/năm kèm bằng chứng." },
        { id: "research_entity_mapper", handle: "@research_entity_mapper", shortTag: "L3 TọaĐộ", title_vi: "Chuyên viên Lập Bản Đồ Nhân Vật & Tọa Độ Địa Lý", role_vi: "Chuẩn hóa tên nhân vật, tổ chức, địa danh và tọa độ điểm nóng." },
        { id: "research_fact_cross_checker", handle: "@research_fact_cross_checker", shortTag: "L4 Kiểm", title_vi: "Chuyên viên Kiểm Chứng Chéo & Khử Sai Lệch", role_vi: "Rà soát chéo các con số, lời khai và khử hoàn toàn thông tin suy diễn." },
      ],
    },
    script: {
      lead: { id: "script_lead", handle: "@script_lead", shortTag: "👑 Trưởng", title_vi: "Tổ trưởng Biên Kịch Trưởng & Đạo Diễn Tự Sự", role_vi: "Chỉ đạo cấu trúc tự sự điện ảnh và duyệt bản thảo script.md cuối cùng." },
      deputy: { id: "script_deputy", handle: "@script_deputy", shortTag: "🛡️ Phó", title_vi: "Tổ phó Biên Tập Nhịp Điệu & Kiểm Soát Độ Dài", role_vi: "Kiểm soát nhịp câu văn nói, độ dài chương hồi và mật độ chi tiết thị giác." },
      specialists: [
        { id: "script_arc_architect", handle: "@script_arc_architect", shortTag: "L1 Chương", title_vi: "Chuyên viên Thiết Kế Khung Chương Hồi & Điểm Nút", role_vi: "Chia hồ sơ vụ án thành 6-7 chương có cao trào và bước ngoặt phá án." },
        { id: "script_cold_open_writer", handle: "@script_cold_open_writer", shortTag: "L2 MởĐầu", title_vi: "Chuyên viên Viết Mở Màn Cold Open & Chuyển Chương", role_vi: "Chế tác phần mở đầu đi thẳng vào hiện trường và câu kết chương giữ chân." },
        { id: "script_investigative_drafter", handle: "@script_investigative_drafter", shortTag: "L3 Thoại", title_vi: "Chuyên viên Chấp Bút Lời Thoại Điều Tra Chi Tiết", role_vi: "Viết toàn bộ lời bình từng chương giàu chi tiết vật chứng và không gian." },
        { id: "script_visual_cue_annotator", handle: "@script_visual_cue_annotator", shortTag: "L4 Nhịp", title_vi: "Chuyên viên Chuẩn Hóa Nhịp Câu & Tín Hiệu Hình Ảnh", role_vi: "Tách câu ngắn tự nhiên cho TTS và gắn neo dữ kiện hình ảnh." },
      ],
    },
    voice: {
      lead: { id: "voice_lead", handle: "@voice_lead", shortTag: "👑 Trưởng", title_vi: "Tổ trưởng Đạo Diễn Phòng Thu & Thanh Âm", role_vi: "Chỉ đạo biểu cảm giọng đọc, nhịp ngắt nghỉ và ký duyệt narration.wav." },
      deputy: { id: "voice_deputy", handle: "@voice_deputy", shortTag: "🛡️ Phó", title_vi: "Tổ phó Kỹ Thuật Âm Thanh & Đồng Bộ Word-Timestamp", role_vi: "Kiểm định Whisper ASR chống vấp âm và khóa chuẩn SRT từng từ." },
      specialists: [
        { id: "voice_prosody_mapper", handle: "@voice_prosody_mapper", shortTag: "L1 Nhịp", title_vi: "Chuyên viên Thiết Kế Nhịp Thở & Ngắt Nghỉ Cảm Xúc", role_vi: "Phân tích tâm lý từng câu thoại để gán tốc độ đọc và khoảng lặng." },
        { id: "voice_tts_synthesizer", handle: "@voice_tts_synthesizer", shortTag: "L2 ThuTTS", title_vi: "Chuyên viên Tổng Hợp Giọng Đọc Phòng Thu (CofiVoice)", role_vi: "Vận hành CofiVoice GPU sinh các đoạn âm thanh chất lượng cao." },
        { id: "voice_forced_aligner", handle: "@voice_forced_aligner", shortTag: "L3 KhớpTừ", title_vi: "Chuyên viên Đồng Bộ Từng Từ & Phụ Đề SRT", role_vi: "Trích xuất tọa độ thời gian chính xác của từng từ và mệnh đề clauses[0..2]." },
        { id: "voice_acoustics_mastering", handle: "@voice_acoustics_mastering", shortTag: "L4 LUFS", title_vi: "Chuyên viên Ghép Nối & Chuẩn Hóa Âm Lượng", role_vi: "Ghép mượt narration.wav, cân bằng EQ/LUFS và đệm âm cuối câu." },
      ],
    },
    visuals: {
      lead: { id: "visuals_lead", handle: "@visuals_lead", shortTag: "👑 Trưởng", title_vi: "Tổ trưởng Đạo Diễn Phân Cảnh & Bố Cục Hình Ảnh", role_vi: "Chỉ đạo chia beat 1-1 theo câu thoại và ký duyệt visual_manifest.json." },
      deputy: { id: "visuals_deputy", handle: "@visuals_deputy", shortTag: "🛡️ Phó", title_vi: "Tổ phó Kiểm Soát Tỷ Lệ Cảnh & Liên Kết Beat", role_vi: "Đảm bảo 100% lời thoại có visual tương ứng và đúng tỷ lệ REAL_FTG/VOX/AI." },
      specialists: [
        { id: "visuals_beat_segmenter", handle: "@visuals_beat_segmenter", shortTag: "L1 Beat", title_vi: "Chuyên viên Cắt Nhịp Lời Thoại Thành Beat Hình Ảnh", role_vi: "Chia toàn bộ lời bình thành các đơn vị cảnh 3-7 giây trọn vẹn ý nghĩa." },
        { id: "visuals_modality_router", handle: "@visuals_modality_router", shortTag: "L2 Luồng", title_vi: "Chuyên viên Phân Luồng Chất Liệu (FTG / VOX / AI)", role_vi: "Quyết định mỗi beat dùng REAL_FTG, VOX / 3D GIS, AI_4D hay TEXT_BEAT." },
        { id: "visuals_query_compiler", handle: "@visuals_query_compiler", shortTag: "L3 Query", title_vi: "Chuyên viên Biên Soạn Truy Vấn Tư Liệu & Chỉ Đạo Cảnh", role_vi: "Viết bộ từ khóa đa ngôn ngữ cho tư liệu thật và mô tả minh họa VOX/AI." },
        { id: "visuals_continuity_checker", handle: "@visuals_continuity_checker", shortTag: "L4 Mạch", title_vi: "Chuyên viên Kiểm Tra Mạch Thị Giác & Khóa Manifest", role_vi: "Rà soát sự liền mạch cảm xúc giữa các cảnh kế tiếp trong visual_manifest.json." },
      ],
    },
    footage: {
      lead: { id: "footage_lead", handle: "@footage_lead", shortTag: "👑 Trưởng", title_vi: "Tổ trưởng Đạo Diễn Tư Liệu Hiện Trường", role_vi: "Chỉ đạo săn lùng phóng sự gốc đúng vụ án và ký duyệt kho clip S_F*.mp4." },
      deputy: { id: "footage_deputy", handle: "@footage_deputy", shortTag: "🛡️ Phó", title_vi: "Tổ phó Kiểm Định Khung Hình 3-Frame & Chống Trùng", role_vi: "Soi 3 khung hình 15%-50%-85%, loại bỏ MC trường quay, logo đài và phụ đề." },
      specialists: [
        { id: "footage_source_hunter", handle: "@footage_source_hunter", shortTag: "L1 Nguồn", title_vi: "Chuyên viên Săn Tìm Nguồn Phóng Sự Gốc", role_vi: "Tìm kiếm và tải bản tin điều tra, hồ sơ tòa án, CCTV và cảnh quay thực địa." },
        { id: "footage_storyboard_prober", handle: "@footage_storyboard_prober", shortTag: "L2 Lưới100", title_vi: "Chuyên viên Trích Xuất Storyboard & Lưới Tọa Độ 100px", role_vi: "Trích xuất bảng ảnh Storyboard theo giây và ảnh lưới tọa độ 100px." },
        { id: "footage_semantic_selector", handle: "@footage_semantic_selector", shortTag: "L3 SoiGiây", title_vi: "Chuyên viên Soi Mắt Chọn Giây Khớp Nghĩa Lời Thoại", role_vi: "Chọn chính xác giây bắt đầu/kết thúc khớp 100% vật chứng trong câu voice." },
        { id: "footage_safe_crop_engineer", handle: "@footage_safe_crop_engineer", shortTag: "L4 Crop", title_vi: "Chuyên viên Cắt Khung Safe-Crop & Khử Logo/Phụ Đề", role_vi: "Tính toán crop=W:H:X:Y trên lưới 100px giữ trọn chủ thể và sạch bóng chữ." },
      ],
    },
    ai_visual: {
      lead: { id: "ai_visual_lead", handle: "@ai_visual_lead", shortTag: "👑 Trưởng", title_vi: "Tổ trưởng Đạo Diễn Mỹ Thuật Tái Dựng AI 4D", role_vi: "Chỉ đạo mỹ thuật góc kín điện ảnh và ký duyệt bộ ảnh/video AI 16:9." },
      deputy: { id: "ai_visual_deputy", handle: "@ai_visual_deputy", shortTag: "🛡️ Phó", title_vi: "Tổ phó Kiểm Định Mỹ Thuật & Chống Chữ Lạ", role_vi: "Kiểm tra không lộ mặt giả AI, không có biển chữ sai và đúng bảng màu kênh." },
      specialists: [
        { id: "ai_visual_scene_interpreter", handle: "@ai_visual_scene_interpreter", shortTag: "L1 GócKín", title_vi: "Chuyên viên Phân Tích Tâm Lý & Không Gian Góc Kín", role_vi: "Xác định khoảnh khắc nội tâm, góc máy over-the-shoulder/silhouette và đạo cụ." },
        { id: "ai_visual_prompt_architect", handle: "@ai_visual_prompt_architect", shortTag: "L2 Prompt", title_vi: "Chuyên viên Thiết Kế Prompt Điện Ảnh & Ánh Sáng", role_vi: "Biên soạn prompt chuyên sâu với tiêu cự, ánh sáng tương phản và chất liệu kênh." },
        { id: "ai_visual_image_synthesizer", handle: "@ai_visual_image_synthesizer", shortTag: "L3 Vẽ16:9", title_vi: "Chuyên viên Sinh Ảnh Minh Họa Độ Phân Giải Cao", role_vi: "Vận hành trình tạo ảnh AI xuất keyframe 16:9 sắc nét chuẩn điện ảnh." },
        { id: "ai_visual_retouch_inspector", handle: "@ai_visual_retouch_inspector", shortTag: "L4 Màu4D", title_vi: "Chuyên viên Hiệu Chỉnh Màu Sắc & Lớp Parallax 4D", role_vi: "Cân chỉnh độ tương phản, hạt phim và vùng trọng tâm cho chuyển động 4D." },
      ],
    },
    vox: {
      lead: { id: "vox_lead", handle: "@vox_lead", shortTag: "👑 Trưởng", title_vi: "Tổ trưởng Đạo Diễn Đồ Họa Điều Tra VOX", role_vi: "Chỉ đạo biên dịch câu thoại thành Bàn Biên Tập Cắt Dán 10 Archetypes & 3D GIS." },
      deputy: { id: "vox_deputy", handle: "@vox_deputy", shortTag: "🛡️ Phó", title_vi: "Tổ phó Kiến Trúc Bàn Biên Tập & Kiểm Định AST", role_vi: "Kiểm định AST 0% hộp chữ dashboard, 0% copy-paste motion và chuẩn vùng an toàn." },
      specialists: [
        { id: "vox_voice_reader", handle: "@vox_voice_reader", shortTag: "L1 Voice", title_vi: "Chuyên viên Đọc Hiểu Câu Voice & Kịch Bản Visual VOX", role_vi: "Đọc hiểu sâu từng câu thoại và 3 mệnh đề clauses[0..2], xác định vật chứng/sơ đồ." },
        { id: "vox_desk_designer", handle: "@vox_desk_designer", shortTag: "L2 Bàn", title_vi: "Chuyên viên Thiết Kế Bố Cục Bàn Biên Tập & Sơ Đồ SVG", role_vi: "Thiết kế bố cục cắt dán trên bàn #E4DDCF / <BlackCard> và vẽ sơ đồ SVG tay." },
        { id: "vox_asset_creator", handle: "@vox_asset_creator", shortTag: "L3 RGBA", title_vi: "Chuyên viên Tạo Ảnh Đạo Cụ & Cắt Sticker RGBA", role_vi: "Tách nền trong suốt RGBA cho <DieCutSticker>, <VoxPhotoPaper>, <TornClipping>." },
        { id: "vox_motion_designer", handle: "@vox_motion_designer", shortTag: "L4 Motion", title_vi: "Chuyên viên Thiết Kế Chuyển Động & Camera Độc Bản", role_vi: "Chọn đúng 1 trong 12 Động tác Vật lý (motion_intent) và quỹ đạo <World cam> 30fps." },
        { id: "vox_choreography_animator", handle: "@vox_choreography_animator", shortTag: "L5 12fps", title_vi: "Chuyên viên Biên Đạo Nhịp 12fps t1->t2->t3 & Vật Lý", role_vi: "Biên đạo 3 pha t1->t2->t3 khớp từng chữ bằng nhịp cắt giấy 12fps (step12)." },
        { id: "vox_spatial_locator", handle: "@vox_spatial_locator", shortTag: "L6 TọaĐộ", title_vi: "Chuyên viên Định Vị Tọa Độ 100px & Khoanh Manh Mối", role_vi: "Đo lưới 100px khóa cứng <RedCircle>, <OpticalLoupe>, <Underline> và ghim 3D GIS." },
      ],
    },
    edit: {
      lead: { id: "edit_lead", handle: "@edit_lead", shortTag: "👑 Trưởng", title_vi: "Tổ trưởng Đạo Diễn Dựng Phim & Hòa Âm Tổng Thể", role_vi: "Chỉ đạo lắp ráp Timeline Remotion, BGM Story-Arc 8-12 đoạn và Motion-Bound SFX." },
      deputy: { id: "edit_deputy", handle: "@edit_deputy", shortTag: "🛡️ Phó", title_vi: "Tổ phó Kỹ Thuật Timeline & Kiểm Soát Đồng Bộ Frame", role_vi: "Rà soát khớp hình-tiếng từng frame, crossfade BGM 3s và 0% SFX rải bừa." },
      specialists: [
        { id: "edit_timeline_assembler", handle: "@edit_timeline_assembler", shortTag: "L1 RápTrục", title_vi: "Chuyên viên Lắp Ráp Trục Thời Gian Đa Lớp", role_vi: "Đặt toàn bộ clip S_F*.mp4, cảnh VOX, ảnh AI 4D và thẻ chương khớp giọng đọc." },
        { id: "edit_bgm_conductor", handle: "@edit_bgm_conductor", shortTag: "L2 BGM", title_vi: "Chuyên viên Đạo Diễn Nhạc Nền Story-Arc 8-12 Đoạn", role_vi: "Phân chia 8-12 đoạn cảm xúc, tuyển chọn/tải mới BGM và thiết lập crossfade 3s." },
        { id: "edit_motion_sfx_rigger", handle: "@edit_motion_sfx_rigger", shortTag: "L3 SFX", title_vi: "Chuyên viên Gắn SFX Chuyển Động Đồ Họa (Motion-Bound)", role_vi: "Trích xuất đúng offsetFrames chuyển động trong cảnh VOX để gắn SFX vật lý." },
        { id: "edit_master_renderer", handle: "@edit_master_renderer", shortTag: "L4 Render", title_vi: "Chuyên viên Kết Xuất & Chuẩn Hóa Video Master", role_vi: "Thực thi kết xuất Full HD/4K 30fps, ghép phụ đề chuẩn và kiểm tra MP4." },
      ],
    },
    seo: {
      lead: { id: "seo_lead", handle: "@seo_lead", shortTag: "👑 Trưởng", title_vi: "Tổ trưởng Chiến Lược Đóng Gói & Tăng Trưởng CTR", role_vi: "Chỉ đạo bộ Tiêu đề, Thumbnail tương phản cao và ký duyệt seo_package.json." },
      deputy: { id: "seo_deputy", handle: "@seo_deputy", shortTag: "🛡️ Phó", title_vi: "Tổ phó Kiểm Định Thuật Toán & Đối Chiếu Bản Dịch Việt", role_vi: "Kiểm tra 100% trường SEO có bản dịch tiếng Việt chuẩn xác và đúng tâm lý click." },
      specialists: [
        { id: "seo_title_strategist", handle: "@seo_title_strategist", shortTag: "L1 TiêuĐề", title_vi: "Chuyên viên Sáng Tạo Tiêu Đề Tò Mò Cao (High-CTR)", role_vi: "Thiết kế bộ tiêu đề khai thác nghịch lý đắt giá nhất kèm bản dịch tiếng Việt." },
        { id: "seo_thumbnail_director", handle: "@seo_thumbnail_director", shortTag: "L2 Thumb", title_vi: "Chuyên viên Thiết Kế Bố Cục & Chữ Thumbnail", role_vi: "Lên bố cục thị giác 3 lớp cho Thumbnail và câu hook 2-4 từ cực mạnh." },
        { id: "seo_metadata_architect", handle: "@seo_metadata_architect", shortTag: "L3 MôTả", title_vi: "Chuyên viên Biên Soạn Mô Tả, Chapters & Bình Luận Ghim", role_vi: "Viết mô tả chuẩn SEO, mốc thời gian chương hồi và bình luận ghim tương tác." },
        { id: "seo_bilingual_localizer", handle: "@seo_bilingual_localizer", shortTag: "L4 DịchVN", title_vi: "Chuyên viên Chuẩn Hóa Song Ngữ Tiếng Việt & Từ Khóa", role_vi: "Đảm bảo mọi trường trong seo_package.json đều có bản dịch tiếng Việt rõ nghĩa." },
      ],
    },
    evidence_qa: {
      lead: { id: "evidence_qa_lead", handle: "@evidence_qa_lead", shortTag: "👑 Trưởng", title_vi: "Tổ trưởng Thanh Tra Bằng Chứng & Sự Thật Hình Ảnh", role_vi: "Chốt chặn 8 cổng phản biện liên phòng, trả hồ sơ bắt sửa ngay nếu chưa đạt 100%." },
      deputy: { id: "evidence_qa_deputy", handle: "@evidence_qa_deputy", shortTag: "🛡️ Phó", title_vi: "Tổ phó Giám Định Khung Hình & Truy Vết Sai Lệch", role_vi: "Tổng hợp bằng chứng vi phạm từng beat_id và giám sát vòng lặp tự sửa." },
      specialists: [
        { id: "evidence_qa_footage_inspector", handle: "@evidence_qa_footage_inspector", shortTag: "L1 FTG", title_vi: "Chuyên viên Soi Khung Hình Tư Liệu Thật (3-Frame)", role_vi: "Kiểm tra VERIFY_FTG_CLIPS_*.jpg bắt lỗi MC trường quay, logo đài hoặc sai vụ án." },
        { id: "evidence_qa_vox_motion_auditor", handle: "@evidence_qa_vox_motion_auditor", shortTag: "L2 VOX", title_vi: "Chuyên viên Giám Định Chuyển Động Độc Bản VOX", role_vi: "So sánh 3 frame 15%-50%-85% của từng cảnh VOX bắt lỗi copy-paste motion." },
        { id: "evidence_qa_fact_alignment_checker", handle: "@evidence_qa_fact_alignment_checker", shortTag: "L3 SựThật", title_vi: "Chuyên viên Đối Chiếu Nhãn Chữ & Số Liệu Hiện Trường", role_vi: "Đọc toàn bộ thẻ chữ, con dấu, mốc năm trên màn hình đối chiếu hồ sơ gốc." },
        { id: "evidence_qa_verdict_compiler", handle: "@evidence_qa_verdict_compiler", shortTag: "L4 Lệnh", title_vi: "Chuyên viên Tổng Hợp Hồ Sơ Bằng Chứng & Lệnh Sửa", role_vi: "Đóng gói biên bản thanh tra chi tiết từng beat_id và trình ký lệnh." },
      ],
    },
    qc: {
      lead: { id: "qc_lead", handle: "@qc_lead", shortTag: "👑 Trưởng", title_vi: "Tổ trưởng Kiểm Định Chất Lượng Xuất Xưởng Master", role_vi: "Ký giấy phép xuất xưởng cuối cùng sau khi MP4 vượt qua mọi bài đo kỹ thuật." },
      deputy: { id: "qc_deputy", handle: "@qc_deputy", shortTag: "🛡️ Phó", title_vi: "Tổ phó Đo Kiểm Kỹ Thuật Broadcast & Hợp Đồng Kênh", role_vi: "Đối chiếu thông số video/audio thực tế với hợp đồng chất lượng của hồ sơ kênh." },
      specialists: [
        { id: "qc_video_stream_prober", handle: "@qc_video_stream_prober", shortTag: "L1 Luồng", title_vi: "Chuyên viên Đo Kiểm Tín Hiệu Hình Ảnh & Khung Đen", role_vi: "Quét toàn bộ luồng MP4 kiểm tra bitrate, độ phân giải, frozen frames/black frames." },
        { id: "qc_audio_loudness_prober", handle: "@qc_audio_loudness_prober", shortTag: "L2 ĐoLUFS", title_vi: "Chuyên viên Kiểm Định Chuẩn LUFS & Chống Dead-Air", role_vi: "Đo độ lớn âm thanh tích hợp LUFS, True Peak và kiểm tra 0% mất tiếng." },
        { id: "qc_subtitle_sync_auditor", handle: "@qc_subtitle_sync_auditor", shortTag: "L3 PhụĐề", title_vi: "Chuyên viên Kiểm Tra Đồng Bộ Phụ Đề & Vùng An Toàn", role_vi: "Đảm bảo phụ đề khớp giọng đọc và đồ họa VOX không đè vùng phụ đề." },
        { id: "qc_contract_certifier", handle: "@qc_contract_certifier", shortTag: "L4 CấpPhép", title_vi: "Chuyên viên Đối Chiếu Hợp Đồng & Cấp Chứng Nhận", role_vi: "Tổng hợp chỉ số chất lượng vào qc_report.json và xác nhận xuất xưởng." },
      ],
    },
    dev: {
      lead: { id: "dev_lead", handle: "@dev_lead", shortTag: "👑 Trưởng", title_vi: "Tổ trưởng Kiến Trúc Sư Hệ Thống & Công Cụ Sản Xuất", role_vi: "Chỉ đạo kiến trúc hệ thống, API đa phòng ban và hiệu năng toàn xưởng." },
      deputy: { id: "dev_deputy", handle: "@dev_deputy", shortTag: "🛡️ Phó", title_vi: "Tổ phó Kỹ Thuật Tích Hợp & Kiểm Định Mã Nguồn", role_vi: "Kiểm tra tính tương thích Backend-Frontend và bảo vệ quy tắc cách ly kênh." },
      specialists: [
        { id: "dev_backend_engineer", handle: "@dev_backend_engineer", shortTag: "L1 Backend", title_vi: "Chuyên viên Phát Triển Backend & Điều Phối Đa Agent", role_vi: "Xây dựng module xử lý dữ liệu, quản lý 15 phòng ban và luồng bất đồng bộ." },
        { id: "dev_remotion_engine_coder", handle: "@dev_remotion_engine_coder", shortTag: "L2 Remotion", title_vi: "Chuyên viên Phát Triển Thư Viện Đồ Họa Remotion & VOX", role_vi: "Xây dựng nguyên tử bàn biên tập VOX, 12 động tác motion và bản đồ 3D GIS." },
        { id: "dev_frontend_ui_builder", handle: "@dev_frontend_ui_builder", shortTag: "L3 UI-92NS", title_vi: "Chuyên viên Thiết Kế Giao Diện Điều Hành & Sơ Đồ 92 NS", role_vi: "Phát triển giao diện mặt bằng 15 phòng ban × 92 nhân sự trực quan." },
        { id: "dev_test_gate_engineer", handle: "@dev_test_gate_engineer", shortTag: "L4 TestAST", title_vi: "Chuyên viên Xây Dựng Cổng Kiểm Định AST & Unit Test", role_vi: "Viết trình kiểm định mã nguồn tự động và bộ test bảo vệ quy tắc hệ thống." },
      ],
    },
    debug: {
      lead: { id: "debug_lead", handle: "@debug_lead", shortTag: "👑 Trưởng", title_vi: "Tổ trưởng Chẩn Đoán Sự Cố & Cứu Hộ Pipeline", role_vi: "Chỉ huy xử lý sự cố khẩn cấp và khôi phục dây chuyền từ điểm lưu an toàn." },
      deputy: { id: "debug_deputy", handle: "@debug_deputy", shortTag: "🛡️ Phó", title_vi: "Tổ phó Phân Tích Nhật Ký & Kiểm Soát Điểm Lưu", role_vi: "Giám sát tính toàn vẹn của checkpoint và xác nhận sạch lỗi trước khi mở khóa." },
      specialists: [
        { id: "debug_log_tracer", handle: "@debug_log_tracer", shortTag: "L1 NhậtKý", title_vi: "Chuyên viên Truy Vết Stacktrace & Nhật Ký Hệ Thống", role_vi: "Đọc nhật ký thực thi của Python, FFmpeg và Remotion chỉ ra chính xác dòng lỗi." },
        { id: "debug_asset_healer", handle: "@debug_asset_healer", shortTag: "L2 PhụcHồi", title_vi: "Chuyên viên Khôi Phục Tập Tin & Đồng Bộ Đường Dẫn", role_vi: "Xử lý thiếu file media, bộ nhớ đệm âm thanh và đồng bộ workspace/public." },
        { id: "debug_ast_patch_surgeon", handle: "@debug_ast_patch_surgeon", shortTag: "L3 VáTSX", title_vi: "Chuyên viên Phẫu Thuật Lỗi Cú Pháp TSX & Manifest", role_vi: "Sửa nhanh lỗi cú pháp JSX/TypeScript và định dạng JSON trong manifest." },
        { id: "debug_recovery_verifier", handle: "@debug_recovery_verifier", shortTag: "L4 MởKhóa", title_vi: "Chuyên viên Kiểm Thử Hồi Phục & Mở Khóa Dây Chuyền", role_vi: "Chạy kiểm tra nhanh tác vụ vừa sửa để xác nhận lỗi biến mất hoàn toàn." },
      ],
    },
  };

  // Multi-Corridor Cartoon Studio Waypoints so 10 Couriers + 2 Studio Pets roam dynamically across all floors!
  const LOUNGE_SPOTS = [
    { id: "coffee_1", x: 188, y: 262, act: "coffee", fx: "☕", tag: "Pha Espresso nóng hổi!" },
    { id: "coffee_2", x: 268, y: 268, act: "coffee", fx: "🥐", tag: "Bánh sừng bò & Latte sữa đá!" },
    { id: "coffee_3", x: 332, y: 258, act: "coffee", fx: "🧋", tag: "Trà đào tiếp sức ca dựng!" },
    { id: "sofa_1", x: 472, y: 264, act: "sofa", fx: "📋", tag: "Bàn nhanh kịch bản Hồi 3!" },
    { id: "sofa_2", x: 548, y: 268, act: "sofa", fx: "💬", tag: "Chốt 12 Motion Verbs VOX!" },
    { id: "sofa_3", x: 616, y: 258, act: "sofa", fx: "🎬", tag: "Duyệt Storyboard 1-1!" },
    { id: "board_1", x: 760, y: 262, act: "board", fx: "📊", tag: "Cập nhật tiến độ 92 Nhân sự!" },
    { id: "board_2", x: 890, y: 266, act: "board", fx: "🗺️", tag: "Ghim tọa độ 3D GIS OSRM!" },
    { id: "board_3", x: 1020, y: 260, act: "board", fx: "⚡", tag: "Đồng bộ 62 luồng song song!" },
    { id: "plant_1", x: 1152, y: 264, act: "plant", fx: "🪴", tag: "Tưới cây Monstera xanh mát!" },
    { id: "water_1", x: 1258, y: 262, act: "coffee", fx: "💧", tag: "Lấy nước mát tiếp năng lượng!" },
    { id: "arcade_1", x: 1358, y: 264, act: "board", fx: "🕹️", tag: "Nạp hứng khởi sáng tạo!" },
    { id: "corridor_n1", x: 294, y: 215, act: "walk", fx: "📁", tag: "Chuyển hồ sơ gốc sang Biên kịch!" },
    { id: "corridor_n2", x: 855, y: 215, act: "walk", fx: "🎙️", tag: "Giao bản thu TTS sang Phân cảnh!" },
    { id: "corridor_s1", x: 434, y: 518, act: "walk", fx: "🎞️", tag: "Giao clip 3-Frame sang phòng Dựng!" },
    { id: "corridor_s2", x: 998, y: 518, act: "walk", fx: "⚖️", tag: "Trình Pháp Y QA nghiệm thu!" },
  ];

  const LIAISON_AGENTS = [
    "orchestrator",
    "vox",
    "footage",
    "evidence_qa",
  ];

  const STUDIO_PETS = [
    { id: "pet_cat", nameVi: "🐱 Mèo Đạo Diễn", x: 410, y: 268, fx: "🐾", chat: "Meow~ Cảnh VOX này 10 điểm!" },
    { id: "pet_corgi", nameVi: "🐶 Corgi Giao Phim", x: 960, y: 266, fx: "🎞️", chat: "Gâu! Mang cuộn phim Master tới đây!" },
  ];

  const aoState = {
    open: false,
    viewMode: "chibi", // Default directly to Animated Cartoon Movie Studio!
    perspective3d: false, // Default crisp Cartoon Movie 2D view without blurry CSS 3D tilt distortion
    stageMaximized: false, // Toggle full-screen Cartoon Studio vs 72/28 split with Inspector Dock
    floorZoneFilter: "all", // "all" | "north" | "central" | "south" | "direction" | "editorial" | "cinema" | "qa"
    deptDivisionFilter: "all", // "all" | "executive" | "intelligence" | "visual" | "post" | "quality" | "vox"
    soundEnabled: true,
    selectedJobId: "",
    userPinnedJobId: "",
    lastGlobalSelectedJobId: "",
    lastActiveJobId: "",
    pendingRefresh: false,
    pendingRefreshForce: false,
    selectedAgentId: "vox",
    focusedAgentId: null, // Left-click or Auto-Zoom focused department room
    focusedMemberKey: "lead", // "lead" | "deputy" | specialist id/handle
    focusAskMode: "progress", // "progress" | "qa" | "persona"
    autoZoomActiveRoom: false, // Default false so user sees all 15 Rooms × 92 Staff immediately alongside Live Group Chat
    manualOverviewLock: false, // Set true when user clicks "Toàn Cảnh Xưởng Phim" so polling stays on overview until user clicks a room
    manualZoomOutKey: "", // Remembers if user manually zoomed out during current active room
    lastAutoZoomKey: "",
    parallelWaveDept: "", // Specific department running parallel wave (or "all")
    activeTab: "chat", // "chat" | "departments" | "roster" | "critique" | "events" | "charter"
    userGroupChatMessages: [], // Interactive messages sent in the Group Chat + instant Agent responses
    snapshot: null,
    livePhaseTelemetry: null, // { phase, done, total, pct, shortVi, detailVi, byAgent, stepIndex, stepState }
    lastSeenStepKey: "",
    activeStepStartedMs: 0,
    liveClockTimer: null,
    charterCache: {},
    pollTimer: null,
    badgeTimer: null,
    roamTimer: null,
    rafId: null,
    lastFrameTs: 0,
    bubbleTick: 0,
    bubbleTimer: null,
    actors: {}, // liaison/pet id -> { x, y, tx, ty, facingLeft, walking, spotId, nextRoamAt, fx, tag }
    parallelWaveActive: false,
    parallelLastWaveAt: "",
    stageMounted: false,
    fetching: false,
    audioCtx: null,
    lastReworkAlertKey: "",
    _lastKpiSig: "",
    _lastInspectorSig: "",
    _lastFocusSig: "",
    roomSecOpen: {
      progress: true,
      command: true,
      specialists: true,
      groupchat: false,
      all15: false,
    },
    miniRoomOpen: {
      direction: true,
      editorial: true,
      cinema: true,
      qa: true,
    },
    otherDeptsDirectoryOpen: true,
  };

  function ensureRoomCollapseStylesInjected() {
    let st = document.getElementById("aoRoomInteriorFixStyle");
    if (!st) {
      st = document.createElement("style");
      st.id = "aoRoomInteriorFixStyle";
      document.head.appendChild(st);
    }
    st.textContent = `
      #aoFocusReplyCard.ao-focus-reply-card.ao-room-zoom-interior-stage {
        display: flex !important;
        flex-direction: column !important;
        justify-content: flex-start !important;
        align-items: stretch !important;
        gap: 10px !important;
        padding: 12px 14px 22px !important;
        overflow-y: auto !important;
        overflow-x: hidden !important;
        background: linear-gradient(180deg, #060e1c 0%, #091528 50%, #050c18 100%) !important;
        color: #f8fafc !important;
      }
      #aoFocusReplyCard > * {
        flex: 0 0 auto !important;
        flex-shrink: 0 !important;
        min-height: max-content !important;
      }
      .ao-rz-specialists-section,
      .ao-rz-spec-grid,
      .ao-rz-command-deck,
      .ao-rz-live-report-banner {
        flex: 0 0 auto !important;
        flex-shrink: 0 !important;
        height: auto !important;
        min-height: max-content !important;
      }
      .ao-rz-topbar.ao-toon-set-topbar {
        display: flex !important;
        flex-direction: column !important;
        align-items: stretch !important;
        justify-content: flex-start !important;
        gap: 8px !important;
        padding: 10px 14px !important;
        width: 100% !important;
        box-sizing: border-box !important;
      }
      .ao-rz-topbar-row1 {
        display: flex !important;
        align-items: center !important;
        justify-content: space-between !important;
        gap: 12px !important;
        flex-wrap: wrap !important;
        width: 100% !important;
      }
      .ao-rz-topbar .ao-rz-top-left {
        display: flex !important;
        align-items: center !important;
        gap: 12px !important;
        flex: 1 1 520px !important;
        min-width: 300px !important;
        overflow: visible !important;
      }
      .ao-rz-topbar .ao-rz-room-identity {
        display: flex !important;
        align-items: center !important;
        gap: 10px !important;
        flex: 1 1 320px !important;
        min-width: 240px !important;
        overflow: visible !important;
      }
      .ao-rz-topbar .ao-rz-room-icon {
        width: 38px !important;
        height: 38px !important;
        min-width: 38px !important;
        flex: 0 0 38px !important;
        display: grid !important;
        place-items: center !important;
      }
      .ao-rz-room-identity-text {
        flex: 1 1 auto !important;
        min-width: 0 !important;
        display: flex !important;
        flex-direction: column !important;
        gap: 3px !important;
      }
      .ao-rz-topbar .ao-rz-room-title-row {
        display: flex !important;
        align-items: center !important;
        gap: 7px !important;
        flex-wrap: wrap !important;
        overflow: visible !important;
      }
      .ao-rz-topbar .ao-rz-room-title-row h4 {
        font-size: 14px !important;
        font-weight: 900 !important;
        color: #ffffff !important;
        white-space: normal !important;
        overflow: visible !important;
        text-overflow: clip !important;
        margin: 0 !important;
      }
      .ao-rz-topbar .ao-rz-room-sub {
        max-width: 100% !important;
        white-space: normal !important;
        overflow: visible !important;
        line-height: 1.35 !important;
        margin: 0 !important;
      }
      .ao-rz-topbar .ao-rz-top-right {
        display: flex !important;
        align-items: center !important;
        gap: 8px !important;
        flex-shrink: 0 !important;
        flex-wrap: wrap !important;
      }
      .ao-rz-topbar-row2 {
        display: flex !important;
        align-items: center !important;
        gap: 8px !important;
        padding-top: 7px !important;
        border-top: 1px solid rgba(56, 189, 248, 0.22) !important;
        flex-wrap: wrap !important;
        width: 100% !important;
      }
      .ao-rz-strip-label {
        font-size: 10.5px !important;
        font-weight: 800 !important;
        color: #7dd3fc !important;
        white-space: nowrap !important;
      }
      .ao-rz-topbar-row2 .ao-rz-room-strip {
        display: flex !important;
        align-items: center !important;
        gap: 4px !important;
        flex-wrap: wrap !important;
        flex: 1 1 auto !important;
      }
      .ao-rz-collapse-card {
        display: flex !important;
        flex-direction: column !important;
        flex: 0 0 auto !important;
        flex-shrink: 0 !important;
        width: 100% !important;
        border-radius: 13px !important;
        background: linear-gradient(180deg, rgba(11, 25, 46, 0.96) 0%, rgba(7, 16, 31, 0.98) 100%) !important;
        border: 1.5px solid rgba(56, 189, 248, 0.36) !important;
        box-shadow: 0 8px 22px rgba(0, 0, 0, 0.42) !important;
        overflow: hidden !important;
      }
      .ao-rz-collapse-card.is-collapsed {
        border-color: rgba(148, 163, 184, 0.28) !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.28) !important;
      }
      .ao-rz-collapse-head {
        display: flex !important;
        align-items: center !important;
        justify-content: space-between !important;
        gap: 10px !important;
        padding: 9px 14px !important;
        background: linear-gradient(90deg, rgba(15, 31, 56, 0.96) 0%, rgba(11, 23, 42, 0.96) 100%) !important;
        border-bottom: 1px solid rgba(56, 189, 248, 0.24) !important;
        cursor: pointer !important;
        user-select: none !important;
        flex-wrap: wrap !important;
      }
      .ao-rz-collapse-card.is-collapsed .ao-rz-collapse-head {
        border-bottom-color: transparent !important;
      }
      .ao-rz-collapse-head:hover {
        background: linear-gradient(90deg, rgba(20, 44, 78, 0.98) 0%, rgba(14, 31, 58, 0.98) 100%) !important;
      }
      .ao-rz-collapse-head-left {
        display: flex !important;
        align-items: center !important;
        gap: 8px !important;
        flex-wrap: wrap !important;
        min-width: 0 !important;
      }
      .ao-rz-collapse-title {
        font-size: 11.5px !important;
        font-weight: 900 !important;
        color: #f8fafc !important;
        letter-spacing: 0.02em !important;
      }
      .ao-rz-collapse-meta-badge {
        display: inline-flex !important;
        align-items: center !important;
        gap: 4px !important;
        padding: 2px 9px !important;
        border-radius: 999px !important;
        background: rgba(14, 165, 233, 0.16) !important;
        border: 1px solid rgba(56, 189, 248, 0.38) !important;
        color: #7dd3fc !important;
        font-size: 10px !important;
        font-weight: 800 !important;
        white-space: nowrap !important;
      }
      .ao-rz-collapse-meta-badge.emerald {
        background: rgba(16, 185, 129, 0.16) !important;
        border-color: rgba(52, 211, 153, 0.45) !important;
        color: #6ee7b7 !important;
      }
      .ao-rz-collapse-meta-badge.gold {
        background: rgba(234, 179, 8, 0.16) !important;
        border-color: rgba(250, 204, 21, 0.45) !important;
        color: #fde047 !important;
      }
      .ao-rz-collapse-head-right {
        display: flex !important;
        align-items: center !important;
        gap: 8px !important;
        flex-shrink: 0 !important;
      }
      .ao-rz-collapse-toggle-pill {
        display: inline-flex !important;
        align-items: center !important;
        gap: 5px !important;
        padding: 4px 10px !important;
        border-radius: 8px !important;
        background: rgba(30, 41, 59, 0.9) !important;
        border: 1px solid rgba(148, 163, 184, 0.38) !important;
        color: #e2e8f0 !important;
        font-size: 10px !important;
        font-weight: 800 !important;
      }
      .ao-rz-collapse-head:hover .ao-rz-collapse-toggle-pill {
        background: rgba(14, 165, 233, 0.25) !important;
        border-color: #38bdf8 !important;
        color: #ffffff !important;
      }
      .ao-rz-collapse-body {
        display: flex !important;
        flex-direction: column !important;
        gap: 10px !important;
        padding: 12px 14px !important;
        flex: 0 0 auto !important;
        flex-shrink: 0 !important;
        height: auto !important;
      }
      .ao-rz-collapse-card.is-collapsed .ao-rz-collapse-body {
        display: none !important;
      }
      .ao-rz-collapse-all-btn {
        padding: 6px 11px !important;
        border-radius: 8px !important;
        background: rgba(15, 23, 42, 0.9) !important;
        border: 1px solid rgba(56, 189, 248, 0.42) !important;
        color: #7dd3fc !important;
        font-size: 10.5px !important;
        font-weight: 800 !important;
        cursor: pointer !important;
        white-space: nowrap !important;
      }
    `;
  }

  function dispatchMentionToChat(handle, defaultPrompt, keepOfficeOpen) {
    const cleanHandle = String(handle || "@orchestrator").trim();
    const promptBody = String(
      defaultPrompt || "Báo cáo trạng thái trực chiến & thực thi nhiệm vụ chuyên môn trong dây chuyền hiện tại:"
    ).trim();
    const fullCommand = `${cleanHandle} ${promptBody} `;

    if (!keepOfficeOpen) {
      closeAgentOffice();
    }

    const dock = document.getElementById("globalCodexDock");
    if (dock) {
      dock.classList.remove("hidden");
      dock.classList.add("open");
      document.body.classList.add("global-chat-open");
      try {
        localStorage.setItem("cofi-global-chat-open", "1");
      } catch (_e) {}
    }

    const globalInput = document.getElementById("globalCodexInput");
    const prodInput = document.getElementById("producerCodexInput");
    const targetInput = globalInput || prodInput;
    if (targetInput) {
      targetInput.value = fullCommand;
      targetInput.focus();
      try {
        targetInput.setSelectionRange(fullCommand.length, fullCommand.length);
      } catch (_e) {}
    }

    const toastEl = document.getElementById("toast");
    if (toastEl) {
      toastEl.textContent = `📨 Đã nạp lệnh điều phối ${cleanHandle} vào Hộp Chat Điều Phối!`;
      toastEl.classList.remove("error");
      toastEl.classList.add("show");
      setTimeout(() => toastEl.classList.remove("show"), 2800);
    }
  }

  function esc(val) {
    return String(val ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  // Lightweight Cozy Studio Sound Synthesizer (Zero external MP3 needed)
  function playStudioSound(kind) {
    if (!aoState.soundEnabled || !aoState.open) return;
    try {
      const Ctx = window.AudioContext || window.webkitAudioContext;
      if (!Ctx) return;
      if (!aoState.audioCtx) aoState.audioCtx = new Ctx();
      const ctx = aoState.audioCtx;
      if (ctx.state === "suspended") ctx.resume().catch(() => {});

      const now = ctx.currentTime;
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);

      if (kind === "focus") {
        osc.type = "sine";
        osc.frequency.setValueAtTime(520, now);
        osc.frequency.exponentialRampToValueAtTime(780, now + 0.09);
        gain.gain.setValueAtTime(0.05, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.14);
        osc.start(now);
        osc.stop(now + 0.15);
      } else if (kind === "zoomout") {
        osc.type = "sine";
        osc.frequency.setValueAtTime(640, now);
        osc.frequency.exponentialRampToValueAtTime(360, now + 0.1);
        gain.gain.setValueAtTime(0.04, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.12);
        osc.start(now);
        osc.stop(now + 0.13);
      } else if (kind === "ask") {
        osc.type = "triangle";
        osc.frequency.setValueAtTime(660, now);
        osc.frequency.exponentialRampToValueAtTime(880, now + 0.07);
        gain.gain.setValueAtTime(0.04, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.09);
        osc.start(now);
        osc.stop(now + 0.1);
      } else if (kind === "stamp") {
        osc.type = "triangle";
        osc.frequency.setValueAtTime(190, now);
        osc.frequency.exponentialRampToValueAtTime(75, now + 0.14);
        gain.gain.setValueAtTime(0.07, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.16);
        osc.start(now);
        osc.stop(now + 0.17);
      }
    } catch (_e) {
      // Ignore audio policy restrictions
    }
  }

  function currentAppSelectedJobId() {
    const sel = document.getElementById("globalProjectSelect");
    return sel && sel.value ? String(sel.value).trim() : "";
  }

  function cleanActionStringVi(raw) {
    const s = String(raw || "").trim();
    if (!s) return "";
    if (/python\d*\s+-c/i.test(s) || /sys\.path\.insert/i.test(s)) {
      if (/visual_manifest\.json/i.test(s)) return "Kiểm tra & chuẩn hóa khung phân cảnh visual_manifest.json";
      if (/script\.md/i.test(s)) return "Kiểm tra & chuẩn hóa kịch bản script.md";
      if (/outline\.json/i.test(s)) return "Kiểm tra & khóa cấu trúc dàn ý outline.json";
      if (/research\.md/i.test(s)) return "Kiểm tra & đối chiếu hồ sơ điều tra research.md";
      return "Chạy script kiểm tra & đồng bộ dữ liệu tiến độ trên đĩa";
    }
    return s;
  }

  function normalizeOfficeSnapshot(snap) {
    if (!snap || typeof snap !== "object") return snap;
    const selJob = snap.selected_job;
    const runningPhases = Array.isArray(selJob?.running_phases)
      ? selJob.running_phases
      : Array.isArray(snap.summary?.running_phases)
      ? snap.summary.running_phases
      : [];
    const curPhase = String(
      selJob?.current_phase || runningPhases[0] || ""
    ).trim().toLowerCase();
    if (selJob && curPhase && !selJob.current_phase) {
      selJob.current_phase = curPhase;
    }

    const gates = Array.isArray(snap.critique_gates) ? snap.critique_gates : [];
    const curGate = gates.find((g) => g && g.phase === (curPhase || "plan")) || gates[0] || {};
    const proofItems = Array.isArray(curGate.proof_items) ? curGate.proof_items.map((x) => String(x || "")) : [];
    const hasResearchDone = proofItems.some((p) => /research\.md/i.test(p));
    const hasScriptDone = proofItems.some((p) => /script\.md/i.test(p));
    const hasVisManDone = proofItems.some((p) => /phân cảnh|beats|visual_manifest/i.test(p));

    // Clean any raw `python -c` strings in live_events and agent bubbles
    if (Array.isArray(snap.live_events)) {
      snap.live_events.forEach((ev) => {
        if (ev && ev.action_vi) ev.action_vi = cleanActionStringVi(ev.action_vi);
        if (ev && ev.target && (/python\d*\s+-c/i.test(ev.target) || /sys\.path\.insert/i.test(ev.target))) {
          ev.target = curPhase || "workspace";
        }
      });
    }

    // Ensure only the actual active department executing the current step is marked "working"
    if (Array.isArray(snap.agents) && runningPhases.length > 0) {
      const activeIds = [];
      snap.agents.forEach((ag) => {
        if (!ag) return;
        if (ag.live_bubble) ag.live_bubble = cleanActionStringVi(ag.live_bubble);
        if (ag.live_state === "reworking") {
          // Preserve backend live rework state and status_label_vi
        } else if (ag.id === "orchestrator" && curGate.gate_state !== "reworking_live") {
          ag.live_state = "standby";
          ag.status_label_vi = `Đang giám sát ${curGate.label_vi || curPhase}`;
        } else if (ag.id === "evidence_qa" && curGate.gate_state !== "critic_reviewing" && curGate.gate_state !== "reworking_live") {
          ag.live_state = "standby";
          ag.status_label_vi = `Trực cổng nghiệm thu ${curPhase}`;
        } else if (curPhase === "plan" && curGate.gate_state !== "reworking_live") {
          if (ag.id === "research") {
            if (hasResearchDone) {
              ag.live_state = "done";
              ag.status_label_vi = "Đã bàn giao research.md";
            } else {
              ag.live_state = "working";
              ag.status_label_vi = "Đang tra cứu & lập research.md";
            }
          } else if (ag.id === "script") {
            if (hasResearchDone) {
              ag.live_state = "working";
              ag.status_label_vi = hasScriptDone
                ? "Đang chia khung phân cảnh & rà soát kịch bản"
                : "Đang chấp bút dàn ý & kịch bản script.md";
            } else {
              ag.live_state = "standby";
              ag.status_label_vi = "Chờ nhận research.md từ Phòng 02";
            }
          }
        }
        if (["working", "reworking", "critiquing"].includes(ag.live_state)) {
          activeIds.push(ag.id);
        }
      });
      if (snap.summary) {
        snap.summary.active_agent_ids = activeIds;
        snap.summary.active_agents_count = activeIds.length;
      }
    }

    // Synthesize `live_phase_report` if backend hasn't populated it yet
    if (!snap.live_phase_report) {
      const stepIdx = Number(
        (Array.isArray(snap.live_events) && snap.live_events[0]?.step_index) ||
          snap.summary?.total_cli_steps ||
          0
      );
      const lastEv = Array.isArray(snap.live_events) && snap.live_events[0] ? snap.live_events[0] : null;
      const primaryAg =
        curPhase === "plan"
          ? hasResearchDone
            ? "script"
            : "research"
          : curGate.maker_agent || "script";
      let milestones = [];
      let pct = 20;
      if ((curPhase || "plan") === "plan") {
        const resMatch = proofItems.find((p) => /research\.md/i.test(p)) || "";
        const scrMatch = proofItems.find((p) => /script\.md/i.test(p)) || "";
        const vmMatch = proofItems.find((p) => /phân cảnh|câu thoại/i.test(p)) || "";
        milestones = [
          {
            label_vi: "1. Hồ sơ điều tra gốc",
            file: "research.md",
            done: hasResearchDone,
            detail_vi: hasResearchDone ? resMatch.replace(/^.*research\.md:\s*/i, "Đã xong ") : "Đang tra cứu tư liệu...",
          },
          {
            label_vi: "2. Dàn ý cấu trúc chương hồi",
            file: "outline.json",
            done: hasResearchDone && (hasScriptDone || stepIdx >= 12),
            detail_vi: hasResearchDone ? "Đã khóa cấu trúc 5 hồi" : "Chờ research.md",
          },
          {
            label_vi: "3. Kịch bản văn nói",
            file: "script.md",
            done: hasScriptDone,
            detail_vi: hasScriptDone ? scrMatch.replace(/^.*script\.md:\s*/i, "Đã viết ") : "Đang chấp bút lời bình...",
          },
          {
            label_vi: "4. Khung phân cảnh & Kiểm duyệt",
            file: "visual_manifest.json",
            done: hasVisManDone && !runningPhases.length,
            detail_vi: hasVisManDone ? vmMatch.replace(/^.*:\s*/, "Đã chia ") : "Đang chia beat & rà QA...",
          },
        ];
        const doneCnt = milestones.filter((m) => m.done).length;
        pct = Math.min(runningPhases.length ? 96 : 100, [14, 35, 62, 86, 96][Math.min(4, doneCnt)] + Math.min(10, Math.floor(stepIdx / 6)));
      } else {
        milestones = proofItems.slice(0, 4).map((p, idx) => ({
          label_vi: `${idx + 1}. Hạng mục #${idx + 1}`,
          file: curPhase || "output",
          done: true,
          detail_vi: p.slice(0, 48),
        }));
        pct = runningPhases.length ? Math.min(95, 25 + stepIdx * 2) : 100;
      }

      const evTxt = lastEv
        ? `Bước #${lastEv.step_index || stepIdx} · ${cleanActionStringVi(lastEv.action_vi)}${lastEv.target ? ` → ${lastEv.target}` : ""}`
        : curGate.summary_vi || "Đang thực thi trực tiếp trên workspace…";

      snap.live_phase_report = {
        phase: curPhase || "plan",
        phase_label_vi: curGate.label_vi || `Bước · ${curPhase || "plan"}`,
        primary_agent_id: primaryAg,
        is_running: runningPhases.length > 0,
        step_index: stepIdx,
        percent: pct,
        eta_vi: computePhaseEtaVi(runningPhases.length > 0, pct, curPhase || "plan"),
        current_action_vi: evTxt,
        milestones,
      };
    } else {
      if (
        curPhase === "voice" &&
        /chấm điểm phản biện|tokens|research\.md/i.test(String(snap.live_phase_report.current_action_vi || ""))
      ) {
        const ms2 = Array.isArray(snap.live_phase_report.milestones) ? snap.live_phase_report.milestones[1] : null;
        snap.live_phase_report.current_action_vi =
          ms2 && ms2.detail_vi && !/Đang tổng hợp TTS/i.test(ms2.detail_vi)
            ? `Đang tổng hợp giọng đọc CofiVoice (${ms2.detail_vi}) & đồng bộ phụ đề SRT`
            : "Đang tổng hợp giọng đọc CofiVoice GPU theo từng phân cảnh & căn chỉnh phụ đề SRT";
      }
      if (!snap.live_phase_report.eta_vi) {
        snap.live_phase_report.eta_vi = computePhaseEtaVi(
          Boolean(snap.live_phase_report.is_running),
          Number(snap.live_phase_report.percent || 50),
          String(snap.live_phase_report.phase || curPhase || "plan")
        );
      }
    }

    return snap;
  }

  function computePhaseEtaVi(isRunning, pct, phase) {
    if (!isRunning) {
      return "Đã hoàn tất công đoạn hiện tại (0 giây) — sẵn sàng bước tiếp theo";
    }
    const p = Number(pct || 0);
    const ph = String(phase || "plan").toLowerCase();
    if (p >= 92) {
      return "Còn khoảng ~30–60 giây nữa xong (đang khóa kiểm duyệt cuối & bàn giao)";
    }
    if (p >= 75) {
      return "Còn khoảng ~1–2 phút nữa hoàn tất bàn giao sang phòng kế tiếp";
    }
    if (p >= 45) {
      if (ph === "voice") return "Còn khoảng ~2–3 phút nữa xong thu âm TTS & căn phụ đề SRT";
      if (ph === "footage") return "Còn khoảng ~2–4 phút nữa xong soi lưới 100px & cắt clip 3-Frame";
      if (ph === "edit") return "Còn khoảng ~2–3 phút nữa xong dựng Timeline Remotion & kiểm định AST";
      return "Còn khoảng ~2–3 phút nữa hoàn tất công đoạn này";
    }
    return "Còn khoảng ~3–5 phút nữa hoàn tất toàn bộ 4 hạng mục trong bước này";
  }

  async function fetchOfficeSnapshot(jobId, pinned) {
    const params = [];
    if (jobId) params.push(`job_id=${encodeURIComponent(jobId)}`);
    if (pinned) params.push("pinned=true");
    params.push(`_t=${Date.now()}`);
    const q = `?${params.join("&")}`;
    const resp = await fetch(`/api/agency/office-live${q}`, { cache: "no-store" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const rawSnap = await resp.json();
    return normalizeOfficeSnapshot(rawSnap);
  }

  function shortPathTarget(raw) {
    const s = String(raw || "").trim().replace(/"/g, "");
    if (!s) return "";
    const parts = s.split(/[\\/]/).filter(Boolean);
    return parts.length ? parts[parts.length - 1] : s;
  }

  function humanizeStepRecord(su) {
    if (!su) return null;
    const idx = Number(su.step_index || 0);
    const st = String(su.state || "");
    const stype = String(su.step_type || "");
    const tname = String(su.tool_name || su.tool_info?.name || "");
    const params = su.tool_info?.parameters || {};

    if (stype === "agent_response") {
      const tok = su.usage?.total_tokens ? ` (${Math.round(su.usage.total_tokens / 100) / 10}k tok)` : "";
      return {
        idx,
        state: st,
        targetRole: "lead",
        textVi: st === "ACTIVE" ? `Đang suy luận & biên đạo chi tiết…` : `Hoàn tất phân tích & lập phương án${tok}`,
      };
    }

    const pFile = shortPathTarget(params.Path || params.TargetFile || params.File || "");
    const cmd = String(params.CommandLine || params.command || "").trim();

    if (tname === "read_file" && pFile) {
      const low = pFile.toLowerCase();
      const role = /\.(jpg|jpeg|png|webp|mp4|webm)$/.test(low)
        ? "footage"
        : /\.(tsx|ts|css)$|vox|map|chart/i.test(pFile)
        ? "vox"
        : "lead";
      return {
        idx,
        state: st,
        targetRole: role,
        textVi: /\.(jpg|jpeg|png|webp)$/.test(low)
          ? `Soi kiểm tra khung hình ${pFile}`
          : `Đọc & đối chiếu ${pFile}`,
      };
    }

    if ((tname === "write_file" || tname === "edit_file" || tname === "replace_file_content") && pFile) {
      const role = /footage|download|yt|clip/i.test(pFile)
        ? "footage"
        : /\.(tsx|ts)$|vox|map|scene|motion/i.test(pFile)
        ? "vox"
        : "lead";
      return {
        idx,
        state: st,
        targetRole: role,
        textVi: /\.(tsx|ts)$/.test(pFile.toLowerCase())
          ? `Code đồ họa Remotion / Vox: ${pFile}`
          : `Cập nhật tệp ${pFile}`,
      };
    }

    if (tname === "run_command" && cmd) {
      if (/python\d*\s+-c/i.test(cmd) || /sys\.path\.insert/i.test(cmd)) {
        return {
          idx,
          state: st,
          targetRole: "lead",
          textVi: cleanActionStringVi(cmd),
        };
      }
      const scriptMatch = cmd.match(/([A-Za-z0-9_.-]+\.(?:py|ps1|js|mjs|tsx))/i);
      const shortCmd = scriptMatch ? scriptMatch[1] : cmd.replace(/\s+/g, " ").slice(0, 44);
      const role = /footage|yt-dlp|ffmpeg|probe|frame/i.test(cmd)
        ? "footage"
        : /remotion|vox|tsx|tsc|bundle/i.test(cmd)
        ? "vox"
        : "lead";
      return {
        idx,
        state: st,
        targetRole: role,
        textVi: `Chạy lệnh thực thi: ${shortCmd}`,
      };
    }

    if (tname) {
      return {
        idx,
        state: st,
        targetRole: "lead",
        textVi: `Gọi công cụ ${tname}${pFile ? ` -> ${pFile}` : ""}`,
      };
    }
    return null;
  }

  async function fetchLivePhaseTelemetry(jobId, currentPhase) {
    if (!jobId || !currentPhase) return null;
    const byAgent = {};
    let stepIndex = 0;
    let stepState = "";
    let latestActionVi = "";

    // 1. Parse live phase JSONL log tail so every active specialist shows continuous real-time steps!
    try {
      const lr = await fetch(`/api/jobs/${encodeURIComponent(jobId)}/logs/${encodeURIComponent(currentPhase)}?tail_bytes=32768&_t=${Date.now()}`, { cache: "no-store" });
      if (lr.ok) {
        const rawLog = await lr.text();
        const tailLines = rawLog.split(/\r?\n/).filter((x) => x.trim()).slice(-28);
        const parsed = [];
        tailLines.forEach((ln) => {
          try {
            const obj = JSON.parse(ln);
            if (obj && obj.step_update) {
              const h = humanizeStepRecord(obj.step_update);
              if (h) parsed.push(h);
            }
          } catch (_e) {}
        });

        if (parsed.length > 0) {
          const last = parsed[parsed.length - 1];
          stepIndex = last.idx;
          stepState = last.state;
          latestActionVi = last.textVi;

          const stepKey = `${currentPhase}:${stepIndex}:${stepState}`;
          if (aoState.lastSeenStepKey !== stepKey) {
            aoState.lastSeenStepKey = stepKey;
            aoState.activeStepStartedMs = Date.now();
          }

          const lastFootage = [...parsed].reverse().find((x) => x.targetRole === "footage");
          const lastVox = [...parsed].reverse().find((x) => x.targetRole === "vox");
          if (lastFootage) byAgent.footage = `#${lastFootage.idx} · ${lastFootage.textVi}`;
          if (lastVox) byAgent.vox = `#${lastVox.idx} · ${lastVox.textVi}`;

          const leadMap = { plan: "script", voice: "voice", visuals: "visuals", footage: "footage", ai_visual: "ai_visual", edit: "edit", seo: "seo", qc: "qc" };
          const leadId = leadMap[currentPhase] || "orchestrator";
          byAgent[leadId] = `#${last.idx} · ${last.textVi}`;
        }
      }
    } catch (_e) {}

    try {
      if (currentPhase === "ai_visual") {
        const r = await fetch(`/api/jobs/${encodeURIComponent(jobId)}/artifact/ai_visual_manifest.json?_t=${Date.now()}`, { cache: "no-store" });
        if (r.ok) {
          const m = JSON.parse(await r.text());
          const total = Array.isArray(m.target_beat_ids) ? m.target_beat_ids.length : 0;
          const missing = Array.isArray(m.remaining_missing_beats) ? m.remaining_missing_beats.length : 0;
          if (total > 0) {
            const done = Math.max(0, total - missing);
            const pct = Math.min(100, Math.round((done / total) * 100));
            byAgent.ai_visual = `Vẽ Keyframe 16:9: ${done}/${total} cảnh (${pct}%) · Còn ${missing} cảnh`;
            byAgent.orchestrator = `Chỉ huy bước Vẽ AI: đạt ${done}/${total} ảnh (${pct}%)`;
            byAgent.evidence_qa = `Trực nghiệm thu ${done}/${total} ảnh AI (lỗi bố cục/tỷ lệ sẽ bắt vẽ lại)`;
            return {
              phase: "ai_visual",
              agentId: "ai_visual",
              done,
              total,
              pct,
              stepIndex,
              stepState,
              byAgent,
              shortVi: `🎨 Đang vẽ ${done}/${total} ảnh (${pct}%)`,
              detailVi: byAgent.ai_visual,
            };
          }
        }
      } else if (currentPhase === "edit" || currentPhase === "qc") {
        let em = null;
        try {
          const emr = await fetch(`/api/jobs/${encodeURIComponent(jobId)}/artifact/edit_manifest.json?_t=${Date.now()}`, { cache: "no-store" });
          if (emr.ok) em = JSON.parse(await emr.text());
        } catch (_emErr) {}

        const emBeatsCount = em && Array.isArray(em.beats) ? em.beats.length : 0;
        const emTotalBeats = em ? Number(em.total_beats || emBeatsCount || 0) : 0;
        const emRealFootage = em ? Number(em.real_footage_beats_count || 0) : 0;
        const emVoxBeats = em ? Number(em.vox_beats_count || 0) : 0;
        const emUniqueClips = em ? Number(em.unique_footage_clips_mounted || 0) : 0;

        const r = await fetch(`/api/jobs/${encodeURIComponent(jobId)}/export-progress?_t=${Date.now()}`, { cache: "no-store" });
        if (r.ok) {
          const ep = await r.json();
          const isActivelyRendering = ep && (ep.running === true || ep.status === "running" || Number(ep.percent || 0) >= 1);
          if (isActivelyRendering) {
            const pct = Math.min(100, Math.round(Number(ep.percent || 0)));
            const rf = Number(ep.rendered_frames || ep.renderedFrames || 0);
            const tf = Number(ep.total_frames || ep.totalFrames || 0);
            const frameTxt = tf > 0 ? ` (${rf}/${tf} frames)` : "";
            const targetAg = currentPhase === "qc" ? "qc" : "edit";
            byAgent[targetAg] = `Render MP4 trực tiếp: ${pct}%${frameTxt}`;
            byAgent.orchestrator = `Giám sát xuất Master MP4: ${pct}%${frameTxt}`;
            if (emUniqueClips > 0 && !byAgent.footage) {
              byAgent.footage = `Đã gắn ${emUniqueClips} clip tư liệu sạch lên ${emRealFootage} phân cảnh`;
            }
            if (emVoxBeats > 0 && !byAgent.vox) {
              byAgent.vox = `Đã đóng gói ${emVoxBeats} đại cảnh Motion Vox 2.5D riêng biệt`;
            }
            return {
              phase: currentPhase,
              agentId: targetAg,
              done: rf || emBeatsCount,
              total: tf || emTotalBeats,
              pct,
              stepIndex,
              stepState,
              byAgent,
              editManifestSummary: em ? { doneBeats: emBeatsCount, totalBeats: emTotalBeats, realFootage: emRealFootage, voxBeats: emVoxBeats, uniqueClips: emUniqueClips } : null,
              shortVi: `🎬 Render MP4 ${pct}%`,
              detailVi: byAgent[targetAg],
            };
          }
        }
        const er = await fetch(`/api/jobs/${encodeURIComponent(jobId)}/artifact/edit_progress.json?_t=${Date.now()}`, { cache: "no-store" });
        if (er.ok || em) {
          const ed = er.ok ? JSON.parse(await er.text()) : {};
          const rawTotalB = Number(ed.total_beats || (Array.isArray(ed.assigned_beat_ids) ? ed.assigned_beat_ids.length : 0));
          const rawDoneB = Number(ed.completed_beats || (Array.isArray(ed.completed_beat_ids) ? ed.completed_beat_ids.length : 0));
          const totalB = Math.max(rawTotalB, emTotalBeats);
          const doneB = Math.min(totalB || Math.max(rawDoneB, emBeatsCount), Math.max(rawDoneB, emBeatsCount));
          const msg = ed.status_message || ed.message || ed.stage || "";
          const pct = totalB > 0 ? Math.min(100, Math.max(8, Math.round((doneB / totalB) * 100))) : 15;
          if (!byAgent.edit) {
            byAgent.edit = totalB > 0 ? `Đã ráp ${doneB}/${totalB} cảnh · ${latestActionVi || msg}` : (latestActionVi || msg);
          } else if (totalB > 0) {
            byAgent.edit = `[${doneB}/${totalB} cảnh] ${byAgent.edit}`;
          }
          if (!byAgent.vox) {
            byAgent.vox = emVoxBeats > 0
              ? `Đã lắp ${emVoxBeats} đại cảnh Motion Vox 2.5D đa cơ chế vào Timeline`
              : totalB > 0
              ? `Thiết kế sa bàn Motion Vox 2.5D đa cơ chế cho ${totalB} phân cảnh`
              : `Biên đạo đồ họa bản đồ & timeline Vox 2.5D khớp thoại`;
          }
          if (!byAgent.footage) {
            byAgent.footage = emUniqueClips > 0
              ? `Đã tuyển chọn & gắn ${emUniqueClips} clip sạch (3-Frame) cho ${emRealFootage} cảnh`
              : `Đối chiếu & kiểm duyệt khung hình sạch 3-Frame cho timeline`;
          } else if (emUniqueClips > 0) {
            byAgent.footage = `[${emUniqueClips} clip sạch] ${byAgent.footage}`;
          }
          byAgent.orchestrator = stepIndex > 0
            ? `Điều phối bước Dựng (#${stepIndex}) · Timeline ${doneB}/${totalB || 199} cảnh`
            : `Điều phối bước Dựng Remotion (${doneB}/${totalB || 199} cảnh)`;
          byAgent.evidence_qa = `Gác cổng Dựng Phim · Kiểm định ${doneB}/${totalB || 199} cảnh & đa dạng Vox 2.5D`;

          return {
            phase: currentPhase,
            agentId: "edit",
            done: doneB,
            total: totalB,
            pct,
            stepIndex,
            stepState,
            byAgent,
            editManifestSummary: em ? { doneBeats: doneB, totalBeats: totalB, realFootage: emRealFootage, voxBeats: emVoxBeats, uniqueClips: emUniqueClips } : null,
            shortVi: stepIndex > 0
              ? `⚡ #${stepIndex}: ${(latestActionVi || `Timeline ${doneB}/${totalB} cảnh`).slice(0, 44)}`
              : `✂️ Timeline ${doneB}/${totalB} cảnh (${Math.round((doneB / Math.max(1, totalB)) * 100)}%)`,
            detailVi: byAgent.edit,
          };
        }
      }
    } catch (_e) {
      // Ignore transient artifact read errors while file is being written
    }

    if (stepIndex > 0) {
      return {
        phase: currentPhase,
        agentId: currentPhase,
        done: 0,
        total: 0,
        pct: 0,
        stepIndex,
        stepState,
        byAgent,
        shortVi: `⚡ #${stepIndex}: ${latestActionVi.slice(0, 44)}`,
        detailVi: `#${stepIndex} · ${latestActionVi}`,
      };
    }
    return null;
  }

  async function fetchAgentCharter(agentId) {
    if (!agentId) return null;
    if (aoState.charterCache[agentId]) return aoState.charterCache[agentId];
    const resp = await fetch(`/api/agency/agents/${encodeURIComponent(agentId)}?include_body=true`);
    if (!resp.ok) return null;
    const data = await resp.json();
    aoState.charterCache[agentId] = data;
    return data;
  }

  // Specialist visual presets so each of the 92 staff members has a distinct Chibi look
  const SPECIALIST_STYLE_VARIATIONS = [
    { hairStyle: "headset", glasses: "visor", hair: "#0f172a", skin: "#fed7aa", hatTone: "#38bdf8" },
    { hairStyle: "cap", glasses: "round", hair: "#312e81", skin: "#fde68a", hatTone: "#f59e0b" },
    { hairStyle: "bob", glasses: "square", hair: "#701a75", skin: "#ffedd5", hatTone: "#ec4899" },
    { hairStyle: "spiky", glasses: "none", hair: "#064e3b", skin: "#fed7aa", hatTone: "#10b981" },
    { hairStyle: "beret", glasses: "round", hair: "#7c2d12", skin: "#fde68a", hatTone: "#a855f7" },
    { hairStyle: "bun", glasses: "visor", hair: "#1e3a8a", skin: "#ffedd5", hatTone: "#f43f5e" },
  ];

  // Build Articulated Cartoon Movie Character SVG for any of the 92 Staff Members (Lead, Deputy, or Specialist 0..5)
  function buildMemberChibiSvg(agentId, roleType, specIndex) {
    const p = CHIBI_PROFILES[agentId] || CHIBI_PROFILES.orchestrator;
    const isLead = !roleType || roleType === "lead";
    const isDeputy = roleType === "deputy";
    const v = SPECIALIST_STYLE_VARIATIONS[(Number(specIndex) || 0) % SPECIALIST_STYLE_VARIATIONS.length];

    const hairStyle = isLead ? p.hairStyle : isDeputy ? "headset" : v.hairStyle;
    const glasses = isLead ? p.glasses : isDeputy ? "square" : v.glasses;
    const skin = isLead ? p.skin : isDeputy ? "#ffedd5" : v.skin;
    const hair = isLead ? p.hair : isDeputy ? "#1e293b" : v.hair;
    const hatColor = isLead ? p.hatColor : isDeputy ? "#0284c7" : v.hatTone;
    const outfit = p.outfit;
    const accent = isLead ? "#facc15" : isDeputy ? "#38bdf8" : p.accent;
    const delaySec = (((Number(specIndex) || 0) * 0.27 + (isDeputy ? 0.41 : 0.13)) % 1.4).toFixed(2);

    let hairSvg = "";
    if (hairStyle === "beret") {
      hairSvg = `
        <path d="M16 25 C16 13, 52 13, 52 25 Z" fill="${hair}" stroke="#1e1b18" stroke-width="1.6" />
        <ellipse cx="35" cy="13.5" rx="19" ry="7" fill="${hatColor}" stroke="#1e1b18" stroke-width="1.7" transform="rotate(-9 35 13.5)" />
        <circle cx="35" cy="6.8" r="2.6" fill="${accent}" stroke="#1e1b18" stroke-width="1.2" />
      `;
    } else if (hairStyle === "headset") {
      hairSvg = `
        <path d="M16 26 C16 11, 52 11, 52 26 C48 19, 20 19, 16 26 Z" fill="${hair}" stroke="#1e1b18" stroke-width="1.6" />
        <path d="M14 27 C14 9, 54 9, 54 27" fill="none" stroke="${hatColor}" stroke-width="3.6" />
        <rect x="10.5" y="22" width="6.5" height="11" rx="3" fill="${hatColor}" stroke="#1e1b18" stroke-width="1.4" />
        <rect x="51" y="22" width="6.5" height="11" rx="3" fill="${hatColor}" stroke="#1e1b18" stroke-width="1.4" />
        <path d="M15 31 Q22 36 28 35" fill="none" stroke="#1e1b18" stroke-width="1.5" stroke-linecap="round" />
        <circle cx="28.5" cy="35" r="1.8" fill="#10b981" />
      `;
    } else if (hairStyle === "detective") {
      hairSvg = `
        <path d="M17 25 C17 14, 51 14, 51 25 Z" fill="${hair}" stroke="#1e1b18" stroke-width="1.6" />
        <ellipse cx="34" cy="15.5" rx="21" ry="4.5" fill="${hatColor}" stroke="#1e1b18" stroke-width="1.6" />
        <path d="M21 15.5 C22 5.5, 46 5.5, 47 15.5 Z" fill="${hatColor}" stroke="#1e1b18" stroke-width="1.6" />
        <rect x="22.5" y="13" width="23" height="2.6" fill="#fbbf24" />
      `;
    } else if (hairStyle === "cap") {
      hairSvg = `
        <path d="M17 25 C17 12, 51 12, 51 25 Z" fill="${hatColor}" stroke="#1e1b18" stroke-width="1.6" />
        <path d="M31 18 L56 21 C54 24.5, 42 24.5, 31 22.5 Z" fill="${accent}" stroke="#1e1b18" stroke-width="1.4" />
      `;
    } else if (hairStyle === "bun") {
      hairSvg = `
        <circle cx="34" cy="8.5" r="7" fill="${hair}" stroke="#1e1b18" stroke-width="1.6" />
        <path d="M16 26 C16 12, 52 12, 52 26 C46 20, 22 20, 16 26 Z" fill="${hair}" stroke="#1e1b18" stroke-width="1.6" />
        <rect x="27.5" y="12.5" width="13" height="2.8" rx="1.4" fill="${hatColor}" />
      `;
    } else if (hairStyle === "hardhat") {
      hairSvg = `
        <path d="M17 22 C17 8, 51 8, 51 22 Z" fill="${hatColor}" stroke="#1e1b18" stroke-width="1.6" />
        <rect x="14" y="20" width="40" height="3.5" rx="1.7" fill="#facc15" stroke="#1e1b18" stroke-width="1.3" />
        <rect x="30.5" y="9" width="7" height="9.5" rx="1.8" fill="#fef08a" />
      `;
    } else if (hairStyle === "doctor") {
      hairSvg = `
        <path d="M16 26 C16 12, 52 12, 52 26 Z" fill="${hair}" stroke="#1e1b18" stroke-width="1.6" />
        <rect x="18" y="14.5" width="32" height="4.4" rx="2.2" fill="#f8fafc" stroke="#1e1b18" stroke-width="1.2" />
        <circle cx="34" cy="16.5" r="4.6" fill="#38bdf8" stroke="#1e1b18" stroke-width="1.4" />
      `;
    } else if (hairStyle === "spiky") {
      hairSvg = `
        <path d="M16 26 L19 11 L27 16 L34 7 L41 16 L49 11 L52 26 Z" fill="${hair}" stroke="#1e1b18" stroke-width="1.6" stroke-linejoin="round" />
      `;
    } else if (hairStyle === "bob") {
      hairSvg = `
        <path d="M15 32 C14 11, 54 11, 53 32 L48 23.5 L20 23.5 Z" fill="${hair}" stroke="#1e1b18" stroke-width="1.6" stroke-linejoin="round" />
      `;
    } else {
      hairSvg = `
        <path d="M16 27 C16 11, 52 11, 52 27 C43 19.5, 25 20.5, 16 27 Z" fill="${hair}" stroke="#1e1b18" stroke-width="1.6" />
      `;
    }

    let glassesSvg = "";
    if (glasses === "round") {
      glassesSvg = `
        <circle cx="27" cy="29" r="4.6" fill="rgba(255,255,255,0.22)" stroke="#d97706" stroke-width="1.6" />
        <circle cx="41" cy="29" r="4.6" fill="rgba(255,255,255,0.22)" stroke="#d97706" stroke-width="1.6" />
        <line x1="31.6" y1="29" x2="36.4" y2="29" stroke="#d97706" stroke-width="1.5" />
      `;
    } else if (glasses === "square") {
      glassesSvg = `
        <rect x="22.2" y="25.2" width="9.6" height="6.8" rx="1.8" fill="rgba(56,189,248,0.2)" stroke="#1e293b" stroke-width="1.6" />
        <rect x="36.2" y="25.2" width="9.6" height="6.8" rx="1.8" fill="rgba(56,189,248,0.2)" stroke="#1e293b" stroke-width="1.6" />
        <line x1="31.8" y1="28.5" x2="36.2" y2="28.5" stroke="#1e293b" stroke-width="1.5" />
      `;
    } else if (glasses === "visor") {
      glassesSvg = `
        <rect x="21" y="25.2" width="26" height="6.5" rx="3.2" fill="rgba(45,212,191,0.52)" stroke="#0f766e" stroke-width="1.5" />
      `;
    }

    const rankCrestSvg = isLead
      ? `<polygon points="25,10 28.5,2 34,7.5 39.5,2 43,10" fill="#facc15" stroke="#1e1b18" stroke-width="1.3" />`
      : isDeputy
      ? `<polygon points="34,2.5 39.5,5.8 37.5,11 30.5,11 28.5,5.8" fill="#38bdf8" stroke="#1e1b18" stroke-width="1.3" />`
      : "";

    return `
      <svg class="ao-chibi-svg ao-toon-rig ao-role-${esc(roleType || "lead")}" style="--toon-delay:${delaySec}s;" viewBox="0 0 68 76" aria-hidden="true">
        <ellipse class="toon-ground-shadow" cx="34" cy="70" rx="16" ry="3.5" fill="rgba(28,25,23,0.28)" />
        <g class="chibi-leg-l toon-leg-l">
          <rect x="24.5" y="53" width="6.8" height="12" rx="3.2" fill="#1e293b" stroke="#1e1b18" stroke-width="1.5" />
          <ellipse cx="27.2" cy="65.8" rx="5.2" ry="2.8" fill="#f8fafc" stroke="#1e1b18" stroke-width="1.5" />
        </g>
        <g class="chibi-leg-r toon-leg-r">
          <rect x="36.5" y="53" width="6.8" height="12" rx="3.2" fill="#1e293b" stroke="#1e1b18" stroke-width="1.5" />
          <ellipse cx="40.8" cy="65.8" rx="5.2" ry="2.8" fill="#f8fafc" stroke="#1e1b18" stroke-width="1.5" />
        </g>
        <g class="toon-torso">
          <path d="M20 39 C20 35.5, 48 35.5, 48 39 L50 56 C50 58.5, 18 58.5, 18 56 Z" fill="${outfit}" stroke="#1e1b18" stroke-width="1.8" />
          <polygon points="29.5,38 38.5,38 34,47.5" fill="#ffffff" stroke="#1e1b18" stroke-width="1.1" />
          <polygon points="32,39 36,39 34,49" fill="${accent}" />
        </g>
        <g class="toon-arm-l">
          <rect x="13" y="39.5" width="7" height="13.5" rx="3.5" fill="${outfit}" stroke="#1e1b18" stroke-width="1.6" transform="rotate(14 16.5 41)" />
          <circle cx="15.2" cy="52.5" r="3.4" fill="${skin}" stroke="#1e1b18" stroke-width="1.5" />
        </g>
        <g class="toon-arm-r">
          <rect x="48" y="39.5" width="7" height="13.5" rx="3.5" fill="${outfit}" stroke="#1e1b18" stroke-width="1.6" transform="rotate(-14 51.5 41)" />
          <circle cx="52.8" cy="52.5" r="3.4" fill="${skin}" stroke="#1e1b18" stroke-width="1.5" />
        </g>
        <g class="toon-head-rig">
          <rect x="17.5" y="14.5" width="33" height="25.5" rx="12.5" fill="${skin}" stroke="#1e1b18" stroke-width="1.8" />
          <ellipse cx="22.8" cy="33" rx="3.5" ry="2" fill="rgba(251,113,133,0.58)" />
          <ellipse cx="45.2" cy="33" rx="3.5" ry="2" fill="rgba(251,113,133,0.58)" />
          <g class="toon-eyes-blink">
            <ellipse cx="27" cy="29" rx="2.7" ry="3.1" fill="#1e1b18" />
            <ellipse cx="41" cy="29" rx="2.7" ry="3.1" fill="#1e1b18" />
            <circle cx="28" cy="27.8" r="1.1" fill="#ffffff" />
            <circle cx="42" cy="27.8" r="1.1" fill="#ffffff" />
            <circle cx="26.2" cy="30.2" r="0.55" fill="#ffffff" />
            <circle cx="40.2" cy="30.2" r="0.55" fill="#ffffff" />
          </g>
          <path class="toon-mouth-talk" d="M30.5 34.2 Q34 37.6 37.5 34.2" fill="#ef4444" stroke="#1e1b18" stroke-width="1.5" stroke-linecap="round" />
          ${glassesSvg}
          ${hairSvg}
          ${rankCrestSvg}
        </g>
      </svg>
    `;
  }

  function buildStudioPetSvg(petId) {
    if (petId === "pet_cat") {
      return `
        <svg class="ao-chibi-svg ao-toon-pet-svg" viewBox="0 0 60 54" aria-hidden="true">
          <ellipse cx="30" cy="48" rx="16" ry="3.5" fill="rgba(28,25,23,0.25)" />
          <path class="toon-pet-tail" d="M44 38 Q55 28 51 18" fill="none" stroke="#f97316" stroke-width="4.5" stroke-linecap="round" />
          <ellipse cx="31" cy="37" rx="13" ry="9.5" fill="#fb923c" stroke="#1e1b18" stroke-width="1.8" />
          <circle class="toon-leg-l" cx="23" cy="46" r="3.4" fill="#fff7ed" stroke="#1e1b18" stroke-width="1.4" />
          <circle class="toon-leg-r" cx="38" cy="46" r="3.4" fill="#fff7ed" stroke="#1e1b18" stroke-width="1.4" />
          <g class="toon-head-rig">
            <polygon points="15,22 18,9 26,17" fill="#f97316" stroke="#1e1b18" stroke-width="1.7" />
            <polygon points="39,22 36,9 28,17" fill="#f97316" stroke="#1e1b18" stroke-width="1.7" />
            <ellipse cx="27" cy="24" rx="13" ry="10.5" fill="#fdba74" stroke="#1e1b18" stroke-width="1.8" />
            <circle cx="22.5" cy="23.5" r="2.2" fill="#1e1b18" />
            <circle cx="31.5" cy="23.5" r="2.2" fill="#1e1b18" />
            <circle cx="23.2" cy="22.8" r="0.8" fill="#ffffff" />
            <circle cx="32.2" cy="22.8" r="0.8" fill="#ffffff" />
            <polygon points="25.5,26 28.5,26 27,28" fill="#f43f5e" />
            <path d="M24 28.5 Q27 30.5 30 28.5" fill="none" stroke="#1e1b18" stroke-width="1.4" stroke-linecap="round" />
          </g>
        </svg>
      `;
    }
    return `
      <svg class="ao-chibi-svg ao-toon-pet-svg" viewBox="0 0 60 54" aria-hidden="true">
        <ellipse cx="30" cy="48" rx="16" ry="3.5" fill="rgba(28,25,23,0.25)" />
        <path class="toon-pet-tail" d="M44 35 Q53 27 49 21" fill="none" stroke="#eab308" stroke-width="5" stroke-linecap="round" />
        <ellipse cx="31" cy="37" rx="14" ry="9.5" fill="#f59e0b" stroke="#1e1b18" stroke-width="1.8" />
        <ellipse cx="26" cy="38" rx="7" ry="6" fill="#fef9c3" />
        <circle class="toon-leg-l" cx="22" cy="46" r="3.5" fill="#fef9c3" stroke="#1e1b18" stroke-width="1.4" />
        <circle class="toon-leg-r" cx="39" cy="46" r="3.5" fill="#fef9c3" stroke="#1e1b18" stroke-width="1.4" />
        <g class="toon-head-rig">
          <polygon points="15,21 16,7 25,16" fill="#d97706" stroke="#1e1b18" stroke-width="1.7" />
          <polygon points="39,21 38,7 29,16" fill="#d97706" stroke="#1e1b18" stroke-width="1.7" />
          <ellipse cx="27" cy="24" rx="13" ry="10.5" fill="#fbbf24" stroke="#1e1b18" stroke-width="1.8" />
          <ellipse cx="27" cy="27" rx="6" ry="4.5" fill="#fef9c3" />
          <circle cx="22.5" cy="22.5" r="2.2" fill="#1e1b18" />
          <circle cx="31.5" cy="22.5" r="2.2" fill="#1e1b18" />
          <circle cx="27" cy="25.8" r="2" fill="#1e1b18" />
          <path d="M25.5 28.5 Q27 31.5 28.5 28.5" fill="#f43f5e" stroke="#1e1b18" stroke-width="1.1" />
        </g>
      </svg>
    `;
  }

  function buildChibiSvg(agentId) {
    return buildMemberChibiSvg(agentId, "lead", 0);
  }

  function getMergedDeptRoster(agentId, snap) {
    const def = DEFAULT_DEPT_ROSTER_92[agentId] || DEFAULT_DEPT_ROSTER_92.orchestrator;
    const liveDept =
      (Array.isArray(snap?.departments) && snap.departments.find((d) => d.agent_id === agentId)) ||
      (Array.isArray(snap?.agents) && snap.agents.find((a) => a.id === agentId)?.department_hierarchy) ||
      {};
    const pe = liveDept.parallel_engine || {};
    const liveBatches = Array.isArray(pe.batches) ? pe.batches : [];
    const liveSpecs = Array.isArray(liveDept.specialists) && liveDept.specialists.length ? liveDept.specialists : def.specialists;
    const totalSpecs = def.specialists.length;

    const lead = {
      id: liveDept.lead?.id || def.lead.id,
      handle: liveDept.lead?.handle || def.lead.handle,
      shortTag: def.lead.shortTag || "👑 Trưởng",
      title_vi: liveDept.lead?.title_vi || def.lead.title_vi,
      role_vi: liveDept.lead?.role_vi || def.lead.role_vi,
      approval_output_vi: liveDept.lead?.approval_output_vi || "Ký duyệt & Bàn giao",
      live_badge_vi: liveDept.lead?.live_badge_vi || "👑 Chỉ huy & Chia lô",
    };
    const deputy = {
      id: liveDept.deputy?.id || def.deputy.id,
      handle: liveDept.deputy?.handle || def.deputy.handle,
      shortTag: def.deputy.shortTag || "🛡️ Phó",
      title_vi: liveDept.deputy?.title_vi || def.deputy.title_vi,
      role_vi: liveDept.deputy?.role_vi || def.deputy.role_vi,
      checklist_vi: Array.isArray(liveDept.deputy?.checklist_vi) ? liveDept.deputy.checklist_vi : [],
      live_badge_vi: liveDept.deputy?.live_badge_vi || "🛡️ Rà Checklist 100%",
    };

    const specialists = def.specialists.map((dSp, idx) => {
      const lSp = liveSpecs[idx] || {};
      const b = liveBatches[idx] || {};
      const lane = idx + 1;
      const batchId = b.batch_id || lSp.batch_id || `LÔ-0${lane}`;
      const startBeat = idx * Math.floor(204 / totalSpecs) + 1;
      const endBeat = idx === totalSpecs - 1 ? 204 : (idx + 1) * Math.floor(204 / totalSpecs);
      const itemsLabel = b.items_label || lSp.items_label || `B${String(startBeat).padStart(3, "0")}–B${String(endBeat).padStart(3, "0")}`;
      const pct = Number(b.progress_pct != null ? b.progress_pct : lSp.progress_pct != null ? lSp.progress_pct : 100);
      return {
        id: lSp.id || dSp.id,
        handle: lSp.handle || dSp.handle,
        shortTag: dSp.shortTag || `L${lane}`,
        title_vi: lSp.title_vi || dSp.title_vi,
        role_vi: lSp.role_vi || lSp.task_detail_vi || dSp.role_vi,
        artifact_key: lSp.artifact_key || b.artifact_key || "artifact.json",
        input_from: lSp.input_from || lead.handle,
        output_to: lSp.output_to || deputy.handle,
        parallel_lane: lane,
        batch_id: batchId,
        items_label: itemsLabel,
        progress_pct: pct,
        worker_thread: b.worker_thread || lSp.worker_thread || `pool-${agentId}-w0${lane}`,
        elapsed_ms: Number(b.elapsed_ms || lSp.elapsed_ms || 18 + lane * 5),
        finding_vi: b.finding_vi || b.current_action_vi || lSp.current_action_vi || dSp.role_vi,
      };
    });

    return {
      code: liveDept.code || CHIBI_PROFILES[agentId]?.deptCode || "DEPT",
      name_vi: liveDept.name_vi || CHIBI_PROFILES[agentId]?.nickVi || agentId,
      headcount: 2 + specialists.length,
      speedup_factor: pe.speedup_factor || (specialists.length >= 6 ? "4.5x" : "4.2x"),
      active_mini_agent_handle: liveDept.active_mini_agent_handle || "",
      lead,
      deputy,
      specialists,
    };
  }

  function updateTriggerButtons(snap) {
    if (!snap || !snap.summary) return;
    const sum = snap.summary;
    const activeCount = Number(sum.active_agents_count || 0);
    const criticCount = Number(sum.active_critic_count || 0);
    const reworkedCount = Number(sum.reworked_gates || 0);

    const gates = Array.isArray(snap.critique_gates) ? snap.critique_gates : [];
    const liveReworkingGate = gates.find((g) => g && g.gate_state === "reworking_live");
    const liveReworking = Boolean(liveReworkingGate);

    if (liveReworkingGate) {
      const rk = `${liveReworkingGate.phase}:${liveReworkingGate.badge_vi}`;
      if (aoState.lastReworkAlertKey !== rk) {
        aoState.lastReworkAlertKey = rk;
        playStudioSound("stamp");
      }
    }

    const btn = document.getElementById("openAgentOfficeBtn");
    const badge = document.getElementById("aoTriggerBadge");
    const titleBtn = document.getElementById("desktopAgentOfficeBtn");
    const healthDept = document.getElementById("healthDepartments");
    const healthDeptSub = document.getElementById("healthDepartmentsSub");

    if (btn) {
      btn.classList.toggle("has-active", activeCount > 0 && criticCount === 0 && !liveReworking);
      btn.classList.toggle("has-critic", criticCount > 0 || liveReworking);
    }
    if (badge) {
      if (liveReworking) {
        badge.textContent = "🔄 Phòng tự sửa";
      } else if (criticCount > 0) {
        badge.textContent = "⚖️ Đang nghiệm thu";
      } else if (activeCount > 0) {
        badge.textContent = `${activeCount}/15 Phòng chạy`;
      } else if (reworkedCount > 0) {
        badge.textContent = `🔄 ${reworkedCount} Phòng sửa đạt`;
      } else {
        badge.textContent = "15 Phòng · 92 NS";
      }
    }
    if (titleBtn) {
      titleBtn.style.color = criticCount > 0 || liveReworking ? "#fbbf24" : activeCount > 0 ? "#34d399" : "";
      titleBtn.title =
        criticCount > 0 || liveReworking
          ? "🏛️ 15 Phòng Ban Chuyên Môn · Đang nghiệm thu & phản biện trực tiếp!"
          : activeCount > 0
          ? `🏛️ 15 Phòng Ban Chuyên Môn · ${activeCount}/15 Phòng Ban đang trực chiến (92 NS)`
          : "🏛️ Mở 15 Phòng Ban Chuyên Môn (15 Tổ trưởng · 15 Tổ phó · 62 Chuyên viên Mini-Agents) (Ctrl+Shift+O)";
    }
    if (healthDept) {
      healthDept.textContent =
        activeCount > 0
          ? `🟢 ${activeCount}/15 Phòng đang chạy`
          : "15 Trưởng · 15 Phó · 62 CV";
    }
    if (healthDeptSub) {
      healthDeptSub.textContent =
        activeCount > 0
          ? `92 Nhân sự trực chiến · Đang vận hành dây chuyền`
          : "92 Nhân sự · DEPT-00..14 · @vox 8 NS";
    }
  }

  function renderJobPicker(snap) {
    const sel = document.getElementById("agentOfficeJobSelect");
    if (!sel || !snap) return;
    const jobs = Array.isArray(snap.jobs_list) ? snap.jobs_list : [];
    const activeId = snap.selected_job?.id || aoState.selectedJobId || "";
    window.__cofiAgentOfficeActiveJobId = activeId;
    const autoLabel = snap.selected_job
      ? `🟢 Tự động theo dự án đang chạy (${esc(snap.selected_job.id)} — ${esc(String(snap.selected_job.title || "").slice(0, 58))})`
      : "Tự động theo dự án đang chạy";
    const pinnedId = aoState.userPinnedJobId || "";
    const html = [
      `<option value=""${!pinnedId ? " selected" : ""}>${autoLabel}</option>`,
      ...jobs.map((j) => {
        const mark = j.status === "running" ? "🟢 " : j.status === "completed" ? "✓ " : "• ";
        const selected = pinnedId && j.id === pinnedId ? " selected" : "";
        return `<option value="${esc(j.id)}"${selected}>${mark}${esc(j.id)} — ${esc(j.title)}</option>`;
      }),
    ].join("");
    if (sel.innerHTML !== html) {
      sel.innerHTML = html;
      sel.value = pinnedId;
    }
  }

  function renderKpis(snap) {
    const host = document.getElementById("agentOfficeKpis");
    if (!host || !snap) return;
    const s = snap.summary || {};
    const dsum = snap.departments_summary || {};
    const depts = Array.isArray(snap.departments) ? snap.departments : [];
    const voxDept = depts.find((d) => d.agent_id === "vox");
    const voxActiveMini = voxDept?.active_mini_agent_handle || "6 Chuyên viên trực chiến";
    const ageText =
      s.latest_event_age_sec !== null && s.latest_event_age_sec !== undefined
        ? `Đồng bộ ${s.latest_event_age_sec}s trước`
        : "Đồng bộ thời gian thực";
    const ageLine = `${ageText}${s.total_output_tokens ? ` · ${(s.total_output_tokens / 1000).toFixed(1)}k tok` : ""}`;

    const kpiSig = [
      Number(s.active_agents_count || 0),
      Number(dsum.total_departments || s.total_departments || 15),
      Number(dsum.total_personnel || s.total_personnel || 92),
      voxActiveMini,
      Number(s.passed_gates || 0),
      Number(s.total_gates || 8),
      Number(s.reworked_gates || 0),
      Number(s.total_rewrites_or_rerolls || 0),
      Number(s.total_output_tokens || 0),
    ].join("|");

    if (aoState._lastKpiSig === kpiSig && host.children.length > 0) {
      const ageEl = host.querySelector("[data-ao-kpi-age]");
      if (ageEl && ageEl.textContent !== ageLine) {
        ageEl.textContent = ageLine;
      }
      renderLiveStatusBar(snap);
      return;
    }
    aoState._lastKpiSig = kpiSig;

    host.innerHTML = `
      <div class="ao-kpi-card">
        <div>
          <span>🏢 TỔ HỢP VĂN PHÒNG 2.5D</span>
          <strong>${Number(s.active_agents_count || 0)} / ${Number(dsum.total_departments || s.total_departments || 15)} Phòng Hoạt Động</strong>
          <small>${Number(dsum.total_personnel || s.total_personnel || 92)} Nhân sự (15 Trưởng · 15 Phó · 62 Chuyên viên)</small>
        </div>
        <span class="ao-kpi-ico">${Number(s.active_agents_count || 0) > 0 ? "🟢" : "🏢"}</span>
      </div>
      <div class="ao-kpi-card" style="border-color:rgba(16,185,129,0.38);">
        <div>
          <span>⭐ PHÒNG TRỌNG ĐIỂM · DEPT-08 VOX</span>
          <strong>8 Nhân sự · 6 Bàn Chuyên Viên 2.5D</strong>
          <small>Trạng thái: ${esc(voxActiveMini)}</small>
        </div>
        <span class="ao-kpi-ico">🗺️</span>
      </div>
      <div class="ao-kpi-card">
        <div>
          <span>⚖️ CỔNG NGHIỆM THU LIÊN PHÒNG</span>
          <strong>${Number(s.passed_gates || 0)} / ${Number(s.total_gates || 8)} Cổng Đạt Chuẩn</strong>
          <small>Trưởng phân lô ➔ Chuyên viên ➔ Phó duyệt</small>
        </div>
        <span class="ao-kpi-ico">⚖️</span>
      </div>
      <div class="ao-kpi-card kpi-rework">
        <div>
          <span>🔄 KIỂM SOÁT CHẤT LƯỢNG &amp; TỰ SỬA</span>
          <strong>${Number(s.reworked_gates || 0)} khâu · ${Number(s.total_rewrites_or_rerolls || 0)} lượt tinh chỉnh</strong>
          <small data-ao-kpi-age="1">${esc(ageLine)}</small>
        </div>
        <span class="ao-kpi-ico">⚡</span>
      </div>
    `;
    renderLiveStatusBar(snap);
  }

  function renderLiveStatusBar(snap) {
    const barEl = document.getElementById("agentOfficeLiveStatusBar");
    if (!barEl || !snap) return;
    const lpr = snap.live_phase_report || {};
    const tel = aoState.livePhaseTelemetry || {};
    const primaryId = resolvePrimaryWorkingDepartment(snap) || lpr.primary_agent_id || "script";
    const prof = CHIBI_PROFILES[primaryId] || CHIBI_PROFILES.script;
    const roster = getMergedDeptRoster(primaryId, snap);
    const isRunning = Boolean(lpr.is_running);
    const pct = Number(tel.pct || lpr.percent || (isRunning ? 65 : 100));
    const stepIdx = Number(tel.stepIndex || lpr.step_index || snap.summary?.total_cli_steps || 0);
    const phaseLabel = String(lpr.phase_label_vi || "Bước 1 · Lập Kế Hoạch & Kịch Bản");
    const actionVi = String(
      (tel.byAgent && tel.byAgent[primaryId]) ||
        lpr.current_action_vi ||
        "Đang thực thi dây chuyền sản xuất trực tiếp…"
    );
    const etaVi = String(lpr.eta_vi || computePhaseEtaVi(isRunning, pct, lpr.phase || "plan"));
    const milestones = Array.isArray(lpr.milestones) ? lpr.milestones : [];

    const jumpBtn = document.getElementById("aoJumpActiveRoomBtn");
    if (jumpBtn) {
      jumpBtn.textContent = `🔍 Vào Phòng Đang Làm (${prof.deptCode} @${primaryId} · ${roster.headcount} NS)`;
      jumpBtn.setAttribute("data-ao-jump-active-room", primaryId);
    }

    const msPillsHtml = milestones
      .slice(0, 4)
      .map((m) => {
        const ic = m.done ? "✅" : "⚡";
        const cls = m.done ? "is-done" : "is-pending";
        return `<span class="ao-lsb-ms-pill ${cls}" title="${esc(m.label_vi)}: ${esc(m.detail_vi)}">${ic} <b>${esc(m.file)}</b> <small>${esc(m.detail_vi)}</small></span>`;
      })
      .join("");

    barEl.innerHTML = `
      <div class="ao-lsb-row">
        <div class="ao-lsb-left">
          <span class="ao-lsb-pulse ${isRunning ? "is-running" : "is-idle"}"></span>
          <span class="ao-lsb-dept-badge" data-ao-focus-member="${esc(primaryId)}:lead" title="Click để vào xem bên trong phòng ${esc(prof.deptCode)}">
            ${prof.prop} <b>${esc(prof.deptCode)} · @${esc(primaryId)}</b> (${roster.headcount}/92 NS)
          </span>
          <div class="ao-lsb-main-txt">
            <strong>${esc(phaseLabel)}${stepIdx > 0 ? ` · Bước #${stepIdx}` : ""}:</strong>
            <span>${esc(actionVi)}</span>
          </div>
        </div>
        <div class="ao-lsb-center">
          <div class="ao-lsb-bar-wrap">
            <div class="ao-lsb-bar-fill" style="width:${Math.max(6, Math.min(100, pct))}%;"></div>
          </div>
          <span class="ao-lsb-pct">${pct}%</span>
          <span class="ao-lsb-eta-pill" title="Thời gian dự kiến hoàn tất công đoạn hiện tại">
            ⏱️ <b>Bao lâu nữa xong:</b> ${esc(etaVi)}
          </span>
        </div>
        <div class="ao-lsb-right">
          ${
            aoState.focusedAgentId
              ? `<button type="button" class="ao-lsb-btn" data-ao-exit-focus="true">⬅ Toàn Cảnh 15 Phòng (92 NS)</button>`
              : `<button type="button" class="ao-lsb-btn primary" data-ao-focus-member="${esc(primaryId)}:lead">🔍 Vào Phòng @${esc(primaryId)}</button>`
          }
          <button type="button" class="ao-lsb-btn chat-btn" data-ao-open-group-chat="1">💬 Nhóm Chat Báo Cáo</button>
        </div>
      </div>
      ${msPillsHtml ? `<div class="ao-lsb-ms-row">${msPillsHtml}</div>` : ""}
    `;
  }

  function buildLiveGroupChatMessages(snap) {
    if (!snap) return [];
    const lpr = snap.live_phase_report || {};
    const tel = aoState.livePhaseTelemetry || {};
    const curPhase = String(lpr.phase || snap.selected_job?.current_phase || "plan").toLowerCase();
    const isRunning = Boolean(lpr.is_running);
    const pct = Number(tel.pct || lpr.percent || (isRunning ? 65 : 100));
    const stepIdx = Number(tel.stepIndex || lpr.step_index || snap.summary?.total_cli_steps || 0);
    const etaVi = String(lpr.eta_vi || computePhaseEtaVi(isRunning, pct, curPhase));
    const primaryId = resolvePrimaryWorkingDepartment(snap) || lpr.primary_agent_id || "script";
    const prof = CHIBI_PROFILES[primaryId] || CHIBI_PROFILES.script;
    const roster = getMergedDeptRoster(primaryId, snap);
    const milestones = Array.isArray(lpr.milestones) ? lpr.milestones : [];
    const doneMs = milestones.filter((m) => m.done);
    const pendingMs = milestones.filter((m) => !m.done);

    const nextDeptMap = {
      plan: "voice",
      research: "script",
      script: "voice",
      voice: "visuals",
      visuals: "footage",
      footage: "ai_visual",
      ai_visual: "vox",
      vox: "edit",
      edit: "seo",
      seo: "qc",
      qc: "orchestrator",
    };
    const nextDeptId = nextDeptMap[primaryId] || nextDeptMap[curPhase] || "voice";
    const nextProf = CHIBI_PROFILES[nextDeptId] || CHIBI_PROFILES.voice;
    const nextRoster = getMergedDeptRoster(nextDeptId, snap);

    const msgs = [];

    // 1. Orchestrator Lead opens the shift for all 15 Departments × 92 Staff
    msgs.push({
      id: "msg-orch-open",
      agentId: "orchestrator",
      senderHandle: "@orchestrator_lead",
      senderTitle: "Tổng Đạo Diễn Điều Hành",
      deptCode: "DEPT-00",
      deptName: "Ban Điều Hành (6 NS)",
      roleBadge: "👑 Tổng Chỉ Huy",
      avatar: "📣",
      timeLabel: "Ca trực LIVE",
      statusPill: "🟢 15 Phòng · 92 NS trực chiến",
      text: `Chào anh em toàn xưởng (15 Phòng Ban · 92 Nhân sự)! Hiện tại dây chuyền đang chạy «${lpr.phase_label_vi || `Bước · ${curPhase}`}». Đề nghị Tổ trưởng @${primaryId}_lead (${prof.deptCode}) cùng các Chuyên viên báo cáo rõ trên nhóm: đang làm gì, đã xong đến đâu (%), và BAO LÂU NỮA THÌ XONG để @${nextDeptId}_lead chuẩn bị nhận bàn giao!`,
    });

    // 2. If in `plan` and research.md is done, @research_lead reports handoff to @script_lead
    if (curPhase === "plan") {
      const resMs = milestones.find((m) => /research\.md/i.test(m.file));
      if (resMs && resMs.done) {
        msgs.push({
          id: "msg-research-handoff",
          agentId: "research",
          senderHandle: "@research_lead",
          senderTitle: "Tổ Trưởng Điều Tra Hồ Sơ",
          deptCode: "DEPT-02",
          deptName: "Phòng Hồ Sơ (6 NS)",
          roleBadge: "✅ Đã bàn giao 100%",
          avatar: "🔎",
          timeLabel: "Đã hoàn tất",
          statusPill: `✅ research.md (${resMs.detail_vi})`,
          text: `Báo cáo @orchestrator_lead và @script_lead: Phòng 02 (6/6 NS: @research_source_hunter, @research_timeline_mapper, @research_fact_verifier, @research_deputy) đã khóa xong hồ sơ điều tra gốc research.md (${resMs.detail_vi}). Đã chuyển toàn bộ mốc thời gian & chứng cứ sang Phòng 03 (@script_lead)!`,
        });
      }
    }

    // 3. Active Department Lead assigns batches to the 4–6 Specialists
    const specHandlesList = roster.specialists.map((s) => `${s.handle} (${s.shortTag})`).join(", ");
    msgs.push({
      id: `msg-${primaryId}-lead-plan`,
      agentId: primaryId,
      senderHandle: roster.lead.handle,
      senderTitle: roster.lead.title_vi,
      deptCode: roster.code,
      deptName: `${prof.shortTitleVi} (${roster.headcount} NS)`,
      roleBadge: "👑 Tổ Trưởng Chỉ Huy",
      avatar: prof.prop,
      timeLabel: stepIdx > 0 ? `Bước #${Math.max(1, stepIdx - 2)}` : "Đang chạy",
      statusPill: `⚡ Chia ${roster.specialists.length} lô song song (${roster.speedup_factor})`,
      text: `Đã nhận lệnh từ @orchestrator_lead! Phòng ${roster.code} (${roster.headcount}/92 nhân sự) đang chia ${roster.specialists.length} luồng chạy song song cho: ${specHandlesList}. Anh em báo cáo tiến độ từng hạng mục lên nhóm ngay nhé!`,
    });

    // 4. Specialists report completed & currently running milestones in the Group Chat
    roster.specialists.slice(0, 4).forEach((sp, idx) => {
      const ms = milestones[idx];
      if (!ms) return;
      const isDone = Boolean(ms.done);
      const spPct = isDone ? 100 : Math.max(55, Math.min(96, pct));
      msgs.push({
        id: `msg-${primaryId}-spec-${idx}`,
        agentId: primaryId,
        senderHandle: sp.handle,
        senderTitle: sp.title_vi,
        deptCode: roster.code,
        deptName: `${sp.batch_id} · ${sp.items_label}`,
        roleBadge: isDone ? `✅ Xong Lô #${idx + 1}` : `🟢 Đang làm Lô #${idx + 1}`,
        avatar: isDone ? "✅" : "⚡",
        timeLabel: isDone ? "Hoàn tất 100%" : `Đang chạy · ${spPct}%`,
        statusPill: `${ms.file} (${ms.detail_vi})`,
        text: isDone
          ? `Báo cáo ${roster.lead.handle} & ${roster.deputy.handle}: Em đã hoàn thành 100% hạng mục «${ms.label_vi}» → tệp ${ms.file} (${ms.detail_vi}). Đã đẩy sang Tổ phó kiểm tra!`
          : `Báo cáo cả nhóm: Em đang trực tiếp xử lý «${ms.label_vi}» → tệp ${ms.file} (${ms.detail_vi}). Hiện đạt ${spPct}%, đang phối hợp cùng ${roster.deputy.handle} để khóa sổ!`,
      });
    });

    // 5. Active Department Deputy reports overall checklist, current action, % and ETA ("bao lâu nữa thì xong")
    const curActionClean = String(
      (tel.byAgent && tel.byAgent[primaryId]) ||
        lpr.current_action_vi ||
        "Đang hoàn thiện & rà soát đầu ra trên đĩa"
    );
    msgs.push({
      id: `msg-${primaryId}-deputy-eta`,
      agentId: primaryId,
      senderHandle: roster.deputy.handle,
      senderTitle: roster.deputy.title_vi,
      deptCode: roster.code,
      deptName: `${prof.shortTitleVi} (${roster.headcount} NS)`,
      roleBadge: "🛡️ Tổ Phó Báo Cáo ETA",
      avatar: "🛡️",
      timeLabel: stepIdx > 0 ? `LIVE · Bước #${stepIdx}` : "LIVE",
      statusPill: `📊 Tiến độ ${pct}% · ⏱️ ${etaVi}`,
      isHighlightEta: true,
      text: `📊 [BÁO CÁO TIẾN ĐỘ & THỜI GIAN HOÀN THÀNH] Báo cáo Sếp và @orchestrator_lead:\n• Đang làm gì: ${curActionClean}\n• Làm đến đâu: Đã hoàn tất ${doneMs.length}/${milestones.length || 4} cột mốc (${doneMs.map((m) => m.file).join(", ") || "đang khởi tạo"})${pendingMs.length ? ` — đang khóa nốt ${pendingMs.map((m) => m.file).join(", ")}` : ""} — Tổng tiến độ đạt ${pct}%.\n• ⏱️ Bao lâu nữa xong (ETA): ${etaVi}!`,
    });

    // 6. QA Lead & Next Department Lead acknowledge in the group chat
    msgs.push({
      id: `msg-next-ready-${nextDeptId}`,
      agentId: nextDeptId,
      senderHandle: nextRoster.lead.handle,
      senderTitle: nextRoster.lead.title_vi,
      deptCode: nextRoster.code,
      deptName: `${nextProf.shortTitleVi} (${nextRoster.headcount} NS)`,
      roleBadge: "⏳ Trực nhận bàn giao",
      avatar: nextProf.prop,
      timeLabel: "Trực chiến",
      statusPill: `Sẵn sàng ${nextRoster.headcount}/${nextRoster.headcount} NS`,
      text: `Đã rõ @${primaryId}_lead và ${roster.deputy.handle}! Đội ${nextRoster.code} (${nextRoster.headcount} nhân sự) cùng Thanh tra @evidence_qa_lead đang trực sẵn trên nhóm. Ngay khi ${roster.code} báo xong (${etaVi}) là bên mình tiếp nhận chạy tiếp ngay lập tức!`,
    });

    // 7. Append any interactive messages sent by the user in this session
    if (Array.isArray(aoState.userGroupChatMessages) && aoState.userGroupChatMessages.length > 0) {
      aoState.userGroupChatMessages.forEach((um) => msgs.push(um));
    }

    return msgs;
  }

  function handleSendGroupChatMessage(rawText) {
    const txt = String(rawText || "").trim();
    if (!txt) return;
    const snap = aoState.snapshot || buildInstantFallbackSnapshot();
    const lpr = snap.live_phase_report || {};
    const tel = aoState.livePhaseTelemetry || {};
    const primaryId = resolvePrimaryWorkingDepartment(snap) || lpr.primary_agent_id || "script";
    const prof = CHIBI_PROFILES[primaryId] || CHIBI_PROFILES.script;
    const roster = getMergedDeptRoster(primaryId, snap);
    const isRunning = Boolean(lpr.is_running);
    const pct = Number(tel.pct || lpr.percent || (isRunning ? 65 : 100));
    const stepIdx = Number(tel.stepIndex || lpr.step_index || snap.summary?.total_cli_steps || 0);
    const etaVi = String(lpr.eta_vi || computePhaseEtaVi(isRunning, pct, lpr.phase || "plan"));
    const milestones = Array.isArray(lpr.milestones) ? lpr.milestones : [];
    const doneFiles = milestones.filter((m) => m.done).map((m) => `${m.file} (${m.detail_vi})`).join(", ") || "đang xử lý";
    const nowStr = new Date().toLocaleTimeString("vi-VN", { hour12: false });

    aoState.userGroupChatMessages.push({
      id: `user-msg-${Date.now()}`,
      agentId: "user",
      senderHandle: "🧑‍💼 Giám Đốc Sản Xuất (Bạn)",
      senderTitle: "Chỉ đạo trực tiếp trên Nhóm Chat",
      deptCode: "PRODUCER",
      deptName: "Ban Giám Đốc",
      roleBadge: "👑 Sếp Chỉ Đạo",
      avatar: "🧑‍💼",
      timeLabel: nowStr,
      statusPill: "📨 Tin nhắn mới",
      isUser: true,
      text: txt,
    });

    let replyText = "";
    if (/nhân sự|mấy người|bao nhiêu|điểm danh|15 phòng|92/i.test(txt)) {
      replyText = `Báo cáo Sếp! Toàn xưởng có đầy đủ 15 Phòng Ban × 92 Nhân sự (15 Tổ trưởng · 15 Tổ phó · 62 Chuyên viên Mini-Agents + 12 Giao liên & Thú cưng). Hiện tại Phòng ${roster.code} (${prof.shortTitleVi} · ${roster.headcount} NS) đang trực tiếp làm bước «${lpr.phase_label_vi || "Hiện tại"}», còn 14 Phòng Ban kia (86 NS) đang trực chiến chờ nhận bàn giao theo dây chuyền!`;
    } else if (/bao lâu|khi nào xong|mấy phút|eta|tiến độ|đến đâu/i.test(txt)) {
      replyText = `Báo cáo Sếp ngay ạ!\n• Phòng phụ trách: ${roster.code} (${roster.lead.handle} + ${roster.deputy.handle} + ${roster.specialists.length} Chuyên viên)\n• Công việc đang làm: ${lpr.current_action_vi || "Đang xử lý trực tiếp trên workspace"} (Bước #${stepIdx})\n• Đã hoàn thành: ${doneFiles} — đạt ${pct}%\n• ⏱️ Bao lâu nữa xong: ${etaVi}!`;
    } else {
      replyText = `Đã nhận lệnh của Sếp («${txt}»)! Tổ trưởng ${roster.lead.handle} cùng Tổ phó ${roster.deputy.handle} và ${roster.specialists.length} Chuyên viên (${roster.code}) đang thực thi ở mức ${pct}% (Bước #${stepIdx}). ⏱️ Dự kiến: ${etaVi}. Nếu Sếp muốn giao lệnh sâu vào hệ thống, bấm nút «📨 Chuyển vào Hộp Chat Chính» bên dưới nhé!`;
    }

    aoState.userGroupChatMessages.push({
      id: `agent-reply-${Date.now() + 1}`,
      agentId: primaryId,
      senderHandle: roster.lead.handle,
      senderTitle: roster.lead.title_vi,
      deptCode: roster.code,
      deptName: `${prof.shortTitleVi} (${roster.headcount} NS)`,
      roleBadge: "👑 Trả lời Sếp ngay",
      avatar: prof.prop,
      timeLabel: nowStr,
      statusPill: `📊 ${pct}% · ⏱️ ${etaVi}`,
      isHighlightEta: true,
      text: replyText,
    });

    playStudioSound("ask");
    aoState._lastInspectorSig = "";
    aoState._lastFocusSig = "";
    if (aoState.snapshot) {
      renderInspector(aoState.snapshot, true);
      if (aoState.focusedAgentId) renderFocusReplyOverlay();
    }
    setTimeout(() => {
      document.querySelectorAll(".ao-gchat-messages").forEach((el) => {
        el.scrollTop = el.scrollHeight;
      });
    }, 30);
  }

  function renderGroupChatPanelHtml(snap, isCompact) {
    const lpr = snap?.live_phase_report || {};
    const tel = aoState.livePhaseTelemetry || {};
    const primaryId = resolvePrimaryWorkingDepartment(snap) || lpr.primary_agent_id || "script";
    const prof = CHIBI_PROFILES[primaryId] || CHIBI_PROFILES.script;
    const roster = getMergedDeptRoster(primaryId, snap);
    const isRunning = Boolean(lpr.is_running);
    const pct = Number(tel.pct || lpr.percent || (isRunning ? 65 : 100));
    const etaVi = String(lpr.eta_vi || computePhaseEtaVi(isRunning, pct, lpr.phase || "plan"));
    const msgs = buildLiveGroupChatMessages(snap);
    const inputId = isCompact ? "aoRoomGroupChatInput" : "aoDockGroupChatInput";

    const msgsHtml = msgs
      .map((m) => {
        const cls = [
          "ao-gchat-msg",
          m.isUser ? "is-user-msg" : "",
          m.isHighlightEta ? "is-eta-report" : "",
        ]
          .filter(Boolean)
          .join(" ");
        return `
          <article class="${cls}" data-ao-gchat-agent="${esc(m.agentId)}">
            <div class="ao-gchat-avatar" data-ao-focus-member="${esc(m.agentId === "user" ? primaryId : m.agentId)}:lead" title="Click để vào phòng ${esc(m.deptCode)}">
              <span>${m.avatar || "💬"}</span>
            </div>
            <div class="ao-gchat-bubble">
              <header class="ao-gchat-head">
                <div class="ao-gchat-who">
                  <span class="ao-gchat-dept-tag">${esc(m.deptCode)}</span>
                  <strong class="ao-gchat-handle">${esc(m.senderHandle)}</strong>
                  <span class="ao-gchat-role-pill">${esc(m.roleBadge)}</span>
                </div>
                <span class="ao-gchat-time">${esc(m.timeLabel)}</span>
              </header>
              <div class="ao-gchat-sub">${esc(m.senderTitle)} · ${esc(m.deptName)}</div>
              <div class="ao-gchat-text">${esc(m.text).replace(/\n/g, "<br/>")}</div>
              <footer class="ao-gchat-foot">
                <span class="ao-gchat-status-chip">${esc(m.statusPill)}</span>
                ${
                  m.agentId !== "user"
                    ? `<div class="ao-gchat-actions">
                         <button type="button" class="ao-gchat-mini-btn" data-ao-focus-member="${esc(m.agentId)}:lead">🔍 Vào phòng</button>
                         <button type="button" class="ao-gchat-mini-btn" data-ao-dispatch-handle="${esc(m.senderHandle)}">📨 Giao việc</button>
                       </div>`
                    : ""
                }
              </footer>
            </div>
          </article>
        `;
      })
      .join("");

    return `
      <section class="ao-gchat-panel${isCompact ? " is-in-room" : ""}" aria-label="Nhóm chat báo cáo tiến độ trực tiếp của 15 Phòng Ban">
        <header class="ao-gchat-banner">
          <div class="ao-gchat-banner-top">
            <div>
              <div class="ao-gchat-title-row">
                <span class="ao-lsb-pulse ${isRunning ? "is-running" : "is-idle"}"></span>
                <strong>💬 NHÓM CHAT TRỰC CHIẾN 15 PHÒNG BAN (92 NHÂN SỰ)</strong>
              </div>
              <small>Các Agent tự động báo cáo đang làm gì · làm đến đâu (%) · bao lâu nữa xong (ETA) &amp; bàn giao liên phòng</small>
            </div>
            <span class="ao-gchat-online-pill">🟢 92/92 Online</span>
          </div>
          <div class="ao-gchat-eta-box">
            <div class="ao-gchat-eta-row">
              <span>🎯 <b>Đang trực chiến:</b> ${prof.prop} ${esc(roster.code)} · ${esc(prof.shortTitleVi)} (${roster.headcount} NS)</span>
              <span class="ao-gchat-eta-pct">${pct}%</span>
            </div>
            <div class="ao-gchat-eta-bar"><i style="width:${Math.max(6, Math.min(100, pct))}%;"></i></div>
            <div class="ao-gchat-eta-time">⏱️ <strong>Dự kiến bao lâu nữa xong:</strong> <span>${esc(etaVi)}</span></div>
          </div>
        </header>

        <div class="ao-gchat-messages">
          ${msgsHtml}
        </div>

        <footer class="ao-gchat-composer">
          <div class="ao-gchat-quick-chips">
            <button type="button" class="ao-gchat-ask-chip" data-ao-gchat-quick="Bao lâu nữa thì xong bước hiện tại và đang làm đến đâu rồi?">⏱️ Bao lâu nữa xong?</button>
            <button type="button" class="ao-gchat-ask-chip" data-ao-gchat-quick="Báo cáo chi tiết các file đã làm xong và tiến độ % hiện tại!">📊 Báo cáo tiến độ %</button>
            <button type="button" class="ao-gchat-ask-chip" data-ao-gchat-quick="Điểm danh toàn bộ 15 Phòng Ban và 92 Nhân sự trong xưởng!">👥 Điểm danh 92 NS</button>
          </div>
          <div class="ao-gchat-input-row">
            <input type="text" id="${inputId}" class="ao-gchat-input" placeholder="Chat hỏi tiến độ trên nhóm (VD: @${esc(primaryId)}_lead bao lâu nữa xong?)…" />
            <button type="button" class="ao-gchat-send-btn" data-ao-gchat-send="${inputId}">Gửi lên Nhóm ↵</button>
            <button type="button" class="ao-gchat-mainchat-btn" data-ao-dispatch-handle="${esc(roster.lead.handle)}" title="Mở Hộp Chat Điều Phối Chính của App">📨 Hộp Chat Chính</button>
          </div>
        </footer>
      </section>
    `;
  }

  // Gather rich real-time progress lines for continuous bubbles & persona replies
  function getAgentOwnedGates(agentId, snap) {
    const gates = Array.isArray(snap?.critique_gates) ? snap.critique_gates : [];
    if (agentId === "evidence_qa") {
      return gates.filter((g) => g.critic_agent === "evidence_qa");
    }
    if (agentId === "qc") {
      return gates.filter((g) => g.phase === "qc" || g.critic_agent === "qc");
    }
    return gates.filter(
      (g) => g.maker_agent === agentId || (Array.isArray(g.co_agents) && g.co_agents.includes(agentId))
    );
  }

  function buildContinuousBubbleText(ag, snap, tick) {
    const prof = CHIBI_PROFILES[ag.id] || CHIBI_PROFILES.orchestrator;
    const ownedGates = getAgentOwnedGates(ag.id, snap);
    const liveTel = aoState.livePhaseTelemetry;

    if (ag.live_state === "working" || ag.live_state === "critiquing" || ag.live_state === "reworking") {
      if (liveTel && liveTel.byAgent && liveTel.byAgent[ag.id]) {
        const s = liveTel.byAgent[ag.id];
        return s.length > 62 ? `${s.slice(0, 60)}…` : s;
      }
      if (liveTel && liveTel.agentId === ag.id && liveTel.shortVi) {
        return liveTel.shortVi;
      }
      if (ag.id === "orchestrator" && liveTel && liveTel.shortVi) {
        return `📣 Chỉ huy: ${liveTel.shortVi}`;
      }
      const pool = [];
      if (ag.live_bubble) pool.push(ag.live_bubble);
      if (ag.status_label_vi) pool.push(`${prof.prop} ${ag.status_label_vi}`);
      ownedGates.forEach((g) => {
        if (g.gate_state === "reworking_live" || g.gate_state === "maker_working" || g.gate_state === "critic_reviewing") {
          if (g.summary_vi && !g.summary_vi.includes("Đang thực thi trực tiếp")) pool.push(g.summary_vi);
        }
      });
      if (ag.last_event && ag.last_event.summary) {
        pool.push(`⚡ ${ag.last_event.summary}`);
      }
      const unique = Array.from(new Set(pool.filter(Boolean)));
      if (!unique.length) return `${prof.prop} Đang xử lý trực tiếp…`;
      const pick = unique[tick % unique.length];
      return pick.length > 62 ? `${pick.slice(0, 60)}…` : pick;
    }

    if (ag.live_state === "done") {
      if (ag.rework_badge) return `🔄 ${ag.rework_badge}`;
      if (ag.completed_badge) return `✓ ${ag.completed_badge.slice(0, 62)}`;
      return "✓ Đã hoàn thành & bàn giao";
    }

    return ag.wait_hint_vi || `👥 ${prof.headcount || 6} nhân sự đang trực chiến sẵn sàng`;
  }

  // Build 1st-Person Interactive Reply when User Clicks any of the 92 Staff Members on #officeFloor
  function buildPersonaFocusReply(ag, snap, mode, memberKey) {
    const prof = CHIBI_PROFILES[ag.id] || CHIBI_PROFILES.orchestrator;
    const roster = getMergedDeptRoster(ag.id, snap);
    const ownedGates = getAgentOwnedGates(ag.id, snap);
    const jobTitle = snap?.selected_job?.title || "dự án hiện tại";
    const mKey = memberKey || aoState.focusedMemberKey || "lead";

    let memberObj = roster.lead;
    let roleKind = "lead";
    if (mKey === "deputy") {
      memberObj = roster.deputy;
      roleKind = "deputy";
    } else if (mKey !== "lead") {
      const foundSp = roster.specialists.find((s) => s.id === mKey || s.handle === mKey);
      if (foundSp) {
        memberObj = foundSp;
        roleKind = "specialist";
      }
    }

    if (mode === "persona") {
      return `“Chào sếp! Tôi là ${memberObj.handle} (${memberObj.title_vi}) thuộc ${roster.code} · ${prof.shortTitleVi}. Nhiệm vụ chuyên trách: ${memberObj.role_vi}”`;
    }

    if (mode === "qa") {
      const checks = (roster.deputy.checklist_vi || []).slice(0, 3).join(" · ");
      if (roleKind === "deputy") {
        return `“Báo cáo sếp! Với tư cách Tổ phó ${roster.deputy.handle}, tôi trực tiếp rà checklist ${roster.specialists.length}/${roster.specialists.length} lô chuyên viên (${checks || "Kiểm định nội bộ 100%"}) trước khi trình Tổ trưởng ${roster.lead.handle} ký duyệt!”`;
      }
      if (roleKind === "specialist") {
        return `“Lô ${memberObj.batch_id} (${memberObj.items_label}) của tôi (${memberObj.handle}) xuất ra ${memberObj.artifact_key}, bàn giao từ ${memberObj.input_from} sang ${memberObj.output_to} và luôn đối chiếu chặt với Tổ phó ${roster.deputy.handle}!”`;
      }
      const reworked = ownedGates.filter((g) => g.rework_triggered || g.gate_state === "reworking_live");
      if (reworked.length > 0) {
        const g = reworked[0];
        return `“Ở khâu ${g.label_vi}, đội ${roster.headcount} nhân sự của tôi đã phối hợp cùng @${g.critic_agent} tự động chỉnh sửa ${g.rework_count || 1} điểm (${g.badge_vi}) ngay trên đĩa!”`;
      }
      return `“Tổ trưởng ${roster.lead.handle} cùng Tổ phó ${roster.deputy.handle} và ${roster.specialists.length} Chuyên viên luôn kiểm định chéo 100% đầu ra cùng @evidence_qa trước khi chuyển phase!”`;
    }

    // Default mode === "progress"
    if (roleKind === "specialist") {
      return `“Báo cáo sếp! Tôi là ${memberObj.handle} (${memberObj.title_vi}) — phụ trách ${memberObj.batch_id} (${memberObj.items_label}, luồng ${memberObj.worker_thread}). Trạng thái hiện tại: ${memberObj.finding_vi}”`;
    }
    if (roleKind === "deputy") {
      return `“Báo cáo sếp! Tôi là Tổ phó ${roster.deputy.handle} (${roster.deputy.title_vi}). Tôi đang giám sát đồng thời ${roster.specialists.length} lô song song của phòng (${roster.specialists.map((s) => s.shortTag).join(", ")}) để hợp nhất kết quả cho «${jobTitle.slice(0, 44)}»!”`;
    }
    if (ag.live_state === "working" || ag.live_state === "critiquing" || ag.live_state === "reworking") {
      const bubble = ag.live_bubble || ag.status_label_vi || "Đang xử lý trực tiếp";
      return `“Báo cáo sếp! Tổ trưởng ${roster.lead.handle} cùng Tổ phó ${roster.deputy.handle} và ${roster.specialists.length} Chuyên viên đang trực chiến tại cụm bàn ${roster.code}: ${bubble}.”`;
    }
    return `“Báo cáo sếp! Cụm bàn ${roster.code} (${roster.headcount} nhân sự: 1 Tổ trưởng ${roster.lead.handle} · 1 Tổ phó ${roster.deputy.handle} · ${roster.specialists.length} Chuyên viên) đang trực chiến đầy đủ, sẵn sàng chia ${roster.specialists.length} lô chạy song song tốc độ ${roster.speedup_factor}!”`;
  }

  const TOON_ROOM_THEMES = {
    orchestrator: { rug: "#fee2e2", rugBorder: "#f87171", wall: "#fffbeb", gizmo: "📣", gizmoAnim: "pulse", fx: "✨" },
    radar: { rug: "#ccfbf1", rugBorder: "#2dd4bf", wall: "#f0fdfa", gizmo: "📡", gizmoAnim: "spin", fx: "🛰️" },
    research: { rug: "#fef3c7", rugBorder: "#fbbf24", wall: "#fffbeb", gizmo: "🔎", gizmoAnim: "swing", fx: "💡" },
    script: { rug: "#e0e7ff", rugBorder: "#818cf8", wall: "#f5f3ff", gizmo: "🖋️", gizmoAnim: "float", fx: "📝" },
    voice: { rug: "#fce7f3", rugBorder: "#f472b6", wall: "#fdf2f8", gizmo: "🎙️", gizmoAnim: "pulse", fx: "🎵" },
    visuals: { rug: "#dbeafe", rugBorder: "#60a5fa", wall: "#eff6ff", gizmo: "🎬", gizmoAnim: "snap", fx: "🎞️" },
    footage: { rug: "#e0f2fe", rugBorder: "#38bdf8", wall: "#f0f9ff", gizmo: "🎞️", gizmoAnim: "spin", fx: "👁️" },
    ai_visual: { rug: "#f3e8ff", rugBorder: "#c084fc", wall: "#faf5ff", gizmo: "🎨", gizmoAnim: "float", fx: "✨" },
    vox: { rug: "#d1fae5", rugBorder: "#34d399", wall: "#ecfdf5", gizmo: "🗺️", gizmoAnim: "spin", fx: "✂️" },
    edit: { rug: "#ffedd5", rugBorder: "#fb923c", wall: "#fff7ed", gizmo: "✂️", gizmoAnim: "snap", fx: "🎶" },
    seo: { rug: "#ffe4e6", rugBorder: "#fb7185", wall: "#fff1f2", gizmo: "🚀", gizmoAnim: "float", fx: "🔥" },
    evidence_qa: { rug: "#fef9c3", rugBorder: "#facc15", wall: "#fefce8", gizmo: "⚖️", gizmoAnim: "swing", fx: "🔍" },
    qc: { rug: "#ccfbf1", rugBorder: "#14b8a6", wall: "#f0fdfa", gizmo: "🛡️", gizmoAnim: "pulse", fx: "✅" },
    dev: { rug: "#e2e8f0", rugBorder: "#94a3b8", wall: "#f8fafc", gizmo: "⚙️", gizmoAnim: "spin", fx: "⚡" },
    debug: { rug: "#dcfce7", rugBorder: "#4ade80", wall: "#f0fdf4", gizmo: "🩺", gizmoAnim: "pulse", fx: "💊" },
  };

  function buildPodMemberSeatHtml(agentId, roleType, member, idx) {
    const roleCls = roleType === "lead" ? "role-lead" : roleType === "deputy" ? "role-deputy" : "role-specialist";
    const mKey = roleType === "lead" ? "lead" : roleType === "deputy" ? "deputy" : member.id;
    const isCmd = roleType === "lead" || roleType === "deputy";
    const theme = TOON_ROOM_THEMES[agentId] || TOON_ROOM_THEMES.orchestrator;
    const roleBadgeTxt =
      roleType === "lead"
        ? "👑 TRƯỞNG PHÒNG (DEPARTMENT LEAD)"
        : roleType === "deputy"
        ? "🛡️ PHÓ PHÒNG (QUALITY DEPUTY)"
        : `⚡ CHUYÊN VIÊN ${member.batch_id || `LÔ #${idx + 1}`} (${member.items_label || "Parallel"})`;

    const seatMetaHtml = isCmd
      ? `<div class="ao-cmd-seat-meta">
           <span class="ao-member-tag">${roleType === "lead" ? "👑 Trưởng" : "🛡️ Phó"}</span>
           <div class="ao-toon-exec-desk">
             <span class="ao-toon-laptop"><i></i></span>
             <span class="ao-toon-mug">☕</span>
           </div>
         </div>`
      : `<div class="ao-toon-spec-desk">
           <span class="ao-toon-laptop"><i></i></span>
           <span class="ao-member-tag">${esc(member.shortTag)}</span>
         </div>`;

    return `
      <div class="ao-pod-member ao-toon-seat ${roleCls}"
           id="aoMember-${esc(agentId)}-${esc(mKey)}"
           data-ao-agent="${esc(agentId)}"
           data-ao-member-key="${esc(mKey)}"
           data-ao-member-handle="${esc(member.handle)}"
           data-ao-tip-role="${esc(roleBadgeTxt)}"
           data-ao-tip-title="${esc(member.title_vi)}"
           data-ao-tip-duty="${esc(member.role_vi)}"
           data-ao-tip-batch="${esc(roleType === "specialist" ? `🎯 ${member.batch_id} · ${member.items_label} · 🧵 ${member.worker_thread}` : member.live_badge_vi || "Trực chiến 100%")}">
        <div class="ao-member-chibi-wrap">
          <span class="ao-toon-char-sparkle" style="animation-delay:${((idx * 0.43) % 1.8).toFixed(2)}s;">${isCmd ? (roleType === "lead" ? "👑" : "🛡️") : theme.fx}</span>
          ${buildMemberChibiSvg(agentId, roleType, idx)}
          <span class="ao-member-mon" title="Màn hình hoạt hình của ${esc(member.handle)}">
            <i class="ao-typing-bar"></i><i class="ao-typing-bar"></i>
          </span>
          <span class="ao-member-led"></span>
        </div>
        ${seatMetaHtml}
      </div>
    `;
  }

  function buildTeamPodStationHtml(agentId, p, snap) {
    const roster = getMergedDeptRoster(agentId, snap);
    const isVox = agentId === "vox";
    const specColsCls = roster.specialists.length >= 6 ? "cols-6" : "cols-4";
    const podW = p.podW || (isVox ? 274 : 262);
    const numCode = String(p.deptCode || "DEPT-00").replace("DEPT-", "");
    const theme = TOON_ROOM_THEMES[agentId] || TOON_ROOM_THEMES.orchestrator;

    const specsSeatsHtml = roster.specialists
      .map((sp, idx) => buildPodMemberSeatHtml(agentId, "specialist", sp, idx))
      .join("");

    return `
      <div class="ao-station ao-team-pod ao-25d-glass-room ao-toon-room st-standby${isVox ? " is-vox-pod" : ""}"
           id="aoStation-${esc(agentId)}"
           data-ao-agent="${esc(agentId)}"
           data-ao-zone="${esc(p.zone)}"
           data-ao-subzone="${esc(p.subZone || p.zone)}"
           style="left:${p.hx}px;top:${p.hy}px;width:${podW}px;--pod-accent:${esc(p.hatColor || "#38bdf8")};--room-rug:${theme.rug};--room-rug-border:${theme.rugBorder};--room-wall:${theme.wall};">
        <div class="ao-chibi-bubble" id="aoBubble-${esc(agentId)}" hidden></div>
        <div class="ao-pod-header ao-toon-signboard" data-ao-agent="${esc(agentId)}">
          <span class="ao-pod-title-txt">
            <b class="ao-pod-num">${esc(numCode)}</b>
            <span class="ao-toon-room-gizmo gizmo-${theme.gizmoAnim}">${theme.gizmo}</span>
            ${esc(p.shortTitleVi || agentId)}
          </span>
          <span class="ao-pod-count-badge" id="aoPodBadge-${esc(agentId)}" title="Click để vào Phim Trường Phòng Hoạt Hình">${roster.headcount} NS</span>
        </div>
        <div class="ao-toon-room-rug">
          <div class="ao-pod-command-row">
            ${buildPodMemberSeatHtml(agentId, "lead", roster.lead, 0)}
            ${buildPodMemberSeatHtml(agentId, "deputy", roster.deputy, 0)}
          </div>
          <div class="ao-pod-spec-row ${specColsCls}">
            ${specsSeatsHtml}
          </div>
        </div>
        <span class="ao-toon-corner-plant" title="Cây xanh studio">🪴</span>
        <div class="ao-pod-floor-led"></div>
      </div>
    `;
  }

  // Ensure Animated Cartoon Movie Studio Stage DOM (#officeFloor / #aoChibiViewport) is mounted with 15 Cartoon Rooms × 92 Staff + 12 Roamers!
  function ensureChibiStageMounted(host) {
    if (aoState.stageMounted && host.querySelector("#aoChibiViewport") && host.querySelector(".ao-team-pod")) return;

    const stationsHtml = Object.entries(CHIBI_PROFILES)
      .map(([id, p]) => buildTeamPodStationHtml(id, p, aoState.snapshot))
      .join("");

    // 10 Roaming Cartoon Couriers & Directors walking dynamically across all corridors
    const liaisonsHtml = LIAISON_AGENTS.map((id, idx) => {
      const p = CHIBI_PROFILES[id] || CHIBI_PROFILES.orchestrator;
      const spot = LOUNGE_SPOTS[(idx * 2) % LOUNGE_SPOTS.length];
      const nextSpot = LOUNGE_SPOTS[(idx * 2 + 3) % LOUNGE_SPOTS.length];
      if (!aoState.actors[id]) {
        aoState.actors[id] = {
          x: spot.x,
          y: spot.y,
          tx: nextSpot.x,
          ty: nextSpot.y,
          facingLeft: nextSpot.x < spot.x,
          walking: true,
          spotId: nextSpot.id,
          nextRoamAt: performance.now() + 600 + idx * 750,
          fx: spot.fx,
          tag: spot.tag,
        };
      }
      return `
        <div class="ao-chibi-actor ao-lounge-liaison is-walking state-working"
             id="aoActor-${esc(id)}"
             data-ao-agent="${esc(id)}"
             data-ao-member-key="lead"
             style="transform:translate3d(${aoState.actors[id].x}px,${aoState.actors[id].y}px,0);">
          <div class="ao-roamer-bubble" id="aoRoamerBub-${esc(id)}">${esc(spot.tag)}</div>
          <div class="ao-chibi-shadow"></div>
          <div class="ao-chibi-sprite">
            ${buildMemberChibiSvg(id, idx % 2 === 0 ? "lead" : "specialist", idx)}
            <span class="ao-chibi-fx" id="aoFx-${esc(id)}">${spot.fx}</span>
            <span class="ao-walk-dust">💨</span>
          </div>
          <span class="ao-chibi-nametag">${esc(p.deptCode)} · ${esc(p.shortTitleVi)}</span>
        </div>
      `;
    }).join("");

    // 2 Cute Animated Studio Mascots (Cat Director & Corgi Courier) trotting around the studio!
    const petsHtml = STUDIO_PETS.map((pet, idx) => {
      const spot = LOUNGE_SPOTS[(idx * 5 + 1) % LOUNGE_SPOTS.length];
      const nextSpot = LOUNGE_SPOTS[(idx * 5 + 4) % LOUNGE_SPOTS.length];
      if (!aoState.actors[pet.id]) {
        aoState.actors[pet.id] = {
          x: pet.x,
          y: pet.y,
          tx: nextSpot.x,
          ty: nextSpot.y,
          facingLeft: nextSpot.x < pet.x,
          walking: true,
          spotId: nextSpot.id,
          nextRoamAt: performance.now() + 500 + idx * 900,
          fx: pet.fx,
          tag: pet.chat,
          isPet: true,
        };
      }
      return `
        <div class="ao-chibi-actor ao-lounge-liaison ao-studio-pet is-walking"
             id="aoActor-${esc(pet.id)}"
             data-ao-agent="vox"
             data-ao-member-key="lead"
             style="transform:translate3d(${aoState.actors[pet.id].x}px,${aoState.actors[pet.id].y}px,0);">
          <div class="ao-roamer-bubble is-pet-bubble" id="aoRoamerBub-${esc(pet.id)}">${esc(pet.chat)}</div>
          <div class="ao-chibi-sprite">
            ${buildStudioPetSvg(pet.id)}
            <span class="ao-chibi-fx" id="aoFx-${esc(pet.id)}">${pet.fx}</span>
          </div>
          <span class="ao-chibi-nametag pet-tag">${esc(pet.nameVi)}</span>
        </div>
      `;
    }).join("");

    // 3 Animated Flying Paper Airplanes & Film Reels zipping between departments (active on work/hover)!
    const flyingCouriersHtml = `
      <div class="ao-flying-couriers-layer" aria-hidden="true">
        <span class="ao-flying-parcel fp-1">✈️ <i>Kịch bản</i></span>
        <span class="ao-flying-parcel fp-2">🗺️ <i>VOX 12fps</i></span>
        <span class="ao-flying-parcel fp-3">🎬 <i>Master MP4</i></span>
      </div>
    `;

    // Animated Cartoon Footstep Stepping Stones between the 5 Columns on all 3 Wings
    const colGaps = [294, 574, 855, 1140];
    const rowYs = [118, 410, 628];
    const flowConnectorsHtml = rowYs
      .map((ry, rIdx) =>
        colGaps
          .map(
            (gx, cIdx) =>
              `<div class="ao-floor-flow-badge${rIdx === 1 && (cIdx === 1 || cIdx === 2) ? " is-parallel" : ""}" style="left:${gx}px;top:${ry}px;" title="Luồng chuyển hồ sơ hoạt hình giữa các Phòng Ban">${
                rIdx === 1 && (cIdx === 1 || cIdx === 2) ? "⚡" : "➔"
              }</div>`
          )
          .join("")
      )
      .join("");

    host.innerHTML = `
      <div class="ao-chibi-viewport is-cartoon-movie-studio${aoState.perspective3d ? " is-perspective-25d" : ""}" id="aoChibiViewport" data-office-floor-stage="true">
        <div class="ao-chibi-world ao-toon-studio-floor" id="officeFloor" data-ao-world="aoChibiWorld">
          <!-- SUNLIGHT RAYS & FLOATING CARTOON SPARKLES -->
          <div class="ao-toon-sunbeams" aria-hidden="true">
            <i class="sunbeam sb-1"></i>
            <i class="sunbeam sb-2"></i>
            <i class="sunbeam sb-3"></i>
          </div>

          <!-- KHU A (TẦNG BẮC): KHỐI CHỈ HUY & NỘI DUNG (DEPT-00..04 · 30 NS) -->
          <div class="ao-zone ao-zone-north-left" data-zone-box="north">
            <span class="ao-zone-label">🏛️ KHỐI CHỈ HUY &amp; TÌNH BÁO RADAR · 00–01</span>
          </div>
          <div class="ao-zone ao-zone-north-right" data-zone-box="north">
            <span class="ao-zone-label">🖋️ KHỐI HỒ SƠ · BIÊN KỊCH &amp; PHÒNG THU · 02–04</span>
            <div class="ao-vocal-booth">
              <span class="ao-on-air-sign" id="aoOnAirSign">● STUDIO VOICE</span>
            </div>
          </div>

          <!-- ĐẠI LỘ HOẠT HÌNH TRUNG TÂM (BUSTLING CARTOON STUDIO BOULEVARD) -->
          <div class="ao-zone ao-zone-lounge ao-toon-boulevard" data-zone-box="lounge">
            <span class="ao-zone-label">🎬 ĐẠI LỘ PHIM TRƯỜNG HOẠT HÌNH · CAFE &amp; GIAO LƯU LIÊN PHÒNG</span>
          </div>

          <!-- KHU B (TẦNG TRUNG): KHỐI SẢN XUẤT HÌNH ẢNH & ĐỒ HỌA VOX (DEPT-05..09 · 32 NS) -->
          <div class="ao-zone ao-zone-central" data-zone-box="central">
            <span class="ao-zone-label">🎨 KHỐI HÌNH ẢNH · ĐỒ HỌA VOX (8 NS ⭐) &amp; DỰNG REMOTION · 05–09</span>
          </div>

          <!-- KHU C (TẦNG NAM): KHỐI PHÁT HÀNH, PHÁP Y QA & KỸ THUẬT (DEPT-10..14 · 30 NS) -->
          <div class="ao-zone ao-zone-south-left" data-zone-box="south">
            <span class="ao-zone-label">🚀 KHỐI PHÁT HÀNH · PHÁP Y QA &amp; DUYỆT MASTER · 10–12</span>
          </div>
          <div class="ao-zone ao-zone-south-right" data-zone-box="south">
            <span class="ao-zone-label">⚙️ KHỐI KỸ THUẬT LÕI &amp; CHẨN ĐOÁN · 13–14</span>
          </div>

          <!-- Illustrated Cartoon Lounge Props in the Central Boulevard -->
          <div class="ao-prop ao-coffee-bar ao-toon-prop-card">
            <span class="ao-steam">♨️</span>
            <span class="ao-toon-prop-icon">☕🥐</span>
            <div class="ao-toon-prop-text">
              <strong>Quầy Cà Phê Hoạt Hình</strong>
              <small>Espresso &amp; Bánh nóng</small>
            </div>
          </div>
          <div class="ao-prop ao-sofa-box ao-toon-prop-card">
            <span class="ao-toon-prop-icon">🛋️💬</span>
            <div class="ao-toon-prop-text">
              <strong>Sofa Đạo Diễn</strong>
              <small>Thảo luận kịch bản</small>
            </div>
          </div>
          <div class="ao-prop ao-board-box ao-toon-cinema-board">
            <div class="ao-board-title" id="aoLiveBoardTitle">🎬 XƯỞNG PHIM HOẠT HÌNH COFI · 15 PHÒNG BAN · 92 NHÂN SỰ</div>
            <div class="ao-board-bar"><div class="ao-board-fill" id="aoLiveBoardFill" style="width:100%;"></div></div>
            <div class="ao-board-sub" id="aoLiveBoardSub">Mọi nhân vật đang làm việc sống động · Bấm vào Phòng bất kỳ để vào Cảnh Quay Nội Thất!</div>
          </div>
          <div class="ao-prop ao-plant-box ao-toon-prop-card" style="left:1158px;">
            <span class="ao-toon-prop-icon ao-sway-plant">🌴🪴</span>
            <div class="ao-toon-prop-text">
              <strong>Vườn Xanh Studio</strong>
              <small>Góc thư giãn sáng tạo</small>
            </div>
          </div>

          ${flowConnectorsHtml}
          ${flyingCouriersHtml}
          <svg class="ao-chibi-links" id="aoChibiLinksSvg" viewBox="0 0 ${STAGE_W} ${STAGE_H}"></svg>
          ${stationsHtml}
          ${liaisonsHtml}
          ${petsHtml}
        </div>
        <div class="ao-floor-member-tooltip" id="aoFloorMemberTooltip" hidden></div>
        <div class="ao-focus-reply-card" id="aoFocusReplyCard" hidden></div>
      </div>
    `;

    const vp = document.getElementById("aoChibiViewport");
    if (vp) {
      vp.addEventListener("contextmenu", (ev) => {
        ev.preventDefault();
        if (aoState.focusedAgentId || aoState.floorZoneFilter !== "all") {
          aoState.floorZoneFilter = "all";
          document.querySelectorAll("[data-ao-zone-filter]").forEach((b) => {
            b.classList.toggle("active", b.getAttribute("data-ao-zone-filter") === "all");
          });
          exitChibiFocus();
          syncCameraTransform();
        }
      });

      vp.addEventListener("mousemove", (ev) => {
        const tip = document.getElementById("aoFloorMemberTooltip");
        if (!tip) return;
        const memberEl = ev.target.closest(".ao-pod-member[data-ao-member-handle]");
        if (!memberEl) {
          tip.hidden = true;
          return;
        }
        const handle = memberEl.getAttribute("data-ao-member-handle") || "";
        const roleTxt = memberEl.getAttribute("data-ao-tip-role") || "";
        const titleTxt = memberEl.getAttribute("data-ao-tip-title") || "";
        const dutyTxt = memberEl.getAttribute("data-ao-tip-duty") || "";
        const batchTxt = memberEl.getAttribute("data-ao-tip-batch") || "";
        tip.innerHTML = `
          <div class="ao-tip-head">
            <span class="ao-tip-role">${esc(roleTxt)}</span>
            <code>${esc(handle)}</code>
          </div>
          <strong class="ao-tip-title">${esc(titleTxt)}</strong>
          <p class="ao-tip-duty">${esc(dutyTxt)}</p>
          <div class="ao-tip-foot">${esc(batchTxt)} · <em>Click để vào Phòng 2.5D</em></div>
        `;
        tip.hidden = false;
        const vRect = vp.getBoundingClientRect();
        let lx = ev.clientX - vRect.left + 14;
        let ly = ev.clientY - vRect.top - tip.offsetHeight - 12;
        if (lx + 290 > vRect.width) lx = Math.max(8, vRect.width - 295);
        if (ly < 8) ly = ev.clientY - vRect.top + 18;
        tip.style.transform = `translate3d(${Math.round(lx)}px, ${Math.round(ly)}px, 0)`;
      });

      vp.addEventListener("mouseleave", () => {
        const tip = document.getElementById("aoFloorMemberTooltip");
        if (tip) tip.hidden = true;
      });
    }

    aoState.stageMounted = true;
    syncCameraTransform();
  }

  function computeWorldScale() {
    const vp = document.getElementById("aoChibiViewport");
    if (!vp) return 1;
    const rect = vp.getBoundingClientRect();
    if (!rect.width) return 1;
    const sw = (rect.width - 18) / STAGE_W;
    const sh = rect.height > 100 ? (rect.height - 18) / STAGE_H : sw;
    return Math.min(1.06, Math.max(0.42, Math.min(sw, sh)));
  }

  const ZONE_CAMERA_TARGETS = {
    north: { cx: 720, cy: 118, z: 1.24 },
    central: { cx: 720, cy: 410, z: 1.24 },
    south: { cx: 720, cy: 628, z: 1.24 },
    direction: { cx: 294, cy: 118, z: 1.48 },
    editorial: { cx: 996, cy: 118, z: 1.32 },
    cinema: { cx: 720, cy: 410, z: 1.24 },
    qa: { cx: 856, cy: 628, z: 1.32 },
  };

  function resolvePrimaryWorkingDepartment(snap) {
    if (!snap) return null;
    if (aoState.parallelWaveActive && aoState.parallelWaveDept && CHIBI_PROFILES[aoState.parallelWaveDept]) {
      return aoState.parallelWaveDept;
    }
    const lpr = snap.live_phase_report;
    if (lpr && lpr.is_running && lpr.primary_agent_id && CHIBI_PROFILES[lpr.primary_agent_id]) {
      return lpr.primary_agent_id;
    }
    const agents = Array.isArray(snap.agents) ? snap.agents : [];
    const curPhase = String(snap.selected_job?.current_phase || "").trim().toLowerCase();
    const phaseToDept = {
      plan: "script",
      research: "research",
      script: "script",
      voice: "voice",
      visuals: "visuals",
      footage: "footage",
      ai_visual: "ai_visual",
      vox: "vox",
      edit: "edit",
      seo: "seo",
      qc: "qc",
    };

    const reworkingAg = agents.find((a) => a.live_state === "reworking" && a.id !== "orchestrator");
    if (reworkingAg) return reworkingAg.id;

    if (aoState.livePhaseTelemetry && aoState.livePhaseTelemetry.agentId && CHIBI_PROFILES[aoState.livePhaseTelemetry.agentId]) {
      return aoState.livePhaseTelemetry.agentId;
    }

    if (curPhase && phaseToDept[curPhase]) {
      const mappedId = phaseToDept[curPhase];
      const mappedAg = agents.find((a) => a.id === mappedId);
      if (mappedAg && ["working", "reworking", "critiquing"].includes(mappedAg.live_state)) {
        return mappedId;
      }
    }

    const activeNonOrch = agents.filter(
      (a) => a.id !== "orchestrator" && ["working", "reworking", "critiquing"].includes(a.live_state)
    );
    if (activeNonOrch.length > 0 && activeNonOrch.length < 15) {
      return activeNonOrch[0].id;
    }
    return null;
  }

  function buildSpecialistWorkScreenHtml(agentId, sp, idx, isWorking) {
    const liveCls = isWorking ? " is-screen-live" : "";
    const art = esc(sp.artifact_key || "output.json");
    const laneNum = idx + 1;

    let canvasInner = "";
    if (agentId === "vox") {
      if (idx === 0) {
        canvasInner = `
          <div class="ao-ws-row"><span class="ao-ws-tag">KR VOICE</span><code>clauses[0..2]</code></div>
          <div class="ao-ws-wave"><i></i><i></i><i></i><i></i><i></i><i></i><i></i></div>
          <div class="ao-ws-chip-row"><span>t1: Mở</span><span>➔</span><span>t2: Xoáy</span><span>➔</span><span class="hi">vox_prompt</span></div>
        `;
      } else if (idx === 1) {
        canvasInner = `
          <div class="ao-ws-desk-mock">
            <span class="ao-ws-paper">#E4DDCF Desk</span>
            <span class="ao-ws-blackcard">&lt;BlackCard&gt;</span>
            <span class="ao-ws-svg-draw">📐 SVG Cutaway</span>
          </div>
        `;
      } else if (idx === 2) {
        canvasInner = `
          <div class="ao-ws-rgba-grid">
            <span class="ao-ws-sticker">✂️ &lt;DieCutSticker&gt;</span>
            <span class="ao-ws-rgba-pill">RGBA Alpha 100%</span>
          </div>
        `;
      } else if (idx === 3) {
        canvasInner = `
          <div class="ao-ws-row"><span class="ao-ws-tag">30FPS CAM</span><code>&lt;World cam&gt;</code></div>
          <div class="ao-ws-cam-curve"><span>🎥 Δx,Δy,scale</span><b class="hi">1/12 Motion Verb</b></div>
        `;
      } else if (idx === 4) {
        canvasInner = `
          <div class="ao-ws-row"><span class="ao-ws-tag">12FPS STEP12</span><code>t1 ➔ t2 ➔ t3</code></div>
          <div class="ao-ws-timeline-3p"><span class="p1">15%</span><span class="p2">50%</span><span class="p3">85%</span></div>
        `;
      } else {
        canvasInner = `
          <div class="ao-ws-grid100">
            <span class="ao-ws-redcircle">⭕ RedCircle 0.0px</span>
            <span class="ao-ws-gis">🛰️ 3D GIS OSRM</span>
          </div>
        `;
      }
    } else if (agentId === "footage") {
      if (idx === 0) {
        canvasInner = `
          <div class="ao-ws-row"><span class="ao-ws-tag">CCTV RAW</span><code>yt-dlp / Archive</code></div>
          <div class="ao-ws-bars"><i style="width:92%"></i><i style="width:78%"></i></div>
        `;
      } else if (idx === 1) {
        canvasInner = `
          <div class="ao-ws-grid100">
            <span>🖼️ STORYBOARD.jpg</span>
            <span class="hi">📏 Lưới 100px</span>
          </div>
        `;
      } else if (idx === 2) {
        canvasInner = `
          <div class="ao-ws-3frame">
            <span>15% ✓</span><span>50% ✓</span><span>85% ✓</span>
          </div>
          <div class="ao-ws-sub">👁️ Eye-Verified · Khớp thoại</div>
        `;
      } else {
        canvasInner = `
          <div class="ao-ws-crop-box">
            <span>✂️ crop=W:H:X:Y</span>
            <b class="hi">0% Logo / Phụ đề</b>
          </div>
        `;
      }
    } else if (agentId === "voice") {
      canvasInner = `
        <div class="ao-ws-wave"><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i></div>
        <div class="ao-ws-chip-row"><span>🎙️ GPU TTS</span><span>·</span><span class="hi">${idx === 2 ? "SRT Word-Sync" : idx === 3 ? "-16.0 LUFS" : "Prosody"}</span></div>
      `;
    } else if (agentId === "ai_visual") {
      canvasInner = `
        <div class="ao-ws-ai-frame">
          <span>🎨 16:9 Chiaroscuro</span>
          <small class="hi">Minh họa tái dựng · Góc kín 4D</small>
        </div>
      `;
    } else if (agentId === "edit") {
      canvasInner = `
        <div class="ao-ws-nle-tracks">
          <i class="tr-v">FTG + VOX + AI</i>
          <i class="tr-a">BGM Story-Arc · Crossfade 3s</i>
          <i class="tr-s">Motion-Bound SFX (offsetFrames)</i>
        </div>
      `;
    } else if (agentId === "evidence_qa" || agentId === "qc") {
      canvasInner = `
        <div class="ao-ws-3frame">
          <span>Gate #${laneNum}</span><span class="hi">✓ PASS 100%</span>
        </div>
        <div class="ao-ws-sub">⚖️ Soi mắt 3-Frame &amp; AST Gate</div>
      `;
    } else {
      canvasInner = `
        <div class="ao-ws-row"><span class="ao-ws-tag">LANE #${laneNum}</span><code>${esc(sp.batch_id)}</code></div>
        <div class="ao-ws-bars"><i style="width:${Math.max(45, Number(sp.progress_pct || 100))}%"></i><i style="width:84%"></i></div>
        <div class="ao-ws-sub">🎯 ${esc(sp.items_label)}</div>
      `;
    }

    return `
      <div class="ao-rz-workscreen${liveCls}">
        <div class="ao-rz-ws-top">
          <span class="ao-rz-ws-dots"><i></i><i></i><i></i></span>
          <code class="ao-rz-ws-file">${art}</code>
          <span class="ao-rz-ws-live">${isWorking ? "● LIVE" : "● READY"}</span>
        </div>
        <div class="ao-rz-ws-canvas">
          ${canvasInner}
        </div>
      </div>
    `;
  }

  function syncCameraTransform() {
    const vp = document.getElementById("aoChibiViewport");
    const world = document.getElementById("officeFloor") || document.getElementById("aoChibiWorld");
    if (!vp || !world) return;

    const baseScale = computeWorldScale();
    const vRect = vp.getBoundingClientRect();
    const vw = vRect.width || STAGE_W;
    const vh = vRect.height || STAGE_H;

    vp.classList.toggle("is-perspective-25d", Boolean(aoState.perspective3d));

    // Highlight or dim pods by zone filter
    const zf = aoState.floorZoneFilter || "all";
    world.querySelectorAll(".ao-team-pod").forEach((pod) => {
      const pz = pod.getAttribute("data-ao-zone") || "";
      const subz = pod.getAttribute("data-ao-subzone") || "";
      const match = zf === "all" || pz === zf || subz === zf;
      pod.classList.toggle("is-zone-dimmed", !match);
    });

    if (!aoState.focusedAgentId) {
      vp.classList.remove("has-focus");
      if (zf !== "all" && ZONE_CAMERA_TARGETS[zf]) {
        const zt = ZONE_CAMERA_TARGETS[zf];
        const zoom = Math.min(1.52, baseScale * zt.z);
        let tx = vw / 2 - zt.cx * zoom;
        let ty = vh / 2 - zt.cy * zoom;
        tx = Math.min(20, Math.max(vw - STAGE_W * zoom - 20, tx));
        ty = Math.min(20, Math.max(vh - STAGE_H * zoom - 20, ty));
        const tilt = aoState.perspective3d ? " perspective(1750px) rotateX(15deg)" : "";
        world.style.transform = `translate3d(${tx.toFixed(1)}px, ${ty.toFixed(1)}px, 0) scale(${zoom.toFixed(4)})${tilt}`;
        return;
      }
      if (aoState.perspective3d) {
        const isoScale = baseScale * 0.96;
        const ox = Math.max(0, (vw - STAGE_W * isoScale) / 2);
        const oy = Math.max(2, (vh - STAGE_H * isoScale) / 2 - 6);
        world.style.transform = `perspective(1750px) translate3d(${ox.toFixed(1)}px, ${oy.toFixed(1)}px, 0) scale(${isoScale.toFixed(4)}) rotateX(17deg)`;
      } else {
        const ox = Math.max(0, (vw - STAGE_W * baseScale) / 2);
        const oy = Math.max(0, (vh - STAGE_H * baseScale) / 2);
        world.style.transform = `translate3d(${ox.toFixed(1)}px, ${oy.toFixed(1)}px, 0) scale(${baseScale.toFixed(4)})`;
      }
      return;
    }

    // Zoom camera smoothly directly into the focused Room Pod on #officeFloor
    vp.classList.add("has-focus");
    const prof = CHIBI_PROFILES[aoState.focusedAgentId] || CHIBI_PROFILES.orchestrator;
    const ax = prof.hx;
    const ay = prof.hy;
    const zoom = Math.min(2.25, Math.max(1.55, baseScale * 1.95));
    let tx = vw / 2 - ax * zoom;
    let ty = vh * 0.45 - ay * zoom;
    const minTx = vw - STAGE_W * zoom - 60;
    const minTy = vh - STAGE_H * zoom - 120;
    tx = Math.min(60, Math.max(minTx, tx));
    ty = Math.min(60, Math.max(minTy, ty));
    world.style.transform = `translate3d(${tx.toFixed(1)}px, ${ty.toFixed(1)}px, 0) scale(${zoom.toFixed(4)})`;
  }

  function focusChibiAgent(agentId, memberKey, isAutoZoom) {
    if (!agentId || !CHIBI_PROFILES[agentId]) return;
    const changedRoom = aoState.focusedAgentId !== agentId;
    aoState.focusedAgentId = agentId;
    aoState.selectedAgentId = agentId;
    aoState.focusedMemberKey = memberKey || aoState.focusedMemberKey || "lead";
    aoState.focusAskMode = "progress";
    if (!isAutoZoom) {
      aoState.manualOverviewLock = false;
      aoState.manualZoomOutKey = "";
    }
    if (changedRoom) {
      playStudioSound("focus");
    }

    document.querySelectorAll(".ao-team-pod, .ao-chibi-actor").forEach((el) => {
      el.classList.toggle("is-focused", el.getAttribute("data-ao-agent") === agentId);
    });
    document.querySelectorAll(".ao-pod-member").forEach((el) => {
      const match =
        el.getAttribute("data-ao-agent") === agentId &&
        el.getAttribute("data-ao-member-key") === aoState.focusedMemberKey;
      el.classList.toggle("is-member-focused", match);
    });
    syncCameraTransform();
    renderFocusReplyOverlay();
    if (aoState.snapshot && changedRoom) renderInspector(aoState.snapshot);
  }

  function exitChibiFocus() {
    aoState.focusedAgentId = null;
    aoState.manualOverviewLock = true;
    aoState._lastFocusSig = "";
    if (aoState.lastAutoZoomKey) {
      aoState.manualZoomOutKey = aoState.lastAutoZoomKey;
    }
    playStudioSound("zoomout");
    document.querySelectorAll(".ao-team-pod.is-focused, .ao-chibi-actor.is-focused").forEach((el) =>
      el.classList.remove("is-focused")
    );
    document.querySelectorAll(".ao-pod-member.is-member-focused").forEach((el) =>
      el.classList.remove("is-member-focused")
    );
    const vp = document.getElementById("aoChibiViewport");
    if (vp) vp.classList.remove("has-focus");
    const card = document.getElementById("aoFocusReplyCard");
    if (card) {
      card.hidden = true;
      card.setAttribute("hidden", "hidden");
      card.style.display = "none";
      card.className = "ao-focus-reply-card";
      card.innerHTML = "";
    }
    syncCameraTransform();
  }

  // Animated Cartoon Movie Set Interior (#aoFocusReplyCard) — With Real-Time Progress & Concrete Work Report
  function renderFocusReplyOverlay() {
    const card = document.getElementById("aoFocusReplyCard");
    if (!card) return;
    if (!aoState.focusedAgentId) {
      aoState._lastFocusSig = "";
      card.hidden = true;
      card.setAttribute("hidden", "hidden");
      card.style.display = "none";
      card.innerHTML = "";
      return;
    }
    const snap = aoState.snapshot || buildInstantFallbackSnapshot();
    const allAgents = Array.isArray(snap.agents) ? snap.agents : [];
    const ag = allAgents.find((a) => a.id === aoState.focusedAgentId) || {
      id: aoState.focusedAgentId,
      live_state: "standby",
      status_label_vi: "Đang trực chiến tại xưởng",
    };
    const prof = CHIBI_PROFILES[ag.id] || CHIBI_PROFILES.orchestrator;
    const theme = TOON_ROOM_THEMES[ag.id] || TOON_ROOM_THEMES.orchestrator;
    const roster = getMergedDeptRoster(ag.id, snap);
    const mKey = aoState.focusedMemberKey || "lead";
    const speech = buildPersonaFocusReply(ag, snap, aoState.focusAskMode, mKey);

    const lpr = snap.live_phase_report || {};
    const tel = aoState.livePhaseTelemetry || {};
    const isRoomWorking =
      aoState.parallelWaveActive ||
      ["working", "reworking", "critiquing"].includes(ag.live_state) ||
      (lpr.is_running && lpr.primary_agent_id === ag.id) ||
      (tel.agentId === ag.id);

    const livePct = isRoomWorking
      ? Number(tel.pct || lpr.percent || 65)
      : ag.live_state === "done"
      ? 100
      : Number(lpr.percent || 100);
    const liveStepIdx = Number(tel.stepIndex || lpr.step_index || snap.summary?.total_cli_steps || 0);
    const livePhaseLabel = String(
      lpr.phase_label_vi ||
        (snap.selected_job?.current_phase ? `Bước · ${snap.selected_job.current_phase}` : "Trực chiến dây chuyền")
    );
    const liveActionVi = String(
      (tel.byAgent && tel.byAgent[ag.id]) ||
        (isRoomWorking && lpr.current_action_vi) ||
        ag.live_bubble ||
        ag.status_label_vi ||
        roster.lead.role_vi
    );
    const milestones = Array.isArray(lpr.milestones) ? lpr.milestones : [];

    const secState = aoState.roomSecOpen || {
      progress: true,
      command: true,
      specialists: true,
      groupchat: false,
      all15: false,
    };
    const secSig = ["progress", "command", "specialists", "groupchat", "all15"]
      .map((k) => `${k}:${secState[k] ? 1 : 0}`)
      .join(",");

    const focusSig = [
      ag.id,
      ag.live_state || "standby",
      liveActionVi,
      livePct,
      liveStepIdx,
      ag.active_mini_agent_handle || "",
      roster.active_mini_agent_handle || "",
      mKey,
      aoState.focusAskMode,
      isRoomWorking ? "1" : "0",
      aoState.parallelWaveActive ? "1" : "0",
      speech,
      secSig,
      milestones.map((m) => `${m.file}:${m.done ? 1 : 0}:${m.detail_vi}`).join("|"),
      roster.specialists.map((sp) => `${sp.id}:${sp.progress_pct}:${sp.finding_vi}`).join("|"),
    ].join("::");

    if (aoState._lastFocusSig === focusSig && !card.hidden && card.children.length > 0) {
      return;
    }
    aoState._lastFocusSig = focusSig;
    ensureRoomCollapseStylesInjected();

    let activeMember = roster.lead;
    let activeRoleBadge = "👑 TRƯỞNG PHÒNG";
    if (mKey === "deputy") {
      activeMember = roster.deputy;
      activeRoleBadge = "🛡️ PHÓ PHÒNG";
    } else if (mKey !== "lead") {
      const sp = roster.specialists.find((s) => s.id === mKey || s.handle === mKey);
      if (sp) {
        activeMember = sp;
        activeRoleBadge = `⚡ ${sp.batch_id} (${sp.items_label})`;
      }
    }

    // Quick 15-room switcher strip at top of zoomed room
    const roomStripHtml = Object.entries(CHIBI_PROFILES)
      .map(([rid, rp]) => {
        const rag = allAgents.find((a) => a.id === rid);
        const rWorking =
          aoState.parallelWaveActive ||
          (rag && ["working", "reworking", "critiquing"].includes(rag.live_state)) ||
          (lpr.is_running && lpr.primary_agent_id === rid) ||
          (tel.agentId === rid);
        const num = String(rp.deptCode || "00").replace("DEPT-", "");
        const isCur = rid === ag.id;
        return `
          <button type="button"
                  class="ao-rz-room-pill${isCur ? " active" : ""}${rWorking ? " is-working" : ""}"
                  data-ao-focus-member="${esc(rid)}:lead"
                  title="Chuyển sang ${esc(rp.deptCode)} · ${esc(rp.shortTitleVi)} (${rp.headcount || 6} NS)">
            <span class="ao-rz-rp-dot"></span>
            <b>${esc(num)}</b>
          </button>
        `;
      })
      .join("");

    // Clean 2-item Deputy checklist preview
    const checksPreview = (
      Array.isArray(roster.deputy.checklist_vi) && roster.deputy.checklist_vi.length
        ? roster.deputy.checklist_vi.slice(0, 2)
        : [
            "Khớp 100% dữ liệu & ngữ nghĩa câu thoại",
            "Kiểm định đầu ra từng lô Chuyên viên 1..N",
          ]
    )
      .map((c) => `<div class="ao-rz-check-line"><span>✓</span> ${esc(c)}</div>`)
      .join("");

    // Build 4-Milestone Live Progress Grid
    let foundFirstPending = false;
    const milestonesHtml = (milestones.length
      ? milestones
      : roster.specialists.slice(0, 4).map((sp, i) => ({
          label_vi: `${i + 1}. ${sp.title_vi.slice(0, 28)}`,
          file: sp.artifact_key || `lane_${i + 1}`,
          done: ag.live_state === "done" || Number(sp.progress_pct || 0) >= 100,
          detail_vi: `${sp.batch_id} · ${sp.items_label}`,
        }))
    )
      .slice(0, 4)
      .map((ms) => {
        const isDone = Boolean(ms.done);
        const isCurrentMs = !isDone && !foundFirstPending && isRoomWorking;
        if (isCurrentMs) foundFirstPending = true;
        const icon = isDone ? "✅" : isCurrentMs ? "⚡" : "⏳";
        const cls = isDone ? " is-done" : isCurrentMs ? " is-active-ms" : "";
        return `
          <div class="ao-rz-milestone-card${cls}">
            <div class="ao-rz-ms-left">
              <strong>${icon} ${esc(ms.label_vi)}</strong>
              <small>${esc(ms.detail_vi)}</small>
            </div>
            <code class="ao-rz-ms-file">${esc(ms.file)}</code>
          </div>
        `;
      })
      .join("");

    // Cartoon Movie Set Specialist Desks (4 desks or 6 desks for DEPT-08 VOX)
    const specColsCls = roster.specialists.length >= 6 ? "cols-3-vox" : "cols-4-std";
    const specialistDesksHtml = roster.specialists
      .map((sp, idx) => {
        const isSel = mKey === sp.id || mKey === sp.handle;
        const msForLane = milestones[idx];
        const isMiniActive =
          isRoomWorking ||
          roster.active_mini_agent_handle === sp.handle ||
          ag.active_mini_agent_handle === sp.handle;
        let pct = Math.max(45, Math.min(100, Number(sp.progress_pct || 100)));
        let shortComicSpeech = String(sp.finding_vi || sp.role_vi || "Đang xử lý lô công việc!");
        if (isRoomWorking && msForLane) {
          pct = msForLane.done ? 100 : Math.max(55, Math.min(95, livePct));
          shortComicSpeech = `${msForLane.done ? "✓ Hoàn tất" : "⚡ Đang làm"} ${msForLane.file}: ${msForLane.detail_vi}`;
        }
        shortComicSpeech = shortComicSpeech.slice(0, 56);
        return `
          <article class="ao-rz-spec-desk ao-25d-workstation ao-toon-movie-desk${isSel ? " is-selected-desk" : ""}${isMiniActive ? " is-desk-working" : ""}"
                   data-ao-focus-member="${esc(ag.id)}:${esc(sp.id)}">
            <div class="ao-toon-desk-comic-bub">
              <span>${theme.fx} ${esc(shortComicSpeech)}${shortComicSpeech.length >= 56 ? "…" : ""}</span>
            </div>

            <div class="ao-rz-desk-stage ao-toon-desk-stage">
              <div class="ao-rz-chibi-seat">
                <div class="ao-rz-chibi-avatar">
                  ${buildMemberChibiSvg(ag.id, "specialist", idx)}
                  <span class="ao-rz-prop-badge">${prof.prop}</span>
                </div>
                <span class="ao-rz-seat-tag">${esc(sp.shortTag)}</span>
              </div>
              ${buildSpecialistWorkScreenHtml(ag.id, sp, idx, isMiniActive)}
            </div>

            <div class="ao-toon-wood-desktop">
              <span class="ao-toon-kb-strip">⌨️ <i></i><i></i><i></i></span>
              <span class="ao-toon-desk-plaque">⚡ ${esc(sp.batch_id)} · ${esc(sp.items_label)}</span>
              <span class="ao-toon-desk-cup">☕</span>
            </div>

            <div class="ao-rz-desk-info">
              <div class="ao-toon-name-row">
                <strong class="ao-rz-desk-title">${esc(sp.title_vi)}</strong>
                <code class="ao-rz-spec-handle">${esc(sp.handle)}</code>
              </div>
              <div class="ao-rz-progress-wrap">
                <div class="ao-rz-progress-bar"><i style="width:${pct}%;"></i></div>
                <span class="ao-rz-progress-num">${pct}%</span>
              </div>
            </div>

            <footer class="ao-rz-desk-actions">
              <button type="button" class="ao-rz-mini-btn" data-ao-open-spec-monitor="${esc(ag.id)}:${esc(sp.id)}">🔍 Màn hình #${idx + 1}</button>
              <button type="button" class="ao-rz-mini-btn" data-ao-dispatch-handle="${esc(sp.handle)}">📨 Giao việc</button>
            </footer>
          </article>
        `;
      })
      .join("");

    const liveRoomBannerTxt = isRoomWorking
      ? `🟢 ĐANG LÀM VIỆC · TIẾN ĐỘ ${livePct}%`
      : ag.live_state === "done"
      ? `✅ ĐÃ BÀN GIAO 100% · ${roster.headcount} NS`
      : `● TRỰC CHIẾN · ${roster.headcount} NHÂN SỰ`;
    const liveEtaVi = String(lpr.eta_vi || computePhaseEtaVi(Boolean(lpr.is_running || isRoomWorking), livePct, lpr.phase || "plan"));

    // Build scrollable 15-Department × 92-Personnel quick directory inside the room view so user always sees all 92 staff
    const all15RoomsGridHtml = Object.entries(CHIBI_PROFILES)
      .map(([rid, rp]) => {
        const rag = allAgents.find((a) => a.id === rid) || {};
        const rRoster = getMergedDeptRoster(rid, snap);
        const rWorking =
          aoState.parallelWaveActive ||
          ["working", "reworking", "critiquing"].includes(rag.live_state) ||
          (lpr.is_running && lpr.primary_agent_id === rid) ||
          (tel.agentId === rid);
        const isCur = rid === ag.id;
        const stTag = rWorking ? "🟢 ĐANG LÀM" : rag.live_state === "done" ? "✅ ĐÃ XONG" : `👥 ${rRoster.headcount} NS`;
        return `
          <div class="ao-rz-all15-card${isCur ? " is-current" : ""}${rWorking ? " is-working" : ""}" data-ao-focus-member="${esc(rid)}:lead">
            <div class="ao-rz-all15-top">
              <span class="ao-rz-all15-code">${esc(rp.deptCode)}</span>
              <strong>${rp.prop} ${esc(rp.shortTitleVi)}</strong>
              <span class="ao-rz-all15-st">${stTag}</span>
            </div>
            <div class="ao-rz-all15-roles">
              <span>👑 <code>${esc(rRoster.lead.handle)}</code></span>
              <span>🛡️ <code>${esc(rRoster.deputy.handle)}</code></span>
              <span>⚡ ${rRoster.specialists.length} Chuyên viên</span>
            </div>
          </div>
        `;
      })
      .join("");

    const doneMsCount = milestones.filter((m) => m.done).length;
    const totalMsCount = milestones.length || 4;
    const allOpenCount = ["progress", "command", "specialists", "groupchat", "all15"].filter((k) => secState[k]).length;
    const toggleAllLabel = allOpenCount >= 4 ? "▴ Thu gọn gọn gàng" : "▾ Mở rộng tất cả (5 mục)";

    card.className = `ao-focus-reply-card ao-room-zoom-interior-stage ao-room-25d-interior ao-toon-movie-set${isRoomWorking ? " is-room-live-working" : ""}`;
    card.style.setProperty("--room-accent", prof.hatColor || "#38bdf8");
    card.style.setProperty("--room-rug", theme.rug);
    card.style.setProperty("--room-rug-border", theme.rugBorder);
    card.style.setProperty("--room-wall", theme.wall);
    card.removeAttribute("hidden");
    card.hidden = false;
    card.style.display = "flex";
    card.innerHTML = `
      <!-- TOP STUDIO NAVIGATION BAR (2-TIER ZERO-CLIPPING LAYOUT) -->
      <header class="ao-rz-topbar ao-toon-set-topbar">
        <div class="ao-rz-topbar-row1">
          <div class="ao-rz-top-left">
            <button type="button" class="ao-rz-back-office-btn" data-ao-exit-focus="true" title="Thu nhỏ camera về Toàn Cảnh Xưởng Phim 15 Phòng Ban (92 Nhân sự)">
              ⬅ Toàn Cảnh 15 Phòng (92 NS)
            </button>
            <div class="ao-rz-room-identity">
              <span class="ao-rz-room-icon ao-toon-room-gizmo gizmo-${theme.gizmoAnim}">${prof.prop}</span>
              <div class="ao-rz-room-identity-text">
                <div class="ao-rz-room-title-row">
                  <span class="ao-rz-code-pill">${esc(roster.code)}</span>
                  <h4>${esc(prof.nickVi || prof.shortTitleVi)}</h4>
                  <span class="ao-rz-live-status-pill">${esc(liveRoomBannerTxt)}</span>
                  <span class="ao-rz-headcount-note">👥 Phòng này: ${roster.headcount} NS / Toàn xưởng: 15 Phòng · 92 NS</span>
                </div>
                <p class="ao-rz-room-sub">${esc(prof.roleVi || "")} · <em>Bấm vào thanh tiêu đề từng mục bên dưới để <b>Thu gọn ▴ / Mở rộng ▾</b></em></p>
              </div>
            </div>
          </div>
          <div class="ao-rz-top-right">
            <button type="button" class="ao-rz-collapse-all-btn" data-ao-toggle-all-room-sec="1" title="Đóng hoặc mở rộng toàn bộ 5 khu vực trong phòng">
              ${toggleAllLabel}
            </button>
            <button type="button" class="ao-rz-run-room-btn" data-ao-dispatch-parallel-dept="${esc(ag.id)}" title="Kích hoạt toàn bộ ${roster.headcount} nhân sự trong phòng này chạy Chia Lô Song Song">
              ⚡ Chia ${roster.specialists.length} Lô Song Song
            </button>
          </div>
        </div>
        <div class="ao-rz-topbar-row2">
          <span class="ao-rz-strip-label">🏛️ Chuyển nhanh 15 Phòng:</span>
          <div class="ao-rz-room-strip" title="Chuyển nhanh giữa 15 Phòng Chuyên Môn">
            ${roomStripHtml}
          </div>
        </div>
      </header>

      <!-- SECTION 1 (COLLAPSIBLE): REAL-TIME PROGRESS & 4 MILESTONES -->
      <section class="ao-rz-collapse-card theme-emerald ${secState.progress ? "is-open" : "is-collapsed"}" data-ao-sec="progress">
        <header class="ao-rz-collapse-head" data-ao-toggle-room-sec="progress" title="Bấm để Thu gọn / Mở rộng bảng Tiến độ & 4 Cột mốc">
          <div class="ao-rz-collapse-head-left">
            <span class="ao-rz-live-pulse-dot"></span>
            <span class="ao-rz-collapse-title">📊 MỤC 1 · TIẾN ĐỘ THỰC THI &amp; 4 CỘT MỐC ĐẦU RA (${esc(livePhaseLabel)})</span>
            <span class="ao-rz-collapse-meta-badge emerald">${doneMsCount}/${totalMsCount} cột mốc · ${livePct}%</span>
            ${liveStepIdx > 0 ? `<span class="ao-rz-collapse-meta-badge">⚡ Bước #${liveStepIdx}</span>` : ""}
            <span class="ao-rz-collapse-meta-badge gold">⏱️ ${esc(liveEtaVi)}</span>
          </div>
          <div class="ao-rz-collapse-head-right">
            <span class="ao-rz-collapse-toggle-pill">${secState.progress ? "Thu gọn ▴" : "Mở rộng ▾"}</span>
          </div>
        </header>
        <div class="ao-rz-collapse-body">
          <div class="ao-rz-live-report-banner" style="padding:10px 12px;margin:0;">
            <div class="ao-rz-live-report-top">
              <div class="ao-rz-live-report-title">
                <span class="ao-rz-live-phase-tag">${esc(livePhaseLabel)}</span>
                <span class="ao-rz-live-action-txt">${esc(liveActionVi)}</span>
              </div>
              <div class="ao-rz-live-pct-wrap">
                <div class="ao-rz-live-bar-outer"><div class="ao-rz-live-bar-fill" style="width:${livePct}%;"></div></div>
                <span class="ao-rz-live-pct-num">${livePct}%</span>
                <span class="ao-rz-eta-badge">⏱️ Bao lâu nữa xong: <b>${esc(liveEtaVi)}</b></span>
              </div>
            </div>
            <div class="ao-rz-milestone-grid">
              ${milestonesHtml}
            </div>
          </div>
        </div>
      </section>

      <!-- SECTION 2 (COLLAPSIBLE): EXECUTIVE COMMAND STAGE (LEAD ↔ WORKFLOW ↔ DEPUTY) -->
      <section class="ao-rz-collapse-card theme-gold ${secState.command ? "is-open" : "is-collapsed"}" data-ao-sec="command">
        <header class="ao-rz-collapse-head" data-ao-toggle-room-sec="command" title="Bấm để Thu gọn / Mở rộng Ban Chỉ Huy Phòng (Tổ trưởng · Quy trình · Tổ phó)">
          <div class="ao-rz-collapse-head-left">
            <span class="ao-rz-collapse-title">👑 MỤC 2 · BAN CHỈ HUY PHÒNG ${esc(roster.code)} (TỔ TRƯỞNG · QUY TRÌNH · TỔ PHÓ)</span>
            <span class="ao-rz-collapse-meta-badge gold">👑 ${esc(roster.lead.handle)}</span>
            <span class="ao-rz-collapse-meta-badge">🛡️ ${esc(roster.deputy.handle)}</span>
            <span class="ao-rz-collapse-meta-badge emerald">🚀 Tăng tốc ${esc(roster.speedup_factor)}</span>
          </div>
          <div class="ao-rz-collapse-head-right">
            <span class="ao-rz-collapse-toggle-pill">${secState.command ? "Thu gọn ▴" : "Mở rộng ▾"}</span>
          </div>
        </header>
        <div class="ao-rz-collapse-body">
          <div class="ao-rz-command-deck ao-toon-exec-stage">
            <!-- BÀN TRƯỞNG PHÒNG -->
            <div class="ao-rz-leader-desk ao-25d-exec-desk ao-toon-boss-desk role-lead${mKey === "lead" ? " is-selected-desk" : ""}" data-ao-focus-member="${esc(ag.id)}:lead">
              <div class="ao-rz-leader-left">
                <div class="ao-rz-leader-chibi">
                  <span class="ao-toon-boss-bub">👑 Chỉ huy!</span>
                  ${buildMemberChibiSvg(ag.id, "lead", 0)}
                  <span class="ao-rz-rank-pill">👑 TRƯỞNG PHÒNG</span>
                </div>
              </div>
              <div class="ao-rz-leader-main">
                <div class="ao-rz-leader-head">
                  <strong>${esc(roster.lead.title_vi)}</strong>
                  <code>${esc(roster.lead.handle)}</code>
                </div>
                <p class="ao-rz-leader-duty">${esc(liveActionVi)}</p>
                <div class="ao-rz-leader-screen">
                  <span>📊 Chia ${roster.specialists.length} lô (${esc(roster.speedup_factor)})</span>
                  <span>✍️ <b>${esc(roster.lead.approval_output_vi)}</b></span>
                </div>
                <div class="ao-rz-leader-actions">
                  <button type="button" class="ao-rz-mini-btn" data-ao-open-spec-monitor="${esc(ag.id)}:lead">🔍 Giám sát</button>
                  <button type="button" class="ao-rz-mini-btn" data-ao-dispatch-handle="${esc(roster.lead.handle)}">📨 Giao việc</button>
                </div>
              </div>
            </div>

            <!-- BẢNG QUY TRÌNH CỦA PHÒNG -->
            <div class="ao-rz-intra-flow ao-25d-wall-board ao-toon-corkboard">
              <div class="ao-rz-flow-title">📌 BẢNG PHÂN CẢNH &amp; QUY TRÌNH ${esc(roster.code)}</div>
              <div class="ao-rz-flow-steps">
                <span class="ao-rz-fstep">👑 <b>Trưởng</b><small>Chia ${roster.specialists.length} lô</small></span>
                <span class="ao-rz-farrow">➔</span>
                <span class="ao-rz-fstep hi">⚡ <b>${roster.specialists.length} CV</b><small>Song song</small></span>
                <span class="ao-rz-farrow">➔</span>
                <span class="ao-rz-fstep">🛡️ <b>Phó</b><small>Duyệt 100%</small></span>
                <span class="ao-rz-farrow">➔</span>
                <span class="ao-rz-fstep ok">✅ <b>Xuất</b><small>Bàn giao</small></span>
              </div>
            </div>

            <!-- BÀN PHÓ PHÒNG -->
            <div class="ao-rz-leader-desk ao-25d-exec-desk ao-toon-boss-desk role-deputy${mKey === "deputy" ? " is-selected-desk" : ""}" data-ao-focus-member="${esc(ag.id)}:deputy">
              <div class="ao-rz-leader-left">
                <div class="ao-rz-leader-chibi">
                  <span class="ao-toon-boss-bub deputy">🛡️ Duyệt kỹ!</span>
                  ${buildMemberChibiSvg(ag.id, "deputy", 0)}
                  <span class="ao-rz-rank-pill deputy">🛡️ PHÓ PHÒNG</span>
                </div>
              </div>
              <div class="ao-rz-leader-main">
                <div class="ao-rz-leader-head">
                  <strong>${esc(roster.deputy.title_vi)}</strong>
                  <code>${esc(roster.deputy.handle)}</code>
                </div>
                <div class="ao-rz-deputy-checklist">
                  ${checksPreview}
                </div>
                <div class="ao-rz-leader-actions">
                  <button type="button" class="ao-rz-mini-btn" data-ao-open-spec-monitor="${esc(ag.id)}:deputy">🔍 Checklist</button>
                  <button type="button" class="ao-rz-mini-btn" data-ao-dispatch-handle="${esc(roster.deputy.handle)}">📨 Giao việc</button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- SECTION 3 (COLLAPSIBLE): SPECIALIST WORKSTATIONS GRID -->
      <section class="ao-rz-collapse-card theme-cyan ${secState.specialists ? "is-open" : "is-collapsed"}" data-ao-sec="specialists">
        <header class="ao-rz-collapse-head" data-ao-toggle-room-sec="specialists" title="Bấm để Thu gọn / Mở rộng Cụm bàn Chuyên viên phân lô song song">
          <div class="ao-rz-collapse-head-left">
            <span class="ao-rz-collapse-title">⚡ MỤC 3 · CỤM BÀN CHUYÊN VIÊN PHÂN LÔ (${roster.specialists.length} CHUYÊN VIÊN · CHẠY SONG SONG)</span>
            <span class="ao-rz-collapse-meta-badge emerald">📁 Đồng bộ Lô 1..${roster.specialists.length} ➔ ${esc(roster.deputy.handle)} duyệt ✓</span>
          </div>
          <div class="ao-rz-collapse-head-right">
            <span class="ao-rz-collapse-toggle-pill">${secState.specialists ? "Thu gọn ▴" : "Mở rộng ▾"}</span>
          </div>
        </header>
        <div class="ao-rz-collapse-body">
          <div class="ao-rz-spec-grid ${specColsCls}">
            ${specialistDesksHtml}
          </div>
        </div>
      </section>

      <!-- COMPACT ACTIVE MEMBER DIALOGUE & QUICK ACTIONS BAR -->
      <footer class="ao-rz-dialogue-footer ao-toon-comic-footer">
        <div class="ao-rz-dialogue-left">
          <span class="ao-rz-speaker-pill">${esc(activeRoleBadge)} · <code>${esc(activeMember.handle)}</code></span>
          <p class="ao-rz-speech-txt">${esc(speech)}</p>
        </div>
        <div class="ao-rz-dialogue-actions">
          <button type="button" class="ao-focus-ask-btn${aoState.focusAskMode === "progress" ? " active" : ""}" data-ao-ask="progress">📊 Tiến độ</button>
          <button type="button" class="ao-focus-ask-btn${aoState.focusAskMode === "qa" ? " active" : ""}" data-ao-ask="qa">⚖️ Nghiệm thu</button>
          <button type="button" class="ao-focus-ask-btn${aoState.focusAskMode === "persona" ? " active" : ""}" data-ao-ask="persona">👤 Nhiệm vụ</button>
          <button type="button" class="ao-focus-ask-btn primary-glow" data-ao-open-spec-monitor="${esc(ag.id)}:${esc(mKey)}">🔍 Màn hình ${esc(activeMember.handle)}</button>
          <button type="button" class="ao-focus-ask-btn" data-ao-open-charter="${esc(ag.id)}">📜 Hồ sơ Phòng</button>
        </div>
      </footer>

      <!-- SECTION 4 (COLLAPSIBLE): EMBEDDED LIVE GROUP CHAT -->
      <section class="ao-rz-collapse-card theme-emerald ${secState.groupchat ? "is-open" : "is-collapsed"}" data-ao-sec="groupchat">
        <header class="ao-rz-collapse-head" data-ao-toggle-room-sec="groupchat" title="Bấm để Mở rộng / Thu gọn Nhóm Chat Trực Chiến ngay trong phòng">
          <div class="ao-rz-collapse-head-left">
            <span class="ao-rz-collapse-title">💬 MỤC 4 · NHÓM CHAT TRỰC CHIẾN 15 PHÒNG BAN (92 NHÂN SỰ)</span>
            <span class="ao-rz-collapse-meta-badge emerald">🟢 92/92 Online</span>
            <span class="ao-rz-collapse-meta-badge gold">⏱️ ${esc(liveEtaVi)}</span>
          </div>
          <div class="ao-rz-collapse-head-right">
            <span class="ao-rz-collapse-toggle-pill">${secState.groupchat ? "Thu gọn ▴" : "Mở rộng ▾"}</span>
          </div>
        </header>
        <div class="ao-rz-collapse-body">
          ${renderGroupChatPanelHtml(snap, true)}
        </div>
      </section>

      <!-- SECTION 5 (COLLAPSIBLE): ALL 15 DEPARTMENTS (92 STAFF) QUICK DIRECTORY -->
      <section class="ao-rz-collapse-card theme-cyan ${secState.all15 ? "is-open" : "is-collapsed"}" data-ao-sec="all15">
        <header class="ao-rz-collapse-head" data-ao-toggle-room-sec="all15" title="Bấm để Mở rộng / Thu gọn Danh bạ chuyển nhanh 15 Phòng Ban (92 Nhân sự)">
          <div class="ao-rz-collapse-head-left">
            <span class="ao-rz-collapse-title">🏛️ MỤC 5 · DANH BẠ TOÀN BỘ 15 PHÒNG BAN · 92 NHÂN SỰ (15 TRƯỞNG · 15 PHÓ · 62 CHUYÊN VIÊN)</span>
            <span class="ao-rz-collapse-meta-badge">Đang xem: ${esc(roster.code)} (${roster.headcount} NS)</span>
          </div>
          <div class="ao-rz-collapse-head-right">
            <span class="ao-rz-collapse-toggle-pill">${secState.all15 ? "Thu gọn ▴" : "Mở rộng ▾"}</span>
          </div>
        </header>
        <div class="ao-rz-collapse-body">
          <div class="ao-rz-all15-grid">
            ${all15RoomsGridHtml}
          </div>
        </div>
      </section>
    `;
  }

  // Update 15 Cartoon Rooms (92 Staff Members), 10 Roaming Couriers + 2 Pets, Live Board & Links from Snapshot
  function syncChibiStageWithSnapshot(snap) {
    const host = document.getElementById("agentOfficeFloorplanCanvas");
    if (!host || !snap) return;
    ensureChibiStageMounted(host);

    const agents = Array.isArray(snap.agents) ? snap.agents : [];
    const gates = Array.isArray(snap.critique_gates) ? snap.critique_gates : [];
    const s = snap.summary || {};

    // Update ON AIR vocal booth sign
    const voiceAg = agents.find((a) => a.id === "voice");
    const onAirEl = document.getElementById("aoOnAirSign");
    if (onAirEl && voiceAg) {
      const liveVoice = voiceAg.live_state === "working" || voiceAg.live_state === "reworking";
      onAirEl.classList.toggle("is-live", liveVoice);
      onAirEl.textContent = liveVoice ? "🔴 ON AIR · ĐANG THU" : "● STUDIO VOICE";
    }

    // Update Central Boulevard Cinema Scoreboard
    const activeCnt = Number(s.active_agents_count || 0);
    const vpEl = document.getElementById("aoChibiViewport");
    if (vpEl) {
      vpEl.classList.toggle("has-active-work", activeCnt > 0 || Boolean(aoState.parallelWaveActive));
    }
    const lpr = snap.live_phase_report || {};
    const pct = lpr.is_running
      ? Number(lpr.percent || 45)
      : Math.min(100, Math.round(((Number(s.passed_gates || 0)) / Math.max(1, Number(s.total_gates || 8))) * 100));
    const fillEl = document.getElementById("aoLiveBoardFill");
    const subEl = document.getElementById("aoLiveBoardSub");
    const titleEl = document.getElementById("aoLiveBoardTitle");
    if (fillEl) fillEl.style.width = `${aoState.parallelWaveActive ? 100 : Math.max(18, pct)}%`;
    if (titleEl) {
      const curPhase = snap.selected_job?.current_phase;
      if (aoState.parallelWaveActive) {
        titleEl.textContent = `⚡ ĐANG CHẠY SONG SONG 15 PHÒNG BAN · 92 NHÂN SỰ (62 LUỒNG)`;
      } else if (lpr.is_running && lpr.phase_label_vi) {
        titleEl.textContent = `🎬 ${lpr.phase_label_vi.toUpperCase()} (${pct}%) · PHÒNG @${String(lpr.primary_agent_id || "script").toUpperCase()} ĐANG LÀM VIỆC`;
      } else if (curPhase) {
        titleEl.textContent = `🎬 BƯỚC «${String(curPhase).toUpperCase()}» · ${activeCnt}/15 PHÒNG ĐANG HOẠT ĐỘNG`;
      } else {
        titleEl.textContent = `🎬 XƯỞNG PHIM HOẠT HÌNH COFI · 15 PHÒNG BAN · 92 NHÂN SỰ`;
      }
    }
    if (subEl) {
      subEl.textContent = lpr.is_running && lpr.current_action_vi
        ? `${lpr.current_action_vi} · ${snap.selected_job?.title || ""}`
        : snap.selected_job?.title
        ? `${snap.selected_job.title}`
        : "15 Trưởng phòng · 15 Phó phòng · 62 Chuyên viên — Bấm vào Phòng để vào Phim Trường Nội Thất!";
    }

    // Update each of the 15 Cartoon Rooms & their 6-8 seated staff members
    agents.forEach((ag) => {
      const p = CHIBI_PROFILES[ag.id];
      if (!p) return;
      const roster = getMergedDeptRoster(ag.id, snap);
      const isDeptWave = aoState.parallelWaveActive && (!aoState.parallelWaveDept || aoState.parallelWaveDept === "all" || aoState.parallelWaveDept === ag.id);
      const st = isDeptWave ? "working" : ag.live_state || "standby";
      const stEl = document.getElementById(`aoStation-${ag.id}`);
      if (stEl) {
        const isVox = ag.id === "vox" ? " is-vox-pod" : "";
        const isFoc = aoState.focusedAgentId === ag.id ? " is-focused" : "";
        const isWave = isDeptWave ? " is-parallel-wave" : "";
        const isDim =
          aoState.floorZoneFilter !== "all" && p.zone !== aoState.floorZoneFilter ? " is-zone-dimmed" : "";
        const nextCls = `ao-station ao-team-pod ao-25d-glass-room ao-toon-room st-${st}${isVox}${isFoc}${isWave}${isDim}`;
        if (stEl.className !== nextCls) {
          stEl.className = nextCls;
        }
      }
      const badgeEl = document.getElementById(`aoPodBadge-${ag.id}`);
      if (badgeEl) {
        const nextBadge =
          st === "working" || isDeptWave
            ? `🟢 ĐANG QUAY`
            : st === "done"
            ? `✓ XONG`
            : `${roster.headcount} NS`;
        if (badgeEl.textContent !== nextBadge) {
          badgeEl.textContent = nextBadge;
        }
      }

      // Highlight active mini-agent inside the pod if specified
      roster.specialists.forEach((sp) => {
        const mEl = document.getElementById(`aoMember-${ag.id}-${sp.id}`);
        if (mEl) {
          const isActiveMini =
            isDeptWave ||
            st === "working" ||
            roster.active_mini_agent_handle === sp.handle ||
            ag.active_mini_agent_handle === sp.handle;
          mEl.classList.toggle("is-active-worker", Boolean(isActiveMini));
        }
      });
    });

    // Sync state classes on the 4 Roaming Couriers + 2 Studio Pets
    const allRoamerIds = [...LIAISON_AGENTS, ...STUDIO_PETS.map((p) => p.id)];
    allRoamerIds.forEach((id) => {
      const ac = aoState.actors[id];
      const ag = agents.find((a) => a.id === id) || { id, live_state: "working" };
      if (!ac) return;

      const reviewingGate = !ac.isPet && gates.find((g) => g.maker_agent === id && g.gate_state === "critic_reviewing");
      if (reviewingGate && id !== "evidence_qa") {
        ac.spotId = null;
        ac.tx = 740;
        ac.ty = 266;
        ac.fx = "📄";
        ac.tag = "Mang hồ sơ qua cổng QA!";
      }

      const actorEl = document.getElementById(`aoActor-${id}`);
      if (actorEl) {
        const walkCls = ac.walking ? " is-walking" : "";
        const faceCls = ac.facingLeft ? " facing-left" : "";
        const petCls = ac.isPet ? " ao-studio-pet" : "";
        const focCls = aoState.focusedAgentId === id ? " is-focused" : "";
        const nextActorCls = `ao-chibi-actor ao-lounge-liaison${petCls} state-${ag.live_state || "working"}${walkCls}${faceCls}${focCls}`;
        if (actorEl.className !== nextActorCls) {
          actorEl.className = nextActorCls;
        }
      }
    });

    // Auto-Zoom into the room currently executing work if autoZoomActiveRoom is enabled and user hasn't locked overview!
    const primaryWorkingDept = resolvePrimaryWorkingDepartment(snap);
    if (aoState.autoZoomActiveRoom && !aoState.manualOverviewLock && primaryWorkingDept && CHIBI_PROFILES[primaryWorkingDept]) {
      const autoKey = `${snap.selected_job?.id || "job"}:${snap.selected_job?.current_phase || "phase"}:${primaryWorkingDept}`;
      aoState.lastAutoZoomKey = autoKey;
      if (aoState.focusedAgentId !== primaryWorkingDept && aoState.manualZoomOutKey !== autoKey) {
        focusChibiAgent(primaryWorkingDept, "lead", true);
      }
    }

    refreshAllChibiBubbles(snap);
    drawChibiWorldLinks(snap.links || []);
    if (aoState.focusedAgentId) {
      renderFocusReplyOverlay();
      syncCameraTransform();
    }
  }

  function refreshAllChibiBubbles(snap) {
    if (!snap || !Array.isArray(snap.agents)) return;
    snap.agents.forEach((ag, idx) => {
      const bubEl = document.getElementById(`aoBubble-${ag.id}`);
      if (!bubEl) return;
      const isWorkingNow =
        ag.live_state === "working" ||
        ag.live_state === "critiquing" ||
        ag.live_state === "reworking";
      if (!isWorkingNow || aoState.focusedAgentId) {
        bubEl.hidden = true;
        return;
      }
      const txt = buildContinuousBubbleText(ag, snap, aoState.bubbleTick + idx);
      if (!txt) {
        bubEl.hidden = true;
        return;
      }
      const cls =
        ag.live_state === "working"
          ? "bub-working"
          : ag.live_state === "critiquing"
          ? "bub-critiquing"
          : "bub-reworking";
      const nextBubCls = `ao-chibi-bubble ${cls}`;
      if (bubEl.className !== nextBubCls) bubEl.className = nextBubCls;
      if (bubEl.textContent !== txt) {
        bubEl.textContent = txt;
      }
      bubEl.hidden = false;
    });
  }

  function drawChibiWorldLinks(links) {
    const svg = document.getElementById("aoChibiLinksSvg");
    if (!svg) return;
    const paths = [];
    (links || []).forEach((lnk) => {
      const p1 = CHIBI_PROFILES[lnk.from];
      const p2 = CHIBI_PROFILES[lnk.to];
      if (!p1 || !p2) return;
      const x1 = p1.hx;
      const y1 = p1.hy - 24;
      const x2 = p2.hx;
      const y2 = p2.hy - 24;
      const cx = (x1 + x2) / 2;
      const cy = Math.min(y1, y2) - 34;
      paths.push(
        `<path class="ao-link-line kind-${esc(lnk.kind)}" d="M ${x1.toFixed(1)} ${y1.toFixed(1)} Q ${cx.toFixed(1)} ${cy.toFixed(1)} ${x2.toFixed(1)} ${y2.toFixed(1)}" />`
      );
    });
    const nextHtml = paths.join("");
    if (svg._lastHtml !== nextHtml) {
      svg._lastHtml = nextHtml;
      svg.innerHTML = nextHtml;
    }
  }

  // Ultra-Lightweight GPU Hardware-Accelerated CSS Transition Roaming (0% CPU 60fps JS loop!)
  function stepRoamersCss() {
    if (!aoState.open || aoState.viewMode !== "chibi" || aoState.focusedAgentId || document.hidden) {
      return;
    }
    const occupiedSpots = new Set();
    Object.values(aoState.actors).forEach((ac) => {
      if (ac.spotId) occupiedSpots.add(ac.spotId);
    });

    Object.entries(aoState.actors).forEach(([id, ac]) => {
      const el = document.getElementById(`aoActor-${id}`);
      if (!el) return;

      occupiedSpots.delete(ac.spotId);
      const freeSpots = LOUNGE_SPOTS.filter((sp) => !occupiedSpots.has(sp.id));
      const pick = freeSpots.length > 0
        ? freeSpots[Math.floor(Math.random() * freeSpots.length)]
        : LOUNGE_SPOTS[Math.floor(Math.random() * LOUNGE_SPOTS.length)];
      if (!pick) return;

      ac.spotId = pick.id;
      occupiedSpots.add(pick.id);
      const nextX = pick.x + (Math.random() * 18 - 9);
      const nextY = pick.y + (Math.random() * 10 - 5);
      const dx = nextX - ac.x;
      if (Math.abs(dx) > 2) {
        ac.facingLeft = dx < 0;
      }
      ac.x = nextX;
      ac.y = nextY;
      ac.tx = nextX;
      ac.ty = nextY;
      ac.walking = true;
      ac.fx = ac.isPet ? (id === "pet_cat" ? "🐾" : "🎞️") : pick.fx;
      ac.tag = ac.isPet
        ? id === "pet_cat"
          ? "Meow~ Đi tuần xưởng phim!"
          : "Gâu! Giao cuộn phim Master!"
        : pick.tag;

      el.classList.add("is-walking");
      el.classList.toggle("facing-left", Boolean(ac.facingLeft));
      el.style.transform = `translate3d(${ac.x.toFixed(1)}px,${ac.y.toFixed(1)}px,0)`;

      const fxEl = document.getElementById(`aoFx-${id}`);
      if (fxEl && fxEl.textContent !== ac.fx) fxEl.textContent = ac.fx;
      const bubEl = document.getElementById(`aoRoamerBub-${id}`);
      if (bubEl && bubEl.textContent !== ac.tag) bubEl.textContent = ac.tag;
    });
  }

  function startSimulationLoop() {
    if (aoState.rafId) {
      cancelAnimationFrame(aoState.rafId);
      aoState.rafId = null;
    }
    if (!aoState.roamTimer && aoState.open && aoState.viewMode === "chibi") {
      setTimeout(() => stepRoamersCss(), 150);
      aoState.roamTimer = setInterval(stepRoamersCss, 3400);
    }
  }

  // Classic Technical Grid Fallback (`viewMode === "grid"`) — Upgraded to 3-Tier Department Card
  function renderDeskCard(ag) {
    const stateCls = ` state-${ag.live_state || "standby"}`;
    const selectedCls = aoState.selectedAgentId === ag.id ? " is-selected" : "";
    const dept = ag.department_hierarchy || {};
    const lead = ag.lead || dept.lead || {};
    const deputy = ag.deputy || dept.deputy || {};
    const specs = Array.isArray(ag.specialists) ? ag.specialists : Array.isArray(dept.specialists) ? dept.specialists : [];
    const specCount = specs.length || 4;
    const headcount = dept.headcount || ag.headcount || 2 + specCount;
    const deptCode = dept.code || ag.dept_code || CHIBI_PROFILES[ag.id]?.deptCode || "DEPT";
    const deptName = dept.name_vi || ag.dept_name_vi || ag.title_vi || ag.name;
    const stateIcon =
      ag.live_state === "working"
        ? "🟢"
        : ag.live_state === "critiquing"
        ? "⚖️"
        : ag.live_state === "reworking"
        ? "🔄"
        : ag.live_state === "done"
        ? "✓"
        : ag.live_state === "blocked"
        ? "⛔"
        : "•";

    const bubbleHtml = ag.live_bubble
      ? `<div class="ao-speech-bubble">${esc(ag.live_bubble)}</div>`
      : ag.completed_badge
      ? `<div class="ao-desk-Subnote">✓ ${esc(ag.completed_badge)}</div>`
      : `<div class="ao-desk-Subnote">${esc(ag.wait_hint_vi || "")}</div>`;

    const reworkHtml = ag.rework_badge
      ? `<div><span class="ao-rework-pill">🔄 ${esc(ag.rework_badge)}</span></div>`
      : "";

    const activeMiniHtml = ag.active_mini_agent_handle
      ? `<div class="ao-mini-agent-chip" title="${esc(ag.active_mini_agent_task_vi || "")}">⚡ Đang xử lý: <strong>${esc(ag.active_mini_agent_handle)}</strong> · ${esc(ag.active_mini_agent_title_vi || "")}</div>`
      : "";

    const specPillsHtml = specs
      .map(
        (sp, i) =>
          `<span class="ao-desk-spec-pill${ag.active_mini_agent_handle === sp.handle ? " is-active" : ""}" title="${esc(sp.title_vi)}: ${esc(sp.input_from)} ➔ ${esc(sp.output_to)} (${esc(sp.artifact_key)})">B${i + 1} ${esc(sp.handle)}</span>`
      )
      .join("");

    return `
      <div class="ao-desk${stateCls}${selectedCls}${ag.id === "vox" ? " is-vox-flagship" : ""}" data-ao-agent="${esc(ag.id)}">
        <div class="ao-desk-top">
          <div class="ao-avatar-wrap">
            <div class="ao-avatar">${esc(ag.emoji || "🏛️")}</div>
            <div class="ao-desk-name">
              <div style="display:flex;align-items:center;gap:5px;flex-wrap:wrap;">
                <span class="ao-dept-code">${esc(deptCode)}</span>
                <code>@${esc(ag.id)}</code>
                <span class="ao-dept-headcount">👥 ${headcount} NS (1 Tổ trưởng · 1 Tổ phó · ${specCount} Chuyên viên)</span>
              </div>
              <strong>${esc(deptName)}</strong>
            </div>
          </div>
          <div class="ao-monitor" title="Màn hình trực chiến Phòng Ban">
            <i class="ao-typing-bar"></i>
            <i class="ao-typing-bar"></i>
            <i class="ao-typing-bar"></i>
          </div>
        </div>
        <div class="ao-desk-status">
          <span>${stateIcon} ${esc(ag.status_label_vi)}</span>
        </div>
        <div class="ao-desk-hierarchy-mini">
          <div>👑 <strong>${esc(lead.handle || `@${ag.id}_lead`)}</strong> · ${esc(lead.title_vi || "Tổ trưởng")} <em style="color:#fde68a;">(${esc(lead.live_badge_vi || "Trực chiến")})</em></div>
          <div>🛡️ <strong>${esc(deputy.handle || `@${ag.id}_deputy`)}</strong> · ${esc(deputy.title_vi || "Tổ phó")} <em style="color:#7dd3fc;">(${esc(deputy.live_badge_vi || "Trực chiến")})</em></div>
        </div>
        ${activeMiniHtml}
        <div class="ao-desk-spec-pills">${specPillsHtml}</div>
        ${bubbleHtml}
        ${reworkHtml}
        <div class="ao-desk-quick-actions">
          <button type="button" class="ao-dispatch-chip" data-ao-open-charter="${esc(ag.id)}">📜 Chi tiết 3 Tầng</button>
          <button type="button" class="ao-dispatch-chip" data-ao-dispatch-handle="@${esc(ag.id)}">📨 @${esc(ag.id)}</button>
          <button type="button" class="ao-dispatch-chip" data-ao-dispatch-handle="${esc(lead.handle || `@${ag.id}_lead`)}">👑 ${esc(lead.handle || `@${ag.id}_lead`)}</button>
          <button type="button" class="ao-dispatch-chip" data-ao-dispatch-handle="${esc(deputy.handle || `@${ag.id}_deputy`)}">🛡️ ${esc(deputy.handle || `@${ag.id}_deputy`)}</button>
        </div>
      </div>
    `;
  }

  function renderDepartmentOrgCard(dept, isCompact) {
    if (!dept) return "";
    const st = dept.department_state || "standby";
    const lead = dept.lead || {};
    const deputy = dept.deputy || {};
    const specs = Array.isArray(dept.specialists) ? dept.specialists : [];
    const chain = Array.isArray(dept.workflow_chain_vi) ? dept.workflow_chain_vi : [];
    const isSel = aoState.selectedAgentId === dept.agent_id;
    const isVox = dept.agent_id === "vox";
    const divLabel = DIVISION_LABELS_VI[dept.division] || dept.division || "Khối Chuyên Môn";
    const headcount = dept.headcount || 2 + specs.length;

    const stateLabel =
      st === "working"
        ? "🟢 Đang vận hành dây chuyền"
        : st === "critiquing"
        ? "⚖️ Đang kiểm định đầu ra"
        : st === "reworking"
        ? "🔄 Đang tinh chỉnh nội bộ"
        : st === "done"
        ? "✅ Đã ký duyệt bàn giao"
        : st === "blocked"
        ? "⛔ Tạm dừng chờ xử lý"
        : "⚪ Trực chiến sẵn sàng";

    const leadRespsHtml = Array.isArray(lead.responsibilities_vi) && lead.responsibilities_vi.length
      ? `<ul class="ao-dept-check-list">${(isCompact ? lead.responsibilities_vi.slice(0, 2) : lead.responsibilities_vi)
          .map((r) => `<li>▸ ${esc(r)}</li>`)
          .join("")}</ul>`
      : "";

    const deputyChecksHtml = Array.isArray(deputy.checklist_vi) && deputy.checklist_vi.length
      ? `<ul class="ao-dept-check-list">${deputy.checklist_vi
          .map((c) => `<li>✓ ${esc(c)}</li>`)
          .join("")}</ul>`
      : `<div class="ao-dept-leader-out">✓ Checklist: <em>Kiểm soát quy trình &amp; chất lượng nội bộ</em></div>`;

    const specsHtml = specs
      .map((sp, idx) => {
        const stepNum = sp.step_order || idx + 1;
        const spState = sp.live_state || "standby";
        const isCurrent =
          dept.active_mini_agent_id === sp.id ||
          dept.active_mini_agent_handle === sp.handle;
        return `
          <div class="ao-dept-spec-node sp-${esc(spState)}${isCurrent ? " is-current-mini" : ""}">
            <div class="ao-dept-spec-head">
              <span class="ao-dept-rank-tag">⚡ Bước ${stepNum}/${specs.length} · ${esc(sp.rank_label_vi || `Chuyên viên ${stepNum}`)}</span>
              <button type="button" class="ao-dispatch-chip" data-ao-dispatch-handle="${esc(sp.handle)}" title="Bấm để gửi lệnh điều phối trực tiếp cho ${esc(sp.handle)}">💬 ${esc(sp.handle)}</button>
            </div>
            <strong class="ao-dept-spec-title">${esc(sp.title_vi)}</strong>
            <p class="ao-dept-spec-role">${esc(sp.task_detail_vi || sp.role_vi)}</p>
            <div class="ao-dept-spec-artifact">📦 Đầu ra: <code>${esc(sp.artifact_key || "artifact")}</code></div>
            <div class="ao-dept-spec-foot">
              <span class="ao-dept-handoff-tag">📥 ${esc(sp.input_from)} ➔ 📤 ${esc(sp.output_to)}</span>
              <span class="ao-dept-live-badge">${esc(sp.live_badge_vi || "Trực chiến")}</span>
            </div>
          </div>
        `;
      })
      .join('<div class="ao-dept-chain-arrow">➔</div>');

    const chainHtml = chain.length
      ? `
        <div class="ao-dept-workflow-box">
          <div class="ao-dept-workflow-head">
            <span>🔄 LUỒNG BÀN GIAO NỘI BỘ (TỔ TRƯỞNG PHÂN CÔNG ➔ CHUYÊN VIÊN 1..${specs.length} ➔ TỔ PHÓ RÀ CHECKLIST ➔ TỔ TRƯỞNG KÝ DUYỆT)</span>
          </div>
          <div class="ao-dept-workflow-steps">
            ${chain.map((stepTxt) => `<span class="ao-dept-workflow-pill">${esc(stepTxt)}</span>`).join('<span class="ao-dept-workflow-sep">➔</span>')}
          </div>
        </div>
      `
      : "";

    const voxFlagshipBanner = isVox
      ? `<div class="ao-vox-flagship-ribbon">⭐ TRỤ CỘT ĐỒ HỌA ĐIỀU TRA VOX · 8 NHÂN SỰ (1 Tổ trưởng <code>@vox_lead</code> · 1 Tổ phó <code>@vox_deputy</code> · 6 Chuyên viên: <code>@vox_voice_reader</code> ➔ <code>@vox_desk_designer</code> ➔ <code>@vox_asset_creator</code> ➔ <code>@vox_motion_designer</code> ➔ <code>@vox_choreography_animator</code> ➔ <code>@vox_spatial_locator</code>)</div>`
      : "";

    return `
      <article class="ao-dept-card dept-st-${esc(st)}${isSel ? " is-selected" : ""}${isVox ? " is-vox-flagship" : ""}" data-ao-agent="${esc(dept.agent_id)}" style="--dept-accent:${esc(dept.color || "#38bdf8")};">
        ${voxFlagshipBanner}
        <header class="ao-dept-card-head">
          <div class="ao-dept-card-title">
            <span class="ao-dept-emoji">${esc(dept.emoji || "🏛️")}</span>
            <div>
              <div class="ao-dept-code-row">
                <span class="ao-dept-code">${esc(dept.code || "DEPT")}</span>
                <code>${esc(dept.handle || `@${dept.agent_id}`)}</code>
                <span class="ao-dept-division-pill">${esc(divLabel)}</span>
                <span class="ao-dept-headcount">👥 ${esc(headcount)} nhân sự: 1 Tổ trưởng · 1 Tổ phó · ${specs.length} Chuyên viên</span>
              </div>
              <h4>${esc(dept.name_vi)}</h4>
            </div>
          </div>
          <div class="ao-dept-head-right">
            <span class="ao-dept-state-pill">${esc(dept.live_badge_vi || stateLabel)}</span>
          </div>
        </header>
        <p class="ao-dept-mission">${esc(dept.live_speech_vi || dept.mission_vi || "")}</p>

        <div class="ao-dept-command-row">
          <div class="ao-dept-leader-box role-lead st-${esc(lead.live_state || st)}">
            <div class="ao-dept-leader-top">
              <span class="ao-dept-leader-badge">👑 TẦNG 1 · TỔ TRƯỞNG (LEAD)</span>
              <span class="ao-dept-live-badge">${esc(lead.live_badge_vi || "Trực chỉ huy")}</span>
              <button type="button" class="ao-dispatch-chip" data-ao-dispatch-handle="${esc(lead.handle || `@${dept.agent_id}_lead`)}" title="Gửi lệnh trực tiếp cho Tổ trưởng ${esc(lead.handle)}">⚡ ${esc(lead.handle || "")}</button>
            </div>
            <strong>${esc(lead.title_vi || "")}</strong>
            <p>${esc(lead.role_vi || "")}</p>
            ${leadRespsHtml}
            <div class="ao-dept-leader-out">✍️ Đầu ra ký duyệt: <em>${esc(lead.approval_output_vi || "")}</em></div>
          </div>

          <div class="ao-dept-leader-box role-deputy st-${esc(deputy.live_state || st)}">
            <div class="ao-dept-leader-top">
              <span class="ao-dept-leader-badge">🛡️ TẦNG 2 · TỔ PHÓ (DEPUTY)</span>
              <span class="ao-dept-live-badge">${esc(deputy.live_badge_vi || "Trực rà soát")}</span>
              <button type="button" class="ao-dispatch-chip" data-ao-dispatch-handle="${esc(deputy.handle || `@${dept.agent_id}_deputy`)}" title="Gửi lệnh rà checklist cho Tổ phó ${esc(deputy.handle)}">🛡️ ${esc(deputy.handle || "")}</button>
            </div>
            <strong>${esc(deputy.title_vi || "")}</strong>
            <p>${esc(deputy.role_vi || "")}</p>
            <div class="ao-dept-checklist-title">📋 Checklist nghiệm thu nội bộ (${(deputy.checklist_vi || []).length} tiêu chí):</div>
            ${deputyChecksHtml}
          </div>
        </div>

        <div class="ao-dept-spec-section-label">
          <span>⚡ TẦNG 3 · DÂY CHUYỀN CHUYÊN VIÊN MINI-AGENTS (${specs.length} CHUYÊN VIÊN · BƯỚC 1 ➔ BƯỚC ${specs.length})</span>
          ${
            dept.active_mini_agent_handle
              ? `<span class="ao-dept-active-mini">🔥 Chuyên viên đang xử lý chính: <strong>${esc(dept.active_mini_agent_handle)}</strong> (${esc(dept.active_mini_agent_title_vi)}) — <em>${esc(dept.active_mini_agent_task_vi || "")}</em></span>`
              : ""
          }
        </div>
        <div class="ao-dept-specialists-chain">
          ${specsHtml}
        </div>
        ${chainHtml}
        <footer class="ao-dept-card-footer">
          <div class="ao-dept-dispatch-bar">
            <span class="ao-dept-dispatch-label">📨 Điều phối nhanh vào Hộp Chat:</span>
            <button type="button" class="ao-dispatch-btn primary" data-ao-dispatch-handle="${esc(dept.handle || `@${dept.agent_id}`)}">🏛️ Giao Phòng ${esc(dept.handle || `@${dept.agent_id}`)}</button>
            <button type="button" class="ao-dispatch-btn" data-ao-dispatch-handle="${esc(lead.handle || `@${dept.agent_id}_lead`)}">👑 Tổ trưởng ${esc(lead.handle || "")}</button>
            <button type="button" class="ao-dispatch-btn" data-ao-dispatch-handle="${esc(deputy.handle || `@${dept.agent_id}_deputy`)}">🛡️ Tổ phó ${esc(deputy.handle || "")}</button>
            <button type="button" class="ao-dispatch-btn ghost" data-ao-open-charter="${esc(dept.agent_id)}">📜 Mở Hồ Sơ &amp; Checklist Phòng</button>
          </div>
        </footer>
      </article>
    `;
  }

  function renderFloorplan(snap) {
    const host = document.getElementById("agentOfficeFloorplanCanvas");
    const stageWrap = document.getElementById("agentOfficeStageWrap");
    if (!host || !snap) return;

    if (stageWrap) {
      stageWrap.classList.toggle("is-chibi-mode", aoState.viewMode === "chibi");
    }

    document.querySelectorAll("[data-ao-view]").forEach((b) => {
      b.classList.toggle("active", b.getAttribute("data-ao-view") === aoState.viewMode);
    });

    if (aoState.viewMode === "chibi") {
      syncChibiStageWithSnapshot(snap);
      startSimulationLoop();
      return;
    }

    aoState.stageMounted = false;

    if (aoState.viewMode === "departments") {
      const depts = Array.isArray(snap.departments) ? snap.departments : [];
      const dsum = snap.departments_summary || {};
      const curFilter = aoState.deptDivisionFilter || "all";
      const filteredDepts = depts.filter((d) => {
        if (curFilter === "all") return true;
        if (curFilter === "vox") return d.agent_id === "vox";
        return d.division === curFilter;
      });

      host.innerHTML = `
        <div class="ao-dept-stage-board">
          <div class="ao-dept-stage-banner">
            <div>
              <strong>🏛️ 15 Phòng Ban Chuyên Môn (15 Tổ trưởng · 15 Tổ phó · 62 Chuyên viên Mini-Agents)</strong>
              <p>Mỗi Phòng Ban (từ <code>DEPT-00 @orchestrator</code> đến <code>DEPT-14 @debug</code>, đặc biệt <code>DEPT-08 @vox</code> 8 nhân sự) vận hành theo cơ cấu 3 tầng độc lập: <strong>👑 Tổ trưởng phân công</strong> ➔ <strong>⚡ Chuyên viên Bước 1..N thực thi</strong> ➔ <strong>🛡️ Tổ phó rà checklist</strong> ➔ <strong>👑 Tổ trưởng ký duyệt bàn giao</strong>.</p>
              <div class="ao-dept-filter-bar" role="group" aria-label="Lọc theo Khối Phòng Ban">
                <button type="button" class="ao-dept-filter-btn${curFilter === "all" ? " active" : ""}" data-ao-dept-filter="all">🏛️ Tất cả 15 Phòng (92 NS)</button>
                <button type="button" class="ao-dept-filter-btn${curFilter === "vox" ? " active" : ""}" data-ao-dept-filter="vox">⭐ DEPT-08 @vox (8 NS)</button>
                <button type="button" class="ao-dept-filter-btn${curFilter === "executive" ? " active" : ""}" data-ao-dept-filter="executive">📣 Ban Chỉ Huy (DEPT-00)</button>
                <button type="button" class="ao-dept-filter-btn${curFilter === "intelligence" ? " active" : ""}" data-ao-dept-filter="intelligence">🔎 Tình Báo &amp; Nội Dung (DEPT-01..04)</button>
                <button type="button" class="ao-dept-filter-btn${curFilter === "visual" ? " active" : ""}" data-ao-dept-filter="visual">🎨 Hình Ảnh &amp; VOX (DEPT-05..08)</button>
                <button type="button" class="ao-dept-filter-btn${curFilter === "post" ? " active" : ""}" data-ao-dept-filter="post">🎬 Dựng &amp; Xuất Bản (DEPT-09..10)</button>
                <button type="button" class="ao-dept-filter-btn${curFilter === "quality" ? " active" : ""}" data-ao-dept-filter="quality">⚖️ Pháp Y, QC &amp; Kỹ Thuật (DEPT-11..14)</button>
              </div>
            </div>
            <div class="ao-dept-banner-badges">
              <span>🏛️ <strong>${Number(dsum.total_departments || depts.length || 15)}</strong> Phòng Ban</span>
              <span>👑 <strong>${Number(dsum.total_leads || 15)}</strong> Tổ trưởng</span>
              <span>🛡️ <strong>${Number(dsum.total_deputies || 15)}</strong> Tổ phó</span>
              <span>⚡ <strong>${Number(dsum.total_specialists || 62)}</strong> Chuyên viên Mini-Agents</span>
              <span>👥 Tổng: <strong>${Number(dsum.total_personnel || 92)}</strong> Nhân sự</span>
            </div>
          </div>
          <div class="ao-dept-cards-list">
            ${filteredDepts.map((d) => renderDepartmentOrgCard(d, false)).join("")}
          </div>
        </div>
      `;
      return;
    }
    const divs = Array.isArray(snap.divisions) ? snap.divisions : [];
    const byId = {};
    divs.forEach((d) => {
      byId[d.id] = d;
    });

    function roomHtml(div, fullWidth) {
      if (!div) return "";
      const activeCls = div.active_count > 0 ? " room-active" : "";
      const fullCls = fullWidth ? " room-full" : "";
      const pillTxt = div.active_count > 0 ? `${div.active_count} đang hoạt động` : `${(div.agents || []).length} bàn trực`;
      return `
        <section class="ao-room${activeCls}${fullCls}" data-ao-room="${esc(div.id)}">
          <div class="ao-room-head">
            <div class="ao-room-title">
              <span style="font-size:18px;">${esc(div.icon || "🏢")}</span>
              <div>
                <strong>${esc(div.title_vi)}</strong>
                <small>${esc(div.subtitle_vi)}</small>
              </div>
            </div>
            <span class="ao-room-pill">${esc(pillTxt)}</span>
          </div>
          <div class="ao-desks-grid">
            ${(div.agents || []).map(renderDeskCard).join("")}
          </div>
        </section>
      `;
    }

    host.innerHTML = `
      <svg class="ao-links-svg" id="agentOfficeLinksSvg"></svg>
      <div class="ao-rooms-row">
        ${roomHtml(byId.direction, false)}
        ${roomHtml(byId.editorial, false)}
      </div>
      <div class="ao-rooms-row">
        ${roomHtml(byId.visual_cinema, true)}
      </div>
      <div class="ao-rooms-row">
        ${roomHtml(byId.quality_and_engineering, true)}
      </div>
    `;

    requestAnimationFrame(() => drawFloorplanLinks(snap.links || []));
  }

  function drawFloorplanLinks(links) {
    const canvas = document.getElementById("agentOfficeFloorplanCanvas");
    const svg = document.getElementById("agentOfficeLinksSvg");
    if (!canvas || !svg) return;

    const cRect = canvas.getBoundingClientRect();
    if (!cRect.width || !cRect.height) return;
    svg.setAttribute("viewBox", `0 0 ${Math.round(cRect.width)} ${Math.round(cRect.height)}`);

    const paths = [];
    (links || []).forEach((lnk) => {
      const fromEl = canvas.querySelector(`[data-ao-agent="${CSS.escape(lnk.from)}"]`);
      const toEl = canvas.querySelector(`[data-ao-agent="${CSS.escape(lnk.to)}"]`);
      if (!fromEl || !toEl) return;
      const r1 = fromEl.getBoundingClientRect();
      const r2 = toEl.getBoundingClientRect();
      const x1 = r1.left - cRect.left + r1.width / 2;
      const y1 = r1.top - cRect.top + r1.height / 2;
      const x2 = r2.left - cRect.left + r2.width / 2;
      const y2 = r2.top - cRect.top + r2.height / 2;
      const cx = (x1 + x2) / 2;
      const cy = Math.min(y1, y2) - 24;
      paths.push(
        `<path class="ao-link-line kind-${esc(lnk.kind)}" d="M ${x1.toFixed(1)} ${y1.toFixed(1)} Q ${cx.toFixed(1)} ${cy.toFixed(1)} ${x2.toFixed(1)} ${y2.toFixed(1)}" />`
      );
    });
    svg.innerHTML = paths.join("");
  }

  // Fixed 4-Room Layout — Permanently locked positions for all 15 Departments (92 Personnel)
  const FIXED_MINI_ROOMS = [
    { id: "direction", titleVi: "🏛️ Ban Chỉ Huy & Phòng Tình Báo Radar (DEPT-00 · DEPT-01 · 12 NS)", cols: 2, agents: ["orchestrator", "radar"] },
    { id: "editorial", titleVi: "🖋️ Khối Hồ Sơ, Biên Kịch & Phòng Thu Voice (DEPT-02..04 · 18 NS)", cols: 3, agents: ["research", "script", "voice"] },
    { id: "cinema", titleVi: "🎨 Khối Hình Ảnh, Phòng VOX (8 NS), Dựng & SEO (DEPT-05..10 · 38 NS)", cols: 2, agents: ["visuals", "footage", "ai_visual", "vox", "edit", "seo"] },
    { id: "qa", titleVi: "⚖️ Khối Pháp Y QA, Duyệt Master & Kỹ Thuật (DEPT-11..14 · 24 NS)", cols: 2, agents: ["evidence_qa", "qc", "dev", "debug"] },
  ];

  function formatStepElapsed() {
    if (!aoState.activeStepStartedMs) return "LIVE";
    const sec = Math.max(0, Math.floor((Date.now() - aoState.activeStepStartedMs) / 1000));
    const mm = String(Math.floor(sec / 60)).padStart(2, "0");
    const ss = String(sec % 60).padStart(2, "0");
    return `${mm}:${ss}s`;
  }

  function tickLiveElapsedClocks() {
    if (!aoState.open) return;
    const txt = formatStepElapsed();
    document.querySelectorAll("[data-ao-live-clock]").forEach((el) => {
      el.textContent = txt;
    });
  }

  function renderMiniFixedDesk(ag, snap) {
    const prof = CHIBI_PROFILES[ag.id] || CHIBI_PROFILES.orchestrator;
    const dept = ag.department_hierarchy || {};
    const lead = ag.lead || dept.lead || {};
    const deputy = ag.deputy || dept.deputy || {};
    const specs = Array.isArray(ag.specialists) ? ag.specialists : Array.isArray(dept.specialists) ? dept.specialists : [];
    const specCount = specs.length || 4;
    const headcount = dept.headcount || ag.headcount || 2 + specCount;
    const deptCode = dept.code || ag.dept_code || prof.deptCode || "DEPT";
    const deptName = dept.name_vi || ag.dept_name_vi || prof.nickVi || ag.title_vi;
    const st = ag.live_state || "standby";
    const isSel = aoState.selectedAgentId === ag.id || aoState.focusedAgentId === ag.id;
    const liveTel = aoState.livePhaseTelemetry;
    const isLive = st === "working" || st === "critiquing" || st === "reworking";

    let lineHtml = "";
    let metaHtml = "";
    let barHtml = "";

    const hierarchyLine = `
      <div class="ao-mini-dept-roles">
        <span>👑 <code>${esc(lead.handle || `@${ag.id}_lead`)}</code></span>
        <span>🛡️ <code>${esc(deputy.handle || `@${ag.id}_deputy`)}</code></span>
        <span>⚡ <strong>${specCount} CV</strong>${ag.active_mini_agent_handle ? ` (${esc(ag.active_mini_agent_handle)})` : ""}</span>
      </div>
    `;

    if (isLive) {
      let liveLine = "";
      if (liveTel && liveTel.byAgent && liveTel.byAgent[ag.id]) {
        liveLine = liveTel.byAgent[ag.id];
      } else if (liveTel && liveTel.agentId === ag.id && liveTel.detailVi) {
        liveLine = liveTel.detailVi;
      } else if (ag.live_bubble && !ag.live_bubble.includes("C:\\Users\\")) {
        liveLine = ag.live_bubble;
      } else {
        liveLine = ag.status_label_vi || "Đang thực thi dây chuyền trực tiếp…";
      }

      if (liveTel && (liveTel.agentId === ag.id || ag.id === "orchestrator") && liveTel.total > 0) {
        barHtml = `<div class="ao-roster-progress"><div class="ao-roster-progress-fill" style="width:${Math.max(4, liveTel.pct)}%;"></div></div>`;
      }

      const stepBadge = liveTel && liveTel.stepIndex > 0 ? `Bước #${liveTel.stepIndex}` : "Đang chạy";
      lineHtml = `<div class="ao-mini-live-line">${esc(liveLine)}</div>`;
      metaHtml = `
        <div class="ao-mini-meta">
          <span><i class="ao-mini-pulse"></i>${esc(stepBadge)} · <span data-ao-live-clock="1">${formatStepElapsed()}</span></span>
          <div style="display:flex;gap:4px;">
            <button type="button" class="ao-roster-doc-btn" data-ao-dispatch-handle="@${esc(ag.id)}" title="Điều phối Phòng @${esc(ag.id)}">📨</button>
            <button type="button" class="ao-roster-doc-btn" data-ao-open-charter="${esc(ag.id)}" title="Mở chi tiết 3 tầng @${esc(ag.id)}">📜</button>
          </div>
        </div>
      `;
    } else if (st === "done") {
      const owned = getAgentOwnedGates(ag.id, snap);
      const proofs = [];
      owned.forEach((g) => (g.proof_items || []).forEach((p) => proofs.push(p)));
      const doneTxt = ag.completed_badge || proofs[0] || "Đã ký duyệt & bàn giao";
      lineHtml = `<div class="ao-mini-quiet-line">✓ ${esc(doneTxt)}</div>`;
      metaHtml = `
        <div class="ao-mini-meta" style="color:#7dd3fc;">
          ${ag.rework_badge ? `<span class="ao-mini-rework-tag">🔄 ${esc(ag.rework_badge)}</span>` : `<span>✓ Tổ trưởng đã duyệt</span>`}
          <div style="display:flex;gap:4px;">
            <button type="button" class="ao-roster-doc-btn" data-ao-dispatch-handle="@${esc(ag.id)}" title="Điều phối Phòng @${esc(ag.id)}">📨</button>
            <button type="button" class="ao-roster-doc-btn" data-ao-open-charter="${esc(ag.id)}" title="Mở chi tiết 3 tầng @${esc(ag.id)}">📜</button>
          </div>
        </div>
      `;
    } else {
      lineHtml = `<div class="ao-mini-quiet-line">${esc(ag.wait_hint_vi || "Trực chiến chờ lệnh")}</div>`;
      metaHtml = `
        <div class="ao-mini-meta">
          <span>👥 ${headcount} NS sẵn sàng</span>
          <div style="display:flex;gap:4px;">
            <button type="button" class="ao-roster-doc-btn" data-ao-dispatch-handle="@${esc(ag.id)}" title="Điều phối Phòng @${esc(ag.id)}">📨</button>
            <button type="button" class="ao-roster-doc-btn" data-ao-open-charter="${esc(ag.id)}" title="Mở chi tiết 3 tầng @${esc(ag.id)}">📜</button>
          </div>
        </div>
      `;
    }

    return `
      <div class="ao-mini-desk md-${esc(st)}${isSel ? " is-selected" : ""}" data-ao-agent="${esc(ag.id)}" title="Bấm để xem Chi tiết Phòng ${esc(deptCode)} @${esc(ag.id)}">
        <div class="ao-mini-top">
          <div class="ao-mini-who">
            <div class="ao-mini-ico">${prof.prop || esc(ag.emoji || "🏛️")}</div>
            <div class="ao-mini-title">
              <strong>${esc(deptCode)} · ${esc(deptName)}</strong>
              <span>@${esc(ag.id)} · ${headcount} NS (1 Trưởng · 1 Phó · ${specCount} CV)</span>
            </div>
          </div>
          <div class="ao-mini-mon"><i></i><i></i><i></i></div>
        </div>
        ${hierarchyLine}
        ${lineHtml}
        ${barHtml}
        ${metaHtml}
      </div>
    `;
  }

  async function renderInspector(snap, forceRebuild) {
    const host = document.getElementById("agentOfficeInspectorBody");
    if (!host || !snap) return;

    document.querySelectorAll("[data-ao-tab]").forEach((btn) => {
      btn.classList.toggle("active", btn.getAttribute("data-ao-tab") === aoState.activeTab);
    });

    const agents = Array.isArray(snap.agents) ? snap.agents : [];
    const gates = Array.isArray(snap.critique_gates) ? snap.critique_gates : [];
    const evs = Array.isArray(snap.live_events) ? snap.live_events : [];
    const handoffs = Array.isArray(snap.nexus_handoffs) ? snap.nexus_handoffs : [];
    const liveTel = aoState.livePhaseTelemetry;
    const inspectorSig = [
      aoState.activeTab,
      aoState.selectedAgentId,
      aoState.focusedAgentId,
      snap.selected_job?.id || "",
      snap.selected_job?.current_phase || "",
      liveTel?.stepIndex || 0,
      liveTel?.pct || 0,
      liveTel?.detailVi || "",
      agents.map((a) => `${a.id}:${a.live_state}:${a.active_mini_agent_handle || ""}:${a.live_bubble || ""}:${a.completed_badge || ""}`).join(","),
      gates.map((g) => `${g.phase}:${g.gate_state}:${(g.proof_items || []).length}:${(g.rounds || []).length}`).join(","),
      evs.length,
      evs[0]?.summary || "",
      handoffs.length,
    ].join("|");

    if (!forceRebuild && aoState._lastInspectorSig === inspectorSig && host.children.length > 0) {
      return;
    }
    aoState._lastInspectorSig = inspectorSig;

    if (aoState.activeTab === "chat") {
      host.innerHTML = renderGroupChatPanelHtml(snap, false);
      return;
    }

    if (aoState.activeTab === "roster") {
      const byId = {};
      agents.forEach((a) => {
        byId[a.id] = a;
      });
      const activeCnt = agents.filter((a) => ["working", "critiquing", "reworking"].includes(a.live_state)).length;
      const doneCnt = agents.filter((a) => a.live_state === "done").length;
      const stepNote = liveTel && liveTel.stepIndex > 0 ? `⚡ Lệnh thật #${liveTel.stepIndex}` : "92 Nhân sự · 15 Phòng Ban";

      host.innerHTML = `
        <div class="ao-roster-summary-bar">
          <span>🟢 <strong>${activeCnt}</strong> Phòng sáng đèn · ✅ <strong>${doneCnt}</strong> Phòng đã xong · 15 Phòng Ban (92 NS)</span>
          <small style="color:#6ee7b7;font-family:'JetBrains Mono',monospace;">${esc(stepNote)}</small>
        </div>
        ${FIXED_MINI_ROOMS.map((rm) => {
          const rmAgents = rm.agents.map((id) => byId[id]).filter(Boolean);
          const rmLive = rmAgents.filter((a) => ["working", "critiquing", "reworking"].includes(a.live_state)).length;
          const isOpen = aoState.miniRoomOpen ? aoState.miniRoomOpen[rm.id] !== false : true;
          const pill = rmLive > 0 ? `🟢 ${rmLive} Phòng đang chạy` : `${rmAgents.length} Phòng Ban`;
          return `
            <section class="ao-fixed-room${rmLive > 0 ? " room-live" : ""}${isOpen ? "" : " is-collapsed"}">
              <div class="ao-fixed-room-head" data-ao-toggle-mini-room="${esc(rm.id)}" title="Bấm để Thu gọn / Mở rộng khối phòng này">
                <strong>${rm.titleVi}</strong>
                <div style="display:flex;align-items:center;gap:6px;">
                  <span class="ao-fixed-room-pill">${pill}</span>
                  <span class="ao-rz-collapse-toggle-pill" style="padding:2px 7px;font-size:9.5px;">${isOpen ? "▴" : "▾"}</span>
                </div>
              </div>
              <div class="ao-fixed-grid${rm.cols === 3 ? " cols-3" : ""}" style="${isOpen ? "" : "display:none;"}">
                ${rmAgents.map((a) => renderMiniFixedDesk(a, snap)).join("")}
              </div>
            </section>
          `;
        }).join("")}
      `;
      return;
    }

    if (aoState.activeTab === "departments") {
      const depts = Array.isArray(snap.departments) ? snap.departments : [];
      const dsum = snap.departments_summary || {};
      const activeId = aoState.focusedAgentId || aoState.selectedAgentId || "vox";
      const spotlightDept = depts.find((d) => d.agent_id === activeId) || depts.find((d) => d.agent_id === "vox") || depts[0];
      const otherDepts = depts.filter((d) => d && d.agent_id !== spotlightDept?.agent_id);

      const matrixPillsHtml = depts
        .map((d) => {
          const isCur = d.agent_id === spotlightDept?.agent_id;
          const isVox = d.agent_id === "vox";
          const num = String(d.code || "DEPT-00").replace("DEPT-", "");
          const p = CHIBI_PROFILES[d.agent_id] || {};
          return `
            <button type="button"
                    class="ao-dock-matrix-pill${isCur ? " active" : ""}${isVox ? " is-vox" : ""}"
                    data-ao-select-dept-dock="${esc(d.agent_id)}"
                    title="${esc(d.code)} · ${esc(d.name_vi)} (${d.headcount || 6} NS)">
              <span class="ao-dock-pill-code">${esc(num)}</span>
              <span class="ao-dock-pill-name">${p.prop || d.emoji || "🏛️"} ${esc(p.shortTitleVi || d.name_vi)}</span>
            </button>
          `;
        })
        .join("");

      const compactDirectoryHtml = otherDepts
        .map((d) => {
          const p = CHIBI_PROFILES[d.agent_id] || {};
          const r = getMergedDeptRoster(d.agent_id, snap);
          return `
            <div class="ao-dock-compact-row" data-ao-select-dept-dock="${esc(d.agent_id)}">
              <div class="ao-dock-compact-left">
                <span class="ao-dept-code">${esc(d.code)}</span>
                <strong>${p.prop || d.emoji || "🏛️"} ${esc(p.shortTitleVi || d.name_vi)}</strong>
                <small>👥 ${r.headcount} NS (👑 ${esc(r.lead.handle)} · 🛡️ ${esc(r.deputy.handle)} · ⚡${r.specialists.length} Lô)</small>
              </div>
              <button type="button" class="ao-dispatch-chip" data-ao-dispatch-handle="@${esc(d.agent_id)}">📨 @${esc(d.agent_id)}</button>
            </div>
          `;
        })
        .join("");

      host.innerHTML = `
        <div class="ao-roster-summary-bar">
          <span>🏛️ <strong>${Number(dsum.total_departments || depts.length || 15)}</strong> Phòng · <strong>${Number(dsum.total_personnel || 92)}</strong> Nhân sự</span>
          <small style="color:#6ee7b7;font-family:'JetBrains Mono',monospace;">15 👑 · 15 🛡️ · 62 ⚡</small>
        </div>
        <div class="ao-dock-matrix-box">
          <div class="ao-dock-matrix-label">🎯 CHỌN NHANH PHÒNG BAN TRÊN SƠ ĐỒ 3×5 (15 PHÒNG):</div>
          <div class="ao-dock-matrix-grid">
            ${matrixPillsHtml}
          </div>
        </div>
        <div class="ao-dept-inspector-list">
          ${spotlightDept ? renderDepartmentOrgCard(spotlightDept, true) : ""}
        </div>
        <div class="ao-dock-directory-box">
          <div class="ao-dock-matrix-label" data-ao-toggle-other-depts="1" style="display:flex;align-items:center;justify-content:space-between;cursor:pointer;user-select:none;" title="Bấm để Thu gọn / Mở rộng danh bạ 14 phòng ban khác">
            <span>📋 DANH BẠ CÁC PHÒNG BAN KHÁC (CLICK ĐỂ XEM CHI TIẾT 3 TẦNG):</span>
            <span class="ao-rz-collapse-toggle-pill" style="padding:2px 8px;font-size:9.5px;">${aoState.otherDeptsDirectoryOpen !== false ? "Thu gọn ▴" : "Mở rộng ▾"}</span>
          </div>
          <div class="ao-dock-compact-list" style="${aoState.otherDeptsDirectoryOpen !== false ? "" : "display:none;"}">
            ${compactDirectoryHtml}
          </div>
        </div>
      `;
      return;
    }

    if (aoState.activeTab === "critique") {
      const gates = Array.isArray(snap.critique_gates) ? snap.critique_gates : [];
      const liveTel = aoState.livePhaseTelemetry;
      host.innerHTML = `
        <div style="margin-bottom:10px;padding:9px 11px;border-radius:10px;background:rgba(14,116,144,0.16);border:1px solid rgba(56,189,248,0.28);font-size:11.5px;color:#cbd5e1;line-height:1.45;">
          <strong style="color:#f8fafc;">Cơ chế Chốt Chặn Phản Biện Liên Phòng Thật 100%:</strong> Mọi công đoạn đều có cặp <code>Phòng Ban Sản Xuất (Maker Department)</code> ↔ <code>Phòng Pháp Y &amp; Kiểm Định (@evidence_qa / @qc)</code>. Tổ phó rà checklist nội bộ trước khi Tổ trưởng ký duyệt nộp qua Cổng Phản Biện.
        </div>
        <div class="ao-gate-list">
          ${gates
            .map((g) => {
              const coTxt = (g.co_agents || []).length ? ` + ${g.co_agents.map((c) => `@${c}`).join(", ")}` : "";
              const summaryTxt =
                liveTel && liveTel.phase === g.phase && liveTel.detailVi
                  ? liveTel.detailVi
                  : g.summary_vi;
              const pctBar =
                liveTel && liveTel.phase === g.phase
                  ? `<div class="ao-roster-progress" style="margin:7px 0 2px;"><div class="ao-roster-progress-fill" style="width:${Math.max(4, liveTel.pct)}%;"></div></div>`
                  : "";
              const proofs = (g.proof_items || []).length
                ? `<ul class="ao-proof-list">${g.proof_items.map((p) => `<li>${esc(p)}</li>`).join("")}</ul>`
                : "";
              const roundsHtml = (g.rounds || []).length
                ? `<div class="ao-rounds-box">${g.rounds
                    .map(
                      (r) =>
                        `<div><strong>Vòng ${esc(r.round)} (${esc(r.verdict)}):</strong> ${esc(r.summary)}${
                          r.applied ? ` — <em>Đã sửa ${esc(r.applied)} điểm</em>` : ""
                        }</div>`
                    )
                    .join("")}</div>`
                : "";
              return `
                <article class="ao-gate-card gate-${esc(g.gate_state)}">
                  <div class="ao-gate-head">
                    <div>
                      <strong>${esc(g.label_vi)}</strong>
                      <div class="ao-gate-pair">Phòng Sản Xuất: <code>@${esc(g.maker_agent)}</code>${esc(coTxt)} → Phòng Kiểm Định: <code>@${esc(g.critic_agent)}</code></div>
                    </div>
                    <span class="ao-gate-badge">${esc(g.badge_vi)}</span>
                  </div>
                  <p class="ao-gate-summary">${esc(summaryTxt)}</p>
                  ${pctBar}
                  ${proofs}
                  ${roundsHtml}
                </article>
              `;
            })
            .join("")}
        </div>
      `;
      return;
    }

    if (aoState.activeTab === "events") {
      const evs = Array.isArray(snap.live_events) ? snap.live_events : [];
      const handoffs = Array.isArray(snap.nexus_handoffs) ? snap.nexus_handoffs : [];
      const handoffHtml = handoffs.length
        ? `<div style="margin-bottom:10px;">
            <div style="font-size:11px;font-weight:800;color:#6ee7b7;margin-bottom:6px;">📦 GÓI BÀN GIAO LIÊN PHÒNG BAN (NEXUS LEDGER)</div>
            ${handoffs
              .slice()
              .reverse()
              .map(
                (h) => `
                <div class="ao-event-item" style="border-color:rgba(52,211,153,0.35);margin-bottom:6px;">
                  <div class="ao-event-top">
                    <span class="ao-event-agent">📤 Phòng @${esc(h.from_agent)} ➔ Phòng @${esc(h.to_agent)}</span>
                    <span class="ao-event-meta">QA: ${esc(h.qa_gate_verdict)}</span>
                  </div>
                  <div>Chuyển giao từ bước <strong>${esc(h.from_phase)}</strong> sang <strong>${esc(h.to_phase)}</strong></div>
                </div>`
              )
              .join("")}
          </div>`
        : "";

      host.innerHTML = `
        ${handoffHtml}
        <div style="font-size:11px;font-weight:800;color:#7dd3fc;margin-bottom:6px;">⚡ NHẬT KÝ CÔNG CỤ 15 PHÒNG BAN ĐANG GỌI TRỰC TIẾP</div>
        <div class="ao-event-list">
          ${
            evs.length
              ? evs
                  .map(
                    (e) => `
                  <div class="ao-event-item${e.active ? " is-active" : ""}">
                    <div class="ao-event-top">
                      <span class="ao-event-agent">Phòng @${esc(e.agent_id)} · ${esc(e.phase || "studio")}</span>
                      <span class="ao-event-meta">${esc(e.tool)} · ${esc(e.status)}</span>
                    </div>
                    <div class="ao-event-target">${esc(e.summary)}</div>
                  </div>`
                  )
                  .join("")
              : `<div class="ao-event-item">Các bước Python/GPU nội bộ của 15 Phòng Ban báo tiến độ trực tiếp trên từng thẻ Phòng Ban &amp; Cổng Kiểm Duyệt.</div>`
          }
        </div>
      `;
      return;
    }

    // Tab: "charter" — Full 3-Tier Department Detail & Quick Dispatch Inspector
    const agentId = aoState.selectedAgentId || "vox";
    const ag = (snap.agents || []).find((a) => a.id === agentId) || (snap.agents || [])[0];
    const allDepts = Array.isArray(snap.departments) ? snap.departments : [];
    host.innerHTML = `<div class="ao-charter-card">Đang tải hồ sơ Phòng Ban <strong>@${esc(agentId)}</strong>…</div>`;
    const charter = await fetchAgentCharter(agentId);
    if (!ag) return;

    const perms = charter?.permissions || ag.permissions || {};
    const skills = charter?.bound_skills || ag.bound_skills || [];
    const deptHierarchy =
      ag.department_hierarchy ||
      charter?.department_hierarchy ||
      allDepts.find((d) => d.agent_id === agentId) ||
      {};
    const lead = deptHierarchy.lead || ag.lead || {};
    const deputy = deptHierarchy.deputy || ag.deputy || {};
    const specs = Array.isArray(deptHierarchy.specialists)
      ? deptHierarchy.specialists
      : Array.isArray(ag.specialists)
      ? ag.specialists
      : [];

    const deptSelectorPills = allDepts
      .map(
        (d) =>
          `<button type="button" class="ao-dept-picker-pill${d.agent_id === agentId ? " active" : ""}" data-ao-open-charter="${esc(d.agent_id)}">${esc(d.code)} ${esc(d.handle)}</button>`
      )
      .join("");

    const deptHtml = deptHierarchy && deptHierarchy.code
      ? `<div style="margin:10px 0;">${renderDepartmentOrgCard(deptHierarchy, false)}</div>`
      : "";

    host.innerHTML = `
      <div class="ao-charter-card">
        <div class="ao-dept-picker-strip" aria-label="Chọn nhanh 1 trong 15 Phòng Ban">
          ${deptSelectorPills}
        </div>

        <div class="ao-charter-dispatch-panel">
          <div style="font-size:11px;font-weight:800;color:#67e8f9;margin-bottom:6px;">
            📨 ĐIỀU PHỐI NHANH PHÒNG BAN (${esc(deptHierarchy.code || "DEPT")} · ${esc(deptHierarchy.name_vi || ag.title_vi)}) VÀO HỘP CHAT
          </div>
          <div class="ao-charter-dispatch-chips">
            <button type="button" class="ao-dispatch-btn primary" data-ao-dispatch-handle="@${esc(ag.id)}">🏛️ Cả Phòng @${esc(ag.id)}</button>
            <button type="button" class="ao-dispatch-btn" data-ao-dispatch-handle="${esc(lead.handle || `@${ag.id}_lead`)}">👑 Tổ trưởng ${esc(lead.handle || `@${ag.id}_lead`)}</button>
            <button type="button" class="ao-dispatch-btn" data-ao-dispatch-handle="${esc(deputy.handle || `@${ag.id}_deputy`)}">🛡️ Tổ phó ${esc(deputy.handle || `@${ag.id}_deputy`)}</button>
            ${specs
              .map(
                (sp, idx) =>
                  `<button type="button" class="ao-dispatch-chip" data-ao-dispatch-handle="${esc(sp.handle)}" title="${esc(sp.title_vi)}">⚡ B${idx + 1} ${esc(sp.handle)}</button>`
              )
              .join("")}
          </div>
          <div class="ao-charter-custom-cmd">
            <input type="text" id="aoCharterQuickCmdInput" class="ao-charter-cmd-input" placeholder="Nhập yêu cầu cụ thể cho @${esc(ag.id)} / ${esc(lead.handle || `@${ag.id}_lead`)}…" />
            <button type="button" class="ao-dispatch-btn primary" data-ao-quick-send="@${esc(ag.id)}">Gửi sang Chat ↵</button>
          </div>
        </div>

        ${deptHtml}

        <div style="font-size:11px;color:#94a3b8;line-height:1.6;padding:8px 10px;border-radius:8px;background:rgba(15,23,42,0.65);border:1px solid rgba(148,163,184,0.16);margin-bottom:10px;">
          <div><strong>Tệp hiến chương gốc:</strong> <code>${esc(ag.source_file || `agents/${ag.id}.md`)}</code></div>
          <div><strong>Trạng thái Phòng Ban:</strong> <span style="color:#6ee7b7;">${esc(ag.status_label_vi)}</span></div>
          <div><strong>Quyền ghi thư mục (Least-Privilege):</strong> <code>${esc((perms.write_dirs || []).join(", ") || "Chỉ đọc (Read-Only)")}</code></div>
          <div><strong>Hành động được cấp phép:</strong> <code>${esc((perms.allowed_actions || []).join(", ") || "inspect")}</code></div>
          <div><strong>Kỹ năng gắn kèm:</strong> <code>${esc(skills.join(", ") || "Mặc định")}</code></div>
        </div>
        ${
          charter?.body_markdown
            ? `<pre class="ao-charter-pre">${esc(charter.body_markdown)}</pre>`
            : ""
        }
      </div>
    `;
  }

  function buildInstantFallbackSnapshot() {
    const agents = Object.keys(CHIBI_PROFILES).map((id) => {
      const p = CHIBI_PROFILES[id];
      const r = getMergedDeptRoster(id, null);
      return {
        id,
        name: p.shortTitleVi,
        title_vi: p.nickVi,
        dept_code: p.deptCode,
        dept_name_vi: p.shortTitleVi,
        emoji: p.prop,
        live_state: "standby",
        status_label_vi: "Trực chiến 100%",
        wait_hint_vi: `👥 ${r.headcount} nhân sự trực chiến sẵn sàng`,
        headcount: r.headcount,
        lead: r.lead,
        deputy: r.deputy,
        specialists: r.specialists,
        department_hierarchy: r,
      };
    });
    const departments = Object.keys(CHIBI_PROFILES).map((id) => {
      const p = CHIBI_PROFILES[id];
      const r = getMergedDeptRoster(id, null);
      return {
        agent_id: id,
        code: p.deptCode,
        handle: `@${id}`,
        name_vi: p.shortTitleVi,
        emoji: p.prop,
        color: p.hatColor,
        division: p.zone === "direction" ? "executive" : p.zone === "editorial" ? "intelligence" : p.zone === "cinema" ? "visual" : "quality",
        department_state: "standby",
        headcount: r.headcount,
        lead: r.lead,
        deputy: r.deputy,
        specialists: r.specialists,
      };
    });
    return {
      status: "ok",
      summary: {
        total_departments: 15,
        total_personnel: 92,
        total_leads: 15,
        total_deputies: 15,
        total_specialists: 62,
        active_agents_count: 1,
        passed_gates: 0,
        total_gates: 8,
      },
      departments_summary: {
        total_departments: 15,
        total_personnel: 92,
        total_leads: 15,
        total_deputies: 15,
        total_specialists: 62,
      },
      live_phase_report: {
        phase: "plan",
        phase_label_vi: "Đang kết nối dữ liệu dự án đang chạy…",
        primary_agent_id: "research",
        is_running: true,
        step_index: 1,
        percent: 15,
        eta_vi: "Đang tải trạng thái thời gian thực từ Workspace…",
        current_action_vi: "Đang đồng bộ tiến độ thực tế của dự án hiện tại…",
        milestones: [],
      },
      agents,
      departments,
      critique_gates: [],
      links: [],
    };
  }

  async function refreshOffice(forceInspector) {
    if (aoState.fetching) {
      aoState.pendingRefresh = true;
      aoState.pendingRefreshForce = Boolean(aoState.pendingRefreshForce || forceInspector);
      if (aoState.open) {
        const instantSnap = aoState.snapshot || buildInstantFallbackSnapshot();
        renderKpis(instantSnap);
        renderFloorplan(instantSnap);
        if (forceInspector) renderInspector(instantSnap);
      }
      return;
    }
    aoState.fetching = true;
    try {
      const globalJobId = currentAppSelectedJobId();
      if (globalJobId && globalJobId !== aoState.lastGlobalSelectedJobId) {
        aoState.lastGlobalSelectedJobId = globalJobId;
        // When the main app switches project (e.g. a new job starts), release any stale pin
        aoState.userPinnedJobId = "";
        aoState.selectedJobId = "";
      }
      const isPinned = Boolean(aoState.userPinnedJobId);
      const targetJob = isPinned ? aoState.userPinnedJobId : globalJobId;
      const snap = await fetchOfficeSnapshot(targetJob, isPinned);
      const resolvedJobId = snap?.selected_job?.id || targetJob || "";
      if (resolvedJobId && resolvedJobId !== aoState.lastActiveJobId) {
        aoState.lastActiveJobId = resolvedJobId;
        aoState._lastKpiSig = "";
        aoState.livePhaseTelemetry = null;
      }
      window.__cofiAgentOfficeActiveJobId = resolvedJobId;
      aoState.snapshot = snap;
      updateTriggerButtons(snap);

      if (aoState.open) {
        const stamp = document.getElementById("agentOfficeLiveStamp");
        if (stamp) {
          const now = new Date();
          stamp.textContent = `LIVE · ${now.toLocaleTimeString("vi-VN", { hour12: false })}`;
        }
        renderJobPicker(snap);
        renderKpis(snap);
        renderFloorplan(snap);
        if (aoState.focusedAgentId) {
          renderFocusReplyOverlay();
        }
        if (forceInspector || aoState.activeTab !== "charter") {
          await renderInspector(snap, Boolean(forceInspector));
        }

        const effJobId = snap.selected_job?.id || targetJob;
        const curPhase = snap.selected_job?.current_phase || "";
        aoState.livePhaseTelemetry = await fetchLivePhaseTelemetry(effJobId, curPhase);
        renderLiveStatusBar(snap);

        // Hot-reconcile edit_manifest.json beat counts into critique_gates so continuous mode never shows stale 0/total
        const emSum = aoState.livePhaseTelemetry?.editManifestSummary;
        if (emSum && emSum.doneBeats > 0 && Array.isArray(snap.critique_gates)) {
          const editGate = snap.critique_gates.find((g) => g && g.phase === "edit");
          if (editGate) {
            const realLine = `Tiến độ dựng Timeline Remotion: ${emSum.doneBeats}/${emSum.totalBeats || emSum.doneBeats} phân cảnh`;
            const mixLine =
              emSum.realFootage || emSum.voxBeats
                ? `Phân bổ thị giác: ${emSum.realFootage} cảnh tư liệu thật (${emSum.uniqueClips} clip sạch) · ${emSum.voxBeats} cảnh Motion Vox 2.5D`
                : "";
            const prevProofs = Array.isArray(editGate.proof_items) ? editGate.proof_items : [];
            const cleaned = prevProofs.filter(
              (p) => !String(p).startsWith("Tiến độ dựng Timeline Remotion:") && !String(p).startsWith("Phân bổ thị giác:")
            );
            editGate.proof_items = [realLine, ...(mixLine ? [mixLine] : []), ...cleaned];
          }
        }
      }
    } catch (_err) {
      const stamp = document.getElementById("agentOfficeLiveStamp");
      if (stamp && aoState.open) stamp.textContent = "Đang kết nối lại…";
    } finally {
      aoState.fetching = false;
      if (aoState.pendingRefresh) {
        const nextForce = aoState.pendingRefreshForce;
        aoState.pendingRefresh = false;
        aoState.pendingRefreshForce = false;
        setTimeout(() => refreshOffice(nextForce), 40);
      }
    }
  }

  function openAgentOffice() {
    const dlg = document.getElementById("agentOfficeDialog");
    if (!dlg) return;
    aoState.open = true;
    aoState.manualOverviewLock = false;
    aoState.manualZoomOutKey = "";
    const globalJobId = currentAppSelectedJobId();
    if (globalJobId && globalJobId !== aoState.lastGlobalSelectedJobId) {
      aoState.lastGlobalSelectedJobId = globalJobId;
      aoState.userPinnedJobId = "";
      aoState.selectedJobId = "";
    }
    if (typeof dlg.showModal === "function" && !dlg.open) {
      dlg.showModal();
    } else {
      dlg.setAttribute("open", "open");
    }
    // Mount 15 Department Team Pods × 92 Personnel immediately (0ms delay!)
    const instantSnap =
      aoState.snapshot && (!globalJobId || aoState.snapshot.selected_job?.id === globalJobId)
        ? aoState.snapshot
        : buildInstantFallbackSnapshot();
    renderKpis(instantSnap);
    renderFloorplan(instantSnap);
    renderInspector(instantSnap, true);
    requestAnimationFrame(() => syncCameraTransform());
    refreshOffice(true);
    startSimulationLoop();
    if (aoState.pollTimer) clearInterval(aoState.pollTimer);
    aoState.pollTimer = setInterval(() => {
      if (!document.hidden) refreshOffice(false);
    }, 3200);
    if (aoState.liveClockTimer) clearInterval(aoState.liveClockTimer);
    aoState.liveClockTimer = setInterval(tickLiveElapsedClocks, 1000);
    if (aoState.bubbleTimer) clearInterval(aoState.bubbleTimer);
    aoState.bubbleTimer = setInterval(() => {
      if (document.hidden) return;
      aoState.bubbleTick += 1;
      if (aoState.open && aoState.snapshot && aoState.viewMode === "chibi") {
        refreshAllChibiBubbles(aoState.snapshot);
      }
    }, 4200);
  }

  function closeAgentOffice() {
    const dlg = document.getElementById("agentOfficeDialog");
    aoState.open = false;
    aoState.focusedAgentId = null;
    if (aoState.pollTimer) {
      clearInterval(aoState.pollTimer);
      aoState.pollTimer = null;
    }
    if (aoState.liveClockTimer) {
      clearInterval(aoState.liveClockTimer);
      aoState.liveClockTimer = null;
    }
    if (aoState.bubbleTimer) {
      clearInterval(aoState.bubbleTimer);
      aoState.bubbleTimer = null;
    }
    if (aoState.roamTimer) {
      clearInterval(aoState.roamTimer);
      aoState.roamTimer = null;
    }
    if (aoState.rafId) {
      cancelAnimationFrame(aoState.rafId);
      aoState.rafId = null;
    }
    if (dlg && dlg.open && typeof dlg.close === "function") {
      dlg.close();
    } else if (dlg) {
      dlg.removeAttribute("open");
    }
  }

  function ensureFloorSpecMonitorDrawer() {
    const dlg = document.getElementById("agentOfficeDialog") || document.body;
    let drawer = document.getElementById("aoSpecialistLiveMonitorDrawer");
    if (!drawer) {
      drawer = document.createElement("div");
      drawer.id = "aoSpecialistLiveMonitorDrawer";
      drawer.className = "ao-spec-monitor-backdrop";
      dlg.appendChild(drawer);
    }
    return drawer;
  }

  function openFloorSpecialistMonitor(deptId, memberKey) {
    const cleanDept = deptId && CHIBI_PROFILES[deptId] ? deptId : "vox";
    const prof = CHIBI_PROFILES[cleanDept] || CHIBI_PROFILES.vox;
    const roster = getMergedDeptRoster(cleanDept, aoState.snapshot);
    const mKey = memberKey || "lead";

    let roleBadge = "⚡ CHUYÊN VIÊN PHÂN LÔ SONG SONG (PARALLEL SPECIALIST)";
    let member = roster.lead;
    let laneLabel = `Đồng bộ ${roster.specialists.length} Luồng`;
    let batchId = "LÔ-ALL";
    let itemsLabel = "Toàn bộ dải Beat của Phòng";
    let workerThread = `cofi-parallel-${cleanDept}-master`;
    let elapsedMs = 28;
    let progressPct = 100;
    let findingVi = "";
    let artifactKey = "department_parallel_state.json";
    let handoffPair = `${roster.lead.handle} ➔ ${roster.deputy.handle}`;

    if (mKey === "lead") {
      roleBadge = "👑 TẦNG 1 · TỔ TRƯỞNG CHỈ HUY & KÝ DUYỆT (DEPARTMENT LEAD)";
      member = roster.lead;
      findingVi = `Tổ trưởng ${roster.lead.handle} chia ${roster.specialists.length} lô song song (${roster.speedup_factor}) và ký duyệt đầu ra của phòng ${roster.code}.`;
      artifactKey = roster.lead.approval_output_vi || "Master Sign-off";
    } else if (mKey === "deputy") {
      roleBadge = "🛡️ TẦNG 2 · TỔ PHÓ RÀ SOÁT CHECKLIST & HỢP NHẤT LÔ (DEPARTMENT DEPUTY)";
      member = roster.deputy;
      findingVi = `Tổ phó ${roster.deputy.handle} đối chiếu checklist nghiệm thu nội bộ trên toàn bộ ${roster.specialists.length}/${roster.specialists.length} lô chuyên viên.`;
      artifactKey = "Internal Checklist Gate (100%)";
    } else {
      const sp = roster.specialists.find((s) => s.id === mKey || s.handle === mKey) || roster.specialists[0];
      if (sp) {
        member = sp;
        laneLabel = `Lane #${sp.parallel_lane} / ${roster.specialists.length}`;
        batchId = sp.batch_id;
        itemsLabel = sp.items_label;
        workerThread = sp.worker_thread;
        elapsedMs = sp.elapsed_ms;
        progressPct = sp.progress_pct;
        findingVi = sp.finding_vi;
        artifactKey = sp.artifact_key;
        handoffPair = `📥 ${sp.input_from} ➔ 📤 ${sp.output_to}`;
      }
    }

    const checksHtml = (roster.deputy.checklist_vi || [])
      .map((c) => `<li>✓ ${esc(c)}</li>`)
      .join("");

    const teamSwitchHtml = [
      `<button type="button" class="ao-dispatch-chip${mKey === "lead" ? " is-selected-member" : ""}" data-ao-open-spec-monitor="${esc(cleanDept)}:lead">👑 ${esc(roster.lead.handle)}</button>`,
      `<button type="button" class="ao-dispatch-chip${mKey === "deputy" ? " is-selected-member" : ""}" data-ao-open-spec-monitor="${esc(cleanDept)}:deputy">🛡️ ${esc(roster.deputy.handle)}</button>`,
      ...roster.specialists.map(
        (sp) =>
          `<button type="button" class="ao-dispatch-chip${mKey === sp.id ? " is-selected-member" : ""}" data-ao-open-spec-monitor="${esc(cleanDept)}:${esc(sp.id)}">⚡ ${esc(sp.shortTag)} ${esc(sp.handle)}</button>`
      ),
    ].join("");

    const drawer = ensureFloorSpecMonitorDrawer();
    drawer.innerHTML = `
      <aside class="ao-spec-monitor-panel" role="dialog" aria-label="Màn Hình Giám Sát Nhân Sự">
        <header class="ao-spec-monitor-head">
          <div>
            <div style="font-size:10.5px;font-weight:800;color:#34d399;letter-spacing:0.04em;margin-bottom:4px;">${esc(roleBadge)}</div>
            <h4 style="margin:0 0 4px;font-size:15px;color:#f8fafc;">${esc(member.title_vi)} <code style="color:#38bdf8;font-size:13px;">${esc(member.handle)}</code></h4>
            <div style="font-size:11.5px;color:#94a3b8;">${prof.prop} ${esc(roster.code)} · ${esc(prof.shortTitleVi)} (${roster.headcount} Nhân sự · Tăng tốc ${esc(roster.speedup_factor)})</div>
          </div>
          <button type="button" class="icon-btn channel-profile-dialog-close" data-ao-close-spec-monitor="1" title="Đóng màn hình giám sát">×</button>
        </header>
        <div class="ao-spec-monitor-body">
          <div style="display:flex;flex-wrap:wrap;gap:5px;">
            ${teamSwitchHtml}
          </div>
          <div class="ao-spec-monitor-kv-grid">
            <div class="ao-spec-monitor-kv">
              <span>Luồng &amp; Mã Lô Song Song</span>
              <strong>⚡ ${esc(laneLabel)} · ${esc(batchId)}</strong>
            </div>
            <div class="ao-spec-monitor-kv">
              <span>Dải Beat Phụ Trách (Batch Scope)</span>
              <strong style="color:#fde68a;">🎯 ${esc(itemsLabel)}</strong>
            </div>
            <div class="ao-spec-monitor-kv">
              <span>Worker Thread &amp; Thời Gian</span>
              <strong style="color:#6ee7b7;">🧵 ${esc(workerThread)} (${Number(elapsedMs).toFixed(1)}ms)</strong>
            </div>
            <div class="ao-spec-monitor-kv">
              <span>Tiến Độ &amp; Tăng Tốc</span>
              <strong style="color:#38bdf8;">${progressPct}% · 🚀 ${esc(roster.speedup_factor)}</strong>
            </div>
          </div>

          <section class="ao-spec-monitor-section">
            <h5>📌 Nhiệm Vụ Chuyên Môn &amp; Luồng Bàn Giao</h5>
            <p style="margin:0 0 6px;font-size:12.5px;color:#f1f5f9;line-height:1.45;"><strong>Chuyên môn:</strong> ${esc(member.role_vi)}</p>
            <div style="font-size:11.5px;color:#93c5fd;font-family:'JetBrains Mono',monospace;">🔄 Bàn giao: ${esc(handoffPair)} · 📦 Đầu ra: <code>${esc(artifactKey)}</code></div>
          </section>

          <section class="ao-spec-monitor-section" style="border-color:rgba(52,211,153,0.4);">
            <h5>🔬 Báo Cáo Trực Chiến &amp; Checklist Nghiệm Thu Nội Bộ</h5>
            <p style="margin:0 0 8px;font-size:12.5px;color:#d1fae5;line-height:1.5;">${esc(findingVi)}</p>
            ${
              checksHtml
                ? `<div style="font-size:11.5px;color:#cbd5e1;"><strong>Checklist nghiệm thu (${esc(roster.deputy.handle)}):</strong><ul style="margin:5px 0 0;padding-left:18px;line-height:1.45;">${checksHtml}</ul></div>`
                : ""
            }
          </section>

          <section class="ao-spec-monitor-section">
            <h5>📨 Gửi Lệnh Điều Phối Trực Tiếp Cho ${esc(member.handle)}</h5>
            <div class="ao-spec-monitor-cmd-box">
              <input type="text" id="aoSpecMonitorCmdInput" class="ao-spec-monitor-cmd-input" value="Thực thi & kiểm tra lô ${esc(batchId)} (${esc(itemsLabel)}) — ${esc(member.title_vi)}" aria-label="Nhập lệnh điều phối riêng cho nhân sự" />
              <div style="display:flex;gap:8px;flex-wrap:wrap;">
                <button type="button" class="ao-parallel-cta-all-btn" style="padding:8px 14px;font-size:12px;" data-ao-send-spec-monitor-cmd="${esc(member.handle)}">📨 Gửi Lệnh Cho ${esc(member.handle)}</button>
                <button type="button" class="ao-pod-run-btn" style="padding:8px 12px;font-size:12px;" data-ao-dispatch-parallel-dept="${esc(cleanDept)}">⚡ Chạy Chia Lô Phòng ${esc(roster.code)} (${roster.specialists.length} Luồng)</button>
              </div>
            </div>
          </section>
        </div>
      </aside>
    `;
    drawer.classList.add("is-open");
  }

  function closeFloorSpecialistMonitor() {
    const drawer = document.getElementById("aoSpecialistLiveMonitorDrawer");
    if (drawer) drawer.classList.remove("is-open");
  }

  async function triggerFloorParallelDispatch(deptIdOrAll) {
    const target = deptIdOrAll || "all";
    aoState.parallelWaveActive = true;
    aoState.parallelWaveDept = target;
    const now = new Date();
    aoState.parallelLastWaveAt = now.toLocaleTimeString("vi-VN", { hour12: false });
    playStudioSound("focus");

    if (target !== "all" && CHIBI_PROFILES[target] && aoState.viewMode === "chibi") {
      focusChibiAgent(target, "lead", false);
    } else if (target === "all" && aoState.autoZoomActiveRoom && !aoState.focusedAgentId && aoState.viewMode === "chibi") {
      const targetZoom = resolvePrimaryWorkingDepartment(aoState.snapshot) || aoState.selectedAgentId || "vox";
      focusChibiAgent(targetZoom, "lead", true);
    }

    const waveBtn = document.getElementById("aoFloorParallelWaveBtn");
    if (waveBtn) {
      waveBtn.classList.add("is-dispatching");
      waveBtn.textContent = "⚡ Đang chạy 62 luồng Chuyên viên song song (15 Phòng · 92 NS)…";
    }
    if (aoState.snapshot) {
      syncChibiStageWithSnapshot(aoState.snapshot);
    }

    try {
      const jobId = aoState.selectedJobId || currentAppSelectedJobId();
      const resp = await fetch("/api/agent-departments/dispatch-parallel", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ dept_id: target, job_id: jobId }),
      });
      if (resp.ok) {
        const data = await resp.json();
        if (aoState.snapshot && Array.isArray(data.departments) && data.departments.length) {
          aoState.snapshot.departments = data.departments;
        }
      }
    } catch (_e) {
      // Optimistic wave animation continues smoothly even if endpoint is busy
    }

    const toastEl = document.getElementById("toast");
    if (toastEl) {
      toastEl.textContent =
        target === "all"
          ? `⚡ Đã kích hoạt Chia Lô Chạy Song Song Toàn Xưởng: 15 Phòng Ban · 92 Nhân sự (62 luồng Chuyên viên đồng thời)!`
          : `⚡ Đã kích hoạt Chia Lô Chạy Song Song cho Phòng @${target}!`;
      toastEl.classList.remove("error");
      toastEl.classList.add("show");
      setTimeout(() => toastEl.classList.remove("show"), 3200);
    }

    setTimeout(() => {
      aoState.parallelWaveActive = false;
      aoState.parallelWaveDept = "";
      if (waveBtn) {
        waveBtn.classList.remove("is-dispatching");
        waveBtn.textContent = `✓ Đã Chia Lô 92 NS (${aoState.parallelLastWaveAt}) · ⚡ Chạy Lại`;
      }
      if (aoState.snapshot) {
        syncChibiStageWithSnapshot(aoState.snapshot);
      }
    }, 4500);
  }

  function initAgentOffice() {
    document.addEventListener("click", (ev) => {
      const toggleRoomSecBtn = ev.target.closest("[data-ao-toggle-room-sec]");
      if (toggleRoomSecBtn) {
        ev.preventDefault();
        ev.stopPropagation();
        const secKey = toggleRoomSecBtn.getAttribute("data-ao-toggle-room-sec") || "";
        if (secKey) {
          if (!aoState.roomSecOpen) {
            aoState.roomSecOpen = { progress: true, command: true, specialists: true, groupchat: false, all15: false };
          }
          aoState.roomSecOpen[secKey] = !aoState.roomSecOpen[secKey];
          aoState._lastFocusSig = "";
          renderFocusReplyOverlay();
        }
        return;
      }
      const toggleAllRoomSecBtn = ev.target.closest("[data-ao-toggle-all-room-sec]");
      if (toggleAllRoomSecBtn) {
        ev.preventDefault();
        ev.stopPropagation();
        if (!aoState.roomSecOpen) {
          aoState.roomSecOpen = { progress: true, command: true, specialists: true, groupchat: false, all15: false };
        }
        const keys = ["progress", "command", "specialists", "groupchat", "all15"];
        const openCnt = keys.filter((k) => aoState.roomSecOpen[k]).length;
        if (openCnt >= 4) {
          // Collapse to ultra-compact mode (keep only progress & specialists open, collapse others)
          aoState.roomSecOpen = { progress: true, command: false, specialists: true, groupchat: false, all15: false };
        } else {
          // Expand all 5 sections
          aoState.roomSecOpen = { progress: true, command: true, specialists: true, groupchat: true, all15: true };
        }
        aoState._lastFocusSig = "";
        renderFocusReplyOverlay();
        return;
      }
      const toggleMiniRoomBtn = ev.target.closest("[data-ao-toggle-mini-room]");
      if (toggleMiniRoomBtn) {
        ev.preventDefault();
        ev.stopPropagation();
        const rmId = toggleMiniRoomBtn.getAttribute("data-ao-toggle-mini-room") || "";
        if (rmId) {
          if (!aoState.miniRoomOpen) aoState.miniRoomOpen = { direction: true, editorial: true, cinema: true, qa: true };
          aoState.miniRoomOpen[rmId] = aoState.miniRoomOpen[rmId] === false ? true : false;
          aoState._lastInspectorSig = "";
          if (aoState.snapshot) renderInspector(aoState.snapshot, true);
        }
        return;
      }
      const toggleOtherDeptsBtn = ev.target.closest("[data-ao-toggle-other-depts]");
      if (toggleOtherDeptsBtn) {
        ev.preventDefault();
        ev.stopPropagation();
        aoState.otherDeptsDirectoryOpen = aoState.otherDeptsDirectoryOpen === false ? true : false;
        aoState._lastInspectorSig = "";
        if (aoState.snapshot) renderInspector(aoState.snapshot, true);
        return;
      }
      if (ev.target.closest("[data-ao-exit-focus]")) {
        ev.preventDefault();
        ev.stopPropagation();
        exitChibiFocus();
        if (aoState.snapshot) renderLiveStatusBar(aoState.snapshot);
        return;
      }
      const jumpActiveBtn = ev.target.closest("[data-ao-jump-active-room]");
      if (jumpActiveBtn) {
        ev.preventDefault();
        ev.stopPropagation();
        const targetRoom =
          resolvePrimaryWorkingDepartment(aoState.snapshot) ||
          jumpActiveBtn.getAttribute("data-ao-jump-active-room") ||
          "script";
        aoState.viewMode = "chibi";
        focusChibiAgent(targetRoom, "lead", false);
        if (aoState.snapshot) renderLiveStatusBar(aoState.snapshot);
        return;
      }
      const openGchatBtn = ev.target.closest("[data-ao-open-group-chat]");
      if (openGchatBtn) {
        ev.preventDefault();
        ev.stopPropagation();
        aoState.activeTab = "chat";
        aoState._lastInspectorSig = "";
        if (aoState.snapshot) renderInspector(aoState.snapshot, true);
        const inspectorEl = document.getElementById("agentOfficeInspectorAside");
        if (inspectorEl && typeof inspectorEl.scrollIntoView === "function") {
          inspectorEl.scrollIntoView({ behavior: "smooth", block: "nearest" });
        }
        return;
      }
      const gchatQuickBtn = ev.target.closest("[data-ao-gchat-quick]");
      if (gchatQuickBtn) {
        ev.preventDefault();
        ev.stopPropagation();
        const qTxt = gchatQuickBtn.getAttribute("data-ao-gchat-quick") || "";
        handleSendGroupChatMessage(qTxt);
        return;
      }
      const gchatSendBtn = ev.target.closest("[data-ao-gchat-send]");
      if (gchatSendBtn) {
        ev.preventDefault();
        ev.stopPropagation();
        const inpId = gchatSendBtn.getAttribute("data-ao-gchat-send") || "aoDockGroupChatInput";
        const inp = document.getElementById(inpId);
        if (inp && inp.value.trim()) {
          const val = inp.value.trim();
          inp.value = "";
          handleSendGroupChatMessage(val);
        }
        return;
      }
      const openTrigger = ev.target.closest("[data-open-agent-office]");
      if (openTrigger) {
        ev.preventDefault();
        openAgentOffice();
        return;
      }
      if (ev.target.closest("#closeAgentOfficeDialog")) {
        ev.preventDefault();
        closeAgentOffice();
        return;
      }
      const autoZoomBtn = ev.target.closest("[data-ao-toggle-auto-zoom]");
      if (autoZoomBtn) {
        ev.preventDefault();
        ev.stopPropagation();
        aoState.autoZoomActiveRoom = !aoState.autoZoomActiveRoom;
        aoState.manualOverviewLock = !aoState.autoZoomActiveRoom;
        aoState.manualZoomOutKey = "";
        autoZoomBtn.classList.toggle("active", aoState.autoZoomActiveRoom);
        autoZoomBtn.textContent = aoState.autoZoomActiveRoom
          ? "🎥 Tự Vào Phòng Đang Làm: BẬT"
          : "🎥 Tự Vào Phòng Đang Làm: TẮT";
        if (aoState.autoZoomActiveRoom && aoState.viewMode === "chibi") {
          const targetRoom =
            resolvePrimaryWorkingDepartment(aoState.snapshot) ||
            aoState.focusedAgentId ||
            aoState.selectedAgentId ||
            "vox";
          focusChibiAgent(targetRoom, "lead", false);
        } else if (!aoState.autoZoomActiveRoom && aoState.focusedAgentId) {
          exitChibiFocus();
        }
        return;
      }
      const toggleMaxBtn = ev.target.closest("[data-ao-toggle-max-stage]");
      if (toggleMaxBtn) {
        ev.preventDefault();
        ev.stopPropagation();
        aoState.stageMaximized = !aoState.stageMaximized;
        const bodyGrid = document.getElementById("agentOfficeBodyGrid");
        if (bodyGrid) bodyGrid.classList.toggle("is-stage-maximized", aoState.stageMaximized);
        toggleMaxBtn.classList.toggle("active", aoState.stageMaximized);
        toggleMaxBtn.textContent = aoState.stageMaximized ? "◧ Hiện Thanh Tra" : "⛶ Toàn Cảnh";
        requestAnimationFrame(() => syncCameraTransform());
        setTimeout(() => syncCameraTransform(), 60);
        return;
      }
      const toggle3dBtn = ev.target.closest("[data-ao-toggle-3d]");
      if (toggle3dBtn) {
        ev.preventDefault();
        ev.stopPropagation();
        aoState.perspective3d = !aoState.perspective3d;
        toggle3dBtn.classList.toggle("active", aoState.perspective3d);
        toggle3dBtn.textContent = aoState.perspective3d
          ? "🧊 Góc 2.5D: BẬT"
          : "📐 Góc 2D: PHẲNG";
        requestAnimationFrame(() => syncCameraTransform());
        return;
      }
      const selectDeptDockBtn = ev.target.closest("[data-ao-select-dept-dock]");
      if (selectDeptDockBtn && !ev.target.closest("[data-ao-dispatch-handle]")) {
        ev.preventDefault();
        ev.stopPropagation();
        const deptId = selectDeptDockBtn.getAttribute("data-ao-select-dept-dock") || "vox";
        aoState.selectedAgentId = deptId;
        if (aoState.viewMode === "chibi") {
          focusChibiAgent(deptId, "lead", false);
        }
        document.querySelectorAll(".ao-team-pod").forEach((el) => {
          el.classList.toggle("is-dock-selected", el.getAttribute("data-ao-agent") === deptId);
        });
        if (aoState.snapshot) renderInspector(aoState.snapshot);
        return;
      }
      if (ev.target.closest("[data-ao-exit-focus]")) {
        ev.preventDefault();
        exitChibiFocus();
        return;
      }
      if (ev.target.closest("[data-ao-close-spec-monitor]") || ev.target.id === "aoSpecialistLiveMonitorDrawer") {
        ev.preventDefault();
        ev.stopPropagation();
        closeFloorSpecialistMonitor();
        return;
      }
      const openSpecBtn = ev.target.closest("[data-ao-open-spec-monitor]");
      if (openSpecBtn) {
        ev.preventDefault();
        ev.stopPropagation();
        const raw = openSpecBtn.getAttribute("data-ao-open-spec-monitor") || "vox:lead";
        const parts = raw.split(":");
        openFloorSpecialistMonitor(parts[0] || "vox", parts[1] || "lead");
        return;
      }
      const sendSpecCmdBtn = ev.target.closest("[data-ao-send-spec-monitor-cmd]");
      if (sendSpecCmdBtn) {
        ev.preventDefault();
        ev.stopPropagation();
        const handle = sendSpecCmdBtn.getAttribute("data-ao-send-spec-monitor-cmd") || "@vox_lead";
        const inp = document.getElementById("aoSpecMonitorCmdInput");
        const cmdTxt = inp && inp.value.trim() ? inp.value.trim() : "";
        closeFloorSpecialistMonitor();
        dispatchMentionToChat(handle, cmdTxt, false);
        return;
      }
      const parallelBtn = ev.target.closest("[data-ao-dispatch-parallel-dept]");
      if (parallelBtn) {
        ev.preventDefault();
        ev.stopPropagation();
        const targetDept = parallelBtn.getAttribute("data-ao-dispatch-parallel-dept") || "all";
        triggerFloorParallelDispatch(targetDept);
        return;
      }
      const focusMemberBtn = ev.target.closest("[data-ao-focus-member]");
      if (focusMemberBtn) {
        ev.preventDefault();
        ev.stopPropagation();
        const raw = focusMemberBtn.getAttribute("data-ao-focus-member") || "vox:lead";
        const parts = raw.split(":");
        focusChibiAgent(parts[0] || "vox", parts[1] || "lead");
        return;
      }
      const zoneFilterBtn = ev.target.closest("[data-ao-zone-filter]");
      if (zoneFilterBtn) {
        ev.preventDefault();
        ev.stopPropagation();
        aoState.floorZoneFilter = zoneFilterBtn.getAttribute("data-ao-zone-filter") || "all";
        document.querySelectorAll("[data-ao-zone-filter]").forEach((b) => {
          b.classList.toggle("active", b.getAttribute("data-ao-zone-filter") === aoState.floorZoneFilter);
        });
        aoState.focusedAgentId = null;
        const card = document.getElementById("aoFocusReplyCard");
        if (card) card.hidden = true;
        syncCameraTransform();
        return;
      }
      const askBtn = ev.target.closest("[data-ao-ask]");
      if (askBtn) {
        ev.preventDefault();
        aoState.focusAskMode = askBtn.getAttribute("data-ao-ask") || "progress";
        playStudioSound("ask");
        renderFocusReplyOverlay();
        return;
      }
      const dispatchBtn = ev.target.closest("[data-ao-dispatch-handle]");
      if (dispatchBtn) {
        ev.preventDefault();
        ev.stopPropagation();
        const handle = dispatchBtn.getAttribute("data-ao-dispatch-handle") || "@orchestrator";
        const customInput = document.getElementById("aoCharterQuickCmdInput");
        const promptTxt =
          dispatchBtn.getAttribute("data-ao-dispatch-prompt") ||
          (customInput && customInput.value.trim() ? customInput.value.trim() : "");
        dispatchMentionToChat(handle, promptTxt, false);
        return;
      }
      const quickSendBtn = ev.target.closest("[data-ao-quick-send]");
      if (quickSendBtn) {
        ev.preventDefault();
        ev.stopPropagation();
        const handle = quickSendBtn.getAttribute("data-ao-quick-send") || "@orchestrator";
        const customInput = document.getElementById("aoCharterQuickCmdInput");
        const promptTxt = customInput && customInput.value.trim() ? customInput.value.trim() : "";
        dispatchMentionToChat(handle, promptTxt, false);
        return;
      }
      const filterBtn = ev.target.closest("[data-ao-dept-filter]");
      if (filterBtn) {
        ev.preventDefault();
        ev.stopPropagation();
        aoState.deptDivisionFilter = filterBtn.getAttribute("data-ao-dept-filter") || "all";
        if (aoState.snapshot) renderFloorplan(aoState.snapshot);
        return;
      }
      const viewBtn = ev.target.closest("[data-ao-view]");
      if (viewBtn) {
        ev.preventDefault();
        aoState.viewMode = viewBtn.getAttribute("data-ao-view") || "chibi";
        aoState.focusedAgentId = null;
        if (aoState.snapshot) renderFloorplan(aoState.snapshot);
        return;
      }
      const charterBtn = ev.target.closest("[data-ao-open-charter]");
      if (charterBtn) {
        ev.preventDefault();
        ev.stopPropagation();
        aoState.selectedAgentId = charterBtn.getAttribute("data-ao-open-charter") || "orchestrator";
        aoState.activeTab = "charter";
        if (aoState.snapshot) renderInspector(aoState.snapshot);
        return;
      }
      const tabBtn = ev.target.closest("[data-ao-tab]");
      if (tabBtn) {
        aoState.activeTab = tabBtn.getAttribute("data-ao-tab") || "departments";
        if (aoState.snapshot) renderInspector(aoState.snapshot);
        return;
      }
      const memberEl = ev.target.closest(".ao-pod-member[data-ao-member-key]");
      if (memberEl) {
        ev.preventDefault();
        ev.stopPropagation();
        const aid = memberEl.getAttribute("data-ao-agent") || "orchestrator";
        const mKey = memberEl.getAttribute("data-ao-member-key") || "lead";
        focusChibiAgent(aid, mKey);
        return;
      }
      const deskOrActor = ev.target.closest("[data-ao-agent]");
      if (deskOrActor) {
        const aid = deskOrActor.getAttribute("data-ao-agent") || "orchestrator";
        if (aoState.viewMode === "chibi") {
          focusChibiAgent(aid, "lead");
        } else {
          aoState.selectedAgentId = aid;
          aoState.activeTab = "charter";
          if (aoState.snapshot) {
            renderFloorplan(aoState.snapshot);
            renderInspector(aoState.snapshot);
          }
        }
      }
    });

    const soundBtn = document.getElementById("agentOfficeSoundBtn");
    if (soundBtn) {
      soundBtn.addEventListener("click", () => {
        aoState.soundEnabled = !aoState.soundEnabled;
        soundBtn.classList.toggle("is-muted", !aoState.soundEnabled);
        soundBtn.textContent = aoState.soundEnabled ? "🔊 Âm thanh" : "🔇 Tắt tiếng";
        if (aoState.soundEnabled) playStudioSound("ask");
      });
    }

    const jobSel = document.getElementById("agentOfficeJobSelect");
    if (jobSel) {
      jobSel.addEventListener("change", () => {
        aoState.userPinnedJobId = jobSel.value || "";
        aoState.selectedJobId = aoState.userPinnedJobId;
        refreshOffice(true);
      });
    }

    const globalJobSel = document.getElementById("globalProjectSelect");
    if (globalJobSel) {
      globalJobSel.addEventListener("change", () => {
        aoState.lastGlobalSelectedJobId = globalJobSel.value || "";
        aoState.userPinnedJobId = "";
        aoState.selectedJobId = "";
        refreshOffice(true);
      });
    }

    const manualBtn = document.getElementById("agentOfficeRefreshBtn");
    if (manualBtn) {
      manualBtn.addEventListener("click", () => refreshOffice(true));
    }

    const dlg = document.getElementById("agentOfficeDialog");
    if (dlg) {
      dlg.addEventListener("close", () => {
        aoState.open = false;
        aoState.focusedAgentId = null;
        if (aoState.pollTimer) {
          clearInterval(aoState.pollTimer);
          aoState.pollTimer = null;
        }
        if (aoState.bubbleTimer) {
          clearInterval(aoState.bubbleTimer);
          aoState.bubbleTimer = null;
        }
        if (aoState.roamTimer) {
          clearInterval(aoState.roamTimer);
          aoState.roamTimer = null;
        }
        if (aoState.rafId) {
          cancelAnimationFrame(aoState.rafId);
          aoState.rafId = null;
        }
      });
      dlg.addEventListener("click", (ev) => {
        if (ev.target === dlg) closeAgentOffice();
      });
    }

    document.addEventListener("keydown", (ev) => {
      if (ev.key === "Enter" && ev.target && ev.target.classList && ev.target.classList.contains("ao-gchat-input")) {
        ev.preventDefault();
        const val = String(ev.target.value || "").trim();
        if (val) {
          ev.target.value = "";
          handleSendGroupChatMessage(val);
        }
        return;
      }
      if ((ev.ctrlKey || ev.metaKey) && ev.shiftKey && ev.key.toLowerCase() === "o") {
        ev.preventDefault();
        if (aoState.open) closeAgentOffice();
        else openAgentOffice();
      }
    });

    window.addEventListener("resize", () => {
      if (!aoState.open || !aoState.snapshot) return;
      if (aoState.viewMode === "chibi") {
        syncCameraTransform();
      } else {
        drawFloorplanLinks(aoState.snapshot.links || []);
      }
    });

    // Background lightweight poll for topbar live badge (8000ms, skips hidden tab)
    refreshOffice(false);
    aoState.badgeTimer = setInterval(() => {
      if (!aoState.open && !document.hidden) refreshOffice(false);
    }, 8000);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initAgentOffice);
  } else {
    initAgentOffice();
  }
})();
