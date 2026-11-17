"""True Crime Animated Vox & Real Satellite Semantic Scene Router.

Analyzes spoken voice narration (Korean / Vietnamese) to semantically route beats to matching animated Vox & Satellite Map scenes with sliding-window variety, voice-duration & clause synchronization (`voice_spec`), and preset/visual strategy isolation.
"""

from __future__ import annotations

import importlib
import re
import sys
from typing import Any, Dict, List, Optional
from documentary.audio_library_manager import select_contextual_sfx_for_beat

_reloaded_submods: dict[str, Any] = {}
for _submod_name in (
    "documentary.vox_engine.typography",
    "documentary.vox_engine.archetypes",
    "documentary.vox_engine.composable_scene_graph",
    "documentary.store",
    "documentary.ai_visual",
    "documentary.footage",
    "documentary.thumbnail_studio",
):
    try:
        _submod = sys.modules.get(_submod_name)
        if _submod is not None:
            _reloaded_submods[_submod_name] = importlib.reload(_submod)
        else:
            _reloaded_submods[_submod_name] = importlib.import_module(_submod_name)
    except Exception:
        pass
try:
    from documentary.hot_reload import _rebind_live_instances
    if _reloaded_submods:
        _rebind_live_instances(_reloaded_submods)
except Exception:
    pass


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
        "cluster": "satellite_corridor",
        "label": "Tactical Rooftop Store / Compound Satellite Plate (0% Camera Zoom)",
        "regex_ko": r"(매점|학교|캠퍼스|지붕|옥상|건물|급습|현장\s*포위|주소|골목\s*안|매점\s*주인|아파트\s*단지|산스화위안|4동)",
        "regex_vi": r"(tiệm\s*tạp\s*hóa|mái\s*nhà|trường\s*học|khuôn\s*viên|nóc\s*nhà|đột\s*kích|bao\s*vây|tạp\s*hóa\s*trường|khu\s*chung\s*cư|tòa\s*4)",
        "priority_score": 92,
    },
    "#M6": {
        "cluster": "satellite_corridor",
        "label": "Split Dual Satellite Plate (Macro vs Micro, 0% Camera Zoom)",
        "regex_ko": r"(광역.*좁혀졌|도심.*매점|위성.*분할|포착|광역.*정밀|항저우.*단지)",
        "regex_vi": r"(thu\s*hẹp.*phạm\s*vi|từ\s*toàn\s*cảnh.*đến\s*chi\s*tiết|chia\s*đôi\s*vệ\s*tinh|vệ\s*tinh\s*kép)",
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
        return ["Evidence Analysis In Progress"]

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
    is_ko = any("\uac00" <= c <= "\ud7a3" for c in clause_text)
    return f"핵심 요지 0{idx + 1}" if is_ko else f"Key Point 0{idx + 1}"


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

    is_ko = (
        str(beat.get("language") or "").lower().startswith("ko")
        or any("\uac00" <= c <= "\ud7a3" for c in narration)
    )

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
        fallback_metrics = ["수사 단서", "정밀 분석", "증거 대조"] if is_ko else ["FORENSIC EVIDENCE", "DETAILED ANALYSIS", "CROSS-CHECK"]
        metrics = words[:4] if words else fallback_metrics

    beat_id = str(beat.get("beat_id") or beat.get("id") or f"B{beat_index + 1:03d}").strip()
    act_label = str(beat.get("act") or beat.get("chapter") or f"ACT {(beat_index // 65) + 1}").strip()
    default_loc = "형사 과학수사 증거 분석실" if is_ko else "FORENSIC ANALYSIS LAB"
    location_label = str(beat.get("location") or beat.get("header_ko") or default_loc).strip()
    is_callback = bool(beat.get("is_purposeful_callback") or _CALLBACK_RE.search(narration))

    # Build a concise header from the first clause or beat title
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
        "contextual_sfx": select_contextual_sfx_for_beat(
            narration,
            str(beat.get("scene_archetype") or beat.get("voxArchetype") or beat.get("archetype") or "").strip(),
            beat_index=beat_index,
        ),
    }


def is_vox_satellite_enabled(job: dict[str, Any], profile: dict[str, Any] | None = None) -> bool:
    """Verifies whether Vox & Satellite engine should activate for this job/profile.

    Strictly activates for forensic_noir / true_crime_noir presets or visual strategies,
    while protecting non-crime profiles from unintended activation.
    """
    for cand_ed in (
        job.get("editing_dna"),
        (profile or {}).get("editing_dna") if isinstance(profile, dict) else None,
        (job.get("channel_profile_snapshot") or {}).get("editing_dna") if isinstance(job.get("channel_profile_snapshot"), dict) else None,
    ):
        if isinstance(cand_ed, dict) and isinstance(cand_ed.get("vox_satellite_enabled"), bool):
            return bool(cand_ed["vox_satellite_enabled"])

    profile_id = str(
        job.get("channel_profile_id")
        or (profile or {}).get("id")
        or (job.get("channel_profile_snapshot") or {}).get("id")
        or ""
    ).strip()

    # Legacy fallback when job dict has only channel_profile_id without editing_dna snapshot
    if profile_id in {"channel-e544a64b7c", "channel-kr-truecrime-director-v2", "channel-kr-financial-fugitive-director-v2"}:
        return True

    # Strict blacklist for known non-crime channels
    if profile_id in {"channel-1e24de3ab5", "channel-aa913eb90d", "channel-f6ec4dfff3", "channel-cn-cyber-finance-kr"}:
        return False

    # Check editing preset and visual strategy
    preset_id = str(
        (job.get("editing_dna") or {}).get("preset_id")
        or ((profile or {}).get("editing_dna") or {}).get("preset_id")
        or ((job.get("channel_profile_snapshot") or {}).get("editing_dna") or {}).get("preset_id")
        or ""
    ).strip().lower()
    if preset_id in {"forensic_noir", "forensic_noir_director_v2", "vox_china_crime_newsroom_v10"}:
        return True

    strategy = str(
        job.get("visual_strategy")
        or (job.get("production_recipe") or {}).get("visual_strategy")
        or ""
    ).strip().lower()
    if strategy in {"forensic_noir", "true_crime_noir_ai"}:
        return True

    return False


