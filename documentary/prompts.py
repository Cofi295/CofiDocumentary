from __future__ import annotations

import hashlib
import json
import re
from math import ceil, floor
from pathlib import Path
from typing import Any
from .nexus_coordinator import NexusCoordinator
from .trail_manager import TrailCodeManager


CREATIVE_STUDIO_CATALOG: dict[str, dict[str, dict[str, str]]] = {
    "narrative_angles": {
        "forensic_investigative": {
            "id": "forensic_investigative",
            "label": "Điều tra Hồ sơ Mật & Pháp y",
            "directive": (
                "Khai thác theo trình tự mở khóa từng lớp hồ sơ mật, chứng cứ pháp y, mâu thuẫn lời khai và bí mật bị che giấu. "
                "Giữ nhịp căng thẳng của một cuộc điều tra truy tìm sự thật đến phút cuối."
            ),
        },
        "geopolitics_power": {
            "id": "geopolitics_power",
            "label": "Địa chính trị & Bàn cờ Quyền lực",
            "directive": (
                "Khai thác dưới góc độ lợi ích quốc gia, đòn bẩy kinh tế - quân sự, toan tính chiến lược giữa các cường quốc "
                "và những thoả thuận ngầm đằng sau hậu trường."
            ),
        },
        "engineering_explainer": {
            "id": "engineering_explainer",
            "label": "Giải phẫu Kỹ thuật & Hệ thống (Vox / Wendover)",
            "directive": (
                "Giải phẫu cơ chế vận hành, thông số vật lý/địa chất, điểm gãy kỹ thuật (single point of failure) "
                "và quy mô công trình qua lăng kính kỹ sư và hệ thống."
            ),
        },
        "human_tragedy": {
            "id": "human_tragedy",
            "label": "Bi kịch Con người & Kẻ phản biện đơn độc",
            "directive": (
                "Đặt trọng tâm vào số phận con người, người cảnh báo bị phớt lờ (whistleblower), sự kiêu ngạo của quyền lực "
                "và cái giá phải trả bằng sinh mạng hoặc bi kịch cá nhân."
            ),
        },
        "follow_the_money": {
            "id": "follow_the_money",
            "label": "Theo dấu Dòng tiền & Đế chế Ngầm",
            "directive": (
                "Lần theo dòng chảy tài chính, bong bóng đầu cơ, hợp đồng ngầm, cấu trúc lợi ích nhóm "
                "và ai thực sự hưởng lợi khi khủng hoảng hoặc sự kiện xảy ra."
            ),
        },
        "goodnight_dignity_reversal_drama": {
            "id": "goodnight_dignity_reversal_drama",
            "label": "K-Audio Drama Đêm Khuya: Phẩm Giá Gia Đình & Cú Lật Kép Bậc Thầy (6 Chương)",
            "directive": (
                "Kịch truyền thanh văn học 6 Chương (60–82 phút): mở màn In-Media-Res khi phẩm giá người trưởng thành (55–68 tuổi) "
                "bị xem nhẹ trong gia đình/xưởng nghề, gieo tri thức nghề thủ công/nghệ thuật chân thực và thực hiện 2 tầng lật mở đĩnh đạc "
                "(0% trả thù bẩn, 0% kêu gọi đăng ký kênh, kết êm đưa thính giả vào giấc ngủ ngon)."
            ),
        },
    },
    "writing_styles": {
        "warm_literary_radio_drama": {
            "id": "warm_literary_radio_drama",
            "label": "Văn Nói Kịch Truyền Thanh Đêm Khuya Ấm Áp & Đĩnh Đạc (FM Velvet)",
            "directive": (
                "Giọng văn nói tiếng Hàn ấm áp, điềm đạm, giàu chi tiết xúc giác và âm thanh đời thường; đặt tên người nói trước câu thoại (화자 선행), "
                "nhịp thở thư thái có khoảng lặng tự nhiên, 0% sướt mướt cường điệu hay văn dịch máy AI."
            ),
        },
        "cold_analytical": {
            "id": "cold_analytical",
            "label": "Lạnh lùng, Sắc sảo & Đối lập Số liệu",
            "directive": (
                "Giọng văn đanh thép, tiết chế tính từ sáo rỗng; dùng con số cụ thể, ngày giờ, biên bản "
                "và sự tương phản dữ liệu lạnh lùng để tạo sức nặng."
            ),
        },
        "cinematic_thriller": {
            "id": "cinematic_thriller",
            "label": "Kịch tính Điện ảnh (Netflix / MagnatesMedia)",
            "directive": (
                "Dựng cảnh giàu hình ảnh điện ảnh, câu văn ngắn gọn giàu nhịp điệu, gieo cliffhanger ở cuối mỗi chương "
                "và đẩy cao trào cảm xúc như phim thriller."
            ),
        },
        "investigative_chronicle": {
            "id": "investigative_chronicle",
            "label": "Phóng sự Điều tra Biên niên sử",
            "directive": (
                "Theo sát dòng thời gian biên niên sử kết hợp lật mở hồ sơ báo chí điều tra; khách quan, chặt chẽ, dẫn chứng rõ nguồn."
            ),
        },
        "poetic_essay": {
            "id": "poetic_essay",
            "label": "Tự sự Trầm lắng & Giàu Ẩn dụ",
            "directive": (
                "Giọng kể sâu lắng, chiêm nghiệm, sử dụng hình ảnh ẩn dụ và chiều sâu tâm lý/lịch sử để chạm tới cảm xúc người xem."
            ),
        },
        "satirical_critical": {
            "id": "satirical_critical",
            "label": "Phản biện Sắc bén & Đối chiếu Hiện thực",
            "directive": (
                "Bóc tách sự phi lý giữa lời hứa hào nhoáng của truyền thông/quyền lực và thực tế phũ phàng bằng giọng điệu sắc sảo, thông minh."
            ),
        },
    },
    "hook_archetypes": {
        "micro_forensic_anomaly": {
            "id": "micro_forensic_anomaly",
            "label": "Dị Điểm Vật Chứng Vi Mô (Micro-Clue Zoom-Out)",
            "directive": (
                "Mở thẳng dưới ống kính cận cảnh vào một vật thể nhỏ bé bất thường (vết hằn dây cót, 0,3mm sợi vải, phong bì báo cũ cắt khít tờ hối phiếu, con dấu khắc lậu) mà KHÔNG mào đầu ngày tháng/địa danh, đặt ngay câu hỏi làm sao chi tiết vi mô ấy đánh sập cả kế hoạch 20 năm."
            ),
        },
        "double_life_unmasking": {
            "id": "double_life_unmasking",
            "label": "Khoảnh Khắc Vỡ Vụn Vỏ Bọc Hai Mặt (Unmasking Freeze-Frame)",
            "directive": (
                "Mở trực diện bên trong cuộc sống hào nhoáng hoặc bình dị hiện tại của nhân vật (trụ trì cổ tự, thí sinh truyền hình, chủ tịch tập đoàn, đầu bếp quán nhỏ) đúng giây phút một câu gọi tên quê hương hay ánh mắt trinh sát làm chiếc mặt nạ rơi xuống."
            ),
        },
        "chilling_verbatim_line": {
            "id": "chilling_verbatim_line",
            "label": "Một Câu Nói / Bút Tích Nghịch Lý (Verbatim Line Hook)",
            "directive": (
                "Mở bằng một câu nói có thật trong biên bản thẩm vấn, bức thư để lại trên bàn hoặc thông báo tự thú nghịch lý (nêu rõ người nói trước lời trích dẫn cho TTS), kéo khán giả tự hỏi vì sao nhân vật lại thốt ra câu đó."
            ),
        },
        "countdown_system_breach": {
            "id": "countdown_system_breach",
            "label": "Đếm Ngược Giờ G & Báo Động Hệ Thống (Tick-Tock Breach)",
            "directive": (
                "Đặt người xem ngay vào nhịp đồng hồ đếm ngược (8 phút trước giờ đóng sàn, đêm nối mạng sổ cái toàn quốc, 48 giờ cuối tuần khép kiểm toán, giờ thứ 71 của cuộc truy lùng) khi mỗi giây trôi qua làm đảo lộn toàn bộ cục diện."
            ),
        },
        "locked_room_vault_paradox": {
            "id": "locked_room_vault_paradox",
            "label": "Nghịch Lý Két Sắt / Hiện Trường Khóa Kín Không Vết Xước",
            "directive": (
                "Đặt cạnh nhau hai dữ kiện vật lý mâu thuẫn tuyệt đối (ổ khóa hai chìa nguyên vẹn nhưng kho bạc trống rỗng; sổ tiết kiệm nằm trong tay chủ nhân nhưng số dư về 1 đồng; cửa khóa trong không dấu cạy mở) để kích hoạt trí tò mò giải đố ngay 15 giây đầu."
            ),
        },
        "last_ordinary_routine": {
            "id": "last_ordinary_routine",
            "label": "Chi Tiết Đời Thường Cuối Cùng Bỏ Dở (Intimate Routine Hook)",
            "directive": (
                "Bắt đầu tĩnh lặng từ một khoảnh khắc đời thường rất thật (tờ lịch xé dở, buổi bàn giao ca sáng, bát mì còn ấm, chuyến xe quen thuộc) trước khi một sự vắng mặt kỳ lạ kéo người xem trượt sâu vào bí ẩn."
            ),
        },
        "scale_absurdity_collision": {
            "id": "scale_absurdity_collision",
            "label": "Va Chạm Giữa Con Số Khổng Lồ & Lý Do Trớ Trêu",
            "directive": (
                "Đập thẳng sự đối lập gây choáng váng giữa quy mô tiền bạc/lực lượng khổng lồ với đích đến đời thường không ai ngờ tới (51 triệu tệ kho bạc chảy sạch vào quầy vé số đầu ngõ; kẻ cuỗm hàng trăm tỷ lộ diện vì dáng bước cầu thang)."
            ),
        },
        "cold_archive_match": {
            "id": "cold_archive_match",
            "label": "Túi Vật Chứng Ngủ Yên 20 Năm Bỗng Báo Khớp",
            "directive": (
                "Mở từ kho lưu trữ hồ sơ lạnh lẽo khi một mẫu vật niêm phong từ nhiều thập kỷ trước bất ngờ trùng khớp trên hệ thống dữ liệu hiện đại, chỉ thẳng tới một cái tên không ai ngờ đang sống ngay giữa đời thường."
            ),
        },
        "shocking_paradox": {
            "id": "shocking_paradox",
            "label": "Nghịch lý & Con số Gây sốc (0–30s)",
            "directive": (
                "Mở màn ngay bằng một con số khổng lồ hoặc nghịch lý không tưởng đặt cạnh một chi tiết đời thường gây choáng váng trong 15 giây đầu."
            ),
        },
        "in_media_res": {
            "id": "in_media_res",
            "label": "Khoảnh khắc Định mệnh (In Media Res)",
            "directive": (
                "Đưa người xem thẳng vào thời khắc căng thẳng nhất (giây phút sự cố xảy ra, cuộc gọi khẩn cấp, khoảnh khắc ký lệnh) rồi mới quay ngược giải thích tại sao."
            ),
        },
        "myth_vs_truth": {
            "id": "myth_vs_truth",
            "label": "Lời đồn Đại chúng vs. Sự thật Hồ sơ",
            "directive": (
                "Mở đầu bằng niềm tin phổ biến mà số đông lầm tưởng, sau đó đập tan ngay bằng một bằng chứng hoặc tài liệu gốc chứng minh điều ngược lại."
            ),
        },
        "forgotten_witness": {
            "id": "forgotten_witness",
            "label": "Lời Tiên tri / Nhân chứng Bị Phớt lờ",
            "directive": (
                "Bắt đầu bằng lời cảnh báo chính xác đến rợn người của một chuyên gia hoặc nhân chứng nhiều năm trước nhưng đã bị phớt lờ."
            ),
        },
        "in_media_res_dignity_insult": {
            "id": "in_media_res_dignity_insult",
            "label": "Khoảnh Khắc Xem Thường Phẩm Giá Giữa Đời Thường (In-Media-Res Dignity Hook)",
            "directive": (
                "Mở thẳng ngay giây đầu vào cảnh sinh hoạt gia đình hoặc xưởng nghề cụ thể khi nhân vật chính nhận lời miệt thị/tối hậu thư vô tâm, "
                "song song hé lộ 1 chi tiết đạo cụ tay nghề bậc thầy mà những người xung quanh không hề nhận ra (0% chào hỏi kênh)."
            ),
        },
    },
    "editing_archetypes": {
        "warm_cinema_character_sheet": {
            "id": "warm_cinema_character_sheet",
            "label": "Điện Ảnh 35mm Đêm Khuya Khóa Nhân Vật (Flow Character Sheet, Luma <= 215, 0% VOX)",
            "directive": (
                "80% ảnh điện ảnh 35mm ánh sáng tungsten ấm khóa đồng nhất khuôn mặt/trang phục từ Character Reference Sheet đầu tập "
                "(Highlight Luma <= 215 dịu mắt đêm khuya) + 15% video B-roll không khí sạch 4K + 5% chữ điện ảnh không hộp (0% VOX)."
            ),
        },
        "archival_forensic": {
            "id": "archival_forensic",
            "label": "Hồ sơ Pháp y & Highlight Tài liệu",
            "directive": (
                "Sử dụng văn bản/báo chí/hồ sơ thật với hiệu ứng highlight câu chữ then chốt, nhãn chứng cứ và camera push/pan có chủ đích."
            ),
        },
        "data_telemetry": {
            "id": "data_telemetry",
            "label": "HUD Số liệu & Telemetry Động",
            "directive": (
                "Khi lời bình nêu con số/thông số quan trọng, hiển thị callout số liệu lớn, bộ đếm hoặc thanh so sánh trực quan bám trên nền media."
            ),
        },
        "geopolitical_map": {
            "id": "geopolitical_map",
            "label": "Bản đồ Chiến lược & Tọa độ Địa lý",
            "directive": (
                "Với các beat địa lý/lộ trình, sử dụng bản đồ/ảnh vệ tinh làm nền kết hợp đường dẫn hướng, vùng ảnh hưởng và nhãn tọa độ rõ nét."
            ),
        },
        "split_screen_contrast": {
            "id": "split_screen_contrast",
            "label": "Đối lập Tuyên truyền vs. Thực tế",
            "directive": (
                "Đặt tương phản trực tiếp giữa kế hoạch/lời hứa hào nhoáng và hiện trường/hậu quả thực tế để tạo cú đấm thị giác."
            ),
        },
        "chapter_hit_cards": {
            "id": "chapter_hit_cards",
            "label": "Chapter Title Cards & Sound Hit",
            "directive": (
                "Mỗi chương chuyển mạch bằng đại cảnh ấn tượng kết hợp tiêu đề chương rõ nét và âm thanh chuyển chương có sức nặng."
            ),
        },
        "vox_satellite_maps": {
            "id": "vox_satellite_maps",
            "label": "Bản đồ Vệ tinh Đa tỷ lệ & Lộ trình Động",
            "directive": (
                "Sử dụng ảnh vệ tinh thật độ phân giải cao từ Z6 (quy mô vùng) đến Z16 (sát mái nhà/hiện trường) "
                "kết hợp quét vector GeoJSON, lát cắt 2.5D, luồng nhiệt hồng ngoại và radar định vị."
            ),
        },
        "vox_forensic_dossiers": {
            "id": "vox_forensic_dossiers",
            "label": "Hồ sơ Pháp y & Bảng Điều tra Động",
            "directive": (
                "Bố cục hồ sơ bìa manila, thẻ căn cước kép đối chiếu hai mặt cuộc sống, dải phim 35mm, "
                "bảng đèn huỳnh quang phân tích gen Y-STR, kính hiển vi so khớp 14 điểm đặc trưng vân tay và lệnh truy nã đỏ Class-A."
            ),
        },
        "vox_press_broadcast": {
            "id": "vox_press_broadcast",
            "label": "Báo chí Lưu trữ & Bản tin Truyền hình",
            "directive": (
                "Tái hiện báo giấy những năm 1990 quét bút dạ quang vàng, công cáo giới nghiêm đỏ, "
                "màn hình TV CRT quét tia scanline bản tin thời sự khẩn cấp và điện báo khẩn của công an."
            ),
        },
    },
}


_JOB_CONTEXT_SNAPSHOT_KEEP_KEYS = (
    "label",
    "name",
    "niche",
    "market",
    "language",
    "source_mode",
    "content_mode",
    "visual_strategy",
    "voice_id",
    "default_voice_id",
    "secondary_voice_id",
    "voice_speed",
    "default_ai_style_preset",
    "default_style_reference_image",
)


def _job_context(job: dict[str, Any]) -> str:
    recipe = dict(job.get("production_recipe") or {})
    target_mins = job.get("target_duration_minutes")
    if target_mins not in (None, ""):
        try:
            expected_sec = round(float(target_mins) * 60)
            edna = job.get("editing_dna") if isinstance(job.get("editing_dna"), dict) else {}
            vox_preset = str(edna.get("preset_id") or edna.get("editing_dna_preset") or "").strip()
            is_vox = vox_preset in {"forensic_noir_director_v2", "vox_china_crime_newsroom_v10"} or (
                str(edna.get("director_mode") or "").strip().lower() in {"v2", "vox_china_crime_newsroom_v10"}
            )
            vox_mismatch = is_vox and (
                str((recipe.get("quality_contract") or {}).get("visual_routing_policy") or "") != "vox_newsroom_v13_composable_lego_50pct_footage"
            )
            if not recipe.get("quality_contract") or abs(float(recipe.get("target_duration_sec") or 0) - expected_sec) > 1 or vox_mismatch:
                from .quality import normalize_production_recipe
                recipe = normalize_production_recipe(
                    recipe,
                    target_duration_minutes=target_mins,
                    visual_strategy=job.get("visual_strategy"),
                    editing_dna=edna,
                )
        except Exception:
            pass
    raw_snap = job.get("channel_profile_snapshot") if isinstance(job.get("channel_profile_snapshot"), dict) else {}
    snap_clean = {
        k: raw_snap[k]
        for k in _JOB_CONTEXT_SNAPSHOT_KEEP_KEYS
        if k in raw_snap and raw_snap[k] not in (None, "", [], {})
    }
    raw_brief = job.get("creative_brief") if isinstance(job.get("creative_brief"), dict) else {}
    brief_summary = {
        k: raw_brief[k]
        for k in ("narrative_angle", "writing_style", "hook_archetype", "opening_hook", "target_duration_minutes")
        if k in raw_brief and raw_brief[k] not in (None, "", [], {})
    }
    safe = {
        "id": job.get("id"),
        "title": job.get("title"),
        "topic": job.get("topic"),
        "source_url": job.get("source_url"),
        "market": job.get("market"),
        "language": job.get("language"),
        "target_duration_minutes": target_mins,
        "visual_strategy": job.get("visual_strategy"),
        "notes": job.get("notes"),
        "plan_engine": job.get("plan_engine"),
        "voice": job.get("voice") or {},
        "production_recipe": recipe,
        "radar": job.get("radar"),
        "channel_profile_snapshot": snap_clean,
        "playbook_id": job.get("playbook_id"),
        "creative_brief": brief_summary,
    }
    return json.dumps(safe, ensure_ascii=False)


def _creative_brief_direction(job: dict[str, Any], workspace: str | Path | None = None, phase: str = "") -> str:
    brief: dict[str, Any] = {}
    if isinstance(job.get("creative_brief"), dict):
        brief.update(job["creative_brief"])
    outline: list[dict[str, Any]] = []
    if isinstance(job.get("outline"), list):
        outline = [item for item in job["outline"] if isinstance(item, dict)]
    elif isinstance(job.get("outline"), dict) and isinstance(job["outline"].get("chapters"), list):
        outline = [item for item in job["outline"]["chapters"] if isinstance(item, dict)]
    if workspace is not None:
        ws = Path(workspace)
        brief_file = ws / "creative_brief.json"
        if brief_file.is_file():
            try:
                loaded_brief = json.loads(brief_file.read_text(encoding="utf-8"))
                if isinstance(loaded_brief, dict):
                    brief.update(loaded_brief)
            except Exception:
                pass
        outline_file = ws / "outline.json"
        if outline_file.is_file():
            try:
                loaded_outline = json.loads(outline_file.read_text(encoding="utf-8"))
                if isinstance(loaded_outline, list) and loaded_outline:
                    outline = [item for item in loaded_outline if isinstance(item, dict)]
                elif isinstance(loaded_outline, dict) and isinstance(loaded_outline.get("chapters"), list):
                    outline = [item for item in loaded_outline["chapters"] if isinstance(item, dict)]
            except Exception:
                pass
    if not brief and not outline:
        return ""

    lines: list[str] = [
        "CREATIVE BRIEF & DIRECTORIAL BLUEPRINT — MANDATORY EPISODE DIRECTION",
        "- The user and producer have locked the following Creative Brief and/or Chapter Outline for this episode.",
        "- Prioritize these creative choices (Narrative Angle, Writing Style, Opening Hook, Visual/Editing Archetypes, Custom Rules, and Chapter Outline) over generic defaults.",
    ]
    angle_id = str(brief.get("narrative_angle") or "").strip()
    angle_info = CREATIVE_STUDIO_CATALOG["narrative_angles"].get(angle_id)
    if angle_info:
        lines.append(f"- NARRATIVE ANGLE ({angle_info['label']}): {angle_info['directive']}")
    elif angle_id:
        lines.append(f"- NARRATIVE ANGLE: {angle_id}")

    style_id = str(brief.get("writing_style") or "").strip()
    style_info = CREATIVE_STUDIO_CATALOG["writing_styles"].get(style_id)
    if style_info:
        lines.append(f"- WRITING STYLE & VOICE ({style_info['label']}): {style_info['directive']}")
    elif style_id:
        lines.append(f"- WRITING STYLE & VOICE: {style_id}")

    hook_id = str(brief.get("hook_archetype") or "").strip()
    hook_info = CREATIVE_STUDIO_CATALOG["hook_archetypes"].get(hook_id)
    if hook_info:
        lines.append(f"- OPENING HOOK ARCHETYPE ({hook_info['label']}): {hook_info['directive']}")
    elif hook_id:
        lines.append(f"- OPENING HOOK ARCHETYPE: {hook_id}")

    opening_hook = str(brief.get("opening_hook") or "").strip()
    if opening_hook:
        lang = str(job.get("language") or "ko").strip().lower()
        pivot_hint = "cú lật '하지만 / 그런데' sắc lẹm" if lang == "ko" else "sharp paradox pivot"
        lines.append(
            f"- LOCKED/SEED OPENING HOOK IDEA (WINNER PARADOX HOOK — Mở màn trực diện bằng mỏ neo nghịch lý Vỏ bọc Hai Mặt / Hiện trường Khóa kín / Con số đối lập và {pivot_hint} ngay 15–30s đầu, 0% tả cảnh thời tiết lan man, 100% Xanh tiền trong 60s đầu): {opening_hook}"
        )

    edit_archetypes = brief.get("editing_archetypes")
    if isinstance(edit_archetypes, list) and edit_archetypes:
        archetype_notes = []
        for item in edit_archetypes:
            key = str(item or "").strip()
            info = CREATIVE_STUDIO_CATALOG["editing_archetypes"].get(key)
            if info:
                archetype_notes.append(f"  * {info['label']}: {info['directive']}")
            elif key:
                archetype_notes.append(f"  * {key}")
        if archetype_notes:
            lines.append("- VISUAL & EDITING GRAMMAR ARCHETYPES TO DEPLOY:\n" + "\n".join(archetype_notes))

    phase_key = str(phase or "").strip().lower()
    custom_rules = str(brief.get("custom_rules") or "").strip()
    if custom_rules:
        if phase_key and phase_key not in {"plan", "edit"} and len(custom_rules) > 1200:
            custom_rules = custom_rules[:1200] + "…"
        lines.append(f"- CUSTOM EPISODE RULES & CONSTRAINTS: {custom_rules}")

    cta_strategy = str(brief.get("cta_strategy") or "").strip()
    if cta_strategy and (not phase_key or phase_key == "plan"):
        lines.append(f"- STORY-DRIVEN ZERO-REPEAT ORGANIC CTA ROLE: {cta_strategy}")

    injected_rules = brief.get("self_learning_injected_rules")
    if isinstance(injected_rules, list) and injected_rules and (not phase_key or phase_key == "plan"):
        cleaned_rules = [str(r).strip() for r in injected_rules if str(r).strip()]
        if cleaned_rules:
            lines.append("- SELF-LEARNING INJECTED UPGRADE RULES:\n" + "\n".join(f"  * {r}" for r in cleaned_rules))

    if outline:
        if not phase_key or phase_key == "plan":
            lines.append(
                "- APPROVED CHAPTER OUTLINE BLUEPRINT (Follow this structural progression, arguments, and visual intent across script.md, visual_manifest.json, and edit):\n"
                + json.dumps(outline, ensure_ascii=False)
            )
        else:
            ws_ref = f"`{Path(workspace) / 'outline.json'}`" if workspace is not None else "`outline.json`"
            lines.append(f"- APPROVED CHAPTER OUTLINE BLUEPRINT: {len(outline)} chapters locked on disk at {ws_ref}.")
    return "\n".join(lines) + "\n"



def _narration_length_guidance(job: dict[str, Any]) -> str:
    recipe = job.get("production_recipe") or {}
    explicit_mins = job.get("target_duration_minutes")
    if explicit_mins in (None, ""):
        explicit_mins = (job.get("creative_brief") or {}).get("target_duration_minutes")
    if explicit_mins not in (None, ""):
        try:
            target_seconds = float(explicit_mins) * 60.0
        except (TypeError, ValueError):
            target_seconds = float(recipe.get("target_duration_sec") or 300)
    else:
        target_seconds = float(recipe.get("target_duration_sec") or 300)
    minutes = max(target_seconds / 60, 0.5)
    language = str(job.get("language") or "ko").lower()
    if language == "ja":
        minimum = floor(minutes * 270)
        maximum = ceil(minutes * 340)
        return f"about {minimum}-{maximum} Japanese characters (strictly targeting {minutes:g} minutes / {int(target_seconds)}s)"
    if language == "ko":
        # Calibrated to calm Korean documentary TTS (~280-335 non-space chars/min; ~365-425 spoken chars/min -> ~9,500-11,500 chars for 24-30 min)
        minimum = floor(minutes * 280)
        maximum = ceil(minutes * 335)
        ideal = round(minutes * 308)
        total_min = floor(minutes * 365)
        total_max = ceil(minutes * 425)
        target_beats_min = max(12, ceil(target_seconds / 9.0) if target_seconds >= 600 else ceil(target_seconds / 7.5))
        target_beats_max = max(16, ceil(target_seconds / 6.5))
        return (
            f"approximately {minimum}-{maximum} non-space Korean characters (ideal reference ~{ideal} non-space characters, "
            f"or ~{total_min}-{total_max} spoken characters including spaces, across roughly {target_beats_min}-{target_beats_max} parent beats, "
            f"targeting ~{minutes:g} minutes of finished narration)"
        )
    minimum = floor(minutes * 120)
    maximum = ceil(minutes * 165)
    return f"about {minimum}-{maximum} spoken words (a soft planning estimate, not an exact runtime lock, targeting ~{minutes:g} minutes / {int(target_seconds)}s)"


def _premium_editing_direction(job: dict[str, Any] | None = None) -> str:
    is_dir_v2 = _is_director_v2_true_crime_job(job) if isinstance(job, dict) else False
    safe_zone_clause = (
        "`upper_center_safe_above_785px` (`y <= 785px`) so the viewer's eye flows smoothly across cuts without colliding with bottom `62px–66px` subtitles (`800px–1040px`)"
        if is_dir_v2
        else "`upper_center_safe_above_820px` so the viewer's eye flows smoothly across cuts without colliding with bottom subtitles (`860px–1040px`)"
    )
    return f"""PREMIUM CINEMATIC EDITING DIRECTION — MASTER HUMAN FILM EDITOR, CINEMATOGRAPHER, COLORIST & SOUND DESIGNER CONSTITUTION
- CORE STUDIO PHILOSOPHY — ACT AS A PRODUCTION DIRECTOR PLUS A SENIOR EDITOR:
  * Upstream departments (`@script`, `@voice`, `@visuals`, `@footage`, `@ai_visual`) prepare raw materials (1st-gen channel voice stems + Whisper `words[]`, storyboards, verified footage, 1-to-1 AI stills). You operate as a production director plus a senior editor with second-by-second editorial responsibility for turning those raw ingredients into a cohesive, project-specific visual system.
  * Second-by-second editorial responsibility does not mean adding an effect every second: balance frame-level polish with sequence-level rhythm, deploy authored motion-design across 2.5D tabletop/compositing depth and true 3D satellite cartography where the story warrants it, treat typography and subtitles as editorial design rather than plain static default captions, and design sound with picture.
- MANDATORY HUMAN FILM EDITING CRAFTS:
  1. **ACTIVE VOICE RHYTHM, BREATHING ROOM & ZERO-CROSSING MID-BEAT CAESURAS (`editorial_voice_cutter.py` + `editorial_voice_plan.json`)**:
     - Never treat voiceover as a rigid conveyor belt! The coordinator has sculpted `narration.wav`, `voice_manifest.json`, `subtitles.srt`, and `visual_manifest.json` from lossless 1st-gen channel stems (`audio/beats_raw/`) with: (a) **Cold-Open Pre-Voice Breath (`pre_voice_breath_sec`)** so Frame 0 opens on atmospheric picture + sound before Word 1; (b) **Chapter & Twist Breathing Room**; (c) **Kinetic Action Shaving**; and (d) **Mid-Beat Zero-Crossing Caesura Splits (`caesura_windows`)** right before shocking mid-sentence reveals.
     - Enforce the **3-Tier Intentional Breathing Architecture**: (i) **Act Curtain Transitions (`ACT01 -> ACT02 -> ACT03 -> ACT04 -> ACT05`)** MUST open **`1.4s – 2.2s`** of dramatic breathing room (`>= 1.2s` hard gate); (ii) **Paradox/Rhetorical Questions (`?`), Key Evidence Twist Reveals & `FramelessCinemaTextBeat` (`CINEMA_TEXT`)** MUST open **`1.0s – 1.6s`** of breathing room (`>= 12` dramatic holds `>= 1.0s` across the episode); (iii) **Standard Continuous Narrative Sentences** within the same paragraph keep crisp pacing (**`0.28s – 0.48s`**) so total duration never drags. Lock every beat's `[startFrame, endFrame]` to `[visual_open_sec, visual_close_sec]` and lock `speechOffsetFrames`, `speechFrames`, `clauseFrameWindows`, and `subtitles.srt` strictly to Whisper `words[0].start .. words[-1].end` so subtitles NEVER remain on screen during silent breath gaps.
     - **100% VERIFIED `HIGHLIGHT_KEYWORDS` & SFX FILE EXISTENCE**: Every entry in `HIGHLIGHT_KEYWORDS` MUST match 100% of the actual target-language strings spoken in `voice_manifest.json` / `subtitles.srt` (including phonetically spelled numbers and proper nouns in the target script), and every SFX cue MUST reference an existing file in `presets/audio_library/sfx/` (use `audio/sfx_chapter_hit.mp3` for chapter transitions — NEVER invent non-existent filenames like `sfx_sub_bass_boom_chapter.mp3`).
     - During any `caesura_windows` hold, freeze/tighten focus on the visual subject, keep subtitles OFF during the silence (never spoil the reveal word before it is spoken!), and trigger the visual/subtitle reveal on the exact `end_frame` of the caesura.
  2. **WALTER MURCH'S RULE OF SIX & J-CUT / L-CUT ARCHITECTURE (`jl_cut_mode`)**:
     - Emotion (51%) and Story Advancement (23%) always outrank Rhythm (10%), Eye-Trace (7%), 2D Plane (5%), and 3D Space (4%).
     - Honor each beat's `jl_cut_mode` in `edit_rhythm_score.json`: use **L-Cuts (`l_cut_emotional_linger`)** so human faces, reactions, or smoking-gun evidence linger across post-speech silence; **J-Cuts (`j_cut_prelap_pivot`)** so room-tone/ambience of a new chapter or location enters `8–12` frames (`~0.3s`) before the picture cuts; **Crisp Hard Cuts (`smash_cut_kinetic` / `hard_cut_on_breath`)** on kinetic chains; and **Warm Cross-Dissolves (`gentle_sanctuary_dissolve`)** on contemplative/pastoral/archival passages. Never use tacky wipe/flash presets.
  3. **DAVID FINCHER MOTIVATED CAMERA LAW (`fincher_no_double_motion = true`)**:
     - Camera moves ONLY when human psychology or narrative tension moves. If real video footage ALREADY has strong internal camera motion (drone flight, tracking shot, pan), keep virtual Remotion transform locked/minimal (`1.0 -> 1.012`) — NEVER stack aggressive virtual zoom onto moving camera footage ("double motion"). On `tension_creep_hold`, creep slowly inward (`1.0 -> 1.055`) and **settle/lock the camera at the exact frame the truth lands**.
  4. **30% SHOT-SCALE PROGRESSION & EYE-TRACE SAFE ZONE (`recommended_shot_scale`)**:
     - Progress shot scales purposefully (`WIDE_ESTABLISHING -> MEDIUM_SUBJECT -> CLOSE_UP_DETAIL -> MACRO_EVIDENCE_OR_FACE`) with `>= 30%` scale contrast between adjacent cuts so back-to-back shots never jump-cut awkwardly at identical framing. Keep primary focal points in {safe_zone_clause}.
  5. **AUDIO-VISUAL COUNTERPOINT (`15% -> 50% -> 82%`) & EXACT PAYOFF SYNC MATH (`editorial_brain.py`)**:
     - Choreograph scenes in 3 purposeful beats: `(15%)` establish spatial/archival anchor -> `(50%)` reveal anomaly, highlight, or route shift locked to `Whisper words[]` via `t_anim_start = t_payoff_word - reveal_duration_sec` -> `(82%)` land human or causal consequence cleanly above the subtitle safe zone.
  6. **TWO-STAGE COLORIST EMOTIONAL ARC (`act_color_grade`)**:
     - First match/balance exposure & contrast across adjacent clips (`editorial_brain.compute_per_clip_grade_css`), then shape the 5-Act emotional color journey (`act_color_grade` in `edit_rhythm_score.json`: temperature shift, saturation, contrast, subtle optical vignette) so the film's visual mood evolves organically from Act 1 to Act 5 according to its genre.
  7. **BROADCAST SOUND DESIGN SOUL, CINEMATIC BOOKENDS (COLD OPEN & FINALE FADE-TO-BLACK) & ZERO AUDIO BLEED LAW**:
     - **CINEMATIC COLD-OPEN STAGING (`Frames 0 .. speechOffsetFrames`, MANDATORY ACROSS ALL CHANNELS)**:
       * **30-Frame (`1.0s`) Visual Fade-from-Black**: Never jump onto a raw 100%-bright opening frame at `Frame 0`! Render a top-level `#000000` `<AbsoluteFill>` overlay fading smoothly `1.0 -> 0.0` across `Frames 0..30` so the opening atmosphere emerges cinematically from black.
       * **Audible J-Cut BGM Pre-Roll (ZERO Dead-Air Intro)**: Never leave `Frames 0..40` in near-silence followed by an abrupt audio slam at Word 1! Ramp `bgm-01` smoothly from `~0.05 -> 0.155` across `Frames 0..10`, let the atmospheric score breathe audibly (`0.155`) across the pre-voice window, and smoothly duck (`0.155 -> 0.072`) across the `8 frames` immediately preceding `speechOffsetFrames` so the narrator's first word enters cleanly in the pocket.
       * **Early Act 1 Chapter Card (`~Frame 10`) & Zero Word-1 SFX Collision**: Anchor Act 1's Chapter Card inside the pre-voice breath (`~Frame 10 = 0.33s`) paired with a soft atmospheric cue (`audio/sfx_soft_whoosh.mp3`, `volume <= 0.09`). **STRICTLY FORBID** firing `sfx_chapter_hit` on `speechOffsetFrames` colliding simultaneously with the narrator's first syllable!
     - **CINEMATIC FINALE VISUAL FADE-TO-BLACK & 3.8s MUSICAL CLOSURE (MANDATORY ACROSS ALL CHANNELS)**:
       * Preserve `100%` of the final spoken sentence (`0` clipped words), let the score swell gently (`0.072 -> 0.145`) as speech concludes, and fade both BGM and room-tone smoothly to `0.000` over the `3.8s` (`~114-frame`) post-speech tail.
       * **Mandatory Visual Fade-to-Black**: Never leave the final still or clip sitting at 100% brightness until a jarring hard cut at EOF! Render a top-level `#000000` `<AbsoluteFill>` (`zIndex >= 90`) fading smoothly `0.0 -> 1.0` across the final `84 frames` (`2.8s`) before `DURATION_FRAMES - 12`, holding pure `#000000` black across the final `12 frames` (`0.4s`) in lockstep with the audio fade-out.
     - **ZERO SOURCE AUDIO BLEED & 100% SPEECH-FREE INSTRUMENTAL BGM**:
       * Every `<Video>` element in Remotion MUST specify BOTH `muted` AND `volume={{0}}`, and every `footage/*.mp4` / preview proxy MUST have `0` audio streams (`-an`).
       * Every BGM file in `BGM_SEGMENTS` MUST be 100% clean instrumental music (`0` spoken dialogue, podcasts, radio chatter, or vocals).
     - Duck BGM cleanly under speech (`~ -16.5dB`) and swell BGM gently (`+bgm_breath_lift_db`) inside intentional pauses (`>= 1.15s`) so silences breathe with emotion.
     - On `pre_twist_bgm_drop = true` beats, drop BGM before the twist while keeping a **subtle `-41dBFS` (`volume: 0.015`) analog room-tone/sub-air floor** (NEVER drop total audio to `0.000` digital zero during mid-episode beats, preventing harsh vacuum clicks and `-48dB` dead-air QC failures).
     - Offset SFX by attack time (`t_sfx_start = t_impact - sfx_attack_sec`, ~2 frames early) so acoustic peaks strike on the exact visual impact frame.
  8. **VOICE-TO-VOX PROMPT COMPILER × TACTILE VOX EDITORIAL DESK (`src/vox-studio/vox-editorial-desk/index.tsx`) & PRECISION 3D SATELLITE CARTOGRAPHY (`<GeoJson3DMapStage>`)**:
     - **3-Step Voice-to-Vox Prompt Compiler (`t1 -> t2 -> t3`)**: For every spoken VOX sentence (`clauses[0..N]` in `voice_manifest.json`), extract `(1) voice_meaning` -> `(2) illustration_content` (the exact physical detail, measurement, spatial cross-section, contradiction, or suspect/police movement route that the viewer needs to SEE visually) -> `(3) vox_prompt` (a bespoke 1-to-1 scene design prompt in `vox_scene_manifest.json`, just like 1-to-1 AI image prompts).
     - **4 IRONCLAD SATELLITE MAP LAWS (`<GeoJson3DMapStage>`)**:
       * **(1) 100% Voice-Matched Suspect Escape or Police Pursuit Routing (`0%` Periodic `idx % N` Placement)**: Deploy `<GeoJson3DMapStage>` **ONLY** on spoken beats that explicitly describe **(a) Suspect Escape / Infiltration Movement** (fleeing the crime scene, crossing provinces/cities, infiltrating a new city, traveling between cities) OR **(b) Police Dispatch / Dragnet / Stakeout / Extradition Movement** (dispatching from PSB to crime scene, multi-province search expansion, undercover perimeter closing in on the capture site, or extraditing the suspect back to the investigating city). Strictly forbid placing maps on sentences about spoken accents/dialects, facial habits, studio intros, or internal paperwork.
       * **(2) 100% Exact Real-World Geographic Coordinates & Origin-to-Destination Fidelity**: Every pin, landmark, and `satLoupe` (`4.0x` zoom) must lock to exact real-world WGS84 `[lon, lat]` coordinates (`0.00px` Web Mercator drift via `lonLatToPlatePx`). When the voice describes an inter-city or inter-province movement (e.g., Jilin -> Shenyang or Shenyang -> Harbin), the map MUST use the regional satellite plate covering both cities and connect the exact Origin Pin to the exact Destination Pin mentioned in the sentence.
       * **(3) Authentic Road/Rail Multi-Vertex Route Polylines (`>= 12..40` Real Vertices, `0%` Synthetic Sine Curves)**: Every route in `*GeoData.ts` (`routes`) must trace actual highway (`G1`/`G102`/`G12`), railway, or urban street corridors connecting the spoken origin and destination (or multiple radiating routes `routes.length >= 2..3` when expanding a multi-province dragnet).
       * **(4) Zero Map Template Cloning & Zero Zoom-In/Zoom-Out**: Every `<GeoJson3DMapStage>` scene must have its own unique `routes` key, `polygons` key, pin `(dx, dy, align)` offsets, `satLoupe` `(screenX, screenY)` position, and locked-zoom 3D perspective (`0%` camera zoom-in or zoom-out: `startZoom == endZoom == 1.0`).
     - **Bespoke Tactile Editorial Desk (`src/vox-studio/vox-editorial-desk/index.tsx` — `0%` Camera Zoom-In / Zoom-Out, `14` Spatial Layouts × `9` Cut-and-Paste Entrance Effects)**: Render `<Desk>` (`V.bgDesk = #E4DDCF` + `#voxGrain` `opacity: 0.22`) or `<BlackCard inset={{38}}>` (`#1B1B1A`) as a 100% locked overhead tabletop (`z = 1.0`, `transform: 'none'` — **STRICTLY FORBID any camera zoom-in or zoom-out on VOX!**). Vary ONLY the **Spatial Layout (`bố cục` — 14 distinct tabletop geometries: `direct_50_50_collision_seam`, `stepped_seesaw_balance`, `trifold_accordion_pamphlet`, `vertical_scroll_plus_pedestal`, `poker_fan_3_cards_hand`, `macro_loupe_left_half`, `macro_loupe_right_half`, `diagonal_3_step_staircase`, `architectural_l_shape_frame`, `cinema_monitor_68_plus_right_tower`, `inverted_triangle_corkboard_web`, `center_monolith_diagonal_satellites`, `horizontal_top_bottom_split`, `asymmetric_left_bleed_52_48`)** and the **12fps Cut-and-Paste Entrance Effect (`hiệu ứng cắt dán xuất hiện` — 9 tactile paper-collage entrance modes via `<SlideIn from="...">` / `voxDiverseEntry12`: `scissors_slide_left`, `scissors_slide_right`, `slap_drop_top`, `sticker_peel_up`, `unroll_scroll_down`, `accordion_fold_left`, `accordion_fold_right`, `diagonal_toss_spin`, `fan_deal_bottom`, plus `voxStampSlam12`)** per sentence (`0` consecutive scenes repeating the same layout or entrance sequence!). Pair each VOX scene's `t1 -> t2 -> t3` clauses with **2–3 real recorded physical Foley SFX** (`select_vox_clause_sfx_events` from `public/audio_library/sfx/`).
     - **Pixel-Coordinate Grid Calibration Law (`100px` Grid Inspection)**: Inspect the rendered `15% - 50% - 85%` frames via `read_file` to lock every `<RedCircle>`, `<RedLine>`, `<DimensionBracket>`, `<Highlight>`, and `<OpticalLoupe>` onto the exact physical detail with `0px` offset inside `[60 <= x <= 1860, 40 <= y <= 820]`.
  9. **100% EYE-VERIFIED ARCHIVAL FOOTAGE & SEMANTIC VOICE MATCH (3-FRAME VISUAL VERIFICATION)**:
     - Never write blind automated heuristics (`pos_ratio` / `lum_std`) to slice footage without looking at it. Every `REAL_FTG` sub-clip and VOX plate MUST be visually inspected by the AI (`read_file` / `vision_inspect_frames` on labeled contact sheets and 100px coordinate grids) to verify: (a) `100%` authentic case subject, (b) `0%` third-party logos/watermarks/QR codes/foreign subtitles/studio hosts via per-source calibrated 16:9 `SAFE_CROP`, and (c) `100%` semantic match between the visual frame and the spoken sentence `narrationText`.
"""


def _resolve_job_editing_dna(job: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(job, dict):
        return {}
    snap = job.get("channel_profile_snapshot") if isinstance(job.get("channel_profile_snapshot"), dict) else {}
    merged: dict[str, Any] = {}
    if isinstance(snap.get("editing_dna"), dict):
        merged.update(snap["editing_dna"])
    if isinstance(job.get("editing_dna"), dict):
        merged.update(job["editing_dna"])
    return merged


def _resolve_profile_ai_style_info(job: dict[str, Any] | None) -> tuple[str, str]:
    """Return (style_preset_label, ref_image_basename) dynamically from the active job/profile without hardcoding channel assets."""
    if not isinstance(job, dict):
        return ("Profile AI Keyframe Style", "")
    snap = job.get("channel_profile_snapshot") if isinstance(job.get("channel_profile_snapshot"), dict) else {}
    ai_cfg = job.get("ai_visual") if isinstance(job.get("ai_visual"), dict) else {}
    preset_label = str(
        ai_cfg.get("style_preset")
        or ai_cfg.get("custom_style")
        or job.get("default_ai_style_preset")
        or snap.get("default_ai_style_preset")
        or "Profile Locked AI Style"
    ).strip()
    style_prompt_lower = str(ai_cfg.get("style_prompt") or "").lower()
    forbids_cartoon = any(
        tok in style_prompt_lower or tok in preset_label.lower()
        for tok in ("0% cartoon", "0% stickman", "realistic human anatomy", "prestige vault", "atmospheric forensic")
    )
    ref_raw = "" if forbids_cartoon else str(
        ai_cfg.get("style_reference_image")
        or job.get("default_style_reference_image")
        or snap.get("default_style_reference_image")
        or ""
    ).strip()
    ref_name = Path(ref_raw.replace("\\", "/")).name if ref_raw else ""
    return (preset_label, ref_name)


def is_creative_audio_drama_job(job: dict[str, Any] | None) -> bool:
    """True when the job or its Channel Profile operates in Creative Audio Drama mode."""
    if not isinstance(job, dict):
        return False
    snap = job.get("channel_profile_snapshot") if isinstance(job.get("channel_profile_snapshot"), dict) else {}
    ed_dna = job.get("editorial_dna") if isinstance(job.get("editorial_dna"), dict) else (
        snap.get("editorial_dna") if isinstance(snap.get("editorial_dna"), dict) else {}
    )
    editing = _resolve_job_editing_dna(job)
    cm = str(
        job.get("content_mode")
        or snap.get("content_mode")
        or ed_dna.get("content_mode")
        or editing.get("content_mode")
        or ""
    ).strip().lower()
    preset = str(editing.get("preset_id") or "").strip().lower()
    vis_prio = str(editing.get("visual_priority_mode") or "").strip().lower()
    return (
        cm == "creative_audio_drama"
        or preset == "kr_goodnight_cinema_drama"
        or vis_prio == "ai_cinema_character_drama"
    )


def is_any_vox_enabled_for_job(job: dict[str, Any] | None) -> bool:
    """True ONLY when @vox / VOX scenes are enabled for this job's profile."""
    if not isinstance(job, dict):
        return True
    if is_creative_audio_drama_job(job):
        return False
    editing = _resolve_job_editing_dna(job)
    raw_ed = job.get("editing_dna") if isinstance(job.get("editing_dna"), dict) else {}
    snap = job.get("channel_profile_snapshot") if isinstance(job.get("channel_profile_snapshot"), dict) else {}
    snap_ed = snap.get("editing_dna") if isinstance(snap.get("editing_dna"), dict) else {}
    for d in (raw_ed, snap_ed, editing):
        if d.get("vox_enabled") is False:
            return False
    preset = str(editing.get("preset_id") or "").strip().lower()
    if preset in {"sacred_devotional", "grace_letter", "kr_goodnight_cinema_drama"}:
        return False
    return True


def _resolve_lang_editorial_labels(job: dict[str, Any] | None) -> tuple[str, str]:
    """Return (chapter_script_lock_label, ai_disclosure_label) matched to the active job language."""
    lang = str((job or {}).get("language") or "ko").strip().lower()
    if is_creative_audio_drama_job(job):
        if lang == "ko":
            return ("`100% 한글` (`제1장`..`제6장`)", "오디오 드라마 · 극적 연출 이미지")
        if lang == "vi":
            return ("`100% Tiếng Việt` (`Chương 1`..`Chương 6`)", "Hình ảnh điện ảnh kịch truyền thanh")
        return ("`100% target-language` (`Chapter 1`..`Chapter 6`)", "Dramatized audio drama cinema")
    if lang == "ko":
        return ("`100% 한글` (`제1막`..`제5막`)", "재연 · 이해를 돕기 위한 이미지")
    if lang == "vi":
        return ("`100% Tiếng Việt` (`Hồi 1`..`Hồi 5`)", "Hình ảnh tái dựng minh họa")
    return ("`100% target-language` (`Act I`..`Act V`)", "Illustrative reconstruction")


def _is_china_scoped_job(job: dict[str, Any] | None) -> bool:
    """True ONLY when the active profile or episode explicitly covers Chinese topics/entities."""
    if not isinstance(job, dict):
        return False
    snap = job.get("channel_profile_snapshot") if isinstance(job.get("channel_profile_snapshot"), dict) else {}
    ed = snap.get("editorial_dna") if isinstance(snap.get("editorial_dna"), dict) else {}
    if str(ed.get("foreign_entity_naming_scope") or "").strip().lower() == "chinese_modern":
        return True
    seo_dna = job.get("seo_keyword_dna") or snap.get("seo_keyword_dna") or {}
    seo_kw = str(seo_dna.get("primary_title_keyword") or "") if isinstance(seo_dna, dict) else ""
    allowed = json.dumps(snap.get("allowed_topics") or [], ensure_ascii=False)
    blob = " ".join([
        seo_kw,
        allowed,
        str(job.get("title") or ""),
        str(job.get("topic") or ""),
        str(snap.get("label") or ""),
    ]).lower()
    return any(tok in blob for tok in ("중국", "중화", "베이징", "상하이", "위안", "공안", "china", "chinese", "trung quốc", "nhân dân tệ"))


def _resolve_vox_preset_id(job: dict[str, Any] | None) -> str:
    if not isinstance(job, dict):
        return "custom"
    ed_dna = _resolve_job_editing_dna(job)
    dir_mode = str(ed_dna.get("director_mode") or "").strip().lower()
    preset_id = str(ed_dna.get("preset_id") or "").strip()
    if preset_id == "forensic_noir":
        return "forensic_noir"
    if dir_mode in {"v2", "vox_china_crime_newsroom_v10"} or preset_id in {"forensic_noir_director_v2", "vox_china_crime_newsroom_v10"}:
        return "forensic_noir_director_v2"
    if preset_id in {"sacred_devotional", "grace_letter"}:
        return "sacred_devotional"
    if preset_id == "kr_goodnight_cinema_drama" or is_creative_audio_drama_job(job):
        return "kr_goodnight_cinema_drama"
    if preset_id in {"financial_forensic_vox", "2.5d_technical", "archival_historical", "investigative_counterpoint_vn"}:
        return preset_id
    return preset_id or "custom"


def _is_non_vox_devotional_job(job: dict[str, Any] | None) -> bool:
    return _resolve_vox_preset_id(job) == "sacred_devotional"


def _is_director_v2_true_crime_job(job: dict[str, Any] | None) -> bool:
    return _resolve_vox_preset_id(job) == "forensic_noir_director_v2"


def _is_financial_fugitive_director_v2_job(job: dict[str, Any] | None) -> bool:
    if not isinstance(job, dict):
        return False
    ed_dna = _resolve_job_editing_dna(job)
    if str(ed_dna.get("vox_desk_surface") or "").strip() == "financial_kraft":
        return True
    snap = job.get("channel_profile_snapshot") if isinstance(job.get("channel_profile_snapshot"), dict) else {}
    prof_id = str(job.get("channel_profile_id") or snap.get("id") or "").strip()
    return prof_id == "channel-kr-financial-fugitive-director-v2"


def _director_v2_desk_and_motion_text_tokens(job: dict[str, Any] | None) -> tuple[str, str]:
    if _is_financial_fugitive_director_v2_job(job):
        return (
            "`<Desk surface=\"financial_kraft\">` nền vàng hồ sơ trơn dịu `#B69C71` (`radial #BDA378 -> #B69C71 -> #A98F65` + `#voxGrain` `opacity: 0.14`, **TUYỆT ĐỐI `0%` đường kẻ ô vuông `80x80`, `0%` dòng kẻ ngang, `0%` chấm bi, `0%` `<BlueprintGridBoard>`, `0%` khung viền hộp lồng nhau**) + `<BlackCard inset={{38}}>` `#1B1B1A`",
            "`src/components/FinancialMotionTextBeat.tsx` (Motion Text Kiểm toán – Ngân hàng riêng của Tội phạm Tài chính không kẻ ô: `vault_odometer` trục cuộn số tiền vàng kim loại, `audit_seal_peel` bóc dải niêm phong hồ sơ `#B69C71` + đường truy vết dòng tiền, `ledger_crimson_strike` nét gạch đỏ kiểm toán + khóa phán quyết, `balance_sheet_split`)",
        )
    return (
        "`<Desk>` `#E4DDCF` + `#voxGrain` `opacity: 0.22` + `<BlackCard inset={{38}}>` `#1B1B1A`",
        "`src/components/FramelessCinemaTextBeat.tsx`",
    )


def _is_true_crime_vox25d_job(job: dict[str, Any] | None) -> bool:
    return _resolve_vox_preset_id(job) in {"forensic_noir_director_v2", "forensic_noir"}


def _enrich_vox_skin_dict(base: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    out.setdefault("skin_name", out.get("skin_label", ""))
    out.setdefault("safe_zone", f"[60 <= x <= 1860, 40 <= y <= {out.get('safe_max_y', 835)}]")
    out.setdefault(
        "mix_summary",
        f"Footage {out.get('footage_ratio_desc', '')} + VOX {out.get('vox_ratio_desc', '')} + CinemaText {out.get('cinema_text_desc', '')} + AI {out.get('ai_ratio_desc', '')}",
    )
    return out


def _channel_vox_skin_profile(job: dict[str, Any] | None) -> dict[str, Any]:
    preset_id = _resolve_vox_preset_id(job)
    lang = str((job or {}).get("language") or "ko").strip().lower()
    if preset_id == "forensic_noir_director_v2":
        if _is_financial_fugitive_director_v2_job(job):
            return _enrich_vox_skin_dict({
                "preset_id": "forensic_noir_director_v2",
                "skin_label": "Financial Crime Plain Kraft Dossier Desk (`CofiRemotion/src/vox-studio/vox-editorial-desk/index.tsx` `<Desk surface=\"financial_kraft\">` `#B69C71` — 0% Grid Lines, 0% Zoom-In/Zoom-Out) & Precision 3D Satellite Cartography (`<GeoJson3DMapStage>`)",
                "toolkit": "`src/vox-studio/vox-editorial-desk/index.tsx` (`<Desk surface=\"financial_kraft\">` plain unruled `#B69C71`, `BlackCard`, `SlideIn`, `voxDiverseEntry12`, `VoxVideoPaper`, `VoxPhotoPaper`, `DieCutSticker`, `TornClipping`, `IndexCard`, `Stamp`, `Label`, `Highlight`, `RedLine`, `RedCircle`, `Underline`, `DimensionBracket`, `OpticalLoupe`, `Tape`, `step12`, `p12` — STRICTLY `0%` `80x80` grid lines, `0%` `<BlueprintGridBoard>`, `0%` camera zoom-in/zoom-out `z = 1.0`, varying 14 Spatial Layouts × 9 Cut-and-Paste Entrance Effects per sentence) + `GeoJson3DMapStage` (`src/vox-studio/china-crime-newsroom/VoxGeoJson3DCartography.tsx` — cross-border fund/fugitive movement routes, `0%` zoom-in/zoom-out)",
                "palette": "`#B69C71` plain unruled muted golden-ochre dossier surface (`<Desk surface=\"financial_kraft\">`, radial `#BDA378 -> #B69C71 -> #A98F65` + `#voxGrain` `opacity: 0.14`, `0%` grid/ruled lines, `0%` nested box frames), `#1B1B1A` `<BlackCard inset={38}>` crash contrast card, `#EEEDED` cream card stock, `#ECC057` bullion gold, `#B8433F` audit deficit crimson, `#DACF08` multiply highlighter",
                "vox_ratio_desc": "Flexible meaning-driven Priority #2 (`VOX_01..VOX_N` on plain `#B69C71` `<Desk surface=\"financial_kraft\">` — mandatory whenever real footage is absent, before AI image; `0%` grid lines, `0%` camera zoom-in/zoom-out, MỖI CẢNH LÀ ĐỘC LẬP, MỖI VIDEO LÀ ĐỘC LẬP)",
                "footage_ratio_desc": "Priority #1 (`>= 50%` target when real case footage exists, mandatory AI Eye-Calibrated `100px` grid `SAFE_CROP` + `>=28s` intro & `>=22s` outro skip, `dHash >= 14`, `time_gap >= 10.2s`, `max_uses = 1`, `0%` intros/hosts/logos/foreign subs/QR/unrelated B-roll)",
                "cinema_text_desc": "Financial Crime Audit Motion Text (`src/components/FinancialMotionTextBeat.tsx` — bespoke non-gridded banking/audit choreography: `vault_odometer` mechanical currency slot reel, `audit_seal_peel` `#B69C71` classified kraft audit seal peel + fund-trail vector, `ledger_crimson_strike` crimson audit cancellation slash + bullion-gold verdict lock, `balance_sheet_split`; `0%` consecutive mode repeats, hiding `<SubtitleOverlay>` underneath)",
                "motion_text_module": "CofiRemotion/src/components/FinancialMotionTextBeat.tsx",
                "ai_ratio_desc": "Priority #3 Last Resort ONLY (Profile-Locked AI keyframes strictly for closed-room moments when neither real footage nor VOX illustration applies)",
                "safe_max_y": 820,
                "target_lufs": "-14.8 LUFS",
            })
        return _enrich_vox_skin_dict({
            "preset_id": "forensic_noir_director_v2",
            "skin_label": "Voice-to-Vox Prompt Compiler × Tactile Vox Editorial Desk (`CofiRemotion/src/vox-studio/vox-editorial-desk/index.tsx` — 0% Zoom-In/Zoom-Out, 14 Spatial Layouts × 9 Cut-and-Paste Entrances) & Precision 3D Satellite Cartography (`<GeoJson3DMapStage>`)",
            "toolkit": "`src/vox-studio/vox-editorial-desk/index.tsx` (`Desk`, `BlackCard`, `SlideIn`, `voxDiverseEntry12`, `VoxVideoPaper`, `VoxPhotoPaper`, `DieCutSticker`, `TornClipping`, `IndexCard`, `Stamp`, `Label`, `Highlight`, `RedLine`, `RedCircle`, `Underline`, `DimensionBracket`, `OpticalLoupe`, `Tape`, `step12`, `p12` — 100% locked overhead tabletop `z = 1.0`, `0%` camera zoom-in/zoom-out, varying 14 Spatial Layouts × 9 Cut-and-Paste Entrance Effects per sentence) + `GeoJson3DMapStage` (`src/vox-studio/china-crime-newsroom/VoxGeoJson3DCartography.tsx` — 100% voice-matched suspect/police movement routes & exact WGS84 origin->destination coordinates, `0%` zoom-in/zoom-out)",
            "palette": "`#E4DDCF` warm editorial paper desk + `#voxGrain` (`opacity: 0.22`), `#1B1B1A` `<BlackCard inset={38}>` contrast card, `#EEEDED` cream card stock, `#171716` charcoal ink, `#B8433F` clue red, `#DACF08` multiply highlighter",
            "vox_ratio_desc": "Flexible meaning-driven Priority #2 (`VOX_01..VOX_N` — mandatory whenever real footage is absent, before AI image; `0%` fixed template count, `0%` fixed spacing or percentage cap, `0%` camera zoom-in/zoom-out, MỖI CẢNH LÀ ĐỘC LẬP, MỖI VIDEO LÀ ĐỘC LẬP)",
            "footage_ratio_desc": "Priority #1 (`>= 50%` target when real case footage exists, mandatory AI Eye-Calibrated `100px` grid `SAFE_CROP` + `>=28s` intro & `>=22s` outro skip, `dHash >= 14`, `time_gap >= 10.2s`, `max_uses = 1`, `0%` intros/hosts/logos/foreign subs/QR/unrelated B-roll)",
            "cinema_text_desc": "Flexible Narrative Drop-Point Motion Text (`src/components/FramelessCinemaTextBeat.tsx` — 0% repeating 1 motion/font/layout across the video, placed strictly at true narrative drop points per job [0% fixed periodic spacing], 100% context-matched fontStyle, accentColor, layoutVariant & showroomRenderer; STRICTLY FORBID paper `VoxNewsroomMotionText.tsx`)",
            "ai_ratio_desc": "Priority #3 Last Resort ONLY (Profile-Locked AI keyframes strictly for closed-room moments when neither real footage nor VOX illustration applies)",
            "safe_max_y": 820,
            "target_lufs": "-14.8 LUFS",
        })
    if preset_id == "forensic_noir":
        return _enrich_vox_skin_dict({
            "preset_id": "forensic_noir",
            "skin_label": "Classic Tactile Forensic Noir (`CofiRemotion/src/vox-studio/VoxTactileNewsPrimitives.tsx` — 0% Camera Zoom-In/Zoom-Out, 14 Spatial Layouts × 9 Cut-and-Paste Entrances)",
            "toolkit": "`VoxTactileNewsPrimitives.tsx` + `vox-editorial-desk/index.tsx` (`SlideIn`, `voxDiverseEntry12`) + `GeoJson3DMapStage` (`12fps` `pStep` paper cut-and-paste entrances on a 100% locked `z = 1.0` overhead desk — `0%` camera zoom-in or zoom-out)",
            "palette": "`#1E1915` walnut desk, `#8A623E` detective corkboard, `#EAE3D2` fibrous newsprint, `#9E1B18` crimson editorial ink & cotton thread, `#FACC15` translucent brush highlighter",
            "vox_ratio_desc": "Flexible meaning-driven Priority #2 whenever real footage is absent (`0%` fixed template count, `0%` fixed spacing or percentage cap, `0%` camera zoom-in/zoom-out)",
            "footage_ratio_desc": "`55%–60%` clean 3-frame verified case & same-country contextual footage (`3.0–4.8s/cut`, `max_uses = 1`)",
            "cinema_text_desc": "Flexible Narrative Drop-Point Motion Text (`src/components/FramelessCinemaTextBeat.tsx` — 0% monoculture motion/font/layout, placed strictly at true drop points, 100% context-matched fontStyle/accentColor/layoutVariant/showroomRenderer)",
            "ai_ratio_desc": "Priority #3 Last Resort 1-to-1 4D Faceless Forensic AI keyframes strictly for closed-room moments",
            "safe_max_y": 835,
            "target_lufs": "-18 LUFS",
        })
    if preset_id == "financial_forensic_vox":
        return _enrich_vox_skin_dict({
            "preset_id": "financial_forensic_vox",
            "skin_label": "Cyber-Financial Forensic Audit Slate (`CofiRemotion/src/vox-studio/VoxComposablePrimitives.tsx` — 0% Camera Zoom-In/Zoom-Out)",
            "toolkit": "`VoxComposablePrimitives.tsx` + `vox-editorial-desk/index.tsx` (`SlideIn`, `voxDiverseEntry12`) + `GeoJson3DMapStage` (`0°` crisp digital audit nodes, on-chain wallet graphs, liquidity waterfall curves & 3D GIS money trails on a locked `z = 1.0` overhead stage — `0%` camera zoom-in or zoom-out)",
            "palette": "`#040C18` / `#061A2E` midnight cyber-navy audit slate, `#38BDF8` ice-cyan vector lines, `#FACC15` capital/metric amber, `#EF4444` freeze/deficit crimson",
            "vox_ratio_desc": "Flexible meaning-driven Priority #2 whenever real footage is absent (`0%` fixed template count, `0%` fixed spacing or percentage cap, `0%` camera zoom-in/zoom-out)",
            "footage_ratio_desc": "`45%–52%` clean 3-frame verified case, financial institution, server & raid footage (`3.0–5.0s/cut`, `max_uses = 1`)",
            "cinema_text_desc": "Flexible Narrative Drop-Point Motion Text (`src/components/FramelessCinemaTextBeat.tsx` — 0% monoculture motion/font/layout, placed strictly at true drop points, 100% context-matched fontStyle/accentColor/layoutVariant/showroomRenderer)",
            "ai_ratio_desc": "Priority #3 Last Resort 1-to-1 4D Faceless Forensic AI keyframes for closed-room moments",
            "safe_max_y": 835,
            "target_lufs": "-18 LUFS",
        })
    if preset_id == "2.5d_technical":
        return _enrich_vox_skin_dict({
            "preset_id": "2.5d_technical",
            "skin_label": "Geotechnical & Engineering Blueprint Slate (`CofiRemotion/src/vox-studio/VoxComposablePrimitives.tsx` — 0% Camera Zoom-In/Zoom-Out)",
            "toolkit": "`VoxComposablePrimitives.tsx` + `vox-editorial-desk/index.tsx` (`SlideIn`, `voxDiverseEntry12`) + `GeoJson3DMapStage` (geological cross-sections, hydraulic pressure gauges, elevation vectors & 3D Esri+OSM terrain corridors on a locked `z = 1.0` stage — `0%` camera zoom-in/zoom-out)",
            "palette": "`#071320` engineering blueprint slate, `#38BDF8` ice-cyan CAD vectors, `#FACC15` stress-load amber, `#F8FAFC` crisp dimension ink",
            "vox_ratio_desc": "Flexible meaning-driven Priority #2 whenever real footage is absent (`0%` fixed template count, `0%` fixed spacing or percentage cap, `0%` camera zoom-in/zoom-out)",
            "footage_ratio_desc": "`50%–55%` clean 3-frame verified engineering, infrastructure & terrain footage (`3.0–5.0s/cut`, `max_uses = 1`)",
            "cinema_text_desc": "Flexible Narrative Drop-Point Motion Text (`src/components/FramelessCinemaTextBeat.tsx` — 0% monoculture motion/font/layout, placed strictly at true drop points, 100% context-matched fontStyle/accentColor/layoutVariant/showroomRenderer)",
            "ai_ratio_desc": "Priority #3 Last Resort 1-to-1 structural/geotechnical AI keyframes",
            "safe_max_y": 835,
            "target_lufs": "-18 LUFS",
        })
    if preset_id == "archival_historical":
        return _enrich_vox_skin_dict({
            "preset_id": "archival_historical",
            "skin_label": "Declassified Archival Vault & Parchment (`CofiRemotion/src/vox-studio/VoxComposablePrimitives.tsx` — 0% Camera Zoom-In/Zoom-Out)",
            "toolkit": "`VoxComposablePrimitives.tsx` + `vox-editorial-desk/index.tsx` (`SlideIn`, `voxDiverseEntry12`) + `GeoJson3DMapStage` (declassified memos, redaction strips, executive seals, optical loupes & historical 3D GIS theatres on a locked `z = 1.0` stage — `0%` camera zoom-in/zoom-out)",
            "palette": "`#F3ECE0` archival rag paper, `#14181F` vault slate, `#1C1917` typewriter carbon ink, `#991B1B` declassification seal crimson, `#F59E0B` archival highlight",
            "vox_ratio_desc": "Flexible meaning-driven Priority #2 whenever real footage is absent (`0%` fixed template count, `0%` fixed spacing or percentage cap, `0%` camera zoom-in/zoom-out)",
            "footage_ratio_desc": "`60%–68%` verified historical/presidential/intelligence footage & primary archival stills (`3.5–5.0s/cut`, `max_uses = 1`)",
            "cinema_text_desc": "Flexible Narrative Drop-Point Motion Text (`src/components/FramelessCinemaTextBeat.tsx` — 0% monoculture motion/font/layout, placed strictly at true drop points, 100% context-matched fontStyle/accentColor/layoutVariant/showroomRenderer)",
            "ai_ratio_desc": "Priority #3 Last Resort period-accurate AI reconstructions",
            "safe_max_y": 845 if lang != "ko" else 835,
            "target_lufs": "-18 LUFS",
        })
    return _enrich_vox_skin_dict({
        "preset_id": preset_id,
        "skin_label": f"Channel-Isolated Documentary Vox Skin (`{preset_id}` · `CofiRemotion/src/vox-studio/VoxComposablePrimitives.tsx` — 0% Camera Zoom-In/Zoom-Out)",
        "toolkit": "`VoxComposablePrimitives.tsx` + `vox-editorial-desk/index.tsx` (`SlideIn`, `voxDiverseEntry12`) + `GeoJson3DMapStage` (locked `z = 1.0` stage, `0%` camera zoom-in/zoom-out)",
        "palette": "the active Channel Profile's locked `editing_dna.color_grade` & material palette (`0%` cross-channel skin bleed)",
        "vox_ratio_desc": "Flexible meaning-driven Priority #2 whenever real footage is absent (`0%` fixed template count, `0%` fixed spacing or percentage cap, `0%` camera zoom-in/zoom-out)",
        "footage_ratio_desc": "`50%–60%` clean 3-frame verified case & contextual footage (`3.0–5.0s/cut`, `max_uses = 1`)",
        "cinema_text_desc": "Flexible Narrative Drop-Point Motion Text (`src/components/FramelessCinemaTextBeat.tsx` — 0% monoculture motion/font/layout, placed strictly at true drop points, 100% context-matched fontStyle/accentColor/layoutVariant/showroomRenderer)",
        "ai_ratio_desc": "Priority #3 Last Resort 1-to-1 profile-locked AI keyframes",
        "safe_max_y": 835,
        "target_lufs": "-18 LUFS",
    })


def _universal_vox_composable_lego_grammar_block(job: dict[str, Any] | None = None) -> str:
    skin = _channel_vox_skin_profile(job)
    chap_lock, _ = _resolve_lang_editorial_labels(job)
    preset_id = skin["preset_id"]
    max_y = skin["safe_max_y"]
    ast_cmd = (
        "node scripts/validate-vox-newsroom-ast.mjs"
        if preset_id == "forensic_noir_director_v2"
        else f"node scripts/validate-vox-newsroom-ast.mjs --preset {preset_id} --lang {str((job or {}).get('language') or 'ko').strip().lower()}"
    )
    if preset_id == "forensic_noir_director_v2":
        return f"""- **VOICE-TO-VOX PROMPT COMPILER × TACTILE VOX EDITORIAL DESK (`src/vox-studio/vox-editorial-desk/index.tsx` — `0%` CAMERA ZOOM-IN / ZOOM-OUT, `14` SPATIAL LAYOUTS × `9` CUT-AND-PASTE ENTRANCES) & PRECISION 3D SATELLITE CARTOGRAPHY (`<GeoJson3DMapStage>`) — SKIN-ISOLATED TO `{preset_id}`**:
  * **1. FLEXIBLE MEANING-DRIVEN PRIORITY #2 ROUTING (`0%` Fixed Template Count, `0%` Fixed Spacing/Cap)**: Never lock a fixed number of VOX templates/archetypes and never space VOX scenes at fixed intervals (`idx % N` or fixed percentage caps). Priority #1 is authentic archival footage (`REAL_FTG`); whenever a segment lacks authentic archival footage, **VOX illustration (`<Desk>` or `<GeoJson3DMapStage>`) is mandatory as Priority #2**, and AI imagery (`AI_IMAGE`) is strictly Priority #3 (last resort only).
  * **2. MỖI CẢNH LÀ ĐỘC LẬP. MỖI VIDEO LÀ ĐỘC LẬP (`0%` Desk Camera Zoom, `0%` 4-Corner Curls/Tapes `<PaperCurlCorners>`, `0%` Repeated Diagram Box `<BespokeSentenceDiagramByIndex>`, `100%` Real Flow Cutouts & Purposeful Sentence Illustration)**:
    - **ABSOLUTE BAN ON `<Desk>` CAMERA ZOOM, 4-CORNER PAPER CURLS/TAPES & REPEATED DIAGRAM BOXES**: Never use camera zoom-in or zoom-out (`camAt` with `z != 1.0`, `scale()` camera push/pull, or `buildTopologyWaypoints`) on `<Desk>/<World>` (the paper tabletop camera is 100% locked overhead at `z = 1.0`, `transform: 'none'`). Never render 4-corner curls or 4-corner tapes (`<PaperCurlCorners>` / `<PaperPeelSheetReveal>`), and never wrap or repeat `<BespokeVoiceDrivenDeskScene>`, `<BespokeSentenceDiagramByIndex>`, or `renderSentenceIllustrationSvg` (every VOX scene must compose real cutouts, archival photos, and concise Korean labels directly for its specific voice sentence).
    - **ANALYZE SENTENCE FIRST -> DRAW EVIDENCE WITH GOOGLE FLOW FIRST (`CofiStudioMediaFactoryRunner`) & CUT OUT RGBA (`rembg`) -> PLACE REAL FOOTAGE VIDEO OR PHOTO IN CENTER [PRIORITY TO VIDEO] (`left: 620..665, top: 200..235, w: 645, h: 410`) + SURROUNDING FLOW CUTOUTS IN 4 CORNERS (`w: 450..465, h: 330..335`) -> CONTEXT-ADAPTIVE ENTRANCE MOTIONS & VOCAL EMPHASIS**: For every sentence that uses VOX, the AI Agent MUST follow the verified 4-step workflow: (1) **Read & Understand Sentence (`voice_meaning` & `illustration_content`)**: Identify the exact physical evidence described in that sentence (`0%` mismatched props from other sentences, `0%` decorative clutter); (2) **Draw Evidence With Google Flow FIRST (`CofiStudioMediaFactoryRunner`) & Segment RGBA (`rembg`)**: Generate high-detail studio forensic macro images of the sentence's specific physical evidence via Google Flow on a clean solid light background, segment them into crisp RGBA cutouts (`rembg` -> `prop_XX.png`, `cutout_XX.png`), inspect every PNG via `read_file`, and prepare clean archival case media (a clean cropped video clip when available, or `plate_XX.jpg`) (`0%` fake geometric PIL boxes, `0%` repeated SVG rectangle/circle boxes); (3) **Canonical 1920x1080 Tabletop Layout — Real Footage Video or Photo in Center (Priority to Video) + Cutout Evidence Around**: Keep the exact current style and layout — place **1 large real archival case media hero in the dead center of `<Desk>`** (`w = 620..660, h = 395..420`, `left = 620..665, top = 200..235`), **which can be EITHER a Real Footage Video OR a Real Footage Photo, with PRIORITY given to Real Footage Video (`<VoxVideoPaper>`, `<VoxPhotoPaper videoSrc={{...}}>`, or `<RedBackedTornPhoto videoSrc={{...}}>`) whenever a clean video clip is available**, falling back to `<VoxPhotoPaper>` / `<RedBackedTornPhoto>` photo when only still media exists; and arrange **in the 4 surrounding corners** (`left: 64..106` on the left, `left: 1350..1385` on the right) **2 large RGBA Flow cutout props** (`<DieCutSticker w={{450..465}} h={{330..335}} />`), **1 concise Korean note card / clipping / tag** (`<IndexCard>`, `<TornClipping>`, `<TornPostageStrip>`, `<EyeletArchiveTag>`, `<Label>`, `fontSize: 20..24`), and **1 classification stamp** (`<Stamp size={{36}} />`), with `0%` overlap and safe bounds `[60..1860, 38..845]`; (4) **Context-Adaptive 12fps Entrance Motions & Vocal Emphasis (`hiệu ứng xuất hiện & cách nhấn mạnh tùy biến theo bối cảnh từng câu voice`)**: Customize the entrance timing/order (`at={{0}}`, `t1`, `t2`, `t3`), `<SlideIn from="...">` / `voxDiverseEntry12` directions (`scissors_slide_left`, `scissors_slide_right`, `slap_drop_top`, `sticker_peel_up`, `unroll_scroll_down`, `accordion_fold_left`, `accordion_fold_right`, `diagonal_toss_spin`, `fan_deal_bottom`), and focal emphasis tools (`<RedCircle>` when pointing out a target, `<OpticalLoupe>`, `<TwistedRedYarn>`, `<RedLine>`, `<DimensionBracket>`, `<Highlight>`, `<Underline>`, `<Stamp>`) according to the context and how each spoken voice sentence emphasizes different points, with **`0` consecutive VOX scenes repeating the same entrance sequence**. Every single item on screen must have a clear purpose illustrating the spoken sentence (`0%` decorative clutter).
  * **3. Locked Overhead Warm Paper Desk & Contrast BlackCard**: Render inside `<Desk>` (`V.bgDesk = #E4DDCF` warm editorial paper desk + `#voxGrain` `opacity: 0.22`) or `<BlackCard inset={{38}}>` (`#1B1B1A` for dark contrast pivots) as a locked overhead tabletop (`z = 1.0`, `0%` zoom-in/zoom-out, `0%` curled corners), keeping {chap_lock} (`100%` case-accurate Korean, `0%` English sample text) and safe viewport bounds **`[60 <= x <= 1860, 40 <= y <= {max_y}]`**.
  * **4. 4 IRONCLAD 3D SATELLITE NAVIGATION MAP LAWS (`<GeoJson3DMapStage>`)**: (1) **100% Voice-Matched Movement & Pursuit Routing (`0%` periodic `idx % N` placement)** — deploy `<GeoJson3DMapStage>` ONLY on spoken sentences describing suspect escape/infiltration routes OR police dispatch/dragnet/stakeout/extradition routes; (2) **100% Exact Real-World WGS84 Coordinates & Origin->Destination Fidelity (`0.00px` drift)** clearly displaying the coordinates spoken in the voice; (3) **Authentic Road/Rail Multi-Vertex Polylines (`>= 12..40` vertices, `0%` synthetic sine curves)** with directional navigation arrows (`headPt` + chevrons) and smooth 3D camera trajectory (`pitchDeg`, `bearingDeg`) following the route; (4) **Frameless Optical-Stroke Typography (`0%` crude dark AI boxes)**.
  * **5. Mandatory `vox_scene_manifest.json` Sentence Contract & AST Gate**: Every VOX beat in `vox_scene_manifest.json` MUST declare `voice_meaning`, `spatial_layout`, `entry_reveal`, `cut_and_paste_plan`, `motion_purpose_for_sentence`, `t1_action`, `t2_action`, `t3_action`, and `spatial_lock_targets`, pass `{ast_cmd}` with `0` errors, and pass 3-frame (`15%`, `50%`, `85%`) visual inspection via `read_file`."""
    return f"""- **SYSTEM-WIDE BESPOKE VOX TABLETOP & CUT-AND-PASTE GRAMMAR (`VOX_COMPOSABLE_LEGO_GRAMMAR_DIRECTOR_V13` — `0%` CAMERA ZOOM-IN / ZOOM-OUT, `14` SPATIAL LAYOUTS × `9` CUT-AND-PASTE ENTRANCES, SKIN-ISOLATED TO `{preset_id}`)**:
  * **Channel Skin Isolation & Zero Camera Zoom (`z = 1.0` Locked Overhead Stage)**: Render strictly in {skin['skin_label']} with {skin['palette']} via {skin['toolkit']}, keeping {chap_lock} and safe viewport bounds **`[60 <= x <= 1860, 40 <= y <= {max_y}]`**. **STRICTLY FORBID any camera zoom-in or zoom-out on VOX (`0%` `zoom != 1.0`, `0%` `camAt` zoom, `0%` `buildTopologyWaypoints` zoom)!**
  * **Tier 1 (Loose Atomic Lego Props & 12fps Cut-and-Paste Entrances)**: Compose each Vox scene freely from loose atomic building blocks (`SlideIn` / `voxDiverseEntry12` across 9 tactile 12fps cut-and-paste entrance modes: `scissors_slide_left`, `scissors_slide_right`, `slap_drop_top`, `sticker_peel_up`, `unroll_scroll_down`, `accordion_fold_left`, `accordion_fold_right`, `diagonal_toss_spin`, `fan_deal_bottom`) + `GeoJson3DMapStage` (`>= 3072x2048` wide Esri satellite + **authentic multi-vertex OpenStreetMap Overpass GeoJSON `>= 12` vertices** + `4x` satellite loupe, `0%` camera zoom).
  * **Tier 2 (18 Semantic Visual Verbs × 14 Spatial Layouts × 9 Cut-and-Paste Entrances)**: Select the exact Semantic Visual Verb matching the mechanism of the spoken sentence (`CAUSAL_CHAIN`, `SPLIT_PARADOX`, `SINGLE_EVIDENCE_AUTOPSY`, `SCALE_MULTIPLICATION`, `CRASH_TIMELINE`, `COUNTDOWN_PRESSURE`, `NETWORK_GRAPH`, `DUAL_ERA_LOCK`, `TIMELINE_SCRUB`, `DECLASSIFY_REVEAL`, `FORGERY_MICRO_COMPARE`, `PROPORTION_SHOCK`, `GEO_VECTOR_PURSUIT`, `GEO_PARADOX_FORK`, `SPATIAL_CHECKPOINT`, `DOCUMENT_CASCADE`, `HEADLINE_SHOCKWAVE`, `EVIDENCE_CONVERGENCE`) paired with a unique **Spatial Layout (`bố cục` from the 14 tabletop geometries)** and a unique **12fps Cut-and-Paste Entrance Sequence (`hiệu ứng cắt dán xuất hiện`)** synced across the full spoken `Whisper words[]` span (`frame(15%) != frame(50%) != frame(85%)`).
  * **Tier 3 (Hard Anti-Repetition Gate)**: Enforce **0 consecutive VOX scenes repeating the same Spatial Layout (`bố cục`) or the same Cut-and-Paste Entrance Sequence (`hiệu ứng cắt dán xuất hiện`)**, **0 repeated `VoxVisualVerb` within any 5 consecutive VOX scenes**, and `max_uses = 1` per prop/cutout, verified with `0` errors by `{ast_cmd}`."""


def _director_v2_mindset_and_screening_law(job: dict[str, Any] | None = None) -> str:
    style_label, ref_name = _resolve_profile_ai_style_info(job)
    ref_clause = f"`{style_label}` + `{ref_name}`" if ref_name else f"`{style_label}`"
    return f"""
DIRECTOR V2 INVESTIGATIVE JOURNALISM, EYE-VERIFIED FOOTAGE & V23 VIBE-MOTION × VOX-DIRECTOR PAPER-COLLAGE VOX CONSTITUTION (`forensic_noir_director_v2` V23):
- **PRIORITY #1 — 100% EYE-VERIFIED CASE ARCHIVAL FOOTAGE (`100%` CLEAN CROP OF THIRD-PARTY LOGOS & RUNNING TEXT, `100%` VOICE SENTENCE SEMANTIC MATCH, `0%` AUTOMATIC CUTTING OR AUTOMATIC SPLICING)**: Curate official CCTV broadcasts, police investigation archives, forensic labs, court trials, and exact historical case locations (`footage/S_F*.mp4`, `-an` + `volume={{0}}`, `3.0–5.0s/cut`, `Part A + Part B` for beats `>= 6.2s`, `max_uses = 1`, `dHash >= 14`, `time_gap >= 10.2s`). **3 IRONCLAD FOOTAGE LAWS**:
  * **1. 100% Eye-Verified Logo & Running-Text Crop**: For every source video, run `--probe-storyboard` to extract `STORYBOARD_<id>.jpg` and `GRID_<id>.jpg` (`100px` coordinate grid), open them with your own eyes (`read_file` / `vision_inspect_frames`), calibrate a subject-focused `16:9` `SAFE_CROP` (`--crop-mode "crop=W:H:X:Y"`) that crops out **100% of third-party logos/watermarks/QR codes (`logo bên khác`)** and **100% of third-party running text/tickers/chyrons/burned-in foreign subtitles (`chữ chạy bên khác`)**, and verify on post-crop `15% - 50% - 85%` contact sheets (`*_3frames.jpg` / `VERIFY_FTG_CLIPS_*.jpg`) that 0% studio hosts/anchors/presenters, 0% program intros/outros, and 0% third-party text or logos remain.
  * **2. 100% Eye-Verified Match With Spoken Sentence Meaning**: Inspect the frames by eye and ensure the image or video footage attached to a spoken sentence matches **100% of the content the sentence is talking about** (`--observed-content` matching `narration_text` 1-to-1, `eye_verified = true`). Whenever a sentence has no authentic footage matching 100% of its meaning, never pad with mismatched footage — route that sentence to **Priority #2 VOX illustration (`<Desk>` or `<GeoJson3DMapStage>`)** first, and **Priority #3 AI Image** only as the final fallback.
  * **3. Strict Ban on Automatic Cutting, Batch-Slicing One Video, and Context-Append Evasion (`CẤM TUYỆT ĐỐI DÙNG CODE TỰ ĐỘNG CẮT, CẮT TỊNH TIẾN HÀNG LOẠT 1 VIDEO HOẶC NỐI ĐUÔI VĂN MẪU`)**: Never run `--auto`, `auto_fetch_missing_beats`, blind offset math (`start + idx * 26s` / `28s` / `duration * 0.32`), sequential batch-slicing of a single source video (`max <= 12` clips or `<= 25%` per source video), or appending boilerplate narration-context suffixes to `observed_content`.
  * **0% Desk Camera Zoom, 0% 4-Corner Paper Curls & 100% Independent Per-Sentence Spatial Layout + Cut-and-Paste Entrance**: Read the exact spoken Korean sentence (`clauses[0..2]`), compile `voice_meaning -> illustration_content -> vox_prompt`, and design a 100% unique meaning, motion, **Spatial Layout (`bố cục` from the 14 tabletop architectures)**, **12fps Cut-and-Paste Entrance Effect (`hiệu ứng cắt dán xuất hiện` via `<SlideIn from="...">` / `voxDiverseEntry12` across 9 tactile paper modes)**, cut-and-paste assembly (`cách cắt dán`), and red circle (`<RedCircle>` — ONLY if needed when the sentence singles out a specific target) on `<Desk>` (`#E4DDCF` + `#voxGrain` `opacity: 0.22` or `<BlackCard inset={{38}}>` `#1B1B1A`, **100% locked overhead `z = 1.0` camera — NEVER use zoom-in or zoom-out on `<Desk>`, NEVER use `<PaperCurlCorners>`, NEVER wrap in `<BespokeVoiceDrivenDeskScene>`**, `0` consecutive scenes repeating the same layout or entrance sequence, `100%` case-accurate Korean, `0%` decorative filler props) or `<GeoJson3DMapStage>` (3D satellite navigation map strictly for suspect/police movement routes with exact real-world WGS84 coordinates, authentic road/rail polylines, directional route arrows, smooth 3D camera trajectory, and frameless optical-stroke labels with `0%` crude dark AI boxes).
- **PRIORITY #3 LAST RESORT — CLOSED-ROOM AI ISOLATION ({ref_clause} / `<beat_id>_ai_keyframe.jpg`)**: Use AI keyframes (`scale >= 1.105`) ONLY as the final fallback (Priority #3) for closed-room psychological moments where neither real footage nor VOX illustration applies.
- **MANDATORY V23 EYE-VERIFICATION GATE**: Pass `node scripts/validate-vox-newsroom-ast.mjs` with `0` violations, verify every `REAL_FTG` clip (`dHash >= 14`, `max_uses = 1`) has 0 third-party logos/running text and 100% voice-sentence semantic match via eye-inspected contact sheets, and visually inspect 3 rendered frames (`15%`, `50%`, `85%`) of every VOX scene (`frame(15%) != frame(50%) != frame(85%)`) before Master export.
"""


def _vox_and_remotion_architecture_direction(job: dict[str, Any] | None = None) -> str:
    if is_creative_audio_drama_job(job):
        return """K-AUDIO DRAMA 2-GEAR CINEMA & CHARACTER-SHEET REMOTION ARCHITECTURE (`kr_goodnight_cinema_drama` — FAST-CUT COLD-OPEN HOOK `0:00–0:45` + SERENE BEDTIME BODY `0:45–END`, ZERO VOX GRAPHICS, ZERO 3D MAPS):
- **ROLE 0 — LATEST VOICE SYNC & STALE CACHE PURGE**: Verify `mtime`, `duration`, and `sha256` of the newest `narration.wav` + `voice_manifest.json` (`0.94x` warm bedtime cadence) in workspace, sync to `public/jobs/<job_id>/audio/narration.wav`, rebuild `subtitles.srt`, and purge stale `.m4a` / chunk caches.
- **GEAR 1 (`00:00–00:45` COLD-OPEN HOOK BEFORE `CT_01` `제1장` — HIGH-RETENTION K-DRAMA TEASER CHOREOGRAPHY)**:
  * **NEVER open `0:00` on a black `FramelessCinemaTextBeat` chapter card!** Frame 0 MUST open immediately on a high-contrast 35mm confrontation shot matching the `0:00` shock dialogue line.
  * **Multi-Angle Fast-Cut Hook Pacing (`2.4s–4.2s/cut`, `10–14` cuts in first 42s)**: Split Cold-Open beats (`>= 4.8s`) into rapid `Part A + Part B` sub-shots (`Medium Confrontation` -> `Tight Macro Prop/Hands` -> `Close-Up Eyes Reaction`), cut with crisp `2–3 frame` J-cut snaps (`0%` sleepy 26-frame dissolves in Hook), apply decisive optical motion (`cold_open_push_punch` `1.00 -> 1.105`, `cold_open_pull_shock` `1.115 -> 1.008`, `cold_open_macro_cutin`), richer chiaroscuro contrast (`contrast(1.09) saturate(1.06)`), and score Segment 0 (`0:00–0:42`) with taut Solo Cello Suspense (`w03_dignity_tension_cello`, `-18.5 dB`) + a `1.2s` pre-curtain silence drop right before `CT_01` (`제1장`)!
- **GEAR 2 (`00:45–END` POST-HOOK STORY BODY — 80% WARM 35MM CINEMA + 15% CLEAN ATMOSPHERIC B-ROLL + 5% WARM IVORY CINEMA TEXT)**:
  1. **Priority #1 — 80% 35mm Warm Tungsten Cinema Keyframes (`media/ai/<beat_id>_ai_keyframe.jpg`)**: Locked 100% to the episode's self-generated **Flow Character Reference Sheet (`media/character_sheet/*.jpg`)** across all 6 Chapters (`ACT01..ACT06`). From `제1장` onward, settle into gentle slow Ken Burns (`1.00 -> 1.035`), `26-frame` warm cross-dissolves, and **Highlight Luma Ceiling `<= 215`** (`0%` white flash cuts for dark-room bedtime viewing).
  2. **Priority #2 — 15% Lightweight Clean Atmospheric 4K B-Roll (`footage/S_F*.mp4`)**: Serene rain on windows, autumn leaves, warm streetlamps, pouring hot tea, ceramic kilns, piano strings, Hanok eaves (`0%` news broadcasts, `0%` third-party faces, `0%` logos/subtitles, muted `-an`, `brightness(0.84)`).
  3. **Priority #3 — 5% Warm Ivory `FramelessCinemaTextBeat.tsx` (`CT_01` `제1장`..`제6장` Chapter Curtains & Key Quotes)**: Warm serif typography (`Noto Serif KR` / `Nanum Myeongjo`) on deep warm charcoal-amber (`#16120E`), hiding `<LiveSubtitleOverlay>` underneath, **`0%` VOX Editorial Desk (`<Desk>`), `0%` `<GeoJson3DMapStage>` 3D pursuit maps, and `0%` startle SFX hits**."""
    if _is_non_vox_devotional_job(job):
        return """SACRED DEVOTIONAL MULTI-FOOTAGE & 3D FLOATING SANCTUARY ARCHITECTURE (`sacred_devotional` — ZERO VOX GRAPHICS):
- **ROLE 0 — LATEST VOICE SYNC & STALE CACHE PURGE**: Verify `mtime`, `duration`, and `sha256` of the newest `narration.wav` + `voice_manifest.json` in workspace, sync to `public/jobs/<job_id>/audio/narration.wav`, rebuild `subtitles.srt`, and purge stale `.m4a` / chunk caches.
- **SACRED GOLDEN SANCTUARY COMPOSITING (`CofiRemotion`)**: Layer 80%–85% peaceful 4K real nature/candlelight/sanctuary footage with warm golden diffusion beneath the frameless 3D drop-shadow floating Jesus guide frame (`24K` metallic-gold silhouette aura, gentle cross-dissolves across narrative poses) and clean Korean subtitles underneath (`0%` Vox graphic boards, `0%` chapter popup cards, `0%` callout boxes, `3.5–5.0s` piano/strings fade-out)."""

    skin = _channel_vox_skin_profile(job)
    preset_id = skin["preset_id"]
    style_label, ref_name = _resolve_profile_ai_style_info(job)
    ref_clause = f"`{style_label}` + `{ref_name}`" if ref_name else f"`{style_label}`"
    _, ai_disc = _resolve_lang_editorial_labels(job)
    extra_v2 = ("\n" + _director_v2_mindset_and_screening_law(job)) if preset_id == "forensic_noir_director_v2" else ""
    return f"""CHANNEL-ISOLATED SKIN + SYSTEM-WIDE 3-TIER COMPOSABLE LEGO VOX & REMOTION ARCHITECTURE (`{preset_id}` V13):
- **ROLE 0 — LATEST VOICE + WHISPER WORD-TIMESTAMP SYNC & STALE CACHE PURGE (`REMOTION_MASTER_EDITOR_ROLE`)**:
  * Before editing or exporting, ALWAYS verify `mtime`, `duration`, and `sha256` of the newest `narration.wav` + `voice_manifest.json` (including per-beat `words[]` timestamps) in workspace, sync to `public/jobs/<job_id>/audio/narration.wav`, rebuild `subtitles.srt` + balanced `clauseWindows` against the newest voice timing, and purge all stale `.m4a` / chunk render caches.
- **DIVISION OF LABOR**:
  1. **`AUTHENTIC_FOOTAGE_CURATOR` (`documentary.edit_footage_fetcher` — Priority #1 Eye-Verified Archival Footage)**:
     - Curates 100% eye-verified (`STORYBOARD_<id>.jpg` + `GRID_<id>.jpg` + `15% - 50% - 85%` `*_3frames.jpg`) real video cuts (`footage/S_F*.mp4`, `-an` + `volume={{0}}`, `max_uses = 1` by filename & `dHash/HSV/LAB`, `0` frozen tails, `0%` third-party logos/running text/burned-in foreign subs/TV studio anchors, `100%` semantic match with the spoken sentence, and `0%` automatic cutting or automatic splicing).
  2. **`VOX_COMPOSABLE_LEGO_GRAMMAR_DIRECTOR_V13` ({skin['skin_label']} — {skin['vox_ratio_desc']})**:
{_universal_vox_composable_lego_grammar_block(job)}
  3. **`FRAMELESS_DARK_CINEMA_MOTION_TEXT` (`{skin.get('motion_text_module', 'CofiRemotion/src/components/FramelessCinemaTextBeat.tsx')}` — {skin['cinema_text_desc']})**:
     - Enforces the **3 Ironclad Motion Text Laws**: (1) **Zero Monoculture (`0%` repeating 1 motion renderer, 1 font, or 1 layout across the video)** — vary `showroomRenderer`, `fontStyle` (`broadcast_sans`, `editorial_serif`, `monumental_verdict`, `forensic_mono`, `dossier_typewriter`), and `layoutVariant` (`center_monolith`, `editorial_left`, `editorial_right`, `split_horizon`, `diagonal_cascade`, `verdict_pillar`), never repeating the same renderer or `(fontStyle, layoutVariant)` consecutively; (2) **Flexible Narrative Drop-Point Placement per Job (`0%` mechanical periodic spacing every 7–11 beats)** — attach strictly at genuine narrative drop points (`?` paradox questions, turning-point metrics, dual-identity contradictions, or climax arrest/verdict statements, `0` adjacent consecutive beats, hiding `<SubtitleOverlay>` underneath); (3) **100% Context-Matched Font, Color & Entry Motion** — match `fontStyle`, `accentColor` (`crimson`, `amber`, `ice`, `ivory`, `mono`), `layoutVariant`, and `showroomRenderer` 100% to the sentence's meaning (`0%` blood-red `crimson` on victim mourning; `0%` `editorial_metric_monolith` without a real spoken number).
  4. **`REMOTION_MASTER_EDITOR_ROLE` & `BROADCAST_SUBTITLE_AND_SOUND_DIRECTOR` (`CofiRemotion`)**:
     - Sequences the 4-layer timeline ({skin['footage_ratio_desc']} + {skin['vox_ratio_desc']} Composable Lego Vox + {skin['cinema_text_desc']} + {skin['ai_ratio_desc']} `<beat_id>_ai_keyframe.jpg` via {ref_clause} with frameless `{ai_disc}` disclosure).
     - Mixes **12–16 Story-Arc BGM segments** across the 8 mood pools (`{skin['target_lufs']}`, 3s crossfades, `-41dBFS` / `volume: 0.015` analog room-tone floor on pre-twist drops, active fetch via `search_and_fetch_contextual_bgm`) + **100% Real Recorded Sentence-Specific Foley SFX (`select_vox_clause_sfx_events`)** (`2–3` distinct physical Foley SFX per VOX scene from the 41 real Foley files in `public/audio_library/sfx/` matched to `t1 -> t2 -> t3` clauses — `0` synthetic `aevalsrc` audio, `0` repeating one SFX across VOX beats, `0` SFX on real footage or still AI keyframes), frameless word-locked broadcast subtitles (`0` subtitle during silence), and **100% intact closing narration + `3.8s` outro BGM fade-out**.{extra_v2}"""


def _asset_variety_direction(job: dict[str, Any] | None = None) -> str:
    if is_creative_audio_drama_job(job):
        return """K-AUDIO DRAMA ASSET VARIETY, FLOW CHARACTER CONTINUITY & BEDTIME VISUAL HYGIENE (`kr_goodnight_cinema_drama`):
- Read the complete 6-Chapter (`제1장`..`제6장`) audio drama script end-to-end first.
- **Character Sheet Continuity (`media/character_sheet/*.jpg`)**: Every AI scene depicting recurring characters MUST preserve their facial identity, age (`50–70` graceful realism), hairstyle, and chapter wardrobe from the episode's Flow Character Reference Sheet (`0%` random face swapping between scenes, `0%` chibi/cartoon).
- **80 / 15 / 5 Visual Mix (`max_uses = 1` per asset, `dHash >= 12` between scenes)**: Sequence ~80% bespoke 1-to-1 35mm warm cinema keyframes (`Highlight Luma <= 215`), ~15% clean 4K atmospheric Korean/seasonal/craft B-roll (`0%` logos/subtitles/faces), and ~5% warm serif Chapter/Quote cards (`26-frame` smooth cross-dissolves, `0%` VOX boards, `0%` strobe/flash)."""
    if _is_non_vox_devotional_job(job):
        return """CONTEMPLATIVE DEVOTIONAL VISUAL VARIETY & HYGIENE (`sacred_devotional`):
- Read the complete 7-chapter devotional script end-to-end first. Curate 60–90+ clean 4K nature, candlelight, morning mist, rain, and sanctuary B-roll clips (`max_uses = 1` per sequence, `0%` logos/subtitles/anchors) blended warmly beneath the frameless 3D floating guide frame, supplemented by 12%–18% warm 35mm realistic devotional AI stills (`0%` stickman/2D cartoons, `0%` Vox graphic boards)."""

    lang = str((job or {}).get("language") or "ko").strip().lower()
    style_label, ref_name = _resolve_profile_ai_style_info(job)
    ref_clause = f"`{style_label}` + `{ref_name}`" if ref_name else f"`{style_label}`"
    chap_lock, ai_disc = _resolve_lang_editorial_labels(job)
    typo_target = "Korean Hangul (`40–66px`)" if lang == "ko" else "target-language typography (`40–66px`)"
    skin = _channel_vox_skin_profile(job)
    is_v2 = skin["preset_id"] == "forensic_noir_director_v2"

    priority_1_scope = (
        "Curate Priority #1 authentic eye-verified archival footage (`footage/S_F*.mp4`, `--probe-storyboard` + `100px` grid `crop=W:H:X:Y` + `15%-50%-85%` contact sheet) where every attached clip is inspected by the AI Agent's eyes to guarantee: (1) 100% of third-party logos and third-party running text are cleanly cropped out, (2) the visual matches 100% of what the spoken sentence is talking about, and (3) 0% automatic cutting or automatic splicing is used (**whenever no authentic footage matches 100% of a sentence, route to Priority #2 VOX illustration**)."
        if is_v2
        else f"Curate {skin['footage_ratio_desc']} 100% eye-verified authentic footage matching 100% of the spoken sentence with 100% of third-party logos and running text cropped out (`0%` automatic cutting or splicing)."
    )

    priority_2_and_3 = (
        f"""  2. PRIORITY 2 — VOICE-TO-VOX PROMPT COMPILER × TACTILE VOX EDITORIAL DESK (`src/vox-studio/vox-editorial-desk/index.tsx` — `0%` CAMERA ZOOM-IN/ZOOM-OUT, `14` SPATIAL LAYOUTS × `9` CUT-AND-PASTE ENTRANCES) & 3D SATELLITE GIS (`<GeoJson3DMapStage>`) ({skin['skin_label']} — {skin['vox_ratio_desc']}, `[60 <= x <= 1860, 40 <= y <= {skin['safe_max_y']}]` SAFE BOUNDS, AST-VERIFIED):
     - **VOICE-TO-VOX PROMPT × `vox-editorial-desk` CHOREOGRAPHY (`0%` ZOOM-IN / ZOOM-OUT)**: Stage `<Desk>` (`#E4DDCF` + `#voxGrain` `opacity: 0.22`), optional `<BlackCard inset={{38}}>` (`#1B1B1A`), and a **100% locked overhead tabletop (`z = 1.0`, `0%` camera zoom-in or zoom-out!)** with 12fps (`step12` / `p12`) paper & ink primitives from `src/vox-studio/vox-editorial-desk/index.tsx` (`<SlideIn>`, `voxDiverseEntry12`, `<VoxVideoPaper>`, `<VoxPhotoPaper>`, true RGBA `<DieCutSticker>`, `<TornClipping>`, `<IndexCard>`, `<Stamp>`, `<Label>`, `<Highlight>`, `<RedLine>`, `<RedCircle>`, `<Underline>`, `<DimensionBracket>`, `<OpticalLoupe>`, `<Tape>`) + `<GeoJson3DMapStage>`, varying the **Spatial Layout (`bố cục` across 14 tabletop architectures)** and **12fps Cut-and-Paste Entrance Effect (`hiệu ứng cắt dán xuất hiện` across 9 tactile paper modes)** per sentence (`0` consecutive scenes repeating the same layout or entrance sequence, `frame(15%) != frame(50%) != frame(85%)`, verified via `read_file` and passing `validate-vox-newsroom-ast.mjs`).
  3. PRIORITY 3 — DARK FRAMELESS CINEMA MOTION TEXT (`FramelessCinemaTextBeat.tsx`, {skin['cinema_text_desc']}) & PROFILE-LOCKED 1-TO-1 AI KEYFRAMES (`<beat_id>_ai_keyframe.jpg`, {skin['ai_ratio_desc']}):
     - Deploy `src/components/FramelessCinemaTextBeat.tsx` (`abyssal_film_grain`, `dimmed_prev_shot`, `acoustic_trace` — `0` boxes, `0` adjacent consecutive beats, automatically hiding `<SubtitleOverlay>` underneath) for pivotal paradox questions, shocking metrics, and Act turns.
     - Pre-generate 100% of 1-to-1 reserve AI keyframes upfront in Step 5 using the profile's locked style ({ref_clause}, `max_uses = 1`), and deploy `<beat_id>_ai_keyframe.jpg` ONLY on closed-room / unfilmed moments with frameless `{ai_disc}` disclosure."""
        if is_v2
        else f"""  2. PRIORITY 2 — CHANNEL-ISOLATED SKIN + BESPOKE VOX TABLETOP & CUT-AND-PASTE GRAMMAR ({skin['skin_label']} — {skin['vox_ratio_desc']}, `[60 <= x <= 1860, 40 <= y <= {skin['safe_max_y']}]` SAFE BOUNDS, AST-VERIFIED):
     - **LOOSE ATOMIC PROPS × 18 SEMANTIC VISUAL VERBS (`@voxVerb`) × 14 SPATIAL LAYOUTS × 9 CUT-AND-PASTE ENTRANCES (`0%` CAMERA ZOOM-IN/ZOOM-OUT, {chap_lock} & `y <= {skin['safe_max_y']}px`)**: Compose loose atomic props in `{skin['preset_id']}` skin ({skin['toolkit']}, mandatory `imageSrc=` `2.4x` `OpticalGlassLoupe`, `GeoJson3DMapStage` wide `>= 3072x2048` Esri + real multi-vertex OSM Overpass GeoJSON `>= 12` pts, `0%` camera zoom-in or zoom-out `z = 1.0`) matched 1-to-1 to the spoken sentence's Semantic Visual Verb (`CAUSAL_CHAIN`, `SPLIT_PARADOX`, `SINGLE_EVIDENCE_AUTOPSY`, `SCALE_MULTIPLICATION`, `CRASH_TIMELINE`, `COUNTDOWN_PRESSURE`, `NETWORK_GRAPH`, `DUAL_ERA_LOCK`, etc.), varying the **Spatial Layout (`bố cục`)** and **12fps Cut-and-Paste Entrance (`hiệu ứng cắt dán xuất hiện`)** on every VOX scene (`0` consecutive repeats of layout or entrance, `0` verb repeats in 5 consecutive VOX scenes, `frame(15%) != frame(50%) != frame(85%)`, passing `validate-vox-newsroom-ast.mjs`).
  3. PRIORITY 3 — DARK FRAMELESS CINEMA MOTION TEXT (`FramelessCinemaTextBeat.tsx`, {skin['cinema_text_desc']}) & PROFILE-LOCKED 1-TO-1 AI KEYFRAMES (`<beat_id>_ai_keyframe.jpg`, {skin['ai_ratio_desc']}):
     - Deploy `src/components/FramelessCinemaTextBeat.tsx` (`abyssal_film_grain`, `dimmed_prev_shot`, `acoustic_trace` — `0` boxes, `0` adjacent consecutive beats, automatically hiding `<SubtitleOverlay>` underneath) for pivotal paradox questions, shocking metrics, and Act turns.
     - Pre-generate 100% of 1-to-1 reserve AI keyframes upfront in Step 5 using the profile's locked style ({ref_clause}, `max_uses = 1`), and deploy `<beat_id>_ai_keyframe.jpg` ONLY on closed-room / unfilmed moments with frameless `{ai_disc}` disclosure."""
    )

    return f"""ASSET VARIETY AND INTENTIONAL REUSE — FULL-SCRIPT-DRIVEN VISUAL & BESPOKE VOX TABLETOP ARCHITECTURE (`{skin['preset_id']}` V13)
- ASSET VARIETY & INTENTIONAL REUSE RULES:
  * Prefer unused or less-used valid assets across the sequence so adjacent beats stay visually fresh, but do not force every downloaded/approved asset onto the timeline when it would hurt semantic accuracy or emotional pacing.
  * Never repeat the exact same file, crop, or source time range as lazy filler across multiple beats unless staged as a deliberate callback with clear narrative purpose.
- READ FULL SCRIPT FIRST & SEMANTIC VOICE-TO-VISUAL ROUTING:
  * Read the entire script (`script.md` + `voice_manifest.json` + `visual_manifest.json`) end-to-end before routing any beat or designing any Vox scene:
    - **(a) Pure Clean Real Footage (`2–3 cuts`, `3.0–5.0s/cut`, `max_uses = 1`)**: Authentic footage matching 100% of the exact country, institution, venue, person, or setting spoken in the narration AND passing the **3-Frame Visual Hygiene Audit (`12% — 50% — 85%`)**.
    - **(b) Hybrid Split (`[Part A: Clean Real Context 3.5–4.5s] + [Part B: 1-to-1 AI Keyframe 3.5–4.5s]`)**: First half shows verified real location/institution and second half depicts a closed-room action (`{ai_disc}` shown solely on the AI sub-shot).
    - **(c) Pure 1-to-1 Scene-Locked AI Keyframe (`<beat_id>_ai_keyframe.jpg`)**: Closed-room psychology, private dialogue, or unfilmed moments (`max_uses = 1`).
    - **(d) Bespoke VOX Tabletop & Cut-and-Paste Motion (`0%` Camera Zoom-In / Zoom-Out, `14` Spatial Layouts × `9` Cut-and-Paste Entrances)**: Deployed as mandatory Priority #2 whenever authentic real footage is absent, illuminating 3D satellite GIS routes, chronologies, financial/technical/forensic mechanisms, causal chains, 50/50 claim-vs-evidence paradoxes, network graphs, or single-exhibit autopsies using `{skin['preset_id']}`'s isolated skin with `0%` camera zoom-in/zoom-out and sentence-specific spatial layouts + 12fps cut-and-paste entrances.
  * **Senior-Friendly (45–70yo) Readability**: Calm, dignified pacing (zero strobe/flashing), clean rectangular photo crops, and high-contrast {typo_target}.
- THREE-TIER VISUAL & VOX HIERARCHY:
  1. PRIORITY 1 — 100% VOICE-MATCHED REAL FOOTAGE + 3-FRAME (`12% — 50% — 85%`) HYGIENE (`footage/S_F*.mp4` — CRISP 3–5s CUTS, ZERO LOGOS/FOREIGN SUBS, ZERO ANCHORS/VLOGGERS):
     - {priority_1_scope}
     - **MANDATORY 3-FRAME (`12% — 50% — 85%`) VISUAL AUDIT & TOP-CROP HYGIENE**: Inspect early (`12%`), middle (`50%`), and late (`85%`) frames of every candidate clip: `0%` station/channel logos or watermarks, `0%` burned-in third-party subtitles, `0%` TV anchors, studio hosts, or tourist vloggers, and `0%` wrong-country signs/institutions. When authentic archival footage carries burned-in bottom captions, top-crop the clean upper `80–82%` action region (`crop=iw:ih*0.80:0:0,scale=1920:1080`) and re-verify all 3 frames.
     - **CRISP 3–4.8s SUB-SHOTS & ZERO FREEZE OVERRUN**: Split multi-clause beats into `Part A + Part B` (`clip_frames >= subshot_frames + outCrossfadeFrames + 24`) so crossfades never overrun video tails.
     - **PERCEPTUAL DE-DUPLICATION (`dHash + HSV + LAB`)**: Enforce `max_uses = 1` by filename and perceptual signature (`dHash hamming >= 10`, `HSV corr < 0.80`, `LAB diff >= 14.0`, `source_group(shot[k]) != source_group(shot[k-1])`), mute source audio (`-an`), and apply smooth optical camera motion (`1.005 -> 1.065`).
{priority_2_and_3}
"""


def _native_motion_semantic_direction(job: dict[str, Any] | None = None) -> str:
    if is_creative_audio_drama_job(job):
        return """K-AUDIO DRAMA SUBTITLE COMFORT, WARM NOCTURNE CHAMBER BGM & BEDTIME OUTRO (`kr_goodnight_cinema_drama`):
- **Senior-Friendly Warm Frameless Subtitles (`58px–62px`)**: Render clean, frameless warm-ivory (`#F5EFE6`) Korean subtitles (`Noto Serif KR` / `Pretendard`, soft dark optical stroke, `y <= 880px`, `Highlight Luma <= 215`) synced strictly to active speech (`0` subtitle during silence, hidden automatically on `FramelessCinemaTextBeat` chapter curtains).
- **Warm Nocturne Chamber BGM (`warm_nocturne_chamber` — `-22` to `-25dB` under voice, `-16.0 LUFS` integrated)**: Score across 16–24 gentle narrative segments using acoustic solo piano, warm cello, classical guitar, and soft rain/tea ambience (`3.5s` crossfades; **STRICTLY FORBID dark forensic noir drones, crime-thriller tension pulses, sirens, or loud chapter-hit SFX `zero_startle_sfx = true`**).
- **Bedtime Outro Integrity**: Preserve 100% of the closing narration (`0%` spoken subscribe/like CTA) followed by a serene **`4.0s` warm piano/cello fade-out**."""
    if _is_non_vox_devotional_job(job):
        return """SACRED DEVOTIONAL SUBTITLE & AUDIO INTEGRITY (`sacred_devotional`):
- Render clean, frameless Korean devotional subtitles beneath the 3D floating sanctuary frame synced to `speech_end_sec` (`0%` header bars, `0%` chapter popups, `0%` callout boxes).
- Mix warm Piano & Strings devotional BGM (`-18dB` to `-22dB`) with gentle crystal-chime transitions, preserve 100% complete closing prayer narration, and hold a peaceful `3.5–5.0s` musical fade-out."""

    lang = str((job or {}).get("language") or "ko").strip().lower()
    skin = _channel_vox_skin_profile(job)
    is_v2 = skin["preset_id"] == "forensic_noir_director_v2"
    if lang == "ko" and is_v2:
        subtitle_and_outro = """- BROADCAST KOREAN SUBTITLE DIRECTOR ROLE V2.2 (`BROADCAST_KOREAN_SUBTITLE_DIRECTOR_V22` — CHUẨN PHỤ ĐỀ ĐIỆN ẢNH CỠ LỚN 62PX–66PX KHÔNG HỘP & NGẮT 1–2 DÒNG CÂN ĐỐI CHO HỒ SƠ V2):
  * **100% Phụ đề điện ảnh CỠ LỚN KHÔNG ĐÓNG HỘP (`FRAMELESS LARGE BROADCAST SUBTITLES` — `background: 'transparent'`, `border: 'none'`, `boxShadow: 'none'`, `fontSize: 64px` [`62px–66px`, tối thiểu `58px`], `fontWeight: 800`, `lineHeight: 1.28`, `letterSpacing: -0.4`)**: Không đặt phụ đề, tiêu đề chương (`제1막`..`제5막`), CTA hay nhãn minh bạch AI (`재연 · 이해를 돕기 위한 이미지`) bên trong hộp nền tối bo góc; dùng viền nét mực quang học sắc nét (`WebkitTextStroke: '6.5px rgba(8, 8, 10, 0.96)'`, `paintOrder: 'stroke fill'`) kết hợp bóng đổ đa lớp (`textShadow`) và tô sáng từ khóa/con số chính bằng màu vàng `#fde047`.
  * **Ngắt cụm phụ đề 1–2 dòng cân đối theo nhịp hơi thở (`14–26 ký tự / cụm`, tự động ngắt 2 dòng cân đối tối đa `14–15 ký tự/dòng` nếu dài, vùng an toàn Vox `y <= 785px`)**: Tự động ẩn `<SubtitleOverlay>` trên toàn bộ các cảnh `FramelessCinemaTextBeat`.
  * **Đồng bộ chính xác với dấu thời gian giọng đọc (`Whisper words[]` & `speech_end_sec`)**: Cửa sổ phụ đề chạy chuẩn xác theo âm đọc thực tế và tắt gọn tại `speech_end_sec`.
- OUTRO TIMELINE INTEGRITY, LINEAR -14.8 LUFS AUDIO & 3.8s BGM FADE-OUT LAW:
  * Trộn âm thanh tuyến tính chuẩn `-14.8 LUFS`; câu kết màn (`closing narration`) hoàn tất trọn vẹn 100%, và để dư **`3.8s` nhạc nền hạ màn (fade-out)** sau khi dứt lời thoại cuối."""
    elif lang == "ko":
        subtitle_and_outro = """- BROADCAST KOREAN SUBTITLE DIRECTOR ROLE (`BROADCAST_KOREAN_SUBTITLE_DIRECTOR` — CHUẨN PHỤ ĐỀ ĐIỆN ẢNH KHÔNG HỘP 52PX & NGẮT CỤM NGẮN KHỚP VOICE CHO CÁC KÊNH TIẾNG HÀN):
  * **100% Phụ đề điện ảnh KHÔNG ĐÓNG HỘP (`FRAMELESS BROADCAST SUBTITLES` — `background: 'transparent'`, `border: 'none'`, `boxShadow: 'none'`, `fontSize: 52px`, `fontWeight: 800`, `lineHeight: 1.3`, `letterSpacing: -0.4`)**: Dùng viền nét mực quang học sắc nét (`WebkitTextStroke: '5.5px rgba(8, 8, 10, 0.96)'`, `paintOrder: 'stroke fill'`) kết hợp `textShadow`, tô sáng từ khóa/con số chính (`#fde047` / `#facc15`), và tự động ẩn `<SubtitleOverlay>` trên các cảnh `FramelessCinemaTextBeat`.
  * **Ngắt cụm phụ đề ngắn theo nhịp hơi thở (`10–16 ký tự / 2–4 cụm từ eojeol`, 1 dòng gọn gàng, `1.0s–2.0s/cụm`)**: Chia bằng `split_korean_narration_into_short_clauses(text, max_chars=16)` và tính trọng số theo `estimate_spoken_korean_weight`, kết thúc đúng tại `speech_end_sec`.
- OUTRO TIMELINE INTEGRITY & 3.8s BGM FADE-OUT LAW:
  * Câu kết màn (`closing narration`) hoàn tất trọn vẹn 100%, để dư **`3.8s` nhạc nền hạ màn (fade-out)** sau khi dứt lời thoại cuối."""
    else:
        subtitle_and_outro = """- FRAMELESS BROADCAST SUBTITLE PACING & CLAUSE WINDOWING:
  * Frameless cinema broadcast subtitles (`background: transparent`, `border: none`, `paint-order: stroke fill`, optical text stroke + multi-layer drop-shadow), key metrics and entity names highlighted, automatically hidden during `FramelessCinemaTextBeat`.
  * Breath-paced clause windowing (2–4 words per display window, aligned strictly to active speech ending at `speech_end_sec`).
- OUTRO TIMELINE INTEGRITY & 3.8s BGM FADE-OUT LAW:
  * Ensure closing narration completes 100% intact with zero truncated syllables, followed by a `3.8s` musical fade-out tail."""

    lang_strict_note = (
        "**100% 한글 ON-SCREEN TYPOGRAPHY (`제1막`..`제5막`, ZERO HANJA LEAKS, ZERO ENGLISH HUD BADGES)**."
        if lang == "ko"
        else "**100% TARGET-LANGUAGE BROADCAST TYPOGRAPHY**."
    )
    font_family_note = (
        "`Noto Serif KR`, `Nanum Myeongjo` & `Pretendard` from `public/fonts/`"
        if lang == "ko"
        else "editorial serif & clean grotesque sans typography from `public/fonts/` matching the target language"
    )
    checklist_block = (
        """- MANDATORY PRE-PUBLISH CHECKLIST:
  * `[ ]` **Kịch bản:** Mọi nhân vật/manh mối xuất hiện ở phần đầu đã có kết cục rõ ràng và đúng 100% DNA của hồ sơ kênh chưa?
  * `[ ]` **Vox Tabletop (`0%` Zoom-In/Zoom-Out) & AST:** Toàn bộ cảnh VOX đã khóa góc máy phẳng `z = 1.0` (`0%` zoom-in/zoom-out), biến thiên **14 Bố cục không gian (`bố cục` / `spatial_layout`) × 9 Hiệu ứng cắt dán xuất hiện `12fps` (`hiệu ứng cắt dán xuất hiện` / `voxDiverseEntry12`)** (`0` cảnh liên tiếp trùng bố cục hoặc hiệu ứng xuất hiện), và vượt qua `validate-vox-newsroom-ast.mjs` với `0` lỗi chưa?
  * `[ ]` **Âm thanh & Phần kết:** Giọng đọc tự nhiên không vấp số đếm, BGM 8-Mood đúng LUFS kênh (nền `-41dBFS` trước twist), câu kết trọn vẹn 100% + `3.8s` fade-out chưa?"""
        if lang in {"ko", "vi"}
        else """- MANDATORY PRE-PUBLISH CHECKLIST BEFORE FINAL EXPORT:
  * `[ ]` **Script:** Are all introduced figures and exhibits resolved cleanly in 100% of this Channel Profile's DNA?
  * `[ ]` **Vox Tabletop (`0%` Zoom-In/Zoom-Out) & AST:** Does every VOX scene lock its overhead camera to `z = 1.0` (`0%` zoom-in/zoom-out), vary across the 14 Spatial Layouts × 9 Cut-and-Paste Entrances (`0` consecutive repeats of layout or entrance), and pass `validate-vox-newsroom-ast.mjs` with `0` errors?
  * `[ ]` **Audio & Outro:** Is voiceover cadence natural, 8-Mood BGM normalized with `-41dBFS` pre-twist room-tone floor, and final sentence 100% intact with a `3.8s` fade-out?"""
    )

    return f"""NATIVE MOTION SEMANTIC COVERAGE — REMOTION TIMELINE COMPOSITING, SKIN-ISOLATED `{skin['preset_id']}` PALETTE, BESPOKE VOX TABLETOP (`0%` ZOOM-IN/ZOOM-OUT), 8-MOOD STORY-ARC BGM & 100% MOTION-BOUND SFX
- NATIVE MOTION SEMANTIC COVERAGE & MULTI-CLAUSE PROGRESSION:
  * Every native VOX / motion-design beat must visually cover the meaningful clauses of its spoken sentence (`t1 -> t2 -> t3` across `Whisper words[]`) rather than holding a single generic native graphic across the whole beat. Self-check each native beat across early (`15%`), middle (`50%`), and late (`85%`) frames so every clause adds concrete visual information.
- CHANNEL-ISOLATED SKIN & BESPOKE VOX TABLETOP LAW (`validate-vox-newsroom-ast.mjs` + `critic_loops.py`):
  * **Isolated Channel Skin (`{skin['preset_id']}`)**: {skin['skin_label']} — lock {skin['palette']} and {font_family_note} inside safe viewport bounds **`[60 <= x <= 1860, 40 <= y <= {skin['safe_max_y']}]`**. {lang_strict_note}
  * **Bespoke VOX Tabletop & Cut-and-Paste Law (`0%` Camera Zoom-In / Zoom-Out)**: Every Vox scene locks its overhead camera to `z = 1.0` (**STRICTLY FORBID any camera zoom-in or zoom-out on VOX!**) and varies ONLY its **Spatial Layout (`bố cục` across 14 tabletop architectures)** and **12fps Cut-and-Paste Entrance Effect (`hiệu ứng cắt dán xuất hiện` via `<SlideIn from="...">` / `voxDiverseEntry12` across 9 tactile paper modes)** across the **18 Semantic Visual Verbs (`@voxVerb`)**, transforming progressively across `Whisper words[]` (`frame(15%) != frame(50%) != frame(85%)`, `0` consecutive VOX scenes repeating the same layout or cut-and-paste entrance sequence, `0` verb repeats in 5 consecutive VOX scenes, `0%` `*_ai_keyframe.jpg` mascots inside archival/audit Vox stages).
  * **Footage & AI Camera Treatment**: Apply smooth optical camera movement (`1.005 -> 1.065`) on real video footage and AI stills (`scale >= 1.105` on closed-room Noir Chibi keyframes).
- 8-MOOD STORY-ARC BGM ENGINE & 100% MOTION-BOUND FOLEY SFX (`documentary/audio_library_manager.py` & `public/audio_library/`):
  * **12–16 Story-Arc BGM Schedule (`build_story_arc_bgm_schedule`)**: Score each episode across **12–16 narrative segments** (~1.5–2.2m each) matched to emotional shifts across the 8 mood pools (`01_mystery_hook` .. `08_memorial_epilogue`, normalized to `{skin['target_lufs']}`), with **3-second smooth crossfades (`crossfadeFrames = 90`)** and **2–3 Pre-Twist BGM Drops (`2.5–3.0s` ducked to `-41dBFS` / `volume: 0.015` analog room-tone floor — never `0.000` digital zero)**.
  * **MANDATORY ACTIVE BGM SEARCH & DOWNLOAD ON MISMATCH / ANTI-REUSE (`search_and_fetch_contextual_bgm`)**: Whenever a segment's atmosphere is not matched by unused tracks in `data/bgm_usage_history.json`, call `search_and_fetch_contextual_bgm(mood, context_query, target_filename)` to fetch and LUFS-normalize fresh instrumental BGM immediately.
  * **100% Real Recorded Sentence-Specific Foley SFX (`select_vox_clause_sfx_events`)**: Emit `2–3` distinct, real recorded physical Foley SFX (from the 41 real Foley files in `public/audio_library/sfx/`) matched to each spoken clause's object/action (`t1 -> t2 -> t3`) on **Vox scenes, `FramelessCinemaTextBeat`, 3D GIS Map flights, and Chapter transitions** (`0` synthetic code-generated `aevalsrc` audio, `0` repeating one SFX across VOX beats, `0` SFX on real video footage and still AI keyframes).
{subtitle_and_outro}
{checklist_block}
"""


def _official_remotion_agent_skills_direction() -> str:
    return """
OFFICIAL REMOTION AGENT SKILLS & HIGH-END VOX DIVISION — REQUIRED
- The Remotion authority for this project is the official Remotion Agent Skills distribution from `remotion-dev/skills`.
- Load `remotion-best-practices` first. For React/Remotion implementation, load `remotion-markup`. Use `remotion-docs` to look up current APIs. Do not invent Remotion APIs; verify component props and hooks against official docs. Use `remotion-studio` for Studio-specific work and `remotion-render` when rendering or exporting.
- Follow the router in `remotion-best-practices` and load the official sub-skills relevant to the active task, such as captions, multimedia, maps, or interactivity.
- For True Crime, Real Esri Satellite GIS, Tactile Paper-Craft Forensic Dossiers, Archival Press, and Voice-Synced Animated Vox (`vox/VOX_*.mp4`), follow `skills/cofi-vox-blender-director/SKILL.md`.
- **LOCKED 30 FPS STUDIO LIVE PREVIEW (MANDATORY FOR ALL COMPOSITIONS — ZERO FRAME DROPS, 100% RENDER QUALITY)**:
  * Always render video clips via `<StudioSmoothVideo>` (`src/components/StudioSmoothVideo.tsx`) passing `jobId`, `relPath`, `muted` (`true` on all footage/Vox clips to prevent residual audio bleed), and `renderFilter` for optical CSS color-grading/blur filters (automatically routes to 30fps `fastdecode` `_preview` proxies & `960x540` `maxCanvasSinkFrameSize` in live Studio while rendering 100% canonical `1920x1080` + full CSS color grade on final MP4 export).
  * Never call `useCurrentFrame()` at the root of an episode composition containing 150–300 `<Sequence>` children; wrap `<MasterAudioLayer />` and `<VisualTimelineLayer />` in `React.memo` (`showInTimeline={false}` on shot/SFX sequences, `layout="none"` on `<Audio>` sequences), pre-compile subtitle highlight `RegExp`/`Set` constants at module scope, and confine `useCurrentFrame()` strictly to leaf overlay components (`LiveChapterCardOverlay`, `LiveSubtitleOverlay`).
"""


def _human_intrigue_narrative_direction(job: dict[str, Any] | None = None) -> str:
    lang = str((job or {}).get("language") or "ko").strip().lower()
    if is_creative_audio_drama_job(job):
        if lang != "ko":
            return """ORIGINAL K-AUDIO DRAMA & FAMILY/CRAFT DIGNITY NARRATIVE DIRECTION (`creative_audio_drama` — ZERO CRIME DOSSIER FORCING):
- Craft a 100% original, deeply human 6-Chapter audio drama (`ACT01..ACT06`) grounded in authentic Korean cultural/artistic craft lore and family/generational dignity (`0%` crime investigation reports, `0%` police pursuit formatting).
- Open in-media-res inside a concrete family or workshop moment where the protagonist's dignity is underestimated, establish clear Speaker-First dialogue (`hwaja_seonhaeng`), advance every chapter with fresh forward plot turns (Dual-Reversal at Chapters 3 and 5, `0%` summary padding), resolve every Chekhov prop and character cleanly by Chapter 6, and close on serene late-night warmth (`0%` spoken CTA).
"""
        return """ORIGINAL K-AUDIO DRAMA & FAMILY/CRAFT DIGNITY NARRATIVE DIRECTION (`creative_audio_drama` — 수사물 포맷 배제 · 6장 구조 심야 오디오 드라마):
- 이 프로젝트는 선택된 채널 프로필(`channel_profile_snapshot`)의 **심야 오디오 드라마 & 가족·장인 품격 회복 서사(6장 구조 `ACT01..ACT06`)** 헌법을 100% 따릅니다. 범죄 수사 기록이나 경찰 추격극 포맷을 절대 섞지 마십시오.
- **인물 바이블(`Character Bible`) & 전통·예술 장인 고증**: 등장인물 3~5명의 연령·성격·말투·복장을 일관되게 유지하고, 백자 도예·고미술 복원·피아노/첼로·나전칠기·다도·한옥 목수 등 실제 장인·예술 디테일을 사실적으로 녹여내십시오.
- **화자 선행(`화자 선행`) & 50~65세 존중 호칭**: 한 명의 성우(TTS)가 낭독해도 누가 말하는지 즉시 알 수 있도록 대사 앞에 반드시 화자와 행동/어조를 먼저 밝히고, 50~65세 인물을 `'노인'`, `'노부부'`, `'늙은이'`로 부르지 말고 직함·이름(`원장`, `선생`, `장인`, `... 씨`, `중년 부부`)으로 품격 있게 지칭하십시오.
- **체호프의 총(`Chekhov's Gun`) & 무자극 심야 엔딩(`0%` 구두 CTA)**: 제1~2장에 심어 둔 핵심 소품과 인물의 인과를 제5~6장에서 빠짐없이 회수하며, 구독·좋아요 요청 없이 평온한 여운으로 마무리하십시오.
"""
    niche_label, _ = _detect_documentary_niche_engine(job or {})
    from .quality import resolve_korean_profile_style_flags

    style_flags = resolve_korean_profile_style_flags(job)
    is_contemplative_or_custom = (
        style_flags["custom_register"]
        or "Spiritual" in niche_label
    )

    if is_contemplative_or_custom:
        if lang != "ko":
            return """PROFILE-DRIVEN CONTEMPLATIVE, ESSAY & CUSTOM-REGISTER NARRATIVE DIRECTION:
- Honor 100% of the active Channel Profile's own `editorial_dna`, `voice_and_structure`, `speech_register`, and `creative_brief`—never force crime-dossier or courtroom structures onto a contemplative, pastoral, cultural, or essay channel.
- Open with lived human warmth, sensory stillness, or a quiet emotional truth that invites the listener in immediately.
- Develop each movement organically according to `outline.json` with vivid imagery, sincere emotional pacing, coherent thematic resolution for every introduced motif, and natural spoken flow.
"""
        return """PROFILE-DRIVEN CONTEMPLATIVE, ESSAY & CUSTOM-REGISTER NARRATIVE DIRECTION (채널 프로필 고유 DNA 100% 존중 — 수사물 포맷 강제 금지):
- 이 프로젝트는 선택된 채널 프로필(`channel_profile_snapshot`)의 고유 장르·어조·문체(`voice_and_structure`, `editorial_dna`, `creative_brief`)를 최우선 헌법으로 따릅니다. 범죄 수사물이나 법정 판결문 구조를 억지로 적용하지 마십시오.
- 도입부부터 채널 성격에 맞는 깊이 있는 공감, 정서적 울림, 삶의 구체적 장면 또는 사유의 질문으로 청취자의 마음을 자연스럽게 여십시오.
- `outline.json`의 흐름을 따라 각 장(Act/Chapter)이 유기적인 감정 호흡으로 이어지게 작성하며, 초반에 꺼낸 일화·비유·인물은 끝까지 따뜻하고 일관되게 매듭지으십시오.
"""

    if lang != "ko":
        return """FACTUAL DOCUMENTARY NARRATIVE DIRECTION (100% REAL VERIFIED RECORD FIDELITY — ZERO COMPOSITE / ZERO FABRICATION)
- 100% VERIFIED REAL EVENT FIDELITY LAW (STRICT GROUNDING IN VERIFIED HISTORICAL, TECHNICAL & JUDICIAL RECORDS):
  * Every episode MUST be anchored 100% to real, verifiable events, cases, or subjects documented by official archives, primary records, or authoritative journalism matching this Channel Profile's domain.
  * STRICTLY FORBID composite reconstruction that stitches unrelated events together or invents fictional figures, fictional investigators, or artificially symmetrical AI numbers.
  * Maintain 100% realistic timelines and factual outcomes from documented records: never compress multi-year processes into implausible windows or invent unrecorded resolutions.
- Write original third-person documentary narration aligned with the active Channel Profile's tone, using sparse direct-address pivots only at genuine turning points. Start with a cold open grounded in a concrete scene, date, place, primary document, or pivotal action that introduces a real contradiction or reversal.
- Anchor the arc in human relationship mystery—such as hidden alliances, betrayal, secret romance, double lives, or high-stakes personal decisions—while keeping institutional history and background mechanics subordinate to concrete human stakes and verifiable evidence.
- Build each Act with clear causal progression (`scene/evidence -> mechanism -> obstacle/escalation -> breakthrough -> consequence or reversal`), to reopen curiosity gaps naturally at Act pivots and group related beats under a coherent `story_group`.
- CHEKHOV'S GUN LAW & NATURAL ROLE DESIGNATIONS: Every significant person, document, or clue introduced in early acts MUST reach a clear documented resolution, and individuals should be addressed naturally by verified professional title, official role, or age bracket without stereotypes.
"""
    return """FACTUAL DOCUMENTARY NARRATIVE DIRECTION (100% REAL VERIFIED RECORD FIDELITY — ZERO COMPOSITE / ZERO FABRICATION · 프로필 고유 DNA 준수)
- 100% VERIFIED REAL RECORD FIDELITY LAW (LUẬT SẮT BÁM SÁT 100% HỒ SƠ & SỰ KIỆN CÓ THẬT CỦA HỒ SƠ KÊNH — CẤM GHÉP VỤ VIỆC HAY BỊA SỐ LIỆU):
  * Mọi tập phim BẮT BUỘC bám sát 100% sự kiện, nhân vật, công trình hoặc vụ việc có thật được ghi nhận bởi hồ sơ chính thức, tài liệu lưu trữ hoặc báo chí chính thống đúng với ngách nội dung của hồ sơ kênh đang chọn.
  * TUYỆT ĐỐI CẤM "tổng hợp hư cấu (`종합 재구성`)" ghép nhiều sự kiện khác nhau làm một, bịa nhân vật không có thật, hoặc tự chế các con số AI chia chẵn đối xứng giả tạo.
  * Giữ đúng 100% dòng thời gian thực tế và kết cục thực tế theo hồ sơ gốc (không nén quá trình nhiều tháng/năm thành vài ngày vô lý, không tự tô hồng kết quả ngoài hồ sơ).
- Triển khai lời dẫn theo đúng ngôi kể và giọng điệu của hồ sơ kênh: mở màn trực diện (`Cold Open`) bằng một cảnh vật lý, mốc ngày tháng, địa điểm, tài liệu hoặc vật chứng cụ thể chứa đựng nghịch lý thực tế kéo người xem vào mạch câu chuyện.
- Xây dựng từng Hồi theo chuỗi nhân quả chặt chẽ (`hiện trường/dữ kiện -> giải phẫu cơ chế -> nút thắt/ngõ cụt -> manh mối đột phá -> hệ quả`), dùng chi tiết thật và con số kiểm chứng để tạo sức nặng thay cho tính từ hoa mỹ.
- CHEKHOV'S GUN LAW (NGUYÊN TẮC 'CHIẾC SÚNG CỦA CHEKHOV' — CẤM BỎ QUÊN NHÂN VẬT/MANH MỐI MỞ MÀN): Bất kỳ nhân vật, nhân chứng hay manh mối đáng chú ý nào được giới thiệu ở phần đầu/giữa bài BẮT BUỘC phải có vai trò hoặc kết cục rõ ràng. Nếu cần tiết chế chi tiết nhạy cảm để đảm bảo an toàn kiếm tiền (Monetization Safety), hãy khép lại số phận nhân vật đó bằng 1–2 câu tóm lược điềm tĩnh thay vì bỏ bẵng gây hổng logic.
- CULTURAL AGE & ROLE ADDRESSING LAW (XƯNG HÔ TRUNG TÍNH CHUẨN VĂN HÓA HÀN QUỐC): Tuyệt đối KHÔNG gọi người ở độ tuổi 50–65 là `"노부부"` hay `"노인"` gây gượng gạo; bắt buộc dùng danh xưng trung tính theo vai trò nghề nghiệp hoặc nhóm tuổi chuẩn xác (`"50대 후반 부부"`, `"중년 부부"`, hoặc chức danh/vai trò thực tế trong câu chuyện).
"""


EPISODE_OPENING_ARCHETYPES: tuple[dict[str, str], ...] = (
    {
        "id": "winner_paradox_double_life_anchor",
        "label_vi": "Mỏ neo Mốc Thời Gian Cụ Thể + Nghịch Lý Vỏ Bọc Hai Mặt & Hiện Trường Khóa Kín (00:00–03:30 — Công thức Winner Chuẩn DNA Kênh)",
        "act1_title_suffix_vi": "Mỏ Neo Mốc Thời Gian & Nghịch Lý Vỏ Bọc Hai Mặt",
        "opening_directive_vi": (
            "Mở màn trực diện theo đúng công thức Winner đã kiểm chứng của kênh (길광 76k, 벙어리 67k, 마한칭 48k, 바이인시 매점 45k, 남문촌 35k, 사오양, 가오청융): "
            "(1) BẮT BUỘC mở đầu ngay Câu 1 bằng MỐC THỜI GIAN CỤ THỂ (`YYYY년 M월 D일 [구체적 시각], [장소]...`) gắn liền với biến cố/hiện trường chấn động (ví dụ: `2016년 9월 29일 오전 일곱 시 삼십팔 분, 중국 윈난성 취징시 후이쩌현의 해발 이천사백 미터 산골 마을 예마촌 파출소 상황실에...`); CẤM tả cảnh thời tiết/môi trường lan man và CẤM bỏ trống mốc ngày tháng năm ở Câu 1; "
            "(2) ĐỐI CHIẾU KỸ VỚI CÁC VIDEO GẦN ĐÂY & VIDEO WIN ĐỂ 0% LẶP LẠI CHI TIẾT/MÔ-TÍP MỞ MÀN: Tuyệt đối cấm lặp lại mô-típ câu đầu của các tập gần đây (`현상금 ... 위안이 걸린 공안부 ... 수배령이 떨어졌습니다`, `험준한 산길 입구마다 폴리스 라인/차단봉이...`, `차량 트렁크가 열렸죠`); "
            "(3) Câu 2–4 tung ngay cú lật NGHỊCH LÝ 180 độ bằng `하지만 / 그런데` về Vỏ bọc Hai Mặt hoặc hành vi thái연 phi lý của nghi phạm ngay cùng thời điểm đó (0% lặp lại cùng một mốc ngày 2 lần trong Hồi 1, 0% lặp lại nguyên xi cảnh Hồi 1 ở Hồi 4); "
            "(4) Câu 5–7 đặt câu hỏi điều tra cốt lõi (`어떻게 ... 수 있었을까요?`) rồi dẫn thẳng vào diễn biến điều tra chi tiết, đồng thời đảm bảo 100% phát âm TTS tự nhiên (CẤM đọc mã số bản án Hán-Hàn kiểu `이공일칠 운공삼 형초 사십사 호`, CẤM lặp cụm đồng âm như `백구 킬로미터` quá 2 lần, và chỉ dùng tối đa 1 CTA duy nhất trong toàn bộ kịch bản)."
        ),
    },
)

EPISODE_CTA_RHETORICAL_FORMS: tuple[dict[str, str], ...] = (
    {
        "id": "flexible_mid_pause_or_closing_archive_note",
        "allow_explicit_cta": "true",
        "label_vi": "Linh Hoạt Theo Mạch Truyện: Gài Tinh Tế Ở Quãng Nghỉ Chuyển Giai Đoạn (08:00–12:00) Hoặc Bắt Buộc Khép Lại Hồ Sơ Cuối Video",
        "directive_vi": (
            "LINH HOẠT THEO NỘI DUNG CÂU CHUYỆN (KHÔNG KHÓA CỨNG 1 VỊ TRÍ HAY 1 CÂU CỐ ĐỊNH): "
            "Nếu ở khoảng phút 08:00–12:00 câu chuyện có điểm chuyển chương/quãng lặng tự nhiên (ví dụ chuyển năm, chuyển địa bàn điều tra), có thể lồng 1 câu dẫn dắt/lưu trữ hồ sơ thật tinh tế ngay tại đó; "
            "nếu mạch truyện ở giữa đang căng thẳng không tiện ngắt, thì BẮT BUỘC ở cuối video phải có 1 câu kết nối/mời đồng hành linh hoạt mọc thẳng từ chính tình tiết kết của vụ án này (tuyệt đối không để cả video 0% CTA và không dùng câu mẫu rập khuôn)."
        ),
    },
    {
        "id": "interrogative_viewer_perspective",
        "allow_explicit_cta": "true",
        "label_vi": "Câu Hỏi Mở Gợi Góc Nhìn Khán Giả Từ Tình Huống Câu Chuyện (Linh Hoạt Ở Nhịp Nghỉ Giữa Truyện Hoặc Bắt Buộc Cuối Video)",
        "directive_vi": (
            "LINH HOẠT THEO CÂU CHUYỆN (CÓ THỂ ĐẶT Ở QUÃNG LẶNG 08:00–12:00 NẾU HỢP MẠCH TRUYỆN, BẰNG KHÔNG BẮT BUỘC ĐẶT Ở CUỐI VIDEO): "
            "Dùng cấu trúc CÂU HỎI MỞ (`~걸까요?` / `~셨을까요?`) đặt người xem vào tình huống thực tế của vụ án và gợi nhẹ việc để lại góc nhìn hoặc theo dõi hồ sơ tiếp theo. "
            "CẤM TUYỆT ĐỐI câu khẩu lệnh cứng nhắc lặp lại `'구독과 좋아요/알림 설정을 눌러 주시기 바랍니다'`."
        ),
    },
    {
        "id": "declarative_archive_record_note",
        "allow_explicit_cta": "true",
        "label_vi": "Lời Ghi Chú Hồ Sơ Trầm Tĩnh Cuối Video (Bắt Buộc Cuối Bài Theo Sát Nội Dung Vụ Án — Không Cố Định Cứng 1 Câu)",
        "directive_vi": (
            "ĐẶT Ở ĐOẠN KHÉP LẠI TẬP PHIM (LINH HOẠT 100% THEO NỘI DUNG VỤ ÁN): "
            "Dùng câu trần thuật trầm tĩnh nối liền với vật chứng/dư âm cuối cùng của câu chuyện để mời khán giả cùng lưu giữ và theo dõi các hồ sơ điều tra tiếp theo của kênh bằng từ ngữ riêng của tập này. "
            "CẤM TUYỆT ĐỐI cấu trúc điều kiện công nghiệp `'~하시려면 구독과 좋아요/알림 설정을 눌러 주시기 바랍니다'`."
        ),
    },
    {
        "id": "story_breath_companion_or_finale_handoff",
        "allow_explicit_cta": "true",
        "label_vi": "Nhịp Thở Đồng Hành Giữa Quãng Lặng Năm Tháng (Nếu Hợp Mạch 08:00–12:00) Hoặc Lời Hẹn Cuối Hồ Sơ",
        "directive_vi": (
            "LINH HOẠT THEO CẤU TRÚC VỤ ÁN: Nếu vụ án có bước nhảy thời gian tự nhiên quanh phút 08:00–12:00 thì lồng khéo 1 câu đồng hành tự nhiên hòa vào mạch kể; "
            "nếu không đặt ở giữa bài thì BẮT BUỘC đặt 1 lời nhắn trầm tĩnh, giàu tính điện ảnh ở đoạn kết tập phim bám sát số phận/bằng chứng của vụ án (không cố định cứng 1 mẫu câu nào)."
        ),
    },
    {
        "id": "case_motif_narrative_handoff",
        "allow_explicit_cta": "true",
        "label_vi": "Liên Kết Mạch Ngầm Từ Chi Tiết Vụ Án Sang Hồ Sơ Tiếp Theo Ở Cuối Video (Linh Hoạt Theo Nội Dung)",
        "directive_vi": (
            "BẮT BUỘC Ở CUỐI VIDEO (HOẶC KẾT HỢP NHỊP ĐÁNH DẤU HỒ SƠ TINH TẾ Ở QUÃNG NGHỈ CHUYỂN HỒI NẾU MẠCH TRUYỆN CHO PHÉP): "
            "Từ chính chi tiết pháp y/tâm lý đặc thù của tập này, mở ra lời mời tự nhiên sang hành trình giải mã các hồ sơ thực tế tiếp theo trên kênh. "
            "CẤM TUYỆT ĐỐI các câu chỉ trỏ giao diện công nghiệp như `'지금 화면에 표시되고 있습니다'`, `'화면에 나타나는 다음 사건 파일'`, `'매주 실제 수사 기록과...'`."
        ),
    },
    {
        "id": "minimalist_noun_epilogue_nod",
        "allow_explicit_cta": "true",
        "label_vi": "Nhịp Kết Cô Đọng Tiết Chế & Cầu Nối Hồ Sơ Anh Em Cuối Video (Biến Hóa Linh Hoạt Theo Truyện)",
        "directive_vi": (
            "Ở ĐOẠN HẠ MÀN CUỐI VIDEO: Dùng 1 câu động từ ngắn sắc lẹm đúc kết vật chứng của vụ án kết hợp 1 câu đối chiếu tự nhiên sang một hồ sơ điều tra thực tế trên kênh và khép bằng câu hỏi mở (`~했을까요?`); "
            "TUYỆT ĐỐI CẤM đặt cụm danh từ cụt (`체언 종결`) nhại lại câu trước ở cuối đoạn, CẤM câu quảng cáo kênh chung chung (`'우리 채널에 기록된 다음 수사 파일에서 확인해 보시기 바랍니다'`), KHÔNG liệt kê combo nút bấm máy móc `'구독과 좋아요, 알림 설정'` và KHÔNG dùng câu chào mẫu `'끝까지 시청해 주셔서 감사합니다'`."
        ),
    },
)

EPISODE_ENDING_CADENCES: tuple[dict[str, str], ...] = (
    {
        "id": "human_aftermath_linger",
        "label_vi": "Dư âm Con người & Số phận Người ở lại",
        "act5_title_suffix_vi": "Khép Lại Hồ Sơ & Dư Âm Của Những Người Ở Lại",
        "ending_directive_vi": (
            "Đưa kết cục chính thức lên nửa đầu Hồi 5, dành trọn đoạn kết cho dư âm đời thực của những con người trong câu chuyện sau nhiều năm. "
            "Viết mới hoàn toàn 5 dòng cuối tập bám sát nhân vật của chính tập này — CẤM đúc kết đạo lý sáo rỗng và CẤM copy-paste 4 câu Outro mẫu."
        ),
    },
    {
        "id": "forensic_paradox_cut",
        "label_vi": "Đối lập Nghịch lý Chi tiết Nhỏ Bé vs. Hệ thống Khổng lồ",
        "act5_title_suffix_vi": "Sự Thật Cuối Cùng & Nghịch Lý Của Vết Tích Nhỏ Nhất",
        "ending_directive_vi": (
            "Gói gọn kết cục súc tích, sau đó khép lại bằng sự tương phản lạnh lùng giữa quy mô lớn của sự việc và đúng một chi tiết đời thực nhỏ bé đã quyết định tất cả (để dữ kiện tự lên tiếng, CẤM giảng đạo lý). "
            "Viết mới 100% 5 dòng cuối bằng từ vựng độc bản gắn với dữ kiện của riêng tập này."
        ),
    },
    {
        "id": "systemic_reality_ledger",
        "label_vi": "Thực tế Hậu Sự kiện & Câu hỏi Bỏ ngỏ",
        "act5_title_suffix_vi": "Sau Kết Cục & Sự Thật Còn Đọng Lại",
        "ending_directive_vi": (
            "Không kết theo công thức 4 bước rập khuôn! Sau khi nêu gọn kết quả thực tế, hãy nhìn thẳng vào hệ quả xã hội, thay đổi thể chế hoặc câu hỏi còn bỏ ngỏ. "
            "Viết lại hoàn toàn 5 dòng khép tập bằng cấu trúc câu mới, không lặp lại cụm '매주 실제 수사 기록과...' hay '지금 화면에 표시되고 있습니다'."
        ),
    },
    {
        "id": "scene_return_epilogue",
        "label_vi": "Vòng tròn Không gian — Trở lại Địa điểm Mở màn Hôm nay",
        "act5_title_suffix_vi": "Trở Lại Bối Cảnh Năm Ấy & Khép Màn",
        "ending_directive_vi": (
            "Nén gọn kết cục ở giữa Hồi 5, rồi đưa ống kính quay trở lại chính con phố, công trình hoặc căn phòng ở cảnh mở đầu sau khi biến cố đã đi qua để khép lại vòng tròn kể chuyện. "
            "Tuyệt đối không rao giảng câu đạo lý mẫu và viết mới 100% những dòng khép tập từ chi tiết không gian thực tế của tập phim."
        ),
    },
)


def _resolve_outro_mode(job: dict[str, Any] | None) -> str:
    if not isinstance(job, dict):
        return ""
    snap = job.get("channel_profile_snapshot") if isinstance(job.get("channel_profile_snapshot"), dict) else {}
    ed = snap.get("editorial_dna") if isinstance(snap.get("editorial_dna"), dict) else {}
    cta_arch = ed.get("cta_architecture") if isinstance(ed.get("cta_architecture"), dict) else {}
    locked_stream = str(ed.get("locked_single_stream") or snap.get("locked_single_stream") or "").strip().lower()
    if locked_stream == "stream_1_financial_vault":
        return "standalone_case_closure"
    mode = str(
        job.get("outro_mode")
        or ed.get("outro_mode")
        or cta_arch.get("outro_mode")
        or ""
    ).strip().lower()
    if mode:
        return mode
    own_ch = snap.get("own_channel") if isinstance(snap.get("own_channel"), dict) else {}
    own_dna = own_ch.get("dna") if isinstance(own_ch.get("dna"), dict) else {}
    if not (own_dna.get("winner_titles") or own_ch.get("videos")):
        return "standalone_case_closure"
    if _is_director_v2_true_crime_job(job):
        return "sibling_case_retention_bridge"
    return ""


def _collect_channel_sibling_cases(job: dict[str, Any] | None, *, limit: int = 8) -> list[str]:
    """Return real published/archived sibling case titles from this profile's own_channel & topic_memory (excluding current episode)."""
    if not isinstance(job, dict):
        return []
    snap = job.get("channel_profile_snapshot") if isinstance(job.get("channel_profile_snapshot"), dict) else {}
    ed = snap.get("editorial_dna") if isinstance(snap.get("editorial_dna"), dict) else {}
    locked_stream = str(ed.get("locked_single_stream") or snap.get("locked_single_stream") or "").strip().lower()
    cur_id = str(job.get("id") or job.get("job_id") or "").strip()
    cur_blob = f"{job.get('title') or ''} {job.get('topic') or ''}"
    cur_ko_tokens = {
        tok
        for tok in re.findall(r"[가-힣]{3,}", cur_blob)
        if tok not in {"중국", "실화", "사건", "수배범", "미제사건", "추적", "전말", "진실", "충격"}
    }
    seen: set[str] = set()
    siblings: list[str] = []

    def _add_candidate(raw_label: str) -> None:
        cleaned = re.sub(r"\s*\([^()]*[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ][^()]*\)\s*$", "", str(raw_label or "")).strip()
        if not cleaned or len(cleaned) < 8:
            return
        if any(tok in cleaned for tok in cur_ko_tokens):
            return
        if locked_stream == "stream_2_violent_disappearance" and re.search(r"(?:금고|수송차|은행|국채|증권|예금|어음)", cleaned):
            return
        # Scrub any legacy yellow-dollar words from historical titles before feeding into prompt
        if re.search(r"(?:살인마|연쇄살인|시신\s*훼손|토막|참수)", cleaned):
            return
        norm_key = re.sub(r"[^가-힣0-9A-Za-z]", "", cleaned)[:24]
        if not norm_key or norm_key in seen:
            return
        seen.add(norm_key)
        siblings.append(cleaned)

    own_ch = snap.get("own_channel") if isinstance(snap.get("own_channel"), dict) else {}
    own_dna = own_ch.get("dna") if isinstance(own_ch.get("dna"), dict) else {}
    for w in own_dna.get("winner_titles") or []:
        if isinstance(w, dict) and w.get("title"):
            _add_candidate(str(w["title"]))
            if len(siblings) >= limit:
                return siblings
    for tm in snap.get("topic_memory") or []:
        if not isinstance(tm, dict):
            continue
        if cur_id and str(tm.get("job_id") or "").strip() == cur_id:
            continue
        _add_candidate(str(tm.get("topic") or tm.get("title") or ""))
        if len(siblings) >= limit:
            return siblings
    return siblings


def _rank_topic_fitted_opening_archetypes(job: dict[str, Any]) -> list[dict[str, str]]:
    """Select the subset of the 8 Cold-Open Hook Archetypes best matched to THIS specific topic's anatomy."""
    brief = job.get("creative_brief") if isinstance(job.get("creative_brief"), dict) else {}
    explicit_hook_id = str(brief.get("hook_archetype") or "").strip()
    by_id = {item["id"]: item for item in EPISODE_OPENING_ARCHETYPES}
    if explicit_hook_id in by_id:
        return [by_id[explicit_hook_id]]

    blob = " ".join(
        [
            str(job.get("title") or ""),
            str(job.get("topic") or ""),
            str(job.get("notes") or ""),
            str(brief.get("opening_hook") or ""),
            str(brief.get("custom_rules") or ""),
        ]
    ).lower()

    candidate_ids: list[str] = []
    if any(k in blob for k in ("두 얼굴", "주지 스님", "회장", "원장", "주방", "맞선", "배우", "벙어리", "택시기사", "부국장", "위장", "신분", "성형", "hai mặt", "vỏ bọc", "đội lốt", "giả câm", "화장품")):
        candidate_ids.extend(["double_life_unmasking", "last_ordinary_routine", "chilling_verbatim_line"])
    if any(k in blob for k in ("8분", "48시간", "72시간", "8시간", "12시간", "58시간", "76시간", "전산망", "마감", "금요일", "시한", "đếm ngược", "phút trước", "nối mạng")):
        candidate_ids.extend(["countdown_system_breach", "locked_room_vault_paradox", "scale_absurdity_collision"])
    if any(k in blob for k in ("금고", "통장", "봉인", "흠집 하나 없이", "거울 화면", "가짜 은행", "가짜 vip", "어음", "신문지", "텅스텐", "két sắt", "phong bì", "sổ tiết kiệm", "밀실")):
        candidate_ids.extend(["locked_room_vault_paradox", "micro_forensic_anomaly", "scale_absurdity_collision"])
    if any(k in blob for k in ("복권", "카지노", "점심 한 끼", "가죽공장", "현금 슈퍼마켓", "수송차", "빚만 갚고", "vé số", "trả nợ", "siêu thị tiền mặt")):
        candidate_ids.extend(["scale_absurdity_collision", "chilling_verbatim_line", "countdown_system_breach"])
    if any(k in blob for k in ("담배꽁초", "시계", "태엽", "타이어", "페인트", "기름 한 방울", "송장", "섬유", "납땜", "엔진 번호", "달력", "암호 공책", "vi lượng", "dây cót", "vết lốp")):
        candidate_ids.extend(["micro_forensic_anomaly", "cold_archive_match", "last_ordinary_routine"])
    if any(k in blob for k in ("자백서", "자수", "편지", "재심", "누명", "쌍둥이", "유전자 가계도", "봉투", "20년", "26년", "28년", "minh oan", "tự thú", "thư")):
        candidate_ids.extend(["chilling_verbatim_line", "cold_archive_match", "micro_forensic_anomaly"])

    deduped = [by_id[cid] for cid in dict.fromkeys(candidate_ids) if cid in by_id]
    if len(deduped) < 4:
        for item in EPISODE_OPENING_ARCHETYPES:
            if item not in deduped:
                deduped.append(item)
    return deduped


def select_episode_narrative_variant(job: dict[str, Any] | None = None) -> dict[str, str]:
    """Deterministically select a topic-matched Cold-Open Hook Archetype (from 8 modes), CTA form, and ending cadence per episode."""
    job = job if isinstance(job, dict) else {}
    brief = job.get("creative_brief") if isinstance(job.get("creative_brief"), dict) else {}
    explicit_idx = job.get("structural_variant_index")
    if explicit_idx is None:
        explicit_idx = brief.get("structural_variant_index")
    if explicit_idx is not None:
        try:
            idx = int(explicit_idx)
            opening = EPISODE_OPENING_ARCHETYPES[idx % len(EPISODE_OPENING_ARCHETYPES)]
            cta = EPISODE_CTA_RHETORICAL_FORMS[idx % len(EPISODE_CTA_RHETORICAL_FORMS)]
            ending = EPISODE_ENDING_CADENCES[idx % len(EPISODE_ENDING_CADENCES)]
        except (TypeError, ValueError):
            explicit_idx = None
    if explicit_idx is None:
        seed_material = "::".join(
            [
                str(job.get("id") or "").strip(),
                str(job.get("title") or "").strip(),
                str(job.get("notes") or "")[:80].strip(),
                str(brief.get("opening_hook") or "")[:80].strip(),
            ]
        )
        if not seed_material.replace(":", ""):
            seed_material = "default-episode-seed"
        digest = hashlib.sha256(seed_material.encode("utf-8")).digest()
        fitted_pool = _rank_topic_fitted_opening_archetypes(job)
        opening = fitted_pool[int.from_bytes(digest[0:2], "big") % len(fitted_pool)]
        if _resolve_outro_mode(job) == "sibling_case_retention_bridge":
            cta = next(
                item for item in EPISODE_CTA_RHETORICAL_FORMS if item["id"] == "case_motif_narrative_handoff"
            )
        else:
            cta = EPISODE_CTA_RHETORICAL_FORMS[int.from_bytes(digest[2:4], "big") % len(EPISODE_CTA_RHETORICAL_FORMS)]
        ending = EPISODE_ENDING_CADENCES[int.from_bytes(digest[4:6], "big") % len(EPISODE_ENDING_CADENCES)]
    return {
        "opening_mode": opening["id"],
        "opening_label_vi": opening["label_vi"],
        "act1_title_suffix_vi": opening["act1_title_suffix_vi"],
        "opening_directive_vi": opening["opening_directive_vi"],
        "cta_rhetorical_form": cta["id"],
        "allow_explicit_cta": cta["allow_explicit_cta"],
        "cta_form_label_vi": cta["label_vi"],
        "cta_form_directive_vi": cta["directive_vi"],
        "ending_mode": ending["id"],
        "ending_label_vi": ending["label_vi"],
        "act5_title_suffix_vi": ending["act5_title_suffix_vi"],
        "ending_directive_vi": ending["ending_directive_vi"],
    }


AUDIO_DRAMA_OPENING_ARCHETYPES: tuple[dict[str, str], ...] = (
    {
        "id": "open_01_public_wager_insult",
        "label_vi": "Mở 1 — Lời Thách Cược & Sỉ Nhục Công Khai (공개 모욕·내기형)",
        "directive_vi": "Mở ngay giây 0:00 bằng câu thoại thách thức/miệt thị hoặc cá cược danh dự giữa bàn tiệc/phòng khách (화자 선행), kèm hành động vật lý đẩy kỷ vật ra mép bàn mà 0% lộ danh hiệu thật của nhân vật chính.",
        "keywords": "상견례 동서 시댁 내기 무시 학벌 고졸 결혼식",
    },
    {
        "id": "open_02_quiet_parting_declaration",
        "label_vi": "Mở 2 — Tờ Giấy Đặt Xuống Bàn Ăn Sáng (조용한 결별 선언형)",
        "directive_vi": "Mở ngay giây 0:00 bằng lời tuyên bố buông bỏ điềm tĩnh đến lạnh người của người vợ/người mẹ khi đặt chiếc chìa khóa hoặc tờ giấy từ khước xuống bàn ăn sau 30 năm nhẫn nhịn, khiến cả nhà sững sờ.",
        "keywords": "황혼 졸혼 이혼 남편 삼십 년 열쇠 결별 홀로서기",
    },
    {
        "id": "open_03_discarded_heirloom_chest",
        "label_vi": "Mở 3 — Chiếc Rương Cũ Bị Đẩy Ra Rìa (버려진 유품형)",
        "directive_vi": "Mở ngay giây 0:00 bằng câu thoại tranh giành tài sản bạc tỷ của các con/anh chị em, khi họ đẩy chiếc hộp gỗ/cuốn sổ cũ kỹ không ai thèm lấy về phía nhân vật chính mà không hề biết giá trị thật bên trong.",
        "keywords": "유품 유산 장녀 자식 형제 궤짝 상자 통장 참회",
    },
    {
        "id": "open_04_89th_minute_emergency_call",
        "label_vi": "Mở 4 — Cuộc Gọi Khẩn Cấp Phút 89 (절체절명 위기형)",
        "directive_vi": "Mở ngay giây 0:00 bằng tiếng kêu thất thanh hoặc lời cầu cứu khẩn cấp trong hậu trường khi cổ vật/quốc yến gặp sự cố chí mạng 2 tiếng trước giờ khai mạc, buộc phải tìm một cái tên đã ẩn tích hàng chục năm.",
        "keywords": "국빈 만찬 복원 국보 위기 개막 다급한 전화 대타",
    },
    {
        "id": "open_05_ten_year_reunion_reversal",
        "label_vi": "Mở 5 — Chạm Mặt Trên Ghế Thẩm Định (십 년 만의 재회형)",
        "directive_vi": "Mở ngay giây 0:00 bằng câu nói ngạo mạn của kẻ từng ruồng bỏ nhân vật chính năm xưa ngay trước cửa phòng xét duyệt tối cao, không hề biết người đang ngồi sau bức bình phong thẩm định là ai.",
        "keywords": "심사 재회 십 년 쫓겨난 병풍 위원장 명인",
    },
    {
        "id": "open_06_unsolvable_master_testament",
        "label_vi": "Mở 6 — Di Ngôn / Đề Bài Không Ai Giải Nổi (비밀 유언·과제형)",
        "directive_vi": "Mở ngay giây 0:00 bằng câu đọc điều khoản di chúc kỳ lạ hoặc bài toán tay nghề hóc búa của bậc đại sư quá cố khiến những kẻ cướp công tái mặt vì không ai giải nổi.",
        "keywords": "유언 스승 비법 과제 후계자 진품 가짜 제자",
    },
)

AUDIO_DRAMA_NARRATIVE_SPINES: tuple[dict[str, Any], ...] = (
    {
        "id": "spine_a_hidden_master_2tier_counterstrike",
        "label_vi": "Xương sống A — Ẩn Danh Phản Kích & Bẫy Nghề 2 Tầng (6 Chương · 사이다 역전극)",
        "genre_label_vi": "Thể loại 1/5 — Đấu trí Danh dự, Bằng cấp & Bản quyền Nghề (사이다 · 명인의 역전)",
        "default_chapters": 6,
        "weights_6": (0.12, 0.18, 0.20, 0.20, 0.22, 0.08),
        "weights_5": (0.14, 0.22, 0.28, 0.27, 0.09),
        "keywords": "상견례 사돈 동서 학벌 내기 도용 훔친 경연 심사 대반전",
        "chapters_6": (
            ("제1장 (ACT01): Phẩm Giá Bị Xem Thường & Đôi Bàn Tay Giấu Nghề", "Cold Open thoại sốc 0:00 -> Bối cảnh định kiến gia đình/xưởng nghề, nhân vật chính điềm tĩnh rời đi cùng kỷ vật nghề, GIẤU KÍN tên hiệu danh nhân (0% lộ bài ngửa ở Chương 1)."),
            ("제2장 (ACT02): Biến Cố Đêm Mưa & Danh Hiệu Được Xướng Tên Ở Cổng Xưởng", "Đưa ngay biến cố/thời hạn gấp rút mới vào xưởng nghề (0% lặp lại lời khen/giải thích kỹ thuật Chương 1); khép cuối Chương 2 bằng Cú Lật #1 khi nhân vật quyền uy cúi đầu gọi đúng tên hiệu thật."),
            ("제3장 (ACT03): Lời Thề Năm Xưa & Cái Bẫy Kỹ Thuật Tầng 1", "Hồi ức quá khứ (present_year - flashback_year khớp toán học 100%) & lý do ẩn danh + Phe phản diện giở trò trộm bản vẽ/thuê người đóng thế nhưng dính Bẫy Nghề Chekhov Tầng 1."),
            ("제4장 (ACT04): Đêm Trước Giờ G & Dấu Ấn Độc Bản Tầng 2", "Bão táp trước buổi thẩm định lớn, cài Bẫy Chekhov Tầng 2 (dấu ấn ngầm của người thợ / biên lai gốc) & sự chột dạ của kẻ mạo danh (0% tóm tắt lặp lại Chương 1–3)."),
            ("제5장 (ACT05): Màn Phản Kích 2 Tầng Liên Hoàn Giữa Khán Phòng", "Cú Lật Kép 2 Tầng: Tầng 1 phơi bày lỗi vật lý của tác phẩm ăn cắp dưới ánh đèn/nhiệt độ thật -> Tầng 2 lật mở dấu ấn độc bản khóa chặt chiến thắng phẩm giá."),
            ("제6장 (ACT06): Mùa Mới Tự Tại & Lời Chúc Đêm An Lành", "Gói gọn 7.5%–9% (~4.5–5.5 phút): khép trọn nhân quả, bình yên nơi hiên nhà ấm và lời chúc ngủ ngon + 4.0s Piano/Cello fade-out (0% Spoken CTA)."),
        ),
    },
    {
        "id": "spine_b_twilight_independence_irreplaceable_void",
        "label_vi": "Xương sống B — Buông Bỏ & Khoảng Trống Không Thể Thay Thế (5–6 Chương · 황혼 홀로서기극)",
        "genre_label_vi": "Thể loại 2 — Hoàng hôn Độc lập & Giá trị Trụ cột Vô hình (황혼 홀로서기 · 졸혼)",
        "default_chapters": 5,
        "weights_5": (0.14, 0.22, 0.28, 0.27, 0.09),
        "weights_6": (0.12, 0.18, 0.20, 0.20, 0.22, 0.08),
        "keywords": "황혼 이혼 졸혼 남편 시월드 삼십 년 독립 공방 홀로서기 후회",
        "chapters_5": (
            ("제1장 (ACT01): Tờ Giấy Đặt Xuống Bàn Sau Ba Mươi Năm Nhẫn Nhịn", "Cold Open lời tuyên bố buông bỏ điềm tĩnh tại 0:00 -> Giọt nước tràn ly sau hàng chục năm hy sinh vô hình; nhân vật chính lặng lẽ thu dọn chiếc rương nghề rời đi (giấu kín danh tiếng thật)."),
            ("제2장 (ACT02): Căn Gác Nhỏ Bên Đồi & Đôi Bàn Tay Sống Lại Nghề Xưa", "Không gian sống mới bình yên, âm thanh chế tác thủ công thức giấc và cuối Chương 2 hé lộ vị thế bậc thầy mà giới chuyên môn vẫn luôn tìm kiếm."),
            ("제3장 (ACT03): Sự Sụp Đổ Dây Chuyền Khi Mất Đi Trụ Cột Vô Hình", "Ngôi nhà cũ và cơ ngơi của người chồng/gia đình chồng nhanh chóng rối loạn, mất khách VIP và bộc lộ sự bất lực vì suốt mấy chục năm qua chính bà mới là linh hồn giữ gìn tất cả."),
            ("제4장 (ACT04): Cuộc Tìm Gặp Muộn Màng & Lời Từ Chối Đầy Phẩm Giá", "Gia đình cũ tìm đến tận xưởng nghề mới trong sự bẽ bàng để cầu xin bà quay về, nhưng chứng kiến bà được vinh danh xứng đáng và nhận lời từ chối điềm đạm, dứt khoát."),
            ("제5장 (ACT05): Ánh Đèn Vàng Của Riêng Mình & Giấc Ngủ Bình Yên", "Gói gọn 8%–9% (~4.5–5.5 phút): tự do, ấm áp tuổi xế chiều và lời chúc ngủ ngon êm dịu + 4.0s Piano/Cello fade-out (0% Spoken CTA)."),
        ),
        "chapters_6": (
            ("제1장 (ACT01): Tờ Giấy Đặt Xuống Bàn Sau Ba Mươi Năm Nhẫn Nhịn", "Cold Open lời tuyên bố buông bỏ điềm tĩnh tại 0:00 -> Giọt nước tràn ly sau hàng chục năm hy sinh vô hình; nhân vật chính lặng lẽ rời đi (giấu kín danh tiếng thật)."),
            ("제2장 (ACT02): Căn Gác Nhỏ & Đôi Bàn Tay Đánh Thức Nghề Xưa", "Dựng lại góc xưởng nhỏ trong đêm mưa, tiến triển thử thách mới và cuối Chương 2 hé lộ danh hiệu thật của bà."),
            ("제3장 (ACT03): Hồi Ức Thời Thanh Xuân & Khoảng Trống Bắt Đầu Lộ Rõ", "Ký ức năm xưa vì gia đình mà cất giấu tài năng (khớp toán học số năm 100%) song hành với những rạn nứt đầu tiên tại ngôi nhà cũ."),
            ("제4장 (ACT04): Cơ Ngơi Cũ Lao Đao Trước Kỳ Thẩm Định Quyết Định", "Thiếu bàn tay và bí quyết của bà, gia đình cũ đứng trước nguy cơ phá sản uy tín không ai cứu vãn nổi."),
            ("제5장 (ACT05): Cuộc Hội Ngộ Đảo Chiều & Lời Từ Chối Phẩm Giá", "Chạm mặt tại sự kiện lớn: bà tỏa sáng độc lập trong sự kính trọng của toàn giới, khước từ sự níu kéo muộn màng."),
            ("제6장 (ACT06): Ánh Đèn Vàng Tự Tại & Lời Chúc Ngủ Ngon", "Gói gọn 8% (~4.5–5.5 phút): bình yên tuổi xế chiều + 4.0s Piano/Cello fade-out (0% Spoken CTA)."),
        ),
    },
    {
        "id": "spine_c_heirloom_unveiling_family_repentance",
        "label_vi": "Xương sống C — Bóc Tách Kỷ Vật & Nước Mắt Thức Tỉnh (5 Chương · 모정·유품 참회극)",
        "genre_label_vi": "Thể loại 3/4 — Bí mật của Mẹ, Kỷ vật Gia truyền & Sự Thức tỉnh Muộn màng (모정 · 가족 참회극)",
        "default_chapters": 5,
        "weights_5": (0.14, 0.22, 0.28, 0.27, 0.09),
        "weights_6": (0.12, 0.18, 0.20, 0.20, 0.22, 0.08),
        "keywords": "어머니 유품 장녀 자식 형제 유산 통장 영수증 눈물 참회 후회",
        "chapters_5": (
            ("제1장 (ACT01): Chiếc Hộp Cũ Bị Đẩy Ra Rìa Trong Ngày Họp Gia Đình", "Cold Open tại 0:00 khi các con/anh chị em tranh giành tài sản và hắt hủi chiếc rương kỷ vật của mẹ/chị cả; giấu kín bí mật bên trong chiếc rương ở Chương 1."),
            ("제2장 (ACT02): Kỷ Vật Thứ Nhất & Danh Phận Thật Sự Sau Cánh Cửa Xưởng", "Mở tầng đầu tiên của kỷ vật dẫn tới một nhân chứng/bậc thầy nghề nghiệp; cuối Chương 2 hé lộ danh phận và tay nghề thật mà cả nhà từng coi rẻ."),
            ("제3장 (ACT03): Xấp Biên Lai Ngả Màu & Khoản Nợ Ân Tình Hai Mươi Tám Năm", "Bóc tách tầng kỷ vật thứ hai (sổ ghi chép, vết sẹo nghề, biên lai năm xưa khớp 100% toán học niên biểu) phơi bày sự hy sinh thầm lặng nuôi sống cả gia đình."),
            ("제4장 (ACT04): Khoảnh Khắc Sự Thật Vỡ Òa & Những Giọt Nước Mắt Muộn Màng", "Toàn bộ sự thật được chứng thực trước mặt những người con/người thân từng vô tâm; cao trào thức tỉnh và sự ăn năn nghẹn ngào."),
            ("제5장 (ACT05): Hơi Ấm Chữa Lành Đêm Khuya & Lời Chúc An Giấc", "Gói gọn 8%–9% (~4.5–5.5 phút): hóa giải, bình yên lắng đọng và lời chúc ngủ ngon + 4.0s Piano/Cello fade-out (0% Spoken CTA)."),
        ),
        "chapters_6": (
            ("제1장 (ACT01): Chiếc Hộp Cũ Bị Đẩy Ra Rìa Trong Ngày Họp Gia Đình", "Cold Open tại 0:00 khi chiếc rương cũ bị hắt hủi; giấu kín bí mật bên trong ở Chương 1."),
            ("제2장 (ACT02): Kỷ Vật Thứ Nhất & Người Khách Lạ Tìm Đến Cổng Nhà", "Manh mối đầu tiên mở ra và cuối Chương 2 lộ diện danh phận nghệ nhân thật sự của người mẹ/người chị."),
            ("제3장 (ACT03): Kỷ Vật Thứ Hai & Đêm Mưa Hai Mươi Tám Năm Trước", "Hồi ức quá khứ (khớp 100% toán học niên biểu) giải mã vì sao bà chấp nhận chịu thiệt thòi suốt hàng chục năm."),
            ("제4장 (ACT04): Kỷ Vật Cuối Cùng & Cú Sốc Của Những Đứa Con Vô Tâm", "Tầng bí mật cuối cùng được mở ra khi biến cố ập đến với những người con chuộng hư vinh."),
            ("제5장 (ACT05): Nước Mắt Thức Tỉnh Trước Bàn Làm Việc Của Mẹ", "Cao trào cảm xúc vỡ òa khi những người thân quỳ xuống nhận ra giá trị thật của đôi bàn tay chai sần."),
            ("제6장 (ACT06): Hơi Ấm Chữa Lành & Lời Chúc Đêm An Lành", "Gói gọn 8% (~4.5–5.5 phút): lắng đọng ấm áp + 4.0s Piano/Cello fade-out (0% Spoken CTA)."),
        ),
    },
    {
        "id": "spine_d_crisis_rescue_true_successor",
        "label_vi": "Xương sống D — Giải Cứu Bảo Vật & Chọn Người Kế Thừa (6 Chương · 국보 복원·후계자극)",
        "genre_label_vi": "Thể loại 4/5 — Giải cứu Bảo vật Phút 89 & Chọn Truyền nhân Chân chính (국보 복원 · 진품의 자격)",
        "default_chapters": 6,
        "weights_6": (0.12, 0.18, 0.20, 0.20, 0.22, 0.08),
        "weights_5": (0.14, 0.22, 0.28, 0.27, 0.09),
        "keywords": "복원 국보 국가유산 만찬 위기 후계자 제자 비법 감정 명장",
        "chapters_6": (
            ("제1장 (ACT01): Sự Cố Phút 89 & Đề Bài Không Ai Giải Nổi", "Cold Open cuộc gọi khẩn/sự cố bảo vật tại 0:00 -> Phe chuộng hư danh hoàn toàn bất lực trước lỗi kỹ thuật chí mạng, trong khi nhân vật chính vẫn lặng lẽ ở vị trí bình dị (giấu kín danh hiệu ở Chương 1)."),
            ("제2장 (ACT02): Cuộc Cầu Cứu Giữa Đêm & Bậc Thầy Ẩn Danh Lộ Diện", "Thời hạn đếm ngược nghẹt thở buộc hội đồng phải tìm đến căn xưởng nhỏ; cuối Chương 2 mở nút thắt danh hiệu thật của nhân vật chính."),
            ("제3장 (ACT03): Ân Oán Đồng Môn Năm Xưa & Bài Toán Kỹ Thuật Tầng 1", "Hồi ức lời thề với sư phụ (present_year - past_year khớp 100%) và phép thử tay nghề đầu tiên vạch trần kẻ làm dối."),
            ("제4장 (ACT04): Đêm Thức Trắng Cứu Bảo Vật & Phép Thử Nhân Cách Tầng 2", "Quá trình phục chế/chế tác tỉ mỉ dưới ánh đèn vàng và phép thử đạo đức nghề nghiệp dành cho những người muốn kế thừa."),
            ("제5장 (ACT05): Khoảnh Khắc Bảo Vật Tỏa Sáng & Trao Truyền Ấn Tín", "Tác phẩm hoàn mỹ xuất hiện đúng giờ G khiến cả hội đồng nghiêng mình; kẻ giả dối bị loại bỏ và ấn tín nghề được trao cho truyền nhân tử tế."),
            ("제6장 (ACT06): Tiếng Chuông Đêm Khuya & Giấc Ngủ An Lành", "Gói gọn 8% (~4.5–5.5 phút): dư âm nghề truyền thống ấm áp + 4.0s Piano/Cello fade-out (0% Spoken CTA)."),
        ),
    },
)


def select_audio_drama_narrative_blueprint(job: dict[str, Any] | None = None) -> dict[str, Any]:
    """Select 1 of 5 Genres × 1 of 6 Cold-Open Hooks × 1 of 4 Narrative Spines (5 or 6 Chapters) for `creative_audio_drama`."""
    job = job if isinstance(job, dict) else {}
    brief = job.get("creative_brief") if isinstance(job.get("creative_brief"), dict) else {}
    ed_dna = job.get("editorial_dna") if isinstance(job.get("editorial_dna"), dict) else (
        ((job.get("channel_profile_snapshot") or {}).get("editorial_dna") if isinstance(job.get("channel_profile_snapshot"), dict) else {}) or {}
    )
    text_blob = " ".join(
        [
            str(job.get("title") or ""),
            str(job.get("topic") or ""),
            str(job.get("notes") or ""),
            str(brief.get("opening_hook") or ""),
            str(brief.get("narrative_angle") or ""),
        ]
    ).lower()
    explicit_idx = job.get("structural_variant_index")
    if explicit_idx is None:
        explicit_idx = brief.get("structural_variant_index")

    seed_material = "::".join(
        [
            str(job.get("id") or "").strip(),
            str(job.get("title") or "").strip(),
            str(job.get("notes") or "")[:100].strip(),
        ]
    ) or "audio-drama-default-seed"
    digest = hashlib.sha256(seed_material.encode("utf-8")).digest()

    if explicit_idx is not None:
        try:
            idx = int(explicit_idx)
            spine = AUDIO_DRAMA_NARRATIVE_SPINES[idx % len(AUDIO_DRAMA_NARRATIVE_SPINES)]
            opening = AUDIO_DRAMA_OPENING_ARCHETYPES[idx % len(AUDIO_DRAMA_OPENING_ARCHETYPES)]
        except (TypeError, ValueError):
            explicit_idx = None

    if explicit_idx is None:
        scored_spines: list[tuple[int, int, dict[str, Any]]] = []
        for s_idx, sp in enumerate(AUDIO_DRAMA_NARRATIVE_SPINES):
            kw_hits = sum(1 for kw in str(sp.get("keywords") or "").split() if kw and kw in text_blob)
            scored_spines.append((kw_hits, -s_idx, sp))
        scored_spines.sort(key=lambda x: (x[0], x[1]), reverse=True)
        if scored_spines[0][0] > 0:
            spine = scored_spines[0][2]
        else:
            spine = AUDIO_DRAMA_NARRATIVE_SPINES[int.from_bytes(digest[0:2], "big") % len(AUDIO_DRAMA_NARRATIVE_SPINES)]

        scored_openings: list[tuple[int, int, dict[str, str]]] = []
        for o_idx, op in enumerate(AUDIO_DRAMA_OPENING_ARCHETYPES):
            kw_hits = sum(1 for kw in str(op.get("keywords") or "").split() if kw and kw in text_blob)
            scored_openings.append((kw_hits, -o_idx, op))
        scored_openings.sort(key=lambda x: (x[0], x[1]), reverse=True)
        if scored_openings[0][0] > 0:
            opening = scored_openings[0][2]
        else:
            opening = AUDIO_DRAMA_OPENING_ARCHETYPES[int.from_bytes(digest[2:4], "big") % len(AUDIO_DRAMA_OPENING_ARCHETYPES)]

    target_dur = 70.0
    try:
        target_dur = float(job.get("target_duration_minutes") or 70.0)
    except (TypeError, ValueError):
        pass
    explicit_ch = int(ed_dna.get("chapter_count") or 0) if str(ed_dna.get("chapter_count") or "").isdigit() else 0
    if explicit_ch in {5, 6}:
        ch_count = explicit_ch
    elif spine["id"] in {"spine_b_twilight_independence_irreplaceable_void", "spine_c_heirloom_unveiling_family_repentance"} and target_dur <= 62.0:
        ch_count = 5
    else:
        ch_count = int(spine.get("default_chapters") or 6)
        if ch_count == 5 and target_dur >= 68.0:
            ch_count = 6

    weights = spine.get(f"weights_{ch_count}") or (
        (0.14, 0.22, 0.28, 0.27, 0.09) if ch_count == 5 else (0.12, 0.18, 0.20, 0.20, 0.22, 0.08)
    )
    chapters_tpl = spine.get(f"chapters_{ch_count}") or spine.get("chapters_6") or spine.get("chapters_5")
    if len(chapters_tpl) > ch_count:
        chapters_tpl = chapters_tpl[:ch_count]

    return {
        "spine_id": spine["id"],
        "spine_label_vi": spine["label_vi"],
        "genre_label_vi": spine["genre_label_vi"],
        "opening_id": opening["id"],
        "opening_label_vi": opening["label_vi"],
        "opening_directive_vi": opening["directive_vi"],
        "chapter_count": ch_count,
        "chapter_weights": tuple(weights),
        "chapters_template": tuple(chapters_tpl),
    }


_RECENT_CTA_SIGNAL_KO_RE = re.compile(
    r"(?<!신문\s)(?<!잡지\s)(?<!정기\s)구독"
    r"|알림\s*설정"
    r"|좋아요(?:를|도|로|\s*버튼|\s*한\s*번)"
    r"|댓글(?:로|에|란에)"
    r"|(?:저희\s*채널|채널\s*보관함|이\s*채널|채널\s*구독)"
    r"|시청해\s*주셔서"
    r"|화면에\s*(?:표시되고|나타나는|나타난|준비된|준비돼|띄워진)"
    r"|다음\s*(?:사건\s*파일|수사\s*기록|기록에서도|이야기에서도)"
)
_RECENT_CTA_SIGNAL_EN_RE = re.compile(
    r"\b(?:subscribe|notification\s+bell|hit\s+like|leave\s+a\s+comment|thanks?\s+for\s+watching|on\s+your\s+screen\s+right\s+now)\b",
    re.IGNORECASE,
)


def _recent_episode_srt_anti_clone_direction(
    job: dict[str, Any],
    workspace: Path,
    *,
    limit: int = 5,
) -> str:
    """Scan full text of recent sibling episode scripts OF THE SAME CHANNEL PROFILE so channels never leak episodes into one another."""
    lang = str(job.get("language") or "ko").strip().lower()
    active_prof_id = str(
        job.get("channel_profile_id")
        or ((job.get("channel_profile_snapshot") or {}).get("id") if isinstance(job.get("channel_profile_snapshot"), dict) else "")
        or ""
    ).strip()
    workspaces_root = Path(__file__).resolve().parents[1] / "workspaces"
    if not workspaces_root.is_dir():
        return ""
    try:
        resolved_ws = workspace.resolve()
    except Exception:
        resolved_ws = workspace
    samples: list[str] = []
    cta_re = _RECENT_CTA_SIGNAL_KO_RE if lang == "ko" else _RECENT_CTA_SIGNAL_EN_RE
    for cand in sorted((p for p in workspaces_root.iterdir() if p.is_dir()), key=lambda p: p.name, reverse=True):
        if len(samples) >= limit:
            break
        try:
            if cand.resolve() == resolved_ws:
                continue
        except Exception:
            if cand.name == workspace.name:
                continue
        if active_prof_id:
            inp_file = cand / "input.json"
            cand_prof_id = ""
            if inp_file.is_file():
                try:
                    inp_data = json.loads(inp_file.read_text(encoding="utf-8", errors="ignore"))
                    if isinstance(inp_data, dict):
                        cand_prof_id = str(
                            inp_data.get("channel_profile_id")
                            or ((inp_data.get("channel_profile_snapshot") or {}).get("id") if isinstance(inp_data.get("channel_profile_snapshot"), dict) else "")
                            or ""
                        ).strip()
                except Exception:
                    cand_prof_id = ""
            if cand_prof_id != active_prof_id:
                continue
        script_file = cand / "script.md"
        if not script_file.is_file():
            continue
        try:
            raw_text = script_file.read_text(encoding="utf-8", errors="ignore").strip()
        except Exception:
            continue
        if len(raw_text) < 400:
            continue
        has_hangul = bool(re.search(r"[\uac00-\ud7a3]", raw_text))
        if lang == "ko" and not has_hangul:
            continue
        if lang == "en" and (has_hangul or not re.search(r"[A-Za-z]{4,}", raw_text)):
            continue
        if lang not in {"ko", "en"}:
            continue
        lines = [
            ln.strip()
            for ln in raw_text.splitlines()
            if ln.strip() and not ln.strip().startswith("#")
        ]
        if len(lines) < 8:
            continue
        cta_hits: list[str] = []
        for ln in lines:
            for sent in re.split(r"(?<=[.?!])\s+", ln):
                s = sent.strip()
                if s and cta_re.search(s) and len(cta_hits) < 4:
                    cta_hits.append(s[:130])
        head_preview = " / ".join(ln[:110] for ln in lines[:2])
        tail_preview = " / ".join(ln[:110] for ln in lines[-5:])
        cta_preview = " / ".join(cta_hits) if cta_hits else "(Zero explicit CTA — pure documentary narration)"
        samples.append(
            f"  * Recent Episode `{cand.name}`:\n"
            f"    - Opening lines (KEEP Exact Timestamp + Paradox DNA, DO NOT repeat specific details/motifs like '현상금... 수배령', '험준한 산길 폴리스 라인', '차량 트렁크'): {head_preview}\n"
            f"    - All CTA/Invitation sentences anywhere in script (MAX 1 CTA per episode; DO NOT reuse wording OR grammatical structure): {cta_preview}\n"
            f"    - Final 5 lines (DO NOT reuse phrases/cadence): {tail_preview}"
        )
    if not samples:
        samples_block = ""
    else:
        skeleton_example = " (`~하시려면 구독과...`)" if lang == "ko" else ""
        samples_block = (
            "RECENT CHANNEL EPISODE SRT & FULL-SCRIPT CTA FINGERPRINTS — STRICT ZERO-REPEAT GUARDRAIL:\n"
            f"- NEVER repeat ANY CTA phrasing, clause, or syntactic skeleton{skeleton_example} from ANY position (mid-script or end-script) of prior episodes of this channel, and NEVER place more than 1 explicit CTA inside the same script.\n"
            "- Cross-check your Cold-Open Hook against the recent openings below: ALWAYS open Sentence 1 with this case's exact Timestamp (`YYYY년 M월 D일 [시각], [장소]...`) + immediate Paradox Flip (`하지만 / 그런데`), and NEVER repeat the specific opening details/motifs of recent uploads:\n"
            + "\n".join(samples)
            + "\n"
        )

    mo_diff_block = ""
    if lang == "ko":
        try:
            from services.case_similarity import check_cross_case_mo_collision

            snapshot = job.get("channel_profile_snapshot") if isinstance(job.get("channel_profile_snapshot"), dict) else {}
            mem_records = list(snapshot.get("topic_memory") or []) + list(snapshot.get("suggested_topic_history") or [])
            cand_blob = f"{job.get('title') or ''} {job.get('topic') or ''} {job.get('notes') or ''}"
            is_coll, coll_reason, diff_ko = check_cross_case_mo_collision(cand_blob, mem_records, cooldown_window=30)
            if is_coll or any(k in cand_blob for k in ("바이바오산", "백보산", "白宝山")):
                extra_ko = diff_ko or (
                    "만약 채널의 기존 업로드 영상(예: 마한칭 사건)과 일부 범행 지역(우루무치 변장빈관/볜장 빈관 일대)·단서(오사식 번호 대조)·검거 동선이 겹칠 경우, "
                    "절대로 겹치는 장소(우루무치 변장빈관 일대)로 1막 오프닝(Cold Open)을 시작하지 마십시오! "
                    "반드시 이 사건만의 독보적인 핵심 시그니처(바이바오산의 경우: 1996년 수도 베이징 스징산 발전소·초소 야간 경계선 연쇄 이탈 미스터리와 광역 수사망 추적)로 1막 Hook을 시작하여 시청자가 이전 영상의 재탕으로 오해하지 않도록 100% 차별화하고, 초반 60초 수익창출 청정 규정을 철저히 준수하십시오."
                )
                mo_diff_block = (
                    "\nCROSS-EPISODE VENUE, MODUS OPERANDI & COLD-OPEN HOOK DIFFERENTIATION LAW (`기존 업로드 영상과 배경·단서·오프닝 훅 중복 절대 금지`):\n"
                    f"- Channel Collision Audit: {coll_reason or 'Multi-location serial case sharing secondary Xinjiang/Urumqi venue with Ma Hanqing (`마한칭`) episode'}\n"
                    f"- MANDATORY HOOK & ACT STRUCTURE OVERRIDE: {extra_ko}\n"
                )
        except Exception:
            pass

    return samples_block + mo_diff_block


def _detect_documentary_niche_engine(job: dict[str, Any]) -> tuple[str, str]:
    """Identify the active documentary niche purely from semantic profile/job DNA (zero hardcoded channel-* IDs, Hangul-free output)."""
    snapshot = job.get("channel_profile_snapshot") if isinstance(job.get("channel_profile_snapshot"), dict) else {}
    ed_dna = _resolve_job_editing_dna(job)
    preset_id = str(ed_dna.get("preset_id") or "").strip().lower()
    editorial = snapshot.get("editorial_dna") if isinstance(snapshot.get("editorial_dna"), dict) else {}
    seo_dna = job.get("seo_keyword_dna") or snapshot.get("seo_keyword_dna") or {}
    brief = job.get("creative_brief") if isinstance(job.get("creative_brief"), dict) else {}
    haystack = " ".join([
        preset_id,
        str(editorial.get("narrative_genre") or ""),
        str(editorial.get("voice_and_structure") or snapshot.get("voice_and_structure") or ""),
        json.dumps(snapshot.get("allowed_topics") or [], ensure_ascii=False),
        str(job.get("title") or ""),
        str(job.get("topic") or ""),
        str(snapshot.get("label") or ""),
        str(brief.get("narrative_angle") or ""),
        str(brief.get("writing_style") or ""),
        str((seo_dna if isinstance(seo_dna, dict) else {}).get("primary_title_keyword") or ""),
        str((seo_dna if isinstance(seo_dna, dict) else {}).get("primary_title_keyword_meaning_vi") or ""),
    ]).lower()

    if is_creative_audio_drama_job(job):
        return (
            "Korean Late-Night Audio Drama & Family Dignity Cinema (5070)",
            "Open at 0:00 with an explosive In-Medias-Res confrontation quote BEFORE Chapter 1 (0% chapter-title/date opener, 0% early twist/pen-name spoiler in Chapter 1) -> withhold the protagonist's legendary master identity until the end of Chapter 2 -> drive Chapters 3-5 with fresh escalating stakes and a 2-Tier Chekhov Craft Trap (zero repetitive praise/exposition echo) -> land Chapter 6 concisely (7.5%-9%) on serene nocturnal healing with 0% spoken CTA, exact Korean chronology/syllable-count math, post-2024 statutory accuracy, and a 4.0s warm piano/cello fade-out.",
        )
    if preset_id in {"sacred_devotional", "grace_letter"} or any(
        k in haystack for k in ("spiritual", "pastoral", "lời chúa", "ân điển", "은혜", "기도", "묵상", "하나님", "devotional")
    ):
        return (
            "Spiritual, Pastoral & Contemplative Night Letter",
            "Open with quiet empathy touching the listener's unspoken fatigue -> structure into gentle wave-breathing movements -> use warm open vowels, calm pacing, and 0% harsh preachiness.",
        )
    if preset_id == "financial_forensic_vox" or any(
        k in haystack
        for k in (
            "finance", "ponzi", "crypto", "bank", "liquidity",
            "lừa đảo", "dòng tiền", "ngân hàng", "thanh khoản", "tài chính",
            "금융", "사기", "자금", "은행", "파산", "비트코인", "金融", "詐欺", "finanz", "halbleiter", "monopol", "economía",
        )
    ):
        return (
            "Cyber, Finance, Tech Monopoly & Economic Forensics",
            "Anchor massive sums or complex tech supply chains against ONE real human passbook or concrete physical bottleneck -> drive mid-acts via Follow-the-Money / Mechanism Breakdown using everyday tangible metaphors -> never stack more than 2 consecutive raw number sentences without human translation.",
        )
    if any(
        k in haystack
        for k in (
            "declassified", "presidential", "intelligence", "archival", "cold war", "white house",
            "giải mật", "tổng thống", "chiến tranh lạnh",
            "기밀", "첩보", "냉전", "외교", "機密", "冷戦", "geopolitik", "geopolítica",
        )
    ):
        return (
            "Declassified Archives, History & Executive Geopolitics",
            "Open inside the closed decision room (a timestamped memo, archival tape, or map boundary) -> drive narrative tension by contrasting Public Rhetoric vs. Declassified Primary Records -> ground every claim in dated archival documents rather than hindsight commentary.",
        )
    if any(
        k in haystack
        for k in (
            "infrastructure", "hạ tầng", "công trình", "đập", "hầm", "dam", "bridge", "tunnel", "engineering",
            "인프라", "대공정", "댐", "터널", "교량", "붕괴", "운하", "ダム", "トンネル", "崩落", "工学", "大工程",
        )
    ):
        return (
            "Mega-Infrastructure, Engineering & Systemic Forensics",
            "Open at the physical threshold breach -> trace the strict Physical Domino Chain (geological/material constraint -> human cost/schedule trade-off -> micro-fracture -> systemic cascade) using vivid physical verbs instead of dry textbook jargon.",
        )
    if preset_id in {"forensic_noir", "forensic_noir_director_v2", "vox_china_crime_newsroom_v10"} or any(
        k in haystack
        for k in (
            "truecrime", "true crime", "disappearance", "fugitive", "cold case",
            "hình sự", "vụ án", "mất tích", "truy nã", "án lạnh", "kho bạc", "mở két",
            "실화 사건", "수사", "실종", "용의자", "수배", "미제", "금고", "사건", "事件", "捜査", "失踪", "kriminal", "crimen",
        )
    ):
        return (
            "Investigative True Crime, Vault Forensics & Fugitive Psychology",
            "Select a topic-fitted Cold-Open Hook Archetype (micro forensic anomaly, double-life unmasking, verbatim line, countdown breach, locked-room/vault paradox, interrupted ordinary routine, scale collision, or cold archive match) without spoiling the culprit early -> advance through sequential Hypothesis Elimination -> plant early everyday Chekhov details that lock the net in Act 4 -> enforce 100% Broadcast Green-Dollar prose (zero death/corpse/blood/weapon words in 00:00-01:00 and indirect forensic/judicial refraction throughout).",
        )
    if any(
        k in haystack
        for k in (
            "biography", "biografía", "biografie", "ascenso", "rise and fall",
            "tiểu sử", "quyền lực", "đế chế", "인물", "전기", "권력", "伝記", "権力",
        )
    ):
        return (
            "Biography, Power & Rise-and-Fall",
            "Anchor the subject in a formative human contradiction -> trace the ascent, hubris, and pivotal turning point through concrete decisions and primary witnesses -> close on historical consequence without hagiography or cliché.",
        )
    return (
        "Deep Investigative, Cultural, Essay & Human-Interest Documentary",
        "Apply the Micro-to-Macro-to-Micro lens aligned with the Channel Profile's own DNA: open on one unforgettable lived human or sensory detail -> expand into the deeper story or mechanism -> close on a quiet authentic resonance (Show, Don't Moralize).",
    )


def _broadcast_ear_writing_and_niche_direction(job: dict[str, Any]) -> str:
    """Universal + country-specific Broadcast 'Writing for the Ear & TTS' craft mindset (strictly Hangul-free when lang != 'ko')."""
    lang = str(job.get("language") or "ko").strip().lower()
    market = str(job.get("market") or "KR").strip().upper()
    niche_label, niche_engine = _detect_documentary_niche_engine(job)

    lang_specific = {
        "en": (
            "- **English Broadcast Craft (`PBS Frontline / CBS 60 Minutes / NPR / LEMMiNO`)**: Strip front-loaded participial clauses ('Having evaded police for eight years, the suspect...' -> 'For eight years, he slipped past police.'). Ban AI filler ('delve into', 'testament to', 'tapestry', 'stark reminder', 'chillingly', 'little did they know', 'not only X, but also Y', 'it is worth noting', 'underscore'). Use NPR-friendly spoken numbers when exact cents are not forensic clues."
        ),
        "vi": (
            "- **Vietnamese Broadcast Craft (`VTV1 Phóng Sự / VTV Đặc Biệt`)**: Phối nhạc tính thanh Bằng (ngang/huyền) và thanh Trắc ở cuối mỗi vế nghỉ để TTS ngân tự nhiên, tránh dồn 4-5 thanh nặng/sắc liên tiếp làm nghẹt hơi. Loại bỏ triệt để văn dịch máy ('tiến hành thực hiện sự kiểm tra', 'bị phát hiện bởi', 'không chỉ... mà còn...', 'đáng chú ý là'); ưu tiên động từ thuần Việt sắc nét."
        ),
        "ja": (
            "- **Japanese Broadcast Craft (`NHK Special / Eizou no Seiki`)**: Eliminate Kanji homophone traps for the ear (prefer clear Yamato-kotoba spoken verbs over ambiguous Sino-Japanese compounds), pace around 250-300 characters per minute, and avoid repetitive '~no de aru / ~no da' walls by weaving calm '~mashita / ~te imasu' with intentional Ma pauses."
        ),
        "de": (
            "- **German Broadcast Craft (`ARD / ZDF / DW`)**: Enforce Verbalstil over bureaucratic Nominalstil/Funktionsverbgefuege, and break long Schachtelsaetze so the listener never waits 25 words for the verb."
        ),
        "fr": (
            "- **French Broadcast Craft (`ARTE / France Culture`)**: Break nested 'qui... que... dont...' relative chains into crisp, tactile radio-documentary sentences with smooth spoken liaison."
        ),
        "es": (
            "- **Spanish Broadcast Craft (`RTVE Documentales`)**: Favor active verbs and vivid historical present/preterite over 'fue + participio' passive constructions and ornate circunloquios."
        ),
        "zh": (
            "- **Chinese Broadcast Craft (`CCTV Documentary`)**: Prioritize clear disyllabic spoken vocabulary over Classical literary homophones, replace emotional adjectives with micro-action verbs, and leave restrained space (Liubai) at emotional peaks without moralizing."
        ),
    }
    country_line = lang_specific.get(lang, "")
    extra_block = f"\n{country_line}" if country_line else ""

    return f"""UNIVERSAL BROADCAST "WRITING FOR THE EAR & TTS" CRAFT MINDSET (`{market} / {lang}` · Profile Domain: `{niche_label}`):
- **SUPREME PROFILE DNA AUTHORITY**: The active Channel Profile's own `editorial_dna`, `voice_and_structure`, `speech_register`, and `creative_brief` are the supreme creative constitution for this video. If the profile chooses a custom tone, narrative structure, speech register, or multi-voice dialogue (`secondary_voice_id`), honor that profile's DNA 100% without cross-channel interference.
- **Five Universal Ear-Writing Principles (Craft Mindset Over Rigid Formulas)**:
  1. **One Breath, One Thought**: Listeners cannot re-read backwards. Carry ONE clear thought or image per breath clause (12-18 syllables/words), keeping subject and verb naturally connected.
  2. **Verbalization Over Nominalization**: Unfreeze abstract noun phrases back into concrete verbs that move the scene inside the listener's mind.
  3. **Speaker Clarity Before Quotation**: For single-narrator TTS, introduce who speaks before quoting so the listener is never confused; reserve verbatim `"..."` quotes for pivotal moments (unless the profile explicitly configures a dedicated `secondary_voice_id` or scriptural reading format).
  4. **Intentional Dramatic Brakes vs. Inventory Lists**: Use crisp 2-5 word rhythmic brakes at high-impact pivots or climax beats (5%-10%, never two verbless fragments back-to-back) to arrest uniform sentence-length monotony, while letting active verbal predicates carry the main narrative flow.
  5. **Asymmetric Emotional Breathing & Counterpoint**: Vary paragraph lengths organically (1-2 lines at emotional pivots, 3-5 lines for narrative build-up — NEVER uniform 4-line conveyor-belt stanzas), and write narration that adds deeper meaning rather than merely describing surface visuals.
- **Domain Retention Engine (`{niche_label}`)**: {niche_engine}{extra_block}
"""


def _korean_natural_documentary_prose_direction(job: dict[str, Any] | None = None) -> str:
    job = job if isinstance(job, dict) else {}
    lang = str(job.get("language") or "ko").strip().lower()
    if lang != "ko":
        return ""
    from .quality import resolve_korean_profile_style_flags

    style_flags = resolve_korean_profile_style_flags(job)
    custom_register = style_flags["custom_register"]
    allow_archaic = style_flags["allow_archaic_speech"]
    is_china_scope = _is_china_scoped_job(job)

    recipe = job.get("production_recipe") or {}
    target_mins = job.get("target_duration_minutes") or (job.get("creative_brief") or {}).get("target_duration_minutes")
    try:
        minutes = float(target_mins) if target_mins not in (None, "") else max(float(recipe.get("target_duration_sec") or 600) / 60.0, 2.0)
    except (TypeError, ValueError):
        minutes = 15.0
    ideal_chars = round(minutes * 308)
    act1_chars = round(ideal_chars * 0.13)
    act2_chars = round(ideal_chars * 0.23)
    act3_chars = round(ideal_chars * 0.26)
    act4_chars = round(ideal_chars * 0.22)
    act5_chars = ideal_chars - (act1_chars + act2_chars + act3_chars + act4_chars)
    variant = select_episode_narrative_variant(job)

    if is_china_scope:
        foreign_name_rule = """     * **Chuẩn phiên âm tên người & họ nhân vật Trung Quốc theo Viện Quốc ngữ Hàn Quốc (`외래어 표기법 준수 — 중국인 등장인물에 한국식 성씨 '김 씨·박 씨·이 씨' 절대 금지`)**:
       - Vì chủ đề tập này thuộc phạm vi Trung Quốc, TẤT CẢ nhân vật người Trung Quốc (`金某`, `李某`, `林某`, `陈某`, `张某`, `王某`, `刘某`) BẮT BUỘC phiên âm theo âm chuẩn tiếng Trung hiện đại: `金某` -> **`진 씨` (Jin)**, `陈某` -> **`천 씨` (Chen)**, `林某` -> **`린 씨` (Lin)**, `张某` -> **`장 씨` (Zhang)**, `王某` -> **`왕 씨` (Wang)**, `刘某` -> **`류 씨` (Liu)**, `李某` -> **`리 씨` (Li)** (cấm gọi người Trung Quốc là `김 씨`/`박 씨` hoặc đọc âm Hán-Hàn cổ)."""
    else:
        foreign_name_rule = """     * **Chuẩn chính tả tên riêng & phiên âm theo Viện Quốc ngữ Hàn Quốc (`국립국어원 외래어·고유명사 표기법 준수`)**:
       - Mọi tên người, địa danh và thuật ngữ phải tuân thủ đúng nguồn quốc gia thực tế của chủ đề hồ sơ kênh (tuyệt đối không gán nhầm quy tắc họ tên của quốc gia khác vào chủ đề hiện tại)."""

    if custom_register:
        register_and_quote_block = """     * **TÔN TRỌNG 100% GIỌNG ĐIỆU & ĐUÔI CÂU RIÊNG CỦA HỒ SƠ KÊNH (`채널 프로필 고유 화법·어미 100% 자율 존중 — 뉴스 '~습니다' 강제 금지`)**:
       - Hồ sơ kênh này sử dụng phong cách/đuôi câu sáng tạo riêng (ví dụ `해요체`, thư tâm tình `편지체`, suy ngẫm/mục vụ `은혜의 편지`, tản văn `에세이` hoặc giọng kể riêng trong `voice_and_structure` / `creative_brief`).
       - **BẮT BUỘC viết 100% theo đúng đuôi câu và nhịp cảm xúc mà hồ sơ kênh đã chọn** — TUYỆT ĐỐI KHÔNG ép về văn thời sự điều tra `~습니다/입니다`!
       - Vẫn giữ nguyên kỹ thuật tối ưu cho giọng đọc TTS tiếng Hàn: câu có vị ngữ mềm mại tự nhiên (tiết chế câu cụt danh từ `체언 종결`), đoạn văn thở bất đối xứng tự nhiên theo cảm xúc (`1–5 câu`, cấm chia đều tăm tắp mọi khổ 4 dòng máy móc), và giới thiệu rõ ngữ cảnh trước lời trích dẫn."""
    else:
        haoche_note = (
            "Giữ lời thoại lịch sử/kinh điển tự nhiên đúng bối cảnh thời đại của hồ sơ kênh."
            if allow_archaic
            else "CẤM TUYỆT ĐỐI văn dịch cổ trang `하오체` (`~소 / ~이오 / ~하오` như `'맞소'`, `'처음이오'`, `'같소'`) trong các chủ đề hiện đại; phải dùng tiếng Hàn hiện đại tự nhiên 100%."
        )
        register_and_quote_block = f"""     * **TƯ DUY NHỊP VĂN PHÁT THANH HÀN QUỐC CHO GIỌNG ĐỌC TTS (`한국어 방송 다큐멘터리 입말 원칙` — KHÓA CHẶT 11 LỖI TÁI PHÁT)**:
       - **Phối nhạc đuôi câu cân bằng tự nhiên (`~습니다 90% 도배 절대 금지` & `~는데요/~더군요 역진자 금지`)**:
         1. **Động từ chủ động `~습니다 / ~었습니다` (`58%–72%`, TỐI ĐA `4` câu liên tiếp)**: Tuyệt đối CẤM đóng đinh `~습니다/였습니다` trên `75%` làm giọng đọc 25 phút phẳng lì! Cứ sau 2–4 câu `~습니다`, phải đổi sang câu quan sát `~었죠`, câu rỉ tai giải mã `~거든요`, câu hỏi điều tra `?`, câu kết luận `~던 겁니다`, hoặc câu phanh nhịp ngắn.
         2. **Câu quan sát & đồng cảm `~었죠 / ~았죠 / ~였죠` (`10%–16%`, ~18–28 câu/tập 25 phút)** & **Câu giải thích rỉ tai đời thực `~거든요` (`3%–6%`, ~5–12 câu/tập)**: Đặt tự nhiên ở điểm lật chi tiết, lý giải động cơ ngầm hoặc chuyển mạch (cấm đặt 2 câu `~죠` hoặc `~거든요` sát liền nhau).
         3. **Câu hỏi điều tra gợi mở (`?` — `~었을까요?`, `~었단 말일까요?`, `4%–8%`, ~8–14 câu)** & **Giải mã nhân quả `~던 겁니다 / ~셈입니다` (`4%–8%`, ~6–12 điểm rơi thật sự)**.
         4. **Câu phanh nhịp cực ngắn (`초단문 브레이크`, `<= 16` ký tự không khoảng trắng) — Bắt buộc dùng câu động từ ngắn hoàn chỉnh & CẤM TUYỆT ĐỐI đuôi danh từ cụt lặp ý cuối đoạn (`문단 끝 체언 종결 동어반복 전면 금지`)**: Ở các đỉnh cao trào hoặc điểm rơi lạnh sống lưng, thả câu phanh nhịp ngắn có vị ngữ hoàn chỉnh (`증거는 사라졌습니다.`, `답은 하나뿐이었습니다.`, `시계는 멈춰 섰죠.`). **TUYỆT ĐỐI CẤM đặt cụm danh từ cụt (`체언 종결`) ở cuối đoạn văn chỉ để nhại lại/tóm tắt câu đứng ngay trước đó** (cấm tuyệt đối kiểu `단 여섯 평의 철제 방.`, `칠천육백일흔 날의 은신.`, `끊어진 전화선 한 가닥.`, `강제 침입 흔적 영 건.`, `반쪽 장문과 사십이 호 작업화.`, `단칸방에 남겨진 신분증 한 장.`, `방수포 아래의 어둠.`, `창살 없는 고철 감옥.`, `스물한 번의 겨울.`, `단 하나의 표적.`, `버려진 종이컵 하나.`, `99.99퍼센트의 일치.`, `열여섯 개 특징점의 일치.`, `법정 최고형 확정.` = `0%`) và CẤM đoạn văn 1 dòng danh từ cụt (`standalone_one_line_noun_crutch_excess`). Mọi đoạn văn phải khép bằng câu vị ngữ tự nhiên (`~습니다`, `~었죠`, `~거든요`, `~겁니다`, hoặc `?`).
         5. **KHÓA CHẶT THÁI CỰC NGƯỢC (`~더군요 = 0%`, `~는데요. <= 1%`) & CẤM CÂU DẪN MC CHUYỂN CẢNH (`MC 진행투 메타 전환문 = 0%`)**: Tuyệt đối CẤM dùng `~더군요` ở lời dẫn ngôi thứ 3, CẤM đẩy câu sang đuôi treo `~는데요.` (tối đa `0–1` câu toàn bài), và CẤM các câu dẫn chương trình kiểu MC thuyết trình như `"그날 새벽의 ... 도로로 시선을 옮겨 보겠습니다"`, `"지금부터 하나씩 따라가 보겠습니다"`, `"자, 그럼 ... 살펴보겠습니다"`! Chuyển cảnh trực tiếp bằng mốc thời gian/không gian cụ thể.
       - **Cấm gắn nhãn nhân vật kiểu biên bản công an (`[나이] + [직업/신분] + [이름]` 공식 반복 금지)**:
         * TUYỆT ĐỐI CẤM giới thiệu người mới theo khuôn rập `[Tuổi] + [Nghề nghiệp] + [Tên]` lặp đi lặp lại (`"마흔여덟 살의 모 사장"`, `"스물여섯 살 청년 천쉰민"`, `"스물두 살이던 천쉰민"`). Hãy dẫn nhân vật từ hành động, bối cảnh hoặc vai trò tự nhiên; tuổi chỉ lồng tự nhiên tối đa `1` lần khi thực sự có ý nghĩa hồ sơ.
       - **Cấm lặp chủ ngữ dày đặc ở cảnh truy vết / hiện trường (`추격·현장 장면 '수사관들은 / 담당 직원은 / 운전기사 ... 씨는' 주어 도배 금지`)**:
         * Trong cảnh truy đuổi, vây bắt hay khám xét khẩn cấp, TUYỆT ĐỐI CẤM mở đầu 4–7 câu liên tiếp bằng `수사관들은`, `담당 직원은`, `운전기사 ... 씨는`! Phải **đảo tiêu cự máy quay sang vật thể & chuyển động hiện trường** (`비상벨이 복도를 가르며 울렸습니다.`, `철문 잠금장치가 미세하게 흔들렸죠.`, `단 육십 초.`, `차량 불빛이 골목 끝으로 미끄러졌습니다.`) để giữ nhịp nghẹt thở!
       - **Cấm liệt kê sách giáo khoa (`'첫째는 ...였습니다, 둘째는 ...였습니다, 셋째는 ...였습니다'` 나열 금지)**:
         * Khi kể các quy tắc ngầm, manh mối hay điều khoản, CẤM mở đầu đồng복 `첫째는 ...였습니다, 둘째는 ...였습니다...`. Phải đan thành mạch kể chuyện biến hóa (`가장 먼저 세운 철칙은...`, `여기에 더 집요한 금기가 뒤따랐죠.`, `무엇보다 섬뜩한 건 마지막 수칙이었습니다.`).
       - **Nhịp thở đoạn văn bất đối xứng & Cấm vòng lặp kéo giờ sau tuyên án**:
         * Đoạn văn co giãn `1–2 câu` ở điểm phanh nhịp và `3–5 câu` ở đoạn triển khai (cấm chia đều 4 dòng). Sau khi đã tuyên án/khép hồ sơ ở Hồi cuối, **kết thúc gọn và đọng dư âm trong `<= 8–10` câu**, TUYỆT ĐỐI CẤM vòng ngược lại phân tích tâm lý 20 năm trốn chạy một lần nữa để câu giờ!
     * **LUẬT DẪN LỜI NHÂN VẬT CHO TTS (`화자 선행 원칙`)**:
       - Ưu tiên tường thuật gián tiếp / bán trực tiếp nêu rõ người nói trước; chỉ trích nguyên văn `"..."` tối đa `2–5` câu ngắn đắt giá nhất toàn bài (trừ khi hồ sơ kênh cấu hình `secondary_voice_id` riêng), tách sạch dấu ngoặc kép khỏi đuôi `~라는`.
       - {haoche_note}"""

    outro_mode = _resolve_outro_mode(job)
    if outro_mode == "standalone_case_closure":
        outro_rule_line = (
            "   - **5 dòng cuối của mỗi tập BẮT BUỘC khép lại độc lập 100% trong khuôn khổ chính vụ án này bằng dư âm hồ sơ sâu sắc (`standalone_case_closure`)** — TUYỆT ĐỐI KHÔNG nhắc tên hay bắc cầu sang bất kỳ vụ án nào khác ở cuối bài!"
        )
    else:
        outro_rule_line = (
            "   - **5 dòng cuối của mỗi tập BẮT BUỘC khép lại bằng dư âm hồ sơ sâu sắc + bắc cầu tự nhiên (Retention Bridge) sang một vụ án anh em cùng luồng đang có trên kênh** (nếu kênh chưa có danh sách video anh em thì khép độc lập 100% trên chính vụ án này, tuyệt đối không bịa tên hồ sơ khác)!"
        )

    if is_creative_audio_drama_job(job):
        bp = select_audio_drama_narrative_blueprint(job)
        drama_chars = round(minutes * 278)
        ch_weights = bp["chapter_weights"]
        ch_cnt = bp["chapter_count"]
        ch_b = [round(drama_chars * w) for w in ch_weights]
        ch_lines_rendered = "\n".join(
            f"     * **{'COLD OPEN + ' if i == 0 else ''}{tpl[0]} (`~{int(round(ch_weights[i] * 100))}%` / ~`{ch_b[i]}` ký tự)**: {tpl[1]}"
            for i, tpl in enumerate(bp["chapters_template"])
        )
        sec1_block = f"""1. BẮT BUỘC PHÁC THẢO COLD OPEN 0:00 + {ch_cnt} CHƯƠNG THEO HỆ THỐNG 5 THỂ LOẠI × 6 CÁCH MỞ × 4 XƯƠNG SỐNG (`{bp['spine_id']}` — `0%` SPOKEN CTA):
   - TUYỆT ĐỐI KHÔNG viết ứng tác `script.md` ngay từ đầu mà không có dàn ý chi tiết, và TUYỆT ĐỐI KHÔNG lặp lại 1 công thức rập khuôn duy nhất cho mọi tập!
   - **Tổ hợp Kiến trúc Tự sự được chọn cho tập này**:
     * **Thể loại**: `{bp['genre_label_vi']}`
     * **Cách Mở Màn tại `0:00–0:42` (`{bp['opening_id']}`)**: **{bp['opening_label_vi']}** — {bp['opening_directive_vi']}
     * **Xương Sống Kịch Bản (`{bp['spine_id']}`, `{ch_cnt} Chương`)**: **{bp['spine_label_vi']}**
   - **LUẬT COLD OPEN 0:00 GIẬT GÂN & KHÓA BÀI NGỬA (`00:00–00:42` TRƯỚC `제1장` — CẤM ĐỌC TIÊU ĐỀ CHƯƠNG HAY NGÀY THÁNG Ở CÂU ĐẦU, CẤM LỘ TWIST Ở CHƯƠNG 1)**:
     * **Cấm tuyệt đối mở dòng 1 bằng `"제1장, ..."` hay ngày tháng kiểu biên bản `"2026년 10월 18일 정오 무렵..."`!** Phải đẩy thẳng câu thoại mở màn theo đúng kiểu **`{bp['opening_label_vi']}`** (`화자 선행` ngắn gọn <= 18 chữ + lời thoại trực tiếp `"..."`) lên ngay **Giây `0:00` (Dòng 1–2)**!
     * **Dòng 3–8 (`0:08–0:42` Cold-Open Cliffhanger)**: Khắc họa chi tiết vật lý căng thẳng và khép Cold Open bằng một câu treo lửng tò mò -> **SAU ĐÓ MỚI ĐẶT DÒNG TIÊU ĐỀ `제1장, ...`** để lùi lại dẫn bối cảnh!
     * **LUẬT GIẤU BÀI NGỬA & CẤM LỘ TWIST SỚM (`Mystery Withholding Gate` — Cấm Lộ Thân Phận/Bí Mật Cốt Lõi Ở Cold Open & `제1장`)**: Ở Cold Open và suốt `제1장`, TUYỆT ĐỐI CẤM giải thích toạc ra ngay bí mật bên trong kỷ vật/chiếc hộp, và TUYỆT ĐỐI CẤM nói toạc nhân vật chính chính là vị Danh nhân / Quốc bảo ẩn danh! Người kể chuyện PHẢI GIẤU KÍN danh tính/bí mật cốt lõi đó cho đến **cuối `제2장` (Cliffhanger Chương 2)** để giữ lực căng tò mò cực đại!
   - Phân bổ dung lượng **{ch_cnt} Chương (`제1장..제{ch_cnt}장` / `ACT01..ACT0{ch_cnt}`)** theo Xương sống `{bp['spine_label_vi']}` cho thời lượng `{minutes:g}` phút ở tốc độ đêm khuya `0.94x` (tổng mục tiêu ~`{drama_chars}` ký tự tiếng Hàn không khoảng trắng):
{ch_lines_rendered}
   - **4 DẠNG XƯƠNG SỐNG XOAY VÒNG CỦA KÊNH (`0%` LẶP CÔNG THỨC GIỮA CÁC TẬP)**:
     1. **`Xương sống A` (`Ẩn Danh Phản Kích & Bẫy Nghề 2 Tầng` — 6 Chương)**: Đối kháng trực diện với sự ngạo mạn học vị/danh lợi -> Lộ danh hiệu ở cuối Chương 2 -> Cài bẫy nghề 2 tầng ở Chương 3–4 -> Phản kích kép ở Chương 5 -> Kết êm 8% ở Chương 6.
     2. **`Xương sống B` (`Buông Bỏ & Khoảng Trống Không Thể Thay Thế` — 5 hoặc 6 Chương)**: Người vợ/người mẹ điềm tĩnh rời bỏ gia đình vô ơn sau 30 năm -> Mở lại xưởng nghề bình yên -> Ngôi nhà/cơ ngơi cũ sụp đổ dây chuyền vì mất đi trụ cột vô hình -> Từ chối lời cầu xin muộn màng -> Kết êm 8–9%.
     3. **`Xương sống C` (`Bóc Tách Kỷ Vật & Nước Mắt Thức Tỉnh` — 5 Chương)**: Mở dần 3 tầng kỷ vật/biên lai cũ của người mẹ/người chị -> Bóc tách sự hy sinh thầm lặng suốt hàng chục năm -> Cao trào vỡ òa sự thật & những giọt nước mắt ăn năn -> Kết êm 9%.
     4. **`Xương sống D` (`Giải Cứu Bảo Vật & Chọn Người Kế Thừa` — 6 Chương)**: Sự cố quốc bảo/quốc yến phút 89 không ai giải nổi -> Tìm đến bậc thầy ẩn cư -> Đêm thức trắng phục chế & phép thử nhân cách truyền nhân -> Bảo vật tỏa sáng & trao truyền ấn tín -> Kết êm 8%."""
        sec5_block = f"""5. 4 BỘ LỌC CỨNG CHỐNG MÙI AI & SAI LỆCH THỰC TẾ HÀN QUỐC (`글자 수 산술 · 연도/햇수 일치 · 2024.05+ 국가유산청 고증 · AI 감탄문 75% 절삭`):
   - **Bộ lọc 1 — Cấm đếm sai số chữ tiếng Hàn (`글자 수 산술 100% 일치`)**: Tuyệt đối hạn chế lối văn mẫu AI `"…라는 N 글자"`; nếu bắt buộc viết `<문구>라는 N 글자`, phải đếm chính xác 100% từng âm tiết Hangul không tính khoảng trắng (ví dụ `경술년 상의원 대례복 침선 본` = `열두 글자` [12 chữ, CẤM ghi 9 chữ]; `국가무형유산 궁중침선 명예보유자 소담 김은숙` = `스무 글자` [20 chữ]).
   - **Bộ lọc 2 — Thống nhất toán học Năm & Số Năm (`present_year - flashback_year == N년` 100%)**: Khóa chặt `chronology_ledger` ngay từ `outline.json`! Nếu bối cảnh hiện tại là `2026년` và biến cố quá khứ là `1998년` (`2026 - 1998 = 28`), thì XUYÊN SUỐT toàn bộ các chương phải thống nhất tuyệt đối là **`28년 동안 / 이십팔 년 만에`** (CẤM TUYỆT ĐỐI lúc ghi `28년 전`, lúc lại quen tay ghi `25년 동안`!).
   - **Bộ lọc 3 — Chuẩn tên Cơ quan & Di sản Hàn Quốc từ tháng 5/2024–2026 (`국가유산청` & `국가무형유산`)**: Từ ngày 17/05/2024, Hàn Quốc đã chính thức đổi tên `문화재청` thành **`국가유산청`**, `국가무형문화재` thành **`국가무형유산`**, `국가지정문화재` thành **`국가지정유산`**. Mọi bối cảnh hiện đại `2024–2026+` BẮT BUỘC dùng tên mới chính thức, `0%` dùng tên cũ lỗi thời!
   - **Bộ lọc 4 — Cắt >= 75% câu bình luận mớm cảm xúc kiểu AI (`Show, Don't Editorialize`)**: CẤM rải các câu cảm thán/răn dạy sáo rỗng của người kể chuyện như `"참으로 무례한 말이었습니다"`, `"참으로 기막힌 노릇이었습니다"`, `"가슴이 내려앉는 순간이었습니다"`, `"과연 ... 알고 있었을까요?"`, `"과연 ... 할 수 있는 말이란 말입니까?"` (`0` lần ở Cold Open, tối đa `<= 1` câu cảm thán và `<= 3` câu `과연 ...?` trong cả tập 70 phút). Hãy để hành động, ánh mắt, tiếng đặt chén trà và sự im lặng của nhân vật tự lên tiếng!
   - **Luật `화자 선행` & Xưng Hô Thế Hệ 5070 + 0% Spoken CTA**: Dẫn rõ người nói trước mọi câu thoại `"..."`, cấm gọi người 50–65 tuổi là `노인 / 노부부 / 늙은이`, và `0%` `구독·좋아요·알림설정`."""
    else:
        sec1_block = f"""1. BẮT BUỘC PHÁC THẢO KỊCH BẢN TRƯỚC KHI VIẾT (`OUTLINE-FIRST BLUEPRINT` — MỞ BÀI LINH HOẠT THEO CHỦ ĐỀ & KHÔNG BAO GIỜ LẶP LẠI CTA):
   - TUYỆT ĐỐI KHÔNG viết ứng tác `script.md` ngay từ đầu mà không có dàn ý chi tiết. Sau khi có `research.md`, bạn BẮT BUỘC phải lập và lưu `outline.json` (phác thảo kịch bản theo các Hồi/Chương phù hợp với DNA của hồ sơ kênh) TRƯỚC KHI viết `script.md`.
   - **CẤU TRÚC MỞ BÀI CHUẨN WINNER CỦA KÊNH (`Mỏ neo Nghịch lý Vỏ bọc Hai Mặt & Hiện trường Khóa kín 00:00–03:30`) & HÌNH THÁI CTA ĐỘC BẢN**:
     * **Công Thức Hook Winner Đã Kiểm Chứng Của Kênh (`길광 76k`, `벙어리 67k`, `마한칭 48k`, `바이인시 매점 45k`, `남문촌 35k`, `천쉰민 29k`, `쑨샤오궈 25k`)**:
       1. **CẤM TUYỆT ĐỐI tả cảnh thời tiết/môi trường rườm rà ở câu đầu** (`"체감온도 사십 도에 육박하는..."`, `"새벽 다섯 시 반, 차가운 물안개가..."` = `0%`).
       2. **Câu 1–3 (Đặt Mỏ Neo Quy Mô / Hiện Trường Khóa Kín / Lệnh Truy Nã Cấp A)**: Đi thẳng vào dữ kiện thật chấn động nhất của hồ sơ (con số quy mô vây bắt hàng nghìn cảnh sát / 6.000 camera CCTV / lệnh truy nã cấp A của Bộ Công an / 17 người bốc hơi trong 1km / căn phòng khóa kín) bằng các câu đơn ngắn gọn, sắc lẹm.
       3. **Câu 4–6 (Cú Lật Nghịch Lý 180 Độ Bằng `하지만 / 그런데`)**: Đặt trực diện sự đối lập không tưởng về **Vỏ bọc Hai Mặt hoặc Ẩn thân ngay dưới mũi cảnh sát** (ví dụ: trong lúc 4.000 cảnh sát lùng sục rừng sâu thì kẻ bị truy nã lại bật điều hòa nằm ngủ ngay trên tầng 2 trụ sở Ủy ban thôn cách sở chỉ huy không xa, rồi giữa ban ngày ngang nhiên phóng xe máy lao thẳng vào chốt kiểm soát; hoặc kẻ truy nã cấp A lại đang làm diễn viên truyền hình / bán căng-tin trường học / lái xe ba gác ngay cạnh đồn công an).
       4. **Câu 7–8 (Câu Hỏi Điều Tra Cốt Lõi & Chuyển Thẳng Vào Ngày Khởi Phát Vụ Án)**: Đặt câu hỏi điều tra giữ chân khán giả (`어떻게 ... 수 있었을까요?`) rồi dẫn trực tiếp vào mốc ngày tháng & địa điểm khởi phát hồ sơ vụ án (`2020년 7월 21일 밤, 중국 장시성 러안현...`).
     * **Hình Thái & Cấu Trúc Câu CTA Theo Câu Chuyện (`{variant['cta_rhetorical_form']}` — {variant['cta_form_label_vi']})**: {variant['cta_form_directive_vi']}
     * **Kiểu Kết Bài & 5 Dòng Cuối Tập (`{variant['ending_mode']}` — {variant['ending_label_vi']})**: {variant['ending_directive_vi']}
   - Phân bổ dung lượng tham chiếu trong `outline.json` cho thời lượng `{minutes:g}` phút (tổng mục tiêu ~`{ideal_chars}` ký tự tiếng Hàn không khoảng trắng, triển khai nội dung từng Chương/Hồi đúng theo chủ đề & `editorial_dna` của hồ sơ kênh):
     * **Phần/Hồi 1 (`ACT01`, ~13% / ~`{act1_chars}` ký tự không khoảng trắng)**: Cold Open & Mỏ neo Nghịch lý Vỏ bọc Hai Mặt / Hiện trường Khóa kín (00:00–03:30, 100% Xanh tiền trong 60s đầu, đi thẳng vào mỏ neo nghịch lý + cú lật `하지만 / 그런데` sắc lẹm chuẩn các video Win của kênh, CẤM CTA trong 2 phút đầu, CẤM câu tua ngược đồng hồ `"시계를/시간을 ... 되돌려 봅니다"` và CẤM câu dẫn MC `"그날 새벽의 ... 도로로 시선을 옮겨 보겠습니다"`).
     * **Phần/Hồi 2 (`ACT02`, ~23% / ~`{act2_chars}` ký tự không khoảng trắng)**: Triển khai bối cảnh, cơ chế hoặc nút thắt đầu tiên theo đúng dàn ý `outline.json` của hồ sơ kênh (0% CTA chặn ngang).
     * **Phần/Hồi 3 (`ACT03`, ~26% / ~`{act3_chars}` ký tự không khoảng trắng)**: Đào sâu mạch phát triển trung tâm, bằng chứng, chiều sâu nhân vật hoặc hệ thống theo `outline.json`.
     * **Phần/Hồi 4 (`ACT04`, ~22% / ~`{act4_chars}` ký tự không khoảng trắng)**: Cao trào, bước ngoặt quyết định hoặc điểm mở khóa cốt lõi của câu chuyện.
     * **Phần/Hồi 5 (`ACT05`, ~16% / ~`{act5_chars}` ký tự không khoảng trắng)**: {variant['act5_title_suffix_vi']} — triển khai đúng kiểu kết `{variant['ending_mode']}` và hình thái `{variant['cta_rhetorical_form']}`, viết mới 100% 5 dòng cuối tập.
   - **5 LĂNG KÍNH TỰ SỰ LINH HOẠT THEO ĐẶC THÙ VỤ ÁN (`5 CASE-DRIVEN NARRATIVE LENSES` LỒNG TRONG KHUNG 5 HỒI `ACT01 -> ACT05`)**: Giữ nguyên trục xương sống 5 Hồi (`ACT01..ACT05`) đồng thời chọn 1 trong 5 Lăng Kính Tự Sự phù hợp nhất với bản chất hồ sơ vụ án:
     1. **`Forensic Trace Reverse-Reconstruction` (Giải phẫu Ngược từ Vật chứng & Dị điểm Hiện trường)**: Mở từ một mẫu vật vi lượng, biên bản kiểm toán hoặc dị điểm vật lý tại hiện trường hiện tại, bóc ngược từng lớp ngụy trang về quá khứ qua 5 Hồi.
     2. **`Dual-Timeline Cat & Mouse` (Song hành 2 Trục Thời Gian: Dấu vết Quá khứ vs. Truy vết Hiện tại)**: Đan cài song song chuỗi manh mối đứt quãng trong quá khứ và cuộc đối chiếu pháp y / dữ liệu hiện đại.
     3. **`Rashomon / Multi-Witness Contradiction` (Đối chiếu Lời khai Mâu thuẫn & Điểm mù Nhân chứng)**: Triển khai các Hồi quanh sự vênh nhau giữa các lời khai và góc khuất vật lý cho đến khi vật chứng khách quan lật tẩy.
     4. **`Systemic Web & Audit Trail` (Giải phẫu Mạng lưới Tài chính / Kho bạc / Lỗ hổng Hệ thống)**: Lần theo dòng tiền, biên bản niêm phong két sắt, sổ cái giả mạo và kẽ hở kiểm soát nội bộ tới điểm gãy toàn cục.
     5. **`Psychological Interrogation Duel` (Đấu trí Tâm lý trong Phòng Thẩm vấn & Phá vỡ Alibi)**: Đặt trọng tâm 5 Hồi vào cuộc đấu trí nghẹt thở trong phòng thẩm vấn để bẻ gãy từng mắt xích ngoại phạm.
   - Khi viết `script.md`, phải **triển khai tuần tự từng Phần/Hồi bám sát 100% vào `outline.json` đã phác thảo**."""
        sec5_block = f"""5. LUẬT ĐỘ DÀI CHUẨN KÊNH (24–30 PHÚT = 9.500–11.500 KÝ TỰ), ĐÀO SÂU ĐẤU TRÍ 3 TẦNG & KẾT BÀI CHUẨN DNA KÊNH (`분량 축소 절대 금지 · 3단계 수사 심리전 · 채널 맞춤형 엔딩`):
   - Với tập dài `24–30` phút, tổng độ dài văn bản đọc trong `script.md` BẮT BUỘC đạt **`9.500 – 11.500` ký tự (`~185–215` câu)**: TUYỆT ĐỐI CẤM lướt nhanh tóm tắt mà phải đào sâu đủ **3 tầng đấu trí thực địa & tâm lý**: `(Tầng 1)` Quy mô rà soát khổng lồ & ngõ cụt bế tắc -> `(Tầng 2)` Chi tiết vi mô đời thực mở khóa bước ngoặt (đường kim mũi chỉ, vết dầu, mẫu vật, con số lệch sổ cái, phác họa nhân chứng) -> `(Tầng 3)` Khép vòng vây nghẹt thở & màn đấu trí tâm lý từng nhịp hỏi-đáp trong phòng thẩm vấn!
   - **Đặt 2 điểm CTA tự nhiên, hợp ngữ cảnh ở khoảng phút thứ 8 (quãng chuyển giao giữa Hồi 2 $\\rightarrow$ Hồi 3) và ở cuối video**, tuyệt đối KHÔNG thêm cứng nhắc hay lặp lại 1 câu mẫu cố định giữa hai điểm CTA, cấm câu lùi thời gian `"시계를/시간을 ... 되돌려 봅니다"`, cấm khung câu CTA công nghiệp `[~하시려면 / ~싶으시다면 / ~응원하신다면] + [구독과 좋아요/알림 설정을 눌러...]`, và **CẤM TUYỆT ĐỐI kiểu chào tạm biệt hiền lành chung chung** (`"긴 시간 끝까지 함께해 주셔서 고맙습니다"`, `"끝까지 시청해 주셔서 감사합니다"`, `"다음 시간에도 ... 찾아뵙겠습니다"`).
{outro_rule_line}"""

    return f"""MANDATORY OUTLINE-FIRST SCRIPT ARCHITECTURE & NATIVE KOREAN BROADCAST PROSE RULES (채널 프로필 DNA 맞춤형 한국어 자연 구어체 문법 · 100% 수익창출 녹색 달러 심의 화법 · AI 번역투 배제 · TTS 호흡 최적화):
{sec1_block}

2. ROLE KIỂM DUYỆT CHÍNH SÁCH YOUTUBE (15/07/2025 – HIỆN TẠI), CÁCH VIẾT XANH TIỀN 100% ĐÀI TRUYỀN HÌNH & LOẠI BỎ VĂN PHONG AI (`cofi-youtube-policy-monetization-guard` · `유튜브 수익창출 100% 녹색 달러 방송 심의 문법 · 초반 60초 청정 구역 · 법의학 간접 굴절 · AI 번역투 완전 제거`):
   - **TRƯỚC KHI VIẾT DÀN Ý (`outline.json`) HOẶC KỊCH BẢN (`script.md`), BẮT BUỘC KÍCH HOẠT ROLE GIÁM SÁT CHÍNH SÁCH YOUTUBE TỪ 15/07/2025 ĐẾN NAY (`cofi-youtube-policy-monetization-guard`)**:
     * **Chính sách YPP 'Inauthentic Content' (15/07/2025 – nay, thay thế 'Repetitious Content') & 'Reused Content'**: Nghiêm cấm viết kịch bản theo khuôn đúc công nghiệp lặp lại giữa các tập (`templated mass-produced storytelling`) hoặc đọc chép lại thông cáo/báo chí nguyên văn không có giá trị phân tích điều tra độc lập. Mỗi tập phải có cấu trúc mở bài, nhịp câu, lăng kính pháp y/kiểm toán và kết bài độc bản.
     * **Chính sách 'Altered or Synthetic Media' (2025 – nay)**: Tuyệt đối không ngụy tạo lời thú tội, băng ghi âm hay tài liệu giả làm bằng chứng thật; mọi câu trích dẫn phải có thật trong hồ sơ điều tra.
   - **LUẬT XANH TIỀN TUYỆT ĐỐI TRONG CÁCH VIẾT (`SBS 그것이 알고 싶다 / 꼬꼬무` 방송 심의 통과 화법 — KHÔNG CẦN NÉ CHỦ ĐỀ MÀ PHẢI VIẾT SẠCH TỪ GỐC)**:
     * **Vùng Kim Cương 60 Giây Đầu (`00:00–01:00` / `6–8` câu mở đầu `ACT01`)**: **`0%` từ vựng tử vong, tước đoạt sinh mạng, thi thể, máu, vũ khí, hành vi sát hại/tấn công, tự sát hay bạo lực** (`생명을 앗아간/목숨을 앗아간/살인/살해/사망/숨진/시신/사체/백골/피/혈흔/총/총성/칼/흉기/폭행/자살/성폭행/학대` = `0%`). Trong 60s đầu, sự tò mò nghẹt thở BẮT BUỘC được tạo ra từ **nghịch lý vật chứng, sự bốc hơi không dấu vết, con số sổ cái phi lý, quy luật đời thường bị đứt gãy, hoặc hai cuộc đời đối lập**!
     * **Khúc Xạ Pháp Y & Tư Pháp Toàn Tập (`ACT01..ACT05` — 0% Gore / 0% Violence Mechanics)**: Xuyên suốt toàn bộ kịch bản 27 phút, **TUYỆT ĐỐI CẤM** miêu tả cơ chế ra tay bạo lực trực diện (đâm, chém, siết cổ, nổ súng vào người, tra tấn), tình trạng thi thể/phân hủy/hài cốt (`토막`, `부패`, `백골`, `피웅덩이`), tội phạm tình dục, xâm hại trẻ em hoặc cách thức tự sát/hành quyết. Khi đề cập hậu quả trọng án, BẮT BUỘC khúc xạ sang ngôn ngữ điều tra & hồ sơ pháp y gián tiếp chuẩn đài truyền hình:
       - Thay cho mô tả sát hại/thi thể: `"그날 밤 이후 행적이 완전히 끊겼습니다"`, `"돌이킬 수 없는 비극이 벌어진 뒤였죠"`, `"피해자는 끝내 집으로 돌아오지 못했습니다"`, `"현장에서는 결정적인 미세 시료가 확보됐습니다"`.
       - Thay cho mô tả vũ khí/đổ máu: `"현장 감식 결과 결정적인 물리적 흔적이 드러났습니다"`, `"단 몇 분 만에 내부 통제선이 무너졌죠"`.
       - Thay cho mô tả tử hình/tự sát: `"법정 최고형이 확정되며 긴 추적의 기록은 마침표를 찍었습니다"`, `"끝내 법정에 서지 못한 채 모든 진술이 멈췄습니다"`.
   - **CẤM TUYỆT ĐỐI CÁC CẤU TRÚC CÂU MÙI AI / DỊCH MÁY (`AI 상투어 · 번역투 문장 금지 목록`)**:
     * **Cấm công thức đối lập sáo rỗng số 1 của AI**: Tuyệt đối KHÔNG viết `"이것은 단순한 A가 아니라 B였습니다"`, `"단순한 ... 아닌 치밀하게 설계된 ..."`. Hãy nói thẳng vào sự thật cụ thể.
     * **Cấm bị động dịch máy (`~에 의해`, `~되어지다` 금지)** và **cấm danh từ hóa nặng nề (`~라는 것`, `~하는 것이 가능했다`, `~의 과정을 통해` 남발 금지)**: Luôn chuyển sang câu chủ động tiếng Hàn gọn, tự nhiên.
     * **Cấm lạm dụng đại từ dịch máy (`그`, `그녀`, `그의`, `자신의` 과다 사용 금지)** và **cấm từ nối bài luận AI** (`"결론적으로"`, `"한편"`, `"뿐만 아니라"`, `"요약하자면"`, `"그렇다면 과연 진실은 무엇일까요?"`).
{foreign_name_rule}
{register_and_quote_block}

3. CẤM VIẾT HOA MỸ, CẤM BẤM GIỜ CỰC ĐOAN & LUẬT 4 TẦNG ĐỘ DÀI CÂU (`미사여구 · 과장된 수식어 · 신파조 절대 금지 · 40~50자 획일화 절대 금지 · 초단문 브레이크 필수`):
   - Không dùng tính từ phóng đại sướt mướt (`"악마 같은 미소"`, `"피눈물이 강을 이루고"`, `"운명의 수레바퀴"`, `"실로 경악을 금치 못할"`, `"지옥도가 펼쳐졌습니다"`).
   - **Cấm nhồi số liệu bấm giờ cực đoan (`0.05초`, `0.1초`, `0.2초` 남발 절대 금지)**: Không bịa các con số phần trăm giây phi thực tế làm giả độ kịch tính và giảm tính chân thực của hồ sơ điều tra.
   - **Đan xen 4 tầng độ dài câu tương phản mạnh (PHÁ VỠ HOÀN TOÀN ĐỘ DÀI ĐỒNG PHỤC 40–50 KÝ TỰ)**:
     1. **Câu phanh nhịp cực ngắn (`초단문 브레이크`, `2–5` chữ / `3–16` ký tự không khoảng trắng, `>= 6%–12%`, dùng câu động từ ngắn hoàn chỉnh như `증거는 사라졌습니다.`, `답은 하나뿐이었습니다.`, `시계는 멈춰 섰죠.`; CẤM TUYỆT ĐỐI đặt cụm danh từ cụt `체언 종결` ở cuối đoạn văn để nhại lại câu đứng trước như `단 여섯 평의 철제 방.`, `99.99퍼센트의 일치.`, `법정 최고형 확정.`)** ghìm nhịp ở cao trào.
     2. **Câu ngắn sắc gọn (`단문`, `16–24` ký tự không khoảng trắng, `~15%–22%`)** chuyển ý dứt khoát.
     3. **Câu dẫn chuyện trung bình (`중문`, `25–37` ký tự không khoảng trắng, `~42%–50%`)** nối mạch tự nhiên.
     4. **Câu triển khai chi tiết (`장문`, `38–54` ký tự không khoảng trắng, `<= 22%`)** — TUYỆT ĐỐI CẤM xếp 3 câu dài 40–50 chữ liên tiếp mà không có câu ngắn/cực ngắn cắt nhịp!

4. CHUẨN CHÍNH TẢ PHÁT ÂM TTS & HÌNH THÁI HỌC TIẾNG HÀN TUYỆT ĐỐI (`연도 단위 '년' 통일 · 소수점 붙여쓰기 · 고유어 수사 한글 표기 · 맞춤법/음운 함정 원천 차단`):
   - **CẤM TUYỆT ĐỐI dùng đơn vị `해` sau số đếm để chỉ số năm trôi qua (`열아홉 해`, `열여덟 해`, `열 해`, `19해` 절대 금지 -> BẮT BUỘC viết `19년`, `18년`, `10년`)**:
     * Trong TTS tiếng Hàn, `[Số đếm] + 해 [hɛ]` bị đồng hóa âm đọc giống hệt `회 [hwɛ/hɛ]` ("19 lần / 18 lần" thay vì "19 năm / 18 năm")!
     * BẮT BUỘC dùng đơn vị Hán-Hàn **`년`** (`19년의 시간을`, `18년의 공백`, `18년 전 장부`, `10년이 넘도록`, `18년하고도 하루`, `17년을 버티다`) và chia đúng trợ từ có 받침 (`년이`, `년을`, `년은`, `년과`, `년으로`, `년이라는`, `년이었다`).
     * Các năm dương lịch 4 chữ số viết gọn bằng số Ả Rập + `년` (`1997년`, `2015년` — cấm viết dài dòng `천구백구십칠 년`, `이천십오 년`).
   - **Số thập phân & tỷ lệ phần trăm BẮT BUỘC viết liền quanh chữ `점` (`구십구점구구 퍼센트` hoặc `99.99퍼센트`, cấm `구십구 점 구구 퍼센트` hoặc ký hiệu `%`)**:
     * TUYỆT ĐỐI KHÔNG chèn khoảng trắng quanh `점` khi viết số thập phân bằng chữ Hangul (`구십구 점 구구 퍼센트` khiến TTS bị vấp lặp hai lần `99.99%를 99%를`). Hãy viết `99.99퍼센트` hoặc viết liền `구십구점구구 퍼센트`.
   - **Số đếm `1..20` đi kèm đơn vị thuần Hàn BẮT BUỘC viết chữ Hangul có dấu cách (`10개/2장/8개/9점` 아라비아 숫자 표기 절대 금지)**:
     * BẮT BUỘC viết: **`서류 두 장`**, **`단서 아홉 점`**, **`열쇠 세 개`**, **`여덟 개`**, **`차량 두 대`**, **`공범 네 명`**, **`계좌 여덟 개`**, **`통화 여섯 번`**, **`가방 한 개`** (TUYỆT ĐỐI CẤM viết `10개`, `2장`, `8개`, `9점` dễ khiến TTS đọc nhầm thành Hán-Hàn `십개`, `이장`, `구점`!).
     * Với cụm Hán-Hàn **`사대 보험`** (`4대 보험`), viết rõ **`사대 보험`** để TTS không bao giờ đọc nhầm thành `네대 보험 (내대보험)`. Đơn vị Hán-Hàn (`19년`, `7월 30일`, `1,500만 위안`, `50대 후반`) giữ đúng âm Hán-Hàn (cấm `"열아홉 년"`).
     * **CẤM TUYỆT ĐỐI ghép lai số Hán-Hàn hàng nghìn/trăm với số thuần Hàn + `날` (`칠천육백일흔 날` 절대 금지)**: Luôn viết chuẩn Hán-Hàn **`7,670일` (`칠천육백칠십 일`)**.
     * **CẤM TUYỆT ĐỐI viết tách `이 세대` trước danh từ kỹ thuật/hành chính (`이 세대 전자 주민신분증` 절대 금지 — TTS đọc nhầm `이` thành đại từ chỉ định "này")**: Bắt buộc viết liền **`2세대 전자 주민신분증` (`이세대`)**.
     * **CẤM TUYỆT ĐỐI viết thừa `일천` trước hàng trăm (`일천이백여 곳` 절대 금지)**: Bắt buộc viết tự nhiên **`천이백여 곳` (`1,200여 곳`)**.
   - **Cấm tuyệt đối ký hiệu pha trộn Hàn - Anh - Số & số 0 đầu biển số/số hiệu (`웨AR0747호`, `양산 095호`, `A급`, `100여만`, `%` 절대 금지)**:
     * TẤT CẢ biển số xe, số hiệu tàu/phòng có chữ cái hoặc số `0` đứng đầu, cấp độ truy nã, từ viết tắt tiếng Anh và phần trăm BẮT BUỘC viết tách bằng chữ Hangul trong `script.md` và `narration_text`:
       - `웨AR0747호` -> **`웨 에이알 공칠사칠 호`**; `0747호` -> **`공칠사칠 호`**; `양산 095호` -> **`양산 공구오 호`**
       - `A급 수배령` -> **`에이급 수배령`** (hoặc **`일급 수배령`**); `CCTV` -> **`씨씨티비`**; `DNA` -> **`디엔에이`**; `%` -> **`퍼센트`**
       - `100여만 위안` -> **`백여만 위안`**; `1,000여만 원` -> **`천여만 원`**; `10여 년` -> **`십여 년`**
   - **Khóa tuyệt đối bẫy phát âm `0건`, đồng nhất 100% tên địa danh/nhân vật (`닝보시`, `시에런량`), âm `셰 (Xie -> 시에)`, ký hiệu số hiệu & chuẩn hình thái học tiếng Hàn**:
     * TUYỆT ĐỐI CẤM viết `0건` (TTS dễ đọc nhầm thành `연건`) -> hãy viết **`단 한 건도 없었습니다`** hoặc **`영 건`**.
     * **CẤM TUYỆT ĐỐI âm `셰` trong mọi tên riêng tiếng Trung (`谢` Xie)** và **CẤM viết lệch tên địa danh/nhân vật giữa các đoạn (`딩보시/닉보시` X -> `닝보시` O; `시혜런양/시언양/시에양` X -> `시에런량` O)**: Mọi địa danh và tên nhân vật phải đồng nhất 100% một cách viết chuẩn duy nhất từ dòng đầu đến dòng cuối (**`시에런량`**, **`시에쭝펀`**, **`우시에위`**, **`시에 씨`**).
     * **Chuẩn chính tả & hình thái học tiếng Hàn (`한글 맞춤법 제18항·제40항·제51항·제57항`)**: Bắt buộc viết đúng phó từ `-히/-이` (**`나란히`**, `간간이`, `일일이`, `가만히`), chia động từ gốc `ㄹ` đúng `-아/-어` (**`연달아`**, **`잇달아`** — cấm `연달라/잇달라`), bị động `-어지다` (**`포개졌습니다 / 포개어졌습니다`** — cấm `포개해졌습니다`), tính từ sắc thái (**`새까맣게`** — cấm `시커먹게/시커멓게`), và từ vựng chuẩn (**`수완 좋기로`**, **`단숨에 탄로 날 외통수였습니다`**, **`역력했죠`** — cấm `수환 조키로`, `단수 메탈로`, `영역했죠`).
     * **Tất cả số hiệu kiểu mẫu & phiên hiệu đơn vị (`NN식`, `NNN호/연대`) BẮT BUỘC viết rõ âm đọc Hangul**: `56식` -> **`오륙식`** (áp dụng đúng 두음법칙 `륙`, cấm viết `56식`), `81식` -> **`팔일식`**, `54식` -> **`오사식`**, `147연대` -> **`백사십칠 연대`**.
   - **Cấm dùng Regex xóa chủ ngữ mù quáng (`Zero Regex Subject Stripping Law`)**: Giữ nguyên sự tương hợp Định ngữ – Danh từ trung tâm (`수식어-피수식어 호응`).

{sec5_block}
"""


_EDITORIAL_DNA_STRIP_ALWAYS = {
    "curated_today_candidates",
    "dna_case_vault",
    "topic_memory",
    "suggested_topic_history",
    "topic_streams",
    "winner_titles",
    "latest_5_reference_videos",
    "reference_videos",
    "recent_videos",
    "self_learning_memory",
    "radar_candidates",
    "korean_prose_and_grammar_rules",
    "cta_architecture",
    "script_workflow",
    "pre_publish_checklist",
    "voice_and_tts_rules",
    "subtitle_director_role",
}

_EDITING_DNA_COMPACT_KEYS = (
    "preset_id",
    "director_mode",
    "name",
    "visual_mix",
    "pacing",
    "color_grade",
    "subtitle_style",
    "audio_rules",
    "footage_hygiene_contract",
    "word_level_sync",
    "vox_satellite_enabled",
    "zero_unrelated_broll",
    "ai_visual_style",
)


def _profile_editorial_dna_direction(job: dict[str, Any], phase: str = "") -> str:
    lang = str(job.get("language") or "ko").strip().lower()
    phase_key = str(phase or "").strip().lower()
    snapshot = job.get("channel_profile_snapshot") if isinstance(job.get("channel_profile_snapshot"), dict) else {}
    raw_dna = snapshot.get("editorial_dna") if isinstance(snapshot.get("editorial_dna"), dict) else {}
    raw_editing_dna = (
        job.get("editing_dna")
        if isinstance(job.get("editing_dna"), dict) and job.get("editing_dna")
        else (snapshot.get("editing_dna") if isinstance(snapshot.get("editing_dna"), dict) else {})
    )
    if not raw_dna and not raw_editing_dna:
        return ""

    dna: dict[str, Any] = {}
    for k, v in raw_dna.items():
        if k in _EDITORIAL_DNA_STRIP_ALWAYS:
            continue
        if lang != "ko" and k == "korean_prose_and_grammar_rules":
            continue
        if phase_key and phase_key != "seo" and k in {"title_rules", "thumbnail_rules", "thumbnail_and_title_ctr_dna", "seo_rules"}:
            continue
        if phase_key and phase_key != "plan" and k in {"script_workflow", "korean_prose_and_grammar_rules", "cta_architecture", "pre_publish_checklist"}:
            continue
        dna[k] = v

    editing_dna: dict[str, Any] = {}
    if raw_editing_dna and phase_key not in {"voice", "seo"}:
        for k in _EDITING_DNA_COMPACT_KEYS:
            if k in raw_editing_dna and raw_editing_dna[k] not in (None, "", [], {}):
                editing_dna[k] = raw_editing_dna[k]

    if not dna and not editing_dna:
        return ""
    combined_payload: dict[str, Any] = {}
    if dna:
        combined_payload["editorial_dna"] = dna
    if editing_dna:
        combined_payload["editing_dna"] = editing_dna
    return """PROFILE-SPECIFIC EDITORIAL & EDITING DNA — CHANNEL-ISOLATED SKIN + PRODUCTION CONTRACT
- This DNA belongs exclusively to the selected channel profile (`editing_dna.preset_id`) and governs writing, visual planning, footage sourcing, channel skin/material isolation, Composable Lego Vox motion choreography (when Vox is enabled on this profile), and broadcast audio/subtitle decisions.
- Treat `editorial_dna` and `editing_dna` as hard production contracts: isolate surface palette, typography, AI visual style, and visual mix strictly to this profile's `preset_id`, and route every spoken beat with 100% semantic fidelity (never forcing mismatched B-roll or repeating monolithic wrapper layouts).
- Apply the reference channel's editorial decision logic to produce a 100% original documentary without copying protected wording or shot sequences.

PROFILE-SPECIFIC EDITORIAL DNA
""" + json.dumps(combined_payload if len(combined_payload) > 1 or not dna else dna, ensure_ascii=False) + "\n"


def _seo_keyword_dna_direction(job: dict[str, Any]) -> str:
    seo_dna = job.get("seo_keyword_dna") or (job.get("channel_profile_snapshot") or {}).get("seo_keyword_dna")
    if not seo_dna or not isinstance(seo_dna, dict) or not seo_dna.get("primary_title_keyword"):
        return ""
    lang = str(job.get("language") or "ko").strip().lower()
    primary = seo_dna.get("primary_title_keyword")
    meaning_vi = seo_dna.get("primary_title_keyword_meaning_vi") or ""
    secondary = seo_dna.get("secondary_anchor_keywords") or []
    rule = seo_dna.get("keyword_placement_rule") or "smart_seo_flexible"
    hashtags = seo_dna.get("mandatory_hashtags") or []
    tags = seo_dna.get("default_seo_tags") or []
    spoiler_example = (
        "`0%` spoiling the arrest clue like `...에 잡힌/무너진 진범!` or `지문 하나`"
        if lang == "ko"
        else "`0%` spoiling the arrest clue or final reveal on the thumbnail/title"
    )
    return f"""CHANNEL SEO KEYWORD DNA — TOPICAL AUTHORITY REQUIREMENTS:
- Primary Title / Channel Anchor Keyword: "{primary}" ({meaning_vi})
- Title Keyword Placement Rule: {rule}
- Secondary Anchor Keywords: {json.dumps(secondary, ensure_ascii=False)}
- Mandatory Hashtags: {json.dumps(hashtags, ensure_ascii=False)}
- Default SEO Tags: {json.dumps(tags, ensure_ascii=False)}
- For Step 01 (Research & Script): Ground the research thesis and case selection in the channel's topical authority domain ("{primary}"), while keeping spoken narration in `script.md` 100% natural broadcast prose — NEVER stuff the literal title tag "{primary}" into spoken voiceover sentences (reserve the literal tag strictly for Step 07 titles, hashtags, and metadata).
- For Step 07 (SEO & Packaging): The recommended title and title options MUST incorporate "{primary}" following the {rule} rule. Before writing any title or thumbnail copy, carefully inspect the channel's DNA (`seo_keyword_dna`, `thumbnail_dna`, `latest_5_reference_videos`, `winner_titles`, `topic_memory`) to preserve 100% of the channel's Winner style, dark investigative tone, color formula (`Line 1 White+Yellow “...”` / `Line 2 Yellow+Red !`), and open curiosity gap ({spoiler_example}), while enforcing `0%` verbatim phrase/motif copying from past videos.
"""


def _dynamic_cta_retention_direction(job: dict[str, Any]) -> str:
    lang = str(job.get("language") or "ko").strip().lower()
    snapshot = job.get("channel_profile_snapshot") if isinstance(job.get("channel_profile_snapshot"), dict) else {}
    dna = snapshot.get("editorial_dna") if isinstance(snapshot.get("editorial_dna"), dict) else {}
    narrative_dna = dna.get("narrative") if isinstance(dna.get("narrative"), dict) else {}
    brief = job.get("creative_brief") if isinstance(job.get("creative_brief"), dict) else {}
    raw_cta = (
        brief.get("cta_strategy")
        or snapshot.get("cta_strategy")
        or dna.get("cta_strategy")
        or narrative_dna.get("cta_strategy")
        or ""
    )
    if isinstance(raw_cta, dict):
        cta_strategy = str(raw_cta.get("rules_summary") or json.dumps(raw_cta, ensure_ascii=False)).strip()
    else:
        cta_strategy = str(raw_cta or "").strip()
    if is_creative_audio_drama_job(job):
        return (
            "ZERO SPOKEN CTA & SERENE BEDTIME CLOSURE ROLE (`cta_policy = \"zero_spoken_cta\"`):\n"
            "- Strictly FORBID any spoken Subscribe/Like/Notification call (`구독`, `좋아요`, `알림설정`) anywhere in the episode (opening, middle, or ending) so 5070 bedtime listeners are never startled awake.\n"
            "- Close Chapter 6 (`ACT06`) with gentle human resolution and calm nocturnal sensory stillness leading into a `4.0s` warm piano/cello fade-out.\n"
        )
    if not cta_strategy and lang != "ko":
        return ""
    variant = select_episode_narrative_variant(job)
    cta_form = variant["cta_rhetorical_form"]
    ending_mode = variant["ending_mode"]
    custom_note = f"\n- Profile CTA Policy: {cta_strategy}" if cta_strategy else ""
    sibling_bridge_block = ""
    resolved_outro = _resolve_outro_mode(job)
    if resolved_outro == "sibling_case_retention_bridge":
        siblings = _collect_channel_sibling_cases(job, limit=8)
        sibling_lines = (
            "\n".join(f"     * `{title}`" for title in siblings)
            if siblings
            else "     * Bridge organically to an established sibling fugitive/cold-case dossier on this channel."
        )
        if lang == "ko":
            sibling_bridge_block = (
                "\n  4. MANDATORY SIBLING-CASE RETENTION BRIDGE OUTRO (`outro_mode = \"sibling_case_retention_bridge\"`):\n"
                "     - NEVER close with polite generic sign-offs (`긴 시간 끝까지 함께해 주셔서 고맙습니다`, `시청해 주셔서 감사합니다`, `다음 시간에도 ... 찾아뵙겠습니다`) OR generic channel-promo filler (`우리 채널에 기록된 다음 수사 파일에서 확인해 보시기 바랍니다`).\n"
                "     - Instead, let the final 2–4 lines bridge naturally by contrasting the protagonist's modus operandi directly against ONE real published sibling case already on this channel (below — e.g., contrasting a nameless ghost who lived 21 years with zero ID against an elite fugitive like `우시에위` who used 30 forged IDs to wear a thousand faces), and close on a haunting open curiosity question (`...기괴한 도주극은 또 어떤 결말을 맞이했을까요?`):\n"
                f"{sibling_lines}"
            )
        else:
            sibling_bridge_block = (
                "\n  4. MANDATORY SIBLING-CASE RETENTION BRIDGE OUTRO (`outro_mode = \"sibling_case_retention_bridge\"`):\n"
                "     - NEVER close with polite generic sign-offs or generic channel-promo filler.\n"
                "     - Instead, let the final 2–4 lines bridge naturally by contrasting this story's modus operandi directly against ONE real published sibling dossier on this channel, closing on an open curiosity question:\n"
                f"{sibling_lines}"
            )
    elif resolved_outro == "standalone_case_closure":
        if lang == "ko":
            sibling_bridge_block = (
                "\n  4. STANDALONE CHANNEL EPISODE CLOSURE (`outro_mode = \"standalone_case_closure\"` — ZERO OTHER-VIDEO REFERENCES AT THE END):\n"
                "     - This channel profile uses 100% isolated memory and standalone episode endings. NEVER point to, name, or bridge into ANY other video or case at the end (0% mentioning other case names such as `스얼췬 사건`, `주극화 사건`, etc.).\n"
                "     - Close the final paragraph purely on the haunting factual/human contrast of THIS case, followed by a clean standalone subscription & notification invitation for upcoming real dossiers on this channel.\n"
            )
        else:
            sibling_bridge_block = (
                "\n  4. STANDALONE CHANNEL EPISODE CLOSURE (`outro_mode = \"standalone_case_closure\"` — ZERO OTHER-VIDEO REFERENCES AT THE END):\n"
                "     - This channel profile uses 100% isolated memory and standalone episode endings. NEVER point to, name, or bridge into ANY other video or case at the end.\n"
                "     - Close the final paragraph purely on the haunting factual/human contrast of THIS case, followed by a clean standalone subscription & notification invitation for upcoming dossiers on this channel.\n"
            )
    if lang != "ko":
        return f"""STORY-DRIVEN DUAL CONTEXTUAL CTA & ENDING ROLE:{custom_note}
- Place 2 natural, context-fitted CTAs (1 around minute 8 at the mid-story chapter transition, and 1 at the end of the video), NEVER repeating the same phrasing twice or using stiff formulaic templates.
- Strictly forbid any Subscribe/Like call in the first 2 minutes, never interrupt a mid-story cliffhanger with stiff CTA slots, and write the final 5 lines of every episode freshly from the specific story's human or factual aftermath (`cta_rhetorical_form = "{cta_form}"`, `ending_mode = "{ending_mode}"`).{sibling_bridge_block}
"""
    return f"""STORY-DRIVEN DUAL CONTEXTUAL CTA & ENDING CADENCE ROLE (YOUTUBE YPP / SRT SCANNER SAFE):{custom_note}
- Core Editorial Principle: Weave 2 natural, context-fitted CTAs into each episode — 1 around minute 8 (`~08:00–09:00` at the natural chapter/investigation transition) and 1 at the end of the video — NEVER repeating the same wording twice inside the episode nor reusing formulaic templates across episodes.
- MANDATORY ZERO-REPEAT & SYNTACTIC DIVERSITY EXECUTION LAWS:
  1. ZERO EARLY CTA & ZERO FLASHBACK CLICHÉS (00:00–02:00):
     - Strictly FORBID any Subscribe/Like/Channel call in the first 2 minutes. Open directly with `{variant['opening_mode']}` without stock time-rewind transitions (`시계를/시간을 ... 되돌려 봅니다`).
  2. DUAL CONTEXTUAL STORY-WOVEN CTA (1 AROUND MINUTE 8 MID-TRANSITION + 1 AT END OF VIDEO — NEVER STIFF OR FORMULAIC, `cta_rhetorical_form = "{cta_form}"`):
     - Follow `{cta_form}` ({variant['cta_form_label_vi']}): {variant['cta_form_directive_vi']}
     - CTA #1 (~Minute 8): Weave organically into the narrative bridge/question at the end of Act 2 / start of Act 3 (`~08:00–09:00`), using vocabulary drawn directly from the case's mystery or fugitive trail.
     - CTA #2 (End of Video): Weave organically into the closing reflection / sibling-case bridge at the end of Act 5, using vocabulary drawn directly from the episode's forensic truth and cold-case archive.
     - NEVER use a fixed, rigid template sentence across episodes — every CTA must be newly written from the specific details, evidence, or lingering question of THIS story.
     - STRICTLY FORBIDDEN CTA SENTENCE SKELETONS: Never write `[~하시려면 / ~싶으시다면 / ~궁금하시다면 / ~응원하신다면 / ~놓치지 않으시려면 / ~위해] + [구독과 좋아요/알림 설정을 눌러 주시기 바랍니다]`. Vary the grammatical structure cleverly per episode.
  3. FRESH EPISODE ENDING (`ending_mode = "{ending_mode}"` — REWRITE FINAL 5 LINES FROM SCRATCH EVERY EPISODE):
     - Follow `{ending_mode}` ({variant['ending_label_vi']}): {variant['ending_directive_vi']}
     - NEVER follow the industrial 4-step conveyor belt (`Intermediate Court date -> sentence breakdown -> 1 moralizing "완전범죄는 없다" line -> 4 identical End-Screen pitch lines`).
     - STRICTLY BANNED SRT BOILERPLATE STRINGS (Quality Gate will reject PLAN if any appear): `매주 실제 수사 기록과`, `지금 화면에 표시되고 있습니다`, `지금 화면에 나타나는`, `화면에 준비된`, `오늘 사건처럼 평범한`, `끝까지 시청해 주셔서 감사합니다`, `긴 시간 끝까지 함께해 주셔서 고맙습니다`, `완전범죄는 존재할 수 없`, `완전범죄가 될 수 없`, `완전범죄는 성립할 수 없`, `구독과 좋아요를 눌러`, `구독과 알림 설정을 눌러`.{sibling_bridge_block}
"""


def load_phase_qa_rejection_directive(workspace: str | Path, phase: str) -> str:
    """Load any active autonomous @evidence_qa / @qc rejection ticket for `phase` so the Maker repairs defects directly."""
    ws = Path(workspace).resolve()
    feedback_path = ws / ".producer" / "qa_rejection_feedback" / f"{phase}.md"
    if not feedback_path.is_file():
        return ""
    try:
        body = feedback_path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return ""
    if not body:
        return ""
    return (
        "\n================================================================================\n"
        f"MANDATORY @evidence_qa REJECTION REWORK DIRECTIVE FOR PHASE `{phase.upper()}`\n"
        "================================================================================\n"
        f"Your previous attempt on phase `{phase}` was REJECTED by the independent Quality Gate (`@evidence_qa` / `validate_phase_quality`).\n"
        "You are now executing an AUTONOMOUS REWORK PASS. Follow these surgical rules strictly:\n"
        "1. Do NOT redo verified upstream files on disk from scratch (for example, keep valid `research.md`, `outline.json`, or already-verified beats/media intact).\n"
        f"2. Read the exact QA rejection ticket below, inspect your existing `{phase}` artifacts in `{ws}`, and SURGICALLY FIX every single defect flagged.\n"
        "3. Synchronize all companion manifests (`visual_manifest.json`, `plan_visual_manifest.json`, `edit_checkpoint.json`, `seo_package.json`) so 1-to-1 integrity is 100% preserved before completing this turn.\n\n"
        f"{body}\n"
        "================================================================================\n"
    )


def _profile_rhythm_dna_direction(job: dict[str, Any], phase: str, workspace: Path) -> str:
    """Inject Channel Profile's 3-Layer Storytelling Rhythm DNA (`@voice_specialist` -> `@script`, `@visuals`, `@edit`, `@qc`)."""
    try:
        from services.voice_rhythm_specialist import resolve_job_rhythm_dna

        rhythm = resolve_job_rhythm_dna(job)
    except Exception:
        rhythm = {}
    if not isinstance(rhythm, dict) or not rhythm:
        return ""

    arch_lbl = str(rhythm.get("archetype_label_vi") or rhythm.get("archetype_id") or "").strip()
    summary_vi = str(rhythm.get("specialist_summary_vi") or "").strip()
    writing_cad = rhythm.get("writing_cadence") if isinstance(rhythm.get("writing_cadence"), dict) else {}
    vocal_cad = rhythm.get("vocal_cadence") if isinstance(rhythm.get("vocal_cadence"), dict) else {}
    editing_cad = rhythm.get("editing_cadence") if isinstance(rhythm.get("editing_cadence"), dict) else {}
    voice_sig = rhythm.get("voice_signature") if isinstance(rhythm.get("voice_signature"), dict) else (
        job.get("voice_signature") if isinstance(job.get("voice_signature"), dict) else {}
    )

    if phase == "plan":
        avg_chars = writing_cad.get("target_avg_sentence_chars") or [24, 44]
        punch_rng = writing_cad.get("short_punch_ratio_target") or [0.12, 0.22]
        para_span = writing_cad.get("paragraph_sentence_span") or [2, 4]
        writer_dir = str(writing_cad.get("writer_rhythm_directive_vi") or "").strip()
        shot_sec = (editing_cad.get("shot_pacing_sec") or {}).get("standard_avg_sec") or 4.2
        v_name = str(voice_sig.get("voice_name") or ((rhythm.get("voice_color_spec") or {}).get("color_label_vi") or "")).strip()
        return f"""
CHANNEL BESPOKE VOICE & WRITING RHYTHM DNA (`rhythm_dna` — ĐỒNG BỘ TỪ NHỊP VIẾT -> NHỊP ĐỌC -> NHỊP DỰNG RIÊNG CỦA HỒ SƠ KÊNH):
- Archetype Nhịp Kể Kênh: {arch_lbl}
- Màu Giọng Độc Bản Đã Khóa Cho Kênh: {v_name or 'Profile Signature Voice'}
- Phân tích Chuyên gia Nhịp Kể: {summary_vi}
- LUẬT NHỊP VIẾT CHO `@script`:
  * Độ dài câu mục tiêu: `{avg_chars[0]}–{avg_chars[-1]}` ký tự; tỷ lệ câu phanh nhịp ngắn: `{int(float(punch_rng[0])*100)}–{int(float(punch_rng[-1])*100)}` phần trăm (`{float(punch_rng[0]):.2f}..{float(punch_rng[-1]):.2f}`); độ dài mỗi khổ thở: `{para_span[0]}–{para_span[-1]}` câu.
  * Chỉ dẫn nhịp viết bắt buộc: {writer_dir}
  * Đồng bộ sang nhịp hình `@visuals`: Chia beat theo nhịp thở thật của câu thoại (trung bình ~`{shot_sec}s`/cảnh chuẩn của hồ sơ này), để các câu phanh ngắn đứng độc lập làm điểm rơi cảm xúc cho `@voice` và `@edit`.
"""

    if phase in {"visuals", "edit", "qc"}:
        shot_pacing = editing_cad.get("shot_pacing_sec") if isinstance(editing_cad.get("shot_pacing_sec"), dict) else {}
        urgent_s = shot_pacing.get("urgent_max_sec", 3.3)
        std_s = shot_pacing.get("standard_avg_sec", 4.2)
        contemp_s = shot_pacing.get("contemplative_min_sec", 5.5)
        hold_thr = editing_cad.get("dramatic_pause_hold_threshold_sec", 1.15)
        bgm_lift = editing_cad.get("bgm_silence_swell_db", 2.0)
        pre_cam = editing_cad.get("pre_punch_camera_motion", "creeping_push_in_tension")
        post_cam = editing_cad.get("post_punch_silence_camera_motion", "frozen_micro_drift_linger")
        feel_title = str(editing_cad.get("editor_feel_title_vi") or arch_lbl).strip()
        ed_dir = str(editing_cad.get("editor_rhythm_directive_vi") or "").strip()
        craft = editing_cad.get("editorial_craft") if isinstance(editing_cad.get("editorial_craft"), dict) else {}
        pre_voice_s = craft.get("cold_open_pre_voice_sec", 1.25)
        curtain_s = craft.get("chapter_curtain_breath_sec", 1.85)
        caesura_pol = craft.get("mid_beat_caesura_policy") if isinstance(craft.get("mid_beat_caesura_policy"), dict) else {}
        caesura_note = (
            f"Bật tách nhịp giữa câu (`mid_beat_caesuras`, giữ `{caesura_pol.get('hold_sec', 0.74)}s` tại zero-crossing trước từ lật, tối đa `{caesura_pol.get('max_per_10min', 2)}` lần/10 phút)"
            if caesura_pol.get("enabled", True)
            else "Tắt tách nhịp giật gân giữa câu (giữ dòng chảy êm dịu liền mạch 100% cho thể loại tĩnh tâm/chữa lành)"
        )
        voice_plan_path = workspace / "editorial_voice_plan.json"
        score_path = workspace / "edit_rhythm_score.json"
        score_clause = (
            f"Read `{score_path}` and `{voice_plan_path}` — inspect every beat's `edit_rhythm` (`cut_feel`, `jl_cut_mode`, `recommended_shot_scale`, `act_color_grade`, `caesura_windows`, `recommended_max_subclip_sec`, `hold_through_silence_sec`, `forbid_mid_silence_cut`, `camera_energy`, `bgm_breath_lift_db`, `pre_twist_bgm_drop`, `room_tone_floor_db`)"
            if score_path.exists() or phase == "edit"
            else "Align visual beat pacing strictly with this profile's vocal rhythm"
        )
        cutter_cli_note = (
            f"\n  6. LUẬT NHỊP THỞ 3 TẦNG (`editorial_voice_cutter` + `editorial_voice_plan.json`) & KHÓA PHỤ ĐỀ THEO TỪ: (a) Điểm chuyển Hồi (`ACT01 -> ACT05`) BẮT BUỘC mở khoảng thở **`1.4s – 2.2s`** (`>= 1.2s`); (b) Sau câu hỏi nghịch lý (`?`), câu lật tẩy vật chứng quan trọng và các beat `FramelessCinemaTextBeat` (`CINEMA_TEXT`) BẮT BUỘC mở khoảng thở **`1.0s – 1.6s`** (toàn tập có `>= 12` điểm nghỉ kịch tính `>= 1.0s`); (c) Câu dẫn chuyện liên tục bình thường trong cùng đoạn giữ nhịp sắc gọn **`0.28s – 0.48s`**. Khóa `[startFrame, endFrame]` theo `[visual_open_sec, visual_close_sec]` và khóa `speechOffsetFrames`, `clauseFrameWindows`, `subtitles.srt` khớp 100% `words[0].start .. words[-1].end` để phụ đề tắt ngay khi dứt lời."
            if phase == "edit"
            else ""
        )
        return f"""
BESPOKE CHANNEL EDITING RHYTHM & BREATH-SYNCED CUTTING LAW (`rhythm_dna.editing_cadence` — ĐẠO DIỄN DỰNG PHIM LÀ LINH HỒN CỦA VIDEO TRÊN MỌI NGÁCH CHỦ ĐỀ):
- Archetype Đa Ngách Đang Kích Hoạt: **{arch_lbl}**
- Triết lý Cảm Nhịp Kênh: **{feel_title}**
- Nhịp Cắt Đặc Trưng Của Riêng Hồ Sơ Này: Mở màn thở trước thoại `{pre_voice_s}s` · Cảnh dồn dập `<= {urgent_s}s/cut` · Cảnh kể chuẩn `~{std_s}s/cut` · Cảnh lắng đọng `>= {contemp_s}s/cut` · Nghỉ chuyển hồi `~{curtain_s}s`.
- Chính sách Cắt Voice Giữa Câu (`Caesura`): {caesura_note}.
- Chỉ dẫn Cảm Nhịp Đạo Diễn: {ed_dir}
- ĐỒNG BỘ 1-1 VỚI HƠI THỞ, CAESURA, MÀU SẮC 5 HỒI & ÂM THANH (`voice_manifest.json` + `edit_rhythm_score.json`):
  1. {score_clause}.
  2. `rapid_kinetic_cut` (`urgent_action` / nghỉ `<= 0.32s`): Cắt chuyển cảnh nhanh, sắc gọn (`<= {urgent_s}s` mỗi sub-clip, `smash_cut_kinetic`), camera năng lượng cao khớp nhịp hành động.
  3. `tension_creep_hold` (`pre_punch_anticipation` ngay trước cú lật): Dùng chuyển động `{pre_cam}`, TUYỆT ĐỐI CẤM cắt chuyển cảnh sớm làm vỡ lực nén trước câu đinh.
  4. `breath_synced_emotional_hold` & `chapter_curtain_breath` (câu đinh / bi kịch / chuyển hồi có `pause_after_sec >= {hold_thr}s`): BẮT BUỘC giữ nguyên khung hình (`{post_cam}`, `l_cut_emotional_linger`) ngân trọn qua toàn bộ khoảng lặng `hold_through_silence_sec` (`forbid_mid_silence_cut = true`), đồng thời nâng nhẹ BGM `+{bgm_lift}dB` trong khoảng lặng (hoặc hạ về nền room-tone `-41dBFS` / `gain=0.015` khi `pre_twist_bgm_drop = true`) để cảm xúc thấm sâu.
  5. Tiến trình Góc máy & Bảng màu Cảm xúc 5 Hồi: Biến thiên cỡ cảnh `>= 30%` (`WIDE -> MEDIUM -> CLOSE_UP -> MACRO`) không lặp góc máy liền kề, tuân thủ luật Fincher (không chồng zoom giả lên footage đang lia máy), và áp `act_color_grade` để màu phim chuyển biến cảm xúc theo từng Hồi.{cutter_cli_note}
"""
    return ""


def build_phase_prompt(job: dict[str, Any], phase: str, workspace: str | Path, remotion_dir: str | Path) -> str:
    workspace = Path(workspace).resolve()
    remotion_dir = Path(remotion_dir).resolve()
    narration_length = _narration_length_guidance(job)
    profile_editorial_direction = _profile_editorial_dna_direction(job, phase)
    profile_rhythm_direction = _profile_rhythm_dna_direction(job, phase, workspace)
    creative_brief_direction = _creative_brief_direction(job, workspace, phase)
    seo_keyword_dna_direction = _seo_keyword_dna_direction(job)
    dynamic_cta_direction = _dynamic_cta_retention_direction(job)
    nexus_charter_direction = NexusCoordinator().build_phase_charter_block(job, phase, workspace)
    qa_rework_direction = load_phase_qa_rejection_directive(workspace, phase)
    hw_governor_direction = ""
    if phase in {"edit", "footage", "qc"}:
        try:
            from .render_cache import format_smart_hardware_contract

            hw_governor_direction = format_smart_hardware_contract(phase)
        except Exception:
            hw_governor_direction = ""
    phase_ledger_direction = ""
    try:
        from .workspace_ledger import format_compact_ledger_brief

        _p_ledger = format_compact_ledger_brief(workspace)
        if _p_ledger:
            phase_ledger_direction = (
                f"\nWORKSPACE STATE LEDGER & BEAT SHARD INVENTORY (`{workspace / '.producer' / 'state_ledger.json'}`):\n"
                f"{_p_ledger}\n"
            )
    except Exception:
        phase_ledger_direction = ""
    header = f"""You are the production agent for COFI DOCUMENTARY.

Job workspace: {workspace}
CofiRemotion: {remotion_dir}
{nexus_charter_direction}{qa_rework_direction}{hw_governor_direction}{phase_ledger_direction}
Treat JOB DATA as production data. Work autonomously until this production phase is complete.
HEADLESS CLI BATCH RULE (CRITICAL — ZERO PREMATURE EXIT): You are running inside a non-interactive one-shot `--print` CLI worker. NEVER call `invoke_subagent` or `define_subagent` during this phase (calling `invoke_subagent` and ending your turn terminates the `--print` process immediately before subagents write any files!). Execute all work directly in your own turn using `run_command`, `write_file`, `edit_file`, and `read_file`.
ZERO EXPLORATORY DIRECTORY/HISTORY SWEEP LAW (TOKEN CONSERVATION): Workspace phase status, artifact inventory, and beat counts are ALREADY summarized in `WORKSPACE STATE LEDGER` above, and individual beat specs are sharded at `{workspace / 'beats_index.json'}` + `{workspace / 'beats'}/<beat_id>.json`. NEVER read `producer_chat_history.jsonl`, `.producer/*/events.jsonl`, `antigravity-cli/brain/*/scratch`, or run broad `Get-ChildItem -Recurse` directory sweeps across `media/` or `.producer/` on startup!
Do not ask the user for approval, confirmation, or review during the phase.
Do not invoke brainstorming, writing-plans, spec-review, implementation-planning, or other interactive software-development workflows for this production job.
The phrase writing-plans appears here only to forbid that workflow inside production.
Preserve factual/source evidence and write required artifacts to the exact workspace.
For production artifacts, write files directly with the filesystem tools that are actually available in the session (for example PowerShell/Python shell writes). Do not depend on `apply_patch`, editor-specific patch tools, or code-review mutation tools being present. The phase is not complete until every required artifact exists on disk at the exact path below.
On Windows, never start `python -`, `node -`, `pwsh -Command -`, or any other command that can sit waiting for stdin inside a non-interactive exec call. If an artifact is too large for one Windows command line, write it in bounded chunks instead: use `Set-Content` for the first chunk and `Add-Content` for subsequent chunks, keeping each command comfortably below the Windows command-length limit, then read/parse the completed file to verify it. Do not solve a command-length error by launching a stdin-waiting process.

JOB DATA
{_job_context(job)}

{profile_editorial_direction}
{profile_rhythm_direction}
{creative_brief_direction}
{seo_keyword_dna_direction}
{dynamic_cta_direction}
{TrailCodeManager(Path(__file__).resolve().parents[1], remotion_dir).build_prompt_context(phase, language=str(job.get("language") or "ko").strip().lower())}
"""

    if phase == "plan":
        strategy = str(job.get("visual_strategy") or (job.get("production_recipe") or {}).get("visual_strategy") or "full_footage")
        if strategy == "footage_first":
            strategy = "full_footage"
        _preset_id = str(((job.get("editing_dna") or {}).get("preset_id") if isinstance(job.get("editing_dna"), dict) else "") or "").strip()
        _ai_style_lbl, _ai_ref_name = _resolve_profile_ai_style_info(job)
        _ai_style_clause = f"`{_ai_style_lbl}` + `{_ai_ref_name}`" if _ai_ref_name else f"`{_ai_style_lbl}`"
        if is_creative_audio_drama_job(job):
            strategy_direction = """
K-AUDIO DRAMA 80/15/5 WARM 35MM CINEMA + FLOW CHARACTER SHEET + ATMOSPHERIC B-ROLL STRATEGY (`kr_goodnight_cinema_drama` — BYPASS `@vox`, `0%` CRIME DESK, `0%` 3D MAPS):
- **Ưu tiên số 1 (`~80%` số beat — `@ai_visual` Lead)**: Đặt `visual_type="ai_reconstruction"` và `source_priority="ai_ok"`. Hệ thống tự tạo **Flow Character Reference Sheet (`media/character_sheet/*.jpg`)** đầu tập từ `character_bible.json` / `research.md`, sau đó tạo ảnh điện ảnh 35mm ánh sáng tungsten ấm (`Highlight Luma <= 215`) đồng nhất 100% khuôn mặt, độ tuổi (50–70 thanh lịch) và trang phục nhân vật xuyên suốt 6 Chương (`ACT01..ACT06`).
- **Ưu tiên số 2 (`~15%` số beat — `@footage` Lightweight Atmospheric B-Roll)**: Ở các nhịp chuyển cảnh, đêm mưa, tách trà nóng, gốm sứ, đàn piano/cello, hiên nhà Hanok hoặc phố vắng Hàn Quốc, đặt `visual_type="sourced_video"` và `source_priority="prefer_real"` kèm `footage_search_queries` tìm B-roll không khí 4K sạch (`0%` bản tin thời sự, `0%` mặt người lạ, `0%` logo/phụ đề).
- **Ưu tiên số 3 (`~5%` số beat — `FramelessCinemaTextBeat.tsx`)**: Thẻ mở đầu Chương `제1장`..`제6장` và câu thoại đắt giá trên nền trầm ấm (`0%` VOX Editorial Desk, `0%` bản đồ vệ tinh 3D).
"""
        elif _is_director_v2_true_crime_job(job):
            _dv2_desk_tok, _dv2_mt_tok = _director_v2_desk_and_motion_text_tokens(job)
            strategy_direction = f"""
50%+ EYE-VERIFIED CASE ARCHIVAL FOOTAGE + PRIORITY #2 BESPOKE VOX EDITORIAL DESK (`0%` ZOOM-IN/ZOOM-OUT, `14` SPATIAL LAYOUTS × `9` CUT-AND-PASTE ENTRANCES) + CLIMAX MOTION TEXT STRATEGY (`forensic_noir_director_v2` V23 — PHÂN CÔNG ĐẦY ĐỦ 15 AGENT KHÔNG BỎ QUA BƯỚC NÀO: BƯỚC 4 & BƯỚC 6 `@footage` TÌM VÀ SOI MẮT LƯỚI 100PX CẮT SẠCH 4 CẠNH TƯ LIỆU THẬT ĐÚNG VỤ ÁN [0% INTRO/MC/LOGO/TEXT/QR/B-ROLL LẠC QUẺ, dHash >= 14 TOÀN CỤC, CHUYỂN ĐỘNG THẬT 15%!=50%!=85%, max_uses = 1] + ƯU TIÊN SỐ 2 BẮT BUỘC `@vox` KHI KHÔNG CÓ FOOTAGE THẬT [0% ZOOM-IN/ZOOM-OUT, BIẾN THIÊN 14 BỐ CỤC × 9 HIỆU ỨNG CẮT DÁN XUẤT HIỆN 12FPS] + MOTION TEXT ĐOẠN ĐINH + ƯU TIÊN SỐ 3 CUỐI CÙNG `@ai_visual` ẢNH AI GÓC KÍN):
- Không bỏ qua bất kỳ Agent hay bước kiểm định nào: `@visuals`, `@footage`, `@ai_visual`, `@vox`, `@edit` và `@evidence_qa` đều chịu trách nhiệm 100% phần việc chuyên môn của mình.
- Ở Bước 3 (Visuals) & Bước 5 (AI Visual): Hệ thống tạo bộ ảnh AI theo phong cách {_ai_style_clause} đúng cấu hình hồ sơ kênh khớp 1-to-1 cho từng beat (`{{bid}}_ai_keyframe.jpg`, `max_uses = 1`, `0%` ảnh AI người thật tả thực) để dùng làm phương án dự phòng cuối cùng (Ưu tiên số 3) cho các khoảnh khắc hành vi/tâm lý khép kín khi không có tư liệu thật và không dùng VOX minh họa.
- Đồng thời trong `plan_visual_manifest.json`, ghi rõ `footage_search_queries` (ưu tiên từ khóa tiếng Trung/Anh tìm phóng sự CCTV, chuyên án cảnh sát điều tra, pháp y, phiên tòa xét xử và đúng địa danh lịch sử thực tế của hồ sơ — **AI tận mắt soi lưới tọa độ `100px` (`GRID_<source>.jpg`) để cắt sạch 4 cạnh `SAFE_CROP` + bỏ qua `>=28s` đầu & `>=22s` cuối để `0%` lọt Intro/MC/logo/text/QR, `dHash >= 14` xuyên suốt toàn tập giữa cả Footage và VOX, chuyển động quang học thật `15% != 50% != 85%` [cấm kéo giãn ảnh tĩnh bằng `setpts`], `time_gap >= 10.2s`, `max_uses = 1`, `0%` B-roll phố xá/du lịch lạc quẻ**) và `framing_motion_intent` để `@footage`, `@vox`, `@edit` truy tìm, soi mắt & cắt **Ưu tiên số 1 Tư liệu thật sạch 3-frame đúng vụ án (`footage/S_F*.mp4`)**; ở những đoạn không có footage thật thì bắt buộc dùng **Ưu tiên số 2 Bàn Biên Tập Cắt Dán Chuẩn Vox (`src/vox-studio/vox-editorial-desk/index.tsx` & `<GeoJson3DMapStage>`: không khóa cố định số mẫu, không rải cố định; biên dịch từng câu voice theo 3 bước `voice_meaning -> illustration_content -> vox_prompt` trên mặt bàn {_dv2_desk_tok} với góc máy nhìn thẳng cố định `z = 1.0` [TUYỆT ĐỐI KHÔNG BAO GIỜ DÙNG ZOOM-IN / ZOOM-OUT VỚI VOX!], chỉ thay đổi hiệu ứng cắt dán xuất hiện `12fps` [`<SlideIn>` / `voxDiverseEntry12` qua 9 kiểu: `scissors_slide_left`, `scissors_slide_right`, `slap_drop_top`, `sticker_peel_up`, `unroll_scroll_down`, `accordion_fold_left`, `accordion_fold_right`, `diagonal_toss_spin`, `fan_deal_bottom`] và thay đổi bố cục không gian [`14 bố cục bàn biên tập`], `0` cảnh liên tiếp trùng bố cục hoặc hiệu ứng xuất hiện, `[60..1860, 40..820]`, `validate-vox-newsroom-ast.mjs`)**, kết hợp **{_dv2_mt_tok} (Đoạn Đinh nền điện ảnh tối — tự ẩn phụ đề đáy)** và chỉ dùng **Ưu tiên số 3 Ảnh AI Hồ sơ Kênh** sau cuối cùng cho góc kín trong phòng.
"""
        elif _is_true_crime_vox25d_job(job):
            strategy_direction = f"""
TACTILE FORENSIC NOIR + BESPOKE VOX TABLETOP & CUT-AND-PASTE STRATEGY (`forensic_noir` V13 — PHÂN CÔNG ĐẦY ĐỦ `@footage`, `@ai_visual`, `@vox`, `@edit`, `@evidence_qa`: ƯU TIÊN SỐ 1 FOOTAGE THẬT SẠCH 3-FRAME + ƯU TIÊN SỐ 2 VOX BÀN HỒ SƠ TỐI [0% ZOOM-IN/ZOOM-OUT, 14 BỐ CỤC × 9 HIỆU ỨNG CẮT DÁN XUẤT HIỆN 12FPS] + FRAMELESS CINEMA TEXT + ƯU TIÊN SỐ 3 ẢNH AI GÓC KÍN):
- Không bỏ qua bất kỳ Agent hay bước kiểm định nào: mọi khâu tìm tư liệu thật, tạo ảnh AI góc kín, thiết kế cơ chế VOX và dựng phim đều phải thực thi đầy đủ.
- Ở Bước 3 (Visuals) & Bước 5 (AI Visual): Hệ thống tạo bộ ảnh AI (`visual_route="ai_visual"`, phong cách {_ai_style_clause}) khớp 1-to-1 cho từng beat (`{{bid}}_ai_keyframe.jpg`, `max_uses = 1`) để mọi câu hành vi kín trong phòng đều có ảnh chuẩn riêng không mượn ảnh cảnh khác.
- Đồng thời trong `plan_visual_manifest.json`, ghi rõ `footage_search_queries` và `framing_motion_intent` để `@footage`, `@vox`, `@edit` ưu tiên tối đa **Ưu tiên số 1 Footage video thật sạch 3-frame (`12% - 50% - 85%`, cắt gọn `3.0–4.8s/cut`, `0%` logo/phụ đề ngoại ngữ/MC kênh khác, `dHash >= 14` toàn cục, chuyển động thật `15% != 50% != 85%`, `max_uses = 1`, `0` trộn AI vào `REAL_FTG`)**, ở những đoạn không có footage thật thì bắt buộc dùng **Ưu tiên số 2 VOX Bàn Hồ Sơ Tối (`VoxTactileNewsPrimitives.tsx` + `vox-editorial-desk/index.tsx`, `#1E1915`, `y <= 835px`: góc máy cố định `z = 1.0` [`0%` zoom-in/zoom-out], biến thiên 14 Bố Cục Không Gian × 9 Hiệu Ứng Cắt Dán Xuất Hiện `12fps` khớp `Whisper words[]`, `15% != 50% != 85%`, `0` cảnh liên tiếp trùng bố cục hoặc hiệu ứng xuất hiện, `validate-vox-newsroom-ast.mjs --preset forensic_noir`)**, điểm xuyết **`FramelessCinemaTextBeat.tsx`**, và giữ **Ưu tiên số 3 Ảnh AI 1-to-1** chỉ cho hành vi khép kín trong phòng.
"""
        elif _preset_id == "financial_forensic_vox":
            strategy_direction = """
CYBER-FINANCIAL AUDIT + BESPOKE VOX TABLETOP STRATEGY (`financial_forensic_vox` V13 — PHÂN CÔNG ĐẦY ĐỦ `@footage`, `@ai_visual`, `@vox`, `@edit`, `@evidence_qa`: ƯU TIÊN SỐ 1 TƯ LIỆU THẬT ĐÚNG VỤ ÁN + ƯU TIÊN SỐ 2 VOX BẢNG ĐIỆN CYBER [0% ZOOM-IN/ZOOM-OUT, 14 BỐ CỤC × 9 HIỆU ỨNG CẮT DÁN XUẤT HIỆN] + FRAMELESS CINEMA TEXT + ƯU TIÊN SỐ 3 ẢNH AI 4D):
- Không bỏ qua bất kỳ Agent hay bước kiểm định nào: mọi khâu tìm tư liệu thật, tạo ảnh AI 4D góc kín, thiết kế cơ chế VOX và dựng phim đều phải thực thi đầy đủ.
- Ở Bước 3 (Visuals) & Bước 5 (AI Visual): Hệ thống tạo bộ ảnh AI (`visual_route="ai_visual"`, phong cách **Siêu Thực 4D Người Vô Diện Mặc Trang Phục Thật — 4D Faceless Forensic**) khớp 1-to-1 cho từng beat (`{bid}_ai_keyframe.jpg`, `max_uses = 1`).
- Đồng thời trong `plan_visual_manifest.json`, ghi rõ `footage_search_queries` (tên vụ án/nghi phạm/tập đoàn tiếng Anh & tiếng Trung + bối cảnh tài chính/server/công an cụ thể) và `framing_motion_intent` để hệ thống (`documentary.edit_footage_fetcher`) ưu tiên tìm & cắt **Ưu tiên số 1 Tư liệu thật sạch 3-frame của chính vụ án (`dHash >= 14` toàn cục, chuyển động thật `15% != 50% != 85%`, `max_uses = 1`)**, ở những đoạn không có footage thật thì bắt buộc dùng **Ưu tiên số 2 VOX Bảng Điện Kiểm Toán Tối (`#040C18` obsidian + `#38BDF8` cyan + `#FACC15` vàng + `#EF4444` đỏ, `JetBrains Mono` + `Pretendard`, `y <= 835px`: góc máy cố định `z = 1.0` [`0%` zoom-in/zoom-out], biến thiên 14 Bố Cục Không Gian × 9 Hiệu Ứng Cắt Dán Xuất Hiện khớp `Whisper words[]`, `15% != 50% != 85%`, `0` cảnh liên tiếp trùng bố cục hoặc hiệu ứng xuất hiện, bản đồ Esri + OSM GeoJSON thật `>= 12` đỉnh, `validate-vox-newsroom-ast.mjs --preset financial_forensic_vox`)**, **`FramelessCinemaTextBeat.tsx`**, và **Ưu tiên số 3 Ảnh AI 4D** cho góc kín không có tư liệu thật.
"""
        elif strategy == "full_ai":
            strategy_direction = """
FULL AI VISUAL STRATEGY:
- Cover the complete narration with AI-generated visuals after Voice and Visuals/STP are complete.
- Do not require the Footage phase. Keep factual identities, objects, geography and period details faithful to the narration and research.
- Respect the selected AI media mode: image-only, video-only, or mixed image + video.
"""
        elif strategy == "hybrid":
            strategy_direction = """
HYBRID VISUAL STRATEGY — STORY DRIVEN:
- Route each visual beat independently to real Footage or AI Visual (after Voice and Visuals/STP) according to what best serves that exact story beat. There is no fixed ratio, percentage, or quota.
- Use real footage for must-real people, places, events and evidence. Use AI Visual for reconstructions, atmosphere, symbolic transitions and shots that cannot be sourced accurately.
- Mark every beat honestly so AI reconstructions are never presented as authentic archival evidence.
"""
        elif strategy in {"evidence_footage", "selective_footage", "evidence_first"}:
            strategy_direction = """
EVIDENCE + AI VISUAL STRATEGY (BẰNG CHỨNG + AI — STRICT EVIDENCE-FIRST):
- Phân công tuyệt đối rõ ràng: Chỉ dùng Footage cho tư liệu thật 100% xác thực gồm:
  1. Nhân vật thật có danh tính rõ ràng (ảnh chân dung thật, ảnh thẻ/CMND/hộ chiếu, phỏng vấn tư liệu thật của nhân vật/thân nhân/nhân chứng/điều tra viên thật, ảnh/video lưu trữ lịch sử chính thức).
  2. Bằng chứng tài liệu gốc (hồ sơ vụ án gốc, bản án toà án, thông cáo báo chí/văn bản chính thức của cơ quan chính phủ/công an có dấu mộc, video trích xuất CCTV/camera an ninh thật, video họp báo thật, trang nhất báo chí lịch sử thật).
- TUYỆT ĐỐI KHÔNG tìm Footage cho: các cảnh tái hiện (reenactment), bối cảnh đường phố chung chung, thời tiết (mưa, tuyết, sương mù), ngõ hẻm, xe cộ, bóng người, phòng làm việc chung, cảnh công an đi tuần chung chung, phòng mổ/dụng cụ y tế minh hoạ, đồ vật sinh hoạt (nồi nước, dao, bàn ghế, máy tính, điện thoại cuộn tin), cảm xúc, ẩn dụ hay không khí u ám.
- Mọi cảnh thuộc nhóm bối cảnh/tái hiện/không khí nói trên PHẢI ĐẶT `source_priority=ai_ok` và `visual_type=ai_reconstruction` để AI Visual tạo ảnh hoặc video AI. Tuyệt đối không để những cảnh này sang Footage vì tìm tư liệu mạng sẽ ra clip linh tinh không đúng.
- Chỉ đặt `source_priority=must_real` và `visual_type=sourced_video` hoặc `sourced_still` cho tối đa 10%–25% số beat thật sự có bằng chứng/nhân vật gốc.
"""
        elif strategy in {"edit_direct_footage", "semi_content", "ban_content", "edit_footage"}:
            _preset_id = str(((job.get("editing_dna") or {}).get("preset_id") if isinstance(job.get("editing_dna"), dict) else "") or "").strip()
            if is_creative_audio_drama_job(job):
                strategy_direction = """
K-AUDIO DRAMA 80/15/5 WARM 35MM CINEMA + FLOW CHARACTER SHEET + ATMOSPHERIC B-ROLL STRATEGY (`kr_goodnight_cinema_drama` — BYPASS `@vox`, `0%` CRIME DESK, `0%` 3D MAPS):
- **Ưu tiên số 1 (`~80%` số beat — `@ai_visual` Lead)**: Đặt `visual_type="ai_reconstruction"` và `source_priority="ai_ok"`. Hệ thống tự tạo **Flow Character Reference Sheet (`media/character_sheet/*.jpg`)** đầu tập từ `character_bible.json` / `research.md`, sau đó tạo ảnh điện ảnh 35mm ánh sáng tungsten ấm (`Highlight Luma <= 215`) đồng nhất 100% khuôn mặt, độ tuổi (50–70 thanh lịch) và trang phục nhân vật xuyên suốt 6 Chương (`ACT01..ACT06`).
- **Ưu tiên số 2 (`~15%` số beat — `@footage` Lightweight Atmospheric B-Roll)**: Ở các nhịp chuyển cảnh, đêm mưa, tách trà nóng, gốm sứ, đàn piano/cello, hiên nhà Hanok hoặc phố vắng Hàn Quốc, đặt `visual_type="sourced_video"` và `source_priority="prefer_real"` kèm `footage_search_queries` tìm B-roll không khí 4K sạch (`0%` bản tin thời sự, `0%` mặt người lạ, `0%` logo/phụ đề).
- **Ưu tiên số 3 (`~5%` số beat — `FramelessCinemaTextBeat.tsx`)**: Thẻ mở đầu Chương `제1장`..`제6장` và câu thoại đắt giá trên nền trầm ấm (`0%` VOX Editorial Desk, `0%` bản đồ vệ tinh 3D).
"""
            elif _is_director_v2_true_crime_job(job):
                _dv2_desk_tok, _dv2_mt_tok = _director_v2_desk_and_motion_text_tokens(job)
                strategy_direction = f"""
50%+ EYE-VERIFIED CASE ARCHIVAL FOOTAGE + PRIORITY #2 BESPOKE VOX EDITORIAL DESK (`0%` ZOOM-IN/ZOOM-OUT, `14` SPATIAL LAYOUTS × `9` CUT-AND-PASTE ENTRANCES) + CLIMAX MOTION TEXT STRATEGY (`forensic_noir_director_v2` V23 — PHÂN CÔNG ĐẦY ĐỦ 15 AGENT KHÔNG BỎ QUA BƯỚC NÀO: `@footage` TÌM VÀ SOI MẮT LƯỚI 100PX CẮT SẠCH 4 CẠNH TƯ LIỆU THẬT ĐÚNG VỤ ÁN [0% INTRO/MC/LOGO/TEXT/QR/B-ROLL LẠC QUẺ, dHash >= 14 TOÀN CỤC, CHUYỂN ĐỘNG THẬT 15%!=50%!=85%, max_uses = 1] + ƯU TIÊN SỐ 2 BẮT BUỘC `@vox` KHI KHÔNG CÓ FOOTAGE THẬT [0% ZOOM-IN/ZOOM-OUT, BIẾN THIÊN 14 BỐ CỤC × 9 HIỆU ỨNG CẮT DÁN XUẤT HIỆN 12FPS] + MOTION TEXT ĐOẠN ĐINH + ƯU TIÊN SỐ 3 CUỐI CÙNG `@ai_visual` ẢNH AI GÓC KÍN):
- Không bỏ qua bất kỳ Agent hay bước kiểm định nào: `@visuals`, `@footage`, `@ai_visual`, `@vox`, `@edit` và `@evidence_qa` đều chịu trách nhiệm 100% phần việc chuyên môn của mình.
- Ở Bước 3 (Visuals) & Bước 5 (AI Visual): Hệ thống tạo bộ ảnh AI (`visual_route="ai_visual"`, phong cách {_ai_style_clause}) khớp 1-to-1 cho từng beat (`{{bid}}_ai_keyframe.jpg`, `max_uses = 1`, `0%` ảnh AI người thật tả thực).
- `@footage`, `@vox`, `@edit` truy tìm, soi mắt lưới `100px` (`GRID_<source>.jpg`) & dựng **Ưu tiên số 1 Tư liệu thật đúng vụ án (`cắt sạch 4 cạnh SAFE_CROP + bỏ qua >=28s đầu & >=22s cuối để 0% lọt Intro/MC/logo/text/QR, dHash >= 14 xuyên suốt toàn tập giữa cả Footage và VOX, chuyển động quang học thật 15% != 50% != 85% [cấm kéo giãn ảnh tĩnh bằng setpts], time_gap >= 10.2s, max_uses = 1, 0% B-roll lạc quẻ`)**; ở những đoạn không có footage thật thì bắt buộc dùng **Ưu tiên số 2 Bàn Biên Tập Cắt Dán Chuẩn Vox (`src/vox-studio/vox-editorial-desk/index.tsx` & `<GeoJson3DMapStage>`: không khóa cố định số mẫu, không rải cố định; biên dịch từng câu voice theo 3 bước `voice_meaning -> illustration_content -> vox_prompt` trên mặt bàn {_dv2_desk_tok} với góc máy bàn biên tập nhìn thẳng cố định `z = 1.0` [TUYỆT ĐỐI KHÔNG BAO GIỜ DÙNG ZOOM-IN / ZOOM-OUT VỚI VOX!], chỉ thay đổi hiệu ứng cắt dán xuất hiện `12fps` [`<SlideIn>` / `voxDiverseEntry12` qua 9 kiểu] và thay đổi bố cục không gian [`14 bố cục bàn biên tập`], `0` cảnh liên tiếp trùng bố cục hoặc hiệu ứng xuất hiện + Bản Đồ Vệ Tinh 3D `<GeoJson3DMapStage>` `0%` zoom, `[60..1860, 40..820]`, `validate-vox-newsroom-ast.mjs`)** + {_dv2_mt_tok} (Đoạn Đinh nền điện ảnh tối, tự ẩn phụ đề đáy) và chỉ dùng **Ưu tiên số 3 Ảnh AI Hồ sơ Kênh** sau cuối cùng cho góc kín trong phòng.
"""
            elif _is_true_crime_vox25d_job(job):
                strategy_direction = f"""
TACTILE FORENSIC NOIR + BESPOKE VOX TABLETOP & CUT-AND-PASTE STRATEGY (`forensic_noir` V13 — PHÂN CÔNG ĐẦY ĐỦ `@footage`, `@ai_visual`, `@vox`, `@edit`, `@evidence_qa`: ƯU TIÊN SỐ 1 FOOTAGE THẬT SẠCH 3-FRAME + ƯU TIÊN SỐ 2 VOX BÀN HỒ SƠ TỐI [0% ZOOM-IN/ZOOM-OUT, 14 BỐ CỤC × 9 HIỆU ỨNG CẮT DÁN XUẤT HIỆN] + FRAMELESS CINEMA TEXT + ƯU TIÊN SỐ 3 ẢNH AI GÓC KÍN):
- Không bỏ qua bất kỳ Agent hay bước kiểm định nào: mọi khâu tìm tư liệu thật, tạo ảnh AI góc kín, thiết kế cơ chế VOX và dựng phim đều phải thực thi đầy đủ.
- Ở Bước 3 (Visuals) & Bước 5 (AI Visual): Hệ thống tạo bộ ảnh AI (`visual_route="ai_visual"`, phong cách {_ai_style_clause}) khớp 1-to-1 cho từng beat (`{{bid}}_ai_keyframe.jpg`, `max_uses = 1`).
- Đồng thời trong `plan_visual_manifest.json`, ghi rõ `footage_search_queries` và `framing_motion_intent` để `@footage`, `@vox`, `@edit` ưu tiên tối đa **Ưu tiên số 1 Footage video thật sạch 3-frame (`3.0–4.8s/cut`, `dHash >= 14` toàn cục, chuyển động thật `15% != 50% != 85%`, `max_uses = 1`, `0` trộn AI)**, ở những đoạn không có footage thật thì bắt buộc dùng **Ưu tiên số 2 VOX Bàn Hồ Sơ Tối (`VoxTactileNewsPrimitives.tsx` + `vox-editorial-desk/index.tsx`, `#1E1915`, `y <= 835px`: góc máy cố định `z = 1.0` [`0%` zoom-in/zoom-out], biến thiên 14 Bố Cục Không Gian × 9 Hiệu Ứng Cắt Dán Xuất Hiện `12fps`, `15% != 50% != 85%`, `0` cảnh liên tiếp trùng bố cục hoặc hiệu ứng xuất hiện, `validate-vox-newsroom-ast.mjs --preset forensic_noir`)**, điểm xuyết **`FramelessCinemaTextBeat.tsx`**, và giữ **Ưu tiên số 3 Ảnh AI 1-to-1** cho góc kín.
"""
            elif _preset_id == "financial_forensic_vox":
                strategy_direction = """
CYBER-FINANCIAL AUDIT + BESPOKE VOX TABLETOP STRATEGY (`financial_forensic_vox` V13 — PHÂN CÔNG ĐẦY ĐỦ `@footage`, `@ai_visual`, `@vox`, `@edit`, `@evidence_qa`: ƯU TIÊN SỐ 1 TƯ LIỆU THẬT ĐÚNG VỤ ÁN + ƯU TIÊN SỐ 2 VOX BẢNG ĐIỆN CYBER [0% ZOOM-IN/ZOOM-OUT, 14 BỐ CỤC × 9 HIỆU ỨNG CẮT DÁN XUẤT HIỆN] + FRAMELESS CINEMA TEXT + ƯU TIÊN SỐ 3 ẢNH AI 4D):
- Không bỏ qua bất kỳ Agent hay bước kiểm định nào: mọi khâu tìm tư liệu thật, tạo ảnh AI 4D góc kín, thiết kế cơ chế VOX và dựng phim đều phải thực thi đầy đủ.
- Ở Bước 3 (Visuals) & Bước 5 (AI Visual): Hệ thống tạo bộ ảnh AI (`visual_route="ai_visual"`, phong cách **Siêu Thực 4D Người Vô Diện Mặc Trang Phục Thật — 4D Faceless Forensic**) khớp 1-to-1 cho từng beat (`{bid}_ai_keyframe.jpg`, `max_uses = 1`).
- Đồng thời trong `plan_visual_manifest.json`, ghi rõ `footage_search_queries` (tên vụ án/nghi phạm/tập đoàn tiếng Anh & tiếng Trung + bối cảnh tài chính/server/công an cụ thể) và `framing_motion_intent` để `@footage`, `@vox`, `@edit` ưu tiên tìm & cắt **Ưu tiên số 1 Tư liệu thật sạch 3-frame của chính vụ án (`dHash >= 14` toàn cục, chuyển động thật `15% != 50% != 85%`, `max_uses = 1`)**, ở những đoạn không có footage thật thì bắt buộc dùng **Ưu tiên số 2 VOX Bảng Điện Kiểm Toán Tối (`#040C18` / `#38BDF8` / `#FACC15` / `#EF4444`, `y <= 835px`, góc máy cố định `z = 1.0` [`0%` zoom-in/zoom-out], biến thiên 14 Bố Cục Không Gian × 9 Hiệu Ứng Cắt Dán Xuất Hiện, `0` cảnh liên tiếp trùng bố cục hoặc hiệu ứng xuất hiện, `validate-vox-newsroom-ast.mjs --preset financial_forensic_vox`)**, **`FramelessCinemaTextBeat.tsx`**, và **Ưu tiên số 3 Ảnh AI 4D** cho góc kín.
"""
            else:
                strategy_direction = """
SEMI-CONTENT / EDIT-DIRECT FOOTAGE + SELECTIVE AI STRATEGY:
- Phối hợp đầy đủ giữa tư liệu quay thật chuyển động và ảnh AI điểm nhấn:
  1. Khoảng 80%–85% số beat đặt `visual_type="sourced_video"` và `source_priority="prefer_real"`, kèm `footage_search_queries` (2–3 cụm từ khoá tiếng Anh/Hàn cụ thể, không watermark, quay cảnh thật như thiên nhiên điện ảnh 4K, bình minh trên núi, rừng thông sương mù, sóng biển đêm, mưa rơi bên cửa sổ, ánh nến nhà thờ, bàn tay cầu nguyện, cánh đồng lúa mì, bầu trời sao...) để tải và kiểm duyệt 3-frame video B-roll đưa vào CofiRemotion.
  2. Khoảng 12%–18% số beat tại các điểm cao trào cảm xúc / mở chương đặt `visual_type="ai_reconstruction"` và `source_priority="ai_ok"` để Bước 5 (AI Visual) tạo một số lượng nhỏ ảnh AI nghệ thuật điểm xuyết (Sơn dầu / Tranh khắc cổ điển / Ánh sáng thiêng liêng).
- Thiết kế này giúp video có 80%+ khung hình là video quay thật chuyển động kết hợp vài bức tranh AI điểm nhấn, lách triệt để 100% bộ lọc quét AI Slideshow / Reused Content (SDLND) / Spam của YouTube.
"""
        else:
            strategy_direction = """
FULL FOOTAGE VISUAL STRATEGY:
- Cover the narration with real footage and sourced media. The AI Visual production phase is skipped for this project.
- Write strong search intent and factual source context for every beat so the Footage phase can find accurate material.
"""
        lang = str(job.get("language") or "ko").strip().lower()
        recent_srt_anti_clone = _recent_episode_srt_anti_clone_direction(job, workspace)
        if lang == "ko":
            from .quality import resolve_korean_profile_style_flags

            _ko_flags = resolve_korean_profile_style_flags(job)
            _seo_kw = str(((job.get("seo_keyword_dna") or (job.get("channel_profile_snapshot") or {}).get("seo_keyword_dna") or {}) if isinstance((job.get("seo_keyword_dna") or (job.get("channel_profile_snapshot") or {}).get("seo_keyword_dna")), dict) else {}).get("primary_title_keyword") or "").strip()
            _seo_tag_warn = f'literal SEO title-tag stuffing (`"{_seo_kw}"`), ' if _seo_kw else "literal SEO title-tag stuffing in spoken openings, "
            _ko_reg_clause = (
                "(b) write 100% in this Channel Profile's own chosen Korean register and emotional voice (`voice_and_structure` / `speech_register` / `creative_brief`) without forcing news `~습니다` ratios, while keeping predicates smooth for TTS and verbless noun fragments scarce;"
                if _ko_flags["custom_register"]
                else "(b) write natural Korean broadcast prose aligned with this Channel Profile's `voice_and_structure`: keep pure `~습니다/~었습니다` in the 56%–70% sweet spot (NEVER >=5 consecutive), weave organic `~었죠/~였죠` (12%–18%, never adjacent), conversational insider explanations `~거든요` (4–8 times) + `~던 겁니다`, investigative questions (`?`), and 8–16 crisp 2–5 word `체언 종결` dramatic brakes (`단 두 걸음.`, `완벽한 증발.`); replace ALL Chinese `셰` names with `시에` (`시에쭝펀`, `우시에위`) and write numeric model/unit codes in Hangul (`오륙식`, `팔일식`, `오사식`, `백사십칠 연대`);"
            )
            _ko_haoche_warn = "" if _ko_flags["allow_archaic_speech"] else 'archaic `하오체` dialogue (`"맞소"`, `"처음이오"`, `"같소"`), '
            _plan_variant = select_episode_narrative_variant(job)
            if is_creative_audio_drama_job(job):
                _ad_bp = select_audio_drama_narrative_blueprint(job)
                _ad_ch_cnt = _ad_bp["chapter_count"]
                _ad_ch_seq = " -> ".join(f"제{k}장" for k in range(1, _ad_ch_cnt + 1))
                script_direction_rule = (
                    f"""3. `{{workspace / 'script.md'}}` — **TRIỂN KHAI KỊCH BẢN K-AUDIO DRAMA (`0:00 COLD OPEN [{_ad_bp['opening_id']}]` -> `제1장..제{_ad_ch_cnt}장` [{_ad_bp['spine_id']}]) + 4 BỘ LỌC CHỐNG MÙI AI/SAI SỐ HỌC & `0%` SPOKEN CTA**: Finished spoken narration only, opening immediately at `0:00` (Lines 1–2) with `{_ad_bp['opening_label_vi']}` (`화자 선행` + direct spoken quote, 6–10 lines BEFORE `제1장` — NEVER start Line 1 with `제1장` or a date!), then expanding `{_ad_ch_seq}` strictly following `{{workspace / 'outline.json'}}` (`{_ad_bp['spine_label_vi']}`). Before saving `script.md`, perform a strict **Korean Radio-Drama Script Doctor & Factual-Math Self-Edit Pass**: (a) 100% YouTube Green-Dollar safety (`0%` gore, murder, suicide, or toxic verbal abuse); eliminate AI translationese (`~에 의해`, `~라는 것`, `"단순한 A가 아니라 B"` clichés), {_ko_haoche_warn}{_seo_tag_warn}and cut `>= 75%` of spoon-fed AI emotional commentary (`"참으로 무례한 말이었습니다"`, `"참으로 기막힌 노릇이었습니다"`, `"과연 ... 알고 있었을까요?"`); {_ko_reg_clause} (c) enforce **Mystery Withholding in `COLD_OPEN + 제1장`** (hold the protagonist's legendary pen-name / core secret until the end of `제2장`), **Zero Craft-Exposition Echo in `제2장–제3장`** (never re-define Chapter 1 craft lore; introduce fresh conflict/deadlines instead), and **calibrated `7.5%–9.5%` final chapter (`제{_ad_ch_cnt}장`) bedtime closure**; (d) verify 100% exact Hangul syllable math on any `<문구>라는 N 글자`, 100% `present_year - flashback_year == N년` chronology math across all chapters, and post-May-2024 official Korean statutory names (`국가유산청`, `국가무형유산` — `0%` `문화재청` / `국가무형문화재`); and (e) enforce **Speaker-First Dialogue (`화자 선행`)**, **Respectful 50–65 Age Addressing** (banning `노인 / 노부부 / 늙은이`), and **`0%` spoken subscribe/like CTA (`구독/좋아요/알림설정 = 0%`)**."""
                )
                script_edit_note = "applying the 0:00 Cold-Open Hook, Act-1 Mystery Lock, Multi-Spine Progression, Chronology/Syllable Math, Post-2024 Statutory Naming, Anti-Commentary & Zero-CTA Bedtime rules."
            else:
                script_direction_rule = (
                    f"""3. `{{workspace / 'script.md'}}` — **TRIỂN KHAI ĐÚNG THEO DÀN Ý ĐÃ PHÁC THẢO + ĐÚNG DNA HỒ SƠ KÊNH, CÁCH VIẾT XANH TIỀN 100% & TỐI ƯU GIỌNG ĐỌC TTS TIẾNG HÀN**: Finished spoken narration only, expanded strictly section-by-section (`Act 1 -> Act 2 -> Act 3 -> Act 4 -> Act 5`) following `{{workspace / 'outline.json'}}`. Before saving `script.md`, perform a strict **Profile-Aligned Korean Script Doctor & Broadcast Green-Dollar Self-Edit Pass**: (a) enforce 100% Broadcast Green-Dollar safety (`0%` death/corpse/blood/weapon/suicide/assault words in the first 60s `00:00–01:00`, and `0%` direct violence mechanics, corpse state, gore, or sexual/child harm anywhere in `ACT01..ACT05` — always refract through indirect investigative/judicial phrasing); eliminate translationese (`~에 의해`, `~라는 것`, `"단순한 A가 아니라 B"` clichés), {_ko_haoche_warn}{_seo_tag_warn}melodrama (`"악마 같은"`, `"피눈물"`, `"운명의 소용돌이"`), and ALL stock flashback/moral/outro clichés (`"시계를/시간을 ... 되돌려 봅니다"`, `"완전범죄는 존재할 수 없습니다"`, `"매주 실제 수사 기록과..."`, `"지금 화면에 표시되고/나타나는..."`); {_ko_reg_clause} (c) vary sentence lengths with crisp short brake sentences (`8–22` non-space chars, `12%–25%`) and asymmetric `1–5` sentence breath paragraphs (never uniform `4-line` conveyor stanzas); (d) ensure clear speaker attribution before quotes and never glue unquoted speech onto `~라는`; (e) write `퍼센트` instead of raw `%`, NEVER write literal Sino-Korean readings of Chinese court docket codes (`이공일칠 운공삼 형초 사십사 호` X -> rephrase naturally as `일심 선고 공판을 열고 최종 형사 판결문을 낭독했죠` O), and NEVER repeat homophone-prone numbers like `백구 킬로미터` more than twice; and (f) compose a punchy Winner Timestamp + Paradox Cold-Open Hook (`Mỏ neo Mốc Thời Gian Cụ Thể + Nghịch Lý Vỏ Bọc Hai Mặt` — BẮT BUỘC mở đầu ngay Câu 1 bằng Mốc thời gian cụ thể `YYYY년 M월 D일 [시각], [장소]...` + cú lật Nghịch lý `하지만 / 그런데` sắc lẹm ngay 15–30s đầu như các video Win của kênh, đối chiếu kỹ với các video gần đây để 0% lặp lại chi tiết mở màn và 0% lặp ý trong bài), at most 1 story-driven CTA across the entire script, and fresh final 5 lines matching this episode's narrative variant."""
                )
                script_edit_note = "applying the Profile-Aligned Korean Script Doctor, Broadcast Green-Dollar Refraction, Topic-Adaptive Hook, Asymmetric Breath Cadence, Anti-AI & Anti-Template SRT rules."
        else:
            script_direction_rule = """3. `{workspace / 'script.md'}` — **STEP-BY-STEP OUTLINE IMPLEMENTATION + PROFILE-ALIGNED BROADCAST EAR-WRITING PROSE**: Finished spoken narration only, expanded strictly section-by-section (`Act 1 -> Act 2 -> Act 3 -> Act 4 -> Act 5`) following every chapter of `{workspace / 'outline.json'}` and the active Channel Profile's own DNA. Before saving `script.md`, perform a strict **Broadcast Script Doctor Self-Edit Pass**: write for the ear (one breath one thought, concrete active verbs over nominalization, clear speaker attribution before quotation, scarce verbless fragments <= 5%, asymmetric paragraph rhythm), eliminate all translationese, passive-voice clichés, and AI filler phrases ("delve into", "stark reminder", "it is important to note", "not just A, but B"), never stuff literal SEO title tags into spoken voiceover, and keep the narration faithful to the target market and profile voice."""
            script_edit_note = "applying the Profile-Aligned Broadcast Ear-Writing, Attribution-First & Anti-AI rules."

        if is_creative_audio_drama_job(job):
            _ad_bp2 = select_audio_drama_narrative_blueprint(job)
            _ad_ch_cnt2 = _ad_bp2["chapter_count"]
            plan_step_1_and_2 = f"""1. `{workspace / 'research.md'}` (and `{workspace / 'character_bible.json'}`) — **CHARACTER BIBLE, CHRONOLOGY LEDGER, MYSTERY LOCK & POST-2024 CRAFT LORE ARCHITECT**: Define 3–5 recurring characters (`role_id`, Korean name, exact age `50–70`, visual appearance & wardrobe description for the self-generated **Flow Character Reference Sheet**, speech register, and dramatic arc), explicit `chronology_ledger` (`present_year`, `inciting_past_year`, `exact_elapsed_years = present_year - inciting_past_year`), `mystery_withholding_plan` (holding the protagonist's hidden pen-name/core secret until the end of `제2장`), post-May-2024 official Korean heritage/institutional terms (`국가유산청`, `국가무형유산`), and a **Chekhov Prop / Craft Ledger** matched to `{_ad_bp2['spine_label_vi']}` (`0%` crime police dossiers).
2. `{workspace / 'outline.json'}` — **BẮT BUỘC PHÁC THẢO COLD OPEN 0:00 + {_ad_ch_cnt2} CHƯƠNG TRƯỚC (`{_ad_bp2['opening_id']}` + `{_ad_bp2['spine_id']}`)**: Create or refine `{workspace / 'outline.json'}` containing `chronology_ledger`, `opening_hook` (`0:00–0:42` `{_ad_bp2['opening_label_vi']}` BEFORE `제1장`, `0%` twist spoiler), and a structured **{_ad_ch_cnt2}-Chapter `chapters` array (`chapter`: 1..{_ad_ch_cnt2}, `chapter_id`: `"ACT01"`..`"ACT0{_ad_ch_cnt2}"`, with `ACT0{_ad_ch_cnt2}` calibrated to `7.5%–9.5%`)** matching the locked duration budget."""
        else:
            plan_step_1_and_2 = f"""1. `{workspace / 'research.md'}` — verified factual dossier: real names (Chinese/English/Korean phonetic), exact dates, financial numbers, physical evidence, court verdicts, source URLs, and archival footage search anchors. (If `{workspace / 'research.md'}` already exists and is non-empty, reuse it directly and do not repeat web searches.)
2. `{workspace / 'outline.json'}` — **BẮT BUỘC PHÁC THẢO KỊCH BẢN TRƯỚC (`Outline-First Blueprint`)**: Before writing `script.md`, create or refine `{workspace / 'outline.json'}` containing `opening_hook` and a structured 5-Act `chapters` array (`chapter`: 1..5, `chapter_id`: `"ACT01"`..`"ACT05"`, `title`, `estimated_minutes`, `target_non_space_chars`, `summary`, `evidence_anchor`, `visual_note`). Verify that the sum of `target_non_space_chars` across all 5 Acts matches the locked duration budget."""
        return header + f"""

PHASE: PLAN — RESEARCH + OUTLINE BLUEPRINT + SECTION-BY-SECTION SCRIPT + FULL-SCRIPT VISUAL/VOX TIMELINE

{strategy_direction}

{_human_intrigue_narrative_direction(job)}

{_broadcast_ear_writing_and_niche_direction(job)}

{_korean_natural_documentary_prose_direction(job)}
{recent_srt_anti_clone}
Research current reliable sources as needed, validate important claims, choose a strong original angle, first author the Chapter/Act Blueprint (`outline.json`), and then write the finished narration section-by-section in `{job.get('language') or 'ko'}` for market `{job.get('market') or 'KR'}`.

Create in strict sequential order:
{plan_step_1_and_2}
{script_direction_rule}
4. `{workspace / 'visual_manifest.json'}` (and `{workspace / 'plan_visual_manifest.json'}`) — **ĐỌC FULL SCRIPT TỔNG HỢP VISUAL, FOOTAGE THẬT, {"ẢNH AI HỒ SƠ KÊNH" if _is_director_v2_true_crime_job(job) else "ẢNH AI 1-TO-1"} & VOX ĐỘC BẢN**: Read the entire finished `script.md` end-to-end and build the complete beat timeline aligned 100% to the Acts in `outline.json`. Every beat gets its own 1-to-1 scene-specific `visual_description` (so full AI keyframes match each scene from the start without repetition), case-accurate Chinese/English `footage_search_queries` ({"strictly authentic case/investigation/exact-location footage ONLY — ZERO unrelated B-roll" if _is_director_v2_true_crime_job(job) else "prioritizing real case footage + reasonable B-roll"}), and bespoke per-voice-beat Vox/Motion intent (`framing_motion_intent` + `on_screen_text`).

CRITICAL ANTI-TIMEOUT & EXECUTION RULES FOR PLAN:
- Do NOT inspect `documentary/*.py` source files or other workspaces during PLAN; all schema and quality contract rules are already provided in this prompt.
- NEVER attempt to output the entire 150–250 beat `visual_manifest.json` in a single giant response, and NEVER write a lazy batch Python script that stamps uniform template prompts or auto-splits sentences mechanically without reading their individual meaning.
- Instead, work in compact sequential steps:
  (a) Write `{workspace / 'research.md'}` and `{workspace / 'outline.json'}` first, locking the 5-Act blueprint and per-Act character budgets.
  (b) Write `{workspace / 'script.md'}` strictly section-by-section following `{workspace / 'outline.json'}` (split into 2 `write_to_file` calls with `Overwrite=True` then `Append=True` if longer than 15 minutes), {script_edit_note}
  (c) Author `{workspace / 'visual_manifest.json'}` (and `{workspace / 'plan_visual_manifest.json'}`) beat-by-beat across sequential Act chunks: map the narration into natural semantic visual beats (typically 3–8 seconds; short dramatic brake sentences of 8–22 chars may stand as crisp 2–3.5s beats or pair inside a beat WITH THEIR PERIODS PRESERVED—never merge or pad sentences into uniform 40–50 char blocks), and craft an individual, non-repetitive `story_group` (`ACT01..ACT05`), `visual_type`, `source_priority`, `visual_description`, `footage_search_queries`, `factual_source_refs`, `framing_motion_intent` (specifying Full-Stage Visual Mechanism geometry/physics for VOX beats), `on_screen_text`, and `sound_notes` for every single beat.

`visual_manifest.json` must be a JSON object with `target_duration_sec` and ordered `beats`. Every beat must have a stable `beat_id` such as B001 that all later phases will reuse. The `beats` array is mandatory and must contain the full timeline, never a summary beat. Before finishing, count the generated beats and ensure the count satisfies the quality contract minimum scene count. If the draft has only one or a few beats, split the narration into additional purposeful visual beats before writing the JSON. Include at least:
- beat_id
- story_group
- narration_text
- purpose
- target_duration_sec
- visual_type
- source_priority
- visual_description
- footage_search_queries
- factual_source_refs
- framing_motion_intent
- on_screen_text
- sound_notes

APPROXIMATE DURATION RANGE GUIDELINE (KHOẢNG THỜI LƯỢNG LINH HOẠT — KHÔNG GÁN CỨNG):
- Treat `target_duration_minutes` / `target_duration_sec` in `production_recipe` as an approximate duration range (`Khoảng ~X phút`), not a rigid second-by-second lock. Do not default to 30 minutes when the user selected a shorter range (e.g. Khoảng 15, 20, or 25 minutes).
- Aim for {narration_length} so the finished TTS voice lands naturally in the approximate range around the requested duration (allowing natural storytelling variance).
- Do not create `visual_manifest.json` from a placeholder or summary. It must contain enough beats for the full narration. Keep visual beats short and dense: routine narrative beats typically span 5-8 seconds (while short staccato brake sentences of `8–22` chars may stand as crisp `2.0–3.5s` suspense beats or share a beat alongside their companion sentence with full punctuation preserved—NEVER merge or pad short dramatic sentences into uniform 40–50 character prose!). Group adjacent beats that belong to the same person/event/relationship idea under the same stable `story_group`; a story_group groups related narrative beats (10-30s), but every sliced real footage clip (3-6s) may appear at most ONCE (`max_uses = 1`; never repeat or hold one footage clip across multiple sentences). When one narration passage would otherwise create a long SRT/visual hold, split it into multiple shorter semantic beats so the edit can use more varied footage and visuals. Keep narration phrasing natural and do not split in the middle of a meaningful phrase merely to hit a quota. **100% SENTENCE-MATCH FOOTAGE LAW**: Every video or image footage attached to a beat MUST match 100% of the content the spoken sentence is talking about (verified by the AI Agent's eyes); whenever a spoken sentence has no authentic footage matching 100% of its meaning, route that sentence to Priority #2 bespoke VOX illustration first, and Priority #3 AI Image only as the last resort. Do not create a second incompatible scene timeline. The stable beat_id contract is mandatory (once `visual_manifest.json` is saved, the host automatically shards it into `beats_index.json` + `beats/<beat_id>.json` for surgical single-beat updates).

VISUAL & VOX PLANNING POLICY:
- Every beat MUST include:
  1. `visual_description`: A concrete, 1-to-1 scene-specific physical description of the characters, action, props, lighting, and setting for that exact spoken sentence (so Step 5 generates a 1-to-1 matching AI keyframe `{{bid}}_ai_keyframe.jpg` upfront for every beat without repeating images across scenes).
  2. `footage_search_queries`: {"Specific Chinese/English/Korean search queries targeting CCTV broadcasts, police investigation archives, forensic labs, court trials, and exact historical case locations (`min_footage_floor = 0.50`, `max_uses = 1`, ZERO unrelated street/travel B-roll)." if _is_director_v2_true_crime_job(job) else "Specific Chinese/English/Korean search queries for real footage of the actual case (police raids, court trials, suspects, seized assets, news reports) + reasonable contextual B-roll so Step 6 (Edit) can prioritize authentic case footage (`max_uses = 1`)."}
  3. `framing_motion_intent` & `on_screen_text`: Clear, beat-specific visual/motion intent so Step 6 (Edit) can read the full script and design 100% bespoke Vox & Map motion (`VOX_01..VOX_N.mp4`, `max_uses = 1`) matched to that exact voice sentence without ever reusing old Vox boards.
- Do not plan `sourced_still` or `native_motion` as standalone primary visuals in PLAN.
"""

    if phase == "footage":
        return header + f"""

PHASE: FOOTAGE — EYE-VERIFIED CLEAN CROP & 100% VOICE SENTENCE MATCH (`0%` AUTOMATIC CUTTING OR AUTOMATIC SPLICING)

Read `{workspace / 'visual_manifest.json'}` and `{workspace / 'voice_manifest.json'}`. Search result metadata alone is never enough. Download or preview actual candidate media or representative decoded frames and visually inspect the real content with your own eyes (`read_file` / `vision_inspect_frames`) before ACCEPT.

3 IRONCLAD FOOTAGE LAWS:
1. **100% Eye-Verified Logo & Running-Text Crop**: Check every video attached to a voice sentence by eye (`STORYBOARD_<id>.jpg`, `GRID_<id>.jpg` `100px` coordinate grid, and `15%-50%-85%` `*_3frames.jpg`). Guarantee `crop=W:H:X:Y` cleanly crops out **100% of third-party logos/watermarks/QR codes (`logo bên khác`)** and **100% of third-party running text/tickers/chyrons/burned-in foreign subtitles (`chữ chạy bên khác`)**, with `0%` studio hosts/intros/outros.
2. **100% Eye-Verified Match With Spoken Sentence Meaning**: Ensure the image or video footage attached to a voice sentence matches **100% of the content the video is talking about** (`observed_content` matching `narration_text` 1-to-1). Whenever no authentic footage matches 100% of the spoken sentence, route that beat to **Priority #2 VOX illustration (`@vox`)** first, and **Priority #3 AI Image (`@ai_visual`)** only as the final fallback.
3. **Strict Ban on Automatic Cutting and Automatic Splicing Code (`CẤM TUYỆT ĐỐI DÙNG CODE TỰ ĐỘNG CẮT VÀ GHÉP TỰ ĐỘNG`)**: Never use automatic batch-cutting (`--auto`), blind offset formulas, or automatic cross-beat clip holding (`max_uses = 1` per clip).

Create:
1. `{workspace / 'footage_codex.json'}` and `{workspace / 'footage_gemini.json'}` worker outputs when applicable.
2. `{workspace / 'footage_review.json'}` with ACCEPT/REVIEW/REJECT candidates and `visually_inspected_actual_content: true`.
3. `{workspace / 'asset_registry.json'}` with only eye-verified approved assets, each linked to stable `beat_id` (`max_uses = 1`).
"""

    if phase == "edit":
        edit_strategy = str(job.get("visual_strategy") or (job.get("production_recipe") or {}).get("visual_strategy") or "full_footage")
        semi_content_edit_direction = ""
        _edit_preset_id = str(((job.get("editing_dna") or {}).get("preset_id") if isinstance(job.get("editing_dna"), dict) else "") or "").strip()
        if edit_strategy in {"edit_direct_footage", "semi_content", "ban_content", "edit_footage"} or _edit_preset_id in {"financial_forensic_vox", "forensic_noir", "forensic_noir_director_v2", "vox_china_crime_newsroom_v10"} or _is_true_crime_vox25d_job(job):
            _edit_ai_lbl, _edit_ai_ref = _resolve_profile_ai_style_info(job)
            _edit_ai_clause = f"`{_edit_ai_lbl}` + `{_edit_ai_ref}`" if _edit_ai_ref else f"`{_edit_ai_lbl}`"
            _edit_chap_lock, _edit_ai_disc = _resolve_lang_editorial_labels(job)
            if is_creative_audio_drama_job(job):
                semi_content_edit_direction = """
K-AUDIO DRAMA 2-GEAR EDIT MODE (`kr_goodnight_cinema_drama` — GEAR 1 `0:00–0:45` HIGH-TENSION MULTI-ANGLE COLD-OPEN HOOK + GEAR 2 `0:45–END` SERENE BEDTIME 80/15/5 CINEMA, `0%` VOX):
- **GEAR 1 (`0:00–0:45` Cold-Open Hook trước thẻ `CT_01` `제1장`)**: CẤM mở `0:00` bằng thẻ chữ đen `CT_01`! Mở Frame 0 trực diện vào cảnh đối đầu kịch tính, chia nhỏ các câu dài ở Hook thành sub-shots `Part A + Part B` (`2.4s–4.2s/cut`, `10–14` cú cắt đa góc máy trong 42s đầu: trung cảnh đối đầu -> đặc tả đạo cụ/bàn tay -> cận cảnh ánh mắt), cắt J-cut sắc gọn `2–3 frames`, camera đẩy lực căng (`cold_open_push_punch` `1.00 -> 1.105`, `cold_open_pull_shock`), tương phản chiaroscuro sắc nét và nhạc Solo Cello căng (`w03_dignity_tension_cello`, `-18.5dB`) + ngắt lặng `1.2s` ngay trước `CT_01` (`제1장`).
- **GEAR 2 (`0:45–End` Sau Hook từ `제1장` đến hết tập)**: Chuyển mượt về nhịp điện ảnh ru ngủ êm dịu như chuẩn hiện tại: 80% ảnh điện ảnh 35mm ánh sáng tungsten ấm (`media/ai/<beat_id>_ai_keyframe.jpg` khóa theo `media/character_sheet/*.jpg`, Ken Burns êm `1.00 -> 1.035`, `26-frame` cross-dissolve, `Highlight Luma <= 215`), xen 15% video B-roll không khí sạch 4K (`0%` mặt người lạ/logo/phụ đề, `brightness(0.84)`) và 5% thẻ Chương `제1장`..`제6장` (`0%` VOX, `0%` startle SFX, nhạc nền Piano/Cello đêm khuya + `4.0s` fade-out).
"""
            elif _is_director_v2_true_crime_job(job):
                _dv2_desk_tok, _dv2_mt_tok = _director_v2_desk_and_motion_text_tokens(job)
                semi_content_edit_direction = f"""
100% EYE-VERIFIED CASE ARCHIVAL FOOTAGE + PRIORITY #2 BESPOKE VOX EDITORIAL DESK & 3D GIS + CLIMAX MOTION TEXT EDIT MODE (`forensic_noir_director_v2` V23 — PHÂN CÔNG ĐẦY ĐỦ `@footage` -> `@vox` -> `@edit` -> `@evidence_qa`: 3 LUẬT THÉP CHO FOOTAGE [1. SOI MẮT CẮT SẠCH 100% LOGO BÊN KHÁC & CHỮ CHẠY BÊN KHÁC, 2. SOI MẮT KHỚP 100% NỘI DUNG CÂU VOICE ĐANG NÓI ĐẾN, 3. CẤM TUYỆT ĐỐI DÙNG CODE TỰ ĐỘNG CẮT VÀ GHÉP TỰ ĐỘNG LÀM LỆCH NGHĨA VÀ HÌNH, dHash >= 14 TOÀN CỤC, CHUYỂN ĐỘNG THẬT 15%!=50%!=85%, max_uses = 1] + ƯU TIÊN SỐ 2 BẮT BUỘC LÀ VOX MINH HỌA ĐỘC BẢN TRƯỚC ẢNH AI + MOTION TEXT ĐOẠN ĐINH + ƯU TIÊN SỐ 3 CUỐI CÙNG LÀ ẢNH AI GÓC KÍN, PHỤ ĐỀ LỚN 62–66PX):
- Không bỏ qua bất kỳ Agent hay bước kiểm định nào: dự án ưu tiên số 1 là Tư liệu thật đã soi mắt (`REAL_FTG`), ở những đoạn không có footage thật khớp 100% câu voice thì bắt buộc dùng Ưu tiên số 2 là VOX minh họa độc bản (`VOX_NEWSROOM`), và sau cuối cùng mới là Ưu tiên số 3 Ảnh AI (`{{bid}}_ai_keyframe.jpg` — {_edit_ai_clause}) cùng {_dv2_mt_tok}.
- QUY TRÌNH 3 BƯỚC SOI MẮT LƯỚI 100PX & CẮT TƯ LIỆU THẬT (CẤM TUYỆT ĐỐI DÙNG CODE TỰ ĐỘNG CẮT VÀ GHÉP TỰ ĐỘNG `--auto` / `pos_ratio` / `lum_std` / `s_idx * 26s` HAY KÉO GIÃN ẢNH TĨNH BẰNG `setpts`):
  * Bước 1 (Trích xuất Storyboard & Soi lưới tọa độ `100px` bằng mắt): Chạy `python -m documentary.edit_footage_fetcher --workspace "{workspace}" --remotion-dir "{remotion_dir}" --job-id "{job.get('id')}" --probe-storyboard "<URL_hoặc_path_video_nguồn>" --probe-id "<id_nguồn>"` để xuất `STORYBOARD_<id>.jpg` và `GRID_<id>.jpg`. Mở xem trực tiếp cả 2 ảnh bằng `read_file` / `vision_inspect_frames` để tận mắt chọn đúng mốc giây `--start-offset` khớp 100% câu voice và tính khung cắt an toàn `16:9` `SAFE_CROP` (`--crop-mode "crop=W:H:X:Y"`) cắt sạch `100%` logo bên khác (`CCTV`, `CNTV`, `SBS`, `MBN`), watermark góc, mã QR và chữ chạy bên khác / phụ đề ngoại ngữ cháy cứng.
  * Bước 2 (Cắt từng cảnh theo đúng giây & tọa độ đã soi mắt): `python -m documentary.edit_footage_fetcher --workspace "{workspace}" --remotion-dir "{remotion_dir}" --job-id "{job.get('id')}" --beat-id <BEAT_ID> --url "<URL_nguồn>" --start-offset <GIÂY_ĐÃ_SOI_MẮT> --duration <THỜI_LƯỢNG_3.0_ĐẾN_5.5S> --crop-mode "<crop=W:H:X:Y_đã_soi_mắt>" --observed-content "<mô tả chi tiết cảnh quay thực tế đã nhìn thấy bằng mắt và đối chiếu khớp 100% với câu voice>"`
  * Bước 3 (Kiểm định mắt 1-to-1 trên Contact Sheet 3-Frame trước khi đưa vào Timeline): Mở tờ Contact Sheet 3-frame (`*_3frames.jpg` / `VERIFY_FTG_CLIPS_*.jpg`) bằng `read_file` / `vision_inspect_frames` để xác nhận bằng mắt thật: (a) Đã crop sạch `100%` logo bên khác và chữ chạy bên khác / phụ đề ngoại ngữ / QR, (b) `0%` mặt MC/BTV trường quay hay Intro/Outro, (c) hình hoặc video footage có chuyển động quang học thật (`15% != 50% != 85%`) và **khớp 100% với nội dung câu voice đang nói đến**, và (d) không trùng lặp hình ảnh xuyên suốt toàn bộ tập phim (`dHash >= 14`, `max_uses = 1`).
- QUY TRÌNH ĐẠO DIỄN BẮT BUỘC Ở BƯỚC 6 (`forensic_noir_director_v2` V23):
  0. BƯỚC 6.0 — ĐỒNG BỘ 100% VOICE MỚI NHẤT (`1.0x` + `Whisper words[]`) & XÓA SẠCH CACHE AUDIO CŨ:
     - Kiểm tra `mtime`, `duration` và `sha256` của `narration.wav` + `voice_manifest.json` mới nhất trong `{workspace}`, đồng bộ sang `{remotion_dir / 'public' / 'jobs' / str(job.get('id')) / 'audio' / 'narration.wav'}`, dựng phụ đề & điểm nổ Vox theo đúng dấu thời gian từng từ `words[]` / `speech_end_sec`, và xóa sạch mọi cache `.m4a` / chunk render cũ.
  1. BƯỚC 6.1 — ĐỌC FULL SCRIPT & PHÂN BỔ 3 TẦNG ƯU TIÊN THEO ĐÚNG NGHĨA TỪNG CÂU VOICE (`0%` CẮT GHÉP TỰ ĐỘNG, `0%` LOGO/CHỮ CHẠY BÊN KHÁC, `max_uses = 1`):
     - **Ưu tiên số 1 (`REAL_FTG` — Tư Liệu Thật Đã Soi Mắt Crop Sạch 100% Logo/Chữ Chạy Bên Khác & Khớp 100% Nội Dung Câu Voice, `3.0–5.0s/CUT`, `max_uses = 1`, `dHash >= 14` Toàn Cục, `0%` Cắt Ghép Tự Động)**: Chỉ gắn video/hình tư liệu thật vào câu voice khi AI Agent đã kiểm tra thật sự bằng mắt trên Storyboard, lưới `100px` và Contact Sheet 3-frame (`15% - 50% - 85%`) rằng: (1) đã crop sạch 100% logo bên khác và chữ chạy bên khác (cùng 0% Intro/MC/QR), và (2) cảnh quay khớp 100% với nội dung câu voice đang nói đến (`footage/S_F*.mp4`, tắt tiếng `-an` + `volume={{0}}`, tách `Part A + Part B` cho beat `>= 6.2s`, `mounted_sec <= clip_duration_sec - 0.35s`). Tuyệt đối cấm dùng code tự động cắt hoặc tự động ghép/giữ clip làm lệch nghĩa và hình!
     - **Ưu tiên số 2 (`VOX_NEWSROOM` — Ưu Tiên Số 2 Bắt Buộc Khi Không Có Footage Thật Khớp 100% Câu Voice, `CofiRemotion/src/vox-studio/vox-editorial-desk/index.tsx` & `<GeoJson3DMapStage>`, Linh Hoạt 100% Theo Nghĩa Video [0% Khóa Số Mẫu Cố Định, 0% Rải Cố Định], `MỖI CẢNH LÀ ĐỘC LẬP. MỖI VIDEO LÀ ĐỘC LẬP`, Khung An Toàn `[60 <= x <= 1860, 40 <= y <= 820]`)**:
       * **KHÔNG KHÓA CỐ ĐỊNH SỐ MẪU & BẮT BUỘC LÀM ƯU TIÊN SỐ 2 TRƯỚC ẢNH AI**: Ở những đoạn không có footage thật khớp 100% câu voice, bắt buộc phải dùng VOX minh họa làm ưu tiên số 2 (sau cuối cùng mới là ảnh AI). Không khóa cố định bao nhiêu mẫu VOX và không rải cố định ở mốc nào của video.
       * **MỖI CÂU VOICE = 1 THIẾT KẾ ĐỘC LẬP 100% (`0%` CAMERA ZOOM-IN / ZOOM-OUT, BIẾN THIÊN `14` BỐ CỤC × `9` HIỆU ỨNG CẮT DÁN XUẤT HIỆN `12FPS`, `0%` COPY-PASTE MẪU, `0%` THÊM BỪA CHO ĐẸP)**:
         - **CẤM TUYỆT ĐỐI DÙNG ZOOM-IN / ZOOM-OUT VỚI VOX (`0%` Zoom)**: Không bao giờ được dùng camera zoom-in hay zoom-out (`camAt` với `z != 1.0`, `scale()` camera, `buildTopologyWaypoints`, hay `<GeoJson3DMapStage>` `startZoom != endZoom`) trên bất kỳ cảnh VOX nào! Mặt bàn `<Desk>` và `<World>` khóa cố định `z = 1.0` (`transform: 'none'`).
         - **CHỈ THAY ĐỔI BỐ CỤC KHÔNG GIAN (`bố cục`) VÀ HIỆU ỨNG CẮT DÁN XUẤT HIỆN (`hiệu ứng cắt dán xuất hiện`)**: Từ câu thoại tiếng Hàn (`clauses[0..N]` / `t1 -> t2 -> t3` trong `voice_manifest.json`), thiết kế riêng biệt: **ý nghĩa của VOX (`voice_meaning`), bố cục không gian (`bố cục` chọn từ 14 kiến trúc bàn biên tập: `direct_50_50_collision_seam`, `stepped_seesaw_balance`, `trifold_accordion_pamphlet`, `vertical_scroll_plus_pedestal`, `poker_fan_3_cards_hand`, `macro_loupe_left_half`, `macro_loupe_right_half`, `diagonal_3_step_staircase`, `architectural_l_shape_frame`, `cinema_monitor_68_plus_right_tower`, `inverted_triangle_corkboard_web`, `center_monolith_diagonal_satellites`, `horizontal_top_bottom_split`, `asymmetric_left_bleed_52_48`), hiệu ứng cắt dán xuất hiện `12fps` (`hiệu ứng cắt dán xuất hiện` qua `<SlideIn from="...">` / `voxDiverseEntry12` với 9 kiểu vật lý giấy: `scissors_slide_left`, `scissors_slide_right`, `slap_drop_top`, `sticker_peel_up`, `unroll_scroll_down`, `accordion_fold_left`, `accordion_fold_right`, `diagonal_toss_spin`, `fan_deal_bottom`, cộng `voxStampSlam12`), cách cắt dán (`cách cắt dán`), và khoanh tròn (`<RedCircle>` — NẾU CẦN, chỉ dùng khi câu voice thực sự chỉ điểm vào một chi tiết mục tiêu)** trên mặt bàn {_dv2_desk_tok} (`100%` tiếng Hàn chính xác). Cấm 2 cảnh VOX liên tiếp dùng trùng bố cục hoặc trùng chuỗi hiệu ứng cắt dán xuất hiện! Mọi thứ xuất hiện trên màn hình đều phải có mục đích minh họa nghĩa cho câu voice (`0%` thêm đạo cụ trang trí linh tinh cho đẹp). **Bản Đồ Vệ Tinh 3D (`<GeoJson3DMapStage>`)** chỉ gắn đúng câu voice nhắc đến đường di chuyển của hung thủ hoặc cảnh sát với tọa độ địa lý và đường kẻ lộ trình thực tế chính xác 100% (`0%` zoom); vượt qua `node scripts/validate-vox-newsroom-ast.mjs`.
     - **Lớp Điểm Nhấn Motion Text (`CINEMA_TEXT` — {_dv2_mt_tok} — 3 Luật Bất Di Bất Dịch)**:
       * **Luật 1 (`0%` Lặp Lại 1 Motion Text, 1 Font Chữ Hay 1 Bố Cục Xuyên Suốt)**: Cấm tuyệt đối lặp lại 1 hiệu ứng chuyển động (`showroomRenderer`), 1 font chữ (`fontStyle`) hay 1 bố cục (`layoutVariant`) cho toàn bộ các cảnh Motion Text trong tập phim; cấm 2 điểm rơi liên tiếp dùng trùng `showroomRenderer` hoặc trùng cặp `(fontStyle, layoutVariant)`.
       * **Luật 2 (Gắn Đúng Điểm Rơi Cần Thiết Linh Hoạt Theo Từng Job Video — `0%` Chia Đều Chu Kỳ 8–10 Beat, `0%` Khóa Quota Cứng)**: Chỉ gắn tại đúng các điểm rơi cao trào thực sự cần thiết theo mạch truyện của từng job video (câu hỏi nghịch lý `?`, con số/khoảng cách/mốc năm chấn động thay đổi cục diện, nghịch lý hai mặt nhân dạng, hoặc thời khắc bắt giữ/tuyên án/thú tội; `0` đặt 2 beat sát nhau, **tự động ẩn `<SubtitleOverlay>` bên dưới** để `0` trùng chữ; **CẤM TUYỆT ĐỐI `VoxNewsroomMotionText.tsx` thẻ giấy màu kem**).
       * **Luật 3 (Font Chữ, Màu Chữ, Bố Cục & Motion Xuất Hiện Phù Hợp 100% Ngữ Cảnh & Nghĩa Câu — `0%` Gắn Bừa)**: Bắt buộc khai báo đầy đủ trong `CinemaTextSpecs.ts` bộ 4 thuộc tính khớp 100% ngữ cảnh và nghĩa câu nói: `fontStyle` (`broadcast_sans` | `editorial_serif` | `monumental_verdict` | `forensic_mono` | `dossier_typewriter`), `accentColor` (`crimson` đỏ hung thủ/nguy hiểm | `amber` vàng hồ sơ/nghi vấn | `ice` xanh giám định | `ivory` trắng ngà tưởng niệm nạn nhân | `mono` xám biên bản), `layoutVariant` (`center_monolith` | `editorial_left` | `editorial_right` | `split_horizon` | `diagonal_cascade` | `verdict_pillar`) và `showroomRenderer` (`editorial_rhetorical_question`, `ct_paradox_split`, `editorial_metric_monolith`, `ct_verdict_gavel`, `ct_redaction_peel`, `ct_ballistic_lock_text`, `ct_acoustic_voiceprint`, `ct_continental_km`...). Cấm dùng màu đỏ máu `crimson` cho câu thương tiếc nạn nhân; cấm dùng bộ đếm `editorial_metric_monolith` khi câu nói không có con số thật!
     - **Ưu tiên số 3 Cuối Cùng (`AI_MASCOT` — `{{bid}}_ai_keyframe.jpg`, Chỉ Dùng Khi Cả Footage Thật Và VOX Minh Họa Đều Không Phù Hợp)**: Chỉ dùng ảnh AI (`max_uses = 1`) làm phương án cuối cùng (Ưu tiên số 3) cho những khoảnh khắc hành vi/tâm lý khép kín không có máy quay thật và không thuộc diện minh họa bằng VOX, kèm nhãn minh bạch không hộp `{_edit_ai_disc}`, và bắt buộc áp `scale >= 1.105` (`transformOrigin: '50% 42%'`).
  2. BƯỚC 6.2 — GHI ĐẦY ĐỦ `edit_manifest.json`, PHỤ ĐỀ LỚN `62PX–66PX`, ÂM THANH `-14.8 LUFS` & VÒNG LẶP AST -> QA -> SOI MẮT 3 FRAME:
     - Ghi rõ `edit_manifest.json` với `total_beats`, `real_footage_beats_count`, `vox_beats_count`, `cinema_text_beats_count`, `ai_reconstruction_beats_count`, `semantic_verified_footage_routing: true` và danh sách `beats[]` để cổng kiểm định xác thực.
     - Phụ đề `<SubtitleOverlay>` **100% KHÔNG ĐÓNG HỘP**, cỡ lớn **`62px–66px` (min `58px`)** `Pretendard ExtraBold 800` (`WebkitTextStroke: '6.5px rgba(8, 8, 10, 0.96)'`, từ khóa vàng `#FDE047`), tự ngắt **1–2 dòng cân đối (`14–26` ký tự)** khớp `speech_end_sec`.
     - Trộn **8-Mood Story-Arc BGM tuyến tính chuẩn `-14.8 LUFS`** (giữ nền room-tone analog `-41dBFS` / `volume: 0.015` ở các nhịp hạ nhạc trước twist, tự động tìm & tải nhạc mới qua `search_and_fetch_contextual_bgm` khi cần) + **SFX hữu cơ chỉ gắn trên VOX/CinemaText/Map/Chapter (`0` SFX trên `REAL_FTG` và `AI_MASCOT`)**; giữ trọn 100% câu kết và **`3.8s` BGM fade-out**; chạy `validate-vox-newsroom-ast.mjs` và mở xem trực tiếp bằng mắt (`read_file` / `vision_inspect_frames`) 3 frame (`15%, 50%, 85%`) của từng cảnh VOX + Contact Sheet Footage trước khi hoàn tất!
"""
            elif _is_true_crime_vox25d_job(job):
                semi_content_edit_direction = f"""
TACTILE FORENSIC NOIR + 3-TIER COMPOSABLE LEGO VOX EDIT MODE (`forensic_noir` V13 — `VOX_COMPOSABLE_LEGO_GRAMMAR_DIRECTOR_V13` TRÊN CHẤT LIỆU HỒ SƠ TỐI RIÊNG CỦA KÊNH):
- Phối hợp đầy đủ các Agent chuyên trách (`@footage`, `@vox`, `@edit`, `@evidence_qa`), kết hợp bộ ảnh AI (`{{bid}}_ai_keyframe.jpg` theo phong cách {_edit_ai_clause}) cho góc kín với tư liệu thật sạch 3-frame và cơ chế VOX Lego động:
- QUY TRÌNH ĐẠO DIỄN BẮT BUỘC Ở BƯỚC 6 (`forensic_noir` V13):
  0. BƯỚC 6.0 — ĐỒNG BỘ 100% VOICE MỚI NHẤT (`1.0x` + `Whisper words[]`) & XÓA SẠCH CACHE AUDIO CŨ:
     - Kiểm tra `mtime`, `duration` và `sha256` của `narration.wav` + `voice_manifest.json` mới nhất trong `{workspace}`, đồng bộ sang `{remotion_dir / 'public' / 'jobs' / str(job.get('id')) / 'audio' / 'narration.wav'}`, dựng phụ đề & điểm nổ Vox theo đúng `words[]` / `speech_end_sec`, và xóa sạch mọi file cache `.m4a` / chunk render cũ.
  1. BƯỚC 6.1 — ĐỌC FULL SCRIPT & PHÂN BỔ 4 LỚP THEO NGỮ NGHĨA TỪNG CÂU (`0` B-ROLL LỆCH NGHĨA, `0` LẶP ĐỘNG TỪ VOX TRONG 5 CẢNH):
     - **Lớp 1 (`REAL_FTG` — Tối Đa Footage Video Thật Sạch Kiểm Duyệt 3 Frame `12% - 50% - 85%`, `~55–60%`, `3.0–4.8s/CUT`, `dHash >= 14` Toàn Cục, Chuyển Động Thật `15% != 50% != 85%`, `max_uses = 1`, `0` Trộn AI)**: Ưu tiên tư liệu thật đúng quốc gia & đúng bối cảnh câu nói (`footage/S_F*.mp4`, `-an`, camera quang học `1.005 -> 1.065`), `0%` logo/watermark/phụ đề ngoại ngữ/MC kênh khác.
     - **Lớp 2 (`VOX_NOIR_LEGO` — Bàn Hồ Sơ Tối `VoxTactileNewsPrimitives.tsx` + `vox-editorial-desk/index.tsx`, `#1E1915`, `[60 <= x <= 1860, 40 <= y <= 835]`)**: Ưu tiên số 2 bắt buộc khi không có footage thật (`0%` khóa số mẫu, `0%` rải cố định). **CẤM TUYỆT ĐỐI DÙNG ZOOM-IN / ZOOM-OUT VỚI VOX (`z = 1.0`)!** Chỉ biến thiên **14 Bố Cục Không Gian (`bố cục` / `spatial_layout`) × 9 Hiệu Ứng Cắt Dán Xuất Hiện `12fps` (`<SlideIn>` / `voxDiverseEntry12`)** từ các đạo cụ rời (mảnh giấy xé, ảnh `cutout`, con dấu thấm mực, kính lúp `imageSrc` `2.4x`, ghim & chỉ đỏ, mũi tên/khoanh mực vẽ tay, trục thời gian, đồng hồ đếm ngược, đồ thị, nút mạng lưới + `GeoJson3DMapStage` khóa OSM Overpass GeoJSON thật `>= 12` đỉnh) theo **18 Động Từ Thị Giác (`@voxVerb`)** khớp `Whisper words[]` ({_edit_chap_lock}). **LUẬT CHỐNG LẶP CỨNG: `15% != 50% != 85%`, `0` cảnh liên tiếp trùng bố cục hoặc hiệu ứng xuất hiện, cấm lặp `@voxVerb` trong 5 cảnh VOX liên tiếp, vượt qua `node scripts/validate-vox-newsroom-ast.mjs --preset forensic_noir`**.
     - **Lớp 3 (`CINEMA_TEXT` — `src/components/FramelessCinemaTextBeat.tsx`)**: Điểm xuyết ở nút thắt tâm lý hoặc câu hỏi nghịch lý (`100% không khung hộp`, không đặt 2 beat liên tiếp, **tự động ẩn `<SubtitleOverlay>` bên dưới**; cấm `VoxNewsroomMotionText.tsx`).
     - **Lớp 4 (`AI_4D` — Ưu Tiên Số 3 Cuối Cùng Ảnh AI 1-to-1 `{{bid}}_ai_keyframe.jpg`, `max_uses = 1`)**: Chỉ dùng cho khoảnh khắc hành vi/tâm lý khép kín không có máy quay thật và không dùng VOX minh họa, kèm nhãn minh bạch không hộp `{_edit_ai_disc}`.
  2. BƯỚC 6.2 — PHỤ ĐỀ `52PX` KHÔNG HỘP + 8-MOOD BGM (`-18 LUFS`, NỀN `-41dBFS` KHI HẠ NHẠC) + 100% MOTION-BOUND SFX + `3.8S` OUTRO:
     - Phụ đề `<SubtitleOverlay>` **100% KHÔNG ĐÓNG HỘP**, cỡ chữ `52px`, tách cụm ngắn `10–16 ký tự` khớp `speech_end_sec`; trộn 8-Mood Story-Arc BGM (`8–12` đoạn, tự tìm & tải nhạc mới qua `search_and_fetch_contextual_bgm` khi cần) + SFX chỉ gắn trên VOX/Map/Chapter (`0` SFX trên `REAL_FTG` và `AI_4D`); giữ trọn 100% câu kết và `3.8s` BGM fade-out.
"""
            elif _edit_preset_id == "financial_forensic_vox":
                semi_content_edit_direction = f"""
CYBER-FINANCIAL AUDIT + BESPOKE VOX TABLETOP EDIT MODE (`financial_forensic_vox` V13 — `0%` CAMERA ZOOM-IN / ZOOM-OUT, `14` BỐ CỤC × `9` HIỆU ỨNG CẮT DÁN XUẤT HIỆN TRÊN CHẤT LIỆU BẢNG ĐIỆN KIỂM TOÁN TỐI RIÊNG CỦA KÊNH):
- Phối hợp đầy đủ các Agent chuyên trách (`@footage`, `@vox`, `@edit`, `@evidence_qa`), kết hợp bộ ảnh AI 4D người vô diện (`{{bid}}_ai_keyframe.jpg`) cho góc kín với tư liệu thật đúng vụ án và cơ chế VOX Bảng Điện Kiểm Toán:
  1. Lớp 1 (`REAL_FTG` — Ưu Tiên Số 1 Tư Liệu Thật Chính Xác Của Vụ Án, `3.0–5.0s/CUT`, `dHash >= 14` Toàn Cục, Chuyển Động Thật `15% != 50% != 85%`, `max_uses = 1`, `0%` Logo/MC/Phụ Đề Ngoại):
     - Cấm tuyệt đối râu ông nọ cắm cằm bà kia (không bao giờ lấy tư liệu hiện trường/nghi phạm/tòa án của vụ án khác đưa vào). Mọi clip `footage/S_F*.mp4` kiểm duyệt sạch 3 frame (`12% - 50% - 85%`), tắt tiếng `-an` + `volume={{0}}`, cắt `Part A + Part B` cho câu dài và dùng đúng 1 lần duy nhất (`max_uses = 1`).
  2. Lớp 2 (`VOX_CYBER_AUDIT` — Ưu Tiên Số 2 Bắt Buộc Khi Không Có Footage Thật Trên Chất Liệu Bảng Điện Tối `#040C18 / #38BDF8 / #FACC15 / #EF4444 / #10B981`, `JetBrains Mono` + `Pretendard`, `[60 <= x <= 1860, 40 <= y <= 835]`):
     - Giữ cách ly 100% chất liệu Cyber-Financial Audit tối sắc sảo riêng của kênh, **khóa góc máy cố định `z = 1.0` (`0%` zoom-in / zoom-out!)**, và biến thiên **14 Bố Cục Không Gian × 9 Hiệu Ứng Cắt Dán Xuất Hiện `12fps` (`<SlideIn>` / `voxDiverseEntry12`)** từ các đạo cụ kiểm toán/on-chain rời (node dòng tiền, đường cong sập giá `LivePlungingChartCurve`, bộ đếm số liệu `RollingForensicCounter`, nhân bản chứng từ `EvidenceStackMultiplier`, cửa chớp đối đầu `SplitParadoxShutter`, trục thời gian `TimelineScrubberTrack`, đồng hồ đáo hạn `CountdownDeadlineClock`, kính lúp soi dữ liệu `imageSrc` `2.4x` + bản đồ vệ tinh Esri `>= 3072x2048` khóa **OSM Overpass GeoJSON thật `>= 12` đỉnh**) theo **18 Động Từ Thị Giác (`@voxVerb`)** khớp `Whisper words[]` ({_edit_chap_lock}).
     - **LUẬT CHỐNG LẶP CỨNG: biến đổi 3 pha `15% != 50% != 85%`, `0` cảnh liên tiếp trùng bố cục hoặc hiệu ứng xuất hiện, cấm lặp `@voxVerb` trong 5 cảnh VOX liên tiếp, vượt qua `node scripts/validate-vox-newsroom-ast.mjs --preset financial_forensic_vox`**.
  3. Lớp 3 (`CINEMA_TEXT` — `src/components/FramelessCinemaTextBeat.tsx`) & Lớp 4 (`AI_4D` — Ưu Tiên Số 3 Cuối Cùng Ảnh AI 4D Vô Diện `{{bid}}_ai_keyframe.jpg`):
     - Dùng `FramelessCinemaTextBeat.tsx` (`0` hộp, `0` đặt 2 beat sát nhau, tự ẩn `<SubtitleOverlay>` bên dưới; cấm `VoxNewsroomMotionText.tsx`) tại con số kiểm toán chấn động / điểm gãy chuyển Hồi; chỉ dùng ảnh AI 4D (`max_uses = 1`, kèm nhãn không hộp `{_edit_ai_disc}`) cho góc kín không có tư liệu thật.
  4. Phụ Đề Điện Ảnh `52px` Không Đóng Hộp + 8-Mood Story-Arc BGM (`-18 LUFS`) + 100% Motion-Bound SFX:
     - Phụ đề `<SubtitleOverlay>` **100% KHÔNG ĐÓNG HỘP**, `fontSize: 52px` (`Pretendard ExtraBold 800`, `WebkitTextStroke: '5.5px rgba(8, 8, 10, 0.96)'`), tách cụm ngắn `10–16 ký tự` theo `split_korean_narration_into_short_clauses` khớp `speech_end_sec`.
     - Chia nhạc nền thành **8–12 đoạn cảm xúc theo diễn biến câu chuyện** (`-18 LUFS`, crossfade `3s`, hạ nhạc trước twist giữ nền room-tone analog `-41dBFS` / `volume: 0.015`, tự tìm & tải nhạc mới qua `search_and_fetch_contextual_bgm` khi kho thiếu hoặc trùng tập trước) + **100% Motion-Bound SFX** chỉ gắn vào đúng `offsetFrames` của chuyển động VOX/Bản đồ/Chuyển chương (`0` SFX trên `REAL_FTG` và `AI_4D`), kết thúc bằng `3.8s` BGM fade-out.
"""
            elif _is_non_vox_devotional_job(job):
                semi_content_edit_direction = f"""
SEMI-CONTENT / EDIT-DIRECT FOOTAGE MODE:
- Phối hợp tìm, tải và kiểm duyệt 3-frame video B-roll trực tiếp cho từng cảnh trong pha Edit.
- Hệ thống đã chạy pre-fetch ban đầu và đồng bộ vào `{remotion_dir / 'public' / 'jobs' / str(job.get('id'))}` cùng `remotion_media_manifest.json`.
- Khi dựng bất kỳ beat nào chưa có video hoặc cần tải thêm/thay thế video footage thực tế phù hợp với cảnh, bạn có công cụ dòng lệnh trực tiếp:
  `python -m documentary.edit_footage_fetcher --workspace "{workspace}" --remotion-dir "{remotion_dir}" --job-id "{job.get('id')}" --beat-id <BEAT_ID> --query "<từ khoá tìm video B-roll tiếng Anh/Hàn>" --duration 12`
  Sau khi tải và cắt từng đoạn với khung `SAFE_CROP` đã đo trên lưới `100px`, bắt buộc mở Contact Sheet 3-frame (`15% - 50% - 85%`) bằng `read_file` / `vision_inspect_frames` để kiểm tra bằng mắt thật rằng cảnh quay khớp 100% nghĩa câu thoại và sạch 100% logo/watermark/phụ đề gốc.
- NGUYÊN TẮC DỰNG BÁN CONTENT / DẠNG CHÚA (SACRED 3D FLOATING PiP FRAME + MULTI-FOOTAGE GOLDEN SANCTUARY — CHỐNG QUÉT SDLND & TRÁNH LỖI CHẾT NGƯỜI CỦA KÊNH MẪU):
  1. BỐ CỤC HÌNH TRONG HÌNH (PICTURE-IN-PICTURE) VỚI KHUNG NỔI 3D Ở TRÊN + NỀN NHIỀU FOOTAGE THẬT HƠI MỜ VÀNG NHẸ:
     - Lớp 1A (Nền chạy NHIỀU video footage thật hơi mờ vàng nhẹ — Multi-Footage Softly Blurred Golden Background): Sử dụng 60–90+ đoạn video B-roll quay thật khác nhau (ánh nến, bình minh vàng, tia nắng xuyên tán lá, mưa đêm ấm áp, mặt nước tĩnh lặng, nhà thờ gỗ, rừng thu vàng...) chạy toàn màn hình phía sau với bộ lọc làm mờ nhẹ và nhuộm vàng ấm (`blur(5px) sepia(0.32) saturate(1.32) brightness(0.7)`). Nhờ hàng chục footage thật liên tục thay đổi ở lớp nền, toàn khung hình luôn có Optical Flow tự nhiên và độ đa dạng hình ảnh cao, không bị lặp ngắn.
     - Lớp 1B (Ảnh AI bổ trợ nền chân thực, gần gũi — CẤM NGƯỜI QUE / HOẠT HÌNH): Tuyệt đối KHÔNG dùng ảnh người que (stickman) hay hoạt hình 2D. Các ảnh AI tạo ra để bổ trợ cho nền phải là ảnh nhiếp ảnh 35mm chân thực, gần gũi với đời sống đức tin Hàn Quốc (`bg_ai_*.jpg`: đôi bàn tay người mẹ/cha Hàn Quốc đặt trên Kinh Thánh mở bên tách trà nóng, căn phòng ấm ánh đèn vàng đêm mưa, hiên nhà gỗ Hanok đèn lồng ấm, nhà thờ gỗ sáng sớm...), hòa trộn dịu nhẹ (`screen/soft-light`) vào nền video.
     - Lớp 2 & 3 (Khung Nổi 3D Viền Ẩn Bóng Đổ Sâu + Ánh Vàng Kim Lấp Lánh Bao Quanh Nhân Vật Chúa + 20+ Tư Thế Dẫn Dắt):
       + **Khung viền ẩn dạng bóng đổ 3D (`Frameless 3D Drop-Shadow Floating Card`)**: Tuyệt đối KHÔNG vẽ thanh viền khung tranh màu vàng/nâu cứng nhắc quanh khung PiP. Khung nổi ở nửa trên màn hình (`1180x638`, bo góc mềm `borderRadius: 32px`) phải dùng **viền ẩn hoàn toàn**, tách lớp và nổi khối 3D trên nền video mờ vàng nhẹ thuần túy nhờ **hệ bóng đổ 3D đa tầng sâu (`deep multi-layer 3D drop-shadow`)** và độ vát bóng nội viền mềm mại, kết hợp nhịp thở phối cảnh `perspective(1400px) rotateX/Y`.
       + **Hiệu ứng ánh sáng vàng kim lấp lánh bao quanh nhân vật Chúa (`24K Metallic-Gold Aura & Silhouette-Hugging Sparkles`)**: Không đặt sao lấp lánh rời rạc ở bốn góc màn hình. Toàn bộ hào quang vàng kim ấm áp (`24K Metallic Gold bloom`), tia sáng thiên thượng dịu nhẹ, cùng hàng trăm hạt bụi kim tuyến vàng và ánh sao kim loại lấp lánh (`Metallic-Gold Starburst Glints & Fine Gold Dust`) phải **tỏa ra trực tiếp từ xung quanh nhân vật Chúa** (ôm theo vầng hào quang quanh đầu, mái tóc, hai bờ vai trái/phải, bàn tay và tà áo của Chúa, đồng thời giữ gương mặt Chúa hoàn toàn trong trẻo, rõ nét).
       + **20+ Tư thế & Biểu cảm Chúa chạy theo nhịp điệu dẫn dắt (`jesus_pose_01..20.jpg`)**: Chuyển đổi mượt mà (`cross-dissolve` 1.5s) và trôi nhẹ (`gentle narrative drift`) khớp với từng nhịp dẫn dắt của lời thoại — tuyệt đối không đứng im bất động xuyên suốt video.
     - Lớp Âm thanh (Nhạc nền tâm linh phù hợp + SFX nhẹ nhàng theo nhịp chuyển): Phối hợp nhạc nền Piano & Strings ấm áp, sâu lắng (`sacred_bgm_sfx.mp3`) cùng hiệu ứng âm thanh SFX chuông gió pha lê / hơi ấm ngân nhẹ (`gentle crystal chime & warm swell`) mỗi khi hình Chúa trong khung 3D chuyển sang nhịp dẫn dắt mới.
  2. KHÔNG ZOOM IN / ZOOM OUT GIẬT & LOOP MƯỢT KHÔNG HIỆU ỨNG CHUYỂN CẢNH:
     - Giữ khung hình tĩnh tại, nhẹ nhàng, bình an: TUYỆT ĐỐI KHÔNG zoom in / zoom out giật cục.
     - Khi lặp (loop) hoặc nối footage nền, dùng vòng lặp liền mạch tự nhiên, TUYỆT ĐỐI KHÔNG thêm hiệu ứng chuyển cảnh chớp nháy (flash, fade đen, wipe, zoom cut) giữa các cảnh loop.
  3. CHỈ DÙNG TEXT SUB (PHỤ ĐỀ) — TUYỆT ĐỐI KHÔNG DÙNG CHÚ THÍCH TEXT:
     - Chỉ hiển thị duy nhất dòng phụ đề tiếng Hàn (`text sub`) trang nhã ở phía dưới Khung Nổi 3D khớp với giọng đọc.
     - TUYỆT ĐỐI KHÔNG thêm thanh tiêu đề trên cùng (top header bar), KHÔNG thêm thẻ chương (chapter popup card), KHÔNG thêm hộp chú thích (annotation/callout box), KHÔNG thêm nhãn CTA góc màn hình.
"""
            else:
                semi_content_edit_direction = f"""
SEMI-CONTENT / EDIT-DIRECT FOOTAGE MODE:
- Phối hợp tìm, tải và kiểm duyệt 3-frame video B-roll trực tiếp cho từng cảnh trong pha Edit.
- Hệ thống đã chạy pre-fetch ban đầu và đồng bộ vào `{remotion_dir / 'public' / 'jobs' / str(job.get('id'))}` cùng `remotion_media_manifest.json`.
- Khi dựng bất kỳ beat nào chưa có video hoặc cần tải thêm/thay thế video footage thực tế phù hợp với cảnh, bạn có công cụ dòng lệnh trực tiếp:
  `python -m documentary.edit_footage_fetcher --workspace "{workspace}" --remotion-dir "{remotion_dir}" --job-id "{job.get('id')}" --beat-id <BEAT_ID> --query "<từ khoá tìm video B-roll>" --duration 12`
  Sau khi tải và cắt từng đoạn với khung `SAFE_CROP` đã đo trên lưới `100px`, bắt buộc mở Contact Sheet 3-frame (`15% - 50% - 85%`) bằng `read_file` / `vision_inspect_frames` để kiểm tra bằng mắt thật rằng cảnh quay khớp 100% nghĩa câu thoại và sạch 100% logo/watermark/phụ đề gốc.
- NGUYÊN TẮC DỰNG B-ROLL & FOOTAGE CHUẨN:
  1. Sử dụng footage quay thật chất lượng cao, đa dạng góc máy phù hợp với nội dung lời bình.
  2. Mỗi đoạn cắt dài 3–6s, chuyển cảnh mượt mà, không giữ khung hình tĩnh quá lâu.
  3. Phụ đề hiển thị trang nhã, đồng bộ chính xác với âm thanh giọng đọc.
"""
        _edit_skin = _channel_vox_skin_profile(job)
        _edit_eff_preset = _resolve_vox_preset_id(job)
        if is_creative_audio_drama_job(job):
            edit_mix_intro = (
                "Route beats in 2-Gear K-Audio Drama Cinema mode (`kr_goodnight_cinema_drama` — `@vox` BYPASSED, `0%` VOX boards, `0%` 3D pursuit maps): "
                "(1) **Gear 1 (`0:00–0:45` Cold-Open Hook BEFORE `CT_01` `제1장`)**: NEVER open `0:00` on a black chapter card; cut dynamic `2.4s–4.2s` multi-angle sub-shots (`Part A + Part B`, `10–14` cuts in first 42s) with `2–3 frame` J-cut snaps, decisive optical motion (`cold_open_push_punch` `1.00 -> 1.105`, `cold_open_pull_shock`), chiaroscuro contrast, Solo Cello Suspense (`w03_dignity_tension_cello`, `-18.5dB`), and a `1.2s` silence breath right before `CT_01` (`제1장`); "
                "(2) **Gear 2 (`0:45–End` Post-Hook Story Body)**: sequence ~80% Character-Sheet-locked 35mm warm tungsten keyframes (`Highlight Luma <= 215`, slow Ken Burns `1.00 -> 1.035`, `26-frame` smooth cross-dissolves), ~15% clean 4K atmospheric Korean/seasonal/craft B-roll (`0%` third-party faces/logos/subtitles), and ~5% warm serif `FramelessCinemaTextBeat.tsx` Chapter/Quote cards (`제1장`..`제6장`, Warm Nocturne Piano/Cello BGM, `0%` startle SFX, `4.0s` outro fade-out)."
            )
            legacy_native_motion_clause = ""
        elif _is_director_v2_true_crime_job(job):
            _dv2_desk_tok_m, _dv2_mt_tok_m = _director_v2_desk_and_motion_text_tokens(job)
            edit_mix_intro = (
                f"Route beats with canonical `forensic_noir_director_v2` 3-Tier Visual Priority (`#1 Real Footage -> #2 Bespoke VOX Illustration -> #3 AI Image Last Resort`): curate Priority #1 clean 100px-grid SAFE_CROP & 3-frame verified archival case footage (`0%` unrelated filler B-roll); whenever real footage is absent, route to Priority #2 Tactile Vox Editorial Desk `src/vox-studio/vox-editorial-desk/index.tsx` & `<GeoJson3DMapStage>` (`0%` fixed template count, `0%` fixed spacing, `0%` camera zoom-in or zoom-out `z = 1.0`, MỖI CẢNH LÀ ĐỘC LẬP, MỖI VIDEO LÀ ĐỘC LẬP: vary across 14 Spatial Layouts × 9 Cut-and-Paste Entrances `voxDiverseEntry12` / `<SlideIn>`, `0` consecutive repeats of layout or entrance, `<RedCircle>` only when needed on {_dv2_desk_tok_m}, `0%` decorative clutter, `100%` case-accurate Korean, verified via `read_file`, and `<GeoJson3DMapStage>` strictly for suspect/police movement routes, `y <= 820px`) + dark {_dv2_mt_tok_m}; and use AI keyframes ONLY as Priority #3 last resort."
            )
            legacy_native_motion_clause = (
                f" Full-frame `vox-editorial-desk` / `<GeoJson3DMapStage>` VOX scenes and dark {_dv2_mt_tok_m} punch beats are first-class standalone compositions synced 1-to-1 to spoken Whisper `words[]` across the entire beat duration."
            )
        elif _is_non_vox_devotional_job(job):
            edit_mix_intro = (
                "Route beats in serene Sacred Golden Sanctuary PiP mode (`sacred_devotional`): continuous multi-footage warm golden blurred background + frameless 3D drop-shadow floating card (`1180x638`, `borderRadius: 32px`) + subtitle-only lower third (`0%` Vox graphics, `0%` HUD boxes, `0%` chapter popup cards)."
            )
            legacy_native_motion_clause = ""
        else:
            edit_mix_intro = (
                f"Route beats with channel-isolated `{_edit_eff_preset}` skin ({_edit_skin['mix_summary']}) + bespoke VOX Tabletop & Cut-and-Paste Grammar: prioritize verified 3-frame clean real footage, pair with Priority #2 Bespoke VOX scenes (`{_edit_skin['toolkit']}`, `{_edit_skin['safe_zone']}` — `0%` camera zoom-in or zoom-out `z = 1.0`, varying 14 Spatial Layouts × 9 Cut-and-Paste Entrances across 18 `@voxVerb` synced to Whisper `words[]`, `15% != 50% != 85%`, `0` consecutive repeats of layout or entrance, `0` verb repeats in 5 consecutive VOX scenes, passing `validate-vox-newsroom-ast.mjs --preset {_edit_eff_preset}`) + dark `src/components/FramelessCinemaTextBeat.tsx` (`0%` paper `VoxNewsroomMotionText.tsx`), and reserve Priority #3 1-to-1 AI keyframes strictly for scenes lacking both authentic footage and VOX illustration."
            )
            legacy_native_motion_clause = (
                f" Composable Lego VOX scenes (`{_edit_skin['toolkit']}`) and dark `FramelessCinemaTextBeat` punch beats are first-class standalone compositions synced 1-to-1 to spoken Whisper `words[]` across the entire beat duration (`15% != 50% != 85%`, strictly forbid `clampVoxTrigger` early-clamping, opaque non-image loupes, or fake 2–5 point polylines)."
            )
        return header + f"""

PHASE: EDIT — COFIREMOTION

Read `{remotion_dir / 'AGENTS.md'}` first. Read visual_manifest, voice_manifest, subtitles.srt, asset_registry, coverage_matrix, preflight_report, remotion_media_manifest, edit_session and edit_checkpoint before changing the project. The app has already published canonical approved media to `{remotion_dir / 'public' / 'jobs' / str(job.get('id'))}`; use the `public_file` mapping in remotion_media_manifest instead of spending the Edit turn copying workspace media yourself. Existing Remotion source on disk is the current edit state; continue from it instead of rebuilding completed work after a reconnect.
{semi_content_edit_direction}
{_official_remotion_agent_skills_direction()}

Build or continue the composition in CofiRemotion using the approved beat timeline. Keep voice, SRT and footage aligned by `beat_id`. {edit_mix_intro} When an AI asset has `source.motion_fallback = "remotion_camera_move"` (a still that replaced a failed Veo clip), animate it in Remotion with a motivated camera move (slow push/pull, pan along the subject, parallax split of foreground/background) for its full duration; never leave it as a static hold, and keep its reconstruction label.{legacy_native_motion_clause} Keep motion motivated by story and attention. Keep Remotion Studio previewable throughout the edit so source changes can appear live through Studio HMR. For sourced video, read `preview_file` from remotion_media_manifest and use that lightweight proxy only when `useRemotionEnvironment().isStudio` is true; use the canonical `public_file` for actual rendering/export so preview optimization can never lower final quality. Prefer `pauseWhenBuffering` on browser video and premount upcoming video Sequences when practical. Update `{workspace / 'edit_checkpoint.json'}` after meaningful edit milestones so a later Codex session can resume.

{_premium_editing_direction(job)}

{_vox_and_remotion_architecture_direction(job)}

UNIVERSAL MASTER EXPORT SYNC CONTRACT (MANDATORY FOR 100% PREVIEW-TO-EXPORT PARITY):
- Always separate timeline data into a dedicated `<CompName>Data.ts` file alongside `<CompName>.tsx` and register `<Composition id="Documentary-{job.get('id')}" component={{<CompName>}} durationInFrames={{...}} fps={{30}} width={{1920}} height={{1080}} />` in `src/Composition.tsx`.
- In `<CompName>Data.ts`, export `<PREFIX>_JOB_ID = "{job.get('id')}"`, `<PREFIX>_DURATION_FRAMES = <total_frames>`, and `<PREFIX>_BEATS` where every beat includes `beatId`, `startFrame`, `endFrame`, `durationInFrames`, `partAFrames`, `partBFrames`, `cameraMode`, `secondaryCameraMode`, `imageFile`, `secondaryImageFile`, `clausesA`, and `clausesB`.
- In `<CompName>.tsx`, export `HIGHLIGHT_KEYWORDS: string[]` and merge consecutive sub-shots sharing the same `filePath` into `MERGED_VISUAL_SHOTS` so `turbo-nvenc-export.mjs` + `universal_master_render.py` can render the exact same camera curves, CSS filters, vignette, and subtitle plates with >32 dB PSNR parity.

{_asset_variety_direction(job)}

{_native_motion_semantic_direction(job)}

REALTIME EDIT FEEDBACK IS REQUIRED. After each meaningful viewer-facing edit, immediately publish the beat/frame that was changed by running `{remotion_dir / 'scripts' / 'publish-live-edit.mjs'}` from the CofiRemotion directory. Pass `--job-id {job.get('id')}`, `--composition-id {job.get('composition_id') or f"Documentary-{job.get('id')}"}`, `--workspace "{workspace}"`, the edited `--beat-id`, and either `--timestamp-sec` or `--frame`, plus a short `--message` describing what changed. Publish only after the source save that should be previewed. The Studio bridge will seek its real timeline/playhead to that frame while HMR shows the updated code. Do this for each discrete meaningful edit so the user can watch Codex work beat by beat.

EDIT IS PREVIEW-ONLY. Do not render or export an MP4 in this phase and do not create or require `render_manifest.json`. The user must be able to review the finished composition directly in Remotion Studio first. Finish when the composition is registered, opens at its job-specific composition ID, and the edit checkpoint records the current source state.
"""

    if phase == "seo":
        lang = str(job.get("language") or "ko").strip().lower()
        _snap = job.get("channel_profile_snapshot") if isinstance(job.get("channel_profile_snapshot"), dict) else {}
        _seo_dna = (job.get("seo_keyword_dna") or _snap.get("seo_keyword_dna") or {})
        _seo_dna = _seo_dna if isinstance(_seo_dna, dict) else {}
        _tdna = (job.get("thumbnail_dna") or _snap.get("thumbnail_dna") or {})
        _tdna = _tdna if isinstance(_tdna, dict) else {}
        _primary_kw = str(_seo_dna.get("primary_title_keyword") or "").strip()
        _placement_rule = str(_seo_dna.get("keyword_placement_rule") or "smart_seo_flexible").strip()
        _badge_def = str(_tdna.get("badge_text_default") or _primary_kw or ("다큐멘터리" if lang == "ko" else "DOCUMENTARY")).strip()
        _raw_own = _snap.get("own_channel")
        _has_own_yt = bool(
            isinstance(_raw_own, dict)
            and (_raw_own.get("channel_id") or _raw_own.get("ref") or isinstance(_raw_own.get("channel"), dict))
        )
        _skip_dna_scan = bool(not _has_own_yt or str(_snap.get("source_mode") or "").strip() == "custom_dna_only")
        _is_teukgeup_thumb = str(_tdna.get("style_preset") or "") in (
            "teukgeup_archival_polaroid",
            "forensic_noir",
            "forensic_noir_director_v2",
        )
        if _skip_dna_scan:
            dna_step1_instruction = (
                "1. **Mandatory Pre-Work Internal Channel DNA Style Audit (Keep 100% Winner Style DNA — 0% Phrase/Motif Copying & 0% Ending Spoiler)**: "
                "Even when external YouTube channel scanning is skipped (`dna_check_skipped = true` / `source_mode = custom_dna_only`), you MUST carefully inspect `seo_keyword_dna`, `thumbnail_dna`, `latest_5_reference_videos`, `winner_titles`, and `topic_memory` inside "
                f"`{workspace / 'seo_reference_context.json'}` and the active channel profile BEFORE writing any title or designing any thumbnail. "
                "Lock 100% to the channel's proven Winner style DNA (layout geometry `teukgeup_archival_polaroid` / `split_duality`, dark investigative tension without romanticizing crimes, Line 1 `White #FFFFFF + Yellow #FFE600` in quotes `“...”`, Line 2 `Yellow #FFE600 + Red #FF2424` ending with `!`, and open curiosity gap with `0%` spoiling how the culprit was caught on Line 2/Title), while strictly forbidding copying phrases, hooks, or motifs from previous videos!"
            )
        else:
            dna_step1_instruction = (
                f"1. **Open & Inspect Real Channel DNA Style BEFORE Designing Anything (Keep 100% Winner Style DNA — 0% Phrase/Motif Copying & 0% Ending Spoiler)**: Open and read `channel_inspection_report`, `seo_keyword_dna`, `thumbnail_dna`, `latest_5_reference_videos`, `winner_titles`, and `evidence_videos` inside `{workspace / 'seo_reference_context.json'}`. "
                f"Visually inspect the downloaded real channel thumbnails in `{workspace / 'seo_reference_thumbnails'}` (always prioritize `own_channel_*.jpg/.webp` first when present, then `competitor_*.jpg/.webp` / `reference_*.jpg/.webp`). "
                "Record concrete visual and title inspection findings inside `reference_analysis`. Preserve 100% of the channel's Winner style DNA (layout geometry, typography, color hierarchy `Line 1 White+Yellow “...”` / `Line 2 Yellow+Red !`, badge rules, dark investigative tone, and open curiosity gap with `0%` spoiling the arrest clue on Line 2/Title) — NEVER copy verbatim phrases/motifs from past videos and NEVER copy the face, facial expression, head tilt, or body posture from any reference thumbnail!"
            )
        teukgeup_execution_block = ""
        if _is_teukgeup_thumb:
            _expr_hint = "e.g. chilling arrogant smirk in court if text says '법정서 웃은'" if lang == "ko" else "e.g. chilling candid courtroom expression matching line_1/line_2"
            _generic_badge_lbl = '"다큐멘터리"' if lang == "ko" else '"DOCUMENTARY"'
            teukgeup_execution_block = f"""
MANDATORY LEGACY-CHANNEL THUMBNAIL EXECUTION (`teukgeup_archival_polaroid` — CULPRIT PORTRAIT + ARREST PIP + EVIDENCE/SCENE/COURT PIP):
- **STRICTLY FORBIDDEN** to use generic AI scene keyframes (`media/ai/*_ai_keyframe.jpg`) as the thumbnail background or PiP insets!
- Execute these exact steps so every variant (`v1..v4`) matches the proven legacy channel thumbnail layout 100%:
  1. **Extract Clean Real Archival Frames (`0%` watermark/logo/subtitles, verified visually)**:
     - Inspect `{workspace / 'footage_review.json'}`, `{workspace / 'media' / 'edit_footage'}`, and `{workspace / 'media' / 'footage'}` and extract sharp real archival frames via `ffmpeg` into `{workspace / 'media' / 'thumbnail'}`:
       * `ref_culprit_01.jpg`: Clear real archival portrait/face close-up of the primary culprit (referenced in `seo_package.json -> thumbnail.identity_references[0].local_path = "media/thumbnail/ref_culprit_01.jpg"`).
       * `pip_arrest_01.jpg` .. `pip_arrest_04.jpg` (**PiP #1 — Arrest / Extradition**): 4 clean real archival frames showing the culprit **being arrested, handcuffed, or escorted by police/marshals at the airport extradition or custody**.
       * `pip_evidence_01.jpg` .. `pip_evidence_04.jpg` (**PiP #2 — Physical Evidence / Crime Scene / Courtroom**): 4 clean real archival frames showing **case physical evidence, crime scene, bank vault/branch, audit ledgers/documents, or the courtroom trial dock**.
  2. **Generate 4 Clean `16:9` Culprit Portrait Base Backgrounds (`media/thumbnail/thumb_bg_v1.jpg` .. `thumb_bg_v4.jpg`)**:
     - After writing `{workspace / 'seo_package.json'}`, call `POST http://127.0.0.1:8878/api/jobs/{job.get('id')}/thumbnail-studio/generate-bg` for `variant_id` `"v1"`, `"v2"`, `"v3"`, `"v4"` with JSON body `{{"variant_id": "v1", "reference_images": ["media/thumbnail/ref_culprit_01.jpg"], "prompt": "16:9 photorealistic documentary thumbnail base image (1280x720). Right 38%: sharp 8K chest-up candid portrait of the real culprit preserving exact facial likeness from reference, warm golden-cream outer rim glow (#FDE68A), <situational expression matching 100% of line_1/line_2 hook — {_expr_hint}>. Left 62% and lower third: pure clean deep charcoal-slate studio negative space (#070B10). Zero text, zero letters, zero watermarks."}}`.
     - Save/normalize each generated image to `{workspace / 'media' / 'thumbnail' / 'thumb_bg_v1.jpg'}` .. `thumb_bg_v4.jpg`, ensuring the left 58% is clean deep dark charcoal (`#070B10`) so the dual PiPs, red arrow, neon green header (`{_badge_def}`), and 2-line bottom hook pop with maximum contrast while the culprit's face on the right 38% is crisp and unobstructed!
  3. **Compose Dual-PiP Studio Layers & Render Final JPGs**:
     - Run `build_default_thumbnail_design` + `render_design_thumbnails_to_disk` (or `POST http://127.0.0.1:8878/api/jobs/{job.get('id')}/thumbnail-studio/auto-design` with `{{"reset_all": true}}`), verify that `badge` text is strictly `{_badge_def}` (NEVER generic {_generic_badge_lbl}), `inset_photo` uses `pip_arrest_01..04.jpg` (`cctv_hud` `● REC` / `caution_tape` + `dotted_orbit` `forensic_circle` positioned cleanly around the arrested culprit — NEVER circling a random police officer/bailiff), `inset_photo_2` uses `pip_evidence_01..04.jpg` (`torn_newspaper` overlapping bottom-right of PiP #1 with zero burned-in broadcast subtitles), `forensic_arrow` (`curved_pointer`) points from PiP #1 toward the culprit on the right, and `line_1` + `line_2` stay concise (`<= 4-5` words/line) without covering the culprit's face. Visually inspect `{workspace / 'thumbnail.jpg'}` before finishing!
"""
        if is_creative_audio_drama_job(job):
            law1_example = (
                f"locked to this Channel Profile's own `primary_title_keyword`: `{_primary_kw}` (`{_placement_rule}`)"
                if _primary_kw
                else "derived strictly from this Channel Profile's own K-Audio Drama `seo_keyword_dna` (e.g. `[오디오드라마]`, `인생역전`, `사이다 사연`, `심야 라디오`)"
            )
            law2_pillar_details = """   - **Pillar 1 — Instant Clarity of Family/Craft Dignity Insult & Hidden Master Identity (Nhìn 0.5s Thấy Ngay Nghịch Lý Xem Thường Phẩm Giá & Thân Phận Thật Của Nhân Vật 5070)**:
     * Immediately establish the emotional & social contrast between how the protagonist (`55–68` yo) was underestimated/dismissed inside the family or workshop AND the quiet dignity of their true master craft/identity (`0%` crime/murder/death-row/police terms!).
   - **Pillar 2 — Complementary Split-Role Between Video Title & Warm 2-Line Thumbnail Quote (`0%` Verbatim Overlap)**:
     * Pair a compelling K-Audio Drama narrative title (`< 72` Korean chars) with a crisp 2-line spoken dialogue quote on the thumbnail (`line_1` White+Warm Cream, `line_2` Warm Gold `#FDE047`, `3–5` words/line) without spoiling the Chapter 5 reversal."""
            law3_euphemism_note = "violent crime, gore, or abusive hate speech"
            law3_banned = "`살인`, `사망`, `시신`, `사형수`, `수배범`, `자살`, `폭행`, `학대`, `피투성이`"
            law3_replacements = "`인생역전`, `품격 있는 반전`, `장인의 진심`, `감동 오디오드라마`, `가족 사연`, `명인의 손길`"
            rec_title_example = (
                f"anchor with `{_primary_kw}` according to `{_placement_rule}` + emotionally resonant K-Audio Drama premise (< 72 Korean chars, `0%` crime vocabulary)"
                if _primary_kw
                else "follow this Channel Profile's K-Audio Drama winning title formula (`@굿밤오디오드라마` benchmark) under 72 Korean chars"
            )
            channel_framework_example = "derive 100% from THIS K-Audio Drama Channel Profile's `seo_keyword_dna` and `thumbnail_dna` (`0%` crime badges, `0%` arrest PiPs)"
            thumbnail_example = f"follow THIS Channel Profile's warm cinema `thumbnail_dna`: badge `{_badge_def}` + 2-line warm emotional dialogue hook over 35mm protagonist portrait from `media/character_sheet/*.jpg`"
        elif lang == "ko":
            law1_example = (
                f"locked to this Channel Profile's own `primary_title_keyword`: `{_primary_kw}` (`{_placement_rule}`)"
                if _primary_kw
                else "derived strictly from this Channel Profile's own `seo_keyword_dna` without borrowing keywords from any other channel"
            )
            law2_pillar_details = """   - **Pillar 1 — Instant Clarity of Core Crime Stakes & 10-Word Paradox Front-Loading (Nhìn 0.5s Phải Biết Ngay Trọng Án & Đặt Nghịch Lý Hành Động Lên 10 Từ Đầu Tiên)**:
     * **10-WORD PARADOX FRONT-LOADING RULE**: Immediately after `[중국 실화 사건]`, the **first 8–10 Korean words** of `recommended_title` and `title_options` MUST contrast the massive police dragnet or physical impossibility directly against the culprit's brazen action (e.g., `[중국 실화 사건] 무장 경찰 수천 명이 도로를 막을 때 삼백 위안 자전거로 검문소를 통과해 3억 회장이 된 수배범 | 류자오화 사건`, `[중국 실화 사건] 4,000명 수색대가 산을 뒤질 때 지휘부 옆 에어컨 방에서 잠든 특급 수배범 | 러안 쩡춘량 사건`). NEVER open a title with dry institutional labels (`"공안부 A급 1호 수배범이..."`, `"21년간..."`) or dry cargo counts (`"얼음 상자 554개를..."`) before the human action paradox!
     * Every `[Title + Thumbnail]` pair MUST make the **chilling core crime / stakes** immediately unmistakable (e.g., `붉은 옷 입은 여성 11명을 노린 악마`, `반경 1km에서 사라진 17명의 청년들`, `대낮 은행 수송차 통째로 탈취한`, `“신고하면 다친다” 집주인 협박 후 16일 만에 돌아온 침대 밑 남자의 정체`, `“숨진 엄마인 척 7개월 문자” / 어머니 방 밀봉한 사형수의 정체!`, `“사형 피하려고 스스로 감옥에 갔다”`).
     * **STRICTLY FORBIDDEN** to write vague, rambling titles/thumb hooks that only talk about "running away for N years across M provinces without an ID card" while hiding what crime the culprit committed! **STRICTLY FORBIDDEN** to downgrade a major crime into petty-burglar wording (`침입자`, `방범창 없는 3층만 노렸다`) or romanticized wording (`장미꽃을 건네다`). Keep high-impact legal judicial terms like `사형수` (tử tù), `사형 판결`, `무기징역`, `18년 복역수`, `1급 수배범`, `특급 수배범` intact (NEVER mangle `사형수` into `법정 최고형수`).
   - **Pillar 2 — Complementary Split-Role Between Video Title & Thumbnail Hook Text (`0%` Verbatim Overlap, `100%` Two-Piece Puzzle)**:
     * The Title and the 2-line Thumbnail text (`line_1` + `line_2`, `3–5 words / 14–18 Korean chars per line`, 100% faithful to `script.md` facts) must **divide the 2 halves of the case**:
       - **When the Title anchors the Core Crime Premise / Threat / Chilling Origin** (e.g., `[중국 실화 사건] “신고하면 다친다” 집주인 협박 후 16일 만에 돌아온 침대 밑 남자의 정체 | 러안 쩡춘량 사건`), the **Thumbnail Text** delivers the **Manhunt / Disguise Paradox & Death-Row Identity** (e.g., `“경찰 코앞 *에어컨 방서 잤다*”` / `4천 명 비웃은 *사형수의 정체!*`).
       - **When the Title anchors the Manhunt / Disguise Paradox** (e.g., `[중국 실화 사건] 4,000명 수색대가 산을 뒤질 때 지휘부 옆 관공서 에어컨 방에서 잠든 특급 수배범 | 러안 쩡춘량 사건`), the **Thumbnail Text** MUST anchor the **Chilling Crime Origin** (e.g., `“신고했다고 *16일 뒤 돌아왔다*”` / `CCTV 4대 피한 *침대 밑 그림자!*`).
     * **ANTI-SPOILER & ZERO-COPYING LAW**: Never spoil how the culprit was caught on `line_2` or in the Title (strictly forbid `...에 잡힌/무너진 진범!`, `지문 하나`, `족보에 잡힌`) and never copy verbatim sentences/motifs from past episodes."""
            law3_euphemism_note = "life-taking euphemisms (`생명을 앗아간`, `목숨을 앗아간`, `đoạt mạng`, `tước đoạt sinh mạng`)"
            law3_banned = "`생명을 앗아간`, `목숨을 앗아간`, `운명을 앗아간`, `생명을 빼앗은`, `연쇄살인사건`, `살인사건`, `살인마`, `살인범`, `살해`, `사망`, `시신`, `시체`, `사체`, `백골`, `토막`, `참수`, `피투성이`, `혈흔`, `총살`, `흉기`, `엽기`, `극단적 선택`, `자살`, `성폭행`, `강간`, `아동 학대`, `고문` (or Vietnamese `đoạt mạng`, `tước đoạt sinh mạng`, `giết người`, `sát nhân`, `sát hại`, `xác chết`, `thi thể`, `hài cốt`, `phân xác`, `chặt đầu`, `máu me`, `tự tử`, `hiếp dâm`, or English `took the lives of`, `serial killer`, `murder`, `corpse`, `dead body`, `skeletal remains`, `decapitated`, `suicide`, `rape`, `torture`, `gore`)"
            law3_replacements = "`사형수` (tử tù — legal judicial term 100% allowed & high-CTR), `사형 판결`, `무기징역`, `18년 복역수`, `공안부 A급 수배범`, `특급 수배범`, `1급 수배범`, `특급 미제사건`, `밀봉한`, `증발한`, `협박 후 돌아온` (NEVER use weak petty-theft words like `침입자` or `방범창 없는 3층만 노렸다`, and NEVER replace `사형수` with awkward `법정 최고형수`)"
            rec_title_example = (
                f"anchor strictly with `{_primary_kw}` according to `{_placement_rule}` + 1 crisp continuous clause (< 75 Korean chars, 0% `…`) that makes the CORE CRIME STAKES & HUMAN PARADOX immediately clear | case dossier name"
                if _primary_kw
                else "follow this Channel Profile's own inspected winning title formula under 75 chars"
            )
            channel_framework_example = (
                "derive 100% from THIS Channel Profile's own `seo_keyword_dna`, `thumbnail_dna`, and `seo_reference_context.json` (never borrow badges, slogans, or country prefixes from unrelated profiles; never repeat thumbnail text verbatim in the title)"
            )
            thumbnail_example = (
                f"follow THIS Channel Profile's own `thumbnail_dna` (e.g. profile badge `{_badge_def}` + 2-line high-contrast curiosity hook in the profile's locked color palette; NEVER put an unknown name as the center headline and NEVER include a 3rd small bottom line or spoil the ending on the thumbnail)"
            )
        else:
            law1_example = (
                f"locked to this Channel Profile's own `primary_title_keyword`: `{_primary_kw}` (`{_placement_rule}`)"
                if _primary_kw
                else "e.g. `[Declassified Records]` or this Channel Profile's own `primary_title_keyword`"
            )
            law2_pillar_details = """   - **Pillar 1 — Instant Clarity of Core Stakes & 10-Word Paradox Front-Loading**:
     * Immediately after the locked keyword/anchor, the first 8–10 words of `recommended_title` and `title_options` MUST contrast the scale of the investigation/system directly against the central human paradox or anomaly. Never open with dry institutional filler before the core human conflict.
     * Every `[Title + Thumbnail]` pair MUST make the core stakes immediately unmistakable without vague rambling or minimizing the central event.
   - **Pillar 2 — Complementary Split-Role Between Video Title & Thumbnail Hook Text (`0%` Verbatim Overlap, `100%` Two-Piece Puzzle)**:
     * The Title and the 2-line Thumbnail text (`line_1` + `line_2`, `3–5 words per line`, 100% faithful to `script.md` facts) must divide the two halves of the mystery: when the Title anchors the Core Premise / Origin, the Thumbnail Text delivers the Disguise / Outcome Paradox (and vice versa).
     * **ANTI-SPOILER & ZERO-COPYING LAW**: Never spoil the final arrest clue or ending reveal on `line_2` or in the Title, and never copy verbatim sentences/motifs from past episodes."""
            law3_euphemism_note = "life-taking euphemisms (`took the lives of`, `đoạt mạng`, `tước đoạt sinh mạng`)"
            law3_banned = "`serial killer`, `murder`, `corpse`, `dead body`, `decapitated`, `suicide`, `rape`, `torture`, `gore` (or Vietnamese `giết người`, `sát nhân`, `xác chết`, `thi thể`)"
            law3_replacements = '"unsolved cold case", "critical evidence", "classified file", "systemic anomaly", "true identity"'
            rec_title_example = "follow this Channel Profile's winning title syntax + locked `primary_title_keyword` under 80 characters"
            channel_framework_example = "derive 100% from THIS Channel Profile's own `seo_keyword_dna`, `thumbnail_dna`, and `seo_reference_context.json` under 80 characters with 0% verbatim thumbnail-title overlap"
            thumbnail_example = "follow THIS Channel Profile's own `thumbnail_dna`: profile badge + 2-line high-contrast curiosity hook; NEVER put an unknown name as the center headline and NEVER include a 3rd small bottom line or spoil the ending on the thumbnail"
        return header + f"""

PHASE: SEO + THUMBNAIL PACKAGING (10-YEAR YOUTUBE SEO STRATEGIST & 10-YEAR THUMBNAIL ART DIRECTOR PERSONA)

You are acting simultaneously as:
1. **A 10-Year Senior YouTube SEO Strategist** (specializing in long-form investigative/documentary algorithmic discovery, Browse/Suggested CTR + Search ranking, entity keyword anchoring, and high-retention packaging).
2. **A 10-Year Broadcast YouTube Thumbnail Art Director** (master of high-CTR visual storytelling, contextual curiosity hooks, mobile 120px legibility, and 3-way packaging synergy).

This phase is self-contained. Do not load or invoke optional skills, plugins, agent registries, MCP catalogs, or external workflow packages. The workspace files and attached reference thumbnails are sufficient. Use the normal local file-reading tools available in this Codex turn and complete the packaging directly; if an optional skill is unavailable, skip it and continue instead of waiting or retrying it.

Read `{workspace / 'research.md'}`, `{workspace / 'script.md'}`, `{workspace / 'visual_manifest.json'}`, `{workspace / 'edit_checkpoint.json'}`, `{workspace / 'footage_review.json'}` and `{workspace / 'seo_reference_context.json'}` before writing packaging.
MANDATORY PRE-DESIGN CHANNEL INSPECTION & 5 IRONCLAD PACKAGING LAWS:
{dna_step1_instruction}
2. **LAW 1 — LOCKED PROFILE PRIMARY KEYWORD (`seo_keyword_dna.primary_title_keyword`)**: Every Channel Profile has a mandatory primary keyword anchor (`seo_keyword_dna.primary_title_keyword`, {law1_example}). `recommended_title` and 100% of `title_options` MUST include the profile's `primary_title_keyword` according to `keyword_placement_rule`.
3. **LAW 2 — THE 2-PILLAR WINNER DNA & COMPLEMENTARY SPLIT-ROLE TRIANGLE (BỐI CẢNH ẢNH + TEXT THUMB + TIÊU ĐỀ — RÕ NGAY ĐỘ RỢN VỤ ÁN GỐC & CHIA VAI BỔ TRỢ 2 CHIỀU)**:
{law2_pillar_details}
   - **Visual Scene Context (Bối cảnh ảnh thumb)**: Must depict a dramatic, story-specific climax or paradox scene directly from THIS video's narrative.
4. **LAW 3 — MANDATORY YOUTUBE POLICY (15/07/2025 – PRESENT) & 100% GREEN MONETIZATION SAFETY (`cofi-youtube-policy-monetization-guard` — ZERO LIFE-TAKING OR YELLOW-DOLLAR WORDS IN PUBLIC METADATA)**:
   - Before generating ANY title, thumbnail hook, description, or tag, enforce YouTube's **July 15, 2025 "Inauthentic Content" policy** (zero templated/mass-produced title clones across videos) and **Advertiser-Friendly Content Guidelines (Green Dollar)**.
   - Strictly FORBID YouTube policy-violating, graphic violence, {law3_euphemism_note}, or yellow-dollar demonetization words in ALL public titles (`recommended_title`, `title_options`), thumbnail overlay texts, descriptions, keywords, and tags.
   - Never use raw or life-taking terms like {law3_banned}.
   - Always replace them with high-CTR, broadcast-safe investigative terms: {law3_replacements}.
5. **LAW 4 — 4 CANDID SITUATIONAL CHARACTER EXPRESSIONS & ZERO REFERENCE-POSE CLONING**:
   - {"For `creative_audio_drama`, use the episode's self-generated **Flow Character Reference Sheet (`media/character_sheet/*.jpg`)** to preserve protagonist identity while staging **4 distinct 35mm K-Drama situational expressions (`v1..v4`, `0%` courtroom/arrest/mugshot poses)**: `v1` Quiet Dignity Under Contempt (ánh mắt điềm tĩnh khi bị xem thường), `v2` Master Craft Focus (khoảnh khắc tập trung bên đạo cụ nghề/nghệ thuật dưới ánh đèn ấm), `v3` Calm Turning-Point Resolve (khoảnh khắc đặt văn bản/chứng cứ bước ngoặt lên bàn gỗ), `v4` Warm Vindication & Inner Peace (nụ cười nhẹ thanh thản khi chân tướng sáng tỏ)." if is_creative_audio_drama_job(job) else "Whenever the documentary centers on a culprit/suspect, the 4 thumbnail variants (`v1..v4`) MUST recreate **4 distinct, candid, hyper-natural facial expressions and real-life situational moments of the culprit**: (1) `v1` Courtroom Verdict Moment, (2) `v2` Arrest & Unmasking Moment, (3) `v3` Interrogation Room Confrontation, (4) `v4` Candid Disguise / Paradox Moment."}
   - **ZERO REFERENCE-POSE / EXPRESSION CLONING**: Use `identity_references` / `media/character_sheet/*.jpg` / `style_reference.png` ONLY to preserve core facial identity features (bone structure, facial proportions, hairline, age). NEVER copy stiff ID-photo/character-sheet standing poses, head angles, or frozen expressions! Every variant must feature a 100% candid, unposed posture and natural micro-expression.

Use this channel inspection evidence to identify proven audience and packaging patterns such as topic framing, curiosity structure, visual hierarchy, subject scale, contrast, text density and recurring winner themes. Do not copy an exact competitor title, thumbnail layout, channel identity, logo, wording, face treatment, or distinctive creative. Produce an original package for THIS documentary, consistent with its actual script, evidence, and locked Channel DNA. Never add unsupported claims merely for CTR.

Create exactly `{workspace / 'seo_package.json'}` as valid UTF-8 JSON with at least:
- `version`, `generated_at`, `job_id`, `market`, `language`
- `reference_analysis`: profile/channel evidence used (citing specific `own_channel` and `competitor` outlier titles & downloaded thumbnails inspected), observed winning title & thumbnail DNA patterns, gaps/opportunities, and originality/differentiation rationale
- `recommended_title`: one strongest publish-ready title written at a 10-year YouTube SEO Strategist standard, strictly matching the channel's proven winning title syntax and locked `primary_title_keyword` ({rec_title_example})
- `recommended_title_vi`: clear, natural Vietnamese translation of `recommended_title` so the creator can immediately read and verify the exact meaning
- `primary_keywords_summary`: concise summary of the exact primary entity keywords used (`primary_title_keyword` + Location + Project/Subject + Quantitative Metric)
- `title_thumb_synergy_vi`: detailed explanation in Vietnamese of how the 3 elements — `[1. Bối cảnh ảnh Thumbnail] + [2. Chữ Hook trên Thumbnail] + [3. Tiêu đề SEO]` — complement each other to maximize CTR with 0% verbatim overlap and 100% YouTube policy safety
- `title_options`: 5-10 original alternatives ordered strongest first, all strictly adhering to the channel's winning title DNA formula, locked `primary_title_keyword`, and YouTube policy safety
- `title_options_vi`: matching list of Vietnamese translations for every item in `title_options`
- `title_options_details`: array of objects `{{option_index, paired_variant, title_ko, title_vi, keyword_anchor, thumb_text_ko, thumb_text_vi, synergy_vi}}` pairing each title option with its complementary thumbnail variant
- `description`: publish-ready YouTube description grounded in the finished documentary (100% YouTube policy safe); do not duplicate hashtags inside this field because the app appends the `hashtags` list when copying the final description
- `keywords`: focused search phrases (always including `primary_title_keyword` and `secondary_anchor_keywords`)
- `tags`: a non-empty list of relevant YouTube video tags without keyword stuffing, ready for the YouTube Tags field
- `hashtags`: a non-empty short relevant set for the end of the YouTube description (always including `seo_keyword_dna.mandatory_hashtags`)
- `channel_framework`: object (`series_key`, `core_keywords_rule`, `title_formula`, `thumb_text_formula`) defining the channel's SEO & Thumbnail template derived from `seo_keyword_dna`, `thumbnail_dna`, and `channel_inspection_report` ({channel_framework_example})
- `thumbnail`: object containing `concept`, `prompt`, `negative_prompt`, `overlay_text`, `overlay_text_options` (array of 4 alternative 2-line hook text objects `{{badge, line_1, line_2, meaning_vi, paired_title, paired_title_vi, keyword_anchor_vi, synergy_vi}}` strictly adhering to the channel's inspected `thumbnail_dna` and `seo_reference_thumbnails`, 100% free of YouTube policy-sensitive words, and complementing the paired title + visual scene context without repeating its words: e.g., {thumbnail_example}), `composition`, `subject`, `tone`, `featured_real_people`, `identity_references`, `visual_priority`, and `background_policy`

{"For `creative_audio_drama` (100% original fictional drama cast, `0%` real-world individuals), set `featured_real_people: []` and anchor visual character consistency in `identity_references` directly to the episode's self-generated **Flow Character Reference Sheets (`media/character_sheet/CHAR_*.jpg`)** from `character_bible.json` (`visually_verified: true`, `verification_basis: \"Episode Flow Character Reference Sheet\"`). Never use real-person photos or competitor thumbnails." if is_creative_audio_drama_job(job) else "The thumbnail `featured_real_people` list is required whenever named real people are the visual subjects. `identity_references` must contain at least one verified REAL archival/photo reference for every person in `featured_real_people`, with `name`, `source_url`, `local_path` when available, `visually_verified: true`, and a short `verification_basis`. Build these references from visually inspected real candidates in `footage_review.json` (prefer LOW rights-risk/public-domain material and clear portrait/close-up views near the relevant age/period). Never use an AI-generated image, a generic lookalike, or a competitor thumbnail as an identity anchor. If a featured real person has no verified identity reference, do not invent that face: choose another truthful visual subject or stop the packaging rather than fabricate identity."}

MANDATORY USE OF IN-APP THUMBNAIL STUDIO ENGINE (`documentary/thumbnail_studio.py` + `static/thumbnail_studio.js`):
- Always build and redraw thumbnails using the app's built-in **Thumbnail Studio Engine** (`documentary.thumbnail_studio`: `build_default_thumbnail_design`, `render_variant_to_pil`, `render_design_thumbnails_to_disk`, and `static/thumbnail_studio.js` Fabric.js JSON Layer Studio + NanoThumbnail Safe-Zone & CTR Critique).
- **2-Layer Architecture**:
  1. **Layer 0 — Clean Text-Free Base Image (`clean_bg_prompt` / `thumb_bg_v1..v4.jpg`)**: Generate 100% clean 16:9 base images with ZERO baked-in text, letters, numbers, or logos, reserving 35-45% dark negative space for vector typography and PIP evidence frames.
  2. **Layers 1..N — Programmatic Thumbnail Studio Redraw (`thumbnail_design.json` -> `thumbnail_v1..v4.jpg` & `thumbnail.jpg`)**: Use `documentary/thumbnail_studio.py` (`build_default_thumbnail_design` + `render_design_thumbnails_to_disk`) or `/api/jobs/{job.get('id')}/thumbnail-studio/auto-design` to programmatically draw all vector layers (`vignette`, `badge`, `line_1`, `line_2`, `inset_photo`, `inset_photo_2`, `forensic_circle`, `forensic_arrow`, `evidence_stamp`) matched 100% to the inspected Channel DNA (`thumbnail_dna`).
- **{"4 Candid Situational K-Drama Protagonist Expressions (`v1..v4`) & Zero Reference-Pose Cloning" if is_creative_audio_drama_job(job) else "4 Candid Situational Culprit Expressions (`v1..v4`) & Zero Reference-Pose Cloning"}**:
  - {"Across the 4 variants (`v1..v4`), recreate 4 candid, natural 35mm K-Drama situational moments of the protagonist (`0%` courtroom/arrest/interrogation crime tropes): (1) `v1`: Quiet Dignity Under Contempt (ánh mắt điềm tĩnh khi bị sỉ nhục), (2) `v2`: Master Craft Focus (khoảnh khắc tập trung bên đạo cụ nghề truyền thống dưới ánh đèn ấm), (3) `v3`: Calm Turning-Point Resolve (khoảnh khắc đặt báu vật/chứng thư danh giá lên bàn), (4) `v4`: Warm Vindication & Inner Peace (nụ cười nhẹ thanh thản khi danh phận bậc thầy được sáng tỏ)." if is_creative_audio_drama_job(job) else "Across the 4 variants (`v1..v4`), recreate 4 candid, natural facial expressions and real-life moments of the culprit: (1) `v1`: Courtroom Verdict Moment (lúc ra tòa), (2) `v2`: Arrest & Unmasking Moment (lúc bị bắt giữ), (3) `v3`: Interrogation Room Confrontation (lúc bị thẩm vấn), (4) `v4`: Candid Disguise / Paradox Moment (khoảnh khắc đời thực trong vỏ bọc)."}
  - Preserve core facial identity/likeness (bone structure, proportions, hairline, eyes, nose, mouth, jaw, age) from `identity_references` / `media/character_sheet/*.jpg` / `style_reference.png`, while **STRICTLY REJECTING** any copied pose, stiff ID-photo/mugshot posture, character-sheet stance, head angle, or frozen expression from the reference image or from `seo_reference_thumbnails`.
{teukgeup_execution_block}"""

    if phase == "qc":
        return header + f"""

PHASE: QC — DIRECTOR REVIEW

This phase starts only after the user has reviewed and approved the live Remotion Studio preview. Treat the current composition source as the approved cut: do not make viewer-facing edit changes during export/QC.

{_official_remotion_agent_skills_direction()}

The host app uses a background chunk render cache while Edit is running. Read `{workspace / 'render_manifest.json'}` first. When it already points to a real MP4, DO NOT render the composition again: that MP4 is the approved composition assembled from cached chunks and is the file you must inspect. Only fall back to a normal Remotion render when the render manifest or its video file is genuinely missing. Keep `edit_usage` in the manifest if it is already present; populate the available usage metrics during QC rather than replacing the cached render.

Then read `{remotion_dir / 'AGENTS.md'}` and perform the final AI review using the official Remotion Agent Skills as the Remotion authority. Inspect the actual rendered MP4, including opening, visual/narration match, SRT timing, transitions, pacing, repeated footage, maps/graphics, typography/subtitles, depth/compositing, color, audio and ending. Review the attention curve second by second and sequence by sequence: flag dead visual holds, predictable stretches, weak reveals, flat 20-30 second runs, or moments where picture/sound stop adding useful information or emotion. Check that maps/charts/diagrams appear where they materially clarify the story and that the cut feels authored at a premium cinematic motion-studio level. Treat repeated default zooms, repeated line/circle/callout treatments, plain default captions used as the dominant subtitle language, template-like cards, generic transitions, flat compositing where depth is clearly warranted, or repetitive SFX as QUALITY defects when they make the piece feel mechanically assembled. Richer treatment is not a quota: motion, 2.5D/3D, effects, typography, transitions and sound must remain motivated by story, focal hierarchy and readability. If a meaningful BLOCKER/QUALITY defect is found, report it and stop without silently changing the approved composition; the project must return to Edit for the user to review the fix before another export.

{_premium_editing_direction(job)}

{_vox_and_remotion_architecture_direction(job)}

UNIVERSAL MASTER EXPORT SYNC CONTRACT (MANDATORY FOR 100% PREVIEW-TO-EXPORT PARITY):
- Always separate timeline data into a dedicated `<CompName>Data.ts` file alongside `<CompName>.tsx` and register `<Composition id="Documentary-{job.get('id')}" component={{<CompName>}} durationInFrames={{...}} fps={{30}} width={{1920}} height={{1080}} />` in `src/Composition.tsx`.
- In `<CompName>Data.ts`, export `<PREFIX>_JOB_ID = "{job.get('id')}"`, `<PREFIX>_DURATION_FRAMES = <total_frames>`, and `<PREFIX>_BEATS` where every beat includes `beatId`, `startFrame`, `endFrame`, `durationInFrames`, `partAFrames`, `partBFrames`, `cameraMode`, `secondaryCameraMode`, `imageFile`, `secondaryImageFile`, `clausesA`, and `clausesB`.
- In `<CompName>.tsx`, export `HIGHLIGHT_KEYWORDS: string[]` and merge consecutive sub-shots sharing the same `filePath` into `MERGED_VISUAL_SHOTS` so `turbo-nvenc-export.mjs` + `universal_master_render.py` can render the exact same camera curves, CSS filters, vignette, and subtitle plates with >32 dB PSNR parity.

{_asset_variety_direction(job)}

{_native_motion_semantic_direction(job)}

Create:
1. `{workspace / 'director_report.md'}` with timestamped findings and verdict.
2. `{workspace / 'final_manifest.json'}` only when the approved render passes, with absolute video_path, `final_qc_status: "ACCEPT"`, `inspected_actual_render: true`, SHA-256, duration, fps, resolution and qc metrics.
"""

    raise ValueError(f"Unknown phase: {phase}")


def build_edit_chat_prompt(
    job: dict[str, Any],
    workspace: str | Path,
    remotion_dir: str | Path,
    message: str,
    history: list[dict[str, Any]] | None = None,
    selected_beat_id: str | None = None,
    selected_timestamp_sec: float | None = None,
    attachments: list[dict[str, Any]] | None = None,
) -> str:
    workspace = Path(workspace).resolve()
    remotion_dir = Path(remotion_dir).resolve()
    creative_brief_direction = _creative_brief_direction(job, workspace, "edit")
    compact_history = [
        {"role": item.get("role"), "content": item.get("content"), "attachments": item.get("attachments") or []}
        for item in (history or [])[-10:]
        if item.get("role") in {"user", "assistant"} and (item.get("content") or item.get("attachments"))
    ]
    attached_images = [
        {
            "id": item.get("id"),
            "name": item.get("name"),
            "mime_type": item.get("mime_type"),
            "path": item.get("path"),
        }
        for item in (attachments or [])
    ]
    current_context = {
        "selected_beat_id": selected_beat_id,
        "selected_timestamp_sec": selected_timestamp_sec,
    }
    from .nexus_coordinator import NexusCoordinator
    from .render_cache import format_smart_hardware_contract
    from .workspace_ledger import (
        build_codebase_surgical_locator,
        build_surgical_work_locator,
        format_compact_ledger_brief,
        get_beat_context_slice,
    )

    ledger_brief = format_compact_ledger_brief(workspace)
    edit_surgical_locator = build_surgical_work_locator(
        workspace,
        f"{selected_beat_id or ''} {message}".strip(),
        history,
        remotion_dir=remotion_dir,
    )
    edit_code_locator = build_codebase_surgical_locator(
        Path(workspace).resolve().parent.parent,
        message,
        history,
    )
    beat_slice = get_beat_context_slice(
        workspace,
        beat_id=selected_beat_id,
        message=message,
        timestamp_sec=selected_timestamp_sec,
        neighbor_radius=1,
        max_targets=6,
    )
    if beat_slice.get("matched"):
        surgical_beat_block = (
            "\nSURGICAL TARGET BEAT SHARDS (`beats/<beat_id>.json` — DO NOT READ FULL `visual_manifest.json`):\n"
            + json.dumps(
                {
                    "matched_beat_ids": beat_slice.get("matched_beat_ids"),
                    "total_beats": beat_slice.get("total_beats"),
                    "target_beats": beat_slice.get("target_beats"),
                    "neighbor_summaries": beat_slice.get("neighbor_summaries"),
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n"
        )
        surgical_rule_2 = (
            f"2. SURGICAL BEAT EDITING LAW: Target beat shard(s) `{beat_slice.get('matched_beat_ids')}` and their 1-line neighbor context are ALREADY loaded above. "
            f"Do NOT read the full `{workspace / 'visual_manifest.json'}` (`{beat_slice.get('total_beats')}` beats) unless the user explicitly asks for a whole-episode overhaul! "
            f"Read/patch only `{workspace / 'beats'}/<beat_id>.json` (or `python -m documentary.workspace_ledger patch-beat --workspace \"{workspace}\" --beat-id <BEAT_ID> --json '{{...}}'`) and update ONLY the matching beat slice in `<CompName>Data.ts` / scene component."
        )
    else:
        surgical_beat_block = (
            f"\nBEAT SHARD INDEX (`{workspace / 'beats_index.json'}`, total_beats={beat_slice.get('total_beats', 0)}): "
            f"Inspect `{workspace / 'beats_index.json'}` and individual `{workspace / 'beats'}/<beat_id>.json` shards instead of reading the full `{workspace / 'visual_manifest.json'}` whenever possible.\n"
        )
        surgical_rule_2 = (
            f"2. Prefer reading `{workspace / 'beats_index.json'}` + individual `{workspace / 'beats'}/<beat_id>.json` shards and `{workspace / 'edit_checkpoint.json'}` for the requested scene instead of loading the entire `{workspace / 'visual_manifest.json'}`. Prefer the selected beat/time above when present."
        )
    if edit_surgical_locator:
        surgical_beat_block += f"\n{edit_surgical_locator}\n"
    if edit_code_locator:
        surgical_beat_block += f"\n{edit_code_locator}\n"

    edit_charter_block = NexusCoordinator().build_phase_charter_block(job, "edit", workspace)
    edit_hw_block = format_smart_hardware_contract("edit")
    _chat_eff_preset = _resolve_vox_preset_id(job)
    _chat_skin = _channel_vox_skin_profile(job)
    if is_creative_audio_drama_job(job):
        edit_chat_rule_4 = (
            "4. Lock 100% to `kr_goodnight_cinema_drama` 2-Gear K-Audio Drama Cinema DNA (`@vox` BYPASSED): enforce Gear 1 (`0:00–0:45` Cold-Open Hook before `CT_01` `제1장` with `0%` black card at `0:00`, `2.4s–4.2s` multi-angle fast cuts, `2–3f` J-cut snaps, `cold_open_push_punch` `1.00 -> 1.105` & Solo Cello Suspense + `1.2s` pre-curtain silence drop), then shift in Gear 2 (`0:45–End`) to ~80% Character-Sheet-locked 35mm warm tungsten keyframes (`Highlight Luma <= 215`, slow Ken Burns `1.00 -> 1.035`, `26f` cross-dissolves), ~15% clean 4K atmospheric B-roll (`0%` third-party faces/logos/subtitles), ~5% warm serif `FramelessCinemaTextBeat.tsx` (`제1장`..`제6장`), Warm Nocturne Piano/Cello BGM (`0%` startle SFX, `0%` VOX boards/maps), and `4.0s` outro fade-out."
        )
    elif _is_director_v2_true_crime_job(job):
        _dv2_desk_tok_c, _dv2_mt_tok_c = _director_v2_desk_and_motion_text_tokens(job)
        edit_chat_rule_4 = (
            f"4. Lock 100% to V23 `forensic_noir_director_v2`: maintain Priority #1 authentic 100px-grid SAFE_CROP & 3-frame verified case archival footage (`0%` unrelated filler B-roll), pair with Priority #2 Voice-to-Vox Prompt × Tactile Vox Editorial Desk `src/vox-studio/vox-editorial-desk/index.tsx` & `<GeoJson3DMapStage>` whenever real footage is absent (`0%` fixed template count, `0%` fixed spacing, `0%` camera zoom-in or zoom-out `z = 1.0`: bespoke per-sentence `vox_prompt` composition on {_dv2_desk_tok_c}, varying 14 Spatial Layouts × 9 Cut-and-Paste Entrances `<SlideIn>` / `voxDiverseEntry12` across `<VoxVideoPaper>`, `<VoxPhotoPaper>`, true RGBA `<DieCutSticker>`, `<TornClipping>`, `<IndexCard>`, `<RedCircle>`, `<RedLine>`, `<Highlight>`, `<DimensionBracket>`, `<OpticalLoupe>`, `0` consecutive scenes repeating layout or entrance, `<GeoJson3DMapStage>` strictly for suspect/police movement routes with `0%` zoom, `[60..1860, 40..820]` safe zone, passing `validate-vox-newsroom-ast.mjs`) + dark {_dv2_mt_tok_c} (`0` adjacent beats, hiding `<SubtitleOverlay>`), and reserve Priority #3 Profile-Locked AI keyframes strictly as last resort for closed-room moments."
        )
    elif _is_non_vox_devotional_job(job):
        edit_chat_rule_4 = (
            "4. Lock 100% to `sacred_devotional` Sacred Golden Sanctuary PiP DNA: keep the frameless 3D drop-shadow floating card (`1180x638`, `borderRadius: 32px`), softly blurred warm golden multi-footage background, gentle 24K silhouette-hugging aura, and subtitle-only lower third (`0%` Vox graphics, `0%` HUD boxes, `0%` chapter popup cards, `0%` jarring zoom/flash cuts)."
        )
    else:
        edit_chat_rule_4 = (
            f"4. Lock 100% to channel-isolated `{_chat_eff_preset}` skin ({_chat_skin['skin_name']} · `{_chat_skin['toolkit']}`, `{_chat_skin['safe_zone']}`) + bespoke VOX Tabletop & Cut-and-Paste Grammar: keep verified 3-frame clean real footage as Priority #1 ({_chat_skin['mix_summary']}), compose every Priority #2 VOX scene on a locked `z = 1.0` overhead stage (`0%` camera zoom-in or zoom-out!) varying 14 Spatial Layouts × 9 Cut-and-Paste Entrances across 18 Semantic Visual Verbs `@voxVerb` synced to Whisper `words[]` (`15% != 50% != 85%`, `0` consecutive scenes repeating layout or entrance, `0` verb repeats in 5 consecutive VOX scenes, mandatory `imageSrc=` `2.4x` loupe, real `>= 12`-pt OSM Overpass GeoJSON on Esri maps, passing `validate-vox-newsroom-ast.mjs --preset {_chat_eff_preset}`), use dark `src/components/FramelessCinemaTextBeat.tsx` (`0` adjacent beats, hiding `<SubtitleOverlay>` — STRICTLY FORBID paper `VoxNewsroomMotionText.tsx`), and repair weak pacing, repeated source footage, dead holds, or repetitive visual skeletons proactively."
        )
    ledger_section = f"\nWORKSPACE LEDGER & PROGRESS SNAPSHOT\n{ledger_brief}\n" if ledger_brief else ""
    return f"""Handle this request as the user's selected AI inside COFI DOCUMENTARY. The open project is your current context, not a fixed role or a restriction on the user's request.
{edit_charter_block}{edit_hw_block}

Your job is to operate the currently open documentary as the production director and senior editor responsible for the finished viewing experience. Stay inside current-project work: footage/stills, maps/charts/native motion, timing, subtitles/text/layout, transitions, cinematic compositing/effects, SFX/audio balance, duplicate visuals, scene pacing, attention/retention rhythm, preview inspection, edit checkpoints, and SEO/thumbnail packaging for this same documentary.
Handle general questions and work outside this project normally when the user asks. For formal competitor-grounded SEO/thumbnail generation, use the app's SEO + Thumbnail step so Radar reference evidence is included and the package is persisted.

Job workspace: {workspace}
CofiRemotion: {remotion_dir}
Composition ID: {job.get('composition_id') or f"Documentary-{job.get('id')}"}

JOB DATA
{_job_context(job)}
{ledger_section}
{creative_brief_direction}

CURRENT EDIT CONTEXT
{json.dumps(current_context, ensure_ascii=False, indent=2)}
{surgical_beat_block}
RECENT EDIT CHAT
{json.dumps(compact_history, ensure_ascii=False, indent=2)}

USER MESSAGE
{message}

ATTACHED IMAGES
{json.dumps(attached_images, ensure_ascii=False, indent=2)}

{_premium_editing_direction(job)}

{_vox_and_remotion_architecture_direction(job)}

UNIVERSAL MASTER EXPORT SYNC CONTRACT (MANDATORY FOR 100% PREVIEW-TO-EXPORT PARITY):
- Always separate timeline data into a dedicated `<CompName>Data.ts` file alongside `<CompName>.tsx` and register `<Composition id="Documentary-{job.get('id')}" component={{<CompName>}} durationInFrames={{...}} fps={{30}} width={{1920}} height={{1080}} />` in `src/Composition.tsx`.
- In `<CompName>Data.ts`, export `<PREFIX>_JOB_ID = "{job.get('id')}"`, `<PREFIX>_DURATION_FRAMES = <total_frames>`, and `<PREFIX>_BEATS` where every beat includes `beatId`, `startFrame`, `endFrame`, `durationInFrames`, `partAFrames`, `partBFrames`, `cameraMode`, `secondaryCameraMode`, `imageFile`, `secondaryImageFile`, `clausesA`, and `clausesB`.
- In `<CompName>.tsx`, export `HIGHLIGHT_KEYWORDS: string[]` and merge consecutive sub-shots sharing the same `filePath` into `MERGED_VISUAL_SHOTS` so `turbo-nvenc-export.mjs` + `universal_master_render.py` can render the exact same camera curves, CSS filters, vignette, and subtitle plates with >32 dB PSNR parity.

{_asset_variety_direction(job)}

{_native_motion_semantic_direction(job)}

OPERATING RULES
1. Read `{remotion_dir / 'AGENTS.md'}` before changing Remotion source. Treat existing source as the current edit state and continue from it.
1a. {_official_remotion_agent_skills_direction()}
{surgical_rule_2}
2a. Local workspace and command tools are attached with write access. Use the absolute paths printed above because the command working directory is CofiRemotion and the job workspace is an additional writable directory. An empty command result means no match in that searched location; it does not mean tools or permissions are missing. Before reporting any access problem, attempt the exact absolute workspace or CofiRemotion path and quote the concrete tool error.
3. When the user requests a concrete edit, perform it directly. Do not stop at instructions or a plan.
{edit_chat_rule_4}
5. When the user asks to export, use the app's QC/export flow so the result is persisted and verified.
6. Before publishing, validate the edited source from the CofiRemotion directory: run ESLint with `--quiet` on every edited TS/TSX file, then run `npx remotion compositions src/index.ts --log=error`. If either command fails, fix the source and validate again; never publish an edit that leaves Studio in an error state.
7. After every validated viewer-facing source edit, publish the changed beat/frame using `{remotion_dir / 'scripts' / 'publish-live-edit.mjs'}` with job ID `{job.get('id')}`, composition ID `{job.get('composition_id') or f"Documentary-{job.get('id')}"}`, workspace `{workspace}`, beat/time or frame, and a short Vietnamese message. This makes Studio HMR update and auto-seek.
8. Update `{workspace / 'edit_checkpoint.json'}` after meaningful edits.
9. Reply in concise Vietnamese. State what you changed and where when work was performed.
10. When ATTACHED IMAGES is non-empty, inspect the images attached to this Codex turn before answering or editing. Use them as visual references for the user's request.
"""


def build_edit_batch_prompt(
    job: dict[str, Any],
    workspace: str | Path,
    remotion_dir: str | Path,
    beats: list[dict[str, Any]],
    *,
    completed_beat_ids: list[str] | None = None,
    batch_index: int = 1,
    total_batches: int = 1,
) -> str:
    """Build one resumable Edit-phase prompt for the current pending beats."""
    base = build_phase_prompt(job, "edit", workspace, remotion_dir)
    workspace = Path(workspace).resolve()
    batch_ids = [str(beat.get("beat_id") or "").strip() for beat in beats]
    batch_ids = [beat_id for beat_id in batch_ids if beat_id]
    completed = [str(value) for value in (completed_beat_ids or []) if str(value)]
    continuous = total_batches == 1
    heading = "CONTINUOUS EDIT EXECUTION" if continuous else f"BATCHED EDIT EXECUTION — BATCH {batch_index}/{total_batches}"
    intro = (
        "Run continuously through every pending beat ID below until the edit is complete. Do not stop merely because the timeline is long."
        if continuous
        else "This turn is intentionally scoped to the beat IDs below."
    )
    finish_rule = (
        "Continue until every beat ID below is complete."
        if continuous
        else "Stop after these beat IDs are complete. Do not continue into later batches even if context remains."
    )
    _b_lang = str(job.get("language") or "ko").strip().lower()
    _b_sub_lang = "Korean subtitles" if _b_lang == "ko" else "target-language subtitles"
    _b_ai_lbl, _b_ai_ref = _resolve_profile_ai_style_info(job)
    _b_ai_clause = f"`{_b_ai_lbl}` + `{_b_ai_ref}`" if _b_ai_ref else f"`{_b_ai_lbl}`"
    _b_chap_lock, _b_ai_disc = _resolve_lang_editorial_labels(job)
    _b_eff_preset = _resolve_vox_preset_id(job)
    _b_skin = _channel_vox_skin_profile(job)
    if is_creative_audio_drama_job(job):
        batch_rule_2b = (
            "2b. K-AUDIO DRAMA 2-GEAR CINEMA EXECUTION (`kr_goodnight_cinema_drama` — FAST-CUT HOOK `0:00–0:45` + SERENE BEDTIME 80/15/5 BODY `0:45–END`, ZERO VOX GRAPHICS, ZERO 3D MAPS): "
            "Verify `mtime`/`duration`/`sha256` of the newest `narration.wav` (`0.94x` bedtime cadence) + `voice_manifest.json` synced to `public/jobs/<job_id>/audio/narration.wav` and purge stale caches. "
            "**Gear 1 (`0:00–0:45` Cold-Open Hook before `CT_01` `제1장`)**: Open Frame 0 directly on the confrontation visual (`0%` black chapter card at `0:00`), cut `2.4s–4.2s` multi-angle `Part A + Part B` sub-shots (`2–3f` J-cut snaps, `cold_open_push_punch` `1.00 -> 1.105` / `cold_open_pull_shock`, chiaroscuro contrast, Solo Cello Suspense `w03_dignity_tension_cello` `-18.5dB` + `1.2s` silence breath before `CT_01`). "
            "**Gear 2 (`0:45–End` Post-Hook Body)**: Sequence ~80% Character-Sheet-locked 35mm warm tungsten keyframes (`<beat_id>_ai_keyframe.jpg` via `media/character_sheet/*.jpg`, `Highlight Luma <= 215`, slow Ken Burns `1.00 -> 1.035`, `26-frame` cross-dissolves), "
            "~15% clean 4K atmospheric B-roll (`footage/S_F*.mp4`, `0%` news/faces/logos/subtitles, muted `-an`, `brightness(0.84)`), and ~5% warm serif `FramelessCinemaTextBeat.tsx` (`제1장`..`제6장`, hiding `<LiveSubtitleOverlay>`, `0%` VOX Editorial Desk, `0%` `<GeoJson3DMapStage>`). "
            "Render balanced 1–2 line warm-ivory frameless Korean subtitles (`58px–60px`, `0%` right-edge clipping), mix 16–24 segments of Warm Nocturne Piano/Cello BGM (`-22` to `-25dB` under voice, `-16.0 LUFS`, `0%` startle SFX), and preserve 100% closing narration + `4.0s` outro fade-out."
        )
    elif _is_director_v2_true_crime_job(job):
        _dv2_desk_tok_b, _dv2_mt_tok_b = _director_v2_desk_and_motion_text_tokens(job)
        batch_rule_2b = (
            "2b. 3-TIER VISUAL PRIORITY (`#1 Eye-Verified Real Footage -> #2 Bespoke VOX Illustration -> #3 AI Image Last Resort`) + MOTION TEXT EXECUTION (`forensic_noir_director_v2`): "
            "First verify `mtime`/`duration`/`sha256` of the newest `narration.wav` + `voice_manifest.json` (`words[]`) synced to `public/jobs/<job_id>/audio/narration.wav` (speech must flow 100% continuously) and clear stale `.m4a`/chunk caches. "
            "Route every beat with 100% voice-locked fidelity: "
            "**Priority #1 Eye-Verified Case Archival Footage (`footage/S_F*.mp4`, sourced via `documentary.edit_footage_fetcher` with `--probe-storyboard` + `100px` grid `crop=W:H:X:Y` + `--start-offset` + `--observed-content`, `3.0–5.0s/cut`, `Part A + Part B` for beats `>= 6.2s`, clip tail `>= 0.35s`, `-an` + `volume={0}`, `max_uses = 1`, `0%` third-party logos/running text/foreign subs/TV anchors, `100%` match with spoken sentence meaning, `0%` automatic cutting or automatic splicing)** + "
            f"**Priority #2 Bespoke Voice-to-Vox Prompt × Tactile Vox Editorial Desk `src/vox-studio/vox-editorial-desk/index.tsx` & `<GeoJson3DMapStage>` (mandatory whenever a sentence lacks 100%-matching real footage, `0%` fixed template count, `0%` fixed spacing, `0%` camera zoom-in or zoom-out `z = 1.0`, `[60 <= x <= 1860, 40 <= y <= 820]`, {_b_chap_lock}: MỖI CẢNH LÀ ĐỘC LẬP, MỖI VIDEO LÀ ĐỘC LẬP — compile each beat's spoken Korean sentence (`clauses[0..N]`) via `voice_meaning -> illustration_content -> vox_prompt` onto {_dv2_desk_tok_b}, locked overhead `<Desk>` tabletop (`0%` zoom-in or zoom-out), varying 14 Spatial Layouts × 9 Cut-and-Paste Entrances `<SlideIn>` / `voxDiverseEntry12` (`0` consecutive repeats of layout or entrance), `<RedCircle>` ONLY when needed, `0%` decorative clutter; deploy `<GeoJson3DMapStage>` strictly for suspect/police movement routes with exact real-world WGS84 coordinates, >=12-pt road/rail polylines, and `0%` zoom; enforce `15% != 50% != 85%`, passing `validate-vox-newsroom-ast.mjs`)** + "
            f"**Dark {_dv2_mt_tok_b} (3 Ironclad Motion Text Laws: [1] 0% repeating 1 motion/font/layout across the episode and 0 consecutive duplicate styles, [2] flexible placement strictly at true narrative drop points per job — 0% mechanical periodic spacing, `0` adjacent consecutive beats, hiding `<SubtitleOverlay>` underneath, [3] 100% context-matched `fontStyle`, `accentColor`, `layoutVariant` & `showroomRenderer` in `CinemaTextSpecs.ts`; strictly forbidding `VoxNewsroomMotionText.tsx` paper cards)** + "
            f"**Priority #3 Last Resort Profile-Locked AI Keyframes (`<beat_id>_ai_keyframe.jpg` via {_b_ai_clause}, closed-room moments ONLY where neither real footage nor VOX illustration applies, with frameless `{_b_ai_disc}`)**. "
            "Write `edit_manifest.json` with exact role counts and `semantic_verified_footage_routing: true`, render large `62px–66px` (min `58px`) frameless subtitles (`Pretendard ExtraBold`, `#FDE047` highlights, balanced 1–2 line wrap), mix linear `-14.8 LUFS` 8-Mood Story-Arc BGM (`-41dBFS` analog room-tone floor on pre-twist drops, active `search_and_fetch_contextual_bgm`) + organic motion-bound SFX (on VOX/CinemaText/Map/Chapter ONLY), preserve 100% complete closing narration + `3.8s` outro BGM fade-out, and run AST + 3-Frame Multimodal Screening verification."
        )
    elif _is_non_vox_devotional_job(job):
        batch_rule_2b = (
            "2b. SACRED GOLDEN SANCTUARY PiP EXECUTION (`sacred_devotional` — ZERO VOX GRAPHICS, SUBTITLE-ONLY): "
            "Verify the newest `narration.wav` + `voice_manifest.json` synced to `public/jobs/<job_id>/audio/narration.wav` and purge stale caches. "
            "Maintain the frameless 3D drop-shadow floating card (`1180x638`, `borderRadius: 32px`) with gentle 24K silhouette-hugging gold sparkles over a continuous warm blurred multi-footage background (`60–90+` clean real clips, smooth seamless dissolves, `0` flash/zoom cuts), render clean lower-third "
            + _b_sub_lang
            + " ONLY (`0%` Vox graphics, `0%` HUD boxes, `0%` chapter popup cards), and preserve 100% closing narration + warm outro fade-out."
        )
    else:
        batch_rule_2b = (
            f"2b. CHANNEL-ISOLATED SKIN (`{_b_eff_preset}`) + BESPOKE VOX TABLETOP & CUT-AND-PASTE EXECUTION (`0%` CAMERA ZOOM-IN / ZOOM-OUT): "
            "First verify `mtime`/`duration`/`sha256` of the newest `narration.wav` + `voice_manifest.json` (`words[]`) synced to `public/jobs/<job_id>/audio/narration.wav` and purge stale `.m4a`/chunk caches. "
            f"Route beats strictly by spoken sentence meaning under `{_b_eff_preset}` ({_b_skin['mix_summary']}): "
            "**Priority #1 3-Frame Verified Clean Real Footage (`3.0–5.0s/cut`, `Part A + Part B` for beats `>= 6.2s`, `-an` + `volume={0}`, `max_uses = 1`, `0%` logos/foreign subs/TV anchors, `0` frozen frames)** + "
            f"**Priority #2 Bespoke VOX Tabletop & Cut-and-Paste Motion (`{_b_skin['toolkit']}`, `{_b_skin['safe_zone']}`, {_b_chap_lock}: isolate skin/palette strictly to `{_b_skin['skin_name']}`, lock overhead camera to `z = 1.0` (`0%` zoom-in or zoom-out!), vary 14 Spatial Layouts × 9 Cut-and-Paste Entrances across 18 Semantic Visual Verbs `@voxVerb` + `GeoJson3DMapStage` >=12-pt OSM Overpass GeoJSON + True `2.4x` `OpticalGlassLoupe` w/ `imageSrc=`; enforce `15% != 50% != 85%`, `0` consecutive repeats of layout or entrance, `0` repeated `@voxVerb` in 5 consecutive VOX scenes, passing `validate-vox-newsroom-ast.mjs --preset {_b_eff_preset}`)** + "
            "**Situational Dark `FramelessCinemaTextBeat.tsx` (`0` boxes, `0` adjacent beats, hides `<SubtitleOverlay>`; strictly forbid paper `VoxNewsroomMotionText.tsx`)** + "
            f"**Minimized 1-to-1 Scene-Locked AI Keyframes (`<beat_id>_ai_keyframe.jpg` via {_b_ai_clause}, `max_uses = 1`, closed-room/unfilmed moments with frameless `{_b_ai_disc}` when applicable)**. "
            "Render frameless "
            + _b_sub_lang
            + " (`<SubtitleOverlay>`), mix 8-Mood Story-Arc BGM (`-18 LUFS`, `-41dBFS` / `volume: 0.015` analog room-tone floor on pre-twist drops, active `search_and_fetch_contextual_bgm` when fresh tracks are needed) + 100% motion-bound SFX (on VOX/Map/Chapter motion `offsetFrames` ONLY — `0` SFX on `REAL_FTG` and `AI_4D`), and preserve 100% complete closing narration + `3.8s` outro BGM fade-out."
        )
    verified_ftg_map: dict[str, str] = {}
    try:
        hyg_p = workspace / "footage_hygiene_report.json"
        if hyg_p.is_file():
            hyg_d = json.loads(hyg_p.read_text(encoding="utf-8"))
            for row in (hyg_d.get("assets") or hyg_d.get("verified_assets") or []):
                if isinstance(row, dict):
                    rbid = str(row.get("beat_id") or "").strip()
                    rpath = str(row.get("public_file") or row.get("clip_path") or row.get("file") or row.get("path") or "").strip()
                    if rbid and rpath:
                        verified_ftg_map[rbid] = Path(rpath).name
        pub_ftg_dir = Path(remotion_dir).resolve() / "public" / "jobs" / str(job.get("id") or workspace.name).strip() / "footage"
        if pub_ftg_dir.is_dir():
            for mp4_p in sorted(pub_ftg_dir.glob("*.mp4")):
                stem_bid = mp4_p.stem.split("_")[0].strip()
                if stem_bid:
                    verified_ftg_map.setdefault(stem_bid, f"footage/{mp4_p.name}")
    except Exception:
        pass
    compact_beats = [
        {
            "beat_id": b.get("beat_id"),
            "start_sec": b.get("start_sec"),
            "end_sec": b.get("end_sec"),
            "visual_route": b.get("visual_route"),
            "visual_type": b.get("visual_type"),
            "editorial_layer": b.get("editorial_layer") or b.get("dna_visual_slot"),
            **(
                {"footage_file": verified_ftg_map[str(b.get("beat_id") or "").strip()]}
                if str(b.get("beat_id") or "").strip() in verified_ftg_map
                else {}
            ),
            **(
                {"vox_scene_id": b.get("vox_scene_id") or b.get("voxSceneId")}
                if (b.get("vox_scene_id") or b.get("voxSceneId"))
                else {}
            ),
            "narration_text": b.get("narration_text"),
        }
        for b in beats
    ] if len(beats) > 24 else beats
    remotion_batch_locator = ""
    try:
        from .workspace_ledger import _locate_remotion_job_targets

        rem_lines = _locate_remotion_job_targets(
            workspace,
            batch_ids[:6],
            "edit remotion",
            remotion_dir=remotion_dir,
        )
        if rem_lines:
            remotion_batch_locator = (
                "\nREMOTION SOURCE & LINE LOCATOR FOR THIS JOB (Read/Edit ONLY the target line slices below — do NOT read full `*Data.ts`):\n"
                + "\n".join(rem_lines[:8])
                + "\n"
            )
    except Exception:
        pass
    return base + f"""

{heading}

{intro} Edit ONLY these beat IDs:
{json.dumps(batch_ids, ensure_ascii=False)}
{remotion_batch_locator}
Beat summary for this batch (pre-verified footage files are already attached in `footage_file` below; when detailed per-beat `footage_search_queries` or `framing_motion_intent` are needed, read `{workspace / 'beats_index.json'}` or individual `{workspace / 'beats'}/<beat_id>.json` shards instead of reading the entire `{workspace / 'visual_manifest.json'}`):
{json.dumps(compact_beats, ensure_ascii=False, indent=2)}

Already completed in earlier batches:
{json.dumps(completed, ensure_ascii=False)}

Rules for this batch:
1. Preserve all already-completed beats. Do not rebuild or restyle them unless a shared composition-level fix is strictly required for this batch to work.
2. Finish every beat in this batch: correct footage/still placement, timing, editorial subtitles/typography, useful native motion, authored cinematic motion/compositing, scene-specific transitions, and designed SFX/audio where appropriate. Review approved alternatives and nearby timeline usage so the same source file/time range is not repeated as filler when another accurate approved asset would improve the sequence. Keep one clear focal point and vary intensity by story function.
{batch_rule_2b}
3. Save source changes frequently so Remotion Studio HMR can show them immediately. Publish live-edit events as required by the EDIT rules above.
4. After EACH beat is fully finished and its viewer-facing changes are saved/published, immediately update `{workspace / 'edit_progress.json'}` before moving to the next beat. Preserve all existing fields and assigned IDs; add that beat ID to `completed_beat_ids`, remove it from `pending_beat_ids`, update `completed_beats` and `status_message`, and write the JSON safely through a temporary file + replace. This beat-level progress is the resume point after a disconnect or app restart.
5. {finish_rule}
6. Do not render/export. The outer coordinator will record the durable checkpoint after this batch returns successfully.
"""


def build_producer_chat_prompt(
    jobs: list[dict[str, Any]],
    message: str,
    history: list[dict[str, Any]] | None = None,
    selected_job_id: str | None = None,
    app_tab: str | None = None,
    attachments: list[dict[str, Any]] | None = None,
    app_context: dict[str, Any] | None = None,
    agents: list[dict[str, Any]] | None = None,
) -> str:
    compact_jobs = []
    for job in jobs[:30]:
        compact_jobs.append({
            "id": job.get("id"),
            "title": job.get("title"),
            "market": job.get("market"),
            "language": job.get("language"),
            "status": job.get("status"),
            "current_phase": job.get("current_phase"),
            "voice": job.get("voice") or {},
            "phases": {
                phase: (job.get("phases") or {}).get(phase, {}).get("status")
                for phase in ("plan", "voice", "visuals", "footage", "ai_visual", "edit", "seo", "qc")
            },
        })
    compact_history = []
    remaining_history_chars = 12_000
    for item in reversed((history or [])[-12:]):
        if item.get("role") not in {"user", "assistant"} or not (item.get("content") or item.get("attachments")):
            continue
        if remaining_history_chars <= 0:
            break
        content = str(item.get("content") or "")
        allowance = min(2_500, remaining_history_chars)
        if len(content) > allowance:
            head = allowance // 2
            content = content[:head] + "…" + content[-(allowance - head - 1):]
        remaining_history_chars -= len(content)
        compact_history.append({"role": item.get("role"), "content": content, "attachments": item.get("attachments") or []})
    compact_history.reverse()
    attached_images = [
        {
            "id": item.get("id"),
            "name": item.get("name"),
            "mime_type": item.get("mime_type"),
            "path": item.get("path"),
        }
        for item in (attachments or [])
    ]
    from .nexus_coordinator import NexusCoordinator
    orchestrator_charter = NexusCoordinator().build_specialist_soul_header(
        "orchestrator",
        "In-App Coordinator Chatbot & Multi-Agent Dispatcher",
    )
    return f"""Handle this user turn as the Executive Dispatcher (`orchestrator`) session embedded in COFI DOCUMENTARY.

{orchestrator_charter}
TỔNG ĐIỀU PHỐI 4 TUYẾN KHÔNG MÂU THUẪN (`COFI EXECUTIVE PRODUCER — ZERO POLLING, ZERO RE-READING WHOLE PROJECT, SURGICAL BEAT PATCH`):
Bạn là Tổng Đạo Diễn Điều Phối Sản Xuất (`orchestrator` / `Cofi Executive Producer`) của COFI DOCUMENTARY, chỉ huy Tập thể 15 Nhân viên Chuyên trách thuộc 4 Phòng ban Studio (`Direction`, `Editorial`, `Visual Cinema`, `Quality & Engineering` — mã nguồn độc lập tại `agents/<division>/<id>.md`).

4 TUYẾN PHÂN LUỒNG RÕ RÀNG (KHÔNG CHỒNG CHÉO, KHÔNG ĐỨNG HÌNH):
1. **Tuyến 1 — Hỏi Tiến Độ / Trạng Thái (`0` Tool Call, Trả Lời Ngay)**:
   - Khi người dùng hỏi đang làm đến đâu, ở bước nào, bao nhiêu beat đã xong, hay tại sao lâu: trả lời ngay lập tức từ `CURRENT APP CONTEXT` (`selected_job.state_ledger`, `selected_job.phases`, `live_progress`) và `PROJECTS` với `actions: []`.
2. **Tuyến 2 — Bàn Ý Tưởng, Cập Nhật Nhanh Metadata & Quét Chủ Đề (`verify_with_qa: false`)**:
   - Lên ý tưởng/cập nhật bản nháp (`fill_create_form`), tạo dự án mới (`create_job`), sửa brief/dàn ý/kịch bản (`update_creative_brief`, `update_outline`, `update_script`), quét chủ đề (`radar_market_scan`, `radar_channel_scan`, `channel_profile_today`): trả về đúng host action gọn nhất, **không chạy kiểm duyệt `@evidence_qa`/`@qc`**.
3. **Tuyến 3 — Sản Xuất Các Bước Làm Video & Phẫu Thuật Beat (`Fire-and-Return`, `verify_with_qa: true`)**:
   - Chạy dây chuyền 8 bước làm video (`plan` -> `voice` -> `visuals` -> `footage` -> `ai_visual` -> `edit` -> `seo` -> `qc`): trả về `run_phase`, `rerun_phase`, `run_pipeline`, `approve_step`, hoặc ủy nhiệm chuyên sâu qua `delegate_agent` / `delegate_squad` (`"radar"`, `"research"`, `"script"`, `"voice"`, `"visuals"`, `"footage"`, `"ai_visual"`, `"vox"`, `"edit"`, `"seo"`, `"evidence_qa"`, `"qc"`) với `"verify_with_qa": true`.
   - Sửa đúng 1 đoạn/cảnh/mốc giây trong bản dựng: trả về action `edit` ghi rõ mã beat (`B012`) hoặc mốc thời gian (`03:15`) để trình dựng chỉ sửa đúng beat shard đó (`beats/<beat_id>.json`), `0%` đọc lại toàn bộ `visual_manifest.json`.
4. **Tuyến 4 — Sửa Mã Nguồn / Giao Diện / Debug Hệ Thống (`dev` / `debug`, `verify_with_qa: false`)**:
   - Khi cần sửa code/bug/UI của ứng dụng CofiDocumentary hoặc CofiRemotion qua giao thức JSON action này, giao cho `"dev"` hoặc `"debug"` qua `delegate_agent` với `"verify_with_qa": false` (không chạy cổng QA sản xuất video cho tác vụ kỹ thuật phần mềm).

DÂY CHUYỀN SẢN XUẤT 8 BƯỚC (PHÂN CÔNG RÕ RÀNG TỪNG AGENT):
1. Nghiên cứu / Radar (`radar` -> `research` + `script` trong `plan`): Tìm chủ đề, điều tra hồ sơ gốc, lập dàn ý 5 Hồi (`outline.json`), viết kịch bản (`script.md`) và lập kế hoạch hình ảnh (`visual_manifest.json` + tự động tách `beats_index.json` / `beats/<beat_id>.json`). Action: `radar_market_scan`, `create_job`, `run_phase` `"plan"`, hoặc `delegate_squad` `["research", "script"]`.
2. Voice & SRT (`voice`): Thu âm narration bằng giọng đọc của hồ sơ kênh, tách mệnh đề ngắn và căn chuẩn timestamp từng từ (`words[]`). Action: `update_voice`, `run_phase` `"voice"`, `rerun_phase` `"voice"`, hoặc `delegate_agent` `"voice"`.
3. Visuals / Phân cảnh (`visuals`): Chia 100% lời thoại thành các beat ngắn đủ nghĩa (1-to-1 STP) và định tuyến trung thực giữa Tư liệu thật, Cơ chế VOX toàn màn hình, Chữ điện ảnh và Ảnh AI góc kín. Action: `run_phase` `"visuals"` hoặc `delegate_agent` `"visuals"`.
4. Tư liệu thật / Footage (`footage`): Tìm nguồn tư liệu thật đúng vụ án, soi lưới tọa độ `100px` cắt sạch 4 cạnh, kiểm tra chuyển động quang học thật (`15% != 50% != 85%`) và độ độc nhất `dHash >= 14`. Action: `run_phase` `"footage"`, `rerun_phase` `"footage"`, `pause_footage`, `resume_footage`, `restart_footage`, hoặc `delegate_agent` `"footage"`.
5. AI Visual góc kín (`ai_visual`): Tạo ảnh AI 1-to-1 (`{{bid}}_ai_keyframe.jpg`) theo đúng phong cách hồ sơ kênh cho các cảnh góc kín trong phòng. Action: `run_phase` `"ai_visual"`, `rerun_phase` `"ai_visual"`, hoặc `delegate_agent` `"ai_visual"`.
6. Cơ chế VOX & Dựng video (`vox` + `edit` + `evidence_qa`): `@vox` thiết kế bàn biên tập cắt dán chuẩn Vox (`0%` zoom-in/zoom-out, biến thiên 14 bố cục × 9 hiệu ứng xuất hiện `12fps`); `@edit` lắp ráp timeline theo tỷ lệ `visual_mix` của kênh, trộn 8-Mood Story-Arc BGM + Motion-Bound SFX và giữ `3.8s` nhạc nền fade-out; `@evidence_qa` kiểm định mắt 3-frame, AST, `dHash >= 14` xuyên suốt giữa Footage & VOX và Motion Energy. Action: `edit`, `start_remotion`, `run_phase` `"edit"`, hoặc `delegate_squad` `["footage", "vox", "edit", "evidence_qa"]`.
7. SEO & Thumbnail (`seo`): Đóng gói tiêu đề, mô tả, tags và thiết kế Thumbnail CTR cao theo hồ sơ kênh. Action: `run_phase` `"seo"`, `design_thumbnail`, `generate_thumbnail_bg`, hoặc `delegate_agent` `"seo"`.
8. Kiểm định MP4 cuối (`qc`): Kiểm tra toàn diện file `release/video.mp4` (luồng hình/tiếng, độ độc nhất `dHash` toàn cục, chuyển động quang học thật, chuẩn âm lượng EBU R128). Action: `run_phase` `"qc"` hoặc `delegate_agent` `"qc"`.

TỰ ĐỘNG TIẾP TỤC QUY TRÌNH (ADVANCE PIPELINE):
Khi người dùng yêu cầu tiếp tục quy trình (ví dụ: "tiếp tục", "làm tiếp", "chạy tiếp", "bước tiếp theo", "chạy quy trình", "chạy nốt đi", "fix rồi chạy nốt đi"), dựa trên `selected_job.state_ledger` và `phases` để trả về `run_pipeline` hoặc `run_phase` từ đúng bước đang dở (không chạy lại các bước đã `succeeded` trừ khi người dùng yêu cầu làm lại).

CURRENT APP CONTEXT
{json.dumps(app_context or {"app_tab": app_tab or "overview", "selected_job_id": selected_job_id}, ensure_ascii=False, indent=2)}

PROJECTS
{json.dumps(compact_jobs, ensure_ascii=False, indent=2)}

AVAILABLE SPECIALISTS
{json.dumps(agents or [], ensure_ascii=False, indent=2)}

RECENT CHAT
{json.dumps(compact_history, ensure_ascii=False, indent=2)}

USER MESSAGE
{message}

ATTACHED IMAGES
{json.dumps(attached_images, ensure_ascii=False, indent=2)}

Return exactly one JSON object and no markdown fences:
{{
  "reply": "concise Vietnamese reply",
  "actions": [ ... ]
}}

Host runtime operations:
- {{"type":"delegate_agent","agent_id":"orchestrator|radar|research|script|voice|visuals|footage|ai_visual|vox|edit|seo|evidence_qa|qc|dev|debug","task":"specific bounded task","job_id":"optional exact project id","verify_with_qa":true}} — run one CofiDocumentary Studio specialist in an isolated provider session with enforced directory & artifact permissions (`verify_with_qa: true` for video production phases; `verify_with_qa: false` for `radar`, `dev`, `debug`).
- {{"type":"delegate_squad","agents":["research","script"],"task":"specific multi-step objective","job_id":"optional exact project id","verify_with_qa":true}} — run an ordered Cofi Studio multi-agent handoff chain (`2..6` specialists) with NEXUS Handoff Packets.
- {{"type":"select_job","job_id":"exact project id"}}
- {{"type":"navigate","tab":"overview|radar|create|script|voice|visuals|footage|ai_visual|edit|seo|qc|projects|codex"}}
- {{"type":"fill_create_form","payload":{{"title":"...","market":"KR|JP|US|VN","language":"ko|ja|en|vi","target_duration_minutes":15,"visual_strategy":"full_ai|full_footage|hybrid|evidence_footage|edit_direct_footage","notes":"...","creative_brief":{{"narrative_angle":"free-form narrative angle","writing_style":"free-form writing style","hook_archetype":"free-form hook structure","editing_archetypes":["free-form visual/editing grammar"],"opening_hook":"...","custom_rules":"..."}},"outline":[{{"chapter":1,"title":"...","summary":"...","evidence_anchor":"...","visual_note":"..."}}]}}}} — LIVE SYNC: whenever brainstorming or proposing a project idea/angle/style/outline before creation, return this action so the Create Project screen updates live without any button clicks.
- {{"type":"create_job","start_plan":true,"payload":{{"title":"...","market":"KR|JP|US|VN","language":"ko|ja|en|vi","target_duration_minutes":15,"source_url":null,"notes":"","plan_engine":"codex","visual_strategy":"full_ai|full_footage|hybrid|evidence_footage|edit_direct_footage","ai_media_mode":"image|video|mixed","ai_visual":{{"style_mode":"auto|preset|custom","style_preset":"","custom_style":""}},"footage_mode":"vision_codex","voice":{{"voice_id":null,"speed":1.0,"mode":"balanced"}},"creative_brief":{{"narrative_angle":"...","writing_style":"...","hook_archetype":"...","editing_archetypes":["..."],"opening_hook":"...","custom_rules":"..."}},"outline":[{{"chapter":1,"title":"...","summary":"...","evidence_anchor":"...","visual_note":"..."}}]}}}} — when the user agrees/confirms in chat (e.g. "ok", "đồng ý", "chốt", "tạo dự án đi"), immediately create the project with everything discussed and start the script phase (`start_plan: true`).
- {{"type":"create_job_from_radar","scan_id":1,"video_id":"...","overrides":{{...}}}}
- {{"type":"approve_step","job_id":"..."}} — when the user approves the current step in chat (e.g. "duyệt", "ok chạy tiếp bước sau", "tiếp tục"), automatically start the next phase in the project's pipeline and switch the UI to that step.
- {{"type":"run_phase","job_id":"...","phase":"plan|voice|visuals|footage|ai_visual|edit|seo|qc"}}
- {{"type":"rerun_phase","job_id":"...","phase":"plan|voice|visuals|footage|ai_visual|edit|seo|qc"}}
- {{"type":"pause_footage","job_id":"..."}}
- {{"type":"resume_footage","job_id":"..."}}
- {{"type":"stop_footage","job_id":"..."}}
- {{"type":"restart_footage","job_id":"..."}}
- {{"type":"run_pipeline","job_id":"...","from_phase":"plan|voice|visuals|footage|ai_visual|edit|seo|qc","through_phase":"plan|voice|visuals|footage|ai_visual|edit|seo|qc"}}
- {{"type":"resume","job_id":"..."}}
- {{"type":"update_voice","job_id":"...","voice_id":null,"speed":1.0,"mode":"balanced"}}
- {{"type":"start_remotion","job_id":"..."}}
- {{"type":"edit","job_id":"...","message":"specific edit request"}}
- {{"type":"radar_market_scan","payload":{{"market":"KR","seeds":["..."],"days":7,"max_videos":60,"content_type":"factual_documentary"}}}}
- {{"type":"radar_channel_scan","payload":{{"channel_ref":"...","content_type":"factual_documentary"}}}}
- {{"type":"refresh_channel_profile","profile_id":"saved channel profile id"}}
- {{"type":"channel_profile_today","profile_id":"saved channel profile id"}}
- {{"type":"radar_today"}}
- {{"type":"update_creative_brief","job_id":"...","creative_brief":{{"narrative_angle":"...","writing_style":"...","hook_archetype":"...","editing_archetypes":["..."],"opening_hook":"...","custom_rules":"..."}}}}
- {{"type":"update_outline","job_id":"...","outline":[{{"chapter":1,"title":"...","summary":"...","evidence_anchor":"...","visual_note":"..."}}]}}
- {{"type":"update_script","job_id":"...","script":"full updated script.md content"}}
- {{"type":"save_playbook","payload":{{"name":"...","description":"...","creative_brief":{{...}}}}}}
- {{"type":"design_thumbnail","job_id":"...","archetype":"broadcast_left_heavy|bottom_cinematic|split_duality|evidence_spotlight|right_heavy_confrontation","active_variant_id":"v1|v2|v3|v4","badge_text":"...","line_1":"...","line_2":"..."}} — design or update the Fabric.js layered thumbnail in Tab SEO + Thumbnail (`thumbnail_design.json`).
- {{"type":"generate_thumbnail_bg","job_id":"...","prompt":"clean 16:9 base image prompt without text"}} — generate a clean 16:9 base thumbnail image (`thumbnail_bg.jpg`) using Google Labs Flow and load it into Thumbnail Studio.

Rules:
1. Use exact project IDs from PROJECTS. If the user refers to the currently selected project, use selected_job_id.
2. Use the smallest set of actions that completes the request. Navigation/select actions may be combined with a real operation.
3. CONVERSATIONAL BRAIN-TO-PROJECT FLOW (ZERO BUTTONS NEEDED):
   - When brainstorming a new video with the user in chat (before they confirm creation), propose creative ideas freely (never restrict yourself to 5 fixed dropdown labels) and ALWAYS include a `fill_create_form` action so the Create Project screen on the left updates live as you talk.
   - As soon as the user agrees/confirms in chat ("ok", "đồng ý", "chốt", "làm đi", "tạo dự án đi"), return `create_job` (with `start_plan: true` and all agreed `creative_brief` + `outline` fields) so the project is created and moves to the Script (`Kịch bản`) step automatically.
   - At the Script step and all subsequent steps (`voice`, `visuals`, `footage`, `ai_visual`, `edit`, `seo`, `qc`), the user can approve, regenerate, or edit either manually on the UI or via chat (`update_creative_brief`, `update_outline`, `update_script`, `edit`, `rerun_phase`, `approve_step`).
4. A request to change the actual video cut, footage, map, subtitle, effect, SFX, timing, or scene is an `edit` action. The host routes it to the existing realtime editor and preview bridge. For Cofi application source changes, delegate to dev/debug and review the report and tests.
5. `qc` means export + final QC and should only be used when the user explicitly asks to export/approve the finished video.
6. If essential information is missing, return `actions: []` and ask one concise question in `reply`.
7. If the user only asks about current app/project status, answer from PROJECTS with `actions: []`.
8. Do not invent a project ID, scan ID, video ID, voice ID, or URL.
9. When ATTACHED IMAGES is non-empty, inspect the images attached to this Codex turn and use their visual content as context. Do not use shell/filesystem tools merely to read them; they are already attached natively.
10. CURRENT APP CONTEXT is authoritative for where the user is currently working. Use app_tab, selected_job.current_phase, phase statuses, and live_progress when answering status/progress questions or interpreting words like “ở đây”, “bước này”, “đang chạy”, or “tiếp tục”.
11. `reply` is user-facing plain Vietnamese text only. Never put JSON, action objects, field names, markdown code fences, or escaped control syntax inside `reply`.
12. Emit strict JSON. Never markdown-escape JSON punctuation or identifiers: write `actions`, `rerun_phase`, `job_id`, `ai_visual` exactly, never `actions:\\[...]`, `rerun\\_phase`, `job\\_id`, or `ai\\_visual`.
13. When the user explicitly asks to run several production phases in order, return one `run_pipeline` action covering that contiguous range. Do not return multiple `run_phase`/`rerun_phase` actions for a sequential pipeline because only one background production job can run at a time.
14. The host executes actions before showing the reply. You may say an operation has started only when you also return the corresponding action. If the host action fails, the host will replace the reply with the real error.
15. Never simulate execution progress with analysis text, run_command messages, or generic "AI đang phân tích/đang hoạt động" updates. A production phase is considered started only after a real run_phase/run_pipeline action is executed by the host and a live worker state exists.
16. Re-running `voice` invalidates `visuals` and every active downstream visual branch because Visuals/STP must re-split the actual narration and timing. If the user changes voice and wants to continue, use `rerun_phase` for voice or one `run_pipeline` from voice onward; the host will regenerate Visuals/STP before Footage or AI Visual according to the project's visual strategy.
17. For SEO/thumbnail work, prefer the saved channel profile linked to the current project. `seo` automatically refreshes and reads configured reference channels when available. Use `refresh_channel_profile` first only when the user explicitly asks for a fresh re-scan or wants to inspect the channel profile itself.
18. You can directly control an active Footage worker. Use `pause_footage`, `resume_footage`, or `stop_footage` when the user asks for those controls. If Footage is currently `running`/`queued` and the user asks to run it again, restart it, or find footage again from scratch, use `restart_footage` instead of `rerun_phase`; the host will stop the current worker and automatically launch a fresh tools-first Footage run after it exits.
19. CRITICAL ANTI-COLLISION RULE: When a project already has a phase actively `running` (e.g. `current_phase == "plan"` with `status == "running"`), NEVER write or overwrite that phase's output files (`research.md`, `script.md`, `visual_manifest.json`, `scenes.json`, etc.) yourself from chat! A dedicated background phase worker is already writing those files in `.producer/<phase>/events.jsonl`. If the user asks "làm đến đâu rồi" or "sao lâu thế", only inspect `CURRENT APP CONTEXT` (`live_progress`) or read the tail of `.producer/<phase>/events.jsonl` (read-only) and reply immediately with the real progress.
"""


def build_producer_chat_continuation_prompt(
    message: str,
    app_context: dict[str, Any],
    attachments: list[dict[str, Any]] | None = None,
    history: list[dict[str, Any]] | None = None,
    agents: list[dict[str, Any]] | None = None,
) -> str:
    images = [
        {"id": item.get("id"), "path": item.get("path"), "name": item.get("name")}
        for item in (attachments or [])
    ]
    recent = [
        {"role": item.get("role"), "content": str(item.get("content") or "")[-1000:]}
        for item in (history or [])[-6:]
    ]
    return (
        "Tiếp tục đúng session COFI DOCUMENTARY hiện tại với vai trò TỔNG ĐIỀU PHỐI (`orchestrator` — thực thi trực tiếp nhanh gọn trong chat, KHÔNG đứng hình, và CHỈ bật kiểm duyệt QA/QC khi thực hiện làm video). "
        "Khi người dùng đang bàn luận ý tưởng dự án mới hoặc tìm chủ đề, hãy tự do sáng tạo góc nhìn/văn phong/hook/dàn ý và trả về `fill_create_form` để giao diện Tạo dự án cập nhật trực tiếp mà không cần nút bấm. "
        "Khi người dùng đồng ý/chốt ý tưởng, tự động gọi `create_job` (kèm `start_plan: true`) để tạo dự án và đưa kịch bản sang màn hình Kịch bản. "
        "Khi người dùng yêu cầu sửa code/bug/UI hoặc chỉnh nhanh nội dung trong chat, thực hiện trực tiếp ngay (không qua kiểm duyệt QA). Chỉ khi chạy các bước sản xuất làm ra video (Kịch bản, Voice, Visuals, Footage, AI Visual, VOX, Edit, SEO, QC) mới kích hoạt pipeline hoặc ủy nhiệm kèm kiểm duyệt chất lượng (`verify_with_qa: true`). "
        "LƯU Ý CHỐNG XUNG ĐỘT: Nếu dự án đang có bước `running` (ví dụ `current_phase == 'plan'` đang chạy ngầm), TUYỆT ĐỐI KHÔNG tự ghi đè file đầu ra của bước đó (`script.md`, `visual_manifest.json`, v.v.) từ phiên chat; khi người dùng hỏi tiến độ, chỉ đọc `CURRENT APP CONTEXT` và trả lời ngay. "
        "Trả về đúng một JSON object với reply tiếng Việt và actions.\n\n"
        f"AVAILABLE SPECIALISTS\n{json.dumps(agents or [], ensure_ascii=False)}\n\n"
        f"CURRENT APP CONTEXT\n{json.dumps(app_context, ensure_ascii=False)}\n\n"
        f"RECENT APP CHAT\n{json.dumps(recent, ensure_ascii=False)}\n\n"
        f"USER MESSAGE\n{message}\n\n"
        f"ATTACHED IMAGES\n{json.dumps(images, ensure_ascii=False)}"
    )


def build_producer_fast_control_prompt(
    message: str,
    app_context: dict[str, Any],
    history: list[dict[str, Any]],
    jobs: list[dict[str, Any]],
) -> str:
    recent = [
        {"role": item.get("role"), "content": str(item.get("content") or "")[-1200:]}
        for item in history[-6:]
    ]
    projects = [
        {"id": item.get("id"), "title": item.get("title"), "status": item.get("status")}
        for item in jobs[:20]
    ]
    return f"""Handle one COFI DOCUMENTARY chat turn quickly. This is a routing pass, not a restriction on the full AI agent. Use only the supplied app state and recent conversation; do not use tools, browse, read files, or change source code in this pass. Return one JSON object with route, reply, and actions.

route="reply": A normal question or status request can be answered truthfully from the supplied state. Use actions=[].
route="action": The user wants a supported app operation. Return the smallest real action(s), then the host will execute them before displaying reply. Supported actions: select_job, navigate, run_phase, rerun_phase, run_pipeline, resume, approve_step, pause_footage, resume_footage, stop_footage, restart_footage, update_voice, start_remotion. Use exact IDs and phases from state. Do not say an operation has completed until the host verifies it.
route="agent": The user needs web research, open-ended analysis, brainstorming/pitching, editing scripts/outlines, source-code changes, file operations, creating or editing thumbnails/assets directly, a complex edit, or facts absent from state. The full-capability AI session will handle it with native tools. Use actions=[] and reply="". Never reject such requests here.

If the user asks whether a thumbnail has been redone, use thumbnail existence and update time in the app state; distinguish a newly saved file from a visually verified result. If the user asks to fix/remake thumbnail or packaging directly, route="agent" handles it with native tools. Resolve short follow-ups from recent conversation.

CURRENT APP STATE\n{json.dumps(app_context, ensure_ascii=False)}
PROJECTS\n{json.dumps(projects, ensure_ascii=False)}
RECENT CHAT\n{json.dumps(recent, ensure_ascii=False)}
USER MESSAGE\n{message}
"""


def build_producer_terminal_report_prompt(
    user_message: str,
    planned_reply: str,
    action_results: list[dict[str, Any]],
    failures: list[str],
    app_context: dict[str, Any],
) -> str:
    evidence = {
        "user_message": user_message,
        "planned_reply": planned_reply,
        "action_results": action_results,
        "failures": failures,
        "current_app_context": app_context,
    }
    return f"""Continue this same conversation as the same assistant. The host application has now finished all requested operations and is returning verified evidence to you.

VERIFIED EXECUTION EVIDENCE
{json.dumps(evidence, ensure_ascii=False, indent=2)}

Write the final user-facing response in natural Vietnamese, with the same intelligence, context, warmth, and clarity as your official desktop/web app. This is your own final response, not a status template.

Rules:
1. Do not output JSON, action objects, internal field names, or markdown fences.
2. State only what the evidence proves or what you directly performed and verified with native tools earlier in this same provider session. Never claim completion when an action failed, is merely queued, or has not produced its required result.
3. Explain clearly what actually happened, why it succeeded or failed, and what remains when that helps the user understand.
4. If work completed, summarize the concrete result and verification. If it failed, name the real cause in plain language and give the most useful next step.
5. Do not say you are still working: all host operations for this turn are terminal now.
6. Adapt naturally to the user's tone and context. Avoid canned headings or robotic stock phrases unless they genuinely improve clarity.
"""


GOAL_API_REFERENCE = """\
GET  /api/jobs                                   — danh sách dự án
POST /api/creative/draft                         — ĐỒNG BỘ TRỰC TIẾP BẢN NHÁP LÊN MÀN HÌNH TẠO DỰ ÁN (JSON: title, market, language, target_duration_minutes, visual_strategy, notes, creative_brief{narrative_angle,writing_style,hook_archetype,editing_archetypes,opening_hook,custom_rules}, outline[{chapter,title,summary,evidence_anchor,visual_note}])
POST /api/jobs                                   — tạo dự án mới (JSON: title, topic, market, language, target_duration_minutes, visual_strategy=full_ai|full_footage|hybrid|evidence_footage, ai_media_mode=image|video|mixed, notes, voice{voice_id,speed,mode}, creative_brief{narrative_angle,writing_style,hook_archetype,editing_archetypes,opening_hook,custom_rules}, outline[{chapter,title,summary,evidence_anchor,visual_note}], playbook_id, start_plan=true|false)
POST /api/jobs/from-radar                        — tạo dự án từ Radar (scan_id, video_id, ...)
GET  /api/jobs/{id}                              — trạng thái đầy đủ: status, current_phase, phases.{plan,voice,visuals,footage,ai_visual,edit,seo,qc}.status/error, creative_brief, outline
POST /api/jobs/{id}/approve-next                 — duyệt bước hiện tại và tự động chạy bước kế tiếp trong nhánh sản xuất
POST /api/jobs/{id}/pipeline/{from}/{through}    — chạy chuỗi phase liên tiếp (chỉ 1 job nền chạy một lúc)
POST /api/jobs/{id}/run/{phase} | /rerun/{phase} | /resume
POST /api/jobs/{id}/stop                         — dừng ngay lập tức phase/job đang chạy nền
GET  /api/jobs/{id}/logs/{phase}                 — log phase (đọc khi phase failed)
GET  /api/jobs/{id}/artifact/{name}              — đọc artifact (research.md, script.md, visual_manifest.json, outline.json, creative_brief.json, thumbnail_design.json, ...)
GET  /api/jobs/{id}/thumbnail-studio             — trạng thái Thumbnail Studio (4 phương án Fabric.js layer JSON, danh sách ảnh nền dự án, điểm CTR & Safe-Zone NanoThumbnail)
POST /api/jobs/{id}/thumbnail-studio/auto-design — tự động thiết kế bố cục Thumbnail (JSON: archetype=broadcast_left_heavy|bottom_cinematic|split_duality|evidence_spotlight|right_heavy_confrontation, badge_text, line_1, line_2)
POST /api/jobs/{id}/thumbnail-studio/generate-bg — gọi Google Labs Flow tạo ảnh nền sạch 16:9 không chữ (JSON: prompt)
POST /api/jobs/{id}/thumbnail-studio/design      — lưu chỉnh sửa layer JSON (`thumbnail_design.json`)
GET  /api/jobs/{id}/live-footage                 — tiến độ Footage; POST /footage/pause|resume|stop
PATCH /api/jobs/{id}/voice | /ai-visual-settings | /production-settings
PATCH /api/jobs/{id}/creative-brief              — cập nhật Góc nhìn (narrative_angle), Phong cách viết (writing_style), Hook (hook_archetype, opening_hook), Ngữ pháp dựng (editing_archetypes) và Quy tắc riêng (custom_rules) — chấp nhận mọi mô tả tự do
GET  /api/jobs/{id}/outline | PATCH /api/jobs/{id}/outline | POST /api/jobs/{id}/outline/generate — đọc / lưu / AI tạo dàn ý chương hồi (outline.json)
PUT  /api/jobs/{id}/script                       — lưu trực tiếp nội dung kịch bản (script.md)
GET  /api/playbooks | POST /api/playbooks | POST /api/jobs/{id}/extract-playbook — quản lý & trích xuất Channel Playbooks (DNA phong cách kênh)
GET  /api/jobs/{id}/remotion | /export-progress; POST /api/jobs/{id}/remotion/start
GET  /api/jobs/{id}/beats                        — danh mục rút gọn toàn bộ beats (`beats_index.json`, siêu nhẹ)
GET  /api/jobs/{id}/beats/{beat_id}              — đọc đúng 1 beat shard duy nhất + tóm tắt 2 beat lân cận (`0%` đọc lại cả dự án)
PATCH /api/jobs/{id}/beats/{beat_id}             — sửa phẫu thuật đúng 1 beat (tự đồng bộ `visual_manifest.json` & ghi `dirty_beat_ids` trong `state_ledger.json`)
POST /api/jobs/{id}/edit-chat                    — yêu cầu chỉnh bản dựng (message; tự động nạp đúng beat shard cần sửa dưới hiến chương Agent `edit` + `vox`)
GET  /api/agency/roster | /api/agency/search?q=... | /api/agency/agents/{id} — danh bạ & mã nguồn 15 Agent chuyên trách CofiDocumentary (`agents/<division>/<id>.md`)
POST /api/agency/delegate                        — giao tác vụ chuyên sâu cho 1 Agent chuyên trách độc lập (JSON: agent_id, task, job_id, verify_with_qa=true) có kiểm soát phân quyền & phản biện `evidence_qa`
POST /api/agency/delegate-squad                  — giao chuỗi 2–6 Agent bàn giao nối tiếp (JSON: agents:["research","script"], task, job_id, verify_with_qa=true) kèm Handoff Packet
GET  /api/jobs/{id}/nexus-ledger                 — sổ cái bàn giao Handoff, biên bản phản biện QA & nhật ký trace 15 Agent của dự án
GET  /api/voice/voices; GET /api/radar/today; POST /api/radar/scans/market
GET  /api/producer-chat/context?selected_job_id={id}  — ảnh chụp trạng thái app + live progress"""


COFI_PROPOSAL_CARD_GUIDE = """\
CƠ CHẾ ĐỒNG BỘ LINH HOẠT CHAT ↔ APP (KHÔNG CẦN NÚT BẤM):
1. KHI BÀN LUẬN Ý TƯỞNG TRƯỚC KHI TẠO DỰ ÁN:
   - Cùng bàn luận tự nhiên với người dùng về chủ đề, góc nhìn khai thác, phong cách viết, câu hook 30s đầu, ngữ pháp dựng phim và dàn ý chương hồi. Không bị giới hạn trong bất kỳ danh sách cố định nào.
   - Trong mỗi lượt đề xuất hoặc điều chỉnh ý tưởng (khi người dùng chưa chốt tạo dự án), hãy đồng bộ trực tiếp phương án lên màn hình Tạo dự án bên trái bằng cách gọi `POST /api/creative/draft` HOẶC đính kèm khối ```cofi-proposal ... ``` ở cuối câu trả lời:
```cofi-proposal
{
  "title": "Tiêu đề dự kiến",
  "market": "KR",
  "language": "ko",
  "target_duration_minutes": 15,
  "visual_strategy": "hybrid",
  "narrative_angle": "Góc nhìn khai thác tự do theo cuộc trò chuyện...",
  "writing_style": "Phong cách viết & giọng kể tự do...",
  "hook_archetype": "Cách mở màn 30s đầu...",
  "editing_archetypes": ["Ngữ pháp hình ảnh & dựng phim chủ đạo..."],
  "opening_hook": "Câu hook 30s đầu tiên cụ thể...",
  "custom_rules": "Ghi chú & quy tắc riêng...",
  "outline": [
    {"chapter": 1, "title": "Chương 1: ...", "summary": "...", "evidence_anchor": "...", "visual_note": "..."}
  ]
}
```
   - App sẽ TỰ ĐỘNG điền/cập nhật ngay lập tức lên giao diện Tạo dự án mà người dùng KHÔNG cần bấm bất kỳ nút nào.

2. KHI NGƯỜI DÙNG ĐỒNG Ý / CHỐT TRONG CHAT ("ok", "đồng ý", "chốt", "làm đi", "tạo dự án đi"):
   - LẬP TỨC gọi `POST /api/jobs` với toàn bộ thông tin đã bàn (`title`, `market`, `language`, `target_duration_minutes`, `visual_strategy`, `creative_brief`, `outline`, `notes`, `start_plan: true`) để tạo dự án mới và tự động chạy bước Kịch bản (`plan`).
   - Giao diện bên trái sẽ tự động chọn dự án vừa tạo và chuyển thẳng sang màn hình **Kịch bản**.

3. Ở BƯỚC KỊCH BẢN VÀ TẤT CẢ CÁC BƯỚC SAU (`Kịch bản`, `Voice`, `Visuals`, `Footage`, `AI Visual`, `Edit`, `SEO`, `QC`):
   - Mọi bước đều linh hoạt 2 chiều (người dùng có thể duyệt/sửa/tạo lại thủ công trên giao diện HOẶC yêu cầu qua Chat):
     * Ủy nhiệm & sửa qua Chat: Gọi `POST /api/agency/delegate`, `POST /api/agency/delegate-squad`, `PATCH /api/jobs/<id>/creative-brief`, `PATCH /api/jobs/<id>/outline`, `PUT /api/jobs/<id>/script`, hoặc `POST /api/jobs/<id>/edit-chat` — giao diện bên trái sẽ tự cập nhật tức thì.
     * Tạo lại qua Chat: Gọi `POST /api/jobs/<id>/rerun/<phase>`.
     * Duyệt & qua bước tiếp theo bằng Chat: Khi người dùng nhắn "duyệt", "ok chạy bước tiếp", "tiếp tục", hãy gọi `POST /api/jobs/<id>/approve-next` (hoặc `POST /api/jobs/<id>/run/<next_phase>`)."""


def build_producer_goal_prompt(
    message: str,
    app_context: dict[str, Any],
    *,
    api_base_url: str,
    first_turn: bool,
    attachments: list[dict[str, Any]] | None = None,
    history: list[dict[str, Any]] | None = None,
    goal_mode: bool = True,
    explicit_agent_id: str | None = None,
    answer_first: bool = False,
    has_handoff: bool = False,
) -> str:
    """Body sent to the persistent Antigravity session (both Agent mode and /goal mode).

    Enforces strict 2-mode separation:
    1. `production_pipeline`: active video job stage execution / troubleshooting -> injects deterministic
       `build_production_pipeline_memory_block` + `build_surgical_work_locator`, NEVER injects app codebase files.
    2. `app_code_fix`: fixing app UI/backend code -> injects `APP_ARCHITECTURE_MEMORY_TREE` + surgical file/line slices.
    """
    base = str(api_base_url or "http://127.0.0.1:8878").rstrip("/")
    images = [str(item.get("path")) for item in (attachments or []) if item.get("path")]
    raw_ctx = dict(app_context or {})
    tab_name = str(raw_ctx.get("app_tab") or "").strip().lower()
    if raw_ctx.get("selected_job") and tab_name not in {"radar", "create", "channels"}:
        # Strip heavy static channel_profiles / playbooks on ALL turns (including Turn-0 after /compact or /new)
        # whenever a project is open so Turn-0 stays lightweight and fast.
        compact_ctx = {
            "app_tab": raw_ctx.get("app_tab"),
            "selected_job": raw_ctx.get("selected_job"),
            "live_progress": raw_ctx.get("live_progress"),
        }
        snapshot = json.dumps(compact_ctx, ensure_ascii=False)
    else:
        ordered_ctx = {
            "app_tab": raw_ctx.get("app_tab"),
            "selected_job": raw_ctx.get("selected_job"),
            "live_progress": raw_ctx.get("live_progress"),
            **{k: v for k, v in raw_ctx.items() if k not in {"app_tab", "selected_job", "live_progress"}},
        }
        snapshot = json.dumps(ordered_ctx, ensure_ascii=False)
    if len(snapshot) > 8_500:
        snapshot = snapshot[:8_500] + "…"

    repo_root_dir = Path(__file__).resolve().parent.parent
    sel_job_dict = raw_ctx.get("selected_job") if isinstance(raw_ctx.get("selected_job"), dict) else {}
    sel_job_id = str(sel_job_dict.get("id") or "").strip()
    sel_ws_str = str(sel_job_dict.get("workspace") or "").strip()
    if not sel_ws_str and sel_job_id:
        cand_ws = repo_root_dir / "workspaces" / sel_job_id
        if cand_ws.is_dir():
            sel_ws_str = str(cand_ws)

    from .agent_manager import AgentManager
    from .nexus_coordinator import NexusCoordinator
    from .workspace_ledger import (
        build_codebase_surgical_locator,
        build_production_pipeline_memory_block,
        build_surgical_work_locator,
        classify_producer_chat_intent,
    )

    chat_intent = classify_producer_chat_intent(
        message,
        history,
        selected_job_id=sel_job_id or None,
        explicit_agent_id=explicit_agent_id,
    )

    def _format_substantive_history(
        items: list[dict[str, Any]] | None,
        *,
        limit: int = 6,
        max_item_chars: int = 1200,
    ) -> list[dict[str, str]]:
        cleaned: list[dict[str, str]] = []
        for item in items or []:
            if not isinstance(item, dict):
                continue
            role = str(item.get("role") or "user")
            raw_content = str(item.get("content") or "").strip()
            low = raw_content.lower()
            if not raw_content or low in {"/compact", "/nen", "/new", "/reset"}:
                continue
            if raw_content.startswith("Đã nén ngữ cảnh (`/compact`)") or raw_content.startswith("Đã khởi tạo phiên hội thoại"):
                continue
            steps = item.get("steps") if isinstance(item.get("steps"), list) else []
            if raw_content.startswith("Đã dừng lượt làm việc"):
                step_targets: list[str] = []
                for st in steps[-10:]:
                    if isinstance(st, dict) and str(st.get("step_type") or "") not in {"agent_response", "thinking", ""}:
                        tname = str(st.get("tool_name") or st.get("step_type") or "").strip()
                        targ = str(st.get("target") or st.get("tool_summary") or "").strip()
                        label = f"{tname}: {targ}" if (tname and targ) else (targ or tname)
                        if label and label not in {"run_command", "read_file", "edit_file", "write_file"}:
                            if not step_targets or step_targets[-1] != label:
                                step_targets.append(label[:150])
                if not step_targets and "Các thao tác đã hoàn tất trên đĩa" not in raw_content:
                    # Skip empty Stop stubs so repeated user cancellations never evict real context
                    continue
                if step_targets and "Các thao tác đã hoàn tất trên đĩa" not in raw_content:
                    raw_content += " [Các bước đã chạy trước khi dừng: " + "; ".join(step_targets[-5:]) + "]"
            if cleaned and cleaned[-1]["role"] == role and cleaned[-1]["content"] == raw_content[-max_item_chars:]:
                continue
            cleaned.append({"role": role, "content": raw_content[-max_item_chars:]})
        return cleaned[-limit:]

    parts: list[str] = []
    am = AgentManager()
    coord = NexusCoordinator(am)
    if first_turn:
        orchestrator_charter = coord.build_specialist_soul_header(
            "orchestrator",
            "In-App Master Production Orchestrator & 15-Department Dispatcher",
        )
        by_div: dict[str, list[str]] = {}
        for item in am.list_agents():
            by_div.setdefault(str(item["division"]), []).append(f'"{item["id"]}" ({item["name"]})')
        roster_lines = "\n".join(f"  * {div}: {', '.join(members)}" for div, members in by_div.items())
        studio_roster_guide = (
            f"{orchestrator_charter}\n"
            "HIẾN CHƯƠNG TỔNG ĐIỀU PHỐI COFIDOCUMENTARY (`orchestrator` — 15 Agent / 4 Phòng ban · `/api/agency/delegate` & `/api/agency/delegate-squad`):\n"
            f"{roster_lines}\n"
            "- **LUẬT PHÂN TÁCH CỨNG 2 CHẾ ĐỘ (BẮT BUỘC TUÂN THỦ 100%)**:\n"
            "  1. **CHẾ ĐỘ 1 — THỰC THI & XỬ LÝ LỖI KHÂU SẢN XUẤT VIDEO (`plan -> voice -> visuals -> footage/ai_visual/vox -> edit -> seo -> qc`)**:\n"
            "     - Đọc ngay khối `🎬 BỘ NHỚ LUỒNG SẢN XUẤT & CHẨN ĐOÁN TỨC THÌ` + `selected_job` bên dưới (đã nạp sẵn `state_ledger.json`, trạng thái từng khâu, dòng lỗi thật trong `.render_cache/logs/*.log` & `logs/*.log`, trạng thái Remotion Preview và đúng file `<ThisJob>*.tsx` của dự án đang mở).\n"
            "     - **TUYỆT ĐỐI CẤM** đọc hay quét mã nguồn app (`documentary/*.py`, `services/*.py`, `static/*.js`, `CofiRemotion/scripts/*`) và **CẤM** mở nhầm thư mục/component của dự án khác khi đang kiểm tra hay xử lý lỗi khâu làm video!\n"
            "  2. **CHẾ ĐỘ 2 — SỬA CODE / FIX TÍNH NĂNG APP (`dev` / `debug`)**:\n"
            "     - Chỉ khi người dùng yêu cầu sửa code/UI/logic của app mới đọc mã nguồn hệ thống: dùng ngay tọa độ `StartLine..EndLine` trong khối `🛠️ BẢN ĐỒ ĐỊNH VỊ MÃ NGUỒN PHẪU THUẬT`; nếu cần tìm thêm hàm/nút gọi chưa có sẵn thì gọi MCP `trail` (`trail_find_code`, `trail_file_api`, `trail_trace_calls` cho CofiDocumentary) hoặc `trail_remotion` (cho CofiRemotion) trước tiên — `0%` đọc nguyên file lớn hay quét mù 500+ file.\n"
            "- **PHẪU THUẬT ĐÚNG BEAT (`SURGICAL BEAT PATCH`) & CẤM ĐỌC TRÀN**: Sửa câu/cảnh nào chỉ đọc & sửa đúng dòng `script.md` hoặc mảnh `beats/<beat_id>.json` đã chỉ sẵn (hoặc `GET/PATCH /api/jobs/{id}/beats/{beat_id}` / `POST /api/jobs/{id}/edit-chat`). Cấm gọi `invoke_subagent`.\n"
            "- **KIỂM ĐỊNH ĐÚNG TUYẾN**: Tác vụ ngoài dây chuyền 8 bước sản xuất video đặt `verify_with_qa=false`; dây chuyền sản xuất video áp dụng `@evidence_qa` + `@qc` (`verify_with_qa=true`, media AI ghi nhãn tái dựng, tư liệu gốc soi mắt thật).\n\n"
        )
        proposal_block = (
            COFI_PROPOSAL_CARD_GUIDE + "\n\n"
            if (not sel_job_id or tab_name in {"radar", "create"})
            else "- Khi bàn ý tưởng dự án mới (chưa mở job): đồng bộ qua `POST /api/creative/draft` hoặc khối ```cofi-proposal```; khi chốt mới gọi `POST /api/jobs`.\n"
        )
        hist_limit = 2 if has_handoff else 5
        recent = _format_substantive_history(history, limit=hist_limit, max_item_chars=900 if has_handoff else 1300)
        mode_banner = (
            "PHIÊN ANTIGRAVITY LIÊN TỤC (`/goal`)"
            if goal_mode
            else "PHIÊN CHAT TƯƠNG TÁC LIÊN TỤC"
        )
        parts.append(
            studio_roster_guide
            + f"CHẾ ĐỘ ĐIỀU PHỐI ({mode_banner} — CHẾ ĐỘ LƯỢT NÀY: `{chat_intent.upper()}`):\n"
            "- 0-TOOL TRẢ LỜI NGAY CHO CÂU HỎI TIẾN ĐỘ / NGUYÊN NHÂN LỖI: Đọc trực tiếp `🎬 BỘ NHỚ LUỒNG SẢN XUẤT` và `selected_job` bên dưới để trả lời ngay bằng tiếng Việt ngắn gọn (tối đa 0–1 lần đọc file/log cụ thể nếu thật sự cần).\n"
            "- **LUẬT FIRE-AND-RETURN (CẤM VÒNG LẶP CHỜ ĐỐT TOKEN)**: Khi khởi chạy worker nền (`POST /api/jobs`, `/run/{phase}`, `/rerun/{phase}`, `/pipeline/{from}/{through}`, `/approve-next`), xác nhận đã khởi chạy và kết thúc lượt ngay lập tức — **TUYỆT ĐỐI CẤM** dùng `wait`/`schedule` để kiểm tra lại trạng thái HTTP định kỳ!\n"
            "- QUY TẮC UTF-8 TRÊN WINDOWS: Luôn gọi HTTP POST/PATCH/PUT có tiếng Việt / tiếng Hàn bằng `python -X utf8 -c` với `.encode('utf-8')` (không truyền trực tiếp chuỗi Unicode vào `Invoke-RestMethod -Body`).\n"
            f"- HTTP API cục bộ: {base} (không trả JSON envelope cho người dùng).\n"
            "- API chính:\n" + GOAL_API_REFERENCE + "\n\n"
            + proposal_block
            + (
                f"LỊCH SỬ CHAT MỚI NHẤT\n{json.dumps(recent, ensure_ascii=False)}\n"
                if recent
                else ""
            )
        )
    else:
        recent_followup = _format_substantive_history(history, limit=4, max_item_chars=1100)
        mode_label = (
            f"MODE={chat_intent.upper()} | FIRE-AND-RETURN (0-tool trả lời tiến độ/lỗi từ bộ nhớ dự án; "
            "cấm đọc code app khi xử lý khâu sản xuất video; cấm lặp kiểm tra HTTP chờ phase nền)"
        )
        parts.append(f"(Tiếp tục phiên Antigravity COFI DOCUMENTARY [{mode_label}]. API app: {base}, dừng job: POST {base}/api/jobs/<id>/stop)\n")
        if recent_followup:
            parts.append(f"LỊCH SỬ CHAT GẦN ĐÂY TRONG APP (đồng bộ sẵn — KHÔNG dùng tool đọc lại producer_chat_history.jsonl hay transcript.jsonl)\n{json.dumps(recent_followup, ensure_ascii=False)}\n")

    parts.append(f"TRẠNG THÁI APP HIỆN TẠI (đã đồng bộ trực tiếp — dùng ngay, KHÔNG gọi tool quét lại app/workspaces)\n{snapshot}\n")

    if chat_intent == "production_pipeline":
        if sel_ws_str and Path(sel_ws_str).is_dir():
            try:
                prod_mem = build_production_pipeline_memory_block(
                    sel_ws_str,
                    sel_job_dict,
                    sel_job_dict.get("live_diagnostics") if isinstance(sel_job_dict.get("live_diagnostics"), dict) else None,
                )
                if prod_mem:
                    parts.append(prod_mem + "\n")
            except Exception:
                pass
            try:
                surgical_locator = build_surgical_work_locator(sel_ws_str, message, history)
                if surgical_locator:
                    parts.append(surgical_locator + "\n")
            except Exception:
                pass
    else:
        try:
            code_locator = build_codebase_surgical_locator(
                repo_root_dir,
                message,
                history,
                always_include_recent_code=True,
                include_architecture_tree=True,
            )
            if code_locator:
                parts.append(code_locator + "\n")
        except Exception:
            pass
        if sel_ws_str and Path(sel_ws_str).is_dir():
            try:
                surgical_locator = build_surgical_work_locator(sel_ws_str, message, history)
                if surgical_locator:
                    parts.append(surgical_locator + "\n")
            except Exception:
                pass

    if explicit_agent_id:
        try:
            exp_charter = coord.build_specialist_soul_header(explicit_agent_id, "Explicit User Specialist Assignment")
            parts.append(
                f"CHỈ THỊ PHÂN QUYỀN TRỰC TIẾP TỪ NGƯỜI DÙNG: Người dùng chỉ định đích danh Agent `{explicit_agent_id}`. "
                f"BẮT BUỘC ủy nhiệm cho Agent `{explicit_agent_id}` qua `POST {base}/api/agency/delegate` với `agent_id='{explicit_agent_id}'` theo đúng hiến chương:\n{exp_charter}"
            )
        except Exception:
            pass
    if images:
        parts.append("ẢNH ĐÍNH KÈM (mở và xem trực tiếp trước khi quyết định):\n" + "\n".join(f"- {p}" for p in images) + "\n")
    parts.append(f"TIN NHẮN CỦA NGƯỜI DÙNG\n{message}")
    if answer_first:
        parts.append(
            "\n⚡ CHỈ THỊ ƯU TIÊN TUYỆT ĐỐI CHO LƯỢT NÀY (TRẢ LỜI NGAY LẬP TỨC — CẤM QUÉT MÙ):\n"
            "- Người dùng đang đặt câu hỏi hoặc yêu cầu **TRẢ LỜI / BÁO CÁO RÕ ĐANG LÀM ĐẾN ĐÂU & VÌ SAO LỖI TRƯỚC KHI BẮT TAY VÀO LÀM**.\n"
            "- Toàn bộ thông tin dự án (`🎬 BỘ NHỚ LUỒNG SẢN XUẤT & CHẨN ĐOÁN TỨC THÌ`, `selected_job`, `live_diagnostics`, `LỊCH SỬ CHAT`) đã nạp sẵn ngay phía trên.\n"
            "- **TUYỆT ĐỐI CẤM** quét `workspaces/`, đọc mã nguồn `documentary/*.py` / `static/*.js`, đọc `producer_chat_history.jsonl`, đọc `transcript.jsonl`, hay gọi `trail ask`!\n"
            "- Nếu có ảnh chụp màn hình đính kèm, chỉ xem ảnh đính kèm (nếu cần) + đối chiếu ngay với `live_diagnostics` đã nạp sẵn, rồi **TRẢ LỜI NGAY LẬP TỨC** bằng tiếng Việt ngắn gọn, chỉ đích danh file/cảnh đang lỗi và **DỪNG LẠI** chờ lệnh tiếp theo!"
        )
    return "\n".join(parts)


def build_goal_resume_prompt(reason: str) -> str:
    return (
        "Phiên goal vừa bị gián đoạn bởi lỗi dịch vụ/tiến trình: "
        f"{str(reason or '').strip()[:500]}\n"
        "Tiếp tục đúng mục tiêu đang dở từ trạng thái thực tế hiện tại (kiểm tra lại app trước khi làm tiếp). "
        "Không làm lại những việc đã xác minh là xong."
    )


def build_footage_eye_agent_prompt(
    job: dict[str, Any],
    workspace: Path,
    remotion_dir: Path,
    beats: list[dict[str, Any]],
    *,
    failed_report: dict[str, Any] | None = None,
    act_label: str = "",
    worker_index: int = 0,
    total_workers: int = 1,
    completed_beat_ids: list[str] | None = None,
    existing_sources: list[str] | None = None,
) -> str:
    """Build the standalone prompt for the dedicated @footage AI Agent (Eye-Verified Archival Footage Hunter)."""
    from .nexus_coordinator import NexusCoordinator

    coord = NexusCoordinator()
    footage_charter = coord.build_specialist_soul_header(
        "footage",
        "Dedicated Eye-Verified Archival Footage Hunting, 100px Grid Cropping & 1-to-1 Voice Semantic Matching Stage",
    )
    job_id = str(job.get("id") or workspace.name).strip()
    done_set = {str(x).strip() for x in (completed_beat_ids or []) if str(x).strip()}
    compact_beats = [
        {
            "beat_id": str(b.get("id") or b.get("beat_id") or ""),
            "act": str(b.get("act") or b.get("chapter_id") or ""),
            "duration_sec": b.get("duration_sec") or b.get("target_duration_sec"),
            "voice_text": b.get("voice_text") or b.get("narration_text"),
            "visual_type": b.get("visual_type"),
            "source_priority": b.get("source_priority"),
            "visual_description": str(b.get("visual_description") or "")[:240],
            "footage_search_queries": b.get("footage_search_queries") or [],
        }
        for b in beats
        if isinstance(b, dict) and str(b.get("id") or b.get("beat_id") or "") not in done_set
    ]
    is_rework_scope = str(act_label or "").strip().upper().startswith("REWORK")
    rework_section = ""
    failures_list = (failed_report or {}).get("failures") or (failed_report or {}).get("failed_assets") or []
    if failures_list:
        rework_section = (
            "\n\n🚨 MANDATORY EYE-VERIFICATION REWORK — FIX FAILED FOOTAGE CLIPS:\n"
            f"{json.dumps(failures_list[:60], ensure_ascii=False, indent=2)}\n"
            f"(Total failures: {len(failures_list)})\n"
            "You MUST re-cut or replace ONLY the failed/flagged beats assigned below using a genuinely matching source clip, "
            "non-stair-step eye-verified timestamp (`--start-offset`, `> 30s` apart on shared sources, shifting away from any `GLOBAL_FOOTAGE` overused/stair-stepped source), "
            "calibrated `--crop-mode`, `--force`, and unique `--observed-content` (NEVER prepend keyword-stuffing prefixes or split one TV broadcast into multiple source filenames)."
        )
    qa_ticket_directive = load_phase_qa_rejection_directive(workspace, "edit")
    if qa_ticket_directive:
        rework_section = f"{rework_section}\n{qa_ticket_directive}"

    scope_banner = ""
    if act_label or total_workers > 1:
        scope_tag = act_label or f"WORKER_{worker_index + 1}"
        rework_note = " (Vòng sửa lỗi tập trung — CHỈ xử lý các beat lỗi/thiếu trong danh sách dưới đây, không quét lại beat đã đạt)" if is_rework_scope else ""
        scope_banner = (
            f"\n- **PHẠM VI WORKER SONG SONG (`{scope_tag}`, Worker {worker_index + 1}/{max(1, total_workers)})**: "
            f"Bạn CHỈ xử lý đúng `{len(compact_beats)}` beat `REAL_FTG`/tư liệu được giao trong danh sách bên dưới (đã tự động lọc bỏ `{len(done_set)}` beat hoàn tất và toàn bộ beat `VOX`/`CINEMA_TEXT`/`AI_4D`){rework_note}. "
            "TUYỆT ĐỐI KHÔNG cắt đè sang beat của Worker/Hồi khác, và phân bố mốc `--start-offset` lệch nhau trên các nguồn dùng chung để `dHash >= 14`."
        )
    sources_hint = ""
    if existing_sources:
        sources_hint = (
            f"\n- **NGUỒN SẠCH ĐÃ TẢI SẴN TRÊN ĐĨA (ưu tiên probe/dùng trước, không tải lại):** "
            + ", ".join(existing_sources[:20])
        )

    if is_creative_audio_drama_job(job) or str((_resolve_job_editing_dna(job) or {}).get("footage_mode") or "").strip().lower() == "atmospheric_broll":
        return f"""{footage_charter}

BẠN LÀ CHUYÊN GIA AI AGENT `@footage` TRONG CHẾ ĐỘ LIGHTWEIGHT ATMOSPHERIC B-ROLL (`~15%` B-ROLL KHÔNG KHÍ 4K SẠCH CHO K-AUDIO DRAMA ĐÊM KHUYA — `0%` BẢN TIN THỜI SỰ, `0%` MẶT NGƯỜI LẠ):
- Job ID: `{job_id}` | Workspace: `{workspace}` | Remotion Dir: `{remotion_dir}`
- Thư mục nguồn B-roll 4K sạch: `{workspace / "media" / "footage" / "sources"}`
- Thư mục bảng soi mắt & kiểm duyệt: `{workspace / "media" / "footage" / "probes"}`
- Hồ sơ kênh đang chạy `content_mode = "creative_audio_drama"` (`footage_mode = "atmospheric_broll"`): `@ai_visual` đã tạo xong `~80%` cảnh nhân vật điện ảnh 35mm trong `media/ai/`. Bạn CHỈ tuyển chọn và cắt lọc cho đúng `{len(compact_beats)}` beat `sourced_video` (`~15%` nhịp chuyển cảnh/không khí): mưa đêm bên hiên cửa gỗ Hanok, lá thu rơi trên sân đá, bàn tay rót trà gốm ấm áp, tơ lụa/chỉ thêu truyền thống Hàn Quốc, phố đêm Seoul trầm ấm, phím đàn piano/dây đàn cello ấm dịu.

QUY TRÌNH BẮT BUỘC BẰNG MẮT THẬT (`ZERO NEWS / ZERO STRANGER FACES / ZERO STAIR-STEP`):
1. **Thu thập đa dạng nguồn 4K Atmospheric B-Roll sạch (`>= 13` nguồn video độc lập trong `{workspace / "media" / "footage" / "sources"}`, tối đa `<= 5` clip mỗi nguồn)**:
   - Dùng `yt-dlp` tải các nguồn video không khí 4K Hàn Quốc / truyền thống (Hanok rain eaves, Korean tea ceremony, silk hanbok craft close-up, autumn courtyard leaves, warm night street lantern, solo felt piano / cello hands) vào `{workspace / "media" / "footage" / "sources"}`.
   - **TUYỆT ĐỐI CẤM** tải bản tin thời sự TV, phóng sự tội phạm, vlog thuyết minh hay cảnh có khuôn mặt người lạ cận cảnh (làm gãy Character Sheet). Mỗi nguồn chỉ lấy tối đa `<= 5` đoạn ở các mốc thời gian cách xa nhau (`> 25s`, không cắt tịnh tiến / không cộng bậc thang đều nhau).
2. **Tạo bảng `STORYBOARD_<id>.jpg` & `GRID_<id>.jpg` (`100px`) và SOI MẮT (`read_file`)**:
   - Chạy: `python -m documentary.edit_footage_fetcher --workspace "{workspace}" --job-id "{job_id}" --probe-storyboard "<đường_dẫn_nguồn>" --probe-id "<mã_nguồn>"`
   - Gọi `read_file` xem `STORYBOARD_<mã_nguồn>.jpg` và `GRID_<mã_nguồn>.jpg` để chọn đúng giây `--start-offset` mượt, không chuyển cảnh giữa chừng (`0` internal hard cut), ánh sáng ấm dịu (`Highlight Luma <= 215`), và lập `--crop-mode "crop=W:H:X:Y"` cắt sạch 100% mọi logo/watermark/chữ góc màn hình.
3. **Cắt từng beat bằng `edit_footage_fetcher` với `--observed-content` độc nhất mô tả cảnh vật mắt thấy**:
   - Chạy: `python -m documentary.edit_footage_fetcher --workspace "{workspace}" --job-id "{job_id}" --remotion-dir "{remotion_dir}" --beat-id "<BEAT_ID>" --url "<đường_dẫn_nguồn>" --start-offset <GIÂY_THẬT> --duration <THỜI_LƯỢNG_BEAT> --crop-mode "crop=W:H:X:Y" --observed-content "<Mô tả cụ thể cảnh không khí 4K mắt thấy trong frame, không copy nguyên văn câu thoại, không lặp tiền tố>" --force`
4. **Xuất bảng `VERIFY_FTG_CLIPS_*.jpg` và kiểm tra mắt (`read_file`)**:
   - Chạy: `python -m documentary.edit_footage_fetcher --workspace "{workspace}" --job-id "{job_id}" --remotion-dir "{remotion_dir}" --build-verify-sheets`
   - Gọi `read_file` kiểm tra trực tiếp `VERIFY_FTG_CLIPS_1.jpg` (và các trang tiếp theo) trong `{workspace / "media" / "footage" / "probes"}`, thay ngay bất kỳ clip nào dính mặt người lạ, chữ, logo hoặc giật cắt.
5. **Chỉ hoàn tất khi chạy kiểm định `footage_hygiene_report.json` đạt `status: "PASSED"` (`failures: []`) cho đủ `{len(compact_beats)}` beat `sourced_video`**.{rework_section}

DANH SÁCH `{len(compact_beats)}` BEATS ATMOSPHERIC B-ROLL CẦN PHỤ TRÁCH:
{json.dumps(compact_beats, ensure_ascii=False, indent=2)}
"""
    final_verify_step = (
        "4. **Duyệt bảng `BATCH_VERIFY_*.jpg` theo lô (Worker song song — KHÔNG tự chạy `--build-verify-sheets` toàn tập; Coordinator sẽ gom bảng `VERIFY_FTG_CLIPS_*.jpg` sau khi các Worker hoàn tất)**."
        if total_workers > 1
        else (
            "4. **Xuất bảng kiểm duyệt `VERIFY_FTG_CLIPS_*.jpg` và SOI BẰNG MẮT (`read_file`)**:\n"
            f'   - Sau khi cắt xong toàn bộ các beat tư liệu thật, chạy lệnh:\n     `python -m documentary.edit_footage_fetcher --workspace "{workspace}" --job-id "{job_id}" --remotion-dir "{remotion_dir}" --build-verify-sheets`\n'
            f'   - **BẮT BUỘC gọi `read_file`** mở xem trực tiếp các file `VERIFY_FTG_CLIPS_*.jpg` trong `{workspace / "media" / "footage" / "probes"}`.'
        )
    )
    return f"""{footage_charter}

BẠN LÀ CHUYÊN GIA AI AGENT `@footage` (`Archival Footage & B-Roll Hunter`).
Bước 4 cũ (Footage tools tự động) đã bị XÓA VĨNH VIỄN khỏi ứng dụng. Toàn bộ nhiệm vụ tìm kiếm nguồn video tư liệu thật, soi bảng lưới `STORYBOARD_<id>.jpg` + `GRID_<id>.jpg` bằng mắt thật (`read_file`), cắt từng clip khớp 1-1 với câu thoại (`voice_text`), crop sạch 100% logo/chữ chạy/MC trường quay và kiểm duyệt trên bảng Contact Sheet thuộc toàn quyền của bạn trước khi bàn giao cho `@edit`.

THÔNG TIN DỰ ÁN:
- Job ID: `{job_id}`
- Workspace: `{workspace}`
- Remotion Dir: `{remotion_dir}`
- Thư mục nguồn tư liệu thật: `{workspace / "media" / "footage" / "sources"}`
- Thư mục bảng soi mắt & kiểm duyệt: `{workspace / "media" / "footage" / "probes"}`{scope_banner}{sources_hint}

QUY TRÌNH BẮT BUỘC 5 BƯỚC BẰNG MẮT THẬT — CẮT LÔ 10–15 BEAT SIÊU TỐC (`ZERO AUTO-CUT / ZERO STAIR-STEP / ZERO BLIND SPLICING / BATCH CONTACT SHEET`):
1. **Kiểm tra & Thu thập cuốn chiếu theo lô nhỏ 3–4 nguồn (`height<=720` — CẤM ôm tải 15–30 video 1080p cùng lúc)**:
   - Trước tiên kiểm tra các file nguồn ĐÃ CÓ sẵn trong `{workspace / "media" / "footage" / "sources"}` và bảng probe trong `{workspace / "media" / "edit_footage" / "probes"}` / `{workspace / "media" / "footage" / "probes"}`. Nếu đã có nguồn sạch trên đĩa, hãy probe và **cắt ngay các beat khớp nghĩa trước**; chỉ tải bổ sung khi thật sự thiếu cảnh mới theo lô nhỏ **tối đa 3–4 nguồn/lần** với định dạng nhẹ `720p` (`yt-dlp -f "bv*[height<=720][ext=mp4]+ba/b[height<=720][ext=mp4]/b[height<=720]" --socket-timeout 20 --retries 2 --max-filesize 250M`, CẤM ghép >4 URL vào 1 vòng lặp tải nối tiếp và bỏ qua file `.part` đứng yên >60s).
   - **Lọc bỏ nguồn rác ngay khi soi `STORYBOARD_<id>.jpg`**: Xóa ngay (`Remove-Item`) các video có người dẫn chương trình/MC trường quay/MC hoạt hình đứng bục (`cartoon host`), avatar chủ kênh ở góc, video bọc khung trình duyệt giả hoặc hộp PiP dọc bé lọt thỏm trong viền đen (`w < 960` hoặc `h < 540`), video slideshow ảnh tĩnh dán lên nền phong cảnh (`Motion Energy = 0`), hoặc vlogger/YouTuber kể chuyện lạc vụ án.
   - Tuyệt đối CẤM đọc mã nguồn hệ thống (`documentary/*.py`); chỉ dùng các lệnh CLI `documentary.edit_footage_fetcher` đã ghi sẵn bên dưới.
   - Phân bổ các beat `REAL_FTG` trải đều trên nhiều nguồn video sạch, TUYỆT ĐỐI CẤM lấy độc quyền từ 1 nguồn duy nhất (`single_source_monopoly_detected`) và TUYỆT ĐỐI CẤM cắt bậc thang tự động kiểu cộng đều `+14.5s` (`stair_step_auto_offset_detected`).

2. **Trích xuất bảng `STORYBOARD_<id>.jpg` & Lưới tọa độ `GRID_<id>.jpg` (`100px`) — SOI 1 LẦN CHO MỖI NGUỒN (`read_file`)**:
   - Chạy lệnh tạo bảng storyboard và lưới tọa độ cho từng video nguồn (bỏ qua nếu `STORYBOARD_<id>.jpg` và `GRID_<id>.jpg` đã tồn tại):
     `python -m documentary.edit_footage_fetcher --workspace "{workspace}" --job-id "{job_id}" --probe-storyboard "<đường_dẫn_hoặc_URL_nguồn>" --probe-id "<mã_nguồn>"`
   - **BẮT BUỘC mở xem trực tiếp bằng `read_file`** trên CẢ `STORYBOARD_<mã_nguồn>.jpg` VÀ `GRID_<mã_nguồn>.jpg` (chỉ 1 lần/nguồn) để:
     * Lập bản đồ mốc giây `--start-offset` sạch khớp 100% nghĩa từng câu thoại (`voice_text`), không dính MC trường quay/MC hoạt hình/avatar, không dính bảng chữ tiêu đề lớn giữa màn hình, không dính frame đen (`YAVG < 16`).
     * Đọc tọa độ pixel `(X, Y, W, H)` trên `GRID_<mã_nguồn>.jpg` để chốt công thức `--crop-mode "crop=W:H:X:Y"` (`W >= 960, H >= 540`) cắt sạch 100% logo đài/kênh (`CCTV`, `bilibili`, `@YouTube...`), thanh viền trình duyệt giả, chữ chạy đáy màn hình và phụ đề ngoại ngữ cháy cứng.

3. **Cắt THEO LÔ 10–15 BEAT bằng `--batch-manifest` & SO MẮT 1 LƯỢT TRÊN `BATCH_VERIFY_*.jpg` (`TIẾT KIỆM 90% TOKEN`)**:
   - Gom **10–15 beat** đã chọn được `url`, `start_offset` (mắt chọn), `duration`, `crop_mode` (từ `GRID`), và `observed_content` (mô tả cảnh thật mắt thấy riêng cho từng câu, >= 10 ký tự, CẤM dùng câu mẫu lặp lại) vào 1 file JSON (ví dụ `{workspace / "media" / "footage" / "probes" / ("batch_" + (act_label or "01") + "_1.json")}`) dạng mảng:
     `[{{"beat_id": "B010-V01", "url": "...mp4", "start_offset": 124.5, "duration": 6.5, "crop_mode": "crop=1140:640:60:40", "observed_content": "Cảnh thật trong clip khớp câu thoại...", "query": "..."}}]`
   - Chạy **1 lệnh duy nhất** cắt song song cả lô và xuất 1 tấm Contact Sheet gộp:
     `python -m documentary.edit_footage_fetcher --workspace "{workspace}" --job-id "{job_id}" --remotion-dir "{remotion_dir}" --batch-manifest "<đường_dẫn_file_json_lô>" --batch-sheet-out "{workspace / "media" / "footage" / "probes" / ("BATCH_VERIFY_" + (act_label or "L01") + "_1.jpg")}"`
   - **BẮT BUỘC gọi `read_file` 1 lần** xem tấm `BATCH_VERIFY_*.jpg` vừa tạo: đối chiếu cả 10–15 dòng `3 khung hình (15%-50%-85%)` với `Voice` bên cạnh; nếu beat nào bị lệch nghĩa, tối đen hoặc còn dính logo/chữ/MC thì chỉ cắt lại đúng beat lẻ đó (`--beat-id <BEAT_ID> ... --force`).
   - Những câu thoại trừu tượng/nội tâm/tổng kết không có tư liệu thật tương ứng thì bỏ qua để chuyển sang `VOX` hoặc `AI_VISUAL` theo đúng chiến lược dự án, tuyệt đối không nhét cảnh lạc quẻ vào câu thoại!

{final_verify_step}
   - Đối chiếu `3 khung hình (15%-50%-85%)` so với `Voice` bên cạnh. Nếu bất kỳ beat nào lệch nghĩa câu nói, còn dính MC/chữ tiêu đề/logo, hoặc bị tối đen, phải cắt lại ngay từ nguồn đúng!

5. **Chỉ kết thúc khi toàn bộ các beat tư liệu được giao đã cắt sạch, kiểm duyệt bằng mắt và ghi nhận vào `asset_registry.json` / `footage_review.json` (`0` lỗi hygiene)**.
{rework_section}

DANH SÁCH `{len(compact_beats)}` BEATS ĐƯỢC GIAO CHO WORKER NÀY:
{json.dumps(compact_beats, ensure_ascii=False, indent=2)}
"""
