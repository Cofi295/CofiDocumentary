from __future__ import annotations

import copy
import json
from pathlib import Path
import re
from typing import Any

# Multi-lingual documentary verbatim quote patterns:
# 1. Court verdicts & official judicial rulings
# 2. Official warrants, indictment seals & police search records
# 3. Witness & suspect statements, confessions & testimonies

_COURT_VERDICT_PATTERNS = [
    # Korean
    r"판결문", r"법원\s*판결", r"재판부(?:는|의)?", r"사형에\s*처한다", r"무기징역",
    r"유죄(?:를)?\s*선고", r"주문\s*:\s*피고인", r"인민법원\s*판결", r"선고공판",
    # English
    r"court\s*verdict", r"verdict\s*:", r"court\s*ruled", r"sentenced\s*to",
    r"the\s*judge\s*(?:stated|declared|ruled)", r"found\s*guilty", r"official\s*ruling",
    # Vietnamese
    r"bản\s*án", r"tòa\s*tuyên\s*án", r"hội\s*đồng\s*xét\s*xử", r"phán\s*quyết\s*của\s*tòa",
    # Japanese
    r"判決", r"判決文", r"裁判長", r"死刑に処する", r"有罪判決",
    # Chinese
    r"判决", r"判决书", r"宣判", r"法院判决", r"判处死刑", r"无期徒刑",
]

_OFFICIAL_WARRANT_PATTERNS = [
    # Korean
    r"영장", r"압수수색", r"체포영장", r"구속영장", r"수배령", r"1급\s*수배",
    r"공안부\s*공식\s*발표", r"수사\s*기록", r"감정서",
    # English
    r"warrant", r"arrest\s*warrant", r"search\s*warrant", r"official\s*warrant",
    r"police\s*blotter", r"official\s*indictment", r"indictment\s*record",
    # Vietnamese
    r"lệnh\s*bắt", r"lệnh\s*khám\s*xét", r"lệnh\s*truy\s*nã", r"hồ\s*sơ\s*điều\s*tra",
    # Japanese
    r"逮捕状", r"捜索差押令状", r"指名手配", r"令状",
    # Chinese
    r"通缉令", r"搜查令", r"逮捕令", r"立案决定书",
]

_WITNESS_SUSPECT_PATTERNS = [
    # Korean
    r"목격자\s*진술", r"피의자\s*진술", r"자백", r"진술\s*:", r"증언\s*:",
    r"목격자는\s*말했다", r"피의자는\s*이렇게\s*말했다", r"취조실\s*기록",
    # English
    r"witness\s*statement", r"testimony\s*:", r"confessed\s*:", r"statement\s*:",
    r"suspect\s*stated", r"witness\s*recalled", r"in\s*their\s*confession",
    # Vietnamese
    r"lời\s*khai", r"nhân\s*chứng\s*khai", r"nhân\s*chứng\s*kể", r"lời\s*thú\s*tội",
    r"nghi\s*phạm\s*khai",
    # Japanese
    r"目撃者の証言", r"供述", r"自白", r"証言\s*:", r"供述\s*:",
    # Chinese
    r"目击者证言", r"口供", r"供述", r"交代\s*:",
]

_ALL_QUOTE_REGEX = re.compile(
    "|".join(f"(?:{p})" for p in (
        _COURT_VERDICT_PATTERNS + _OFFICIAL_WARRANT_PATTERNS + _WITNESS_SUSPECT_PATTERNS
    )),
    re.IGNORECASE,
)

_QUOTATION_MARK_REGEX = re.compile(r'["“「\']([^"”」\']{6,120})["”」\']')


def detect_verbatim_quotes(text: str) -> bool:
    """Analyze a dialogue/narration line to determine if it is a verbatim documentary quote."""
    raw = str(text or "").strip()
    if not raw or len(raw) < 4:
        return False

    # Check for direct keyword matches
    if _ALL_QUOTE_REGEX.search(raw):
        return True

    # Check for quoted speech with explicit attribution
    if _QUOTATION_MARK_REGEX.search(raw):
        attribution_markers = (
            "말했다", "진술", "증언", "기록", "판결", "선고",
            "said", "stated", "recalled", "testified", "confessed",
            "khai", "nói", "kể", "bảo", "tuyên",
        )
        lower = raw.lower()
        if any(marker in lower for marker in attribution_markers) or ":" in raw or "：" in raw:
            return True

    return False


def score_quote_candidate(text: str) -> int:
    """Score a beat text on its documentary quote likelihood."""
    raw = str(text or "").strip()
    if not raw:
        return 0
    score = 0
    for p in _COURT_VERDICT_PATTERNS:
        if re.search(p, raw, re.IGNORECASE):
            score += 10
            break
    for p in _OFFICIAL_WARRANT_PATTERNS:
        if re.search(p, raw, re.IGNORECASE):
            score += 8
            break
    for p in _WITNESS_SUSPECT_PATTERNS:
        if re.search(p, raw, re.IGNORECASE):
            score += 6
            break
    if _QUOTATION_MARK_REGEX.search(raw):
        score += 4
    if ":" in raw or "：" in raw:
        score += 2
    return score


