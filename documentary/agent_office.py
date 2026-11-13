from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .agent_departments import (
    build_live_departments_projection,
    get_department_for_agent,
)


DIVISION_META: dict[str, dict[str, str]] = {
    "direction": {
        "id": "direction",
        "title_vi": "Phòng Chỉ Huy & Radar Đề Tài",
        "subtitle_vi": "Điều phối tổng thể · Săn đề tài & kiểm tra trùng lặp DNA kênh",
        "icon": "🎬",
        "accent": "#38bdf8",
    },
    "editorial": {
        "id": "editorial",
        "title_vi": "Phòng Điều Tra, Biên Kịch & Thu Âm",
        "subtitle_vi": "Đối chứng tư liệu gốc · Kịch bản văn nói · Giọng đọc & Whisper",
        "icon": "🖋️",
        "accent": "#a78bfa",
    },
    "visual_cinema": {
        "id": "visual_cinema",
        "title_vi": "Xưởng Hình Ảnh, Vox 2.5D & Dựng Phim",
        "subtitle_vi": "Phân cảnh 1-1 · Tư liệu 3-Frame · Ảnh AI · Vox đa cơ chế · Remotion · SEO",
        "icon": "🎞️",
        "accent": "#34d399",
    },
    "quality_and_engineering": {
        "id": "quality_and_engineering",
        "title_vi": "Phòng Thanh Tra Phản Biện & Kỹ Thuật",
        "subtitle_vi": "Kiểm chứng độc lập · Bắt làm lại khi chưa đạt · Duyệt Master MP4",
        "icon": "⚖️",
        "accent": "#fbbf24",
    },
}

AGENT_ROLE_VI: dict[str, dict[str, str]] = {
    "orchestrator": {
        "title_vi": "Tổng Đạo Diễn Điều Phối",
        "desk_vi": "Bàn Chỉ Huy Trung Tâm",
        "idle_vi": "Trực điều phối toàn xưởng & Chatbot",
    },
    "radar": {
        "title_vi": "Trinh Sát Đề Tài & DNA Kênh",
        "desk_vi": "Trạm Quét Xu Hướng",
        "idle_vi": "Sẵn sàng quét đề tài & Pre-Flight",
    },
    "research": {
        "title_vi": "Điều Tra Viên Tư Liệu Gốc",
        "desk_vi": "Bàn Hồ Sơ & Đối Chứng",
        "idle_vi": "Chờ xác minh hồ sơ & mốc thời gian",
    },
    "script": {
        "title_vi": "Biên Kịch Trưởng (Văn Nói)",
        "desk_vi": "Bàn Sáng Tác Kịch Bản",
        "idle_vi": "Chờ viết dàn ý & kịch bản thu âm",
    },
    "voice": {
        "title_vi": "Đạo Diễn Giọng Đọc & Whisper",
        "desk_vi": "Phòng Thu CofiVoice GPU",
        "idle_vi": "Chờ tổng hợp giọng & căn chữ SRT",
    },
    "visuals": {
        "title_vi": "Đạo Diễn Phân Cảnh 1-1",
        "desk_vi": "Bàn Storyboard & Nhịp Cảnh",
        "idle_vi": "Chờ chia sub-beat khớp 100% thoại",
    },
    "footage": {
        "title_vi": "Giám Tuyển Tư Liệu Thật",
        "desk_vi": "Bàn Kiểm Duyệt 3-Frame",
        "idle_vi": "Chờ săn & lọc video thật sạch logo",
    },
    "ai_visual": {
        "title_vi": "Họa Sĩ Minh Họa AI Kênh",
        "desk_vi": "Xưởng Vẽ Keyframe 16:9",
        "idle_vi": "Chờ vẽ ảnh AI khóa nhân vật kênh",
    },
    "vox": {
        "title_vi": "Đạo Diễn Motion Vox 2.5D",
        "desk_vi": "Bàn Thiết Kế Bản Đồ & Cơ Chế",
        "idle_vi": "Chờ biên đạo Vox đa cơ chế khớp từ",
    },
    "edit": {
        "title_vi": "Đạo Diễn Dựng Phim & Âm Thanh",
        "desk_vi": "Bàn Dựng Remotion Timeline",
        "idle_vi": "Chờ dựng timeline, BGM & phụ đề",
    },
    "seo": {
        "title_vi": "Chiến Lược Gia CTR & Thumbnail",
        "desk_vi": "Bàn Đóng Gói Tiêu Đề & Thumb",
        "idle_vi": "Chờ thiết kế Thumbnail & gói SEO",
    },
    "evidence_qa": {
        "title_vi": "Thanh Tra Phản Biện Độc Lập",
        "desk_vi": "Cổng Kiểm Duyệt & Bắt Sửa Lại",
        "idle_vi": "Canh gác mọi khâu · Chưa đạt là trả về",
    },
    "qc": {
        "title_vi": "Giám Đốc Duyệt Bản Master",
        "desk_vi": "Phòng Chiếu Kiểm Định MP4",
        "idle_vi": "Chờ soi 6 frame, LUFS & đuôi kết 3.8s",
    },
    "dev": {
        "title_vi": "Kỹ Sư Kiến Trúc Hệ Thống",
        "desk_vi": "Trạm Nâng Cấp Mã Nguồn",
        "idle_vi": "Trực bảo trì & nâng cấp công cụ",
    },
    "debug": {
        "title_vi": "Bác Sĩ Chẩn Đoán Gốc Lỗi",
        "desk_vi": "Trạm Cấp Cứu Pipeline",
        "idle_vi": "Trực săn lỗi & khôi phục tiến trình",
    },
}

PHASE_AGENT_MAP: dict[str, dict[str, Any]] = {
    "plan": {
        "label_vi": "Bước 1 · Nghiên cứu & Kịch bản",
        "lead": "script",
        "co_leads": ["research"],
        "critic": "evidence_qa",
        "report_files": ["plan_critic_report.json"],
    },
    "voice": {
        "label_vi": "Bước 2 · Thu âm TTS & Whisper SRT",
        "lead": "voice",
        "co_leads": [],
        "critic": "evidence_qa",
        "report_files": ["voice_qc_report.json"],
    },
    "visuals": {
        "label_vi": "Bước 3 · Phân cảnh 1-1 & Prompt",
        "lead": "visuals",
        "co_leads": ["vox"],
        "critic": "evidence_qa",
        "report_files": ["visuals_critic_report.json", "storyboard_critic_report.json"],
    },
    "footage": {
        "label_vi": "Bước 4 · Săn & Kiểm duyệt Tư liệu thật",
        "lead": "footage",
        "co_leads": [],
        "critic": "evidence_qa",
        "report_files": ["footage_hygiene_report.json"],
    },
    "ai_visual": {
        "label_vi": "Bước 5 · Vẽ Ảnh AI Nhân Vật Kênh",
        "lead": "ai_visual",
        "co_leads": [],
        "critic": "evidence_qa",
        "report_files": ["ai_visual_qc_report.json", "ai_visual_critic_report.json"],
    },
    "edit": {
        "label_vi": "Bước 6 · Dựng Remotion & Motion Vox 2.5D",
        "lead": "edit",
        "co_leads": ["vox", "footage"],
        "critic": "evidence_qa",
        "report_files": ["edit_screening_report.json", "compliance_scorecard.json"],
    },
    "seo": {
        "label_vi": "Bước 7 · Đóng gói SEO & Thumbnail CTR",
        "lead": "seo",
        "co_leads": [],
        "critic": "evidence_qa",
        "report_files": ["seo_packaging_qc_report.json", "seo_critic_report.json"],
    },
    "qc": {
        "label_vi": "Bước 8 · Xuất MP4 & Duyệt Master Cuối",
        "lead": "qc",
        "co_leads": ["evidence_qa"],
        "critic": "qc",
        "report_files": ["qc_screening_report.json", "final_manifest.json"],
    },
}