def calculate_proportional_vox_scenes(duration_minutes: float) -> int:
    """Calculate dynamic script-proportional Vox scene count based on duration (replaces fixed 31 quota).
    - 12 min -> 8–15 scenes
    - 20 min -> 16–24 scenes
    - 30 min -> 25–38 scenes
    """
    m = float(duration_minutes or 20.0)
    if m <= 0.0:
        return 10
    if m <= 14.0:
        return max(8, min(15, int(round(m * 0.95))))
    elif m <= 24.0:
        return max(16, min(24, int(round(m * 0.95))))
    else:
        return max(25, min(38, int(round(m * 1.0))))


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
                _meta_preset = str((metadata or {}).get("preset_id") or "").strip()
                if _meta_preset != "financial_forensic_vox":
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
        2. Dynamic Script-Proportional Vox Scene Counts: scales naturally with episode duration (replaces fixed 31 limits).
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
        target_dur = float(
            job.get("target_duration_minutes")
            or (profile or {}).get("target_duration_minutes")
            or 0.0
        )
        if target_dur > 0 and is_full_documentary:
            vox_quota = min(total_beats, calculate_proportional_vox_scenes(target_dur))
        elif is_full_documentary:
            vox_quota = max(1, round(total_beats * 0.30))
        else:
            vox_quota = total_beats

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
            prev_vox_spec: dict[str, Any] | None = None
            for idx, r_beat in enumerate(routed_beats):
                attach_two_layer_visual_prompts(
                    r_beat,
                    beat_index=idx,
                    total_beats=total_beats,
                    prev_vox_spec=prev_vox_spec,
                )
                if str(r_beat.get("dna_visual_slot") or "") == "vox_motion":
                    prev_vox_spec = r_beat.get("vox_blueprint_spec")
            return routed_beats

        # Meaning-driven flexible pass (0% fixed quota cap, 0% periodic min_gap spacing):
        # Priority #1: Real archival footage (`real_footage`) when authentic footage applies.
        # Priority #2: VOX illustration (`vox_motion` — <Desk> or <GeoJson3DMapStage>) whenever real footage is absent.
        # Priority #3 (Last Resort Only): AI image (`ai_visual`) strictly for closed-room psychological beats.
        voice_specs: list[dict[str, Any]] = []
        selected_vox_indices: set[int] = set()
        for idx, beat in enumerate(beats):
            text = str(beat.get("narration_text") or beat.get("text") or "").strip()
            v_spec = build_voice_spec_for_beat(beat, beat_index=idx)
            voice_specs.append(v_spec)
            vtype = str(beat.get("visual_type") or "").strip().lower()
            vroute = str(beat.get("visual_route") or "").strip().lower()
            intent = str(beat.get("framing_motion_intent") or "").strip()
            src_prio = str(beat.get("source_priority") or "").strip().lower()

            if (
                vtype in {"vox", "vox_motion"}
                or vroute in {"vox", "vox_motion"}
                or intent.startswith(("[VOX_NEWSROOM", "V23 "))
            ):
                selected_vox_indices.add(idx)
                continue

            if vtype == "cinema_text" or vroute == "cinema_text" or intent.startswith(("[CINEMA_TEXT", "FramelessCinemaTextBeat", "FinancialMotionTextBeat")):
                continue

            if intent.startswith(("AUTHENTIC_CASE_ARCHIVAL_FOOTAGE_BACKBONE", "[REAL_FTG")) or src_prio in {"must_real", "footage_only"}:
                continue

            if intent.startswith(("CLOSED_ROOM_PROFILE_AI_RECONSTRUCTION", "[AI_IMAGE")) or vroute == "ai_visual" or vtype in {"ai_reconstruction", "ai_visual"}:
                continue

            # For beats without explicit real footage or closed-room AI lock, probe semantic VOX match
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
            if p_score >= 95.0 and vroute != "footage":
                selected_vox_indices.add(idx)

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
        prev_vox_spec: dict[str, Any] | None = None
        for idx, r_beat in enumerate(routed_beats):
            attach_two_layer_visual_prompts(
                r_beat,
                beat_index=idx,
                total_beats=total_beats,
                prev_vox_spec=prev_vox_spec,
            )
            if str(r_beat.get("dna_visual_slot") or "") == "vox_motion":
                prev_vox_spec = r_beat.get("vox_blueprint_spec")
        return routed_beats


_GEO_SATELLITE_MAP_NEEDED_RE = re.compile(
    r"(escape\s*route|escape\s*vector|fled\s*to|infiltrat|extradit|police\s*pursuit|dragnet|stakeout\s*route|"
    r"도주\s*경로|도주\s*루트|탈출\s*경로|잠입|도피\s*행각|압송|호송|추적망|포위망|수색망.*확대|기동대.*출동|건너가|넘어가|숨어들었|"
    r"검문소.*통과|검문소.*뚫|국도를\s*따라|산악.*도주|산길로\s*도주|이동\s*경로|"
    r"반경\s*[\d이삼사오육칠팔구십]+\s*(?:킬로미터|km|미터|m)\b|"
    r"(?:동|서|남|북|동남|동북|서남|서북)쪽으로.*?(?:도로|길|킬로미터|km|향해|이어)|"
    r"(?:비포장도로|시골길|국도|고속도로|도로가?).*?(?:이어|달리|향해|뻗어)|"
    r"(?:이십|십|삼십|사십|\d+)\s*(?:킬로미터|km)\s*(?:떨어진|시골길|거리|이어|달리)|"
    r"(?:무장\s*경력|기동대|수색대|형사대대|경찰).*?(?:급파|출동|투입|배치)|"
    r"실종\s*지도를?\s*펼쳐|"
    r"đường\s*trốn|lộ\s*trình\s*đào\s*tẩu|lẩn\s*trốn\s*từ|xâm\s*nhập\s*vào|áp\s*giải|truy\s*kích|khép\s*vòng\s*vây|mở\s*rộng\s*truy\s*xét)",
    re.IGNORECASE,
)

_GEO_NON_MOVEMENT_EXCLUDE_RE = re.compile(
    r"(사투리|억양|방언|말투|목소리|노래를|가수|무대\s*진행|참가\s*신청서|원서|이력서|심리|표정|눈빛|법정에서|재판장|중환자실|부검\s*결과)",
    re.IGNORECASE,
)


def _is_voice_movement_or_pursuit_sentence(text: str) -> bool:
    clean = str(text or "").strip()
    if not clean or _GEO_NON_MOVEMENT_EXCLUDE_RE.search(clean):
        return False
    return bool(_GEO_SATELLITE_MAP_NEEDED_RE.search(clean))


