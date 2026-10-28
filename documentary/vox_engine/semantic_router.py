"""True Crime Animated Vox & Real Satellite Semantic Scene Router.

Analyzes spoken voice narration (Korean / Vietnamese) to semantically route beats to matching animated Vox & Satellite Map scenes with sliding-window variety, voice-duration & clause synchronization (`voice_spec`), and channel profile isolation to channel-e544a64b7c.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from documentary.audio_library_manager import select_contextual_sfx_for_beat


VOX_ARCHETYPE_RULES: dict[str, dict[str, Any]] = {
    "#V_FULLSCREEN_GIS_FLIGHT": {
        "cluster": "fullscreen_map_flight",
        "label": "Full-Screen 1920x1080 Regional/Basin Terrain & Administrative GeoJSON Map Flight (A->B Camera + Progressive Route + PiP Video)",
        "regex_ko": r"(베이징.*운남|베이징.*쿤밍|독도조.*파견|제1교도소.*제2교도소|비밀\s*이감|최고인민법원.*복핵|광역.*이동|전역.*투입|2,100km|직할.*급파)",
        "regex_vi": r"(Bắc\s*Kinh.*Vân\s*Nam|Bắc\s*Kinh.*Côn\s*Minh|tổ\s*đốc\s*đạo.*điều\s*động|trại\s*giam\s*số\s*1.*trại\s*giam\s*số\s*2|chuyển\s*trại|Tòa\s*án\s*tối\s*cao.*phúc\s*hạch|bay\s*qua\s*bản\s*đồ)",
        "priority_score": 99,
    },
    "#V_FULLSCREEN_SATELLITE_RECON": {
        "cluster": "fullscreen_satellite_recon",
        "label": "Full-Screen 1920x1080 High-Res Urban Satellite Reconnaissance Map (A->B Camera + Radar Pins + PiP Video)",
        "regex_ko": r"(도심.*유흥가|나이트클럽.*확장|관두구.*노래방|춘성만보.*특종|파출소.*무마|전면\s*위성|도심\s*전역)",
        "regex_vi": r"(khu\s*ăn\s*chơi|hộp\s*đêm.*mở\s*rộng|quán\s*karaoke|đồn\s*công\s*an.*bao\s*che|vệ\s*tinh\s*toàn\s*màn\s*hình)",
        "priority_score": 97,
    },
    "#V_FORENSIC_CROSS_SECTION": {
        "cluster": "forensic_mechanism",
        "label": "2D Spatial/Architectural Cross-Section & Mechanism Flow Diagram",
        "regex_ko": r"(정화조|배관|파이프|하수구|단면도|802호.*지하|지하.*탱크|38대.*흡입|흡입차|분쇄.*배출|수돗물\s*2톤|수직\s*배관|거름망.*고압|특허|도면|구조도)",
        "regex_vi": r"(hầm\s*tự\s*hoại|bể\s*phốt|đường\s*ống\s*ngầm|ống\s*thoát\s*nước|mặt\s*cắt\s*tòa\s*nhà|38\s*xe\s*hút\s*bùn|2\s*tấn\s*nước|cấu\s*trúc\s*đường\s*ống|bằng\s*sáng\s*chế|bản\s*vẽ)",
        "priority_score": 98,
    },
    "#V_POPOUT_HIGHLIGHT": {
        "cluster": "press_popout",
        "label": "2D Blur-Background Document Pop-Out & Clause-Synced Highlighter",
        "regex_ko": r"(형광펜|하이라이트|기사\s*일부|보고서.*구절|진술.*모순|밑줄|발췌|기록.*문구|결정적\s*구절|진술.*앞뒤|보도.*내용|수사\s*보고서.*줄)",
        "regex_vi": r"(tô\s*sáng|nhấn\s*mạnh|đoạn\s*văn|trích\s*dẫn\s*báo|mâu\s*thuẫn\s*lời\s*khai|gạch\s*chân|phóng\s*nổi|chi\s*tiết\s*biên\s*bản)",
        "priority_score": 96,
    },
    "#V_CLAUSE_TIMELINE": {
        "cluster": "clause_timeline",
        "label": "2D Voice-Synced Progressive Multi-Node Timeline & Causal Chain",
        "regex_ko": r"(시간대별|분\s*단위|동선\s*추적|순서대로|이어서.*시각|연쇄\s*과정|오전.*오후|새벽.*밤|행적\s*재구성|단계별|인과\s*관계|17시\s*04분)",
        "regex_vi": r"(theo\s*từng\s*mốc|từng\s*phút|lần\s*lượt|quá\s*trình\s*di\s*chuyển|tái\s*hiện\s*lộ\s*trình|chuỗi\s*nhân\s*quả|từng\s*bước)",
        "priority_score": 95,
    },
    "#V_SAT_ZONE_DRAW": {
        "cluster": "satellite_zone",
        "label": "2D Real Esri Satellite Map & Animated Zone/Route Vector Drawing",
        "regex_ko": r"(관할\s*구역|반경|포위망|도주\s*경로|위치\s*추적|위성\s*지도|구역\s*설정|이동\s*경로|지리적\s*배치)",
        "regex_vi": r"(khoanh\s*vùng|bản\s*đồ\s*vệ\s*tinh|lộ\s*trình\s*di\s*chuyển|khu\s*vực\s*quản\s*lý|vòng\s*vây|tọa\s*độ\s*vệ\s*tinh)",
        "priority_score": 94,
    },
    "#V_DOSSIER_BOARD": {
        "cluster": "dossier_network",
        "label": "2D Tactile Case Dossier Folder & Suspect Relationship Network Board",
        "regex_ko": r"(보호우산|비호\s*세력|공모\s*관계|연루자|배후\s*인물|인맥\s*연결망|수사망|대조\s*파일|신원\s*대조)",
        "regex_vi": r"(ô\s*dù\s*bảo\s*kê|mạng\s*lưới\s*quan\s*hệ|đồng\s*phạm|hồ\s*sơ\s*đối\s*chiếu|thế\s*lực\s*chống\s*lưng)",
        "priority_score": 94,
    },
    "#V_BLENDER_3D_STAGE": {
        "cluster": "blender_stage",
        "label": "Multi-Layer Investigation Stage & Evidence Network",
        "regex_ko": r"(입체\s*재구성|다층\s*수사망|3D\s*분석|증거\s*네트워크)",
        "regex_vi": r"(tái\s*dựng\s*đa\s*tầng|mạng\s*lưới\s*bằng\s*chứng\s*lập\s*thể)",
        "priority_score": 95,
    },
    "#D4": {
        "cluster": "biometrics",
        "label": "Y-STR DNA Lightbox & Clan Pedigree Tree",
        "regex_ko": r"(Y-염색체|유전자|족보|가문|DNA|부계|혈통|친척|가오씨|대조\s*검사|염색체|가계도|인체\s*조직|20그램)",
        "regex_vi": r"(Y-STR|nhiễm\s*sắc\s*thể\s*Y|ADN\s*dòng\s*họ|phả\s*hệ|gia\s*tộc|huyết\s*thống|quan\s*hệ\s*họ\s*hàng|xét\s*nghiệm\s*ADN|mô\s*người|20\s*gram)",
        "priority_score": 96,
    },
    "#M1": {
        "cluster": "satellite_zoom",
        "label": "Zoom x16 Tactical Rooftop Store / Compound",
        "regex_ko": r"(매점|학교|캠퍼스|지붕|옥상|건물|급습|현장\s*포위|주소|골목\s*안|매점\s*주인|아파트\s*단지|산스화위안|4동)",
        "regex_vi": r"(tiệm\s*tạp\s*hóa|mái\s*nhà|trường\s*học|khuôn\s*viên|nóc\s*nhà|đột\s*kích|bao\s*vây|tạp\s*hóa\s*trường|khu\s*chung\s*cư|tòa\s*4)",
        "priority_score": 92,
    },
    "#M6": {
        "cluster": "satellite_zoom",
        "label": "Split Dual Satellite (Macro vs Micro)",
        "regex_ko": r"(광역.*좁혀졌|도심.*매점|위성.*분할|확대.*포착|줌인|광역.*정밀|항저우.*단지)",
        "regex_vi": r"(thu\s*hẹp.*phạm\s*vi|vệ\s*tinh.*phóng\s*to|từ\s*toàn\s*cảnh.*đến\s*chi\s*tiết|chia\s*đôi\s*vệ\s*tinh|vệ\s*tinh\s*kép)",
        "priority_score": 88,
    },
    "#M2": {
        "cluster": "satellite_corridor",
        "label": "Regional Satellite Corridor Z6/Z9",
        "regex_ko": r"(황토\s*고원|공업\s*기지|광산|간쑤성|란저우|바이인시|고속도로|회랑|지형|성도|도주로|장강\s*삼각주|저장성|항저우시)",
        "regex_vi": r"(cao\s*nguyên\s*hoàng\s*thổ|mỏ\s*đồng|công\s*nghiệp|Cam\s*Túc|Lan\s*Châu|Bạch\s*Ngân|tuyến\s*đường|hành\s*lang|Chiết\s*Giang|Hàng\s*Châu)",
        "priority_score": 82,
    },
    "#M3": {
        "cluster": "satellite_corridor",
        "label": "Administrative Boundary / River Crossing",
        "regex_ko": r"(성\s*경계|행정구역|도주로|호구|외지인|관할|경계선|강을\s*건너|철도|황하|쳰탕강|운하)",
        "regex_vi": r"(ranh\s*giới\s*tỉnh|ranh\s*giới\s*hành\s*chính|đường\s*trốn\s*chạy|hộ\s*khẩu|ngoại\s*tỉnh|vượt\s*sông|ngoài\s*tầm\s*kiểm\s*soát|sông\s*Hoàng\s*Hà|sông\s*Tiền\s*Đường)",
        "priority_score": 87,
    },
    "#M5": {
        "cluster": "satellite_slab",
        "label": "2.5D Tilted Satellite Slab",
        "regex_ko": r"(좌표|지리적\s*패턴|연결하자|입체|3차원|위성\s*지형|슬랩|동선\s*패턴|거리.*연결|좌표.*거리|출입구.*카메라)",
        "regex_vi": r"(tọa\s*độ|mô\s*thức\s*địa\s*lý|bản\s*đồ\s*lập\s*thể|khối\s*3D|mô\s*hình\s*không\s*gian|khối\s*bản\s*đồ|khoảng\s*cách.*liên\s*kết|tọa\s*độ.*khoảng\s*cách)",
        "priority_score": 92,
    },
    "#M4": {
        "cluster": "satellite_slab",
        "label": "Detective Cork Pinboard & Crime Cluster",
        "regex_ko": r"(핀보드|붉은\s*실|사건\s*연결|연쇄.*분포|범행.*연결|코르크|수사\s*상황판)",
        "regex_vi": r"(bảng\s*điều\s*tra|dây\s*chỉ\s*đỏ|ghim\s*nối|chuỗi\s*án|phân\s*bố\s*tội\s*phạm|bảng\s*gỗ)",
        "priority_score": 86,
    },
    "#M7": {
        "cluster": "curfew_surveillance",
        "label": "Night-Ops Infrared Satellite Curfew",
        "regex_ko": r"(야간\s*통제|통금|해가\s*지면|반경\s*3|적외선|외출\s*금지|밤거리|야간\s*순찰|봉쇄|사각지대|6,000개.*카메라|CCTV\s*망)",
        "regex_vi": r"(giới\s*nghiêm|vùng\s*kiểm\s*soát|màn\s*đêm\s*buông\s*xuống|bán\s*kính\s*3\s*km|hồng\s*ngoại|cấm\s*ra\s*đường\s*đêm|tuần\s*tra\s*đêm|phong\s*tỏa|6\.000\s*camera)",
        "priority_score": 95,
    },
    "#M8": {
        "cluster": "satellite_corridor",
        "label": "Topographic Elevation Profile & Interstate Highway",
        "regex_ko": r"(등고선|고도|해발|산악\s*지형|단면\s*프로파일|협곡\s*고도)",
        "regex_vi": r"(đường\s*đồng\s*mức|độ\s*cao|mặt\s*cắt\s*địa\s*hình|núi\s*cao|đèo\s*dốc|hẻm\s*núi)",
        "priority_score": 83,
    },
    "#D9": {
        "cluster": "fingerprint",
        "label": "Microscope 14-Point Minutiae Comparator",
        "regex_ko": r"(14개|특징점|포개졌|현미경|완벽히\s*일치|단\s*하나의\s*지문|융선|미세\s*조직\s*대조)",
        "regex_vi": r"(đặc\s*điểm\s*vân|14\s*điểm|trùng\s*khớp\s*hoàn\s*hảo|kính\s*hiển\s*vi|vân\s*ngón\s*tay|điểm\s*đặc\s*trưng)",
        "priority_score": 97,
    },
    "#D1": {
        "cluster": "fingerprint",
        "label": "Case Dossier Folder & Verification Matrix",
        "regex_ko": r"(23만\s*장|지문\s*대조망|유령으로|지문\s*카드|불일치|대조했으나|지문|수사\s*기록|사건\s*파일|전수\s*조사|전수\s*판독|명부|대조표|6,000시간)",
        "regex_vi": r"(23\s*vạn\s*dấu\s*vân\s*tay|lưới\s*so\s*sánh|bóng\s*ma|không\s*tìm\s*ra|phiếu\s*vân\s*tay|dấu\s*vân\s*tay|hồ\s*sơ\s*vụ\s*án|hồ\s*sơ\s*điều\s*tra|rà\s*soát\s*toàn\s*bộ)",
        "priority_score": 87,
    },
    "#D3": {
        "cluster": "fingerprint",
        "label": "Three Physical Clues & Case Evidence Dossier",
        "regex_ko": r"(생체\s*시료|혈액형|족적|3대\s*단서|물증|현장\s*증거|신발\s*자국|유류품|신분증|지갑|계량기|수돗물\s*2톤|잠옷|휴대전화)",
        "regex_vi": r"(mẫu\s*sinh\s*học|nhóm\s*máu|dấu\s*chân|3\s*manh\s*mối\s*vật\s*chứng|dấu\s*vết\s*hiện\s*trường|vật\s*chứng\s*để\s*lại|đồng\s*hồ\s*nước)",
        "priority_score": 85,
    },
    "#D5": {
        "cluster": "interrogation",
        "label": "Aluminum Clipboard Q&A + Voiceprint",
        "regex_ko": r"(심문실|자백|진술서|자필|시인했다|녹음|취조|차분한\s*목소리|필적|심문|실종\s*신고|진술)",
        "regex_vi": r"(phòng\s*thẩm\s*vấn|thú\s*tội|lời\s*khai|bản\s*cung|thừa\s*nhận|ghi\s*âm|hỏi\s*cung|bút\s*tích|trình\s*báo|báo\s*án)",
        "priority_score": 96,
    },
    "#D2": {
        "cluster": "interrogation",
        "label": "Dual Identity / Suspect-Victim Case Profile Dossier",
        "regex_ko": r"(두\s*얼굴|이중생활|남편|아버지|괴물|평범한|가면|악마|한\s*지붕|재혼|아파트.*소유|주식\s*투자|빚|재산|쉬궈리|라이후이리)",
        "regex_vi": r"(hai\s*mặt|vỏ\s*bọc|cuộc\s*sống\s*hai\s*mặt|người\s*chồng\s*mẫu\s*mực|quỷ\s*dữ|đội\s*lốt|hồ\s*sơ\s*nhân\s*thân|tài\s*sản|nợ\s*nần)",
        "priority_score": 81,
    },
    "#D6": {
        "cluster": "warrant_sketch",
        "label": "Class-A Red Wanted Warrant & Sketch",
        "regex_ko": r"(수배령|현상금|몽타주|공안부|1급\s*수배|공개수배|인상착의|스케치|20만\s*위안|10만\s*위안)",
        "regex_vi": r"(lệnh\s*truy\s*nã|tiền\s*thưởng|phác\s*họa\s*chân\s*dung|truy\s*nã\s*đỏ|truy\s*nã\s*cấp\s*A|phác\s*thảo|20\s*vạn)",
        "priority_score": 96,
    },
    "#D7": {
        "cluster": "biometrics",
        "label": "Ballistics & Toolmark Comparator",
        "regex_ko": r"(조흔|흉기\s*흔적|공구흔|칼자국|절단흔|탄도|분쇄기)",
        "regex_vi": r"(vết\s*cắt|dấu\s*vết\s*hung\s*khí|vết\s*xước\s*kim\s*loại|dấu\s*kìm|đạn\s*đạo)",
        "priority_score": 84,
    },
    "#D8": {
        "cluster": "biometrics",
        "label": "Autopsy & Medical Examiner Report",
        "regex_ko": r"(부검|검시|사망\s*원인|법의학|시신|타살|질식|사체\s*감정|약물\s*검출)",
        "regex_vi": r"(khám\s*nghiệm\s*tử\s*thi|pháp\s*y|nguyên\s*nhân\s*tử\s*vong|giải\s*phẫu|ngạt\s*thở)",
        "priority_score": 86,
    },
    "#D10": {
        "cluster": "timeline",
        "label": "Cold Case Archive Vault Box",
        "regex_ko": r"(서고|보존\s*상자|미제사건\s*캐비닛|캐비닛|먼지\s*쌓인|증거물\s*보관)",
        "regex_vi": r"(kho\s*lưu\s*trữ|hộp\s*hồ\s*sơ|hồ\s*sơ\s*đóng\s*bụi|tủ\s*tài\s*liệu\s*vụ\s*án|niêm\s*phong)",
        "priority_score": 83,
    },
    "#P3": {
        "cluster": "broadcast",
        "label": "1990s/2020s TV Broadcast Monitor & Interview",
        "regex_ko": r"(방송|뉴스|특보|TV|화면|앵커|보도자료|아카이브\s*영상|당시\s*보도|브라운관|CRT|인터뷰|카메라\s*앞)",
        "regex_vi": r"(bản\s*tin\s*truyền\s*hình|phát\s*sóng|thời\s*sự|ti\s*vi|đài\s*truyền\s*hình|băng\s*VHS|màn\s*hình\s*CRT|phỏng\s*vấn)",
        "priority_score": 93,
    },
    "#P2": {
        "cluster": "curfew_surveillance",
        "label": "Archival Newspaper Panic & Public Notice",
        "regex_ko": r"(신문|보도|신문\s*1면|공포에\s*휩싸|비상\s*통고|경고문|호외|붉은\s*옷|실종\s*전단)",
        "regex_vi": r"(báo\s*chí|trang\s*nhất|hoảng\s*loạn|thông\s*báo\s*khẩn|giấy\s*cảnh\s*báo|áo\s*đỏ|dư\s*luận|tờ\s*rơi\s*tìm\s*người)",
        "priority_score": 82,
    },
    "#P1": {
        "cluster": "timeline",
        "label": "Chronological Timeline / Silent Gap",
        "regex_ko": r"(년\s*만에|년\s*동안|세월|침묵|공백|타임라인|미제로\s*남은|흐른\s*뒤|6년|28년|19일\s*동안)",
        "regex_vi": r"(suốt\s*bao\s*nhiêu\s*năm|dòng\s*thời\s*gian|năm\s*im\s*lặng|chưa\s*có\s*lời\s*giải|thời\s*gian\s*trôi|khoảng\s*lặng|6\s*năm|28\s*năm)",
        "priority_score": 88,
    },
    "#P4": {
        "cluster": "warrant_sketch",
        "label": "Police Bulletin Teletype / Telex Dispatch",
        "regex_ko": r"(전신|전문|급보|타자기|전국\s*전파|공안\s*전신|수사\s*속보)",
        "regex_vi": r"(điện\s*báo|bản\s*tin\s*khẩn|máy\s*đánh\s*chữ|báo\s*động\s*toàn\s*quốc|điện\s*mật)",
        "priority_score": 84,
    },
    "#P5": {
        "cluster": "broadcast",
        "label": "Emergency Radio Dispatch Frequency Log",
        "regex_ko": r"(무전|무전기|주파수|순찰차\s*교신|무전\s*일지|신호음|지휘\s*본부)",
        "regex_vi": r"(bộ\s*đàm|tần\s*số|xe\s*tuần\s*tra|liên\s*lạc\s*vô\s*tuyến|sóng\s*radio)",
        "priority_score": 83,
    },
    "#P6": {
        "cluster": "court_verdict",
        "label": "Supreme Court Verdict & Sentence Proclamation",
        "regex_ko": r"(판결문|사형|재판|법원|선고|집행|정치권리\s*박탈|판결)",
        "regex_vi": r"(bản\s*án|tử\s*hình|tòa\s*án|tuyên\s*án|thi\s*hành\s*án|phán\s*quyết)",
        "priority_score": 90,
    },
    "cinema_full": {
        "cluster": "cinema",
        "label": "Fullscreen Cinematic Documentary Frame",
        "regex_ko": r"(눈물|슬픔|유가족|통곡|비통|오열|망연자실|주저앉아|말을\s*잇지\s*못|가슴이\s*무너|희생자의\s*어머니|딸)",
        "regex_vi": r"(nước\s*mắt|đau\s*đớn|người\s*nhà\s*nạn\s*nhân|bi\s*kịch|tưởng\s*niệm|nghẹn\s*ngào|gục\s*ngã|thương\s*tâm|không\s*nói\s*nên\s*lời|người\s*mẹ\s*nạn\s*nhân)",
        "priority_score": 90,
    },
}


_CALLBACK_RE = re.compile(
    r"(다시\s*돌려|앞서\s*살펴본|비교해|대조해|모순|거짓말이|처음\s*진술|재검토|화면\s*속.*다시|일치하지\s*않|đối\s*chiếu\s*lại|mâu\s*thuẫn\s*với|lật\s*lại)",
    re.IGNORECASE,
)

_METRIC_RE = re.compile(
    r"(\d{1,2}시\s*\d{1,2}분|\d{1,2}:\d{2}|\d{4}년\s*\d{1,2}월\s*\d{1,2}일|\d{4}년|\d+(?:,\d+)*(?:\.\d+)?\s*(?:조\s*\d+(?:,\d+)*억\s*원|조\s*원|억\s*위안|만\s*위안|위안|억\s*원|만\s*원|원|억\s*파운드|만\s*파운드|파운드|달러|BTC|비트코인|만\s*명|천\s*명|명|만\s*개|천\s*개|개|만\s*대|대|건|회|곳|배|단계|개국|톤|그램|g|kg|도|℃|시간|분|초|개월|일|년|층|호|동|m|km|%))"
)


def split_narration_into_clauses(narration_text: str, max_clauses: int = 5) -> list[str]:
    """Splits a spoken narration sentence into 1..N (up to max_clauses) natural broadcast clauses for flexible progressive reveal."""
    text = str(narration_text or "").strip()
    if not text:
        return ["수사 기록 정밀 분석 진행 중"]

    # Step 1: Split on sentence punctuation, em-dashes, commas, or Korean connective transitions
    raw_parts = re.split(
        r"(?<=[.?!,])\s+|\s+—\s+|\s+·\s+|\s+(?=(?:하지만|그러나|그런데|결국|즉시|이때|그리고|반면|게다가|더구나|이후|이어)\s)",
        text,
    )
    parts = [p.strip() for p in raw_parts if p and len(p.strip()) >= 2]

    # Step 2: Further split any long segment (>= 32 chars) on natural Korean clause connectives
    refined: list[str] = []
    for seg in parts:
        if len(seg) >= 32:
            sub = re.split(
                r"(?<=[고며자때면뒤])\s+|(?<=지만)\s+|(?<=는데)\s+|(?<=더니)\s+|(?<=면서)\s+|(?<=던)\s+|(?<=으니)\s+",
                seg,
            )
            sub_clean = [s.strip() for s in sub if s and s.strip()]
            if len(sub_clean) > 1:
                refined.extend(sub_clean)
                continue
        refined.append(seg)
    parts = refined if refined else [text]

    # Step 3: Merge any tiny orphan fragment (< 9 chars, e.g. '있었습니다.', '씨 부부') into its neighbor
    i = 0
    while i < len(parts) and len(parts) > 1:
        if len(parts[i]) < 9:
            if i > 0:
                parts[i - 1] = f"{parts[i - 1]} {parts[i]}".strip()
                parts.pop(i)
                continue
            elif i + 1 < len(parts):
                parts[i + 1] = f"{parts[i]} {parts[i + 1]}".strip()
                parts.pop(i)
                continue
        i += 1

    # Step 4: If still 1 clause and very long (>= 44 chars), split at a natural particle/space near midpoint
    if len(parts) == 1 and len(text) >= 44:
        mid = len(text) // 2
        best_split = -1
        for m in re.finditer(r"(?<=[은는이가을를에의도만])\s+", text):
            pos = m.end()
            if 12 <= pos <= len(text) - 12:
                if best_split == -1 or abs(pos - mid) < abs(best_split - mid):
                    best_split = pos
        if best_split != -1:
            parts = [text[:best_split].strip(), text[best_split:].strip()]
        else:
            space_idx = text.find(" ", mid)
            if space_idx != -1 and 10 <= space_idx <= len(text) - 10:
                parts = [text[:space_idx].strip(), text[space_idx + 1:].strip()]

    # Step 5: Merge if more than max_clauses
    while len(parts) > max_clauses:
        min_len = 999999
        merge_idx = 0
        for idx_m in range(len(parts) - 1):
            combined_len = len(parts[idx_m]) + len(parts[idx_m + 1])
            if combined_len < min_len:
                min_len = combined_len
                merge_idx = idx_m
        parts[merge_idx] = f"{parts[merge_idx]} {parts[merge_idx + 1]}".strip()
        parts.pop(merge_idx + 1)

    return parts


def _extract_clause_focus_tag(clause_text: str, idx: int) -> str:
    """Extracts the primary spoken metric or concise 2-word focus phrase from a single clause."""
    m_hits = _METRIC_RE.findall(clause_text)
    if m_hits:
        return m_hits[0].strip()
    words = [w.strip(".,?!\"'()[]") for w in clause_text.split() if len(w.strip(".,?!\"'()[]")) >= 2]
    if len(words) >= 2:
        return f"{words[0]} {words[1]}"[:16]
    if words:
        return words[0][:16]
    return f"핵심 요지 0{idx + 1}"


def build_voice_spec_for_beat(beat: dict[str, Any], beat_index: int = 0) -> dict[str, Any]:
    """Extracts full voice-duration timing, flexible 1..N progressive clause windows, and spoken metrics from a beat.

    Matches the full spoken sentence duration (`end_sec - start_sec`) and progressive clause windows.
    """
    narration = str(
        beat.get("narration_text")
        or beat.get("narration")
        or beat.get("voice_text")
        or beat.get("text")
        or beat.get("script_text")
        or ""
    ).strip()

    # Compute exact voice duration without a 6.0s cap
    dur = float(beat.get("duration_sec") or beat.get("duration") or 0.0)
    if dur <= 0.0:
        start_s = float(beat.get("start_sec") or 0.0)
        end_s = float(beat.get("end_sec") or 0.0)
        if end_s > start_s:
            dur = end_s - start_s
    if dur <= 0.0:
        # Estimate naturally from character count (approx 7.2 Korean chars/sec)
        dur = max(4.0, min(14.5, round(max(12, len(narration)) / 7.2, 2)))

    clauses = split_narration_into_clauses(narration, max_clauses=5)
    char_lengths = [max(4, len(c)) for c in clauses]
    total_chars = float(sum(char_lengths))

    clause_windows: list[tuple[float, float]] = []
    clause_timestamps_sec: list[tuple[float, float]] = []
    cursor = 0.0
    for clen in char_lengths:
        span = clen / total_chars
        w_start = round(cursor, 4)
        w_end = round(min(1.0, cursor + span), 4)
        clause_windows.append((w_start, w_end))
        clause_timestamps_sec.append((round(w_start * dur, 2), round(w_end * dur, 2)))
        cursor += span

    clause_focus_tags = [_extract_clause_focus_tag(c, i) for i, c in enumerate(clauses)]

    metrics = []
    for m in _METRIC_RE.findall(narration):
        m_clean = m.strip()
        if m_clean and m_clean not in metrics:
            metrics.append(m_clean)
    for c_tag in clause_focus_tags:
        if c_tag and c_tag not in metrics:
            metrics.append(c_tag)
    if not metrics:
        words = [w.strip(".,?!\"'") for w in narration.split() if len(w.strip(".,?!\"'")) >= 2]
        metrics = words[:4] if words else ["수사 단서", "정밀 분석", "증거 대조"]

    beat_id = str(beat.get("beat_id") or beat.get("id") or f"B{beat_index + 1:03d}").strip()
    act_label = str(beat.get("act") or beat.get("chapter") or f"ACT {(beat_index // 65) + 1}").strip()
    location_label = str(beat.get("location") or beat.get("header_ko") or "형사 과학수사 증거 분석실").strip()
    is_callback = bool(beat.get("is_purposeful_callback") or _CALLBACK_RE.search(narration))

    # Build a concise Korean header from the first clause or beat title
    first_clause = clauses[0] if clauses else narration
    header_ko = str(beat.get("vox_header_ko") or first_clause[:28]).strip()
    sub_ko = str(beat.get("vox_sub_ko") or (clauses[1][:42] if len(clauses) > 1 else first_clause[:42])).strip()

    return {
        "beat_id": beat_id,
        "beat_index": beat_index,
        "duration_sec": round(dur, 2),
        "narration_text": narration,
        "clauses": clauses,
        "clause_windows": clause_windows,
        "clause_timestamps_sec": clause_timestamps_sec,
        "clause_focus_tags": clause_focus_tags,
        "metrics": metrics[:6],
        "act_label": act_label,
        "location_label": location_label,
        "header_ko": header_ko,
        "sub_ko": sub_ko,
        "is_purposeful_callback": is_callback,
        "variation_seed": beat_index * 37 + sum(ord(c) for c in beat_id),
        "contextual_sfx": select_contextual_sfx_for_beat(narration, str(beat.get("scene_archetype") or ""), beat_index),
    }


def is_vox_satellite_enabled(job: dict[str, Any], profile: dict[str, Any] | None = None) -> bool:
    """Verifies whether Vox & Satellite engine should activate for this job/profile.

    Strictly activates for True Crime profile (channel-e544a64b7c) or forensic_noir preset,
    while strictly protecting non-crime profiles (channel-1e24de3ab5, channel-aa913eb90d, channel-f6ec4dfff3).
    """
    profile_id = str(
        job.get("channel_profile_id")
        or (profile or {}).get("id")
        or (job.get("channel_profile_snapshot") or {}).get("id")
        or ""
    ).strip()

    # Strict whitelist for True Crime & Chinese High-Tech/Financial Crime channels
    if profile_id == "channel-e544a64b7c":
        return True

    # Strict blacklist for known non-crime channels
    if profile_id in {"channel-1e24de3ab5", "channel-aa913eb90d", "channel-f6ec4dfff3", "channel-cn-cyber-finance-kr"}:
        return False

    # Check editing preset and visual strategy
    preset_id = str(
        (job.get("editing_dna") or {}).get("preset_id")
        or ((profile or {}).get("editing_dna") or {}).get("preset_id")
        or ""
    ).strip().lower()
    if preset_id == "forensic_noir":
        return True

    strategy = str(
        job.get("visual_strategy")
        or (job.get("production_recipe") or {}).get("visual_strategy")
        or ""
    ).strip().lower()
    if strategy in {"forensic_noir", "true_crime_noir_ai"}:
        return True

    return False


class VoxSemanticRouter:
    """Voice-driven semantic router for True Crime investigative archetypes.

    Implements:
    1. Bilingual intent scoring (Korean broadcast voice + Vietnamese briefs).
    2. Voice-synced animated Vox & Satellite GIS modes.
    3. Sliding-window scene variety and purposeful callback awareness.
    4. Full voice-duration & clause synchronization via `voice_spec`.
    """

    def __init__(self, history_size: int = 6):
        self.history_size = history_size
        self.recent_archetypes: list[str] = []
        self.archetype_usage_counts: dict[str, int] = {}

    def reset_history(self) -> None:
        self.recent_archetypes.clear()
        self.archetype_usage_counts.clear()

    def _same_cluster(self, arch1: str, arch2: str) -> bool:
        c1 = (VOX_ARCHETYPE_RULES.get(arch1) or {}).get("cluster")
        c2 = (VOX_ARCHETYPE_RULES.get(arch2) or {}).get("cluster")
        return bool(c1 and c2 and c1 == c2)

    def route_beat(
        self,
        narration_text: str,
        metadata: dict[str, Any] | None = None,
        recent_history: list[str] | None = None,
    ) -> dict[str, Any]:
        """Classifies a single narration beat and resolves the optimal archetype."""
        text = str(narration_text or "").strip()
        history = list(recent_history) if recent_history is not None else list(self.recent_archetypes)
        is_callback = bool((metadata or {}).get("is_purposeful_callback") or _CALLBACK_RE.search(text))

        candidates: list[tuple[float, str, str, str]] = []

        # Check emotional trigger first
        cinema_rule = VOX_ARCHETYPE_RULES["cinema_full"]
        ko_emotion = bool(re.search(cinema_rule["regex_ko"], text, re.IGNORECASE))
        vi_emotion = bool(re.search(cinema_rule["regex_vi"], text, re.IGNORECASE))
        if ko_emotion or vi_emotion:
            penalty = 180.0 if history and history[-1] == "cinema_full" else 0.0
            score = max(0.0, 120.0 - penalty)
            if score > 0.0:
                candidates.append((score, "cinema_full", cinema_rule["label"], "Human sorrow / dramatic confrontation detected"))

        for arch_id, rule in VOX_ARCHETYPE_RULES.items():
            if arch_id == "cinema_full":
                continue
            if arch_id.startswith("#FIN"):
                _meta_prof = str((metadata or {}).get("channel_profile_id") or "").strip()
                _meta_preset = str((metadata or {}).get("preset_id") or "").strip()
                if _meta_prof != "channel-cn-cyber-finance-kr" and _meta_preset != "financial_forensic_vox":
                    continue

            match_ko = bool(re.search(rule["regex_ko"], text, re.IGNORECASE))
            match_vi = bool(re.search(rule["regex_vi"], text, re.IGNORECASE))

            if not (match_ko or match_vi):
                continue

            base_score = float(rule["priority_score"])
            if match_ko:
                base_score += 30.0
            if match_vi:
                base_score += 25.0

            # Strict Zero-Repetition (max_uses = 1 across video) + Recency penalty
            penalty = 0.0
            if self.archetype_usage_counts.get(arch_id, 0) >= 1:
                penalty += 250.0
            if history:
                if history[-1] == arch_id:
                    penalty += 180.0
                if len(history) >= 2 and history[-2] == arch_id:
                    penalty += 40.0
                if len(history) >= 3 and history[-3] == arch_id:
                    penalty += 15.0
                if self._same_cluster(history[-1], arch_id):
                    penalty += 25.0

            final_score = max(0.0, base_score - penalty)
            reason = f"Matched tokens on {arch_id} ({rule['label']}) [base={base_score:.0f}, penalty={penalty:.0f}]"
            candidates.append((final_score, arch_id, rule["label"], reason))

        valid_candidates = [
            c for c in candidates
            if c[0] > 0.0 and (not history or c[1] != history[-1])
        ]

        if not valid_candidates:
            chosen_id = "cinema_full" if history and history[-1] != "cinema_full" else "#D2"
            chosen_label = VOX_ARCHETYPE_RULES[chosen_id]["label"]
            chosen_reason = f"Default fallback / anti-repetition rotation away from {history[-1] if history else 'none'}"
            chosen_cluster = VOX_ARCHETYPE_RULES[chosen_id]["cluster"]
            winning_score = 0.0
        else:
            valid_candidates.sort(key=lambda x: x[0], reverse=True)
            winning_score, chosen_id, chosen_label, chosen_reason = valid_candidates[0]
            chosen_cluster = VOX_ARCHETYPE_RULES[chosen_id]["cluster"]

        self.recent_archetypes.append(chosen_id)
        if len(self.recent_archetypes) > self.history_size:
            self.recent_archetypes.pop(0)
        if chosen_id != "cinema_full":
            self.archetype_usage_counts[chosen_id] = self.archetype_usage_counts.get(chosen_id, 0) + 1

        return {
            "archetype": chosen_id,
            "label": chosen_label,
            "cluster": chosen_cluster,
            "score": winning_score,
            "reason": chosen_reason,
            "is_purposeful_callback": is_callback,
        }

    def route_timeline(
        self,
        beats: list[dict[str, Any]],
        job: dict[str, Any],
        profile: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Tags all beats in a project timeline with their resolved scene archetypes, `dna_visual_slot`, and `voice_spec`.

        Enforces:
        1. Universal 4-Tier Semantic Visual Priority Rule (Real Video -> Real Photo -> Blender Vox -> AI Image).
        2. Locked Channel DNA Visual Mix (50% Real Footage + 30% Vox Motion + 10% AI Visual + 10% Flexible Reserve)
           in full documentaries (`len(beats) > 15`), spacing out Vox beats (`min_vox_gap >= 2`) so Vox never exceeds 30%.
        3. Full Voice Duration & Clause Sync: attaches `voice_spec` (`duration_sec`, `clauses`,
           `clause_windows`, `clause_focus_tags`, `metrics`, `variation_seed`) to every beat.
        """
        if not is_vox_satellite_enabled(job, profile):
            return beats

        self.reset_history()
        routed_beats: list[dict[str, Any]] = []
        used_archetypes: dict[str, int] = {}
        total_beats = len(beats)
        is_full_documentary = total_beats > 15
        vox_quota = max(1, round(total_beats * 0.30)) if is_full_documentary else total_beats

        _prof_id = str(
            job.get("channel_profile_id")
            or (profile or {}).get("id")
            or (job.get("channel_profile_snapshot") or {}).get("id")
            or ""
        ).strip()
        _preset_id = str(
            (job.get("editing_dna") or {}).get("preset_id")
            or ((profile or {}).get("editing_dna") or {}).get("preset_id")
            or ""
        ).strip().lower()

        if not is_full_documentary:
            for idx, beat in enumerate(beats):
                text = str(beat.get("narration_text") or beat.get("text") or "").strip()
                voice_spec = build_voice_spec_for_beat(beat, beat_index=idx)
                decision = self.route_beat(
                    text,
                    metadata={
                        **beat,
                        "is_purposeful_callback": voice_spec["is_purposeful_callback"],
                        "channel_profile_id": _prof_id,
                        "preset_id": _preset_id,
                    },
                )
                arch = decision["archetype"]
                label = decision["label"]
                cluster = decision["cluster"]
                score = float(decision.get("score") or 0.0)
                if score <= 0.0:
                    arch = "cinema_full"
                    label = VOX_ARCHETYPE_RULES["cinema_full"]["label"]
                    cluster = "cinema"
                else:
                    used_archetypes[arch] = used_archetypes.get(arch, 0) + 1
                voice_spec["occurrence_index"] = used_archetypes.get(arch, 1)
                voice_spec["contextual_sfx"] = select_contextual_sfx_for_beat(text, arch, beat_index=idx)
                routed_beats.append(
                    {
                        **beat,
                        "scene_archetype": arch,
                        "archetype_label": label,
                        "archetype_cluster": cluster,
                        "dna_visual_slot": "vox_motion" if arch != "cinema_full" else "real_footage",
                        "dna_mix_target": dict(DNA_VISUAL_MIX_50_30_10_10),
                        "voice_spec": voice_spec,
                    }
                )
            return routed_beats

        # Full-documentary pass: score all beats first, then pick strictly 30% Vox beats spaced across timeline
        pre_scores: list[tuple[float, int]] = []
        voice_specs: list[dict[str, Any]] = []
        for idx, beat in enumerate(beats):
            text = str(beat.get("narration_text") or beat.get("text") or "").strip()
            v_spec = build_voice_spec_for_beat(beat, beat_index=idx)
            voice_specs.append(v_spec)
            self.reset_history()
            probe = self.route_beat(
                text,
                metadata={
                    **beat,
                    "is_purposeful_callback": v_spec["is_purposeful_callback"],
                    "channel_profile_id": _prof_id,
                    "preset_id": _preset_id,
                },
            )
            p_score = float(probe.get("score") or 0.0) if probe.get("archetype") != "cinema_full" else 0.0
            if re.search(r"\d", text):
                p_score += 4.0
            pre_scores.append((p_score, idx))

        selected_vox_indices: set[int] = set()
        sorted_candidates = sorted(pre_scores, key=lambda x: (-x[0], x[1]))
        for min_gap in (2, 1):
            for sc, idx in sorted_candidates:
                if len(selected_vox_indices) >= vox_quota:
                    break
                if idx in selected_vox_indices:
                    continue
                if min_gap == 2 and sc <= 0.0:
                    continue
                if all(abs(idx - chosen) >= min_gap for chosen in selected_vox_indices):
                    selected_vox_indices.add(idx)
            if len(selected_vox_indices) >= vox_quota:
                break

        self.reset_history()
        for idx, beat in enumerate(beats):
            text = str(beat.get("narration_text") or beat.get("text") or "").strip()
            voice_spec = voice_specs[idx]
            if idx in selected_vox_indices:
                decision = self.route_beat(
                    text,
                    metadata={
                        **beat,
                        "is_purposeful_callback": voice_spec["is_purposeful_callback"],
                        "channel_profile_id": _prof_id,
                        "preset_id": _preset_id,
                    },
                )
                arch = decision["archetype"]
                if arch == "cinema_full":
                    arch = "#D1"
                label = VOX_ARCHETYPE_RULES.get(arch, VOX_ARCHETYPE_RULES["#D1"])["label"]
                cluster = VOX_ARCHETYPE_RULES.get(arch, VOX_ARCHETYPE_RULES["#D1"])["cluster"]
                used_archetypes[arch] = used_archetypes.get(arch, 0) + 1
                dna_slot = "vox_motion"
            else:
                arch = "cinema_full"
                label = VOX_ARCHETYPE_RULES["cinema_full"]["label"]
                cluster = "cinema"
                dna_slot = "real_footage"

            voice_spec["occurrence_index"] = used_archetypes.get(arch, 1)
            voice_spec["contextual_sfx"] = select_contextual_sfx_for_beat(text, arch, beat_index=idx)
            motion_treatment, render_vox_board = (
                resolve_scene_motion_treatment(text, arch, cluster, voice_spec.get("clauses") or [text], idx)
                if dna_slot == "vox_motion"
                else ("optical_camera_drift", False)
            )
            routed_beats.append(
                {
                    **beat,
                    "scene_archetype": arch,
                    "archetype_label": label,
                    "archetype_cluster": cluster,
                    "dna_visual_slot": dna_slot,
                    "motion_treatment": motion_treatment,
                    "render_vox_board": render_vox_board,
                    "dna_mix_target": dict(DNA_VISUAL_MIX_50_30_10_10),
                    "voice_spec": voice_spec,
                }
            )

        assign_non_vox_dna_slots(routed_beats, total_beats)
        return routed_beats


