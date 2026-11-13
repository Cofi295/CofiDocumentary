"""Dedicated Financial & Investigative 2.5D Tactile Vox & GIS Map Engine.

Strictly isolated to `financial_forensic_vox` preset.
Never mix or share these archetypes with True Crime (`forensic_noir`).

Core Principles:
1. Authentic Tactile Vox Craft: Full-bleed paper grain, Financial Times salmon newsprint,
   Manila folders, dark walnut desks, full-screen Esri satellite GIS plates, torn-edge photo
   mounts, hand-drawn Rough.js-style marker circles/arrows, and felt-pen highlighter sweeps.
2. Zero Clutter & 100% Voice Focus: No repetitive outer dashboard boxes, no generic top/bottom
   HUD bars, and no filler text. Every scene focuses solely on the exact numbers, entities,
   and clauses spoken in that specific voice beat.
3. Strict Zero-Repetition (`max_uses = 1`): All 24 archetypes (`#FIN01` .. `#FIN24`) have
   completely distinct full-screen surfaces and geometries, and each can be used at most once
   per video.
"""

from __future__ import annotations

import math
import re
from typing import Any
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

from documentary.vox_engine.archetypes import (
    W,
    H,
    VOX_CRIMSON,
    VOX_INK,
    _draw_circular_official_seal,
    _draw_paperclip,
    _draw_pushpin,
    _extract_voice_clauses_and_windows,
    draw_cinema_subtitle,
    draw_geojson_feature_on_plate,
    draw_text_safe,
    ease_in_out_cubic,
    ease_out_cubic,
    fit_crop,
    get_cork_pinboard_shell,
    get_dark_investigation_desk,
    get_fallback_image,
    get_torn_paper_sheet,
    paste_photo_polaroid,
)
from documentary.vox_engine.gis_cache import get_vox_styled_gansu_base, load_gis_json, load_gis_plate


FINANCIAL_VOX_ARCHETYPE_RULES: dict[str, dict[str, Any]] = {
    "#FIN01_SPLINE_CLIFF_DIVERGENCE": {
        "cluster": "financial_spline_chart",
        "label": "Full-Bleed FT Salmon Paper: Promised Yield Curve vs Cliff Collapse",
        "regex_ko": r"(수익률\s*곡선|가짜\s*수익|미끼\s*입금|0\.3초\s*만에|잔고\s*0원|통장\s*잔고|계좌\s*감사\s*원장|배당금\s*입금|원금\s*전액\s*이체|출금\s*차단|수익.*급등|절벽.*추락)",
        "regex_vi": r"(biểu\s*đồ\s*lãi\s*ảo|lãi\s*suất\s*ảo|mồi\s*nhử\s*tiền\s*lãi|0[.,]3\s*giây|số\s*dư\s*0|sổ\s*cái\s*ngân\s*hàng|chặn\s*rút\s*tiền|rơi\s*thẳng\s*đứng)",
        "priority_score": 106,
    },
    "#FIN02_SANKEY_LAUNDERING_FLOW": {
        "cluster": "sankey_laundering_flow",
        "label": "Warm Editorial Grid: Tactile Sankey Ribbon Flow Between Evidence Photos",
        "regex_ko": r"(환치기|대포통장.*쪼개기|테더.*비트코인|위안화.*파운드|4단계.*환전|자금\s*세탁\s*흐름|파이프라인|다단계\s*이체|분산\s*송금|불법\s*환전)",
        "regex_vi": r"(quy\s*đổi\s*ngoại\s*tệ|tài\s*khoản\s*rác|chia\s*nhỏ\s*dòng\s*tiền|rửa\s*tiền|luồng\s*tiền|chuyển\s*tiền\s*đa\s*tầng)",
        "priority_score": 105,
    },
    "#FIN03_WAFFLE_DOT_PROPORTION": {
        "cluster": "waffle_dot_matrix",
        "label": "Editorial Cream Paper: 10x10 Tactile Waffle Grid & Giant Highlighted Ratio",
        "regex_ko": r"(95\.6%|207개.*196개|84명.*83명|바람잡이|비율.*조작|전수\s*감사\s*결과|허위\s*비중|압도적\s*비율|가짜\s*기업\s*비율)",
        "regex_vi": r"(95[.,]6%|207.*196|84\s*người.*83|quân\s*xanh|tỷ\s*lệ\s*ảo|ma\s*trận\s*tỷ\s*trọng|kiểm\s*toán\s*toàn\s*bộ)",
        "priority_score": 105,
    },
    "#FIN04_GIS_25D_CROSSBORDER_ARC": {
        "cluster": "gis_crossborder_flight",
        "label": "Full-Screen Continental Satellite GIS & Great-Circle Escape Arc with Pinned Stills",
        "regex_ko": r"(대륙\s*횡단|국경.*넘어|톈진.*미얀마|두바이.*런던|허페이.*와방|해외\s*도피\s*루트|초국가\s*자금\s*추적|유라시아.*지도|도피\s*경로)",
        "regex_vi": r"(xuyên\s*lục\s*địa|xuyên\s*biên\s*giới|bản\s*đồ\s*dòng\s*tiền|Thiên\s*Tân.*Myanmar|Dubai.*London|lộ\s*trình\s*đào\s*tẩu)",
        "priority_score": 104,
    },
    "#FIN05_GIS_OPTICAL_LOUPE_RECON": {
        "cluster": "gis_optical_loupe",
        "label": "Full-Screen High-Res Satellite Recon & 2.5x Optical Loupe with Torn Photo Callout",
        "regex_ko": r"(위성\s*사진|광학\s*루페|정밀\s*판독|야산.*매립|굴착기.*GPS|국경\s*범죄단지|위성\s*좌표|현장\s*특정|외곽\s*황무지)",
        "regex_vi": r"(ảnh\s*vệ\s*tinh|kính\s*lúp\s*quang\s*học|tọa\s*độ\s*GPS|máy\s*xúc|đặc\s*khu\s*biên\s*giới|soi\s*vệ\s*tinh)",
        "priority_score": 104,
    },
    "#FIN06_RADIAL_SHELL_HUB_NETWORK": {
        "cluster": "radial_shell_network",
        "label": "Detective Corkboard: Polaroid Core Photo & Red-String Shell Company Web",
        "regex_ko": r"(페이퍼\s*컴퍼니|유령\s*회사|지배\s*구조|핵심\s*지휘부|조직도|다단계\s*법인|차명\s*법인망|거미줄.*통제|자회사\s*네트워크)",
        "regex_vi": r"(công\s*ty\s*ma|công\s*ty\s*vỏ\s*bọc|mạng\s*lưới\s*chân\s*rết|sơ\s*đồ\s*tổ\s*chức|cấu\s*trúc\s*điều\s*hành)",
        "priority_score": 103,
    },
    "#FIN07_TACTILE_LEDGER_HIGHLIGHT": {
        "cluster": "tactile_ledger_highlight",
        "label": "Dark Walnut Desk: Tilted Physical Bank Statement & Pop-Out Highlighted Clause",
        "regex_ko": r"(비밀\s*장부|회계\s*원장|거래\s*내역서|입출금\s*명세|형광펜|발췌\s*대조|수기\s*장부|1,200권|계좌\s*추적표)",
        "regex_vi": r"(sổ\s*cái\s*bí\s*mật|sao\s*kê\s*giao\s*dịch|bút\s*dạ\s*quang|trích\s*xuất\s*sổ\s*sách|1\.200\s*cuốn\s*sổ)",
        "priority_score": 103,
    },
    "#FIN08_PONZI_PYRAMID_FRACTURE": {
        "cluster": "ponzi_pyramid_fracture",
        "label": "Manila Dossier Paper: Papercraft 3-Tier Ponzi Pyramid & Red Fracture Line",
        "regex_ko": r"(폰지\s*사기|돌려막기|다단계\s*피라미드|하위\s*투자자|신규\s*원금.*이자|피라미드\s*붕괴|연쇄\s*도산|유동성\s*고갈)",
        "regex_vi": r"(mô\s*hình\s*Ponzi|lấy\s*người\s*sau\s*trả\s*người\s*trước|tháp\s*đa\s*cấp|vỡ\s*trận\s*thanh\s*khoản|sụp\s*đổ\s*dây\s*chuyền)",
        "priority_score": 102,
    },
    "#FIN09_STRATA_CROSS_SECTION_6M": {
        "cluster": "strata_cross_section",
        "label": "Full-Bleed Underground Geological Cross-Section (0m Surface to -6m Hidden Vault)",
        "regex_ko": r"(지하\s*6미터|땅속.*묻|단면도|금속탐지기|점토층|진공\s*포장\s*마대|지하\s*금고|20시간.*발굴|심야\s*매립)",
        "regex_vi": r"(dưới\s*lòng\s*đất\s*6\s*mét|mặt\s*cắt\s*địa\s*chất|máy\s*dò\s*kim\s*loại|chôn\s*giấu|hầm\s*ngầm|khai\s*quật\s*20\s*giờ)",
        "priority_score": 104,
    },
    "#FIN10_DUAL_GAUGE_RATE_CONTRAST": {
        "cluster": "dual_gauge_contrast",
        "label": "50/50 Split-Screen Editorial Contrast: Legal Bank Rate vs Fraudulent Bait Rate",
        "regex_ko": r"(시중은행\s*금리|정기예금.*비교|연\s*14\.6%|연\s*24%|금리\s*격차|8\.7배|확정\s*고수익|이자율\s*비교)",
        "regex_vi": r"(lãi\s*suất\s*ngân\s*hàng|so\s*sánh\s*lãi\s*suất|14[.,]6%|24%/năm|chênh\s*lệch\s*lãi\s*suất|gấp\s*8[.,]7\s*lần)",
        "priority_score": 102,
    },
    "#FIN11_ISOMETRIC_PILLAR_COMPARISON": {
        "cluster": "isometric_pillar_compare",
        "label": "Architectural Isometric Grid: 2.5D Extruded Columns with Long Cast Shadows",
        "regex_ko": r"(누적\s*모금액|18개월\s*만에|500억\s*위안|598억\s*위안|단계별\s*폭증|규모\s*비교|예치금\s*급증|자금\s*규모)",
        "regex_vi": r"(tổng\s*vốn\s*huy\s*động|sau\s*18\s*tháng|50\s*tỷ\s*NDT|tăng\s*trưởng\s*nóng|so\s*sánh\s*quy\s*mô)",
        "priority_score": 101,
    },
    "#FIN12_GIS_REGIONAL_RIPPLE_HEATMAP": {
        "cluster": "gis_regional_ripple",
        "label": "Full-Screen Regional Satellite GIS + Glowing Province Border & Shockwave Rings",
        "regex_ko": r"(전국\s*31개\s*성|90만\s*명|12만\s*8천\s*명|전역\s*확산|피해자\s*분포|은퇴자.*확산|지역별\s*피해|집단\s*패닉)",
        "regex_vi": r"(31\s*tỉnh\s*thành|900\.000\s*nạn\s*nhân|128\.000\s*người|lan\s*rộng\s*toàn\s*quốc|bản\s*đồ\s*thiệt\s*hại)",
        "priority_score": 102,
    },
    "#FIN13_XRAY_FACADE_VS_REALITY": {
        "cluster": "xray_facade_split",
        "label": "Full-Screen Photo X-Ray Wipe: Golden Propaganda Facade vs Dark Insolvency Core",
        "regex_ko": r"(두\s*얼굴|화려한\s*외피|인민대회당|국영\s*방송\s*광고|1억\s*3천만\s*위안\s*광고|속\s*빈\s*강정|위장된\s*제국|광고\s*세뇌)",
        "regex_vi": r"(hai\s*bộ\s*mặt|vỏ\s*bọc\s*hào\s*nhoáng|quảng\s*cáo\s*đài\s*truyền\s*hình|Đại\s*hội\s*đường|ruột\s*rỗng)",
        "priority_score": 102,
    },
    "#FIN14_HORIZONTAL_STEPPER_TIMELINE": {
        "cluster": "horizontal_stepper_timeline",
        "label": "Panoramic Archival Scroll: 3-Stop Chronological Photo & Red-Marker Timeline",
        "regex_ko": r"(연표|시간순|1차.*2차.*3차|2만\s*위안.*10만\s*위안.*80만\s*위안|단계별\s*유인|타임라인|순차적\s*진행)",
        "regex_vi": r"(trục\s*thời\s*gian|theo\s*trình\s*tự|bước\s*1.*bước\s*2.*bước\s*3|từng\s*giai\s*đoạn|biên\s*niên\s*sử)",
        "priority_score": 101,
    },
    "#FIN15_FORGED_SEAL_MICRO_COMPARATOR": {
        "cluster": "forged_seal_comparator",
        "label": "Forensic Optical Lightbox: Dual Circular Microscope Lenses Comparing Seals & Photos",
        "regex_ko": r"(가짜\s*인감|위조\s*계약서|공문서\s*위조|도장.*위조|허위\s*이력|계약서\s*날인|진위\s*대조|감정\s*결과)",
        "regex_vi": r"(con\s*dấu\s*giả|hợp\s*đồng\s*giả\s*mạo|làm\s*giả\s*giấy\s*tờ|đối\s*chiếu\s*con\s*dấu|hồ\s*sơ\s*ngụy\s*tạo)",
        "priority_score": 102,
    },
    "#FIN16_WATERFALL_DEFICIT_CASCADE": {
        "cluster": "waterfall_deficit_cascade",
        "label": "Editorial Ledger Paper: 3-Step Waterfall Asset Drain & Hand-Drawn Deficit Arrow",
        "regex_ko": r"(환급률\s*35%|미상환\s*380억|230억\s*위안.*탕진|회수\s*불능|손실\s*정산|원금\s*대비\s*환수|남겨진\s*피해)",
        "regex_vi": r"(tỷ\s*lệ\s*hoàn\s*trả\s*35%|không\s*thể\s*thu\s*hồi|tiêu\s*xài\s*hoang\s*phí|thác\s*nước\s*thâm\s*hụt|còn\s*lại\s*35%)",
        "priority_score": 102,
    },
    "#FIN17_BLOCKCHAIN_TUMBLER_SPLITTER": {
        "cluster": "blockchain_tumbler_splitter",
        "label": "Dark Blueprint Grid: Master Wallet Dispersion into Cold Wallets with Evidence Card",
        "regex_ko": r"(61,000\s*BTC|콜드월렛|믹서|텀블러|블록체인\s*추적|하드웨어\s*지갑|가상자산\s*은닉|지갑\s*분할)",
        "regex_vi": r"(61\.000\s*BTC|ví\s*lạnh|trộn\s*coin|추적\s*blockchain|chia\s*nhỏ\s*ví\s*điện\s*tử|tài\s*sản\s*mã\s*hóa)",
        "priority_score": 103,
    },
    "#FIN18_JUDICIAL_VERDICT_STAMP_SCROLL": {
        "cluster": "judicial_verdict_stamp",
        "label": "Double-Red-Border Court Verdict Document with Suspect Photo & Official Seal",
        "regex_ko": r"(무기징역|종신형|징역\s*15년|징역\s*11년|중급인민법원|공소장|판결문|법정\s*선고|전\s*재산\s*몰수)",
        "regex_vi": r"(tù\s*chung\s*thân|15\s*năm\s*tù|tòa\s*án\s*nhân\s*dân|bản\s*cáo\s*trạng|tuyên\s*án|tịch\s*thu\s*toàn\s*bộ\s*tài\s*sản)",
        "priority_score": 104,
    },
    "#FIN19_RADAR_ANOMALY_SPIKE_CHART": {
        "cluster": "radar_anomaly_spike",
        "label": "Seismograph Paper Strip: Flat Baseline vs Giant Red Anomaly Spike & Photo Proof",
        "regex_ko": r"(40배.*전력|전기세.*폭증|이상\s*징후|스파이크|비정상\s*급증|트래픽\s*폭주|서버\s*과부하|변압기)",
        "regex_vi": r"(tiền\s*điện\s*gấp\s*40|đột\s*biến\s*bất\s*thường|xung\s*đột\s*biến|quá\s*tải\s*máy\s*chủ|tăng\s*vọt\s*40\s*lần)",
        "priority_score": 101,
    },
    "#FIN20_BALANCE_SCALE_ASYMMETRY": {
        "cluster": "balance_scale_asymmetry",
        "label": "Minimalist Editorial Fulcrum: Crushing Red Debt Block vs Zero Real Collateral",
        "regex_ko": r"(담보\s*0원|자융자담|자체\s*보증|불균형|실물\s*자산\s*전무|부실\s*채권|위험\s*전가|무담보)",
        "regex_vi": r"(tài\s*sản\s*đảm\s*bảo\s*bằng\s*0|tự\s*huy\s*động\s*tự\s*bảo\s*lãnh|mất\s*cân\s*đối|nợ\s*xấu\s*khổng\s*lồ)",
        "priority_score": 100,
    },
    "#FIN21_CONCENTRIC_ONION_LAYERS": {
        "cluster": "concentric_onion_layers",
        "label": "Tactile Cutout Paper Rings: 3-Layer Concentric Deconstruction into Core Photo",
        "regex_ko": r"(3중\s*방어막|위장\s*구조|다층\s*은폐|껍질을\s*벗기|내부\s*고발|핵심\s*코어|심층\s*해부)",
        "regex_vi": r"(3\s*lớp\s*vỏ\s*bọc|bóc\s*tách\s*từng\s*lớp|che\s*giấu\s*đa\s*tầng|lõi\s*tội\s*phạm)",
        "priority_score": 100,
    },
    "#FIN22_ASSET_SEIZURE_TREEMAP": {
        "cluster": "asset_seizure_treemap",
        "label": "Full-Bleed Editorial Collage Treemap of Seized Real Estate, Gold & Crypto",
        "regex_ko": r"(핑크\s*다이아몬드|전용기|런던.*대저택|금괴|호화\s*사치품|압수\s*목록|동결\s*자산\s*구분|150억\s*위안\s*환수)",
        "regex_vi": r"(kim\s*cương\s*hồng|chuyên\s*cơ|biệt\s*thự\s*London|vàng\s*thỏi|danh\s*mục\s*tài\s*sản\s*tịch\s*thu)",
        "priority_score": 102,
    },
    "#FIN23_GIS_CORRIDOR_ELEVATION_TRACE": {
        "cluster": "gis_corridor_elevation",
        "label": "Full-Screen Basin Satellite Route + Synchronized Bottom Elevation/Speed Profile",
        "regex_ko": r"(새벽\s*2시.*승합차|붉은\s*진흙|타이어\s*흔적|이동\s*궤적|왕복\s*3시간|교외\s*추적|차량\s*동선)",
        "regex_vi": r"(2\s*giờ\s*sáng.*xe\s*tải|bùn\s*đỏ\s*bám\s*lốp|quỹ\s*đạo\s*di\s*chuyển|3\s*tiếng\s*khứ\s*hồi|theo\s*dấu\s*xe)",
        "priority_score": 102,
    },
    "#FIN24_RED_FLAG_EDITORIAL_CHECKLIST": {
        "cluster": "red_flag_checklist",
        "label": "Special Audit Dossier Sheet: Pinned Case Photo & 3 Hand-Checked Red Flags",
        "regex_ko": r"(제1법칙|제2법칙|제3법칙|경고\s*신호|사기\s*식별|예방\s*원칙|기억해야\s*할\s*교훈|체크리스트)",
        "regex_vi": r"(nguyên\s*tắc\s*số\s*1|dấu\s*hiệu\s*nhận\s*biết|bài\s*học\s*cảnh\s*giác|quy\s*tắc\s*bảo\s*vệ\s*vốn)",
        "priority_score": 101,
    },
    # Legacy aliases preserved for backward compatibility
    "#FIN1_DUAL_CURVE_LEDGER": {
        "cluster": "financial_spline_chart",
        "label": "Financial Dual-Curve Area Chart & Bank Audit Ledger",
        "regex_ko": r"(수익률\s*곡선|잔고\s*0원)",
        "regex_vi": r"(biểu\s*đồ\s*lãi\s*ảo|số\s*dư\s*0)",
        "priority_score": 95,
    },
    "#FIN2_CURRENCY_FLOW_BALANCE": {
        "cluster": "sankey_laundering_flow",
        "label": "4-Stage Multi-Currency Laundering Flow",
        "regex_ko": r"(환치기|자금\s*세탁\s*흐름표)",
        "regex_vi": r"(rửa\s*tiền\s*qua\s*USDT|bảng\s*cân\s*đối\s*ngoại\s*tệ)",
        "priority_score": 95,
    },
    "#FIN3_ASSET_FREEZE_PORTFOLIO": {
        "cluster": "waffle_dot_matrix",
        "label": "Proportional Asset & Shell Matrix",
        "regex_ko": r"(동결\s*자산\s*포트폴리오)",
        "regex_vi": r"(danh\s*mục\s*tài\s*sản\s*phong\s*tỏa)",
        "priority_score": 95,
    },
    "#FIN4_FULLSCREEN_EURASIA_MONEY_MAP": {
        "cluster": "gis_crossborder_flight",
        "label": "Full-Screen Cross-Border Money Trail GIS Map Flight",
        "regex_ko": r"(유라시아.*자금\s*지도)",
        "regex_vi": r"(bản\s*đồ\s*dòng\s*tiền\s*xuyên\s*quốc\s*gia)",
        "priority_score": 95,
    },
    "#FIN5_OVERSIZED_PHONE_SHILL_EXPOSE": {
        "cluster": "radial_shell_network",
        "label": "Syndicate Manipulation Network",
        "regex_ko": r"(단톡방\s*사기극)",
        "regex_vi": r"(màn\s*kịch\s*nhóm\s*chat)",
        "priority_score": 95,
    },
    "#FIN6_SATELLITE_COMPOUND_POWER_ANOMALY": {
        "cluster": "gis_optical_loupe",
        "label": "Satellite Recon & Power Anomaly Loupe",
        "regex_ko": r"(전력\s*소비량\s*비교)",
        "regex_vi": r"(tiêu\s*thụ\s*điện\s*năng\s*đột\s*biến)",
        "priority_score": 95,
    },
}

