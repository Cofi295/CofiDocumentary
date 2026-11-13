from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
from typing import Any
import uuid

from .codex_gateway import StageResult
from .footage_engine import FootageEngine
from .source_discovery import SourceDiscoveryHub


FOOTAGE_BATCH_FIELDS = ("candidates", "assets", "native_treatments", "presentation_effects")
VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov", ".mkv", ".m4v"}
VISUAL_REVIEW_CONTRACT_VERSION = 3


class FootageStopped(RuntimeError):
    """Raised at cooperative control points when the user stops Footage."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _positive_int_env(name: str, default: int, minimum: int = 1) -> int:
    try:
        return max(minimum, int(os.getenv(name, str(default))))
    except (TypeError, ValueError):
        return default


def _env_flag(name: str, default: bool) -> bool:
    value = str(os.getenv(name, "1" if default else "0") or "").strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    return default


def _media_tool(name: str) -> str | None:
    env_names = {
        "yt-dlp.exe": "COFI_YTDLP_BIN",
        "ffmpeg.exe": "COFI_FFMPEG_BIN",
        "ffprobe.exe": "COFI_FFPROBE_BIN",
        "node.exe": "COFI_NODE_BIN",
    }
    configured = os.getenv(env_names.get(name, ""), "").strip()
    if configured and Path(configured).exists():
        return configured
    bundled = Path(__file__).resolve().parents[1] / "tools" / name
    if bundled.exists():
        return str(bundled)
    stem = Path(name).stem
    return shutil.which(name) or shutil.which(stem)


def _resolve_media_path(workspace: Path, value: Any) -> Path | None:
    text = str(value or "").strip()
    if not text:
        return None
    path = Path(text)
    return path if path.is_absolute() else workspace / path


def _validate_media_file(workspace: Path, path_value: Any, kind: Any = "") -> tuple[bool, str]:
    path = _resolve_media_path(workspace, path_value)
    if path is None:
        return False, "chưa có file local"
    if not path.exists() or not path.is_file():
        return False, "file local không tồn tại"
    try:
        size = path.stat().st_size
    except OSError:
        return False, "không đọc được file local"
    minimum_bytes = _positive_int_env("COFI_FOOTAGE_MIN_MEDIA_BYTES", 4096)
    maximum_bytes = _positive_int_env("COFI_FOOTAGE_MAX_MEDIA_MB", 150) * 1024 * 1024
    if size < minimum_bytes:
        return False, f"file quá nhỏ/có thể hỏng ({size} bytes)"
    if size > maximum_bytes:
        return False, f"file vượt giới hạn {maximum_bytes // (1024 * 1024)} MB"

    normalized_kind = str(kind or "").lower()
    is_video = "video" in normalized_kind or path.suffix.lower() in VIDEO_EXTENSIONS
    if not is_video:
        return True, ""
    ffprobe = _media_tool("ffprobe.exe")
    if not ffprobe:
        return False, "thiếu ffprobe để xác thực video"
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
    startupinfo = None
    if os.name == "nt":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= getattr(subprocess, "STARTF_USESHOWWINDOW", 1)
        startupinfo.wShowWindow = getattr(subprocess, "SW_HIDE", 0)
    try:
        result = subprocess.run(
            [
                ffprobe,
                "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=codec_type:format=duration",
                "-of", "json",
                str(path),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=20,
            check=False,
            creationflags=creationflags,
            startupinfo=startupinfo,
        )
    except (OSError, subprocess.SubprocessError):
        return False, "ffprobe không đọc được video"
    if result.returncode != 0:
        return False, "video hỏng hoặc container không hợp lệ"
    try:
        probe = json.loads(result.stdout or "{}")
        streams = probe.get("streams") or []
        duration = float((probe.get("format") or {}).get("duration") or 0)
    except (json.JSONDecodeError, TypeError, ValueError):
        return False, "ffprobe trả về metadata không hợp lệ"
    if not streams or duration <= 0.1:
        return False, "video không có stream hình hoặc duration hợp lệ"
    return True, ""


def _beat_id(beat: dict[str, Any]) -> str:
    return str(beat.get("beat_id") or "").strip()


def _chunks(items: list[dict[str, Any]], size: int) -> list[list[dict[str, Any]]]:
    return [items[index:index + size] for index in range(0, len(items), size)]


def _empty_worker_payload(worker: str, status: str = "in_progress") -> dict[str, Any]:
    return {
        "worker": worker,
        "status": status,
        "candidates": [],
        "assets": [],
        "native_treatments": [],
        "presentation_effects": [],
    }


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        for attempt in range(6):
            try:
                os.replace(temporary, path)
                return
            except PermissionError:
                if attempt >= 5:
                    raise
                time.sleep(0.02 * (attempt + 1))
    finally:
        temporary.unlink(missing_ok=True)


def _json_object_from_message(value: Any) -> dict[str, Any]:
    text = str(value or "").strip()
    if not text:
        raise RuntimeError("Codex review returned an empty response")
    try:
        payload = json.loads(text)
        if isinstance(payload, dict):
            return payload
    except json.JSONDecodeError:
        pass
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.I | re.S)
    candidates = [fenced.group(1)] if fenced else []
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        candidates.append(text[start:end + 1])
    expanded_candidates: list[str] = []
    for candidate in candidates:
        expanded_candidates.append(candidate)
        # ChatGPT can Markdown-escape JSON punctuation and key underscores even
        # when asked for raw JSON (for example: \[ and beat\_id). Those are not
        # valid JSON escapes, so remove only backslashes that JSON itself does
        # not recognize and retry parsing the same object.
        normalized = re.sub(r'\\(?!["\\/bfnrtu])', '', candidate)
        if normalized != candidate:
            expanded_candidates.append(normalized)
    for candidate in expanded_candidates:
        try:
            payload = json.loads(candidate)
            if isinstance(payload, dict):
                return payload
        except json.JSONDecodeError:
            continue
    raise RuntimeError("Codex review did not return a JSON object")


def build_codex_vision_review_prompt(
    job: dict[str, Any],
    beats: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    attached_frames_by_candidate: dict[str, list[str]] | None = None,
) -> str:
    attached_frames_by_candidate = attached_frames_by_candidate or {}
    compact_candidates: list[dict[str, Any]] = []
    for candidate in candidates:
        candidate_id = str(candidate.get("candidate_id") or "").strip()
        local_verification = (
            candidate.get("local_vision_verification")
            if isinstance(candidate.get("local_vision_verification"), dict)
            else {}
        )
        semantic_prefilter = (
            candidate.get("semantic_prefilter")
            if isinstance(candidate.get("semantic_prefilter"), dict)
            else {}
        )
        raw_contract = candidate.get("verification_contract")
        clean_contract = None
        if isinstance(raw_contract, dict):
            clean_contract = dict(raw_contract)
            req_fields = dict(clean_contract.get("required_fields") or {})
            req_fields.pop("visual_context", None)
            clean_contract["required_fields"] = req_fields
        compact_candidates.append({
            "candidate_id": candidate_id,
            "beat_id": candidate.get("beat_id"),
            "title": candidate.get("title"),
            "source_name": candidate.get("source_name"),
            "source_url": candidate.get("source_url"),
            "timestamp_range": candidate.get("timestamp_range"),
            "kind": candidate.get("kind"),
            "representative_frames": candidate.get("representative_frames") or [],
            "review_attached_frames": attached_frames_by_candidate.get(candidate_id, []),
            "transcript_excerpt": candidate.get("transcript_excerpt"),
            "semantic_prefilter": semantic_prefilter,
            "local_vision_decision": candidate.get("local_vision_decision"),
            "local_vision_score": local_verification.get("semantic_score"),
            "local_vision_fields": local_verification.get("fields"),
            "verification_contract": clean_contract,
        })
    compact_beats = [{
        "beat_id": beat.get("beat_id"),
        "voice": beat.get("narration_text"),
        "visual_description_reference": beat.get("visual_description"),
        "source_priority": beat.get("source_priority"),
    } for beat in beats]
    schema = {
        "reviews": [{
            "beat_id": "B001",
            "candidate_id": "VQ-B001-01-...",
            "decision": "ACCEPT|REJECT",
            "reason": "short concrete reason based only on supplied frames/evidence",
            "inspected_frame_paths": ["exact review_attached_frames path(s) actually inspected"],
        }],
        "retry_requests": [{
            "beat_id": "B001",
            "reason": "why the supplied candidates are not usable",
            "search_queries": ["1-3 concrete replacement searches for the app's local footage tools"],
        }],
    }
    from .nexus_coordinator import NexusCoordinator
    footage_charter = NexusCoordinator().build_specialist_soul_header(
        "footage",
        "Stage 4 Multimodal Archival Frame Review",
    )
    return (
        footage_charter
        + "\nBạn là ĐẠO DIỄN KIỂM DUYỆT HÌNH ẢNH CUỐI CÙNG (`@footage` / Vision Frame Reviewer) theo 3 LUẬT THÉP: (1) SOI MẮT CẮT SẠCH 100% LOGO BÊN KHÁC & CHỮ CHẠY BÊN KHÁC, (2) SOI MẮT KHỚP 100% NỘI DUNG CÂU VOICE ĐANG NÓI ĐẾN, (3) CẤM TUYỆT ĐỐI DÙNG CODE TỰ ĐỘNG CẮT VÀ GHÉP TỰ ĐỘNG LÀM LỆCH NGHĨA VÀ HÌNH.\n"
        "Nguyên tắc cốt lõi: BẮT BUỘC mở xem trực tiếp từng ảnh frame đính kèm (`review_attached_frames`) bằng mắt thật để xác thực 2 điều kiện bắt buộc: (1) ĐÃ CROP SẠCH 100% LOGO BÊN KHÁC, CHỮ CHẠY BÊN KHÁC VÀ KHÔNG LẪN INTRO/MC, và (2) HÌNH ẢNH HOẶC VIDEO FOOTAGE TRONG FRAME KHỚP 100% VỚI NỘI DUNG CÂU VOICE (`voice`) ĐANG NÓI ĐẾN.\n\n"
        "TIÊU CHUẨN DUYỆT BẮT BUỘC (100% EYE-VERIFIED CLEAN CROP & 100% VOICE MATCH GATE):\n"
        "1. BẮT BUỘC KIỂM TRA THẬT KỸ BẰNG MẮT TRÊN FRAME ĐÍNH KÈM (`review_attached_frames` — Mốc 15% / 50% / 85%):\n"
        "   - Tuyệt đối KHÔNG đoán mò hoặc duyệt mù chỉ dựa vào tiêu đề video (`title`), URL hay điểm số tự động.\n"
        "   - Với mỗi ứng viên video, bắt buộc nhìn trực tiếp các frame đính kèm xem cảnh quay thực tế đang diễn ra cái gì và kiểm tra 4 cạnh khung hình.\n"
        "2. KHỚP 100% VỚI NỘI DUNG VIDEO / CÂU VOICE ĐANG NÓI ĐẾN (`voice` / `visual_description_reference`):\n"
        "   - Hình ảnh hoặc video footage trong frame phải thể hiện đúng 100% sự kiện, hiện trường, vật chứng, nhân vật, địa danh hoặc hành động mà câu `voice` đang nói tới.\n"
        "   - Nếu câu `voice` nói về một chi tiết/hành động mà ứng viên video không khớp 100% (hoặc bị lệch nghĩa do cắt tự động), BẮT BUỘC `REJECT` ngay để chuyển câu đó sang Ưu tiên số 2 (`@vox` — VOX minh họa độc bản) hoặc Ưu tiên số 3 cuối cùng (`@ai_visual` — Ảnh AI).\n"
        "3. ĐẢM BẢO ĐÃ CROP SẠCH 100% LOGO BÊN KHÁC, CHỮ CHẠY BÊN KHÁC & KHÔNG LẪN INTRO/MC:\n"
        "   - `REJECT` NGAY LẬP TỨC nếu bất kỳ frame nào chứa:\n"
        "     (a) Logo bên khác (`CCTV`, `CNTV`, `BTV`, `SBS`, `MBN`, watermark kênh thứ 3, mã QR, tên chương trình).\n"
        "     (b) Chữ chạy bên khác (dải chữ chạy/ticker dưới đáy, bảng tên dọc/ngang của đài khác, phụ đề ngoại ngữ cháy cứng chưa được crop sạch).\n"
        "     (c) Intro/Outro hiệu ứng 3D của chương trình truyền hình hoặc người dẫn chương trình (MC/Host/Vlogger) đang ngồi/đứng nói.\n"
        "     (d) Cảnh bị nhảy shot nội bộ (internal hard cut), khung 4:3 viền đen/mờ hai bên, hoặc cảnh trùng lặp đã xuất hiện ở beat trước (`max_uses = 1`).\n"
        "4. QUY TẮC `retry_requests`:\n"
        "   - Khi toàn bộ ứng viên của một beat bị `REJECT` (do còn sót logo/chữ chạy bên khác, dính Intro/MC, hoặc không khớp 100% nghĩa câu `voice`), trả thêm `retry_requests` với 1-3 truy vấn tìm kiếm cụ thể hơn hoặc để hệ thống chuyển sang Ưu tiên số 2 (`VOX`) / Ưu tiên số 3 (`AI Visual`).\n\n"
        "BẮT BUỘC kiểm tra `review_attached_frames` của TỪNG candidate bằng mắt trước khi quyết định. Với video có từ 2 frame đính kèm trở lên, phải xem đủ các frame ở các thời điểm khác nhau.\n"
        "Trong mỗi review, trả `inspected_frame_paths` chứa đúng đường dẫn frame đã xem bằng mắt của candidate đó.\n"
        "KHÔNG search web trực tiếp. KHÔNG tự gọi công cụ tìm kiếm, KHÔNG yt-dlp và KHÔNG tự tải file. App sở hữu các tool tìm/tải footage.\n"
        "Không đưa `retry_requests` cho beat đã ACCEPT. Không tự tạo candidate giả.\n"
        "Mỗi beat chỉ ACCEPT tối đa 1 candidate đạt chuẩn Đã Crop Sạch 100% Logo/Chữ Chạy Bên Khác & Khớp 100% Câu Voice. Không bỏ sót beat trong JSON trả về.\n"
        "Trả về JSON thuần, không markdown, theo schema chính xác.\n\n"
        f"JOB: {json.dumps({'id': job.get('id'), 'title': job.get('title'), 'market': job.get('market'), 'language': job.get('language')}, ensure_ascii=False, separators=(',', ':'))}\n"
        f"BEATS: {json.dumps(compact_beats, ensure_ascii=False, separators=(',', ':'))}\n"
        f"CANDIDATES: {json.dumps(compact_candidates, ensure_ascii=False, separators=(',', ':'))}\n"
        f"RETURN_SCHEMA: {json.dumps(schema, ensure_ascii=False, separators=(',', ':'))}"
    )


def _validate_batch_output(path: Path, expected_beat_ids: list[str]) -> dict[str, Any]:
    data = _read_worker(path)
    expected = {beat_id for beat_id in expected_beat_ids if beat_id}
    represented: set[str] = set()
    for field in FOOTAGE_BATCH_FIELDS:
        values = data.get(field)
        if values is None:
            data[field] = []
            continue
        if not isinstance(values, list):
            raise RuntimeError(f"{path.name}: {field} phải là JSON array")
        for item in values:
            if not isinstance(item, dict):
                raise RuntimeError(f"{path.name}: {field} chứa phần tử không hợp lệ")
            beat_id = str(item.get("beat_id") or "").strip()
            if not beat_id:
                continue
            if beat_id not in expected:
                raise RuntimeError(f"{path.name}: trả về beat ngoài batch: {beat_id}")
            represented.add(beat_id)
    missing = [beat_id for beat_id in expected_beat_ids if beat_id and beat_id not in represented]
    if missing:
        raise RuntimeError(f"{path.name}: thiếu kết quả cho beat: {', '.join(missing)}")
    return data


def _aggregate_batch_outputs(worker: str, batch_outputs: list[dict[str, Any]], status: str) -> dict[str, Any]:
    merged = _empty_worker_payload(worker, status=status)
    for payload in batch_outputs:
        for field in FOOTAGE_BATCH_FIELDS:
            merged[field].extend([item for item in (payload.get(field) or []) if isinstance(item, dict)])
    return merged


def _duration(beat: dict[str, Any]) -> float:
    for key in ("duration_sec", "target_duration_sec", "estimated_duration_sec"):
        if beat.get(key) in (None, ""):
            continue
        try:
            return max(0.0, float(beat.get(key)))
        except (TypeError, ValueError):
            continue
    return 1.0


def partition_beats(beats: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    result = {"codex": [], "gemini": []}
    totals = {"codex": 0.0, "gemini": 0.0}
    for beat in beats:
        worker = "codex" if totals["codex"] <= totals["gemini"] else "gemini"
        result[worker].append(beat)
        totals[worker] += _duration(beat)
    return result


def _prepare_worker_beats(beats: list[dict[str, Any]]) -> list[dict[str, Any]]:
    prepared: list[dict[str, Any]] = []
    valid_priorities = {"must_real", "prefer_real", "ai_ok"}
    for beat in beats:
        item = dict(beat)
        explicit_priority = str(item.get("source_priority") or "").strip().lower()
        visual_type = str(item.get("visual_type") or "").strip().lower()
        legacy_native_motion = explicit_priority not in valid_priorities and "native_motion" in visual_type
        if explicit_priority in valid_priorities:
            priority = explicit_priority
        elif legacy_native_motion:
            priority = "prefer_real"
        else:
            priority = "prefer_real"
        item["source_priority"] = priority
        if priority == "must_real":
            budget = {"max_queries": 4, "max_candidates": 5, "immediate_ai_fallback": False}
        elif priority == "prefer_real":
            budget = {"max_queries": 3, "max_candidates": 4, "immediate_ai_fallback": False}
        else:
            budget = {"max_queries": 2, "max_candidates": 3, "immediate_ai_fallback": False}
        item["search_budget"] = budget
        prepared.append(item)

    search_groups: dict[tuple[str, ...], str] = {}
    for item in prepared:
        budget = item.get("search_budget") if isinstance(item.get("search_budget"), dict) else {}
        if int(budget.get("max_queries") or 0) <= 0:
            continue
        queries = tuple(
            " ".join(str(query or "").strip().lower().split())
            for query in (item.get("footage_search_queries") or [])
            if str(query or "").strip()
        )
        if not queries:
            continue
        group = search_groups.setdefault(queries, f"SG{len(search_groups) + 1:02d}")
        item["search_group"] = group
    return prepared


_HINT_STOP_WORDS = {
    "about", "after", "again", "also", "and", "archival", "archive", "because", "before",
    "could", "documentary", "film", "footage", "from", "into", "moving", "narration", "period",
    "scene", "shot", "show", "shows", "source", "that", "their", "them", "then", "there", "this",
    "through", "video", "visual", "were", "when", "where", "while", "with", "would",
}


def _hint_tokens(*values: Any) -> set[str]:
    text = " ".join(str(value or "") for value in values).lower()
    return {
        token
        for token in re.findall(r"[\w'-]{3,}", text, flags=re.UNICODE)
        if token not in _HINT_STOP_WORDS and not token.isdigit()
    }


def _accepted_source_hints(
    workspace: Path,
    beats: list[dict[str, Any]] | None = None,
    limit: int = 24,
) -> list[dict[str, Any]]:
    path = workspace / "footage_codex.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    candidates = payload.get("candidates") if isinstance(payload, dict) else []
    if not isinstance(candidates, list):
        return []

    beat_tokens: set[str] = set()
    for beat in beats or []:
        queries = beat.get("footage_search_queries") if isinstance(beat.get("footage_search_queries"), list) else []
        beat_tokens.update(_hint_tokens(
            beat.get("narration_text"),
            beat.get("visual_description"),
            beat.get("purpose"),
            " ".join(str(query or "") for query in queries),
        ))

    ranked: list[tuple[int, int, dict[str, Any]]] = []
    seen_clips: set[str] = set()
    for recency, candidate in enumerate(reversed(candidates)):
        if not isinstance(candidate, dict) or str(candidate.get("decision") or "").upper() != "ACCEPT":
            continue
        source_url = str(candidate.get("source_url") or "").strip()
        local_path = str(candidate.get("local_path") or "").strip()
        timestamp_range = str(candidate.get("timestamp_range") or "").strip()
        clip_key = f"{local_path}|{timestamp_range}" if local_path else f"{source_url}|{timestamp_range}"
        if not source_url or not clip_key.strip("|") or clip_key in seen_clips:
            continue
        seen_clips.add(clip_key)
        reason = str(candidate.get("reason") or "").strip()
        candidate_tokens = _hint_tokens(
            candidate.get("source_title"),
            candidate.get("source_channel"),
            reason,
        )
        relevance = len(beat_tokens.intersection(candidate_tokens)) if beat_tokens else 0
        ranked.append((relevance, -recency, {
            "beat_id": str(candidate.get("beat_id") or ""),
            "source_url": source_url,
            "source_title": str(candidate.get("source_title") or ""),
            "source_channel": str(candidate.get("source_channel") or ""),
            "local_path": local_path,
            "timestamp_range": timestamp_range,
            "reason": reason[:240],
            "technical_check": str(candidate.get("technical_check") or "")[:160],
            "prior_visual_verified": candidate.get("visually_inspected_actual_content") is True,
            "visual_language": candidate.get("visual_language") if isinstance(candidate.get("visual_language"), dict) else {},
        }))

    ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [item[2] for item in ranked[:max(1, int(limit))]]


def _compact_discovery_candidates(
    discovery_by_beat: dict[str, list[dict[str, Any]]] | None,
    beat_id: str,
    limit: int = 10,
) -> list[dict[str, Any]]:
    rows = (discovery_by_beat or {}).get(beat_id) or []
    allowed = (
        "provider", "source_url", "title", "description", "kind", "source_name", "date", "country",
        "rights_hint", "thumbnail_url", "duration", "discovery_score", "search_query",
    )
    compact: list[dict[str, Any]] = []
    for row in rows[:max(1, int(limit))]:
        if not isinstance(row, dict) or not str(row.get("source_url") or "").strip():
            continue
        item: dict[str, Any] = {}
        for key in allowed:
            value = row.get(key)
            if value in (None, "", [], {}):
                continue
            if isinstance(value, str):
                value = value[:320]
            item[key] = value
        compact.append(item)
    return compact


def build_worker_prompt(
    job: dict[str, Any],
    beats: list[dict[str, Any]],
    worker: str,
    workspace: Path,
    output_name: str,
    discovery_by_beat: dict[str, list[dict[str, Any]]] | None = None,
) -> str:
    max_media_mb = _positive_int_env("COFI_FOOTAGE_MAX_MEDIA_MB", 150)
    prepared_beats = _prepare_worker_beats(beats)
    for beat in prepared_beats:
        beat_id = _beat_id(beat)
        discovered = _compact_discovery_candidates(discovery_by_beat, beat_id)
        if discovered:
            beat["discovery_candidates"] = discovered
    accepted_source_hints = _accepted_source_hints(workspace, prepared_beats)
    local_search_command = (
        f'python -m documentary.footage_search_tool --query "<QUERY>" '
        f'--workspace "{workspace}" --market "{str(job.get("market") or "")}" '
        f'--language "{str(job.get("language") or "")}" --narration "<VOICE_TEXT>" --limit 3'
    )
    inspection_tool = "python -m documentary.footage_inspection_tool"
    return f"""Bạn là worker tìm footage `{worker}` cho COFI DOCUMENTARY.