def tag_verbatim_quotes(
    beats: list[dict[str, Any]],
    *,
    target_min: int = 3,
    target_max: int = 5,
) -> list[dict[str, Any]]:
    """Analyze script dialogue beats to detect 3–5 short verbatim documentary quotes per episode.

    Tags matching beats with `is_verbatim_quote = True`. Clamps to max 5 quotes.
    If the script has zero quotes, all beats remain `is_verbatim_quote = False`.
    """
    if not beats:
        return []

    # Check if any beats are already explicitly tagged
    explicitly_tagged_indices = [
        idx for idx, b in enumerate(beats)
        if b.get("is_verbatim_quote") is True or b.get("is_quote") is True
    ]

    scored_candidates: list[tuple[int, int, int]] = []  # (score, -length, index)
    for idx, b in enumerate(beats):
        if idx in explicitly_tagged_indices:
            continue
        text = str(b.get("narration_text") or b.get("text") or "").strip()
        score = score_quote_candidate(text)
        if score > 0 or detect_verbatim_quotes(text):
            scored_candidates.append((score, -len(text), idx))

    scored_candidates.sort(reverse=True)

    selected_indices: set[int] = set()
    # Prioritize already explicitly tagged quotes
    for idx in explicitly_tagged_indices:
        if len(selected_indices) < target_max:
            selected_indices.add(idx)

    # Add top scored candidates until reaching up to target_max quotes
    for _, _, idx in scored_candidates:
        if len(selected_indices) >= target_max:
            break
        selected_indices.add(idx)

    out_beats: list[dict[str, Any]] = []
    for idx, b in enumerate(beats):
        b_copy = copy.deepcopy(b)
        b_copy["is_verbatim_quote"] = idx in selected_indices
        out_beats.append(b_copy)

    return out_beats


def analyze_and_tag_visual_manifest(
    workspace_or_path: str | Path,
    *,
    target_min: int = 3,
    target_max: int = 5,
) -> dict[str, Any]:
    """Load visual_manifest.json, analyze dialogue beats, tag 3–5 verbatim quotes, and persist back."""
    target = Path(workspace_or_path)
    manifest_path = target if target.is_file() else target / "visual_manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"visual_manifest.json not found at {manifest_path}")

    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    beats = [b for b in (data.get("beats") or []) if isinstance(b, dict)]
    tagged = tag_verbatim_quotes(beats, target_min=target_min, target_max=target_max)
    data["beats"] = tagged

    manifest_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    # Also keep plan_visual_manifest.json in sync if it exists in the same folder
    plan_path = manifest_path.parent / "plan_visual_manifest.json"
    if plan_path.exists() and plan_path != manifest_path:
        try:
            plan_data = json.loads(plan_path.read_text(encoding="utf-8"))
            plan_beats = [b for b in (plan_data.get("beats") or []) if isinstance(b, dict)]
            plan_tagged = tag_verbatim_quotes(plan_beats, target_min=target_min, target_max=target_max)
            plan_data["beats"] = plan_tagged
            plan_path.write_text(json.dumps(plan_data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    return data


def route_multi_voice_quotes(
    beats: list[dict[str, Any]],
    profile: dict[str, Any],
) -> list[dict[str, Any]]:
    """Route 3-5 short verbatim documentary quotes to secondary_voice_id when configured."""
    primary_voice = profile.get("voice_id") or "voice-narrator-default"
    raw_sec = profile.get("secondary_voice_id")
    secondary_voice = str(raw_sec).strip() if raw_sec and str(raw_sec).strip() else None

    routed_beats: list[dict[str, Any]] = []
    verbatim_quote_count = 0

    for beat in beats:
        b = copy.deepcopy(beat)
        is_quote = bool(b.get("is_verbatim_quote") or b.get("is_quote"))
        if is_quote and secondary_voice and verbatim_quote_count < 5:
            b["assigned_voice_id"] = secondary_voice
            b["voice_role"] = "secondary_quote"
            b["speaker_type"] = "secondary"
            b["voice_id"] = secondary_voice
            verbatim_quote_count += 1
        else:
            b["assigned_voice_id"] = primary_voice
            b["voice_role"] = "primary_narrator"
            b["speaker_type"] = "primary"
            b["voice_id"] = primary_voice
        routed_beats.append(b)

    return routed_beats


class ScriptEngine:
    """Documentary script engine with verbatim quote detection and multi-voice dispatch."""

    def __init__(self, workspace: str | Path | None = None):
        self.workspace = Path(workspace) if workspace else None

    def tag_quotes(
        self,
        beats: list[dict[str, Any]],
        *,
        target_min: int = 3,
        target_max: int = 5,
    ) -> list[dict[str, Any]]:
        return tag_verbatim_quotes(beats, target_min=target_min, target_max=target_max)

    def route_voices(
        self,
        beats: list[dict[str, Any]],
        profile: dict[str, Any],
    ) -> list[dict[str, Any]]:
        return route_multi_voice_quotes(beats, profile)

    def process_workspace(self, workspace: str | Path | None = None) -> dict[str, Any]:
        ws = Path(workspace or self.workspace)
        return analyze_and_tag_visual_manifest(ws)