CANONICAL_24_FIN_ARCHETYPES: list[str] = [
    f"#FIN{i:02d}_{suffix}"
    for i, suffix in enumerate(
        [
            "SPLINE_CLIFF_DIVERGENCE",
            "SANKEY_LAUNDERING_FLOW",
            "WAFFLE_DOT_PROPORTION",
            "GIS_25D_CROSSBORDER_ARC",
            "GIS_OPTICAL_LOUPE_RECON",
            "RADIAL_SHELL_HUB_NETWORK",
            "TACTILE_LEDGER_HIGHLIGHT",
            "PONZI_PYRAMID_FRACTURE",
            "STRATA_CROSS_SECTION_6M",
            "DUAL_GAUGE_RATE_CONTRAST",
            "ISOMETRIC_PILLAR_COMPARISON",
            "GIS_REGIONAL_RIPPLE_HEATMAP",
            "XRAY_FACADE_VS_REALITY",
            "HORIZONTAL_STEPPER_TIMELINE",
            "FORGED_SEAL_MICRO_COMPARATOR",
            "WATERFALL_DEFICIT_CASCADE",
            "BLOCKCHAIN_TUMBLER_SPLITTER",
            "JUDICIAL_VERDICT_STAMP_SCROLL",
            "RADAR_ANOMALY_SPIKE_CHART",
            "BALANCE_SCALE_ASYMMETRY",
            "CONCENTRIC_ONION_LAYERS",
            "ASSET_SEIZURE_TREEMAP",
            "GIS_CORRIDOR_ELEVATION_TRACE",
            "RED_FLAG_EDITORIAL_CHECKLIST",
        ],
        start=1,
    )
]


def is_financial_vox_enabled(job: dict[str, Any], profile: dict[str, Any] | None = None) -> bool:
    """Strictly activates via editing_dna.financial_vox_enabled capability flag, preset_id, or legacy fallback."""
    for cand_ed in (
        job.get("editing_dna"),
        (profile or {}).get("editing_dna") if isinstance(profile, dict) else None,
        (job.get("channel_profile_snapshot") or {}).get("editing_dna") if isinstance(job.get("channel_profile_snapshot"), dict) else None,
    ):
        if isinstance(cand_ed, dict) and isinstance(cand_ed.get("financial_vox_enabled"), bool):
            return bool(cand_ed["financial_vox_enabled"])
    profile_id = str(
        job.get("channel_profile_id")
        or (profile or {}).get("id")
        or (job.get("channel_profile_snapshot") or {}).get("id")
        or ""
    ).strip()
    if profile_id == "channel-cn-cyber-finance-kr":
        return True
    if profile_id in {"channel-e544a64b7c", "channel-kr-truecrime-director-v2", "channel-kr-financial-fugitive-director-v2"}:
        return False
    preset_id = str(
        (job.get("editing_dna") or {}).get("preset_id")
        or ((profile or {}).get("editing_dna") or {}).get("preset_id")
        or (job.get("channel_profile_snapshot") or {}).get("editing_dna", {}).get("preset_id")
        or ""
    ).strip().lower()
    if preset_id == "financial_forensic_vox":
        return True
    strategy = str(
        job.get("visual_strategy")
        or (profile or {}).get("visual_strategy")
        or ""
    ).strip().lower()
    if "cyber_finance" in strategy or "financial" in strategy:
        return True
    niche = str(
        job.get("niche")
        or (profile or {}).get("niche")
        or (job.get("channel_profile_snapshot") or {}).get("niche")
        or ""
    ).strip().lower()
    return "financial" in niche and "crime" in niche


# ==============================================================================
# TACTILE PAPER SURFACES, TORN PHOTO MOUNTS & HAND-DRAWN ROUGH ANNOTATIONS
# ==============================================================================

_BG_CACHE: dict[tuple[Any, ...], Image.Image] = {}


def _make_tactile_bg(
    base_rgb: tuple[int, int, int],
    grain_sigma: float = 4.2,
    grid_type: str = "dots",
    seed: int = 10,
) -> Image.Image:
    """Creates a full-bleed 1920x1080 tactile paper/board canvas with organic fiber grain & vignette."""
    key = (base_rgb, round(grain_sigma, 1), grid_type, seed)
    if key in _BG_CACHE:
        return _BG_CACHE[key].copy()

    rng = np.random.default_rng(seed)
    sw, sh = W // 4, H // 4
    yy, xx = np.mgrid[0:sh, 0:sw]
    nx = (xx - sw * 0.5) / (sw * 0.62)
    ny = (yy - sh * 0.5) / (sh * 0.62)
    vignette = (1.0 - np.clip((nx * nx + ny * ny) * 0.14, 0, 0.24))[:, :, None]
    noise = rng.normal(0.0, grain_sigma, (sh, sw, 1))
    arr = np.clip((np.array(base_rgb, dtype=np.float32) + noise) * vignette, 0, 255).astype(np.uint8)
    canvas = Image.fromarray(arr, "RGB").resize((W, H), Image.Resampling.BICUBIC)
    draw = ImageDraw.Draw(canvas, "RGBA")

    is_light = sum(base_rgb) > 380
    if grid_type == "dots":
        col = (30, 28, 24, 38) if is_light else (148, 163, 184, 34)
        for gx in range(72, W - 48, 64):
            for gy in range(72, H - 48, 64):
                draw.ellipse([gx - 1, gy - 1, gx + 2, gy + 2], fill=col)
    elif grid_type == "lines":
        col = (30, 28, 24, 20) if is_light else (56, 189, 248, 22)
        for gx in range(0, W, 80):
            draw.line([(gx, 0), (gx, H)], fill=col, width=1)
        for gy in range(0, H, 80):
            draw.line([(0, gy), (W, gy)], fill=col, width=1)
    elif grid_type == "newsprint":
        # Vertical broadsheet column dividers
        col = (40, 34, 28, 28)
        for gx in (480, 960, 1440):
            draw.line([(gx, 60), (gx, H - 60)], fill=col, width=1)

    _BG_CACHE[key] = canvas
    return canvas.copy()