def resolve_scene_motion_treatment(
    narration_text: str,
    arch_id: str,
    cluster: str,
    clauses: list[str],
    beat_index: int = 0,
) -> tuple[str, bool]:
    """Resolves the bespoke VOX motion treatment for a spoken sentence (`0%` modulo fallback):
    - Routes to `satellite_gis_map_flight` (`<GeoJson3DMapStage>`) ONLY when the sentence genuinely
      describes a suspect escape/infiltration route or police pursuit/dragnet/extradition route.
    - Otherwise routes to a bespoke per-sentence `<Desk>` cut-and-paste illustration derived from the sentence's meaning.
    """
    text = str(narration_text or "").strip()
    if _is_voice_movement_or_pursuit_sentence(text):
        return ("satellite_gis_map_flight", True)

    if re.search(r"(달리|반면|대조|겉으로는|실제로는|양면|VS|비교|불일치|모순|ngược\s*lại|đối\s*chiếu|mâu\s*thuẫn|contrast|versus)", text, re.IGNORECASE):
        return ("bespoke_desk_contradiction_compare", True)
    if re.search(r"(화면|장부|통장|단서|포착|확대|수첩|영수증|지문|CCTV|근접|점|흉터|얼굴|인상착의|cận\s*cảnh|phóng\s*đại|vật\s*chứng|fingerprint|loupe|증거|검증)", text, re.IGNORECASE):
        return ("bespoke_desk_clue_isolation", True)
    if re.search(r"(가명|신분|위장|숨기|감추|뒤집|드러나|실체|정체|서류|신청서|수배|전단|판결|선고)", text, re.IGNORECASE):
        return ("bespoke_desk_layer_peel_dossier", True)
    if re.search(r"(\d[\d,\.]*\s*(년|월|일|시|분|초|조|억|만|천|백|원|위안|달러|%|개|명|배|km|미터|cm|세))", text, re.IGNORECASE):
        return ("bespoke_desk_chrono_metric_trace", True)
    return ("bespoke_desk_cutout_collage", True)


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

    has_explicit_plan_slots = any(
        str(routed_beats[i].get("visual_type") or "").strip().lower() in {"cinema_text", "ai_reconstruction"}
        or str(routed_beats[i].get("visual_route") or "").strip().lower() == "ai_visual"
        for i in non_vox_indices
    )
    if has_explicit_plan_slots and any(
        str(routed_beats[i].get("visual_type") or "").strip().lower() == "cinema_text"
        for i in non_vox_indices
    ):
        from .typography import resolve_contextual_motion_text_design

        prev_mt_design: dict[str, Any] | None = None
        for idx in non_vox_indices:
            b = routed_beats[idx]
            b["dna_mix_target"] = dict(DNA_VISUAL_MIX_50_30_10_10)
            vtype = str(b.get("visual_type") or "").strip().lower()
            vroute = str(b.get("visual_route") or "").strip().lower()
            if vroute == "ai_visual" or vtype == "ai_reconstruction":
                b["dna_visual_slot"] = "ai_visual"
                b["editorial_layer"] = "AI_MASCOT"
            elif vtype == "cinema_text":
                b["dna_visual_slot"] = "flexible_reserve"
                b["editorial_layer"] = "CINEMA_TEXT"
                mt_design = resolve_contextual_motion_text_design(
                    narration_text=str(b.get("narration_text") or b.get("text") or ""),
                    beat_id=str(b.get("beat_id") or f"B{idx + 1:03d}"),
                    beat_index=idx,
                    prev_design=prev_mt_design,
                )
                b["motion_text_spec"] = mt_design
                prev_mt_design = mt_design
            else:
                b["dna_visual_slot"] = "real_footage"
                b["editorial_layer"] = "REAL_FTG"
        for idx, b in enumerate(routed_beats):
            if str(b.get("dna_visual_slot") or "") == "vox_motion":
                b["editorial_layer"] = "VOX_NEWSROOM"
        return

    from .typography import resolve_contextual_motion_text_design

    ai_quota = min(m, max(1 if m >= 3 else 0, round(n * 0.10)))

    for idx in non_vox_indices:
        routed_beats[idx]["dna_visual_slot"] = "real_footage"
        routed_beats[idx]["dna_mix_target"] = dict(DNA_VISUAL_MIX_50_30_10_10)

    # Pick closed-room candidates purely by sentence meaning (0% periodic bucket spacing)
    chosen_ai: set[int] = set()
    if ai_quota > 0:
        scored_ai_candidates: list[tuple[int, int]] = []
        for i in non_vox_indices:
            txt_i = str(routed_beats[i].get("narration_text") or routed_beats[i].get("text") or "")
            vroute_i = str(routed_beats[i].get("visual_route") or "").strip().lower()
            vtype_i = str(routed_beats[i].get("visual_type") or "").strip().lower()
            affinity = 0
            if vroute_i == "ai_visual" or vtype_i == "ai_reconstruction":
                affinity += 100
            if _AI_RECONSTRUCTION_SLOT_RE.search(txt_i):
                affinity += 50
            if affinity > 0:
                scored_ai_candidates.append((affinity, i))
        scored_ai_candidates.sort(key=lambda item: (-item[0], item[1]))
        for _, cand_i in scored_ai_candidates:
            if len(chosen_ai) >= ai_quota:
                break
            if any(abs(cand_i - prev_i) < 3 for prev_i in chosen_ai):
                continue
            chosen_ai.add(cand_i)
            routed_beats[cand_i]["dna_visual_slot"] = "ai_visual"

    # Flexible Narrative Drop-Point Placement for Motion Text (0% mechanical periodic bucket spacing):
    # Attach `flexible_reserve` / `CINEMA_TEXT` strictly at genuine narrative drop points (`is_valid_drop_point`)
    # with at least >= 4 beats separation and 100% context-matched font/color/layout/motion.
    remaining_indices = [i for i in non_vox_indices if i not in chosen_ai]
    last_ct_beat_idx = -999
    prev_mt_design = None
    max_flexible_drop_points = max(1, round(n * 0.10))
    chosen_ct_count = 0
    for idx in remaining_indices:
        if chosen_ct_count >= max_flexible_drop_points:
            break
        if idx - last_ct_beat_idx < 4:
            continue
        b = routed_beats[idx]
        nar_txt = str(b.get("narration_text") or b.get("text") or "")
        is_callback = bool((b.get("voice_spec") or {}).get("is_purposeful_callback"))
        mt_design = resolve_contextual_motion_text_design(
            narration_text=nar_txt,
            beat_id=str(b.get("beat_id") or f"B{idx + 1:03d}"),
            beat_index=idx,
            prev_design=prev_mt_design,
        )
        if mt_design.get("is_valid_drop_point") or is_callback:
            b["dna_visual_slot"] = "flexible_reserve"
            b["editorial_layer"] = "CINEMA_TEXT"
            b["motion_text_spec"] = mt_design
            prev_mt_design = mt_design
            last_ct_beat_idx = idx
            chosen_ct_count += 1


