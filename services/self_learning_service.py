"""
Continuous Self-Learning & Post-Mortem Engine for CofiDocumentary (Milestone 4).
Scans channel YouTube catalog and internal project history, classifies Outlier Winners vs Underperformers,
diagnoses root failure causes across failure dimensions, and synthesizes evolutionary upgrade rules.
"""

from __future__ import annotations

import copy
import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROFILES_FILE = ROOT / "data" / "channel_profiles.json"
DEFAULT_JOBS_DIR = ROOT / "data" / "jobs"
RADAR_DB_PATH = Path(r"B:\ALL_TOOLS\CofiRadar\data\cofi-radar.db")

_file_lock = threading.RLock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SelfLearningService:
    def __init__(
        self,
        profiles_file: Path | str | None = None,
        jobs_dir: Path | str | None = None,
        radar_db: Path | str | None = None,
        profile_service: Any = None,
    ):
        self.profiles_file = Path(profiles_file) if profiles_file else DEFAULT_PROFILES_FILE
        self.jobs_dir = Path(jobs_dir) if jobs_dir else DEFAULT_JOBS_DIR
        self.radar_db = Path(radar_db) if radar_db else RADAR_DB_PATH
        self.profile_service = profile_service

    def get_profile(self, profile_id: str) -> dict[str, Any]:
        """Fetch profile dict by profile ID."""
        if self.profile_service and hasattr(self.profile_service, "get_profile"):
            try:
                return self.profile_service.get_profile(profile_id)
            except Exception:
                pass

        with _file_lock:
            if not self.profiles_file.exists():
                raise KeyError(f"Profile {profile_id} not found: storage file missing")
            data = json.loads(self.profiles_file.read_text(encoding="utf-8"))
            for p in data.get("profiles", []):
                if p.get("id") == profile_id:
                    return p
        raise KeyError(f"Profile {profile_id} not found")

    def save_profile(self, profile: dict[str, Any]) -> None:
        """Persist profile back into data/channel_profiles.json atomically."""
        profile_id = profile.get("id")
        if not profile_id:
            raise ValueError("Profile missing 'id'")

        if self.profile_service and hasattr(self.profile_service, "update_profile"):
            try:
                self.profile_service.update_profile(profile_id, profile)
                return
            except Exception:
                pass

        with _file_lock:
            if not self.profiles_file.exists():
                profiles = [profile]
            else:
                data = json.loads(self.profiles_file.read_text(encoding="utf-8"))
                profiles = data.get("profiles", [])
                updated = False
                for i, p in enumerate(profiles):
                    if p.get("id") == profile_id:
                        profiles[i] = profile
                        updated = True
                        break
                if not updated:
                    profiles.append(profile)

            tmp_path = self.profiles_file.with_suffix(".tmp")
            tmp_path.write_text(json.dumps({"profiles": profiles}, indent=2, ensure_ascii=False), encoding="utf-8")
            tmp_path.replace(self.profiles_file)

    def collect_channel_videos(self, profile: dict[str, Any]) -> list[dict[str, Any]]:
        """Collect video history from own_channel DNA, radar db, and internal jobs."""
        videos: list[dict[str, Any]] = []
        seen_ids: set[str] = set()

        # 1. From own_channel.dna.winner_titles
        own_channel = profile.get("own_channel") or {}
        dna = own_channel.get("dna") or {}
        winner_titles = dna.get("winner_titles") or []
        for i, wt in enumerate(winner_titles):
            vid = f"wt_{i+1}"
            if isinstance(wt, dict):
                v_title = str(wt.get("title") or "").strip()
                v_views = int(wt.get("views") or wt.get("view_count") or 50000)
                is_breakout = bool(wt.get("is_breakout") or wt.get("outlier_score", 0) >= 2.0)
                vid = str(wt.get("id") or wt.get("video_id") or vid)
            else:
                v_title = str(wt).strip()
                v_views = 50000
                is_breakout = True
            if v_title and vid not in seen_ids:
                seen_ids.add(vid)
                videos.append({"id": vid, "title": v_title, "views": v_views, "is_breakout": is_breakout})

        # 2. From own_channel.videos
        channel_videos = own_channel.get("videos") or []
        for cv in channel_videos:
            if isinstance(cv, dict) and cv.get("title"):
                vid = str(cv.get("id") or cv.get("video_id") or f"cv_{len(seen_ids)+1}")
                if vid not in seen_ids:
                    seen_ids.add(vid)
                    videos.append({
                        "id": vid,
                        "title": str(cv["title"]).strip(),
                        "views": int(cv.get("views") or cv.get("view_count") or 0),
                        "is_breakout": bool(cv.get("is_breakout")),
                    })

        # 3. From internal jobs
        profile_id = profile.get("id")
        if profile_id and self.jobs_dir.exists():
            for job_dir in self.jobs_dir.iterdir():
                if not job_dir.is_dir():
                    continue
                job_file = job_dir / "job.json"
                if not job_file.exists():
                    continue
                try:
                    job = json.loads(job_file.read_text(encoding="utf-8"))
                    job_pid = job.get("channel_profile_id") or job.get("channel_profile_snapshot", {}).get("id")
                    if job_pid == profile_id and job.get("title"):
                        vid = job.get("id") or job_dir.name
                        if vid not in seen_ids:
                            seen_ids.add(vid)
                            videos.append({
                                "id": vid,
                                "title": str(job["title"]).strip(),
                                "views": int(job.get("views") or 0),
                                "is_breakout": False,
                            })
                except Exception:
                    continue

        return videos

    def analyze_post_mortem(self, videos: list[dict[str, Any]], profile: dict[str, Any]) -> dict[str, Any]:
        """
        Execute Win/Loss classification and diagnostic post-mortem.
        Compatible with E2E opaque-box reference specification.
        """
        profile_id = profile.get("id", "channel_default")
        if not videos:
            return {
                "status": "success",
                "profile_id": profile_id,
                "analyzed_videos_count": 0,
                "winners": [],
                "underperformers": [],
                "diagnostics": [],
                "upgrade_rules": {
                    "what_to_stop_doing": [],
                    "what_to_double_down_on": [],
                    "next_video_upgrades": [
                        "Khóa chặt góc nhìn điều tra khách quan",
                        "Mở đầu bằng số liệu chênh lệch",
                    ],
                },
                "thumbnail_dna": {
                    "archetype": "broadcast_left_heavy",
                    "max_words": 5,
                    "accent_color": "#38BDF8",
                },
                "seo_dna": {
                    "min_tags": 8,
                    "core_winner_tags": [],
                },
                "title_winner_patterns": [
                    "investigative_hook_keyword",
                    "quantitative_metric_formula",
                ],
            }

        views = [int(v.get("views") or 0) for v in videos]
        sorted_views = sorted(views)
        median_views = sorted_views[len(sorted_views) // 2] if views else 1
        effective_median = max(median_views, 1)

        winners: list[dict[str, Any]] = []
        underperformers: list[dict[str, Any]] = []
        diagnostics: list[str] = []

        own_dna = profile.get("own_channel", {}).get("dna", {})
        weak_terms = [str(wt).lower() for wt in own_dna.get("weak_terms", [])]

        for v in videos:
            v_views = int(v.get("views") or 0)
            v_id = str(v.get("id") or v.get("video_id") or "v")
            v_title = str(v.get("title") or "")
            outlier_multiplier = v_views / effective_median

            if outlier_multiplier >= 2.0 or v.get("is_breakout"):
                winners.append({
                    "video_id": v_id,
                    "title": v_title,
                    "views": v_views,
                    "multiplier": round(outlier_multiplier, 2),
                })
            elif outlier_multiplier < 0.6:
                cause = "weak_hook_or_niche_deviation"
                if len(v_title.split()) > 15:
                    cause = "title_too_long_low_ctr"
                elif any(wt in v_title.lower() for wt in weak_terms if wt):
                    cause = "weak_keyword_fatigue"

                underperformers.append({
                    "video_id": v_id,
                    "title": v_title,
                    "views": v_views,
                    "multiplier": round(outlier_multiplier, 2),
                    "cause": cause,
                })
                diagnostics.append(f"Video '{v_title}' thua vì {cause}")

        # Synthesize Evolutionary Upgrade Rules
        what_to_stop_doing = [
            "Tiêu đề dài dòng mơ hồ",
            "Mô tả bạo lực trực diện vi phạm YPP",
            "Cấm bỏ quên nhân vật mở màn (vi phạm nguyên tắc Chiếc súng của Chekhov — nhắc thương nhân họ Ngụy ở đầu nhưng bỏ bẵng kết cục)",
            "Cấm gọi người 58–62 tuổi (50–65 tuổi) là 'ông bà già / cụ già' (노부부 / 노인) gây gượng gạo văn hóa Hàn Quốc",
            "Cấm cắt ngang câu kết màn (closing narration) giữa chừng hoặc kết thúc cụt ngủn không có nhạc nền fade-out",
            "Cấm dùng tông giọng TTS quá căng/gắt gây mệt tai ('목소리 톤이 넘 강팔라 피곤해'), đọc sai số đếm ('19년' đọc thành '열아홉 년'), hoặc để TTS cắt đôi số có dấu phẩy ('2,000') và kéo dài khoảng nghỉ giữa câu >0.5s làm nhịp đọc bị chậm",
            "Cấm tuyệt đối dùng Regex / Find-and-Replace xóa hoặc thay chủ ngữ hàng loạt trong kịch bản tiếng Hàn gây lỗi định ngữ gắn nhầm vào đồ vật ('서른한 살이 된 동영상 플랫폼', '무릎을 꿇은 판결문 복사본') hoặc đánh tráo chủ thể hung thủ - nạn nhân",
            "Cấm dùng giao diện Cyber-Finance HUD tối màu cho kênh True Crime Hình Sự ('특급수배록') hoặc đặt sai bố cục 2 ảnh phụ Polaroid góc trái trên của Thumbnail DNA",
            "Cấm viết chuỗi số phiên âm Hangul dài ngoằng ('천구백팔십이년생', '오백팔십일억 칠천오백만 위안', '백구십육 개', '십사점육 퍼센트', '구조 원') trực tiếp vào script.md và phụ đề gây khó đọc và làm TTS ngắt sai ('백구... 십육 개')",
        ]
        if any(u.get("cause") == "title_too_long_low_ctr" for u in underperformers):
            what_to_stop_doing.append("Tiêu đề quá 15 từ làm giảm tỷ lệ click trên thiết bị di động")
        if any(u.get("cause") == "weak_keyword_fatigue" for u in underperformers):
            what_to_stop_doing.append("Lạm dụng từ khóa học thuật chung chung thiếu điểm nổ cảm xúc")

        what_to_double_down_on = [
            "Cấu trúc 5 hồi kịch tính",
            "Bản đồ 2.5D vệ tinh đối chiếu hiện trường",
            "Nguyên tắc Chiếc súng của Chekhov: Mọi nhân vật/manh mối mở màn đều có kết cục rõ ràng (hoặc 1–2 câu tóm lược nhẹ nhàng nếu nhạy cảm)",
            "Tông giọng trầm ấm, đầm, đều đặn chuẩn kể chuyện đêm khuya (K1 - Trầm Sâu Đêm Khuya SBS Style / K1 - Điềm Tĩnh) + chuẩn hóa số đếm Hán-Hàn (십구 년, 오십대)",
            "Hoàn tất trọn vẹn 100% câu chào kết màn + để dư 3.5–5 giây (3.8s) nhạc nền hạ màn (fade-out) tự nhiên",
        ]
        winner_terms = own_dna.get("winner_terms") or []
        if winner_terms:
            top_winners_str = ", ".join(str(w) for w in winner_terms[:4])
            what_to_double_down_on.append(f"Tập trung khai thác cụm từ khóa Outlier thắng thế: {top_winners_str}")

        next_video_upgrades = [
            "Mở đầu bằng nghịch lý 30 giây",
            "Tối ưu text thumbnail dưới 5 từ",
            "Khóa chặt góc nhìn điều tra khách quan",
            "Mở đầu bằng số liệu chênh lệch",
            "Tăng mật độ HUD 2.5D",
            "[Checklist Kịch bản] Mọi nhân vật xuất hiện ở phần đầu đã có kết cục rõ ràng (Chekhov's Gun) + xưng hô trung tính chuẩn văn hóa Hàn ('여관 주인 부부', '50대 후반 부부')",
            "[Checklist Giọng đọc] Tông giọng trầm ấm êm tai chuẩn đêm khuya + rà soát số đếm/năm tháng/danh từ riêng (19년=십구 년) không đọc vấp",
            "[Checklist Phần kết] Câu thoại cuối cùng hoàn tất trọn vẹn 100% + có 3–5 giây (3.8s) nhạc nền hạ màn fade-out",
            "[Checklist Ngữ pháp Hàn] Cấm dùng Regex xóa/thay chủ ngữ; kiểm tra 100% sự tương hợp Định ngữ - Danh từ trung tâm và phân biệt chuẩn chủ thể Nạn nhân vs Hung thủ",
            "[Checklist Nhịp độ Voice] Chuẩn hóa số có dấu phẩy sang Hangul (2,000킬로미터 -> 이천 킬로미터) trước TTS + gọt khoảng nghỉ giữa câu (0.285s/0.185s) đạt chuẩn 255–270 SPM đài SBS",
        ]

        # Idempotent deduplication preserving order
        what_to_stop_doing = list(dict.fromkeys(what_to_stop_doing))
        what_to_double_down_on = list(dict.fromkeys(what_to_double_down_on))
        next_video_upgrades = list(dict.fromkeys(next_video_upgrades))

        upgrade_rules = {
            "what_to_stop_doing": what_to_stop_doing,
            "what_to_double_down_on": what_to_double_down_on,
            "next_video_upgrades": next_video_upgrades,
        }

        return {
            "status": "success",
            "profile_id": profile_id,
            "analyzed_videos_count": len(videos),
            "median_views": median_views,
            "last_analysis": _now(),
            "winners": winners,
            "underperformers": underperformers,
            "diagnostics": diagnostics,
            "upgrade_rules": upgrade_rules,
            "thumbnail_dna": {
                "archetype": "broadcast_left_heavy",
                "max_words": 5,
                "accent_color": "#38BDF8",
                "min_contrast": 4.5,
            },
            "seo_dna": {
                "min_tags": 8,
                "core_winner_tags": [str(t) for t in winner_terms[:8]],
                "include_timestamp_chapters": True,
            },
            "title_winner_patterns": [
                "investigative_hook_keyword",
                "quantitative_metric_formula",
                "crisis_paradox_structure",
            ],
        }

    def run_self_learning(self, profile_id: str, save_to_profile: bool = True) -> dict[str, Any]:
        """Main service entrypoint running self-learning analysis and saving to profile."""
        profile = self.get_profile(profile_id)
        videos = self.collect_channel_videos(profile)
        report = self.analyze_post_mortem(videos, profile)

        if save_to_profile:
            profile["self_learning_memory"] = report
            self.save_profile(profile)

        return report

    def get_self_learning(self, profile_id: str) -> dict[str, Any]:
        """Fetch existing self-learning memory or run fresh analysis if empty."""
        profile = self.get_profile(profile_id)
        existing = profile.get("self_learning_memory")
        if (
            existing
            and isinstance(existing, dict)
            and isinstance(existing.get("upgrade_rules"), dict)
            and existing.get("upgrade_rules", {}).get("next_video_upgrades")
            and "diagnostics" in existing
        ):
            res = dict(existing)
            res.setdefault("status", "success")
            res.setdefault("profile_id", profile_id)
            res.setdefault("winners", [])
            res.setdefault("underperformers", [])
            res.setdefault("diagnostics", [])
            return res
        return self.run_self_learning(profile_id, save_to_profile=True)

    def inject_self_learning_rules(self, profile_id: str, creative_brief: dict[str, Any]) -> dict[str, Any]:
        """Inject synthesized evolutionary rules into project creative brief."""
        report = self.get_self_learning(profile_id)
        upgrades = report.get("upgrade_rules", {}).get("next_video_upgrades", [])
        brief = dict(creative_brief)
        brief["self_learning_injected_rules"] = upgrades
        return brief
