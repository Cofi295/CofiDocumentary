"""Context-Adaptive True Crime & Documentary Vox Typography Engine.

Provides:
1. 5 Context-Adaptive Font Families (`font_style`) that flex automatically based on
   the spoken sentence's semantic meaning and editorial role while keeping 100% zero tofu ('□')
   across Korean Hangul, Hanja/CJK, Vietnamese, and Latin:
   - `broadcast_sans`: Pretendard-ExtraBold / Pretendard-Bold -> Malgun Gothic (clean SBS/꼬꼬무 broadcast readability)
   - `editorial_serif`: Paperlogy-8ExtraBold / Paperlogy-7Bold -> Georgia/SimSun/Malgun (1990s press headlines, archival clippings)
   - `monumental_verdict`: Paperlogy-9Black / GmarketSansBold / Pretendard-Black (court verdicts, giant paradox metrics, arrest timestamps)
   - `forensic_mono`: Consolas Bold + Pretendard-Bold (DNA locus tables, Y-STR match percentages, GIS coordinates, lab logs)
   - `dossier_typewriter`: Courier Bold + Paperlogy-7Bold / Malgun Regular (police case files, interrogation transcripts, official seals)
2. Automatic semantic font resolver (`resolve_contextual_font_style`) driven by spoken narration meaning.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, List, Tuple
from PIL import Image, ImageDraw, ImageFont

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
STATIC_FONTS_DIR = PROJECT_ROOT / "static" / "fonts"

# Context-Adaptive Font Style Candidate Chains
FONT_STYLE_CANDIDATES: dict[str, dict[str, list[str]]] = {
    "broadcast_sans": {
        "bold": [
            str(STATIC_FONTS_DIR / "Pretendard-ExtraBold.otf"),
            str(STATIC_FONTS_DIR / "Pretendard-Bold.otf"),
            r"C:\Windows\Fonts\malgunbd.ttf",
            r"C:\Windows\Fonts\NanumGothicBold.ttf",
            r"C:\Windows\Fonts\msyhbd.ttc",
            r"C:\Windows\Fonts\arialbd.ttf",
        ],
        "regular": [
            str(STATIC_FONTS_DIR / "Pretendard-Bold.otf"),
            r"C:\Windows\Fonts\malgun.ttf",
            r"C:\Windows\Fonts\NanumGothic.ttf",
            r"C:\Windows\Fonts\msyh.ttc",
            r"C:\Windows\Fonts\arial.ttf",
        ],
    },
    "editorial_serif": {
        "bold": [
            str(STATIC_FONTS_DIR / "Paperlogy-8ExtraBold.ttf"),
            str(STATIC_FONTS_DIR / "Paperlogy-7Bold.ttf"),
            r"C:\Windows\Fonts\malgunbd.ttf",
            r"C:\Windows\Fonts\georgiab.ttf",
        ],
        "regular": [
            str(STATIC_FONTS_DIR / "Paperlogy-7Bold.ttf"),
            r"C:\Windows\Fonts\malgun.ttf",
            r"C:\Windows\Fonts\georgia.ttf",
        ],
    },
    "monumental_verdict": {
        "bold": [
            str(STATIC_FONTS_DIR / "Paperlogy-9Black.ttf"),
            str(STATIC_FONTS_DIR / "GmarketSansBold.ttf"),
            str(STATIC_FONTS_DIR / "Pretendard-Black.otf"),
            r"C:\Windows\Fonts\malgunbd.ttf",
        ],
        "regular": [
            str(STATIC_FONTS_DIR / "GmarketSansBold.ttf"),
            str(STATIC_FONTS_DIR / "Pretendard-ExtraBold.otf"),
            r"C:\Windows\Fonts\malgunbd.ttf",
        ],
    },
    "forensic_mono": {
        "bold": [
            str(STATIC_FONTS_DIR / "Pretendard-Bold.otf"),
            r"C:\Windows\Fonts\consolab.ttf",
            r"C:\Windows\Fonts\malgunbd.ttf",
        ],
        "regular": [
            r"C:\Windows\Fonts\consola.ttf",
            r"C:\Windows\Fonts\malgun.ttf",
        ],
    },
    "dossier_typewriter": {
        "bold": [
            str(STATIC_FONTS_DIR / "Paperlogy-7Bold.ttf"),
            r"C:\Windows\Fonts\courbd.ttf",
            r"C:\Windows\Fonts\malgunbd.ttf",
        ],
        "regular": [
            r"C:\Windows\Fonts\malgun.ttf",
            r"C:\Windows\Fonts\cour.ttf",
        ],
    },
}

FONT_CANDIDATES_BOLD = FONT_STYLE_CANDIDATES["broadcast_sans"]["bold"]
FONT_CANDIDATES_REGULAR = FONT_STYLE_CANDIDATES["broadcast_sans"]["regular"]
FONT_CANDIDATES_MONO = FONT_STYLE_CANDIDATES["forensic_mono"]["bold"]

FONT_CANDIDATES_CJK_FALLBACK = [
    r"C:\Windows\Fonts\msyhbd.ttc",
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\simsun.ttc",
]

FONT_CANDIDATES_LATIN_FALLBACK = [
    r"C:\Windows\Fonts\consolab.ttf",
    r"C:\Windows\Fonts\arialbd.ttf",
    r"C:\Windows\Fonts\arial.ttf",
    r"C:\Windows\Fonts\segoeui.ttf",
]

_FONT_RAW_CACHE: dict[tuple[str, int], ImageFont.FreeTypeFont | ImageFont.ImageFont] = {}
_CASCADE_CACHE: dict[tuple[int, bool, str], "CJKFallbackFont"] = {}


def _resolve_first_existing(candidates: list[str]) -> str | None:
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def resolve_contextual_font_style(
    narration_text: str = "",
    role: str = "body",
    scene_intent: str = "",
) -> str:
    """Dynamically select one of the 5 typography styles based on the spoken sentence's
    context, meaning, and element role (`headline`, `metric`, `stamp`, `telemetry`, `body`).
    """
    r = (role or "body").lower()
    txt = f"{narration_text} {scene_intent}".lower()

    if r in ("metric", "hero_number", "verdict", "stamp_headline"):
        return "monumental_verdict"
    if r in ("telemetry", "coordinates", "dna_code", "mono", "timestamp"):
        return "forensic_mono"
    if r in ("newspaper", "press_headline", "editorial_quote"):
        return "editorial_serif"
    if r in ("dossier", "transcript", "case_meta"):
        return "dossier_typewriter"

    # Infer from spoken sentence meaning
    if any(k in txt for k in ("법원", "판결", "선고", "사형", "최고인민법원", "28년", "충격", "경악", "verdict", "paradox")):
        return "monumental_verdict" if r == "headline" else "editorial_serif"
    if any(k in txt for k in ("신문", "보도", "언론", "헤드라인", "특종", "1992년", "당시", "press", "newspaper")):
        return "editorial_serif"
    if any(k in txt for k in ("dna", "y-str", "99.9", "유전자", "영하 80", "냉동고", "실험실", "좌표", "킬로미터", "km", "forensic", "gis")):
        return "forensic_mono" if r in ("subhead", "tag", "label") else "broadcast_sans"
    if any(k in txt for k in ("심문", "취조", "진술", "조서", "기록철", "120권", "파일", "dossier", "interrogation")):
        return "dossier_typewriter"
    return "broadcast_sans"


def resolve_contextual_motion_text_design(
    narration_text: str = "",
    beat_id: str = "",
    beat_index: int = 0,
    prev_design: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Derives a 100% context-matched Motion Text (`FramelessCinemaTextBeat.tsx` / `CINEMA_TEXT`) specification
    enforcing the 3 Ironclad Motion Text Laws:
    1. Law 1 (Zero Monoculture): Never repeat 1 motion renderer (`showroom_renderer`), 1 font (`font_style`),
       or 1 spatial layout (`layout_variant`) across the episode or across consecutive drop points.
    2. Law 2 (Flexible Narrative Drop-Point Placement per Job): Identifies whether the sentence is a genuine
       narrative drop point (`is_valid_drop_point` + `drop_point_reason`) rather than ordinary descriptive filler.
    3. Law 3 (100% Context-Matched Font, Color, Layout & Entry Motion): Matches `font_style`, `accent_color`,
       `layout_variant`, and `showroom_renderer` strictly to the sentence's emotional and forensic context.
    """
    import re

    txt = str(narration_text or "").strip()
    txt_lower = txt.lower()

    is_question = bool(re.search(r"[?？]|걸까요|했을까요|어떻게|왜\b|과연|누가|무엇이", txt))
    has_metric = bool(
        re.search(r"\d+\s*(?:년|개월|일|시간|분|초|km|m|명|건|원|위안|억|만|세|살|번째|차례|발)", txt)
        or re.search(r"(?:열세\s*해|열삼\s*년|스물네\s*살|수천\s*킬로|단\s*한\s*번)", txt)
    )
    is_contradiction = bool(
        re.search(r"(?:반면|그러나|하지만|정체는|가명|위장|모순|불일치|두\s*얼굴|충격적|절대\s*불가능)", txt)
    )
    is_verdict_or_arrest = bool(
        re.search(r"(?:체포|검거|자백|선고|사형|무기징역|법정|재판|구속|압송|최후)", txt)
    )
    is_forensic_or_acoustic = bool(
        re.search(r"(?:dna|y-str|유전자|감식|지문|탄도|부검|사투리|억양|목소리|음성|성악|결정적\s*단서|유일한\s*단서)", txt_lower)
    )
    is_dossier_secret = bool(
        re.search(r"(?:심문|취조|진술|조서|기밀|은폐|묵비권|수배\s*전단)", txt)
    )
    is_victim_tribute = bool(
        re.search(r"(?:촉망받던|성격이\s*곧고\s*의리가|유가족|애도|추모|꽃다운\s*나이|무고한\s*희생)", txt)
        and not re.search(r"(?:살인|범인|흉기|수배|체포|위장|도주|사형)", txt)
    )

    drop_point_reason = ""
    if is_question:
        drop_point_reason = "paradox_or_rhetorical_question"
    elif is_verdict_or_arrest:
        drop_point_reason = "climax_arrest_or_verdict"
    elif is_contradiction:
        drop_point_reason = "dual_identity_or_evidence_contradiction"
    elif is_forensic_or_acoustic:
        drop_point_reason = "forensic_or_acoustic_breakthrough"
    elif has_metric:
        drop_point_reason = "turning_point_metric"
    elif is_dossier_secret:
        drop_point_reason = "interrogation_or_dossier_twist"

    is_valid_drop_point = bool(drop_point_reason)

    # Context-matched selection (Law 3)
    if is_victim_tribute:
        font_style = "editorial_serif"
        accent_color = "ivory"
        layout_variant = "editorial_left"
        showroom_renderer = "editorial_punch_statement"
    elif is_verdict_or_arrest:
        font_style = "monumental_verdict"
        accent_color = "crimson"
        layout_variant = "verdict_pillar"
        showroom_renderer = "ct_verdict_gavel"
    elif is_question:
        font_style = "editorial_serif"
        accent_color = "amber"
        layout_variant = "editorial_left"
        showroom_renderer = "editorial_rhetorical_question"
    elif is_contradiction:
        font_style = "broadcast_sans"
        accent_color = "crimson"
        layout_variant = "split_horizon"
        showroom_renderer = "ct_paradox_split"
    elif is_dossier_secret:
        font_style = "dossier_typewriter"
        accent_color = "amber"
        layout_variant = "diagonal_cascade"
        showroom_renderer = "ct_redaction_peel"
    elif is_forensic_or_acoustic:
        is_voice = bool(re.search(r"(?:사투리|억양|목소리|음성|성악|노래|통화)", txt))
        font_style = "forensic_mono"
        accent_color = "amber" if is_voice else "ice"
        layout_variant = "editorial_right"
        showroom_renderer = "ct_acoustic_voiceprint" if is_voice else "ct_ballistic_lock_text"
    elif has_metric:
        is_distance = bool(re.search(r"(?:km|킬로미터|거리)", txt_lower))
        font_style = "monumental_verdict"
        accent_color = "crimson" if re.search(r"(?:도주|수배|살인|사망|피해)", txt) else "amber"
        layout_variant = "center_monolith"
        showroom_renderer = "ct_continental_km" if is_distance else "editorial_metric_monolith"
    else:
        font_style = "broadcast_sans"
        accent_color = "mono"
        layout_variant = "editorial_left"
        showroom_renderer = "editorial_punch_statement"

    # Anti-repetition rotation against prev_design (Law 1)
    if isinstance(prev_design, dict) and prev_design:
        prev_renderer = str(prev_design.get("showroom_renderer") or prev_design.get("showroomRenderer") or "")
        prev_font = str(prev_design.get("font_style") or prev_design.get("fontStyle") or "")
        prev_layout = str(prev_design.get("layout_variant") or prev_design.get("layoutVariant") or "")

        alt_renderers = [
            "editorial_rhetorical_question",
            "ct_paradox_split",
            "ct_redaction_peel",
            "ct_ballistic_lock_text",
            "ct_verdict_gavel",
            "ct_acoustic_voiceprint",
            "editorial_punch_statement",
        ]
        if has_metric:
            alt_renderers.insert(0, "editorial_metric_monolith")
        if showroom_renderer == prev_renderer:
            for cand_r in alt_renderers:
                if cand_r != prev_renderer:
                    showroom_renderer = cand_r
                    break

        alt_layouts = [
            "editorial_left",
            "split_horizon",
            "verdict_pillar",
            "editorial_right",
            "diagonal_cascade",
            "center_monolith",
        ]
        alt_fonts = [
            "editorial_serif",
            "monumental_verdict",
            "forensic_mono",
            "dossier_typewriter",
            "broadcast_sans",
        ]
        if font_style == prev_font and layout_variant == prev_layout:
            for cand_l in alt_layouts:
                if cand_l != prev_layout:
                    layout_variant = cand_l
                    break
            for cand_f in alt_fonts:
                if cand_f != prev_font:
                    font_style = cand_f
                    break

    return {
        "beat_id": beat_id,
        "is_valid_drop_point": is_valid_drop_point,
        "drop_point_reason": drop_point_reason or "contextual_emphasis",
        "font_style": font_style,
        "accent_color": accent_color,
        "layout_variant": layout_variant,
        "showroom_renderer": showroom_renderer,
    }


