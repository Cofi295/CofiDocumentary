"""
Channel-DNA Pre-Flight Service for CofiDocumentary (Milestone 4).
Queries real YouTube channel DNA (winner_terms, weak_terms, outlier multipliers, winner_titles)
and internal job catalogs to validate Topics, Titles, Thumbnails (3+ variants), and SEO packages.
"""

from __future__ import annotations

import copy
import json
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROFILES_FILE = ROOT / "data" / "channel_profiles.json"
DEFAULT_JOBS_DIR = ROOT / "data" / "jobs"
_file_lock = threading.RLock()

from services.case_similarity import check_case_similarity, extract_case_anchors_and_entities


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class PreflightService:
    def __init__(
        self,
        profiles_file: Path | str | None = None,
        jobs_dir: Path | str | None = None,
        profile_service: Any = None,
    ):
        self.profiles_file = Path(profiles_file) if profiles_file else DEFAULT_PROFILES_FILE
        self.jobs_dir = Path(jobs_dir) if jobs_dir else DEFAULT_JOBS_DIR
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

    def get_channel_history_titles(self, profile_id: str) -> list[str]:
        """Collect all historical published video titles for a channel profile."""
        titles: list[str] = []
        try:
            profile = self.get_profile(profile_id)
        except Exception:
            profile = {}

        # 1. From profile own_channel DNA
        own_channel = profile.get("own_channel") or {}
        dna = own_channel.get("dna") or {}
        winner_titles = dna.get("winner_titles") or []
        for wt in winner_titles:
            if isinstance(wt, str) and wt.strip():
                titles.append(wt.strip())
            elif isinstance(wt, dict) and wt.get("title"):
                titles.append(str(wt["title"]).strip())

        # 2. From profile videos list if present
        videos = own_channel.get("videos") or []
        for v in videos:
            if isinstance(v, dict) and v.get("title"):
                titles.append(str(v["title"]).strip())

        # 3. From internal job catalog
        if self.jobs_dir.exists():
            for job_dir in self.jobs_dir.iterdir():
                if not job_dir.is_dir():
                    continue
                job_file = job_dir / "job.json"
                if not job_file.exists():
                    continue
                try:
                    job_data = json.loads(job_file.read_text(encoding="utf-8"))
                    job_pid = job_data.get("channel_profile_id") or job_data.get("channel_profile_snapshot", {}).get("id")
                    if job_pid == profile_id and job_data.get("title"):
                        titles.append(str(job_data["title"]).strip())
                except Exception:
                    continue

        # Deduplicate while preserving order
        return list(dict.fromkeys([t for t in titles if t]))

    def check(
        self,
        profile: dict[str, Any],
        stage: str,
        input_data: dict[str, Any],
        history_titles: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Execute pre-flight check logic for topics, titles, thumbnails, and SEO.
        Compatible with E2E opaque-box reference specification.
        """
        forbidden_raw = profile.get("forbidden_topics") or profile.get("editorial_dna", {}).get("forbidden_topics") or ""
        allowed_raw = profile.get("allowed_topics") or profile.get("editorial_dna", {}).get("allowed_topics") or ""

        if isinstance(forbidden_raw, list):
            forbidden = [str(t).strip().lower() for t in forbidden_raw if str(t).strip()]
        else:
            forbidden = [t.strip().lower() for t in str(forbidden_raw).split(",") if t.strip()]

        if isinstance(allowed_raw, list):
            allowed = [str(t).strip().lower() for t in allowed_raw if str(t).strip()]
        else:
            allowed = [t.strip().lower() for t in str(allowed_raw).split(",") if t.strip()]

        hist_list = history_titles if history_titles is not None else []
        duplicate_risk = False
        passed = True
        recommendations: list[str] = []
        matched_patterns: list[str] = []
        details: dict[str, Any] = {}

        channel_history_check: dict[str, Any] = {
            "passed": True,
            "status": "clean",
            "checked_count": 0,
            "matches": [],
            "duplicate_found": False,
        }
        profile_memory_check: dict[str, Any] = {
            "passed": True,
            "status": "clean",
            "checked_count": 0,
            "matches": [],
            "duplicate_found": False,
            "matched_job_id": None,
        }

        if stage in {"topic", "title"}:
            raw_title = str(input_data.get("title") or "").strip()
            raw_topic = str(input_data.get("topic") or raw_title).strip()
            cand_text = f"{raw_title} {raw_topic}".strip()

            title = raw_title.lower()
            topic = raw_topic.lower()

            # ------------------------------------------------------------------
            # PASS 1: YouTube Channel Video Check (channel_history_check)
            # ------------------------------------------------------------------
            video_titles: list[str] = []
            own_ch = profile.get("own_channel") or {}
            for v in (own_ch.get("videos") or []):
                if isinstance(v, dict) and v.get("title"):
                    video_titles.append(str(v["title"]).strip())
            dna_wt = (own_ch.get("dna") or {}).get("winner_titles") or []
            for wt in dna_wt:
                if isinstance(wt, str) and wt.strip():
                    video_titles.append(wt.strip())
                elif isinstance(wt, dict) and wt.get("title"):
                    video_titles.append(str(wt["title"]).strip())
            for ht in hist_list:
                if ht and ht not in video_titles:
                    video_titles.append(ht)

            video_titles = list(dict.fromkeys([vt for vt in video_titles if vt]))
            channel_history_matches: list[dict[str, Any]] = []

            for vt in video_titles:
                is_dup, reason, score = check_case_similarity(cand_text, vt)
                if not is_dup and title:
                    clean_vt = vt.lower()
                    if (title and clean_vt == title) or (topic and topic in clean_vt) or (title and title in clean_vt and len(title) >= 8):
                        is_dup = True
                        reason = "Trùng khớp nguyên văn tiêu đề video đã xuất bản trên kênh"
                        score = 0.95
                if is_dup:
                    channel_history_matches.append({
                        "video_title": vt,
                        "reason": reason,
                        "score": score,
                    })

            channel_history_check = {
                "passed": len(channel_history_matches) == 0,
                "status": "clean" if not channel_history_matches else "duplicate_detected",
                "checked_count": len(video_titles),
                "matches": channel_history_matches,
                "duplicate_found": len(channel_history_matches) > 0,
            }

            # ------------------------------------------------------------------
            # PASS 2: Profile Produced-Topic Memory Check (profile_memory_check)
            # ------------------------------------------------------------------
            pid = str(profile.get("id") or "")
            topic_memories: list[dict[str, Any]] = []
            if profile.get("topic_memory"):
                topic_memories.extend(list(profile.get("topic_memory") or []))
            elif self.profile_service and hasattr(self.profile_service, "get_topic_memory") and pid:
                try:
                    topic_memories.extend(self.profile_service.get_topic_memory(pid))
                except Exception:
                    pass

            if self.jobs_dir.exists():
                for jdir in self.jobs_dir.iterdir():
                    if not jdir.is_dir():
                        continue
                    jfile = jdir / "job.json"
                    if not jfile.is_file():
                        continue
                    try:
                        jdata = json.loads(jfile.read_text(encoding="utf-8"))
                        job_pid = str(jdata.get("channel_profile_id") or jdata.get("channel_profile_snapshot", {}).get("id") or "")
                        if job_pid == pid:
                            jid = str(jdata.get("id") or jdir.name)
                            jtitle = str(jdata.get("title") or "")
                            jtopic = str(jdata.get("topic") or jtitle)
                            if not any(str(m.get("job_id")) == jid for m in topic_memories):
                                topic_memories.append({
                                    "job_id": jid,
                                    "title": jtitle,
                                    "topic": jtopic,
                                    "source": "job",
                                })
                    except Exception:
                        continue

            profile_memory_matches: list[dict[str, Any]] = []

            for entry in topic_memories:
                m_title = str(entry.get("title") or "")
                m_topic = str(entry.get("topic") or m_title)
                m_tags = list(entry.get("tags") or entry.get("anchors") or [])
                is_dup, reason, score = check_case_similarity(
                    cand_text,
                    m_title,
                    target_topic=m_topic,
                    target_entities=m_tags,
                )
                if not is_dup and title:
                    clean_m = m_title.lower()
                    if (title and clean_m == title) or (title and title in clean_m and len(title) >= 8):
                        is_dup = True
                        reason = "Trùng khớp nguyên văn đề tài đã lưu trong hồ sơ kênh"
                        score = 0.95
                if is_dup:
                    profile_memory_matches.append({
                        "job_id": str(entry.get("job_id") or ""),
                        "title": m_title,
                        "topic": m_topic,
                        "reason": reason,
                        "score": score,
                    })

            profile_memory_check = {
                "passed": len(profile_memory_matches) == 0,
                "status": "clean" if not profile_memory_matches else "duplicate_detected",
                "checked_count": len(topic_memories),
                "matches": profile_memory_matches,
                "duplicate_found": len(profile_memory_matches) > 0,
                "matched_job_id": profile_memory_matches[0]["job_id"] if profile_memory_matches else None,
            }

            details["channel_history_check"] = channel_history_check
            details["profile_memory_check"] = profile_memory_check

            if channel_history_matches or profile_memory_matches:
                duplicate_risk = True
                passed = False
                for m in channel_history_matches:
                    recommendations.append(f"Pass 1 (Kênh YouTube): Trùng lặp video đã xuất bản '{m['video_title']}' ({m['reason']})")
                for m in profile_memory_matches:
                    job_str = f" [Job {m['job_id']}]" if m.get("job_id") else ""
                    recommendations.append(f"Pass 2 (Bộ nhớ Hồ sơ): Trùng lặp đề tài đã sản xuất{job_str}: '{m['title']}' ({m['reason']})")

            # 2. Check forbidden topics
            for fb in forbidden:
                if (fb and fb in title) or (fb and fb in topic):
                    passed = False
                    recommendations.append(f"Chủ đề vi phạm điều cấm của DNA kênh: '{fb}'")

            # 3. Check winner patterns and hook terms
            winner_keywords = ["đại án", "hạ tầng", "vỏ bọc", "giải phẫu", "bê bối", "sụp đổ", "lật tẩy", "hồ sơ mật"]
            if any(k in title for k in ["đại án", "hạ tầng", "vỏ bọc"]):
                matched_patterns.append("investigative_hook_keyword")

            # Quantitative metric pattern in title
            if re.search(r"\d+[\.,]?\d*\s*(tỷ|triệu|km|tấn|năm|%|억|만|ton|billion|m³)", title):
                matched_patterns.append("quantitative_metric_formula")

            # Cross-check channel winner terms from own_channel.dna
            own_dna = profile.get("own_channel", {}).get("dna", {})
            winner_terms = own_dna.get("winner_terms") or []
            matched_winner_terms = [wt for wt in winner_terms if str(wt).lower() in title or str(wt).lower() in topic]
            if matched_winner_terms:
                matched_patterns.append("winner_dna_term_match")
                details["matched_winner_terms"] = matched_winner_terms

            # Weak terms check
            weak_terms = own_dna.get("weak_terms") or []
            flagged_weak_terms = [wt for wt in weak_terms if str(wt).lower() in title or str(wt).lower() in topic]
            if flagged_weak_terms:
                recommendations.append(f"Cảnh báo: Tiêu đề chứa từ khóa kém hiệu quả: {', '.join(flagged_weak_terms)}")
                details["flagged_weak_terms"] = flagged_weak_terms

            # SEO Keyword DNA check
            seo_dna = profile.get("seo_keyword_dna") or {}
            primary_kw = str(seo_dna.get("primary_title_keyword") or "").strip()
            if primary_kw:
                if primary_kw.lower() in title or primary_kw.lower() in topic:
                    matched_patterns.append("primary_seo_keyword_dna_match")
                    details["primary_seo_keyword_dna_matched"] = True
                else:
                    details["primary_seo_keyword_dna_matched"] = False
                    recommendations.append(f"Khuyến nghị chèn từ khóa SEO chủ lực của kênh: '{primary_kw}'")

            details["title_word_count"] = len(title.split()) if title else 0

        elif stage == "thumbnail":
            variants = input_data.get("variants") or []
            if len(variants) < 3:
                passed = False
                recommendations.append("Cần tạo tối thiểu 3 biến thể thumbnail để A/B test.")

            text_overlay = str(input_data.get("text_overlay") or input_data.get("overlay_text") or "").strip()
            word_count = len(text_overlay.split()) if text_overlay else 0
            details["overlay_word_count"] = word_count
            if word_count > 6:
                recommendations.append("Text overlay quá dài (> 6 từ), có thể giảm CTR trên mobile.")

            archetype = input_data.get("archetype")
            if archetype:
                details["archetype"] = archetype
                matched_patterns.append(f"archetype_{archetype}")

        elif stage == "seo":
            tags = input_data.get("tags") or []
            details["tags_count"] = len(tags)
            if len(tags) < 5:
                recommendations.append("Bổ sung tối thiểu 5 tags liên quan đến DNA kênh.")

            seo_dna = profile.get("seo_keyword_dna") or {}
            primary_kw = str(seo_dna.get("primary_title_keyword") or "").strip()
            title_val = str(input_data.get("recommended_title") or input_data.get("title") or "").strip().lower()
            if primary_kw:
                if primary_kw.lower() in title_val:
                    matched_patterns.append("seo_primary_keyword_matched")
                    details["seo_primary_keyword_matched"] = True
                else:
                    details["seo_primary_keyword_matched"] = False
                    recommendations.append(f"Tiêu đề SEO chưa chứa từ khóa chủ lực của kênh: '{primary_kw}'")

            mand_hashtags = seo_dna.get("mandatory_hashtags") or []
            hashtags = [str(h).lower() for h in (input_data.get("hashtags") or [])]
            missing_hashtags = [h for h in mand_hashtags if str(h).lower() not in hashtags]
            if missing_hashtags:
                recommendations.append(f"Thiếu hashtag bắt buộc của kênh: {', '.join(missing_hashtags)}")
                details["missing_mandatory_hashtags"] = missing_hashtags

            own_dna = profile.get("own_channel", {}).get("dna", {})
            winner_terms = own_dna.get("winner_terms") or []
            covered_winners = [t for t in tags if str(t).lower() in [wt.lower() for wt in winner_terms]]
            if covered_winners:
                matched_patterns.append("seo_winner_terms_covered")
                details["covered_winner_terms"] = covered_winners

        # Deduplicate recommendations and matched patterns
        recommendations = list(dict.fromkeys(recommendations))
        matched_patterns = list(dict.fromkeys(matched_patterns))

        return {
            "status": "ok" if passed else "warning",
            "channel_history_check": channel_history_check,
            "profile_memory_check": profile_memory_check,
            "preflight_summary": {
                "passed": passed,
                "stage": stage,
                "duplicate_risk": duplicate_risk,
                "winner_patterns_matched": matched_patterns,
                "recommendations": recommendations,
                "channel_history_check": channel_history_check,
                "profile_memory_check": profile_memory_check,
                "details": details,
            },
        }

    def run_preflight_check(
        self,
        profile_or_id: str | dict[str, Any],
        stage: str = "topic",
        input_data: dict[str, Any] | None = None,
        history_titles: list[str] | None = None,
    ) -> dict[str, Any]:
        """Main service entrypoint accepting profile ID or dict."""
        if isinstance(profile_or_id, str):
            profile = self.get_profile(profile_or_id)
            profile_id = profile_or_id
        else:
            profile = profile_or_id
            profile_id = profile.get("id", "unknown_profile")

        if history_titles is None:
            history_titles = self.get_channel_history_titles(profile_id)

        data = input_data or {}
        result = self.check(profile, stage, data, history_titles=history_titles)
        result["profile_id"] = profile_id
        result["stage"] = stage
        return result