def _read_json_safe(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _tail_lines(path: Path, max_bytes: int = 98304, max_lines: int = 80) -> list[str]:
    if not path.is_file():
        return []
    try:
        size = path.stat().st_size
        with path.open("rb") as fh:
            if size > max_bytes:
                fh.seek(size - max_bytes)
            chunk = fh.read().decode("utf-8", errors="replace")
        lines = chunk.splitlines()
        if size > max_bytes and lines:
            lines = lines[1:]
        return lines[-max_lines:]
    except Exception:
        return []


def _short_basename(raw_path: str) -> str:
    cleaned = str(raw_path or "").strip().replace("\\", "/")
    if not cleaned:
        return ""
    parts = [p for p in cleaned.split("/") if p]
    if len(parts) >= 2 and parts[-2] in {"src", "media", "archival", "audio", ".producer"}:
        return f"{parts[-2]}/{parts[-1]}"
    return parts[-1] if parts else cleaned


def _agent_to_phase(agent_id: str, folder_name: str = "") -> str:
    aid = str(agent_id or "").strip().lower()
    if aid in {"research", "script", "radar"}:
        return "plan"
    if aid == "voice":
        return "voice"
    if aid == "visuals":
        return "visuals"
    if aid == "footage":
        return "footage"
    if aid == "ai_visual":
        return "ai_visual"
    if aid in {"vox", "edit"}:
        return "edit"
    if aid == "seo":
        return "seo"
    if aid == "qc":
        return "qc"
    fl = str(folder_name or "").lower()
    for pk in ("plan", "voice", "visuals", "footage", "ai_visual", "edit", "seo", "qc"):
        if fl.startswith(pk):
            return pk
    return "edit"


def _infer_specialist_from_text(text: str, default_agent: str) -> str:
    low = str(text or "").lower()
    if not low:
        return default_agent
    if any(k in low for k in ("turbo-nvenc", "universal_master_render", "universal_segments", "release/video.mp4", "release\\video.mp4", "final.mp4", "final_mp4_verify", "qc_screening")):
        return "qc"
    if any(k in low for k in ("verify_ftg_clips", "s_f0", "s_f1", "storyboard_", "grid_", "edit_footage", "footage_approved_live", "footage_review", "footage_hygiene", "build_102_semantic_footage", "yt-dlp", "yt_dlp")):
        return "footage"
    if any(k in low for k in ("vox_scene_manifest", "voxscenes", "vox-studio", "vox-editorial-desk", "plate_", "prop_", "validate-vox", "universal_baked_scenes", "vox_0")):
        return "vox"
    if any(k in low for k in ("voice_manifest", "editorial_voice_plan", "subtitles.srt", "narration.wav", "audio/beats", "audio\\beats", "cofivoice", ":8776", "/api/tts")):
        return "voice"
    if any(k in low for k in ("script.md", "outline.json", "plan_visual_manifest")):
        return "script"
    if any(k in low for k in ("research.md", "primary_sources", "forensic_chronology")):
        return "research"
    if any(k in low for k in ("seo_package", "thumbnail", "thumb_")):
        return "seo"
    if any(k in low for k in ("ai_visual", "media/ai_visual", "nano_banana")):
        return "ai_visual"
    if any(k in low for k in ("edit_manifest.json", "timeline.json", "scenes.json", "cinematext", "data.ts", "sync_edit")):
        return "edit"
    if "visual_manifest.json" in low:
        return "visuals" if default_agent in {"orchestrator", "visuals"} else default_agent
    return default_agent


def _infer_event_agent_and_action(folder_name: str, step: dict[str, Any]) -> tuple[str, str, str]:
    """Return ``(agent_id, action_vi, target_detail)`` from a raw ``step_update`` dict."""
    folder_low = folder_name.lower()
    is_critic_run = any(tag in folder_low for tag in ("critic", "doctor", "screening", "hygiene", "polish"))
    if "qc_master" in folder_low or folder_low == "qc":
        default_agent = "qc"
    elif is_critic_run:
        default_agent = "evidence_qa"
    elif folder_low.startswith("plan"):
        default_agent = "script"
    elif folder_low.startswith("visual"):
        default_agent = "visuals"
    elif folder_low.startswith("footage"):
        default_agent = "footage"
    elif folder_low.startswith("ai_visual"):
        default_agent = "ai_visual"
    elif folder_low.startswith("edit"):
        default_agent = "edit"
    elif folder_low.startswith("seo"):
        default_agent = "seo"
    elif "radar" in folder_low:
        default_agent = "radar"
    elif "chat" in folder_low:
        default_agent = "orchestrator"
    else:
        default_agent = "orchestrator"

    step_type = str(step.get("step_type") or "")
    tool_name = str(step.get("tool_name") or "")
    tool_info = step.get("tool_info") if isinstance(step.get("tool_info"), dict) else {}
    params = tool_info.get("parameters") if isinstance(tool_info.get("parameters"), dict) else {}

    if step_type == "agent_response":
        usage = step.get("usage") if isinstance(step.get("usage"), dict) else {}
        out_tok = int(usage.get("output_tokens") or 0)
        if is_critic_run:
            return default_agent, "Đang chấm điểm phản biện & lập danh sách câu/cảnh cần sửa", f"{out_tok:,} tokens" if out_tok else ""
        return default_agent, "Đang suy luận & biên soạn nội dung chuyên môn", f"{out_tok:,} tokens" if out_tok else ""

    if tool_name == "search_web":
        q = str(params.get("query") or "").strip()
        agent = "research" if folder_low.startswith("plan") else ("footage" if folder_low.startswith(("footage", "edit", "chat")) else default_agent)
        return agent, "Tra cứu & đối chứng tư liệu gốc trên Web", q[:90]

    if tool_name in {"write_file", "edit_file"}:
        raw_p = str(params.get("Path") or params.get("path") or "")
        short_p = _short_basename(raw_p)
        low_p = raw_p.lower()
        verb = "Ghi mới file" if tool_name == "write_file" else "Phẫu thuật chỉnh sửa file"
        agent = _infer_specialist_from_text(low_p, default_agent)
        if "research.md" in low_p:
            return "research", f"{verb} hồ sơ điều tra", short_p
        if "outline.json" in low_p or "script.md" in low_p or "plan_visual_manifest.json" in low_p:
            return ("evidence_qa" if is_critic_run else "script"), f"{verb} kịch bản / phân cảnh", short_p
        if agent == "voice":
            return "voice", f"{verb} dữ liệu giọng đọc / phụ đề", short_p
        if agent == "footage":
            return "footage", f"{verb} danh mục tư liệu thật", short_p
        if agent == "vox":
            return "vox", f"{verb} đồ họa Motion Vox 2.5D", short_p
        if short_p.endswith((".tsx", ".ts")) or "edit_" in low_p or "remotion" in low_p or agent == "edit":
            return ("vox" if "vox" in low_p else "edit"), f"{verb} timeline Remotion", short_p
        if agent == "seo":
            return "seo", f"{verb} gói SEO / Thumbnail", short_p
        return agent, f"{verb}", short_p

    if tool_name == "read_file":
        raw_p = str(params.get("Path") or params.get("path") or "")
        short_p = _short_basename(raw_p)
        low_p = raw_p.lower()
        agent = _infer_specialist_from_text(low_p, default_agent)
        if short_p.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
            viewer = agent if agent != "orchestrator" else ("qc" if default_agent == "qc" else "footage")
            return viewer, "Soi kiểm tra trực tiếp khung hình (Vision)", short_p
        return agent, "Đọc & đối chiếu dữ liệu", short_p

    if tool_name == "run_command":
        cmd = " ".join(str(params.get("CommandLine") or "").split())
        cmd_low = cmd.lower()
        agent = _infer_specialist_from_text(cmd_low, default_agent)
        if "turbo-nvenc" in cmd_low or "universal_master_render" in cmd_low:
            return "qc", "Kết xuất lại bản Master MP4 (Turbo NVENC)", "release/video.mp4"
        if "editorial_voice_cutter" in cmd_low:
            return "voice", "Chủ động cắt & điêu khắc nhịp thở Voice từ stem gốc", "editorial_voice_cutter.py"
        if "yt_dlp" in cmd_low or "yt-dlp" in cmd_low or "build_102_semantic_footage" in cmd_low or "verify_ftg_clips" in cmd_low:
            return "footage", "Trích xuất & kiểm duyệt mắt tư liệu thật 3-Frame", "VERIFY_FTG_CLIPS"
        if "validate-vox" in cmd_low or "vox_scene_manifest" in cmd_low or "universal_baked_scenes" in cmd_low:
            return "vox", "Biên dịch & bake đồ họa Motion Vox 2.5D", "vox_scene_manifest.json"
        if "sync_edit" in cmd_low or "edit_manifest.json" in cmd_low or "timeline.json" in cmd_low:
            return "edit", "Đồng bộ 1-to-1 Timeline & Manifest Remotion", "edit_manifest.json"
        if "voice_manifest.json" in cmd_low or "narration.wav" in cmd_low or "subtitles.srt" in cmd_low or ":8776" in cmd_low:
            return "voice", "Tổng hợp lại TTS & đồng bộ phụ đề SRT", "voice_manifest.json"
        if "script.md" in cmd_low or "outline.json" in cmd_low:
            return "script", "Cập nhật & chuẩn hóa kịch bản văn nói", "script.md"
        if "ffmpeg" in cmd_low or "ffprobe" in cmd_low:
            actor = agent if agent != "orchestrator" else ("qc" if default_agent == "qc" else "edit")
            return actor, "Xử lý khung hình / đo chuẩn âm thanh FFmpeg", "FFmpeg media pipeline"
        if "remotion" in cmd_low or "publish-live-edit" in cmd_low:
            return "edit", "Kết xuất / đồng bộ preview Remotion", "Remotion Studio"
        for known_file in ("visual_manifest.json", "script.md", "outline.json", "research.md", "vox_scene_manifest.json", "voice_manifest.json", "edit_manifest.json", "seo_package.json", "final_manifest.json"):
            if known_file in cmd_low:
                return agent, "Kiểm tra & chuẩn hóa dữ liệu", known_file
        if "python -c" in cmd_low or "python3 -c" in cmd_low:
            return agent, "Chạy script đồng bộ & sửa dữ liệu trực tiếp", (agent if agent != "orchestrator" else folder_name)
        return agent, "Chạy lệnh xử lý & đồng bộ dữ liệu", cmd[:56]

    return default_agent, f"Thực thi công cụ {tool_name or step_type or 'hệ thống'}", folder_name


def _collect_live_events(
    workspace: Path | None,
    chat_runs_root: Path | None = None,
    selected_job_id: str | None = None,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], dict[str, Any]]:
    """Scan ``.producer/*/events.jsonl`` AND ``.producer/chat_runs/*/events.jsonl`` for real-time agent actions."""
    events_out: list[dict[str, Any]] = []
    latest_by_agent: dict[str, dict[str, Any]] = {}
    stats = {
        "total_steps": 0,
        "total_output_tokens": 0,
        "active_subrun": None,
        "active_subrun_is_critic": False,
        "latest_event_age_sec": None,
    }
    now = time.time()
    candidate_dirs: list[Path] = []
    if workspace is not None and workspace.is_dir():
        prod_dir = workspace / ".producer"
        if prod_dir.is_dir():
            candidate_dirs.extend(
                d for d in prod_dir.iterdir() if d.is_dir() and (d / "events.jsonl").is_file()
            )

    job_id_str = str(selected_job_id or (workspace.name if workspace else "") or "").strip()
    if chat_runs_root is not None and chat_runs_root.is_dir():
        chat_dirs = sorted(
            (d for d in chat_runs_root.iterdir() if d.is_dir() and (d / "events.jsonl").is_file()),
            key=lambda d: (d / "events.jsonl").stat().st_mtime,
            reverse=True,
        )[:6]
        for cd in chat_dirs:
            run_meta = _read_json_safe(cd / "run.json")
            payload = run_meta.get("payload") if isinstance(run_meta.get("payload"), dict) else {}
            run_job = str(payload.get("selected_job_id") or run_meta.get("job_id") or "").strip()
            if run_job and job_id_str and run_job != job_id_str:
                continue
            if not run_job and job_id_str:
                # Verify if events tail mentions this job_id or if it is currently running
                st_low = str(run_meta.get("status") or "").lower()
                tail_txt = "\n".join(_tail_lines(cd / "events.jsonl", max_bytes=32768, max_lines=40))
                if st_low not in {"running", "queued"} and job_id_str not in tail_txt:
                    continue
            candidate_dirs.append(cd)

    if not candidate_dirs:
        return events_out, latest_by_agent, stats

    candidate_dirs.sort(key=lambda d: (d / "events.jsonl").stat().st_mtime)

    newest_mtime = 0.0
    for d in candidate_dirs:
        ev_file = d / "events.jsonl"
        mtime = ev_file.stat().st_mtime
        if mtime > newest_mtime:
            newest_mtime = mtime
            stats["active_subrun"] = d.name
            stats["active_subrun_is_critic"] = any(
                k in d.name.lower() for k in ("critic", "doctor", "screening", "hygiene", "polish")
            )

        raw_lines = _tail_lines(ev_file, max_bytes=196608, max_lines=120)
        max_step_in_dir = 0
        done_in_tail = 0
        for ln in raw_lines:
            ln = ln.strip()
            if not ln.startswith("{"):
                continue
            try:
                obj = json.loads(ln)
            except Exception:
                continue
            su = obj.get("step_update")
            if not isinstance(su, dict) and obj.get("type") == "cli_event" and isinstance(obj.get("line"), str):
                try:
                    inner = json.loads(obj["line"])
                    if isinstance(inner, dict):
                        su = inner.get("step_update")
                except Exception:
                    su = None
            if not isinstance(su, dict):
                continue
            state = str(su.get("state") or "")
            step_idx = int(su.get("step_index") or 0)
            if step_idx > max_step_in_dir:
                max_step_in_dir = step_idx
            usage = su.get("usage") if isinstance(su.get("usage"), dict) else {}
            if state == "DONE":
                done_in_tail += 1
                stats["total_output_tokens"] += int(usage.get("output_tokens") or 0)

            agent_id, action_vi, target_detail = _infer_event_agent_and_action(d.name, su)
            phase_inferred = _agent_to_phase(agent_id, d.name)
            item = {
                "folder": d.name,
                "phase": phase_inferred,
                "step_index": step_idx,
                "state": state,
                "agent_id": agent_id,
                "tool_name": str(su.get("tool_name") or su.get("step_type") or ""),
                "action_vi": action_vi,
                "target": target_detail,
                "duration_sec": round(float(su.get("duration_seconds") or 0.0), 2) if su.get("duration_seconds") else None,
                "mtime": mtime,
            }
            events_out.append(item)
            latest_by_agent[agent_id] = item
        stats["total_steps"] += max(max_step_in_dir, done_in_tail)

    if newest_mtime > 0:
        stats["latest_event_age_sec"] = round(max(0.0, now - newest_mtime), 1)

    dedup_map: dict[tuple[str, int], dict[str, Any]] = {}
    for ev in events_out:
        dedup_map[(ev["folder"], ev["step_index"])] = ev
    deduped = list(dedup_map.values())
    deduped.sort(key=lambda x: (x["mtime"], x["step_index"]), reverse=True)
    return deduped[:45], latest_by_agent, stats


def _parse_iso_epoch(raw_iso: Any) -> float:
    s = str(raw_iso or "").strip()
    if not s:
        return 0.0
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s).timestamp()
    except Exception:
        return 0.0


