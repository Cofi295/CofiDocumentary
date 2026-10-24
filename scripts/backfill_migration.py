#!/usr/bin/env python3
"""
Backfill Migration Script for CofiDocumentary (Milestone 1)
- Non-destructive backup of existing data/channel_profiles.json and data/jobs/ to data/backups/
- Repairs and backfills all 4 existing Channel Profiles in data/channel_profiles.json
- Repairs and backfills all 4 existing Jobs in data/jobs/
- Validates schema completeness and ensures non-null fields
"""

from __future__ import annotations

import copy
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
PROFILES_FILE = DATA_DIR / "channel_profiles.json"
JOBS_DIR = DATA_DIR / "jobs"
WORKSPACES_DIR = ROOT / "workspaces"
BACKUPS_DIR = DATA_DIR / "backups"

# ==============================================================================
# CANONICAL CHANNEL PROFILE BACKFILL DEFINITIONS
# ==============================================================================

PROFILES_BACKFILL: dict[str, dict[str, Any]] = {
    "channel-1e24de3ab5": {
        "id": "channel-1e24de3ab5",
        "channel_profile_id": "channel-1e24de3ab5",
        "label": "판세의 이면 · Trung Quốc - Hàn Quốc (Hạ Tầng & Địa Chính Trị)",
        "market": "KR",
        "default_language": "ko",
        "language": "ko",
        "default_duration_minutes": 22,
        "target_duration_minutes": 22,
        "default_visual_strategy": "hybrid",
        "visual_strategy": "hybrid",
        "default_ai_media_mode": "image",
        "ai_media_mode": "image",
        "default_ai_style_mode": "custom",
        "default_ai_custom_style": "2.5D Technical & Infrastructure Investigation (Bản đồ địa hình 2.5D, mặt cắt địa chất, HUD telemetry thông số kỹ thuật)",
        "dna_mode": "radar_hybrid",
        "voice_and_structure": "Phóng sự Điều tra Kỹ thuật Hàn Quốc Sắc Lạnh — Dẫn chứng Số liệu & Cơ chế Vật lý (판세의 이면 스타일 · 22 Phút)",
        "allowed_topics": "Bóc tách sâu cơ chế vật lý, địa chất, thông số kỹ thuật các đại công trình hạ tầng Trung Quốc, điểm gãy hệ thống, đập thủy điện, giao thông vận tải, kênh dẫn nước đại quy mô.",
        "forbidden_topics": "Chủ đề chính trị tranh cãi không có cơ sở kỹ thuật, tin tức giật gân nông cạn, từ khóa yếu ('이유', '역설', '문제' đứng đơn lẻ).",
        "monetization_safety_policy": "Phóng sự khoa học kỹ thuật khách quan — 100% Green Monetization, giải mã cơ chế vật lý hiện trường, không kích động.",
        "reference_image_policy": "Kết hợp Footage thực tế (công trường, đập, bản đồ vệ tinh) và AI Visual giải phẫu mặt cắt địa chất.",
        "default_creative_brief": {
            "market": "KR",
            "language": "ko",
            "target_duration_minutes": 22,
            "ai_media_mode": "image",
            "visual_strategy": "hybrid",
            "narrative_angle": "Điều tra Kỹ thuật Hạ tầng & Giải phẫu Điểm gãy Hệ thống (중국 초대형 인프라 설계 한계 & 지질 공학 분석)",
            "writing_style": "Phóng sự Điều tra Kỹ thuật Hàn Quốc Sắc Lạnh — Dẫn chứng Số liệu & Cơ chế Vật lý (판세의 이면 스타일 · 22 Phút)",
            "hook_archetype": "Con số Định lượng Cực hạn & Nghịch lý Vật lý Hiện trường (00:00–02:30)",
            "editing_archetypes": [
                "Bản đồ Địa hình 2.5D & Đường tuyến Vệ tinh",
                "HUD Số liệu Kỹ thuật & Đồ thị Độ lún",
                "Đối chiếu Bản vẽ Thiết kế vs. Hiện trường Thực tế",
                "Chapter Title Card Điện ảnh + Sound Hit"
            ],
            "opening_hook": "남쪽의 물을 북쪽으로 보내기 위해 산을 뚫고 강 위로 다리를 놓아 만든 1,432킬로미터의 인공 물길. 5,000억 위안이 투입된 중국 남수북조 중선 공정은 세기의 기적이라 불렸습니다. 하지만 수로가 지나는 허난성과 허베이성 일대에서 지반이 최대 수십 센티미터씩 내려앉고, 물이 닿기만 하면 부풀어 오르는 '팽창토'가 콘크리트 수로를 밀어 올리기 시작했습니다.",
            "notes": "Hồ sơ kênh Trung Quốc - Hàn Quốc (@판세의이면). Hạ tầng, đại công trình, đập thủy điện, cơ chế vật lý.",
            "custom_rules": "CHUẨN DNA KÊNH @판세의이면 (TRUNG QUỐC - HÀN QUỐC | 22 PHÚT | HYBRID FOOTAGE + AI)"
        },
        "editing_dna": {
            "version": 1,
            "pacing": 4.5,
            "typical_pacing_sec": 4.5,
            "visual_mix": {"footage": 0.5, "ai": 0.35, "motion": 0.15},
            "editing_archetypes": [
                "2.5d_satellite_terrain_flyover",
                "technical_hud_telemetry_gauge",
                "blueprint_vs_reality_split",
                "cinematic_chapter_card_hit"
            ],
            "subtitle_style": {
                "font_family": "Pretendard, sans-serif",
                "color": "#ffffff",
                "highlight_color": "#38bdf8",
                "font_size": 42
            },
            "color_grade": "technical_cool_cyan",
            "audio_rules": {
                "music_ducking_db": -18,
                "sfx_hit_on_chapter": True,
                "tension_drone_under_interrogation": False
            }
        },
        "self_learning_memory": {
            "analyzed_videos_count": 26,
            "winners": ["cơ chế vật lý điểm gãy", "đất trương nở", "đập Tam Hiệp"],
            "underperformers": ["tin vắn chính trị", "từ khóa chung chung"],
            "winner_patterns": ["cơ chế vật lý điểm gãy", "đất trương nở", "đập Tam Hiệp"],
            "losing_patterns": ["tin vắn chính trị", "từ khóa chung chung"],
            "upgrade_rules": {
                "what_to_stop_doing": [
                    "Tránh dùng các từ khóa yếu như '이유', '역설', '문제' đứng đơn lẻ mà không có thông số kỹ thuật",
                    "Không dùng clip stock chung chung không có bối cảnh công trình thực tế"
                ],
                "what_to_double_down_on": [
                    "Bóc tách thông số kỹ thuật cực hạn và cơ chế địa chất",
                    "Tăng cường bản đồ 2.5D và HUD telemetry"
                ],
                "next_video_upgrades": [
                    "Mở đầu bằng số liệu chênh lệch cực hạn trong 30s đầu",
                    "Tăng mật độ HUD 2.5D ở các phân cảnh giải thích cơ chế"
                ]
            },
            "next_video_upgrades": [
                "Mở đầu bằng số liệu chênh lệch cực hạn trong 30s đầu",
                "Tăng mật độ HUD 2.5D ở các phân cảnh giải thích cơ chế"
            ]
        },
        "seo_keyword_dna": {
            "primary_title_keyword": "중국 인프라의 이면",
            "primary_title_keyword_meaning_vi": "Mặt Tối & Đại Công Trình Hạ Tầng Trung Quốc",
            "keyword_placement_rule": "smart_seo_flexible",
            "secondary_anchor_keywords": [
                "판세의 이면",
                "중국 대공정",
                "남수북조",
                "삼협댐",
                "토목공학",
                "지질 역학"
            ],
            "mandatory_hashtags": [
                "#판세의이면",
                "#중국인프라",
                "#남수북조",
                "#대공정"
            ],
            "default_seo_tags": [
                "판세의이면",
                "중국인프라",
                "중국대공정",
                "남수북조",
                "삼협댐",
                "토목공학",
                "지반침하",
                "팽창토"
            ]
        },
        "editing_dna_history": [],
        "thumbnail_dna": {
            "style_preset": "infrastructure_blueprint",
            "visual_signature": "Megaproject Satellite & Geotechnical Blueprint",
            "color_palette": {
                "primary": "#38BDF8",
                "secondary": "#0F172A",
                "accent": "#F59E0B",
                "background": "#082F49"
            },
            "typography_preset": {
                "font_family": "Pretendard",
                "title_weight": "900",
                "stroke_color": "#082F49",
                "stroke_width": 6
            },
            "layout_template": "split_duality",
            "reference_character_path": "",
            "mascot_lock": False,
            "version": 1
        },
        "thumbnail_dna_history": []
    },
    "channel-e544a64b7c": {
        "id": "channel-e544a64b7c",
        "channel_profile_id": "channel-e544a64b7c",
        "label": "🇰🇷 Hồ sơ Kênh True Crime Hình Sự Trung Quốc (KR · 30 Phút · 100% Full AI)",
        "market": "KR",
        "default_language": "ko",
        "language": "ko",
        "default_duration_minutes": 30,
        "target_duration_minutes": 30,
        "default_visual_strategy": "full_ai",
        "visual_strategy": "full_ai",
        "default_ai_media_mode": "image",
        "ai_media_mode": "image",
        "default_ai_style_mode": "custom",
        "default_ai_custom_style": "Cold Forensic Noir (Tông màu điện ảnh điều tra sắc lạnh, phòng thẩm vấn, hiện trường phong tỏa)",
        "dna_mode": "custom_dna_only",
        "voice_and_structure": "Hàn Quốc (KR) — Giọng kể điều tra sắc lạnh, kịch tính, lôi cuốn (그것이 알고싶다 / 꼬꼬무 스타일 · 30 Phút · 5 Hồi)",
        "allowed_topics": "Trọng án hình sự có thật tại Trung Quốc: giết người hàng loạt, bắt cóc tống tiền, lẩn trốn thay tên đổi họ nhiều năm, đấu trí phòng thẩm vấn, phân tích tâm lý tội phạm nguy hiểm.",
        "forbidden_topics": "Án kinh tế, tham nhũng quan chức, hối lộ, chính trị, các vụ bạo lực học đường nhỏ, tranh chấp dân sự.",
        "monetization_safety_policy": "Ngôi thứ 3 theo góc nhìn Hồ sơ Điều tra viên Hình sự. Cắt bỏ 100% miêu tả hành vi bạo lực, tra tấn, máu me trực diện (áp dụng kỹ thuật Cắt cảnh Sau Cơn Bão — chuyển ngay sang khám nghiệm hiện trường, hồ sơ vật chứng và biên bản điều tra). 100% Green Monetization.",
        "reference_image_policy": "100% Full AI (full_ai) sử dụng bộ ảnh tái hiện phong cách Cold Forensic Noir, khóa nhân vật nhất quán và không hiển thị cảnh máu me phản cảm.",
        "default_creative_brief": {
            "market": "KR",
            "language": "ko",
            "target_duration_minutes": 30,
            "ai_media_mode": "image",
            "visual_strategy": "full_ai",
            "narrative_angle": "Điều tra Hồ sơ Hình sự & Giải mã Tâm lý Tội phạm Nguy hiểm (형사 수사 기록 & 프로파일링 — Ngôi thứ 3)",
            "writing_style": "Phóng sự Điều tra Hình sự Hàn Quốc Sắc Lạnh (그것이 알고싶다 / 꼬꼬무 스타일 — 5 Hồi 30 Phút)",
            "hook_archetype": "Mỏ neo Nghịch lý Vỏ bọc Hai Mặt & Hiện trường Khóa kín (00:00–03:30)",
            "editing_archetypes": [
                "Hồ sơ điều tra & Sơ đồ mạng lưới",
                "Phóng to chi tiết & Quét tài liệu",
                "Chia đôi màn hình đối chiếu",
                "Bản đồ 2.5D & Camera vệ tinh"
            ],
            "opening_hook": "샤먼의 한 고급 쇼핑몰 시계 매장. 20년 동안 단 한 번도 신분증을 쓰지 않고 유령처럼 살아온 그녀의 진짜 이름은 라오룽즈. 중국 전역을 공포에 떨게 했던 최악의 1급 수배범이었습니다.",
            "notes": "Hồ sơ Kênh True Crime Hình Sự Trung Quốc (KR - 30 Phút - Full AI). Điều tra trọng án hình sự, 100% Green Monetization.",
            "custom_rules": "CHUẨN DNA KÊNH ĐỘC QUYỀN (KR - 30 PHÚT - 100% FULL AI)"
        },
        "editing_dna": {
            "version": 1,
            "pacing": 5.5,
            "typical_pacing_sec": 5.5,
            "visual_mix": {"footage": 0.0, "ai": 0.85, "motion": 0.15},
            "editing_archetypes": [
                "forensic_case_board_red_string",
                "document_scanner_telemetry",
                "split_screen_investigation",
                "noir_chapter_transition"
            ],
            "subtitle_style": {
                "font_family": "Pretendard, sans-serif",
                "color": "#ffffff",
                "highlight_color": "#eab308",
                "font_size": 44
            },
            "color_grade": "cold_forensic_noir",
            "audio_rules": {
                "music_ducking_db": -20,
                "tension_drone_under_interrogation": True,
                "sfx_hit_on_chapter": True
            }
        },
        "self_learning_memory": {
            "analyzed_videos_count": 15,
            "winners": ["vỏ bọc hai mặt 20 năm", "giám định ADN Big Data", "phòng thẩm vấn"],
            "underperformers": ["mô tả bạo lực trực diện", "vụ án tài sản nhỏ"],
            "winner_patterns": ["vỏ bọc hai mặt 20 năm", "giám định ADN Big Data", "phòng thẩm vấn"],
            "losing_patterns": ["mô tả bạo lực trực diện", "vụ án tài sản nhỏ"],
            "upgrade_rules": {
                "what_to_stop_doing": [
                    "Không mô tả chi tiết vết thương hay máu me trực diện",
                    "Không dùng từ ngữ bạo lực trong 60 giây đầu"
                ],
                "what_to_double_down_on": [
                    "Khóa chặt góc nhìn Điều tra viên Hình sự",
                    "Tập trung vào đấu trí phòng thẩm vấn và dấu vết Big Data"
                ],
                "next_video_upgrades": [
                    "Khóa chặt góc nhìn Điều tra viên",
                    "Không hiển thị vũ khí sát thương",
                    "Tăng nhịp cắt màn hình đối chiếu hồ sơ"
                ]
            },
            "next_video_upgrades": [
                "Khóa chặt góc nhìn Điều tra viên",
                "Không hiển thị vũ khí sát thương",
                "Tăng nhịp cắt màn hình đối chiếu hồ sơ"
            ]
        },
        "seo_keyword_dna": {
            "primary_title_keyword": "중국 실화 사건",
            "primary_title_keyword_meaning_vi": "Vụ Án Có Thật ở Trung Quốc",
            "keyword_placement_rule": "smart_seo_flexible",
            "secondary_anchor_keywords": [
                "중국 미제사건",
                "실제 사건 파일",
                "공안 수사 기록",
                "특급수배록",
                "중국 강력범죄 실화"
            ],
            "mandatory_hashtags": [
                "#중국실화사건",
                "#특급수배록",
                "#중국미제사건",
                "#실화사건"
            ],
            "default_seo_tags": [
                "중국실화사건",
                "특급수배록",
                "중국미제사건",
                "실제사건파일",
                "공안수사기록",
                "중국강력범죄실화",
                "그것이알고싶다",
                "범죄실화"
            ]
        },
        "editing_dna_history": [],
        "thumbnail_dna": {
            "style_preset": "cold_forensic_noir",
            "visual_signature": "Cold Forensic Noir + 2D Golden Detective Mascot (#FFE84A)",
            "color_palette": {
                "primary": "#FFE84A",
                "secondary": "#0F172A",
                "accent": "#EF4444",
                "background": "#020617"
            },
            "typography_preset": {
                "font_family": "Pretendard",
                "title_weight": "900",
                "stroke_color": "#000000",
                "stroke_width": 6,
                "text_transform": "uppercase"
            },
            "layout_template": "broadcast_left_heavy",
            "reference_character_path": "workspaces/20261019-185102-31983814/media/style_reference/style_reference.png",
            "mascot_lock": True,
            "version": 1
        },
        "thumbnail_dna_history": []
    },
    "channel-aa913eb90d": {
        "id": "channel-aa913eb90d",
        "channel_profile_id": "channel-aa913eb90d",
        "label": "bí mật US · Archival Vault & Intelligence Declassification",
        "market": "US",
        "default_language": "en",
        "language": "en",
        "default_duration_minutes": 30,
        "target_duration_minutes": 30,
        "default_visual_strategy": "hybrid",
        "visual_strategy": "hybrid",
        "default_ai_media_mode": "mixed",
        "ai_media_mode": "mixed",
        "default_ai_style_mode": "custom",
        "default_ai_custom_style": "US Archival Intelligence & Classified Forensics",
        "dna_mode": "radar_hybrid",
        "voice_and_structure": "US Historical Documentary — Archival Vault & Intelligence Declassification · 30 Minutes",
        "allowed_topics": "US historical declassifications, Cold War covert operations, presidential executive orders, forensic institutional investigations.",
        "forbidden_topics": "Contemporary partisan politics, defamatory claims, graphic gore.",
        "monetization_safety_policy": "Third-person historical investigative documentary — 100% YouTube Green Monetization.",
        "reference_image_policy": "Archival document and evidence footage mixed with 2.5D historical maps.",
        "default_creative_brief": {
            "market": "US",
            "language": "en",
            "target_duration_minutes": 30,
            "ai_media_mode": "mixed",
            "visual_strategy": "hybrid",
            "narrative_angle": "Declassified Historical Investigation & Archival Forensics",
            "writing_style": "Cold US Investigative Documentary (Frontline / PBS style · 30 Min)",
            "hook_archetype": "Declassified Memo Paradox & Institutional Concealment",
            "editing_archetypes": [
                "Archival Document Scanner & Redaction Reveal",
                "Historical Timeline Telemetry",
                "Archival Photo Zoom & Parallax",
                "Chapter Title Card + Sound Hit"
            ],
            "opening_hook": "In the national archives, a single declassified memorandum held back for forty years revealed what really happened behind closed doors.",
            "notes": "US Archival Vault & Intelligence Declassification documentary profile.",
            "custom_rules": "STRICT US ARCHIVAL VAULT DNA (US - 30 MIN - HYBRID FOOTAGE + AI)"
        },
        "editing_dna": {
            "version": 1,
            "pacing": 5.0,
            "typical_pacing_sec": 5.0,
            "visual_mix": {"footage": 0.6, "ai": 0.25, "motion": 0.15},
            "editing_archetypes": [
                "archival_document_scanner",
                "historical_map_parallax",
                "split_screen_memo",
                "chapter_title_card_hit"
            ],
            "subtitle_style": {
                "font_family": "Inter, sans-serif",
                "color": "#f8fafc",
                "highlight_color": "#38bdf8",
                "font_size": 40
            },
            "color_grade": "archival_warm_vintage",
            "audio_rules": {
                "music_ducking_db": -16,
                "typewriter_sound_on_memo": True,
                "sfx_hit_on_chapter": True
            }
        },
        "self_learning_memory": {
            "analyzed_videos_count": 57,
            "winners": [
                "Why Donald Trump's Parents Hated Him So Much",
                "Mamie Eisenhower's Marriage Was Much Nastier Than You Thought"
            ],
            "underperformers": [
                "generic news recap",
                "contemporary partisan opinion"
            ],
            "winner_patterns": [
                "personal paradox behind power",
                "disturbing marriage truth",
                "unseen institutional archives"
            ],
            "losing_patterns": [
                "surface-level political commentary",
                "lack of declassified documentation"
            ],
            "upgrade_rules": {
                "what_to_stop_doing": [
                    "Stop relying on generic public domain montages without document telemetry",
                    "Avoid partisan political commentary"
                ],
                "what_to_double_down_on": [
                    "Declassified memo paradoxes with red line redaction reveals",
                    "First 30s institutional contradiction hooks"
                ],
                "next_video_upgrades": [
                    "Incorporate high-res document scanner overlays",
                    "Align archival photographs with audio typewriter sound hits"
                ]
            },
            "next_video_upgrades": [
                "Incorporate high-res document scanner overlays",
                "Align archival photographs with audio typewriter sound hits"
            ]
        },
        "seo_keyword_dna": {
            "primary_title_keyword": "Declassified US Intelligence Files",
            "primary_title_keyword_meaning_vi": "Hồ Sơ Giải Mật Tình Báo Hoa Kỳ",
            "keyword_placement_rule": "smart_seo_flexible",
            "secondary_anchor_keywords": [
                "Declassified Files",
                "Cold War Vault",
                "CIA Project",
                "National Archives"
            ],
            "mandatory_hashtags": [
                "#Declassified",
                "#ColdWarVault",
                "#CIAFiles",
                "#USHistory"
            ],
            "default_seo_tags": [
                "Declassified",
                "National Archives",
                "Cold War",
                "Project Azorian",
                "CIA",
                "Intelligence Vault"
            ]
        },
        "editing_dna_history": [],
        "thumbnail_dna": {
            "style_preset": "archival_intelligence",
            "visual_signature": "Declassified CIA Redaction & Aged Document Vault",
            "color_palette": {
                "primary": "#F8FAFC",
                "secondary": "#7F1D1D",
                "accent": "#DC2626",
                "background": "#1C1917"
            },
            "typography_preset": {
                "font_family": "Pretendard",
                "title_weight": "900",
                "stroke_color": "#000000",
                "stroke_width": 6
            },
            "layout_template": "evidence_spotlight",
            "reference_character_path": "",
            "mascot_lock": False,
            "version": 1
        },
        "thumbnail_dna_history": []
    },
    "channel-f6ec4dfff3": {
        "id": "channel-f6ec4dfff3",
        "channel_profile_id": "channel-f6ec4dfff3",
        "label": "The First Family Vault · Presidential Records & Executive Forensics",
        "market": "US",
        "default_language": "en",
        "language": "en",
        "default_duration_minutes": 30,
        "target_duration_minutes": 30,
        "default_visual_strategy": "hybrid",
        "visual_strategy": "hybrid",
        "default_ai_media_mode": "mixed",
        "ai_media_mode": "mixed",
        "default_ai_style_mode": "custom",
        "default_ai_custom_style": "American Presidential Vault Documentary",
        "dna_mode": "radar_hybrid",
        "voice_and_structure": "US Presidential Vault Documentary — Executive Power & Archival Records · 30 Minutes",
        "allowed_topics": "Presidential archives, White House historic decisions, executive orders, national security records.",
        "forbidden_topics": "Modern partisan election attacks, unverified hearsay, violent graphic imagery.",
        "monetization_safety_policy": "Third-person presidential history documentary — 100% Green Monetization.",
        "reference_image_policy": "Presidential photography & authentic footage paired with 2.5D archival document scans.",
        "default_creative_brief": {
            "market": "US",
            "language": "en",
            "target_duration_minutes": 30,
            "ai_media_mode": "mixed",
            "visual_strategy": "hybrid",
            "narrative_angle": "Presidential Vault Records & Executive Decision Forensics",
            "writing_style": "American Presidential History Documentary (30 Minutes)",
            "hook_archetype": "Presidential Order & Secret Clause Paradox",
            "editing_archetypes": [
                "Executive Order Scanner & Signature Zoom",
                "Oval Office Timeline Reconstruction",
                "Split-Screen Audio-Visual Match",
                "Chapter Card Cinematic Hit"
            ],
            "opening_hook": "Behind the public portraits and state dinners, the presidential archives hold executive orders signed in the dead of night that reshaped American history.",
            "notes": "Presidential archives and White House executive history documentary profile.",
            "custom_rules": "STRICT PRESIDENTIAL VAULT DNA (US - 30 MIN - PRESIDENTIAL ARCHIVES)"
        },
        "editing_dna": {
            "version": 1,
            "pacing": 5.0,
            "typical_pacing_sec": 5.0,
            "visual_mix": {"footage": 0.65, "ai": 0.2, "motion": 0.15},
            "editing_archetypes": [
                "executive_order_scanner",
                "timeline_hud",
                "cinematic_chapter_card",
                "oval_office_reconstruction"
            ],
            "subtitle_style": {
                "font_family": "Inter, sans-serif",
                "color": "#f8fafc",
                "highlight_color": "#f59e0b",
                "font_size": 40
            },
            "color_grade": "presidential_amber_kodachrome",
            "audio_rules": {
                "music_ducking_db": -18,
                "orchestral_swells": True,
                "sfx_hit_on_chapter": True
            }
        },
        "self_learning_memory": {
            "analyzed_videos_count": 82,
            "winners": [
                "Why Donald Trump's Parents Hated Him So Much",
                "Donald Trump’s Mother’s Marriage With Fred Trump Was CRUELER Than You Thought"
            ],
            "underperformers": [
                "general timeline recaps without private family letters"
            ],
            "winner_patterns": [
                "private family correspondence paradox",
                "cruel family dynamic contrast",
                "executive signature analysis"
            ],
            "losing_patterns": [
                "superficial chronological retelling",
                "lack of primary document evidence"
            ],
            "upgrade_rules": {
                "what_to_stop_doing": [
                    "Avoid superficial chronological storytelling without primary source exhibits"
                ],
                "what_to_double_down_on": [
                    "Focus on primary executive orders, private letters, and signature zooms"
                ],
                "next_video_upgrades": [
                    "Include presidential seal chapter title cards",
                    "Synchronize dramatic orchestral swells with critical archive reveals"
                ]
            },
            "next_video_upgrades": [
                "Include presidential seal chapter title cards",
                "Synchronize dramatic orchestral swells with critical archive reveals"
            ]
        },
        "seo_keyword_dna": {
            "primary_title_keyword": "Presidential Records & Executive Forensics",
            "primary_title_keyword_meaning_vi": "Hồ Sơ Tổng Thống & Mệnh Lệnh Mật",
            "keyword_placement_rule": "smart_seo_flexible",
            "secondary_anchor_keywords": [
                "Presidential Archives",
                "Executive Orders",
                "White House Tapes",
                "Secret History"
            ],
            "mandatory_hashtags": [
                "#PresidentialRecords",
                "#WhiteHouseVault",
                "#ExecutiveOrders",
                "#AmericanHistory"
            ],
            "default_seo_tags": [
                "Presidential Vault",
                "Executive Orders",
                "National Archives",
                "White House Tapes",
                "Secret Memos"
            ]
        },
        "editing_dna_history": [],
        "thumbnail_dna": {
            "style_preset": "presidential_vault",
            "visual_signature": "Executive Seal & High-Contrast Presidential Forensics",
            "color_palette": {
                "primary": "#FACC15",
                "secondary": "#1E3A8A",
                "accent": "#B91C1C",
                "background": "#0A0A0A"
            },
            "typography_preset": {
                "font_family": "Pretendard",
                "title_weight": "900",
                "stroke_color": "#000000",
                "stroke_width": 6
            },
            "layout_template": "bottom_cinematic",
            "reference_character_path": "",
            "mascot_lock": False,
            "version": 1
        },
        "thumbnail_dna_history": []
    }
}