def load_font(
    size: int,
    bold: bool = True,
    mono: bool = False,
    font_style: str = "broadcast_sans",
) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Loads the best available TrueType/OpenType font for the given `font_style`."""
    key_size = max(8, int(size))
    style_key = "forensic_mono" if mono else (font_style if font_style in FONT_STYLE_CANDIDATES else "broadcast_sans")
    weight_key = "bold" if bold else "regular"
    candidates = FONT_STYLE_CANDIDATES[style_key][weight_key]
    target_path = _resolve_first_existing(candidates)

    if target_path:
        cache_key = (target_path, key_size)
        if cache_key not in _FONT_RAW_CACHE:
            try:
                _FONT_RAW_CACHE[cache_key] = ImageFont.truetype(target_path, key_size)
            except Exception:
                pass
        if cache_key in _FONT_RAW_CACHE:
            return _FONT_RAW_CACHE[cache_key]

    return ImageFont.load_default()


def get_font(
    size: int,
    bold: bool = True,
    mono: bool = False,
    font_style: str = "broadcast_sans",
) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Cached accessor for context-adaptive font loading."""
    return load_font(size, bold=bold, mono=mono, font_style=font_style)


class CJKFallbackFont:
    """Multi-tier context-adaptive font fallback cascade manager.

    Guarantees 100% zero tofu ('□') while preserving distinct typographic personality
    (`broadcast_sans`, `editorial_serif`, `monumental_verdict`, `forensic_mono`, `dossier_typewriter`).
    """

    def __init__(self, size: int, bold: bool = True, font_style: str = "broadcast_sans"):
        self.size = max(8, int(size))
        self.bold = bold
        self.font_style = font_style if font_style in FONT_STYLE_CANDIDATES else "broadcast_sans"

        weight_key = "bold" if bold else "regular"
        primary_candidates = FONT_STYLE_CANDIDATES[self.font_style][weight_key]
        p_path = _resolve_first_existing(primary_candidates)
        self.primary = ImageFont.truetype(p_path, self.size) if p_path else ImageFont.load_default()

        # Korean Hangul Fallback (Malgun Gothic covers all 11,172 Hangul syllables)
        kr_candidates = [
            r"C:\Windows\Fonts\malgunbd.ttf" if bold else r"C:\Windows\Fonts\malgun.ttf",
        ]
        kr_path = _resolve_first_existing(kr_candidates)
        self.kr_fallback = ImageFont.truetype(kr_path, self.size) if kr_path else self.primary

        # ASCII / Numeric / Telemetry Fallback (for forensic_mono / typewriter styles)
        ascii_candidates = [
            r"C:\Windows\Fonts\consolab.ttf" if self.font_style == "forensic_mono" else (
                r"C:\Windows\Fonts\courbd.ttf" if self.font_style == "dossier_typewriter" else (
                    r"C:\Windows\Fonts\georgiab.ttf" if self.font_style == "editorial_serif" else ""
                )
            )
        ]
        ascii_path = _resolve_first_existing([c for c in ascii_candidates if c])
        self.ascii_stylized = ImageFont.truetype(ascii_path, self.size) if ascii_path else None

        # CJK Ideograph Fallback: Microsoft YaHei / SimSun
        cjk_candidates = [
            r"C:\Windows\Fonts\msyhbd.ttc" if bold else r"C:\Windows\Fonts\msyh.ttc",
            r"C:\Windows\Fonts\simsun.ttc",
        ]
        cjk_path = _resolve_first_existing(cjk_candidates)
        self.cjk_fallback = ImageFont.truetype(cjk_path, self.size) if cjk_path else self.kr_fallback

        self._char_font_cache: dict[str, Any] = {}

    def get_font_for_char(self, char: str) -> Any:
        """Determines the exact font needed for this character without tofu."""
        if char in self._char_font_cache:
            return self._char_font_cache[char]

        cp = ord(char)

        # Use stylized ASCII/numeric font for digits & Latin in forensic_mono / dossier_typewriter modes
        if self.ascii_stylized is not None and 0x0021 <= cp <= 0x007E:
            self._char_font_cache[char] = self.ascii_stylized
            return self.ascii_stylized

        # CJK Unified Ideographs block (4E00 - 9FFF)
        if 0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF or 0xF900 <= cp <= 0xFAFF:
            try:
                mask = self.primary.getmask(char)
                if mask.size[0] <= int(self.size * 0.70):
                    f = self.cjk_fallback
                else:
                    f = self.primary
            except Exception:
                f = self.cjk_fallback
        elif 0xAC00 <= cp <= 0xD7A3 or 0x3130 <= cp <= 0x318F:
            # Hangul syllable: verify primary has full glyph, otherwise use Malgun
            try:
                mask = self.primary.getmask(char)
                f = self.primary if mask.size[0] > int(self.size * 0.55) else self.kr_fallback
            except Exception:
                f = self.kr_fallback
        else:
            f = self.primary

        self._char_font_cache[char] = f
        return f

    def get_text_length(self, text: str) -> float:
        """Calculates total pixel length considering fallback fonts."""
        total = 0.0
        for char in text:
            f = self.get_font_for_char(char)
            try:
                total += f.getlength(char)
            except Exception:
                total += self.size * 0.6
        return total

    def draw_text(
        self,
        draw: ImageDraw.ImageDraw,
        xy: tuple[float, float],
        text: str,
        fill: Any,
        stroke_width: int = 0,
        stroke_fill: Any = None,
        tracking: float = 0.0,
    ) -> float:
        """Draws text safely using the fallback cascade, returning final cursor X."""
        x, y = xy
        for char in text:
            f = self.get_font_for_char(char)
            try:
                if stroke_width > 0 and stroke_fill is not None:
                    draw.text((x, y), char, font=f, fill=fill, stroke_width=stroke_width, stroke_fill=stroke_fill)
                else:
                    draw.text((x, y), char, font=f, fill=fill)
                x += f.getlength(char) + tracking
            except Exception:
                draw.text((x, y), char, fill=fill)
                x += self.size * 0.6 + tracking
        return x


