"""
Bilingual Case, Entity, and Semantic Similarity Engine for CofiDocumentary.
Detects duplicate documentary topics and true crime cases across Korean, Vietnamese, and English.
"""

from __future__ import annotations

import re
from typing import Any


def _normalize_text(text: str) -> str:
    if not text:
        return ""
    for pat in (r'\[중국\s*실화\s*사건\]', r'\[중국\s*사기\s*실화\]', r'\[중국\s*인프라의\s*이면\]', r'\[중국\]', r'\[하나님의\s*말씀\]', r'\[vụ\s*án\s*có\s*thật\s*ở\s*trung\s*quốc\]', r'\[vụ\s*lừa\s*đảo\s*có\s*thật\s*ở\s*trung\s*quốc\]', r'\[mặt\s*tối\s*hạ\s*tầng\s*trung\s*quốc\]', r'\[lời\s*chúa\s*mỗi\s*ngày\]', r'\[declassified\s*us\s*intelligence\s*files\]', r'\[presidential\s*records\s*&\s*executive\s*forensics\]'):
        text = re.sub(pat, ' ', text, flags=re.IGNORECASE)
    cleaned = text.lower()
    # Normalize punctuation and brackets
    cleaned = re.sub(r"[\(\)\[\]\{\}\<\>\"\'`«»\—\–\-·|:/\\,.?!;~@#$%^&*+=_\n\r\t]+", " ", cleaned)
    return " ".join(cleaned.split())


