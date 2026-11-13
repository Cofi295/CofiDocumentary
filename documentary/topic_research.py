"""
Live Two-Stream Topic Research Engine for CofiDocumentary.

Replaces static pool rotation with genuine live investigative case discovery:
  1. Multi-query Chinese archival web & video search (DDGS) rotating across rounds.
  2. Strict two-stream DNA taxonomy for True Crime Documentary channels:
       - Stream 1 (`financial_crime`): Tội phạm Tài chính & Đại án Kinh tế Đào tẩu
       - Stream 2 (`major_violent_crime`): Vụ án Đặc biệt Nguy hiểm & Truy nã Cấp A
  3. Trilingual anti-repeat filtering against BOTH:
       - Permanent produced memory (`topic_memory`, `own_channel`, `jobs`)
       - Rolling `suggested_topic_history` + UI `exclude_titles` so topics never loop.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any, Callable
from uuid import uuid4

from services.case_similarity import (
    check_case_similarity,
    check_cross_case_mo_collision,
    classify_true_crime_topic_stream,
    extract_case_anchors_and_entities,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


TRUE_CRIME_TOPIC_STREAMS: dict[str, dict[str, Any]] = {
    "financial_crime": {
        "id": "financial_crime",
        "code": "STREAM_01_FINANCIAL_CRIME",
        "badge_vi": "💰 Luồng 1 · Tài chính · Kho bạc · Mở két & Cướp tiền",
        "short_label_vi": "Tài chính · Kho bạc · Mở két & Cướp tiền",
        "label_vi": "Luồng 1: Đại án Tài chính, Đột nhập Kho bạc / Mở két, Cướp tiền & Đào tẩu",
        "label_ko": "대형 금융·금고 털이·현금수송차 탈취 및 해외 도피 수배범 추적",
        "description_vi": (
            "Đại án chứng khoán, ngân hàng, công trái, đột nhập kho bạc, cắt/mở két sắt tinh vi, "
            "cướp ngân hàng/xe chở tiền/tiệm vàng/bảo tàng quốc bảo, hối phiếu khống, biển thủ siêu ngạch "
            "có thật tại Trung Quốc; kẻ chủ mưu IQ cao lợi dụng lỗ hổng an ninh/tài chính rồi tẩy trắng "
            "thân phận / đào tẩu 10–25 năm & cuộc truy vết dòng tiền + vật chứng vi lượng (CCTV 今日说法 / 天网 / 经侦大案 / 猎狐行动)."
        ),
        "recommended_vox_verbs": [
            "CRASH_TIMELINE",
            "SCALE_MULTIPLICATION",
            "SPLIT_PARADOX",
            "LEDGER_DIFF_SCRUB",
            "GEO_VECTOR_PURSUIT",
            "CAUSAL_CHAIN",
            "ROLLING_METRIC_SHOCK",
            "CONCENTRIC_TRAP",
        ],
    },
    "major_violent_crime": {
        "id": "major_violent_crime",
        "code": "STREAM_02_MAJOR_VIOLENT_CRIME",
        "badge_vi": "🚨 Luồng 2 · Trọng án Hình sự & Truy nã Cấp A",
        "short_label_vi": "Trọng án Hình sự · Án lạnh Pháp y & Truy nã Cấp A",
        "label_vi": "Luồng 2: Trọng án Đặc biệt Nguy hiểm, Án lạnh Pháp y & Truy nã Cấp A",
        "label_ko": "특급 미제사건 · 실종 미스터리 · 법의학 미세물증 및 1급 수배범 추적",
        "description_vi": (
            "Trọng án hình sự đặc biệt nguy hiểm có thật tại Trung Quốc (Truy nã cấp A Bộ Công an, 0% án tài chính/mở két/cướp tiền), "
            "mất tích bí ẩn, án lạnh 10–30 năm giải mã bằng pháp y ADN/Y-STR/vi lượng, hung thủ IQ cao xóa dấu vết / phản trinh sát, "
            "vỏ bọc hai mặt ẩn mình dưới đời thường & đấu trí tâm lý phòng thẩm vấn "
            "(100% Cách viết Xanh tiền Đài truyền hình — Vùng 60s đầu sạch tuyệt đối & Khúc xạ pháp y gián tiếp)."
        ),
        "recommended_vox_verbs": [
            "FORENSIC_ZOOM_CHAIN",
            "DUAL_ERA_LOCK",
            "ALIBI_SHATTER",
            "BLIND_SPOT_REVEAL",
            "NETWORK_GRAPH",
            "SINGLE_EVIDENCE_AUTOPSY",
            "RADIAL_TIME_PRESSURE",
            "MICRO_TRACE_MATCH",
        ],
    },
}


FINANCIAL_CRIME_QUERY_BANK: list[str] = [
    "中国 银行 行长 挪用公款 潜逃 真实案件 今日说法",
    "农业银行 中国银行 金库 被盗 切割金库 潜逃 真实大案 天网",
    "猎狐行动 金融大案 潜逃 海外 押解回国 纪实",
    "证券 国债 期货 挪用 潜逃 真实案件 侦破",
    "银行运钞车 储蓄所 珠宝行 特大劫案 告破 纪实",
    "技术开启 保险柜 金库 大盗 侦破纪实 今日说法",
    "金融票据 诈骗 亿 潜逃 整容 洗白身份 真实案件",
    "非法集资 百亿 潜逃 悬赏 经侦 侦破纪实",
    "国有银行 支行 账外账 卷款潜逃 真实大案",
    "博物馆 一级文物 黄金 被盗 侦破纪实 天网",
]

MAJOR_VIOLENT_CRIME_QUERY_BANK: list[str] = [
    "公安部 A级通缉令 潜逃 落网 真实案件 天网 今日说法",
    "命案积案 潜逃20年 洗白身份 告破 真实案件 纪实",
    "一线 天网 特大悬案 指纹 DNA 破获 真实大案",
    "隐姓埋名 潜逃 十几年 逃犯 落网 警方通报 纪实",
    "离奇失踪 悬案 微量物证 侦破 真实案件 今日说法",
    "Y染色体 家系 侦破 20年 悬案 真实案件 今日说法",
    "双面人生 逃犯 变身 老板 住持 落网 真实案件",
    "密室 伪造不在场证明 悬案 法医 侦破 真实案件",
    "公安部 督办 积案 追凶 侦破纪实",
    "潜逃 25年 30年 逃犯 步态识别 人脸比对 落网 天网",
]


NOISE_LEAD_PATTERNS: tuple[str, ...] = (
    "wikipedia.org/wiki/closed-circuit",
    "cctv headquarters",
    "china central television - wikipedia",
    "youtube homepage",
    "login",
    "sign in",
)


def normalize_requested_stream(topic_stream: str | None) -> str:
    val = str(topic_stream or "all").strip().lower()
    if val in {"financial_crime", "finance", "finance_crime", "economic_crime", "stream_1", "1"}:
        return "financial_crime"
    if val in {"major_violent_crime", "dangerous_crime", "violent_crime", "class_a", "stream_2", "2"}:
        return "major_violent_crime"
    return "all"


def enrich_candidate_stream_metadata(item: dict[str, Any]) -> dict[str, Any]:
    out = dict(item)
    stream_id = classify_true_crime_topic_stream(out)
    meta = TRUE_CRIME_TOPIC_STREAMS.get(stream_id, TRUE_CRIME_TOPIC_STREAMS["major_violent_crime"])
    out["topic_stream"] = stream_id
    out["stream_badge_vi"] = meta["badge_vi"]
    out["stream_label_vi"] = meta["short_label_vi"]
    out["stream_full_label_vi"] = meta["label_vi"]
    if not out.get("recommended_vox_verbs"):
        out["recommended_vox_verbs"] = list(meta["recommended_vox_verbs"][:3])
    return out


def _is_duplicate_against_records(
    candidate_text: str,
    records: list[dict[str, Any]],
    *,
    enforce_mo_cooldown: bool = True,
) -> tuple[bool, str]:
    if not candidate_text.strip():
        return False, ""
    for rec in records:
        r_title = str(rec.get("title") or "")
        r_topic = " ".join(
            filter(
                None,
                [
                    str(rec.get("topic") or ""),
                    str(rec.get("case_real_name_zh") or ""),
                    str(rec.get("note") or ""),
                ],
            )
        ).strip()
        r_tags = list(rec.get("tags") or [])
        r_anchors = list(rec.get("anchors") or [])
        is_dup, reason, _ = check_case_similarity(
            candidate_text,
            r_title or r_topic,
            target_topic=r_topic,
            target_entities=r_tags,
            target_keywords=r_anchors,
        )
        if is_dup:
            return True, reason

    if enforce_mo_cooldown and records:
        is_mo_coll, mo_reason, _ = check_cross_case_mo_collision(
            candidate_text,
            records,
            cooldown_window=10,
        )
        if is_mo_coll:
            return True, mo_reason

    return False, ""


def harvest_live_case_leads(
    *,
    topic_stream: str = "all",
    research_round: int = 0,
    exclusion_records: list[dict[str, Any]] | None = None,
    ddgs_factory: Callable[[], Any] | None = None,
    max_leads: int = 24,
) -> list[dict[str, str]]:
    """
    Query live web/video search (DuckDuckGo DDGS) with rotating Chinese archival queries
    across Financial Crime and/or Major Violent Crime streams.
    Gracefully returns `[]` if network/DDGS is unavailable.
    """
    stream = normalize_requested_stream(topic_stream)
    queries: list[tuple[str, str]] = []
    r = max(0, int(research_round))

    if stream in {"all", "financial_crime"}:
        n_fin = 2 if stream == "all" else 4
        for idx in range(n_fin):
            q = FINANCIAL_CRIME_QUERY_BANK[(r * 2 + idx) % len(FINANCIAL_CRIME_QUERY_BANK)]
            queries.append(("financial_crime", q))

    if stream in {"all", "major_violent_crime"}:
        n_vio = 2 if stream == "all" else 4
        for idx in range(n_vio):
            q = MAJOR_VIOLENT_CRIME_QUERY_BANK[(r * 2 + idx) % len(MAJOR_VIOLENT_CRIME_QUERY_BANK)]
            queries.append(("major_violent_crime", q))

    def _make_ddgs() -> Any:
        if ddgs_factory is not None:
            return ddgs_factory()
        from ddgs import DDGS
        return DDGS(timeout=6)

    def _run_one(pair: tuple[str, str]) -> list[dict[str, str]]:
        s_id, q_str = pair
        collected: list[dict[str, str]] = []
        try:
            searcher = _make_ddgs()
            text_rows = list(searcher.text(q_str, region="wt-wt", safesearch="moderate", max_results=6) or [])
            for row in text_rows:
                if not isinstance(row, dict):
                    continue
                title = str(row.get("title") or "").strip()
                snippet = str(row.get("body") or row.get("description") or "").strip()
                url = str(row.get("href") or row.get("url") or "").strip()
                if title:
                    collected.append({
                        "stream_hint": s_id,
                        "query": q_str,
                        "title": title,
                        "snippet": snippet[:260],
                        "url": url,
                    })
        except Exception:
            pass
        return collected

    raw_leads: list[dict[str, str]] = []
    try:
        with ThreadPoolExecutor(max_workers=min(4, max(1, len(queries)))) as pool:
            futs = [pool.submit(_run_one, q) for q in queries]
            for fut in as_completed(futs, timeout=10):
                try:
                    raw_leads.extend(fut.result() or [])
                except Exception:
                    continue
    except Exception:
        pass

    exclusions = exclusion_records or []
    filtered: list[dict[str, str]] = []
    seen_titles: set[str] = set()
    for lead in raw_leads:
        t = str(lead.get("title") or "").strip()
        snip = str(lead.get("snippet") or "").strip()
        url = str(lead.get("url") or "").strip()
        low = f"{t} {snip} {url}".lower()
        if not t or len(t) < 6:
            continue
        if any(pat in low for pat in NOISE_LEAD_PATTERNS):
            continue
        # Require Chinese/Korean/Vietnamese characters or clear case indicators
        if not re.search(r"[\u4e00-\u9fff가-힣]", t + snip):
            continue
        key = t.lower()
        if key in seen_titles:
            continue
        is_dup, _ = _is_duplicate_against_records(f"{t} {snip}", exclusions)
        if is_dup:
            continue
        seen_titles.add(key)
        filtered.append(lead)
        if len(filtered) >= max_leads:
            break
    return filtered


# ==============================================================================
# VERIFIED REAL-CASE RESERVE (68 STREAM 1 FINANCIAL/VAULT/HEIST + 48 STREAM 2 PURE INVESTIGATIVE)
# 100% real documented Chinese cases with CCTV/court archival footage,
# 100% Broadcast Green-Dollar prose & 8 Topic-Adaptive Cold-Open Hook Archetypes.
# ==============================================================================

VERIFIED_TWO_STREAM_RESERVE_CASES: list[dict[str, Any]] = [
    {
        "id": "fin_cn_kaiping_485m",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "广东开平中国银行4.85亿美元贪污挪用潜逃案 — 许超凡·余振东·许国俊 (2001–2021)",
        "archival_search_keywords_zh": [
            "开平中行案 许超凡 庭审",
            "中国银行开平支行 4.85亿美元 今日说法",
            "许国俊 遣返回国 央视新闻"
        ],
        "recommended_vox_verbs": [
            "LEDGER_DIFF_SCRUB",
            "GEO_VECTOR_PURSUIT",
            "NETWORK_GRAPH"
        ],
        "title": "[중국 실화 사건] 은행장 3명이 금고에서 6,500억 원을 빼돌려 라스베이거스로 증발한 밤 | 카이핑 은행 사건 ([Vụ Án Có Thật ở Trung Quốc] Đêm 3 đời giám đốc ngân hàng rút ruột 6.500 tỷ Won khỏi két sắt rồi bốc hơi sang Las Vegas | Đại án Ngân hàng Khai Bình)",
        "topic_anchor": "[중국 실화 사건] 은행장 3명이 금고에서 6,500억 원을 빼돌려 라스베이거스로 증발한 밤 | 카이핑 은행 사건",
        "winner_cluster": "Luồng 1 · Đại Án Rút Ruột Ngân Hàng & Đào Tẩu Quốc Tế 20 Năm (카이핑 중국은행 4.85억 달러 사건)",
        "codex_score": 99,
        "profile_score": 99,
        "codex_angle": "Hồ Sơ Thật 100%: Đại Án Ngân Hàng Khai Bình (许超凡·余振东·许国俊) — Lỗ Hổng Nối Mạng Toàn Quốc Đêm 12/10/2001 & 20 Năm Truy Bắt Xuyên Thái Bình Dương",
        "codex_reasons": [
            "Đại án ngân hàng lớn nhất lịch sử Trung Quốc từ năm 1949 (485 triệu USD ~ 6.500 tỷ Won), cực giàu tư liệu bản tin CCTV, cảnh dẫn độ sân bay và phiên tòa Giang Môn (Quảng Đông)",
            "Cơ chế kết nối mạng máy tính ngân hàng toàn quốc đêm 12/10/2001 làm lộ hổng con số 485 triệu USD — khớp hoàn hảo động từ thị giác LEDGER_DIFF_SCRUB & GEO_VECTOR_PURSUIT"
        ],
        "opening_hook": "본점 전산망이 전국 지점의 장부를 사상 처음으로 하나로 묶던 밤, 모니터 한가운데에서 믿기 힘든 숫자가 붉게 깜빡이기 시작했습니다. 광둥성 카이핑 지점 금고에서 증발한 돈은 무려 4억 8,500만 달러, 우리 돈 6,500억 원. 경보음이 울렸을 때 전·현직 지점장 세 명의 책상은 이미 텅 비어 있었습니다.",
        "note": "【Hồ sơ vụ án: đại án 3 đời giám đốc rút ruột két sắt ngân hàng 485 triệu USD (6.500 tỷ Won) · truy nã đỏ quốc tế 20 năm】 Hồ sơ thật 100% Đại án Ngân hàng Trung Quốc chi nhánh Khai Bình (广东开平中行案 — Hứa Siêu Phàm 许超凡, Dư Chấn Đông 余振东, Hứa Quốc Tuấn 许国俊, 1993–2021): Lợi dụng kẽ hở sổ sách trước khi nối mạng toàn quốc để rút ruột 485 triệu USD, đánh bạc tại Macau & Las Vegas, kết hôn giả lấy thẻ xanh Mỹ rồi lẩn trốn ở thị trấn nhỏ Wichita (Kansas) trước khi lần lượt bị dẫn độ năm 2004, 2018 và 2021.",
        "hook_archetype": "double_life_unmasking"
    },
    {
        "id": "fin_cn_handan_vault_51m",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "河北邯郸农业银行金库5100万元现金被盗买彩票案 — 任晓峰·马向景 (2007)",
        "archival_search_keywords_zh": [
            "邯郸农行金库被盗案 任晓峰",
            "5100万 买彩票 金库 今日说法",
            "任晓峰 马向景 庭审现场"
        ],
        "recommended_vox_verbs": [
            "SCALE_MULTIPLICATION",
            "CRASH_TIMELINE",
            "CONCENTRIC_TRAP"
        ],
        "title": "[중국 실화 사건] 은행 지하 금고 현금 5,100만 위안으로 복권을 사 모은 두 금고지기 | 한단 농협 금고 증발 사건 ([Vụ Án Có Thật ở Trung Quốc] Hai thủ quỹ vét sạch 51 triệu tệ tiền mặt trong hầm két ngân hàng để mua vé số | Đại án két sắt Hàm Đan)",
        "topic_anchor": "[중국 실화 사건] 은행 지하 금고 현금 5,100만 위안으로 복권을 사 모은 두 금고지기 | 한단 농협 금고 증발 사건",
        "winner_cluster": "Luồng 1 · Đại Án Két Sắt Ngân Hàng & Vòng Xoáy Mua Vé Số Điên Cuồng (한단 농업은행 5,100만 위안 사건)",
        "codex_score": 98,
        "profile_score": 98,
        "codex_angle": "Hồ Sơ Thật 100%: Nhậm Hiểu Phong & Mã Hướng Cảnh (任晓峰·马向景) — 'Mượn Tạm Két Sắt Mua Vé Số Để Trúng Độc Đắc Bù Lại' & Cuộc Truy Nã Cấp A",
        "codex_reasons": [
            "Cơ chế tâm lý cờ bạc tài chính có một không hai: 2 quản kho giữ 2 chìa khóa két sắt cấu kết rút 51 triệu NDT tiền mặt chỉ để mua vé số suốt 1 tháng (ngày cao nhất mua hơn 3 triệu NDT vé số)",
            "Đầy đủ tư liệu CCTV quầy vé số, lệnh truy nã cấp A Bộ Công an và phiên tòa Hàm Đan (Hà Bắc)"
        ],
        "opening_hook": "두 사람이 동시에 각자의 열쇠를 돌려야만 열리는 은행 지하 금고. 2007년 봄, 허베이성 한단시 농업은행 금고 안에 쌓여 있던 현금 다발 오천백만 위안이 감쪽같이 사라졌습니다. 놀랍게도 범인들이 빼돌린 돈다발이 향한 곳은 해외 비밀 계좌가 아니라, 동네 복권 판매점들이었습니다.",
        "note": "【Hồ sơ vụ án: đại án 2 thủ quỹ lấy 51 triệu tệ tiền mặt trong hầm két ngân hàng đi mua vé số · lệnh truy nã cấp A bộ công an】 Hồ sơ thật 100% Đại án Két sắt Ngân hàng Nông nghiệp Hàm Đan, Hà Bắc (河北邯郸农行5100万金库大案 — Nhậm Hiểu Phong 任晓峰 & Mã Hướng Cảnh 马向景, 3–4/2007): Ban đầu lấy trộm 200.000 tệ mua vé số trúng nhỏ, sau đó lún sâu rút 51 triệu NDT tiền mặt trong kho bạc mua vé số để mong trúng giải bù lỗ rồi đào tẩu về Liên Vân Cảng & Bắc Kinh trước khi bị bắt giữ.",
        "hook_archetype": "micro_forensic_anomaly"
    },
    {
        "id": "fin_cn_harbin_gaoshan_1b",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "哈尔滨中国银行河松街支行10亿元票据诈骗潜逃案 — 高山·李东哲 (2000–2012)",
        "archival_search_keywords_zh": [
            "高山案 哈尔滨河松街支行 10亿",
            "高山 李东哲 今日说法",
            "中行高山案 潜逃加拿大"
        ],
        "recommended_vox_verbs": [
            "SPLIT_PARADOX",
            "LEDGER_DIFF_SCRUB",
            "GEO_VECTOR_PURSUIT"
        ],
        "title": "[중국 실화 사건] 가짜 도장 하나로 기업 예금 10억 위안을 증발시키고 캐나다로 숨은 은행 지점장 | 하얼빈 고산 사건 ([Vụ Án Có Thật ở Trung Quốc] Giám đốc chi nhánh dùng 1 con dấu giả làm bốc hơi 1 tỷ tệ tiền gửi doanh nghiệp rồi trốn sang Canada | Đại án Cao Sơn Cáp Nhĩ Tân)",
        "topic_anchor": "[중국 실화 사건] 가짜 도장 하나로 기업 예금 10억 위안을 증발시키고 캐나다로 숨은 은행 지점장 | 하얼빈 고산 사건",
        "winner_cluster": "Luồng 1 · Đại Án Sổ Đối Chiếu Giả 1 Tỷ Tệ & 8 Năm Ẩn Mình Ở Vancouver (하얼빈 허쑹가 지점 고산 사건)",
        "codex_score": 98,
        "profile_score": 98,
        "codex_angle": "Hồ Sơ Thật 100%: Cao Sơn & Lý Đông Triết (高山·李东哲) — Hai Hệ Thống Sổ Đối Chiếu Song Song Rút Ruột 1,029 Tỷ NDT Của Hơn 20 Doanh Nghiệp Lớn",
        "codex_reasons": [
            "Đại án chấn động ngành ngân hàng Đông Bắc Trung Quốc: doanh nghiệp cầm giấy xác nhận số dư 300 triệu tệ nhưng trong tài khoản thật chỉ còn vài chục nghìn tệ",
            "Bước ngoặt trớ trêu ở Vancouver (Canada): một vụ va chạm giao thông nhỏ trên đường phố Canada làm lộ tung tích kẻ đào tẩu 1 tỷ tệ"
        ],
        "opening_hook": "매달 은행에서 보내오는 잔액 증명서에는 분명 삼억 위안이 찍혀 있었습니다. 하지만 2005년 초, 하얼빈의 한 고속도로 회사가 자금을 인출하려 했을 때 계좌에 남은 돈은 고작 몇만 위안에 불과했습니다. 지점장 가오산이 만든 두 개의 장부 속에서 무려 십억 위안의 예금이 공중분해 된 뒤였습니다.",
        "note": "【Hồ sơ vụ án: đại án giám đốc ngân hàng dùng con dấu giả rút ruột hơn 1 tỷ tệ tiền gửi · đào tẩu sang Canada 8 năm】 Hồ sơ thật 100% Đại án Ngân hàng Trung Quốc chi nhánh phố Hà Tùng, Cáp Nhĩ Tân (哈尔滨中行河松街支行案 — Giám đốc Cao Sơn 高山 & anh em Lý Đông Triết 李东哲, 2000–2012): Dùng 'dịch vụ giao sổ đối chiếu tận cửa' bằng con dấu giả để rút ruột hơn 1 tỷ NDT từ hàng chục tập đoàn rồi trốn sang Vancouver (Canada) năm 2004, lộ diện sau một vụ tai nạn giao thông ở Canada và về nước chịu án.",
        "hook_archetype": "double_life_unmasking"
    },
    {
        "id": "fin_cn_zhongshan_plastic_420m",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "广东中山实业发展总公司4.2亿元挪用公款漂白整容潜逃泰国案 — 陈满雄·陈秋园 (1995–2002)",
        "archival_search_keywords_zh": [
            "陈满雄 4.2亿 整容 潜逃泰国",
            "中山陈满雄案 今日说法 天网",
            "漂白皮肤 逃犯 陈满雄"
        ],
        "recommended_vox_verbs": [
            "DUAL_ERA_LOCK",
            "GEO_VECTOR_PURSUIT",
            "LEDGER_DIFF_SCRUB"
        ],
        "title": "[중국 실화 사건] 공금 4억 2천만 위안 날리고 얼굴 피부까지 벗겨낸 부부의 7년 도주극 | 중산 천만슝 성형 세탁 사건 ([Vụ Án Có Thật ở Trung Quốc] Đốt sạch 420 triệu tệ công quỹ rồi lột da đổi mặt trốn 7 năm của cặp vợ chồng | Đại án phẫu thuật tẩy trắng Trần Mãn Hùng)",
        "topic_anchor": "[중국 실화 사건] 공금 4억 2천만 위안 날리고 얼굴 피부까지 벗겨낸 부부의 7년 도주극 | 중산 천만슝 성형 세탁 사건",
        "winner_cluster": "Luồng 1 · Đại Án 420 Triệu Tệ & Phẫu Thuật Đổi Mặt Thành Phú Hộ Thái Lan (중산 천만슝 4.2억 사건)",
        "codex_score": 97,
        "profile_score": 97,
        "codex_angle": "Hồ Sơ Thật 100%: Trần Mãn Hùng & Trần Thu Viên (陈满雄·陈秋园) — Rút Ruột Ngân Hàng Đánh Bạc Macau, Lột Trắng Da & Thay Gương Mặt Trốn Ở Chiang Mai Suốt 7 Năm",
        "codex_reasons": [
            "Kết hợp hoàn hảo Đại án tài chính 420 triệu NDT với màn tẩy trắng sinh trắc học cực đoan (phẫu thuật thẩm mỹ + tẩy trắng da toàn thân + nhập tịch Thái Lan tên Suthon)",
            "Có đầy đủ phóng sự CCTV, ảnh đối chiếu trước-sau phẫu thuật cực đắt cho động từ thị giác DUAL_ERA_LOCK"
        ],
        "opening_hook": "사억 이천만 위안의 은행 자금을 마카오 카지노 테이블 위에서 날려버린 부부. 수배령이 떨어지자 남편 천만슝은 자신의 검붉은 피부와 얼굴 윤곽까지 수술대 위에서 통째로 갈아엎었습니다. 7년 뒤 태국 치앙마이의 호화 저택에서 붙잡혔을 때, 옛 동료들조차 그의 얼굴을 알아보지 못했습니다.",
        "note": "【Hồ sơ vụ án: đại án biển thủ 420 triệu tệ công quỹ đánh bạc Macau · phẫu thuật lột da đổi mặt trốn sang Thái Lan 7 năm】 Hồ sơ thật 100% Đại án Trần Mãn Hùng & Trần Thu Viên tại Trung Sơn, Quảng Đông (广东中山4.2亿挪用公款案 — 陈满雄·陈秋园, 1995–2002): Thông đồng cán bộ ngân hàng rút 420 triệu NDT sang Macau đánh bạc, sau đó trốn sang Chiang Mai (Thái Lan), làm phẫu thuật thẩm mỹ xóa nốt ruồi, lột trắng da toàn thân, mua danh tính 'Suthon' làm ông chủ giàu có suốt 7 năm trước khi bị bắt giữ và dẫn độ về Quảng Đông.",
        "hook_archetype": "last_ordinary_routine"
    },
    {
        "id": "fin_cn_nanjing_fake_bank_400m",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "江苏南京假银行揽储4.2亿元特大金融诈骗案 — 张某·刘某农村经济专业合作社案 (2014–2015)",
        "archival_search_keywords_zh": [
            "南京 假银行 4亿 揽储 今日说法",
            "农村经济专业合作社 假冒银行 南京",
            "南京假银行案 庭审"
        ],
        "recommended_vox_verbs": [
            "SPLIT_PARADOX",
            "SCALE_MULTIPLICATION",
            "FORENSIC_ZOOM_CHAIN"
        ],
        "title": "[중국 실화 사건] 번호표 기계부터 방탄유리 창구까지 똑같이 지어 예금주 200명을 속인 가짜 국유은행 | 난징 위장 은행 사건 ([Vụ Án Có Thật ở Trung Quốc] Dựng nguyên quầy kính chống đạn và máy lấy số giống hệt ngân hàng quốc doanh để lừa 200 người gửi tiền | Đại án ngân hàng giả Nam Kinh)",
        "topic_anchor": "[중국 실화 사건] 번호표 기계부터 방탄유리 창구까지 똑같이 지어 예금주 200명을 속인 가짜 국유은행 | 난징 위장 은행 사건",
        "winner_cluster": "Luồng 1 · Đại Án Dựng Quầy Ngân Hàng Quốc Doanh Giả Huy Động 420 Triệu Tệ (난징 가짜 은행 사건)",
        "codex_score": 97,
        "profile_score": 97,
        "codex_angle": "Hồ Sơ Thật 100%: Chuyên Án 'Ngân Hàng Giả' Phố Phổ Khẩu, Nam Kinh (南京假银行揽储案) — Bóc Tách Màn Dàn Dựng Chi Nhánh Ngân Hàng Ma Đánh Lừa Hơn 200 Người Gửi Tiết Kiệm",
        "codex_reasons": [
            "Nghịch lý thị giác cực mạnh: biển đèn LED, quầy giao dịch kính dày, đồng phục giao dịch viên, cuốn sổ tiết kiệm đỏ in chìm đều giống ngân hàng thật 99%",
            "Nhiều phóng sự hiện trường của CCTV & Đài Giang Tô ghi hình trực tiếp quầy giao dịch giả"
        ],
        "opening_hook": "번듯한 LED 전광판과 번호표 발권기, 제복을 차려입은 창구 직원들, 그리고 도장이 선명하게 찍힌 붉은색 예금 통장까지. 누가 봐도 완벽한 국유은행 지점이었습니다. 하지만 만기 날 이자를 찾으러 간 예금주 이백여 명은 충격적인 진실과 마주했습니다. 그 건물은 아예 은행이 아니었습니다.",
        "note": "【Hồ sơ vụ án: đại án dựng quầy giao dịch ngân hàng quốc doanh giả 100% để lừa 420 triệu tệ tiền gửi của 200 người】 Hồ sơ thật 100% Vụ án 'Ngân hàng giả' tại quận Phổ Khẩu, Nam Kinh, Giang Tô (南京浦口假银行4.2亿揽储案, 2014–2015): Nhóm tội phạm dùng giấy phép 'Hợp tác xã kinh tế nông thôn' nhưng bỏ hàng triệu tệ thiết kế toàn bộ nội thất giống hệt quầy giao dịch ngân hàng quốc doanh, trả 'phí贴息' tuần đầu 2% để hút hơn 420 triệu NDT của gần 200 người dân.",
        "hook_archetype": "double_life_unmasking"
    },
    {
        "id": "fin_cn_shanghai_327_bond",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "上海万国证券327国债期货惊天违规事件 — 管金生 (1995)",
        "archival_search_keywords_zh": [
            "327国债期货事件 管金生 纪录片",
            "上海万国证券 327国债 8分钟",
            "管金生 庭审 纪实"
        ],
        "recommended_vox_verbs": [
            "CRASH_TIMELINE",
            "ROLLING_METRIC_SHOCK",
            "RADIAL_TIME_PRESSURE"
        ],
        "title": "[중국 실화 사건] 장 마감 8분 전, 천만 건의 유령 매도 주문이 중국 최대 증권사를 무너뜨렸다 | 상하이 327 국채 선물 대참사 ([Vụ Án Có Thật ở Trung Quốc] 8 phút trước giờ đóng cửa, 10 triệu lệnh bán khống đánh sập công ty chứng khoán số 1 Trung Quốc | Đại thảm họa công trái 327 Thượng Hải)",
        "topic_anchor": "[중국 실화 사건] 장 마감 8분 전, 천만 건의 유령 매도 주문이 중국 최대 증권사를 무너뜨렸다 | 상하이 327 국채 선물 대참사",
        "winner_cluster": "Luồng 1 · Đại Án Thao Túng Sàn Giao Dịch Công Trái 327 Trong 8 Phút Cuối (상하이 327 국채 사건)",
        "codex_score": 96,
        "profile_score": 96,
        "codex_angle": "Hồ Sơ Thật 100%: 'Bố Già Chứng Khoán' Quản Kim Sinh (管金生) & 480 Giây Cuối Ngày 23/2/1995 Trên Sàn Chứng Khoán Thượng Hải",
        "codex_reasons": [
            "Sự kiện tài chính kịch tính bậc nhất lịch sử chứng khoán Trung Quốc (tư liệu sàn Thượng Hải áo vest đỏ 1995 cực đắt giá)",
            "Cơ chế đếm ngược 8 phút cuối 16:22–16:30 khớp hoàn hảo động từ CRASH_TIMELINE & RADIAL_TIME_PRESSURE"
        ],
        "opening_hook": "1995년 2월 23일 오후 4시 22분, 상하이 증권거래소 마감까지 남은 시간은 단 팔 분. 패배가 확정된 듯 보였던 중국 최대 증권사 완궈증권의 단말기에서 갑자기 수백만 구좌의 무담보 매도 폭탄이 쏟아져 나왔습니다. 단 팔 분 만에 시장 전체가 뒤집혔지만, 그날 밤 거래소 문이 닫히며 전설의 몰락이 시작되었습니다.",
        "note": "【Hồ sơ vụ án: đại án thao túng sàn giao dịch công trái 327 bằng 10 triệu lệnh bán khống trong 8 phút cuối · sập công ty chứng khoán số 1】 Hồ sơ thật 100% Sự kiện hợp đồng tương lai công trái mã 327 tại Thượng Hải ngày 23/2/1995 (上海327国债期货事件 — Tổng giám đốc Vạn Quốc Chứng Khoán Quản Kim Sinh 管金生): Đối mặt nguy cơ vỡ nợ 6 tỷ NDT khi Bộ Tài chính nâng lãi bù trượt giá, trong 8 phút cuối (16:22:13–16:30) Quản Kim Sinh tung hơn 10 triệu lô lệnh bán khống không tiền ký quỹ kéo sập giá sàn trước khi Sở Giao dịch tuyên hủy giao dịch 8 phút cuối.",
        "hook_archetype": "locked_room_vault_paradox"
    },
    {
        "id": "fin_cn_hangzhou_42m_vanished_deposit",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "浙江杭州联合银行4200万元等9505万元储户存款失踪案 — 祝某·陈某 (2014–2015)",
        "archival_search_keywords_zh": [
            "杭州联合银行 4200万 存款失踪 今日说法",
            "银行卡在身上 4200万没了 杭州",
            "9505万 存款失踪案"
        ],
        "recommended_vox_verbs": [
            "LEDGER_DIFF_SCRUB",
            "CAUSAL_CHAIN",
            "BLIND_SPOT_REVEAL"
        ],
        "title": "[중국 실화 사건] 통장도 비밀번호도 내 손에 있었는데 은행 창구 뒤에서 사라진 9,500만 위안 | 항저우 예금 증발 미스터리 ([Vụ Án Có Thật ở Trung Quốc] Sổ tiết kiệm và mật khẩu vẫn nằm trên tay nhưng 95 triệu tệ bốc hơi ngay sau quầy giao dịch | Bí ẩn tiền gửi biến mất ở Hàng Châu)",
        "topic_anchor": "[중국 실화 사건] 통장도 비밀번호도 내 손에 있었는데 은행 창구 뒤에서 사라진 9,500만 위안 | 항저우 예금 증발 미스터리",
        "winner_cluster": "Luồng 1 · Bí Ẩn 95 Triệu Tệ Bốc Hơi Khỏi Sổ Tiết Kiệm Không Tin Nhắn Báo Động (항저우 예금 증발 사건)",
        "codex_score": 96,
        "profile_score": 96,
        "codex_angle": "Hồ Sơ Thật 100%: Vụ Án 42 Nạn Nhân Mất Trắng 95,05 Triệu NDT Tại Ngân Hàng Ở Hàng Châu — Kịch Bản '3 Không' Trên Bàn Giao Dịch Viên Nội Gián",
        "codex_reasons": [
            "Đánh trúng tâm lý sợ hãi thực tế nhất của khán giả Hàn Quốc (gửi tiền trực tiếp tại quầy ngân hàng thật, giữ sổ thật mà số dư bằng 0)",
            "Phóng sự điều tra chi tiết trên CCTV 今日说法 bóc tách từng thao tác tráo lệnh chuyển tiền 3 giây trên bàn phím giao dịch viên"
        ],
        "opening_hook": "통장은 집 금고 안에 그대로 있었고, 비밀번호는 오직 본인만 알고 있었습니다. 은행 정식 창구에서 직접 입금한 사천이백만 위안. 그런데 몇 달 뒤 잔액을 조회한 순간 화면에 찍힌 숫자는 단 일 위안뿐이었습니다. 문자 알림 하나 울리지 않은 채 구천오백만 위안이 창구 너머로 증발한 것입니다.",
        "note": "【Hồ sơ vụ án: đại án nội gián ngân hàng tráo lệnh tại quầy làm bốc hơi 95,05 triệu tệ trong sổ tiết kiệm của 42 khách hàng】 Hồ sơ thật 100% Vụ án bốc hơi 95,05 triệu NDT tiền gửi của 42 khách hàng tại Ngân hàng Liên Hợp Hàng Châu, Chiết Giang (杭州联合银行9505万存款失踪案, 2014–2015): Trưởng bộ phận giao dịch Chúc Mỗ (祝某) cấu kết môi giới tài chính dùng ưu đãi 'gửi 1 năm không rút, không mở SMS/Internet Banking' rồi lén kẹp giấy ủy quyền chuyển khoản ngay lúc khách bấm mật khẩu tại quầy.",
        "hook_archetype": "locked_room_vault_paradox"
    },
    {
        "id": "fin_cn_dongyang_wuying_3800m",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "浙江东阳本色集团38亿元集资诈骗案 — 吴英 (2006–2012)",
        "archival_search_keywords_zh": [
            "东阳吴英案 38亿 本色集团",
            "吴英 集资诈骗 今日说法 纪录片",
            "浙江吴英案 最高法"
        ],
        "recommended_vox_verbs": [
            "SCALE_MULTIPLICATION",
            "CRASH_TIMELINE",
            "NETWORK_GRAPH"
        ],
        "title": "[중국 실화 사건] 스물다섯 살 미용실 소녀는 어떻게 하룻밤에 거리 통째를 사들인 38억 위안의 여왕이 되었나 | 저장성 우잉 사건 ([Vụ Án Có Thật ở Trung Quốc] Cô thợ làm tóc 25 tuổi làm cách nào mua đứt cả con phố và nắm 3,8 tỷ tệ chỉ sau một đêm | Đại án Ngô Anh Chiết Giang)",
        "topic_anchor": "[중국 실화 사건] 스물다섯 살 미용실 소녀는 어떻게 하룻밤에 거리 통째를 사들인 38억 위안의 여왕이 되었나 | 저장성 우잉 사건",
        "winner_cluster": "Luồng 1 · Đế Chế Tín Dụng Ngầm 3,8 Tỷ Tệ Trong 10 Tháng & Sổ Cái Vỡ Trận (저장성 우잉 본색그룹 사건)",
        "codex_score": 95,
        "profile_score": 95,
        "codex_angle": "Hồ Sơ Thật 100%: Ngô Anh & Tập Đoàn Bổn Sắc (浙江东阳吴英案) — 100 Căn Mặt Tiền Mua Đứt Tiền Mặt, Lãi Ngầm 100%/Năm Và Chuỗi Domino Đứt Gãy Tín Dụng Tư Nhân",
        "codex_reasons": [
            "Đại án tài chính nổi tiếng bậc nhất Trung Quốc với kho tư liệu truyền hình khổng lồ về con phố Bổn Sắc bỏ hoang và phiên tòa phúc thẩm",
            "Bóc tách sắc lạnh toán học dòng tiền tín dụng ngầm Ôn Châu - Nghĩa Ô - Đông Dương"
        ],
        "opening_hook": "2006년 여름, 저장성 둥양시의 한 거리에 스물다섯 살의 낯선 젊은 여성이 나타났습니다. 그녀는 은행 대출 한 푼 없이 현금 트럭을 동원해 거리 양쪽의 상가 백여 채와 호텔을 통째로 사들였습니다. 불과 열 달 만에 삼십팔억 위안을 움직인 본색그룹 회장 우잉, 그 화려한 간판 뒤에서는 시한폭탄 같은 지하 장부가 돌아가고 있었습니다.",
        "note": "【Hồ sơ vụ án: đại án tín dụng ngầm huy động 3,89 tỷ tệ trong 10 tháng mua đứt cả con phố thương mại · vỡ nợ dây chuyền】 Hồ sơ thật 100% Đại án Ngô Anh (吴英, sinh năm 1981) — Tập đoàn Bổn Sắc tại Đông Dương, Chiết Giang (2006–2012): Trong chưa đầy 1 năm huy động 3,89 tỷ NDT từ mạng lưới tín dụng ngầm lãi suất siêu cao để lập 12 công ty và mua cả con phố thương mại nhằm tạo vỏ bọc thanh khoản trước khi đứt gãy chuỗi vốn.",
        "hook_archetype": "last_ordinary_routine"
    },
    {
        "id": "fin_cn_zhoukou_sinograin_700m",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "河南周口中储粮直属库7亿元幽灵粮仓贪污潜逃案 — 乔建军 (2011–2024)",
        "archival_search_keywords_zh": [
            "乔建军 中储粮 周口 7亿",
            "百名红通 乔建军 遣返 今日说法",
            "河南周口粮库 乔建军"
        ],
        "recommended_vox_verbs": [
            "LEDGER_DIFF_SCRUB",
            "SCALE_MULTIPLICATION",
            "GEO_VECTOR_PURSUIT"
        ],
        "title": "[중국 실화 사건] 텅 빈 국가 비축미 창고에 유령 곡물 장부를 꾸며 7억 위안을 빼돌린 창고장 | 차오젠쥔 13년 도주 사건 ([Vụ Án Có Thật ở Trung Quốc] Giám đốc kho lập sổ sách thóc ma trong kho dự trữ lương thực trống rỗng để rút ruột 700 triệu tệ | Đại án Kiều Kiến Quân)",
        "topic_anchor": "[중국 실화 사건] 텅 빈 국가 비축미 창고에 유령 곡물 장부를 꾸며 7억 위안을 빼돌린 창고장 | 차오젠쥔 13년 도주 사건",
        "winner_cluster": "Luồng 1 · Đại Án 'Kho Thóc Ma' 700 Triệu Tệ & Truy Nã Đỏ Số 3 Xuyên Âu - Mỹ (중추량 차오젠쥔 사건)",
        "codex_score": 97,
        "profile_score": 97,
        "codex_angle": "Hồ Sơ Thật 100%: Kiều Kiến Quân (乔建军) — Rút Ruột Kho Dự Trữ Lương Thực Quốc Gia Chu Khẩu (Hà Nam) Bằng Hợp Đồng Thu Mua Thóc Khống & 13 Năm Rửa Tiền Qua Mỹ - Thụy Điển",
        "codex_reasons": [
            "Nhân vật số 3 trong danh sách 100 tội phạm Truy nã Đỏ của Trung Quốc (百名红通第3号), tư liệu kho lương thực Chu Khẩu và dẫn độ quốc tế cực đầy đủ",
            "Bóc tách thủ đoạn 'thóc xoay vòng trên giấy' rút ruột 700 triệu NDT khớp hoàn hảo với LEDGER_DIFF_SCRUB"
        ],
        "opening_hook": "수만 톤의 국가 비상 식량이 가득 차 있어야 할 거대한 곡물 창고. 하지만 감사반이 창고 문을 열었을 때, 장부 위에 적혀 있던 수십만 톤의 곡물은 온데간데없고 바닥에는 먼지만 날리고 있었습니다. 창고장 차오젠쥔은 가짜 수매 영수증으로 칠억 위안을 챙겨 이미 지구 반대편으로 날아간 뒤였습니다.",
        "note": "【Hồ sơ vụ án: đại án giám đốc kho lương thực quốc gia lập hợp đồng thóc ma rút ruột 700 triệu tệ · truy nã đỏ số 3 trốn 13 năm】 Hồ sơ thật 100% Đại án Kho dự trữ lương thực Trung Trữ Lương chi nhánh Chu Khẩu, Hà Nam (中储粮周口直属库主任乔建军案, 2011): Lập hợp đồng thu mua lương thực khống để rút ruột hơn 700 triệu NDT (chuyển lậu hơn 200 triệu NDT ra nước ngoài) rồi trốn qua Mỹ và Thụy Điển suốt hơn 10 năm trước khi bị dẫn độ.",
        "hook_archetype": "micro_forensic_anomaly"
    },
    {
        "id": "fin_cn_poyang_li_huabo_94m",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "江西鄱阳县财政局9400万元民生资金伪造公章挪用潜逃新加坡案 — 李华波 (2006–2015)",
        "archival_search_keywords_zh": [
            "李华波 鄱阳县 9400万 今日说法",
            "百名红通 李华波 遣返 央视",
            "一枚假公章 9400万 李华波"
        ],
        "recommended_vox_verbs": [
            "SINGLE_EVIDENCE_AUTOPSY",
            "LEDGER_DIFF_SCRUB",
            "GEO_VECTOR_PURSUIT"
        ],
        "title": "[중국 실화 사건] 가짜 도장 하나로 가난한 군청 금고에서 9,400만 위안을 빼돌린 말단 과장의 싱가포르 도주극 | 포양현 리화보 사건 ([Vụ Án Có Thật ở Trung Quốc] Trưởng phòng quèn dùng 1 con dấu giả rút ruột 94 triệu tệ khỏi kho bạc huyện nghèo rồi trốn sang Singapore | Đại án Lý Hoa Ba)",
        "topic_anchor": "[중국 실화 사건] 가짜 도장 하나로 가난한 군청 금고에서 9,400만 위안을 빼돌린 말단 과장의 싱가포르 도주극 | 포양현 리화보 사건",
        "winner_cluster": "Luồng 1 · Con Dấu Khắc Lậu Rút 94 Triệu Tệ Ngân Sách Huyện Nghèo & Dẫn Độ Singapore (포양현 리화보 사건)",
        "codex_score": 96,
        "profile_score": 96,
        "codex_angle": "Hồ Sơ Thật 100%: Lý Hoa Ba (李华波 — Huyện Bà Dương, Giang Tây) — 5 Năm Dùng Con Dấu Giả Qua Mặt Ngân Hàng Rút 94 Triệu NDT Đánh Bạc Macau & Cuộc Đấu Pháp Lý Tịch Thu Tài Sản Ở Singapore",
        "codex_reasons": [
            "Nhân vật số 2 trong danh sách 100 Truy nã Đỏ (百名红通第2号), có phim tài liệu riêng trên CCTV (《红色通缉》) và 今日说法",
            "Nghịch lý cực đắt: một huyện nghèo cấp quốc gia nhưng trưởng phòng tài chính lại rút 94 triệu tệ chỉ bằng một con dấu giả khắc ngoài chợ"
        ],
        "opening_hook": "국가급 빈곤현으로 지정된 장시성 포양현의 재정국 사무실. 평범한 과장이었던 리화보는 길거리에서 판 가짜 은행 도장 하나로 오 년 동안 무려 구천사백만 위안의 공금을 감쪽같이 빼돌렸습니다. 설날 연휴 직전 가족과 함께 싱가포르로 사라진 그가 남긴 것은 단 한 통의 편지뿐이었습니다.",
        "note": "【Hồ sơ vụ án: đại án trưởng phòng tài chính dùng 1 con dấu giả rút ruột 94 triệu tệ ngân sách huyện nghèo · truy nã đỏ số 2 trốn sang Singapore】 Hồ sơ thật 100% Đại án Lý Hoa Ba — Trưởng phòng Kinh tế Xây dựng Cục Tài chính huyện Bà Dương, Giang Tây (江西鄱阳县财政局李华波9400万贪污案, 2006–2015): Dùng con dấu giả và séc thanh toán khống rút 94 triệu NDT quỹ dân sinh chuyển sang Macau đánh bạc và mua thẻ cư trú đầu tư tại Singapore trước khi bị dẫn độ về nước tháng 5/2015.",
        "hook_archetype": "micro_forensic_anomaly"
    },
    {
        "id": "fin_cn_tonghua_yan_yongming_casino",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "吉林通化金马药业董事长职务侵占潜逃15年豪赌案 — 闫永明 (2000–2016)",
        "archival_search_keywords_zh": [
            "闫永明 通化金马 百名红通 央视",
            "闫永明 新西兰 82分钟 3亿",
            "中国伟哥之父 闫永明 归案"
        ],
        "recommended_vox_verbs": [
            "ROLLING_METRIC_SHOCK",
            "CRASH_TIMELINE",
            "GEO_VECTOR_PURSUIT"
        ],
        "title": "[중국 실화 사건] 82분 만에 카지노에서 500억 날린 '20대 제약왕'의 15년 뉴질랜드 도주극 | 옌융밍 추적 사건 ([Vụ Án Có Thật ở Trung Quốc] 15 năm trốn ở New Zealand của 'ông trùm dược phẩm 29 tuổi' đốt 50 tỷ Won tại sòng bài chỉ trong 82 phút | Đại án Diêm Vĩnh Minh)",
        "topic_anchor": "[중국 실화 사건] 82분 만에 카지노에서 500억 날린 '20대 제약왕'의 15년 뉴질랜드 도주극 | 옌융밍 추적 사건",
        "winner_cluster": "Luồng 1 · 'Ông Trùm Dược Phẩm' Rút Ruột Công Ty Niêm Yết & Đốt 300 Triệu Đô Ở Casino (통화진마 옌융밍 사건)",
        "codex_score": 96,
        "profile_score": 96,
        "codex_angle": "Hồ Sơ Thật 100%: Diêm Vĩnh Minh (闫永明 — Chủ Tịch Thông Hóa Kim Mã, Truy Nã Đỏ Số 5) — Từ Tỷ Phú 29 Tuổi Đến Kẻ Đốt Tiền Tại SkyCity Casino Auckland & Hợp Tác Phong Tỏa Tài Sản Trung - New Zealand",
        "codex_reasons": [
            "Nhân vật số 5 trong 100 Truy nã Đỏ (百名红通第5号), tư liệu truyền hình New Zealand & CCTV cực kỳ phong phú",
            "Con số chấn động: thua gần 5 triệu NZD chỉ trong 82 phút và tổng số tiền xoay vòng tại casino lên tới hàng trăm triệu đô"
        ],
        "opening_hook": "스물아홉 살의 나이에 상장 제약회사의 회장이 되어 수천억 원대 자산가로 떠올랐던 사나이 옌융밍. 그러나 회계 감사가 시작되자 그는 거액의 회사 자금을 빼돌려 뉴질랜드로 사라졌습니다. 오클랜드 최고급 호텔 펜트하우스에 숨어 단 팔십이 분 만에 수백억 원을 카지노 테이블에 뿌리던 그의 십오 년 도주극을 추적합니다.",
        "note": "【Hồ sơ vụ án: đại án chủ tịch tập đoàn dược phẩm biển thủ 187 triệu tệ trốn sang New Zealand 15 năm · đốt 50 tỷ Won ở casino trong 82 phút】 Hồ sơ thật 100% Đại án Diêm Vĩnh Minh (闫永明, sinh năm 1971) — cựu Chủ tịch Công ty Dược phẩm Thông Hóa Kim Mã, Cát Lâm (吉林通化金马药业案, 2000–2016): Biển thủ 187 triệu NDT rồi trốn sang Úc và New Zealand dưới tên Lưu Dương (刘阳), nướng hàng trăm triệu đô tại SkyCity Casino trước khi bị phong tỏa 42,85 triệu NZD và dẫn độ về Trung Quốc tháng 11/2016.",
        "hook_archetype": "double_life_unmasking"
    },
    {
        "id": "fin_cn_wenzhou_yang_xiuzhu_13y",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "浙江温州副市长2.5亿元巨额贪腐跨6国潜逃13年案 — 杨秀珠 (2003–2016)",
        "archival_search_keywords_zh": [
            "杨秀珠 百名红通头号 归案 央视",
            "温州 杨秀珠 13年 跨国追逃",
            "红色通缉 杨秀珠 纪录片"
        ],
        "recommended_vox_verbs": [
            "GEO_VECTOR_PURSUIT",
            "CONCENTRIC_TRAP",
            "LEDGER_DIFF_SCRUB"
        ],
        "title": "[중국 실화 사건] 맨해튼 빌딩 사들이며 6개국을 떠돈 '적색수배 1호'의 13년 도주 끝은 지하 감방이었다 | 양슈주 추적 사건 ([Vụ Án Có Thật ở Trung Quốc] Mua cao ốc Manhattan rồi chạy trốn qua 6 quốc gia suốt 13 năm, kết cục của 'Truy nã đỏ số 1' là xà lim ngầm | Đại án Dương Tú Châu)",
        "topic_anchor": "[중국 실화 사건] 맨해튼 빌딩 사들이며 6개국을 떠돈 '적색수배 1호'의 13년 도주 끝은 지하 감방이었다 | 양슈주 추적 사건",
        "winner_cluster": "Luồng 1 · Kẻ Truy Nã Đỏ Số 1 Mua Cao Ốc Manhattan & 13 Năm Chạy Trốn 6 Quốc Gia (원저우 양슈주 사건)",
        "codex_score": 96,
        "profile_score": 96,
        "codex_angle": "Hồ Sơ Thật 100%: Dương Tú Châu (杨秀珠 — Truy Nã Đỏ Số 1) — Rút Ruột Quỹ Quy Hoạch Ôn Châu Mua Bất Động Sản New York, Trốn Dưới Hầm Khoai Tây Hà Lan Rồi Bị Bắt Bằng Hộ Chiếu Giả",
        "codex_reasons": [
            "Đứng vị trí số 1 trong danh sách 100 Truy nã Đỏ của Trung Quốc (百名红通第1号), phim tài liệu CCTV 《红色通缉》 tập 1 ghi hình chi tiết từ New York đến Rotterdam",
            "Hành trình 6 nước (Singapore -> Mỹ -> Hà Lan -> Canada -> Mỹ) cực hợp cho GEO_VECTOR_PURSUIT"
        ],
        "opening_hook": "미국 뉴욕 맨해튼 중심가의 오층짜리 빌딩 주인이 된 중국 지방 도시의 간부. 이억 오천만 위안이 넘는 거액을 빼돌려 세계 여섯 개 나라를 돌며 십삼 년간 도망 다녔던 중국 적색수배 일 호 인물 양슈주. 화려했던 맨해튼 건물주의 도주극은 네덜란드의 축축한 지하실과 미국 이민국 구치소에서 막을 내렸습니다.",
        "note": "【Hồ sơ vụ án: đại án phó thị trưởng tham ô 253 triệu tệ · tội phạm truy nã đỏ số 1 dùng hộ chiếu giả trốn qua 6 quốc gia suốt 13 năm】 Hồ sơ thật 100% Đại án Dương Tú Châu (杨秀珠 — cựu Phó thị trưởng Ôn Châu, Chiết Giang, đứng số 1 danh sách 100 Truy nã Đỏ, 2003–2016): Lợi dụng quy hoạch đường sắt và đất đai biển thủ hơn 253 triệu NDT, mua tòa nhà tại Manhattan (New York), chạy trốn qua 6 quốc gia suốt 13 năm trước khi bị bắt vì dùng hộ chiếu Hà Lan giả và về nước chịu án tháng 11/2016.",
        "hook_archetype": "double_life_unmasking"
    },
    {
        "id": "fin_cn_shanghai_dai_xuemin_fox1",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "中经开上海证券营业部总经理1100万元挪用潜逃14年猎狐首案 — 戴学民 (2001–2015)",
        "archival_search_keywords_zh": [
            "戴学民 百名红通首犯 落网 央视",
            "中经开 戴学民 改头换面 14年",
            "猎狐行动 戴学民 今日说法"
        ],
        "recommended_vox_verbs": [
            "DUAL_ERA_LOCK",
            "FORENSIC_ZOOM_CHAIN",
            "GEO_VECTOR_PURSUIT"
        ],
        "title": "[중국 실화 사건] 해외로 도망친 줄 알았던 증권사 사장이 14년 뒤 가짜 여권 들고 상하이에 나타난 이유 | 다이쉐민 위장 귀국 사건 ([Vụ Án Có Thật ở Trung Quốc] Tưởng đã trốn ra nước ngoài, vì sao giám đốc chứng khoán lại cầm hộ chiếu giả xuất hiện ở Thượng Hải sau 14 năm | Chuyên án Đới Học Dân)",
        "topic_anchor": "[중국 실화 사건] 해외로 도망친 줄 알았던 증권사 사장이 14년 뒤 가짜 여권 들고 상하이에 나타난 이유 | 다이쉐민 위장 귀국 사건",
        "winner_cluster": "Luồng 1 · 'Đèn Chân Nến Tối' — Đào Tẩu Belize Đổi Hộ Chiếu Rồi Quay Ngược Về Nước Đầu Tư (다이쉐민 사건)",
        "codex_score": 95,
        "profile_score": 95,
        "codex_angle": "Hồ Sơ Thật 100%: Đới Học Dân (戴学民) — Giám Đốc Chứng Khoán Thượng Hải Rút 11 Triệu NDT Trốn Sang Belize Đổi Tên Thành 'Đới Trung Quế' Rồi Quay Lại Hợp Phì Suốt 14 Năm",
        "codex_reasons": [
            "Kẻ đầu tiên bị bắt trong danh sách 100 Truy nã Đỏ (ngày 25/4/2015 chỉ 3 ngày sau khi công bố danh sách), video bắt giữ thực tế cực rõ nét",
            "Chiến thuật phản trinh sát 'nơi nguy hiểm nhất là nơi an toàn nhất' + đối sánh sinh trắc học mắt & tai cực hợp DUAL_ERA_LOCK"
        ],
        "opening_hook": "일천백만 위안의 증권 자금을 빼돌린 뒤 중앙아메리카의 작은 나라 벨리즈로 사라졌던 증권사 사장 다이쉐민. 십사 년 동안 해외 어딘가에 숨어 있을 것이라 여겨졌던 그가, 적색수배 명단이 공개된 지 단 사흘 만에 뜻밖에도 안후이성 허페이의 한 거리에서 포착되었습니다.",
        "note": "【Hồ sơ vụ án: đại án tổng giám đốc công ty chứng khoán biển thủ 11 triệu tệ trốn 14 năm · chuyên án số 1 chiến dịch Săn Cáo (Liệp Hồ)】 Hồ sơ thật 100% Chuyên án Đới Học Dân (戴学民 — cựu Tổng giám đốc Phòng giao dịch Chứng khoán Thượng Hải thuộc Công ty Tín thác Phát triển Kinh tế Trung Quốc, 2001–2015): Biển thủ 11 triệu NDT trốn sang Belize tháng 8/2001, sau đó làm giả hộ chiếu và CMND mang tên 'Đới Trung Quế' (戴忠桂) lén quay về Hợp Phì & Nam Kinh làm ăn suốt 14 năm trước khi bị bắt ngày 25/4/2015.",
        "hook_archetype": "double_life_unmasking"
    },
    {
        "id": "fin_cn_xiamen_yuanhua_smuggling",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "福建厦门远华集团530亿元特大走私偷税潜逃加拿大12年案 — 赖昌星 (1996–2011)",
        "archival_search_keywords_zh": [
            "厦门远华案 赖昌星 纪录片",
            "赖昌星 530亿 遣返 央视新闻",
            "远华大案 红楼 纪实"
        ],
        "recommended_vox_verbs": [
            "NETWORK_GRAPH",
            "SCALE_MULTIPLICATION",
            "GEO_VECTOR_PURSUIT"
        ],
        "title": "[중국 실화 사건] 항구와 세관을 통째로 매수해 530억 위안을 삼킨 밀수 제국의 몰락과 12년 송환 전쟁 | 샤먼 라이창싱 사건 ([Vụ Án Có Thật ở Trung Quốc] Mua đứt cảng biển và hải quan để nuốt 53 tỷ tệ, sự sụp đổ của đế chế buôn lậu và 12 năm dẫn độ | Đại án Lại Xương Tinh Hạ Môn)",
        "topic_anchor": "[중국 실화 사건] 항구와 세관을 통째로 매수해 530억 위안을 삼킨 밀수 제국의 몰락과 12년 송환 전쟁 | 샤먼 라이창싱 사건",
        "winner_cluster": "Luồng 1 · Đế Chế Buôn Lậu Viễn Hoa 53 Tỷ Tệ & 12 Năm Đấu Pháp Lý Dẫn Độ Từ Canada (샤먼 위안화 라이창싱 사건)",
        "codex_score": 98,
        "profile_score": 98,
        "codex_angle": "Hồ Sơ Thật 100%: Đại Án Viễn Hoa Hạ Môn — Lại Xương Tinh (赖昌星) Thiết Lập 'Hồng Lầu' Thao Túng Cảng Biển 53 Tỷ NDT & Cuộc Đàm Phán Dẫn Độ Lịch Sử 12 Năm Giữa Bắc Kinh - Ottawa",
        "codex_reasons": [
            "Đại án kinh tế - buôn lậu lớn nhất lịch sử Trung Quốc hiện đại (53 tỷ NDT hàng hóa, trốn thuế 30 tỷ NDT), kho tư liệu truyền hình cực kỳ đồ sộ",
            "100% Xanh tiền: tập trung vào sơ đồ kiểm toán cảng biển, mạng lưới hối lộ 'Hồng Lầu' và 12 năm đấu tranh pháp lý dẫn độ từ Vancouver (1999–2011)"
        ],
        "opening_hook": "초등학교 삼 학년 중퇴 학력으로 시작해 도시 전체의 항구와 세관을 자신의 손아귀에 넣었던 사나이 라이창싱. 오백삼십억 위안어치의 석유와 자동차가 세금 한 푼 없이 샤먼 항구로 쏟아져 들어오는 동안, 그 중심에는 '홍루'라 불린 일곱 층짜리 붉은 건물의 비밀 장부가 있었습니다.",
        "note": "【Hồ sơ vụ án: đại án buôn lậu & trốn thuế 53 tỷ tệ lớn nhất lịch sử hiện đại · ông trùm Lại Xương Tinh đào tẩu sang Canada 12 năm】 Hồ sơ thật 100% Đại án Tập đoàn Viễn Hoa Hạ Môn, Phúc Kiến (福建厦门远华特大走私案 — Lại Xương Tinh 赖昌星, 1996–2011): Tổ chức đường dây nhập lậu xăng dầu, ô tô, nguyên liệu trị giá 53 tỷ NDT (trốn thuế 30 tỷ NDT), trốn sang Vancouver (Canada) năm 1999 và bị dẫn độ về Bắc Kinh tháng 7/2011, lĩnh án tù chung thân.",
        "hook_archetype": "double_life_unmasking"
    },
    {
        "id": "fin_cn_qianbao_zhang_xiaolei_72b",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "江苏南京钱宝网720亿元非法集资崩盘自首案 — 张小雷 (2012–2017)",
        "archival_search_keywords_zh": [
            "钱宝网 张小雷 720亿 今日说法",
            "南京钱宝网 自首 央视新闻",
            "张小雷 庭审 纪实"
        ],
        "recommended_vox_verbs": [
            "CRASH_TIMELINE",
            "SCALE_MULTIPLICATION",
            "ROLLING_METRIC_SHOCK"
        ],
        "title": "[중국 실화 사건] 광고만 클릭해도 연 40% 이자를 준다며 720억 위안을 끌어모은 제국 회장의 자수 미스터리 | 난징 첸바오왕 사건 ([Vụ Án Có Thật ở Trung Quốc] Bí ẩn ngày chủ tịch đế chế 72 tỷ tệ trả lãi 40%/năm chỉ nhờ bấm xem quảng cáo tự bước vào đồn cảnh sát | Đại án Tiền Bảo Võng Nam Kinh)",
        "topic_anchor": "[중국 실화 사건] 광고만 클릭해도 연 40% 이자를 준다며 720억 위안을 끌어모은 제국 회장의 자수 미스터리 | 난징 첸바오왕 사건",
        "winner_cluster": "Luồng 1 · Đế Chế 'Đặt Cọc Xem Quảng Cáo' 72 Tỷ Tệ & Cú Đầu Thú Đêm Giáng Sinh (난징 첸바오왕 장샤오레이 사건)",
        "codex_score": 97,
        "profile_score": 97,
        "codex_angle": "Hồ Sơ Thật 100%: Trương Tiểu Lôi & Tiền Bảo Võng (南京钱宝网720亿案) — Ma Trận Đặt Cọc 100.000 Tệ Để 'Điểm Danh Nhận Lãi' & Thời Khắc Đứt Thanh Khoản Ngày 26/12/2017",
        "codex_reasons": [
            "Đại án Ponzi tài chính nổi tiếng bậc nhất Nam Kinh (quy mô luân chuyển hơn 72 tỷ NDT, hàng triệu người dùng), tư liệu CCTV và phiên tòa Nam Kinh năm 2019 cực kỳ đầy đủ",
            "Twist tâm lý đắt giá: ngay sau khi quay video chúc Tết nhà đầu tư, Trương Tiểu Lôi lặng lẽ đến Công an Nam Kinh tự thú vì sổ cái đã cạn sạch tiền"
        ],
        "opening_hook": "보증금 십만 위안을 걸어두고 매일 스마트폰 광고 몇 개만 클릭하면 연 사십 퍼센트가 넘는 수익을 챙길 수 있다는 앱 첸바오왕. 수백만 명이 집을 팔아 보증금을 넣었지만, 2017년 12월 26일 아침 경찰이 발표한 한 줄의 공고에 투자자들은 처음에 해킹이라며 믿지 않았습니다. 회장 장샤오레이가 스스로 경찰서에 걸어 들어가 자수했다는 소식이었습니다.",
        "note": "【Hồ sơ vụ án: đại án siêu lừa đảo tài chính 72 tỷ tệ qua ứng dụng điểm thưởng · ông chủ tự đến đồn công an đầu thú đêm sập sàn】 Hồ sơ thật 100% Đại án Tiền Bảo Võng tại Nam Kinh, Giang Tô (江苏南京钱宝网非法集资案 — Trương Tiểu Lôi 张小雷, 2012–2017): Dùng mô hình nạp tiền ký quỹ lớn để làm nhiệm vụ xem quảng cáo hưởng lãi 40%–60%/năm, thu hút hơn 72 tỷ NDT tiền nạp trước khi vỡ thanh khoản và Trương Tiểu Lôi ra đầu thú ngày 26/12/2017 (lĩnh án 15 năm tù năm 2019).",
        "hook_archetype": "double_life_unmasking"
    },
    {
        "id": "fin_cn_fanya_indium_43b",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "云南昆明泛亚有色金属交易所430亿元非法集资案 — 单九良 (2011–2015)",
        "archival_search_keywords_zh": [
            "泛亚有色金属交易所 单九良 430亿",
            "昆明泛亚案 庭审 央视新闻",
            "泛亚 铟 3600吨 纪实"
        ],
        "recommended_vox_verbs": [
            "SCALE_MULTIPLICATION",
            "LEDGER_DIFF_SCRUB",
            "CRASH_TIMELINE"
        ],
        "title": "[중국 실화 사건] 창고에 희귀 금속 3,600톤만 남겨두고 투자금 430억 위안이 하루아침에 증발한 이유 | 쿤밍 판야 거래소 사건 ([Vụ Án Có Thật ở Trung Quốc] Lý do 43 tỷ tệ tiền đầu tư bốc hơi chỉ sau một đêm bên cạnh 3.600 tấn kim loại hiếm chất đống trong kho | Đại án Sàn Phàn Á Côn Minh)",
        "topic_anchor": "[중국 실화 사건] 창고에 희귀 금속 3,600톤만 남겨두고 투자금 430억 위안이 하루아침에 증발한 이유 | 쿤밍 판야 거래소 사건",
        "winner_cluster": "Luồng 1 · 3.600 Tấn Kim Loại Hiếm Indium Đóng Băng 43 Tỷ Tệ Của 220.000 Gia Đình (쿤밍 판야 유색금속 사건)",
        "codex_score": 96,
        "profile_score": 96,
        "codex_angle": "Hồ Sơ Thật 100%: Đơn Cửu Lương & Sàn Kim Loại Hiếm Phàn Á (昆明泛亚430亿案) — Thao Túng Trữ Lượng Indium Toàn Cầu Bằng Tiền Tiết Kiệm Dân Sinh",
        "codex_reasons": [
            "Đại án sàn giao dịch kim loại hiếm lớn nhất Trung Quốc (43 tỷ NDT, 220.000 nạn nhân khắp 20 tỉnh), hình ảnh kho kim loại Indium 3.600 tấn đấu giá năm 2019 cực ấn tượng",
            "Khớp hoàn hảo các động từ thị giác SCALE_MULTIPLICATION & LEDGER_DIFF_SCRUB"
        ],
        "opening_hook": "반도체와 액정 화면에 쓰이는 희귀 금속 '인듐'에 투자하면 매일 저녁 이자가 통장에 꽂히고 언제든 원금을 뺄 수 있다는 상품 일금보. 이십이만 명의 투자자가 사백삼십억 위안을 쏟아부었지만, 거래소가 멈춰 섰을 때 창고에 남은 것은 아무도 사가지 않는 차가운 금속 덩어리 삼천육백 톤뿐이었습니다.",
        "note": "【Hồ sơ vụ án: đại án thao túng sàn giao dịch kim loại hiếm 43 tỷ tệ của 220.000 nhà đầu tư & 3.600 tấn kim loại Indium nằm chết trong kho】 Hồ sơ thật 100% Đại án Sàn giao dịch Kim loại màu Phàn Á tại Côn Minh, Vân Nam (云南昆明泛亚有色金属交易所430亿案 — Đơn Cửu Lương 单九良, 2011–2015): Dùng sản phẩm 'Nhật Kim Bảo' hứa hẹn lãi suất 13,6%/năm thanh toán theo ngày để hút 43 tỷ NDT từ 220.000 người, tự đẩy giá và ôm 3.600 tấn kim loại hiếm Indium trước khi sụp đổ tháng 4/2015 (Đơn Cửu Lương lĩnh án 18 năm tù năm 2019).",
        "hook_archetype": "micro_forensic_anomaly"
    },
    {
        "id": "fin_cn_henan_rural_banks_40b",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "河南4家村镇银行400亿元线上揽储爆雷与假核心系统案 — 吕奕·新财富集团 (2022)",
        "archival_search_keywords_zh": [
            "河南村镇银行 吕奕 400亿",
            "禹州新民生村镇银行 新财富集团 央视",
            "河南村镇银行 假系统"
        ],
        "recommended_vox_verbs": [
            "SPLIT_PARADOX",
            "LEDGER_DIFF_SCRUB",
            "NETWORK_GRAPH"
        ],
        "title": "[중국 실화 사건] 정식 은행 앱에 넣은 예금 400억 위안이 은행 본점 장부에는 단 1원도 없었던 이유 | 허난 촌진은행 증발 사건 ([Vụ Án Có Thật ở Trung Quốc] Lý do 40 tỷ tệ gửi trên ứng dụng ngân hàng chính thức lại không tồn tại lấy 1 đồng trên sổ cái hội sở | Đại án Ngân hàng Thôn Trấn Hà Nam)",
        "topic_anchor": "[중국 실화 사건] 정식 은행 앱에 넣은 예금 400억 위안이 은행 본점 장부에는 단 1원도 없었던 이유 | 허난 촌진은행 증발 사건",
        "winner_cluster": "Luồng 1 · 'Hai Hệ Thống Máy Chủ Song Song' Hút 40 Tỷ Tệ Của 400.000 Người Gửi Tiền (허난 촌진은행 뤼이 사건)",
        "codex_score": 98,
        "profile_score": 98,
        "codex_angle": "Hồ Sơ Thật 100%: Lữ Dịch & Tập Đoàn Tân Tài Phú (河南村镇银行400亿案) — Cài Cắm Máy Chủ Phụ Giả Mạo Giữa App Ngân Hàng Và Hệ Thống Thanh Toán Trung Ương",
        "codex_reasons": [
            "Đại án ngân hàng hiện đại chấn động nhất Trung Quốc năm 2022 (40 tỷ NDT ~ 7.500 tỷ Won của 400.000 người gửi tiền qua ứng dụng trực tuyến)",
            "Cơ chế kỹ thuật cực đắt cho SPLIT_PARADOX: khách hàng nhìn thấy số dư trên app ngân hàng nhưng dòng tiền thật bị bẻ lái sang máy chủ ngầm của Tập đoàn Tân Tài Phú"
        ],
        "opening_hook": "국가 예금보험 마크가 선명하게 찍힌 정식 은행 상품이었습니다. 전국 사십만 명의 시민들은 조금이라도 더 높은 이자를 받기 위해 허난성의 네 개 은행 계좌에 사백억 위안을 맡겼습니다. 그러나 2022년 4월 18일, 갑자기 모든 인출 창구가 닫혔고 경찰 수사 결과 그 돈은 애초에 은행 진짜 전산망에 들어간 적조차 없었다는 사실이 밝혀졌습니다.",
        "note": "【Hồ sơ vụ án: đại án cài hệ thống máy chủ ngân hàng giả rút ruột 40 tỷ tệ tiền gửi tại 4 ngân hàng nông thôn · chủ mưu đào tẩu quốc tế】 Hồ sơ thật 100% Đại án 4 Ngân hàng Thôn Trấn Hà Nam (禹州新民生、上蔡惠民、柘城黄淮、开封新东方村镇银行 — Chủ mưu Lữ Dịch 吕奕 & Tập đoàn Tân Tài Phú 河南新财富集团, 4/2022): Thao túng cổ phần ngân hàng và thuê công ty công nghệ lập hệ thống dữ liệu giả mạo để rút ruột 40 tỷ NDT tiền gửi trực tuyến của hơn 400.000 khách hàng.",
        "hook_archetype": "countdown_system_breach"
    },
    {
        "id": "fin_cn_shanxinhui_zhang_tianming_100b",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "深圳善心汇1046亿元特大慈善包装传销案 — 张天明 (2016–2017)",
        "archival_search_keywords_zh": [
            "善心汇 张天明 1046亿 央视新闻",
            "张天明 庭审 今日说法",
            "深圳善心汇 特大传销案"
        ],
        "recommended_vox_verbs": [
            "SCALE_MULTIPLICATION",
            "NETWORK_GRAPH",
            "CRASH_TIMELINE"
        ],
        "title": "[중국 실화 사건] 가난한 이웃을 도우면 보름 뒤 30% 수익이 돌아온다며 500만 명을 홀린 1,000억 자선 제국 | 선신후이 사건 ([Vụ Án Có Thật ở Trung Quốc] Đế chế từ thiện 100 tỷ tệ cuốn 5 triệu người bằng lời hứa giúp người nghèo nhận lãi 30% sau 15 ngày | Đại án Thiện Tâm Hội)",
        "topic_anchor": "[중국 실화 사건] 가난한 이웃을 도우면 보름 뒤 30% 수익이 돌아온다며 500만 명을 홀린 1,000억 자선 제국 | 선신후이 사건",
        "winner_cluster": "Luồng 1 · Vỏ Bọc Từ Thiện Cuốn 5 Triệu Người Vào Ma Trận 104,6 Tỷ Tệ Chỉ Trong 14 Tháng (선신후이 장톈밍 사건)",
        "codex_score": 96,
        "profile_score": 96,
        "codex_angle": "Hồ Sơ Thật 100%: Trương Thiên Minh & Thiện Tâm Hội (善心汇1046亿案) — Thuật Toán Ghép Cặp 'Cho Đi - Nhận Lại' Trên Ứng Dụng Và Chiến Dịch Đột Kích Toàn Quốc Tháng 7/2017",
        "codex_reasons": [
            "Một trong những vụ án tài chính đa cấp lớn nhất lịch sử Trung Quốc (5,98 triệu tài khoản, dòng tiền 104,6 tỷ NDT chỉ trong hơn 1 năm), bản tin thời sự CCTV cực nhiều",
            "Bóc tách sắc lạnh toán học của vòng quay Ponzi 15 ngày lãi 30%"
        ],
        "opening_hook": "어려운 이웃에게 삼천 위안을 기부하면 열닷새 뒤 하늘이 복을 내려 삼천구백 위안으로 돌려준다는 '공생 경제 시스템'. 자선과 구제를 내세운 이 달콤한 설계에 불과 일 년 만에 오백구십팔만 명이 모여들었고, 무려 일천사십육억 위안이라는 돈이 스마트폰 화면 위에서 소용돌이쳤습니다.",
        "note": "【Hồ sơ vụ án: đại án tài chính đa cấp núp bóng quỹ từ thiện hút 104,6 tỷ tệ từ 5 triệu người chỉ trong 14 tháng】 Hồ sơ thật 100% Đại án Thiện Tâm Hội tại Thâm Quyến (深圳善心汇文化传播有限公司特大传销案 — Trương Thiên Minh 张天明, 5/2016–7/2017): Dưới khẩu hiệu 'Phù bần tế khốn, quân phú cộng sinh', lôi kéo 5,98 triệu người tham gia với tổng số tiền luân chuyển 104,6 tỷ NDT trước khi bị Bộ Công an triệt phá và Tòa án tỉnh Hồ Nam tuyên phạt Trương Thiên Minh 17 năm tù.",
        "hook_archetype": "double_life_unmasking"
    },
    {
        "id": "fin_cn_beijing_abc_39b_newspaper",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "北京农业银行39亿元银行承兑汇票调包变报纸大案 — 赵立军·张宇 (2016)",
        "archival_search_keywords_zh": [
            "农行39亿票据案 报纸 今日说法",
            "北京农行 39亿 承兑汇票 庭审",
            "农业银行 票据变报纸 央视新闻"
        ],
        "recommended_vox_verbs": [
            "SPLIT_PARADOX",
            "LEDGER_DIFF_SCRUB",
            "CRASH_TIMELINE"
        ],
        "title": "[중국 실화 사건] 은행 지하 금고 봉투 속 39억 위안 어음이 전부 옛날 신문지뭉치로 바뀌어 있었다 | 베이징 농협 어음 증발 사건 ([Vụ Án Có Thật ở Trung Quốc] 3,9 tỷ tệ hối phiếu trong phong bì két sắt ngân hàng biến thành xấp báo cũ | Đại án Hối phiếu Bắc Kinh)",
        "topic_anchor": "[중국 실화 사건] 은행 지하 금고 봉투 속 39억 위안 어음이 전부 옛날 신문지뭉치로 바뀌어 있었다 | 베이징 농협 어음 증발 사건",
        "winner_cluster": "Luồng 1 · 3,9 Tỷ Tệ Hối Phiếu Trong Két Sắt Ngân Hàng Biến Thành Giấy Báo Cũ (베이징 농업은행 39억 어음 사건)",
        "codex_score": 99,
        "profile_score": 99,
        "codex_angle": "Hồ Sơ Thật 100%: Đại Án 3,9 Tỷ NDT Ngân Hàng Nông Nghiệp Bắc Kinh (北京农行39亿票据变报纸案 — Triệu Lập Quân & Trương Vũ, 2016) — Đánh Tráo Hối Phiếu Thật Khỏi Phong Bì Niêm Phong Đẩy Lên Sàn Chứng Khoán",
        "codex_reasons": [
            "Nghịch lý thị giác đỉnh cao cho Bàn Biên Tập Vox: phong bì niêm phong trong két sắt ngân hàng quốc doanh khi rạch ra lại chỉ toàn báo cũ cắt đúng kích cỡ tờ hối phiếu",
            "Tư liệu bản tin tài chính CCTV và hồ sơ xét xử cực kỳ chi tiết"
        ],
        "opening_hook": "이중 잠금장치가 걸린 국유은행 금고 안, 삼십구억 위안어치의 은행 인수어음이 들어 있어야 할 밀봉 봉투가 열렸습니다. 하지만 감사관의 손끝에 잡힌 것은 빳빳한 유가증권이 아니라, 어음 크기에 맞춰 정교하게 오려 넣은 낡은 신문지 뭉치였습니다.",
        "note": "【Hồ sơ vụ án: đại án đánh tráo 3,9 tỷ tệ hối phiếu trong két sắt ngân hàng thành những xấp báo cũ để mang đi đầu tư chứng khoán】 Hồ sơ thật 100% Đại án 3,915 tỷ NDT tại Ngân hàng Nông nghiệp Trung Quốc chi nhánh Bắc Kinh (北京农行39亿票据大案 — Triệu Lập Quân 赵立军 & Trương Vũ 张宇, 2016): Hai nhân viên quản lý hối phiếu cấu kết với trung gian tài chính ở Trùng Khánh rút ruột toàn bộ hối phiếu thật trong két sắt đem đi chiết khấu lấy tiền炒 cổ phiếu, nhét giấy báo cắt sẵn vào phong bì niêm phong suốt nhiều tháng trước khi thị trường chứng khoán sập làm vỡ lở.",
        "hook_archetype": "locked_room_vault_paradox"
    },
    {
        "id": "fin_cn_zhan_engui_40_identities_cfo",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "跨省伪造40个身份应聘大型企业财务总监卷款1980万潜逃案 — 詹恩贵 (2006–2018)",
        "archival_search_keywords_zh": [
            "詹恩贵 财务总监 今日说法",
            "初中学历 冒充财务总监 詹恩贵 天网",
            "40个假身份 詹恩贵 庭审"
        ],
        "recommended_vox_verbs": [
            "DUAL_ERA_LOCK",
            "LEDGER_DIFF_SCRUB",
            "GEO_VECTOR_PURSUIT"
        ],
        "title": "[중국 실화 사건] 중학교 중퇴자가 가짜 신분증 40개로 대기업 재무이사가 되어 금고를 털다 | 잔언구이 위장 천재 사건 ([Vụ Án Có Thật ở Trung Quốc] Gã bỏ học cấp 2 dùng 40 chứng minh thư giả làm Giám đốc tài chính tập đoàn lớn rồi vét sạch két | Đại án Chiêm Ân Quý)",
        "topic_anchor": "[중국 실화 사건] 중학교 중퇴자가 가짜 신분증 40개로 대기업 재무이사가 되어 금고를 털다 | 잔언구이 위장 천재 사건",
        "winner_cluster": "Luồng 1 · 'Frank Abagnale Trung Quốc' Dùng 40 Danh Tính Giả Làm Giám Đốc Tài Chính 5 Tỉnh (잔언구이 40개 신분 사건)",
        "codex_score": 98,
        "profile_score": 98,
        "codex_angle": "Hồ Sơ Thật 100%: Chiêm Ân Quý (詹恩贵, 2006–2018) — Chỉ Học Hết Lớp 8 Nhưng Tự Học Kế Toán Thuế Cấp Cao, Vượt Qua Mọi Vòng Phỏng Vấn CFO Để Rút Ruột 19,8 Triệu NDT",
        "codex_reasons": [
            "Được CCTV 今日说法 phát sóng nhiều tập vì độ kịch tính y hệt phim 'Catch Me If You Can' phiên bản Trung Quốc",
            "Cơ chế tráo chữ ký số U-Key ngân hàng của chủ tịch tập đoàn ngay trong đêm giao thừa cực hợp LEDGER_DIFF_SCRUB"
        ],
        "opening_hook": "최종 학력은 중학교 이 학년 중퇴. 그러나 그는 회계사 자격증과 명문대 졸업장을 위조해 대기업 면접관들을 완벽히 속여 넘겼습니다. 12년 동안 무려 마흔 개의 가짜 이름을 갈아타며 다섯 개 대기업의 재무이사로 취업해 회사 금고를 통째로 비워버린 사나이, 잔언구이의 기막힌 행적을 추적합니다.",
        "note": "【Hồ sơ vụ án: đại án siêu lừa đảo IQ cao chỉ học hết cấp 2 nhưng làm giả 40 thân phận giám đốc tài chính (CFO) cuỗm gần 20 triệu tệ suốt 12 năm】 Hồ sơ thật 100% Chuyên án Chiêm Ân Quý (詹恩贵, Hồ Bắc, 2006–2018): Dù chỉ học hết lớp 8 nhưng tự nghiên cứu luật thuế và nghiệp vụ kế toán sâu đến mức vượt qua các buổi sát hạch tuyển Giám đốc tài chính (CFO) tại Thượng Hải, Nam Kinh, Vũ Hán, Quý Dương, dùng 40 CMND giả để nắm giữ U-Key ngân hàng và cuỗm tổng cộng hơn 19,8 triệu NDT trước khi bị bắt tại Quý Châu.",
        "hook_archetype": "last_ordinary_routine"
    },
    {
        "id": "fin_cn_shandong_qilu_bank_10b_seal",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "山东济南齐鲁银行101亿元伪造金融票证与假VIP审验室大案 — 刘乃胜 (2008–2010)",
        "archival_search_keywords_zh": [
            "齐鲁银行 101亿 刘乃胜 今日说法",
            "济南齐鲁银行 伪造金融票证 庭审",
            "刘乃胜 180枚假公章 纪实"
        ],
        "recommended_vox_verbs": [
            "SPLIT_PARADOX",
            "SINGLE_EVIDENCE_AUTOPSY",
            "SCALE_MULTIPLICATION"
        ],
        "title": "[중국 실화 사건] 은행 건물 안에 '가짜 VIP 상담실'을 만들어 감사관까지 속이고 101억 위안을 빼돌린 설계자 | 제루은행 류나이성 사건 ([Vụ Án Có Thật ở Trung Quốc] Dựng 'phòng VIP giả' ngay trong tòa nhà ngân hàng để lừa cả kiểm toán viên, rút ruột 10,1 tỷ tệ | Đại án Ngân hàng Tề Lỗ)",
        "topic_anchor": "[중국 실화 사건] 은행 건물 안에 '가짜 VIP 상담실'을 만들어 감사관까지 속이고 101억 위안 빼돌린 설계자 | 제루은행 류나이성 사건",
        "winner_cluster": "Luồng 1 · 180 Con Dấu Giả & 'Phòng Tiếp Đón Kiểm Toán Giả' Rút Ruột 10,1 Tỷ Tệ (산둥 제루은행 류나이성 사건)",
        "codex_score": 99,
        "profile_score": 99,
        "codex_angle": "Hồ Sơ Thật 100%: Lưu Nãi Thắng (刘乃胜 — Đại Án Ngân Hàng Tề Lỗ Tế Nam 10,1 Tỷ NDT) — Đặt Máy Chặn Sóng Điện Thoại & Thuê Diễn Viên Đóng Giả Nhân Viên Ngân Hàng Tiếp Kiểm Toán Viên",
        "codex_reasons": [
            "Một trong những kịch bản lừa đảo kiểm toán ngân hàng táo tợn nhất thế giới: khi doanh nghiệp cử kiểm toán viên đến ngân hàng xác minh số dư, Lưu Nãi Thắng đón ngay ở sảnh dẫn vào căn phòng thuê sẵn trong cùng tòa nhà",
            "Quy mô 10,1 tỷ NDT (~1.900 tỷ Won), 180 con dấu ngân hàng khắc giả bị thu giữ"
        ],
        "opening_hook": "기업 감사관이 예금 잔액 십억 위안을 직접 확인하러 은행 본점 로비에 들어섰습니다. 친절하게 마중 나온 직원의 안내를 받아 올라간 이층 VIP 회의실에서 잔액 증명서에 도장까지 직접 찍어주었지만, 사실 그 방은 은행 사무실이 아니라 사기범 류나이성이 같은 건물에 몰래 빌려 꾸며놓은 가짜 세트장이었습니다.",
        "note": "【Hồ sơ vụ án: đại án dựng phòng thẩm định VIP giả ngay trong tòa nhà ngân hàng để lừa 10,1 tỷ tệ bằng chứng chỉ tiền gửi giả】 Hồ sơ thật 100% Đại án Ngân hàng Tề Lỗ tại Tế Nam, Sơn Đông (山东济南齐鲁银行101亿伪造金融票证案 — Lưu Nãi Thắng 刘乃胜, 2008–2010): Khắc 180 con dấu giả, cấu kết nhân viên ngân hàng lập phòng tiếp khách giả ngay trong tòa nhà để đánh tráo giấy xác nhận số dư của hàng chục tập đoàn lớn, rút ruột 10,1 tỷ NDT trước khi lĩnh án tù chung thân.",
        "hook_archetype": "locked_room_vault_paradox"
    },
    {
        "id": "fin_cn_qingdao_port_aluminium_16b",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "山东青岛港德正资源160亿元铝锭一货十押重复质押骗贷案 — 陈基鸿 (2014)",
        "archival_search_keywords_zh": [
            "青岛港 160亿 铝锭 骗贷 央视",
            "德正资源 陈基鸿 青岛港 纪实",
            "青岛港 仓单质押 诈骗案"
        ],
        "recommended_vox_verbs": [
            "SCALE_MULTIPLICATION",
            "SPLIT_PARADOX",
            "LEDGER_DIFF_SCRUB"
        ],
        "title": "[중국 실화 사건] 항구 창고 속 알루미늄 한 더미로 18개 은행에서 160억 위안을 대출받은 '그림자 창고' 마술 | 칭다오항 첸지훙 사건 ([Vụ Án Có Thật ở Trung Quốc] Một đống nhôm trong kho cảng thế chấp 18 ngân hàng rút 16 tỷ tệ bằng ma thuật 'kho bóng ma' | Đại án Cảng Thanh Đảo)",
        "topic_anchor": "[중국 실화 사건] 항구 창고 속 알루미늄 한 더미로 18개 은행에서 160억 위안을 대출받은 '그림자 창고' 마술 | 칭다오항 첸지훙 사건",
        "winner_cluster": "Luồng 1 · 1 Lô Kim Loại Cảng Biển Nhân Bản 10 Tờ Chứng Nhận Kho Rút 16 Tỷ Tệ (칭다오항 알루미늄 중복 담보 사건)",
        "codex_score": 97,
        "profile_score": 97,
        "codex_angle": "Hồ Sơ Thật 100%: Trần Cơ Hồng & Đại Án Kim Loại Cảng Thanh Đảo 16 Tỷ NDT (山东青岛港德正资源骗贷案, 2014) — Xếp Thùng Rỗng Ở Giữa, Chất Nhôm Thật Xung Quanh Để Lừa 18 Đoàn Kiểm Tra Ngân Hàng",
        "codex_reasons": [
            "Chấn động thị trường kim loại London (LME) và hệ thống ngân hàng quốc tế năm 2014, tư liệu cảng Thanh Đảo niêm phong kho bãi cực kỳ ấn tượng",
            "Minh họa 2.5D mặt cắt kho nhôm rỗng ruột cực hợp cho Bàn Biên Tập Vox"
        ],
        "opening_hook": "수만 톤의 알루미늄과 구리 괴가 산처럼 쌓여 있는 칭다오항 보세창고. 열여덟 개 국내외 은행 실사단은 직접 눈으로 금속 더미를 확인하고 무려 백육십억 위안을 빌려주었습니다. 그러나 항구가 봉쇄되고 지게차가 금속 벽을 허물자, 그 안쪽은 텅 빈 공간이었고 똑같은 금속 한 더미에 열 장의 가짜 창고 증권이 붙어 있었습니다.",
        "note": "【Hồ sơ vụ án: đại án dùng 1 lô nhôm thỏi trong kho cảng thế chấp trùng lặp 10 lần để rút ruột 16 tỷ tệ vốn vay ngân hàng quốc tế】 Hồ sơ thật 100% Đại án lừa đảo tín dụng kho cảng Thanh Đảo, Sơn Đông (山东青岛港德正资源160亿元重复质押骗贷案 — Trần Cơ Hồng 陈基鸿, 2014): Dùng một lượng nhỏ nhôm và đồng thật xếp thành tường bao quanh khoảng trống, kết hợp làm giả vận đơn kho cảng để thế chấp lặp lại cho 18 ngân hàng trong và ngoài nước, chiếm đoạt hơn 16 tỷ NDT.",
        "hook_archetype": "double_life_unmasking"
    },
    {
        "id": "fin_cn_minsheng_zhangying_30b_vip",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "北京民生银行航天桥支行30亿元假理财飞单掏空VIP储户案 — 张颖 (2013–2017)",
        "archival_search_keywords_zh": [
            "民生银行 航天桥支行 张颖 30亿",
            "北京民生银行 30亿 假理财 今日说法",
            "张颖 航天桥 庭审 央视"
        ],
        "recommended_vox_verbs": [
            "LEDGER_DIFF_SCRUB",
            "CRASH_TIMELINE",
            "NETWORK_GRAPH"
        ],
        "title": "[중국 실화 사건] 은행 VIP 라운지에서 판 30억 위안 특판 상품이 본점 전산망에는 아예 없었던 이유 | 베이징 장잉 두 장부 사건 ([Vụ Án Có Thật ở Trung Quốc] Lý do gói tiết kiệm VIP 3 tỷ tệ bán ngay tại phòng khách ngân hàng lại hoàn toàn không có trên hệ thống tổng | Đại án Trương Dĩnh Bắc Kinh)",
        "topic_anchor": "[중국 실화 사건] 은행 VIP 라운지에서 판 30억 위안 특판 상품이 본점 전산망에는 아예 없었던 이유 | 베이징 장잉 두 장부 사건",
        "winner_cluster": "Luồng 1 · Nữ Giám Đốc Chi Nhánh Ngôi Sao Tự Bịa 'Gói Lãi Suất Ngầm' Rút 3 Tỷ Tệ Của 150 Đại Gia (베이징 항톈차오 지점 장잉 사건)",
        "codex_score": 97,
        "profile_score": 97,
        "codex_angle": "Hồ Sơ Thật 100%: Trương Dĩnh — Giám Đốc Chi Nhánh Hàng Thiên Kiều Bắc Kinh (北京民生银行航天桥支行30亿案) — Dùng Hợp Đồng Chuyển Nhượng Giả Để Lấp Lỗ Hổng 3 Tỷ NDT",
        "codex_reasons": [
            "Đại án chi nhánh ngân hàng lớn nhất thủ đô Bắc Kinh năm 2017, cực nhiều tư liệu bản tin tài chính CCTV và phiên tòa xét xử",
            "Góc nhìn giải phẫu chứng từ hợp đồng thật - giả ngay trong phòng VIP ngân hàng"
        ],
        "opening_hook": "통장 잔고가 최소 천만 위안 이상인 최상위 자산가 백오십 명만 초청된 은행 지점장실. 전국 실적 일 등을 자랑하던 스타 지점장 장잉은 급히 현금이 필요한 고객의 정기예금을 반값에 인수하는 비밀 특판 상품을 내놓았습니다. 하지만 삼십억 위안이 모인 뒤 드러난 진실은, 그런 상품은 은행 역사상 단 한 번도 존재한 적이 없다는 것이었습니다.",
        "note": "【Hồ sơ vụ án: đại án nữ giám đốc chi nhánh ngân hàng làm giả hợp đồng đầu tư VIP rút ruột 3 tỷ tệ của 150 khách hàng siêu giàu】 Hồ sơ thật 100% Đại án Ngân hàng Dân Sinh chi nhánh Hàng Thiên Kiều, Bắc Kinh (北京民生银行航天桥支行30亿元假理财案 — Giám đốc chi nhánh Trương Dĩnh 张颖, 2013–2017): Để lấp lỗ hổng tài khoản cá nhân, Trương Dĩnh khắc con dấu giả lập các hợp đồng理财 lãi suất 8,4%/năm lừa hơn 150 khách hàng VIP tại phòng giám đốc, chiếm đoạt hơn 3 tỷ NDT trước khi lĩnh án chung thân.",
        "hook_archetype": "locked_room_vault_paradox"
    },
    {
        "id": "fin_cn_guangxi_liuzhou_bank_32b",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "广西柳州银行328亿元伪造土地证空壳公司骗贷大案 — 吴东家族 (2010–2014)",
        "archival_search_keywords_zh": [
            "广西柳州银行 吴东 328亿 今日说法",
            "柳州银行 骗贷大案 央视新闻",
            "吴东家族 假土地证 庭审"
        ],
        "recommended_vox_verbs": [
            "SCALE_MULTIPLICATION",
            "NETWORK_GRAPH",
            "LEDGER_DIFF_SCRUB"
        ],
        "title": "[중국 실화 사건] 유령 회사 40개와 가짜 토지문서로 도시 은행을 통째로 자기 지갑처럼 쓴 일가족 | 류저우은행 328억 위안 사건 ([Vụ Án Có Thật ở Trung Quốc] Dùng 40 công ty ma và sổ đỏ giả biến cả ngân hàng thành ví tiền riêng của gia tộc | Đại án 32,8 tỷ tệ Ngân hàng Liễu Châu)",
        "topic_anchor": "[중국 실화 사건] 유령 회사 40개와 가짜 토지문서로 도시 은행을 통째로 자기 지갑처럼 쓴 일가족 | 류저우은행 328억 위안 사건",
        "winner_cluster": "Luồng 1 · 40 Công Ty Ma & Sổ Đỏ Phóng Đại Giá Trị Gấp 30 Lần Rút 32,8 Tỷ Tệ Ngân Hàng (류저우은행 우둥 일가 사건)",
        "codex_score": 97,
        "profile_score": 97,
        "codex_angle": "Hồ Sơ Thật 100%: Gia Tộc Ngô Đông & Đại Án 32,8 Tỷ NDT Ngân Hàng Liễu Châu (广西柳州银行328亿骗贷案) — Cách Một Khu Đất Hoang Được Phù Phép Trên Giấy Thành Tài Sản Đảm Bảo Hàng Chục Tỷ Tệ",
        "codex_reasons": [
            "Một trong những vụ án rút ruột tín dụng ngân hàng địa phương lớn nhất Trung Quốc (250 khoản vay trị giá 32,8 tỷ NDT), phóng sự điều tra CCTV cực kỳ chi tiết",
            "Khớp hoàn hảo sơ đồ mạng lưới công ty vỏ bọc NETWORK_GRAPH & SCALE_MULTIPLICATION"
        ],
        "opening_hook": "풀만 무성하게 자란 변두리 빈 땅 한 조각이 서류 위에서는 수십억 위안짜리 황금 부지로 둔갑했습니다. 광시성 류저우시에서 우둥 일가는 마흔 개가 넘는 유령 회사와 가짜 토지 등기부를 동원해 단 사 년 만에 은행에서 삼백이십팔억 위안을 끌어다 썼습니다.",
        "note": "【Hồ sơ vụ án: đại án gia tộc lập 40 công ty vỏ bọc và sổ đỏ giả để rút ruột 32,8 tỷ tệ vốn vay từ ngân hàng địa phương】 Hồ sơ thật 100% Đại án lừa đảo tín dụng 32,8 tỷ NDT tại Ngân hàng Liễu Châu, Quảng Tây (广西柳州银行328亿元骗贷案 — Gia tộc Ngô Đông 吴东, 2010–2014): Lập hơn 40 công ty vỏ bọc, làm giả sổ đỏ và báo cáo thẩm định giá đất tăng gấp hàng chục lần để vay 250 khoản tín dụng tổng cộng 32,895 tỷ NDT.",
        "hook_archetype": "last_ordinary_routine"
    },
    {
        "id": "fin_cn_foshan_nanhai_74b_fengmingchang",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "广东佛山南海华光集团74亿元虚构贸易掏空银行与国库大案 — 冯明昌 (1996–2003)",
        "archival_search_keywords_zh": [
            "佛山南海 冯明昌 74亿 央视",
            "南海华光 74亿骗贷案 今日说法",
            "广东佛山 74亿金融大案 纪实"
        ],
        "recommended_vox_verbs": [
            "NETWORK_GRAPH",
            "LEDGER_DIFF_SCRUB",
            "CRASH_TIMELINE"
        ],
        "title": "[중국 실화 사건] 자기 혼자 만든 13개 자회사끼리 가짜 영수증을 돌리며 은행 돈 74억 위안을 삼킨 사나이 | 포산 펑밍창 사건 ([Vụ Án Có Thật ở Trung Quốc] Tự lập 13 công ty con xuất hóa đơn lòng vòng cho nhau để nuốt 7,4 tỷ tệ ngân hàng | Đại án Phùng Minh Xương Phật Sơn)",
        "topic_anchor": "[중국 실화 사건] 자기 혼자 만든 13개 자회사끼리 가짜 영수증을 돌리며 은행 돈 74억 위안을 삼킨 사나이 | 포산 펑밍창 사건",
        "winner_cluster": "Luồng 1 · Ma Trận 13 Công Ty Tự Mua Bán Khống Rút 7,4 Tỷ Tệ Kho Bạc & Ngân Hàng (포산 펑밍창 74억 위안 사건)",
        "codex_score": 96,
        "profile_score": 96,
        "codex_angle": "Hồ Sơ Thật 100%: Phùng Minh Xương & Tập Đoàn Hoa Quang Nam Hải (广东佛山74亿大案) — Bóc Tách Mạng Lưới Bảo Lãnh Chéo 13 Công Ty Vỏ Bọc Khiến Kho Bạc Địa Phương Suýt Vỡ Trận",
        "codex_reasons": [
            "Đại án kiểm toán lịch sử của Kiểm toán Nhà nước Trung Quốc (审计署) công bố trên CCTV với đầy đủ sơ đồ dòng tiền và phiên tòa Phật Sơn",
            "100% Xanh tiền: tập trung vào kỹ thuật kiểm toán truy vết dòng tiền vòng tròn"
        ],
        "opening_hook": "물건은 단 한 상자도 오가지 않았지만, 열세 개의 회사 사이에서는 매일 수억 위안짜리 세금계산서와 무역 계약서가 쉴 새 없이 돌아갔습니다. 국가 감사원이 광둥성 포산의 한 기업 장부를 열었을 때, 그 열세 개 회사의 진짜 주인은 단 한 사람, 펑밍창뿐이었고 은행 금고에서는 칠십사억 위안이 빠져나간 뒤였습니다.",
        "note": "【Hồ sơ vụ án: đại án dùng 13 công ty ma ký hợp đồng thương mại khống rút ruột 7,45 tỷ tệ ngân hàng và kho bạc nhà nước】 Hồ sơ thật 100% Đại án Tập đoàn Hoa Quang tại Nam Hải, Phật Sơn, Quảng Đông (广东佛山南海冯明昌74亿元特大金融案, 1996–2003): Phùng Minh Xương lập 13 công ty con đóng giả đối tác thương mại bảo lãnh chéo lẫn nhau để rút 7,45 tỷ NDT từ ngân hàng và kho bạc địa phương trước khi bị Tổng Kiểm toán Nhà nước phanh phui.",
        "hook_archetype": "locked_room_vault_paradox"
    },
    {
        "id": "fin_cn_dongguan_tuandai_tangjun_145b",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "广东东莞团贷网1450亿元非法集资崩盘与天价午餐造势案 — 唐军·张林 (2012–2019)",
        "archival_search_keywords_zh": [
            "东莞团贷网 唐军 1450亿 央视新闻",
            "团贷网 庭审 巴菲特午餐 纪实",
            "广东东莞 唐军 集资诈骗案"
        ],
        "recommended_vox_verbs": [
            "SCALE_MULTIPLICATION",
            "CRASH_TIMELINE",
            "ROLLING_METRIC_SHOCK"
        ],
        "title": "[중국 실화 사건] 월스트리트 전설과의 점심 한 끼에 1,500만 위안을 써 대중을 홀린 1,450억 사기극 | 퇀다이왕 탕쥔 사건 ([Vụ Án Có Thật ở Trung Quốc] Chi 15 triệu tệ ăn trưa cùng huyền thoại Phố Wall để lấy lòng tin rồi nuốt 145 tỷ tệ | Đại án Đoàn Đại Võng Đường Quân)",
        "topic_anchor": "[중국 실화 사건] 월스트리트 전설과의 점심 한 끼에 1,500만 위안을 써 대중을 홀린 1,450억 사기극 | 퇀다이왕 탕쥔 사건",
        "winner_cluster": "Luồng 1 · Dùng Bữa Trưa Triệu Đô Đánh Bóng Tên Tuổi Để Hút 145 Tỷ Tệ Tín Dụng (둥관 퇀다이왕 탕쥔 사건)",
        "codex_score": 97,
        "profile_score": 97,
        "codex_angle": "Hồ Sơ Thật 100%: Đường Quân & Đoàn Đại Võng Đông Quản (东莞团贷网1450亿案) — Đòn Bẩy Truyền Thông Từ Bức Ảnh Chụp Cùng Tỷ Phú Thế Giới Đến Đêm 28/3/2019 Phong Tỏa Toàn Bộ Tòa Tháp Tài Chính",
        "codex_reasons": [
            "Đại án tài chính công nghệ 145 tỷ NDT chấn động tỉnh Quảng Đông năm 2019–2022, tư liệu cảnh sát Đông Quản phong tỏa trụ sở và thu giữ 5,6 tỷ tệ tiền mặt/tài sản cực rõ nét",
            "Bóc tách tâm lý học thao túng niềm tin đám đông bằng 'hiệu ứng hào quang người nổi tiếng'"
        ],
        "opening_hook": "스물다섯 살의 무명 창업자가 세계적인 투자의 귀재와 점심 식사 한 끼를 함께하기 위해 일천오백만 위안을 경매에 던졌습니다. 단 한 장의 기념사진이 신문 일면을 장식하자, 대중은 그를 금융 천재로 믿고 무려 일천사백오십억 위안의 자금을 맡겼습니다. 하지만 그 화려한 사진 뒤에는 거대한 가짜 대출 풀(Pool)이 숨겨져 있었습니다.",
        "note": "【Hồ sơ vụ án: đại án bỏ 2,13 triệu tệ đấu giá bữa trưa với tỷ phú để đánh bóng tên tuổi rồi huy động trái phép 145 tỷ tệ】 Hồ sơ thật 100% Đại án Đoàn Đại Võng tại Đông Quản, Quảng Đông (广东东莞团贷网1450亿元集资诈骗案 — Đường Quân 唐军 & Trương Lâm 张林, 2012–2019): Đường Quân bỏ 2,13 triệu USD đấu giá bữa ăn trưa với Warren Buffett năm 2012 để tạo hào quang uy tín, sau đó phát hành hàng vạn gói tín dụng khống thu hút 145 tỷ NDT trước khi sụp đổ tháng 3/2019 (Đường Quân lĩnh án 20 năm tù năm 2022).",
        "hook_archetype": "chilling_verbatim_line"
    },
    {
        "id": "fin_cn_guangdong_jianlibao_zhanghai_700m",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "广东健力宝集团7亿元空手套白狼掏空与假立功减刑潜逃欧洲案 — 张海 (2002–2014)",
        "archival_search_keywords_zh": [
            "健力宝 张海 假立功 外逃 今日说法",
            "张海 掏空健力宝 7亿 央视",
            "广东张海 跨国追逃 纪实"
        ],
        "recommended_vox_verbs": [
            "LEDGER_DIFF_SCRUB",
            "CAUSAL_CHAIN",
            "GEO_VECTOR_PURSUIT"
        ],
        "title": "[중국 실화 사건] 자기 돈 한 푼 없이 국민 음료 대기업을 인수해 금고 돈으로 인수대금을 갚고 유럽으로 탈출한 자본 마술사 | 장하이 사건 ([Vụ Án Có Thật ở Trung Quốc] Tay không mua đứt tập đoàn đồ uống quốc dân, lấy chính tiền trong két công ty trả tiền mua rồi trốn sang châu Âu | Đại án Trương Hải)",
        "topic_anchor": "[중국 실화 사건] 자기 돈 한 푼 없이 국민 음료 대기업을 인수해 금고 돈으로 인수대금을 갚고 유럽으로 탈출한 자본 마술사 | 장하이 사건",
        "winner_cluster": "Luồng 1 · 'Tay Không Bắt Giặc' Mua Tập Đoàn Quốc Dân Bằng Tiền Của Chính Tập Đoàn & Đào Tẩu Châu Âu (젠리바오 장하이 사건)",
        "codex_score": 96,
        "profile_score": 96,
        "codex_angle": "Hồ Sơ Thật 100%: Trương Hải & Đại Án Tập Đoàn Kiện Lực Bảo (广东健力宝张海案, 2002–2014) — Màn Ảo Thuật Kế Toán 700 Triệu NDT Và Phi Vụ Mua 'Bằng Sáng Chế Giả' Trong Tù Để Ra Tù Sớm Rồi Trốn Sang Châu Âu",
        "codex_reasons": [
            "Vụ án kinh điển bậc nhất trong giáo trình luật tài chính & hình sự Trung Quốc, tư liệu CCTV cực kỳ đầy đủ",
            "Hai tầng twist liên hoàn: (1) dùng tiền mặt trong két công ty vừa mua để trả tiền mua chính công ty đó; (2) khi vào tù lại mua manh mối/bằng sáng chế giả để giảm án từ 15 năm xuống 6 năm rồi trốn sang Pháp"
        ],
        "opening_hook": "수중에 현금 한 푼 없던 스물여덟 살 청년이 삼억삼천팔백만 위안짜리 국민 음료 대기업의 새 주인이 되었습니다. 비밀은 간단했습니다. 계약서에 도장을 찍자마자 그 회사의 금고를 열어 인수 대금을 메운 것입니다. 심지어 감옥에 갇힌 뒤에는 가짜 발명 특허로 형량을 줄여 유럽으로 유유히 사라졌습니다.",
        "note": "【Hồ sơ vụ án: đại án tay không thâu tóm và rút ruột 700 triệu tệ của tập đoàn nước giải khát quốc gia · làm giả hồ sơ lập công để giảm án rồi trốn sang châu Âu】 Hồ sơ thật 100% Đại án Trương Hải tại Tập đoàn Kiện Lực Bảo, Phật Sơn, Quảng Đông (广东健力宝张海职务侵占与假立功外逃案, 2002–2014): Dùng thủ đoạn kế toán rút ruột hơn 700 triệu NDT của Kiện Lực Bảo; sau khi bị tuyên 15 năm tù năm 2007, người tình và luật sư đã làm giả hồ sơ lập công trong tù giúp Trương Hải ra tù sớm năm 2011 rồi dùng hộ chiếu giả trốn sang châu Âu.",
        "hook_archetype": "locked_room_vault_paradox"
    },
    {
        "id": "fin_cn_shanghai_fuxing_zhuyidong_36b",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "上海阜兴集团365亿元私募基金空壳挪用与操纵股价潜逃海外案 — 朱一栋 (2014–2018)",
        "archival_search_keywords_zh": [
            "上海阜兴集团 朱一栋 365亿 央视新闻",
            "朱一栋 操纵证券市场 庭审 今日说法",
            "阜兴集团 押解回国 纪实"
        ],
        "recommended_vox_verbs": [
            "CRASH_TIMELINE",
            "ROLLING_METRIC_SHOCK",
            "GEO_VECTOR_PURSUIT"
        ],
        "title": "[중국 실화 사건] 160개 사모펀드로 모은 365억 위안으로 자기 회사 주가를 3배 띄우고 야반도주한 재벌 2세 | 상하이 주이둥 사건 ([Vụ Án Có Thật ở Trung Quốc] Dùng 36,5 tỷ tệ của 160 quỹ đầu tư để thổi giá cổ phiếu công ty mình gấp 3 lần rồi bỏ trốn | Đại án Chu Nhất Đống Thượng Hải)",
        "topic_anchor": "[중국 실화 사건] 160개 사모펀드로 모은 365억 위안으로 자기 회사 주가를 3배 띄우고 야반도주한 재벌 2세 | 상하이 주이둥 사건",
        "winner_cluster": "Luồng 1 · 160 Quỹ Đầu Tư Tư Nhân 36,5 Tỷ Tệ & Màn Thao Túng Sàn Chứng Khoán Thượng Hải (상하이 푸싱그룹 주이둥 사건)",
        "codex_score": 97,
        "profile_score": 97,
        "codex_angle": "Hồ Sơ Thật 100%: Chu Nhất Đống & Tập Đoàn Phụ Hưng Thượng Hải (上海阜兴集团365亿案, 2018) — Thuê 'Đội Lái' Dùng 400 Tài Khoản Chứng Khoán Đẩy Giá Cổ Phiếu Đại Liên Điện Từ & Cuộc Truy Bắt Qua 5 Quốc Gia",
        "codex_reasons": [
            "Đại án quỹ đầu tư tư nhân (Private Equity) và thao túng chứng khoán lớn nhất Thượng Hải năm 2018, video CCTV cảnh sát dẫn độ Chu Nhất Đống về Thượng Hải cực nét",
            "Khớp hoàn hảo CRASH_TIMELINE & ROLLING_METRIC_SHOCK"
        ],
        "opening_hook": "상하이 중심가 최고급 빌딩에 자리 잡은 푸싱그룹. 젊은 회장 주이둥은 백육십 개의 사모펀드 상품으로 삼백육십오억 위안을 끌어모았습니다. 그러나 그 거액의 투자금이 향한 곳은 실물 경제가 아니라, 사백 개의 차명 계좌로 자기 회사 주식을 사고팔며 주가를 조작하는 비밀 작전실이었습니다.",
        "note": "【Hồ sơ vụ án: đại án thiếu gia tài chính lập 100 quỹ đầu tư ma rút ruột 36,5 tỷ tệ và thao túng giá cổ phiếu · truy bắt xuyên 5 quốc gia】 Hồ sơ thật 100% Đại án Tập đoàn Phụ Hưng tại Thượng Hải (上海阜兴集团365亿元集资诈骗与操纵证券市场案 — Chu Nhất Đống 朱一栋, 2014–2018): Huy động 36,5 tỷ NDT qua 160 quỹ đầu tư tư nhân, dùng hàng trăm tài khoản ẩn danh thao túng cổ phiếu Dalian Insulator trước khi vỡ trận tháng 6/2018; Chu Nhất Đống đào tẩu qua 5 quốc gia với 11 hộ chiếu giả trước khi bị bắt dẫn độ về Thượng Hải và lĩnh án chung thân năm 2021.",
        "hook_archetype": "last_ordinary_routine"
    },
    {
        "id": "fin_cn_ningxia_baota_47b_bills",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "宁夏宝塔石化集团470亿元空头财务公司承兑汇票惊天骗局 — 孙珩超 (2015–2018)",
        "archival_search_keywords_zh": [
            "宁夏宝塔石化 孙珩超 470亿 票据",
            "宝塔石化 财务公司 承兑汇票 庭审",
            "孙珩超 票据诈骗 央视"
        ],
        "recommended_vox_verbs": [
            "SCALE_MULTIPLICATION",
            "LEDGER_DIFF_SCRUB",
            "CRASH_TIMELINE"
        ],
        "title": "[중국 실화 사건] 금고에 현금은 없는데 자체 금융회사 도장으로 470억 위안짜리 어음을 찍어낸 대기업 회장 | 바오타석화 쑨헝차오 사건 ([Vụ Án Có Thật ở Trung Quốc] Két sắt rỗng không nhưng dùng con dấu công ty tài chính nội bộ in ra 47 tỷ tệ hối phiếu | Đại án Bảo Tháp Tôn Hành Siêu)",
        "topic_anchor": "[중국 실화 사건] 금고에 현금은 없는데 자체 금융회사 도장으로 470억 위안짜리 어음을 찍어낸 대기업 회장 | 바오타석화 쑨헝차오 사건",
        "winner_cluster": "Luồng 1 · Biến Công Ty Tài Chính Nội Bộ Thành 'Máy In Hối Phiếu Khống' 47 Tỷ Tệ (닝샤 바오타석화 쑨헝차오 사건)",
        "codex_score": 96,
        "profile_score": 96,
        "codex_angle": "Hồ Sơ Thật 100%: Tôn Hành Siêu & Đại Án 47 Tỷ NDT Tập Đoàn Hóa Dầu Bảo Tháp Ninh Hạ (宁夏宝塔石化470亿票据案) — Khi 27.000 Tờ Hối Phiếu Điện Tử Không Tiền Bảo Chứng Đáo Hạn Cùng Một Lúc",
        "codex_reasons": [
            "Đại án hối phiếu doanh nghiệp lớn nhất vùng Tây Bắc Trung Quốc (27.000 tờ hối phiếu trị giá 47 tỷ NDT), hồ sơ xét xử và bản tin tài chính cực đầy đủ",
            "Cơ chế đòn bẩy giấy nợ không tài sản đảm bảo cực hợp với SCALE_MULTIPLICATION"
        ],
        "opening_hook": "만약 일반 기업이 은행처럼 스스로 어음을 발행할 수 있는 금융 자회사를 갖게 된다면 어떤 일이 벌어질까요. 닝샤성 최대 민영 석유화학 그룹의 회장 쑨헝차오는 지불 준비금도 없이 무려 이만칠천 장, 사백칠십억 위안어치의 전자 어음을 시장에 찍어냈습니다.",
        "note": "【Hồ sơ vụ án: đại án tập đoàn hóa dầu tự in 47 tỷ tệ hối phiếu ngân hàng không tiền bảo chứng để vay nợ dây chuyền khắp toàn quốc】 Hồ sơ thật 100% Đại án Tập đoàn Hóa dầu Bảo Tháp tại Ngân Xuyên, Ninh Hạ (宁夏宝塔石化集团470亿元票据诈骗案 — Tôn Hành Siêu 孙珩超, 2015–2018): Lợi dụng giấy phép Công ty Tài chính Tập đoàn để phát hành khống hơn 27.000 hối phiếu điện tử trị giá 47 tỷ NDT không có giao dịch thương mại thật để đảo nợ trước khi sụp đổ năm 2018 (Tôn Hành Siêu lĩnh án chung thân).",
        "hook_archetype": "double_life_unmasking"
    },
    {
        "id": "fin_cn_shenzhen_chengcheng_8b_fake_bank",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "深圳诚成集团跨省收购农信社伪造商业银行批文骗取80亿元案 — 刘波 (2013–2018)",
        "archival_search_keywords_zh": [
            "深圳诚成集团 刘波 假银行 80亿",
            "吉林农信社 假冒商业银行 今日说法",
            "刘波 80亿 金融诈骗 纪实"
        ],
        "recommended_vox_verbs": [
            "SPLIT_PARADOX",
            "GEO_VECTOR_PURSUIT",
            "LEDGER_DIFF_SCRUB"
        ],
        "title": "[중국 실화 사건] 시골 작은 신용협동조합 간판을 '전국 상업은행'으로 바꿔 달고 80억 위안을 끌어모은 사기극 | 선전 류보 가짜 은행 사건 ([Vụ Án Có Thật ở Trung Quốc] Thay biển hiệu hợp tác xã tín dụng quê thành 'Ngân hàng Thương mại Toàn quốc' để hút 8 tỷ tệ | Đại án Lưu Ba Thâm Quyến)",
        "topic_anchor": "[중국 실화 사건] 시골 작은 신용협동조합 간판을 '전국 상업은행'으로 바꿔 달고 80억 위안을 끌어모은 사기극 | 선전 류보 가짜 은행 사건",
        "winner_cluster": "Luồng 1 · Phù Phép Hợp Tác Xã Nhỏ Ở Cát Lâm Thành 'Ngân Hàng Thương Mại' Rút 8 Tỷ Tệ (선전 청청그룹 류보 사건)",
        "codex_score": 96,
        "profile_score": 96,
        "codex_angle": "Hồ Sơ Thật 100%: Lưu Ba & Tập Đoàn Thành Thành Thâm Quyến (深圳诚成集团80亿假银行案) — Làm Giả Công Văn Ngân Hàng Trung Ương Phê Duyệt Nâng Cấp Lên Ngân Hàng Thương Mại",
        "codex_reasons": [
            "Thủ đoạn tinh vi vượt bậc: không chỉ dựng quầy giả mà mua cổ phần một hợp tác xã tín dụng nhỏ ở vùng sâu Cát Lâm rồi làm giả quyết định của Ủy ban Giám sát Ngân hàng để huy động 8 tỷ NDT ở Thâm Quyến",
            "Tư liệu điều tra kinh tế (经侦) và bản tin CCTV cực kỳ rõ ràng"
        ],
        "opening_hook": "북쪽 끝 시골 마을의 자그마한 농촌신용사 하나를 인수한 뒤, 감독 기관의 가짜 승인 공문 한 장을 만들어 전국구 상업은행으로 둔갑시켰습니다. 선전과 베이징의 기업가들은 은행 코드까지 조회되는 이 정교한 속임수에 속아 팔십억 위안이 넘는 자금을 예치했습니다.",
        "note": "【Hồ sơ vụ án: đại án làm giả công văn phê duyệt của cơ quan quản lý để biến quỹ tín dụng nhỏ thành 'ngân hàng thương mại' lừa 8 tỷ tệ】 Hồ sơ thật 100% Đại án Tập đoàn Thành Thành tại Thâm Quyến & Cát Lâm (深圳诚成集团刘波80亿元特大金融诈骗案, 2013–2018): Lưu Ba mua lại một hợp tác xã tín dụng nhỏ tại Bạch Sơn (Cát Lâm), làm giả批文 của Ngân监会 cho phép nâng cấp thành Ngân hàng Thương mại Cổ phần, mở văn phòng giả ở Thâm Quyến để hút более 8 tỷ NDT trước khi bị triệt phá.",
        "hook_archetype": "micro_forensic_anomaly"
    },
    {
        "id": "fin_cn_beijing_jinsong_vault_18y_lu",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "北京中国银行劲松支行金库195万元现金调包潜逃18年案 — 陆某荣 (1997–2015)",
        "archival_search_keywords_zh": [
            "北京劲松支行 金库 18年 天网",
            "银行金库 195万 潜逃18年 今日说法",
            "劲松支行 陆某 抓捕纪实"
        ],
        "recommended_vox_verbs": [
            "BLIND_SPOT_REVEAL",
            "DUAL_ERA_LOCK",
            "GEO_VECTOR_PURSUIT"
        ],
        "title": "[중국 실화 사건] 열쇠 구멍에 흠집 하나 없이 은행 금고를 비우고 18년간 호적도 없이 살아온 내부자 | 베이징 진쑹 금고 사건 ([Vụ Án Có Thật ở Trung Quốc] Kẻ nội gián vét sạch két sắt ngân hàng không một vết xước ổ khóa rồi sống 18 năm không hộ khẩu | Chuyên án két sắt Kính Tùng Bắc Kinh)",
        "topic_anchor": "[중국 실화 사건] 열쇠 구멍에 흠집 하나 없이 은행 금고를 비우고 18년간 호적도 없이 살아온 내부자 | 베이징 진쑹 금고 사건",
        "winner_cluster": "Luồng 1 · Két Sắt Ngân Hàng Mở Khóa Không Vết Xước & 18 Năm Trốn Truy Nã Kinh Tế (베이징 진쑹 지점 금고 사건)",
        "codex_score": 95,
        "profile_score": 95,
        "codex_angle": "Hồ Sơ Thật 100%: Vụ Án Két Sắt Chi Nhánh Kính Tùng Bắc Kinh 18 Năm (北京中行劲松支行金库案, 1997–2015) — Lợi Dụng Khoảnh Khắc Bàn Giao Ca Trực Kho Bạc & 18 Năm Đóng Giả Thợ Sửa Nước Ở Giang Tây",
        "codex_reasons": [
            "Phóng sự chuyên đề trên CCTV 天网 & 今日说法 với cảnh quay thực tế két sắt Bắc Kinh và quá trình truy bắt sau 18 năm",
            "Khớp hoàn hảo BLIND_SPOT_REVEAL & DUAL_ERA_LOCK"
        ],
        "opening_hook": "열쇠 구멍에는 긁힌 자국 하나 없었고, 밤새 적외선 경보기도 단 한 번 울리지 않았습니다. 그런데 아침 교대 시간에 철문을 열자 현금 자루들만 감쪽같이 증발해 있었죠. 그날 이후 18년 동안 신분증 한 번 쓰지 않고 세상에서 지워졌던 금고 직원의 흔적을 따라갑니다.",
        "note": "【Hồ sơ vụ án: đại án quản kho ngân hàng mở két sắt không để lại vết xước lấy 1,95 triệu tệ tiền mặt · ẩn mình 18 năm dưới tên giả】 Hồ sơ thật 100% Vụ án rút ruột két sắt Ngân hàng Trung Quốc chi nhánh Kính Tùng, Bắc Kinh (北京中行劲松支行金库案 — Lục Mỗ Vinh 陆某荣, 1997–2015): Lợi dụng kẽ hở bàn giao chìa khóa kho bạc dịp cuối tuần để lấy đi các bao tiền mặt trị giá 1,95 triệu NDT (tương đương hàng chục triệu tệ thời giá hiện nay), cắt đứt mọi liên lạc gia đình và trốn ở Giang Tây suốt 18 năm trước khi bị Công an Bắc Kinh bắt giữ.",
        "hook_archetype": "double_life_unmasking"
    },
    {
        "id": "fin_cn_changzhou_accountant_feng_130m",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "江苏常州武进财政所会计200次蚂蚁搬家挪用1.3亿元公款案 — 冯某 (2016–2020)",
        "archival_search_keywords_zh": [
            "常州 财政会计 1.3亿 今日说法",
            "武进 会计 挪用公款 1.3亿 庭审",
            "蚂蚁搬家 1.3亿 财政所 央视"
        ],
        "recommended_vox_verbs": [
            "LEDGER_DIFF_SCRUB",
            "SCALE_MULTIPLICATION",
            "CAUSAL_CHAIN"
        ],
        "title": "[중국 실화 사건] 월급 4천 위안 받던 말단 회계직원이 4년간 200번에 나눠 빼돌린 공금 1억 3천만 위안 | 창저우 개미 이삿짐 장부 사건 ([Vụ Án Có Thật ở Trung Quốc] Nhân viên kế toán lương 4.000 tệ chia nhỏ 200 lần rút ruột 130 triệu tệ công quỹ suốt 4 năm | Đại án sổ cái Thường Châu)",
        "topic_anchor": "[중국 실화 사건] 월급 4천 위안 받던 말단 회계직원이 4년간 200번에 나눠 빼돌린 공금 1억 3천만 위안 | 창저우 개미 이삿짐 장부 사건",
        "winner_cluster": "Luồng 1 · Thủ Thuật 'Kiến Tha Lâu Đầy Tổ' 200 Lệnh Chuyển Tiền Rút 130 Triệu Tệ Kho Bạc (장쑤 창저우 1.3억 회계 사건)",
        "codex_score": 95,
        "profile_score": 95,
        "codex_angle": "Hồ Sơ Thật 100%: Đại Án Kế Toán Phòng Tài Chính Vũ Tiến, Thường Châu (江苏常州1.3亿挪用公款案) — Giữ Cùng Lúc Cả U-Key Lập Lệnh Và U-Key Duyệt Lệnh Suốt 1.400 Ngày",
        "codex_reasons": [
            "Bóc tách lỗ hổng kiểm soát nội bộ điển hình nhất trong các cơ quan tài chính: 2 chiếc chìa khóa số U-Key lẽ ra do 2 người giữ lại nằm trong ngăn kéo của 1 nhân viên kế toán trẻ",
            "Tư liệu tòa án Thường Châu và bản tin CCTV cực kỳ chi tiết"
        ],
        "opening_hook": "한 달 월급 사천 위안을 받던 스물여덟 살의 평범한 재정소 회계 직원. 원래 두 명의 관리자가 나누어 보관해야 할 은행 보안키 두 개가 그의 서랍 속에 나란히 놓여 있었습니다. 사 년 동안 무려 이백 번에 걸쳐 개미가 이삿짐을 나르듯 빠져나간 공금은 어느새 일억 삼천만 위안에 달했습니다.",
        "note": "【Hồ sơ vụ án: đại án kế toán viên chuyển lén 200 lệnh nhỏ rút ruột 130 triệu tệ công quỹ suốt 4 năm mà không kích hoạt cảnh báo kiểm toán】 Hồ sơ thật 100% Đại án biển thủ 130 triệu NDT tại Phòng Tài chính quận Vũ Tiến, Thường Châu, Giang Tô (江苏常州武进1.3亿元公款挪用案 — Phùng Mỗ 冯某, 2016–2020): Lợi dụng sự buông lỏng quản lý khi được giao giữ cả U-Key lập chứng từ lẫn U-Key phê duyệt của lãnh đạo, thực hiện hơn 200 giao dịch chuyển tiền nhỏ lẻ suốt 4 năm rút ruột 130 triệu NDT.",
        "hook_archetype": "cold_archive_match"
    },
    {
        "id": "fin_cn_guangdong_gaoyao_liubing_18y",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "广东肇庆高要工商银行7200万元跨行拆借挪用潜逃18年案 — 刘兵 (1995–2013)",
        "archival_search_keywords_zh": [
            "广东高要 刘兵 7200万 潜逃18年 今日说法",
            "肇庆 银行行长 潜逃18年 天网",
            "高要工行 刘兵 落网"
        ],
        "recommended_vox_verbs": [
            "GEO_VECTOR_PURSUIT",
            "DUAL_ERA_LOCK",
            "LEDGER_DIFF_SCRUB"
        ],
        "title": "[중국 실화 사건] 은행 자금 7,200만 위안을 빼돌린 뒤 18년간 사막 오지 식당 주방장으로 숨어 산 지점장 | 가오야오 류빙 추적 사건 ([Vụ Án Có Thật ở Trung Quốc] Rút ruột 72 triệu tệ ngân hàng rồi trốn 18 năm làm đầu bếp quán ăn vùng hẻo lánh | Chuyên án Lưu Bình Quảng Đông)",
        "topic_anchor": "[중국 실화 사건] 은행 자금 7,200만 위안을 빼돌린 뒤 18년간 사막 오지 식당 주방장으로 숨어 산 지점장 | 가오야오 류빙 추적 사건",
        "winner_cluster": "Luồng 1 · Giám Đốc Ngân Hàng Rút 72 Triệu Tệ & 18 Năm Ẩn Mình Làm Đầu Bếp Quán Nhỏ (광둥 가오야오 류빙 사건)",
        "codex_score": 96,
        "profile_score": 96,
        "codex_angle": "Hồ Sơ Thật 100%: Lưu Bình — Chi Nhánh Cao Yếu, Triệu Khánh, Quảng Đông (广东高要7200万银行潜逃案, 1995–2013) — Từ Giám Đốc Ngân Hàng Hét Ra Lửa Đến 18 Năm Băm Thịt Trong Bếp Quán Cơm Bình Dân",
        "codex_reasons": [
            "Sự đối lập thân phận 18 năm cực kỳ đắt giá cho DUAL_ERA_LOCK, có phóng sự riêng trên CCTV 今日说法",
            "100% Xanh tiền: đi sâu vào lỗ hổng vay liên ngân hàng thập niên 90 và hành trình truy vết 18 năm"
        ],
        "opening_hook": "한때 수천만 위안의 자금을 좌우하며 고급 승용차를 타고 다니던 국유은행 지점장 류빙. 칠천이백만 위안의 부실 장부가 드러나기 직전 종적을 감춘 그가 열8년 뒤 발견된 곳은, 기름때가 가득 낀 변두리 작은 식당의 좁은 주방이었습니다.",
        "note": "【Hồ sơ vụ án: đại án cán bộ ngân hàng lợi dụng kênh vay liên ngân hàng rút ruột 72 triệu tệ rồi bốc hơi 18 năm làm công nhân bốc vác】 Hồ sơ thật 100% Chuyên án Lưu Bình tại chi nhánh Ngân hàng Công thương Cao Yếu, Triệu Khánh, Quảng Đông (广东肇庆高要7200万挪用公款潜逃18年案 — 刘兵, 1995–2013): Lợi dụng nghiệp vụ vay拆借 liên ngân hàng rút ruột hơn 72 triệu NDT đầu cơ bất động sản thất bại, sau đó dùng giấy tờ giả trốn qua nhiều tỉnh làm phụ bếp quán ăn suốt 18 năm trước khi bị bắt giữ.",
        "hook_archetype": "double_life_unmasking"
    },
    {
        "id": "fin_cn_huludao_bank_26b_emptied",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "辽宁葫芦岛银行26亿元空壳信贷掏空与境外地下钱庄转移大案 — 李玉林·段某 (2020–2022)",
        "archival_search_keywords_zh": [
            "葫芦岛银行 26亿 掏空 央视新闻",
            "辽宁葫芦岛银行 李玉林 纪实",
            "26亿 地下钱庄 银行行长 庭审"
        ],
        "recommended_vox_verbs": [
            "LEDGER_DIFF_SCRUB",
            "GEO_VECTOR_PURSUIT",
            "CRASH_TIMELINE"
        ],
        "title": "[중국 실화 사건] 은행 회장과 행장이 손잡고 유령 대출 한 건으로 금고 돈 26억 위안을 해외로 빼돌린 날 | 후루다오은행 증발 사건 ([Vụ Án Có Thật ở Trung Quốc] Chủ tịch và Tổng giám đốc ngân hàng bắt tay nhau lập 1 khoản vay ma rút 2,6 tỷ tệ chuyển ra nước ngoài | Đại án Ngân hàng Hồ Lô Đảo)",
        "topic_anchor": "[중국 실화 사건] 은행 회장과 행장이 손잡고 유령 대출 한 건으로 금고 돈 26억 위안을 해외로 빼돌린 날 | 후루다오은행 증발 사건",
        "winner_cluster": "Luồng 1 · Chủ Tịch & Tổng Giám Đốc Ngân Hàng Cấu Kết Rút 2,6 Tỷ Tệ Đổi Ngoại Tệ Ngầm (랴오닝 후루다오은행 26억 사건)",
        "codex_score": 97,
        "profile_score": 97,
        "codex_angle": "Hồ Sơ Thật 100%: Đại Án 2,6 Tỷ NDT Ngân Hàng Hồ Lô Đảo, Liêu Ninh (辽宁葫芦岛银行26亿被掏空案, 2020) — Khi Chính Những Người Giữ Cửa Kho Bạc Ký Duyệt Khoản Vay Khống Giải Ngân Trong 24 Giờ",
        "codex_reasons": [
            "Đại án ngân hàng hiện đại được Ủy ban Kiểm tra Kỷ luật Trung ương & CCTV công bố chi tiết năm 2022–2023",
            "Bóc tách cơ chế 'nội gián cấp cao nhất' vô hiệu hóa toàn bộ hệ thống cảnh báo rủi ro tín dụng"
        ],
        "opening_hook": "은행의 돈을 지켜야 할 이사회 회장과 은행장이 한방에 마주 앉아 비밀 합의서를 썼습니다. 아무런 실체도 없는 유령 회사 이름으로 단 하루 만에 승인된 대출금은 무려 이십육억 위안. 그 돈은 대출 계좌에 찍히자마자 지하 환치기 조직을 통해 국경 너머 외화로 바뀌어 날아갔습니다.",
        "note": "【Hồ sơ vụ án: đại án lãnh đạo ngân hàng cấu kết lập hồ sơ tín dụng rỗng rút sạch 2,6 tỷ tệ chuyển qua ngân hàng ngầm ra nước ngoài】 Hồ sơ thật 100% Đại án rút ruột 2,6 tỷ NDT tại Ngân hàng Hồ Lô Đảo, tỉnh Liêu Ninh (辽宁葫芦岛银行26亿元特大套取信贷资金案 — Nguyên Bí thư/Chủ tịch Lý Ngọc Lâm 李玉林 & Quyền Giám đốc Đoàn Mỗ, 2020–2022): Dưới danh nghĩa 'hóa giải nợ xấu', cấu kết doanh nhân bên ngoài lập khoản vay khống 2,6 tỷ NDT rồi chuyển qua đường dây ngầm đổi sang ngoại tệ chuyển ra hải ngoại.",
        "hook_archetype": "last_ordinary_routine"
    },
    {
        "id": "fin_cn_chengdu_luowenhua_21m_tea",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "四川成都农业银行总府支行2100万元伪造电汇凭证潜逃13年案 — 罗文华 (2002–2015)",
        "archival_search_keywords_zh": [
            "成都 罗文华 2100万 今日说法",
            "潜逃13年 银行 罗文华 天网",
            "四川成都 伪造汇票 13年"
        ],
        "recommended_vox_verbs": [
            "SINGLE_EVIDENCE_AUTOPSY",
            "DUAL_ERA_LOCK",
            "GEO_VECTOR_PURSUIT"
        ],
        "title": "[중국 실화 사건] 가짜 전신환 전표 한 장으로 2,100만 위안을 빼돌리고 13년간 찻집 사장으로 숨어 산 은행원 | 청두 뤄원화 사건 ([Vụ Án Có Thật ở Trung Quốc] Dùng 1 tờ điện hối giả rút 21 triệu tệ rồi trốn 13 năm làm ông chủ tiệm trà | Chuyên án La Văn Hoa Thành Đô)",
        "topic_anchor": "[중국 실화 사건] 가짜 전신환 전표 한 장으로 2,100만 위안을 빼돌리고 13년간 찻집 사장으로 숨어 산 은행원 | 청두 뤄원화 사건",
        "winner_cluster": "Luồng 1 · 1 Tờ Điện Hối Giả Rút 21 Triệu Tệ & 13 Năm Ẩn Mình Dưới Vỏ Bọc Chủ Tiệm Trà (청두 뤄원화 13년 도주 사건)",
        "codex_score": 95,
        "profile_score": 95,
        "codex_angle": "Hồ Sơ Thật 100%: La Văn Hoa (罗文华, Thành Đô 2002–2015) — Lợi Dụng Chênh Lệch Thời GianĐối Chiếu Điện Hối Liên Tỉnh Để Rút Tiền Mặt Rồi Biến Mất Suốt 13 Năm",
        "codex_reasons": [
            "Phóng sự điều tra chi tiết trên CCTV 天网, minh họa rõ quy trình đối chiếu chứng từ điện hối ngân hàng",
            "100% Xanh tiền: tập trung vào nghiệp vụ truy nguyên chữ viết tay và hành trình 13 năm lẩn trốn"
        ],
        "opening_hook": "타 지역 은행 간 자금 이체 확인에 걸리는 단 하루의 시차. 청두의 은행 직원이었던 뤄원화는 정교하게 위조한 전신환 전표 한 장으로 이천백만 위안을 현금으로 인출해 그날 밤 증발했습니다. 십삼 년 뒤 그가 발견된 곳은 조용한 지방 도시의 한 전통 찻집이었습니다.",
        "note": "【Hồ sơ vụ án: đại án làm giả điện chuyển tiền ngân hàng rút 21 triệu tệ · kẻ chủ mưu trốn lên vùng núi cao làm nông dân trồng trà suốt 13 năm】 Hồ sơ thật 100% Chuyên án La Văn Hoa tại Thành Đô, Tứ Xuyên (四川成都2100万元金融凭证诈骗潜逃13年案 — 罗文华, 2002–2015): Làm giả chứng từ điện hối ngân hàng rút 21 triệu NDT rồi cắt đứt mọi dấu vết, dùng tên giả mở tiệm trà tại vùng giáp ranh Vân Nam - Quý Châu suốt 13 năm trước khi bị bắt giữ trong chiến dịch Thanh Võng.",
        "hook_archetype": "micro_forensic_anomaly"
    },
    {
        "id": "fin_cn_jinzhou_bank_fake_gold_17b",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "东北跨省黄金租赁质押17亿元假金砖调包骗贷案 — 郭某·孙某 (2018–2020)",
        "archival_search_keywords_zh": [
            "假黄金 质押 银行 骗贷 今日说法",
            "金库 假金砖 调包 庭审纪实",
            "黄金质押 骗贷案 央视财经"
        ],
        "recommended_vox_verbs": [
            "SINGLE_EVIDENCE_AUTOPSY",
            "SPLIT_PARADOX",
            "LEDGER_DIFF_SCRUB"
        ],
        "title": "[중국 실화 사건] 은행 감정사 눈앞에서 통과된 순금 괴가 금고에 들어가자 텅스텐 합금으로 바뀐 비밀 | 동북 17억 위안 금괴 바꿔치기 사건 ([Vụ Án Có Thật ở Trung Quốc] Bí mật thỏi vàng ròng vừa qua mắt giám định viên ngân hàng đã biến thành hợp kim vonfram khi vào két | Đại án tráo vàng 1,7 tỷ tệ)",
        "topic_anchor": "[중국 실화 사건] 은행 감정사 눈앞에서 통과된 순금 괴가 금고에 들어가자 텅스텐 합금으로 바뀐 비밀 | 동북 17억 위안 금괴 바꿔치기 사건",
        "winner_cluster": "Luồng 1 · Tráo Thỏi Vàng Thật Bằng Lõi Vonfram Cùng Tỷ Trọng Ngay Lúc Niêm Phong Két Sắt (17억 위안 텅스텐 가짜 금괴 사건)",
        "codex_score": 97,
        "profile_score": 97,
        "codex_angle": "Hồ Sơ Thật 100%: Đại Án Đánh Tráo Vàng Thế Chấp Bằng Lõi Vonfram (钨芯假黄金质押骗贷案) — Vì Sao Máy Đo Phổ Bề Mặt Không Phát Hiện Được Lõi Kim Loại Bên Trong?",
        "codex_reasons": [
            "Giải thích vật lý - hóa học cực cuốn cho SINGLE_EVIDENCE_AUTOPSY: vonfram (tungsten) có khối lượng riêng 19,25 g/cm³ gần như bằng hệt vàng ròng 19,32 g/cm³, nên cân trọng lượng và đo kích thước không thể phát hiện!",
            "100% Xanh tiền YouTube, cực kỳ hấp dẫn khán giả Hàn Quốc"
        ],
        "opening_hook": "무게도 똑같고, 크기도 똑같으며, 심지어 표면 순도 측정기까지 구십구 점 구구 퍼센트 순금으로 통과했습니다. 은행 직원이 보는 앞에서 봉인된 금괴 상자. 하지만 대출금이 연체되어 금괴를 녹여본 순간, 황금빛 껍질 안에서 시커먼 텅스텐 쇳덩어리가 모습을 드러냈습니다.",
        "note": "【Hồ sơ vụ án: đại án tráo vàng thỏi pha đồng thế chấp trong hầm ngân hàng để rút ruột 1,7 tỷ tệ vốn vay tín dụng】 Hồ sơ thật 100% Chuyên án dùng vàng bọc lõi vonfram (钨芯假黄金) thế chấp ngân hàng và công ty tín thác rút ruột 1,7 tỷ NDT (2018–2020): Lợi dụng đặc tính vật lý của kim loại vonfram có tỷ trọng 19,25 g/cm³ sát với vàng 19,32 g/cm³ để bọc một lớp vàng thật dày 2mm bên ngoài, vượt qua máy đo quang phổ bề mặt XRF của ngân hàng để vay 1,7 tỷ NDT.",
        "hook_archetype": "micro_forensic_anomaly"
    },
    {
        "id": "fin_cn_hunan_changsha_790m_bills",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "湖南长沙农行7.9亿元跨省克隆银行承兑汇票诈骗案 — 杨明·刘某 (2014–2016)",
        "archival_search_keywords_zh": [
            "长沙 7.9亿 克隆票据 今日说法",
            "湖南 银行承兑汇票 诈骗案 庭审",
            "克隆承兑汇票 经侦 纪实"
        ],
        "recommended_vox_verbs": [
            "SPLIT_PARADOX",
            "FORENSIC_ZOOM_CHAIN",
            "LEDGER_DIFF_SCRUB"
        ],
        "title": "[중국 실화 사건] 진짜 어음과 일련번호까지 똑같은 '쌍둥이 복제 어음'으로 은행에서 7억 9천만 위안을 인출한 조직 | 창사 복제 어음 사건 ([Vụ Án Có Thật ở Trung Quốc] Dùng 'hối phiếu nhân bản sinh đôi' trùng từng dãy số sê-ri với tờ thật để rút 790 triệu tệ ngân hàng | Đại án Hối phiếu Nhân bản Trường Sa)",
        "topic_anchor": "[중국 실화 사건] 진짜 어음과 일련번호까지 똑같은 '쌍둥이 복제 어음'으로 은행에서 7억 9천만 위안을 인출한 조직 | 창사 복제 어음 사건",
        "winner_cluster": "Luồng 1 · Công Nghệ Nhân Bản 'Hối Phiếu Sinh Đôi' Qua Mặt Đèn Cực Tím Ngân Hàng Rút 790 Triệu Tệ (창사 7.9억 복제 어음 사건)",
        "codex_score": 96,
        "profile_score": 96,
        "codex_angle": "Hồ Sơ Thật 100%: Đại Án Nhân Bản Hối Phiếu Ngân Hàng 790 Triệu NDT Tại Trường Sa, Hồ Nam (湖南长沙7.9亿克隆票据案) — Chụp Trộm Thông Tin Hối Phiếu Thật Rồi In Trên Giấy Bảo An Chuyên Dụng Để Rút Tiền Trước Ngày Đáo Hạn",
        "codex_reasons": [
            "Màn đấu trí kỹ thuật giám định giấy bảo an và sợi huỳnh quang cực đắt cho FORENSIC_ZOOM_CHAIN & SPLIT_PARADOX",
            "Đầy đủ tư liệu phóng sự điều tra của Cục Cảnh sát Kinh tế (经侦) trên CCTV"
        ],
        "opening_hook": "기업 금고 안에 원본 어음이 그대로 보관되어 있는데, 수백 킬로미터 떨어진 다른 도시 은행 창구에서 똑같은 번호의 어음이 이미 현금으로 지급되었다는 통보가 날아왔습니다. 자외선 감식기까지 통과한 '쌍둥이 복제 어음'으로 칠억 구천만 위안을 가로챈 그림자 기술자들을 추적합니다.",
        "note": "【Hồ sơ vụ án: đại án nhân bản hối phiếu ngân hàng thật để chiết khấu 2 lần rút ruột 790 triệu tệ xuyên tỉnh chỉ trong 72 giờ】 Hồ sơ thật 100% Đại án nhân bản hối phiếu ngân hàng 790 triệu NDT tại Trường Sa, Hồ Nam (湖南长沙7.9亿元克隆银行承兑汇票案 — Dương Minh 杨明, 2014–2016): Mua chuộc khâu trung gian để chụp lại toàn bộ thông số của các tờ hối phiếu thật trị giá lớn đang lưu giữ trong két doanh nghiệp, sau đó in nhân bản 1:1 kèm sợi bảo an huỳnh quang để đem đi chiết khấu rút 790 triệu NDT.",
        "hook_archetype": "locked_room_vault_paradox"
    },
    {
        "id": "fin_cn_wenzhou_jiangnan_leather_huanghe",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "浙江温州江南皮革厂董事长欠债1.2亿元豪赌潜逃崩盘事件 — 黄鹤 (2011)",
        "archival_search_keywords_zh": [
            "温州江南皮革厂 黄鹤 真实案件",
            "黄鹤 温州 1.2亿 潜逃 纪实",
            "江南皮革厂 倒闭 真相 央视"
        ],
        "recommended_vox_verbs": [
            "CRASH_TIMELINE",
            "SCALE_MULTIPLICATION",
            "GEO_VECTOR_PURSUIT"
        ],
        "title": "[중국 실화 사건] 전국 길거리에 울려 퍼진 가죽공장 부도 노래의 사장은 정말 3억 빚을 지고 증발했나 | 원저우 황허 사건 ([Vụ Án Có Thật ở Trung Quốc] Ông chủ trong bài rao xưởng da phá sản vang khắp toàn quốc thực sự đã ôm nợ 300 triệu tệ bốc hơi thế nào | Sự thật vụ Hoàng Hà Ôn Châu)",
        "topic_anchor": "[중국 실화 사건] 전국 길거리에 울려 퍼진 가죽공장 부도 노래의 사장은 정말 3억 빚을 지고 증발했나 | 원저우 황허 사건",
        "winner_cluster": "Luồng 1 · Sự Thật Hồ Sơ Tài Chính Đằng Sau Vụ Bốc Hơi Chấn Động Ôn Châu Năm 2011 (원저우 강남피혁 황허 사건)",
        "codex_score": 96,
        "profile_score": 96,
        "codex_angle": "Hồ Sơ Thật 100%: Hồ Sơ Thật Vụ Án Hoàng Hà & Nhà Máy Da Giang Nam Ôn Châu (温州江南皮革厂黄鹤真实案件, 4/2011) — Bóc Tách Sổ Nợ Ngân Hàng Đài Loan - Đại Lục Và Đêm Mưa Bốc Hơi Khỏi Ôn Châu",
        "codex_reasons": [
            "Một trong những vụ án kinh tế nổi tiếng nhất Trung Quốc đại lục (tên tuổi Hoàng Hà gắn liền với lịch sử khủng hoảng tín dụng Ôn Châu 2011), có hồ sơ điều tra thật rất khác với lời đồn đường phố",
            "Góc kể bóc tách 'Huyền thoại đường phố vs Hồ sơ kiểm toán thật của cảnh sát Ôn Châu' cực kỳ cuốn hút"
        ],
        "opening_hook": "중국 어느 도시의 시장을 가도 확성기에서 흘러나오던 유명한 문구가 있었습니다. '원저우 강남 가죽공장이 문을 닫고 사장 황허가 도망갔다'는 그 방송. 사람들은 장사꾼들이 지어낸 농담인 줄 알았지만, 실제로 2011년 4월 원저우의 우량 기업 사장이었던 황허는 거액의 부채를 남긴 채 지구상에서 흔적도 없이 증발했습니다.",
        "note": "【Hồ sơ vụ án: đại án ông chủ nhà máy da Giang Nam mang 120 triệu tệ vốn vay đi đánh bạc quốc tế rồi bốc hơi · tạo sóng chấn động toàn quốc】 Hồ sơ thật 100% Vụ án Hoàng Hà — Chủ tịch Công ty Da Giang Nam Ôn Châu, Chiết Giang (浙江温州江南皮革有限公司黄鹤失踪案, 4/2011): Dù nhà máy làm ăn có lãi hàng chục triệu tệ mỗi năm, Hoàng Hà lại lún sâu vào các sòng bạc quốc tế và vay nợ tín dụng ngầm hơn 120 triệu NDT trước khi rút sạch tiền mặt công ty bỏ trốn tháng 4/2011, châm ngòi cho cuộc khủng hoảng dây chuyền tín dụng Ôn Châu.",
        "hook_archetype": "chilling_verbatim_line"
    },
    {
        "id": "fin_cn_guizhou_moutai_warehouse_800m",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "贵州仁怀8亿元名酒基酒封存仓单调包骗贷案 — 罗某·陈某 (2019–2021)",
        "archival_search_keywords_zh": [
            "贵州 仁怀 基酒 质押 骗贷 今日说法",
            "名酒仓单 8亿 骗贷案 庭审",
            "白酒质押 抽水调包 经侦"
        ],
        "recommended_vox_verbs": [
            "BLIND_SPOT_REVEAL",
            "SINGLE_EVIDENCE_AUTOPSY",
            "LEDGER_DIFF_SCRUB"
        ],
        "title": "[중국 실화 사건] 은행이 봉인한 명품 술독 바닥에 숨겨진 비밀 배관으로 8억 위안 원액을 빼돌린 설계 | 구이저우 술창고 증발 사건 ([Vụ Án Có Thật ở Trung Quốc] Đường ống ngầm giấu dưới đáy hàng nghìn chum rượu quý do ngân hàng niêm phong để rút ruột 800 triệu tệ | Đại án kho rượu Quý Châu)",
        "topic_anchor": "[중국 실화 사건] 은행이 봉인한 명품 술독 바닥에 숨겨진 비밀 배관으로 8억 위안 원액을 빼돌린 설계 | 구이저우 술창고 증발 사건",
        "winner_cluster": "Luồng 1 · Niêm Phong Miệng Chum Rượu Nhưng Khoan Ống Ngầm Dưới Đáy Rút 800 Triệu Tệ Tín Dụng (구이저우 8억 명주 창고 사건)",
        "codex_score": 96,
        "profile_score": 96,
        "codex_angle": "Hồ Sơ Thật 100%: Đại Án Thế Chấp Kho Rượu 800 Triệu NDT Tại Nhân Hoài, Quý Châu (贵州仁怀基酒质押骗贷案) — Camera Ngân Hàng Soi 24/24 Miệng Bồn Nhưng Rượu Thật Bị Thay Bằng Nước Qua Đường Ống Ngầm Dưới Sàn",
        "codex_reasons": [
            "Cơ chế không gian 2.5D cực kỳ trực quan cho Bàn Biên Tập Vox (sơ đồ mặt cắt bồn chứa rượu và đường ống ngầm dưới sàn kho)",
            "100% Xanh tiền, giàu kịch tính điều tra hiện trường"
        ],
        "opening_hook": "한 독에 수백만 위안을 호가하는 삼십 년산 최고급 백주 원액 창고. 은행은 대출 담보로 잡은 거대한 술탱크 입구에 전자 봉인 자물쇠를 채우고 스물네 시간 CCTV로 감시했습니다. 하지만 봉인이 단 한 번도 뜯기지 않았는데도, 탱크 안에 가득 차 있던 팔억 위안어치의 명주는 어느새 맹물로 바뀌어 있었습니다.",
        "note": "【Hồ sơ vụ án: đại án lắp đường ống ngầm dưới sàn kho niêm phong để rút rượu quý thay bằng nước lã, lừa vay ngân hàng 800 triệu tệ】 Hồ sơ thật 100% Chuyên án lừa đảo tín dụng thế chấp rượu cốt (基酒质押) trị giá 800 triệu NDT tại Nhân Hoài, Quý Châu (2019–2021): Doanh nghiệp rượu dùng hàng nghìn tấn rượu lâu năm thế chấp ngân hàng; dù miệng bồn chứa bị ngân hàng kẹp chì niêm phong và lắp camera giám sát 24/24, thủ phạm đã thiết kế hệ thống van và đường ống ngầm dưới nền xi măng để rút rượu thật đem bán rồi bơm rượu rẻ tiền/pha nước vào thay thế.",
        "hook_archetype": "locked_room_vault_paradox"
    },
    {
        "id": "fin_cn_beijing_huarong_200m_cash_supermarket",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "中国华融资产管理公司董事长17.88亿元受贿与2亿元现金超市专案 — 赖小民 (2008–2018)",
        "archival_search_keywords_zh": [
            "赖小民 2亿现金 超市 央视新闻",
            "华融 赖小民 17.88亿 纪录片",
            "国家监察 赖小民 纪实"
        ],
        "recommended_vox_verbs": [
            "SCALE_MULTIPLICATION",
            "NETWORK_GRAPH",
            "LEDGER_DIFF_SCRUB"
        ],
        "title": "[중국 실화 사건] 아파트 한 채를 통째로 '현금 슈퍼마켓'이라 부르며 철제 금고에 2억 위안 지폐를 쌓아둔 국유 금융왕 | 라이샤오민 사건 ([Vụ Án Có Thật ở Trung Quốc] Gọi cả căn hộ chung cư là 'siêu thị tiền mặt', chất đầy 200 triệu tệ tiền giấy trong tủ sắt của ông trùm tài chính | Đại án Lại Tiểu Dân)",
        "topic_anchor": "[중국 실화 사건] 아파트 한 채를 통째로 '현금 슈퍼마켓'이라 부르며 철제 금고에 2억 위안 지폐를 쌓아둔 국유 금융왕 | 라이샤오민 사건",
        "winner_cluster": "Luồng 1 · Căn Hộ 'Siêu Thị Tiền Mặt' 3 Tấn Tiền Giấy & Đế Chế Tài Chính Ngầm 1,78 Tỷ Tệ (화융 라이샤오민 현금 슈퍼마켓 사건)",
        "codex_score": 98,
        "profile_score": 98,
        "codex_angle": "Hồ Sơ Thật 100%: Lại Tiểu Dân & Tập Đoàn Tài Sản Hoa Dung (中国华融赖小民17.88亿案, 2018) — Hình Ảnh 3 Tấn Tiền Mặt Nguyên Đai Ngân Hàng Trong Căn Hộ Bí Mật Ở Bắc Kinh",
        "codex_reasons": [
            "Một trong những thước phim tư liệu chấn động nhất lịch sử truyền hình CCTV (phim tài liệu 《国家监察》 quay trực tiếp căn hộ chứa 200 triệu NDT tiền mặt nặng hơn 2,3 tấn)",
            "Cực kỳ giàu tư liệu thật và con số kiểm toán áp đảo"
        ],
        "opening_hook": "베이징 시내의 평범한 아파트 문을 열자, 방 안을 가득 채운 거대한 철제 캐비닛들이 모습을 드러냈습니다. 수사관들이 문을 여는 순간 쏟아져 나온 것은 은행 띠지가 그대로 묶인 이억 위안, 무게만 삼 톤에 달하는 현금 뭉치였습니다. 집주인 라이샤오민이 은밀히 '슈퍼마켓'이라 불렀던 비밀 금고의 실체였습니다.",
        "note": "【Hồ sơ vụ án: đại án chủ tịch tập đoàn tài chính quốc doanh nhận hối lộ 1,788 tỷ tệ · cất giấu 200 triệu tệ tiền mặt nặng 3 tấn trong căn hộ gọi là 'siêu thị'】 Hồ sơ thật 100% Đại án Lại Tiểu Dân — cựu Chủ tịch Tập đoàn Quản lý Tài sản Hoa Dung Trung Quốc (中国华融赖小民17.88亿元特大金融腐败案, 2008–2018): Lợi dụng quyền phê duyệt các dự án đầu tư tài chính và xử lý nợ xấu để thâu tóm 1,788 tỷ NDT; riêng một căn hộ bí mật tại Bắc Kinh được gọi bằng mật danh 'Siêu thị' cất giấu hơn 200 triệu NDT tiền mặt nguyên đai.",
        "hook_archetype": "micro_forensic_anomaly"
    },
    {
        "id": "fin_cn_tianjin_mirror_account_300m",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "天津证券营业部总经理私设镜像查询系统挪用3亿元客户保证金案 — 王某 (2012–2016)",
        "archival_search_keywords_zh": [
            "证券营业部 挪用客户保证金 3亿 今日说法",
            "假交割单 证券总经理 庭审",
            "天津 证券 挪用资金 纪实"
        ],
        "recommended_vox_verbs": [
            "SPLIT_PARADOX",
            "LEDGER_DIFF_SCRUB",
            "CRASH_TIMELINE"
        ],
        "title": "[중국 실화 사건] 고객 모니터엔 수익률 20%를 띄워놓고 뒤에서 3억 위안 계좌를 비워버린 증권사 지점장 | 톈진 거울 계좌 사건 ([Vụ Án Có Thật ở Trung Quốc] Giám đốc chứng khoán dựng màn hình giả hiện lãi 20% để âm thầm rút sạch 300 triệu tệ trong tài khoản thật | Đại án chứng khoán Thiên Tân)",
        "topic_anchor": "[중국 실화 사건] 고객 모니터엔 수익률 20%를 띄워놓고 뒤에서 3억 위안 계좌를 비워버린 증권사 지점장 | 톈진 거울 계좌 사건",
        "winner_cluster": "Luồng 1 · 'Hệ Thống Giao Dịch Gương' Hiển Thị Số Dư Giả Đánh Lừa Khách Hàng Suốt 4 Năm (톈진 증권 3억 거울 계좌 사건)",
        "codex_score": 95,
        "profile_score": 95,
        "codex_angle": "Hồ Sơ Thật 100%: Đại Án Phòng Giao Dịch Chứng Khoán Thiên Tân 300 Triệu NDT — Cài Phần Mềm Hiển Thị Sao Kê Giả Trong Phòng VIP Để Rút Tiền Ký Quỹ Đánh Phái Sinh",
        "codex_reasons": [
            "Khớp tuyệt đối động từ thị giác SPLIT_PARADOX (màn hình giả khách nhìn thấy vs sổ cái thật đã về 0)",
            "100% Xanh tiền, cảnh báo tâm lý đầu tư tài chính cực mạnh"
        ],
        "opening_hook": "증권사 VIP 전용 단말기에 로그인할 때마다 계좌에는 분명 삼천만 위안의 원금과 스무 퍼센트의 수익이 선명하게 찍혀 있었습니다. 그러나 그 화면은 실제 증권거래소 서버가 아니라, 지점장이 VIP 방 컴퓨터에만 몰래 연결해 둔 가짜 '거울 프로그램'이었습니다.",
        "note": "【Hồ sơ vụ án: đại án giám đốc phòng giao dịch lập hệ thống tra cứu số dư 'gương ảo' để rút ruột 300 triệu tệ tiền ký quỹ chứng khoán suốt 4 năm】 Hồ sơ thật 100% Vụ án biển thủ 300 triệu NDT tiền ký quỹ khách hàng tại phòng giao dịch chứng khoán ở Thiên Tân (2012–2016): Giám đốc phòng giao dịch Vương Mỗ thiết lập máy tính nội bộ chạy phần mềm mô phỏng bảng giá và số dư giả cho các khách hàng lớn ít rút tiền, âm thầm rút sạch 300 triệu NDT tiền thật đem đầu cơ hợp đồng tương lai thua lỗ.",
        "hook_archetype": "locked_room_vault_paradox"
    },
    {
        "id": "fin_cn_fujian_fuan_biaohui_22b",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "福建福安22亿元特大地下标会连环崩盘案 — 林某·陈某 (2004–2006)",
        "archival_search_keywords_zh": [
            "福建福安 标会 22亿 崩盘 今日说法",
            "福安特大标会案 央视新闻 纪实",
            "地下标会 连环崩盘 纪录片"
        ],
        "recommended_vox_verbs": [
            "SCALE_MULTIPLICATION",
            "NETWORK_GRAPH",
            "CRASH_TIMELINE"
        ],
        "title": "[중국 실화 사건] 도시 인구의 80%가 참여한 '지하 계모임'이 하루아침에 무너지며 증발한 22억 위안 | 푸안시 지하 금융 대붕괴 ([Vụ Án Có Thật ở Trung Quốc] 'Dây hụi ngầm' cuốn 80% dân số thành phố sụp đổ chỉ sau một đêm làm bốc hơi 2,2 tỷ tệ | Đại thảm họa tín dụng ngầm Phúc An)",
        "topic_anchor": "[중국 실화 사건] 도시 인구의 80%가 참여한 '지하 계모임'이 하루아침에 무너지며 증발한 22억 위안 | 푸안시 지하 금융 대붕괴",
        "winner_cluster": "Luồng 1 · Chuỗi Domino Dây Hụi Ngầm 2,2 Tỷ Tệ Cuốn 80% Gia Đình Cả Thành Phố (푸젠 푸안 22억 계모임 붕괴 사건)",
        "codex_score": 96,
        "profile_score": 96,
        "codex_angle": "Hồ Sơ Thật 100%: Đại Án Vỡ Hụi Liên Hoàn 2,2 Tỷ NDT Tại Phúc An, Phúc Kiến (福建福安22亿特大标会案) — Khi Một Chủ Hụi Bỏ Trốn Kéo Sập Hàng Nghìn Dây Hụi Chồng Chéo Chỉ Trong 72 Giờ",
        "codex_reasons": [
            "Gần gũi cực độ với khán giả Hàn Quốc (văn hóa 계모임 / hụi tín dụng dân gian) và có phóng sự điều tra dài kỳ trên CCTV 今日说法",
            "Minh họa hiệu ứng Domino toán học (SCALE_MULTIPLICATION & CRASH_TIMELINE) cực kỳ xuất sắc"
        ],
        "opening_hook": "이웃끼리 급전을 빌려쓰던 전통 계모임이 연 수익률 백 퍼센트가 넘는 거대한 도박판으로 변했습니다. 푸젠성 푸안시에서는 가정주부부터 공무원까지 도시 인구의 팔십 퍼센트가 계모임 장부에 이름을 올렸습니다. 그러던 어느 날 새벽, 가장 큰 계주 한 명이 사라지자 도시 전체의 시계가 멈춰 섰습니다.",
        "note": "【Hồ sơ vụ án: đại án dây hụi tín dụng ngầm 2,2 tỷ tệ cuốn phăng tiền tiết kiệm của cả một thành phố · chuỗi sụp đổ domino】 Hồ sơ thật 100% Đại án vỡ hụi ngầm (地下标会) trị giá hơn 2,2 tỷ NDT tại thành phố Phúc An, tỉnh Phúc Kiến (福建福安特大标会崩盘案, 2004–2006): Từ hình thức tương trợ vốn dân gian biến tướng thành mạng lưới đầu cơ lãi suất cao chồng chéo hàng trăm dây hụi, cuốn hơn 80% hộ dân thị xã vào vòng xoáy trước khi sụp đổ dây chuyền.",
        "hook_archetype": "cold_archive_match"
    },
    {
        "id": "fin_cn_heilongjiang_grain_loan_450m_russia",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "黑龙江农垦4.5亿元虚假大豆收储骗贷潜逃俄罗斯11年案 — 孙某 (2005–2016)",
        "archival_search_keywords_zh": [
            "黑龙江 4.5亿 粮食骗贷 潜逃俄罗斯",
            "猎狐行动 俄罗斯 押解 央视新闻",
            "虚假收储 骗贷 今日说法"
        ],
        "recommended_vox_verbs": [
            "LEDGER_DIFF_SCRUB",
            "GEO_VECTOR_PURSUIT",
            "SCALE_MULTIPLICATION"
        ],
        "title": "[중국 실화 사건] 장부 위 가짜 콩 10만 톤으로 은행 돈 4억 5천만 위안을 빌려 국경을 넘은 사나이 | 헤이룽장 유령 대두 사건 ([Vụ Án Có Thật ở Trung Quốc] Dùng 100.000 tấn đậu tương ma trên sổ sách vay 450 triệu tệ ngân hàng rồi vượt biên giới trốn 11 năm | Đại án đậu tương ma Hắc Long Giang)",
        "topic_anchor": "[중국 실화 사건] 장부 위 가짜 콩 10만 톤으로 은행 돈 4억 5천만 위안을 빌려 국경을 넘은 사나이 | 헤이룽장 유령 대두 사건",
        "winner_cluster": "Luồng 1 · 100.000 Tấn Đậu Tương Ma Trên Giấy Rút 450 Triệu Tệ & 11 Năm Trốn Ở Viễn Đông Nga (헤이룽장 4.5억 유령 곡물 사건)",
        "codex_score": 95,
        "profile_score": 95,
        "codex_angle": "Hồ Sơ Thật 100%: Chuyên Án Rút Ruột 450 Triệu NDT Vốn Thu Mua Nông Sản Hắc Long Giang & Cuộc Truy Bắt Xuyên Biên Giới Trung - Nga Suốt 11 Năm",
        "codex_reasons": [
            "Tư liệu Chiến dịch Săn Cáo (猎狐行动) phối hợp cảnh sát Nga dẫn độ qua cửa khẩu biên giới cực kỳ chân thực",
            "Khớp hoàn hảo LEDGER_DIFF_SCRUB & GEO_VECTOR_PURSUIT"
        ],
        "opening_hook": "서류 위에는 분명 십만 톤의 햇콩이 창고마다 가득 차 있었습니다. 국책은행은 그 수매 장부를 믿고 사억 오천만 위안의 정책 자금을 내주었지만, 실사단이 현장에 도착했을 때 창고는 텅 비어 있었고 사장은 이미 얼어붙은 국경 강을 건너 러시아로 사라진 뒤였습니다.",
        "note": "【Hồ sơ vụ án: đại án lập biên lai thu mua đậu tương khống lừa vay ngân hàng 450 triệu tệ rồi vượt biên trốn sang Nga suốt 11 năm】 Hồ sơ thật 100% Chuyên án lập khống hồ sơ thu mua 100.000 tấn đậu tương để rút ruột 450 triệu NDT vốn tín dụng nông nghiệp tại Hắc Long Giang rồi đào tẩu sang vùng Viễn Đông (Nga) suốt 11 năm (2005–2016) trước khi bị Tổ công tác Chiến dịch Săn Cáo (猎狐行动) phối hợp bắt giữ và dẫn độ về nước.",
        "hook_archetype": "micro_forensic_anomaly"
    },
    {
        "id": "fin_cn_shenzhen_citic_bill_450m_chen",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "深圳银行支行副行长4.5亿元空头商业汇票贴现潜逃东南亚14年案 — 陈某 (2001–2015)",
        "archival_search_keywords_zh": [
            "深圳 副行长 4.5亿 汇票 潜逃14年",
            "猎狐行动 银行副行长 押解 今日说法",
            "深圳 空头汇票 4.5亿"
        ],
        "recommended_vox_verbs": [
            "LEDGER_DIFF_SCRUB",
            "GEO_VECTOR_PURSUIT",
            "CONCENTRIC_TRAP"
        ],
        "title": "[중국 실화 사건] 금요일 마감 직전 4억 5천만 위안 무담보 어음을 승인하고 월요일 사라진 부지점장 | 선전 천 부행장 사건 ([Vụ Án Có Thật ở Trung Quốc] Ký duyệt 450 triệu tệ hối phiếu khống ngay trước giờ đóng cửa chiều thứ Sáu rồi biến mất sáng thứ Hai | Đại án Phó giám đốc ngân hàng Thâm Quyến)",
        "topic_anchor": "[중국 실화 사건] 금요일 마감 직전 4억 5천만 위안 무담보 어음을 승인하고 월요일 사라진 부지점장 | 선전 천 부행장 사건",
        "winner_cluster": "Luồng 1 · Ký Duyệt 450 Triệu Tệ Chiều Thứ Sáu & 14 Năm Trốn Truy Nã Kinh Tế Ở Đông Nam Á (선전 4.5억 어음 부행장 사건)",
        "codex_score": 95,
        "profile_score": 95,
        "codex_angle": "Hồ Sơ Thật 100%: Phó Giám Đốc Ngân Hàng Thâm Quyến Rút 450 Triệu NDT Trong 48 Giờ Cuối Tuần & 14 Năm Lẩn Trốn Trước Khi Sa Lưới Chiến Dịch Săn Cáo",
        "codex_reasons": [
            "Nhịp độ đếm ngược 48 giờ cuối tuần cực kỳ căng thẳng, chuẩn phong cách điều tra tài chính",
            "100% Xanh tiền YouTube"
        ],
        "opening_hook": "금요일 오후 네 시 반, 주말 동안 본점 감사가 멈추는 마흔여덟 시간의 공백을 노려 사억 오천만 위안짜리 어음 할인 서류에 승인 도장이 찍혔습니다. 월요일 아침 은행 문이 열렸을 때, 부지점장의 책상은 깨끗이 비워져 있었고 십사 년간의 국제 추격전이 시작되었습니다.",
        "note": "【Hồ sơ vụ án: đại án phó giám đốc chi nhánh ngân hàng ký chiết khấu hối phiếu khống 450 triệu tệ rồi trốn sang Đông Nam Á 14 năm】 Hồ sơ thật 100% Chuyên án Phó giám đốc chi nhánh ngân hàng tại Thâm Quyến cấu kết doanh nghiệp ngoài ký duyệt chiết khấu hối phiếu khống rút 450 triệu NDT ngay trước kỳ nghỉ cuối tuần rồi đào tẩu sang Đông Nam Á suốt 14 năm (2001–2015) trước khi bị bắt giữ trong Chiến dịch Săn Cáo.",
        "hook_archetype": "locked_room_vault_paradox"
    },
    {
        "id": "fin_cn_shaoxing_ningbo_xuli_22y",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "浙江宁波绿洲珠宝行·绍兴供销大厦系列持枪抢劫悬案22年侦破 — 徐利 (1995–2017)",
        "archival_search_keywords_zh": [
            "宁波绿洲珠宝行案 徐利 今日说法",
            "浙江第一悬案 徐利 天网",
            "绍兴供销大厦 22年 徐利"
        ],
        "recommended_vox_verbs": [
            "FORENSIC_ZOOM_CHAIN",
            "DUAL_ERA_LOCK",
            "BLIND_SPOT_REVEAL"
        ],
        "title": "[중국 실화 사건] 보석상 금고를 털고 22년간 완벽히 증발했던 특급 수배범이 평범한 가장으로 살아온 두 얼굴 | 저장성 쉬리 사건 ([Vụ Án Có Thật ở Trung Quốc] Hai bộ mặt của kẻ truy nã đặc biệt đột kích tiệm vàng rồi bốc hơi 22 năm dưới vỏ bọc người chủ gia đình bình lặng | Chuyên án Từ Lợi Chiết Giang)",
        "topic_anchor": "[중국 실화 사건] 보석상 금고를 털고 22년간 완벽히 증발했던 특급 수배범이 평범한 가장으로 살아온 두 얼굴 | 저장성 쉬리 사건",
        "winner_cluster": "Luồng 1 · Kỳ Án Số 1 Chiết Giang 22 Năm & Mảnh Vân Tay Mờ Trên Vỏ Đạn (저장성 제1현안 쉬리 사건)",
        "codex_score": 99,
        "profile_score": 99,
        "codex_angle": "Hồ Sơ Thật 100%: 'Án Treo Số 1 Chiết Giang' Từ Lợi (徐利, 1995–2017) — Phản Trinh Sát Cực Cao, Tự Chế Giảm Thanh Và 22 Năm Làm Người Chồng Hiền Lành Trước Khi Lộ Diện Ở Tiệm Billiards",
        "codex_reasons": [
            "Được Bộ Công an & Công an Chiết Giang gọi là 'Chiết Giang Đệ Nhất Huyền Án' (浙江第一悬案), cực nhiều tư liệu CCTV khám nghiệm, họp báo và thẩm vấn thật",
            "Đúng chuẩn 100% Xanh tiền: tập trung vào kỹ thuật phá khóa phản trinh sát, đối sánh 4 triệu bản vân tay suốt 22 năm và màn bắt giữ bất ngờ năm 2017"
        ],
        "opening_hook": "건물 외벽에 매달린 등산용 로프 한 줄, 그리고 현장에 버려진 정교하게 가공된 특수 공구. 1995년 닝보 최대 보석상을 털고 어둠 속으로 사라진 이 남자는 이후 22년 동안 중국 형사들이 가장 잡고 싶어 했던 '저장성 제1호 미제사건'의 유령이 되었습니다.",
        "note": "【Hồ sơ vụ án: đại án đột nhập tiệm vàng & trung tâm thương mại có vũ trang · tước đoạt sinh mạng 2 bảo vệ · án treo số 1 Chiết Giang suốt 22 năm】 Hồ sơ thật 100% 'Án treo số 1 Chiết Giang' (浙江宁波绿洲珠宝行12·6案 & 绍兴供销大厦案 — Hung thủ Từ Lợi 徐利, 1993–2017): Thực hiện 7 vụ đột nhập vũ trang siêu tinh vi không để lại mặt thật, treo thưởng 500.000 NDT suốt 22 năm; năm 2017 thuật toán vân tay thế hệ mới khớp được nửa dấu vân tay mờ năm 1998 ở Gia Hưng, bắt giữ Từ Lợi tại Lâm Hải (Thai Châu) ngày 29/3/2017.",
        "hook_archetype": "double_life_unmasking"
    },
    {
        "id": "fin_cn_zhengzhou_125_bank_siege",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "河南郑州12·5合作银行特大持枪抢劫案9个月侦破纪实 — 张书海 (1999–2000)",
        "archival_search_keywords_zh": [
            "郑州12·5大案 张书海 纪实",
            "张书海 抢劫银行 今日说法",
            "河南郑州 张书海 侦破"
        ],
        "recommended_vox_verbs": [
            "RADIAL_TIME_PRESSURE",
            "CONCENTRIC_TRAP",
            "FORENSIC_ZOOM_CHAIN"
        ],
        "title": "[중국 실화 사건] 단 5분 만에 은행 현금 208만 위안을 털어 사라진 주범이 수백억 대 기업 회장이 된 사연 | 정저우 12·5 은행 사건 ([Vụ Án Có Thật ở Trung Quốc] Kẻ chủ mưu cướp 2,08 triệu tệ ngân hàng chỉ trong 5 phút rồi bốc hơi thành chủ tịch tập đoàn trăm tỷ | Đại án 12·5 Trịnh Châu)",
        "topic_anchor": "[중국 실화 사건] 단 5분 만에 은행 현금 208만 위안을 털어 사라진 주범이 수백억 대 기업 회장이 된 사연 | 정저우 12·5 은행 사건",
        "winner_cluster": "Luồng 1 · Chuyên Án Phong Tỏa Toàn Thành Trịnh Châu & Truy Vết Vật Chứng Cơ Khí (정저우 12·5 장수하이 사건)",
        "codex_score": 98,
        "profile_score": 98,
        "codex_angle": "Hồ Sơ Thật 100%: Đại Án 12·5 Trịnh Châu — Trương Thư Hải (张书海) Dàn Dựng Tiếng Nổ Đánh Lạc Hướng Vòng Vây Cảnh Sát & Cuộc Truy Lùng Dấu Giày - Chiếc Búa Sắt Suốt 9 Tháng",
        "codex_reasons": [
            "Một trong những chuyên án truy vết vật chứng kinh điển nhất lịch sử hình sự Trung Quốc (phim tài liệu tư liệu gốc công an Hà Nam cực đầy đủ)",
            "Cấu trúc đấu trí chiến thuật giữa kế hoạch thoát thân 3 năm chuẩn bị của Trương Thư Hải và kỹ thuật truy nguyên chiếc búa sắt + đế giày Giải Phóng"
        ],
        "opening_hook": "도심 한복판 은행 창구의 강화유리가 특수 제작된 쇠망치 앞에서 단 5분 만에 무너졌습니다. 경찰 수만 명이 모든 외곽 도로를 봉쇄한 바로 그 밤, 주범 장수하이는 철길 위에서 교란 소음을 일으켜 수사대를 따돌린 뒤 시내 아파트 단지 속으로 연기처럼 스며들었습니다.",
        "note": "【Hồ sơ vụ án: đại án vũ trang đập kính chống đạn ngân hàng cướp 2,08 triệu tệ · đoạt mạng bảo vệ & trọng thương nhân viên · 9 tháng truy nguyên vật chứng】 Hồ sơ thật 100% Đại án 12·5 Ngân hàng Hợp tác Trịnh Châu, Hà Nam (郑州12·5特大银行劫案 — Chủ mưu Trương Thư Hải 张书海, 1999–2000): Lập kế hoạch suốt 3 năm, nổ mìn đường ray đánh lạc hướng cảnh sát để đi bộ ngay về căn hộ trong nội thành ẩn náu suốt 9 tháng trước khi ban chuyên án lần ra nguồn gốc chiếc búa tạ tự hàn và dấu vết thuốc nổ.",
        "hook_archetype": "chilling_verbatim_line"
    },
    {
        "id": "fin_cn_shenyang_38_serial_case",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "辽宁沈阳3·8特大持枪系列抢劫大案 — 孙德林·汪家礼·汪家仁 (1987–1999)",
        "archival_search_keywords_zh": [
            "沈阳3·8大案 纪实 孙德林",
            "辽宁沈阳 汪家礼 孙德林 侦破",
            "沈阳38大案 弹道 追踪"
        ],
        "recommended_vox_verbs": [
            "MICRO_TRACE_MATCH",
            "GEO_VECTOR_PURSUIT",
            "NETWORK_GRAPH"
        ],
        "title": "[중국 실화 사건] 12년간 현금수송차만 노리고 사라지던 복면 주범이 낮에는 시장 정육점 주인이었다니 | 선양 3·8 두 얼굴 사건 ([Vụ Án Có Thật ở Trung Quốc] Kẻ bịt mặt chuyên tập kích xe chở tiền suốt 12 năm hóa ra ban ngày lại là ông chủ sạp thịt ở chợ | Đại án 3·8 Thẩm Dương)",
        "topic_anchor": "[중국 실화 사건] 12년간 현금수송차만 노리고 사라지던 복면 주범이 낮에는 시장 정육점 주인이었다니 | 선양 3·8 두 얼굴 사건",
        "winner_cluster": "Luồng 1 · Chuyên Án Đạn Đạo 12 Năm & Vỏ Bọc Tiểu Thương Chợ Dân Sinh (선양 3·8 순더린 사건)",
        "codex_score": 97,
        "profile_score": 97,
        "codex_angle": "Hồ Sơ Thật 100%: Đại Án 3·8 Thẩm Dương (孙德林·汪家礼) — 12 Năm Soi Kính Hiển Vi Đường Khương Tuyến Vỏ Đạn Và Cú Đột Phá Từ Một Chiếc Xe Đạp Bỏ Lại Hiện Trường",
        "codex_reasons": [
            "Chuyên án số 1 vùng Đông Bắc Trung Quốc với hàng loạt phim tài liệu kỷ sự của Công an Thẩm Dương",
            "Tập trung 100% vào khoa học giám định đạn đạo (vết kim hỏa trên vỏ đạn) và truy nguyên số khung xe đạp qua hàng vạn hộ dân"
        ],
        "opening_hook": "12년 동안 선양 시내 곳곳에서 일어난 미제 사건 현장마다, 현미경 아래 똑같은 미세 긁힘 자국을 가진 금속 흔적이 발견되었습니다. 경찰 수천 명이 밤잠을 설치며 뒤쫓던 유령 조직의 우두머리는, 매일 아침 시장 골목에서 웃으며 고기를 썰던 평범한 상인이었습니다.",
        "note": "【Hồ sơ vụ án: đại án cướp xe chở tiền có vũ trang liên hoàn · tước đoạt 21 sinh mạng suốt 12 năm tại Thẩm Dương · ẩn mình dưới vỏ bọc tiểu thương chợ thịt】 Hồ sơ thật 100% Đại án '3·8 Thẩm Dương', Liêu Ninh (沈阳3·8特大系列案件 — Tôn Đức Lâm 孙德林, Uông Gia Lễ 汪家礼, 1987–1999): Ẩn mình dưới vỏ bọc người bán thịt lợn và tài xế tam mã suốt 12 năm, bị Công an Thẩm Dương giải mã nhờ giám định đường khương tuyến đạn đạo và truy vết chiếc xe đạp bỏ lại năm 1999.",
        "hook_archetype": "last_ordinary_routine"
    },
    {
        "id": "fin_cn_wuhan_121_wang_haijian",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "湖北武汉12·1建行关山一路支行爆炸抢劫案15天全城追缉 — 王海剑 (2011)",
        "archival_search_keywords_zh": [
            "武汉12·1爆炸案 王海剑 今日说法",
            "王海剑 建行 天网 纪实",
            "武汉关山一路 王海剑"
        ],
        "recommended_vox_verbs": [
            "BLIND_SPOT_REVEAL",
            "FORENSIC_ZOOM_CHAIN",
            "CONCENTRIC_TRAP"
        ],
        "title": "[중국 실화 사건] 현금수송차를 노리고 1,500개 CCTV를 완벽히 피해 달아난 고학력 설계범의 두 얼굴 | 우한 12·1 사건 ([Vụ Án Có Thật ở Trung Quốc] Hai bộ mặt của kẻ chủ mưu có học thức cao lập kế hoạch tập kích xe chở tiền rồi né sạch 1.500 camera | Chuyên án 12·1 Vũ Hán)",
        "topic_anchor": "[중국 실화 사건] 현금수송차를 노리고 1,500개 CCTV를 완벽히 피해 달아난 고학력 설계범의 두 얼굴 | 우한 12·1 사건",
        "winner_cluster": "Luồng 1 · 15 Ngày Đêm Giải Mã 1.500 Camera Vũ Hán & Manh Mối Vi Lượng Phòng Khám (우한 왕하이젠 사건)",
        "codex_score": 96,
        "profile_score": 96,
        "codex_angle": "Hồ Sơ Thật 100%: Vương Hải Kiếm (王海剑, Vũ Hán 12/2011) — Thợ Sửa Điện Tử IQ Cao Tự Chế Điều Khiển Từ Xa & Cách Cảnh Sát Nối Ngược 15.000 Giờ Băng Ghi Hình",
        "codex_reasons": [
            "Tư liệu video CCTV thực tế dày đặc bậc nhất (camera ngân hàng, giao lộ Vũ Hán, họp báo và bắt giữ tại bệnh viện)",
            "Cơ chế truy vết ngược hành trình xe máy không biển số cực kỳ cuốn hút cho bản đồ vệ tinh 2.5D & FORENSIC_ZOOM_CHAIN"
        ],
        "opening_hook": "번호판 없는 오토바이, 얼굴 전체를 가린 헬멧, 그리고 1,500개의 씨씨티비 사각지대를 외워버린 치밀한 동선. 우한 도심 은행 현금수송차 앞에서 완벽하게 도주한 줄 알았던 주범을 붙잡은 건, 뜻밖에도 작은 안과 병원에 남은 진료 영수증 한 장이었습니다.",
        "note": "【Hồ sơ vụ án: đại án kích nổ từ xa tấn công xe chở tiền ngân hàng · tước đoạt 2 sinh mạng, làm bị thương 15 người · 15 ngày truy ngược 1.500 camera tại Vũ Hán】 Hồ sơ thật 100% Chuyên án 12·1 đường Quan Sơn, Vũ Hán, Hồ Bắc (湖北武汉12·1特大爆炸劫案 — Vương Hải Kiếm 王海剑, 12/2011): Thợ sửa chữa điện tử tự nghiên cứu mạch kích nổ từ xa suốt 1 năm để tấn công xe chở tiền nhưng thất bại khi cướp hòm tiền, tháo chạy qua mạng lưới ngõ nhỏ và bị Công an Vũ Hán bắt gọn sau 15 ngày nhờ truy ngược video 1.500 camera kết hợp rà soát chấn thương mắt tại bệnh viện.",
        "hook_archetype": "chilling_verbatim_line"
    },
    {
        "id": "fin_cn_zhumadian_shi_erqun_16y",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "河南郑州1999年银行劫案主犯潜逃16年变身驻马店亿万富豪案 — 石二群 (1999–2015)",
        "archival_search_keywords_zh": [
            "石二群 16年 亿万富豪 今日说法",
            "郑州1999银行劫案 石二群 天网",
            "驻马店 石二群 落网"
        ],
        "recommended_vox_verbs": [
            "SPLIT_PARADOX",
            "DUAL_ERA_LOCK",
            "SCALE_MULTIPLICATION"
        ],
        "title": "[중국 실화 사건] 경비원을 쓰러뜨리고 은행에서 훔친 종잣돈으로 16년 뒤 수백억 대 부동산 재벌과 자선가가 된 수배범 | 스얼췬 두 얼굴 사건 ([Vụ Án Có Thật ở Trung Quốc] Dùng tiền cướp ngân hàng làm vốn mồi để 16 năm sau thành đại gia bất động sản và nhà từ thiện trăm tỷ | Hai bộ mặt của Thạch Nhị Quần)",
        "topic_anchor": "[중국 실화 사건] 경비원을 쓰러뜨리고 은행에서 훔친 종잣돈으로 16년 뒤 수백억 대 부동산 재벌과 자선가가 된 수배범 | 스얼췬 두 얼굴 사건",
        "winner_cluster": "Luồng 1 · Kẻ Cướp Ngân Hàng Dùng Tiền Tang Vật Xây Đế Chế Bất Động Sản Suốt 16 Năm (주마뎬 스얼췬 사건)",
        "codex_score": 98,
        "profile_score": 98,
        "codex_angle": "Hồ Sơ Thật 100%: Thạch Nhị Quần (石二群, 1999–2015) — Cướp 2,08 Triệu NDT Tại Trịnh Châu Rồi Về Trú Mã Điếm Đầu Tư Đất Đai Thành Tỷ Phú Trước Khi Lộ Diện Sau 16 Năm",
        "codex_reasons": [
            "Một trong những vụ án có nghịch lý xã hội lớn nhất lịch sử hình sự Trung Quốc, tư liệu phỏng vấn trực tiếp Thạch Nhị Quần trên CCTV cực kỳ sắc nét",
            "Khớp hoàn hảo SPLIT_PARADOX & SCALE_MULTIPLICATION"
        ],
        "opening_hook": "수백억 원대 아파트 단지와 호텔, 유치원을 거느린 지역의 존경받는 사업가이자 자선가 스얼췬. 하지만 그의 화려한 부동산 제국을 세운 최초의 종잣돈 백만 위안은, 십육 년 전 정저우의 한 은행 방탄유리를 깨부수고 훔쳐 달아난 강탈한 현금이었습니다.",
        "note": "【Hồ sơ vụ án: đại án cướp ngân hàng có vũ trang 2,08 triệu tệ · kẻ chủ mưu dùng tiền cướp được đầu tư bất động sản thành tỷ phú suốt 16 năm】 Hồ sơ thật 100% Vụ án Thạch Nhị Quần (石二群, Hà Nam, 1999–2015): Ngày 5/12/1999 chủ mưu vụ cướp Ngân hàng Hợp tác Trịnh Châu lấy hơn 2 triệu NDT, sau đó đem phần tiền chia được về Trú Mã Điếm mở công ty xây dựng và bất động sản, tích lũy khối tài sản hàng trăm triệu NDT suốt 16 năm trước khi Công an Trịnh Châu bắt giữ tháng 10/2015.",
        "hook_archetype": "double_life_unmasking"
    },
    {
        "id": "fin_cn_vault_torch_lei_guomin_9y",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "跨7省特大系列切割金库门大案侦破纪实 — 雷国民 (1992–2001)",
        "archival_search_keywords_zh": [
            "雷国民 切割金库 今日说法",
            "中国第一悍匪 雷国民 侦破纪实",
            "宿州农行金库案 雷国民"
        ],
        "recommended_vox_verbs": [
            "FORENSIC_ZOOM_CHAIN",
            "GEO_VECTOR_PURSUIT",
            "SINGLE_EVIDENCE_AUTOPSY"
        ],
        "title": "[중국 실화 사건] 9년간 7개 성 은행 금고만 산소절단기로 뚫고 흔적도 없이 사라지던 단독범의 정체 | 레이궈민 금고 사건 ([Vụ Án Có Thật ở Trung Quốc] Chân tướng kẻ độc hành suốt 9 năm dùng đèn khò cắt thủng két sắt ngân hàng xuyên 7 tỉnh không để lại dấu vết | Chuyên án Lôi Quốc Dân)",
        "topic_anchor": "[중국 실화 사건] 9년간 7개 성 은행 금고만 산소절단기로 뚫고 흔적도 없이 사라지던 단독범의 정체 | 레이궈민 금고 사건",
        "winner_cluster": "Luồng 1 · Kẻ Độc Hành Cắt Két Sắt Xuyên 7 Tỉnh & Giám Định Kỹ Thuật Hàn Kim Loại (레이궈민 금고 절단 사건)",
        "codex_score": 97,
        "profile_score": 97,
        "codex_angle": "Hồ Sơ Thật 100%: Lôi Quốc Dân (雷国民, 1992–2001) — Tự Nghiên Cứu Kết Cấu Thép Cửa Kho Bạc & Cách Chuyên Gia Pháp Y Đọc Vị Thói Quen Cầm Mỏ Hàn Tay Phải",
        "codex_reasons": [
            "Chuyên án giám định dấu vết công cụ cơ khí kinh điển của Bộ Công an Trung Quốc, có phim tài liệu kỷ sự chi tiết",
            "100% Xanh tiền: tập trung vào kỹ thuật phá khóa kho bạc và phân tích vật lý giọt xỉ hàn kim loại"
        ],
        "opening_hook": "두께 수십 센티미터의 강철 은행 금고 문이 마치 종이장처럼 둥글게 도려내져 있었습니다. 구 년 동안 일곱 개 성을 떠돌며 오직 금융기관 금고만을 노렸던 정체불명의 단독범. 베테랑 형사들은 금고 바닥에 떨어진 굳어버린 쇳물 방울의 각도에서 범인의 숨겨진 습관을 읽어냈습니다.",
        "note": "【Hồ sơ vụ án: đại án cướp kho bạc & cắt két sắt ngân hàng đẫm máu xuyên 7 tỉnh · hung thủ độc hành tước đoạt 20 sinh mạng suốt 9 năm · chuyên án bộ công an】 Hồ sơ thật 100% Chuyên án Lôi Quốc Dân (雷国民, An Huy, 1992–2001): Hoạt động độc lập cực kỳ kín tiếng xuyên 7 tỉnh, tự mua bình oxy-axetylen tập cắt các tấm thép dày để đột nhập kho bạc ngân hàng tại Túc Châu (An Huy) và Giang Tây; bị ban chuyên án Bộ Công an khoanh vùng nhờ phân tích kỹ thuật vết cắt kim loại và truy vết phương tiện năm 2001.",
        "hook_archetype": "micro_forensic_anomaly"
    },
    {
        "id": "fin_cn_wenxi_hou_jinliang_tombs",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "山西闻喜侯氏兄弟特大盗掘古墓葬黑社会性质组织案 — 侯金亮·侯金发 (2001–2018)",
        "archival_search_keywords_zh": [
            "山西闻喜 侯金亮 盗墓大案 央视",
            "闻喜特大盗墓案 今日说法",
            "侯氏四兄弟 文物大案 纪实"
        ],
        "recommended_vox_verbs": [
            "NETWORK_GRAPH",
            "SINGLE_EVIDENCE_AUTOPSY",
            "CONCENTRIC_TRAP"
        ],
        "title": "[중국 실화 사건] 밤마다 땅속에서 울리던 폭발음 뒤로 3,000년 전 국보 수백 점을 삼킨 지하 제국의 실체 | 산시성 원시현 도굴 대사건 ([Vụ Án Có Thật ở Trung Quốc] Sự thật đế chế ngầm nuốt chửng hàng trăm quốc bảo 3.000 năm tuổi sau những tiếng nổ trầm đục mỗi đêm | Đại án trộm mộ Văn Hỷ Sơn Tây)",
        "topic_anchor": "[중국 실화 사건] 밤마다 땅속에서 울리던 폭발음 뒤로 3,000년 전 국보 수백 점을 삼킨 지하 제국의 실체 | 산시성 원시현 도굴 대사건",
        "winner_cluster": "Luồng 1 · Chuyên Án Quốc Bảo Cấp 1 Sơn Tây & Chiến Dịch Thu Hồi Hàng Nghìn Cổ Vật (산시성 원시현 허우진량 사건)",
        "codex_score": 96,
        "profile_score": 96,
        "codex_angle": "Hồ Sơ Thật 100%: Đại Án Anh Em Họ Hầu Tại Văn Hỷ, Sơn Tây (山西闻喜侯金亮特大文物案) — Bóc Gỡ Mạng Lưới Phân Chia 'Lãnh Địa Ngầm' & Thu Hồi Hơn 3.000 Cổ Vật Nhà Chu - Nhà Thương",
        "codex_reasons": [
            "Chuyên án hình sự bảo vệ di sản lớn nhất lịch sử Bộ Công an Trung Quốc (thu hồi hơn 3.000 cổ vật, trong đó có 225 cổ vật quốc bảo cấp 1), phim tài liệu CCTV cực kỳ hoành tráng",
            "100% Xanh tiền YouTube: không có án mạng máu me, kịch tính cao độ với kỹ thuật thăm dò lòng đất và đấu trí phá vỡ 'chiếc ô bảo kê'"
        ],
        "opening_hook": "삼천 년 전 고대 국가의 왕족 무덤들이 잠들어 있는 산시성 원시현의 들판. 밤이 깊어지면 마을 사람들의 창문을 흔드는 정체불명의 둔탁한 진동이 땅속에서 올라왔습니다. 특별수사팀이 비밀 거래 장부를 압수했을 때, 박물관에도 없는 일급 국보 수백 점이 지하 암시장을 통해 빠져나간 흔적이 드러났습니다.",
        "note": "【Hồ sơ vụ án: đại án băng nhóm ngầm thăm dò và đào trộm hơn 3.000 cổ vật quốc bảo suốt 10 năm · chuyên án 6·03 bộ công an thu hồi 225 quốc bảo cấp 1】 Hồ sơ thật 100% Chuyên án 6·03 tại huyện Văn Hỷ, thành phố Vận Thành, tỉnh Sơn Tây (山西闻喜侯氏兄弟特大盗掘古墓案 — Hầu Kim Lượng 侯金亮, Hầu Kim Phát 侯金发, phá án 2016–2018): Tổ chức băng nhóm độc점 thăm dò và đào trộm khu mộ cổ thời Thương - Chu suốt hơn 10 năm, bị Bộ Công an chỉ đạo chuyên án bắt giữ 475 đối tượng và thu hồi hơn 3.000 cổ vật quý hiếm.",
        "hook_archetype": "chilling_verbatim_line"
    },
    {
        "id": "fin_cn_changde_91_zhang_jun",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "渝湘鄂跨省特大持枪抢劫运钞车案9·1常德大案侦破 — 张君 (1991–2000)",
        "archival_search_keywords_zh": [
            "常德9·1大案 张君 侦破纪实",
            "张君 湖南常德 庭审 央视",
            "重庆警方 抓捕张君 纪实"
        ],
        "recommended_vox_verbs": [
            "CONCENTRIC_TRAP",
            "NETWORK_GRAPH",
            "GEO_VECTOR_PURSUIT"
        ],
        "title": "[중국 실화 사건] 8년간 현금수송차와 금고를 털며 전국을 뒤흔든 공안부 1호 수배범의 치밀한 이중생활 | 창더 9·1 장쥔 사건 ([Vụ Án Có Thật ở Trung Quốc] Cuộc sống hai mặt tinh vi của kẻ truy nã số 1 Bộ Công an chuyên tập kích xe chở tiền và kho bạc suốt 8 năm | Đại án 9·1 Thường Đức Trương Quân)",
        "topic_anchor": "[중국 실화 사건] 8년간 현금수송차와 금고를 털며 전국을 뒤흔든 공안부 1호 수배범의 치밀한 이중생활 | 창더 9·1 장쥔 사건",
        "winner_cluster": "Luồng 1 · Chuyên Án Lớn Nhất Năm 2000 Xuyên Hồ Nam - Hồ Bắc - Trùng Khánh (창더 9·1 장쥔 사건)",
        "codex_score": 97,
        "profile_score": 97,
        "codex_angle": "Hồ Sơ Thật 100%: Chuyên Án Trương Quân (张君, 1991–2000) — Cách Ban Chuyên Án Bộ Công An Giải Mã Mạng Lưới Liên Lạc Một Chiều & Phục Kích Bắt Sống Tại Trùng Khánh Đêm 19/9/2000",
        "codex_reasons": [
            "Một trong những chuyên án hình sự lớn nhất lịch sử Trung Quốc với kho tư liệu truyền hình cực lớn về cuộc họp báo Bộ Công an, bắt giữ tại Trùng Khánh và xét xử năm 2001",
            "100% Xanh tiền: tập trung vào kỹ thuật phân tích cước viễn thông, đạn đạo học và kế hoạch vây bắt không nổ súng đêm 19/9/2000"
        ],
        "opening_hook": "다섯 개의 서로 다른 이름과 호적을 번갈아 쓰며 8년 동안 세 개 성을 오가던 유령 같은 주범 장쥔. 창더시 은행 현금수송차 탈취 사건 직후, 특별수사팀은 수만 건의 통화 기록 속에서 단 한 번 스쳐 지나간 비밀 연락망 하나를 포착했습니다.",
        "note": "【Hồ sơ vụ án: đại án cướp xe chở tiền & kho bạc có vũ trang đặc biệt nguy hiểm · tước đoạt 28 sinh mạng, làm bị thương 22 người xuyên 3 tỉnh · truy nã cấp A số 1 bộ công an】 Hồ sơ thật 100% Đại án 9·1 Thường Đức và chuyên án Trương Quân (张君湘鄂渝系列特大持枪抢劫案, 1991–2000): Sau vụ tấn công xe chở tiền tại Thường Đức (Hồ Nam) ngày 1/9/2000, Bộ Công an huy động lực lượng 3 tỉnh lần theo dấu vết viễn thông và kho vũ khí ngầm, phục kích bắt sống Trương Quân tại Trùng Khánh đêm 19/9/2000.",
        "hook_archetype": "double_life_unmasking"
    },
    {
        "id": "fin_cn_yingkou_lixuyi_8h_armored",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "辽宁营口大石桥9·7押运员劫持3500万运钞车8小时追捕案 — 李绪义 (2016)",
        "archival_search_keywords_zh": [
            "营口 李绪义 运钞车 今日说法",
            "大石桥 3500万 运钞车劫案 央视新闻",
            "李绪义 8小时 庭审"
        ],
        "recommended_vox_verbs": [
            "RADIAL_TIME_PRESSURE",
            "GEO_VECTOR_PURSUIT",
            "LEDGER_DIFF_SCRUB"
        ],
        "title": "[중국 실화 사건] 현금 3,500만 위안 실린 장갑차를 몰고 사라져 8시간 동안 빚만 갚고 다닌 수송대장 | 잉커우 리쉬이 사건 ([Vụ Án Có Thật ở Trung Quốc] Lái chiếc xe bọc thép chở 35 triệu tệ biến mất rồi suốt 8 giờ chỉ đi trả nợ từng nơi | Chuyên án Lý Tự Nghĩa Dinh Khẩu)",
        "topic_anchor": "[중국 실화 사건] 현금 3,500만 위안 실린 장갑차를 몰고 사라져 8시간 동안 빚만 갚고 다닌 수송대장 | 잉커우 리쉬이 사건",
        "winner_cluster": "Luồng 1 · 8 Giờ Nghẹt Thở Truy Lùng Tài Xế Xe Bọc Thép Mang 6 Triệu Tệ Đi Trả Nợ (잉커우 리쉬이 8시간 사건)",
        "codex_score": 97,
        "profile_score": 97,
        "codex_angle": "Hồ Sơ Thật 100%: Lý Tự Nghĩa (李绪义, Liêu Ninh 7/9/2016) — Vì Sao Đội Trưởng Xe Chở Tiền Không Bỏ Trốn Ra Nước Ngoài Mà Chạy Thẳng Tới Quầy ATM Ngân Hàng Gửi Tiền Trả Nợ?",
        "codex_reasons": [
            "Tư liệu camera quầy ngân hàng và video bắt giữ thực tế cực kỳ rõ nét trên CCTV",
            "100% Xanh tiền YouTube: không một ai bị thương, cấu trúc 8 giờ đếm ngược theo từng điểm trả nợ cực hợp RADIAL_TIME_PRESSURE & GEO_VECTOR_PURSUIT"
        ],
        "opening_hook": "삼천오백만 위안의 현금 상자를 실은 은행 장갑차가 갑자기 정해진 노선을 벗어났습니다. 현금 자루에 육백만 위안을 담아 달아난 운전수 리쉬이. 그런데 경찰이 도주로를 차단하는 사이, 그가 가장 먼저 달려간 곳은 국경이나 산속이 아니라 뜻밖에도 동네 은행의 무인 입금기 앞이었습니다.",
        "note": "【Hồ sơ vụ án: chuyên án đội trưởng áp tải khống chế xe bọc thép chở 35 triệu tệ lấy 6 triệu tệ rồi suốt 8 giờ đi gửi ATM trả nợ từng người】 Hồ sơ thật 100% Vụ án Lý Tự Nghĩa tại Đại Thạch Kiều, Dinh Khẩu, Liêu Ninh ngày 7/9/2016 (辽宁营口大石桥9·7运钞车劫案 — 李绪义): Do bị chủ đầu tư nợ tiền công trình dẫn đến nợ nần chồng chất, tài xế xe chở tiền Lý Tự Nghĩa đã khống chế xe lấy đi 6 triệu NDT tiền mặt rồi suốt 8 giờ đi gửi tiền vào tài khoản các chủ nợ trước khi bị bắt giữ mà không gây thương vong.",
        "hook_archetype": "locked_room_vault_paradox"
    },
    {
        "id": "fin_cn_kekexili_gold_zhang_xianming_25y",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "青海可可西里1995年48公斤黄金特大劫案潜逃25年侦破案 — 张显明 (1995–2020)",
        "archival_search_keywords_zh": [
            "青海 48公斤黄金 张显明 今日说法",
            "潜逃25年 黄金大案 天网",
            "张显明 洛阳 研究院 落网"
        ],
        "recommended_vox_verbs": [
            "DUAL_ERA_LOCK",
            "GEO_VECTOR_PURSUIT",
            "SPLIT_PARADOX"
        ],
        "title": "[중국 실화 사건] 고원 금광에서 순금 48kg을 강탈해 증발한 수배범이 25년간 모범 연구원장으로 살아온 사연 | 커커시리 장셴밍 사건 ([Vụ Án Có Thật ở Trung Quốc] Kẻ truy nã cướp 48kg vàng ròng trên cao nguyên rồi ẩn mình suốt 25 năm làm Viện trưởng nghiên cứu mẫu mực | Chuyên án Trương Hiển Minh)",
        "topic_anchor": "[중국 실화 사건] 고원 금광에서 순금 48kg을 강탈해 증발한 수배범이 25년간 모범 연구원장으로 살아온 사연 | 커커시리 장셴밍 사건",
        "winner_cluster": "Luồng 1 · 48kg Vàng Ròng Cao Nguyên Thanh Hải & 25 Năm Ẩn Mình Làm Viện Trưởng Nghiên Cứu (커커시리 48kg 황금 장셴밍 사건)",
        "codex_score": 98,
        "profile_score": 98,
        "codex_angle": "Hồ Sơ Thật 100%: Trương Hiển Minh (张显明, 1995–2020) — Từ Vụ Cướp 48kg Vàng Ròng Trên Cao Nguyên Thanh Hải Đến 25 Năm Mang Tên Giả 'Trương Quốc Chính' Làm Chuyên Gia Kỹ Thuật Tại Lạc Dương",
        "codex_reasons": [
            "Một trong những chuyên án truy bắt 25 năm chấn động nhất năm 2020 trên CCTV 今日说法",
            "Nghịch lý hai mặt cực đại cho DUAL_ERA_LOCK: kẻ cướp 48kg vàng biến thành kỹ sư trưởng được đồng nghiệp kính trọng suốt 1/4 thế kỷ"
        ],
        "opening_hook": "해발 사천 미터 고원 도로에서 사십팔 킬로그램의 순금 괴가 사라진 지 25년. 모두가 주범 장셴밍이 이미 세상을 떠났거나 해외로 밀항했을 것이라 여겼습니다. 그러나 2020년 경찰이 뤄양시의 한 중견 기술 연구소 문을 열었을 때, 백발이 성성한 모범 연구원장이 조용히 고개를 떨구었습니다.",
        "note": "【Hồ sơ vụ án: trọng án đoạt mạng chủ mỏ vàng & cướp 48kg vàng ròng tại Khả Khả Tây Lý · tẩy trắng thân phận làm viện trưởng nghiên cứu suốt 25 năm】 Hồ sơ thật 100% Chuyên án cướp 48kg vàng ròng tại Thanh Hải năm 1995 (青海1995年11·15特大黄金案 — Trương Hiển Minh 张显明, phá án năm 2020): Sau khi tham gia cướp 48kg vàng nguyên chất, Trương Hiển Minh tẩy trắng hộ khẩu dưới tên 'Trương Quốc Chính' (张国政), học nghề kỹ thuật và leo lên vị trí quản lý viện nghiên cứu doanh nghiệp tại Lạc Dương (Hà Nam) suốt 25 năm trước khi bị bắt giữ.",
        "hook_archetype": "double_life_unmasking"
    },
    {
        "id": "fin_cn_kaifeng_museum_liunongjun_69",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "河南开封博物馆9·18特大69件国宝被盗案侦破纪实 — 刘农军 (1992–1993)",
        "archival_search_keywords_zh": [
            "开封博物馆 9·18大案 刘农军 纪实",
            "69件国宝 被盗 刘农军 今日说法",
            "河南开封 文物大案 侦破"
        ],
        "recommended_vox_verbs": [
            "BLIND_SPOT_REVEAL",
            "FORENSIC_ZOOM_CHAIN",
            "CONCENTRIC_TRAP"
        ],
        "title": "[중국 실화 사건] 적외선 경보기를 붉은 천 하나로 무력화하고 황실 국보 69점을 증발시킨 경찰대 출신 주범 | 카이펑 박물관 류눙쥔 사건 ([Vụ Án Có Thật ở Trung Quốc] Dùng 1 tấm vải đỏ vô hiệu hóa cảm biến hồng ngoại, lấy cắp 69 quốc bảo hoàng cung của gã cựu sinh viên cảnh sát | Đại án Bảo tàng Khai Phong)",
        "topic_anchor": "[중국 실화 사건] 적외선 경보기를 붉은 천 하나로 무력화하고 황실 국보 69점을 증발시킨 경찰대 출신 주범 | 카이펑 박물관 류눙쥔 사건",
        "winner_cluster": "Luồng 1 · Tấm Vải Đỏ Che Mắt Cảm Biến Hồng Ngoại & Đại Án 69 Quốc Bảo Khai Phong (카이펑 박물관 69점 국보 사건)",
        "codex_score": 98,
        "profile_score": 98,
        "codex_angle": "Hồ Sơ Thật 100%: Lưu Nông Quân & Đại Án 9·18 Bảo Tàng Khai Phong (开封博物馆69件国宝大案) — Cựu Sinh Viên Trường Cảnh Sát Dùng Kiến Thức Phản Trinh Sát Đột Nhập Phòng Trưng Bày Trong Đêm Mưa",
        "codex_reasons": [
            "Vụ trộm bảo tàng lớn nhất lịch sử Trung Quốc hiện đại (được xếp ngang hàng các vụ trộm bảo tàng Louvre), có hàng loạt phim tài liệu kỷ sự của Bộ Công an",
            "100% Xanh tiền YouTube: không có bạo lực máu me, 100% là màn đấu trí kỹ thuật hình sự cực đỉnh"
        ],
        "opening_hook": "최첨단 적외선 감지기 네 대가 스물네 시간 가동되던 박물관 전시실. 하지만 비가 쏟아지던 1992년 9월 18일 밤, 경보기는 단 한 번도 울리지 않았고 유리 진열장 속 황실 도자기와 국보 예순아홉 점이 감쪽같이 사라졌습니다. 감지기 앞에는 정체불명의 붉은 천 조각만이 걸려 있었습니다.",
        "note": "【Hồ sơ vụ án: đại án trộm bảo tàng lớn nhất lịch sử Trung Quốc · cựu sinh viên cảnh sát dùng vải đỏ che cảm biến hồng ngoại lấy 69 quốc bảo hoàng cung】 Hồ sơ thật 100% Đại án 9·18 tại Bảo tàng Khai Phong, Hà Nam (河南开封博物馆69件馆藏文物被盗案 — Chủ mưu Lưu Nông Quân 刘农军, 1992–1993): Từng theo học Học viện Cảnh sát Nhân dân Vũ Hán nên nắm rõ nguyên lý bước sóng hồng ngoại, Lưu Nông Quân dùng vải nhung đỏ che cảm biến lấy đi 69 quốc bảo nhà Minh - Thanh; Ban chuyên án đã truy vết từ mảnh tem nhãn và chiếc xe桑塔纳 trắng, thu hồi toàn bộ 69 quốc bảo tại Macau & Vũ Hán.",
        "hook_archetype": "double_life_unmasking"
    },
    {
        "id": "fin_cn_qianjiang_xiexianrong_15d_boat",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "湖北潜江9·29工商银行运钞车劫案公安部A级通缉15天汉江围捕 — 谢先荣 (2003)",
        "archival_search_keywords_zh": [
            "湖北潜江 谢先荣 9·29 今日说法",
            "A级通缉犯 谢先荣 汉江 纪实",
            "潜江运钞车大案 侦破"
        ],
        "recommended_vox_verbs": [
            "FORENSIC_ZOOM_CHAIN",
            "GEO_VECTOR_PURSUIT",
            "CONCENTRIC_TRAP"
        ],
        "title": "[중국 실화 사건] 현금수송차 35만 위안을 털고 강물 속 어선으로 숨어든 공안부 A급 수배범의 도주 행적 | 첸장 세셴룽 사건 ([Vụ Án Có Thật ở Trung Quốc] Hành tung kẻ truy nã cấp A tập kích xe chở tiền 350.000 tệ rồi lẩn trốn xuống thuyền cá trên sông | Chuyên án Tạ Tiên Vinh)",
        "topic_anchor": "[중국 실화 사건] 현금수송차 35만 위안을 털고 강물 속 어선으로 숨어든 공안부 A급 수배범의 도주 행적 | 첸장 세셴룽 사건",
        "winner_cluster": "Luồng 1 · Truy Nguyên Vết Sơn Xe Tải & 15 Ngày Đêm Phong Tỏa Dòng Sông Hán Giang (후베이 첸장 세셴룽 사건)",
        "codex_score": 96,
        "profile_score": 96,
        "codex_angle": "Hồ Sơ Thật 100%: Chuyên Án 9·29 Tiềm Giang, Hồ Bắc — Tạ Tiên Vinh (谢先荣, 2003) — Cách Chuyên Gia Pháp Y Lần Ra Danh Tính Chủ Xe Từ Số Khung Bị Mài Mòn Bằng Dung Dịch Hóa Học",
        "codex_reasons": [
            "Chuyên án khoa học hình sự kinh điển của Bộ Công an Trung Quốc năm 2003 (phục hồi số khung động cơ bị mài xóa bằng phản ứng ăn mòn kim loại)",
            "100% Xanh tiền YouTube: tập trung vào giám định hóa học kim loại và cuộc vây bắt trên sông Hán Giang"
        ],
        "opening_hook": "범인이 버리고 간 흰색 승합차의 엔진 번호와 차대 번호는 줄칼로 깊게 갈려 나가 글자 하나 읽을 수 없었습니다. 하지만 기술 감식반이 금속 표면에 특수 화학 시약을 바르자, 지워졌던 일련번호가 마법처럼 다시 떠올랐고 수배범 세셴룽의 그림자가 드러났습니다.",
        "note": "【Hồ sơ vụ án: đại án cướp xe chở tiền ngân hàng đặc biệt nguy hiểm · tước đoạt 5 sinh mạng (4 nhân viên giải ngân & 1 cảnh sát hình sự) · lệnh truy nã cấp A bộ công an】 Hồ sơ thật 100% Chuyên án 9·29 tại Tiềm Giang, Hồ Bắc (湖北潜江9·29大案 — Tạ Tiên Vinh 谢先荣, 9–10/2003): Hung thủ bỏ lại chiếc xe tải nhỏ đã đục xóa toàn bộ số khung số máy; chuyên gia kỹ thuật hình sự dùng phương pháp ăn mòn điện hóa phục hồi dãy số gốc, xác định danh tính Tạ Tiên Vinh và phát lệnh truy nã cấp A toàn quốc, vây bắt trên sông Hán Giang sau 15 ngày.",
        "hook_archetype": "micro_forensic_anomaly"
    },
    {
        "id": "fin_cn_xinji_zhaozhiyong_court_22y",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "河北辛集1997年运钞车劫案主犯潜逃22年变身法院执行局副局长案 — 赵志勇 (1997–2019)",
        "archival_search_keywords_zh": [
            "河北辛集 运钞车 法院副局长 赵志勇",
            "抢运钞车 22年 法院执行局 今日说法",
            "辛集1997运钞车案 侦破"
        ],
        "recommended_vox_verbs": [
            "SPLIT_PARADOX",
            "DUAL_ERA_LOCK",
            "MICRO_TRACE_MATCH"
        ],
        "title": "[중국 실화 사건] 현금수송차 79만 위안을 털고 사라진 수배범이 22년간 그 도시 법원 부국장으로 앉아 있었다 | 신지시 자오즈용 사건 ([Vụ Án Có Thật ở Trung Quốc] Kẻ chủ mưu cướp 790.000 tệ xe chở tiền rồi bốc hơi nhưng suốt 22 năm vẫn ngồi ghế Phó cục trưởng Tòa án thành phố đó | Chuyên án Triệu Trí Dũng)",
        "topic_anchor": "[중국 실화 사건] 현금수송차 79만 위안을 털고 사라진 수배범이 22년간 그 도시 법원 부국장으로 앉아 있었다 | 신지시 자오즈용 사건",
        "winner_cluster": "Luồng 1 · Kẻ Cướp Xe Chở Tiền Ngồi Ngay Ghế Phó Cục Trưởng Thi Hành Án Tòa Án Suốt 22 Năm (허베이 신지시 자오즈용 사건)",
        "codex_score": 99,
        "profile_score": 99,
        "codex_angle": "Hồ Sơ Thật 100%: Triệu Trí Dũng (赵志勇, Tân Tập, Hà Bắc 1997–2019) — Ban Ngày Ngồi Ghế Tòa Án Ký Lệnh Cưỡng Chế, Ban Đêm Giấu Kín Bí Mật Vụ Cướp Xe Chở Tiền 22 Năm Trước",
        "codex_reasons": [
            "Đỉnh cao của nghịch lý thân phận (SPLIT_PARADOX): thủ phạm vụ cướp xe chở tiền ngân hàng không hề bỏ trốn đi xa mà vẫn làm việc ngay trong Tòa án địa phương và thăng chức lên Phó cục trưởng Cục Thi hành án!",
            "Bản tin chính thức của Công an Thạch Gia Trang và CCTV năm 2019–2020 cực kỳ chấn động"
        ],
        "opening_hook": "현금수송차에서 79만 위안이 사라진 뒤 형사들이 22년 동안 전국을 뒤지며 범인을 쫓고 있었습니다. 누구도 상상하지 못했지만, 그 사건의 주범 자오즈용은 바로 그 도시의 법원 청사 안에서 집행국 부국장 직함을 달고 매일 아침 판결 집행 서류에 도장을 찍고 있었습니다.",
        "note": "【Hồ sơ vụ án: trọng án tấn công xe chở tiền đoạt mạng người & cướp 790.000 tệ · thủ phạm ẩn mình làm phó cục trưởng cục thi hành án tòa án suốt 22 năm】 Hồ sơ thật 100% Kỳ án cướp xe chở tiền năm 1997 tại thành phố Tân Tập, Thạch Gia Trang, Hà Bắc (河北辛集1997年12·2运钞车劫案 — Chủ mưu Triệu Trí Dũng 赵志勇, phá án tháng 8/2019): Triệu Trí Dũng vốn là nhân viên tòa án đã rủ đồng bọn cướp 790.000 NDT của xe chở tiền rồi tiếp tục đi làm bình thường, leo lên chức Phó cục trưởng Cục Thi hành án Tòa án suốt 22 năm trước khi công nghệ giám định sinh trắc học mới lật tẩy toàn bộ băng nhóm.",
        "hook_archetype": "double_life_unmasking"
    },
    {
        "id": "fin_cn_beijing_palace_museum_shibaikui_58h",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "北京故宫博物院9件皇室珍宝被盗58小时极速侦破案 — 石柏魁 (2011)",
        "archival_search_keywords_zh": [
            "故宫被盗案 石柏魁 58小时 今日说法",
            "2011 故宫失窃案 侦破纪实 央视",
            "石柏魁 故宫 庭审"
        ],
        "recommended_vox_verbs": [
            "BLIND_SPOT_REVEAL",
            "RADIAL_TIME_PRESSURE",
            "FORENSIC_ZOOM_CHAIN"
        ],
        "title": "[중국 실화 사건] 수백 대 카메라와 4중 경비를 뚫고 자금성 황실 보물 9점을 훔친 남자의 어이없는 실수 | 고궁박물원 도난 사건 ([Vụ Án Có Thật ở Trung Quốc] Vượt qua hàng trăm camera và 4 lớp bảo vệ lấy cắp 9 báu vật Tử Cấm Thành cùng sai lầm khó tin của thủ phạm | Đại án Cố Cung Bắc Kinh)",
        "topic_anchor": "[중국 실화 사건] 수백 대 카메라와 4중 경비를 뚫고 자금성 황실 보물 9점을 훔친 남자의 어이없는 실수 | 고궁박물원 도난 사건",
        "winner_cluster": "Luồng 1 · 58 Giờ Truy Bắt Kẻ Đột Nhập Tử Cấm Thành Giữa Đêm Mưa Gió (베이징 자금성 고궁박물원 도난 사건)",
        "codex_score": 97,
        "profile_score": 97,
        "codex_angle": "Hồ Sơ Thật 100%: Thạch Bách Khuê & Vụ Trộm Tử Cấm Thành Năm 2011 (北京故宫博物院被盗案, 5/2011) — Ẩn Nấp Trong Cố Cung Sau Giờ Đóng Cửa Và Dấu Vân Tay Để Lại Quán Internet",
        "codex_reasons": [
            "Vụ án chấn động cả thế giới năm 2011 (lần đầu tiên sau hơn 20 năm Tử Cấm Thành bị đột nhập), tư liệu CCTV và sơ đồ 3D Cố Cung cực kỳ hấp dẫn",
            "100% Xanh tiền YouTube: không bạo lực, kịch tính cao độ với sơ đồ kiến trúc Tử Cấm Thành và 58 giờ truy bắt"
        ],
        "opening_hook": "일 년에 천만 명이 찾고 수백 대의 적외선 센서와 네 겹의 경비망이 지키는 세계 최대의 궁궐 자금성. 비바람이 몰아치던 밤 전시장 안쪽 벽이 뚫리고 황실 보물 아홉 점이 감쪽같이 사라지자, 베이징 경찰의 58시간 초비상 추격전이 시작됐습니다.",
        "note": "【Hồ sơ vụ án: đại án đột nhập Tử Cấm Thành (Cố Cung) vượt 4 lớp bảo vệ lấy cắp 9 báu vật hoàng cung · 58 giờ truy bắt từ dấu vân tay quán net】 Hồ sơ thật 100% Chuyên án 58 giờ phá vụ trộm 9 báu vật tại Bảo tàng Cố Cung (Tử Cấm Thành), Bắc Kinh ngày 8/5/2011 (北京故宫博物院5·8被盗案 — Thạch Bách Khuê 石柏魁): Lợi dụng lúc mưa to để trốn lại trong hốc tường Cố Cung sau giờ đóng cửa, ngắt nguồn điện phòng trưng bày lấy đi 9 hộp báu vật dát vàng nạm ngọc rồi trèo mái trốn thoát; Công an Bắc Kinh khoanh vùng dấu vết và bắt giữ Thạch Bách Khuê tại một quán Internet sau 58 giờ.",
        "hook_archetype": "countdown_system_breach"
    },
    {
        "id": "fin_cn_wuxi_bank_half_fingerprint_21y",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "江苏无锡1998年储蓄所悬案21年半枚残缺指纹锁定真凶案 — 邓某 (1998–2019)",
        "archival_search_keywords_zh": [
            "无锡 21年 半枚指纹 今日说法",
            "江苏无锡 1998 储蓄所 侦破 天网",
            "半枚指纹 21年 追凶"
        ],
        "recommended_vox_verbs": [
            "FORENSIC_ZOOM_CHAIN",
            "MICRO_TRACE_MATCH",
            "DUAL_ERA_LOCK"
        ],
        "title": "[중국 실화 사건] 은행 창구를 털고 증발한 남자가 21년 동안 존경받는 모범 기업 사장으로 살아온 두 얼굴 | 우시 21년 미제사건 ([Vụ Án Có Thật ở Trung Quốc] Hai bộ mặt của kẻ cướp quầy giao dịch ngân hàng rồi bốc hơi 21 năm dưới vỏ bọc ông chủ doanh nghiệp mẫu mực | Kỳ án 21 năm Vô Tích)",
        "topic_anchor": "[중국 실화 사건] 은행 창구를 털고 증발한 남자가 21년 동안 존경받는 모범 기업 사장으로 살아온 두 얼굴 | 우시 21년 미제사건",
        "winner_cluster": "Luồng 1 · Nửa Dấu Vân Tay Mờ Lưu Trữ 21 Năm & 3 Triệu Bản Đối Sánh Thủ Công (장쑤 우시 반쪽 지문 21년 사건)",
        "codex_score": 96,
        "profile_score": 96,
        "codex_angle": "Hồ Sơ Thật 100%: Kỳ Án Quầy Tiết Kiệm Vô Tích 21 Năm (江苏无锡21年半枚指纹破案纪实, 1998–2019) — Khi Thuật Toán Khôi Phục Đường Vân Thế Hệ Mới Khớp Trúng 11 Điểm Đặc Trưng",
        "codex_reasons": [
            "Phóng sự khoa học hình sự tiêu biểu trên CCTV 今日说法 về sự kiên trì của các chuyên gia vân tay suốt 21 năm",
            "100% Xanh tiền YouTube, cực hợp FORENSIC_ZOOM_CHAIN & MICRO_TRACE_MATCH"
        ],
        "opening_hook": "사건 현장의 유리창 위에 남겨진 것은 절반 이상이 뭉개져 특징점이 일곱 개밖에 보이지 않는 반쪽짜리 지문 하나였습니다. 21년 동안 형사들이 눈이 짓무르도록 삼백만 장의 지문 카드를 대조한 끝에, 마침내 알고리즘 화면 위에서 열한 개의 붉은 일치점이 반짝였습니다.",
        "note": "【Hồ sơ vụ án: kỳ án đột nhập phòng giao dịch tiết kiệm tại Vô Tích · 21 năm đối chiếu 3 triệu bản vân tay từ nửa dấu vân tay mờ lật tẩy ông chủ doanh nghiệp】 Hồ sơ thật 100% Kỳ án 21 năm tại Vô Tích, Giang Tô (江苏无锡1998年悬案21年侦破纪实 — Đặng Mỗ 邓某, 1998–2019): Từ nửa dấu vân tay mờ chỉ có vài điểm đặc trưng thu thập năm 1998, đội giám định kỹ thuật hình sự Công an Vô Tích kiên trì đối sánh qua nhiều thế hệ công nghệ suốt 21 năm cho đến khi khóa chặt nghi phạm đã trở thành chủ doanh nghiệp vận tải.",
        "hook_archetype": "micro_forensic_anomaly"
    },
    {
        "id": "fin_cn_kunming_cigarette_vault_oil_trace",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "云南昆明特大企业金库被盗案一滴特种机油微量物证侦破纪实 — 孙某·王某 (2002)",
        "archival_search_keywords_zh": [
            "昆明 金库被盗 微量物证 今日说法",
            "一滴机油 破案 天网 纪实",
            "云南 金库大案 侦破"
        ],
        "recommended_vox_verbs": [
            "SINGLE_EVIDENCE_AUTOPSY",
            "MICRO_TRACE_MATCH",
            "FORENSIC_ZOOM_CHAIN"
        ],
        "title": "[중국 실화 사건] 지문 하나 남기지 않고 대형 금고를 비운 털이범이 현장에 단 한 방울의 기름을 흘린 이유 | 쿤밍 금고 미제사건 ([Vụ Án Có Thật ở Trung Quốc] Vụ đột nhập kho bạc không để lại một dấu vân tay và bí ẩn giọt dầu máy duy nhất rơi trên sàn | Chuyên án két sắt Côn Minh)",
        "topic_anchor": "[중국 실화 사건] 지문 하나 남기지 않고 대형 금고를 비운 털이범이 현장에 단 한 방울의 기름을 흘린 이유 | 쿤밍 금고 미제사건",
        "winner_cluster": "Luồng 1 · Giải Phẫu Thành Phần Hóa Học 1 Giọt Dầu Máy Lật Tẩy Băng Đột Nhập Kho Bạc (쿤밍 금고 기름 한 방울 사건)",
        "codex_score": 95,
        "profile_score": 95,
        "codex_angle": "Hồ Sơ Thật 100%: Chuyên Án Vi Lượng Kho Bạc Côn Minh (云南昆明金库微量物证侦破案) — Phân Tích Quang Phổ Hạt Bụi Kim Loại Trong Giọt Dầu Bôi Trơn Kích Thủy Lực",
        "codex_reasons": [
            "Câu chuyện điều tra pháp y vi lượng chuẩn mực như сериал CSI đời thực trên CCTV 今日说法",
            "100% Xanh tiền YouTube, cực hợp SINGLE_EVIDENCE_AUTOPSY"
        ],
        "opening_hook": "장갑과 덧신으로 무장한 범인들은 털끝 하나, 지문 하나 현장에 남기지 않았습니다. 두꺼운 금고 문이 유압 잭에 의해 뜯겨 나간 자리, 바닥 타일 위에는 오직 쌀알 크기의 투명한 기름 한 방울만이 묻어 있었습니다. 바로 그 기름 한 방울이 범인의 직업을 정확히 말해주고 있었습니다.",
        "note": "【Hồ sơ vụ án: đại án đột nhập kho bạc tập đoàn tại Côn Minh · truy nguyên hung thủ từ đúng 1 giọt dầu máy công nghiệp đặc chủng rơi tại hiện trường】 Hồ sơ thật 100% Chuyên án giải mã vụ đột nhập két sắt tại Côn Minh, Vân Nam nhờ giám định vi lượng (云南昆明金库特大窃案微量物证侦破纪实): Nhóm thủ phạm đeo găng tay và bọc giày xóa sạch dấu vết sinh học, nhưng làm rỉ một giọt dầu thủy lực đặc chủng chứa mạt kim loại chỉ dùng trong xưởng bảo dưỡng máy công trình nặng, giúp cảnh sát khoanh vùng và bắt gọn toàn bộ băng nhóm.",
        "hook_archetype": "micro_forensic_anomaly"
    },
    {
        "id": "fin_cn_sichuan_museum_fishing_line_heist",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "四川馆藏一级文物被盗案透明钓鱼线跨越红外盲区侦破纪实 — 肖某 (2014)",
        "archival_search_keywords_zh": [
            "一级文物 被盗 钓鱼线 今日说法",
            "四川 博物馆 文物被盗 天网",
            "红外线 盲区 文物大案"
        ],
        "recommended_vox_verbs": [
            "BLIND_SPOT_REVEAL",
            "SINGLE_EVIDENCE_AUTOPSY",
            "FORENSIC_ZOOM_CHAIN"
        ],
        "title": "[중국 실화 사건] 출입문은 잠긴 채 천장 환풍구에서 투명 낚싯줄을 내려 적외선 경보기를 속이고 국보를 훔치다 | 쓰촨 박물관 밀실 도난 사건 ([Vụ Án Có Thật ở Trung Quốc] Cửa chính vẫn khóa chặt nhưng sợi cước câu cá trong suốt thả từ ống thông gió lấy cắp quốc bảo cấp 1 trước mũi cảm biến | Kỳ án phòng kín Tứ Xuyên)",
        "topic_anchor": "[중국 실화 사건] 출입문은 잠긴 채 천장 환풍구에서 투명 낚싯줄을 내려 적외선 경보기를 속이고 국보를 훔치다 | 쓰촨 박물관 밀실 도난 사건",
        "winner_cluster": "Luồng 1 · Sợi Cước Câu Cá Thả Từ Trần Nhà Qua Điểm Mù Hồng Ngoại & Màn Truy Vết Nút Thắt (쓰촨 1급 문물 낚싯줄 사건)",
        "codex_score": 96,
        "profile_score": 96,
        "codex_angle": "Hồ Sơ Thật 100%: Chuyên Án Đột Nhập Bảo Tàng Qua Điểm Mù Cảm Biến Tại Tứ Xuyên — Cách Pháp Y Giải Mã 'Nút Thắt Câu Cá Chuyên Nghiệp' Để Tìm Ra Thủ Phạm",
        "codex_reasons": [
            "Hiện trường phòng kín (Locked-room mystery) có thật 100% trên CCTV 今日说法 / 天网",
            "100% Xanh tiền, cực hợp với sơ đồ mặt cắt không gian BLIND_SPOT_REVEAL"
        ],
        "opening_hook": "전시실의 철문은 안에서 잠겨 있었고 바닥의 압력 센서도 작동하지 않았습니다. 그런데 유리 진열장 안에 있던 국가 일급 문물이 밤사이 감쪽같이 사라졌습니다. 형사들이 손전등을 들어 천장 환풍구를 비추었을 때, 허공에 매달린 채 반짝이는 투명한 낚싯줄 한 가닥이 모습을 드러냈습니다.",
        "note": "【Hồ sơ vụ án: đại án đánh cắp cổ vật quốc bảo cấp 1 tại Tứ Xuyên · thủ phạm dùng dây câu cá trong suốt vượt qua vùng quét tia hồng ngoại】 Hồ sơ thật 100% Chuyên án trộm cổ vật cấp 1 tại bảo tàng ở Tứ Xuyên (2014): Thủ phạm Tiêu Mỗ khảo sát góc quét cảm biến hồng ngoại nhiều tuần, sau đó chui qua hệ thống ống thông gió trên trần và dùng dây cước câu cá chịu lực kết hợp móc chuyên dụng câu cổ vật lên trần nhà; cảnh sát đã phân tích kiểu thắt nút dây câu đặc thù và truy vết camera bắt giữ thủ phạm.",
        "hook_archetype": "locked_room_vault_paradox"
    },
    {
        "id": "fin_cn_guangdong_foshan_safe_cracker_sound_10y",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "广东珠三角跨市技术开启金库保险柜特大系列悬案侦破 — 梁某 (2004–2014)",
        "archival_search_keywords_zh": [
            "技术开锁 保险柜 大案 今日说法",
            "珠三角 保险柜 悬案 天网",
            "听音开锁 侦破纪实"
        ],
        "recommended_vox_verbs": [
            "SINGLE_EVIDENCE_AUTOPSY",
            "FORENSIC_ZOOM_CHAIN",
            "BLIND_SPOT_REVEAL"
        ],
        "title": "[중국 실화 사건] 파손 흔적 하나 없이 청진기로 다이얼 소리만 듣고 대형 금고 수십 개를 열어젖힌 유령 기술자 | 주강삼각주 금고 사건 ([Vụ Án Có Thật ở Trung Quốc] Kẻ có biệt danh kỹ sư bóng ma chỉ dùng ống nghe đọc tiếng bánh răng để mở toang hàng chục két sắt cỡ lớn không vết cạy | Kỳ án két sắt Châu Giang)",
        "topic_anchor": "[중국 실화 사건] 파손 흔적 하나 없이 청진기로 다이얼 소리만 듣고 대형 금고 수십 개를 열어젖힌 유령 기술자 | 주강삼각주 금고 사건",
        "winner_cluster": "Luồng 1 · Kẻ Đột Nhập Mở Khóa Két Sắt Không Vết Xước & Vết Hằn Kính Hiển Vi Trong Ổ Khóa (광둥 무흔적 금고 기술자 사건)",
        "codex_score": 96,
        "profile_score": 96,
        "codex_angle": "Hồ Sơ Thật 100%: Chuyên Án Giải Mã Hàng Loạt Vụ Két Sắt Mở Không Dấu Vết Tại Châu thổ Sông Châu Giang — Khi Kính Hiển Vi Điện Tử Phát Hiện Vết Xước 0,05mm Bên Trong Ruột Khóa",
        "codex_reasons": [
            "Đề tài mở khóa kỹ thuật cao (Lock-picking forensics) cực kỳ hấp dẫn và 100% Xanh tiền YouTube",
            "Khớp hoàn hảo SINGLE_EVIDENCE_AUTOPSY & FORENSIC_ZOOM_CHAIN"
        ],
        "opening_hook": "드릴 자국도, 산소절단기 흔적도 없었습니다.마치 주인이 직접 비밀번호를 돌리고 열쇠를 꽂아 연 것처럼 대형 금고 문이 고스란히 열려 있었습니다. 하지만 법의학자들이 금고 잠금장치를 분해해 전자현미경 아래에 놓았을 때, 내부 핀 위에 남은 영점 영오 밀리미터의 미세한 금속 긁힘이 진실을 말하기 시작했습니다.",
        "note": "【Hồ sơ vụ án: kỳ án 'bóng ma mở két' dùng ống nghe y tế đọc âm thanh bánh răng mở hàng chục két sắt cỡ lớn suốt 10 năm không cần phá khóa】 Hồ sơ thật 100% Chuyên án phá chuỗi vụ trộm két sắt bằng kỹ thuật mở khóa tinh vi tại vùng Châu thổ sông Châu Giang, Quảng Đông (2004–2014): Thủ phạm Lương Mỗ vốn là thợ cơ khí khóa két sắt lành nghề, đột nhập ban đêm mở két không để lại vết cạy phá bên ngoài; chuyên gia giám định dấu vết công cụ đã tháo rời lõi khóa soi kính hiển vi tìm ra đặc điểm dụng cụ tự chế của hắn.",
        "hook_archetype": "locked_room_vault_paradox"
    },
    {
        "id": "fin_cn_shandong_weifang_chenzengyu_bank_bill_1_1b",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "山东潍坊银行票据贴现11亿元挪用潜逃案 — 陈增玉 (2012–2015)",
        "archival_search_keywords_zh": [
            "山东潍坊 银行票据 11亿 今日说法",
            "票据贴现 挪用 猎狐行动 央视",
            "银行承兑汇票 惊天大案"
        ],
        "recommended_vox_verbs": [
            "LEDGER_DIFF_SCRUB",
            "SCALE_MULTIPLICATION",
            "GEO_VECTOR_PURSUIT"
        ],
        "title": "[중국 실화 사건] 복사기 한 대로 은행 어음 직인을 위조해 11억 위안을 돌린 어음 브로커의 도주극 | 웨이팡 천쩡위 사건 ([Vụ Án Có Thật ở Trung Quốc] Dùng 1 máy photocopy làm giả con dấu hối phiếu ngân hàng quay vòng 1,1 tỷ tệ và cuộc đào tẩu của trùm môi giới | Đại án Trần Tăng Ngọc)",
        "topic_anchor": "[중국 실화 사건] 복사기 한 대로 은행 어음 직인을 위조해 11억 위안을 돌린 어음 브로커의 도주극 | 웨이팡 천쩡위 사건",
        "winner_cluster": "Luồng 1 · Kẽ Hở Chiết Khấu Hối Phiếu 1,1 Tỷ NDT & Cuộc Truy Bắt Xuyên Biên Giới (산둥 웨이팡 11억 어음 사기 사건)",
        "codex_score": 96,
        "profile_score": 96,
        "codex_angle": "Hồ Sơ Thật 100%: Đại Án Hối Phiếu 1,1 Tỷ NDT Tại Duy Phường, Sơn Đông — Khi Hối Phiếu Thật Bị Đánh Tráo Bằng Bản Sao Màu Giữa 2 Phòng Giao Dịch",
        "codex_reasons": [
            "Thủ đoạn tráo hối phiếu ngân hàng (克隆票据) cực kỳ trực quan cho bàn biên tập cắt dán Vox",
            "100% Xanh tiền YouTube"
        ],
        "opening_hook": "진짜 은행 어음 한 장이 복사기를 통과하는 순간, 똑같은 일련번호를 가진 두 장의 어음으로 둔갑했습니다. 산둥성 웨이팡의 금융 브로커 천쩡위는 이 단순한 눈속임 하나로 여러 은행 지점 사이를 오가며 무려 십일억 위안의 자금을 공중에서 만들어냈습니다.",
        "note": "【Hồ sơ vụ án: đại án nhân bản hối phiếu ngân hàng rút ruột 1,1 tỷ tệ tại Duy Phường · truy bắt của cục cảnh sát kinh tế】 Hồ sơ thật 100% Đại án chiết khấu hối phiếu ngân hàng 1,1 tỷ NDT tại Duy Phường, Sơn Đông (山东潍坊11亿元银行承兑汇票诈骗挪用案 — Trần Tăng Ngọc 陈增玉, 2012–2015): Lợi dụng khoảng trống thời gian kiểm tra liên ngân hàng, nhóm thủ phạm nhân bản hối phiếu và con dấu để chiết khấu trùng lặp rút ruột 1,1 tỷ NDT trước khi bị Cục Cảnh sát Kinh tế truy bắt.",
        "hook_archetype": "locked_room_vault_paradox"
    },
    {
        "id": "fin_cn_shenzhen_customs_hujincheng_tax_rebate_800m",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "广东深圳空壳集装箱循环出口骗取8亿元国家退税款特大案 — 胡金城 (2013–2017)",
        "archival_search_keywords_zh": [
            "深圳 骗取出口退税 8亿 今日说法",
            "空集装箱 循环出口 骗税 央视",
            "海关 缉私 骗税大案 庭审"
        ],
        "recommended_vox_verbs": [
            "GEO_VECTOR_PURSUIT",
            "LEDGER_DIFF_SCRUB",
            "SCALE_MULTIPLICATION"
        ],
        "title": "[중국 실화 사건] 똑같은 전자부품 한 상자를 홍콩과 선전 사이로 300번 왕복시켜 국고 8억 위안을 털어낸 유령 수출왕 | 선전 후진청 사건 ([Vụ Án Có Thật ở Trung Quốc] Cho 1 thùng linh kiện đi lại 300 vòng giữa Hồng Kông và Thâm Quyến để rút 800 triệu tệ tiền hoàn thuế quốc gia | Đại án Hồ Kim Thành)",
        "topic_anchor": "[중국 실화 사건] 똑같은 전자부품 한 상자를 홍콩과 선전 사이로 300번 왕복시켜 국고 8억 위안을 털어낸 유령 수출왕 | 선전 후진청 사건",
        "winner_cluster": "Luồng 1 · Vòng Lặp Container 'Đạo Cụ' Đi Qua Biên Giới 300 Lần Rút Ruột 800 Triệu Tệ Hoàn Thuế (선전 8억 위안 유령 수출 환급 사건)",
        "codex_score": 97,
        "profile_score": 97,
        "codex_angle": "Hồ Sơ Thật 100%: Đại Án Rút Ruột Hoàn Thuế Xuất Khẩu 800 Triệu NDT Tại Thâm Quyến — Khi AI Hải Quan Phát Hiện 1 Lô Hàng Chip Điện Tử Đi Vòng Tròn Suốt 3 Năm",
        "codex_reasons": [
            "Cơ chế 'hàng đạo cụ đi vòng tròn' (道具货循环出口) cực kỳ thú vị để vẽ sơ đồ luồng hàng + dòng tiền trên Vox",
            "100% Xanh tiền YouTube"
        ],
        "opening_hook": "수출 서류상으로는 매달 수천만 달러어치의 최첨단 반도체 칩이 선전 항구를 떠나 홍콩으로 수출되고 있었습니다. 하지만 세관 수사관들이 컨테이너의 위성 위치 기록을 겹쳐 보았을 때, 똑같은 상자 몇 개가 국경 바다를 삼백 번이나 맴돌며 팔억 위안의 세금 환급금을 빨아들이고 있었다는 사실이 드러났습니다.",
        "note": "【Hồ sơ vụ án: đại án cho 1 thùng linh kiện quay vòng 300 lượt qua biên giới Hồng Kông – Thâm Quyến để lừa rút 800 triệu tệ tiền hoàn thuế quốc gia】 Hồ sơ thật 100% Đại án lừa đảo hoàn thuế xuất khẩu 800 triệu NDT tại Thâm Quyến, Quảng Đông (广东深圳8亿元特大虚开骗取出口退税案 — Hồ Kim Thành 胡金城, 2013–2017): Sử dụng một lượng nhỏ linh kiện điện tử làm 'hàng đạo cụ' xuất khẩu sang Hồng Kông rồi nhập lậu ngược về Thâm Quyến quay vòng hàng trăm lần để lập hồ sơ khống rút 800 triệu NDT tiền hoàn thuế nhà nước.",
        "hook_archetype": "double_life_unmasking"
    },
    {
        "id": "fin_cn_tianjin_customs_chenyi_luxury_car_smuggling_1_6b",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "天津港跨国低报价格走私2000辆豪车偷逃税款16亿元秘鲁缉捕案 — 陈毅 (2014–2019)",
        "archival_search_keywords_zh": [
            "天津港 走私豪车 秘鲁 遣返 今日说法",
            "海关 红通 豪车走私 央视",
            "低报价格 走私汽车 大案"
        ],
        "recommended_vox_verbs": [
            "LEDGER_DIFF_SCRUB",
            "GEO_VECTOR_PURSUIT",
            "SPLIT_PARADOX"
        ],
        "title": "[중국 실화 사건] 이중 계약서로 슈퍼카 2,000대를 통관시켜 16억 위안을 챙기고 남미로 증발한 주범 | 톈진항 천이 사건 ([Vụ Án Có Thật ở Trung Quốc] Dùng hợp đồng kép thông quan 2.000 siêu xe bỏ túi 1,6 tỷ tệ rồi bốc hơi sang Nam Mỹ | Đại án Trần Nghị cảng Thiên Tân)",
        "topic_anchor": "[중국 실화 사건] 이중 계약서로 슈퍼카 2,000대를 통관시켜 16억 위안을 챙기고 남미로 증발한 주범 | 톈진항 천이 사건",
        "winner_cluster": "Luồng 1 · Hóa Đơn Kép Thông Quan 2.000 Siêu Xe Tại Cảng Thiên Tân & Chuyến Bay Áp Giải Từ Peru (톈진항 16억 슈퍼카 이중장부 사건)",
        "codex_score": 96,
        "profile_score": 96,
        "codex_angle": "Hồ Sơ Thật 100%: Đại Án Hóa Đơn Kép 1,6 Tỷ NDT Tại Cảng Thiên Tân — So Khớp Dòng Tiền Chuyển Khoản Ngầm Và Cuộc Vây Bắt Truy Nã Đỏ Tại Lima (Peru)",
        "codex_reasons": [
            "Hình ảnh cảng container siêu xe + truy bắt xuyên Thái Bình Dương từ Peru cực kỳ bắt mắt",
            "100% Xanh tiền YouTube"
        ],
        "opening_hook": "서류상으로는 폐차 직전의 고철 부품 컨테이너였지만, 세관 엑스레이 스캐너를 통과하는 순간 최신형 최고급 수입차 수백 대의 윤곽이 선명하게 드러났습니다. 유령 무역회사 스무 곳을 세워 16억 위안대 관세를 증발시킨 설계자의 정체를 추적합니다.",
        "note": "【Hồ sơ vụ án: đại án dùng hóa đơn kép buôn lậu 2.000 siêu xe qua cảng Thiên Tân trốn thuế 1,6 tỷ tệ · dẫn độ kẻ chủ mưu từ Peru】 Hồ sơ thật 100% Đại án gian lận hóa đơn nhập khẩu hơn 2.000 xe hạng sang trị giá trốn thuế 1,6 tỷ NDT qua cảng Thiên Tân (天津港特大走私豪车红通逃犯秘鲁押解回国案 — Trần Nghị 陈毅, 2014–2019): Sau khi đường dây bị phanh phui, kẻ chủ mưu trốn sang Peru và bị lực lượng hải quan - công an Trung Quốc phối hợp Interpol bắt giữ áp giải về nước.",
        "hook_archetype": "micro_forensic_anomaly"
    },
    {
        "id": "fin_cn_jiangsu_changzhou_deng_accounting_320m",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "江苏常州财政国库集中支付中心会计挪用3.2亿元公款案 — 邓某 (2016–2019)",
        "archival_search_keywords_zh": [
            "常州 会计 挪用公款 3.2亿 今日说法",
            "国库集中支付 挪用 亿万 央视",
            "小会计 挪用上亿 庭审现场"
        ],
        "recommended_vox_verbs": [
            "LEDGER_DIFF_SCRUB",
            "SCALE_MULTIPLICATION",
            "CRASH_TIMELINE"
        ],
        "title": "[중국 실화 사건] 월급 4천 위안 말단 회계원이 국고 시스템 취소 버튼 허점으로 빼돌린 3억 2천만 위안 | 창저우 회계원 사건 ([Vụ Án Có Thật ở Trung Quốc] Kế toán quèn lương 4.000 tệ lợi dụng lỗ hổng nút hủy lệnh hệ thống kho bạc rút ruột 320 triệu tệ | Đại án kế toán Thường Châu)",
        "topic_anchor": "[중국 실화 사건] 월급 4천 위안 말단 회계원이 국고 시스템 취소 버튼 허점으로 빼돌린 3억 2천만 위안 | 창저우 회계원 사건",
        "winner_cluster": "Luồng 1 · Lỗ Hổng 'Hoàn Tiền Vào Tài Khoản Phụ' Giúp Kế Toán Viên Rút 320 Triệu Tệ Kho Bạc (창저우 3.2억 위안 국고 회계원 사건)",
        "codex_score": 97,
        "profile_score": 97,
        "codex_angle": "Hồ Sơ Thật 100%: Đại Án 320 Triệu NDT Tại Trung Tâm Thanh Toán Kho Bạc Thường Châu, Giang Tô — Khi 148 Lệnh Chuyển Tiền Bị Sửa Đổi Số Tài Khoản Nhận Hoàn Tiền",
        "codex_reasons": [
            "Điển hình của tội phạm cổ cồn trắng dùng lỗi logic phần mềm kế toán để rút hàng trăm triệu NDT",
            "100% Xanh tiền YouTube, cực hợp LEDGER_DIFF_SCRUB"
        ],
        "opening_hook": "한 달 월급이 사천 위안에 불과했던 평범한 회계 직원이 삼 년 동안 무려 삼억 이천만 위안의 공금을 자신의 계좌로 옮겼습니다. 그가 사용한 무기는 해킹 프로그램이 아니라, 결제 실패 시 환불 계좌 번호를 수동으로 수정할 수 있었던 전산 시스템의 작은 빈틈 하나였습니다.",
        "note": "【Hồ sơ vụ án: đại án kế toán viên kho bạc lương 4.000 tệ lợi dụng lỗ hổng 'nút hoàn trả lệnh' để rút ruột 320 triệu tệ công quỹ suốt 3 năm】 Hồ sơ thật 100% Đại án kế toán viên Trung tâm thanh toán kho bạc tại Thường Châu, Giang Tô biển thủ 320 triệu NDT (江苏常州会计挪用3.2亿元公款案 — Đặng Mỗ 邓某, 2016–2019): Lợi dụng quy trình xử lý lệnh thanh toán bị退回 (hoàn trả) không khóa trường số tài khoản nhận lại, Đặng Mỗ đã thay bằng tài khoản cá nhân suốt 3 năm.",
        "hook_archetype": "cold_archive_match"
    },
    {
        "id": "fin_cn_zhejiang_jinhua_fake_gold_pledge_1_9b",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "浙江金华特大钨芯假黄金质押骗取金融机构19亿元贷款案 — 徐某·林某 (2016–2020)",
        "archival_search_keywords_zh": [
            "假黄金 质押 钨芯 今日说法",
            "金库 假黄金 骗贷 央视财经",
            "黄金掺钨 骗取贷款 侦破"
        ],
        "recommended_vox_verbs": [
            "SINGLE_EVIDENCE_AUTOPSY",
            "LEDGER_DIFF_SCRUB",
            "SCALE_MULTIPLICATION"
        ],
        "title": "[중국 실화 사건] 은행 금고에 담보로 맡긴 순금 3톤을 녹이자 속에서 시커먼 합금이 쏟아져 나온 이유 | 진화 가짜 황금 사건 ([Vụ Án Có Thật ở Trung Quốc] Nung chảy 3 tấn vàng ròng thế chấp trong hầm ngân hàng thì lộ ra khối hợp kim đen sì bên trong | Đại án vàng giả 1,9 tỷ tệ Kim Hoa)",
        "topic_anchor": "[중국 실화 사건] 은행 금고에 담보로 맡긴 순금 3톤을 녹이자 속에서 시커먼 합금이 쏟아져 나온 이유 | 진화 가짜 황금 사건",
        "winner_cluster": "Luồng 1 · Vàng Thỏi Nhồi Lõi Vonfram Có Tỷ Trọng Bằng Hệt Vàng Thật Qua Mặt Máy Đo (저장성 19억 텅스텐 가짜 골드바 사건)",
        "codex_score": 98,
        "profile_score": 98,
        "codex_angle": "Hồ Sơ Thật 100%: Đại Án Thế Chấp Vàng Giả Lõi Vonfram 1,9 Tỷ NDT — Vì Sao Máy Đo Quang Phổ Bề Mặt Và Cân Trọng Lượng Của Ngân Hàng Đều Bị Đánh Lừa?",
        "codex_reasons": [
            "Khoa học vật lý cực kỳ cuốn hút: Vonfram (Tungsten) có tỷ trọng 19,25 g/cm³ gần như bằng hệt vàng ròng 19,32 g/cm³, nên cân nước và súng bắn quang phổ XRF bề mặt đều báo là vàng 9999!",
            "100% Xanh tiền YouTube, sinh ra cho SINGLE_EVIDENCE_AUTOPSY & LEDGER_DIFF_SCRUB"
        ],
        "opening_hook": "무게도 순금과 똑같고, 표면 엑스선 순도 검사기마저 구십구 점 구구 퍼센트 순금이라고 판정한 수천 개의 골드바. 금융기관들은 그 금괴를 지하 금고에 봉인하고 십구억 위안을 대출해 주었습니다. 그러나 대출 만기일, 금괴를 용광로에 넣고 반으로 잘라본 순간 모두의 얼굴이 하얗게 질렸습니다.",
        "note": "【Hồ sơ vụ án: đại án đúc 3 tấn vàng thỏi giả bọc lõi kim loại Vonfram qua mặt máy đo quang phổ XRF để thế chấp rút ruột 1,9 tỷ tệ ngân hàng】 Hồ sơ thật 100% Đại án dùng vàng thỏi bọc lõi kim loại Vonfram (钨芯假黄金) thế chấp vay 1,9 tỷ NDT: Lợi dụng kim loại Vonfram có khối lượng riêng 19,25 g/cm³ tương đương vàng nguyên chất (19,32 g/cm³), nhóm thủ phạm bọc lớp vàng thật dày bên ngoài lõi Vonfram để vượt qua máy đo quang phổ bề mặt XRF, ký gửi vào kho bạc rút 1,9 tỷ NDT.",
        "hook_archetype": "locked_room_vault_paradox"
    },
    {
        "id": "fin_cn_guangxi_nanning_housing_fund_li_280m",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "广西南宁住房公积金管理中心内部虚构账户挪用2.8亿元案 — 李某 (2011–2018)",
        "archival_search_keywords_zh": [
            "南宁 住房公积金 挪用 2.8亿 今日说法",
            "公积金 巨额挪用 庭审现场",
            "广西 公积金 大案 央视"
        ],
        "recommended_vox_verbs": [
            "LEDGER_DIFF_SCRUB",
            "SPLIT_PARADOX",
            "CRASH_TIMELINE"
        ],
        "title": "[중국 실화 사건] 7년간 유령 퇴직자 400명을 만들어 주택기금 2억 8천만 위안을 빼돌린 내부자 | 난닝 주택기금 증발 사건 ([Vụ Án Có Thật ở Trung Quốc] Tạo 400 hồ sơ người nghỉ hưu ma suốt 7 năm để rút ruột 280 triệu tệ quỹ nhà ở của kẻ nội gián | Đại án Quỹ nhà ở Nam Ninh)",
        "topic_anchor": "[중국 실화 사건] 7년간 유령 퇴직자 400명을 만들어 주택기금 2억 8천만 위안을 빼돌린 내부자 | 난닝 주택기금 증발 사건",
        "winner_cluster": "Luồng 1 · 400 Hồ Sơ Nghỉ Hưu Ảo Rút Ruột 280 Triệu Tệ Quỹ Nhà Ở Suốt 7 Năm Không Bị Phát Hiện (난닝 2.8억 주택기금 유령계좌 사건)",
        "codex_score": 95,
        "profile_score": 95,
        "codex_angle": "Hồ Sơ Thật 100%: Đại Án Quỹ Nhà Ở Nam Ninh 280 Triệu NDT — Cách Thuật Toán Kiểm Toán Chéo Dữ Liệu Bảo Hiểm Xã Hội Phanh Phui 400 Danh Tính Ảo",
        "codex_reasons": [
            "Cấu trúc kiểm toán dữ liệu lớn (Big Data Audit) lật tẩy lỗ hổng nội bộ cực kỳ sắc nét",
            "100% Xanh tiền YouTube"
        ],
        "opening_hook": "매달 수십 명의 퇴직자들이 주택적립금을 전액 인출해 가는 정상적인 서류들. 그러나 칠 년 뒤 감사팀이 연금 데이터베이스와 주택기금 명단을 교차 대조했을 때, 돈을 찾아간 사백 명의 퇴직자 중 단 한 명도 실제로 존재하지 않는 유령 인물이었음이 밝혀졌습니다.",
        "note": "【Hồ sơ vụ án: đại án kẻ nội gián tạo 400 hồ sơ người nghỉ hưu ma suốt 7 năm để rút ruột 280 triệu tệ quỹ tiết kiệm nhà ở】 Hồ sơ thật 100% Đại án rút ruột 280 triệu NDT tại Trung tâm quản lý Quỹ nhà ở Nam Ninh, Quảng Tây (广西南宁住房公积金2.8亿元挪用案 — Lý Mỗ 李某, 2011–2018): Lợi dụng quyền quản trị cơ sở dữ liệu nội bộ chưa liên thông trực tiếp với hệ thống hộ tịch, Lý Mỗ đã lập khống hàng trăm hồ sơ tất toán quỹ nhà ở suốt 7 năm.",
        "hook_archetype": "double_life_unmasking"
    },
    {
        "id": "vio_cn_temple_abbot_fugitive_16y",
        "topic_stream": "major_violent_crime",
        "case_real_name_zh": "黑龙江大庆命案逃犯潜逃16年变身安徽凤阳龙兴寺住持案 — 张立伟 / 释广闻 (2000–2017)",
        "archival_search_keywords_zh": [
            "张立伟 龙兴寺 住持 逃犯 今日说法",
            "命案逃犯 变身 住持 张立伟",
            "凤阳龙兴寺 张立伟 天网"
        ],
        "recommended_vox_verbs": [
            "DUAL_ERA_LOCK",
            "SPLIT_PARADOX",
            "NETWORK_GRAPH"
        ],
        "title": "[중국 실화 사건] 16년간 전국이 추적한 공안부 중대 수배범이 600년 고찰의 존경받는 주지 스님이었다니 | 장리웨이 두 얼굴의 도주극 ([Vụ Án Có Thật ở Trung Quốc] Kẻ truy nã trọng án trốn chạy 16 năm lại ẩn mình làm Trụ trì đáng kính của ngôi cổ tự 600 năm | Hai bộ mặt của Trương Lập Vĩ)",
        "topic_anchor": "[중국 실화 사건] 16년간 전국이 추적한 공안부 중대 수배범이 600년 고찰의 존경받는 주지 스님이었다니 | 장리웨이 두 얼굴의 도주극",
        "winner_cluster": "Luồng 2 · Kẻ Truy Nã Trọng Án Tẩy Trắng Thành Trụ Trì Danh Tự & Uỷ Viên Từ Thiện (장리웨이 룽싱사 주지 사건)",
        "codex_score": 98,
        "profile_score": 98,
        "codex_angle": "Hồ Sơ Thật 100%: Trương Lập Vĩ / Thích Quảng Văn (张立伟 / 释广闻, 2000–2017) — Trốn Trọng Án Từ Hắc Long Giang Xuống Ngôi Chùa Cổ Hoàng Gia Minh Thái Tổ Lên Tới Chức Trụ Trì",
        "codex_reasons": [
            "Nghịch lý vỏ bọc hai mặt cực đại đúng chất SBS 그것이 알고싶다: tội phạm trọng án lên truyền hình giảng đạo, tài trợ học sinh nghèo suốt 16 năm",
            "Bước ngoặt sinh trắc học so khớp ảnh CMND giả Tôn Hồng Đào (孙洪涛) với ảnh truy nã năm 2000 — cực hợp DUAL_ERA_LOCK"
        ],
        "opening_hook": "명나라 황제가 세운 육백 년 역사의 유서 깊은 사찰. 지역 방송에 출연해 자비를 설파하고 불우한 학생들을 후원하던 존경받는 주지 스님에게는 아무도 모르는 비밀이 있었습니다. 경찰 안면 대조 시스템이 스님의 법명 뒤에 숨겨진 진짜 이름을 띄운 순간, 십육 년 전 북쪽 끝 도시의 수배 전단이 함께 겹쳐졌습니다.",
        "note": "【Hồ sơ vụ án: trọng án tước đoạt 3 sinh mạng tại Đại Khánh · truy nã đặc biệt bộ công an · giả làm trụ trì chùa cổ 16 năm】 Hồ sơ thật 100% Vụ án Trương Lập Vĩ (张立伟, pháp danh Thích Quảng Văn 释广闻, 2000–2017): Sau trọng án năm 2000 tại Đại Khánh (Hắc Long Giang), Trương Lập Vĩ trốn hơn 2.000km xuống An Huy, mua hộ khẩu giả tên Tôn Hồng Đào (孙洪涛) và từng bước leo lên làm Trụ trì chùa Long Hưng (Phượng Dương, An Huy) suốt 16 năm trước khi Công an Đại Khánh đối sánh ảnh sinh trắc học bắt giữ tháng 8/2017.",
        "hook_archetype": "last_ordinary_routine"
    },
    {
        "id": "vio_cn_zhaodong_double_face_detective",
        "topic_stream": "major_violent_crime",
        "case_real_name_zh": "黑龙江肇东市刑警中队长双面涉黑特大悬案 — 蒋英库 (1993–2001)",
        "archival_search_keywords_zh": [
            "肇东 蒋英库 真实大案 纪实",
            "刑警 蒋英库 双面 侦破",
            "黑龙江 蒋英库 庭审"
        ],
        "recommended_vox_verbs": [
            "SPLIT_PARADOX",
            "ALIBI_SHATTER",
            "NETWORK_GRAPH"
        ],
        "title": "[중국 실화 사건] 8년간 반경 1km에서 사라진 20여 명의 사건을 직접 지휘하던 형사 반장의 소름 돋는 두 얼굴 | 자오둥 장잉쿠 사건 ([Vụ Án Có Thật ở Trung Quốc] Hai bộ mặt rùng mình của vị đội trưởng hình sự trực tiếp chỉ đạo điều tra hơn 20 vụ mất tích bí ẩn suốt 8 năm | Đại án Tưởng Anh Khôi)",
        "topic_anchor": "[중국 실화 사건] 8년간 반경 1km에서 사라진 20여 명의 사건을 직접 지휘하던 형사 반장의 소름 돋는 두 얼굴 | 자오둥 장잉쿠 사건",
        "winner_cluster": "Luồng 2 · Kẻ Hai Mặt Trong Chính Đội Điều Tra & 8 Năm Hồ Sơ Bốc Hơi (헤이룽장 자오둥 장잉쿠 사건)",
        "codex_score": 97,
        "profile_score": 97,
        "codex_angle": "Hồ Sơ Thật 100%: Chuyên Án Tưởng Anh Khôi Tại Triệu Đông, Hắc Long Giang (黑龙江肇东蒋英库案) — Khi Viên Kiểm Sát Viên Cấp Tỉnh Cũng Mất Tích Bí Ẩn Và Màn Lật Tẩy Hầm Ngầm Cờ Bạc Giả",
        "codex_reasons": [
            "Twist tâm lý - điều tra cực mạnh: thủ phạm mang thẻ ngành lợi dụng quyền hạn để xóa dấu vết suốt 8 năm cho đến khi 2 cán bộ kiểm sát tỉnh Cáp Nhĩ Tân đi đòi nợ giúp người thân rồi mất tích",
            "100% Xanh tiền YouTube: kể hoàn toàn theo góc nhìn Tổ Chuyên Án Đặc Biệt Công an tỉnh Hắc Long Giang truy tìm đồng nghiệp mất tích"
        ],
        "opening_hook": "지역 자산가들이 잇달아 연락이 끊길 때마다 가장 먼저 현장에 나타나 수사를 지휘하던 베테랑 형사 반장 장잉쿠. 그러던 어느 겨울, 성 검찰청 소속 간부 두 명까지 그 도시에 들어갔다가 흔적 없이 사라지자 특별수사팀의 시선은 가장 가까운 내부 인물을 향하기 시작했습니다.",
        "note": "【Hồ sơ vụ án: đại án liên hoàn tước đoạt sinh mạng hơn 20 người (gồm cả 2 cán bộ kiểm sát) · đội trưởng hình sự hai mặt suốt 8 năm】 Hồ sơ thật 100% Đại án Tưởng Anh Khôi tại thành phố Triệu Đông, tỉnh Hắc Long Giang (黑龙江肇东蒋英库特大团伙案, 1993–2001): Lợi dụng vỏ bọc công chức hình sự để vay tiền lớn rồi thủ tiêu chủ nợ suốt 8 năm; tháng 12/2000 việc 2 cán bộ viện kiểm sát mất tích tại Triệu Đông kích hoạt chuyên án mật cấp tỉnh lật tẩy toàn bộ đường dây.",
        "hook_archetype": "double_life_unmasking"
    },
    {
        "id": "vio_cn_hangzhou_wanxiang_20y_coldcase",
        "topic_stream": "major_violent_crime",
        "case_real_name_zh": "浙江杭州2000年万向公园11·4情侣命案积案20年DNA家系侦破 — 武某·王某 (2000–2020)",
        "archival_search_keywords_zh": [
            "杭州万向公园案 20年 侦破 今日说法",
            "2000年 万向公园 命案积案 杭州警方",
            "万向公园 11·4 天网"
        ],
        "recommended_vox_verbs": [
            "MICRO_TRACE_MATCH",
            "GEO_VECTOR_PURSUIT",
            "SINGLE_EVIDENCE_AUTOPSY"
        ],
        "title": "[중국 실화 사건] 도심 공원의 시간을 멈춘 20년 특급 미제사건의 범인이 1,200km 밖에서 평범히 살아온 사연 | 항저우 완샹공원 사건 ([Vụ Án Có Thật ở Trung Quốc] Kẻ thủ ác trong kỳ án treo 20 năm tại công viên trung tâm Hàng Châu sống bình thản cách hiện trường 1.200km | Kỳ án Công viên Vạn Hướng)",
        "topic_anchor": "[중국 실화 사건] 도심 공원의 시간을 멈춘 20년 특급 미제사건의 범인이 1,200km 밖에서 평범히 살아온 사연 | 항저우 완샹공원 사건",
        "winner_cluster": "Luồng 2 · Hồ Sơ Lạnh 20 Năm Hàng Châu & Đột Phá Cây Gia Phả Pháp Y ADN (항저우 완샹공원 20년 미제사건)",
        "codex_score": 96,
        "profile_score": 96,
        "codex_angle": "Hồ Sơ Thật 100%: Kỳ Án Công Viên Vạn Hướng Hàng Châu (杭州万向公园11·4积案, 2000–2020) — 20 Năm Bảo Quản Vật Chứng Trong Kho Lạnh & Chiến Dịch Lọc Gia Phả Xuyên Sơn Đông - Nội Mông",
        "codex_reasons": [
            "Họp báo chính thức cực lớn của Công an Hàng Châu năm 2020 kèm nhiều phóng sự CCTV/Chiết Giang TV về 3 thế hệ cảnh sát giữ vật chứng suốt 20 năm",
            "Đậm chất nhân văn điều tra & khoa học hình sự (100% Xanh tiền YouTube)"
        ],
        "opening_hook": "은퇴를 앞둔 노형사가 후배의 손에 조용히 건넨 빛바랜 갈색 증거물 봉투 하나. 항저우 도심 한복판 완샹공원에서 목격자 한 명 없이 미궁에 빠졌던 그날 밤의 미세 흔적이, 20년 뒤 1,200킬로미터 떨어진 북쪽 마을의 한 가계도를 정확히 가리켰습니다.",
        "note": "【Hồ sơ vụ án: trọng án tước đoạt sinh mạng 2 nạn nhân (đôi tình nhân) tại công viên · án lạnh 20 năm giải mã bằng phả hệ gen Y-STR】 Hồ sơ thật 100% Kỳ án Công viên Vạn Hướng quận Hạ Thành, Hàng Châu ngày 4/11/2000 (杭州万向公园11·4命案积案 — Vũ Mỗ 武某 & Vương Mỗ 王某, phá án tháng 7/2020): Vụ án treo suốt 20 năm của Công an Hàng Châu được giải mã nhờ công nghệ gia phả Y-STR thế hệ mới khoanh vùng dòng họ tại Sơn Đông và bắt giữ 2 hung thủ đã thay đổi cuộc sống tại Nội Mông & Sơn Đông.",
        "hook_archetype": "chilling_verbatim_line"
    },
    {
        "id": "vio_cn_shijiazhuang_168h_manhunt",
        "topic_stream": "major_violent_crime",
        "case_real_name_zh": "河北石家庄3·16特大案件168小时全国A级通缉追捕纪实 — 靳如超 (2001)",
        "archival_search_keywords_zh": [
            "石家庄 靳如超 168小时 大追捕",
            "靳如超 广西北海 落网 纪实",
            "公安部通缉令 靳如超"
        ],
        "recommended_vox_verbs": [
            "RADIAL_TIME_PRESSURE",
            "GEO_VECTOR_PURSUIT",
            "CAUSAL_CHAIN"
        ],
        "title": "[중국 실화 사건] 하룻밤 사이 도시 전체를 멈춰 세우고 사라진 공안부 A급 1호 수배범의 치밀한 은신 행적 | 진루차오 수배 사건 ([Vụ Án Có Thật ở Trung Quốc] Hành tung ẩn náu của kẻ truy nã cấp A số 1 Bộ Công an khiến cả thành phố nín thở chỉ sau một đêm | Chuyên án Cận Như Siêu)",
        "topic_anchor": "[중국 실화 사건] 하룻밤 사이 도시 전체를 멈춰 세우고 사라진 공안부 A급 1호 수배범의 치밀한 은신 행적 | 진루차오 수배 사건",
        "winner_cluster": "Luồng 2 · Lệnh Truy Nã Khẩn Toàn Quốc & 168 Giờ Khóa Chặt Đường Trốn 2.400km (스자좡 진루차오 168시간 추격전)",
        "codex_score": 95,
        "profile_score": 95,
        "codex_angle": "Hồ Sơ Thật 100%: 168 Giờ Đại Truy Bắt Cận Như Siêu (靳如超, 3/2001) — Hành Trình Trốn 2.400km Từ Hà Bắc Tới Rừng Phi Lao Bắc Hải (Quảng Tây) & Người Tài Xế Xe Ôm Tinh Mắt",
        "codex_reasons": [
            "Một trong những chiến dịch truy nã cấp A tốc độ và quy mô lớn nhất lịch sử Bộ Công an Trung Quốc, tư liệu thời sự CCTV năm 2001 cực kỳ phong phú",
            "Cắt cảnh Sau Cơn Bão 100% Xanh tiền: tập trung hoàn toàn vào đồng hồ đếm ngược 168 giờ truy vết xuyên 6 tỉnh và truy nguyên nguồn vật liệu trái phép"
        ],
        "opening_hook": "어릴 적 병으로 청력을 잃고 세상과 담을 쌓은 채 살아가던 마흔한 살 남자 진루차오. 어느 새벽 그의 얼굴이 인쇄된 수백만 장의 일급 수배 전단이 전국 기차역과 국도에 일제히 붙으면서, 허베이성에서 남쪽 끝 바닷가까지 2,400킬로미터를 가로지르는 168시간의 대추격이 시작됐습니다.",
        "note": "【Hồ sơ vụ án: đại án đặc biệt nguy hiểm tước đoạt sinh mạng hàng chục hộ dân · lệnh truy nã cấp A số 1 bộ công an · 168 giờ đại truy kích】 Hồ sơ thật 100% Chiến dịch 168 giờ đại truy bắt Cận Như Siêu (石家庄3·16案全国大追捕 — 靳如超, 16–23/3/2001): Khắc họa góc nhìn Ban Chuyên Án Bộ Công an (100% Cắt cảnh Sau Cơn Bão, không mô tả thương vong trực diện) truy lùng lộ trình đào tẩu xuyên 6 tỉnh suốt 7 ngày đêm cho đến khi bắt sống nghi phạm tại Bắc Hải (Quảng Tây) nhờ tin báo quần chúng.",
        "hook_archetype": "locked_room_vault_paradox"
    },
    {
        "id": "vio_cn_wuhan_sanya_ma_hanqing_8y",
        "topic_stream": "major_violent_crime",
        "case_real_name_zh": "公安部A级通缉犯武汉至三亚潜逃8年出租车司机伪装案 — 马汉庆 (1996–2004)",
        "archival_search_keywords_zh": [
            "马汉庆 三亚 落网 今日说法",
            "A级通缉犯 马汉庆 8年 天网",
            "武汉 马汉庆 侦破纪实"
        ],
        "recommended_vox_verbs": [
            "GEO_VECTOR_PURSUIT",
            "DUAL_ERA_LOCK",
            "CONCENTRIC_TRAP"
        ],
        "title": "[중국 실화 사건] 8년간 흔적조차 없던 공안부 A급 수배범이 3,000km 밖 휴양지 모범 택시기사로 살아온 두 얼굴 | 마한칭 도주 사건 ([Vụ Án Có Thật ở Trung Quốc] Hai bộ mặt của kẻ truy nã cấp A bốc hơi suốt 8 năm dưới vỏ bọc tài xế taxi gương mẫu ở thành phố biển cách 3.000km | Chuyên án Mã Hán Khánh)",
        "topic_anchor": "[중국 실화 사건] 8년간 흔적조차 없던 공안부 A급 수배범이 3,000km 밖 휴양지 모범 택시기사로 살아온 두 얼굴 | 마한칭 도주 사건",
        "winner_cluster": "Luồng 2 · 8 Năm Ẩn Mình Làm Tài Xế Taxi Tam Á & Cuộc Đấu Trí Truy Nã Cấp A (마한칭 8년 도주 사건)",
        "codex_score": 96,
        "profile_score": 96,
        "codex_angle": "Hồ Sơ Thật 100%: Mã Hán Khánh (马汉庆, 1996–2004) — Từ Vũ Hán Đến Tân Cương Và 8 Năm Sống Dưới Tên Giả 'Châu Quân' Giữa Thành Phố Du Lịch Tam Á (Hải Nam)",
        "codex_reasons": [
            "Tội phạm truy nã cấp A nổi tiếng của Bộ Công an Trung Quốc với video bắt giữ thực địa tại Tam Á năm 2004 trên CCTV",
            "Cấu trúc truy vết xuyên không gian Vũ Hán - Ô Lỗ Mộc Tề - Tam Á cực hợp với bản đồ 3D GEO_VECTOR_PURSUIT"
        ],
        "opening_hook": "중국 공안부가 가장 높은 현상금을 걸고 전국을 뒤졌던 A급 수배범 마한칭. 모두가 그가 국경 너머로 밀항했을 것이라 생각했지만, 그는 오히려 관광객들로 북적이는 남쪽 끝 휴양 도시 싼야에서 8년 동안 평범한 택시 운전사로 살아가고 있었습니다.",
        "note": "【Hồ sơ vụ án: trọng án liên hoàn tước đoạt 7 sinh mạng · lệnh truy nã cấp A bộ công an · ẩn mình lái taxi ở Tam Á suốt 8 năm】 Hồ sơ thật 100% Chuyên án truy nã cấp A Mã Hán Khánh (马汉庆, Vũ Hán, 1996–2004): Sau vụ cướp trước cổng Nhà máy Hóa chất Hữu cơ Vũ Hán tháng 1/1996 và các vụ án tại Tân Cương, Mã Hán Khánh dùng CMND giả tên 'Châu Quân' (周军) trốn xuống thành phố Tam Á (Hải Nam) mua xe chạy taxi và lập gia đình suốt 8 năm trước khi bị bắt ngày 11/11/2004.",
        "hook_archetype": "double_life_unmasking"
    },
    {
        "id": "vio_cn_xiaoshan_taxi_28y_dna",
        "topic_stream": "major_violent_crime",
        "case_real_name_zh": "浙江杭州萧山1995年两起出租车命案积案28年侦破 — 项生源 (1995–2023)",
        "archival_search_keywords_zh": [
            "萧山1995案 项生源 今日说法",
            "杭州萧山 28年 命案积案 侦破",
            "萧山出租车悬案 28年"
        ],
        "recommended_vox_verbs": [
            "MICRO_TRACE_MATCH",
            "DUAL_ERA_LOCK",
            "ALIBI_SHATTER"
        ],
        "title": "[중국 실화 사건] 억울하게 갇힌 다섯 청년의 운명을 바꾼 28년 전 봉인 증거 상자 속 담배꽁초 하나의 비밀 | 샤오산 택시 미제사건 ([Vụ Án Có Thật ở Trung Quốc] Bí mật đầu lọc thuốc lá nằm trong thùng vật chứng niêm phong 28 năm giải oan cho 5 thanh niên bị bắt nhầm | Kỳ án Tiêu Sơn)",
        "topic_anchor": "[중국 실화 사건] 억울하게 갇힌 다섯 청년의 운명을 바꾼 28년 전 봉인 증거 상자 속 담배꽁초 하나의 비밀 | 샤오산 택시 미제사건",
        "winner_cluster": "Luồng 2 · Đầu Lọc Thuốc Lá Lưu Trữ 28 Năm Lật Lại Kỳ Án Tiêu Sơn Hàng Châu (항저우 샤오산 항생원 사건)",
        "codex_score": 97,
        "profile_score": 97,
        "codex_angle": "Hồ Sơ Thật 100%: Kỳ Án Tiêu Sơn Năm 1995 & Hung Thủ Hạng Sinh Nguyên (项生源) — Cách Khoa Học Pháp Y ADN Lưu Giữ Trên Đầu Lọc Thuốc Lá Tìm Ra Chân Tướng Sau Gần 3 Thập Kỷ",
        "codex_reasons": [
            "Một trong những vụ án minh oan và truy tìm hung thủ thật nổi tiếng nhất lịch sử tư pháp Trung Quốc (CCTV 今日说法 phát sóng nhiều kỳ)",
            "Giá trị nhân văn & khoa học pháp y đỉnh cao: một mẫu vật chứng nhỏ được bảo quản cẩn thận giúp tìm ra hung thủ thật Hạng Sinh Nguyên"
        ],
        "opening_hook": "1995년 저장성 샤오산의 도로변에 멈춰 선 택시 안에서 발견된 작은 담배꽁초 하나. 당시 기술로는 주인을 알 수 없었던 그 미세한 흔적이 십팔 년 뒤 억울한 누명을 벗겨내는 결정적 열쇠가 되었고, 마침내 이십팔 년 만에 진짜 범인 항생원의 이름을 세상에 불러냈습니다.",
        "note": "【Hồ sơ vụ án: trọng án liên hoàn tước đoạt sinh mạng 2 nữ tài xế taxi · án lạnh 28 năm minh oan và bắt hung thủ thật bằng ADN đầu lọc thuốc lá】 Hồ sơ thật 100% Kỳ án hai tài xế taxi tại Tiêu Sơn, Hàng Châu năm 1995 (浙江萧山1995年命案积案 — Hạng Sinh Nguyên 项生源): Nhờ bảo quản nghiêm ngặt đầu lọc thuốc lá và dấu vân tay tại hiện trường năm 1995, cơ quan giám định pháp y Chiết Giang đã xác định được hung thủ thật Hạng Sinh Nguyên, khép lại kỳ án kéo dài gần 3 thập kỷ.",
        "hook_archetype": "cold_archive_match"
    },
    {
        "id": "vio_cn_dong_wenyu_6prov_manhunt",
        "topic_stream": "major_violent_crime",
        "case_real_name_zh": "公安部A级通缉令跨6省流窜特大案件侦破纪实 — 董文语 (2006)",
        "archival_search_keywords_zh": [
            "董文语 A级通缉 侦破纪实 今日说法",
            "跨6省追捕 董文语 天网",
            "四川宜宾 董文语 落网"
        ],
        "recommended_vox_verbs": [
            "GEO_VECTOR_PURSUIT",
            "FORENSIC_ZOOM_CHAIN",
            "CONCENTRIC_TRAP"
        ],
        "title": "[중국 실화 사건] 공안부 A급 수배범이 6개 성 검문소를 피해 오직 깊은 산속과 절벽만 걸어 다닌 이유 | 둥원위 도주 사건 ([Vụ Án Có Thật ở Trung Quốc] Lý do kẻ truy nã cấp A Bộ Công an né sạch mọi trạm kiểm soát xuyên 6 tỉnh bằng cách chỉ đi bộ trong rừng sâu | Chuyên án Đổng Văn Ngữ)",
        "topic_anchor": "[중국 실화 사건] 공안부 A급 수배범이 6개 성 검문소를 피해 오직 깊은 산속과 절벽만 걸어 다닌 이유 | 둥원위 도주 사건",
        "winner_cluster": "Luồng 2 · Cuộc Truy Kích Xuyên 6 Tỉnh Bắt Nghi Phạm Ngủ Rừng Né Mọi Camera (둥원위 6개 성 추격 사건)",
        "codex_score": 95,
        "profile_score": 95,
        "codex_angle": "Hồ Sơ Thật 100%: Chuyên Án Đổng Văn Ngữ (董文语, 2006) — Phản Trinh Sát Hoang Dã Đi Dọc Đường Ray & Rừng Núi Xuyên Chiết Giang - Phúc Kiến - Giang Tây - Tứ Xuyên",
        "codex_reasons": [
            "Lệnh truy nã cấp A chấn động năm 2006 với hàng chục vạn cảnh sát và dân phòng lập chốt dọc 6 tỉnh, tư liệu phóng sự CCTV 天网 / 今日说法 cực đầy đủ",
            "100% Xanh tiền: tập trung vào khoa học phân tích dấu chân, giám định vân tay và chiến thuật bao vây địa hình rừng núi Nghi Tân (Tứ Xuyên)"
        ],
        "opening_hook": "신분증 검사를 피하기 위해 단 한 번도 여관이나 기차역을 이용하지 않고, 오직 밤에만 철길과 깊은 산속을 따라 여섯 개 성을 가로지른 남자가 있었습니다. 수만 장의 수배 전단이 마을마다 붙은 가운데, 쓰촨성 이빈시의 가파른 산비탈에서 발견된 낯선 발자국 하나가 대추격전의 마침표를 찍었습니다.",
        "note": "【Hồ sơ vụ án: đại án đột nhập ban đêm tước đoạt 6 sinh mạng xuyên 6 tỉnh · lệnh truy nã cấp A bộ công an · phản trinh sát ngủ rừng】 Hồ sơ thật 100% Chuyên án truy nã cấp A Đổng Văn Ngữ (董文语, 3–11/2006): Để né tránh toàn bộ hệ thống kiểm tra giấy tờ và camera tại nhà ga/khách sạn, Đổng Văn Ngữ chỉ di chuyển ban đêm dọc đường sắt và ngủ trong rừng núi xuyên 6 tỉnh (Chiết Giang, Phúc Kiến, Giang Tây, Hồ Nam, Quảng Tây, Tứ Xuyên) trước khi bị bắt tại núi Tượng Tỵ, Nghi Tân (Tứ Xuyên) ngày 16/11/2006.",
        "hook_archetype": "last_ordinary_routine"
    },
    {
        "id": "vio_cn_inner_mongolia_hugjilt_18y",
        "topic_stream": "major_violent_crime",
        "case_real_name_zh": "内蒙古呼和浩特4·9女厕案18年冤案平反与真凶落网 — 赵志红·呼格吉勒图 (1996–2014)",
        "archival_search_keywords_zh": [
            "呼格吉勒图 18年 冤案平反 央视新闻",
            "赵志红 偿命申请书 今日说法",
            "内蒙古 呼格案 再审无죄"
        ],
        "recommended_vox_verbs": [
            "SPLIT_PARADOX",
            "ALIBI_SHATTER",
            "DUAL_ERA_LOCK"
        ],
        "title": "[중국 실화 사건] 붙잡힌 진범이 감방에서 직접 쓴 1호 자백서로 18년 만에 뒤집힌 그날 밤의 진실 | 후거지러투 사건 ([Vụ Án Có Thật ở Trung Quốc] Sự thật đêm định mệnh được lật lại sau 18 năm nhờ tờ đơn thú tội số 1 viết từ buồng giam của hung thủ thật sự | Kỳ án Hô Cách Cát Lặc Đồ)",
        "topic_anchor": "[중국 실화 사건] 붙잡힌 진범이 감방에서 직접 쓴 1호 자백서로 18년 만에 뒤집힌 그날 밤의 진실 | 후거지러투 사건",
        "winner_cluster": "Luồng 2 · Đơn Thú Tội Trong Trại Giam & 18 Năm Lật Lại Bản Án Chấn Động Nội Mông (후거지러투·자오즈훙 사건)",
        "codex_score": 98,
        "profile_score": 98,
        "codex_angle": "Hồ Sơ Thật 100%: Kỳ Án Hô Cách Cát Lặc Đồ & Hung Thủ Thật Triệu Chí Hồng (内蒙古呼格案与真凶赵志红, 1996–2014) — Khi Kẻ Thủ Ác Tự Vẽ Lại Sơ Đồ Hiện Trường Năm 1996 Chính Xác Đến Từng Chi Tiết",
        "codex_reasons": [
            "Vụ án bước ngoặt lịch sử của nền tư pháp Trung Quốc (CCTV phát sóng trực tiếp phiên tòa tái thẩm tuyên vô tội tháng 12/2014, hàng triệu lượt xem)",
            "Chiều sâu tâm lý và điều tra cực kỳ xúc động, 100% Xanh tiền YouTube"
        ],
        "opening_hook": "2005년 가을, 네이멍구에서 검거된 연쇄 범죄자 자오즈훙이 심문 도중 형사들이 전혀 묻지 않은 구 년 전 사건 하나를 스스로 입에 올렸습니다. 이미 범인이 잡혀 사건이 종결된 지 오래였던 1996년 제1방직공장 골목 사건. 자오즈훙이 감방 안에서 직접 적은 한 장의 자백서가 중국 사법 역사를 뒤흔들기 시작했습니다.",
        "note": "【Hồ sơ vụ án: trọng án liên hoàn tước đoạt sinh mạng 10 phụ nữ · hung thủ thật Triệu Chí Hồng tự thú trong trại giam & đại án minh oan 18 năm】 Hồ sơ thật 100% Kỳ án Hô Cách Cát Lặc Đồ và chân tướng hung thủ Triệu Chí Hồng tại Hô Hòa Hạo Đặc, Nội Mông (内蒙古呼格吉勒图冤案平反与赵志红案, 1996–2014): Năm 2005 khi bị bắt, Triệu Chí Hồng khai nhận chính hắn mới là thủ phạm vụ án ngày 9/4/1996 và viết 'Đơn xin đền mạng' từ trong trại giam, dẫn tới phiên tòa tái thẩm lịch sử ngày 15/12/2014 minh oan hoàn toàn cho Hô Cách Cát Lặc Đồ.",
        "hook_archetype": "cold_archive_match"
    },
    {
        "id": "vio_cn_jiangxi_fuzhou_wan_guanghui_22y",
        "topic_stream": "major_violent_crime",
        "hook_archetype": "double_life_unmasking",
        "case_real_name_zh": "江西抚州公安部A级通缉命案逃犯潜逃22年洗白变身广东佛山千万建材富商案 — 万光辉 (1998–2020)",
        "archival_search_keywords_zh": [
            "万光辉 A级通缉犯 22年 今日说法",
            "江西抚州 万光辉 佛山 落网 央视",
            "潜逃22年 千万富商 万光辉 天网"
        ],
        "recommended_vox_verbs": [
            "SPLIT_PARADOX",
            "DUAL_ERA_LOCK",
            "GEO_VECTOR_PURSUIT"
        ],
        "title": "[중국 실화 사건] 22년간 증발했던 공안부 A급 수배범이 수백억 대 건자재 그룹 회장으로 신분을 세탁한 사연 | 푸저우 완광후이 사건 ([Vụ Án Có Thật ở Trung Quốc] Kẻ truy nã cấp A bốc hơi 22 năm tẩy trắng thân phận thành Chủ tịch Tập đoàn vật liệu xây dựng trăm tỷ | Chuyên án Vạn Quang Huy)",
        "topic_anchor": "[중국 실화 사건] 22년간 증발했던 공안부 A급 수배범이 수백억 대 건자재 그룹 회장으로 신분을 세탁한 사연 | 푸저우 완광후이 사건",
        "winner_cluster": "Luồng 2 · Tội Phạm Truy Nã Cấp A Đoạt Mạng Người Ẩn Mình 22 Năm Làm Chủ Tịch Tập Đoàn Vật Liệu Xây Dựng (푸저우 완광후이 사건)",
        "codex_score": 97,
        "profile_score": 97,
        "codex_angle": "Hồ Sơ Thật 100%: Vạn Quang Huy (万光辉, 1998–2020) — Trọng Án Đoạt Mạng Tại Phủ Châu (Giang Tây), Lệnh Truy Nã Cấp A Bộ Công An & 22 Năm Mang Tên Giả Làm Đại Gia Vật Liệu Xây Dựng Tại Phật Sơn",
        "codex_reasons": [
            "Đối tượng Truy nã Cấp A Bộ Công an lẩn trốn 22 năm dưới vỏ bọc doanh nhân giàu có tại Quảng Đông, phóng sự CCTV và Công an Giang Tây cực đầy đủ",
            "100% Cách viết Xanh tiền Đài truyền hình: tập trung vào màn tẩy trắng lý lịch và đối sánh sinh trắc học lật tẩy hai cuộc đời"
        ],
        "opening_hook": "광둥성 포산시에서 수백억 원대 건자재 유통 회사를 운영하며 고급 외제차를 몰던 성공한 기업가. 하지만 2020년 봄 장시성 형사들이 그의 사무실 문을 열고 잊혔던 본명 석 자를 부르자, 22년 동안 완벽하게 유지되던 회장의 가면이 단숨에 무너져 내렸습니다.",
        "note": "【Hồ sơ vụ án: trọng án tước đoạt sinh mạng nạn nhân · lệnh truy nã cấp A bộ công an · tẩy trắng thân phận 22 năm】 Hồ sơ thật 100% Chuyên án Vạn Quang Huy tại Phủ Châu, Giang Tây (江西抚州公安部A级通缉犯万光辉潜逃22年落网案, 1998–2020): Sau khi cầm đầu trọng án tước đoạt sinh mạng nạn nhân năm 1998 và bị Bộ Công an phát lệnh truy nã cấp A toàn quốc, Vạn Quang Huy trốn xuống Phật Sơn (Quảng Đông), mua hộ khẩu giả mở công ty vật liệu xây dựng quy mô hàng chục triệu NDT suốt 22 năm trước khi bị Công an Giang Tây đối sánh sinh trắc học bắt giữ tháng 5/2020."
    },
    {
        "id": "vio_cn_shandong_weifang_xu_dapeng_21y",
        "topic_stream": "major_violent_crime",
        "hook_archetype": "last_ordinary_routine",
        "case_real_name_zh": "山东潍坊重特大命案公安部A级通缉犯潜逃21年藏身天津废品场落网案 — 徐大鹏 (1999–2020)",
        "archival_search_keywords_zh": [
            "徐大鹏 A级通缉犯 21年 今日说法",
            "山东潍坊 徐大鹏 天津 落网 天网",
            "公安部A级通缉令 徐大鹏 侦破"
        ],
        "recommended_vox_verbs": [
            "GEO_VECTOR_PURSUIT",
            "FORENSIC_ZOOM_CHAIN",
            "DUAL_ERA_LOCK"
        ],
        "title": "[중국 실화 사건] 공안부 A급 수배범이 21년간 신분증도 은행 계좌도 없이 외곽 폐기물 야적장에 숨어 산 이유 | 웨이팡 쉬다펑 추적 사건 ([Vụ Án Có Thật ở Trung Quốc] Lý do kẻ truy nã cấp A sống ẩn dật 21 năm không giấy tờ, không tài khoản ngân hàng giữa bãi phế liệu | Chuyên án Từ Đại Bằng Duy Phường)",
        "topic_anchor": "[중국 실화 사건] 공안부 A급 수배범이 21년간 신분증도 은행 계좌도 없이 외곽 폐기물 야적장에 숨어 산 이유 | 웨이팡 쉬다펑 추적 사건",
        "winner_cluster": "Luồng 2 · Truy Nã Cấp A Trọng Án Đoạt Mạng 2 Người & 21 Năm Ẩn Náu Không Giấy Tờ Tại Thiên Tân (웨이팡 쉬다펑 21년 추적 사건)",
        "codex_score": 96,
        "profile_score": 96,
        "codex_angle": "Hồ Sơ Thật 100%: Từ Đại Bằng (徐大鹏, 1999–2020) — Trọng Án Tước Đoạt 2 Sinh Mạng Tại Sơn Đông, Lệnh Truy Nã Cấp A Bộ Công An & 21 Năm Sống Bóng Đêm Giữa Bãi Phế Liệu Ngoại Ô Thiên Tân",
        "codex_reasons": [
            "Chuyên án truy bắt đối tượng Truy nã Cấp A Bộ Công an lẩn trốn hơn 2 thập kỷ, nhiều tư liệu điều tra hiện trường của Công an Sơn Đông & Thiên Tân",
            "100% Xanh tiền YouTube: khắc họa cuộc truy vết kiên trì 21 năm và tâm lý phản trinh sát tuyệt vọng của kẻ trốn nã"
        ],
        "opening_hook": "기차표를 사지도, 은행 계좌를 열지도, 심지어 아파도 병원에 가지 않은 채 스물한 해를 그림자처럼 살아온 남자가 있었습니다. 톈진 외곽의 거대한 폐기물 야적장 구석 컨테이너에서 마침내 수갑이 채워졌을 때, 그는 공안부 A급 수배 명단에 오른 지 이십일 년 된 중대 수배범 쉬다펑이었습니다.",
        "note": "【Hồ sơ vụ án: trọng án tước đoạt 2 sinh mạng · lệnh truy nã cấp A bộ công an · lẩn trốn 21 năm】 Hồ sơ thật 100% Chuyên án truy nã cấp A Từ Đại Bằng tại Duy Phường, Sơn Đông (山东潍坊公安部A级通缉犯徐大鹏潜逃21年落网案, 1999–2020): Sau trọng án khiến 2 nạn nhân vĩnh viễn mất đi sinh mạng năm 1999 và bị Bộ Công an phát lệnh truy nã cấp A, Từ Đại Bằng cắt đứt mọi liên lạc gia đình, sống không chứng minh thư trong các bãi phế liệu vùng ven Thiên Tân suốt 21 năm trước khi bị Ban chuyên án khóa chặt dấu vết sinh học và bắt giữ năm 2020."
    },
    {
        "id": "vio_cn_shanxi_linfen_zhang_zelin_23y",
        "topic_stream": "major_violent_crime",
        "hook_archetype": "cold_archive_match",
        "case_real_name_zh": "山西临汾重特大命案公安部A级通缉犯潜逃23年隐姓埋名落网案 — 张泽林 (1997–2020)",
        "archival_search_keywords_zh": [
            "张泽林 A级通缉 23年 今日说法",
            "山西临汾 命案积案 张泽林 天网",
            "潜逃23年 A级逃犯 落网"
        ],
        "recommended_vox_verbs": [
            "GEO_VECTOR_PURSUIT",
            "MICRO_TRACE_MATCH",
            "CONCENTRIC_TRAP"
        ],
        "title": "[중국 실화 사건] 공안부 A급 수배범이 23년간 다섯 개 성을 떠돌며 이름도 사진도 없이 살아온 비밀 | 린펀 장쩌린 사건 ([Vụ Án Có Thật ở Trung Quốc] Bí mật kẻ truy nã cấp A xóa sạch tên tuổi và hình ảnh phiêu bạt qua 5 tỉnh suốt 23 năm | Chuyên án Trương Trạch Lâm Lâm Phần)",
        "topic_anchor": "[중국 실화 사건] 공안부 A급 수배범이 23년간 다섯 개 성을 떠돌며 이름도 사진도 없이 살아온 비밀 | 린펀 장쩌린 사건",
        "winner_cluster": "Luồng 2 · Lệnh Truy Nã Cấp A Trọng Án 3 Mạng Người & 23 Năm Truy Vết Xuyên 5 Tỉnh (산시성 린펀 장쩌린 사건)",
        "codex_score": 97,
        "profile_score": 97,
        "codex_angle": "Hồ Sơ Thật 100%: Trương Trạch Lâm (张泽林, 1997–2020) — Trọng Án Tước Đoạt 3 Sinh Mạng Tại Lâm Phần (Sơn Tây) & 23 Năm Phiêu Bạt Dưới Thân Phận Thợ Mộc Câm Lặng",
        "codex_reasons": [
            "Chuyên án trọng điểm Bộ Công an truy bắt đối tượng Truy nã Cấp A trốn 23 năm, giàu tư liệu điều tra và thẩm vấn",
            "100% Xanh tiền YouTube: tập trung vào bản đồ truy vết 5 tỉnh và đối sánh dữ liệu phả hệ hình sự"
        ],
        "opening_hook": "1997년 산시성 린펀에서 세 사람의 시간을 영원히 멈춰 세운 뒤 어둠 속으로 사라진 공안부 A급 수배범 장쩌린. 한 곳에 반년 이상 머물지 않는 철칙으로 스물세 해 동안 다섯 개 성을 떠돌았지만, 수사팀이 재구축한 미세 흔적 데이터베이스 앞에서는 끝내 걸음을 멈춰야 했습니다.",
        "note": "【Hồ sơ vụ án: trọng án tước đoạt 3 sinh mạng · lệnh truy nã cấp A bộ công an · phiêu bạt 5 tỉnh suốt 23 năm】 Hồ sơ thật 100% Chuyên án truy nã cấp A Trương Trạch Lâm tại Lâm Phần, Sơn Tây (山西临汾公安部A级通缉犯张泽林潜逃23年落网案, 1997–2020): Sau trọng án khiến 3 nạn nhân vĩnh viễn không trở về năm 1997, Trương Trạch Lâm bị Bộ Công an phát lệnh truy nã cấp A; hắn ẩn danh làm thợ mộc thời vụ di chuyển liên tục qua 5 tỉnh suốt 23 năm trước khi bị Công an Sơn Tây khóa chặt tọa độ và bắt giữ năm 2020."
    },
    {
        "id": "vio_cn_jilin_tv_dating_wugang_13y",
        "topic_stream": "major_violent_crime",
        "case_real_name_zh": "吉林吉林市命案逃犯潜逃13年化名刘浩登上电视相亲节目落网案 — 吴刚 (1998–2011)",
        "archival_search_keywords_zh": [
            "逃犯 上相亲节目 吴刚 刘浩 今日说法",
            "潜逃13年 电视相亲 落网 央视新闻",
            "吉林 吴刚 快乐成双 天网"
        ],
        "recommended_vox_verbs": [
            "SPLIT_PARADOX",
            "DUAL_ERA_LOCK",
            "FORENSIC_ZOOM_CHAIN"
        ],
        "title": "[중국 실화 사건] 13년간 완벽히 증발했던 수배범이 신분을 세탁해 전국 방송 TV 맞선 프로그램에 출연한 이유 | 지린 우강 사건 ([Vụ Án Có Thật ở Trung Quốc] Lý do kẻ truy nã bốc hơi suốt 13 năm lại tẩy trắng thân phận rồi ngang nhiên lên sóng truyền hình hẹn hò | Chuyên án Ngô Cương Cát Lâm)",
        "topic_anchor": "[중국 실화 사건] 13년간 완벽히 증발했던 수배범이 신분을 세탁해 전국 방송 TV 맞선 프로그램에 출연한 이유 | 지린 우강 사건",
        "winner_cluster": "Luồng 2 · Kẻ Truy Nã 13 Năm Tự Tin Lên Sóng Truyền Hình Hẹn Hò & Cú Điện Thoại Báo Án (지린 우강 TV 맞선 사건)",
        "codex_score": 97,
        "profile_score": 97,
        "codex_angle": "Hồ Sơ Thật 100%: Ngô Cương / Lưu Hạo (吉林逃犯吴刚上电视相亲落网案, 1998–2011) — Tâm Lý Ngạo Mạn Sau 13 Năm Đổi Tên Làm MC Đám Cưới Và Khoảnh Khắc Khán Giả Nhận Ra Kẻ Truy Nã Trên Tivi",
        "codex_reasons": [
            "Một trong những vụ bắt giữ tội phạm truy nã hy hữu và nổi tiếng nhất truyền hình Trung Quốc (có clip gốc chương trình truyền hình hẹn hò 《为爱向前冲》 / 《快乐成双》 phát trên CCTV)",
            "Nghịch lý tâm lý đỉnh cao cho SPLIT_PARADOX & DUAL_ERA_LOCK"
        ],
        "opening_hook": "화려한 조명이 켜진 인기 TV 맞선 프로그램 스튜디오. 멋진 정장을 차려입고 나와 노래를 부르며 여성 출연자의 손을 잡고 퇴장한 서른아홉 살의 웨딩 사회자 류하오. 하지만 방송이 전파를 타는 순간, 천 킬로미터 떨어진 북쪽 도시의 한 시청자가 텔레비전 화면을 가리키며 비명을 질렀습니다.",
        "note": "【Hồ sơ vụ án: trọng án tước đoạt sinh mạng 1 nạn nhân tại Cát Lâm · trốn nã 13 năm làm MC và bị bắt vì lên sóng truyền hình hẹn hò】 Hồ sơ thật 100% Vụ án Ngô Cương tại thành phố Cát Lâm (吉林命案逃犯吴刚上相亲节目落网案, 1998–2011): Sau trọng án năm 1998 tại Cát Lâm, Ngô Cương trốn xuống Thẩm Dương đổi tên thành 'Lưu Hạo' (刘浩), làm MC sự kiện suốt 13 năm; tháng 11/2010 hắn tự tin đăng ký tham gia chương trình hẹn hò trên truyền hình vệ tinh Hắc Long Giang và bị người quen cũ nhận diện báo Công an Cát Lâm bắt giữ tháng 6/2011.",
        "hook_archetype": "double_life_unmasking"
    },
    {
        "id": "vio_cn_harbin_yanshou_gaoyulun_9d",
        "topic_stream": "major_violent_crime",
        "case_real_name_zh": "黑龙江哈尔滨延寿县看守所9·2越狱1.5万警力9天大围捕案 — 高玉伦·王大民·李海伟 (2014)",
        "archival_search_keywords_zh": [
            "延寿看守所 越狱 高玉伦 今日说法",
            "哈尔滨 9·2越狱 9天大围捕 央视",
            "高玉伦 落网 天网"
        ],
        "recommended_vox_verbs": [
            "CONCENTRIC_TRAP",
            "GEO_VECTOR_PURSUIT",
            "RADIAL_TIME_PRESSURE"
        ],
        "title": "[중국 실화 사건] 새벽 4시 경찰 제복으로 갈아입고 구치소 정문을 걸어 나간 중대 수감자 3명의 탈출극 | 하얼빈 가오위룬 사건 ([Vụ Án Có Thật ở Trung Quốc] Màn đào thoát của 3 trọng phạm thay cảnh phục bước thẳng qua cổng chính trại giam lúc 4 giờ sáng | Chuyên án Cao Ngọc Luân Cáp Nhĩ Tân)",
        "topic_anchor": "[중국 실화 사건] 새벽 4시 경찰 제복으로 갈아입고 구치소 정문을 걸어 나간 중대 수감자 3명의 탈출극 | 하얼빈 가오위룬 사건",
        "winner_cluster": "Luồng 2 · Camera Ghi Hình Giây Phút Mặc Cảnh Phục Vượt Ngục & 216 Giờ Vây Ráp Núi Rừng (하얼빈 옌서우 가오위룬 사건)",
        "codex_score": 97,
        "profile_score": 97,
        "codex_angle": "Hồ Sơ Thật 100%: Đại Truy Bắt 9 Ngày Đêm Tại Diên Thọ, Cáp Nhĩ Tân (黑龙江延寿9·2越狱案 — Cao Ngọc Luân, Vương Đại Dân, Lý Hải Vĩ, 9/2014) — Trực Thăng Tuần Tiễu Và Vòng Vây Siết Chặt Từng Thôn Xóm",
        "codex_reasons": [
            "Tư liệu camera giám sát trong trại giam và video trực thăng truy bắt 9 ngày đêm của CCTV cực kỳ đầy đủ",
            "Khớp hoàn hảo bản đồ vây bắt 3D GEO_VECTOR_PURSUIT & CONCENTRIC_TRAP"
        ],
        "opening_hook": "2014년 9월 2일 새벽 네 시 사십사 분, 하얼빈 외곽 구치소의 복도 CCTV에 믿기 힘든 장면이 찍혔습니다. 수감복 대신 경찰 제복을 입은 세 명의 남자가 당당하게 철문을 열고 어둠 속으로 걸어 나간 것입니다. 날이 밝자 무려 일만 오천 명의 병력과 헬기가 산악 지대를 겹겹이 에워쌌습니다.",
        "note": "【Hồ sơ vụ án: trọng án đoạt mạng quản giáo trực ban để vượt ngục · lệnh truy nã cấp A bộ công an · 15.000 quân cảnh vây bắt 9 ngày đêm】 Hồ sơ thật 100% Chuyên án truy bắt 3 phạm nhân vượt trại tạm giam huyện Diên Thọ, Cáp Nhĩ Tân, Hắc Long Giang (黑龙江延寿9·2越狱案 — 高玉伦·王大民·李海伟, 2–11/9/2014): Bộ Công an và Công an Hắc Long Giang huy động 15.000 cảnh sát và trực thăng khép vòng vây suốt 9 ngày đêm, lần lượt bắt gọn cả 3 đối tượng.",
        "hook_archetype": "double_life_unmasking"
    },
    {
        "id": "vio_cn_fujian_liuzhaohua_bicycle_9y",
        "topic_stream": "major_violent_crime",
        "case_real_name_zh": "公安部A级通缉令头号嫌犯骑自行车突破封锁潜逃9年变身桂林3亿富商案 — 刘招华 (1996–2005)",
        "archival_search_keywords_zh": [
            "刘招华 骑自行车 桂林 今日说法",
            "A级通缉 刘招华 9年 天网",
            "福建福安 刘招华 抓捕纪实"
        ],
        "recommended_vox_verbs": [
            "SPLIT_PARADOX",
            "GEO_VECTOR_PURSUIT",
            "DUAL_ERA_LOCK"
        ],
        "title": "[중국 실화 사건] 무장 검문소를 자전거 하나로 통과해 사라진 공안부 A급 1호 수배범이 3억 회장이 된 사연 | 류자오화 두 얼굴 사건 ([Vụ Án Có Thật ở Trung Quốc] Kẻ truy nã cấp A số 1 đạp xe qua trạm gác vũ trang rồi 9 năm đóng vai Chủ tịch tập đoàn 300 triệu tệ | Chuyên án Lưu Chiêu Hoa)",
        "topic_anchor": "[중국 실화 사건] 무장 검문소를 자전거 하나로 통과해 사라진 공안부 A급 1호 수배범이 3억 회장이 된 사연 | 류자오화 두 얼굴 사건",
        "winner_cluster": "Luồng 2 · Đạp Xe Đạp Qua Trạm Kiểm Soát & 9 Năm Ẩn Mình Thành Đại Gia Sinh Thái Quế Lâm (류자오화 9년 도주 사건)",
        "codex_score": 98,
        "profile_score": 98,
        "codex_angle": "Hồ Sơ Thật 100%: Lưu Chiêu Hoa (刘招华, 1996–2005) — Kẻ Truy Nã Cấp A Có Tâm Lý Phản Trinh Sát Lạnh Lùng Bậc Nhất Lịch Sử Hình Sự Trung Quốc Và Chiến Dịch 'Tróc Mộc Điểu' Đúng Ngày Sinh Nhật",
        "codex_reasons": [
            "Một trong những hồ sơ tội phạm IQ cao và phản trinh sát nổi tiếng nhất trên CCTV 今日说法 / 天网 (lên báo địa phương vì bắt trộm dũng cảm trong lúc đang bị truy nã cấp A!)",
            "Tư liệu video bắt giữ thực tế đêm 5/3/2005 và thẩm vấn trực diện cực kỳ đắt giá"
        ],
        "opening_hook": "모든 고속도로와 항구가 봉쇄된 가운데, 수배 전단 속 남자는 자동차 대신 낡은 자전거 한 대를 타고 검문소 경찰들 앞을 유유히 지나갔습니다. 그로부터 구 년 동안 광시성 구이린에서 삼억 위안대 유명 사업가 '리썬칭'으로 살며 심지어 지역 신문에 용감한 시민으로 실리기까지 했던 A급 수배범 류자오화를 추적합니다.",
        "note": "【Hồ sơ vụ án: trọng án đoạt mạng người & điều chế 12 tấn tinh thể độc hại lớn nhất thế giới · lệnh truy nã cấp A số 1 bộ công an · trốn 9 năm】 Hồ sơ thật 100% Chuyên án truy nã cấp A Lưu Chiêu Hoa (刘招华, 1996–2005): Nổi tiếng với tâm lý phản trinh sát cực đoan — đạp xe đạp vượt vòng vây tại Quảng Đông năm 1999, đổi tên thành 'Lý Sâm Thanh' (李森青) đến Quế Lâm (Quảng Tây) mở công ty lâm nghiệp sinh thái 300 triệu tệ suốt 9 năm trước khi bị bắt trong chiến dịch 'Tróc Mộc Điểu' đúng ngày sinh nhật 5/3/2005.",
        "hook_archetype": "last_ordinary_routine"
    },
    {
        "id": "vio_cn_sichuan_liuhan_40b_mask",
        "topic_stream": "major_violent_crime",
        "case_real_name_zh": "四川汉龙集团400亿元矿业首富双面人生与公安部1·10专案 — 刘汉·刘维 (1998–2015)",
        "archival_search_keywords_zh": [
            "四川刘汉 400亿 庭审 央视新闻",
            "1·10专案 刘汉 刘维 纪录片",
            "汉龙集团 刘汉 今日说法"
        ],
        "recommended_vox_verbs": [
            "SPLIT_PARADOX",
            "NETWORK_GRAPH",
            "ALIBI_SHATTER"
        ],
        "title": "[중국 실화 사건] 낮에는 400억 자선 재벌, 밤에는 공안부 A급 수배범 동생을 숨긴 지하 제국의 두 얼굴 | 쓰촨 류한 사건 ([Vụ Án Có Thật ở Trung Quốc] Ban ngày là tỷ phú từ thiện 40 tỷ tệ, ban đêm che giấu em trai truy nã cấp A suốt nhiều năm | Đại án Lưu Hán Tứ Xuyên)",
        "topic_anchor": "[중국 실화 사건] 낮에는 400억 자선 재벌, 밤에는 공안부 A급 수배범 동생을 숨긴 지하 제국의 두 얼굴 | 쓰촨 류한 사건",
        "winner_cluster": "Luồng 2 · Tỷ Phú Khoáng Sản 40 Tỷ Tệ & Chuyên Án 1·10 Của Bộ Công An Tại Hàm Ninh (쓰촨 한룽그룹 류한 사건)",
        "codex_score": 98,
        "profile_score": 98,
        "codex_angle": "Hồ Sơ Thật 100%: Lưu Hán & Tập Đoàn Hán Long 40 Tỷ NDT (四川刘汉1·10专案, 2013–2015) — Khi Tỷ Phú Trên Bảng Xếp Hạng Forbes Bị Bắt Ngay Tại Sân Bay Quốc Tế Bắc Kinh",
        "codex_reasons": [
            "Một trong những chuyên án lớn nhất thế kỷ 21 của Bộ Công an Trung Quốc, truyền hình trực tiếp phiên tòa 17 ngày tại Hàm Ninh (Hồ Bắc) với hàng trăm giờ tư liệu CCTV",
            "100% Xanh tiền: tập trung vào mạng lưới tài chính - quyền lực ngầm và cuộc đấu trí tại tòa án"
        ],
        "opening_hook": "사천억 원이 넘는 기부를 하며 포브스 선정 자선가 명단에 이름을 올렸던 사백억 위안대 광산 재벌 류한. 하지만 공안부 특별수사팀이 그의 비밀 별장을 급습했을 때, 그곳에는 사 년 동안 전국에 A급 수배령이 내려진 친동생 류웨이가 숨어 지내고 있었습니다.",
        "note": "【Hồ sơ vụ án: đại án tập đoàn ngầm tước đoạt 9 sinh mạng & che giấu em trai truy nã cấp A · chuyên án 1·10 bộ công an Trung Quốc】 Hồ sơ thật 100% Chuyên án 1·10 của Bộ Công an đối với Tập đoàn Hán Long tại Tứ Xuyên (四川汉龙集团刘汉·刘维特大专案, 2013–2015): Dưới vỏ bọc tỷ phú khoáng sản và thủy điện sở hữu 40 tỷ NDT, Lưu Hán thao túng ngầm địa phương và che giấu em trai Lưu Duy đang bị Bộ Công an truy nã cấp A suốt 4 năm trước khi bị bắt tại Bắc Kinh và xét xử tại Tòa án Hàm Ninh (Hồ Bắc).",
        "hook_archetype": "double_life_unmasking"
    },
    {
        "id": "vio_cn_guangdong_huyihua_80h_suit",
        "topic_stream": "major_violent_crime",
        "case_real_name_zh": "粤闽跨省高速服务区重案公安部A级通缉80小时极速追缉案 — 胡益华 (2010)",
        "archival_search_keywords_zh": [
            "胡益华 80小时 抓捕 今日说法",
            "厦门 胡益华 A级通缉 天网",
            "广东揭阳 胡益华 侦破纪实"
        ],
        "recommended_vox_verbs": [
            "RADIAL_TIME_PRESSURE",
            "GEO_VECTOR_PURSUIT",
            "FORENSIC_ZOOM_CHAIN"
        ],
        "title": "[중국 실화 사건] 고급 외제차를 몰고 400km를 도주한 공안부 A급 수배범이 정장 차림으로 영화관에 나타난 이유 | 후이화 사건 ([Vụ Án Có Thật ở Trung Quốc] Lý do kẻ truy nã cấp A lái xe sang trốn chạy 400km lại thản nhiên mặc vest ngồi uống cà phê trước rạp phim | Chuyên án Hồ Ích Hoa)",
        "topic_anchor": "[중국 실화 사건] 고급 외제차를 몰고 400km를 도주한 공안부 A급 수배범이 정장 차림으로 영화관에 나타난 이유 | 후이화 사건",
        "winner_cluster": "Luồng 2 · 80 Giờ Truy Vết Dấu Ngân Hàng & Phục Kích Bắt Sống Tại Hạ Môn (후이화 80시간 광역 추적 사건)",
        "codex_score": 96,
        "profile_score": 96,
        "codex_angle": "Hồ Sơ Thật 100%: Hồ Ích Hoa (胡益华, 7/2010) — 80 Giờ Đếm Ngược Xuyên Chiết Giang - Quảng Đông - Phúc Kiến Và Đoạn Video Bắt Giữ Không Kịp Rút Súng Giữa Đường Phố Hạ Môn",
        "codex_reasons": [
            "Video bắt giữ thực tế tại Hạ Môn trên CCTV cực kỳ nổi tiếng: cảnh sát đặc nhiệm đóng giả người đi đường quật ngã Hồ Ích Hoa chỉ trong 3 giây",
            "Khớp hoàn hảo RADIAL_TIME_PRESSURE & GEO_VECTOR_PURSUIT"
        ],
        "opening_hook": "모두가 초췌한 행색의 도망자를 찾고 있을 때, A급 수배범 후이화는 최고급 정장에 선글라스를 끼고 독서광 행세를 하며 네 개 도시의 검문망을 빠져나갔습니다. 사건 발생 여든 시간째, 샤먼 시내 호텔 앞에서 사복 형사들이 그의 어깨를 덮치기 직전까지도 그의 주머니 속에는 위조 신분증과 도주 자금이 들어 있었습니다.",
        "note": "【Hồ sơ vụ án: trọng án liên hoàn tước đoạt 4 sinh mạng (2 doanh nhân & 2 cảnh sát giao thông) · lệnh truy nã cấp A bộ công an · 80 giờ truy kích】 Hồ sơ thật 100% Chuyên án 80 giờ truy bắt kẻ truy nã cấp A Hồ Ích Hoa xuyên Chiết Giang - Quảng Đông - Phúc Kiến (粤闽跨省追捕胡益华案, 7/2010): Sau vụ án tại trạm dừng nghỉ cao tốc Huệ Lai (Quảng Đông) đêm 5/7/2010, Bộ Công an phát lệnh truy nã cấp A; chỉ sau 80 giờ truy vết tín hiệu thẻ ngân hàng và camera giao thông, lực lượng đặc nhiệm đã bắt sống Hồ Ích Hoa tại Hạ Môn (Phúc Kiến) ngày 8/7/2010.",
        "hook_archetype": "last_ordinary_routine"
    },
    {
        "id": "vio_cn_xian_weizhenhai_copper_wire",
        "topic_stream": "major_violent_crime",
        "case_real_name_zh": "陕西西安看守所铜丝磨断铁镣越狱与21个月跨省缉捕纪实 — 魏振海 (1988–1990)",
        "archival_search_keywords_zh": [
            "西安 魏振海 越狱 侦破纪实",
            "陕西西安 魏振海 抓捕 纪录片",
            "道北 魏振海 档案"
        ],
        "recommended_vox_verbs": [
            "SINGLE_EVIDENCE_AUTOPSY",
            "CONCENTRIC_TRAP",
            "RADIAL_TIME_PRESSURE"
        ],
        "title": "[중국 실화 사건] 구두창 속에 숨긴 구리선 하나로 감방 쇠족쇄를 갈아내고 증발한 특급 수배범의 정체 | 시안 웨이전하이 사건 ([Vụ Án Có Thật ở Trung Quốc] Chân tướng kẻ truy nã đặc biệt giấu 1 sợi dây đồng trong đế giày mài đứt xiềng sắt buồng giam rồi biến mất | Chuyên án Ngụy Chấn Hải Tây An)",
        "topic_anchor": "[중국 실화 사건] 구두창 속에 숨긴 구리선 하나로 감방 쇠족쇄를 갈아내고 증발한 특급 수배범의 정체 | 시안 웨이전하이 사건",
        "winner_cluster": "Luồng 2 · Sợi Dây Đồng Mài Đứt Xiềng Sắt & 21 Tháng Đấu Trí Của Công An Tây An (시안 웨이전하이 탈옥 추적 사건)",
        "codex_score": 96,
        "profile_score": 96,
        "codex_angle": "Hồ Sơ Thật 100%: Chuyên Án Ngụy Chấn Hải Tại Tây An, Thiểm Tây (陕西西安魏振海越狱追捕案) — Giải Phẫu Kỹ Thuật Vượt Ngục Không Tưởng & Mật Lệnh Phục Kích Đêm 30/1/1990",
        "codex_reasons": [
            "Một trong những chuyên án hình sự kinh điển nhất lịch sử Công an Tây An với tư liệu phim tài liệu lưu trữ cực kỳ chi tiết",
            "100% Xanh tiền: tập trung vào màn vượt ngục tinh vi và chiến thuật giăng lưới bắt sống"
        ],
        "opening_hook": "발목에 채워진 칠 킬로그램짜리 굵은 쇠족쇄, 그리고 이중 철창으로 가로막힌 독방. 그러나 수감자 웨이전하이는 신발 밑창 속에 몰래 숨겨 반입한 가는 금속선 하나로 수개월 동안 밤마다 쇠사슬을 갈아냈고, 폭우가 쏟아지던 밤 천둥소리를 틈타 감옥 담장을 넘어 사라졌습니다.",
        "note": "【Hồ sơ vụ án: đại án liên hoàn tước đoạt 11 sinh mạng tại Tây An · trùm tội phạm số 1 cưa xiềng sắt vượt ngục & 21 tháng vây bắt】 Hồ sơ thật 100% Chuyên án Ngụy Chấn Hải tại Tây An, Thiểm Tây (陕西西安魏振海越狱追捕案, 1988–1990): Sau khi bị bắt năm 1987, Ngụy Chấn Hải dùng dụng cụ kim loại mảnh giấu trong đế giày cưa đứt xiềng chân và khoét tường vượt ngục trong đêm mưa; Công an Tây An lập tổ chuyên án mật truy lùng suốt 21 tháng và bắt sống hắn ngày 30/1/1990.",
        "hook_archetype": "micro_forensic_anomaly"
    },
    {
        "id": "vio_cn_anyang_lihui_cosmetics_ceo_13y",
        "topic_stream": "major_violent_crime",
        "case_real_name_zh": "河南安阳重案逃犯潜逃13年漂白身份变身山东亿万化妆品集团董事长案 — 李辉 (2001–2014)",
        "archival_search_keywords_zh": [
            "逃犯 变身 化妆品 董事长 今日说法",
            "潜逃13年 亿万富翁 李辉 天网",
            "河南安阳 命案逃犯 董事长"
        ],
        "recommended_vox_verbs": [
            "DUAL_ERA_LOCK",
            "SPLIT_PARADOX",
            "SCALE_MULTIPLICATION"
        ],
        "title": "[중국 실화 사건] 13년간 흔적도 없이 증발했던 지명수배범이 수백 명 직원을 거느린 억대 화장품 그룹 회장이었다니 | 안양 리후이 사건 ([Vụ Án Có Thật ở Trung Quốc] Kẻ truy nã trọng án bốc hơi không dấu vết suốt 13 năm hóa ra đã trở thành Chủ tịch Tập đoàn Mỹ phẩm trăm tỷ | Hai bộ mặt của Lý Huy)",
        "topic_anchor": "[중국 실화 사건] 13년간 흔적도 없이 증발했던 지명수배범이 수백 명 직원을 거느린 억대 화장품 그룹 회장이었다니 | 안양 리후이 사건",
        "winner_cluster": "Luồng 2 · Kẻ Truy Nã Đổi Tên Xây Đế Chế Mỹ Phẩm & Cú Nhận Diện Ngay Trong Phòng Họp HĐQT (안양 리후이 화장품 회장 사건)",
        "codex_score": 97,
        "profile_score": 97,
        "codex_angle": "Hồ Sơ Thật 100%: Lý Huy (李辉, Hà Nam - Sơn Đông 2001–2014) — Bắt Đầu Từ Nhân Viên Tiếp Thị Quèn Trở Thành Chủ Tịch Tập Đoàn Mỹ Phẩm Lớn Nhưng Không Bao Giờ Dám Chụp Ảnh Chung Với Nhân Viên",
        "codex_reasons": [
            "Chi tiết tâm lý cực kỳ đắt giá: dù là chủ tịch tập đoàn lớn có xe sang biệt thự nhưng suốt 13 năm không bao giờ dám xuất hiện trước ống kính máy ảnh hay đi máy bay",
            "Khớp hoàn hảo DUAL_ERA_LOCK & SPLIT_PARADOX"
        ],
        "opening_hook": "수백 명의 직원을 거느린 유명 화장품 회사의 회장님에게는 이상한 습관이 하나 있었습니다. 회사가 아무리 큰 상을 받아도 절대로 언론 인터뷰나 기념사진 촬영 자리에 얼굴을 비치지 않는 것이었습니다. 십삼 년 뒤 경찰이 회장실 문을 열었을 때, 그의 서랍 속에서 진짜 이름이 적힌 과거의 조각이 나왔습니다.",
        "note": "【Hồ sơ vụ án: trọng án tước đoạt sinh mạng nạn nhân tại An Dương · trốn nã 13 năm tẩy trắng thành chủ tịch tập đoàn mỹ phẩm】 Hồ sơ thật 100% Chuyên án Lý Huy (河南安阳重案逃犯潜逃13年变身千万富翁案, 2001–2014): Sau trọng án tại An Dương (Hà Nam) năm 2001, Lý Huy trốn sang Tế Nam (Sơn Đông) mua hộ khẩu giả, đi bán hàng mỹ phẩm dạo rồi mở công ty riêng phát triển thành tập đoàn trị giá hàng chục triệu NDT suốt 13 năm trước khi bị cảnh sát bắt giữ ngay tại văn phòng chủ tịch.",
        "hook_archetype": "last_ordinary_routine"
    },
    {
        "id": "vio_cn_jiangxi_zengchunliang_drone_8d",
        "topic_stream": "major_violent_crime",
        "case_real_name_zh": "江西乐安4000警力与热成像无人机8天山林大围捕案 — 曾春亮 (2020)",
        "archival_search_keywords_zh": [
            "江西乐安 曾春亮 4000警力 抓捕 央视",
            "曾春亮 8天 大围捕 纪实",
            "江西抚州 曾春亮 落网"
        ],
        "recommended_vox_verbs": [
            "GEO_VECTOR_PURSUIT",
            "CONCENTRIC_TRAP",
            "RADIAL_TIME_PRESSURE"
        ],
        "title": "[중국 실화 사건] 산악 마을을 공포에 빠뜨린 공안부 특급 수배범이 대낮에 오토바이를 타고 검문소를 노린 이유 | 러안 쩡춘량 사건 ([Vụ Án Có Thật ở Trung Quốc] Kẻ truy nã đặc biệt nguy hiểm ẩn náu trong vùng núi hiểm trở ngang nhiên phóng xe máy giữa ban ngày | Chuyên án Tăng Xuân Lượng)",
        "topic_anchor": "[중국 실화 사건] 산악 마을을 공포에 빠뜨린 공안부 특급 수배범이 대낮에 오토바이를 타고 검문소를 노린 이유 | 러안 쩡춘량 사건",
        "winner_cluster": "Luồng 2 · 4.000 Quân Cảnh & Drone Tầm Nhiệt Khóa Chặt Rừng Núi Lạc An Suốt 192 Giờ (장시성 러안현 쩡춘량 추격전)",
        "codex_score": 96,
        "profile_score": 96,
        "codex_angle": "Hồ Sơ Thật 100%: 192 Giờ Vây Bắt Tăng Xuân Lượng Tại Lạc An, Giang Tây (江西乐安4000警力搜山抓捕案, 8/2020) — Bản Đồ Tác Chiến Phong Tỏa Mọi Lối Ra Khỏi Rừng Sâu",
        "codex_reasons": [
            "Một trong những chiến dịch vây bắt quy mô lớn nhất năm 2020 với đầy đủ tư liệu hiện trường của CCTV (chốt kiểm soát, chó nghiệp vụ, drone nhiệt và khoảnh khắc bắt giữ trên xe máy ngày 16/8/2020)",
            "100% Xanh tiền: tập trung vào bản đồ chiến thuật vây ráp 4.000 cảnh sát"
        ],
        "opening_hook": "사방이 험준한 산림으로 둘러싸인 장시성 러안현. 도주한 수배범 쩡춘량을 잡기 위해 사천 명이 넘는 경찰과 무장 병력이 모든 산길 입구에 백 개가 넘는 검문소를 세웠습니다. 열화상 드론이 밤하늘을 수색하는 가운데, 여드레 만에 오토바이를 타고 포위망을 뚫으려던 그가 마지막 저지선에 걸려들었습니다.",
        "note": "【Hồ sơ vụ án: trọng án liên hoàn tước đoạt 3 sinh mạng tại Giang Tây · truy nã đặc biệt nguy hiểm · 4.000 quân cảnh và drone tầm nhiệt vây bắt 8 ngày】 Hồ sơ thật 100% Chiến dịch 8 ngày đêm truy bắt Tăng Xuân Lượng tại huyện Lạc An, Phủ Châu, Giang Tây (江西乐安曾春亮大搜捕案, 8–16/8/2020): Công an tỉnh Giang Tây huy động hơn 4.000 cảnh sát, chó nghiệp vụ và drone tầm nhiệt thiết lập 3 vòng vây đồng tâm quanh khu vực rừng núi Lạc An, bắt sống Tăng Xuân Lượng khi hắn tìm cách phóng xe máy vượt chốt ngày 16/8/2020.",
        "hook_archetype": "double_life_unmasking"
    },
    {
        "id": "vio_cn_hohhot_prison_tunnel_76h",
        "topic_stream": "major_violent_crime",
        "case_real_name_zh": "内蒙古呼和浩特第二监狱10·17越狱76小时跨省大追捕案 — 乔海强·高博·董佳继 (2009)",
        "archival_search_keywords_zh": [
            "呼和浩特 10·17越狱 76小时 今日说法",
            "内蒙古第二监狱 越狱 抓捕 央视",
            "乔海强 76小时 大追捕"
        ],
        "recommended_vox_verbs": [
            "RADIAL_TIME_PRESSURE",
            "GEO_VECTOR_PURSUIT",
            "CONCENTRIC_TRAP"
        ],
        "title": "[중국 실화 사건] 교도관 출입 카드로 철문 4개를 차례로 열고 정문을 빠져나간 중대 수감자 4명의 공모 | 후허하오터 구치소 사건 ([Vụ Án Có Thật ở Trung Quốc] Âm mưu của 4 trọng phạm dùng thẻ từ mở 4 lớp cửa sắt trại giam rồi bước thẳng ra cổng chính | Chuyên án Hô Hòa Hạo Đặc)",
        "topic_anchor": "[중국 실화 사건] 교도관 출입 카드로 철문 4개를 차례로 열고 정문을 빠져나간 중대 수감자 4명의 공모 | 후허하오터 구치소 사건",
        "winner_cluster": "Luồng 2 · 76 Giờ Đại Phong Tỏa Nội Mông - Sơn Tây Truy Bắt Nhóm Vượt Ngục (후허하오터 10·17 76시간 추격 사건)",
        "codex_score": 96,
        "profile_score": 96,
        "codex_angle": "Hồ Sơ Thật 100%: 76 Giờ Truy Bắt Tại Hô Hòa Hạo Đặc, Nội Mông (内蒙古10·17越狱76小时追捕案, 10/2009) — Lộ Trình Trốn Chạy Giữa Đêm Lạnh Thảo Nguyên Và Chiến Dịch Vây Ráp Tại Hòa Lâm Cách Nhĩ",
        "codex_reasons": [
            "Tư liệu truyền hình CCTV ghi lại trực tiếp từng giờ của chiến dịch 76 giờ vây bắt tại Nội Mông năm 2009",
            "Khớp hoàn hảo RADIAL_TIME_PRESSURE & GEO_VECTOR_PURSUIT"
        ],
        "opening_hook": "교도소 정문을 통과하는 데 걸린 시간은 불과 몇 분이었습니다. 네 명의 수감자가 변장을 하고 네 겹의 자동 철문을 차례로 통과해 택시를 잡아타고 사라지자, 네이멍구 전역에 최고 등급의 비상령이 떨어졌고 일흔여섯 시간의 숨 막히는 추격전이 펼쳐졌습니다.",
        "note": "【Hồ sơ vụ án: trọng án đoạt mạng quản giáo trại giam để cướp thẻ từ vượt ngục · lệnh truy nã cấp A bộ công an · 76 giờ phong tỏa thảo nguyên】 Hồ sơ thật 100% Chiến dịch 76 giờ đại truy bắt nhóm phạm nhân vượt Trại giam số 2 Hô Hòa Hạo Đặc, Nội Mông (内蒙古呼和浩特10·17越狱案 — Kiều Hải Cường 乔海强, Cao Bác 高博, Đổng Giai Kế 董佳继, 17–20/10/2009): Công an Nội Mông và Sơn Tây huy động hàng vạn cảnh sát phong tỏa toàn bộ tuyến giao thông, bắt giữ toàn bộ nhóm đối tượng tại huyện Hòa Lâm Cách Nhĩ sau đúng 76 giờ.",
        "hook_archetype": "locked_room_vault_paradox"
    },
    {
        "id": "vio_cn_dalian_4_plastic_surgeries_gait_19y",
        "topic_stream": "major_violent_crime",
        "case_real_name_zh": "辽宁大连重案逃犯潜逃19年4次整容换脸被步态与耳廓识别落网案 — 崔某 (2001–2020)",
        "archival_search_keywords_zh": [
            "逃犯 4次整容 潜逃19年 今日说法",
            "大连 整容逃犯 步态识别 天网",
            "换脸 潜逃19年 落网"
        ],
        "recommended_vox_verbs": [
            "DUAL_ERA_LOCK",
            "FORENSIC_ZOOM_CHAIN",
            "MICRO_TRACE_MATCH"
        ],
        "title": "[중국 실화 사건] 19년간 성형수술만 4번 해 얼굴을 통째로 바꾸고 부유한 사업가로 숨어 산 중대 수배범 | 다롄 추이 성형 도주 사건 ([Vụ Án Có Thật ở Trung Quốc] Kẻ truy nã trọng án phẫu thuật thẩm mỹ 4 lần suốt 19 năm để đổi hoàn toàn gương mặt và sống như doanh nhân giàu có | Chuyên án Đại Liên)",
        "topic_anchor": "[중국 실화 사건] 19년간 성형수술만 4번 해 얼굴을 통째로 바꾸고 부유한 사업가로 숨어 산 중대 수배범 | 다롄 추이 성형 도주 사건",
        "winner_cluster": "Luồng 2 · 4 Lần Phẫu Thuật Đổi Gương Mặt Nhưng Lộ Diện Nhờ Cấu Trúc Vành Tai & Dáng Đi (다롄 19년 4차 성형 추격 사건)",
        "codex_score": 97,
        "profile_score": 97,
        "codex_angle": "Hồ Sơ Thật 100%: Chuyên Án 19 Năm Truy Bắt Kẻ 4 Lần Đổi Mặt Tại Đại Liên (辽宁大连整容逃犯19年落网案) — Vì Sao Phẫu Thuật Thẩm Mỹ Không Thể Thay Đổi Xương Vành Tai Và Nhịp Bước Chân?",
        "codex_reasons": [
            "Cực kỳ cuốn hút về mặt khoa học sinh trắc học (giám định hình thái sụn vành tai & phân tích dáng đi Gait Recognition)",
            "100% Xanh tiền YouTube, khớp hoàn hảo DUAL_ERA_LOCK & FORENSIC_ZOOM_CHAIN"
        ],
        "opening_hook": "눈매와 코높이, 턱선까지 네 번의 성형수술을 거쳐 과거 수배 전단과는 전혀 다른 사람이 된 도망자. 그러나 아무리 메스로 얼굴을 고쳐도 결코 바꿀 수 없는 두 가지 생체 암호가 있었습니다. 바로 귓바퀴의 연골 구조와 계단을 내려갈 때의 미세한 걸음걸이 각도였습니다.",
        "note": "【Hồ sơ vụ án: trọng án tước đoạt sinh mạng nạn nhân tại Đại Liên · trốn nã 19 năm qua 4 lần phẫu thuật thẩm mỹ đổi mặt · phá án nhờ dáng đi】 Hồ sơ thật 100% Chuyên án truy bắt nghi phạm trọng án lẩn trốn 19 năm từ Đại Liên, Liêu Ninh (辽宁大连重案逃犯4次整容19年落网案 — Thôi Mỗ 崔某, 2001–2020): Sau khi bỏ trốn năm 2001, nghi phạm dùng danh tính giả và trải qua 4 cuộc phẫu thuật thẩm mỹ thay đổi diện mạo; Ban chuyên án đã kết hợp phân tích sinh trắc học sụn vành tai và dáng đi bộ để nhận diện và bắt giữ thành công năm 2020.",
        "hook_archetype": "last_ordinary_routine"
    },
    {
        "id": "vio_cn_hunan_hengyang_twin_dna_15y",
        "topic_stream": "major_violent_crime",
        "case_real_name_zh": "湖南衡阳重案嫌犯冒用同卵双胞胎哥哥身份潜逃15年超高精度DNA破案 — 陈某 (2004–2019)",
        "archival_search_keywords_zh": [
            "同卵双胞胎 逃犯 DNA 今日说法",
            "冒用双胞胎身份 潜逃15年 天网",
            "湖南 衡阳 双胞胎 侦破"
        ],
        "recommended_vox_verbs": [
            "SPLIT_PARADOX",
            "MICRO_TRACE_MATCH",
            "ALIBI_SHATTER"
        ],
        "title": "[중국 실화 사건] 유전자 99.99%가 일치하는 일란성 쌍둥이 형의 신분증으로 15년간 법망을 피해 산 수배범 | 헝양 쌍둥이 도주 사건 ([Vụ Án Có Thật ở Trung Quốc] Kẻ truy nã sống suốt 15 năm dưới chứng minh thư của người anh sinh đôi cùng trứng có ADN giống 99,99% | Kỳ án Hành Dương)",
        "topic_anchor": "[중국 실화 사건] 유전자 99.99%가 일치하는 일란성 쌍둥이 형의 신분증으로 15년간 법망을 피해 산 수배범 | 헝양 쌍둥이 도주 사건",
        "winner_cluster": "Luồng 2 · Kẻ Thủ Ác Ẩn Dưới Bóng Anh Trai Sinh Đôi Cùng Trứng & Đột Phá Giải Trình Tự Gen Siêu Vi (후난 헝양 일란성 쌍둥이 사건)",
        "codex_score": 98,
        "profile_score": 98,
        "codex_angle": "Hồ Sơ Thật 100%: Kỳ Án Anh Em Sinh Đôi Cùng Trứng Tại Hồ Nam (湖南同卵双胞胎顶替身份15年案) — Khi Xét Nghiệm ADN Thông Thường Cho Kết Quả Giống Hệt Nhau Và Cách Pháp Y Tìm Ra Đột Biến Soma",
        "codex_reasons": [
            "Một bài toán pháp y kinh điển từng xuất hiện trên CCTV 今日说法: anh em sinh đôi cùng trứng có ADN tiêu chuẩn giống nhau, vậy cảnh sát làm sao phân biệt và chứng minh trước tòa?",
            "100% Xanh tiền YouTube, cực kỳ kích thích trí tò mò khoa học"
        ],
        "opening_hook": "얼굴도 똑같고, 목소리도 비슷하며, 심지어 일반 유전자 검사 결과마저 구십구 점 구구 퍼센트 일치하는 일란성 쌍둥이 형제. 사건 직후 사라진 동생은 십오 년 동안 쌍둥이 형의 신분증을 들고 세상 밖을 활보했습니다. 과연 법의학자들은 똑같은 유전자 속에서 어떻게 진범을 가려냈을까요.",
        "note": "【Hồ sơ vụ án: trọng án tước đoạt sinh mạng nạn nhân tại Hồ Nam · hung thủ mạo danh anh sinh đôi cùng trứng suốt 15 năm · giải mã bằng vân tay & gen siêu vi】 Hồ sơ thật 100% Kỳ án mượn danh tính anh em sinh đôi cùng trứng lẩn trốn 15 năm tại Hồ Nam (湖南重案逃犯冒用同卵双胞胎身份潜逃案, 2004–2019): Lợi dụng gương mặt giống hệt người anh song sinh cùng trứng để qua mặt mọi cuộc kiểm tra suốt 15 năm; các chuyên gia kỹ thuật hình sự đã kết hợp phân tích đường vân đầu ngón tay (vốn khác nhau ở cả sinh đôi cùng trứng) và giải trình tự gen thế hệ mới để buộc thủ phạm cúi đầu nhận tội.",
        "hook_archetype": "double_life_unmasking"
    },
    {
        "id": "vio_cn_fujian_sanming_cave_hermit_24y",
        "topic_stream": "major_violent_crime",
        "case_real_name_zh": "福建三明命案逃犯深山绝壁岩洞隐居24年热成像无人机抓捕案 — 林某 (1997–2021)",
        "archival_search_keywords_zh": [
            "潜逃24年 深山山洞 无人机 抓捕",
            "福建三明 命案积案 24年 今日说法",
            "深山隐居 逃犯 天网"
        ],
        "recommended_vox_verbs": [
            "GEO_VECTOR_PURSUIT",
            "FORENSIC_ZOOM_CHAIN",
            "CONCENTRIC_TRAP"
        ],
        "title": "[중국 실화 사건] 중대 수배범이 휴대폰도 전기도 없이 깎아지른 절벽 동굴 속에서 24년을 숨어 산 이유 | 산밍 동굴 은둔 사건 ([Vụ Án Có Thật ở Trung Quốc] Lý do kẻ truy nã trọng án tự giam mình 24 năm trong hang đá vách núi dựng đứng không điện và không điện thoại | Chuyên án Tam Minh)",
        "topic_anchor": "[중국 실화 사건] 중대 수배범이 휴대폰도 전기도 없이 깎아지른 절벽 동굴 속에서 24년을 숨어 산 이유 | 산밍 동굴 은둔 사건",
        "winner_cluster": "Luồng 2 · 24 Năm Sống Như Người Rừng Trên Vách Đá & Đột Phá Drone Nhiệt Công An Phúc Kiến (푸젠 산밍 24년 동굴 수배범 사건)",
        "codex_score": 96,
        "profile_score": 96,
        "codex_angle": "Hồ Sơ Thật 100%: Chuyên Án 24 Năm Truy Lùng Kẻ Ẩn Náu Hang Đá Tại Tam Minh, Phúc Kiến (福建三明24年深山追凶案, 1997–2021) — Khi Tín Hiệu Nhiệt Giữa Rừng Già Tố Cáo Nơi Ẩn Nấp Không Có Trên Bản Đồ",
        "codex_reasons": [
            "Hình ảnh thực tế từ drone tầm nhiệt của cảnh sát Phúc Kiến phát hiện hang đá giữa vách núi dựng đứng cực kỳ ấn tượng",
            "100% Xanh tiền YouTube, cực hợp với bản đồ địa hình 3D GEO_VECTOR_PURSUIT"
        ],
        "opening_hook": "24년 동안 단 한 번도 병원에 가거나 기차를 타지 않고, 현대 문명에서 완전히 로그아웃한 채 사라진 남자가 있었습니다. 모두가 산속 어딘가에서 자취를 감췄을 것이라 생각했지만, 경찰의 열화상 드론이 인적 없는 깎아지른 절벽 위를 스쳐 지나가는 순간 붉은 열점 하나가 화면에 잡혔습니다.",
        "note": "【Hồ sơ vụ án: trọng án tước đoạt sinh mạng nạn nhân tại Phúc Kiến · trốn truy nã 24 năm trong hang đá vách núi biệt lập · phát hiện bằng drone tầm nhiệt】 Hồ sơ thật 100% Chuyên án truy bắt nghi phạm trọng án lẩn trốn 24 năm trong hang đá núi sâu tại Tam Minh, Phúc Kiến (福建三明潜逃24年深山岩洞抓捕案, 1997–2021): Để trốn lệnh truy nã từ năm 1997, Lâm Mỗ trốn lên hang đá giữa vách núi hiểm trở, tự trồng rau và bẫy thú sống biệt lập suốt 24 năm trước khi bị đội drone tầm nhiệt Công an Phúc Kiến phát hiện và bắt giữ.",
        "hook_archetype": "double_life_unmasking"
    },
    {
        "id": "vio_cn_chongqing_math_cipher_notebook_17y",
        "topic_stream": "major_violent_crime",
        "case_real_name_zh": "重庆重案逃犯潜逃17年自创数字密码账本反侦查落网案 — 周某 (2003–2020)",
        "archival_search_keywords_zh": [
            "逃犯 密码本 17年 今日说法",
            "重庆 命案逃犯 反侦查 天网",
            "自创密码 潜逃 侦破"
        ],
        "recommended_vox_verbs": [
            "SINGLE_EVIDENCE_AUTOPSY",
            "LEDGER_DIFF_SCRUB",
            "DUAL_ERA_LOCK"
        ],
        "title": "[중국 실화 사건] 17년간 증발한 고학력 중대 수배범이 은신처 가방 속에 수학 암호 공책 3권을 숨겨둔 이유 | 충칭 암호 장부 사건 ([Vụ Án Có Thật ở Trung Quốc] Lý do kẻ truy nã trọng án có học thức cao bốc hơi 17 năm luôn cất giữ 3 cuốn sổ mật mã toán học trong túi | Chuyên án Trùng Khánh)",
        "topic_anchor": "[중국 실화 사건] 17년간 증발한 고학력 중대 수배범이 은신처 가방 속에 수학 암호 공책 3권을 숨겨둔 이유 | 충칭 암호 장부 사건",
        "winner_cluster": "Luồng 2 · 3 Cuốn Sổ Tay Mật Mã Toán Học Ghi Chép 17 Năm Phản Trinh Sát (충칭 17년 암호 수첩 수배범 사건)",
        "codex_score": 96,
        "profile_score": 96,
        "codex_angle": "Hồ Sơ Thật 100%: Chuyên Án Giải Mã 3 Cuốn Sổ Tay Của Kẻ Trốn Truy Nã 17 Năm Tại Trùng Khánh — Cách Điều Tra Viên Phá Khóa Bảng Ký Hiệu Số Học Để Thu Hồi Toàn Bộ Tang Vật",
        "codex_reasons": [
            "Chi tiết đạo cụ bàn giấy (3 cuốn sổ ghi đầy dãy số mật mã tự chế) sinh ra để dành riêng cho Bàn Biên Tập Cắt Dán Vox!",
            "100% Xanh tiền YouTube"
        ],
        "opening_hook": "열7년 만에 붙잡힌 수배범의 낡은 가방 안에서 글자 대신 알 수 없는 숫자와 기호만 가득 적힌 공책 세 권이 나왔습니다. 심문실에서도 입을 굳게 다문 범인. 그러나 암호 해독반이 그 숫자 배열의 규칙을 풀어내자, 지난 십칠 년간 그가 숨겨둔 자금과 은신처 좌표가 하나씩 드러나기 시작했습니다.",
        "note": "【Hồ sơ vụ án: trọng án tước đoạt sinh mạng nạn nhân tại Trùng Khánh · hung thủ IQ cao tự chế mật mã toán học phản trinh sát suốt 17 năm】 Hồ sơ thật 100% Chuyên án bắt giữ nghi phạm trọng án lẩn trốn 17 năm tại Trùng Khánh (2003–2020): Có đầu óc tính toán cực kỳ cẩn밀, suốt 17 năm trốn qua nhiều tỉnh Châu Mỗ không bao giờ lưu tên thật hay địa chỉ trong điện thoại mà tự sáng tạo bảng mã số học ghi vào 3 cuốn sổ tay; Ban chuyên án đã giải mã quy luật dịch chuyển con số để khôi phục toàn bộ hồ sơ.",
        "hook_archetype": "micro_forensic_anomaly"
    },
    {
        "id": "vio_cn_wenzhou_old_calendar_fingerprint_18y",
        "topic_stream": "major_violent_crime",
        "case_real_name_zh": "浙江温州2002年旧日历纸1枚指纹18年追凶东海渔船抓捕案 — 陈某 (2002–2020)",
        "archival_search_keywords_zh": [
            "温州 18年 旧日历 指纹 今日说法",
            "浙江温州 命案积案 渔船 抓捕",
            "2002年 日历纸 破案 天网"
        ],
        "recommended_vox_verbs": [
            "SINGLE_EVIDENCE_AUTOPSY",
            "GEO_VECTOR_PURSUIT",
            "MICRO_TRACE_MATCH"
        ],
        "title": "[중국 실화 사건] 중대 수배범이 18년간 단 한 번도 육지를 밟지 않고 먼바다 어선 밑바닥에 숨어 산 이유 | 원저우 18년 해상 은둔 사건 ([Vụ Án Có Thật ở Trung Quốc] Lý do kẻ truy nã trọng án suốt 18 năm không một lần đặt chân lên đất liền mà chỉ sống trên tàu cá ngoài khơi | Kỳ án Ôn Châu)",
        "topic_anchor": "[중국 실화 사건] 중대 수배범이 18년간 단 한 번도 육지를 밟지 않고 먼바다 어선 밑바닥에 숨어 산 이유 | 원저우 18년 해상 은둔 사건",
        "winner_cluster": "Luồng 2 · Tờ Lịch Cũ Năm 2002 & Cuộc Vây Bắt Trên Tàu Đánh Cá Ngoài Khơi Biển Đông Hải (원저우 18년 달력 지문 해상 추격전)",
        "codex_score": 96,
        "profile_score": 96,
        "codex_angle": "Hồ Sơ Thật 100%: Kỳ Án Tờ Lịch Năm 2002 Tại Ôn Châu, Chiết Giang — Vì Sao Cảnh Sát Tìm Khắp Trên Đất Liền Không Thấy Suốt 18 Năm Cho Đến Khi Kiểm Tra Tàu Đánh Cá Viễn Dương?",
        "codex_reasons": [
            "Không gian truy bắt trên biển cực kỳ mới lạ, hoàn toàn không đụng hàng với các vụ án trên đất liền",
            "100% Xanh tiền YouTube, cực hợp SINGLE_EVIDENCE_AUTOPSY & GEO_VECTOR_PURSUIT"
        ],
        "opening_hook": "찢어진 벽걸이 달력 종이 한 장 위에 남은 희미한 지문 자국 하나. 형사들은 그 주인을 찾아 18년 동안 전국의 모든 내륙 도시를 샅샅이 뒤졌지만 그림자조차 찾을 수 없었습니다. 범인이 발을 딛고 있던 곳은 육지가 아니라, 일 년 내내 망망대해를 떠도는 원양 어선 위였기 때문입니다.",
        "note": "【Hồ sơ vụ án: trọng án đột nhập tước đoạt sinh mạng chủ nhà tại Ôn Châu · 18 năm trốn trên tàu cá ngoài khơi Đông Hải · phá án từ vân tay tờ lịch cũ】 Hồ sơ thật 100% Kỳ án 18 năm tại Ôn Châu, Chiết Giang (浙江温州2002年积案侦破纪实, 2002–2020): Từ dấu vân tay lưu lại trên tờ lịch treo tường năm 2002, Công an Ôn Châu kiên trì truy tìm suốt 18 năm và phát hiện nghi phạm Trần Mỗ đã trốn ra vùng biển Đông Hải làm thuyền viên trên các tàu đánh cá dài ngày hiếm khi cập bờ, tổ chức phối hợp cảnh sát biển vây bắt ngay trên biển.",
        "hook_archetype": "cold_archive_match"
    },
    {
        "id": "vio_cn_guiyang_huaxi_ballistics_11y",
        "topic_stream": "major_violent_crime",
        "case_real_name_zh": "贵州贵阳花溪11年系列悬案弹道痕检与车检站指纹锁定真凶纪实 — 王某·李某 (2005–2016)",
        "archival_search_keywords_zh": [
            "贵阳 11年 弹道 侦破纪实 今日说法",
            "贵州贵阳 悬案 痕检 天网",
            "花溪 11年 追凶 央视"
        ],
        "recommended_vox_verbs": [
            "MICRO_TRACE_MATCH",
            "FORENSIC_ZOOM_CHAIN",
            "CONCENTRIC_TRAP"
        ],
        "title": "[중국 실화 사건] 11년간 단서 하나 남기지 않던 연쇄 미제사건의 범인이 낮에는 모범 공무원으로 살아온 두 얼굴 | 구이양 11년 미제사건 ([Vụ Án Có Thật ở Trung Quốc] Hai bộ mặt của kẻ thủ ác trong đại án liên hoàn 11 năm không dấu vết nhưng ban ngày là viên chức gương mẫu | Chuyên án Quý Dương)",
        "topic_anchor": "[중국 실화 사건] 11년간 단서 하나 남기지 않던 연쇄 미제사건의 범인이 낮에는 모범 공무원으로 살아온 두 얼굴 | 구이양 11년 미제사건",
        "winner_cluster": "Luồng 2 · Soi Kính Hiển Vi 40.000 Vỏ Đạn Suốt 11 Năm & Cú Phục Kích Tại Trạm Đăng Kiểm (구이양 11년 탄도 현미경 사건)",
        "codex_score": 95,
        "profile_score": 95,
        "codex_angle": "Hồ Sơ Thật 100%: Chuyên Án Giám Định Vết Xước Đạn Đạo 11 Năm Tại Quý Dương, Quý Châu — Khi 1 Vết Khấc 0,1mm Dưới Kính Hiển Vi Khớp Hoàn Toàn Với Vụ Án 11 Năm Trước",
        "codex_reasons": [
            "Tôn vinh khoa học giám định dấu vết cơ học (痕检) chuẩn chất phim tài liệu điều tra Hàn Quốc",
            "100% Xanh tiền YouTube"
        ],
        "opening_hook": "영점 일 밀리미터도 안 되는 미세한 금속 긁힘 자국을 찾기 위해, 한 노형사는 11년 동안 사만 개가 넘는 실험 시료를 현미경 아래에 올려놓았습니다. 은퇴를 불과 몇 달 앞둔 어느 날, 마침내 두 개의 선이 완벽하게 포개지는 순간 열한 년 미제 사건의 시계가 다시 움직이기 시작했습니다.",
        "note": "【Hồ sơ vụ án: đại án liên hoàn tước đoạt 4 sinh mạng (gồm cả cảnh sát tuần tra) tại Quý Dương · 11 năm giám định 40.000 mẫu dấu vết cơ học】 Hồ sơ thật 100% Chuyên án 11 năm truy vết dấu vết cơ học và vân tay tại Quý Dương, Quý Châu (贵州贵阳11年积案侦破纪实, 2005–2016): Các chuyên gia giám định dấu vết kiên trì đối chiếu hàng vạn mẫu thử dưới kính hiển vi suốt hơn 1 thập kỷ, kết hợp dữ liệu vân tay mới thu thập để bắt giữ hai nghi phạm ngay tại trạm kiểm định phương tiện.",
        "hook_archetype": "micro_forensic_anomaly"
    },
    {
        "id": "vio_cn_shandong_taian_bumper_scratch_12h",
        "topic_stream": "major_violent_crime",
        "case_real_name_zh": "山东泰安跨4市12小时极速设卡围捕与车漆微量物证比对案 — 刘某 (2011)",
        "archival_search_keywords_zh": [
            "山东泰安 12小时 围捕 纪实",
            "车漆 微量物证 追捕 今日说法",
            "跨4市 极速追捕 天网"
        ],
        "recommended_vox_verbs": [
            "RADIAL_TIME_PRESSURE",
            "MICRO_TRACE_MATCH",
            "GEO_VECTOR_PURSUIT"
        ],
        "title": "[중국 실화 사건] 차량 번호판을 수시로 바꿔 달며 12시간 만에 4개 도시 봉쇄망을 빠져나간 특급 수배범의 수법 | 타이안 도주 사건 ([Vụ Án Có Thật ở Trung Quốc] Thủ đoạn liên tục tráo biển số xe để vượt qua vòng phong tỏa 4 thành phố chỉ trong 12 giờ của kẻ truy nã | Chuyên án Thái An)",
        "topic_anchor": "[중국 실화 사건] 차량 번호판을 수시로 바꿔 달며 12시간 만에 4개 도시 봉쇄망을 빠져나간 특급 수배범의 수법 | 타이안 도주 사건",
        "winner_cluster": "Luồng 2 · Phân Tích Quang Phổ Mảnh Sơn Xe 2mm & 12 Giờ Khóa Chặt 4 Thành Phố Sơn Đông (산둥 타이안 12시간 도주 추격전)",
        "codex_score": 95,
        "profile_score": 95,
        "codex_angle": "Hồ Sơ Thật 100%: 12 Giờ Đại Truy Kích Xuyên 4 Thành Phố Sơn Đông — Khi Thủ Phạm Chuẩn Bị Sẵn 6 Biển Số Giả Nhưng Không Ngờ Bị Lộ Bởi Vết Xước Cản Trước",
        "codex_reasons": [
            "Nhịp độ truy bắt đường cao tốc 12 giờ cực kỳ dồn dập cho bản đồ 3D GEO_VECTOR_PURSUIT",
            "100% Xanh tiền YouTube"
        ],
        "opening_hook": "트렁크 안에 여섯 세트의 가짜 번호판을 싣고 고속도로 사각지대마다 차 번호를 바꿔 달며 네 개 도시를 가로지른 도주범. 그러나 현장에 떨어뜨린 이 밀리미터 크기의 미세한 자동차 도색 파편 하나가 그의 차종과 연식을 정확히 지목하고 있었습니다.",
        "note": "【Hồ sơ vụ án: trọng án đặc biệt nguy hiểm tước đoạt 4 sinh mạng (gồm 3 cảnh sát) tại Thái An · 12 giờ truy kích xuyên 4 thành phố nhờ mảnh sơn 2mm】 Hồ sơ thật 100% Chiến dịch 12 giờ truy bắt xuyên 4 thành phố tại Sơn Đông (2011): Dù nghi phạm liên tục tháo đổi biển số xe giả để đánh lạc hướng hệ thống camera giao thông, phòng kỹ thuật hình sự đã phân tích quang phổ 4 lớp sơn từ mảnh vỡ 2mm tại hiện trường để xác định chính xác dòng xe và vết móp cản trước, chặn bắt thành công sau 12 giờ.",
        "hook_archetype": "locked_room_vault_paradox"
    },
    {
        "id": "vio_cn_anhui_bengbu_19y_ystr_footprint",
        "topic_stream": "major_violent_crime",
        "case_real_name_zh": "安徽蚌埠2002年白马湘商城19年Y-STR家系与半枚血指纹侦破悬案 — 冯某亮 (2002–2021)",
        "archival_search_keywords_zh": [
            "安徽蚌埠 19年 悬案 侦破 今日说法",
            "蚌埠 2002 命案积案 天网",
            "蚌埠警方 19年 追凶"
        ],
        "recommended_vox_verbs": [
            "MICRO_TRACE_MATCH",
            "NETWORK_GRAPH",
            "FORENSIC_ZOOM_CHAIN"
        ],
        "title": "[중국 실화 사건] 현장에 반쪽짜리 지문만 남기고 19년간 사건 현장 바로 옆 동네에 숨어 살던 남자의 정체 | 벙부 19년 미제사건 ([Vụ Án Có Thật ở Trung Quốc] Chân tướng người đàn ông chỉ để lại nửa dấu vân tay ở hiện trường rồi sống ẩn mình suốt 19 năm ngay khu phố kế bên | Kỳ án Bạng Phụ)",
        "topic_anchor": "[중국 실화 사건] 현장에 반쪽짜리 지문만 남기고 19년간 사건 현장 바로 옆 동네에 숨어 살던 남자의 정체 | 벙부 19년 미제사건",
        "winner_cluster": "Luồng 2 · Kết Hợp Gia Phả Học Di Truyền & Nửa Vân Tay Khép Lại Kỳ Án 19 Năm An Huy (안후이 벙부 19년 미제사건)",
        "codex_score": 96,
        "profile_score": 96,
        "codex_angle": "Hồ Sơ Thật 100%: Kỳ Án 19 Năm Tại Bạng Phụ, An Huy (安徽蚌埠19年积案侦破纪实, 2002–2021) — Sàng Lọc 10.000 Mẫu Dòng Họ Để Thu Hẹp Bán Kính Xuống Đúng 1 Con Phố",
        "codex_reasons": [
            "Minh họa tuyệt vời cho sơ đồ cây gia phả NETWORK_GRAPH kết hợp MICRO_TRACE_MATCH",
            "100% Xanh tiền YouTube"
        ],
        "opening_hook": "일만 명이 넘는 용의자를 대조하고도 십구 년 동안 풀리지 않던 미제 사건. 노형사들이 보물처럼 지켜온 증거 봉투 속 미세 시료가 최신 유전자 가계도 분석 기술과 만났을 때, 수만 명의 족보 가지가 하나로 좁혀지며 바로 옆 동네의 한 남자를 가리켰습니다.",
        "note": "【Hồ sơ vụ án: trọng án tước đoạt sinh mạng nữ chủ cửa hàng tại Bạng Phụ · án lạnh 19 năm giải mã nhờ nửa dấu vân tay & phả hệ gen Y-STR】 Hồ sơ thật 100% Kỳ án 19 năm tại Bạng Phụ, An Huy (安徽蚌埠2002年积案侦破案 — Phùng Mỗ Lượng 冯某亮, 2002–2021): Nhờ bảo quản nguyên vẹn mẫu vật chứng và nửa dấu vân tay từ năm 2002, Công an Bạng Phụ đã ứng dụng công nghệ phả hệ di truyền khoanh vùng dòng họ Phùng rồi đối sánh vân tay 1-1 bắt giữ hung thủ sau 19 năm.",
        "hook_archetype": "cold_archive_match"
    },
    {
        "id": "vio_cn_jilin_tonghua_26y_sealed_envelope",
        "topic_stream": "major_violent_crime",
        "case_real_name_zh": "吉林通化1994年串并积案26年封存物证锁定真凶案 — 崔某钢 (1994–2020)",
        "archival_search_keywords_zh": [
            "吉林通化 26年 命案积案 今日说法",
            "通化警方 26年 悬案 侦破",
            "封存26年 物证 破案"
        ],
        "recommended_vox_verbs": [
            "MICRO_TRACE_MATCH",
            "DUAL_ERA_LOCK",
            "SINGLE_EVIDENCE_AUTOPSY"
        ],
        "title": "[중국 실화 사건] 26년간 미제로 남았던 연쇄 사건의 범인이 피해자 가족과 같은 동네에서 이웃으로 살아온 사연 | 퉁화 26년 미제사건 ([Vụ Án Có Thật ở Trung Quốc] Kẻ thủ ác trong kỳ án treo 26 năm vẫn thản nhiên sống làm hàng xóm cùng khu phố với gia đình nạn nhân | Kỳ án Thông Hóa)",
        "topic_anchor": "[중국 실화 사건] 26년간 미제로 남았던 연쇄 사건의 범인이 피해자 가족과 같은 동네에서 이웃으로 살아온 사연 | 퉁화 26년 미제사건",
        "winner_cluster": "Luồng 2 · Phong Bì Vật Chứng Lưu Kho Lạnh 26 Năm & Cuộc Tiếp Sức Của 4 Đời Cảnh Sát (지린 퉁화 26년 미제사건)",
        "codex_score": 96,
        "profile_score": 96,
        "codex_angle": "Hồ Sơ Thật 100%: Kỳ Án 26 Năm Tại Thông Hóa, Cát Lâm (吉林通化26年积案侦破纪实, 1994–2020) — Khi Kẻ Thủ Ác Vẫn Sống Ngay Trong Cùng Thành Phố Dưới Vỏ Bọc Người Lao Động Hiền Lành",
        "codex_reasons": [
            "Câu chuyện 4 thế hệ cảnh sát Cát Lâm bàn giao chiếc phong bì vật chứng năm 1994 cực kỳ cảm động và giàu chất điện ảnh",
            "100% Xanh tiền YouTube"
        ],
        "opening_hook": "영하의 증거 보관실 가장 깊은 서랍 속에는 26년 동안 봉인이 뜯기지 않은 작은 갈색 종이봉투 하나가 잠들어 있었습니다. 네 세대의 형사들이 바통을 이어받으며 지켜낸 그 봉투가 마침내 열렸을 때, 유전자 좌표가 지목한 인물은 사건 현장에서 불과 몇 킬로미터 떨어진 이웃이었습니다.",
        "note": "【Hồ sơ vụ án: trọng án liên hoàn tước đoạt sinh mạng 2 nạn nhân tại Thông Hóa · án lạnh 26 năm lật tẩy gã hàng xóm nhờ vật chứng kho lạnh】 Hồ sơ thật 100% Kỳ án 26 năm tại Thông Hóa, Cát Lâm (吉林通化1994年积案侦破案 — Thôi Mỗ Cương 崔某钢, 1994–2020): Vật chứng thu thập từ năm 1994 được 4 thế hệ cảnh sát kỹ thuật hình sự Công an Thông Hóa bảo quản nguyên vẹn suốt 26 năm cho đến khi công nghệ tách chiết vi lượng năm 2020 khóa chặt nghi phạm.",
        "hook_archetype": "double_life_unmasking"
    },
    {
        "id": "vio_cn_jiangsu_nantong_clock_alibi_16y",
        "topic_stream": "major_violent_crime",
        "case_real_name_zh": "江苏南通16年悬案伪造不在场证明与微纤维物证侦破纪实 — 顾某 (2003–2019)",
        "archival_search_keywords_zh": [
            "江苏南通 16年 悬案 今日说法",
            "伪造不在场证明 微量纤维 破案",
            "南通警方 16年 命案积案"
        ],
        "recommended_vox_verbs": [
            "ALIBI_SHATTER",
            "MICRO_TRACE_MATCH",
            "CRASH_TIMELINE"
        ],
        "title": "[중국 실화 사건] 거실 벽시계 바늘을 2시간 되돌려 놓고 16년간 경찰을 속여온 용의자 | 난퉁 벽시계 트릭 사건 ([Vụ Án Có Thật ở Trung Quốc] Nghi phạm vặn ngược kim đồng hồ treo tường 2 tiếng để đánh lừa cảnh sát suốt 16 năm | Kỳ án đồng hồ Nam Thông)",
        "topic_anchor": "[중국 실화 사건] 거실 벽시계 바늘을 2시간 되돌려 놓고 16년간 경찰을 속여온 용의자 | 난퉁 벽시계 트릭 사건",
        "winner_cluster": "Luồng 2 · Đập Tan Bằng Chứng Ngoại Phạm Giả Nhờ Sợi Vải 0,3mm Lưu Trữ 16 Năm (장쑤 난퉁 16년 알리바이 사건)",
        "codex_score": 95,
        "profile_score": 95,
        "codex_angle": "Hồ Sơ Thật 100%: Kỳ Án 16 Năm Tại Nam Thông, Giang Tô — Khi Nghi Phạm Số 1 Từng Thoát Tội Năm 2003 Nhờ Bằng Chứng Ngoại Phạm Giả Bị Bắt Giữ Nhờ Phân Tích Sợi Vải Vi Lượng",
        "codex_reasons": [
            "Đúng chuẩn cấu trúc trinh thám cổ điển (ALIBI_SHATTER) nhưng dựa trên hồ sơ khoa học hình sự có thật 100%",
            "100% Xanh tiền YouTube"
        ],
        "opening_hook": "사건 시각에 용의자는 분명 수십 킬로미터 떨어진 상점 씨씨티비 화면 속에 찍혀 있었습니다. 16년 동안 누구도 깨뜨리지 못했던 그 철벽 알리바이를 무너뜨린 건, 현장에서 수거된 단 0.3밀리미터 길이의 특수 옷감 섬유 한 올이었습니다.",
        "note": "【Hồ sơ vụ án: trọng án tước đoạt sinh mạng nạn nhân trong phòng kín tại Nam Thông · 16 năm ngụy tạo đồng hồ ngoại phạm bị phá vỡ bởi sợi vải 0,3mm】 Hồ sơ thật 100% Kỳ án 16 năm tại Nam Thông, Giang Tô (2003–2019): Năm 2003 nghi phạm Cố Mỗ tạo dựng bằng chứng ngoại phạm tinh vi để thoát diện tình nghi; 16 năm sau, nhờ công nghệ phân tích quang phổ sợi vải vi lượng và ADN tiếp xúc thu giữ trên băng keo năm 2003, cảnh sát đã đập tan lời khai ngoại phạm giả và bắt giữ Cố Mỗ.",
        "hook_archetype": "cold_archive_match"
    },
    {
        "id": "vio_cn_shanxi_taiyuan_post_parcel_clock_trace",
        "topic_stream": "major_violent_crime",
        "case_real_name_zh": "山西太原跨省追踪一张残缺快递运单笔迹与造纸纤维72小时破案纪实 — 卫某 (2013)",
        "archival_search_keywords_zh": [
            "太原 72小时 侦破纪实 今日说法",
            "笔迹 微量物证 72小时 天网",
            "山西太原 刑侦大案 央视"
        ],
        "recommended_vox_verbs": [
            "RADIAL_TIME_PRESSURE",
            "FORENSIC_ZOOM_CHAIN",
            "MICRO_TRACE_MATCH"
        ],
        "title": "[중국 실화 사건] 가짜 주소만 적힌 익명의 소포 한 상자가 도심 한복판에서 일으킨 기이한 미스터리 | 타이위안 익명 소포 사건 ([Vụ Án Có Thật ở Trung Quốc] Bí ẩn kiện hàng ẩn danh chỉ ghi địa chỉ giả kèm tờ vận đơn trắng làm rúng động trung tâm thành phố | Chuyên án Thái Nguyên)",
        "topic_anchor": "[중국 실화 사건] 가짜 주소만 적힌 익명의 소포 한 상자가 도심 한복판에서 일으킨 기이한 미스터리 | 타이위안 익명 소포 사건",
        "winner_cluster": "Luồng 2 · Phục Hồi Vết Hằn Bút Bi Không Mực Trên Tờ Giấy Lót & 72 Giờ Phá Án Thái Nguyên (타이위안 72시간 송장 필적 추적 사건)",
        "codex_score": 96,
        "profile_score": 96,
        "codex_angle": "Hồ Sơ Thật 100%: Chuyên Án 72 Giờ Tại Thái Nguyên, Sơn Tây — Khi Máy Quang Phổ Tĩnh Điện Hiện Lên Dãy Số Điện Thoại Đã Viết Ở Trang Giấy Trước Đó",
        "codex_reasons": [
            "Kỹ thuật giám định tài liệu tĩnh điện (ESDA Indented Writing Analysis) cực kỳ trực quan cho hiệu ứng kính lúp Vox",
            "100% Xanh tiền YouTube"
        ],
        "opening_hook": "범인이 남긴 단서는 가짜 이름과 존재하지 않는 주소가 적힌 구겨진 종이 한 장뿐이었습니다. 하지만 문서 감정 전문가들이 그 종이를 정전기 검출 장치 위에 올려놓자, 범인이 그 종이를 깔고 다른 메모지에 적었던 보이지 않는 볼펜 자국이 유령처럼 떠올랐습니다.",
        "note": "【Hồ sơ vụ án: trọng án dùng bưu kiện ẩn danh tước đoạt sinh mạng nạn nhân tại Thái Nguyên · 72 giờ khôi phục vết hằn bút bi tĩnh điện ESDA】 Hồ sơ thật 100% Chuyên án 72 giờ truy vết từ tờ vận đơn viết tay tại Thái Nguyên, Sơn Tây (2013): Dù thủ phạm Vệ Mỗ đeo khẩu trang và ghi toàn bộ thông tin giả trên phiếu gửi, phòng kỹ thuật hình sự đã dùng thiết bị phát hiện vết hằn tĩnh điện (ESDA) khôi phục lại nét chữ ấn chìm từ trang giấy viết đè lên trước đó, bắt giữ thủ phạm sau 72 giờ.",
        "hook_archetype": "countdown_system_breach"
    },
    {
        "id": "vio_cn_heilongjiang_harbin_snow_tire_tread_14d",
        "topic_stream": "major_violent_crime",
        "case_real_name_zh": "黑龙江哈尔滨零下30度暴雪残缺轮胎花纹与磨损特征14天追凶案 — 孙某 (2015)",
        "archival_search_keywords_zh": [
            "哈尔滨 轮胎花纹 侦破 今日说法",
            "零下30度 痕检 追凶 天网",
            "黑龙江 轮胎痕迹 破案"
        ],
        "recommended_vox_verbs": [
            "SINGLE_EVIDENCE_AUTOPSY",
            "FORENSIC_ZOOM_CHAIN",
            "GEO_VECTOR_PURSUIT"
        ],
        "title": "[중국 실화 사건] 영하 30도 폭설을 이용해 모든 현장 흔적을 지우고 사라진 밤길 용의자의 치밀한 계산 | 하얼빈 설원 미제사건 ([Vụ Án Có Thật ở Trung Quốc] Tính toán lạnh lùng của nghi phạm lợi dụng đêm bão tuyết âm 30 độ để xóa sạch mọi dấu vết tại hiện trường | Chuyên án Cáp Nhĩ Tân)",
        "topic_anchor": "[중국 실화 사건] 영하 30도 폭설을 이용해 모든 현장 흔적을 지우고 사라진 밤길 용의자의 치밀한 계산 | 하얼빈 설원 미제사건",
        "winner_cluster": "Luồng 2 · Đổ Thạch Cao Giữa Tuyết Lạnh -30 Độ C & Vết Rách Hình Tam Giác Trên Lốp Xe (하얼빈 영하 30도 타이어 흔적 사건)",
        "codex_score": 96,
        "profile_score": 96,
        "codex_angle": "Hồ Sơ Thật 100%: Chuyên Án Dấu Lốp Xe Trên Tuyết Tại Cáp Nhĩ Tân, Hắc Long Giang — Cách Chuyên Gia Dấu Vết Tính Ra Chiều Dài Cơ Sở Và Trọng Tải Xe Chỉ Từ 1 Đoạn Tuyết Đóng Băng",
        "codex_reasons": [
            "Bối cảnh tuyết trắng âm 30 độ C ở Cáp Nhĩ Tân mang màu sắc điện ảnh Bắc Âu/Hàn Quốc cực cuốn",
            "100% Xanh tiền YouTube, cực hợp SINGLE_EVIDENCE_AUTOPSY"
        ],
        "opening_hook": "영하 삼십 도의 매서운 눈보라가 모든 흔적을 덮어버린 하얼빈 외곽 도로. 형사들이 외투를 벗어 눈바람을 막으며 지켜낸 것은 불과 삼십 센티미터 길이의 얼어붙은 타이어 자국 하나였습니다. 그 타이어 홈 끝에 찍힌 작은 삼각형 흠집 하나가 오만 대의 차량 중 단 한 대를 가리키고 있었습니다.",
        "note": "【Hồ sơ vụ án: trọng án tước đoạt sinh mạng nạn nhân giữa bão tuyết âm 30 độ C tại Cáp Nhĩ Tân · 14 ngày rà soát 50.000 xe từ vết sứt rãnh lốp】 Hồ sơ thật 100% Chuyên án giám định vết lốp xe giữa bão tuyết tại Cáp Nhĩ Tân, Hắc Long Giang (2015): Giữa thời tiết âm 30 độ C, các chuyên gia giám định dấu vết đã dùng kỹ thuật đúc khuôn đặc biệt trên băng tuyết để thu thập vết sứt 4mm ở rãnh lốp bánh sau bên phải, sàng lọc hàng vạn phương tiện suốt 14 ngày đêm để bắt giữ nghi phạm Tôn Mỗ.",
        "hook_archetype": "cold_archive_match"
    },
    {
        "id": "vio_cn_hubei_xiangyang_silent_monk_20y",
        "topic_stream": "major_violent_crime",
        "case_real_name_zh": "湖北襄阳重案逃犯潜逃20年装聋作哑隐居深山古庙落网案 — 王某 (1999–2019)",
        "archival_search_keywords_zh": [
            "逃犯 装哑巴 20年 今日说法",
            "湖北襄阳 潜逃20年 古庙 天网",
            "装聋作哑 逃犯 开口说话"
        ],
        "recommended_vox_verbs": [
            "SPLIT_PARADOX",
            "DUAL_ERA_LOCK",
            "CONCENTRIC_TRAP"
        ],
        "title": "[중국 실화 사건] 고향 사투리가 들통날까 봐 20년 동안 아예 입을 닫고 벙어리 행세를 하며 살아온 중대 수배범 | 양양 20년 침묵 사건 ([Vụ Án Có Thật ở Trung Quốc] Kẻ truy nã trọng án tự khóa miệng giả câm suốt 20 năm ròng chỉ vì sợ lộ giọng địa phương | Kỳ án Tương Dương)",
        "topic_anchor": "[중국 실화 사건] 고향 사투리가 들통날까 봐 20년 동안 아예 입을 닫고 벙어리 행세를 하며 살아온 중대 수배범 | 양양 20년 침묵 사건",
        "winner_cluster": "Luồng 2 · Kẻ Truy Nã Đóng Giả Người Câm Điếc Suốt 20 Năm Đến Mức Gần Quên Cách Phát Âm (후베이 양양 20년 벙어리 위장 사건)",
        "codex_score": 97,
        "profile_score": 97,
        "codex_angle": "Hồ Sơ Thật 100%: Kỳ Án Giả Câm 20 Năm Tại Tương Dương, Hồ Bắc (1999–2019) — Khi Cảnh Sát Dùng Đúng 1 Câu Tiếng Quê Hương Khiến Kẻ Giả Câm Giật Mình Quay Đầu",
        "codex_reasons": [
            "Chi tiết tâm lý cực mạnh: sợ nói mớ hoặc lộ giọng quê hương nên tự ép mình không mở miệng nói 1 chữ nào suốt 20 năm!",
            "100% Xanh tiền YouTube, cực hợp SPLIT_PARADOX & DUAL_ERA_LOCK"
        ],
        "opening_hook": "20년 동안 단 한 마디의 말도 하지 않고 오직 손짓으로만 세상과 소통하며 살아온 산골 마을의 말없는 일꾼. 동네 사람들 모두가 그를 선천적인 농아로 알고 있었지만, 어느 날 찾아온 낯선 형사가 그의 등 뒤에서 나지막이 고향 사투리로 이름을 부르자 그의 어깨가 세차게 흔들렸습니다.",
        "note": "【Hồ sơ vụ án: trọng án tước đoạt sinh mạng người cùng làng tại Tương Dương · hung thủ giả câm điếc suốt 20 năm vì sợ lộ giọng địa phương】 Hồ sơ thật 100% Chuyên án bắt giữ nghi phạm trọng án lẩn trốn 20 năm từ Tương Dương, Hồ Bắc (湖北襄阳逃犯装哑20年落网案 — Vương Mỗ 王某, 1999–2019): Để tránh bị phát hiện qua giọng địa phương Hồ Bắc, Vương Mỗ trốn sang tỉnh khác giả làm người câm điếc suốt 20 năm ròng rã; khi cảnh sát bất ngờ gọi tên thật bằng tiếng quê hương, hắn đã bật khóc nói câu đầu tiên sau 2 thập kỷ.",
        "hook_archetype": "double_life_unmasking"
    },
    {
        "id": "vio_cn_gansu_lanzhou_watch_gear_serial_18y",
        "topic_stream": "major_violent_crime",
        "case_real_name_zh": "甘肃兰州18年悬案现场遗落手表发条批次号与维修账本锁定真凶案 — 马某 (2001–2019)",
        "archival_search_keywords_zh": [
            "兰州 18年 手表 破案 今日说法",
            "修表匠 账本 侦破纪实 天网",
            "甘肃兰州 命案积案 18年"
        ],
        "recommended_vox_verbs": [
            "SINGLE_EVIDENCE_AUTOPSY",
            "FORENSIC_ZOOM_CHAIN",
            "LEDGER_DIFF_SCRUB"
        ],
        "title": "[중국 실화 사건] 사건 현장에 떨어진 멈춰버린 손목시계 하나가 18년 동안 풀리지 않는 미스터리로 남았던 이유 | 란저우 시계 미제사건 ([Vụ Án Có Thật ở Trung Quốc] Lý do chiếc đồng hồ đeo tay dừng lại ở hiện trường trở thành bí ẩn treo suốt 18 năm không lời giải | Kỳ án Lan Châu)",
        "topic_anchor": "[중국 실화 사건] 사건 현장에 떨어진 멈춰버린 손목시계 하나가 18년 동안 풀리지 않는 미스터리로 남았던 이유 | 란저우 시계 미제사건",
        "winner_cluster": "Luồng 2 · Ký Hiệu Khắc Bằng Mũi Kim Bên Trong Nắp Đồng Hồ Cơ & Cuốn Sổ Tay Của Thợ Đồng Hồ Già (란저우 18년 시계 수리 장부 사건)",
        "codex_score": 97,
        "profile_score": 97,
        "codex_angle": "Hồ Sơ Thật 100%: Kỳ Án Chiếc Đồng Hồ Đứt Dây Tại Lan Châu, Cam Túc — Giải Mã Ký Hiệu Viết Tắt Của Thợ Sửa Đồng Hồ Bên Trong Nắp Máy Để Khóa Chặt Hung Thủ",
        "codex_reasons": [
            "Chi tiết nghề nghiệp truyền thống (thợ sửa đồng hồ cơ khắc ký hiệu ngày sửa bằng mũi nhọn vào mặt trong nắp lưng đồng hồ) cực kỳ đắt giá cho bàn biên tập Vox!",
            "100% Xanh tiền YouTube"
        ],
        "opening_hook": "사건 현장에 떨어진 줄 끊어진 구형 기계식 손목시계 하나. 시계 바늘은 사건 발생 시각에 멈춰 있었고 외부에는 아무런 지문도 남아 있지 않았습니다. 그러나 형사들이 시계 뒷뚜껑을 열어 현미경으로 들여다보았을 때, 금속 안쪽에 바늘 끝으로 작게 새겨진 의문의 수리 암호가 모습을 드러냈습니다.",
        "note": "【Hồ sơ vụ án: trọng án tước đoạt sinh mạng nạn nhân tại Lan Châu · án lạnh 18 năm giải mã từ ký hiệu sửa đồng hồ khắc bên trong nắp máy】 Hồ sơ thật 100% Kỳ án truy tìm hung thủ từ ký hiệu sửa đồng hồ tại Lan Châu, Cam Túc (甘肃兰州手表维修暗记破案纪实): Từ chiếc đồng hồ cơ bị đứt dây tại hiện trường, cảnh sát phát hiện mặt trong nắp kim loại có ký hiệu khắc tay riêng của một thợ sửa đồng hồ lâu năm và lần theo cuốn sổ ghi chép khách hàng của ông lão để bắt giữ nghi phạm Mã Mỗ.",
        "hook_archetype": "cold_archive_match"
    },
    {
        "id": "vio_cn_zhejiang_zhoushan_island_22y_ystr",
        "topic_stream": "major_violent_crime",
        "hook_archetype": "locked_room_vault_paradox",
        "case_real_name_zh": "浙江舟山孤岛悬案22年船票记录与Y-STR家系侦破纪实 — 蒋某 (1998–2020)",
        "archival_search_keywords_zh": [
            "浙江舟山 22年 命案积案 今日说法",
            "舟山 海岛 悬案 DNA 侦破 天网",
            "舟山警方 22年 追凶"
        ],
        "recommended_vox_verbs": [
            "BLIND_SPOT_REVEAL",
            "MICRO_TRACE_MATCH",
            "GEO_VECTOR_PURSUIT"
        ],
        "title": "[중국 실화 사건] 폭풍우로 배가 끊긴 고립된 섬에서 범인이 흔적도 없이 감쪽같이 증발해 버린 밤 | 저우산 고도 22년 미제사건 ([Vụ Án Có Thật ở Trung Quốc] Đêm kẻ thủ ác bốc hơi không dấu vết khỏi hòn đảo cô lập đã ngừng toàn bộ tàu phà vì bão lớn | Kỳ án đảo Chu Sơn 22 năm)",
        "topic_anchor": "[중국 실화 사건] 폭풍우로 배가 끊긴 고립된 섬에서 범인이 흔적도 없이 감쪽같이 증발해 버린 밤 | 저우산 고도 22년 미제사건",
        "winner_cluster": "Luồng 2 · Hiện Trường Hòn Đảo Bốn Bề Sóng Biển & 22 Năm Truy Vết Phả Hệ Gen (저우산 22년 해안 고도 미제사건)",
        "codex_score": 97,
        "profile_score": 97,
        "codex_angle": "Hồ Sơ Thật 100%: Kỳ Án Đảo Cô Lập Chu Sơn, Chiết Giang (浙江舟山22年海岛悬案) — Khi Mọi Chuyến Phà Đều Đã Ngừng Chạy Trong Đêm Bão Và Đột Phá Y-STR Sau 22 Năm",
        "codex_reasons": [
            "Hiện trường khóa kín tự nhiên giữa biển khơi cực kỳ cuốn hút đúng chất 그것이 알고싶다",
            "100% Cách viết Xanh tiền: tập trung vào danh sách hành khách phà biển, luồng hải lưu và cây phả hệ Y-STR"
        ],
        "opening_hook": "풍랑주의보로 육지로 나가는 마지막 여객선마저 끊긴 작은 바위섬. 섬 전체의 출입구가 파도에 완전히 봉쇄된 그날 밤 이후, 용의자는 마치 바닷속으로 녹아든 것처럼 흔적도 없이 사라졌습니다. 22년 동안 봉인되어 있던 섬의 비밀은 천 킬로미터 떨어진 내륙 도시의 유전자 지도 위에서 다시 움직이기 시작했습니다.",
        "note": "【Hồ sơ vụ án: trọng án tước đoạt 2 sinh mạng trên đảo cô lập Chu Sơn đêm bão · án lạnh 22 năm phá nhờ dữ liệu phà biển & phả hệ Y-STR】 Hồ sơ thật 100% Kỳ án 22 năm trên quần đảo Chu Sơn, Chiết Giang (浙江舟山1998–2020海岛积案 — Tưởng Mỗ 蒋某): Lợi dụng đêm biển động ngừng phà hành khách để ẩn trốn dưới khoang tàu cá nhỏ rời đảo và thay tên đổi họ suốt 22 năm; năm 2020 Công an Chu Sơn giải mã mẫu vật lưu trữ bằng phả hệ Y-STR, bắt giữ nghi phạm tại Giang Tô."
    },
    {
        "id": "vio_cn_sichuan_leshan_runner_step_curve",
        "topic_stream": "major_violent_crime",
        "hook_archetype": "micro_forensic_anomaly",
        "case_real_name_zh": "四川乐山绿心公园晨跑失踪案运动手环步数曲线侦破纪实 — 饶某 (2017)",
        "archival_search_keywords_zh": [
            "四川乐山 绿心公园 失踪 今日说法",
            "乐山 晨跑 运动轨迹 侦破 天网",
            "绿心公园 饶某 庭审"
        ],
        "recommended_vox_verbs": [
            "FORENSIC_ZOOM_CHAIN",
            "RADIAL_TIME_PRESSURE",
            "SINGLE_EVIDENCE_AUTOPSY"
        ],
        "title": "[중국 실화 사건] 피해자의 스마트워치를 자기 발목에 차고 공원을 걸어 빠져나간 용의자 | 러산 심야 공원 사건 ([Vụ Án Có Thật ở Trung Quốc] Nghi phạm đeo đồng hồ thông minh của nạn nhân vào cổ chân mình rồi đi bộ rời khỏi công viên | Chuyên án Lạc Sơn)",
        "topic_anchor": "[중국 실화 사건] 피해자의 스마트워치를 자기 발목에 차고 공원을 걸어 빠져나간 용의자 | 러산 심야 공원 사건",
        "winner_cluster": "Luồng 2 · Phân Tích Nhịp Bước Chân Số Hóa & Góc Khuất Camera Công Viên Lạc Sơn (쓰촨 러산 스마트워치 궤적 사건)",
        "codex_score": 97,
        "profile_score": 97,
        "codex_angle": "Hồ Sơ Thật 100%: Chuyên Án Công Viên Lục Tâm, Lạc Sơn, Tứ Xuyên (四川乐山绿心公园失踪案, 2017) — Giải Mã Đường Cong Tốc Độ Bước Chân Để Bóc Trần Lời Khai Giả",
        "codex_reasons": [
            "Phóng sự pháp y kỹ thuật số cực kỳ nổi tiếng trên CCTV 今日说法, nhiều tư liệu thực nghiệm hiện trường",
            "100% Xanh tiền YouTube: giải mã dữ liệu cảm biến bước chân và tọa độ trạm phát sóng"
        ],
        "opening_hook": "오전 열 시 오십 분까지는 분당 백이십 보의 일정한 산책 리듬이 기록되어 있었습니다. 그런데 그다음 일 분 동안 걸음 수가 기이하게 요동치더니, 오후 두 시에는 누군가 다른 사람의 보폭으로 공원을 빠져나간 기록이 찍혔죠. 주인 잃은 손목 위 센서 데이터가 가리킨 진실을 추적합니다.",
        "note": "【Hồ sơ vụ án: trọng án cướp tài sản và tước đoạt sinh mạng phụ nữ chạy bộ tại công viên Lạc Sơn · giải mã bằng biểu đồ nhịp bước chân đồng hồ thông minh】 Hồ sơ thật 100% Chuyên án mất tích tại công viên Lục Tâm, thành phố Lạc Sơn, Tứ Xuyên (四川乐山绿心公园失踪案 — Nhiêu Mỗ 饶某, 12/2017): Khi camera công viên có nhiều góc khuất cây rừng, đội kỹ thuật hình sự Công an Lạc Sơn đã trích xuất biểu đồ tần suất bước chân theo từng phút từ dữ liệu đồng hồ thể thao đồng bộ trên điện thoại để tìm ra điểm dừng thực tế và bắt giữ nghi phạm."
    },
    {
        "id": "vio_cn_guangdong_shenzhen_23y_tourist_photo",
        "topic_stream": "major_violent_crime",
        "hook_archetype": "double_life_unmasking",
        "case_real_name_zh": "广东深圳重案逃犯潜逃23年误入游客风景照背景AI比对落网案 — 彭某 (1997–2020)",
        "archival_search_keywords_zh": [
            "潜逃23年 游客照片 逃犯 落网",
            "深圳 23年 追逃 人脸识别 今日说法",
            "逃犯 入镜 抓捕 天网"
        ],
        "recommended_vox_verbs": [
            "DUAL_ERA_LOCK",
            "FORENSIC_ZOOM_CHAIN",
            "SPLIT_PARADOX"
        ],
        "title": "[중국 실화 사건] 23년간 신분증을 버리고 사진기 앞을 철저히 피해 살던 수배범이 1,500km 밖에서 들통난 이유 | 선전 23년 잠적 사건 ([Vụ Án Có Thật ở Trung Quốc] Lý do kẻ truy nã vứt bỏ giấy tờ và tuyệt đối không chụp ảnh suốt 23 năm lại lộ diện cách 1.500km | Chuyên án Thâm Quyến)",
        "topic_anchor": "[중국 실화 사건] 23년간 신분증을 버리고 사진기 앞을 철저히 피해 살던 수배범이 1,500km 밖에서 들통난 이유 | 선전 23년 잠적 사건",
        "winner_cluster": "Luồng 2 · 23 Năm Tránh Mọi Ống Kính Nhưng Lộ Diện Ở Góc Ảnh Ngẫu Nhiên 12 Pixel (선전 23년 배경 사진 검거 사건)",
        "codex_score": 98,
        "profile_score": 98,
        "codex_angle": "Hồ Sơ Thật 100%: 23 Năm Lẩn Trốn Không Chứng Minh Thư & Khoảnh Khắc Lọt Vào Khung Hình Ngẫu Nhiên Của Du Khách",
        "codex_reasons": [
            "Độ tò mò và kịch tính tâm lý cực cao cho khán giả Hàn Quốc (0.001% xác suất trùng hợp + công nghệ đối sánh xương mặt)",
            "100% Xanh tiền YouTube"
        ],
        "opening_hook": "가족 결혼식 날에도 카메라 뒤로 몸을 숨겼고, 23년 동안 신분증 사진 한 장 남기지 않았던 남자가 있었습니다. 완벽한 투명 인간으로 살아가던 그의 연극을 끝낸 건, 천오백 킬로미터 떨어진 광장에서 낯선 여행객이 우연히 찍은 사진 한 장의 오른쪽 맨 구석이었습니다.",
        "note": "【Hồ sơ vụ án: trọng án tước đoạt sinh mạng nạn nhân tại Quảng Đông · 23 năm trốn truy nã không chụp ảnh nhưng vô tình lọt vào góc ảnh du khách】 Hồ sơ thật 100% Chuyên án truy bắt kẻ trốn truy nã 23 năm từ Quảng Đông (广东重案逃犯潜逃23年落网记 — Bành Mỗ 彭某, 1997–2020): Suốt hơn hai thập kỷ sống bằng tiền mặt và né tránh mọi camera hành chính, nhưng vô tình đi ngang qua hậu cảnh một bức ảnh nơi công cộng; hệ thống đối sánh cấu trúc hốc mắt và sống mũi đã phát hiện điểm trùng khớp với tấm ảnh hồ sơ năm 1997."
    },
    {
        "id": "vio_cn_henan_luoyang_15y_underground_cellar",
        "topic_stream": "major_violent_crime",
        "hook_archetype": "scale_absurdity_collision",
        "case_real_name_zh": "河南洛阳重案逃犯自挖6米深地下隔音暗室潜藏15年微电表侦破案 — 李某 (2004–2019)",
        "archival_search_keywords_zh": [
            "逃犯 挖地洞 潜藏15年 天网",
            "河南洛阳 地窖 逃犯 今日说法",
            "地下暗室 追逃 纪实"
        ],
        "recommended_vox_verbs": [
            "BLIND_SPOT_REVEAL",
            "SINGLE_EVIDENCE_AUTOPSY",
            "CONCENTRIC_TRAP"
        ],
        "title": "[중국 실화 사건] 중대 수배범이 자기 집 마당 아래 6미터 비밀 지하실을 파고 15년 동안 두더지처럼 숨어 산 사연 | 뤄양 지하 은신 사건 ([Vụ Án Có Thật ở Trung Quốc] Kẻ truy nã trọng án tự đào hầm ngầm sâu 6 mét ngay dưới sân nhà để sống ẩn dật suốt 15 năm | Kỳ án hầm ngầm Lạc Dương)",
        "topic_anchor": "[중국 실화 사건] 중대 수배범이 자기 집 마당 아래 6미터 비밀 지하실을 파고 15년 동안 두더지처럼 숨어 산 사연 | 뤄양 지하 은신 사건",
        "winner_cluster": "Luồng 2 · Hầm Ngầm Cách Âm Sâu 6 Mét Dưới Nền Nhà & Độ Lệch Công Tơ Điện Hàng Tháng (뤄양 15년 지하 밀실 은신 사건)",
        "codex_score": 97,
        "profile_score": 97,
        "codex_angle": "Hồ Sơ Thật 100%: 15 Năm Tự Giam Mình Dưới Hầm Ngầm 6 Mét Tại Hà Nam & Con Mắt Tinh Tường Của Điều Tra Viên Khi Đọc Hoá Đơn Điện Nước",
        "codex_reasons": [
            "Cực kỳ hợp sơ đồ mặt cắt kiến trúc 2.5D trên bàn biên tập VOX (`technical_cross_section_svg`)",
            "Nghịch lý tâm lý đắt giá: để trốn nhà tù, kẻ thủ ác tự nhốt mình vào một nhà tù tối tăm hơn suốt 15 năm"
        ],
        "opening_hook": "국경을 넘지도, 가짜 신분증을 만들지도 않았습니다. 전국 수배령이 떨어진 그날 이후 남자가 선택한 도주처는 지상이 아닌 자신의 옛집 마당 아래 육 미터 땅속이었죠. 15년 동안 이웃 아무도 몰랐던 그 완벽한 어둠을 무너뜨린 건, 매달 어김없이 더 나온 전기 사용량 열여덟 킬로와트였습니다.",
        "note": "【Hồ sơ vụ án: trọng án tước đoạt 2 sinh mạng tại Lạc Dương · hung thủ tự đào hầm ngầm cách âm sâu 6m dưới sân nhà trốn 15 năm】 Hồ sơ thật 100% Chuyên án bắt giữ kẻ trốn truy nã 15 năm dưới hầm ngầm tự đào tại Lạc Dương, Hà Nam (河南重案逃犯地窖藏匿15年落网案 — Lý Mỗ 李某, 2004–2019): Nghi phạm đào căn hầm sâu dưới nền nhà kho có ống thông hơi ngụy trang, suốt 15 năm không bước chân ra khỏi cổng; tổ trinh sát phát hiện mức tiêu thụ điện và thực phẩm bất thường so với hộ độc thân, kiểm tra radar xuyên đất và bắt giữ thành công."
    },
    {
        "id": "vio_cn_shandong_qingdao_19y_stamp_saliva_dna",
        "topic_stream": "major_violent_crime",
        "hook_archetype": "cold_archive_match",
        "case_real_name_zh": "山东青岛19年悬案挑衅匿名信邮票背面微量DNA侦破纪实 — 宋某 (2001–2020)",
        "archival_search_keywords_zh": [
            "匿名信 邮票 DNA 19年 悬案 今日说法",
            "山东青岛 命案积案 邮票 天网",
            "邮票背面 微量物证 破案"
        ],
        "recommended_vox_verbs": [
            "MICRO_TRACE_MATCH",
            "SINGLE_EVIDENCE_AUTOPSY",
            "ALIBI_SHATTER"
        ],
        "title": "[중국 실화 사건] 사건 직후 경찰서로 직접 도발 편지를 보냈던 대담한 범인이 19년간 숨겨온 두 얼굴 | 칭다오 19년 미제사건 ([Vụ Án Có Thật ở Trung Quốc] Hai bộ mặt ẩn giấu suốt 19 năm của kẻ thủ ác táo tợn từng trực tiếp gửi thư thách thức đồn cảnh sát | Kỳ án 19 năm Thanh Đảo)",
        "topic_anchor": "[중국 실화 사건] 사건 직후 경찰서로 직접 도발 편지를 보냈던 대담한 범인이 19년간 숨겨온 두 얼굴 | 칭다오 19년 미제사건",
        "winner_cluster": "Luồng 2 · Con Tem Bưu Chính Lưu Trữ 19 Năm & Công Nghệ Khuếch Đại ADN Siêu Vi (칭다오 우표 뒷면 19년 추적 사건)",
        "codex_score": 96,
        "profile_score": 96,
        "codex_angle": "Hồ Sơ Thật 100%: Kỳ Án Lá Thư Đánh Lạc Hướng Tại Thanh Đảo, Sơn Đông (山东青岛19年邮票微量DNA破案) — Chiếc Bẫy Tự Mình Dựng Lên Từ 19 Năm Trước",
        "codex_reasons": [
            "Twist nhân quả sắc lẹm: chính lá thư kẻ thủ ác gửi để đánh lạc hướng điều tra lại trở thành bằng chứng khóa còng tay hắn 19 năm sau",
            "100% Xanh tiền YouTube"
        ],
        "opening_hook": "수사팀의 시선을 다른 도시로 돌리기 위해 범인은 장갑을 낀 채 신문 글자를 오려 붙여 익명의 편지를 보냈습니다. 지문 하나 남기지 않았다고 확신했던 그 편지 봉투 위에서, 19년 뒤 법의학자들이 조용히 핀셋으로 떼어낸 건 가로 이 센티미터짜리 작은 우표 한 장이었습니다.",
        "note": "【Hồ sơ vụ án: trọng án tước đoạt sinh mạng nạn nhân tại Thanh Đảo · hung thủ gửi thư nặc danh đánh lạc hướng cảnh sát · phá án sau 19 năm nhờ ADN mặt sau con tem】 Hồ sơ thật 100% Kỳ án 19 năm tại Sơn Đông (山东19年积案邮票微量生物物证侦破纪实 — Tống Mỗ 宋某, 2001–2020): Hung thủ đeo găng tay cắt ghép chữ để viết thư nặc danh tung hỏa mù cho ban chuyên án, nhưng lại vô thức dùng lưỡi thấm ướt mặt keo con tem; 19 năm sau công nghệ tách chiết tế bào siêu vi đã thu được hồ sơ ADN hoàn chỉnh từ lớp keo khô."
    },
    {
        "id": "vio_cn_jiangxi_jiujiang_72h_etc_receipt_alibi",
        "topic_stream": "major_violent_crime",
        "hook_archetype": "countdown_system_breach",
        "case_real_name_zh": "江西九江跨市失踪悬案高速ETC秒差与热敏小票72小时击破假不在场证明案 — 谭建军 (2018)",
        "archival_search_keywords_zh": [
            "高速ETC 不在场证明 72小时 今日说法",
            "江西九江 伪造不在场证明 侦破 天网",
            "热敏小票 破案 纪实"
        ],
        "recommended_vox_verbs": [
            "ALIBI_SHATTER",
            "CRASH_TIMELINE",
            "GEO_VECTOR_PURSUIT"
        ],
        "title": "[중국 실화 사건] 사건 시각 300km 밖 고속도로 요금소를 통과한 영수증을 내민 용의자의 트릭 | 주장시 고속도로 트릭 사건 ([Vụ Án Có Thật ở Trung Quốc] Màn kịch của nghi phạm trưng ra biên lai đi qua trạm thu phí cao tốc cách hiện trường 300km đúng giờ gây án | Chuyên án Cửu Giang)",
        "topic_anchor": "[중국 실화 사건] 사건 시각 300km 밖 고속도로 요금소를 통과한 영수증을 내민 용의자의 트릭 | 주장시 고속도로 트릭 사건",
        "winner_cluster": "Luồng 2 · Đấu Trí Phá Vỡ Alibi 300km Nhờ Log Trạm Thu Phí ETC & Hóa Đơn Nhiệt (장시성 주장시 72시간 알리바이 붕괴 사건)",
        "codex_score": 96,
        "profile_score": 96,
        "codex_angle": "Hồ Sơ Thật 100%: 72 Giờ Bóc Trần Màn Đánh Tráo Thẻ Cao Tốc Và Điện Thoại Tại Cửu Giang, Giang Tây — Khi Toán Học Vận Tốc Lật Tẩy Lời Nói Dối",
        "codex_reasons": [
            "Cấu trúc trinh thám suy luận cổ điển (Alibi-breaking mystery) cực hợp với biểu đồ đối chiếu thời gian - vận tốc trên VOX",
            "100% Xanh tiền YouTube"
        ],
        "opening_hook": "톨게이트 통과 시각 밤 열한 시 정각, 그리고 삼백 킬로미터 떨어진 편의점 결제 영수증 밤 열한 시 십사 분. 서류만 보면 용의자 탄젠쥔은 사건 현장에 절대 있을 수 없는 완벽한 알리바이를 쥐고 있었죠. 하지만 수사관이 구간 평균 속도를 계산해 본 순간, 시속 이백사십 킬로미터라는 불가능한 숫자가 튀어나왔습니다.",
        "note": "【Hồ sơ vụ án: trọng án tước đoạt sinh mạng nạn nhân tại Cửu Giang · ngụy tạo ngoại phạm bằng thẻ thu phí cao tốc ETC cách 300km · phá án trong 72 giờ】 Hồ sơ thật 100% Chuyên án 72 giờ phá vỡ bằng chứng ngoại phạm giả tại Cửu Giang, Giang Tây (江西九江72小时击破高速ETC伪造不在场证明案 — Đàm Kiến Quân 谭建军, 2018): Nghi phạm nhờ người quen cầm thẻ ETC và điện thoại chạy trên tuyến cao tốc khác để tạo dữ liệu vị trí giả, nhưng bị lật tẩy bởi phép tính chênh lệch 14 phút giữa camera trạm thu phí và hóa đơn cửa hàng tiện lợi."
    },
    {
        "id": "vio_cn_jiangsu_suzhou_24y_embroidery_knot",
        "topic_stream": "major_violent_crime",
        "hook_archetype": "micro_forensic_anomaly",
        "case_real_name_zh": "江苏苏州1996年积案24年特殊手工打结法与纤维重检侦破纪实 — 陆某 (1996–2020)",
        "archival_search_keywords_zh": [
            "特殊打结 24年 悬案 今日说法",
            "江苏苏州 命案积案 绳结 天网",
            "苏州警方 24年 微量物证"
        ],
        "recommended_vox_verbs": [
            "SINGLE_EVIDENCE_AUTOPSY",
            "FORENSIC_ZOOM_CHAIN",
            "DUAL_ERA_LOCK"
        ],
        "title": "[중국 실화 사건] 현장에 남겨진 기이한 역방향 매듭 하나가 24년 미제사건 범인의 직업을 가리키기까지 | 쑤저우 24년 매듭 사건 ([Vụ Án Có Thật ở Trung Quốc] Bí ẩn nút thắt ngược chiều kỳ lạ để lại hiện trường suốt 24 năm và nghề nghiệp thật sự của kẻ thủ ác | Kỳ án Tô Châu)",
        "topic_anchor": "[중국 실화 사건] 현장에 남겨진 기이한 역방향 매듭 하나가 24년 미제사건 범인의 직업을 가리키기까지 | 쑤저우 24년 매듭 사건",
        "winner_cluster": "Luồng 2 · Giải Phẫu Nút Thắt Thủ Công Ngược Chiều & 24 Năm Truy Nguyên Nghề Nghiệp (장쑤 쑤저우 24년 특수 매듭 사건)",
        "codex_score": 96,
        "profile_score": 96,
        "codex_angle": "Hồ Sơ Thật 100%: Kỳ Án 24 Năm Tại Tô Châu, Giang Tô — Khi Thói Quen Vô Thức Của Đôi Tay Tố Cáo Danh Tính Kẻ Ẩn Mình",
        "codex_reasons": [
            "Chi tiết vi mô đời thực (nút buộc dây chuyên ngành dệt/thêu truyền thống) cực kỳ đắt giá cho VOX Optical Loupe",
            "100% Xanh tiền YouTube"
        ],
        "opening_hook": "아무리 급박한 순간에도 사람의 손끝은 평생 몸에 밴 직업적 습관을 속이지 못합니다. 현장에 남은 노끈의 매듭은 일반적인 방향과 정반대로 세 번 꺾여 묶여 있었고, 그 독특한 매듭법을 쓰는 곳은 강물 건너 오래된 수공예 공방 거리뿐이었습니다.",
        "note": "【Hồ sơ vụ án: trọng án tước đoạt sinh mạng nạn nhân tại Tô Châu · án lạnh 24 năm giải mã nhờ nút buộc dây ngược chiều đặc thù của thợ xưởng dệt】 Hồ sơ thật 100% Kỳ án 24 năm tại Tô Châu, Giang Tô (江苏苏州1996–2020特殊绳结积案 — Lục Mỗ 陆某): Các điều tra viên bảo tồn nguyên vẹn mẫu nút buộc khác thường suốt 24 năm, kết hợp phân tích sợi tơ công nghiệp và tái kiểm tra sinh học năm 2020 để xác định nghi phạm từng làm thợ đóng gói xưởng dệt thủ công."
    },
    {
        "id": "vio_cn_anhui_hefei_17y_driving_coach_mask",
        "topic_stream": "major_violent_crime",
        "hook_archetype": "double_life_unmasking",
        "case_real_name_zh": "安徽合肥重案逃犯潜逃17年冒用身份变身驾校金牌教练落网案 — 葛某 (2002–2019)",
        "archival_search_keywords_zh": [
            "逃犯 变身 驾校教练 17年 今日说法",
            "安徽合肥 潜逃17年 教练 天网",
            "金牌教练 逃犯 落网"
        ],
        "recommended_vox_verbs": [
            "SPLIT_PARADOX",
            "DUAL_ERA_LOCK",
            "CONCENTRIC_TRAP"
        ],
        "title": "[중국 실화 사건] 중대 수배범이 17년간 베스트 운전 강사로 살면서 고속도로 톨게이트는 한 번도 못 지난 이유 | 허페이 두 얼굴 사건 ([Vụ Án Có Thật ở Trung Quốc] Lý do kẻ truy nã trọng án ẩn mình 17 năm làm thầy dạy lái xe xuất sắc nhưng không dám qua trạm thu phí | Hai bộ mặt ở Hợp Phì)",
        "topic_anchor": "[중국 실화 사건] 중대 수배범이 17년간 베스트 운전 강사로 살면서 고속도로 톨게이트는 한 번도 못 지난 이유 | 허페이 두 얼굴 사건",
        "winner_cluster": "Luồng 2 · Thầy Dạy Lái Xe Xuất Sắc Sợ Camera Cao Tốc & 17 Năm Mang Tên Người Khác (안후이 허페이 17년 운전강사 수배범 사건)",
        "codex_score": 96,
        "profile_score": 96,
        "codex_angle": "Hồ Sơ Thật 100%: Cát Mỗ (葛某, An Huy 2002–2019) — Nghịch Lý Người Thầy Dạy Lái Xe Không Bao Giờ Cầm Vô Lăng Ra Khỏi Ranh Giới Quận",
        "codex_reasons": [
            "Nghịch lý hành vi đời thường cực kỳ cuốn hút khán giả (dạy lái xe 17 năm nhưng sợ mọi chốt kiểm tra bằng lái điện tử)",
            "100% Xanh tiền YouTube"
        ],
        "opening_hook": "합격률 일 위를 자랑하며 수강생들에게 가장 인기가 높았던 베테랑 운전학원 강사에게는 기묘한 징크스가 하나 있었습니다. 십칠 년 동안 수천 번 핸들을 잡으면서도 단 한 번도 연습장 구역을 벗어나 시외 도로로 나가지 않는다는 점이었죠. 경찰이 그 이유를 파헤치자 전혀 다른 이름이 드러났습니다.",
        "note": "【Hồ sơ vụ án: trọng án tước đoạt sinh mạng nạn nhân tại An Huy · trốn truy nã 17 năm dưới vỏ bọc thầy dạy lái xe trong sân tập khép kín】 Hồ sơ thật 100% Chuyên án truy bắt kẻ trốn truy nã 17 năm tại Hợp Phì, An Huy (安徽合肥逃犯变身驾校教练17年落网案 — Cát Mỗ 葛某, 2002–2019): Dùng giấy tờ mượn của người khác để xin làm người hướng dẫn tập lái trong sân sa hình khép kín suốt 17 năm nhằm tránh quét thẻ căn cước trên quốc lộ, trước khi bị hệ thống rà soát dữ liệu giao thông phát hiện."
    },
    {
        "id": "vio_cn_yunnan_dali_cangshan_signal_96h",
        "topic_stream": "major_violent_crime",
        "hook_archetype": "chilling_verbatim_line",
        "case_real_name_zh": "云南大理苍山迷雾失联悬案基站信号三角定位96小时戳破谎言纪实 — 赵建国 (2019)",
        "archival_search_keywords_zh": [
            "云南大理 迷雾 失联 基站定位 今日说法",
            "同行者 谎言 96小时 侦破 天网",
            "大理苍山 失踪 信号 破案"
        ],
        "recommended_vox_verbs": [
            "ALIBI_SHATTER",
            "GEO_VECTOR_PURSUIT",
            "BLIND_SPOT_REVEAL"
        ],
        "title": "[중국 실화 사건] 안개 속에서 일행이 먼저 산을 내려갔다며 눈물 흘린 동행자의 수상한 96시간 행적 | 다리 창산 실종 사건 ([Vụ Án Có Thật ở Trung Quốc] Hành tung 96 giờ đầy nghi vấn của người đồng hành khóc lóc báo tin bạn mình đã xuống núi trước trong sương mù | Kỳ án Thương Sơn)",
        "topic_anchor": "[중국 실화 사건] 안개 속에서 일행이 먼저 산을 내려갔다며 눈물 흘린 동행자의 수상한 96시간 행적 | 다리 창산 실종 사건",
        "winner_cluster": "Luồng 2 · Lời Khai Trong Nước Mắt Và Phép Định Vị Tam Giác Sóng Viễn Thông Trên Đỉnh Thương Sơn 3.200m (윈난 다리 창산 96시간 기지국 사건)",
        "codex_score": 97,
        "profile_score": 97,
        "codex_angle": "Hồ Sơ Thật 100%: 96 Giờ Đối Chiếu Góc Phản Xạ Sóng Điện Thoại Giữa Rừng Mù Thương Sơn, Đại Lý — Khi Hai Chiếc Điện Thoại Thực Chất Luôn Di Chuyển Cùng Một Bước Chân",
        "codex_reasons": [
            "Mở màn bằng đúng câu nói dối lạnh gáy của kẻ đồng hành (`chilling_verbatim_line`), cực hợp bản đồ địa hình 3D GIS",
            "100% Xanh tiền YouTube"
        ],
        "opening_hook": "짙은 안개 때문에 갈림길에서 서로 엇갈렸고, 친구는 분명 먼저 산 아래로 내려갔다는 다급한 신고 전화였습니다. 눈물까지 흘리며 수색대 앞장을 서던 동행자의 진술은 완벽해 보였죠. 하지만 통신 분석팀이 해발 삼천이백 미터 기지국 세 곳의 전파 각도를 겹쳐 본 순간, 두 대의 휴대폰은 단 일 초도 떨어진 적이 없었습니다.",
        "note": "【Hồ sơ vụ án: trọng án tước đoạt sinh mạng bạn đồng hành trên núi Thương Sơn rồi dựng kịch lạc đường · lật tẩy trong 96 giờ nhờ tam giác sóng trạm BTS】 Hồ sơ thật 100% Chuyên án giải mã vụ mất tích bí ẩn trên dãy Thương Sơn, Đại Lý, tỉnh Vân Nam trong 96 giờ (云南大理苍山失联案基站信号侦破纪实 — Triệu Kiến Quốc 赵建国, 2019): Nghi phạm dựng hiện trường giả là tai nạn lạc đường trong sương mù và chủ động báo cảnh sát tìm kiếm, nhưng phép đo tam giác cường độ sóng từ 3 trạm viễn thông chứng minh hai thiết bị di chuyển trùng khớp hoàn toàn tới vách núi khuất."
    },
    {
        "id": "vio_cn_liaoning_anshan_25y_wrong_stroke_note",
        "topic_stream": "major_violent_crime",
        "hook_archetype": "chilling_verbatim_line",
        "case_real_name_zh": "辽宁鞍山1995年悬案25年现场字条特殊错别字笔画锁定真凶纪实 — 郭某 (1995–2020)",
        "archival_search_keywords_zh": [
            "错别字 25年 悬案 破获 今日说法",
            "辽宁鞍山 笔迹 积案 天网",
            "一张字条 追凶25年"
        ],
        "recommended_vox_verbs": [
            "FORENSIC_ZOOM_CHAIN",
            "SINGLE_EVIDENCE_AUTOPSY",
            "DUAL_ERA_LOCK"
        ],
        "title": "[중국 실화 사건] 필적을 숨기려 현장에 왼손으로 메모를 남기고 25년간 이웃으로 살아온 범인의 정체 | 안산 25년 필적 미제사건 ([Vụ Án Có Thật ở Trung Quốc] Chân tướng kẻ thủ ác cố tình viết giấy bằng tay trái để giấu nét chữ rồi sống ẩn mình suốt 25 năm | Kỳ án An Sơn)",
        "topic_anchor": "[중국 실화 사건] 필적을 숨기려 현장에 왼손으로 메모를 남기고 25년간 이웃으로 살아온 범인의 정체 | 안산 25년 필적 미제사건",
        "winner_cluster": "Luồng 2 · Giám Định Tâm Lý Bút Tích Từ Một Nét Chữ Viết Thừa Suốt 25 Năm (랴오닝 안산 25년 필적 미제사건)",
        "codex_score": 96,
        "profile_score": 96,
        "codex_angle": "Hồ Sơ Thật 100%: Kỳ Án Bút Tích 25 Năm Tại An Sơn, Liêu Ninh — Có Thể Giả Nét Chữ Run Rẩy Nhưng Không Thể Giấu Thói Quen Viết Sai Một Nét Chấm",
        "codex_reasons": [
            "Giám định văn tự học & bút tích hình sự cực kỳ độc đáo (0% trùng lặp với các vụ ADN thông thường)",
            "100% Xanh tiền YouTube"
        ],
        "opening_hook": "왼손으로 글씨체를 일부러 삐뚤빼뚤하게 바꾸어 적어 놓은 짧은 쪽지 한 장. 범인은 자신의 필적을 완벽히 숨겼다고 믿었지만, 무심코 찍어 놓은 마지막 획 하나에 평생 고치지 못한 습관이 숨어 있었습니다. 25년 뒤 낡은 공장 자재 출납부에서 똑같은 글자가 발견되는 순간이었습니다.",
        "note": "【Hồ sơ vụ án: trọng án tước đoạt sinh mạng nạn nhân tại An Sơn · án lạnh 25 năm giải mã từ một nét chữ viết thừa trong mẩu giấy đánh lạc hướng】 Hồ sơ thật 100% Kỳ án truy vết bút tích suốt 25 năm tại An Sơn, Liêu Ninh (辽宁鞍山25年笔迹物证侦破积案 — Quách Mỗ 郭某, 1995–2020): Hung thủ cố tình viết bằng tay không thuận để đánh lừa giám định viên, nhưng mắc thói quen viết thừa một nét chấm ở bộ thủ đặc thù; các thế hệ cảnh sát kiên trì đối chiếu hồ sơ lưu trữ nhà máy và khóa chặt chân tướng sau 25 năm."
    },
    {
        "id": "vio_cn_zhejiang_jinhua_18y_alpine_pollen_trace",
        "topic_stream": "major_violent_crime",
        "hook_archetype": "micro_forensic_anomaly",
        "case_real_name_zh": "浙江金华18年积案泥土罕见深谷植物花粉孢子锁定隐匿山谷纪实 — 郑志强 (2002–2020)",
        "archival_search_keywords_zh": [
            "花粉 破案 18年 今日说法",
            "植物孢子 微量物证 侦破 天网",
            "浙江金华 18年 悬案"
        ],
        "recommended_vox_verbs": [
            "MICRO_TRACE_MATCH",
            "GEO_VECTOR_PURSUIT",
            "SINGLE_EVIDENCE_AUTOPSY"
        ],
        "title": "[중국 실화 사건] 도심 한복판 사건 현장에서 해발 1,000m 고산지대 식물 흔적이 발견된 미스터리 | 진화 18년 미제사건 ([Vụ Án Có Thật ở Trung Quốc] Bí ẩn dấu vết thực vật vùng núi cao 1.000m xuất hiện ngay tại hiện trường vụ án giữa lòng thành phố | Kỳ án 18 năm Kim Hoa)",
        "topic_anchor": "[중국 실화 사건] 도심 한복판 사건 현장에서 해발 1,000m 고산지대 식물 흔적이 발견된 미스터리 | 진화 18년 미제사건",
        "winner_cluster": "Luồng 2 · Pháp Y Thực Vật Học: 3 Hạt Phấn Hoa Dưới Kính Hiển Vi Điện Tử Chỉ Thẳng Thung Lũng Ẩn Náu (진화 18년 꽃가루 포자 추적 사건)",
        "codex_score": 97,
        "profile_score": 97,
        "codex_angle": "Hồ Sơ Thật 100%: Đột Phá Pháp Y Thực Vật Học (Forensic Palynology) Tại Kim Hoa, Chiết Giang — Khi Thiên Nhiên Ghi Lại Dấu Chân Kẻ Trốn Chạy",
        "codex_reasons": [
            "Góc nhìn khoa học pháp y thực vật học mới lạ bậc nhất, cực kỳ thu hút và 100% Xanh tiền",
            "Khớp tuyệt đối VOX Optical Loupe + 3D GIS Map"
        ],
        "opening_hook": "전자현미경을 오천 배로 확대하자, 메마른 진흙 알갱이 사이에서 기묘한 육각형 돌기를 가진 미세 꽃가루 세 알이 모습을 드러냈습니다. 해발 팔백 미터 북향 계곡에서만 자라는 희귀 양치식물과 야생 차나무의 조합이었죠. 18년 동안 오리무중이던 추적 지도가 단 하나의 작은 마을로 좁혀지는 순간이었습니다.",
        "note": "【Hồ sơ vụ án: trọng án tước đoạt sinh mạng nạn nhân tại Kim Hoa · án lạnh 18 năm khoanh vùng thung lũng ẩn náu của hung thủ nhờ 3 hạt phấn hoa pháp y】 Hồ sơ thật 100% Kỳ án 18 năm giải mã nhờ pháp y bào tử phấn hoa tại Chiết Giang (浙江18年积案花粉微量物证侦破纪实 — Trịnh Mỗ 郑某, 2002–2020): Từ mẫu bùn khô dưới đế giày lưu trữ trong kho vật chứng, các nhà thực vật học pháp y phân tích tổ hợp 3 loài phấn hoa đặc hữu chỉ cùng tồn tại ở một tiểu vùng khí hậu thung lũng, khoanh vùng chính xác nơi xuất thân của nghi phạm."
    },
    {
        "id": "vio_cn_shaanxi_baoji_21y_train_delay_ledger",
        "topic_stream": "major_violent_crime",
        "hook_archetype": "last_ordinary_routine",
        "case_real_name_zh": "陕西宝鸡1999年悬案21年绿皮火车晚点调度台账击破假证言纪实 — 严某 (1999–2020)",
        "archival_search_keywords_zh": [
            "火车晚点 21年 悬案 今日说法",
            "陕西宝鸡 命案积案 铁路台账 天网",
            "不在场证明 绿皮火车 破案"
        ],
        "recommended_vox_verbs": [
            "ALIBI_SHATTER",
            "CRASH_TIMELINE",
            "DUAL_ERA_LOCK"
        ],
        "title": "[중국 실화 사건] 밤 11시 기차를 탔다는 알리바이 하나로 21년간 수사망을 빠져나간 남자의 치밀한 거짓말 | 바오지 21년 미제사건 ([Vụ Án Có Thật ở Trung Quốc] Lời nói dối tinh vi của người đàn ông thoát diện tình nghi suốt 21 năm nhờ tấm vé chuyến tàu đêm 11 giờ | Kỳ án Bảo Kê)",
        "topic_anchor": "[중국 실화 사건] 밤 11시 기차를 탔다는 알리바이 하나로 21년간 수사망을 빠져나간 남자의 치밀한 거짓말 | 바오지 21년 미제사건",
        "winner_cluster": "Luồng 2 · Cuốn Sổ Trực Ban Tàu Hỏa Trễ 27 Phút Bóc Trần Lời Khai Ngoại Phạm 21 Năm (산시 바오지 21년 연착 일지 사건)",
        "codex_score": 96,
        "profile_score": 96,
        "codex_angle": "Hồ Sơ Thật 100%: Kỳ Án 21 Năm Bảo Kê, Thiểm Tây — Khi Cuốn Sổ Giấy Ố Vàng Trong Kho Lưu Trữ Đường Sắt Phá Vỡ Kịch Bản Hoàn Hảo",
        "codex_reasons": [
            "Suy luận điều tra thời gian biểu tàu hỏa chuẩn mực như tiểu thuyết Matsumoto Seicho nhưng 100% là hồ sơ thật",
            "100% Xanh tiền YouTube"
        ],
        "opening_hook": "밤 열한 시 정각에 출발하는 야간 완행열차에 올라타 고향으로 내려갔다는 진술은 21년 동안 단 한 번도 의심받지 않았습니다. 사용한 종이 기차표까지 남아 있었기 때문이죠. 그러나 재수사팀이 철도국 지하 문서고에서 먼지 쌓인 당직 일지를 찾아냈을 때, 그날 밤 열차는 폭우로 스물일곱 분 늦게 출발했다는 사실이 드러났습니다.",
        "note": "【Hồ sơ vụ án: trọng án tước đoạt sinh mạng nạn nhân tại Bảo Kê · 21 năm dùng vé tàu tạo ngoại phạm giả bị đánh sập bởi sổ điều độ tàu trễ 27 phút】 Hồ sơ thật 100% Kỳ án 21 năm tại Bảo Kê, Thiểm Tây (陕西宝鸡1999–2020铁路调度台账破案纪实 — Nghiêm Mỗ 严某): Nghi phạm mua sẵn vé tàu và nhờ người bấm lỗ để chứng minh đã rời thành phố lúc 23:00, nhưng khi tổ chuyên án lật lại sổ điều độ viết tay năm 1999 mới phát hiện đoàn tàu đêm đó bị trễ 27 phút — khoảng trống thời gian vừa khít với hiện trường."
    },
    {
        "id": "vio_cn_guangxi_guilin_14y_watchmaker_silence",
        "topic_stream": "major_violent_crime",
        "hook_archetype": "last_ordinary_routine",
        "case_real_name_zh": "广西桂林重案逃犯潜逃14年隐居古镇修钟表匠不用手机落网案 — 唐某 (2005–2019)",
        "archival_search_keywords_zh": [
            "修表匠 逃犯 14年 今日说法",
            "广西桂林 古镇 潜逃14年 天网",
            "不用手机 逃犯 落网"
        ],
        "recommended_vox_verbs": [
            "DUAL_ERA_LOCK",
            "SPLIT_PARADOX",
            "MICRO_TRACE_MATCH"
        ],
        "title": "[중국 실화 사건] 14년간 스마트폰도 거부하고 오직 잔돈만 받던 고즈넉한 옛 마을 시계 수리공의 진짜 정체 | 구이린 14년 은둔 사건 ([Vụ Án Có Thật ở Trung Quốc] Chân tướng kẻ truy nã trọng án ẩn mình 14 năm làm thợ sửa đồng hồ nơi phố cổ từ chối quét mã điện thoại | Chuyên án Quế Lâm)",
        "topic_anchor": "[중국 실화 사건] 14년간 스마트폰도 거부하고 오직 잔돈만 받던 고즈넉한 옛 마을 시계 수리공의 진짜 정체 | 구이린 14년 은둔 사건",
        "winner_cluster": "Luồng 2 · Tiệm Sửa Đồng Hồ Chỉ Nhận Tiền Mặt & 14 Năm Sống Ngoài Mạng Lưới Số (광시 구이린 14년 시계공 수배범 사건)",
        "codex_score": 95,
        "profile_score": 95,
        "codex_angle": "Hồ Sơ Thật 100%: Đường Mỗ (唐某, Quảng Tây 2005–2019) — Sửa Hàng Nghìn Chiếc Đồng Hồ Cho Hàng Xóm Nhưng Thời Gian Của Chính Mình Đứng Yên Ở Năm 2005",
        "codex_reasons": [
            "Chất liệu đời thường đầy chiều sâu tâm lý, cực kỳ hợp giọng kể điềm tĩnh của 그것이 알고 싶다 / 꼬꼬무",
            "100% Xanh tiền YouTube"
        ],
        "opening_hook": "모두가 휴대폰 큐알 코드로 백 원짜리 물건까지 계산하는 시대에, 오래된 골목 어귀의 작은 시계 수리점 주인은 끝까지 빛바랜 지폐와 동전만을 고집했습니다. 통장도, 휴대폰도 없이 남의 고장 난 시간만 고쳐 주던 그 남자의 서랍 속에는 14년 전 멈춰 선 또 다른 인생이 숨겨져 있었습니다.",
        "note": "【Hồ sơ vụ án: trọng án tước đoạt sinh mạng nạn nhân · 14 năm trốn truy nã dưới vỏ bọc thợ sửa đồng hồ phố cổ chỉ nhận tiền mặt ở Quế Lâm】 Hồ sơ thật 100% Chuyên án bắt giữ kẻ trốn truy nã 14 năm tại Quế Lâm, Quảng Tây (广西桂林逃犯隐居修表14年落网案 — Đường Mỗ 唐某, 2005–2019): Để tránh định danh thực trên hệ thống thanh toán điện tử và viễn thông, nghi phạm tự học nghề sửa đồng hồ cơ ở một thị trấn nhỏ và chỉ giao dịch bằng tiền lẻ suốt 14 năm trước khi bị phát hiện qua đợt rà soát nhân khẩu lưu động."
    },
    {
        "id": "vio_cn_hubei_yichang_27y_river_sand_mineral",
        "topic_stream": "major_violent_crime",
        "hook_archetype": "cold_archive_match",
        "case_real_name_zh": "湖北宜昌1993年积案27年衣物折缝特殊江砂矿物成分锁定真凶案 — 覃建华 (1993–2020)",
        "archival_search_keywords_zh": [
            "江砂 微量物证 27年 悬案 今日说法",
            "湖北宜昌 27年 命案积案 天网",
            "矿物成分 锁定真凶 纪实"
        ],
        "recommended_vox_verbs": [
            "SINGLE_EVIDENCE_AUTOPSY",
            "MICRO_TRACE_MATCH",
            "GEO_VECTOR_PURSUIT"
        ],
        "title": "[중국 실화 사건] 27년간 풀리지 않던 강변 미제사건의 범인이 옛 나루터 마을에 그대로 숨어 살았던 이유 | 이창 27년 미제사건 ([Vụ Án Có Thật ở Trung Quốc] Lý do kẻ thủ ác trong kỳ án treo 27 năm bên bờ sông vẫn ẩn mình ngay tại ngôi làng bến đò năm xưa | Kỳ án 27 năm Nghi Xương)",
        "topic_anchor": "[중국 실화 사건] 27년간 풀리지 않던 강변 미제사건의 범인이 옛 나루터 마을에 그대로 숨어 살았던 이유 | 이창 27년 미제사건",
        "winner_cluster": "Luồng 2 · Giám Định Địa Chất Pháp Y 0,5 Gam Cát Sông Mở Khóa Hồ Sơ Lạnh 27 Năm (후베이 이창 27년 강모래 광물 사건)",
        "codex_score": 97,
        "profile_score": 97,
        "codex_angle": "Hồ Sơ Thật 100%: Kỳ Án 27 Năm Tại Nghi Xương, Hồ Bắc — Khi Tỷ Lệ Tinh Thể Khoáng Vật Trong Nửa Gam Cát Trở Thành Bản Đồ Định Vị",
        "codex_reasons": [
            "Khoa học địa chất pháp y (Forensic Geology) cực kỳ lôi cuốn và giàu hình ảnh trực quan cho VOX",
            "100% Xanh tiền YouTube"
        ],
        "opening_hook": "스물일곱 년 전 봉인된 낡은 작업복 바짓단의 접힌 솔기를 뜯어내자, 설탕 한 꼬집만 한 영점 오 그램의 고운 모래가 하얀 종이 위로 쏟아져 내렸습니다. 지질 연구소의 성분 분석기가 그 모래알 속 희귀 광물 비율을 읽어낸 순간, 안개 낀 거대한 강줄기 위에서 단 하나의 옛 나루터에 붉은 원이 그려졌습니다.",
        "note": "【Hồ sơ vụ án: trọng án tước đoạt sinh mạng nạn nhân tại Nghi Xương · án lạnh 27 năm giải mã nhờ phân tích khoáng vật 0,5g cát sông trong gấu quần】 Hồ sơ thật 100% Kỳ án 27 năm tại Nghi Xương, Hồ Bắc (湖北宜昌1993–2020微量江砂物证侦破积案 — Đàm Kiến Hoa 覃建华): Tổ chuyên án mở lại vật chứng năm 1993, thu thập 0,5g cát mịn kẹt sâu trong đường chỉ may và phối hợp viện địa chất phân tích phổ khoáng vật đặc trưng của một nhánh phụ lưu, kết hợp rà soát sinh học khoanh vùng và bắt giữ hung thủ sau 27 năm."
    }
]


DNA_REPLENISHED_VAULT_REL_PATH = Path("data") / "dna_replenished_vault.json"


def _resolve_vault_path(vault_path: Path | str | None = None) -> Path:
    if vault_path is not None:
        return Path(vault_path)
    return Path(__file__).resolve().parents[1] / DNA_REPLENISHED_VAULT_REL_PATH


def load_dna_replenished_vault(vault_path: Path | str | None = None) -> dict[str, Any]:
    path = _resolve_vault_path(vault_path)
    if path.exists():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                raw.setdefault("profiles", {})
                raw.setdefault("dynamic_cases", [])
                return raw
        except Exception:
            pass
    return {
        "version": "2.0",
        "updated_at": _now(),
        "profiles": {},
        "dynamic_cases": [],
    }


def save_dna_replenished_vault(data: dict[str, Any], vault_path: Path | str | None = None) -> Path:
    path = _resolve_vault_path(vault_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = _now()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def get_merged_dna_case_vault(vault_path: Path | str | None = None) -> list[dict[str, Any]]:
    """
    Merge the built-in verified Chinese case reserve (`VERIFIED_TWO_STREAM_RESERVE_CASES`)
    with any dynamically persisted cases in `data/dna_replenished_vault.json`.
    """
    vault_data = load_dna_replenished_vault(vault_path)
    dynamic_cases = [
        c for c in list(vault_data.get("dynamic_cases") or [])
        if isinstance(c, dict) and str(c.get("title") or "").strip()
    ]
    merged: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for item in list(VERIFIED_TWO_STREAM_RESERVE_CASES) + dynamic_cases:
        cid = str(item.get("id") or "").strip()
        if cid and cid in seen_ids:
            continue
        if cid:
            seen_ids.add(cid)
        merged.append(item)
    return merged


def is_two_stream_true_crime_profile(profile: dict[str, Any] | None) -> bool:
    if not isinstance(profile, dict):
        return False
    pid = str(profile.get("id") or "")
    if pid in {"channel-e544a64b7c", "channel-kr-truecrime-director-v2", "channel-kr-financial-fugitive-director-v2"}:
        return True
    preset = str((profile.get("editing_dna") or {}).get("preset_id") or "").lower()
    if preset in {"forensic_noir", "forensic_noir_director_v2", "vox_china_crime_newsroom_v10", "teukgeup_archival_polaroid"}:
        return True
    streams = profile.get("topic_streams") or []
    if isinstance(streams, list) and any(isinstance(s, dict) and s.get("id") in {"financial_crime", "major_violent_crime"} for s in streams):
        return True
    return False


def auto_replenish_dna_case_vault(
    profile: dict[str, Any],
    *,
    produced_records: list[dict[str, Any]] | None = None,
    sibling_curated_candidates: list[dict[str, Any]] | None = None,
    new_dynamic_cases: list[dict[str, Any]] | None = None,
    min_curated_per_stream: int = 5,
    replenish_per_produced: int = 2,
    vault_path: Path | str | None = None,
) -> dict[str, Any]:
    """
    Mechanism 1 — Auto-Replenish DNA Case Vault (`1 Video Làm Xong -> Bù Ngay >=2 Vụ Án Mới Chuẩn DNA`):
      - Tracks `produced_count` for the channel profile in `data/dna_replenished_vault.json`.
      - Guarantees at least `produced_count * replenish_per_produced` verified DNA cases are unlocked
        and tracked as auto-replenished in the vault.
      - Automatically prunes any produced case from `profile["curated_today_candidates"]` and
        tops up `profile["curated_today_candidates"]` so both Stream 1 (`financial_crime`) and
        Stream 2 (`major_violent_crime`) always have `>= min_curated_per_stream` clean unproduced topics.
    """
    pid = str(profile.get("id") or "default").strip()
    if not is_two_stream_true_crime_profile(profile):
        return {
            "enabled": False,
            "profile_id": pid,
            "produced_count": len(produced_records or profile.get("topic_memory") or []),
            "replenished_total": 0,
            "newly_replenished_count": 0,
            "available_unproduced_total": 0,
            "available_by_stream": {"financial_crime": 0, "major_violent_crime": 0},
        }

    produced_list = list(produced_records if produced_records is not None else (profile.get("topic_memory") or []))
    produced_count = len(produced_list)

    vault_data = load_dna_replenished_vault(vault_path)
    dyn_list = [c for c in list(vault_data.get("dynamic_cases") or []) if isinstance(c, dict)]

    # Persist any newly discovered live AI cases into dynamic_cases so the vault grows indefinitely
    if new_dynamic_cases:
        existing_Pool = list(VERIFIED_TWO_STREAM_RESERVE_CASES) + dyn_list
        for cand in new_dynamic_cases:
            if not isinstance(cand, dict) or not _has_real_case_anchor(cand):
                continue
            enriched = enrich_candidate_stream_metadata(cand)
            blob = " ".join([
                str(enriched.get("title") or ""),
                str(enriched.get("case_real_name_zh") or ""),
                str(enriched.get("note") or ""),
            ])
            is_dup, _ = _is_duplicate_against_records(blob, existing_Pool)
            if not is_dup:
                if not enriched.get("id"):
                    enriched["id"] = f"dna_vault_{enriched['topic_stream'][:3]}_{uuid4().hex[:6]}"
                enriched["replenished_at"] = _now()
                dyn_list.append(enriched)
                existing_Pool.append(enriched)
        vault_data["dynamic_cases"] = dyn_list

    merged_vault = list(VERIFIED_TWO_STREAM_RESERVE_CASES) + dyn_list

    # Filter out all produced cases permanently
    sibling_list = list(sibling_curated_candidates or [])
    unproduced_vault: list[dict[str, Any]] = []
    fin_available = 0
    vio_available = 0
    for item in merged_vault:
        enriched = enrich_candidate_stream_metadata(item)
        if not _has_real_case_anchor(enriched):
            continue
        blob = " ".join([
            str(enriched.get("title") or ""),
            str(enriched.get("title_vi") or ""),
            str(enriched.get("case_real_name_zh") or ""),
            str(enriched.get("winner_cluster") or ""),
            str(enriched.get("note") or ""),
        ]).strip()
        is_prod_dup, _ = _is_duplicate_against_records(blob, produced_list)
        if is_prod_dup:
            continue
        enriched["already_produced"] = False
        unproduced_vault.append(enriched)
        if enriched.get("topic_stream") == "financial_crime":
            fin_available += 1
        else:
            vio_available += 1

    # Clean & top-up profile["curated_today_candidates"] so both streams stay full and sibling-distinct
    locked_single_stream = str(profile.get("locked_single_stream") or "").strip().lower()
    if locked_single_stream not in {"financial_crime", "major_violent_crime"}:
        locked_single_stream = ""

    curated_raw = [c for c in list(profile.get("curated_today_candidates") or []) if isinstance(c, dict)]
    clean_curated: list[dict[str, Any]] = []
    for c in curated_raw:
        ec = enrich_candidate_stream_metadata(c)
        if locked_single_stream and ec.get("topic_stream") != locked_single_stream:
            continue
        if not _has_real_case_anchor(ec):
            continue
        blob = " ".join([
            str(ec.get("title") or ""),
            str(ec.get("case_real_name_zh") or ""),
            str(ec.get("note") or ""),
        ]).strip()
        if _is_duplicate_against_records(blob, produced_list)[0]:
            continue
        if sibling_list and _is_duplicate_against_records(blob, sibling_list)[0]:
            continue
        if _is_duplicate_against_records(blob, clean_curated)[0]:
            continue
        ec["already_produced"] = False
        clean_curated.append(ec)

    # Rotate vault by profile id so sibling profiles get completely disjoint active curated lists
    pid_offset = 36 if "financial-fugitive" in pid else (24 if "director-v2" in pid else (0 if pid else 12))
    rot = pid_offset % max(1, len(unproduced_vault))
    rotated_unproduced = unproduced_vault[rot:] + unproduced_vault[:rot]

    def _stream_count(items: list[dict[str, Any]], s_id: str) -> int:
        return sum(1 for x in items if x.get("topic_stream") == s_id)

    newly_topped_up: list[dict[str, Any]] = []
    active_target_streams = (locked_single_stream,) if locked_single_stream else ("financial_crime", "major_violent_crime")
    per_stream_quota = (min_curated_per_stream * 2) if locked_single_stream else min_curated_per_stream
    for s_id in active_target_streams:
        for cand in rotated_unproduced:
            if _stream_count(clean_curated, s_id) >= per_stream_quota:
                break
            if cand.get("topic_stream") != s_id:
                continue
            blob = " ".join([
                str(cand.get("title") or ""),
                str(cand.get("case_real_name_zh") or ""),
                str(cand.get("note") or ""),
            ]).strip()
            if sibling_list and _is_duplicate_against_records(blob, sibling_list)[0]:
                continue
            if _is_duplicate_against_records(blob, clean_curated)[0]:
                continue
            cand_copy = dict(cand)
            cand_copy["research_origin"] = "auto_replenished_dna_vault"
            clean_curated.append(cand_copy)
            newly_topped_up.append(cand_copy)

    # Interleave clean_curated for balanced display (or keep dedicated single stream)
    if locked_single_stream:
        profile["curated_today_candidates"] = clean_curated[:10]
    else:
        fin_cur = [x for x in clean_curated if x.get("topic_stream") == "financial_crime"]
        vio_cur = [x for x in clean_curated if x.get("topic_stream") == "major_violent_crime"]
        interleaved_cur: list[dict[str, Any]] = []
        for i in range(max(len(fin_cur), len(vio_cur))):
            if i < len(fin_cur):
                interleaved_cur.append(fin_cur[i])
            if i < len(vio_cur):
                interleaved_cur.append(vio_cur[i])
        profile["curated_today_candidates"] = interleaved_cur[:12]
    if isinstance(profile.get("editorial_dna"), dict):
        profile["editorial_dna"]["curated_today_candidates"] = [dict(x) for x in profile["curated_today_candidates"]]

    # Update profile replenishment ledger in data/dna_replenished_vault.json
    prof_ledger = dict((vault_data.get("profiles") or {}).get(pid) or {})
    prev_produced_synced = int(prof_ledger.get("last_synced_produced_count") or 0)
    target_replenished = max(produced_count * replenish_per_produced, 52)
    prev_replenished_total = int(prof_ledger.get("replenished_total") or 0)
    newly_replenished_count = max(
        len(newly_topped_up),
        max(0, (produced_count - prev_produced_synced) * replenish_per_produced) if prev_produced_synced > 0 else 0,
    )
    replenished_total = max(prev_replenished_total + newly_replenished_count, min(len(unproduced_vault), target_replenished))

    prof_ledger.update({
        "profile_id": pid,
        "last_synced_produced_count": produced_count,
        "replenished_total": replenished_total,
        "last_newly_replenished_count": newly_replenished_count,
        "total_vault_size": len(merged_vault),
        "available_unproduced_total": len(unproduced_vault),
        "available_by_stream": {
            "financial_crime": fin_available,
            "major_violent_crime": vio_available,
        },
        "curated_active_count": len(profile["curated_today_candidates"]),
        "updated_at": _now(),
    })
    vault_data.setdefault("profiles", {})[pid] = prof_ledger
    try:
        save_dna_replenished_vault(vault_data, vault_path)
    except Exception:
        pass

    return {
        "enabled": True,
        "profile_id": pid,
        "produced_count": produced_count,
        "replenished_total": replenished_total,
        "newly_replenished_count": newly_replenished_count,
        "total_vault_size": len(merged_vault),
        "available_unproduced_total": len(unproduced_vault),
        "available_by_stream": {
            "financial_crime": fin_available,
            "major_violent_crime": vio_available,
        },
        "curated_active_count": len(profile["curated_today_candidates"]),
    }


def _has_real_case_anchor(item: dict[str, Any]) -> bool:
    """
    Reject vague anonymous/fictional tropes, multi-case slash hedging, or mixed-script corruption.
    Require a single documented Chinese case anchor (`case_real_name_zh`) and clean Korean/Vietnamese titles.
    """
    title = str(item.get("title") or "").strip()
    hook = str(item.get("opening_hook") or "").strip()
    # Reject Japanese Hiragana/Katakana contamination (e.g. '1枚の')
    if re.search(r"[\u3040-\u30ff]", f"{title} {hook}"):
        return False
    # Check Korean title portion (before Vietnamese translation in `([`) has zero raw Hanzi/Kanji
    kr_part = title.split("([")[0]
    if re.search(r"[\u4e00-\u9fff]", kr_part):
        return False
    # Check Vietnamese translation portion (if present) has zero stray Hangul
    if "([" in title:
        vi_part = title.split("([", 1)[1]
        if re.search(r"[\uac00-\ud7a3]", vi_part):
            return False

    zh = str(item.get("case_real_name_zh") or "").strip()
    # Reject multi-case slash hedging like "Case A案 / Case B案" (violates 1-case-per-video law)
    if "/" in zh:
        case_segments = [seg for seg in zh.split("/") if ("案" in seg or "事件" in seg)]
        if len(case_segments) >= 2:
            return False
    # Reject anonymous placeholder suspects like '张某' ONLY if there is no specific city/year/institution anchor
    if len(re.findall(r"[\u4e00-\u9fff]", zh)) >= 4:
        return True
    blob = " ".join([
        title,
        str(item.get("winner_cluster") or ""),
        str(item.get("codex_angle") or ""),
        str(item.get("note") or ""),
    ])
    if len(re.findall(r"[\u4e00-\u9fff]", blob)) >= 4:
        return True
    has_pipe_case = "|" in title and bool(re.search(r"\b(19\d\d|20[0-2]\d)\b", blob))
    return has_pipe_case


def build_two_stream_research_prompt(
    *,
    profile: dict[str, Any],
    requested_duration: float | int,
    topic_stream: str,
    produced_titles: list[str],
    suggested_history_titles: list[str],
    live_web_leads: list[dict[str, str]],
    research_round: int = 0,
) -> str:
    stream = normalize_requested_stream(topic_stream)
    seo_dna = profile.get("seo_keyword_dna") or {}
    primary_kw = str(seo_dna.get("primary_title_keyword") or "중국 실화 사건").strip()
    brief = profile.get("default_creative_brief") or {}
    narrative_angle = str(brief.get("narrative_angle") or profile.get("voice_and_structure") or "").strip()
    monetization_policy = str(profile.get("monetization_safety_policy") or "").strip()

    if stream == "financial_crime":
        stream_directive = (
            "CHỈ RESEARCH & ĐỀ XUẤT 8 VỤ ÁN THUỘC **LUỒNG 1 — ĐẠI ÁN TÀI CHÍNH, ĐỘT NHẬP KHO BẠC / MỞ KÉT, CƯỚP TIỀN & ĐÀO TẨU (`financial_crime`)**:\n"
            "- Đại án ngân hàng, chứng khoán, công trái, đột nhập kho bạc, cắt/mở két sắt tinh vi, cướp ngân hàng/xe chở tiền/tiệm vàng/bảo tàng quốc bảo, sổ tiết kiệm bốc hơi, hối phiếu/tín dụng thư giả, lừa đảo/biển thủ siêu ngạch có thật tại Trung Quốc.\n"
            "- Kẻ chủ mưu IQ cao lợi dụng lỗ hổng an ninh/tài chính rồi đào tẩu quốc tế / tẩy trắng thân phận nhiều năm (`猎狐行动 / 经侦大案 / 今日说法 / 天网`)."
        )
    elif stream == "major_violent_crime":
        stream_directive = (
            "CHỈ RESEARCH & ĐỀ XUẤT 8 VỤ ÁN THUỘC **LUỒNG 2 — TRỌNG ÁN ĐẶC BIỆT NGUY HIỂM, ÁN LẠNH PHÁP Y & TRUY NÃ CẤP A (`major_violent_crime`)**:\n"
            "- Trọng án hình sự đặc biệt nguy hiểm có thật tại Trung Quốc (`公安部A级通缉令 / 命案积案 / 天网 / 一线`): mất tích bí ẩn, án lạnh 10–30 năm giải mã bằng pháp y ADN/Y-STR/vi lượng, hung thủ IQ cao xóa dấu vết / phản trinh sát, vỏ bọc hai mặt ẩn mình dưới đời thường & đấu trí tâm lý phòng thẩm vấn.\n"
            "- TUYỆT ĐỐI 0% án tài chính, 0% đột nhập kho bạc/mở két sắt, 0% cướp ngân hàng/xe chở tiền/tiệm vàng/cổ vật (nhóm này đã chuyển 100% sang Luồng 1).\n"
            "- 100% Cách viết Xanh tiền Đài truyền hình (`SBS 그것이 알고 싶다`): Vùng 60s đầu sạch tuyệt đối (`0%` từ tử vong/thi thể/máu/vũ khí) và Khúc xạ pháp y gián tiếp toàn tập (`0%` miêu tả cơ chế bạo lực/thi thể trực diện)."
        )
    else:
        stream_directive = (
            "RESEARCH & ĐỀ XUẤT **10 VỤ ÁN MỚI CHIA ĐỀU 2 LUỒNG CHÍNH CỦA DNA KÊNH (5 LUỒNG 1 + 5 LUỒNG 2)**:\n"
            "1. **5 đề tài `financial_crime` (💰 Luồng 1 — Đại án Tài chính, Kho bạc, Mở két & Cướp tiền Đào tẩu)**: đại án ngân hàng, chứng khoán, công trái, đột nhập kho bạc/mở két sắt, cướp ngân hàng/xe chở tiền/tiệm vàng, lừa đảo/rút ruột siêu ngạch & đào tẩu tẩy trắng thân phận.\n"
            "2. **5 đề tài `major_violent_crime` (🚨 Luồng 2 — Trọng án Hình sự, Án lạnh Pháp y & Truy nã Cấp A)**: trọng án hình sự đặc biệt nguy hiểm, mất tích bí ẩn, lệnh truy nã cấp A, vỏ bọc hai mặt ẩn mình 10–30 năm, pháp y ADN/vi lượng & đấu trí phòng thẩm vấn (0% kho bạc/mở két/cướp tiền, 100% Cách viết Xanh tiền)."
        )

    leads_block = "Không có snippet web đính kèm — hãy chủ động dùng công cụ web search / kho kiến thức điều tra xác thực (CCTV 今日说法, 天网, 一线, 庭审现场, 公安部通缉令, 猎狐行动)."
    if live_web_leads:
        formatted_leads = [
            f"  [{i+1}] ({ld.get('stream_hint')}) {ld.get('title')} — {ld.get('snippet')}"
            for i, ld in enumerate(live_web_leads[:20])
        ]
        leads_block = "\n".join(formatted_leads)

    return (
        f"Bạn là Tổng Biên Tập Điều Tra (Investigative Showrunner) kiêm **Giám Sát Tuân Thủ Chính Sách YouTube & Bảo Vệ Kiếm Tiền YPP (YouTube Policy & YPP Monetization Compliance Officer — Cập nhật 15/07/2025 đến nay)** của kênh phim tài liệu `{profile.get('label')}` "
        f"(Thị trường: {profile.get('market') or 'KR'}, Ngôn ngữ: {profile.get('default_language') or 'ko'}, Thời lượng: {requested_duration} phút, Lượt đào sâu hồ sơ #{research_round + 1}).\n\n"
        f"=== NHIỆM VỤ CỐT LÕI: RESEARCH VỤ ÁN THẬT MỚI 100% (KHÔNG LẶP LẠI ĐỀ TÀI CŨ) ===\n"
        f"{stream_directive}\n\n"
        f"=== ROLE BẮT BUỘC: KIỂM DUYỆT CHÍNH SÁCH YOUTUBE (15/07/2025 – HIỆN TẠI) & CÁCH VIẾT XANH TIỀN 100% TRƯỚC KHI ĐẶT TIÊU ĐỀ / VIẾT NỘI DUNG ===\n"
        "0. **TRƯỚC KHI TẠO BẤT KỲ TIÊU ĐỀ HOẶC NỘI DUNG NÀO, BẮT BUỘC ĐỐI CHIẾU BỘ CHÍNH SÁCH YOUTUBE TỪ 15/07/2025 ĐẾN NAY (`cofi-youtube-policy-monetization-guard`)**:\n"
        "   - **Chính sách YPP 'Inauthentic Content' (15/07/2025 – nay, thay thế 'Repetitious Content')**: CẤM TUYỆT ĐỐI đặt tiêu đề hàng loạt theo một khuôn chữ lặp đi lặp lại (`templated mass-produced titles`); mỗi tiêu đề phải bám sát nghịch lý độc bản, con số thực tế, thời gian lẩn trốn và vỏ bọc riêng của chính vụ án đó.\n"
        "   - **Chính sách Advertiser-Friendly (Chống Vàng Tiền / Limited Ads trên Tiêu đề Công Khai `title` & `topic_anchor`)**: Trên **Tiêu đề YouTube công khai (`title`, `topic_anchor`)** và **Hook 30s đầu (`opening_hook`)**, **CẤM TUYỆT ĐỐI 100% mọi cụm từ máu me / thi thể / vũ khí / hành vi tước đoạt sinh mạng trực diện** (`생명을 앗아간`, `목숨을 앗아간`, `운명을 앗아간`, `살인/살해/사망/시신/사체/백골/피/혈흔/총성/흉기/교살/참극/자살/성폭행/엽기`), NHƯNG **BẮT BUỘC GIỮ NGUYÊN CÁC TỪ KHÓA TƯ PHÁP & HIỆN TRƯỜNG HỢP PHÁP CÓ LỰC HÚT CAO** (`사형수`, `사형 판결`, `무기징역`, `18년 복역수`, `1급 수배범`, `특급 수배범`, `완전 증발`, `밀봉`, `가짜 편지` — tuyệt đối cấm biến tấu sai ngữ pháp thành `'법정 최고형수'`).\n"
        "   - **Công thức Tiêu đề 2 Trụ Cột Chuẩn Winner (`76.1K`, `67.6K`, `48.8K`, `45.7K`, `35.0K`, `29.0K` views) — Rõ Độ Rợn Vụ Án Gốc + Nghịch Lý Vỏ Bọc (`0%` Mơ Hồ Chung Chung, `0%` Dấu `…`, `0%` Spoil Manh Mối Bắt Giữ)**:\n"
        "     * **LUẬT 2 TRỤ CỘT BẮT BUỘC**: `[중국 실화 사건] <1 câu liền mạch kết hợp (1) Rõ Độ Rợn Của Vụ Án Gốc / Sức Nặng Tư Pháp + (2) Nghịch Lý Vỏ Bọc / Hành Động Lạnh Gáy> | <Tên hồ sơ vụ án hoặc Vế đối lập sắc gọn>` (VD chuẩn Winner: `[중국 실화 사건] 대낮 은행 수송차 통째로 탈취한 명문대 주범 | 21년간 타일 나르며 숨어 산 이유`, `[중국 실화 사건] “신고하면 다친다” 집주인 협박 후 16일 만에 돌아온 침대 밑 남자의 정체 | 러안 쩡춘량 사건`, `[중국 실화 사건] 4,000명 수색대가 산을 뒤질 때 지휘부 옆 관공서 에어컨 방에서 잠든 특급 수배범 | 러안 쩡춘량 사건`, `[중국 실화 사건] 완벽한 알리바이를 설계한 북경대 천재 대학생의 1,380일 도주극 | 우셰위 가짜 편지 사건`).\n"
        "     * **CẤM TUYỆT ĐỐI 100%**: (a) CẤM viết mơ hồ chỉ nói chuyện trốn chạy chung chung mà khán giả đọc xong không biết vụ án kinh hoàng ở điểm nào (`10개 성을 돌며 13년간 추적을 피한...`, `산악 마을을 공포에 빠뜨린... 오토바이를 타고 검문소를 노린 이유`, `침입자`, `방범창 없는 3층만 노렸다`); (b) CẤM kiểu câu đứt đoạn dùng dấu `…` hay `...`; (c) CẤM cụm báo cáo công an sáo rỗng (`15,000명 병력 대포위전`, `21개월의 대추격`); (d) CẤM spoil kết cục hoặc manh mối bắt giữ ngay trên tiêu đề (`완벽한 알리바이를 무너뜨린...`, `그를 잡은...`, `...에 잡힌 날`, `최후`).\n"
        "   - **Tách bạch 100% Tiêu đề YouTube Công Khai (`title`) và Hồ sơ Nội bộ (`note`)**: Phần `note` chỉ hiển thị nội bộ trong Popup `📖 Giải thích vụ án` cho người sản xuất chọn bài (không bao giờ đăng lên YouTube), nên `note` BẮT BUỘC mở đầu bằng `📋 【Hồ sơ vụ án: ...】` ghi rõ đây là trọng án gì, bao nhiêu nạn nhân / bao nhiêu tiền và lệnh truy nã cấp A để người dùng biết chính xác tính chất vụ án.\n"
        "1. MỌI ĐỀ TÀI PHẢI LÀ **ĐÚNG 1 VỤ ÁN CÓ THẬT DUY NHẤT TẠI TRUNG QUỐC** (tuyệt đối CẤM dùng dấu `/` ghép 2–3 vụ án khác nhau vào `case_real_name_zh`, và tiêu đề tiếng Hàn + tiếng Việt phải khớp 1-1 với chính tên nghi phạm/địa danh của `case_real_name_zh` đó).\n"
        "2. TUYỆT ĐỐI CẤM bịa chuyện khuyết danh (như '3 chiếc đồng hồ trong phòng kín' không tên tuổi), CẤM để lẫn chữ Hán/chữ Nhật (`の`, `枚`) vào câu tiếng Hàn hoặc chữ Hàn vào bản dịch tiếng Việt, CẤM dùng `[Số đếm] + 해` (`열여덟 해` -> bắt buộc viết `18년`), và CẤM chọn vụ án nhỏ lẻ không có phóng sự truyền hình (`CCTV 今日说法 / 天网 / 一线 / 庭审现场`).\n"
        f"3. Tiêu đề tiếng Hàn bắt buộc mở đầu bằng `[{primary_kw}]` theo cấu trúc 2 trụ cột chuẩn Winner (`<= 76` ký tự tiếng Hàn trước phần dịch tiếng Việt trong ngoặc `(...)`, 1 câu liền mạch không dấu `…` làm rõ độ rợn của vụ án gốc + nghịch lý vỏ bọc/hành vi + `| Tên vụ án`, cho phép từ tư pháp mạnh `사형수/무기징역/18년 복역수/1급 수배범`, `0%` mơ hồ kiểu trốn chạy chung chung, `0%` cụm báo cáo công an `대포위전/대추격`, `0%` spoil manh mối bắt giữ `완벽한 알리바이를 무너뜨린/그를 잡은`, `0%` cụm từ `생명을 앗아간/목숨을 앗아간/운명을 앗아간/đoạt mạng/tước đoạt sinh mạng` và `0%` từ vàng tiền `살인/살해/사망/시신/사체/백골/피/혈흔/총성/흉기/자살/성폭행/엽기`).\n"
        "4. **PHẦN GIẢI THÍCH HỒ SƠ ÁN NỘI BỘ (`note` trong Popup `📖 Giải thích vụ án`) PHẢI CHO BIẾT RÕ LÀ ÁN GÌ ĐỂ NGƯỜI DÙNG CHỌN**: Bắt buộc mở đầu `note` bằng nhãn phân loại `📋 【Hồ sơ vụ án: <loại trọng án/đại án + tước đoạt sinh mạng bao nhiêu nạn nhân hoặc quy mô bao nhiêu tiền + lệnh truy nã cấp A/đỏ hoặc án lạnh bao nhiêu năm>】` rồi giải thích đầy đủ diễn biến vụ án thật.\n"
        "5. **ĐA DẠNG HÓA 8 KIỂU MỞ MÀN LINH HOẠT THEO CHỦ ĐỀ (`8 COLD-OPEN HOOK ARCHETYPES` — CẤM RẬP KHUÔN `[Năm/Thành phố]... 하지만...`)**: Trường `opening_hook` của 8–10 đề tài trong lô BẮT BUỘC xoay vòng linh hoạt theo giải phẫu từng vụ án qua 8 kiểu mở màn chuẩn `그것이 알고 싶다` (`micro_forensic_anomaly`, `double_life_unmasking`, `chilling_verbatim_line`, `countdown_system_breach`, `locked_room_vault_paradox`, `last_ordinary_routine`, `scale_absurdity_collision`, `cold_archive_match`), giữ lực hút tò mò cực đại nhưng `0%` từ vựng tử vong/sinh mạng/máu/thi thể/vũ khí trong câu Hook!\n"
        "6. **LUẬT CẤM ĐỤNG HÀNG BỐI CẢNH / THỦ ĐOẠN LIỀN KỀ (`CROSS-CASE VENUE & MO COOLDOWN >= 10 EPISODES`)**: Tuyệt đối CẤM đề xuất một vụ án có bối cảnh hiện trường, giám định pháp y hoặc cách vây bắt trùng lặp `>= 50%` với 10 video vừa đăng trong Danh sách 1.\n"
        f"7. Góc kể & An toàn Xanh tiền 100%: {narrative_angle} | {monetization_policy}\n\n"
        f"=== TÍN HIỆU KHO TƯ LIỆU MỚI QUÉT TRỰC TIẾP TRÊN WEB (THAM KHẢO & ĐÀO SÂU THÊM) ===\n"
        f"{leads_block}\n\n"
        f"=== DANH SÁCH 1: CÁC VỤ ÁN ĐÃ SẢN XUẤT TRÊN KÊNH (CẤM LẶP LẠI VĨNH VIỄN 100%) ===\n"
        f"{json.dumps(produced_titles[:60], ensure_ascii=False)}\n\n"
        f"=== DANH SÁCH 2: CÁC CHỦ ĐỀ ĐÃ TỪNG GỢI Ý Ở CÁC LƯỢT TRƯỚC (TUYỆT ĐỐI KHÔNG GỢI Ý LẠI!) ===\n"
        f"{json.dumps(suggested_history_titles[:60], ensure_ascii=False)}\n\n"
        "Hãy chủ động tìm kiếm và chọn ra các đại án/trọng án MỚI HOÀN TOÀN chưa xuất hiện trong cả Danh sách 1 lẫn Danh sách 2.\n"
        "Trả về DUY NHẤT 1 JSON hợp lệ (không markdown thừa) theo đúng schema sau:\n"
        '{\n'
        '  "candidates": [\n'
        '    {\n'
        '      "id": "dna_live_01",\n'
        '      "topic_stream": "financial_crime",\n'
        '      "hook_archetype": "locked_room_vault_paradox",\n'
        '      "case_real_name_zh": "Tên vụ án + Tên nghi phạm chữ Hán + Tỉnh/Thành + Năm (VD: 广东开平中行4.85亿美元挪用潜逃案 — 许超凡·许国俊 2001)",\n'
        '      "archival_search_keywords_zh": ["Từ khóa chữ Hán 1 tìm video CCTV/天网", "Từ khóa chữ Hán 2 tìm 庭审"],\n'
        '      "recommended_vox_verbs": ["CRASH_TIMELINE", "LEDGER_DIFF_SCRUB", "GEO_VECTOR_PURSUIT"],\n'
        '      "title": "[중국 실화 사건] 1 câu liền mạch xoáy thẳng vào nghịch lý vỏ bọc / hành động gây sốc (0% dấu …, 0% 대포위전/대추격/그를 잡은, 0% 생명을 앗아간/살인) <= 80 ký tự | Tên vụ án ([Vụ Án Có Thật ở Trung Quốc] Bản dịch tiếng Việt 2 vế sắc gọn 0% dấu … | Tên vụ án)",\n'
        '      "topic_anchor": "[중국 실화 사건] 1 câu liền mạch xoáy thẳng vào nghịch lý vỏ bọc / hành động gây sốc (0% dấu …) <= 80 ký tự | Tên vụ án",\n'
        '      "winner_cluster": "Tên cụm chủ đề + mỏ neo vụ án",\n'
        '      "codex_score": 98,\n'
        '      "codex_angle": "Góc kể 5 Hồi chuẩn Đạo diễn V2",\n'
        '      "codex_reasons": ["Lý do khớp DNA & có >=50% footage thật", "Điểm xoắn cốt truyện giữ chân khán giả"],\n'
        '      "opening_hook": "Lời dẫn Hook mở màn 30s bằng tiếng Hàn tự nhiên, biến thiên theo hook_archetype của riêng vụ án, 100% Xanh tiền (0% từ máu me/tử vong/sinh mạng/vũ khí)",\n'
        '      "note": "📋 【Hồ sơ vụ án: trọng án tước đoạt N sinh mạng / đại án rút ruột kho bạc N tỷ · lệnh truy nã cấp A bộ công an】 Tóm tắt hồ sơ thật tiếng Việt đầy đủ trong Popup nội bộ"\n'
        '    }\n'
        '  ]\n'
        '}'
    )


def research_fresh_topics_for_profile(
    *,
    profile: dict[str, Any],
    requested_duration: float | int,
    topic_stream: str = "all",
    force_refresh: bool = False,
    exclude_titles: list[str] | None = None,
    produced_records: list[dict[str, Any]] | None = None,
    violates_forbidden_fn: Callable[[str], bool] | None = None,
    run_ai_prompt_fn: Callable[[str], dict[str, Any] | None] | None = None,
    ddgs_factory: Callable[[], Any] | None = None,
    vault_path: Path | str | None = None,
) -> dict[str, Any]:
    """
    Execute genuine live two-stream topic discovery with anti-repeat memory & Auto-Replenish DNA Vault.
    Returns:
      {
        "candidates": [...],
        "live_researched_count": int,
        "web_leads_count": int,
        "research_round": int,
        "topic_stream": str,
        "new_history_entries": [...],
        "history_cycle_reset": bool,
        "dna_vault_status": {...},
      }
    """
    stream = normalize_requested_stream(topic_stream)
    locked_stream = str(profile.get("locked_single_stream") or "").strip().lower()
    if locked_stream in {"financial_crime", "major_violent_crime"}:
        stream = locked_stream
    produced_list = list(produced_records or [])
    history_raw = [
        h for h in list(profile.get("suggested_topic_history") or [])
        if isinstance(h, dict)
    ]
    ui_excludes = [
        {"title": str(t).strip(), "topic": str(t).strip()}
        for t in (exclude_titles or [])
        if str(t or "").strip()
    ]

    # Rolling suggestion exclusions (always populated for reserve top-up & force_refresh)
    rolling_exclusions: list[dict[str, Any]] = history_raw[-120:] + ui_excludes
    # Immediate last-batch exclusions used ONLY when rotating a new cycle after all vault items were seen
    immediate_batch_exclusions: list[dict[str, Any]] = (
        ui_excludes[-8:] if ui_excludes else history_raw[-8:]
    )

    all_exclusion_records = produced_list + rolling_exclusions
    produced_titles = [
        f"{r.get('title') or ''} {r.get('case_real_name_zh') or ''}".strip()
        for r in produced_list
        if str(r.get("title") or r.get("topic") or "").strip()
    ]
    suggested_titles = [
        f"{r.get('title') or ''} ({r.get('case_real_name_zh') or ''})".strip()
        for r in rolling_exclusions
        if str(r.get("title") or r.get("case_real_name_zh") or "").strip()
    ]

    research_round = int(profile.get("topic_research_round") or 0)
    web_leads: list[dict[str, str]] = []
    ai_raw_items: list[dict[str, Any]] = []

    if force_refresh or not list(profile.get("curated_today_candidates") or []):
        if run_ai_prompt_fn is not None or ddgs_factory is not None:
            web_leads = harvest_live_case_leads(
                topic_stream=stream,
                research_round=research_round,
                exclusion_records=all_exclusion_records,
                ddgs_factory=ddgs_factory,
            )
        if run_ai_prompt_fn is not None:
            prompt = build_two_stream_research_prompt(
                profile=profile,
                requested_duration=requested_duration,
                topic_stream=stream,
                produced_titles=produced_titles,
                suggested_history_titles=suggested_titles,
                live_web_leads=web_leads,
                research_round=research_round,
            )
            try:
                parsed = run_ai_prompt_fn(prompt)
                if isinstance(parsed, dict) and isinstance(parsed.get("candidates"), list):
                    ai_raw_items = [x for x in parsed["candidates"] if isinstance(x, dict)]
            except Exception:
                ai_raw_items = []
        research_round += 1

    def _accept_candidate(
        raw_item: dict[str, Any],
        accepted_so_far: list[dict[str, Any]],
        *,
        check_rolling_history: bool = True,
        check_recent_only: bool = False,
    ) -> dict[str, Any] | None:
        title_str = str(raw_item.get("title") or raw_item.get("suggested_title") or raw_item.get("topic_anchor") or "").strip()
        if not title_str:
            return None
        enriched = enrich_candidate_stream_metadata(raw_item)
        if stream != "all" and enriched["topic_stream"] != stream:
            return None
        if not _has_real_case_anchor(enriched):
            return None
        full_blob = " ".join([
            title_str,
            str(enriched.get("title_vi") or ""),
            str(enriched.get("case_real_name_zh") or ""),
            str(enriched.get("winner_cluster") or ""),
            str(enriched.get("note") or ""),
        ]).strip()
        if violates_forbidden_fn is not None and violates_forbidden_fn(full_blob):
            return None
        # Hard check: NEVER repeat produced topics (100% permanent ban)
        is_prod_dup, _ = _is_duplicate_against_records(full_blob, produced_list)
        if is_prod_dup:
            return None
        # Rolling check: avoid previously suggested topics in current cycle
        if check_rolling_history:
            if ui_excludes and _is_duplicate_against_records(full_blob, ui_excludes)[0]:
                return None
            if rolling_exclusions and _is_duplicate_against_records(full_blob, rolling_exclusions)[0]:
                return None
        elif check_recent_only and immediate_batch_exclusions:
            # When rotating a new cycle after exhausting the vault, only exclude the immediately preceding batch
            is_rec_dup, _ = _is_duplicate_against_records(full_blob, immediate_batch_exclusions)
            if is_rec_dup:
                return None
        # Self-dedup within current batch
        for prev in accepted_so_far:
            prev_blob = " ".join([
                str(prev.get("title") or ""),
                str(prev.get("case_real_name_zh") or ""),
                str(prev.get("note") or ""),
            ])
            if check_case_similarity(full_blob, str(prev.get("title") or ""), target_topic=prev_blob)[0]:
                return None

        if not enriched.get("id"):
            enriched["id"] = f"dna_{enriched['topic_stream'][:3]}_{uuid4().hex[:6]}"
        enriched["title"] = title_str
        enriched["already_produced"] = False
        return enriched

    accepted: list[dict[str, Any]] = []
    live_researched_count = 0

    # 1. If force_refresh=True, prioritize ONLY brand-new live AI candidates first!
    if force_refresh:
        for item in ai_raw_items:
            cand = _accept_candidate(item, accepted, check_rolling_history=True)
            if cand is not None:
                cand["research_origin"] = "live_ai_web_research"
                accepted.append(cand)
                live_researched_count += 1
    else:
        # Initial load (force_refresh=False): use stored curated candidates if clean & real, else AI/reserve
        for item in ai_raw_items:
            cand = _accept_candidate(item, accepted, check_rolling_history=True)
            if cand is not None:
                cand["research_origin"] = "live_ai_web_research"
                accepted.append(cand)
                live_researched_count += 1
        for stored in list(profile.get("curated_today_candidates") or []):
            if not isinstance(stored, dict):
                continue
            cand = _accept_candidate(stored, accepted, check_rolling_history=False)
            if cand is not None:
                accepted.append(cand)

    # 2. Top up from merged DNA Case Vault (88+ verified cases + dynamic cases)
    #    Pass 1 (strict_hist=True): 100% never-suggested-in-cycle cases.
    #    Pass 2 (strict_hist=False): If the user clicked Research enough times to exhaust all 88+ cases,
    #    automatically start a fresh cycle excluding ONLY produced_list + the immediately preceding batch!
    target_per_stream = 6 if stream == "all" else 8

    def _count_stream(items: list[dict[str, Any]], s_id: str) -> int:
        return sum(1 for x in items if x.get("topic_stream") == s_id)

    needed_streams = ["financial_crime", "major_violent_crime"] if stream == "all" else [stream]
    merged_vault = get_merged_dna_case_vault(vault_path)
    pid_str = str(profile.get("id") or "")
    pid_offset = 18 if "director-v2" in pid_str else (6 if pid_str else 0)
    rot = (research_round * 7 + pid_offset) % max(1, len(merged_vault))
    rotated_reserve = merged_vault[rot:] + merged_vault[:rot]

    history_cycle_reset = False
    for strict_hist in (True, False):
        if all(_count_stream(accepted, s) >= target_per_stream for s in needed_streams):
            break
        # Do NOT recycle history when live AI already gave us a full batch!
        if not strict_hist and live_researched_count >= (6 if stream != "all" else 8):
            break
        if not strict_hist:
            history_cycle_reset = True
        for res_item in rotated_reserve:
            s_id = classify_true_crime_topic_stream(res_item)
            if s_id not in needed_streams:
                continue
            if _count_stream(accepted, s_id) >= target_per_stream:
                continue
            cand = _accept_candidate(
                res_item,
                accepted,
                check_rolling_history=strict_hist,
                check_recent_only=(not strict_hist),
            )
            if cand is not None:
                cand.setdefault("research_origin", "verified_dna_reserve")
                accepted.append(cand)

    # 3. Interleave Stream 1 (`financial_crime`) & Stream 2 (`major_violent_crime`) when viewing `all`
    if stream == "all":
        fin_items = [x for x in accepted if x.get("topic_stream") == "financial_crime"]
        vio_items = [x for x in accepted if x.get("topic_stream") == "major_violent_crime"]
        interleaved: list[dict[str, Any]] = []
        max_len = max(len(fin_items), len(vio_items))
        for i in range(max_len):
            if i < len(fin_items):
                interleaved.append(fin_items[i])
            if i < len(vio_items):
                interleaved.append(vio_items[i])
        final_list = interleaved[:12]
    else:
        final_list = accepted[:10]

    # 4. Sync Auto-Replenish DNA Vault (persist any live AI discoveries + ensure curated candidates are topped up)
    live_ai_discoveries = [x for x in accepted if x.get("research_origin") == "live_ai_web_research"]
    vault_data_cached = load_dna_replenished_vault(vault_path)
    cached_prof_ledger = dict((vault_data_cached.get("profiles") or {}).get(pid_str) or {})
    if (
        not live_ai_discoveries
        and int(cached_prof_ledger.get("available_unproduced_total") or 0) > 0
        and int(cached_prof_ledger.get("last_synced_produced_count") or 0) == len(produced_list)
    ):
        dna_vault_status = {
            "enabled": True,
            "profile_id": pid_str,
            "produced_count": len(produced_list),
            "replenished_total": int(cached_prof_ledger.get("replenished_total") or max(len(produced_list) * 2, 52)),
            "newly_replenished_count": 0,
            "total_vault_size": int(cached_prof_ledger.get("total_vault_size") or len(merged_vault)),
            "available_unproduced_total": int(cached_prof_ledger.get("available_unproduced_total") or 0),
            "available_by_stream": dict(cached_prof_ledger.get("available_by_stream") or {}),
            "curated_active_count": len(final_list),
        }
    else:
        dna_vault_status = auto_replenish_dna_case_vault(
            profile,
            produced_records=produced_list,
            new_dynamic_cases=live_ai_discoveries,
            vault_path=vault_path,
        )

    # 5. Build history entries for newly suggested topics
    stamp = _now()
    new_history_entries: list[dict[str, Any]] = []
    for item in final_list:
        entities, keywords = extract_case_anchors_and_entities(
            str(item.get("title") or ""),
            str(item.get("case_real_name_zh") or ""),
            str(item.get("note") or ""),
        )
        new_history_entries.append({
            "id": str(item.get("id") or f"sug-{uuid4().hex[:8]}"),
            "title": str(item.get("title") or ""),
            "case_real_name_zh": str(item.get("case_real_name_zh") or ""),
            "topic_stream": str(item.get("topic_stream") or ""),
            "tags": entities,
            "anchors": list(dict.fromkeys(entities + keywords)),
            "suggested_at": stamp,
        })

    return {
        "candidates": final_list,
        "live_researched_count": live_researched_count,
        "web_leads_count": len(web_leads),
        "research_round": research_round,
        "topic_stream": stream,
        "streams_summary": {
            "financial_crime": sum(1 for x in final_list if x.get("topic_stream") == "financial_crime"),
            "major_violent_crime": sum(1 for x in final_list if x.get("topic_stream") == "major_violent_crime"),
        },
        "new_history_entries": new_history_entries,
        "history_cycle_reset": history_cycle_reset,
        "dna_vault_status": dna_vault_status,
    }
