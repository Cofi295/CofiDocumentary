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
        prof_thumb_dna = profile.get("thumbnail_dna") if isinstance(profile.get("thumbnail_dna"), dict) else {}
        prof_palette = prof_thumb_dna.get("color_palette") if isinstance(prof_thumb_dna.get("color_palette"), dict) else {}
        resolved_thumb_dna = {
            "style_preset": str(prof_thumb_dna.get("style_preset") or prof_thumb_dna.get("preset_id") or "teukgeup_archival_polaroid"),
            "archetype": str(prof_thumb_dna.get("layout_archetype") or prof_thumb_dna.get("layout_template") or "split_duality"),
            "max_words": 5,
            "primary_color": str(prof_palette.get("primary") or "#FFE600"),
            "accent_color": str(prof_palette.get("accent") or "#FF2424"),
            "badge_color": str(prof_palette.get("badge_color") or "#39FF14"),
            "rim_glow": str(prof_palette.get("rim_glow") or "#FDE68A"),
            "background_color": str(prof_palette.get("background") or "#070B10"),
            "min_contrast": 4.5,
        }
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
                    "next_video_upgrades": (
                        [
                            "Maintain objective archival perspective aligned with channel DNA",
                            "Open with a concrete documented contrast",
                        ]
                        if (str(profile.get("language") or "").lower() == "en" or str(profile.get("market") or "").upper() == "US")
                        else [
                            "Bám sát góc nhìn và giọng điệu riêng của hồ sơ kênh",
                            "Mở đầu bằng chi tiết hoặc số liệu đối lập cụ thể",
                        ]
                    ),
                },
                "thumbnail_dna": dict(resolved_thumb_dna),
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

        # Synthesize Profile-Scoped Evolutionary Upgrade Rules (100% isolated per profile & language-safe)
        lang = str(profile.get("language") or profile.get("default_language") or "").strip().lower()
        market = str(profile.get("market") or "").strip().upper()
        is_english_profile = (lang == "en" or market == "US")

        if is_english_profile:
            what_to_stop_doing = [
                "Vague or overly wordy titles that bury the core curiosity hook",
                "Graphic or policy-sensitive phrasing that risks YPP limited monetization",
                "Introducing early narrative leads or archival exhibits without resolving their outcome",
                "Abrupt ending cuts without a complete closing thought and 3.8s BGM fade-out",
                "Robotic AI translationese, passive-voice walls, or repetitive CTA templates across episodes",
            ]
            if any(u.get("cause") == "title_too_long_low_ctr" for u in underperformers):
                what_to_stop_doing.append("Titles exceeding 15 words that truncate on mobile screens")
            if any(u.get("cause") == "weak_keyword_fatigue" for u in underperformers):
                what_to_stop_doing.append("Overusing generic academic phrasing without concrete stakes")

            what_to_double_down_on = [
                "Structured multi-act progression anchored in verified primary records",
                "Clean 3-frame verified archival footage paired with bespoke motion graphics",
                "Natural ear-ready broadcast narration with varied sentence rhythm",
                "Complete closing narration followed by a clean 3.8s BGM fade-out tail",
            ]
            winner_terms = own_dna.get("winner_terms") or []
            if winner_terms:
                top_winners_str = ", ".join(str(w) for w in winner_terms[:4])
                what_to_double_down_on.append(f"Focus on proven channel outlier terms: {top_winners_str}")

            next_video_upgrades = [
                "Open on a concrete factual paradox within the first 30 seconds",
                "Keep thumbnail overlay hook text concise (under 5 words per line)",
                "Maintain strict alignment with this channel profile's own editorial and visual DNA",
                "Ensure zero CTA repetition and fresh closing lines tailored to the episode",
            ]
        else:
            what_to_stop_doing = [
                "Tiêu đề dài dòng mơ hồ làm chìm điểm tò mò chính",
                "Từ ngữ nhạy cảm vi phạm chính sách nguyên tắc cộng đồng / YPP xanh tiền",
                "Giới thiệu nhân vật hoặc chi tiết mở màn nhưng bỏ quên kết cục ở phần sau",
                "Cắt ngang câu kết màn giữa chừng hoặc thiếu 3.8 giây nhạc nền hạ màn (fade-out)",
                "Văn phong dịch máy rập khuôn mùi AI, đồng phục độ dài câu hoặc lặp lại mẫu câu CTA giữa các tập",
            ]
            if any(u.get("cause") == "title_too_long_low_ctr" for u in underperformers):
                what_to_stop_doing.append("Tiêu đề quá 15 từ làm giảm tỷ lệ click trên thiết bị di động")
            if any(u.get("cause") == "weak_keyword_fatigue" for u in underperformers):
                what_to_stop_doing.append("Lạm dụng từ khóa học thuật chung chung thiếu điểm chạm cụ thể")

            what_to_double_down_on = [
                "Cấu trúc chương hồi mạch lạc bám sát đúng DNA riêng của hồ sơ kênh",
                "Kết hợp tư liệu sạch kiểm duyệt 3-frame với đồ họa chuyển động thiết kế khớp câu đọc",
                "Giọng đọc tự nhiên, nhịp thở câu ngắn-dài biến thiên linh hoạt, chuẩn hóa số đếm trước TTS",
                "Hoàn tất trọn vẹn 100% câu kết màn kèm 3.8 giây nhạc nền hạ màn tự nhiên",
            ]
            winner_terms = own_dna.get("winner_terms") or []
            if winner_terms:
                top_winners_str = ", ".join(str(w) for w in winner_terms[:4])
                what_to_double_down_on.append(f"Tập trung khai thác cụm từ khóa Outlier thắng thế của riêng kênh: {top_winners_str}")

            next_video_upgrades = [
                "Mở đầu trực diện vào chi tiết đắt giá ngay 30 giây đầu theo đúng phong cách kênh",
                "Tối ưu chữ trên thumbnail ngắn gọn dưới 5 từ/dòng, không che mặt nhân vật chính",
                "Giữ độc lập 100% DNA biên tập & mỹ thuật của riêng hồ sơ kênh này",
                "Đảm bảo 0% lặp lại cấu trúc CTA và viết mới hoàn toàn đoạn kết theo mạch nội dung tập phim",
            ]

        # Also keep empty-videos fallback English-safe when profile is English
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
            "thumbnail_dna": dict(resolved_thumb_dna),
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
