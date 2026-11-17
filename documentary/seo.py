"""SEO Synthetic-Media Transparency & Packaging Module."""
from __future__ import annotations

import importlib
import json
from pathlib import Path
from typing import Any

try:
    from . import hot_reload as _hr_mod

    importlib.reload(_hr_mod)
    _hr_mod.ensure_runtime_modules_synced(force=True, caller_module=__name__)
except Exception:
    pass

SYNTHETIC_MEDIA_DISCLOSURE_FOOTERS: dict[str, str] = {
    "ko": "본 다큐멘터리는 사실에 기반한 역사적 사건 기록이며, 일부 장면은 시각적 이해를 돕기 위해 AI 재구성 및 극화 연출 기법이 사용되었습니다.",
    "en": "This documentary is grounded in real historical records; select visual scenes utilize AI-assisted reconstruction and dramatization for educational context.",
    "ja": "本ドキュメンタリーは史実に基づく記録であり、一部の映像は視覚的理解を深めるためAI生成および再現演出を使用しています。",
    "vi": "Bộ phim tài liệu dựa trên các tài liệu lịch sử có thật; một số phân cảnh sử dụng hình ảnh tái hiện AI nhằm tăng cường trực quan.",
}


CREATIVE_DRAMA_DISCLOSURE_FOOTERS: dict[str, str] = {
    "ko": "본 영상은 창작 오디오드라마이며, 이야기 몰입을 위해 일부 시각 연출 화면에 AI 생성 기법이 사용되었습니다.",
    "en": "This video is an original creative audio drama; select visual scenes utilize AI-generated illustration to enhance storytelling immersion.",
    "ja": "本映像は創作オーディオドラマであり、物語への没入感を高めるため一部の演出画面にAI生成技術を使用しています。",
    "vi": "Video này là kịch truyền thanh sáng tác nguyên bản; một số khung hình minh họa sử dụng công nghệ tạo ảnh AI để tăng chiều sâu cảm xúc.",
}


def get_synthetic_media_disclosure_footer(
    language: str = "ko",
    *,
    job: dict[str, Any] | None = None,
) -> str:
    """Return the localized editorial source & synthetic media disclosure footer."""
    lang = (language or "en").strip().lower()
    if isinstance(job, dict):
        snap = job.get("channel_profile_snapshot") if isinstance(job.get("channel_profile_snapshot"), dict) else {}
        prof = job.get("profile") if isinstance(job.get("profile"), dict) else {}
        for guard_src in (
            job.get("youtube_policy_guardrails"),
            snap.get("youtube_policy_guardrails"),
            prof.get("youtube_policy_guardrails"),
        ):
            if isinstance(guard_src, dict):
                custom_disc = str(
                    guard_src.get(f"synthetic_content_disclosure_{lang}")
                    or guard_src.get("synthetic_content_disclosure")
                    or ""
                ).strip()
                if custom_disc:
                    return custom_disc
        cm = str(
            job.get("content_mode")
            or snap.get("content_mode")
            or prof.get("content_mode")
            or ""
        ).strip().lower()
        if cm == "creative_audio_drama":
            return CREATIVE_DRAMA_DISCLOSURE_FOOTERS.get(lang, CREATIVE_DRAMA_DISCLOSURE_FOOTERS["en"])
    return SYNTHETIC_MEDIA_DISCLOSURE_FOOTERS.get(lang, SYNTHETIC_MEDIA_DISCLOSURE_FOOTERS["en"])