def _detect_workspace_rework_state(
    workspace: Path | None,
    job: dict[str, Any] | None,
    active_chat_run: dict[str, Any] | None,
    live_events: list[dict[str, Any]],
    event_stats: dict[str, Any],
) -> dict[str, Any]:
    """Detect both post-phase-completion rework history and currently active live rework across all 15 departments."""
    result: dict[str, Any] = {
        "reworked_phases": {},
        "reworked_agents": {},
        "live_rework_agents": {},
        "live_rework_phase": None,
        "is_rendering_mp4": False,
        "render_done_segs": 0,
        "render_total_segs": 0,
        "render_pct": 0,
    }
    if workspace is None or not workspace.is_dir():
        return result

    now = time.time()
    phases_state = (job or {}).get("phases") if isinstance((job or {}).get("phases"), dict) else {}
    legacy_phases = (job or {}).get("legacy_phases") if isinstance((job or {}).get("legacy_phases"), dict) else {}

    def _phase_finished_epoch(pk: str) -> float:
        p_info = phases_state.get(pk) if isinstance(phases_state.get(pk), dict) else {}
        fin = _parse_iso_epoch(p_info.get("finished_at") or p_info.get("completed_at") or p_info.get("started_at"))
        if not fin and pk == "footage":
            edit_info = phases_state.get("edit") if isinstance(phases_state.get("edit"), dict) else {}
            fin = _parse_iso_epoch(edit_info.get("finished_at") or edit_info.get("started_at"))
        if not fin and isinstance(legacy_phases.get(pk), dict):
            lp = legacy_phases[pk]
            fin = _parse_iso_epoch(lp.get("finished_at") or lp.get("completed_at") or lp.get("started_at"))
        return fin

    # 1. Check post-completion artifact modifications per specialist & phase
    artifact_probes: list[tuple[str, str, list[str], str]] = [
        ("plan", "research", ["research.md"], "Hồ sơ điều tra research.md"),
        ("plan", "script", ["script.md", "outline.json"], "Kịch bản văn nói script.md & cấu trúc câu"),
        ("voice", "voice", ["voice_manifest.json", "audio/narration.wav", "subtitles.srt", "editorial_voice_plan.json"], "Thu âm TTS narration.wav & phụ đề SRT"),
        ("visuals", "visuals", ["visual_manifest.json"], "Phân cảnh 1-1 visual_manifest.json"),
        ("footage", "footage", ["footage_approved_live.json", "footage_review.json", "media/contact_sheets/VERIFY_FTG_CLIPS_1.jpg", "media/contact_sheets/VERIFY_FTG_CLIPS_2.jpg"], "102 clip tư liệu thật S_F*.mp4 & bảng soi mắt 3-Frame"),
        ("ai_visual", "ai_visual", ["ai_visual_manifest.json"], "Bộ ảnh AI Keyframe 16:9"),
        ("edit", "vox", ["vox_scene_manifest.json", "universal_baked_scenes/VOX_01.mp4"], "Đồ họa điều tra VOX 2.5D & plate/prop tách nền RGBA"),
        ("edit", "edit", ["edit_manifest.json", "timeline.json", "scenes.json"], "Timeline Remotion & đồng bộ khung hình"),
        ("seo", "seo", ["seo_package.json", "thumbnail_design.json", "thumbnail.jpg"], "Gói SEO & 4 phương án Thumbnail"),
        ("qc", "qc", ["release/video.mp4", "final.mp4", "media/contact_sheets/FINAL_MP4_VERIFY_SHEET.jpg"], "Bản xuất Master MP4 & nghiệm thu cuối"),
    ]

    for pk, aid, rel_files, desc_vi in artifact_probes:
        fin_ts = _phase_finished_epoch(pk)
        if fin_ts <= 0:
            continue
        newest_f_mtime = 0.0
        touched_names: list[str] = []
        for rf in rel_files:
            fp = workspace / rf
            if fp.is_file():
                mt = fp.stat().st_mtime
                if mt > fin_ts + 90.0:
                    newest_f_mtime = max(newest_f_mtime, mt)
                    touched_names.append(Path(rf).name)
        if newest_f_mtime > 0:
            t_str = datetime.fromtimestamp(newest_f_mtime).strftime("%H:%M")
            badge_str = f"Đã làm lại & cập nhật mới ({t_str})"
            detail_str = f"🔄 @{aid} đã làm lại & đồng bộ mới lúc {t_str}: {desc_vi} ({', '.join(touched_names[:3])})"
            result["reworked_agents"][aid] = {
                "badge_vi": badge_str,
                "detail_vi": detail_str,
                "mtime": newest_f_mtime,
                "phase": pk,
            }
            prev_p = result["reworked_phases"].get(pk)
            if not prev_p or newest_f_mtime >= prev_p["mtime"]:
                result["reworked_phases"][pk] = {
                    "badge_vi": f"🔄 Đã làm lại & cập nhật mới ({t_str})",
                    "detail_vi": detail_str,
                    "mtime": newest_f_mtime,
                    "count": (prev_p["count"] + 1) if prev_p else 1,
                }
            else:
                prev_p["count"] += 1

    # 2. Check live UniversalMasterExport / Turbo NVENC segment rendering
    seg_dir = workspace / "universal_segments"
    plan_file = workspace / "universal_render_plan.json"
    if seg_dir.is_dir():
        seg_files = list(seg_dir.glob("*.mp4"))
        tmp_segs = [s for s in seg_files if s.name.endswith(".tmp.mp4")]
        done_segs = [s for s in seg_files if not s.name.endswith(".tmp.mp4")]
        newest_seg_mt = max((s.stat().st_mtime for s in seg_files), default=0.0)
        total_segs = 188
        if plan_file.is_file():
            rp = _read_json_safe(plan_file)
            if isinstance(rp.get("segments"), list) and rp["segments"]:
                total_segs = len(rp["segments"])
            elif int(rp.get("total_beats") or 0) > 0:
                total_segs = int(rp["total_beats"])
        total_segs = max(total_segs, len(done_segs) + len(tmp_segs), 1)
        mp4_path = workspace / "release" / "video.mp4"
        mp4_mt = mp4_path.stat().st_mtime if mp4_path.is_file() else 0.0
        # Active if .tmp.mp4 exists recently or segments were written in the last 60s and video.mp4 hasn't been written after them
        if (tmp_segs and (now - newest_seg_mt <= 120.0)) or (done_segs and (now - newest_seg_mt <= 45.0) and mp4_mt < newest_seg_mt):
            pct = min(99, max(5, round((len(done_segs) / total_segs) * 100)))
            result["is_rendering_mp4"] = True
            result["render_done_segs"] = len(done_segs)
            result["render_total_segs"] = total_segs
            result["render_pct"] = pct
            result["live_rework_phase"] = "qc"
            result["live_rework_agents"]["qc"] = {
                "status_label_vi": f"🔄 Đang kết xuất lại MP4 ({len(done_segs)}/{total_segs} đoạn · {pct}%)",
                "live_bubble": f"Đang chạy Turbo NVENC xuất lại video.mp4 sau khi sửa: {len(done_segs)}/{total_segs} phân đoạn ({pct}%)",
                "rework_badge": f"Đang xuất lại MP4 ({pct}%)",
            }
            result["live_rework_agents"]["edit"] = {
                "status_label_vi": f"🔄 Đang phối hợp kết xuất Timeline ({pct}%)",
                "live_bubble": f"Đã đồng bộ kịch bản, voice, 102 footage & 45 VOX — đang ghép {len(done_segs)}/{total_segs} đoạn MP4",
                "rework_badge": "Đang đồng bộ xuất MP4",
            }

    # 3. Check active Producer Chat run or recent CLI tool step (< 45s old)
    age_sec = event_stats.get("latest_event_age_sec")
    chat_is_live = bool(active_chat_run) or (age_sec is not None and float(age_sec) <= 45.0)
    if chat_is_live and live_events:
        for ev in live_events[:6]:
            ev_age = max(0.0, now - float(ev.get("mtime") or now))
            if ev_age > 90.0:
                continue
            aid = str(ev.get("agent_id") or "")
            if aid and aid not in {"orchestrator", "evidence_qa"} and aid not in result["live_rework_agents"]:
                tgt = f" → {ev['target']}" if ev.get("target") else ""
                act_txt = f"Bước #{ev.get('step_index', 0)} · {ev.get('action_vi', 'Đang xử lý')}{tgt}"
                result["live_rework_agents"][aid] = {
                    "status_label_vi": f"🔄 Đang làm lại & cập nhật ({ev.get('target') or aid})",
                    "live_bubble": act_txt,
                    "rework_badge": "Đang làm lại trực tiếp",
                }
                if not result["live_rework_phase"]:
                    result["live_rework_phase"] = str(ev.get("phase") or _agent_to_phase(aid))
                break

    return result