# Known high-specificity case anchor clusters
CASE_CLUSTERS: list[dict[str, Any]] = [
    {
        "key": "case_baiyin_serial_killer",
        "name": "Đại án Bạch Ngân Cao Thừa Dũng (Baiyin 28-year School Store Case)",
        "markers": [
            "bạch ngân", "baiyin", "바이인", "바이인시",
            "cao thừa dũng", "gao chengyong", "고승용",
            "y-염색체", "y-str", "nhiễm sắc thể y",
        ],
        "scenario_a": ["28년간", "28년", "28 năm", "28-year"],
        "scenario_b": ["학교 매점", "매점", "tiệm tạp hóa", "tạp hóa trường học", "grocery store", "school store"],
    },
    {
        "key": "case_lao_rongzhi",
        "name": "Đại án Lao Vinh Chi / Lao Rongzhi (20-year fugitive disguise)",
        "markers": [
            "lao rongzhi", "lao vinh chi", "라오룽즈", "劳荣枝",
            "fa ziying", "파즈잉", "法子英", "sherry", "hong moujiao", "홍모자오",
        ],
        "scenario_a": ["20년간", "20년", "20 năm", "20-year"],
        "scenario_b": [
            "신분을 세탁", "tẩy trắng thân phận", "thay tên đổi họ", "vỏ bọc",
            "백화점", "tiệm đồng hồ", "시계 매장", "watch counter", "안면인식",
        ],
    },
    {
        "key": "case_south_to_north_water_diversion",
        "name": "Đại công trình Nam Thủy Bắc Điều 1,432km & Đất trương nở / Đập Đan Giang Khẩu",
        "markers": [
            "nam thủy bắc điều", "south-to-north", "남수북조",
            "đan giang khẩu", "danjiangkou", "단장커우",
        ],
        "scenario_a": ["1,432km", "1432km", "1,432 km", "1432 km", "1,432킬로미터", "1432킬로미터"],
        "scenario_b": [
            "đất trương nở", "팽창토", "expansive soil", "지반 침하",
            "sụt lún", "5,000억 위안", "5000억 위안", "500 tỷ",
        ],
    },
    {
        "key": "case_zhou_kehua",
        "name": "Đại án Chu Khắc Hoa (8 năm vượt 10 tỉnh vây ráp hang núi)",
        "markers": ["chu khắc hoa", "zhou kehua", "주커화", "주극화", "폭두남"],
        "scenario_a": ["8년간", "8년", "8 năm"],
        "scenario_b": ["동굴", "hang núi", "10개 성", "10 tỉnh", "걸음걸이", "dáng đi", "충칭", "가화산"],
    },
    {
        "key": "case_liu_yongbiao",
        "name": "Kỳ án Lưu Vĩnh Bưu / Nhà trọ Hồ Châu (22 năm ẩn mình thành nhà văn)",
        "markers": ["lưu vĩnh bưu", "liu yongbiao", "유영표", "호주 여관", "호주 여관 사건", "hồ châu"],
        "scenario_a": ["22년간", "22년", "22 năm"],
        "scenario_b": ["작가", "nhà văn", "소설", "tiểu thuyết", "best seller", "베스트셀러", "여관"],
    },
    {
        "key": "case_ji_siguang",
        "name": "Kỳ án Cát Quang / Ji Siguang (13 năm trốn truy nã thành diễn viên phim truyền hình)",
        "markers": ["cát quang", "cát tứ quang", "ji siguang", "길광", "길사광", "지쓰광", "길광 도주"],
        "scenario_a": ["13년간", "13년", "13 năm"],
        "scenario_b": ["드라마 배우", "인기 드라마", "잠복", "diễn viên", "phim truyền hình", "엑스트라"],
    },
    {
        "key": "case_xiao_qiqiang",
        "name": "Kỳ án Tiêu Kỳ Cường / Xiao Qiqiang (17 năm giả câm điếc ăn xin trốn truy nã)",
        "markers": ["tiêu kỳ cường", "xiao qiqiang", "소기강", "샤오치창", "소기강 신분세탁"],
        "scenario_a": ["17년간", "17년", "17 năm"],
        "scenario_b": ["벙어리", "거지", "말을 잃어버린", "giả câm", "ăn xin", "mất tiếng"],
    },
    {
        "key": "case_xiang_nanfang",
        "name": "Vụ án Hướng Nam Phương / Xiang Nanfang (12 năm tẩy trắng thân phận thành triệu phú Vương Bân)",
        "markers": ["hướng nam phương", "xiang nanfang", "행남방", "샹난팡", "행남방 도주", "왕 빈", "왕빈"],
        "scenario_a": ["12년간", "12년", "12 năm"],
        "scenario_b": ["수백만 위안 자산가", "자산가로 변신", "triệu phú", "자선가", "72시간"],
    },
    {
        "key": "case_ma_jiajue",
        "name": "Kỳ án Mã Gia Tước / Ma Jiajue (Ký túc xá ĐH Vân Nam 2004)",
        "markers": ["mã gia tước", "ma jiajue", "마가작", "마지아주에", "운남대 기숙사"],
        "scenario_a": ["2004년", "2004", "4명", "bốn bạn"],
        "scenario_b": ["기숙사", "벽장", "트럼프", "ký túc xá", "đánh bài"],
    },
    {
        "key": "case_three_gorges_silt",
        "name": "Đập Tam Hiệp 1,9 tỷ tấn bùn cát & Xói ngầm hạ lưu",
        "markers": ["tam hiệp", "three gorges", "삼협댐", "싼샤댐"],
        "scenario_a": ["19억 톤", "1.9 tỷ tấn", "1900000000"],
        "scenario_b": ["청수세굴", "퇴적물", "xói ngầm", "bùn cát", "bồi lắng"],
    },
    {
        "key": "case_baihetan_dam",
        "name": "Siêu đập Bạch Hạc Than / Baihetan 289m không vết nứt",
        "markers": ["bạch hạc than", "baihetan", "바이허탄", "백학탄"],
        "scenario_a": ["289m", "289미터", "2,200억 위안"],
        "scenario_b": ["균열 0", "저열 시멘트", "아치댐", "không vết nứt"],
    },
    {
        "key": "case_hangzhou_bay_bridge",
        "name": "Cầu vượt biển Vịnh Hàng Châu 36km",
        "markers": ["vịnh hàng châu", "hangzhou bay", "항저우만"],
        "scenario_a": ["36km", "36킬로미터"],
        "scenario_b": ["해상대교", "메탄가스", "조수간만"],
    },
    {
        "key": "case_sichuan_tibet_railway",
        "name": "Đường sắt Tứ Xuyên - Tây Tạng 3,200 tỷ tệ",
        "markers": ["tứ xuyên tây tạng", "sichuan tibet", "쓰촨-티베트", "천장철도"],
        "scenario_a": ["3조 2천억", "3,000m", "3000m"],
        "scenario_b": ["고원 철도", "단층대", "터널"],
    },
    {
        "key": "case_qian_zhimin_60k_btc",
        "name": "Đại án Tiền Chí Mẫn / Lam Thiên Cách Nhuệ (61.000 Bitcoin / 8.000 tỷ Won trong USB)",
        "markers": ["tiền chí mẫn", "qian zhimin", "첸즈민", "람천격예", "lam thiên cách nhuệ", "6만 비트코인", "61,000 btc", "61000 btc"],
        "scenario_a": ["8조 원", "12만 명", "6만 개"],
        "scenario_b": ["usb", "런던", "영국 경찰", "비트코인 세탁"],
    },
    {
        "key": "case_plustoken_30t",
        "name": "Đại án PlusToken 30.000 tỷ Won (Sorry, we have run / Vanuatu)",
        "markers": ["plustoken", "plus token", "플러스토큰", "딩잔칭", "천보", "바누아투", "vanuatu"],
        "scenario_a": ["30조 원", "200만 명", "194,775"],
        "scenario_b": ["도망쳤다", "we have run", "유령 지갑", "28,000"],
    },
]