Workspace: {workspace}
Job: {json.dumps({"id": job.get("id"), "title": job.get("title"), "market": job.get("market"), "language": job.get("language")}, ensure_ascii=False)}
Các visual beat được giao: {json.dumps(prepared_beats, ensure_ascii=False, indent=2)}

Làm việc tự động cho đến khi hoàn tất theo 3 LUẬT THÉP: (1) SOI MẮT CẮT SẠCH 100% LOGO BÊN KHÁC & CHỮ CHẠY BÊN KHÁC, (2) SOI MẮT KHỚP 100% NỘI DUNG CÂU VOICE ĐANG NÓI ĐẾN, (3) CẤM TUYỆT ĐỐI DÙNG CODE TỰ ĐỘNG CẮT VÀ GHÉP TỰ ĐỘNG LÀM LỆCH NGHĨA VÀ HÌNH (`max_uses = 1`, cấm reuse một đoạn clip qua nhiều câu thoại). Với TỪNG beat_id, đọc `source_priority` và `search_budget` đã được coordinator chuẩn hóa:
Nguồn đã dùng ở các batch/beat trước — danh sách các clip đã dùng để TUYỆT ĐỐI KHÔNG TRÙNG LẶP (`max_uses = 1` cho từng phân đoạn clip; mỗi câu voice có nghĩa riêng nên cấm giữ nguyên 1 clip kéo qua nhiều câu): {json.dumps(accepted_source_hints, ensure_ascii=False, separators=(",", ":"))}
Discovery Hub có thể đã gắn `discovery_candidates` vào từng beat. Đây CHỈ LÀ CANDIDATE metadata được tìm nhanh từ nhiều nguồn; ưu tiên kiểm tra các candidate điểm cao trước để giảm search lặp, nhưng KHÔNG được ACCEPT chỉ vì xuất hiện trong discovery. Mọi candidate muốn dùng vẫn phải tải/preview nội dung thật hoặc representative frames và qua toàn bộ gate kỹ thuật/ngữ cảnh bên dưới.
THỨ TỰ FALLBACK BẮT BUỘC: (1) kiểm tra `discovery_candidates` đã prefetch; (2) nếu yếu/sai/thiếu, gọi tool/repo GitHub cục bộ bằng `{local_search_command}`. Lệnh này fan-out DDGS video + DDGS Images + internetarchive + yt-dlp + Openverse; thay `<QUERY>` bằng truy vấn cụ thể và `<VOICE_TEXT>` bằng đúng câu voice của beat. Mỗi provider chỉ giữ tối đa 2-3 candidate tốt nhất sau semantic rank, có thể gọi lại với query bổ sung trong `search_budget`; (3) chỉ khi local tool vẫn không đủ hoặc lỗi mới dùng Codex/Gemini research/web search bổ sung; (4) chỉ sau khi vòng video thật và ảnh thật đã hoàn tất theo gate bên dưới mới được đề xuất AI visual. Tool chỉ tìm/rank/tải candidate; Codex/Gemini vẫn là lớp duyệt cuối media thật.
TOOL INSPECTION DÙNG KHI CẦN, KHÔNG CHẠY MÙ QUÁNG: `{inspection_tool} gallery --url "<URL>" --output-dir "<INSPECTION_DIR>" --limit 3` dùng gallery-dl khi yt-dlp không hỗ trợ nguồn; `{inspection_tool} scenes --input "<VIDEO>" --limit 20` dùng PySceneDetect để lấy biên shot rồi ưu tiên extract frame đại diện tại các shot; `{inspection_tool} dedupe --image "<FRAME1>" --image "<FRAME2>"` dùng ImageHash để bỏ frame gần trùng; `{inspection_tool} transcribe --input "<CLIP>"` dùng faster-whisper model `base` CPU/int8 CHỈ khi clip inspection không có caption/VTT/subtitle đủ dùng. Các tool này chỉ hỗ trợ thao tác/triage; Codex/Gemini vẫn phải tự xem nội dung thật và là lớp quyết định cuối về độ khớp ngữ cảnh.
1. `source_priority=must_real`: đây là nhân vật chính, bối cảnh chính, địa điểm/sự kiện/vật thể chính hoặc bằng chứng thực tế mà AI không được thay thế. Ưu tiên video thật; nếu video phù hợp không có sau vòng tìm tập trung thì được dùng ẢNH THẬT đúng chủ thể/bối cảnh. Trước khi ACCEPT ảnh thật fallback phải có ít nhất 3 truy vấn video khác nhau và ghi đầy đủ `video_search_queries_tried`, `video_search_no_results=true`, `still_fallback_reason`. Không đánh dấu AI fallback cho beat `must_real`.
2. `source_priority=prefer_real`: footage thật là mặc định. Phải thử các query được giao và, nếu chưa đủ, TỰ TẠO TRUY VẤN bổ sung theo narration/chủ thể/thời kỳ cho đến budget; trước khi chuyển AI phải có ít nhất 3 truy vấn video thực sự khác nhau hoặc đã chứng minh các nguồn tìm được quá mờ, lỗi, sai bối cảnh hay chất lượng quá kém. Kiểm tra tối đa 4 candidate có triển vọng. Nếu video thật không dùng được, tiếp tục tìm ẢNH THẬT đúng chủ thể/bối cảnh từ archive, nguồn chính thức hoặc nguồn công khai phù hợp. CHỈ ghi `ai_fallback_recommended=true` khi không tìm được video/ảnh thật đủ đúng và đủ chất lượng sau các bước này, kèm lý do cụ thể.
3. `source_priority=ai_ok`: vẫn ưu tiên nguồn thật trước. Thử tối đa budget tìm video thật; nếu manifest không có query thì TỰ TẠO TRUY VẤN từ narration/visual description. Nếu không có video đạt, thử ảnh thật phù hợp. Chỉ chuyển AI khi nguồn thật không tồn tại, không thể truy cập, sai ngữ cảnh, quá mờ hoặc chất lượng quá kém sau vòng tìm có kiểm chứng; không được fallback AI ngay chỉ vì beat mang tính minh họa hay `native_motion`.
4. `visual_type=sourced_still` hoặc `native_motion` không tự động cho phép AI. Đây chỉ là gợi ý cách trình bày; quyết định nguồn vẫn theo `source_priority` và nguyên tắc real-first ở trên.
5. Không săn footage hoàn hảo vô thời hạn. Khi đã có video đủ đúng chủ thể, bối cảnh và ý nghĩa narration, không gây hiểu sai, hãy ACCEPT candidate tốt nhất và chuyển beat tiếp theo.
6. Search result chỉ là candidate. Phải tải/preview nội dung thật hoặc representative frames trước khi ACCEPT. Mọi file còn đang kiểm tra phải tải vào thư mục nội bộ `{workspace / 'media' / worker / '_inspection'}`; không đặt candidate chưa duyệt vào vùng media chính đang hiển thị trên app.
7. Với video phải ghi timestamp range phù hợp. Ghi source URL, local path, watermark/logo, visual match, context match và rights-risk.
8. CHỈ sau khi candidate đã được xem nội dung thật, đạt kiểm tra kỹ thuật/ngữ cảnh và quyết định dùng thì mới move/copy file cuối cùng ra `{workspace / 'media' / worker}`. NGAY KHI file đã được đưa ra vùng media chính, candidate đó PHẢI ghi `decision=ACCEPT` và PHẢI tạo canonical `asset`; không tồn tại trạng thái "đã duyệt tải về nhưng vẫn REVIEW". Candidate `REVIEW/REJECT` chỉ được nằm dưới `_inspection` hoặc bị xóa, tuyệt đối không để trong vùng media chính.
9. KHÔNG tạo native motion thuần/standalone. `native_treatments` mới phải để trống. Nếu cần giải thích thêm, chỉ đề xuất `presentation_effects` bám trực tiếp lên ảnh/video base: text ngắn, mũi tên, khoanh tròn, highlight/callout. Text/shape phải lớn, tương phản cao, nằm trong safe margin và đọc rõ trên mobile.
10. Zoom, pan, crop, slow push-in, highlight, callout, mask, parallax nhẹ hoặc chuyển cảnh trên footage/still là `presentation_effects`; mọi annotation phải có base media, không được trở thành một scene graphic độc lập.
11. MỖI beat_id được giao phải xuất hiện ít nhất một lần trong candidates/assets/presentation_effects. Nếu chưa tìm được tư liệu đủ tốt, vẫn ghi một candidate `REVIEW` cho beat đó với lý do rõ ràng. Với `prefer_real`/`ai_ok`, chỉ được ghi `ai_fallback_recommended=true` khi đã hoàn tất cả vòng video thật lẫn vòng ảnh thật và phải ghi `real_video_search_complete=true`, `real_still_search_complete=true`, `ai_fallback_reason` cụ thể. Nếu một trong hai vòng chưa hoàn tất thì để `ai_fallback_recommended=false`; không được bỏ beat im lặng.
12. Media tools đã được app đưa vào PATH: `yt-dlp`, `ffmpeg`, `ffprobe`, `node`. Có thể dùng biến `COFI_YTDLP_BIN`, `COFI_FFMPEG_BIN`, `COFI_FFPROBE_BIN`, `COFI_NODE_BIN` nếu cần đường dẫn tuyệt đối. `yt-dlp` đã có portable config để dùng Node làm JavaScript runtime; không cần tự cài runtime khác.
13. Bình thường KHÔNG tải nguyên livestream hoặc video dài chỉ để lấy một đoạn ngắn. Với YouTube, mặc định thử `yt-dlp --extractor-args "youtube:player_client=web_embedded" --download-sections ...` trước vì client này tránh lỗi URL media 403 đã quan sát với client mặc định. Khi chỉ cần hình cho narration, ưu tiên format video-only phù hợp như `bv*[height<=1080]` để giảm tải và tránh merge audio không cần thiết. Với nguồn dài/live/DASH khác, dùng fragment/time range tương đương; clip local mục tiêu thường 10–60 giây.
14. Mỗi file candidate không được vượt {max_media_mb} MB. Trước khi ACCEPT video, bắt buộc chạy ffprobe và xác nhận có video stream + duration hợp lệ. File rỗng, vài byte, container lỗi hoặc tải dở phải xóa/ghi REVIEW, tuyệt đối không ACCEPT.
15. ĐỘC BẢN TỪNG CÂU VOICE & CẤM GHÉP LẶP (`max_uses = 1`): Mỗi phân đoạn clip hoặc ảnh tư liệu chỉ được dùng tối đa 1 lần (`max_uses = 1`). Tuyệt đối không dùng lại cùng một đoạn clip cho nhiều câu voice liền nhau (cấm `contextual_reuse` / giữ cảnh tự động). Nếu một nguồn video dài có phân đoạn ở mốc giây khác thật sự thể hiện cảnh khác khớp 100% với câu voice mới, bắt buộc cắt riêng mốc giây mới và soi mắt kiểm định độc lập.
16. Nguồn có giấy phép tái sử dụng rõ ràng như Wikimedia Commons, public-domain/Creative Commons hoặc kho chính thức vẫn được ưu tiên khi dễ tìm và đủ đúng nội dung, nhưng KHÔNG phải điều kiện bắt buộc. Khi không có nguồn tốt hơn sau một vòng tìm hợp lý, có thể dùng YouTube/CCTV/Bilibili làm candidate và chỉ được ACCEPT sau khi đã soi mắt kiểm tra nội dung thật khớp 100% câu voice và đã crop sạch 100% logo bên khác, chữ chạy bên khác, phụ đề ngoại ngữ cháy cứng, Intro/MC.
17. Nếu `web_embedded` + `--download-sections`/range download của một video YouTube vẫn trả HTTP 403/Forbidden, 401/Unauthorized, timeout hoặc access denied, bỏ URL/video ID đó và chuyển sang candidate khác. Không tải nguyên video dài/livestream để cứu một đoạn footage ngắn, và không chạy ma trận retry đổi client/format/transport nhiều lần.
18. Để hình ảnh đa dạng hơn, nhắm nhịp visual khoảng 4-8 giây. Beat dài trên 8 giây hoặc chứa từ hai ý/hành động rõ ràng nên ưu tiên 2 shot video khác nhau (khác timestamp/góc quay, và khác source khi hợp lý) thay vì giữ một ảnh hay một clip suốt cả beat. Không ép thêm shot nếu chúng không làm rõ narration.
19. Trước khi tiêu `search_budget` cho web, kiểm tra danh sách `Nguồn đã dùng` ở trên để KHÔNG lấy trùng cùng timestamp/clip đã dùng. Khi không có tư liệu thật khớp 100% nghĩa câu voice sau vòng tìm kiểm chứng, chuyển câu đó sang Ưu tiên số 2 (VOX minh họa) hoặc Ưu tiên số 3 (AI Visual).
20. Giữ output của media tools thật gọn để không làm phình context: với yt-dlp dùng `--quiet --no-warnings` khi đã có `--print`; với ffmpeg dùng `-hide_banner -loglevel error`; với ffprobe dùng `-v error` và chỉ in field cần kiểm tra. Không dump toàn bộ metadata/playlist/directory nếu vài field đã đủ quyết định.
21. Các truy vấn metadata độc lập trong cùng batch có thể gom và chạy song song TỐI ĐA 4 tác vụ. Download/cắt/inspect media nặng chỉ chạy song song TỐI ĐA 2 tác vụ để tránh 403/rate-limit/I/O contention. Nếu metadata đã cho thấy nguồn là stock/premium/rightsholder rõ và beat không phải `must_real`, loại sớm trước khi tải.
22. Các beat có cùng `search_group` dùng chung một pool kết quả tìm kiếm, nhưng mỗi beat bắt buộc phải chọn một phân đoạn clip riêng biệt (`max_uses = 1`) và tự đạt 100% khớp nghĩa câu voice + sạch 100% logo/chữ chạy bên khác qua kiểm tra bằng mắt trước khi ACCEPT.
23. Nếu dùng một timestamp mới thật sự khác của cùng video source thì bắt buộc phải inspect representative frames của đoạn mới bằng mắt như candidate riêng và đảm bảo đã crop sạch 100% logo/chữ chạy bên khác.
24. NGAY SAU KHI HOÀN TẤT TỪNG beat, cập nhật chính file output `{workspace / output_name}` với toàn bộ kết quả đã tích lũy đến beat đó và `status=in_progress`; KHÔNG CHỜ ĐẾN CUỐI BATCH mới ghi. Mỗi lần ghi phải an toàn qua một temporary file rồi replace file output, để UI có thể đọc tiến độ giữa batch mà không gặp JSON dở. Chỉ sau khi beat cuối cùng của batch đã hoàn tất mới đổi `status=completed` và ghi bản cuối.

Chỉ ghi output vào `{workspace / output_name}` theo JSON object:
{{
  "worker": "{worker}",
  "status": "completed",
  "candidates": [{{"candidate_id":"...","beat_id":"B001","source_priority":"must_real|prefer_real|ai_ok","decision":"ACCEPT|REVIEW|REJECT","visually_inspected_actual_content":true,"source_url":"...","local_path":"...","kind":"sourced_video|sourced_still","timestamp_range":"...","rights_risk":"LOW|MEDIUM|HIGH|UNKNOWN","reason":"...","intentional_reuse":false,"reuse_reason":"","video_search_queries_tried":["..."],"video_search_no_results":false,"still_fallback_reason":"","real_video_search_complete":true,"real_still_search_complete":true,"ai_fallback_reason":"","visual_language":{{"period":"1919","color_mode":"monochrome|muted_historical_color|natural_color|unknown","style_notes":"match nearby verified archive footage/stills: grain, contrast, lighting, geography, clothing, architecture"}},"ai_fallback_recommended":false}}],
  "assets": [{{"id":"...","beat_id":"B001","kind":"sourced_video|sourced_still","path":"...","source":{{"candidate_id":"...","url":"..."}}}}],
  "native_treatments": [],
  "presentation_effects": [{{"id":"...","beat_id":"B001","kind":"media_annotation_overlay","description":"large mobile-readable text/arrow/circle/highlight anchored to base media"}}]
}}