_LENS_AND_ANGLE_RIGS: tuple[str, ...] = (
    "35mm anamorphic low-angle ground-level tracking shot with shallow depth of field",
    "85mm portrait telephoto tight over-the-shoulder documentary framing",
    "24mm wide architectural interior perspective with dramatic chiaroscuro doorway shadows",
    "100mm macro forensic close-up at 15-degree oblique inspection angle under raking side-light",
    "50mm eye-level observational handheld documentary framing through rain-streaked glass",
    "Overhead 90-degree bird's-eye tabletop evidence flat-lay under warm 3200K tungsten cone",
    "Split-diopter dual-plane focus linking foreground physical clue to background silhouette",
    "High-angle stairwell/corridor surveillance perspective with cold sodium-vapor rim light",
    "Dutch-tilt 12-degree tense investigative corridor shot with flashlight beam cutting mist",
    "Extreme close-up profile framing capturing micro-tension, sweat, and fabric texture",
    "Medium-wide forensic reconstruction shot with crime-scene scale ruler in foreground",
    "Telephoto compressed exterior night-watch framing through dense mountain bamboo foliage",
)

_VOX_DESK_SPATIAL_LAYOUT_CATALOG: tuple[dict[str, Any], ...] = (
    {
        "layout_id": "direct_50_50_collision_seam",
        "stage_component": "TornPaperSplitReveal",
        "layout_variant": "peelDirection='horizontal'",
        "board_surface": "SplitVersusBoard (#EFECE3 left vs #1B1B1A right)",
        "layout_summary": "50/50 Direct Horizontal Collision across central red-yarn seam (Left A x:95..915 vs Right B x:965..1800)",
        "entry_sequence": ("scissors_slide_left", "scissors_slide_right", "sticker_peel_up"),
        "regex": r"(달리|반면|대조|겉으로는|실제로는|양면|VS|비교|불일치|모순|두\s*얼굴|이중생활)",
    },
    {
        "layout_id": "stepped_seesaw_balance",
        "stage_component": "ScrapbookCollageAssembly",
        "layout_variant": "variant='center_pinned_web'",
        "board_surface": "BlackCard (#1B1B1A darkroom contrast board)",
        "layout_summary": "Stepped Seesaw Balance (High-Left card y:72..415 vs Low-Right card y:340..685 bridged by Center-Pinned RGBA Cutout)",
        "entry_sequence": ("slap_drop_top", "sticker_peel_up", "diagonal_toss_spin"),
        "regex": r"(가명|신분\s*세탁|위장|거짓말|탄로|들통|정체|실체|가면|속이|은폐)",
    },
    {
        "layout_id": "trifold_accordion_pamphlet",
        "stage_component": "PaperUnfoldCollage",
        "layout_variant": "variant='dossier_spread'",
        "board_surface": "ManilaKraftBoard (#C8AD82 archival kraft dossier)",
        "layout_summary": "3-Panel Tri-Fold Accordion Dossier Pamphlet (Left x:95..625 | Center x:635..1265 | Right x:1275..1805)",
        "entry_sequence": ("accordion_fold_left", "unroll_scroll_down", "accordion_fold_right"),
        "regex": r"(수첩|수배령|현상금|수배\s*전단|공안부|판결|선고|보고서|진술서|신청서|원서|문서|기록부)",
    },
    {
        "layout_id": "vertical_scroll_plus_pedestal",
        "stage_component": "PaperUnfoldCollage",
        "layout_variant": "variant='evidence_triptych'",
        "board_surface": "Desk (#E4DDCF warm newsprint copy-stand)",
        "layout_summary": "Tall Vertical Unrolling Scroll on Left (x:100..860, h=665) + Isolated Right Cutout Pedestal (x:960..1800)",
        "entry_sequence": ("unroll_scroll_down", "slap_drop_top", "scissors_slide_right"),
        "regex": r"(목록|명단|계좌|장부|내역|통장|영수증|이력|편지|일기|메모|자백서)",
    },
    {
        "layout_id": "poker_fan_3_cards_hand",
        "stage_component": "PaperUnfoldCollage",
        "layout_variant": "variant='ledger_unfold'",
        "board_surface": "BlackCard (#1B1B1A darkroom contrast board)",
        "layout_summary": "3-Card Poker Fan-Out Hand from Bottom-Center Pivot (-13deg Left, 0deg Center, +13deg Right)",
        "entry_sequence": ("fan_deal_bottom", "scissors_slide_left", "scissors_slide_right"),
        "regex": r"(세\s*가지|3대|연속|차례로|하나씩|여러\s*건|일련의|종류|각각|첫째|둘째)",
    },
    {
        "layout_id": "macro_loupe_left_half",
        "stage_component": "LoupePhotoCutout",
        "layout_variant": "loupeFocusX=0.36, loupeFocusY=0.44",
        "board_surface": "ManilaKraftBoard (#C8AD82 archival kraft dossier)",
        "layout_summary": "Giant Left Half-Screen Macro Forensic Plate (x:100..915) + 140px Gliding OpticalLoupe (0% camera zoom) + Right Cutout & Verdict",
        "entry_sequence": ("accordion_fold_left", "slap_drop_top", "scissors_slide_right"),
        "regex": r"(지문|특징점|사마귀|점|흉터|혈흔|유전자|DNA|미세|돋보기|확대|정밀\s*감식)",
    },
    {
        "layout_id": "macro_loupe_right_half",
        "stage_component": "LoupePhotoCutout",
        "layout_variant": "loupeFocusX=0.68, loupeFocusY=0.48",
        "board_surface": "BlackCard (#1B1B1A darkroom contrast board)",
        "layout_summary": "Left Die-Cut Subject & Clipping (x:100..925) + Giant Right Half-Screen Macro Forensic Plate (x:965..1810) + 140px Gliding OpticalLoupe (0% camera zoom)",
        "entry_sequence": ("scissors_slide_left", "accordion_fold_right", "sticker_peel_up"),
        "regex": r"(단서|포착|발견|흔적|결정적|일치|대조|조흔|번호판|안경|시계|반지)",
    },
    {
        "layout_id": "diagonal_3_step_staircase",
        "stage_component": "TornPaperSplitReveal",
        "layout_variant": "peelDirection='diagonal'",
        "board_surface": "ManilaKraftBoard (#C8AD82 archival kraft dossier)",
        "layout_summary": "Diagonal 3-Step Staircase Cascade (Step 1 Top-Left x:95,y:68 -> Step 2 Center x:650,y:215 -> Step 3 Bottom-Right x:1080,y:455)",
        "entry_sequence": ("diagonal_toss_spin", "slap_drop_top", "fan_deal_bottom"),
        "regex": r"(시간|분\s*단위|순서|이어서|직후|년\s*뒤|개월|단계|과정|흐름|연쇄)",
    },
    {
        "layout_id": "architectural_l_shape_frame",
        "stage_component": "TornPaperSplitReveal",
        "layout_variant": "peelDirection='vertical'",
        "board_surface": "BlueprintGridBoard (#F4F0E6 architectural grid)",
        "layout_summary": "Architectural L-Shape Frame (Tall Left Pillar x:95..615, h=660 + Wide Bottom Bar x:645..1800, y:490..755) enclosing Upper-Right Focal Cutout",
        "entry_sequence": ("unroll_scroll_down", "scissors_slide_right", "sticker_peel_up"),
        "regex": r"(건물|아파트|방\s*안|구조|지하|창문|출입구|복도|현장|밀실|내부|골목)",
    },
    {
        "layout_id": "cinema_monitor_68_plus_right_tower",
        "stage_component": "ScrapbookCollageAssembly",
        "layout_variant": "variant='corkboard_grid'",
        "board_surface": "Desk (#E4DDCF warm newsprint copy-stand)",
        "layout_summary": "68%-Wide Archival Cinema Monitor Plate on Left (x:95..1175, w=1080, h=620) + Narrow Right Vertical Evidence Tower (x:1220..1810)",
        "entry_sequence": ("scissors_slide_left", "slap_drop_top", "sticker_peel_up"),
        "regex": r"(방송|뉴스|TV|프로그램|화면|영상|카메라|인터뷰|취재|보도|언론|시청자)",
    },
    {
        "layout_id": "inverted_triangle_corkboard_web",
        "stage_component": "ScrapbookCollageAssembly",
        "layout_variant": "variant='diagonal_cascade'",
        "board_surface": "ManilaKraftBoard (#C8AD82 archival kraft dossier)",
        "layout_summary": "Inverted Triangle Investigation Web (2 Upper Corner Plates Top-Left & Top-Right converging via <TwistedRedYarn> into Bottom-Center Apex Cutout)",
        "entry_sequence": ("scissors_slide_left", "scissors_slide_right", "fan_deal_bottom"),
        "regex": r"(공범|조직|관계|연결|배후|친척|가족|아내|남편|피해자|목격자|제보자)",
    },
    {
        "layout_id": "center_monolith_diagonal_satellites",
        "stage_component": "CutoutPopOutStage",
        "layout_variant": "layoutVariant='center_split'",
        "board_surface": "BlackCard (#1B1B1A darkroom contrast board)",
        "layout_summary": "Center Spotlight Monolith (x:580..1340) flanked by Top-Left (x:90..540) and Bottom-Right (x:1365..1815) Diagonal Satellites",
        "entry_sequence": ("slap_drop_top", "diagonal_toss_spin", "scissors_slide_right"),
        "regex": r"(핵심|결국|마침내|드디어|체포|검거|자백|충격|진실|결론|비극)",
    },
    {
        "layout_id": "horizontal_top_bottom_split",
        "stage_component": "CutoutPopOutStage",
        "layout_variant": "layoutVariant='right_hero'",
        "board_surface": "ManilaKraftBoard (#C8AD82 archival kraft dossier)",
        "layout_summary": "Top-vs-Bottom Horizontal Split (Panoramic Upper Evidence Strip y:68..385 + Lower Split Cutout & Verdict Deck y:420..760)",
        "entry_sequence": ("unroll_scroll_down", "scissors_slide_left", "accordion_fold_right"),
        "regex": r"(전국|전역|확산|여론|사회|충격파|이후|결과|상황|수사망)",
    },
    {
        "layout_id": "asymmetric_left_bleed_52_48",
        "stage_component": "CutoutPopOutStage",
        "layout_variant": "layoutVariant='left_hero'",
        "board_surface": "Desk (#E4DDCF warm newsprint copy-stand)",
        "layout_summary": "2-Block Asymmetric 52/48 Split (Giant Left Bleed Archival Plate x:95..880 + Overlapping Right RGBA Cutout & Korean Clipping x:960..1800)",
        "entry_sequence": ("scissors_slide_left", "slap_drop_top", "sticker_peel_up"),
        "regex": r".*",
    },
)