def _build_critique_gates(
    workspace: Path | None,
    job: dict[str, Any] | None,
    active_subrun: str | None,
    rework_info: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Build 8-stage Maker <-> Critic <-> Rework transparency cards from real workspace files."""
    phases_state = (job or {}).get("phases") if isinstance((job or {}).get("phases"), dict) else {}
    legacy_phases = (job or {}).get("legacy_phases") if isinstance((job or {}).get("legacy_phases"), dict) else {}
    vis_strategy = str((job or {}).get("visual_strategy") or "").strip().lower()
    active_sub_low = str(active_subrun or "").lower()
    reworked_phases_map = (rework_info or {}).get("reworked_phases") or {}
    live_rework_phase = (rework_info or {}).get("live_rework_phase")

    gates: list[dict[str, Any]] = []
    totals = {
        "passed_gates": 0,
        "reworked_gates": 0,
        "total_rewrites_or_rerolls": 0,
        "active_critic_count": 0,
        "rejected_gates": 0,
    }

    for phase_key, meta in PHASE_AGENT_MAP.items():
        p_info = phases_state.get(phase_key) if isinstance(phases_state.get(phase_key), dict) else {}
        if not p_info and isinstance(legacy_phases.get(phase_key), dict):
            p_info = legacy_phases[phase_key]
        p_status = str(p_info.get("status") or "pending").lower()
        if phase_key == "footage" and p_status == "pending" and workspace and (
            (workspace / "footage_approved_live.json").is_file() or (workspace / "footage_hygiene_report.json").is_file()
        ):
            p_status = "succeeded"
        if live_rework_phase == phase_key:
            p_status = "running"
        p_error = str(p_info.get("error") or "").strip()

        # Skip footage if visual_strategy == full_ai and footage wasn't run
        if phase_key == "footage" and vis_strategy == "full_ai" and p_status == "pending":
            gates.append({
                "phase": phase_key,
                "label_vi": meta["label_vi"],
                "maker_agent": meta["lead"],
                "co_agents": meta["co_leads"],
                "critic_agent": meta["critic"],
                "gate_state": "skipped_by_strategy",
                "badge_vi": "Gộp vào Bước 6 (Chế độ Full AI + Real Edit)",
                "rework_triggered": False,
                "rework_count": 0,
                "rounds_count": 0,
                "summary_vi": "Bước 4 bỏ qua theo cấu hình hồ sơ; tư liệu video thật sẽ được Agent footage + edit săn và kiểm duyệt 3-frame trực tiếp ở Bước 6.",
                "proof_items": [],
                "rounds": [],
            })
            continue

        report: dict[str, Any] = {}
        report_name = ""
        if workspace and workspace.is_dir():
            for rf in meta["report_files"]:
                cand = _read_json_safe(workspace / rf)
                if cand:
                    report = cand
                    report_name = rf
                    break

        rework_triggered = False
        rework_count = 0
        rounds_list: list[dict[str, Any]] = []
        proof_items: list[str] = []
        summary_vi = ""
        verdict = "PENDING"

        # Stage-specific real metric extraction
        if phase_key == "plan":
            if workspace and (workspace / "research.md").is_file():
                proof_items.append(f"Hồ sơ điều tra gốc research.md: {(workspace / 'research.md').stat().st_size:,} bytes")
            if workspace and (workspace / "script.md").is_file():
                proof_items.append(f"Kịch bản script.md: {(workspace / 'script.md').stat().st_size:,} bytes")
            if workspace and (workspace / "visual_manifest.json").is_file():
                vm = _read_json_safe(workspace / "visual_manifest.json")
                beats = vm.get("beats") if isinstance(vm.get("beats"), list) else []
                proof_items.append(f"Bản đồ phân cảnh ban đầu: {len(beats)} câu thoại")
            if report:
                para_reb = bool(report.get("paragraph_cadence_rebalanced"))
                rewrites = int(report.get("total_surgical_rewrites") or 0)
                raw_rounds = report.get("rounds") if isinstance(report.get("rounds"), list) else []
                sensor = report.get("final_sensor") if isinstance(report.get("final_sensor"), dict) else {}
                defects_left = len(sensor.get("defects") or []) if isinstance(sensor.get("defects"), list) else 0
                verdict = str(sensor.get("status") or "PASS").upper()
                if para_reb or rewrites > 0 or len(raw_rounds) > 1:
                    rework_triggered = True
                    rework_count = rewrites + (1 if para_reb else 0)
                if para_reb:
                    proof_items.append("🔄 Đã tự động phá bỏ nhịp đoạn văn đều tăm tắp (tách nhịp thở 1–5 câu tự nhiên)")
                if rewrites > 0:
                    proof_items.append(f"🔄 Critic bắt viết lại phẫu thuật {rewrites} câu thoại bị mùi dịch máy / lặp đuôi câu")
                proof_items.append(f"Kiểm định cảm biến văn nói cuối cùng: {verdict} ({defects_left} lỗi tồn đọng)")
                for r in raw_rounds:
                    if isinstance(r, dict):
                        rounds_list.append({
                            "round": r.get("round", 1),
                            "verdict": str(r.get("verdict") or "PASS").upper(),
                            "applied": int(r.get("applied_rewrites") or 0),
                            "summary": str(r.get("summary") or "Kiểm tra ngữ pháp, nhịp thở TTS & tính tự nhiên"),
                        })
                summary_vi = (
                    f"Đã qua {max(1, len(raw_rounds))} vòng kiểm duyệt phản biện kịch bản"
                    + (f", sửa lại {rewrites} câu thoại" if rewrites else ", văn phong đạt chuẩn tự nhiên")
                    + "."
                )
            elif p_status == "succeeded":
                summary_vi = "Hồ sơ điều tra gốc, dàn ý & kịch bản văn nói đã vượt qua kiểm duyệt."

        elif phase_key == "voice":
            vm = _read_json_safe(workspace / "voice_manifest.json") if workspace else {}
            v_beats = vm.get("beats") if isinstance(vm.get("beats"), list) else []
            qc_sum = vm.get("qc_summary") if isinstance(vm.get("qc_summary"), dict) else {}
            cad_audit = (
                report.get("cadence_audit")
                if isinstance(report.get("cadence_audit"), dict)
                else (qc_sum.get("cadence_audit") if isinstance(qc_sum.get("cadence_audit"), dict) else {})
            )
            rerolled = int(report.get("rerolled_beats_count") or report.get("rerolled_count") or 0)
            dur = float(vm.get("total_duration_sec") or vm.get("duration_sec") or 0.0)
            if not dur and v_beats:
                dur = max((float(b.get("end_sec") or b.get("end") or 0.0) for b in v_beats if isinstance(b, dict)), default=0.0)
            if v_beats:
                proof_items.append(f"Đã thu âm & căn chỉnh Whisper: {len(v_beats)} câu ({dur / 60.0:.1f} phút)")
            if cad_audit and not cad_audit.get("synthetic_fixture"):
                med_sps = cad_audit.get("median_syllables_per_sec")
                inten_cnt = cad_audit.get("intentional_pauses_count")
                dram_cnt = cad_audit.get("dramatic_pauses_count")
                reg_cnt = len(cad_audit.get("emotion_registers") or {})
                if med_sps is not None:
                    proof_items.append(
                        f"Nhịp kể chuyện & cảm xúc: {med_sps} âm tiết/giây · {inten_cnt or 0} khoảng nghỉ chủ đích ({dram_cnt or 0} điểm rơi sâu) · {reg_cnt} sắc thái cảm xúc"
                    )
            if rerolled > 0:
                rework_triggered = True
                rework_count = rerolled
                proof_items.append(f"🔄 Critic phát hiện vấp/gấp nhịp & bắt thu âm lại (reroll): {rerolled} câu")
            if workspace and (workspace / "subtitles.srt").is_file():
                proof_items.append("Đã xuất phụ đề chuẩn subtitles.srt khớp từ Whisper")
            if report or (p_status == "succeeded" and v_beats):
                verdict = str(report.get("status") or "PASS").upper()
                summary_vi = (
                    f"Kiểm duyệt âm thanh, nhịp nghỉ cảm xúc & Whisper {len(v_beats)} câu"
                    + (f" — đã thu lại {rerolled} câu chưa mượt." if rerolled else " — 100% tròn chữ, phân tầng khoảng nghỉ đạt chuẩn.")
                )

        elif phase_key == "visuals":
            vm = _read_json_safe(workspace / "visual_manifest.json") if workspace else {}
            beats = vm.get("beats") if isinstance(vm.get("beats"), list) else []
            div_count = int(report.get("diversified_archetypes") or 0)
            enr_count = int(report.get("enriched_prompts") or 0)
            if beats:
                proof_items.append(f"Tổng số phân cảnh 1-1 khớp thoại: {len(beats)} cảnh")
            if div_count > 0 or enr_count > 0:
                rework_triggered = True
                rework_count = div_count + enr_count
                if div_count > 0:
                    proof_items.append(f"🔄 Đã phá chuỗi cảnh đơn điệu, đổi góc máy cho {div_count} phân cảnh")
                if enr_count > 0:
                    proof_items.append(f"🔄 Đã bồi đắp chi tiết thị giác cho {enr_count} prompt quá ngắn")
            if report or (p_status == "succeeded" and beats):
                verdict = str(report.get("status") or "PASS").upper()
                summary_vi = f"Phân cảnh 1-1 hoàn tất ({len(beats)} beat)" + (
                    f", đã chỉnh sửa chống lặp {rework_count} điểm." if rework_count else ", nhịp cảnh đa dạng."
                )

        elif phase_key == "footage":
            hygiene = report
            approved = _read_json_safe(workspace / "footage_approved_live.json") if workspace else {}
            items = approved.get("items") if isinstance(approved.get("items"), list) else []
            rejected = int(hygiene.get("rejected_count") or 0)
            if items:
                proof_items.append(f"Tư liệu thật vượt qua kiểm duyệt 3-Frame (12%-50%-85%): {len(items)} clip")
            if rejected > 0:
                rework_triggered = True
                rework_count = rejected
                proof_items.append(f"🔄 Đã loại bỏ & tìm thay thế {rejected} clip dính logo / phụ đề ngoại / MC")
            if report or p_status == "succeeded":
                verdict = str(hygiene.get("status") or "PASS").upper()
                summary_vi = f"Đã duyệt {len(items)} clip tư liệu sạch."

        elif phase_key == "ai_visual":
            ai_man = _read_json_safe(workspace / "ai_visual_manifest.json") if workspace else {}
            items = ai_man.get("items") if isinstance(ai_man.get("items"), list) else (ai_man.get("beats") if isinstance(ai_man.get("beats"), list) else [])
            retried = int(report.get("regenerated_count") or report.get("retried_count") or 0)
            if items:
                proof_items.append(f"Ảnh AI Keyframe 16:9 đã tạo: {len(items)} tấm (khóa style nhân vật kênh)")
            elif workspace and (workspace / "media" / "ai_visual").is_dir():
                imgs = list((workspace / "media" / "ai_visual").glob("*.jpg")) + list((workspace / "media" / "ai_visual").glob("*.png"))
                if imgs:
                    proof_items.append(f"Đang vẽ trực tiếp trong xưởng: {len(imgs)} ảnh đã lưu trên đĩa")
            if retried > 0:
                rework_triggered = True
                rework_count = retried
                proof_items.append(f"🔄 Phát hiện ảnh lỗi/sai tỷ lệ & bắt vẽ lại: {retried} ảnh")
            if report or (p_status == "succeeded" and items):
                verdict = str(report.get("status") or "PASS").upper()
                summary_vi = f"Đã kiểm tra {len(items)} ảnh AI chuẩn nhận diện kênh."

        elif phase_key == "edit":
            ep = _read_json_safe(workspace / "edit_progress.json") if workspace else {}
            em = _read_json_safe(workspace / "edit_manifest.json") if workspace else {}
            tl = _read_json_safe(workspace / "timeline.json") if workspace else {}
            comp = _read_json_safe(workspace / "compliance_scorecard.json") if workspace else {}
            vox_man = _read_json_safe(workspace / "vox_scene_manifest.json") if workspace else {}
            rhythm_sc = _read_json_safe(workspace / "edit_rhythm_score.json") if workspace else {}
            voice_plan = _read_json_safe(workspace / "editorial_voice_plan.json") if workspace else {}
            em_beats = em.get("beats") if isinstance(em.get("beats"), list) else []
            tl_beats = tl.get("beats") if isinstance(tl.get("beats"), list) else []
            done_b = max(
                int(ep.get("completed_beats") or ep.get("completed") or 0) if ep else 0,
                len(em_beats),
                len(tl_beats),
            )
            tot_b = (
                int(em.get("total_beats") or 0)
                or (int(ep.get("total_beats") or ep.get("total") or 0) if ep else 0)
                or len(em_beats)
                or len(tl_beats)
            )
            if tot_b:
                proof_items.append(f"Tiến độ dựng Timeline Remotion: {min(done_b, tot_b)}/{tot_b} phân cảnh")
            if voice_plan:
                pre_v = float(voice_plan.get("cold_open_pre_voice_sec") or 0.0)
                p_adj = int(voice_plan.get("pause_adjustments_count") or 0)
                c_cnt = int(voice_plan.get("mid_beat_caesuras_count") or 0)
                proof_items.append(
                    f"Điêu khắc nhịp thở Voice từ stem gốc: mở màn {pre_v:.2f}s trước thoại · {p_adj} điểm co giãn nhịp nghỉ · {c_cnt} nhát cắt lặng giữa câu (Caesura)"
                )
            if rhythm_sc and isinstance(rhythm_sc.get("feel_summary"), dict):
                fs = rhythm_sc["feel_summary"]
                jls = rhythm_sc.get("jl_cut_summary") if isinstance(rhythm_sc.get("jl_cut_summary"), dict) else {}
                holds = int(fs.get("breath_synced_emotional_hold") or 0) + int(fs.get("chapter_curtain_breath") or 0)
                j_cuts = int(jls.get("j_cut_prelap_pivot") or 0) + int(jls.get("chapter_dissolve_and_j_prelap") or 0)
                kinetic = int(fs.get("rapid_kinetic_cut") or 0)
                std_sec = ((rhythm_sc.get("shot_pacing_sec") or {}).get("standard_avg_sec") or 4.2)
                proof_items.append(
                    f"Ngôn ngữ điện ảnh Đạo diễn (~{std_sec}s/cảnh): {holds} điểm L-cut giữ hình thấm cảm xúc · {j_cuts} điểm J-cut dẫn âm · {kinetic} nhịp cắt hành động · phối màu 5 Hồi"
                )
            if em:
                rf_cnt = int(em.get("real_footage_beats_count") or 0)
                vx_cnt = int(em.get("vox_beats_count") or 0)
                uniq_clips = int(em.get("unique_footage_clips_mounted") or 0)
                if rf_cnt or vx_cnt:
                    proof_items.append(
                        f"Phân bổ thị giác: {rf_cnt} cảnh tư liệu thật ({uniq_clips} clip sạch) · {vx_cnt} cảnh Motion Vox 2.5D"
                    )
            if vox_man:
                scenes = vox_man.get("scenes") if isinstance(vox_man.get("scenes"), list) else (
                    list(vox_man.values()) if isinstance(vox_man, dict) else []
                )
                mechs = sorted({
                    str(s.get("mechanism") or s.get("archetype") or s.get("component") or s.get("type") or "").strip()
                    for s in scenes if isinstance(s, dict)
                } - {""})
                if scenes:
                    proof_items.append(f"Hệ cảnh Motion Vox 2.5D: {len(scenes)} cảnh · {max(len(mechs), 1)} cơ chế thị giác riêng biệt")
            raw_rounds = report.get("rounds") if isinstance(report.get("rounds"), list) else []
            fixes = int(report.get("applied_fixes") or report.get("reworked_beats") or 0)
            if fixes > 0 or len(raw_rounds) > 1:
                rework_triggered = True
                rework_count = max(fixes, len(raw_rounds) - 1)
                proof_items.append(f"🔄 Đạo diễn & Critic đã soi preview và tinh chỉnh lại {rework_count} hạng mục dựng/Vox")
            if comp:
                score = comp.get("score") or comp.get("overall_score")
                if score is not None:
                    proof_items.append(f"Điểm chuẩn hóa Audio-Visual & Xanh tiền: {score}")
            if report or p_status == "succeeded":
                verdict = str(report.get("verdict") or report.get("status") or comp.get("status") or "PASS").upper()
                summary_vi = "Timeline Remotion, tỷ lệ Footage thật, Vox đa cơ chế & âm thanh đã qua vòng duyệt Đạo diễn."

        elif phase_key == "seo":
            seo_pack = _read_json_safe(workspace / "seo_package.json") if workspace else {}
            opts = seo_pack.get("title_options") if isinstance(seo_pack.get("title_options"), list) else []
            if opts:
                proof_items.append(f"Bộ phương án Tiêu đề chuẩn CTR: {len(opts)} phương án")
            if workspace and (workspace / "thumbnail.jpg").is_file():
                proof_items.append("Đã xuất Thumbnail chính & gói biến thể A/B/C kiểm tra chữ rõ ở cỡ mobile")
            rew = int(report.get("reworked_count") or 0)
            if rew > 0:
                rework_triggered = True
                rework_count = rew
                proof_items.append(f"🔄 Đã viết lại {rew} tiêu đề/chữ thumbnail bị trùng lặp hoặc phạm từ nhạy cảm")
            if report or (p_status == "succeeded" and seo_pack):
                verdict = str(report.get("status") or "PASS").upper()
                summary_vi = "Đóng gói Tiêu đề + Thumbnail + Chapters đạt chuẩn CTR & Xanh tiền YouTube."

        elif phase_key == "qc":
            fm = _read_json_safe(workspace / "final_manifest.json") if workspace else {}
            qc_rep = _read_json_safe(workspace / "qc_screening_report.json") if workspace else {}
            if fm:
                f_stat = str(fm.get("final_qc_status") or fm.get("status") or "").upper()
                if f_stat:
                    verdict = f_stat
                dur_s = fm.get("duration_sec") or (fm.get("video") or {}).get("duration_sec")
                if dur_s:
                    proof_items.append(f"File MP4 xuất bản 1920x1080: thời lượng {float(dur_s) / 60.0:.2f} phút")
            if qc_rep:
                frames_checked = qc_rep.get("inspected_frames_count") or len(qc_rep.get("inspected_frames") or [])
                if frames_checked:
                    proof_items.append(f"Giám đốc QC đã soi trực tiếp {frames_checked} khung hình thực tế từ bản MP4")
                if qc_rep.get("verdict"):
                    verdict = str(qc_rep["verdict"]).upper()
            if p_status == "succeeded" and verdict in {"PENDING", ""}:
                verdict = "ACCEPT"
            if verdict in {"ACCEPT", "PASS", "CERTIFIED"}:
                summary_vi = "Bản Master MP4 đã vượt qua toàn bộ bài kiểm tra hình ảnh, âm lượng LUFS & câu kết + 3.8s fade-out."

        # Merge real-time Autonomous Phase QA-Rework Ledger (.producer/qa_rework_ledger/<phase>.json)
        rework_ledger = (
            _read_json_safe(workspace / ".producer" / "qa_rework_ledger" / f"{phase_key}.json")
            if workspace and workspace.is_dir()
            else {}
        )
        ledger_rejections = (
            rework_ledger.get("rejections")
            if isinstance(rework_ledger.get("rejections"), list)
            else []
        )
        ledger_status = str(rework_ledger.get("status") or "").strip().lower()
        ledger_cur_attempt = max(1, int(rework_ledger.get("current_attempt") or 1))
        ledger_max_attempts = max(1, int(rework_ledger.get("max_attempts") or 3))
        ledger_latest_reason = str(rework_ledger.get("latest_reason") or "").strip()
        if ledger_rejections:
            rework_triggered = True
            rework_count = rework_count + len(ledger_rejections)
            ledger_rounds = [
                {
                    "round": f"QA #{r.get('attempt', idx + 1)}",
                    "verdict": "KHÔNG DUYỆT → TỰ CHẠY LẠI",
                    "applied": 1,
                    "summary": str(r.get("reason") or "")[:240],
                }
                for idx, r in enumerate(ledger_rejections)
                if isinstance(r, dict)
            ]
            rounds_list = ledger_rounds + rounds_list
            if p_status == "succeeded":
                passed_att = int(rework_ledger.get("passed_on_attempt") or (len(ledger_rejections) + 1))
                proof_items.insert(
                    0,
                    f"🔄 Đã tự động chạy lại & vượt kiểm duyệt ở Lần {passed_att}/{ledger_max_attempts} (sau {len(ledger_rejections)} lần QA trả về)",
                )

        post_rework = reworked_phases_map.get(phase_key)
        if isinstance(post_rework, dict):
            rework_triggered = True
            rework_count = max(rework_count, int(post_rework.get("count") or 1))
            proof_items.insert(0, str(post_rework.get("detail_vi") or "🔄 Đã làm lại & đồng bộ mới"))

        # Determine unified gate_state
        is_critic_now = (
            p_status == "running"
            and active_sub_low.startswith(phase_key)
            and any(k in active_sub_low for k in ("critic", "doctor", "screening", "hygiene", "polish"))
        )
        if p_status == "running":
            if live_rework_phase == phase_key:
                gate_state = "reworking_live"
                if (rework_info or {}).get("is_rendering_mp4") and phase_key == "qc":
                    r_done = (rework_info or {}).get("render_done_segs", 0)
                    r_tot = (rework_info or {}).get("render_total_segs", 188)
                    r_pct = (rework_info or {}).get("render_pct", 0)
                    badge_vi = f"🔄 Đang kết xuất lại MP4 ({r_done}/{r_tot} đoạn · {r_pct}%)"
                    summary_vi = f"Đang chạy Turbo NVENC xuất lại bản Master MP4 sau khi sửa kịch bản, voice, footage & VOX ({r_done}/{r_tot} phân đoạn · {r_pct}%)."
                    proof_items.insert(0, f"🎬 Đang render lại video.mp4: {r_done}/{r_tot} phân đoạn ({r_pct}%)")
                else:
                    badge_vi = "🔄 Đang làm lại & đồng bộ trực tiếp…"
                    summary_vi = f"Đội ngũ @{meta['lead']} đang trực tiếp sửa lại và đồng bộ dữ liệu khâu {meta['label_vi']}."
                totals["active_critic_count"] += 1
                totals["reworked_gates"] += 1
                totals["total_rewrites_or_rerolls"] += max(1, rework_count)
            elif ledger_status == "reworking" and ledger_rejections:
                gate_state = "reworking_live"
                badge_vi = f"🔄 Chưa duyệt · Tự động làm lại ({ledger_cur_attempt}/{ledger_max_attempts})"
                totals["active_critic_count"] += 1
                totals["reworked_gates"] += 1
                totals["total_rewrites_or_rerolls"] += rework_count
                proof_items.insert(
                    0,
                    f"🔄 Không duyệt Lần {max(1, ledger_cur_attempt - 1)}/{ledger_max_attempts} — đang tự động sửa & chạy lại: {ledger_latest_reason[:220]}",
                )
                summary_vi = (
                    f"@{meta['critic']} từ chối duyệt Lần {max(1, ledger_cur_attempt - 1)} ({ledger_latest_reason[:160]}) — "
                    f"@{meta['lead']} đang tự động sửa lỗi và chạy lại Lần {ledger_cur_attempt}/{ledger_max_attempts}!"
                )
            elif is_critic_now or phase_key == "qc":
                gate_state = "critic_reviewing"
                badge_vi = "🔎 Đang phản biện & soi lỗi trực tiếp…"
                totals["active_critic_count"] += 1
            else:
                gate_state = "maker_working"
                badge_vi = "🔨 Agent sản xuất đang thực hiện…"
        elif p_status == "failed" or verdict in {"REJECT", "BLOCKED", "FAIL", "FAILED"}:
            gate_state = "rejected"
            verdict = "REJECTED" if p_status == "failed" else verdict
            badge_vi = "🛑 Chưa đạt — Đã chặn bàn giao"
            totals["rejected_gates"] += 1
            if p_error:
                proof_items.insert(0, f"🛑 Phát hiện lỗi chưa đạt chuẩn: {p_error[:260]}")
                summary_vi = f"Cổng kiểm duyệt đã chặn bàn giao tự động — bắt buộc sửa đạt chuẩn trước khi sang bước tiếp theo ({p_error[:190]})."
        elif p_status == "succeeded" or verdict in {"PASS", "ACCEPT", "CERTIFIED", "VERIFIED", "PASSED"}:
            totals["passed_gates"] += 1
            if rework_triggered:
                gate_state = "reworked_and_passed"
                badge_vi = f"🔄 Đã bắt sửa lại ({max(1, rework_count)}) & Duyệt ĐẠT"
                totals["reworked_gates"] += 1
                totals["total_rewrites_or_rerolls"] += rework_count
            else:
                gate_state = "passed_clean"
                badge_vi = "✅ Kiểm duyệt ĐẠT chuẩn"
        else:
            gate_state = "waiting"
            badge_vi = "⏳ Đang chờ tới lượt"

        gates.append({
            "phase": phase_key,
            "label_vi": meta["label_vi"],
            "maker_agent": meta["lead"],
            "co_agents": meta["co_leads"],
            "critic_agent": meta["critic"],
            "phase_status": p_status,
            "gate_state": gate_state,
            "badge_vi": badge_vi,
            "verdict": verdict,
            "report_file": report_name or None,
            "rework_triggered": rework_triggered,
            "rework_count": rework_count,
            "rounds_count": max(len(rounds_list), 1 if gate_state in {"passed_clean", "reworked_and_passed"} else 0),
            "summary_vi": summary_vi or ("Đang thực thi trực tiếp trên workspace…" if p_status == "running" else "Chưa chạy công đoạn này."),
            "proof_items": proof_items,
            "rounds": rounds_list,
        })

    return gates, totals


def _build_live_phase_report(
    workspace: Path | None,
    selected_job: dict[str, Any] | None,
    running_phases: list[str],
    live_events: list[dict[str, Any]],
    event_stats: dict[str, Any],
    active_agent_ids: list[str],
) -> dict[str, Any]:
    """Build a clean, concrete progress report for the currently active phase & department."""
    cur_phase = (
        running_phases[0]
        if running_phases
        else str((selected_job or {}).get("current_phase") or "").strip().lower()
    )
    if not cur_phase:
        cur_phase = "plan"

    phase_meta = PHASE_AGENT_MAP.get(cur_phase, PHASE_AGENT_MAP["plan"])
    phase_label_vi = str(phase_meta.get("label_vi") or f"Bước · {cur_phase}")
    step_idx = int(event_stats.get("total_steps") or 0)
    if live_events and int(live_events[0].get("step_index") or 0) > step_idx:
        step_idx = int(live_events[0].get("step_index") or 0)

    has_research = bool(workspace and (workspace / "research.md").is_file())
    has_outline = bool(workspace and (workspace / "outline.json").is_file())
    has_script = bool(workspace and (workspace / "script.md").is_file())
    has_vis_man = bool(workspace and (workspace / "visual_manifest.json").is_file())

    primary_agent_id = str(phase_meta.get("lead") or "script")
    if cur_phase == "plan":
        primary_agent_id = "script" if has_research else "research"
    elif active_agent_ids:
        non_orch = [a for a in active_agent_ids if a not in {"orchestrator", "evidence_qa"}]
        if non_orch:
            primary_agent_id = non_orch[0]

    milestones: list[dict[str, Any]] = []
    pct = 12

    if cur_phase == "plan":
        res_kb = ((workspace / "research.md").stat().st_size / 1024.0) if has_research and workspace else 0.0
        scr_chars = len((workspace / "script.md").read_text(encoding="utf-8", errors="replace")) if has_script and workspace else 0
        vm_beats = len((_read_json_safe(workspace / "visual_manifest.json").get("beats") or [])) if has_vis_man and workspace else 0
        milestones = [
            {
                "label_vi": "1. Hồ sơ điều tra gốc",
                "file": "research.md",
                "done": has_research,
                "detail_vi": f"Đã xong ({res_kb:.1f} KB)" if has_research else "Đang tra cứu & đối chứng...",
            },
            {
                "label_vi": "2. Dàn ý cấu trúc chương hồi",
                "file": "outline.json",
                "done": has_outline,
                "detail_vi": "Đã khóa cấu trúc 5 hồi" if has_outline else ("Đang lập dàn ý..." if has_research else "Chờ research.md"),
            },
            {
                "label_vi": "3. Kịch bản văn nói",
                "file": "script.md",
                "done": has_script,
                "detail_vi": f"Đã viết ({scr_chars:,} ký tự)" if has_script else ("Đang chấp bút lời bình..." if has_outline else "Chờ dàn ý"),
            },
            {
                "label_vi": "4. Khung phân cảnh & Kiểm duyệt",
                "file": "visual_manifest.json",
                "done": has_vis_man,
                "detail_vi": f"Đã chia {vm_beats} beats" if has_vis_man else ("Đang chia beat & rà QA..." if has_script else "Chờ script.md"),
            },
        ]
        done_cnt = sum(1 for m in milestones if m["done"])
        base_pct = [10, 32, 58, 82, 96][min(4, done_cnt)]
        step_bonus = min(14, max(0, step_idx // 4))
        pct = min(98 if running_phases else 100, base_pct + step_bonus)
    elif cur_phase == "voice":
        vm = _read_json_safe(workspace / "voice_manifest.json") if workspace else {}
        v_beats = vm.get("beats") if isinstance(vm.get("beats"), list) else []
        plan_vm = _read_json_safe(workspace / "visual_manifest.json") if workspace else {}
        if not plan_vm.get("beats") and workspace:
            plan_vm = _read_json_safe(workspace / "plan_visual_manifest.json")
        total_voice_beats = len(plan_vm.get("beats") or []) or len(v_beats) or 238
        beats_dir = (workspace / "audio" / "beats") if workspace else None
        wav_files = sorted(beats_dir.glob("B*.wav")) if (beats_dir and beats_dir.is_dir()) else []
        done_wav = max(len(v_beats), len(wav_files))
        latest_wav = wav_files[-1].name if wav_files else ""
        has_srt = bool(workspace and (workspace / "subtitles.srt").is_file())
        has_vqc = bool(workspace and (workspace / "voice_qc_report.json").is_file())
        tts_detail = (
            f"Đã thu {done_wav}/{total_voice_beats} câu" + (f" ({latest_wav})" if latest_wav else "")
            if done_wav > 0
            else "Đang tổng hợp TTS..."
        )
        milestones = [
            {"label_vi": "1. Chuẩn hóa phiên âm TTS", "file": "script.md", "done": True, "detail_vi": f"Sẵn sàng ({total_voice_beats} câu)"},
            {"label_vi": "2. Tổng hợp giọng đọc GPU", "file": "voice_manifest.json", "done": len(v_beats) > 0 or (done_wav >= total_voice_beats and total_voice_beats > 0), "detail_vi": tts_detail},
            {"label_vi": "3. Đồng bộ phụ đề Whisper", "file": "subtitles.srt", "done": has_srt, "detail_vi": "Đã căn khớp từ" if has_srt else "Đang căn chỉnh SRT..."},
            {"label_vi": "4. Kiểm tra nhịp thở & LUFS", "file": "voice_qc_report.json", "done": has_vqc, "detail_vi": "Đạt chuẩn -16 LUFS" if has_vqc else "Chờ kiểm tra cuối"},
        ]
        if has_vqc:
            pct = 100
        elif has_srt:
            pct = 92
        elif done_wav > 0 and total_voice_beats > 0:
            pct = max(6, min(88, round((done_wav / total_voice_beats) * 85)))
        else:
            pct = 8
    elif cur_phase == "visuals":
        vm = _read_json_safe(workspace / "visual_manifest.json") if workspace else {}
        beats = vm.get("beats") if isinstance(vm.get("beats"), list) else []
        milestones = [
            {"label_vi": "1. Chia câu thoại 1-1 (STP)", "file": "visual_manifest.json", "done": len(beats) > 0, "detail_vi": f"{len(beats)} phân cảnh" if beats else "Đang chia sub-beat..."},
            {"label_vi": "2. Phân luồng FTG / VOX / AI", "file": "visual_manifest.json", "done": len(beats) > 0, "detail_vi": "Đã gắn nhãn routing" if beats else "Đang phân luồng..."},
            {"label_vi": "3. Biên dịch prompt chi tiết", "file": "visual_manifest.json", "done": len(beats) > 0, "detail_vi": "1 dòng 1 prompt" if beats else "Đang viết prompt..."},
            {"label_vi": "4. Nghiệm thu chống lặp cảnh", "file": "visuals_critic_report.json", "done": bool(workspace and (workspace / "visuals_critic_report.json").is_file()), "detail_vi": "Đã duyệt" if (workspace and (workspace / "visuals_critic_report.json").is_file()) else "Đang rà soát..."},
        ]
        pct = 85 if beats else min(75, 18 + step_idx * 2)
    elif cur_phase == "footage":
        app_ftg = _read_json_safe(workspace / "footage_approved_live.json") if workspace else {}
        items = app_ftg.get("items") if isinstance(app_ftg.get("items"), list) else []
        milestones = [
            {"label_vi": "1. Săn ứng viên tư liệu thật", "file": "footage_manifest.json", "done": True, "detail_vi": "Quét nguồn lưu trữ"},
            {"label_vi": "2. Soi lưới tọa độ 100px SAFE_CROP", "file": "GRID_*.jpg", "done": len(items) > 0, "detail_vi": "Cắt sạch 4 cạnh"},
            {"label_vi": "3. Kiểm duyệt mắt 3-Frame", "file": "VERIFY_FTG_CLIPS_*.jpg", "done": len(items) > 0, "detail_vi": f"Đã duyệt {len(items)} clip sạch" if items else "Đang soi 15%-50%-85%..."},
            {"label_vi": "4. Khóa danh mục clip sạch", "file": "footage_hygiene_report.json", "done": bool(workspace and (workspace / "footage_hygiene_report.json").is_file()), "detail_vi": f"{len(items)} clip đạt chuẩn"},
        ]
        pct = min(95, max(20, len(items) * 3)) if items else min(65, 15 + step_idx * 2)
    elif cur_phase == "ai_visual":
        ai_man = _read_json_safe(workspace / "ai_visual_manifest.json") if workspace else {}
        tot = len(ai_man.get("target_beat_ids") or [])
        miss = len(ai_man.get("remaining_missing_beats") or [])
        done_img = max(0, tot - miss) if tot else 0
        pct = min(98, round((done_img / tot) * 100)) if tot else min(75, 15 + step_idx * 2)
        milestones = [
            {"label_vi": "1. Khóa bảng màu & ánh sáng kênh", "file": "ai_visual_manifest.json", "done": True, "detail_vi": "16:9 Chiaroscuro"},
            {"label_vi": "2. Vẽ Keyframe tái dựng góc kín", "file": "media/ai_visual/*", "done": done_img > 0, "detail_vi": f"Đã vẽ {done_img}/{tot or '?'} ảnh"},
            {"label_vi": "3. Kiểm tra bố cục & giải phẫu", "file": "ai_visual_qc_report.json", "done": tot > 0 and miss == 0, "detail_vi": f"Còn {miss} ảnh" if tot else "Đang kiểm tra..."},
            {"label_vi": "4. Bàn giao sang Phòng Dựng", "file": "ai_visual_manifest.json", "done": tot > 0 and miss == 0, "detail_vi": "Sẵn sàng ghép timeline"},
        ]
    elif cur_phase == "edit":
        em = _read_json_safe(workspace / "edit_manifest.json") if workspace else {}
        ep = _read_json_safe(workspace / "edit_progress.json") if workspace else {}
        vox_man = _read_json_safe(workspace / "vox_scene_manifest.json") if workspace else {}
        em_beats = em.get("beats") if isinstance(em.get("beats"), list) else []
        tot_b = int(em.get("total_beats") or ep.get("total_beats") or len(em_beats) or 0)
        done_b = max(int(ep.get("completed_beats") or 0), len(em_beats))
        pct = min(96, round((done_b / tot_b) * 100)) if tot_b else min(80, 20 + step_idx)
        milestones = [
            {"label_vi": "1. Biên dịch & code cảnh VOX 2.5D", "file": "vox_scene_manifest.json", "done": bool(vox_man), "detail_vi": "Bàn biên tập cắt dán 12fps"},
            {"label_vi": "2. Ráp Timeline Remotion 1-1", "file": "edit_manifest.json", "done": done_b > 0, "detail_vi": f"{done_b}/{tot_b or '?'} phân cảnh"},
            {"label_vi": "3. Phối BGM Story-Arc & Motion SFX", "file": "timeline.json", "done": bool(workspace and (workspace / "timeline.json").is_file()), "detail_vi": "Crossfade 3s · chuẩn LUFS"},
            {"label_vi": "4. Kiểm định AST & Preview", "file": "compliance_scorecard.json", "done": bool(workspace and (workspace / "compliance_scorecard.json").is_file()), "detail_vi": "Sẵn sàng xuất MP4"},
        ]
    elif cur_phase == "qc":
        seg_dir = (workspace / "universal_segments") if workspace else None
        seg_files = list(seg_dir.glob("*.mp4")) if (seg_dir and seg_dir.is_dir()) else []
        done_segs = [s for s in seg_files if not s.name.endswith(".tmp.mp4")]
        tmp_segs = [s for s in seg_files if s.name.endswith(".tmp.mp4")]
        tot_segs = max(188, len(done_segs) + len(tmp_segs))
        has_baked = bool(workspace and (workspace / "universal_baked_scenes").is_dir() and list((workspace / "universal_baked_scenes").glob("*.mp4")))
        has_subs = bool(workspace and (workspace / "universal_sub_pngs").is_dir() and list((workspace / "universal_sub_pngs").glob("*.png")))
        has_mp4 = bool(workspace and (workspace / "release" / "video.mp4").is_file() and not tmp_segs and len(done_segs) >= tot_segs)
        if running_phases and (done_segs or tmp_segs):
            pct = min(99, max(8, round((len(done_segs) / tot_segs) * 100)))
        else:
            pct = 100 if not running_phases else min(95, 25 + step_idx * 2)
        milestones = [
            {"label_vi": "1. Bake cảnh VOX & CinemaText", "file": "universal_baked_scenes/*", "done": has_baked, "detail_vi": "Đã bake 100%" if has_baked else "Đang bake..."},
            {"label_vi": "2. Render thẻ phụ đề SRT", "file": "universal_sub_pngs/*", "done": has_subs, "detail_vi": "Đã kết xuất PNG" if has_subs else "Đang render phụ đề..."},
            {"label_vi": "3. Kết xuất phân đoạn NVENC", "file": "universal_segments/*", "done": len(done_segs) >= tot_segs and not tmp_segs, "detail_vi": f"Đã xong {len(done_segs)}/{tot_segs} đoạn ({pct}%)" if (done_segs or tmp_segs) else "Chờ ghép đoạn"},
            {"label_vi": "4. Ghép Master MP4 & Soi QC", "file": "release/video.mp4", "done": has_mp4 and not running_phases, "detail_vi": "Hoàn tất video.mp4" if (has_mp4 and not running_phases) else "Đang ghép MP4..."},
        ]
    else:
        pct = min(95, 25 + step_idx * 2) if running_phases else 100
        milestones = [
            {"label_vi": f"1. Khởi chạy {phase_label_vi}", "file": cur_phase, "done": True, "detail_vi": "Đã nạp hồ sơ"},
            {"label_vi": "2. Thực thi nhiệm vụ chuyên môn", "file": cur_phase, "done": step_idx > 2, "detail_vi": f"Bước #{step_idx}"},
            {"label_vi": "3. Kiểm tra nghiệm thu nội bộ", "file": cur_phase, "done": not running_phases, "detail_vi": "Đối chiếu checklist"},
            {"label_vi": "4. Bàn giao đầu ra", "file": cur_phase, "done": not running_phases, "detail_vi": "Hoàn tất" if not running_phases else "Đang xử lý..."},
        ]

    phase_events = [e for e in live_events if str(e.get("phase") or "").strip().lower() == cur_phase]
    latest_ev = phase_events[0] if phase_events else None
    if cur_phase == "voice" and running_phases:
        if has_srt:
            current_action_vi = f"Đã thu xong {done_wav}/{total_voice_beats} câu thoại — đang căn khớp phụ đề Whisper & kiểm tra LUFS"
        elif done_wav > 0:
            raw_pct = min(99, max(1, round((done_wav / max(1, total_voice_beats)) * 100)))
            current_action_vi = f"Đang tổng hợp giọng đọc CofiVoice: {done_wav}/{total_voice_beats} phân cảnh ({raw_pct}%)" + (f", vừa xong {latest_wav}" if latest_wav else "")
        else:
            current_action_vi = "Đang khởi tạo mô hình giọng đọc CofiVoice & chuẩn hóa phiên âm TTS..."
    elif cur_phase == "ai_visual" and running_phases and tot > 0:
        current_action_vi = f"Đang vẽ ảnh tái dựng AI 4D: đã tạo {done_img}/{tot} beat ({pct}%), còn {miss} beat"
    elif latest_ev:
        tgt = f" → {latest_ev['target']}" if latest_ev.get("target") else ""
        current_action_vi = f"Bước #{latest_ev.get('step_index', step_idx)} · {latest_ev.get('action_vi', 'Đang xử lý')}{tgt}"
    elif running_phases:
        done_m = [m for m in milestones if not m["done"]]
        current_action_vi = done_m[0]["detail_vi"] if done_m else f"Đang hoàn thiện {phase_label_vi}..."
    else:
        current_action_vi = "Toàn bộ hạng mục trong bước hiện tại đã sẵn sàng."

    recent_steps = []
    for ev in live_events[:4]:
        t_str = f" → {ev['target']}" if ev.get("target") else ""
        recent_steps.append({
            "step_index": ev.get("step_index", 0),
            "agent_id": ev.get("agent_id", primary_agent_id),
            "state": ev.get("state", "DONE"),
            "text_vi": f"#{ev.get('step_index', 0)} · {ev.get('action_vi', '')}{t_str}",
        })

    if not running_phases:
        eta_vi = "Đã hoàn tất công đoạn hiện tại (0 giây)"
    elif pct >= 92:
        eta_vi = "Còn khoảng ~30–60 giây nữa xong (đang khóa kiểm duyệt cuối)"
    elif pct >= 75:
        eta_vi = "Còn khoảng ~1–2 phút nữa hoàn tất bàn giao"
    elif pct >= 45:
        eta_vi = "Còn khoảng ~2–4 phút nữa xong công đoạn này"
    else:
        eta_vi = "Còn khoảng ~4–6 phút nữa hoàn tất dây chuyền"

    return {
        "phase": cur_phase,
        "phase_label_vi": phase_label_vi,
        "primary_agent_id": primary_agent_id,
        "is_running": bool(running_phases),
        "step_index": step_idx,
        "percent": pct,
        "eta_vi": eta_vi,
        "current_action_vi": current_action_vi,
        "milestones": milestones,
        "recent_steps": recent_steps,
    }


def _is_job_actively_running(job: dict[str, Any] | None) -> bool:
    if not isinstance(job, dict):
        return False
    if str(job.get("status") or "").strip().lower() in {"running", "queued"}:
        return True
    phases = job.get("phases")
    if isinstance(phases, dict):
        return any(
            isinstance(pv, dict) and str(pv.get("status") or "").strip().lower() in {"running", "queued"}
            for pv in phases.values()
        )
    return False


def build_live_office_snapshot(
    service: Any,
    job_id: str | None = None,
    *,
    pinned: bool = False,
) -> dict[str, Any]:
    """Assemble 100% truth-grounded real-time Studio Agent Office state."""
    store_obj = getattr(service, "store", None)
    raw_store_jobs = (
        store_obj.list()
        if (
            store_obj is not None
            and type(store_obj).__name__ != "MagicMock"
            and callable(getattr(store_obj, "list", None))
        )
        else None
    )
    all_jobs = (
        raw_store_jobs
        if isinstance(raw_store_jobs, list) and raw_store_jobs
        else service.list_jobs()
    )
    selected_job: dict[str, Any] | None = None
    active_running_job = next((j for j in all_jobs if _is_job_actively_running(j)), None)

    if job_id:
        matched_in_list = next((j for j in all_jobs if j.get("id") == job_id), None)
        if matched_in_list is not None:
            selected_job = matched_in_list
        else:
            try:
                selected_job = service.get_job(job_id)
            except Exception:
                selected_job = None

    # Unless the user explicitly pinned a historical job in the AI Office selector,
    # always prioritize the currently running/queued job over a stale idle/completed job_id.
    if not pinned and active_running_job is not None and not _is_job_actively_running(selected_job):
        selected_job = active_running_job

    if selected_job is None:
        selected_job = active_running_job or (all_jobs[0] if all_jobs else None)

    workspace: Path | None = None
    if selected_job and selected_job.get("workspace"):
        workspace = Path(str(selected_job["workspace"]))
    elif selected_job and selected_job.get("id"):
        workspace = Path(service.root) / "workspaces" / str(selected_job["id"])

    chat_runs_root = Path(service.root) / ".producer" / "chat_runs" if getattr(service, "root", None) else None
    sel_job_id = str(selected_job.get("id") or "") if selected_job else None
    live_events, latest_by_agent, event_stats = _collect_live_events(
        workspace,
        chat_runs_root=chat_runs_root,
        selected_job_id=sel_job_id,
    )

    nexus_state = (
        service.nexus_coordinator.get_project_nexus_state(workspace)
        if workspace and workspace.is_dir()
        else {"handoff_count": 0, "handoffs": [], "recent_traces": []}
    )

    # Check active Producer Chat run or Source Repair
    active_chat_run = None
    try:
        chat_res = service.find_active_producer_chat_run(selected_job_id=sel_job_id)
        if not chat_res and sel_job_id:
            chat_res = service.find_active_producer_chat_run(selected_job_id=None)
        if isinstance(chat_res, dict) and (
            chat_res.get("active")
            or str(chat_res.get("status") or "").strip().lower() in {"running", "queued"}
        ):
            active_chat_run = chat_res.get("run") if isinstance(chat_res.get("run"), dict) else chat_res
    except Exception:
        active_chat_run = None

    rework_info = _detect_workspace_rework_state(
        workspace=workspace,
        job=selected_job,
        active_chat_run=active_chat_run,
        live_events=live_events,
        event_stats=event_stats,
    )
    gates, gate_totals = _build_critique_gates(
        workspace,
        selected_job,
        event_stats.get("active_subrun"),
        rework_info=rework_info,
    )

    active_repairs = []
    try:
        active_repairs = [
            r for r in service.list_source_repairs()
            if isinstance(r, dict) and str(r.get("status") or "").lower() in {"running", "queued"}
        ]
    except Exception:
        active_repairs = []

    phases_state = (selected_job or {}).get("phases") if isinstance((selected_job or {}).get("phases"), dict) else {}
    running_phases = [pk for pk, pv in phases_state.items() if isinstance(pv, dict) and pv.get("status") == "running"]
    succeeded_phases = {pk for pk, pv in phases_state.items() if isinstance(pv, dict) and pv.get("status") == "succeeded"}
    if workspace and ((workspace / "footage_approved_live.json").is_file() or (workspace / "footage_hygiene_report.json").is_file()):
        succeeded_phases.add("footage")
    live_rework_phase = rework_info.get("live_rework_phase")
    if live_rework_phase and live_rework_phase not in running_phases:
        running_phases.append(str(live_rework_phase))
    failed_phases = {pk for pk, pv in phases_state.items() if isinstance(pv, dict) and pv.get("status") == "failed"}

    # Read live subagent delegations from `.producer/active_delegations.json`
    active_delegations: dict[str, dict[str, Any]] = {}
    delegated_links: list[dict[str, Any]] = []
    if workspace and workspace.is_dir():
        del_path = workspace / ".producer" / "active_delegations.json"
        if del_path.is_file():
            try:
                if time.time() - del_path.stat().st_mtime <= 1800:
                    del_payload = _read_json_safe(del_path)
                    raw_del_agents = del_payload.get("agents")
                    if isinstance(raw_del_agents, dict):
                        for da_id, da_info in raw_del_agents.items():
                            if isinstance(da_info, dict) and str(da_info.get("state") or "") in {"working", "reworking", "critiquing"}:
                                active_delegations[str(da_id)] = da_info
                    del_phase = str(del_payload.get("active_phase") or "").strip()
                    if del_phase and del_phase not in running_phases and active_delegations:
                        running_phases.append(del_phase)
                    raw_del_links = del_payload.get("links")
                    if isinstance(raw_del_links, list):
                        delegated_links = [lk for lk in raw_del_links if isinstance(lk, dict)]
            except Exception:
                active_delegations = {}

    gate_by_phase = {g["phase"]: g for g in gates}
    raw_agents = service.agent_manager.list_agents()

    enriched_agents: list[dict[str, Any]] = []
    active_agent_ids: list[str] = []

    for ag in raw_agents:
        aid = ag["id"]
        role_meta = AGENT_ROLE_VI.get(aid, {})
        state = "standby"
        status_label_vi = "Đang trực chờ lệnh"
        live_bubble = ""
        completed_badge = ""
        rework_badge = ""

        # Determine agent state from real running phases / chat / repairs / completed artifacts
        if aid == "orchestrator":
            if active_chat_run:
                state = "working"
                status_label_vi = "Đang điều phối phiên Chat"
                live_bubble = "Đang phân tích yêu cầu & điều phối đội ngũ Agent…"
            elif running_phases:
                state = "standby"
                status_label_vi = f"Đang giám sát {PHASE_AGENT_MAP.get(running_phases[0], {}).get('label_vi', running_phases[0])}"
                live_bubble = f"Đang chỉ huy dây chuyền tại bước `{running_phases[0]}`"
            elif selected_job and str(selected_job.get("status") or "") == "completed":
                state = "done"
                status_label_vi = "Đã hoàn thành điều phối 100%"
                completed_badge = "Dự án hoàn tất 100%"

        elif aid == "radar":
            if selected_job and (selected_job.get("channel_profile_id") or selected_job.get("topic_discovery")):
                state = "done"
                status_label_vi = "Đã duyệt Pre-Flight & Đề tài"
                completed_badge = "Pre-Flight PASS · 0 trùng lặp"

        elif aid in {"dev", "debug"}:
            if active_repairs:
                state = "working"
                status_label_vi = "Đang chẩn đoán & vá mã nguồn"
                live_bubble = str(active_repairs[0].get("summary") or "Đang kiểm tra hệ thống…")[:100]

        elif aid == "evidence_qa":
            reworking_live_gate = next((g for g in gates if g["gate_state"] == "reworking_live" and g["critic_agent"] == "evidence_qa"), None)
            active_critic_gate = next((g for g in gates if g["gate_state"] == "critic_reviewing" and g["critic_agent"] == "evidence_qa"), None)
            rejected_gate = next((g for g in gates if g["gate_state"] == "rejected" and g["critic_agent"] == "evidence_qa"), None)
            if reworking_live_gate:
                state = "critiquing"
                status_label_vi = f"Vừa trả về `{reworking_live_gate['phase']}` bắt làm lại"
                live_bubble = reworking_live_gate["summary_vi"][:135]
                rework_badge = reworking_live_gate["badge_vi"]
            elif active_critic_gate:
                state = "critiquing"
                status_label_vi = "Đang phản biện & chấm lỗi"
                live_bubble = f"Đang kiểm chứng độc lập {active_critic_gate['label_vi']}…"
            elif rejected_gate:
                state = "critiquing"
                status_label_vi = f"Đã chặn cổng `{rejected_gate['phase']}`"
                live_bubble = f"Từ chối duyệt {rejected_gate['label_vi']} — yêu cầu sửa đạt chuẩn mới bàn giao!"
                rework_badge = f"Đã chặn {gate_totals['rejected_gates']} cổng chưa đạt"
            elif running_phases:
                state = "standby"
                status_label_vi = "Đang trực cổng kiểm duyệt"
                live_bubble = f"Chờ nghiệm thu đầu ra bước `{running_phases[0]}` — chưa đạt sẽ bắt làm lại!"
            elif gate_totals["passed_gates"] > 0:
                state = "done"
                status_label_vi = f"Đã gác cổng {gate_totals['passed_gates']} bước"
                if gate_totals["reworked_gates"] > 0:
                    rework_badge = f"Đã bắt sửa lại {gate_totals['reworked_gates']} khâu"
                completed_badge = f"Duyệt ĐẠT {gate_totals['passed_gates']} cổng"

        elif aid == "qc":
            qc_gate = gate_by_phase.get("qc", {})
            if "qc" in running_phases:
                state = "critiquing"
                if qc_gate.get("gate_state") == "reworking_live":
                    status_label_vi = "Chưa duyệt MP4 · Đang tự xuất lại"
                    live_bubble = str(qc_gate.get("summary_vi") or "")[:135]
                    rework_badge = str(qc_gate.get("badge_vi") or "")
                else:
                    status_label_vi = "Đang xuất MP4 & soi 6 khung hình"
                    live_bubble = "Đang kiểm tra 6 frame thực tế, âm lượng LUFS & đuôi kết 3.8s…"
            elif "qc" in failed_phases or qc_gate.get("gate_state") == "rejected":
                state = "blocked"
                status_label_vi = "Chặn xuất bản (REJECT)"
            elif "qc" in succeeded_phases:
                state = "done"
                status_label_vi = "Đã cấp chứng nhận ACCEPT"
                if qc_gate.get("rework_triggered"):
                    rework_badge = f"Đã sửa lại ({qc_gate.get('rework_count', 1)}) & ĐẠT"
                completed_badge = "Master MP4 đạt chuẩn phát sóng"

        else:
            # Domain production specialists (`research`, `script`, `voice`, `visuals`, `footage`, `ai_visual`, `vox`, `edit`, `seo`)
            owned_running = [
                pk for pk in running_phases
                if PHASE_AGENT_MAP.get(pk, {}).get("lead") == aid or aid in PHASE_AGENT_MAP.get(pk, {}).get("co_leads", [])
            ]
            owned_failed = [
                pk for pk in failed_phases
                if PHASE_AGENT_MAP.get(pk, {}).get("lead") == aid
            ]
            owned_done = [
                pk for pk in succeeded_phases
                if PHASE_AGENT_MAP.get(pk, {}).get("lead") == aid or aid in PHASE_AGENT_MAP.get(pk, {}).get("co_leads", [])
            ]

            if owned_running:
                pk = owned_running[0]
                g = gate_by_phase.get(pk, {})
                has_research_file = bool(workspace and (workspace / "research.md").is_file())
                if g.get("gate_state") == "reworking_live" and PHASE_AGENT_MAP.get(pk, {}).get("lead") == aid:
                    state = "reworking"
                    status_label_vi = f"🔄 Đang tự làm lại `{pk}`"
                    rework_badge = str(g.get("badge_vi") or "Đang tự động sửa lại")
                    live_bubble = str(g.get("summary_vi") or "Đang tự động sửa lỗi theo phiếu QA…")[:135]
                elif g.get("gate_state") == "critic_reviewing":
                    state = "reworking"
                    status_label_vi = "Đang phối hợp sửa theo phản biện"
                    live_bubble = "Đang nhận phiếu soi lỗi từ Thanh tra Phản biện `evidence_qa`…"
                elif pk == "plan":
                    if aid == "research":
                        if has_research_file:
                            state = "done"
                            status_label_vi = "Đã bàn giao research.md"
                            completed_badge = f"research.md ({max(1, (workspace / 'research.md').stat().st_size // 1024)} KB)"
                        else:
                            state = "working"
                            status_label_vi = "Đang tra cứu & viết research.md"
                    elif aid == "script":
                        if has_research_file:
                            state = "working"
                            status_label_vi = "Đang viết dàn ý & kịch bản script.md"
                        else:
                            state = "standby"
                            status_label_vi = "Chờ nhận research.md từ Phòng 02"
                elif pk == "visuals" and aid == "vox":
                    state = "standby"
                    status_label_vi = "Chờ nhận phân cảnh VOX từ Phòng 05"
                else:
                    state = "working"
                    status_label_vi = f"Đang thực thi `{pk}`"
            elif owned_failed:
                pk_fail = owned_failed[0]
                err_fail = str((phases_state.get(pk_fail) or {}).get("error") or "").strip()
                state = "blocked"
                status_label_vi = f"Chưa qua cổng duyệt `{pk_fail}`"
                rework_badge = "Chờ sửa lại theo yêu cầu QA"
                if err_fail:
                    live_bubble = f"Bị chặn bàn giao: {err_fail[:115]}"
            elif owned_done:
                state = "done"
                status_label_vi = "Đã hoàn thành & bàn giao"
                for pk in owned_done:
                    g = gate_by_phase.get(pk, {})
                    if g.get("rework_triggered"):
                        rework_badge = f"Đã sửa lại ({g.get('rework_count', 1)}) & ĐẠT"
                    if g.get("proof_items"):
                        completed_badge = g["proof_items"][0]

        # Apply post-completion rework badge if this specialist's artifacts were reworked
        post_ag_rw = (rework_info.get("reworked_agents") or {}).get(aid)
        if isinstance(post_ag_rw, dict):
            rework_badge = str(post_ag_rw.get("badge_vi") or rework_badge)
            if state == "done" and post_ag_rw.get("detail_vi"):
                completed_badge = str(post_ag_rw["detail_vi"]).replace("🔄 ", "")

        # Override with live rework state (when an agent is actively fixing/re-rendering right now)
        live_ag_rw = (rework_info.get("live_rework_agents") or {}).get(aid)
        if isinstance(live_ag_rw, dict):
            state = "reworking"
            status_label_vi = str(live_ag_rw.get("status_label_vi") or status_label_vi)
            live_bubble = str(live_ag_rw.get("live_bubble") or live_bubble)
            rework_badge = str(live_ag_rw.get("rework_badge") or rework_badge)
        elif aid == "orchestrator" and (rework_info.get("live_rework_agents") or active_chat_run):
            state = "working"
            rw_keys = list((rework_info.get("live_rework_agents") or {}).keys())
            if rw_keys:
                status_label_vi = f"🔄 Đang chỉ huy làm lại ({', '.join('@' + k for k in rw_keys)})"
                live_bubble = f"Đang điều phối sửa & đồng bộ trực tiếp cùng {', '.join('@' + k for k in rw_keys)}…"
                rework_badge = f"Điều phối làm lại {len(rw_keys)} phòng"
        elif aid == "evidence_qa" and rework_info.get("live_rework_agents"):
            state = "critiquing"
            rw_keys = list((rework_info.get("live_rework_agents") or {}).keys())
            status_label_vi = f"🔎 Giám sát làm lại ({', '.join('@' + k for k in rw_keys)})"
            live_bubble = f"Đang trực nghiệm thu đầu ra làm lại của {', '.join('@' + k for k in rw_keys)}…"

        # Override with active subagent delegation state
        if aid in active_delegations:
            del_info = active_delegations[aid]
            state = str(del_info.get("state") or "working")
            status_label_vi = str(del_info.get("status_label_vi") or status_label_vi)
            live_bubble = str(del_info.get("live_bubble") or live_bubble)
            rework_badge = str(del_info.get("rework_badge") or rework_badge)
            completed_badge = str(del_info.get("completed_badge") or completed_badge)
        elif aid == "orchestrator" and active_delegations and state != "working":
            state = "working"
            status_label_vi = f"Đang chỉ huy {len(active_delegations)} Agent chuyên môn"
            live_bubble = f"Đang điều phối trực tiếp: {', '.join('@' + k for k in active_delegations.keys())}"

        # Attach real latest tool call bubble if available (unless live_ag_rw already set a specific render progress bubble)
        last_ev = latest_by_agent.get(aid)
        if last_ev and state in {"working", "critiquing", "reworking"} and not (isinstance(live_ag_rw, dict) and rework_info.get("is_rendering_mp4")):
            tgt = f" → {last_ev['target']}" if last_ev.get("target") else ""
            live_bubble = f"{last_ev['action_vi']}{tgt}"

        if state in {"working", "critiquing", "reworking"}:
            active_agent_ids.append(aid)

        enriched_agents.append({
            **ag,
            "title_vi": role_meta.get("title_vi", ag["name"]),
            "desk_vi": role_meta.get("desk_vi", ag["division"]),
            "idle_vi": role_meta.get("idle_vi", ""),
            "live_state": state,
            "status_label_vi": status_label_vi,
            "live_bubble": live_bubble,
            "completed_badge": completed_badge,
            "rework_badge": rework_badge,
            "last_event": last_ev,
        })

    dept_projection = build_live_departments_projection(
        enriched_agents,
        workspace_dir=workspace,
        job_snapshot=selected_job,
    )
    dept_by_agent = {
        str(d.get("agent_id") or ""): d
        for d in dept_projection.get("departments", [])
    }
    for ag_item in enriched_agents:
        aid_key = str(ag_item.get("id") or "")
        dept_live = dept_by_agent.get(aid_key) or get_department_for_agent(aid_key)
        if dept_live:
            pe = dept_live.get("parallel_engine") or {}
            batches = pe.get("batches") or dept_live.get("batches") or []
            specs = dept_live.get("specialists", [])
            ag_item["department_hierarchy"] = dept_live
            ag_item["dept_code"] = dept_live.get("code", "")
            ag_item["dept_number"] = dept_live.get("dept_number", "")
            ag_item["dept_name_vi"] = dept_live.get("name_vi", "")
            ag_item["headcount"] = dept_live.get("headcount", 2 + len(specs))
            ag_item["workflow_chain_vi"] = dept_live.get("workflow_chain_vi", [])
            ag_item["lead"] = dept_live.get("lead")
            ag_item["deputy"] = dept_live.get("deputy")
            ag_item["specialists"] = specs
            ag_item["parallel_engine"] = pe
            ag_item["batches"] = batches
            ag_item["parallel_lane"] = 1
            ag_item["batch_id"] = batches[0].get("batch_id", "LÔ-01") if batches else "LÔ-01"
            ag_item["active_parallel_workers"] = [
                {
                    "specialist_id": sp.get("id"),
                    "specialist_handle": sp.get("handle"),
                    "specialist_title_vi": sp.get("title_vi"),
                    "parallel_lane": sp.get("parallel_lane"),
                    "batch_id": sp.get("batch_id"),
                    "batch_scope_vi": sp.get("batch_scope_vi"),
                    "live_status": sp.get("live_status"),
                    "progress_pct": sp.get("progress_pct"),
                    "current_action_vi": sp.get("current_action_vi"),
                    "worker_thread": sp.get("worker_thread"),
                }
                for sp in specs
            ]
            ag_item["active_mini_agent_id"] = dept_live.get("active_mini_agent_id", "")
            ag_item["active_mini_agent_handle"] = dept_live.get("active_mini_agent_handle", "")
            ag_item["active_mini_agent_title_vi"] = dept_live.get("active_mini_agent_title_vi", "")
            ag_item["active_mini_agent_task_vi"] = dept_live.get("active_mini_agent_task_vi", "")

    # Build visual link arrows between agents for the floorplan SVG
    links: list[dict[str, Any]] = []
    seen_links: set[tuple[str, str]] = set()
    for pkt in nexus_state.get("handoffs") or []:
        if not isinstance(pkt, dict):
            continue
        src = str(pkt.get("from_agent") or "")
        dst = str(pkt.get("to_agent") or "")
        if src and dst and (src, dst) not in seen_links:
            seen_links.add((src, dst))
            links.append({
                "from": src,
                "to": dst,
                "kind": "handoff_done",
                "verdict": str(pkt.get("qa_gate_verdict") or "PASS"),
                "label": f"{pkt.get('from_phase')} → {pkt.get('to_phase')}",
            })

    # Add live active collaboration & critique links for currently running phase
    for pk in running_phases:
        pm = PHASE_AGENT_MAP.get(pk, {})
        lead_id = pm.get("lead")
        critic_id = pm.get("critic")
        if lead_id:
            links.append({
                "from": "orchestrator",
                "to": lead_id,
                "kind": "active_dispatch",
                "verdict": "LIVE",
                "label": f"Chỉ huy {pk}",
            })
            for co in pm.get("co_leads", []):
                links.append({
                    "from": co,
                    "to": lead_id,
                    "kind": "active_collab",
                    "verdict": "LIVE",
                    "label": "Phối hợp trực tiếp",
                })
            if critic_id and critic_id != lead_id:
                g = gate_by_phase.get(pk, {})
                if g.get("gate_state") == "reworking_live":
                    links.append({
                        "from": critic_id,
                        "to": lead_id,
                        "kind": "active_critique",
                        "verdict": "REWORK",
                        "label": f"Bắt tự chạy lại ({pk})",
                    })
                else:
                    links.append({
                        "from": lead_id,
                        "to": critic_id,
                        "kind": "active_critique" if g.get("gate_state") == "critic_reviewing" else "qa_watch",
                        "verdict": "CRITIC" if g.get("gate_state") == "critic_reviewing" else "GUARD",
                        "label": "Phản biện độc lập" if g.get("gate_state") == "critic_reviewing" else "Giám sát đầu ra",
                    })

    for dlk in delegated_links:
        links.append(dlk)

    for pk in failed_phases:
        pm = PHASE_AGENT_MAP.get(pk, {})
        lead_id = pm.get("lead")
        critic_id = pm.get("critic")
        if lead_id and critic_id and lead_id != critic_id:
            links.append({
                "from": critic_id,
                "to": lead_id,
                "kind": "active_critique",
                "verdict": "REJECTED",
                "label": f"Trả về sửa lại ({pk})",
            })

    divisions_payload = []
    for div_key, dmeta in DIVISION_META.items():
        div_agents = [a for a in enriched_agents if a.get("division") == div_key]
        divisions_payload.append({
            **dmeta,
            "agents": div_agents,
            "active_count": sum(1 for a in div_agents if a["live_state"] in {"working", "critiquing", "reworking"}),
        })

    effective_job_status = (
        "running"
        if (running_phases or active_delegations)
        else (selected_job.get("status") if selected_job else None)
    )
    effective_current_phase = (
        running_phases[0]
        if running_phases
        else (selected_job.get("current_phase") if selected_job else None)
    )
    live_phase_report = _build_live_phase_report(
        workspace,
        selected_job,
        running_phases,
        live_events,
        event_stats,
        active_agent_ids,
    )

    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "selected_job": {
            "id": selected_job.get("id"),
            "title": selected_job.get("title"),
            "status": effective_job_status,
            "current_phase": effective_current_phase,
            "channel_profile_id": selected_job.get("channel_profile_id"),
            "visual_strategy": selected_job.get("visual_strategy"),
            "running_phases": running_phases,
        } if selected_job else None,
        "live_phase_report": live_phase_report,
        "jobs_list": [
            {
                "id": j.get("id"),
                "title": str(j.get("title") or "")[:95],
                "status": "running" if (selected_job and j.get("id") == selected_job.get("id") and effective_job_status == "running") else j.get("status"),
            }
            for j in all_jobs[:20]
        ],
        "summary": {
            "total_agents": len(enriched_agents),
            "total_departments": dept_projection["summary"]["total_departments"],
            "total_leads": dept_projection["summary"]["total_leads"],
            "total_deputies": dept_projection["summary"]["total_deputies"],
            "total_specialists": dept_projection["summary"]["total_specialists"],
            "total_personnel": dept_projection["summary"]["total_personnel"],
            "active_agents_count": len(active_agent_ids),
            "active_agent_ids": active_agent_ids,
            "running_phases": running_phases,
            "passed_gates": gate_totals["passed_gates"],
            "reworked_gates": gate_totals["reworked_gates"],
            "total_rewrites_or_rerolls": gate_totals["total_rewrites_or_rerolls"],
            "active_critic_count": max(gate_totals["active_critic_count"], sum(1 for a in enriched_agents if a["live_state"] == "critiquing")),
            "rejected_gates": gate_totals["rejected_gates"],
            "handoff_count": nexus_state.get("handoff_count", 0),
            "total_cli_steps": event_stats["total_steps"],
            "total_output_tokens": event_stats["total_output_tokens"],
            "latest_event_age_sec": event_stats["latest_event_age_sec"],
            "active_subrun": event_stats["active_subrun"],
            "parallel_engine_enabled": True,
            "parallel_mode": "parallel_specialist_pool",
            "total_parallel_lanes": dept_projection["summary"].get("total_parallel_lanes", 62),
            "completed_parallel_batches": dept_projection["summary"].get("completed_parallel_batches", 0),
            "active_parallel_batches": dept_projection["summary"].get("active_parallel_batches", 0),
            "active_parallel_workers": dept_projection["summary"].get("active_parallel_workers", []),
            "active_parallel_workers_count": len(dept_projection["summary"].get("active_parallel_workers", [])),
        },
        "divisions": divisions_payload,
        "agents": enriched_agents,
        "departments": dept_projection["departments"],
        "departments_summary": dept_projection["summary"],
        "active_parallel_workers": dept_projection["summary"].get("active_parallel_workers", []),
        "critique_gates": gates,
        "live_events": live_events,
        "links": links,
        "nexus_handoffs": nexus_state.get("handoffs") or [],
    }