_GEO_SATELLITE_MAP_NEEDED_RE = re.compile(
    r"(톈진|미얀마|두바이|런던|운남|쿤밍|베이징|바이인|국경|위성|지도|경로|루트|도주|이동|해외|캄보디아|필리핀|동남아|대륙\s*횡단|"
    r"Thiên\s*Tân|Myanmar|Dubai|London|Vân\s*Nam|Bắc\s*Kinh|biên\s*giới|vệ\s*tinh|bản\s*đồ|lộ\s*trình|đường\s*trốn|xuyên\s*quốc\s*gia)",
    re.IGNORECASE,
)


def resolve_scene_motion_treatment(
    narration_text: str,
    arch_id: str,
    cluster: str,
    clauses: list[str],
    beat_index: int = 0,
) -> tuple[str, bool]:
    """Resolves the 30% Motion + Map slot under Option B:
    - Drops static/newspaper/table Vox boards (`render_vox_board = False`) and uses direct scene motion
      on Real Footage / AI Keyframes (`kinetic_metric_overlay`, `split_screen_ab`, `forensic_macro_loupe`,
      `multi_cut_clause_montage`, `optical_depth_push`).
    - Enables `render_vox_board = True` (`satellite_gis_map_flight`) ONLY when a geographic/satellite map
      is genuinely needed by the spoken narration.
    """
    text = str(narration_text or "").strip()
    is_map_arch = (
        cluster in {"gis_map", "satellite", "map"}
        or arch_id.startswith("#M")
        or "GIS" in arch_id
        or "SATELLITE" in arch_id
    )
    if is_map_arch and _GEO_SATELLITE_MAP_NEEDED_RE.search(text):
        return ("satellite_gis_map_flight", True)
    if _GEO_SATELLITE_MAP_NEEDED_RE.search(text) and re.search(r"(지도|위성|루트|경로|횡단|bản\s*đồ|vệ\s*tinh|lộ\s*trình)", text, re.IGNORECASE):
        return ("satellite_gis_map_flight", True)

    if re.search(r"(출금\s*정지|마비|멈춰|증발|폭락|붕괴|돌려막기|러그풀|rug\s*pull|đóng\s*băng|sập\s*sàn)", text, re.IGNORECASE):
        return ("exchange_candlestick_crash", False)
    if re.search(r"(믹서|텀블러|차명\s*계좌|세탁|분산|쪼개|페이퍼컴퍼니|익명\s*지갑|mixer|tumbler|rửa\s*tiền)", text, re.IGNORECASE):
        return ("crypto_tumbler_splitter", False)
    if re.search(r"(블록체인|온체인|원장|해시|스마트\s*컨트랙트|콜드월렛|비트코인|이더리움|테더|BTC|ETH|USDT|0\.3초|on-chain|blockchain|ví\s*lạnh)", text, re.IGNORECASE):
        return ("crypto_onchain_ledger_trace", False)
    if re.search(r"(95\.6%|207개|196개|비율|비중|유령\s*회사|유령\s*법인|전수\s*실사|tỷ\s*lệ|công\s*ty\s*ma)", text, re.IGNORECASE):
        return ("donut_matrix_audit_chart", False)
    if re.search(r"(환수|적자|결손|차이|비교|대비|총\s*모집|thâm\s*hụt|thu\s*hồi)", text, re.IGNORECASE):
        return ("waterfall_bar_chart", False)
    if re.search(r"(수익률|이율|이자|연\s*\d+%|금리|배당|격차|괴리|lãi\s*suất|phân\s*kỳ)", text, re.IGNORECASE):
        return ("dual_spline_divergence_chart", False)
    if re.search(r"(달리|반면|대조|겉으로는|실제로는|양면|VS|ngược\s*lại|đối\s*chiếu)", text, re.IGNORECASE):
        return ("split_screen_ab", False)
    if re.search(r"(화면|장부|통장|단서|포착|확대|수첩|영수증|지문|CCTV|근접|cận\s*cảnh|phóng\s*đại|vật\s*chứng)", text, re.IGNORECASE):
        return ("forensic_macro_loupe", False)
    if re.search(r"(\d[\d,\.]*\s*(조|억|만|천|백|원|위안|달러|%|개|명|배|초|분|시간))", text, re.IGNORECASE):
        return ("kinetic_metric_overlay", False)
    if len(clauses) >= 3:
        return ("multi_cut_clause_montage", False)
    fallbacks = (
        "dual_spline_divergence_chart",
        "waterfall_bar_chart",
        "donut_matrix_audit_chart",
        "exchange_candlestick_crash",
        "crypto_tumbler_splitter",
        "crypto_onchain_ledger_trace",
        "kinetic_metric_overlay",
        "forensic_macro_loupe",
    )
    return (fallbacks[beat_index % len(fallbacks)], False)


