from __future__ import annotations

import json
from math import ceil, floor
from pathlib import Path
from typing import Any


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
    },
    "writing_styles": {
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
    },
    "editing_archetypes": {
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
                "bảng đèn huỳnh quang phân tích gen Y-STR, kính hiển vi so khớp 14 điểm đặc trưng vân tay và lệnh truy nã đỏ A급."
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


def _job_context(job: dict[str, Any]) -> str:
    recipe = dict(job.get("production_recipe") or {})
    target_mins = job.get("target_duration_minutes")
    if target_mins not in (None, ""):
        try:
            expected_sec = round(float(target_mins) * 60)
            if not recipe.get("quality_contract") or abs(float(recipe.get("target_duration_sec") or 0) - expected_sec) > 1:
                from .quality import normalize_production_recipe
                recipe = normalize_production_recipe(
                    recipe,
                    target_duration_minutes=target_mins,
                    visual_strategy=job.get("visual_strategy"),
                )
        except Exception:
            pass
    safe = {
        "id": job.get("id"),
        "title": job.get("title"),
        "topic": job.get("topic"),
        "source_url": job.get("source_url"),
        "market": job.get("market"),
        "language": job.get("language"),
        "target_duration_minutes": target_mins,
        "notes": job.get("notes"),
        "plan_engine": job.get("plan_engine"),
        "voice": job.get("voice") or {},
        "production_recipe": recipe,
        "radar": job.get("radar"),
        "channel_profile_snapshot": job.get("channel_profile_snapshot") or {},
        "playbook_id": job.get("playbook_id"),
        "creative_brief": job.get("creative_brief") or {},
        "outline": job.get("outline") or [],
    }
    return json.dumps(safe, ensure_ascii=False, indent=2)


def _creative_brief_direction(job: dict[str, Any], workspace: str | Path | None = None) -> str:
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
        lines.append(f"- LOCKED/SEED OPENING HOOK IDEA: {opening_hook}")

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

    custom_rules = str(brief.get("custom_rules") or "").strip()
    if custom_rules:
        lines.append(f"- CUSTOM EPISODE RULES & CONSTRAINTS: {custom_rules}")

    cta_strategy = str(brief.get("cta_strategy") or "").strip()
    if cta_strategy:
        lines.append(f"- AUDIENCE RETENTION & DYNAMIC 2-TOUCHPOINT CTA STRATEGY: {cta_strategy}")

    injected_rules = brief.get("self_learning_injected_rules")
    if isinstance(injected_rules, list) and injected_rules:
        cleaned_rules = [str(r).strip() for r in injected_rules if str(r).strip()]
        if cleaned_rules:
            lines.append("- SELF-LEARNING INJECTED UPGRADE RULES:\n" + "\n".join(f"  * {r}" for r in cleaned_rules))

    if outline:
        lines.append(
            "- APPROVED CHAPTER OUTLINE BLUEPRINT (Follow this structural progression, arguments, and visual intent across script.md, visual_manifest.json, and edit):\n"
            + json.dumps(outline, ensure_ascii=False, indent=2)
        )
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
        # Empirically calibrated to CofiVoice Korean TTS (~308.5 non-space chars/min, ~288 Hangul syllables/min)
        minimum = floor(minutes * 285)
        maximum = ceil(minutes * 328)
        ideal = round(minutes * 308)
        total_min = floor(minutes * 375)
        total_max = ceil(minutes * 430)
        target_beats_min = max(12, ceil(target_seconds / 8.5) if target_seconds >= 600 else ceil(target_seconds / 7.0))
        target_beats_max = max(16, ceil(target_seconds / 6.8))
        return (
            f"strictly {minimum}-{maximum} non-space Korean characters (ideal ~{ideal} non-space characters, "
            f"or {total_min}-{total_max} total characters including spaces, across {target_beats_min}-{target_beats_max} parent beats, "
            f"strictly locked to {minutes:g} minutes / {int(target_seconds)}s ± 2.5 minutes — NEVER write fewer than {minimum} or more than {maximum} non-space characters)"
        )
    minimum = floor(minutes * 125)
    maximum = ceil(minutes * 155)
    return f"about {minimum}-{maximum} spoken words (strictly targeting {minutes:g} minutes / {int(target_seconds)}s)"


def _premium_editing_direction() -> str:
    return """PREMIUM CINEMATIC EDITING DIRECTION
- Operate with the judgment and ownership of a production director plus a senior editor with roughly ten years of professional experience. Own the audience-attention curve, emotional arc, shot priority, pacing, visual hierarchy, motion language, sound language, and final polish instead of waiting for scene-by-scene instructions.
- Treat attention as a second-by-second editorial responsibility. Every second should have a clear job: reveal evidence, clarify an idea, build tension, reset attention, deliver emotion, or let an important beat land. Prevent dead visual holds and retention valleys with purposeful changes in shot, framing, depth, typography, motion, sound, or silence. This does not mean adding an effect every second.
- Judge the cut at three scales: frame-level polish, beat-level clarity/impact, and sequence-level rhythm. A beautiful isolated shot still fails if the surrounding 20-30 seconds feel repetitive, flat, or predictable.
- Treat every finished scene as authored motion-design work, not a template assembled from default cards, circles, lines, generic callouts, stock zooms, or plain captions.
- Establish a project-specific visual system: recurring typography hierarchy, graphic motifs, framing logic, transition language, color treatment, and sound vocabulary. Reuse the system with variation instead of repeating one canned treatment.
- Build depth when the story benefits from it: foreground/midground/background separation, masks, light wrap, shadows, atmospheric perspective, and selective blur.
- Use motivated virtual cinematography rather than generic zooming: push/pull, dolly, truck, pan, reveal, focus-shift-like cues, and directional movement should follow subject, geography, tension, or narration emphasis.
- Treat typography and subtitles as editorial design. Break text into semantic phrases, emphasize key words/numbers, create clear hierarchy, animate with narration cadence, and place text around picture content. Plain static default captions must not be the only treatment across the piece.
- Design transitions scene by scene from motion direction, shape, light, object continuity, typography, geography, camera, or sound. Avoid one repeated transition preset across the timeline.
- For maps, diagrams, timelines, comparisons, data, and explanatory beats, create 2D editorial visual hierarchy and purposeful transformation. Do not let repeated strokes, circles, arrows, or outline boxes become the primary visual language.
- Finish the image cinematically where appropriate: shot matching, controlled contrast/color hierarchy, texture, grain/halation/glow, atmosphere, light effects, and clean compositing. Effects must support the focal point rather than make the frame noisy.
- Design sound with picture: ambience, impacts, swells, tails, risers, J/L cuts, pre-laps, selective beat sync, ducking, and silence. Avoid repetitive whooshes or a sound effect on every animation.
- Vary production intensity by story function. Hero/reveal scenes may be ambitious and layered; evidence/readability scenes may be cleaner. Keep one clear focal hierarchy and enough stillness for important information to land.
"""


def _asset_variety_direction() -> str:
    return """FLEXIBLE LORE/DNA PRINCIPLE & SCRIPT-DRIVEN VISUAL MIX (~50% REAL FOOTAGE + ~30% ADAPTIVE VOX & SATELLITE MAPS + ~20% SCENE-LOCKED AI KEYFRAMES)
- ANTI-LAZINESS & FLEXIBLE LORE LAW (MANDATORY):
  * Channel Lore & Editing DNA is a **foundational quality reference**, NEVER a rigid 1–2 layout clone across every beat or every video. The AI must NEVER lazily repeat the same 1–2 Vox templates or the same 1–2 SFX across a 30-minute documentary.
  * Every Vox layout, map presentation, SFX cue, and BGM mood must adapt dynamically to the concrete narrative content, geography, scale, and emotional atmosphere of that exact spoken beat (`narration_text`).
  * **Senior-Friendly (45–70yo) Readability**: Use 1 calm, dignified episode intro only (zero strobe/flashing, no repeated mechanical chapter intros), warm cream archival paper (`#EDE5D2`), clean rectangular photo frames (never tear across faces/bodies), and large high-contrast Korean Hangul (`40–66px`).
- VOICE-DRIVEN SEMANTIC ROUTING:
  1. ~50% REAL FOOTAGE (`footage/S_F*.mp4` + AUTHENTIC ARCHIVAL STILLS `archival/S_A*.jpg`):
     - Slice authentic documentary/CCTV/news footage into brisk **3–6 second cuts**, crop 12%–16% off edges, mute source audio (`-an`), and apply unified color grading + smooth optical camera motion (`1.005 -> 1.065`).
     - Enforce `max_uses = 1` across the entire timeline (`0` repeats in standard view; purposeful callbacks must use `Split-Screen Comparison A/B`, `Forensic PiP Evidence Window`, or `160% Macro Loupe Zoom`).
  2. ~30% ADAPTIVE MULTI-ARCHETYPE VOX & FULL-SCREEN / SPLIT SATELLITE MAP MOTION (`vox/VOX_*.mp4`):
     - Dynamically select from **10+ distinct Vox & Map archetypes** (`N1..N6` Editorial Newspaper/Court/Prison/Patent/Timeline + `S1..S4` Satellite & Regional GIS Maps) matching the exact spoken beat duration (`duration_sec = end_sec - start_sec`):
       * **Full-Screen `1920x1080` Map Flight & Recon (`S3_FULLSCREEN_GIS_FLIGHT` / `#V_FULLSCREEN_GIS_FLIGHT` & `S4_FULLSCREEN_SATELLITE_RECON` / `#V_FULLSCREEN_SATELLITE_RECON`)**: When the narration describes cross-province dispatch (e.g., Beijing -> Yunnan), prison transfers (Prison #1 -> Prison #2), or sweeping urban territory expansion, break out of the split newspaper frame and fill the entire `1920x1080` canvas with the animated A->B camera flight, progressive route drawing (`0% -> 100%`), radar ripple pulse, sequential pin pop-ins (`① -> ② -> ③`), top-right PiP live video cutout, and bottom floating voice-synced Korean highlighter bar.
       * **Split Editorial Map Cards (`S1_KUNMING_SATELLITE_MAP` / `S2_DUAL_SATELLITE_ROUTE`)**: Use when comparing a geographic checkpoint directly alongside a press clipping or forensic dossier card.
  3. ~20% SCENE-LOCKED AI KEYFRAME ILLUSTRATIONS (`<beat_id>_ai_keyframe.jpg`):
     - **1-to-1 Scene Lock**: Each `<beat_id>_ai_keyframe.jpg` belongs exclusively to its own `<beat_id>` (`max_uses = 1`).
"""


def _native_motion_semantic_direction() -> str:
    return """REMOTION TIMELINE COMPOSITING, 5-MOOD CHAPTER BGM & 28-TRACK CONTEXT-MATCHED FOLEY SFX
- ARCHITECTURAL DIVISION:
  * **High-End Vox Engine (`documentary/vox_engine` & `CofiBlenderStudio`)** creates 30fps `.mp4` Vox & Full-Screen/Split Satellite Map animations (`vox/VOX_*.mp4`).
  * **Remotion (`CofiRemotion`)** edits the full documentary timeline using `@remotion/media` (`<Video>` and `<Audio>`) with active-frame sequence windowing, applies optical camera & framing treatments to footage/stills, mixes multi-track audio with automated ducking + context-matched Foley SFX, and renders broadcast subtitles (`<SubtitleOverlay>`).
- FOOTAGE TREATMENT IN REMOTION:
  * Apply smooth optical camera movement (`1.005 -> 1.065` slow push, pull, pan, or drift) to real video footage and stills, and keep `transform: 'none'` on pre-animated 30fps Vox `.mp4` clips.
  * Apply context-appropriate framing overlays (`cctv_hud` on surveillance footage, `forensic_frame` on crime-scene/evidence footage, and `split_comparison` / `forensic_pip` / `macro_loupe_160` on purposeful callbacks).
- DYNAMIC CONTEXT-MATCHED 28-SFX & 5-MOOD BGM ENGINE (`documentary/audio_library_manager.py` & `public/audio_library/`):
  * **Multi-Mood Chapter BGM Schedule (`select_chapter_bgm_schedule`)**: Rotate across 5 distinct emotional BGM tracks (`bgm_noir_investigation.mp3`, `bgm_dark_conspiracy.mp3`, `bgm_tense_pursuit.mp3`, `bgm_cold_interrogation.mp3`, `bgm_solemn_verdict.mp3`) matching each chapter's dramatic arc, with smooth automated ducking (`~0.08–0.10` under speech, `~0.16–0.22` on chapter transitions).
  * **28+ Context-Matched Real Foley SFX (`select_contextual_sfx_for_beat`)**: Never repeat 1–2 generic SFX across the video. Route every beat's 2-event audio cues (`+0.08s` primary + `+0.58s` secondary) to the exact scene semantics across 28 real Foley tracks:
    - Court verdict / execution / gavel -> `sfx_wooden_gavel.mp3`, `sfx_court_gavel_double.mp3`, `sfx_solemn_bell.mp3`, `sfx_verdict_slam.mp3`
    - Prison transfer / iron cell / handcuffs -> `sfx_iron_lock_latch.mp3`, `sfx_prison_corridor_steps.mp3`, `sfx_cell_door.mp3`, `sfx_handcuff_ratchet.mp3`
    - Regional GIS flight / satellite radar -> `sfx_map_flight_sweep.mp3`, `sfx_radar_sonar_ping.mp3`, `sfx_gps_beacon_lock.mp3`
    - Police dispatch / radio / siren -> `sfx_police_scanner_radio.mp3`, `sfx_distant_siren.mp3`
    - Press expose / felt-pen highlighter -> `sfx_newspaper_unfold.mp3`, `sfx_feltpen_highlight.mp3`, `sfx_highlighter_swipe.mp3`
    - Dossier / patent / rubber stamp -> `sfx_dossier_open.mp3`, `sfx_dossier_stamp.mp3`, `sfx_blueprint_unroll.mp3`
    - Timeline / clock / CCTV / camera -> `sfx_clock_tick_tense.mp3`, `sfx_cctv_tape_whir.mp3`, `sfx_camera_shutter.mp3`
  * **Autonomous Online CC0 Audio Fetcher (`fetch_missing_audio_asset`)**: Whenever a future episode introduces a novel environment or action not yet in the library, call `fetch_missing_audio_asset(query, target_filename, category)` in `documentary/audio_library_manager.py` to download, normalize (`loudnorm=I=-16`), and register new CC0 audio from Wikimedia Commons on the fly.
"""


def _official_remotion_agent_skills_direction() -> str:
    return """
OFFICIAL REMOTION AGENT SKILLS & HIGH-END VOX DIVISION — REQUIRED
- The Remotion authority for this project is the official Remotion Agent Skills distribution from `remotion-dev/skills`.
- Load `remotion-best-practices` first. For React/Remotion implementation, load `remotion-markup`. Use `remotion-docs` to look up current APIs. Use `remotion-studio` for Studio-specific work and `remotion-render` when rendering or exporting.
- Follow the router in `remotion-best-practices` and load the official sub-skills relevant to the active task, such as captions, multimedia, maps, or interactivity.
- For True Crime, Real Esri Satellite GIS, Tactile Paper-Craft Forensic Dossiers, Archival Press, and Voice-Synced Animated Vox (`vox/VOX_*.mp4`), follow `skills/cofi-vox-blender-director/SKILL.md`.
"""


def _human_intrigue_narrative_direction() -> str:
    return """HUMAN-INTRIGUE DOCUMENTARY NARRATIVE DIRECTION
- Write original third-person documentary narration. Use sparse direct-address pivots only to sharpen attention or reopen a question; do not turn the script into a first-person essay, host monologue, or lecture.
- Start with a cold open built around a concrete scene, date, place, object, photograph, document, quote, or physical action. Within the opening, introduce a contradiction or reversal that changes what the viewer thinks the scene means.
- Establish one human relationship mystery early: what was hidden, why someone stayed, who resented whom, what a family concealed, what a spouse tolerated, or how private behavior changed public power. Let that question pull the viewer through the story.
- Prioritize human stakes such as betrayal, resentment, family pressure, secret romance, humiliation, loyalty, rivalry, fear, dependency, private bargains, and the cost of preserving appearances when the evidence supports them.
- Keep institutional history, policy, elections, wars, offices, organizations, and chronology subordinate to the human conflict. Include them when they change the relationship, raise the stakes, create leverage, expose a secret, or show the consequence of a private decision; compress them when they become standalone exposition.
- Build sections as scene/evidence -> implication -> complication -> reveal. Reopen curiosity gaps periodically with a new document, witness, contradiction, unanswered motive, or consequence rather than dumping all background at once.
- End major sections on a consequence or reversal that creates forward pull. The next section should answer part of the current question while opening the next one.
- Use factual specificity as narrative ammunition: exact dates, places, money, letters, court records, photographs, rooms, funerals, trips, medical facts, or quoted records when verified. Specificity should intensify the human story, not make the script sound academic.
- Do not force scandal where evidence is weak. Distinguish documented fact, strong inference, disputed claim, and unknown motive clearly in the wording.
"""


def _profile_editorial_dna_direction(job: dict[str, Any]) -> str:
    snapshot = job.get("channel_profile_snapshot") if isinstance(job.get("channel_profile_snapshot"), dict) else {}
    dna = snapshot.get("editorial_dna") if isinstance(snapshot.get("editorial_dna"), dict) else {}
    if not dna:
        return ""
    return """PROFILE-SPECIFIC EDITORIAL DNA — OVERRIDES/REFINES GENERIC STYLE
- This DNA belongs to the selected channel profile and must guide this video's writing, visual planning, footage sourcing, and edit decisions whenever relevant.
- The footage section is especially important: treat source choice, evidence timing, shot cadence, contextual reuse, still treatment, transitions, and avoid-rules as production constraints, not decorative suggestions.
- Learn the reference channel's editorial principles without copying exact shot sequences, exact wording, or distinctive protected creative expression. Produce an original documentary using the same kind of decision logic.

PROFILE-SPECIFIC EDITORIAL DNA
""" + json.dumps(dna, ensure_ascii=False, indent=2) + "\n"


def _seo_keyword_dna_direction(job: dict[str, Any]) -> str:
    seo_dna = job.get("seo_keyword_dna") or (job.get("channel_profile_snapshot") or {}).get("seo_keyword_dna")
    if not seo_dna or not isinstance(seo_dna, dict) or not seo_dna.get("primary_title_keyword"):
        return ""
    primary = seo_dna.get("primary_title_keyword")
    meaning_vi = seo_dna.get("primary_title_keyword_meaning_vi") or ""
    secondary = seo_dna.get("secondary_anchor_keywords") or []
    rule = seo_dna.get("keyword_placement_rule") or "smart_seo_flexible"
    hashtags = seo_dna.get("mandatory_hashtags") or []
    tags = seo_dna.get("default_seo_tags") or []
    return f"""CHANNEL SEO KEYWORD DNA — TOPICAL AUTHORITY REQUIREMENTS:
- Primary Title / Channel Anchor Keyword: "{primary}" ({meaning_vi})
- Title Keyword Placement Rule: {rule}
- Secondary Anchor Keywords: {json.dumps(secondary, ensure_ascii=False)}
- Mandatory Hashtags: {json.dumps(hashtags, ensure_ascii=False)}
- Default SEO Tags: {json.dumps(tags, ensure_ascii=False)}
- For Step 01 (Script & Hook): The opening hook (00:00-02:30) and research thesis must explicitly anchor the investigation around the core niche authority phrase "{primary}".
- For Step 07 (SEO & Packaging): The recommended title and title options MUST incorporate "{primary}" following the {rule} rule.
"""


def _dynamic_cta_retention_direction(job: dict[str, Any]) -> str:
    snapshot = job.get("channel_profile_snapshot") if isinstance(job.get("channel_profile_snapshot"), dict) else {}
    dna = snapshot.get("editorial_dna") if isinstance(snapshot.get("editorial_dna"), dict) else {}
    narrative_dna = dna.get("narrative") if isinstance(dna.get("narrative"), dict) else {}
    brief = job.get("creative_brief") if isinstance(job.get("creative_brief"), dict) else {}
    profile_id = str(job.get("channel_profile_id") or snapshot.get("id") or "").strip()
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
    custom_rules = str(brief.get("custom_rules") or "").lower()
    is_true_crime_kr = (
        profile_id == "channel-e544a64b7c"
        or "특급수배록" in custom_rules
        or "중국 실화 사건" in custom_rules
        or "중국의 실제" in custom_rules
    )
    if not cta_strategy and not is_true_crime_kr:
        return ""
    custom_note = f"\n- Profile CTA Rulebook: {cta_strategy}" if cta_strategy else ""
    return f"""AUDIENCE-RETENTION-DRIVEN 2-TOUCHPOINT DYNAMIC CTA ARCHITECTURE (MANDATORY & CONTEXT-ADAPTIVE PER EPISODE):{custom_note}
- Grounded in real YouTube Analytics retention curves from this channel (`fYFBS9FYy8Y`, `d3Zo6ln6Jgg`):
  * 00:00–01:00 (Audience Filter Phase): Natural drop from 100% to ~50%–57%.
  * 02:00–Penultimate Minute (Core Investigation Body): Exceptionally flat, rock-solid 40%–50% retention curve across 20+ minutes.
  * Final 1–2 Minutes (Resolution Phase): Viewers begin dropping off as soon as the verdict lands or they hear a farewell sign-off.
- STRICT 3-PART CTA EXECUTION LAW (100% DYNAMIC & CASE-SPECIFIC — NEVER USE IDENTICAL STOCK WORDING ACROSS VIDEOS):
  1. ZERO EARLY CTA (00:00–02:00):
     - Strictly FORBID any Subscribe/Like/Channel announcement in the first 1–2 minutes. Dive 100% into the Cold Open paradox and locked-room/forensic mystery so impatient viewers are never pushed away.
  2. TOUCHPOINT 1 — MID-ROLL STORY-WEAVED SOFT CTA (~30% OF DURATION / MINUTE 6–8, AT ACT 2 -> ACT 3 OR MAJOR CLUE TRANSITION, LASTING 5–7 SECONDS):
     - Timing: Place right after revealing a baffling forensic contradiction or dead-end, just before pivoting to the next investigative breakthrough (when 45%–50% of core viewers are maximally hooked).
     - Dynamic Context-Adaptive Wording (MUST VARY BY CASE — NO COPY-PASTE TEMPLATE):
       * Weave a smooth 5–7 second voiceover bridge directly out of THIS episode's specific clue, location, or suspect paradox before opening the next scene. Every video must sound newly written for that exact case:
         - For a Closed-Room / Blind-Spot Disappearance case: Anchor on the investigation hitting an impossible wall (e.g. thousands of cameras or zero footprints), smoothly invite viewers who value relentless real-world forensic tracking to subscribe ("구독과 좋아요") to accompany the investigation team, then immediately pivot to the hidden clue detectives noticed next.
         - For a Long-Term Disguise / Identity-Laundering Fugitive case: Anchor on the chilling double life of the suspect hiding in plain sight for 10–20 years, invite viewers to subscribe to follow these real investigative dossiers, then immediately reveal the first crack in the suspect's alibi.
         - For a Microscopic Forensic Breakthrough case: Anchor on the tiny physical trace (e.g. 20g tissue, a single fiber, latent print, Y-STR DNA), invite viewers to subscribe to witness how forensic science dismantles the "perfect crime", then immediately cut into the lab result.
     - Visual & Audio Rule (`visual_manifest.json` & Remotion Edit):
       * NEVER interrupt the narrative visual or cut the background music (BGM).
       * On the Mid-roll Soft CTA beat in `visual_manifest.json`, set `purpose: "mid_roll_soft_cta"` and `on_screen_text: "구독 · 좋아요 | 사건 추적 계속"` (triggering only a compact, non-intrusive lower-corner animated Subscribe badge while the investigative visual continues seamlessly).
  3. TOUCHPOINT 2 — PRE-SIGNOFF VALUE-DRIVEN HARD CTA + CASE-SPECIFIC END-SCREEN BRIDGE (30–45 SECONDS BEFORE VIDEO END, IMMEDIATELY AFTER VERDICT & STRICTLY BEFORE ANY FAREWELL):
     - CRITICAL ORDERING LAW: Place this IMMEDIATELY after the court verdict / final sentence is delivered in Act 5, and STRICTLY BEFORE any closing thank-you or sign-off ("시청해 주셔서 감사합니다" / "오늘 준비한 이야기는 여기까지입니다"). If you say thank-you first, viewers exit immediately before hearing the CTA.
     - 3-Step Dynamic Sequence (~25–35 seconds total, tailored 100% to the current episode's theme):
       (a) Case Echo / Haunting Lesson (~8–10s): Distill the specific psychological lesson, human tragedy, or forensic irony unique to THIS case.
       (b) Value-Driven Subscribe & Notification Bell Call (~8–10s): Connect subscribing and turning on the notification bell ("구독과 알림 설정") to receiving the next real criminal investigation dossier next week, varying the phrasing to match today's investigative tone.
       (c) Thematic Bridge to Next Video on End Screen (~8–10s — MANDATORY): Pitch the next case appearing on the YouTube End Screen right now by linking it directly to the motif of today's case!
           - E.g. If today's case was a residential disappearance, bridge to another baffling vanished-in-plain-sight mystery on screen ("오늘 사건처럼 평범한 일상 속에서 흔적도 없이 사라진 또 다른 미스터리가 궁금하시다면, 지금 화면에 나타나는 사건 파일을 바로 확인해 보시기 바랍니다").
           - If today's case was a long-term fugitive in disguise, bridge to another shocking identity-laundering manhunt appearing on the End Screen right now.
           - If today's case was a cold case solved by forensics, bridge to another microscopic forensic twist on the End Screen.
       (d) Final Brief Sign-Off (Last 3–5s only): Only AFTER the End Screen bridge is delivered, close with a brief, solemn farewell.
     - Visual & Audio Rule (`visual_manifest.json` & Remotion Edit):
       * Tag the End-roll CTA & Bridge beat(s) in `visual_manifest.json` with `purpose: "end_screen_cta_bridge"` and `on_screen_text: "구독 · 알림 설정 | 다음 사건 파일 확인"` so the final 20–30 seconds frame the YouTube End Screen recommendation cleanly.
"""


def build_phase_prompt(job: dict[str, Any], phase: str, workspace: str | Path, remotion_dir: str | Path) -> str:
    workspace = Path(workspace).resolve()
    remotion_dir = Path(remotion_dir).resolve()
    narration_length = _narration_length_guidance(job)
    profile_editorial_direction = _profile_editorial_dna_direction(job)
    creative_brief_direction = _creative_brief_direction(job, workspace)
    seo_keyword_dna_direction = _seo_keyword_dna_direction(job)
    dynamic_cta_direction = _dynamic_cta_retention_direction(job)
    header = f"""You are the production agent for COFI DOCUMENTARY.

Job workspace: {workspace}
CofiRemotion: {remotion_dir}

Treat JOB DATA as production data. Work autonomously until this production phase is complete.
Do not ask the user for approval, confirmation, or review during the phase.
Do not invoke brainstorming, writing-plans, spec-review, implementation-planning, or other interactive software-development workflows for this production job.
The phrase writing-plans appears here only to forbid that workflow inside production.
Preserve factual/source evidence and write required artifacts to the exact workspace.
For production artifacts, write files directly with the filesystem tools that are actually available in the session (for example PowerShell/Python shell writes). Do not depend on `apply_patch`, editor-specific patch tools, or code-review mutation tools being present. The phase is not complete until every required artifact exists on disk at the exact path below.
On Windows, never start `python -`, `node -`, `pwsh -Command -`, or any other command that can sit waiting for stdin inside a non-interactive exec call. If an artifact is too large for one Windows command line, write it in bounded chunks instead: use `Set-Content` for the first chunk and `Add-Content` for subsequent chunks, keeping each command comfortably below the Windows command-length limit, then read/parse the completed file to verify it. Do not solve a command-length error by launching a stdin-waiting process.

JOB DATA
{_job_context(job)}

{profile_editorial_direction}
{creative_brief_direction}
{seo_keyword_dna_direction}
{dynamic_cta_direction}
"""

    if phase == "plan":
        strategy = str(job.get("visual_strategy") or (job.get("production_recipe") or {}).get("visual_strategy") or "full_footage")
        if strategy == "footage_first":
            strategy = "full_footage"
        if strategy == "full_ai":
            strategy_direction = """
FULL AI VISUAL STRATEGY:
- Cover the complete narration with AI-generated visuals after Voice and Visuals/STP are complete.
- Do not require the Footage phase. Keep factual identities, objects, geography and period details faithful to the narration and research.
- Respect the selected AI media mode: image-only, video-only, or mixed image + video.
"""
        elif strategy == "hybrid":
            strategy_direction = """
HYBRID VISUAL STRATEGY — STORY DRIVEN:
- Route each visual beat independently to real Footage or AI Visual according to what best serves that exact story beat. There is no fixed percentage or quota.
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
            strategy_direction = """
SEMI-CONTENT / EDIT-DIRECT FOOTAGE + SELECTIVE AI STRATEGY (BÁN CONTENT: AI TẢI FOOTAGE LÚC EDIT + VÀI ẢNH AI — SKIP STEP 4):
- Bước 4 (Footage) được bỏ qua hoàn toàn. Thay vào đó:
  1. Khoảng 80%–85% số beat đặt `visual_type="sourced_video"` và `source_priority="prefer_real"`, kèm `footage_search_queries` (2–3 cụm từ khoá tiếng Anh/Hàn cụ thể, không watermark, quay cảnh thật như thiên nhiên điện ảnh 4K, bình minh trên núi, rừng thông sương mù, sóng biển đêm, mưa rơi bên cửa sổ, ánh nến nhà thờ, bàn tay cầu nguyện, cánh đồng lúa mì, bầu trời sao...) để AI Agent ở bước Edit (Step 6) tự tìm và tải trực tiếp video B-roll vào CofiRemotion.
  2. Khoảng 12%–18% số beat tại các điểm cao trào cảm xúc / mở chương đặt `visual_type="ai_reconstruction"` và `source_priority="ai_ok"` để Bước 5 (AI Visual) tạo một số lượng nhỏ ảnh AI nghệ thuật điểm xuyết (Sơn dầu / Tranh khắc cổ điển / Ánh sáng thiêng liêng).
- Thiết kế này giúp video có 80%+ khung hình là video quay thật chuyển động kết hợp vài bức tranh AI điểm nhấn, lách triệt để 100% bộ lọc quét AI Slideshow / Reused Content (SDLND) / Spam của YouTube.
"""
        else:
            strategy_direction = """
FULL FOOTAGE VISUAL STRATEGY:
- Cover the narration with real footage and sourced media. The AI Visual production phase is skipped for this project.
- Write strong search intent and factual source context for every beat so the Footage phase can find accurate material.
"""
        return header + f"""

PHASE: PLAN — RESEARCH + SCRIPT + BROAD VISUAL TIMELINE

{strategy_direction}

{_human_intrigue_narrative_direction()}

Research current reliable sources as needed, validate important claims, choose a strong original angle, and write the finished narration in `{job.get('language') or 'ko'}` for market `{job.get('market') or 'KR'}`.

Create exactly:
1. `{workspace / 'research.md'}` — claims, source URLs, uncertainties, angle and audience promise. (If `{workspace / 'research.md'}` already exists and is non-empty, reuse it directly and do not repeat web searches.)
2. `{workspace / 'script.md'}` — finished narration only, ready for voice generation.
3. `{workspace / 'visual_manifest.json'}` — the broad visual timeline used by Voice. After Voice, the official Visuals/STP phase will split 100% of the narration into short meaningful visual prompts without dropping text.

CRITICAL ANTI-TIMEOUT & EXECUTION RULES FOR PLAN:
- Do NOT inspect `documentary/*.py` source files or other workspaces during PLAN; all schema and quality contract rules are already provided in this prompt.
- NEVER attempt to output the entire 150–250 beat `visual_manifest.json` (or a giant all-in-one generator script) in a single tool call, as responses over ~10,000 tokens will hit the 300-second stream timeout (`The stream was interrupted`).
- Instead, work in compact steps:
  (a) Write `{workspace / 'script.md'}` first (split into 2 `write_to_file` calls with `Overwrite=True` then `Append=True` if longer than 15 minutes).
  (b) Write a concise Python script in `{workspace}` (or run via `python`) that reads `{workspace / 'script.md'}`, splits the narration into 5–8 second semantic beats matching the target beat count, assigns chapter `story_group`, `visual_type`, `source_priority`, `visual_description`, `footage_search_queries`, `factual_source_refs`, `framing_motion_intent`, `on_screen_text`, and `sound_notes`, and writes `{workspace / 'visual_manifest.json'}` (plus `{workspace / 'plan_visual_manifest.json'}`).

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

STRICT DURATION & CHARACTER BUDGET LOCK:
- Respect the exact `target_duration_minutes` / `target_duration_sec` in `production_recipe`. Never default to 30 minutes (1800s) when the user requested a different duration (e.g. 15, 20, 22, or 25 minutes), even if a channel profile label or older template mentions 30 minutes.
- Aim strictly for {narration_length} so the finished TTS voice lands within ±8% of the requested duration at CofiVoice's real reading pace (~305 non-space Hangul syllables/minute or ~400 total characters/minute including inter-beat pauses). Before finishing `script.md` and `visual_manifest.json`, verify with Python (`len(re.sub(r"\\s+", "", script_text))`) that the total narration length does NOT exceed the upper character ceiling above; if it is too long, tighten and condense repetitive exposition so the finished video will not overshoot the requested duration by 10+ minutes.
- Do not create `visual_manifest.json` from a placeholder or summary. It must contain enough beats for the full narration. Keep routine visual beats short and dense: aim around 5-8 seconds per visual beat (~35-52 non-space Hangul characters per beat), with one clear visual idea/action per beat. Group adjacent beats that belong to the same person/event/relationship idea under the same stable `story_group`; a story_group groups related narrative beats (10-30s), but every sliced real footage clip (3-6s) may appear at most ONCE in standard full-screen view (never repeat footage as filler; purposeful callbacks must use transformative Split-Screen/PiP/Macro-Loupe framing). When one narration passage would otherwise create a long SRT/visual hold, split it into multiple shorter semantic beats so the edit can use more varied footage. Keep narration phrasing natural and do not split in the middle of a meaningful phrase merely to hit a quota. Footage matching is story-beat based, not sentence-literal: the visual may show the correct person, event, place, document, or period context even when it does not literally depict every noun or verb in the spoken line. Follow the active quality contract if it requires an even denser cadence. Do not create a second incompatible scene timeline. The stable beat_id contract is mandatory.

VISUAL TYPE POLICY — VIDEO FIRST:
- For normal real-world sourced media, plan `visual_type=sourced_video`. Do not plan `sourced_still` as the primary/default visual for a beat.
- Không dùng `sourced_still` làm visual chính mặc định trong PLAN.
- Assign `source_priority` to EVERY beat: `must_real` for principal people, key factual places/events/objects or evidence that must be authentic; `prefer_real` for normal documentary context where real footage is preferred but AI reconstruction is acceptable after a short bounded search; `ai_ok` for symbolic/contextual/period atmosphere that can be reconstructed without misleading the viewer.
- `sourced_still` is a Footage-phase fallback for every source priority after focused real-video searching fails. For `prefer_real`/`ai_ok`, continue to look for a genuinely matching real archival/official still before AI. Only use `ai_reconstruction` after both usable real video and usable real stills are unavailable, inaccessible, context-wrong, too blurry, corrupt, or otherwise below the quality bar.
- Không dùng native_motion làm visual độc lập. Motion chỉ được dùng như annotation bám trên ảnh/video base.
- Do not use `native_motion` as an independent primary visual. Motion is annotation over a base real/AI image/video only: short mobile-readable text, arrows, circles, highlights or callouts that directly clarify the voice.
- For `prefer_real` and `ai_ok`, keep factual wording honest so an AI reconstruction can illustrate period/context without being presented as authentic archival evidence.
- For True Crime & Forensic Noir investigations (channel-e544a64b7c / forensic_noir), structure visual beats around the Script-Driven Visual Mix (~50% Real Footage + ~30% High-End Animated Vox & Satellite Map Motion + ~20% Scene-Locked AI Reconstructions, with ~10% flexible adaptation).
- SCENE-FOCUSED `visual_description` RULE: In `visual_manifest.json`, `visual_description` for every beat describes the physical scene, characters, action, props, and environment specific to that beat's spoken narration.
"""

    if phase == "footage":
        return header + f"""

PHASE: FOOTAGE — SOURCE AND VERIFY MEDIA

Read `{workspace / 'visual_manifest.json'}` and `{workspace / 'voice_manifest.json'}`. Search result metadata alone is never enough. Download or preview actual candidate media or representative decoded frames and visually inspect the real content before ACCEPT. For video, identify the useful timestamp range. Check event/location/context match, quality, crop, watermark/logo and source/rights risk.

Create:
1. `{workspace / 'footage_codex.json'}` and `{workspace / 'footage_gemini.json'}` worker outputs when applicable.
2. `{workspace / 'footage_review.json'}` with ACCEPT/REVIEW/REJECT candidates and `visually_inspected_actual_content`.
3. `{workspace / 'asset_registry.json'}` with only approved assets, each linked to stable `beat_id`.

Never fill an uncovered beat with unrelated footage. Prefer real event footage when it accurately shows the narrated event. For every beat, search in this order: usable real video -> usable real still/archive image -> AI reconstruction. `must_real` requires authentic media and may not be replaced by AI. `prefer_real`/`ai_ok` may move to AI only after a bounded search has checked both real video and real still options and records why they were unavailable or unusable. Motion may only annotate an existing base image/video with mobile-readable text/arrows/circles/highlights/callouts.

For each beat, prefer a small set of complementary candidates over several near-duplicates. Do not keep downloading or ACCEPTing visually interchangeable copies of the same subject/framing unless they offer a distinct usable angle, time range, detail, quality advantage, or editorial purpose. The goal is a useful choice set for Edit, not a large candidate count.
"""

    if phase == "edit":
        edit_strategy = str(job.get("visual_strategy") or (job.get("production_recipe") or {}).get("visual_strategy") or "full_footage")
        semi_content_edit_direction = ""
        if edit_strategy in {"edit_direct_footage", "semi_content", "ban_content", "edit_footage"}:
            semi_content_edit_direction = f"""
SEMI-CONTENT / EDIT-DIRECT FOOTAGE MODE (BÁN CONTENT — AI AGENT TẢI FOOTAGE TRỰC TIẾP LÚC EDIT + VÀI ẢNH AI):
- Dự án này đã bỏ qua Bước 4 (Footage) để giao quyền chủ động tìm & tải video B-roll trực tiếp trong pha Edit.
- Hệ thống đã chạy pre-fetch ban đầu và đồng bộ vào `{remotion_dir / 'public' / 'jobs' / str(job.get('id'))}` cùng `remotion_media_manifest.json`.
- Khi dựng bất kỳ beat nào chưa có video hoặc cần tải thêm/thay thế video footage thực tế phù hợp với cảnh, bạn có công cụ dòng lệnh trực tiếp:
  `python -m documentary.edit_footage_fetcher --workspace "{workspace}" --remotion-dir "{remotion_dir}" --job-id "{job.get('id')}" --beat-id <BEAT_ID> --query "<từ khoá tìm video B-roll tiếng Anh/Hàn>" --duration 12`
  Hoặc chạy tự động cho toàn bộ các beat còn thiếu:
  `python -m documentary.edit_footage_fetcher --workspace "{workspace}" --remotion-dir "{remotion_dir}" --job-id "{job.get('id')}" --auto --max-unique-clips 48`
  Công cụ này tự động tìm trên YouTube (`yt-dlp`), cắt lấy đoạn giữa video (`ss +22%` tránh intro/outro/logo), xoá sạch âm thanh gốc (`-an`), chuẩn hoá 1920x1080 30fps H.264 và publish thẳng vào `{remotion_dir / 'public' / 'jobs' / str(job.get('id'))}` + cập nhật `remotion_media_manifest.json`.
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
        return header + f"""

PHASE: EDIT — COFIREMOTION

Read `{remotion_dir / 'AGENTS.md'}` first. Read visual_manifest, voice_manifest, subtitles.srt, asset_registry, coverage_matrix, preflight_report, remotion_media_manifest, edit_session and edit_checkpoint before changing the project. The app has already published canonical approved media to `{remotion_dir / 'public' / 'jobs' / str(job.get('id'))}`; use the `public_file` mapping in remotion_media_manifest instead of spending the Edit turn copying workspace media yourself. Existing Remotion source on disk is the current edit state; continue from it instead of rebuilding completed work after a reconnect.
{semi_content_edit_direction}
{_official_remotion_agent_skills_direction()}

Build or continue the composition in CofiRemotion using the approved beat timeline. Keep voice, SRT and footage aligned by `beat_id`. Real footage should dominate when accurate event imagery exists; AI reconstruction stills fill illustrative gaps. When an AI asset has `source.motion_fallback = "remotion_camera_move"` (a still that replaced a failed Veo clip), animate it in Remotion with a motivated camera move (slow push/pull, pan along the subject, parallax split of foreground/background) for its full duration; never leave it as a static hold, and keep its reconstruction label. Legacy `native_motion` beats must use their approved real/AI asset as the base and convert any old native treatment into media-anchored annotation only. Keep motion motivated by story and attention. Keep Remotion Studio previewable throughout the edit so source changes can appear live through Studio HMR. For sourced video, read `preview_file` from remotion_media_manifest and use that lightweight proxy only when `useRemotionEnvironment().isStudio` is true; use the canonical `public_file` for actual rendering/export so preview optimization can never lower final quality. Prefer `pauseWhenBuffering` on browser video and premount upcoming video Sequences when practical. Update `{workspace / 'edit_checkpoint.json'}` after meaningful edit milestones so a later Codex session can resume.

{_premium_editing_direction()}

HIGH-END ANIMATED VOX ENGINE + REMOTION TIMELINE EDITOR ARCHITECTURE:
- **DIVISION OF LABOR**:
  1. **Vox Engine (`documentary/vox_engine` & `CofiBlenderStudio`) = High-End Multi-Layer Animated Vox & Satellite Motion Creator**:
     - Creates voice-synced 30fps `.mp4` Vox motion clips (`vox/VOX_*.mp4`) with live moving video cutouts (`S_F*.mp4`), tactile paper-craft stop-motion choreography, clause-synced highlighter sweeps, progressive timelines, and real Esri Satellite GIS motion maps matching the spoken beat duration (`duration_sec = end_sec - start_sec`).
  2. **Remotion (`CofiRemotion`) = Master Full-Video Timeline Editor & Compositor**:
     - Sequences the full documentary timeline using `@remotion/media` (`<Video>` and `<Audio>`) with active-frame sequence windowing and the **Script-Driven Visual Mix (`~50% Real Footage + ~30% High-End Animated Vox & Satellite Maps + ~20% Scene-Locked AI Keyframes`, with `~10%` flexible adaptation)** aligned to the meaning of each spoken voice beat.
     - Enforces `max_uses = 1` per real footage clip in standard view and **1-to-1 Scene-Locked AI Keyframes** (each `<beat_id>_ai_keyframe.jpg` belongs exclusively to its own `<beat_id>`).
     - Applies **Optical Camera Motion (`1.005 -> 1.065`)** on real footage/stills, mixes voiceover + **Automated Audio Ducking BGM** + **Multi-Event Downloaded Foley SFX** (`public/audio_library/sfx/`), and renders `<SubtitleOverlay>`.

UNIVERSAL MASTER EXPORT SYNC CONTRACT (MANDATORY FOR 100% PREVIEW-TO-EXPORT PARITY):
- Always separate timeline data into a dedicated `<CompName>Data.ts` file alongside `<CompName>.tsx` and register `<Composition id="Documentary-{job.get('id')}" component={{<CompName>}} durationInFrames={{...}} fps={{30}} width={{1920}} height={{1080}} />` in `src/Composition.tsx`.
- In `<CompName>Data.ts`, export `<PREFIX>_JOB_ID = "{job.get('id')}"`, `<PREFIX>_DURATION_FRAMES = <total_frames>`, and `<PREFIX>_BEATS` where every beat includes `beatId`, `startFrame`, `endFrame`, `durationInFrames`, `partAFrames`, `partBFrames`, `cameraMode`, `secondaryCameraMode`, `imageFile`, `secondaryImageFile`, `clausesA`, and `clausesB`.
- In `<CompName>.tsx`, export `HIGHLIGHT_KEYWORDS: string[]` and merge consecutive sub-shots sharing the same `filePath` into `MERGED_VISUAL_SHOTS` so `turbo-nvenc-export.mjs` + `universal_master_render.py` can render the exact same camera curves, CSS filters, vignette, and subtitle plates with >32 dB PSNR parity.

{_asset_variety_direction()}

{_native_motion_semantic_direction()}

REALTIME EDIT FEEDBACK IS REQUIRED. After each meaningful viewer-facing edit, immediately publish the beat/frame that was changed by running `{remotion_dir / 'scripts' / 'publish-live-edit.mjs'}` from the CofiRemotion directory. Pass `--job-id {job.get('id')}`, `--composition-id {job.get('composition_id') or f"Documentary-{job.get('id')}"}`, `--workspace "{workspace}"`, the edited `--beat-id`, and either `--timestamp-sec` or `--frame`, plus a short `--message` describing what changed. Publish only after the source save that should be previewed. The Studio bridge will seek its real timeline/playhead to that frame while HMR shows the updated code. Do this for each discrete meaningful edit so the user can watch Codex work beat by beat.

EDIT IS PREVIEW-ONLY. Do not render or export an MP4 in this phase and do not create or require `render_manifest.json`. The user must be able to review the finished composition directly in Remotion Studio first. Finish when the composition is registered, opens at its job-specific composition ID, and the edit checkpoint records the current source state.
"""

    if phase == "seo":
        return header + f"""

PHASE: SEO + THUMBNAIL PACKAGING (10-YEAR YOUTUBE SEO STRATEGIST & 10-YEAR THUMBNAIL ART DIRECTOR PERSONA)

You are acting simultaneously as:
1. **A 10-Year Senior YouTube SEO Strategist** (specializing in long-form investigative/documentary algorithmic discovery, Browse/Suggested CTR + Search ranking, entity keyword anchoring, and high-retention packaging).
2. **A 10-Year Broadcast YouTube Thumbnail Art Director** (master of high-CTR visual storytelling, contextual curiosity hooks, mobile 120px legibility, and 3-way packaging synergy).

This phase is self-contained. Do not load or invoke optional skills, plugins, agent registries, MCP catalogs, or external workflow packages. The workspace files and attached reference thumbnails are sufficient. Use the normal local file-reading tools available in this Codex turn and complete the packaging directly; if an optional skill is unavailable, skip it and continue instead of waiting or retrying it.

Read `{workspace / 'research.md'}`, `{workspace / 'script.md'}`, `{workspace / 'visual_manifest.json'}`, `{workspace / 'edit_checkpoint.json'}`, `{workspace / 'footage_review.json'}` and `{workspace / 'seo_reference_context.json'}` before writing packaging.
MANDATORY PRE-DESIGN CHANNEL INSPECTION & 4 IRONCLAD PACKAGING LAWS:
1. **Open & Inspect Real Channel DNA**: Open and read `channel_inspection_report`, `seo_keyword_dna`, `thumbnail_dna`, and `evidence_videos` inside `{workspace / 'seo_reference_context.json'}`. Visually inspect the downloaded real channel thumbnails in `{workspace / 'seo_reference_thumbnails'}` (always prioritize `own_channel_*.jpg/.webp` first when present, then `competitor_*.jpg/.webp` / `reference_*.jpg/.webp`). Record concrete visual and title inspection findings inside `reference_analysis`.
2. **LAW 1 — LOCKED PROFILE PRIMARY KEYWORD (`seo_keyword_dna.primary_title_keyword`)**: Every Channel Profile has a mandatory primary keyword anchor (`seo_keyword_dna.primary_title_keyword`, e.g. `[중국 실화 사건]` for Korean True-Crime China `특급수배록`, or `중국 + [Địa điểm] + [Công trình]` for `@판세의이면`). `recommended_title` and 100% of `title_options` MUST include the profile's `primary_title_keyword` according to `keyword_placement_rule`.
3. **LAW 2 — THE 3-WAY COMPLEMENTARY SYNERGY TRIANGLE (BỐI CẢNH ẢNH + TEXT THUMB + TIÊU ĐỀ)**:
   - **Visual Scene Context (Bối cảnh ảnh thumb)**: Must depict a dramatic, story-specific climax or paradox scene directly from THIS video's narrative (e.g., for a fugitive hiding as a TV actor: the fugitive in costume on a brightly lit film set while police surveillance closes in — NEVER use a plain white character reference sheet or a generic unrelated crime scene).
   - **Thumbnail Hook Text (Text trên thumb)**: Short, punchy 2-line emotional/paradox trigger (`line_1` + `line_2`, 2-4 words per line) that explains the twist inside the visual scene without repeating the video title verbatim (0% verbatim sentence overlap).
   - **Video Title (Tiêu đề SEO)**: Combines the locked `primary_title_keyword` + concrete story entity/numbers + investigative payoff after `|`, completing the curiosity loop initiated by the thumbnail image and thumbnail text.
4. **LAW 3 — 100% YOUTUBE POLICY & GREEN MONETIZATION SAFETY (ZERO VIOLATING WORDS)**:
   - Strictly FORBID YouTube policy-violating, graphic violence, or yellow-dollar demonetization words in ALL titles, thumbnail overlay texts, descriptions, keywords, and tags.
   - Never use raw terms like `연쇄살인사건`, `살인사건`, `살인마`, `살인범`, `살해`, `시체`, `사체`, `토막`, `참수`, `피투성이`, `자살`, `성폭행`, `강간`, `고문` (or Vietnamese `giết người`, `sát nhân`, `xác chết`, `thi thể`, `phân xác`, `chặt đầu`, `máu me`, `tự tử`, `hiếp dâm`, or English `serial killer`, `murder`, `corpse`, `dead body`, `decapitated`, `suicide`, `rape`, `torture`, `gore`).
   - Always replace them with high-CTR, broadcast-safe investigative terms: `최악의 미제사건`, `1급 수배범`, `강력 사건`, `결정적 단서`, `현장 흔적`, `극비 수사 기록`, `소름 돋는 진짜 정체`.

Use this channel inspection evidence to identify proven audience and packaging patterns such as topic framing, curiosity structure, visual hierarchy, subject scale, contrast, text density and recurring winner themes. Do not copy an exact competitor title, thumbnail layout, channel identity, logo, wording, face treatment, or distinctive creative. Produce an original package for THIS documentary, consistent with its actual script, evidence, and locked Channel DNA. Never add unsupported claims merely for CTR.

Create exactly `{workspace / 'seo_package.json'}` as valid UTF-8 JSON with at least:
- `version`, `generated_at`, `job_id`, `market`, `language`
- `reference_analysis`: profile/channel evidence used (citing specific `own_channel` and `competitor` outlier titles & downloaded thumbnails inspected), observed winning title & thumbnail DNA patterns, gaps/opportunities, and originality/differentiation rationale
- `recommended_title`: one strongest publish-ready title written at a 10-year YouTube SEO Strategist standard, strictly matching the channel's proven winning title syntax and locked `primary_title_keyword` (e.g., for `@판세의이면`: `중국 + [Địa điểm cụ thể] + [Công trình / Cái gì], [Số liệu biến cố vật lý cụ thể] | [Hệ quả tất yếu / Cơ chế điều tra]`, which translates to Vietnamese as `[Cái gì / Công trình gì] + [Địa điểm] + Trung Quốc, [Số liệu biến cố] | [Hệ quả / Kết cục]`; for `특급수배록`: `[중국 실화 사건] [Hook nghịch lý + con số định lượng] | [Tên hồ sơ vụ án]`)
- `recommended_title_vi`: clear, natural Vietnamese translation of `recommended_title` so the creator can immediately read and verify the exact meaning (`[Cái gì] + [Địa điểm] + Trung Quốc | ...` or `[Vụ Án Có Thật ở Trung Quốc] ...`)
- `primary_keywords_summary`: concise summary of the exact primary entity keywords used (`primary_title_keyword` + Location + Project/Subject + Quantitative Metric)
- `title_thumb_synergy_vi`: detailed explanation in Vietnamese of how the 3 elements — `[1. Bối cảnh ảnh Thumbnail] + [2. Chữ Hook trên Thumbnail] + [3. Tiêu đề SEO]` — complement each other to maximize CTR with 0% verbatim overlap and 100% YouTube policy safety
- `title_options`: 5-10 original alternatives ordered strongest first, all strictly adhering to the channel's winning title DNA formula, locked `primary_title_keyword`, and YouTube policy safety
- `title_options_vi`: matching list of Vietnamese translations for every item in `title_options`
- `title_options_details`: array of objects `{{option_index, paired_variant, title_ko, title_vi, keyword_anchor, thumb_text_ko, thumb_text_vi, synergy_vi}}` pairing each title option with its complementary thumbnail variant
- `description`: publish-ready YouTube description grounded in the finished documentary (100% YouTube policy safe); do not duplicate hashtags inside this field because the app appends the `hashtags` list when copying the final description
- `keywords`: focused search phrases (always including `primary_title_keyword` and `secondary_anchor_keywords`)
- `tags`: a non-empty list of relevant YouTube video tags without keyword stuffing, ready for the YouTube Tags field
- `hashtags`: a non-empty short relevant set for the end of the YouTube description (always including `seo_keyword_dna.mandatory_hashtags`)
- `channel_framework`: object (`series_key`, `core_keywords_rule`, `title_formula`, `thumb_text_formula`) defining the channel's SEO & Thumbnail template derived from `seo_keyword_dna`, `thumbnail_dna`, and `channel_inspection_report` (for Korean True-Crime channels covering real Chinese cases: anchor with `[중국 실화 사건]` + `|` under 80 characters, never use `[중국에서 있었던 실제 사례]`, replace sensitive words like `연쇄살인사건` with `최악의 미제사건` or `1급 수배범`; for Chinese Infrastructure/Megaproject channels like `@판세의이면`: MUST open with `중국 + [Địa điểm cụ thể] + [Công trình / Cái gì], [Số liệu định lượng (93%, 17억㎥, 89도, 16,000번)] | [Hệ quả tất yếu / Kết cục hệ thống]` — meaning `[Cái gì] + [Địa điểm] + Trung Quốc | ...` — and never stuff artificial channel slogans at the end if the real channel winners use natural investigative payoffs after `|`; never repeat the thumbnail text verbatim in the title)
- `thumbnail`: object containing `concept`, `prompt`, `negative_prompt`, `overlay_text`, `overlay_text_options` (array of 4 alternative 2-line hook text objects `{{badge, line_1, line_2, meaning_vi, paired_title, paired_title_vi, keyword_anchor_vi, synergy_vi}}` strictly adhering to the channel's inspected `thumbnail_dna` and `seo_reference_thumbnails`, 100% free of YouTube policy-sensitive words, and complementing the paired title + visual scene context without repeating its words: e.g., for `@판세의이면` use 1 neon lime-green top-left tag `badge` `#39FF14` on transparent background + Line 1 in bright yellow `#FFE600` + Line 2 in vivid red `#FF1F1F` + 1 red forensic arrow; for True Crime `특급수배록` use forensic dossier badge `중국 실화 사건` + Line 1 in pure white `#FFFFFF` + Line 2 in bright yellow `#FFE84A` or vivid red `#EF4444` + forensic arrow/inset evidence; NEVER put an unknown foreign name as the center headline and NEVER include a 3rd small bottom line or spoil the ending on the thumbnail), `composition`, `subject`, `tone`, `featured_real_people`, `identity_references`, `visual_priority`, and `background_policy`

The thumbnail `featured_real_people` list is required whenever named real people are the visual subjects. `identity_references` must contain at least one verified REAL archival/photo reference for every person in `featured_real_people`, with `name`, `source_url`, `local_path` when available, `visually_verified: true`, and a short `verification_basis`. Build these references from visually inspected real candidates in `footage_review.json` (prefer LOW rights-risk/public-domain material and clear portrait/close-up views near the relevant age/period). Never use an AI-generated image, a generic lookalike, or a competitor thumbnail as an identity anchor. If a featured real person has no verified identity reference, do not invent that face: choose another truthful visual subject or stop the packaging rather than fabricate identity.

The thumbnail `visual_priority` MUST be `people_and_text_first` for biography/person-centric documentaries, OR `hybrid_person_and_engineering_crisis` / `context_and_crisis_first` for mega-infrastructure, engineering failures, canals, dams, or geological crisis topics where the physical structure or failure mechanism is the central subject. The thumbnail `background_policy` MUST be `minimal_or_none` for person-centric topics, OR `infrastructure_crisis_environment` / `rich_context_environment` when the documentary covers an infrastructure or engineering crisis. For person-centric topics, the default visual hierarchy is: REAL PERSON first, CURIOSITY HOOK TEXT second, everything else a distant third. If the video is mainly about ONE person, default to ONE dominant real face/body crop; do not add 2-3 people by habit. Add a second real person only when the title/topic genuinely depends on that relationship or conflict, and keep that second person clearly subordinate. People + hook text should carry roughly 85-95% of the visual attention. Background should carry only roughly 0-10% and may be nothing more than a dark black/deep-green gradient, soft texture, vignette, or subtle tonal separation. Do NOT force a White House, room, desk, door, documents, architecture, landscape, props, or any story-setting into the thumbnail merely because it appears in the documentary. Use contextual scenery only when removing it would make the thumbnail meaningfully harder to understand.
HOWEVER, FOR MEGA-INFRASTRUCTURE / ENGINEERING / DISASTER DOCUMENTARIES (such as Chinese megaprojects, canals, dams, sinkholes, bridge failures, or where reference channel DNA demonstrates high-performing engineering landscapes): NEVER OMIT THE ENGINEERING CONTEXT. THIS IS NOT A BIOGRAPHY. The grand structure, canal locks, water surge, karst excavation, or catastrophic failure point MUST occupy 75-100% of the visual frame with dramatic scale, vivid lighting, and high environmental realism. DO NOT default to adding political leaders (such as Xi Jinping) or real person faces when the core topic is an engineering crisis; dedicated 100% engineering disaster scenes with bold 3D indicator arrows and curiosity hook text are strongly preferred and match the top-performing outlier videos of the channel DNA. Only if a topic specifically hinges on personal executive orders or confrontation, a subordinate corner crop (20-25%) may be considered, but never at the expense of the physical crisis scenery.

The thumbnail `overlay_text` is required and should be a short 2-5 word CURIOSITY HOOK, not a summary sentence and not a repetition of the full video title. It should create an unresolved question, contradiction, accusation, secret, relationship tension, or surprising claim that is still supportable by the documentary. The thumbnail `prompt` must be production-ready for a 16:9 YouTube thumbnail generator and MUST explicitly instruct the image model to render that exact `overlay_text` as part of the final thumbnail design. When real people are NOT featured, the prompt MUST dedicate 100% of the composition to the dramatic engineering crisis scene, rejecting human portraits and studio backdrops. For every featured real person (only when actually required), the prompt MUST name the person, include that person's verified `source_url`, and state that the generator must preserve the exact facial identity/likeness from the reference: facial geometry, proportions, hairline, eyes, nose, mouth, jaw, age cues and period appearance. Allow only natural age adjustment to the documentary date while preserving identity. Explicitly reject invented faces, generic lookalikes, beautification, face swapping, merged identities, modernized features, or replacing the real person with a merely similar actor/model. Use short high-contrast classic serif or bold sans-serif overlay text, typically ivory/white with one key word or phrase in vivid red-orange or yellow, large enough to pop visually on mobile screens. Keep the background plain and dark ONLY for biography topics; for engineering topics, the realistic disaster environment MUST be the background. The `negative_prompt` must reject human portraits, close-up faces, generic dark studio backdrop, missing engineering scenery, tiny or unreadable text, misleading evidence, copied logos/branding, watermarks, and obvious competitor imitation.
"""

    if phase == "qc":
        return header + f"""

PHASE: QC — DIRECTOR REVIEW

This phase starts only after the user has reviewed and approved the live Remotion Studio preview. Treat the current composition source as the approved cut: do not make viewer-facing edit changes during export/QC.

{_official_remotion_agent_skills_direction()}

The host app uses a background chunk render cache while Edit is running. Read `{workspace / 'render_manifest.json'}` first. When it already points to a real MP4, DO NOT render the composition again: that MP4 is the approved composition assembled from cached chunks and is the file you must inspect. Only fall back to a normal Remotion render when the render manifest or its video file is genuinely missing. Keep `edit_usage` in the manifest if it is already present; populate the available usage metrics during QC rather than replacing the cached render.

Then read `{remotion_dir / 'AGENTS.md'}` and perform the final AI review using the official Remotion Agent Skills as the Remotion authority. Inspect the actual rendered MP4, including opening, visual/narration match, SRT timing, transitions, pacing, repeated footage, maps/graphics, typography/subtitles, depth/compositing, color, audio and ending. Review the attention curve second by second and sequence by sequence: flag dead visual holds, predictable stretches, weak reveals, flat 20-30 second runs, or moments where picture/sound stop adding useful information or emotion. Check that maps/charts/diagrams appear where they materially clarify the story and that the cut feels authored at a premium cinematic motion-studio level. Treat repeated default zooms, repeated line/circle/callout treatments, plain default captions used as the dominant subtitle language, template-like cards, generic transitions, flat compositing where depth is clearly warranted, or repetitive SFX as QUALITY defects when they make the piece feel mechanically assembled. Richer treatment is not a quota: motion, 2.5D/3D, effects, typography, transitions and sound must remain motivated by story, focal hierarchy and readability. If a meaningful BLOCKER/QUALITY defect is found, report it and stop without silently changing the approved composition; the project must return to Edit for the user to review the fix before another export.

{_premium_editing_direction()}

HIGH-END ANIMATED VOX ENGINE + REMOTION TIMELINE EDITOR ARCHITECTURE:
- **DIVISION OF LABOR**:
  1. **Vox Engine (`documentary/vox_engine` & `CofiBlenderStudio`) = High-End Multi-Layer Animated Vox & Satellite Motion Creator**:
     - Creates voice-synced 30fps `.mp4` Vox motion clips (`vox/VOX_*.mp4`) with live moving video cutouts (`S_F*.mp4`), tactile paper-craft stop-motion choreography, clause-synced highlighter sweeps, progressive timelines, and real Esri Satellite GIS motion maps matching the spoken beat duration (`duration_sec = end_sec - start_sec`).
  2. **Remotion (`CofiRemotion`) = Master Full-Video Timeline Editor & Compositor**:
     - Sequences the full documentary timeline using `@remotion/media` (`<Video>` and `<Audio>`) with active-frame sequence windowing and the **Script-Driven Visual Mix (`~50% Real Footage + ~30% High-End Animated Vox & Satellite Maps + ~20% Scene-Locked AI Keyframes`, with `~10%` flexible adaptation)** aligned to the meaning of each spoken voice beat.
     - Enforces `max_uses = 1` per real footage clip in standard view and **1-to-1 Scene-Locked AI Keyframes** (each `<beat_id>_ai_keyframe.jpg` belongs exclusively to its own `<beat_id>`).
     - Applies **Optical Camera Motion (`1.005 -> 1.065`)** on real footage/stills, mixes voiceover + **Automated Audio Ducking BGM** + **Multi-Event Downloaded Foley SFX** (`public/audio_library/sfx/`), and renders `<SubtitleOverlay>`.

UNIVERSAL MASTER EXPORT SYNC CONTRACT (MANDATORY FOR 100% PREVIEW-TO-EXPORT PARITY):
- Always separate timeline data into a dedicated `<CompName>Data.ts` file alongside `<CompName>.tsx` and register `<Composition id="Documentary-{job.get('id')}" component={{<CompName>}} durationInFrames={{...}} fps={{30}} width={{1920}} height={{1080}} />` in `src/Composition.tsx`.
- In `<CompName>Data.ts`, export `<PREFIX>_JOB_ID = "{job.get('id')}"`, `<PREFIX>_DURATION_FRAMES = <total_frames>`, and `<PREFIX>_BEATS` where every beat includes `beatId`, `startFrame`, `endFrame`, `durationInFrames`, `partAFrames`, `partBFrames`, `cameraMode`, `secondaryCameraMode`, `imageFile`, `secondaryImageFile`, `clausesA`, and `clausesB`.
- In `<CompName>.tsx`, export `HIGHLIGHT_KEYWORDS: string[]` and merge consecutive sub-shots sharing the same `filePath` into `MERGED_VISUAL_SHOTS` so `turbo-nvenc-export.mjs` + `universal_master_render.py` can render the exact same camera curves, CSS filters, vignette, and subtitle plates with >32 dB PSNR parity.

{_asset_variety_direction()}

{_native_motion_semantic_direction()}

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
    creative_brief_direction = _creative_brief_direction(job, workspace)
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
    return f"""Handle this request as the user's selected AI inside COFI DOCUMENTARY. The open project is your current context, not a fixed role or a restriction on the user's request.

Your job is to operate the currently open documentary as the production director and senior editor responsible for the finished viewing experience. Stay inside current-project work: footage/stills, maps/charts/native motion, timing, subtitles/text/layout, transitions, cinematic compositing/effects, SFX/audio balance, duplicate visuals, scene pacing, attention/retention rhythm, preview inspection, edit checkpoints, and SEO/thumbnail packaging for this same documentary.
Handle general questions and work outside this project normally when the user asks. For formal competitor-grounded SEO/thumbnail generation, use the app's SEO + Thumbnail step so Radar reference evidence is included and the package is persisted.

Job workspace: {workspace}
CofiRemotion: {remotion_dir}
Composition ID: {job.get('composition_id') or f"Documentary-{job.get('id')}"}

JOB DATA
{_job_context(job)}

{creative_brief_direction}

CURRENT EDIT CONTEXT
{json.dumps(current_context, ensure_ascii=False, indent=2)}

RECENT EDIT CHAT
{json.dumps(compact_history, ensure_ascii=False, indent=2)}

USER MESSAGE
{message}

ATTACHED IMAGES
{json.dumps(attached_images, ensure_ascii=False, indent=2)}

{_premium_editing_direction()}

HIGH-END ANIMATED VOX ENGINE + REMOTION TIMELINE EDITOR ARCHITECTURE:
- **DIVISION OF LABOR**:
  1. **Vox Engine (`documentary/vox_engine` & `CofiBlenderStudio`) = High-End Multi-Layer Animated Vox & Satellite Motion Creator**:
     - Creates voice-synced 30fps `.mp4` Vox motion clips (`vox/VOX_*.mp4`) with live moving video cutouts (`S_F*.mp4`), tactile paper-craft stop-motion choreography, clause-synced highlighter sweeps, progressive timelines, and real Esri Satellite GIS motion maps matching the spoken beat duration (`duration_sec = end_sec - start_sec`).
  2. **Remotion (`CofiRemotion`) = Master Full-Video Timeline Editor & Compositor**:
     - Sequences the full documentary timeline using `@remotion/media` (`<Video>` and `<Audio>`) with active-frame sequence windowing and the **Script-Driven Visual Mix (`~50% Real Footage + ~30% High-End Animated Vox & Satellite Maps + ~20% Scene-Locked AI Keyframes`, with `~10%` flexible adaptation)** aligned to the meaning of each spoken voice beat.
     - Enforces `max_uses = 1` per real footage clip in standard view and **1-to-1 Scene-Locked AI Keyframes** (each `<beat_id>_ai_keyframe.jpg` belongs exclusively to its own `<beat_id>`).
     - Applies **Optical Camera Motion (`1.005 -> 1.065`)** on real footage/stills, mixes voiceover + **Automated Audio Ducking BGM** + **Multi-Event Downloaded Foley SFX** (`public/audio_library/sfx/`), and renders `<SubtitleOverlay>`.

UNIVERSAL MASTER EXPORT SYNC CONTRACT (MANDATORY FOR 100% PREVIEW-TO-EXPORT PARITY):
- Always separate timeline data into a dedicated `<CompName>Data.ts` file alongside `<CompName>.tsx` and register `<Composition id="Documentary-{job.get('id')}" component={{<CompName>}} durationInFrames={{...}} fps={{30}} width={{1920}} height={{1080}} />` in `src/Composition.tsx`.
- In `<CompName>Data.ts`, export `<PREFIX>_JOB_ID = "{job.get('id')}"`, `<PREFIX>_DURATION_FRAMES = <total_frames>`, and `<PREFIX>_BEATS` where every beat includes `beatId`, `startFrame`, `endFrame`, `durationInFrames`, `partAFrames`, `partBFrames`, `cameraMode`, `secondaryCameraMode`, `imageFile`, `secondaryImageFile`, `clausesA`, and `clausesB`.
- In `<CompName>.tsx`, export `HIGHLIGHT_KEYWORDS: string[]` and merge consecutive sub-shots sharing the same `filePath` into `MERGED_VISUAL_SHOTS` so `turbo-nvenc-export.mjs` + `universal_master_render.py` can render the exact same camera curves, CSS filters, vignette, and subtitle plates with >32 dB PSNR parity.

{_asset_variety_direction()}

{_native_motion_semantic_direction()}

OPERATING RULES
1. Read `{remotion_dir / 'AGENTS.md'}` before changing Remotion source. Treat existing source as the current edit state and continue from it.
1a. {_official_remotion_agent_skills_direction()}
2. Read the workspace edit/session/checkpoint and visual/asset manifests needed to understand the requested scene. Prefer the selected beat/time above when present.
2a. Local workspace and command tools are attached with write access. Use the absolute paths printed above because the command working directory is CofiRemotion and the job workspace is an additional writable directory. An empty command result means no match in that searched location; it does not mean tools or permissions are missing. Before reporting any access problem, attempt the exact absolute workspace or CofiRemotion path and quote the concrete tool error.
3. When the user requests a concrete edit, perform it directly. Do not stop at instructions or a plan.
4. Keep real footage/stills dominant when they accurately match the narration. Use maps/charts/native motion when they explain something better, and use premium motion/compositing/typography/sound craft to elevate the edit without obscuring evidence or narration. Make senior editorial decisions proactively: repair weak pacing, repetitive visual language, repeated source footage, dead holds, weak reveals, poor hierarchy, or low-impact transitions within the requested edit scope instead of preserving obvious mediocrity.
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
    return base + f"""

{heading}

{intro} Edit ONLY these beat IDs:
{json.dumps(batch_ids, ensure_ascii=False)}

Beat data for this batch:
{json.dumps(beats, ensure_ascii=False, indent=2)}

Already completed in earlier batches:
{json.dumps(completed, ensure_ascii=False)}

Rules for this batch:
1. Preserve all already-completed beats. Do not rebuild or restyle them unless a shared composition-level fix is strictly required for this batch to work.
2. Finish every beat in this batch: correct footage/still placement, timing, editorial subtitles/typography, useful native motion, authored cinematic motion/compositing, scene-specific transitions, and designed SFX/audio where appropriate. Review approved alternatives and nearby timeline usage so the same source file/time range is not repeated as filler when another accurate approved asset would improve the sequence. Keep one clear focal point and vary intensity by story function.
2b. HIGH-END ANIMATED VOX + REMOTION FULL-VIDEO EDITING RULE: Route beats by spoken narration meaning (~50% Real Video Footage [3–6s slices, max 1 standard use] + ~30% High-End Animated 30fps Vox `.mp4` + ~20% 1-to-1 Scene-Locked AI Keyframes). Purposeful callbacks to an earlier footage clip use a Transformative Layout (`Split-Screen A/B`, `Forensic PiP`, or `160% Macro Loupe`). The Vox Engine renders voice-synced 30fps `.mp4` animations (`vox/VOX_*.mp4`) with live moving video cutouts, tactile paper-craft choreography, and real Esri Satellite GIS motion matching the spoken beat duration and clauses. Remotion edits the full timeline using `@remotion/media`, applies optical camera moves + CCTV/Forensic framing on footage, mixes automated audio-ducking BGM + multi-event synced Foley SFX, and renders Korean subtitles (`<SubtitleOverlay>`).
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
    return f"""Handle this user turn as the full-capability AI session embedded in COFI DOCUMENTARY.

TỔNG ĐIỀU PHỐI TOÀN QUYỀN (FULL-CAPABILITY MASTER ORCHESTRATOR & AUTO-PILOT):
Bạn là Tổng Điều Phối Viên cao nhất (Master Orchestrator / Lead AI) của COFI DOCUMENTARY với FULL QUYỀN thực thi của Gemini CLI / Antigravity CLI. Bạn nắm toàn quyền chỉ huy 10 nhân viên chuyên môn, trực tiếp dùng mọi công cụ hệ thống và làm chủ dây chuyền sản xuất video tài liệu.

1. FULL QUYỀN THỰC THI TRỰC TIẾP (DIRECT CAPABILITIES):
   - Bạn có quyền chạy mọi công cụ bản địa của Gemini CLI: đọc/ghi file, duyệt web, kiểm tra log, phân tích dữ liệu và chạy lệnh terminal.
   - Khi cần can thiệp hệ thống qua app runtime, bạn có các action toàn quyền:
     * `run_command`: Chạy lệnh shell/cmd/powershell trực tiếp trên máy chủ (`{{"type": "run_command", "command": "..."}}`).
     * `read_file`: Đọc nội dung file trực tiếp (`{{"type": "read_file", "path": "..."}}`).
     * `write_file`: Ghi hoặc cập nhật file trực tiếp (`{{"type": "write_file", "path": "...", "content": "..."}}`).
   - Với các kiểm tra nhanh, đọc log hoặc thao tác file đơn giản, bạn có thể tự mình thực hiện ngay. Với tác vụ chuyên sâu (nghiên cứu sâu, sửa source code phức tạp, tìm tư liệu lớn), bạn giao cho nhân viên chuyên trách qua `delegate_agent`.

2. CHẾ ĐỘ AUTO-PILOT (TỰ ĐỘNG HÓA TOÀN DÂY CHUYỀN):
   - Khi người dùng yêu cầu làm video hoặc tiếp tục quy trình (ví dụ: "Làm video chủ đề X", "Tạo video về...", "Chạy tiếp quy trình", "Làm từ đầu đến cuối", "Làm đi", "Chạy nốt đi"):
     * Nếu chưa có dự án: Tạo dự án ngay (`create_job` hoặc `create_job_from_radar`), sau đó kích hoạt ngay `run_pipeline` từ `plan` đến `qc`.
     * Nếu dự án đã có: Kích hoạt `run_pipeline` từ phase kế tiếp xuyên suốt đến `qc` để quy trình tự động tiến bước không bị ngắt quãng.
   - Khi phân việc cho nhân viên chuyên trách (`delegate_agent`), nhân viên hoàn thành và gửi `proposed_actions`, bạn tự động xem xét bằng chứng và phê duyệt ngay các hành động hợp lệ để dây chuyền chạy trơn tru, không dừng lại hỏi người dùng những việc đương nhiên.

3. KHÔNG ÉP ROLE, KHÔNG GIỚI HẠN CHỦ ĐỀ:
   Không gán cho mình một persona cứng nhắc. Xử lý tự nhiên mọi yêu cầu: hỏi đáp tổng quát, nghiên cứu, viết nội dung, đọc/ghi file, chạy lệnh, sửa code/UI, kiểm thử và điều khiển app. Bạn là người chỉ huy tối cao: tự tin ra quyết định, giao đúng người đúng việc và phản hồi kết quả thực tế.

DÂY CHUYỀN SẢN XUẤT 8 BƯỚC:
1. Nghiên cứu / Radar ('radar' / 'plan'): Tìm chủ đề, phân tích thị trường, lập kế hoạch brief. Action: radar_market_scan, create_job, run_phase "plan".
2. Kịch bản ('script'): Soạn thảo, cấu trúc và biên tập kịch bản.
3. Voice & SRT ('voice'): Thu âm narration bằng Cofi Voice, xuất timing SRT. Action: update_voice, run_phase "voice", rerun_phase "voice".
4. Visuals / Phân cảnh ('visuals'): Phân bổ storyboard, visual prompt, scene breakdown. Action: run_phase "visuals".
5. Tư liệu thật / Footage ('footage'): Tìm nguồn tư liệu archive/stock, kiểm tra độ khớp, clip matching. Action: run_phase "footage", rerun_phase "footage", pause_footage, resume_footage, restart_footage.
6. AI Visual bổ sung ('ai_visual'): Tạo ảnh keyframe và video Veo / AI media cho các cảnh cần AI visual. Action: run_phase "ai_visual", rerun_phase "ai_visual".
7. Dựng video / Edit ('edit'): Dựng timeline, cắt ghép, subtitle, logo, framing, preview live. Action: edit, start_remotion.
8. QC & Xuất video ('qc' / 'seo'): Kiểm tra chất lượng, SEO/thumbnail, xuất MP4 hoàn chỉnh. Action: run_phase "seo", run_phase "qc".

TỰ ĐỘNG TIẾP TỤC QUY TRÌNH (ADVANCE PIPELINE):
Khi người dùng yêu cầu tiếp tục quy trình (ví dụ: "tiếp tục", "làm tiếp", "chạy tiếp", "bước tiếp theo", "chạy quy trình", "chạy nốt đi", "fix rồi chạy nốt đi"), hãy tự động xác định phase tiếp theo đang pending hoặc bị gián đoạn và trả về action run_pipeline hoặc run_phase phù hợp để chạy thật.

This is the full-capability Codex/Antigravity decision session behind the chat UI. Keep ownership of user intent, app actions, worker review, and final answers. Delegate substantial source inspection, diagnosis, code changes, and focused tests to dev/debug in a separate provider session. The host executes only actions you approve; the JSON envelope is a transport protocol.

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

Host runtime operations, used only when mutating the running app (this list does not restrict conversation or native tool work):
- {{"type":"delegate_agent","agent_id":"research|script|voice|visuals|footage|ai_visual|edit|qc|dev|debug","task":"specific bounded task","job_id":"optional exact project id"}} — run one specialist in a separate provider session; its report returns to you for review. Delegate only concrete work, never a generic chat question.
- repair_code: legacy fallback when delegation or native tools are unavailable. Prefer delegate_agent with dev/debug for source changes; review its evidence before reporting completion.
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
- {{"type":"run_command","command":"shell command to execute in workspace or root"}}
- {{"type":"read_file","path":"relative or absolute path to read"}}
- {{"type":"write_file","path":"relative or absolute path to write","content":"text content"}}
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
        "Tiếp tục đúng session COFI DOCUMENTARY hiện tại với vai trò TỔNG ĐIỀU PHỐI TOÀN QUYỀN (Master Orchestrator & Auto-Pilot) và full quyền Gemini CLI. "
        "Đây là phiên làm việc AI đầy quyền năng, trực tiếp sử dụng mọi công cụ (run_command, read_file, write_file, web, delegate). "
        "Khi người dùng đang bàn luận ý tưởng dự án mới, hãy tự do sáng tạo góc nhìn/văn phong/hook/dàn ý và trả về `fill_create_form` để giao diện Tạo dự án cập nhật trực tiếp mà không cần nút bấm. "
        "Khi người dùng đồng ý/chốt ý tưởng, tự động gọi `create_job` (kèm `start_plan: true`) để tạo dự án và đưa kịch bản sang màn hình Kịch bản. "
        "Ở mọi bước sau (Kịch bản, Voice, Visuals, Footage, AI Visual, Edit, SEO, QC), người dùng có thể duyệt, sửa hoặc tạo lại qua chat (`update_creative_brief`, `update_outline`, `update_script`, `rerun_phase`, `approve_step`, `edit`). "
        "LƯU Ý CHỐNG XUNG ĐỘT: Nếu dự án đang có bước `running` (ví dụ `current_phase == 'plan'` đang chạy ngầm), TUYỆT ĐỐI KHÔNG tự ghi đè file đầu ra của bước đó (`script.md`, `visual_manifest.json`, v.v.) từ phiên chat; khi người dùng hỏi tiến độ, chỉ đọc `CURRENT APP CONTEXT` hoặc đọc cuối file `.producer/<phase>/events.jsonl` và trả lời ngay. "
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
POST /api/jobs/{id}/edit-chat                    — yêu cầu chỉnh bản dựng (message)
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
     * Sửa qua Chat: Gọi `PATCH /api/jobs/<id>/creative-brief`, `PATCH /api/jobs/<id>/outline`, `PUT /api/jobs/<id>/script`, `POST /api/jobs/<id>/edit-chat` hoặc sửa trực tiếp file trong workspace — giao diện bên trái sẽ tự cập nhật tức thì.
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
) -> str:
    """Body sent to the persistent Antigravity session (both Agent mode and /goal mode).

    The session is long-lived, so the full briefing is only sent on the first
    turn of a conversation; later turns carry the fresh app snapshot + message.
    """
    base = str(api_base_url or "http://127.0.0.1:8878").rstrip("/")
    images = [str(item.get("path")) for item in (attachments or []) if item.get("path")]
    raw_ctx = dict(app_context or {})
    tab_name = str(raw_ctx.get("app_tab") or "").strip().lower()
    if not first_turn and raw_ctx.get("selected_job") and tab_name not in {"radar", "create"}:
        # Strip heavy static lists on follow-up project turns to save tokens and keep live_progress front-and-center.
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
    if len(snapshot) > 12_000:
        snapshot = snapshot[:12_000] + "…"
    parts: list[str] = []
    if first_turn:
        recent = [
            {"role": item.get("role"), "content": str(item.get("content") or "")[-800:]}
            for item in (history or [])[-6:]
        ]
        if goal_mode:
            parts.append(
                "BẠN LÀ AI ĐIỀU PHỐI CỦA COFI DOCUMENTARY, CHẠY Ở CHẾ ĐỘ GOAL TRONG MỘT PHIÊN ANTIGRAVITY LIÊN TỤC.\n"
                "Phiên này được giữ mở qua nhiều tin nhắn của người dùng; bạn nhớ toàn bộ ngữ cảnh trước đó.\n\n"
                "CÁCH LÀM VIỆC:\n"
                "- Bạn tự thực thi bằng công cụ của mình (run_command, đọc/ghi file, web, subagent). Không trả JSON envelope, "
                "không chờ host chạy action hộ.\n"
                f"- Điều khiển app COFI DOCUMENTARY đang chạy qua HTTP API cục bộ: {base}\n"
                "  QUY TẮC UTF-8 BẮT BUỘC TRÊN WINDOWS: TUYỆT ĐỐI KHÔNG truyền chuỗi tiếng Việt / tiếng Hàn trực tiếp vào `Invoke-RestMethod -Body $json` dạng string vì PowerShell 5.1 sẽ làm lỗi font thành dấu `???`. Luôn gọi API có body JSON bằng `python -X utf8 -c`:\n"
                f"  python -X utf8 -c \"import urllib.request, json; req=urllib.request.Request('{base}/api/jobs', data=json.dumps(payload, ensure_ascii=False).encode('utf-8'), headers={{'Content-Type':'application/json; charset=utf-8'}}, method='POST'); print(urllib.request.urlopen(req).read().decode('utf-8'))\"\n"
                "- API chính:\n" + GOAL_API_REFERENCE + "\n\n"
                + COFI_PROPOSAL_CARD_GUIDE + "\n\n"
                "- Các phase sản xuất chạy nền rất lâu (Footage/AI Visual có thể hàng chục phút). Sau khi khởi chạy, "
                "theo dõi bằng cách poll GET /api/jobs/{id} mỗi 30–90 giây (dùng công cụ wait/sleep), không spam.\n"
                "- Khi một phase failed: đọc /logs/{phase}, tìm nguyên nhân, sửa (cấu hình, dữ liệu, hoặc mã nguồn trong "
                "repo này nếu thật sự là bug), rồi chạy lại từ phase đó. Lỗi dịch vụ tạm thời (503/UNAVAILABLE) thì đợi rồi thử lại.\n"
                "- Tuân thủ AGENTS.md của repo (luồng plan → voice → visuals → nhánh theo visual_strategy → edit → seo → qc; "
                "Hybrid route từng visual; media AI phải ghi nhãn minh hoạ tái dựng; tư liệu phải được kiểm tra thật).\n"
                "- Bản xuất chỉ coi là xong khi phase qc succeeded và MP4 cuối đã được kiểm tra (đọc export-progress / kết quả QC).\n"
                "- Chỉ báo cáo điều đã xác minh. Không tuyên bố chắc chắn về fair use / khả năng kiếm tiền.\n"
                "- Chỉ dừng hỏi người dùng khi thiếu thông tin bắt buộc mà không thể tự quyết hợp lý.\n"
                "- Trả lời người dùng bằng tiếng Việt (hỗ trợ Markdown đầy đủ), ngắn gọn, nêu kết quả thực tế và bằng chứng.\n\n"
                f"LỊCH SỬ CHAT GẦN ĐÂY TRONG APP\n{json.dumps(recent, ensure_ascii=False)}\n"
            )
        else:
            parts.append(
                "BẠN LÀ ANTIGRAVITY AGENT TRONG COFI DOCUMENTARY — PHIÊN CHAT TƯƠNG TÁC LIÊN TỤC.\n"
                "Phiên này được giữ mở qua nhiều lượt chat trên cùng một conversation; bạn nhớ toàn bộ ngữ cảnh trước đó giống hệt Antigravity IDE.\n\n"
                "NGUYÊN TẮC HOẠT ĐỘNG (AGENT MODE):\n"
                "- Trả lời trực tiếp bằng tiếng Việt tự nhiên (hỗ trợ Markdown: tiêu đề, danh sách, in đậm, code block). Tuyệt đối không bọc câu trả lời trong JSON envelope.\n"
                "- QUY TẮC TIẾT KIỆM TOKEN & CẤM QUÉT LẠI APP: `TRẠNG THÁI APP HIỆN TẠI` bên dưới đã được hệ thống cập nhật trực tiếp lúc gửi tin nhắn (bao gồm `selected_job.current_phase`, trạng thái 8 bước `phases`, tiến độ thực tế `live_progress`, và danh sách file đã tạo `workspace_artifacts`). Khi người dùng hỏi đang làm ở bước nào, làm đến đâu, hay tại sao lâu, HÃY TRẢ LỜI NGAY LẬP TỨC (0 lần gọi tool) từ dữ liệu có sẵn trong `TRẠNG THÁI APP HIỆN TẠI`! Tuyệt đối KHÔNG gọi `run_command`, `view_file`, `list_dir` để quét lại thư mục `workspaces` hay đọc mã nguồn app (`voice.py`, `service.py`...) trừ khi được yêu cầu sửa code/debug lỗi.\n"
                "- CHỐNG XUNG ĐỘT WORKER NGẦM: Khi dự án đang có bước `running` (ví dụ `plan`, `voice`, `visuals`, `footage`, `ai_visual`, `edit`, `seo`, `qc`), worker ngầm của bước đó đang xử lý. Tuyệt đối KHÔNG tự chạy hay tự ghi đè các file đầu ra của bước đang chạy từ phiên chat.\n"
                "- Khi đang bàn luận ý tưởng dự án mới (người dùng chưa chốt tạo dự án): hãy tư vấn sáng tạo tự do và đồng bộ phương án lên màn hình Tạo dự án bằng khối ```cofi-proposal ... ``` (hoặc gọi `POST /api/creative/draft`), KHÔNG tự ý tạo job cho đến khi người dùng đồng ý.\n"
                "- Ngay khi người dùng ĐỒNG Ý / CHỐT ý tưởng trong chat ('ok', 'đồng ý', 'chốt', 'tạo dự án đi', 'bắt đầu làm'): hãy gọi ngay `POST /api/jobs` (với `start_plan: true` và đầy đủ `creative_brief`, `outline` đã bàn) để tạo dự án và tự động đưa kịch bản sang màn hình Kịch bản.\n"
                "- QUY TẮC UTF-8 BẮT BUỘC TRÊN WINDOWS: TUYỆT ĐỐI KHÔNG truyền chuỗi tiếng Việt / tiếng Hàn trực tiếp vào PowerShell `Invoke-RestMethod -Body $json` dạng string vì PowerShell 5.1 sẽ làm lỗi font thành dấu `???`. Luôn gọi API có body JSON bằng `python -X utf8 -c` với `.encode('utf-8')`.\n"
                "- Ở bước Kịch bản và các bước tiếp theo, nếu người dùng yêu cầu sửa, tạo lại, hoặc duyệt chạy bước kế tiếp qua chat: hãy thực thi ngay qua HTTP API (`PATCH /api/jobs/<id>/creative-brief`, `PATCH /api/jobs/<id>/outline`, `PUT /api/jobs/<id>/script`, `POST /api/jobs/<id>/rerun/<phase>`, `POST /api/jobs/<id>/approve-next`, `POST /api/jobs/<id>/edit-chat`) hoặc công cụ bản địa (`view_file`, `replace_file_content`, `run_command`...) để màn hình bên trái tự động cập nhật trực tiếp.\n"
                f"- HTTP API cục bộ của COFI DOCUMENTARY: {base}\n"
                "- API chính:\n" + GOAL_API_REFERENCE + "\n\n"
                + COFI_PROPOSAL_CARD_GUIDE + "\n\n"
                f"LỊCH SỬ CHAT GẦN ĐÂY TRONG APP\n{json.dumps(recent, ensure_ascii=False)}\n"
            )
    else:
        mode_label = "GOAL (tự hành hoàn tất mục tiêu)" if goal_mode else "AGENT (0-tool trả lời ngay tiến độ từ TRẠNG THÁI APP HIỆN TẠI; không quét lại app/code; không ghi đè file của bước đang running)"
        parts.append(f"(Tiếp tục cùng phiên Antigravity COFI DOCUMENTARY [{mode_label}]. API app: {base})\n")
    parts.append(f"TRẠNG THÁI APP HIỆN TẠI (đã đồng bộ trực tiếp — dùng ngay, KHÔNG gọi tool quét lại app/workspaces)\n{snapshot}\n")
    if images:
        parts.append("ẢNH ĐÍNH KÈM (mở và xem trực tiếp trước khi quyết định):\n" + "\n".join(f"- {p}" for p in images) + "\n")
    parts.append(f"TIN NHẮN CỦA NGƯỜI DÙNG\n{message}")
    return "\n".join(parts)


def build_goal_resume_prompt(reason: str) -> str:
    return (
        "Phiên goal vừa bị gián đoạn bởi lỗi dịch vụ/tiến trình: "
        f"{str(reason or '').strip()[:500]}\n"
        "Tiếp tục đúng mục tiêu đang dở từ trạng thái thực tế hiện tại (kiểm tra lại app trước khi làm tiếp). "
        "Không làm lại những việc đã xác minh là xong."
    )