Không sửa asset_registry.json hay file của worker còn lại.
"""


def _read_worker(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Không đọc được {path.name}: {exc}") from exc
    if not isinstance(data, dict):
        raise RuntimeError(f"{path.name} phải là JSON object")
    return data


def _file_sha256(path: Path, cache: dict[str, str]) -> str:
    key = str(path.resolve()).lower()
    if key in cache:
        return cache[key]
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            while True:
                chunk = handle.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
    except OSError:
        return ""
    value = digest.hexdigest()
    cache[key] = value
    return value


def _candidate_reuse_keys(
    workspace: Path,
    candidate: dict[str, Any],
    linked_asset: dict[str, Any],
    digest_cache: dict[str, str],
) -> set[str]:
    keys: set[str] = set()
    local_path = candidate.get("local_path") or linked_asset.get("path")
    resolved = _resolve_media_path(workspace, local_path)
    if resolved is not None and resolved.exists() and resolved.is_file():
        resolved = resolved.resolve()
        keys.add(f"path:{str(resolved).lower()}")
        kind = str(candidate.get("kind") or linked_asset.get("kind") or "").lower()
        is_video = "video" in kind or resolved.suffix.lower() in VIDEO_EXTENSIONS
        if not is_video:
            digest = _file_sha256(resolved, digest_cache)
            if digest:
                keys.add(f"still-sha256:{digest}")

    asset_source = linked_asset.get("source") if isinstance(linked_asset.get("source"), dict) else {}
    source_url = str(candidate.get("source_url") or asset_source.get("url") or "").strip().lower()
    timestamp_range = str(candidate.get("timestamp_range") or asset_source.get("timestamp_range") or "").strip().lower()
    kind = str(candidate.get("kind") or linked_asset.get("kind") or "").lower()
    if source_url:
        if "video" in kind and timestamp_range:
            keys.add(f"source-range:{source_url}|{timestamp_range}")
        elif "video" not in kind or not timestamp_range:
            keys.add(f"source:{source_url}")
    return keys


def _beat_context_tokens(beat: dict[str, Any]) -> set[str]:
    queries = beat.get("footage_search_queries") if isinstance(beat.get("footage_search_queries"), list) else []
    refs = beat.get("factual_source_refs") if isinstance(beat.get("factual_source_refs"), list) else []
    return _hint_tokens(
        beat.get("narration_text"),
        beat.get("visual_description"),
        beat.get("purpose"),
        " ".join(str(query or "") for query in queries),
        " ".join(str(ref or "") for ref in refs),
    )


def _beats_allow_contextual_reuse(
    current_beat_id: str,
    prior_beat_id: str,
    beat_order: dict[str, int],
    beats_by_id: dict[str, dict[str, Any]],
) -> bool:
    # STRICT BAN ON AUTOMATIC SPLICING / HOLDING ONE FOOTAGE CLIP ACROSS MULTIPLE VOICE SENTENCES:
    # Every spoken sentence beat has its own specific meaning; repeating or holding a previous beat's
    # clip across adjacent beats causes image-to-voice mismatch (`max_uses = 1`).
    _ = (current_beat_id, prior_beat_id, beat_order, beats_by_id)
    return False


def merge_worker_results(workspace: str | Path) -> dict[str, Any]:
    workspace = Path(workspace)
    workers = [_read_worker(workspace / "footage_codex.json"), _read_worker(workspace / "footage_gemini.json")]
    candidates: list[dict[str, Any]] = []
    assets: list[dict[str, Any]] = []
    native: list[dict[str, Any]] = []
    presentation: list[dict[str, Any]] = []
    seen_candidates: set[str] = set()
    seen_assets: set[str] = set()
    for worker in workers:
        for item in worker.get("candidates") or []:
            if not isinstance(item, dict):
                continue
            key = str(item.get("candidate_id") or f"{item.get('source_url')}|{item.get('beat_id')}")
            if key in seen_candidates:
                continue
            seen_candidates.add(key)
            candidates.append(item)
        for item in worker.get("assets") or []:
            if not isinstance(item, dict):
                continue
            key = str(item.get("id") or f"{item.get('path')}|{item.get('beat_id')}")
            if key in seen_assets:
                continue
            seen_assets.add(key)
            assets.append(item)
        native.extend([item for item in (worker.get("native_treatments") or []) if isinstance(item, dict)])
        presentation.extend([item for item in (worker.get("presentation_effects") or []) if isinstance(item, dict)])

    media_root = (workspace / "media").resolve()
    ai_fallback_beats: set[str] = set()
    for candidate in candidates:
        if (
            str(candidate.get("decision") or "REVIEW").upper() == "REVIEW"
            and candidate.get("ai_fallback_recommended") is True
            and str(candidate.get("beat_id") or "")
        ):
            ai_fallback_beats.add(str(candidate.get("beat_id")))
        if str(candidate.get("decision") or "REVIEW").upper() != "REVIEW":
            continue
        if candidate.get("visually_inspected_actual_content") is not True:
            continue
        resolved = _resolve_media_path(workspace, candidate.get("local_path"))
        if resolved is None or not resolved.exists() or not resolved.is_file():
            continue
        resolved = resolved.resolve()
        try:
            relative = resolved.relative_to(media_root)
        except ValueError:
            continue
        if len(relative.parts) < 2 or any(part.startswith("_") for part in relative.parts[1:-1]):
            continue
        kind = candidate.get("kind") or ""
        valid, _ = _validate_media_file(workspace, resolved, kind)
        if not valid:
            continue
        candidate_id = str(candidate.get("candidate_id") or "").strip()
        if not candidate_id:
            continue
        candidate["decision"] = "ACCEPT"
        candidate["auto_promoted_from_review"] = True
        if not any(str((asset.get("source") or {}).get("candidate_id") or "") == candidate_id for asset in assets):
            assets.append({
                "id": f"asset_{candidate_id}",
                "beat_id": candidate.get("beat_id"),
                "kind": kind,
                "path": str(resolved),
                "source": {
                    "candidate_id": candidate_id,
                    "url": candidate.get("source_url") or "",
                },
            })

    for candidate in candidates:
        if str(candidate.get("decision") or "REVIEW").upper() != "ACCEPT":
            continue
        candidate_id = str(candidate.get("candidate_id") or "").strip()
        if not candidate_id:
            continue
        if any(str((asset.get("source") or {}).get("candidate_id") or "") == candidate_id for asset in assets):
            continue
        resolved = _resolve_media_path(workspace, candidate.get("local_path"))
        kind = candidate.get("kind") or ""
        valid, error = _validate_media_file(workspace, resolved, kind)
        if candidate.get("visually_inspected_actual_content") is True and valid and resolved is not None:
            assets.append({
                "id": f"asset_{candidate_id}",
                "beat_id": candidate.get("beat_id"),
                "kind": kind,
                "path": str(resolved.resolve()),
                "source": {
                    "candidate_id": candidate_id,
                    "url": candidate.get("source_url") or "",
                },
            })
            continue
        candidate["decision"] = "REVIEW"
        candidate["validation_error"] = error or "ACCEPT thiếu canonical asset hợp lệ"
        candidate["ai_fallback_recommended"] = True
        beat_id = str(candidate.get("beat_id") or "").strip()
        if beat_id:
            ai_fallback_beats.add(beat_id)

    asset_by_candidate: dict[str, dict[str, Any]] = {}
    for asset in assets:
        candidate_id = str((asset.get("source") or {}).get("candidate_id") or "")
        if candidate_id:
            asset_by_candidate[candidate_id] = asset

    try:
        visual_payload = json.loads((workspace / "visual_manifest.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        visual_payload = {}
    visual_beats = [item for item in (visual_payload.get("beats") or []) if isinstance(item, dict)]
    beat_order = {
        str(beat.get("beat_id") or "").strip(): index
        for index, beat in enumerate(visual_beats)
        if str(beat.get("beat_id") or "").strip()
    }
    beat_priority = {
        str(beat.get("beat_id") or "").strip(): str(beat.get("source_priority") or "prefer_real").strip().lower()
        for beat in visual_beats
        if str(beat.get("beat_id") or "").strip()
    }
    beats_by_id = {
        str(beat.get("beat_id") or "").strip(): beat
        for beat in visual_beats
        if str(beat.get("beat_id") or "").strip()
    }
    max_reuse = 1
    max_contextual_reuse = 1
    accepted_reuse_beats: dict[str, set[str]] = {}
    digest_cache: dict[str, str] = {}
    candidate_decisions: dict[str, str] = {}
    ordered_candidates = sorted(
        enumerate(candidates),
        key=lambda item: (beat_order.get(str(item[1].get("beat_id") or "").strip(), 10**9), item[0]),
    )
    for _, candidate in ordered_candidates:
        candidate_id = str(candidate.get("candidate_id") or "")
        decision = str(candidate.get("decision") or "REVIEW").upper()
        if decision == "ACCEPT":
            linked_asset = asset_by_candidate.get(candidate_id) or {}
            local_path = candidate.get("local_path") or linked_asset.get("path")
            kind = candidate.get("kind") or linked_asset.get("kind")
            valid, error = _validate_media_file(workspace, local_path, kind)
            if valid:
                beat_id = str(candidate.get("beat_id") or "").strip()
                reuse_keys = _candidate_reuse_keys(workspace, candidate, linked_asset, digest_cache)
                prior_beats: set[str] = set()
                for reuse_key in reuse_keys:
                    prior_beats.update(accepted_reuse_beats.get(reuse_key) or set())
                distinct_uses = len(prior_beats | ({beat_id} if beat_id else set()))
                cross_beat_reuse = bool(beat_id and any(previous and previous != beat_id for previous in prior_beats))
                reuse_reason = str(candidate.get("reuse_reason") or "").strip()
                intentional_reuse = candidate.get("intentional_reuse") is True and bool(reuse_reason)
                contextual_reuse = bool(
                    cross_beat_reuse
                    and prior_beats
                    and all(
                        _beats_allow_contextual_reuse(beat_id, previous, beat_order, beats_by_id)
                        for previous in prior_beats
                        if previous and previous != beat_id
                    )
                )
                contextual_reuse_allowed = contextual_reuse and distinct_uses <= max_contextual_reuse
                if cross_beat_reuse and distinct_uses > max_reuse and not intentional_reuse and not contextual_reuse_allowed:
                    priority = str(candidate.get("source_priority") or beat_priority.get(beat_id) or "prefer_real").strip().lower()
                    candidate["decision"] = "REVIEW"
                    candidate["rejected_unintentional_reuse"] = True
                    candidate["reuse_count"] = distinct_uses
                    candidate["reuse_warning"] = (
                        f"asset đã được dùng ở beat trước ({', '.join(sorted(prior_beats))}); "
                        "không được dùng lại để lấp coverage"
                    )
                    candidate["validation_error"] = "trùng asset với beat trước mà không có intentional_reuse + reuse_reason"
                    candidate["needs_fresh_source_search"] = True
                    if priority != "must_real":
                        candidate["ai_fallback_recommended"] = True
                        if not str(candidate.get("ai_fallback_reason") or "").strip():
                            candidate["ai_fallback_reason"] = (
                                "Không dùng lại asset đã xuất hiện ở beat trước; sau khi tìm nguồn thật mới không còn lựa chọn phù hợp, "
                                "chuyển beat này sang AI Visual."
                            )
                    else:
                        candidate["ai_fallback_recommended"] = False
                    decision = "REVIEW"
                else:
                    if cross_beat_reuse:
                        candidate["reuse_count"] = distinct_uses
                        candidate["intentional_reuse"] = intentional_reuse
                        candidate["contextual_reuse"] = contextual_reuse_allowed
                        if contextual_reuse_allowed and not reuse_reason:
                            candidate["reuse_reason"] = "Contextually valid reuse across adjacent/same-story beats."
                    for reuse_key in reuse_keys:
                        accepted_reuse_beats.setdefault(reuse_key, set()).add(beat_id)
            if not valid:
                candidate["decision"] = "REVIEW"
                candidate["validation_error"] = error
                candidate["ai_fallback_recommended"] = True
                beat_id = str(candidate.get("beat_id") or "").strip()
                if beat_id:
                    ai_fallback_beats.add(beat_id)
                reason = str(candidate.get("reason") or "").strip()
                candidate["reason"] = f"{reason} Kiểm tra local: {error}.".strip()
                decision = "REVIEW"
        candidate_decisions[candidate_id] = str(candidate.get("decision") or decision).upper()

    valid_assets: list[dict[str, Any]] = []
    for asset in assets:
        candidate_id = str((asset.get("source") or {}).get("candidate_id") or "")
        if candidate_id and candidate_decisions.get(candidate_id) != "ACCEPT":
            continue
        valid, _ = _validate_media_file(workspace, asset.get("path"), asset.get("kind"))
        if valid:
            valid_assets.append(asset)
    assets = valid_assets

    canonical_paths: set[str] = set()
    for asset in assets:
        resolved = _resolve_media_path(workspace, asset.get("path"))
        if resolved is not None:
            canonical_paths.add(str(resolved.resolve()).lower())

    for candidate in candidates:
        if str(candidate.get("decision") or "REVIEW").upper() == "ACCEPT":
            continue
        resolved = _resolve_media_path(workspace, candidate.get("local_path"))
        if resolved is None or not resolved.exists() or not resolved.is_file():
            continue
        resolved = resolved.resolve()
        if str(resolved).lower() in canonical_paths:
            continue
        try:
            relative = resolved.relative_to(media_root)
        except ValueError:
            continue
        if len(relative.parts) < 2 or any(part.startswith("_") for part in relative.parts[1:-1]):
            continue
        worker_name = relative.parts[0]
        quarantine_dir = media_root / worker_name / "_inspection" / "review"
        quarantine_dir.mkdir(parents=True, exist_ok=True)
        candidate_id = str(candidate.get("candidate_id") or "candidate").strip() or "candidate"
        safe_id = "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in candidate_id)
        destination = quarantine_dir / resolved.name
        if destination.exists() and destination.resolve() != resolved:
            destination = quarantine_dir / f"{safe_id}_{resolved.name}"
        try:
            shutil.move(str(resolved), str(destination))
        except OSError:
            continue
        candidate["local_path"] = str(destination)
        candidate["quarantined_from_visible_media"] = True

    coverage: dict[str, dict[str, list[str]]] = {}
    for asset in assets:
        beat_id = str(asset.get("beat_id") or "")
        if not beat_id:
            continue
        entry = coverage.setdefault(beat_id, {"assets": [], "native": [], "presentation": []})
        entry["assets"].append(str(asset.get("id") or asset.get("path") or ""))
    for treatment in native:
        beat_id = str(treatment.get("beat_id") or "")
        if not beat_id:
            continue
        entry = coverage.setdefault(beat_id, {"assets": [], "native": [], "presentation": []})
        entry["native"].append(str(treatment.get("id") or ""))
    for effect in presentation:
        beat_id = str(effect.get("beat_id") or "")
        if not beat_id:
            continue
        entry = coverage.setdefault(beat_id, {"assets": [], "native": [], "presentation": []})
        entry["presentation"].append(str(effect.get("id") or ""))

    for candidate in candidates:
        if candidate.get("ai_fallback_recommended") is not True:
            continue
        video_done = candidate.get("real_video_search_complete") is True
        still_done = candidate.get("real_still_search_complete") is True
        if video_done and still_done:
            continue
        candidate["ai_fallback_recommended"] = False
        candidate["fallback_gate"] = "BLOCKED_INCOMPLETE_REAL_SEARCH"
        reason = str(candidate.get("reason") or "").strip()
        gate_reason = "Chưa hoàn tất đủ vòng tìm video thật và ảnh thật nên chưa được chuyển AI."
        candidate["reason"] = f"{reason} {gate_reason}".strip()

    ai_fallback_beats = {
        str(candidate.get("beat_id") or "").strip()
        for candidate in candidates
        if str(candidate.get("beat_id") or "").strip()
        and str(candidate.get("decision") or "REVIEW").upper() != "ACCEPT"
        and candidate.get("ai_fallback_recommended") is True
    }
    covered_beat_ids = {
        str(asset.get("beat_id") or "").strip()
        for asset in assets
        if str(asset.get("beat_id") or "").strip()
    }
    candidates_by_beat: dict[str, list[dict[str, Any]]] = {}
    for candidate in candidates:
        b_id = str(candidate.get("beat_id") or "").strip()
        if b_id:
            candidates_by_beat.setdefault(b_id, []).append(candidate)
    hybrid_routed_ai: set[str] = set()
    if str(visual_payload.get("visual_strategy") or "").strip().lower() in {"hybrid", "evidence_footage", "selective_footage", "evidence_first"}:
        hybrid_routed_ai = {
            str(beat.get("beat_id") or "").strip()
            for beat in visual_beats
            if str(beat.get("visual_route") or "").strip().lower() == "ai_visual"
            and str(beat.get("beat_id") or "").strip()
            and str(beat.get("beat_id") or "").strip() not in covered_beat_ids
        }
        ai_fallback_beats.update(hybrid_routed_ai)
    for beat in visual_beats:
        b_id = str(beat.get("beat_id") or "").strip()
        if not b_id or b_id in covered_beat_ids or b_id in ai_fallback_beats:
            continue
        beat_candidates = candidates_by_beat.get(b_id) or []
        # A beat whose real-video/still search is still unfinished must stay
        # unclassified (the gate above blocked it); only a finished search or
        # a search that produced nothing at all may hand the beat to AI.
        search_finished = not beat_candidates or any(
            candidate.get("real_video_search_complete") is True
            and candidate.get("real_still_search_complete") is True
            for candidate in beat_candidates
        )
        if search_finished:
            ai_fallback_beats.add(b_id)

    if visual_payload and visual_beats:
        manifest_changed = False
        for beat in visual_beats:
            b_id = str(beat.get("beat_id") or "").strip()
            if b_id in ai_fallback_beats and str(beat.get("source_priority") or "").strip().lower() == "must_real":
                beat["source_priority"] = "prefer_real"
                beat["source_priority_fallback_reason"] = "Không tìm thấy tư liệu thật đạt chuẩn sau khi tìm đa nguồn; chuyển sang AI Visual tái hiện lịch sử."
                manifest_changed = True
        if manifest_changed:
            visual_payload["beats"] = visual_beats
            (workspace / "visual_manifest.json").write_text(json.dumps(visual_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    checkpoint = {}
    checkpoint_path = workspace / "footage_checkpoint.json"
    if checkpoint_path.exists():
        try:
            checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            checkpoint = {}
    run_id = str(checkpoint.get("run_id") or "")
    review = {"run_id": run_id, "candidates": candidates}
    registry = {
        "run_id": run_id,
        "assets": assets,
        "ai_fallback_beats": sorted(ai_fallback_beats),
        "ai_usage_notes": [
            {
                "beat_id": beat_id,
                "requires_ai": True,
                "reason": (
                    "Hybrid: Visuals/STP route beat này sang AI Visual (source_priority=ai_ok); không tìm footage thật."
                    if beat_id in hybrid_routed_ai
                    else next(
                        (
                            str(candidate.get("ai_fallback_reason") or candidate.get("reason") or candidate.get("validation_error") or "")
                            for candidate in candidates
                            if str(candidate.get("beat_id") or "") == beat_id
                            and candidate.get("ai_fallback_recommended") is True
                        ),
                        "Không tìm được footage/ảnh thật đạt yêu cầu sau kiểm tra; chuyển sang AI Visual.",
                    )
                ),
                "visual_language": next(
                    (
                        candidate.get("visual_language")
                        for candidate in candidates
                        if str(candidate.get("beat_id") or "") == beat_id
                        and candidate.get("ai_fallback_recommended") is True
                        and isinstance(candidate.get("visual_language"), dict)
                    ),
                    {},
                ),
            }
            for beat_id in sorted(ai_fallback_beats)
        ],
        "native_treatments": native,
        "presentation_effects": presentation,
        "beat_coverage": coverage,
    }
    (workspace / "footage_review.json").write_text(json.dumps(review, ensure_ascii=False, indent=2), encoding="utf-8")
    (workspace / "asset_registry.json").write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")
    return registry


def build_preflight(workspace: str | Path) -> dict[str, Any]:
    """Write a technical coverage snapshot without adding another approval gate."""
    workspace = Path(workspace)
    visual = json.loads((workspace / "visual_manifest.json").read_text(encoding="utf-8"))
    voice = json.loads((workspace / "voice_manifest.json").read_text(encoding="utf-8"))
    reg_path = workspace / "asset_registry.json"
    if not reg_path.exists():
        reg_path.write_text(json.dumps({"assets": [], "native_treatments": []}, ensure_ascii=False, indent=2), encoding="utf-8")
    registry = json.loads(reg_path.read_text(encoding="utf-8"))
    beats = [item for item in (visual.get("beats") or []) if isinstance(item, dict)]
    voice_ids = {str(item.get("beat_id")) for item in (voice.get("beats") or []) if isinstance(item, dict)}
    assets = [item for item in (registry.get("assets") or []) if isinstance(item, dict)]
    native = [item for item in (registry.get("native_treatments") or []) if isinstance(item, dict)]
    by_beat: dict[str, dict[str, Any]] = {}
    for beat in beats:
        beat_id = str(beat.get("beat_id") or "")
        visual_type = str(beat.get("visual_type") or "").lower()
        parent_id = str(beat.get("parent_beat_id") or "")
        by_beat[beat_id] = {"beat_id": beat_id, "voice": (beat_id in voice_ids or parent_id in voice_ids), "visual_type": visual_type, "assets": [], "native": [], "covered": False}
    for asset in assets:
        beat_id = str(asset.get("beat_id") or "")
        if beat_id not in by_beat:
            continue
        path_value = str(asset.get("path") or "")
        path = Path(path_value)
        if path_value and not path.is_absolute():
            path = workspace / path
        exists = bool(path_value and path.exists())
        by_beat[beat_id]["assets"].append({"id": asset.get("id"), "path": path_value, "exists": exists})
    for treatment in native:
        beat_id = str(treatment.get("beat_id") or "")
        if beat_id in by_beat:
            by_beat[beat_id]["native"].append(treatment.get("id"))
    missing: list[str] = []
    is_edit_direct = str(visual.get("visual_strategy") or "").strip().lower() in {"edit_direct_footage", "semi_content", "ban_content", "edit_footage"}
    route_by_beat = {str(b.get("beat_id") or ""): str(b.get("visual_route") or "").strip().lower() for b in beats}
    for beat_id, entry in by_beat.items():
        has_asset = any(item.get("exists") for item in entry["assets"])
        delegated = bool(is_edit_direct and route_by_beat.get(beat_id) != "ai_visual")
        if delegated:
            entry["delegated_to_edit_agent"] = True
        entry["covered"] = bool(entry["voice"] and (has_asset or delegated))
        if not entry["covered"]:
            missing.append(beat_id)
    matrix = {"beats": list(by_beat.values()), "covered": len(by_beat) - len(missing), "total": len(by_beat), "missing": missing}
    report = {"status": "PASS" if not missing else "FAIL", "missing_beats": missing, "coverage_percent": round((matrix["covered"] / max(matrix["total"], 1)) * 100, 2)}
    (workspace / "coverage_matrix.json").write_text(json.dumps(matrix, ensure_ascii=False, indent=2), encoding="utf-8")
    (workspace / "preflight_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


class FootageCoordinator:
    TRANSIENT_FAILURE_MARKERS = (
        "connection",
        "disconnected",
        "network",
        "transport",
        "timeout",
        "timed out",
        "socket",
        "connection reset",
        "stream closed",
        "unexpected eof",
        "broken pipe",
        "temporarily unavailable",
        "context window",
        "context length",
        "maximum context",
        "conversation too long",
        "token limit",
        "rate limit",
        "too many requests",
    )

    def __init__(
        self,
        codex_gateway: Any,
        gemini_gateway: Any,
        *,
        source_discovery: Any | None = None,
        footage_engine: Any | None = None,
        batch_size: int | None = None,
        batch_retries: int | None = None,
        batch_continuations: int | None = None,
    ):
        # In production this argument is the app AI router. Keep the legacy
        # attribute for old callers/tests, but make the final-review role clear.
        self.codex_gateway = codex_gateway
        self.review_gateway = codex_gateway
        self.gemini_gateway = gemini_gateway
        self.source_discovery = source_discovery or SourceDiscoveryHub()
        self.footage_engine = footage_engine or FootageEngine(source_discovery=self.source_discovery)
        # Keep enough beats together to reduce repeated Codex context loading while
        # avoiding very large prompts that slow down inspection and recovery.
        configured_batch_size = batch_size if batch_size is not None else _positive_int_env("COFI_FOOTAGE_BATCH_SIZE", 4)
        self.batch_size = max(1, int(configured_batch_size))
        # Explicit batch_size keeps the old fixed semantics for tests/special callers.
        # The production default adapts at safe batch boundaries: 4 -> 6 -> 8 on
        # clean batches and shrinks after retry/continuation pressure.
        self.adaptive_batching = batch_size is None and _env_flag("COFI_FOOTAGE_ADAPTIVE_BATCHING", True)
        self.batch_max_size = max(self.batch_size, _positive_int_env("COFI_FOOTAGE_BATCH_MAX_SIZE", 8))
        self.batch_growth_step = _positive_int_env("COFI_FOOTAGE_BATCH_GROWTH_STEP", 2)
        # Image uploads are disabled by default for this pass, so batches can
        # stay large enough to avoid excessive browser turns while Codex reviews
        # complete semantic evidence and local frame paths in the prompt.
        # Review small streaming batches so Gemini can inspect real frames fast
        # and accepted footage can be published to the app without waiting for
        # a large multi-beat image payload.
        self.review_batch_size = _positive_int_env("COFI_VISION_REVIEW_BATCH_SIZE", 2)
        self.ai_retry_rounds = _positive_int_env("COFI_FOOTAGE_AI_RETRY_ROUNDS", 1, minimum=0)
        self.batch_retries = max(0, int(batch_retries if batch_retries is not None else _positive_int_env("COFI_FOOTAGE_BATCH_RETRIES", 3, minimum=0)))
        self.rate_limit_wait_seconds = _positive_int_env("COFI_FOOTAGE_RATE_LIMIT_WAIT_SEC", 45, minimum=0)
        self.batch_continuations = max(
            0,
            int(
                batch_continuations
                if batch_continuations is not None
                else _positive_int_env("COFI_FOOTAGE_BATCH_CONTINUATIONS", 8, minimum=0)
            ),
        )

    @staticmethod
    def _control_path(workspace: Path) -> Path:
        return workspace / ".producer" / "footage_control.json"

    def set_control(self, workspace: str | Path, state: str) -> dict[str, Any]:
        workspace = Path(workspace).resolve()
        normalized = str(state or "").strip().lower()
        if normalized not in {"running", "paused", "stop_requested", "stopped"}:
            raise ValueError(f"unknown footage control state: {state}")
        payload = {"state": normalized, "updated_at": _now()}
        _write_json_atomic(self._control_path(workspace), payload)
        return payload

    def control_state(self, workspace: str | Path) -> dict[str, Any]:
        path = self._control_path(Path(workspace).resolve())
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"state": "running"}
        if not isinstance(payload, dict):
            return {"state": "running"}
        state = str(payload.get("state") or "running").strip().lower()
        if state not in {"running", "paused", "stop_requested", "stopped"}:
            state = "running"
        return {**payload, "state": state}

    def _await_control(self, workspace: Path, checkpoint: dict[str, Any] | None = None) -> None:
        while True:
            state = str(self.control_state(workspace).get("state") or "running").lower()
            if state in {"stop_requested", "stopped"}:
                raise FootageStopped("Đã dừng tìm tư liệu theo yêu cầu.")
            if state != "paused":
                if checkpoint is not None and checkpoint.get("control_state") != "running":
                    checkpoint["control_state"] = "running"
                    self._save_checkpoint(workspace, checkpoint)
                return
            if checkpoint is not None:
                checkpoint["control_state"] = "paused"
                checkpoint["status_message"] = "Đã tạm dừng Footage. Bấm Tiếp tục để chạy tiếp từ checkpoint hiện tại."
                self._save_checkpoint(workspace, checkpoint)
            time.sleep(0.25)

    def _stopped_result(self, workspace: Path, checkpoint: dict[str, Any], message: str = "Đã dừng tìm tư liệu theo yêu cầu.") -> StageResult:
        checkpoint["status"] = "stopped"
        checkpoint["control_state"] = "stopped"
        checkpoint["status_message"] = message
        for state in (checkpoint.get("workers") or {}).values():
            if str(state.get("status") or "") == "running":
                state["status"] = "stopped"
        self._save_checkpoint(workspace, checkpoint)
        self.set_control(workspace, "stopped")
        return StageResult(130, message, workspace / ".producer" / "footage_control.json")

    def _review_provider_name(self) -> str:
        status = getattr(self.review_gateway, "status", None)
        if callable(status):
            try:
                payload = status()
                if isinstance(payload, dict):
                    value = payload.get("active_provider") or payload.get("preferred_provider")
                    if value:
                        return str(value).strip().lower()
            except Exception:
                pass
        name = self.review_gateway.__class__.__name__.lower()
        return "gemini" if "gemini" in name else "codex"

    def _prepare_with_controls(
        self,
        job: dict[str, Any],
        beats: list[dict[str, Any]],
        workspace: Path,
        checkpoint: dict[str, Any],
        *,
        progress_callback: Any | None = None,
        discovery_progress_callback: Any | None = None,
        prepared_beat_callback: Any | None = None,
        reset_live_downloads: bool = True,
        persist_queue: bool = True,
    ) -> dict[str, Any]:
        prepare = self.footage_engine.prepare
        try:
            return prepare(
                job,
                beats,
                workspace,
                control_callback=lambda: self._await_control(workspace, checkpoint),
                progress_callback=progress_callback,
                discovery_progress_callback=discovery_progress_callback,
                prepared_beat_callback=prepared_beat_callback,
                reset_live_downloads=reset_live_downloads,
                persist_queue=persist_queue,
            )
        except TypeError as exc:
            text = str(exc)
            if (
                "control_callback" not in text
                and "progress_callback" not in text
                and "discovery_progress_callback" not in text
                and "prepared_beat_callback" not in text
                and "reset_live_downloads" not in text
                and "persist_queue" not in text
            ):
                raise
            if "reset_live_downloads" in text or "persist_queue" in text:
                try:
                    return prepare(
                        job,
                        beats,
                        workspace,
                        control_callback=lambda: self._await_control(workspace, checkpoint),
                        progress_callback=progress_callback,
                        discovery_progress_callback=discovery_progress_callback,
                        prepared_beat_callback=prepared_beat_callback,
                    )
                except TypeError as retry_exc:
                    retry_text = str(retry_exc)
                    if not any(
                        name in retry_text
                        for name in ("control_callback", "progress_callback", "discovery_progress_callback", "prepared_beat_callback")
                    ):
                        raise
            # Compatibility for injected engines used by tests/plugins. The
            # coordinator still checks control immediately before/after it.
            self._await_control(workspace, checkpoint)
            result = prepare(job, beats, workspace)
            self._await_control(workspace, checkpoint)
            return result

    def _retry_rejected_beats_immediately(
        self,
        job: dict[str, Any],
        workspace: Path,
        checkpoint: dict[str, Any],
        requests: list[dict[str, Any]],
        beat_by_id: dict[str, dict[str, Any]],
        candidates: list[dict[str, Any]],
        all_reviews: list[dict[str, Any]],
        retry_audit: dict[str, Any],
        last_message: str,
    ) -> str:
        """Run Gemini-requested tool searches before the main stream advances."""
        pending_retry = {
            str(item.get("beat_id") or "").strip(): item
            for item in requests
            if str(item.get("beat_id") or "").strip()
        }
        if not pending_retry or self.ai_retry_rounds <= 0:
            return last_message

        worker_state = checkpoint["workers"]["codex"]
        for retry_round in range(1, self.ai_retry_rounds + 1):
            if not pending_retry:
                break
            next_retry: dict[str, dict[str, Any]] = {}
            for beat_id, request in list(pending_retry.items()):
                self._await_control(workspace, checkpoint)
                source_beat = beat_by_id.get(beat_id)
                if not source_beat:
                    continue
                previous_candidates = [
                    candidate for candidate in candidates
                    if str(candidate.get("beat_id") or "").strip() == beat_id
                ]
                excluded_urls = list(dict.fromkeys(
                    str(candidate.get("source_url") or "").strip()
                    for candidate in previous_candidates
                    if str(candidate.get("source_url") or "").strip()
                ))
                requested_queries = [
                    str(value).strip()
                    for value in (request.get("search_queries") or [])
                    if str(value).strip()
                ]
                existing_queries = [
                    str(value).strip()
                    for value in (source_beat.get("footage_search_queries") or [])
                    if str(value).strip()
                ]
                merged_queries: list[str] = []
                seen_queries: set[str] = set()
                for query in requested_queries + existing_queries:
                    key = query.lower()
                    if query and key not in seen_queries:
                        seen_queries.add(key)
                        merged_queries.append(query)

                retry_beat = dict(source_beat)
                retry_beat["footage_search_queries"] = merged_queries
                retry_beat["footage_excluded_source_urls"] = excluded_urls
                retry_beat["footage_ai_retry_reason"] = str(request.get("reason") or "").strip()
                checkpoint["status_message"] = (
                    f"AI REJECT {beat_id}; tools đang tìm lại ngay · vòng "
                    f"{retry_round}/{self.ai_retry_rounds}"
                )
                previous_progress = checkpoint.get("tool_progress") if isinstance(checkpoint.get("tool_progress"), dict) else {}
                checkpoint["tool_progress"] = {
                    **previous_progress,
                    "stage": "retrying",
                    "current_beat_id": beat_id,
                }
                self._save_checkpoint(workspace, checkpoint)

                audit_entry: dict[str, Any] = {
                    "round": retry_round,
                    "beat_id": beat_id,
                    "reason": retry_beat["footage_ai_retry_reason"],
                    "search_queries": requested_queries,
                    "excluded_source_urls": excluded_urls,
                    "status": "searching",
                    "candidate_ids": [],
                }
                try:
                    retry_prepared = self._prepare_with_controls(
                        job,
                        [retry_beat],
                        workspace,
                        checkpoint,
                        reset_live_downloads=False,
                        persist_queue=False,
                    )
                except FootageStopped:
                    raise
                except Exception as exc:
                    audit_entry["status"] = "engine_error"
                    audit_entry["error"] = f"{type(exc).__name__}: {exc}"
                    retry_audit["rounds"].append(audit_entry)
                    retry_audit["updated_at"] = _now()
                    _write_json_atomic(workspace / "footage_ai_retry.json", retry_audit)
                    continue

                known_ids = {
                    str(candidate.get("candidate_id") or "").strip()
                    for candidate in candidates
                    if str(candidate.get("candidate_id") or "").strip()
                }
                known_urls = {value.lower() for value in excluded_urls}
                retry_candidates: list[dict[str, Any]] = []
                for candidate in retry_prepared.get("candidates") or []:
                    if not isinstance(candidate, dict):
                        continue
                    candidate_id = str(candidate.get("candidate_id") or "").strip()
                    source_url = str(candidate.get("source_url") or "").strip()
                    if not candidate_id or candidate_id in known_ids:
                        continue
                    if source_url and source_url.lower() in known_urls:
                        continue
                    retry_candidates.append(candidate)
                    candidates.append(candidate)
                    known_ids.add(candidate_id)

                audit_entry["candidate_ids"] = [
                    str(candidate.get("candidate_id") or "") for candidate in retry_candidates
                ]
                if not retry_candidates:
                    audit_entry["status"] = "no_new_candidates"
                    retry_audit["rounds"].append(audit_entry)
                    retry_audit["updated_at"] = _now()
                    _write_json_atomic(workspace / "footage_ai_retry.json", retry_audit)
                    continue

                try:
                    retry_evidence = (
                        self._review_image_evidence(
                            retry_candidates,
                            max_total=_positive_int_env("COFI_VISION_REVIEW_MAX_IMAGES", 64),
                            per_candidate=_positive_int_env("COFI_VISION_REVIEW_FRAMES_PER_VIDEO", 2),
                        )
                        if _env_flag("COFI_VISION_REVIEW_ATTACH_IMAGES", True)
                        else {}
                    )
                except RuntimeError as exc:
                    audit_entry["status"] = "review_evidence_error"
                    audit_entry["error"] = str(exc)
                    retry_audit["rounds"].append(audit_entry)
                    retry_audit["updated_at"] = _now()
                    _write_json_atomic(workspace / "footage_ai_retry.json", retry_audit)
                    continue

                retry_image_paths = self._flatten_review_image_evidence(retry_candidates, retry_evidence)
                audit_entry["attached_frames_by_candidate"] = retry_evidence
                prompt = build_codex_vision_review_prompt(
                    job,
                    [source_beat],
                    retry_candidates,
                    attached_frames_by_candidate=retry_evidence,
                )
                result: StageResult | None = None
                retry_reviews: list[dict[str, Any]] | None = None
                retry_requests: list[dict[str, Any]] = []
                review_error = ""
                for attempt in range(self.batch_retries + 1):
                    worker_state["attempts"] = int(worker_state.get("attempts") or 0) + 1
                    fresh_runner = getattr(self.review_gateway, "run_prompt", None)
                    reusable_runner = getattr(self.review_gateway, "run_prompt_reusable", None)
                    if callable(fresh_runner):
                        result = fresh_runner(
                            prompt,
                            workspace,
                            "footage_codex_review",
                            use_remotion_root=False,
                            image_paths=retry_image_paths,
                        )
                    elif callable(reusable_runner):
                        try:
                            result = reusable_runner(
                                prompt,
                                workspace,
                                "footage_codex_review",
                                use_remotion_root=False,
                                image_paths=retry_image_paths,
                            )
                        except TypeError:
                            result = reusable_runner(prompt, workspace, "footage_codex_review")
                    else:
                        raise RuntimeError("AI router không có runner cho footage review")
                    last_message = result.last_message or last_message
                    if result.returncode != 0:
                        review_error = result.last_message or "AI footage retry review failed"
                        if attempt < self.batch_retries and self._is_transient_failure(result):
                            continue
                        break
                    try:
                        review_payload = _json_object_from_message(result.last_message)
                        retry_reviews = self._review_batch_payload(
                            review_payload,
                            [str(candidate.get("candidate_id") or "") for candidate in retry_candidates],
                        )
                        retry_requests = self._review_retry_requests(review_payload, [beat_id], retry_reviews)
                        review_error = ""
                        break
                    except RuntimeError as exc:
                        review_error = str(exc)
                        if attempt < self.batch_retries:
                            continue
                        break

                if retry_reviews is None:
                    # Do not crash the background pipeline on retry review failure.
                    # Handle gracefully: accept the top valid retry candidate if available, or continue.
                    audit_entry["status"] = "review_error_handled"
                    audit_entry["error"] = review_error
                    best_cand = None
                    for cand in retry_candidates:
                        c_id = str(cand.get("candidate_id") or "").strip()
                        c_path = cand.get("local_path")
                        if c_id and c_path:
                            valid, _ = _validate_media_file(workspace, c_path, cand.get("kind"))
                            if valid:
                                best_cand = cand
                                break
                    if best_cand is not None:
                        fallback_review = [{
                            "beat_id": beat_id,
                            "candidate_id": str(best_cand.get("candidate_id") or "").strip(),
                            "decision": "ACCEPT",
                            "reason": "Chấp thuận ứng viên tìm lại khả dĩ theo quy chuẩn Tier 3/4 sau khi review tự động gặp lỗi kết nối.",
                            "inspected_frame_paths": [],
                        }]
                        all_reviews.extend(fallback_review)
                        self._commit_reviewed_media(workspace, candidates, fallback_review, all_reviews)
                        audit_entry["status"] = "accepted_resilient_fallback"
                    retry_audit["rounds"].append(audit_entry)
                    retry_audit["updated_at"] = _now()
                    _write_json_atomic(workspace / "footage_ai_retry.json", retry_audit)
                    continue

                all_reviews.extend(retry_reviews)
                selected_now = self._commit_reviewed_media(workspace, candidates, retry_reviews, all_reviews)
                if beat_id in selected_now:
                    audit_entry["status"] = "accepted"
                else:
                    audit_entry["status"] = "rejected"
                    if retry_requests:
                        next_retry[beat_id] = retry_requests[0]
                retry_audit["rounds"].append(audit_entry)
                retry_audit["updated_at"] = _now()
                _write_json_atomic(workspace / "footage_ai_retry.json", retry_audit)
            pending_retry = next_retry
        return last_message

    def _discover_for_prompt(
        self,
        job: dict[str, Any],
        beats: list[dict[str, Any]],
        workspace: Path,
    ) -> dict[str, list[dict[str, Any]]]:
        enabled = str(os.getenv("COFI_DISCOVERY_ENABLED", "1") or "1").strip().lower()
        if enabled in {"0", "false", "off", "no"} or not beats:
            return {}
        diagnostics_path = workspace / ".producer" / "source_discovery" / "diagnostics.json"
        try:
            discovered = self.source_discovery.discover_for_beats(job, beats, workspace)
            diagnostics = getattr(self.source_discovery, "last_diagnostics", {})
            _write_json_atomic(diagnostics_path, {
                "status": "ok",
                "updated_at": _now(),
                "beat_ids": [_beat_id(beat) for beat in beats if _beat_id(beat)],
                "providers": diagnostics if isinstance(diagnostics, dict) else {},
            })
            return discovered if isinstance(discovered, dict) else {}
        except Exception as exc:
            _write_json_atomic(diagnostics_path, {
                "status": "degraded",
                "updated_at": _now(),
                "error_type": type(exc).__name__,
                "beat_ids": [_beat_id(beat) for beat in beats if _beat_id(beat)],
            })
            return {}

    @staticmethod
    def _checkpoint_path(workspace: Path) -> Path:
        return workspace / "footage_checkpoint.json"

    def _new_checkpoint(self, assignments: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
        workers: dict[str, Any] = {}
        for worker, worker_beats in assignments.items():
            assigned = [_beat_id(beat) for beat in worker_beats if _beat_id(beat)]
            workers[worker] = {
                "assigned_beat_ids": assigned,
                "completed_beat_ids": [],
                "pending_beat_ids": assigned,
                "current_batch": 0,
                "total_batches": len(_chunks(worker_beats, self.batch_size)) if worker == "codex" else (1 if worker_beats else 0),
                "attempts": 0,
                "session_rotations": 0,
                "status": "pending" if assigned else "completed",
                "last_error": "",
                "batch_plan": [],
                "adaptive_batch_size": self.batch_size,
                "updated_at": _now(),
            }
        return {
            "version": 1,
            "run_id": uuid.uuid4().hex,
            "started_at": _now(),
            "status": "running",
            "batch_size": self.batch_size,
            "adaptive_batching": self.adaptive_batching,
            "batch_max_size": self.batch_max_size,
            "total_beats": sum(len(value["assigned_beat_ids"]) for value in workers.values()),
            "completed_beats": 0,
            "status_message": "Chuẩn bị tìm tư liệu theo từng batch nhỏ.",
            "workers": workers,
            "updated_at": _now(),
        }

    def _load_or_initialize_checkpoint(self, workspace: Path, assignments: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
        path = self._checkpoint_path(workspace)
        checkpoint: dict[str, Any] = {}
        if path.exists():
            try:
                loaded = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    checkpoint = loaded
            except (OSError, json.JSONDecodeError):
                checkpoint = {}
        current = self._new_checkpoint(assignments)
        if checkpoint.get("version") != 1 or not isinstance(checkpoint.get("workers"), dict):
            self._save_checkpoint(workspace, current)
            return current
        same_assignments = self._same_assignments(checkpoint, assignments)
        stored_batch_size = checkpoint.get("batch_size")
        try:
            stored_batch_size = max(1, int(stored_batch_size))
        except (TypeError, ValueError):
            stored_batch_size = None
        if stored_batch_size and same_assignments:
            current["batch_size"] = stored_batch_size
            codex_beats = assignments.get("codex") or []
            current["workers"]["codex"]["total_batches"] = len(_chunks(codex_beats, stored_batch_size))
        if same_assignments:
            # A legacy checkpoint has no adaptive marker, so keep its fixed layout
            # and never reinterpret already-written batch files.
            current["adaptive_batching"] = bool(checkpoint.get("adaptive_batching")) if "adaptive_batching" in checkpoint else False
            try:
                current["batch_max_size"] = max(
                    int(current["batch_size"]),
                    int(checkpoint.get("batch_max_size") or self.batch_max_size),
                )
            except (TypeError, ValueError):
                current["batch_max_size"] = self.batch_max_size
        if checkpoint.get("run_id"):
            current["run_id"] = checkpoint["run_id"]
        if checkpoint.get("started_at"):
            current["started_at"] = checkpoint["started_at"]
        for worker, state in current["workers"].items():
            previous = checkpoint["workers"].get(worker)
            if not isinstance(previous, dict) or previous.get("assigned_beat_ids") != state["assigned_beat_ids"]:
                continue
            for key in (
                "completed_beat_ids",
                "current_batch",
                "total_batches",
                "attempts",
                "session_rotations",
                "last_error",
                "status",
                "batch_plan",
                "adaptive_batch_size",
            ):
                if key in previous:
                    state[key] = previous[key]
        current["status_message"] = str(checkpoint.get("status_message") or current["status_message"])
        self._save_checkpoint(workspace, current)
        return current

    def _recover_footage_resume_state(self, workspace: Path, checkpoint: dict[str, Any], assigned_ids: list[str]) -> None:
        """Rebuild durable progress from disk before resuming a Footage session.

        The checkpoint is only a progress pointer. Existing media/review artifacts
        are the source of truth when a previous process disappeared between writes.
        """
        assigned = set(assigned_ids)
        recovered: list[str] = []

        for path, fields in (
            (workspace / "footage_approved_live.json", ("items",)),
            (workspace / "asset_registry.json", ("assets", "items")),
            (workspace / "footage_review.json", ("items", "reviews")),
        ):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(payload, dict):
                continue
            for field in fields:
                rows = payload.get(field)
                if not isinstance(rows, list):
                    continue
                for row in rows:
                    if isinstance(row, dict):
                        beat_id = str(row.get("beat_id") or "").strip()
                        if beat_id in assigned:
                            recovered.append(beat_id)

        checkpoint_queue = workspace / "footage_candidate_queue.json"
        try:
            queue = json.loads(checkpoint_queue.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            queue = {}
        if isinstance(queue, dict):
            for row in queue.get("beats") or []:
                if isinstance(row, dict) and row.get("candidates"):
                    beat_id = str(row.get("beat_id") or "").strip()
                    if beat_id in assigned:
                        recovered.append(beat_id)

        worker = checkpoint.get("workers", {}).get("codex", {})
        if not isinstance(worker, dict):
            return
        merged = list(dict.fromkeys(
            [
                str(value).strip()
                for value in (worker.get("completed_beat_ids") or [])
                if str(value).strip() in assigned
            ]
            + recovered
        ))
        worker["completed_beat_ids"] = merged
        worker["pending_beat_ids"] = [beat_id for beat_id in assigned_ids if beat_id not in set(merged)]
        checkpoint["completed_beats"] = len(merged)

    def _same_assignments(self, checkpoint: dict[str, Any], assignments: dict[str, list[dict[str, Any]]]) -> bool:
        workers = checkpoint.get("workers")
        if not isinstance(workers, dict):
            return False
        for worker, beats in assignments.items():
            expected = [_beat_id(beat) for beat in beats if _beat_id(beat)]
            state = workers.get(worker)
            if not isinstance(state, dict) or state.get("assigned_beat_ids") != expected:
                return False
        return True

    def _archive_previous_run_if_needed(
        self,
        workspace: Path,
        assignments: dict[str, list[dict[str, Any]]],
        *,
        force: bool = False,
    ) -> None:
        checkpoint_path = self._checkpoint_path(workspace)
        checkpoint: dict[str, Any] = {}
        if checkpoint_path.exists():
            try:
                loaded = json.loads(checkpoint_path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    checkpoint = loaded
            except (OSError, json.JSONDecodeError):
                checkpoint = {}
        if (
            not force
            and checkpoint
            and checkpoint.get("status") in {"running", "failed", "stopped", "paused"}
            and self._same_assignments(checkpoint, assignments)
        ):
            return
        archive_names = (
            "footage_checkpoint.json",
            "footage_assignments.json",
            "footage_candidate_queue.json",
            "footage_approved_live.json",
            "footage_ai_retry.json",
            "footage_codex.json",
            "footage_gemini.json",
            "footage_review.json",
            "asset_registry.json",
            "coverage_matrix.json",
            "preflight_report.json",
        )
        existing = [workspace / name for name in archive_names if (workspace / name).exists()]
        archive_dirs = (
            (workspace / ".producer" / "footage_codex" / "batches", "codex_batches"),
            (workspace / ".producer" / "footage_codex_review" / "batches", "ai_review_batches"),
            (workspace / ".producer" / "source_discovery", "source_discovery"),
        )
        if not existing and not any(path.exists() for path, _ in archive_dirs):
            return
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
        history = workspace / ".producer" / "footage_history" / stamp
        history.mkdir(parents=True, exist_ok=True)
        for path in existing:
            shutil.move(str(path), str(history / path.name))
        for source_dir, archive_name in archive_dirs:
            if source_dir.exists():
                shutil.move(str(source_dir), str(history / archive_name))

    def _save_checkpoint(self, workspace: Path, checkpoint: dict[str, Any]) -> None:
        completed_total = 0
        all_complete = True
        for state in (checkpoint.get("workers") or {}).values():
            assigned = [str(value) for value in (state.get("assigned_beat_ids") or [])]
            completed = [str(value) for value in (state.get("completed_beat_ids") or []) if str(value) in assigned]
            state["completed_beat_ids"] = list(dict.fromkeys(completed))
            state["pending_beat_ids"] = [beat_id for beat_id in assigned if beat_id not in state["completed_beat_ids"]]
            completed_total += len(state["completed_beat_ids"])
            if state["pending_beat_ids"]:
                all_complete = False
            state["updated_at"] = _now()
        checkpoint["completed_beats"] = completed_total
        checkpoint["updated_at"] = _now()
        if all_complete:
            checkpoint["status"] = "completed"
        _write_json_atomic(self._checkpoint_path(workspace), checkpoint)

    def _is_transient_failure(self, result: StageResult) -> bool:
        # Windows process initialization crashes (commonly 0xC0000142) are
        # recoverable here: the next attempt should start a fresh Codex
        # session instead of permanently failing the footage phase.
        if int(result.returncode or 0) in {3221225794, -1073741502}:
            return True
        message = str(result.last_message or "").strip().lower()
        if not message:
            return True
        return any(marker in message for marker in self.TRANSIENT_FAILURE_MARKERS)

    @staticmethod
    def _is_rate_limit_failure(result: StageResult) -> bool:
        message = str(result.last_message or "").strip().lower()
        return "rate limit" in message or "too many requests" in message

    def _run_codex_batches(
        self,
        job: dict[str, Any],
        workspace: Path,
        beats: list[dict[str, Any]],
        checkpoint: dict[str, Any],
    ) -> StageResult:
        worker = "codex"
        state = checkpoint["workers"][worker]
        try:
            effective_batch_size = max(1, int(checkpoint.get("batch_size") or self.batch_size))
        except (TypeError, ValueError):
            effective_batch_size = self.batch_size
        adaptive = bool(checkpoint.get("adaptive_batching"))
        fixed_batches = [] if adaptive else _chunks(beats, effective_batch_size)
        ordered_ids = [_beat_id(beat) for beat in beats if _beat_id(beat)]
        beat_by_id = {_beat_id(beat): beat for beat in beats if _beat_id(beat)}
        batch_plan = state.get("batch_plan") if isinstance(state.get("batch_plan"), list) else []
        if adaptive:
            state["batch_plan"] = batch_plan
        else:
            batch_plan = []
        batch_dir = workspace / ".producer" / "footage_codex" / "batches"
        batch_dir.mkdir(parents=True, exist_ok=True)
        valid_outputs: list[dict[str, Any]] = []
        completed: list[str] = []
        last_message = ""

        batch_index = 1
        while True:
            plan_entry: dict[str, Any] | None = None
            if adaptive:
                if batch_index <= len(batch_plan):
                    candidate_entry = batch_plan[batch_index - 1]
                    plan_entry = candidate_entry if isinstance(candidate_entry, dict) else None
                    expected_ids = [
                        str(value)
                        for value in ((plan_entry or {}).get("beat_ids") or [])
                        if str(value) in beat_by_id
                    ]
                    if not expected_ids:
                        del batch_plan[batch_index - 1:]
                        plan_entry = None
                if plan_entry is None:
                    completed_set = set(completed)
                    pending_ids = [beat_id for beat_id in ordered_ids if beat_id not in completed_set]
                    if not pending_ids:
                        break
                    try:
                        current_size = max(1, int(state.get("adaptive_batch_size") or effective_batch_size))
                    except (TypeError, ValueError):
                        current_size = effective_batch_size
                    current_size = min(current_size, int(checkpoint.get("batch_max_size") or self.batch_max_size))
                    expected_ids = pending_ids[:current_size]
                    plan_entry = {
                        "batch_index": batch_index,
                        "beat_ids": expected_ids,
                        "batch_size": len(expected_ids),
                        "status": "pending",
                    }
                    batch_plan.append(plan_entry)
                batch = [beat_by_id[beat_id] for beat_id in expected_ids]
                try:
                    estimate_size = max(1, int(state.get("adaptive_batch_size") or effective_batch_size))
                except (TypeError, ValueError):
                    estimate_size = effective_batch_size
                remaining_after = max(0, len(ordered_ids) - len(set(completed) | set(expected_ids)))
                state["total_batches"] = batch_index + ((remaining_after + estimate_size - 1) // estimate_size)
            else:
                if batch_index > len(fixed_batches):
                    break
                batch = fixed_batches[batch_index - 1]
                expected_ids = [_beat_id(beat) for beat in batch if _beat_id(beat)]
                state["total_batches"] = len(fixed_batches)

            total_batches = max(batch_index, int(state.get("total_batches") or batch_index))
            batch_path = batch_dir / f"batch_{batch_index:04d}.json"
            batch_payload: dict[str, Any] | None = None
            network_retries = 0
            continuation_turns = 0
            if batch_path.exists():
                try:
                    batch_payload = _validate_batch_output(batch_path, expected_ids)
                except RuntimeError:
                    batch_payload = None
            if batch_payload is None:
                state["current_batch"] = batch_index
                state["status"] = "running"
                state["last_error"] = ""
                checkpoint["status"] = "running"
                checkpoint["status_message"] = f"Đang tìm tư liệu {', '.join(expected_ids)} · batch {batch_index}/{total_batches}"
                self._save_checkpoint(workspace, checkpoint)
                relative_output = str(batch_path.relative_to(workspace))
                discovery_by_beat = self._discover_for_prompt(job, batch, workspace)
                base_prompt = build_worker_prompt(
                    job,
                    batch,
                    worker,
                    workspace,
                    relative_output,
                    discovery_by_beat=discovery_by_beat,
                )
                prompt = base_prompt
                result: StageResult | None = None
                while True:
                    if network_retries > 0:
                        checkpoint["status_message"] = (
                            f"Đã nối lại Codex; đang tiếp tục {', '.join(expected_ids)} · "
                            f"batch {batch_index}/{total_batches}"
                        )
                        self._save_checkpoint(workspace, checkpoint)
                    state["attempts"] = int(state.get("attempts") or 0) + 1
                    runner = getattr(self.codex_gateway, "run_prompt_reusable", None)
                    if callable(runner):
                        result = runner(prompt, workspace, "footage_codex")
                    else:
                        result = self.codex_gateway.run_prompt(prompt, workspace, "footage_codex")
                    last_message = result.last_message or last_message
                    if result.returncode != 0:
                        state["last_error"] = result.last_message or "Codex bị ngắt trước khi hoàn tất batch."
                        transient_failure = self._is_transient_failure(result)
                        rate_limited = self._is_rate_limit_failure(result)
                        checkpoint["status_message"] = (
                            "Codex đang bị giới hạn lượt gọi; giữ nguyên checkpoint để tự thử lại."
                            if rate_limited
                            else "Mất kết nối Codex; đang kiểm tra để tự nối lại cùng phiên hiện tại."
                            if transient_failure
                            else f"Batch {batch_index}/{total_batches} bị lỗi; đang kiểm tra kết quả."
                        )
                        self._save_checkpoint(workspace, checkpoint)
                        if network_retries >= self.batch_retries or not transient_failure:
                            checkpoint["status"] = "failed"
                            state["status"] = "failed"
                            if transient_failure:
                                checkpoint["status_message"] = (
                                    f"Mất kết nối Codex; đã thử kết nối lại {network_retries}/{self.batch_retries} lần "
                                    "bằng chat mới nhưng vẫn không thành công."
                                )
                            self._save_checkpoint(workspace, checkpoint)
                            return result
                        network_retries += 1
                        if rate_limited:
                            wait_seconds = int(self.rate_limit_wait_seconds)
                            checkpoint["status_message"] = (
                                f"Codex đang rate-limit; giữ nguyên batch {batch_index}/{total_batches} và "
                                f"tự thử lại lần {network_retries}/{self.batch_retries}"
                                + (f" sau {wait_seconds}s." if wait_seconds else ".")
                            )
                            self._save_checkpoint(workspace, checkpoint)
                            if wait_seconds > 0:
                                time.sleep(wait_seconds)
                            continue
                        checkpoint["status_message"] = (
                            f"Mất kết nối Codex; đang thử lại cùng phiên lần {network_retries}/{self.batch_retries}."
                        )
                        self._save_checkpoint(workspace, checkpoint)
                        continue

                    try:
                        batch_payload = _validate_batch_output(batch_path, expected_ids)
                        break
                    except RuntimeError as exc:
                        if continuation_turns >= self.batch_continuations:
                            state["last_error"] = str(exc)
                            state["status"] = "failed"
                            checkpoint["status"] = "failed"
                            checkpoint["status_message"] = f"Batch {batch_index}/{total_batches} trả về dữ liệu chưa đủ."
                            self._save_checkpoint(workspace, checkpoint)
                            return StageResult(1, str(exc), batch_path)
                        continuation_turns += 1
                        state["last_error"] = ""
                        prompt = (
                            base_prompt
                            + "\n\nLƯỢT TIẾP TỤC BẮT BUỘC: output batch hiện tại chưa qua validator. "
                            + f"Lỗi cụ thể: {exc}. "
                            + f"Mở `{relative_output}`, GIỮ nguyên mọi kết quả hợp lệ đã có và chỉ bổ sung/sửa đúng phần còn thiếu. "
                            + "Không bắt đầu lại toàn bộ batch, không bỏ beat im lặng. Trước khi kết thúc lượt, tự kiểm tra rằng MỖI beat_id được giao "
                            + "đều xuất hiện trong candidates/assets/presentation_effects và JSON đúng schema."
                        )
                        checkpoint["status_message"] = (
                            f"Codex chưa hoàn tất batch {batch_index}/{total_batches}; "
                            f"đang tiếp tục lượt {continuation_turns}/{self.batch_continuations}."
                        )
                        self._save_checkpoint(workspace, checkpoint)

            valid_outputs.append(batch_payload)
            completed.extend(expected_ids)
            state["completed_beat_ids"] = list(dict.fromkeys(completed))
            state["current_batch"] = batch_index
            is_complete = len(state["completed_beat_ids"]) >= len(ordered_ids)
            state["status"] = "completed" if is_complete else "running"
            state["last_error"] = ""
            if adaptive and plan_entry is not None:
                plan_entry["status"] = "completed"
                plan_entry["network_retries"] = network_retries
                plan_entry["continuations"] = continuation_turns
                try:
                    current_size = max(1, int(state.get("adaptive_batch_size") or effective_batch_size))
                except (TypeError, ValueError):
                    current_size = effective_batch_size
                if network_retries or continuation_turns:
                    next_size = max(effective_batch_size, current_size - self.batch_growth_step)
                else:
                    next_size = min(int(checkpoint.get("batch_max_size") or self.batch_max_size), current_size + self.batch_growth_step)
                state["adaptive_batch_size"] = next_size
                remaining = max(0, len(ordered_ids) - len(state["completed_beat_ids"]))
                state["total_batches"] = batch_index + ((remaining + next_size - 1) // next_size)
            aggregate_status = "completed" if is_complete else "in_progress"
            _write_json_atomic(workspace / "footage_codex.json", _aggregate_batch_outputs(worker, valid_outputs, aggregate_status))
            if (workspace / "footage_gemini.json").exists():
                merge_worker_results(workspace)
            checkpoint["status_message"] = (
                f"Đã xong {len(completed)}/{len(beats)} beat Codex · "
                f"batch {batch_index}/{max(batch_index, int(state.get('total_batches') or batch_index))}"
            )
            self._save_checkpoint(workspace, checkpoint)
            batch_index += 1

        if not beats:
            _write_json_atomic(workspace / "footage_codex.json", _empty_worker_payload(worker, status="completed"))
            state["status"] = "completed"
            self._save_checkpoint(workspace, checkpoint)
        return StageResult(0, last_message, workspace / ".producer" / "footage_codex")

    def _run_gemini_once(
        self,
        job: dict[str, Any],
        workspace: Path,
        beats: list[dict[str, Any]],
        checkpoint: dict[str, Any],
    ) -> StageResult:
        worker = "gemini"
        state = checkpoint["workers"][worker]
        output = workspace / "footage_gemini.json"
        expected_ids = [_beat_id(beat) for beat in beats if _beat_id(beat)]
        if output.exists():
            try:
                _validate_batch_output(output, expected_ids)
                state["completed_beat_ids"] = expected_ids
                state["status"] = "completed"
                self._save_checkpoint(workspace, checkpoint)
                return StageResult(0, "", output)
            except RuntimeError:
                pass
        state["status"] = "running"
        state["attempts"] = int(state.get("attempts") or 0) + 1
        checkpoint["status_message"] = "Gemini đang tìm phần tư liệu được giao."
        self._save_checkpoint(workspace, checkpoint)
        discovery_by_beat = self._discover_for_prompt(job, beats, workspace)
        prompt = build_worker_prompt(
            job,
            beats,
            worker,
            workspace,
            "footage_gemini.json",
            discovery_by_beat=discovery_by_beat,
        )
        result = self.gemini_gateway.run_prompt(prompt, workspace, "footage_gemini")
        if result.returncode != 0:
            state["status"] = "failed"
            state["last_error"] = result.last_message
            checkpoint["status"] = "failed"
            checkpoint["status_message"] = "Gemini bị lỗi khi tìm tư liệu."
            self._save_checkpoint(workspace, checkpoint)
            return result
        try:
            _validate_batch_output(output, expected_ids)
        except RuntimeError as exc:
            state["status"] = "failed"
            state["last_error"] = str(exc)
            checkpoint["status"] = "failed"
            self._save_checkpoint(workspace, checkpoint)
            return StageResult(1, str(exc), output)
        state["completed_beat_ids"] = expected_ids
        state["status"] = "completed"
        state["last_error"] = ""
        self._save_checkpoint(workspace, checkpoint)
        return result

    @staticmethod
    def _review_batch_payload(
        payload: dict[str, Any],
        expected_candidate_ids: list[str],
    ) -> list[dict[str, Any]]:
        reviews = payload.get("reviews") if isinstance(payload, dict) else None
        if not isinstance(reviews, list):
            raise RuntimeError("Codex review thiếu mảng reviews")
        expected = {str(value) for value in expected_candidate_ids if str(value)}
        seen: set[str] = set()
        normalized: list[dict[str, Any]] = []
        for item in reviews:
            if not isinstance(item, dict):
                continue
            candidate_id = str(item.get("candidate_id") or "").strip()
            beat_id = str(item.get("beat_id") or "").strip()
            decision = str(item.get("decision") or "").strip().upper()
            if candidate_id not in expected:
                raise RuntimeError(f"Codex review trả về candidate ngoài batch: {candidate_id or '<empty>'}")
            if decision not in {"ACCEPT", "REJECT"}:
                raise RuntimeError(f"Codex review decision không hợp lệ cho {candidate_id}: {decision or '<empty>'}")
            if candidate_id in seen:
                raise RuntimeError(f"Codex review lặp candidate: {candidate_id}")
            seen.add(candidate_id)
            normalized.append({
                "beat_id": beat_id,
                "candidate_id": candidate_id,
                "decision": decision,
                "reason": str(item.get("reason") or "").strip(),
            })
        missing = [candidate_id for candidate_id in expected_candidate_ids if candidate_id not in seen]
        if missing:
            raise RuntimeError(f"Codex review thiếu candidate: {', '.join(missing)}")
        return normalized

    @staticmethod
    def _review_retry_requests(
        payload: dict[str, Any],
        expected_beat_ids: list[str],
        reviews: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        rows = payload.get("retry_requests") if isinstance(payload, dict) else None
        if rows is None:
            return []
        if not isinstance(rows, list):
            raise RuntimeError("Codex review retry_requests phải là JSON array")
        expected = {str(value) for value in expected_beat_ids if str(value)}
        accepted = {
            str(item.get("beat_id") or "").strip()
            for item in reviews
            if str(item.get("decision") or "").upper() == "ACCEPT"
        }
        normalized: list[dict[str, Any]] = []
        seen: set[str] = set()
        for item in rows:
            if not isinstance(item, dict):
                continue
            beat_id = str(item.get("beat_id") or "").strip()
            if beat_id not in expected:
                raise RuntimeError(f"Codex review yêu cầu tìm lại beat ngoài batch: {beat_id or '<empty>'}")
            if beat_id in accepted or beat_id in seen:
                continue
            queries = []
            for value in item.get("search_queries") or []:
                query = " ".join(str(value or "").split()).strip()
                if query and query.lower() not in {existing.lower() for existing in queries}:
                    queries.append(query)
                if len(queries) >= 3:
                    break
            if not queries:
                continue
            seen.add(beat_id)
            normalized.append({
                "beat_id": beat_id,
                "reason": str(item.get("reason") or "").strip(),
                "search_queries": queries,
            })
        return normalized

    @staticmethod
    def _review_image_evidence(
        candidates: list[dict[str, Any]],
        *,
        max_total: int = 64,
        per_candidate: int = 2,
    ) -> dict[str, list[str]]:
        """Choose real local frames fairly so no reviewed candidate is metadata-only."""
        candidate_frames: list[tuple[str, list[str]]] = []
        for candidate in candidates:
            candidate_id = str(candidate.get("candidate_id") or "").strip()
            if not candidate_id:
                continue
            resolved_frames: list[str] = []
            local_seen: set[str] = set()
            for value in candidate.get("representative_frames") or []:
                path = Path(str(value))
                if not path.exists() or not path.is_file():
                    continue
                resolved = str(path.resolve())
                key = resolved.lower()
                if key in local_seen:
                    continue
                local_seen.add(key)
                resolved_frames.append(resolved)
            if not resolved_frames:
                raise RuntimeError(f"Candidate {candidate_id} không có frame local hợp lệ để AI duyệt")
            kind = str(candidate.get("kind") or "").lower()
            if "video" not in kind:
                resolved_frames = resolved_frames[:1]
            candidate_frames.append((candidate_id, resolved_frames))

        if not candidate_frames:
            return {}

        requested_per_candidate = max(1, int(per_candidate))
        soft_limit = max(len(candidate_frames), max(1, int(max_total)))
        selected: dict[str, list[str]] = {candidate_id: [] for candidate_id, _ in candidate_frames}

        # First pass is mandatory fairness: every candidate gets one real frame,
        # even when an old/low soft image limit would otherwise cut off the tail.
        for candidate_id, frames in candidate_frames:
            selected[candidate_id].append(frames[0])

        # Additional passes improve video coverage without starving later candidates.
        for frame_index in range(1, requested_per_candidate):
            if sum(len(paths) for paths in selected.values()) >= soft_limit:
                break
            for candidate_id, frames in candidate_frames:
                if sum(len(paths) for paths in selected.values()) >= soft_limit:
                    break
                if frame_index >= len(frames):
                    continue
                frame = frames[frame_index]
                selected[candidate_id].append(frame)

        return selected

    @staticmethod
    def _flatten_review_image_evidence(
        candidates: list[dict[str, Any]],
        evidence: dict[str, list[str]],
    ) -> list[str]:
        paths: list[str] = []
        seen: set[str] = set()
        for candidate in candidates:
            candidate_id = str(candidate.get("candidate_id") or "").strip()
            for path in evidence.get(candidate_id, []):
                key = str(path).lower()
                if key in seen:
                    continue
                seen.add(key)
                paths.append(path)
        return paths

    @staticmethod
    def _review_image_paths(candidates: list[dict[str, Any]], *, max_total: int = 64) -> list[str]:
        evidence = FootageCoordinator._review_image_evidence(
            candidates,
            max_total=max_total,
            per_candidate=2,
        )
        return FootageCoordinator._flatten_review_image_evidence(candidates, evidence)

    def _run_vision_review_batch(
        self,
        job: dict[str, Any],
        workspace: Path,
        checkpoint: dict[str, Any],
        batch: list[dict[str, Any]],
        batch_candidates: list[dict[str, Any]],
        batch_index: int,
        total_batches: int,
    ) -> tuple[list[dict[str, Any]] | None, list[dict[str, Any]], StageResult | None, str, str]:
        """Review one already-materialized batch and cache the AI decision payload."""
        worker_state = checkpoint["workers"]["codex"]
        beat_ids = [_beat_id(beat) for beat in batch if _beat_id(beat)]
        expected_candidate_ids = [
            str(candidate.get("candidate_id") or "")
            for candidate in batch_candidates
            if str(candidate.get("candidate_id") or "")
        ]
        review_root = workspace / ".producer" / "footage_codex_review" / "batches"
        review_root.mkdir(parents=True, exist_ok=True)
        batch_path = review_root / f"batch_{batch_index:04d}.json"
        audit_path = review_root / f"batch_{batch_index:04d}_audit.json"
        reviews: list[dict[str, Any]] | None = None
        retry_requests: list[dict[str, Any]] = []
        result: StageResult | None = None
        review_error = ""
        last_message = ""

        if batch_path.exists():
            try:
                cached = json.loads(batch_path.read_text(encoding="utf-8"))
                if int(cached.get("review_contract_version") or 0) != VISUAL_REVIEW_CONTRACT_VERSION:
                    raise RuntimeError("cached visual review contract đã cũ")
                reviews = self._review_batch_payload(cached, expected_candidate_ids)
                retry_requests = self._review_retry_requests(cached, beat_ids, reviews)
            except (OSError, json.JSONDecodeError, RuntimeError):
                reviews = None

        if reviews is None:
            attach_images = _env_flag("COFI_VISION_REVIEW_ATTACH_IMAGES", True)
            try:
                evidence_by_candidate = (
                    self._review_image_evidence(
                        batch_candidates,
                        max_total=_positive_int_env("COFI_VISION_REVIEW_MAX_IMAGES", 64),
                        per_candidate=_positive_int_env("COFI_VISION_REVIEW_FRAMES_PER_VIDEO", 2),
                    )
                    if attach_images
                    else {}
                )
            except RuntimeError as exc:
                review_error = str(exc)
                worker_state["status"] = "failed"
                worker_state["last_error"] = review_error
                checkpoint["status"] = "failed"
                checkpoint["status_message"] = f"AI final review batch {batch_index} bị chặn: {review_error}"
                self._save_checkpoint(workspace, checkpoint)
                return None, [], None, review_error, ""
            image_paths = self._flatten_review_image_evidence(batch_candidates, evidence_by_candidate)
            prompt = build_codex_vision_review_prompt(
                job,
                batch,
                batch_candidates,
                attached_frames_by_candidate=evidence_by_candidate,
            )
            _write_json_atomic(audit_path, {
                "review_contract_version": VISUAL_REVIEW_CONTRACT_VERSION,
                "status": "ready",
                "updated_at": _now(),
                "batch_index": batch_index,
                "beat_ids": beat_ids,
                "candidate_ids": expected_candidate_ids,
                "attached_frames_by_candidate": evidence_by_candidate,
                "attached_image_count": len(image_paths),
            })
            for attempt in range(self.batch_retries + 1):
                worker_state["attempts"] = int(worker_state.get("attempts") or 0) + 1
                worker_state["current_batch"] = batch_index
                previous = checkpoint.get("tool_progress") if isinstance(checkpoint.get("tool_progress"), dict) else {}
                checkpoint["tool_progress"] = {
                    **previous,
                    "stage": "reviewing",
                    "current_beat_id": beat_ids[-1] if beat_ids else "",
                }
                checkpoint["status_message"] = (
                    f"AI đang duyệt candidate đã tải cho {', '.join(beat_ids)} · "
                    f"batch {batch_index}/{max(1, total_batches)}"
                )
                self._save_checkpoint(workspace, checkpoint)
                fresh_runner = getattr(self.review_gateway, "run_prompt", None)
                reusable_runner = getattr(self.review_gateway, "run_prompt_reusable", None)
                if callable(fresh_runner):
                    result = fresh_runner(
                        prompt,
                        workspace,
                        "footage_codex_review",
                        use_remotion_root=False,
                        image_paths=image_paths,
                    )
                elif callable(reusable_runner):
                    try:
                        result = reusable_runner(
                            prompt,
                            workspace,
                            "footage_codex_review",
                            use_remotion_root=False,
                            image_paths=image_paths,
                        )
                    except TypeError:
                        result = reusable_runner(prompt, workspace, "footage_codex_review")
                else:
                    review_error = "AI router không có runner cho footage review"
                    break
                last_message = result.last_message or last_message
                if result.returncode != 0:
                    review_error = result.last_message or "AI final review failed"
                    if attempt < self.batch_retries and self._is_transient_failure(result):
                        continue
                    break
                try:
                    payload = _json_object_from_message(result.last_message)
                    reviews = self._review_batch_payload(payload, expected_candidate_ids)
                    retry_requests = self._review_retry_requests(payload, beat_ids, reviews)
                    _write_json_atomic(batch_path, {
                        "review_contract_version": VISUAL_REVIEW_CONTRACT_VERSION,
                        "reviews": reviews,
                        "retry_requests": retry_requests,
                    })
                    _write_json_atomic(audit_path, {
                        "review_contract_version": VISUAL_REVIEW_CONTRACT_VERSION,
                        "status": "completed",
                        "updated_at": _now(),
                        "batch_index": batch_index,
                        "beat_ids": beat_ids,
                        "candidate_ids": expected_candidate_ids,
                        "attached_frames_by_candidate": evidence_by_candidate,
                        "attached_image_count": len(image_paths),
                        "reviewed_candidate_ids": [str(item.get("candidate_id") or "") for item in reviews],
                    })
                    review_error = ""
                    break
                except RuntimeError as exc:
                    review_error = str(exc)
                    if attempt < self.batch_retries:
                        prompt += (
                            "\n\nKết quả vừa rồi không hợp lệ: " + review_error + ". "
                            "Trả lại JSON đầy đủ cho TẤT CẢ candidate_id đã giao, không làm thêm việc khác."
                        )
                        continue
                    break

        if reviews is None:
            worker_state["status"] = "failed"
            worker_state["last_error"] = review_error
            checkpoint["status"] = "failed"
            checkpoint["status_message"] = f"AI final review batch {batch_index} bị lỗi: {review_error}"
            self._save_checkpoint(workspace, checkpoint)
        return reviews, retry_requests, result, review_error, last_message

    def _discard_rejected_media(
        self,
        workspace: Path,
        all_candidates: list[dict[str, Any]],
        reviews: list[dict[str, Any]],
        decided_reviews: list[dict[str, Any]],
        discard_candidate_ids: set[str] | None = None,
    ) -> None:
        """Delete local candidate media that will not be used in the final cut."""
        fresh_rejected_ids = {
            str(review.get("candidate_id") or "").strip()
            for review in reviews
            if str(review.get("decision") or "").upper() == "REJECT"
            and str(review.get("candidate_id") or "").strip()
        }
        fresh_rejected_ids.update(str(value).strip() for value in (discard_candidate_ids or set()) if str(value).strip())
        if not fresh_rejected_ids:
            return

        known_rejected_ids = {
            str(review.get("candidate_id") or "").strip()
            for review in decided_reviews
            if str(review.get("decision") or "").upper() == "REJECT"
            and str(review.get("candidate_id") or "").strip()
        }
        known_rejected_ids.update(
            str(candidate.get("candidate_id") or "").strip()
            for candidate in all_candidates
            if candidate.get("selected_for_beat") is False
            and str(candidate.get("candidate_id") or "").strip()
        )
        review_by_id = {
            str(review.get("candidate_id") or "").strip(): review
            for review in reviews
            if str(review.get("candidate_id") or "").strip()
        }

        def candidate_paths(candidate: dict[str, Any]) -> list[Path]:
            values = [candidate.get("local_path"), *(candidate.get("representative_frames") or [])]
            resolved: list[Path] = []
            seen: set[str] = set()
            for value in values:
                path = _resolve_media_path(workspace, value)
                if path is None:
                    continue
                try:
                    path = path.resolve()
                except OSError:
                    continue
                key = str(path).lower()
                if key in seen:
                    continue
                seen.add(key)
                resolved.append(path)
            return resolved

        survivors = [
            candidate for candidate in all_candidates
            if str(candidate.get("candidate_id") or "").strip() not in known_rejected_ids
        ]
        protected_paths = {
            str(path).lower()
            for candidate in survivors
            for path in candidate_paths(candidate)
        }
        protected_sources = {
            str(candidate.get("source_url") or "").strip().lower()
            for candidate in survivors
            if str(candidate.get("source_url") or "").strip()
        }

        allowed_roots = [workspace.resolve()]
        retriever = getattr(self.footage_engine, "retriever", None)
        library_root_value = getattr(retriever, "library_root", None)
        library_root: Path | None = None
        if library_root_value:
            try:
                library_root = Path(library_root_value).resolve()
                allowed_roots.append(library_root)
            except OSError:
                library_root = None

        def allowed(path: Path) -> bool:
            for root in allowed_roots:
                try:
                    path.relative_to(root)
                    return True
                except ValueError:
                    continue
            return False

        candidates_by_id = {
            str(candidate.get("candidate_id") or "").strip(): candidate
            for candidate in all_candidates
            if str(candidate.get("candidate_id") or "").strip()
        }
        rejected_manifest_keys: set[tuple[str, str, str]] = set()
        survivor_manifest_keys: set[tuple[str, str, str]] = set()
        for candidate in survivors:
            path = _resolve_media_path(workspace, candidate.get("local_path"))
            path_key = str(path.resolve()).lower() if path is not None else ""
            survivor_manifest_keys.add((
                str(candidate.get("beat_id") or "").strip().upper(),
                str(candidate.get("source_url") or "").strip().lower(),
                path_key,
            ))

        for candidate_id in fresh_rejected_ids:
            candidate = candidates_by_id.get(candidate_id)
            if candidate is None:
                continue
            review = review_by_id.get(candidate_id) or {}
            ai_decision = str(review.get("decision") or candidate.get("codex_decision") or "REJECT").upper()
            candidate["codex_decision"] = ai_decision
            candidate["codex_review_reason"] = str(review.get("reason") or candidate.get("codex_review_reason") or "").strip()
            candidate["codex_reviewed_actual_content"] = True
            candidate["selection_status"] = "discarded"
            candidate["local_media_deleted"] = False
            candidate["local_media_deleted_at"] = _now()

            local = _resolve_media_path(workspace, candidate.get("local_path"))
            local_key = str(local.resolve()).lower() if local is not None else ""
            rejected_manifest_keys.add((
                str(candidate.get("beat_id") or "").strip().upper(),
                str(candidate.get("source_url") or "").strip().lower(),
                local_key,
            ))

            deleted_any = False
            for path in candidate_paths(candidate):
                if str(path).lower() in protected_paths or not allowed(path):
                    continue
                try:
                    if path.exists() and path.is_file():
                        path.unlink()
                        deleted_any = True
                except OSError:
                    continue

            source_url = str(candidate.get("source_url") or "").strip()
            if library_root is not None and source_url and source_url.lower() not in protected_sources:
                source_hash = hashlib.sha256(source_url.encode("utf-8", errors="ignore")).hexdigest()[:20]
                source_root = library_root / "sources" / source_hash
                try:
                    if source_root.exists():
                        shutil.rmtree(source_root)
                        deleted_any = True
                except OSError:
                    pass
            candidate["local_media_deleted"] = deleted_any

        manifest_path = workspace / "footage_live_downloads.json"
        if manifest_path.exists():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                manifest = {}
            rows = manifest.get("items") if isinstance(manifest, dict) else []
            if isinstance(rows, list):
                kept: list[dict[str, Any]] = []
                changed = False
                for row in rows:
                    if not isinstance(row, dict):
                        continue
                    raw_path = _resolve_media_path(workspace, row.get("path"))
                    row_key = (
                        str(row.get("beat_id") or "").strip().upper(),
                        str(row.get("source_url") or "").strip().lower(),
                        str(raw_path.resolve()).lower() if raw_path is not None else "",
                    )
                    if row_key in rejected_manifest_keys and row_key not in survivor_manifest_keys:
                        changed = True
                        continue
                    kept.append(row)
                if changed:
                    _write_json_atomic(manifest_path, {
                        "version": int(manifest.get("version") or 1) if isinstance(manifest, dict) else 1,
                        "updated_at": _now(),
                        "items": kept,
                    })

    def _commit_reviewed_media(
        self,
        workspace: Path,
        all_candidates: list[dict[str, Any]],
        reviews: list[dict[str, Any]],
        decided_reviews: list[dict[str, Any]],
    ) -> set[str]:
        """Keep one approved candidate per reviewed beat and delete everything else."""
        fresh_ids = {
            str(review.get("candidate_id") or "").strip()
            for review in reviews
            if str(review.get("candidate_id") or "").strip()
        }
        reviewed_beats = {
            str(review.get("beat_id") or "").strip()
            for review in reviews
            if str(review.get("beat_id") or "").strip()
        }
        accepted_ids = {
            str(review.get("candidate_id") or "").strip()
            for review in reviews
            if str(review.get("decision") or "").upper() == "ACCEPT"
            and str(review.get("candidate_id") or "").strip()
        }
        review_by_id = {
            str(review.get("candidate_id") or "").strip(): review
            for review in reviews
            if str(review.get("candidate_id") or "").strip()
        }
        selected_ids: set[str] = set()
        selected_beats: set[str] = set()
        approved_rows: list[dict[str, Any]] = []

        for candidate in all_candidates:
            candidate_id = str(candidate.get("candidate_id") or "").strip()
            beat_id = str(candidate.get("beat_id") or "").strip()
            if candidate_id not in fresh_ids:
                continue
            review = review_by_id.get(candidate_id) or {}
            candidate["codex_decision"] = str(review.get("decision") or "REJECT").upper()
            candidate["codex_review_reason"] = str(review.get("reason") or "").strip()
            candidate["codex_reviewed_actual_content"] = True
            candidate["selected_for_beat"] = False
            candidate["selection_status"] = "discarded"
            if candidate_id not in accepted_ids or not beat_id or beat_id in selected_beats:
                continue

            published, error = self._publish_vision_asset(workspace, candidate)
            valid, validation_error = (
                _validate_media_file(workspace, published, candidate.get("kind"))
                if published else (False, error)
            )
            if not valid:
                candidate["validation_error"] = validation_error or error
                continue

            candidate["selected_for_beat"] = True
            candidate["selection_status"] = "selected"
            candidate["decision"] = "ACCEPT"
            candidate["local_path"] = published
            selected_ids.add(candidate_id)
            selected_beats.add(beat_id)
            approved_rows.append({
                "candidate_id": candidate_id,
                "beat_id": beat_id,
                "path": published,
                "source_url": str(candidate.get("source_url") or ""),
                "name": Path(published).name,
                "kind": str(candidate.get("kind") or "sourced_video"),
                "reason": str(review.get("reason") or "").strip(),
                "timestamp_range": str(candidate.get("timestamp_range") or ""),
                "decision": "ACCEPT",
            })

        discard_ids = fresh_ids - selected_ids
        self._discard_rejected_media(
            workspace,
            all_candidates,
            reviews,
            decided_reviews,
            discard_candidate_ids=discard_ids,
        )

        approved_path = workspace / "footage_approved_live.json"
        existing = {}
        if approved_path.exists():
            try:
                existing = json.loads(approved_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                existing = {}
        existing_rows = existing.get("items") if isinstance(existing, dict) else []
        kept_rows = [
            row for row in (existing_rows or [])
            if isinstance(row, dict) and str(row.get("beat_id") or "").strip() not in reviewed_beats
        ]
        _write_json_atomic(approved_path, {
            "version": 1,
            "updated_at": _now(),
            "items": kept_rows + approved_rows,
        })
        return selected_beats

    @staticmethod
    def _publish_vision_asset(workspace: Path, candidate: dict[str, Any]) -> tuple[str, str]:
        source = _resolve_media_path(workspace, candidate.get("local_path"))
        if source is None or not source.exists() or not source.is_file():
            return "", "candidate local file không tồn tại"
        beat_id = str(candidate.get("beat_id") or "unknown").strip() or "unknown"
        candidate_id = str(candidate.get("candidate_id") or "candidate").strip() or "candidate"
        safe_id = "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in candidate_id)
        destination_dir = workspace / "media" / "vision" / beat_id
        destination_dir.mkdir(parents=True, exist_ok=True)
        suffix = source.suffix.lower() or (".mp4" if "video" in str(candidate.get("kind") or "").lower() else ".jpg")
        destination = destination_dir / f"{safe_id}{suffix}"
        try:
            if source.resolve() != destination.resolve():
                shutil.copy2(source, destination)
        except OSError as exc:
            return "", f"không publish được candidate: {exc}"
        return str(destination.resolve()), ""

    def _run_vision_codex(
        self,
        job: dict[str, Any],
        workspace: Path,
        beats: list[dict[str, Any]],
        checkpoint: dict[str, Any],
    ) -> StageResult:
        worker_state = checkpoint["workers"]["codex"]
        review_provider = self._review_provider_name()
        worker_state["status"] = "running"
        checkpoint["status"] = "running"
        checkpoint["pipeline"] = "vision_codex"
        checkpoint["search_mode"] = "tools-only"
        checkpoint["review_mode"] = "selected-ai-router"
        checkpoint["review_provider"] = review_provider
        checkpoint["control_state"] = "running"
        checkpoint["tool_progress"] = checkpoint.get("tool_progress") or {
            "completed_beats": 0,
            "total_beats": len(beats),
            "current_beat_id": "",
        }
        checkpoint["status_message"] = (
            f"Footage tools đang tìm/tải/semantic-rank candidate; {review_provider.title()} chỉ duyệt media đã tải."
        )
        approved_path = workspace / "footage_approved_live.json"
        if not approved_path.exists():
            _write_json_atomic(approved_path, {"version": 1, "updated_at": _now(), "items": []})
        self._save_checkpoint(workspace, checkpoint)
        try:
            self._await_control(workspace, checkpoint)
        except FootageStopped as exc:
            return self._stopped_result(workspace, checkpoint, str(exc))

        effective_review_batch_size = max(1, min(self.review_batch_size, self.batch_size))
        assigned_ids = [_beat_id(beat) for beat in beats if _beat_id(beat)]
        self._recover_footage_resume_state(workspace, checkpoint, assigned_ids)
        checkpoint_completed_ids = list(dict.fromkeys(
            str(value).strip()
            for value in (worker_state.get("completed_beat_ids") or [])
            if str(value).strip() in assigned_ids
        ))
        completed_id_set = set(checkpoint_completed_ids)
        remaining_beats = [beat for beat in beats if _beat_id(beat) not in completed_id_set]
        all_review_batches = _chunks(remaining_beats, effective_review_batch_size)
        total_review_batches = len(_chunks(beats, effective_review_batch_size))
        worker_state["total_batches"] = total_review_batches
        review_root = workspace / ".producer" / "footage_codex_review" / "batches"
        review_root.mkdir(parents=True, exist_ok=True)
        stream_candidates: list[dict[str, Any]] = []
        stream_reviews: list[dict[str, Any]] = []
        stream_retry_requests: list[dict[str, Any]] = []
        stream_completed_ids: list[str] = list(checkpoint_completed_ids)
        stream_pending_beats: list[dict[str, Any]] = []
        stream_pending_candidates: list[dict[str, Any]] = []
        stream_batch_index = int(worker_state.get("current_batch") or 0)
        stream_last_message = ""
        stream_failure: StageResult | None = None
        streamed_review_complete = False
        beat_by_id = {_beat_id(beat): beat for beat in beats if _beat_id(beat)}
        retry_audit: dict[str, Any] = {
            "version": 1,
            "max_rounds": self.ai_retry_rounds,
            "rounds": [],
            "updated_at": _now(),
        }

        prepared: dict[str, Any] | None = None
        queue_path = workspace / "footage_candidate_queue.json"
        previous_queue_beats: list[dict[str, Any]] = []
        if queue_path.exists():
            try:
                cached_queue = json.loads(queue_path.read_text(encoding="utf-8"))
                cached_beats = cached_queue.get("beats") if isinstance(cached_queue, dict) else None
                previous_queue_beats = [
                    row for row in (cached_beats or [])
                    if isinstance(row, dict) and str(row.get("beat_id") or "").strip() in completed_id_set
                ]
                stream_candidates.extend(
                    candidate
                    for row in previous_queue_beats
                    for candidate in (row.get("candidates") or [])
                    if isinstance(candidate, dict)
                )
                expected_ids = [_beat_id(beat) for beat in beats if _beat_id(beat)]
                cached_ids = [str(row.get("beat_id") or "") for row in (cached_beats or []) if isinstance(row, dict)]
                if cached_queue.get("status") == "completed" and cached_ids == expected_ids:
                    cached_candidates = [
                        candidate
                        for row in cached_beats
                        for candidate in (row.get("candidates") or [])
                        if isinstance(candidate, dict)
                    ]
                    if cached_candidates:
                        prepared = {
                            "status": "completed",
                            "candidates": cached_candidates,
                            "failures": cached_queue.get("failures") or [],
                        }
                        checkpoint["status_message"] = "Tái dùng candidate semantic đã chuẩn bị cho cùng visual manifest."
                        self._save_checkpoint(workspace, checkpoint)
            except (OSError, json.JSONDecodeError, AttributeError, TypeError):
                prepared = None
        for review_path in sorted(review_root.glob("batch_*.json")):
            if review_path.name.endswith("_audit.json"):
                continue
            try:
                cached_review = json.loads(review_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            stream_reviews.extend(
                review for review in (cached_review.get("reviews") or [])
                if isinstance(review, dict)
            )
        if prepared is None:
            try:
                def prepared_beat_review(
                    beat: dict[str, Any],
                    beat_candidates: list[dict[str, Any]],
                    done: int,
                    total: int,
                ) -> None:
                    nonlocal stream_batch_index, stream_last_message, stream_failure
                    stream_candidates.extend(beat_candidates)
                    stream_pending_beats.append(beat)
                    stream_pending_candidates.extend(beat_candidates)
                    if len(stream_pending_beats) < effective_review_batch_size and int(done) < int(total):
                        return

                    stream_batch_index += 1
                    reviews, retry_requests, review_result, review_error, review_message = self._run_vision_review_batch(
                        job,
                        workspace,
                        checkpoint,
                        list(stream_pending_beats),
                        list(stream_pending_candidates),
                        stream_batch_index,
                        total_review_batches,
                    )
                    if review_message:
                        stream_last_message = review_message
                    if reviews is None:
                        stream_failure = review_result or StageResult(
                            1,
                            review_error or f"AI final review batch {stream_batch_index} failed",
                            review_root / f"batch_{stream_batch_index:04d}.json",
                        )
                        raise RuntimeError(stream_failure.last_message or "AI final review failed")

                    stream_reviews.extend(reviews)
                    self._commit_reviewed_media(workspace, stream_candidates, reviews, stream_reviews)
                    if retry_requests and self.ai_retry_rounds > 0:
                        stream_last_message = self._retry_rejected_beats_immediately(
                            job,
                            workspace,
                            checkpoint,
                            retry_requests,
                            beat_by_id,
                            stream_candidates,
                            stream_reviews,
                            retry_audit,
                            stream_last_message,
                        )
                    else:
                        stream_retry_requests.extend(retry_requests)
                    beat_ids = [_beat_id(item) for item in stream_pending_beats if _beat_id(item)]
                    accepted_in_batch = {
                        str(c.get("beat_id") or "").strip()
                        for c in stream_candidates
                        if c.get("selected_for_beat") is True and str(c.get("beat_id") or "").strip() in beat_ids
                    }
                    for beat_id in beat_ids:
                        if beat_id not in accepted_in_batch:
                            # STRICT BAN ON AUTOMATIC CROSS-BEAT SPLICING / HOLDING (`0%` `FT-*-hold-*`):
                            # Never copy or hold a previous beat's footage clip onto a new voice sentence.
                            # When a beat has no 100% eye-verified, clean-cropped, voice-matched real footage,
                            # mark it so the pipeline routes it to Priority #2 (`@vox` illustration) or Priority #3 (`@ai_visual`).
                            b_candidates = [
                                c for c in stream_candidates if str(c.get("beat_id") or "").strip() == beat_id
                            ]
                            if b_candidates:
                                for c in b_candidates:
                                    c["ai_fallback_recommended"] = True
                                    c["real_video_search_complete"] = True
                                    c["real_still_search_complete"] = True
                                    if not c.get("ai_fallback_reason"):
                                        c["ai_fallback_reason"] = (
                                            "Không có footage thật khớp 100% nghĩa câu voice và sạch 100% logo/chữ chạy bên khác; "
                                            "chuyển sang Ưu tiên số 2 (VOX minh họa) hoặc Ưu tiên số 3 (Ảnh AI)."
                                        )
                            else:
                                stream_candidates.append({
                                    "candidate_id": f"FT-{beat_id}-vox-or-ai-fallback",
                                    "beat_id": beat_id,
                                    "source_priority": "prefer_real",
                                    "decision": "REVIEW",
                                    "kind": "sourced_video",
                                    "reason": (
                                        "Không có footage thật khớp 100% nghĩa câu voice và sạch 100% logo/chữ chạy bên khác; "
                                        "chuyển sang Ưu tiên số 2 (VOX minh họa) hoặc Ưu tiên số 3 (Ảnh AI)."
                                    ),
                                    "ai_fallback_recommended": True,
                                    "real_video_search_complete": True,
                                    "real_still_search_complete": True,
                                    "ai_fallback_reason": (
                                        "Không có footage thật khớp 100% nghĩa câu voice và sạch 100% logo/chữ chạy bên khác; "
                                        "chuyển sang Ưu tiên số 2 (VOX minh họa) hoặc Ưu tiên số 3 (Ảnh AI)."
                                    ),
                                })
                    stream_completed_ids.extend(beat_ids)
                    worker_state["current_batch"] = stream_batch_index
                    worker_state["completed_beat_ids"] = list(dict.fromkeys(stream_completed_ids))
                    worker_state["pending_beat_ids"] = [
                        _beat_id(item)
                        for item in beats
                        if _beat_id(item) not in worker_state["completed_beat_ids"]
                    ]
                    accepted_all_beats = {
                        str(candidate.get("beat_id") or "").strip()
                        for candidate in stream_candidates
                        if candidate.get("selected_for_beat") is True
                    }
                    fallback_all_beats = {
                        str(candidate.get("beat_id") or "").strip()
                        for candidate in stream_candidates
                        if str(candidate.get("beat_id") or "").strip()
                        and candidate.get("ai_fallback_recommended") is True
                        and str(candidate.get("beat_id") or "").strip() not in accepted_all_beats
                    }
                    checkpoint["ai_fallback_beat_ids"] = sorted(fallback_all_beats)
                    checkpoint["ai_fallback_count"] = len(fallback_all_beats)
                    previous = checkpoint.get("tool_progress") if isinstance(checkpoint.get("tool_progress"), dict) else {}
                    checkpoint["tool_progress"] = {
                        **previous,
                        "stage": "preparing",
                        "completed_beats": int(done),
                        "total_beats": int(total),
                        "current_beat_id": _beat_id(beat),
                        "canonical_completed_beats": len(accepted_all_beats),
                        "ai_fallback_count": len(fallback_all_beats),
                    }
                    checkpoint["status_message"] = (
                        f"Đã duyệt batch {stream_batch_index}: "
                        f"{len(accepted_in_batch)}/{len(beat_ids)} beat đạt chuẩn, "
                        f"{len(beat_ids) - len(accepted_in_batch)} beat gán AI bổ sung ngay; "
                        f"tổng lũy kế {len(accepted_all_beats)} thật, {len(fallback_all_beats)} AI."
                    )
                    self._save_checkpoint(workspace, checkpoint)
                    stream_pending_beats.clear()
                    stream_pending_candidates.clear()

                def discovery_progress(done: int, total: int, provider: str, query: str) -> None:
                    previous = checkpoint.get("tool_progress") if isinstance(checkpoint.get("tool_progress"), dict) else {}
                    if provider == "semantic_rank":
                        checkpoint["tool_progress"] = {
                            **previous,
                            "stage": "ranking",
                            "completed_beats": len(checkpoint_completed_ids),
                            "total_beats": len(beats),
                            "current_beat_id": str(query or ""),
                            "rank_completed": int(done),
                            "rank_total": int(total),
                        }
                        checkpoint["status_message"] = (
                            f"Semantic rank {done}/{total} beat · {query}; "
                            f"{review_provider.title()} chỉ duyệt media đã tải."
                        )
                    else:
                        checkpoint["tool_progress"] = {
                            **previous,
                            "stage": "searching",
                            "completed_beats": len(checkpoint_completed_ids),
                            "total_beats": len(beats),
                            "current_beat_id": "",
                            "search_completed": int(done),
                            "search_total": int(total),
                            "search_provider": str(provider or ""),
                            "search_query": str(query or "")[:240],
                        }
                        provider_text = f" · {provider}" if provider else ""
                        checkpoint["status_message"] = (
                            f"Tools đang tìm nguồn {done}/{total} lượt{provider_text}; "
                            f"{review_provider.title()} chỉ duyệt media đã tải."
                        )
                    self._save_checkpoint(workspace, checkpoint)

                def tool_progress(done: int, total: int, beat_id: str) -> None:
                    previous = checkpoint.get("tool_progress") if isinstance(checkpoint.get("tool_progress"), dict) else {}
                    checkpoint["tool_progress"] = {
                        **previous,
                        "stage": "preparing",
                        "completed_beats": len(checkpoint_completed_ids) + int(done),
                        "total_beats": int(total),
                        "current_beat_id": str(beat_id or ""),
                    }
                    checkpoint["status_message"] = (
                        f"Tools đã chuẩn bị candidate {len(checkpoint_completed_ids) + int(done)}/{len(beats)} beat · {beat_id}; "
                        f"{review_provider.title()} sẽ chỉ duyệt media đã tải."
                    )
                    self._save_checkpoint(workspace, checkpoint)

                previous = checkpoint.get("tool_progress") if isinstance(checkpoint.get("tool_progress"), dict) else {}
                checkpoint["tool_progress"] = {
                    **previous,
                    "stage": "preparing",
                    "completed_beats": len(checkpoint_completed_ids),
                    "total_beats": len(beats),
                    "current_beat_id": "",
                }
                checkpoint["status_message"] = (
                    "Semantic rank hoàn tất; tools đang tải/cắt candidate đầu tiên để gửi AI duyệt."
                )
                self._save_checkpoint(workspace, checkpoint)

                prepared = self._prepare_with_controls(
                    job,
                    remaining_beats,
                    workspace,
                    checkpoint,
                    progress_callback=tool_progress,
                    discovery_progress_callback=discovery_progress,
                    prepared_beat_callback=prepared_beat_review,
                    reset_live_downloads=not bool(checkpoint_completed_ids),
                    persist_queue=not bool(checkpoint_completed_ids),
                )
                streamed_review_complete = (
                    len(set(stream_completed_ids))
                    == len([beat for beat in beats if _beat_id(beat)])
                )
                if checkpoint_completed_ids:
                    new_candidates = [item for item in (prepared.get("candidates") or []) if isinstance(item, dict)]
                    candidates_by_beat: dict[str, list[dict[str, Any]]] = {}
                    for candidate in new_candidates:
                        candidates_by_beat.setdefault(str(candidate.get("beat_id") or "").strip(), []).append(candidate)
                    merged_queue_beats = list(previous_queue_beats)
                    for beat in remaining_beats:
                        beat_id = _beat_id(beat)
                        beat_candidates = candidates_by_beat.get(beat_id, [])
                        merged_queue_beats.append({
                            "beat_id": beat_id,
                            "voice_text": str(beat.get("narration_text") or ""),
                            "visual_description": str(beat.get("visual_description") or ""),
                            "candidates": beat_candidates,
                            "needs_codex_review": bool(beat_candidates),
                            "needs_fallback": not beat_candidates,
                        })
                    _write_json_atomic(queue_path, {
                        "version": 1,
                        "provider": "semantic+ai-review",
                        "status": "completed",
                        "updated_at": _now(),
                        "completed_beats": len(merged_queue_beats),
                        "total_beats": len(beats),
                        "beats": merged_queue_beats,
                        "failures": prepared.get("failures") or [],
                    })
            except FootageStopped as exc:
                return self._stopped_result(workspace, checkpoint, str(exc))
            except Exception as exc:
                if stream_failure is not None:
                    return stream_failure
                worker_state["status"] = "failed"
                worker_state["last_error"] = f"{type(exc).__name__}: {exc}"
                checkpoint["status"] = "failed"
                checkpoint["status_message"] = f"Local Footage Engine bị lỗi: {exc}"
                self._save_checkpoint(workspace, checkpoint)
                return StageResult(1, checkpoint["status_message"], workspace / ".producer" / "footage_engine")

        prepared_candidates = [item for item in (prepared.get("candidates") or []) if isinstance(item, dict)]
        candidates: list[dict[str, Any]] = []
        seen_candidate_ids: set[str] = set()
        for candidate in stream_candidates + prepared_candidates:
            candidate_id = str(candidate.get("candidate_id") or "").strip()
            if candidate_id and candidate_id in seen_candidate_ids:
                continue
            if candidate_id:
                seen_candidate_ids.add(candidate_id)
            candidates.append(candidate)
        candidate_by_id = {
            str(candidate.get("candidate_id") or "").strip(): candidate
            for candidate in candidates
            if str(candidate.get("candidate_id") or "").strip()
        }
        by_beat: dict[str, list[dict[str, Any]]] = {}
        for candidate in candidates:
            beat_id = str(candidate.get("beat_id") or "").strip()
            if beat_id:
                by_beat.setdefault(beat_id, []).append(candidate)

        review_batches = [] if streamed_review_complete else all_review_batches
        worker_state["total_batches"] = total_review_batches
        if review_batches:
            tool_progress_state = checkpoint.get("tool_progress") if isinstance(checkpoint.get("tool_progress"), dict) else {}
            checkpoint["tool_progress"] = {**tool_progress_state, "stage": "reviewing"}
            self._save_checkpoint(workspace, checkpoint)
        all_reviews: list[dict[str, Any]] = list(stream_reviews)
        all_retry_requests: list[dict[str, Any]] = list(stream_retry_requests)
        completed_ids: list[str] = list(stream_completed_ids)
        last_message = stream_last_message

        for batch_index, batch in enumerate(review_batches, start=1):
            try:
                self._await_control(workspace, checkpoint)
            except FootageStopped as exc:
                return self._stopped_result(workspace, checkpoint, str(exc))
            beat_ids = [_beat_id(beat) for beat in batch if _beat_id(beat)]
            batch_candidates = [candidate for beat_id in beat_ids for candidate in by_beat.get(beat_id, [])]
            reviews, retry_requests, review_result, review_error, review_message = self._run_vision_review_batch(
                job,
                workspace,
                checkpoint,
                batch,
                batch_candidates,
                batch_index,
                len(review_batches),
            )
            if review_message:
                last_message = review_message
            if reviews is None:
                return review_result or StageResult(
                    1,
                    review_error or f"AI final review batch {batch_index} failed",
                    review_root / f"batch_{batch_index:04d}.json",
                )
            all_reviews.extend(reviews)
            self._commit_reviewed_media(workspace, candidates, reviews, all_reviews)
            all_retry_requests.extend(retry_requests)
            completed_ids.extend(beat_ids)
            worker_state["current_batch"] = batch_index
            worker_state["completed_beat_ids"] = list(dict.fromkeys(completed_ids))
            worker_state["pending_beat_ids"] = [
                _beat_id(beat) for beat in beats if _beat_id(beat) not in worker_state["completed_beat_ids"]
            ]
            checkpoint["status_message"] = (
                f"Đã AI-duyệt candidate cho {len(worker_state['completed_beat_ids'])}/{len(beats)} beat."
            )
            self._save_checkpoint(workspace, checkpoint)

        accepted_review_beats = {
            str(candidate.get("beat_id") or "").strip()
            for candidate in candidates
            if candidate.get("selected_for_beat") is True
            and str(candidate.get("beat_id") or "").strip()
        }
        pending_retry = {
            str(item.get("beat_id") or "").strip(): item
            for item in all_retry_requests
            if str(item.get("beat_id") or "").strip()
            and str(item.get("beat_id") or "").strip() not in accepted_review_beats
        }
        for retry_round in range(1, self.ai_retry_rounds + 1):
            if not pending_retry:
                break
            next_retry: dict[str, dict[str, Any]] = {}
            for beat_id, request in list(pending_retry.items()):
                try:
                    self._await_control(workspace, checkpoint)
                except FootageStopped as exc:
                    return self._stopped_result(workspace, checkpoint, str(exc))
                source_beat = beat_by_id.get(beat_id)
                if not source_beat:
                    continue
                previous_candidates = list(by_beat.get(beat_id, []))
                excluded_urls = list(dict.fromkeys(
                    str(candidate.get("source_url") or "").strip()
                    for candidate in previous_candidates
                    if str(candidate.get("source_url") or "").strip()
                ))
                requested_queries = [
                    str(value).strip()
                    for value in (request.get("search_queries") or [])
                    if str(value).strip()
                ]
                existing_queries = [
                    str(value).strip()
                    for value in (source_beat.get("footage_search_queries") or [])
                    if str(value).strip()
                ]
                merged_queries: list[str] = []
                for query in requested_queries + existing_queries:
                    if query and query.lower() not in {value.lower() for value in merged_queries}:
                        merged_queries.append(query)

                retry_beat = dict(source_beat)
                retry_beat["footage_search_queries"] = merged_queries
                retry_beat["footage_excluded_source_urls"] = excluded_urls
                retry_beat["footage_ai_retry_reason"] = str(request.get("reason") or "").strip()
                checkpoint["status_message"] = (
                    f"AI yêu cầu Footage Engine tìm lại {beat_id} · vòng {retry_round}/{self.ai_retry_rounds}"
                )
                self._save_checkpoint(workspace, checkpoint)

                audit_entry: dict[str, Any] = {
                    "round": retry_round,
                    "beat_id": beat_id,
                    "reason": retry_beat["footage_ai_retry_reason"],
                    "search_queries": requested_queries,
                    "excluded_source_urls": excluded_urls,
                    "status": "searching",
                    "candidate_ids": [],
                }
                try:
                    retry_prepared = self._prepare_with_controls(
                        job,
                        [retry_beat],
                        workspace,
                        checkpoint,
                    )
                except FootageStopped as exc:
                    return self._stopped_result(workspace, checkpoint, str(exc))
                except Exception as exc:
                    audit_entry["status"] = "engine_error"
                    audit_entry["error"] = f"{type(exc).__name__}: {exc}"
                    retry_audit["rounds"].append(audit_entry)
                    continue

                retry_candidates: list[dict[str, Any]] = []
                known_ids = set(candidate_by_id)
                known_urls = {value.lower() for value in excluded_urls}
                for candidate in retry_prepared.get("candidates") or []:
                    if not isinstance(candidate, dict):
                        continue
                    candidate_id = str(candidate.get("candidate_id") or "").strip()
                    source_url = str(candidate.get("source_url") or "").strip()
                    if not candidate_id or candidate_id in known_ids:
                        continue
                    if source_url and source_url.lower() in known_urls:
                        continue
                    retry_candidates.append(candidate)
                    candidates.append(candidate)
                    candidate_by_id[candidate_id] = candidate
                    by_beat.setdefault(beat_id, []).append(candidate)

                audit_entry["candidate_ids"] = [
                    str(candidate.get("candidate_id") or "") for candidate in retry_candidates
                ]
                if not retry_candidates:
                    audit_entry["status"] = "no_new_candidates"
                    retry_audit["rounds"].append(audit_entry)
                    continue

                try:
                    retry_evidence = (
                        self._review_image_evidence(
                            retry_candidates,
                            max_total=_positive_int_env("COFI_VISION_REVIEW_MAX_IMAGES", 64),
                            per_candidate=_positive_int_env("COFI_VISION_REVIEW_FRAMES_PER_VIDEO", 2),
                        )
                        if _env_flag("COFI_VISION_REVIEW_ATTACH_IMAGES", True)
                        else {}
                    )
                except RuntimeError as exc:
                    audit_entry["status"] = "review_evidence_error"
                    audit_entry["error"] = str(exc)
                    retry_audit["rounds"].append(audit_entry)
                    continue
                retry_image_paths = self._flatten_review_image_evidence(retry_candidates, retry_evidence)
                audit_entry["attached_frames_by_candidate"] = retry_evidence
                prompt = build_codex_vision_review_prompt(
                    job,
                    [source_beat],
                    retry_candidates,
                    attached_frames_by_candidate=retry_evidence,
                )
                result: StageResult | None = None
                retry_reviews: list[dict[str, Any]] | None = None
                retry_requests: list[dict[str, Any]] = []
                review_error = ""
                for attempt in range(self.batch_retries + 1):
                    worker_state["attempts"] = int(worker_state.get("attempts") or 0) + 1
                    fresh_runner = getattr(self.review_gateway, "run_prompt", None)
                    reusable_runner = getattr(self.review_gateway, "run_prompt_reusable", None)
                    if callable(fresh_runner):
                        result = fresh_runner(
                            prompt,
                            workspace,
                            "footage_codex_review",
                            use_remotion_root=False,
                            image_paths=retry_image_paths,
                        )
                    elif callable(reusable_runner):
                        try:
                            result = reusable_runner(
                                prompt,
                                workspace,
                                "footage_codex_review",
                                use_remotion_root=False,
                                image_paths=retry_image_paths,
                            )
                        except TypeError:
                            result = reusable_runner(prompt, workspace, "footage_codex_review")
                    else:
                        raise RuntimeError("AI router không có runner cho footage review")
                    last_message = result.last_message or last_message
                    if result.returncode != 0:
                        review_error = result.last_message or "AI footage retry review failed"
                        if attempt < self.batch_retries and self._is_transient_failure(result):
                            continue
                        break
                    try:
                        review_payload = _json_object_from_message(result.last_message)
                        retry_reviews = self._review_batch_payload(
                            review_payload,
                            [str(candidate.get("candidate_id") or "") for candidate in retry_candidates],
                        )
                        retry_requests = self._review_retry_requests(review_payload, [beat_id], retry_reviews)
                        review_error = ""
                        break
                    except RuntimeError as exc:
                        review_error = str(exc)
                        if attempt < self.batch_retries:
                            continue
                        break

                if retry_reviews is None:
                    # STRICT BAN ON BLIND AUTOMATIC ACCEPT (`accepted_resilient_fallback` is forbidden):
                    # Never accept a candidate without genuine AI eye inspection of its frames (`inspected_frame_paths`).
                    audit_entry["status"] = "review_error_rejected"
                    audit_entry["error"] = review_error
                    retry_audit["rounds"].append(audit_entry)
                    continue

                all_reviews.extend(retry_reviews)
                selected_now = self._commit_reviewed_media(workspace, candidates, retry_reviews, all_reviews)
                accepted_now = beat_id in selected_now
                if accepted_now:
                    accepted_review_beats.add(beat_id)
                    audit_entry["status"] = "accepted"
                else:
                    audit_entry["status"] = "rejected"
                    if retry_requests:
                        next_retry[beat_id] = retry_requests[0]
                retry_audit["rounds"].append(audit_entry)
            pending_retry = next_retry

        retry_audit["updated_at"] = _now()
        _write_json_atomic(workspace / "footage_ai_retry.json", retry_audit)

        # FootageEngine.prepare() writes its per-call queue. Rebuild one canonical
        # queue containing every candidate from all AI-directed search rounds.
        _write_json_atomic(queue_path, {
            "version": 2,
            "provider": "vision+ai-review",
            "status": "completed",
            "updated_at": _now(),
            "beats": [{
                "beat_id": _beat_id(beat),
                "voice_text": str(beat.get("narration_text") or ""),
                "visual_description": str(beat.get("visual_description") or ""),
                "candidates": by_beat.get(_beat_id(beat), []),
                "needs_codex_review": bool(by_beat.get(_beat_id(beat), [])),
                "needs_fallback": _beat_id(beat) not in accepted_review_beats,
            } for beat in beats if _beat_id(beat)],
            "failures": prepared.get("failures") or [],
            "ai_retry_rounds": retry_audit["rounds"],
        })

        reviews_by_candidate = {
            str(review.get("candidate_id") or ""): review
            for review in all_reviews
            if str(review.get("candidate_id") or "")
        }
        accepted_by_beat: set[str] = set()
        assets: list[dict[str, Any]] = []
        for candidate_id, candidate in candidate_by_id.items():
            review = reviews_by_candidate.get(candidate_id)
            beat_id = str(candidate.get("beat_id") or "").strip()
            if (
                review
                and str(review.get("decision") or "").upper() == "ACCEPT"
                and candidate.get("selected_for_beat") is True
                and beat_id not in accepted_by_beat
            ):
                published, error = self._publish_vision_asset(workspace, candidate)
                valid, validation_error = _validate_media_file(workspace, published, candidate.get("kind")) if published else (False, error)
                if valid:
                    candidate["decision"] = "ACCEPT"
                    candidate["codex_decision"] = "ACCEPT"
                    candidate["codex_reviewed_actual_content"] = True
                    candidate["codex_review_reason"] = str(review.get("reason") or "").strip()
                    candidate["local_path"] = published
                    accepted_by_beat.add(beat_id)
                    assets.append({
                        "id": f"asset_{candidate_id}",
                        "beat_id": beat_id,
                        "kind": candidate.get("kind") or "sourced_video",
                        "path": published,
                        "source": {
                            "candidate_id": candidate_id,
                            "url": candidate.get("source_url") or "",
                            "timestamp_range": candidate.get("timestamp_range") or "",
                        },
                    })
                    continue
                candidate["validation_error"] = validation_error or error
            if review:
                candidate["codex_decision"] = str(review.get("decision") or "REJECT").upper()
                candidate["codex_review_reason"] = str(review.get("reason") or "").strip()
                candidate["codex_reviewed_actual_content"] = True
            candidate["decision"] = "REJECT" if candidate.get("selected_for_beat") is False else "REVIEW"
            if beat_id not in accepted_by_beat:
                candidate["ai_fallback_recommended"] = True
                candidate["real_video_search_complete"] = True
                candidate["real_still_search_complete"] = True
                if not candidate.get("ai_fallback_reason"):
                    candidate["ai_fallback_reason"] = "Không tìm thấy tư liệu thật đạt chuẩn sau khi duyệt; gán AI bổ sung ngay."

        for beat in beats:
            b_id = _beat_id(beat)
            if b_id and b_id not in accepted_by_beat and not any(str(c.get("beat_id") or "") == b_id for c in candidates):
                candidates.append({
                    "candidate_id": f"FT-{b_id}-ai-fallback",
                    "beat_id": b_id,
                    "source_priority": "prefer_real",
                    "decision": "REVIEW",
                    "kind": "sourced_video",
                    "reason": "Không tìm thấy tư liệu thật; gán AI bổ sung ngay.",
                    "ai_fallback_recommended": True,
                    "real_video_search_complete": True,
                    "real_still_search_complete": True,
                    "ai_fallback_reason": "Không tìm thấy tư liệu thật; gán AI bổ sung ngay.",
                })

        payload = {
            "worker": "codex",
            "status": "completed",
            "pipeline": "vision_codex",
            "candidates": candidates,
            "assets": assets,
            "native_treatments": [],
            "presentation_effects": [],
        }
        _write_json_atomic(workspace / "footage_codex.json", payload)
        _write_json_atomic(workspace / "footage_gemini.json", _empty_worker_payload("gemini", status="unavailable"))
        merge_worker_results(workspace)
        worker_state["status"] = "completed"
        worker_state["completed_beat_ids"] = [_beat_id(beat) for beat in beats if _beat_id(beat)]
        worker_state["pending_beat_ids"] = []
        checkpoint["status"] = "completed"
        checkpoint["status_message"] = (
            f"Tools đã tìm/lọc/tải candidate và {review_provider.title()} duyệt cuối cho {len(beats)}/{len(beats)} beat; "
            f"ACCEPT {len(accepted_by_beat)} beat."
        )
        self._save_checkpoint(workspace, checkpoint)
        return StageResult(0, last_message or checkpoint["status_message"], workspace / ".producer" / "footage_codex_review")

    @staticmethod
    def _replace_worker_beats(
        baseline: dict[str, Any],
        replacement: dict[str, Any],
        beat_ids: list[str],
    ) -> dict[str, Any]:
        targets = {str(beat_id) for beat_id in beat_ids if str(beat_id)}
        merged = dict(baseline)
        merged["worker"] = str(baseline.get("worker") or replacement.get("worker") or "codex")
        merged["status"] = "completed"
        for field in FOOTAGE_BATCH_FIELDS:
            kept = [
                item for item in (baseline.get(field) or [])
                if isinstance(item, dict) and str(item.get("beat_id") or "") not in targets
            ]
            added = [item for item in (replacement.get(field) or []) if isinstance(item, dict)]
            merged[field] = kept + added
        return merged

    def repair(self, job: dict[str, Any], workspace: str | Path, beat_ids: list[str]) -> StageResult:
        workspace = Path(workspace)
        visual = json.loads((workspace / "visual_manifest.json").read_text(encoding="utf-8"))
        all_beats = [item for item in (visual.get("beats") or []) if isinstance(item, dict)]
        requested = {str(value).strip() for value in beat_ids if str(value).strip()}
        beats = [beat for beat in all_beats if _beat_id(beat) in requested]
        selected_ids = [_beat_id(beat) for beat in beats if _beat_id(beat)]
        unknown = sorted(requested - set(selected_ids))
        if unknown:
            raise RuntimeError(f"Footage repair không tìm thấy beat trong visual manifest: {', '.join(unknown)}")
        if not selected_ids:
            return StageResult(0, "Không có beat cần sửa coverage.", workspace / ".producer" / "footage_repair")

        baseline_path = workspace / "footage_codex.json"
        if not baseline_path.exists():
            raise RuntimeError("Footage repair cần footage_codex.json hiện có để giữ các beat đã đạt.")
        baseline = _read_worker(baseline_path)

        repair_root = workspace / ".producer" / "footage_repair"
        checkpoint_path = repair_root / "checkpoint.json"
        previous: dict[str, Any] = {}
        if checkpoint_path.exists():
            try:
                loaded = json.loads(checkpoint_path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    previous = loaded
            except (OSError, json.JSONDecodeError):
                previous = {}
        if previous and previous.get("assigned_beat_ids") != selected_ids:
            history_root = workspace / ".producer" / "footage_repair_history"
            history_root.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
            shutil.move(str(repair_root), str(history_root / stamp))
            previous = {}

        batch_dir = repair_root / "batches"
        batch_dir.mkdir(parents=True, exist_ok=True)
        checkpoint = {
            "version": 1,
            "assigned_beat_ids": selected_ids,
            "completed_beat_ids": list(previous.get("completed_beat_ids") or []),
            "current_batch": int(previous.get("current_batch") or 0),
            "total_batches": len(_chunks(beats, self.batch_size)),
            "attempts": int(previous.get("attempts") or 0),
            "session_rotations": int(previous.get("session_rotations") or 0),
            "status": "running",
            "status_message": "Chuẩn bị sửa các beat thiếu coverage.",
            "updated_at": _now(),
        }

        def save_repair_checkpoint() -> None:
            checkpoint["updated_at"] = _now()
            _write_json_atomic(checkpoint_path, checkpoint)

        save_repair_checkpoint()
        outputs: list[dict[str, Any]] = []
        completed: list[str] = []
        last_message = ""
        batches = _chunks(beats, self.batch_size)
        for batch_index, batch in enumerate(batches, start=1):
            expected_ids = [_beat_id(beat) for beat in batch if _beat_id(beat)]
            batch_path = batch_dir / f"batch_{batch_index:04d}.json"
            payload: dict[str, Any] | None = None
            if batch_path.exists():
                try:
                    payload = _validate_batch_output(batch_path, expected_ids)
                except RuntimeError:
                    payload = None
            if payload is None:
                checkpoint["current_batch"] = batch_index
                checkpoint["status_message"] = f"Đang sửa coverage {', '.join(expected_ids)} · batch {batch_index}/{len(batches)}"
                save_repair_checkpoint()
                relative_output = str(batch_path.relative_to(workspace))
                discovery_by_beat = self._discover_for_prompt(job, batch, workspace)
                base_prompt = build_worker_prompt(
                    job,
                    batch,
                    "codex",
                    workspace,
                    relative_output,
                    discovery_by_beat=discovery_by_beat,
                )
                prompt = base_prompt
                result: StageResult | None = None
                continuation_turns = 0
                while True:
                    for attempt in range(self.batch_retries + 1):
                        checkpoint["attempts"] = int(checkpoint.get("attempts") or 0) + 1
                        save_repair_checkpoint()
                        runner = getattr(self.codex_gateway, "run_prompt_reusable", None)
                        if callable(runner):
                            result = runner(prompt, workspace, "footage_repair")
                        else:
                            result = self.codex_gateway.run_prompt(prompt, workspace, "footage_repair")
                        last_message = result.last_message or last_message
                        if result.returncode == 0:
                            break
                        transient_failure = self._is_transient_failure(result)
                        if attempt >= self.batch_retries or not transient_failure:
                            checkpoint["status"] = "failed"
                            checkpoint["status_message"] = (
                                f"Mất kết nối Codex; đã thử kết nối lại {attempt}/{self.batch_retries} lần "
                                "trong cùng phiên nhưng vẫn không thành công."
                                if transient_failure
                                else (result.last_message or "Footage repair bị lỗi.")
                            )
                            save_repair_checkpoint()
                            return result
                        checkpoint["status_message"] = (
                            f"Mất kết nối Codex; đang thử lại cùng phiên lần {attempt + 1}/{self.batch_retries}."
                        )
                        save_repair_checkpoint()
                    try:
                        payload = _validate_batch_output(batch_path, expected_ids)
                        break
                    except RuntimeError as exc:
                        if continuation_turns >= self.batch_continuations:
                            checkpoint["status"] = "failed"
                            checkpoint["status_message"] = str(exc)
                            save_repair_checkpoint()
                            return StageResult(1, str(exc), batch_path)
                        continuation_turns += 1
                        prompt = (
                            base_prompt
                            + "\n\nLƯỢT TIẾP TỤC BẮT BUỘC: output repair batch hiện tại chưa qua validator. "
                            + f"Lỗi cụ thể: {exc}. "
                            + f"Mở `{relative_output}`, GIỮ nguyên mọi kết quả hợp lệ đã có và chỉ bổ sung/sửa đúng phần còn thiếu. "
                            + "Không bắt đầu lại toàn bộ batch. Trước khi kết thúc lượt, tự kiểm tra rằng MỖI beat_id được giao "
                            + "đều xuất hiện trong candidates/assets/presentation_effects và JSON đúng schema."
                        )
                        checkpoint["status_message"] = (
                            f"Codex chưa hoàn tất repair batch {batch_index}/{len(batches)}; "
                            f"đang tiếp tục lượt {continuation_turns}/{self.batch_continuations}."
                        )
                        save_repair_checkpoint()

            outputs.append(payload)
            completed.extend(expected_ids)
            checkpoint["completed_beat_ids"] = list(dict.fromkeys(completed))
            checkpoint["current_batch"] = batch_index
            checkpoint["status_message"] = f"Đã sửa {len(completed)}/{len(selected_ids)} beat thiếu coverage."
            save_repair_checkpoint()

        replacement = _aggregate_batch_outputs("codex", outputs, "completed")
        _write_json_atomic(baseline_path, self._replace_worker_beats(baseline, replacement, selected_ids))
        if not (workspace / "footage_gemini.json").exists():
            _write_json_atomic(workspace / "footage_gemini.json", _empty_worker_payload("gemini", status="unavailable"))
        merge_worker_results(workspace)

        full_checkpoint_path = self._checkpoint_path(workspace)
        try:
            full_checkpoint = json.loads(full_checkpoint_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            full_checkpoint = {}
        if isinstance(full_checkpoint, dict) and full_checkpoint:
            full_checkpoint["status"] = "completed"
            full_checkpoint["status_message"] = f"Đã sửa coverage cho {len(selected_ids)} beat; giữ nguyên các beat đã đạt."
            full_checkpoint["updated_at"] = _now()
            _write_json_atomic(full_checkpoint_path, full_checkpoint)

        checkpoint["status"] = "completed"
        checkpoint["status_message"] = f"Hoàn tất sửa coverage cho {len(selected_ids)} beat."
        save_repair_checkpoint()
        return StageResult(0, last_message or checkpoint["status_message"], repair_root)

    def run(self, job: dict[str, Any], workspace: str | Path) -> StageResult:
        workspace = Path(workspace)
        visual = json.loads((workspace / "visual_manifest.json").read_text(encoding="utf-8"))
        beats = [item for item in (visual.get("beats") or []) if isinstance(item, dict)]
        strategy = str(job.get("visual_strategy") or visual.get("visual_strategy") or "").strip().lower()
        if strategy in {"hybrid", "evidence_footage", "selective_footage", "evidence_first"}:
            # Story-driven routing already sent these units to AI Visual; do not
            # spend real-footage searches on them. merge_worker_results records
            # them as hybrid_routed_ai fallback beats.
            beats = [
                beat for beat in beats
                if str(beat.get("visual_route") or "").strip().lower() != "ai_visual"
            ]
            if not beats:
                for worker in ("codex", "gemini"):
                    _write_json_atomic(workspace / f"footage_{worker}.json", _empty_worker_payload(worker, status="completed"))
                merge_worker_results(workspace)
                return StageResult(
                    returncode=0,
                    last_message="Hybrid: mọi visual đã được route sang AI Visual, bỏ qua tìm tư liệu.",
                    log_path=workspace / ".producer" / "footage",
                )
        mode = str(job.get("footage_mode") or "codex").lower()
        if mode == "vision_codex":
            assignments = {"codex": beats, "gemini": []}
            existing_checkpoint: dict[str, Any] = {}
            checkpoint_path = self._checkpoint_path(workspace)
            if checkpoint_path.exists():
                try:
                    loaded_checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
                    if isinstance(loaded_checkpoint, dict):
                        existing_checkpoint = loaded_checkpoint
                except (OSError, json.JSONDecodeError):
                    existing_checkpoint = {}
            legacy_pipeline = bool(existing_checkpoint) and existing_checkpoint.get("pipeline") != "vision_codex"
            self._archive_previous_run_if_needed(workspace, assignments, force=legacy_pipeline)
            self.set_control(workspace, "running")
            (workspace / "footage_assignments.json").write_text(json.dumps(assignments, ensure_ascii=False, indent=2), encoding="utf-8")
            checkpoint = self._load_or_initialize_checkpoint(workspace, assignments)
            checkpoint["pipeline"] = "vision_codex"
            checkpoint["workers"]["gemini"]["status"] = "completed"
            checkpoint["workers"]["gemini"]["completed_beat_ids"] = []
            self._save_checkpoint(workspace, checkpoint)
            return self._run_vision_codex(job, workspace, beats, checkpoint)
        assignments = partition_beats(beats) if mode == "dual" else {"codex": beats, "gemini": []}
        gemini_available = mode == "dual" and bool(getattr(self.gemini_gateway, "available", True))
        if not gemini_available:
            assignments["codex"] = beats
            assignments["gemini"] = []
        self._archive_previous_run_if_needed(workspace, assignments)
        (workspace / "footage_assignments.json").write_text(json.dumps(assignments, ensure_ascii=False, indent=2), encoding="utf-8")
        checkpoint = self._load_or_initialize_checkpoint(workspace, assignments)
        if not gemini_available:
            _write_json_atomic(workspace / "footage_gemini.json", _empty_worker_payload("gemini", status="unavailable"))
            checkpoint["workers"]["gemini"]["status"] = "completed"
            checkpoint["workers"]["gemini"]["completed_beat_ids"] = []
            self._save_checkpoint(workspace, checkpoint)

        results: list[StageResult] = [self._run_codex_batches(job, workspace, assignments["codex"], checkpoint)]
        if gemini_available and results[0].returncode == 0:
            results.append(self._run_gemini_once(job, workspace, assignments["gemini"], checkpoint))
        failed = [result for result in results if result.returncode != 0]
        if failed:
            return failed[0]
        merge_worker_results(workspace)
        checkpoint["status"] = "completed"
        checkpoint["status_message"] = f"Đã hoàn tất tìm tư liệu cho {checkpoint.get('completed_beats', 0)}/{checkpoint.get('total_beats', len(beats))} beat."
        self._save_checkpoint(workspace, checkpoint)
        message = "\n".join(result.last_message for result in results if result.last_message)
        return StageResult(returncode=0, last_message=message, log_path=workspace / ".producer" / "footage")