def evaluate_seo_synthetic_disclosure(
    package: dict[str, Any],
    uses_ai_visuals: bool = True,
    language: str = "ko",
    *,
    job: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate SEO synthetic content disclosure metadata and description footer."""
    if not isinstance(package, dict):
        raise ValueError("SEO package must be a dictionary")

    desc = str(package.get("description") or "")
    altered_flag = package.get("altered_or_synthetic_content_disclosure_required")
    expected_footer = get_synthetic_media_disclosure_footer(language, job=job)

    if uses_ai_visuals:
        if altered_flag is not True:
            raise RuntimeError("SEO validation failed: altered_or_synthetic_content_disclosure_required must be true")
        if expected_footer not in desc:
            package["description"] = f"{desc}\n\n---\n{expected_footer}"
            package["altered_or_synthetic_content_disclosure_required"] = True

    return {
        "status": "PASSED",
        "altered_flag": package.get("altered_or_synthetic_content_disclosure_required"),
        "has_footer": expected_footer in package.get("description", ""),
    }


def apply_synthetic_media_disclosure(
    package: dict[str, Any],
    uses_ai_visuals: bool = True,
    uses_ai_tts: bool = False,
    language: str = "ko",
    *,
    job: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], bool]:
    """Ensure altered_or_synthetic_content_disclosure_required and localized disclosure footer are present in SEO package."""
    if not isinstance(package, dict):
        return package, False

    changed = False
    expected_footer = get_synthetic_media_disclosure_footer(language, job=job)

    if uses_ai_visuals or uses_ai_tts:
        if package.get("altered_or_synthetic_content_disclosure_required") is not True:
            package["altered_or_synthetic_content_disclosure_required"] = True
            changed = True

        desc = str(package.get("description") or "")
        # Strip legacy documentary footer if accidentally present on a creative_audio_drama job
        doc_footer = SYNTHETIC_MEDIA_DISCLOSURE_FOOTERS.get((language or "en").strip().lower(), "")
        if doc_footer and doc_footer != expected_footer and doc_footer in desc:
            desc = desc.replace(f"\n\n---\n{doc_footer}", "").replace(doc_footer, "").rstrip()
            changed = True
        if expected_footer not in desc:
            if desc.strip():
                package["description"] = f"{desc.rstrip()}\n\n---\n{expected_footer}"
            else:
                package["description"] = expected_footer
            changed = True
        elif changed:
            package["description"] = desc

    return package, changed


def detect_ai_usage_in_project(
    job: dict[str, Any] | None = None,
    workspace: Path | None = None,
) -> tuple[bool, bool]:
    """Detect whether AI visuals or AI TTS are used in the project."""
    job = job if isinstance(job, dict) else {}
    strategy = str(job.get("visual_strategy") or "").strip().lower()

    uses_ai_visuals = strategy in {"full_ai", "hybrid", "evidence_footage", "edit_direct_footage"}
    uses_ai_tts = bool(job.get("voice_id") or job.get("tts_engine") or True)

    if workspace and isinstance(workspace, Path):
        ai_manifest = workspace / "ai_visual_manifest.json"
        if ai_manifest.is_file():
            uses_ai_visuals = True
        visual_manifest = workspace / "visual_manifest.json"
        if visual_manifest.is_file():
            try:
                vm = json.loads(visual_manifest.read_text(encoding="utf-8"))
                beats = vm.get("beats") or []
                for b in beats:
                    if isinstance(b, dict):
                        vt = str(b.get("visual_type") or b.get("kind") or "").lower()
                        if "ai" in vt:
                            uses_ai_visuals = True
                            break
            except Exception:
                pass

    return uses_ai_visuals, uses_ai_tts


def ensure_seo_package_synthetic_disclosure(
    workspace: Path,
    job: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], bool]:
    """Read seo_package.json from workspace, apply disclosure rules, and write back if changed."""
    seo_file = workspace / "seo_package.json"
    if not seo_file.is_file():
        return {}, False

    try:
        package = json.loads(seo_file.read_text(encoding="utf-8"))
    except Exception:
        return {}, False

    job = job if isinstance(job, dict) else {}
    profile = job.get("profile") if isinstance(job.get("profile"), dict) else {}
    snapshot = job.get("channel_profile_snapshot") if isinstance(job.get("channel_profile_snapshot"), dict) else {}
    lang = str(job.get("language") or profile.get("language") or snapshot.get("language") or "ko").strip().lower()

    uses_ai_visuals, uses_ai_tts = detect_ai_usage_in_project(job, workspace)
    package, changed = apply_synthetic_media_disclosure(
        package,
        uses_ai_visuals=uses_ai_visuals,
        uses_ai_tts=uses_ai_tts,
        language=lang,
        job=job,
    )

    if changed:
        temp_file = workspace / f"seo_package.tmp.{Path(__file__).stem}.json"
        temp_file.write_text(json.dumps(package, ensure_ascii=False, indent=2), encoding="utf-8")
        temp_file.replace(seo_file)

    return package, changed