def _paste_torn_photo(
    canvas: Image.Image,
    img: Image.Image | None,
    x: int,
    y: int,
    w: int,
    h: int,
    caption: str = "",
    badge: str = "",
    pin_color: tuple[int, int, int] | None = (185, 28, 28),
    paperclip: bool = False,
    seed: int = 21,
) -> None:
    """Mounts a real evidence photo onto a tactile torn-edge paper card with soft drop shadow."""
    src = img if isinstance(img, Image.Image) else get_fallback_image(w, h, caption[:14] or "EVIDENCE")
    pad = 16
    bot_pad = 58 if caption else 18
    sheet = get_torn_paper_sheet(w + pad * 2, h + pad + bot_pad, fill_rgb=(250, 246, 238), roughness=3.2, seed=seed)
    cropped = fit_crop(src.convert("RGB"), w, h)
    # Subtle archival contrast
    cropped = ImageEnhance.Contrast(cropped).enhance(1.06)
    sheet.paste(cropped.convert("RGBA"), (28 + pad, 28 + pad))
    sdraw = ImageDraw.Draw(sheet, "RGBA")
    sdraw.rectangle([28 + pad, 28 + pad, 28 + pad + w, 28 + pad + h], outline=(40, 36, 32, 90), width=1)

    if badge:
        bw = max(90, min(260, len(badge) * 18 + 26))
        sdraw.rectangle([28 + pad + 10, 28 + pad + 10, 28 + pad + 10 + bw, 28 + pad + 42], fill=(185, 28, 28, 238))
        draw_text_safe(sdraw, (28 + pad + 20, 28 + pad + 14), badge[:16], fill=(255, 255, 255, 255), font_size=16, bold=True)

    if caption:
        sdraw.rectangle([28 + pad, 28 + pad + h + 10, 28 + pad + 5, 28 + pad + h + 42], fill=(185, 28, 28, 255))
        draw_text_safe(sdraw, (28 + pad + 14, 28 + pad + h + 12), caption[:32], fill=(24, 22, 19, 255), font_size=20, bold=True)

    canvas.paste(sheet, (x - 28, y - 28), sheet)
    draw = ImageDraw.Draw(canvas, "RGBA")
    if pin_color is not None:
        _draw_pushpin(draw, x + w // 2 + pad, y + 6, color=pin_color)
    if paperclip:
        _draw_paperclip(draw, x + 28, y - 8, tall=54)


def _draw_hand_circle(
    draw: ImageDraw.ImageDraw,
    cx: int,
    cy: int,
    rx: int,
    ry: int,
    color: tuple[int, int, int] = (210, 32, 32),
    width: int = 5,
    p: float = 1.0,
) -> None:
    """Draws an organic double-loop hand-drawn red marker circle (`roughjs` aesthetic)."""
    steps = max(12, int(64 * min(1.0, max(0.15, p))))
    for loop_offset, alpha in ((0.0, 235), (0.045, 165)):
        pts = []
        for i in range(steps + 1):
            ang = -math.pi * 0.35 + (i / 64.0) * (math.pi * 2.15)
            wobble = 1.0 + loop_offset * math.sin(ang * 3.0 + 1.2)
            px = cx + int(rx * wobble * math.cos(ang))
            py = cy + int(ry * wobble * math.sin(ang))
            pts.append((px, py))
        if len(pts) >= 2:
            draw.line(pts, fill=color + (alpha,), width=width)


def _draw_hand_arrow(
    draw: ImageDraw.ImageDraw,
    x0: int,
    y0: int,
    x1: int,
    y1: int,
    color: tuple[int, int, int] = (210, 32, 32),
    width: int = 5,
    curve_lift: int = -38,
) -> None:
    """Draws a curved hand-drawn marker arrow from (x0, y0) to (x1, y1)."""
    mx = (x0 + x1) // 2
    my = (y0 + y1) // 2 + curve_lift
    pts = []
    for i in range(25):
        t = i / 24.0
        px = int((1 - t) ** 2 * x0 + 2 * (1 - t) * t * mx + t ** 2 * x1)
        py = int((1 - t) ** 2 * y0 + 2 * (1 - t) * t * my + t ** 2 * y1)
        pts.append((px, py))
    draw.line(pts, fill=color + (235,), width=width)
    ang = math.atan2(y1 - my, x1 - mx)
    for wing in (-2.55, 2.55):
        wx = int(x1 + 22 * math.cos(ang + wing))
        wy = int(y1 + 22 * math.sin(ang + wing))
        draw.line([(x1, y1), (wx, wy)], fill=color + (235,), width=width)


def _draw_felt_highlighter(
    draw: ImageDraw.ImageDraw,
    x0: int,
    y0: int,
    w: int,
    h: int,
    p: float = 1.0,
    color: tuple[int, int, int] = (250, 204, 21),
    alpha: int = 160,
) -> None:
    """Draws a voice-synced translucent yellow felt-marker sweep."""
    cur_w = max(8, int(w * min(1.0, max(0.08, p))))
    draw.rounded_rectangle([x0, y0, x0 + cur_w, y0 + h], radius=6, fill=color + (alpha,))


def _load_sat_fullbleed(plate_name: str, brightness: float = 0.88, contrast: float = 1.08) -> Image.Image:
    """Loads a real cached Esri satellite plate scaled to full-screen 1920x1080."""
    clean_name = str(plate_name).replace(".png", "").strip()
    res = load_gis_plate(clean_name)
    img = res[0] if isinstance(res, tuple) else res
    if isinstance(img, Image.Image):
        full = fit_crop(img.convert("RGB"), W, H)
        full = ImageEnhance.Brightness(full).enhance(brightness)
        full = ImageEnhance.Contrast(full).enhance(contrast)
        return full
    return _make_tactile_bg((18, 26, 36), grain_sigma=5.0, grid_type="lines", seed=99)


def _clean_phrase(text: str, max_chars: int = 28) -> str:
    """Truncates at a clean word boundary so Korean words are never sliced mid-syllable."""
    t = str(text or "").strip()
    if len(t) <= max_chars:
        return t
    cut = t[:max_chars]
    last_space = cut.rfind(" ")
    if last_space >= max_chars // 2:
        return cut[:last_space].rstrip("·,.")
    return cut.rstrip("·,.")


def _draw_editorial_title_banner(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    kicker: str,
    headline: str,
    on_dark: bool = False,
    on_sat: bool = False,
    accent: tuple[int, int, int] = (190, 24, 24),
) -> None:
    """Draws a clean, frameless Vox newspaper/editorial headline (with torn/backing strip on satellite maps)."""
    clean_head = _clean_phrase(headline, 30)
    if on_sat:
        draw.rounded_rectangle([x - 12, y - 10, x + 860, y + 88], radius=8, fill=(14, 18, 24, 215))
    draw.rectangle([x, y, x + 8, y + 76], fill=accent + (255,))
    k_col = (250, 204, 21, 245) if (on_dark or on_sat) else accent + (255,)
    h_col = (248, 250, 252, 255) if (on_dark or on_sat) else (20, 20, 18, 255)
    draw_text_safe(draw, (x + 22, y + 2), kicker[:38], fill=k_col, font_size=19, bold=True)
    draw_text_safe(draw, (x + 22, y + 30), clean_head, fill=h_col, font_size=34, bold=True)


# ==============================================================================
# FLEXIBLE CLAUSE-ADAPTIVE PLANNER (1..N CLAUSES & PROGRESSIVE SUB-BEAT SYNC)
# ==============================================================================

_CLAUSE_METRIC_RE = re.compile(
    r"(\d{1,2}시\s*\d{1,2}분|\d{1,2}:\d{2}|\d{4}년\s*\d{1,2}월\s*\d{1,2}일|\d{4}년|\d+(?:,\d+)*(?:\.\d+)?\s*(?:조\s*\d+(?:,\d+)*억\s*원|조\s*원|억\s*위안|만\s*위안|위안|억\s*원|만\s*원|원|억\s*파운드|만\s*파운드|파운드|달러|BTC|비트코인|만\s*명|천\s*명|명|만\s*개|천\s*개|개|만\s*대|대|건|회|곳|배|단계|개국|톤|그램|g|kg|도|℃|시간|분|초|개월|일|년|층|호|동|m|km|%))"
)


def _derive_third_photo(
    frame_a: Image.Image | None,
    frame_b: Image.Image | None,
    voice_spec: dict[str, Any] | None,
) -> Image.Image | None:
    """Resolves a 3rd evidence photo (`_frame_c`) or creates a zoomed forensic detail crop."""
    fc = (voice_spec or {}).get("_frame_c")
    if isinstance(fc, Image.Image):
        return fc
    base = frame_b if isinstance(frame_b, Image.Image) else frame_a
    if isinstance(base, Image.Image):
        bw, bh = base.size
        if bw >= 120 and bh >= 120:
            return base.crop((int(bw * 0.14), int(bh * 0.14), int(bw * 0.86), int(bh * 0.86)))
    return base


def _resolve_flexible_clause_plan(
    seq_p: float,
    subtitle_text: str,
    voice_spec: dict[str, Any] | None,
) -> tuple[list[str], list[tuple[float, float]], list[float], int, str, list[str], list[str]]:
    """Extracts 1..N natural clauses, time windows, per-clause progress `c_prog`, active clause, and per-clause focus tags."""
    if not voice_spec and subtitle_text:
        from documentary.vox_engine.semantic_router import build_voice_spec_for_beat
        voice_spec = build_voice_spec_for_beat({"narration_text": subtitle_text})

    raw_clauses, windows, raw_metrics, header_ko, sub_ko = _extract_voice_clauses_and_windows(
        voice_spec,
        [subtitle_text] if subtitle_text else [
            "핵심 자금 흐름 및 포렌식 원장 교차 검증",
            "위장된 수익 구조 이면의 실제 자금 은닉 경로 추적",
            "사법 당국 최종 압수·환수 및 법적 단죄 확정",
        ],
    )
    clauses: list[str] = []
    extracted_win: list[tuple[float, float]] = []
    for idx_c, c in enumerate(raw_clauses or []):
        if isinstance(c, dict):
            txt = str(c.get("text") or "").strip()
            if txt:
                clauses.append(txt)
                s_r = float(c.get("start_ratio", idx_c / max(1, len(raw_clauses))))
                e_r = float(c.get("end_ratio", (idx_c + 1) / max(1, len(raw_clauses))))
                extracted_win.append((s_r, e_r))
        else:
            txt = str(c).strip()
            if txt:
                clauses.append(txt)

    if not clauses:
        clauses = [str(subtitle_text or header_ko or "포렌식 핵심 단서 검증").strip()]

    n_c = len(clauses)
    if len(extracted_win) == n_c:
        windows = extracted_win
    elif len(windows) != n_c:
        windows = [(i / n_c, (i + 1) / n_c) for i in range(n_c)]

    c_prog: list[float] = []
    active_idx = 0
    for i, (w0, w1) in enumerate(windows):
        span = max(0.08, float(w1) - float(w0))
        # Progressive reveal starts slightly ahead of window so visual lands right on voice syllable
        lp = ease_out_cubic(max(0.0, min(1.0, (seq_p - max(0.0, float(w0) - 0.05)) / span)))
        c_prog.append(lp)
        if seq_p >= float(w0) - 0.02:
            active_idx = i

    active_clause = clauses[min(active_idx, n_c - 1)]

    metrics = [
        str(m.get("value") or m.get("text") if isinstance(m, dict) else m).strip()
        for m in (raw_metrics or [])
        if m
    ]
    raw_focus_tags = list((voice_spec or {}).get("clause_focus_tags") or [])
    c_tags: list[str] = []
    for i in range(max(6, n_c)):
        if i < len(raw_focus_tags) and str(raw_focus_tags[i]).strip():
            c_tags.append(str(raw_focus_tags[i]).strip())
        elif i < n_c:
            m_hit = _CLAUSE_METRIC_RE.findall(clauses[i])
            if m_hit:
                c_tags.append(m_hit[0].strip())
            elif i < len(metrics):
                c_tags.append(metrics[i])
            else:
                words = [w.strip(".,?!\"'()[]") for w in clauses[i].split() if len(w.strip(".,?!\"'()[]")) >= 2]
                c_tags.append(" ".join(words[:2])[:16] if words else f"핵심 요지 0{i + 1}")
        elif i < len(metrics):
            c_tags.append(metrics[i])
        else:
            c_tags.append(c_tags[-1] if c_tags else "핵심 단서")

    while len(metrics) < 5:
        metrics.append(c_tags[len(metrics) % len(c_tags)])

    return clauses, windows, c_prog, active_idx, active_clause, c_tags, metrics


# ==============================================================================
# 24 BESPOKE FULL-BLEED VOX & GIS MAP ARCHETYPE RENDERERS (#FIN01 .. #FIN24)
# ==============================================================================

def _make_archetype_renderer(arch_idx: int):
    def _render(
        seq_p: float,
        frame_a: Image.Image | None = None,
        frame_b: Image.Image | None = None,
        subtitle_text: str = "",
        voice_spec: dict[str, Any] | None = None,
    ) -> Image.Image:
        clauses, windows, c_prog, active_idx, active_clause, c_tags, metrics = _resolve_flexible_clause_plan(
            seq_p, subtitle_text, voice_spec
        )
        n_c = len(clauses)
        frame_c = _derive_third_photo(frame_a, frame_b, voice_spec)
        photos = [frame_a, frame_b or frame_a, frame_c or frame_b or frame_a]

        p = ease_out_cubic(max(0.12, min(1.0, seq_p * 1.2)))
        c0 = clauses[0]
        c1 = clauses[1] if n_c > 1 else c0
        m0, m1, m2 = c_tags[0], c_tags[1], c_tags[2]
        headline_parts = list(dict.fromkeys(c_tags[:min(3, max(1, n_c))]))
        headline = " · ".join(headline_parts) if len(headline_parts) > 1 else f"{m0} — {_clean_phrase(c0, 18)}"
        cap_ab = f"{m0} · {m1}" if n_c > 1 else m0
        cap_bc = f"{m1} · {m2}" if n_c > 2 else cap_ab

        suppress_sub = bool((voice_spec or {}).get("suppress_burned_subtitle"))

        def _maybe_draw_subtitle(cv: Image.Image, clause_str: str, on_light_paper: bool = False) -> None:
            if not suppress_sub:
                draw_cinema_subtitle(cv, clause_str, on_light_paper=on_light_paper)

        # ----------------------------------------------------------------------
        # #FIN01: Full-Bleed FT Salmon Paper — Promised Yield vs Cliff Collapse
        # (Flexible 1..N clause callout pins along curve + 1..2 progressive photos)
        # ----------------------------------------------------------------------
        if arch_idx == 1:
            canvas = _make_tactile_bg((246, 229, 211), grain_sigma=4.2, grid_type="lines", seed=101)
            draw = ImageDraw.Draw(canvas, "RGBA")
            _draw_editorial_title_banner(draw, 84, 54, "FINANCIAL TIMES ARCHIVE · 수익률 추락 분석", headline, on_dark=False)

            # Left column: 1 photo if 1 clause, or 2 progressive photos if 2+ clauses
            if n_c >= 2 and c_prog[1] > 0.08:
                _paste_torn_photo(canvas, frame_a, 88, 168, 430, 235, caption=f"{m0} · {_clean_phrase(c0, 16)}", badge=m0[:12], seed=11)
                _paste_torn_photo(canvas, frame_b or frame_a, 88, 488, 430, 235, caption=f"{m1} · {_clean_phrase(c1, 16)}", badge=m1[:12], paperclip=True, seed=12)
            else:
                _paste_torn_photo(canvas, frame_a, 92, 185, 440, 310, caption=f"{m0} · {_clean_phrase(c0, 18)}", badge=m0[:12], seed=11)
                draw = ImageDraw.Draw(canvas, "RGBA")
                _draw_felt_highlighter(draw, 92, 575, 440, 72, p=c_prog[0])
                draw_text_safe(draw, (110, 592), f"핵심 수치: {m0}", fill=(20, 18, 16, 255), font_size=34, bold=True)
            draw = ImageDraw.Draw(canvas, "RGBA")

            # Baseline axes on salmon paper
            gx0, gy0, gx1, gy1 = 600, 185, 1790, 810
            draw.line([(gx0, gy1), (gx1, gy1)], fill=(40, 34, 28, 220), width=4)
            draw.line([(gx0, gy0), (gx0, gy1)], fill=(40, 34, 28, 140), width=2)

            pts_prom, pts_real = [], []
            steps = int(65 * p)
            for i in range(max(2, steps)):
                t = i / 64.0
                x = int(gx0 + t * (gx1 - gx0))
                yp = int(gy1 - 80 - 480 * (t ** 1.15))
                yr = int(gy1 - 80 - 340 * t) if t < 0.62 else int(gy1 - 16)
                pts_prom.append((x, yp))
                pts_real.append((x, yr))

            draw.polygon(pts_prom + [(pts_prom[-1][0], gy1), (gx0, gy1)], fill=(14, 116, 144, 32))
            draw.line(pts_prom, fill=(14, 116, 144, 235), width=6)
            draw.line(pts_real, fill=(190, 24, 24, 255), width=9)

            # Progressive 1..N clause callout markers along the curve
            for idx_c, cl_txt in enumerate(clauses):
                cp = c_prog[idx_c]
                if cp <= 0.04:
                    continue
                t_pos = (idx_c + 0.5) / max(1, n_c)
                pt_idx = min(len(pts_real) - 1, max(0, int(t_pos * (len(pts_real) - 1))))
                px, py = pts_real[pt_idx] if idx_c == n_c - 1 else pts_prom[pt_idx]
                col_c = (190, 24, 24) if idx_c == n_c - 1 else (14, 116, 144)
                _draw_hand_circle(draw, px, py, 44, 38, color=col_c, width=4, p=cp)
                ly = 195 + idx_c * min(135, 520 // max(1, n_c))
                _draw_felt_highlighter(
                    draw, 635, ly, 680, 62, p=cp,
                    color=(250, 204, 21) if idx_c == active_idx else (242, 220, 198),
                    alpha=195 if idx_c == active_idx else 145,
                )
                draw.rectangle([635, ly, 645, ly + 62], fill=col_c + (255,))
                draw_text_safe(
                    draw, (658, ly + 14),
                    f"[{c_tags[idx_c]}] {_clean_phrase(cl_txt, 24)}",
                    fill=(20, 18, 16, 255), font_size=25, bold=True,
                )

            _maybe_draw_subtitle(canvas, active_clause, on_light_paper=True)
            return canvas

        # ----------------------------------------------------------------------
        # #FIN02: Warm Dot-Grid Paper — Flexible 1..N Tactile Sankey Ribbon Flow
        # ----------------------------------------------------------------------
        if arch_idx == 2:
            canvas = _make_tactile_bg((243, 238, 228), grain_sigma=4.0, grid_type="dots", seed=102)
            draw = ImageDraw.Draw(canvas, "RGBA")
            _draw_editorial_title_banner(draw, 84, 54, "MONEY TRAIL SANKEY · 다단계 자금 세탁 경로", headline, on_dark=False)

            _paste_torn_photo(canvas, frame_a, 84, 225, 395, 305, caption=f"출발 원점 · {m0}", badge="ORIGIN", seed=21)
            if n_c >= 2 and c_prog[min(1, n_c - 1)] > 0.05:
                _paste_torn_photo(canvas, frame_b, 1425, 225, 395, 305, caption=f"최종 귀착 · {c_tags[n_c - 1]}", badge="TERMINAL", seed=22)
            draw = ImageDraw.Draw(canvas, "RGBA")

            # Dynamically scale middle Sankey conduits to match n_c (1..5 clauses)
            palette_cols = [(190, 24, 24), (217, 119, 6), (14, 116, 144), (124, 58, 237), (30, 41, 59)]
            n_nodes = max(1, min(5, n_c))
            y_start = 380 if n_nodes == 1 else (215 if n_nodes <= 3 else 175)
            y_step = 0 if n_nodes == 1 else (540 // max(1, n_nodes - 1) if n_nodes <= 3 else 580 // max(1, n_nodes - 1))

            for i in range(n_nodes):
                cp = c_prog[i] if i < len(c_prog) else p
                if cp <= 0.02:
                    continue
                ny = y_start + i * y_step
                nx = 955
                col = palette_cols[i % len(palette_cols)]
                lbl = f"{c_tags[i]} · {_clean_phrase(clauses[i], 15)}"
                rib_w = max(12, 26 - n_nodes * 2)

                for step_i in range(36):
                    t0, t1 = step_i / 36.0, (step_i + 1) / 36.0
                    if t0 > cp:
                        break
                    x_a = int(510 + (nx - 185 - 510) * t0)
                    y_a = int(380 + (ny - 380) * ease_in_out_cubic(t0))
                    x_b = int(510 + (nx - 185 - 510) * t1)
                    y_b = int(380 + (ny - 380) * ease_in_out_cubic(t1))
                    draw.line([(x_a, y_a), (x_b, y_b)], fill=col + (195,), width=rib_w)

                    if n_c >= 2:
                        rx_a = int(nx + 185 + (1405 - (nx + 185)) * t0)
                        ry_a = int(ny + (380 - ny) * ease_in_out_cubic(t0))
                        rx_b = int(nx + 185 + (1405 - (nx + 185)) * t1)
                        ry_b = int(ny + (380 - ny) * ease_in_out_cubic(t1))
                        draw.line([(rx_a, ry_a), (rx_b, ry_b)], fill=col + (195,), width=rib_w)

                tag_h = 92 if n_nodes <= 3 else 78
                tag = get_torn_paper_sheet(380, tag_h, fill_rgb=(252, 250, 245), roughness=2.2, seed=200 + i * 17)
                tdraw = ImageDraw.Draw(tag, "RGBA")
                if i == active_idx:
                    _draw_felt_highlighter(tdraw, 34, 30, 340, tag_h - 10, p=cp, alpha=165)
                tdraw.rectangle([28, 28, 38, 28 + tag_h - 4], fill=col + (255,))
                draw_text_safe(tdraw, (50, 28 + tag_h // 2 - 16), lbl[:22], fill=(20, 20, 18, 255), font_size=22, bold=True)
                canvas.paste(tag, (nx - 218, ny - tag_h // 2 - 24), tag)
                draw = ImageDraw.Draw(canvas, "RGBA")

            _maybe_draw_subtitle(canvas, active_clause, on_light_paper=True)
            return canvas

        # ----------------------------------------------------------------------
        # #FIN03: Editorial Cream Paper — Giant % + 10x10 Grid & 1..N Clause Breakdown
        # ----------------------------------------------------------------------
        if arch_idx == 3:
            canvas = _make_tactile_bg((248, 245, 237), grain_sigma=3.8, grid_type="dots", seed=103)
            draw = ImageDraw.Draw(canvas, "RGBA")
            _draw_editorial_title_banner(draw, 84, 52, "PROPORTIONAL AUDIT · 전수 실사 비율 검증", headline, on_dark=False)

            _draw_felt_highlighter(draw, 84, 165, 580, 108, p=c_prog[0])
            draw_text_safe(draw, (102, 176), m0[:12], fill=(185, 28, 28, 255), font_size=76, bold=True)

            # Progressive 1..N clause breakdown strips on left + photo(s)
            for idx_c, cl_txt in enumerate(clauses):
                cp = c_prog[idx_c]
                if cp <= 0.03:
                    continue
                sy = 295 + idx_c * min(72, 210 // max(1, n_c))
                _draw_felt_highlighter(
                    draw, 88, sy, 580, 56, p=cp,
                    color=(250, 204, 21) if idx_c == active_idx else (236, 230, 216),
                    alpha=180,
                )
                draw.rectangle([88, sy, 98, sy + 56], fill=(190, 24, 24, 255) if idx_c == 0 else (14, 116, 144, 255))
                draw_text_safe(draw, (112, sy + 12), f"[{c_tags[idx_c]}] {_clean_phrase(cl_txt, 22)}", fill=(22, 20, 18, 255), font_size=23, bold=True)

            photo_y = 295 + n_c * min(72, 210 // max(1, n_c)) + 16
            photo_h = max(210, 775 - photo_y)
            if n_c >= 3 and c_prog[min(2, n_c - 1)] > 0.1:
                _paste_torn_photo(canvas, frame_a, 88, photo_y, 275, photo_h, caption=m0, badge="AUDIT A", seed=31)
                _paste_torn_photo(canvas, frame_b, 395, photo_y, 275, photo_h, caption=m1, badge="AUDIT B", seed=32)
            else:
                _paste_torn_photo(canvas, frame_a, 88, photo_y, 575, photo_h, caption=cap_bc, badge=m0[:12], seed=31)
            draw = ImageDraw.Draw(canvas, "RGBA")

            # Right: 10x10 = 100 tactile stamp blocks partitioned by clause stage
            gx0, gy0 = 780, 165
            active_cells = int(100 * p)
            cell_cols = [(190, 24, 24, 235), (217, 119, 6, 235), (14, 116, 144, 235), (30, 41, 59, 235)]
            for idx in range(100):
                r, c = idx // 10, idx % 10
                bx = gx0 + c * 98
                by = gy0 + r * 66
                if idx < active_cells:
                    group_i = 0 if idx < 82 else min(n_c - 1, 1 + (idx - 82) // max(1, 18 // max(1, n_c)))
                    fill_c = cell_cols[group_i % len(cell_cols)]
                else:
                    fill_c = (210, 204, 192, 160)
                draw.rounded_rectangle([bx + 3, by + 4, bx + 78, by + 52], radius=6, fill=(20, 18, 15, 45))
                draw.rounded_rectangle([bx, by, bx + 76, by + 48], radius=6, fill=fill_c)

            _maybe_draw_subtitle(canvas, active_clause, on_light_paper=True)
            return canvas

        # ----------------------------------------------------------------------
        # #FIN04: Full-Screen Continental Satellite GIS + Multi-Hop Escape/Flow Arcs
        # ----------------------------------------------------------------------
        if arch_idx == 4:
            canvas = _load_sat_fullbleed("plate_china_bj_yn_sat_z5.png", brightness=0.82, contrast=1.12)
            draw = ImageDraw.Draw(canvas, "RGBA")
            _draw_editorial_title_banner(draw, 72, 48, "CROSS-BORDER SATELLITE TRACKING · 초국가 도피·자금 루트", headline, on_dark=True, on_sat=True)

            # Accurate inland East/Southeast Asia hub coordinates (Beijing/Anhui -> Central Hub -> Yunnan Border -> Myanmar Wa State)
            all_hubs = [(1220, 420), (1175, 545), (945, 680), (815, 755), (735, 815)]
            n_hubs = max(2, min(5, n_c + 1 if n_c == 1 else n_c))
            hubs = [all_hubs[int(round(i * (len(all_hubs) - 1) / max(1, n_hubs - 1)))] for i in range(n_hubs)]

            for seg_i in range(len(hubs) - 1):
                cp = c_prog[min(seg_i, len(c_prog) - 1)]
                if cp <= 0.02:
                    continue
                p0, p1 = hubs[seg_i], hubs[seg_i + 1]
                arc_pts = []
                for step_k in range(45):
                    t = step_k / 44.0
                    if t > cp:
                        break
                    ax = int(p0[0] + (p1[0] - p0[0]) * t)
                    ay = int(p0[1] + (p1[1] - p0[1]) * t - 180 * math.sin(math.pi * t))
                    arc_pts.append((ax, ay))
                if len(arc_pts) >= 2:
                    sh_pts = [(x, y + int(75 * math.sin(math.pi * (k / 45.0)))) for k, (x, y) in enumerate(arc_pts)]
                    draw.line(sh_pts, fill=(0, 0, 0, 130), width=8)
                    draw.line(arc_pts, fill=(250, 204, 21, 255), width=7)
                    hx, hy = arc_pts[-1]
                    _draw_hand_circle(draw, hx, hy, 38, 38, color=(239, 68, 68), width=5, p=cp)

            for h_i, (hx, hy) in enumerate(hubs):
                cp = c_prog[min(h_i, len(c_prog) - 1)]
                if cp <= 0.02:
                    continue
                draw.ellipse([hx - 12, hy - 12, hx + 12, hy + 12], fill=(239, 68, 68, 255), outline=(255, 255, 255, 255), width=3)
                lbl_tag = c_tags[min(h_i, len(c_tags) - 1)]
                draw.rounded_rectangle([hx - 110, hy + 18, hx + 130, hy + 62], radius=6, fill=(14, 18, 24, 230), outline=(250, 204, 21, 220), width=2)
                draw_text_safe(draw, (hx - 96, hy + 26), f"0{h_i + 1} · {lbl_tag[:12]}", fill=(250, 204, 21, 255), font_size=20, bold=True)

            _maybe_draw_subtitle(canvas, active_clause, on_light_paper=False)
            return canvas

        # ----------------------------------------------------------------------
        # #FIN05: Full-Screen High-Res Satellite + Optical Loupe & 1..N Recon Strips
        # ----------------------------------------------------------------------
        if arch_idx == 5:
            canvas = _load_sat_fullbleed("plate_baiyin_campus_sat_z16.png", brightness=0.86, contrast=1.10)
            draw = ImageDraw.Draw(canvas, "RGBA")
            _draw_editorial_title_banner(draw, 72, 48, "OPTICAL SATELLITE RECON · 고해상도 위성 정밀 판독", headline, on_dark=True, on_sat=True)

            tx, ty = 770, 535
            for r_ring in (28, 64, 108):
                draw.ellipse([tx - r_ring, ty - r_ring, tx + r_ring, ty + r_ring], outline=(239, 68, 68, 210), width=3)
            draw.ellipse([tx - 8, ty - 8, tx + 8, ty + 8], fill=(250, 204, 21, 255))

            lx, ly, lr = 350, 520, 225
            loupe_crop = canvas.crop((tx - 110, ty - 110, tx + 110, ty + 110)).resize((lr * 2, lr * 2), Image.Resampling.BICUBIC)
            mask = Image.new("L", (lr * 2, lr * 2), 0)
            ImageDraw.Draw(mask, "L").ellipse([0, 0, lr * 2 - 1, lr * 2 - 1], fill=255)
            canvas.paste(loupe_crop, (lx - lr, ly - lr), mask)
            draw = ImageDraw.Draw(canvas, "RGBA")
            draw.ellipse([lx - lr, ly - lr, lx + lr, ly + lr], outline=(250, 204, 21, 255), width=8)
            draw.line([(lx + lr - 18, ly - 40), (tx, ty)], fill=(250, 204, 21, 220), width=3)
            draw.line([(lx - lr + 24, ly), (lx + lr - 24, ly)], fill=(56, 189, 248, 160), width=2)
            draw.line([(lx, ly - lr + 24), (lx, ly + lr - 24)], fill=(56, 189, 248, 160), width=2)

            strip_y0 = 420
            for idx_c, cl_txt in enumerate(clauses):
                cp = c_prog[idx_c]
                if cp <= 0.03:
                    continue
                sy = strip_y0 + idx_c * min(82, 360 // max(1, n_c))
                draw.rounded_rectangle([1140, sy, 1835, sy + 64], radius=8, fill=(14, 18, 24, 230), outline=(250, 204, 21, 220) if idx_c == active_idx else (100, 116, 139, 160), width=2)
                _draw_felt_highlighter(draw, 1148, sy + 8, int(680 * cp), 48, p=cp, color=(220, 38, 38) if idx_c == active_idx else (30, 41, 59), alpha=185)
                draw_text_safe(draw, (1164, sy + 16), f"[0{idx_c + 1} · {c_tags[idx_c]}] {_clean_phrase(cl_txt, 22)}", fill=(255, 255, 255, 255), font_size=23, bold=True)

            _maybe_draw_subtitle(canvas, active_clause, on_light_paper=False)
            return canvas

        # ----------------------------------------------------------------------
        # #FIN06: Detective Corkboard — Polaroid Core & Dynamic 1..N Red-String Web
        # ----------------------------------------------------------------------
        if arch_idx == 6:
            canvas = get_cork_pinboard_shell()
            draw = ImageDraw.Draw(canvas, "RGBA")
            _draw_editorial_title_banner(draw, 84, 54, "SYNDICATE PINBOARD · 유령 법인·차명 지배구조", headline, on_dark=True)

            cx, cy = 960, 520
            all_slots = [
                (270, 265),
                (1630, 265),
                (250, 665),
                (1640, 665),
                (610, 815),
                (1310, 815),
            ]
            n_cards = max(2, min(6, n_c if n_c >= 2 else 3))
            for idx_s in range(n_cards):
                cp = c_prog[idx_s] if idx_s < len(c_prog) else p
                if cp <= 0.03:
                    continue
                sx, sy = all_slots[idx_s]
                ex = int(cx + (sx - cx) * cp)
                ey = int(cy + (sy - cy) * cp)
                draw.line([(cx, cy + 4), (ex, ey + 4)], fill=(0, 0, 0, 120), width=5)
                draw.line([(cx, cy), (ex, ey)], fill=(210, 32, 32, 245), width=4)

                cl_str = clauses[idx_s] if idx_s < n_c else clauses[idx_s % n_c]
                tag_str = c_tags[idx_s]
                card = get_torn_paper_sheet(340, 118, fill_rgb=(235, 220, 188), roughness=2.5, seed=60 + idx_s)
                cdraw = ImageDraw.Draw(card, "RGBA")
                if idx_s == active_idx:
                    _draw_felt_highlighter(cdraw, 34, 34, 300, 82, p=cp, alpha=165)
                draw_text_safe(cdraw, (44, 38), f"[{tag_str[:12]}]", fill=(185, 28, 28, 255), font_size=19, bold=True)
                draw_text_safe(cdraw, (44, 68), _clean_phrase(cl_str, 18), fill=(24, 20, 16, 255), font_size=22, bold=True)
                canvas.paste(card, (sx - 195, sy - 78), card)
                draw = ImageDraw.Draw(canvas, "RGBA")
                _draw_pushpin(draw, sx, sy - 38, color=(210, 32, 32))

            if n_c >= 3 and c_prog[1] > 0.1:
                paste_photo_polaroid(canvas, fit_crop(frame_a or get_fallback_image(320, 230, m0), 320, 230), (cx - 175, cy - 10), caption=f"핵심 지휘 · {m0}", angle_deg=-2.5, accent_badge="HUB A")
                paste_photo_polaroid(canvas, fit_crop(frame_b or frame_a or get_fallback_image(320, 230, m1), 320, 230), (cx + 175, cy + 10), caption=f"공범 거점 · {m1}", angle_deg=2.2, accent_badge="HUB B")
            else:
                paste_photo_polaroid(canvas, fit_crop(frame_a or get_fallback_image(360, 260, m0), 360, 260), (cx, cy - 10), caption=f"핵심 지휘부 · {m0}", angle_deg=-2.0, accent_badge="CORE HUB")
            draw = ImageDraw.Draw(canvas, "RGBA")
            _draw_pushpin(draw, cx, cy - 155, color=(250, 204, 21))
            _maybe_draw_subtitle(canvas, active_clause, on_light_paper=False)
            return canvas

        # ----------------------------------------------------------------------
        # #FIN07: Dark Walnut Desk — Bank Statement with Dynamic 1..N Clause Rows
        # ----------------------------------------------------------------------
        if arch_idx == 7:
            canvas = get_dark_investigation_desk()
            draw = ImageDraw.Draw(canvas, "RGBA")
            _draw_editorial_title_banner(draw, 84, 52, "FORENSIC BANK LEDGER · 계좌 원장 전수 발췌", headline, on_dark=True)

            if n_c >= 3 and c_prog[1] > 0.1:
                _paste_torn_photo(canvas, frame_a, 84, 175, 460, 275, caption=f"원장 증거 A · {m0}", badge="AUDIT #1", paperclip=True, seed=71)
                _paste_torn_photo(canvas, frame_b, 84, 525, 460, 275, caption=f"원장 증거 B · {m1}", badge="AUDIT #2", seed=73)
            else:
                _paste_torn_photo(canvas, frame_a, 88, 195, 470, 560, caption=f"계좌 추적 증거 · {m0}", badge="AUDIT", paperclip=True, seed=71)

            ledger = get_torn_paper_sheet(1180, 690, fill_rgb=(250, 247, 238), roughness=2.4, seed=72)
            ldraw = ImageDraw.Draw(ledger, "RGBA")
            ldraw.rectangle([48, 44, 1180 - 20, 108], fill=(24, 28, 36, 255))
            draw_text_safe(ldraw, (72, 60), f"BANK STATEMENT AUDIT · 원장 대조 기록 ({n_c}개 핵심 항목)", fill=(250, 204, 21, 255), font_size=24, bold=True)

            n_rows = max(1, min(5, n_c))
            row_step = min(130, 520 // max(1, n_rows))
            for r_i in range(n_rows):
                cp = c_prog[r_i]
                if cp <= 0.02:
                    continue
                ry = 135 + r_i * row_step
                r_val = c_tags[r_i]
                r_txt = _clean_phrase(clauses[r_i], 30)
                if r_i == active_idx:
                    ldraw.rounded_rectangle([38, ry - 6, 1146, ry + row_step - 12], radius=10, fill=(255, 255, 255, 255), outline=(190, 24, 24, 255), width=4)
                    _draw_felt_highlighter(ldraw, 56, ry + 8, 1060, row_step - 36, p=cp)
                    draw_text_safe(ldraw, (72, ry + 20), f"#0{r_i + 1}  [{r_val[:12]}]  {r_txt}", fill=(18, 18, 16, 255), font_size=27, bold=True)
                else:
                    ldraw.line([(56, ry + row_step - 16), (1140, ry + row_step - 16)], fill=(200, 194, 182, 255), width=2)
                    draw_text_safe(ldraw, (68, ry + 20), f"#0{r_i + 1}   {r_val[:14]}   |   {r_txt}", fill=(70, 66, 60, 255), font_size=24, bold=True)

            _draw_circular_official_seal(ldraw, 1055, 575, dept_ko="금융포렌식감식국", sub_ko="원장대조필", r=54)
            canvas.paste(ledger, (620, 150), ledger)
            _maybe_draw_subtitle(canvas, active_clause, on_light_paper=False)
            return canvas

        # ----------------------------------------------------------------------
        # #FIN08: Manila Dossier — Dynamic N-Tier Papercraft Ponzi Pyramid
        # ----------------------------------------------------------------------
        if arch_idx == 8:
            canvas = _make_tactile_bg((232, 218, 192), grain_sigma=4.5, grid_type="dots", seed=108)
            draw = ImageDraw.Draw(canvas, "RGBA")
            _draw_editorial_title_banner(draw, 84, 54, "PONZI STRUCTURE ANATOMY · 다단계 피라미드 붕괴", headline, on_dark=False)

            n_tiers = max(2, min(5, n_c if n_c >= 2 else 3))
            tier_cols = [(190, 24, 24), (217, 119, 6), (14, 116, 144), (30, 41, 59), (71, 85, 105)]
            t_h = min(165, (580 - (n_tiers - 1) * 18) // n_tiers)
            for t_i in range(n_tiers):
                cp = c_prog[t_i] if t_i < len(c_prog) else p
                if cp <= 0.02:
                    continue
                ty = 195 + t_i * (t_h + 18)
                tw = int((360 + t_i * (580 // max(1, n_tiers - 1))) * cp)
                x0 = 560 - tw // 2
                col = tier_cols[t_i % len(tier_cols)]
                draw.rounded_rectangle([x0 + 8, ty + 10, x0 + tw + 8, ty + t_h + 10], radius=10, fill=(20, 16, 12, 70))
                draw.rounded_rectangle([x0, ty, x0 + tw, ty + t_h], radius=10, fill=col + (245,), outline=(255, 255, 255, 235) if t_i == active_idx else (255, 255, 255, 180), width=4 if t_i == active_idx else 2)

            # Lightning fracture across pyramid
            draw.line([(705, 180), (670, 365), (740, 540), (690, 785)], fill=(250, 204, 21, 255), width=8)
            draw.line([(705, 180), (670, 365), (740, 540), (690, 785)], fill=(220, 38, 38, 255), width=4)

            for t_i in range(n_tiers):
                cp = c_prog[t_i] if t_i < len(c_prog) else p
                if cp <= 0.02:
                    continue
                ty = 195 + t_i * (t_h + 18)
                tw = int((360 + t_i * (580 // max(1, n_tiers - 1))) * cp)
                x0 = 560 - tw // 2
                cl_str = clauses[t_i] if t_i < n_c else clauses[t_i % n_c]
                lbl = f"0{t_i + 1} · {c_tags[t_i]} — {_clean_phrase(cl_str, 16)}"
                draw_text_safe(draw, (x0 + 28, ty + t_h // 2 - 16), lbl[:26], fill=(255, 255, 255, 255), font_size=25, bold=True)

            if n_c >= 2 and c_prog[1] > 0.1:
                _paste_torn_photo(canvas, frame_a, 1180, 185, 580, 255, caption=f"상위 설계 · {m0}", badge="TIER 01", seed=81)
                _paste_torn_photo(canvas, frame_b, 1180, 520, 580, 255, caption=f"하위 피해 · {m1}", badge="COLLAPSE", seed=82)
            else:
                _paste_torn_photo(canvas, frame_a, 1180, 215, 590, 460, caption=cap_ab, badge="COLLAPSE", seed=81)
            draw = ImageDraw.Draw(canvas, "RGBA")
            _draw_hand_arrow(draw, 1150, 330, 760, 275, color=(190, 24, 24), width=6)
            _maybe_draw_subtitle(canvas, active_clause, on_light_paper=True)
            return canvas

        # ----------------------------------------------------------------------
        # #FIN09: Full-Screen Geological Cross-Section — Dynamic N-Strata Excavation
        # ----------------------------------------------------------------------
        if arch_idx == 9:
            canvas = Image.new("RGB", (W, H), (28, 36, 48))
            draw = ImageDraw.Draw(canvas, "RGBA")

            n_strata = max(2, min(5, n_c if n_c >= 2 else 4))
            strata_cols = [(36, 48, 64), (78, 56, 42), (112, 46, 24), (76, 22, 18), (48, 10, 10)]
            sh_step = H // n_strata
            for s_i in range(n_strata):
                y0 = s_i * sh_step
                y1 = H if s_i == n_strata - 1 else (s_i + 1) * sh_step
                col = strata_cols[s_i % len(strata_cols)]
                draw.rectangle([0, y0, W, y1], fill=col + (255,))
                draw.line([(0, y1), (W, y1)], fill=(250, 204, 21, 150), width=3)
                cp = c_prog[s_i] if s_i < len(c_prog) else p
                if cp > 0.03:
                    depth_m = round(s_i * (6.0 / max(1, n_strata - 1)), 1)
                    cl_str = clauses[s_i] if s_i < n_c else clauses[s_i % n_c]
                    draw_text_safe(
                        draw, (110, y0 + 28),
                        f"-{depth_m}m [{c_tags[s_i]}] {_clean_phrase(cl_str, 26)}",
                        fill=(250, 204, 21, 255) if s_i == active_idx else (248, 250, 252, 235),
                        font_size=27, bold=True,
                    )

            draw.line([(72, 60), (72, H - 60)], fill=(250, 204, 21, 230), width=4)
            for ry in range(100, H - 80, 60):
                draw.line([(58, ry), (86, ry)], fill=(250, 204, 21, 200), width=2)

            shaft_h = int(780 * p)
            draw.rectangle([830, 160, 1080, 160 + shaft_h], fill=(15, 23, 42, 195), outline=(250, 204, 21, 235), width=4)
            vault_y = min(H - 130, 160 + shaft_h)
            _draw_hand_circle(draw, 955, vault_y, 175, 65, color=(250, 204, 21), width=6, p=p)
            draw_text_safe(draw, (860, vault_y - 20), c_tags[min(active_idx, len(c_tags) - 1)][:14], fill=(250, 204, 21, 255), font_size=38, bold=True)

            if n_c >= 2 and c_prog[1] > 0.1:
                _paste_torn_photo(canvas, frame_a, 1230, 140, 560, 270, caption=f"지표 굴착 · {m0}", badge="SURFACE", seed=91)
                _paste_torn_photo(canvas, frame_b, 1230, 495, 560, 270, caption=f"심층 은닉 · {m1}", badge="DEPTH -6.0M", seed=92)
            else:
                _paste_torn_photo(canvas, frame_a, 1240, 220, 560, 440, caption=cap_bc, badge="DEPTH -6.0M", seed=91)
            _maybe_draw_subtitle(canvas, active_clause, on_light_paper=False)
            return canvas

        # ----------------------------------------------------------------------
        # #FIN10: 50/50 Split-Screen Contrast + Progressive Multi-Clause Badges
        # ----------------------------------------------------------------------
        if arch_idx == 10:
            canvas = Image.new("RGB", (W, H), (244, 240, 230))
            draw = ImageDraw.Draw(canvas, "RGBA")
            draw.rectangle([W // 2, 0, W, H], fill=(28, 12, 16, 255))
            draw.line([(W // 2, 0), (W // 2, H)], fill=(250, 204, 21, 255), width=6)

            # Stage 1 (Left): Normal Benchmark + Photo A
            p_left = c_prog[0]
            draw_text_safe(draw, (96, 68), "STAGE 01 · 기준 대조 및 초기 상태", fill=(14, 116, 144, 255), font_size=22, bold=True)
            draw_text_safe(draw, (96, 110), m0[:14], fill=(24, 24, 22, 255), font_size=64, bold=True)
            cx_l, cy_l, r_g = 460, 460, 210
            draw.arc([cx_l - r_g, cy_l - r_g, cx_l + r_g, cy_l + r_g], start=180, end=360, fill=(200, 195, 185, 255), width=38)
            draw.arc([cx_l - r_g, cy_l - r_g, cx_l + r_g, cy_l + r_g], start=180, end=int(180 + 50 * p_left), fill=(14, 116, 144, 255), width=38)
            _paste_torn_photo(canvas, frame_a, 140, 540, 560, 240, caption=_clean_phrase(c0, 22), badge=m0[:12], seed=100)
            draw = ImageDraw.Draw(canvas, "RGBA")

            # Stage 2 (Right): Fraudulent Bait + Photo B
            p_right = c_prog[min(1, n_c - 1)]
            if p_right > 0.02:
                draw_text_safe(draw, (W // 2 + 96, 68), "STAGE 02 · 비정상 폭증 및 왜곡 실체", fill=(250, 204, 21, 255), font_size=22, bold=True)
                draw_text_safe(draw, (W // 2 + 96, 110), m1[:14], fill=(244, 63, 94, 255), font_size=68, bold=True)
                cx_r, cy_r = 1440, 460
                draw.arc([cx_r - r_g, cy_r - r_g, cx_r + r_g, cy_r + r_g], start=180, end=360, fill=(68, 28, 34, 255), width=38)
                draw.arc([cx_r - r_g, cy_r - r_g, cx_r + r_g, cy_r + r_g], start=180, end=int(180 + 172 * p_right), fill=(244, 63, 94, 255), width=38)
                _paste_torn_photo(canvas, frame_b or frame_a, W // 2 + 160, 540, 560, 240, caption=_clean_phrase(c1, 22), badge=m1[:12], seed=101)
                draw = ImageDraw.Draw(canvas, "RGBA")

            # Stage 3..N: Additional clause callout cards pinned across center spine
            for extra_i in range(2, n_c):
                cp = c_prog[extra_i]
                if cp <= 0.04:
                    continue
                ey = 210 + (extra_i - 2) * 125
                draw.rounded_rectangle([W // 2 - 280, ey, W // 2 + 280, ey + 96], radius=10, fill=(252, 249, 242, 250), outline=(190, 24, 24, 255), width=4)
                _draw_felt_highlighter(draw, W // 2 - 264, ey + 14, 528, 68, p=cp)
                draw_text_safe(draw, (W // 2 - 248, ey + 28), f"[{c_tags[extra_i]}] {_clean_phrase(clauses[extra_i], 20)}", fill=(20, 18, 16, 255), font_size=24, bold=True)

            _maybe_draw_subtitle(canvas, active_clause, on_light_paper=False)
            return canvas

        # ----------------------------------------------------------------------
        # #FIN11: Architectural Isometric Grid — Dynamic 1..N 2.5D Extruded Pillars
        # ----------------------------------------------------------------------
        if arch_idx == 11:
            canvas = _make_tactile_bg((236, 240, 245), grain_sigma=3.6, grid_type="lines", seed=111)
            draw = ImageDraw.Draw(canvas, "RGBA")
            _draw_editorial_title_banner(draw, 84, 54, "SCALE COMPARISON · 단계별 자금 규모 폭증 비교", headline, on_dark=False)

            if n_c >= 3 and c_prog[1] > 0.1:
                _paste_torn_photo(canvas, frame_a, 88, 185, 480, 260, caption=f"초기 단계 · {m0}", badge="STAGE 01", seed=111)
                _paste_torn_photo(canvas, frame_b, 88, 520, 480, 260, caption=f"폭증 단계 · {m1}", badge="SCALE UP", seed=112)
            else:
                _paste_torn_photo(canvas, frame_a, 92, 205, 500, 490, caption=cap_ab, badge="SCALE UP", seed=111)
            draw = ImageDraw.Draw(canvas, "RGBA")

            floor_y = 815
            n_pil = max(1, min(5, n_c))
            p_cols = [(100, 116, 139), (14, 116, 144), (217, 119, 6), (190, 24, 24), (136, 19, 55)]
            avail_w = 1120
            slot_w = avail_w // n_pil
            bw = min(240, max(130, slot_w - 65))

            for i in range(n_pil):
                cp = c_prog[i]
                if cp <= 0.02:
                    continue
                bx = 680 + i * slot_w + (slot_w - bw) // 2
                rat = (i + 1) / float(n_pil)
                col = p_cols[min(len(p_cols) - 1, int(round(i * (len(p_cols) - 1) / max(1, n_pil - 1))))]
                bh = max(52, int(470 * rat * cp))
                by = floor_y - bh
                draw.polygon([(bx + bw, floor_y), (bx + bw + 80, floor_y - 46), (bx + 80, floor_y - 46), (bx, floor_y)], fill=(15, 23, 42, 45))
                draw.polygon([(bx, by), (bx + 36, by - 28), (bx + bw + 36, by - 28), (bx + bw, by)], fill=col + (195,))
                draw.polygon([(bx + bw, by), (bx + bw + 36, by - 28), (bx + bw + 36, floor_y - 28), (bx + bw, floor_y)], fill=(20, 24, 32, 185))
                draw.rectangle([bx, by, bx + bw, floor_y], fill=col + (245,))
                if i == active_idx:
                    _draw_felt_highlighter(draw, bx - 6, by - 115, bw + 44, 78, p=cp)
                draw_text_safe(draw, (bx + 6, by - 108), _clean_phrase(clauses[i], 12), fill=(30, 41, 59, 255), font_size=20, bold=True)
                draw_text_safe(draw, (bx + 6, by - 76), str(c_tags[i])[:12], fill=col + (255,), font_size=30, bold=True)

            _maybe_draw_subtitle(canvas, active_clause, on_light_paper=True)
            return canvas

        # ----------------------------------------------------------------------
        # #FIN12: Full-Screen Regional Satellite GIS + 1..N Shockwaves & Regional Pins
        # ----------------------------------------------------------------------
        if arch_idx == 12:
            gansu_plate, _ = get_vox_styled_gansu_base()
            canvas = fit_crop(gansu_plate.convert("RGB"), W, H)
            draw = ImageDraw.Draw(canvas, "RGBA")
            _draw_editorial_title_banner(draw, 72, 48, "REGIONAL SHOCKWAVE GIS · 광역 피해 확산 지도", headline, on_dark=True, on_sat=True)

            ex, ey = 660, 540
            for idx_r in range(max(2, n_c + 1)):
                rr = int((65 + idx_r * 75) * p)
                draw.ellipse([ex - rr, ey - rr, ex + rr, ey + rr], outline=(239, 68, 68, 220), width=4)
            draw.ellipse([ex - 14, ey - 14, ex + 14, ey + 14], fill=(250, 204, 21, 255), outline=(185, 28, 28, 255), width=4)

            pin_coords = [(660, 540), (460, 360), (880, 350), (520, 720), (890, 690)]
            for idx_c in range(n_c):
                cp = c_prog[idx_c]
                if cp <= 0.03:
                    continue
                px, py = pin_coords[idx_c % len(pin_coords)]
                draw.line([(ex, ey), (px, py)], fill=(250, 204, 21, 210), width=3)
                _draw_pushpin(draw, px, py, color=(239, 68, 68) if idx_c == active_idx else (250, 204, 21))

            if n_c >= 2 and c_prog[1] > 0.1:
                _paste_torn_photo(canvas, frame_a, 1170, 165, 315, 250, caption=m0, badge="EPICENTER", seed=121)
                _paste_torn_photo(canvas, frame_b, 1520, 165, 315, 250, caption=m1, badge="SPREAD", seed=122)
                y_list = 495
            else:
                _paste_torn_photo(canvas, frame_a, 1180, 175, 620, 320, caption=cap_ab, badge="EPICENTER", seed=121)
                y_list = 565
            draw = ImageDraw.Draw(canvas, "RGBA")
            draw.line([(ex, ey), (1170, 310)], fill=(250, 204, 21, 235), width=4)

            for idx_c, cl_txt in enumerate(clauses):
                cp = c_prog[idx_c]
                if cp <= 0.03:
                    continue
                sy = y_list + idx_c * min(74, 290 // max(1, n_c))
                _draw_felt_highlighter(draw, 1170, sy, 665, 58, p=cp, color=(250, 204, 21) if idx_c == active_idx else (248, 245, 235), alpha=210)
                draw_text_safe(draw, (1190, sy + 13), f"[{c_tags[idx_c]}] {_clean_phrase(cl_txt, 22)}", fill=(20, 18, 16, 255), font_size=24, bold=True)

            _maybe_draw_subtitle(canvas, active_clause, on_light_paper=False)
            return canvas

        # ----------------------------------------------------------------------
        # #FIN13: Full-Screen Photo X-Ray Split — Dynamic Scanner & 1..N X-Ray Findings
        # ----------------------------------------------------------------------
        if arch_idx == 13:
            src_a = frame_a if isinstance(frame_a, Image.Image) else get_fallback_image(W, H, m0)
            left_img = fit_crop(src_a.convert("RGB"), W, H)
            left_img = ImageEnhance.Brightness(left_img).enhance(0.95)

            src_b = frame_b if isinstance(frame_b, Image.Image) else src_a
            right_img = fit_crop(src_b.convert("RGB"), W, H).convert("L")
            right_rgb = Image.merge("RGB", (
                right_img.point(lambda v: int(v * 0.25)),
                right_img.point(lambda v: int(v * 0.18)),
                right_img.point(lambda v: int(v * 0.28)),
            ))

            split_x = int(W * (0.62 - 0.22 * p))
            canvas = left_img.copy()
            canvas.paste(right_rgb.crop((split_x, 0, W, H)), (split_x, 0))
            draw = ImageDraw.Draw(canvas, "RGBA")

            draw.line([(split_x, 0), (split_x, H)], fill=(56, 189, 248, 255), width=8)
            draw.rectangle([56, 56, 590, 182], fill=(252, 249, 242, 238))
            draw.rectangle([56, 56, 68, 182], fill=(14, 116, 144, 255))
            draw_text_safe(draw, (88, 70), "PUBLIC FACADE · 화려한 홍보 외피", fill=(14, 116, 144, 255), font_size=20, bold=True)
            draw_text_safe(draw, (88, 108), f"{m0} — {_clean_phrase(c0, 14)}", fill=(20, 20, 18, 255), font_size=32, bold=True)

            # Right X-Ray progressive 1..N clause findings
            rx0 = split_x + 48
            rw = max(480, W - rx0 - 56)
            for idx_c, cl_txt in enumerate(clauses):
                cp = c_prog[idx_c]
                if cp <= 0.03:
                    continue
                ry = 185 + idx_c * min(135, 560 // max(1, n_c))
                _draw_felt_highlighter(
                    draw, rx0, ry, rw, 92, p=cp,
                    color=(220, 38, 38) if idx_c == active_idx else (30, 41, 59),
                    alpha=225 if idx_c == active_idx else 185,
                )
                draw_text_safe(draw, (rx0 + 22, ry + 12), f"X-RAY #0{idx_c + 1} · {c_tags[idx_c]}", fill=(250, 204, 21, 255), font_size=22, bold=True)
                draw_text_safe(draw, (rx0 + 22, ry + 44), _clean_phrase(cl_txt, 24), fill=(255, 255, 255, 255), font_size=28, bold=True)

            _maybe_draw_subtitle(canvas, active_clause, on_light_paper=False)
            return canvas

        # ----------------------------------------------------------------------
        # #FIN14: Panoramic Archival Scroll — Dynamic 1..N Stop Timeline & Photos
        # ----------------------------------------------------------------------
        if arch_idx == 14:
            canvas = _make_tactile_bg((242, 236, 224), grain_sigma=4.0, grid_type="lines", seed=114)
            draw = ImageDraw.Draw(canvas, "RGBA")
            _draw_editorial_title_banner(draw, 84, 52, "CHRONOLOGICAL PROGRESSION · 단계별 사건 타임라인", headline, on_dark=False)

            ry = 515
            draw.line([(120, ry), (120 + int(1680 * p), ry)], fill=(190, 24, 24, 255), width=10)

            n_stops = max(1, min(5, n_c))
            if n_stops == 1:
                stop_xs = [960]
            else:
                stop_xs = [int(260 + i * (1400 / (n_stops - 1))) for i in range(n_stops)]
            card_w = min(420, max(260, 1540 // n_stops - 36))

            for idx_s in range(n_stops):
                cp = c_prog[idx_s]
                if cp <= 0.02:
                    continue
                sx = stop_xs[idx_s]
                draw.ellipse([sx - 22, ry - 22, sx + 22, ry + 22], fill=(190, 24, 24, 255), outline=(252, 249, 242, 255), width=5)
                st_tag = f"STEP 0{idx_s + 1}"
                val = c_tags[idx_s]
                desc = _clean_phrase(clauses[idx_s], 20)
                img_s = photos[idx_s % len(photos)]

                if idx_s % 2 == 0:
                    _paste_torn_photo(canvas, img_s, sx - card_w // 2, 175, card_w, 245, caption=f"{st_tag} · {val}", badge=st_tag, seed=140 + idx_s)
                    draw = ImageDraw.Draw(canvas, "RGBA")
                    _draw_felt_highlighter(draw, sx - card_w // 2, ry + 48, card_w + 20, 68, p=cp, color=(250, 204, 21) if idx_s == active_idx else (235, 228, 212))
                    draw_text_safe(draw, (sx - card_w // 2 + 12, ry + 64), desc, fill=(24, 22, 19, 255), font_size=24, bold=True)
                else:
                    _paste_torn_photo(canvas, img_s, sx - card_w // 2, ry + 55, card_w, 235, caption=f"{st_tag} · {val}", badge=st_tag, seed=140 + idx_s)
                    draw = ImageDraw.Draw(canvas, "RGBA")
                    _draw_felt_highlighter(draw, sx - card_w // 2, ry - 125, card_w + 20, 74, p=cp, color=(250, 204, 21) if idx_s == active_idx else (235, 228, 212))
                    draw_text_safe(draw, (sx - card_w // 2 + 12, ry - 108), f"[{val}] {desc}", fill=(190, 24, 24, 255), font_size=24, bold=True)

            _maybe_draw_subtitle(canvas, active_clause, on_light_paper=True)
            return canvas

        # ----------------------------------------------------------------------
        # #FIN15: Forensic Optical Lightbox — Microscope Lenses & 1..N Match Points
        # ----------------------------------------------------------------------
        if arch_idx == 15:
            canvas = _make_tactile_bg((14, 19, 28), grain_sigma=3.8, grid_type="lines", seed=115)
            draw = ImageDraw.Draw(canvas, "RGBA")
            _draw_editorial_title_banner(draw, 84, 48, "OPTICAL FORENSIC COMPARATOR · 진위 정밀 감정", headline, on_dark=True)

            lenses = [
                (480, 415, frame_a, "SAMPLE A · 대조 기준", m0, (56, 189, 248), c_prog[0]),
                (1440, 415, frame_b, "SAMPLE B · 변조·위조 적발", m1, (244, 63, 94), c_prog[min(1, n_c - 1)]),
            ]
            lr = 235
            for lx, ly, l_img, lbl, val, col, lp_lens in lenses:
                if lp_lens <= 0.02:
                    continue
                src = l_img if isinstance(l_img, Image.Image) else get_fallback_image(lr * 2, lr * 2, val)
                crop_l = fit_crop(src.convert("RGB"), lr * 2, lr * 2)
                mask = Image.new("L", (lr * 2, lr * 2), 0)
                ImageDraw.Draw(mask, "L").ellipse([0, 0, lr * 2 - 1, lr * 2 - 1], fill=255)
                canvas.paste(crop_l, (lx - lr, ly - lr), mask)
                draw = ImageDraw.Draw(canvas, "RGBA")
                draw.ellipse([lx - lr, ly - lr, lx + lr, ly + lr], outline=col + (255,), width=8)
                draw.ellipse([lx - lr + 18, ly - lr + 18, lx + lr - 18, ly + lr - 18], outline=(255, 255, 255, 110), width=2)
                draw.line([(lx - lr + 40, ly), (lx + lr - 40, ly)], fill=col + (165,), width=2)
                draw.line([(lx, ly - lr + 40), (lx, ly + lr - 40)], fill=col + (165,), width=2)
                draw_text_safe(draw, (lx - 195, ly + lr + 16), f"{lbl} ({val})", fill=col + (255,), font_size=24, bold=True)

            draw.line([(480 + lr, 415), (1440 - lr, 415)], fill=(250, 204, 21, 245), width=5)
            _draw_circular_official_seal(draw, 960, 415, dept_ko="문서감정원", sub_ko="위조판정", r=62)

            # Bottom progressive 1..N forensic verification badges
            n_pts = max(1, min(4, n_c))
            slot_w = 1680 // n_pts
            for i in range(n_pts):
                cp = c_prog[i]
                if cp <= 0.03:
                    continue
                bx = 120 + i * slot_w
                bw = slot_w - 28
                draw.rounded_rectangle([bx, 725, bx + bw, 815], radius=10, fill=(22, 30, 44, 245), outline=(250, 204, 21, 240) if i == active_idx else (56, 189, 248, 175), width=3)
                _draw_felt_highlighter(draw, bx + 12, 735, int((bw - 24) * cp), 68, p=cp, color=(220, 38, 38) if i == active_idx else (30, 58, 92), alpha=185)
                draw_text_safe(draw, (bx + 24, 752), f"[감정 0{i + 1} · {c_tags[i]}] {_clean_phrase(clauses[i], 18)}", fill=(255, 255, 255, 255), font_size=23, bold=True)

            _maybe_draw_subtitle(canvas, active_clause, on_light_paper=False)
            return canvas

        # ----------------------------------------------------------------------
        # #FIN16: Editorial Ledger Paper — Dynamic 1..N Waterfall Asset Drain
        # ----------------------------------------------------------------------
        if arch_idx == 16:
            canvas = _make_tactile_bg((238, 244, 248), grain_sigma=3.8, grid_type="lines", seed=116)
            draw = ImageDraw.Draw(canvas, "RGBA")
            _draw_editorial_title_banner(draw, 84, 52, "DEFICIT WATERFALL · 원금 증발 및 미상환 손실 정산", headline, on_dark=False)

            n_wf = max(1, min(5, n_c))
            wf_cols = [(14, 116, 144), (217, 119, 6), (234, 88, 12), (190, 24, 24), (136, 19, 55)]
            avail_w = 1220
            slot_w = avail_w // n_wf
            bw = min(310, max(165, slot_w - 38))

            for i in range(n_wf):
                cp = c_prog[i]
                if cp <= 0.02:
                    continue
                bx = 110 + i * slot_w
                rat = max(0.28, 1.0 - i * (0.68 / max(1, n_wf - 1)))
                bh = max(48, int(520 * rat * cp))
                top_y = 215 + int((520 - int(520 * rat)) * 0.85)
                col = wf_cols[i % len(wf_cols)]
                draw.rounded_rectangle([bx + 8, top_y + 8, bx + bw + 8, top_y + bh + 8], radius=10, fill=(15, 23, 42, 45))
                draw.rounded_rectangle([bx, top_y, bx + bw, top_y + bh], radius=10, fill=col + (245,))
                if i == active_idx:
                    _draw_felt_highlighter(draw, bx, top_y - 54, bw, 46, p=cp)
                draw_text_safe(draw, (bx + 10, top_y - 46), str(c_tags[i])[:12], fill=col + (255,), font_size=30, bold=True)
                draw_text_safe(draw, (bx + 10, 790), f"0{i + 1} · {_clean_phrase(clauses[i], 11)}", fill=(30, 41, 59, 255), font_size=21, bold=True)
                if i > 0:
                    prev_bx = 110 + (i - 1) * slot_w + bw // 2
                    _draw_hand_arrow(draw, prev_bx, top_y - 20, bx + bw // 2, top_y + 10, color=(190, 24, 24), width=5, curve_lift=-35)

            if n_c >= 3 and c_prog[1] > 0.1:
                _paste_torn_photo(canvas, frame_a, 1390, 185, 430, 265, caption=f"원금 유입 · {m0}", badge="ORIGIN", seed=161)
                _paste_torn_photo(canvas, frame_b, 1390, 520, 430, 265, caption=f"손실 확정 · {m1}", badge="LOSS", seed=162)
            else:
                _paste_torn_photo(canvas, frame_a, 1400, 210, 420, 520, caption=cap_ab, badge="LOSS", seed=161)
            _maybe_draw_subtitle(canvas, active_clause, on_light_paper=True)
            return canvas

        # ----------------------------------------------------------------------
        # #FIN17: Dark Blueprint Grid — Crypto Tumbler Splitter to 1..N Wallets
        # ----------------------------------------------------------------------
        if arch_idx == 17:
            canvas = _make_tactile_bg((11, 19, 32), grain_sigma=4.0, grid_type="lines", seed=117)
            draw = ImageDraw.Draw(canvas, "RGBA")
            _draw_editorial_title_banner(draw, 84, 48, "BLOCKCHAIN TUMBLER TRACE · 가상자산 쪼개기 추적", headline, on_dark=True)

            if n_c >= 3 and c_prog[1] > 0.1:
                _paste_torn_photo(canvas, frame_a, 84, 185, 410, 255, caption=f"원점 지갑 · {m0}", badge="MASTER WALLET", seed=171)
                _paste_torn_photo(canvas, frame_b, 84, 515, 410, 255, caption=f"세탁 종점 · {m1}", badge="COLD STORAGE", seed=172)
            else:
                _paste_torn_photo(canvas, frame_a, 88, 220, 420, 460, caption=f"원점 지갑 · {m0}", badge="MASTER WALLET", seed=171)
            draw = ImageDraw.Draw(canvas, "RGBA")

            sx, sy = 540, 450
            n_w = max(1, min(5, n_c))
            w_step = 0 if n_w == 1 else 540 // max(1, n_w - 1)
            w_start = 430 if n_w == 1 else 185
            box_h = 115 if n_w <= 3 else 92

            wallets = [
                (1320, w_start + i * w_step, f"0{i + 1} · {c_tags[i]} — {_clean_phrase(clauses[i], 14)}", c_prog[i])
                for i in range(n_w)
            ]
            for m_i in range(5):
                mx, my = 910, 215 + m_i * 118
                draw.line([(sx, sy), (mx, my)], fill=(56, 189, 248, 195), width=3)
                for wx, wy, _, wp in wallets:
                    if wp > 0.03:
                        draw.line([(mx + 120, my), (wx, wy + box_h // 2)], fill=(250, 204, 21, 185), width=3)
                draw.rounded_rectangle([mx - 20, my - 24, mx + 135, my + 24], radius=8, fill=(18, 32, 54, 250), outline=(56, 189, 248, 240), width=2)
                draw_text_safe(draw, (mx - 2, my - 14), f"MIXER #{m_i + 1:02d}", fill=(248, 250, 252, 255), font_size=18, bold=True)

            for idx_w, (wx, wy, w_lbl, wp) in enumerate(wallets):
                if wp <= 0.03:
                    continue
                draw.rounded_rectangle([wx, wy, wx + 510, wy + box_h], radius=12, fill=(24, 36, 58, 250), outline=(244, 63, 94, 255) if idx_w == active_idx else (250, 204, 21, 245), width=4 if idx_w == active_idx else 2)
                draw_text_safe(draw, (wx + 24, wy + box_h // 2 - 16), w_lbl[:24], fill=(250, 204, 21, 255), font_size=24, bold=True)

            _maybe_draw_subtitle(canvas, active_clause, on_light_paper=False)
            return canvas

        # ----------------------------------------------------------------------
        # #FIN18: Court Verdict Document — 1..2 Photos & Dynamic 1..N Verdict Orders
        # ----------------------------------------------------------------------
        if arch_idx == 18:
            canvas = _make_tactile_bg((244, 236, 220), grain_sigma=4.2, grid_type="dots", seed=118)
            draw = ImageDraw.Draw(canvas, "RGBA")
            draw.rectangle([42, 36, W - 42, H - 36], outline=(185, 28, 28, 245), width=6)
            draw.rectangle([56, 50, W - 56, H - 50], outline=(185, 28, 28, 165), width=2)

            draw_text_safe(draw, (560, 78), "중화인민공화국 인민법원 형사 판결문", fill=(185, 28, 28, 255), font_size=42, bold=True)
            draw.line([(120, 145), (W - 120, 145)], fill=(185, 28, 28, 220), width=3)

            if n_c >= 3 and c_prog[1] > 0.1:
                _paste_torn_photo(canvas, frame_a, 115, 185, 510, 265, caption=f"피고인 판결 · {m0}", badge="VERDICT A", paperclip=True, seed=181)
                _paste_torn_photo(canvas, frame_b, 115, 525, 510, 265, caption=f"몰수 집행 · {m1}", badge="VERDICT B", seed=182)
            else:
                _paste_torn_photo(canvas, frame_a, 120, 200, 520, 540, caption=f"선고 확정 · {m0}", badge="VERDICT", paperclip=True, seed=181)
            draw = ImageDraw.Draw(canvas, "RGBA")

            for idx_c, cl_txt in enumerate(clauses):
                cp = c_prog[idx_c]
                if cp <= 0.02:
                    continue
                vy = 195 + idx_c * min(125, 520 // max(1, n_c))
                _draw_felt_highlighter(
                    draw, 710, vy, 1060, 88, p=cp,
                    color=(250, 204, 21) if idx_c == active_idx else (236, 226, 206),
                    alpha=195 if idx_c == active_idx else 145,
                )
                draw.rectangle([710, vy, 722, vy + 88], fill=(185, 28, 28, 255))
                draw_text_safe(draw, (740, vy + 10), f"판결 주문 제0{idx_c + 1}항 · [{c_tags[idx_c]}]", fill=(185, 28, 28, 255), font_size=22, bold=True)
                draw_text_safe(draw, (740, vy + 42), _clean_phrase(cl_txt, 28), fill=(20, 18, 16, 255), font_size=30, bold=True)

            _draw_circular_official_seal(draw, 1610, 660, dept_ko="중급인민법원", sub_ko="형사판결전용장", r=98, alpha=225)
            _maybe_draw_subtitle(canvas, active_clause, on_light_paper=True)
            return canvas

        # ----------------------------------------------------------------------
        # #FIN19: Seismograph Strip — Dynamic 1..N Anomaly Spikes & Pinned Photos
        # ----------------------------------------------------------------------
        if arch_idx == 19:
            canvas = _make_tactile_bg((16, 22, 30), grain_sigma=4.0, grid_type="lines", seed=119)
            draw = ImageDraw.Draw(canvas, "RGBA")
            _draw_editorial_title_banner(draw, 84, 48, "ANOMALY SEISMOGRAPH · 비정상 폭증 스파이크 탐지", headline, on_dark=True)

            base_y = 685
            n_sp = max(1, min(4, n_c))
            spike_centers = [int(28 + (i + 0.5) * (56 / n_sp)) for i in range(n_sp)]
            pts_wave = []
            for i in range(90):
                tx = 96 + i * 13
                lift = int(20 * math.sin(i * 0.7))
                for s_idx, sc in enumerate(spike_centers):
                    if abs(i - sc) <= 5:
                        cp = c_prog[s_idx]
                        amp = 240 + int(230 * ((s_idx + 1) / n_sp))
                        lift = max(lift, int(amp * math.cos((i - sc) / 5.0 * (math.pi * 0.5)) * cp))
                pts_wave.append((tx, base_y - lift))

            draw.line([(96, base_y), (1260, base_y)], fill=(100, 116, 139, 140), width=2)
            draw.line(pts_wave, fill=(56, 189, 248, 240), width=5)

            for s_idx, sc in enumerate(spike_centers):
                cp = c_prog[s_idx]
                if cp <= 0.04:
                    continue
                s0, s1 = max(0, sc - 5), min(len(pts_wave), sc + 6)
                draw.line(pts_wave[s0:s1], fill=(244, 63, 94, 255), width=8)
                px, py = pts_wave[sc]
                _draw_hand_circle(draw, px, py + 24, 68, 68, color=(250, 204, 21), width=4, p=cp)
                draw_text_safe(draw, (max(96, px - 140), max(145, py - 68)), f"0{s_idx + 1} · {c_tags[s_idx]}", fill=(250, 204, 21, 255), font_size=28, bold=True)

            if n_c >= 2 and c_prog[1] > 0.1:
                _paste_torn_photo(canvas, frame_a, 1310, 175, 510, 260, caption=f"이상 징후 A · {m0}", badge="SPIKE #1", seed=191)
                _paste_torn_photo(canvas, frame_b, 1310, 510, 510, 260, caption=f"이상 징후 B · {m1}", badge="SPIKE #2", seed=192)
            else:
                _paste_torn_photo(canvas, frame_a, 1310, 195, 510, 520, caption=cap_ab, badge="SPIKE ×40", seed=191)
            _maybe_draw_subtitle(canvas, active_clause, on_light_paper=False)
            return canvas

        # ----------------------------------------------------------------------
        # #FIN20: Minimalist Editorial Fulcrum — Dynamic 1..N Stacked Debt Weights
        # ----------------------------------------------------------------------
        if arch_idx == 20:
            canvas = _make_tactile_bg((242, 239, 231), grain_sigma=3.8, grid_type="dots", seed=120)
            draw = ImageDraw.Draw(canvas, "RGBA")
            _draw_editorial_title_banner(draw, 84, 52, "ASYMMETRIC LEVERAGE · 무담보 부실 채무 불균형", headline, on_dark=False)

            fx, fy = 820, 620
            draw.polygon([(fx, fy), (fx - 95, 810), (fx + 95, 810)], fill=(30, 28, 24, 255))
            draw.line([(220, 410), (1490, 725)], fill=(30, 28, 24, 255), width=16)

            _paste_torn_photo(canvas, frame_a, 130, 155, 360, 225, caption=f"담보 실체 · {m0}", badge="COLLATERAL", seed=201)
            if n_c >= 3 and c_prog[1] > 0.1:
                _paste_torn_photo(canvas, frame_b, 530, 155, 340, 225, caption=f"현장 증거 · {m1}", badge="EVIDENCE", seed=202)
            draw = ImageDraw.Draw(canvas, "RGBA")

            # Right: Stack 1..N heavy crimson debt blocks as clauses progress
            n_blocks = max(1, min(4, n_c))
            bh = min(135, 420 // n_blocks)
            for b_i in range(n_blocks):
                cp = c_prog[b_i]
                if cp <= 0.03:
                    continue
                bx0 = 1060
                bw = 720
                by0 = 685 - (b_i + 1) * (bh + 12)
                col = (185, 28, 28, 250) if b_i == active_idx else (136, 19, 55, 240)
                draw.rounded_rectangle([bx0 + 8, by0 + 10, bx0 + bw + 8, by0 + bh + 10], radius=12, fill=(20, 16, 12, 80))
                draw.rounded_rectangle([bx0, by0, bx0 + bw, by0 + bh], radius=12, fill=col, outline=(250, 204, 21, 240) if b_i == active_idx else (255, 255, 255, 160), width=3)
                draw_text_safe(draw, (bx0 + 28, by0 + 16), f"0{b_i + 1} · {c_tags[b_i]}", fill=(250, 204, 21, 255), font_size=26, bold=True)
                draw_text_safe(draw, (bx0 + 28, by0 + 54), _clean_phrase(clauses[b_i], 24), fill=(255, 255, 255, 255), font_size=24, bold=True)

            _maybe_draw_subtitle(canvas, active_clause, on_light_paper=True)
            return canvas

        # ----------------------------------------------------------------------
        # #FIN21: Tactile Cutout Paper Rings — Dynamic 1..N Concentric Deconstruction
        # ----------------------------------------------------------------------
        if arch_idx == 21:
            canvas = _make_tactile_bg((232, 229, 222), grain_sigma=4.2, grid_type="dots", seed=121)
            draw = ImageDraw.Draw(canvas, "RGBA")
            _draw_editorial_title_banner(draw, 84, 52, "LAYER DECONSTRUCTION · 다중 위장 구조 해부", headline, on_dark=False)

            cx, cy = 520, 520
            n_rings = max(1, min(4, n_c))
            ring_cols = [(30, 41, 59), (14, 116, 144), (217, 119, 6), (190, 24, 24)]
            radii = [int(340 - i * (185 / max(1, n_rings))) for i in range(n_rings)]

            for idx_r, rad in enumerate(radii):
                cp = c_prog[idx_r]
                r_cur = int(rad * max(0.25, cp))
                col = ring_cols[idx_r % len(ring_cols)]
                draw.ellipse([cx - r_cur + 8, cy - r_cur + 10, cx + r_cur + 8, cy + r_cur + 10], fill=(15, 15, 15, 55))
                draw.ellipse([cx - r_cur, cy - r_cur, cx + r_cur, cy + r_cur], fill=col + (245,), outline=(252, 249, 242, 240), width=5)

            core_r = max(85, radii[-1] - 42)
            src_c = frame_a if isinstance(frame_a, Image.Image) else get_fallback_image(core_r * 2, core_r * 2, m0)
            crop_c = fit_crop(src_c.convert("RGB"), core_r * 2, core_r * 2)
            mask = Image.new("L", (core_r * 2, core_r * 2), 0)
            ImageDraw.Draw(mask, "L").ellipse([0, 0, core_r * 2 - 1, core_r * 2 - 1], fill=255)
            canvas.paste(crop_c, (cx - core_r, cy - core_r), mask)
            draw = ImageDraw.Draw(canvas, "RGBA")

            for idx_r, rad in enumerate(radii):
                cp = c_prog[idx_r]
                if cp <= 0.03:
                    continue
                col = ring_cols[idx_r % len(ring_cols)]
                ly = 185 + idx_r * min(155, 560 // max(1, n_rings))
                draw.line([(cx + int(rad * 0.7), cy - int(rad * 0.3)), (1010, ly + 38)], fill=col + (235,), width=4)
                _draw_felt_highlighter(
                    draw, 1010, ly, 810, 78, p=cp,
                    color=(250, 204, 21) if idx_r == active_idx else (255, 255, 255),
                    alpha=195,
                )
                draw.rectangle([1010, ly, 1022, ly + 78], fill=col + (255,))
                draw_text_safe(draw, (1042, ly + 18), f"[0{idx_r + 1} · {c_tags[idx_r]}] {_clean_phrase(clauses[idx_r], 20)}", fill=(20, 20, 18, 255), font_size=28, bold=True)

            _maybe_draw_subtitle(canvas, active_clause, on_light_paper=True)
            return canvas

        # ----------------------------------------------------------------------
        # #FIN22: Full-Bleed Magazine Collage Treemap — Dynamic 1..N Asset Cells
        # ----------------------------------------------------------------------
        if arch_idx == 22:
            canvas = _make_tactile_bg((24, 22, 20), grain_sigma=3.5, grid_type="none", seed=122)
            src_a = frame_a if isinstance(frame_a, Image.Image) else get_fallback_image(1120, H, m0)
            left_tile = ImageEnhance.Brightness(fit_crop(src_a.convert("RGB"), 1120, H)).enhance(0.72)
            canvas.paste(left_tile, (0, 0))

            src_b = frame_b if isinstance(frame_b, Image.Image) else src_a
            top_r = ImageEnhance.Brightness(fit_crop(src_b.convert("RGB"), W - 1132, 530)).enhance(0.68)
            canvas.paste(top_r, (1132, 0))

            if n_c >= 3 and isinstance(frame_c, Image.Image):
                bot_r = ImageEnhance.Brightness(fit_crop(frame_c.convert("RGB"), W - 1132, H - 542)).enhance(0.45)
                canvas.paste(bot_r, (1132, 542))

            draw = ImageDraw.Draw(canvas, "RGBA")
            if n_c < 3 or not isinstance(frame_c, Image.Image):
                draw.rectangle([1132, 542, W, H], fill=(165, 24, 28, 255))
            else:
                draw.rectangle([1132, 542, W, H], fill=(165, 24, 28, 155))

            draw.line([(1126, 0), (1126, H)], fill=(252, 249, 242, 255), width=12)
            draw.line([(1126, 536), (W, 536)], fill=(252, 249, 242, 255), width=12)

            # Left cell: Clause 1 + optional Clause 4+
            _draw_felt_highlighter(draw, 72, 110, 760, 105, p=c_prog[0])
            draw_text_safe(draw, (92, 125), c_tags[0][:14], fill=(18, 18, 16, 255), font_size=68, bold=True)
            draw_text_safe(draw, (76, 240), _clean_phrase(c0, 24), fill=(255, 255, 255, 255), font_size=34, bold=True, stroke_width=3, stroke_fill=(0, 0, 0, 220))

            for extra_i in range(3, n_c):
                if c_prog[extra_i] > 0.04:
                    ey = 360 + (extra_i - 3) * 110
                    _draw_felt_highlighter(draw, 72, ey, 860, 82, p=c_prog[extra_i], color=(220, 38, 38), alpha=215)
                    draw_text_safe(draw, (92, ey + 18), f"[{c_tags[extra_i]}] {_clean_phrase(clauses[extra_i], 22)}", fill=(255, 255, 255, 255), font_size=28, bold=True)

            if c_prog[min(1, n_c - 1)] > 0.03:
                draw_text_safe(draw, (1180, 68), "SEIZED ASSET #02", fill=(250, 204, 21, 255), font_size=22, bold=True)
                draw_text_safe(draw, (1180, 110), c_tags[min(1, n_c - 1)][:16], fill=(255, 255, 255, 255), font_size=48, bold=True, stroke_width=3, stroke_fill=(0, 0, 0, 220))
                draw_text_safe(draw, (1180, 185), _clean_phrase(c1, 18), fill=(248, 250, 252, 255), font_size=26, bold=True, stroke_width=2, stroke_fill=(0, 0, 0, 200))

            if c_prog[min(2, n_c - 1)] > 0.03:
                c2_txt = clauses[2] if n_c > 2 else clauses[-1]
                draw_text_safe(draw, (1180, 585), "FINAL FORFEITURE · 최종 환수·몰수", fill=(250, 204, 21, 255), font_size=22, bold=True)
                draw_text_safe(draw, (1180, 630), c_tags[min(2, n_c - 1)][:16], fill=(255, 255, 255, 255), font_size=50, bold=True)
                draw_text_safe(draw, (1180, 705), _clean_phrase(c2_txt, 18), fill=(254, 226, 226, 255), font_size=26, bold=True)

            _maybe_draw_subtitle(canvas, active_clause, on_light_paper=False)
            return canvas

        # ----------------------------------------------------------------------
        # #FIN23: Full-Screen Basin Satellite Route + Dynamic 1..N Waypoints & Profile
        # ----------------------------------------------------------------------
        if arch_idx == 23:
            canvas = _load_sat_fullbleed("plate_kunming_basin_sat_z12.png", brightness=0.84, contrast=1.10)
            draw = ImageDraw.Draw(canvas, "RGBA")
            _draw_editorial_title_banner(draw, 72, 46, "GPS CORRIDOR & ELEVATION · 심야 이동 궤적 추적", headline, on_dark=True, on_sat=True)

            all_route_pts = [(180, 480), (470, 310), (760, 430), (1040, 270), (1260, 380)]
            n_pts = max(2, min(5, n_c if n_c >= 2 else 3))
            route_pts = [all_route_pts[int(round(i * (len(all_route_pts) - 1) / max(1, n_pts - 1)))] for i in range(n_pts)]

            for seg_i in range(len(route_pts) - 1):
                cp = c_prog[min(seg_i, len(c_prog) - 1)]
                if cp <= 0.02:
                    continue
                x0, y0 = route_pts[seg_i]
                x1, y1 = route_pts[seg_i + 1]
                cx_seg = int(x0 + (x1 - x0) * cp)
                cy_seg = int(y0 + (y1 - y0) * cp)
                draw.line([(x0, y0), (cx_seg, cy_seg)], fill=(250, 204, 21, 255), width=8)

            for idx_pt, (gx, gy) in enumerate(route_pts):
                cp = c_prog[min(idx_pt, len(c_prog) - 1)]
                if cp <= 0.02:
                    continue
                draw.ellipse([gx - 16, gy - 16, gx + 16, gy + 16], fill=(190, 24, 24, 255), outline=(255, 255, 255, 255), width=3)
                tag_pt = c_tags[min(idx_pt, len(c_tags) - 1)]
                draw.rounded_rectangle([gx - 85, gy - 62, gx + 115, gy - 22], radius=6, fill=(14, 18, 24, 230), outline=(250, 204, 21, 220), width=2)
                draw_text_safe(draw, (gx - 72, gy - 56), f"0{idx_pt + 1} · {tag_pt[:10]}", fill=(250, 204, 21, 255), font_size=19, bold=True)

            if n_c >= 2 and c_prog[1] > 0.1:
                _paste_torn_photo(canvas, frame_a, 1340, 140, 245, 225, caption=m0, badge="GPS #1", seed=231)
                _paste_torn_photo(canvas, frame_b, 1615, 140, 245, 225, caption=m1, badge="GPS #2", seed=232)
            else:
                _paste_torn_photo(canvas, frame_a, 1360, 140, 470, 390, caption=cap_ab, badge="GPS LOCK", seed=231)
            draw = ImageDraw.Draw(canvas, "RGBA")

            draw.rectangle([0, 685, W, H], fill=(15, 23, 42, 235))
            draw.line([(0, 685), (W, 685)], fill=(250, 204, 21, 255), width=4)
            prof_pts = []
            for i in range(64):
                px = 120 + i * 27
                py = int(895 - (55 + 115 * abs(math.sin(i * 0.22))) * p)
                prof_pts.append((px, py))
            draw.polygon([(120, 915)] + prof_pts + [(prof_pts[-1][0], 915)], fill=(56, 189, 248, 65))
            draw.line(prof_pts, fill=(56, 189, 248, 255), width=5)
            draw_text_safe(draw, (120, 704), f"이동 궤적·고도 동기화 [{active_idx + 1}/{n_c}단계]: {_clean_phrase(active_clause, 32)}", fill=(250, 204, 21, 255), font_size=26, bold=True)
            _maybe_draw_subtitle(canvas, active_clause, on_light_paper=False)
            return canvas

        # ----------------------------------------------------------------------
        # #FIN24: Special Audit Dossier Sheet — 1..2 Photos & Dynamic 1..N Hand-Checked Flags
        # ----------------------------------------------------------------------
        canvas = _make_tactile_bg((246, 242, 233), grain_sigma=4.0, grid_type="lines", seed=124)
        draw = ImageDraw.Draw(canvas, "RGBA")
        _draw_editorial_title_banner(draw, 84, 52, "FORENSIC RED FLAGS · 핵심 사기 식별 경고 신호", headline, on_dark=False)

        if n_c >= 3 and c_prog[1] > 0.1:
            _paste_torn_photo(canvas, frame_a, 88, 185, 530, 265, caption=f"경고 증거 A · {m0}", badge="ALERT #1", paperclip=True, seed=241)
            _paste_torn_photo(canvas, frame_b, 88, 520, 530, 265, caption=f"경고 증거 B · {m1}", badge="ALERT #2", seed=242)
        else:
            _paste_torn_photo(canvas, frame_a, 92, 195, 550, 560, caption=cap_ab, badge="WARNING", paperclip=True, seed=241)
        draw = ImageDraw.Draw(canvas, "RGBA")

        n_checks = max(1, min(5, n_c))
        c_step = min(180, 580 // max(1, n_checks))
        for idx_c in range(n_checks):
            cp = c_prog[idx_c]
            if cp <= 0.02:
                continue
            cy = 195 + idx_c * c_step
            draw.rectangle([720, cy, 780, cy + 60], outline=(30, 28, 24, 255), width=4)
            draw.line([(732, cy + 32), (750, cy + 50), (794, cy - 6)], fill=(190, 24, 24, 255), width=8)
            _draw_felt_highlighter(
                draw, 812, cy - 4, 1010, 68, p=cp,
                color=(250, 204, 21) if idx_c == active_idx else (238, 232, 218),
                alpha=190 if idx_c == active_idx else 155,
            )
            draw_text_safe(
                draw, (832, cy + 12),
                f"[{c_tags[idx_c]}] {_clean_phrase(clauses[idx_c], 26)}",
                fill=(20, 18, 16, 255), font_size=29, bold=True,
            )

        _maybe_draw_subtitle(canvas, active_clause, on_light_paper=True)
        return canvas

    return _render


render_fin1_dual_curve_ledger = _make_archetype_renderer(1)
render_fin2_currency_flow_balance = _make_archetype_renderer(2)
render_fin3_asset_freeze_portfolio = _make_archetype_renderer(3)
render_fin5_oversized_phone_shill_expose = _make_archetype_renderer(6)
render_fin6_satellite_compound_power_anomaly = _make_archetype_renderer(5)

FINANCIAL_ARCHETYPE_RENDERERS: dict[str, Any] = {
    arch_id: _make_archetype_renderer(idx)
    for idx, arch_id in enumerate(CANONICAL_24_FIN_ARCHETYPES, start=1)
}
FINANCIAL_ARCHETYPE_RENDERERS.update(
    {
        "#FIN1_DUAL_CURVE_LEDGER": render_fin1_dual_curve_ledger,
        "#FIN2_CURRENCY_FLOW_BALANCE": render_fin2_currency_flow_balance,
        "#FIN3_ASSET_FREEZE_PORTFOLIO": render_fin3_asset_freeze_portfolio,
        "#FIN4_FULLSCREEN_EURASIA_MONEY_MAP": _make_archetype_renderer(4),
        "#FIN5_OVERSIZED_PHONE_SHILL_EXPOSE": render_fin5_oversized_phone_shill_expose,
        "#FIN6_SATELLITE_COMPOUND_POWER_ANOMALY": render_fin6_satellite_compound_power_anomaly,
    }
)


class FinancialVoxSemanticRouter:
    """Dedicated semantic router for financial forensic vox with strict Zero-Repetition (`max_uses = 1`)."""

    def __init__(self) -> None:
        self.recent_archetypes: list[str] = []
        self.archetype_usage_counts: dict[str, int] = {}

    def reset_history(self) -> None:
        self.recent_archetypes.clear()
        self.archetype_usage_counts.clear()

    def route_beat(self, narration_text: str) -> dict[str, Any]:
        text = str(narration_text or "").strip()
        min_use = min((self.archetype_usage_counts.get(a, 0) for a in CANONICAL_24_FIN_ARCHETYPES), default=0)
        recent_block = set(self.recent_archetypes[-8:])
        least_used_pool = [
            arch_id
            for arch_id in CANONICAL_24_FIN_ARCHETYPES
            if self.archetype_usage_counts.get(arch_id, 0) == min_use and arch_id not in recent_block
        ]
        if not least_used_pool:
            least_used_pool = [
                arch_id
                for arch_id in CANONICAL_24_FIN_ARCHETYPES
                if self.archetype_usage_counts.get(arch_id, 0) == min_use
            ]
        candidate_pool = least_used_pool if least_used_pool else CANONICAL_24_FIN_ARCHETYPES

        best_score = -1.0
        best_arch = candidate_pool[len(self.recent_archetypes) % len(candidate_pool)]
        best_label = FINANCIAL_VOX_ARCHETYPE_RULES[best_arch]["label"]
        best_cluster = FINANCIAL_VOX_ARCHETYPE_RULES[best_arch]["cluster"]

        last_cluster = (
            FINANCIAL_VOX_ARCHETYPE_RULES.get(self.recent_archetypes[-1], {}).get("cluster")
            if self.recent_archetypes
            else None
        )

        for arch_id in candidate_pool:
            rule = FINANCIAL_VOX_ARCHETYPE_RULES[arch_id]
            m_ko = bool(re.search(rule["regex_ko"], text, re.IGNORECASE))
            m_vi = bool(re.search(rule["regex_vi"], text, re.IGNORECASE))
            if not (m_ko or m_vi):
                continue
            score = float(rule["priority_score"]) + (30.0 if m_ko else 0.0) + (25.0 if m_vi else 0.0)
            if last_cluster and rule["cluster"] == last_cluster:
                score -= 25.0
            if score > best_score:
                best_score = score
                best_arch = arch_id
                best_label = rule["label"]
                best_cluster = rule["cluster"]

        self.recent_archetypes.append(best_arch)
        self.archetype_usage_counts[best_arch] = self.archetype_usage_counts.get(best_arch, 0) + 1

        return {
            "archetype": best_arch,
            "label": best_label,
            "cluster": best_cluster,
            "score": max(100.0 if best_score < 0 else best_score, 0.0),
        }

    def _score_beat_for_vox(self, narration_text: str) -> float:
        text = str(narration_text or "").strip()
        best = 0.0
        for arch_id in CANONICAL_24_FIN_ARCHETYPES:
            rule = FINANCIAL_VOX_ARCHETYPE_RULES[arch_id]
            m_ko = bool(re.search(rule["regex_ko"], text, re.IGNORECASE))
            m_vi = bool(re.search(rule["regex_vi"], text, re.IGNORECASE))
            if m_ko or m_vi:
                sc = float(rule["priority_score"]) + (30.0 if m_ko else 0.0) + (25.0 if m_vi else 0.0)
                if sc > best:
                    best = sc
        if re.search(r"\d", text):
            best += 8.0
        return best

    def route_timeline(
        self,
        beats: list[dict[str, Any]],
        job: dict[str, Any] | None = None,
        enforce_dna_mix: bool | None = None,
    ) -> list[dict[str, Any]]:
        """Routes an entire timeline enforcing `max_uses = 1` (0% duplicate Vox archetypes),
        the locked Channel DNA Mix (50% Real Footage + 30% Vox Motion + 10% AI Visual + 10% Flexible Reserve),
        and attaches flexible `voice_spec`.
        """
        from documentary.vox_engine.semantic_router import (
            DNA_VISUAL_MIX_50_30_10_10,
            assign_non_vox_dna_slots,
            build_voice_spec_for_beat,
            resolve_scene_motion_treatment,
        )

        self.reset_history()
        total_beats = len(beats)
        should_enforce_dna = (
            bool(enforce_dna_mix)
            if enforce_dna_mix is not None
            else ((job is not None and total_beats >= 10) or total_beats > len(CANONICAL_24_FIN_ARCHETYPES))
        )

        if not should_enforce_dna:
            routed_direct: list[dict[str, Any]] = []
            for idx, beat in enumerate(beats):
                text = str(beat.get("narration_text") or beat.get("text") or "").strip()
                decision = self.route_beat(text)
                voice_spec = beat.get("voice_spec") or build_voice_spec_for_beat(beat, beat_index=idx)
                motion_treatment, render_vox_board = resolve_scene_motion_treatment(
                    text, decision["archetype"], decision["cluster"], voice_spec.get("clauses") or [text], idx
                )
                routed_direct.append(
                    {
                        **beat,
                        "scene_archetype": decision["archetype"],
                        "archetype_label": decision["label"],
                        "archetype_cluster": decision["cluster"],
                        "dna_visual_slot": "vox_motion",
                        "motion_treatment": motion_treatment,
                        "render_vox_board": render_vox_board,
                        "dna_mix_target": dict(DNA_VISUAL_MIX_50_30_10_10),
                        "voice_spec": voice_spec,
                    }
                )
            return routed_direct

        vox_quota = max(1, round(total_beats * 0.30))
        scored_candidates: list[tuple[float, int]] = []
        for idx, beat in enumerate(beats):
            text = str(beat.get("narration_text") or beat.get("text") or "").strip()
            scored_candidates.append((self._score_beat_for_vox(text), idx))

        selected_vox_indices: set[int] = set()
        sorted_candidates = sorted(scored_candidates, key=lambda x: (-x[0], x[1]))
        for min_gap in (2, 1):
            for sc, idx in sorted_candidates:
                if len(selected_vox_indices) >= vox_quota:
                    break
                if idx in selected_vox_indices:
                    continue
                if min_gap == 2 and sc <= 0.0 and any(s > 0.0 for s, _ in sorted_candidates):
                    continue
                if all(abs(idx - chosen) >= min_gap for chosen in selected_vox_indices):
                    selected_vox_indices.add(idx)
            if len(selected_vox_indices) >= vox_quota:
                break

        routed: list[dict[str, Any]] = []
        for idx, beat in enumerate(beats):
            text = str(beat.get("narration_text") or beat.get("text") or "").strip()
            voice_spec = beat.get("voice_spec") or build_voice_spec_for_beat(beat, beat_index=idx)
            if idx in selected_vox_indices:
                decision = self.route_beat(text)
                motion_treatment, render_vox_board = resolve_scene_motion_treatment(
                    text, decision["archetype"], decision["cluster"], voice_spec.get("clauses") or [text], idx
                )
                routed.append(
                    {
                        **beat,
                        "scene_archetype": decision["archetype"],
                        "archetype_label": decision["label"],
                        "archetype_cluster": decision["cluster"],
                        "dna_visual_slot": "vox_motion",
                        "motion_treatment": motion_treatment,
                        "render_vox_board": render_vox_board,
                        "dna_mix_target": dict(DNA_VISUAL_MIX_50_30_10_10),
                        "voice_spec": voice_spec,
                    }
                )
            else:
                routed.append(
                    {
                        **beat,
                        "scene_archetype": "cinema_full",
                        "archetype_label": "Full-Bleed Real Footage / AI / Flexible Scene",
                        "archetype_cluster": "cinema",
                        "dna_visual_slot": "real_footage",
                        "motion_treatment": "optical_camera_drift",
                        "render_vox_board": False,
                        "dna_mix_target": dict(DNA_VISUAL_MIX_50_30_10_10),
                        "voice_spec": voice_spec,
                    }
                )

        assign_non_vox_dna_slots(routed, total_beats)
        return routed