DNA_VISUAL_MIX_50_30_10_10: dict[str, float] = {
    "footage": 0.50,
    "vox": 0.30,
    "ai": 0.10,
    "flexible": 0.10,
}

_AI_RECONSTRUCTION_SLOT_RE = re.compile(
    r"(심리|내면|비밀|암호|기억|상상|재구성|독백|방\s*안|어둠|공포|불안|환각|악몽|"
    r"tâm\s*lý|bí\s*mật|ẩn\s*náu|tái\s*hiện|độc\s*thoại|bóng\s*tối|nỗi\s*sợ)",
    re.IGNORECASE,
)

_FLEXIBLE_RESERVE_SLOT_RE = re.compile(
    r"(다시|앞서|반면|그러나|전환|연결|비교|대조|요약|결국|한편|"
    r"nhắc\s*lại|trước\s*đó|ngược\s*lại|tuy\s*nhiên|đối\s*chiếu|tóm\s*lại|chuyển\s*sang)",
    re.IGNORECASE,
)


def assign_non_vox_dna_slots(routed_beats: list[dict[str, Any]], total_beats: int | None = None) -> None:
    """Partitions all non-Vox (`cinema_full`) beats into the locked DNA slots:
    50% `real_footage`, 10% `ai_visual`, and 10% `flexible_reserve` ( alongside 30% `vox_motion`).
    Modifies `routed_beats` in-place.
    """
    n = total_beats if total_beats is not None else len(routed_beats)
    if n <= 0:
        return

    non_vox_indices = [
        i
        for i, b in enumerate(routed_beats)
        if str(b.get("scene_archetype") or "cinema_full") == "cinema_full"
    ]
    m = len(non_vox_indices)
    if m == 0:
        return

    ai_quota = min(m, max(1 if m >= 3 else 0, round(n * 0.10)))
    flex_quota = min(max(0, m - ai_quota), max(1 if m >= 4 else 0, round(n * 0.10)))

    for idx in non_vox_indices:
        routed_beats[idx]["dna_visual_slot"] = "real_footage"
        routed_beats[idx]["dna_mix_target"] = dict(DNA_VISUAL_MIX_50_30_10_10)

    # Pick `ai_quota` evenly spaced buckets among non_vox_indices with highest AI reconstruction affinity
    chosen_ai: set[int] = set()
    if ai_quota > 0:
        for b_idx in range(ai_quota):
            start_pos = int(round(b_idx * m / ai_quota))
            end_pos = int(round((b_idx + 1) * m / ai_quota))
            bucket = non_vox_indices[max(0, start_pos):max(start_pos + 1, end_pos)]
            if not bucket:
                continue
            best_i = max(
                bucket,
                key=lambda i: (
                    1 if _AI_RECONSTRUCTION_SLOT_RE.search(str(routed_beats[i].get("narration_text") or routed_beats[i].get("text") or "")) else 0,
                    1 if str(routed_beats[i].get("visual_route") or "") == "ai_visual" else 0,
                    -abs(i - bucket[len(bucket) // 2]),
                ),
            )
            chosen_ai.add(best_i)
            routed_beats[best_i]["dna_visual_slot"] = "ai_visual"

    remaining_indices = [i for i in non_vox_indices if i not in chosen_ai]
    r_len = len(remaining_indices)
    if flex_quota > 0 and r_len > 0:
        for b_idx in range(min(flex_quota, r_len)):
            start_pos = int(round(b_idx * r_len / flex_quota))
            end_pos = int(round((b_idx + 1) * r_len / flex_quota))
            bucket = remaining_indices[max(0, start_pos):max(start_pos + 1, end_pos)]
            if not bucket:
                continue
            best_i = max(
                bucket,
                key=lambda i: (
                    1 if _FLEXIBLE_RESERVE_SLOT_RE.search(str(routed_beats[i].get("narration_text") or routed_beats[i].get("text") or "")) else 0,
                    1 if (routed_beats[i].get("voice_spec") or {}).get("is_purposeful_callback") else 0,
                    -abs(i - bucket[len(bucket) // 2]),
                ),
            )
            routed_beats[best_i]["dna_visual_slot"] = "flexible_reserve"