# ==============================================================================
# CANONICAL JOBS BACKFILL DEFINITIONS
# ==============================================================================

JOBS_BACKFILL: dict[str, dict[str, Any]] = {
    "20261018-223750-3aecfbcd": {
        "channel_profile_id": "channel-1e24de3ab5",
        "visual_strategy": "hybrid",
        "default_creative_brief": {
            "market": "KR",
            "language": "ko",
            "target_duration_minutes": 22,
            "ai_media_mode": "image",
            "visual_strategy": "hybrid",
            "narrative_angle": "Điều tra Kỹ thuật Hạ tầng & Giải phẫu Điểm gãy Hệ thống (중국 초대형 인프라 설계 한계 & 지질 공학 분석)",
            "writing_style": "Phóng sự Điều tra Kỹ thuật Hàn Quốc Sắc Lạnh — Dẫn chứng Số liệu & Cơ chế Vật lý (판세의 이면 스타일 · 22 Phút)",
            "hook_archetype": "Con số Định lượng Cực hạn & Nghịch lý Vật lý Hiện trường (00:00–02:30)",
            "editing_archetypes": [
                "Bản đồ Địa hình 2.5D & Đường tuyến Vệ tinh",
                "HUD Số liệu Kỹ thuật & Đồ thị Độ lún",
                "Đối chiếu Bản vẽ Thiết kế vs. Hiện trường Thực tế",
                "Chapter Title Card Điện ảnh + Sound Hit"
            ],
            "opening_hook": "남쪽의 물을 북쪽으로 보내기 위해 산을 뚫고 강 위로 다리를 놓아 만든 1,432킬로미터의 인공 물길. 5,000억 위안이 투입된 중국 남수북조 중선 공정은 세기의 기적이라 불렸습니다. 하지만 수로가 지나는 허난성과 허베이성 일대에서 지반이 최대 수십 센티미터씩 내려앉고, 물이 닿기만 하면 부풀어 오르는 '팽창토'가 콘크리트 수로를 밀어 올리기 시작했습니다.",
            "notes": "Hồ sơ kênh Trung Quốc - Hàn Quốc (@판세의이면). Hạ tầng, đại công trình, đập thủy điện, cơ chế vật lý.",
            "custom_rules": "CHUẨN DNA KÊNH @판세의이면 (TRUNG QUỐC - HÀN QUỐC | 22 PHÚT | HYBRID FOOTAGE + AI)"
        }
    },
    "20261017-164519-fd65f7e1": {
        "channel_profile_id": "channel-e544a64b7c",
        "visual_strategy": "full_ai",
        "default_creative_brief": {
            "market": "KR",
            "language": "ko",
            "target_duration_minutes": 30,
            "ai_media_mode": "image",
            "visual_strategy": "full_ai",
            "narrative_angle": "Điều tra Hồ sơ Hình sự & Giải mã Tâm lý Tội phạm Nguy hiểm (형사 수사 기록 & 프로파일링 — Ngôi thứ 3)",
            "writing_style": "Phóng sự Điều tra Hình sự Hàn Quốc Sắc Lạnh (그것이 알고싶다 / 꼬꼬무 스타일 — 5 Hồi 30 Phút)",
            "hook_archetype": "Mỏ neo Nghịch lý Vỏ bọc Hai Mặt & Hiện trường Khóa kín (00:00–03:30)",
            "editing_archetypes": [
                "Hồ sơ điều tra & Sơ đồ mạng lưới",
                "Phóng to chi tiết & Quét tài liệu",
                "Chia đôi màn hình đối chiếu",
                "Bản đồ 2.5D & Camera vệ tinh"
            ],
            "opening_hook": "샤먼의 한 고급 쇼핑몰 시계 매장. 단정한 옷차림에 온화한 미소, 유창한 화술로 고객들에게 '가장 친절한 매니저'로 불리던 한 여성. 20년 동안 단 한 번도 신분증을 쓰지 않고 유령처럼 살아온 그녀의 진짜 이름은 라오룽즈(劳荣枝). 중국 전역을 공포에 떨게 했던 최악의 1급 수배범이었습니다.",
            "notes": "Vụ án Lao Rongzhi 20 năm lẩn trốn. 100% Green Monetization.",
            "custom_rules": "CHUẨN DNA KÊNH ĐỘC QUYỀN (KR - 30 PHÚT - 100% FULL AI)"
        }
    },
    "20261017-003022-ecb75736": {
        "channel_profile_id": "channel-e544a64b7c",
        "visual_strategy": "full_ai",
        "default_creative_brief": {
            "market": "KR",
            "language": "ko",
            "target_duration_minutes": 30,
            "ai_media_mode": "image",
            "visual_strategy": "full_ai",
            "narrative_angle": "Điều tra Hồ sơ Hình sự & Đấu trí Pháp y Tài chính (Forensic Investigative True Crime - 그것이 알고싶다 스타일)",
            "writing_style": "Phóng sự điều tra hồ sơ vụ án Hàn Quốc sắc lạnh, cuốn hút (Cold Investigative Case File)",
            "hook_archetype": "Cuộc gọi định mệnh & Con số nghịch lý 4.400 tỷ won (The Fatal Phone Call + Shocking Financial Paradox)",
            "editing_archetypes": [
                "Bàn hồ sơ điều tra & Sơ đồ mạng lưới nghi phạm (Forensic Case Board & Evidence Map)",
                "HUD Telemetry dòng tiền mật",
                "biên bản cáo trạng & mốc thời gian phá án",
                "Đối chiếu vỏ bọc 'quan thanh liêm' trên truyền thông vs. Khối tài sản ngầm 4.400 tỷ won (Split-Screen Contrast)",
                "Chapter Title Card điện ảnh + Sound Hit mỗi chương"
            ],
            "opening_hook": "낡은 자전거를 타고 출근하며 30년 동안 단 한 번도 부패 혐의를 받지 않았던 중국의 모범 공무원. 심지어 그를 고발했던 사람들마저 차례로 사라지거나 침묵했고, 그는 오히려 초고속 승진을 거듭했습니다. 하지만 4,400억 원이라는 천문학적 비자금 제국은, 한 탐사보도 기자가 걸어온 단 한 통의 전화와 아주 사소한 영수증 한 장에서 무너지기 시작했습니다.",
            "notes": "Đại án 4.400 tỷ quan thanh liêm. Forensic finance and psychological interrogation.",
            "custom_rules": "QUY TẮC AN TOÀN CHÍNH SÁCH YOUTUBE CHO TRUE CRIME (100% GREEN MONETIZATION)"
        }
    },
    "20261015-014818-f0fdc122": {
        "channel_profile_id": "channel-1e24de3ab5",
        "visual_strategy": "hybrid",
        "default_creative_brief": {
            "market": "KR",
            "language": "ko",
            "target_duration_minutes": 20,
            "ai_media_mode": "image",
            "visual_strategy": "hybrid",
            "narrative_angle": "Áp lực 39,3 tỷ tấn nước lên đới đứt gãy Tam Hiệp: Giới hạn thiết kế bê tông trọng lực và bài học cảnh báo từ thảm họa đập Bản Kiều 1975",
            "writing_style": "Phóng sự tài liệu điều tra kỹ thuật chuyên sâu (판세의 이면 스타일 · 20 Phút)",
            "hook_archetype": "Nghịch lý Bồi lắng Sa bồi & Thân đập 39.3 tỷ tấn nước (00:00–02:30)",
            "editing_archetypes": [
                "Bản đồ Địa hình 2.5D & Radar Vệ tinh InSAR",
                "HUD Thông số Kỹ thuật Thân đập",
                "Đối chiếu Bản vẽ vs. Hiện trường",
                "Chapter Title Card Điện ảnh"
            ],
            "opening_hook": "393억 톤의 괴물.. 만약 중국 싼샤댐이 무너지면 어떤 일이 벌어질까? 싼샤댐의 콘크리트 중력 댐 구조와 퇴적 토사 18억 톤의 압력을 과학적으로 분석합니다.",
            "notes": "Đập Tam Hiệp 393 tỷ tấn nước. Phân tích kết cấu kỹ thuật và bồi lắng sa bồi.",
            "custom_rules": "CHUẨN DNA KÊNH @판세의이면 (TRUNG QUỐC - HÀN QUỐC | 20 PHÚT | HYBRID FOOTAGE + AI)"
        }
    }
}