def extract_case_anchors_and_entities(
    title: str, topic: str = "", notes: str = ""
) -> tuple[list[str], list[str]]:
    """
    Extract core entities and subject keywords from title, topic, and notes.
    """
    combined = f"{title} {topic} {notes}".strip()
    norm = _normalize_text(combined)

    entities: list[str] = []
    keywords: list[str] = []

    # 1. Match known case clusters
    for cluster in CASE_CLUSTERS:
        has_marker = any(m in norm for m in cluster["markers"])
        has_scen_a = any(sa in norm for sa in cluster["scenario_a"])
        has_scen_b = any(sb in norm for sb in cluster["scenario_b"])
        if has_marker or (has_scen_a and has_scen_b):
            for m in cluster["markers"][:3]:
                if m not in entities:
                    entities.append(m)
            for s in cluster["scenario_a"][:2] + cluster["scenario_b"][:3]:
                if s not in keywords:
                    keywords.append(s)

    # 2. Extract numbered timeframes and measurements
    metric_matches = re.findall(
        r"(\d+[\.,]?\d*\s*(?:년간|년|năm|km|킬로미터|억 위안|tỷ|tấn|m³|phút|giây|미터))",
        combined,
        re.IGNORECASE,
    )
    for mm in metric_matches:
        mm_clean = mm.strip()
        if mm_clean and mm_clean not in keywords:
            keywords.append(mm_clean)

    # 3. Extract proper capitalized names and Hangul word blocks (excluding generic niche stopwords)
    generic_stopwords = {
        "중국", "중국의", "실화", "사건", "실화사건", "미제사건", "미제사건의", "수배범", "수배범이",
        "수배범의", "용의자", "진범", "진범이", "범인이", "형사들", "형사들의", "수사관", "공안",
        "동안", "전말", "이유", "사연", "진실", "진실을", "사라진", "숨겨진", "남겨진", "밝혀진",
        "트루크라임", "특급수배록", "역사상", "최대", "최악의", "살아온", "행세한", "위장해",
        "변신한", "숨어", "지낸", "사건의", "범인의", "남자의", "여인의", "마을에서", "중대",
        "trung quốc", "vụ án", "vụ án có thật", "kỳ án", "đại án", "chuyên án", "hồ sơ",
        "tội phạm", "truy nã", "cảnh sát", "hình sự", "pháp y", "sự thật", "bí ẩn", "toàn cảnh",
        "nghi phạm", "hung thủ", "nhà văn", "triệu phú", "tử tù", "xanh tiền", "màn kịch",
        "lừa đảo", "ừa đảo", "công nghệ cao", "tài chính", "tiền ảo", "dòng tiền", "truy vết",
        "하나에", "증발한", "남기고", "도망쳤다", "지갑의", "다단계", "사기", "금융", "첨단", "실체", "추적",
    }
    hangul_entities = re.findall(r"([가-힣]{3,}(?:시|성|사건|공정|수배범)?)", combined)
    for he in hangul_entities:
        if he.lower() not in generic_stopwords and he not in entities and len(he) >= 3 and len(entities) < 8:
            entities.append(he)

    vn_caps = re.findall(r"([A-ZÀ-Ỹ][a-zà-ỹ]+(?:\s+[A-ZÀ-Ỹ][a-zà-ỹ]+){1,3})", combined)
    for vc in vn_caps:
        if vc.lower() not in generic_stopwords and vc not in entities and len(entities) < 8:
            entities.append(vc)

    return entities[:8], keywords[:10]


