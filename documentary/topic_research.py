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
    candidate_id: str = "",
    enforce_mo_cooldown: bool = True,
) -> tuple[bool, str]:
    if not candidate_text.strip() and not candidate_id.strip():
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
        r_cid = str(rec.get("candidate_id") or rec.get("id") or "")
        is_dup, reason, _ = check_case_similarity(
            candidate_text,
            r_title or r_topic,
            target_topic=r_topic,
            target_entities=r_tags,
            target_keywords=r_anchors,
            candidate_id=candidate_id,
            target_candidate_id=r_cid,
        )
        if is_dup:
            return True, reason

    if enforce_mo_cooldown and records and candidate_text.strip():
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
# VERIFIED REAL-CASE RESERVE (52 STREAM 1 FINANCIAL/VAULT/HEIST + 48 STREAM 2 PURE INVESTIGATIVE — 0% ANONYMOUS '某')
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
        "note": "📋 【Hồ sơ vụ án: đại án 3 đời giám đốc rút ruột két sắt ngân hàng 485 triệu USD (6.500 tỷ Won) · truy nã đỏ quốc tế 20 năm】 Hồ sơ thật 100% Đại án Ngân hàng Trung Quốc chi nhánh Khai Bình (广东开平中行案 — Hứa Siêu Phàm 许超凡, Dư Chấn Đông 余振东, Hứa Quốc Tuấn 许国俊, 1993–2021): Lợi dụng kẽ hở sổ sách trước khi nối mạng toàn quốc để rút ruột 485 triệu USD, đánh bạc tại Macau & Las Vegas, kết hôn giả lấy thẻ xanh Mỹ rồi lẩn trốn ở thị trấn nhỏ Wichita (Kansas) trước khi lần lượt bị dẫn độ năm 2004, 2018 và 2021.",
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
        "note": "📋 【Hồ sơ vụ án: đại án 2 thủ quỹ lấy 51 triệu tệ tiền mặt trong hầm két ngân hàng đi mua vé số · lệnh truy nã cấp A bộ công an】 Hồ sơ thật 100% Đại án Két sắt Ngân hàng Nông nghiệp Hàm Đan, Hà Bắc (河北邯郸农行5100万金库大案 — Nhậm Hiểu Phong 任晓峰 & Mã Hướng Cảnh 马向景, 3–4/2007): Ban đầu lấy trộm 200.000 tệ mua vé số trúng nhỏ, sau đó lún sâu rút 51 triệu NDT tiền mặt trong kho bạc mua vé số để mong trúng giải bù lỗ rồi đào tẩu về Liên Vân Cảng & Bắc Kinh trước khi bị bắt giữ.",
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
        "note": "📋 【Hồ sơ vụ án: đại án giám đốc ngân hàng dùng con dấu giả rút ruột hơn 1 tỷ tệ tiền gửi · đào tẩu sang Canada 8 năm】 Hồ sơ thật 100% Đại án Ngân hàng Trung Quốc chi nhánh phố Hà Tùng, Cáp Nhĩ Tân (哈尔滨中行河松街支行案 — Giám đốc Cao Sơn 高山 & anh em Lý Đông Triết 李东哲, 2000–2012): Dùng 'dịch vụ giao sổ đối chiếu tận cửa' bằng con dấu giả để rút ruột hơn 1 tỷ NDT từ hàng chục tập đoàn rồi trốn sang Vancouver (Canada) năm 2004, lộ diện sau một vụ tai nạn giao thông ở Canada và về nước chịu án.",
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
        "note": "📋 【Hồ sơ vụ án: đại án biển thủ 420 triệu tệ công quỹ đánh bạc Macau · phẫu thuật lột da đổi mặt trốn sang Thái Lan 7 năm】 Hồ sơ thật 100% Đại án Trần Mãn Hùng & Trần Thu Viên tại Trung Sơn, Quảng Đông (广东中山4.2亿挪用公款案 — 陈满雄·陈秋园, 1995–2002): Thông đồng cán bộ ngân hàng rút 420 triệu NDT sang Macau đánh bạc, sau đó trốn sang Chiang Mai (Thái Lan), làm phẫu thuật thẩm mỹ xóa nốt ruồi, lột trắng da toàn thân, mua danh tính 'Suthon' làm ông chủ giàu có suốt 7 năm trước khi bị bắt giữ và dẫn độ về Quảng Đông.",
        "hook_archetype": "last_ordinary_routine"
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
        "note": "📋 【Hồ sơ vụ án: đại án thao túng sàn giao dịch công trái 327 bằng 10 triệu lệnh bán khống trong 8 phút cuối · sập công ty chứng khoán số 1】 Hồ sơ thật 100% Sự kiện hợp đồng tương lai công trái mã 327 tại Thượng Hải ngày 23/2/1995 (上海327国债期货事件 — Tổng giám đốc Vạn Quốc Chứng Khoán Quản Kim Sinh 管金生): Đối mặt nguy cơ vỡ nợ 6 tỷ NDT khi Bộ Tài chính nâng lãi bù trượt giá, trong 8 phút cuối (16:22:13–16:30) Quản Kim Sinh tung hơn 10 triệu lô lệnh bán khống không tiền ký quỹ kéo sập giá sàn trước khi Sở Giao dịch tuyên hủy giao dịch 8 phút cuối.",
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
        "note": "📋 【Hồ sơ vụ án: đại án tín dụng ngầm huy động 3,89 tỷ tệ trong 10 tháng mua đứt cả con phố thương mại · vỡ nợ dây chuyền】 Hồ sơ thật 100% Đại án Ngô Anh (吴英, sinh năm 1981) — Tập đoàn Bổn Sắc tại Đông Dương, Chiết Giang (2006–2012): Trong chưa đầy 1 năm huy động 3,89 tỷ NDT từ mạng lưới tín dụng ngầm lãi suất siêu cao để lập 12 công ty và mua cả con phố thương mại nhằm tạo vỏ bọc thanh khoản trước khi đứt gãy chuỗi vốn.",
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
        "note": "📋 【Hồ sơ vụ án: đại án giám đốc kho lương thực quốc gia lập hợp đồng thóc ma rút ruột 700 triệu tệ · truy nã đỏ số 3 trốn 13 năm】 Hồ sơ thật 100% Đại án Kho dự trữ lương thực Trung Trữ Lương chi nhánh Chu Khẩu, Hà Nam (中储粮周口直属库主任乔建军案, 2011): Lập hợp đồng thu mua lương thực khống để rút ruột hơn 700 triệu NDT (chuyển lậu hơn 200 triệu NDT ra nước ngoài) rồi trốn qua Mỹ và Thụy Điển suốt hơn 10 năm trước khi bị dẫn độ.",
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
        "note": "📋 【Hồ sơ vụ án: đại án trưởng phòng tài chính dùng 1 con dấu giả rút ruột 94 triệu tệ ngân sách huyện nghèo · truy nã đỏ số 2 trốn sang Singapore】 Hồ sơ thật 100% Đại án Lý Hoa Ba — Trưởng phòng Kinh tế Xây dựng Cục Tài chính huyện Bà Dương, Giang Tây (江西鄱阳县财政局李华波9400万贪污案, 2006–2015): Dùng con dấu giả và séc thanh toán khống rút 94 triệu NDT quỹ dân sinh chuyển sang Macau đánh bạc và mua thẻ cư trú đầu tư tại Singapore trước khi bị dẫn độ về nước tháng 5/2015.",
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
        "note": "📋 【Hồ sơ vụ án: đại án chủ tịch tập đoàn dược phẩm biển thủ 187 triệu tệ trốn sang New Zealand 15 năm · đốt 50 tỷ Won ở casino trong 82 phút】 Hồ sơ thật 100% Đại án Diêm Vĩnh Minh (闫永明, sinh năm 1971) — cựu Chủ tịch Công ty Dược phẩm Thông Hóa Kim Mã, Cát Lâm (吉林通化金马药业案, 2000–2016): Biển thủ 187 triệu NDT rồi trốn sang Úc và New Zealand dưới tên Lưu Dương (刘阳), nướng hàng trăm triệu đô tại SkyCity Casino trước khi bị phong tỏa 42,85 triệu NZD và dẫn độ về Trung Quốc tháng 11/2016.",
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
        "note": "📋 【Hồ sơ vụ án: đại án phó thị trưởng tham ô 253 triệu tệ · tội phạm truy nã đỏ số 1 dùng hộ chiếu giả trốn qua 6 quốc gia suốt 13 năm】 Hồ sơ thật 100% Đại án Dương Tú Châu (杨秀珠 — cựu Phó thị trưởng Ôn Châu, Chiết Giang, đứng số 1 danh sách 100 Truy nã Đỏ, 2003–2016): Lợi dụng quy hoạch đường sắt và đất đai biển thủ hơn 253 triệu NDT, mua tòa nhà tại Manhattan (New York), chạy trốn qua 6 quốc gia suốt 13 năm trước khi bị bắt vì dùng hộ chiếu Hà Lan giả và về nước chịu án tháng 11/2016.",
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
        "note": "📋 【Hồ sơ vụ án: đại án tổng giám đốc công ty chứng khoán biển thủ 11 triệu tệ trốn 14 năm · chuyên án số 1 chiến dịch Săn Cáo (Liệp Hồ)】 Hồ sơ thật 100% Chuyên án Đới Học Dân (戴学民 — cựu Tổng giám đốc Phòng giao dịch Chứng khoán Thượng Hải thuộc Công ty Tín thác Phát triển Kinh tế Trung Quốc, 2001–2015): Biển thủ 11 triệu NDT trốn sang Belize tháng 8/2001, sau đó làm giả hộ chiếu và CMND mang tên 'Đới Trung Quế' (戴忠桂) lén quay về Hợp Phì & Nam Kinh làm ăn suốt 14 năm trước khi bị bắt ngày 25/4/2015.",
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
        "note": "📋 【Hồ sơ vụ án: đại án buôn lậu & trốn thuế 53 tỷ tệ lớn nhất lịch sử hiện đại · ông trùm Lại Xương Tinh đào tẩu sang Canada 12 năm】 Hồ sơ thật 100% Đại án Tập đoàn Viễn Hoa Hạ Môn, Phúc Kiến (福建厦门远华特大走私案 — Lại Xương Tinh 赖昌星, 1996–2011): Tổ chức đường dây nhập lậu xăng dầu, ô tô, nguyên liệu trị giá 53 tỷ NDT (trốn thuế 30 tỷ NDT), trốn sang Vancouver (Canada) năm 1999 và bị dẫn độ về Bắc Kinh tháng 7/2011, lĩnh án tù chung thân.",
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
        "note": "📋 【Hồ sơ vụ án: đại án siêu lừa đảo tài chính 72 tỷ tệ qua ứng dụng điểm thưởng · ông chủ tự đến đồn công an đầu thú đêm sập sàn】 Hồ sơ thật 100% Đại án Tiền Bảo Võng tại Nam Kinh, Giang Tô (江苏南京钱宝网非法集资案 — Trương Tiểu Lôi 张小雷, 2012–2017): Dùng mô hình nạp tiền ký quỹ lớn để làm nhiệm vụ xem quảng cáo hưởng lãi 40%–60%/năm, thu hút hơn 72 tỷ NDT tiền nạp trước khi vỡ thanh khoản và Trương Tiểu Lôi ra đầu thú ngày 26/12/2017 (lĩnh án 15 năm tù năm 2019).",
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
        "note": "📋 【Hồ sơ vụ án: đại án thao túng sàn giao dịch kim loại hiếm 43 tỷ tệ của 220.000 nhà đầu tư & 3.600 tấn kim loại Indium nằm chết trong kho】 Hồ sơ thật 100% Đại án Sàn giao dịch Kim loại màu Phàn Á tại Côn Minh, Vân Nam (云南昆明泛亚有色金属交易所430亿案 — Đơn Cửu Lương 单九良, 2011–2015): Dùng sản phẩm 'Nhật Kim Bảo' hứa hẹn lãi suất 13,6%/năm thanh toán theo ngày để hút 43 tỷ NDT từ 220.000 người, tự đẩy giá và ôm 3.600 tấn kim loại hiếm Indium trước khi sụp đổ tháng 4/2015 (Đơn Cửu Lương lĩnh án 18 năm tù năm 2019).",
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
        "note": "📋 【Hồ sơ vụ án: đại án cài hệ thống máy chủ ngân hàng giả rút ruột 40 tỷ tệ tiền gửi tại 4 ngân hàng nông thôn · chủ mưu đào tẩu quốc tế】 Hồ sơ thật 100% Đại án 4 Ngân hàng Thôn Trấn Hà Nam (禹州新民生、上蔡惠民、柘城黄淮、开封新东方村镇银行 — Chủ mưu Lữ Dịch 吕奕 & Tập đoàn Tân Tài Phú 河南新财富集团, 4/2022): Thao túng cổ phần ngân hàng và thuê công ty công nghệ lập hệ thống dữ liệu giả mạo để rút ruột 40 tỷ NDT tiền gửi trực tuyến của hơn 400.000 khách hàng.",
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
        "note": "📋 【Hồ sơ vụ án: đại án tài chính đa cấp núp bóng quỹ từ thiện hút 104,6 tỷ tệ từ 5 triệu người chỉ trong 14 tháng】 Hồ sơ thật 100% Đại án Thiện Tâm Hội tại Thâm Quyến (深圳善心汇文化传播有限公司特大传销案 — Trương Thiên Minh 张天明, 5/2016–7/2017): Dưới khẩu hiệu 'Phù bần tế khốn, quân phú cộng sinh', lôi kéo 5,98 triệu người tham gia với tổng số tiền luân chuyển 104,6 tỷ NDT trước khi bị Bộ Công an triệt phá và Tòa án tỉnh Hồ Nam tuyên phạt Trương Thiên Minh 17 năm tù.",
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
        "note": "📋 【Hồ sơ vụ án: đại án đánh tráo 3,9 tỷ tệ hối phiếu trong két sắt ngân hàng thành những xấp báo cũ để mang đi đầu tư chứng khoán】 Hồ sơ thật 100% Đại án 3,915 tỷ NDT tại Ngân hàng Nông nghiệp Trung Quốc chi nhánh Bắc Kinh (北京农行39亿票据大案 — Triệu Lập Quân 赵立军 & Trương Vũ 张宇, 2016): Hai nhân viên quản lý hối phiếu cấu kết với trung gian tài chính ở Trùng Khánh rút ruột toàn bộ hối phiếu thật trong két sắt đem đi chiết khấu lấy tiền炒 cổ phiếu, nhét giấy báo cắt sẵn vào phong bì niêm phong suốt nhiều tháng trước khi thị trường chứng khoán sập làm vỡ lở.",
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
        "note": "📋 【Hồ sơ vụ án: đại án siêu lừa đảo IQ cao chỉ học hết cấp 2 nhưng làm giả 40 thân phận giám đốc tài chính (CFO) cuỗm gần 20 triệu tệ suốt 12 năm】 Hồ sơ thật 100% Chuyên án Chiêm Ân Quý (詹恩贵, Hồ Bắc, 2006–2018): Dù chỉ học hết lớp 8 nhưng tự nghiên cứu luật thuế và nghiệp vụ kế toán sâu đến mức vượt qua các buổi sát hạch tuyển Giám đốc tài chính (CFO) tại Thượng Hải, Nam Kinh, Vũ Hán, Quý Dương, dùng 40 CMND giả để nắm giữ U-Key ngân hàng và cuỗm tổng cộng hơn 19,8 triệu NDT trước khi bị bắt tại Quý Châu.",
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
        "note": "📋 【Hồ sơ vụ án: đại án dựng phòng thẩm định VIP giả ngay trong tòa nhà ngân hàng để lừa 10,1 tỷ tệ bằng chứng chỉ tiền gửi giả】 Hồ sơ thật 100% Đại án Ngân hàng Tề Lỗ tại Tế Nam, Sơn Đông (山东济南齐鲁银行101亿伪造金融票证案 — Lưu Nãi Thắng 刘乃胜, 2008–2010): Khắc 180 con dấu giả, cấu kết nhân viên ngân hàng lập phòng tiếp khách giả ngay trong tòa nhà để đánh tráo giấy xác nhận số dư của hàng chục tập đoàn lớn, rút ruột 10,1 tỷ NDT trước khi lĩnh án tù chung thân.",
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
        "note": "📋 【Hồ sơ vụ án: đại án dùng 1 lô nhôm thỏi trong kho cảng thế chấp trùng lặp 10 lần để rút ruột 16 tỷ tệ vốn vay ngân hàng quốc tế】 Hồ sơ thật 100% Đại án lừa đảo tín dụng kho cảng Thanh Đảo, Sơn Đông (山东青岛港德正资源160亿元重复质押骗贷案 — Trần Cơ Hồng 陈基鸿, 2014): Dùng một lượng nhỏ nhôm và đồng thật xếp thành tường bao quanh khoảng trống, kết hợp làm giả vận đơn kho cảng để thế chấp lặp lại cho 18 ngân hàng trong và ngoài nước, chiếm đoạt hơn 16 tỷ NDT.",
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
        "note": "📋 【Hồ sơ vụ án: đại án nữ giám đốc chi nhánh ngân hàng làm giả hợp đồng đầu tư VIP rút ruột 3 tỷ tệ của 150 khách hàng siêu giàu】 Hồ sơ thật 100% Đại án Ngân hàng Dân Sinh chi nhánh Hàng Thiên Kiều, Bắc Kinh (北京民生银行航天桥支行30亿元假理财案 — Giám đốc chi nhánh Trương Dĩnh 张颖, 2013–2017): Để lấp lỗ hổng tài khoản cá nhân, Trương Dĩnh khắc con dấu giả lập các hợp đồng理财 lãi suất 8,4%/năm lừa hơn 150 khách hàng VIP tại phòng giám đốc, chiếm đoạt hơn 3 tỷ NDT trước khi lĩnh án chung thân.",
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
        "note": "📋 【Hồ sơ vụ án: đại án gia tộc lập 40 công ty vỏ bọc và sổ đỏ giả để rút ruột 32,8 tỷ tệ vốn vay từ ngân hàng địa phương】 Hồ sơ thật 100% Đại án lừa đảo tín dụng 32,8 tỷ NDT tại Ngân hàng Liễu Châu, Quảng Tây (广西柳州银行328亿元骗贷案 — Gia tộc Ngô Đông 吴东, 2010–2014): Lập hơn 40 công ty vỏ bọc, làm giả sổ đỏ và báo cáo thẩm định giá đất tăng gấp hàng chục lần để vay 250 khoản tín dụng tổng cộng 32,895 tỷ NDT.",
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
        "note": "📋 【Hồ sơ vụ án: đại án dùng 13 công ty ma ký hợp đồng thương mại khống rút ruột 7,45 tỷ tệ ngân hàng và kho bạc nhà nước】 Hồ sơ thật 100% Đại án Tập đoàn Hoa Quang tại Nam Hải, Phật Sơn, Quảng Đông (广东佛山南海冯明昌74亿元特大金融案, 1996–2003): Phùng Minh Xương lập 13 công ty con đóng giả đối tác thương mại bảo lãnh chéo lẫn nhau để rút 7,45 tỷ NDT từ ngân hàng và kho bạc địa phương trước khi bị Tổng Kiểm toán Nhà nước phanh phui.",
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
        "note": "📋 【Hồ sơ vụ án: đại án bỏ 2,13 triệu tệ đấu giá bữa trưa với tỷ phú để đánh bóng tên tuổi rồi huy động trái phép 145 tỷ tệ】 Hồ sơ thật 100% Đại án Đoàn Đại Võng tại Đông Quản, Quảng Đông (广东东莞团贷网1450亿元集资诈骗案 — Đường Quân 唐军 & Trương Lâm 张林, 2012–2019): Đường Quân bỏ 2,13 triệu USD đấu giá bữa ăn trưa với Warren Buffett năm 2012 để tạo hào quang uy tín, sau đó phát hành hàng vạn gói tín dụng khống thu hút 145 tỷ NDT trước khi sụp đổ tháng 3/2019 (Đường Quân lĩnh án 20 năm tù năm 2022).",
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
        "note": "📋 【Hồ sơ vụ án: đại án tay không thâu tóm và rút ruột 700 triệu tệ của tập đoàn nước giải khát quốc gia · làm giả hồ sơ lập công để giảm án rồi trốn sang châu Âu】 Hồ sơ thật 100% Đại án Trương Hải tại Tập đoàn Kiện Lực Bảo, Phật Sơn, Quảng Đông (广东健力宝张海职务侵占与假立功外逃案, 2002–2014): Dùng thủ đoạn kế toán rút ruột hơn 700 triệu NDT của Kiện Lực Bảo; sau khi bị tuyên 15 năm tù năm 2007, người tình và luật sư đã làm giả hồ sơ lập công trong tù giúp Trương Hải ra tù sớm năm 2011 rồi dùng hộ chiếu giả trốn sang châu Âu.",
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
        "note": "📋 【Hồ sơ vụ án: đại án thiếu gia tài chính lập 100 quỹ đầu tư ma rút ruột 36,5 tỷ tệ và thao túng giá cổ phiếu · truy bắt xuyên 5 quốc gia】 Hồ sơ thật 100% Đại án Tập đoàn Phụ Hưng tại Thượng Hải (上海阜兴集团365亿元集资诈骗与操纵证券市场案 — Chu Nhất Đống 朱一栋, 2014–2018): Huy động 36,5 tỷ NDT qua 160 quỹ đầu tư tư nhân, dùng hàng trăm tài khoản ẩn danh thao túng cổ phiếu Dalian Insulator trước khi vỡ trận tháng 6/2018; Chu Nhất Đống đào tẩu qua 5 quốc gia với 11 hộ chiếu giả trước khi bị bắt dẫn độ về Thượng Hải và lĩnh án chung thân năm 2021.",
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
        "note": "📋 【Hồ sơ vụ án: đại án tập đoàn hóa dầu tự in 47 tỷ tệ hối phiếu ngân hàng không tiền bảo chứng để vay nợ dây chuyền khắp toàn quốc】 Hồ sơ thật 100% Đại án Tập đoàn Hóa dầu Bảo Tháp tại Ngân Xuyên, Ninh Hạ (宁夏宝塔石化集团470亿元票据诈骗案 — Tôn Hành Siêu 孙珩超, 2015–2018): Lợi dụng giấy phép Công ty Tài chính Tập đoàn để phát hành khống hơn 27.000 hối phiếu điện tử trị giá 47 tỷ NDT không có giao dịch thương mại thật để đảo nợ trước khi sụp đổ năm 2018 (Tôn Hành Siêu lĩnh án chung thân).",
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
        "note": "📋 【Hồ sơ vụ án: đại án làm giả công văn phê duyệt của cơ quan quản lý để biến quỹ tín dụng nhỏ thành 'ngân hàng thương mại' lừa 8 tỷ tệ】 Hồ sơ thật 100% Đại án Tập đoàn Thành Thành tại Thâm Quyến & Cát Lâm (深圳诚成集团刘波80亿元特大金融诈骗案, 2013–2018): Lưu Ba mua lại một hợp tác xã tín dụng nhỏ tại Bạch Sơn (Cát Lâm), làm giả批文 của Ngân监会 cho phép nâng cấp thành Ngân hàng Thương mại Cổ phần, mở văn phòng giả ở Thâm Quyến để hút более 8 tỷ NDT trước khi bị triệt phá.",
        "hook_archetype": "micro_forensic_anomaly"
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
        "note": "📋 【Hồ sơ vụ án: đại án ông chủ nhà máy da Giang Nam mang 120 triệu tệ vốn vay đi đánh bạc quốc tế rồi bốc hơi · tạo sóng chấn động toàn quốc】 Hồ sơ thật 100% Vụ án Hoàng Hà — Chủ tịch Công ty Da Giang Nam Ôn Châu, Chiết Giang (浙江温州江南皮革有限公司黄鹤失踪案, 4/2011): Dù nhà máy làm ăn có lãi hàng chục triệu tệ mỗi năm, Hoàng Hà lại lún sâu vào các sòng bạc quốc tế và vay nợ tín dụng ngầm hơn 120 triệu NDT trước khi rút sạch tiền mặt công ty bỏ trốn tháng 4/2011, châm ngòi cho cuộc khủng hoảng dây chuyền tín dụng Ôn Châu.",
        "hook_archetype": "chilling_verbatim_line"
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
        "note": "📋 【Hồ sơ vụ án: đại án chủ tịch tập đoàn tài chính quốc doanh nhận hối lộ 1,788 tỷ tệ · cất giấu 200 triệu tệ tiền mặt nặng 3 tấn trong căn hộ gọi là 'siêu thị'】 Hồ sơ thật 100% Đại án Lại Tiểu Dân — cựu Chủ tịch Tập đoàn Quản lý Tài sản Hoa Dung Trung Quốc (中国华融赖小民17.88亿元特大金融腐败案, 2008–2018): Lợi dụng quyền phê duyệt các dự án đầu tư tài chính và xử lý nợ xấu để thâu tóm 1,788 tỷ NDT; riêng một căn hộ bí mật tại Bắc Kinh được gọi bằng mật danh 'Siêu thị' cất giấu hơn 200 triệu NDT tiền mặt nguyên đai.",
        "hook_archetype": "micro_forensic_anomaly"
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
        "note": "📋 【Hồ sơ vụ án: đại án đột nhập tiệm vàng & trung tâm thương mại có vũ trang · tước đoạt sinh mạng 2 bảo vệ · án treo số 1 Chiết Giang suốt 22 năm】 Hồ sơ thật 100% 'Án treo số 1 Chiết Giang' (浙江宁波绿洲珠宝行12·6案 & 绍兴供销大厦案 — Hung thủ Từ Lợi 徐利, 1993–2017): Thực hiện 7 vụ đột nhập vũ trang siêu tinh vi không để lại mặt thật, treo thưởng 500.000 NDT suốt 22 năm; năm 2017 thuật toán vân tay thế hệ mới khớp được nửa dấu vân tay mờ năm 1998 ở Gia Hưng, bắt giữ Từ Lợi tại Lâm Hải (Thai Châu) ngày 29/3/2017.",
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
        "title": "[중국 실화 사건] 단 5분 만에 방탄유리를 뚫고 208만 위안을 털어 도심 아파트에 숨어 산 가족 범죄단 | 정저우 12·5 장수하이 사건 ([Vụ Án Có Thật ở Trung Quốc] Phá kính chống đạn cướp 2,08 triệu tệ chỉ trong 5 phút rồi ẩn náu ngay trong chung cư nội đô của băng tội phạm gia đình | Đại án 12·5 Trương Thư Hải Trịnh Châu)",
        "topic_anchor": "[중국 실화 사건] 단 5분 만에 방탄유리를 뚫고 208만 위안을 털어 도심 아파트에 숨어 산 가족 범죄단 | 정저우 12·5 장수하이 사건",
        "winner_cluster": "Luồng 1 · 5 Phút Phá Kính Chống Đạn Cướp 2,08 Triệu Tệ & 9 Tháng Truy Nguyên Kíp Nổ Giữa Nội Đô Trịnh Châu (정저우 12·5 은행 장수하이 사건)",
        "codex_score": 98,
        "profile_score": 98,
        "codex_angle": "Hồ Sơ Thật 100%: Đại Án 12·5 Trịnh Châu — Trương Thư Hải (张书海) Dàn Dựng Tiếng Nổ Đánh Lạc Hướng Vòng Vây Cảnh Sát & Cuộc Truy Lùng Dấu Giày - Chiếc Búa Sắt Suốt 9 Tháng",
        "codex_reasons": [
            "Một trong những chuyên án truy vết vật chứng kinh điển nhất lịch sử hình sự Trung Quốc (phim tài liệu tư liệu gốc công an Hà Nam cực đầy đủ)",
            "Cấu trúc đấu trí chiến thuật giữa kế hoạch thoát thân 3 năm chuẩn bị của Trương Thư Hải và kỹ thuật truy nguyên chiếc búa sắt + đế giày Giải Phóng"
        ],
        "opening_hook": "도심 한복판 은행 창구의 강화유리가 특수 제작된 쇠망치 앞에서 단 5분 만에 무너졌습니다. 경찰 수만 명이 모든 외곽 도로를 봉쇄한 바로 그 밤, 주범 장수하이는 철길 위에서 교란 소음을 일으켜 수사대를 따돌린 뒤 시내 아파트 단지 속으로 연기처럼 스며들었습니다.",
        "note": "📋 【Hồ sơ vụ án: đại án vũ trang đập kính chống đạn ngân hàng cướp 2,08 triệu tệ · đoạt mạng bảo vệ & trọng thương nhân viên · 9 tháng truy nguyên vật chứng】 Hồ sơ thật 100% Đại án 12·5 Ngân hàng Hợp tác Trịnh Châu, Hà Nam (郑州12·5特大银行劫案 — Chủ mưu Trương Thư Hải 张书海, 1999–2000): Lập kế hoạch suốt 3 năm, nổ mìn đường ray đánh lạc hướng cảnh sát để đi bộ ngay về căn hộ trong nội thành ẩn náu suốt 9 tháng trước khi ban chuyên án lần ra nguồn gốc chiếc búa tạ tự hàn và dấu vết thuốc nổ.",
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
        "note": "📋 【Hồ sơ vụ án: đại án cướp xe chở tiền có vũ trang liên hoàn · tước đoạt 21 sinh mạng suốt 12 năm tại Thẩm Dương · ẩn mình dưới vỏ bọc tiểu thương chợ thịt】 Hồ sơ thật 100% Đại án '3·8 Thẩm Dương', Liêu Ninh (沈阳3·8特大系列案件 — Tôn Đức Lâm 孙德林, Uông Gia Lễ 汪家礼, 1987–1999): Ẩn mình dưới vỏ bọc người bán thịt lợn và tài xế tam mã suốt 12 năm, bị Công an Thẩm Dương giải mã nhờ giám định đường khương tuyến đạn đạo và truy vết chiếc xe đạp bỏ lại năm 1999.",
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
        "note": "📋 【Hồ sơ vụ án: đại án kích nổ từ xa tấn công xe chở tiền ngân hàng · tước đoạt 2 sinh mạng, làm bị thương 15 người · 15 ngày truy ngược 1.500 camera tại Vũ Hán】 Hồ sơ thật 100% Chuyên án 12·1 đường Quan Sơn, Vũ Hán, Hồ Bắc (湖北武汉12·1特大爆炸劫案 — Vương Hải Kiếm 王海剑, 12/2011): Thợ sửa chữa điện tử tự nghiên cứu mạch kích nổ từ xa suốt 1 năm để tấn công xe chở tiền nhưng thất bại khi cướp hòm tiền, tháo chạy qua mạng lưới ngõ nhỏ và bị Công an Vũ Hán bắt gọn sau 15 ngày nhờ truy ngược video 1.500 camera kết hợp rà soát chấn thương mắt tại bệnh viện.",
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
        "note": "📋 【Hồ sơ vụ án: đại án cướp ngân hàng có vũ trang 2,08 triệu tệ · kẻ chủ mưu dùng tiền cướp được đầu tư bất động sản thành tỷ phú suốt 16 năm】 Hồ sơ thật 100% Vụ án Thạch Nhị Quần (石二群, Hà Nam, 1999–2015): Ngày 5/12/1999 chủ mưu vụ cướp Ngân hàng Hợp tác Trịnh Châu lấy hơn 2 triệu NDT, sau đó đem phần tiền chia được về Trú Mã Điếm mở công ty xây dựng và bất động sản, tích lũy khối tài sản hàng trăm triệu NDT suốt 16 năm trước khi Công an Trịnh Châu bắt giữ tháng 10/2015.",
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
        "note": "📋 【Hồ sơ vụ án: đại án cướp kho bạc & cắt két sắt ngân hàng đẫm máu xuyên 7 tỉnh · hung thủ độc hành tước đoạt 20 sinh mạng suốt 9 năm · chuyên án bộ công an】 Hồ sơ thật 100% Chuyên án Lôi Quốc Dân (雷国民, An Huy, 1992–2001): Hoạt động độc lập cực kỳ kín tiếng xuyên 7 tỉnh, tự mua bình oxy-axetylen tập cắt các tấm thép dày để đột nhập kho bạc ngân hàng tại Túc Châu (An Huy) và Giang Tây; bị ban chuyên án Bộ Công an khoanh vùng nhờ phân tích kỹ thuật vết cắt kim loại và truy vết phương tiện năm 2001.",
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
        "note": "📋 【Hồ sơ vụ án: đại án băng nhóm ngầm thăm dò và đào trộm hơn 3.000 cổ vật quốc bảo suốt 10 năm · chuyên án 6·03 bộ công an thu hồi 225 quốc bảo cấp 1】 Hồ sơ thật 100% Chuyên án 6·03 tại huyện Văn Hỷ, thành phố Vận Thành, tỉnh Sơn Tây (山西闻喜侯氏兄弟特大盗掘古墓案 — Hầu Kim Lượng 侯金亮, Hầu Kim Phát 侯金发, phá án 2016–2018): Tổ chức băng nhóm độc점 thăm dò và đào trộm khu mộ cổ thời Thương - Chu suốt hơn 10 năm, bị Bộ Công an chỉ đạo chuyên án bắt giữ 475 đối tượng và thu hồi hơn 3.000 cổ vật quý hiếm.",
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
        "note": "📋 【Hồ sơ vụ án: đại án cướp xe chở tiền & kho bạc có vũ trang đặc biệt nguy hiểm · tước đoạt 28 sinh mạng, làm bị thương 22 người xuyên 3 tỉnh · truy nã cấp A số 1 bộ công an】 Hồ sơ thật 100% Đại án 9·1 Thường Đức và chuyên án Trương Quân (张君湘鄂渝系列特大持枪抢劫案, 1991–2000): Sau vụ tấn công xe chở tiền tại Thường Đức (Hồ Nam) ngày 1/9/2000, Bộ Công an huy động lực lượng 3 tỉnh lần theo dấu vết viễn thông và kho vũ khí ngầm, phục kích bắt sống Trương Quân tại Trùng Khánh đêm 19/9/2000.",
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
        "note": "📋 【Hồ sơ vụ án: chuyên án đội trưởng áp tải khống chế xe bọc thép chở 35 triệu tệ lấy 6 triệu tệ rồi suốt 8 giờ đi gửi ATM trả nợ từng người】 Hồ sơ thật 100% Vụ án Lý Tự Nghĩa tại Đại Thạch Kiều, Dinh Khẩu, Liêu Ninh ngày 7/9/2016 (辽宁营口大石桥9·7运钞车劫案 — 李绪义): Do bị chủ đầu tư nợ tiền công trình dẫn đến nợ nần chồng chất, tài xế xe chở tiền Lý Tự Nghĩa đã khống chế xe lấy đi 6 triệu NDT tiền mặt rồi suốt 8 giờ đi gửi tiền vào tài khoản các chủ nợ trước khi bị bắt giữ mà không gây thương vong.",
        "hook_archetype": "locked_room_vault_paradox"
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
        "note": "📋 【Hồ sơ vụ án: đại án trộm bảo tàng lớn nhất lịch sử Trung Quốc · cựu sinh viên cảnh sát dùng vải đỏ che cảm biến hồng ngoại lấy 69 quốc bảo hoàng cung】 Hồ sơ thật 100% Đại án 9·18 tại Bảo tàng Khai Phong, Hà Nam (河南开封博物馆69件馆藏文物被盗案 — Chủ mưu Lưu Nông Quân 刘农军, 1992–1993): Từng theo học Học viện Cảnh sát Nhân dân Vũ Hán nên nắm rõ nguyên lý bước sóng hồng ngoại, Lưu Nông Quân dùng vải nhung đỏ che cảm biến lấy đi 69 quốc bảo nhà Minh - Thanh; Ban chuyên án đã truy vết từ mảnh tem nhãn và chiếc xe桑塔纳 trắng, thu hồi toàn bộ 69 quốc bảo tại Macau & Vũ Hán.",
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
        "note": "📋 【Hồ sơ vụ án: đại án cướp xe chở tiền ngân hàng đặc biệt nguy hiểm · tước đoạt 5 sinh mạng (4 nhân viên giải ngân & 1 cảnh sát hình sự) · lệnh truy nã cấp A bộ công an】 Hồ sơ thật 100% Chuyên án 9·29 tại Tiềm Giang, Hồ Bắc (湖北潜江9·29大案 — Tạ Tiên Vinh 谢先荣, 9–10/2003): Hung thủ bỏ lại chiếc xe tải nhỏ đã đục xóa toàn bộ số khung số máy; chuyên gia kỹ thuật hình sự dùng phương pháp ăn mòn điện hóa phục hồi dãy số gốc, xác định danh tính Tạ Tiên Vinh và phát lệnh truy nã cấp A toàn quốc, vây bắt trên sông Hán Giang sau 15 ngày.",
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
        "note": "📋 【Hồ sơ vụ án: trọng án tấn công xe chở tiền đoạt mạng người & cướp 790.000 tệ · thủ phạm ẩn mình làm phó cục trưởng cục thi hành án tòa án suốt 22 năm】 Hồ sơ thật 100% Kỳ án cướp xe chở tiền năm 1997 tại thành phố Tân Tập, Thạch Gia Trang, Hà Bắc (河北辛集1997年12·2运钞车劫案 — Chủ mưu Triệu Trí Dũng 赵志勇, phá án tháng 8/2019): Triệu Trí Dũng vốn là nhân viên tòa án đã rủ đồng bọn cướp 790.000 NDT của xe chở tiền rồi tiếp tục đi làm bình thường, leo lên chức Phó cục trưởng Cục Thi hành án Tòa án suốt 22 năm trước khi công nghệ giám định sinh trắc học mới lật tẩy toàn bộ băng nhóm.",
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
        "note": "📋 【Hồ sơ vụ án: đại án đột nhập Tử Cấm Thành (Cố Cung) vượt 4 lớp bảo vệ lấy cắp 9 báu vật hoàng cung · 58 giờ truy bắt từ dấu vân tay quán net】 Hồ sơ thật 100% Chuyên án 58 giờ phá vụ trộm 9 báu vật tại Bảo tàng Cố Cung (Tử Cấm Thành), Bắc Kinh ngày 8/5/2011 (北京故宫博物院5·8被盗案 — Thạch Bách Khuê 石柏魁): Lợi dụng lúc mưa to để trốn lại trong hốc tường Cố Cung sau giờ đóng cửa, ngắt nguồn điện phòng trưng bày lấy đi 9 hộp báu vật dát vàng nạm ngọc rồi trèo mái trốn thoát; Công an Bắc Kinh khoanh vùng dấu vết và bắt giữ Thạch Bách Khuê tại một quán Internet sau 58 giờ.",
        "hook_archetype": "countdown_system_breach"
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
        "note": "📋 【Hồ sơ vụ án: trọng án tước đoạt 3 sinh mạng tại Đại Khánh · truy nã đặc biệt bộ công an · giả làm trụ trì chùa cổ 16 năm】 Hồ sơ thật 100% Vụ án Trương Lập Vĩ (张立伟, pháp danh Thích Quảng Văn 释广闻, 2000–2017): Sau trọng án năm 2000 tại Đại Khánh (Hắc Long Giang), Trương Lập Vĩ trốn hơn 2.000km xuống An Huy, mua hộ khẩu giả tên Tôn Hồng Đào (孙洪涛) và từng bước leo lên làm Trụ trì chùa Long Hưng (Phượng Dương, An Huy) suốt 16 năm trước khi Công an Đại Khánh đối sánh ảnh sinh trắc học bắt giữ tháng 8/2017.",
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
        "note": "📋 【Hồ sơ vụ án: đại án liên hoàn tước đoạt sinh mạng hơn 20 người (gồm cả 2 cán bộ kiểm sát) · đội trưởng hình sự hai mặt suốt 8 năm】 Hồ sơ thật 100% Đại án Tưởng Anh Khôi tại thành phố Triệu Đông, tỉnh Hắc Long Giang (黑龙江肇东蒋英库特大团伙案, 1993–2001): Lợi dụng vỏ bọc công chức hình sự để vay tiền lớn rồi thủ tiêu chủ nợ suốt 8 năm; tháng 12/2000 việc 2 cán bộ viện kiểm sát mất tích tại Triệu Đông kích hoạt chuyên án mật cấp tỉnh lật tẩy toàn bộ đường dây.",
        "hook_archetype": "double_life_unmasking"
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
        "note": "📋 【Hồ sơ vụ án: đại án đặc biệt nguy hiểm tước đoạt sinh mạng hàng chục hộ dân · lệnh truy nã cấp A số 1 bộ công an · 168 giờ đại truy kích】 Hồ sơ thật 100% Chiến dịch 168 giờ đại truy bắt Cận Như Siêu (石家庄3·16案全国大追捕 — 靳如超, 16–23/3/2001): Khắc họa góc nhìn Ban Chuyên Án Bộ Công an (100% Cắt cảnh Sau Cơn Bão, không mô tả thương vong trực diện) truy lùng lộ trình đào tẩu xuyên 6 tỉnh suốt 7 ngày đêm cho đến khi bắt sống nghi phạm tại Bắc Hải (Quảng Tây) nhờ tin báo quần chúng.",
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
        "note": "📋 【Hồ sơ vụ án: trọng án liên hoàn tước đoạt 7 sinh mạng · lệnh truy nã cấp A bộ công an · ẩn mình lái taxi ở Tam Á suốt 8 năm】 Hồ sơ thật 100% Chuyên án truy nã cấp A Mã Hán Khánh (马汉庆, Vũ Hán, 1996–2004): Sau vụ cướp trước cổng Nhà máy Hóa chất Hữu cơ Vũ Hán tháng 1/1996 và các vụ án tại Tân Cương, Mã Hán Khánh dùng CMND giả tên 'Châu Quân' (周军) trốn xuống thành phố Tam Á (Hải Nam) mua xe chạy taxi và lập gia đình suốt 8 năm trước khi bị bắt ngày 11/11/2004.",
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
        "note": "📋 【Hồ sơ vụ án: trọng án liên hoàn tước đoạt sinh mạng 2 nữ tài xế taxi · án lạnh 28 năm minh oan và bắt hung thủ thật bằng ADN đầu lọc thuốc lá】 Hồ sơ thật 100% Kỳ án hai tài xế taxi tại Tiêu Sơn, Hàng Châu năm 1995 (浙江萧山1995年命案积案 — Hạng Sinh Nguyên 项生源): Nhờ bảo quản nghiêm ngặt đầu lọc thuốc lá và dấu vân tay tại hiện trường năm 1995, cơ quan giám định pháp y Chiết Giang đã xác định được hung thủ thật Hạng Sinh Nguyên, khép lại kỳ án kéo dài gần 3 thập kỷ.",
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
        "note": "📋 【Hồ sơ vụ án: đại án đột nhập ban đêm tước đoạt 6 sinh mạng xuyên 6 tỉnh · lệnh truy nã cấp A bộ công an · phản trinh sát ngủ rừng】 Hồ sơ thật 100% Chuyên án truy nã cấp A Đổng Văn Ngữ (董文语, 3–11/2006): Để né tránh toàn bộ hệ thống kiểm tra giấy tờ và camera tại nhà ga/khách sạn, Đổng Văn Ngữ chỉ di chuyển ban đêm dọc đường sắt và ngủ trong rừng núi xuyên 6 tỉnh (Chiết Giang, Phúc Kiến, Giang Tây, Hồ Nam, Quảng Tây, Tứ Xuyên) trước khi bị bắt tại núi Tượng Tỵ, Nghi Tân (Tứ Xuyên) ngày 16/11/2006.",
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
        "note": "📋 【Hồ sơ vụ án: trọng án liên hoàn tước đoạt sinh mạng 10 phụ nữ · hung thủ thật Triệu Chí Hồng tự thú trong trại giam & đại án minh oan 18 năm】 Hồ sơ thật 100% Kỳ án Hô Cách Cát Lặc Đồ và chân tướng hung thủ Triệu Chí Hồng tại Hô Hòa Hạo Đặc, Nội Mông (内蒙古呼格吉勒图冤案平反与赵志红案, 1996–2014): Năm 2005 khi bị bắt, Triệu Chí Hồng khai nhận chính hắn mới là thủ phạm vụ án ngày 9/4/1996 và viết 'Đơn xin đền mạng' từ trong trại giam, dẫn tới phiên tòa tái thẩm lịch sử ngày 15/12/2014 minh oan hoàn toàn cho Hô Cách Cát Lặc Đồ.",
        "hook_archetype": "cold_archive_match"
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
        "note": "📋 【Hồ sơ vụ án: trọng án tước đoạt sinh mạng 1 nạn nhân tại Cát Lâm · trốn nã 13 năm làm MC và bị bắt vì lên sóng truyền hình hẹn hò】 Hồ sơ thật 100% Vụ án Ngô Cương tại thành phố Cát Lâm (吉林命案逃犯吴刚上相亲节目落网案, 1998–2011): Sau trọng án năm 1998 tại Cát Lâm, Ngô Cương trốn xuống Thẩm Dương đổi tên thành 'Lưu Hạo' (刘浩), làm MC sự kiện suốt 13 năm; tháng 11/2010 hắn tự tin đăng ký tham gia chương trình hẹn hò trên truyền hình vệ tinh Hắc Long Giang và bị người quen cũ nhận diện báo Công an Cát Lâm bắt giữ tháng 6/2011.",
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
        "note": "📋 【Hồ sơ vụ án: trọng án đoạt mạng quản giáo trực ban để vượt ngục · lệnh truy nã cấp A bộ công an · 15.000 quân cảnh vây bắt 9 ngày đêm】 Hồ sơ thật 100% Chuyên án truy bắt 3 phạm nhân vượt trại tạm giam huyện Diên Thọ, Cáp Nhĩ Tân, Hắc Long Giang (黑龙江延寿9·2越狱案 — 高玉伦·王大民·李海伟, 2–11/9/2014): Bộ Công an và Công an Hắc Long Giang huy động 15.000 cảnh sát và trực thăng khép vòng vây suốt 9 ngày đêm, lần lượt bắt gọn cả 3 đối tượng.",
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
        "note": "📋 【Hồ sơ vụ án: trọng án đoạt mạng người & điều chế 12 tấn tinh thể độc hại lớn nhất thế giới · lệnh truy nã cấp A số 1 bộ công an · trốn 9 năm】 Hồ sơ thật 100% Chuyên án truy nã cấp A Lưu Chiêu Hoa (刘招华, 1996–2005): Nổi tiếng với tâm lý phản trinh sát cực đoan — đạp xe đạp vượt vòng vây tại Quảng Đông năm 1999, đổi tên thành 'Lý Sâm Thanh' (李森青) đến Quế Lâm (Quảng Tây) mở công ty lâm nghiệp sinh thái 300 triệu tệ suốt 9 năm trước khi bị bắt trong chiến dịch 'Tróc Mộc Điểu' đúng ngày sinh nhật 5/3/2005.",
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
        "note": "📋 【Hồ sơ vụ án: đại án tập đoàn ngầm tước đoạt 9 sinh mạng & che giấu em trai truy nã cấp A · chuyên án 1·10 bộ công an Trung Quốc】 Hồ sơ thật 100% Chuyên án 1·10 của Bộ Công an đối với Tập đoàn Hán Long tại Tứ Xuyên (四川汉龙集团刘汉·刘维特大专案, 2013–2015): Dưới vỏ bọc tỷ phú khoáng sản và thủy điện sở hữu 40 tỷ NDT, Lưu Hán thao túng ngầm địa phương và che giấu em trai Lưu Duy đang bị Bộ Công an truy nã cấp A suốt 4 năm trước khi bị bắt tại Bắc Kinh và xét xử tại Tòa án Hàm Ninh (Hồ Bắc).",
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
        "note": "📋 【Hồ sơ vụ án: trọng án liên hoàn tước đoạt 4 sinh mạng (2 doanh nhân & 2 cảnh sát giao thông) · lệnh truy nã cấp A bộ công an · 80 giờ truy kích】 Hồ sơ thật 100% Chuyên án 80 giờ truy bắt kẻ truy nã cấp A Hồ Ích Hoa xuyên Chiết Giang - Quảng Đông - Phúc Kiến (粤闽跨省追捕胡益华案, 7/2010): Sau vụ án tại trạm dừng nghỉ cao tốc Huệ Lai (Quảng Đông) đêm 5/7/2010, Bộ Công an phát lệnh truy nã cấp A; chỉ sau 80 giờ truy vết tín hiệu thẻ ngân hàng và camera giao thông, lực lượng đặc nhiệm đã bắt sống Hồ Ích Hoa tại Hạ Môn (Phúc Kiến) ngày 8/7/2010.",
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
        "note": "📋 【Hồ sơ vụ án: trọng án liên hoàn tước đoạt 3 sinh mạng tại Giang Tây · truy nã đặc biệt nguy hiểm · 4.000 quân cảnh và drone tầm nhiệt vây bắt 8 ngày】 Hồ sơ thật 100% Chiến dịch 8 ngày đêm truy bắt Tăng Xuân Lượng tại huyện Lạc An, Phủ Châu, Giang Tây (江西乐安曾春亮大搜捕案, 8–16/8/2020): Công an tỉnh Giang Tây huy động hơn 4.000 cảnh sát, chó nghiệp vụ và drone tầm nhiệt thiết lập 3 vòng vây đồng tâm quanh khu vực rừng núi Lạc An, bắt sống Tăng Xuân Lượng khi hắn tìm cách phóng xe máy vượt chốt ngày 16/8/2020.",
        "hook_archetype": "double_life_unmasking"
    },
    {
        "id": "fin_cn_shantou_807_vat_323b_chenshaofeng",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "广东汕头8·07共和国第一税案虚开323亿元增值税发票案 — 陈少峰·林贞木 (1999–2001)",
        "archival_search_keywords_zh": [
            "汕头 807大案 虚开增值税发票 今日说法",
            "共和国第一税案 陈少峰 林贞木 纪实",
            "汕头 323亿 骗税大案 审判"
        ],
        "recommended_vox_verbs": [
            "LEDGER_DIFF_SCRUB",
            "SCALE_MULTIPLICATION",
            "NETWORK_GRAPH"
        ],
        "title": "[중국 실화 사건] 유령 회사 1,100개로 323억 위안 세금계산서를 찍어내 국고를 털어낸 도시 카르텔 | 산터우 8·07 세금 대사건 ([Vụ Án Có Thật ở Trung Quốc] Lập 1.100 công ty ma in 32,3 tỷ tệ hóa đơn khống rút ruột ngân sách quốc gia của tập đoàn ngầm | Đại án thuế 8·07 Sán Đầu)",
        "topic_anchor": "[중국 실화 사건] 유령 회사 1,100개로 323억 위안 세금계산서를 찍어내 국고를 털어낸 도시 카르텔 | 산터우 8·07 세금 대사건",
        "winner_cluster": "Luồng 1 · 1.100 Công Ty Ma In 32,3 Tỷ Tệ Hóa Đơn Khống & Cuộc Đột Kích Của Đoàn Đặc Phái Trung Ương (광둥 산터우 8·07 제1호 세금 대사건)",
        "codex_score": 99,
        "profile_score": 99,
        "codex_angle": "Hồ Sơ Thật 100%: Đại Án 8·07 Sán Đầu (陈少峰·林贞木, 1999–2001) — Đệ Nhất Án Thuế Vụ Lịch Sử Trung Quốc Với 32,3 Tỷ NDT Hóa Đơn Khống Và Màn Đấu Trí Bảo Vệ Kho Sổ Cái Mật",
        "codex_reasons": [
            "Đại án kinh tế lớn nhất lịch sử thuế vụ Trung Quốc (共和国第一税案), Thủ tướng trực tiếp chỉ đạo điều tra và Tòa án Sán Đầu tuyên án tử hình 30 bị cáo cầm đầu",
            "Cực hợp LEDGER_DIFF_SCRUB & SCALE_MULTIPLICATION trên bàn biên tập cắt dán Vox"
        ],
        "opening_hook": "공장 기계는 단 한 대도 돌아가지 않는데, 서류상으로는 매달 수십억 위안어치의 전자제품과 원단이 해외로 수출되고 있었습니다. 유령 회사 일천백 곳이 서로 가짜 영수증을 주고받으며 국고에서 사십이억 위안의 환급금을 빨아들인 전대미문의 세금 카르텔을 추적합니다.",
        "note": "📋 【Hồ sơ vụ án: đệ nhất đại án thuế vụ Trung Quốc xuất khống 32,3 tỷ tệ hóa đơn GTGT rút ruột 4,2 tỷ tệ ngân sách · phóng hỏa nhà khách đoàn thanh tra trung ương · tuyên án tử hình Trần Thiếu Phong, Lâm Trinh Mộc】 Hồ sơ thật 100% Chuyên án 8·07 tại Sán Đầu, Quảng Đông (广东潮阳·普宁8·07虚开增值税专用发票案 — Trần Thiếu Phong 陈少峰, Lâm Trinh Mộc 林贞木, 1999–2001): Hơn 1.100 công ty ma cấu kết in khống 32,3 tỷ NDT hóa đơn GTGT rút ruột 4,2 tỷ NDT tiền hoàn thuế và thậm chí phóng hỏa Nhà khách Nghênh Tân (7·15迎宾馆纵火案) nhằm tiêu hủy hồ sơ thanh tra; Tòa án Nhân dân Trung cấp Sán Đầu và Tòa án Tối cao đã xét xử, tuyên án tử hình 30 đối tượng cầm đầu.",
        "hook_archetype": "scale_absurdity_collision"
    },
    {
        "id": "fin_cn_xian_tang_consort_27ton_sarcophagus_yangbin",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "陕西西安唐贞顺皇后武惠妃敬陵27吨石椁跨国盗卖与追索大案 — 杨彬 (2004–2011)",
        "archival_search_keywords_zh": [
            "武惠妃石椁 杨彬 盗墓 今日说法",
            "唐贞顺皇后 27吨石椁 追索 天网",
            "西安 敬陵 国宝被盗 审判"
        ],
        "recommended_vox_verbs": [
            "FORENSIC_ZOOM_CHAIN",
            "GEO_VECTOR_PURSUIT",
            "SINGLE_EVIDENCE_AUTOPSY"
        ],
        "title": "[중국 실화 사건] 지하 궁전에서 27톤 황실 국보 석관을 통째로 해체해 해외로 빼돌린 도굴왕의 행적 | 시안 양빈 국보 도굴 사건 ([Vụ Án Có Thật ở Trung Quốc] Tháo rời nguyên cỗ quách đá hoàng hậu nặng 27 tấn dưới lòng đất rồi tuồn ra nước ngoài của trùm đạo mộ | Đại án Dương Bân Tây An)",
        "topic_anchor": "[중국 실화 사건] 지하 궁전에서 27톤 황실 국보 석관을 통째로 해체해 해외로 빼돌린 도굴왕의 행적 | 시안 양빈 국보 도굴 사건",
        "winner_cluster": "Luồng 1 · 31 Tấm Đá Chạm Khắc Nặng 27 Tấn Bốc Hơi Khỏi Lăng Mộ Hoàng Gia & Chiếc Thẻ Nhớ SD Mở Khóa Đại Án (시안 27톤 황후 석관 도굴 사건)",
        "codex_score": 98,
        "profile_score": 98,
        "codex_angle": "Hồ Sơ Thật 100%: Dương Bân & Đại Án Đánh Cắp Quách Đá Võ Huệ Phi Nặng 27 Tấn Tại Tây An (2004–2011) — Cuộc Truy Vết Xuyên Thái Bình Dương Thu Hồi Quốc Bảo Cấp 1",
        "codex_reasons": [
            "Vụ buôn lậu quốc bảo nặng nhất lịch sử khảo cổ Trung Quốc (27 tấn đá cẩm thạch chạm khắc thời Đường), có phim tài liệu đặc biệt trên CCTV 今日说法 / 国宝档案",
            "Tòa án Nhân dân Trung cấp Tây An tuyên án tử hình treo/chung thân đối với Dương Bân và thu hồi quốc bảo về bảo tàng"
        ],
        "opening_hook": "무게가 무려 이십칠 톤에 달하는 당나라 황실의 거대한 채색 석관이 지하 십오 미터 무덤 속에서 감쪽같이 사라졌습니다. 도굴단 두목 양빈은 어떻게 건물 한 채 크기의 국보를 서른한 조각으로 분해해 국경 세관까지 통과시켰던 것일까요.",
        "note": "📋 【Hồ sơ vụ án: đại án đào trộm lăng Kính Lăng của Võ Huệ Phi đời Đường · tháo rời cỗ quách đá quốc bảo cấp 1 nặng 27 tấn bán sang Mỹ giá 1 triệu USD · Tòa án Tây An tuyên án chung thân Dương Bân】 Hồ sơ thật 100% Đại án trộm cắp và buôn lậu Quách đá Võ Huệ Phi (唐贞顺皇后武惠妃石椁案 — Chủ mưu Dương Bân 杨彬, 2004–2011): Dương Bân chỉ đạo đồng bọn đào hầm suốt 2 năm vào lăng mộ hoàng gia ở Tây An, tháo rời cỗ quách đá 27 tấn thành 31 khối tuồn qua cảng Hồng Kông bán ra nước ngoài; Công an Tây An khôi phục ảnh chụp từ chiếc thẻ nhớ SD thu giữ tại sào huyệt, bắt giữ Dương Bân tuyên án chung thân và thu hồi nguyên vẹn quốc bảo năm 2010.",
        "hook_archetype": "locked_room_vault_paradox"
    },
    {
        "id": "fin_cn_meishan_jiangkou_sunken_silver_wangmin",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "四川眉山彭山区江口明末张献忠沉银遗址特大夜潜盗掘国宝案 — 王敏·宋先杰 (2014–2017)",
        "archival_search_keywords_zh": [
            "江口沉银 虎钮永昌大元帅金印 今日说法",
            "四川眉山 盗掘沉银 王敏 宋先杰 央视",
            "张献忠 沉银 特大文物案 庭审"
        ],
        "recommended_vox_verbs": [
            "SINGLE_EVIDENCE_AUTOPSY",
            "NETWORK_GRAPH",
            "GEO_VECTOR_PURSUIT"
        ],
        "title": "[중국 실화 사건] 밤마다 잠수복 입고 강물 바닥에서 1,000억 대 황금 국보 직인을 건져 올린 비밀 도굴단 | 쓰촨 장커우 침은 사건 ([Vụ Án Có Thật ở Trung Quốc] Đêm đêm mặc đồ lặn xuống đáy sông trục vớt ấn vàng quốc bảo 100 triệu tệ của băng đạo mộ ngầm | Đại án kho báu Giang Khẩu Tứ Xuyên)",
        "topic_anchor": "[중국 실화 사건] 밤마다 잠수복 입고 강물 바닥에서 1,000억 대 황금 국보 직인을 건져 올린 비밀 도굴단 | 쓰촨 장커우 침은 사건",
        "winner_cluster": "Luồng 1 · Thợ Lặn Đêm Trục Vớt Kho Bạc Đáy Sông Dân Giang & Ấn Vàng Nguyên Soái 100 Triệu Tệ (쓰촨 메이산 강바닥 황금 국보 사건)",
        "codex_score": 98,
        "profile_score": 98,
        "codex_angle": "Hồ Sơ Thật 100%: Vương Mẫn · Tống Tiên Kiệt & Chuyên Án Kho Báu Đáy Sông Giang Khẩu, Tứ Xuyên (2014–2017) — Truy Vết Chiếc Ấn Vàng 50 Lạng Từ Lời Đồn Chợ Đồ Cổ",
        "codex_reasons": [
            "Chuyên án văn vật cấp A do Bộ Công an Trung Quốc trực tiếp chỉ đạo (thu hồi hơn 1.000 cổ vật vàng bạc trị giá 300 triệu NDT), lên sóng nhiều tập trên CCTV 今日说法",
            "Tòa án Nhân dân tỉnh Tứ Xuyên xét xử công khai 70 bị cáo, tuyên phạt Vương Mẫn và Tống Tiên Kiệt 14–15 năm tù"
        ],
        "opening_hook": "삼백 년 동안 전설로만 전해지던 강바닥의 보물선이 사실이었다는 것이 밝혀진 순간, 고요하던 강변 마을의 밤이 바뀌었습니다. 산소통과 수중 금속탐지기를 멘 잠수부들이 검은 강물 속으로 사라지더니, 시가 일억 위안짜리 순금 원수 직인이 암시장에 등장했습니다.",
        "note": "📋 【Hồ sơ vụ án: đại án lặn đêm trục vớt kho báu đáy sông Giang Khẩu trị giá 300 triệu tệ (gồm ấn vàng quốc bảo cấp 1 nặng 50 lạng) · Bộ Công an bắt 70 đối tượng, tuyên án Vương Mẫn & Tống Tiên Kiệt】 Hồ sơ thật 100% Đại án trục vớt trái phép di chỉ kho bạc chìm Giang Khẩu tại Mi Sơn, Tứ Xuyên (四川眉山5·1特大盗掘倒卖文物案 — Vương Mẫn 王敏, Tống Tiên Kiệt 宋先杰, 2014–2017): Nhóm thủ phạm sắm thiết bị lặn chuyên nghiệp và máy dò kim loại dưới nước, lặn đêm vớt ấn vàng 'Hổ Nữu Vĩnh Xương Đại Nguyên Soái Kim Ấn' cùng hàng trăm thỏi bạc thời Minh bán ra chợ đen; Công an Tứ Xuyên bắt giữ 70 đối tượng, thu hồi toàn bộ quốc bảo và tòa tuyên án nghiêm khắc.",
        "hook_archetype": "micro_forensic_anomaly"
    },
    {
        "id": "fin_cn_shenyang_118_armored_van_zhangxianguang",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "辽宁沈阳1·18商业银行运钞车210万元劫案与公安部A级通缉跨省追缉案 — 张显光·张显明·张显辉 (2000–2006)",
        "archival_search_keywords_zh": [
            "沈阳 1·18大案 张显光 今日说法",
            "A级通缉犯 张显光 运钞车 天网",
            "张显光 庭审 死刑 纪实"
        ],
        "recommended_vox_verbs": [
            "CRASH_TIMELINE",
            "GEO_VECTOR_PURSUIT",
            "FORENSIC_ZOOM_CHAIN"
        ],
        "title": "[중국 실화 사건] 은행 앞 자전거 짐받이에 원격 장치를 숨겨 현금수송차 210만 위안을 탈취한 3형제 주범 | 선양 장셴광 사건 ([Vụ Án Có Thật ở Trung Quốc] Giấu thiết bị kích hoạt từ xa trên gác-ba-ga xe đạp trước cổng ngân hàng cướp 2,1 triệu tệ xe chở tiền của 3 anh em | Đại án Trương Hiển Quang)",
        "topic_anchor": "[중국 실화 사건] 은행 앞 자전거 짐받이에 원격 장치를 숨겨 현금수송차 210만 위안을 탈취한 3형제 주범 | 선양 장셴광 사건",
        "winner_cluster": "Luồng 1 · Chiếc Xe Đạp Dựng Trước Ngân Hàng Lúc 17h50 & 3 Năm Truy Bắt Tội Phạm Cấp A Trương Hiển Quang (선양 1·18 현금수송차 장셴광 사건)",
        "codex_score": 98,
        "profile_score": 98,
        "codex_angle": "Hồ Sơ Thật 100%: Trương Hiển Quang & Đại Án 1·18 Ngân Hàng Thương Mại Thẩm Dương (2003–2006) — Truy Nguyên Khung Xe Đạp Cũ Và Cuộc Vây Bắt Tại Tề Tề Cáp Nhĩ",
        "codex_reasons": [
            "Một trong những đại án cướp xe chở tiền chấn động nhất lịch sử vùng Đông Bắc Trung Quốc, có đầy đủ tư liệu hiện trường, truy nã cấp A và phiên tòa xét xử trên CCTV",
            "Tòa án Nhân dân Trung cấp Thẩm Dương xét xử công khai và thi hành án tử hình Trương Hiển Quang tháng 12/2006"
        ],
        "opening_hook": "2003년 1월 18일 저녁 다섯 시 오십 분, 선양시 상업은행 정문 앞에 세워져 있던 낡은 자전거 한 대가 현금수송차가 도착하는 순간 거대한 굉음을 내며 터졌습니다. 단 삼 분 만에 현금 가방이 사라졌고, 주범 장셴광은 안개 속으로 자취를 감췄습니다.",
        "note": "📋 【Hồ sơ vụ án: đại án dùng thiết bị nổ điều khiển từ xa trên xe đạp tập kích xe chở tiền ngân hàng cướp 2,1 triệu tệ và tước đoạt 3 sinh mạng · lệnh truy nã cấp A Bộ Công an · tuyên án tử hình Trương Hiển Quang】 Hồ sơ thật 100% Đại án 1·18 tại Thẩm Dương, Liêu Ninh (辽宁沈阳1·18运钞车劫案 — Ba anh em Trương Hiển Quang 张显光, Trương Hiển Minh 张显明, Trương Hiển Huy 张显辉, 2000–2006): Sau khi gây án cướp 2,1 triệu NDT trước Ngân hàng Thương mại Thẩm Dương, hai người em bị bắt còn kẻ cầm đầu Trương Hiển Quang trốn lên Hắc Long Giang dưới tên giả làm thợ hồ suốt 3 năm trước khi bị bắt tại Tề Tề Cáp Nhĩ và bị Tòa án Thẩm Dương tuyên án tử hình.",
        "hook_archetype": "countdown_system_breach"
    },
    {
        "id": "fin_cn_beijing_luxianzhou_armored_van_1996",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "北京1996年首例连续劫持银行运钞车220万元与亚运村地库藏金案 — 鹿宪州 (1996)",
        "archival_search_keywords_zh": [
            "北京 1996 运钞车大案 鹿宪州 纪实",
            "鹿宪州 亚运村 银行劫案 侦破",
            "北京刑侦 鹿宪州 档案"
        ],
        "recommended_vox_verbs": [
            "GEO_VECTOR_PURSUIT",
            "SINGLE_EVIDENCE_AUTOPSY",
            "CONCENTRIC_TRAP"
        ],
        "title": "[중국 실화 사건] 대낮 수도 한복판에서 은행 현금수송차 3대를 털어 고급 아파트 지하 주차장에 숨긴 수배범 | 베이징 루셴저우 사건 ([Vụ Án Có Thật ở Trung Quốc] Chặn cướp 3 xe chở tiền ngân hàng giữa ban ngày ở thủ đô rồi giấu tiền trong hầm chung cư cao cấp | Đại án Lộc Hiến Châu Bắc Kinh)",
        "topic_anchor": "[중국 실화 사건] 대낮 수도 한복판에서 은행 현금수송차 3대를 털어 고급 아파트 지하 주차장에 숨긴 수배범 | 베이징 루셴저우 사건",
        "winner_cluster": "Luồng 1 · Vết Sơn Xước Trên Xe Jeep Cherokee & Hầm Giấu Tiền 2,2 Triệu Tệ Giữa Làng Á Vận Hội Bắc Kinh (베이징 루셴저우 현금수송차 사건)",
        "codex_score": 97,
        "profile_score": 97,
        "codex_angle": "Hồ Sơ Thật 100%: Lộc Hiến Châu (鹿宪州, 1996) — Vụ Cướp Xe Chở Tiền Đầu Tiên Giữa Thủ Đô Bắc Kinh Buộc Toàn Hệ Thống Ngân Hàng Trung Quốc Phải Thay Đổi Xe Bọc Thép",
        "codex_reasons": [
            "Vụ án bước ngoặt lịch sử năm 1996 tại Bắc Kinh khiến Ngân hàng Nhân dân Trung Quốc ra lệnh thay toàn bộ xe tải chở tiền thường bằng xe bọc thép chống đạn trên toàn quốc",
            "Tư liệu điều tra dấu vết sơn xe và cuộc vây bắt tại Bắc Kinh cực kỳ kịch tính"
        ],
        "opening_hook": "1996년 2월 8일 오전, 베이징 번화가 은행 앞에서 흰색 방한모를 쓴 남자가 현금수송차의 문을 가로막고 백이십만 위안이 든 철제 상자를 통째로 들고 사라졌습니다. 도주 차량을 버리고 흔적을 지운 그가 현금 더미를 숨긴 곳은 뜻밖에도 수도 한복판의 최고급 아파트 지하 주차장이었습니다.",
        "note": "📋 【Hồ sơ vụ án: đại án liên hoàn chặn cướp xe chở tiền ngân hàng đầu tiên tại thủ đô Bắc Kinh (cướp hơn 2,2 triệu tệ, tước đoạt 2 sinh mạng) · truy vết sơn xe Jeep và vây bắt Lộc Hiến Châu】 Hồ sơ thật 100% Chuyên án Lộc Hiến Châu tại Bắc Kinh năm 1996 (北京1996年2·8及6·3连续劫持银行运钞车案 — Lộc Hiến Châu 鹿宪州): Lợi dụng thời gian tạm hoãn chấp hành án để chữa bệnh, Lộc Hiến Châu trộm xe Jeep liên tiếp chặn cướp xe chở tiền ngân hàng tại Tây Đơn và Triều Dương Môn, giấu tiền trong hầm xe Làng Á vận hội; Công an Bắc Kinh lần theo vết sơn va quệt trên thân xe, vây bắt và tiêu diệt/xét xử toàn bộ băng nhóm tháng 9/1996.",
        "hook_archetype": "last_ordinary_routine"
    },
    {
        "id": "fin_cn_shenzhen_wangjianye_10m_forex_extradition",
        "topic_stream": "financial_crime",
        "case_real_name_zh": "广东深圳计划局财贸处长千万元跨境骗汇潜逃泰国引渡第一案 — 王建业 (1992–1995)",
        "archival_search_keywords_zh": [
            "深圳 王建业 特大经济案 纪实",
            "王建业 潜逃泰国 引渡 死刑",
            "深圳第一大案 王建业 档案"
        ],
        "recommended_vox_verbs": [
            "LEDGER_DIFF_SCRUB",
            "GEO_VECTOR_PURSUIT",
            "SPLIT_PARADOX"
        ],
        "title": "[중국 실화 사건] 가짜 외환 승인서로 1,000만 위안을 빼돌려 태국으로 달아났다 현지 조직에 납치된 국장 | 선전 왕젠예 사건 ([Vụ Án Có Thật ở Trung Quốc] Dùng giấy phép ngoại hối giả rút 10 triệu tệ trốn sang Thái Lan rồi bị băng đảng bản địa bắt cóc của vị trưởng phòng | Đại án Vương Kiến Nghiệp)",
        "topic_anchor": "[중국 실화 사건] 가짜 외환 승인서로 1,000만 위안을 빼돌려 태국으로 달아났다 현지 조직에 납치된 국장 | 선전 왕젠예 사건",
        "winner_cluster": "Luồng 1 · Con Dấu Phê Duyệt Ngoại Hối Giả 10 Triệu Tệ & Chuyên Án Dẫn Độ Hình Sự Đầu Tiên Từ Thái Lan (선전 왕젠예 외환 사기 송환 사건)",
        "codex_score": 97,
        "profile_score": 97,
        "codex_angle": "Hồ Sơ Thật 100%: Vương Kiến Nghiệp (王建业, Thâm Quyến 1992–1995) — Từ Trưởng Phòng Nắm Quyền Cấp Hạn Ngạch Ngoại Hối Đến Cuộc Giải Cứu Và Dẫn Độ Lịch Sử Tại Bangkok",
        "codex_reasons": [
            "Chuyên án dẫn độ tội phạm kinh tế đặc biệt nghiêm trọng đầu tiên của Đặc khu Thâm Quyến và Viện Kiểm sát Tối cao Trung Quốc, tình tiết đảo chiều liên tục như phim điện ảnh",
            "Tòa án Nhân dân Trung cấp Thâm Quyến và Tòa án Tối cao tuyên án tử hình Vương Kiến Nghiệp tháng 12/1995"
        ],
        "opening_hook": "특구 도시 선전의 외환 배정 도장을 쥐고 있던 재무처장 왕젠예는 가짜 승인서 몇 장으로 일천만 위안과 거액의 달러를 해외 계좌로 빼돌린 뒤 태국으로 사라졌습니다. 그러나 방콕에서 억만장자의 삶을 꿈꾸던 그를 기다리고 있던 것은 현지 무장 납치단의 몸값 협박 전화였습니다.",
        "note": "📋 【Hồ sơ vụ án: đại án trưởng phòng Cục Kế hoạch Thâm Quyến làm giả văn bản phê duyệt ngoại hối rút ruột hơn 10 triệu tệ & 1,39 triệu USD trốn sang Thái Lan · dẫn độ về nước tuyên án tử hình Vương Kiến Nghiệp】 Hồ sơ thật 100% Đại án Vương Kiến Nghiệp tại Thâm Quyến, Quảng Đông (广东深圳王建业特大受贿诈骗潜逃引渡案, 1992–1995): Vương Kiến Nghiệp cấu kết với Sử Yến Thanh làm giả hạn ngạch xuất khẩu hoàn thuế và ngoại hối rút hơn 10 triệu NDT rồi mang hộ chiếu giả trốn sang Bangkok, bị băng đảng địa phương bắt cóc đòi tiền chuộc trước khi Cảnh sát Thái Lan giải cứu và bàn giao cho Viện Kiểm sát Trung Quốc dẫn độ về nước thi hành án tử hình.",
        "hook_archetype": "double_life_unmasking"
    },
    {
        "id": "vio_cn_guangdong_foshan_huangwenyi_5d",
        "topic_stream": "major_violent_crime",
        "case_real_name_zh": "广东佛山南海12·28特大命案公安部A级通缉5天极速抓捕案 — 黄文义 (2006–2007)",
        "archival_search_keywords_zh": [
            "佛山 黄文义 12·28 公安部A级通缉 今日说法",
            "广东南海 黄文义 庭审 死刑",
            "A级通缉犯 黄文义 5天抓捕 天网"
        ],
        "recommended_vox_verbs": [
            "RADIAL_TIME_PRESSURE",
            "GEO_VECTOR_PURSUIT",
            "ALIBI_SHATTER"
        ],
        "title": "[중국 실화 사건] 약국 체인점 여러 곳을 운영하던 모범 가장이 하룻밤 새 공안부 A급 1호 수배범이 된 이유 | 포산 황원이 사건 ([Vụ Án Có Thật ở Trung Quốc] Lý do ông chủ chuỗi hiệu thuốc hiền lành sau một đêm trở thành tội phạm truy nã cấp A số 1 Bộ Công an | Đại án Hoàng Văn Nghĩa Phật Sơn)",
        "topic_anchor": "[중국 실화 사건] 약국 체인점 여러 곳을 운영하던 모범 가장이 하룻밤 새 공안부 A급 1호 수배범이 된 이유 | 포산 황원이 사건",
        "winner_cluster": "Luồng 2 · Ông Chủ Chuỗi Hiệu Thuốc Trầm Lặng & 120 Giờ Truy Bắt Truy Nã Cấp A Giữa Đêm Giao Thừa (포산 황원이 A급 수배 사건)",
        "codex_score": 98,
        "profile_score": 98,
        "codex_angle": "Hồ Sơ Thật 100%: Hoàng Văn Nghĩa (黄文义, Phật Sơn 2006–2007) — Giải Mã Tâm Lý Lệch Lạc Đằng Sau Vỏ Bọc Ông Chủ Hiệu Thuốc Thành Đạt Và 5 Ngày Đêm Phong Tỏa Quảng Châu",
        "codex_reasons": [
            "Chuyên án truy nã cấp A chấn động toàn Trung Quốc dịp Tết Dương lịch 2007, lên sóng CCTV 今日说法 / 天网 với đầy đủ video vây bắt và thẩm vấn",
            "Tòa án Nhân dân Trung cấp Phật Sơn xét xử công khai và thi hành án tử hình Hoàng Văn Nghĩa"
        ],
        "opening_hook": "이웃들에게는 늘 공손하게 인사하고 약국 세 곳을 성실히 운영하던 서른네 살의 가장 황원이. 하지만 2006년 12월 28일 밤이 지나자 그는 현금 십만 위안을 챙겨 야간 택시를 타고 사라졌고, 공안부는 즉시 전국에 A급 수배령을 내렸습니다.",
        "note": "📋 【Hồ sơ vụ án: trọng án đặc biệt nghiêm trọng tước đoạt 6 sinh mạng tại Phật Sơn · lệnh truy nã cấp A Bộ Công an · bắt giữ sau 5 ngày đêm và Tòa án Phật Sơn tuyên án tử hình Hoàng Văn Nghĩa】 Hồ sơ thật 100% Chuyên án 12·28 tại quận Nam Hải, Phật Sơn, Quảng Đông (广东佛山南海12·28特大命案 — Hoàng Văn Nghĩa 黄文义, 2006–2007): Bề ngoài là ông chủ chuỗi hiệu thuốc giàu có và hiền lành, Hoàng Văn Nghĩa gây ra thảm án 6 người thân trong đêm 28/12/2006 rồi mang 100.000 NDT dùng chứng minh thư giả liên tục đổi khách sạn tại Quảng Châu; bị bắt giữ ngày 1/1/2007 dưới lệnh truy nã cấp A và bị Tòa án Phật Sơn tuyên án tử hình.",
        "hook_archetype": "double_life_unmasking"
    },
    {
        "id": "vio_cn_beijing_daxing_lilei_sanya_6d",
        "topic_stream": "major_violent_crime",
        "case_real_name_zh": "北京大兴清城11·23特大命案跨3000公里三亚6天追缉案 — 李磊 (2009)",
        "archival_search_keywords_zh": [
            "北京大兴 李磊 11·23 今日说法",
            "大兴特大命案 李磊 三亚抓捕 法治进行时",
            "李磊 庭审 死刑 央视"
        ],
        "recommended_vox_verbs": [
            "GEO_VECTOR_PURSUIT",
            "RADIAL_TIME_PRESSURE",
            "SPLIT_PARADOX"
        ],
        "title": "[중국 실화 사건] 집 안 에어컨을 최저 온도로 맞춰 밀봉해 두고 3,000km 밖 휴양지로 사라진 모범 남편 | 베이징 리레이 사건 ([Vụ Án Có Thật ở Trung Quốc] Chỉnh điều hòa căn hộ xuống nhiệt độ thấp nhất, khóa kín cửa rồi biến mất tới khu nghỉ dưỡng cách 3.000km của người chồng | Đại án Lý Lỗi Bắc Kinh)",
        "topic_anchor": "[중국 실화 사건] 집 안 에어컨을 최저 온도로 맞춰 밀봉해 두고 3,000km 밖 휴양지로 사라진 모범 남편 | 베이징 리레이 사건",
        "winner_cluster": "Luồng 2 · Căn Hộ Bật Điều Hòa Lạnh Sâu Giữa Mùa Đông Bắc Kinh & 144 Giờ Truy Vết 3.000km Tới Tam Á (베이징 다싱구 리레이 사건)",
        "codex_score": 98,
        "profile_score": 98,
        "codex_angle": "Hồ Sơ Thật 100%: Lý Lỗi & Chuyên Án 11·23 Đại Hưng, Bắc Kinh (2009) — Sự Bùng Nổ Tâm Lý Sau 10 Năm Nhẫn Nhịn Và Cuộc Truy Bắt Thần Tốc Tại Đảo Hải Nam",
        "codex_reasons": [
            "Một trong những đại án hình sự lớn nhất Bắc Kinh thập niên 2000, có đầy đủ tư liệu của đài truyền hình Bắc Kinh (法治进行时) và CCTV 今日说法",
            "Tòa án Nhân dân Trung cấp số 1 Bắc Kinh tuyên án tử hình và thi hành án đối với Lý Lỗi tháng 9/2011"
        ],
        "opening_hook": "영하로 떨어진 11월의 베이징 아파트 안에서 에어컨이 가장 낮은 냉방 온도로 사흘 내내 돌아가고 있었습니다. 방문마다 출입을 막는 메모를 붙여 시간을 끈 스물아홉 살의 가장 리레이는 이미 삼천 킬로미터 남쪽 열대 해변 도시에 도착해 있었습니다.",
        "note": "📋 【Hồ sơ vụ án: trọng án đặc biệt nghiêm trọng tước đoạt 6 sinh mạng trong căn hộ khóa kín tại Đại Hưng, Bắc Kinh · 6 ngày truy bắt xuyên 3.000km tới Tam Á · Tòa án Bắc Kinh tuyên án tử hình Lý Lỗi】 Hồ sơ thật 100% Chuyên án 11·23 tại quận Đại Hưng, Bắc Kinh (北京大兴11·23特大命案 — Lý Lỗi 李磊, 11/2009): Sau khi gây án tại căn hộ khu Thanh Thành đêm 23/11/2009, Lý Lỗi bật điều hòa lạnh sâu và khóa kín các phòng để trì hoãn việc phát hiện rồi mang tiền mặt đi tàu suốt 3.000km xuống Tam Á (Hải Nam); Công an Bắc Kinh và Hải Nam phối hợp bắt giữ Lý Lỗi sau 6 ngày và Tòa án Bắc Kinh tuyên án tử hình.",
        "hook_archetype": "locked_room_vault_paradox"
    },
    {
        "id": "vio_cn_hubei_suizhou_xiongzhenlin_7d",
        "topic_stream": "major_violent_crime",
        "case_real_name_zh": "湖北随州洛阳镇1·4特大命案公安部A级通缉7天跨省抓捕案 — 熊振林 (2009)",
        "archival_search_keywords_zh": [
            "湖北随州 熊振林 公安部A级通缉 今日说法",
            "熊振林 1·4特大案 武汉抓捕 天网",
            "随州 熊振林 庭审 死刑"
        ],
        "recommended_vox_verbs": [
            "GEO_VECTOR_PURSUIT",
            "CONCENTRIC_TRAP",
            "RADIAL_TIME_PRESSURE"
        ],
        "title": "[중국 실화 사건] 남쪽 섬으로 도망친 줄 알았던 공안부 A급 수배범이 수염을 기르고 수사 본부 코앞에 나타난 이유 | 슝전린 추적 사건 ([Vụ Án Có Thật ở Trung Quốc] Tưởng đã trốn ra đảo cực Nam nhưng kẻ truy nã cấp A lại để râu quay ngược về ngay sát tổng hành dinh cảnh sát | Chuyên án Hùng Chấn Lâm)",
        "topic_anchor": "[중국 실화 사건] 남쪽 섬으로 도망친 줄 알았던 공안부 A급 수배범이 수염을 기르고 수사 본부 코앞에 나타난 이유 | 슝전린 추적 사건",
        "winner_cluster": "Luồng 2 · Đòn Nghi Binh Đi Xuống Hải Nam Rồi Quay Ngược Về Vũ Hán & 7 Ngày Đêm Truy Nã Cấp A (후베이 쑤이저우 슝전린 사건)",
        "codex_score": 98,
        "profile_score": 98,
        "codex_angle": "Hồ Sơ Thật 100%: Hùng Chấn Lâm (熊振林, Tùy Châu, Hồ Bắc 2009) — Cuộc Đấu Trí Phản Trinh Sát Của Lệnh Truy Nã Cấp A Số 1 Năm 2009 Và Phiên Tòa Xét Xử Công Khai",
        "codex_reasons": [
            "Chuyên án truy nã cấp A lớn nhất đầu năm 2009 của Bộ Công an Trung Quốc, có video bắt sống tại hiện trường Vũ Hán và phiên tòa xét xử trực tiếp trên CCTV",
            "Khớp hoàn hảo bản đồ truy đuổi 3D GEO_VECTOR_PURSUIT (Tùy Châu -> Hải Nam -> Vũ Hán)"
        ],
        "opening_hook": "하이난섬 삼아 해변에서 공안부 A급 수배범 슝전린의 흔적이 발견되자 전국의 추적망이 일제히 남쪽 바다로 쏠렸습니다. 하지만 그 시각 슝전린은 경찰의 허를 찔러 다시 북쪽으로 기차를 타고 올라와, 사건 발생 성도인 우한 시내 철물점에서 변장 도구를 고르고 있었습니다.",
        "note": "📋 【Hồ sơ vụ án: trọng án đặc biệt nguy hiểm tước đoạt 8 sinh mạng tại Tùy Châu, Hồ Bắc · lệnh truy nã cấp A Bộ Công an · bắt giữ sau 7 ngày tại Vũ Hán và Tòa án Tùy Châu tuyên án tử hình Hùng Chấn Lâm】 Hồ sơ thật 100% Chuyên án 1·4 tại thị trấn Lạc Dương, Tùy Châu, Hồ Bắc (湖北随州1·4特大命案 — Hùng Chấn Lâm 熊振林, 1/2009): Sau khi gây trọng án đêm 4/1/2009, Hùng Chấn Lâm bắt tàu trốn xuống Tam Á (Hải Nam) rồi bất ngờ quay ngược về Vũ Hán nhằm mua dụng cụ trốn tiếp lên Đông Bắc; dưới lệnh truy nã cấp A của Bộ Công an, cảnh sát Vũ Hán nhận diện và quật ngã hắn ngày 11/1/2009, Tòa án Tùy Châu tuyên án tử hình.",
        "hook_archetype": "countdown_system_breach"
    },
    {
        "id": "vio_cn_henan_pingyu_huangyong_netcafe",
        "topic_stream": "major_violent_crime",
        "case_real_name_zh": "河南平舆11·12特大系列少年失踪案与张成亮机智逃生纪实 — 黄勇 (2001–2003)",
        "archival_search_keywords_zh": [
            "河南平舆 黄勇 11·12大案 今日说法",
            "平舆特大案件 黄勇 张成亮 纪实",
            "驻马店 黄勇 审判 死刑"
        ],
        "recommended_vox_verbs": [
            "ALIBI_SHATTER",
            "BLIND_SPOT_REVEAL",
            "SINGLE_EVIDENCE_AUTOPSY"
        ],
        "title": "[중국 실화 사건] PC방에 간다던 남학생들이 2년간 차례로 증발한 마을과 16세 소년의 극적인 탈출극 | 허난 황융 사건 ([Vụ Án Có Thật ở Trung Quốc] Thị trấn nơi hàng loạt nam sinh đi quán net bốc hơi suốt 2 năm và màn đấu trí thoát thân của thiếu niên 16 tuổi | Đại án Hoàng Dũng Hà Nam)",
        "topic_anchor": "[중국 실화 사건] PC방에 간다던 남학생들이 2년간 차례로 증발한 마을과 16세 소년의 극적인 탈출극 | 허난 황융 사건",
        "winner_cluster": "Luồng 2 · Lời Nói Dối 'Tuyển Dụng Việc Làm Lương Cao' Ở Quán Net & Màn Đấu Trí Sống Còn Của Thiếu Niên 16 Tuổi (허난 핑위현 황융 사건)",
        "codex_score": 99,
        "profile_score": 99,
        "codex_angle": "Hồ Sơ Thật 100%: Hoàng Dũng & Đại Án 11·12 Bình Dư, Hà Nam (2001–2003) — Cách Thiếu Niên 16 Tuổi Trương Thành Lương Giữ Bình Tĩnh Đánh Lừa Kẻ Thủ Ác Để Đưa Cảnh Sát Tới Ngôi Nhà Biệt Lập",
        "codex_reasons": [
            "Một trong những chuyên án điều tra nổi tiếng nhất thập niên 2000 của Bộ Công an Trung Quốc, có phóng sự chuyên đề trên CCTV 今日说法 / 法治在线",
            "Tòa án Nhân dân Trung cấp Trú Mã Điếm xét xử lưu động trước hàng vạn người dân và thi hành án tử hình Hoàng Dũng tháng 12/2003"
        ],
        "opening_hook": "2001년부터 허난성 핑위현의 작은 읍내에서 PC방에 간다던 남학생들이 한 명씩 흔적도 없이 사라지기 시작했습니다. 모두가 대도시로 가출했을 것이라 믿었지만, 2003년 11월 외딴 벽돌집에서 극적으로 빠져나온 열여섯 살 소년 장청량이 경찰서 문을 두드리며 2년간의 미스터리가 드러났습니다.",
        "note": "📋 【Hồ sơ vụ án: trọng án đặc biệt nghiêm trọng dụ dỗ 17 nam sinh từ quán Internet tại Bình Dư, Hà Nam · thiếu niên 16 tuổi Trương Thành Lương mưu trí thoát thân báo công an · Tòa án Trú Mã Điếm tuyên án tử hình Hoàng Dũng】 Hồ sơ thật 100% Đại án 11·12 tại huyện Bình Dư, Trú Mã Điếm, Hà Nam (河南平舆11·12特大系列案件 — Hoàng Dũng 黄勇, 2001–2003): Hoàng Dũng giả làm người giới thiệu việc làm ở các quán Internet để dụ nam sinh về ngôi nhà gạch hẻo lánh; tháng 11/2003, nam sinh 16 tuổi Trương Thành Lương bình tĩnh thuyết phục Hoàng Dũng lấy lòng tin để được thả ra lấy tiền rồi lập tức báo công an bắt giữ và tuyên án tử hình Hoàng Dũng.",
        "hook_archetype": "chilling_verbatim_line"
    },
    {
        "id": "vio_cn_shaanxi_shangluo_longzhimin_1985",
        "topic_stream": "major_violent_crime",
        "case_real_name_zh": "陕西商县王墹村48人连环失踪特大悬案与1元8角5分麦草条侦破纪实 — 龙治民·闫淑霞 (1983–1985)",
        "archival_search_keywords_zh": [
            "陕西商县 龙治民 48人 特大案 纪实",
            "龙治民 1元8角5分 刑侦档案",
            "商洛 龙治民 审判 死刑"
        ],
        "recommended_vox_verbs": [
            "SINGLE_EVIDENCE_AUTOPSY",
            "BLIND_SPOT_REVEAL",
            "FORENSIC_ZOOM_CHAIN"
        ],
        "title": "[중국 실화 사건] 장터에 간 주민 48명이 감쪽같이 증발한 마을과 1위안 8마오 영수증 한 장이 밝혀낸 진실 | 산시성 룽즈민 사건 ([Vụ Án Có Thật ở Trung Quốc] 48 người đi chợ huyện bốc hơi kỳ bí và tờ hóa đơn 1,85 tệ phanh phui ngôi nhà luôn đóng kín cửa sổ | Đại án Long Trị Dân Thiểm Tây)",
        "topic_anchor": "[중국 실화 사건] 장터에 간 주민 48명이 감쪽같이 증발한 마을과 1위안 8마오 영수증 한 장이 밝혀낸 진실 | 산시성 룽즈민 사건",
        "winner_cluster": "Luồng 2 · Tờ Giấy Nhận Tiền Bán Rơm 1,85 Tệ & Ngôi Nhà Đất Đóng Kín Cửa Sổ Suốt 3 Năm (산시성 상현 룽즈민 48인 실종 사건)",
        "codex_score": 99,
        "profile_score": 99,
        "codex_angle": "Hồ Sơ Thật 100%: Đại Án Long Trị Dân Tại Thương Lạc, Thiểm Tây (1983–1985) — Khi Một Tờ Hóa Đơn 1,85 Nhân Dân Tệ Mở Khóa Kỳ Án Mất Tích Lớn Nhất Lịch Sử Hình Sự Trung Quốc",
        "codex_reasons": [
            "Hồ sơ hình sự kinh điển bậc nhất trong lịch sử Bộ Công an Trung Quốc, có đầy đủ ảnh tư liệu hồ sơ lưu trữ và biên bản xét xử của Tòa án Thương Lạc năm 1985",
            "Mỏ neo vật chứng 1 tờ biên lai 1,85 tệ cực kỳ đắt giá cho SINGLE_EVIDENCE_AUTOPSY trên bàn biên tập Vox"
        ],
        "opening_hook": "1983년부터 산시성 상현의 읍내 장터와 버스터미널 주변에서 일자리를 찾던 농민 마흔여덟 명이 차례로 증발했습니다. 아무런 단서도 없던 1985년 5월, 실종자 가족이 찾아낸 단서라곤 다른 남자의 이름이 적힌 일 위안 팔 마오짜리 밀짚 판매 영수증 한 장뿐이었습니다.",
        "note": "📋 【Hồ sơ vụ án: đại án mất tích liên hoàn lớn nhất lịch sử hình sự Trung Quốc (48 nạn nhân tại huyện Thương, Thiểm Tây) · phá án từ tờ hóa đơn bán rơm 1,85 tệ · Tòa án Thương Lạc tuyên án tử hình Long Trị Dân & Diêm Thục Hà】 Hồ sơ thật 100% Đại án Long Trị Dân tại thôn Vương Gian, huyện Thương (nay là Thương Lạc), Thiểm Tây (陕西商县龙治民特大案, 1983–1985): Long Trị Dân lấy cớ thuê người làm công giá cao hoặc giới thiệu chỗ trọ miễn phí ở chợ huyện để dụ 48 người về căn nhà đất hẻo lánh; tháng 5/1985, gia đình nạn nhân Đỗ Trường Anh phát hiện Long Trị Dân cầm tờ biên lai bán rơm 1,85 tệ của người mất tích đi lĩnh tiền, giúp công an khám phá toàn bộ vụ án và tuyên án tử hình.",
        "hook_archetype": "micro_forensic_anomaly"
    },
    {
        "id": "vio_cn_henan_ruyang_yangxinhai_bicycle",
        "topic_stream": "major_violent_crime",
        "case_real_name_zh": "豫皖鲁冀跨4省夜间流窜特大系列案件侦破纪实 — 杨新海 (1999–2003)",
        "archival_search_keywords_zh": [
            "杨新海 跨四省 特大案件 纪实",
            "公安部督办 杨新海 沧州落网 天网",
            "河南漯河 杨新海 审判 死刑"
        ],
        "recommended_vox_verbs": [
            "GEO_VECTOR_PURSUIT",
            "FORENSIC_ZOOM_CHAIN",
            "MICRO_TRACE_MATCH"
        ],
        "title": "[중국 실화 사건] 발 크기를 속이려고 일부러 큰 신발을 신고 4개 성을 넘나든 공안부 특급 수배범의 치밀한 위장 | 양신하이 추적 사건 ([Vụ Án Có Thật ở Trung Quốc] Cố tình đi giày cỡ lớn hơn chân thật để đánh lừa pháp y và hành tung vượt 4 tỉnh của kẻ truy nã đặc biệt | Chuyên án Dương Tân Hải)",
        "topic_anchor": "[중국 실화 사건] 발 크기를 속이려고 일부러 큰 신발을 신고 4개 성을 넘나든 공안부 특급 수배범의 치밀한 위장 | 양신하이 추적 사건",
        "winner_cluster": "Luồng 2 · Thủ Đoạn Mặc 3 Lớp Áo Đổi Nhân Dạng & Giám Định ADN Kép Liên Tỉnh Khóa Chặt Dương Tân Hải (4개 성 광역 추적 양신하이 사건)",
        "codex_score": 98,
        "profile_score": 98,
        "codex_angle": "Hồ Sơ Thật 100%: Chuyên Án Liên Tỉnh Dương Tân Hải (杨新海, 1999–2003) — Cách Chuyên Gia Dấu Vết Bộ Công An Giải Mã Thủ Đoạn 'Đi Giày Cỡ Lớn Hơn Chân Thật' Để Gộp Án 4 Tỉnh",
        "codex_reasons": [
            "Chuyên án hình sự liên tỉnh lớn nhất vùng Hoa Bắc giai đoạn 1999–2003 do Bộ Công an trực tiếp chỉ đạo, tư liệu bắt giữ tại Thương Châu và xét xử tại Tháp Hà đầy đủ",
            "Tòa án Nhân dân Trung cấp Tháp Hà (Hà Nam) tuyên án tử hình và thi hành án đối với Dương Tân Hải tháng 2/2004"
        ],
        "opening_hook": "네 개 성의 스물여섯 개 현장에서 남겨진 발자국 크기가 매번 조금씩 달랐기에 경찰은 오랫동안 서로 다른 범인들의 소행이라 생각했습니다. 하지만 법의학자들이 신발 밑창 안쪽의 압력 중심점을 정밀 분석하자, 한 남자가 일부러 큰 신발을 겹쳐 신고 추적망을 교란해 왔다는 사실이 밝혀졌습니다.",
        "note": "📋 【Hồ sơ vụ án: đại án liên tỉnh đặc biệt nguy hiểm xuyên 4 tỉnh Hà Nam, An Huy, Sơn Đông, Hà Bắc · thủ đoạn mặc 3 lớp áo và đi giày cỡ lớn đánh lừa pháp y · bắt giữ tại Thương Châu và Tòa án Tháp Hà tuyên án tử hình Dương Tân Hải】 Hồ sơ thật 100% Chuyên án Dương Tân Hải (豫皖鲁冀特大系列案 — Dương Tân Hải 杨新海, 1999–2003): Dương Tân Hải luôn mặc nhiều lớp quần áo để vứt bỏ lớp ngoài sau khi gây án và đi giày lớn hơn cỡ chân thật để làm lệch kết quả đo chiều cao pháp y; tháng 11/2003, Công an Thương Châu (Hà Bắc) bắt giữ Dương Tân Hải trong đợt kiểm tra ban đêm và đối chiếu ADN khớp toàn bộ chuỗi án 4 tỉnh, Tòa án Tháp Hà tuyên án tử hình.",
        "hook_archetype": "micro_forensic_anomaly"
    },
    {
        "id": "vio_cn_heilongjiang_jiamusi_gongrunbo_2006",
        "topic_stream": "major_violent_crime",
        "case_real_name_zh": "黑龙江佳木斯向阳区特大系列少年失踪案侦破纪实 — 宫润伯 (2005–2006)",
        "archival_search_keywords_zh": [
            "佳木斯 宫润伯 特大案件 今日说法",
            "黑龙江佳木斯 宫润伯 侦破纪实 天网",
            "宫润伯 庭审 死刑 央视"
        ],
        "recommended_vox_verbs": [
            "BLIND_SPOT_REVEAL",
            "RADIAL_TIME_PRESSURE",
            "SINGLE_EVIDENCE_AUTOPSY"
        ],
        "title": "[중국 실화 사건] 창문마다 신문지를 겹겹이 바른 외곽 셋방과 9살 소년이 기억해낸 결정적 단서 하나 | 자무쓰 궁룬보 사건 ([Vụ Án Có Thật ở Trung Quốc] Căn phòng thuê dán kín báo cũ ở ngoại ô và manh mối sống còn từ trí nhớ của cậu bé 9 tuổi | Đại án Cung Nhuận Bá Hắc Long Giang)",
        "topic_anchor": "[중국 실화 사건] 창문마다 신문지를 겹겹이 바른 외곽 셋방과 9살 소년이 기억해낸 결정적 단서 하나 | 자무쓰 궁룬보 사건",
        "winner_cluster": "Luồng 2 · Căn Phòng Thuê Dán Kín Giấy Báo Ở Giai Mộc Tư & Trí Nhớ Chính Xác Của Cậu Bé 9 Tuổi (헤이룽장 자무쓰 궁룬보 사건)",
        "codex_score": 97,
        "profile_score": 97,
        "codex_angle": "Hồ Sơ Thật 100%: Chuyên Án Cung Nhuận Bá Tại Giai Mộc Tư, Hắc Long Giang (2005–2006) — Cuộc Đột Kích Trong Đêm Tuyết Lạnh Và Bản Án Tử Hình Của Tòa Án Giai Mộc Tư",
        "codex_reasons": [
            "Đại án hình sự chấn động tỉnh Hắc Long Giang năm 2006 được Bộ Công an khen thưởng đặc biệt và dựng thành phóng sự trên CCTV 今日说法 / 天网",
            "Tòa án Nhân dân Trung cấp Giai Mộc Tư xét xử công khai và thi hành án tử hình Cung Nhuận Bá tháng 12/2006"
        ],
        "opening_hook": "영하 이십 도의 눈보라가 몰아치던 2006년 2월 저녁, 아홉 살 소년이 신발 한 짝이 벗겨진 채 자무쓰시 공안국 분국으로 뛰어들어왔습니다. 소년이 떨리는 손으로 가리킨 골목 끝에는 일 년 내내 창문마다 신문지가 겹겹이 발라져 있던 수상한 단칸방이 있었습니다.",
        "note": "📋 【Hồ sơ vụ án: trọng án đặc biệt nghiêm trọng khiến 6 thiếu niên mất tích tại Giai Mộc Tư, Hắc Long Giang · cậu bé 9 tuổi mưu trí thoát khỏi căn nhà thuê khóa kín báo cảnh sát · Tòa án Giai Mộc Tư tuyên án tử hình Cung Nhuận Bá】 Hồ sơ thật 100% Chuyên án 2·28 tại Giai Mộc Tư, Hắc Long Giang (黑龙江佳木斯宫润伯特大案, 2005–2006): Cung Nhuận Bá thuê một căn nhà nhỏ ở ngoại ô dán kín báo cũ lên cửa sổ để che giấu hành tung; tháng 2/2006, một cậu bé 9 tuổi lợi dụng lúc hắn sơ hở đã mở chốt cửa chạy thẳng tới đồn cảnh sát, giúp Công an Giai Mộc Tư ập vào bắt giữ Cung Nhuận Bá và Tòa án tuyên án tử hình.",
        "hook_archetype": "chilling_verbatim_line"
    },
    {
        "id": "vio_cn_beijing_wanglihua_kidnap_22h",
        "topic_stream": "major_violent_crime",
        "case_real_name_zh": "北京三里屯冒充刑警绑架明星吴若甫22小时极速解救案 — 王立华·王庆晓 (2004)",
        "archival_search_keywords_zh": [
            "吴若甫 绑架案 王立华 22小时 今日说法",
            "北京刑警 解救吴若甫 真实录像 央视",
            "王立华 庭审 死刑 纪实"
        ],
        "recommended_vox_verbs": [
            "RADIAL_TIME_PRESSURE",
            "GEO_VECTOR_PURSUIT",
            "CONCENTRIC_TRAP"
        ],
        "title": "[중국 실화 사건] 가짜 경찰 신분증과 수갑으로 형사 전문 유명 배우를 납치한 주범과 22시간의 숨 막히는 추격 | 베이징 왕리화 사건 ([Vụ Án Có Thật ở Trung Quốc] Dùng thẻ cảnh sát giả và còng số 8 bắt cóc ngôi sao chuyên đóng vai hình cảnh cùng 22 giờ giải cứu nghẹt thở | Đại án Vương Lập Hoa Bắc Kinh)",
        "topic_anchor": "[중국 실화 사건] 가짜 경찰 신분증과 수갑으로 형사 전문 유명 배우를 납치한 주범과 22시간의 숨 막히는 추격 | 베이징 왕리화 사건",
        "winner_cluster": "Luồng 2 · 22 Giờ Truy Vết Tần Số Vô Tuyến Giải Cứu Ngôi Sao Điện Ảnh Ngô Nhược Phủ Giữa Thủ Đô Bắc Kinh (베이징 왕리화 22시간 구출 작전)",
        "codex_score": 99,
        "profile_score": 99,
        "codex_angle": "Hồ Sơ Thật 100%: Vương Lập Hoa & Vụ Bắt Cóc Ngôi Sao Ngô Nhược Phủ Năm 2004 (吾先生原案) — Cuộc Đột Kích 3 Giây Của Đặc Nhiệm Bắc Kinh Trước Khi Kẻ Chủ Mưu Kịp Chạm Vào Chốt Nổ",
        "codex_reasons": [
            "Nguyên mẫu đời thực 100% của bộ phim điện ảnh kinh điển 'Giải cứu Ngô tiên sinh (解救吾先生)', toàn bộ quá trình đặc nhiệm phá cửa giải cứu và thẩm vấn đều được camera cảnh sát Bắc Kinh ghi hình thực tế",
            "Tòa án Nhân dân Cấp cao Bắc Kinh tuyên án tử hình và thi hành án đối với Vương Lập Hoa, Vương Khánh Hiểu, Đổng Lập Dân tháng 9/2005"
        ],
        "opening_hook": "텔레비전 드라마에서 수없이 강력계 형사 반장 역할을 맡았던 유명 배우 우뤄푸가 새벽 두 시 베이징 번화가에서 경찰 배지를 내민 세 남자에게 포위됐습니다. 수갑이 채워져 차에 타는 순간 그는 눈앞의 남자들이 경찰이 아니라 이백만 위안을 노린 왕리화 일당임을 직감했습니다.",
        "note": "📋 【Hồ sơ vụ án: trọng án giả danh cảnh sát hình sự bắt cóc tống tiền liên hoàn (sát hại con tin Vương Bằng và bắt cóc diễn viên Ngô Nhược Phủ đòi 2 triệu tệ) · 22 giờ đặc nhiệm Bắc Kinh giải cứu sống và Tòa án Bắc Kinh tuyên án tử hình Vương Lập Hoa】 Hồ sơ thật 100% Chuyên án 2·3 giải cứu diễn viên Ngô Nhược Phủ tại Bắc Kinh (北京2004年吴若甫绑架案 — Vương Lập Hoa 王立华, Vương Khánh Hiểu 王庆晓, Đổng Lập Dân 董立民): Rạng sáng 3/2/2004, băng nhóm Vương Lập Hoa đóng giả cảnh sát bắt cóc Ngô Nhược Phủ đòi 2 triệu NDT và mang theo lựu đạn; Công an Bắc Kinh định vị chiếc xe phát sóng di động, bắt sống Vương Lập Hoa sau 22 giờ, giải cứu toàn vẹn 2 con tin và Tòa án Bắc Kinh tuyên án tử hình.",
        "hook_archetype": "countdown_system_breach"
    },
    {
        "id": "vio_cn_liaoning_shenyang_liuyong_retrial",
        "topic_stream": "major_violent_crime",
        "case_real_name_zh": "辽宁沈阳嘉阳集团亿万富豪涉黑大案与最高院首次提审改判死刑案 — 刘涌 (1995–2003)",
        "archival_search_keywords_zh": [
            "沈阳 刘涌 最高人民法院 提审 今日说法",
            "嘉阳集团 刘涌 涉黑大案 纪实",
            "锦州 刘涌 终审 死刑 央视"
        ],
        "recommended_vox_verbs": [
            "SPLIT_PARADOX",
            "NETWORK_GRAPH",
            "ALIBI_SHATTER"
        ],
        "title": "[중국 실화 사건] 2심에서 기적처럼 최고형을 면한 억대 재벌을 대법관이 직접 교도소로 찾아가 재심판한 날 | 선양 류융 사건 ([Vụ Án Có Thật ở Trung Quốc] Tỷ phú thoát án tử hình ở phiên phúc thẩm và ngày Thẩm phán Tòa Tối cao đích thân tới tận nơi mở phiên tòa đặc biệt | Đại án Lưu Dũng Thẩm Dương)",
        "topic_anchor": "[중국 실화 사건] 2심에서 기적처럼 최고형을 면한 억대 재벌을 대법관이 직접 교도소로 찾아가 재심판한 날 | 선양 류융 사건",
        "winner_cluster": "Luồng 2 · Lần Đầu Tiên Tòa Án Tối Cao Trung Quốc Trực Tiếp Đề Thẩm (提审) Lật Ngược Bản Án Giảm Hình Phạt Của Tỷ Phú Ngầm (선양 류융 대법원 직접 재판 사건)",
        "codex_score": 99,
        "profile_score": 99,
        "codex_angle": "Hồ Sơ Thật 100%: Lưu Dũng (刘涌, Thẩm Dương 1995–2003) — Từ Chủ Tịch Tập Đoàn Gia Dương Kiêm Đại Biểu Nhân Dân Đến Phiên Tòa Đề Thẩm Lịch Sử Tại Cẩm Châu Ngày 22/12/2003",
        "codex_reasons": [
            "Vụ án lịch sử chưa từng có tiền lệ từ năm 1949 khi Tòa án Nhân dân Tối cao Trung Quốc trực tiếp cử Hội đồng thẩm phán xuống Cẩm Châu xét xử lại (提审) một vụ án hình sự thông thường và thi hành án tử hình ngay trong ngày tuyên án",
            "Tư liệu truyền hình CCTV về đế chế Gia Dương, vụ bắt giữ ở biên giới Hắc Hà và phiên tòa Tối cao cực kỳ đồ sộ"
        ],
        "opening_hook": "일심에서 최고형을 선고받았던 선양의 칠억 위안대 재벌 회장 류융이 이심 법정에서 돌연 최고형 유예로 감형되자 중국 전역이 발칵 뒤집혔습니다. 그러자 베이징의 최고인민법원이 건국 이래 처음으로 형사 사건 직접 재판권을 발동해 대법관들을 특별 열차에 태워 진저우로 내려보냈습니다.",
        "note": "📋 【Hồ sơ vụ án: đại án tập đoàn ngầm Gia Dương do đại biểu nhân dân Lưu Dũng cầm đầu tại Thẩm Dương · Tòa án Nhân dân Tối cao lần đầu tiên trong lịch sử trực tiếp đề thẩm (提审) tuyên án tử hình thi hành ngay ngày 22/12/2003】 Hồ sơ thật 100% Đại án Lưu Dũng tại Thẩm Dương, Liêu Ninh (辽宁沈阳刘涌特大涉黑案与最高院提审案, 1995–2003): Lưu Dũng dùng vỏ bọc Chủ tịch Tập đoàn Gia Dương tài trợ cảnh sát và mua chuộc quan chức để thao túng thị trường Thẩm Dương, rồi trốn lên cửa khẩu Hắc Hà định vượt biên sang Nga; sau khi Tòa Cấp cao tỉnh Liêu Ninh giảm án xuống tử hình treo tháng 8/2003, Tòa án Nhân dân Tối cao đã trực tiếp mở phiên tòa đề thẩm tại Cẩm Châu tuyên án tử hình và thi hành án ngay trong ngày.",
        "hook_archetype": "scale_absurdity_collision"
    },
    {
        "id": "vio_cn_shanghai_fudan_linsenhao_water",
        "topic_stream": "major_violent_crime",
        "case_real_name_zh": "上海复旦大学医学院研究生饮水机N-二甲基亚硝胺投毒案 — 林森浩 (2013–2015)",
        "archival_search_keywords_zh": [
            "复旦投毒案 林森浩 今日说法",
            "林森浩 黄洋 庭审现场 央视",
            "N-二甲基亚硝胺 复旦 侦破纪实"
        ],
        "recommended_vox_verbs": [
            "SINGLE_EVIDENCE_AUTOPSY",
            "MICRO_TRACE_MATCH",
            "ALIBI_SHATTER"
        ],
        "title": "[중국 실화 사건] 병원 모든 정밀 검사에서 원인을 못 찾던 명문 의대생의 위독 상태와 익명 문자 한 통의 반전 | 상하이 린썬하오 사건 ([Vụ Án Có Thật ở Trung Quốc] Nghiên cứu sinh y khoa nguy kịch không rõ nguyên nhân và tin nhắn ẩn danh lật tẩy người bạn cùng phòng | Vụ án Lâm Sâm Hạo Thượng Hải)",
        "topic_anchor": "[중국 실화 사건] 병원 모든 정밀 검사에서 원인을 못 찾던 명문 의대생의 위독 상태와 익명 문자 한 통의 반전 | 상하이 린썬하오 사건",
        "winner_cluster": "Luồng 2 · Tin Nhắn Nhắc Tên Hóa Chất Thí Nghiệm Hiếm & Cuộc Đấu Trí Pháp Y Trong Ký Túc Xá Y Khoa (상하이 푸단대 린썬하오 사건)",
        "codex_score": 99,
        "profile_score": 99,
        "codex_angle": "Hồ Sơ Thật 100%: Lâm Sâm Hạo (林森浩, Đại Học Phúc Đán 2013–2015) — Khi Chính Người Bạn Cùng Phòng Trực Tiếp Cầm Phiếu Siêu Âm Khám Cho Nạn Nhân Trước Khi Lộ Diện",
        "codex_reasons": [
            "Một trong những vụ án trí thức chấn động nhất Trung Quốc hiện đại, toàn bộ video thẩm vấn, phỏng vấn trong trại giam và phiên tòa của Lâm Sâm Hạo được CCTV phát sóng chi tiết",
            "Tòa án Nhân dân Cấp cao Thượng Hải và Tòa án Tối cao phê chuẩn thi hành án tử hình Lâm Sâm Hạo tháng 12/2015"
        ],
        "opening_hook": "상하이 최고 명문 의과대학 기숙사에서 물 한 모금을 마신 대학원생 황양이 갑자기 급성 간부전으로 쓰러졌습니다. 최고의 의사들이 모여 일주일 내내 원인을 찾지 못해 헤매던 그때, 선배의 휴대폰으로 기숙사 정수기와 실험실 시약 이름을 지목하는 짧은 문자 메시지 한 통이 도착했습니다.",
        "note": "📋 【Hồ sơ vụ án: trọng án nghiên cứu sinh y khoa Đại học Phúc Đán Lâm Sâm Hạo bỏ hóa chất thí nghiệm N-Nitrosodimethylamine vào bình nước uống ký túc xá · phát hiện nhờ tin nhắn chỉ điểm chất độc · Tòa án Tối cao phê chuẩn tử hình năm 2015】 Hồ sơ thật 100% Vụ án tại Học viện Y khoa Đại học Phúc Đán, Thượng Hải (上海复旦大学林森浩投毒案, 2013–2015): Ngày 31/3/2013, Lâm Sâm Hạo lấy hợp chất N-二甲基亚硝胺 từ phòng thí nghiệm đổ vào bình nước uống trong phòng ký túc xá 421 khiến bạn cùng phòng Hoàng Dương tử vong; khi Hoàng Dương nhập viện, Lâm Sâm Hạo vẫn bình thản trực tiếp siêu âm cho bạn và xóa lịch sử tìm kiếm máy tính trước khi bị Công an Thượng Hải bắt giữ và tòa tuyên án tử hình.",
        "hook_archetype": "micro_forensic_anomaly"
    },
    {
        "id": "vio_cn_zhejiang_hangzhou_mohuanjing_fire",
        "topic_stream": "major_violent_crime",
        "case_real_name_zh": "浙江杭州蓝色钱江高档公寓保姆赌博盗窃纵火案 — 莫焕晶 (2017–2018)",
        "archival_search_keywords_zh": [
            "杭州保姆纵火案 莫焕晶 今日说法",
            "蓝色钱江 莫焕晶 庭审 死刑 央视",
            "莫焕晶 赌博 侦破纪实"
        ],
        "recommended_vox_verbs": [
            "CRASH_TIMELINE",
            "ALIBI_SHATTER",
            "LEDGER_DIFF_SCRUB"
        ],
        "title": "[중국 실화 사건] 도박 빚을 갚으려 주인집 거실에 몰래 불을 지르고 '구출 영웅' 연극을 꾸민 입주 가사도우미 | 항저우 모환징 사건 ([Vụ Án Có Thật ở Trung Quốc] Bảo mẫu lén đốt phòng khách chung cư hạng sang lúc 5 giờ sáng để diễn kịch 'anh hùng dập lửa' xin tiền trả nợ cờ bạc | Đại án Mạc Hoán Tinh)",
        "topic_anchor": "[중국 실화 사건] 도박 빚을 갚으려 주인집 거실에 몰래 불을 지르고 '구출 영웅' 연극을 꾸민 입주 가사도우미 | 항저우 모환징 사건",
        "winner_cluster": "Luồng 2 · Chiếc Đồng Hồ Patek Philippe Bị Đem Cầm Cố & Màn Kịch Tự Đốt Tự Dập Lúc 4h55 Sáng Tầng 18 (항저우 모환징 가사도우미 사건)",
        "codex_score": 98,
        "profile_score": 98,
        "codex_angle": "Hồ Sơ Thật 100%: Mạc Hoán Tinh (莫焕晶, Hàng Châu 2017–2018) — Khi Lịch Sử Tìm Kiếm 'Bật Lửa Tự Nổ' Lúc Rạng Sáng Đập Tan Lời Khai Giả Trước Tòa",
        "codex_reasons": [
            "Vụ án chấn động toàn Trung Quốc năm 2017–2018 với hàng trăm bản tin truyền hình CCTV, video phiên tòa xét xử công khai tại Hàng Châu",
            "Tòa án Nhân dân Trung cấp Hàng Châu và Tòa án Tối cao phê chuẩn thi hành án tử hình Mạc Hoán Tinh tháng 9/2018"
        ],
        "opening_hook": "새벽 네 시 오십오 분, 항저우 최고급 아파트 십팔 층에서 연기가 피어오르자 입주 가사도우미 모환징만 전용 엘리베이터를 타고 혼자 무사히 건물을 빠져나왔습니다. 경찰 앞에서는 집주인을 구하려다 실패했다며 눈물을 흘렸지만, 그녀의 스마트폰 검색 기록에는 소름 돋는 네 글자가 남아 있었습니다.",
        "note": "📋 【Hồ sơ vụ án: trọng án bảo mẫu Mạc Hoán Tinh trộm đồng hồ Patek Philippe đánh bạc trực tuyến rồi tự châm lửa phòng khách tầng 18 nhằm diễn kịch dập lửa lập công vay tiền, gây tử vong 4 mẹ con chủ nhà · Tòa án Hàng Châu tuyên án tử hình】 Hồ sơ thật 100% Vụ án tại khu căn hộ Lam Sắc Tiền Giang, Hàng Châu, Chiết Giang (浙江杭州莫焕晶放火盗窃案, 2017–2018): Được chủ nhà tin tưởng trả lương cao và cho vay 114.000 NDT, Mạc Hoán Tinh vẫn lén lấy đồng hồ đắt tiền đi cầm cố nướng vào cờ bạc online; rạng sáng 22/6/2017, ả dùng bật lửa đốt sách trên sofa phòng khách định tự dập lửa để xin thêm tiền nhưng lửa bùng lớn khiến ả bỏ chạy một mình, bị Tòa án Hàng Châu tuyên án tử hình.",
        "hook_archetype": "double_life_unmasking"
    },
    {
        "id": "vio_cn_shanghai_zhuxiaodong_105d_wechat",
        "topic_stream": "major_violent_crime",
        "case_real_name_zh": "上海虹口区丈夫伪造妻子微信聊天记录105天完美假象案 — 朱晓东 (2016–2020)",
        "archival_search_keywords_zh": [
            "上海 朱晓东 105天 今日说法",
            "朱晓东 杨俪萍 庭审 死刑 央视",
            "虹口 朱晓东 伪造微信 纪实"
        ],
        "recommended_vox_verbs": [
            "ALIBI_SHATTER",
            "LEDGER_DIFF_SCRUB",
            "SPLIT_PARADOX"
        ],
        "title": "[중국 실화 사건] 105일 동안 오직 문자 메시지로만 안부를 전해온 딸과 장인 생일 전날 무너진 남편의 연극 | 상하이 주샤오둥 사건 ([Vụ Án Có Thật ở Trung Quốc] Cô con gái suốt 105 ngày chỉ nhắn tin WeChat không gọi thoại và vở kịch của người chồng sụp đổ trước sinh nhật bố vợ | Vụ án Chu Hiểu Đông)",
        "topic_anchor": "[중국 실화 사건] 105일 동안 오직 문자 메시지로만 안부를 전해온 딸과 장인 생일 전날 무너진 남편의 연극 | 상하이 주샤오둥 사건",
        "winner_cluster": "Luồng 2 · 105 Ngày Giả Giọng Vợ Nhắn Tin WeChat Cho Gia Đình & Bản Sao Kê Thẻ Tín Dụng Phơi Bày Sự Thật (상하이 주샤오둥 105일 위챗 트릭 사건)",
        "codex_score": 98,
        "profile_score": 98,
        "codex_angle": "Hồ Sơ Thật 100%: Chu Hiểu Đông (朱晓东, Thượng Hải 2016–2020) — 105 Ngày Đóng Hai Vai Trên Điện Thoại Và Phán Quyết Tử Hình Của Tòa Án Thượng Hải",
        "codex_reasons": [
            "Vụ án tâm lý - gia đình nổi tiếng bậc nhất trên CCTV 今日说法 / 一线, tập trung 100% vào màn kịch 105 ngày giả mạo tin nhắn WeChat và sao kê tài chính",
            "Tòa án Nhân dân Trung cấp số 2 Thượng Hải tuyên án tử hình và thi hành án đối với Chu Hiểu Đông tháng 6/2020"
        ],
        "opening_hook": "성실하던 초등학교 교사 양리핑이 갑자기 사직서를 내고 남편과 홍콩으로 여행을 떠났다는 위챗 메시지를 보냈습니다. 그날부터 백오 일 동안 그녀는 부모님과 친구들에게 꾸준히 안부 문자를 보냈지만, 단 한 번도 전화 통화나 영상통화는 받지 못한다며 핑계를 댔습니다.",
        "note": "📋 【Hồ sơ vụ án: trọng án người chồng Chu Hiểu Đông sát hại vợ tại quận Hồng Khẩu, Thượng Hải rồi cầm điện thoại giả giọng vợ nhắn tin WeChat với bố mẹ vợ suốt 105 ngày · Tòa án Thượng Hải tuyên án tử hình】 Hồ sơ thật 100% Vụ án Chu Hiểu Đông tại Thượng Hải (上海虹口区朱晓东案, 2016–2020): Sau khi sát hại vợ là giáo viên tiểu học Dương Lệ Bình ngày 18/10/2016, Chu Hiểu Đông dùng điện thoại của vợ nhắn tin WeChat giả vờ đang đi du lịch suốt hơn 3 tháng và quẹt thẻ tín dụng của vợ tiêu xài 150.000 NDT; đến ngày 1/2/2017 là đại thọ 60 tuổi của bố vợ không thể tiếp tục viện cớ vắng mặt, Chu Hiểu Đông buộc phải thú nhận và bị Tòa án Thượng Hải thi hành án tử hình.",
        "hook_archetype": "chilling_verbatim_line"
    },
    {
        "id": "vio_cn_chongqing_zhangbo_yechengchen_15f",
        "topic_stream": "major_violent_crime",
        "case_real_name_zh": "重庆南岸区锦江华府15楼伪造意外案与1.7万条删除微信恢复纪实 — 张波·叶诚尘 (2020–2024)",
        "archival_search_keywords_zh": [
            "重庆 张波 叶诚尘 1.7万条微信 今日说法",
            "锦江华府 张波 庭审 死刑 央视",
            "重庆姐弟坠亡案 电子物证恢复"
        ],
        "recommended_vox_verbs": [
            "ALIBI_SHATTER",
            "LEDGER_DIFF_SCRUB",
            "FORENSIC_ZOOM_CHAIN"
        ],
        "title": "[중국 실화 사건] 아파트 15층 사고 직후 바닥을 치며 통곡하던 아버지의 휴대폰에서 복원된 17,000건의 삭제 메시지 | 충칭 장보 사건 ([Vụ Án Có Thật ở Trung Quốc] 17.000 tin nhắn đã xóa khôi phục từ điện thoại người cha ngồi gào khóc đập đầu dưới sân chung cư tầng 15 | Đại án Trương Ba Trùng Khánh)",
        "topic_anchor": "[중국 실화 사건] 아파트 15층 사고 직후 바닥을 치며 통곡하던 아버지의 휴대폰에서 복원된 17,000건의 삭제 메시지 | 충칭 장보 사건",
        "winner_cluster": "Luồng 2 · Màn Kịch Gào Khóc Dưới Sân Chung Cư & 17.000 Dòng Tin Nhắn Đã Xóa Phơi Bày Âm Mưu Lạnh Gáy (충칭 장보·예청천 1.7만 건 위챗 복원 사건)",
        "codex_score": 99,
        "profile_score": 99,
        "codex_angle": "Hồ Sơ Thật 100%: Trương Ba · Diệp Thành Trần (重庆张波·叶诚尘案, 2020–2024) — Khi Pháp Y Kỹ Thuật Số Khôi Phục Toàn Bộ Dữ Liệu Điện Thoại Đã Xóa Trắng Để Lật Tẩy Vở Kịch Tai Nạn",
        "codex_reasons": [
            "Một trong những vụ án được theo dõi nhiều nhất Trung Quốc giai đoạn 2020–2024, màn đối chiếu 17.000 tin nhắn WeChat khôi phục cực hợp cho bàn biên tập cắt dán Vox",
            "Tòa án Nhân dân Tối cao phê chuẩn và thi hành án tử hình cả Trương Ba lẫn Diệp Thành Trần ngày 31/1/2024"
        ],
        "opening_hook": "잠옷 바람으로 아파트 화단으로 달려 내려와 머리를 벽에 찧으며 오열하던 아버지 장보의 모습에 이웃 주민들까지 눈시울을 붉혔습니다. 모두가 내가 잠든 사이 일어난 비극적인 추락 사고라 믿었지만, 디지털 포렌식 팀이 초기화된 두 대의 스마트폰에서 일만 칠천 건의 삭제된 대화 기록을 복원해냈습니다.",
        "note": "📋 【Hồ sơ vụ án: trọng án Trương Ba và nhân tình Diệp Thành Trần thông đồng ngụy tạo vụ rơi lầu tầng 15 của 2 con nhỏ tại Trùng Khánh · công an khôi phục 17.000 tin nhắn WeChat đã xóa · Tòa án Tối cao thi hành án tử hình cả 2 bị cáo năm 2024】 Hồ sơ thật 100% Vụ án tại chung cư Cẩm Giang Hoa Phủ, quận Nam Ngạn, Trùng Khánh (重庆张波·叶诚尘案, 2020–2024): Ngày 2/11/2020, Trương Ba đẩy hai con ruột từ cửa sổ tầng 15 rồi chạy xuống sân đóng kịch gào khóc; Cảnh sát Trùng Khánh thu giữ điện thoại, dùng công nghệ pháp y số khôi phục hơn 17.000 tin nhắn WeChat đã xóa sạch giữa Trương Ba và Diệp Thành Trần bàn bạc kế hoạch ngụy tạo tai nạn, đưa cả hai ra thi hành án tử hình ngày 31/1/2024.",
        "hook_archetype": "chilling_verbatim_line"
    },
    {
        "id": "vio_cn_jiangsu_yuxiaodong_thai_cliff_34m",
        "topic_stream": "major_violent_crime",
        "case_real_name_zh": "江苏孕妇泰国乌汶帕登国家公园34米悬崖坠落生还逆转案 — 俞晓东·王暖暖 (2019–2023)",
        "archival_search_keywords_zh": [
            "泰国坠崖孕妇 王暖暖 俞晓东 今日说法",
            "帕登国家公园 34米悬崖 俞晓东 审判",
            "消失的她 原型 王暖暖 央视采访"
        ],
        "recommended_vox_verbs": [
            "ALIBI_SHATTER",
            "SPLIT_PARADOX",
            "GEO_VECTOR_PURSUIT"
        ],
        "title": "[중국 실화 사건] 34m 절벽 아래에서 기적처럼 살아 돌아온 아내의 중환자실 침대 곁을 밤낮으로 지킨 남편의 본색 | 타이 왕놘놘 절벽 사건 ([Vụ Án Có Thật ở Trung Quốc] Sống sót kỳ diệu dưới vách đá cao 34m và bộ mặt thật của người chồng túc trực đêm ngày bên giường hồi sức | Vụ án Vương Noãn Noãn)",
        "topic_anchor": "[중국 실화 사건] 34m 절벽 아래에서 기적처럼 살아 돌아온 아내의 중환자실 침대 곁을 밤낮으로 지킨 남편의 본색 | 타이 왕놘놘 절벽 사건",
        "winner_cluster": "Luồng 2 · Sống Sót Kỳ Diệu Dưới Vực Đá 34 Mét & Cuộc Ghi Âm Bí Mật Ngay Trên Giường Hồi Sức ICU (왕놘놘·위샤오둥 34m 절벽 생환 역전 사건)",
        "codex_score": 99,
        "profile_score": 99,
        "codex_angle": "Hồ Sơ Thật 100%: Vương Noãn Noãn & Du Hiểu Đông (泰国乌汶34米悬崖案, 2019–2023) — Khi Nạn Nhân Giả Vờ Mất Trí Nhớ Tạm Thời Để Tự Thu Thập Bằng Chứng Ngay Trước Mặt Thủ Phạm",
        "codex_reasons": [
            "Vụ án có thật 100% nổi tiếng khắp châu Á (được CCTV 今日说法 phỏng vấn độc quyền nạn nhân sống sót Vương Noãn Noãn), 0% tử vong và kịch tính đấu trí cực đại",
            "Tòa án Tối cao Thái Lan tuyên phạt Du Hiểu Đông 33 năm 4 tháng tù giam năm 2023"
        ],
        "opening_hook": "삼십사 미터 높이의 깎아지른 절벽 아래에서 온몸의 뼈 열일곱 군데가 부러진 채 기적적으로 구조된 사업가 왕놘놘. 그녀가 중환자실에서 눈을 떴을 때 침대 머리맡을 지키고 서서 조용히 입단속을 속삭인 사람은 다름 아닌 그녀를 절벽 끝으로 데려갔던 남편 위샤오둥이었습니다.",
        "note": "📋 【Hồ sơ vụ án: trọng án người chồng Du Hiểu Đông đẩy vợ đang mang thai xuống vách đá cao 34m tại Công viên Quốc gia Pha Taem nhằm chiếm đoạt tài sản trả nợ cờ bạc · nạn nhân kỳ diệu sống sót và ghi âm vạch mặt chồng · Tòa Tối cao tuyên phạt 33 năm 4 tháng tù】 Hồ sơ thật 100% Vụ án tại Công viên Quốc gia Pha Taem, Ubon Ratchathani (Thái Lan) của nữ doanh nhân Giang Tô Vương Noãn Noãn (江苏孕妇泰国坠崖案 — Du Hiểu Đông 俞晓东, 2019–2023): Ngày 9/6/2019, Du Hiểu Đông dẫn vợ tới vách đá vắng người rồi đẩy cô xuống vực sâu 34m; khi Vương Noãn Noãn sống sót kỳ diệu, Du Hiểu Đông túc trực 24/24 ở phòng ICU để khống chế lời khai, nhưng cô đã mưu trí nhờ bạn bè ghi âm cuộc đối thoại thừa nhận tội ác của hắn để giao nộp cho tòa án.",
        "hook_archetype": "chilling_verbatim_line"
    },
    {
        "id": "vio_cn_tianjin_zhangyifan_phuket_insurance",
        "topic_stream": "major_violent_crime",
        "case_real_name_zh": "天津男子泰国普吉岛伪造泳池意外骗保3000万元跨国侦破案 — 张轶凡 (2018–2020)",
        "archival_search_keywords_zh": [
            "天津 普吉岛 骗保 3000万 张轶凡 今日说法",
            "张轶凡 泰国 庭审 央视新闻",
            "跨国骗保案 张轶凡 侦破纪实"
        ],
        "recommended_vox_verbs": [
            "LEDGER_DIFF_SCRUB",
            "ALIBI_SHATTER",
            "SINGLE_EVIDENCE_AUTOPSY"
        ],
        "title": "[중국 실화 사건] 풀빌라 휴가 중 일어난 안타까운 사고라더니 집 서랍 속에서 쏟아져 나온 3,000만 위안 비밀 보험증권 11장 | 톈진 장이판 사건 ([Vụ Án Có Thật ở Trung Quốc] Báo tin vợ gặp tai nạn ở biệt thự nghỉ dưỡng nhưng trong ngăn kéo ở nhà lộ ra 11 hợp đồng bảo hiểm 30 triệu tệ | Đại án Trương Dật Phàm)",
        "topic_anchor": "[중국 실화 사건] 풀빌라 휴가 중 일어난 안타까운 사고라더니 집 서랍 속에서 쏟아져 나온 3,000만 위안 비밀 보험증권 11장 | 톈진 장이판 사건",
        "winner_cluster": "Luồng 2 · 11 Hợp Đồng Bảo Hiểm 30 Triệu Tệ Mua Dồn Dập Trong 2 Tháng & Chữ Ký Giả Trên Hồ Sơ Thụ Hưởng (톈진 장이판 3,000만 위안 보험증권 사건)",
        "codex_score": 98,
        "profile_score": 98,
        "codex_angle": "Hồ Sơ Thật 100%: Trương Dật Phàm (张轶凡, Thiên Tân 2018–2020) — Khi Cục Cảnh Sát Kinh Tế Thiên Tân Và Pháp Y Quốc Tế Khớp Nối 11 Hợp Đồng Bảo Hiểm Ký Giả",
        "codex_reasons": [
            "Vụ án trục lợi bảo hiểm xuyên quốc gia nổi tiếng nhất trên CCTV 今日说法, cực hợp với bàn biên tập đối chiếu hợp đồng LEDGER_DIFF_SCRUB",
            "Tòa án tuyên án chung thân / tử hình đối với Trương Dật Phàm sau hơn 1 năm xét xử"
        ],
        "opening_hook": "결혼기념일 여행을 떠난 지 이틀 만에 사위 장이판에게서 딸이 풀빌라에서 불의의 사고를 당했다는 급보가 날아왔습니다. 하지만 슬픔에 잠긴 부모님이 사위의 서재를 정리하던 순간, 출발 직전 두 달 사이에 열한 개 보험회사에서 몰래 가입된 삼천만 위안짜리 생명보험 증권 다발이 쏟아져 나왔습니다.",
        "note": "📋 【Hồ sơ vụ án: đại án Trương Dật Phàm giả mạo chữ ký vợ mua 11 hợp đồng bảo hiểm nhân thọ trị giá hơn 30 triệu tệ rồi đưa sang biệt thự Phuket ngụy tạo tai nạn · cảnh sát Trung Quốc – Thái Lan phối hợp điều tra và tòa tuyên án nghiêm khắc】 Hồ sơ thật 100% Chuyên án lừa đảo bảo hiểm 30 triệu NDT của Trương Dật Phàm tại Thiên Tân – Phuket (天津男子张轶凡泰国普吉岛3000万骗保案, 2018–2020): Đã nghỉ việc ngân hàng từ lâu nhưng giả vờ đi làm mỗi ngày, Trương Dật Phàm âm thầm mua hơn 10 gói bảo hiểm tử kỳ trị giá hơn 30 triệu NDT đứng tên mình thụ hưởng rồi đưa vợ đi du lịch tháng 10/2018; bị gia đình nạn nhân và cảnh sát hai nước vạch trần toàn bộ chữ ký giả và dữ liệu tài chính.",
        "hook_archetype": "locked_room_vault_paradox"
    },
    {
        "id": "vio_cn_hebei_wangshujin_nieshubin_21y",
        "topic_stream": "major_violent_crime",
        "case_real_name_zh": "河北石家庄西郊玉米地1994年悬案一串钥匙口供与21年跨省平反案 — 王书金·聂树斌 (1994–2016)",
        "archival_search_keywords_zh": [
            "王书金 聂树斌 一串钥匙 今日说法",
            "最高人民法院 聂树斌再审 无罪 央视",
            "石家庄 玉米地案 王书金 死刑"
        ],
        "recommended_vox_verbs": [
            "SINGLE_EVIDENCE_AUTOPSY",
            "DUAL_ERA_LOCK",
            "ALIBI_SHATTER"
        ],
        "title": "[중국 실화 사건] 이미 범인이 잡혀 종결된 11년 전 사건 현장의 '열쇠 꾸러미 위치'를 정확히 말한 낯선 수배범 | 왕수진·녜수빈 21년 사건 ([Vụ Án Có Thật ở Trung Quốc] Kẻ truy nã bị bắt ở tỉnh khác bất ngờ tả chính xác vị trí chùm chìa khóa của vụ án đã khép lại 11 năm trước | Đại án Vương Thư Kim – Nhiếp Thụ Bân)",
        "topic_anchor": "[중국 실화 사건] 이미 범인이 잡혀 종결된 11년 전 사건 현장의 '열쇠 꾸러미 위치'를 정확히 말한 낯선 수배범 | 왕수진·녜수빈 21년 사건",
        "winner_cluster": "Luồng 2 · Chùm Chìa Khóa Nằm Sát Chân Nạn Nhân Chỉ Chân Hung Mới Biết & 21 Năm Minh Oan Lịch Sử (왕수진·녜수빈 열쇠 꾸러미 사건)",
        "codex_score": 99,
        "profile_score": 99,
        "codex_angle": "Hồ Sơ Thật 100%: Vương Thư Kim & Kỳ Án 21 Năm Minh Oan Cho Nhiếp Thụ Bân (1994–2016) — Khi Chi Tiết 'Chùm Chìa Khóa Rơi Trên Đất' Mở Ra Cuộc Phúc Thẩm Lịch Sử Của Tòa Tối Cao",
        "codex_reasons": [
            "Đại án tư pháp chấn động nhất lịch sử Trung Quốc hiện đại (cùng với vụ Hô Cách Cát Lặc Đồ), được Tòa án Nhân dân Tối cao tuyên vô tội năm 2016 và thi hành án tử hình Vương Thư Kim năm 2021",
            "Mỏ neo vật chứng 'chùm chìa khóa tại hiện trường năm 1994' cực hợp cho SINGLE_EVIDENCE_AUTOPSY & DUAL_ERA_LOCK"
        ],
        "opening_hook": "2005년 허난성에서 붙잡힌 떠돌이 수배범 왕수진이 십일 년 전 스자좡 외곽 옥수수밭 사건을 자신이 저질렀다며 현장 바닥에 떨어져 있던 열쇠 꾸러미의 위치까지 정확히 진술했습니다. 문제는 그 사건이 이미 십 년 전에 다른 청년의 유죄 판결로 완전히 종결된 상태였다는 점이었습니다.",
        "note": "📋 【Hồ sơ vụ án: kỳ án lịch sử tư pháp Trung Quốc 21 năm tại Thạch Gia Trang, Hà Bắc · hung thủ thật Vương Thư Kim bị bắt năm 2005 khai chính xác chi tiết chùm chìa khóa hiện trường · Tòa án Tối cao minh oan cho Nhiếp Thụ Bân năm 2016 và thi hành án tử hình Vương Thư Kim năm 2021】 Hồ sơ thật 100% Vụ án Vương Thư Kim – Nhiếp Thụ Bân (河北王书金案与聂树斌再审平反案, 1994–2021): Tháng 1/2005, Vương Thư Kim bị bắt tại Hà Nam đã chủ động dẫn cảnh sát tới hiện trường vụ án năm 1994 tại Thạch Gia Trang và nêu đúng chi tiết chùm chìa khóa rơi sát chân nạn nhân chưa từng công bố; Tòa án Nhân dân Tối cao giao Tòa Cấp cao Sơn Đông thẩm tra chéo, tuyên Nhiếp Thụ Bân vô tội tháng 12/2016 và thi hành án tử hình Vương Thư Kim tháng 2/2021.",
        "hook_archetype": "cold_archive_match"
    },
    {
        "id": "vio_cn_shaanxi_hanzhong_zhangkoukou_48h",
        "topic_stream": "major_violent_crime",
        "case_real_name_zh": "陕西汉中南郑区除夕重案48小时山林搜捕与两代恩怨审判纪实 — 张扣扣 (1996–2019)",
        "archival_search_keywords_zh": [
            "陕西汉中 张扣扣 庭审现场 央视",
            "张扣扣 除夕案 今日说法",
            "汉中中院 张扣扣 死刑 纪实"
        ],
        "recommended_vox_verbs": [
            "DUAL_ERA_LOCK",
            "RADIAL_TIME_PRESSURE",
            "GEO_VECTOR_PURSUIT"
        ],
        "title": "[중국 실화 사건] 22년 전 사건의 기억을 품고 특전사 제대 후 고향으로 돌아온 남자의 48시간 행적 | 산시성 장커우커우 사건 ([Vụ Án Có Thật ở Trung Quốc] Mang ký ức vụ án 22 năm trước, gã cựu binh đặc nhiệm trở về quê hương vào trưa 30 Tết và 48 giờ truy bắt | Vụ án Trương Khấu Khấu)",
        "topic_anchor": "[중국 실화 사건] 22년 전 사건의 기억을 품고 특전사 제대 후 고향으로 돌아온 남자의 48시간 행적 | 산시성 장커우커우 사건",
        "winner_cluster": "Luồng 2 · Hồ Sơ Lưu Trữ Năm 1996 & 48 Giờ Vây Bắt Trong Rừng Núi Tần Ba Trước Khi Ra Đầu Thú Lúc Rạng Sáng (산시성 한중 장커우커우 사건)",
        "codex_score": 98,
        "profile_score": 98,
        "codex_angle": "Hồ Sơ Thật 100%: Trương Khấu Khấu (张扣扣, Hán Trung, Thiểm Tây 1996–2019) — 8 Giờ Tranh Luận Pháp Lý Được Phát Sóng Trực Tiếp Tại Tòa Án Hán Trung",
        "codex_reasons": [
            "Phiên tòa xét xử Trương Khấu Khấu được Tòa án Nhân dân Trung cấp Hán Trung phát trực tiếp toàn bộ quá trình tranh tụng và lên sóng đặc biệt trên CCTV 庭审现场 / 今日说法",
            "Tòa án Nhân dân Tối cao phê chuẩn thi hành án tử hình Trương Khấu Khấu tháng 7/2019"
        ],
        "opening_hook": "열세 살이던 1996년 어머니를 잃은 소년 장커우커우는 22년 동안 단 한 번도 그날의 사건 기록을 잊지 않았습니다. 2018년 설날 전날 낮, 모자와 마스크로 얼굴을 가린 그가 고향 마을 골목에 다시 나타났고, 곧이어 사십팔 시간의 산악 수색 작전이 시작됐습니다.",
        "note": "📋 【Hồ sơ vụ án: trọng án ngày 30 Tết năm 2018 tại Hán Trung, Thiểm Tây tước đoạt 3 sinh mạng do ân oán từ vụ án năm 1996 · 48 giờ vây bắt trên núi Tần Ba · Tòa án Hán Trung và Tòa Tối cao tuyên án tử hình Trương Khấu Khấu】 Hồ sơ thật 100% Vụ án Trương Khấu Khấu tại quận Nam Trịnh, Hán Trung, Thiểm Tây (陕西汉中张扣扣案, 1996–2019): Mang mối hận từ vụ xô xát khiến mẹ ruột tử vong năm 1996 khi mới 13 tuổi, Trương Khấu Khấu sau khi xuất ngũ và đi làm xa đã trở về quê hương gây án vào trưa 15/2/2018 (30 Tết), lẩn trốn trong núi 48 giờ rồi tới đồn công an đầu thú; bị Tòa án Hán Trung tuyên án tử hình và thi hành án tháng 7/2019.",
        "hook_archetype": "last_ordinary_routine"
    },
    {
        "id": "vio_cn_jilin_changchun_zhouxijun_38h",
        "topic_stream": "major_violent_crime",
        "case_real_name_zh": "吉林长春3·4盗车连带两月大婴儿失踪案万人全城暴雪搜寻38小时纪实 — 周喜军 (2013)",
        "archival_search_keywords_zh": [
            "长春 盗车婴儿案 周喜军 今日说法",
            "吉林长春 3·4案件 38小时 央视新闻",
            "周喜军 庭审 死刑 纪实"
        ],
        "recommended_vox_verbs": [
            "RADIAL_TIME_PRESSURE",
            "GEO_VECTOR_PURSUIT",
            "CONCENTRIC_TRAP"
        ],
        "title": "[중국 실화 사건] 슈퍼마켓 앞 시동 켜진 SUV를 훔쳐 달아났다 뒷좌석 아기를 발견한 범인과 만 명의 38시간 폭설 추격 | 창춘 저우시쥔 사건 ([Vụ Án Có Thật ở Trung Quốc] Lấy trộm chiếc SUV đang nổ máy trước siêu thị rồi phát hiện em bé ở ghế sau và 38 giờ cả thành phố đội bão tuyết truy lùng | Vụ án Chu Hỷ Quân)",
        "topic_anchor": "[중국 실화 사건] 슈퍼마켓 앞 시동 켜진 SUV를 훔쳐 달아났다 뒷좌석 아기를 발견한 범인과 만 명의 38시간 폭설 추격 | 창춘 저우시쥔 사건",
        "winner_cluster": "Luồng 2 · 2 Phút Quên Tắt Máy Xe Trước Siêu Thị & 38 Giờ Bão Tuyết Huy Động 10.000 Cảnh Sát Cùng Toàn Bộ Taxi Trường Xuân (창춘 38시간 전 도시 수색 저우시쥔 사건)",
        "codex_score": 98,
        "profile_score": 98,
        "codex_angle": "Hồ Sơ Thật 100%: Chu Hỷ Quân & Chuyên Án 38 Giờ Trường Xuân (吉林长春3·4案, 2013) — Khi Mọi Đài Phát Thanh Và Camera Cao Tốc Khép Vòng Vây Giữa Bão Tuyết",
        "codex_reasons": [
            "Chuyên án huy động lực lượng lớn nhất lịch sử thành phố Trường Xuân (hơn 10.000 cảnh sát + hàng vạn tài xế taxi phát sóng trực tiếp trên đài phát thanh và CCTV)",
            "Tòa án Nhân dân Trung cấp Trường Xuân xét xử công khai và thi hành án tử hình Chu Hỷ Quân tháng 11/2013"
        ],
        "opening_hook": "2013년 3월 4일 아침 일곱 시 이십 분, 창춘시의 한 슈퍼마켓 주인이 가게 문을 열기 위해 히터를 켜둔 은색 SUV에서 단 이 분 동안 자리를 비웠습니다. 그 찰나 낯선 남자가 운전석에 올라타 차를 몰고 사라졌고, 뒷좌석 담요 속에는 태어난 지 두 달 된 아기가 잠들어 있었습니다.",
        "note": "📋 【Hồ sơ vụ án: trọng án Chu Hỷ Quân lấy trộm xe Toyota RAV4 có em bé 2 tháng tuổi trên ghế sau tại Trường Xuân, Cát Lâm · 10.000 cảnh sát và toàn thành phố đội bão tuyết truy lùng suốt 38 giờ · Tòa án Trường Xuân tuyên án tử hình Chu Hỷ Quân】 Hồ sơ thật 100% Chuyên án 3·4 tại Trường Xuân, Cát Lâm (吉林长春3·4盗车害命案 — Chu Hỷ Quân 周喜军, 2013): Sáng 4/3/2013, Chu Hỷ Quân lấy trộm chiếc SUV biển số 吉AMM102 đang nổ máy sưởi trước cửa siêu thị rồi gây án trên đường chạy trốn về Công Chúa Lĩnh; trước vòng vây khép kín của hơn 10.000 cảnh sát suốt 38 giờ, Chu Hỷ Quân phải ra đầu thú và bị Tòa án Trường Xuân tuyên án tử hình.",
        "hook_archetype": "countdown_system_breach"
    },
    {
        "id": "vio_cn_yunnan_qujing_yangqingpei_36h",
        "topic_stream": "major_violent_crime",
        "case_real_name_zh": "云南曲靖会泽待补镇9·28特大命案公安部督办36小时跨市缉捕案 — 杨清培 (2016)",
        "archival_search_keywords_zh": [
            "云南会泽 杨清培 9·28特大案 央视新闻",
            "公安部督办 曲靖 杨清培 36小时 破案",
            "杨清培 庭审 死刑 纪实"
        ],
        "recommended_vox_verbs": [
            "GEO_VECTOR_PURSUIT",
            "FORENSIC_ZOOM_CHAIN",
            "RADIAL_TIME_PRESSURE"
        ],
        "title": "[중국 실화 사건] 고향 산골 마을을 발칵 뒤집어 놓고 아무 일 없던 듯 성도로 돌아가 출근한 20대 청년의 두 얼굴 | 윈난 양칭페이 사건 ([Vụ Án Có Thật ở Trung Quốc] Gây chấn động ngôi làng hẻo lánh trên núi rồi thản nhiên lái xe về thủ phủ đi làm như chưa có chuyện gì của gã thanh niên | Đại án Dương Thanh Bồi)",
        "topic_anchor": "[중국 실화 사건] 고향 산골 마을을 발칵 뒤집어 놓고 아무 일 없던 듯 성도로 돌아가 출근한 20대 청년의 두 얼굴 | 윈난 양칭페이 사건",
        "winner_cluster": "Luồng 2 · Dấu Giày Bùn Đỏ Trên Đường Núi & 36 Giờ Ban Chuyên Án Bộ Công An Truy Bắt Dương Thanh Bồi Tại Côn Minh (윈난 후이쩌현 양칭페이 36시간 검거 사건)",
        "codex_score": 98,
        "profile_score": 98,
        "codex_angle": "Hồ Sơ Thật 100%: Dương Thanh Bồi & Chuyên Án 9·28 Hội Trạch, Vân Nam (2016) — Từ Khoản Nợ Cờ Bạc Trực Tuyến Đến 36 Giờ Khóa Chặt Dấu Vết Giữa Thủ Phủ Côn Minh",
        "codex_reasons": [
            "Một trong những đại án hình sự lớn nhất thập niên 2010 do Thứ trưởng Bộ Công an Trung Quốc trực tiếp bay vào Vân Nam chỉ đạo phá án trong 36 giờ",
            "Tòa án Nhân dân Trung cấp Khúc Tĩnh xét xử công khai và tuyên án tử hình Dương Thanh Bồi"
        ],
        "opening_hook": "깊은 산속 고요한 마을 예마촌의 여섯 가구가 하룻밤 사이 모든 연락이 끊긴 채 발견되자 공안부 특별 수사팀이 즉시 급파됐습니다. 현장에서 수거된 단서들을 교차 분석한 지 불과 서른여섯 시간 만에, 형사들은 이백 킬로미터 떨어진 쿤밍 도심에서 평온하게 지내고 있던 스물일곱 살 청년 양칭페이를 포위했습니다.",
        "note": "📋 【Hồ sơ vụ án: đại án đặc biệt nghiêm trọng ngày 28/9/2016 tại huyện Hội Trạch, Khúc Tĩnh, Vân Nam (19 nạn nhân) · Bộ Công an trực tiếp chỉ đạo phá án bắt Dương Thanh Bồi tại Côn Minh sau 36 giờ · Tòa án Khúc Tĩnh tuyên án tử hình】 Hồ sơ thật 100% Chuyên án 9·28 tại thôn Dã Mã, thị trấn Đãi Bổ, huyện Hội Trạch, Vân Nam (云南曲靖会泽9·28特大命案 — Dương Thanh Bồi 杨清培, 2016): Do ngập trong nợ cờ bạc trên mạng tại Côn Minh, Dương Thanh Bồi về quê đòi tiền cha mẹ rồi gây ra thảm án liên hoàn nhằm bịt đầu mối trước khi quay lại Côn Minh; Ban chuyên án Bộ Công an khóa chặt hành tung và bắt giữ Dương Thanh Bồi sau 36 giờ, tuyên án tử hình.",
        "hook_archetype": "micro_forensic_anomaly"
    },
    {
        "id": "vio_cn_inner_mongolia_aiwangquan_fake_mine_74",
        "topic_stream": "major_violent_crime",
        "case_real_name_zh": "内蒙古巴彦淖尔跨6省伪造矿难骗取巨额赔偿金74人特大系列案 — 艾汪全·王付祥 (2014–2016)",
        "archival_search_keywords_zh": [
            "艾汪全 王付祥 伪造矿难 74人 今日说法",
            "巴彦淖尔 盲井案 庭审 死刑 央视",
            "跨6省 伪造矿难 公安部督办"
        ],
        "recommended_vox_verbs": [
            "NETWORK_GRAPH",
            "ALIBI_SHATTER",
            "LEDGER_DIFF_SCRUB"
        ],
        "title": "[중국 실화 사건] 광산 낙석 사고로 위장해 거액의 합의금을 챙기러 나타난 '가짜 유가족' 74명의 소름 돋는 분업 | 네이멍구 아이왕취안 사건 ([Vụ Án Có Thật ở Trung Quốc] Dàn dựng tai nạn sập hầm mỏ để đòi bồi thường tiền tỷ và màn phân vai rợn người của 74 'người nhà giả mạo' | Đại án Ngải Uông Toàn)",
        "topic_anchor": "[중국 실화 사건] 광산 낙석 사고로 위장해 거액의 합의금을 챙기러 나타난 '가짜 유가족' 74명의 소름 돋는 분업 | 네이멍구 아이왕취안 사건",
        "winner_cluster": "Luồng 2 · Phiên Bản Đời Thực Của 'Manh Tỉnh' Xuyên 6 Tỉnh & Vết Nứt Bất Thường Dưới Kính Pháp Y Nội Mông (네이멍구 6개 성 위장 광산 사고 74인 사건)",
        "codex_score": 99,
        "profile_score": 99,
        "codex_angle": "Hồ Sơ Thật 100%: Ngải Uông Toàn · Vương Phú Tường & Đại Án 74 Bị Cáo Ngụy Tạo Tai Nạn Hầm Mỏ Xuyên 6 Tỉnh (2014–2019) — Khi Giấy Chứng Minh Nhân Dân Của 'Người Vợ Khóc Đòi Bồi Thường' Bị Lật Tẩy",
        "codex_reasons": [
            "Đại án điển hình năm của Tòa án Nhân dân Tối cao Trung Quốc và phóng sự nhiều kỳ trên CCTV 今日说法, cấu trúc mạng lưới 74 đối tượng phân vai cực hợp NETWORK_GRAPH trên Vox",
            "Tòa án Nhân dân Trung cấp Bayannur (Nội Mông) tuyên án tử hình và thi hành án đối với Ngải Uông Toàn, Vương Phú Tường cùng các kẻ cầm đầu năm 2019"
        ],
        "opening_hook": "깊은 지하 광산 갱도에서 야간 작업 중 바위가 무너져 내리는 사고가 발생하자, 다음 날 아침 먼 외지에서 왔다는 아내와 친척들이 찾아와 광산주에게 오십만 위안의 합의금을 요구했습니다. 하지만 법의학자가 사고 현장의 각도를 재구성하고 유가족의 신분증을 조회한 순간, 여섯 개 성에 걸친 거대한 범죄 설계도가 드러났습니다.",
        "note": "📋 【Hồ sơ vụ án: đại án liên tỉnh 74 bị cáo do Ngải Uông Toàn & Vương Phú Tường cầm đầu lừa 17 người lao động xuống hầm mỏ tại 6 tỉnh rồi ngụy tạo tai nạn sập hầm để tống tiền bồi thường · Tòa án Nội Mông tuyên án tử hình năm 2019】 Hồ sơ thật 100% Đại án ngụy tạo tai nạn mỏ xuyên 6 tỉnh Nội Mông, Sơn Tây, Thiểm Tây, Hà Bắc, Vân Nam (内蒙古巴彦淖尔艾汪全·王付祥等74人系列伪造矿难案, 2014–2019): Băng nhóm phân công người đi dụ lao động đơn độc, người làm giả hộ khẩu đóng vai vợ/anh em ruột và người trực tiếp dàn dựng sập hầm để ép chủ mỏ bồi thường 500.000–800.000 NDT/vụ; bị Công an Nội Mông phanh phui và Tòa án Tối cao phê chuẩn thi hành án tử hình các tên cầm đầu tháng 8/2019.",
        "hook_archetype": "scale_absurdity_collision"
    },
    {
        "id": "vio_cn_zhejiang_qiandaohu_hairui_boat_1994",
        "topic_stream": "major_violent_crime",
        "case_real_name_zh": "浙江淳安千岛湖3·31海瑞号游船特大劫案20天水下痕检侦破纪实 — 吴黎宏·胡志瀚·余爱军 (1994)",
        "archival_search_keywords_zh": [
            "千岛湖事件 海瑞号 吴黎宏 侦破纪实",
            "1994 千岛湖特大案 审判 死刑",
            "浙江淳安 海瑞号 刑侦档案"
        ],
        "recommended_vox_verbs": [
            "FORENSIC_ZOOM_CHAIN",
            "GEO_VECTOR_PURSUIT",
            "BLIND_SPOT_REVEAL"
        ],
        "title": "[중국 실화 사건] 천 개의 섬으로 둘러싸인 호수 한가운데서 유람선 통째로 연락이 끊긴 밤과 20일간의 수중 역추적 | 저장성 첸다오후 사건 ([Vụ Án Có Thật ở Trung Quốc] Đêm con tàu du lịch Hải Thụy mất liên lạc giữa hồ nước rộng 1.000 hòn đảo và 20 ngày truy nguyên dấu vết dưới đáy nước | Đại án Hồ Thiên Đảo)",
        "topic_anchor": "[중국 실화 사건] 천 개의 섬으로 둘러싸인 호수 한가운데서 유람선 통째로 연락이 끊긴 밤과 20일간의 수중 역추적 | 저장성 첸다오후 사건",
        "winner_cluster": "Luồng 2 · Cửa Khoang Tàu Khóa Trái Từ Bên Ngoài Giữa Hồ Thiên Đảo & Vết Sơn Xuồng Máy Cao Tốc (저장성 첸다오후 하이루이호 사건)",
        "codex_score": 98,
        "profile_score": 98,
        "codex_angle": "Hồ Sơ Thật 100%: Ngô Lê Hồng · Hồ Chí Hãn · Dư Ái Quân & Chuyên Án Tàu Hải Thụy Trên Hồ Thiên Đảo (1994) — 20 Ngày Lọc Tìm 1 Chiếc Xuồng Máy Không Biển Số Giữa Hàng Ngàn Đảo Nhỏ",
        "codex_reasons": [
            "Đại án hình sự nổi tiếng bậc nhất thập niên 1990 tại Chiết Giang, sơ đồ mặt cắt con tàu Hải Thụy 3 tầng và bản đồ vệ tinh 1.078 đảo trên hồ Thiên Đảo cực hợp VOX & 3D GIS",
            "Tòa án Nhân dân Trung cấp Hàng Châu xét xử công khai và thi hành án tử hình cả 3 thủ phạm tháng 6/1994"
        ],
        "opening_hook": "천일흔여덟 개의 섬이 미로처럼 얽혀 있는 거대한 호수 첸다오후에서 승객 서른두 명을 태운 유람선 하이루이호가 해 질 무렵 갑자기 무전 연락이 끊겼습니다. 이튿날 아침 깊은 수역에서 발견된 배의 아래층 선실 문은 누군가 밖에서 철사로 단단히 잠가 놓은 상태였습니다.",
        "note": "📋 【Hồ sơ vụ án: đại án cướp tàu du lịch Hải Thụy trên hồ Thiên Đảo, Chiết Giang khiến 32 hành khách & thuyền viên thiệt mạng · 20 ngày truy nguyên chiếc xuồng máy cao tốc · Tòa án Hàng Châu tuyên án tử hình Ngô Lê Hồng, Hồ Chí Hãn, Dư Ái Quân】 Hồ sơ thật 100% Đại án 3·31 trên hồ Thiên Đảo, huyện Thuần An, Chiết Giang (浙江千岛湖3·31海瑞号特大劫案 — Ngô Lê Hồng 吴黎宏, Hồ Chí Hãn 胡志瀚, Dư Ái Quân 余爱军, 1994): Lợi dụng sương mù chiều tối trên mặt hồ rộng lớn, 3 đối tượng lái xuồng máy áp sát khống chế tàu Hải Thụy cướp tài sản, khóa khoang dưới và đánh chìm tàu; Công an Chiết Giang rà soát toàn bộ xuồng máy và tờ tiền ngoại tệ lưu thông, bắt gọn cả 3 tên sau 20 ngày và tuyên án tử hình.",
        "hook_archetype": "locked_room_vault_paradox"
    },
    {
        "id": "vio_cn_shandong_jinan_duanyihe_detonator_2007",
        "topic_stream": "major_violent_crime",
        "case_real_name_zh": "山东济南7·9闹市遥控炸药包案雷管编号14天破案与极速死刑审判 — 段义和·陈志 (2007)",
        "archival_search_keywords_zh": [
            "济南 7·9爆炸案 段义和 陈志 今日说法",
            "段义和 雷管编号 侦破纪实 央视",
            "山东段义和 庭审 死刑"
        ],
        "recommended_vox_verbs": [
            "SINGLE_EVIDENCE_AUTOPSY",
            "FORENSIC_ZOOM_CHAIN",
            "SPLIT_PARADOX"
        ],
        "title": "[중국 실화 사건] 퇴근길 도심 한복판 승용차에서 수거된 쌀알만 한 뇌관 일련번호가 가리킨 도시 최고위 권력자 | 지난 돤이허 사건 ([Vụ Án Có Thật ở Trung Quốc] Mảnh số seri kíp nổ nhỏ bằng hạt gạo giữa ngã tư giờ tan tầm chỉ thẳng tới nhân vật quyền lực số 1 thành phố | Đại án Đoạn Nghĩa Hòa Tế Nam)",
        "topic_anchor": "[중국 실화 사건] 퇴근길 도심 한복판 승용차에서 수거된 쌀알만 한 뇌관 일련번호가 가리킨 도시 최고위 권력자 | 지난 돤이허 사건",
        "winner_cluster": "Luồng 2 · Mảnh Vỏ Kíp Nổ Mang Mã Số Lô Hàng & 14 Ngày Lật Tẩy Chủ Tịch HĐND Thành Phố Tế Nam Đoạn Nghĩa Hòa (산둥 지난 7·9 돤이허 사건)",
        "codex_score": 99,
        "profile_score": 99,
        "codex_angle": "Hồ Sơ Thật 100%: Đoạn Nghĩa Hòa · Trần Chí & Chuyên Án 7·9 Tế Nam, Sơn Đông (2007) — Từ Việc Dùng Rây Bột Lọc Từng Gam Bùn Đất Hiện Trường Đến Bản Án Tử Hình Thi Hành Sau 60 Ngày",
        "codex_reasons": [
            "Một trong những chuyên án giám định vật chứng nổ nổi tiếng nhất của Bộ Công an Trung Quốc, lên sóng CCTV 今日说法 / 新闻调查",
            "Tòa án Nhân dân Trung cấp Truy Bác và Tòa án Tối cao tuyên án tử hình, thi hành án đối với Đoạn Nghĩa Hòa và Trần Chí ngày 5/9/2007"
        ],
        "opening_hook": "2007년 7월 9일 오후 다섯 시 반, 퇴근길 차량이 쏟아지던 지난시 중심가에서 은색 승용차 한 대가 거대한 소리와 함께 파손됐습니다. 폭우 속에서 감식반이 고운 체로 흙탕물을 걸러 찾아낸 쌀알 크기의 금속 조각 위에는 사건의 배후에 숨은 도시 권력자의 이름을 밝힐 일련번호가 찍혀 있었습니다.",
        "note": "📋 【Hồ sơ vụ án: đại án cài thuốc nổ điều khiển từ xa dưới ghế lái ô tô giữa phố Tế Nam, Sơn Đông · pháp y Bộ Công an khôi phục mã số kíp nổ bắt cảnh sát Trần Chí và kẻ chủ mưu Chủ tịch HĐND thành phố Đoạn Nghĩa Hòa · thi hành án tử hình sau 60 ngày】 Hồ sơ thật 100% Chuyên án 7·9 tại Tế Nam, Sơn Đông (山东济南7·9段义和·陈志爆炸案, 2007): Để thoát khỏi sự đòi hỏi tiền bạc và chức vụ của người tình Liễu Hải Bình, Chủ tịch HĐND thành phố Tế Nam Đoạn Nghĩa Hòa đã sai cháu rể là cảnh sát Trần Chí chế tạo gói thuốc nổ điều khiển từ xa đặt dưới ghế lái; chuyên gia Bộ Công an sàng lọc hiện trường dưới mưa lớn tìm ra mảnh vỏ kíp nổ có mã số quản lý, bắt giữ cả hai sau 14 ngày và thi hành án tử hình ngày 5/9/2007.",
        "hook_archetype": "micro_forensic_anomaly"
    },
    {
        "id": "vio_cn_guangxi_liucheng_weiyinyong_parcels_2015",
        "topic_stream": "major_violent_crime",
        "case_real_name_zh": "广西柳州柳城县9·30同城快递包裹连环爆炸案48小时侦破纪实 — 韦银勇 (2015)",
        "archival_search_keywords_zh": [
            "广西柳城 9·30 快递包裹 韦银勇 央视新闻",
            "柳州 韦银勇 48小时 侦破纪实",
            "柳城县 连环包裹案 警方通报"
        ],
        "recommended_vox_verbs": [
            "RADIAL_TIME_PRESSURE",
            "NETWORK_GRAPH",
            "SINGLE_EVIDENCE_AUTOPSY"
        ],
        "title": "[중국 실화 사건] 수취인 확인 전화를 걸어 동시에 작동시킨 18개의 익명 택배 상자와 48시간의 역추적 | 광시 웨이인융 사건 ([Vụ Án Có Thật ở Trung Quốc] 18 kiện hàng chuyển phát nhanh ẩn danh kích hoạt cùng lúc sau cuộc gọi xác nhận và 48 giờ truy nguyên kíp nổ | Chuyên án Vi Ngân Dũng Quảng Tây)",
        "topic_anchor": "[중국 실화 사건] 수취인 확인 전화를 걸어 동시에 작동시킨 18개의 익명 택배 상자와 48시간의 역추적 | 광시 웨이인융 사건",
        "winner_cluster": "Luồng 2 · Sơ Đồ 18 Kiện Hàng Đồng Thành & Cuộc Chạy Đua 48 Giờ Chặn Đứng Kẻ Chủ Mưu Trước Chuyến Bay Xuất Cảnh (광시 류청현 18개 익명 소포 사건)",
        "codex_score": 98,
        "profile_score": 98,
        "codex_angle": "Hồ Sơ Thật 100%: Vi Ngân Dũng & Chuyên Án 9·30 Liễu Thành, Quảng Tây (2015) — Khi Chuyên Gia Kỹ Thuật Hình Sự Lần Theo Nguồn Gốc Thuốc Nổ Mỏ Đá Và Lịch Trình Đặt Vé Máy Bay",
        "codex_reasons": [
            "Chuyên án bưu kiện chấn động toàn Trung Quốc ngày 30/9/2015 (100% có thật với tên tuổi đầy đủ Vi Ngân Dũng 韦银勇, thay thế hoàn toàn đề tài khuyết danh cũ), có bản tin chính thức của CCTV và Bộ Công an",
            "Cực hợp với sơ đồ mạng lưới giao hàng NETWORK_GRAPH & RADIAL_TIME_PRESSURE trên bàn biên tập Vox"
        ],
        "opening_hook": "국경절 연휴를 하루 앞둔 2015년 9월 30일 오후 세 시 십오 분, 광시성 류청현 곳곳으로 배달된 열여덟 개의 택배 상자가 불과 몇 분 간격으로 연달아 작동하기 시작했습니다. 발신인 이름도 가짜였고 배달원조차 영문을 몰랐던 그 상자들의 출발점을 찾기 위해 사십팔 시간의 역추적이 시작됐습니다.",
        "note": "📋 【Hồ sơ vụ án: đại án 18 bưu kiện chuyển phát nhanh chứa thuốc nổ công nghiệp kích hoạt đồng loạt tại huyện Liễu Thành, Liễu Châu, Quảng Tây · truy nguyên lô thuốc nổ mỏ đá khóa chặt thủ phạm Vi Ngân Dũng trong 48 giờ】 Hồ sơ thật 100% Chuyên án 9·30 tại huyện Liễu Thành, Liễu Châu, Quảng Tây (广西柳城9·30快递包裹爆炸案 — Vi Ngân Dũng 韦银勇, 2015): Do mâu thuẫn khai thác mỏ đá, quản lý kỹ thuật nổ mìn Vi Ngân Dũng đã lấy thuốc nổ công nghiệp ngụy trang thành 18 bưu kiện thuê người giao tới nhiều địa điểm trong huyện ngày 30/9/2015 đồng thời đặt hộ chiếu và vé máy bay định trốn sang Thái Lan; Công an Quảng Tây và Bộ Công an khoanh vùng nguồn thuốc nổ, phá án trong 48 giờ.",
        "hook_archetype": "countdown_system_breach"
    },
    {
        "id": "vio_cn_guangdong_lufeng_caidongjia_3000_police",
        "topic_stream": "major_violent_crime",
        "case_real_name_zh": "广东陆丰博社村12·29雷霆行动3000警力海陆空夜袭收网案 — 蔡东家·蔡旋 (2013–2019)",
        "archival_search_keywords_zh": [
            "陆丰博社村 蔡东家 12·29 雷霆扫毒 今日说法",
            "破冰行动原型 蔡东家 3000警力 央视",
            "博社村 蔡东家 死刑 纪实"
        ],
        "recommended_vox_verbs": [
            "CONCENTRIC_TRAP",
            "GEO_VECTOR_PURSUIT",
            "NETWORK_GRAPH"
        ],
        "title": "[중국 실화 사건] 마을 입구마다 감시초소를 세우고 경찰까지 매수해 요새를 만든 촌장과 3,000명 심야 헬기 기습 작전 | 보서촌 차이둥자 사건 ([Vụ Án Có Thật ở Trung Quốc] Trưởng thôn dựng trạm gác quanh làng, mua chuộc cả cảnh sát để lập pháo đài ngầm và đêm 3.000 đặc nhiệm cùng trực thăng đột kích | Đại án Thái Đông Gia)",
        "topic_anchor": "[중국 실화 사건] 마을 입구마다 감시초소를 세우고 경찰까지 매수해 요새를 만든 촌장과 3,000명 심야 헬기 기습 작전 | 보서촌 차이둥자 사건",
        "winner_cluster": "Luồng 2 · Nguyên Mẫu Đời Thực Của 'Phá Băng Hành Động': 3.000 Quân Cảnh Hải Lục Không Đột Kích Pháo Đài Thôn Bác Xã Lúc 4 Giờ Sáng (광둥 보서촌 차이둥자 3,000명 기습 사건)",
        "codex_score": 99,
        "profile_score": 99,
        "codex_angle": "Hồ Sơ Thật 100%: Thái Đông Gia & Chiến Dịch Sấm Sét 12·29 Tại Thôn Bác Xã, Lục Phong (2013–2019) — Khi Công An Tỉnh Quảng Đông Điều Quân Từ Các Tỉnh Khác Và Cắt Sóng Liên Lạc Để Chống Nội Gián",
        "codex_reasons": [
            "Chuyên án nguyên mẫu 100% của bộ phim truyền hình nổi tiếng 'Phá Băng Hành Động (破冰行动)', video quay đêm từ trực thăng cảnh sát Quảng Đông và phiên tòa xét xử Thái Đông Gia cực kỳ mãn nhãn",
            "Tòa án Nhân dân Trung cấp Phật Sơn và Tòa án Tối cao thi hành án tử hình Thái Đông Gia tháng 1/2019"
        ],
        "opening_hook": "외부 차량이 마을 입구에 들어서기만 해도 수십 대의 오토바이 감시조가 따라붙어 경찰조차 쉽게 들어가지 못하던 광둥성 해안 마을 보서촌. 그 난공불락의 요새를 지휘하던 인물은 놀랍게도 마을 당서기이자 시 인민대표였던 차이둥자였습니다. 2013년 12월 29일 새벽 네 시, 헬기와 경비정을 앞세운 삼천 명의 타 지역 특공대가 어둠을 뚫고 일제히 진입했습니다.",
        "note": "📋 【Hồ sơ vụ án: đại án nguyên mẫu phim 'Phá Băng Hành Động' tại thôn Bác Xã, Lục Phong, Quảng Đông · Bí thư thôn Thái Đông Gia mua chuộc cảnh sát bảo kê pháo đài sản xuất gần 3 tấn hàng cấm · 3.000 cảnh sát hải lục không đột kích và Tòa án Phật Sơn tuyên án tử hình Thái Đông Gia】 Hồ sơ thật 100% Chuyên án Lôi Đình 12·29 tại thôn Bác Xã, Lục Phong, Quảng Đông (广东陆丰博社村蔡东家特大制贩毒与保护伞案, 2013–2019): Thái Đông Gia lợi dụng chức Bí thư thôn kiêm đại biểu HĐND để biến thôn Bác Xã thành căn cứ khép kín có đội trinh sát báo động và mua chuộc 14 cán bộ công an địa phương; rạng sáng 29/12/2013, Công an tỉnh Quảng Đông bí mật điều 3.000 quân cảnh từ các thành phố khác cùng trực thăng và tàu tuần tra bao vây thu giữ 2,925 tấn tinh thể, đưa Thái Đông Gia ra thi hành án tử hình tháng 1/2019.",
        "hook_archetype": "scale_absurdity_collision"
    },
    {
        "id": "vio_cn_chongqing_wenqiang_fishpond_20m",
        "topic_stream": "major_violent_crime",
        "case_real_name_zh": "重庆市司法局长鱼塘底2000万油布现金与双面黑伞覆灭案 — 文强 (2000–2010)",
        "archival_search_keywords_zh": [
            "重庆 文强 鱼塘 2000万 今日说法",
            "文强 庭审 死刑 央视新闻",
            "重庆打黑 文强 侦破纪实"
        ],
        "recommended_vox_verbs": [
            "SPLIT_PARADOX",
            "SINGLE_EVIDENCE_AUTOPSY",
            "NETWORK_GRAPH"
        ],
        "title": "[중국 실화 사건] 1호 수배범을 직접 체포했던 전설적인 경찰 부국장이 교외 양어장 바닥에 2,000만 위안을 묻어둔 이유 | 충칭 원창 두 얼굴 사건 ([Vụ Án Có Thật ở Trung Quốc] Lý do vị Phó giám đốc Công an huyền thoại từng trực tiếp bắt trùm cướp số 1 lại chôn 20 triệu tệ dưới đáy ao cá | Đại án Văn Cường Trùng Khánh)",
        "topic_anchor": "[중국 실화 사건] 1호 수배범을 직접 체포했던 전설적인 경찰 부국장이 교외 양어장 바닥에 2,000만 위안을 묻어둔 이유 | 충칭 원창 두 얼굴 사건",
        "winner_cluster": "Luồng 2 · Từ Anh Hùng Bắt Sống Trương Quân Đến 20 Triệu Tệ Bọc Vải Dầu Dưới Đáy Ao Cá Ngoại Ô (충칭 사법국장 원창 양어장 2,000만 위안 사건)",
        "codex_score": 99,
        "profile_score": 99,
        "codex_angle": "Hồ Sơ Thật 100%: Văn Cường (文强, Trùng Khánh 2000–2010) — Khi Bơm Cạn Nước Ao Cá Ngoại Ô Phơi Bày Những Kiện Tiền Bọc Vải Dầu Chống Thấm Của Vị Cục Trưởng Tư Pháp",
        "codex_reasons": [
            "Một trong những đại án 'người thực thi pháp luật hai mặt' chấn động nhất lịch sử Trung Quốc, cảnh bơm cạn ao cá vớt 20 triệu NDT tiền mặt bọc vải dầu được CCTV phát sóng toàn quốc",
            "Tòa án Nhân dân Trung cấp số 5 Trùng Khánh và Tòa án Tối cao phê chuẩn thi hành án tử hình Văn Cường tháng 7/2010"
        ],
        "opening_hook": "2000년 공안부 1호 수배범 장쥔의 머리를 발로 밟으며 체포해 전국적인 영웅으로 떠올랐던 충칭시 공안국 부국장 원창. 그러나 구 년 뒤 특별 수사팀이 교외 별장 앞 양어장의 물을 전부 퍼내자, 진흙 바닥 속에서 방수 기름종이로 겹겹이 밀봉된 이천만 위안의 현금 뭉치가 모습을 드러냈습니다.",
        "note": "📋 【Hồ sơ vụ án: đại án Phó giám đốc Công an kiêm Cục trưởng Cục Tư pháp Trùng Khánh Văn Cường làm 'ô dù bảo kê' cho 6 băng nhóm tội phạm ngầm và chôn 20 triệu tệ tiền mặt dưới đáy ao cá · Tòa án Trùng Khánh tuyên án tử hình năm 2010】 Hồ sơ thật 100% Đại án Văn Cường tại Trùng Khánh (重庆文强受贿包庇纵容黑社会性质组织案, 2000–2010): Từng là Phó giám đốc Công an Trùng Khánh nổi danh cả nước khi chỉ huy bắt giữ Trương Quân năm 2000, Văn Cường đã bị mua chuộc trở thành người bảo kê lớn nhất cho các băng nhóm tội phạm có tổ chức suốt gần 10 năm; khi bị bắt năm 2009, ban chuyên án bơm cạn ao cá của em dâu Văn Cường thu giữ 20 triệu NDT tiền mặt bọc vải dầu chống nước, và Tòa án Tối cao phê chuẩn thi hành án tử hình ngày 7/7/2010.",
        "hook_archetype": "double_life_unmasking"
    },
    {
        "id": "vio_cn_liaoning_liaoyang_yuanbaojing_futures_2006",
        "topic_stream": "major_violent_crime",
        "case_real_name_zh": "北京建昊集团37亿董事长四川期货9000万亏损雇凶悬案 — 袁宝璟·袁宝琦 (1996–2006)",
        "archival_search_keywords_zh": [
            "袁宝璟 37亿首富 死刑 今日说法",
            "辽宁辽阳 袁宝璟 汪兴 侦破纪实",
            "中国股票第一人 袁宝璟 审判"
        ],
        "recommended_vox_verbs": [
            "CAUSAL_CHAIN",
            "SPLIT_PARADOX",
            "FORENSIC_ZOOM_CHAIN"
        ],
        "title": "[중국 실화 사건] 법정에서 500억 위안 유전 지분을 기부하겠다며 선처를 호소한 '중국 주식의 신'이 7년간 숨긴 범죄 | 베이징 위안바오징 사건 ([Vụ Án Có Thật ở Trung Quốc] Tuyên bố hiến tặng 50 tỷ tệ cổ phần mỏ dầu ngay tại tòa để xin giữ mạng và tội ác giấu kín 7 năm của 'Thần chứng khoán' | Đại án Viên Bảo Cảnh)",
        "topic_anchor": "[중국 실화 사건] 법정에서 500억 위안 유전 지분을 기부하겠다며 선처를 호소한 '중국 주식의 신'이 7년간 숨긴 범죄 | 베이징 위안바오징 사건",
        "winner_cluster": "Luồng 2 · 90 Triệu Tệ Thua Lỗ Sàn Kỳ Hạn Tứ Xuyên & Lời Đề Nghị Đổi 49,5 Tỷ Tệ Cổ Phần Mỏ Dầu Trước Giờ Thi Hành Án (베이징 37억 부호 위안바오징 사건)",
        "codex_score": 99,
        "profile_score": 99,
        "codex_angle": "Hồ Sơ Thật 100%: Viên Bảo Cảnh (袁宝璟, 1996–2006) — Từ Tỷ Phú Trẻ Nhất Bắc Kinh Đến Màn Đấu Trí 7 Năm Với Cựu Đội Trưởng Hình Cảnh Uông Hưng",
        "codex_reasons": [
            "Đại án tỷ phú số 1 Trung Quốc bị thi hành án tử hình (kèm tình tiết chấn động hiến 49,5 tỷ NDT cổ phần mỏ dầu Indonesia tại tòa Liêu Dương), có đầy đủ tư liệu CCTV 今日说法",
            "Tòa án Nhân dân Trung cấp Liêu Dương (Liêu Ninh) tuyên án tử hình và thi hành án đối với 3 anh em họ Viên ngày 17/3/2006"
        ],
        "opening_hook": "서른 살의 나이에 삼십칠억 위안의 자산을 일궈내 중국 증권가의 전설로 불리던 베이징 건호그룹 회장 위안바오징. 그가 2005년 법정 피고인석에 서서 최고형을 면하게 해준다면 사백구십오억 위안 가치의 해외 유전 지분을 국가에 전부 바치겠다고 외쳤을 때, 법정 안은 충격으로 술렁였습니다.",
        "note": "📋 【Hồ sơ vụ án: đại án tỷ phú 3,7 tỷ tệ Viên Bảo Cảnh ('Thần chứng khoán Trung Quốc') sau khi thua lỗ 90 triệu tệ kỳ hạn đã thuê anh em họ truy sát cộng sự Uông Hưng suốt 7 năm · đề nghị hiến 49,5 tỷ tệ mỏ dầu để xin tha tội nhưng vẫn bị Tòa án Liêu Dương thi hành án tử hình】 Hồ sơ thật 100% Đại án Viên Bảo Cảnh tại Bắc Kinh – Liêu Dương, Liêu Ninh (北京建昊集团董事长袁宝璟雇凶案, 1996–2006): Năm 1996, Viên Bảo Cảnh thua lỗ 90 triệu NDT trên sàn kỳ hạn Tứ Xuyên nên nghi ngờ cộng sự Uông Hưng (cựu đội trưởng hình cảnh Liêu Dương) bán đứng mình; khi Uông Hưng nắm giữ bằng chứng tống tiền ngược lại, Viên Bảo Cảnh đã chi tiền sai Viên Bảo Kỳ và Viên Bảo Sâm ra tay năm 2003, và cả ba bị Tòa án Liêu Dương thi hành án tử hình ngày 17/3/2006.",
        "hook_archetype": "scale_absurdity_collision"
    },
    {
        "id": "vio_cn_hunan_anhua_liuaibing_fog_20h",
        "topic_stream": "major_violent_crime",
        "case_real_name_zh": "湖南安化12·12特大命案1000警力20小时大雾山林围捕案 — 刘爱兵 (2009)",
        "archival_search_keywords_zh": [
            "湖南安化 刘爱兵 12·12特大案 央视",
            "益阳 安化 刘爱兵 审判 死刑",
            "安化 1000警力 围捕 纪实"
        ],
        "recommended_vox_verbs": [
            "CONCENTRIC_TRAP",
            "GEO_VECTOR_PURSUIT",
            "RADIAL_TIME_PRESSURE"
        ],
        "title": "[중국 실화 사건] 짙은 안개 낀 대나무 산맥 속으로 사라진 수배범을 1,000명의 수색대가 20시간 만에 포위한 방법 | 후난 류아이빙 사건 ([Vụ Án Có Thật ở Trung Quốc] Cách 1.000 quân cảnh khép vòng vây chỉ trong 20 giờ bắt sống kẻ thủ ác lẩn vào rừng trúc sương mù dày đặc | Chuyên án Lưu Ái Binh Hồ Nam)",
        "topic_anchor": "[중국 실화 사건] 짙은 안개 낀 대나무 산맥 속으로 사라진 수배범을 1,000명의 수색대가 20시간 만에 포위한 방법 | 후난 류아이빙 사건",
        "winner_cluster": "Luồng 2 · 3 Vòng Vây Đồng Tâm Khóa Chặt Rừng Trúc Sương Mù Trong 20 Giờ Tại An Hóa, Hồ Nam (후난 안화현 류아이빙 20시간 포위 사건)",
        "codex_score": 97,
        "profile_score": 97,
        "codex_angle": "Hồ Sơ Thật 100%: Lưu Ái Binh & Chuyên Án 12·12 An Hóa, Hồ Nam (2009–2010) — Chiến Thuật Khóa Đỉnh Đồi Và Chốt Chặn Nguồn Nước Trong Rừng Sâu",
        "codex_reasons": [
            "Chuyên án vây bắt rừng núi quy mô lớn của Công an tỉnh Hồ Nam năm 2009, cực hợp bản đồ vệ tinh 3D CONCENTRIC_TRAP",
            "Tòa án Nhân dân Trung cấp Ích Dương tuyên án tử hình và thi hành án đối với Lưu Ái Binh tháng 12/2010"
        ],
        "opening_hook": "한 치 앞도 보이지 않는 짙은 겨울 안개가 내려앉은 후난성 안화현의 해발 팔백 미터 대나무 숲속으로 중대 용의자 류아이빙이 사라졌습니다. 산길마다 갈림길이 수십 개로 뻗어 있었지만, 일천 명의 합동 수색대는 산등성이와 수원지를 세 겹의 동심원으로 봉쇄하며 포위망을 좁혀 들어갔습니다.",
        "note": "📋 【Hồ sơ vụ án: đại án đặc biệt nghiêm trọng ngày 12/12/2009 tại huyện An Hóa, Ích Dương, Hồ Nam (12 nạn nhân) · 1.000 cảnh sát khép vòng vây rừng trúc sương mù bắt sống Lưu Ái Binh sau 20 giờ · Tòa án Ích Dương tuyên án tử hình】 Hồ sơ thật 100% Chuyên án 12·12 tại thôn 칠 Tinh, huyện An Hóa, Hồ Nam (湖南安化12·12刘爱兵特大命案, 2009–2010): Sau khi gây án lúc rạng sáng 12/12/2009 tại quê nhà, Lưu Ái Binh lẩn trốn vào vùng rừng núi hiểm trở giữa sương mù dày đặc; Công an tỉnh Hồ Nam huy động hơn 1.000 cảnh sát cơ động và chó nghiệp vụ lập 3 vòng vây khóa chặt các đỉnh đồi, bắt giữ Lưu Ái Binh lúc 6h50 sáng hôm sau và tuyên án tử hình.",
        "hook_archetype": "countdown_system_breach"
    },
    {
        "id": "vio_cn_heilongjiang_harbin_songyongjia_qiaosi_1991",
        "topic_stream": "major_violent_crime",
        "case_real_name_zh": "黑龙江哈尔滨一号涉黑集团覆灭与专案组秘密抓捕纪实 — 宋永佳（乔四）(1986–1991)",
        "archival_search_keywords_zh": [
            "哈尔滨 乔四 宋永佳 覆灭纪实",
            "黑龙江 宋永佳 专案组 审判 死刑",
            "黑A88888 乔四 刑侦档案"
        ],
        "recommended_vox_verbs": [
            "NETWORK_GRAPH",
            "CONCENTRIC_TRAP",
            "SPLIT_PARADOX"
        ],
        "title": "[중국 실화 사건] 숫자 8 다섯 개가 찍힌 번호판을 달고 도시 철거권을 독점했던 지하 제국 두목과 비밀 특공대의 심야 기습 | 하얼빈 송융자 사건 ([Vụ Án Có Thật ở Trung Quốc] Ông trùm gắn biển số xe năm số 8 độc quyền mảng giải tỏa cả thành phố và cuộc đột kích bí mật của Tổ chuyên án Trung ương | Đại án Tống Vĩnh Giai)",
        "topic_anchor": "[중국 실화 사건] 숫자 8 다섯 개가 찍힌 번호판을 달고 도시 철거권을 독점했던 지하 제국 두목과 비밀 특공대의 심야 기습 | 하얼빈 송융자 사건",
        "winner_cluster": "Luồng 2 · Biển Số Xe Đen A88888 & Mật Lệnh Cắt Liên Lạc Nội Bộ Để Bắt Gọn Đế Chế Tống Vĩnh Giai Tại Cáp Nhĩ Tân (하얼빈 송융자 차오쓰 사건)",
        "codex_score": 98,
        "profile_score": 98,
        "codex_angle": "Hồ Sơ Thật 100%: Tống Vĩnh Giai (Kiều Tứ — 宋永佳, Cáp Nhĩ Tân 1986–1991) — Khi Tổ Chuyên Án Bí Mật Dùng Lý Lịch Giả Đặt Phòng Khách Sạn Để Tránh Tai Mắt Bảo Kê",
        "codex_reasons": [
            "Một trong những đại án chống tội phạm có tổ chức nổi tiếng nhất lịch sử vùng Đông Bắc Trung Quốc, có đầy đủ ảnh/video phiên tòa xét xử công khai và tuyên án tử hình tháng 6/1991",
            "Cực hợp NETWORK_GRAPH & CONCENTRIC_TRAP"
        ],
        "opening_hook": "1980년대 말 하얼빈 시내에서 검은색 벤츠 승용차 번호판 끝에 숫자 팔 다섯 개가 찍힌 차가 나타나면 교통신호등마저 길을 비켜주곤 했습니다. 평범한 벽돌공 출신에서 도시 재개발 철거 시장을 통째로 삼킨 송융자의 제국을 무너뜨리기 위해, 베이징에서 내려온 비밀 수사팀이 암호명으로 작전을 개시했습니다.",
        "note": "📋 【Hồ sơ vụ án: đại án triệt phá tập đoàn tội phạm có tổ chức lớn nhất vùng Đông Bắc do Tống Vĩnh Giai (Kiều Tứ) cầm đầu tại Cáp Nhĩ Tân · Tổ chuyên án bí mật bắt giữ ngày 10/8/1990 · Tòa án Hắc Long Giang tuyên án tử hình tháng 6/1991】 Hồ sơ thật 100% Chuyên án Tống Vĩnh Giai (宋永佳, biệt danh Kiều Tứ 乔四) tại Cáp Nhĩ Tân, Hắc Long Giang (1986–1991): Xuất thân là thợ nề ở cầu Đại Kiều, Tống Vĩnh Giai lập băng nhóm cưỡng ép độc quyền các dự án giải tỏa mặt bằng tại Cáp Nhĩ Tân và mua chuộc nhiều quan chức; tháng 8/1990, Tổ chuyên án 8·10 giữ bí mật tuyệt đối bắt gọn toàn bộ băng nhóm và Tòa án Hắc Long Giang thi hành án tử hình Tống Vĩnh Giai cùng 13 đồng phạm ngày 9/6/1991.",
        "hook_archetype": "scale_absurdity_collision"
    },
    {
        "id": "vio_cn_guangdong_yangjiang_xujianqiang_linguokin_2009",
        "topic_stream": "major_violent_crime",
        "case_real_name_zh": "广东阳江十二年双首脑垄断海鲜水泥市场涉黑大案侦破纪实 — 许建强·林国钦 (1996–2009)",
        "archival_search_keywords_zh": [
            "广东阳江 许建强 林国钦 今日说法",
            "阳江涉黑大案 焦点访谈 央视",
            "许建强 林国钦 庭审 死刑"
        ],
        "recommended_vox_verbs": [
            "NETWORK_GRAPH",
            "LEDGER_DIFF_SCRUB",
            "CONCENTRIC_TRAP"
        ],
        "title": "[중국 실화 사건] 시멘트부터 해산물 도매시장 가격까지 12년간 마음대로 정하던 두 억대 회장의 비밀 장부 | 광둥 양장시 쉬젠창 사건 ([Vụ Án Có Thật ở Trung Quốc] Cuốn sổ cái mật của hai vị Chủ tịch tập đoàn tự tay định giá từ xi măng đến hải sản suốt 12 năm ở một thành phố | Đại án Hứa Kiến Cường Quảng Đông)",
        "topic_anchor": "[중국 실화 사건] 시멘트부터 해산물 도매시장 가격까지 12년간 마음대로 정하던 두 억대 회장의 비밀 장부 | 광둥 양장시 쉬젠창 사건",
        "winner_cluster": "Luồng 2 · Hai Ông Trùm Thao Túng Mọi Chợ Đầu Mối Dương Giang Suốt 12 Năm & Đêm 500 Cảnh Sát Cơ Động Tỉnh Đột Kích (광둥 양장시 쉬젠창·린궈친 사건)",
        "codex_score": 97,
        "profile_score": 97,
        "codex_angle": "Hồ Sơ Thật 100%: Hứa Kiến Cường · Lâm Quốc Khâm (广东阳江涉黑大案, 1996–2009) — Phiên Tòa 43 Bị Cáo Kéo Dài 42 Ngày Và Bản Án Tử Hình Của Tòa Án Tối Cao",
        "codex_reasons": [
            "Chuyên án điểm của Bộ Công an Trung Quốc được phát sóng trên cả CCTV 焦点访谈 và 今日说法, cực kỳ giàu tư liệu phiên tòa",
            "Tòa án Nhân dân Trung cấp Dương Giang và Tòa án Tối cao phê chuẩn thi hành án tử hình Hứa Kiến Cường tháng 12/2009"
        ],
        "opening_hook": "광둥성 해안 도시 양장시에서는 십이 년 동안 시민들이 집을 지을 때 쓰는 시멘트 한 포대부터 식탁에 오르는 생선 한 마리까지 두 사람의 허락 없이는 유통될 수 없었습니다. 자선 사업가와 정협 위원 명함을 들고 다녔던 쉬젠창과 린궈친의 제국이 오백 명의 성 공안청 특공대에 의해 일제히 봉쇄됐습니다.",
        "note": "📋 【Hồ sơ vụ án: đại án 43 bị cáo do hai trùm Hứa Kiến Cường & Lâm Quốc Khâm cầm đầu thao túng kinh tế và gây trọng án suốt 12 năm tại Dương Giang, Quảng Đông · 500 cảnh sát tỉnh đột kích thu giữ sổ cái mật · Tòa Tối cao thi hành án tử hình Hứa Kiến Cường năm 2009】 Hồ sơ thật 100% Đại án Hứa Kiến Cường và Lâm Quốc Khâm tại Dương Giang, Quảng Đông (广东阳江许建强·林国钦等43人涉黑大案, 1996–2009): Dưới vỏ bọc doanh nhân tỷ phú, hai đối tượng lập mạng lưới cưỡng đoạt và độc quyền 8 ngành nghề thiết yếu của thành phố suốt 12 năm; đêm 21/11/2007, Công an tỉnh Quảng Đông điều 500 cảnh sát cơ động bao vây bắt giữ toàn bộ 43 đối tượng, xét xử liên tục 42 ngày và thi hành án tử hình Hứa Kiến Cường tháng 12/2009.",
        "hook_archetype": "double_life_unmasking"
    },
    {
        "id": "vio_cn_hunan_changsha_pengshuiyang_10d",
        "topic_stream": "major_violent_crime",
        "case_real_name_zh": "湖南长沙芙蓉区7·30案件公安部A级通缉10天跨省抓捕纪实 — 彭水洋 (2010)",
        "archival_search_keywords_zh": [
            "长沙 7·30 彭水洋 公安部A级通缉 央视",
            "湖南长沙 彭水洋 福建泉州落网 纪实",
            "彭水洋 庭审 死刑"
        ],
        "recommended_vox_verbs": [
            "GEO_VECTOR_PURSUIT",
            "FORENSIC_ZOOM_CHAIN",
            "RADIAL_TIME_PRESSURE"
        ],
        "title": "[중국 실화 사건] 대낮 관공서 복도에 검은 가방을 내려놓고 사라진 공안부 A급 수배범의 10일 도주 경로 | 창사 펑수이양 사건 ([Vụ Án Có Thật ở Trung Quốc] Đặt chiếc túi đen ở hành lang cơ quan thuế giữa ban ngày rồi biến mất và 10 ngày truy lùng tội phạm cấp A | Chuyên án Bành Thủy Dương Trường Sa)",
        "topic_anchor": "[중국 실화 사건] 대낮 관공서 복도에 검은 가방을 내려놓고 사라진 공안부 A급 수배범의 10일 도주 경로 | 창사 펑수이양 사건",
        "winner_cluster": "Luồng 2 · Dấu Vết Điện Tử Từ Phòng Máy Tính & 10 Ngày Truy Bắt Bành Thủy Dương Xuyên 4 Tỉnh Tới Phúc Kiến (후난 창사 A급 수배범 펑수이양 사건)",
        "codex_score": 97,
        "profile_score": 97,
        "codex_angle": "Hồ Sơ Thật 100%: Bành Thủy Dương & Chuyên Án 7·30 Trường Sa, Hồ Nam (2010) — Khi Lệnh Truy Nã Cấp A Của Bộ Công An Khóa Chặt Quán Internet Tại Tuyền Châu",
        "codex_reasons": [
            "Chuyên án truy nã cấp A của Bộ Công an Trung Quốc tháng 8/2010 với lộ trình đào tẩu xuyên Hồ Nam – Giang Tây – Quảng Tây – Phúc Kiến cực hợp bản đồ 3D GIS",
            "Tòa án Nhân dân Trung cấp Trường Sa xét xử công khai và tuyên án tử hình Bành Thủy Dương"
        ],
        "opening_hook": "2010년 7월 30일 오후 네 시 십오 분, 창사시 푸룽구 세무분국 삼 층 회의실 복도에 낯선 남자가 검은 가방 하나를 밀어 넣고 계단으로 빠르게 내려갔습니다. 공안부가 현상금 십만 위안의 A급 수배령을 내린 지 열흘째 되던 날, 천 킬로미터 밖 해안 도시의 작은 PC방 모니터 앞에서 그의 행적이 포착됐습니다.",
        "note": "📋 【Hồ sơ vụ án: đại án 7·30 tại Chi cục thuế quận Phù Dung, Trường Sa, Hồ Nam (tước đoạt 4 sinh mạng) · lệnh truy nã cấp A Bộ Công an · 10 ngày truy bắt xuyên 4 tỉnh tới Tuyền Châu, Phúc Kiến và Tòa án Trường Sa tuyên án tử hình Bành Thủy Dương】 Hồ sơ thật 100% Chuyên án 7·30 tại Trường Sa, Hồ Nam (湖南长沙7·30彭水洋爆炸案, 2010): Sau khi gây án tại Chi cục thuế Đông Đồn Độ chiều 30/7/2010 do bất mãn cá nhân, Bành Thủy Dương bắt xe trốn qua Giang Tây, Quảng Tây rồi sang Phúc Kiến; Bộ Công an phát lệnh truy nã cấp A toàn quốc và bắt giữ hắn tại Tuyền Châu ngày 8/8/2010, Tòa án Trường Sa tuyên án tử hình.",
        "hook_archetype": "countdown_system_breach"
    },
    {
        "id": "vio_cn_hubei_wuhan_zhangminggao_10y",
        "topic_stream": "major_violent_crime",
        "case_real_name_zh": "湖北武汉1991–2000年连环特大悬案10年弹道痕检侦破纪实 — 张明高 (1991–2000)",
        "archival_search_keywords_zh": [
            "武汉 张明高 10年大案 侦破纪实",
            "湖北 12·4大案 张明高 审判 死刑",
            "张明高 刑侦档案 央视"
        ],
        "recommended_vox_verbs": [
            "FORENSIC_ZOOM_CHAIN",
            "DUAL_ERA_LOCK",
            "MICRO_TRACE_MATCH"
        ],
        "title": "[중국 실화 사건] 겨울밤에만 나타나 흔적 없이 사라지던 10년 미제사건 주범이 도심 골목 잡화점 주인이었다니 | 우한 장밍가오 사건 ([Vụ Án Có Thật ở Trung Quốc] Kẻ thủ ác chỉ xuất hiện vào đêm mùa đông suốt 10 năm hóa ra là chủ tiệm bách hóa nhỏ ngay trong ngõ | Đại án Trương Minh Cao Vũ Hán)",
        "topic_anchor": "[중국 실화 사건] 겨울밤에만 나타나 흔적 없이 사라지던 10년 미제사건 주범이 도심 골목 잡화점 주인이었다니 | 우한 장밍가오 사건",
        "winner_cluster": "Luồng 2 · Quy Luật Chỉ Xuất Hiện Vào Tháng Chạp Suốt 10 Năm & Đường Khương Tuyến Kính Hiển Vi Khóa Chặt Trương Minh Cao (우한 10년 미제 장밍가오 사건)",
        "codex_score": 97,
        "profile_score": 97,
        "codex_angle": "Hồ Sơ Thật 100%: Trương Minh Cao & Kỳ Án 10 Năm Tại Vũ Hán (1991–2000) — Khi Hồ Sơ Phân Tích Tâm Lý Không Gian Khoanh Trúng Bán Kính 2km Quanh Hán Khẩu",
        "codex_reasons": [
            "Một trong những chuyên án điều tra dấu vết và tâm lý học tội phạm nổi tiếng nhất của Công an Vũ Hán thập niên 1990, Tòa án Vũ Hán tuyên án tử hình năm 2001",
            "Cực hợp DUAL_ERA_LOCK & FORENSIC_ZOOM_CHAIN"
        ],
        "opening_hook": "1991년부터 9년 동안 우한시에서는 찬 바람이 부는 연말 겨울밤마다 동일한 흔적을 남기는 중대 사건이 잇달아 발생했습니다. 범인은 한 번 나타나면 일 년 내내 감쪽같이 숨어버렸는데, 프로파일러들이 모든 도주 경로의 교차점을 지도 위에 찍자 번화가 골목의 작은 일용품 가게 하나가 떠올랐습니다.",
        "note": "📋 【Hồ sơ vụ án: đại án liên hoàn kéo dài 10 năm tại Vũ Hán, Hồ Bắc · chuyên gia giám định dấu vết và tâm lý hình sự khoanh vùng bắt giữ Trương Minh Cao vào đêm Giao thừa năm 2000 · Tòa án Vũ Hán tuyên án tử hình】 Hồ sơ thật 100% Chuyên án Trương Minh Cao tại Vũ Hán, Hồ Bắc (湖北武汉张明高十年系列特大案件, 1991–2000): Suốt 10 năm từ 1991 đến 2000, Trương Minh Cao chỉ ra tay vào dịp cuối năm rồi quay về ẩn mình dưới vỏ bọc chủ quầy hàng nhỏ và người chồng hiền lành tại Hán Khẩu; Công an Vũ Hán phân tích tọa độ địa lý hiện trường kết hợp giám định dấu vết, bắt gọn Trương Minh Cao và Tòa án Vũ Hán tuyên án tử hình đầu năm 2001.",
        "hook_archetype": "cold_archive_match"
    },
    {
        "id": "vio_cn_heilongjiang_hegang_nanshan_1995",
        "topic_stream": "major_violent_crime",
        "case_real_name_zh": "黑龙江鹤岗1995年1·28南山矿特大案件与烧毁编号390814化学复原侦破纪实 — 田原·田宇·孙海波·闫文宇 (1995)",
        "archival_search_keywords_zh": [
            "鹤岗 1·28大案 田原 孙海波 纪实",
            "黑龙江鹤岗 南山矿 侦破纪实 央视",
            "1995 鹤岗大案 审判 死刑"
        ],
        "recommended_vox_verbs": [
            "SINGLE_EVIDENCE_AUTOPSY",
            "MICRO_TRACE_MATCH",
            "FORENSIC_ZOOM_CHAIN"
        ],
        "title": "[중국 실화 사건] 불에 타 녹아내린 금속 표면에서 화학 시약으로 되살려낸 여섯 자리 일련번호 '390814'의 비밀 | 허강 1·28 사건 ([Vụ Án Có Thật ở Trung Quốc] Dãy số seri 6 chữ số '390814' phục hồi bằng dung dịch hóa học trên khối kim loại bị nung chảy giữa đêm tuyết | Đại án 1·28 Hạc Cương)",
        "topic_anchor": "[중국 실화 사건] 불에 타 녹아내린 금속 표면에서 화학 시약으로 되살려낸 여섯 자리 일련번호 '390814'의 비밀 | 허강 1·28 사건",
        "winner_cluster": "Luồng 2 · Phản Ứng Ăn Mòn Hóa Học Khôi Phục Dãy Số '390814' & 12 Ngày Đêm Phá Đại Án Hạc Cương (헤이룽장 허강 390814 일련번호 복원 사건)",
        "codex_score": 98,
        "profile_score": 98,
        "codex_angle": "Hồ Sơ Thật 100%: Anh Em Điền Nguyên · Tôn Hải Ba & Đại Án 1·28 Hạc Cương, Hắc Long Giang (1995) — Khi Giám Định Kim Tương Học Biến Đống Tro Tàn Thành Danh Sách Nghi Phạm Chính Xác",
        "codex_reasons": [
            "Một trong những đại án hình sự kinh điển nhất lịch sử công an Hắc Long Giang, màn phục hồi số seri kim loại '390814' trong phòng thí nghiệm cực hợp SINGLE_EVIDENCE_AUTOPSY",
            "Tòa án Nhân dân Trung cấp Hạc Cương xét xử công khai trước 30.000 người dân và thi hành án tử hình tháng 3/1995"
        ],
        "opening_hook": "범인들은 모든 단서를 지우기 위해 현장에 불을 지르고 금속 부품의 일련번호까지 줄칼로 깊게 갈아낸 뒤 영하 삼십 도의 눈보라 속으로 사라졌습니다. 하지만 형사 기술진이 불에 그을린 강철 표면에 특수 부식액을 떨어뜨리고 현미경 렌즈를 맞추자, 지워졌던 여섯 자리 숫자 삼구공팔일사가 희미하게 모습을 드러냈습니다.",
        "note": "📋 【Hồ sơ vụ án: đại án 1·28 năm 1995 tại mỏ Nam Sơn, Hạc Cương, Hắc Long Giang (tước đoạt 10 sinh mạng) · kỹ thuật hình sự dùng phản ứng ăn mòn hóa học khôi phục số seri 390814 phá án trong 12 ngày · Tòa án Hạc Cương tuyên án tử hình Điền Nguyên, Tôn Hải Ba, Diêm Văn Vũ】 Hồ sơ thật 100% Đại án 1·28 tại Hạc Cương, Hắc Long Giang (黑龙江鹤岗1995年1·28南山矿特大案 — Điền Nguyên 田原, Điền Vũ 田宇, Tôn Hải Ba 孙海波, Diêm Văn Vũ 闫文宇): Đêm 28/1/1995 (28 Tết), 4 đối tượng tấn công khu bảo vệ mỏ Nam Sơn rồi đốt hiện trường xóa dấu vết; chuyên gia kỹ thuật hình sự phục hồi thành công dãy số seri 390814 bị mài xóa trên kim loại, truy ra nguồn gốc tại nông trường Bảo Tuyền Lĩnh và bắt gọn băng nhóm sau 12 ngày, tuyên án tử hình.",
        "hook_archetype": "micro_forensic_anomaly"
    },
    {
        "id": "vio_cn_hebei_shijiazhuang_zhangyujun_melamine_2008",
        "topic_stream": "major_violent_crime",
        "case_real_name_zh": "河北石家庄三鹿蛋白粉源头制售600吨特大危害公共安全案 — 张玉军·耿金平 (2007–2009)",
        "archival_search_keywords_zh": [
            "张玉军 耿金平 蛋白粉 庭审 今日说法",
            "三鹿事件 源头 张玉军 死刑 央视",
            "石家庄中院 张玉军 审判纪实"
        ],
        "recommended_vox_verbs": [
            "SINGLE_EVIDENCE_AUTOPSY",
            "SCALE_MULTIPLICATION",
            "NETWORK_GRAPH"
        ],
        "title": "[중국 실화 사건] 단백질 수치 검사기만 감쪽같이 속이는 '가짜 마법 가루' 600톤을 지하 창고에서 배합한 남자의 비밀 | 스자좡 장위쥔 사건 ([Vụ Án Có Thật ở Trung Quốc] Pha chế 600 tấn 'bột thần kỳ' trong kho ngầm để đánh lừa máy đo độ đạm và bản án tử hình cho kẻ đầu sỏ | Đại án Trương Ngọc Quân Thạch Gia Trang)",
        "topic_anchor": "[중국 실화 사건] 단백질 수치 검사기만 감쪽같이 속이는 '가짜 마법 가루' 600톤을 지하 창고에서 배합한 남자의 비밀 | 스자좡 장위쥔 사건",
        "winner_cluster": "Luồng 2 · Lỗ Hổng Phương Pháp Đo Nitơ Kjeldahl & Cuộc Truy Nguyên 600 Tấn Bột Công Nghiệp Tới Kho Ngầm Của Trương Ngọc Quân (스자좡 장위쥔·겅진핑 600톤 원료 추적 사건)",
        "codex_score": 99,
        "profile_score": 99,
        "codex_angle": "Hồ Sơ Thật 100%: Trương Ngọc Quân · Cảnh Kim Bình (河北石家庄三鹿源头特大案, 2007–2009) — Khi Ban Chuyên Án Bộ Công An Lần Ngược Chuỗi Cung Ứng Tới Xưởng Pha Chế Bí Mật Ở Sơn Đông",
        "codex_reasons": [
            "Một trong những đại án an toàn cộng đồng chấn động nhất thế kỷ 21 tại Trung Quốc, nguyên lý hóa học đánh lừa máy kiểm nghiệm Kjeldahl cực hợp đồ họa giải phẫu VOX",
            "Tòa án Nhân dân Trung cấp Thạch Gia Trang và Tòa án Tối cao phê chuẩn thi hành án tử hình Trương Ngọc Quân và Cảnh Kim Bình tháng 11/2009"
        ],
        "opening_hook": "물을 잔뜩 타서 묽어진 우유에 이 하얀 가루 한 스푼만 섞으면, 공장의 최첨단 단백질 함량 검사기가 즉시 최고 등급 합격 판정을 내렸습니다. 화학 지식을 악용해 지하 작업장에서 무려 육백 톤의 가짜 단백질 가루를 만들어 전국으로 유통시킨 장위쥔의 비밀 공장을 추적합니다.",
        "note": "📋 【Hồ sơ vụ án: đại án xâm phạm an toàn công cộng đặc biệt nghiêm trọng · Trương Ngọc Quân pha chế 600 tấn bột melamine công nghiệp đánh lừa máy đo độ đạm bán cho Cảnh Kim Bình · Tòa án Thạch Gia Trang tuyên án tử hình cả 2 bị cáo năm 2009】 Hồ sơ thật 100% Đại án nguồn gốc bột đạm giả tại Thạch Gia Trang (Hà Bắc) và Tế Nam (Sơn Đông) (河北石家庄张玉军·耿金平以危险方法危害公共安全案, 2007–2009): Lợi dụng quy trình kiểm tra độ đạm bằng cách đo hàm lượng nguyên tố Nitơ, Trương Ngọc Quân lập xưởng ngầm pha trộn hóa chất công nghiệp melamine với maltodextrin tạo thành hơn 600 tấn 'bột đạm chuyên dụng', còn Cảnh Kim Bình trực tiếp đổ vào bồn sữa nguyên liệu; cả hai bị Tòa án Thạch Gia Trang tuyên án tử hình và thi hành án ngày 24/11/2009.",
        "hook_archetype": "scale_absurdity_collision"
    },
    {
        "id": "vio_cn_shandong_jinan_panghongwei_vaccine_2016",
        "topic_stream": "major_violent_crime",
        "case_real_name_zh": "山东济南跨24省5.7亿元未冷藏疫苗非法经营特大专案 — 庞红卫·孙琪 (2010–2016)",
        "archival_search_keywords_zh": [
            "山东济南 庞红卫 5.7亿 疫苗案 央视新闻",
            "庞红卫 孙琪 庭审 纪实",
            "济南特大非法经营案 侦破"
        ],
        "recommended_vox_verbs": [
            "NETWORK_GRAPH",
            "LEDGER_DIFF_SCRUB",
            "GEO_VECTOR_PURSUIT"
        ],
        "title": "[중국 실화 사건] 집행유예 기간 중 한여름 40도 창고에서 5억 7천만 위안어치 의약품을 24개 성으로 보낸 모녀의 비밀 장부 | 지난 팡훙웨이 사건 ([Vụ Án Có Thật ở Trung Quốc] Đang hưởng án treo vẫn thuê nhà kho nóng 40 độ gửi hàng trăm triệu tệ dược phẩm đi 24 tỉnh và cuốn sổ mật của hai mẹ con | Đại án Bàng Hồng Vệ)",
        "topic_anchor": "[중국 실화 사건] 집행유예 기간 중 한여름 40도 창고에서 5억 7천만 위안어치 의약품을 24개 성으로 보낸 모녀의 비밀 장부 | 지난 팡훙웨이 사건",
        "winner_cluster": "Luồng 2 · Nhà Kho Không Máy Lạnh Nóng 40 Độ C & Cuốn Sổ Giao Dịch 570 Triệu Tệ Phủ Khắp 24 Tỉnh (산둥 지난 팡훙웨이 5.7억 위안 사건)",
        "codex_score": 97,
        "profile_score": 97,
        "codex_angle": "Hồ Sơ Thật 100%: Bàng Hồng Vệ · Tôn Kỳ & Đại Án 570 Triệu NDT Tại Tế Nam, Sơn Đông (2010–2017) — Cuộc Truy Vết Hơn 300 Tài Khoản Ngân Hàng Và Hóa Đơn Chuyển Phát Nhanh Toàn Quốc",
        "codex_reasons": [
            "Chuyên án lớn do Quốc vụ viện và Bộ Công an Trung Quốc trực tiếp chỉ đạo năm 2016, bản đồ mạng lưới phân phối 24 tỉnh và sổ cái 570 triệu NDT cực hợp VOX",
            "Tòa án Nhân dân Trung cấp Tế Nam xét xử công khai và tuyên phạt tổng cộng 19 năm tù đối với Bàng Hồng Vệ"
        ],
        "opening_hook": "영하가 아닌 영상 이 도에서 팔 도 사이의 정밀한 냉장 온도를 유지해야 하는 특수 의약품 수십만 상자가 한여름 실내 온도가 사십 도까지 치솟는 일반 지하 창고에 수북이 쌓여 있었습니다. 이미 같은 죄로 집행유예를 선고받았던 전직 약사 팡훙웨이가 딸과 함께 세운 오억 칠천만 위안 규모의 지하 유통망을 파헤칩니다.",
        "note": "📋 【Hồ sơ vụ án: đại án Bàng Hồng Vệ & con gái Tôn Kỳ đang trong thời gian thử thách án treo vẫn thuê kho thường không bảo quản lạnh để buôn bán 570 triệu tệ vắc-xin xuyên 24 tỉnh · Quốc vụ viện chỉ đạo phá án và Tòa án Tế Nam tuyên án 19 năm tù】 Hồ sơ thật 100% Đại án 570 triệu NDT tại Tế Nam, Sơn Đông (山东济南庞红卫·孙琪5.7亿元非法经营疫苗案, 2010–2017): Từng là dược sĩ bệnh viện tại Hà Trạch và bị phạt tù treo năm 2009, Bàng Hồng Vệ chuyển lên Tế Nam tiếp tục cùng con gái Tôn Kỳ thu mua và vận chuyển dược phẩm bằng thùng xốp thường đi 24 tỉnh thành thu về 570 triệu NDT trước khi bị Công an Tế Nam bắt giữ và tòa tuyên án.",
        "hook_archetype": "cold_archive_match"
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
    min_curated_per_stream: int = 6,
    single_stream_quota: int = 10,
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

    merged_vault: list[dict[str, Any]] = []
    seen_vault_ids: set[str] = set()
    for _v_item in list(VERIFIED_TWO_STREAM_RESERVE_CASES) + dyn_list:
        _v_cid = str(_v_item.get("id") or "").strip()
        if _v_cid and _v_cid in seen_vault_ids:
            continue
        if _v_cid:
            seen_vault_ids.add(_v_cid)
        merged_vault.append(_v_item)

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
        is_prod_dup, _ = _is_duplicate_against_records(
            blob,
            produced_list,
            candidate_id=str(enriched.get("id") or ""),
            enforce_mo_cooldown=False,
        )
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
        ec_cid = str(ec.get("id") or "")
        blob = " ".join([
            str(ec.get("title") or ""),
            str(ec.get("case_real_name_zh") or ""),
            str(ec.get("note") or ""),
        ]).strip()
        if _is_duplicate_against_records(blob, produced_list, candidate_id=ec_cid, enforce_mo_cooldown=False)[0]:
            continue
        if sibling_list and _is_duplicate_against_records(blob, sibling_list, candidate_id=ec_cid, enforce_mo_cooldown=False)[0]:
            continue
        if _is_duplicate_against_records(blob, clean_curated, candidate_id=ec_cid, enforce_mo_cooldown=False)[0]:
            continue
        ec["already_produced"] = False
        clean_curated.append(ec)

    # Rotate vault by profile id + produced_count so each new replenishment advances smoothly
    pid_offset = 36 if "financial-fugitive" in pid else (24 if "director-v2" in pid else (0 if pid else 12))
    rot = (pid_offset + produced_count) % max(1, len(unproduced_vault))
    rotated_unproduced = unproduced_vault[rot:] + unproduced_vault[:rot]

    def _stream_count(items: list[dict[str, Any]], s_id: str) -> int:
        return sum(1 for x in items if x.get("topic_stream") == s_id)

    newly_topped_up: list[dict[str, Any]] = []
    active_target_streams = (locked_single_stream,) if locked_single_stream else ("financial_crime", "major_violent_crime")
    per_stream_quota = max(single_stream_quota, min_curated_per_stream) if locked_single_stream else min_curated_per_stream
    for s_id in active_target_streams:
        for enforce_mo in (True, False):
            if _stream_count(clean_curated, s_id) >= per_stream_quota:
                break
            for cand in rotated_unproduced:
                if _stream_count(clean_curated, s_id) >= per_stream_quota:
                    break
                if cand.get("topic_stream") != s_id:
                    continue
                cand_cid = str(cand.get("id") or "")
                blob = " ".join([
                    str(cand.get("title") or ""),
                    str(cand.get("case_real_name_zh") or ""),
                    str(cand.get("note") or ""),
                ]).strip()
                if enforce_mo and _is_duplicate_against_records(blob, produced_list, candidate_id=cand_cid, enforce_mo_cooldown=True)[0]:
                    continue
                if sibling_list and _is_duplicate_against_records(blob, sibling_list, candidate_id=cand_cid, enforce_mo_cooldown=False)[0]:
                    continue
                if _is_duplicate_against_records(blob, clean_curated, candidate_id=cand_cid, enforce_mo_cooldown=False)[0]:
                    continue
                cand_copy = dict(cand)
                cand_copy["research_origin"] = "auto_replenished_dna_vault"
                clean_curated.append(cand_copy)
                newly_topped_up.append(cand_copy)

    # Interleave clean_curated for balanced display (or keep dedicated single stream)
    if locked_single_stream:
        profile["curated_today_candidates"] = clean_curated[:per_stream_quota]
    else:
        fin_cur = [x for x in clean_curated if x.get("topic_stream") == "financial_crime"]
        vio_cur = [x for x in clean_curated if x.get("topic_stream") == "major_violent_crime"]
        interleaved_cur: list[dict[str, Any]] = []
        for i in range(max(len(fin_cur), len(vio_cur))):
            if i < len(fin_cur):
                interleaved_cur.append(fin_cur[i])
            if i < len(vio_cur):
                interleaved_cur.append(vio_cur[i])
        profile["curated_today_candidates"] = interleaved_cur[: min_curated_per_stream * 2]
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
        "replenished_candidates": [dict(x) for x in newly_topped_up],
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
    note_text = str(item.get("note") or "").strip()
    # Strictly reject anonymous placeholder suspects ('张某', '陈某', '刘某', '某') — every case must have a 100% real full name
    if "某" in zh or "某" in note_text or "某" in title:
        return False
    if re.search(r"\b[가-힣]모\s*(씨|사건)\b", title):
        return False
    # Reject multi-case slash hedging like "Case A案 / Case B案" (violates 1-case-per-video law)
    if "/" in zh:
        case_segments = [seg for seg in zh.split("/") if ("案" in seg or "事件" in seg)]
        if len(case_segments) >= 2:
            return False
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
        "2. TUYỆT ĐỐI CẤM dùng tên viết tắt khuyết danh kiểu `张某`, `陈某`, `刘某`, `王某`, `某` (`장모`, `천모`, `류모`) hoặc bịa chuyện khuyết danh — BẮT BUỘC 100% vụ án phải có HỌ TÊN THẬT ĐẦY ĐỦ của thủ phạm chính đã được tòa án xét xử công khai và báo chí chính thống (`CCTV 今日说法 / 天网 / 一线 / 庭审现场 / 新华社`) đăng tải, CẤM để lẫn chữ Hán/chữ Nhật (`の`, `枚`) vào câu tiếng Hàn hoặc chữ Hàn vào bản dịch tiếng Việt, CẤM dùng `[Số đếm] + 해` (`열여덟 해` -> bắt buộc viết `18년`), và CẤM chọn vụ án nhỏ lẻ không có phóng sự truyền hình (`CCTV 今日说法 / 天网 / 一线 / 庭审现场`).\n"
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