def backup_data() -> tuple[Path, Path]:
    """Perform non-destructive backup of profiles and jobs."""
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Backup channel_profiles.json
    profile_backup_file = BACKUPS_DIR / f"channel_profiles_{stamp}.json"
    if PROFILES_FILE.exists():
        shutil.copy2(PROFILES_FILE, profile_backup_file)
        # Also maintain a latest pointer
        shutil.copy2(PROFILES_FILE, BACKUPS_DIR / "channel_profiles_backup.json")
        print(f"[BACKUP] Backed up channel profiles to {profile_backup_file}")
    else:
        print(f"[BACKUP WARN] {PROFILES_FILE} does not exist, skipping profile backup.")

    # Backup jobs/
    jobs_backup_dir = BACKUPS_DIR / f"jobs_{stamp}"
    if JOBS_DIR.exists():
        shutil.copytree(JOBS_DIR, jobs_backup_dir, dirs_exist_ok=True)
        # Also maintain a latest pointer
        latest_jobs_backup = BACKUPS_DIR / "jobs_backup"
        if latest_jobs_backup.exists():
            shutil.rmtree(latest_jobs_backup)
        shutil.copytree(JOBS_DIR, latest_jobs_backup, dirs_exist_ok=True)
        print(f"[BACKUP] Backed up jobs directory to {jobs_backup_dir}")
    else:
        print(f"[BACKUP WARN] {JOBS_DIR} does not exist, skipping jobs backup.")

    return profile_backup_file, jobs_backup_dir