def check_case_similarity(
    candidate_text: str,
    target_title: str,
    target_topic: str = "",
    target_entities: list[str] | None = None,
    target_keywords: list[str] | None = None,
) -> tuple[bool, str, float]:
    """
    Determine if candidate_text refers to the same underlying documentary case / topic
    as target_title / target_topic / entities.
    Returns: (is_duplicate: bool, reason: str, confidence: float)
    """
    cand_norm = _normalize_text(candidate_text)
    t_title_norm = _normalize_text(target_title)
    t_topic_norm = _normalize_text(target_topic)
    target_combined = f"{t_title_norm} {t_topic_norm}".strip()

    if not cand_norm or not target_combined:
        return False, "", 0.0

    # 1. Exact or near-exact string match
    if cand_norm == t_title_norm or (len(cand_norm) >= 12 and (cand_norm in t_title_norm or t_title_norm in cand_norm)):
        return True, "Trùng khớp nguyên văn tiêu đề đề tài", 1.0

    # 2. Cluster anchor match (bilingual case resolution)
    for cluster in CASE_CLUSTERS:
        cand_has_marker = any(m in cand_norm for m in cluster["markers"])
        cand_has_scen_a = any(sa in cand_norm for sa in cluster["scenario_a"])
        cand_has_scen_b = any(sb in cand_norm for sb in cluster["scenario_b"])
        cand_matches_cluster = cand_has_marker or (cand_has_scen_a and cand_has_scen_b)

        target_has_marker = any(m in target_combined for m in cluster["markers"])
        target_has_scen_a = any(sa in target_combined for sa in cluster["scenario_a"])
        target_has_scen_b = any(sb in target_combined for sb in cluster["scenario_b"])
        target_matches_cluster = target_has_marker or (target_has_scen_a and target_has_scen_b)

        if cand_matches_cluster and target_matches_cluster:
            # If both match the same specific real-world case anchor
            matched_anchors = [m for m in cluster["markers"] if m in cand_norm or m in target_combined]
            scen_anchors = [s for s in cluster["scenario_a"] + cluster["scenario_b"] if s in cand_norm or s in target_combined]
            desc = ", ".join((matched_anchors + scen_anchors)[:4])
            return True, f"Trùng khớp hồ sơ vụ việc '{cluster['name']}' (Mỏ neo: {desc})", 0.95

    # 3. Target entities overlap
    generic_stopwords = {
        "중국", "중국의", "실화", "사건", "실화사건", "미제사건", "미제사건의", "수배범", "수배범이",
        "수배범의", "용의자", "진범", "진범이", "범인이", "형사들", "형사들의", "수사관", "공안",
        "동안", "전말", "이유", "사연", "진실", "진실을", "사라진", "숨겨진", "남겨진", "밝혀진",
        "트루크라임", "특급수배록", "역사상", "최대", "최악의", "살아온", "행세한", "위장해",
        "변신한", "숨어", "지낸", "사건의", "범인의", "남자의", "여인의", "마을에서", "중대",
        "trung quốc", "vụ án", "vụ án có thật", "kỳ án", "đại án", "chuyên án", "hồ sơ",
        "tội phạm", "truy nã", "cảnh sát", "hình sự", "pháp y", "sự thật", "bí ẩn", "toàn cảnh",
        "nghi phạm", "hung thủ", "nhà văn", "triệu phú", "tử tù", "xanh tiền", "màn kịch",
        "lừa đảo", "ừa đảo", "công nghệ cao", "tài chính", "tiền ảo", "dòng tiền", "truy vết",
        "하나에", "증발한", "남기고", "도망쳤다", "지갑의", "다단계", "사기", "금융", "첨단", "실체", "추적",
    }
    t_entities = [
        e.lower() for e in (target_entities or [])
        if e and len(e) >= 2 and e.lower().strip() not in generic_stopwords
    ]
    t_keywords = [
        k.lower() for k in (target_keywords or [])
        if k and len(k) >= 2 and k.lower().strip() not in generic_stopwords
    ]

    extra_generic = {
        "vụ lừa đảo có", "vụ án có", "thật ở trung quốc", "mặt tối hạ tầng", "lời chúa mỗi ngày",
        "평생", "모은", "퇴직금을", "퇴직금", "넣자", "벌어진", "노후", "자금", "이자에", "땅속",
        "묻힌", "비밀", "장부", "범인은", "바로", "동네", "모범", "시민이었다", "우등생은",
        "도주했나", "프로파일링", "무너지게", "한마디", "수사", "기록의", "알리바이를", "설계한",
    }
    t_entities = [
        e for e in t_entities
        if e not in extra_generic
        and not re.fullmatch(r"\d+[\.,]?\d*\s*(?:년간|년|năm|km|킬로미터|억|조|만|미터|일|개월|시간|%|자루의|그램의)?", e)
        and "vụ án" not in e and "vụ lừa đảo" not in e and "trung quốc" not in e
    ]
    t_keywords = [
        k for k in t_keywords
        if k not in extra_generic
        and not re.fullmatch(r"\d+[\.,]?\d*\s*(?:년간|년|năm|km|킬로미터|억|조|만|미터|일|개월|시간|%|자루의|그램의)?", k)
        and "vụ án" not in k and "vụ lừa đảo" not in k and "trung quốc" not in k
    ]
    matched_entities = [e for e in t_entities if len(e) >= 3 and e in cand_norm]
    matched_keywords = [k for k in t_keywords if len(k) >= 3 and k in cand_norm and k not in matched_entities]

    if len(matched_entities) >= 2 and len(matched_keywords) >= 1:
        return (
            True,
            f"Trùng khớp thực thể cốt lõi ({len(matched_entities)} entities) & từ khóa vụ án ({len(matched_keywords)} keywords)",
            0.90,
        )
    if len(matched_entities) >= 3:
        return True, f"Trùng khớp 3 thực thể định danh chính của đề tài", 0.88

    # 4. Token bi-gram / n-gram Jaccard overlap
    words_cand = [w for w in cand_norm.split() if len(w) >= 2]
    words_target = [w for w in target_combined.split() if len(w) >= 2]
    if words_cand and words_target:
        set_cand = set(words_cand)
        set_target = set(words_target)
        intersection = set_cand.intersection(set_target)
        union = set_cand.union(set_target)
        jaccard = len(intersection) / len(union) if union else 0.0

        # High overlap threshold
        if jaccard >= 0.38 and len(intersection) >= 4:
            matched_terms = list(intersection)[:5]
            return True, f"Trùng lặp cấu trúc từ khóa chuyên biệt: {', '.join(matched_terms)}", jaccard

    return False, "", 0.0


def is_duplicate_case(text_a: str, text_b: str) -> bool:
    """Helper shortcut returning boolean."""
    is_dup, _, _ = check_case_similarity(text_a, text_b)
    return is_dup