def _select_diverse_desk_layout_and_entry(
    text: str,
    beat_index: int,
    prev_vox_spec: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Selects a sentence-matched `<Desk>` Spatial Layout (`bố cục`) and 12fps Cut-and-Paste Entrance Sequence
    (`hiệu ứng cắt dán xuất hiện`), guaranteeing ZERO consecutive repetition of layout or entrance sequence
    and 0% camera zoom-in/zoom-out.
    """
    prev_layout_id = str((prev_vox_spec or {}).get("spatial_layout") or "").strip()
    prev_entry_sig = str((prev_vox_spec or {}).get("entry_reveal") or "").strip()
    prev_stage_comp = str((prev_vox_spec or {}).get("stage_component") or "").strip()

    scored: list[tuple[int, int, dict[str, Any]]] = []
    for idx_cat, item in enumerate(_VOX_DESK_SPATIAL_LAYOUT_CATALOG[:-1]):
        matched = bool(re.search(item["regex"], text, re.IGNORECASE))
        score = 100 if matched else 10
        # Deterministic sentence-hash tie-breaker so different sentences naturally spread across all 14 layouts
        sent_hash = (beat_index * 7 + sum(ord(ch) for ch in text[:24])) % 13
        if idx_cat == sent_hash:
            score += 25
        entry_sig = " -> ".join(item["entry_sequence"])
        if item["layout_id"] == prev_layout_id:
            score -= 500
        if entry_sig == prev_entry_sig:
            score -= 300
        if item["stage_component"] == prev_stage_comp:
            score -= 45
        scored.append((score, -idx_cat, item))

    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
    chosen = scored[0][2]
    entry_seq = list(chosen["entry_sequence"])
    entry_sig = " -> ".join(entry_seq)

    # Extra safeguard: if entry_sig still matches prev_entry_sig, rotate the entrance modes
    all_entry_modes = (
        "scissors_slide_left",
        "scissors_slide_right",
        "slap_drop_top",
        "sticker_peel_up",
        "unroll_scroll_down",
        "accordion_fold_left",
        "accordion_fold_right",
        "diagonal_toss_spin",
        "fan_deal_bottom",
    )
    if entry_sig == prev_entry_sig:
        base_idx = (beat_index * 3 + len(text)) % len(all_entry_modes)
        entry_seq = [
            all_entry_modes[base_idx % len(all_entry_modes)],
            all_entry_modes[(base_idx + 2) % len(all_entry_modes)],
            all_entry_modes[(base_idx + 5) % len(all_entry_modes)],
        ]
        entry_sig = " -> ".join(entry_seq)

    return {
        "spatial_layout": chosen["layout_id"],
        "stage_component": chosen["stage_component"],
        "layout_variant": chosen["layout_variant"],
        "board_surface": chosen["board_surface"],
        "layout_summary": chosen["layout_summary"],
        "entry_sequence": entry_seq,
        "entry_reveal": entry_sig,
    }


def _infer_sentence_specific_vox_mechanism(
    narration: str,
    clauses: list[str],
    metrics: list[str],
    arch_id: str,
    beat_id: str,
    beat_index: int,
    visual_description: str = "",
    purpose: str = "",
    prev_vox_spec: dict[str, Any] | None = None,
    framing_motion_intent: str = "",
) -> dict[str, Any]:
    """Derives a 100% independent per-sentence VOX design specification (`MỖI CẢNH LÀ ĐỘC LẬP. MỖI VIDEO LÀ ĐỘC LẬP`):
    - 0% Camera Zoom-In / Zoom-Out (`camera_zoom_policy: "FORBIDDEN_0_PERCENT_ZOOM_IN_OR_ZOOM_OUT"`).
    - No fixed template list, no `beat_index % N` modulo cloning, and no banned `<Broadcast*>` dashboard boxes.
    - Routes to `<GeoJson3DMapStage>` ONLY when the spoken sentence describes a suspect escape/infiltration route
      or a police dispatch/dragnet/stakeout/extradition route (with constant locked zoom `startZoom == endZoom`).
    - For all other VOX beats, derives a bespoke `<Desk>` / `<BlackCard>` / `<ManilaKraftBoard>` paper-collage
      specification with a unique sentence-matched **Spatial Layout (`bố cục`)** and **12fps Cut-and-Paste Entrance
      Sequence (`hiệu ứng cắt dán xuất hiện`)**, plus purposeful `<RedCircle>` ONLY when needed.
    """
    text = str(narration or "").strip()
    c1 = clauses[0] if clauses else text
    c2 = clauses[1] if len(clauses) > 1 else c1
    c3 = clauses[2] if len(clauses) > 2 else (clauses[-1] if clauses else text)
    primary_metric = metrics[0] if metrics else ""
    vis_clean = re.sub(r"\s+", " ", str(visual_description or "")).strip()
    if "clear physical foreground prop focus" in vis_clean or "Noir Chibi 2D Detective Documentary style" in vis_clean:
        vis_clean = ""
    bid_tag = beat_id.replace("-", "_")
    clip_id = f"S_F{beat_index + 1:03d}"

    needs_red_circle = bool(
        re.search(
            r"(지목|포착|발견|단서|흔적|특징|흉터|사마귀|점|지문|번호|숫자|일치|결정적|바로\s*이|주목|확대|정확히)",
            text,
            re.IGNORECASE,
        )
    )
    circle_directive = (
        f"Draw 12fps `<RedCircle>` around the exact target clue in '{c3}' (100px-grid locked, 0px drift)"
        if needs_red_circle
        else "No `<RedCircle>` needed for this sentence (use `<Highlight>` / `<Underline>` / `<TwistedRedYarn>` without unnecessary circles)"
    )

    planned_geo_intent = (
        "GeoJson3DMapStage" in str(framing_motion_intent or "")
        or "parabolic_3d_gis_flyto" in str(purpose or "")
        or "3d_gis" in str(purpose or "").lower()
    )
    if _is_voice_movement_or_pursuit_sentence(text) or (
        planned_geo_intent and not _GEO_NON_MOVEMENT_EXCLUDE_RE.search(text)
    ):
        is_police_route = bool(re.search(r"(압송|호송|추적|포위|출동|잠복|수색망|공안|형사|경찰|검거|급파|파출소|실종\s*지도)", text))
        map_actor = "police_pursuit_or_extradition" if is_police_route else "suspect_escape_or_infiltration"
        grammar = "BESPOKE_3D_SATELLITE_ROUTE_MAP"
        verb = f"GEO_ROUTE_TRACE_{bid_tag}"
        spatial_layout = f"satellite_route_{map_actor}"
        entry_reveal = "constant_altitude_route_trace -> pin_drop_lock -> sat_loupe_cutout_pop"
        stage_component = "GeoJson3DMapStage"
        layout_variant = map_actor
        coord_pairs = re.findall(r"\d{1,3}\.\d+°[NS],\s*\d{1,3}\.\d+°[EW]", str(framing_motion_intent or ""))
        coord_hint = f" [Locked WGS84 anchors: {' -> '.join(coord_pairs)}]" if coord_pairs else ""
        geom = (
            f"[<GeoJson3DMapStage> · {map_actor} · 0% CAMERA ZOOM-IN/ZOOM-OUT (`startZoom === endZoom`)] "
            f"100% voice-matched Esri satellite map (Web Mercator 0.00px lock + authentic road/rail polyline >=12 vertices, 0% synthetic sine curve): "
            f"t1 locks origin pin for '{c1}', t2 traces exact real-world route corridor for '{c2}', "
            f"and t3 pops in destination cutout & 4x `satLoupe` for '{c3}'.{coord_hint}"
        )
        prop_desc = f"High-resolution Esri satellite plate & authentic road/rail GeoJSON route matching '{c1} -> {c3}' for {beat_id}."
        ftg_role = f"Verified geographic route & landmark plate for `{beat_id}` ({map_actor})"
    else:
        desk_plan = _select_diverse_desk_layout_and_entry(text, beat_index=beat_index, prev_vox_spec=prev_vox_spec)
        spatial_layout = desk_plan["spatial_layout"]
        stage_component = desk_plan["stage_component"]
        layout_variant = desk_plan["layout_variant"]
        board_surface = desk_plan["board_surface"]
        layout_summary = desk_plan["layout_summary"]
        entry_seq = desk_plan["entry_sequence"]
        entry_reveal = desk_plan["entry_reveal"]
        e1, e2, e3 = entry_seq[0], entry_seq[1], entry_seq[2]

        grammar = f"BESPOKE_DESK_{spatial_layout.upper()}"
        verb = f"CUT_AND_PASTE_{spatial_layout.upper()}_{bid_tag}"
        context_note = f" ({vis_clean[:100]})" if vis_clean and vis_clean != text else ""
        geom = (
            f"[<Desk> · <{stage_component} {layout_variant}> on {board_surface} · BỐ CỤC `{spatial_layout}` · 0% CAMERA ZOOM-IN/ZOOM-OUT (`z=1.0, transform='none'`)]{context_note}: "
            f"{layout_summary}. "
            f"Cut-and-Paste 12fps Entrance Choreography (`voxDiverseEntry12`): "
            f"t1 enters via `{e1}` placing primary archival cutout (`<VoxVideoPaper>` / `<VoxPhotoPaper>`) for '{c1}'; "
            f"t2 enters via `{e2}` pasting RGBA die-cut prop (`<DieCutSticker>`) & `<Tape>` for '{c2}'; "
            f"t3 enters via `{e3}` + 12fps `<Highlight color='#DACF08'>` / `<Stamp>` on '{c3}'{f' ({primary_metric})' if primary_metric else ''}. "
            f"{circle_directive}."
        )
        prop_desc = (
            f"Bespoke RGBA die-cut evidence prop (`<DieCutSticker>`) & archival photo/clipping arranged in `{spatial_layout}` "
            f"with `{entry_reveal}` 12fps cut-and-paste entrance strictly illustrating '{c1}' and '{c2}' for {beat_id} (0% camera zoom, 0% decorative clutter)."
        )
        ftg_role = f"Authentic case archival media (`footage/{clip_id}.mp4`) mounted inside `<{stage_component} {layout_variant}>` (`{spatial_layout}`) on `<Desk>`"

    return {
        "broadcast_grammar": grammar,
        "dominant_verb": verb,
        "spatial_layout": spatial_layout,
        "stage_component": stage_component,
        "layout_variant": layout_variant,
        "entry_reveal": entry_reveal,
        "camera_zoom_policy": "FORBIDDEN_0_PERCENT_ZOOM_IN_OR_ZOOM_OUT",
        "stage_geometry_description": geom,
        "cutout_prop_description": prop_desc,
        "real_footage_role": ftg_role,
        "needs_red_circle": needs_red_circle,
    }


def build_bespoke_ai_scene_prompt(
    beat: dict[str, Any],
    beat_index: int = 0,
) -> str:
    """Builds a 100% sentence-specific Layer-1 AI visual reconstruction prompt with unique camera rig,
    lens focal length, physical foreground subject, and lighting derived from the exact Korean sentence.
    """
    beat_id = str(beat.get("beat_id") or f"B{beat_index + 1:03d}-V01").strip()
    narration = str(beat.get("narration_text") or beat.get("text") or "").strip()
    vis_desc = re.sub(r"\s+", " ", str(beat.get("visual_description") or "")).strip()
    if "clear physical foreground prop focus" in vis_desc or "Noir Chibi 2D Detective Documentary style" in vis_desc:
        vis_desc = ""
    purpose = re.sub(r"\s+", " ", str(beat.get("purpose") or "")).strip()
    queries = [str(q).strip() for q in (beat.get("footage_search_queries") or []) if str(q).strip()]
    vspec = beat.get("voice_spec") if isinstance(beat.get("voice_spec"), dict) else build_voice_spec_for_beat(beat, beat_index=beat_index)
    clauses = list(vspec.get("clauses") or split_narration_into_clauses(narration, max_clauses=3))
    c1 = clauses[0] if clauses else narration
    c2 = clauses[1] if len(clauses) > 1 else c1
    c3 = clauses[2] if len(clauses) > 2 else (clauses[-1] if clauses else narration)
    rig = _LENS_AND_ANGLE_RIGS[beat_index % len(_LENS_AND_ANGLE_RIGS)]
    q_hint = queries[0] if queries else c1
    detail_clause = (
        vis_desc
        if (vis_desc and vis_desc != narration)
        else f"opening on '{c1}', shifting physical focus to '{c2}', and resolving on '{c3}' (archival anchor: {q_hint}; narrative function: {purpose or 'forensic progression'})"
    )
    return (
        f"[TẦNG 1 · AI VISUAL KEYFRAME · {beat_id}] {rig}, Forensic Noir 35mm archival film grain (zero text/logos/watermarks): "
        f"depicting the exact moment \"{narration}\" — {detail_clause}, with tactile foreground lighting on '{c1}'."
    )


def build_bespoke_vox_design_prompt(
    beat: dict[str, Any],
    beat_index: int = 0,
    total_beats: int = 192,
    prev_vox_spec: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any], str]:
    """Builds Layer 2 (`vox_design_prompt` + `vox_blueprint_spec`) and Layer 1's `ai_cutout_prop_prompt`
    for a single voice beat with:
    - 0% Camera Zoom-In / Zoom-Out (`camera_zoom_policy: "FORBIDDEN_0_PERCENT_ZOOM_IN_OR_ZOOM_OUT"`).
    - Sentence-specific Spatial Layout (`spatial_layout` / `bố cục`) and 12fps Cut-and-Paste Entrance Effect (`entry_reveal` / `hiệu ứng cắt dán xuất hiện`).
    """
    beat_id = str(beat.get("beat_id") or f"B{beat_index + 1:03d}-V01").strip()
    narration = str(beat.get("narration_text") or beat.get("text") or "").strip()
    vspec = beat.get("voice_spec") if isinstance(beat.get("voice_spec"), dict) else build_voice_spec_for_beat(beat, beat_index=beat_index)
    clauses = list(vspec.get("clauses") or split_narration_into_clauses(narration, max_clauses=3))
    windows = list(vspec.get("clause_windows") or [(0.0, 0.34), (0.34, 0.68), (0.68, 1.0)])
    metrics = list(vspec.get("metrics") or [])
    focus_tags = list(vspec.get("clause_focus_tags") or [])
    arch_id = str(beat.get("scene_archetype") or "#D1").strip()
    editorial_layer = str(beat.get("editorial_layer") or "").strip()
    dna_slot = str(beat.get("dna_visual_slot") or "").strip()
    is_vox_beat = editorial_layer == "VOX_NEWSROOM" or dna_slot == "vox_motion" or (arch_id != "cinema_full" and arch_id != "")

    c1 = clauses[0] if clauses else narration
    c2 = clauses[1] if len(clauses) > 1 else c1
    c3 = clauses[2] if len(clauses) > 2 else (clauses[-1] if clauses else narration)
    w0 = windows[0] if windows else (0.0, 0.33)
    w1 = windows[1] if len(windows) > 1 else (0.33, 0.67)
    w2 = windows[2] if len(windows) > 2 else (0.67, 1.0)

    mech = _infer_sentence_specific_vox_mechanism(
        narration=narration,
        clauses=clauses,
        metrics=metrics,
        arch_id=arch_id,
        beat_id=beat_id,
        beat_index=beat_index,
        visual_description=str(beat.get("visual_description") or ""),
        purpose=str(beat.get("purpose") or ""),
        prev_vox_spec=prev_vox_spec,
        framing_motion_intent=str(beat.get("framing_motion_intent") or ""),
    )

    clip_id = f"S_F{beat_index + 1:03d}"
    footage_path = str(beat.get("footage_path") or f"footage/{clip_id}.mp4").strip()
    queries = list(beat.get("footage_search_queries") or [narration[:60]])
    existing_spec = beat.get("vox_blueprint_spec") if isinstance(beat.get("vox_blueprint_spec"), dict) else {}
    raw_labels = list(existing_spec.get("micro_labels_ko") or []) or (metrics[:2] + focus_tags[:2])
    micro_labels: list[str] = []
    for lbl in raw_labels:
        clean_lbl = re.sub(r"\s+", " ", str(lbl or "")).strip()
        if clean_lbl and clean_lbl not in micro_labels:
            micro_labels.append(clean_lbl)
        if len(micro_labels) >= 3:
            break
    if len(micro_labels) < 2:
        for fallback_clause in (c1, c2, c3):
            words_fb = [w for w in re.split(r"\s+", fallback_clause.strip()) if w]
            cand_fb = " ".join(words_fb[:3])[:18].strip()
            if cand_fb and cand_fb not in micro_labels:
                micro_labels.append(cand_fb)
            if len(micro_labels) >= 2:
                break
    if not micro_labels:
        micro_labels = [c1[:14]]

    vox_scene_signature = f"VOX_BROADCAST_{beat_id.replace('-', '_')}_{mech['dominant_verb']}"
    ai_cutout_prop_prompt = (
        f"[AUTHENTIC ARCHIVAL PLATE CROP · {beat_id} · max_uses=1] {mech['cutout_prop_description']} "
        f"Extracted directly from verified archival video `{footage_path}` (0% synthetic PIL drawing, 0% AI cartoon stickers)."
    )

    vox_design_prompt = (
        f"[VOX CUT-AND-PASTE COLLAGE PROMPT · {beat_id} ({beat_index + 1}/{total_beats}) · layout={mech['spatial_layout']} · entry={mech['entry_reveal']} · zoom=0%_FORBIDDEN · sig={vox_scene_signature}] "
        f"1. EXACT WORD-TIMESTAMP CHOREOGRAPHY (`voice_manifest.json` frame lock): \"{narration}\" -> "
        f"t1 ({w0[0]:.2f}-{w0[1]:.2f}): \"{c1}\" | "
        f"t2 ({w1[0]:.2f}-{w1[1]:.2f}): \"{c2}\" ({mech['dominant_verb']}) | "
        f"t3 ({w2[0]:.2f}-{w2[1]:.2f}): \"{c3}\". "
        f"2. ZERO ZOOM-IN / ZOOM-OUT (`camera_zoom_policy={mech['camera_zoom_policy']}`): Camera is 100% locked overhead (`z=1.0, transform='none'`); NEVER zoom in or zoom out on VOX! "
        f"3. SENTENCE-SPECIFIC SPATIAL LAYOUT (`{mech['spatial_layout']}`) & 12FPS CUT-AND-PASTE ENTRANCE (`{mech['entry_reveal']}`): {mech['stage_geometry_description']} "
        f"4. MANDATORY REAL ARCHIVAL MEDIA: {mech['real_footage_role']} (`{footage_path}`, queries={queries[:2]}, max_uses=1). "
        f"5. ZERO-TRUNCATION LABELS (KR): {' | '.join(micro_labels)} (0% text ellipsis, 0px bounding-box overlap, y <= 785px)."
    )

    vox_blueprint_spec: dict[str, Any] = {
        **existing_spec,
        "beat_id": beat_id,
        "beat_index": beat_index,
        "is_active_vox_scene": is_vox_beat,
        "vox_scene_signature": vox_scene_signature,
        "broadcast_grammar": mech["broadcast_grammar"],
        "spatial_layout": mech["spatial_layout"],
        "stage_component": mech["stage_component"],
        "layout_variant": mech["layout_variant"],
        "entry_reveal": mech["entry_reveal"],
        "camera_zoom_policy": mech["camera_zoom_policy"],
        "evidence_media_mode": "real_footage_broadcast_motion",
        "real_footage_binding": {
            **(existing_spec.get("real_footage_binding") if isinstance(existing_spec.get("real_footage_binding"), dict) else {}),
            "clip_id": clip_id,
            "footage_path": footage_path,
            "role_in_vox": mech["real_footage_role"],
            "footage_search_queries": queries,
            "require_authentic_case_media": True,
            "forbid_synthetic_pil_drawing": True,
            "forbid_blind_svg_scribble": True,
            "max_uses": 1,
        },
        "dominant_physical_verb": mech["dominant_verb"],
        "stage_geometry_description": mech["stage_geometry_description"],
        "cutout_prop_description": mech["cutout_prop_description"],
        "ai_cutout_prop_prompt": ai_cutout_prop_prompt,
        "clauses_t1_t2_t3": [
            {"phase": "t1", "window": list(w0), "clause_ko": c1, "role": "input_evidence_state"},
            {"phase": "t2", "window": list(w1), "clause_ko": c2, "role": "dominant_physical_verb"},
            {"phase": "t3", "window": list(w2), "clause_ko": c3, "role": "visible_consequence_reticle_lock"},
        ],
        "micro_labels_ko": micro_labels,
        "max_korean_words_cap": 15,
        "min_geometry_screen_share": 0.80,
    }
    return vox_design_prompt, vox_blueprint_spec, ai_cutout_prop_prompt


def attach_two_layer_visual_prompts(
    beat: dict[str, Any],
    beat_index: int = 0,
    total_beats: int = 192,
    prev_vox_spec: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Attaches explicit Two-Layer Visual Prompts (`ai_visual_layer` + `vox_design_layer`)
    to a beat dictionary in-place and returns it.
    """
    vox_design_prompt, vox_blueprint_spec, ai_cutout_prop_prompt = build_bespoke_vox_design_prompt(
        beat,
        beat_index=beat_index,
        total_beats=total_beats,
        prev_vox_spec=prev_vox_spec,
    )
    raw_ai = str(beat.get("ai_prompt") or beat.get("prompt") or "").strip()
    if (
        not raw_ai
        or "clear physical foreground prop focus on the exact action/evidence described in the sentence" in raw_ai
        or raw_ai.startswith("[TẦNG 2 · VOX DESIGN PROMPT")
    ):
        ai_prompt = build_bespoke_ai_scene_prompt(beat, beat_index=beat_index)
    else:
        ai_prompt = raw_ai
    beat["ai_prompt"] = ai_prompt
    beat["ai_cutout_prop_prompt"] = ai_cutout_prop_prompt
    beat["vox_design_prompt"] = vox_design_prompt
    beat["vox_blueprint_spec"] = vox_blueprint_spec
    beat["visual_layers"] = {
        "layer_1_ai_visual": {
            "role": "closed_room_ai_reconstruction_and_cutout_prop",
            "ai_prompt": ai_prompt,
            "ai_cutout_prop_prompt": ai_cutout_prop_prompt,
            "max_uses": 1,
        },
        "layer_2_vox_design": {
            "role": "sentence_specific_vox_stage_and_real_footage_mechanism",
            "vox_design_prompt": vox_design_prompt,
            "vox_blueprint_spec": vox_blueprint_spec,
        },
    }
    return beat