def backfill_channel_profiles() -> dict[str, Any]:
    """Repair and backfill existing Channel Profiles."""
    if not PROFILES_FILE.exists():
        raise FileNotFoundError(f"Missing {PROFILES_FILE}")

    content = json.loads(PROFILES_FILE.read_text(encoding="utf-8"))
    profiles_list = content.get("profiles", [])
    profiles_by_id = {item.get("id"): item for item in profiles_list if isinstance(item, dict) and item.get("id")}

    updated_profiles = []
    # Process existing and ensure canonical profiles exist
    all_keys = list(profiles_by_id.keys())
    for target_id in PROFILES_BACKFILL.keys():
        if target_id not in all_keys:
            all_keys.append(target_id)

    for profile_id in all_keys:
        existing = profiles_by_id.get(profile_id, {})
        canonical = PROFILES_BACKFILL.get(profile_id, {})

        merged = dict(existing)
        # Apply canonical fields
        for key, value in canonical.items():
            if key == "default_creative_brief" and isinstance(value, dict):
                merged_brief = dict(existing.get("default_creative_brief") or {})
                merged_brief.update(value)
                merged["default_creative_brief"] = merged_brief
            elif key == "editing_dna" and isinstance(value, dict):
                merged_dna = dict(existing.get("editing_dna") or {})
                merged_dna.update(value)
                merged["editing_dna"] = merged_dna
            elif key == "self_learning_memory" and isinstance(value, dict):
                merged_mem = dict(existing.get("self_learning_memory") or {})
                merged_mem.update(value)
                merged["self_learning_memory"] = merged_mem
            elif key == "seo_keyword_dna" and isinstance(value, dict):
                merged_seo = dict(existing.get("seo_keyword_dna") or {})
                merged_seo.update(value)
                merged["seo_keyword_dna"] = merged_seo
            else:
                merged[key] = value

        # Ensure top-level required fields
        merged["id"] = profile_id
        merged["channel_profile_id"] = profile_id
        merged["visual_strategy"] = merged.get("visual_strategy") or merged.get("default_visual_strategy") or "hybrid"
        merged["default_visual_strategy"] = merged["visual_strategy"]
        merged["default_language"] = merged.get("default_language") or merged.get("language") or "ko"
        merged["language"] = merged["default_language"]
        merged["default_duration_minutes"] = merged.get("default_duration_minutes") or merged.get("target_duration_minutes") or 30
        merged["target_duration_minutes"] = merged["default_duration_minutes"]
        merged["default_ai_media_mode"] = merged.get("default_ai_media_mode") or merged.get("ai_media_mode") or "image"
        merged["ai_media_mode"] = merged["default_ai_media_mode"]

        # Ensure default_creative_brief has all 10 non-null keys
        brief = dict(merged.get("default_creative_brief") or {})
        brief.setdefault("market", merged.get("market") or "KR")
        brief.setdefault("language", merged.get("default_language") or "ko")
        brief.setdefault("target_duration_minutes", merged.get("default_duration_minutes") or 30)
        brief.setdefault("ai_media_mode", merged.get("default_ai_media_mode") or "image")
        brief.setdefault("visual_strategy", merged.get("visual_strategy") or "hybrid")
        brief.setdefault("narrative_angle", merged.get("voice_and_structure") or "Investigation")
        brief.setdefault("writing_style", merged.get("voice_and_structure") or "Investigative documentary")
        brief.setdefault("hook_archetype", "High curiosity opening paradox")
        brief.setdefault("editing_archetypes", ["2.5D maps", "document telemetry", "chapter title cards"])
        brief.setdefault("opening_hook", "High impact opening hook line.")
        brief.setdefault("notes", merged.get("label") or "Channel profile notes.")
        merged["default_creative_brief"] = brief

        # Ensure editing_dna complete schema
        dna = dict(merged.get("editing_dna") or {})
        dna.setdefault("version", 1)
        dna.setdefault("pacing", 5.0)
        dna.setdefault("typical_pacing_sec", dna.get("pacing", 5.0))
        dna.setdefault("visual_mix", {"footage": 0.5, "ai": 0.35, "motion": 0.15})
        dna.setdefault("editing_archetypes", ["2.5d_map", "hud_telemetry", "chapter_title_card"])
        dna.setdefault("subtitle_style", {
            "font_family": "Pretendard, sans-serif",
            "color": "#ffffff",
            "highlight_color": "#38bdf8",
            "font_size": 42
        })
        dna.setdefault("color_grade", "technical_cool_cyan")
        dna.setdefault("audio_rules", {"music_ducking_db": -18, "sfx_hit_on_chapter": True})
        merged["editing_dna"] = dna

        # Ensure self_learning_memory initialized structure
        slm = dict(merged.get("self_learning_memory") or {})
        slm.setdefault("analyzed_videos_count", 0)
        slm.setdefault("winners", [])
        slm.setdefault("underperformers", [])
        slm.setdefault("winner_patterns", [])
        slm.setdefault("losing_patterns", [])
        slm.setdefault("upgrade_rules", {
            "what_to_stop_doing": [],
            "what_to_double_down_on": [],
            "next_video_upgrades": []
        })
        slm.setdefault("next_video_upgrades", [])
        merged["self_learning_memory"] = slm

        # Ensure seo_keyword_dna complete schema
        seo = dict(merged.get("seo_keyword_dna") or {})
        seo.setdefault("primary_title_keyword", "")
        seo.setdefault("primary_title_keyword_meaning_vi", "")
        seo.setdefault("keyword_placement_rule", "smart_seo_flexible")
        seo.setdefault("secondary_anchor_keywords", [])
        seo.setdefault("mandatory_hashtags", [])
        seo.setdefault("default_seo_tags", [])
        merged["seo_keyword_dna"] = seo

        # Ensure editing_dna_history is list
        if not isinstance(merged.get("editing_dna_history"), list):
            merged["editing_dna_history"] = []

        # Ensure thumbnail_dna complete schema
        tdna = dict(merged.get("thumbnail_dna") or {})
        tdna.setdefault("style_preset", "cold_forensic_noir")
        tdna.setdefault("visual_signature", "")
        tdna.setdefault("color_palette", {"primary": "#FFE84A", "secondary": "#0F172A", "accent": "#EF4444", "background": "#020617"})
        tdna.setdefault("typography_preset", {"font_family": "Pretendard", "title_weight": "900", "stroke_color": "#000000", "stroke_width": 6})
        tdna.setdefault("layout_template", "broadcast_left_heavy")
        tdna.setdefault("reference_character_path", "")
        tdna.setdefault("mascot_lock", False)
        tdna.setdefault("version", 1)
        merged["thumbnail_dna"] = tdna

        # Ensure thumbnail_dna_history is list
        if not isinstance(merged.get("thumbnail_dna_history"), list):
            merged["thumbnail_dna_history"] = []

        updated_profiles.append(merged)

    # Sort updated profiles consistently
    updated_profiles.sort(key=lambda p: str(p.get("updated_at") or p.get("created_at") or ""), reverse=True)

    result_payload = {"profiles": updated_profiles}

    # Atomic write to PROFILES_FILE
    tmp_path = PROFILES_FILE.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(result_payload, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp_path, PROFILES_FILE)
    print(f"[MIGRATION] Backfilled {len(updated_profiles)} channel profiles in {PROFILES_FILE}")
    return result_payload