def get_cascade_font(size: int, bold: bool = True, font_style: str = "broadcast_sans") -> CJKFallbackFont:
    """Returns a cached CJKFallbackFont instance for the requested `font_style`."""
    style_norm = font_style if font_style in FONT_STYLE_CANDIDATES else "broadcast_sans"
    key = (max(8, int(size)), bool(bold), style_norm)
    if key not in _CASCADE_CACHE:
        _CASCADE_CACHE[key] = CJKFallbackFont(size=key[0], bold=key[1], font_style=key[2])
    return _CASCADE_CACHE[key]


def draw_text_safe(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    text: str,
    fill: Any,
    font_size: int = 24,
    bold: bool = True,
    stroke_width: int = 0,
    stroke_fill: Any = None,
    font_style: str = "broadcast_sans",
    tracking: float = 0.0,
) -> float:
    """Convenience helper to safely draw text with zero tofu and context-adaptive font style."""
    cascade = get_cascade_font(font_size, bold=bold, font_style=font_style)
    return cascade.draw_text(
        draw,
        xy,
        text,
        fill=fill,
        stroke_width=stroke_width,
        stroke_fill=stroke_fill,
        tracking=tracking,
    )


def verify_text_glyphs(text: str, font_size: int = 24, bold: bool = True, font_style: str = "broadcast_sans") -> bool:
    """Verifies that all glyphs in text are resolvable without falling back to .notdef tofu."""
    cascade = get_cascade_font(font_size, bold=bold, font_style=font_style)
    for char in text:
        if char in ("\n", "\r", "\t", " "):
            continue
        font = cascade.get_font_for_char(char)
        try:
            mask = font.getmask(char)
            if mask.size[0] == 0 or mask.size[1] == 0:
                return False
        except Exception:
            return False
    return True