def backfill_jobs(profiles_payload: dict[str, Any]) -> list[str]:
    """Repair and backfill existing jobs in data/jobs/."""
    profiles = {p["id"]: p for p in profiles_payload.get("profiles", [])}
    migrated_job_ids = []

    for job_dir in JOBS_DIR.iterdir():
        if not job_dir.is_dir():
            continue
        job_file = job_dir / "job.json"
        if not job_file.exists():
            continue

        job_id = job_dir.name
        job = json.loads(job_file.read_text(encoding="utf-8"))

        canonical = JOBS_BACKFILL.get(job_id, {})
        target_profile_id = canonical.get("channel_profile_id") or job.get("channel_profile_id")

        # Infer from notes/workspace if needed
        if not target_profile_id:
            notes = str(job.get("notes") or "")
            title = str(job.get("title") or "")
            if "판세의이면" in notes or "중국 - Hàn Quốc" in notes or "남수북조" in title or "싼샤댐" in title:
                target_profile_id = "channel-1e24de3ab5"
            elif "Lao Rongzhi" in notes or "True Crime" in notes or "라오룽즈" in title or "4,400" in title:
                target_profile_id = "channel-e544a64b7c"
            else:
                target_profile_id = "channel-1e24de3ab5"

        parent_profile = profiles.get(target_profile_id, {})

        # Set non-null channel_profile_id
        job["channel_profile_id"] = target_profile_id

        # Set non-null visual_strategy
        job["visual_strategy"] = (
            canonical.get("visual_strategy")
            or job.get("visual_strategy")
            or (job.get("production_recipe") or {}).get("visual_strategy")
            or parent_profile.get("visual_strategy")
            or "hybrid"
        )
        if isinstance(job.get("production_recipe"), dict):
            job["production_recipe"]["visual_strategy"] = job["visual_strategy"]

        # Set non-null default_creative_brief & creative_brief
        brief = copy.deepcopy(
            canonical.get("default_creative_brief")
            or job.get("default_creative_brief")
            or job.get("creative_brief")
            or parent_profile.get("default_creative_brief")
            or {}
        )
        # Try loading from workspace creative_brief.json if brief is incomplete
        workspace_brief_file = WORKSPACES_DIR / job_id / "creative_brief.json"
        if workspace_brief_file.exists():
            try:
                ws_brief = json.loads(workspace_brief_file.read_text(encoding="utf-8"))
                for k, v in ws_brief.items():
                    if v is not None and not brief.get(k):
                        brief[k] = v
            except Exception:
                pass

        # Ensure all 10 required brief fields
        brief.setdefault("market", job.get("market") or parent_profile.get("market") or "KR")
        brief.setdefault("language", job.get("language") or parent_profile.get("default_language") or "ko")
        brief.setdefault("target_duration_minutes", (job.get("production_recipe") or {}).get("target_duration_sec", 1200) / 60)
        brief.setdefault("ai_media_mode", job.get("ai_media_mode") or parent_profile.get("default_ai_media_mode") or "image")
        brief.setdefault("visual_strategy", job["visual_strategy"])
        brief.setdefault("narrative_angle", parent_profile.get("voice_and_structure") or "Investigative documentary")
        brief.setdefault("writing_style", parent_profile.get("voice_and_structure") or "Cold investigative style")
        brief.setdefault("hook_archetype", "Paradoxical opening hook")
        brief.setdefault("editing_archetypes", ["2.5D Map", "HUD Telemetry", "Chapter Title Card"])
        brief.setdefault("opening_hook", job.get("title") or "High impact opening hook line.")
        brief.setdefault("notes", job.get("notes") or "Job production notes.")
        brief.setdefault("custom_rules", parent_profile.get("custom_rules") or "Standard DNA compliance")

        job["default_creative_brief"] = brief
        job["creative_brief"] = brief

        # Set non-null editing_dna
        editing_dna = copy.deepcopy(parent_profile.get("editing_dna") or {
            "version": 1,
            "pacing": 5.0,
            "typical_pacing_sec": 5.0,
            "visual_mix": {"footage": 0.5, "ai": 0.35, "motion": 0.15},
            "editing_archetypes": ["2.5d_map", "hud_telemetry", "chapter_title_card"],
            "subtitle_style": {
                "font_family": "Pretendard, sans-serif",
                "color": "#ffffff",
                "highlight_color": "#38bdf8",
                "font_size": 42
            },
            "color_grade": "technical_cool_cyan",
            "audio_rules": {"music_ducking_db": -18, "sfx_hit_on_chapter": True}
        })
        job["editing_dna"] = editing_dna

        # Set complete seo_keyword_dna
        seo_keyword_dna = copy.deepcopy(parent_profile.get("seo_keyword_dna") or {})
        job["seo_keyword_dna"] = seo_keyword_dna

        # Set complete thumbnail_dna
        thumbnail_dna = copy.deepcopy(parent_profile.get("thumbnail_dna") or {})
        job["thumbnail_dna"] = thumbnail_dna

        # Set complete channel_profile_snapshot
        snapshot = {
            "id": target_profile_id,
            "channel_profile_id": target_profile_id,
            "label": parent_profile.get("label") or target_profile_id,
            "market": parent_profile.get("market") or "KR",
            "language": parent_profile.get("default_language") or "ko",
            "visual_strategy": job["visual_strategy"],
            "default_creative_brief": brief,
            "editing_dna": editing_dna,
            "seo_keyword_dna": seo_keyword_dna,
            "thumbnail_dna": thumbnail_dna,
            "editorial_dna": parent_profile.get("editorial_dna") or {},
        }
        job["channel_profile_snapshot"] = snapshot

        # Atomic write back to job.json
        tmp_job = job_file.with_suffix(".tmp")
        tmp_job.write_text(json.dumps(job, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp_job, job_file)
        migrated_job_ids.append(job_id)
        print(f"[MIGRATION] Backfilled job {job_id} -> profile {target_profile_id}, visual_strategy={job['visual_strategy']}")

    return migrated_job_ids


def validate_migration() -> bool:
    """Validate that all 4 profiles and all jobs pass strict non-null and completeness checks."""
    errors: list[str] = []

    # 1. Validate Channel Profiles
    if not PROFILES_FILE.exists():
        errors.append(f"Missing {PROFILES_FILE}")
    else:
        data = json.loads(PROFILES_FILE.read_text(encoding="utf-8"))
        profiles = {p["id"]: p for p in data.get("profiles", [])}

        required_profile_ids = ["channel-1e24de3ab5", "channel-e544a64b7c", "channel-aa913eb90d", "channel-f6ec4dfff3"]
        for pid in required_profile_ids:
            if pid not in profiles:
                errors.append(f"Required profile {pid} not found in channel_profiles.json")
                continue
            p = profiles[pid]

            # Top-level checks
            for field in ["id", "channel_profile_id", "visual_strategy", "default_visual_strategy", "default_creative_brief", "editing_dna", "self_learning_memory"]:
                val = p.get(field)
                if val is None:
                    errors.append(f"Profile {pid} has null/missing field: {field}")

            # Brief checks
            brief = p.get("default_creative_brief") or {}
            required_brief_keys = [
                "market", "language", "target_duration_minutes", "ai_media_mode",
                "narrative_angle", "writing_style", "hook_archetype", "editing_archetypes",
                "opening_hook", "notes"
            ]
            for bk in required_brief_keys:
                if brief.get(bk) is None:
                    errors.append(f"Profile {pid} default_creative_brief has null/missing key: {bk}")

            # Editing DNA checks
            dna = p.get("editing_dna") or {}
            required_dna_keys = ["pacing", "visual_mix", "editing_archetypes", "subtitle_style", "color_grade", "audio_rules"]
            for dk in required_dna_keys:
                if dna.get(dk) is None:
                    errors.append(f"Profile {pid} editing_dna has null/missing key: {dk}")

            # Self learning memory checks
            slm = p.get("self_learning_memory") or {}
            for sk in ["winners", "underperformers", "upgrade_rules"]:
                if slm.get(sk) is None:
                    errors.append(f"Profile {pid} self_learning_memory has null/missing key: {sk}")

            # SEO Keyword DNA checks
            seo = p.get("seo_keyword_dna") or {}
            if not isinstance(seo, dict) or not seo.get("primary_title_keyword"):
                errors.append(f"Profile {pid} seo_keyword_dna is empty or missing primary_title_keyword")
            for seok in ["primary_title_keyword", "primary_title_keyword_meaning_vi", "keyword_placement_rule", "secondary_anchor_keywords", "mandatory_hashtags", "default_seo_tags"]:
                if seok not in seo:
                    errors.append(f"Profile {pid} seo_keyword_dna missing key: {seok}")

            # History is a list
            if not isinstance(p.get("editing_dna_history"), list):
                errors.append(f"Profile {pid} editing_dna_history is not a list")

            # Thumbnail DNA checks
            tdna = p.get("thumbnail_dna") or {}
            if not isinstance(tdna, dict) or not tdna.get("style_preset"):
                errors.append(f"Profile {pid} thumbnail_dna is empty or missing style_preset")
            for tdk in ["style_preset", "visual_signature", "color_palette", "typography_preset", "layout_template", "version"]:
                if tdk not in tdna:
                    errors.append(f"Profile {pid} thumbnail_dna missing key: {tdk}")

            if not isinstance(p.get("thumbnail_dna_history"), list):
                errors.append(f"Profile {pid} thumbnail_dna_history is not a list")

    # 2. Validate Jobs
    if not JOBS_DIR.exists():
        errors.append(f"Missing {JOBS_DIR}")
    else:
        required_job_ids = ["20261018-223750-3aecfbcd", "20261017-164519-fd65f7e1", "20261017-003022-ecb75736", "20261015-014818-f0fdc122"]
        for jid in required_job_ids:
            jfile = JOBS_DIR / jid / "job.json"
            if not jfile.exists():
                errors.append(f"Job file {jfile} does not exist")
                continue
            job = json.loads(jfile.read_text(encoding="utf-8"))

            for jf in ["channel_profile_id", "visual_strategy", "default_creative_brief", "editing_dna", "thumbnail_dna"]:
                val = job.get(jf)
                if val is None:
                    errors.append(f"Job {jid} has null/missing field: {jf}")

            if not isinstance(job.get("default_creative_brief"), dict) or not job["default_creative_brief"]:
                errors.append(f"Job {jid} default_creative_brief is empty or not a dict")

            if not isinstance(job.get("editing_dna"), dict) or not job["editing_dna"]:
                errors.append(f"Job {jid} editing_dna is empty or not a dict")

    if errors:
        print("[VALIDATION FAILED] The following errors were found:")
        for err in errors:
            print(f"  - {err}")
        return False

    print("[VALIDATION PASSED] All 4 channel profiles and all 4 jobs verified with non-null complete schemas.")
    return True


def run_migration() -> bool:
    """Execute full migration pipeline."""
    print("=" * 60)
    print("Starting CofiDocumentary Milestone 1 Backfill Migration")
    print("=" * 60)

    # 1. Non-destructive backup
    backup_data()

    # 2. Backfill Channel Profiles
    profiles_payload = backfill_channel_profiles()

    # 3. Backfill Jobs
    backfill_jobs(profiles_payload)

    # 4. Strict Validation
    success = validate_migration()
    print("=" * 60)
    if success:
        print("MIGRATION COMPLETED SUCCESSFULLY.")
    else:
        print("MIGRATION ENCOUNTERED VALIDATION FAILURES.")
    print("=" * 60)
    return success


if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