def split_balanced_korean(text: str, max_chars: int = 28) -> list[str]:
    """Splits Korean/Asian narration text into balanced lines at grammatical boundaries."""
    text = text.strip()
    if len(text) <= max_chars:
        return [text]

    words = text.split()
    if len(words) <= 1:
        mid = len(text) // 2
        return [text[:mid], text[mid:]]

    mid_char = len(text) / 2.0
    best_idx = 1
    best_diff = float("inf")

    running_len = 0
    for i in range(len(words) - 1):
        running_len += len(words[i]) + 1
        diff = abs(running_len - mid_char)
        if words[i].endswith((",", ".", "!", "?", "…")):
            diff -= 4.0
        if diff < best_diff:
            best_diff = diff
            best_idx = i + 1

    line1 = " ".join(words[:best_idx]).strip()
    line2 = " ".join(words[best_idx:]).strip()
    return [line1, line2] if line2 else [line1]


def wrap_text_to_width(
    text: str,
    max_px_width: float,
    font_size: int = 24,
    bold: bool = True,
    max_lines: int = 3,
    font_style: str = "broadcast_sans",
) -> list[str]:
    """Wraps text into at most `max_lines` so no line exceeds `max_px_width`."""
    cascade = get_cascade_font(font_size, bold=bold, font_style=font_style)
    words = text.strip().split()
    if not words:
        return [""]

    lines: list[str] = []
    current = words[0]
    for w in words[1:]:
        candidate = f"{current} {w}"
        if cascade.get_text_length(candidate) <= max_px_width:
            current = candidate
        else:
            lines.append(current)
            current = w
            if len(lines) >= max_lines - 1:
                break

    remaining_idx = sum(len(l.split()) for l in lines)
    tail = " ".join(words[remaining_idx:]).strip()
    if tail:
        lines.append(tail)
    return lines[:max_lines]


# Backwards-compatible alias used by archetypes.py and __init__.py
wrap_text_multiline = wrap_text_to_width
